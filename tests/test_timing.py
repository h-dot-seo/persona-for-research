"""Timing observer regression tests use tiny synthetic suites, never full recursive discovery."""
import contextlib
import copy
import io
import json
import os
import re
import shlex
from pathlib import Path
import subprocess
import sys
import types
import unittest
from unittest.mock import patch
from tests import timing as t


class TimingTests(unittest.TestCase):
    def load(self, case):
        class Loader:
            def loadTestsFromName(self, name):return unittest.defaultTestLoader.loadTestsFromTestCase(case)
        return Loader()

    def test_outcomes_and_no_diagnostics(self):
        class Synthetic(unittest.TestCase):
            def test_ok(self):
                print('PRIVATE');sys.stdout.buffer.write(b'PRIVATE_BUFFER');os.write(1,b'PRIVATE_FD')
            def test_fail(self):self.fail('PRIVATE_FAILURE')
            def test_error(self):raise RuntimeError('PRIVATE_ERROR')
            @unittest.skip('PRIVATE_SKIP')
            def test_skip(self):pass
            @unittest.expectedFailure
            def test_expected(self):self.fail('PRIVATE_EXPECTED')
            @unittest.expectedFailure
            def test_unexpected(self):pass
        receipt=t.observe(['tests.test_timing'],self.load(Synthetic))
        self.assertEqual({k:receipt['total'][k] for k in t.COUNTS},dict(tests=6,failures=1,errors=1,skipped=1,expected_failures=1,unexpected_successes=1))
        self.assertNotIn('PRIVATE',json.dumps(receipt));self.assertFalse(receipt['success'])
        self.assertTrue(t.valid(receipt,['tests.test_timing'],1))

    def test_fake_clock_fixture_lifetime_and_order(self):
        events=[];module=types.ModuleType('tests.synthetic_timing')
        module.setUpModule=lambda:events.append('module start')
        module.tearDownModule=lambda:events.append('module end')
        class Synthetic(unittest.TestCase):
            @classmethod
            def setUpClass(cls):events.append('class start')
            @classmethod
            def tearDownClass(cls):events.append('class end')
            def test_a(self):events.append('a')
            def test_b(self):events.append('b')
        Synthetic.__module__=module.__name__
        ticks=iter(range(20))
        with patch.dict(sys.modules,{module.__name__:module}):
            receipt=t.observe(['tests.test_timing'],self.load(Synthetic),lambda:next(ticks))
        self.assertEqual(events,['module start','class start','a','b','class end','module end'])
        self.assertEqual([r['seconds'] for r in receipt['modules'][0]['test_times']],[1,1])
        self.assertEqual(receipt['modules'][0]['seconds'],5)
        self.assertEqual(receipt['total']['seconds'],7)

    def test_partial_restores_subprocess_and_streams(self):
        original=subprocess.run;out=sys.stdout;err=sys.stderr
        class Loader:
            def loadTestsFromName(self,name):raise KeyboardInterrupt('PRIVATE')
        receipt=t.observe(['tests.test_timing','tests.test_skill_contract'],Loader())
        self.assertIs(subprocess.run,original);self.assertIs(sys.stdout,out);self.assertIs(sys.stderr,err)
        self.assertFalse(receipt['complete']);self.assertFalse(receipt['success'])
        self.assertTrue(t.valid(receipt,['tests.test_timing','tests.test_skill_contract'],1))

    def test_stopped_suite_is_partial_not_success(self):
        class Stopped:
            def run(self,result):result.stop()
        class Loader:
            def loadTestsFromName(self,name):return Stopped()
        receipt=t.observe(['tests.test_timing'],Loader())
        self.assertFalse(receipt['complete']);self.assertFalse(receipt['success'])
        self.assertTrue(t.valid(receipt,['tests.test_timing'],1))

    def test_observed_stage_counts_and_fixed_labels(self):
        class Synthetic(unittest.TestCase):
            def test_call(self):
                subprocess.run([sys.executable,'-c','print("PRIVATE_CHILD")'],check=True)
        receipt=t.observe(['tests.test_timing'],self.load(Synthetic))
        stage=receipt['modules'][0]['stages']['OTHER']
        self.assertEqual((stage['calls'],stage['completed']),(1,1))
        self.assertNotIn('PRIVATE',json.dumps(receipt));self.assertNotIn(sys.executable,json.dumps(receipt))
        self.assertEqual(t.stage_name(['python',r'C:\private\research_journey.py']),'research_journey.py')
        self.assertEqual(t.stage_name('SECRET COMMAND'),'OTHER')

    def test_existing_mock_preserved_and_bypass_documented(self):
        class Synthetic(unittest.TestCase):
            def test_mock(self):
                with patch.object(subprocess,'run',return_value=None):subprocess.run(['secret'])
        receipt=t.observe(['tests.test_timing'],self.load(Synthetic))
        self.assertEqual(sum(v['calls'] for v in receipt['modules'][0]['stages'].values()),0)
        self.assertIn('replacement mocks may bypass',receipt['boundary'])

    def test_allowlist_rejects_external_duplicate_and_unknown(self):
        for names in (['/private/test.py'],['tests.test_skill_contract']*2,['tests.not_published']):
            with self.assertRaises(ValueError):t.select_modules(names)
        self.assertEqual(t.select_modules(['tests.test_skill_contract']),['tests.test_skill_contract'])

    def test_receipt_strictness(self):
        class Synthetic(unittest.TestCase):
            def test_ok(self):pass
        receipt=t.observe(['tests.test_timing'],self.load(Synthetic))
        self.assertTrue(t.valid(receipt,['tests.test_timing'],0))
        for key,val in [('success',1),('os_family','PRIVATE_HOST'),('python','PRIVATE_VERSION'),('extra','PRIVATE')]:
            bad=copy.deepcopy(receipt);bad[key]=val;self.assertFalse(t.valid(bad,['tests.test_timing'],0))
        bad=copy.deepcopy(receipt);bad['total']['seconds']=float('nan');self.assertFalse(t.valid(bad,['tests.test_timing'],0))
        bad=copy.deepcopy(receipt);bad['modules'][0]['test_times'][0]['index']=True;self.assertFalse(t.valid(bad,['tests.test_timing'],0))
        self.assertFalse(t.valid(receipt,['tests.test_timing'],1))

    def test_oversized_integer_seconds_fail_closed_at_every_level(self):
        class Synthetic(unittest.TestCase):
            def test_ok(self):pass
        receipt=t.observe(['tests.test_skill_contract'],self.load(Synthetic))
        for location in ('total','module','test','stage'):
            with self.subTest(location=location):
                bad=copy.deepcopy(receipt)
                target={'total':bad['total'], 'module':bad['modules'][0],
                        'test':bad['modules'][0]['test_times'][0],
                        'stage':bad['modules'][0]['stages']['OTHER']}[location]
                target['seconds']=10**400
                self.assertFalse(t.valid(bad,['tests.test_skill_contract'],0))
                process=subprocess.CompletedProcess([],0,json.dumps(bad).encode(),b'PRIVATE')
                stream=io.StringIO()
                with patch.object(subprocess,'run',return_value=process),contextlib.redirect_stdout(stream):
                    code=t.main(['tests.test_skill_contract'])
                self.assertEqual(code,1)
                self.assertEqual(json.loads(stream.getvalue()),t.fixed_error())
                self.assertNotIn('PRIVATE',stream.getvalue())

    def test_parent_withholds_invalid_worker_stdout_and_stderr(self):
        process=subprocess.CompletedProcess([],2,b'PRIVATE_FD\nnot-json',b'PRIVATE_STDERR')
        stream=io.StringIO()
        with patch.object(subprocess,'run',return_value=process),contextlib.redirect_stdout(stream):
            code=t.main(['tests.test_skill_contract'])
        self.assertEqual(code,1);self.assertNotIn('PRIVATE',stream.getvalue())
        self.assertFalse(json.loads(stream.getvalue())['success'])

    def test_selected_real_module_guide_and_unittest_parity(self):
        root=Path(__file__).resolve().parents[1]
        guide=(root/'docs/TEST_TIMING.md').read_text()
        blocks=re.findall(r'```sh\n(.*?)```',guide,re.S)
        self.assertEqual(len(blocks),1)
        args=shlex.split(blocks[0].strip())
        self.assertEqual(args,['python','-m','tests.timing','tests.test_skill_contract'])
        result=subprocess.run([sys.executable,*args[1:]],cwd=root,capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)
        receipt=json.loads(result.stdout)
        self.assertTrue(t.valid(receipt,['tests.test_skill_contract'],0));self.assertEqual(receipt['total']['tests'],3)
        ordinary=subprocess.run([sys.executable,'-m','unittest','tests.test_skill_contract'],cwd=root,capture_output=True)
        self.assertEqual(ordinary.returncode,result.returncode)
        self.assertIn(b'Ran 3 tests',ordinary.stderr)
        guide=(root/'docs/TEST_TIMING.md').read_text()
        self.assertIn('python -m tests.timing tests.test_skill_contract',guide)


if __name__=='__main__':unittest.main()
