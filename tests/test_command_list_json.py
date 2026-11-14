"""Machine-readable AST discovery without importing or running discovered scripts."""
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

import persona_cli as cli

ROOT=Path(__file__).resolve().parents[1]


class CommandListJsonTests(unittest.TestCase):
    def test_exact_shape_sorted_and_plain_rows_agree(self):
        rows=cli.root_scripts();out=json.loads(cli.render_json(rows))
        self.assertEqual(set(out),{'schema','scripts','boundary'})
        self.assertEqual(out['schema'],'persona.command-list.v1')
        self.assertEqual(out['scripts'],[dict(script=a,first_sentence=b) for a,b in rows])
        self.assertEqual([x['script'] for x in out['scripts']],sorted(x['script'] for x in out['scripts']))
        self.assertIn('not an invocation/schema contract',out['boundary'])
        self.assertNotIn('persona_cli.py',[x['script'] for x in out['scripts']])

    def test_deterministic_ascii_lf_and_control_escaping(self):
        rows=[('synthetic.py','Synthetic 한글\n\x1b[2J')]
        a=cli.render_json(rows);self.assertEqual(a,cli.render_json(rows));a.encode('ascii')
        self.assertTrue(a.endswith('\n'));self.assertNotIn('\r',a);self.assertNotIn('\x1b',a)
        self.assertEqual(json.loads(a)['scripts'][0]['first_sentence'],rows[0][1])

    def test_empty_list_has_boundary(self):
        out=json.loads(cli.render_json([]));self.assertEqual(out['scripts'],[]);self.assertTrue(out['boundary'])

    def test_json_output_bound_fails_before_write(self):
        with patch.object(cli,'MAX_LIST_OUTPUT_BYTES',1),self.assertRaises(ValueError):cli.render_json([])
        class Output:
            buffer=io.BytesIO()
        with patch.object(cli,'MAX_LIST_OUTPUT_BYTES',1),patch.object(sys,'stdout',Output()),\
             patch.object(sys,'stderr',io.StringIO()),self.assertRaises(SystemExit):cli.main(['list','--json'])
        self.assertEqual(Output.buffer.getvalue(),b'')

    def test_ast_does_not_execute_top_level_or_imports(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);marker=root/'created'
            script=root/'synthetic.py'
            script.write_text('"""Synthetic discovery only. More text."""\nimport nonexistent_private_module\nraise RuntimeError("must not run")\nif __name__ == "__main__":\n    open('+repr(str(marker))+', "w").write("bad")\n')
            (root/'library.py').write_text('raise RuntimeError("must not import")\n')
            with patch.object(cli,'ROOT',root):
                self.assertEqual(json.loads(cli.render_json(cli.root_scripts()))['scripts'],
                                 [dict(script='synthetic.py',first_sentence='Synthetic discovery only.')])
            self.assertFalse(marker.exists())

    def test_oversize_source_and_parse_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'bad.py';p.write_bytes(b'x'*(cli.MAX_SOURCE_BYTES+1))
            with self.assertRaisesRegex(ValueError,'source bound'):cli.script_record(p)
            p.write_bytes(b'def (')
            with self.assertRaisesRegex(ValueError,'cannot parse'):cli.script_record(p)

    def test_source_read_is_bounded(self):
        class Stream(io.BytesIO):
            def read(self,size=-1):
                self.requested=size;return super().read(size)
        class Source:
            name='synthetic.py'
            def open(self,mode):
                self.stream=Stream(b'x'*(cli.MAX_SOURCE_BYTES+100));return self.stream
            def __str__(self):return self.name
        source=Source()
        with self.assertRaises(ValueError):cli.script_record(source)
        self.assertTrue(source.stream.closed)
        self.assertEqual(source.stream.requested,cli.MAX_SOURCE_BYTES+1)

    def test_symlink_is_not_discovered(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);target=root/'source.txt';target.write_text('if __name__ == "__main__": pass\n')
            try:(root/'linked.py').symlink_to(target)
            except OSError:self.skipTest('symlink unavailable')
            with patch.object(cli,'ROOT',root):self.assertEqual(cli.root_scripts(),[])

    def test_json_failure_redacts_source_details(self):
        out=io.StringIO()
        with patch.object(cli,'root_scripts',side_effect=ValueError('PRIVATE source text')),\
             patch.object(sys,'stderr',out),self.assertRaises(SystemExit):cli.main(['list','--json'])
        self.assertNotIn('PRIVATE',out.getvalue());self.assertIn('cannot produce bounded command list JSON',out.getvalue())

    def test_cli_from_external_cwd_utf8_lf_and_no_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            env=dict(os.environ,PYTHONIOENCODING='ascii',PYTHONDONTWRITEBYTECODE='1')
            args=[sys.executable,str(ROOT/'persona_cli.py'),'list','--json']
            first=subprocess.run(args,cwd=tmp,env=env,capture_output=True);second=subprocess.run(args,cwd=tmp,env=env,capture_output=True)
            self.assertEqual(first.returncode,0,first.stderr);self.assertEqual(first.stdout,second.stdout)
            self.assertEqual(first.stderr,b'');self.assertNotIn(b'\r',first.stdout);json.loads(first.stdout)
            self.assertEqual(list(Path(tmp).iterdir()),[])

    def test_no_repository_imports_or_subprocess_in_json_path(self):
        probe='''import json,runpy,sys
before=set(sys.modules)
sys.argv=[sys.argv[1],'list','--json']
try:runpy.run_path(sys.argv[0],run_name='__main__')
except SystemExit as e:code=e.code
sys.stderr.write(json.dumps(dict(code=code,added=sorted(set(sys.modules)-before))))
'''
        with tempfile.TemporaryDirectory() as tmp:
            run=subprocess.run([sys.executable,'-c',probe,str(ROOT/'persona_cli.py')],cwd=tmp,capture_output=True)
            report=json.loads(run.stderr);self.assertEqual(report['code'],0)
            self.assertNotIn('subprocess',report['added'])
            library={p.stem for p in ROOT.glob('*.py')}-{'persona_cli'}
            self.assertFalse(set(report['added']) & library)
            self.assertEqual(list(Path(tmp).iterdir()),[])

    def test_guide_executes_exactly(self):
        guide=(ROOT/'docs/COMMAND_LIST.md').read_text()
        with tempfile.TemporaryDirectory() as tmp:
            for block in re.findall(r'```sh\n(.*?)```',guide,re.S):
                for line in block.splitlines():
                    if not line.startswith('python '):continue
                    self.assertNotIn('>',line)
                    args=shlex.split(line)[1:]
                    run=subprocess.run([sys.executable,*args],cwd=ROOT,capture_output=True)
                    self.assertEqual(run.returncode,0,(line,run.stderr))
                    if '--json' in args:self.assertEqual(json.loads(run.stdout)['schema'],cli.LIST_SCHEMA)

    def test_list_json_rejects_output_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            run=subprocess.run([sys.executable,str(ROOT/'persona_cli.py'),'list','--json','--output','unexpected'],cwd=tmp,capture_output=True)
            self.assertEqual(run.returncode,2);self.assertEqual(run.stdout,b'');self.assertEqual(list(Path(tmp).iterdir()),[])
