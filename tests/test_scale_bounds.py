"""Tiny deterministic capacity regressions; larger grids are opt-in only."""
import copy
import hashlib
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
import persona
import research_journey as journey
import research_workflow as rw
import review_package
from tests import capacity as c, scale_fixture as f

ROOT=Path(__file__).resolve().parents[1]


class ScaleBoundsTests(unittest.TestCase):
    def test_fixed_fixture_public_flow_and_declarations(self):
        a=f.build(2,2,3,2);b=f.build(2,2,3,2)
        self.assertEqual(c.encoded(a),c.encoded(b))
        self.assertEqual(len(a[0]['knowledge']['papers']),2)
        self.assertEqual(len(a[0]['persona']['rules']),4)
        decisions=a[6]['review']['decisions']
        self.assertEqual([d['decision'] for d in decisions],['accept','accept','reject'])
        self.assertEqual(len(a[5]['claims']),3)
        self.assertEqual(journey.inspect(*a)['status'],'HUMAN_REVIEW_REQUIRED_NOT_RESEARCH_APPROVAL')

    def test_exact_small_counts_and_bytes(self):
        result=c.observe(1,1,2,1)
        self.assertTrue(result['success'])
        expected=[(49,48,0,587,478125,11508),(32,32,0,406,297260,68856),
                  (51,51,0,634,449965,33871),(1,1,1,10,7480,1010)]
        for row,e in zip(result['stages'],expected):
            self.assertEqual(tuple(row['counts'][k] for k in ('build','validated_source_rules','apply','payload_sha256','hash_serialized_bytes'))+(row['output_bytes'],),e)
        self.assertFalse(result['computed_cli_combined_8mib_exceeded'])

    def test_observed_unobserved_bytes_semantics_and_inputs_identical(self):
        args=f.build(1,1,2,1);before=copy.deepcopy(args)
        operations=[('inspect',lambda:journey.inspect(*args),journey.encode_result),
                    ('render',lambda:journey.render(*args),lambda v:v.encode()),
                    ('review',lambda:review_package.render(args[0],f.QUESTION,f.TOPIC),lambda v:v.encode())]
        for name,fn,serialize in operations:
            plain=fn();raw=serialize(plain)
            row,observed=c.stage(name,fn,serialize)
            self.assertEqual(plain,observed);self.assertEqual(raw,serialize(observed))
            self.assertEqual(hashlib.sha256(raw).hexdigest(),row['output_sha256'])
        self.assertEqual(args,before)

    def test_alias_counter_not_stacked_and_restored(self):
        original=persona.payload_sha256;build=rw.build
        with c.counter() as count:
            persona.payload_sha256({'a':1});rw.payload_sha256({'a':1})
            self.assertEqual(count['payload_sha256'],2)
            self.assertEqual(count['hash_serialized_bytes'],14)
        self.assertIs(persona.payload_sha256,original);self.assertIs(rw.build,build)
        with self.assertRaises(RuntimeError):
            with c.counter():raise RuntimeError('synthetic')
        self.assertIs(persona.payload_sha256,original)

    def test_two_hashseeds_canonical_and_counts_not_raw_json_order(self):
        code='from tests.capacity import observe; import json; r=observe(1,1,2,1); [s.pop("seconds") for s in r["stages"]]; r["stages"][1].pop("output_sha256"); print(json.dumps(r,sort_keys=True))'
        results=[]
        for seed in ('1','73'):
            result=subprocess.run([sys.executable,'-c',code],cwd=ROOT,env=dict(os.environ,PYTHONHASHSEED=seed),capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr);results.append(json.loads(result.stdout))
        self.assertEqual(*results)

    def test_api_rejection_preserves_stages_and_no_success_marker(self):
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)/'failed'
            with patch.object(journey,'MAX_OUTPUT_BYTES',10):result=c.run([(1,1,1,1)],out)
            self.assertFalse(result['success']);self.assertFalse((out/'READY.json').exists())
            self.assertTrue((out/'FAILED.json').exists())
            row=json.loads((out/'case-001.json').read_bytes())
            self.assertTrue(row['stages'][0]['success'])
            self.assertFalse(row['stages'][1]['success'])
            self.assertIn('16 MiB',row['stages'][1]['reason'])
            self.assertTrue(row['stages'][3]['success'])

    def test_fixture_rejection_and_runner_bounds(self):
        for values in ((0,1,1,1),(33,1,1,1),(1,1,1,2),(True,1,1,1)):
            with self.assertRaises(ValueError):f.build(*values)
        with patch.object(f,'build',side_effect=ValueError('synthetic fixture rejection')):
            result=c.observe(1,1,1,1)
        self.assertFalse(result['success']);self.assertEqual(len(result['stages']),1)

    def test_exclusive_paths_and_partial_marker(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);out=root/'success';c.run([(1,1,1,1)],out)
            with self.assertRaises(ValueError):c.run([(1,1,1,1)],out)
            with self.assertRaises(ValueError):c.run([(1,1,1,1)],ROOT/'never-capacity')
            real=Path.open;partial=root/'partial'
            def opened(path,*args,**kwargs):
                if path.name=='READY.json':raise OSError('synthetic write failure')
                return real(path,*args,**kwargs)
            with patch.object(Path,'open',opened),self.assertRaises(OSError):c.run([(1,1,1,1)],partial)
            self.assertTrue((partial/'case-001.json').exists());self.assertFalse((partial/'READY.json').exists())

    def test_unexpected_stage_failure_keeps_counts_and_restores(self):
        original=rw.build
        def fail():
            persona.payload_sha256({'a':1})
            raise RuntimeError('PRIVATE_DIAGNOSTIC')
        row,value=c.stage('synthetic',fail,c.encoded)
        self.assertFalse(row['success']);self.assertEqual(row['counts']['payload_sha256'],1)
        self.assertNotIn('PRIVATE',json.dumps(row));self.assertIs(rw.build,original)

    def test_partial_ready_is_retained_not_success(self):
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)/'partial';real=Path.open
            class Short:
                def __enter__(self):return self
                def __exit__(self,*args):return False
                def write(self,raw):
                    with real(out/'READY.json','xb') as stream:stream.write(raw[:7])
                    return 7
            def opened(path,*args,**kwargs):
                return Short() if path.name=='READY.json' else real(path,*args,**kwargs)
            with patch.object(Path,'open',opened),self.assertRaises(OSError):c.run([(1,1,1,1)],out)
            self.assertTrue((out/'case-001.json').exists())
            self.assertEqual(len((out/'READY.json').read_bytes()),7)

    def test_guide_executes_native_path_after_shlex(self):
        guide=(ROOT/'docs/CAPACITY.md').read_text()
        blocks=re.findall(r'```sh\n(.*?)```',guide,re.S);self.assertEqual(len(blocks),1)
        with tempfile.TemporaryDirectory(prefix='capacity space ') as temp:
            for line in blocks[0].splitlines():
                if not line.strip():continue
                args=shlex.split(line);self.assertEqual(args[:3],['python','-m','tests.capacity'])
                self.assertNotIn('>',args)
                args=[sys.executable,*[a.replace('OUTPUT',temp) for a in args[1:]]]
                result=subprocess.run(args,cwd=ROOT,capture_output=True)
                self.assertEqual(result.returncode,0,result.stderr)
            self.assertTrue((Path(temp)/'capacity'/'READY.json').exists())


if __name__=='__main__':unittest.main()
