import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from compare_releases import compare
from extraction_adapter import MockProvider
from observation_input import verified_corpus
from persona import payload_sha256
from publication_timeline import timeline
from research_workflow import apply, build
from review_package import render


class RuleSourceConsistencyTests(unittest.TestCase):
    def setUp(self):
        self.corpus = json.loads(Path('examples/reasoning-corpus.json').read_text())
        self.package = build(verified_corpus(self.corpus))

    def rebind(self, package):
        if 'knowledge_papers_sha256' in package['persona']:
            package['persona']['knowledge_papers_sha256'] = payload_sha256(package['knowledge']['papers'])
        package['knowledge']['persona_payload_sha256'] = payload_sha256(package['persona'])
        return package

    def assert_views_reject(self, package):
        for reader in (lambda p: apply(p, 'Which synthetic model?', 'model design'),
                       lambda p: render(p, 'Which synthetic model?', 'model design'),
                       lambda p: timeline(p, 'model design')):
            with self.assertRaises(ValueError):
                reader(package)

    def test_rehashed_rule_mismatches_reject_even_outside_selected_topic(self):
        for field, value in [('method', 'SYNTHETIC_INVENTED_METHOD'), ('year', 2020.0),
            ('source_kind', 'review'), ('paper_id', 'synthetic-1'), ('locator', 'fabricated locator'),
            ('stance', 'challenge'), ('claim_type', 'operator_interpretation'),
            ('evidence_quote', 'fabricated quote'), ('topic', 'unmatched topic')]:
            bad = copy.deepcopy(self.package)
            bad['persona']['rules'][0][field] = value
            self.assert_views_reject(self.rebind(bad))

    def test_source_changes_and_added_removed_reordered_rules_require_rebuild(self):
        for mode in ('source', 'added', 'removed', 'reordered'):
            bad = copy.deepcopy(self.package)
            if mode == 'source':
                bad['knowledge']['papers'][0]['observations'][0]['method'] = 'different synthetic method'
            elif mode == 'added':
                bad['persona']['rules'].append(copy.deepcopy(bad['persona']['rules'][0]))
            elif mode == 'removed':
                bad['persona']['rules'].pop()
            else:
                bad['persona']['rules'].reverse()
            self.assert_views_reject(self.rebind(bad))

    def test_recorded_quote_labels_must_agree_without_upgrading_checks(self):
        raw = build(self.corpus)
        for target in ('observation', 'component'):
            bad = copy.deepcopy(raw)
            rule = bad['persona']['rules'][0]
            if target == 'component':
                rule = rule['reasoning']['uncertainty']
            rule['evidence_verification'] = 'EXACT_QUOTE_MATCH_ONLY'
            self.assert_views_reject(self.rebind(bad))
        for package, expected in ((raw, 'NOT_PERFORMED'), (self.package, 'EXACT_QUOTE_MATCH_ONLY')):
            result = apply(package, 'Question', 'model design')
            self.assertEqual(result['steps'][0]['evidence_verification'], expected)
            self.assertEqual(result['reasoning_cards'][0]['components']['uncertainty']['evidence_verification'], expected)

    def test_comparison_can_diagnose_a_candidate_without_approving_runtime_use(self):
        bad = copy.deepcopy(self.package)
        bad['persona']['rules'][0]['method'] = 'SYNTHETIC_INVENTED_METHOD'
        self.rebind(bad)
        self.assertEqual(compare(self.package, bad)['status'], 'REVIEW_REQUIRED')
        self.assert_views_reject(bad)

    def test_application_rebuilds_trajectory_instead_of_relaying_cached_summary(self):
        bad = copy.deepcopy(self.package)
        bad['persona']['trajectory'] = [{'year': 2099, 'paper_id': 'SYNTHETIC_FORGED_TRAJECTORY'}]
        self.rebind(bad)
        result = apply(bad, 'Question', 'model design')
        self.assertEqual(result['trajectory'], apply(self.package, 'Question', 'model design')['trajectory'])
        self.assertNotIn('SYNTHETIC_FORGED_TRAJECTORY', json.dumps(result))
        result['trajectory'][0]['year'] = 1900
        self.assertEqual(self.package['knowledge']['papers'][0]['year'], 2020)

    def test_consistency_check_is_read_only_without_provider_or_source_file_reads(self):
        before = copy.deepcopy(self.package)
        with patch.object(MockProvider, 'extract', side_effect=AssertionError('provider called')), \
             patch.object(Path, 'read_text', side_effect=AssertionError('source file opened')):
            apply(self.package, 'Question', 'model design')
            render(self.package, 'Question', 'model design')
            timeline(self.package, 'model design')
        self.assertEqual(self.package, before)
        legacy = copy.deepcopy(self.package)
        del legacy['persona']['knowledge_papers_sha256']
        self.rebind(legacy)
        self.assertEqual(apply(legacy, 'Question', 'model design')['status'], 'PLANNING_SCAFFOLD')
        legacy['persona']['rules'][0]['method'] = 'SYNTHETIC_INVENTED_METHOD'
        self.assert_views_reject(self.rebind(legacy))

    def test_actual_cli_rejects_inconsistent_candidate_without_partial_stdout(self):
        bad = copy.deepcopy(self.package)
        bad['persona']['rules'][0]['year'] = 2099
        self.rebind(bad)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'candidate.json'
            path.write_text(json.dumps(bad))
            for script, extra in (('review_package.py', ['--question', 'Question']),
                                  ('publication_timeline.py', [])):
                result = subprocess.run([sys.executable, script, str(path), '--topic', 'model design', *extra],
                    capture_output=True, text=True, timeout=20)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, '')
                self.assertIn('do not match', result.stderr)


if __name__ == '__main__':
    unittest.main()
