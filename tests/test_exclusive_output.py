"""Synthetic output files are explicit, byte-preserving and never overwritten."""
import argparse
import ast
import hashlib
import importlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import exclusive_output as output
from persona import payload_sha256

ROOT = Path(__file__).resolve().parents[1]
MODULES = (
    'observation_input research_workflow prepare_local_manifest corpus_files curate_local '
    'revise_local source_recheck topic_inventory review_package compare_releases extraction_adapter '
    'model_handoff observation_proposals observation_revision operator_review audit_design_lineage '
    'audit_design_chain publication_timeline publication_context publication_scope reasoning_links '
    'design_scenario answer_draft review_journey evidence_scope citation_reasoning answer_proposals '
    'argument_proposals pattern_proposals application_proposals method_application applicability_review '
    'pattern_hypotheses pattern_transfer_review research_journey journey_inputs journey_compare '
    'revision_impact evaluate_synthetic argument_map human_validation').split()


def capture_parser(name):
    class Captured(Exception):
        pass
    seen = []
    def capture(parser, *args, **kwargs):
        seen.append(parser)
        raise Captured()
    with patch.object(argparse.ArgumentParser, 'parse_args', capture), \
         patch.object(argparse.ArgumentParser, 'parse_intermixed_args', capture):
        try:
            importlib.import_module(name).main()
        except Captured:
            return seen[0]
    raise AssertionError('parser not captured')


def leaves(parser):
    sub = [a for a in parser._actions if isinstance(a, argparse._SubParsersAction)]
    if not sub:
        yield parser
    for action in sub:
        for child in action.choices.values():
            yield from leaves(child)


class ExclusiveOutputTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.target = self.root / 'result.json'

    def emit(self, raw=b'{"synthetic":true}\n'):
        buffer = io.BytesIO()
        stream = io.TextIOWrapper(buffer, encoding='ascii', newline='\r\n')
        errors = io.StringIO()
        try:
            with patch.object(sys, 'stdout', stream), patch.object(sys, 'stderr', errors):
                try:
                    output.emit(argparse.ArgumentParser(), raw, self.target)
                    code = 0
                except SystemExit as exc:
                    code = exc.code
            stream.flush()
            return code, buffer.getvalue(), errors.getvalue()
        finally:
            stream.detach()

    def test_saved_exact_bytes_and_receipt_hashes(self):
        raw = '{"synthetic":"한국어 µ"}\n'.encode('utf-8')
        code, receipt, errors = self.emit(raw)
        self.assertEqual((code, errors), (0, ''))
        self.assertEqual(self.target.read_bytes(), raw)
        r = json.loads(receipt)
        self.assertEqual(r['sha256'], hashlib.sha256(raw).hexdigest())
        self.assertEqual(r['payload_sha256'], payload_sha256(json.loads(raw)))
        self.assertEqual(r['bytes'], len(raw))
        self.assertNotIn('한국어', receipt.decode())
        self.assertEqual(r['status'], 'SAVED')

    def test_text_and_html_have_only_raw_hash(self):
        for raw in (b'Fictional text\n', b'<!doctype html><p>Fictional</p>\n'):
            self.target = self.root / str(len(raw))
            code, receipt, _ = self.emit(raw)
            self.assertEqual(code, 0)
            self.assertIsNone(json.loads(receipt)['payload_sha256'])
            self.assertEqual(self.target.read_bytes(), raw)

    def test_existing_directory_missing_parent_repository_refused(self):
        self.target.write_bytes(b'preserve')
        for path in (self.target, self.root, self.root/'absent'/'x', ROOT/'new-output.json'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                output.check_path(path)
        self.assertEqual(self.target.read_bytes(), b'preserve')

    def test_dangling_and_ancestor_symlinks_refused(self):
        link = self.root/'link'
        try:
            link.symlink_to(self.root/'absent')
            directory = self.root/'dirlink'
            directory.symlink_to(self.root, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest('symlinks unavailable')
        for path in (link, directory/'new.json'):
            with self.assertRaisesRegex(ValueError, 'symlink'):
                output.check_path(path)
        self.assertFalse((self.root/'absent').exists())

    def test_final_exclusive_create_refuses_racing_file(self):
        original = Path.open
        def racing(path, mode='r', *args, **kwargs):
            if path == self.target and mode == 'xb':
                self.target.write_bytes(b'other writer')
            return original(path, mode, *args, **kwargs)
        with patch.object(Path, 'open', racing):
            code, stdout, _ = self.emit(b'new')
        self.assertEqual((code, stdout), (1, b''))
        self.assertEqual(self.target.read_bytes(), b'other writer')

    def test_write_and_close_errors_keep_partial_file_without_receipt(self):
        original = Path.open
        for phase in ('write', 'close', 'short'):
            self.target = self.root/phase
            class Failing:
                def __enter__(inner):
                    inner.stream = original(self.target, 'xb')
                    return inner
                def write(inner, raw):
                    inner.stream.write(raw[:2])
                    if phase == 'write': raise OSError('synthetic write failure')
                    if phase == 'short': return 2
                    return len(raw)
                def __exit__(inner, *args):
                    inner.stream.close()
                    if phase == 'close': raise OSError('synthetic close failure')
            def opened(path, mode='r', *args, **kwargs):
                return Failing() if path == self.target and mode == 'xb' else original(path, mode, *args, **kwargs)
            with patch.object(Path, 'open', opened):
                code, stdout, _ = self.emit(b'payload')
            self.assertEqual((code, stdout), (1, b''))
            self.assertEqual(self.target.read_bytes(), b'pa')

    def test_output_and_receipt_limits_before_file_creation(self):
        for bound in ('MAX_OUTPUT_BYTES', 'MAX_RECEIPT_BYTES'):
            with patch.object(output, bound, 1):
                code, stdout, _ = self.emit(b'{}')
            self.assertEqual((code, stdout), (1, b''))
            self.assertFalse(self.target.exists())

    def test_every_selected_leaf_parser_has_output_and_shared_emission(self):
        for name in MODULES:
            parser = capture_parser(name)
            for leaf in leaves(parser):
                with self.subTest(parser=leaf.prog):
                    options = {o for a in leaf._actions for o in a.option_strings}
                    if name == 'revise_local' and leaf.prog.endswith(' apply'):
                        self.assertNotIn('--output', options)
                    else:
                        self.assertIn('--output', options)
            tree = ast.parse((ROOT/(name+'.py')).read_text(encoding='utf-8'))
            main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
            self.assertFalse(any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                                 and n.func.attr == 'write' for n in ast.walk(main)))

    def test_preflight_precedes_input_read_and_invalid_input_creates_no_file(self):
        import observation_input
        self.target.write_bytes(b'preserve')
        args = ['observation_input.py', 'missing.json', '--question', 'Fictional', '--topic', 'synthetic', '--output', str(self.target)]
        with patch.object(sys, 'argv', args), patch.object(observation_input, 'load', side_effect=AssertionError('input read')), \
             patch.object(sys, 'stderr', io.StringIO()):
            with self.assertRaises(SystemExit) as raised: observation_input.main()
        self.assertEqual(raised.exception.code, 1)
        self.target = self.root/'absent.json'
        result = self.run_cli('observation_input', *args[1:-1], self.target)
        self.assertEqual((result.returncode, result.stdout), (1, b''))
        self.assertFalse(self.target.exists())

    def run_cli(self, name, *args):
        return subprocess.run([sys.executable, str(ROOT/(name+'.py')), *map(str,args)], cwd=ROOT,
                              capture_output=True, timeout=40, env=dict(os.environ, PYTHONIOENCODING='ascii', PYTHONHASHSEED='0'))

    def test_ascii_console_and_subcommand_stdout_file_equality(self):
        for name, args in (
            ('research_workflow', ['examples/observed-corpus.json', '--question', 'Fictional 한국어 µ', '--topic', 'model design']),
            ('journey_inputs', ['template']),
        ):
            self.target = self.root/(name+'.json')
            baseline = self.run_cli(name, *args)
            saved = self.run_cli(name, *args, '--output', self.target)
            self.assertEqual((baseline.returncode, saved.returncode), (0,0), saved.stderr)
            self.assertEqual(self.target.read_bytes(), baseline.stdout)
            self.assertEqual(json.loads(saved.stdout)['sha256'], hashlib.sha256(baseline.stdout).hexdigest())

    def test_journey_prepare_inspect_html_saved_chain(self):
        from tests.test_journey_inputs import JourneyInputTests
        case = JourneyInputTests(); case.setUp(); self.addCleanup(case.doCleanups)
        selection = case.root/'selection.json'; selection.write_text(json.dumps(case.selection), encoding='utf-8')
        card = case.root/'card.json'; html = case.root/'view.html'
        prepared = self.run_cli('journey_inputs', 'prepare', selection, '--input-root', case.root, '--output', card)
        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        args = ['inspect',card,'--input-root',case.root,'--format','html']
        baseline = self.run_cli('journey_inputs', *args)
        saved = self.run_cli('journey_inputs', *args, '--output', html)
        self.assertEqual((baseline.returncode,saved.returncode), (0,0),saved.stderr)
        self.assertEqual(html.read_bytes(),baseline.stdout)
        self.assertIsNone(json.loads(saved.stdout)['payload_sha256'])

    def test_converted_result_modes_save_existing_exact_bytes(self):
        from tests.test_cli_utf8_output import CliUtf8OutputTests
        case = CliUtf8OutputTests(); case.setUp(); self.addCleanup(case.doCleanups)
        for index, (name, args, expected) in enumerate(case.cases):
            if name == 'revise_local' and args[0] == 'apply': continue
            with self.subTest(module=name, mode=args[0]):
                path = self.root/(str(index)+'.json')
                code, receipt, errors = case.run_main(name, args+['--output',str(path)])
                self.assertEqual((code,errors), (0,''))
                self.assertEqual(path.read_bytes(),case.expected_bytes(name,expected))
                self.assertEqual(json.loads(receipt)['payload_sha256'], payload_sha256(expected))

    def test_cli_helper_names_resolve_to_shared_functions(self):
        for name in MODULES:
            module = importlib.import_module(name)
            with self.subTest(module=name):
                self.assertIs(module.emit, output.emit)
                self.assertIs(module.add_output_argument, output.add_output_argument)
                helper = module.preflight_output if name == 'prepare_local_manifest' else module.preflight
                self.assertIs(helper, output.preflight)

    def test_command_reference_usage_matches_parsers(self):
        doc = (ROOT/'docs/COMMANDS.md').read_text(encoding='utf-8')
        def check(parser):
            self.assertIn(' '.join(parser.format_usage().split()), doc)
            for action in parser._actions:
                if isinstance(action, argparse._SubParsersAction):
                    for child in action.choices.values(): check(child)
        for name in MODULES:
            with self.subTest(module=name), patch.object(sys, 'argv', [name+'.py']):
                check(capture_parser(name))

    def test_research_journey_html_direct_stdout_file_equality(self):
        from tests.test_journey_inputs import JourneyInputTests
        case = JourneyInputTests(); case.setUp(); self.addCleanup(case.doCleanups)
        import research_journey
        args = [case.path(name) for name in research_journey.INPUT_NAMES]
        args += ['--pattern-id', 'comparison', '--format', 'html', '--review', case.path('declared_review')]
        baseline = self.run_cli('research_journey', *args)
        saved = self.run_cli('research_journey', *args, '--output', self.target)
        self.assertEqual((baseline.returncode, saved.returncode), (0, 0), saved.stderr)
        self.assertEqual(self.target.read_bytes(), baseline.stdout)
        self.assertIsNone(json.loads(saved.stdout)['payload_sha256'])

    def test_documented_guide_commands_execute_verbatim(self):
        doc = (ROOT/'docs/EXCLUSIVE_OUTPUT.md').read_text(encoding='utf-8')
        for block in re.findall(r'```sh\n(.*?)```', doc, re.S):
            import shlex
            for line in block.splitlines():
                if not line.strip(): continue
                tokens = shlex.split(line)
                self.assertEqual(tokens[0], 'python')
                result = subprocess.run([sys.executable, *[x.replace('OUTPUT',str(self.root)) for x in tokens[1:]]],
                                        cwd=ROOT,capture_output=True,timeout=30)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertEqual(json.loads(result.stdout)['status'],'SAVED')
