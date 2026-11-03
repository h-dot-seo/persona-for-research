import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from strict_json import loads


class StrictJsonTests(unittest.TestCase):
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
