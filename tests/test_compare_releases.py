import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from compare_releases import compare
from persona import payload_sha256
from research_workflow import build


class ReleaseComparisonTests(unittest.TestCase):
    def setUp(self):
        self.corpus = json.loads(Path('examples/research-corpus.json').read_text())
        self.previous = build(self.corpus)

    def test_identical_release_and_wrapped_cli_output(self):
        result = compare(self.previous, {'package': self.previous, 'application': {}})
        self.assertEqual(result['status'], 'NO_EVIDENCE_OR_RULE_CHANGE')
        self.assertFalse(result['canonical_update_performed'])

    def test_build_metadata_change_is_not_evidence_change(self):
        self.corpus['version'] = '2'
        self.corpus['build_id'] = 'new-build'
        result = compare(self.previous, build(self.corpus))
        self.assertFalse(result['evidence_changed'])
        self.assertFalse(result['rule_payload_changed'])
        self.assertNotEqual(result['previous']['persona_sha256'], result['candidate']['persona_sha256'])

    def test_new_and_removed_papers_are_separate(self):
        self.corpus['papers'][1]['paper_id'] = 'synthetic-new'
        result = compare(self.previous, build(self.corpus))
        self.assertEqual(result['added_paper_ids'], ['synthetic-new'])
        self.assertEqual(result['removed_paper_ids'], ['synthetic-1'])
        self.assertEqual(result['status'], 'REVIEW_REQUIRED')

    def test_source_change_does_not_assert_retraction(self):
        self.corpus['papers'][0]['source_sha256'] = 'e' * 64
        result = compare(self.previous, build(self.corpus))
        change = result['modified_papers'][0]
        self.assertTrue(change['source_hash_changed'])
        self.assertFalse(change['observations_changed'])
        self.assertIn('no inferred change of mind', result['boundary'])

    def test_observation_change_triggers_review(self):
        self.corpus['papers'][0]['observations'][0]['stance'] = 'challenge'
        result = compare(self.previous, build(self.corpus))
        self.assertTrue(result['modified_papers'][0]['observations_changed'])
        self.assertTrue(result['rule_payload_changed'])

    def test_identity_mismatch_rejected(self):
        self.corpus['author_id'] = 'other-synthetic-scholar'
        for paper in self.corpus['papers']:
            paper['author_id'] = self.corpus['author_id']
        with self.assertRaisesRegex(ValueError, 'same scholarly identity'):
            compare(self.previous, build(self.corpus))

    def test_tampered_or_legacy_package_rejected(self):
        changed = copy.deepcopy(self.previous)
        changed['knowledge']['papers'][0]['year'] = 1900
        with self.assertRaisesRegex(ValueError, 'payload hash mismatch'):
            compare(self.previous, changed)
        legacy = copy.deepcopy(self.previous)
        del legacy['persona']['knowledge_papers_sha256']
        legacy['knowledge']['persona_payload_sha256'] = payload_sha256(legacy['persona'])
        with self.assertRaisesRegex(ValueError, 'bound knowledge'):
            compare(self.previous, legacy)

    def test_comparison_does_not_mutate_inputs(self):
        original = copy.deepcopy(self.previous)
        self.assertEqual(compare(self.previous, self.previous), compare(self.previous, self.previous))
        self.assertEqual(self.previous, original)

    def test_json_numeric_types_are_structurally_distinct(self):
        candidate = copy.deepcopy(self.previous)
        candidate['persona']['rules'][0]['year'] = 2020.0
        candidate['knowledge']['persona_payload_sha256'] = payload_sha256(candidate['persona'])
        result = compare(self.previous, candidate)
        self.assertTrue(result['rule_payload_changed'])
        self.assertEqual(result['status'], 'REVIEW_REQUIRED')
        candidate = copy.deepcopy(self.previous)
        candidate['knowledge']['papers'][0]['year'] = 2020.0
        candidate['persona']['knowledge_papers_sha256'] = payload_sha256(candidate['knowledge']['papers'])
        candidate['knowledge']['persona_payload_sha256'] = payload_sha256(candidate['persona'])
        result = compare(self.previous, candidate)
        self.assertTrue(result['evidence_changed'])
        self.assertEqual(result['modified_papers'][0]['changed_fields'], ['year'])

    def test_cli_success_and_invalid_input(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'release.json'
            path.write_text(json.dumps(self.previous))
            cmd = [sys.executable, 'compare_releases.py', str(path), str(path)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['status'], 'NO_EVIDENCE_OR_RULE_CHANGE')
            path.write_text('{}')
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn('Traceback', result.stderr)


if __name__ == '__main__':
    unittest.main()
