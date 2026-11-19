"""Synthetic correction, authoritative import, and source-boundary checks."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import observation_preflight as preflight
from corpus_files import load_segment_corpus
from observation_proposals import prepare_observation_handoff
from persona import payload_sha256
from tests.test_observation_preflight import ROOT, inputs


class BoundObservationPreflightTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix='PRIVATE synthetic ')
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.corpus, self.handoff, self.response, self.provenance = inputs()
        self.paths = [self.save(name, value) for name, value in zip(
            ('corpus', 'handoff', 'response', 'provenance'),
            (self.corpus, self.handoff, self.response, self.provenance))]

    def save(self, name, value):
        path = self.root / (name + '.json')
        path.write_bytes((json.dumps(value, ensure_ascii=True) + '\n').encode('ascii'))
        return path

    def cli(self, command, *options):
        return subprocess.run([sys.executable, str(ROOT / 'model_handoff.py'), command,
                               *map(str, self.paths), *map(str, options)],
                              capture_output=True, timeout=30,
                              env=dict(os.environ, PYTHONIOENCODING='ascii'))

    def test_multiple_bad_rows_and_correction_through_real_import(self):
        row = self.response['candidates'][0]
        rows = [dict(row, paper_id='PRIVATE-id'), row, dict(row, locator='PRIVATE-locator'),
                dict(row, evidence_quote='PRIVATE-quote')]
        self.save('response', dict(self.response, candidates=rows))
        before = {p: p.read_bytes() for p in self.paths}
        result = self.cli('preflight-observations')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, b'')
        report = json.loads(result.stdout)
        self.assertEqual(report['evidence_rows_checked'], 4)
        self.assertEqual(report['status'], 'EVIDENCE_ERRORS')
        self.assertEqual(report['source_basis'], 'SUPPLIED_SEGMENTS')
        self.assertFalse(report['import_performed'])
        self.assertEqual(report['errors'], [
            dict(path=['response', 'candidates', '0', 'paper_id'], code='UNKNOWN_PAPER'),
            dict(path=['response', 'candidates', '2', 'locator'], code='UNKNOWN_LOCATOR'),
            dict(path=['response', 'candidates', '3', 'evidence_quote'], code='QUOTE_MISMATCH')])
        text = self.cli('preflight-observations', '--format', 'text')
        self.assertEqual(text.returncode, 1)
        self.assertIn(b'/response/candidates/3/evidence_quote: QUOTE_MISMATCH', text.stdout)
        for raw in (result.stdout, text.stdout):
            for private in ('PRIVATE', row['evidence_quote'], row['paper_id'],
                            self.response['handoff_sha256']):
                self.assertNotIn(private.encode(), raw)
            self.assertNotIn(b'\r', raw)
        self.assertEqual(before, {p: p.read_bytes() for p in self.paths})
        self.assertEqual(self.cli('import', '--task', 'observations').returncode, 1)
        self.save('response', self.response)
        result = self.cli('preflight-observations')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'], 'CHECKS_PASSED')
        imported = self.cli('import', '--task', 'observations')
        self.assertEqual(imported.returncode, 0, imported.stderr)
        self.assertEqual(len(json.loads(imported.stdout)['candidates']), 1)

    def test_both_structures_before_any_source_or_handoff_read(self):
        self.response['candidates'][0].update(method='', PRIVATE='hidden')
        self.save('response', self.response)
        self.paths[3].write_bytes(b'{"PRIVATE":0,"PRIVATE":1}')
        self.paths[0].unlink()
        self.paths[1].unlink()
        with patch.object(preflight, 'load', wraps=preflight.load) as read, patch.object(
                preflight, 'load_segment_corpus', side_effect=AssertionError):
            report = preflight.inspect_files(*self.paths, source_root=self.root)
        self.assertEqual([call.args[0] for call in read.call_args_list], self.paths[2:])
        self.assertEqual(report['status'], 'STRUCTURE_ERRORS')
        self.assertEqual(report['errors'], [
            dict(path=['response', 'candidates', '0'], code='UNSUPPORTED_FIELDS'),
            dict(path=['response', 'candidates', '0', 'method'], code='PATTERN'),
            dict(path=['provenance'], code='INPUT_UNREADABLE_OR_INVALID')])
        self.assertNotIn('PRIVATE', json.dumps(report))

    def test_binding_failures_suppress_evidence_even_for_modified_handoff_sources(self):
        self.handoff['sources'][0]['segments'].clear()
        self.save('handoff', self.handoff)
        with patch.object(preflight, 'quote_issue', side_effect=AssertionError):
            report = preflight.inspect_files(*self.paths)
            self.assertEqual(report['status'], 'BINDING_ERRORS')
            self.assertEqual(report['errors'], [
                dict(path=['handoff'], code='HANDOFF_NOT_CURRENT'),
                dict(path=['response', 'handoff_sha256'], code='RESPONSE_BINDING_MISMATCH')])
            self.save('response', dict(self.response, handoff_sha256=payload_sha256(self.handoff)))
            report = preflight.inspect_files(*self.paths)
        self.assertEqual(report['errors'], [dict(path=['handoff'], code='HANDOFF_NOT_CURRENT')])
        self.assertEqual(report['evidence_rows_checked'], 0)

    def test_holdout_in_last_paper_blocks_every_local_read(self):
        for field, value in [('split', 'holdout'), ('authorized', False),
                             ('runtime_knowledge_eligible', False), ('author_id', 'PRIVATE')]:
            corpus = json.loads(self.paths[0].read_bytes())
            corpus['papers'][-1][field] = value
            self.save('corpus', corpus)
            for source_root in (None, self.root):
                with self.subTest(field=field, source_root=source_root), patch(
                        'corpus_files.source_paths', side_effect=AssertionError), patch(
                        'observation_input.copy.deepcopy', side_effect=AssertionError), patch.object(
                        preflight, 'quote_issue', side_effect=AssertionError):
                    report = preflight.inspect_files(*self.paths, source_root=source_root)
                self.assertEqual(report['status'], 'CORPUS_REJECTED')
                self.assertEqual(report['source_basis'], 'UNVERIFIED')
                self.assertEqual(report['errors'], [dict(path=['corpus'], code='CORPUS_OR_SOURCE_CHECK_FAILED')])
            self.save('corpus', self.corpus)

    def test_local_pinned_bytes_are_rechecked_and_read_errors_redacted(self):
        manifest = json.loads((ROOT / 'examples/file-corpus.json').read_bytes())
        for paper in manifest['papers']:
            paper['observations'] = []
            name = paper['source_file']
            (self.root / name).write_bytes((ROOT / 'examples/synthetic-sources' / name).read_bytes())
        handoff = prepare_observation_handoff(load_segment_corpus(manifest, self.root))
        self.save('corpus', manifest)
        self.save('handoff', handoff)
        self.save('response', dict(handoff_sha256=payload_sha256(handoff), candidates=[]))
        result = self.cli('preflight-observations', '--source-root', self.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['evidence_rows_checked'], 0)
        self.assertEqual(json.loads(result.stdout)['source_basis'], 'PINNED_LOCAL_FILES')
        path = self.root / manifest['papers'][0]['source_file']
        path.write_bytes(b'PRIVATE changed bytes')
        for remove in (False, True):
            if remove:
                path.unlink()
            result = self.cli('preflight-observations', '--source-root', self.root)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(json.loads(result.stdout)['status'], 'CORPUS_REJECTED')
            self.assertNotIn(b'PRIVATE', result.stdout + result.stderr)
            self.assertEqual(result.stderr, b'')

    def test_oversize_rows_reject_without_using_sources(self):
        self.save('response', dict(self.response, candidates=[{'PRIVATE': None}] * 129))
        with patch.object(preflight, 'prepare_observation_handoff', side_effect=AssertionError):
            report = preflight.inspect_files(*self.paths)
        self.assertEqual(report['errors'], [dict(path=['response', 'candidates'], code='MAX_ITEMS')])

    def test_content_free_json_bounds_unicode_and_cli_errors(self):
        self.provenance['operator_id'] = 'PRIVATE\ud800'
        self.save('provenance', self.provenance)
        with patch('strict_json.MAX_INPUT_BYTES', 1024):
            self.paths[2].write_bytes(b' ' * 1025)
            report = preflight.inspect_files(*self.paths)
        self.assertEqual(report['errors'], [
            dict(path=['response'], code='INPUT_UNREADABLE_OR_INVALID'),
            dict(path=['provenance', 'operator_id'], code='NOT_UTF8_ENCODABLE')])
        destination = self.root / 'PRIVATE-report.json'
        for options in [('--format', 'PRIVATE'), ('--PRIVATE',), ('--output', destination)]:
            result = self.cli('preflight-observations', *options)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, b'')
            self.assertNotIn(b'PRIVATE', result.stderr)
            self.assertIn(b'--help', result.stderr)
        self.assertFalse(destination.exists())

    def test_quote_is_confined_to_named_segment_and_exact_unicode(self):
        row = self.response['candidates'][0]
        rows = [dict(row, locator='synthetic section 1'), dict(row, evidence_quote='Compare\u00a0explanations.')]
        self.save('response', dict(self.response, candidates=rows))
        report = preflight.inspect_files(*self.paths)
        self.assertEqual(report['errors'], [dict(path=['response', 'candidates', str(index), 'evidence_quote'],
                                                  code='QUOTE_MISMATCH') for index in range(2)])
        self.assertEqual(self.cli('import', '--task', 'observations').returncode, 1)

    def test_corpus_drift_and_wrong_task_fail_before_row_checks(self):
        from extraction_adapter import prepare_model_handoff
        self.save('corpus', dict(self.corpus, extra='PRIVATE'))
        report = preflight.inspect_files(*self.paths)
        self.assertEqual(report['errors'], [dict(path=['handoff'], code='HANDOFF_NOT_CURRENT')])
        self.save('corpus', self.corpus)
        reasoning = prepare_model_handoff(self.corpus)
        self.save('handoff', reasoning)
        self.save('response', dict(self.response, handoff_sha256=payload_sha256(reasoning)))
        with patch.object(preflight, 'quote_issue', side_effect=AssertionError):
            self.assertEqual(preflight.inspect_files(*self.paths), report)

    def test_128_rows_preserve_order_without_import_or_network(self):
        row = dict(self.response['candidates'][0], locator='PRIVATE')
        self.save('response', dict(self.response, candidates=[row] * 128))
        with patch('socket.socket', side_effect=AssertionError), patch(
                'observation_proposals.import_observation_response', side_effect=AssertionError):
            report = preflight.inspect_files(*self.paths)
        self.assertEqual(report['evidence_rows_checked'], 128)
        self.assertEqual(report['errors'], [dict(path=['response', 'candidates', str(index), 'locator'],
                                                code='UNKNOWN_LOCATOR') for index in range(128)])


if __name__ == '__main__':
    unittest.main()
