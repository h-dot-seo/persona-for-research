import copy
import json
import unittest
from pathlib import Path

from observation_input import verified_corpus
from research_workflow import apply, build


class ProjectionTests(unittest.TestCase):
    def setUp(self):
        self.corpus = json.loads(Path('examples/reasoning-corpus.json').read_text())

    def test_unknown_fields_do_not_enter_knowledge_or_cards(self):
        paper = self.corpus['papers'][0]
        paper['holdout_notes'] = 'PAPER_HOLDOUT_SENTINEL'
        obs = paper['observations'][0]
        obs['private_notes'] = 'OBSERVATION_PRIVATE_SENTINEL'
        obs['reasoning']['uncertainty']['holdout_evidence'] = {
            'split': 'holdout', 'text': 'REASONING_HOLDOUT_SENTINEL'}
        for corpus in (self.corpus, verified_corpus(self.corpus)):
            package = build(corpus)
            output = json.dumps(dict(package=package, application=apply(package, 'Question', 'model design')))
            for sentinel in ('PAPER_HOLDOUT_SENTINEL', 'OBSERVATION_PRIVATE_SENTINEL', 'REASONING_HOLDOUT_SENTINEL'):
                self.assertNotIn(sentinel, output)
            self.assertNotIn('segments', package['knowledge']['papers'][0])

    def test_raw_sections_not_copied_and_authorized_quote_retained(self):
        self.corpus['papers'][0]['segments']['unquoted section'] = 'UNQUOTED_SOURCE_SENTINEL'
        package = build(self.corpus)
        self.assertNotIn('UNQUOTED_SOURCE_SENTINEL', json.dumps(package))
        self.assertEqual(package['knowledge']['papers'][0]['observations'][0]['evidence_quote'],
                         self.corpus['papers'][0]['observations'][0]['evidence_quote'])

    def test_unknown_claim_type_rejected(self):
        for claim_type in ('private_belief', 'proven_author_opinion', None, []):
            corpus = copy.deepcopy(self.corpus)
            corpus['papers'][0]['observations'][0]['claim_type'] = claim_type
            with self.assertRaisesRegex(ValueError, 'claim_type'):
                build(corpus)

    def test_malformed_shapes_fail_cleanly(self):
        for papers in ({}, [None], [{'authorized': True}]):
            corpus = copy.deepcopy(self.corpus)
            corpus['papers'] = papers
            with self.assertRaises(ValueError): build(corpus)
        for observations in ({}, [None]):
            corpus = copy.deepcopy(self.corpus)
            corpus['papers'][0]['observations'] = observations
            with self.assertRaises(ValueError): build(corpus)

    def test_full_corpus_boundary_precedes_observation_processing(self):
        self.corpus['papers'][0]['observations'] = None
        self.corpus['papers'][1]['split'] = 'holdout'
        with self.assertRaisesRegex(ValueError, 'authorized runtime training'):
            build(self.corpus)

    def test_projection_does_not_modify_original(self):
        self.corpus['papers'][0]['extra'] = 'synthetic extra'
        original = copy.deepcopy(self.corpus)
        build(self.corpus)
        self.assertEqual(self.corpus, original)

    def test_supported_scalar_fields_cannot_carry_nested_records(self):
        for field in ('locator', 'topic', 'source_file', 'segments_sha256'):
            corpus = copy.deepcopy(self.corpus)
            corpus['papers'][0][field] = {'holdout': 'synthetic nested record'}
            with self.assertRaises(ValueError): build(corpus)
        self.corpus['papers'][0]['observations'][0]['evidence_quote'] = {'holdout': 'synthetic nested record'}
        with self.assertRaisesRegex(ValueError, 'evidence_quote'):
            build(self.corpus)


if __name__ == '__main__':
    unittest.main()
