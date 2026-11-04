"""Synthetic offline provenance regressions; no model or network calls."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import test_design_lineage as fixture
from answer_draft import template as answer_template
from audit_design_lineage import audit as audit_one
from audit_design_chain import audit as audit_chain
from evidence_scope import disclose, render
from extraction_adapter import (MockProvider, extract_candidates,
    prepare_model_handoff, import_model_response)
from operator_review import prepare_revision
from persona import payload_sha256


class ImportedProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.case = fixture.DesignLineageTests(); self.case.setUp()

    def stage(self, corpus, response, imported, version):
        if imported:
            handoff = prepare_model_handoff(corpus)
            bundle = import_model_response(corpus, handoff,
                dict(handoff_sha256=payload_sha256(handoff), candidates=response),
                dict(provider_id='declared-provider', model_id='declared-model', run_id='declared-run',
                     operator_id='synthetic-operator', execution_location='unknown'))
        else:
            bundle = extract_candidates(corpus, MockProvider(response))
        decisions = []
        for candidate in bundle['candidates']:
            old = corpus['papers'][0]['observations'][0]['reasoning'].get(candidate['dimension'])
            decisions.append(dict(candidate_id=candidate['candidate_id'], decision='accept', review_note='Synthetic declaration.',
                target_rule_id='rule-1', target_paper_id='synthetic-0', operation='replace' if old else 'add',
                expected_component_sha256=payload_sha256(old) if old else None,
                reviewed_text=candidate['candidate_text'], reviewed_claim_type='operator_interpretation'))
        review = dict(candidate_bundle_sha256=payload_sha256(bundle), input_corpus_sha256=payload_sha256(corpus),
                      reviewer_id='synthetic-reviewer', decisions=decisions)
        stage = dict(original_corpus=corpus, candidate_bundle=bundle, operator_review=review,
                     target_version=version, target_build_id='synthetic-' + version)
        package = prepare_revision(corpus, bundle, review, version, 'synthetic-' + version)['package']
        return stage, package

    def continue_corpus(self, original, package):
        corpus = copy.deepcopy(original)
        corpus['version'] = package['persona']['version']; corpus['build_id'] = package['persona']['build_id']
        for raw, paper in zip(corpus['papers'], package['knowledge']['papers']):
            raw['observations'] = copy.deepcopy(paper['observations'])
        return corpus

    def bind(self, package):
        self.case.package = package; self.case.bind_design()

    def audit_one(self, stage, package):
        self.bind(package)
        return audit_one(package, self.case.links, self.case.proposal,
            {key: stage[key] for key in ('original_corpus', 'candidate_bundle', 'operator_review')})

    def audit_chain(self, stages, package):
        self.bind(package)
        return audit_chain(package, self.case.links, self.case.proposal, dict(stages=stages))

    def test_imported_replay_has_separate_origin_and_execution_flags(self):
        stage, package = self.stage(self.case.corpus, self.case.response, True, '2')
        before = copy.deepcopy((stage, package))
        with patch.object(MockProvider, 'extract', side_effect=AssertionError('provider invoked')), \
             patch.object(Path, 'read_text', side_effect=AssertionError('source opened')):
            one = self.audit_one(stage, package)
            chain = self.audit_chain([stage], package)
            plain_stage, plain_package = json.loads(json.dumps((stage, package)))
            self.assertEqual(one, self.audit_one(plain_stage, plain_package))
            self.assertEqual(chain, self.audit_chain([plain_stage], plain_package))
        self.assertEqual((stage, package), before)
        self.assertEqual(one['status'], 'CURRENT_REVISION_REPLAY_MATCH')
        self.assertEqual(chain['status'], 'DECLARED_CHAIN_REPLAY_MATCH')
        self.assertEqual(one['mock_origin_components'], [])
        self.assertEqual(chain['final_mock_origins'], [])
        self.assertEqual(len(one['imported_origin_components']), 2)
        self.assertEqual(len(chain['final_imported_origins']), 2)
        self.assertEqual(one['candidate_origin_components'], one['imported_origin_components'])
        self.assertEqual(one['candidate_provenance']['import_record'], stage['candidate_bundle']['import_record'])
        self.assertEqual(chain['stages'][0]['candidate_provenance'], one['candidate_provenance'])
        for result in (one, chain):
            self.assertFalse(result['llm_used']); self.assertFalse(result['provider_invoked'])
            self.assertIn('CURRENT_AUDIT_ONLY', result['execution_scope'])
            route = result['step_evidence_routes'][0]['uses'][0]['endpoints'][1]
            self.assertEqual(route['mock_origin_audit'], 'NO_MOCK_ORIGIN_ON_SELECTED_RECORD')
            self.assertEqual(route['recorded_candidate_origin'], 'operator_reviewed_imported_candidate')
        one['candidate_provenance']['import_record']['provenance']['run_id'] = 'changed'
        self.assertEqual((stage, package), before)

    def test_imported_bundle_with_mock_final_fails_exact_match(self):
        stage, _ = self.stage(self.case.corpus, self.case.response, True, '2')
        for method, inputs in ((self.audit_one, stage), (self.audit_chain, [stage])):
            with self.assertRaisesRegex(ValueError, 'exactly match'):
                method(inputs, self.case.package)

    def test_imported_initial_history_warning_survives_full_replacement(self):
        first, package = self.stage(self.case.corpus, self.case.response, True, '2')
        corpus = self.continue_corpus(self.case.corpus, package)
        second, package = self.stage(corpus, self.case.response, False, '3')
        shorter = self.audit_chain([second], package)
        self.assertEqual(shorter['status'], 'DECLARED_CHAIN_MATCH_WITH_UNREPLAYED_HISTORY')
        self.assertEqual(shorter['final_candidate_origin_coverage'], 'ALL_FINAL_MARKERS_COVERED_BY_DECLARED_STAGES')
        self.assertEqual(len(shorter['initial_unreplayed_imported_origins']), 2)
        self.assertEqual(shorter['initial_unreplayed_mock_origins'], [])
        self.assertTrue(all(not row['retained_exactly_in_final'] for row in shorter['initial_unreplayed_origins']))
        for row in shorter['initial_unreplayed_origins']:
            self.assertEqual(row['candidate_bundle_sha256'], payload_sha256(first['candidate_bundle']))
        full = self.audit_chain([first, second], package)
        self.assertEqual(full['status'], 'DECLARED_CHAIN_REPLAY_MATCH')
        self.assertEqual(full['final_imported_origins'], [])
        self.assertEqual(full['stages'][0]['candidate_provenance']['import_record'], first['candidate_bundle']['import_record'])
        one = self.audit_one(second, package)
        self.assertEqual(one['status'], 'CURRENT_REVISION_REPLAY_MATCH')
        self.assertEqual(one['inherited_origin_count'], 0)
        self.assertEqual(one['initial_history_status'], 'UNREPLAYED_CANDIDATE_ORIGINS_PRESENT')
        self.assertEqual(len(one['initial_unreplayed_origins']), 2)
        self.assertTrue(all(not row['retained_exactly_in_final'] for row in one['initial_unreplayed_origins']))
        self.assertTrue(all(row['origin'] == 'operator_reviewed_imported_candidate'
                            for row in one['initial_unreplayed_origins']))

    def test_imported_intermediate_stage_is_retained_in_chain_summary(self):
        stages = []; corpus = self.case.corpus
        for index, imported in enumerate((False, True, False), 2):
            stage, package = self.stage(corpus, self.case.response, imported, str(index))
            stages.append(stage); corpus = self.continue_corpus(corpus, package)
        result = self.audit_chain(stages, package)
        self.assertEqual(result['status'], 'DECLARED_CHAIN_REPLAY_MATCH')
        self.assertEqual(result['final_imported_origins'], [])
        self.assertEqual(result['stages'][1]['candidate_provenance']['import_record'], stages[1]['candidate_bundle']['import_record'])
        self.assertTrue(all(row['replay_stage_index'] == 3 for row in result['final_candidate_origins']))

    def test_mixed_retained_origins_scope_repeated_candidate_ids_by_bundle(self):
        first, package = self.stage(self.case.corpus, self.case.response[:1], True, '2')
        corpus = self.continue_corpus(self.case.corpus, package)
        second, package = self.stage(corpus, self.case.response[1:], False, '3')
        result = self.audit_chain([first, second], package)
        imported, mock = result['final_imported_origins'][0], result['final_mock_origins'][0]
        self.assertEqual(imported['candidate_id'], mock['candidate_id'])
        self.assertNotEqual(imported['candidate_bundle_sha256'], mock['candidate_bundle_sha256'])
        self.assertEqual(imported['replay_stage_index'], 1)
        self.assertEqual(mock['replay_stage_index'], 2)
        one = self.audit_one(second, package)
        self.assertEqual(one['inherited_origin_count'], 1)
        self.assertEqual(one['imported_origin_components'][0]['audit_status'], 'INHERITED_ORIGIN_NOT_REPLAYED')
        shorter = self.audit_chain([second], package)
        self.assertEqual(shorter['final_candidate_origin_coverage'], 'FINAL_MARKERS_OUTSIDE_DECLARED_CHAIN')
        self.assertEqual(shorter['final_mock_origin_coverage'], 'ALL_FINAL_MARKERS_COVERED_BY_DECLARED_STAGES')
        self.assertTrue(shorter['initial_unreplayed_imported_origins'][0]['retained_exactly_in_final'])
        # Select the imported component, not its nearby mock neighbor.
        self.case.bind_design(selected_dimension=imported['dimension'])
        selected = audit_chain(package, self.case.links, self.case.proposal, dict(stages=[first, second]))
        endpoint = selected['step_evidence_routes'][0]['uses'][0]['endpoints'][1]
        self.assertEqual(endpoint['candidate_origin_audit'], 'REPLAYED_DECLARED_STAGE')
        self.assertEqual(endpoint['replay_stage_index'], 1)
        self.assertEqual(endpoint['mock_origin_audit'], 'NO_MOCK_ORIGIN_ON_SELECTED_RECORD')

    def test_imported_tamper_bindings_and_recomputed_declarations_fail(self):
        stage, package = self.stage(self.case.corpus, self.case.response, True, '2')
        for field in ('handoff_sha256', 'response_sha256', 'provenance', 'candidate_text', 'review'):
            bad = copy.deepcopy(stage)
            if field in ('handoff_sha256', 'response_sha256'):
                bad['candidate_bundle']['import_record'][field] = '0' * 64
            elif field == 'provenance':
                # A coherent changed declaration cannot authenticate a different final package.
                bad['candidate_bundle']['import_record']['provenance']['run_id'] = 'different-run'
                bad['operator_review']['candidate_bundle_sha256'] = payload_sha256(bad['candidate_bundle'])
            elif field == 'candidate_text':
                bad['candidate_bundle']['candidates'][0]['candidate_text'] += ' changed'
            else:
                bad['operator_review']['decisions'][0]['reviewed_text'] += ' changed'
            for method, inputs in ((self.audit_one, bad), (self.audit_chain, [bad])):
                with self.subTest(field=field, method=method.__name__), self.assertRaises(ValueError):
                    method(inputs, package)

    def test_mixed_scope_classifies_exact_origins_and_counts_each_reference(self):
        first, package = self.stage(self.case.corpus, self.case.response[:1], False, '2')
        corpus = self.continue_corpus(self.case.corpus, package)
        second, package = self.stage(corpus, self.case.response[1:], True, '3')
        self.bind(package)
        draft = answer_template(package, self.case.proposal['question'], 'synthetic-operator')
        draft['claims'] = [dict(claim_id='synthetic-answer', text='Consider both records.',
            claim_type='operator_synthesis', uncertainty='Synthetic only.', citations=[
                dict(role='context', reference=dict(paper_id='synthetic-0', observation_index=0, dimension=c['dimension']))
                for c in self.case.response])]
        with patch.object(MockProvider, 'extract', side_effect=AssertionError('provider invoked')):
            result = disclose(package, self.case.links, self.case.proposal, draft, 2020)
            text = render(package, self.case.links, self.case.proposal, draft, 2020)
        self.assertEqual(len(result['recorded_mock_origin_references']), 1)
        self.assertEqual(len(result['recorded_imported_origin_references']), 1)
        self.assertEqual(len(result['recorded_candidate_origin_references']), 2)
        self.assertEqual(result['coverage']['active_exact_references'], 3)
        self.assertFalse(result['llm_used']); self.assertFalse(result['provider_invoked'])
        self.assertIn('RECORDED_IMPORTED_CANDIDATE_ORIGIN', text)
        self.assertIn('Recorded imported candidate origin', text)
        imported = next(r for g in result['source_groups'] for r in g['active_references']
                        if r['origin_status'] == 'RECORDED_IMPORTED_CANDIDATE_ORIGIN')
        self.assertEqual(imported['recorded_origin']['candidate_bundle_sha256'], payload_sha256(second['candidate_bundle']))
        self.assertEqual(imported['recorded_origin']['proposed_claim_type'], 'explicit_statement')
        self.assertEqual(imported['selected_claim_type'], 'operator_interpretation')

    def test_unused_imported_reference_is_disclosed_not_counted_active(self):
        stage, package = self.stage(self.case.corpus, self.case.response, True, '2')
        self.bind(package); self.case.proposal['steps'] = []
        draft = answer_template(package, self.case.proposal['question'], 'synthetic-operator')
        result = disclose(package, self.case.links, self.case.proposal, draft, 2020)
        self.assertEqual(result['coverage']['active_exact_references'], 0)
        self.assertEqual(result['recorded_imported_origin_references'], [])
        rows = [r for g in result['source_groups'] for r in g['unused_link_references']]
        self.assertTrue(any(r['origin_status'] == 'RECORDED_IMPORTED_CANDIDATE_ORIGIN' for r in rows))


if __name__ == '__main__':
    unittest.main()
