import copy
import json
import unittest
from pathlib import Path
from research_workflow import build, apply

class ResearchTests(unittest.TestCase):
    def setUp(self):
        self.corpus=json.loads(Path('examples/research-corpus.json').read_text())
    def test_evidence_to_plan(self):
        p=build(self.corpus)
        r=apply(p,'Which experiment discriminates models?', 'model design')
        self.assertEqual(len(r['steps']),2)
        self.assertEqual(r['steps'][0]['paper_id'],'synthetic-0')
        self.assertEqual(r['semantic_validation'],'NOT_PERFORMED')
        self.assertEqual(apply(p,'Unknown question','unknown')['status'],'OUTSIDE_PERSONA_COVERAGE')
    def test_holdout_unauthorized_and_tamper(self):
        for field,value in [('split','holdout'),('authorized',False),('author_id','other')]:
            c=copy.deepcopy(self.corpus); c['papers'][0][field]=value
            with self.assertRaises(ValueError): build(c)
        p=build(self.corpus); p['persona']['rules'][0]['method']='changed'
        with self.assertRaises(ValueError): apply(p,'Question','model design')
