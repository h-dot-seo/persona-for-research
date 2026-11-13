"""Detached pre-holdout candidate findings: synthetic records only."""
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

import candidate_challenge as c
import review_package

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = 'examples/trajectory-conditions-package.json'
RECORD = 'examples/manual-candidate-challenge.json'


class CandidateChallengeTests(unittest.TestCase):
    def setUp(self):
        self.package = json.loads((ROOT / PACKAGE).read_text())
        self.record = json.loads((ROOT / RECORD).read_text())

    def test_template_neutral_and_incomplete(self):
        value = c.template(self.package)
        self.assertIsNone(value['status'])
        self.assertIs(value['holdout_inspected'], False)
        self.assertEqual({f['kind'] for f in value['findings']}, {'NOT_EXAMINED'})
        with self.assertRaises(ValueError): c.check(value, self.package)

    def test_current_counts_and_privacy(self):
        before = copy.deepcopy(self.package)
        result = c.check(self.record, self.package)
        self.assertEqual(result['binding_status'], 'CURRENT_PACKAGE')
        self.assertEqual(result['substantive_finding_count'], 1)
        self.assertEqual(result['candidate_approval'], 'NOT_DERIVED')
        self.assertNotIn('axis', result)
        for field in ('rationale', 'source_locator', 'independence_declaration', 'challengers', 'findings'):
            self.assertNotIn(field, result)
        self.assertEqual(self.package, before)

    def test_stale_never_resolves_old_ids_or_scope(self):
        self.record['version'] = 'old'
        self.record['findings'][0]['item_id'] = 'old-rule'
        self.record['scope_topics'] = ['old-topic']
        result = c.check(self.record, self.package)
        self.assertEqual(result['binding_status'], 'STALE_PACKAGE')
        self.assertFalse(result['findings_resolved_against_current_package'])
        self.assertIn('old-rule', result['unresolved_item_ids'])

    def test_unknown_current_rule_rejected(self):
        self.record['findings'][0]['item_id'] = 'absent'
        with self.assertRaises(ValueError): c.check(self.record, self.package)

    def test_package_findings_and_multiple_same_rule_allowed(self):
        f = copy.deepcopy(self.record['findings'][0]); f['finding_id'] = 'another'
        self.record['findings'].append(f)
        c.check(self.record, self.package)
        f['item_id'] = None
        c.check(self.record, self.package)

    def test_no_finding_conflicts_rejected(self):
        f = copy.deepcopy(self.record['findings'][0]); f.update(finding_id='another', kind='NO_FINDING')
        self.record['findings'].append(f)
        with self.assertRaises(ValueError): c.check(self.record, self.package)

    def test_duplicate_finding_id_rejected(self):
        self.record['findings'].append(copy.deepcopy(self.record['findings'][0]))
        with self.assertRaises(ValueError): c.check(self.record, self.package)

    def test_strict_records_and_dates(self):
        for key, value in [('holdout_inspected', True), ('holdout_inspected', 0), ('disposition', 'OPEN'),
                           ('split_declaration_sha256', None), ('challenged_at', '2026-02-30'),
                           ('challenged_at', '20261113'), ('status', None), ('schema_version', 'other'),
                           ('author_id', 'another'), ('scope_topics', []), ('findings', []),
                           ('challengers', []), ('persona_payload_sha256', 'x')]:
            with self.subTest(key=key,value=value):
                r=copy.deepcopy(self.record);r[key]=value
                with self.assertRaises(ValueError): c.check(r,self.package)

    def test_collision_rejected(self):
        self.record['challengers'][0]['challenger_id'] = self.record['author_id']
        with self.assertRaises(ValueError): c.check(self.record, self.package)

    def test_status_mixed_duplicate_and_absent(self):
        self.assertEqual(c.status(self.package)['status'], 'NOT_PERFORMED')
        old=copy.deepcopy(self.record);old['version']='old'
        s=c.status(self.package,records=[old,self.record])
        self.assertEqual((s['current_record_count'],s['stale_record_count']),(1,1))
        with self.assertRaises(ValueError): c.status(self.package,records=[self.record,self.record])

    def test_review_optional_output(self):
        kwargs=dict(question='Synthetic question?',topic=self.record['scope_topics'][0])
        old=review_package.render(self.package,**kwargs)
        self.assertEqual(old,review_package.render(self.package,challenge_records=None,**kwargs))
        new=review_package.render(self.package,challenge_records=[self.record],**kwargs)
        self.assertIn('Pre-holdout challenge record(s): RECORDED_CURRENT',new)
        self.assertNotIn(self.record['findings'][0]['rationale'],new)

    def test_shared_budget_and_strict_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'input.json';p.write_bytes(b'{}')
            read=c.bounded_reader(3);self.assertEqual(read(p),{})
            with self.assertRaises(ValueError):read(p)
            p.write_bytes(b'{"x":1,"x":2}')
            with self.assertRaises(ValueError):c.bounded_reader()(p)
        with patch.object(c,'MAX_OUTPUT_BYTES',1):
            with self.assertRaises(ValueError):c._bounded('{}')

    def test_template_exclusive(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'record.json';c.write_template(self.package,None,p)
            before=p.read_bytes()
            with self.assertRaises((ValueError,OSError)):c.write_template(self.package,None,p)
            self.assertEqual(before,p.read_bytes())

    def test_cli_and_documented_guide_commands(self):
        guide=(ROOT/'docs/CANDIDATE_CHALLENGE.md').read_text()
        with tempfile.TemporaryDirectory(prefix='candidate space ') as tmp:
            for block in re.findall(r'```sh\n(.*?)```',guide,re.S):
                for line in block.splitlines():
                    if not line.startswith('python '):continue
                    args=[part.replace('OUTPUT',tmp) for part in shlex.split(line)[1:]]
                    result=subprocess.run([sys.executable,*args],cwd=ROOT,capture_output=True)
                    self.assertEqual(result.returncode,0,(line,result.stderr))

    def test_cli_invalid_input_redacts_paths(self):
        result=subprocess.run([sys.executable,'candidate_challenge.py','check','private-secret-file',PACKAGE],cwd=ROOT,capture_output=True)
        self.assertNotEqual(result.returncode,0)
        self.assertNotIn(b'private-secret-file',result.stderr)

    def test_review_combined_budget_includes_package(self):
        with patch.object(c,'MAX_INPUT_BYTES',10), patch.object(sys,'argv',
             ['review_package.py',str(ROOT/PACKAGE),'--question','q','--topic','t','--challenge-record',str(ROOT/RECORD)]):
            with self.assertRaises(SystemExit):review_package.main()

    def test_review_all_records_share_one_reader(self):
        hv=json.loads((ROOT/'examples/manual-human-validation.json').read_text())
        # Isolate intake from rendering: prove the three optional records and package use one reader.
        paths=['package.json','challenge.json','human.json','split.json']
        supplied={paths[0]:self.package,paths[1]:self.record,paths[2]:hv,paths[3]:{}}
        calls=[]
        def read(path):
            calls.append(str(path));return supplied[str(path)]
        with patch.object(c,'bounded_reader',return_value=read) as reader, \
             patch('split_declaration.validate_declaration'), \
             patch.object(review_package,'render',return_value='synthetic\n'), \
             patch.object(review_package,'emit'), \
             patch.object(sys,'argv',['review_package.py',paths[0],'--question','q','--topic','t',
                                     '--challenge-record',paths[1],'--human-validation',paths[2],'--split',paths[3]]):
            review_package.main()
        reader.assert_called_once_with()
        self.assertEqual(calls,paths)

    def test_partial_label_collision_is_not_independence(self):
        self.record['challengers'].append(dict(challenger_id=self.record['author_id'],role='Synthetic label'))
        result=c.check(self.record,self.package)
        self.assertEqual(result['colliding_challenger_count'],1)
        self.assertEqual(result['challenger_independence'],'LABEL_DISTINCT_ONLY')

    def test_control_prose_not_echoed(self):
        secret='PRIVATE\x1b[2J\nFORGED'
        self.record['method']=secret
        self.record['findings'][0]['rationale']=secret
        self.assertNotIn('PRIVATE',json.dumps(c.check(self.record,self.package)))
        self.assertNotIn('PRIVATE',c.render_status(c.status(self.package,records=[self.record])))

    def test_invalid_record_does_not_create_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad=Path(tmp)/'bad.json';out=Path(tmp)/'out.json';bad.write_text('{}')
            result=subprocess.run([sys.executable,'candidate_challenge.py','check',str(bad),PACKAGE,'--output',str(out)],cwd=ROOT,capture_output=True)
            self.assertNotEqual(result.returncode,0);self.assertFalse(out.exists());self.assertEqual(result.stdout,b'')

    def test_dangling_symlink_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'out.json'
            try:out.symlink_to(Path(tmp)/'missing.json')
            except OSError:self.skipTest('symlink unavailable')
            with self.assertRaises((OSError,ValueError)):c.write_template(self.package,None,out)
            self.assertTrue(out.is_symlink())
