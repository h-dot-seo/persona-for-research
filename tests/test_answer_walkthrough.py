"""Opt-in invented answer proposals, never user-supplied candidates or provider calls."""
import copy
from collections import Counter
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import synthetic_walkthrough as demo
import answer_draft
import argument_map
from persona import payload_sha256
from tests.test_journey_html import Document


def normalize_paths(value, replacements):
    if isinstance(value, dict): return {key:normalize_paths(item,replacements) for key,item in value.items()}
    if isinstance(value, list): return [normalize_paths(item,replacements) for item in value]
    if isinstance(value, str):
        for old,new in replacements:
            for spelling in dict.fromkeys((old,old.replace('\\','/'))):
                if value==spelling: value=new
                elif value.startswith(spelling+'/') or value.startswith(spelling+'\\'):
                    value=new+value[len(spelling):].replace('\\','/')
                else: value=value.replace(spelling,new)
        return value
    return value


def inventory(root):
    replacements=((str(root), '<DESTINATION>'),(str(root.resolve()), '<DESTINATION>'),
        (str(demo.ROOT), '<REPOSITORY>'),(sys.executable, '<PYTHON>'))
    normalized=lambda value:normalize_paths(value,replacements)
    rows={}
    for path in sorted(root.rglob('*')):
        if not path.is_file(): continue
        text=path.read_text(encoding='utf-8')
        if path.suffix=='.html':
            # Legacy report dictionaries can arrive in hash-randomized key order.
            document=Document(text)
            value=normalized(dict(snapshot=json.loads(document.saved['complete-json']),
                tags=dict(Counter(document.tags)),ids=sorted(document.ids),hrefs=sorted(document.hrefs),
                attributes=sorted(json.dumps([tag,attrs],sort_keys=True) for tag,attrs in document.attributes)))
        else:
            value=normalized(json.loads(text)) if path.suffix=='.json' else normalized(text)
        rows[path.relative_to(root).as_posix()]=hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=True,separators=(',',':')).encode()).hexdigest()
    return rows


class AnswerWalkthroughTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory=tempfile.TemporaryDirectory();cls.root=Path(cls.directory.name)/'합성 answer history'
        result=subprocess.run([sys.executable,str(demo.ROOT/'synthetic_walkthrough.py'),str(cls.root),
            '--candidate-source','offline-import','--research-journey','--recheck-sources',
            '--review-method-use','--import-method-use','--html-review','--import-answers'],
            cwd=cls.directory.name,capture_output=True,timeout=120)
        if result.returncode: cls.directory.cleanup();raise AssertionError(result.stderr.decode('utf-8'))
        cls.receipt=json.loads(result.stdout)
    @classmethod
    def tearDownClass(cls):cls.directory.cleanup()
    def read(self,name):return json.loads((self.root/name).read_text(encoding='utf-8'))

    def test_full_route_has_46_real_commands_and_separate_deferred_answer_review(self):
        self.assertEqual(self.receipt['command_count'],46)
        self.assertEqual(self.receipt['answer_candidate_source'],'offline-import')
        self.assertTrue(self.receipt['answer_import_is_synthetic_fixture'])
        self.assertEqual(self.receipt['answer_review_status'],'ALL_DEFERRED')
        self.assertEqual(self.receipt['research_journey_answer_status'],'DECLARED_REVIEW_INCOMPLETE')
        self.assertFalse(self.receipt['llm_used']);self.assertFalse(self.receipt['external_transmission'])
        self.assertEqual(self.receipt['read_first'][0],'research-journey.html')
        self.assertIn('answer-proposals.txt',self.receipt['read_first'])
        commands=self.read('commands.json');self.assertEqual(len(commands),46)
        stages=[row['argv'][2] for row in commands if Path(row['argv'][1]).name=='answer_proposals.py']
        self.assertEqual(stages,['template','prepare','response-template','import','review-template','review','export'])
        self.assertTrue(all(row['returncode']==0 for row in commands))
        self.assertEqual(self.read('empty-answer-scope.json')['evidence_refs'],[])
        self.assertTrue(all(row['decision']=='defer' and 'reviewed_claim' not in row for row in self.read('deferred-answer-adoption.json')['decisions']))
        self.assertTrue(all(row['decision']=='defer' for row in self.read('answer-review.json')['decisions']))
        self.assertEqual([row['decision'] for row in self.read('synthetic-answer-adoption.json')['decisions']],['accept','accept','accept','reject'])
        self.assertFalse((self.root/'FAILED.txt').exists());self.assertTrue((self.root/'COMPLETE.json').exists())

    def test_all_histories_and_source_checks_survive_json_text_static_html(self):
        report=self.read('research-journey.json');html=(self.root/'research-journey.html').read_text(encoding='utf-8')
        self.assertEqual(json.loads(Document(html).saved['complete-json']),report)
        self.assertTrue(report['source_recheck']['all_stored_quotes_match'])
        self.assertIn('proposal_review',report['method_application_review']);self.assertIn('proposal_review',report['method_application_review']['pattern_review'])
        for output in (json.dumps(report),html,(self.root/'research-journey.txt').read_text(encoding='utf-8')):
            for phrase in ('Original canned answer comparison before explicit reviewer rewrite.',
                           'Check where model predictions differ.', 'Rejected synthetic answer overgeneralization',
                           'OPERATOR_ADOPTED_IMPORTED_SYNTHESIS', 'Canned synthetic model application rationale', 'Canned imported'):
                self.assertIn(phrase,output)
        answer=report['argument_review']['answer']
        self.assertEqual(answer['proposal_review']['candidates'][3]['decision'],'reject')
        self.assertEqual(answer['draft_sha256'],payload_sha256(self.read('draft.json')))
        self.assertFalse(report['automatic_approval']);self.assertFalse(report['scientific_execution'])

    def test_rejected_parent_and_premise_evidence_are_not_promoted(self):
        report=self.read('research-journey.json');rejected=self.read('synthetic-answer-response.json')['candidates'][3]['citations'][0]['reference']
        row=next(row for row in report['evidence_routes'] if row['evidence']['reference']==rejected)
        self.assertFalse(row['actively_used_in_answer_or_design']);self.assertEqual(row['direct_argument_uses'],[])
        self.assertEqual(report['argument_review']['steps'][0]['conclusion']['direct_citation_count'],0)
        active=report['argument_review']['answer']['claims']
        self.assertEqual([row['claim_id'] for row in active],['criterion','comparison','conclusion'])
        self.assertTrue(all(citation['role_origin']=='OPERATOR_ADOPTED_IMPORTED_ROLE' for row in active for citation in row['citations']))
        self.assertEqual(active[0]['origin'],'OPERATOR_ADOPTED_IMPORTED_SOURCE_QUOTE')

    def test_history_only_change_stales_actual_demo_reviews_and_argument(self):
        package=self.read('revision.json');draft=self.read('draft.json');before=answer_draft.inspect(package,draft)
        draft['review']['decisions'][3]['review_note']='Changed invented rejection note.'
        after=answer_draft.inspect(package,draft)
        self.assertEqual(before['draft_content_sha256'],after['draft_content_sha256']);self.assertNotEqual(before['draft_sha256'],after['draft_sha256'])
        with self.assertRaises(ValueError):answer_draft.review(package,draft,self.read('answer-review.json'))
        with self.assertRaises(ValueError):argument_map.inspect(package,draft,self.read('argument.json'))

    def test_mock_extraction_with_answer_import_needs_no_method_or_source_flags(self):
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'minimal answer import';receipt=demo.run(target,research_journey=True,import_answers=True)
            self.assertEqual(receipt['command_count'],32);self.assertEqual(receipt['candidate_source'],'mock')
            self.assertEqual(receipt['answer_review_status'],'ALL_DEFERRED')
            self.assertNotIn('current_source_recheck_status',receipt);self.assertNotIn('method_application_status',receipt)
            self.assertFalse((target/'synthetic-sources').exists());self.assertFalse((target/'research-journey.html').exists())

    def test_option_validation_precedes_output_creation_and_accepts_no_external_response(self):
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'invalid'
            for options,message in ((dict(import_answers=True),'requires research_journey'),(dict(research_journey=True,import_answers='yes'),'boolean')):
                with self.assertRaisesRegex(ValueError,message):demo.run(target,**options)
                self.assertFalse(target.exists())
            result=subprocess.run([sys.executable,str(demo.ROOT/'synthetic_walkthrough.py'),str(target),'--research-journey','--import-answers','--answer-response','external.json'],capture_output=True)
            self.assertNotEqual(result.returncode,0);self.assertFalse(target.exists())

    def test_every_new_cli_failure_prevents_completion_and_preserves_stage(self):
        original=demo.subprocess.run
        for stage in ('template','prepare','response-template','import','review-template','review','export'):
            with self.subTest(stage=stage),tempfile.TemporaryDirectory() as directory:
                target=Path(directory)/'failed'
                def fail(argv,**kwargs):
                    if Path(argv[1]).name=='answer_proposals.py' and argv[2]==stage:
                        return subprocess.CompletedProcess(argv,1,stdout=b'',stderr=b'Synthetic answer-stage failure')
                    return original(argv,**kwargs)
                with patch.object(demo.subprocess,'run',side_effect=fail):
                    with self.assertRaisesRegex(ValueError,'answer-stage failure'):demo.run(target,research_journey=True,import_answers=True)
                self.assertFalse((target/'COMPLETE.json').exists());self.assertFalse((target/'draft.json').exists());self.assertTrue((target/'FAILED.txt').exists())
                commands=json.loads((target/'commands.json').read_text(encoding='utf-8'));self.assertEqual(commands[-1]['returncode'],1);self.assertEqual(commands[-1]['argv'][2],stage)

    def test_fixture_guard_rejects_changed_candidate_or_review_contract(self):
        manual=answer_draft.template(self.read('revision.json'),demo.QUESTION,'synthetic-answer-operator')
        manual['claims']=[copy.deepcopy(row['reviewed_claim']) for row in self.read('synthetic-answer-adoption.json')['decisions'] if row['decision']=='accept']
        for kind in ('proposal','candidate_id','decision','review_id','reviewed_claim','missing_decision'):
            with self.subTest(kind=kind):
                writes={}
                def command(script,args,output,json_output=True):
                    value=self.read(output) if json_output else (self.root/output).read_text(encoding='utf-8')
                    if output=='answer-candidates.json':
                        if kind=='proposal':value['candidates'][0]['proposed_claim']['text']='Unexpected candidate text.'
                        if kind=='candidate_id':value['candidates'][0]['candidate_id']='other'
                    if output=='deferred-answer-adoption.json':
                        if kind=='decision':value['decisions'][0]['decision']='accept'
                        if kind=='review_id':value['decisions'][0]['candidate_id']='other'
                        if kind=='reviewed_claim':value['decisions'][0]['reviewed_claim']={}
                        if kind=='missing_decision':value['decisions'].pop()
                    return value
                with self.assertRaisesRegex(ValueError,'fixture changed'):
                    demo._import_answer_fixture(command,lambda name,value:writes.update({name:value}),Path,'revision.json',self.read('links.json'),manual)
                self.assertNotIn('synthetic-answer-adoption.json',writes)

    def test_golden_path_normalization_preserves_data_and_handles_windows_separators(self):
        replacements=((r'C:\workspace\demo','<DESTINATION>'),(r'C:\Python\python.exe','<PYTHON>'))
        value=[r'C:\workspace\demo\draft.json','C:/workspace/demo/draft.json',r'C:\Python\python.exe',r'unrelated\data']
        self.assertEqual(normalize_paths(value,replacements),['<DESTINATION>/draft.json','<DESTINATION>/draft.json','<PYTHON>',r'unrelated\data'])

    def test_previous_full_demo_inventory_is_unchanged_without_flag(self):
        # Captured independently from the verified v0.52 39-stage route; paths/JSON formatting normalized; HTML uses snapshot and structural inventory, not browser layout.
        expected='d89c01a04314f55a80b9c6eae57c70b215ab73a4a77a4ae70b0f7f94750c5b53'
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'legacy full route';receipt=demo.run(target,candidate_source='offline-import',research_journey=True,
                recheck_sources=True,review_method_use=True,import_method_use=True,html_review=True)
            self.assertEqual(receipt['command_count'],39);self.assertNotIn('answer_candidate_source',receipt)
            digest=payload_sha256(inventory(target));self.assertEqual(digest,expected)


if __name__=='__main__':unittest.main()
