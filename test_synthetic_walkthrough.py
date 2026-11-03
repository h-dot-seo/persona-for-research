import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import synthetic_walkthrough as demo


class SyntheticWalkthroughTests(unittest.TestCase):
    def test_actual_cli_from_other_cwd_with_unicode_spaces_and_all_artifacts(self):
        before={p:p.read_bytes() for p in (demo.ROOT/'examples').rglob('*') if p.is_file()}
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)/'합성 demo output'
            result = subprocess.run([sys.executable, str(demo.ROOT/'synthetic_walkthrough.py'), str(target)],
                cwd=directory, capture_output=True, env=dict(os.environ, PYTHONIOENCODING='ascii'), timeout=30)
            self.assertEqual(result.returncode,0,result.stderr)
            receipt=json.loads(result.stdout)
            self.assertEqual(receipt['command_count'],15)
            self.assertEqual(receipt['answer_review_status'],'ALL_DEFERRED')
            self.assertFalse(receipt['llm_used']); self.assertFalse(receipt['external_transmission'])
            self.assertEqual(receipt['lineage_status'],'CURRENT_REVISION_REPLAY_MATCH')
            self.assertTrue((target/'COMPLETE.json').exists()); self.assertFalse((target/'FAILED.txt').exists())
            for name in receipt['read_first']: self.assertTrue((target/name).is_file())
            commands=json.loads((target/'commands.json').read_text(encoding='utf-8'))
            self.assertEqual(len(commands),15); self.assertTrue(all(c['returncode']==0 for c in commands))
            self.assertTrue(all(Path(c['argv'][1]).parent==demo.ROOT for c in commands))
            self.assertTrue(all(d['decision']=='defer' for d in json.loads((target/'answer-review.json').read_text())['decisions']))
            self.assertIn('NOT_SUPPLIED',(target/'reader-scope.txt').read_text(encoding='utf-8'))
            self.assertIn('AFTER_REFERENCE_YEAR',(target/'review-packet.txt').read_text(encoding='utf-8'))
            self.assertIn('Defeater: NOT_SUPPLIED',(target/'argument-map.txt').read_text(encoding='utf-8'))
            self.assertIn('NO_CITATIONS_SUPPLIED',(target/'argument-map.txt').read_text(encoding='utf-8'))
            baseline=json.loads((target/'baseline.json').read_text()); revised=json.loads((target/'revision.json').read_text())
            self.assertNotEqual(baseline['package']['persona']['version'],revised['package']['persona']['version'])
            self.assertEqual(before,{p:p.read_bytes() for p in before})

    def test_existing_directory_and_files_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'existing';target.mkdir();sentinel=target/'sentinel';sentinel.write_bytes(b'keep')
            with self.assertRaisesRegex(ValueError,'already exists'):demo.run(target)
            self.assertEqual(list(target.iterdir()),[sentinel]);self.assertEqual(sentinel.read_bytes(),b'keep')
            with self.assertRaisesRegex(ValueError,'already exists'):demo.run(sentinel)

    def test_repo_destination_and_missing_parent_reject_before_creation(self):
        target=demo.ROOT/'synthetic-output-forbidden'
        with self.assertRaisesRegex(ValueError,'outside'):demo.run(target)
        self.assertFalse(target.exists())
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError,'parent'):demo.run(Path(directory)/'missing'/'output')
            self.assertFalse((Path(directory)/'missing').exists())

    def test_symlink_parent_rejected_without_writing_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);real=root/'real';real.mkdir();link=root/'link'
            try:link.symlink_to(real,target_is_directory=True)
            except OSError:self.skipTest('symlink creation unavailable on this platform')
            with self.assertRaisesRegex(ValueError,'symlinks'):demo.run(link/'output')
            self.assertEqual(list(real.iterdir()),[])

    def test_failed_stage_is_marked_incomplete_and_not_retried(self):
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'failed'
            failure=subprocess.CompletedProcess([],1,stdout=b'',stderr=b'Synthetic stage failure')
            with patch.object(demo.subprocess,'run',return_value=failure) as call:
                with self.assertRaisesRegex(ValueError,'stage failed'):demo.run(target)
            self.assertEqual(call.call_count,1)
            self.assertTrue((target/'FAILED.txt').exists());self.assertFalse((target/'COMPLETE.json').exists())
            self.assertIn('Synthetic stage failure',(target/'FAILED.txt').read_text())
            self.assertEqual(json.loads((target/'commands.json').read_text())[0]['returncode'],1)
            self.assertTrue((target/'corpus.json').exists())

    def test_malformed_bundled_fixture_reports_incomplete_before_commands(self):
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'bad-fixture'
            with patch.object(demo,'loads',return_value={'papers':[]}):
                with self.assertRaises(IndexError):demo.run(target)
            self.assertTrue((target/'FAILED.txt').exists());self.assertFalse((target/'COMPLETE.json').exists())
            self.assertEqual(json.loads((target/'commands.json').read_text()),[])

    def test_timeout_records_attempt_without_claiming_completion(self):
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'timeout'
            with patch.object(demo.subprocess,'run',side_effect=subprocess.TimeoutExpired('synthetic-stage',30)) as call:
                with self.assertRaises(subprocess.TimeoutExpired):demo.run(target)
            self.assertEqual(call.call_count,1)
            self.assertTrue((target/'FAILED.txt').exists());self.assertFalse((target/'COMPLETE.json').exists())
            record=json.loads((target/'commands.json').read_text())[0]
            self.assertIsNone(record['returncode'])
            self.assertEqual(Path(record['argv'][1]).name,'observation_input.py')

    def test_bundled_inputs_are_not_modified_and_empty_existing_folder_rejects(self):
        before={p:p.read_bytes() for p in (demo.ROOT/'examples').rglob('*') if p.is_file()}
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):demo.run(directory)
        self.assertEqual(before,{p:p.read_bytes() for p in before})


if __name__=='__main__':unittest.main()
