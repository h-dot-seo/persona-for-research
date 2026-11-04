"""Synthetic offline provenance regressions; no model or network calls."""
import copy
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

    def test_imported_final_and_bundle_rejected_without_provider(self):
        stage, package = self.stage(self.case.corpus, self.case.response, True, '2')
        self.bind(package)
        with patch.object(MockProvider, 'extract', side_effect=AssertionError('provider invoked')):
            with self.assertRaisesRegex(ValueError, 'mock-only'):
                audit_one(package, self.case.links, self.case.proposal,
                    {key: stage[key] for key in ('original_corpus', 'candidate_bundle', 'operator_review')})
            with self.assertRaisesRegex(ValueError, 'mock-only'):
                audit_chain(package, self.case.links, self.case.proposal, dict(stages=[stage]))

    def test_imported_bundle_rejected_before_replay_even_with_mock_final(self):
        stage, _ = self.stage(self.case.corpus, self.case.response, True, '2')
        with self.assertRaisesRegex(ValueError, 'imported candidate bundles'):
            audit_one(self.case.package, self.case.links, self.case.proposal,
                {key: stage[key] for key in ('original_corpus', 'candidate_bundle', 'operator_review')})
        with self.assertRaisesRegex(ValueError, 'imported candidate bundles'):
            audit_chain(self.case.package, self.case.links, self.case.proposal, dict(stages=[stage]))

    def test_imported_initial_history_rejected_even_when_fully_replaced(self):
        first, package = self.stage(self.case.corpus, self.case.response, True, '2')
        corpus = self.continue_corpus(self.case.corpus, package)
        second, package = self.stage(corpus, self.case.response, False, '3')
        self.bind(package)
        # Final records are all mock, but the initial imported history is outside scope.
        self.assertTrue(all(c['origin'] == 'operator_reviewed_mock_candidate'
            for c in package['knowledge']['papers'][0]['observations'][0]['reasoning'].values()))
        for stages in ([second], [first, second]):
            with self.assertRaisesRegex(ValueError, 'mock-only'):
                audit_chain(package, self.case.links, self.case.proposal, dict(stages=stages))
        with self.assertRaisesRegex(ValueError, 'mock-only'):
            audit_one(package, self.case.links, self.case.proposal,
                {key: second[key] for key in ('original_corpus', 'candidate_bundle', 'operator_review')})

    def test_imported_intermediate_stage_rejected_when_final_is_mock(self):
        first, package = self.stage(self.case.corpus, self.case.response, False, '2')
        corpus = self.continue_corpus(self.case.corpus, package)
        second, package = self.stage(corpus, self.case.response, True, '3')
        corpus = self.continue_corpus(corpus, package)
        third, package = self.stage(corpus, self.case.response, False, '4')
        self.bind(package)
        with self.assertRaisesRegex(ValueError, 'mock-only'):
            audit_chain(package, self.case.links, self.case.proposal, dict(stages=[first, second, third]))

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
