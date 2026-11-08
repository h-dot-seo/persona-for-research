import copy
import json
import unittest
from pathlib import Path

from observation_input import verified_corpus
from reasoning_cards import DIMENSIONS
from research_workflow import apply, build


class CoverageTests(unittest.TestCase):
    def setUp(self):
        self.corpus = json.loads(Path('examples/reasoning-corpus.json').read_text())

    def report(self, verified=True, topic='model design'):
        corpus = verified_corpus(self.corpus) if verified else self.corpus
        return apply(build(corpus), 'Question', topic)['evidence_coverage']

    def test_partial_coverage_and_claim_type_counts(self):
        result = self.report()
        self.assertEqual(result['status'], 'PARTIAL_DIMENSION_COVERAGE')
        self.assertEqual(result['distinct_paper_count'], 2)
        dimensions = {d['dimension']: d for d in result['dimensions']}
        self.assertEqual(dimensions['uncertainty']['explicit_statement_count'], 1)
        self.assertEqual(dimensions['alternative_explanation']['operator_interpretation_count'], 1)
        self.assertEqual(dimensions['uncertainty']['quote_matched_count'], 1)
        self.assertEqual(dimensions['uncertainty']['evidence'][0]['locator'], 'synthetic reasoning')

    def test_repetition_does_not_multiply_papers(self):
        self.corpus['papers'][0]['observations'] *= 2
        result = self.report()
        self.assertEqual(result['observation_count'], 3)
        self.assertEqual(result['distinct_paper_count'], 2)
        uncertainty = next(d for d in result['dimensions'] if d['dimension'] == 'uncertainty')
        self.assertEqual(uncertainty['component_count'], 2)
        self.assertEqual(uncertainty['paper_ids'], ['synthetic-0'])

    def test_unverified_input_is_not_counted_as_quote_matched(self):
        self.assertTrue(all(d['quote_matched_count'] == 0 for d in self.report(False)['dimensions']))

    def test_absent_reasoning_and_absent_topic_distinguished(self):
        self.assertEqual(self.report(topic='unknown')['status'], 'NO_OBSERVATIONS')
        del self.corpus['papers'][0]['observations'][0]['reasoning']
        self.assertEqual(self.report()['status'], 'NO_REASONING_COMPONENTS')

    def test_all_dimensions_does_not_claim_readiness(self):
        obs = self.corpus['papers'][0]['observations'][0]
        component = obs['reasoning']['uncertainty']
        obs['reasoning'] = {d: copy.deepcopy(component) for d in DIMENSIONS}
        result = self.report()
        self.assertEqual(result['status'], 'ALL_DIMENSIONS_REPRESENTED')
        self.assertIn('do not establish confidence', result['boundary'])
        self.assertEqual(result['missing_dimensions'], [])

    def test_challenge_evidence_keeps_rule_links(self):
        self.corpus['papers'][0]['observations'][0]['stance'] = 'challenge'
        component = next(d for d in self.report()['dimensions'] if d['dimension'] == 'uncertainty')
        self.assertEqual(component['supporting_rule_ids'], [])
        self.assertEqual(component['challenging_rule_ids'], ['rule-1'])


if __name__ == '__main__':
    unittest.main()
