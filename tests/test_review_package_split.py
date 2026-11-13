"""Synthetic detached split review integration; no source access or mutation."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import review_package
import split_declaration as split

ROOT = Path(__file__).resolve().parents[1]


class SplitReviewTests(unittest.TestCase):
    def setUp(self):
        self.package = json.loads((ROOT/'examples/trajectory-conditions-package.json').read_text())
        self.draft = json.loads((ROOT/'examples/synthetic-split-declaration.json').read_text())
        self.record = split.freeze(self.draft)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.record_path = self.folder/'private declaration.json'
        self.record_path.write_text(json.dumps(self.record), encoding='utf-8')
        self.package_path = ROOT/'examples/trajectory-conditions-package.json'

    def cli(self, *args):
        return subprocess.run([sys.executable, str(ROOT/'review_package.py'), str(self.package_path),
            '--question', 'Synthetic question?', '--topic', 'model design', *map(str,args)],
            cwd=self.folder, capture_output=True, timeout=60)

    def render(self, **kwargs):
        return review_package.render(self.package, 'Synthetic question?', 'model design', **kwargs)

    def test_default_output_unchanged_and_no_split_access(self):
        baseline=self.render()
        with patch.object(split, 'status', side_effect=AssertionError('not requested')):
            self.assertEqual(baseline,self.render(split_declaration=None))
        self.assertNotIn('Split declaration report',baseline)

    def test_reuses_complete_status_renderer_without_mutation(self):
        before=copy.deepcopy((self.package,self.record))
        text=self.render(split_declaration=self.record)
        self.assertIn(split.render(split.status(self.package,record=self.record)),text)
        self.assertIn('PACKAGE_WITHIN_DECLARED_TRAINING',text)
        self.assertEqual(before,(self.package,self.record))
        for name in ('synthetic-holdout-only','synthetic-comparator-only','synthetic-excluded-only'):
            self.assertNotIn(name,text)
        self.assertNotIn('CURRENT',text)

    def test_mismatch_is_report_only_and_does_not_change_application(self):
        self.draft['splits']['excluded'].append(self.draft['splits']['training'].pop())
        record=split.freeze(self.draft)
        text=self.render(split_declaration=record)
        self.assertIn('PACKAGE_OUTSIDE_DECLARED_TRAINING',text)
        self.record_path.write_text(json.dumps(record),encoding='utf-8')
        result=self.cli('--split',self.record_path)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn(b'PACKAGE_OUTSIDE_DECLARED_TRAINING',result.stdout)
        self.assertEqual(text.split('Split declaration report')[0],self.render().split('Boundary: curated')[0])

    def test_invalid_or_tampered_record_rejected(self):
        self.record['census_sha256']='0'*64
        with self.assertRaises(ValueError):self.render(split_declaration=self.record)

    def test_cli_preserves_inputs_and_supports_exclusive_output(self):
        original=self.record_path.read_bytes()
        output=self.folder/'review.txt'
        result=self.cli('--split',self.record_path,'--output',output,'--evidence-details')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('PACKAGE_WITHIN_DECLARED_TRAINING',output.read_text())
        self.assertEqual(self.record_path.read_bytes(),original)
        retry=self.cli('--split',self.folder/'missing','--output',output)
        self.assertNotEqual(retry.returncode,0)
        self.assertEqual(original,self.record_path.read_bytes())

    def test_private_parser_errors_have_no_input_values_or_output(self):
        secret='PRIVATE-SPLIT-ID'
        self.record_path.write_text('{"'+secret+'":0,"'+secret+'":1}',encoding='utf-8')
        output=self.folder/'not-created.txt'
        result=self.cli('--split',self.record_path,'--output',output)
        self.assertEqual(result.returncode,1)
        self.assertIn(b'details withheld',result.stderr)
        self.assertNotIn(secret.encode(),result.stdout+result.stderr)
        self.assertFalse(output.exists())

    def test_shared_budget_and_output_limit(self):
        with patch.object(sys,'argv',['review_package.py',str(self.package_path),'--question','q',
               '--topic','t','--split',str(self.record_path)]), patch.object(split,'MAX_INPUT_BYTES',8):
            with self.assertRaises(SystemExit) as raised:review_package.main()
            self.assertEqual(raised.exception.code,1)
        with patch.object(sys,'argv',['review_package.py',str(self.package_path),'--question','q',
               '--topic','t','--split',str(self.record_path)]), patch.object(split,'MAX_OUTPUT_BYTES',8):
            with self.assertRaises(SystemExit) as raised:review_package.main()
            self.assertEqual(raised.exception.code,1)

    def test_symlink_declaration_rejected(self):
        link=self.folder/'link.json'
        try:link.symlink_to(self.record_path)
        except (OSError,NotImplementedError):self.skipTest('symlinks unavailable')
        result=self.cli('--split',link)
        self.assertEqual(result.returncode,1)
        self.assertIn(b'symlink',result.stderr)

    def test_human_records_coexist_without_conflating_the_axes(self):
        result=self.cli('--split',self.record_path,'--human-validation',ROOT/'examples/manual-human-validation.json')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn(b'PACKAGE_WITHIN_DECLARED_TRAINING',result.stdout)
        self.assertIn(b'LABEL_DISTINCT_ONLY',result.stdout)
        self.assertNotIn(b'synthetic-holdout-only',result.stdout)

    def test_all_optional_inputs_share_the_split_reader(self):
        human=ROOT/'examples/manual-human-validation.json'
        paths=[]
        original=split.bounded_reader
        def factory():
            reader=original()
            def read(path):
                paths.append(Path(path))
                return reader(path)
            return read
        with patch.object(sys,'argv',['review_package.py',str(self.package_path),'--question','q',
               '--topic','t','--split',str(self.record_path),'--human-validation',str(human)]), \
               patch.object(split,'bounded_reader',side_effect=factory), patch.object(review_package,'emit'):
            review_package.main()
        self.assertEqual(paths,[self.record_path,self.package_path,human])

    def test_explicit_null_split_fails_before_emitting_review(self):
        self.record_path.write_text('null',encoding='utf-8')
        output=self.folder/'never.txt'
        result=self.cli('--split',self.record_path,'--output',output)
        self.assertEqual(result.returncode,1)
        self.assertEqual(result.stdout,b'')
        self.assertFalse(output.exists())
        self.assertIn(b'missing or unknown fields',result.stderr)
