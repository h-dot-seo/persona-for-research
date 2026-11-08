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
from publication_timeline import timeline
from research_workflow import build
from topic_inventory import inventory, render


class TopicInventoryTests(unittest.TestCase):
    def setUp(self):
        self.corpus = json.loads(Path('examples/reasoning-corpus.json').read_text())
        self.corpus['papers'][0]['observations'][0]['topic'] = 'Model Design'
        self.corpus['papers'][1]['observations'][0]['topic'] = 'MODEL DESIGN'
        self.corpus['papers'][1]['observations'][0]['stance'] = 'challenge'
        self.package = build(verified_corpus(self.corpus))

    def rebind(self, package):
        package['persona']['knowledge_papers_sha256'] = payload_sha256(package['knowledge']['papers'])
        package['knowledge']['persona_payload_sha256'] = payload_sha256(package['persona'])
        return package

    def test_casefold_groups_preserve_counts_claims_and_component_availability(self):
        result = inventory(self.package)
        self.assertEqual(len(result['topics']), 1)
        row = result['topics'][0]
        self.assertEqual(row['topic'], 'model design')
        self.assertEqual(row['original_labels'], ['MODEL DESIGN', 'Model Design'])
        self.assertEqual(row['stance_counts'], dict(support=1, challenge=1))
        self.assertEqual(row['claim_type_counts'], dict(explicit_statement=2, operator_interpretation=0))
        self.assertEqual(row['supplied_component_counts']['uncertainty'], 1)
        self.assertIn('question_framing', row['missing_dimensions'])
        self.assertEqual(row['paper_ids_by_kind'], dict(research=['synthetic-0'], review=['synthetic-1']))
        self.assertFalse(result['selection_performed'])
        self.assertFalse(result['llm_used'])
        for paper, label in zip(self.corpus['papers'], ('Straße', 'STRASSE')):
            paper['observations'][0]['topic'] = label
        self.assertEqual([row['topic'] for row in inventory(build(verified_corpus(self.corpus)))['topics']], ['strasse'])

    def test_related_or_whitespace_topics_not_semantically_merged(self):
        for name in ('model-design', 'model design '):
            other = copy.deepcopy(self.corpus)
            other['papers'][1]['observations'][0]['topic'] = name
            result = inventory(build(verified_corpus(other)))
            self.assertEqual(len(result['topics']), 2)
            self.assertIn(name, [row['topic'] for row in result['topics']])

    def test_source_observations_not_paper_topics_or_unlisted_metadata_drive_output(self):
        package = copy.deepcopy(self.package)
        paper = package['knowledge']['papers'][0]
        paper['topic'] = 'SYNTHETIC_PAPER_ONLY_TOPIC'
        paper['hidden'] = 'SYNTHETIC_UNLISTED_NOTE'
        paper['segments'] = {'section': 'SYNTHETIC_RAW_TEXT'}
        self.rebind(package)
        result = inventory(package)
        for marker in ('SYNTHETIC_PAPER_ONLY_TOPIC', 'SYNTHETIC_UNLISTED_NOTE', 'SYNTHETIC_RAW_TEXT'):
            self.assertNotIn(marker, json.dumps(result))
        for paper in self.corpus['papers']:
            paper['observations'] = []
        empty = inventory(build(self.corpus))
        self.assertEqual(empty['status'], 'NO_OBSERVATION_TOPICS')
        self.assertEqual(empty['topics'], [])

    def test_inventory_scope_agrees_with_timeline_and_keeps_duplicate_sources(self):
        self.corpus['papers'][1]['source_sha256'] = self.corpus['papers'][0]['source_sha256']
        package = build(verified_corpus(self.corpus))
        row = inventory(package)['topics'][0]
        self.assertEqual(row['supplied_source_hash_count'], 1)
        view = timeline(package, row['topic'])
        self.assertEqual(view['paper_count'], 2)
        self.assertEqual(view['supplied_source_hash_count'], row['supplied_source_hash_count'])
        refs = [dict(paper_id=p['paper_id'], observation_index=obs['observation_index'], locator=obs['locator'],
                     stance=obs['stance'], claim_type=obs['claim_type'],
                     supplied_dimensions=[d for d in row['supplied_component_counts'] if d in obs['reasoning']])
                for year in view['years'] for p in year['papers'] for obs in p['observations']]
        self.assertEqual(row['observation_refs'], refs)

    def test_one_paper_can_contribute_multiple_topics_and_both_stances(self):
        first = self.corpus['papers'][0]
        duplicate = copy.deepcopy(first['observations'][0])
        duplicate['stance'] = 'challenge'
        first['observations'].append(duplicate)
        other = copy.deepcopy(duplicate)
        other['topic'] = 'another synthetic topic'
        other.pop('reasoning')
        first['observations'].append(other)
        package = build(verified_corpus(self.corpus))
        for row in inventory(package)['topics']:
            view = timeline(package, row['topic'])
            self.assertEqual(row['observation_count'], sum(len(p['observations']) for y in view['years'] for p in y['papers']))
            self.assertEqual(len(row['paper_ids_by_kind']['research']), 1)
            if row['topic'] == 'model design':
                self.assertEqual(row['stance_counts'], dict(support=1, challenge=2))
                self.assertEqual(row['supplied_component_counts']['uncertainty'], 2)
            else:
                self.assertEqual(row['supplied_component_counts']['uncertainty'], 0)

    def test_invalid_binding_rules_and_unauthorized_sources_rejected(self):
        for mode in ('binding', 'rules', 'holdout'):
            bad = copy.deepcopy(self.package)
            if mode == 'binding':
                bad['knowledge']['papers'][0]['year'] = 2001
            elif mode == 'rules':
                bad['persona']['rules'][0]['method'] = 'invented method'
                self.rebind(bad)
            else:
                bad['knowledge']['papers'][0]['split'] = 'holdout'
                self.rebind(bad)
            with self.assertRaises(ValueError):
                inventory(bad)

    def test_read_only_and_text_control_unicode_boundaries(self):
        self.corpus['papers'][0]['observations'][0]['topic'] = '합성\nFAKE\x1b[31m'
        package = build(verified_corpus(self.corpus))
        before = copy.deepcopy(package)
        with patch.object(MockProvider, 'extract', side_effect=AssertionError('provider called')), \
             patch.object(Path, 'read_text', side_effect=AssertionError('source opened')):
            result = inventory(package)
            text = render(package)
        self.assertEqual(package, before)
        self.assertIn('합성', text)
        self.assertNotIn('\nFAKE', text)
        self.assertNotIn('\x1b', text)
        result['topics'].clear()
        self.assertEqual(package, before)

    def test_actual_cli_discovery_to_timeline_and_review(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, package = root / 'source.json', root / 'package.json'
            source.write_text(json.dumps(self.corpus))
            intake = subprocess.run([sys.executable, 'observation_input.py', str(source),
                '--question', 'Which synthetic model?', '--topic', 'model design'],
                capture_output=True, text=True, timeout=20)
            self.assertEqual(intake.returncode, 0, intake.stderr)
            package.write_text(intake.stdout)
            args = [sys.executable, 'topic_inventory.py', str(package)]
            output = subprocess.run(args, capture_output=True, text=True, timeout=20)
            self.assertEqual(output.returncode, 0, output.stderr)
            topic = json.loads(output.stdout)['topics'][0]['topic']
            for script, extras in (('publication_timeline.py', ['--format', 'text']),
                                   ('review_package.py', ['--question', 'Which synthetic model?'])):
                result = subprocess.run([sys.executable, script, str(package), '--topic', topic, *extras],
                    capture_output=True, text=True, timeout=20)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('synthetic-0', result.stdout)
                self.assertIn('synthetic-1', result.stdout)
            text = subprocess.run(args + ['--format', 'text'], capture_output=True, text=True, timeout=20)
            self.assertEqual(text.returncode, 0, text.stderr)
            self.assertIn('Topic: "model design"', text.stdout)
            package.write_text('{"package": 1}')
            failed = subprocess.run(args, capture_output=True, text=True, timeout=20)
            self.assertNotEqual(failed.returncode, 0)
            self.assertEqual(failed.stdout, '')


if __name__ == '__main__':
    unittest.main()
