"""Selected trusted help capture: bounded, explicit, never argparse-free check execution."""
import ast
import hashlib
import io
import json
import os
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


class CommandDescriptionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.description=c.describe_script('release_record.py')

    def test_actual_root_subcommand_help_and_usage_reference(self):
        out=self.description
        self.assertEqual(out['schema'],'persona.command-description.v1')
        self.assertEqual(out['generated_from'],'argparse --help')
        self.assertEqual([x['name'] for x in out['subcommands']],['template','check','status'])
        reference=(ROOT/'docs/COMMANDS.md').read_text()
        for usage in out['usage']:self.assertIn(usage,reference)
        self.assertEqual(out['source_sha256'],hashlib.sha256((ROOT/'release_record.py').read_bytes()).hexdigest())
        self.assertEqual(out['input_artifact_schema'],'NOT_DERIVED')
        self.assertEqual(out['output_artifact_schema'],'NOT_DERIVED')

    def test_argparse_free_checks_never_spawn(self):
        with patch.object(c,'_capture_help',side_effect=AssertionError('must not spawn')):
            for name in ('verify_manifest.py','audit_publication.py'):
                out=c.describe_script(name)
                self.assertFalse(out['argparse']);self.assertEqual(out['usage'],[])
                self.assertEqual(out['generated_from'],'STATIC_SOURCE_ONLY_NOT_EXECUTED')

    def test_allowlist_covers_current_scripts_explicitly(self):
        self.assertEqual(set(c.TRUSTED_HELP_SCRIPTS),{name for name,_ in c.root_scripts()})
        self.assertEqual(len(c.TRUSTED_HELP_SCRIPTS),len(set(c.TRUSTED_HELP_SCRIPTS)))

    def test_exact_name_and_allowlist_restrictions(self):
        for name in ('../persona.py','strict_json.py','persona_cli.py','missing.py','PERSONA.PY','/tmp/a.py'):
            with self.subTest(name=name),self.assertRaises(ValueError):c.describe_script(name)

    def test_changed_source_or_missing_inventory_prevents_spawn(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/'persona.py';p.write_text('import argparse\nif __name__ == "__main__":pass\n')
            for raw in ('{}',json.dumps(dict(files=[dict(path='persona.py',sha256='a'*64)]))):
                (root/'PUBLICATION_MANIFEST.json').write_text(raw)
                with patch.object(c,'ROOT',root),patch.object(c,'_capture_help',side_effect=AssertionError('spawn')),self.assertRaises(ValueError):c.describe_script('persona.py')

    def test_duplicate_inventory_rows_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/'persona.py';raw=b'import argparse\nif __name__ == "__main__":pass\n';p.write_bytes(raw)
            row=dict(path='persona.py',sha256=hashlib.sha256(raw).hexdigest())
            (root/'PUBLICATION_MANIFEST.json').write_text(json.dumps(dict(files=[row,row])))
            with patch.object(c,'ROOT',root),self.assertRaises(ValueError):c.describe_script('persona.py')

    def test_inventory_duplicate_json_and_nonfinite_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'persona.py').write_text('import argparse\nif __name__ == "__main__":pass\n')
            for raw in ('{"files":[],"files":[]}','{"files":[],"x":NaN}'):
                (root/'PUBLICATION_MANIFEST.json').write_text(raw)
                with patch.object(c,'ROOT',root),self.assertRaises(ValueError):c.describe_script('persona.py')

    def test_timeout_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'synthetic.py';p.write_text('import time\ntime.sleep(10)\n')
            with patch.object(c,'HELP_TIMEOUT_SECONDS',0.1),self.assertRaises(ValueError):c._capture_help(p,[])

    def test_capture_bound_and_nonzero_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'synthetic.py'
            p.write_text('print("usage: " + "x"*10000)\n')
            with patch.object(c,'MAX_HELP_BYTES',100),self.assertRaises(ValueError):c._capture_help(p,[])
            p.write_text('raise SystemExit(4)\n')
            with self.assertRaises(ValueError):c._capture_help(p,[])
            p.write_text('print("not usage")\n')
            with self.assertRaises(ValueError):c._capture_help(p,[])

    def test_capture_environment_fixed_and_no_bytecode_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'synthetic.py';p.write_text('import os,sys\nprint("usage: " + repr({k:os.environ.get(k) for k in ["PYTHONIOENCODING","COLUMNS","NO_COLOR","PYTHON_COLORS","FORCE_COLOR","PYTHONDONTWRITEBYTECODE"]}))\nassert sys.dont_write_bytecode\n')
            with patch.dict(os.environ,{'FORCE_COLOR':'1','PYTHONIOENCODING':'ascii'}):out=c._capture_help(p,[])
            self.assertIn("'FORCE_COLOR': None",out);self.assertIn("'PYTHONIOENCODING': 'utf-8'",out)
            self.assertFalse((p.parent/'__pycache__').exists())

    def test_dynamic_subcommands_come_from_actual_help(self):
        out=c.describe_script('answer_proposals.py')
        self.assertTrue(out['subcommands'])
        for row in out['subcommands']:
            self.assertIn(' '+row['name']+' ',row['usage'])

    def test_ambiguous_subcommands_fail_closed(self):
        tree=ast.parse('import argparse\np.add_subparsers()')
        with patch.object(c,'_help_source',return_value=(ROOT/'persona.py',tree,'a'*64)),\
             patch.object(c,'_capture_help',return_value='usage: persona.py {a,b} {c,d}\n\nhelp'),self.assertRaises(ValueError):c.describe_script('persona.py')

    def test_aggregate_output_bound_and_escaping(self):
        text=c.render_description(dict(value='한글\n\x1b[2J'));text.encode('ascii');self.assertNotIn('\r',text);self.assertNotIn('\x1b',text)
        with patch.object(c,'MAX_LIST_OUTPUT_BYTES',1),self.assertRaises(ValueError):c.render_description(self.description)

    def test_redacted_no_partial_output(self):
        class Output:buffer=io.BytesIO()
        err=io.StringIO()
        with patch.object(c,'describe_script',side_effect=ValueError('PRIVATE')),patch.object(sys,'stdout',Output()),\
             patch.object(sys,'stderr',err),self.assertRaises(SystemExit):c.main(['describe','persona.py','--json'])
        self.assertEqual(Output.buffer.getvalue(),b'');self.assertNotIn('PRIVATE',err.getvalue())

    def test_cli_external_cwd_no_files_and_repeatable(self):
        with tempfile.TemporaryDirectory() as tmp:
            env=dict(os.environ,PYTHONIOENCODING='ascii',PYTHONDONTWRITEBYTECODE='1')
            args=[sys.executable,str(ROOT/'persona_cli.py'),'describe','persona.py']
            a=subprocess.run(args,cwd=tmp,env=env,capture_output=True);b=subprocess.run(args+['--json'],cwd=tmp,env=env,capture_output=True)
            self.assertEqual(a.returncode,0,a.stderr);self.assertEqual((a.stdout,a.stderr),(b.stdout,b.stderr))
            self.assertNotIn(b'\r',a.stdout);self.assertEqual(list(Path(tmp).iterdir()),[])

    def test_describe_parent_imports_no_repository_modules(self):
        probe='''import json,runpy,sys
before=set(sys.modules)
sys.argv=[sys.argv[1],'describe','persona.py','--json']
try:runpy.run_path(sys.argv[0],run_name='__main__')
except SystemExit as e:code=e.code
sys.stderr.write(json.dumps(dict(code=code,added=sorted(set(sys.modules)-before))))
'''
        run=subprocess.run([sys.executable,'-c',probe,str(ROOT/'persona_cli.py')],capture_output=True)
        report=json.loads(run.stderr);self.assertEqual(report['code'],0);self.assertIn('subprocess',report['added'])
        self.assertFalse(set(report['added']) & ({p.stem for p in ROOT.glob('*.py')}-{'persona_cli'}))

    def test_guide_commands_execute(self):
        for block in re.findall(r'```sh\n(.*?)```',(ROOT/'docs/COMMAND_DESCRIPTION.md').read_text(),re.S):
            for line in block.splitlines():
                if not line.startswith('python '):continue
                self.assertNotIn('>',line)
                run=subprocess.run([sys.executable,*shlex.split(line)[1:]],cwd=ROOT,capture_output=True)
                self.assertEqual(run.returncode,0,(line,run.stderr));self.assertEqual(json.loads(run.stdout)['schema'],c.DESCRIBE_SCHEMA)

    def test_no_all_or_output_flag(self):
        for args in (['describe','persona.py','--all'],['describe','persona.py','--output','out']):
            run=subprocess.run([sys.executable,str(ROOT/'persona_cli.py'),*args],capture_output=True)
            self.assertEqual(run.returncode,2);self.assertEqual(run.stdout,b'')

    def test_all_allowlisted_usage_matches_command_reference(self):
        reference=(ROOT/'docs/COMMANDS.md').read_text()
        for name in c.TRUSTED_HELP_SCRIPTS:
            with self.subTest(script=name):
                out=self.description if name=='release_record.py' else c.describe_script(name)
                for usage in out['usage']:self.assertIn(usage,reference)

    def test_valid_inventory_rows_reject_nonfinite_overflow(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);raw=b'import argparse\nif __name__ == "__main__":pass\n';(root/'persona.py').write_bytes(raw)
            rows=json.dumps([dict(path='persona.py',sha256=hashlib.sha256(raw).hexdigest())])
            for value in ('1e999','-1e999','NaN','Infinity'):
                (root/'PUBLICATION_MANIFEST.json').write_text('{"files":'+rows+',"extra":'+value+'}')
                with self.subTest(value=value),patch.object(c,'ROOT',root),self.assertRaises(ValueError):c._help_source('persona.py')
            (root/'PUBLICATION_MANIFEST.json').write_text('{"files":'+rows+',"extra":1.25}')
            with patch.object(c,'ROOT',root):self.assertEqual(c._help_source('persona.py')[0].name,'persona.py')
