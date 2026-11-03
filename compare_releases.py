"""Read-only comparison of bound evidence packages; never update canonical policy."""
import argparse
import json
from pathlib import Path
from persona import payload_sha256, validate
from strict_json import load


def checked_package(value):
    if not isinstance(value, dict):
        raise ValueError('release must be an object')
    package = value.get('package', value)
    if not isinstance(package, dict) or not isinstance(package.get('persona'), dict):
        raise ValueError('release needs a persona and knowledge package')
    persona, knowledge = package['persona'], package.get('knowledge')
    errors = validate(persona, knowledge)
    if errors:
        raise ValueError('; '.join(errors))
    if 'knowledge_papers_sha256' not in persona:
        raise ValueError('release comparison requires bound knowledge; rebuild legacy packages')
    return package


def compare(previous, candidate):
    previous, candidate = checked_package(previous), checked_package(candidate)
    old, new = previous['persona'], candidate['persona']
    if old['author_id'] != new['author_id']:
        raise ValueError('release comparison requires the same scholarly identity')
    before = {p['paper_id']: p for p in previous['knowledge']['papers']}
    after = {p['paper_id']: p for p in candidate['knowledge']['papers']}
    added = sorted(after.keys() - before.keys())
    removed = sorted(before.keys() - after.keys())
    modified = []
    for paper_id in sorted(before.keys() & after.keys()):
        a, b = before[paper_id], after[paper_id]
        if payload_sha256(a) == payload_sha256(b):
            continue
        fields = sorted(k for k in a.keys() | b.keys()
                        if k not in a or k not in b or payload_sha256(a[k]) != payload_sha256(b[k]))
        modified.append(dict(paper_id=paper_id, changed_fields=fields,
            previous_source_sha256=a['source_sha256'], candidate_source_sha256=b['source_sha256'],
            source_hash_changed=a['source_sha256'] != b['source_sha256'],
            observations_changed=payload_sha256(a.get('observations')) != payload_sha256(b.get('observations')),
            previous_locator=a['locator'], candidate_locator=b['locator']))
    evidence_changed = bool(added or removed or modified)
    rules_changed = payload_sha256(old.get('rules')) != payload_sha256(new.get('rules'))
    return dict(author_id=old['author_id'],
        previous=dict(version=old['version'], build_id=old['build_id'], persona_sha256=payload_sha256(old)),
        candidate=dict(version=new['version'], build_id=new['build_id'], persona_sha256=payload_sha256(new)),
        added_paper_ids=added, removed_paper_ids=removed, modified_papers=modified,
        evidence_changed=evidence_changed, rule_payload_changed=rules_changed,
        status='REVIEW_REQUIRED' if evidence_changed or rules_changed else 'NO_EVIDENCE_OR_RULE_CHANGE',
        canonical_update_performed=False, semantic_validation='NOT_PERFORMED',
        boundary='Structural changes only; no inferred change of mind, correction, retraction, '
                 'or semantic equivalence. Paper IDs must be curated consistently. This report '
                 'does not approve a release or replace either canonical package.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('previous', type=Path)
    parser.add_argument('candidate', type=Path)
    args = parser.parse_args()
    try:
        result = compare(load(args.previous), load(args.candidate))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(1, str(exc) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
