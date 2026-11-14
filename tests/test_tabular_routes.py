"""Fresh route tables preserve exact evidence and uses, not spreadsheet decisions."""
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
import source_recheck
import tabular_export as t
import tests.test_journey_inputs as fixture
import tests.test_application_proposals as application_fixture

ROOT=Path(__file__).resolve().parents[1]


def guide_argv(line, card, root, output):
    return [part.replace('CARD',str(card)).replace('INPUTS',str(root)).replace('OUTPUT',str(output))
            for part in shlex.split(line)]


class RouteTests(unittest.TestCase):
    def setUp(self):
        self.case=fixture.JourneyInputTests();self.case.setUp();self.addCleanup(self.case.doCleanups)
        self.root=self.case.root;self.card=self.case.prepare();self.path=self.root/'route card.json'
        self.path.write_bytes((json.dumps(self.card)+'\n').encode())

    def rows(self,raw,delimiter=','):
        return list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig')),delimiter=delimiter))

    def cli(self,*args):
        return subprocess.run([sys.executable,str(ROOT/'tabular_export.py'),*map(str,args)],cwd=ROOT,capture_output=True)

    def application(self):
        case=application_fixture.ApplicationProposalTests();case.setUp();case.accept()
        self.addCleanup(case.doCleanups);self.case.write('method_applications',case.envelope())

    def test_exact_route_evidence_use_lists_and_native_order(self):
        before={p.name:p.read_bytes() for p in self.root.iterdir()}
        report=inputs.inspect(self.card,self.root);rows=self.rows(t.render_routes(self.card,self.root))
        self.assertEqual(len(rows),len(report['evidence_routes']));self.assertTrue(rows)
        for row,route in zip(rows,report['evidence_routes']):
            node=route['evidence']
            self.assertEqual(json.loads(row['evidence_json']),node)
            self.assertEqual(json.loads(row['reference_json']),node['reference'])
            self.assertEqual(row['reference_sha256'],route['reference_sha256'])
            for key in t.ROUTE_USES:
                self.assertEqual(json.loads(row[key+'_json']),route[key]);self.assertEqual(int(row[key+'_count']),len(route[key]))
            self.assertEqual(json.loads(row['pattern_roles_json']),route['pattern_roles'])
            for key in ('in_topic_timeline','actively_used_in_answer_or_design'):
                self.assertIs(json.loads(row[key]),route[key])
            self.assertEqual(row['publication_scope'],route['publication_scope'])
            self.assertEqual(row['journey_input_sha256'],report['journey_input_sha256'])
            self.assertIn(report['boundary'],row['boundary'])
            self.assertEqual(row['observation_claim_type'],node['observation']['claim_type'])
            if node['component'] is None:self.assertEqual(row['component_quote_check'],t.NOT_APPLICABLE)
            if node['component'] is not None:self.assertEqual(row['component_claim_type'],node['component']['claim_type'])
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.root.iterdir()})

    def test_all_four_pinned_option_headers_and_real_values(self):
        for method,source in ((False,False),(True,False),(False,True),(True,True)):
            with self.subTest(method=method,source=source):
                self.case.selection['artifacts']['method_applications']=None
                self.case.selection['artifacts']['source_selection']=None
                if method:self.application()
                root=self.case.source_selection() if source else None
                card=self.case.prepare(source_root=root)
                report=inputs.inspect(card,self.root,source_root=root)
                raw=t.render_routes(card,self.root,source_root=root);rows=self.rows(raw)
                self.assertEqual(next(csv.reader(io.StringIO(raw.decode()))),list(t.route_columns(method,source)))
                for row,route in zip(rows,report['evidence_routes']):
                    self.assertEqual('method_application_uses_json' in row,method)
                    self.assertEqual('current_source_recheck_json' in row,source)
                    if method:
                        self.assertEqual(json.loads(row['method_application_uses_json']),route['method_application_uses'])
                        self.assertEqual(int(row['method_application_uses_count']),len(route['method_application_uses']))
                    if source:self.assertEqual(json.loads(row['current_source_recheck_json']),route['current_source_recheck'])
                    self.assertIs(json.loads(row['source_reread']),source)

    def test_empty_headers_still_follow_options(self):
        for method,source in ((False,False),(True,False),(False,True),(True,True)):
            card=copy.deepcopy(self.card)
            if method:card['artifacts']['method_applications']={'synthetic':'pinned'}
            if source:card['artifacts']['source_selection']={'synthetic':'pinned'}
            report=inputs.inspect(self.card,self.root);report['evidence_routes']=[]
            with patch.object(inputs,'inspect',return_value=report):raw=t.render_routes(card,self.root)
            self.assertEqual(raw,(','.join(t.route_columns(method,source))+'\n').encode())
            self.assertIn('not review completion or approval',t.describe('evidence-routes')['empty'])

    def test_exact_json_retains_absent_null_false_controls_and_labels(self):
        report=inputs.inspect(self.card,self.root);report['evidence_routes']=report['evidence_routes'][:1]
        route=report['evidence_routes'][0];node=route['evidence']
        node['observation']['evidence_quote']=None;node['observation']['method']='=formula\n한국어\u202e'
        node['component']={'claim_type':'operator_interpretation','text':'@component','origin':None,'synthetic_false':False}
        node['reference']['dimension']='uncertainty';route['in_topic_timeline']=False
        route['answer_uses']=[dict(decision='defer',nullable=None,false_value=False,empty='',nested=['\t','\r','\u202e'])]
        with patch.object(inputs,'inspect',return_value=report):row=self.rows(t.render_routes(self.card,self.root))[0]
        self.assertEqual(json.loads(row['evidence_json']),node)
        self.assertEqual(json.loads(row['answer_uses_json']),route['answer_uses'])
        self.assertEqual(row['component_quote_check'],'NOT_PERFORMED')
        self.assertNotIn('evidence_verification',json.loads(row['evidence_json'])['component'])
        self.assertEqual(row['component_origin'],t.NOT_SUPPLIED)
        self.assertEqual(row['component_proposed_claim_type'],t.NOT_APPLICABLE)
        self.assertEqual(row['observation_evidence_quote'],t.NOT_SUPPLIED)
        self.assertEqual(row['component_text'],"'@component")
        self.assertTrue(row['observation_method'].startswith("'=formula\\u000a"))
        self.assertEqual(row['in_topic_timeline'],'false')

    def test_declared_reject_defer_and_citation_roles_not_promoted(self):
        report=inputs.inspect(self.card,self.root)
        rows=self.rows(t.render_routes(self.card,self.root))
        seen=[]
        for row,route in zip(rows,report['evidence_routes']):
            for key in ('answer_uses','direct_argument_uses','unused_link_uses','design_uses'):
                values=json.loads(row[key+'_json']);self.assertEqual(values,route[key])
                seen.extend(v.get('declared_review_decision') for v in values)
            self.assertEqual(row['status'],'HUMAN_REVIEW_REQUIRED_NOT_RESEARCH_APPROVAL')
        self.assertIn('defer',seen)
        # Unknown future keys and reject/defer labels are copied, not interpreted.
        route=report['evidence_routes'][0]
        route['direct_argument_uses']=[dict(declared_review_decision='reject',citation_role='counterevidence'),
                                       dict(declared_review_decision='defer',citation_role='support')]
        with patch.object(inputs,'inspect',return_value=report):row=self.rows(t.render_routes(self.card,self.root))[0]
        self.assertEqual(json.loads(row['direct_argument_uses_json']),route['direct_argument_uses'])

    def test_cached_card_tamper_and_stale_artifact_fail(self):
        for card in (inputs.inspect(self.card,self.root),self.case.selection):
            with self.assertRaises(ValueError):t.render_routes(card,self.root)
        bad=copy.deepcopy(self.card);bad['artifacts']['patterns']['raw_sha256']='0'*64
        with self.assertRaises(ValueError):t.render_routes(bad,self.root)
        self.case.path('patterns').write_bytes(self.case.path('patterns').read_bytes()+b' ')
        with self.assertRaises(ValueError):t.render_routes(self.card,self.root)

    def test_source_pair_required_and_stale_blocks_source_read(self):
        with self.assertRaises(ValueError):t.render_routes(self.card,self.root,source_root=ROOT/'examples/synthetic-sources')
        source=self.case.source_selection();card=self.case.prepare(source_root=source)
        with self.assertRaises(ValueError):t.render_routes(card,self.root)
        self.case.path('patterns').write_bytes(self.case.path('patterns').read_bytes()+b' ')
        with patch.object(source_recheck,'read_source_bytes',side_effect=AssertionError('no reread')):
            with self.assertRaises(ValueError):t.render_routes(card,self.root,source_root=source)

    def test_csv_tsv_bom_and_output_cell_limits(self):
        raw=t.render_routes(self.card,self.root)
        self.assertEqual(self.rows(raw),self.rows(t.render_routes(self.card,self.root,format='tsv'),'\t'))
        self.assertEqual(t.render_routes(self.card,self.root,excel_bom=True),b'\xef\xbb\xbf'+raw)
        with patch.object(t,'MAX_OUTPUT_BYTES',len(raw)-1),self.assertRaises(ValueError):t.render_routes(self.card,self.root)
        with patch.object(t,'MAX_CELL_CHARS',1),self.assertRaises(ValueError):t.render_routes(self.card,self.root)

    def test_describe_without_reads_and_cli_preflight_limits(self):
        with patch.object(inputs,'inspect',side_effect=AssertionError('must not inspect')):
            description=t.describe('evidence-routes')
        self.assertEqual(len(description['column_sets']),4)
        for row in description['column_sets']:
            self.assertEqual(row['columns'],list(t.route_columns(row['method_applications'],row['source_selection'])))
        self.assertEqual(description['max_card_bytes'],128*1024)
        result=self.cli('evidence-routes','--describe');self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout),description)
        for args in [('evidence-routes',self.path),('evidence-routes','--describe','--input-root',self.root)]:
            result=self.cli(*args);self.assertNotEqual(result.returncode,0);self.assertEqual(result.stdout,b'')
        self.path.write_bytes(b' '*(128*1024+1));out=self.root/'not-created.csv'
        result=self.cli('evidence-routes',self.path,'--input-root',self.root,'--output',out)
        self.assertEqual(result.returncode,1);self.assertEqual(result.stdout,b'');self.assertFalse(out.exists())

    def test_guide_native_path_tokenization_and_commands(self):
        windows=r'C:\Users\Synthetic Name\Temp'
        argv=guide_argv('python tabular_export.py evidence-routes CARD --input-root INPUTS --output OUTPUT/routes.csv',windows+'\\card.json',windows,windows)
        self.assertEqual(argv[3],windows+'\\card.json');self.assertEqual(argv[5],windows);self.assertEqual(argv[-1],windows+'/routes.csv')
        text=(ROOT/'docs/TABULAR_EXPORT.md').read_text(encoding='utf-8').split('## Fresh journey evidence routes',1)[1]
        count=0
        for block in text.split('```sh\n')[1:]:
            for line in block.split('```',1)[0].splitlines():
                if not line or line.startswith('#'):continue
                argv=guide_argv(line,self.path,self.root,self.root);self.assertNotIn('>',argv);argv[0]=sys.executable
                result=subprocess.run(argv,cwd=ROOT,capture_output=True)
                self.assertEqual(result.returncode,0,result.stderr);count+=1
        self.assertEqual(count,2)


if __name__=='__main__':unittest.main()
