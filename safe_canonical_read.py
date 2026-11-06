#!/usr/bin/env python3
"""Project canonical JSON into runtime context without holdout identifiers.

Read raw JSON from stdin or a file; never mutate canonical input.
This helper checks only structured boundaries, not scientific validation.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

HOLDOUT = re.compile(r'(^|[^a-z])(blind|holdout)([^a-z]|$)', re.I)
IDENTIFIER = re.compile(r'(paper|source|file|path|locator|title|pmid|doi|rank|identif|bibliograph|excerpt|abstract|full.?text|content|semantic|supporting|training|(^|_)(id|ids)($|_))', re.I)
STATISTIC = re.compile(r'(count|score|reasoning|judgment|overall|threshold|rate|percent|status|flag|policy|access|reused|included|excluded|result|performed|allowed|deny|validation|safety)', re.I)
SPLIT_KEYS = ('split', 'corpus_split', 'persona_core_split', 'dataset_split', 'stage')
REMOVE = object()


def sanitize(document):
    redactions = [0]

    def visit(value, key='', blind=False):
        in_blind = blind or bool(HOLDOUT.search(key))
        # Explicit statistics/flags are safe, even when their key says blind.
        statistic = bool(STATISTIC.search(key))
        identifier = bool(IDENTIFIER.search(key))
        if isinstance(value, dict):
            # Identifier-keyed mappings can expose identifiers in their keys.
            if in_blind and identifier:
                redactions[0] += 1
                return REMOVE
            record_blind = in_blind or any(
                isinstance(value.get(k), str) and HOLDOUT.search(value[k])
                for k in SPLIT_KEYS
            )
            output = {}
            for child_key, child in value.items():
                clean = visit(child, child_key, record_blind)
                if clean is not REMOVE:
                    output[child_key] = clean
            return output
        if isinstance(value, list):
            # Paper/source lists and blind-rank arrays reveal holdout identity.
            if in_blind and (identifier or not statistic):
                redactions[0] += 1
                return REMOVE
            output = []
            for child in value:
                clean = visit(child, key, in_blind)
                if clean is not REMOVE:
                    output.append(clean)
            return output
        if isinstance(value, str) and re.search(r'(^|[/\\])(blind|holdout)([/\\]|$)', value, re.I):
            redactions[0] += 1
            return REMOVE
        if in_blind and isinstance(value, str):
            # A field name such as "status" or "score" does not make an
            # arbitrary string safe: it can still contain a source identifier.
            safe_values = ('DENY', 'ALLOW', 'PASS', 'FAIL', 'BLOCKED',
                           'NOT_PERFORMED', 'TRAINING_ONLY')
            safe_splits = ('blind', 'holdout')
            if value.upper() not in safe_values and not (key in SPLIT_KEYS and value.lower() in safe_splits):
                redactions[0] += 1
                return REMOVE
        if in_blind and identifier and not statistic:
            redactions[0] += 1
            return REMOVE
        return value

    clean = visit(document)
    return {'canonical': clean, 'redacted_fields': redactions[0],
            'projection': 'RUNTIME_SANITIZED_CANONICAL',
            'original_hash_verification': 'NOT_PERFORMED'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', nargs='?', default='-')
    parser.add_argument('--source-kind', choices=['library-read', 'original-bytes'], default='library-read')
    parser.add_argument('--expected-original-sha256')
    args = parser.parse_args()
    if args.expected_original_sha256 and args.source_kind != 'original-bytes':
        parser.error('Original-byte hash verification requires original-bytes input, never reconstructed Library text.')
    try:
        from strict_json import loads
        raw = sys.stdin.buffer.read() if args.input == '-' else Path(args.input).read_bytes()
        result = sanitize(loads(raw))
    except (ValueError, OSError, TypeError, RecursionError) as exc:
        parser.exit(1, str(exc) + '\n')
    if args.source_kind == 'original-bytes':
        actual = hashlib.sha256(raw).hexdigest()
        result['original_sha256'] = actual
        if args.expected_original_sha256:
            if actual != args.expected_original_sha256:
                print(json.dumps({'error': 'ORIGINAL_HASH_MISMATCH', 'projection_emitted': False}))
                return 2
            result['original_hash_verification'] = 'VERIFIED'
        else:
            result['original_hash_verification'] = 'COMPUTED_NO_EXPECTED_BINDING'
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
