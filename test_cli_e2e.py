import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class CliScenario(unittest.TestCase):
    def run_input(self,path):
        return subprocess.run([sys.executable,'observation_input.py',str(path),'--question','Which experiment?','--topic','model design'],capture_output=True,text=True,timeout=20)
    def test_observations_plan_and_source_failure(self):
        path=Path('examples/observed-corpus.json')
        first=self.run_input(path); second=self.run_input(path)
        self.assertEqual(first.returncode,0,first.stderr)
        self.assertEqual(first.stdout,second.stdout)
        result=json.loads(first.stdout)
        self.assertEqual(result['application']['steps'][0]['evidence_verification'],'EXACT_QUOTE_MATCH_ONLY')
        self.assertEqual(result['application']['semantic_validation'],'NOT_PERFORMED')
        with tempfile.TemporaryDirectory() as folder:
            bad=json.loads(path.read_text()); bad['papers'][0]['observations'][0]['locator']='missing'
            out=Path(folder)/'bad.json'; out.write_text(json.dumps(bad))
            failed=self.run_input(out); self.assertNotEqual(failed.returncode,0); self.assertEqual(failed.stdout,'')
            bad=json.loads(path.read_text()); bad['papers'][0]['author_id']='other'; bad['papers'][0]['segments']=None
            out.write_text(json.dumps(bad)); failed=self.run_input(out)
            self.assertIn('author-matched',failed.stderr)
