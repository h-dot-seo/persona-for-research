"""Private notes preserve existing report meaning, not rendering/share safety."""
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import string
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import human_validation as hv
import source_recheck as source
import journey_compare as comparison
import private_markdown as md

ROOT = Path(__file__).resolve().parents[1]
MARKER = '## Complete JSON snapshot\n\n'


def snapshot(text):
    head, raw = text.split(MARKER, 1)
    lines = raw.splitlines()
    if not lines or any(not line.startswith('    ') for line in lines):
        raise AssertionError('snapshot line escaped its indented block')
    return json.loads('\n'.join(line[4:] for line in lines))


class PrivateMarkdownTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='private markdown 한글 space ')
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.work = Path(cls.tmp.name).resolve()
        text = (ROOT / 'docs/MARKDOWN_REPORTS.md').read_text(encoding='utf-8')
        blocks = re.findall(r'```python\n(.*?)```', text, re.S)
        assert len(blocks) == 1
        code = blocks[0].replace("Path('OUTPUT')", 'Path(' + repr(str(cls.work)) + ')')
        exec(compile(code, 'documented synthetic preparation', 'exec'), {})
        blocks = re.findall(r'```sh\n(.*?)```', text, re.S)
        assert len(blocks) == 1
        cls.commands = []
        for line in blocks[0].splitlines():
            if not line.strip(): continue
            tokens = shlex.split(line)
            assert tokens[0] == 'python'
            tokens[0] = sys.executable
            tokens = [str(cls.work.joinpath(*token.split('/')[1:])) if token.startswith('OUTPUT/') else token for token in tokens]
            cls.commands.append(tokens)
        assert len(cls.commands) == 4

    def cli(self, command, seed='7'):
        return subprocess.run(command, cwd=ROOT, capture_output=True, timeout=40,
                              env=dict(os.environ, PYTHONHASHSEED=seed))

    def json_command(self, command):
        command = list(command)
        if '--output' in command:
            i = command.index('--output'); del command[i:i+2]
        if '--markdown' in command: command.remove('--markdown')
        if '--format' in command: command[command.index('--format') + 1] = 'json'
        return command

    def test_four_actual_documented_commands_and_exact_snapshots(self):
        for command in self.commands:
            output = Path(command[command.index('--output') + 1])
            result = self.cli(command)
            self.assertEqual(result.returncode, 0, result.stderr)
            raw = output.read_bytes()
            expected = self.cli(self.json_command(command))
            self.assertEqual(expected.returncode, 0, expected.stderr)
            self.assertEqual(snapshot(raw.decode('utf-8')), json.loads(expected.stdout))
            before = raw
            result = self.cli(command)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, b'')
            self.assertEqual(output.read_bytes(), before)

    def test_punctuation_controls_html_fences_and_urls_remain_data(self):
        hostile = '# heading\n> quote\r\t\x00\x1b\u202e\u2028\ud800 ![image](https://example.invalid/x) <script>x</script> &#x202e; ``` `````` | table |'
        value = {hostile: [hostile, None, False, 0, '한국어', {'url': 'https://example.invalid/private'}]}
        original = copy.deepcopy(value)
        text = md.render('Private title', value, max_bytes=100_000, limit_message='limit')
        self.assertEqual(snapshot(text), value); self.assertEqual(value, original)
        head = text.split(MARKER)[0]
        for raw in ('<script>', '![image]', '\x1b', '\u202e', '\u2028', '\ud800'):
            self.assertNotIn(raw, head)
        for char in string.punctuation:
            self.assertEqual(md.escape(char), '\\' + char)
        self.assertIn('\\<script\\>', head)
        self.assertNotIn('\n> quote', head)
        self.assertNotIn('\n# heading', head)
        self.assertTrue(all(line.startswith('    ') for line in text.split(MARKER)[1].splitlines()))
        text.encode('utf-8')

    def test_snapshot_key_order_empty_shapes_and_budget_exact_boundary(self):
        value = {'z': [], 'a': {}, 'null': None, 'float': 1.0, 'false': False}
        args = dict(max_bytes=100_000, limit_message='fixed limit')
        text = md.render('note', value, **args)
        self.assertEqual(text, md.render('note', dict(reversed(list(value.items()))), **args))
        size = len(text.encode('utf-8'))
        self.assertEqual(md.render('note', value, max_bytes=size, limit_message='fixed limit'), text)
        with self.assertRaisesRegex(ValueError, '^fixed limit$'):
            md.render('note', value, max_bytes=size-1, limit_message='fixed limit')
        self.assertEqual(snapshot(text), value)

    def test_two_seed_actual_output_determinism(self):
        for command in self.commands:
            command = command[:command.index('--output')]
            first = self.cli(command, '7'); second = self.cli(command, '97')
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual((first.returncode, first.stdout, first.stderr), (second.returncode, second.stdout, second.stderr))
            snapshot(first.stdout.decode('utf-8'))

    def test_hv_current_stale_absent_and_template_not_assessment(self):
        package = json.loads((ROOT/'examples/trajectory-conditions-package.json').read_bytes())
        record = json.loads((ROOT/'examples/manual-human-validation.json').read_bytes())
        for value in (record, dict(record, persona_payload_sha256='f'*64)):
            result = hv.check(value, package)
            text = md.render('Human check', result, max_bytes=hv.MAX_OUTPUT_BYTES, limit_message='limit')
            self.assertEqual(snapshot(text), result)
        empty = hv.axis(package)
        self.assertEqual(empty['status'], 'NOT_PERFORMED')
        self.assertEqual(snapshot(md.render('Human status', empty, max_bytes=hv.MAX_OUTPUT_BYTES, limit_message='limit')), empty)
        with self.assertRaises(ValueError): hv.check(hv.template(package), package)

    def test_hv_format_conflict_and_source_template_combination_fail(self):
        command = self.commands[0][:self.commands[0].index('--output')] + ['--text']
        result = self.cli(command)
        self.assertEqual(result.returncode, 2); self.assertEqual(result.stdout, b'')
        command = [sys.executable, 'source_recheck.py', str(self.work/'source-package.json'), '--template', '--operator-id', 'synthetic', '--format', 'markdown']
        result = self.cli(command)
        self.assertEqual(result.returncode, 1); self.assertEqual(result.stdout, b'')
        self.assertEqual(result.stderr, ('template needs JSON output and no source selection/root'+os.linesep).encode('utf-8'))

    def test_journey_fresh_compare_exactly_once_and_full_snapshot(self):
        previous = json.loads((self.work/'previous-card.json').read_bytes())
        current = json.loads((self.work/'current-card.json').read_bytes())
        args = (previous, self.work/'previous inputs', current, self.work/'current inputs')
        with patch.object(comparison, 'compare', wraps=comparison.compare) as compare:
            text = comparison.render(*args, format='markdown')
        self.assertEqual(compare.call_count, 1)
        self.assertEqual(snapshot(text), comparison.compare(*args))
        self.assertFalse(snapshot(text)['automatic_approval'])
        self.assertIn('previous_report', snapshot(text)); self.assertIn('current_report', snapshot(text))

    def test_mixed_version_external_context_stays_separate_in_snapshot(self):
        from tests.test_external_journey import ExternalJourneyTests
        case = ExternalJourneyTests(); case.setUp(); self.addCleanup(case.doCleanups)
        previous, current = case.v1(), case.prepare()
        args = (previous, case.root, current, case.root)
        actual = snapshot(comparison.render(*args, format='markdown'))
        self.assertEqual(actual, comparison.compare(*args))
        self.assertEqual(actual['external_slot_comparison']['previous'], 'NOT_SUPPORTED_BY_CARD_VERSION')
        self.assertEqual(actual['external_slot_comparison']['current'], 'SUPPLIED')
        self.assertEqual(actual['previous_report']['evidence_routes'], actual['current_report']['evidence_routes'])
        self.assertIn('external_evidence_review', actual['current_report'])
        self.assertNotIn('external_evidence_review', actual['previous_report'])

    def test_hv_and_source_read_and_check_calls_unchanged(self):
        for module, command, checker, reader in ((hv, self.commands[0], 'check', 'bounded_reader'), (source, self.commands[2], 'audit', '_load')):
            observations = []
            for markdown in (False, True):
                argv = command[1:command.index('--output')]
                if not markdown:
                    if '--markdown' in argv: argv.remove('--markdown')
                    if '--format' in argv: argv[argv.index('--format')+1] = 'json'
                with patch.object(sys, 'argv', argv), patch.object(module, checker, wraps=getattr(module, checker)) as checked, patch.object(module, reader, wraps=getattr(module, reader)) as read, patch.object(module, 'emit') as emitted:
                    module.main()
                self.assertEqual(emitted.call_count, 1)
                observations.append((checked.call_count, read.call_count, emitted.call_args.args[1]))
            self.assertEqual(observations[0][:2], observations[1][:2])
            self.assertEqual(snapshot(observations[1][2].decode('utf-8')), json.loads(observations[0][2]))

    def test_all_four_command_input_read_order_and_source_bytes_unchanged(self):
        for index, module in ((0, hv), (1, hv), (2, source), (3, comparison)):
            logs = []
            for markdown in (False, True):
                command = self.commands[index]
                argv = command[1:command.index('--output')]
                if not markdown:
                    if '--markdown' in argv: argv.remove('--markdown')
                    if '--format' in argv: argv[argv.index('--format')+1] = 'json'
                calls = []
                with contextlib.ExitStack() as stack:
                    stack.enter_context(patch.object(sys, 'argv', argv))
                    stack.enter_context(patch.object(module, 'emit'))
                    if module is hv:
                        original = hv.bounded_reader
                        def factory(*args, **kwargs):
                            read = original(*args, **kwargs)
                            def tracked(path):
                                calls.append(('json', str(path)))
                                return read(path)
                            return tracked
                        stack.enter_context(patch.object(hv, 'bounded_reader', side_effect=factory))
                    else:
                        targets = ((source, '_load'), (source, 'read_source_bytes')) if module is source else ((comparison.inputs, '_load_card'), (comparison.inputs, 'read_source_bytes'))
                        for owner, name in targets:
                            original = getattr(owner, name)
                            def tracked(*args, _name=name, _original=original, **kwargs):
                                calls.append((_name, str(args[0])))
                                return _original(*args, **kwargs)
                            stack.enter_context(patch.object(owner, name, side_effect=tracked))
                    module.main()
                self.assertTrue(calls)
                logs.append(calls)
            self.assertEqual(logs[0], logs[1], index)

    def test_existing_output_budgets_and_no_partial_emit(self):
        for module, command, constant, message in ((hv, self.commands[0], 'MAX_OUTPUT_BYTES', 'human validation output exceeds 16 MiB'), (source, self.commands[2], 'MAX_JSON_BYTES', 'source recheck output exceeds 8 MiB')):
            argv = command[1:command.index('--output')]
            # Budget smaller than Markdown, but larger than its JSON report and inputs.
            result = self.cli(command[:command.index('--output')]); self.assertEqual(result.returncode, 0)
            limit = len(result.stdout)-1
            stderr = io.StringIO()
            with patch.object(sys,'argv',argv), patch.object(module,constant,limit), patch.object(module,'emit') as emit, contextlib.redirect_stderr(stderr):
                with self.assertRaises(SystemExit) as raised: module.main()
            self.assertEqual(raised.exception.code, 1); emit.assert_not_called()
            self.assertEqual(stderr.getvalue(), message+'\n')
        previous = json.loads((self.work/'previous-card.json').read_bytes()); current = json.loads((self.work/'current-card.json').read_bytes())
        args=(previous,self.work/'previous inputs',current,self.work/'current inputs')
        text=comparison.render(*args,format='markdown')
        with patch.object(comparison,'MAX_OUTPUT_BYTES',len(text.encode('utf-8'))-1):
            with self.assertRaisesRegex(ValueError,'^Markdown journey comparison exceeds 16 MiB$'):
                comparison.render(*args,format='markdown')

    def test_changed_source_and_card_bytes_fail_without_markdown_output(self):
        with tempfile.TemporaryDirectory(prefix='changed note inputs ') as temporary:
            root = Path(temporary)
            sources = root/'sources'; shutil.copytree(self.work/'synthetic sources', sources)
            target = sources/'synthetic-0.md'; target.write_bytes(target.read_bytes()+b'\n')
            command = self.commands[2][:self.commands[2].index('--output')]
            command[command.index('--source-root')+1] = str(sources)
            # Source mismatch is an existing report state, not necessarily a CLI error.
            result = self.cli(command); baseline = self.cli(self.json_command(command))
            self.assertEqual(result.returncode, baseline.returncode)
            if result.returncode == 0:
                self.assertEqual(snapshot(result.stdout.decode('utf-8')), json.loads(baseline.stdout))
            else: self.assertEqual(result.stdout, b'')
            current = root/'current'; shutil.copytree(self.work/'current inputs', current)
            target = current/'patterns.json'; target.write_bytes(target.read_bytes()+b'\n')
            command = self.commands[3][:self.commands[3].index('--output')]
            command[command.index('--current-root')+1] = str(current)
            output = root/'never.md'
            result = self.cli(command+['--output',str(output)])
            self.assertEqual(result.returncode,1); self.assertEqual(result.stdout,b'')
            self.assertFalse(output.exists()); self.assertNotIn(b'Traceback',result.stderr)

    def test_malformed_and_stale_inputs_never_write_notes(self):
        with tempfile.TemporaryDirectory(prefix='invalid private note ') as temporary:
            bad = Path(temporary)/'bad.json'; bad.write_bytes(b'null\n')
            for command in self.commands:
                candidate = command[:command.index('--output')]
                # First positional input after HV subcommand or script.
                candidate[3 if candidate[1]=='human_validation.py' else 2] = str(bad)
                output=Path(temporary)/'never.md'
                result=self.cli(candidate+['--output',str(output)])
                self.assertNotEqual(result.returncode,0);self.assertEqual(result.stdout,b'')
                self.assertNotIn(b'Traceback',result.stderr);self.assertFalse(output.exists())


if __name__ == '__main__': unittest.main()
