"""Regenerate this repository's public file inventory (PUBLICATION_MANIFEST.json)."""
import argparse
import datetime
import hashlib
import json
import re
from pathlib import Path

from audit_publication import audit, PATTERNS
from strict_json import loads, read_bounded
from verify_manifest import MANIFEST, portable_path, has_symlink, inventory, file_digest

ROOT = Path(__file__).resolve().parent
MAX_MANIFEST_BYTES = 8 * 1024 * 1024
BOUNDARY = ('Binds bytes and inventory only: not content review, rights clearance, anonymity '
            'or release approval. audit_publication.py and human review remain separate gates. '
            'No target code executes. No replacement of the original manifest. '
            'Detected changes are rejected, but this is not a hostile-filesystem snapshot or lease. '
            'An output write failure may leave a partial new file; it is not removed.')
DECLARATIONS = ('project', 'private_history_imported', 'actual_corpora_included',
                'synthetic_examples_only', 'license_status')


def _safe_text(raw):
    text = raw.decode('utf-8')
    if any(pattern.search(text) for pattern in PATTERNS.values()):
        raise ValueError('manifest metadata or contents fail the publication pattern scan')


def _name(value):
    if (not portable_path(value) or value == MANIFEST
            or any(p in ('.git', '__pycache__') for p in Path(value).parts)):
        raise ValueError('unsafe or excluded inventory path: ' + json.dumps(value, ensure_ascii=True))
    return value


def _output(destination, root):
    requested = Path(destination).absolute()
    if any(p.is_symlink() for p in (requested, *requested.parents)):
        raise ValueError('output path must not contain symlinks')
    target = requested.resolve()
    for excluded in (ROOT, root):
        if target == excluded or excluded in target.parents:
            raise ValueError('write output outside the repository and selected tree')
    if target.exists():
        raise ValueError('output already exists; no files are overwritten')
    if not target.parent.is_dir():
        raise ValueError('output parent must already exist')
    return target


def _read(root, name):
    if has_symlink(root, Path(name)):
        raise ValueError('symlink path not allowed: ' + name)
    path = root / name
    if not path.is_file():
        raise ValueError('missing or nonregular selected file: ' + name)
    raw = path.read_bytes()
    if b'\r' in raw:
        raise ValueError('CR bytes are not allowed; no normalization performed: ' + name)
    return raw


def _original(root):
    if has_symlink(root, Path(MANIFEST)):
        raise ValueError('manifest symlink is not allowed')
    raw = read_bounded(root / MANIFEST, MAX_MANIFEST_BYTES)
    manifest = loads(raw)
    if not isinstance(manifest, dict) or not all(k in manifest for k in DECLARATIONS):
        raise ValueError('manifest declaration fields are required')
    if not isinstance(manifest.get('files'), list):
        raise ValueError('manifest files must be an array')
    if not isinstance(manifest['project'], str) or not isinstance(manifest['license_status'], str):
        raise ValueError('manifest project and license_status must be strings')
    if any(type(manifest[k]) is not bool for k in DECLARATIONS[1:4]):
        raise ValueError('manifest declaration flags must be booleans')
    if 'release' not in manifest or 'date' not in manifest:
        raise ValueError('manifest release and date are required')
    old = {}
    for row in manifest['files']:
        if not isinstance(row, dict):
            raise ValueError('invalid manifest row')
        name = _name(row.get('path'))
        if name in old:
            raise ValueError('duplicate manifest path: ' + name)
        digest = row.get('sha256')
        if (type(row.get('bytes')) is not int or row['bytes'] < 0
                or not isinstance(digest, str) or re.fullmatch('[0-9a-f]{64}', digest) is None):
            raise ValueError('invalid manifest row metadata: ' + name)
        old[name] = row
    if type(manifest.get('file_count')) is not int or manifest['file_count'] != len(old):
        raise ValueError('manifest file count mismatch')
    return raw, manifest, old


def regenerate(root, *, release, date, output, add=(), remove=()):
    root = Path(root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError('ROOT must be an existing directory')
    target = _output(output, root)
    if not isinstance(release, str) or re.fullmatch(r'[0-9]+\.[0-9]+(?:\.[0-9]+)?(?:-[a-z0-9]+(?:-[a-z0-9]+)*)?', release) is None:
        raise ValueError('release must be a numeric dotted version with optional lowercase hyphen suffix')
    if not isinstance(date, str) or re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', date) is None:
        raise ValueError('date must be YYYY-MM-DD')
    datetime.date.fromisoformat(date)
    original, manifest, old = _original(root)
    additions = [_name(name) for name in add]
    removals = [_name(name) for name in remove]
    if len(set(additions)) != len(additions) or len(set(removals)) != len(removals):
        raise ValueError('duplicate add/remove paths')
    if set(additions) & set(removals):
        raise ValueError('add/remove paths must not overlap')
    if set(additions) & set(old):
        raise ValueError('add paths must not already be listed')
    if set(removals) - set(old):
        raise ValueError('remove paths must already be listed')
    actual, errors, enumerated = inventory(root)
    if errors or not enumerated:
        raise ValueError('; '.join(errors))
    selected = (set(old) - set(removals)) | set(additions)
    missing = sorted(selected - actual)
    unlisted = sorted(actual - selected - {MANIFEST})
    if missing or unlisted:
        raise ValueError(json.dumps(dict(missing=missing, unlisted=unlisted), ensure_ascii=True))
    rows, snapshot = [], {}
    for name in sorted(selected):
        raw = _read(root, name)
        snapshot[name] = file_digest(raw)
        # Preserve existing row key order and any declared extension fields.
        row = dict(old[name]) if name in old else dict(path=name, bytes=0, sha256='')
        row['bytes'], row['sha256'] = snapshot[name]
        rows.append(row)
    result = dict(manifest)
    result['release'], result['date'] = release, date
    result['file_count'], result['files'] = len(rows), rows
    encoded = (json.dumps(result, indent=2) + '\n').encode('utf-8')
    if len(encoded) > MAX_MANIFEST_BYTES:
        raise ValueError('generated manifest exceeds 8 MiB')
    _safe_text(encoded)
    scan = audit(root)
    if not scan['pass']:
        raise ValueError('selected tree fails publication audit: ' + json.dumps(scan['errors'], ensure_ascii=True))
    # Recheck all inputs and names after generation/audit, before exclusive creation.
    if read_bounded(root / MANIFEST, MAX_MANIFEST_BYTES) != original:
        raise ValueError('source manifest changed during generation')
    after, errors, enumerated = inventory(root)
    if errors or not enumerated or after != actual:
        raise ValueError('source inventory changed during generation')
    for name, digest in snapshot.items():
        if file_digest(_read(root, name)) != digest:
            raise ValueError('source bytes changed during generation: ' + name)
    target = _output(target, root)
    summary = dict(schema='persona.manifest-regeneration.v1', added=sorted(additions),
                   removed=sorted(removals), rehashed=sorted(selected & set(old)),
                   changed=sorted(name for name in selected & set(old)
                                  if snapshot[name] != (old[name]['bytes'], old[name]['sha256'])),
                   bytes=len(encoded), sha256=hashlib.sha256(encoded).hexdigest(), boundary=BOUNDARY)
    # Serialize before writing so summary encoding failure cannot cause a silent saved file.
    json.dumps(summary, ensure_ascii=True)
    with target.open('x', encoding='utf-8', newline='\n') as stream:
        written = stream.write(encoded.decode('utf-8'))
        if written != len(encoded.decode('utf-8')):
            raise OSError('incomplete output write; partial new file retained')
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, epilog=BOUNDARY)
    parser.add_argument('root', nargs='?', type=Path, default=ROOT, metavar='ROOT')
    parser.add_argument('--release', required=True)
    parser.add_argument('--date', required=True, metavar='YYYY-MM-DD')
    parser.add_argument('--add', action='append', default=[], metavar='PATH')
    parser.add_argument('--remove', action='append', default=[], metavar='PATH')
    parser.add_argument('--output', required=True, type=Path, metavar='NEWPATH')
    args = parser.parse_args(argv)
    try:
        summary = regenerate(args.root, release=args.release, date=args.date,
                             output=args.output, add=args.add, remove=args.remove)
    except (OSError, ValueError, TypeError, RuntimeError) as exc:
        parser.exit(1, str(exc) + '\n')
    print(json.dumps(summary, ensure_ascii=True, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
