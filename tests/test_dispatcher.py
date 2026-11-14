"""Tests for persona_cli.py: list output, in-process run, rejected names and no side effects in the current directory."""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import persona_cli

ROOT = Path(__file__).resolve().parents[1]
DISPATCHER = ROOT / 'persona_cli.py'
EXAMPLES = ROOT / 'examples'
GUARD = re.compile(r'^if\s+__name__\s*==\s*[\'"]__main__[\'"]\s*:', re.M)


def entry_point_scripts():
    """Independent text-search oracle for the root scripts that have a `__main__` guard."""
    return sorted(path.name for path in ROOT.glob('*.py')
                  if path.name != 'persona_cli.py' and GUARD.search(path.read_text(encoding='utf-8')))


class DispatcherTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cwd = Path(self.tmp.name)

    def dispatch(self, *args):
        return subprocess.run([sys.executable, str(DISPATCHER), *args], cwd=self.cwd,
                              capture_output=True, timeout=120)

    def direct(self, script, *args):
        return subprocess.run([sys.executable, str(ROOT / script), *args], cwd=self.cwd,
                              capture_output=True, timeout=120)

    def listed(self):
        result = self.dispatch('list')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, b'')
        return result.stdout.decode('utf-8').splitlines()

    def test_list_prints_one_line_per_root_script_in_name_order(self):
        lines = self.listed()
        rows = [line.split(None, 1) for line in lines]
        self.assertTrue(all(len(row) == 2 for row in rows), lines)
        names = [row[0] for row in rows]
        self.assertEqual(names, entry_point_scripts())
        self.assertEqual(len(names), len(set(names)))
        for name in ('persona.py', 'verify_manifest.py', 'audit_publication.py', 'synthetic_walkthrough.py'):
            self.assertIn(name, names)
        for name in ('persona_cli.py', 'strict_json.py', 'answer_context.py', 'journey_html.py',
                     'verification_receipt.py'):
            self.assertNotIn(name, names)
        self.assertEqual([name for name in names if name.startswith('test')], [])
        for line in lines:
            self.assertRegex(line, r'^[a-z_]+\.py\s+\S.*\S$')
        by_name = dict(rows)
        self.assertEqual(by_name['persona.py'],
                         'Validate mechanical persona release boundaries; never score scholarly fidelity.')
        self.assertEqual(by_name['safe_canonical_read.py'],
                         'Project canonical JSON into runtime context without holdout identifiers.')
        self.assertEqual(by_name['verify_manifest.py'],
                         'Verify the exact selected public file inventory and its LF-normalized bytes.')
        self.assertEqual(os.listdir(self.cwd), [])

    def test_list_agrees_with_the_command_reference(self):
        reference = (ROOT / 'docs' / 'COMMANDS.md').read_text(encoding='utf-8')
        documented = set(re.findall(r'^### `([a-z_]+\.py)`$', reference, re.M))
        listed = {line.split(None, 1)[0] for line in self.listed()}
        self.assertEqual(listed | {'persona_cli.py'}, documented)

    def test_first_sentence_and_entry_point_helpers(self):
        self.assertEqual(persona_cli.first_sentence('One. Two.'), 'One.')
        self.assertEqual(persona_cli.first_sentence('  Spread\n  over lines. More.'), 'Spread over lines.')
        self.assertEqual(persona_cli.first_sentence('No terminal period'), 'No terminal period')
        self.assertEqual(persona_cli.first_sentence('v1.2 stays whole. Next.'), 'v1.2 stays whole.')
        self.assertEqual(persona_cli.first_sentence(None), '')
        self.assertIsNone(persona_cli.script_record(ROOT / 'strict_json.py'))
        self.assertEqual(persona_cli.script_record(ROOT / 'persona.py'),
                         ('persona.py', 'Validate mechanical persona release boundaries; never score scholarly fidelity.'))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'synthetic.py'
            path.write_bytes(b'def (\n')
            with self.assertRaisesRegex(ValueError, 'cannot parse'):
                persona_cli.script_record(path)
            path.write_bytes(b'#' * (persona_cli.MAX_SOURCE_BYTES + 1))
            with self.assertRaisesRegex(ValueError, 'source bound'):
                persona_cli.script_record(path)
            path.write_bytes(b'"""Synthetic module."""\nif __name__ != "__main__":\n    pass\n')
            self.assertIsNone(persona_cli.script_record(path))
            path.write_bytes(b'if __name__ == "__main__":\n    pass\n')
            self.assertEqual(persona_cli.script_record(path), ('synthetic.py', ''))

    def test_run_reproduces_the_direct_invocation_byte_for_byte(self):
        persona, knowledge = str(EXAMPLES / 'persona.json'), str(EXAMPLES / 'knowledge.json')
        cases = (('verify_manifest.py',),
                 ('persona.py', persona, knowledge),
                 ('persona.py', str(self.cwd / 'missing.json'), knowledge),
                 ('compare_releases.py',),
                 ('safe_canonical_read.py', '--help'),
                 ('human_validation.py', 'status', persona, knowledge, '--text'))
        for case in cases:
            with self.subTest(case=case):
                via = self.dispatch('run', *case)
                direct = self.direct(*case)
                self.assertEqual((via.returncode, via.stdout, via.stderr),
                                 (direct.returncode, direct.stdout, direct.stderr))
        checked = json.loads(self.dispatch('run', 'verify_manifest.py').stdout)
        self.assertEqual(set(checked), {'valid', 'errors'})
        self.assertTrue(json.loads(self.dispatch('run', 'persona.py', persona, knowledge).stdout)['mechanically_valid'])
        self.assertEqual(os.listdir(self.cwd), [])

    def test_run_passes_help_arguments_and_exit_codes_to_the_script(self):
        for flag in ('--help', '-h'):
            helped = self.dispatch('run', 'safe_canonical_read.py', flag)
            self.assertEqual(helped.returncode, 0, helped.stderr)
            self.assertTrue(helped.stdout.decode('utf-8').startswith('usage: safe_canonical_read.py '))
            self.assertNotIn(b'persona_cli', helped.stdout)
        wrong = self.dispatch('run', 'compare_releases.py')
        self.assertEqual(wrong.returncode, 2)
        self.assertEqual(wrong.stdout, b'')
        self.assertIn(b'usage: compare_releases.py', wrong.stderr)
        failing = self.dispatch('run', 'persona.py', str(self.cwd / 'missing.json'), str(EXAMPLES / 'knowledge.json'))
        self.assertEqual(failing.returncode, 1)
        self.assertFalse(json.loads(failing.stdout)['mechanically_valid'])
        self.assertEqual(os.listdir(self.cwd), [])

    def test_run_rejects_names_that_are_not_root_scripts(self):
        for name in ('missing.py', 'strict_json.py', 'answer_context.py', 'persona_cli.py', 'examples/persona.json',
                     '../persona.py', 'tests/test_persona.py', 'tests\\test_persona.py', 'persona', 'Persona.py',
                     'PERSONA.PY', '.persona.py', '', 'tests', 'docs/COMMANDS.md', str(ROOT / 'persona.py')):
            with self.subTest(name=name):
                result = self.dispatch('run', name)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, b'')
                self.assertTrue(result.stderr.startswith(b'persona_cli.py: error: '), result.stderr)
                self.assertIn(b'python persona_cli.py list', result.stderr)
        for args in ((), ('serve',), ('run',), ('run', '--format', 'persona.py'), ('list', 'extra')):
            with self.subTest(args=args):
                result = self.dispatch(*args)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, b'')
                self.assertIn(b'usage: persona_cli.py', result.stderr)
        self.assertEqual(os.listdir(self.cwd), [])

    def test_help_states_the_boundary(self):
        result = self.dispatch('--help')
        self.assertEqual(result.returncode, 0, result.stderr)
        text = result.stdout.decode('utf-8').replace('\r\n', '\n')
        self.assertTrue(text.startswith('usage: persona_cli.py [-h] [--version] {list,describe,run} ...'))
        for phrase in ('changes none of a script\'s arguments, outputs or exit codes',
                       'remains the primary command', 'calls no model, reads no network',
                       'writes no file', 'not an\napproval of any input',
                       'NOT an integrity check or signature', 'python verify_manifest.py'):
            self.assertIn(phrase, text)
        self.assertEqual(os.listdir(self.cwd), [])

    def test_dispatcher_imports_no_repository_module_and_no_shell(self):
        probe = ('import json, runpy, sys\n'
                 'dispatcher, command = sys.argv[1], sys.argv[2:]\n'
                 'before = set(sys.modules)\n'
                 'sys.argv = [dispatcher, *command]\n'
                 'try:\n'
                 '    runpy.run_path(dispatcher, run_name="__main__")\n'
                 'except SystemExit as exc:\n'
                 '    code = exc.code\n'
                 'else:\n'
                 '    code = 0\n'
                 'sys.stderr.write(json.dumps(dict(code=code, added=sorted(set(sys.modules) - before))))\n')
        library = {path.stem for path in ROOT.glob('*.py')} - {'persona_cli'}
        persona, knowledge = str(EXAMPLES / 'persona.json'), str(EXAMPLES / 'knowledge.json')
        for command, expected in ((['list'], set()), (['run', 'persona.py', persona, knowledge], {'strict_json'})):
            with self.subTest(command=command):
                result = subprocess.run([sys.executable, '-c', probe, str(DISPATCHER), *command],
                                        cwd=self.cwd, capture_output=True, timeout=120)
                report = json.loads(result.stderr.decode('utf-8'))
                self.assertEqual(report['code'], 0, result.stderr)
                added = set(report['added'])
                self.assertEqual(added & library, expected)
                self.assertNotIn('subprocess', added)
                self.assertTrue(result.stdout)
        self.assertEqual(os.listdir(self.cwd), [])

    def test_file_relative_modules_still_resolve_the_repository_root(self):
        persona, knowledge = str(EXAMPLES / 'persona.json'), str(EXAMPLES / 'knowledge.json')
        inside = EXAMPLES / 'unlisted-dispatcher-template.json'
        self.assertFalse(inside.exists())
        try:
            via = self.dispatch('run', 'human_validation.py', 'template', persona, knowledge, '--output', str(inside))
            direct = self.direct('human_validation.py', 'template', persona, knowledge, '--output', str(inside))
            self.assertNotEqual(via.returncode, 0)
            self.assertEqual((via.returncode, via.stdout, via.stderr),
                             (direct.returncode, direct.stdout, direct.stderr))
            self.assertFalse(inside.exists())
        finally:
            if inside.exists():
                inside.unlink()
        outside = self.cwd / 'template.json'
        written = self.dispatch('run', 'human_validation.py', 'template', persona, knowledge, '--output', str(outside))
        self.assertEqual(written.returncode, 0, written.stderr)
        self.assertEqual(os.listdir(self.cwd), ['template.json'])
        self.assertEqual(json.loads(outside.read_text(encoding='utf-8'))['status'], None)


if __name__ == '__main__':
    unittest.main()
