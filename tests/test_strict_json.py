import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from strict_json import MAX_DIAGNOSTIC_KEY_CODEPOINTS, loads


class StrictJsonTests(unittest.TestCase):
    def duplicate_error(self, key):
        encoded = json.dumps(key, ensure_ascii=True)
        with self.assertRaises(ValueError) as caught:
            loads('{' + encoded + ': 1, ' + encoded + ': 2}')
        return str(caught.exception)

    def test_duplicate_diagnostics_escape_unicode_and_controls(self):
        for key in ('line\nreturn\rtab\t\x00\x1b[31m\x7f',
                    '\u202e\u2066\u2028\u2029', '\ud800 separated \udfff',
                    '한글 café \U0001f680', 'quote"slash\\literal\\n'):
            with self.subTest(key=ascii(key)):
                message = self.duplicate_error(key)
                self.assertEqual(message, 'duplicate JSON object key: ' + json.dumps(key, ensure_ascii=True))
                self.assertTrue(all(32 <= ord(char) <= 126 for char in message))

    def test_duplicate_diagnostics_bound_display_not_keys(self):
        prefix = '\U0001f680' * MAX_DIAGNOSTIC_KEY_CODEPOINTS
        marker = ' [truncated; first 128 Unicode codepoints shown]'
        exact = self.duplicate_error(prefix)
        self.assertNotIn(marker, exact)
        for suffix in ('x', 'y' * 10000):
            message = self.duplicate_error(prefix + suffix)
            self.assertEqual(message, exact + marker)
            self.assertLessEqual(len(message), len('duplicate JSON object key: ') + 2 + 12 * 128 + len(marker))
            self.assertTrue(all(32 <= ord(char) <= 126 for char in message))
        # Matching previews are not matching keys, including far beyond the preview.
        value = {prefix + 'x' * 10000: 1, prefix + 'x' * 9999 + 'y': 2}
        self.assertEqual(loads(json.dumps(value)), value)

    def test_valid_nested_unicode_and_escaped_equivalent_keys(self):
        value = {'한글\U0001f680': [{'\ud800': 'value\u2028\n'}, {'é': [1, None]}]}
        self.assertEqual(loads(json.dumps(value)), value)
        for raw in ('{"é":1,"\\u00e9":2}', '{"🚀":1,"\\ud83d\\ude80":2}'):
            with self.assertRaisesRegex(ValueError, 'duplicate JSON object key:'):
                loads(raw)

    def test_ordinary_cli_duplicate_diagnostics_are_single_line_ascii(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'duplicate.json'
            key = 'unsafe\n\r\t\x1b\u202e\u2028\ud800\U0001f680' + 'x' * 1000
            encoded = json.dumps(key)
            path.write_text('{' + encoded + ': 1, ' + encoded + ': 2}', encoding='ascii')
            commands = [
                ['argument_map.py', str(path), str(path), str(path)],
                ['research_workflow.py', str(path), '--question', 'Question', '--topic', 'model design'],
                ['answer_proposals.py', 'context', str(path), str(path)],
                ['persona.py', str(path), str(path)]]
            for cmd in commands:
                with self.subTest(script=cmd[0]):
                    result = subprocess.run([sys.executable, *cmd], capture_output=True, timeout=20)
                    self.assertNotEqual(result.returncode, 0)
                    if cmd[0] == 'persona.py':
                        report = json.loads(result.stdout)
                        self.assertFalse(report['mechanically_valid'])
                        self.assertEqual(report['errors'], [self.duplicate_error(key)])
                        self.assertEqual(result.stderr, b'')
                    else:
                        self.assertEqual(result.stdout, b'')
                        self.assertTrue(result.stderr.endswith(b'\n'))
                        payload = result.stderr[:-2] if result.stderr.endswith(b'\r\n') else result.stderr[:-1]
                        self.assertEqual(payload, self.duplicate_error(key).encode('ascii'))
                        self.assertTrue(all(32 <= byte <= 126 for byte in payload))
                    self.assertNotIn(b'Traceback', result.stderr)

    def test_duplicate_keys_rejected_at_any_depth(self):
        for raw in ('{"authorized":false,"authorized":true}',
                    '{"paper":{"split":"holdout","split":"training"}}',
                    '{"a":1,"\\u0061":2}'):
            with self.assertRaisesRegex(ValueError, 'duplicate JSON object key'):
                loads(raw)

    def test_nonfinite_and_overflow_numbers_rejected(self):
        for number in ('NaN', 'Infinity', '-Infinity', '1e999', '-1e999'):
            with self.assertRaises(ValueError): loads('{"value":' + number + '}')

    def test_finite_unicode_json_preserved(self):
        value = {'연구': [1, 1.5, True, None, 'synthetic']}
        self.assertEqual(loads(json.dumps(value, ensure_ascii=False).encode('utf-8')), value)

    def test_excessive_nesting_fails_cleanly(self):
        self.assertIsInstance(loads('[' * 100 + '0' + ']' * 100), list)
        with self.assertRaisesRegex(ValueError, 'nesting'):
            loads('[' * 2000 + '0' + ']' * 2000)

    def test_all_cli_boundaries_reject_ambiguous_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'ambiguous.json'
            for raw in ('{"authorized":false,"authorized":true}', '{"value":NaN}', '0' + ' ' * (8 * 1024 * 1024)):
                path.write_text(raw)
                commands = [
                    ['research_workflow.py', str(path), '--question', 'Question', '--topic', 'model design'],
                    ['observation_input.py', str(path), '--question', 'Question', '--topic', 'model design'],
                    ['corpus_files.py', str(path), '--source-root', directory, '--question', 'Question', '--topic', 'model design'],
                    ['compare_releases.py', str(path), str(path)],
                    ['persona.py', str(path), str(path)],
                    ['safe_canonical_read.py', str(path)]]
                for cmd in commands:
                    result = subprocess.run([sys.executable, *cmd], capture_output=True, text=True, timeout=20)
                    with self.subTest(script=cmd[0], raw_size=len(raw)):
                        self.assertNotEqual(result.returncode, 0)
                        self.assertNotIn('Traceback', result.stderr)
                        if cmd[0] == 'persona.py':
                            self.assertFalse(json.loads(result.stdout)['mechanically_valid'])
                        else:
                            self.assertEqual(result.stdout, '')

    def test_bounded_file_exact_default_and_plus_one(self):
        import strict_json
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'bounded.json'
            path.write_bytes(b'0' + b' ' * (strict_json.MAX_INPUT_BYTES - 1))
            self.assertEqual(strict_json.load(path), 0)
            with path.open('ab') as stream:
                stream.write(b' ')
            with self.assertRaisesRegex(strict_json.InputLimitError, '8 MiB'):
                strict_json.load(path)
            path.write_bytes(b'{} ')
            with patch.object(strict_json, 'MAX_INPUT_BYTES', 2):
                with self.assertRaises(strict_json.InputLimitError):
                    strict_json.load(path)
                self.assertEqual(strict_json.load(path, max_bytes=3), {})
            self.assertEqual(strict_json.read_bounded(path, 3), b'{} ')

    def test_bounded_stream_read_limit_short_reads_and_ownership(self):
        import io
        from strict_json import InputLimitError, read_bounded_stream
        class ShortStream(io.BytesIO):
            def __init__(self, raw):
                super().__init__(raw)
                self.requests = []
            def read(self, count=-1):
                self.requests.append(count)
                return super().read(min(count, 2))
        stream = ShortStream(b'123456789')
        with self.assertRaises(InputLimitError):
            read_bounded_stream(stream, 4)
        self.assertEqual(stream.tell(), 5)
        self.assertEqual(stream.requests, [5, 3, 1])
        self.assertFalse(stream.closed)
        self.assertEqual(read_bounded_stream(ShortStream(b'1234'), 4), b'1234')
        self.assertEqual(read_bounded_stream(io.BytesIO(b''), 0), b'')
        for limit in (-1, True, 1.5, None):
            stream = ShortStream(b'0')
            with self.assertRaises(ValueError):
                read_bounded_stream(stream, limit)
            self.assertEqual(stream.requests, [])
        with self.assertRaises(TypeError):
            read_bounded_stream(io.StringIO('0'), 1)

    def test_bounded_diagnostic_escaped_and_no_directory(self):
        import io
        from strict_json import InputLimitError, read_bounded_stream
        label = 'fictional\n\x1b\u202e' + 'x' * 1000
        with self.assertRaises(InputLimitError) as caught:
            read_bounded_stream(io.BytesIO(b'123'), 2, label=label)
        message = str(caught.exception)
        self.assertIn('[truncated;', message)
        self.assertTrue(all(32 <= ord(c) <= 126 for c in message))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'fictional.json'
            path.write_bytes(b'123')
            from strict_json import read_bounded
            with self.assertRaises(InputLimitError) as caught:
                read_bounded(path, 2)
            self.assertNotIn(directory, str(caught.exception))
            self.assertIn('fictional.json', str(caught.exception))

    def test_bounded_original_encodings_preserved(self):
        from strict_json import load
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'encoded.json'
            for encoding in ('utf-8-sig', 'utf-16', 'utf-32'):
                raw = '{"fictional": "é"}'.encode(encoding)
                path.write_bytes(raw)
                self.assertEqual(load(path, max_bytes=len(raw)), {'fictional': 'é'})

    def test_human_reader_preserves_aggregate_budget_and_message(self):
        import human_validation
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'synthetic.json'
            path.write_bytes(b'{}')
            reader = human_validation.bounded_reader(4)
            self.assertEqual(reader(path), {})
            self.assertEqual(reader(path), {})
            with self.assertRaisesRegex(ValueError, '^combined human validation inputs exceed 8 MiB$'):
                reader(path)
            with patch.object(human_validation, 'MAX_INPUT_BYTES', 1):
                with self.assertRaisesRegex(ValueError, 'combined human validation'):
                    human_validation.bounded_reader()(path)
            # Verify the reader requests only the remaining budget, not the whole file.
            with patch.object(human_validation, 'read_bounded', wraps=human_validation.read_bounded) as bounded:
                reader = human_validation.bounded_reader(4)
                reader(path); reader(path)
                self.assertEqual([c.args[1] for c in bounded.call_args_list], [4, 2])

    def test_projection_stdin_exact_budget_original_hash_and_overflow(self):
        import strict_json
        raw = b'{"fictional":true}'
        raw += b' ' * (strict_json.MAX_INPUT_BYTES - len(raw))
        command = [sys.executable, 'safe_canonical_read.py', '-', '--source-kind',
                   'original-bytes', '--expected-original-sha256', hashlib.sha256(raw).hexdigest()]
        result = subprocess.run(command, input=raw, capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['original_hash_verification'], 'VERIFIED')
        result = subprocess.run(command, input=raw + b' ', capture_output=True, timeout=20)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, b'')
        self.assertIn(b'8 MiB', result.stderr)
        self.assertNotIn(b'Traceback', result.stderr)

    def test_manifest_shared_reader_size_rejection(self):
        from verify_manifest import verify
        import strict_json
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'PUBLICATION_MANIFEST.json').write_bytes(b' ' * (strict_json.MAX_INPUT_BYTES + 1))
            errors = verify(root)
            self.assertEqual(len(errors), 1)
            self.assertIn('manifest unreadable or invalid:', errors[0])
            self.assertIn('8 MiB', errors[0])

    def test_original_byte_hash_behavior_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'original.json'
            raw = b'{"rules": ["synthetic"]}\n'
            path.write_bytes(raw)
            command = [sys.executable, 'safe_canonical_read.py', str(path),
                       '--source-kind', 'original-bytes', '--expected-original-sha256']
            success = subprocess.run([*command, hashlib.sha256(raw).hexdigest()], capture_output=True, text=True, timeout=20)
            self.assertEqual(success.returncode, 0, success.stderr)
            self.assertEqual(json.loads(success.stdout)['original_hash_verification'], 'VERIFIED')
            failed = subprocess.run([*command, '0' * 64], capture_output=True, text=True, timeout=20)
            self.assertEqual(failed.returncode, 2)
            self.assertFalse(json.loads(failed.stdout)['projection_emitted'])


class PrivateReaderConsolidationTests(unittest.TestCase):
    MODULES = ('answer_proposals', 'application_proposals', 'argument_proposals',
               'citation_reasoning', 'method_application', 'observation_proposals',
               'pattern_proposals', 'publication_context', 'research_journey',
               'source_recheck', 'model_handoff')

    def call(self, module, path, budget=8 * 1024 * 1024):
        if module.__name__ == 'citation_reasoning':
            return module._load(path, budget)[0]
        return (module.load if module.__name__ == 'model_handoff' else module._load)(path)

    def test_all_wrappers_use_shared_reader_and_keep_errors(self):
        import importlib
        from unittest.mock import patch
        from strict_json import InputLimitError
        for name in self.MODULES:
            module = importlib.import_module(name)
            with self.subTest(name=name), patch.object(module, 'read_bounded', return_value=b'{"ok":true}') as reader:
                self.assertEqual(self.call(module, 'input.json'), {'ok': True})
                self.assertEqual(reader.call_args.args, ('input.json', 8 * 1024 * 1024))
            with self.subTest(name=name), patch.object(module, 'read_bounded', side_effect=InputLimitError('private diagnostic')):
                with self.assertRaises(ValueError) as caught:
                    self.call(module, 'input.json')
                self.assertIn('8 MiB', str(caught.exception))
                self.assertNotIn('private diagnostic', str(caught.exception))

    def test_patchable_module_bounds_and_citation_byte_accounting(self):
        import importlib
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'input.json'
            raw = b'{"x":1}'
            path.write_bytes(raw)
            for name in self.MODULES:
                module = importlib.import_module(name)
                constant = 'MAX_JSON_BYTES' if name == 'source_recheck' else 'MAX_INPUT_BYTES'
                if hasattr(module, constant) and name != 'citation_reasoning':
                    with self.subTest(name=name), patch.object(module, constant, len(raw)):
                        self.assertEqual(self.call(module, path), {'x': 1})
                    with self.subTest(name=name), patch.object(module, constant, len(raw)-1):
                        with self.assertRaisesRegex(ValueError, '8 MiB'):
                            self.call(module, path)
            import citation_reasoning
            self.assertEqual(citation_reasoning._load(path, len(raw)), ({'x': 1}, len(raw)))
            with self.assertRaisesRegex(ValueError, 'combined citation audit'):
                citation_reasoning._load(path, len(raw)-1)

    def test_encoding_and_strict_parser_contracts(self):
        import importlib
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'input.json'
            for raw in ('{"x":"한글"}'.encode('utf-16'), b'\xef\xbb\xbf{"x":"ok"}'):
                path.write_bytes(raw)
                for name in self.MODULES:
                    module = importlib.import_module(name)
                    with self.subTest(name=name, raw=raw):
                        if name == 'research_journey':
                            with self.assertRaises((ValueError, UnicodeError)):
                                self.call(module, path)
                        else:
                            self.assertIn('x', self.call(module, path))
            for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1e999}'):
                path.write_bytes(raw)
                for name in self.MODULES:
                    with self.subTest(name=name, raw=raw), self.assertRaises(ValueError):
                        self.call(importlib.import_module(name), path)

    def test_short_reads_are_accumulated_by_each_wrapper(self):
        import importlib
        import io
        from unittest.mock import patch
        class ShortStream(io.BytesIO):
            def read(self, size=-1):
                return super().read(min(size, 2))
        for name in self.MODULES:
            with self.subTest(name=name), patch('pathlib.Path.open', return_value=ShortStream(b'{"x":1}')):
                self.assertEqual(self.call(importlib.import_module(name), 'input.json'), {'x': 1})

if __name__ == '__main__':
    unittest.main()
