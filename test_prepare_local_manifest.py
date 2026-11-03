import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from prepare_local_manifest import prepare
from corpus_files import load_sources, read_source_bytes
from research_workflow import build,apply


class PrepareLocalManifestTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.raw=b'# Synthetic\r\n\r\n## Method\r\nCompare invented explanations.\r\n## Limits\r\nSYNTHETIC_BODY_NOT_COPIED\r\n'
        (self.root/'paper.md').write_bytes(self.raw)
        self.selection=dict(author_id='synthetic-scholar',version='1',build_id='synthetic-local-prepared',papers=[dict(
            paper_id='synthetic-local',author_id='synthetic-scholar',split='training',runtime_knowledge_eligible=True,
            authorized=True,locator='synthetic supplied local file',kind='research',year=2020,topic='model design',
            source_file='paper.md',observations=[])])

    def test_hash_and_section_inventory_no_body_or_inferred_observations(self):
        result=prepare(self.selection,self.root);paper=result['papers'][0]
        self.assertEqual(paper['source_sha256'],hashlib.sha256(self.raw).hexdigest())
        self.assertEqual(paper['observations'],[])
        inventory=paper['input_inventory'];self.assertEqual([s['locator'] for s in inventory['sections']],['Method','Limits'])
        self.assertEqual(inventory['sections'][0]['normalized_text_sha256'],hashlib.sha256(b'Compare invented explanations.').hexdigest())
        self.assertNotIn('SYNTHETIC_BODY_NOT_COPIED',json.dumps(result))
        self.assertFalse(inventory['llm_used']);self.assertNotIn('source_sha256',self.selection['papers'][0])
        self.assertEqual((self.root/'paper.md').read_bytes(),self.raw)

    def test_curated_observation_roundtrip_uses_existing_loader_and_drops_inventory(self):
        prepared=prepare(self.selection,self.root)
        prepared['papers'][0]['observations']=[dict(method='Compare invented explanations.',condition='Synthetic model comparison.',
            limitation='No empirical test.',locator='Method',topic='model design',evidence_quote='Compare invented explanations.',
            claim_type='explicit_statement')]
        package=build(load_sources(prepared,self.root))
        result=apply(package,'Which synthetic explanation?','model design')
        self.assertEqual(result['steps'][0]['evidence_verification'],'EXACT_QUOTE_MATCH_ONLY')
        self.assertNotIn('input_inventory',json.dumps(package))
        self.assertNotIn('SYNTHETIC_BODY_NOT_COPIED',json.dumps(package))

    def test_entire_holdout_unauthorized_or_crossauthor_selection_rejects_before_io(self):
        for field,value in [('split','holdout'),('authorized',False),('authorized',1),('runtime_knowledge_eligible',False),('author_id','other')]:
            selection=copy.deepcopy(self.selection);other=copy.deepcopy(selection['papers'][0]);other['paper_id']='synthetic-later'
            other[field]=value;other['source_file']='missing.md';selection['papers'].append(other)
            with patch.object(Path,'resolve',side_effect=AssertionError('filesystem resolved')),patch('prepare_local_manifest.read_source_bytes',side_effect=AssertionError('file opened')):
                with self.assertRaises(ValueError):prepare(selection,self.root)

    def test_all_path_metadata_errors_preflight_before_any_source_read(self):
        for name in ('../outside.md','/absolute.md','C:\\outside.md','bad.pdf'):
            selection=copy.deepcopy(self.selection);other=copy.deepcopy(selection['papers'][0]);other['paper_id']='synthetic-later';other['source_file']=name
            selection['papers'].append(other)
            if name=='bad.pdf':(self.root/name).write_bytes(b'synthetic')
            with patch('prepare_local_manifest.read_source_bytes',side_effect=AssertionError('source opened early')):
                with self.assertRaises((ValueError,OSError)):prepare(selection,self.root)

    def test_existing_hash_pins_bytes_and_curated_evidence_cannot_be_rebaselined(self):
        prepared=prepare(self.selection,self.root);self.assertEqual(prepared,prepare(prepared,self.root))
        (self.root/'paper.md').write_bytes(self.raw+b'changed')
        with self.assertRaisesRegex(ValueError,'byte hash'):prepare(prepared,self.root)
        self.selection['papers'][0]['observations']=[dict(claim_type='operator_interpretation')]
        with patch('prepare_local_manifest.read_source_bytes',side_effect=AssertionError('read before rejecting observations')):
            with self.assertRaisesRegex(ValueError,'empty observations'):prepare(self.selection,self.root)

    def test_duplicate_headings_invalid_utf8_and_unsupported_metadata_fail(self):
        for raw in (b'No sections',b'## Same\na\n## Same\nb',b'## Test\n\xff'):
            (self.root/'paper.md').write_bytes(raw)
            with self.assertRaises(ValueError):prepare(self.selection,self.root)
        for field,value in [('kind','invented'),('year',0),('source_sha256','bad'),('unknown','PRIVATE_SYNTHETIC_MARKER')]:
            selection=copy.deepcopy(self.selection);selection['papers'][0][field]=value
            with patch('prepare_local_manifest.read_source_bytes',side_effect=AssertionError('read before validation')):
                with self.assertRaises(ValueError):prepare(selection,self.root)

    def test_source_read_once_and_annotation_aliases_not_shared(self):
        original=read_source_bytes;calls=[]
        def read(path):calls.append(path);return original(path)
        with patch('prepare_local_manifest.read_source_bytes',read):result=prepare(self.selection,self.root)
        self.assertEqual(calls,[self.root/'paper.md'])
        result['papers'][0]['observations'].append('changed output')
        self.assertEqual(self.selection['papers'][0]['observations'],[])

    def test_symlink_escape_is_rejected_before_reading_bytes(self):
        with tempfile.TemporaryDirectory() as outside:
            other=Path(outside)/'outside.md';other.write_bytes(b'## Outside\nSynthetic only')
            link=self.root/'link.md'
            try:link.symlink_to(other)
            except OSError:self.skipTest('symlink creation unavailable')
            self.selection['papers'][0]['source_file']='link.md'
            with patch('prepare_local_manifest.read_source_bytes',side_effect=AssertionError('escape bytes opened')):
                with self.assertRaisesRegex(ValueError,'escapes'):prepare(self.selection,self.root)

    def test_replaced_symlink_after_preflight_rejected_before_byte_read(self):
        import corpus_files
        with tempfile.TemporaryDirectory() as outside:
            other=Path(outside)/'outside.md';other.write_bytes(b'## Outside\nSYNTHETIC_OUTSIDE')
            original_paths=corpus_files.source_paths
            def replaced(selection,root):
                paths=original_paths(selection,root)
                paths[0].unlink()
                try:paths[0].symlink_to(other)
                except OSError:self.skipTest('symlink creation unavailable')
                return paths
            with patch('prepare_local_manifest.source_paths',replaced),patch.object(corpus_files.os,'open',side_effect=AssertionError('outside descriptor opened')):
                with self.assertRaisesRegex(ValueError,'path changed'):prepare(self.selection,self.root)

    def test_descriptor_identity_mismatch_rejected_before_stream_read(self):
        import corpus_files
        actual=corpus_files.os.fstat
        def mismatched(fd):
            original=actual(fd)
            from types import SimpleNamespace
            return SimpleNamespace(st_mode=original.st_mode,st_dev=original.st_dev,st_ino=original.st_ino+1)
        with patch.object(corpus_files.os,'fstat',mismatched),patch.object(corpus_files.os,'fdopen',side_effect=AssertionError('stream read began')):
            with self.assertRaisesRegex(ValueError,'identity changed'):prepare(self.selection,self.root)

    def test_detected_change_during_read_is_rejected(self):
        import corpus_files
        actual=corpus_files.os.fstat;calls=[]
        def changed(fd):
            value=actual(fd);calls.append(fd)
            if len(calls)==1:return value
            from types import SimpleNamespace
            return SimpleNamespace(st_size=value.st_size+1,st_mtime_ns=value.st_mtime_ns,st_ctime_ns=value.st_ctime_ns)
        with patch.object(corpus_files.os,'fstat',changed):
            with self.assertRaisesRegex(ValueError,'changed while reading'):prepare(self.selection,self.root)

    def test_actual_cli_prepare_curate_and_build(self):
        selection=self.root/'selection.json';selection.write_text(json.dumps(self.selection),encoding='utf-8')
        command=[sys.executable,'prepare_local_manifest.py',str(selection),'--source-root',str(self.root)]
        result=subprocess.run(command,capture_output=True,check=True)
        prepared=json.loads(result.stdout)
        prepared['papers'][0]['observations']=[dict(method='Compare invented explanations.',condition='Synthetic.',limitation='Unverified semantics.',
            locator='Method',topic='model design',evidence_quote='Compare invented explanations.',claim_type='operator_interpretation')]
        saved=self.root/'prepared.json';saved.write_text(json.dumps(prepared),encoding='utf-8')
        output=subprocess.run([sys.executable,'corpus_files.py',str(saved),'--source-root',str(self.root),'--question','Which explanation?',
            '--topic','model design'],capture_output=True,check=True)
        package=json.loads(output.stdout)['package']
        self.assertEqual(package['knowledge']['papers'][0]['source_verification'],'LOCAL_BYTES_SHA256_MATCH')
        self.assertEqual(package['persona']['rules'][0]['claim_type'],'operator_interpretation')
        self.assertNotIn('input_inventory',json.dumps(package))


if __name__=='__main__':unittest.main()
