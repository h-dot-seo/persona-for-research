import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from compare_releases import compare
from extraction_adapter import MockProvider, extract_candidates
from observation_input import verified_corpus
from operator_review import prepare_revision, review_template, target_inventory
from persona import payload_sha256
from research_workflow import build
from review_package import render


class OperatorReviewTests(unittest.TestCase):
    def setUp(self):
        self.corpus = json.loads(Path('examples/reasoning-corpus.json').read_text())
        del self.corpus['papers'][0]['observations'][0]['reasoning']
        self.response = json.loads(Path('examples/mock-extraction-response.json').read_text())
        self.bind()

    def bind(self):
        self.bundle = extract_candidates(self.corpus, MockProvider(self.response))
        self.review = dict(candidate_bundle_sha256=payload_sha256(self.bundle),
            input_corpus_sha256=payload_sha256(self.corpus), reviewer_id='synthetic-reviewer',
            decisions=[dict(candidate_id=c['candidate_id'], decision='accept',
                review_note='Synthetic review decision; no real researcher evaluation.',
                target_rule_id='rule-1', target_paper_id='synthetic-0', operation='add',
                expected_component_sha256=None, reviewed_text=c['candidate_text'],
                reviewed_claim_type='operator_interpretation') for c in self.bundle['candidates']])

    def run_review(self):
        return prepare_revision(self.corpus, self.bundle, self.review, '2', 'synthetic-revision')

    def test_review_creates_separate_candidate_with_provenance(self):
        originals = copy.deepcopy((self.corpus, self.bundle, self.review))
        previous = build(verified_corpus(self.corpus))
        result = self.run_review()
        self.assertEqual(result['status'], 'REVIEWED_REVISION_CANDIDATE')
        self.assertFalse(result['canonical_update_performed'])
        self.assertEqual(result['reviewer_identity'], 'RECORDED_NOT_AUTHENTICATED')
        component = result['package']['persona']['rules'][0]['reasoning']['uncertainty']
        self.assertEqual(component['claim_type'], 'operator_interpretation')
        self.assertEqual(component['proposed_claim_type'], 'explicit_statement')
        self.assertEqual(component['origin'], 'operator_reviewed_mock_candidate')
        self.assertEqual(component['operator_review_sha256'], payload_sha256(self.review))
        self.assertNotIn('segments', result['package']['knowledge']['papers'][0])
        self.assertIn('proposed=explicit_statement', render(result, 'Question', 'model design'))
        self.assertEqual(compare(previous, result)['status'], 'REVIEW_REQUIRED')
        self.assertEqual((self.corpus, self.bundle, self.review), originals)

    def test_review_does_not_invoke_provider(self):
        with patch.object(MockProvider, 'extract', side_effect=AssertionError('provider called')):
            self.run_review()

    def test_inventory_keeps_all_same_paper_targets_without_selecting(self):
        challenge = copy.deepcopy(self.corpus['papers'][0]['observations'][0])
        challenge['stance'] = 'challenge'
        challenge['topic'] = 'different synthetic topic'
        self.corpus['papers'][0]['observations'].append(challenge)
        self.bind()
        before = copy.deepcopy((self.corpus, self.bundle))
        with patch.object(MockProvider, 'extract', side_effect=AssertionError('provider called')):
            inventory = target_inventory(self.corpus, self.bundle)
        self.assertFalse(inventory['selection_performed'])
        self.assertNotIn('package', inventory)
        for row in inventory['candidates']:
            self.assertEqual([t['target_rule_id'] for t in row['targets']], ['rule-1', 'rule-2'])
            self.assertEqual([t['observation']['stance'] for t in row['targets']], ['support', 'challenge'])
            self.assertEqual(row['targets'][1]['observation']['topic'], 'different synthetic topic')
            self.assertTrue(all(t['occupancy'] == 'EMPTY' for t in row['targets']))
            self.assertTrue(all(t['expected_component_sha256'] is None for t in row['targets']))
            self.assertTrue(all('operation' not in t and 'decision' not in t for t in row['targets']))
        self.assertEqual((self.corpus, self.bundle), before)
        inventory['candidates'][0]['targets'][0]['observation']['method'] = 'modified output'
        self.assertEqual((self.corpus, self.bundle), before)
        self.corpus['papers'][0]['observations'][0]['reasoning'] = {}
        challenge['reasoning'] = self.corpus['papers'][0]['observations'][0]['reasoning']
        self.bind()
        self.assertEqual(target_inventory(self.corpus, self.bundle),
                         target_inventory(json.loads(json.dumps(self.corpus)), self.bundle))

    def test_inventory_full_prior_hash_and_projected_component_support_replace(self):
        self.corpus = json.loads(Path('examples/reasoning-corpus.json').read_text())
        raw = self.corpus['papers'][0]['observations'][0]['reasoning']['uncertainty']
        raw['unlisted_synthetic_note'] = 'SYNTHETIC_HIDDEN_MARKER'
        self.bind()
        inventory = target_inventory(self.corpus, self.bundle)
        self.assertNotIn('SYNTHETIC_HIDDEN_MARKER', json.dumps(inventory))
        self.assertNotIn('segments', json.dumps(inventory))
        for decision, row in zip(self.review['decisions'], inventory['candidates']):
            target = row['targets'][0]
            self.assertEqual(target['occupancy'], 'OCCUPIED')
            prior = self.corpus['papers'][0]['observations'][0]['reasoning'][row['dimension']]
            self.assertEqual(target['expected_component_sha256'], payload_sha256(prior))
            decision['operation'] = 'replace'
            decision['expected_component_sha256'] = target['expected_component_sha256']
        self.assertEqual(self.run_review()['status'], 'REVIEWED_REVISION_CANDIDATE')

    def test_inventory_stale_inputs_and_unauthorized_sources_fail(self):
        for field, value in [('authorized', False), ('split', 'holdout')]:
            corpus = copy.deepcopy(self.corpus)
            corpus['papers'][1][field] = value
            with self.assertRaises(ValueError):
                target_inventory(corpus, self.bundle)
        stale = copy.deepcopy(self.corpus)
        stale['papers'][0]['observations'][0]['method'] = 'changed synthetic method'
        with self.assertRaises(ValueError):
            target_inventory(stale, self.bundle)
        bundle = copy.deepcopy(self.bundle)
        bundle['candidates'][0]['candidate_text'] += ' altered'
        changed = target_inventory(self.corpus, bundle)
        self.assertNotEqual(changed['candidate_bundle_sha256'], payload_sha256(self.bundle))
        bundle['candidates'][0]['evidence_quote'] = 'fabricated synthetic quote'
        with self.assertRaises(ValueError):
            target_inventory(self.corpus, bundle)

    def test_inventory_empty_targets_do_not_create_an_observation(self):
        self.corpus['papers'][0]['observations'] = []
        self.bind()
        inventory = target_inventory(self.corpus, self.bundle)
        self.assertTrue(all(row['targets'] == [] for row in inventory['candidates']))
        self.assertFalse(inventory['selection_performed'])

    def test_inventory_cli_and_incompatible_modes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            corpus, bundle = root / 'corpus.json', root / 'bundle.json'
            corpus.write_text(json.dumps(self.corpus))
            bundle.write_text(json.dumps(self.bundle))
            args = [sys.executable, 'operator_review.py', str(corpus), str(bundle), '--targets']
            result = subprocess.run(args, capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), target_inventory(self.corpus, self.bundle))
            for extras in (['--template'], ['--reviewer-id', 'synthetic'],
                           ['--new-version', '2'], [str(root / 'review.json')]):
                result = subprocess.run(args + extras, capture_output=True, text=True, timeout=20)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, '')

    def test_json_equivalent_aliases_cannot_modify_untargeted_records(self):
        for mode in ('shared_reasoning', 'shared_observation_list'):
            self.setUp()
            first = self.corpus['papers'][0]
            if mode == 'shared_reasoning':
                first['observations'][0]['reasoning'] = {}
                challenge = copy.deepcopy(first['observations'][0])
                challenge['stance'] = 'challenge'
                challenge['reasoning'] = first['observations'][0]['reasoning']
                first['observations'].append(challenge)
            else:
                self.corpus['papers'][1]['observations'] = first['observations']
                self.corpus['papers'][1]['segments']['synthetic reasoning'] = first['segments']['synthetic reasoning']
                self.corpus['papers'][1]['segments_sha256'] = payload_sha256(self.corpus['papers'][1]['segments'])
            self.bind()
            result = self.run_review()
            plain = json.loads(json.dumps(self.corpus))
            equivalent = prepare_revision(plain, self.bundle, self.review, '2', 'synthetic-revision')
            self.assertEqual(payload_sha256(result), payload_sha256(equivalent))
            self.assertEqual(result['package']['persona']['rules'][1].get('reasoning', {}), {})

    def test_template_only_defers_without_inferred_targets(self):
        with patch.object(MockProvider, 'extract', side_effect=AssertionError('provider called')):
            template = review_template(self.corpus, self.bundle, 'synthetic-reviewer')
        self.assertTrue(all(d['decision'] == 'defer' for d in template['decisions']))
        self.assertTrue(all('target_rule_id' not in d for d in template['decisions']))
        result = prepare_revision(self.corpus, self.bundle, template, '2', 'synthetic-revision')
        self.assertEqual(result['status'], 'REVIEW_INCOMPLETE')
        self.assertNotIn('package', result)

    def test_changed_corpus_or_bundle_invalidates_binding(self):
        for target in ('source', 'order', 'candidate', 'metadata'):
            self.setUp()
            if target == 'source':
                self.corpus['papers'][0]['segments']['synthetic reasoning'] += ' changed'
            elif target == 'order':
                self.corpus['papers'].reverse()
            elif target == 'candidate':
                self.bundle['candidates'][0]['candidate_text'] = 'altered proposal'
            else:
                self.corpus['build_id'] = 'different-build'
            with self.assertRaises(ValueError): self.run_review()

    def test_unknown_duplicate_missing_and_conflicting_decisions_rejected(self):
        for kind in ('unknown', 'duplicate', 'missing', 'conflict'):
            self.setUp()
            if kind == 'unknown':
                self.review['decisions'][0]['candidate_id'] = 'unknown'
            elif kind == 'duplicate':
                self.review['decisions'].append(copy.deepcopy(self.review['decisions'][0]))
            elif kind == 'missing':
                self.review['decisions'].pop()
            else:
                self.response[1] = copy.deepcopy(self.response[0])
                self.bind()
            with self.assertRaises(ValueError): self.run_review()

    def test_cross_source_target_or_unauthorized_input_rejected(self):
        self.review['decisions'][0]['target_rule_id'] = 'rule-2'
        self.review['decisions'][0]['target_paper_id'] = 'synthetic-1'
        with self.assertRaisesRegex(ValueError, 'candidate source paper'): self.run_review()
        for field, value in [('authorized', False), ('split', 'holdout'), ('author_id', 'other')]:
            self.setUp()
            self.corpus['papers'][0][field] = value
            with self.assertRaises(ValueError): self.run_review()

    def test_occupied_dimension_requires_explicit_exact_replacement(self):
        self.corpus = json.loads(Path('examples/reasoning-corpus.json').read_text())
        self.bind()
        with self.assertRaisesRegex(ValueError, 'unoccupied'): self.run_review()
        for decision, candidate in zip(self.review['decisions'], self.bundle['candidates']):
            decision['operation'] = 'replace'
            old = self.corpus['papers'][0]['observations'][0]['reasoning'][candidate['dimension']]
            decision['expected_component_sha256'] = payload_sha256(old)
        self.run_review()
        self.review['decisions'][0]['expected_component_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'prior component hash'): self.run_review()

    def test_rejection_and_deferral_never_enter_revision(self):
        cid = self.review['decisions'][0]['candidate_id']
        self.review['decisions'][0] = dict(candidate_id=cid, decision='reject', review_note='Synthetic rejection.')
        result = self.run_review()
        self.assertNotIn('alternative_explanation', result['package']['persona']['rules'][0]['reasoning'])
        self.review['decisions'][0]['decision'] = 'defer'
        result = self.run_review()
        self.assertEqual(result['status'], 'REVIEW_INCOMPLETE')
        self.assertNotIn('package', result)
        self.assertEqual(result['applied_candidate_ids'], [])
        for i, c in enumerate(self.bundle['candidates']):
            self.review['decisions'][i] = dict(candidate_id=c['candidate_id'], decision='reject', review_note='Synthetic rejection.')
        self.assertEqual(self.run_review()['status'], 'NO_ACCEPTED_CANDIDATES')
        self.assertNotIn('package', self.run_review())

    def test_unknown_fields_oversized_text_and_unchanged_version_rejected(self):
        for field, value in [('private_notes', 'synthetic extra'), ('reviewed_text', 'x' * 2001),
                             ('reviewed_claim_type', 'author_private_belief')]:
            self.setUp()
            self.review['decisions'][0][field] = value
            with self.assertRaises(ValueError): self.run_review()
        self.setUp()
        with self.assertRaisesRegex(ValueError, 'new version/build'):
            prepare_revision(self.corpus, self.bundle, self.review, self.corpus['version'], self.corpus['build_id'])

    def test_fabricated_locator_or_quote_cannot_be_reviewed(self):
        for field, value in [('locator', 'wrong'), ('evidence_quote', 'fabricated')]:
            self.setUp()
            self.bundle['candidates'][0][field] = value
            self.review['candidate_bundle_sha256'] = payload_sha256(self.bundle)
            with self.assertRaisesRegex(ValueError, 'quote does not match'): self.run_review()

    def test_cli_roundtrip_and_invalid_review_no_partial_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = []
            for name, value in [('corpus', self.corpus), ('candidates', self.bundle), ('review', self.review)]:
                path = root / (name + '.json')
                path.write_text(json.dumps(value))
                paths.append(str(path))
            extracted = subprocess.run([sys.executable, 'extraction_adapter.py', paths[0],
                '--mock-response', 'examples/mock-extraction-response.json'],
                capture_output=True, text=True, timeout=20)
            self.assertEqual(extracted.returncode, 0, extracted.stderr)
            self.assertEqual(json.loads(extracted.stdout), self.bundle)
            Path(paths[1]).write_text(extracted.stdout)
            template = subprocess.run([sys.executable, 'operator_review.py', *paths[:2],
                '--template', '--reviewer-id', 'synthetic-reviewer'],
                capture_output=True, text=True, timeout=20)
            self.assertEqual(template.returncode, 0, template.stderr)
            self.assertTrue(all(d['decision'] == 'defer' for d in json.loads(template.stdout)['decisions']))
            args = [sys.executable, 'operator_review.py', *paths,
                    '--new-version', '2', '--new-build-id', 'synthetic-revision']
            result = subprocess.run(args, capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['status'], 'REVIEWED_REVISION_CANDIDATE')
            revision = root / 'revision.json'
            revision.write_text(result.stdout)
            view = subprocess.run([sys.executable, 'review_package.py', str(revision),
                '--question', 'Question', '--topic', 'model design'], capture_output=True, text=True, timeout=20)
            self.assertEqual(view.returncode, 0, view.stderr)
            self.assertIn('origin=operator_reviewed_mock_candidate', view.stdout)
            base = subprocess.run([sys.executable, 'observation_input.py', paths[0],
                '--question', 'Question', '--topic', 'model design'], capture_output=True, text=True, timeout=20)
            self.assertEqual(base.returncode, 0, base.stderr)
            previous = root / 'previous.json'
            previous.write_text(base.stdout)
            compared = subprocess.run([sys.executable, 'compare_releases.py', str(previous), str(revision)],
                capture_output=True, text=True, timeout=20)
            self.assertEqual(compared.returncode, 0, compared.stderr)
            self.assertEqual(json.loads(compared.stdout)['status'], 'REVIEW_REQUIRED')
            self.review['candidate_bundle_sha256'] = '0' * 64
            Path(paths[2]).write_text(json.dumps(self.review))
            result = subprocess.run(args, capture_output=True, text=True, timeout=20)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, '')


if __name__ == '__main__':
    unittest.main()
