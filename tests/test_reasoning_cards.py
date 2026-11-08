import copy
import json
import unittest
from pathlib import Path

from observation_input import verified_corpus
from persona import payload_sha256
from research_workflow import apply, build


class ReasoningCardTests(unittest.TestCase):
    def setUp(self):
        self.corpus = json.loads(Path('examples/observed-corpus.json').read_text())
        paper = self.corpus['papers'][0]
        paper['segments']['synthetic reasoning'] = 'Compare explanations. State uncertainty.'
        paper['segments_sha256'] = payload_sha256(paper['segments'])
        paper['observations'][0]['reasoning'] = {
            'alternative_explanation': dict(text='Consider an alternative explanation.',
                locator='synthetic reasoning', evidence_quote='Compare explanations.',
                claim_type='operator_interpretation'),
            'uncertainty': dict(text='State uncertainty.', locator='synthetic reasoning',
                evidence_quote='State uncertainty.', claim_type='explicit_statement')}

    def result(self):
        return apply(build(verified_corpus(self.corpus)), 'Which explanation?', 'model design')

    def test_independently_linked_components_and_missing_dimensions(self):
        result = self.result()
        self.assertEqual(len(result['reasoning_cards']), 1)
        card = result['reasoning_cards'][0]
        self.assertEqual(card['paper_id'], 'synthetic-0')
        self.assertEqual(card['components']['uncertainty']['claim_type'], 'explicit_statement')
        self.assertEqual(card['components']['alternative_explanation']['claim_type'], 'operator_interpretation')
        self.assertEqual(card['components']['uncertainty']['evidence_verification'], 'EXACT_QUOTE_MATCH_ONLY')
        self.assertIn('question_framing', card['missing_dimensions'])
        self.assertNotIn('uncertainty', card['missing_dimensions'])
        self.assertFalse(result['processing']['llm_used'])
        self.assertFalse(result['processing']['automatic_extraction'])

    def test_invalid_component_quote_and_locator_rejected(self):
        for field, value in [('evidence_quote', 'Invented quote'), ('locator', 'wrong section')]:
            corpus = copy.deepcopy(self.corpus)
            corpus['papers'][0]['observations'][0]['reasoning']['uncertainty'][field] = value
            with self.assertRaisesRegex(ValueError, 'reasoning quote'):
                verified_corpus(corpus)

    def test_unknown_dimensions_and_malformed_records_rejected(self):
        for components in ([], {'private_belief': {}}, {'uncertainty': None},
                           {'uncertainty': dict(text='claim', locator='x', evidence_quote='q', claim_type='fact')}):
            corpus = copy.deepcopy(self.corpus)
            corpus['papers'][0]['observations'][0]['reasoning'] = components
            with self.assertRaises(ValueError): build(corpus)

    def test_challenges_keep_their_stance(self):
        self.corpus['papers'][0]['observations'][0]['stance'] = 'challenge'
        self.assertEqual(self.result()['reasoning_cards'][0]['evidence_stance'], 'challenge')

    def test_absent_or_uncovered_reasoning_is_not_invented(self):
        package = build(verified_corpus(self.corpus))
        self.assertEqual(apply(package, 'Question', 'unknown')['reasoning_cards'], [])
        del self.corpus['papers'][0]['observations'][0]['reasoning']
        self.assertEqual(self.result()['reasoning_cards'], [])

    def test_holdout_rejected_before_reasoning_inspection(self):
        self.corpus['papers'][0]['split'] = 'holdout'
        self.corpus['papers'][0]['observations'][0]['reasoning'] = None
        with self.assertRaisesRegex(ValueError, 'training evidence'):
            verified_corpus(self.corpus)

    def test_rule_binding_detects_component_tampering(self):
        package = build(verified_corpus(self.corpus))
        package['persona']['rules'][0]['reasoning']['uncertainty']['text'] = 'altered'
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            apply(package, 'Question', 'model design')

    def test_deterministic_and_nonmutating(self):
        original = copy.deepcopy(self.corpus)
        self.assertEqual(self.result(), self.result())
        self.assertEqual(self.corpus, original)


if __name__ == '__main__':
    unittest.main()
