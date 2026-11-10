"""Synthetic source diagnostics; no real sources or scholarly judgments."""
import copy
import json
import re
import shlex
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from corpus_files import sections
from prepare_local_manifest import report_defects, scan_structure, prepare
from tests import test_prepare_local_manifest as fixture


class SourceStructureReportTests(unittest.TestCase):
    def setUp(self):
        fixture.PrepareLocalManifestTests.setUp(self)

    def report(self, raw):
        (self.root/'paper.md').write_bytes(raw)
        return report_defects(self.selection,self.root)

    def test_whole_selection_mixed_results_and_no_body(self):
        other=copy.deepcopy(self.selection['papers'][0]);other['paper_id']='synthetic-second';other['source_file']='other.md'
        self.selection['papers'].append(other);(self.root/'other.md').write_bytes(b'## Invalid\n\xffSECRET')
        original=copy.deepcopy(self.selection)
        result=report_defects(self.selection,self.root)
        self.assertEqual(result['status'],'SOME_SELECTED_FILES_WOULD_NOT_PARSE')
        self.assertEqual(result['papers'][1]['invalid_utf8_byte_offset'],11)
        self.assertEqual(result['papers'][0]['section_parse'],'WOULD_SUCCEED')
        self.assertNotIn('SECRET',json.dumps(result));self.assertNotIn('SYNTHETIC_BODY_NOT_COPIED',json.dumps(result))
        self.assertEqual(self.selection,original)
        self.assertEqual((self.root/'paper.md').read_bytes(),self.raw)
        for key in ('llm_used','manifest_written','source_files_modified'):self.assertFalse(result[key])
        self.assertEqual(result['conversion_fidelity'],'NOT_ASSESSED')
        with self.assertRaises(ValueError):prepare(result,self.root)

    def test_parser_decides_status_including_accepted_findings(self):
        for text in ('No headings','## \nbody','## Same\na\n## Same\nb','## A\n## B\nb','## A  \nb','\ufeff## A\na\n## B\nb','## Name ## {#id}\nx'):
            with self.subTest(text=text):
                row=self.report(text.encode())['papers'][0]
                try: expected=sections(text)
                except ValueError as exc:
                    self.assertEqual(row['section_parse'],'WOULD_RAISE');self.assertEqual(row['section_error'],str(exc))
                else:
                    self.assertEqual(row['section_parse'],'WOULD_SUCCEED')
                    self.assertEqual([r['locator'] for r in row['headings']],list(expected))
        row=self.report(b'## A \n## B\nb')['papers'][0]
        self.assertEqual({r['code'] for r in row['findings']},{'EMPTY_SECTION','WHITESPACE_TRIMMED'})
        self.assertEqual(row['section_parse'],'WOULD_SUCCEED')

    def test_bom_near_misses_cf_preamble_and_deeper_body(self):
        text='\ufeff## Hidden\nSECRET PREAMBLE\n## A\n ## Near\n  ## Near\n   ## Near\n##\tNear\n##\u00a0Near\n##Near\n### Deep\n## B\u200b\nbody'
        row=self.report(text.encode())['papers'][0]
        self.assertEqual(row['encoding'],'UTF8_BOM');self.assertEqual(row['preamble_lines'],2)
        self.assertEqual(row['preamble_characters'],len('\ufeff## Hidden\nSECRET PREAMBLE'))
        codes=[r['code'] for r in row['findings']]
        self.assertEqual(codes.count('NEAR_MISS_HEADING'),6)
        self.assertIn('FIRST_LINE_HEADING_HIDDEN_BY_BOM',codes)
        self.assertIn('INVISIBLE_FORMAT_CHARACTER_IN_LOCATOR',codes)
        self.assertEqual(row['deeper_heading_lines_in_body'],1)
        self.assertNotIn('SECRET PREAMBLE',json.dumps(row));self.assertNotIn('Near',json.dumps(row))
        self.assertIn('\\u200b',json.dumps(row))

    def test_all_splitlines_breaks_and_line_numbers(self):
        text='p\r\n## A\nbody\rmore\vmore\fmore\x1cmore\x1dmore\x1emore\x85more\u2028more\u2029## B\n'
        row=scan_structure(text)
        self.assertEqual(row['line_breaks'],dict(LF=2,CRLF=1,CR=1,other=8))
        self.assertEqual([r['line_number'] for r in row['headings']],[2,12])

    def test_hash_mismatch_and_curated_observations_still_fail(self):
        self.selection['papers'][0]['source_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'byte hash'):report_defects(self.selection,self.root)
        self.selection['papers'][0]['observations']=[{}]
        with patch('prepare_local_manifest.read_source_bytes',side_effect=AssertionError('read')):
            with self.assertRaisesRegex(ValueError,'empty observations'):report_defects(self.selection,self.root)

    def test_reader_failure_is_not_a_report_row(self):
        with patch('prepare_local_manifest.read_source_bytes',side_effect=ValueError('selected source changed while reading')):
            with self.assertRaisesRegex(ValueError,'changed while reading'):report_defects(self.selection,self.root)

    def test_row_limits_count_omissions_without_changing_parser_status(self):
        with patch('prepare_local_manifest.MAX_REPORT_ROWS',2):
            row=scan_structure('## A \n## B \n## C \n## D \n')
        self.assertEqual(row['section_parse'],'WOULD_SUCCEED');self.assertEqual(len(row['headings']),2)
        self.assertEqual(row['headings_omitted'],2);self.assertEqual(len(row['findings']),2)
        self.assertEqual(row['findings_omitted'],6)

    def test_output_limit_and_scanner_disagreement_fail_closed(self):
        with patch('prepare_local_manifest.MAX_REPORT_BYTES',10):
            with self.assertRaisesRegex(ValueError,'8 MiB'):report_defects(self.selection,self.root)
        with patch('prepare_local_manifest.sections',return_value={'different':'body'}):
            with self.assertRaisesRegex(ValueError,'disagreement'):report_defects(self.selection,self.root)

    def cli(self, raw):
        selection=self.root/'selection.json';selection.write_bytes(raw)
        return subprocess.run([sys.executable,'prepare_local_manifest.py',str(selection),'--source-root',str(self.root),'--report-defects'],capture_output=True)

    def test_cli_defects_exit_zero_failure_empty_stdout_and_strict_json(self):
        (self.root/'paper.md').write_bytes(b'not markdown')
        result=self.cli(json.dumps(self.selection).encode());self.assertEqual(result.returncode,0)
        self.assertEqual(json.loads(result.stdout)['status'],'SOME_SELECTED_FILES_WOULD_NOT_PARSE')
        for raw in (b'{"papers": [], "papers": []}',b'{"papers": NaN}',b'{"papers": Infinity}'):
            result=self.cli(raw);self.assertNotEqual(result.returncode,0);self.assertEqual(result.stdout,b'')
        (self.root/'paper.md').unlink()
        result=self.cli(json.dumps(self.selection).encode());self.assertNotEqual(result.returncode,0);self.assertEqual(result.stdout,b'')

    def test_existing_safe_reader_race_and_escape_checks_in_report_mode(self):
        for name in ('test_symlink_escape_is_rejected_before_reading_bytes',
                     'test_replaced_symlink_after_preflight_rejected_before_byte_read',
                     'test_descriptor_identity_mismatch_rejected_before_stream_read',
                     'test_detected_change_during_read_is_rejected'):
            with self.subTest(name=name):
                case=fixture.PrepareLocalManifestTests(name)
                case.setUp()
                try:
                    with patch.object(fixture,'prepare',report_defects):
                        getattr(case,name)()
                finally:
                    case.doCleanups()

    def test_documented_command_executes_exactly(self):
        guide=Path('docs/LOCAL_INPUT_PREPARATION.md').read_text(encoding='utf-8')
        blocks=re.findall(r'```sh\n(.*?)```',guide,re.S);self.assertEqual(len(blocks),1)
        for line in blocks[0].strip().splitlines():
            self.assertNotIn('>',line);args=shlex.split(line);self.assertEqual(args[0],'python')
            result=subprocess.run([sys.executable]+args[1:],capture_output=True,check=True)
            self.assertEqual(json.loads(result.stdout)['status'],'ALL_SELECTED_FILES_WOULD_PARSE')
