import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from audit_design_lineage import audit
from design_scenario import template as design_template
from extraction_adapter import MockProvider, extract_candidates
from operator_review import prepare_revision
from persona import payload_sha256
from reasoning_links import template as link_template


class DesignLineageTests(unittest.TestCase):
    def setUp(self):
        self.corpus = json.loads(Path('examples/reasoning-corpus.json').read_text())
        self.corpus['papers'][0]['observations'][0]['reasoning'] = {}
        second = self.corpus['papers'][1]
        second['segments']['synthetic criterion'] = 'Shared predictions do not discriminate models.'
        second['segments_sha256'] = payload_sha256(second['segments'])
        second['observations'][0]['stance'] = 'challenge'
        second['observations'][0]['reasoning'] = dict(falsification_check=dict(
            text='Check whether predictions differ.', locator='synthetic criterion',
            evidence_quote='Shared predictions do not discriminate models.', claim_type='explicit_statement'))
        self.response = json.loads(Path('examples/mock-extraction-response.json').read_text())
        self.rebuild()

    def rebuild(self):
        self.bundle = extract_candidates(self.corpus, MockProvider(self.response))
        self.declared = dict(candidate_bundle_sha256=payload_sha256(self.bundle), input_corpus_sha256=payload_sha256(self.corpus),
            reviewer_id='synthetic-reviewer', decisions=[dict(candidate_id=c['candidate_id'], decision='accept',
                review_note='Synthetic declared review only.', target_rule_id='rule-1', target_paper_id='synthetic-0',
                operation='add', expected_component_sha256=None, reviewed_text=c['candidate_text'],
                reviewed_claim_type='operator_interpretation') for c in self.bundle['candidates']])
        self.package = prepare_revision(self.corpus, self.bundle, self.declared, '2', 'synthetic-reviewed')['package']
        self.inputs = dict(original_corpus=self.corpus, candidate_bundle=self.bundle, operator_review=self.declared)
        self.bind_design()

    def bind_design(self, selected_dimension='uncertainty'):
        self.links = link_template(self.package, 'synthetic-link-operator')
        self.links['links'] = [dict(link_id='criterion-link', relation='qualifies',
            from_ref=dict(paper_id='synthetic-1', observation_index=0, dimension='falsification_check'),
            to_ref=dict(paper_id='synthetic-0', observation_index=0, dimension=selected_dimension),
            rationale='The synthetic criterion limits the proposed interpretation.', claim_type='operator_interpretation')]
        self.proposal = design_template(self.package, self.links, 'Which synthetic observation distinguishes models?', 'synthetic-design-operator')
        self.proposal['steps'] = [dict(step_id='design-1', proposed_action='Compare synthetic predictions before selecting a measurement.',
            rationale='Inspect discriminating capacity without claiming a validated test.',
            hypothesis='The predicted observations differ.', falsification_check=None, alternative_explanation=None,
            uncertainty='No empirical outputs have been checked.', link_uses=[dict(link_id='criterion-link', role='constraint',
                applicability_note='The operator proposes inspecting the criterion before proceeding.')])]

    def run_audit(self):
        return audit(self.package, self.links, self.proposal, self.inputs)

    def test_replay_routes_mock_claims_and_missing_design_fields(self):
        result = self.run_audit()
        self.assertEqual(result['status'], 'CURRENT_REVISION_REPLAY_MATCH')
        self.assertEqual(result['inherited_origin_count'], 0)
        self.assertEqual(len(result['mock_origin_components']), 2)
        record = next(row for row in result['mock_origin_components'] if row['dimension'] == 'uncertainty')
        self.assertEqual(record['proposed_claim_type'], 'explicit_statement')
        self.assertEqual(record['reviewed_claim_type'], 'operator_interpretation')
        step = result['step_evidence_routes'][0]
        self.assertEqual(step['operator_field_status']['falsification_check'], 'NOT_SUPPLIED')
        selected = step['uses'][0]['endpoints'][1]
        self.assertEqual(selected['reference']['dimension'], 'uncertainty')
        self.assertEqual(selected['mock_origin_audit'], 'REPLAYED_CURRENT_REVISION')
        self.assertEqual(selected['observation_method_sha256'], payload_sha256(self.package['knowledge']['papers'][0]['observations'][0]['method']))
        self.assertEqual(selected['selected_record_locator'], 'synthetic reasoning')
        self.assertEqual(step['uses'][0]['endpoints'][0]['observation_stance'], 'challenge')
        self.assertEqual(step['uses'][0]['endpoints'][0]['mock_origin_audit'], 'NO_MOCK_ORIGIN_ON_SELECTED_RECORD')
        self.assertEqual(result['replayed_package_sha256'], payload_sha256(self.package))

    def test_replay_uses_no_provider_source_reads_or_mutation(self):
        before = copy.deepcopy((self.package, self.links, self.proposal, self.inputs))
        with patch.object(MockProvider, 'extract', side_effect=AssertionError('provider invoked')), \
             patch.object(Path, 'read_text', side_effect=AssertionError('source opened')):
            result = self.run_audit()
            equivalent = audit(*json.loads(json.dumps((self.package, self.links, self.proposal, self.inputs))))
        self.assertEqual(result, equivalent)
        self.assertFalse(result['provider_invoked'])
        self.assertFalse(result['llm_used'])
        result['step_evidence_routes'][0]['uses'][0]['endpoints'][0]['reference']['paper_id'] = 'edited'
        self.assertEqual((self.package, self.links, self.proposal, self.inputs), before)

    def test_stale_candidate_review_and_raw_source_rejected(self):
        for mode in ('candidate', 'review', 'source', 'schema'):
            bad = copy.deepcopy(self.inputs)
            if mode == 'candidate': bad['candidate_bundle']['candidates'][0]['candidate_text'] += ' changed'
            elif mode == 'review': bad['operator_review']['decisions'][0]['reviewed_text'] += ' changed'
            elif mode == 'source': bad['original_corpus']['papers'][0]['segments']['synthetic reasoning'] += ' changed'
            else: bad['unexpected'] = 'unlisted'
            with self.assertRaises(ValueError):
                audit(self.package, self.links, self.proposal, bad)

    def test_self_consistent_different_final_package_fails_exact_replay(self):
        self.package['knowledge']['papers'][1]['observations'][0]['limitation'] = 'different synthetic limitation'
        self.package['persona']['rules'][1]['limitation'] = 'different synthetic limitation'
        self.package['persona']['knowledge_papers_sha256'] = payload_sha256(self.package['knowledge']['papers'])
        self.package['knowledge']['persona_payload_sha256'] = payload_sha256(self.package['persona'])
        self.bind_design()
        with self.assertRaisesRegex(ValueError, 'does not exactly match'):
            self.run_audit()

    def test_reject_or_defer_cannot_supply_a_revision(self):
        for kind in ('reject', 'defer'):
            bad = copy.deepcopy(self.inputs)
            bad['operator_review']['decisions'] = [dict(candidate_id=c['candidate_id'], decision=kind,
                review_note='Synthetic declined or pending decision.') for c in self.bundle['candidates']]
            with self.assertRaisesRegex(ValueError, 'does not produce'):
                audit(self.package, self.links, self.proposal, bad)

    def test_inherited_mock_origin_is_explicitly_not_replayed(self):
        self.corpus['papers'][0]['observations'][0]['reasoning']['question_framing'] = dict(
            text='Which synthetic model?', locator='synthetic reasoning', evidence_quote='Compare explanations.',
            claim_type='operator_interpretation', origin='operator_reviewed_mock_candidate', candidate_id='prior-candidate',
            candidate_bundle_sha256='a' * 64, operator_review_sha256='b' * 64, proposed_claim_type='explicit_statement')
        self.rebuild()
        unselected = self.run_audit()
        self.assertEqual(unselected['inherited_origin_count'], 1)
        self.assertEqual(unselected['step_evidence_routes'][0]['uses'][0]['endpoints'][1]['reference']['dimension'], 'uncertainty')
        self.bind_design(selected_dimension='question_framing')
        result = self.run_audit()
        self.assertEqual(result['status'], 'CURRENT_REVISION_MATCH_WITH_INHERITED_ORIGINS')
        self.assertEqual(result['inherited_origin_count'], 1)
        self.assertEqual(result['step_evidence_routes'][0]['uses'][0]['endpoints'][1]['mock_origin_audit'], 'INHERITED_ORIGIN_NOT_REPLAYED')
        self.assertIn('not complete historical lineage', result['boundary'])

    def test_raw_sections_unknown_metadata_and_candidate_text_not_dumped(self):
        self.corpus['hidden_note'] = 'SYNTHETIC_PRIVATE_MARKER'
        self.corpus['papers'][0]['segments']['unused section'] = 'SYNTHETIC_RAW_MARKER'
        self.corpus['papers'][0]['segments_sha256'] = payload_sha256(self.corpus['papers'][0]['segments'])
        self.response[0]['candidate_text'] = 'SYNTHETIC_CANDIDATE_TEXT_MARKER'
        self.rebuild()
        text = json.dumps(self.run_audit())
        for marker in ('SYNTHETIC_PRIVATE_MARKER', 'SYNTHETIC_RAW_MARKER', 'SYNTHETIC_CANDIDATE_TEXT_MARKER'):
            self.assertNotIn(marker, text)
        self.proposal['steps'] = []
        result = self.run_audit()
        self.assertEqual(result['step_evidence_routes'], [])
        self.assertEqual(result['unreferenced_link_ids'], ['criterion-link'])

    def test_real_cli_mock_to_reviewed_design_to_lineage_audit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = {name: root / (name + '.json') for name in ('corpus', 'response', 'candidates', 'review', 'package', 'links', 'proposal', 'inputs')}
            files['corpus'].write_text(json.dumps(self.corpus)); files['response'].write_text(json.dumps(self.response))
            def run(script, *args):
                result = subprocess.run([sys.executable, script, *map(str, args)], capture_output=True, text=True, timeout=20)
                self.assertEqual(result.returncode, 0, result.stderr)
                return json.loads(result.stdout)
            candidates = run('extraction_adapter.py', files['corpus'], '--mock-response', files['response'])
            self.assertEqual(candidates, self.bundle); files['candidates'].write_text(json.dumps(candidates))
            files['review'].write_text(json.dumps(self.declared))
            revision = run('operator_review.py', files['corpus'], files['candidates'], files['review'],
                           '--new-version', '2', '--new-build-id', 'synthetic-reviewed')
            files['package'].write_text(json.dumps(revision)); files['links'].write_text(json.dumps(self.links))
            files['proposal'].write_text(json.dumps(self.proposal)); files['inputs'].write_text(json.dumps(self.inputs))
            design = run('design_scenario.py', files['package'], files['links'], files['proposal'])
            self.assertEqual(design['steps'][0]['missing_fields'], ['falsification_check', 'alternative_explanation'])
            result = run('audit_design_lineage.py', files['package'], files['links'], files['proposal'], files['inputs'])
            self.assertEqual(result, self.run_audit())
            files['inputs'].write_text('{}')
            failed = subprocess.run([sys.executable, 'audit_design_lineage.py', str(files['package']), str(files['links']),
                str(files['proposal']), str(files['inputs'])], capture_output=True, text=True, timeout=20)
            self.assertNotEqual(failed.returncode, 0); self.assertEqual(failed.stdout, '')


if __name__ == '__main__':
    unittest.main()
