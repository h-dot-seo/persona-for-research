"""Single-step navigation: synthetic fixtures, complete raw replay, no external I/O."""
import copy
import hashlib
import json
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import answer_draft as ad
import argument_map as am
import argument_proposals as gp
from extraction_adapter import MockProvider
from persona import payload_sha256
from review_package import display
import tests.test_argument_map as manual_fixture
from tests.test_argument_replay_reuse import cases


class ManualStepViewTests(unittest.TestCase):
    def setUp(self):
        f = manual_fixture.ArgumentMapTests(); f.setUp()
        self.p, self.d, self.m = f.package, f.draft, f.map

    def view(self, step='combine', review=None):
        return am.inspect_step(self.p, self.d, self.m, step, review)

    def rebind(self, review=None):
        self.m = dict(am.template(self.p, self.d, 'synthetic-map-operator', review), steps=self.m['steps'])

    def test_exact_step_claim_citations_and_review_records(self):
        self.d['claims'][1]['citations'][0]['explanation'] = dict(rationale='Exact reason.', context_boundary='Local scope.')
        review = ad.review_template(self.p, self.d, 'reviewer')
        review['decisions'][0].update(decision='reject', note='Exact rejected endpoint note.')
        self.rebind(review)
        full = am.inspect(self.p, self.d, self.m, review); v = self.view(review=review)
        self.assertEqual(v['selected_step'], full['steps'][0])
        self.assertEqual(v['endpoint_claims'], full['answer']['claims'])
        self.assertEqual(v['endpoint_answer_reviews'][0]['decision'], review['decisions'][0])
        self.assertEqual(v['endpoint_answer_reviews'][1]['decision']['decision'], 'defer')
        self.assertEqual(v['endpoint_claims'][-1]['evidence_status'], 'NO_CITATIONS_SUPPLIED')
        self.assertEqual(v['endpoint_claims'][-1]['citations'], [])
        self.assertEqual([c['role'] for c in v['endpoint_claims'][1]['citations']], ['support', 'challenge'])
        self.assertEqual(v['full_report_reference']['full_report_sha256'], payload_sha256(full))

    def test_declared_topology_premise_order_and_same_conclusion_paths(self):
        first = dict(step_id='first', premise_claim_ids=['q1'], conclusion_claim_id='s1',
                     bridge_rationale='Earlier bridge.', assumptions=[], defeater=None)
        self.m['steps'][0]['premise_claim_ids'] = ['s1', 'q1']
        self.m['steps'].extend([first, dict(copy.deepcopy(self.m['steps'][0]), step_id='alternative')])
        v = self.view()
        self.assertEqual(v['declared_step_ids'], ['combine', 'first', 'alternative'])
        self.assertEqual(v['review_order_step_ids'], ['first', 'combine', 'alternative'])
        self.assertEqual(v['endpoint_claim_ids'], ['s1', 'q1', 'conclusion'])
        self.assertEqual(v['same_conclusion_alternative_step_ids'], ['alternative'])
        self.assertEqual(v['omitted_scope']['other_step_ids'], ['first', 'alternative'])
        self.assertEqual(v['omitted_scope']['other_step_count'], 2)
        self.m['steps'][0]['premise_claim_ids'] = ['s1']
        v = self.view()
        self.assertEqual(v['omitted_scope']['nonendpoint_claim_ids'], ['q1'])
        self.assertEqual(v['omitted_scope']['nonendpoint_claim_count'], 1)
        self.assertNotIn('q1', v['endpoint_claim_ids'])

    def test_complete_validation_precedes_selection_and_no_report_input(self):
        self.m['steps'].append(dict(copy.deepcopy(self.m['steps'][0]), step_id='other', premise_claim_ids=['absent']))
        for key in ('combine', '', 'unknown'):
            with self.assertRaisesRegex(ValueError, 'unknown, duplicate'):
                self.view(key)
        self.m['steps'].pop()
        for key in ('', 'unknown', ' combine', 'COMBINE', None):
            with self.assertRaises(ValueError): self.view(key)
        report = am.inspect(self.p, self.d, self.m)
        with self.assertRaises(ValueError): am.inspect_step(self.p, report, self.m, 'combine')
        self.m['steps'] = []
        with self.assertRaises(ValueError): self.view()

    def test_full_raw_wrapper_identity_and_review_none(self):
        original = self.view()['full_report_reference']
        self.p = dict(package=self.p, wrapper_note='First wrapper.')
        wrapped = self.view()['full_report_reference']
        self.assertNotEqual(original['raw_package_sha256'], wrapped['raw_package_sha256'])
        self.assertEqual(original['full_report_sha256'], wrapped['full_report_sha256'])
        self.p['wrapper_note'] = 'Changed wrapper.'
        self.assertNotEqual(wrapped, self.view()['full_report_reference'])
        self.assertEqual(original['raw_declared_review_sha256'], payload_sha256(None))
        self.assertFalse(original['declared_review_supplied'])
        review = ad.review_template(self.p, self.d, 'reviewer'); self.rebind(review)
        reviewed = self.view(review=review)['full_report_reference']
        self.assertTrue(reviewed['declared_review_supplied'])
        self.assertEqual(reviewed['raw_declared_review_sha256'], payload_sha256(review))

    def test_fresh_calls_isolation_and_no_io(self):
        before = copy.deepcopy((self.p, self.d, self.m))
        with patch.object(MockProvider, 'extract', side_effect=AssertionError('provider')), \
             patch.object(Path, 'read_text', side_effect=AssertionError('source read')), \
             patch.object(Path, 'read_bytes', side_effect=AssertionError('source read')), \
             patch.object(socket, 'socket', side_effect=AssertionError('network')), \
             patch.object(am, 'inspect', wraps=am.inspect) as fresh:
            v = self.view(); am.render_step(self.p, self.d, self.m, 'combine')
            self.assertEqual(fresh.call_count, 2)
        v['endpoint_claims'][0]['citations'][0]['evidence']['observation']['method'] = 'mutated'
        v['selected_step']['premise_claim_ids'].clear()
        self.assertEqual(before, (self.p, self.d, self.m))
        self.assertNotEqual(v, self.view())
        self.d['claims'][1]['uncertainty'] = 'Changed after previous call.'
        with self.assertRaises(ValueError): self.view()

    def test_historical_scope_omission_and_escaped_complete_text(self):
        injected = '한글 café\n\x1b[31m\u202e\u2028$(not-a-command)'
        self.m['steps'][0]['bridge_rationale'] = injected
        self.m['steps'][0]['step_id'] = injected
        v = self.view(injected); text = am.render_step(self.p, self.d, self.m, injected)
        self.assertIn(display(injected), text)
        for control in ('\x1b', '\u202e', '\u2028'): self.assertNotIn(control, text)
        self.assertIn('Full history is NOT embedded', text)
        self.assertIn('no companion file was created', text)
        self.assertIn('without --step-id', text)
        for field in ('current_journey_context', 'method_use', 'source_recheck'):
            self.assertEqual(v[field], 'NOT_EVALUATED_HERE')
        self.assertFalse(v['full_report_reference']['companion_file_created'])
        self.assertFalse(v['omitted_scope']['complete_answer_report_embedded'])
        self.assertEqual(v['citation_transfer'], 'NOT_PERFORMED')

    def test_no_invented_context_and_complete_container_inventory(self):
        self.assertEqual(self.view()['recorded_answer_preparation_context'], 'NOT_SUPPLIED')
        report = dict(answer=dict(proposal_review=dict(candidates=[], research_context_review=dict(status='historical')),
                                 scalar_array=['scalar'] * 10000 + [dict(review=dict(note='retained'))]))
        inventory = am._history_inventory(report)
        self.assertEqual([row['report_path'] for row in inventory],
            [['answer', 'proposal_review'], ['answer', 'proposal_review', 'research_context_review']])
        self.assertTrue(all(not row['full_content_embedded'] for row in inventory))

    def test_legacy_extra_metadata_is_not_report_history(self):
        paper = next(p for p in self.p['knowledge']['papers'] if p['paper_id'] == 'synthetic-1')
        component = paper['observations'][0]['reasoning']['falsification_check']
        component['review'] = dict(candidates=['legacy metadata, not report history'])
        component['research_context_review'] = dict(candidates=[])
        self.p['persona']['knowledge_papers_sha256'] = payload_sha256(self.p['knowledge']['papers'])
        self.p['knowledge']['persona_payload_sha256'] = payload_sha256(self.p['persona'])
        self.d = dict(ad.template(self.p, self.d['question'], self.d['operator_id']), claims=self.d['claims'])
        self.rebind()
        full = am.inspect(self.p, self.d, self.m)
        v = self.view()
        self.assertEqual(v['endpoint_claims'], full['answer']['claims'])
        self.assertEqual(v['full_report_reference']['raw_package_sha256'], payload_sha256(self.p))
        # Unknown legacy component extras are stripped by ordinary runtime projection.
        # Even if embedded metadata has history-like names, inventory must ignore it.
        full['answer']['claims'][0]['citations'][0]['evidence']['component'].update(copy.deepcopy(component))
        self.assertEqual(am._history_inventory(full), [])
        self.assertEqual(v['omitted_scope']['complete_candidate_review_context_histories'], [])
        self.assertEqual(v['recorded_answer_preparation_context'], 'NOT_SUPPLIED')

    def test_no_raw_input_normalization_or_new_legacy_cap(self):
        self.assertEqual(am.MAX_STEP_VIEW_BYTES, 16 * 1024 * 1024)
        bad = copy.deepcopy(self.m)
        bad['steps'] = tuple(bad['steps'])
        with self.assertRaisesRegex(ValueError, 'array'):
            am.inspect_step(self.p, self.d, bad, 'combine')
        wrapped = dict(package=self.p, ignored_legacy_metadata=object())
        am.inspect(wrapped, self.d, self.m)
        with self.assertRaises(TypeError):
            am.inspect_step(wrapped, self.d, self.m, 'combine')

    def test_focus_only_limits_pretty_newline_escaped_text(self):
        full = am.inspect(self.p, self.d, self.m)
        required = len((json.dumps(full, indent=2) + '\n').encode())
        with patch.object(am, 'MAX_STEP_VIEW_BYTES', required - 1):
            with self.assertRaisesRegex(ValueError, 'Complete full JSON'): self.view('absent')
            self.assertEqual(am.inspect(self.p, self.d, self.m), full)
            self.assertTrue(am.render(self.p, self.d, self.m))
        self.assertEqual(am._step_bound('é\n', 'test'), 'é\n')
        with patch.object(am, 'MAX_STEP_VIEW_BYTES', 3):
            self.assertEqual(am._step_bound('é\n', 'test'), 'é\n')
            with self.assertRaises(ValueError): am._step_bound('é\n\n', 'test')
        with patch.object(am, 'MAX_STEP_VIEW_BYTES', 2):
            with self.assertRaises(ValueError): am._step_json({}, 'test')
        # Projected output can itself exceed the full report because of disclosures.
        with patch.object(am, 'MAX_STEP_VIEW_BYTES', required):
            with self.assertRaisesRegex(ValueError, 'Focused'): self.view()
        with patch.object(am, 'MAX_STEP_VIEW_BYTES', 2000):
            with self.assertRaisesRegex(ValueError, 'Focused text'):
                am._render_step_inspected({'operator_text': '\x1b' * 400})

    def test_cli_modes_incompatible_template_and_no_partial_stdout(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = []
            for name, value in [('package', self.p), ('draft', self.d), ('map', self.m)]:
                path = Path(directory)/(name+'.json'); path.write_text(json.dumps(value)); paths.append(str(path))
            cmd = [sys.executable, str(Path(am.__file__)), *paths]
            out = subprocess.run(cmd+['--step-id', 'combine'], capture_output=True, check=True, timeout=30)
            self.assertEqual(json.loads(out.stdout), self.view())
            out = subprocess.run(cmd+['--step-id', 'combine', '--format', 'text'], capture_output=True, check=True, timeout=30)
            self.assertEqual(out.stdout.decode(), am.render_step(self.p, self.d, self.m, 'combine'))
            for options in (['--step-id', 'missing'], ['--template', '--step-id', 'combine']):
                out = subprocess.run(cmd+options, capture_output=True, timeout=30)
                self.assertNotEqual(out.returncode, 0); self.assertEqual(out.stdout, b'')
            bad = Path(directory)/'bad.json'
            key = 'unsafe\n\x1b\u202e'
            bad.write_text('{' + json.dumps(key) + ': 1, ' + json.dumps(key) + ': 2}')
            out = subprocess.run([sys.executable, str(Path(am.__file__)), str(bad), *paths[1:],
                                  '--step-id', 'combine'], capture_output=True, timeout=30)
            self.assertNotEqual(out.returncode, 0); self.assertEqual(out.stdout, b'')
            self.assertIn(json.dumps(key, ensure_ascii=True), out.stderr.decode())
            self.assertEqual(out.stderr.count(b'\n'), 1)
            for control in ('\x1b', '\u202e'): self.assertNotIn(control, out.stderr.decode())
            # Real CLI entrypoint, deliberately tiny focus-only budget, no partial writes.
            script = 'import argument_map as a; a.MAX_STEP_VIEW_BYTES=1; a.main()'
            out = subprocess.run([sys.executable, '-c', script, *paths, '--step-id', 'combine'], capture_output=True, timeout=30)
            self.assertNotEqual(out.returncode, 0); self.assertEqual(out.stdout, b'')


class ImportedStepViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixtures = dict(cases())

    def test_complete_pre_edit_default_json_text_snapshots(self):
        for name, c in self.fixtures.items():
            p, d, r = c['package'], c['draft'], c['declared']
            form = dict(am.template(p, d, 'synthetic-operator', r), steps=[c['step']])
            for kind, supplied in [('manual', form), ('imported', c['envelope'])]:
                outputs = {'json': json.dumps(am.inspect(p, d, supplied, r), indent=2, sort_keys=True)+'\n',
                           'txt': am.render(p, d, supplied, r)}
                for suffix, text in outputs.items():
                    with self.subTest(case=name, kind=kind, suffix=suffix):
                        self.assertEqual(hashlib.sha256(text.encode()).hexdigest(), SNAPSHOTS[name+'-'+kind+'.'+suffix])

    def test_imported_exact_original_adoption_endpoints_and_omitted_histories(self):
        for name in ('plain_reviewed', 'contextual'):
            c = self.fixtures[name]
            v = am.inspect_step(c['package'], c['draft'], c['envelope'], c['step']['step_id'], c['declared'])
            origin = v['selected_step']['proposal_origin']
            self.assertEqual(origin['review_note'], 'Synthetic adoption.')
            self.assertEqual(origin['original_proposal'], c['bundle']['candidates'][0]['proposed_step'])
            self.assertEqual(v['selected_step']['bridge_rationale'], c['step']['bridge_rationale'])
            inventory = v['omitted_scope']['complete_candidate_review_context_histories']
            argument = next(row for row in inventory if row['report_path'] == ['proposal_review'])
            self.assertEqual(argument['candidate_count'], 2)
            self.assertEqual(argument['candidate_ids'], [x['candidate_id'] for x in c['bundle']['candidates']])
            self.assertEqual(v['full_report_reference']['raw_supplied_map_sha256'], payload_sha256(c['envelope']))
            self.assertIn(c['envelope']['schema'], v['full_report_reference']['kind'])
            if name == 'contextual':
                self.assertEqual(v['recorded_answer_preparation_context'], 'HISTORICAL_ONLY_FULL_CONTEXT_OMITTED')
                self.assertTrue(any('recorded_answer_context' in row['report_path'] for row in inventory))
                self.assertTrue(any(row['report_path'] == ['answer', 'proposal_review'] for row in inventory))
                self.assertTrue(v['omitted_scope']['nonendpoint_claim_ids'])
            for candidate in c['bundle']['candidates']:
                with self.assertRaises(ValueError):
                    am.inspect_step(c['package'], c['draft'], c['envelope'], candidate['candidate_id'], c['declared'])

    def test_original_and_revised_bridge_text_and_imported_limits(self):
        c = copy.deepcopy(self.fixtures['plain'])
        c['envelope']['review']['decisions'][0]['reviewed_step']['bridge_rationale'] = 'Distinct reviewed bridge.'
        v = am.inspect_step(c['package'], c['draft'], c['envelope'], c['step']['step_id'])
        self.assertEqual(v['selected_step']['bridge_rationale'], 'Distinct reviewed bridge.')
        self.assertEqual(v['selected_step']['proposal_origin']['original_proposal']['bridge_rationale'],
                         c['step']['bridge_rationale'])
        text = am.render_step(c['package'], c['draft'], c['envelope'], c['step']['step_id'])
        self.assertIn('Distinct reviewed bridge.', text)
        self.assertIn(c['step']['bridge_rationale'], text)
        with patch.object(gp, 'MAX_OUTPUT_BYTES', 1):
            with self.assertRaisesRegex(ValueError, '16 MiB'):
                am.inspect_step(c['package'], c['draft'], c['envelope'], 'absent')

    def test_full_rejected_history_identity_and_stale_binding(self):
        c = copy.deepcopy(self.fixtures['plain'])
        def view(): return am.inspect_step(c['package'], c['draft'], c['envelope'], c['step']['step_id'], c['declared'])
        before = view()
        c['envelope']['review']['decisions'][1]['review_note'] = 'Changed rejected history.'
        after = view()
        self.assertEqual(before['endpoint_claims'], after['endpoint_claims'])
        self.assertNotEqual(before['full_report_reference']['full_report_sha256'], after['full_report_reference']['full_report_sha256'])
        self.assertNotEqual(before['full_report_reference']['raw_supplied_map_sha256'], after['full_report_reference']['raw_supplied_map_sha256'])
        c['envelope']['bundle']['candidates'][1]['proposed_step']['bridge_rationale'] = 'Stale rejected candidate.'
        with self.assertRaises(ValueError): view()
        c = copy.deepcopy(self.fixtures['contextual'])
        c['draft']['review']['decisions'][-1]['review_note'] = 'Changed rejected answer history.'
        with self.assertRaises(ValueError):
            am.inspect_step(c['package'], c['draft'], c['envelope'], c['step']['step_id'], c['declared'])


# Complete default JSON and text captured externally before edits. JSON keys sorted
# for hashing only: legacy contextual reports use process-dependent dictionary key order.
SNAPSHOTS = {'contextual-imported.json': 'ef33c0808c2bdab67fff8dab2bd57a6344d52e296b844507a746eb4be8e9d765',
 'contextual-imported.txt': 'e3d7d699727a36b1138ba8c9f36276cd8d96524617f86f0bfb5c70868c486ce7',
 'contextual-manual.json': '856ab97339b00d3050000b339246a57f52c7458f96e7d1486ba09920de7ecf95',
 'contextual-manual.txt': '9653b977b8c17bde904a40346f441fe4c8eb02db7df014d55147299ca249843f',
 'contextual_reviewed-imported.json': 'd4d7086637689b595c22b76d4b310aa2b6221cf34e7976f59db2924eaf9c7354',
 'contextual_reviewed-imported.txt': 'c32062d160875972a9091967ae3faeaeff928b391920ed112a25bf2947ec02ed',
 'contextual_reviewed-manual.json': 'caed9a20f60b1311f37644c1a4c2f792a01f4ef9385fb33c83e6ecc27459528d',
 'contextual_reviewed-manual.txt': '606abaf1b84897ba077d4cb22cd500c742d1a57848b9e6701edb5bda66ff3b9b',
 'plain-imported.json': 'e388ae70c0ad76740ec94fbff3108c150143a595b47c8ea6061cbee91e7328b9',
 'plain-imported.txt': '04861c3ff6df36d1307d0770801ee396e115e22eb45dd87b4afe5db58a1e0eb0',
 'plain-manual.json': '29170b99e8ba814bb1d369bc3647ce419bea1f1cfb6ed04881bbf7f4b4829e00',
 'plain-manual.txt': '4f4b94063603e0ca7f24038bab4ba85683a81c20a70663b3f3b24f141b92fce2',
 'plain_reviewed-imported.json': '4354ff9173df6c904c85aa289e3254f122bf6e66099811fc1434ac5d6294e846',
 'plain_reviewed-imported.txt': 'e09763fc346782d6d46f31548583f968324e49fba9a7425376a80019e1844fbb',
 'plain_reviewed-manual.json': '364517fc427971faae444faeeedb009fddaefe25c1a9a59650c3e9ee9f74036c',
 'plain_reviewed-manual.txt': '0af65d46d869a8b3e843371ac4c2ef669433f362ad904651abd6727a0cebf5af'}

if __name__ == '__main__': unittest.main()
