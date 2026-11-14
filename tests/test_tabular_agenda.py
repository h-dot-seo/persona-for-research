"""Fresh bound journey agenda rows, never cached approval or spreadsheet decisions."""
import copy
import csv
import io
import json
import shlex
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import journey_inputs as inputs
import tabular_export as t
from persona import payload_sha256
import tests.test_journey_inputs as fixture

ROOT=Path(__file__).resolve().parents[1]


class AgendaTests(unittest.TestCase):
    def setUp(self):
        self.case=fixture.JourneyInputTests();self.case.setUp();self.addCleanup(self.case.doCleanups)
        self.root=self.case.root
        self.card=self.case.prepare()
        self.path=self.root/'bound-card.json'
        self.path.write_bytes((json.dumps(self.card)+'\n').encode('utf-8'))

    def rows(self,raw,delimiter=','):
        return list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig')),delimiter=delimiter))

    def cli(self,*args):
        return subprocess.run([sys.executable,str(ROOT/'tabular_export.py'),*map(str,args)],cwd=ROOT,capture_output=True)

    def test_fresh_agenda_all_targets_status_bindings_and_unchanged_files(self):
        before={p.name:p.read_bytes() for p in self.root.iterdir()}
        report=inputs.inspect(self.card,self.root)
        rows=self.rows(t.render_agenda(self.card,self.root))
        self.assertEqual(len(rows),len(report['review_agenda']));self.assertTrue(rows)
        for row,item in zip(rows,report['review_agenda']):
            self.assertEqual(row['domain'],item['domain']);self.assertEqual(row['code'],item['code'])
            self.assertEqual(json.loads(row['target_json']),{k:v for k,v in item.items() if k not in ('domain','code')})
            self.assertEqual(row['status'],'HUMAN_REVIEW_REQUIRED_NOT_RESEARCH_APPROVAL')
            self.assertEqual(row['journey_input_sha256'],report['journey_input_sha256'])
            self.assertEqual(row['input_card_sha256'],payload_sha256(self.card))
            self.assertEqual(row['source_reread'],'false')
            self.assertIn(report['boundary'],row['boundary'])
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.root.iterdir()})

    def test_cached_report_and_selection_form_are_rejected(self):
        for value in (inputs.inspect(self.card,self.root),self.case.selection):
            with self.assertRaises(ValueError):t.render_agenda(value,self.root)

    def test_stale_bytes_and_edited_card_rejected_without_refresh(self):
        path=self.case.path('patterns');path.write_bytes(path.read_bytes()+b' ')
        before=copy.deepcopy(self.card)
        with self.assertRaisesRegex(ValueError,'bytes changed'):t.render_agenda(self.card,self.root)
        self.assertEqual(before,self.card)
        with self.assertRaises(ValueError):t.render_agenda(dict(self.card,pattern_id='unselected'),self.root)

    def test_source_root_requires_explicit_selection_and_reread_boundary_changes(self):
        with self.assertRaisesRegex(ValueError,'supplied together'):
            t.render_agenda(self.card,self.root,source_root=ROOT/'examples/synthetic-sources')
        source_root=self.case.source_selection();card=self.case.prepare(source_root=source_root)
        with self.assertRaisesRegex(ValueError,'supplied together'):t.render_agenda(card,self.root)
        report=inputs.inspect(card,self.root,source_root=source_root)
        rows=self.rows(t.render_agenda(card,self.root,source_root=source_root))
        self.assertEqual(len(rows),len(report['review_agenda']))
        for row in rows:
            self.assertEqual(row['source_reread'],'true')
            self.assertIn('Selected local files were reread',row['boundary'])
            self.assertNotIn('No source reread,',row['boundary'])
        self.assertEqual(sum(row['domain']=='current_source_recheck' for row in rows),
                         sum(item['domain']=='current_source_recheck' for item in report['review_agenda']))

    def test_header_only_is_not_an_approval_row(self):
        report=inputs.inspect(self.card,self.root);report['review_agenda']=[]
        with patch.object(inputs,'inspect',return_value=report):raw=t.render_agenda(self.card,self.root)
        self.assertEqual(raw,(','.join(t.AGENDA_COLUMNS)+'\n').encode())
        self.assertEqual(self.rows(raw),[])
        self.assertIn('not review completion or approval',t.describe('review-agenda')['empty'])

    def test_dynamic_target_keys_preserved_with_unicode_and_controls(self):
        report=inputs.inspect(self.card,self.root)
        item=dict(domain='=synthetic',code='@code',unknown_future_field=['한국어','\n\u202e'],nested={'empty':None})
        report['review_agenda']=[item]
        with patch.object(inputs,'inspect',return_value=report):row=self.rows(t.render_agenda(self.card,self.root))[0]
        self.assertEqual(row['domain'],"'=synthetic");self.assertEqual(row['code'],"'@code")
        self.assertEqual(json.loads(row['target_json']),{k:v for k,v in item.items() if k not in ('domain','code')})
        self.assertNotIn('\n',row['target_json'])

    def test_bom_tsv_limits_and_invalid_card_no_file(self):
        raw=t.render_agenda(self.card,self.root)
        self.assertEqual(t.render_agenda(self.card,self.root,excel_bom=True),b'\xef\xbb\xbf'+raw)
        self.assertEqual(self.rows(raw),self.rows(t.render_agenda(self.card,self.root,format='tsv'),'\t'))
        with patch.object(t,'MAX_OUTPUT_BYTES',len(raw)-1),self.assertRaisesRegex(ValueError,'16 MiB'):
            t.render_agenda(self.card,self.root)
        self.path.write_bytes(b' '*(128*1024+1));out=self.root/'missing.csv'
        result=self.cli('review-agenda',self.path,'--input-root',self.root,'--output',out)
        self.assertEqual(result.returncode,1);self.assertEqual(result.stdout,b'');self.assertFalse(out.exists())

    def test_cli_describe_modes_and_exclusive_save(self):
        result=self.cli('review-agenda','--describe');self.assertEqual(result.returncode,0,result.stderr)
        description=json.loads(result.stdout)
        self.assertEqual(description['columns'],list(t.AGENDA_COLUMNS));self.assertEqual(description['max_card_bytes'],128*1024)
        args=['review-agenda',self.path,'--input-root',self.root]
        plain=self.cli(*args);out=self.root/'agenda.csv'
        result=self.cli(*args,'--output',out);self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(out.read_bytes(),plain.stdout)
        for argv in (('review-agenda',self.path),('reference-catalog',self.path,'--input-root',self.root),
                     ('review-agenda','--describe','--input-root',self.root)):
            result=self.cli(*argv);self.assertEqual(result.returncode,1);self.assertEqual(result.stdout,b'')

    def test_guide_argv_native_paths_are_substituted_after_split(self):
        # Same runner rule as reference export: tokenize before host paths enter argv.
        text=(ROOT/'docs/TABULAR_EXPORT.md').read_text(encoding='utf-8').split('## Fresh journey review agenda',1)[1].split('## Fresh journey evidence routes',1)[0]
        count=0
        for block in text.split('```sh\n')[1:]:
            for line in block.split('```',1)[0].splitlines():
                if not line or line.startswith('#'):continue
                argv=[part.replace('CARD',str(self.path)).replace('INPUTS',str(self.root)).replace('OUTPUT',str(self.root))
                      for part in shlex.split(line)]
                argv[0]=sys.executable
                result=subprocess.run(argv,cwd=ROOT,capture_output=True)
                self.assertEqual(result.returncode,0,result.stderr);count+=1
        self.assertEqual(count,2)
