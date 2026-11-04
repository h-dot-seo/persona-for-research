"""Synthetic integrated routes, not scientific correctness or scholar-fidelity tests."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import test_pattern_transfer_review as fixture
import test_pattern_evidence_reasons as imported_fixture
import test_observation_revision as observation_fixture
import research_journey as journey
from answer_draft import review_template, template as answer_template
from argument_map import template as argument_template
from publication_context import template as relation_template
from pattern_proposals import export_reviewed
from pattern_transfer_review import inspect as inspect_transfer, render as render_transfer
from pattern_hypotheses import template as pattern_template
from applicability_review import template as context_template
from persona import payload_sha256
from research_workflow import build
from reasoning_links import template as link_template
from design_scenario import template as design_template

ROOT = Path(__file__).resolve().parent


class ResearchJourneyTests(unittest.TestCase):
    def setUp(self):
        case=fixture.PatternTransferTests();case.setUp();self.case=case
        case.draft['claims'].append(dict(claim_id='conclusion',text='Tentative synthetic conclusion.',
            claim_type='operator_synthesis',uncertainty=None,citations=[]))
        self.review=review_template(case.package,case.draft,'synthetic-reviewer')
        self.argument=argument_template(case.package,case.draft,'synthetic-map',self.review)
        self.argument['steps']=[dict(step_id='combine',premise_claim_ids=['claim'],conclusion_claim_id='conclusion',
            bridge_rationale='Synthetic operator bridge.',assumptions=[],defeater=None)]
        self.relations=relation_template(case.package,'synthetic-relations')
        self.relations['relations']=[dict(relation_id='review-context',from_paper_id='synthetic-1',to_paper_id='synthetic-0',
            relation_type='review_summary_of',rationale='Unverified synthetic review comparison.',
            basis_refs=[case.review],uncertainty=None)]

    def args(self):
        c=self.case
        return [c.package,c.patterns,c.context,c.links,c.proposal,c.draft,self.argument,self.relations,'comparison',self.review]

    def report(self):return journey.inspect(*self.args())

    def test_one_packet_connects_full_reviews_without_changing_decisions(self):
        result=self.report()
        self.assertEqual(result['status'],'HUMAN_REVIEW_REQUIRED_NOT_RESEARCH_APPROVAL')
        self.assertEqual(result['answer_review_status'],'DECLARED_REVIEW_INCOMPLETE')
        for answer in (result['argument_review']['answer'],result['pattern_transfer_review']['answer_design_review']['answer']):
            self.assertEqual(answer['review'],self.review)
        self.assertEqual(result['trajectory_review']['topic'],self.case.context['topic'])
        self.assertEqual(result['pattern_transfer_review']['context_review']['decision_counts'],{'consider':0,'exclude':1,'defer':1})
        self.assertEqual(result['evidence_scope']['bindings']['review_sha256'],payload_sha256(self.review))
        for key in ('llm_used','provider_invoked','automatic_approval','scientific_execution','canonical_update_performed','human_review_authenticated'):
            self.assertFalse(result[key])

    def test_direct_argument_routes_never_inherit_premise_citations(self):
        result=self.report();rows=result['evidence_routes']
        uses=[use for row in rows for use in row['direct_argument_uses']]
        self.assertEqual(len(uses),1);self.assertEqual(uses[0]['argument_role'],'premise')
        self.assertEqual(uses[0]['declared_review_decision'],'defer')
        prompts=[row for row in result['review_agenda'] if row['domain']=='argument']
        self.assertTrue(any(row['code']=='NO_DIRECT_CITATIONS_CITATION_TRANSFER_NOT_PERFORMED' and row['claim_id']=='conclusion' for row in prompts))
        conclusion=result['argument_review']['steps'][0]['conclusion']
        self.assertEqual(conclusion['direct_citation_count'],0)

    def test_component_and_parent_reference_roles_are_not_merged(self):
        rows=self.report()['evidence_routes']
        component=next(row for row in rows if row['evidence']['reference']==self.case.b)
        observation=next(row for row in rows if row['evidence']['reference']==self.case.review)
        self.assertEqual(component['pattern_roles'],['support'])
        self.assertEqual(component['context_uses'],[])
        self.assertFalse(component['actively_used_in_answer_or_design'])
        self.assertEqual(observation['pattern_roles'],['challenge'])
        self.assertTrue(observation['context_uses']);self.assertTrue(observation['publication_relationship_basis_uses'])
        self.assertTrue(observation['actively_used_in_answer_or_design'])

    def test_context_only_relations_and_unused_links_do_not_become_active(self):
        self.case.proposal['steps']=[]
        result=self.report();row=next(r for r in result['evidence_routes'] if r['evidence']['reference']==self.case.review)
        self.assertFalse(row['actively_used_in_answer_or_design']);self.assertTrue(row['unused_link_uses'])
        self.assertTrue(row['publication_relationship_basis_uses'])
        self.assertEqual(result['active_publication_context']['selected_paper_ids'],['synthetic-0'])
        self.assertEqual(len(result['active_publication_context']['relations_to_other_supplied_papers']),1)

    def test_review_revision_rejection_is_preserved_in_every_domain(self):
        self.review['decisions'][0].update(decision='reject',note='Synthetic rejected premise.')
        self.review['decisions'][1].update(decision='revise',note='Synthetic unresolved conclusion.')
        self.argument['review_sha256']=payload_sha256(self.review)
        result=self.report()
        self.assertEqual(result['answer_review_status'],'DECLARED_REVIEW_RECORDED_NOT_VALIDATED')
        codes=[row['code'] for row in result['review_agenda']]
        self.assertIn('DECLARED_REJECT',codes);self.assertIn('DECLARED_REVISE',codes)
        self.assertEqual(result['argument_review']['steps'][0]['premises'][0]['declared_review_decision'],'reject')
        self.assertEqual(result['evidence_scope']['answer_claims'][0]['declared_review_decision'],'reject')
        self.assertTrue(any(row['actively_used_in_answer_or_design'] for row in result['evidence_routes']))
        text=journey.render(*self.args())
        self.assertIn('Declared decision: reject',text);self.assertIn('Synthetic rejected premise.',text)

    def test_no_review_requires_separately_bound_argument_and_stays_not_supplied(self):
        args=self.args();args[-1]=None
        with self.assertRaisesRegex(ValueError,'different draft or declared review'):journey.inspect(*args)
        self.argument['review_sha256']=None
        result=journey.inspect(*self.args()[:-1],None)
        self.assertEqual(result['answer_review_status'],'NOT_SUPPLIED')
        self.assertIn('NO_DECLARED_REVIEW',[row['code'] for row in result['review_agenda']])

    def test_retained_everywhere_still_requires_human_and_scientific_review(self):
        for row in self.review['decisions']:row.update(decision='retain',note='Synthetic recorded choice only.')
        self.argument['review_sha256']=payload_sha256(self.review)
        result=self.report()
        self.assertEqual(result['status'],'HUMAN_REVIEW_REQUIRED_NOT_RESEARCH_APPROVAL')
        self.assertFalse(result['automatic_approval']);self.assertEqual(result['scientific_validation'],'NOT_PERFORMED')

    def test_missing_relationships_and_missing_argument_remain_explicit(self):
        self.relations['relations']=[];self.argument['steps']=[]
        result=self.report();codes=[row['code'] for row in result['review_agenda']]
        self.assertIn('NO_DECLARED_RELATIONSHIPS_INDEPENDENCE_NOT_ESTABLISHED',codes)
        self.assertIn('NO_DECLARED_ARGUMENT_STEPS',codes);self.assertIn('UNMAPPED_CLAIM',codes)
        args=self.args();args[7]=None
        with self.assertRaisesRegex(ValueError,'explicit publication'):journey.inspect(*args)

    def test_context_topic_can_be_absent_without_silently_retargeting_pattern(self):
        c=self.case;c.context=context_template(c.package,c.context['question'],'Synthetic different target','absent',2020,'op')
        result=self.report();self.assertEqual(result['trajectory_review']['paper_count'],0)
        self.assertEqual(result['pattern_transfer_review']['context_review']['assessments'],[])
        self.assertTrue(result['evidence_routes']);self.assertTrue(all(not row['in_topic_timeline'] for row in result['evidence_routes']))
        self.assertIn('NO_TOPIC_MATCHING_RECORDS',[row['code'] for row in result['review_agenda']])

    def test_future_review_context_does_not_change_roles_or_date_the_assertion(self):
        result=self.report();codes=[row['code'] for row in result['review_agenda']]
        self.assertIn('RELATION_CONTEXT_INCLUDES_AFTER_REFERENCE_YEAR_PUBLICATION',codes)
        self.assertEqual(result['active_publication_context']['relationship_assertion_time'],'NOT_SUPPLIED')
        self.assertEqual(next(r for r in result['evidence_routes'] if r['evidence']['reference']==self.case.review)['pattern_roles'],['challenge'])

    def test_stale_review_relationship_argument_and_question_reject(self):
        for index,field in [(7,'persona_sha256'),(6,'review_sha256'),(9,'draft_sha256')]:
            args=copy.deepcopy(self.args());args[index][field]='0'*64
            with self.assertRaises(ValueError):journey.inspect(*args)
        c=self.case;c.context=context_template(c.package,'Different question','Context','model design',2020,'op')
        with self.assertRaisesRegex(ValueError,'question'):self.report()

    def test_full_package_auth_and_recorded_check_validation(self):
        for key,value in [('authorized',False),('split','holdout')]:
            args=copy.deepcopy(self.args());args[0]['knowledge']['papers'][1][key]=value
            with self.assertRaises(ValueError):journey.inspect(*args)
        args=copy.deepcopy(self.args());p=args[0];p['knowledge']['papers'][1]['source_verification']='SEMANTIC_PASS'
        p['persona']['knowledge_papers_sha256']=payload_sha256(p['knowledge']['papers'])
        p['knowledge']['persona_payload_sha256']=payload_sha256(p['persona'])
        with self.assertRaises(ValueError):journey.inspect(*args)

    def test_full_input_hash_changes_for_review_notes_relationships_and_argument(self):
        baseline=self.report()['journey_input_sha256']
        for index,mutate in [(7,lambda v:v['relations'][0].update(uncertainty='Unresolved synthetic linkage.')),
                             (6,lambda v:v['steps'][0].update(defeater='A synthetic alternative fits equally well.'))]:
            args=copy.deepcopy(self.args());mutate(args[index])
            self.assertNotEqual(journey.inspect(*args)['journey_input_sha256'],baseline)
        self.review['decisions'][0]['note']='A changed synthetic review note.'
        self.argument['review_sha256']=payload_sha256(self.review)
        self.assertNotEqual(self.report()['journey_input_sha256'],baseline)

    def test_imported_patterns_preserve_original_reviewed_and_rejected_history(self):
        c=imported_fixture.PatternEvidenceReasonTests();c.setUp()
        extra=copy.deepcopy(c.proposal);extra['proposed_hypothesis']='Rejected synthetic alternative.'
        c.response['candidates'].append(extra);c.reimport();c.accept()
        c.review['decisions'][1].update(decision='reject',review_note='Synthetic rejected interpretation.')
        self.case.patterns=export_reviewed(c.package,c.bundle,c.review)
        result=self.report();history=result['pattern_transfer_review']['pattern_proposal_review']
        self.assertEqual(sum(row['decision']=='reject' for row in history['candidates']),1)
        self.assertIn('Model proposed',json.dumps(history))
        self.assertIn('Reviewer supplied',json.dumps(result['evidence_routes']))
        text=journey.render(*self.args());self.assertIn('Rejected synthetic alternative.',text)
        self.assertIn('historical model use is declared, not authenticated',text)

    def test_imported_observation_history_visible_but_not_replayed(self):
        f=observation_fixture.ObservationRevisionTests();f.setUp();package=f.candidate()['package']
        links,proposal,draft=f.bindings(package);review=review_template(package,draft,'synthetic-reviewer')
        argument=argument_template(package,draft,'synthetic-map',review)
        patterns=pattern_template(package,'synthetic-pattern');a=dict(paper_id='synthetic-0',observation_index=0,dimension=None)
        b=dict(a,paper_id='synthetic-1');patterns['hypotheses']=[dict(pattern_id='comparison',operator_hypothesis='Synthetic comparison.',
            scope_note='Synthetic sources only.',support_refs=[a],challenge_refs=[b],alternative_explanation=None,falsification_check=None,uncertainty=None)]
        context=context_template(package,draft['question'],'Synthetic target','model design',2020,'synthetic-context')
        relations=relation_template(package,'synthetic-relations')
        result=journey.inspect(package,patterns,context,links,proposal,draft,argument,relations,'comparison',review)
        self.assertEqual(len(result['evidence_scope']['recorded_imported_observations']),2)
        self.assertTrue(all('observation_origin' in row['evidence']['observation'] for row in result['evidence_routes']))
        self.assertEqual(result['provenance_history_replay'],'NOT_PERFORMED')

    def test_no_input_mutation_provider_source_read_or_external_calls(self):
        before=copy.deepcopy(self.args())
        with patch('pathlib.Path.open',side_effect=AssertionError('no source read')),patch('socket.socket',side_effect=AssertionError('no network')):
            result=self.report();text=journey.render(*self.args())
        self.assertEqual(before,self.args());self.assertIn('human review',text)
        result['evidence_routes'][0]['evidence']['observation']['method']='changed'
        result['pattern_transfer_review']['context_review']['assessments'][0]['decision']='consider'
        self.assertEqual(before,self.args())

    def add_outside_paper(self):
        c=self.case
        corpus={key:c.package['persona'][key] for key in ('author_id','version','build_id')}
        corpus['papers']=copy.deepcopy(c.package['knowledge']['papers'])
        paper=copy.deepcopy(corpus['papers'][0]);paper['paper_id']='synthetic-outside'
        paper['observations'][0]['topic']='other synthetic topic';corpus['papers'].append(paper)
        c.package=build(corpus)
        patterns=pattern_template(c.package,'synthetic-pattern');patterns['hypotheses']=c.patterns['hypotheses'];c.patterns=patterns
        context=context_template(c.package,c.context['question'],c.context['target_context'],c.context['topic'],2020,'synthetic-context')
        context['assessments']=c.context['assessments'];c.context=context
        links=link_template(c.package,'synthetic-links');links['links']=c.links['links'];c.links=links
        proposal=design_template(c.package,c.links,c.context['question'],'synthetic-plan');proposal['steps']=c.proposal['steps'];c.proposal=proposal
        draft=answer_template(c.package,c.context['question'],'synthetic-answer');draft['claims']=c.draft['claims'];c.draft=draft
        self.review=review_template(c.package,c.draft,'synthetic-reviewer')
        argument=argument_template(c.package,c.draft,'synthetic-map',self.review);argument['steps']=self.argument['steps'];self.argument=argument
        relations=relation_template(c.package,'synthetic-relations');relations['relations']=self.relations['relations'];self.relations=relations
        return dict(paper_id='synthetic-outside',observation_index=0,dimension=None)

    def test_relationship_basis_only_outside_all_other_scopes_remains_context(self):
        ref=self.add_outside_paper()
        self.relations['relations'].append(dict(relation_id='outside-basis',from_paper_id='synthetic-outside',to_paper_id='synthetic-0',
            relation_type='challenges',rationale='Synthetic context-only relationship.',basis_refs=[ref],uncertainty=None))
        result=self.report();row=next(r for r in result['evidence_routes'] if r['evidence']['reference']==ref)
        self.assertEqual(len(row['publication_relationship_basis_uses']),1)
        for key in ('context_uses','pattern_roles','answer_uses','design_uses','unused_link_uses','direct_argument_uses'):
            self.assertEqual(row[key],[])
        self.assertFalse(row['in_topic_timeline']);self.assertFalse(row['actively_used_in_answer_or_design'])
        self.assertIn('synthetic-outside',result['evidence_scope']['unused_paper_ids'])
        self.assertIn('outside-basis',journey.render(*self.args()))

    def test_outside_context_counterevidence_only_is_not_an_assessment_or_active_use(self):
        ref=self.add_outside_paper();self.case.context['assessments'][0]['counterevidence_refs'].append(ref)
        result=self.report();row=next(r for r in result['evidence_routes'] if r['evidence']['reference']==ref)
        self.assertEqual([u['role'] for u in row['context_uses']],['counterevidence'])
        self.assertFalse(row['in_topic_timeline']);self.assertFalse(row['actively_used_in_answer_or_design'])
        self.assertEqual(row['publication_relationship_basis_uses'],[])
        self.assertEqual(result['evidence_scope']['coverage']['actively_referenced_paper_ids'],2)

    def test_shared_reference_keeps_dual_roles_and_multiple_claim_step_uses(self):
        c=self.case;c.patterns['hypotheses'][0]['challenge_refs'].append(copy.deepcopy(c.a))
        c.draft['claims'][1]['citations']=[dict(reference=c.a,role='support'),dict(reference=c.a,role='challenge')]
        second=copy.deepcopy(c.proposal['steps'][0]);second['step_id']='second-step';second['link_uses'][0]['role']='counterargument'
        c.proposal['steps'].append(second)
        self.review=review_template(c.package,c.draft,'synthetic-reviewer')
        self.argument.update(draft_sha256=payload_sha256(c.draft),review_sha256=payload_sha256(self.review))
        result=self.report();row=next(r for r in result['evidence_routes'] if r['evidence']['reference']==c.a)
        self.assertEqual(row['pattern_roles'],['support','challenge'])
        self.assertEqual(len(row['answer_uses']),3);self.assertEqual(len(row['design_uses']),2)
        self.assertEqual(len(row['direct_argument_uses']),3)
        self.assertEqual([u['argument_role'] for u in row['direct_argument_uses']],['premise','conclusion','conclusion'])
        self.assertEqual([u['citation_role'] for u in row['direct_argument_uses']],['support','support','challenge'])

    def test_resource_limits_fail_before_emitting_partial_report(self):
        with patch.object(journey,'MAX_INPUT_BYTES',10):
            with self.assertRaisesRegex(ValueError,'combined journey'):self.report()
        with patch.object(journey,'MAX_OUTPUT_BYTES',10):
            with self.assertRaisesRegex(ValueError,'report exceeds'):self.report()
        with self.assertRaisesRegex(ValueError,'finite JSON'):journey._inputs({'a':float('nan')})

    def test_transfer_accepts_review_without_changing_legacy_no_review_result(self):
        args=self.case.inputs()
        original=inspect_transfer(*args,self.relations)
        reviewed=inspect_transfer(*args,self.relations,self.review)
        self.assertNotEqual(original['report_input_sha256'],reviewed['report_input_sha256'])
        self.assertEqual(original['evidence_routes'],reviewed['evidence_routes'])
        self.assertEqual(reviewed['answer_design_review']['answer']['review'],self.review)
        self.assertEqual(reviewed['declared_answer_review_status'],'DECLARED_REVIEW_INCOMPLETE')
        self.assertNotIn('declared_answer_review_status',original)
        self.assertIn('Declared decision: defer',render_transfer(*args,self.relations,self.review))

    def test_actual_cli_json_text_strict_input_and_review_forwarding(self):
        with tempfile.TemporaryDirectory() as directory:
            paths=[]
            for name,value in zip(journey.INPUT_NAMES,self.args()[:8]):
                path=Path(directory)/(name+'.json');path.write_text(json.dumps(value));paths.append(path)
            review=Path(directory)/'review.json';review.write_text(json.dumps(self.review))
            before=[path.read_bytes() for path in [*paths,review]]
            base=[sys.executable,str(ROOT/'research_journey.py'),*map(str,paths),'--pattern-id','comparison','--review',str(review)]
            result=subprocess.run(base,cwd=directory,capture_output=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(json.loads(result.stdout)['journey_input_sha256'],self.report()['journey_input_sha256'])
            text=subprocess.run(base+['--format','text'],cwd=directory,capture_output=True,timeout=30)
            self.assertEqual(text.returncode,0,text.stderr);self.assertIn(b'HUMAN_REVIEW_REQUIRED',text.stdout)
            self.assertEqual(before,[path.read_bytes() for path in [*paths,review]])
            transfer=subprocess.run([sys.executable,str(ROOT/'pattern_transfer_review.py'),*map(str,paths[:6]),'--pattern-id','comparison','--review',str(review)],cwd=directory,capture_output=True,timeout=30)
            self.assertEqual(transfer.returncode,0,transfer.stderr);self.assertIn('review',json.loads(transfer.stdout)['answer_design_review']['answer'])
            paths[7].write_text('{"x":1,"x":2}')
            failed=subprocess.run(base,cwd=directory,capture_output=True,timeout=30)
            self.assertNotEqual(failed.returncode,0);self.assertEqual(failed.stdout,b'');self.assertNotIn(b'Traceback',failed.stderr)


if __name__=='__main__':unittest.main()
