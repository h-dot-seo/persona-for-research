"""Replay one declared mock-review revision and trace a design's evidence routes."""
import argparse
import json
from pathlib import Path

from compare_releases import checked_package
from design_scenario import OPTIONAL_FIELDS, review as review_design
from extraction_adapter import validate_candidate_bundle
from operator_review import prepare_revision
from persona import payload_sha256
from strict_json import load


def audit(value, links, proposal, revision_inputs):
    if not isinstance(revision_inputs, dict) or set(revision_inputs) != {'original_corpus', 'candidate_bundle', 'operator_review'}:
        raise ValueError('revision inputs require exactly original_corpus, candidate_bundle and operator_review')
    package = checked_package(value)
    design = review_design(package, links, proposal)
    corpus = revision_inputs['original_corpus']
    candidates = revision_inputs['candidate_bundle']
    declared_review = revision_inputs['operator_review']
    base = validate_candidate_bundle(corpus, candidates)  # Pure validation; no provider invocation.
    replay = prepare_revision(corpus, candidates, declared_review,
                              package['persona']['version'], package['persona']['build_id'])
    if replay.get('status') != 'REVIEWED_REVISION_CANDIDATE' or 'package' not in replay:
        raise ValueError('declared review does not produce a reviewed revision candidate')
    if payload_sha256(replay['package']) != payload_sha256(package):
        raise ValueError('replayed revision does not exactly match the final package')

    positions = [(paper['paper_id'], index) for paper in corpus['papers']
                 for index, _ in enumerate(paper['observations'])]
    targets = {rule['rule_id']: position for rule, position in zip(base['persona']['rules'], positions)}
    dimensions = {row['candidate_id']: row['dimension'] for row in candidates['candidates']}
    replaced = {(*targets[decision['target_rule_id']], dimensions[decision['candidate_id']])
                for decision in declared_review['decisions'] if decision['decision'] == 'accept'}
    origin_records, origins = [], {}
    for paper in package['knowledge']['papers']:
        for index, observation in enumerate(paper['observations']):
            for dimension, component in observation.get('reasoning', {}).items():
                if component.get('origin') != 'operator_reviewed_mock_candidate':
                    continue
                key = (paper['paper_id'], index, dimension)
                covered = (key in replaced and component['operator_review_sha256'] == payload_sha256(declared_review)
                           and component['candidate_bundle_sha256'] == payload_sha256(candidates)
                           and component['candidate_id'] in replay['applied_candidate_ids'])
                row = dict(paper_id=key[0], observation_index=index, dimension=dimension,
                    candidate_id=component['candidate_id'],
                    candidate_bundle_sha256=component['candidate_bundle_sha256'],
                    operator_review_sha256=component['operator_review_sha256'],
                    proposed_claim_type=component['proposed_claim_type'], reviewed_claim_type=component['claim_type'],
                    audit_status='REPLAYED_CURRENT_REVISION' if covered else 'INHERITED_ORIGIN_NOT_REPLAYED')
                origin_records.append(row); origins[key] = row['audit_status']

    link_map = {link['link_id']: link for link in design['evidence_links']['links']}
    routes = []
    for step in design['steps']:
        uses = []
        for use in step['link_uses']:
            link = link_map[use['link_id']]
            endpoints = []
            for role in ('from', 'to'):
                node = link[role + '_evidence']; ref = node['reference']; component = node['component']
                key = (ref['paper_id'], ref['observation_index'], ref['dimension'])
                endpoints.append(dict(role=role, reference=dict(ref), source_kind=node['source_kind'],
                    publication_year=node['publication_year'], source_sha256=node['source_sha256'],
                    source_locator=node['source_locator'], observation_locator=node['observation']['locator'],
                    selected_record_locator=component['locator'] if component is not None else node['observation']['locator'],
                    observation_stance=node['observation']['stance'],
                    observation_method_sha256=payload_sha256(node['observation']['method']),
                    observation_condition_sha256=payload_sha256(node['observation']['condition']),
                    observation_limitation_sha256=payload_sha256(node['observation']['limitation']),
                    observation_claim_type=node['observation']['claim_type'],
                    selected_component_claim_type=component['claim_type'] if component is not None else None,
                    selected_record_sha256=payload_sha256(component if component is not None else node['observation']),
                    mock_origin_audit=origins.get(key, 'NO_MOCK_ORIGIN_ON_SELECTED_RECORD')))
            uses.append(dict(link_id=use['link_id'], proposed_use_role=use['role'],
                applicability_note_sha256=payload_sha256(use['applicability_note']),
                source_relation=link['relation'], relation_claim_type=link['claim_type'], endpoints=endpoints))
        routes.append(dict(step_id=step['step_id'], claim_type='operator_proposal',
            proposed_action_sha256=payload_sha256(step['proposed_action']),
            operator_field_status={field: 'NOT_SUPPLIED' if step[field] is None else 'SUPPLIED_NOT_VALIDATED'
                                   for field in OPTIONAL_FIELDS},
            evidence_status=step['evidence_status'], uses=uses))
    inherited = sum(row['audit_status'] == 'INHERITED_ORIGIN_NOT_REPLAYED' for row in origin_records)
    return dict(status='CURRENT_REVISION_MATCH_WITH_INHERITED_ORIGINS' if inherited else 'CURRENT_REVISION_REPLAY_MATCH',
        audit_scope='ONE_DECLARED_MOCK_REVIEW_REVISION', replayed_package_sha256=payload_sha256(replay['package']),
        original_corpus_sha256=payload_sha256(corpus), candidate_bundle_sha256=payload_sha256(candidates),
        operator_review_sha256=payload_sha256(declared_review), proposal_sha256=design['proposal_sha256'],
        link_artifact_sha256=design['link_artifact_sha256'],
        question=design['question'], mock_origin_components=origin_records,
        inherited_origin_count=inherited, step_evidence_routes=routes,
        unreferenced_link_ids=list(design['unreferenced_link_ids']),
        semantic_validation='NOT_PERFORMED', operator_identity='RECORDED_NOT_AUTHENTICATED',
        llm_used=False, provider_invoked=False, canonical_update_performed=False,
        boundary='Exact mechanical replay of one declared revision only, not complete historical lineage, '
                 'source authenticity, authenticated human review or researcher fidelity. Inherited mock '
                 'origins are not replayed. Source quotes are checked against supplied segments, not '
                 'independently obtained publications or source-file bytes. No semantic applicability, '
                 'claim ownership, hypothesis validity or experiment quality is established. Selected-record '
                 'routes identify explicit references only; nearby reasoning components are not inferred as '
                 'used. Missing proposal fields stay missing. No raw source sections or candidate text are '
                 'included in this audit; retain the separately bound original artifacts.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('package', 'links', 'proposal', 'revision_inputs'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    try:
        result = audit(load(args.package), load(args.links), load(args.proposal), load(args.revision_inputs))
    except (ValueError, OSError, KeyError, TypeError, AttributeError) as exc:
        parser.exit(1, str(exc) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
