"""Synthetic declared application intent; never proof of actual method use."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import method_application as methods
import research_journey as journey
import source_recheck
import tests.test_research_journey as fixture
import tests.test_pattern_evidence_reasons as imported_fixture
from pattern_proposals import export_reviewed
from persona import payload_sha256
from applicability_review import template as context_template
from design_scenario import template as design_template

ROOT=Path(__file__).resolve().parents[1]


class MethodApplicationTests(unittest.TestCase):
    def setUp(self):
        self.case=fixture.ResearchJourneyTests();self.case.setUp();self.c=self.case.case
        self.form=methods.template(*self.args(),'synthetic-application-operator')

    def args(self):return [self.c.package,self.c.patterns,self.c.context,self.c.links,self.c.proposal,'comparison']
    def inspect(self):return methods.inspect(*self.args(),self.form)
    def resolve(self,decision='consider',ref=None):
        self.form['applications'][0].update(decision=decision,proposed_role='method',
            application_rationale='Apply the selected comparison hypothesis only as a proposed check for this step.',
            target_condition_comparison='This target has not shown distinct predicted outcomes.',
            required_checks=[],failure_condition=None,remaining_uncertainty='Evidence is synthetic and method applicability is untested.',
            evidence_refs=[copy.deepcopy(ref if ref is not None else self.c.a)])

    def test_template_defers_every_step_without_copying_design_or_pattern_fields(self):
        self.assertEqual(len(self.form['applications']),1);row=self.form['applications'][0]
        self.assertEqual(row['decision'],'defer');self.assertIsNone(row['proposed_role'])
        for key in methods.TEXT_FIELDS:self.assertIsNone(row[key])
        self.assertEqual(row['evidence_refs'],[]);self.assertEqual(row['required_checks'],[])
        result=self.inspect();self.assertEqual(result['decision_counts'],{'consider':0,'exclude':0,'defer':1})
        self.assertEqual(result['status'],'METHOD_APPLICATION_REQUIRES_HUMAN_REVIEW')

    def test_consider_keeps_excluded_context_and_missing_checks_failure_visible(self):
        self.resolve();result=self.inspect();row=result['applications'][0];basis=row['evidence'][0]
        self.assertIn('REQUIRED_CHECKS_NOT_SUPPLIED',row['review_prompts'])
        self.assertIn('FAILURE_CONDITION_NOT_SUPPLIED',row['review_prompts'])
        self.assertIn('CONSIDERED_APPLICATION_HAS_EXCLUDED_SOURCE_CONTEXT',basis['review_prompts'])
        self.assertEqual(basis['context_assessment']['decision'],'exclude')
        self.assertEqual(row['checks_completion'],'NOT_RECORDED_OR_EXECUTED')
        self.assertFalse(result['automatic_approval']);self.assertFalse(result['design_modified'])

    def test_exclude_applies_to_pattern_mapping_not_step_removal(self):
        self.resolve('exclude');result=self.inspect()
        self.assertEqual(len(result['design_review']['steps']),1);self.assertEqual(len(result['applications']),1)
        self.assertEqual(result['applications'][0]['target_step']['proposed_action'],self.c.proposal['steps'][0]['proposed_action'])
        self.assertEqual(result['decision_scope'],'SELECTED_PATTERN_TO_STEP_NOT_STEP_EXECUTION_OR_REMOVAL')

    def test_resolved_decisions_require_explicit_role_reason_comparison_uncertainty_and_refs(self):
        for decision in ('consider','exclude'):
            self.resolve(decision)
            for key in ('proposed_role','application_rationale','target_condition_comparison','remaining_uncertainty','evidence_refs'):
                form=copy.deepcopy(self.form);form['applications'][0][key]=[] if key=='evidence_refs' else None
                with self.assertRaises(ValueError):methods.inspect(*self.args(),form)

    def test_filled_defer_and_fully_filled_consider_are_never_approval(self):
        self.resolve();row=self.form['applications'][0]
        row.update(required_checks=['Compare synthetic predictions.'],failure_condition='No distinguishable predicted observation.')
        for decision in ('defer','consider'):
            row['decision']=decision;result=self.inspect()
            self.assertEqual(result['status'],'METHOD_APPLICATION_REQUIRES_HUMAN_REVIEW')
            self.assertEqual(result['semantic_validation'],'NOT_PERFORMED');self.assertFalse(result['scientific_execution'])
            self.assertEqual(result['applications'][0]['decision'],decision)
        self.assertIn('Required checks (not executed)',methods.render(*self.args(),self.form))

    def test_all_steps_exactly_once_including_unlinked_empty_and_reordered_forms(self):
        second=copy.deepcopy(self.c.proposal['steps'][0]);second.update(step_id='unlinked',link_uses=[])
        self.c.proposal['steps'].append(second);self.form=methods.template(*self.args(),'op')
        for rows in (self.form['applications'][:1],self.form['applications']*2,
                     [dict(self.form['applications'][0],step_id='unknown'),self.form['applications'][1]]):
            form=copy.deepcopy(self.form);form['applications']=rows
            with self.assertRaises(ValueError):methods.inspect(*self.args(),form)
        self.form['applications'].reverse();self.assertEqual([r['step_id'] for r in self.inspect()['applications']],['compare','unlinked'])
        self.c.proposal['steps']=[];self.form=methods.template(*self.args(),'op')
        self.assertEqual(self.inspect()['status'],'NO_DESIGN_STEPS_TO_REVIEW')

    def test_refs_must_be_exact_selected_pattern_members_not_parent_or_sibling_aliases(self):
        # A selected component does not authorize its enclosing observation implicitly.
        self.c.patterns['hypotheses'][0]['challenge_refs']=[]
        self.form=methods.template(*self.args(),'op');self.resolve(ref=self.c.b)
        self.assertEqual(self.inspect()['applications'][0]['evidence'][0]['context_match_basis'],'ENCLOSING_OBSERVATION_ONLY')
        for ref in (self.c.review,dict(self.c.b,dimension='uncertainty'),dict(self.c.b,observation_index=True),
                    dict(self.c.b,extra='unsupported'),dict(self.c.b,observation_index=0.0)):
            form=copy.deepcopy(self.form);form['applications'][0]['evidence_refs']=[ref]
            with self.assertRaises(ValueError):methods.inspect(*self.args(),form)
        self.form['applications'][0]['evidence_refs']*=2
        with self.assertRaises(ValueError):self.inspect()

    def test_target_membership_is_specific_to_step_not_other_steps_or_unused_links(self):
        self.c.proposal['steps'].append(dict(self.c.proposal['steps'][0],step_id='other',link_uses=[]))
        self.form=methods.template(*self.args(),'op')
        self.resolve(ref=self.c.review);self.form['applications'][1]=dict(self.form['applications'][0],step_id='other')
        result=self.inspect();first,second=result['applications']
        self.assertTrue(first['evidence'][0]['target_step_link_uses'])
        self.assertEqual(second['evidence'][0]['target_step_link_uses'],[])
        self.assertIn('APPLICATION_REFERENCE_NOT_IN_TARGET_STEP_LINKS',second['evidence'][0]['review_prompts'])
        self.c.proposal['steps'][0]['link_uses']=[];self.form=methods.template(*self.args(),'op');self.resolve(ref=self.c.review)
        self.assertEqual(self.inspect()['applications'][0]['evidence'][0]['target_step_link_uses'],[])

    def test_source_pattern_design_application_roles_remain_distinct(self):
        self.resolve(ref=self.c.review);self.form['applications'][0]['proposed_role']='constraint'
        row=self.inspect()['applications'][0];basis=row['evidence'][0]
        self.assertEqual(row['proposed_role'],'constraint')
        self.assertEqual(basis['pattern_roles'],['challenge']);self.assertEqual(basis['evidence']['observation']['stance'],'challenge')
        self.assertEqual(basis['target_step_link_uses'][0]['role'],'motivation')
        self.assertEqual(basis['target_step_link_uses'][0]['relation'],'challenges')
        self.assertIn('AFTER_REFERENCE_YEAR',basis['review_prompts'])
        self.assertIn('APPLICATION_SOURCE_CONTEXT_DEFERRED',basis['review_prompts'])

    def test_no_enclosing_context_remains_missing_instead_of_inferred_applicability(self):
        self.c.context=context_template(self.c.package,self.c.context['question'],'Different synthetic target','absent',2020,'op')
        self.form=methods.template(*self.args(),'op');self.resolve()
        basis=self.inspect()['applications'][0]['evidence'][0]
        self.assertIsNone(basis['context_assessment']);self.assertEqual(basis['context_match_basis'],'NONE')
        self.assertIn('NO_ENCLOSING_OBSERVATION_CONTEXT_ASSESSMENT',basis['review_prompts'])

    def test_stale_pattern_context_links_and_design_each_invalidate_form(self):
        for index,mutate in [
            (1,lambda v:v['hypotheses'][0].update(operator_hypothesis='Different synthetic pattern.')),
            (2,lambda v:v['assessments'][0].update(remaining_uncertainty='Changed uncertainty.')),
            (3,lambda v:v['links'][0].update(rationale='Changed synthetic link interpretation.')),
            (4,lambda v:v['steps'][0].update(proposed_action='A changed synthetic action.'))]:
            args=copy.deepcopy(self.args());mutate(args[index])
            with self.assertRaises(ValueError):methods.inspect(*args,self.form)
        args=self.args();args[-1]='missing'
        with self.assertRaises(ValueError):methods.inspect(*args,self.form)
        self.c.context=context_template(self.c.package,'Different question','Target','model design',2020,'op')
        with self.assertRaisesRegex(ValueError,'question'):methods.template(*self.args(),'op')

    def test_schema_types_limits_blank_text_and_unknown_claims_fail(self):
        self.resolve()
        for mutate in (lambda r:r.update(decision='approve'),lambda r:r.update(proposed_role='author_method'),
            lambda r:r.update(application_rationale=' '),lambda r:r.update(failure_condition=''),
            lambda r:r.update(remaining_uncertainty='x'*2001),lambda r:r.update(required_checks=['same','same']),
            lambda r:r.update(required_checks=['check']*17),lambda r:r.update(evidence_refs=[self.c.a]*33),
            lambda r:r.update(approved=True),lambda r:r.update(required_checks=[None])):
            form=copy.deepcopy(self.form);mutate(form['applications'][0])
            with self.assertRaises(ValueError):methods.inspect(*self.args(),form)
        with patch.object(methods,'MAX_INPUT_BYTES',10):
            with self.assertRaisesRegex(ValueError,'inputs exceed'):self.inspect()
        with patch.object(methods,'MAX_OUTPUT_BYTES',10):
            with self.assertRaisesRegex(ValueError,'report exceeds'):self.inspect()

    def test_imported_pattern_original_reviewed_reasons_and_rejection_survive(self):
        source=imported_fixture.PatternEvidenceReasonTests();source.setUp()
        extra=copy.deepcopy(source.proposal);extra['proposed_hypothesis']='Rejected synthetic application generalization.'
        source.response['candidates'].append(extra);source.reimport();source.accept()
        source.review['decisions'][1].update(decision='reject',review_note='Synthetic rejection remains visible.')
        self.c.patterns=export_reviewed(source.package,source.bundle,source.review)
        self.form=methods.template(*self.args(),'synthetic-application');self.resolve()
        result=self.inspect();history=result['pattern_review']['proposal_review']
        self.assertEqual([row['decision'] for row in history['candidates']],['accept','reject'])
        text=methods.render(*self.args(),self.form)
        for phrase in ('Rejected synthetic application generalization.','Model proposed','Reviewer supplied','not authenticated'):
            self.assertIn(phrase,text)
        original_form=copy.deepcopy(self.form)
        self.c.patterns['review']['decisions'][0]['review_note']='Changed synthetic reviewer note.'
        with self.assertRaises(ValueError):methods.inspect(*self.args(),original_form)

    def test_no_inherited_failure_condition_and_proposed_checks_never_run(self):
        self.c.patterns['hypotheses'][0]['falsification_check']='Source pattern falsifier, not an application criterion.'
        self.c.proposal['steps'][0]['falsification_check']='A different plan-level criterion.'
        self.form=methods.template(*self.args(),'op');self.resolve()
        row=self.inspect()['applications'][0]
        self.assertIsNone(row['failure_condition']);self.assertEqual(row['required_checks'],[])
        self.assertIn('FAILURE_CONDITION_NOT_SUPPLIED',row['review_prompts'])

    def test_full_package_preflight_and_no_provider_file_access_or_mutation(self):
        self.resolve();before=copy.deepcopy([self.args(),self.form])
        with patch('pathlib.Path.open',side_effect=AssertionError('no files')),patch('socket.socket',side_effect=AssertionError('no network')):
            result=self.inspect();text=methods.render(*self.args(),self.form)
        self.assertEqual(before,[self.args(),self.form]);self.assertIn('semantic support',text)
        result['applications'][0]['evidence'][0]['evidence']['observation']['method']='mutated'
        self.assertEqual(before,[self.args(),self.form])
        self.c.package['knowledge']['papers'][-1]['authorized']=False
        with self.assertRaises(ValueError):self.inspect()

    def test_journey_annotation_never_promotes_pattern_only_reference_to_active_use(self):
        self.resolve(ref=self.c.b)
        before=journey.inspect(*self.case.args())
        after=journey.inspect(*self.case.args(),method_applications=self.form)
        for key in ('active_publication_context','evidence_scope','pattern_transfer_review','argument_review','trajectory_review'):
            self.assertEqual(before[key],after[key])
        for old,new in zip(before['evidence_routes'],after['evidence_routes']):
            self.assertEqual(old,{key:value for key,value in new.items() if key!='method_application_uses'})
        row=next(row for row in after['evidence_routes'] if row['evidence']['reference']==self.c.b)
        self.assertTrue(row['method_application_uses']);self.assertFalse(row['actively_used_in_answer_or_design'])
        self.assertEqual(row['design_uses'],[]);self.assertEqual(row['answer_uses'],[])
        self.assertNotEqual(before['journey_input_sha256'],after['journey_input_sha256'])

    def test_all_decision_role_combinations_preserve_existing_journey_semantics(self):
        before=journey.inspect(*self.case.args())
        for decision in methods.DECISIONS:
            for role in methods.ROLES:
                self.resolve(decision,ref=self.c.b);self.form['applications'][0]['proposed_role']=role
                after=journey.inspect(*self.case.args(),method_applications=self.form)
                for key in ('active_publication_context','evidence_scope','pattern_transfer_review','argument_review','trajectory_review'):
                    self.assertEqual(after[key],before[key])
                for old,new in zip(before['evidence_routes'],after['evidence_routes']):
                    self.assertEqual(old,{k:v for k,v in new.items() if k!='method_application_uses'})
                self.assertEqual(after['method_application_review']['applications'][0]['decision'],decision)
                self.assertEqual(after['method_application_review']['applications'][0]['proposed_role'],role)

    def test_same_year_stays_unresolved_and_extra_binding_fields_reject(self):
        self.resolve();row=self.inspect()['applications'][0]['evidence'][0]
        self.assertEqual(row['publication_scope'],'SAME_YEAR_ORDER_UNRESOLVED')
        self.assertIn('SAME_YEAR_ORDER_UNRESOLVED',row['review_prompts'])
        self.form['bindings']['scientifically_approved']=True
        with self.assertRaisesRegex(ValueError,'stale'):self.inspect()

    def test_application_validation_precedes_live_source_reads_and_can_compose_with_recheck(self):
        self.resolve();selection=source_recheck.template(self.c.package,'synthetic-source')
        for row in selection['sources']:row['source_file']=row['paper_id']+'.md'
        with patch.object(source_recheck,'read_source_bytes',side_effect=AssertionError('must not read')):
            bad=copy.deepcopy(self.form);bad['bindings']['proposal_sha256']='0'*64
            with self.assertRaises(ValueError):journey.inspect(*self.case.args(),method_applications=bad,source_selection=selection,source_root=ROOT/'examples/synthetic-sources')
        result=journey.inspect(*self.case.args(),method_applications=self.form,source_selection=selection,source_root=ROOT/'examples/synthetic-sources')
        self.assertTrue(result['source_reread']);self.assertTrue(result['source_recheck']['all_stored_quotes_match'])
        self.assertEqual(result['method_application_review']['decision_counts']['consider'],1)
        self.assertEqual(result['status'],'HUMAN_REVIEW_REQUIRED_NOT_RESEARCH_APPROVAL')

    def test_no_application_retains_exact_legacy_payload_and_text(self):
        self.assertEqual(payload_sha256(journey.inspect(*self.case.args())),'a4405809c8fde162293d6e73dd2ca8083329570d44ac9e2428f0607fa7d23350')
        self.assertEqual(payload_sha256(journey.render(*self.case.args())),'b21be5e06cde18dfd52a0c6d065d6161b857ba6c42f8921594f03bcfe8605d95')

    def test_cli_form_supports_interspersed_options_across_supported_python_versions(self):
        self.resolve()
        with tempfile.TemporaryDirectory() as directory:
            paths=[]
            for index,value in enumerate([*self.args()[:5],self.form]):
                path=Path(directory)/(str(index)+'.json');path.write_text(json.dumps(value));paths.append(str(path))
            options=['--pattern-id','comparison','--format','json']
            for argv in ([*paths,*options],[*paths[:5],*options,paths[5]],
                         [*options,*paths],[paths[0],*options,*paths[1:]]):
                result=subprocess.run([sys.executable,str(ROOT/'method_application.py'),*argv],
                    cwd=directory,capture_output=True,timeout=20)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertEqual(json.loads(result.stdout)['decision_counts']['consider'],1)

    def test_cli_template_json_text_and_integrated_application(self):
        with tempfile.TemporaryDirectory() as directory:
            paths=[]
            for name,value in zip(('package','patterns','context','links','proposal'),self.args()[:5]):
                path=Path(directory)/(name+'.json');path.write_text(json.dumps(value));paths.append(path)
            base=[sys.executable,str(ROOT/'method_application.py'),*map(str,paths),'--pattern-id','comparison']
            run=subprocess.run(base+['--template','--operator-id','synthetic'],cwd=directory,capture_output=True,timeout=20)
            self.assertEqual(run.returncode,0,run.stderr);self.assertEqual(json.loads(run.stdout)['applications'][0]['decision'],'defer')
            self.resolve();form_path=Path(directory)/'applications.json';form_path.write_text(json.dumps(self.form))
            for suffix in ([],['--format','text']):
                run=subprocess.run([*base,str(form_path),*suffix],cwd=directory,capture_output=True,timeout=20)
                self.assertEqual(run.returncode,0,run.stderr)
                if suffix:self.assertIn(b'FAILURE_CONDITION_NOT_SUPPLIED',run.stdout)
                else:self.assertEqual(json.loads(run.stdout)['decision_counts']['consider'],1)
            extra=[]
            for name,value in [('draft',self.c.draft),('argument',self.case.argument),('relations',self.case.relations),('review',self.case.review)]:
                path=Path(directory)/(name+'.json');path.write_text(json.dumps(value));extra.append(path)
            command=[sys.executable,str(ROOT/'research_journey.py'),*map(str,paths),*map(str,extra[:3]),
                '--pattern-id','comparison','--review',str(extra[3]),'--method-applications',str(form_path),'--format','text']
            run=subprocess.run(command,cwd=directory,capture_output=True,timeout=30)
            self.assertEqual(run.returncode,0,run.stderr);self.assertIn(b'Declared method application:',run.stdout)
            form_path.write_text('{"schema":1,"schema":2}')
            run=subprocess.run([*base,str(form_path)],cwd=directory,capture_output=True,timeout=20)
            self.assertNotEqual(run.returncode,0);self.assertEqual(run.stdout,b'');self.assertNotIn(b'Traceback',run.stderr)


if __name__=='__main__':unittest.main()
