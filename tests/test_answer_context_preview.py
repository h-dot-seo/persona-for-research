"""Offline preview scope contracts, not semantic or researcher-fidelity approval."""
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import answer_context as ac
import answer_draft as ad
import answer_proposals as ap
import pattern_proposals as pp
import tests.test_research_journey as fixture
import tests.test_pattern_evidence_reasons as imported_fixture
from persona import payload_sha256
from reasoning_links import _endpoint, _sources
from review_package import display

ROOT = Path(__file__).resolve().parents[1]


class AnswerContextPreviewTests(unittest.TestCase):
    def setUp(self):
        f = fixture.ResearchJourneyTests(); f.setUp()
        self.c = f.case; self.p = self.c.package
        self.raw = dict(patterns=copy.deepcopy(self.c.patterns), context=copy.deepcopy(self.c.context),
                        publication_relations=copy.deepcopy(f.relations), pattern_id='comparison')
        c = self.raw['context']
        self.s = ap.template(self.p, c['question'], c['topic'], c['reference_year'], 'preview-operator',
                             include_citation_explanations=True, research_context=self.raw)
        self.raw = self.s['research_context']

    def report(self): return ap.inspect_context(self.p, self.s)

    def test_zero_refs_is_prominent_and_prepare_remains_strict(self):
        r = self.report()
        self.assertEqual(r['schema'], 'persona.answer-context-preview.v1')
        self.assertEqual(r['citation_selection_status'], 'NO_EXACT_CITATIONS_SELECTED')
        self.assertEqual(r['exact_selected_evidence'], [])
        self.assertIn('No exact citations selected; prepare requires 1 to 64', ap.render_context(r))
        with self.assertRaisesRegex(ValueError, '1 to 64 explicit references'):
            ap.prepare_handoff(self.p, self.s)
        self.assertEqual(r['reasoning_context']['citable_scope']['evidence_refs'], [])

    def test_all_selected_evidence_matches_existing_handoff_and_context(self):
        self.s['evidence_refs'] = [self.c.a, self.c.b, self.c.review]
        r = self.report(); h = ap.prepare_handoff(self.p, self.s)
        self.assertEqual(r['exact_selected_evidence'], h['evidence'])
        self.assertEqual(r['reasoning_context'], h['reasoning_context'])
        self.assertEqual(r['reasoning_context'], ac.inspect(self.p, self.raw, self.s['question'],
            self.s['topic'], self.s['reference_year'], self.s['evidence_refs']))
        _, papers = _sources(self.p)
        for ref, row in zip(self.s['evidence_refs'], r['exact_selected_evidence']):
            self.assertEqual(row['evidence'], _endpoint(ref, papers))
            for key in ('source_sha256', 'source_locator', 'reference', 'attribution'):
                self.assertIn(key, row['evidence'])
        self.assertEqual([x['publication_scope'] for x in r['exact_selected_evidence']],
                         ['SAME_YEAR_ORDER_UNRESOLVED', 'AFTER_REFERENCE_YEAR', 'AFTER_REFERENCE_YEAR'])

    def test_outside_selected_pattern_resolves_and_displays_full_passage(self):
        self.raw['patterns']['hypotheses'][0]['challenge_refs'] = []
        self.s['evidence_refs'] = [self.c.review]
        r = self.report(); row = r['exact_selected_evidence'][0]
        self.assertNotIn(self.c.review, [x['evidence']['reference'] for x in r['reasoning_context']['selected_pattern_context_routes']])
        text = ap.render_context(r); node = row['evidence']
        self.assertIn(display(node['observation']['evidence_quote']), text)
        self.assertIn(display(node['observation']['locator']), text)
        self.assertIn(node['source_sha256'], text)
        self.assertEqual(r['evidence_refs'], [self.c.review])

    def test_excluded_selected_citation_is_not_banned_and_context_never_expands(self):
        self.s['evidence_refs'] = [self.c.a]
        r = self.report(); inner = r['reasoning_context']
        row = next(x for x in inner['selected_pattern_context_routes'] if x['evidence']['reference'] == self.c.a)
        self.assertEqual(row['context_decision'], 'exclude')
        self.assertFalse(row['citation_prohibited_by_exclude'])
        self.assertEqual(inner['citable_scope']['evidence_refs'], [self.c.a])
        self.assertFalse(inner['citable_scope']['context_expands_citation_scope'])
        self.assertTrue(any(x['context_decision'] == 'defer' for x in inner['selected_pattern_context_routes']))
        self.assertIn('counterevidence', json.dumps(inner))
        for key in ('answer_citation_publication_scope', 'selected_pattern_publication_scope', 'topic_publication_scope'):
            self.assertIn(key, inner)

    def test_consider_and_unselected_patterns_preserved_unchanged(self):
        self.raw['context']['assessments'][0]['decision'] = 'consider'
        other = copy.deepcopy(self.raw['patterns']['hypotheses'][0]); other['pattern_id'] = 'unselected'
        other['operator_hypothesis'] = 'Unselected hypothesis remains context.'
        self.raw['patterns']['hypotheses'].append(other)
        r = self.report()
        self.assertEqual(len(r['reasoning_context']['pattern_review']['hypotheses']), 2)
        self.assertIn(other['operator_hypothesis'], ap.render_context(r))
        self.assertEqual(r['reasoning_context']['context_review']['assessments'][0]['decision'], 'consider')

    def test_bindings_operator_and_reference_order(self):
        self.s['evidence_refs'] = [self.c.a, self.c.b]
        first = self.report()
        self.assertEqual(first['bindings'], dict(package_sha256=payload_sha256(self.p), scope_sha256=payload_sha256(self.s)))
        self.assertEqual(first['scope_schema'], ap.SCHEMAS[3]['scope'])
        self.assertEqual(first['operator_identity'], 'DECLARED_NOT_AUTHENTICATED')
        self.s['operator_id'] = 'other'; second = self.report()
        self.assertNotEqual(first['bindings']['scope_sha256'], second['bindings']['scope_sha256'])
        self.assertEqual(first['reasoning_context'], second['reasoning_context'])
        self.s['evidence_refs'].reverse(); third = self.report()
        self.assertNotEqual(second['bindings']['scope_sha256'], third['bindings']['scope_sha256'])
        self.assertEqual([r['evidence']['reference'] for r in third['exact_selected_evidence']], self.s['evidence_refs'])

    def test_rejected_history_changes_bindings_without_becoming_citable(self):
        c = imported_fixture.PatternEvidenceReasonTests(); c.setUp()
        extra = copy.deepcopy(c.proposal); extra['proposed_hypothesis'] = 'Rejected synthetic alternative.'
        c.response['candidates'].append(extra); c.reimport(); c.accept()
        c.review['decisions'][1].update(decision='reject', review_note='Rejected interpretation.')
        self.raw['patterns'] = pp.export_reviewed(c.package, c.bundle, c.review)
        first = self.report()
        self.assertIn('Rejected synthetic alternative.', ap.render_context(first))
        self.assertEqual(first['evidence_refs'], [])
        self.raw['patterns']['review']['decisions'][1]['review_note'] = 'Changed rejected history.'
        second = self.report()
        self.assertNotEqual(first['bindings']['scope_sha256'], second['bindings']['scope_sha256'])
        self.assertNotEqual(first['reasoning_context']['report_input_sha256'], second['reasoning_context']['report_input_sha256'])

    def test_v1_v2_unknown_versions_rejected_without_upgrade(self):
        for version in (1, 2, 4):
            s = copy.deepcopy(self.s); s['schema'] = 'persona.answer-proposal-scope.v'+str(version)
            s.pop('research_context'); s['evidence_refs'] = [self.c.a]
            with self.subTest(version=version), self.assertRaises(ValueError): ap.inspect_context(self.p, s)

    def test_scope_missing_extra_and_stale_fields_reject(self):
        for key in self.s:
            s = copy.deepcopy(self.s); del s[key]
            with self.subTest(key=key), self.assertRaises(ValueError): ap.inspect_context(self.p, s)
        for s in (dict(self.s, extra=True), dict(self.s, package_sha256='0'*64)):
            with self.assertRaises(ValueError): ap.inspect_context(self.p, s)
        p = copy.deepcopy(self.p); p['persona']['version'] = 'changed'
        with self.assertRaises(ValueError): ap.inspect_context(p, self.s)

    def test_raw_forms_are_freshly_validated(self):
        for key in self.raw:
            s = copy.deepcopy(self.s); s['research_context'][key] = None
            with self.subTest(key=key), self.assertRaises(ValueError): ap.inspect_context(self.p, s)
        inner = self.report()['reasoning_context']
        for key, cached in [('patterns', 'pattern_review'), ('context', 'context_review'), ('publication_relations', 'publication_context_review')]:
            s = copy.deepcopy(self.s); s['research_context'][key] = inner[cached]
            with self.subTest(key=key), self.assertRaises(ValueError): ap.inspect_context(self.p, s)
        for field in ('patterns', 'context', 'publication_relations'):
            s = copy.deepcopy(self.s); s['research_context'][field]['persona_sha256'] = '0'*64
            with self.subTest(field=field), self.assertRaises(ValueError): ap.inspect_context(self.p, s)

    def test_question_topic_year_operator_types_and_exact_alignment(self):
        for key, values in [('question', [None, '', True, 'different']), ('topic', [None, '', True, 'different']),
                            ('reference_year', [True, 2020.0, 0, 10000, 2021]), ('operator_id', [None, '', True, 'x'*129])]:
            for value in values:
                s = dict(self.s); s[key] = value
                with self.subTest(key=key, value=value), self.assertRaises(ValueError): ap.inspect_context(self.p, s)

    def test_references_unique_typed_and_bounded(self):
        for refs in (None, {}, (self.c.a,), [self.c.a]*2, [self.c.a]*65,
                     [dict(self.c.a, extra=True)], [dict(self.c.a, observation_index=True)],
                     [dict(self.c.a, paper_id='missing')], [dict(self.c.a, dimension='missing')]):
            s = dict(self.s, evidence_refs=refs)
            with self.subTest(refs=refs), self.assertRaises(ValueError): ap.inspect_context(self.p, s)

    def test_strict_json_before_normalization(self):
        for value in (float('nan'), float('inf'), ('tuple',), {1:'key'}, object()):
            s = copy.deepcopy(self.s); s['research_context']['extra'] = value
            with self.subTest(value=value), self.assertRaises(ValueError): ap.inspect_context(self.p, s)
        s = copy.deepcopy(self.s); s['research_context']['extra'] = []
        node = s['research_context']['extra']
        for _ in range(130): node.append([]); node = node[0]
        with self.assertRaises(ValueError): ap.inspect_context(self.p, s)

    def test_preview_ignores_handoff_size_and_does_not_prepare(self):
        self.s['evidence_refs'] = [self.c.a]
        with patch.object(ap, 'MAX_HANDOFF_BYTES', 1):
            with self.assertRaisesRegex(ValueError, '2 MiB'): ap.prepare_handoff(self.p, self.s)
            with patch.object(ap, 'prepare_handoff', side_effect=AssertionError('handoff forbidden')):
                self.report()

    def test_api_and_render_caps_include_full_representation(self):
        with patch.object(ap, 'MAX_INPUT_BYTES', 1):
            with self.assertRaisesRegex(ValueError, '8 MiB'): self.report()
        r = self.report(); size = len((json.dumps(r, ensure_ascii=True, indent=2)+'\n').encode())
        with patch.object(ap, 'MAX_OUTPUT_BYTES', size): self.assertEqual(self.report(), r)
        with patch.object(ap, 'MAX_OUTPUT_BYTES', size-1):
            with self.assertRaisesRegex(ValueError, '16 MiB'): self.report()
        text = ap.render_context(r)
        with patch.object(ap, 'MAX_OUTPUT_BYTES', len(text.encode())-1):
            with self.assertRaisesRegex(ValueError, '16 MiB'): ap.render_context(r)

    def test_detached_results_input_immutability_and_no_source_access(self):
        self.s['evidence_refs'] = [self.c.a, self.c.b]
        before = copy.deepcopy([self.p, self.s])
        with patch('builtins.open', side_effect=AssertionError('source access forbidden')), \
             patch('pathlib.Path.open', side_effect=AssertionError('source access forbidden')), \
             patch('socket.socket', side_effect=AssertionError('network forbidden')):
            r = self.report(); ap.render_context(r)
        self.assertEqual([self.p, self.s], before)
        r['evidence_refs'][0]['paper_id'] = 'mutated'
        r['exact_selected_evidence'][0]['evidence']['observation']['method'] = 'mutated'
        r['reasoning_context']['evidence_refs'].clear()
        self.assertEqual([self.p, self.s], before)

    def test_execution_boundaries_and_no_decision_or_handoff(self):
        r = self.report()
        self.assertFalse(r['llm_used'])
        self.assertEqual(r['execution_scope'], 'CURRENT_INSPECTION_ONLY')
        for k, value in r['processing'].items():
            if k != 'scope': self.assertIs(value, False)
        for phrase in ('quotation rights', 'source verification', 'semantic approval', 'researcher belief', 'authorization to transmit'):
            self.assertIn(phrase, r['boundary'])
        self.assertNotIn('response_contract', r); self.assertNotIn('decision', r)

    def test_text_escapes_untrusted_controls(self):
        self.s['operator_id'] = 'op\nFORGED\x1b\u202e'
        self.raw['patterns']['hypotheses'][0]['scope_note'] = 'Scope\nFORGED\x1b\u202e'
        text = ap.render_context(self.report())
        self.assertNotIn('\nFORGED', text); self.assertNotIn('\x1b', text); self.assertNotIn('\u202e', text)
        self.assertIn('\\u000aFORGED\\u001b\\u202e', text)

    def cli(self, p, s, *flags):
        return subprocess.run([sys.executable, str(ROOT/'answer_proposals.py'), 'context', str(p), str(s), *flags], capture_output=True)

    def test_cli_json_text_api_parity_for_empty_and_selected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'package.json'; s = Path(d)/'scope.json'; p.write_text(json.dumps(self.p))
            for refs in ([], [self.c.a, self.c.b]):
                self.s['evidence_refs'] = refs; s.write_text(json.dumps(self.s)); r = self.report()
                out = self.cli(p, s); self.assertEqual(out.returncode, 0, out.stderr)
                self.assertEqual(json.loads(out.stdout), r)
                out = self.cli(p, s, '--format', 'text'); self.assertEqual(out.returncode, 0, out.stderr)
                self.assertEqual(out.stdout.decode(), ap.render_context(r))

    def test_cli_invalid_duplicate_and_large_inputs_have_no_partial_stdout(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'package.json'; s = Path(d)/'scope.json'; p.write_text(json.dumps(self.p))
            for raw in ('{"schema":1,"schema":2}', json.dumps(dict(self.s, package_sha256='0'*64)), ' '*(ap.MAX_INPUT_BYTES+1)):
                s.write_text(raw)
                out = self.cli(p, s); self.assertNotEqual(out.returncode, 0); self.assertEqual(out.stdout, b'')

    def test_cli_output_cap_has_no_partial_stdout(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'package.json'; s = Path(d)/'scope.json'
            p.write_text(json.dumps(self.p)); s.write_text(json.dumps(self.s))
            for fmt in ('json', 'text'):
                code = 'import answer_proposals as a; a.MAX_OUTPUT_BYTES=1; a.main()'
                out = subprocess.run([sys.executable, '-c', code, 'context', str(p), str(s), '--format', fmt], cwd=ROOT, capture_output=True)
                self.assertNotEqual(out.returncode, 0); self.assertEqual(out.stdout, b'')


class FrozenContextualReplayTests(unittest.TestCase):
    def test_frozen_v059_v3_hashes_and_text_remain_exact(self):
        f = json.loads((ROOT/'examples/legacy-contextual-answer-v059.json').read_text())
        self.assertEqual(f['captured_from_commit'], 'b859ab3116bf7e5fb0860610e2e85a547d4a2890')
        self.assertTrue(f['synthetic_only']); p = f['package']; s = f['scope']
        handoff = ap.prepare_handoff(p, s)
        bundle = ap.import_response(p, s, handoff, f['response'], f['provenance'])
        packet = ap.review_proposals(p, bundle, f['adoption'])
        envelope = ap.export_reviewed(p, bundle, f['adoption'])
        inspection = ad.inspect(p, envelope)
        values = dict(handoff=handoff, bundle=bundle, packet=packet, envelope=envelope, inspection=inspection)
        self.assertEqual({k:payload_sha256(v) for k,v in values.items()}, f['expected_sha256'])
        self.assertEqual(hashlib.sha256(ad.render(inspection).encode()).hexdigest(), f['text_sha256'])
        self.assertEqual(ap.inspect_context(p, s)['reasoning_context'], handoff['reasoning_context'])


if __name__ == '__main__': unittest.main()
