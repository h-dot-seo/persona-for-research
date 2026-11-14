"""Synthetic package-to-sheet contracts; no spreadsheet write-back or identity inference."""
import copy
import csv
import io
import json
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import tabular_export as t
from corpus_files import load_sources
from curate_local import append_observation
from prepare_local_manifest import prepare
from research_workflow import build
from review_workspace import create
from strict_json import load

ROOT = Path(__file__).resolve().parents[1]


def guide_argv(line, output):
    # Parse the documented POSIX command before substituting native Windows paths.
    return [part.replace('OUTPUT', str(output)) for part in shlex.split(line)]


class TabularTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name)
        self.manifest = prepare(load(ROOT/'examples/local-selection.json'), ROOT/'examples/synthetic-sources')
        self.empty = build(load_sources(self.manifest, ROOT/'examples/synthetic-sources'))
        for name in ('research', 'review'):
            self.manifest = append_observation(self.manifest, load(ROOT/f'examples/manual-{name}-card.json'), ROOT/'examples/synthetic-sources')
        self.package = build(load_sources(self.manifest, ROOT/'examples/synthetic-sources'))

    def rows(self, raw, delimiter=','):
        return list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig')), delimiter=delimiter))

    def cli(self, *args):
        return subprocess.run([sys.executable, str(ROOT/'tabular_export.py'), *map(str,args)], cwd=ROOT, capture_output=True)

    def test_catalog_exact_refs_separate_components_and_unchanged_input(self):
        before = copy.deepcopy(self.package)
        create(self.package, self.out/'workspace', 'q', 'operator', 2020)
        catalog = load(self.out/'workspace/reference-catalog.json')
        rows = self.rows(t.render(self.package))
        self.assertEqual(len(rows), 4)
        for row, entry in zip(rows, catalog['entries']):
            node=entry['evidence']; ref=node['reference']
            self.assertEqual(json.loads(row['reference_json']), ref)
            self.assertEqual(row['persona_sha256'], catalog['persona_sha256'])
            self.assertEqual(row['knowledge_papers_sha256'], catalog['knowledge_papers_sha256'])
            self.assertEqual(row['observation_claim_type'], node['observation']['claim_type'])
            self.assertEqual(row['row_kind'], 'OBSERVATION' if ref['dimension'] is None else 'COMPONENT')
            if ref['dimension'] is None:
                self.assertEqual(row['component_claim_type'], t.NOT_APPLICABLE)
            else:
                self.assertEqual(row['component_claim_type'], node['component']['claim_type'])
            self.assertEqual(row['boundary'], t.BOUNDARY)
        self.assertEqual(self.package, before)

    def test_empty_observations_not_dropped(self):
        rows=self.rows(t.render(self.empty))
        self.assertEqual([r['paper_id'] for r in rows], ['synthetic-0','synthetic-1'])
        for row in rows:
            self.assertEqual(row['row_kind'],'PAPER_WITHOUT_OBSERVATIONS')
            self.assertEqual(row['reference_json'],t.NOT_APPLICABLE)
            self.assertEqual(row['missing_reasoning_dimensions'],t.NOT_APPLICABLE)
            self.assertNotIn('',row.values())

    def test_display_markers_controls_and_formula_guard(self):
        for value in ('=SUM(A1:A2)', '+1', '-1', '@cmd'):
            self.assertEqual(t.cell(value), "'"+value)
        self.assertEqual(t.cell('\t=1\r\n\u202e'),r'\u0009=1\u000d\u000a\u202e')
        self.assertEqual(t.cell(None),t.NOT_SUPPLIED)
        self.assertEqual(t.cell(''),t.EMPTY_STRING)
        self.assertEqual(t.cell(False),'false')
        self.assertEqual(t.cell([]),'[]')
        self.assertEqual(t.cell('한국어'),'한국어')
        self.assertEqual(t.cell('"quotes",semicolon;'), '"quotes",semicolon;')

    def test_cell_boundary_counts_guard_and_escaping(self):
        self.assertEqual(len(t.cell('a'*32767)),32767)
        for value in ('a'*32768, '='+'a'*32766, '\n'*5462):
            with self.assertRaisesRegex(ValueError,'32767'):t.cell(value)

    def test_tsv_bom_and_lf_determinism(self):
        plain=t.render(self.package); self.assertNotIn(b'\r',plain)
        self.assertEqual(plain,t.render(self.package))
        self.assertEqual(t.render(self.package,excel_bom=True),b'\xef\xbb\xbf'+plain)
        self.assertEqual(self.rows(plain),self.rows(t.render(self.package,format='tsv'),'\t'))
        self.assertEqual(list(self.rows(plain)[0]),list(t.COLUMNS))

    def test_reject_saved_catalog_stale_and_holdout(self):
        create(self.package,self.out/'workspace','q','op',2020)
        with self.assertRaises((ValueError,KeyError,TypeError)):
            t.render(load(self.out/'workspace/reference-catalog.json'))
        for key,value in (('split','holdout'),('paper_id','edited')):
            changed=copy.deepcopy(self.package);changed['knowledge']['papers'][0][key]=value
            with self.assertRaises(ValueError):t.render(changed)

    def test_output_limit_header_and_rows_no_truncation(self):
        raw=t.render(self.package)
        with patch.object(t,'MAX_OUTPUT_BYTES',len(raw)):
            self.assertEqual(t.render(self.package),raw)
        for maximum in (1,len(raw)-1):
            with patch.object(t,'MAX_OUTPUT_BYTES',maximum),self.assertRaisesRegex(ValueError,'16 MiB'):
                t.render(self.package)

    def test_describe_contract_and_invalid_cli_empty_stdout(self):
        result=self.cli('reference-catalog','--describe')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['columns'],list(t.COLUMNS))
        for args in (('reference-catalog',),('reference-catalog','--describe','--excel-bom'),
                     ('reference-catalog','examples/trajectory-conditions-package.json','--describe')):
            result=self.cli(*args);self.assertEqual(result.returncode,1);self.assertEqual(result.stdout,b'')
            self.assertNotIn(b'Traceback',result.stderr)

    def test_exclusive_output_matches_stdout_and_no_overwrite(self):
        args=['reference-catalog','examples/trajectory-conditions-package.json','--format','tsv','--excel-bom']
        normal=self.cli(*args);self.assertEqual(normal.returncode,0,normal.stderr)
        target=self.out/'refs.tsv';saved=self.cli(*args,'--output',target)
        self.assertEqual(saved.returncode,0,saved.stderr)
        self.assertEqual(target.read_bytes(),normal.stdout)
        self.assertIsNone(json.loads(saved.stdout)['payload_sha256'])
        again=self.cli(*args,'--output',target)
        self.assertEqual(again.returncode,1);self.assertEqual(target.read_bytes(),normal.stdout)

    def test_failed_input_leaves_no_file_and_input_bound(self):
        bad=self.out/'bad.json';bad.write_bytes(b'{}')
        target=self.out/'none.csv'
        result=self.cli('reference-catalog',bad,'--output',target)
        self.assertEqual(result.returncode,1);self.assertEqual(result.stdout,b'');self.assertFalse(target.exists())
        bad.write_bytes(b' '*(8*1024*1024+1))
        result=self.cli('reference-catalog',bad)
        self.assertEqual(result.returncode,1);self.assertEqual(result.stdout,b'')
        self.assertIn(b'exceeds',result.stderr)

    def test_guide_native_windows_path_survives_tokenization(self):
        path=r'C:\Users\Synthetic Name\Temp'
        args=guide_argv('python tabular_export.py reference-catalog package.json --output OUTPUT/references.csv',path)
        self.assertEqual(args[-1],path+'/references.csv')
        self.assertEqual(len(args),6)

    def test_documented_commands(self):
        text=(ROOT/'docs/TABULAR_EXPORT.md').read_text(encoding='utf-8')
        count=0
        for block in text.split('```sh\n')[1:]:
            for line in block.split('```',1)[0].splitlines():
                if not line or line.startswith('#'):continue
                argv=guide_argv(line,self.out)
                argv[0]=sys.executable
                result=subprocess.run(argv,cwd=ROOT,capture_output=True)
                self.assertEqual(result.returncode,0,result.stderr);count+=1
        self.assertEqual(count,3)
