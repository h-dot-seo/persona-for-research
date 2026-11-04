"""Replay one declared candidate-review revision and trace a design's evidence routes."""
import argparse
import copy
import json
from pathlib import Path

from compare_releases import checked_package
from design_scenario import OPTIONAL_FIELDS, review as review_design
from extraction_adapter import validate_candidate_bundle
from operator_review import prepare_revision
from persona import payload_sha256
from strict_json import load
from observation_provenance import inventory as observation_origins, KEY as OBSERVATION_ORIGIN


MOCK_ORIGIN = 'operator_reviewed_mock_candidate'
IMPORTED_ORIGIN = 'operator_reviewed_imported_candidate'
CANDIDATE_ORIGINS = (MOCK_ORIGIN, IMPORTED_ORIGIN)


def candidate_records(package):
    """Yield exact recorded candidate origins; never infer origin from neighbors."""
    for paper in package['knowledge']['papers']:
        for index, observation in enumerate(paper['observations']):
            for dimension, component in observation.get('reasoning', {}).items():
                if component.get('origin') in CANDIDATE_ORIGINS:
                    yield (paper['paper_id'], index, dimension), component


def candidate_provenance(bundle):
    """Summarize a validated bundle, not authenticated execution evidence."""
    result = dict(contract_version=bundle['contract_version'],
        origin=IMPORTED_ORIGIN if bundle['contract_version'] == '2' else MOCK_ORIGIN,
        candidate_bundle_sha256=payload_sha256(bundle),
        provenance_status='RECORDED_NOT_AUTHENTICATED', prior_model_use='NOT_VERIFIED')
    if bundle['contract_version'] == '2':
        result['import_record'] = copy.deepcopy(bundle['import_record'])
    return result


def origin_record(key, component):
    return dict(paper_id=key[0], observation_index=key[1], dimension=key[2],
        origin=component['origin'], component_sha256=payload_sha256(component),
        candidate_id=component['candidate_id'],
        candidate_bundle_sha256=component['candidate_bundle_sha256'],
        operator_review_sha256=component['operator_review_sha256'],
        proposed_claim_type=component['proposed_claim_type'], reviewed_claim_type=component['claim_type'])


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
    replaced = {(*targets[decision['target_rule_id']], dimensions[decision['candidate_id']]): decision['candidate_id']
                for decision in declared_review['decisions'] if decision['decision'] == 'accept'}
    origin_records, origins = [], {}
    for key, component in candidate_records(package):
        covered = (replaced.get(key) == component['candidate_id'] and component['operator_review_sha256'] == payload_sha256(declared_review)
                   and component['candidate_bundle_sha256'] == payload_sha256(candidates)
                   and component['candidate_id'] in replay['applied_candidate_ids'])
        row = origin_record(key, component)
        row['audit_status'] = 'REPLAYED_CURRENT_REVISION' if covered else 'INHERITED_ORIGIN_NOT_REPLAYED'
        origin_records.append(row); origins[key] = row
    final_keys = {(*key, payload_sha256(component)) for key, component in candidate_records(package)}
    initial_records = []
    for key, component in candidate_records(base):
        row = origin_record(key, component)
        row.update(retained_exactly_in_final=(*key, payload_sha256(component)) in final_keys,
                   audit_status='INITIAL_HISTORY_NOT_REPLAYED')
        initial_records.append(row)
    imported_history = any(row['origin'] == IMPORTED_ORIGIN for row in initial_records)
    has_imports = (imported_history or candidates['contract_version'] == '2'
                   or any(row['origin'] == IMPORTED_ORIGIN for row in origin_records))

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
                    recorded_candidate_origin=origins[key]['origin'] if key in origins else None,
                    candidate_origin_audit=origins[key]['audit_status'] if key in origins else 'NO_CANDIDATE_ORIGIN_ON_SELECTED_RECORD',
                    mock_origin_audit=(origins[key]['audit_status'] if key in origins and origins[key]['origin'] == MOCK_ORIGIN
                                       else 'NO_MOCK_ORIGIN_ON_SELECTED_RECORD')))
                if OBSERVATION_ORIGIN in node['observation']:
                    endpoints[-1].update(observation_origin_sha256=payload_sha256(node['observation'][OBSERVATION_ORIGIN]),
                        observation_origin_audit='OBSERVATION_ADOPTION_NOT_REPLAYED')
            uses.append(dict(link_id=use['link_id'], proposed_use_role=use['role'],
                applicability_note_sha256=payload_sha256(use['applicability_note']),
                source_relation=link['relation'], relation_claim_type=link['claim_type'], endpoints=endpoints))
        routes.append(dict(step_id=step['step_id'], claim_type='operator_proposal',
            proposed_action_sha256=payload_sha256(step['proposed_action']),
            operator_field_status={field: 'NOT_SUPPLIED' if step[field] is None else 'SUPPLIED_NOT_VALIDATED'
                                   for field in OPTIONAL_FIELDS},
            evidence_status=step['evidence_status'], uses=uses))
    inherited = sum(row['audit_status'] == 'INHERITED_ORIGIN_NOT_REPLAYED' for row in origin_records)
    result = dict(status='CURRENT_REVISION_MATCH_WITH_INHERITED_ORIGINS' if inherited else 'CURRENT_REVISION_REPLAY_MATCH',
        audit_scope='ONE_DECLARED_CANDIDATE_REVIEW_REVISION' if has_imports else 'ONE_DECLARED_MOCK_REVIEW_REVISION',
        candidate_provenance=candidate_provenance(candidates), replayed_package_sha256=payload_sha256(replay['package']),
        original_corpus_sha256=payload_sha256(corpus), candidate_bundle_sha256=payload_sha256(candidates),
        operator_review_sha256=payload_sha256(declared_review), proposal_sha256=design['proposal_sha256'],
        link_artifact_sha256=design['link_artifact_sha256'],
        question=design['question'], candidate_origin_components=origin_records,
        mock_origin_components=[row for row in origin_records if row['origin'] == MOCK_ORIGIN],
        imported_origin_components=[row for row in origin_records if row['origin'] == IMPORTED_ORIGIN],
        inherited_origin_count=inherited, step_evidence_routes=routes,
        initial_unreplayed_origins=initial_records,
        initial_history_status='UNREPLAYED_CANDIDATE_ORIGINS_PRESENT' if initial_records else 'NO_CANDIDATE_ORIGIN_MARKERS_IN_INITIAL_CORPUS',
        unreferenced_link_ids=list(design['unreferenced_link_ids']),
        semantic_validation='NOT_PERFORMED', operator_identity='RECORDED_NOT_AUTHENTICATED',
        execution_scope='CURRENT_AUDIT_ONLY; PRIOR_MODEL_USE_NOT_VERIFIED',
        llm_used=False, provider_invoked=False, canonical_update_performed=False,
        boundary='Exact mechanical replay of one declared revision only, not complete historical lineage, '
                 'source authenticity, authenticated human review or researcher fidelity. Inherited candidate '
                 'origins are not replayed, including initial records later replaced. Current-revision status '
                 'and inherited_origin_count describe final records only; inspect initial_history_status separately. Source quotes are checked against supplied segments, not '
                 'independently obtained publications or source-file bytes. No semantic applicability, '
                 'claim ownership, hypothesis validity or experiment quality is established. Selected-record '
                 'routes identify explicit references only; nearby reasoning components are not inferred as '
                 'used. Missing proposal fields stay missing. No raw source sections or candidate text are '
                 'included in this audit; retain the separately bound original artifacts. Imported provider/model/run '
                 'identities are operator declarations, not authenticated. Execution flags describe this audit '
                 'only and do not establish or deny actual historical model use.')
    if observation_origins(base) or observation_origins(package):
        result.update(status='CURRENT_REVISION_MATCH_WITH_UNREPLAYED_OBSERVATION_HISTORY',
            initial_reasoning_history_status=result['initial_history_status'],
            initial_history_status='UNREPLAYED_REASONING_AND_OBSERVATION_ORIGINS_PRESENT' if initial_records else 'UNREPLAYED_OBSERVATION_ORIGINS_PRESENT',
            initial_unreplayed_observation_origins=observation_origins(base),
            final_unreplayed_observation_origins=observation_origins(package),
            observation_adoption_history_status='NOT_REPLAYED_BY_REASONING_REVISION_AUDIT',
            candidate_origin_coverage_scope='REASONING_COMPONENTS_ONLY')
    return result


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
