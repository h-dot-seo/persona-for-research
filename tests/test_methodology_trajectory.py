"""Synthetic chronology tests; no scientific validity is asserted."""
import copy
import json
import unittest
from pathlib import Path

from observation_input import verified_corpus
from research_workflow import apply, build


class MethodologyTrajectoryTests(unittest.TestCase):
    def setUp(self):
        self.corpus = json.loads(Path('examples/research-corpus.json').read_text())

    def report(self):
        return apply(build(self.corpus), 'Which experiment?', 'model design')['methodology_trajectory']

    def test_chronology_preserves_research_review_and_limits(self):
        report = self.report()[0]
        self.assertEqual(report['year_range'], [2020, 2021])
        self.assertEqual(report['papers_by_kind'],
                         {'research': ['synthetic-0'], 'review': ['synthetic-1']})
        self.assertEqual(report['evidence_status'], 'SUPPORT_ONLY')
        self.assertFalse(report['cross_year_stance_variation'])
        self.assertEqual(report['status'], 'SYSTEM_INFERENCE_REQUIRES_REVIEW')
        self.assertIn('no inferred career stage', report['inference_boundary'])
        self.assertTrue(all(e['locator'] and e['limitation'] for e in report['evidence']))

    def test_later_challenge_is_not_author_reversal(self):
        self.corpus['papers'][1]['observations'][0]['stance'] = 'challenge'
        report = self.report()[0]
        self.assertEqual(report['evidence_status'], 'MIXED_STANCES')
        self.assertTrue(report['cross_year_stance_variation'])
        self.assertFalse(report['within_year_disagreement'])
        self.assertEqual(len(report['evidence']), 2)

    def test_same_year_disagreement_has_no_temporal_order_claim(self):
        self.corpus['papers'][1]['year'] = 2020
        self.corpus['papers'][1]['observations'][0]['stance'] = 'challenge'
        report = self.report()[0]
        self.assertTrue(report['within_year_disagreement'])
        self.assertFalse(report['cross_year_stance_variation'])

    def test_duplicate_observations_do_not_multiply_papers(self):
        self.corpus['papers'][0]['observations'] *= 2
        report = self.report()[0]
        self.assertEqual(len(report['evidence']), 3)
        self.assertEqual(report['distinct_paper_count'], 2)

    def test_conditions_are_not_semantically_merged(self):
        self.corpus['papers'][1]['observations'][0]['condition'] = 'a different context'
        self.assertEqual(len(self.report()), 2)

    def test_challenge_only_and_uncovered_topic(self):
        for paper in self.corpus['papers']:
            paper['observations'][0]['stance'] = 'challenge'
        self.assertEqual(self.report()[0]['evidence_status'], 'CHALLENGE_ONLY')
        self.assertEqual(apply(build(self.corpus), 'Question', 'unknown')['methodology_trajectory'], [])

    def test_verified_quotes_and_claim_types_survive(self):
        corpus = json.loads(Path('examples/observed-corpus.json').read_text())
        package = build(verified_corpus(corpus))
        report = apply(package, 'Question', 'model design')['methodology_trajectory']
        evidence = report[0]['evidence']
        self.assertTrue(all(e['evidence_verification'] == 'EXACT_QUOTE_MATCH_ONLY' for e in evidence))
        self.assertTrue(all(e['evidence_quote'] for e in evidence))
        self.assertEqual([e['claim_type'] for e in evidence],
                         [p['observations'][0]['claim_type'] for p in corpus['papers']])

    def test_temporal_order_does_not_depend_on_input_order(self):
        before = self.report()[0]
        self.corpus['papers'].reverse()
        after = self.report()[0]
        self.assertEqual([e['paper_id'] for e in before['evidence']],
                         [e['paper_id'] for e in after['evidence']])
        self.assertEqual(self.report(), self.report())

    def test_holdout_cannot_enter_chronology(self):
        for field, value in [('split', 'holdout'), ('authorized', False), ('author_id', 'other')]:
            corpus = copy.deepcopy(self.corpus)
            corpus['papers'][1][field] = value
            with self.assertRaises(ValueError):
                build(corpus)


if __name__ == '__main__':
    unittest.main()
