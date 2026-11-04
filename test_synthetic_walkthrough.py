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

    def test_imported_fixture_runs_actual_handoff_review_and_lineage_clis(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)/'imported synthetic output'
            result = subprocess.run([sys.executable, str(demo.ROOT/'synthetic_walkthrough.py'), str(target),
                '--candidate-source', 'offline-import'], cwd=directory, capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            receipt = json.loads(result.stdout)
            self.assertEqual(receipt['command_count'], 17)
            self.assertEqual(receipt['candidate_source'], 'offline-import')
            self.assertTrue(receipt['imported_response_is_synthetic_fixture'])
            self.assertFalse(receipt['llm_used']); self.assertFalse(receipt['external_transmission'])
            self.assertEqual(receipt['answer_review_status'], 'ALL_DEFERRED')
            commands = json.loads((target/'commands.json').read_text())
            self.assertEqual(sum(Path(c['argv'][1]).name == 'model_handoff.py' for c in commands), 3)
            bundle = json.loads((target/'candidates.json').read_text())
            lineage = json.loads((target/'lineage.json').read_text())
            self.assertEqual(bundle['contract_version'], '2')
            self.assertIsNone(bundle['provider']['llm_used'])
            self.assertEqual(len(lineage['imported_origin_components']), 2)
            self.assertEqual(lineage['mock_origin_components'], [])
            self.assertTrue(all(r['audit_status'] == 'REPLAYED_CURRENT_REVISION' for r in lineage['candidate_origin_components']))
            self.assertIn('RECORDED_IMPORTED_CANDIDATE_ORIGIN', (target/'reader-scope.txt').read_text())
            self.assertIn('AFTER_REFERENCE_YEAR', (target/'review-packet.txt').read_text())
            self.assertIn('Defeater: NOT_SUPPLIED', (target/'argument-map.txt').read_text())
            self.assertTrue((target/'COMPLETE.json').exists())
            self.assertFalse((target/'FAILED.txt').exists())

    def test_extended_imported_journey_runs_27_cli_stages_and_keeps_review_gaps(self):
        before={p:p.read_bytes() for p in (demo.ROOT/'examples').rglob('*') if p.is_file()}
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'통합 synthetic journey'
            run=subprocess.run([sys.executable,str(demo.ROOT/'synthetic_walkthrough.py'),str(target),
                '--candidate-source','offline-import','--research-journey'],cwd=directory,capture_output=True,
                env=dict(os.environ,PYTHONIOENCODING='ascii'),timeout=30)
            self.assertEqual(run.returncode,0,run.stderr);receipt=json.loads(run.stdout)
            self.assertEqual(receipt['command_count'],27)
            self.assertEqual(receipt['answer_review_status'],'ALL_DEFERRED')
            self.assertEqual(receipt['research_journey_status'],'HUMAN_REVIEW_REQUIRED_NOT_RESEARCH_APPROVAL')
            commands=json.loads((target/'commands.json').read_text());self.assertEqual(len(commands),27)
            self.assertTrue(all(row['returncode']==0 for row in commands))
            report=json.loads((target/'research-journey.json').read_text())
            history=report['pattern_transfer_review']['pattern_proposal_review']
            self.assertEqual([row['decision'] for row in history['candidates']],['accept','reject'])
            self.assertTrue(all(row['decision']=='defer' for row in json.loads((target/'deferred-pattern-review.json').read_text())['decisions']))
            self.assertEqual(report['pattern_transfer_review']['context_review']['decision_counts'],{'consider':0,'exclude':1,'defer':1})
            codes=[row['code'] for row in report['review_agenda']]
            for code in ('FALSIFICATION_CHECK_NOT_SUPPLIED','DECLARED_DEFER','NO_DIRECT_CITATIONS_CITATION_TRANSFER_NOT_PERFORMED',
                         'RELATION_CONTEXT_INCLUDES_AFTER_REFERENCE_YEAR_PUBLICATION'):
                self.assertIn(code,codes)
            text=(target/'research-journey.txt').read_text(encoding='utf-8')
            for phrase in ('Canned imported','Fixed synthetic reviewer','A rejected synthetic overgeneralization',
                           'Defeater: NOT_SUPPLIED','Declared decision: defer'):
                self.assertIn(phrase,text)
            self.assertTrue((target/'COMPLETE.json').is_file());self.assertFalse((target/'FAILED.txt').exists())
            self.assertEqual(receipt['read_first'][0],'research-journey.txt')
            self.assertTrue(all((target/name).is_file() for name in receipt['read_first']))
        self.assertEqual(before,{p:p.read_bytes() for p in before})

    def test_extended_mock_journey_is_also_explicitly_synthetic(self):
        with tempfile.TemporaryDirectory() as directory:
            receipt=demo.run(Path(directory)/'extended mock',research_journey=True)
            self.assertEqual(receipt['command_count'],25);self.assertEqual(receipt['candidate_source'],'mock')
            self.assertTrue(receipt['research_journey_is_synthetic']);self.assertFalse(receipt['llm_used'])

    def test_late_extended_failure_never_publishes_completion_marker(self):
        original=demo.subprocess.run
        def fail(argv,**kwargs):
            if Path(argv[1]).name=='research_journey.py' and '--format' in argv:
                return subprocess.CompletedProcess(argv,1,stdout=b'',stderr=b'Synthetic late rendering failure')
            return original(argv,**kwargs)
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'incomplete extended'
            with patch.object(demo.subprocess,'run',side_effect=fail):
                with self.assertRaisesRegex(ValueError,'late rendering failure'):
                    demo.run(target,candidate_source='offline-import',research_journey=True)
            self.assertTrue((target/'research-journey.json').is_file())
            self.assertTrue((target/'FAILED.txt').is_file());self.assertFalse((target/'COMPLETE.json').exists())
            commands=json.loads((target/'commands.json').read_text());self.assertEqual(len(commands),27)
            self.assertEqual(commands[-1]['returncode'],1)

    def test_invalid_extended_flag_fails_before_directory_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'invalid extended'
            with self.assertRaisesRegex(ValueError,'boolean'):demo.run(target,research_journey='yes')
            self.assertFalse(target.exists())

    def test_live_source_demo_executes_30_stages_with_unchanged_historical_labels(self):
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'합성 local source journey'
            result=subprocess.run([sys.executable,str(demo.ROOT/'synthetic_walkthrough.py'),str(target),
                '--candidate-source','offline-import','--research-journey','--recheck-sources'],
                cwd=directory,capture_output=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr);receipt=json.loads(result.stdout)
            self.assertEqual(receipt['command_count'],30)
            self.assertEqual(receipt['read_first'][0],'source-recheck.txt')
            self.assertEqual(receipt['answer_review_status'],'ALL_DEFERRED')
            report=json.loads((target/'research-journey.json').read_text())
            current=report['source_recheck'];self.assertEqual(current['checked_record_count'],5)
            self.assertTrue(current['all_stored_quotes_match']);self.assertTrue(report['source_reread'])
            self.assertTrue(all(p['recorded_source_check_before']=='NOT_PERFORMED' for p in current['papers']))
            self.assertTrue(all(p['source_check']=='LOCAL_BYTES_SHA256_MATCH' for p in current['papers']))
            self.assertFalse(report['evidence_scope']['source_checks_repeated'])
            self.assertTrue(all(p['recorded_source_check']=='NOT_PERFORMED' for group in report['evidence_scope']['source_groups'] for p in group['papers']))
            self.assertTrue(all(row['source_file'] is None for row in json.loads((target/'empty-source-selection.json').read_text())['sources']))
            self.assertEqual(len(list((target/'synthetic-sources').glob('*.md'))),2)
            self.assertTrue((target/'COMPLETE.json').exists());self.assertFalse((target/'FAILED.txt').exists())
            self.assertIn('invented local source files', (target/'START_HERE.txt').read_text())

    def test_source_change_between_live_stages_prevents_demo_completion(self):
        original=demo.subprocess.run
        def change_before_audit(argv,**kwargs):
            if Path(argv[1]).name=='source_recheck.py' and '--source-root' in argv:
                root=Path(argv[argv.index('--source-root')+1]);source=root/'synthetic-source-1.md'
                source.write_bytes(source.read_bytes()+b'Unexpected synthetic source change.')
            return original(argv,**kwargs)
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'changed source'
            with patch.object(demo.subprocess,'run',side_effect=change_before_audit):
                with self.assertRaisesRegex(ValueError,'bound package hash'):
                    demo.run(target,research_journey=True,recheck_sources=True)
            self.assertTrue((target/'FAILED.txt').exists());self.assertFalse((target/'COMPLETE.json').exists())
            self.assertFalse((target/'research-journey.json').exists())

    def test_live_demo_flags_reject_incomplete_or_nonboolean_requests_before_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'invalid source demo'
            with self.assertRaisesRegex(ValueError,'requires research_journey'):demo.run(target,recheck_sources=True)
            with self.assertRaisesRegex(ValueError,'boolean'):demo.run(target,research_journey=True,recheck_sources='yes')
            self.assertFalse(target.exists())

    def test_method_use_demo_runs_32_stages_without_approving_pattern_application(self):
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'method use journey'
            result=subprocess.run([sys.executable,str(demo.ROOT/'synthetic_walkthrough.py'),str(target),
                '--candidate-source','offline-import','--research-journey','--recheck-sources','--review-method-use'],
                cwd=directory,capture_output=True,timeout=60)
            self.assertEqual(result.returncode,0,result.stderr);receipt=json.loads(result.stdout)
            self.assertEqual(receipt['command_count'],32)
            self.assertEqual(receipt['method_application_status'],'METHOD_APPLICATION_REQUIRES_HUMAN_REVIEW')
            self.assertEqual(receipt['answer_review_status'],'ALL_DEFERRED')
            self.assertEqual(receipt['read_first'][:2],['source-recheck.txt','method-applications.txt'])
            default=json.loads((target/'deferred-method-applications.json').read_text())
            self.assertTrue(all(row['decision']=='defer' and row['evidence_refs']==[] for row in default['applications']))
            report=json.loads((target/'research-journey.json').read_text());method=report['method_application_review']
            self.assertEqual(method['decision_counts'],{'consider':1,'exclude':0,'defer':0})
            self.assertFalse(method['design_modified']);self.assertFalse(method['scientific_execution'])
            self.assertTrue(report['source_recheck']['all_stored_quotes_match'])
            self.assertIsNone(method['applications'][0]['failure_condition'])
            self.assertIn('CONSIDERED_APPLICATION_HAS_EXCLUDED_SOURCE_CONTEXT',[row['code'] for row in method['review_prompts']])
            text=(target/'method-applications.txt').read_text()
            self.assertIn('failure_condition: NOT_SUPPLIED',text);self.assertIn('Required checks (not executed)',text)
            self.assertTrue((target/'COMPLETE.json').exists());self.assertFalse((target/'FAILED.txt').exists())

    def test_method_review_stage_failure_blocks_completion_without_retry(self):
        original=demo.subprocess.run
        def fail(argv,**kwargs):
            if Path(argv[1]).name=='method_application.py' and '--format' in argv:
                return subprocess.CompletedProcess(argv,1,stdout=b'',stderr=b'Synthetic method review failure')
            return original(argv,**kwargs)
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'failed method review'
            with patch.object(demo.subprocess,'run',side_effect=fail):
                with self.assertRaisesRegex(ValueError,'method review failure'):
                    demo.run(target,research_journey=True,review_method_use=True)
            self.assertTrue((target/'FAILED.txt').exists());self.assertFalse((target/'COMPLETE.json').exists())
            self.assertFalse((target/'research-journey.json').exists())
            commands=json.loads((target/'commands.json').read_text())
            self.assertEqual(commands[-1]['returncode'],1)

    def test_method_use_flags_require_explicit_extended_flow_before_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'invalid method flow'
            with self.assertRaisesRegex(ValueError,'requires research_journey'):demo.run(target,review_method_use=True)
            with self.assertRaisesRegex(ValueError,'boolean'):demo.run(target,research_journey=True,review_method_use='yes')
            self.assertFalse(target.exists())

    def test_invalid_candidate_mode_fails_before_directory_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)/'invalid'
            with self.assertRaisesRegex(ValueError, 'candidate_source'):
                demo.run(target, candidate_source='external-provider')
            self.assertFalse(target.exists())

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
