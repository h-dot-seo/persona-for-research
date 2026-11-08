"""Imported bridge declarations through synthetic research review consumers."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import argument_proposals as proposals
import argument_map
import answer_draft
import answer_proposals
import journey_compare
import journey_html
import journey_inputs
import research_journey
import source_recheck
import tests.test_research_journey as fixture
from tests.test_journey_html import Document
from persona import payload_sha256

ROOT=Path(__file__).resolve().parents[1]
FIELDS=('step_id','premise_claim_ids','conclusion_claim_id','bridge_rationale','assumptions','defeater')


class ArgumentProposalIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.case=fixture.ResearchJourneyTests();self.case.setUp();self.c=self.case.case
        self.c.draft['claims'].insert(1,dict(claim_id='middle',text='Synthetic intermediate claim.',claim_type='operator_synthesis',uncertainty=None,citations=[]))
        self.c.draft['claims'].append(dict(claim_id='unused',text='Synthetic unmapped answer claim.',claim_type='operator_synthesis',uncertainty=None,
            citations=[dict(reference=self.c.b,role='support')]))
        self.case.review=answer_draft.review_template(self.c.package,self.c.draft,'synthetic-answer-reviewer')
        self.setup_candidates()

    def setup_candidates(self):
        self.scope=proposals.template(self.c.package,self.c.draft,'synthetic-argument-operator',self.case.review)
        self.scope['selected_claim_ids']=['claim','middle','conclusion','unused']
        self.handoff=proposals.prepare_handoff(self.c.package,self.c.draft,self.scope,self.case.review)
        self.response=proposals.response_template(self.c.package,self.c.draft,self.scope,self.handoff,self.case.review)
        self.response['candidates']=[
            dict(premise_claim_ids=['middle'],conclusion_claim_id='conclusion',bridge_rationale='Original late synthetic bridge.',assumptions=[],defeater=None),
            dict(premise_claim_ids=['claim'],conclusion_claim_id='middle',bridge_rationale='Original early synthetic bridge.',assumptions=[],defeater=None),
            dict(premise_claim_ids=['unused'],conclusion_claim_id='conclusion',bridge_rationale='Rejected synthetic shortcut.',assumptions=[],defeater=None)]
        self.provenance=dict(provider_id='synthetic-no-provider',model_id='synthetic-no-model',run_id='synthetic-argument-run',operator_id='synthetic-importer',execution_location='unknown')
        self.reimport()

    def reimport(self):
        self.bundle=proposals.import_response(self.c.package,self.c.draft,self.scope,self.handoff,self.response,self.provenance,self.case.review)
        self.adoption=proposals.review_template(self.c.package,self.c.draft,self.bundle,'synthetic-argument-reviewer',self.case.review)
        for index,step_id in enumerate(('late','early')):
            step=dict(copy.deepcopy(self.response['candidates'][index]),step_id=step_id)
            step['bridge_rationale']='Explicit reviewed '+step_id+' synthetic bridge.'
            self.adoption['decisions'][index].update(decision='accept',review_note='Synthetic '+step_id+' adoption only.',reviewed_step=step)
        self.adoption['decisions'][2].update(decision='reject',review_note='Synthetic shortcut rejected, not argument evidence.')
        self.envelope=proposals.export_reviewed(self.c.package,self.c.draft,self.bundle,self.adoption,self.case.review)
        self.case.argument=self.envelope

    def report(self):return research_journey.inspect(*self.case.args())
    def inspected(self):return argument_map.inspect(self.c.package,self.c.draft,self.envelope,self.case.review)
    def card(self,root):
        selection=journey_inputs.template();selection['pattern_id']='comparison'
        for name,value in [*zip(journey_inputs.REQUIRED,self.case.args()[:8]),('declared_review',self.case.review)]:
            filename=name+'.json';selection['artifacts'][name]=filename;(root/filename).write_text(json.dumps(value,ensure_ascii=True)+'\n',encoding='utf-8')
        return journey_inputs.prepare(selection,root)
    def group(self,result,name):return next(row for row in result['declared_record_comparison'] if row['group']==name)

    def test_handoff_includes_bound_question_and_rejects_old_question_context(self):
        self.assertEqual(self.handoff['question'],self.c.draft['question'])
        changed=copy.deepcopy(self.c.draft);changed['question']='Different explicit synthetic research question.'
        review=answer_draft.review_template(self.c.package,changed,'synthetic-answer-reviewer')
        scope=proposals.template(self.c.package,changed,'synthetic-argument-operator',review)
        scope['selected_claim_ids']=self.scope['selected_claim_ids']
        with self.assertRaisesRegex(ValueError,'handoff'):
            proposals.response_template(self.c.package,changed,scope,self.handoff,review)

    def test_declared_order_topology_and_proposal_origin_are_distinct(self):
        result=self.inspected()
        self.assertEqual(result['declared_step_ids'],['late','early'])
        self.assertEqual([row['step_id'] for row in result['steps']],['early','late'])
        for row,index in zip(result['steps'],(1,0)):
            self.assertEqual(row['proposal_origin']['candidate_id'],self.bundle['candidates'][index]['candidate_id'])
            self.assertEqual(row['proposal_origin']['original_proposal'],self.response['candidates'][index])
            self.assertEqual(row['origin'],'OPERATOR_ADOPTED_IMPORTED_ARGUMENT')
        self.assertEqual(result['argument_map_sha256'],payload_sha256(self.envelope))
        self.assertNotEqual(result['argument_map_sha256'],result['argument_content_sha256'])
        self.assertEqual(result['logical_validation'],'NOT_PERFORMED')
        self.assertFalse(result['llm_used']);self.assertEqual(result['historical_model_use'],'DECLARED_NOT_AUTHENTICATED')
        self.assertTrue(all(row['decision']=='defer' for row in result['answer']['review']['decisions']))

    def test_full_histories_survive_journey_text_and_passive_html(self):
        result=self.report();text=research_journey.render(*self.case.args());html=journey_html.render(*self.case.args())
        self.assertEqual(json.loads(Document(html).saved['complete-json']),result)
        for output in (json.dumps(result),text,html):
            for marker in ('Original late synthetic bridge.','Explicit reviewed late synthetic bridge.','Rejected synthetic shortcut.',
                           'OPERATOR_ADOPTED_IMPORTED_ARGUMENT','synthetic-no-model'):
                self.assertIn(marker,output)
        self.assertEqual(result['answer_review_status'],'DECLARED_REVIEW_INCOMPLETE')
        self.assertFalse(result['automatic_approval']);self.assertFalse(result['scientific_execution'])
        self.assertIn('Declared step order',text)

    def test_rejected_endpoint_remains_answer_evidence_but_never_argument_use(self):
        result=self.report();row=next(row for row in result['evidence_routes'] if row['evidence']['reference']==self.c.b)
        self.assertTrue(row['actively_used_in_answer_or_design']);self.assertEqual(row['direct_argument_uses'],[])
        steps=result['argument_review']['steps']
        self.assertEqual(next(row for row in steps if row['step_id']=='late')['conclusion']['direct_citation_count'],0)
        self.assertEqual(next(row for row in steps if row['step_id']=='early')['conclusion']['direct_citation_count'],0)
        self.assertIn('unused',result['argument_review']['unmapped_claim_ids'])

    def test_reordered_review_decisions_do_not_change_declared_step_order(self):
        before=self.inspected();self.adoption['decisions'].reverse()
        envelope=proposals.export_reviewed(self.c.package,self.c.draft,self.bundle,self.adoption,self.case.review)
        after=argument_map.inspect(self.c.package,self.c.draft,envelope,self.case.review)
        self.assertEqual(before['declared_step_ids'],after['declared_step_ids'])
        self.assertEqual(before['argument_content_sha256'],after['argument_content_sha256'])
        self.assertNotEqual(before['argument_map_sha256'],after['argument_map_sha256'])

    def test_comparison_preserves_manual_declared_order_instead_of_topology(self):
        with tempfile.TemporaryDirectory() as directory:
            a=Path(directory)/'a';b=Path(directory)/'b';a.mkdir();b.mkdir()
            manual=argument_map.template(self.c.package,self.c.draft,'synthetic-manual',self.case.review)
            manual['steps']=[copy.deepcopy(row['reviewed_step']) for row in self.adoption['decisions'] if row['decision']=='accept']
            self.case.argument=manual;before=self.card(a);manual['steps'].reverse();after=self.card(b)
            comparison=journey_compare.compare(before,a,after,b);group=self.group(comparison,'argument_steps')
            self.assertEqual(group['previous_id_order'],['late','early']);self.assertEqual(group['current_id_order'],['early','late']);self.assertTrue(group['order_changed'])
            self.assertTrue(all(row['status']=='UNCHANGED_AT_DECLARED_ID' for row in group['records']))
            self.assertEqual([row['step_id'] for row in comparison['previous_report']['argument_review']['steps']],['early','late'])
            self.assertEqual([row['step_id'] for row in comparison['current_report']['argument_review']['steps']],['early','late'])

    def test_manual_imported_transition_keeps_equal_declarations_and_distinct_history(self):
        with tempfile.TemporaryDirectory() as directory:
            a=Path(directory)/'a';b=Path(directory)/'b';a.mkdir();b.mkdir();before=self.card(a)
            manual=argument_map.template(self.c.package,self.c.draft,'synthetic-manual',self.case.review)
            manual['steps']=[copy.deepcopy(row['reviewed_step']) for row in self.adoption['decisions'] if row['decision']=='accept']
            self.case.argument=manual;after=self.card(b)
            for old,oldroot,new,newroot,status in ((before,a,after,b,'ONLY_PREVIOUS_DECLARATION'),(after,b,before,a,'ONLY_CURRENT_DECLARATION')):
                comparison=journey_compare.compare(old,oldroot,new,newroot);group=self.group(comparison,'argument_steps')
                self.assertEqual(group['previous_id_order'],['late','early']);self.assertFalse(group['order_changed'])
                self.assertTrue(all(row['status']=='UNCHANGED_AT_DECLARED_ID' for row in group['records']))
                historical=self.group(comparison,'argument_proposal_candidates')
                self.assertTrue(all(row['status']==status for row in historical['records']))
                self.assertIn('NOT_OPERATOR_AUTHORSHIP',historical['scope'])

    def test_history_only_change_updates_comparison_and_invalidates_old_card(self):
        with tempfile.TemporaryDirectory() as directory:
            a=Path(directory)/'a';b=Path(directory)/'b';a.mkdir();b.mkdir();before=self.card(a);prior=self.inspected()
            self.response['candidates'][2]['bridge_rationale']='Changed rejected bridge history.';self.reimport();after=self.card(b)
            current=self.inspected();self.assertEqual(prior['argument_content_sha256'],current['argument_content_sha256'])
            self.assertNotEqual(prior['argument_map_sha256'],current['argument_map_sha256'])
            comparison=journey_compare.compare(before,a,after,b)
            self.assertTrue(all(row['status']=='UNCHANGED_AT_DECLARED_ID' for row in self.group(comparison,'argument_steps')['records']))
            self.assertTrue(any(row['status']=='CHANGED_AT_DECLARED_ID' for row in self.group(comparison,'argument_proposal_candidates')['records']))
            (a/'argument.json').write_text(json.dumps(self.envelope),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'bytes changed'):journey_inputs.inspect(before,a)

    def test_separate_answer_review_presence_and_content_are_bound(self):
        with self.assertRaises(ValueError):argument_map.inspect(self.c.package,self.c.draft,self.envelope)
        changed=copy.deepcopy(self.case.review);changed['decisions'][0]['note']='Changed review declaration.'
        with self.assertRaises(ValueError):argument_map.inspect(self.c.package,self.c.draft,self.envelope,changed)
        self.assertEqual(self.case.review['decisions'][0]['decision'],'defer')

    def test_invalid_imported_graph_rejects_before_current_source_reads(self):
        selection=source_recheck.template(self.c.package,'synthetic-source')
        for row in selection['sources']:row['source_file']=row['paper_id']+'.md'
        with patch.object(source_recheck,'audit',wraps=source_recheck.audit) as audit:
            report=research_journey.inspect(*self.case.args(),source_selection=selection,source_root=ROOT/'examples/synthetic-sources')
            self.assertEqual(audit.call_count,1);self.assertTrue(report['source_reread'])
        bad=copy.deepcopy(self.envelope);bad['review']['decisions'][2]['decision']='defer';self.case.argument=bad
        with patch.object(source_recheck,'audit',side_effect=AssertionError('no source audit before invalid graph rejection')):
            with self.assertRaises(ValueError):research_journey.inspect(*self.case.args(),source_selection=selection,source_root=ROOT/'examples/synthetic-sources')

    def test_imported_answer_and_argument_histories_compose_without_laundering(self):
        original=copy.deepcopy(self.c.draft)
        scope=answer_proposals.template(self.c.package,original['question'],self.c.context['topic'],2020,'synthetic-answer-importer')
        scope['evidence_refs']=[self.c.a,self.c.b]
        handoff=answer_proposals.prepare_handoff(self.c.package,scope);response=answer_proposals.response_template(self.c.package,scope,handoff)
        response['candidates']=[{key:value for key,value in claim.items() if key!='claim_id'} for claim in original['claims']]
        response['candidates'].append(dict(text='Rejected answer history separate from graph.',claim_type='operator_synthesis',uncertainty=None,citations=[]))
        bundle=answer_proposals.import_response(self.c.package,scope,handoff,response,self.provenance)
        adoption=answer_proposals.review_template(self.c.package,bundle,'synthetic-answer-adopter')
        for index,claim in enumerate(original['claims']):adoption['decisions'][index].update(decision='accept',review_note='Synthetic answer adoption.',reviewed_claim=claim)
        adoption['decisions'][-1].update(decision='reject',review_note='Synthetic answer rejection.')
        self.c.draft=answer_proposals.export_reviewed(self.c.package,bundle,adoption)
        self.case.review=answer_draft.review_template(self.c.package,self.c.draft,'synthetic-final-reviewer');self.setup_candidates()
        result=self.report();argument=result['argument_review']
        self.assertIn('proposal_review',argument);self.assertIn('proposal_review',argument['answer'])
        for marker in ('Rejected answer history separate from graph.','Rejected synthetic shortcut.'):
            self.assertIn(marker,research_journey.render(*self.case.args()))
        self.c.draft['review']['decisions'][-1]['review_note']='Changed rejected answer history only.'
        self.case.review=answer_draft.review_template(self.c.package,self.c.draft,'synthetic-final-reviewer')
        with self.assertRaises(ValueError):self.report()

    def test_untrusted_rejected_bridge_escapes_html_and_inputs_are_unchanged(self):
        attack='<script src="https://invalid.example/x">not executable</script>&\nSynthetic bridge.'
        self.response['candidates'][2]['bridge_rationale']=attack;self.reimport();before=copy.deepcopy(self.case.args())
        html=journey_html.render(*self.case.args());self.assertNotIn('<script src=',html)
        packet=json.loads(Document(html).saved['complete-json'])['argument_review']['proposal_review']
        self.assertEqual(packet['candidates'][2]['candidate']['proposed_step']['bridge_rationale'],attack)
        self.assertEqual(before,self.case.args())

    def test_real_card_cli_reopens_imported_argument_history_without_approval(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);card=self.card(root);(root/'card.json').write_text(json.dumps(card),encoding='utf-8')
            run=subprocess.run([sys.executable,str(ROOT/'journey_inputs.py'),'inspect',str(root/'card.json'),'--input-root',str(root)],
                cwd=directory,capture_output=True,timeout=60)
            self.assertEqual(run.returncode,0,run.stderr.decode('utf-8'));result=json.loads(run.stdout)
            self.assertEqual(result['argument_review']['declared_step_ids'],['late','early'])
            self.assertEqual(result['answer_review_status'],'DECLARED_REVIEW_INCOMPLETE');self.assertFalse(result['automatic_approval'])


if __name__=='__main__':unittest.main()
