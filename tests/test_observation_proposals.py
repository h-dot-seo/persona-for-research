"""Review-only first-observation proposals from synthetic offline responses."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from curate_local import append_observation
from extraction_adapter import MockProvider, prepare_model_handoff
from observation_proposals import (prepare_observation_handoff, import_observation_response,
    validate_bundle, review_template, review_proposals, render)
from operator_review import review_template as reasoning_review_template
from persona import payload_sha256
from research_workflow import build

ROOT=Path(__file__).resolve().parents[1]


class ObservationProposalTests(unittest.TestCase):
    def setUp(self):
        self.corpus=json.loads((ROOT/'examples/reasoning-corpus.json').read_text())
        for paper in self.corpus['papers']:paper['observations']=[]
        self.provenance=dict(provider_id='synthetic-provider',model_id='synthetic-model',run_id='synthetic-run',
                            operator_id='synthetic-operator',execution_location='unknown')
        self.rows=[dict(paper_id='synthetic-0',method='Compare competing explanations.',condition=None,limitation=None,
            topic='model design',locator='synthetic reasoning',evidence_quote='Compare explanations.',
            proposed_claim_type='explicit_statement',proposed_stance='support'),
            dict(paper_id='synthetic-1',method='Question whether comparison distinguishes alternatives.',condition=None,
                limitation='Synthetic interpretation only.',topic=None,locator='synthetic section 1',
                evidence_quote='Compare competing models',proposed_claim_type='operator_interpretation',proposed_stance='challenge')]
        self.handoff=prepare_observation_handoff(self.corpus)
        self.response=dict(handoff_sha256=payload_sha256(self.handoff),candidates=self.rows)
        self.bundle=import_observation_response(self.corpus,self.handoff,self.response,self.provenance)

    def test_empty_observation_corpus_and_missing_fields_are_preserved(self):
        self.assertEqual(build(self.corpus)['persona']['rules'],[])
        self.assertEqual(len(self.bundle['candidates']),2)
        self.assertEqual(self.bundle['candidates'][0]['missing_fields'],['condition','limitation'])
        self.assertEqual(self.bundle['candidates'][1]['missing_fields'],['condition','topic'])
        self.assertIsNone(self.bundle['provider']['llm_used'])
        self.assertFalse(self.bundle['runtime_package_created'])
        self.assertFalse(self.bundle['canonical_update_performed'])
        self.assertNotIn('sources',self.bundle)
        self.assertNotIn('segments',self.bundle)
        self.assertEqual([r['proposed_observation']['stance'] for r in self.bundle['candidates']],['support','challenge'])

    def test_all_deferred_all_rejected_empty_and_mixed_reviews_keep_originals(self):
        review=review_template(self.corpus,self.bundle,'synthetic-reviewer')
        packet=review_proposals(self.corpus,self.bundle,review)
        self.assertEqual(packet['status'],'OBSERVATION_PROPOSAL_REVIEW_INCOMPLETE')
        self.assertTrue(all(r['reviewed_observation'] is None for r in packet['candidates']))
        for decision in review['decisions']:decision['decision']='reject'
        packet=review_proposals(self.corpus,self.bundle,review)
        self.assertEqual(packet['status'],'NO_ACCEPTED_OBSERVATION_PROPOSALS')
        self.assertEqual(len(packet['candidates']),2)
        empty=import_observation_response(self.corpus,self.handoff,dict(self.response,candidates=[]),self.provenance)
        self.assertEqual(review_proposals(self.corpus,empty,review_template(self.corpus,empty,'synthetic-reviewer'))['status'],
                         'NO_ACCEPTED_OBSERVATION_PROPOSALS')
        review['decisions'][0].update(decision='accept',reviewed_observation=copy.deepcopy(self.bundle['candidates'][0]['proposed_observation']))
        review['decisions'][1]['decision']='defer'
        packet=review_proposals(self.corpus,self.bundle,review)
        self.assertEqual(packet['status'],'OBSERVATION_PROPOSAL_REVIEW_INCOMPLETE')
        self.assertEqual(packet['accepted_proposal_count'],1)
        self.assertEqual(packet['candidates'][1]['candidate']['proposed_observation']['stance'],'challenge')
        self.assertFalse(packet['runtime_package_created'])
        self.assertNotIn('package',packet);self.assertNotIn('papers',packet)

    def accepted_review(self):
        review=review_template(self.corpus,self.bundle,'synthetic-reviewer')
        review['decisions'][0].update(decision='accept',reviewed_observation=copy.deepcopy(self.bundle['candidates'][0]['proposed_observation']))
        review['decisions'][1]['decision']='reject'
        return review

    def test_proposed_reviewed_stance_claim_and_missing_fields_stay_distinct(self):
        review=self.accepted_review();obs=review['decisions'][0]['reviewed_observation']
        obs.update(method='Operator proposes testing the comparison.',stance='challenge',claim_type='operator_interpretation')
        packet=review_proposals(self.corpus,self.bundle,review);row=packet['candidates'][0]
        self.assertEqual(packet['status'],'OBSERVATION_PROPOSALS_REVIEWED_NOT_CANONICAL')
        self.assertEqual(row['candidate']['proposed_observation']['stance'],'support')
        self.assertEqual(row['candidate']['proposed_observation']['claim_type'],'explicit_statement')
        self.assertEqual(row['reviewed_observation']['stance'],'challenge')
        self.assertEqual(row['reviewed_observation']['claim_type'],'operator_interpretation')
        self.assertEqual(row['reviewed_missing_fields'],['condition','limitation'])
        text=render(packet)
        for phrase in ('Proposed stance=support','Reviewed stance=challenge','NOT_SUPPLIED','NOT A RUNTIME PACKAGE'):
            self.assertIn(phrase,text)
        for key,value in [('locator','other section'),('evidence_quote','other quote')]:
            bad=copy.deepcopy(review);bad['decisions'][0]['reviewed_observation'][key]=value
            with self.assertRaisesRegex(ValueError,'remain unchanged'):review_proposals(self.corpus,self.bundle,bad)

    def test_no_manual_card_reasoning_bundle_or_runtime_promotion(self):
        packet=review_proposals(self.corpus,self.bundle,self.accepted_review())
        for value in (self.bundle,packet):
            with self.assertRaises(ValueError):build(value)
            with self.assertRaises(ValueError):append_observation(self.corpus,value,ROOT/'examples/synthetic-sources')
            with self.assertRaises(ValueError):reasoning_review_template(self.corpus,value,'synthetic-reviewer')

    def test_entire_authorization_boundary_precedes_source_inspection(self):
        for key,value in [('authorized',False),('authorized',1),('split','holdout'),('author_id','other'),('runtime_knowledge_eligible',False)]:
            corpus=copy.deepcopy(self.corpus);corpus['papers'][0]['segments']=None;corpus['papers'][1][key]=value
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'authorized runtime training'):
                prepare_observation_handoff(corpus)

    def test_task_staleness_metadata_and_source_tampering_rejected(self):
        with self.assertRaisesRegex(ValueError,'stale'):
            import_observation_response(self.corpus,prepare_model_handoff(self.corpus),self.response,self.provenance)
        corpus=copy.deepcopy(self.corpus);corpus['private_note']='new annotation'
        with self.assertRaisesRegex(ValueError,'stale'):
            import_observation_response(corpus,self.handoff,self.response,self.provenance)
        for field,value in [('paper_id','unknown'),('locator','unknown'),('evidence_quote','invented quote'),
                            ('proposed_stance',None),('proposed_claim_type','researcher_belief'),('method',None),('condition','')]:
            response=copy.deepcopy(self.response);response['candidates'][0][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):
                import_observation_response(self.corpus,self.handoff,response,self.provenance)

    def test_strict_schemas_provenance_and_size_limits(self):
        for response in (dict(self.response,extra=True),dict(self.response,candidates=self.rows*65)):
            with self.assertRaises(ValueError):import_observation_response(self.corpus,self.handoff,response,self.provenance)
        for key,value in [('evidence_quote','x'*501),('method','x'*2001),('reasoning',{})]:
            response=copy.deepcopy(self.response);response['candidates'][0][key]=value
            with self.assertRaises(ValueError):import_observation_response(self.corpus,self.handoff,response,self.provenance)
        for provenance in (dict(self.provenance,extra=True),dict(self.provenance,model_id=''),dict(self.provenance,execution_location='verified')):
            with self.assertRaises(ValueError):import_observation_response(self.corpus,self.handoff,self.response,provenance)
        with patch('observation_proposals.MAX_HANDOFF_BYTES',1),self.assertRaisesRegex(ValueError,'2 MiB'):
            prepare_observation_handoff(self.corpus)

    def test_changed_bundle_or_declaration_cannot_reuse_review(self):
        review=self.accepted_review()
        for part in ('top','candidate','observation','provider','receipt'):
            bundle=copy.deepcopy(self.bundle)
            if part=='top':bundle['unexpected']=True
            elif part=='candidate':bundle['candidates'][0]['missing_fields']=[]
            elif part=='observation':bundle['candidates'][0]['proposed_observation']['method']='Changed proposal'
            elif part=='provider':bundle['provider']['llm_used']=True
            else:bundle['import_record']['response_sha256']='a'*64
            with self.subTest(part=part),self.assertRaises(ValueError):validate_bundle(self.corpus,bundle)
        provenance=dict(self.provenance,run_id='new-unsigned-declaration')
        changed=import_observation_response(self.corpus,self.handoff,self.response,provenance)
        validate_bundle(self.corpus,changed)
        with self.assertRaisesRegex(ValueError,'stale'):review_proposals(self.corpus,changed,review)

    def test_missing_duplicate_unknown_decisions_and_silent_accept_fields_reject(self):
        valid=review_template(self.corpus,self.bundle,'synthetic-reviewer')
        for mutation in ('missing','duplicate','unknown','extra','empty_method'):
            review=copy.deepcopy(valid)
            if mutation=='missing':review['decisions'].pop()
            elif mutation=='duplicate':review['decisions'][1]=copy.deepcopy(review['decisions'][0])
            elif mutation=='unknown':review['decisions'][0]['candidate_id']='missing'
            elif mutation=='extra':review['decisions'][0]['reviewed_observation']={}
            else:
                review=self.accepted_review();review['decisions'][0]['reviewed_observation']['method']=''
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):review_proposals(self.corpus,self.bundle,review)

    def test_deterministic_nonmutating_no_provider_network_or_source_reads(self):
        review=self.accepted_review();before=copy.deepcopy((self.corpus,self.bundle,review))
        with patch.object(MockProvider,'extract',side_effect=AssertionError('provider')), \
             patch('socket.socket',side_effect=AssertionError('network')), \
             patch.object(Path,'open',side_effect=AssertionError('source read')):
            packet=review_proposals(self.corpus,self.bundle,review)
            self.assertEqual(packet,review_proposals(*json.loads(json.dumps((self.corpus,self.bundle,review)))))
        self.assertEqual(before,(self.corpus,self.bundle,review))
        packet['candidates'][0]['candidate']['proposed_observation']['method']='changed output'
        self.assertEqual(before,(self.corpus,self.bundle,review))

    def test_text_escapes_untrusted_fields_and_keeps_rejected_challenge(self):
        review=self.accepted_review();review['reviewer_id']='name\nFORGED';review['decisions'][1]['review_note']='note\u202eREVERSED'
        text=render(review_proposals(self.corpus,self.bundle,review))
        self.assertIn('name\\u000aFORGED',text);self.assertNotIn('\nFORGED',text)
        self.assertIn('note\\u202eREVERSED',text);self.assertIn('decision=reject',text)
        self.assertIn('Proposed stance=challenge',text)
        self.assertIn('provider_id=synthetic-provider',text);self.assertIn('model_id=synthetic-model',text)
        self.assertIn('run_id=synthetic-run',text);self.assertIn('Review sha256: '+payload_sha256(review),text)
        self.assertIn('Historical model use remains unverified',text)

    def test_actual_local_cli_empty_observations_to_noncanonical_review(self):
        def invoke(script,*args,success=True):
            result=subprocess.run([sys.executable,str(ROOT/script),*map(str,args)],capture_output=True,timeout=20)
            if success:self.assertEqual(result.returncode,0,result.stderr);return result.stdout
            self.assertNotEqual(result.returncode,0);self.assertEqual(result.stdout,b'');self.assertNotIn(b'Traceback',result.stderr)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);manifest=json.loads((ROOT/'examples/file-corpus.json').read_text())
            for paper in manifest['papers']:paper['observations']=[]
            mp=root/'manifest.json';mp.write_text(json.dumps(manifest));source=ROOT/'examples/synthetic-sources'
            hp=root/'handoff.json';hp.write_bytes(invoke('model_handoff.py','prepare',mp,'--task','observations','--source-root',source))
            response=json.loads(invoke('model_handoff.py','response-template',mp,hp,'--task','observations','--source-root',source))
            response['candidates']=[dict(self.rows[1],paper_id='synthetic-0')]
            rp=root/'response.json';rp.write_text(json.dumps(response));pp=root/'provenance.json';pp.write_text(json.dumps(self.provenance))
            bp=root/'bundle.json';bp.write_bytes(invoke('model_handoff.py','import',mp,hp,rp,pp,'--task','observations','--source-root',source))
            review=json.loads(invoke('observation_proposals.py',mp,bp,'--template','--reviewer-id','synthetic-reviewer','--source-root',source))
            review['decisions'][0]['decision']='reject';vp=root/'review.json';vp.write_text(json.dumps(review))
            packet=json.loads(invoke('observation_proposals.py',mp,bp,vp,'--source-root',source))
            self.assertEqual(packet['status'],'NO_ACCEPTED_OBSERVATION_PROPOSALS');self.assertEqual(len(packet['candidates']),1)
            text=invoke('observation_proposals.py',mp,bp,vp,'--source-root',source,'--format','text').decode()
            self.assertIn('NOT A RUNTIME PACKAGE',text);self.assertIn('Proposed stance=challenge',text)
            rp.write_text('{"candidates":[],"candidates":[]}')
            invoke('model_handoff.py','import',mp,hp,rp,pp,'--task','observations','--source-root',source,success=False)
            invoke('model_handoff.py','response-template',mp,hp,'--source-root',source,success=False)
            self.assertEqual(json.loads(mp.read_text()),manifest)


if __name__=='__main__':unittest.main()
