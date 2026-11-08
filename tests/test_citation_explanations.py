"""Synthetic citation interpretations, not semantic support or author fidelity."""
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
import tests.test_answer_draft as manual_fixture
import tests.test_answer_proposals as imported_fixture
from persona import payload_sha256
from extraction_adapter import MockProvider

ROOT = Path(__file__).resolve().parents[1]
EXPLANATION = dict(rationale='The recorded alternative motivates comparing distinct predictions.',
    context_boundary='Synthetic comparison only; transfer and source authorship are unverified.')


class FrozenLegacyReplayTests(unittest.TestCase):
    def test_captured_v055_manual_and_imported_arguments_replay_exactly(self):
        frozen = json.loads((ROOT/'examples/legacy-answer-argument-v055.json').read_text(encoding='utf-8'))
        self.assertEqual(frozen['captured_from_commit'], '30dbde6fa0a9b40ef1d48648a79e452d3403b067')
        self.assertTrue(frozen['synthetic_only']); package=frozen['package']
        for case in frozen['cases']:
            with self.subTest(case=case['label']):
                d=case['draft'];r=case['review'];s=case['argument_scope'];b=case['argument_bundle'];a=case['argument_adoption']
                values={'answer_inspection':ad.inspect(package,d), 'answer_reviewed':ad.review(package,d,r),
                    'argument_handoff':gp.prepare_handoff(package,d,s,r), 'argument_bundle':gp.validate_bundle(package,d,b,r),
                    'argument_packet':gp.review_proposals(package,d,b,a,r), 'argument_inspection':am.inspect(package,d,case['argument_envelope'],r)}
                self.assertEqual({k:payload_sha256(v) for k,v in values.items()},case['expected_sha256'])
                self.assertEqual(hashlib.sha256(ad.render(values['answer_inspection']).encode('utf-8')).hexdigest(),case['answer_text_sha256'])
                self.assertEqual(gp.import_response(package,d,s,case['argument_handoff'],case['argument_response'],b['import_record']['provenance'],r),b)
                self.assertEqual(gp.export_reviewed(package,d,b,a,r),case['argument_envelope'])

    def test_captured_answer_scope_handoff_bundle_and_envelope_are_identical(self):
        frozen=json.loads((ROOT/'examples/legacy-answer-argument-v055.json').read_text(encoding='utf-8'))
        p=frozen['package'];a=frozen['answer_records'];s=a['scope']
        self.assertEqual(ap.template(p,s['question'],s['topic'],s['reference_year'],s['operator_id']),dict(s,evidence_refs=[]))
        self.assertEqual(ap.prepare_handoff(p,s),a['handoff'])
        self.assertEqual(ap.import_response(p,s,a['handoff'],a['response'],a['bundle']['import_record']['provenance']),a['bundle'])
        self.assertEqual(ap.validate_bundle(p,a['bundle']),a['bundle'])
        self.assertEqual(ap.export_reviewed(p,a['bundle'],a['adoption']),a['envelope'])


class CitationExplanationTests(unittest.TestCase):
    def setUp(self):
        self.case=manual_fixture.AnswerDraftTests();self.case.setUp();self.p=self.case.package;self.d=self.case.draft

    def test_manual_legacy_absent_vs_explicit_null_vs_declared(self):
        old=ad.inspect(self.p,self.d)
        self.assertNotIn('explanation',old['claims'][1]['citations'][0])
        self.d['claims'][1]['citations'][0]['explanation']=None
        self.d['claims'][1]['citations'][1]['explanation']=copy.deepcopy(EXPLANATION)
        result=ad.inspect(self.p,self.d);a,b=result['claims'][1]['citations']
        self.assertEqual(a['explanation_status'],'EXPLICITLY_NOT_SUPPLIED')
        self.assertEqual(a['explanation_review_prompts'],['CITATION_EXPLANATION_NOT_SUPPLIED'])
        self.assertEqual(b['explanation'],EXPLANATION)
        self.assertEqual(b['explanation_origin'],'OPERATOR_SUPPLIED_INTERPRETATION')
        self.assertEqual(b['explanation_review_prompts'],[])
        self.assertEqual(result['semantic_validation'],'NOT_PERFORMED')
        self.assertIn('Interpretation is not verified support',ad.render(result))

    def test_exact_keys_bounds_and_nonempty_fields(self):
        for value in (False,[],{},'reason',{'rationale':'x'},dict(EXPLANATION,extra=True),
                      dict(EXPLANATION,rationale=None),dict(EXPLANATION,rationale=' '),dict(EXPLANATION,rationale='x'*2001),
                      dict(EXPLANATION,context_boundary=' '),dict(EXPLANATION,context_boundary='x'*2001),dict(EXPLANATION,context_boundary=42)):
            with self.subTest(value=value):
                d=copy.deepcopy(self.d);d['claims'][1]['citations'][0]['explanation']=value
                with self.assertRaises(ValueError):ad.inspect(self.p,d)
        self.d['claims'][1]['citations'][0]['explanation']=dict(rationale='x'*2000,context_boundary=None)
        self.assertIsNone(ad.inspect(self.p,self.d)['claims'][1]['citations'][0]['explanation']['context_boundary'])
        self.d['claims'][1]['citations'][0]['extra']='unsupported'
        with self.assertRaises(ValueError):ad.inspect(self.p,self.d)

    def test_source_quote_equality_and_roles_still_enforced(self):
        self.d['claims'][0]['citations'][0]['explanation']=copy.deepcopy(EXPLANATION)
        self.assertEqual(ad.inspect(self.p,self.d)['claims'][0]['quote_check'],'EQUALS_STORED_QUOTE_ONLY')
        self.d['claims'][0]['text']+=' '
        with self.assertRaisesRegex(ValueError,'exactly equal'):ad.inspect(self.p,self.d)
        self.d['claims'][0]['text']=self.d['claims'][0]['text'][:-1]
        self.d['claims'][0]['citations'][0]['role']='author_recommendation'
        with self.assertRaises(ValueError):ad.inspect(self.p,self.d)

    def test_duplicate_reference_role_is_not_avoided_by_different_explanations(self):
        row=self.d['claims'][1]['citations'][0];row['explanation']=copy.deepcopy(EXPLANATION)
        self.d['claims'][1]['citations'].append(dict(copy.deepcopy(row),explanation=None))
        with self.assertRaisesRegex(ValueError,'duplicate'):ad.inspect(self.p,self.d)

    def test_explanation_edit_stales_declared_review_and_argument(self):
        review=ad.review_template(self.p,self.d,'synthetic-reviewer');argument=am.template(self.p,self.d,'synthetic-map',review)
        self.d['claims'][1]['citations'][0]['explanation']=None
        with self.assertRaisesRegex(ValueError,'stale'):ad.review(self.p,self.d,review)
        with self.assertRaises(ValueError):am.inspect(self.p,self.d,argument,review)
        fresh=ad.review_template(self.p,self.d,'synthetic-reviewer')
        with self.assertRaises(ValueError):am.inspect(self.p,self.d,argument,fresh)

    def test_inspection_no_provider_source_read_or_mutation(self):
        self.d['claims'][1]['citations'][0]['explanation']=copy.deepcopy(EXPLANATION)
        before=copy.deepcopy((self.p,self.d))
        with patch.object(MockProvider,'extract',side_effect=AssertionError('provider')),patch.object(Path,'read_text',side_effect=AssertionError('source')):
            result=ad.inspect(self.p,self.d)
        result['claims'][1]['citations'][0]['explanation']['rationale']='output edited'
        self.assertEqual((self.p,self.d),before)


class ReasonedAnswerProposalTests(unittest.TestCase):
    def setUp(self):
        self.c=imported_fixture.AnswerProposalTests();self.c.setUp()
        c=self.c;c.scope=ap.template(c.package,c.scope['question'],c.scope['topic'],c.scope['reference_year'],c.scope['operator_id'],include_citation_explanations=True)
        c.scope['evidence_refs']=[copy.deepcopy(x['reference']) for x in c.candidate['citations']]
        c.handoff=ap.prepare_handoff(c.package,c.scope);c.response=ap.response_template(c.package,c.scope,c.handoff)
        claim=copy.deepcopy(c.candidate)
        for citation in claim['citations']:citation['explanation']=None
        c.response['candidates']=[claim];c.reimport()

    def test_explicit_flag_versioned_contract_empty_selection_and_boolean(self):
        c=self.c
        for version, key in [('scope','scope'),('handoff','handoff'),('bundle','bundle')]:
            self.assertTrue(getattr(c,key)['schema'].endswith('.v2'))
        self.assertEqual(c.handoff['response_contract']['citation_fields'],['reference','role','explanation'])
        self.assertFalse(c.handoff['processing']['provider_invoked'])
        for value in (1,0,None,'true',[]):
            with self.assertRaisesRegex(ValueError,'boolean'):ap.template(c.package,'Q','T',2020,'op',include_citation_explanations=value)
        empty=ap.template(c.package,'Q','T',2020,'op',include_citation_explanations=True)
        self.assertEqual(empty['evidence_refs'],[])
        with self.assertRaises(ValueError):ap.prepare_handoff(c.package,empty)

    def test_missing_explanations_keep_review_deferred_no_auto_approval(self):
        c=self.c;packet=c.packet();row=packet['candidates'][0]
        self.assertEqual(c.review['decisions'][0]['decision'],'defer')
        self.assertIn('CITATION_EXPLANATION_NOT_SUPPLIED',row['original_inspection']['review_prompts'])
        self.assertEqual(row['original_inspection']['citations'][0]['explanation_origin'],'UNTRUSTED_IMPORTED_INTERPRETATION')
        with self.assertRaises(ValueError):c.envelope()
        c.accept();envelope=c.envelope();self.assertTrue(envelope['schema'].endswith('.v2'))
        result=ad.inspect(c.package,envelope)
        self.assertEqual(result['claims'][0]['citations'][0]['explanation_origin'],'OPERATOR_ADOPTED_IMPORTED_INTERPRETATION')
        self.assertEqual(result['semantic_validation'],'NOT_PERFORMED');self.assertFalse(result['llm_used'])
        self.assertNotIn('review',result);self.assertFalse(result['proposal_review']['automatic_approval'])

    def test_v1_rejects_enhanced_original_and_adopted_fields(self):
        c=imported_fixture.AnswerProposalTests();c.setUp()
        c.response['candidates'][0]['citations'][0]['explanation']=None
        with self.assertRaisesRegex(ValueError,'scope version'):c.reimport()
        del c.response['candidates'][0]['citations'][0]['explanation'];c.reimport();c.accept()
        c.review['decisions'][0]['reviewed_claim']['citations'][0]['explanation']=None
        with self.assertRaisesRegex(ValueError,'scope version'):c.envelope()

    def test_v2_requires_slots_in_original_and_adopted_claims(self):
        c=self.c;del c.response['candidates'][0]['citations'][0]['explanation']
        with self.assertRaisesRegex(ValueError,'scope version'):c.reimport()
        c.response['candidates'][0]['citations'][0]['explanation']=None;c.reimport();c.accept()
        del c.review['decisions'][0]['reviewed_claim']['citations'][0]['explanation']
        with self.assertRaisesRegex(ValueError,'scope version'):c.envelope()

    def test_version_mixing_downgrade_and_unknown_schema_reject(self):
        c=self.c;c.accept();envelope=c.envelope()
        for section in ('envelope','bundle','scope'):
            bad=copy.deepcopy(envelope)
            target=bad if section=='envelope' else bad['bundle'] if section=='bundle' else bad['bundle']['scope']
            target['schema']=target['schema'].replace('.v2','.v1')
            with self.assertRaises(ValueError):ad.inspect(c.package,bad)
        for schema in ('persona.answer-proposal-scope.v3',None,[],{}) :
            bad=copy.deepcopy(c.scope);bad['schema']=schema
            with self.assertRaises(ValueError):ap.prepare_handoff(c.package,bad)
        for invalid in (None, [], {}):
            bad=copy.deepcopy(envelope);bad['schema']=invalid
            with self.assertRaises(ValueError):ap.inspect_reviewed(c.package,bad)
            bad=copy.deepcopy(c.bundle);bad['schema']=invalid
            with self.assertRaises(ValueError):ap.validate_bundle(c.package,bad)
        bad=copy.deepcopy(c.handoff);bad['schema']=bad['schema'].replace('.v2','.v1')
        with self.assertRaises(ValueError):ap.response_template(c.package,c.scope,bad)

    def test_original_revised_and_rejected_reason_history_is_preserved(self):
        c=self.c;c.response['candidates'][0]['citations'][0]['explanation']=dict(EXPLANATION,rationale='Original synthetic imported rationale.')
        c.response['candidates'].append(copy.deepcopy(c.response['candidates'][0]));c.response['candidates'][1]['citations'][0]['explanation']['rationale']='Rejected synthetic rationale.'
        c.reimport();c.accept();c.review['decisions'][0]['reviewed_claim']['citations'][0]['explanation']['rationale']='Edited adopted rationale.'
        c.review['decisions'][1].update(decision='reject',review_note='Synthetic rejected candidate.')
        result=ad.inspect(c.package,c.envelope());text=ad.render(result)
        for phrase in ('Original synthetic imported rationale.','Rejected synthetic rationale.','Edited adopted rationale.'):
            self.assertIn(phrase,text)
        self.assertEqual(len(result['claims']),1)
        self.assertEqual(result['claims'][0]['citations'][0]['explanation']['rationale'],'Edited adopted rationale.')
        self.assertIn('UNTRUSTED_IMPORTED_INTERPRETATION',text);self.assertIn('OPERATOR_ADOPTED_IMPORTED_INTERPRETATION',text)
        self.assertFalse(result['proposal_review']['scientific_execution'])

    def test_invalid_explanations_and_quote_equality_are_not_relaxed(self):
        c=self.c;c.response['candidates'][0]['citations'][0]['explanation']={'rationale':'invented'}
        with self.assertRaises(ValueError):c.reimport()
        candidate=copy.deepcopy(c.quote)
        candidate['citations'][0]['explanation']=copy.deepcopy(EXPLANATION)
        c.response['candidates']=[candidate];c.reimport();c.accept()
        self.assertEqual(ad.inspect(c.package,c.envelope())['claims'][0]['quote_check'],'EQUALS_STORED_QUOTE_ONLY')
        c.review['decisions'][0]['reviewed_claim']['text']+=' '
        with self.assertRaises(ValueError):c.envelope()

    def test_enhanced_claim_handoff_and_imported_argument_replay(self):
        c=self.c;c.accept(claim_id='premise');d=c.envelope()
        # Add an independent accepted conclusion explicitly; no citation transfer.
        c.response['candidates'].append(dict(text='Synthetic conclusion.',claim_type='operator_synthesis',uncertainty=None,citations=[]))
        c.reimport();c.accept(0,'premise');c.accept(1,'conclusion');d=c.envelope()
        s=gp.template(c.package,d,'op');s['selected_claim_ids']=['premise','conclusion'];h=gp.prepare_handoff(c.package,d,s)
        self.assertIsNone(h['selected_claims'][0]['citations'][0]['explanation'])
        response=gp.response_template(c.package,d,s,h);response['candidates']=[dict(premise_claim_ids=['premise'],conclusion_claim_id='conclusion',bridge_rationale='Synthetic bridge.',assumptions=[],defeater=None)]
        b=gp.import_response(c.package,d,s,h,response,c.provenance);r=gp.review_template(c.package,d,b,'reviewer')
        r['decisions'][0].update(decision='accept',review_note='Synthetic adoption.',reviewed_step=dict(response['candidates'][0],step_id='step'))
        e=gp.export_reviewed(c.package,d,b,r);result=am.inspect(c.package,d,e)
        self.assertEqual(result['steps'][0]['conclusion']['direct_citation_count'],0)
        self.assertEqual(result['steps'][0]['citation_transfer'],'NOT_PERFORMED')
        changed=copy.deepcopy(d);changed['review']['decisions'][0]['reviewed_claim']['citations'][0]['explanation']=copy.deepcopy(EXPLANATION)
        with self.assertRaises(ValueError):am.inspect(c.package,changed,e)

    def test_cli_version_flag_and_json_inspection(self):
        c=self.c;c.accept()
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);p=root/'package.json';d=root/'draft.json'
            p.write_text(json.dumps(c.package),encoding='utf-8');d.write_text(json.dumps(c.envelope()),encoding='utf-8')
            args=[sys.executable,str(ROOT/'answer_proposals.py'),'template',str(p),'--question','Q','--topic','T','--reference-year','2020','--operator-id','op']
            legacy=subprocess.run(args,capture_output=True,check=True);enhanced=subprocess.run(args+['--include-citation-explanations'],capture_output=True,check=True)
            self.assertTrue(json.loads(legacy.stdout)['schema'].endswith('.v1'));self.assertTrue(json.loads(enhanced.stdout)['schema'].endswith('.v2'))
            inspected=subprocess.run([sys.executable,str(ROOT/'answer_draft.py'),str(p),str(d)],capture_output=True,check=True)
            self.assertEqual(json.loads(inspected.stdout),ad.inspect(c.package,c.envelope()))


if __name__=='__main__':unittest.main()
