"""Replay an explicitly supplied linear chain of mock-review revisions."""
import argparse
import copy
import json
from pathlib import Path

from audit_design_lineage import audit as audit_one, require_mock_only_history
from compare_releases import checked_package
from extraction_adapter import validate_candidate_bundle
from operator_review import prepare_revision
from persona import payload_sha256
from strict_json import load

STAGE_KEYS = {'original_corpus', 'candidate_bundle', 'operator_review', 'target_version', 'target_build_id'}


def _mock_records(package):
    for paper in package['knowledge']['papers']:
        for index, observation in enumerate(paper['observations']):
            for dimension, component in observation.get('reasoning', {}).items():
                if component.get('origin') == 'operator_reviewed_mock_candidate':
                    yield (paper['paper_id'], index, dimension), component


def audit(value, links, proposal, chain):
    package = checked_package(value)
    require_mock_only_history(package)
    if not isinstance(chain, dict) or set(chain) != {'stages'} or not isinstance(chain['stages'], list) or not chain['stages']:
        raise ValueError('chain must contain a nonempty ordered stages array')
    previous, initial, summaries, proofs, identities = None, [], [], {}, set()
    for number, stage in enumerate(chain['stages'], 1):
        if not isinstance(stage, dict) or set(stage) != STAGE_KEYS:
            raise ValueError('stage has missing or unknown fields')
        corpus, candidates, declared = stage['original_corpus'], stage['candidate_bundle'], stage['operator_review']
        base = validate_candidate_bundle(corpus, candidates)
        require_mock_only_history(base, candidates)
        if previous is not None and payload_sha256(base) != payload_sha256(previous):
            raise ValueError('stage ' + str(number) + ' preflight package does not continue the previous replay')
        if previous is None:
            identity = base['persona']
            identities.add((identity['author_id'], identity['version'], identity['build_id']))
            initial = [(key, payload_sha256(component)) for key, component in _mock_records(base)]
        replay = prepare_revision(corpus, candidates, declared, stage['target_version'], stage['target_build_id'])
        if replay.get('status') != 'REVIEWED_REVISION_CANDIDATE' or 'package' not in replay:
            raise ValueError('stage ' + str(number) + ' does not produce a reviewed revision')
        current = replay['package']
        identity = current['persona']; identity = (identity['author_id'], identity['version'], identity['build_id'])
        if identity in identities:
            raise ValueError('chain cannot reuse a prior package identity')
        identities.add(identity)
        positions = [(paper['paper_id'], index) for paper in corpus['papers'] for index, _ in enumerate(paper['observations'])]
        targets = {rule['rule_id']: position for rule, position in zip(base['persona']['rules'], positions)}
        dimensions = {candidate['candidate_id']: candidate['dimension'] for candidate in candidates['candidates']}
        accepted = {(*targets[decision['target_rule_id']], dimensions[decision['candidate_id']]): decision['candidate_id']
                    for decision in declared['decisions'] if decision['decision'] == 'accept'}
        bundle_hash, review_hash = payload_sha256(candidates), payload_sha256(declared)
        for key, component in _mock_records(current):
            if (accepted.get(key) == component['candidate_id'] and component['candidate_bundle_sha256'] == bundle_hash
                    and component['operator_review_sha256'] == review_hash):
                proofs[(*key, payload_sha256(component))] = number
        summaries.append(dict(stage_index=number, original_corpus_sha256=payload_sha256(corpus),
            input_package_sha256=payload_sha256(base), output_package_sha256=payload_sha256(current),
            candidate_bundle_sha256=bundle_hash, operator_review_sha256=review_hash,
            target_version=stage['target_version'], target_build_id=stage['target_build_id']))
        previous = current
    if payload_sha256(previous) != payload_sha256(package):
        raise ValueError('final declared stage does not exactly match the supplied package')
    last = chain['stages'][-1]
    one = audit_one(package, links, proposal, {key: last[key] for key in
                    ('original_corpus', 'candidate_bundle', 'operator_review')})
    final_records, final_status, final_keys = [], {}, set()
    for key, component in _mock_records(package):
        exact = (*key, payload_sha256(component)); final_keys.add(exact)
        stage_index = proofs.get(exact)
        status = 'REPLAYED_DECLARED_STAGE' if stage_index is not None else 'OUTSIDE_DECLARED_CHAIN'
        final_status[key] = (status, stage_index)
        final_records.append(dict(paper_id=key[0], observation_index=key[1], dimension=key[2],
            component_sha256=exact[-1], candidate_id=component['candidate_id'],
            candidate_bundle_sha256=component['candidate_bundle_sha256'], operator_review_sha256=component['operator_review_sha256'],
            proposed_claim_type=component['proposed_claim_type'], reviewed_claim_type=component['claim_type'],
            audit_status=status, replay_stage_index=stage_index))
    initial_records = [dict(paper_id=key[0], observation_index=key[1], dimension=key[2],
        component_sha256=digest, retained_exactly_in_final=(*key, digest) in final_keys,
        audit_status='INITIAL_HISTORY_NOT_REPLAYED') for key, digest in initial]
    routes = copy.deepcopy(one['step_evidence_routes'])
    for step in routes:
        for use in step['uses']:
            for endpoint in use['endpoints']:
                ref = endpoint['reference']; key = (ref['paper_id'], ref['observation_index'], ref['dimension'])
                if key in final_status:
                    endpoint['mock_origin_audit'], endpoint['replay_stage_index'] = final_status[key]
    uncovered = sum(row['audit_status'] == 'OUTSIDE_DECLARED_CHAIN' for row in final_records)
    return dict(status='DECLARED_CHAIN_MATCH_WITH_UNREPLAYED_HISTORY' if initial or uncovered else 'DECLARED_CHAIN_REPLAY_MATCH',
        audit_scope='DECLARED_CONSECUTIVE_MOCK_REVIEW_REVISIONS', chain_sha256=payload_sha256(chain),
        final_package_sha256=payload_sha256(package), proposal_sha256=one['proposal_sha256'],
        link_artifact_sha256=one['link_artifact_sha256'], question=one['question'], stages=summaries,
        final_mock_origin_coverage='FINAL_MARKERS_OUTSIDE_DECLARED_CHAIN' if uncovered else 'ALL_FINAL_MARKERS_COVERED_BY_DECLARED_STAGES',
        final_mock_origins=final_records, initial_unreplayed_origins=initial_records,
        initial_history_status='UNREPLAYED_MOCK_ORIGINS_PRESENT' if initial else 'NO_MOCK_ORIGIN_MARKERS_IN_INITIAL_CORPUS',
        step_evidence_routes=routes, unreferenced_link_ids=one['unreferenced_link_ids'],
        semantic_validation='NOT_PERFORMED', operator_identity='RECORDED_NOT_AUTHENTICATED',
        provider_invoked=False, llm_used=False, canonical_update_performed=False,
        boundary='Mechanical replay of the declared linear chain only, not complete historical lineage '
                 'or source authenticity. Continuity compares projected packages, not byte-identical raw '
                 'corpora; ignored metadata can differ. Every stage must continue the previous output '
                 'without unrecorded runtime edits or new sources. Candidate IDs are scoped to their '
                 'stage, hashes, target and component content. Initial inherited mock history remains '
                 'unaudited even when its records are later replaced. Final component coverage is a '
                 'separate result, not proof of full history, author ownership, scientific validity or '
                 'authenticated human review. No automatic rebasing, semantic inference or provider call occurs.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('package', 'links', 'proposal', 'chain'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    try:
        result = audit(load(args.package), load(args.links), load(args.proposal), load(args.chain))
    except (ValueError, OSError, KeyError, TypeError, AttributeError) as exc:
        parser.exit(1, str(exc) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
