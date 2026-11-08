import hashlib
import json
import unittest
from pathlib import Path
from observation_input import verified_corpus
from research_workflow import build, apply


class ObservationTests(unittest.TestCase):
    def setUp(self):
        self.c=json.loads(Path('examples/research-corpus.json').read_text())
        for paper in self.c['papers']:
            segments={'synthetic section 1':'Compare competing models before designing an experiment.'}
            paper['segments']=segments
            paper['segments_sha256']=hashlib.sha256(json.dumps(segments,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
            paper['observations'][0].update(evidence_quote='Compare competing models',claim_type='explicit_statement')
    def test_observation_to_plan(self):
        c=verified_corpus(self.c)
        self.assertNotIn('segments',c['papers'][0])
        result=apply(build(c),'Which experiment?','model design')
        self.assertEqual(result['steps'][0]['evidence_verification'],'EXACT_QUOTE_MATCH_ONLY')
        self.assertEqual(result['steps'][0]['claim_type'],'explicit_statement')
        self.assertEqual(c,verified_corpus(self.c))
    def test_wrong_quote_hash_and_holdout(self):
        self.c['papers'][0]['observations'][0]['evidence_quote']='fabricated text'
        with self.assertRaises(ValueError): verified_corpus(self.c)
        self.setUp(); self.c['papers'][0]['segments_sha256']='wrong'
        with self.assertRaises(ValueError): verified_corpus(self.c)
        self.setUp(); self.c['papers'][0]['split']='holdout'
        with self.assertRaises(ValueError): verified_corpus(self.c)
