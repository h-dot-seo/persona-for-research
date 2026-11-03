import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
import test_pattern_hypotheses as pattern_fixture
from applicability_review import template as context_template
from reasoning_links import template as link_template
from design_scenario import template as design_template
from answer_draft import template as answer_template
from pattern_transfer_review import inspect,render

ROOT=Path(__file__).resolve().parent

class PatternTransferTests(unittest.TestCase):
    def setUp(self):
        fixture=pattern_fixture.PatternHypothesisTests();fixture.setUp();self.package=fixture.package;self.patterns=fixture.form
        self.a=fixture.a;self.b=fixture.b;self.review=dict(self.b,dimension=None)
        self.context=context_template(self.package,'New synthetic question','Shared predictions, no discriminating observation.','model design',2020,'context-op')
        self.context['assessments'][0].update(decision='exclude',context_comparison='Source requires distinct outcomes, which target lacks.',remaining_uncertainty='No measurement available.',counterevidence_refs=[self.review])
        self.links=link_template(self.package,'link-op');self.links['links']=[dict(link_id='contrast',from_ref=self.review,to_ref=self.a,relation='challenges',rationale='Operator comparison only.',claim_type='operator_interpretation')]
        self.proposal=design_template(self.package,self.links,self.context['question'],'plan-op')
        self.proposal['steps']=[dict(step_id='compare',proposed_action='Compare models before measurement.',rationale='Proposed operator plan.',hypothesis=None,falsification_check=None,alternative_explanation=None,uncertainty=None,link_uses=[dict(link_id='contrast',role='motivation',applicability_note='Unresolved applicability.')])]
        self.draft=answer_template(self.package,self.context['question'],'answer-op');self.draft['claims']=[dict(claim_id='claim',text='Tentative operator answer.',claim_type='operator_synthesis',uncertainty=None,citations=[dict(reference=self.a,role='support')])]

    def inputs(self):return [self.package,self.patterns,self.context,self.links,self.proposal,self.draft,'comparison']

    def test_exclusion_unresolved_conditions_and_unused_pattern_counterrole_visible(self):
        r=inspect(*self.inputs());codes=[p['code'] for p in r['trace_review_prompts']]
        self.assertIn('EXCLUDED_OBSERVATION_HAS_SHARED_DESIGN_REFERENCE',codes)
        self.assertIn('NO_DECLARED_CHALLENGE_USE_FOR_PATTERN_CHALLENGE',codes)
        self.assertIn('CONTEXT_DECISION_DEFERRED',codes);self.assertIn('FALSIFICATION_CHECK_NOT_SUPPLIED',r['selected_pattern_review_prompts'])
        text=render(*self.inputs());self.assertIn('Source requires distinct outcomes',text);self.assertIn('Pattern falsification_check: NOT_SUPPLIED',text)
        self.assertIn('role=motivation relation=challenges',text);self.assertIn('Full supplied answer/design review',text)

    def test_same_parent_context_is_not_exact_component_application(self):
        r=inspect(*self.inputs());row=next(x for x in r['evidence_routes'] if x['evidence']['reference']==self.b)
        self.assertEqual(row['context_match_basis'],'ENCLOSING_OBSERVATION_ONLY')
        self.assertEqual(row['answer_uses'],[]);self.assertEqual(row['design_uses'],[])
        self.assertIn('PATTERN_REFERENCE_NOT_USED_IN_ANSWER_OR_DESIGN',row['review_prompts'])

    def test_explicit_challenge_use_preserves_source_and_operator_roles(self):
        self.draft['claims'][0]['citations'].append(dict(reference=self.review,role='challenge'))
        r=inspect(*self.inputs());row=next(x for x in r['evidence_routes'] if x['evidence']['reference']==self.review)
        self.assertNotIn('NO_DECLARED_CHALLENGE_USE_FOR_PATTERN_CHALLENGE',row['review_prompts'])
        self.assertEqual(row['pattern_roles'],['challenge']);self.assertEqual(row['publication_scope'],'AFTER_REFERENCE_YEAR')
        self.assertTrue(row['declared_context_counterevidence_for'])

    def test_question_mismatch_stale_form_or_missing_selection_reject(self):
        args=self.inputs();args[-1]='missing'
        with self.assertRaises(ValueError):inspect(*args)
        self.context=context_template(self.package,'Different question','Context','model design',2020,'op')
        with self.assertRaisesRegex(ValueError,'question'):inspect(*self.inputs())
        self.context['persona_sha256']='0'*64
        with self.assertRaises(ValueError):inspect(*self.inputs())

    def test_no_context_primary_match_is_not_filled_from_counterreference(self):
        self.context=context_template(self.package,'New synthetic question','Context','other topic',2020,'op')
        r=inspect(*self.inputs());self.assertTrue(all(row['context_assessment'] is None for row in r['evidence_routes']))
        self.assertTrue(all('NO_ENCLOSING_OBSERVATION_CONTEXT_ASSESSMENT' in row['review_prompts'] for row in r['evidence_routes']))

    def test_unused_links_not_reported_as_used_design(self):
        self.proposal['steps']=[];r=inspect(*self.inputs())
        row=next(x for x in r['evidence_routes'] if x['evidence']['reference']==self.review)
        self.assertEqual(row['design_uses'],[]);self.assertTrue(row['unused_link_uses'])
        self.assertIn('PATTERN_REFERENCE_NOT_USED_IN_ANSWER_OR_DESIGN',row['review_prompts'])

    def test_actual_cli_and_input_immutability(self):
        with tempfile.TemporaryDirectory() as d:
            paths=[]
            for name,value in zip(('package','patterns','context','links','proposal','draft'),self.inputs()[:-1]):
                p=Path(d)/(name+'.json');p.write_text(json.dumps(value));paths.append(p)
            before=[p.read_bytes() for p in paths]
            r=subprocess.run([sys.executable,str(ROOT/'pattern_transfer_review.py'),*map(str,paths),'--pattern-id','comparison','--format','text'],cwd=d,capture_output=True,text=True,timeout=20)
            self.assertEqual(r.returncode,0,r.stderr);self.assertIn('EXCLUDED_OBSERVATION_HAS_SHARED_DESIGN_REFERENCE',r.stdout)
            self.assertEqual(before,[p.read_bytes() for p in paths])

    def test_returned_reports_are_detached_from_all_input_artifacts(self):
        before=copy.deepcopy(self.inputs());r=inspect(*self.inputs())
        r['context_review']['assessments'][0]['evidence']['observation']['method']='mutated'
        r['selected_pattern']['evidence'][0]['declared_roles'].append('fake')
        r['answer_design_review']['answer']['claims'][0]['text']='mutated'
        self.assertEqual(before,self.inputs())

    def test_context_counterevidence_outside_selected_pattern_stays_in_text(self):
        self.patterns['hypotheses'][0]['support_refs']=[self.a]
        self.patterns['hypotheses'][0]['challenge_refs']=[]
        text=render(*self.inputs())
        self.assertIn('Full supplied context review',text)
        self.assertIn('Operator-selected counterevidence',text)
        self.assertIn('synthetic-1 / observation 0',text)
