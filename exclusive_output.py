"""Exclusive local CLI output; no overwrite, publication, or scientific validation."""
import hashlib
import json
import sys
from pathlib import Path

from persona import payload_sha256
from strict_json import loads

ROOT = Path(__file__).resolve().parent
MAX_OUTPUT_BYTES = 16 * 1024 * 1024
MAX_RECEIPT_BYTES = 64 * 1024
BOUNDARY = ('Private local output, not permission to share. Hashes identify bytes or JSON values, '
            'not authenticity, scientific validity or human approval. No model or network call, '
            'canonical update or overwrite. A failed write may leave a partial file; it is never removed.')


def add_output_argument(parser):
    parser.add_argument('--output', type=Path, metavar='NEW_FILE',
                        help='Save exact result bytes to a new file outside the repository; print a receipt')


def check_path(destination):
    requested = Path(destination).absolute()
    if any(p.is_symlink() for p in (requested, *requested.parents)):
        raise ValueError('output path must not contain symlinks')
    target = requested.resolve()
    if target == ROOT or ROOT in target.parents:
        raise ValueError('write output outside the repository')
    if target.exists():
        raise ValueError('output already exists; no files are overwritten')
    if not target.parent.is_dir():
        raise ValueError('output parent must already exist')
    return target


def preflight(parser, destination):
    """Validate an explicit destination before a command reads any input."""
    if destination is not None:
        try:
            check_path(destination)
        except (ValueError, OSError, RuntimeError) as exc:
            parser.exit(1, str(exc) + '\n')


def write_exclusive(raw, destination):
    """Recheck before exclusive binary creation; leave partial output on write failure."""
    if len(raw) > MAX_OUTPUT_BYTES:
        raise ValueError('saved output exceeds 16 MiB')
    target = check_path(destination)
    with target.open('xb') as stream:
        written = stream.write(raw)
        if written != len(raw):
            raise OSError('incomplete output write; partial file retained')
    return target


def emit(parser, raw, destination=None):
    """Without a destination preserve existing stdout bytes and bounds exactly."""
    if destination is None:
        sys.stdout.buffer.write(raw)
        return
    try:
        if len(raw) > MAX_OUTPUT_BYTES:
            raise ValueError('saved output exceeds 16 MiB')
        target = check_path(destination)
        logical = None
        try:
            logical = payload_sha256(loads(raw))
        except (ValueError, TypeError, RecursionError, UnicodeError):
            pass  # Text and HTML have a raw byte hash, not a JSON payload hash.
        receipt = dict(schema='persona.saved-output.v1', status='SAVED', path=str(target),
                       bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
                       payload_sha256=logical, boundary=BOUNDARY)
        encoded = (json.dumps(receipt, ensure_ascii=True, indent=2) + '\n').encode('utf-8')
        if len(encoded) > MAX_RECEIPT_BYTES:
            raise ValueError('saved-output receipt exceeds 64 KiB')
        write_exclusive(raw, destination)
    except (ValueError, OSError, RuntimeError) as exc:
        parser.exit(1, str(exc) + '\n')
    sys.stdout.buffer.write(encoded)
