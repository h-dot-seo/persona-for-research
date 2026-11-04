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
            for raw in ('{"authorized":false,"authorized":true}', '{"value":NaN}'):
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
                    with self.subTest(script=cmd[0], raw=raw):
                        self.assertNotEqual(result.returncode, 0)
                        self.assertNotIn('Traceback', result.stderr)
                        if cmd[0] == 'persona.py':
                            self.assertFalse(json.loads(result.stdout)['mechanically_valid'])
                        else:
                            self.assertEqual(result.stdout, '')

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


if __name__ == '__main__':
    unittest.main()
