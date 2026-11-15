"""Synthetic RIS occurrence declarations and separate timeline display."""
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
import census_import as census
import publication_timeline as timeline
from persona import payload_sha256

ROOT=Path(__file__).resolve().parents[1]
RAW=('TY  - JOUR\nTI  - Synthetic 한국어 title\n      continued\nPY  - 2020/99/99\nDO  - SYNTHETIC-DOI-A\nID  - duplicate-id\nAN  - private-accession\nAB  - private-abstract\nN1  - private-note\nER  -\n'
     'TY  - JOUR\nT1  - Another synthetic title\nY1  - 2021\nDO  - synthetic-doi-a\nID  - duplicate-id\nER  -\n').encode('utf-8')

class RISIdentityTests(unittest.TestCase):
    def setUp(self):
        self.package=json.loads((ROOT/'examples/trajectory-conditions-package.json').read_bytes())
        self.topic=self.package['persona']['rules'][0]['topic'];self.paper=self.package['knowledge']['papers'][0]['paper_id']
        self.mapping=self.mapping_for(RAW)
        self.record=self.make(RAW)
    def mapping_for(self,raw):
        entries,digest=p._ris_export(raw)
        return dict(schema=p.MAP_SCHEMA,export_sha256=digest,papers=[dict(paper_id=self.paper,census_id='census-000001',entry_sha256=payload_sha256(entries[0]))])
    def make(self,raw):return p.from_ris(self.package,raw,self.mapping_for(raw),'synthetic-ris-operator','2026-11-15')
    def cli(self,script,*args):return subprocess.run([sys.executable,str(ROOT/script),*map(str,args)],cwd=ROOT,capture_output=True)
    def test_census_same_ordered_hash_and_private_omission(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'export.ris';path.write_bytes(RAW);result=census.import_ris(path)
        self.assertEqual(result['entries'][0]['entry_sha256'],self.mapping['papers'][0]['entry_sha256'])
        self.assertEqual(result['export_sha256'],self.mapping['export_sha256'])
        self.assertEqual(self.record['schema'],p.RIS_SCHEMA)
        row=self.record['papers'][0];self.assertEqual(row['declared_title'],'Synthetic 한국어 title\ncontinued');self.assertEqual(row['declared_year'],2020)
        self.assertEqual(row['identifiers'],dict(doi='SYNTHETIC-DOI-A',pmid=None,pmcid=None,isbn=None,url=None))
        for private in ('private-accession','private-abstract','private-note','duplicate-id'):self.assertNotIn(private,p.encode(self.record).decode())
        self.assertEqual(p.verify(self.record,RAW,self.mapping)['status'],'RIS_COPY_REPLAY_MATCH_NOT_AUTHENTICATED')
    def test_bom_and_three_newlines_preserve_logical_hash_not_raw_hash(self):
        expected=self.mapping['papers'][0]['entry_sha256']
        for newline in (b'\n',b'\r\n',b'\r'):
            for bom in (b'',b'\xef\xbb\xbf'):
                raw=bom+RAW.replace(b'\n',newline);mapping=self.mapping_for(raw)
                self.assertEqual(mapping['papers'][0]['entry_sha256'],expected)
                record=self.make(raw);p.verify(record,raw,mapping)
                if raw!=RAW:
                    self.assertNotEqual(record['export_sha256'],self.record['export_sha256'])
                    with self.assertRaises(ValueError):p.verify(self.record,raw,self.mapping)
    def test_alias_conflicts_equal_alias_and_explicit_year(self):
        for field in (b'TI  - different\n',b'T1  - different\n',b'PY  - 2021\n',b'Y1  - 2020\n',b'DO  - other\n'):
            raw=RAW.replace(b'ER  -\n',field+b'ER  -\n',1)
            with self.assertRaises(ValueError):self.make(raw)
        raw=RAW.replace(b'ER  -\n',b'Y1  - 2020/99/99\nDO  - SYNTHETIC-DOI-A\nER  -\n',1)
        self.assertEqual(self.make(raw)['papers'][0]['declared_year'],2020)
        for literal,expected in ((b'2022',2022),(b'2022/',2022),(b'2022/99/99',2022),(b'circa 2022',None),(b'2022-01-01',None),(b'',None)):
            raw=RAW.replace(b'2020/99/99',literal);self.assertEqual(self.make(raw)['papers'][0]['declared_year'],expected)
        with self.assertRaises(ValueError):self.make(RAW.replace(b'2020/99/99',b'0000'))
    def test_all_tags_order_and_occurrences_bound(self):
        for raw in (RAW.replace(b'private-note',b'changed-note'),RAW.replace(b'ID  - duplicate-id\nAN  - private-accession',b'AN  - private-accession\nID  - duplicate-id')):
            self.assertNotEqual(self.mapping_for(raw)['papers'][0]['entry_sha256'],self.mapping['papers'][0]['entry_sha256'])
            with self.assertRaises(ValueError):p.from_ris(self.package,raw,self.mapping,'synthetic','2026-11-15')
        records=RAW.split(b'ER  -\n');reordered=records[1]+b'ER  -\n'+records[0]+b'ER  -\n'
        with self.assertRaises(ValueError):p.from_ris(self.package,reordered,self.mapping,'synthetic','2026-11-15')
        m=copy.deepcopy(self.mapping);m['papers'].append(copy.deepcopy(m['papers'][0]))
        with self.assertRaises(ValueError):p.from_ris(self.package,RAW,m,'synthetic','2026-11-15')
    def test_verify_dispatch_and_forged_copy(self):
        v=copy.deepcopy(self.record);v['papers'][0]['declared_title']='Forged supplied title';v.pop('payload_sha256');v=p._seal(v)
        self.assertIn('Forged supplied title',p.render(p.check(v,self.package)))
        with self.assertRaises(ValueError):p.verify(v,RAW,self.mapping)
        csl=json.loads((ROOT/'examples/synthetic-paper-identities.json').read_bytes())
        with self.assertRaises(ValueError):p.verify(csl,RAW,self.mapping)
        v=copy.deepcopy(self.record);v['schema']=p.SCHEMA;v['payload_sha256']=payload_sha256({k:x for k,x in v.items() if k!='payload_sha256'})
        with self.assertRaises(ValueError):p.validate_record(v)
    def test_row_visibility_independent_package_staleness(self):
        v=copy.deepcopy(self.record);v['version']='old-version';v.pop('payload_sha256');v=p._seal(v)
        result=p.check(v,self.package);self.assertEqual(result['package_binding_status'],'STALE_PACKAGE');self.assertTrue(result['rows'][0]['values_displayed'])
        for mode in ('hash','absent'):
            x=copy.deepcopy(v)
            if mode=='hash':x['papers'][0]['source_sha256']='0'*64
            else:x['papers'][0]['paper_id']='absent-synthetic-paper'
            x.pop('payload_sha256');x=p._seal(x);out=p.check(x,self.package)
            self.assertFalse(out['rows'][0]['values_displayed']);self.assertNotIn('declared_title',out['rows'][0])
    def test_bounds_encoding_and_existing_csl(self):
        for raw in (RAW.decode('utf-8').encode('utf-16'),RAW+b'\0',b'not RIS',RAW.replace(b'SYNTHETIC-DOI-A',b'x'*129)):
            with self.assertRaises(ValueError):self.make(raw)
        with patch.object(p,'MAX_ROWS',1):
            with self.assertRaises(ValueError):p._ris_export(RAW)
        with patch.object(p,'MAX_INPUT_BYTES',len(RAW)-1):
            with self.assertRaises(ValueError):p._ris_export(RAW)
        with patch.object(p,'MAX_OUTPUT_BYTES',1):
            with self.assertRaises(ValueError):self.make(RAW)
        raw=(ROOT/'examples/synthetic-paper-identity-export.csl.json').read_bytes();mapping=json.loads((ROOT/'examples/synthetic-paper-identity-mapping.json').read_bytes())
        self.assertEqual(p.from_csl(self.package,raw,mapping,'synthetic-bibliography-operator','2026-11-15'),json.loads((ROOT/'examples/synthetic-paper-identities.json').read_bytes()))
    def test_timeline_default_and_opt_in_no_mutation(self):
        from types import SimpleNamespace
        before=copy.deepcopy((self.package,self.record))
        with tempfile.TemporaryDirectory(prefix='RIS timeline space ') as temp:
            root=Path(temp);package=root/'package.json';record=root/'record.json';null=root/'null.json'
            package.write_bytes(p.encode(self.package));record.write_bytes(p.encode(self.record));null.write_bytes(b'null')
            for relations in (None,null):
                for format in ('json','text'):
                    args=SimpleNamespace(package=package,paper_identities=record,publication_relations=relations,topic=self.topic,format=format)
                    out=p.encode(json.loads(timeline._with_paper_identities(args))) if format=='json' else timeline._with_paper_identities(args)
                    if format=='json':
                        result=json.loads(out);review=result.pop('paper_identity_review');result.pop('paper_identity_input_sha256')
                        self.assertEqual(result,timeline.timeline(self.package,self.topic));self.assertEqual(review,p.check(self.record,self.package))
                    else:self.assertTrue(out.startswith(timeline.render(self.package,self.topic)))
            args.paper_identities=null
            with self.assertRaises(ValueError):timeline._with_paper_identities(args)
        self.assertEqual((self.package,self.record),before)
    def test_timeline_relationship_forms_and_budgets(self):
        from types import SimpleNamespace
        from publication_context import template
        form=template(self.package,'synthetic-relations')
        other=self.package['knowledge']['papers'][1]['paper_id']
        filled=copy.deepcopy(form);filled['relations']=[dict(relation_id='synthetic-relation',from_paper_id=self.paper,to_paper_id=other,relation_type='method_extension_of',rationale='Synthetic declared relation',basis_refs=[dict(paper_id=self.paper,observation_index=0,dimension=None)],uncertainty=None)]
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);package=root/'package.json';record=root/'record.json';relations=root/'relations.json'
            package.write_bytes(p.encode(self.package));record.write_bytes(p.encode(self.record))
            for value in (form,filled):
                relations.write_bytes(p.encode(value))
                for format in ('json','text'):
                    args=SimpleNamespace(package=package,paper_identities=record,publication_relations=relations,topic=self.topic,format=format)
                    output=timeline._with_paper_identities(args)
                    if format=='json':
                        result=json.loads(output);result.pop('paper_identity_review');result.pop('paper_identity_input_sha256')
                        self.assertEqual(result,timeline.timeline(self.package,self.topic,value))
                    else:self.assertTrue(output.startswith(timeline.render(self.package,self.topic,value)))
            with patch.object(p,'MAX_INPUT_BYTES',sum(path.stat().st_size for path in (package,record,relations))-1):
                with self.assertRaises(ValueError):timeline._with_paper_identities(args)
            with patch.object(p,'MAX_OUTPUT_BYTES',10000),patch.object(timeline,'render',return_value='x'*20000):
                with self.assertRaises(ValueError):timeline._with_paper_identities(args)
            for value in ({},dict(form,persona_sha256='0'*64)):
                relations.write_bytes(p.encode(value))
                with self.assertRaises(ValueError):timeline._with_paper_identities(args)
            args.paper_identities=root/'missing.json'
            with self.assertRaises(OSError):timeline._with_paper_identities(args)
    def test_shared_mapping_and_declared_scope(self):
        self.assertEqual(json.loads((ROOT/'examples/synthetic-paper-identity-ris-mapping.json').read_bytes()),self.mapping)
        self.assertEqual((ROOT/'examples/synthetic-paper-identity-export.ris').read_bytes(),RAW)
        self.assertEqual(set(self.record),p.TOP_KEYS)
        self.assertEqual(set(self.record['papers'][0]),p.ROW_KEYS)
        mapping=copy.deepcopy(self.mapping);mapping['papers'][0]['paper_id']='not-a-package-paper'
        with self.assertRaises(ValueError):p.from_ris(self.package,RAW,mapping,'synthetic','2026-11-15')
        mapping=copy.deepcopy(self.mapping);mapping['papers'][0]['census_id']='census-999999'
        with self.assertRaises(ValueError):p.from_ris(self.package,RAW,mapping,'synthetic','2026-11-15')
        altered=copy.deepcopy(self.record);altered['author_id']='another-author';altered.pop('payload_sha256');altered=p._seal(altered)
        with self.assertRaises(ValueError):p.check(altered,self.package)
    def test_cli_private_error_and_exclusive_output(self):
        with tempfile.TemporaryDirectory(prefix='RIS CLI space ') as temp:
            root=Path(temp);export=root/'source.ris';mapping=root/'map.json';record=root/'record.json'
            export.write_bytes(RAW);mapping.write_bytes(p.encode(self.mapping))
            args=['from-ris',ROOT/'examples/trajectory-conditions-package.json',export,mapping,'--operator-id','synthetic-ris-operator','--declared-at','2026-11-15','--output',record]
            run=self.cli('paper_identity.py',*args);self.assertEqual(run.returncode,0,run.stderr);self.assertEqual(json.loads(record.read_bytes()),self.record)
            self.assertNotEqual(self.cli('paper_identity.py',*args).returncode,0)
            for raw in (b'null',b'{"PRIVATE_UNKNOWN":"PRIVATE_VALUE"}'):
                record.write_bytes(raw);out=root/'never.txt';run=self.cli('publication_timeline.py',ROOT/'examples/trajectory-conditions-package.json','--topic',self.topic,'--paper-identities',record,'--output',out)
                self.assertEqual(run.returncode,1);self.assertEqual(run.stdout,b'');self.assertFalse(out.exists());self.assertEqual(run.stderr,('Invalid detached bibliography timeline input.'+os.linesep).encode())
    def test_guide(self):
        guide=(ROOT/'docs/RIS_PAPER_IDENTITY.md').read_text(encoding='utf-8');blocks=re.findall(r'```sh\n(.*?)\n```',guide,re.S);self.assertEqual(len(blocks),1)
        with tempfile.TemporaryDirectory(prefix='RIS guide space ') as temp:
            paths={'OUTPUT/'+n:str(Path(temp)/n) for n in ('census.json','declaration.json','replay.json','timeline.json','timeline.txt')}
            for line in blocks[0].splitlines():
                args=shlex.split(line);self.assertEqual(args.pop(0),'python');args=[paths.get(t,t) for t in args]
                result=self.cli(args[0],*args[1:]);self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads((Path(temp)/'timeline.json').read_bytes())['paper_identity_review']['export_copy_replayed'],'NOT_PERFORMED')
