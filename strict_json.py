"""Reject ambiguous keys and non-finite numbers at JSON input boundaries."""
import json
import math
from pathlib import Path

MAX_CONTAINER_DEPTH = 128


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON object key: ' + key)
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


def load(path):
    return loads(Path(path).read_bytes())
