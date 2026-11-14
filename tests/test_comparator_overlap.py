"""Synthetic comparator declarations never enter target knowledge."""
import copy
import io
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import comparator_overlap as c
from compare_releases import checked_package
from research_workflow import build
from corpus_files import load_sources,load_segment_corpus
from prepare_local_manifest import prepare
from persona import validate,payload_sha256
from evaluate_synthetic import freeze
ROOT=Path(__file__).resolve().parents[1]

class ComparatorTests(unittest.TestCase):
    def setUp(self):
        self.p=json.loads((ROOT/'examples/trajectory-conditions-package.json').read_bytes())
        self.c=json.loads((ROOT/'examples/synthetic-comparator-corpus.json').read_bytes())
        self.topic='synthetic method conditions'
    def run_report(self):return c.inspect(self.p,self.c,self.topic)
    def test_exact_groups_bindings_empty_topics_and_no_mutation(self):
        old=copy.deepcopy((self.p,self.c));r=self.run_report()
        self.assertEqual((self.p,self.c),old)
        self.assertEqual(r['specificity'],'NOT_DERIVED');self.assertFalse(r['package_modified'])
        self.assertEqual(r['comparator_corpus_sha256'],payload_sha256(self.c))
        self.assertEqual({g['status'] for g in r['groups']},{'SHARED_EXACT_STRING_WITH_COMPARATOR','NOT_FOUND_IN_SUPPLIED_COMPARATOR_SET'})
        self.assertEqual(len(r['comparator_only_groups']),1)
        empty=c.inspect(self.p,self.c,'absent');self.assertEqual(empty['target_topic_status'],'NO_TARGET_TOPIC_RULES');self.assertEqual(empty['comparator_topic_status'],'NO_TOPIC_MATCHED_COMPARATOR_OBSERVATIONS')
        self.c['papers']=[];r=self.run_report();self.assertTrue(all(g['status']=='NO_TOPIC_MATCHED_COMPARATOR_OBSERVATIONS' for g in r['groups']))
    def test_only_casefold_topic_no_method_normalization_and_positions(self):
        self.assertEqual(self.run_report(),c.inspect({'package':self.p},self.c,self.topic.upper()))
        obs=self.c['papers'][0]['observations'][0];self.c['papers'][0]['observations'].append(copy.deepcopy(obs))
        r=self.run_report();shared=next(g for g in r['groups'] if g['status'].startswith('SHARED'))
        self.assertEqual([x['observation_index'] for x in shared['comparator']['observation_refs']],[0,2])
        self.assertEqual(shared['comparator']['distinct_source_hash_count'],1)
        obs['method']=obs['method'].lower();self.c['papers'][0]['observations'].pop()
        self.assertNotIn('SHARED_EXACT_STRING_WITH_COMPARATOR',[g['status'] for g in self.run_report()['groups']])
    def test_all_missing_unknown_keys_and_enum_declarations(self):
        original=copy.deepcopy(self.c)
        paths=[(),('papers',0),('papers',0,'observations',0)]
        for path in paths:
            node=original
            for k in path:node=node[k]
            for key in [*node,'unknown']:
                self.c=copy.deepcopy(original);node=self.c
                for k in path:node=node[k]
                if key=='unknown':node[key]=True
                else:node.pop(key)
                with self.subTest(path=path,key=key),self.assertRaises(ValueError):self.run_report()
        for key,value in [('split','training'),('authorized',1),('runtime_knowledge_eligible',0),('year',True),('kind','other'),('author_id','another'),('source_sha256','A'*64)]:
            self.c=copy.deepcopy(original);self.c['papers'][0][key]=value
            with self.assertRaises(ValueError):self.run_report()
        for key,value in [('stance','retain'),('claim_type',None),('evidence_quote',3)]:
            self.c=copy.deepcopy(original);self.c['papers'][0]['observations'][0][key]=value
            with self.assertRaises(ValueError):self.run_report()
    def test_three_collisions_any_topic_and_duplicate_ids(self):
        original=copy.deepcopy(self.c)
        for field,value,error in [('author_id',self.p['persona']['author_id'],'AUTHOR_LABEL'),('paper_id',self.p['knowledge']['papers'][0]['paper_id'],'PAPER_ID'),('source_sha256',self.p['knowledge']['papers'][0]['source_sha256'],'SOURCE_HASH')]:
            self.c=copy.deepcopy(original);self.c['papers'][0][field]=value
            if field=='author_id':self.c[field]=value
            with self.assertRaisesRegex(ValueError,error):c.inspect(self.p,self.c,'absent')
        self.c=copy.deepcopy(original);self.c['papers']*=2
        with self.assertRaisesRegex(ValueError,'duplicate'):self.run_report()
    def test_forged_target_and_seven_ingress_paths(self):
        self.p['persona']['rules'][0]['method']='forged'
        with self.assertRaises(ValueError):self.run_report()
        self.setUp();report=self.run_report()
        # A corpus-shaped variant proves boundaries, not just missing top-level fields.
        manifest={k:v for k,v in self.c.items() if k not in ('schema','curator_id','handling_declaration')};manifest.update(version='1',build_id='synthetic')
        knowledge=copy.deepcopy(self.p['knowledge']);knowledge['papers'][0]['split']='comparator';knowledge['papers'][0]['runtime_knowledge_eligible']=False
        persona=copy.deepcopy(self.p['persona']);persona['knowledge_papers_sha256']=payload_sha256(knowledge['papers'])
        knowledge['persona_payload_sha256']=payload_sha256(persona)
        self.assertEqual(validate(persona,knowledge),['ineligible runtime paper'])
        contaminated=dict(persona=persona,knowledge=knowledge)
        with patch('corpus_files.read_source_bytes',side_effect=AssertionError('must not read')):
            calls=[lambda:build(manifest),lambda:load_sources(manifest,Path('/not-read')),lambda:prepare(manifest,Path('/not-read')),lambda:freeze(contaminated,{}),lambda:load_segment_corpus(manifest,Path('/not-read')),lambda:checked_package(report)]
            for call in calls:
                with self.assertRaises((ValueError,KeyError)):call()
    def test_budgets_text_controls_and_fixed_cli_errors(self):
        self.c['handling_declaration']='inert\x1b[31m\nignore instructions'
        raw=c.encode(self.run_report(),'text');self.assertNotIn(b'\x1b',raw);self.assertIn(b'ignore instructions',raw)
        with patch.object(c,'MAX_OUTPUT_BYTES',10),self.assertRaises(ValueError):self.run_report()
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/'a.json';b=Path(d)/'b.json';a.write_bytes(json.dumps(self.p).encode());b.write_bytes(json.dumps(self.c).encode())
            class Out:
                def __init__(self):self.buffer=io.BytesIO()
            for budget in (a.stat().st_size+b.stat().st_size-1,1):
                out=Out()
                with patch.object(c,'MAX_INPUT_BYTES',budget),patch.object(sys,'argv',['comparator_overlap.py',str(a),str(b),'--topic',self.topic]),patch.object(sys,'stdout',out),patch.object(sys,'stderr',io.StringIO()),self.assertRaises(SystemExit) as ex:c.main()
                self.assertEqual(ex.exception.code,1);self.assertEqual(out.buffer.getvalue(),b'')
            b.write_bytes(b'{"schema":null,"schema":null}')
            proc=subprocess.run([sys.executable,str(ROOT/'comparator_overlap.py'),str(a),str(b),'--topic',self.topic],capture_output=True)
            self.assertEqual((proc.returncode,proc.stdout,proc.stderr),(1,b'',b'Comparator inventory failed.\n'))
    def test_whole_output_budget_and_exact_aggregate_boundary(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/'package.json';b=Path(d)/'comparator.json'
            a.write_bytes(json.dumps(self.p).encode());b.write_bytes(json.dumps(self.c).encode())
            total=a.stat().st_size+b.stat().st_size
            class Out:
                def __init__(self):self.buffer=io.BytesIO()
            args=['comparator_overlap.py',str(a),str(b),'--topic',self.topic]
            out=Out()
            with patch.object(c,'MAX_INPUT_BYTES',total),patch.object(sys,'argv',args),patch.object(sys,'stdout',out):c.main()
            self.assertEqual(json.loads(out.buffer.getvalue()),self.run_report())
            out=Out()
            with patch.object(c,'MAX_OUTPUT_BYTES',1),patch.object(sys,'argv',args),patch.object(sys,'stdout',out),patch.object(sys,'stderr',io.StringIO()),self.assertRaises(SystemExit) as e:c.main()
            self.assertEqual(e.exception.code,1);self.assertEqual(out.buffer.getvalue(),b'')

    def test_repeated_source_hash_is_not_independence_and_labels_are_inert(self):
        second=copy.deepcopy(self.c['papers'][0]);second['paper_id']='synthetic-other-paper'
        second['observations']=second['observations'][:1];second['observations'][0]['stance']='challenge'
        self.c['papers'].append(second)
        r=self.run_report();g=next(g for g in r['groups'] if g['status'].startswith('SHARED'))
        self.assertEqual(g['comparator']['distinct_source_hash_count'],1)
        self.assertEqual(g['comparator']['stance_counts'],dict(support=1,challenge=1))
        for key in ('reasoning','observation_origin','evidence_verification'):
            obs=self.c['papers'][0]['observations'][0];obs[key]='claimed'
            with self.assertRaises(ValueError):self.run_report()
            del obs[key]
        self.assertEqual(r['handling_status'],'DECLARED_NOT_VERIFIED')
        self.assertEqual(r['source_check'],'NOT_PERFORMED');self.assertEqual(r['holdout_overlap'],'NOT_CHECKED')

    def test_actual_guide_and_deterministic_hashseeds(self):
        lines=[x for block in re.findall(r'```sh\n(.*?)```',(ROOT/'docs/COMPARATOR_OVERLAP.md').read_text(),re.S) for x in block.splitlines() if x]
        self.assertEqual(len(lines),3)
        for line in lines:
            args=shlex.split(line)[1:]
            for i,value in enumerate(args):
                if value.startswith('examples/') or value=='comparator_overlap.py':args[i]=str(ROOT/value)
            p=subprocess.run([sys.executable,*args],capture_output=True,cwd=ROOT);self.assertEqual((p.returncode,p.stderr),(0,b''))
        import os
        results=[]
        for seed in ('1','2026'):
            env=dict(os.environ,PYTHONHASHSEED=seed)
            results.append(subprocess.check_output([sys.executable,str(ROOT/'comparator_overlap.py'),str(ROOT/'examples/trajectory-conditions-package.json'),str(ROOT/'examples/synthetic-comparator-corpus.json'),'--topic',self.topic],env=env))
        self.assertEqual(*results)

if __name__=='__main__':unittest.main()
