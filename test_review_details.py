"""Synthetic source attribution and per-observation gap review regressions."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from persona import payload_sha256
from reasoning_cards import DIMENSIONS, REVIEW_FIELDS
from research_workflow import build
from review_package import render


class DetailReviewTests(unittest.TestCase):
    def setUp(self):
        self.corpus = json.loads(Path('examples/reasoning-corpus.json').read_text())
        self.corpus['papers'][1]['observations'][0].update(
            stance='challenge', claim_type='operator_interpretation')
        self.package = build(self.corpus)

    def test_default_observation_labels_do_not_borrow_component_labels(self):
        text = render(self.package, 'Which method?', 'model design')
        self.assertIn('rule-1 | synthetic-0 | research 2020 | synthetic section 1 | claim_type=explicit_statement', text)
        self.assertIn('rule-2 | synthetic-1 | review 2021 | synthetic section 1 | claim_type=operator_interpretation', text)
        self.assertNotIn('Component reference:', text)

    def test_global_complete_does_not_fill_individual_gaps(self):
        first = self.corpus['papers'][0]['observations'][0]
        second = self.corpus['papers'][1]['observations'][0]
        record = copy.deepcopy(first['reasoning']['uncertainty'])
        second['reasoning'] = {d: copy.deepcopy(record) for d in DIMENSIONS if d not in first['reasoning']}
        text = render(build(self.corpus), 'Which method?', 'model design', evidence_details=True)
        self.assertIn('Missing supplied records: none (coverage only)', text)
        self.assertIn('Missing for this observation: question_framing, evidence_standard, falsification_check', text)
        self.assertIn('Missing for this observation: alternative_explanation, uncertainty', text)
        self.assertIn('Per-observation gaps are not filled by another paper', text)

    def test_original_indices_and_observation_topic_not_paper_topic(self):
        paper = self.corpus['papers'][0]
        other = copy.deepcopy(paper['observations'][0])
        other.update(topic='other', method='UNRELATED_METHOD')
        paper['observations'].insert(0, other)
        paper['topic'] = 'different paper topic'
        text = render(build(self.corpus), 'Which method?', 'MODEL DESIGN', evidence_details=True)
        self.assertIn('"observation_index": 1, "paper_id": "synthetic-0"', text)
        self.assertNotIn('UNRELATED_METHOD', text)
        self.assertNotIn('"observation_index": 0, "paper_id": "synthetic-0"', text)
        self.assertIn('Evidence: 2 paper IDs', text)

    def test_no_reasoning_and_missing_quote_are_explicit(self):
        obs = self.corpus['papers'][1]['observations'][0]
        obs.pop('evidence_quote')
        text = render(build(self.corpus), 'Which method?', 'model design', evidence_details=True)
        self.assertIn('evidence_quote: [NOT_SUPPLIED]', text)
        self.assertIn('Missing for this observation: ' + ', '.join(DIMENSIONS), text)
        self.assertIn('recorded quote check: NOT_PERFORMED', text)

    def test_all_mock_provenance_survives_with_reviewed_claim_label(self):
        component = self.corpus['papers'][0]['observations'][0]['reasoning']['uncertainty']
        component.update(claim_type='operator_interpretation', origin='operator_reviewed_mock_candidate',
                         candidate_id='fixture-candidate', candidate_bundle_sha256='a' * 64,
                         operator_review_sha256='b' * 64, proposed_claim_type='explicit_statement')
        text = render(build(self.corpus), 'Which method?', 'model design', evidence_details=True)
        for key in REVIEW_FIELDS:
            self.assertIn(key + ': ' + component[key], text)
        self.assertIn('claim_type: operator_interpretation', text)
        self.assertIn('Bindings: persona_payload_sha256=', text)

    def test_readonly_no_source_io_wrapper_is_not_authoritative(self):
        before = copy.deepcopy(self.package)
        with patch('pathlib.Path.open', side_effect=AssertionError('No source reread')):
            text = render(dict(package=self.package, application={'status': 'APPROVED'}), 'Which?',
                          'model design', evidence_details=True)
        self.assertNotIn('APPROVED', text)
        self.assertEqual(before, self.package)
        self.assertIn('not authenticated author claims', text)

    def test_unmatched_and_control_fields(self):
        text = render(self.package, 'Which?', 'missing', evidence_details=True)
        self.assertIn('No topic-matched observations', text)
        self.assertNotIn('Reference:', text)
        self.corpus['papers'][0]['observations'][0]['limitation'] = 'LIMIT\nFORGED\u2028ENTRY'
        text = render(build(self.corpus), 'Which?', 'model design', evidence_details=True)
        self.assertIn('LIMIT\\u000aFORGED\\u2028ENTRY', text)
        self.assertNotIn('FORGED', text.splitlines())

    def test_real_synthetic_journey_to_source_detail_review(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / 'journey'
            result = subprocess.run([sys.executable, 'synthetic_walkthrough.py', str(destination)],
                                    capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stderr)
            complete = json.loads((destination / 'COMPLETE.json').read_text())
            self.assertFalse(complete['llm_used'])
            revision_path = destination / 'revision.json'
            revision_bytes = revision_path.read_bytes()
            result = subprocess.run([sys.executable, 'review_package.py', str(revision_path),
                '--question', 'Which explanation guides the synthetic comparison?',
                '--topic', 'model design', '--evidence-details'],
                capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(revision_bytes, revision_path.read_bytes())
            for token in ('CONTESTED:', 'claim_type: operator_interpretation',
                          'proposed_claim_type: explicit_statement',
                          'Missing for this observation: question_framing, evidence_standard, falsification_check',
                          'Source: review 2021', 'candidate_bundle_sha256:',
                          'not relevance ranking or method selection'):
                self.assertIn(token, result.stdout)

    def test_cli_details_and_rehashed_holdout_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'package.json'
            path.write_text(json.dumps(self.package))
            command = [sys.executable, 'review_package.py', str(path), '--question', 'Which synthetic method?',
                       '--topic', 'model design', '--evidence-details']
            result = subprocess.run(command, capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('Component reference:', result.stdout)
            self.package['knowledge']['papers'][1]['split'] = 'holdout'
            self.package['persona']['knowledge_papers_sha256'] = payload_sha256(self.package['knowledge']['papers'])
            self.package['knowledge']['persona_payload_sha256'] = payload_sha256(self.package['persona'])
            path.write_text(json.dumps(self.package))
            result = subprocess.run(command, capture_output=True, text=True, timeout=20)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, '')


if __name__ == '__main__':
    unittest.main()
