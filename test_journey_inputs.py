"""Explicit synthetic local input cards, never approval or automatic source selection."""
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import journey_inputs as inputs
import journey_html
import research_journey as journey
import source_recheck
import test_research_journey as fixture
import test_application_proposals as application_fixture
from test_journey_html import Document
from persona import payload_sha256

ROOT=Path(__file__).resolve().parent


class JourneyInputTests(unittest.TestCase):
    def setUp(self):
        self.case=fixture.ResearchJourneyTests();self.case.setUp()
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.selection=inputs.template();self.selection['pattern_id']='comparison'
        for name,value in zip(inputs.REQUIRED,self.case.args()[:8]):self.write(name,value)
        self.write('declared_review',self.case.review)
    def write(self,name,value):
        relative='합성 '+name+'.json';self.selection['artifacts'][name]=relative
        (self.root/relative).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    def path(self,name):return self.root/self.selection['artifacts'][name]
    def prepare(self,**kwargs):return inputs.prepare(self.selection,self.root,**kwargs)
    def source_selection(self):
        selection=source_recheck.template(self.case.case.package,'synthetic-source')
        for row in selection['sources']:row['source_file']=row['paper_id']+'.md'
        self.write('source_selection',selection);return ROOT/'examples/synthetic-sources'

    def test_template_has_explicit_null_slots_without_reading_or_selecting_files(self):
        with patch.object(inputs,'read_source_bytes',side_effect=AssertionError('no reads')):
            form=inputs.template()
        self.assertIsNone(form['pattern_id']);self.assertEqual(set(form['artifacts']),set(inputs.NAMES))
        self.assertTrue(all(value is None for value in form['artifacts'].values()))
        with self.assertRaises(ValueError):inputs.prepare(form,self.root)

    def test_prepare_pins_raw_bytes_and_json_and_never_persists_roots_or_decisions(self):
        before={p.name:p.read_bytes() for p in self.root.iterdir()};card=self.prepare()
        self.assertEqual(set(card),{'schema','pattern_id','artifacts'})
        for name,row in card['artifacts'].items():
            if row is None:continue
            raw=self.path(name).read_bytes()
            self.assertEqual(row,dict(path=self.selection['artifacts'][name],bytes=len(raw),raw_sha256=hashlib.sha256(raw).hexdigest(),json_sha256=payload_sha256(json.loads(raw))))
        self.assertNotIn(str(self.root),json.dumps(card));self.assertNotIn('approved',card)
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.root.iterdir()})
        result=inputs.inspect(card,self.root)
        self.assertEqual(result['local_input_file_check']['input_card_sha256'],payload_sha256(card))
        self.assertEqual({k:v for k,v in result.items() if k!='local_input_file_check'},journey.inspect(*self.case.args()))

    def test_render_json_text_html_retains_same_scientific_and_review_boundaries(self):
        card=self.prepare();expected=inputs.inspect(card,self.root)
        self.assertEqual(json.loads(inputs.render(card,self.root,format='json')),expected)
        html=inputs.render(card,self.root,format='html')
        self.assertEqual(json.loads(Document(html).saved['complete-json']),expected)
        text=inputs.render(card,self.root,format='text')
        self.assertTrue(text.startswith(journey.render(*self.case.args())))
        for output in (html,text):
            self.assertIn('EXPLICIT_INPUT_FILES_MATCH_CARD_NOT_APPROVAL',output)
            self.assertIn('HUMAN_REVIEW_REQUIRED_NOT_RESEARCH_APPROVAL',output)
        self.assertFalse(expected['automatic_approval']);self.assertFalse(expected['scientific_execution'])
        with self.assertRaises(ValueError):inputs.render(card,self.root,format='execute')

    def test_each_selected_artifact_changed_even_whitespace_fails_without_rebinding(self):
        card=self.prepare();original=copy.deepcopy(card)
        for name in inputs.NAMES:
            if card['artifacts'][name] is None:continue
            path=self.path(name);raw=path.read_bytes();path.write_bytes(raw+b'\n')
            with patch.object(journey,'inspect',side_effect=AssertionError('inspect must not run')):
                with self.assertRaisesRegex(ValueError,'artifact bytes changed'):inputs.inspect(card,self.root)
            path.write_bytes(raw)
        self.assertEqual(card,original)

    def test_explicit_new_card_after_format_change_does_not_mutate_old_card_or_approve(self):
        old=self.prepare();self.path('patterns').write_bytes(self.path('patterns').read_bytes()+b'\n')
        with self.assertRaises(ValueError):inputs.inspect(old,self.root)
        new=self.prepare()
        self.assertNotEqual(new['artifacts']['patterns']['raw_sha256'],old['artifacts']['patterns']['raw_sha256'])
        self.assertEqual(new['artifacts']['patterns']['json_sha256'],old['artifacts']['patterns']['json_sha256'])
        self.assertEqual(inputs.inspect(new,self.root)['answer_review_status'],'DECLARED_REVIEW_INCOMPLETE')

    def test_logical_digest_forgery_and_semantically_stale_artifacts_fail(self):
        card=self.prepare();card['artifacts']['patterns']['json_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'JSON digest'):inputs.inspect(card,self.root)
        links=json.loads(self.path('links').read_text());links['links'][0]['rationale']='Changed synthetic link interpretation.'
        self.write('links',links)
        with self.assertRaises(ValueError):self.prepare()
        # Merely changing card hashes cannot fix the now-stale design artifact.
        card=self.prepare_without_validation()
        with self.assertRaises(ValueError):inputs.inspect(card,self.root)

    def prepare_without_validation(self):
        with patch.object(journey,'inspect',return_value={}):return self.prepare()

    def test_missing_or_invalid_late_path_preflights_before_any_byte_read(self):
        for bad in ('../escape.json','/absolute.json','folder\\file.json','file.json:stream','a/../b.json','a//b.json','a/./b.json',
                    './file.json','file.txt','https://example.invalid/file.json','file\n.json','file\u202e.json','missing.json'):
            selection=copy.deepcopy(self.selection);selection['artifacts']['declared_review']=bad
            with patch.object(inputs,'read_source_bytes',side_effect=AssertionError('must preflight all paths')) as read:
                with self.assertRaises((ValueError,OSError)):inputs.prepare(selection,self.root)
                read.assert_not_called()
        directory=self.root/'not-a-file.json';directory.mkdir();self.selection['artifacts']['declared_review']=directory.name
        with patch.object(inputs,'read_source_bytes',side_effect=AssertionError('must not read')):
            with self.assertRaises(ValueError):self.prepare()

    def test_duplicate_paths_and_missing_slots_do_not_choose_or_infer_inputs(self):
        for mutate in (lambda v:v['artifacts'].update(patterns=v['artifacts']['package']),lambda v:v['artifacts'].pop('declared_review'),
            lambda v:v['artifacts'].update(package=None),lambda v:v['artifacts'].update(extra='other.json'),
            lambda v:v.update(source_root='/not-authorized'),lambda v:v.update(command='run'),lambda v:v.update(pattern_id=None)):
            selection=copy.deepcopy(self.selection);mutate(selection)
            with patch.object(inputs,'read_source_bytes',side_effect=AssertionError('must not read')):
                with self.assertRaises(ValueError):inputs.prepare(selection,self.root)

    def test_symlink_files_parent_directories_and_root_reject_without_reads(self):
        target=self.path('declared_review');link=self.root/'linked.json'
        try:link.symlink_to(target)
        except OSError:self.skipTest('symlink creation unavailable')
        selection=copy.deepcopy(self.selection);selection['artifacts']['declared_review']=link.name
        directory=self.root/'real';directory.mkdir();nested=directory/'review.json';nested.write_bytes(target.read_bytes())
        alias=self.root/'alias';alias.symlink_to(directory,target_is_directory=True)
        for path in ('linked.json','alias/review.json'):
            selection['artifacts']['declared_review']=path
            with patch.object(inputs,'read_source_bytes',side_effect=AssertionError('must not read')):
                with self.assertRaisesRegex(ValueError,'symlink'):inputs.prepare(selection,self.root)
        root_alias=self.root/'root-alias';root_alias.symlink_to(self.root,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'symlink'):inputs.prepare(self.selection,root_alias)

    @unittest.skipUnless(hasattr(os,'mkfifo'),'FIFO unavailable')
    def test_fifo_rejected_before_open(self):
        path=self.root/'pipe.json';os.mkfifo(path);self.selection['artifacts']['declared_review']=path.name
        with patch.object(inputs,'read_source_bytes',side_effect=AssertionError('must not open FIFO')):
            with self.assertRaises(ValueError):self.prepare()

    @unittest.skipIf(os.name=='nt','Replacing an open descriptor has different Windows semantics')
    def test_detected_path_replacement_fails_closed(self):
        original=os.open;target=self.path('package');done=False
        def replace(path,flags,*args,**kwargs):
            nonlocal done
            fd=original(path,flags,*args,**kwargs)
            if Path(path)==target and not done:
                done=True;raw=target.read_bytes();target.unlink();target.write_bytes(raw)
            return fd
        with patch('corpus_files.os.open',side_effect=replace):
            with self.assertRaisesRegex(ValueError,'identity changed'):self.prepare()

    def test_card_schema_bytes_digests_and_unknown_permissions_fail_before_reads(self):
        card=self.prepare()
        changes=[lambda c:c.update(approved=True),lambda c:c.update(schema='cached-report'),
            lambda c:c['artifacts']['package'].update(bytes=True),lambda c:c['artifacts']['package'].update(bytes=0),
            lambda c:c['artifacts']['package'].update(bytes=inputs.MAX_ARTIFACT_BYTES+1),
            lambda c:c['artifacts']['package'].update(raw_sha256='G'*64),lambda c:c['artifacts']['package'].update(json_sha256='x'),
            lambda c:c['artifacts']['package'].update(source_root='/not-selected')]
        for change in changes:
            bad=copy.deepcopy(card);change(bad)
            with patch.object(inputs,'read_source_bytes',side_effect=AssertionError('must not read')):
                with self.assertRaises(ValueError):inputs.inspect(bad,self.root)

    def test_aggregate_budget_is_all_raw_selected_bytes_not_per_file(self):
        total=sum(self.path(name).stat().st_size for name in inputs.NAMES if self.selection['artifacts'][name] is not None)
        with patch.object(inputs,'MAX_ARTIFACT_BYTES',total):card=self.prepare();inputs.inspect(card,self.root)
        with patch.object(inputs,'MAX_ARTIFACT_BYTES',total-1):
            with self.assertRaises(ValueError):self.prepare()
            with self.assertRaises(ValueError):inputs.inspect(card,self.root)
        with patch.object(inputs,'MAX_CARD_BYTES',10):
            with self.assertRaises(ValueError):self.prepare()

    def test_source_selection_needs_fresh_explicit_root_before_artifact_reads(self):
        with patch.object(inputs,'read_source_bytes',side_effect=AssertionError('must not read')):
            with self.assertRaisesRegex(ValueError,'together'):self.prepare(source_root=ROOT/'examples/synthetic-sources')
        source_root=self.source_selection()
        with patch.object(inputs,'read_source_bytes',side_effect=AssertionError('must not read')):
            with self.assertRaisesRegex(ValueError,'together'):self.prepare()
        card=self.prepare(source_root=source_root)
        self.assertNotIn(str(source_root),json.dumps(card))
        with self.assertRaisesRegex(ValueError,'together'):inputs.inspect(card,self.root)
        with patch.object(source_recheck,'read_source_bytes',wraps=source_recheck.read_source_bytes) as reads:
            result=inputs.inspect(card,self.root,source_root=source_root);self.assertEqual(reads.call_count,2)
        self.assertTrue(result['source_recheck']['all_stored_quotes_match'])

    def test_source_bytes_change_does_not_refresh_bound_inputs_or_source_hash(self):
        original_root=self.source_selection();source_root=self.root/'sources';shutil.copytree(original_root,source_root)
        card=self.prepare(source_root=source_root);before=copy.deepcopy(card)
        path=source_root/'synthetic-0.md';path.write_bytes(path.read_bytes()+b'Changed synthetic source.')
        with self.assertRaisesRegex(ValueError,'bound package hash'):inputs.inspect(card,self.root,source_root=source_root)
        self.assertEqual(card,before)

    def test_changed_artifact_blocks_live_source_reads_and_invalid_package_stays_invalid(self):
        source_root=self.source_selection();card=self.prepare(source_root=source_root)
        self.path('declared_review').write_bytes(self.path('declared_review').read_bytes()+b'\n')
        with patch.object(source_recheck,'read_source_bytes',side_effect=AssertionError('must not read sources')):
            with self.assertRaisesRegex(ValueError,'artifact bytes changed'):inputs.inspect(card,self.root,source_root=source_root)
        package=json.loads(self.path('package').read_text());package['knowledge']['papers'][-1]['authorized']=False;self.write('package',package)
        with patch.object(source_recheck,'read_source_bytes',side_effect=AssertionError('must not read sources')):
            with self.assertRaises(ValueError):self.prepare(source_root=source_root)

    def test_optional_imported_application_history_survives_card_and_html(self):
        c=application_fixture.ApplicationProposalTests();c.setUp();c.accept();envelope=c.envelope()
        self.write('method_applications',envelope);card=self.prepare()
        report=inputs.inspect(card,self.root);self.assertIn('proposal_review',report['method_application_review'])
        html=inputs.render(card,self.root,format='html')
        self.assertIn('Synthetic model proposed',html);self.assertIn('Synthetic reviewer changed',html)
        self.assertEqual(json.loads(Document(html).saved['complete-json']),report)

    def test_no_provider_calls_mutation_or_writes_and_relocated_identical_files_work(self):
        before={p.name:p.read_bytes() for p in self.root.iterdir()};selection=copy.deepcopy(self.selection)
        with patch('socket.socket',side_effect=AssertionError('no network')):
            card=self.prepare();inputs.inspect(card,self.root);inputs.render(card,self.root,format='html')
        self.assertEqual(selection,self.selection);self.assertEqual(before,{p.name:p.read_bytes() for p in self.root.iterdir()})
        with tempfile.TemporaryDirectory() as target:
            for name,raw in before.items():(Path(target)/name).write_bytes(raw)
            self.assertEqual(inputs.inspect(card,self.root),inputs.inspect(card,Path(target)))

    def test_strict_json_utf8_and_no_optional_review_are_explicit(self):
        for raw in (b'{"x":1,"x":2}',b'{"x":NaN}',b'\xff'):
            path=self.path('declared_review');old=path.read_bytes();path.write_bytes(raw)
            with self.assertRaises(ValueError):self.prepare()
            path.write_bytes(old)
        self.selection['artifacts']['declared_review']=None
        argument=json.loads(self.path('argument').read_text());argument['review_sha256']=None;self.write('argument',argument)
        result=inputs.inspect(self.prepare(),self.root);self.assertEqual(result['answer_review_status'],'NOT_SUPPLIED')

    def test_final_output_budget_has_no_partial_result_and_html_inspects_once(self):
        card=self.prepare()
        with patch.object(inputs,'MAX_OUTPUT_BYTES',10):
            with self.assertRaises(ValueError):inputs.render(card,self.root,format='text')
            with self.assertRaises(ValueError):inputs.render(card,self.root,format='json')
        with patch.object(journey,'inspect',wraps=journey.inspect) as inspect:
            inputs.render(card,self.root,format='html');self.assertEqual(inspect.call_count,1)

    def test_selection_card_reader_rejects_nonregular_symlink_and_oversized_files(self):
        path=self.root/'input-card.json';path.write_text(json.dumps(self.prepare()),encoding='utf-8')
        self.assertEqual(inputs._load_card(path),self.prepare())
        with patch.object(inputs,'MAX_CARD_BYTES',5):
            with self.assertRaises(ValueError):inputs._load_card(path)
        directory=self.root/'directory.json';directory.mkdir()
        with self.assertRaises(ValueError):inputs._load_card(directory)
        link=self.root/'card-link.json'
        try:link.symlink_to(path)
        except OSError:return
        with self.assertRaisesRegex(ValueError,'symlink'):inputs._load_card(link)
        if hasattr(os,'mkfifo'):
            fifo=self.root/'card-fifo.json';os.mkfifo(fifo)
            with patch.object(inputs,'read_source_bytes',side_effect=AssertionError('must not read FIFO')):
                with self.assertRaises(ValueError):inputs._load_card(fifo)

    @unittest.skipIf(os.name=='nt','Synthetic symlink replacement requires Unix unlink semantics')
    def test_artifact_symlink_inserted_during_resolution_cannot_choose_another_file(self):
        target=self.path('declared_review');other=self.root/'other-review.json';other.write_bytes(target.read_bytes())
        original=Path.resolve;done=False
        def replace(path,*args,**kwargs):
            nonlocal done
            if path==target and not done:
                done=True;target.unlink();target.symlink_to(other)
            return original(path,*args,**kwargs)
        with patch.object(Path,'resolve',replace),patch.object(inputs,'read_source_bytes',side_effect=AssertionError('no read')):
            with self.assertRaisesRegex(ValueError,'symlink'):self.prepare()

    def test_canonical_spelling_change_keeps_same_file_identity_but_rejects_another_file(self):
        # Models benign OS canonicalization without treating different spelling as
        # replacement. Real Windows temp paths exercise this on both CI versions.
        source=self.path('declared_review');alias=self.root/'same-file.json'
        try:os.link(source,alias)
        except OSError:self.skipTest('hardlink fixture unavailable')
        original=Path.resolve
        def same(path,*args,**kwargs):return alias if path==source else original(path,*args,**kwargs)
        with patch.object(Path,'resolve',same):
            resolved,info=inputs._checked_path(source)
            self.assertEqual(resolved,alias);self.assertEqual(info.st_ino,source.stat().st_ino)
        other=self.root/'different-file.json';other.write_bytes(source.read_bytes())
        def different(path,*args,**kwargs):return other if path==source else original(path,*args,**kwargs)
        with patch.object(Path,'resolve',different):
            with self.assertRaisesRegex(ValueError,'identity changed'):inputs._checked_path(source)

    def test_reparse_point_attribute_is_rejected_even_without_symlink_mode(self):
        from types import SimpleNamespace
        # Preflight canonicalizes the root before visiting artifact components.
        # Bind the mock to that canonical target on Windows as well as POSIX.
        path=self.path('declared_review').resolve(strict=True);original=Path.stat
        def reparse(current,*args,**kwargs):
            if current==path:
                return SimpleNamespace(st_mode=original(current,*args,**kwargs).st_mode,st_file_attributes=0x400)
            return original(current,*args,**kwargs)
        with patch.object(Path,'stat',reparse),patch.object(inputs,'read_source_bytes',side_effect=AssertionError('no read')):
            with self.assertRaisesRegex(ValueError,'reparse'):self.prepare()

    def test_full_synthetic_journey_can_be_reopened_from_committed_input_selection(self):
        target=self.root/'complete synthetic journey'
        run=subprocess.run([sys.executable,str(ROOT/'synthetic_walkthrough.py'),str(target),
            '--candidate-source','offline-import','--research-journey','--recheck-sources',
            '--review-method-use','--import-method-use','--html-review'],capture_output=True,timeout=120)
        self.assertEqual(run.returncode,0,run.stderr);self.assertEqual(json.loads(run.stdout)['command_count'],39)
        selection=ROOT/'examples/synthetic-journey-inputs.json'
        prepared=subprocess.run([sys.executable,str(ROOT/'journey_inputs.py'),'prepare',str(selection),
            '--input-root',str(target),'--source-root',str(target/'synthetic-sources')],capture_output=True,timeout=30)
        self.assertEqual(prepared.returncode,0,prepared.stderr)
        card_path=target/'input-card.json';card_path.write_bytes(prepared.stdout)
        rendered=subprocess.run([sys.executable,str(ROOT/'journey_inputs.py'),'inspect',str(card_path),
            '--input-root',str(target),'--source-root',str(target/'synthetic-sources'),'--format','html'],capture_output=True,timeout=30)
        self.assertEqual(rendered.returncode,0,rendered.stderr)
        snapshot=json.loads(Document(rendered.stdout.decode()).saved['complete-json'])
        expected=json.loads((target/'research-journey.json').read_text(encoding='utf-8'))
        self.assertEqual({k:v for k,v in snapshot.items() if k!='local_input_file_check'},expected)
        self.assertEqual(snapshot['local_input_file_check']['status'],'EXPLICIT_INPUT_FILES_MATCH_CARD_NOT_APPROVAL')
        self.assertIn('Pinned JSON input files',rendered.stdout.decode())

    def test_cli_template_prepare_and_formats_reject_changes_with_empty_stdout(self):
        selection=self.root/'selection.json';selection.write_text(json.dumps(self.selection),encoding='utf-8')
        card_path=self.root/'card.json'
        def run(*args):return subprocess.run([sys.executable,str(ROOT/'journey_inputs.py'),*map(str,args)],cwd=self.root,capture_output=True,timeout=30)
        self.assertEqual(json.loads(run('template').stdout),inputs.template())
        result=run('prepare',selection,'--input-root',self.root);self.assertEqual(result.returncode,0,result.stderr)
        card_path.write_bytes(result.stdout)
        for format in ('json','text','html'):
            result=run('inspect',card_path,'--input-root',self.root,'--format',format)
            self.assertEqual(result.returncode,0,result.stderr)
            if format=='json':self.assertEqual(json.loads(result.stdout)['local_input_file_check']['status'],'EXPLICIT_INPUT_FILES_MATCH_CARD_NOT_APPROVAL')
            elif format=='html':self.assertTrue(result.stdout.startswith(b'<!doctype html>'))
        self.path('patterns').write_bytes(self.path('patterns').read_bytes()+b'\n')
        result=run('inspect',card_path,'--input-root',self.root,'--format','html')
        self.assertNotEqual(result.returncode,0);self.assertEqual(result.stdout,b'');self.assertNotIn(b'Traceback',result.stderr)
        for raw in ('{"a":1,"a":2}','{"a":NaN}'):
            card_path.write_text(raw)
            result=run('inspect',card_path,'--input-root',self.root)
            self.assertNotEqual(result.returncode,0);self.assertEqual(result.stdout,b'')


if __name__=='__main__':unittest.main()
