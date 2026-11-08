import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from corpus_files import load_sources, sections
from research_workflow import build, apply


class FileCorpusTests(unittest.TestCase):
    def fixture(self,root):
        corpus=json.loads(Path('examples/observed-corpus.json').read_text())
        raw=b'# Synthetic paper\n\n## synthetic section 1\nCompare competing models before designing an experiment.\n'
        (root/'paper.md').write_bytes(raw)
        for p in corpus['papers']:
            p.pop('segments'); p.pop('segments_sha256')
            p['source_file']='paper.md'; p['source_sha256']=hashlib.sha256(raw).hexdigest()
        return corpus

    def test_files_to_verified_plan_and_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); corpus=self.fixture(root)
            loaded=load_sources(corpus,root)
            self.assertEqual(loaded['papers'][0]['source_verification'],'LOCAL_BYTES_SHA256_MATCH')
            self.assertNotIn('segments',loaded['papers'][0])
            self.assertEqual(loaded,load_sources(corpus,root))
            self.assertEqual(apply(build(loaded),'Which experiment?','model design')['steps'][0]['evidence_verification'],'EXACT_QUOTE_MATCH_ONLY')
            path=root/'manifest.json'; path.write_text(json.dumps(corpus))
            result=subprocess.run([sys.executable,'corpus_files.py',str(path),'--source-root',str(root),'--question','Which experiment?','--topic','model design'],capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stderr)

    def test_hash_path_and_author_rejections(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); corpus=self.fixture(root)
            for name in ('../outside.md','/absolute.md','C:\\secret.md'):
                altered=copy.deepcopy(corpus); altered['papers'][0]['source_file']=name
                with self.assertRaises(ValueError): load_sources(altered,root)
            altered=copy.deepcopy(corpus); altered['papers'][0]['author_id']='another'
            altered['papers'][0]['source_file']='missing.md'
            with self.assertRaisesRegex(ValueError,'author-matched'): load_sources(altered,root)
            (root/'paper.md').write_text('changed source')
            with self.assertRaisesRegex(ValueError,'byte hash mismatch'): load_sources(corpus,root)

    def test_duplicate_and_missing_headings(self):
        with self.assertRaises(ValueError): sections('## A\none\n## A\ntwo')
        with self.assertRaises(ValueError): sections('No section structure')
