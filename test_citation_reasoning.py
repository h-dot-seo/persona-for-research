"""Synthetic, offline per-use reasoning inventory and strict CLI boundaries."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import answer_draft as ad
import answer_proposals as ap
import citation_reasoning as cr
import test_answer_draft as manual_fixture
import test_answer_proposals as imported_fixture
from extraction_adapter import MockProvider
from persona import payload_sha256

ROOT = Path(__file__).resolve().parent
EXPLANATION = dict(rationale='A synthetic declared comparison.', context_boundary=None)


class CitationReasoningTests(unittest.TestCase):
    def setUp(self):
        case = manual_fixture.AnswerDraftTests(); case.setUp()
        self.p, self.d = case.package, case.draft

    def test_three_states_and_null_context_boundary_are_distinct(self):
        self.d['claims'][1]['citations'][0]['explanation'] = None
        self.d['claims'][1]['citations'][1]['explanation'] = copy.deepcopy(EXPLANATION)
        result = cr.audit(self.p, self.d)
        self.assertEqual([u['explanation']['state'] for u in result['citation_uses']], list(cr.STATES))
        self.assertNotIn('declaration', result['citation_uses'][0]['explanation'])
        self.assertIsNone(result['citation_uses'][1]['explanation']['declaration'])
        self.assertIsNone(result['citation_uses'][2]['explanation']['declaration']['context_boundary'])
        self.assertEqual(result['inventory']['explanation_states'], dict.fromkeys(cr.STATES, 1))
        self.assertEqual(result['final_review'], 'NOT_SUPPLIED')

    def test_identity_includes_claim_reference_role_and_dimension(self):
        synth = self.d['claims'][1]
        synth['citations'].append(dict(role='context', reference=copy.deepcopy(synth['citations'][0]['reference'])))
        synth['citations'].append(dict(role='support', reference=dict(synth['citations'][0]['reference'], dimension=None)))
        clone = copy.deepcopy(synth); clone['claim_id'] = 'second'; self.d['claims'].append(clone)
        uses = cr.audit(self.p, self.d)['citation_uses']
        self.assertEqual(len(uses), 9)
        self.assertEqual(len({u['citation_use_sha256'] for u in uses}), 9)
        for use in uses:
            self.assertEqual(use['citation_use_sha256'], payload_sha256(use['use_key']))
            self.assertEqual(use['use_key']['reference'], use['evidence']['reference'])

    def test_final_review_preserves_all_claims_and_missing_explanations(self):
        for decision in ('retain', 'reject', 'revise', 'defer'):
            with self.subTest(decision=decision):
                review = ad.review_template(self.p, self.d, 'reviewer')
                for row in review['decisions']: row['decision'] = decision
                result = cr.audit(self.p, self.d, review)
                self.assertEqual(len(result['current_claims']), 2)
                self.assertEqual(len(result['citation_uses']), 3)
                self.assertTrue(all(u['claim']['final_review']['decision'] == decision for u in result['citation_uses']))
                self.assertTrue(all(u['explanation']['state'] == 'LEGACY_KEY_ABSENT' for u in result['citation_uses']))
                self.assertEqual(result['bindings']['review_sha256'], payload_sha256(review))

    def test_empty_and_uncited_are_distinct_and_never_inherit_citations(self):
        uncited = copy.deepcopy(self.d['claims'][1]); uncited.update(claim_id='uncited', citations=[])
        self.d['claims'].append(uncited)
        result = cr.audit(self.p, self.d)
        self.assertEqual([c['claim_id'] for c in result['uncited_claims']], ['uncited'])
        self.assertEqual(result['inventory']['citation_uses'], 3)
        self.d['claims'] = []
        result = cr.audit(self.p, self.d)
        self.assertEqual(result['status'], 'NO_CURRENT_DRAFT_CLAIMS')
        self.assertEqual(result['current_claims'], [])
        self.assertEqual(result['uncited_claims'], [])

    def test_evidence_preserves_labels_and_stored_quote_only(self):
        result = cr.audit(self.p, self.d); uses = result['citation_uses']
        self.assertEqual(uses[0]['claim']['quote_check'], 'EQUALS_STORED_QUOTE_ONLY')
        self.assertEqual(uses[0]['evidence']['source_kind'], 'review')
        self.assertEqual(uses[0]['evidence']['component']['claim_type'], 'explicit_statement')
        self.assertIn('recorded_source_check', uses[0]['evidence'])
        self.assertEqual(uses[0]['evidence'], ad.inspect(self.p, self.d)['claims'][0]['citations'][0]['evidence'])
        self.assertEqual(result['current_claims'][0]['origin'], 'OPERATOR_SUPPLIED_DRAFT')

    def test_wrapper_is_not_trusted_but_full_canonical_package_is_bound(self):
        first = cr.audit(self.p, self.d)
        wrapped = dict(package=self.p, cached_report={'status': 'APPROVED'}, arbitrary='ignored')
        self.assertEqual(first, cr.audit(wrapped, self.d))
        changed = dict(self.p, descriptive_annotation='different full canonical payload')
        second = cr.audit(changed, self.d)
        self.assertNotEqual(first['bindings']['package_sha256'], second['bindings']['package_sha256'])
        self.assertEqual(first['bindings']['persona_sha256'], second['bindings']['persona_sha256'])
        with self.assertRaises(ValueError): cr.audit(self.p, first)

    def test_stale_review_rejected(self):
        review = ad.review_template(self.p, self.d, 'reviewer')
        self.d['claims'][1]['citations'][0]['explanation'] = None
        with self.assertRaisesRegex(ValueError, 'stale'): cr.audit(self.p, self.d, review)

    def test_deterministic_detached_and_no_source_or_provider_calls(self):
        before = copy.deepcopy((self.p, self.d))
        with patch.object(MockProvider, 'extract', side_effect=AssertionError('provider')), patch.object(Path, 'open', side_effect=AssertionError('source read')):
            result = cr.audit(self.p, self.d)
            self.assertEqual(result, cr.audit(self.p, self.d))
        result['citation_uses'][0]['evidence']['observation']['method'] = 'edited'
        self.assertEqual((self.p, self.d), before)
        self.assertFalse(result['llm_used'])
        self.assertTrue(all(v is False for k, v in result['processing'].items() if k != 'scope'))

    def test_invalid_quote_explanation_and_references_fail_closed(self):
        bad = copy.deepcopy(self.d); bad['claims'][0]['text'] += ' '
        with self.assertRaises(ValueError): cr.audit(self.p, bad)
        for explanation in ({}, False, dict(EXPLANATION, rationale=''), dict(EXPLANATION, rationale='x'*2001), dict(EXPLANATION, context_boundary=5)):
            bad = copy.deepcopy(self.d); bad['claims'][1]['citations'][0]['explanation'] = explanation
            with self.assertRaises(ValueError): cr.audit(self.p, bad)
        bad = copy.deepcopy(self.d); bad['claims'][1]['citations'][0]['reference']['observation_index'] = True
        with self.assertRaises(ValueError): cr.audit(self.p, bad)

    def test_api_finite_strict_json_and_bounds(self):
        for value in (float('nan'), float('inf'), (1,), {1: 'coercion'}, object()):
            with self.subTest(value=repr(value)):
                with self.assertRaises(ValueError): cr.audit(dict(self.p, extra=value), self.d)
        with patch.object(cr, 'MAX_INPUT_BYTES', 100):
            with self.assertRaisesRegex(ValueError, '8 MiB'): cr.audit(self.p, self.d)
        with patch.object(cr, 'MAX_OUTPUT_BYTES', 100):
            with self.assertRaisesRegex(ValueError, '16 MiB'): cr.audit(self.p, self.d)
        recursive = []; recursive.append(recursive)
        with self.assertRaises(ValueError): cr.audit(recursive, self.d)

    def test_text_output_controls_and_bound(self):
        self.d['question'] = '합성\n\x1b[31m\tquestion'
        result = cr.audit(self.p, self.d); text = cr.render(result)
        self.assertNotIn('\x1b', text)
        self.assertIn('\\u001b', text)
        self.assertIn('LEGACY_KEY_ABSENT', text)
        with patch.object(cr, 'MAX_OUTPUT_BYTES', len(text.encode('utf-8')) - 1):
            with self.assertRaisesRegex(ValueError, '16 MiB'): cr.render(result)


class ImportedCitationReasoningTests(unittest.TestCase):
    def fixture(self, version=1):
        c = imported_fixture.AnswerProposalTests(); c.setUp()
        if version == 2:
            c.scope = ap.template(c.package, c.scope['question'], c.scope['topic'], c.scope['reference_year'], c.scope['operator_id'], include_citation_explanations=True)
            c.scope['evidence_refs'] = [copy.deepcopy(x['reference']) for x in c.candidate['citations']]
            c.handoff = ap.prepare_handoff(c.package, c.scope)
            c.response = ap.response_template(c.package, c.scope, c.handoff)
            c.response['candidates'] = [copy.deepcopy(c.candidate)]
            for citation in c.response['candidates'][0]['citations']: citation['explanation'] = None
        other = copy.deepcopy(c.response['candidates'][0]); other['text'] = 'Rejected synthetic original.'
        c.response['candidates'].append(other); c.reimport(); c.accept()
        c.review['decisions'][0]['reviewed_claim']['text'] = 'Revised adopted synthetic comparison.'
        c.review['decisions'][1].update(decision='reject', review_note='Synthetic rejection.')
        return c

    def test_v1_v2_complete_nonactive_history_and_current_counts(self):
        for version in (1, 2):
            with self.subTest(version=version):
                c = self.fixture(version); envelope = c.envelope(); result = cr.audit(c.package, envelope)
                history = result['proposal_history']
                self.assertFalse(history['active']); self.assertFalse(history['counted_as_current_citation_uses'])
                self.assertEqual(history['packet'], c.packet())
                self.assertEqual(result['inventory']['claims'], 1)
                self.assertEqual(result['inventory']['citation_uses'], 2)
                self.assertNotEqual(history['packet']['candidates'][0]['candidate']['proposed_claim']['text'], result['current_claims'][0]['text'])
                self.assertEqual(history['packet']['candidates'][1]['decision'], 'reject')
                self.assertIn('Rejected synthetic original.', cr.render(result))
                self.assertEqual(result['bindings']['draft_sha256'], payload_sha256(envelope))
                self.assertNotEqual(result['bindings']['draft_sha256'], ad.inspect(c.package, envelope)['draft_content_sha256'])
                self.assertIn('IMPORTED', result['current_claims'][0]['origin'])
                if version == 2:
                    self.assertEqual(result['citation_uses'][0]['explanation']['origin'], 'OPERATOR_ADOPTED_IMPORTED_INTERPRETATION')

    def test_changed_rejected_history_binds_full_draft_and_stales_review(self):
        c = self.fixture(); envelope = c.envelope(); final = ad.review_template(c.package, envelope, 'final reviewer')
        first = cr.audit(c.package, envelope, final)
        c.review['decisions'][1]['review_note'] = 'Changed rejection note.'
        changed = c.envelope()
        self.assertNotEqual(first['bindings']['draft_sha256'], cr.audit(c.package, changed)['bindings']['draft_sha256'])
        with self.assertRaisesRegex(ValueError, 'stale'): cr.audit(c.package, changed, final)

    def test_invalid_exported_envelopes_are_not_relaxed(self):
        c = self.fixture(); envelope = c.envelope()
        for decision in ('defer', 'reject'):
            bad = copy.deepcopy(envelope)
            bad['review']['decisions'][0] = dict(candidate_id=c.review['decisions'][0]['candidate_id'], decision=decision, review_note='Unfinished or rejected.')
            with self.assertRaisesRegex(ValueError, 'resolve every candidate'): cr.audit(c.package, bad)
        bad = copy.deepcopy(envelope)
        bad['review']['decisions'][0]['reviewed_claim']['citations'][0]['explanation'] = None
        with self.assertRaises(ValueError): cr.audit(c.package, bad)
        bad = copy.deepcopy(envelope); bad['extra'] = True
        with self.assertRaises(ValueError): cr.audit(c.package, bad)


class CitationReasoningCLITests(unittest.TestCase):
    def setUp(self):
        c = manual_fixture.AnswerDraftTests(); c.setUp(); self.p, self.d = c.package, c.draft
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.pfile = self.write('package.json', self.p); self.dfile = self.write('draft.json', self.d)

    def write(self, name, value):
        path = self.dir/name; path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8'); return path

    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(ROOT/'citation_reasoning.py'), *map(str, args)], capture_output=True)

    def test_real_json_text_and_review_arguments(self):
        self.d['question'] = '합성 연구 질문'; self.write('draft.json', self.d)
        review = ad.review_template(self.p, self.d, 'reviewer'); rfile = self.write('review.json', review)
        result = self.run_cli(self.pfile, self.dfile, '--review', rfile)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), cr.audit(self.p, self.d, review))
        text = self.run_cli(self.pfile, self.dfile, '--format', 'text')
        self.assertEqual(text.returncode, 0, text.stderr)
        self.assertEqual(text.stdout.decode('utf-8'), cr.render(cr.audit(self.p, self.d)))

    def test_cli_strict_json_errors_stdout_empty(self):
        for raw in ('{"x":1,"x":2}', '{"x":NaN}', '{"x":1e999}', '{bad', 'null'):
            self.dfile.write_text(raw, encoding='utf-8')
            result = self.run_cli(self.pfile, self.dfile)
            self.assertNotEqual(result.returncode, 0); self.assertEqual(result.stdout, b'')
        self.write('draft.json', self.d)
        for args in ((self.pfile,), (self.pfile, self.dfile, '--format', 'xml'), (self.pfile, self.dfile, '--review', self.write('null.json', None))):
            result = self.run_cli(*args)
            self.assertNotEqual(result.returncode, 0); self.assertEqual(result.stdout, b'')

    def test_cli_combined_raw_input_size_bound(self):
        self.dfile.write_bytes(b' ' * cr.MAX_INPUT_BYTES + b'{}')
        result = self.run_cli(self.pfile, self.dfile)
        self.assertNotEqual(result.returncode, 0); self.assertEqual(result.stdout, b'')
        self.assertIn(b'8 MiB', result.stderr)


if __name__ == '__main__': unittest.main()
