"""Verify the exact selected public file inventory and its LF-normalized bytes."""
import hashlib
import argparse
import json
import os
from pathlib import Path, PurePosixPath
from strict_json import load

EXCLUDED_PARTS = {'.git', '__pycache__'}
MANIFEST = 'PUBLICATION_MANIFEST.json'


def portable_path(value):
    if not isinstance(value, str) or not value or '\\' in value or ':' in value:
        return False
    path = PurePosixPath(value)
    return (not path.is_absolute() and path.as_posix() == value and value != '.'
            and '..' not in path.parts and not any(p in EXCLUDED_PARTS for p in path.parts)
            and not any(ord(c) < 32 for c in value))


def has_symlink(root, relative):
    path = root
    for part in relative.parts:
        path = path / part
        if path.is_symlink():
            return True
    return False


def inventory(root):
    """Return exact file names and existing traversal diagnostics without following links."""
    root = Path(root)
    errors = []
    actual = set()
    def walk_error(error):
        raise error
    try:
        for directory, dirs, files in os.walk(root, followlinks=False, onerror=walk_error):
            for name in list(dirs) + files:
                path = Path(directory) / name
                rel = path.relative_to(root)
                if path.is_symlink():
                    errors.append(rel.as_posix() + ': symlink not allowed')
                    if name in dirs:
                        dirs.remove(name)
                    continue
                if rel.parts[0] == '.git':
                    if name in dirs:
                        dirs.remove(name)
                    continue
                if name in files and '__pycache__' in rel.parts and path.suffix == '.pyc':
                    continue
                if name in files:
                    if path.is_file():
                        actual.add(rel.as_posix())
                    else:
                        errors.append(rel.as_posix() + ': nonregular file')
    except OSError as exc:
        return actual, errors + ['cannot enumerate release files: ' + str(exc)], False
    return actual, errors, True


def file_digest(raw):
    """Hash original bytes; checkout, not this helper, supplies LF normalization."""
    return len(raw), hashlib.sha256(raw).hexdigest()


def verify(root):
    root = Path(root)
    errors = []
    if (root / MANIFEST).is_symlink():
        return ['manifest symlink is not allowed']
    try:
        manifest = load(root / MANIFEST)
    except (OSError, ValueError, TypeError) as exc:
        return ['manifest unreadable or invalid: ' + str(exc)]
    if not isinstance(manifest, dict) or not isinstance(manifest.get('files'), list):
        return ['manifest files must be an array']
    actual, errors, enumerated = inventory(root)
    if not enumerated:
        return errors
    seen = set()
    for row in manifest['files']:
        if not isinstance(row, dict) or not portable_path(row.get('path')):
            errors.append('unsafe or noncanonical manifest path')
            continue
        name = row['path']
        if name == MANIFEST:
            errors.append('manifest must not list itself')
            continue
        if name in seen:
            errors.append('duplicate manifest path: ' + name)
        seen.add(name)
        digest = row.get('sha256')
        if (type(row.get('bytes')) is not int or row['bytes'] < 0
                or not isinstance(digest, str) or len(digest) != 64
                or any(c not in '0123456789abcdef' for c in digest)):
            errors.append(name + ': invalid size/hash metadata')
            continue
        relative = Path(name)
        if has_symlink(root, relative):
            errors.append(name + ': symlink path not allowed')
            continue
        path = root / relative
        if not path.is_file():
            errors.append(name + ': missing')
            continue
        try:
            raw = path.read_bytes()
        except OSError as exc:
            errors.append(name + ': unreadable: ' + str(exc))
            continue
        if file_digest(raw) != (row['bytes'], digest):
            errors.append(name + ': size/hash mismatch')
    if type(manifest.get('file_count')) is not int or manifest['file_count'] != len(seen):
        errors.append('file count mismatch')
    for name in sorted(actual - seen - {MANIFEST}):
        errors.append(name + ': unlisted release file')
    for name in sorted(seen - actual):
        errors.append(name + ': not in exact release inventory')
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, epilog='Reads the selected tree as data only; internal consistency or a limited scan is not authenticity, rights clearance or approval.')
    parser.add_argument('root', nargs='?', type=Path, default=Path(__file__).resolve().parent,
                        metavar='ROOT', help='Existing directory to inspect with this trusted script; defaults to the script directory')
    args = parser.parse_args(argv)
    if not args.root.is_dir():
        parser.error('ROOT must be an existing directory')
    result = verify(args.root)
    print(json.dumps(dict(valid=not result, errors=result)))
    return bool(result)


if __name__ == '__main__':
    raise SystemExit(main())
