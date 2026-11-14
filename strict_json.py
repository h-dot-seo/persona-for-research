"""Reject ambiguous keys and non-finite numbers at JSON input boundaries."""
import json
import math
from pathlib import Path

MAX_INPUT_BYTES = 8 * 1024 * 1024
MAX_CONTAINER_DEPTH = 128
MAX_DIAGNOSTIC_KEY_CODEPOINTS = 128


def _key_diagnostic(key):
    """Bound only the display, preserving exact keys for parsing and comparison."""
    preview = json.dumps(key[:MAX_DIAGNOSTIC_KEY_CODEPOINTS], ensure_ascii=True)
    if len(key) > MAX_DIAGNOSTIC_KEY_CODEPOINTS:
        preview += ' [truncated; first 128 Unicode codepoints shown]'
    return preview


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON object key: ' + _key_diagnostic(key))
        result[key] = value
    return result


def _constant(value):
    raise ValueError('non-finite JSON number is not allowed')


def _float(value):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError('JSON number exceeds finite range')
    return result


def loads(raw):
    try:
        result = json.loads(raw, object_pairs_hook=_object, parse_constant=_constant,
                            parse_float=_float)
    except RecursionError as exc:
        raise ValueError('JSON nesting exceeds supported depth') from exc
    pending = [(result, 0)]
    while pending:
        value, depth = pending.pop()
        if isinstance(value, (dict, list)):
            if depth >= MAX_CONTAINER_DEPTH:
                raise ValueError('JSON nesting exceeds supported depth')
            children = value.values() if isinstance(value, dict) else value
            pending.extend((child, depth + 1) for child in children)
    return result


class InputLimitError(ValueError):
    """A bounded reader observed at least one byte beyond its budget."""


def read_bounded_stream(stream, max_bytes, *, label='<stream>'):
    """Read at most limit+1 bytes from a binary stream; never close caller streams.

    This is a byte bound, not a time bound or a regular-file/symlink policy.
    Short reads are accumulated until EOF or the budget is exceeded.
    """
    if type(max_bytes) is not int or max_bytes < 0:
        raise ValueError('max_bytes must be a non-negative integer')
    buffer = bytearray()
    total = 0
    while total <= max_bytes:
        raw = stream.read(max_bytes + 1 - total)
        if not isinstance(raw, bytes):
            raise TypeError('bounded input must be a binary stream')
        if not raw:
            return bytes(buffer)
        total += len(raw)
        if total > max_bytes:
            raise InputLimitError('JSON input exceeds byte budget (default 8 MiB): '
                                  + _key_diagnostic(label))
        buffer.extend(raw)
    raise AssertionError('unreachable input budget state')


def read_bounded(path, max_bytes):
    """Return original bytes, bounding reads without changing path semantics."""
    with Path(path).open('rb') as stream:
        return read_bounded_stream(stream, max_bytes, label=Path(path).name)


def load(path, *, max_bytes=None):
    """Parse one file; None uses the current module's 8 MiB default."""
    limit = MAX_INPUT_BYTES if max_bytes is None else max_bytes
    return loads(read_bounded(path, limit))
