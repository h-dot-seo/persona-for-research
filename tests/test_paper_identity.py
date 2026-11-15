"""Synthetic CSL copying and current-source binding, not authenticated bibliography."""
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import paper_identity as p
from research_workflow import build
from persona import payload_sha256
import review_package

ROOT=Path(__file__).resolve().parents[1]

class PaperIdentityTests(unittest.TestCase):
    def setUp(self):
        self.package=json.loads((ROOT/'examples/trajectory-conditions-package.json').read_bytes())
        self.raw=(ROOT/'examples/synthetic-paper-identity-export.csl.json').read_bytes()
        self.mapping=json.loads((ROOT/'examples/synthetic-paper-identity-mapping.json').read_bytes())
        self.record=json.loads((ROOT/'examples/synthetic-paper-identities.json').read_bytes())
    def make(self,raw=None,mapping=None):return p.from_csl(self.package,self.raw if raw is None else raw,self.mapping if mapping is None else mapping,'synthetic-bibliography-operator','2026-11-15')
    def reseal(self,record):
        record.pop('payload_sha256',None);record['payload_sha256']=payload_sha256(record);return record
    def rebuilt(self,edit):
        corpus={k:self.package['persona'][k] for k in ('author_id','version','build_id')};corpus['papers']=copy.deepcopy(self.package['knowledge']['papers']);edit(corpus)
        return build(corpus)
    def test_template_and_exact_replay_partial_mapping_and_no_body_copy(self):
        empty=p.template(self.package,'synthetic','2026-11-15');p.validate_record(empty)
        self.assertTrue(all(r['status']=='NOT_DECLARED' for r in empty['papers']))
        self.assertTrue(all(all(v is None for v in r['identifiers'].values()) for r in empty['papers']))
        with self.assertRaises(ValueError):p.verify(empty,self.raw,self.mapping)
        self.assertEqual(self.make(),self.record);report=p.verify(self.record,self.raw,self.mapping)
        self.assertEqual(report['replayed_rows'],2);self.assertEqual(report['unmapped_export_occurrences'],1)
        text=json.dumps(self.record)
        for hidden in ('SYNTHETIC_OMITTED_ABSTRACT','SYNTHETIC_OMITTED_NOTE','same-private-id','SYNTHETIC_UNMAPPED_TITLE'):
            self.assertNotIn(hidden,text);self.assertNotIn(hidden,json.dumps(report))
        self.assertEqual(sum(r['status']=='NOT_DECLARED' for r in self.record['papers']),3)
    def test_current_package_stale_only_sources_differ_absent_and_new(self):
        self.assertEqual(p.check(self.record,self.package)['package_binding_status'],'CURRENT_PACKAGE')
        newer=self.rebuilt(lambda c:c.update(version='synthetic-new',build_id='synthetic-new'))
        result=p.check(self.record,newer);self.assertEqual(result['package_binding_status'],'STALE_PACKAGE')
        self.assertTrue(result['rows'][0]['values_displayed']);self.assertEqual(result['rows'][0]['source_binding_status'],'SOURCE_HASH_MATCH')
        changed=self.rebuilt(lambda c:c['papers'][0].update(source_sha256='f'*64))
        result=p.check(self.record,changed);self.assertEqual(result['rows'][0]['source_binding_status'],'SOURCE_HASH_DIFFERS')
        self.assertNotIn('identifiers',result['rows'][0]);self.assertNotIn('declared_title',result['rows'][0]);self.assertNotIn('10.0000/fictional-A',json.dumps(result))
        absent=self.rebuilt(lambda c:c['papers'].pop(0));result=p.check(self.record,absent)
        self.assertEqual(result['rows'][0]['source_binding_status'],'PAPER_ID_ABSENT');self.assertFalse(result['rows'][0]['values_displayed'])
        def add(c):
            row=copy.deepcopy(c['papers'][-1]);row['paper_id']='synthetic-new-paper';c['papers'].append(row)
        result=p.check(self.record,self.rebuilt(add));self.assertEqual(result['new_package_papers_not_declared'],['synthetic-new-paper'])
        def author(c):
            c['author_id']='other-synthetic'
            for row in c['papers']:row['author_id']='other-synthetic'
        with self.assertRaises(ValueError):p.check(self.record,self.rebuilt(author))
    def test_self_digest_is_not_authentication_and_consumer_does_not_replay(self):
        forged=copy.deepcopy(self.record);forged['papers'][0]['identifiers']['doi']='10.0000/fictional-forged'
        with self.assertRaises(ValueError):p.check(forged,self.package)
        self.reseal(forged);checked=p.check(forged,self.package)
        self.assertEqual(checked['rows'][0]['identifiers']['doi'],'10.0000/fictional-forged')
        self.assertEqual(checked['export_copy_replayed'],'NOT_PERFORMED');self.assertFalse(checked['identity_verified'])
        with self.assertRaises(ValueError):p.verify(forged,self.raw,self.mapping)
    def test_occurrences_not_typed_csl_ids_and_reorder_fail_closed(self):
        entries=json.loads(self.raw);self.assertEqual(entries[0]['id'],entries[1]['id'])
        self.assertEqual([r['source_export']['census_id'] for r in self.record['papers'][:2]],['census-000001','census-000002'])
        for raw in (self.raw+b'\n',json.dumps(list(reversed(entries))).encode()):
            with self.assertRaises(ValueError):self.make(raw)
            with self.assertRaises(ValueError):p.verify(self.record,raw,self.mapping)
        bad=copy.deepcopy(self.mapping);bad['papers'][0]['entry_sha256']='0'*64
        with self.assertRaises(ValueError):self.make(mapping=bad)
    def test_unknown_duplicate_mapping_and_repeated_occurrence_explicit(self):
        for mode in ('unknown','duplicate','out-of-range','wrong-type','null'):
            m=copy.deepcopy(self.mapping)
            if mode=='unknown':m['papers'][0]['paper_id']='holdout-not-runtime'
            elif mode=='duplicate':m['papers'].append(copy.deepcopy(m['papers'][0]))
            elif mode=='out-of-range':m['papers'][0]['census_id']='census-999999'
            elif mode=='wrong-type':m['papers'][0]['census_id']=1
            else:m=None
            with self.assertRaises((ValueError,TypeError)):p.from_csl(self.package,self.raw,m,'synthetic','2026-11-15')
        m=copy.deepcopy(self.mapping);m['papers'][1].update(census_id=m['papers'][0]['census_id'],entry_sha256=m['papers'][0]['entry_sha256'])
        record=self.make(mapping=m);self.assertEqual(p.verify(record,self.raw,m)['replayed_rows'],2)
        self.assertEqual(p.verify(record,self.raw,m)['unmapped_export_occurrences'],2)
    def test_doi_exact_ascii_fold_no_normalization_and_year_prompts(self):
        result=p.check(self.record,self.package)
        self.assertEqual(result['exact_declared_doi_groups'],[]);self.assertEqual(len(result['ascii_casefold_declared_doi_groups']),1)
        self.assertEqual(result['rows'][0]['identifiers']['doi'],'10.0000/fictional-A')
        rows=[dict(paper_id='a',identifiers={'doi':'ÄA'}),dict(paper_id='b',identifiers={'doi':'äa'})]
        self.assertEqual(p._doi_groups(rows,True),[])
        record=copy.deepcopy(self.record);record['papers'][0]['declared_year']=None;self.reseal(record)
        self.assertIn('ISSUED_YEAR_NOT_SUPPLIED',p.check(record,self.package)['rows'][0]['prompts'])
    def test_lengths_dates_types_and_unknown_fields(self):
        for key,limit in [('doi',128),('pmid',128),('pmcid',128),('isbn',128),('url',2048)]:
            r=copy.deepcopy(self.record);r['papers'][0]['identifiers'][key]='x'*limit;self.reseal(r);p.validate_record(r)
            r['papers'][0]['identifiers'][key]+='x';self.reseal(r)
            with self.assertRaises(ValueError):p.validate_record(r)
        r=copy.deepcopy(self.record);r['papers'][0]['declared_title']='x'*2000;self.reseal(r);p.validate_record(r)
        r['papers'][0]['declared_title']+='x';self.reseal(r)
        with self.assertRaises(ValueError):p.validate_record(r)
        for year in (True,0,10000,1.0):
            r=copy.deepcopy(self.record);r['papers'][0]['declared_year']=year;self.reseal(r)
            with self.assertRaises(ValueError):p.validate_record(r)
        for date in ('2026-02-30','not-date'):
            with self.assertRaises(ValueError):p.template(self.package,'synthetic',date)
        for path in ((),('papers',0),('papers',0,'identifiers'),('papers',0,'source_export')):
            r=copy.deepcopy(self.record);obj=r
            for key in path:obj=obj[key]
            obj['unknown']='private';self.reseal(r)
            with self.assertRaises(ValueError):p.validate_record(r)
    def test_export_encoding_record_caps_and_empty_year(self):
        for raw in (self.raw.decode().encode('utf-16'),b'\x00',b'[]',b'[null]',b'{"not":"array"}',b'[NaN]'):
            with self.assertRaises((ValueError,UnicodeError)):self.make(raw)
        rows=json.loads(self.raw);raw=b'\xef\xbb\xbf'+self.raw;m=copy.deepcopy(self.mapping);m['export_sha256']=hashlib.sha256(raw).hexdigest()
        self.assertEqual(self.make(raw,m)['papers'],self.record['papers'])
        with patch.object(p,'MAX_ROWS',2),self.assertRaises(ValueError):self.make()
        self.assertIsNone(p.year({'issued':{'date-parts':[[True]]}}));self.assertEqual(p.year({'issued':{'date-parts':[['2020']]}}),2020)
        with patch.object(p,'MAX_OUTPUT_BYTES',10),self.assertRaises(ValueError):p.encode(self.record)
    def test_shared_input_budget_exact_raw_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            a=Path(td)/'a.json';b=Path(td)/'b.json';a.write_bytes(b'{}');b.write_bytes(b'[]')
            with patch.object(p,'MAX_INPUT_BYTES',4):read=p.reader();self.assertEqual(read(a),{});self.assertEqual(read(b),[])
            with patch.object(p,'MAX_INPUT_BYTES',3):
                read=p.reader();read(a)
                with self.assertRaises(ValueError):read(b)
    def test_inputs_unchanged_and_no_network(self):
        before=copy.deepcopy((self.package,self.mapping,self.record))
        with patch('socket.socket',side_effect=AssertionError('no network')):
            made=self.make();p.verify(made,self.raw,self.mapping);p.check(made,self.package)
        self.assertEqual(before,(self.package,self.mapping,self.record))
    def cli(self,*args):return subprocess.run([sys.executable,*map(str,args)],cwd=ROOT,capture_output=True,timeout=30)
    def test_cli_fixed_error_empty_stdout_preflight_and_exclusive(self):
        with tempfile.TemporaryDirectory(prefix='identity space ') as td:
            d=Path(td).resolve();bad=d/'bad.json';bad.write_bytes(b'null');out=d/'out.json'
            run=self.cli('paper_identity.py','check',bad,'examples/trajectory-conditions-package.json','--output',out)
            self.assertEqual((run.returncode,run.stdout,run.stderr),(1,b'',('Invalid paper identity input.'+os.linesep).encode()));self.assertFalse(out.exists())
            out.write_bytes(b'keep');run=self.cli('paper_identity.py','template',bad,'--operator-id','synthetic','--declared-at','2026-11-15','--output',out)
            self.assertEqual((run.returncode,run.stdout),(1,b''));self.assertEqual(out.read_bytes(),b'keep')
    def test_review_option_append_only_and_masking(self):
        args=['review_package.py','examples/trajectory-conditions-package.json','--question','Synthetic question','--topic','model design']
        base=self.cli(*args);new=self.cli(*args,'--paper-identities','examples/synthetic-paper-identities.json')
        self.assertEqual((base.returncode,new.returncode),(0,0));self.assertTrue(new.stdout.startswith(base.stdout));self.assertIn(b'DECLARED_NOT_RESOLVED',new.stdout)
        with tempfile.TemporaryDirectory() as td:
            d=Path(td);package=self.rebuilt(lambda c:c['papers'][0].update(source_sha256='f'*64));path=d/'package.json';path.write_bytes(json.dumps(package).encode())
            run=self.cli('review_package.py',path,'--question','Synthetic','--topic','model design','--paper-identities','examples/synthetic-paper-identities.json')
            self.assertEqual(run.returncode,0,run.stderr);section=run.stdout.split(b'Detached bibliography',1)[1];self.assertNotIn(b'10.0000/fictional-A',section);self.assertIn(b'SOURCE_HASH_DIFFERS',section)
    def test_creation_rejects_package_identity_beyond_sidecar_limits(self):
        for field in ('version','build_id'):
            package=self.rebuilt(lambda c:c.update(**{field:'x'*2001}))
            with self.assertRaises(ValueError):p.template(package,'synthetic','2026-11-15')
        package=self.rebuilt(lambda c:c['papers'][0].update(paper_id='x'*2001))
        with self.assertRaises(ValueError):p.template(package,'synthetic','2026-11-15')
        for value in ('', ' '):
            entries=json.loads(self.raw);entries[0]['DOI']=value;raw=json.dumps(entries).encode()
            mapping=copy.deepcopy(self.mapping);mapping['export_sha256']=hashlib.sha256(raw).hexdigest();mapping['papers'][0]['entry_sha256']=payload_sha256(entries[0])
            with self.assertRaises(ValueError):self.make(raw,mapping)
        entries=json.loads(self.raw);entries[0]['issued']={'literal':'not a parsed year'};raw=json.dumps(entries).encode()
        mapping=copy.deepcopy(self.mapping);mapping['export_sha256']=hashlib.sha256(raw).hexdigest();mapping['papers'][0]['entry_sha256']=payload_sha256(entries[0])
        record=self.make(raw,mapping);self.assertIsNone(record['papers'][0]['declared_year']);p.validate_record(record);p.verify(record,raw,mapping)

    def test_all_exact_object_missing_keys_reject_and_generated_record_roundtrips(self):
        for path in ((),('papers',0),('papers',0,'identifiers'),('papers',0,'source_export')):
            target=self.record
            for key in path:target=target[key]
            for removed in target:
                record=copy.deepcopy(self.record);obj=record
                for key in path:obj=obj[key]
                del obj[removed]
                if removed!='payload_sha256':self.reseal(record)
                with self.assertRaises(ValueError):p.validate_record(record)
        for record in (self.make(),p.template(self.package,'synthetic','2026-11-15')):
            p.validate_record(record);self.assertEqual(p.check(record,self.package)['package_binding_status'],'CURRENT_PACKAGE')

    def test_explicit_null_bibliography_split_and_legacy_release_behavior(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'null.json';path.write_bytes(b'null')
            base=['review_package.py','examples/trajectory-conditions-package.json','--question','Synthetic','--topic','model design']
            nullrecord=self.cli(*base,'--paper-identities',path)
            self.assertEqual((nullrecord.returncode,nullrecord.stdout),(1,b''))
            for flag in ('--split','--release-decision'):
                old=self.cli(*base,flag,path);new=self.cli(*base,flag,path,'--paper-identities','examples/synthetic-paper-identities.json')
                if flag=='--split':self.assertEqual((old.returncode,new.returncode,new.stdout),(1,1,b''))
                else:self.assertEqual((old.returncode,new.returncode),(0,0));self.assertTrue(new.stdout.startswith(old.stdout))

    def test_cli_output_input_budget_asymmetry_is_not_a_new_creation_limit(self):
        import contextlib,io
        package_path=ROOT/'examples/trajectory-conditions-package.json'
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'never.json'
            args=['paper_identity.py','from-csl',str(package_path),str(ROOT/'examples/synthetic-paper-identity-export.csl.json'),str(ROOT/'examples/synthetic-paper-identity-mapping.json'),'--operator-id','synthetic-bibliography-operator','--declared-at','2026-11-15','--output',str(out)]
            # Creation's original inputs fit, but exact declaration + package does not.
            limit=len(p.encode(self.record))+len(package_path.read_bytes())-1
            original_size=len(package_path.read_bytes())+len(self.raw)+len((ROOT/'examples/synthetic-paper-identity-mapping.json').read_bytes())
            self.assertLess(original_size,limit)
            capture=io.BytesIO();stdout=io.TextIOWrapper(capture,encoding='utf-8')
            with patch.object(sys,'argv',args),patch.object(sys,'stdout',stdout),patch.object(p,'MAX_INPUT_BYTES',limit):
                p.main();stdout.flush();self.assertEqual(json.loads(capture.getvalue())['status'],'SAVED')
            self.assertEqual(json.loads(out.read_bytes()),self.record)
            # A structurally valid result can exceed a later combined input budget.
            later=['paper_identity.py','check',str(out),str(package_path)]
            with patch.object(sys,'argv',later),patch.object(p,'MAX_INPUT_BYTES',limit),contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as ex:p.main()
            self.assertEqual(ex.exception.code,1);p.validate_record(json.loads(out.read_bytes()))


    def test_actual_synthetic_guide(self):
        blocks=re.findall(r'```sh\n(.*?)```',(ROOT/'docs/PAPER_IDENTITY.md').read_text(),re.S);self.assertEqual(len(blocks),1)
        with tempfile.TemporaryDirectory(prefix='bibliography guide space ') as td:
            mapping={'OUTPUT/'+n:str(Path(td)/n) for n in ('empty.json','declared.json','replay.json','check.json','review.txt')}
            lines=blocks[0].splitlines();self.assertEqual(len(lines),5)
            for line in lines:
                tokens=shlex.split(line);self.assertEqual(tokens[0],'python');args=[mapping.get(t,t) for t in tokens[1:]]
                run=self.cli(*args);self.assertEqual(run.returncode,0,run.stderr)
            self.assertEqual(json.loads((Path(td)/'declared.json').read_bytes()),self.record)
            self.assertEqual(json.loads((Path(td)/'check.json').read_bytes())['package_binding_status'],'CURRENT_PACKAGE')
            self.assertIn(b'NOT_PERFORMED',(Path(td)/'review.txt').read_bytes())

if __name__=='__main__':unittest.main()
