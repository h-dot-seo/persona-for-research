"""Synthetic exact citation interpretations across review surfaces; no browser use."""
import copy
import json
import unittest
from unittest.mock import patch

import answer_draft as ad
import answer_proposals as ap
import argument_map as am
import evidence_scope
import journey_compare
import journey_html
import research_journey
import revision_impact
import source_recheck
import test_journey_compare as compare_fixture
import test_research_journey as journey_fixture
from test_citation_explanations import EXPLANATION
from test_journey_html import Document
import test_journey_html as html_fixture
from persona import payload_sha256


class CitationExplanationIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.fixture=journey_fixture.ResearchJourneyTests();self.fixture.setUp();self.c=self.fixture.case
        self.c.draft['claims'][0]['citations'][0]['explanation']=copy.deepcopy(EXPLANATION)
        self.rebind()

    def rebind(self,retain=False):
        old=self.fixture.argument['steps'];self.fixture.review=ad.review_template(self.c.package,self.c.draft,'synthetic-reviewer')
        if retain:
            for row in self.fixture.review['decisions']:row.update(decision='retain',note='Synthetic declaration, not validated.')
        self.fixture.argument=am.template(self.c.package,self.c.draft,'synthetic-map',self.fixture.review)
        self.fixture.argument['steps']=old

    def report(self):return self.fixture.report()

    def test_exact_use_propagates_without_changing_source_labels(self):
        result=self.report();ref=self.c.draft['claims'][0]['citations'][0]['reference']
        route=next(row for row in result['evidence_routes'] if row['evidence']['reference']==ref)
        self.assertEqual(route['answer_uses'][0]['explanation'],EXPLANATION)
        self.assertEqual(route['direct_argument_uses'][0]['explanation'],EXPLANATION)
        self.assertNotIn('explanation',route['evidence']);self.assertNotIn('explanation',route['evidence']['observation'])
        self.assertEqual(route['direct_argument_uses'][0]['argument_role'],'premise')
        self.assertEqual(result['argument_review']['steps'][0]['conclusion']['direct_citation_count'],0)
        self.assertEqual(result['evidence_scope']['answer_claims'][0]['citation_explanations'][0]['reference'],ref)
        self.assertEqual(result['evidence_scope']['answer_claims'][0]['citation_explanations'][0]['explanation'],EXPLANATION)
        self.assertEqual(result['scientific_validation'],'NOT_PERFORMED');self.assertFalse(result['automatic_approval'])

    def test_same_source_opposite_claim_roles_keep_separate_explanations(self):
        ref=copy.deepcopy(self.c.draft['claims'][0]['citations'][0]['reference'])
        self.c.draft['claims'][1]['citations']=[dict(reference=ref,role='challenge',explanation=dict(EXPLANATION,rationale='Different claim, opposite role.')),
            dict(reference=ref,role='context',explanation=None)]
        self.rebind();result=self.report();route=next(row for row in result['evidence_routes'] if row['evidence']['reference']==ref)
        uses={(r['claim_id'],r['role']):r for r in route['answer_uses']}
        self.assertEqual(len(uses),3)
        self.assertEqual(uses[('claim','support')]['explanation'],EXPLANATION)
        self.assertEqual(uses[('conclusion','challenge')]['explanation']['rationale'],'Different claim, opposite role.')
        self.assertIsNone(uses[('conclusion','context')]['explanation'])
        prompts=[r for r in result['review_agenda'] if r['code']=='CITATION_EXPLANATION_NOT_SUPPLIED']
        self.assertEqual(len(prompts),1);self.assertEqual(prompts[0]['target_id'],'conclusion')
        self.assertEqual(prompts[0]['reference'],ref);self.assertEqual(prompts[0]['role'],'context')

    def test_explicit_missing_prompt_survives_declared_retain(self):
        self.c.draft['claims'][0]['citations'][0]['explanation']=None;self.rebind(retain=True)
        result=self.report();prompts=[r for r in result['review_agenda'] if r['code']=='CITATION_EXPLANATION_NOT_SUPPLIED']
        self.assertEqual(len(prompts),1);self.assertEqual(prompts[0]['target_id'],'claim')
        self.assertEqual(result['answer_review_status'],'DECLARED_REVIEW_RECORDED_NOT_VALIDATED')
        self.assertTrue(result['evidence_scope']['review_prompts']);self.assertFalse(result['automatic_approval'])
        self.assertIn('EXPLICITLY_NOT_SUPPLIED',research_journey.render(*self.fixture.args()))

    def test_legacy_absence_does_not_get_new_prompts_or_default_fields(self):
        del self.c.draft['claims'][0]['citations'][0]['explanation'];self.rebind()
        result=self.report()
        self.assertNotIn('CITATION_EXPLANATION_NOT_SUPPLIED',[r['code'] for r in result['review_agenda']])
        self.assertNotIn('citation_explanations',result['evidence_scope']['answer_claims'][0])
        for route in result['evidence_routes']:
            for use in route['answer_uses']+route['direct_argument_uses']:self.assertNotIn('explanation',use)

    def test_html_and_text_escape_untrusted_explanation_complete_snapshot(self):
        danger='<script>alert("synthetic")</script>\n\\fake\u202e'
        explanation=dict(rationale=danger,context_boundary='<img src=x onerror=alert(1)>')
        self.c.draft['claims'][0]['citations'][0]['explanation']=explanation;self.rebind()
        before=copy.deepcopy(self.fixture.args());html=journey_html.render(*self.fixture.args());doc=Document(html)
        self.assertEqual(json.loads(doc.saved['complete-json']),self.report())
        html_fixture.JourneyHtmlTests().assert_passive(doc)
        self.assertNotIn('<script>',html);self.assertNotIn('<img',html);self.assertIn('&lt;script&gt;',html)
        text=research_journey.render(*self.fixture.args());self.assertNotIn('\u202e',text)
        self.assertEqual(self.fixture.args(),before)

    def test_invalid_explanation_fails_before_current_source_recheck(self):
        self.c.draft['claims'][0]['citations'][0]['explanation']={'rationale':'missing boundary'}
        selection=source_recheck.template(self.c.package,'synthetic-source-reviewer')
        with patch.object(source_recheck,'audit',side_effect=AssertionError('source read before validation')):
            with self.assertRaises(ValueError):research_journey.inspect(*self.fixture.args(),source_selection=selection,source_root='unused')

    def test_v2_adopted_history_visible_in_full_journey(self):
        c=self.c;ref=c.draft['claims'][0]['citations'][0]['reference']
        scope=ap.template(c.package,c.draft['question'],c.context['topic'],c.context['reference_year'],'synthetic-operator',include_citation_explanations=True)
        scope['evidence_refs']=[copy.deepcopy(ref)]
        h=ap.prepare_handoff(c.package,scope);response=ap.response_template(c.package,scope,h)
        response['candidates']=[{k:copy.deepcopy(v) for k,v in row.items() if k!='claim_id'} for row in c.draft['claims']]
        rejected=copy.deepcopy(response['candidates'][0]);rejected['citations'][0]['explanation']['rationale']='Rejected original interpretation.';response['candidates'].append(rejected)
        provenance=dict(provider_id='synthetic-no-provider',model_id='synthetic-no-model',run_id='synthetic-run',operator_id='synthetic-importer',execution_location='unknown')
        bundle=ap.import_response(c.package,scope,h,response,provenance);review=ap.review_template(c.package,bundle,'synthetic-reviewer')
        for index,row in enumerate(c.draft['claims']):
            review['decisions'][index].update(decision='accept',review_note='Synthetic explicit adoption only.',reviewed_claim=copy.deepcopy(row))
        review['decisions'][-1].update(decision='reject',review_note='Synthetic rejected alternative.')
        review['decisions'][0]['reviewed_claim']['citations'][0]['explanation']['rationale']='Edited interpretation for adopted claim.'
        c.draft=ap.export_reviewed(c.package,bundle,review);self.rebind();result=self.report()
        routes=[u for r in result['evidence_routes'] for u in r['answer_uses']]
        self.assertEqual(len(routes),1);self.assertEqual(routes[0]['explanation_origin'],'OPERATOR_ADOPTED_IMPORTED_INTERPRETATION')
        self.assertEqual(routes[0]['explanation']['rationale'],'Edited interpretation for adopted claim.')
        self.assertIn('Rejected original interpretation.',research_journey.render(*self.fixture.args()))
        snapshot=json.loads(Document(journey_html.render(*self.fixture.args())).saved['complete-json'])
        self.assertEqual(snapshot,result);self.assertFalse(result['provider_invoked'])
        self.assertEqual(result['evidence_scope']['answer_proposal_review']['schema'],'persona.answer-proposal-review.v2')

    def test_revision_disclosure_retains_exact_explanation_use(self):
        c=self.c
        result=revision_impact.inspect(c.package,c.package,c.links,c.proposal,c.draft,c.context['reference_year'])
        uses=[u for r in result['references'] for u in r['answer_uses']]
        self.assertEqual(uses[0]['explanation'],EXPLANATION)
        self.assertFalse(result['automatic_rebinding']);self.assertEqual(result['semantic_validation'],'NOT_PERFORMED')


class CitationExplanationComparisonTests(unittest.TestCase):
    def setUp(self):
        self.c=compare_fixture.JourneyComparisonTests();self.c.setUp();self.addCleanup(self.c.doCleanups)

    def test_reason_change_is_visible_and_does_not_change_stored_evidence(self):
        c=self.c;draft=c.read(1,'draft');draft['claims'][0]['citations'][0]['explanation']=copy.deepcopy(EXPLANATION)
        c.write(1,'draft',draft);c.rebind_answer(1);result=c.compare()
        group=c.group(result,'answer_claims')
        self.assertIn('explanation',json.dumps(group));self.assertIn('CHANGED',json.dumps(group))
        changed=[r for r in result['exact_reference_comparison'] if r['status']=='CHANGED_AT_EXACT_REFERENCE']
        self.assertTrue(changed);self.assertTrue(all(r['changed_evidence_fields']==[] for r in changed))
        self.assertTrue(any('answer_uses' in r['changed_route_fields'] for r in changed))
        self.assertFalse(result['automatic_approval'])

    def test_missing_explanation_prompt_comparison_is_not_resolution(self):
        c=self.c;draft=c.read(1,'draft');draft['claims'][0]['citations'][0]['explanation']=None
        c.write(1,'draft',draft);c.rebind_answer(1);result=c.compare()
        prompts=[r for r in result['exact_prompt_comparison'] if 'CITATION_EXPLANATION_NOT_SUPPLIED' in json.dumps(r)]
        self.assertEqual(len(prompts),1)
        self.assertIn('ONLY_CURRENT',json.dumps(prompts))
        self.assertEqual(result['current_report']['scientific_validation'],'NOT_PERFORMED')


if __name__=='__main__':unittest.main()
