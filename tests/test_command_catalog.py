"""Bounded complete-or-explicitly-partial trusted command help catalogs."""
import copy
import io
import json
import re
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import persona_cli as c
ROOT=Path(__file__).resolve().parents[1]


def small(name,**kwargs):return dict(script=name,usage=['usage: '+name],boundary='Synthetic description')


class CommandCatalogTests(unittest.TestCase):
    def test_complete_sorted_shape_and_deterministic(self):
        with patch.object(c,'TRUSTED_HELP_SCRIPTS',('b.py','a.py')),patch.object(c,'describe_script',side_effect=small):
            one=c.describe_all();two=c.describe_all()
        self.assertEqual(one,two);self.assertEqual(one['schema'],'persona.command-catalog.v1')
        self.assertEqual(one['status'],'COMPLETE_CATALOG');self.assertEqual(one['counts']['DESCRIBED'],2)
        self.assertEqual([r['script'] for r in one['scripts']],['a.py','b.py'])
        self.assertEqual(one['input_artifact_schema'],'NOT_DERIVED')

    def test_failures_are_redacted_and_other_rows_continue(self):
        def describe(name,**kwargs):
            if name=='a.py':raise ValueError('PRIVATE source details')
            return small(name)
        with patch.object(c,'TRUSTED_HELP_SCRIPTS',('a.py','b.py')),patch.object(c,'describe_script',side_effect=describe):out=c.describe_all()
        self.assertEqual(out['status'],'PARTIAL_CATALOG');self.assertEqual(out['counts']['FAILED'],1)
        self.assertEqual(out['counts']['DESCRIBED'],1);self.assertNotIn('PRIVATE',c.render_catalog(out))

    def test_zero_time_budget_never_attempts(self):
        with patch.object(c,'TRUSTED_HELP_SCRIPTS',('a.py','b.py')),patch.object(c,'CATALOG_TIMEOUT_SECONDS',0),\
             patch.object(c,'describe_script',side_effect=AssertionError('attempt')):out=c.describe_all()
        self.assertEqual(out['counts']['NOT_ATTEMPTED_TIME_BUDGET'],2)
        self.assertEqual(out['status'],'PARTIAL_CATALOG')

    def test_shared_deadline_is_forwarded_and_no_later_attempt(self):
        clock=[0.0];seen=[]
        def describe(name,deadline=None):
            seen.append((name,deadline));clock[0]=2.0;raise ValueError('timeout')
        with patch.object(c,'TRUSTED_HELP_SCRIPTS',('a.py','b.py')),patch.object(c,'CATALOG_TIMEOUT_SECONDS',1),\
             patch('time.monotonic',side_effect=lambda:clock[0]),patch.object(c,'describe_script',side_effect=describe):out=c.describe_all()
        self.assertEqual(seen,[('a.py',1.0)]);self.assertEqual(out['counts']['FAILED_TIME_BUDGET'],1)
        self.assertEqual(out['counts']['NOT_ATTEMPTED_TIME_BUDGET'],1)

    def test_output_budget_preserves_prior_success_and_marks_rest(self):
        def describe(name,**kwargs):return small(name) if name=='a.py' else dict(script=name,help='x'*10000)
        with patch.object(c,'TRUSTED_HELP_SCRIPTS',('a.py','b.py','c.py')),patch.object(c,'describe_script',side_effect=describe) as spy,\
             patch.object(c,'MAX_CATALOG_BYTES',5000),patch.object(c,'CATALOG_RESERVE_BYTES',1000):out=c.describe_all()
        self.assertEqual(spy.call_count,2)
        self.assertEqual([r['status'] for r in out['scripts']],['DESCRIBED','OMITTED_OUTPUT_BUDGET','NOT_ATTEMPTED_OUTPUT_BUDGET'])
        self.assertLess(len(c.render_catalog(out).encode()),5000)

    def test_tiny_output_budget_fails_without_capture(self):
        with patch.object(c,'MAX_CATALOG_BYTES',100),patch.object(c,'describe_script',side_effect=AssertionError('capture')),self.assertRaises(ValueError):c.describe_all()

    def test_invalid_allowlist_duplicates_and_count_rejected(self):
        for names in (('a.py','a.py'),tuple('x%d.py'%n for n in range(c.MAX_CATALOG_SCRIPTS+1))):
            with patch.object(c,'TRUSTED_HELP_SCRIPTS',names),self.assertRaises(ValueError):c.describe_all()

    def test_complete_empty_allowlist_is_explicit(self):
        with patch.object(c,'TRUSTED_HELP_SCRIPTS',()):out=c.describe_all()
        self.assertEqual(out['script_count'],0);self.assertEqual(out['scripts'],[])

    def test_single_describe_deadline_enforces_no_capture(self):
        with patch.object(c,'_capture_help',side_effect=AssertionError('capture')),self.assertRaises(ValueError):c.describe_script('persona.py',deadline=0)

    def test_capture_nonpositive_timeout_refuses_before_spawn(self):
        with self.assertRaises(ValueError):c._capture_help(ROOT/'persona.py',[],timeout=0)

    def test_parser_requires_exactly_one_selection(self):
        parser=c.build_parser()
        for args in (['describe'],['describe','persona.py','--all']):
            with patch.object(sys,'stderr',io.StringIO()),self.assertRaises(SystemExit):parser.parse_args(args)
        self.assertTrue(parser.parse_args(['describe','--all','--json']).all_scripts)
        self.assertEqual(parser.parse_args(['describe','persona.py']).script,'persona.py')

    def test_partial_cli_is_json_not_error_or_silent_complete(self):
        class Output:buffer=io.BytesIO()
        with patch.object(c,'TRUSTED_HELP_SCRIPTS',('a.py',)),patch.object(c,'describe_script',side_effect=ValueError('PRIVATE')),\
             patch.object(sys,'stdout',Output()):code=c.main(['describe','--all','--json'])
        self.assertEqual(code,0);out=json.loads(Output.buffer.getvalue());self.assertEqual(out['status'],'PARTIAL_CATALOG')
        self.assertNotIn(b'PRIVATE',Output.buffer.getvalue())

    def test_all_selection_never_runs_argparse_free_checks(self):
        with patch.object(c,'TRUSTED_HELP_SCRIPTS',('verify_manifest.py','audit_publication.py')),\
             patch.object(c,'_capture_help',side_effect=AssertionError('must not run')):out=c.describe_all()
        self.assertEqual(out['status'],'COMPLETE_CATALOG')
        self.assertTrue(all(not row['description']['argparse'] for row in out['scripts']))

    def test_real_guide_catalog_and_reference_usage(self):
        guide=(ROOT/'docs/COMMAND_CATALOG.md').read_text();reference=(ROOT/'docs/COMMANDS.md').read_text()
        for block in re.findall(r'```sh\n(.*?)```',guide,re.S):
            for line in block.splitlines():
                if not line.startswith('python '):continue
                self.assertNotIn('>',line)
                run=subprocess.run([sys.executable,*shlex.split(line)[1:]],cwd=ROOT,capture_output=True,timeout=180)
                self.assertEqual(run.returncode,0,(line,run.stderr));out=json.loads(run.stdout)
                self.assertEqual(out['status'],'COMPLETE_CATALOG');self.assertEqual(out['script_count'],len(c.TRUSTED_HELP_SCRIPTS))
                for row in out['scripts']:
                    for usage in row['description']['usage']:self.assertIn(usage,reference)
                self.assertNotIn(b'\r',run.stdout)

    def test_timeout_reaps_direct_child_and_reader(self):
        import threading
        processes=[];original=subprocess.Popen
        def launch(*args,**kwargs):
            process=original(*args,**kwargs);processes.append(process);return process
        with tempfile.TemporaryDirectory() as tmp:
            script=Path(tmp)/'synthetic.py';script.write_text('import time\ntime.sleep(10)\n')
            before={t.ident for t in threading.enumerate()}
            with patch('subprocess.Popen',side_effect=launch),patch.object(c,'HELP_TIMEOUT_SECONDS',0.1),self.assertRaises(ValueError):c._capture_help(script,[])
            self.assertTrue(processes);self.assertIsNotNone(processes[0].poll())
            self.assertFalse([t for t in threading.enumerate() if t.name=='persona-help-reader' and t.ident not in before])

    def test_completion_is_not_a_hard_timing_certification(self):
        clock=[0.0]
        def describe(name,**kwargs):clock[0]=2.0;return small(name)
        with patch.object(c,'TRUSTED_HELP_SCRIPTS',('a.py',)),patch.object(c,'CATALOG_TIMEOUT_SECONDS',1),\
             patch('time.monotonic',side_effect=lambda:clock[0]),patch.object(c,'describe_script',side_effect=describe):out=c.describe_all()
        self.assertEqual(out['status'],'COMPLETE_CATALOG')
        self.assertEqual(out['counts']['DESCRIBED'],1)
