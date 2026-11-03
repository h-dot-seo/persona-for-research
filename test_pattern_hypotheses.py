import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from strict_json import load
from research_workflow import build
from corpus_files import load_sources
from pattern_hypotheses import template,inspect,render

ROOT=Path(__file__).resolve().parent

class PatternHypothesisTests(unittest.TestCase):
    def setUp(self):
        self.manifest=load(ROOT/'examples/file-corpus.json')
        obs=self.manifest['papers'][1]['observations'][0];obs.update(method='Contrast alternative explanations before deciding.',stance='challenge',claim_type='operator_interpretation')
        obs['reasoning']={'alternative_explanation':dict(text='Other explanations may yield similar comparisons.',locator=obs['locator'],evidence_quote=obs['evidence_quote'],claim_type='operator_interpretation')}
        self.package=build(load_sources(self.manifest,ROOT/'examples/synthetic-sources'))
        self.form=template(self.package,'synthetic-operator')
        self.a=dict(paper_id='synthetic-0',observation_index=0,dimension=None);self.b=dict(paper_id='synthetic-1',observation_index=0,dimension='alternative_explanation')
        self.h=dict(pattern_id='comparison',operator_hypothesis='A possible comparison-first pattern across differently worded records.',scope_note='Only these two synthetic records; no real author claim.',support_refs=[self.a,self.b],challenge_refs=[dict(self.b,dimension=None)],alternative_explanation='A generic discipline convention, not a distinctive researcher method.',falsification_check=None,uncertainty='Quotes alone do not establish the proposed pattern.')
        self.form['hypotheses']=[self.h]

    def test_manual_pattern_keeps_distinct_wording_claim_labels_and_counterevidence(self):
        r=inspect(self.package,self.form);h=r['hypotheses'][0]
        self.assertEqual(h['claim_type'],'operator_interpretation');self.assertEqual(h['distinct_support_paper_id_count'],2)
        self.assertEqual(h['publication_years'],[2020,2021]);self.assertEqual(len(h['evidence']),3)
        self.assertIn('FALSIFICATION_CHECK_NOT_SUPPLIED',h['review_prompts'])
        text=render(r);self.assertIn('Contrast alternative explanations',text);self.assertIn('explicit_statement',text);self.assertIn('Declared use: challenge',text)
        self.assertFalse(r['automatic_pattern_discovery'])

    def test_template_is_empty_and_one_paper_many_components_is_not_repetition(self):
        self.assertEqual(template(self.package,'op')['hypotheses'],[])
        self.h['support_refs']=[self.b,dict(self.b,dimension=None)];r=inspect(self.package,self.form)
        self.assertEqual(r['hypotheses'][0]['distinct_support_paper_id_count'],1)
        self.assertIn('SUPPORT_FROM_FEWER_THAN_TWO_PAPER_IDS',r['hypotheses'][0]['review_prompts'])
        self.assertIn('SAME_REFERENCE_DECLARED_IN_BOTH_ROLES',r['hypotheses'][0]['review_prompts'])

    def test_shared_hash_not_independent_replication(self):
        m=copy.deepcopy(self.manifest);m['papers'][1]['source_file']=m['papers'][0]['source_file'];m['papers'][1]['source_sha256']=m['papers'][0]['source_sha256']
        p=build(load_sources(m,ROOT/'examples/synthetic-sources'));f=template(p,'op');f['hypotheses']=[self.h]
        h=inspect(p,f)['hypotheses'][0];self.assertEqual(h['distinct_source_hash_count'],1)
        self.assertIn('MULTIPLE_PAPER_IDS_SHARE_SOURCE_HASH',h['review_prompts'])

    def test_no_challenge_or_alternatives_remains_visible_not_approved(self):
        self.h.update(challenge_refs=[],alternative_explanation=None,uncertainty=None)
        h=inspect(self.package,self.form)['hypotheses'][0]
        self.assertIn('NO_CHALLENGE_REFERENCES_SUPPLIED',h['review_prompts']);self.assertIn('ALTERNATIVE_EXPLANATION_NOT_SUPPLIED',h['review_prompts'])
        self.assertEqual(h['status'],'OPERATOR_PATTERN_HYPOTHESIS_REQUIRES_REVIEW')

    def test_duplicates_missing_support_invalid_ref_and_stale_reject(self):
        for mutate in (lambda h:h['support_refs'].append(h['support_refs'][0]),lambda h:h.update(support_refs=[]),lambda h:h['support_refs'][0].update(observation_index=True)):
            f=copy.deepcopy(self.form);mutate(f['hypotheses'][0])
            with self.assertRaises(ValueError):inspect(self.package,f)
        f=copy.deepcopy(self.form);f['hypotheses'].append(copy.deepcopy(self.h))
        with self.assertRaises(ValueError):inspect(self.package,f)
        f=copy.deepcopy(self.form);f['persona_sha256']='0'*64
        with self.assertRaises(ValueError):inspect(self.package,f)

    def test_unused_observations_and_holdout_boundary(self):
        self.h['support_refs']=[self.a];self.h['challenge_refs']=[]
        r=inspect(self.package,self.form);self.assertEqual(r['unreferenced_observations'],[dict(self.b,dimension=None)])
        p=copy.deepcopy(self.package);p['knowledge']['papers'][1]['split']='holdout'
        with self.assertRaises(ValueError):inspect(p,self.form)

    def test_output_mutation_does_not_change_inputs(self):
        before=copy.deepcopy((self.package,self.form));r=inspect(self.package,self.form)
        r['hypotheses'][0]['evidence'][0]['evidence']['observation']['method']='mutated'
        self.assertEqual(before,(self.package,self.form))

    def test_actual_cli_template_fill_and_text_review(self):
        with tempfile.TemporaryDirectory() as d:
            pp=Path(d)/'package.json';fp=Path(d)/'form.json';pp.write_text(json.dumps(self.package));base=[sys.executable,str(ROOT/'pattern_hypotheses.py'),str(pp)]
            r=subprocess.run(base+['--template','--operator-id','op'],cwd=d,capture_output=True,text=True,timeout=20);self.assertEqual(r.returncode,0,r.stderr)
            form=json.loads(r.stdout);form['hypotheses']=[self.h];fp.write_text(json.dumps(form));before=(pp.read_bytes(),fp.read_bytes())
            r=subprocess.run(base+[str(fp),'--format','text'],cwd=d,capture_output=True,text=True,timeout=20)
            self.assertEqual(r.returncode,0,r.stderr);self.assertIn('FALSIFICATION_CHECK_NOT_SUPPLIED',r.stdout);self.assertIn('generic discipline convention',r.stdout)
            self.assertEqual(before,(pp.read_bytes(),fp.read_bytes()))

    def test_author_claim_or_validation_fields_cannot_be_added(self):
        for key,value in [('claim_type','explicit_statement'),('validated',True),('author_trait','verified')]:
            f=copy.deepcopy(self.form);f['hypotheses'][0][key]=value
            with self.assertRaises(ValueError):inspect(self.package,f)
        empty=inspect(self.package,template(self.package,'op'))
        self.assertEqual(empty['status'],'NO_PATTERN_HYPOTHESES');self.assertEqual(len(empty['unreferenced_observations']),2)

    def test_unreferenced_bad_year_blocks_template_and_review(self):
        m=copy.deepcopy(self.manifest);m['papers'][1]['year']=0
        p=build(load_sources(m,ROOT/'examples/synthetic-sources'))
        with self.assertRaises(ValueError):template(p,'op')
