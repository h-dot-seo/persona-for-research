import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from extraction_adapter import MockProvider
from observation_input import verified_corpus
from persona import payload_sha256
from publication_timeline import timeline, render
from research_workflow import build


class PublicationTimelineTests(unittest.TestCase):
    def setUp(self):
        self.corpus = json.loads(Path('examples/reasoning-corpus.json').read_text())
        first = self.corpus['papers'][0]
        first['observations'][0]['reasoning']['question_framing'] = dict(
            text='Which synthetic model fits?', locator='synthetic reasoning',
            evidence_quote='Compare explanations.', claim_type='operator_interpretation')
        second = self.corpus['papers'][1]
        second['year'] = 2024
        second['observations'][0]['stance'] = 'challenge'
        third = copy.deepcopy(second)
        third['paper_id'] = 'synthetic-2'
        third['kind'] = 'research'
        third['observations'][0]['stance'] = 'support'
        self.corpus['papers'].append(third)
        self.package = build(verified_corpus(self.corpus))

    def rebind(self, package):
        package['persona']['knowledge_papers_sha256'] = payload_sha256(package['knowledge']['papers'])
        package['knowledge']['persona_payload_sha256'] = payload_sha256(package['persona'])
        return package

    def test_years_keep_support_challenge_source_kinds_and_duplicates(self):
        result = timeline(self.package, 'MODEL DESIGN')
        self.assertEqual([year['publication_year'] for year in result['years']], [2020, 2024])
        later = result['years'][1]['papers']
        self.assertEqual([p['source_kind'] for p in later], ['review', 'research'])
        self.assertEqual([p['observations'][0]['stance'] for p in later], ['challenge', 'support'])
        self.assertEqual(result['paper_count'], 3)
        self.assertEqual(result['supplied_source_hash_count'], 2)
        self.assertFalse(result['llm_used'])
        self.assertFalse(result['canonical_update_performed'])

    def test_question_claim_and_locator_belong_only_to_their_observation(self):
        result = timeline(self.package, 'model design')
        first = result['years'][0]['papers'][0]['observations'][0]
        self.assertEqual(first['claim_type'], 'explicit_statement')
        framing = first['reasoning']['question_framing']
        self.assertEqual(framing['claim_type'], 'operator_interpretation')
        self.assertNotEqual(first['locator'], framing['locator'])
        for later in result['years'][1]['papers']:
            self.assertIn('question_framing', later['observations'][0]['missing_dimensions'])
            self.assertNotIn('question_framing', later['observations'][0]['reasoning'])
        self.assertNotIn('question_framing', result['missing_dimensions'])
        self.assertIn('falsification_check', result['missing_dimensions'])

    def test_topic_filter_applies_to_all_counts_and_empty_results(self):
        empty = timeline(self.package, 'unrelated synthetic topic')
        self.assertEqual(empty['status'], 'NO_MATCHING_RECORDS')
        self.assertEqual(empty['years'], [])
        self.assertEqual(empty['paper_count'], 0)
        self.assertEqual(empty['supplied_source_hash_count'], 0)
        self.assertEqual(len(empty['missing_dimensions']), 5)
        for bad in ('', ' ', None):
            with self.assertRaises(ValueError):
                timeline(self.package, bad)

    def test_bindings_authorization_and_inconsistent_rules_fail(self):
        bad = copy.deepcopy(self.package)
        bad['knowledge']['papers'][0]['year'] = 1999
        with self.assertRaises(ValueError):
            timeline(bad, 'model design')
        for field, value in [('authorized', False), ('split', 'holdout')]:
            bad = copy.deepcopy(self.package)
            bad['knowledge']['papers'][0][field] = value
            with self.assertRaises(ValueError):
                timeline(self.rebind(bad), 'model design')
        for field, value in [('paper_id', 'unknown-source'), ('year', 1999),
                             ('source_kind', 'review'), ('method', 'invented method')]:
            bad = copy.deepcopy(self.package)
            bad['persona']['rules'][0][field] = value
            with self.assertRaises(ValueError):
                timeline(self.rebind(bad), 'model design')

    def test_no_raw_metadata_saved_summary_mutation_or_provider_use(self):
        bad = copy.deepcopy(self.package)
        bad['knowledge']['papers'][0]['hidden_note'] = 'SYNTHETIC_UNLISTED_MARKER'
        bad['knowledge']['papers'][0]['segments'] = {'section': 'SYNTHETIC_RAW_MARKER'}
        bad['persona']['trajectory'] = ['SYNTHETIC_FORGED_SUMMARY']
        self.rebind(bad)
        wrapper = dict(package=bad, application={'invented': 'SYNTHETIC_FORGED_SUMMARY'})
        before = copy.deepcopy(wrapper)
        with patch.object(MockProvider, 'extract', side_effect=AssertionError('provider called')):
            result = timeline(wrapper, 'model design')
        output = json.dumps(result)
        for marker in ('SYNTHETIC_UNLISTED_MARKER', 'SYNTHETIC_RAW_MARKER', 'SYNTHETIC_FORGED_SUMMARY'):
            self.assertNotIn(marker, output)
        self.assertEqual(wrapper, before)
        result['years'][0]['papers'][0]['observations'][0]['reasoning'].clear()
        self.assertEqual(wrapper, before)

    def test_recorded_labels_are_not_reverification_or_nested_data(self):
        result = timeline(self.package, 'model design')
        first = result['years'][0]['papers'][0]['observations'][0]
        self.assertEqual(first['recorded_quote_check'], 'EXACT_QUOTE_MATCH_ONLY')
        self.assertIn('not rechecked here', result['boundary'])
        raw_text = render(build(self.corpus), 'model design')
        checked_text = render(self.package, 'model design')
        self.assertNotEqual(raw_text, checked_text)
        self.assertIn('recorded quote check: NOT_PERFORMED', raw_text)
        self.assertIn('recorded quote check: EXACT_QUOTE_MATCH_ONLY', checked_text)
        self.assertIn('recorded source check: NOT_PERFORMED', checked_text)
        self.assertIn('not rechecked here', checked_text)
        for target in ('paper', 'observation', 'component'):
            bad = copy.deepcopy(self.package)
            paper = bad['knowledge']['papers'][0]
            obs = paper['observations'][0]
            if target == 'paper':
                paper['source_verification'] = {'unlisted': 'SYNTHETIC_NESTED_MARKER'}
            elif target == 'observation':
                obs['evidence_verification'] = {'unlisted': 'SYNTHETIC_NESTED_MARKER'}
            else:
                obs['reasoning']['question_framing']['evidence_verification'] = {'unlisted': 'SYNTHETIC_NESTED_MARKER'}
            with self.assertRaises(ValueError):
                timeline(self.rebind(bad), 'model design')

    def test_chronology_order_does_not_depend_on_paper_input_order(self):
        reverse = copy.deepcopy(self.corpus)
        reverse['papers'].reverse()
        other = build(verified_corpus(reverse))
        self.assertEqual(timeline(self.package, 'model design')['years'],
                         timeline(other, 'model design')['years'])

    def test_cli_roundtrip_text_json_and_failure_without_partial_output(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'corpus.json'
            target = Path(directory) / 'package.json'
            source.write_text(json.dumps(self.corpus))
            intake = subprocess.run([sys.executable, 'observation_input.py', str(source),
                '--question', 'Which synthetic model?', '--topic', 'model design'],
                capture_output=True, text=True, timeout=20)
            self.assertEqual(intake.returncode, 0, intake.stderr)
            target.write_text(intake.stdout)
            args = [sys.executable, 'publication_timeline.py', str(target), '--topic', 'model design']
            output = subprocess.run(args, capture_output=True, text=True, timeout=20)
            self.assertEqual(output.returncode, 0, output.stderr)
            result = json.loads(output.stdout)
            text = subprocess.run(args + ['--format', 'text'], capture_output=True, text=True, timeout=20)
            self.assertEqual(text.returncode, 0, text.stderr)
            for year in result['years']:
                for paper in year['papers']:
                    self.assertIn(paper['paper_id'], text.stdout)
                    self.assertIn(paper['source_sha256'], text.stdout)
            self.assertIn('question_framing [operator_interpretation]', text.stdout)
            target.write_text('{"package": 1}')
            failed = subprocess.run(args, capture_output=True, text=True, timeout=20)
            self.assertNotEqual(failed.returncode, 0)
            self.assertEqual(failed.stdout, '')

    def test_text_escapes_controls_and_preserves_unicode(self):
        self.corpus['papers'][0]['observations'][0]['method'] = '합성 방법\nFAKE\x1b[31m'
        package = build(verified_corpus(self.corpus))
        text = render(package, 'model design')
        self.assertIn('합성 방법\\u000aFAKE\\u001b[31m', text)
        self.assertNotIn('\x1b', text)
        self.assertNotIn('\nFAKE', text)


if __name__ == '__main__':
    unittest.main()
