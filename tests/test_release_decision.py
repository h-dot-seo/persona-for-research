"""Supplied release decisions never become tool approval or canonical updates."""
import copy
import json
import re
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import release_record as r
import review_package

ROOT=Path(__file__).resolve().parents[1]
PACKAGE='examples/trajectory-conditions-package.json'
DECISION='examples/manual-release-decision.json'
HUMAN='examples/manual-human-validation.json'


def read(path):return json.loads((ROOT/path).read_text())


class ReleaseDecisionTests(unittest.TestCase):
    def setUp(self):self.p=read(PACKAGE);self.d=read(DECISION);self.h=read(HUMAN)

    def test_template_neutral_incomplete(self):
        d=r.decision_template(self.p)
        self.assertIsNone(d['decision']);self.assertIsNone(d['status'])
        self.assertEqual(d['axis_records'],dict(human=None,predictive=None,runtime=None))
        with self.assertRaises(ValueError):r.check(d,self.p)

    def test_current_human_hash_match_no_approval(self):
        before=copy.deepcopy((self.p,self.d,self.h));out=r.check(self.d,self.p,human_records=[self.h])
        self.assertEqual(out['recorded_decision'],'NOT_RELEASED')
        self.assertEqual(out['axis_status']['human'],'CURRENT')
        self.assertEqual(out['human_record_reference_check'],'LOGICAL_HASH_MATCH')
        self.assertEqual(out['axis_status']['predictive'],'NO_RECORD_TYPE')
        self.assertEqual(out['candidate_approval'],'NOT_DERIVED')
        self.assertFalse(out['publication_performed'])
        self.assertEqual(before,(self.p,self.d,self.h))

    def test_each_declared_choice_retained_with_unperformed_prompt(self):
        for decision in r.DECISIONS:
            self.d['decision']=decision;out=r.check(self.d,self.p)
            self.assertEqual(out['recorded_decision'],decision)
            self.assertIn('DECISION_RECORDED_WITH_UNPERFORMED_AXES',out['review_prompts'])
            self.assertEqual(out['human_record_reference_check'],'NOT_SUPPLIED')
            self.assertEqual(out['verdict'],'NOT_DERIVED')

    def test_unreferenced_human_rejected(self):
        self.d['axis_records']['human']=None
        self.assertEqual(r.check(self.d,self.p)['human_record_reference_check'],'NOT_DECLARED')
        with self.assertRaises(ValueError):r.check(self.d,self.p,human_records=[self.h])

    def test_substitution_and_duplicate_human_rejected(self):
        h=copy.deepcopy(self.h);h['method']='changed private record'
        with self.assertRaises(ValueError):r.check(self.d,self.p,human_records=[h])
        with self.assertRaises(ValueError):r.check(self.d,self.p,human_records=[self.h,self.h])

    def test_stale_human_reported_without_rebinding(self):
        self.h['version']='old';self.d['axis_records']['human']=r.payload_sha256(self.h)
        out=r.check(self.d,self.p,human_records=[self.h])
        self.assertEqual(out['axis_status']['human'],'STALE')
        self.assertEqual(out['axes_with_current_record'],[])
        self.assertIn('human',out['axes_not_performed'])

    def test_matching_hash_invalid_human_is_still_rejected(self):
        self.h['status']=None;self.d['axis_records']['human']=r.payload_sha256(self.h)
        with self.assertRaises(ValueError):r.check(self.d,self.p,human_records=[self.h])

    def test_foreign_human_identity_rejected(self):
        self.h['author_id']='other';self.d['axis_records']['human']=r.payload_sha256(self.h)
        with self.assertRaises(ValueError):r.check(self.d,self.p,human_records=[self.h])

    def test_strict_decision_record(self):
        for key,value in [('status',None),('schema_version','other'),('decision','APPROVED'),('decision',True),
                          ('decided_at','2026-02-30'),('decided_at','20261114'),('decided_by',''),
                          ('declared_thresholds',''),('rationale',''),('extra',1),('author_id','other'),
                          ('version','old'),('build_id','old'),('persona_payload_sha256','a'*64),
                          ('knowledge_papers_sha256','a'*64)]:
            d=copy.deepcopy(self.d);d[key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):r.check(d,self.p)

    def test_axis_references_exact_keys_and_supported_types(self):
        for refs in ({'human':None},{'human':None,'predictive':None,'runtime':None,'challenge':None},
                     {'human':'bad','predictive':None,'runtime':None},
                     {'human':None,'predictive':'a'*64,'runtime':None},
                     {'human':None,'predictive':None,'runtime':'a'*64}):
            self.d['axis_records']=refs
            with self.assertRaises(ValueError):r.check(self.d,self.p)

    def test_candidate_for_decision_rejected(self):
        with self.assertRaises(ValueError):r.check(self.d,self.p,self.p)

    def test_decision_cannot_masquerade_as_reopening(self):
        with self.assertRaises(ValueError):r.status(self.p,[self.d])
        opening=read('examples/manual-reopening-record.json')
        with self.assertRaises(ValueError):r.decision_check(opening,self.p)

    def test_status_keeps_distinct_declarations(self):
        opening=read('examples/manual-reopening-record.json')
        out=r.status(self.p,[opening],[self.h],self.d)
        self.assertEqual(out['records'][0]['release_decision'],'NOT_RECORDED')
        self.assertEqual(out['supplied_release_decision']['recorded_decision'],'NOT_RELEASED')
        self.assertNotIn('supplied_release_decision',r.status(self.p))
        only=r.status(self.p,release_decision=self.d)
        self.assertEqual(only['status'],'DETACHED_RELEASE_RECORDS_REPORTED')
        self.assertEqual(only['reopening_status'],'NOT_PERFORMED')
        self.assertEqual(only['release_decision'],'SUPPLIED_OPERATOR_DECLARATION')
        self.assertEqual(out['reopening_status'],'RECORDED_CURRENT')

    def test_labels_rationale_and_threshold_prose_omitted(self):
        self.d.update(decided_by='SECRET-LABEL',rationale='PRIVATE\n\x1b[2J',declared_thresholds='PRIVATE-THRESHOLD')
        out=r.check(self.d,self.p)
        for text in (r.render(out),'\n'.join(r.decision_lines(out))):
            self.assertNotIn('PRIVATE',text);self.assertNotIn('SECRET',text)

    def test_review_optional_default_unchanged(self):
        args=dict(question='Synthetic?',topic='synthetic method conditions')
        plain=review_package.render(self.p,**args)
        self.assertEqual(plain,review_package.render(self.p,release_decision=None,**args))
        rendered=review_package.render(self.p,release_decision=self.d,human_validation=[self.h],**args)
        self.assertIn('Supplied release decision (not tool approval): NOT_RELEASED',rendered)
        self.assertIn('runtime=NO_RECORD_TYPE',rendered)
        self.assertNotIn(self.d['rationale'],rendered)

    def test_all_review_inputs_share_reader(self):
        values={'p':self.p,'d':self.d,'h':self.h,'c':{},'s':{}};calls=[]
        def one(path):calls.append(str(path));return values[str(path)]
        with patch('candidate_challenge.bounded_reader',return_value=one) as reader,\
             patch('split_declaration.validate_declaration'),patch.object(review_package,'render',return_value='synthetic\n'),\
             patch.object(review_package,'emit'),patch.object(sys,'argv',['review_package.py','p','--question','q','--topic','t',
             '--release-decision','d','--human-validation','h','--challenge-record','c','--split','s']):
            review_package.main()
        reader.assert_called_once_with();self.assertEqual(calls,['p','c','d','h','s'])

    def test_review_budget_includes_package(self):
        with patch('candidate_challenge.MAX_INPUT_BYTES',1),patch.object(sys,'argv',
             ['review_package.py',str(ROOT/PACKAGE),'--question','q','--topic','t','--release-decision',str(ROOT/DECISION)]),\
             self.assertRaises(SystemExit):review_package.main()

    def test_status_shared_input_reader(self):
        values={'p':self.p,'d':self.d,'h':self.h};calls=[]
        def one(path):calls.append(str(path));return values[str(path)]
        with patch.object(r,'bounded_reader',return_value=one) as reader,patch.object(r,'emit'),\
             patch.object(sys,'argv',['release_record.py','status','p','--release-decision','d','--human-validation','h']):r.main()
        reader.assert_called_once_with();self.assertEqual(calls,['p','h','d'])

    def test_invalid_decision_no_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad=Path(tmp)/'bad';bad.write_text('{}');out=Path(tmp)/'out'
            run=subprocess.run([sys.executable,'release_record.py','check',str(bad),PACKAGE,'--output',str(out)],cwd=ROOT,capture_output=True)
            self.assertNotEqual(run.returncode,0);self.assertEqual(run.stdout,b'');self.assertFalse(out.exists())

    def test_documented_commands_and_template_exclusive(self):
        with tempfile.TemporaryDirectory(prefix='decision space ') as tmp:
            for block in re.findall(r'```sh\n(.*?)```',(ROOT/'docs/RELEASE_DECISION.md').read_text(),re.S):
                for line in block.splitlines():
                    if not line.startswith('python '):continue
                    args=[x.replace('OUTPUT',tmp) for x in shlex.split(line)[1:]]
                    run=subprocess.run([sys.executable,*args],cwd=ROOT,capture_output=True)
                    self.assertEqual(run.returncode,0,(line,run.stderr))
            out=Path(tmp)/'blank-decision.json';before=out.read_bytes()
            run=subprocess.run([sys.executable,'release_record.py','template','decision',PACKAGE,'--output',str(out)],cwd=ROOT,capture_output=True)
            self.assertNotEqual(run.returncode,0);self.assertEqual(before,out.read_bytes())
