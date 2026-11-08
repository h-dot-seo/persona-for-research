"""Synthetic v3 context exposure, not proof of model use or researcher reasoning."""
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import answer_draft as ad
import answer_proposals as ap
import argument_map as am
import argument_proposals as gp
import tests.test_research_journey as fixture
import tests.test_pattern_evidence_reasons as pattern_fixture
import pattern_proposals
from persona import payload_sha256

ROOT=Path(__file__).resolve().parents[1]


class FrozenReasonedReplayTests(unittest.TestCase):
    def test_captured_v2_answer_and_argument_artifacts_replay_exactly(self):
        frozen=json.loads((ROOT/'examples/legacy-reasoned-answer-v056.json').read_text(encoding='utf-8'))
        self.assertEqual(frozen['captured_from_commit'],'6b309ffa65d2957e6efdfa65448e27b39a20962e')
        p=frozen['package'];r=frozen['records'];d=r['draft'];review=r['answer_review']
        values=dict(answer_handoff=ap.prepare_handoff(p,r['answer_scope']),answer_bundle=ap.validate_bundle(p,r['answer_bundle']),
            answer_packet=ap.review_proposals(p,r['answer_bundle'],r['answer_adoption']),answer_inspection=ad.inspect(p,d),answer_reviewed=ad.review(p,d,review),
            argument_handoff=gp.prepare_handoff(p,d,r['argument_scope'],review),argument_bundle=gp.validate_bundle(p,d,r['argument_bundle'],review),
            argument_packet=gp.review_proposals(p,d,r['argument_bundle'],r['argument_adoption'],review),argument_inspection=am.inspect(p,d,r['argument_envelope'],review))
        self.assertEqual({k:payload_sha256(v) for k,v in values.items()},frozen['expected_sha256'])
        self.assertEqual(hashlib.sha256(ad.render(values['answer_inspection']).encode('utf-8')).hexdigest(),frozen['answer_text_sha256'])
        scope=r['answer_scope'];empty=ap.template(p,scope['question'],scope['topic'],scope['reference_year'],scope['operator_id'],include_citation_explanations=True,research_context=None)
        self.assertEqual(empty,dict(scope,evidence_refs=[]))
        self.assertEqual(ap.export_reviewed(p,r['answer_bundle'],r['answer_adoption']),d)
        self.assertEqual(gp.export_reviewed(p,d,r['argument_bundle'],r['argument_adoption'],review),r['argument_envelope'])


class ContextualAnswerTests(unittest.TestCase):
    def setUp(self):
        self.f=fixture.ResearchJourneyTests();self.f.setUp();self.c=self.f.case;self.p=self.c.package
        self.raw=dict(patterns=copy.deepcopy(self.c.patterns),context=copy.deepcopy(self.c.context),publication_relations=copy.deepcopy(self.f.relations),pattern_id='comparison')
        self.provenance=dict(provider_id='synthetic-no-provider',model_id='synthetic-no-model',run_id='synthetic-run',operator_id='synthetic-importer',execution_location='unknown')
        self.scope=self.scope_for(self.raw);self.scope['evidence_refs']=[copy.deepcopy(self.c.a)]
        self.reset()

    def scope_for(self,raw):
        return ap.template(self.p,self.c.context['question'],self.c.context['topic'],self.c.context['reference_year'],'synthetic-operator',include_citation_explanations=True,research_context=raw)

    def reset(self):
        self.handoff=ap.prepare_handoff(self.p,self.scope);self.response=ap.response_template(self.p,self.scope,self.handoff)
        claim={k:copy.deepcopy(v) for k,v in self.c.draft['claims'][0].items() if k!='claim_id'}
        for citation in claim['citations']:citation['explanation']=None
        self.response['candidates']=[claim];self.reimport()

    def reimport(self):
        self.bundle=ap.import_response(self.p,self.scope,self.handoff,self.response,self.provenance)
        self.review=ap.review_template(self.p,self.bundle,'synthetic-reviewer')

    def accept(self,index=0,claim_id='answer-claim'):
        self.review['decisions'][index].update(decision='accept',review_note='Synthetic explicit adoption only.',reviewed_claim=dict(copy.deepcopy(self.response['candidates'][index]),claim_id=claim_id))

    def envelope(self):return ap.export_reviewed(self.p,self.bundle,self.review)

    def test_explicit_context_mode_and_unchanged_v2_response_contract(self):
        self.assertEqual(self.scope['schema'],'persona.answer-proposal-scope.v3')
        self.assertEqual(self.handoff['schema'],'persona.answer-handoff.v3')
        self.assertEqual(self.scope_for(self.raw)['evidence_refs'],[])
        with self.assertRaisesRegex(ValueError,'explicit references'):ap.prepare_handoff(self.p,self.scope_for(self.raw))
        v2=ap.template(self.p,self.scope['question'],self.scope['topic'],self.scope['reference_year'],'synthetic-operator',include_citation_explanations=True)
        v2['evidence_refs']=copy.deepcopy(self.scope['evidence_refs'])
        self.assertEqual(self.handoff['response_contract'],ap.prepare_handoff(self.p,v2)['response_contract'])
        self.assertEqual(self.handoff['reasoning_context']['evidence_refs'],self.scope['evidence_refs'])
        self.assertEqual(self.review['decisions'][0]['decision'],'defer')
        self.assertFalse(self.handoff['processing']['provider_invoked'])
        self.assertIn('Context-only',self.handoff['boundary'])

    def test_context_requires_explanations_and_exact_raw_fields(self):
        with self.assertRaisesRegex(ValueError,'explanation mode'):
            ap.template(self.p,self.scope['question'],self.scope['topic'],2020,'op',research_context=self.raw)
        for raw in (None,[],False,{},dict(self.raw,extra='untrusted')):
            if raw is None:continue # Explicit None is deliberately the unchanged v2 path.
            with self.assertRaises(ValueError):self.scope_for(raw)
        for key in self.raw:
            raw=copy.deepcopy(self.raw);del raw[key]
            with self.assertRaises(ValueError):self.scope_for(raw)
        raw=copy.deepcopy(self.raw);raw['pattern_id']='missing-or-rejected'
        with self.assertRaises(ValueError):self.scope_for(raw)

    def test_exact_context_question_topic_and_year_alignment(self):
        for key,value in [('question',self.scope['question'].upper()),('topic',self.scope['topic'].upper()),('reference_year',2021),('reference_year',True),('reference_year',2020.0)]:
            raw=copy.deepcopy(self.raw);raw['context'][key]=value
            with self.assertRaises(ValueError):self.scope_for(raw)

    def test_stale_raw_context_and_relation_changes_reject_old_handoff(self):
        for mutate in (lambda raw:raw['context']['assessments'][0].update(remaining_uncertainty='Changed declared uncertainty.'),
                       lambda raw:raw['patterns']['hypotheses'][0].update(scope_note='Changed declared scope.'),
                       lambda raw:raw['publication_relations']['relations'][0].update(rationale='Changed relationship basis.')):
            scope=copy.deepcopy(self.scope);mutate(scope['research_context'])
            with self.assertRaisesRegex(ValueError,'handoff changed'):ap.response_template(self.p,scope,self.handoff)
        bundle=copy.deepcopy(self.bundle);bundle['scope']['research_context']['context']['target_context']='Changed target.'
        with self.assertRaises(ValueError):ap.validate_bundle(self.p,bundle)

    def test_context_quotes_and_synthesis_refs_remain_uncitable_without_explicit_selection(self):
        from reasoning_links import _sources,_endpoint
        _,papers=_sources(self.p);outside=copy.deepcopy(self.c.review);node=_endpoint(outside,papers)
        quote=node['observation']['evidence_quote']
        for claim_type,text in [('operator_synthesis','Synthetic unsupported context citation.'),('source_quote',quote)]:
            bad=dict(text=text,claim_type=claim_type,uncertainty=None,citations=[dict(reference=outside,role='context',explanation=None)])
            response=dict(self.response,candidates=[bad])
            with self.assertRaisesRegex(ValueError,'explicit scope reference'):ap.import_response(self.p,self.scope,self.handoff,response,self.provenance)
            self.accept();self.review['decisions'][0]['reviewed_claim']=dict(bad,claim_id='answer-claim')
            with self.assertRaisesRegex(ValueError,'explicit scope reference'):self.envelope()
        self.scope['evidence_refs'].append(outside);self.reset();self.response['candidates']=[bad];self.reimport();self.accept()
        self.assertEqual(ad.inspect(self.p,self.envelope())['claims'][0]['quote_check'],'EQUALS_STORED_QUOTE_ONLY')

    def test_v3_explanation_slots_and_schema_versions_cannot_be_downgraded(self):
        bad=copy.deepcopy(self.response);del bad['candidates'][0]['citations'][0]['explanation']
        with self.assertRaisesRegex(ValueError,'scope version'):ap.import_response(self.p,self.scope,self.handoff,bad,self.provenance)
        self.accept();e=self.envelope()
        for section in ('envelope','bundle','scope'):
            bad=copy.deepcopy(e);target=bad if section=='envelope' else bad['bundle'] if section=='bundle' else bad['bundle']['scope']
            target['schema']=target['schema'].replace('.v3','.v2')
            with self.assertRaises(ValueError):ad.inspect(self.p,bad)
        del self.review['decisions'][0]['reviewed_claim']['citations'][0]['explanation']
        with self.assertRaisesRegex(ValueError,'scope version'):self.envelope()

    def test_context_survives_adopted_rejected_claim_history_and_review(self):
        rejected=copy.deepcopy(self.response['candidates'][0]);rejected['text']='Rejected synthetic answer candidate.';self.response['candidates'].append(rejected)
        self.reimport();self.accept();self.review['decisions'][0]['reviewed_claim']['text']='Rewritten adopted synthetic answer.'
        self.review['decisions'][1].update(decision='reject',review_note='Rejected canned alternative.')
        e=self.envelope();r=ad.inspect(self.p,e);packet=r['proposal_review']
        self.assertEqual(packet['schema'],'persona.answer-proposal-review.v3')
        self.assertEqual(packet['research_context_review'],self.handoff['reasoning_context'])
        self.assertEqual(len(r['claims']),1);self.assertEqual(packet['candidates'][1]['decision'],'reject')
        text=ad.render(r)
        for phrase in ('Rewritten adopted synthetic answer.','Rejected synthetic answer candidate.','not proof of model use','Source requires distinct outcomes'):
            self.assertIn(phrase,text)
        self.assertFalse(packet['automatic_approval']);self.assertEqual(r['semantic_validation'],'NOT_PERFORMED')
        review=ad.review_template(self.p,e,'synthetic-final-reviewer');self.assertEqual(review['decisions'][0]['decision'],'defer')

    def test_full_rejected_pattern_history_is_preserved_and_binds_scope(self):
        p=pattern_fixture.PatternEvidenceReasonTests();p.setUp();p.response['candidates'].append(copy.deepcopy(p.proposal));p.reimport();p.accept()
        p.review['decisions'][1].update(decision='reject',review_note='Rejected pattern interpretation retained.')
        self.raw['patterns']=pattern_proposals.export_reviewed(p.package,p.bundle,p.review)
        self.scope=self.scope_for(self.raw);self.scope['evidence_refs']=[copy.deepcopy(self.c.a)];self.reset();self.accept()
        context=ad.inspect(self.p,self.envelope())['proposal_review']['research_context_review']
        self.assertEqual(context['pattern_review']['proposal_review']['candidates'][1]['decision'],'reject')
        self.assertIn('Rejected pattern interpretation retained.',ap.render_review(ap.review_proposals(self.p,self.bundle,self.review)))
        stale=copy.deepcopy(self.scope);stale['research_context']['patterns']['review']['decisions'][1]['review_note']+=' Changed.'
        with self.assertRaisesRegex(ValueError,'handoff changed'):ap.response_template(self.p,stale,self.handoff)

    def test_new_context_changes_stale_final_answer_reviews_and_arguments(self):
        self.accept();e=self.envelope();review=ad.review_template(self.p,e,'reviewer');argument=am.template(self.p,e,'op',review)
        self.scope['research_context']['context']['assessments'][0]['remaining_uncertainty']='Different declared uncertainty.';self.reset();self.accept();changed=self.envelope()
        with self.assertRaisesRegex(ValueError,'stale'):ad.review(self.p,changed,review)
        with self.assertRaises(ValueError):am.inspect(self.p,changed,argument)

    def test_no_input_mutation_and_bound_failures_preserve_full_history(self):
        before=copy.deepcopy((self.p,self.scope,self.handoff,self.response,self.bundle,self.review))
        with patch.object(Path,'open',side_effect=AssertionError('source read')):
            self.assertEqual(ap.prepare_handoff(self.p,self.scope),self.handoff)
        packet=ap.review_proposals(self.p,self.bundle,self.review);packet['research_context_review']['context_review']['target_context']='output edited'
        self.assertEqual((self.p,self.scope,self.handoff,self.response,self.bundle,self.review),before)
        with patch.object(ap,'MAX_HANDOFF_BYTES',100):
            with self.assertRaisesRegex(ValueError,'logical JSON limit'):ap.prepare_handoff(self.p,self.scope)
        with patch.object(ap,'MAX_INPUT_BYTES',100):
            with self.assertRaisesRegex(ValueError,'8 MiB'):ap.prepare_handoff(self.p,self.scope)
        with patch.object(ap,'MAX_OUTPUT_BYTES',100):
            with self.assertRaisesRegex(ValueError,'16 MiB'):ap.review_proposals(self.p,self.bundle,self.review)

    def test_direct_v3_api_rejects_python_tuple_normalization(self):
        raw=copy.deepcopy(self.raw);raw['patterns']['hypotheses']=tuple(raw['patterns']['hypotheses'])
        with self.assertRaisesRegex(ValueError,'strict JSON'):self.scope_for(raw)
        scope=copy.deepcopy(self.scope);scope['research_context']['patterns']['hypotheses']=tuple(scope['research_context']['patterns']['hypotheses'])
        with self.assertRaisesRegex(ValueError,'strict JSON'):ap.prepare_handoff(self.p,scope)
        bundle=copy.deepcopy(self.bundle);bundle['scope']['research_context']['patterns']['hypotheses']=tuple(bundle['scope']['research_context']['patterns']['hypotheses'])
        with self.assertRaisesRegex(ValueError,'strict JSON'):ap.review_proposals(self.p,bundle,self.review)
        raw=copy.deepcopy(self.raw);raw['context'][1]='non-string key'
        with self.assertRaisesRegex(ValueError,'keys must be strings'):self.scope_for(raw)

    def test_cli_quartet_all_or_none_and_explicit_explanation_mode(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for key,value in [('package',self.p),('patterns',self.raw['patterns']),('context',self.raw['context']),('relations',self.raw['publication_relations'])]:
                (root/(key+'.json')).write_text(json.dumps(value),encoding='utf-8')
            args=[sys.executable,str(ROOT/'answer_proposals.py'),'template',str(root/'package.json'),'--question',self.scope['question'],'--topic',self.scope['topic'],'--reference-year','2020','--operator-id','op']
            context=['--patterns',str(root/'patterns.json'),'--context',str(root/'context.json'),'--publication-relations',str(root/'relations.json'),'--pattern-id','comparison']
            for extra in (context,context[:2]+['--include-citation-explanations'],context[2:]+['--include-citation-explanations']):
                r=subprocess.run(args+extra,capture_output=True);self.assertNotEqual(r.returncode,0);self.assertEqual(r.stdout,b'')
            r=subprocess.run(args+context+['--include-citation-explanations'],capture_output=True,check=True)
            self.assertEqual(json.loads(r.stdout)['schema'],'persona.answer-proposal-scope.v3')


if __name__=='__main__':unittest.main()
