"""External context stays separate through explicit v2 cards and fresh comparisons."""
import copy
import json
import html
import io
from contextlib import redirect_stderr
import stat
from types import SimpleNamespace
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import journey_inputs as cards
import research_journey as journey
import journey_compare as compare
import journey_html
import external_evidence as external
from persona import payload_sha256
from tests import test_research_journey as fixture
from tests.test_journey_html import Document

ROOT=Path(__file__).resolve().parents[1]

class ExternalJourneyTests(unittest.TestCase):
    def setUp(self):
        self.case=fixture.ResearchJourneyTests();self.case.setUp();self.args=self.case.args()
        self.sidecar=external.template(self.args[0],self.args[5],'synthetic-external-operator')
        self.sidecar['items']=[dict(external_id='external-1',kind='other',identifier_text='invented-external-only',year=None,other_package_identity=None,relates_to_claim_ids=['claim'],role='EXTERNAL_CONTEXT_ONLY',rationale='Synthetic private context',uncertainty='Synthetic uncertainty not resolved')]
        self.tmp=tempfile.TemporaryDirectory(prefix='external journey 공백 ');self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve();self.selection=cards.template(include_external=True);self.selection['pattern_id']=self.args[8]
        for name,value in zip(cards.REQUIRED,self.args[:8]):self.write(name,value)
        self.write('declared_review',self.args[9]);self.write('external',self.sidecar)
    def write(self,name,value):
        path='합성 '+name+'.json';self.selection['artifacts'][name]=path
        (self.root/path).write_bytes((json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    def prepare(self):return cards.prepare(self.selection,self.root)
    def v1(self):
        selection=copy.deepcopy(self.selection);selection['schema']=cards.SELECTION_SCHEMA;selection['artifacts'].pop('external')
        return cards.prepare(selection,self.root)
    def test_explicit_versions_and_strict_slots(self):
        self.assertEqual(cards.template()['schema'],cards.SELECTION_SCHEMA);self.assertEqual(len(cards.template()['artifacts']),11)
        self.assertEqual(self.selection['schema'],cards.SELECTION_SCHEMA_V2);self.assertEqual(self.prepare()['schema'],cards.CARD_SCHEMA_V2)
        for version in ('v1','v2'):
            x=copy.deepcopy(self.selection)
            if version=='v1':x['schema']=cards.SELECTION_SCHEMA;x['artifacts']['external']=None
            else:x['artifacts'].pop('external')
            with self.assertRaises(ValueError):cards.prepare(x,self.root)
        x=copy.deepcopy(self.selection);x['artifacts']['PRIVATE_UNKNOWN']='private.json'
        with self.assertRaises(ValueError):cards.prepare(x,self.root)
    def test_exact_review_and_no_core_evidence_or_decision_change(self):
        old=journey.inspect(*self.args);new=journey.inspect(*self.args,external=self.sidecar)
        self.assertEqual(new['external_evidence_review'],external.review(self.args[0],self.args[5],self.sidecar,self.args[9]))
        for key in old:
            if key not in ('bindings','journey_input_sha256','review_agenda'):self.assertEqual(new[key],old[key],key)
        self.assertEqual([r for r in new['review_agenda'] if r['domain']!='external_evidence'],old['review_agenda'])
        self.assertEqual(new['bindings']['external_sha256'],payload_sha256(self.sidecar))
        self.assertNotEqual(new['journey_input_sha256'],old['journey_input_sha256'])
        self.assertEqual(new['evidence_routes'],old['evidence_routes'])
        with patch.object(external,'review',wraps=external.review) as review:
            journey.inspect(*self.args,external=self.sidecar);self.assertEqual(review.call_count,1)
    def test_move_and_fresh_reopen_without_root_authority(self):
        card=self.prepare();old=cards.inspect(card,self.root)
        with tempfile.TemporaryDirectory(prefix='moved 공백 ') as temp:
            destination=Path(temp)/'copied';shutil.copytree(self.root,destination)
            self.assertEqual(cards.inspect(card,destination),old)
            self.assertNotIn(str(self.root),json.dumps(card));self.assertNotIn(str(destination),json.dumps(card))
            changed=destination/self.selection['artifacts']['external'];changed.write_bytes(changed.read_bytes()+b' ')
            with self.assertRaises(ValueError):cards.inspect(card,destination)
    def test_null_file_vs_explicit_absent_and_duplicate_paths(self):
        x=copy.deepcopy(self.selection);x['artifacts']['external']=None;card=cards.prepare(x,self.root)
        self.assertNotIn('external_evidence_review',cards.inspect(card,self.root))
        self.write('external',None)
        with self.assertRaises(ValueError):self.prepare()
        self.write('external',self.sidecar);self.write('declared_review',None)
        with self.assertRaises(ValueError):self.prepare()
        x['artifacts']['external']=x['artifacts']['package']
        with self.assertRaises(ValueError):cards.prepare(x,self.root)
    def test_stale_bindings_types_and_private_values(self):
        for key in ('persona_sha256','knowledge_papers_sha256','draft_sha256'):
            v=copy.deepcopy(self.sidecar);v[key]='0'*64
            with self.assertRaises(ValueError):journey.inspect(*self.args,external=v)
        for v in (False,[],{'PRIVATE_UNKNOWN':'PRIVATE_VALUE'}):
            with self.assertRaises(ValueError) as error:journey.inspect(*self.args,external=v)
            self.assertNotIn('PRIVATE',str(error.exception))
        v=copy.deepcopy(self.args);v[-1]['draft_sha256']='0'*64
        with self.assertRaises(ValueError):journey.inspect(*v,external=self.sidecar)
        v=copy.deepcopy(self.args);v[5]['claims'][0]['text']='changed draft'
        with self.assertRaises(ValueError):journey.inspect(*v,external=self.sidecar)
    def test_v1_v2_null_and_add_change_remove_comparisons(self):
        v1=self.v1();v2=self.prepare();result=compare.compare(v1,self.root,v2,self.root)
        self.assertEqual(result['external_slot_comparison']['previous'],'NOT_SUPPORTED_BY_CARD_VERSION')
        self.assertEqual(result['external_slot_comparison']['current'],'SUPPLIED')
        group=next(g for g in result['declared_record_comparison'] if g['group']=='external_items')
        self.assertEqual(group['records'][0]['status'],'ONLY_CURRENT_DECLARATION')
        selection=copy.deepcopy(self.selection);selection['artifacts']['external']=None;empty=cards.prepare(selection,self.root)
        mixed=compare.compare(v1,self.root,empty,self.root)
        self.assertEqual(mixed['external_slot_comparison']['current'],'NOT_SUPPLIED')
        removed=compare.compare(v2,self.root,empty,self.root)
        group=next(g for g in removed['declared_record_comparison'] if g['group']=='external_items')
        self.assertEqual(group['records'][0]['status'],'ONLY_PREVIOUS_DECLARATION')
        self.assertNotIn('external_slot_comparison',compare.compare(v1,self.root,v1,self.root))
        with tempfile.TemporaryDirectory() as temp:
            other=Path(temp)/'copy';shutil.copytree(self.root,other)
            value=copy.deepcopy(self.sidecar);value['items'][0]['rationale']='Different declared text'
            (other/self.selection['artifacts']['external']).write_bytes(json.dumps(value).encode('utf-8'))
            current=cards.prepare(self.selection,other);result=compare.compare(v2,self.root,current,other)
            group=next(g for g in result['declared_record_comparison'] if g['group']=='external_items')
            self.assertEqual(group['records'][0]['changed_fields'],['rationale'])
            self.assertTrue(all(r['status']=='UNCHANGED_AT_EXACT_REFERENCE' for r in result['exact_reference_comparison']))
    def test_card_tamper_and_aggregate_limits(self):
        card=self.prepare();changed=copy.deepcopy(card);changed['artifacts']['external']['json_sha256']='0'*64
        with self.assertRaises(ValueError):cards.inspect(changed,self.root)
        changed=copy.deepcopy(card);changed['artifacts']['external']['raw_sha256']='0'*64
        with self.assertRaises(ValueError):cards.inspect(changed,self.root)
        total=sum(v['bytes'] for v in card['artifacts'].values() if v)
        with patch.object(cards,'MAX_ARTIFACT_BYTES',total-1):
            with self.assertRaises(ValueError):self.prepare()
        with patch.object(journey,'MAX_INPUT_BYTES',1):
            with self.assertRaises(ValueError):journey.inspect(*self.args,external=self.sidecar)
        with patch.object(journey,'MAX_OUTPUT_BYTES',1):
            with self.assertRaises(ValueError):journey.inspect(*self.args,external=self.sidecar)
    def test_external_path_symlink_and_reparse(self):
        path=self.root/self.selection['artifacts']['external'];target=self.root/'target.json';path.rename(target)
        try:path.symlink_to(target)
        except (OSError,NotImplementedError):self.skipTest('symlink creation not available')
        with self.assertRaises(ValueError):self.prepare()
    def test_html_snapshot_passive_and_comparison_separate(self):
        v=copy.deepcopy(self.sidecar);v['items'][0]['rationale']='<script>PRIVATE()</script> https://example.invalid/ 한국어'
        self.write('external',v);card=self.prepare();text=cards.render(card,self.root,format='html');doc=Document(text)
        self.assertEqual(json.loads(doc.saved['complete-json']),cards.inspect(card,self.root));self.assertNotIn('<script>',text)
        self.assertEqual(len(doc.ids),len(set(doc.ids)));self.assertNotIn('script',doc.tags)
        self.assertIn('External evidence (not persona knowledge)',text)
        compared=compare.render(self.v1(),self.root,card,self.root,format='html');doc=Document(compared)
        self.assertEqual(json.loads(html.unescape(re.search(r'<pre id="json-snapshot">(.*?)</pre>',compared,re.S).group(1))),compare.compare(self.v1(),self.root,card,self.root))
        self.assertIn('external-context',doc.ids);self.assertEqual(len(doc.ids),len(set(doc.ids)));self.assertNotIn('script',doc.tags)
        self.assertTrue(all(href.startswith('#') for href in doc.hrefs))
    def test_cli_template_and_card_roundtrip(self):
        def run(script,*args):return subprocess.run([sys.executable,str(ROOT/script),*map(str,args)],capture_output=True)
        default=run('journey_inputs.py','template');new=run('journey_inputs.py','template','--include-external')
        self.assertEqual(json.loads(default.stdout),cards.template());self.assertEqual(json.loads(new.stdout),cards.template(include_external=True))
        selection=self.root/'selection.json';selection.write_bytes(json.dumps(self.selection).encode('utf-8'));output=self.root/'card.json'
        result=run('journey_inputs.py','prepare',selection,'--input-root',self.root,'--output',output);self.assertEqual(result.returncode,0,result.stderr)
        for fmt in ('json','text','html'):
            result=run('journey_inputs.py','inspect',output,'--input-root',self.root,'--format',fmt);self.assertEqual(result.returncode,0,result.stderr)
        self.assertNotEqual(run('journey_inputs.py','prepare',selection,'--input-root',self.root,'--output',output).returncode,0)
    def test_empty_items_unlinked_context_and_freeze_unchanged(self):
        from evaluate_synthetic import freeze
        before=freeze(self.args[0],self.args[5]);original=copy.deepcopy(self.args)
        empty=copy.deepcopy(self.sidecar);empty['items']=[]
        result=journey.inspect(*self.args,external=empty)
        self.assertEqual(result['external_evidence_review']['status'],'NO_EXTERNAL_ITEMS')
        self.assertFalse(any(row['domain']=='external_evidence' for row in result['review_agenda']))
        value=copy.deepcopy(self.sidecar);value['items'][0]['relates_to_claim_ids']=[]
        result=journey.inspect(*self.args,external=value)
        self.assertEqual(result['external_evidence_review']['items'][0]['relates_to_claim_ids'],[])
        self.assertEqual(freeze(self.args[0],self.args[5]),before);self.assertEqual(self.args,original)
    def test_direct_cli_external_and_explicit_null_errors(self):
        arguments=[str(self.root/self.selection['artifacts'][name]) for name in cards.REQUIRED]
        review=self.root/self.selection['artifacts']['declared_review'];sidecar=self.root/self.selection['artifacts']['external']
        base=[sys.executable,str(ROOT/'research_journey.py'),*arguments,'--pattern-id',self.args[8],'--review',str(review),'--external',str(sidecar)]
        for format in ('json','text','html'):
            run=subprocess.run([*base,'--format',format],capture_output=True);self.assertEqual(run.returncode,0,run.stderr)
        for raw in (b'null',b'{"PRIVATE_UNKNOWN":"PRIVATE_VALUE"}'):
            sidecar.write_bytes(raw);out=self.root/'never.json';run=subprocess.run([*base,'--output',str(out)],capture_output=True)
            self.assertEqual(run.returncode,1);self.assertEqual(run.stdout,b'');self.assertFalse(out.exists());self.assertNotIn(b'PRIVATE',run.stderr);self.assertNotIn(b'Traceback',run.stderr)
        self.write('external',self.sidecar);review.write_bytes(b'null')
        run=subprocess.run(base,capture_output=True);self.assertEqual(run.returncode,1);self.assertEqual(run.stdout,b'')
    def test_external_reparse_attribute_preflight_no_reads(self):
        target=(self.root/self.selection['artifacts']['external']).resolve();original=Path.stat
        def stat_value(path,*args,**kwargs):
            value=original(path,*args,**kwargs)
            if path==target and kwargs.get('follow_symlinks') is False:
                return SimpleNamespace(st_mode=value.st_mode,st_file_attributes=getattr(value,'st_file_attributes',0)|getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',0x400))
            return value
        with patch.object(Path,'stat',stat_value),patch.object(cards,'read_source_bytes',side_effect=AssertionError('no bytes before path preflight')):
            with self.assertRaises(ValueError):self.prepare()
    def test_source_and_method_options_stay_separate(self):
        import source_recheck
        import method_application
        sources=source_recheck.template(self.args[0],'synthetic-source')
        for row in sources['sources']:row['source_file']=row['paper_id']+'.md'
        self.write('source_selection',sources)
        applications=method_application.template(*self.args[:5],self.args[8],'synthetic-application')
        self.write('method_applications',applications)
        root=ROOT/'examples/synthetic-sources'
        card=cards.prepare(self.selection,self.root,source_root=root)
        report=cards.inspect(card,self.root,source_root=root)
        base=journey.inspect(*self.args,source_selection=sources,source_root=root,method_applications=applications)
        self.assertEqual(report['evidence_routes'],base['evidence_routes'])
        self.assertEqual(report['source_recheck'],base['source_recheck'])
        self.assertEqual(report['method_application_review'],base['method_application_review'])
        invalid=copy.deepcopy(self.sidecar);invalid['draft_sha256']='0'*64
        with patch.object(source_recheck,'audit',side_effect=AssertionError('invalid sidecar before source bytes')):
            with self.assertRaises(ValueError):journey.inspect(*self.args,source_selection=sources,source_root=root,external=invalid)
        with patch.object(cards,'read_source_bytes',side_effect=AssertionError('source root pairing before artifacts')):
            with self.assertRaises(ValueError):self.prepare()
    def test_direct_raw_input_budget_no_result(self):
        import human_validation
        paths=[self.root/self.selection['artifacts'][name] for name in cards.REQUIRED]
        review=self.root/self.selection['artifacts']['declared_review'];sidecar=self.root/self.selection['artifacts']['external']
        limit=sum(p.stat().st_size for p in [*paths,review,sidecar])-1
        argv=['research_journey.py',*map(str,paths),'--pattern-id',self.args[8],'--review',str(review),'--external',str(sidecar)]
        capture=io.BytesIO();stdout=io.TextIOWrapper(capture,encoding='utf-8')
        with patch.object(human_validation,'MAX_INPUT_BYTES',limit),patch.object(sys,'argv',argv),patch.object(sys,'stdout',stdout),redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as failure:journey.main()
            stdout.flush();self.assertEqual(capture.getvalue(),b'')
        self.assertEqual(failure.exception.code,1)
    def test_guide(self):
        guide=(ROOT/'docs/EXTERNAL_JOURNEY.md').read_text(encoding='utf-8');blocks=re.findall(r'```python\n(.*?)\n```',guide,re.S);self.assertEqual(len(blocks),1)
        old=Path.cwd()
        try:os.chdir(ROOT);exec(compile(blocks[0],'external-journey-guide','exec'),{})
        finally:os.chdir(old)
