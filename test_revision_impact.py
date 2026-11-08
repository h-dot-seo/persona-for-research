import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from strict_json import load
from prepare_local_manifest import prepare
from curate_local import append_observation
from revise_local import revise
from corpus_files import load_sources
from research_workflow import build
from reasoning_links import template as link_template
from answer_draft import template as answer_template
from design_scenario import template as design_template
from revision_impact import inspect,render

ROOT=Path(__file__).resolve().parent

class RevisionImpactTests(unittest.TestCase):
    def setUp(self):
        self.root=ROOT/'examples/synthetic-sources';m=prepare(load(ROOT/'examples/local-selection.json'),self.root)
        for name in ('research','review'):m=append_observation(m,load(ROOT/f'examples/manual-{name}-card.json'),self.root)
        self.manifest=m;self.old=build(load_sources(m,self.root));revised,_=revise(m,load(ROOT/'examples/manual-revision-card.json'),self.root);self.new=build(load_sources(revised,self.root))
        self.ref=dict(paper_id='synthetic-0',observation_index=0,dimension='question_framing')
        self.reviewref=dict(paper_id='synthetic-1',observation_index=0,dimension=None)
        self.links=link_template(self.old,'synthetic-op');self.links['links']=[dict(link_id='counter',from_ref=self.reviewref,to_ref=self.ref,relation='challenges',rationale='Synthetic operator relation, not source meaning.',claim_type='operator_interpretation')]
        self.proposal=design_template(self.old,self.links,'Which synthetic explanation?','synthetic-op')
        self.proposal['steps']=[dict(step_id='compare',proposed_action='Compare synthetic explanations.',rationale='Operator reasoning.',link_uses=[dict(link_id='counter',role='counterargument',applicability_note='Needs semantic review.')],hypothesis=None,falsification_check=None,alternative_explanation=None,uncertainty=None)]
        self.draft=answer_template(self.old,self.proposal['question'],'synthetic-op')
        self.draft['claims']=[dict(claim_id='answer',text='An operator interpretation.',claim_type='operator_synthesis',citations=[dict(reference=self.ref,role='support'),dict(reference=self.reviewref,role='challenge')],uncertainty=None)]

    def inspect(self,new=None):return inspect(self.old,self.new if new is None else new,self.links,self.proposal,self.draft,2020)

    def test_manual_revision_traces_changed_attribution_to_claim_and_step(self):
        r=self.inspect();self.assertTrue(r['old_artifacts_stale_for_current_package'])
        self.assertEqual(r['changed_reference_count'],1);self.assertEqual(r['unchanged_reference_count'],1)
        self.assertEqual(r['affected_answer_claim_ids'],['answer']);self.assertEqual(r['affected_design_step_ids'],['compare'])
        row=next(x for x in r['references'] if x['status']=='CHANGED_AT_SAME_REFERENCE')
        self.assertIn('observation',row['changed_endpoint_fields']);self.assertEqual(row['previous_evidence']['observation']['claim_type'],'explicit_statement')
        self.assertEqual(row['current_evidence']['observation']['claim_type'],'operator_interpretation')
        self.assertEqual(row['answer_uses'][0]['role'],'support');self.assertEqual(row['design_uses'][0]['relation'],'challenges')
        self.assertIn('Previous evidence',render(r));self.assertFalse(r['automatic_rebinding'])

    def test_missing_component_and_paper_remain_visible(self):
        m=copy.deepcopy(self.manifest);m['papers'][0]['observations'][0]['reasoning']={}
        r=self.inspect(build(load_sources(m,self.root)));self.assertEqual(r['missing_reference_count'],1)
        self.assertEqual(next(x for x in r['references'] if x['current_evidence'] is None)['missing_reason'],'COMPONENT_NOT_PRESENT')
        m['papers']=m['papers'][:1];r=self.inspect(build(load_sources(m,self.root)))
        self.assertEqual(r['missing_reference_count'],2)

    def test_unchanged_endpoints_do_not_make_new_package_bindings_reusable(self):
        m=copy.deepcopy(self.manifest);m['version']='2';m['build_id']='synthetic-new-identity'
        r=self.inspect(build(load_sources(m,self.root)))
        self.assertEqual(r['changed_reference_count'],0);self.assertTrue(r['all_artifacts_require_binding_review'])
        self.assertEqual(r['affected_answer_claim_ids'],[])
        same=self.inspect(self.old);self.assertFalse(same['old_artifacts_stale_for_current_package'])

    def test_old_artifacts_must_validate_against_old_package(self):
        self.draft['knowledge_papers_sha256']='0'*64
        with self.assertRaises(ValueError):self.inspect()

    def test_unused_link_changes_are_reported_without_claiming_step_impact(self):
        self.proposal['steps']=[];self.draft['claims']=[]
        r=self.inspect();self.assertEqual(r['affected_answer_claim_ids'],[]);self.assertEqual(r['affected_design_step_ids'],[])
        self.assertEqual(r['changed_reference_count'],1);self.assertTrue(r['references'][0]['unreferenced_link_uses'])

    def test_current_holdout_and_other_author_rejected(self):
        bad=copy.deepcopy(self.new);bad['knowledge']['papers'][0]['split']='holdout'
        with self.assertRaises(ValueError):self.inspect(bad)
        m=copy.deepcopy(self.manifest);m['author_id']='other'
        for p in m['papers']:p['author_id']='other'
        with self.assertRaisesRegex(ValueError,'same scholarly'):self.inspect(build(load_sources(m,self.root)))

    def test_empty_artifacts_are_zero_scope_not_full_impact_clearance(self):
        self.links=link_template(self.old,'op');self.proposal=design_template(self.old,self.links,'q','op');self.draft=answer_template(self.old,'q','op')
        r=self.inspect();self.assertEqual(r['compared_reference_count'],0);self.assertTrue(r['old_artifacts_stale_for_current_package'])
        self.assertIn('not all changed evidence',r['boundary'])

    def test_actual_cli_and_no_input_changes(self):
        with tempfile.TemporaryDirectory() as d:
            paths=[]
            for name,value in [('old',self.old),('new',self.new),('links',self.links),('proposal',self.proposal),('draft',self.draft)]:
                p=Path(d)/(name+'.json');p.write_text(json.dumps(value));paths.append(p)
            before=[p.read_bytes() for p in paths]
            result=subprocess.run([sys.executable,str(ROOT/'revision_impact.py'),*map(str,paths),'--reference-year','2020','--format','text'],cwd=d,capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stderr);self.assertIn('CHANGED_AT_SAME_REFERENCE',result.stdout);self.assertIn('operator_interpretation',result.stdout)
            self.assertEqual(before,[p.read_bytes() for p in paths])

    def test_year_change_is_visible_and_missing_index_is_not_silently_ignored(self):
        m=copy.deepcopy(self.manifest);m['papers'][0]['year']=2022
        r=self.inspect(build(load_sources(m,self.root)));row=next(x for x in r['references'] if x['reference']==self.ref)
        self.assertEqual(row['previous_publication_scope'],'SAME_YEAR_ORDER_UNRESOLVED');self.assertEqual(row['current_publication_scope'],'AFTER_REFERENCE_YEAR')
        self.assertIn('publication_year',row['changed_endpoint_fields'])
        m['papers'][0]['observations']=[]
        r=self.inspect(build(load_sources(m,self.root)));row=next(x for x in r['references'] if x['reference']==self.ref)
        self.assertEqual(row['missing_reason'],'OBSERVATION_INDEX_NOT_PRESENT')

    def test_result_mutation_does_not_change_input_artifacts(self):
        before=copy.deepcopy((self.old,self.new,self.links,self.proposal,self.draft))
        r=self.inspect();r['references'][0]['previous_evidence']['observation']['method']='MUTATED'
        r['references'][0]['answer_uses'].append({'fake':'use'})
        self.assertEqual(before,(self.old,self.new,self.links,self.proposal,self.draft))

    def test_text_shows_enclosing_observation_changes_and_link_direction(self):
        m=copy.deepcopy(self.manifest)
        m['papers'][0]['observations'][0]['topic']='changed synthetic topic'
        m['papers'][0]['observations'][0]['evidence_quote']='Compare competing'
        r=self.inspect(build(load_sources(m,self.root)));text=render(r)
        self.assertIn('Observation topic: changed synthetic topic',text)
        self.assertIn('Observation stored quote: Compare competing models',text)
        self.assertIn('Observation stored quote: Compare competing\n',text)
        self.assertIn('Observation recorded check',text)
        self.assertIn('endpoint=from',text);self.assertIn('endpoint=to',text)
