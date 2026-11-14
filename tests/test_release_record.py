"""Synthetic prior-package reopening declarations and read-only candidate comparison."""
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
from persona import payload_sha256
from research_workflow import build

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = 'examples/trajectory-conditions-package.json'
CANDIDATE = 'examples/trajectory-conditions-reopened-package.json'
RECORD = 'examples/manual-reopening-record.json'


def read(path):
    return json.loads((ROOT/path).read_text())


def corpus(package):
    return dict(**{k:package['persona'][k] for k in ('author_id','version','build_id')},
                papers=copy.deepcopy(package['knowledge']['papers']))


class ReopeningTests(unittest.TestCase):
    def setUp(self):
        self.p=read(PACKAGE);self.q=read(CANDIDATE);self.r=read(RECORD)

    def test_neutral_template_requires_completion(self):
        blank=r.template(self.p)
        self.assertIsNone(blank['status']);self.assertIsNone(blank['trigger']['kind'])
        self.assertEqual(blank['affected_rule_ids'],[])
        with self.assertRaises(ValueError):r.check(blank,self.p)

    def test_fixture_is_exact_declared_correction_rebuild(self):
        c=corpus(self.p);c.update(version='synthetic-reopened',build_id='synthetic-reopened-build')
        for paper in c['papers']:
            if paper['paper_id']=='synthetic-2024-a-challenge':
                paper['observations'][0]['limitation']='Fictional correction: synthetic scope limitation supplied for a reopening example.'
        self.assertEqual(build(c),self.q)

    def test_bound_comparison_is_read_only_and_prior_rules_only(self):
        before=copy.deepcopy((self.p,self.q,self.r));out=r.check(self.r,self.p,self.q)
        self.assertEqual(out['candidate_comparison']['prior_rules_on_changed_papers'],['rule-5'])
        self.assertFalse(out['candidate_comparison']['candidate_rule_ids_interpreted'])
        self.assertEqual(out['review_prompts'],[])
        self.assertEqual(out['revalidation_axis_status']['human'],'NOT_SUPPLIED')
        self.assertEqual(out['release_decision'],'NOT_RECORDED')
        self.assertEqual(before,(self.p,self.q,self.r))

    def test_declared_missing_changes_are_prompts_not_rejection(self):
        self.r['trigger']['kind']='scope_change';self.r['affected_paper_ids']=[];self.r['affected_rule_ids']=[]
        out=r.check(self.r,self.p,self.q)
        self.assertEqual(set(out['review_prompts']),{'UNDECLARED_PAPER_CHANGE','RULES_ON_CHANGED_PAPERS_NOT_DECLARED'})
        self.assertEqual(out['verdict'],'NOT_DERIVED')

    def test_stale_record_not_reinterpreted(self):
        with self.assertRaises(ValueError):r.check(self.r,self.q)
        for key in ('version','build_id','author_id','persona_payload_sha256','knowledge_papers_sha256'):
            value=copy.deepcopy(self.r);value[key]='a'*64
            with self.subTest(key=key),self.assertRaises(ValueError):r.check(value,self.p)

    def test_strict_record_and_trigger(self):
        for key,value in [('status',None),('schema_version','other'),('extra',1),('operator_id',''),
                          ('operation','both'),('revision_audit_sha256','bad'),('affected_paper_ids',['absent']),
                          ('affected_rule_ids',['absent']),('revalidation_axes_required',['challenge']),
                          ('incoming_paper_ids',['new']),('affected_paper_ids',[]),('affected_rule_ids',['rule-5','rule-5'])]:
            record=copy.deepcopy(self.r);record[key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):r.check(record,self.p)
        for key,value in [('kind','unknown'),('declared_at','2026-02-30'),('declared_at','20261114'),('declared_source_text',''),('extra',1)]:
            record=copy.deepcopy(self.r);record['trigger'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):r.check(record,self.p)

    def test_new_paper_ids_are_prior_absent_and_candidate_compared(self):
        self.r['trigger']['kind']='new_paper';self.r['incoming_paper_ids']=['synthetic-new'];self.r['affected_paper_ids']=[];self.r['affected_rule_ids']=[]
        c=corpus(self.p);paper=copy.deepcopy(c['papers'][0]);paper['paper_id']='synthetic-new';c['papers'].append(paper)
        out=r.check(self.r,self.p,build(c))
        self.assertEqual(out['candidate_comparison']['added_paper_ids'],['synthetic-new'])
        self.assertNotIn('UNDECLARED_PAPER_CHANGE',out['review_prompts'])
        self.r['incoming_paper_ids']=[self.p['knowledge']['papers'][0]['paper_id']]
        with self.assertRaises(ValueError):r.check(self.r,self.p)

    def test_new_paper_requires_incoming(self):
        self.r['trigger']['kind']='new_paper'
        with self.assertRaises(ValueError):r.check(self.r,self.p)

    def test_removed_paper_uses_old_rules(self):
        c=corpus(self.p);c['papers']=[p for p in c['papers'] if p['paper_id']!='synthetic-2024-a-challenge']
        out=r.check(self.r,self.p,build(c))
        self.assertEqual(out['candidate_comparison']['prior_rules_on_changed_papers'],['rule-5'])
        self.assertFalse(out['candidate_comparison']['candidate_rule_ids_interpreted'])

    def test_human_current_stale_and_absent(self):
        human=read('examples/manual-human-validation.json')
        self.assertEqual(r.check(self.r,self.p,human_records=[human])['revalidation_axis_status']['human'],'CURRENT')
        human['version']='old'
        self.assertEqual(r.check(self.r,self.p,human_records=[human])['revalidation_axis_status']['human'],'STALE')
        with self.assertRaises(ValueError):r.status(self.p,human_records=[{}])

    def test_status_and_duplicates(self):
        self.assertEqual(r.status(self.p)['status'],'NOT_PERFORMED')
        self.assertEqual(r.status(self.p,[self.r])['record_count'],1)
        with self.assertRaises(ValueError):r.status(self.p,[self.r,self.r])

    def test_prose_and_operator_not_echoed(self):
        self.r['operator_id']='PRIVATE-OP';self.r['trigger']['declared_source_text']='PRIVATE\n\x1b[2J'
        out=r.render(r.check(self.r,self.p))
        self.assertNotIn('PRIVATE',out)
        self.assertNotIn('declared_source_text',out)

    def test_audit_hash_declared_only(self):
        self.r['revision_audit_sha256']='a'*64
        out=r.check(self.r,self.p)
        self.assertEqual(out['revision_audit_verification'],'DECLARED_NOT_VERIFIED')

    def test_invalid_source_rules_rejected(self):
        self.p['persona']['rules'][0]['limitation']='tampered'
        self.p['knowledge']['persona_payload_sha256']=payload_sha256(self.p['persona'])
        with self.assertRaises(ValueError):r.template(self.p)

    def test_output_bound(self):
        with patch.object(r,'MAX_OUTPUT_BYTES',1),self.assertRaises(ValueError):r.render({})

    def test_cli_failure_no_output_and_redacted(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'out.json'
            run=subprocess.run([sys.executable,'release_record.py','check','private-missing',PACKAGE,'--output',str(out)],cwd=ROOT,capture_output=True)
            self.assertNotEqual(run.returncode,0);self.assertEqual(run.stdout,b'');self.assertFalse(out.exists());self.assertNotIn(b'private-missing',run.stderr)

    def test_documented_commands_and_exclusive_output(self):
        with tempfile.TemporaryDirectory(prefix='reopening space ') as tmp:
            guide=(ROOT/'docs/RELEASE_RECORD.md').read_text()
            for block in re.findall(r'```sh\n(.*?)```',guide,re.S):
                for line in block.splitlines():
                    if not line.startswith('python '):continue
                    args=[part.replace('OUTPUT',tmp) for part in shlex.split(line)[1:]]
                    run=subprocess.run([sys.executable,*args],cwd=ROOT,capture_output=True)
                    self.assertEqual(run.returncode,0,(line,run.stderr))
            out=Path(tmp)/'blank-reopening.json';before=out.read_bytes()
            run=subprocess.run([sys.executable,'release_record.py','template','reopening',PACKAGE,'--output',str(out)],cwd=ROOT,capture_output=True)
            self.assertNotEqual(run.returncode,0);self.assertEqual(before,out.read_bytes())

    def test_paper_reordering_never_matches_candidate_positions(self):
        c=corpus(self.p);c['papers'].reverse()
        out=r.check(self.r,self.p,build(c))
        self.assertIn('RULE_POSITIONS_CHANGED_WITHOUT_PAPER_CHANGE',out['review_prompts'])
        self.assertEqual(out['candidate_comparison']['prior_rules_on_changed_papers'],[])
        self.assertFalse(out['candidate_comparison']['candidate_rule_ids_interpreted'])

    def test_declared_incoming_not_added_reported(self):
        self.r['trigger']['kind']='new_paper';self.r['incoming_paper_ids']=['synthetic-incoming']
        out=r.check(self.r,self.p,self.p)
        self.assertEqual(out['candidate_comparison']['declared_incoming_not_added'],['synthetic-incoming'])

    def test_status_rejects_duplicate_human_without_reopening(self):
        human=read('examples/manual-human-validation.json')
        with self.assertRaises(ValueError):r.status(self.p,human_records=[human,human])
        with tempfile.TemporaryDirectory() as tmp:
            invalid=Path(tmp)/'invalid.json';invalid.write_text('{}')
            run=subprocess.run([sys.executable,'release_record.py','status',PACKAGE,'--human-validation',str(invalid)],cwd=ROOT,capture_output=True)
            self.assertNotEqual(run.returncode,0);self.assertEqual(run.stdout,b'')

    def test_cli_all_inputs_share_reader(self):
        human=read('examples/manual-human-validation.json');values={'p':self.p,'q':self.q,'r':self.r,'h':human};calls=[]
        def read_one(path):calls.append(str(path));return values[str(path)]
        with patch.object(r,'bounded_reader',return_value=read_one) as reader,patch.object(r,'emit'),\
             patch.object(sys,'argv',['release_record.py','check','r','p','q','--human-validation','h']):
            r.main()
        reader.assert_called_once_with();self.assertEqual(calls,['p','h','r','q'])

    def test_shared_reader_duplicate_json_and_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'record';p.write_bytes(b'{}');reader=r.bounded_reader(3);reader(p)
            with self.assertRaises(ValueError):reader(p)
            p.write_bytes(b'{"x":1,"x":2}')
            with self.assertRaises(ValueError):r.bounded_reader()(p)

    def test_template_refuses_dangling_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'dangling'
            try:p.symlink_to(Path(tmp)/'missing')
            except OSError:self.skipTest('symlink unavailable')
            run=subprocess.run([sys.executable,'release_record.py','template','reopening',PACKAGE,'--output',str(p)],cwd=ROOT,capture_output=True)
            self.assertNotEqual(run.returncode,0);self.assertTrue(p.is_symlink())
