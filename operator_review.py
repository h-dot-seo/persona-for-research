"""Apply declared operator decisions to a separate, hash-bound revision candidate."""
import argparse
import copy
import json
from pathlib import Path

from extraction_adapter import MAX_CANDIDATE_CHARS, MAX_HANDOFF_BYTES, validate_candidate_bundle
from corpus_files import load_segment_corpus
from observation_input import verified_corpus
from persona import payload_sha256
from research_workflow import build
from strict_json import load

REVIEW_KEYS = {'candidate_bundle_sha256', 'input_corpus_sha256', 'reviewer_id', 'decisions'}
BASIC_DECISION_KEYS = {'candidate_id', 'decision', 'review_note'}
ACCEPT_KEYS = BASIC_DECISION_KEYS | {'target_rule_id', 'target_paper_id', 'operation',
    'expected_component_sha256', 'reviewed_text', 'reviewed_claim_type'}


def _text(value, name, maximum=MAX_CANDIDATE_CHARS):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(name + ' must be a bounded nonempty string')


def review_template(corpus, bundle, reviewer_id):
    """Prepare bindings and deferred decisions, never inferred approvals or targets."""
    validate_candidate_bundle(corpus, bundle)
    _text(reviewer_id, 'reviewer_id', 128)
    return dict(candidate_bundle_sha256=payload_sha256(bundle),
        input_corpus_sha256=payload_sha256(corpus), reviewer_id=reviewer_id,
        decisions=[dict(candidate_id=c['candidate_id'], decision='defer',
                        review_note='Pending operator review.') for c in bundle['candidates']])


def target_inventory(corpus, bundle):
    """List all same-paper targets in input order, without selection or approval."""
    base = validate_candidate_bundle(corpus, bundle)
    positions = [(pi, oi) for pi, p in enumerate(corpus['papers'])
                 for oi, _ in enumerate(p['observations'])]
    rows = []
    for candidate in bundle['candidates']:
        targets = []
        for rule, (pi, oi) in zip(base['persona']['rules'], positions):
            if rule['paper_id'] != candidate['paper_id']:
                continue
            dimension = candidate['dimension']
            raw = corpus['papers'][pi]['observations'][oi].get('reasoning', {}).get(dimension)
            targets.append(dict(target_rule_id=rule['rule_id'], target_paper_id=rule['paper_id'],
                observation={key: copy.deepcopy(rule[key]) for key in
                    ('method', 'condition', 'limitation', 'locator', 'topic', 'stance', 'claim_type',
                     'evidence_quote', 'evidence_verification', 'attribution')},
                occupancy='EMPTY' if raw is None else 'OCCUPIED',
                expected_component_sha256=None if raw is None else payload_sha256(raw),
                existing_component=copy.deepcopy(rule.get('reasoning', {}).get(dimension))))
        rows.append(dict(candidate_id=candidate['candidate_id'], paper_id=candidate['paper_id'],
            dimension=candidate['dimension'], candidate_text=candidate['candidate_text'],
            proposed_claim_type=candidate['proposed_claim_type'], locator=candidate['locator'],
            evidence_quote=candidate['evidence_quote'], targets=targets))
    return dict(status='TARGET_INVENTORY_ONLY', candidate_bundle_sha256=payload_sha256(bundle),
        input_corpus_sha256=payload_sha256(corpus), candidates=rows,
        selection_performed=False, semantic_validation='NOT_PERFORMED',
        canonical_update_performed=False,
        boundary='All same-paper observations are listed in input order, not ranked by relevance. '
                 'Source membership and quote checks do not establish semantic fit or author ownership. '
                 'No target, operation or approval is inferred. Retain explicit operator decisions; '
                 'hashes identify the full input component, not only the displayed projection.')


def prepare_revision(corpus, bundle, review, new_version, new_build_id):
    base = validate_candidate_bundle(corpus, bundle)  # No provider is called.
    if not isinstance(review, dict) or set(review) != REVIEW_KEYS:
        raise ValueError('operator review must contain only the documented fields')
    bundle_hash = payload_sha256(bundle)
    if review['candidate_bundle_sha256'] != bundle_hash or review['input_corpus_sha256'] != payload_sha256(corpus):
        raise ValueError('review is bound to a different candidate bundle or input corpus')
    _text(review['reviewer_id'], 'reviewer_id', 128)
    _text(new_version, 'new version', 128)
    _text(new_build_id, 'new build ID', 128)
    if (new_version, new_build_id) == (corpus['version'], corpus['build_id']):
        raise ValueError('revision must use a new version/build identity')
    if not isinstance(review['decisions'], list):
        raise ValueError('review decisions must be an array')
    candidates = {c['candidate_id']: c for c in bundle['candidates']}
    positions = [(pi, oi) for pi, p in enumerate(corpus['papers']) for oi, _ in enumerate(p['observations'])]
    targets = {rule['rule_id']: position for rule, position in zip(base['persona']['rules'], positions)}
    seen, occupied, changes, deferred = set(), set(), [], False
    for decision in review['decisions']:
        if not isinstance(decision, dict):
            raise ValueError('decision must be an object')
        kind = decision.get('decision')
        if kind not in ('accept', 'reject', 'defer'):
            raise ValueError('decision must be accept, reject or defer')
        if set(decision) != (ACCEPT_KEYS if kind == 'accept' else BASIC_DECISION_KEYS):
            raise ValueError('decision has missing or unknown fields')
        cid = decision['candidate_id']
        _text(cid, 'candidate_id', 128)
        _text(decision['review_note'], 'review_note')
        if cid not in candidates or cid in seen:
            raise ValueError('unknown or duplicate candidate decision')
        seen.add(cid)
        if kind != 'accept':
            deferred = deferred or kind == 'defer'
            continue
        candidate = candidates[cid]
        for field in ('target_rule_id', 'target_paper_id', 'reviewed_text'):
            _text(decision[field], field)
        if decision['target_rule_id'] not in targets:
            raise ValueError('review target rule is unknown')
        pi, oi = targets[decision['target_rule_id']]
        paper = corpus['papers'][pi]
        if paper['paper_id'] != decision['target_paper_id'] or paper['paper_id'] != candidate['paper_id']:
            raise ValueError('review target must match the candidate source paper')
        dimension = candidate['dimension']
        target = (pi, oi, dimension)
        if target in occupied:
            raise ValueError('multiple accepted candidates target the same component')
        occupied.add(target)
        existing = paper['observations'][oi].get('reasoning', {}).get(dimension)
        if decision['operation'] == 'add':
            if existing is not None or decision['expected_component_sha256'] is not None:
                raise ValueError('add requires an unoccupied dimension and null prior hash')
        elif decision['operation'] == 'replace':
            if existing is None or decision['expected_component_sha256'] != payload_sha256(existing):
                raise ValueError('replacement requires the exact prior component hash')
        else:
            raise ValueError('operation must be add or replace')
        if decision['reviewed_claim_type'] not in ('explicit_statement', 'operator_interpretation'):
            raise ValueError('reviewed claim type is unsupported')
        changes.append((target, candidate, decision))
    if seen != set(candidates):
        raise ValueError('every candidate requires an explicit decision')
    review_hash = payload_sha256(review)
    result = dict(status='REVIEW_INCOMPLETE' if deferred else
        'REVIEWED_REVISION_CANDIDATE' if changes else 'NO_ACCEPTED_CANDIDATES',
        canonical_update_performed=False, reviewer_identity='RECORDED_NOT_AUTHENTICATED',
        semantic_validation='NOT_PERFORMED', candidate_bundle_sha256=bundle_hash,
        operator_review_sha256=review_hash, review_record=copy.deepcopy(review),
        provider=copy.deepcopy(bundle['provider']), applied_candidate_ids=[],
        boundary='Operator decisions are recorded declarations, not authenticated human identity '
                 'or proof of semantic support. This creates a separate revision candidate; '
                 'no canonical package is overwritten or automatically promoted.')
    if deferred or not changes:
        return result
    # Detach JSON-equivalent containers: deepcopy preserves shared Python objects
    # and could otherwise edit an untargeted observation through an alias.
    revised = json.loads(json.dumps(corpus, ensure_ascii=False, allow_nan=False))
    revised['version'], revised['build_id'] = new_version, new_build_id
    for (pi, oi, dimension), candidate, decision in changes:
        observation = revised['papers'][pi]['observations'][oi]
        observation.setdefault('reasoning', {})[dimension] = dict(
            text=decision['reviewed_text'], claim_type=decision['reviewed_claim_type'],
            locator=candidate['locator'], evidence_quote=candidate['evidence_quote'],
            origin=('operator_reviewed_imported_candidate' if bundle['contract_version'] == '2'
                    else 'operator_reviewed_mock_candidate'), candidate_id=candidate['candidate_id'],
            candidate_bundle_sha256=bundle_hash, operator_review_sha256=review_hash,
            proposed_claim_type=candidate['proposed_claim_type'])
        result['applied_candidate_ids'].append(candidate['candidate_id'])
    result['package'] = build(verified_corpus(revised))  # Recheck quotes; project away raw sections.
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('corpus', type=Path)
    parser.add_argument('candidates', type=Path)
    parser.add_argument('review', type=Path, nargs='?')
    parser.add_argument('--new-version')
    parser.add_argument('--new-build-id')
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--template', action='store_true')
    modes.add_argument('--targets', action='store_true')
    parser.add_argument('--reviewer-id')
    parser.add_argument('--source-root', type=Path, help='Recheck a local file manifest and reconstruct its source segments')
    args = parser.parse_args()
    def input_corpus():
        corpus = load(args.corpus)
        if args.source_root is not None:
            corpus = load_segment_corpus(corpus, args.source_root, max_total_bytes=MAX_HANDOFF_BYTES)
        return corpus
    try:
        if args.targets:
            if any(value is not None for value in
                   (args.review, args.new_version, args.new_build_id, args.reviewer_id)):
                raise ValueError('target inventory mode cannot apply review decisions or record a reviewer')
            result = target_inventory(input_corpus(), load(args.candidates))
        elif args.template:
            if args.review is not None or args.new_version is not None or args.new_build_id is not None:
                raise ValueError('template mode cannot apply review decisions')
            result = review_template(input_corpus(), load(args.candidates), args.reviewer_id)
        else:
            if args.review is None or args.new_version is None or args.new_build_id is None or args.reviewer_id is not None:
                raise ValueError('application requires a review file and new version/build; reviewer identity comes from that review')
            result = prepare_revision(input_corpus(), load(args.candidates), load(args.review),
                                      args.new_version, args.new_build_id)
    except (ValueError, OSError, KeyError, TypeError, AttributeError) as exc:
        parser.exit(1, str(exc) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
