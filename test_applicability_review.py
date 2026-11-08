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
from applicability_review import template,inspect,render

ROOT=Path(__file__).resolve().parent

class ApplicabilityTests(unittest.TestCase):
    def setUp(self):
        self.manifest=load(ROOT/'examples/file-corpus.json');self.manifest['papers'][1]['observations'][0]['stance']='challenge'
        self.package=build(load_sources(self.manifest,ROOT/'examples/synthetic-sources'))
        self.form=template(self.package,'Which comparison for the new system?','Synthetic system has only shared predictions; measurement is unavailable.','model design',2020,'synthetic-operator')

    def test_default_defer_keeps_research_review_conditions_and_missing_context(self):
        r=inspect(self.package,self.form);self.assertEqual(r['decision_counts'],{'consider':0,'exclude':0,'defer':2})
        self.assertEqual([x['evidence']['source_kind'] for x in r['assessments']],['research','review'])
        self.assertEqual(r['assessments'][1]['publication_scope'],'AFTER_REFERENCE_YEAR')
        self.assertEqual(r['assessments'][0]['missing_fields'],['context_comparison','remaining_uncertainty'])
        self.assertIn('Condition:',render(r));self.assertIn('NOT_SUPPLIED',render(r));self.assertFalse(r['llm_used'])

    def test_explicit_consider_exclude_preserved_with_declared_counterevidence(self):
        a,b=self.form['assessments'];a.update(decision='consider',context_comparison='Comparison is a possible preliminary step, but the stated distinct-outcomes condition is not met.',remaining_uncertainty='No discriminating measurement supplied.',counterevidence_refs=[b['reference']])
        b.update(decision='exclude',context_comparison='Do not use the later review as evidence available at the earlier cutoff.',remaining_uncertainty='Year alone does not establish availability.')
        r=inspect(self.package,self.form);self.assertEqual(len(r['assessments']),2);self.assertEqual(r['decision_counts']['exclude'],1)
        counter=r['assessments'][0]['counterevidence'][0];self.assertEqual(counter['evidence']['observation']['stance'],'challenge');self.assertEqual(counter['role_origin'],'OPERATOR_SUPPLIED_NOT_SOURCE_STANCE')
        self.assertIn('Operator decision: exclude',render(r));self.assertIn('AFTER_REFERENCE_YEAR',render(r))

    def test_cannot_drop_duplicate_or_add_topic_rows(self):
        for mutate in (lambda f:f['assessments'].pop(),lambda f:f['assessments'].append(copy.deepcopy(f['assessments'][0])),lambda f:f['assessments'][0]['reference'].update(dimension='uncertainty')):
            f=copy.deepcopy(self.form);mutate(f)
            with self.assertRaises(ValueError):inspect(self.package,f)

    def test_consider_requires_comparison_uncertainty_and_supported_decision(self):
        for decision in ('consider','exclude','validated'):
            f=copy.deepcopy(self.form);f['assessments'][0]['decision']=decision
            with self.assertRaises(ValueError):inspect(self.package,f)
        f=copy.deepcopy(self.form);f['assessments'][0]['counterevidence_refs']=[f['assessments'][0]['reference']]
        with self.assertRaises(ValueError):inspect(self.package,f)

    def test_stale_holdout_and_invalid_year_reject(self):
        m=copy.deepcopy(self.manifest);m['version']='2';p=build(load_sources(m,ROOT/'examples/synthetic-sources'))
        with self.assertRaises(ValueError):inspect(p,self.form)
        bad=copy.deepcopy(self.package);bad['knowledge']['papers'][0]['split']='holdout'
        with self.assertRaises(ValueError):inspect(bad,self.form)
        with self.assertRaises(ValueError):template(self.package,'q','c','model design',True,'op')

    def test_topic_match_is_observation_level_and_empty_not_ready(self):
        m=copy.deepcopy(self.manifest);m['papers'][0]['topic']='other publication topic'
        p=build(load_sources(m,ROOT/'examples/synthetic-sources'));f=template(p,'q','context','MODEL DESIGN',2020,'op');self.assertEqual(len(f['assessments']),2)
        f=template(p,'q','context','missing topic',2020,'op');r=inspect(p,f)
        self.assertEqual(r['status'],'NO_TOPIC_MATCHED_OBSERVATIONS');self.assertEqual(r['omitted_other_topic_observation_count'],2)

    def test_form_and_package_unchanged_by_review(self):
        before=copy.deepcopy((self.package,self.form));r=inspect(self.package,self.form)
        r['assessments'][0]['evidence']['observation']['method']='MUTATED'
        self.assertEqual(before,(self.package,self.form))

    def test_actual_cli_template_fill_review_and_no_context_override(self):
        with tempfile.TemporaryDirectory() as d:
            pp=Path(d)/'package.json';pp.write_text(json.dumps(self.package));fp=Path(d)/'form.json'
            base=[sys.executable,str(ROOT/'applicability_review.py'),str(pp)]
            r=subprocess.run(base+['--template','--question','q','--target-context','Synthetic shared predictions','--topic','model design','--reference-year','2020','--operator-id','op'],cwd=d,capture_output=True,text=True,timeout=20)
            self.assertEqual(r.returncode,0,r.stderr);f=json.loads(r.stdout);f['assessments'][0].update(decision='exclude',context_comparison='Distinct outcomes condition not met.',remaining_uncertainty='Measurements not supplied.');fp.write_text(json.dumps(f));before=fp.read_bytes()
            r=subprocess.run(base+[str(fp),'--format','text'],cwd=d,capture_output=True,text=True,timeout=20)
            self.assertEqual(r.returncode,0,r.stderr);self.assertIn('Operator decision: exclude',r.stdout);self.assertIn('Operator decision: defer',r.stdout)
            r=subprocess.run(base+[str(fp),'--target-context','Changed'],cwd=d,capture_output=True,text=True,timeout=20)
            self.assertEqual(r.returncode,1);self.assertEqual(fp.read_bytes(),before)

    def test_reasoning_components_and_missing_dimensions_are_not_filled(self):
        m=copy.deepcopy(self.manifest);m['papers'][0]['observations'][0]['reasoning']={'question_framing':dict(text='Which model comparison?',locator='synthetic section 1',evidence_quote='Compare competing models',claim_type='operator_interpretation')}
        p=build(load_sources(m,ROOT/'examples/synthetic-sources'));f=template(p,'q','context','model design',2020,'op');r=inspect(p,f)
        row=r['assessments'][0];self.assertEqual(len(row['reasoning_component_records']),1)
        self.assertIn('falsification_check',row['missing_reasoning_dimensions']);self.assertNotIn('question_framing',row['missing_reasoning_dimensions'])
        self.assertIn('Which model comparison?',render(r));self.assertIn('operator_interpretation',render(r))

    def test_context_changes_require_fresh_form_not_silent_decision_reuse(self):
        for field,value in [('question','Different question'),('target_context','Different context'),('reference_year',2022),('operator_id','different-operator')]:
            form=copy.deepcopy(self.form);form[field]=value
            with self.assertRaisesRegex(ValueError,'stale'):inspect(self.package,form)

    def test_cross_topic_counterevidence_topic_remains_visible_in_text(self):
        m=copy.deepcopy(self.manifest);m['papers'][1]['observations'][0]['topic']='DIFFERENT_TOPIC_SENTINEL'
        p=build(load_sources(m,ROOT/'examples/synthetic-sources'));f=template(p,'q','context','model design',2020,'op')
        self.assertEqual(len(f['assessments']),1)
        f['assessments'][0]['counterevidence_refs']=[dict(paper_id='synthetic-1',observation_index=0,dimension=None)]
        result=inspect(p,f);self.assertEqual(result['omitted_other_topic_observation_count'],1)
        self.assertIn('Observation topic: DIFFERENT_TOPIC_SENTINEL',render(result))
