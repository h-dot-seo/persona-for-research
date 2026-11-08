"""Synthetic v3 contexts through existing reviews, without citation permission expansion."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import answer_draft as ad
import answer_proposals as ap
import argument_map as am
import argument_proposals as gp
import citation_reasoning
import journey_compare
import journey_html
import journey_inputs
import research_journey
import source_recheck
import tests.test_contextual_answer_proposals as fixture
import tests.test_journey_html as html_fixture
from persona import payload_sha256


class ContextualAnswerIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.c=fixture.ContextualAnswerTests();self.c.setUp();c=self.c;self.f=c.f
        self.before=self.f.report()
        c.response['candidates'].append(dict(text='Synthetic uncited conclusion.',claim_type='operator_synthesis',uncertainty=None,citations=[]))
        c.reimport();c.accept(0,'claim');c.accept(1,'conclusion');self.draft=c.envelope()
        self.f.case.draft=self.draft;self.f.review=ad.review_template(c.p,self.draft,'synthetic-final-reviewer')
        old=self.f.argument['steps'];self.f.argument=am.template(c.p,self.draft,'synthetic-map',self.f.review);self.f.argument['steps']=old

    def test_complete_context_is_separate_from_active_citations(self):
        report=self.f.report();answer=report['pattern_transfer_review']['answer_design_review']['answer']
        packet=answer['proposal_review'];self.assertEqual(packet['research_context_role'],'RECORDED_IMPORT_CONTEXT_NOT_AUTOMATIC_CURRENT_REVIEW_CONTEXT')
        self.assertEqual(packet['research_context_review'],self.c.handoff['reasoning_context'])
        self.assertEqual(report['recorded_answer_context_comparison']['status'],'SAME_RECORDED_ARTIFACTS')
        before={r['reference_sha256']:r['actively_used_in_answer_or_design'] for r in self.before['evidence_routes']}
        after={r['reference_sha256']:r['actively_used_in_answer_or_design'] for r in report['evidence_routes']}
        self.assertEqual(before,after)
        uses=[u for r in report['evidence_routes'] for u in r['answer_uses']]
        self.assertEqual(len(uses),1);self.assertEqual(uses[0]['claim_id'],'claim')
        self.assertEqual(report['argument_review']['steps'][0]['conclusion']['direct_citation_count'],0)
        self.assertFalse(report['automatic_approval']);self.assertEqual(report['answer_review_status'],'DECLARED_REVIEW_INCOMPLETE')

    def test_current_context_difference_is_disclosed_not_blocked_or_overwritten(self):
        original=self.c.raw['context']['assessments'][0]['remaining_uncertainty']
        self.f.case.context['assessments'][0]['remaining_uncertainty']='New current uncertainty, not a contradiction claim.'
        self.f.relations['relations'][0]['rationale']='Updated current relationship annotation.'
        report=self.f.report();difference=report['recorded_answer_context_comparison']
        self.assertEqual(difference['status'],'DIFFERENT_SUPPLIED_ARTIFACTS')
        self.assertEqual(difference['changed_fields'],['context','publication_relations'])
        self.assertFalse(difference['automatic_rebinding']);self.assertFalse(difference['model_use_verified'])
        old=report['pattern_transfer_review']['answer_design_review']['answer']['proposal_review']['research_context_review']['context_review']
        self.assertEqual(old['assessments'][0]['remaining_uncertainty'],original)
        self.assertEqual(report['pattern_transfer_review']['context_review']['assessments'][0]['remaining_uncertainty'],'New current uncertainty, not a contradiction claim.')
        self.assertTrue(any(p['code']=='DIFFERENT_SUPPLIED_CONTEXT_ARTIFACTS' for p in report['review_agenda']))
        text=research_journey.render(*self.f.args());self.assertIn('Different hashes do not establish conflicting judgments',text)
        self.assertIn(original,text);self.assertIn('New current uncertainty',text)

    def test_same_context_is_not_proof_of_model_use_or_approval(self):
        result=self.f.report()['recorded_answer_context_comparison']
        self.assertEqual(result['changed_fields'],[]);self.assertFalse(result['model_use_verified'])
        self.assertIn('Equal hashes do not prove model use',result['boundary'])
        self.assertTrue(result['both_contexts_preserved'])
        self.assertEqual(result['scope'],'LOGICAL_JSON_INPUTS_NOT_SOURCE_BYTES_OR_SEMANTIC_JUDGMENTS')

    def test_v3_answer_supports_existing_imported_argument_workflow(self):
        p=self.c.p;d=self.draft;review=self.f.review
        scope=gp.template(p,d,'synthetic-operator',review);scope['selected_claim_ids']=['claim','conclusion']
        handoff=gp.prepare_handoff(p,d,scope,review);response=gp.response_template(p,d,scope,handoff,review)
        response['candidates']=[dict(premise_claim_ids=['claim'],conclusion_claim_id='conclusion',bridge_rationale='Synthetic explicit bridge.',assumptions=[],defeater=None)]
        bundle=gp.import_response(p,d,scope,handoff,response,self.c.provenance,review);adoption=gp.review_template(p,d,bundle,'synthetic-reviewer',review)
        adoption['decisions'][0].update(decision='accept',review_note='Synthetic explicit adoption.',reviewed_step=dict(response['candidates'][0],step_id='bridge'))
        self.f.argument=gp.export_reviewed(p,d,bundle,adoption,review);report=self.f.report()
        self.assertEqual(report['argument_review']['steps'][0]['conclusion']['direct_citation_count'],0)
        self.assertEqual(report['argument_review']['steps'][0]['citation_transfer'],'NOT_PERFORMED')
        self.assertEqual(report['argument_review']['answer']['proposal_review']['schema'],'persona.answer-proposal-review.v3')

    def test_citation_audit_preserves_recorded_context_without_adding_uses(self):
        result=citation_reasoning.audit(self.c.p,self.draft,self.f.review)
        self.assertEqual(result['inventory']['citation_uses'],1);self.assertEqual(result['inventory']['uncited_claims'],1)
        self.assertEqual(result['proposal_history']['packet']['research_context_review'],self.c.handoff['reasoning_context'])
        self.assertIn('Recorded import context',citation_reasoning.render(result))
        self.assertEqual(result['bindings']['draft_sha256'],payload_sha256(self.draft))

    def test_passive_html_retains_full_context_and_comparison_with_escaping(self):
        self.f.case.context['assessments'][0]['remaining_uncertainty']='<script>current only</script>\u202e'
        text=journey_html.render(*self.f.args());doc=html_fixture.Document(text)
        self.assertEqual(json.loads(doc.saved['complete-json']),self.f.report())
        html_fixture.JourneyHtmlTests().assert_passive(doc)
        self.assertIn('Recorded answer-preparation context versus current review',text)
        self.assertIn('DIFFERENT_SUPPLIED_ARTIFACTS',text);self.assertIn('&lt;script&gt;',text);self.assertNotIn('<script>',text)
        self.assertNotIn('\u202e',text)

    def test_invalid_embedded_context_fails_before_source_recheck(self):
        self.f.case.draft=copy.deepcopy(self.draft)
        self.f.case.draft['bundle']['scope']['research_context']['context']['assessments'][0]['decision']='approve'
        selection=source_recheck.template(self.c.p,'synthetic-source-reviewer')
        with patch.object(source_recheck,'audit',side_effect=AssertionError('premature source access')):
            with self.assertRaises(ValueError):research_journey.inspect(*self.f.args(),source_selection=selection,source_root='unused')

    def test_pinned_comparison_preserves_both_contexts_and_full_history(self):
        with tempfile.TemporaryDirectory() as temp:
            roots=[Path(temp)/'before',Path(temp)/'current'];cards=[]
            for index,root in enumerate(roots):
                root.mkdir();args=copy.deepcopy(self.f.args())
                if index:args[2]['assessments'][0]['remaining_uncertainty']='Current reevaluation annotation.'
                selection=journey_inputs.template();selection['pattern_id']=args[8]
                for name,value in zip(journey_inputs.REQUIRED,args[:8]):
                    selection['artifacts'][name]=name+'.json';(root/(name+'.json')).write_text(json.dumps(value),encoding='utf-8')
                selection['artifacts']['declared_review']='review.json';(root/'review.json').write_text(json.dumps(args[9]),encoding='utf-8')
                cards.append(journey_inputs.prepare(selection,root))
            report=journey_compare.compare(cards[0],roots[0],cards[1],roots[1])
            self.assertEqual(report['previous_report']['recorded_answer_context_comparison']['status'],'SAME_RECORDED_ARTIFACTS')
            self.assertEqual(report['current_report']['recorded_answer_context_comparison']['status'],'DIFFERENT_SUPPLIED_ARTIFACTS')
            history=next(g for g in report['declared_record_comparison'] if g['group']=='answer_proposal_import')
            self.assertTrue(all(r['status']=='UNCHANGED_AT_DECLARED_ID' for r in history['records']))
            prompts=[r for r in report['exact_prompt_comparison'] if r['prompt']['code']=='DIFFERENT_SUPPLIED_CONTEXT_ARTIFACTS']
            self.assertEqual(len(prompts),1);self.assertFalse(report['automatic_approval'])


if __name__=='__main__':unittest.main()
