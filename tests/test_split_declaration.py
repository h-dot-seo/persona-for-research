"""Synthetic declared split isolation, hash, privacy and CLI boundaries."""
import copy
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import split_declaration as split
from persona import payload_sha256

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / 'examples'
SCRIPT = ROOT / 'split_declaration.py'


class SplitDeclarationTests(unittest.TestCase):
    def setUp(self):
        self.draft = json.loads((EXAMPLES / 'synthetic-split-declaration.json').read_text(encoding='utf-8'))
        self.package = json.loads((EXAMPLES / 'trajectory-conditions-package.json').read_text(encoding='utf-8'))
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name)

    def cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], cwd=ROOT,
                              capture_output=True, timeout=60)

    def save(self, name, value):
        path = self.out / name
        path.write_bytes((json.dumps(value) + '\n').encode())
        return path

    def package_with_id(self, paper_id):
        package = copy.deepcopy(self.package)
        package['knowledge']['papers'][0]['paper_id'] = paper_id
        package['persona']['knowledge_papers_sha256'] = payload_sha256(package['knowledge']['papers'])
        package['knowledge']['persona_payload_sha256'] = payload_sha256(package['persona'])
        return package

    def test_freeze_is_deterministic_sorted_and_does_not_mutate(self):
        original = copy.deepcopy(self.draft)
        frozen = split.freeze(self.draft)
        self.assertEqual(self.draft, original)
        self.assertEqual(frozen['status'], 'FROZEN')
        self.draft['census'].reverse()
        for values in self.draft['splits'].values():
            values.reverse()
        self.assertEqual(split.freeze(self.draft), frozen)
        self.assertEqual(frozen['declaration_sha256'], payload_sha256({k:v for k,v in frozen.items() if k != 'declaration_sha256'}))

    def test_authorization_change_changes_census_not_split_hash(self):
        a = split.freeze(self.draft)
        self.draft['census'][0]['authorized'] = False
        b = split.freeze(self.draft)
        self.assertNotEqual(a['census_sha256'], b['census_sha256'])
        self.assertNotEqual(a['declaration_sha256'], b['declaration_sha256'])
        self.assertEqual(a['split_sha256'], b['split_sha256'])

    def test_template_is_blank_and_not_freezable(self):
        record = split.template('synthetic-scholar', 'synthetic-operator')
        self.assertIsNone(record['status'])
        self.assertEqual(record['census'], [])
        with self.assertRaises(ValueError):
            split.freeze(record)
        for label in ('', 'operator' + '@' + 'example.invalid', 'bad\nlabel'):
            with self.assertRaises(ValueError):
                split.template('synthetic-scholar', label)

    def test_exact_fields_schema_dates_and_types(self):
        changes = [('schema','other'), ('status','FROZEN'), ('declared_at','2026-02-30'),
                   ('declared_at','20261113'), ('author_id', []), ('holdout_reading_declaration','')]
        for key,value in changes:
            with self.subTest(key=key,value=value):
                d=copy.deepcopy(self.draft); d[key]=value
                with self.assertRaises(ValueError): split.freeze(d)
        for action in ('extra','missing'):
            d=copy.deepcopy(self.draft)
            if action=='extra': d['unknown']=True
            else: del d['operator_id']
            with self.assertRaises(ValueError): split.freeze(d)
        for key,value in [('year', True),('year',10000),('authorized',1),('kind',[]),
                          ('record_relation','unknown'),('record_id','x\n'),('locator',''),('access_restriction','')]:
            d=copy.deepcopy(self.draft); d['census'][0][key]=value
            with self.subTest(key=key), self.assertRaises(ValueError): split.freeze(d)

    def test_census_and_split_bounds(self):
        for census in ([], {}, self.draft['census'] * (split.MAX_RECORDS + 1)):
            d=copy.deepcopy(self.draft);d['census']=census
            with self.assertRaises(ValueError): split.freeze(d)
        d=copy.deepcopy(self.draft);d['census'].append(d['census'][0])
        with self.assertRaisesRegex(ValueError,'duplicate census'): split.freeze(d)
        d=copy.deepcopy(self.draft);d['splits']['training']='not-an-array'
        with self.assertRaises(ValueError): split.freeze(d)

    def test_exact_cover_and_disjointness(self):
        for change in ('missing','unknown','repeated','overlap','extra'):
            d=copy.deepcopy(self.draft)
            if change=='missing':d['splits']['training'].pop()
            elif change=='unknown':d['splits']['training'].append('synthetic-absent')
            elif change=='repeated':d['splits']['training'].append(d['splits']['training'][0])
            elif change=='overlap':d['splits']['excluded'].append(d['splits']['training'][0])
            else:d['splits']['other']=[]
            with self.subTest(change=change), self.assertRaises(ValueError):split.freeze(d)

    def test_author_consistency_and_training_metadata(self):
        for index,field,value in [(0,'author_id','synthetic-other'),(5,'author_id','synthetic-other'),
                                  (6,'author_id','synthetic-scholar'),(0,'kind','notice'),(0,'year',None)]:
            d=copy.deepcopy(self.draft);d['census'][index][field]=value
            with self.subTest(index=index,field=field), self.assertRaises(ValueError):split.freeze(d)
        split.freeze(self.draft)  # nontraining notice and null year are allowed

    def test_relation_targets_must_be_direct_papers(self):
        for relation,target in [('paper','synthetic-2022-b'),('duplicate_of',None),('notice_of','missing'),
                                ('independent_contribution','synthetic-2020-a')]:
            d=copy.deepcopy(self.draft);d['census'][0].update(record_relation=relation,of_record_id=target)
            with self.subTest(relation=relation,target=target), self.assertRaises(ValueError):split.freeze(d)
        d=copy.deepcopy(self.draft)
        d['census'][0].update(record_relation='duplicate_of',of_record_id='synthetic-2022-b')
        d['census'][1].update(record_relation='notice_of',of_record_id='synthetic-2020-a')
        with self.assertRaises(ValueError):split.freeze(d)

    def test_related_training_and_holdout_or_comparator_is_refused(self):
        for index in (5,6):
            d=copy.deepcopy(self.draft)
            d['census'][index].update(record_relation='duplicate_of',of_record_id='synthetic-2020-a')
            with self.assertRaisesRegex(ValueError,'relation group crosses'):split.freeze(d)
        d=copy.deepcopy(self.draft)
        d['census'][0].update(record_relation='notice_of',of_record_id='synthetic-holdout-only')
        with self.assertRaisesRegex(ValueError,'relation group crosses'):split.freeze(d)

    def test_training_related_records_and_unauthorized_are_policy_counts(self):
        self.draft['census'][0].update(record_relation='duplicate_of',of_record_id='synthetic-2022-b',authorized=False)
        self.draft['census'][2].update(record_relation='notice_of',of_record_id='synthetic-2022-b')
        frozen=split.freeze(self.draft)
        self.assertEqual(split.summary(frozen)['training_policy_counts'],
                         dict(duplicate_of=1,notice_of=1,authorization_not_declared=1))
        self.assertFalse(split.summary(frozen)['policy_counts_are_verdicts'])

    def test_all_frozen_hashes_and_order_are_checked(self):
        frozen=split.freeze(self.draft)
        for change in ('census','split','declaration','order','fields','status'):
            d=copy.deepcopy(frozen)
            if change=='census':d['census'][0]['authorized']=not d['census'][0]['authorized']
            elif change=='split':d['split_sha256']['training']='0'*64
            elif change=='declaration':d['declaration_sha256']='0'*64
            elif change=='order':d['census'].reverse()
            elif change=='fields':d['unknown']=None
            else:d['status']=None
            with self.subTest(change=change), self.assertRaises(ValueError):split.check(d,self.package)

    def test_check_and_status_bound_package_forms_unchanged(self):
        frozen=split.freeze(self.draft);original=copy.deepcopy(self.package)
        a=split.check(frozen,self.package)
        self.assertEqual(a['status'],'PACKAGE_WITHIN_DECLARED_TRAINING')
        self.assertEqual(a['package_paper_count'],5)
        self.assertEqual(a,split.check(frozen,{'package':self.package}))
        self.assertEqual(a,split.check(frozen,self.package['persona'],self.package['knowledge']))
        self.assertEqual(a,split.status(self.package,record=frozen))
        self.assertEqual(self.package,original)
        self.assertEqual(split.status(self.package)['status'],'NOT_DECLARED')

    def test_check_rejects_unbound_packages(self):
        self.package['knowledge']['persona_payload_sha256']='0'*64
        with self.assertRaises(ValueError):split.check(split.freeze(self.draft),self.package)

    def test_package_conflicts_include_only_already_present_ids(self):
        frozen=split.freeze(self.draft)
        for name,code in [('holdout','HOLDOUT_ID_IN_PACKAGE'),('comparator','COMPARATOR_ID_IN_PACKAGE'),
                          ('excluded','PACKAGE_PAPER_NOT_IN_TRAINING_SPLIT')]:
            pid='synthetic-'+name+'-only'
            result=split.check(frozen,self.package_with_id(pid))
            self.assertEqual(result['status'],'PACKAGE_OUTSIDE_DECLARED_TRAINING')
            self.assertIn(dict(paper_id=pid,code=code),result['differences'])
            rendered=split.render(result)
            for other in ('holdout','comparator','excluded'):
                if other!=name:self.assertNotIn('synthetic-'+other+'-only',rendered)
        self.assertEqual(split.check(frozen,self.package_with_id('synthetic-not-listed'))['status'],
                         'PACKAGE_OUTSIDE_DECLARED_TRAINING')

    def test_metadata_mismatch_and_author_mismatch_are_reported(self):
        for field,value in [('kind','review'),('year',2021),('authorized',False)]:
            d=copy.deepcopy(self.draft);d['census'][0][field]=value
            result=split.check(split.freeze(d),self.package)
            self.assertIn(dict(paper_id='synthetic-2020-a',code='TRAINING_METADATA_MISMATCH',field=field),result['differences'])
        d=copy.deepcopy(self.draft);d['author_id']='synthetic-other'
        for row in d['census']:
            if row['author_id']=='synthetic-scholar':row['author_id']='synthetic-other'
        self.assertIn(dict(code='AUTHOR_LABEL_MISMATCH'),split.check(split.freeze(d),self.package)['differences'])

    def test_receipt_reports_and_errors_do_not_echo_withheld_ids(self):
        frozen=split.freeze(self.draft)
        for value in (split.summary(frozen),split.check(frozen,self.package),split.status(self.package,record=frozen)):
            for name in ('holdout','comparator','excluded'):
                self.assertNotIn('synthetic-'+name+'-only',json.dumps(value))
        for name in ('holdout','comparator','excluded'):
            self.assertNotIn('synthetic-'+name+'-only',split.render(split.check(frozen,self.package)))
        d=copy.deepcopy(self.draft);d['splits']['training'].append('synthetic-holdout-only')
        with self.assertRaises(ValueError) as caught:split.freeze(d)
        self.assertNotIn('synthetic-holdout-only',str(caught.exception))

    def test_cli_template_freeze_check_status_and_no_overwrite(self):
        blank=self.out/'blank.json'
        result=self.cli('template','--author-id','synthetic-scholar','--operator-id','synthetic-operator','--output',blank)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'],'SPLIT_TEMPLATE_WRITTEN')
        self.assertNotEqual(self.cli('freeze',blank,'--output',self.out/'invalid.json').returncode,0)
        dest=self.out/'frozen.json'
        args=('freeze',EXAMPLES/'synthetic-split-declaration.json','--output',dest)
        result=self.cli(*args);self.assertEqual(result.returncode,0,result.stderr)
        data=dest.read_bytes(); self.assertNotIn(b'\r',data)
        self.assertNotEqual(self.cli(*args).returncode,0);self.assertEqual(dest.read_bytes(),data)
        for command in [('check',dest,EXAMPLES/'trajectory-conditions-package.json'),
                        ('status',EXAMPLES/'trajectory-conditions-package.json','--split',dest)]:
            got=self.cli(*command);self.assertEqual(got.returncode,0,got.stderr)
            self.assertEqual(json.loads(got.stdout)['status'],'PACKAGE_WITHIN_DECLARED_TRAINING')
            text=self.cli(*command,'--text');self.assertEqual(text.returncode,0,text.stderr)
            self.assertIn(b'Boundary:',text.stdout)
            for name in ('holdout','comparator','excluded'):
                self.assertNotIn(('synthetic-'+name+'-only').encode(),got.stdout+text.stdout+result.stdout)
        report=self.out/'report.json'
        got=self.cli('check',dest,EXAMPLES/'trajectory-conditions-package.json','--output',report)
        self.assertEqual(got.returncode,0,got.stderr)
        self.assertEqual(json.loads(got.stdout)['status'],'SAVED')
        self.assertEqual(json.loads(report.read_bytes())['status'],'PACKAGE_WITHIN_DECLARED_TRAINING')

    def test_cli_check_nonzero_but_status_reports_conflict(self):
        frozen=self.save('frozen.json',split.freeze(self.draft))
        package=self.save('package.json',self.package_with_id('synthetic-holdout-only'))
        checked=self.cli('check',frozen,package)
        self.assertEqual(checked.returncode,1,checked.stderr)
        self.assertEqual(json.loads(checked.stdout)['status'],'PACKAGE_OUTSIDE_DECLARED_TRAINING')
        status=self.cli('status',package,'--split',frozen,'--text')
        self.assertEqual(status.returncode,0,status.stderr)
        self.assertIn(b'PACKAGE_OUTSIDE_DECLARED_TRAINING',status.stdout)

    def test_output_preflight_precedes_input_and_refuses_repository(self):
        existing=self.save('existing.json',{})
        result=self.cli('freeze',self.out/'missing.json','--output',existing)
        self.assertIn(b'output already exists',result.stderr)
        self.assertNotIn(b'missing.json',result.stderr)
        result=self.cli('freeze',EXAMPLES/'synthetic-split-declaration.json','--output',ROOT/'new-split.json')
        self.assertNotEqual(result.returncode,0)
        self.assertFalse((ROOT/'new-split.json').exists())

    def test_symlink_input_and_output_are_refused(self):
        target=self.save('target.json',self.draft);link=self.out/'link.json'
        try:link.symlink_to(target)
        except (OSError,NotImplementedError):self.skipTest('symlink creation unavailable')
        result=self.cli('freeze',link,'--output',self.out/'frozen.json')
        self.assertNotEqual(result.returncode,0);self.assertIn(b'symlink',result.stderr)
        link.unlink();link.symlink_to(self.out/'absent.json')
        result=self.cli('freeze',target,'--output',link)
        self.assertNotEqual(result.returncode,0);self.assertFalse((self.out/'absent.json').exists())

    def test_shared_input_and_output_byte_budgets_and_strict_json(self):
        a=self.out/'a.json';a.write_bytes(b'{}')
        with mock.patch.object(split,'MAX_INPUT_BYTES',3):
            read=split.bounded_reader();self.assertEqual(read(a),{})
            with self.assertRaisesRegex(ValueError,'combined'):read(a)
        for raw in (b'{"a":1,"a":2}', b'{"x":NaN}', b'\xff'):
            a.write_bytes(raw)
            with self.assertRaises(ValueError):split.bounded_reader()(a)
        with mock.patch.object(split,'MAX_OUTPUT_BYTES',2):
            with self.assertRaises(ValueError):split.encode({'x':1})

    def test_cli_private_parser_diagnostics_are_redacted(self):
        secret = 'SYNTHETIC-PRIVATE-WITHHELD-KEY'
        source = self.out / 'private.json'
        for raw in (('{"' + secret + '":1,"' + secret + '":2}').encode(),
                    bytes([255]), ('{"' + secret + '":').encode()):
            source.write_bytes(raw)
            result = self.cli('freeze', source, '--output', self.out / 'not-created.json')
            self.assertEqual(result.returncode, 1)
            self.assertIn(b'invalid strict JSON input; details withheld', result.stderr)
            self.assertNotIn(secret.encode(), result.stderr + result.stdout)
            self.assertFalse((self.out / 'not-created.json').exists())

    def test_documented_shell_commands_run_without_redirection(self):
        text=(ROOT/'docs/SPLIT_DECLARATION.md').read_text(encoding='utf-8')
        import shlex
        blocks=re.findall(r'```sh\n(.*?)```',text,re.S)
        self.assertTrue(blocks)
        for block in blocks:
            for line in block.splitlines():
                if not line.strip() or line.startswith('#'):continue
                # Parse the documented POSIX command before inserting native paths.
                # Otherwise Windows backslashes are consumed as shell escapes.
                argv=[arg.replace('OUTPUT',str(self.out)) for arg in shlex.split(line)]
                self.assertEqual(argv[0],'python')
                result=subprocess.run([sys.executable,*argv[1:]],cwd=ROOT,capture_output=True,timeout=60)
                self.assertEqual(result.returncode,0,(line,result.stderr))
        self.assertTrue((self.out/'synthetic-frozen.json').exists())


if __name__=='__main__':
    unittest.main()
