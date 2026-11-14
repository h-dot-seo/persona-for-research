"""Static, opt-in source-input diagnostics; no guessed binding or permission causes."""
import copy
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import prepare_local_manifest as prepare
import source_recheck as recheck
import rejection_details as details
from corpus_files import load_sources
from research_workflow import build
from tests import test_curate_local as manual_fixtures
from curate_local import append_observation

ROOT=Path(__file__).resolve().parents[1]

class SourceRejectionTests(unittest.TestCase):
    def setUp(self):
        self.selection=json.loads((ROOT/'examples/local-selection.json').read_bytes())
        case=manual_fixtures.ManualObservationTests();case.setUp()
        self.source=case.root
        self.package=build(load_sources(append_observation(case.manifest,case.card(),self.source),self.source))
        self.form=recheck.template(self.package,'synthetic-operator')
        for row in self.form['sources']:row['source_file']=row['paper_id']+'.md'

    def error(self,fn,*args,**kwargs):
        with self.assertRaises(ValueError) as caught:fn(*args,**kwargs)
        return caught.exception

    def test_constants_and_all_nested_missing_keys_preserve_earlier_gates(self):
        self.assertEqual(details.CONTRACTS['paper-selection'],(set(prepare.PAPER_SELECTION_FIELDS),{'source_sha256','input_inventory'}))
        cases=[(self.selection,(),prepare.prepare,(self.source,),'local-selection'),
               (self.selection,('papers',0),prepare.prepare,(self.source,),'paper-selection'),
               (self.form,(),lambda x,*a,**k:recheck.audit(self.package,x,*a,**k),(self.source,),'source-selection'),
               (self.form,('sources',0),lambda x,*a,**k:recheck.audit(self.package,x,*a,**k),(self.source,),'source-selection-row')]
        for value,path,fn,args,contract in cases:
            for key in details.CONTRACTS[contract][0]:
                item=copy.deepcopy(value);target=item
                for part in path:target=target[part]
                del target[key]
                before=copy.deepcopy(item)
                with patch.object(prepare,'read_source_bytes',side_effect=AssertionError('read')),patch.object(recheck,'read_source_bytes',side_effect=AssertionError('read')):
                    old=self.error(fn,item,*args);new=self.error(fn,item,*args,rejection_label='selection')
                self.assertIs(type(old),ValueError);self.assertEqual(str(new),str(old));self.assertEqual(new.args,old.args)
                self.assertEqual(item,before)
                if hasattr(new,'detail'):
                    self.assertIn(details._key_diagnostic(key),new.detail)
                    self.assertTrue(new.detail.isascii());self.assertLessEqual(len(new.detail),512)
                elif contract.startswith('source-'):
                    self.fail('closed recheck missing key was not explained: '+key)
        bad=copy.deepcopy(self.selection);del bad['papers'][0]['authorized']
        exc=self.error(prepare.prepare,bad,self.source,rejection_label='selection')
        self.assertEqual(str(exc),'only author-matched authorized runtime training evidence is allowed')
        self.assertFalse(hasattr(exc,'detail'))

    def test_unknown_keys_only_count_at_each_level_and_type_schema_no_guess(self):
        for source,path,fn in [(self.selection,(),lambda x,**k:prepare.prepare(x,self.source,**k)),
                (self.selection,('papers',0),lambda x,**k:prepare.prepare(x,self.source,**k)),
                (self.form,(),lambda x,**k:recheck.audit(self.package,x,self.source,**k)),
                (self.form,('sources',0),lambda x,**k:recheck.audit(self.package,x,self.source,**k))]:
            x=copy.deepcopy(source);obj=x
            for part in path:obj=obj[part]
            obj['PRIVATE\x1b\nHOLDOUT/path']='PRIVATE-VALUE'
            exc=self.error(fn,x,rejection_label='selection')
            self.assertIn('unsupported_count=1',exc.detail);self.assertNotIn('PRIVATE',exc.detail);self.assertNotIn('HOLDOUT',exc.detail)
        for value in (None,[],{'schema':'wrong',**{k:v for k,v in self.form.items() if k!='schema'}}):
            exc=self.error(recheck.audit,self.package,value,self.source,rejection_label='selection')
            self.assertFalse(hasattr(exc,'detail'))
        bad=copy.deepcopy(self.form);bad['sources'][0]=[]
        self.assertFalse(hasattr(self.error(recheck.audit,self.package,bad,self.source,rejection_label='selection'),'detail'))

    def test_validation_and_reads_same_order_success_and_earlier_failure(self):
        for fn,owner,args,names in [(prepare.prepare,prepare,(self.selection,self.source),('runtime_papers','build','source_paths','read_source_bytes')),
                (prepare.report_defects,prepare,(self.selection,self.source),('runtime_papers','build','source_paths','read_source_bytes')),
                (recheck.audit,recheck,(self.package,self.form,self.source),('_sources','source_paths','read_source_bytes'))]:
            def observe(explain):
                events=[];originals={n:getattr(owner,n) for n in names};patches=[]
                for name in names:
                    def wrapper(*a,_name=name,**kw):
                        events.append(_name);return originals[_name](*a,**kw)
                    patches.append(patch.object(owner,name,side_effect=wrapper))
                try:
                    for p in patches:p.start()
                    value=fn(*args,**({'rejection_label':'selection'} if explain else {}))
                finally:
                    for p in reversed(patches):p.stop()
                return events,value
            self.assertEqual(observe(False),observe(True))
        bad=copy.deepcopy(self.form);bad['package_sha256']='0'*64
        with patch.object(recheck,'source_paths',side_effect=AssertionError('no paths')):
            self.assertFalse(hasattr(self.error(recheck.audit,self.package,bad,self.source,rejection_label='selection'),'detail'))

    def run_cli(self,args):
        return subprocess.run([sys.executable,*args],cwd=ROOT,capture_output=True,timeout=30)

    def test_native_error_bytes_dispatcher_and_no_output_on_rejection(self):
        with tempfile.TemporaryDirectory(prefix='source rejection space ') as td:
            d=Path(td).resolve();selection=d/'selection.json';package=d/'package.json';package.write_bytes(json.dumps(self.package).encode())
            for script,base,value,expected in [
                ('prepare_local_manifest.py',[str(selection),'--source-root',str(self.source)],dict(self.selection,PRIVATE='secret'),'selection uses the existing corpus identity and papers fields only'),
                ('source_recheck.py',[str(package),str(selection),'--source-root',str(self.source)],{},'source selection has missing or unsupported fields; cached reports are not source selections')]:
                selection.write_bytes(json.dumps(value).encode());output=d/'never.json'
                args=[script,*base,'--output',str(output)]
                default=self.run_cli(args);enabled=self.run_cli(args+['--explain-rejection'])
                self.assertEqual((default.returncode,default.stdout,default.stderr),(1,b'',(expected+os.linesep).encode()))
                self.assertEqual((enabled.returncode,enabled.stdout),(1,b''));self.assertTrue(enabled.stderr.startswith(default.stderr))
                self.assertEqual(len(enabled.stderr.splitlines()),2);self.assertNotIn(b'PRIVATE',enabled.stderr.splitlines()[1]);self.assertFalse(output.exists())
                dispatch=self.run_cli(['persona_cli.py','run',*args,'--explain-rejection'])
                self.assertEqual((dispatch.returncode,dispatch.stdout,dispatch.stderr),(enabled.returncode,enabled.stdout,enabled.stderr))

    def test_load_labels_and_cli_success_stale_and_usage(self):
        with tempfile.TemporaryDirectory(prefix='source input space ') as td:
            d=Path(td).resolve();p=d/'package.json';s=d/'selection.json';p.write_bytes(json.dumps(self.package).encode())
            for args,label in [(['prepare_local_manifest.py',str(s),'--source-root',str(self.source)],'selection'),
                    (['source_recheck.py',str(p),str(s),'--source-root',str(self.source)],'selection'),
                    (['source_recheck.py',str(s),'--template','--operator-id','synthetic'],'package')]:
                for raw in (b'null null',b'{"x":1,"x":2}',b'NaN'):
                    s.write_bytes(raw);a=self.run_cli(args);b=self.run_cli(args+['--explain-rejection'])
                    self.assertEqual((a.returncode,b.returncode,b.stdout),(1,1,b''))
                    self.assertEqual(b.stderr,a.stderr+('  input='+label+os.linesep).encode())
            for value,args in [(self.selection,['prepare_local_manifest.py',str(s),'--source-root',str(self.source)]),
                (self.selection,['prepare_local_manifest.py',str(s),'--source-root',str(self.source),'--report-defects']),
                (self.form,['source_recheck.py',str(p),str(s),'--source-root',str(self.source)]),
                (dict(self.form,package_sha256='0'*64),['source_recheck.py',str(p),str(s),'--source-root',str(self.source)])]:
                s.write_bytes(json.dumps(value).encode());a=self.run_cli(args);b=self.run_cli(args+['--explain-rejection'])
                self.assertEqual((a.returncode,a.stdout,a.stderr),(b.returncode,b.stdout,b.stderr))
        for script in ('prepare_local_manifest.py','source_recheck.py'):
            proc=self.run_cli([script,'--explain-rejection'])
            self.assertEqual((proc.returncode,proc.stdout),(2,b''));self.assertNotIn(b'  input=',proc.stderr)

    def test_exclusive_output_and_option_failures_remain_undecorated(self):
        with tempfile.TemporaryDirectory(prefix='source refusal space ') as td:
            d=Path(td).resolve();p=d/'package.json';s=d/'selection.json';out=d/'existing.json'
            p.write_bytes(json.dumps(self.package).encode());s.write_bytes(json.dumps(self.selection).encode());out.write_bytes(b'keep original')
            cases=[['prepare_local_manifest.py',str(s),'--source-root',str(self.source),'--output',str(out)],
                ['source_recheck.py',str(p),'--template','--operator-id','synthetic','--output',str(out)],
                ['source_recheck.py',str(p),'--template','--operator-id','synthetic','--source-root',str(self.source)],
                ['source_recheck.py',str(p)],
                ['source_recheck.py',str(d/'missing.json'),'--template','--operator-id','synthetic']]
            for args in cases:
                a=self.run_cli(args);b=self.run_cli(args+['--explain-rejection'])
                self.assertEqual((a.returncode,a.stdout,a.stderr),(b.returncode,b.stdout,b.stderr))
                self.assertEqual((a.returncode,a.stdout),(1,b''));self.assertNotIn(b'  input=',b.stderr)
            self.assertEqual(out.read_bytes(),b'keep original')

    def test_private_extra_key_cap_and_nonstring_api_keys(self):
        value={str(i)+'PRIVATE':None for i in range(10001)}
        exc=details.closed_rejection('old',value,'paper-selection','selection')
        self.assertIn('unsupported_count=9999+',exc.detail);self.assertIn('additional_missing=3',exc.detail)
        self.assertNotIn('PRIVATE',exc.detail);self.assertLessEqual(len(exc.detail),512)
        self.assertIs(type(details.closed_rejection('old',{1:None},'paper-selection','selection')),ValueError)

    def test_documented_prepare_manual_build_recheck_repair_flow(self):
        doc=(ROOT/'docs/SOURCE_REJECTION_DETAILS.md').read_bytes()
        blocks=re.findall(rb'```sh\n(.*?)```',doc,re.S);self.assertEqual(len(blocks),1)
        lines=blocks[0].decode().splitlines();self.assertEqual(len(lines),7)
        files=('selection.json','prepared.json','curated.json','package.json','template.json','bad-recheck.json','recheck-selection.json','report.json')
        scripts=('prepare_local_manifest.py','curate_local.py','corpus_files.py','source_recheck.py')
        examples=('examples/synthetic-sources','examples/manual-research-card.json')
        protected={p:p.read_bytes() for p in (ROOT/'examples/synthetic-sources').iterdir() if p.is_file()}
        protected[ROOT/'examples/manual-research-card.json']=(ROOT/'examples/manual-research-card.json').read_bytes()
        with tempfile.TemporaryDirectory(prefix='source guide space ') as td:
            d=Path(td).resolve();mapping={'OUTPUT/'+n:str(d/n) for n in files}
            mapping.update({n:str(ROOT/n) for n in examples})
            selected=copy.deepcopy(self.selection);del selected['papers'][0]['kind']
            (d/'selection.json').write_bytes(json.dumps(selected).encode())
            preserved={}
            for number,line in enumerate(lines):
                if number==1:(d/'selection.json').write_bytes(json.dumps(self.selection).encode())
                if number==5:
                    form=json.loads((d/'template.json').read_bytes());self.assertTrue(all(x['source_file'] is None for x in form['sources']))
                    del form['sources'][0]['source_file'];(d/'bad-recheck.json').write_bytes(json.dumps(form).encode())
                if number==6:
                    form=json.loads((d/'template.json').read_bytes())
                    for row in form['sources']:row['source_file']={'synthetic-0':'synthetic-0.md','synthetic-1':'synthetic-1.md'}[row['paper_id']]
                    (d/'recheck-selection.json').write_bytes(json.dumps(form).encode())
                tokens=shlex.split(line);self.assertEqual(tokens[0],'python');self.assertIn(tokens[1],scripts)
                self.assertFalse(any(x in ('>','|','&&') for x in tokens))
                args=[tokens[1],*[mapping.get(x,x) for x in tokens[2:]]]
                self.assertFalse(any('OUTPUT/' in x for x in args))
                proc=self.run_cli(args)
                self.assertEqual(proc.returncode,1 if number in (0,5) else 0,line)
                if number in (0,5):
                    self.assertEqual(proc.stdout,b'');self.assertEqual(len(proc.stderr.splitlines()),2)
                    self.assertFalse((d/('prepared.json' if number==0 else 'report.json')).exists())
                else:
                    self.assertEqual(proc.stderr,b'')
                    receipt=json.loads(proc.stdout);self.assertEqual(receipt['schema'],'persona.saved-output.v1')
                    self.assertEqual(receipt['status'],'SAVED');self.assertEqual(receipt['bytes'],Path(receipt['path']).stat().st_size)
                self.assertEqual(preserved,{p:p.read_bytes() for p in preserved})
                preserved={p:p.read_bytes() for p in d.iterdir() if p.name not in ('selection.json',)}
            report=json.loads((d/'report.json').read_bytes());self.assertFalse(report['package_modified']);self.assertFalse(report['automatic_approval'])
            self.assertEqual(report['checked_paper_count'],2);self.assertEqual(report['matched_quote_count'],2)
            self.assertTrue(report['papers_without_stored_quotes']);self.assertEqual(report['semantic_validation'],'NOT_PERFORMED')
            self.assertEqual(json.loads((d/'prepared.json').read_bytes())['papers'][0]['observations'],[])
            self.assertNotIn('evidence_verification',json.loads((d/'curated.json').read_bytes())['papers'][0]['observations'][0])
            for name in ('prepared.json','curated.json','package.json','template.json','report.json'):
                self.assertNotIn(b'\r',(d/name).read_bytes());self.assertTrue((d/name).read_bytes().endswith(b'\n'))
        self.assertEqual(protected,{p:p.read_bytes() for p in protected})

if __name__=='__main__':unittest.main()
