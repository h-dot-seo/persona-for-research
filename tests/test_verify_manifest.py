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


class TrustedRootCLITests(unittest.TestCase):
    ROOT = Path(__file__).resolve().parents[1]

    def run_cli(self, script, *args, cwd=None):
        import subprocess
        import sys
        return subprocess.run([sys.executable, str(self.ROOT/script), *map(str,args)],
                              cwd=cwd, capture_output=True, timeout=30)

    def target(self, root):
        root.mkdir()
        for name in ('verify_manifest.py','audit_publication.py','strict_json.py'):
            (root/name).write_text('raise RuntimeError("TARGET_CODE_MUST_NOT_RUN")\n')
        rows=[dict(path=p.name,bytes=len(p.read_bytes()),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
              for p in sorted(root.iterdir())]
        (root/'PUBLICATION_MANIFEST.json').write_text(json.dumps(dict(files=rows,file_count=len(rows))))

    def test_other_root_is_data_not_executed_and_read_only(self):
        from audit_publication import audit
        with tempfile.TemporaryDirectory() as td:
            target=Path(td)/'한국어 target with spaces';self.target(target)
            before={p.name:p.read_bytes() for p in target.iterdir()}
            verified=self.run_cli('verify_manifest.py',target,cwd=target)
            scanned=self.run_cli('audit_publication.py',target,cwd=target)
            self.assertEqual(verified.returncode,0,verified.stderr)
            self.assertEqual(json.loads(verified.stdout),dict(valid=True,errors=[]))
            self.assertEqual(scanned.returncode,0,scanned.stderr)
            self.assertEqual(json.loads(scanned.stdout),audit(target))
            self.assertEqual(before,{p.name:p.read_bytes() for p in target.iterdir()})

    def test_relative_root_and_invalid_inventory(self):
        with tempfile.TemporaryDirectory() as td:
            target=Path(td)/'target';self.target(target)
            (target/'extra.txt').write_text('synthetic extra')
            result=self.run_cli('verify_manifest.py','target',cwd=td)
            self.assertEqual(result.returncode,1)
            self.assertFalse(json.loads(result.stdout)['valid'])
            self.assertIn('extra.txt: unlisted release file',json.loads(result.stdout)['errors'])

    def test_audit_existing_prohibited_asset_contract(self):
        with tempfile.TemporaryDirectory() as td:
            target=Path(td)/'target';self.target(target)
            (target/'synthetic.db').write_text('not a real database')
            result=self.run_cli('audit_publication.py',target)
            self.assertEqual(result.returncode,1)
            self.assertIn('synthetic.db: prohibited public asset',json.loads(result.stdout)['errors'])

    def test_invalid_root_is_usage_error_not_empty_scan(self):
        with tempfile.TemporaryDirectory() as td:
            file=Path(td)/'file';file.write_text('synthetic')
            for script in ('verify_manifest.py','audit_publication.py'):
                for path in (file,Path(td)/'missing'):
                    with self.subTest(script=script,path=path):
                        result=self.run_cli(script,path)
                        self.assertEqual(result.returncode,2)
                        self.assertEqual(result.stdout,b'')
                        self.assertIn(b'ROOT must be an existing directory',result.stderr)
                        self.assertNotIn(b'Traceback',result.stderr)

    def test_help_never_calls_inspection(self):
        import verify_manifest, audit_publication
        for module,function in ((verify_manifest,'verify'),(audit_publication,'audit')):
            with patch.object(module,function,side_effect=AssertionError('inspection during help')):
                with self.assertRaises(SystemExit) as caught:module.main(['--help'])
                self.assertEqual(caught.exception.code,0)

    def test_default_output_and_exit_match_existing_api_from_other_cwd(self):
        from audit_publication import audit
        import os
        with tempfile.TemporaryDirectory() as td:
            for script,obj in (('verify_manifest.py',dict(valid=not verify(self.ROOT),errors=verify(self.ROOT))),
                               ('audit_publication.py',audit(self.ROOT))):
                result=self.run_cli(script,cwd=td)
                expected=json.dumps(obj,ensure_ascii=False,indent=2) if script.startswith('audit') else json.dumps(obj)
                expected=(expected+'\n').replace('\n',os.linesep).encode('utf-8')
                self.assertEqual(result.stdout,expected)
                self.assertEqual(result.returncode,int(not obj.get('pass',obj.get('valid'))))
                self.assertEqual(result.stderr,b'')

class WorkflowContractTests(unittest.TestCase):
    """Pin this small checked-in workflow contract without a YAML dependency."""
    def test_only_main_push_and_pull_requests_trigger_ci(self):
        workflow = (Path(__file__).resolve().parents[1] / '.github/workflows/tests.yml').read_text()
        self.assertEqual(workflow.split('on:\n', 1)[1].split('permissions:', 1)[0],
                         '  push:\n    branches: ["main"]\n  pull_request:\n')

    def test_four_platform_jobs_remain_read_only(self):
        workflow = (Path(__file__).resolve().parents[1] / '.github/workflows/tests.yml').read_text()
        self.assertIn('permissions:\n  contents: read\njobs:', workflow)
        self.assertIn('          persist-credentials: false\n', workflow)
        self.assertIn('        os: [ubuntu-latest, windows-latest]\n', workflow)
        self.assertIn('        python: ["3.10", "3.12"]\n', workflow)
        self.assertIn('      fail-fast: false\n', workflow)
        self.assertIn('    timeout-minutes: 15\n', workflow)
        self.assertEqual([line.strip() for line in workflow.splitlines() if line.strip().startswith('- run:')],
                         ['- run: python -m unittest discover -v',
                          '- run: python audit_publication.py',
                          '- run: python verify_manifest.py'])


if __name__ == '__main__':
    unittest.main()
