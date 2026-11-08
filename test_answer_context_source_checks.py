"""Explicit preview source reads using synthetic local files only."""
import copy
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import answer_proposals as ap
import source_recheck as sr
import test_answer_context_preview as fixture
import test_pattern_evidence_reasons as imported_fixture
import pattern_proposals as pp
from persona import payload_sha256
from research_workflow import build

ROOT = Path(__file__).resolve().parent
# Captured before v0.61 edits, at c2880f2b2c691dff75c1d0769e264ff40618f2e3.
# Source: /workspace/shared/persona-v061-default-preview-baseline.json.
FROZEN_DEFAULT = {
    'selected': ('2f8e3da45656528a93849484130303472548ebc9f9ba9586465157834261d84d',
                 'dcaaa305de862cf7520ec1ec6ea64b2a2771783d87d3751edfba2fdbee108710'),
    'empty': ('a44b1b65a404d56d2ee386dce2437c982b3f0d46fdd4ac48a2252a73238e3f08',
              'd3a14a6bf1f7df9354255adabac79908aea9e3603504531f0988d4510222f487')}


class ContextSourceChecksTests(unittest.TestCase):
    def setUp(self):
        self.f = fixture.AnswerContextPreviewTests(); self.f.setUp()
        self.p, self.s, self.c = self.f.p, self.f.s, self.f.c
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)/'sources'
        shutil.copytree(ROOT/'examples/synthetic-sources', self.root)
        self.selection = self.form()

    def form(self):
        selection = sr.template(self.p, 'synthetic-source-operator')
        for row in selection['sources']: row['source_file'] = row['paper_id']+'.md'
        return selection

    def report(self):
        return ap.inspect_context(self.p, self.s, source_selection=self.selection, source_root=self.root)

    def rebuild(self, mutate):
        corpus = {key:self.p['persona'][key] for key in ('author_id', 'version', 'build_id')}
        corpus['papers'] = copy.deepcopy(self.p['knowledge']['papers']); mutate(corpus['papers'])
        self.p = build(corpus)
        for form in self.s['research_context'].values():
            if isinstance(form, dict):
                form['persona_sha256'] = payload_sha256(self.p['persona'])
                form['knowledge_papers_sha256'] = payload_sha256(self.p['knowledge']['papers'])
        self.s['package_sha256'] = payload_sha256(self.p)
        self.selection = self.form()

    def test_frozen_default_json_and_text_hashes(self):
        path = ROOT/'examples/legacy-contextual-answer-v059.json'
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),
            '61eb243f8cf6485c4ab80d537c2ec38dfd767f700aec2badde439fd62d9a01ef')
        f = json.loads(path.read_text())
        for mode in ('selected', 'empty'):
            scope = copy.deepcopy(f['scope'])
            if mode == 'empty': scope['evidence_refs'] = []
            r = ap.inspect_context(f['package'], scope)
            self.assertEqual((payload_sha256(r),
                hashlib.sha256(ap.render_context(r).encode()).hexdigest()), FROZEN_DEFAULT[mode])

    def test_all_papers_empty_and_nonempty_citations_no_approval(self):
        for refs in ([], [self.c.a], [self.c.a, self.c.b, self.c.review]):
            self.s['evidence_refs'] = refs
            r = self.report()
            self.assertEqual(r['source_recheck'], sr.audit(self.p, self.selection, self.root))
            self.assertEqual(r['source_recheck']['checked_paper_count'], 2)
            self.assertEqual(r['source_recheck_scope'], 'ALL_SUPPLIED_PAPERS_INCLUDING_UNUSED_EVIDENCE')
            self.assertTrue(r['processing']['source_reread'])
            for k, v in r['processing'].items():
                if k not in ('scope', 'source_reread'): self.assertIs(v, False)
            self.assertFalse(r['llm_used'])
            if not refs:
                with self.assertRaisesRegex(ValueError, '1 to 64'): ap.prepare_handoff(self.p, self.s)

    def test_exact_association_outside_pattern_and_historical_labels_unchanged(self):
        self.s['research_context']['patterns']['hypotheses'][0]['challenge_refs'] = []
        self.s['evidence_refs'] = [self.c.review, self.c.b, self.c.a]
        before = copy.deepcopy([self.p, self.s, self.selection])
        base = ap.inspect_context(self.p, self.s); r = self.report()
        self.assertEqual(json.dumps(base['reasoning_context']), json.dumps(r['reasoning_context']))
        records = {payload_sha256(record['reference']):record for paper in r['source_recheck']['papers'] for record in paper['records']}
        for original, row in zip(base['exact_selected_evidence'], r['exact_selected_evidence']):
            current = row.pop('current_source_recheck')
            self.assertEqual(current, records[payload_sha256(row['evidence']['reference'])])
            self.assertEqual(original, row)
        self.assertEqual(before, [self.p, self.s, self.selection])
        self.assertNotIn(str(self.root), json.dumps(r))
        self.assertEqual(r['bindings']['source_selection_sha256'], payload_sha256(self.selection))
        self.assertNotIn('no current source verification', r['boundary'])
        self.assertNotIn('external transmission, source reread,', r['boundary'])
        self.assertIn('unchanged historical inspection context', r['boundary'])
        self.assertIn('Unchanged historical research context', ap.render_context(r))

    def test_one_read_per_paper_and_render_has_no_reads(self):
        with patch.object(sr, 'read_source_bytes', wraps=sr.read_source_bytes) as read:
            r = self.report(); self.assertEqual(read.call_count, 2)
            ap.render_context(r); self.assertEqual(read.call_count, 2)
        with patch.object(sr, 'audit', side_effect=AssertionError('audit forbidden')):
            ap.render_context(r)
            ap.inspect_context(self.p, self.s)

    def test_pair_required_api(self):
        for kwargs in ({'source_selection':self.selection}, {'source_root':self.root}):
            with patch.object(sr, 'read_source_bytes', side_effect=AssertionError('read forbidden')):
                with self.assertRaisesRegex(ValueError, 'together'): ap.inspect_context(self.p, self.s, **kwargs)

    def test_invalid_late_raw_context_and_unselected_history_precede_reads(self):
        for key in ('context', 'publication_relations'):
            s = copy.deepcopy(self.s); s['research_context'][key]['extra'] = True
            with patch.object(sr, 'read_source_bytes', side_effect=AssertionError('read forbidden')):
                with self.assertRaises(ValueError): ap.inspect_context(self.p, s, source_selection=self.selection, source_root=self.root)
        other = copy.deepcopy(self.s['research_context']['patterns']['hypotheses'][0])
        other.update(pattern_id='unselected', support_refs=[dict(self.c.a, observation_index=999)])
        self.s['research_context']['patterns']['hypotheses'].append(other)
        with patch.object(sr, 'read_source_bytes', side_effect=AssertionError('read forbidden')):
            with self.assertRaises(ValueError): self.report()

    def test_invalid_rejected_import_history_precedes_reads(self):
        c = imported_fixture.PatternEvidenceReasonTests(); c.setUp()
        extra = copy.deepcopy(c.proposal); extra['proposed_hypothesis'] = 'Rejected synthetic alternative.'
        c.response['candidates'].append(extra); c.reimport(); c.accept()
        c.review['decisions'][1].update(decision='reject', review_note='Rejected interpretation.')
        raw = self.s['research_context']; raw['patterns'] = pp.export_reviewed(c.package, c.bundle, c.review)
        self.report()
        raw['patterns']['bundle']['candidates'][-1]['proposed_pattern']['support_refs'] = [dict(self.c.a, observation_index=999)]
        with patch.object(sr, 'read_source_bytes', side_effect=AssertionError('read forbidden')):
            with self.assertRaises(ValueError): self.report()

    def test_strict_selection_and_combined_budget_before_normalization(self):
        for value in (('tuple',), {1:'key'}, float('nan'), float('inf'), object()):
            selection = dict(self.selection, extra=value)
            with patch.object(sr, 'audit', side_effect=AssertionError('audit forbidden')):
                with self.assertRaises(ValueError): ap.inspect_context(self.p, self.s, source_selection=selection, source_root=self.root)
        size = len(json.dumps([self.p, self.s, self.selection], ensure_ascii=True).encode())
        with patch.object(ap, 'MAX_INPUT_BYTES', size-1), patch.object(sr, 'audit', side_effect=AssertionError('audit forbidden')):
            with self.assertRaisesRegex(ValueError, '8 MiB'): self.report()

    def test_invalid_selection_and_later_paths_precede_reads(self):
        for change in (lambda s:s['sources'].pop(), lambda s:s.update(package_sha256='0'*64),
            lambda s:s['sources'][-1].update(source_file='../escape.md'),
            lambda s:s['sources'][-1].update(source_file='./synthetic-1.md'),
            lambda s:s['sources'][-1].update(source_file='missing.md'),
            lambda s:s['sources'][-1].update(source_file='file.pdf')):
            selection = copy.deepcopy(self.selection); change(selection)
            with patch.object(sr, 'read_source_bytes', side_effect=AssertionError('read forbidden')):
                with self.assertRaises((ValueError, OSError)):
                    ap.inspect_context(self.p, self.s, source_selection=selection, source_root=self.root)

    def test_symlink_escape_root_and_authorization_fail_closed(self):
        outside = Path(self.tmp.name)/'outside.md'; outside.write_text('Synthetic only.')
        link = self.root/'link.md'; link.symlink_to(outside)
        self.selection['sources'][-1]['source_file'] = 'link.md'
        with patch.object(sr, 'read_source_bytes', side_effect=AssertionError('read forbidden')):
            with self.assertRaises(ValueError): self.report()
            self.selection = self.form()
            with self.assertRaises(OSError): ap.inspect_context(self.p, self.s, source_selection=self.selection, source_root=self.root/'absent')
            self.p['knowledge']['papers'][-1]['authorized'] = False
            with self.assertRaises(ValueError): self.report()

    def test_base_and_final_representation_caps(self):
        base = ap.inspect_context(self.p, self.s)
        size = len((json.dumps(base, ensure_ascii=True, indent=2)+'\n').encode())
        with patch.object(ap, 'MAX_OUTPUT_BYTES', size-1), patch.object(sr, 'audit', side_effect=AssertionError('audit forbidden')):
            with self.assertRaisesRegex(ValueError, '16 MiB'): self.report()
        r = self.report(); final = len((json.dumps(r, ensure_ascii=True, indent=2)+'\n').encode())
        with patch.object(ap, 'MAX_OUTPUT_BYTES', final): self.assertEqual(self.report(), r)
        with patch.object(ap, 'MAX_OUTPUT_BYTES', final-1):
            with self.assertRaisesRegex(ValueError, '16 MiB'): self.report()
        with patch.object(ap, 'MAX_OUTPUT_BYTES', len(ap.render_context(r).encode())-1):
            with self.assertRaisesRegex(ValueError, '16 MiB'): ap.render_context(r)
        with patch.object(ap, 'MAX_HANDOFF_BYTES', 1): self.report()

    def test_cumulative_source_and_audit_caps(self):
        total = sum((self.root/x['source_file']).stat().st_size for x in self.selection['sources'])
        with patch.object(sr, 'MAX_SOURCE_BYTES', total): self.assertEqual(self.report()['source_recheck']['source_bytes_read'], total)
        with patch.object(sr, 'MAX_SOURCE_BYTES', total-1):
            with self.assertRaisesRegex(ValueError, 'input limit'): self.report()
        with patch.object(sr, 'MAX_JSON_BYTES', 1):
            with self.assertRaisesRegex(ValueError, '8 MiB'): self.report()

    def test_complete_quote_and_locator_gaps_without_fallback(self):
        def mutate(papers):
            papers[0]['observations'][0].update(evidence_quote=None, locator='missing locator')
            papers[1]['observations'][0]['reasoning']['alternative_explanation']['evidence_quote'] = 'Missing synthetic quote'
        self.rebuild(mutate)
        r = self.report(); audit = r['source_recheck']
        self.assertEqual(audit['checked_record_count'], 3)
        self.assertEqual(len(audit['quote_gaps']), 2)
        self.assertEqual(audit['papers'][0]['records'][0]['locator_status'], 'NOT_FOUND')
        self.assertEqual(audit['papers'][0]['records'][0]['quote_status'], 'STORED_QUOTE_MISSING')
        self.assertIn('STORED_QUOTE_NOT_FOUND_AT_LOCATOR', ap.render_context(r))
        self.assertTrue(r['processing']['source_reread'])

    def test_hash_and_utf8_failures(self):
        path = self.root/'synthetic-1.md'; path.write_bytes(b'Changed synthetic bytes')
        with self.assertRaisesRegex(ValueError, 'bound package hash'): self.report()
        path.write_bytes(b'\xff')
        self.rebuild(lambda papers:papers[1].update(source_sha256=hashlib.sha256(b'\xff').hexdigest()))
        with self.assertRaises(UnicodeError): self.report()

    def cli(self, *flags, code=None, command='context'):
        p = Path(self.tmp.name)/'package.json'; s = Path(self.tmp.name)/'scope.json'; selection = Path(self.tmp.name)/'selection.json'
        p.write_text(json.dumps(self.p)); s.write_text(json.dumps(self.s))
        if not selection.exists(): selection.write_text(json.dumps(self.selection))
        head = [sys.executable, '-c', code] if code else [sys.executable, str(ROOT/'answer_proposals.py')]
        return subprocess.run(head+[command, str(p), str(s), *flags], cwd=ROOT, capture_output=True)

    def flags(self):
        return ['--source-selection', str(Path(self.tmp.name)/'selection.json'), '--source-root', str(self.root)]

    def test_actual_cli_json_text_parity_empty_and_nonempty(self):
        for refs in ([], [self.c.a, self.c.review, self.c.b]):
            self.s['evidence_refs'] = refs; r = self.report()
            out = self.cli(*self.flags()); self.assertEqual(out.returncode, 0, out.stderr)
            self.assertEqual(json.loads(out.stdout), r)
            out = self.cli(*self.flags(), '--format', 'text'); self.assertEqual(out.returncode, 0, out.stderr)
            self.assertEqual(out.stdout.decode(), ap.render_context(r))

    def test_cli_pairs_context_only_and_strict_json_fail_without_stdout(self):
        for flags in (['--source-root', str(self.root)], ['--source-selection', self.flags()[1]]):
            out = self.cli(*flags); self.assertNotEqual(out.returncode, 0); self.assertEqual(out.stdout, b'')
        out = self.cli(*self.flags(), command='prepare'); self.assertNotEqual(out.returncode, 0); self.assertEqual(out.stdout, b'')
        for raw in ('{"schema":1,"schema":2}', '{"value":NaN}', ' '*(ap.MAX_INPUT_BYTES+1)):
            (Path(self.tmp.name)/'selection.json').write_text(raw)
            out = self.cli(*self.flags()); self.assertNotEqual(out.returncode, 0); self.assertEqual(out.stdout, b'')

    def test_cli_hash_utf8_and_final_output_fail_without_stdout(self):
        r = self.report(); size = len((json.dumps(r, ensure_ascii=True, indent=2)+'\n').encode())
        for fmt in ('json', 'text'):
            out = self.cli(*self.flags(), '--format', fmt, code=f'import answer_proposals as a; a.MAX_OUTPUT_BYTES={size-1}; a.main()')
            self.assertNotEqual(out.returncode, 0); self.assertEqual(out.stdout, b'')
        (self.root/'synthetic-1.md').write_bytes(b'changed')
        out = self.cli(*self.flags()); self.assertNotEqual(out.returncode, 0); self.assertEqual(out.stdout, b'')
        (self.root/'synthetic-1.md').write_bytes(b'\xff')
        self.rebuild(lambda papers:papers[1].update(source_sha256=hashlib.sha256(b'\xff').hexdigest()))
        (Path(self.tmp.name)/'selection.json').write_text(json.dumps(self.selection))
        out = self.cli(*self.flags()); self.assertNotEqual(out.returncode, 0); self.assertEqual(out.stdout, b'')


if __name__ == '__main__': unittest.main()
