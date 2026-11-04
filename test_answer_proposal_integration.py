"""Synthetic imported-answer history through existing review consumers, never model calls."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import answer_proposals as proposals
import answer_draft
import argument_map
import evidence_scope
import evaluate_synthetic
import journey_compare
import journey_html
import journey_inputs
import research_journey
import revision_impact
import source_recheck
import test_research_journey as fixture
from test_journey_html import Document
from persona import payload_sha256

ROOT = Path(__file__).resolve().parent


class AnswerProposalIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.case = fixture.ResearchJourneyTests(); self.case.setUp(); self.c = self.case.case
        self.scope = proposals.template(self.c.package, self.c.context['question'], self.c.context['topic'], 2020, 'synthetic-importer')
        self.scope['evidence_refs'] = [self.c.a, self.c.review, self.c.b]
        self.handoff = proposals.prepare_handoff(self.c.package, self.scope)
        self.response = proposals.response_template(self.c.package, self.scope, self.handoff)
        self.response['candidates'] = [
            dict(text='Original synthetic proposal before rewriting.', claim_type='operator_synthesis', uncertainty=None,
                citations=[dict(reference=self.c.a, role='support')]),
            dict(text='Tentative synthetic conclusion.', claim_type='operator_synthesis', uncertainty=None, citations=[]),
            dict(text='Rejected synthetic alternative only in history.', claim_type='operator_synthesis', uncertainty='Not adopted.',
                citations=[dict(reference=self.c.b, role='challenge')])]
        self.provenance = dict(provider_id='synthetic-no-provider', model_id='synthetic-no-model', run_id='synthetic-run',
            operator_id='synthetic-importer', execution_location='unknown')
        self.reimport()

    def reimport(self):
        self.bundle = proposals.import_response(self.c.package, self.scope, self.handoff, self.response, self.provenance)
        self.adoption = proposals.review_template(self.c.package, self.bundle, 'synthetic-reviewer')
        for index, claim_id in enumerate(('claim', 'conclusion')):
            claim = dict(copy.deepcopy(self.response['candidates'][index]), claim_id=claim_id)
            if index == 0: claim['text'] = 'Explicitly revised synthetic answer intent.'
            self.adoption['decisions'][index].update(decision='accept', review_note='Synthetic explicit adoption only.', reviewed_claim=claim)
        self.adoption['decisions'][2].update(decision='reject', review_note='Synthetic rejected candidate remains historical.')
        self.envelope = proposals.export_reviewed(self.c.package, self.bundle, self.adoption)
        self.c.draft = self.envelope
        self.case.review = answer_draft.review_template(self.c.package, self.envelope, 'synthetic-answer-reviewer')
        steps = self.case.argument['steps']
        self.case.argument = argument_map.template(self.c.package, self.envelope, 'synthetic-map', self.case.review)
        self.case.argument['steps'] = steps

    def report(self): return research_journey.inspect(*self.case.args())
    def write_card(self, root):
        selection = journey_inputs.template(); selection['pattern_id'] = 'comparison'
        for name, value in [*zip(journey_inputs.REQUIRED, self.case.args()[:8]), ('declared_review', self.case.review)]:
            filename = name+'.json'; selection['artifacts'][name] = filename
            (root/filename).write_text(json.dumps(value, ensure_ascii=True)+'\n', encoding='utf-8')
        return journey_inputs.prepare(selection, root)

    def test_adoption_is_not_separate_answer_review_or_scientific_approval(self):
        answer = answer_draft.inspect(self.c.package, self.envelope)
        self.assertEqual(answer['draft_sha256'], payload_sha256(self.envelope))
        self.assertNotEqual(answer['draft_sha256'], answer['draft_content_sha256'])
        self.assertEqual([c['claim_id'] for c in answer['claims']], ['claim', 'conclusion'])
        self.assertTrue(all(row['decision'] == 'defer' for row in self.case.review['decisions']))
        result = self.report()
        self.assertEqual(result['answer_review_status'], 'DECLARED_REVIEW_INCOMPLETE')
        for key in ('automatic_approval', 'scientific_execution', 'provider_invoked', 'canonical_update_performed'):
            self.assertFalse(result[key])
        self.assertEqual(answer['historical_model_use'], 'DECLARED_NOT_AUTHENTICATED')
        self.assertEqual(answer['claims'][0]['citations'][0]['role_origin'], 'OPERATOR_ADOPTED_IMPORTED_ROLE')
        self.assertEqual(answer['proposal_review']['candidates'][0]['original_inspection']['citations'][0]['role_origin'], 'IMPORTED_PROPOSAL_NOT_OPERATOR_DECISION')
        self.assertFalse(answer['llm_used']); self.assertEqual(answer['execution_scope'], 'CURRENT_INSPECTION_ONLY')

    def test_journey_and_passive_html_keep_full_history_without_activating_it(self):
        result = self.report(); text = research_journey.render(*self.case.args())
        html = journey_html.render(*self.case.args()); document = Document(html)
        self.assertEqual(json.loads(document.saved['complete-json']), result)
        for output in (json.dumps(result), text, html):
            for value in (self.response['candidates'][0]['text'], self.response['candidates'][2]['text'],
                          'Explicitly revised synthetic answer intent.', 'synthetic-no-model', 'OPERATOR_ADOPTED_IMPORTED_SYNTHESIS'):
                self.assertIn(value, output)
        rejected_ref = next(row for row in result['evidence_routes'] if row['evidence']['reference'] == self.c.b)
        self.assertFalse(rejected_ref['actively_used_in_answer_or_design']); self.assertEqual(rejected_ref['direct_argument_uses'], [])
        self.assertEqual(result['argument_review']['steps'][0]['conclusion']['direct_citation_count'], 0)
        self.assertNotIn('NOT_RESEARCHER_ANSWERS_AUTOMATICALLY_APPROVED', html)

    def test_candidate_id_cannot_substitute_for_an_adopted_claim(self):
        for claim_id in ('answer-candidate-1', 'answer-candidate-3'):
            argument = copy.deepcopy(self.case.argument); argument['steps'][0]['premise_claim_ids'] = [claim_id]
            with self.assertRaisesRegex(ValueError, 'unknown'):
                argument_map.inspect(self.c.package, self.envelope, argument, self.case.review)

    def test_history_only_change_invalidates_review_argument_and_input_card(self):
        old = answer_draft.inspect(self.c.package, self.envelope); review = copy.deepcopy(self.case.review); argument = copy.deepcopy(self.case.argument)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); card = self.write_card(root)
            self.response['candidates'][2]['text'] = 'Changed rejected historical proposal.'; self.reimport()
            new = answer_draft.inspect(self.c.package, self.envelope)
            self.assertEqual(old['draft_content_sha256'], new['draft_content_sha256'])
            self.assertNotEqual(old['draft_sha256'], new['draft_sha256'])
            with self.assertRaises(ValueError): answer_draft.review(self.c.package, self.envelope, review)
            with self.assertRaises(ValueError): argument_map.inspect(self.c.package, self.envelope, argument, self.case.review)
            (root/'draft.json').write_text(json.dumps(self.envelope), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'bytes changed'): journey_inputs.inspect(card, root)

    def test_comparison_separates_active_claims_from_rejected_import_history(self):
        with tempfile.TemporaryDirectory() as directory:
            previous = Path(directory)/'previous'; current = Path(directory)/'current'; previous.mkdir(); current.mkdir()
            old = self.write_card(previous)
            self.response['candidates'][2]['text'] = 'Changed historical rejected candidate.'; self.provenance['run_id'] = 'synthetic-run-two'; self.reimport()
            new = self.write_card(current)
            result = journey_compare.compare(old, previous, new, current)
            groups = {row['group']: row for row in result['declared_record_comparison']}
            self.assertTrue(all(row['status'] == 'UNCHANGED_AT_DECLARED_ID' for row in groups['answer_claims']['records']))
            self.assertTrue(any(row['status'] == 'CHANGED_AT_DECLARED_ID' for row in groups['answer_proposal_candidates']['records']))
            self.assertEqual(groups['answer_proposal_import']['records'][0]['status'], 'CHANGED_AT_DECLARED_ID')
            self.assertEqual(groups['answer_proposal_import']['scope'], 'RECORDED_IMPORTED_HISTORY_NOT_OPERATOR_AUTHORSHIP_OR_ACTIVE_EVIDENCE')
            self.assertEqual(result['current_report'], journey_inputs.inspect(new, current))

    def test_comparison_manual_imported_transition_does_not_erase_history(self):
        with tempfile.TemporaryDirectory() as directory:
            previous = Path(directory)/'previous'; current = Path(directory)/'current'; previous.mkdir(); current.mkdir()
            old = self.write_card(previous)
            self.c.draft = answer_draft.template(self.c.package, self.scope['question'], 'synthetic-reviewer')
            self.c.draft['claims'] = [copy.deepcopy(row['reviewed_claim']) for row in self.adoption['decisions'] if row['decision'] == 'accept']
            self.case.review = answer_draft.review_template(self.c.package, self.c.draft, 'synthetic-answer-reviewer')
            self.case.argument = argument_map.template(self.c.package, self.c.draft, 'synthetic-map', self.case.review)
            new = self.write_card(current)
            for before, broot, after, aroot, status in ((old, previous, new, current, 'ONLY_PREVIOUS_DECLARATION'), (new, current, old, previous, 'ONLY_CURRENT_DECLARATION')):
                result = journey_compare.compare(before, broot, after, aroot)
                group = next(row for row in result['declared_record_comparison'] if row['group'] == 'answer_proposal_candidates')
                self.assertTrue(all(row['status'] == status for row in group['records']))
                self.assertIn('Recorded imported history', journey_compare.render(before, broot, after, aroot, format='text'))

    def test_source_record_origin_is_distinct_from_imported_answer_text(self):
        result = evidence_scope.disclose(self.c.package, self.c.links, self.c.proposal, self.envelope, 2020, self.case.review)
        self.assertEqual(result['answer_origin_scope'], 'ANSWER_TEXT_ORIGIN_SEPARATE_FROM_SOURCE_RECORD_ORIGIN')
        self.assertEqual(result['recorded_imported_origin_references'], [])
        self.assertEqual(result['answer_claims'][0]['origin'], 'OPERATOR_ADOPTED_IMPORTED_SYNTHESIS')
        self.assertEqual(result['answer_proposal_review']['candidates'][2]['decision'], 'reject')
        text = evidence_scope.render(self.c.package, self.c.links, self.c.proposal, self.envelope, 2020, self.case.review)
        self.assertIn(self.response['candidates'][2]['text'], text)
        self.assertIn('source-record origins remain separate', text)

    def test_revision_impact_preserves_previous_history_without_rebinding(self):
        result = revision_impact.inspect(self.c.package, self.c.package, self.c.links, self.c.proposal, self.envelope, 2020)
        self.assertEqual(result['previous_answer_history_scope'], 'PREVIOUS_DRAFT_ONLY_NOT_REBOUND_TO_CURRENT_PACKAGE')
        self.assertEqual(result['previous_answer_proposal_review']['candidates'][2]['decision'], 'reject')
        self.assertFalse(result['automatic_rebinding']); self.assertFalse(result['source_reread'])
        self.assertIn(self.response['candidates'][2]['text'], revision_impact.render(result))

    def test_package_only_change_marks_imported_envelope_stale(self):
        current = copy.deepcopy(self.c.package); current['extra_review_note'] = 'Changed synthetic package metadata.'
        result = revision_impact.inspect(self.c.package, current, self.c.links, self.c.proposal, self.envelope, 2020)
        self.assertTrue(result['old_artifacts_stale_for_current_package']); self.assertTrue(result['all_artifacts_require_binding_review'])
        self.assertEqual(result['changed_reference_count'], 0)
        self.assertNotEqual(result['previous_full_package_sha256'], result['current_full_package_sha256'])
        with self.assertRaises(ValueError): answer_draft.inspect(current, self.envelope)

    def test_synthetic_freeze_keeps_full_draft_identity_but_only_active_metadata(self):
        result = evaluate_synthetic.freeze(dict(package=self.c.package, ignored_cache='not evidence'), self.envelope)
        self.assertEqual(result['draft_sha256'], payload_sha256(self.envelope))
        self.assertEqual([row['claim_id'] for row in result['claims']], ['claim', 'conclusion'])
        self.assertFalse(any(citation['reference'] == self.c.b for row in result['claims'] for citation in row['citations']))
        self.assertNotIn(self.response['candidates'][2]['text'], json.dumps(result))

    def test_invalid_envelope_fails_before_current_source_reads(self):
        selection = source_recheck.template(self.c.package, 'synthetic-source')
        for row in selection['sources']: row['source_file'] = row['paper_id']+'.md'
        with patch.object(source_recheck, 'audit', wraps=source_recheck.audit) as checked:
            result = research_journey.inspect(*self.case.args(), source_selection=selection, source_root=ROOT/'examples/synthetic-sources')
            self.assertEqual(checked.call_count, 1); self.assertTrue(result['source_reread'])
        bad = copy.deepcopy(self.envelope); bad['review']['decisions'][2]['decision'] = 'defer'; self.c.draft = bad
        with patch.object(source_recheck, 'audit', side_effect=AssertionError('no source access before invalid history rejection')):
            with self.assertRaises(ValueError): research_journey.inspect(*self.case.args(), source_selection=selection, source_root=ROOT/'examples/synthetic-sources')

    def test_untrusted_history_is_escaped_in_static_html_and_inputs_unchanged(self):
        attack = '<script src="https://invalid.example/x">not executable</script>&\nSynthetic text.'
        self.response['candidates'][2]['text'] = attack; self.reimport(); before = copy.deepcopy(self.case.args())
        html = journey_html.render(*self.case.args()); self.assertNotIn('<script src=', html)
        saved = json.loads(Document(html).saved['complete-json'])
        self.assertEqual(saved['argument_review']['answer']['proposal_review']['candidates'][2]['candidate']['proposed_claim']['text'], attack)
        self.assertEqual(self.case.args(), before)

    def test_actual_input_card_cli_keeps_adoption_and_answer_review_separate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); card = self.write_card(root); (root/'card.json').write_text(json.dumps(card), encoding='utf-8')
            result = subprocess.run([sys.executable, str(ROOT/'journey_inputs.py'), 'inspect', str(root/'card.json'), '--input-root', str(root)],
                cwd=directory, capture_output=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8'))
            report = json.loads(result.stdout)
            self.assertEqual(report['answer_review_status'], 'DECLARED_REVIEW_INCOMPLETE')
            self.assertEqual(report['argument_review']['answer']['origin'], 'OPERATOR_REVIEWED_IMPORTED_ANSWER_PROPOSALS')


if __name__ == '__main__': unittest.main()
