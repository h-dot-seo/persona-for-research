"""Synthetic private folder inventories, never content approval."""
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import folder_inventory as f

ROOT = Path(__file__).resolve().parents[1]


class FolderInventoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='inventory space ')
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base/'folder'
        self.root.mkdir()
        (self.root/'nested').mkdir()
        (self.root/'nested'/'한국어.txt').write_bytes(b'a\r\nb\n')
        (self.root/'commands.json').write_bytes(b'not JSON; inert argv /private/home\n')
        (self.root/'READY.json').write_bytes(b'null\n')

    def cli(self, *args):
        return subprocess.run([sys.executable, str(ROOT/'folder_inventory.py'), *map(str, args)], capture_output=True)

    def test_determinism_raw_hash_and_no_root_or_argv(self):
        first = f.encoded(f.declare(self.root))
        self.assertEqual(first, f.encoded(f.declare(self.root)))
        value = json.loads(first)
        self.assertNotIn(str(self.root), first.decode())
        self.assertNotIn('/private/home', first.decode())
        row = next(x for x in value['files'] if x['path'].endswith('.txt'))
        self.assertEqual(row['sha256'], hashlib.sha256(b'a\r\nb\n').hexdigest())
        self.assertEqual(row['bytes'], 5)
        self.assertFalse(value['llm_used']); self.assertFalse(value['commands_executed'])
        self.assertEqual(value['content_bindings_verified'], 'NOT_PERFORMED')

    def test_missing_changed_unlisted_and_cli_failure_report(self):
        value = f.declare(self.root)
        manifest = self.base/'manifest.json'; manifest.write_bytes(f.encoded(value))
        (self.root/'READY.json').unlink()
        (self.root/'commands.json').write_bytes(b'changed')
        (self.root/'new').write_bytes(b'')
        report = f.verify(value, self.root)
        self.assertEqual(report['missing'], ['READY.json'])
        self.assertEqual(report['changed'], ['commands.json'])
        self.assertEqual(report['unlisted'], ['new'])
        result = self.cli('verify', manifest, '--root', self.root)
        self.assertEqual(result.returncode, 1); self.assertEqual(result.stderr, b'')
        self.assertEqual(json.loads(result.stdout), report)
        text = self.cli('verify', manifest, '--root', self.root, '--format', 'text')
        self.assertEqual(text.returncode, 1); self.assertIn(b'commands.json: size/hash mismatch', text.stdout)

    def test_declare_verify_roundtrip_and_empty(self):
        output = self.base/'inventory.json'
        result = self.cli('declare', self.root, '--output', output)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'], 'SAVED')
        result = self.cli('verify', output, '--root', self.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)['valid'])
        empty = self.base/'empty'; empty.mkdir()
        self.assertTrue(f.verify(f.declare(empty), empty)['valid'])

    def test_malformed_manifest_fail_closed(self):
        base = f.declare(self.root)
        bads = []
        for key, val in [('schema', 'other'), ('llm_used', 0), ('files', None), ('boundary', 'approval')]:
            bad = copy.deepcopy(base); bad[key] = val; bads.append(bad)
        for key, val in [('path', '../escape'), ('path', 'a\\b'), ('path', 'a\n'), ('path', '.'), ('bytes', True), ('bytes', -1), ('sha256', 'A'*64)]:
            bad = copy.deepcopy(base); bad['files'][0][key] = val; bads.append(bad)
        bad = copy.deepcopy(base); bad['files'].append(bad['files'][0]); bads.append(bad)
        bad = copy.deepcopy(base); bad['files'].reverse(); bads.append(bad)
        for bad in bads:
            with self.subTest(bad=bad), self.assertRaises(ValueError): f.verify(bad, self.root)

    def test_limits(self):
        with patch.object(f, 'MAX_FILES', 2), self.assertRaises(ValueError): f.declare(self.root)
        with patch.object(f, 'MAX_DIRECTORIES', 1), self.assertRaises(ValueError): f.declare(self.root)
        total = sum(x['bytes'] for x in f.declare(self.root)['files'])
        with patch.object(f, 'MAX_TOTAL_BYTES', total): f.declare(self.root)
        with patch.object(f, 'MAX_TOTAL_BYTES', total-1), self.assertRaises(ValueError): f.declare(self.root)
        with patch.object(f, 'MAX_REPORT_BYTES', 30), self.assertRaises(ValueError): f.declare(self.root)

    def test_reject_git_cache_and_special(self):
        for name in ('.git', '__pycache__', '.pytest_cache'):
            p = self.root/name; p.mkdir()
            with self.assertRaises(ValueError): f.declare(self.root)
            p.rmdir()
        if hasattr(os, 'mkfifo'):
            p = self.root/'fifo'; os.mkfifo(p)
            with self.assertRaises(ValueError): f.declare(self.root)

    def test_unsafe_names(self):
        for name in ('a\nb', 'a\u200bb', '../outside', 'a//b', 'a/./b', '/absolute', 'C:foo', 'a\\b'):
            with self.subTest(name=name), self.assertRaises(ValueError): f.relative(name)

    def test_symlink_file_directory_root_and_output_parent(self):
        link = self.base/'link'
        try: link.symlink_to(self.root, target_is_directory=True)
        except OSError as exc: self.skipTest(str(exc))
        with self.assertRaises(ValueError): f.declare(link)
        with self.assertRaises(ValueError): f.output_path(link/'out', self.root)
        inner = self.root/'redirect'; inner.symlink_to(self.base/'outside')
        with self.assertRaises((ValueError, OSError)): f.declare(self.root)

    @unittest.skipUnless(os.name == 'nt', 'Windows junction creation requires Windows')
    def test_windows_junction(self):
        outside = self.base/'outside'; outside.mkdir()
        junction = self.root/'junction'
        made = subprocess.run(['cmd', '/c', 'mklink', '/J', str(junction), str(outside)], capture_output=True)
        if made.returncode: self.skipTest('junction creation unavailable')
        try:
            with self.assertRaises(ValueError): f.declare(self.root)
            with self.assertRaises(ValueError): f.output_path(junction/'out', self.root)
        finally: os.rmdir(junction)

    def test_exclusive_and_inside_output_no_partial_stdout(self):
        for path in (self.root/'inventory.json', ROOT/'never-create-inventory.json', self.base/'missing'/'out'):
            result = self.cli('declare', self.root, '--output', path)
            self.assertEqual(result.returncode, 1); self.assertEqual(result.stdout, b'')
            self.assertNotIn(b'Traceback', result.stderr); self.assertFalse(path.exists())
        existing = self.base/'existing'; existing.write_bytes(b'keep')
        result = self.cli('declare', self.root, '--output', existing)
        self.assertEqual(result.returncode, 1); self.assertEqual(existing.read_bytes(), b'keep')
        self.assertEqual(result.stdout, b'')

    def test_manifest_read_budget(self):
        manifest = self.base/'huge'; manifest.write_bytes(b' '* (f.MAX_REPORT_BYTES + 1))
        output = self.base/'out'
        result = self.cli('verify', manifest, '--root', self.root, '--output', output)
        self.assertEqual(result.returncode, 1); self.assertEqual(result.stdout, b''); self.assertFalse(output.exists())

    def test_manifest_over_eight_mib_roundtrip_and_input_unchanged(self):
        raw = f.encoded(f.declare(self.root))
        manifest = self.base/'padded.json'
        padded = raw + b' ' * (8 * 1024 * 1024)
        manifest.write_bytes(padded)
        before = {str(p): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        result = self.cli('verify', manifest, '--root', self.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)['valid'])
        self.assertEqual(manifest.read_bytes(), padded)
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_mismatch_saved_report_exit_one(self):
        manifest = self.base/'manifest.json'; manifest.write_bytes(f.encoded(f.declare(self.root)))
        (self.root/'READY.json').write_bytes(b'changed')
        output = self.base/'report.json'
        result = self.cli('verify', manifest, '--root', self.root, '--output', output)
        self.assertEqual(result.returncode, 1); self.assertEqual(result.stderr, b'')
        self.assertEqual(json.loads(result.stdout)['status'], 'SAVED')
        self.assertFalse(json.loads(output.read_bytes())['valid'])

    def test_reparse_attribute_without_symlink_is_rejected(self):
        from types import SimpleNamespace
        real = Path.stat
        def mocked(path, *args, **kwargs):
            info = real(path, *args, **kwargs)
            if path == self.root/'nested':
                return SimpleNamespace(st_mode=info.st_mode, st_file_attributes=0x400)
            return info
        with patch.object(Path, 'stat', mocked), self.assertRaises(ValueError): f.declare(self.root)

    def test_detect_enumeration_change(self):
        real = f.read_source_bytes
        def change(path, **kwargs):
            raw = real(path, **kwargs)
            (self.root/'added').write_bytes(b'new')
            return raw
        with patch.object(f, 'read_source_bytes', side_effect=change), self.assertRaises(ValueError): f.declare(self.root)

    def test_guide_native_path_after_shlex(self):
        guide = (ROOT/'docs/FOLDER_INVENTORY.md').read_text(encoding='utf-8')
        blocks = re.findall(r'```sh\n(.*?)```', guide, re.S)
        self.assertEqual(len(blocks), 1)
        for line in blocks[0].splitlines():
            if not line.strip(): continue
            args = shlex.split(line)
            self.assertEqual(args[0], 'python'); self.assertNotIn('>', args)
            args = [sys.executable, str(ROOT/args[1]), *[a.replace('OUTPUT', str(self.base)) for a in args[2:]]]
            result = subprocess.run(args, cwd=ROOT, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
        original = shlex.split('python folder_inventory.py declare OUTPUT/demo --output OUTPUT/inventory.json')
        native = [a.replace('OUTPUT', r'C:\Users\Example Name') for a in original]
        self.assertEqual(native[3], r'C:\Users\Example Name/demo')


if __name__ == '__main__': unittest.main()
