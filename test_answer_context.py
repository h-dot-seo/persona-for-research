"""Mechanical scope contracts; not scientific or researcher-fidelity validation."""
import copy
import json
import unittest
from unittest.mock import patch

import answer_context as context
import test_research_journey as journey_fixture
import test_pattern_evidence_reasons as imported_fixture
from applicability_review import template as context_template
from persona import payload_sha256
from pattern_proposals import export_reviewed


class AnswerContextTests(unittest.TestCase):
    def setUp(self):
        fixture = journey_fixture.ResearchJourneyTests(); fixture.setUp()
        self.case = fixture.case
        self.package = self.case.package
        self.raw = dict(patterns=self.case.patterns, context=self.case.context,
                        publication_relations=fixture.relations, pattern_id='comparison')
        self.refs = [self.case.a]

    def args(self):
        c = self.raw['context']
        return [self.package, self.raw, c['question'], c['topic'], c['reference_year'], self.refs]

    def report(self): return context.inspect(*self.args())

    def test_schema_and_full_bindings(self):
        r = self.report(); b = r['bindings']
        self.assertEqual(r['schema'], 'persona.answer-research-context.v1')
        self.assertEqual(r['status'], 'INSPECTED_NOT_APPROVED_RESEARCH_CONTEXT')
        self.assertEqual(b['package_sha256'], payload_sha256(self.package))
        self.assertEqual(b['raw_sha256'], payload_sha256(self.raw))
        for field, key in [('patterns', 'pattern_form_sha256'), ('context', 'context_form_sha256'),
                           ('publication_relations', 'publication_relation_form_sha256')]:
            self.assertEqual(b[key], payload_sha256(self.raw[field]))
        self.assertEqual(b['evidence_refs_sha256'], payload_sha256(self.refs))
        self.assertEqual(b['question'], self.args()[2]); self.assertEqual(b['topic'], self.args()[3])
        self.assertEqual(b['reference_year'], 2020); self.assertEqual(b['pattern_id'], 'comparison')
        self.assertEqual(r['report_input_sha256'], payload_sha256(b))

    def test_exact_citable_scope_never_expands(self):
        r = self.report()
        self.assertEqual(r['evidence_refs'], self.refs)
        self.assertEqual(r['citable_scope']['evidence_refs'], self.refs)
        self.assertEqual(r['citable_scope']['reference_sha256'], [payload_sha256(self.case.a)])
        self.assertFalse(r['citable_scope']['context_expands_citation_scope'])
        selected = [x['evidence']['reference'] for x in r['selected_pattern_context_routes'] if x['explicitly_selected_for_answer_citation']]
        self.assertEqual(selected, self.refs)
        self.assertEqual(r['answer_citation_publication_scope']['selected_paper_ids'], ['synthetic-0'])
        self.assertEqual(len(r['selected_pattern_publication_scope']['selected_paper_ids']), 2)

    def test_empty_selection_is_valid_and_has_no_citable_context(self):
        self.refs = []; r = self.report()
        self.assertEqual(r['evidence_refs'], [])
        self.assertEqual(r['answer_citation_publication_scope']['selected_paper_ids'], [])
        self.assertTrue(all(not row['explicitly_selected_for_answer_citation'] for row in r['selected_pattern_context_routes']))

    def test_three_relation_projections_always_have_year(self):
        r = self.report()
        for key in ('answer_citation_publication_scope', 'selected_pattern_publication_scope', 'topic_publication_scope'):
            s = r[key]; self.assertEqual(s['reference_year'], 2020)
            rows = s['relations_between_selected_papers'] + s['relations_to_other_supplied_papers']
            self.assertTrue(rows)
            self.assertEqual(rows[0]['publication_reference_scope']['from_publication'], 'AFTER_REFERENCE_YEAR')
            self.assertIn('basis_reference_scopes', rows[0])
        self.assertNotIn('publication_context_scope', r['publication_timeline'])
        self.assertEqual([g['publication_year'] for g in r['publication_timeline']['years']], [2020, 2021])

    def test_timeline_is_called_without_relations(self):
        from publication_timeline import timeline
        with patch('publication_timeline.timeline', wraps=timeline) as call:
            self.report()
        call.assert_called_once_with(self.package, self.raw['context']['topic'])

    def test_same_year_is_unresolved_not_available(self):
        self.raw['context'] = context_template(self.package, self.args()[2], 'Context', self.args()[3], 2021, 'op')
        r = self.report()
        later = [x for x in r['selected_pattern_context_routes'] if x['evidence']['publication_year'] == 2021]
        self.assertTrue(later)
        self.assertTrue(all(x['publication_scope'] == 'SAME_YEAR_ORDER_UNRESOLVED' for x in later))
        self.assertTrue(all('SAME_YEAR_ORDER_UNRESOLVED' in x['review_prompts'] for x in later))

    def test_enclosing_only_assessment_no_component_approval(self):
        r = self.report()
        row = next(x for x in r['selected_pattern_context_routes'] if x['evidence']['reference'] == self.case.b)
        self.assertEqual(row['context_match_basis'], 'ENCLOSING_OBSERVATION_ONLY')
        self.assertIsNone(row['context_assessment']['evidence']['reference']['dimension'])
        self.assertFalse(row['component_approval_inherited'])
        self.assertFalse(row['explicitly_selected_for_answer_citation'])

    def test_exclusion_does_not_ban_citation(self):
        row = next(x for x in self.report()['selected_pattern_context_routes'] if x['evidence']['reference'] == self.case.a)
        self.assertEqual(row['context_decision'], 'exclude')
        self.assertTrue(row['explicitly_selected_for_answer_citation'])
        self.assertFalse(row['citation_prohibited_by_exclude'])

    def test_defer_missing_comparison_uncertainty_and_late_year(self):
        row = next(x for x in self.report()['selected_pattern_context_routes'] if x['evidence']['reference'] == self.case.b)
        for code in ('CONTEXT_DECISION_DEFERRED', 'CONTEXT_COMPARISON_NOT_SUPPLIED', 'REMAINING_UNCERTAINTY_NOT_SUPPLIED', 'AFTER_REFERENCE_YEAR'):
            self.assertIn(code, row['review_prompts'])

    def test_absent_assessment_not_inferred_from_reference(self):
        self.raw['context'] = context_template(self.package, self.args()[2], 'Context', 'other topic', 2020, 'op')
        r = self.report()
        self.assertEqual(r['publication_timeline']['years'], [])
        self.assertEqual(r['topic_publication_scope']['selected_paper_ids'], [])
        for row in r['selected_pattern_context_routes']:
            self.assertIsNone(row['context_assessment']); self.assertEqual(row['context_decision'], 'NOT_SUPPLIED')
            self.assertIn('NO_ENCLOSING_OBSERVATION_CONTEXT_ASSESSMENT', row['review_prompts'])

    def test_all_context_assessments_and_counterevidence_retained(self):
        self.raw['patterns']['hypotheses'][0]['support_refs'] = [self.case.a]
        self.raw['patterns']['hypotheses'][0]['challenge_refs'] = []
        r = self.report()
        self.assertEqual(len(r['context_review']['assessments']), 2)
        self.assertTrue(r['context_review']['assessments'][0]['counterevidence'])
        self.assertIn('Operator-selected counterevidence', context.render(r))

    def test_unselected_patterns_are_preserved_not_routes(self):
        other = copy.deepcopy(self.raw['patterns']['hypotheses'][0]); other['pattern_id'] = 'unselected'
        other['operator_hypothesis'] = 'Unselected hypothesis remains context only.'
        self.raw['patterns']['hypotheses'].append(other)
        r = self.report(); self.assertEqual(len(r['pattern_review']['hypotheses']), 2)
        self.assertEqual(r['selected_pattern']['pattern_id'], 'comparison')
        self.assertIn(other['operator_hypothesis'], context.render(r))

    def test_imported_original_reviewed_rejected_history_and_reasons(self):
        c = imported_fixture.PatternEvidenceReasonTests(); c.setUp()
        extra = copy.deepcopy(c.proposal); extra['proposed_hypothesis'] = 'Rejected synthetic alternative.'
        c.response['candidates'].append(extra); c.reimport(); c.accept()
        c.review['decisions'][1].update(decision='reject', review_note='Rejected interpretation.')
        self.raw['patterns'] = export_reviewed(c.package, c.bundle, c.review)
        r = self.report(); history = r['pattern_review']['proposal_review']
        self.assertEqual(sum(x['decision'] == 'reject' for x in history['candidates']), 1)
        self.assertIn('Model proposed', json.dumps(history))
        self.assertIn('Reviewer supplied', json.dumps(r['selected_pattern_context_routes']))
        text = context.render(r)
        for phrase in ('Rejected synthetic alternative.', 'Model proposed', 'Reviewer supplied'):
            self.assertIn(phrase, text)

    def test_question_topic_and_year_require_exact_match(self):
        for index, value in ((2, self.args()[2].upper()), (3, self.args()[3].upper()), (4, 2021)):
            args = self.args(); args[index] = value
            with self.subTest(index=index), self.assertRaisesRegex(ValueError, 'match'):
                context.inspect(*args)

    def test_invalid_pattern_ids_reject(self):
        for value in ('absent', '', ' ', None, True, 1, [], {}):
            self.raw['pattern_id'] = value
            with self.subTest(value=value), self.assertRaises(ValueError): self.report()

    def test_cached_inspection_reports_reject(self):
        r = self.report()
        for name, key in [('patterns', 'pattern_review'), ('context', 'context_review'), ('publication_relations', 'publication_context_review')]:
            original = self.raw[name]; self.raw[name] = r[key]
            with self.subTest(name=name), self.assertRaises(ValueError): self.report()
            self.raw[name] = original

    def test_raw_null_missing_extra_keys_reject(self):
        for raw in (None, [], {}, dict(self.raw, extra=True), {k:v for k,v in self.raw.items() if k != 'publication_relations'}):
            args = self.args(); args[1] = raw
            with self.subTest(raw=raw), self.assertRaises(ValueError): context.inspect(*args)
        for key in self.raw:
            args = copy.deepcopy(self.args()); args[1][key] = None
            with self.subTest(key=key), self.assertRaises(ValueError): context.inspect(*args)

    def test_invalid_text_and_year_types_reject(self):
        for index, values in [(2, [None, '', ' ', 1, True]), (3, [None, '', ' ', 1, True]), (4, [None, True, 2020.0, 0, 10000, '2020'])]:
            for value in values:
                args = self.args(); args[index] = value
                with self.subTest(index=index, value=value), self.assertRaises(ValueError): context.inspect(*args)

    def test_explicit_refs_unique_exact_bounded_and_typed(self):
        for refs in (None, {}, (self.case.a,), [self.case.a]*2, [self.case.a]*65,
                     [dict(self.case.a, extra=True)], [dict(self.case.a, observation_index=True)],
                     [dict(self.case.a, paper_id='missing')], [dict(self.case.a, dimension='missing')]):
            self.refs = refs
            with self.subTest(refs=refs), self.assertRaises(ValueError): self.report()

    def test_nonfinite_nonjson_values_reject(self):
        for value in (float('nan'), float('inf'), float('-inf'), ('tuple',), {1: 'integer key'}, object()):
            self.raw['extra'] = value
            with self.subTest(value=value), self.assertRaises(ValueError): self.report()

    def test_input_output_bounds(self):
        with patch.object(context, 'MAX_INPUT_BYTES', 10):
            with self.assertRaisesRegex(ValueError, '8 MiB'): self.report()
        with patch.object(context, 'MAX_OUTPUT_BYTES', 10):
            with self.assertRaisesRegex(ValueError, '16 MiB'): self.report()
        r = self.report()
        with patch.object(context, 'MAX_OUTPUT_BYTES', len(context.encode_result(r))):
            # Text contains all review prose and scoped fields and may be smaller than JSON.
            output = context.render(r)
            self.assertLessEqual(len(output.encode('utf-8')), context.MAX_OUTPUT_BYTES)

    def test_detached_outputs_and_render_do_not_mutate(self):
        before = copy.deepcopy(self.args()); r = self.report(); original = copy.deepcopy(r)
        context.render(r); self.assertEqual(r, original)
        r['selected_pattern']['evidence'][0]['declared_roles'].append('fake')
        r['context_review']['assessments'][0]['evidence']['observation']['method'] = 'mutated'
        r['evidence_refs'][0]['paper_id'] = 'mutated'
        self.assertEqual(before, self.args())
        self.assertEqual(original['pattern_review'], r['pattern_review'])
        self.assertEqual(r['citable_scope']['evidence_refs'], self.refs)

    def test_render_escapes_controls_and_preserves_scopes(self):
        self.raw['patterns']['hypotheses'][0]['scope_note'] = 'Scope\nFORGED\x1b\u202e'
        text = context.render(self.report())
        self.assertNotIn('\x1b', text); self.assertNotIn('\u202e', text)
        self.assertIn('Scope\\u000aFORGED', text)
        for key in ('answer_citation_publication_scope', 'selected_pattern_publication_scope', 'topic_publication_scope',
                    'selected_pattern_context_routes', 'evidence_refs_sha256', 'publication_timeline'):
            self.assertIn(key, text)

    def test_consider_is_not_component_approval(self):
        assessment = self.raw['context']['assessments'][0]
        assessment['decision'] = 'consider'
        row = next(x for x in self.report()['selected_pattern_context_routes'] if x['evidence']['reference'] == self.case.a)
        self.assertEqual(row['context_decision'], 'consider')
        self.assertFalse(row['component_approval_inherited'])

    def test_before_reference_year_and_ref_order_binding(self):
        self.raw['context'] = context_template(self.package, self.args()[2], 'Context', self.args()[3], 2022, 'op')
        self.refs = [self.case.a, self.case.b]
        r = self.report()
        self.assertTrue(all(x['publication_scope'] == 'BEFORE_REFERENCE_YEAR' for x in r['selected_pattern_context_routes']))
        self.refs.reverse()
        self.assertNotEqual(r['bindings']['evidence_refs_sha256'], self.report()['bindings']['evidence_refs_sha256'])
        self.assertEqual(self.report()['evidence_refs'], self.refs)

    def test_render_final_text_bound_without_truncation(self):
        r = self.report(); encoded = context.encode_result(r)
        with patch.object(context, 'encode_result', return_value=encoded), patch.object(context, 'MAX_OUTPUT_BYTES', 10):
            with self.assertRaisesRegex(ValueError, 'text exceeds 16 MiB'): context.render(r)

    def test_no_files_are_read_or_written_during_inspection(self):
        with patch('builtins.open', side_effect=AssertionError('file access forbidden')), \
                patch('pathlib.Path.read_bytes', side_effect=AssertionError('source reread forbidden')), \
                patch('subprocess.run', side_effect=AssertionError('external execution forbidden')):
            context.render(self.report())

    def test_stale_forms_and_package_fail_closed(self):
        for field in ('patterns', 'context', 'publication_relations'):
            original = self.raw[field]['persona_sha256']
            self.raw[field]['persona_sha256'] = '0' * 64
            with self.subTest(field=field), self.assertRaises(ValueError): self.report()
            self.raw[field]['persona_sha256'] = original
        self.package['persona']['knowledge_papers_sha256'] = '0' * 64
        with self.assertRaises(ValueError): self.report()

    def test_execution_boundaries(self):
        r = self.report()
        self.assertTrue(r['human_review_required'])
        for key in ('source_reread', 'provider_invoked', 'browser_used', 'llm_used', 'external_transmission',
                    'canonical_update_performed', 'scientific_execution', 'automatic_approval',
                    'human_review_authenticated', 'source_selection_performed'):
            self.assertIs(r[key], False)
        self.assertEqual(r['scientific_validation'], 'NOT_PERFORMED')
        self.assertEqual(r['semantic_validation'], 'NOT_PERFORMED')
        self.assertIn('Recorded source checks are not reread', r['boundary'])


if __name__ == '__main__': unittest.main()
