#!/usr/bin/env python3
"""Declare or compare a private folder's raw file bytes without interpreting its contents."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import unicodedata

import exclusive_output
from corpus_files import read_source_bytes
from journey_inputs import _checked_path, _plain_components
from strict_json import loads
from review_package import display

SCHEMA = 'persona.folder-inventory.v1'
MAX_FILES = 4096
MAX_DIRECTORIES = 4096
MAX_TOTAL_BYTES = 256 * 1024 * 1024
MAX_REPORT_BYTES = 16 * 1024 * 1024
BOUNDARY = ('Private filenames: do not publish this inventory. Raw byte hashes are not signatures, '
            'authenticity, scientific validity, completion or approval. Keep the inventory or its hash '
            'separately; someone editing the folder can also replace its inventory. Differences describe '
            'edits, not judgments. No commands are executed or argv copied; READY/COMPLETE files are '
            'ordinary bytes. Enumeration is not selection or permission. Content bindings are not checked. '
            'Filesystem checks detect some races, not all hostile concurrent changes.')
FLAGS = dict(llm_used=False, commands_executed=False, content_bindings_verified='NOT_PERFORMED')


def relative(value):
    if (not isinstance(value, str) or not value or len(value) > 1024 or '\\' in value or ':' in value
            or any(unicodedata.category(c) in ('Cc', 'Cf', 'Cs', 'Zl', 'Zp') for c in value)):
        raise ValueError('path must be bounded portable relative text without controls')
    path = PurePosixPath(value)
    if path.is_absolute() or '..' in path.parts or str(path) != value or not path.parts:
        raise ValueError('path must be canonical and relative')
    if any(p in ('.git', '__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache') for p in path.parts) or path.suffix in ('.pyc', '.pyo'):
        raise ValueError('repository/cache entries are not allowed; nothing is silently excluded')
    return value


def root_path(root):
    root, info = _checked_path(root)
    if not stat.S_ISDIR(info.st_mode):
        raise ValueError('root must be a plain directory')
    return root


def paths(root):
    result = []
    # An explicit stack avoids recursive Python calls on deep directory trees.
    pending = [root]
    directories = 1
    while pending:
        directory = pending.pop()
        _plain_components(directory)
        with os.scandir(directory) as entries:
            for entry in entries:
                path = Path(entry.path)
                name = relative(path.relative_to(root).as_posix())
                info = _plain_components(path)
                if stat.S_ISDIR(info.st_mode):
                    directories += 1
                    if directories > MAX_DIRECTORIES:
                        raise ValueError('folder exceeds directory count limit')
                    pending.append(path)
                elif stat.S_ISREG(info.st_mode):
                    result.append((name, path))
                    if len(result) > MAX_FILES:
                        raise ValueError('folder exceeds file count limit')
                else:
                    raise ValueError('folder contains a non-regular entry: ' + name)
    return sorted(result)


def scan(root):
    root = root_path(root)
    selected = paths(root)
    rows = []
    remaining = MAX_TOTAL_BYTES
    for name, path in selected:
        _plain_components(path)
        raw = read_source_bytes(path, max_bytes=remaining)
        remaining -= len(raw)
        rows.append(dict(path=name, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()))
    if selected != paths(root):
        raise ValueError('folder inventory changed during reading')
    return rows


def encoded(value):
    raw = (json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf-8')
    if len(raw) > MAX_REPORT_BYTES:
        raise ValueError('inventory/report exceeds 16 MiB')
    return raw


def declare(root):
    result = dict(schema=SCHEMA, status='DECLARED_INVENTORY_NOT_APPROVAL',
                  input_root='EXPLICIT_CURRENT_ARGUMENT_NOT_PERSISTED', files=scan(root),
                  boundary=BOUNDARY, **FLAGS)
    encoded(result)
    return result


def validate(value):
    expected = {'schema', 'status', 'input_root', 'files', 'boundary', *FLAGS}
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError('inventory has missing or unsupported fields')
    if (value['schema'] != SCHEMA or value['status'] != 'DECLARED_INVENTORY_NOT_APPROVAL'
            or value['input_root'] != 'EXPLICIT_CURRENT_ARGUMENT_NOT_PERSISTED'
            or value['boundary'] != BOUNDARY or any(type(value[k]) is not type(v) or value[k] != v for k, v in FLAGS.items())):
        raise ValueError('inventory metadata does not match the declared schema')
    rows = value['files']
    if not isinstance(rows, list) or len(rows) > MAX_FILES:
        raise ValueError('inventory files must be a bounded list')
    names = []
    total = 0
    for row in rows:
        if not isinstance(row, dict) or set(row) != {'path', 'bytes', 'sha256'}:
            raise ValueError('inventory row requires path, bytes and sha256')
        names.append(relative(row['path']))
        if type(row['bytes']) is not int or not 0 <= row['bytes'] <= MAX_TOTAL_BYTES:
            raise ValueError('invalid inventory byte size')
        total += row['bytes']
        h = row['sha256']
        if not isinstance(h, str) or len(h) != 64 or any(c not in '0123456789abcdef' for c in h):
            raise ValueError('invalid SHA-256')
    if names != sorted(set(names)) or total > MAX_TOTAL_BYTES:
        raise ValueError('inventory must have distinct sorted paths within total byte limit')
    encoded(value)
    return value


def verify(inventory, root):
    inventory = validate(inventory)
    current = {r['path']: r for r in scan(root)}
    previous = {r['path']: r for r in inventory['files']}
    missing = sorted(previous.keys() - current.keys())
    unlisted = sorted(current.keys() - previous.keys())
    changed = sorted(p for p in previous.keys() & current.keys() if previous[p] != current[p])
    errors = ([p + ': missing' for p in missing] + [p + ': size/hash mismatch' for p in changed]
              + [p + ': unlisted file' for p in unlisted])
    result = dict(schema='persona.folder-inventory-verification.v1', valid=not errors, errors=errors,
                  missing=missing, unlisted=unlisted, changed=changed,
                  status='DECLARED_INVENTORY_MATCH_NOT_APPROVAL' if not errors else 'DECLARED_INVENTORY_MISMATCH_NOT_APPROVAL',
                  boundary=BOUNDARY, **FLAGS)
    encoded(result)
    return result


def output_path(destination, root):
    # Check unresolved ancestors too: resolve() alone would conceal junctions.
    requested = Path(destination).absolute()
    _plain_components(requested.parent)
    target = exclusive_output.check_path(requested)
    if target == root or root in target.parents:
        raise ValueError('write inventory/report outside the inventoried folder')
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('declare', help='Declare raw bytes; no approval')
    p.add_argument('root', type=Path)
    p.add_argument('--output', type=Path, required=True, metavar='NEW_FILE')
    p = sub.add_parser('verify', help='Compare declared bytes with a current folder')
    p.add_argument('manifest', type=Path)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--format', choices=('json', 'text'), default='json')
    exclusive_output.add_output_argument(p)
    args = parser.parse_args()
    try:
        root = root_path(args.root)
        if args.output is not None:
            output_path(args.output, root)
        if args.command == 'declare':
            result = declare(root)
        else:
            manifest, info = _checked_path(args.manifest)
            if not stat.S_ISREG(info.st_mode):
                raise ValueError('inventory must be a regular file')
            result = verify(loads(read_source_bytes(manifest, max_bytes=MAX_REPORT_BYTES)), root)
        raw = encoded(result)
        if args.command == 'verify' and args.format == 'text':
            raw = ('\n'.join([result['status'], *[display(e) for e in result['errors']], BOUNDARY]) + '\n').encode('utf-8')
            if len(raw) > MAX_REPORT_BYTES:
                raise ValueError('report exceeds 16 MiB')
        if args.output is not None:
            output_path(args.output, root)
    except (ValueError, OSError, RuntimeError, TypeError, RecursionError) as exc:
        parser.exit(1, str(exc) + '\n')
    exclusive_output.emit(parser, raw, args.output)
    if args.command == 'verify' and not result['valid']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
