"""Synthetic version labels are bounded display data, never an integrity result."""
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import persona_cli

ROOT = Path(__file__).resolve().parents[1]


class DispatcherVersionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.manifest = self.root / 'PUBLICATION_MANIFEST.json'

    def invoke(self, raw):
        self.manifest.write_bytes(raw)
        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.object(persona_cli, 'ROOT', self.root), contextlib.redirect_stdout(stdout), \
                contextlib.redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as exited:
                persona_cli.main(['--version'])
        return exited.exception.code, stdout.getvalue(), stderr.getvalue()

    def test_version_from_another_directory_has_labels_runtime_and_nonclaims(self):
        result = subprocess.run([sys.executable, str(ROOT / 'persona_cli.py'), '--version'],
                                cwd=self.root, capture_output=True, timeout=30,
                                env={**os.environ, 'PYTHONIOENCODING': 'ascii'})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, b'')
        text = result.stdout.decode('ascii')
        manifest = json.loads((ROOT / 'PUBLICATION_MANIFEST.json').read_bytes())
        self.assertIn('release: ' + json.dumps(manifest['release']), text)
        self.assertIn('Manifest date: ' + manifest['date'], text)
        self.assertIn('Python: ' + '.'.join(map(str, sys.version_info[:3])), text)
        for phrase in ('NOT an integrity check or signature', 'not authenticated',
                       'No file hashes checked', 'python verify_manifest.py', 'network access or file writes'):
            self.assertIn(phrase, text)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_only_labels_are_displayed_without_hash_or_inventory_validation(self):
        raw = json.dumps({'release': 'Fictional "label" α', 'date': '2024-02-29',
                          'files': [{'path': 'nonexistent', 'sha256': 'not-a-hash'}]}).encode()
        code, out, err = self.invoke(raw)
        self.assertEqual((code, err), (0, ''))
        self.assertIn('"Fictional \\"label\\" \\u03b1"', out)
        self.assertNotIn('nonexistent', out)
        self.assertTrue(out.isascii())

    def test_rejects_bad_structure_encoding_numbers_depth_and_duplicate_keys(self):
        good = b'{"release":"Fictional","date":"2026-11-10"}'
        cases = [b'', b'{', b'[]', b'null', b'{}', b'\xff', b'\xef\xbb\xbf' + good,
                 good.decode().encode('utf-16'), good + b' {}',
                 b'{"release":"Fictional","release":"Other","date":"2026-11-10"}',
                 good[:-1] + b',"extra":{"secret\\u001b":1,"secret\\u001b":2}}',
                 good[:-1] + b',"extra":NaN}', good[:-1] + b',"extra":Infinity}',
                 good[:-1] + b',"extra":1e999}',
                 good[:-1] + b',"extra":' + b'[' * 130 + b'0' + b']' * 130 + b'}']
        for raw in cases:
            with self.subTest(raw=raw[:60]):
                code, out, err = self.invoke(raw)
                self.assertEqual((code, out), (1, ''))
                self.assertIn('cannot read version labels', err)
                self.assertNotIn('Traceback', err)
                self.assertNotIn('secret', err)
                self.assertTrue(err.isascii())
                self.assertLess(len(err), 500)

    def test_rejects_bad_release_and_date_labels_without_echoing_them(self):
        for field, values in (
                ('release', [None, 3, True, [], {}, '', ' ', ' leading', 'trailing ',
                             'x' * 129, 'Fictional\nFAKE', 'Fictional\x1b[31m',
                             'Fictional\u202e', 'Fictional\ud800', 'Fictional\x7f']),
                ('date', [None, 3, True, [], {}, '', '2026-11-31', '2026-1-01',
                          '20261110', '2026-W46-2', '2026-11-10\nFAKE'])):
            for value in values:
                with self.subTest(field=field, value=value):
                    labels = {'release': 'Fictional', 'date': '2026-11-10', field: value}
                    code, out, err = self.invoke(json.dumps(labels).encode())
                    self.assertEqual((code, out), (1, ''))
                    self.assertNotIn('FAKE', err)
                    self.assertNotIn('Traceback', err)

    def test_byte_bound_is_inclusive_and_reads_are_bounded(self):
        good = b'{"release":"' + b'x' * 128 + b'","date":"2026-11-10"}'
        bounded = good + b' ' * (persona_cli.MAX_MANIFEST_BYTES - len(good))
        self.assertEqual(self.invoke(bounded)[0], 0)
        self.assertEqual(self.invoke(bounded + b' ')[0:2], (1, ''))
        # A growing file cannot turn the read into an unbounded allocation.
        self.manifest.write_bytes(good)
        stream = mock.MagicMock()
        stream.__enter__.return_value.read.return_value = bounded + b' '
        with mock.patch.object(persona_cli, 'ROOT', self.root), \
                mock.patch.object(Path, 'open', return_value=stream):
            with self.assertRaisesRegex(ValueError, 'cannot read version labels'):
                persona_cli.version_text()
        stream.__enter__.return_value.read.assert_called_once_with(persona_cli.MAX_MANIFEST_BYTES + 1)

    def test_missing_unreadable_directory_and_symlink_manifest_fail_safely(self):
        with mock.patch.object(persona_cli, 'ROOT', self.root):
            with self.assertRaisesRegex(ValueError, 'cannot read version labels'):
                persona_cli.version_text()
            self.manifest.mkdir()
            with self.assertRaisesRegex(ValueError, 'cannot read version labels'):
                persona_cli.version_text()
            self.manifest.rmdir()
            with mock.patch.object(Path, 'lstat', side_effect=PermissionError('PRIVATE\x1b')):
                with self.assertRaises(ValueError) as error:
                    persona_cli.version_text()
                self.assertNotIn('PRIVATE', str(error.exception))
            try:
                self.manifest.symlink_to(self.root / 'missing')
            except (OSError, NotImplementedError):
                return  # Native Windows may not grant symlink creation.
            with self.assertRaisesRegex(ValueError, 'cannot read version labels'):
                persona_cli.version_text()

    def test_help_list_and_forwarded_version_do_not_read_manifest(self):
        with mock.patch.object(persona_cli, 'version_text', side_effect=AssertionError('eager read')):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(persona_cli.main(['list']), 0)
                with self.assertRaises(SystemExit) as exited:
                    persona_cli.main(['--help'])
                self.assertEqual(exited.exception.code, 0)
            with mock.patch.object(persona_cli, 'execute') as execute:
                self.assertEqual(persona_cli.main(['run', 'persona.py', '--version']), 0)
                execute.assert_called_once_with(ROOT / 'persona.py', ['--version'])


if __name__ == '__main__':
    unittest.main()
