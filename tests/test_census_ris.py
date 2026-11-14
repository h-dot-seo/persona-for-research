"""Synthetic fixed-column RIS extension, without external bibliographic resolution."""
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import census_import as c
import ris_export_parser as parser
from persona import payload_sha256
from prepare_local_manifest import prepare
from corpus_files import load_sources

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT/'examples/synthetic-bibliography.ris'


class RisCensusTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.path=self.root/'input.ris'
        self.raw=FIXTURE.read_bytes();self.path.write_bytes(self.raw)

    def imported(self,raw):
        self.path.write_bytes(raw);return c.import_ris(self.path)

    def test_parser_copy_and_original_hashes(self):
        expected='53e16edc7fd8e2ec5fbdf30ac228bd18b4b01340c3294f66bb04246b0200e39c'
        self.assertEqual(hashlib.sha256((ROOT/'ris_export_parser.py').read_bytes()).hexdigest(),expected)
        result=c.import_ris(self.path)
        self.assertEqual(result['ris_parser_sha256'],expected)
        self.assertEqual(result['export_sha256'],hashlib.sha256(self.raw).hexdigest())
        c.verify_census(result)

    def test_occurrences_and_exact_duplicate_groups(self):
        result=c.import_ris(self.path);entries=result['entries']
        self.assertEqual(entries[0]['entry_sha256'],entries[2]['entry_sha256'])
        self.assertNotEqual(entries[0]['census_id'],entries[2]['census_id'])
        self.assertEqual(result['exact_doi_groups'][0]['census_ids'],['census-000001','census-000003'])
        self.assertEqual(entries[0]['other_identifiers'],{'SN':'synthetic-serial-label'})
        self.assertEqual(entries[0]['authors'],['Invented Scholar A'])
        self.assertEqual(entries[3]['flags'],['NO_YEAR','NO_DOI'])

    def test_bom_crlf_and_entry_hash_stability(self):
        expected=c.import_ris(self.path)
        for raw in (b'\xef\xbb\xbf'+self.raw,self.raw.replace(b'\n',b'\r\n'),self.raw.replace(b'\n',b'\r')):
            result=self.imported(raw)
            self.assertEqual(result['entries'],expected['entries'])
            self.assertNotEqual(result['export_sha256'],expected['export_sha256'])

    def test_parser_rejections_propagate_with_line_numbers(self):
        for raw in (b'TY  - JOUR\nTI  - unclosed\n',b'TY  - JOUR\nER  - value\n',
                    b'TI  - first\nER  -\n',b'TY  - JOUR\n bad continuation\nER  -\n',
                    b'TY  - JOUR\n\nER  -\n',b'TY  - JOUR\nTI  - \xff\nER  -\n',
                    b'\xff\xfeT\x00Y\x00',b'TY  - JOUR\nTI  - \x00\nER  -\n'):
            with self.subTest(raw=raw),self.assertRaisesRegex(ValueError,'line '):self.imported(raw)

    def test_alias_conflicts_and_equal_aliases(self):
        for fields in ('TI  - one\nT1  - two\n','DO  - a\nDO  - b\n','JO  - a\nJF  - b\n','SN  - a\nSN  - b\n'):
            with self.assertRaisesRegex(ValueError,'conflicting RIS'):self.imported(('TY  - JOUR\n'+fields+'ER  -\n').encode())
        result=self.imported(b'TY  - JOUR\nTI  - same\nT1  - same\nER  -\n')
        self.assertEqual(result['entries'][0]['title'],'same')

    def test_continuations_unknown_tags_and_literal_author(self):
        raw=b'TY  - GEN\nTI  - first\n      second\nAU  - literal name\n      more\nXX  - unknown\nER  -\n'
        first=self.imported(raw)['entries'][0]
        self.assertEqual(first['title'],'first\nsecond');self.assertEqual(first['authors'],['literal name\nmore'])
        second=self.imported(raw.replace(b'unknown',b'changed'))['entries'][0]
        self.assertNotEqual(first['entry_sha256'],second['entry_sha256'])
        self.assertEqual(first['item_type'],'GEN')

    def test_year_is_only_exact_ascii_or_slash_prefix(self):
        for value,want in [('2020',2020),('2020/03/20',2020),('2020/',2020),('2020-01',None),('２０２０',None),('about 2020',None)]:
            result=self.imported(('TY  - JOUR\nPY  - '+value+'\nER  -\n').encode())
            self.assertEqual(result['entries'][0]['year'],want)

    def test_format_specific_schema_and_rehashed_tampering(self):
        result=c.import_ris(self.path)
        variants=[]
        for key,value in [('ris_parser_sha256','bad'),('format','csl-json')]:
            changed=copy.deepcopy(result);changed[key]=value;variants.append(changed)
        for key,value in [('authors',[{'literal':'name'}]),('other_identifiers',{'PMID':'guessed'}),('year',True)]:
            changed=copy.deepcopy(result);changed['entries'][0][key]=value;variants.append(changed)
        changed=copy.deepcopy(result);del changed['ris_parser_sha256'];variants.append(changed)
        for changed in variants:
            changed['payload_sha256']=payload_sha256({k:v for k,v in changed.items() if k!='payload_sha256'})
            with self.assertRaises(ValueError):c.selection(changed,['census-000001'])

    def test_existing_csl_record_still_accepted_without_parser_hash(self):
        result=c.import_csl(ROOT/'examples/synthetic-bibliography.csl.json')
        self.assertNotIn('ris_parser_sha256',result)
        result['implementation_sha256']='a'*64
        result['payload_sha256']=payload_sha256({k:v for k,v in result.items() if k!='payload_sha256'})
        c.selection(result,['census-000001'])

    def test_bounds_and_unapproved_filled_roundtrip(self):
        with patch.object(c,'MAX_EXPORT_BYTES',len(self.raw)-1):
            with self.assertRaises(ValueError):c.import_ris(self.path)
        with patch.object(c,'MAX_RECORDS',3):
            with self.assertRaises(ValueError):c.import_ris(self.path)
        with patch.object(c,'MAX_OUTPUT_BYTES',10):
            with self.assertRaises(ValueError):c.import_ris(self.path)
        result=c.import_ris(self.path);s,_=c.selection(result,['census-000001','census-000002'])
        source=ROOT/'examples/synthetic-sources'
        with self.assertRaises(ValueError):prepare(s,source)
        s.update(author_id='synthetic-scholar',version='1',build_id='ris-test')
        for i,p in enumerate(s['papers']):p.update(author_id='synthetic-scholar',authorized=True,runtime_knowledge_eligible=True,split='training',kind='research',topic='synthetic topic',source_file='synthetic-%d.md'%i)
        self.assertEqual(len(load_sources(prepare(s,source),source)['papers']),2)

    def test_cli_saves_new_output_and_rejects_collision(self):
        output=self.root/'census.json'
        argv=[sys.executable,str(ROOT/'census_import.py'),'import',str(self.path),'--format','ris','--output',str(output)]
        first=subprocess.run(argv,capture_output=True,cwd=ROOT);self.assertEqual(first.returncode,0,first.stderr)
        before=output.read_bytes();c.verify_census(json.loads(before))
        second=subprocess.run(argv,capture_output=True,cwd=ROOT);self.assertNotEqual(second.returncode,0);self.assertEqual(second.stdout,b'');self.assertEqual(output.read_bytes(),before)


if __name__=='__main__':unittest.main()
