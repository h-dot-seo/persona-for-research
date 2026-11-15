"""Repository rights-state consistency, not legal/license/SPDX validation."""
import copy
import json
from pathlib import Path, PurePosixPath
import tempfile
import unittest

from strict_json import load
from verify_manifest import inventory, portable_path

ROOT = Path(__file__).resolve().parents[1]
STATEMENTS = (
    ('RIGHTS.md', 'A reuse license has not been selected'),
    ('README.md', 'No license has been selected by the owner yet'),
    ('docs/README.ko.md', '라이선스는 아직 선택되지 않았습니다'),
    ('docs/WORKFLOWS.md', 'No license has been selected by the owner yet'),
)


def license_name(path):
    """Explicit mechanical naming scope; never infer rights from file contents."""
    name = PurePosixPath(path).name.casefold()
    return any(name == stem or name.startswith(stem + '.') for stem in ('license', 'copying'))


def consistency_errors(root):
    """Test-only inspection of a repository tree, never a published CLI/checker."""
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        return ['root must be a real directory']
    actual, errors, complete = inventory(root)
    if errors or not complete:
        return ['inventory contains unsafe or unreadable entries']
    try:
        manifest = load(root / 'PUBLICATION_MANIFEST.json')
        if type(manifest) is not dict or type(manifest.get('files')) is not list:
            return ['manifest object and files array required']
        label = manifest.get('license_status')
        if type(label) is not str or not label.strip():
            return ['nonblank license_status string required']
        paths = []
        for row in manifest['files']:
            if type(row) is not dict or not portable_path(row.get('path')):
                return ['manifest paths must be canonical portable relative paths']
            paths.append(row['path'])
        if len(paths) != len(set(paths)):
            return ['duplicate manifest paths']
        if len(paths) != len({path.casefold() for path in paths}):
            return ['case-colliding manifest paths']
        states = [needle in ' '.join((root / name).read_text(encoding='utf-8').split())
                  for name, needle in STATEMENTS]
    except (OSError, ValueError, TypeError, UnicodeError):
        return ['manifest or statement files unreadable/invalid']
    if len(actual) != len({path.casefold() for path in actual}):
        return ['case-colliding tree paths']
    listed = {path for path in paths if license_name(path)}
    present = {path for path in actual if license_name(path)}
    unselected = label == 'NOT_SELECTED'
    if any(state != unselected for state in states):
        errors.append('four statement signals and manifest status disagree')
    if unselected:
        if listed or present:
            errors.append('unselected state must have no listed or actual license/copying files')
    elif len(listed) != 1 or len(present) != 1 or listed != present:
        errors.append('selected state needs one identical listed and actual license/copying path')
    return errors


class RightsConsistencyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='rights consistency 한글 ')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        for name, needle in STATEMENTS:
            path = self.root / name; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(needle+'\n', encoding='utf-8')
        self.manifest = dict(license_status='NOT_SELECTED', files=[dict(path=name) for name, _ in STATEMENTS])
        self.save()

    def save(self):
        (self.root/'PUBLICATION_MANIFEST.json').write_bytes((json.dumps(self.manifest, ensure_ascii=False)+'\n').encode('utf-8'))

    def selected(self, filename='LICENSE'):
        # A fictional state marker, not a selected/recommended real license.
        self.manifest['license_status'] = 'SYNTHETIC_SELECTED_STATE'
        for name, _ in STATEMENTS:
            (self.root/name).write_text('Synthetic alternate state for this test only.\n', encoding='utf-8')
        (self.root/filename).parent.mkdir(parents=True, exist_ok=True)
        (self.root/filename).write_bytes(b'Synthetic fixture, not a license grant.\n')
        self.manifest['files'].append(dict(path=filename)); self.save()

    def test_current_repository_signals_are_consistent_not_policy_fixed(self):
        self.assertEqual(consistency_errors(ROOT), [])

    def test_unselected_and_synthetic_selected_states(self):
        self.assertEqual(consistency_errors(self.root), [])
        self.selected(); self.assertEqual(consistency_errors(self.root), [])

    def test_each_statement_partial_transition_is_rejected(self):
        for name, needle in STATEMENTS:
            original=(self.root/name).read_bytes()
            (self.root/name).write_text('Synthetic alternate statement.\n', encoding='utf-8')
            self.assertTrue(consistency_errors(self.root), name)
            (self.root/name).write_bytes(original)
        self.selected()
        for name, needle in STATEMENTS:
            original=(self.root/name).read_bytes()
            (self.root/name).write_text(needle+'\n', encoding='utf-8')
            self.assertTrue(consistency_errors(self.root), name)
            (self.root/name).write_bytes(original)

    def test_manifest_only_and_file_only_transitions_reject(self):
        self.manifest['license_status']='SYNTHETIC_SELECTED_STATE';self.save()
        self.assertTrue(consistency_errors(self.root))
        self.manifest['license_status']='NOT_SELECTED';self.save()
        (self.root/'COPYING').write_bytes(b'synthetic')
        self.assertTrue(consistency_errors(self.root))
        (self.root/'COPYING').unlink()
        self.manifest['files'].append(dict(path='COPYING'));self.save()
        self.assertTrue(consistency_errors(self.root))

    def test_selected_missing_or_duplicate_or_mismatched_paths_reject(self):
        self.selected()
        saved=copy.deepcopy(self.manifest)
        self.manifest['files'].append(dict(path='COPYING'));self.save()
        (self.root/'COPYING').write_bytes(b'synthetic')
        self.assertTrue(consistency_errors(self.root))
        (self.root/'COPYING').unlink();self.manifest=saved;self.save()
        (self.root/'LICENSE').rename(self.root/'COPYING')
        self.assertTrue(consistency_errors(self.root))
        (self.root/'COPYING').unlink();self.assertTrue(consistency_errors(self.root))

    def test_empty_wrongtype_labels_and_manifest_shapes_reject(self):
        for value in ('', ' \t\n', None, False, 1, [], {}):
            self.manifest['license_status']=value;self.save()
            self.assertTrue(consistency_errors(self.root), repr(value))
        for value in (None, [], {'license_status':'NOT_SELECTED','files':{}}):
            (self.root/'PUBLICATION_MANIFEST.json').write_text(json.dumps(value),encoding='utf-8')
            self.assertTrue(consistency_errors(self.root))

    def test_strict_json_duplicate_keys_and_constants_reject(self):
        for raw in (b'{"license_status":"NOT_SELECTED","license_status":"other","files":[]}',
                    b'{"license_status":NaN,"files":[]}', b'{"license_status":Infinity,"files":[]}', b'{'):
            (self.root/'PUBLICATION_MANIFEST.json').write_bytes(raw)
            self.assertTrue(consistency_errors(self.root))

    def test_whitespace_normalization_and_explicit_utf8(self):
        for name, needle in STATEMENTS:
            (self.root/name).write_text(' \r\n\t'.join(needle.split())+'\n',encoding='utf-8')
        self.assertEqual(consistency_errors(self.root), [])
        from unittest.mock import patch
        original=Path.read_text;calls=[]
        def read(path,*args,**kwargs):
            if path.name!='PUBLICATION_MANIFEST.json':calls.append(kwargs.get('encoding'))
            return original(path,*args,**kwargs)
        with patch.object(Path,'read_text',read):self.assertEqual(consistency_errors(self.root),[])
        self.assertEqual(calls,['utf-8']*4)

    def test_unsafe_duplicate_and_case_collision_manifest_paths_reject(self):
        original=copy.deepcopy(self.manifest)
        for path in ('../LICENSE','/LICENSE','sub/../LICENSE','sub\\LICENSE','./LICENSE','LICENSE:stream','.git/LICENSE','x\x00LICENSE'):
            self.manifest=copy.deepcopy(original);self.manifest['files'].append(dict(path=path));self.save()
            self.assertTrue(consistency_errors(self.root),repr(path))
        for path in ('RIGHTS.md','rights.md'):
            self.manifest=copy.deepcopy(original);self.manifest['files'].append(dict(path=path));self.save()
            self.assertTrue(consistency_errors(self.root))

    def test_license_name_scope_and_nested_exact_path(self):
        for name in ('LICENSE','copying','LICENSE.txt','Copying.md','terms/LICENSE.rst'):
            self.assertTrue(license_name(name))
        for name in ('LICENSE_NOTES.md','COPYINGRIGHT','docs/rights.md'):
            self.assertFalse(license_name(name))
        self.selected('terms/COPYING.txt');self.assertEqual(consistency_errors(self.root),[])
        self.manifest['files'][-1]['path']='terms/copying.txt';self.save()
        self.assertTrue(consistency_errors(self.root))

    def test_actual_only_duplicates_and_directory_not_license_file(self):
        self.selected()
        (self.root/'COPYING.md').write_bytes(b'synthetic second actual file')
        self.assertTrue(consistency_errors(self.root))
        (self.root/'COPYING.md').unlink()
        (self.root/'LICENSE').unlink(); (self.root/'LICENSE').mkdir()
        self.assertTrue(consistency_errors(self.root))

    def test_missing_status_and_bad_row_shape_reject(self):
        self.manifest.pop('license_status');self.save()
        self.assertTrue(consistency_errors(self.root))
        self.manifest['license_status']='NOT_SELECTED'
        for row in (None, [], 'LICENSE', {}, {'path':None}):
            self.manifest['files']=[row];self.save()
            self.assertTrue(consistency_errors(self.root))

    def test_missing_statement_and_symlink_fail_without_following(self):
        (self.root/'RIGHTS.md').unlink();self.assertTrue(consistency_errors(self.root))
        try:(self.root/'RIGHTS.md').symlink_to(self.root/'README.md')
        except (OSError,NotImplementedError):self.skipTest('symlink creation unavailable')
        self.assertTrue(consistency_errors(self.root))


if __name__=='__main__':unittest.main()
