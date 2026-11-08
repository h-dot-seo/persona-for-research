import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import tests.test_design_scenario as fixture
from answer_draft import template, inspect, review_template, review, render
from extraction_adapter import MockProvider
from persona import payload_sha256


class AnswerDraftTests(unittest.TestCase):
    def setUp(self):
        case = fixture.DesignScenarioTests(); case.setUp(); self.package = case.package
        self.draft = template(self.package, 'How could two synthetic explanations be distinguished?', 'synthetic-operator')
        self.quote = dict(claim_id='q1', text='A shared prediction does not discriminate the models.',
            claim_type='source_quote', uncertainty=None, citations=[dict(role='context', reference=dict(
                paper_id='synthetic-1', observation_index=0, dimension='falsification_check'))])
        self.synthesis = dict(claim_id='s1', text='Inspect where model predictions differ before designing a comparison.',
            claim_type='operator_synthesis', uncertainty='Transfer to this question has not been tested.',
            citations=[dict(role='support', reference=dict(paper_id='synthetic-0', observation_index=0, dimension='alternative_explanation')),
                       dict(role='challenge', reference=dict(paper_id='synthetic-1', observation_index=0, dimension='falsification_check'))])
        self.draft['claims'] = [self.quote, self.synthesis]

    def test_quote_equality_and_source_labels_separate_from_synthesis(self):
        result = inspect(self.package, self.draft)
        self.assertEqual(result['claims'][0]['quote_check'], 'EQUALS_STORED_QUOTE_ONLY')
        self.assertEqual(result['claims'][1]['claim_type'], 'operator_synthesis')
        evidence = result['claims'][1]['citations']
        self.assertEqual(evidence[0]['evidence']['component']['claim_type'], 'operator_interpretation')
        self.assertEqual(evidence[1]['evidence']['component']['claim_type'], 'explicit_statement')
        self.assertEqual([x['evidence']['source_kind'] for x in evidence], ['research', 'review'])
        self.assertTrue(result['claims'][1]['challenge_citation_supplied'])
        self.assertTrue(result['claims'][0]['missing_uncertainty'])
        self.assertEqual(result['semantic_validation'], 'NOT_PERFORMED')

    def test_quote_substrings_wrong_dimension_and_unbound_author_claim_reject(self):
        for text in ('A shared prediction', self.quote['text'] + ' ', 'Invented quotation.'):
            draft = copy.deepcopy(self.draft); draft['claims'][0]['text'] = text
            with self.assertRaises(ValueError): inspect(self.package, draft)
        for kind in ('explicit_statement', 'author_recommendation', 'model_inference'):
            draft = copy.deepcopy(self.draft); draft['claims'][1]['claim_type'] = kind
            with self.assertRaises(ValueError): inspect(self.package, draft)
        for citations in ([], self.quote['citations'] * 2):
            draft = copy.deepcopy(self.draft); draft['claims'][0]['citations'] = citations
            with self.assertRaises(ValueError): inspect(self.package, draft)

    def test_no_citation_is_visible_and_uncited_challenge_kept(self):
        self.draft['claims'] = [self.synthesis]; self.synthesis['citations'] = []
        result = inspect(self.package, self.draft)
        self.assertEqual(result['claims'][0]['evidence_status'], 'NO_CITATIONS_SUPPLIED')
        self.assertEqual(len(result['uncited_observations']), 2)
        self.assertEqual(result['uncited_observations'][1]['observation']['stance'], 'challenge')
        self.assertIn('[challenge;', render(result))

    def test_review_decisions_do_not_drop_rejected_claims_or_validate_science(self):
        supplied = review_template(self.package, self.draft, 'synthetic-reviewer')
        self.assertEqual(review(self.package, self.draft, supplied)['status'], 'DECLARED_REVIEW_INCOMPLETE')
        supplied['decisions'][0].update(decision='reject', note='Quote does not answer the question.')
        supplied['decisions'][1].update(decision='revise', note='Supply a question-specific falsification condition.')
        result = review(self.package, self.draft, supplied)
        self.assertEqual(result['status'], 'DECLARED_REVIEW_RECORDED_NOT_VALIDATED')
        self.assertEqual(len(result['claims']), 2)
        self.assertEqual(result['reviewer_identity'], 'RECORDED_NOT_AUTHENTICATED')
        self.assertIn('Declared decision: reject', render(result))

    def test_changed_text_question_role_or_uncertainty_invalidates_review(self):
        supplied = review_template(self.package, self.draft, 'synthetic-reviewer')
        variants = []
        for field in ('text', 'uncertainty'):
            draft = copy.deepcopy(self.draft); draft['claims'][1][field] += ' Changed.'; variants.append(draft)
        draft = copy.deepcopy(self.draft); draft['question'] += ' Changed.'; variants.append(draft)
        draft = copy.deepcopy(self.draft); draft['claims'][1]['citations'][0]['role'] = 'context'; variants.append(draft)
        for draft in variants:
            with self.assertRaisesRegex(ValueError, 'stale'): review(self.package, draft, supplied)

    def test_review_requires_complete_unique_known_decisions(self):
        for mode in ('missing', 'duplicate', 'unknown', 'unsupported', 'extra'):
            supplied = review_template(self.package, self.draft, 'synthetic-reviewer')
            if mode == 'missing': supplied['decisions'].pop()
            elif mode == 'duplicate': supplied['decisions'].append(copy.deepcopy(supplied['decisions'][0]))
            elif mode == 'unknown': supplied['decisions'][0]['claim_id'] = 'unknown'
            elif mode == 'unsupported': supplied['decisions'][0]['decision'] = 'scientifically_verified'
            else: supplied['decisions'][0]['author_approval'] = True
            with self.assertRaises(ValueError): review(self.package, self.draft, supplied)

    def test_unknown_fields_refs_duplicates_and_holdout_reject(self):
        for change in ('extra', 'duplicate', 'missing_dimension', 'bool_index'):
            draft = copy.deepcopy(self.draft)
            if change == 'extra': draft['claims'][0]['author'] = 'invented'
            elif change == 'duplicate': draft['claims'].append(copy.deepcopy(draft['claims'][0]))
            elif change == 'missing_dimension': draft['claims'][0]['citations'][0]['reference']['dimension'] = 'question_framing'
            else: draft['claims'][0]['citations'][0]['reference']['observation_index'] = True
            with self.assertRaises(ValueError): inspect(self.package, draft)
        self.package['knowledge']['papers'][0]['split'] = 'holdout'
        self.package['persona']['knowledge_papers_sha256'] = payload_sha256(self.package['knowledge']['papers'])
        self.package['knowledge']['persona_payload_sha256'] = payload_sha256(self.package['persona'])
        with self.assertRaises(ValueError): inspect(self.package, self.draft)

    def test_no_calls_input_mutation_aliasing_or_terminal_injection(self):
        before = copy.deepcopy((self.package, self.draft))
        with patch.object(MockProvider, 'extract', side_effect=AssertionError('provider called')), \
             patch.object(Path, 'read_text', side_effect=AssertionError('source read')):
            result = inspect(self.package, self.draft)
        result['claims'][0]['citations'][0]['evidence']['component']['text'] = 'mutated'
        self.assertNotEqual(result['claims'][1]['citations'][1]['evidence']['component']['text'], 'mutated')
        self.assertEqual((self.package, self.draft), before)
        self.synthesis['text'] = '합성\nFORGED\x1b[31m'
        self.assertIn('합성\\u000aFORGED\\u001b[31m', render(inspect(self.package, self.draft)))

    def test_empty_draft_and_review_never_approved(self):
        draft = template(self.package, 'Question', 'operator')
        supplied = review_template(self.package, draft, 'reviewer')
        self.assertEqual(review(self.package, draft, supplied)['status'], 'NO_ANSWER_CLAIMS')
        self.assertEqual(len(inspect(self.package, draft)['uncited_observations']), 2)

    def test_text_keeps_reviewer_identity_and_mock_origin_checks(self):
        import tests.test_design_lineage as lineage_fixture
        case = lineage_fixture.DesignLineageTests(); case.setUp()
        draft = template(case.package, 'Synthetic question', 'synthetic-draft-operator')
        claim = copy.deepcopy(self.synthesis)
        claim['citations'] = [dict(role='context', reference=dict(paper_id='synthetic-0', observation_index=0, dimension='uncertainty'))]
        draft['claims'] = [claim]
        first = review_template(case.package, draft, 'reviewer-one')
        second = review_template(case.package, draft, 'reviewer-two')
        text = render(review(case.package, draft, first))
        self.assertNotEqual(text, render(review(case.package, draft, second)))
        for value in ('reviewer-one', 'synthetic-draft-operator', 'operator_reviewed_mock_candidate',
                      'proposed claim label=explicit_statement', 'Component [operator_interpretation]',
                      payload_sha256(case.bundle), payload_sha256(case.declared), payload_sha256(first)):
            self.assertIn(value, text)

    def test_actual_cli_draft_review_template_and_reviewed_text(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, value in [('package', self.package), ('draft', self.draft)]:
                (root / (name + '.json')).write_text(json.dumps(value), encoding='utf-8')
            command = [sys.executable, 'answer_draft.py', str(root/'package.json'), str(root/'draft.json')]
            def run(args): return subprocess.run(args, capture_output=True, check=True).stdout
            self.assertEqual(json.loads(run(command)), inspect(self.package, self.draft))
            supplied = json.loads(run(command + ['--review-template', '--reviewer-id', 'synthetic-reviewer']))
            for d in supplied['decisions']: d.update(decision='retain', note='Recorded synthetic judgment, not scientific validation.')
            (root/'review.json').write_text(json.dumps(supplied), encoding='utf-8')
            text = run(command + ['--review', str(root/'review.json'), '--format', 'text']).decode('utf-8')
            for value in ('DECLARED_REVIEW_RECORDED_NOT_VALIDATED', '[review]', '[research]', 'synthetic criterion',
                          'operator_synthesis', 'explicit_statement', 'Declared decision: retain', 'NOT_SUPPLIED'):
                self.assertIn(value, text)


if __name__ == '__main__': unittest.main()
