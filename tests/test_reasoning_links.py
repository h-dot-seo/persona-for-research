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
from reasoning_links import review, render, template
from research_workflow import build


class ReasoningLinksTests(unittest.TestCase):
    def setUp(self):
        self.corpus = json.loads(Path('examples/reasoning-corpus.json').read_text())
        paper = self.corpus['papers'][1]
        obs = paper['observations'][0]
        obs.update(method='test sensitivity to competing explanations',
            condition='a shared confound can mimic outcomes', stance='challenge', topic='sensitivity review',
            evidence_quote='test sensitivity to competing explanations')
        paper['segments']['synthetic section 1'] = 'When a shared confound can mimic outcomes, test sensitivity to competing explanations.'
        paper['segments']['synthetic falsification'] = 'A disconfirming outcome challenges the selected model.'
        paper['segments_sha256'] = payload_sha256(paper['segments'])
        obs['reasoning'] = dict(falsification_check=dict(
            text='Check a disconfirming outcome.', locator='synthetic falsification',
            evidence_quote='A disconfirming outcome challenges the selected model.', claim_type='explicit_statement'))
        self.package = build(verified_corpus(self.corpus))
        self.supplied = template(self.package, 'synthetic-operator')
        self.link = dict(link_id='link-1', relation='qualifies',
            from_ref=dict(paper_id='synthetic-1', observation_index=0, dimension='falsification_check'),
            to_ref=dict(paper_id='synthetic-0', observation_index=0, dimension='alternative_explanation'),
            rationale='In this synthetic comparison, the later review criterion qualifies the earlier alternative explanation.',
            claim_type='operator_interpretation')
        self.supplied['links'] = [self.link]

    def rebind(self, package):
        package['persona']['knowledge_papers_sha256'] = payload_sha256(package['knowledge']['papers'])
        package['knowledge']['persona_payload_sha256'] = payload_sha256(package['persona'])
        return package

    def test_cross_method_year_topic_link_preserves_source_and_interpretation(self):
        result = review(self.package, self.supplied)
        link = result['links'][0]
        left, right = link['from_evidence'], link['to_evidence']
        self.assertGreater(left['publication_year'], right['publication_year'])
        self.assertNotEqual(left['observation']['method'], right['observation']['method'])
        self.assertNotEqual(left['observation']['topic'], right['observation']['topic'])
        self.assertEqual(left['observation']['stance'], 'challenge')
        self.assertEqual(left['source_kind'], 'review')
        self.assertEqual(right['source_kind'], 'research')
        self.assertEqual(left['component']['claim_type'], 'explicit_statement')
        self.assertEqual(right['component']['claim_type'], 'operator_interpretation')
        self.assertEqual(link['claim_type'], 'operator_interpretation')
        self.assertNotEqual(left['component']['locator'], left['observation']['locator'])
        self.assertEqual(result['operator_identity'], 'RECORDED_NOT_AUTHENTICATED')
        self.assertFalse(result['canonical_update_performed'])

    def test_empty_template_creates_no_links_or_selection(self):
        empty = template(self.package, 'synthetic-operator')
        self.assertEqual(empty['links'], [])
        self.assertEqual(review(self.package, empty)['status'], 'NO_SUPPLIED_LINKS')
        for invalid in ('', ' ', None, 'x' * 129):
            with self.assertRaises(ValueError):
                template(self.package, invalid)

    def test_endpoint_indexes_and_missing_dimensions_fail_without_fallback(self):
        for key, values in (('observation_index', (-1, True, 0.0, 3, '0')),
                            ('dimension', ('question_framing', 'unknown', [])),
                            ('paper_id', ('foreign-paper', None, []))):
            for value in values:
                bad = copy.deepcopy(self.supplied)
                bad['links'][0]['from_ref'][key] = value
                with self.assertRaises(ValueError):
                    review(self.package, bad)
        plain = copy.deepcopy(self.supplied)
        plain['links'][0]['from_ref']['dimension'] = None
        self.assertIsNone(review(self.package, plain)['links'][0]['from_evidence']['component'])

    def test_stale_package_and_reordered_observations_invalidate_links(self):
        stale = copy.deepcopy(self.package)
        stale['persona']['build_id'] = 'another-build'
        stale['knowledge']['build_id'] = 'another-build'
        with self.assertRaises(ValueError):
            review(self.rebind(stale), self.supplied)
        other = copy.deepcopy(self.corpus)
        other['papers'].reverse()
        with self.assertRaises(ValueError):
            review(build(verified_corpus(other)), self.supplied)
        first = self.corpus['papers'][0]['observations']
        extra = copy.deepcopy(first[0]); extra['stance'] = 'challenge'; first.append(extra)
        original = build(verified_corpus(self.corpus))
        bound = template(original, 'synthetic-operator'); bound['links'] = [self.link]
        first.reverse()
        with self.assertRaises(ValueError):
            review(build(verified_corpus(self.corpus)), bound)

    def test_unauthorized_holdout_cross_author_or_inconsistent_source_rejected(self):
        for key, value in [('authorized', False), ('split', 'holdout'), ('author_id', 'another-scholar')]:
            bad = copy.deepcopy(self.package)
            bad['knowledge']['papers'][1][key] = value
            with self.assertRaises(ValueError):
                review(self.rebind(bad), self.supplied)
        bad = copy.deepcopy(self.package)
        bad['persona']['rules'][0]['method'] = 'invented method'
        with self.assertRaises(ValueError):
            template(self.rebind(bad), 'synthetic-operator')

    def test_bad_schema_duplicates_self_links_and_author_claims_rejected(self):
        for change in (dict(relation='proves'), dict(claim_type='explicit_statement'),
                       dict(rationale=''), dict(rationale='x' * 2001), dict(extra='unlisted')):
            bad = copy.deepcopy(self.supplied); bad['links'][0].update(change)
            with self.assertRaises(ValueError):
                review(self.package, bad)
        for mode in ('same_id', 'same_edge', 'self', 'inverse_contrast'):
            bad = copy.deepcopy(self.supplied)
            if mode == 'self':
                bad['links'][0]['to_ref'] = copy.deepcopy(bad['links'][0]['from_ref'])
            else:
                added = copy.deepcopy(bad['links'][0])
                if mode != 'same_id': added['link_id'] = 'link-2'
                if mode == 'inverse_contrast':
                    bad['links'][0]['relation'] = added['relation'] = 'contrasts'
                    added['from_ref'], added['to_ref'] = added['to_ref'], added['from_ref']
                bad['links'].append(added)
            with self.assertRaises(ValueError):
                review(self.package, bad)

    def test_conflicting_relations_and_cycles_are_not_resolved_or_expanded(self):
        self.link['relation'] = 'supports'
        challenge = copy.deepcopy(self.link); challenge.update(link_id='link-2', relation='challenges')
        reverse = copy.deepcopy(self.link); reverse['link_id'] = 'link-3'
        reverse['from_ref'], reverse['to_ref'] = reverse['to_ref'], reverse['from_ref']
        self.supplied['links'] += [challenge, reverse]
        result = review(self.package, self.supplied)
        self.assertEqual([link['relation'] for link in result['links']], ['supports', 'challenges', 'supports'])
        self.assertEqual(len(result['links']), 3)

    def test_same_source_hash_projection_and_no_mutation_provider_or_source_reads(self):
        self.corpus['papers'][1]['source_sha256'] = self.corpus['papers'][0]['source_sha256']
        package = build(verified_corpus(self.corpus))
        package['knowledge']['papers'][0]['segments'] = {'section': 'SYNTHETIC_RAW_MARKER'}
        package['knowledge']['papers'][0]['hidden'] = 'SYNTHETIC_PRIVATE_MARKER'
        self.rebind(package)
        supplied = template(package, 'synthetic-operator'); supplied['links'] = [self.link]
        before = copy.deepcopy((package, supplied))
        with patch.object(MockProvider, 'extract', side_effect=AssertionError('provider called')), \
             patch.object(Path, 'read_text', side_effect=AssertionError('source opened')):
            result = review(package, supplied)
        self.assertTrue(result['links'][0]['same_source_hash'])
        self.assertNotIn('SYNTHETIC_RAW_MARKER', json.dumps(result))
        self.assertNotIn('SYNTHETIC_PRIVATE_MARKER', json.dumps(result))
        result['links'][0]['from_evidence']['component']['text'] = 'changed output'
        self.assertEqual((package, supplied), before)

    def test_text_shows_claims_recorded_checks_and_escaped_controls(self):
        self.supplied['operator_id'] = '합성\nFAKE\x1b[31m'
        text = render(self.package, self.supplied)
        self.assertIn('합성\\u000aFAKE\\u001b[31m', text)
        self.assertNotIn('\x1b', text)
        self.assertIn('qualifies [operator_interpretation]', text)
        self.assertIn('Component [explicit_statement]', text)
        self.assertIn('Component [operator_interpretation]', text)
        self.assertIn('Topic: sensitivity review', text)
        self.assertIn('Topic: model design', text)
        self.assertIn('recorded check=EXACT_QUOTE_MATCH_ONLY', text)
        self.assertIn('recorded check=NOT_PERFORMED', text)
        self.assertIn('not rechecked here', text)

    def test_actual_cli_intake_template_explicit_link_and_review(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            corpus, package, links = [root / name for name in ('corpus.json', 'package.json', 'links.json')]
            corpus.write_text(json.dumps(self.corpus))
            intake = subprocess.run([sys.executable, 'observation_input.py', str(corpus),
                '--question', 'Which synthetic test?', '--topic', 'model design'], capture_output=True, text=True, timeout=20)
            self.assertEqual(intake.returncode, 0, intake.stderr); package.write_text(intake.stdout)
            command = [sys.executable, 'reasoning_links.py', str(package)]
            empty = subprocess.run(command + ['--template', '--operator-id', 'synthetic-operator'],
                capture_output=True, text=True, timeout=20)
            self.assertEqual(empty.returncode, 0, empty.stderr)
            supplied = json.loads(empty.stdout); self.assertEqual(supplied['links'], [])
            supplied['links'] = [self.link]; links.write_text(json.dumps(supplied))
            for format in ('json', 'text'):
                output = subprocess.run(command + [str(links), '--format', format], capture_output=True, text=True, timeout=20)
                self.assertEqual(output.returncode, 0, output.stderr)
                self.assertIn('synthetic-0', output.stdout); self.assertIn('synthetic-1', output.stdout)
            for extras in ([str(links), '--template'], ['--template', '--format', 'text'],
                           [str(links), '--operator-id', 'unexpected'], []):
                output = subprocess.run(command + extras, capture_output=True, text=True, timeout=20)
                self.assertNotEqual(output.returncode, 0); self.assertEqual(output.stdout, '')
            supplied['links'][0]['from_ref']['observation_index'] = True
            links.write_text(json.dumps(supplied))
            output = subprocess.run(command + [str(links)], capture_output=True, text=True, timeout=20)
            self.assertNotEqual(output.returncode, 0); self.assertEqual(output.stdout, '')


if __name__ == '__main__':
    unittest.main()
