import copy
import hashlib
import json
import re
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import census_import as ci
from corpus_files import load_sources
from persona import payload_sha256
from prepare_local_manifest import prepare, PAPER_SELECTION_FIELDS

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'examples/synthetic-bibliography.csl.json'


class CensusImportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.census = ci.import_csl(FIXTURE)

    def export(self, value, raw=None):
        path = self.root / 'input.json'
        path.write_bytes(raw if raw is not None else json.dumps(value).encode())
        return path

    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(ROOT / 'census_import.py'), *map(str, args)],
                              cwd=ROOT, capture_output=True)

    def rehash(self, value):
        value['payload_sha256'] = payload_sha256({k:v for k,v in value.items() if k != 'payload_sha256'})

    def test_occurrences_groups_hashes(self):
        entries = self.census['entries']
        self.assertEqual(entries[0]['entry_sha256'], entries[2]['entry_sha256'])
        self.assertNotEqual(entries[0]['census_id'], entries[2]['census_id'])
        self.assertEqual(self.census['exact_doi_groups'][0]['census_ids'], ['census-000001','census-000003'])
        self.assertEqual(self.census['export_sha256'], hashlib.sha256(FIXTURE.read_bytes()).hexdigest())
        self.assertEqual(self.census['implementation_sha256'], hashlib.sha256((ROOT/'census_import.py').read_bytes()).hexdigest())
        ci.verify_census(self.census)

    def test_year_rules(self):
        for value, expected in [(True,None),('２０２０',None),('2020',2020),('2020/',None),(2020,2020),(0,0),(20.0,None)]:
            self.assertEqual(ci.year({'issued':{'date-parts':[[value]]}}), expected)
        self.assertIsNone(ci.year({'issued':{'raw':'2020','literal':'2020'}}))

    def test_exact_strings_and_verbatim_names(self):
        records = [dict(title='EXAMPLE', DOI='X', author=[dict(given=' A ',family='B',literal=' C ')]),
                   dict(title='example', DOI='x'),dict(title='Correction of invented example')]
        result = ci.import_csl(self.export(records))
        self.assertEqual(result['exact_doi_groups'], [])
        self.assertEqual(len(result['casefold_title_groups']), 1)
        self.assertEqual(result['entries'][0]['authors'], records[0]['author'])
        self.assertEqual(result['entries'][2]['flags'], ['NO_YEAR','NO_DOI'])
        self.assertEqual(self.census['entries'][1]['item_type'], 'review')

    def test_utf8_bom_crlf_and_encoding_rejection(self):
        raw = FIXTURE.read_bytes()
        for other in [b'\xef\xbb\xbf'+raw, raw.replace(b'\n',b'\r\n')]:
            result = ci.import_csl(self.export(None, other))
            self.assertEqual(result['entries'], self.census['entries'])
            self.assertNotEqual(result['export_sha256'], self.census['export_sha256'])
        for bad in [raw.decode().encode('utf-16'), b'[\x00]', b'["\xff"]']:
            with self.assertRaises((ValueError,UnicodeError)):
                ci.import_csl(self.export(None,bad))

    def test_invalid_json_and_shapes(self):
        for raw in [b'[{"title":"A","title":"B"}]', b'[{"x":NaN}]']:
            with self.assertRaises(ValueError):ci.import_csl(self.export(None,raw))
        for value in [{},[],[False],[{'title':[]}],[{'author':['name']}],[{'author':[{'family':4}]}],[{'DOI':3}]]:
            with self.assertRaises(ValueError):ci.import_csl(self.export(value))

    def test_input_record_output_limits(self):
        size = len(FIXTURE.read_bytes())
        with patch.object(ci,'MAX_EXPORT_BYTES',size):ci.import_csl(FIXTURE)
        with patch.object(ci,'MAX_EXPORT_BYTES',size-1):
            with self.assertRaises(ValueError):ci.import_csl(FIXTURE)
        with patch.object(ci,'MAX_RECORDS',4):
            with self.assertRaises(ValueError):ci.import_csl(FIXTURE)
        with patch.object(ci,'MAX_OUTPUT_BYTES',10):
            with self.assertRaises(ValueError):ci.import_csl(FIXTURE)
            with self.assertRaises(ValueError):ci.save_selection(self.census,['census-000001'],self.root/'out')
        self.assertFalse((self.root/'out').exists())

    def test_exact_skeleton_and_missing_values(self):
        skeleton, mapping = ci.selection(self.census,['census-000003','census-000004','census-000005'])
        self.assertEqual(set(skeleton),{'author_id','version','build_id','papers'})
        self.assertIsNone(skeleton['author_id'])
        for paper in skeleton['papers']:
            self.assertEqual(set(paper),set(PAPER_SELECTION_FIELDS))
            self.assertFalse(paper['authorized']);self.assertFalse(paper['runtime_knowledge_eligible'])
            for key in ('author_id','kind','topic','split','source_file'):self.assertIsNone(paper[key])
        self.assertIsNone(skeleton['papers'][1]['year'])
        self.assertEqual(mapping['papers'][0]['paper_path'],'papers[0]')
        self.assertEqual(mapping['papers'][0]['census_id'],'census-000003')
        blank = ci.import_csl(self.export([{}]))
        self.assertIsNone(ci.selection(blank,['census-000001'])[0]['papers'][0]['locator'])

    def test_unknown_repeated_empty_selection(self):
        for ids in [[],['missing'],['census-000001']*2]:
            with self.assertRaises(ValueError):ci.selection(self.census,ids)

    def test_mutation_and_schema_metadata_rejected(self):
        for key, value in [('format','ris'),('schema','other'),('external_calls',False),('kind','research'),('utf8_bom',0)]:
            changed=copy.deepcopy(self.census);changed[key]=value;self.rehash(changed)
            with self.assertRaises(ValueError):ci.selection(changed,['census-000001'])
        changed=copy.deepcopy(self.census);changed['entries'][0]['title']='changed'
        with self.assertRaisesRegex(ValueError,'hash mismatch'):ci.selection(changed,['census-000001'])
        for key,value in [('census_id','renamed'),('year',True),('flags',[]),('authors',['name'])]:
            changed=copy.deepcopy(self.census);changed['entries'][3][key]=value;self.rehash(changed)
            with self.assertRaises(ValueError):ci.selection(changed,['census-000001'])
        changed=copy.deepcopy(self.census);changed['extra']=True
        with self.assertRaises(ValueError):ci.verify_census(changed)

    def test_untouched_rejected_filled_roundtrip(self):
        skeleton,_=ci.selection(self.census,['census-000001','census-000002'])
        source=ROOT/'examples/synthetic-sources'
        with self.assertRaises(ValueError):prepare(skeleton,source)
        skeleton.update(author_id='synthetic-scholar',version='1',build_id='synthetic-census-test')
        for i,paper in enumerate(skeleton['papers']):
            paper.update(author_id='synthetic-scholar',authorized=True,runtime_knowledge_eligible=True,
                         split='training',kind='research',topic='model design',source_file='synthetic-%d.md'%i)
        prepared=prepare(skeleton,source)
        loaded=load_sources(prepared,source)
        self.assertEqual(len(loaded['papers']),2)
        self.assertEqual(prepared['papers'][0]['source_sha256'],hashlib.sha256((source/'synthetic-0.md').read_bytes()).hexdigest())

    def test_directory_and_ready_hashes(self):
        destination=self.root/'selection'
        ci.save_selection(self.census,['census-000001'],destination)
        self.assertEqual({p.name for p in destination.iterdir()}, {'selection-skeleton.json','selection-census-map.json','READY.json'})
        ready=json.loads((destination/'READY.json').read_bytes())
        self.assertEqual(ready['selection_sha256'],payload_sha256(json.loads((destination/'selection-skeleton.json').read_bytes())))
        self.assertEqual(ready['map_sha256'],payload_sha256(json.loads((destination/'selection-census-map.json').read_bytes())))
        with self.assertRaises(ValueError):ci.save_selection(self.census,['census-000001'],destination)

    def test_path_rejection_and_empty_stdout(self):
        existing=self.root/'exists';existing.write_bytes(b'keep')
        for output in [existing,self.root/'missing'/'out', ROOT/'forbidden-census-output.json']:
            result=self.run_cli('import',FIXTURE,'--format','csl-json','--output',output)
            self.assertNotEqual(result.returncode,0);self.assertEqual(result.stdout,b'')
        self.assertEqual(existing.read_bytes(),b'keep')
        self.assertFalse((ROOT/'forbidden-census-output.json').exists())

    def test_symlink_paths(self):
        link=self.root/'link'
        try:link.symlink_to(self.root,target_is_directory=True)
        except OSError:self.skipTest('symlinks unavailable')
        with self.assertRaises(ValueError):ci.save_selection(self.census,['census-000001'],link/'out')

    def test_permission_failure_no_success(self):
        with patch('census_import.Path.mkdir',side_effect=PermissionError('synthetic denial')):
            with self.assertRaises(PermissionError):ci.save_selection(self.census,['census-000001'],self.root/'out')
        self.assertFalse((self.root/'out').exists())

    def test_preflight_precedes_read_and_failed_write_has_no_ready(self):
        existing=self.root/'exists';existing.write_bytes(b'keep')
        with patch.object(sys,'argv',['census_import.py','import','missing-export','--format','csl-json','--output',str(existing)]), patch.object(ci,'import_csl') as read:
            with self.assertRaises(SystemExit):ci.main()
            read.assert_not_called()
        destination=self.root/'partial'
        original=Path.open
        def fail_first(path,*args,**kwargs):
            if path.name == 'selection-skeleton.json':
                raise PermissionError('synthetic write denial')
            return original(path,*args,**kwargs)
        with patch.object(Path,'open',fail_first):
            with self.assertRaises(PermissionError):ci.save_selection(self.census,['census-000001'],destination)
        self.assertTrue(destination.is_dir())
        self.assertFalse((destination/'READY.json').exists())

    def test_documented_commands(self):
        text=(ROOT/'docs/CENSUS_IMPORT.md').read_text(encoding='utf-8')
        blocks=re.findall(r'```sh\n(.*?)```',text,re.S)
        self.assertEqual(len(blocks),1)
        for line in blocks[0].splitlines():
            if not line.strip():continue
            args=shlex.split(line);self.assertNotIn('>',args)
            args=[a.replace('OUTPUT',str(self.root)) for a in args];args[0]=sys.executable
            result=subprocess.run(args,cwd=ROOT,capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)
        self.assertTrue((self.root/'selection'/'READY.json').exists())

    def test_ris_rejected_and_help_no_input(self):
        result=self.run_cli('import',FIXTURE,'--format','ris','--output',self.root/'out')
        self.assertNotEqual(result.returncode,0);self.assertEqual(result.stdout,b'')
        self.assertFalse((self.root/'out').exists())
        self.assertEqual(self.run_cli('--help').returncode,0)


if __name__ == '__main__':
    unittest.main()
