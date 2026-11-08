import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from verify_manifest import verify


class ManifestTests(unittest.TestCase):
    def fixture(self, root, paths=('allowed.txt',)):
        rows = []
        for name in paths:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'synthetic public fixture\n')
            rows.append(dict(path=name, bytes=path.stat().st_size,
                             sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        manifest = dict(files=rows, file_count=len(rows))
        (root / 'PUBLICATION_MANIFEST.json').write_text(json.dumps(manifest))
        return manifest

    def test_exact_inventory_and_unlisted_ordinary_text(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            self.assertEqual(verify(root), [])
            (root / 'unexpected-notes.txt').write_text('synthetic unreviewed conversation-like text')
            self.assertIn('unexpected-notes.txt: unlisted release file', verify(root))

    def test_missing_and_changed_bytes_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            (root / 'allowed.txt').write_text('changed')
            self.assertIn('allowed.txt: size/hash mismatch', verify(root))
            (root / 'allowed.txt').unlink()
            self.assertIn('allowed.txt: missing', verify(root))

    def test_noncanonical_paths_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = self.fixture(root)
            for path in ('../outside.txt', '/absolute.txt', 'a/../allowed.txt', './allowed.txt',
                         'a//b', 'C:relative.txt', 'a\\b', '__pycache__/x', '.git/config'):
                manifest['files'][0]['path'] = path
                (root / 'PUBLICATION_MANIFEST.json').write_text(json.dumps(manifest))
                self.assertIn('unsafe or noncanonical manifest path', verify(root))

    def test_duplicate_paths_and_invalid_schema_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = self.fixture(root)
            manifest['files'] *= 2
            (root / 'PUBLICATION_MANIFEST.json').write_text(json.dumps(manifest))
            self.assertIn('duplicate manifest path: allowed.txt', verify(root))
            (root / 'PUBLICATION_MANIFEST.json').write_text('{"files":[],"files":[],"file_count":0}')
            self.assertTrue(verify(root))

    def test_only_documented_metadata_excluded(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            for name in ('.git/config', '__pycache__/fixture.pyc'):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('synthetic metadata')
            self.assertEqual(verify(root), [])
            (root / '__pycache__/notes.txt').write_text('synthetic unlisted notes')
            self.assertIn('__pycache__/notes.txt: unlisted release file', verify(root))
            (root / '.unlisted').write_text('synthetic')
            self.assertIn('.unlisted: unlisted release file', verify(root))

    def test_case_alias_cannot_substitute_for_exact_inventory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = self.fixture(root)
            alias = dict(manifest['files'][0], path='ALLOWED.TXT')
            manifest['files'].append(alias)
            manifest['file_count'] = 2
            (root / 'PUBLICATION_MANIFEST.json').write_text(json.dumps(manifest))
            self.assertIn('ALLOWED.TXT: not in exact release inventory', verify(root))

    def test_file_and_directory_symlinks_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'release'
            root.mkdir()
            self.fixture(root)
            outside = Path(directory) / 'outside'
            outside.mkdir()
            (outside / 'synthetic.txt').write_text('synthetic outside release')
            try:
                (root / 'link.txt').symlink_to(outside / 'synthetic.txt')
                (root / 'linked').symlink_to(outside, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest('symlink creation unavailable on this test host')
            errors = verify(root)
            self.assertIn('link.txt: symlink not allowed', errors)
            self.assertIn('linked: symlink not allowed', errors)
            manifest_path = root / 'PUBLICATION_MANIFEST.json'
            manifest = json.loads(manifest_path.read_text())
            for name in ('link.txt', 'linked/synthetic.txt'):
                manifest['files'].append(dict(path=name, bytes=1, sha256='0' * 64))
            manifest['file_count'] = len(manifest['files'])
            manifest_path.write_text(json.dumps(manifest))
            original_read = Path.read_bytes
            def guarded_read(path):
                if path in (root / 'link.txt', root / 'linked/synthetic.txt'):
                    raise AssertionError('symlink content read')
                return original_read(path)
            with patch.object(Path, 'read_bytes', guarded_read):
                errors = verify(root)
            self.assertIn('link.txt: symlink path not allowed', errors)
            self.assertIn('linked/synthetic.txt: symlink path not allowed', errors)


if __name__ == '__main__':
    unittest.main()
