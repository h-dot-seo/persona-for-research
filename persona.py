#!/usr/bin/env python3
"""Validate mechanical persona release boundaries; never score scholarly fidelity."""
import argparse
import hashlib
import json
from pathlib import Path
from strict_json import load


def payload_sha256(value):
    """Logical JSON hash: UTF-8, sorted keys, compact separators, no excluded keys."""
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def validate(persona, knowledge):
    errors = []
    if not isinstance(persona, dict) or not isinstance(knowledge, dict):
        return ['persona and knowledge must be objects']
    identity = persona.get('identity', {})
    if not isinstance(identity, dict):
        return ['identity must be an object']
    if identity.get('simulation_only') is not True:
        errors.append('simulation_only must be true')
    if identity.get('private_beliefs_inferred') is not False:
        errors.append('private_beliefs_inferred must be false')
    for key in ('author_id', 'version', 'build_id'):
        if not isinstance(persona.get(key), str) or not persona[key]:
            errors.append('missing persona ' + key)
        if knowledge.get(key) != persona.get(key):
            errors.append('binding mismatch: ' + key)
    if knowledge.get('persona_payload_sha256') != payload_sha256(persona):
        errors.append('persona logical payload hash mismatch')
    papers = knowledge.get('papers')
    if not isinstance(papers, list):
        errors.append('papers must be an array')
        papers = []
    if 'knowledge_papers_sha256' in persona and persona['knowledge_papers_sha256'] != payload_sha256(papers):
        errors.append('knowledge papers payload hash mismatch')
    seen = set()
    for row in papers:
        if not isinstance(row, dict):
            errors.append('paper must be an object'); continue
        paper_id = row.get('paper_id')
        if not isinstance(paper_id, str) or not paper_id or paper_id in seen:
            errors.append('missing or duplicate paper_id')
        else:
            seen.add(paper_id)
        if row.get('author_id') != persona.get('author_id'):
            errors.append('cross-author runtime record')
        if row.get('authorized') is not True:
            errors.append('runtime paper authorization required')
        if row.get('split') != 'training' or row.get('runtime_knowledge_eligible') is not True:
            errors.append('ineligible runtime paper')
        digest = row.get('source_sha256', '')
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
            errors.append('invalid source_sha256')
        if not row.get('locator'):
            errors.append('source locator missing')
    return errors


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('persona', type=Path); p.add_argument('knowledge', type=Path)
    args = p.parse_args()
    try:
        errors = validate(load(args.persona), load(args.knowledge))
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        errors = [str(exc)]
    print(json.dumps({'mechanically_valid': not errors, 'errors': errors,
                      'semantic_validation': 'NOT_PERFORMED'}, ensure_ascii=False))
    return int(bool(errors))


if __name__ == '__main__':
    raise SystemExit(main())
