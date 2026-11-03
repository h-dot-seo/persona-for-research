import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import test_design_lineage as synthetic_fixture
from audit_design_chain import audit
from extraction_adapter import MockProvider, extract_candidates
from operator_review import prepare_revision
from persona import payload_sha256


class DesignChainTests(unittest.TestCase):
    def setUp(self):
        self.base = synthetic_fixture.DesignLineageTests()
        self.base.setUp()
        self.configure_chain()

    def configure_chain(self, dimension='question_framing'):
        first = dict(**self.base.inputs, target_version='2', target_build_id='synthetic-reviewed')
        original = copy.deepcopy(self.base.corpus)
        original['version'], original['build_id'] = '2', 'synthetic-reviewed'
        for raw, paper in zip(original['papers'], self.base.package['knowledge']['papers']):
            raw['observations'] = copy.deepcopy(paper['observations'])
        response = copy.deepcopy(self.base.response[:1])
        response[0].update(dimension=dimension, candidate_text='Which synthetic observation distinguishes explanations?')
        self.chain = dict(stages=[first])
        self.set_second(original, response)

    def set_second(self, corpus, response, target_version='3', target_build='synthetic-third'):
        bundle = extract_candidates(corpus, MockProvider(response))
        candidate = bundle['candidates'][0]
        old = corpus['papers'][0]['observations'][0]['reasoning'].get(candidate['dimension'])
        declared = dict(candidate_bundle_sha256=payload_sha256(bundle), input_corpus_sha256=payload_sha256(corpus),
            reviewer_id='synthetic-second-reviewer', decisions=[dict(candidate_id=candidate['candidate_id'], decision='accept',
                review_note='Explicit second synthetic review.', target_rule_id='rule-1', target_paper_id='synthetic-0',
                operation='replace' if old is not None else 'add', expected_component_sha256=payload_sha256(old) if old is not None else None,
                reviewed_text=candidate['candidate_text'], reviewed_claim_type='operator_interpretation')])
        second = dict(original_corpus=corpus, candidate_bundle=bundle, operator_review=declared,
                      target_version=target_version, target_build_id=target_build)
        self.chain['stages'] = self.chain['stages'][:1] + [second]
        self.package = prepare_revision(corpus, bundle, declared, target_version, target_build)['package']
        self.base.package = self.package
        self.base.bind_design()
        self.links, self.proposal = self.base.links, self.base.proposal

    def run_audit(self):
        return audit(self.package, self.links, self.proposal, self.chain)

    def test_two_stage_add_covers_prior_origins_and_repeated_candidate_ids(self):
        result = self.run_audit()
        self.assertEqual(result['status'], 'DECLARED_CHAIN_REPLAY_MATCH')
        self.assertEqual(result['final_mock_origin_coverage'], 'ALL_FINAL_MARKERS_COVERED_BY_DECLARED_STAGES')
        self.assertEqual(result['initial_unreplayed_origins'], [])
        origins = {r['dimension']: r for r in result['final_mock_origins']}
        self.assertEqual(origins['alternative_explanation']['candidate_id'], origins['question_framing']['candidate_id'])
        self.assertEqual(origins['alternative_explanation']['replay_stage_index'], 1)
        self.assertEqual(origins['question_framing']['replay_stage_index'], 2)
        self.assertEqual(result['step_evidence_routes'][0]['uses'][0]['endpoints'][1]['replay_stage_index'], 1)
        self.assertEqual(result['stages'][0]['output_package_sha256'], result['stages'][1]['input_package_sha256'])

    def test_second_stage_explicit_replace_uses_exact_prior_content(self):
        self.base.setUp(); self.configure_chain('uncertainty')
        result = self.run_audit()
        origins = {r['dimension']: r for r in result['final_mock_origins']}
        self.assertEqual(origins['uncertainty']['replay_stage_index'], 2)
        self.assertEqual(origins['alternative_explanation']['replay_stage_index'], 1)
        self.chain['stages'][1]['operator_review']['decisions'][0]['expected_component_sha256'] = '0' * 64
        with self.assertRaises(ValueError): self.run_audit()

    def test_skipped_reordered_and_wrong_final_stages_fail(self):
        for stages in ([self.chain['stages'][0]], list(reversed(self.chain['stages']))):
            with self.assertRaises(ValueError):
                audit(self.package, self.links, self.proposal, dict(stages=stages))
        # Starting from stage 2 is a valid shorter declaration, but it must preserve
        # the warning that inherited prior origins were not replayed.
        shorter = audit(self.package, self.links, self.proposal, dict(stages=[self.chain['stages'][1]]))
        self.assertEqual(shorter['status'], 'DECLARED_CHAIN_MATCH_WITH_UNREPLAYED_HISTORY')
        self.assertTrue(shorter['initial_unreplayed_origins'])

    def test_unrecorded_runtime_edits_and_new_sources_break_continuity(self):
        for mode in ('counterevidence', 'new_source'):
            self.setUp()
            second = self.chain['stages'][1]
            corpus = copy.deepcopy(second['original_corpus'])
            if mode == 'counterevidence':
                corpus['papers'][1]['observations'][0]['limitation'] = 'changed untargeted challenge limitation'
            else:
                added = copy.deepcopy(corpus['papers'][1]); added['paper_id'] = 'synthetic-new-source'
                corpus['papers'].append(added)
            response = copy.deepcopy(self.base.response[:1]); response[0]['dimension'] = 'question_framing'
            self.set_second(corpus, response)
            with self.assertRaisesRegex(ValueError, 'does not continue'):
                self.run_audit()

    def test_initial_history_warning_survives_when_inherited_component_is_replaced(self):
        self.base.setUp()
        self.base.corpus['papers'][0]['observations'][0]['reasoning']['question_framing'] = dict(
            text='Earlier synthetic framing.', locator='synthetic reasoning', evidence_quote='Compare explanations.',
            claim_type='operator_interpretation', origin='operator_reviewed_mock_candidate', candidate_id='prior-candidate',
            candidate_bundle_sha256='a' * 64, operator_review_sha256='b' * 64, proposed_claim_type='explicit_statement')
        self.base.rebuild(); self.configure_chain()
        result = self.run_audit()
        self.assertEqual(result['status'], 'DECLARED_CHAIN_MATCH_WITH_UNREPLAYED_HISTORY')
        self.assertEqual(result['final_mock_origin_coverage'], 'ALL_FINAL_MARKERS_COVERED_BY_DECLARED_STAGES')
        self.assertEqual(len(result['initial_unreplayed_origins']), 1)
        self.assertFalse(result['initial_unreplayed_origins'][0]['retained_exactly_in_final'])
        self.assertEqual(result['initial_history_status'], 'UNREPLAYED_MOCK_ORIGINS_PRESENT')

    def test_strict_stage_schema_pending_review_and_reused_identity_rejected(self):
        for chain in ({}, {'stages': []}, {'stages': [dict(self.chain['stages'][0], extra=True)]}):
            with self.assertRaises(ValueError):
                audit(self.package, self.links, self.proposal, chain)
        bad = copy.deepcopy(self.chain)
        bad['stages'][1]['operator_review']['decisions'] = [dict(candidate_id='candidate-1', decision='defer', review_note='Pending synthetic review.')]
        with self.assertRaises(ValueError): audit(self.package, self.links, self.proposal, bad)
        second = self.chain['stages'][1]
        response = copy.deepcopy(self.base.response[:1]); response[0]['dimension'] = 'question_framing'
        self.set_second(copy.deepcopy(second['original_corpus']), response, target_version='1', target_build='synthetic-build')
        with self.assertRaisesRegex(ValueError, 'reuse'):
            self.run_audit()

    def test_projected_continuity_alias_equivalence_no_provider_and_no_raw_leakage(self):
        second = self.chain['stages'][1]
        corpus = copy.deepcopy(second['original_corpus'])
        corpus['ignored_note'] = 'SYNTHETIC_UNLISTED_MARKER'
        corpus['papers'][0]['ignored_note'] = corpus['papers'][1]  # Shared JSON-equivalent metadata.
        response = copy.deepcopy(self.base.response[:1]); response[0].update(dimension='question_framing', candidate_text='SYNTHETIC_CANDIDATE_MARKER')
        self.set_second(corpus, response)
        before = copy.deepcopy((self.package, self.links, self.proposal, self.chain))
        with patch.object(MockProvider, 'extract', side_effect=AssertionError('provider called')), \
             patch.object(Path, 'read_text', side_effect=AssertionError('source opened')):
            result = self.run_audit()
            plain = audit(*json.loads(json.dumps((self.package, self.links, self.proposal, self.chain))))
        self.assertEqual(result, plain)
        self.assertEqual((self.package, self.links, self.proposal, self.chain), before)
        self.assertNotIn('SYNTHETIC_UNLISTED_MARKER', json.dumps(result))
        self.assertNotIn('SYNTHETIC_CANDIDATE_MARKER', json.dumps(result))
        self.assertFalse(result['provider_invoked'])

    def test_real_cli_two_review_transitions_to_chain_audit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            final = root / 'final.json'
            for index, stage in enumerate(self.chain['stages']):
                paths = [root / (str(index) + name + '.json') for name in ('corpus', 'candidates', 'review')]
                for path, key in zip(paths, ('original_corpus', 'candidate_bundle', 'operator_review')):
                    path.write_text(json.dumps(stage[key]))
                output = subprocess.run([sys.executable, 'operator_review.py', *map(str, paths),
                    '--new-version', stage['target_version'], '--new-build-id', stage['target_build_id']],
                    capture_output=True, text=True, timeout=20)
                self.assertEqual(output.returncode, 0, output.stderr); final.write_text(output.stdout)
            paths = [root / name for name in ('links.json', 'proposal.json', 'chain.json')]
            for path, data in zip(paths, (self.links, self.proposal, self.chain)): path.write_text(json.dumps(data))
            command = [sys.executable, 'audit_design_chain.py', str(final), *map(str, paths)]
            result = subprocess.run(command, capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), self.run_audit())
            paths[-1].write_text(json.dumps(dict(stages=list(reversed(self.chain['stages'])))))
            failed = subprocess.run(command, capture_output=True, text=True, timeout=20)
            self.assertNotEqual(failed.returncode, 0); self.assertEqual(failed.stdout, '')


if __name__ == '__main__':
    unittest.main()
