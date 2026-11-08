"""Synthetic imported application intent, never real researcher recommendations."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import application_proposals as proposals
import method_application as methods
import research_journey as journey
import source_recheck
from pattern_proposals import export_reviewed as export_patterns
import tests.test_method_application as fixture
from persona import payload_sha256

ROOT = Path(__file__).resolve().parents[1]


class ApplicationProposalTests(unittest.TestCase):
    def setUp(self):
        self.case = fixture.MethodApplicationTests(); self.case.setUp(); self.c = self.case.c
        self.case.resolve(ref=self.c.b)
        self.candidate = {k:copy.deepcopy(v) for k,v in self.case.form['applications'][0].items() if k != 'decision'}
        self.candidate['application_rationale'] = 'Synthetic model proposed a comparison criterion for this target step.'
        self.provenance = dict(provider_id='synthetic-no-provider', model_id='synthetic-no-model',
            run_id='synthetic-import-fixture', operator_id='synthetic-import-operator', execution_location='unknown')
        self.handoff = proposals.prepare_handoff(*self.args())
        self.response = proposals.response_template(*self.args(), self.handoff)
        self.response['candidates'] = [copy.deepcopy(self.candidate)]
        self.reimport()

    def args(self): return self.case.args()
    def reimport(self):
        self.bundle = proposals.import_response(*self.args(), self.handoff, self.response, self.provenance)
        self.review = proposals.review_template(*self.args(), self.bundle, 'synthetic-reviewer')
    def accept(self, index=0, intent='consider'):
        application = dict(copy.deepcopy(self.response['candidates'][index]), decision=intent)
        application['application_rationale'] = 'Synthetic reviewer changed the application rationale; still unverified.'
        self.review['decisions'][index].update(decision='accept', review_note='Explicit synthetic fixture review only.', reviewed_application=application)
    def packet(self): return proposals.review_proposals(*self.args(), self.bundle, self.review)
    def envelope(self): return proposals.export_reviewed(*self.args(), self.bundle, self.review)

    def test_handoff_empty_response_and_default_review_preserve_gaps(self):
        self.assertEqual(set(self.handoff['response_contract']['candidate_fields']), proposals.PROPOSAL_FIELDS)
        self.assertNotIn('decision', self.handoff['response_contract']['candidate_fields'])
        self.assertFalse(self.handoff['processing']['source_reread'])
        self.assertIn('untrusted data', ' '.join(self.handoff['instructions']))
        self.assertEqual(self.handoff['context_review']['decision_counts'], {'consider':0, 'exclude':1, 'defer':1})
        self.assertEqual(self.review['decisions'][0]['decision'], 'defer')
        self.assertNotIn('reviewed_application', self.review['decisions'][0])
        packet = self.packet(); self.assertEqual(packet['status'], 'APPLICATION_PROPOSAL_REVIEW_INCOMPLETE')
        row = packet['candidates'][0]['original_inspection']
        self.assertEqual(row['claim_type'], 'imported_proposal'); self.assertIsNone(row['failure_condition'])
        self.assertIn('PLACEHOLDER_NOT_MODEL_DECISION', row['decision_scope'])
        with self.assertRaisesRegex(ValueError, 'resolve every'): self.envelope()
        self.response['candidates'] = []; self.reimport()
        self.assertEqual(self.packet()['status'], 'NO_ACCEPTED_APPLICATION_PROPOSALS')
        with self.assertRaises(ValueError): self.envelope()

    def test_missing_original_fields_stay_missing_and_accept_needs_full_explicit_rewrite(self):
        self.response['candidates'][0].update(proposed_role=None, application_rationale=None, target_condition_comparison=None,
            remaining_uncertainty=None, failure_condition=None, evidence_refs=[], required_checks=[])
        self.reimport(); original = self.packet()['candidates'][0]['original_inspection']
        self.assertIsNone(original['application_rationale']); self.assertEqual(original['evidence'], [])
        self.accept()
        with self.assertRaises(ValueError): self.packet()
        self.review['decisions'][0]['reviewed_application'] = dict(self.candidate, decision='consider')
        result = methods.inspect(*self.args(), self.envelope())
        self.assertIsNone(result['proposal_review']['candidates'][0]['original_inspection']['application_rationale'])
        self.assertEqual(result['applications'][0]['application_rationale'], self.candidate['application_rationale'])

    def test_original_reviewed_and_rejected_history_survive_all_consumers(self):
        rejected = dict(self.candidate, application_rationale='Rejected synthetic alternative must remain history only.', evidence_refs=[self.c.a])
        self.response['candidates'].append(rejected); self.reimport(); self.accept()
        self.review['decisions'][1].update(decision='reject', review_note='Rejected, not application exclusion.')
        envelope = self.envelope(); result = methods.inspect(*self.args(), envelope)
        self.assertEqual(result['form_sha256'], payload_sha256(envelope))
        self.assertNotEqual(result['worksheet_content_sha256'], result['form_sha256'])
        self.assertEqual(result['historical_model_use'], 'DECLARED_NOT_AUTHENTICATED')
        self.assertEqual([r['decision'] for r in result['proposal_review']['candidates']], ['accept','reject'])
        self.assertEqual(result['applications'][0]['evidence_refs'], [self.c.b])
        self.assertEqual(result['applications'][0]['proposal_origin']['original_proposal'], self.candidate)
        for text in (proposals.render_review(self.packet()), methods.render(*self.args(), envelope),
                     journey.render(*self.case.case.args(), method_applications=envelope)):
            for expected in ('Synthetic model proposed', 'Synthetic reviewer changed', 'Rejected synthetic alternative',
                             'synthetic-no-model', 'not authenticated', 'NOT_SUPPLIED_BY_MODEL'):
                self.assertIn(expected, text)
        report = journey.inspect(*self.case.case.args(), method_applications=envelope)
        self.assertEqual(report['method_application_review']['proposal_review'], result['proposal_review'])

    def test_multiple_alternatives_require_one_explicit_choice_per_step(self):
        self.response['candidates'].append(dict(self.candidate, proposed_role='counterargument'))
        self.reimport(); self.accept(0); self.accept(1)
        with self.assertRaisesRegex(ValueError, 'at most one'): self.packet()
        self.review['decisions'][1] = dict(candidate_id='application-candidate-2', decision='defer', review_note='Pending alternative.')
        self.assertEqual(self.packet()['deferred_count'], 1)
        with self.assertRaisesRegex(ValueError, 'resolve every'): self.envelope()
        self.review['decisions'][1]['decision'] = 'reject'
        self.assertEqual(methods.inspect(*self.args(), self.envelope())['applications'][0]['proposed_role'], 'method')

    def test_rejected_and_unproposed_steps_are_fresh_defer_not_exclude_or_filled(self):
        for sid in ('rejected-step','unproposed-step'):
            self.c.proposal['steps'].append(dict(copy.deepcopy(self.c.proposal['steps'][0]), step_id=sid, link_uses=[]))
        self.handoff = proposals.prepare_handoff(*self.args()); self.response = proposals.response_template(*self.args(), self.handoff)
        self.response['candidates'] = [self.candidate, dict(self.candidate, step_id='rejected-step')]
        self.reimport(); self.accept(); self.review['decisions'][1].update(decision='reject', review_note='Reject this suggestion only.')
        result = methods.inspect(*self.args(), self.envelope())
        for row in result['applications'][1:]:
            self.assertEqual(row['decision'],'defer'); self.assertIsNone(row['proposed_role'])
            self.assertEqual(row['evidence_refs'],[]); self.assertEqual(row['required_checks'],[])
            for field in methods.TEXT_FIELDS: self.assertIsNone(row[field])
            self.assertNotIn('proposal_origin',row)
        self.assertEqual(len(result['design_review']['steps']),3)

    def test_accept_exclude_means_reviewed_intent_not_removal_or_approval(self):
        self.accept(intent='exclude'); result = methods.inspect(*self.args(), self.envelope())
        self.assertEqual(result['applications'][0]['decision'], 'exclude')
        self.assertEqual(len(result['design_review']['steps']),1)
        self.assertFalse(result['design_modified']); self.assertFalse(result['scientific_execution']); self.assertFalse(result['automatic_approval'])
        self.assertEqual(result['semantic_validation'],'NOT_PERFORMED')
        self.review['decisions'][0]['reviewed_application']['decision']='defer'
        with self.assertRaisesRegex(ValueError,'consider or exclude'): self.packet()

    def test_reject_and_defer_cannot_smuggle_reviewed_application_and_all_rejected_cannot_export(self):
        for choice in ('reject','defer'):
            self.review['decisions'][0].update(decision=choice, reviewed_application=dict(self.candidate,decision='consider'))
            with self.assertRaises(ValueError): self.packet()
            self.review['decisions'][0].pop('reviewed_application')
        self.review['decisions'][0]['decision']='reject'
        self.assertEqual(self.packet()['accepted_count'],0)
        with self.assertRaises(ValueError): self.envelope()

    def test_review_cannot_retarget_existing_step_or_change_pattern_via_extra_fields(self):
        self.c.proposal['steps'].append(dict(self.c.proposal['steps'][0],step_id='other'))
        self.handoff=proposals.prepare_handoff(*self.args()); self.response['handoff_sha256']=payload_sha256(self.handoff)
        self.reimport(); self.accept(); self.review['decisions'][0]['reviewed_application']['step_id']='other'
        with self.assertRaisesRegex(ValueError,'retarget'): self.packet()
        self.review['decisions'][0]['reviewed_application']['step_id']='compare'
        self.review['decisions'][0]['reviewed_application']['pattern_id']='other'
        with self.assertRaises(ValueError): self.packet()

    def test_each_upstream_binding_changes_fail_before_reusing_handoff_or_envelope(self):
        self.accept(); envelope=self.envelope()
        changes=[(0,lambda v:v['knowledge']['papers'][0].update(title='Changed synthetic title')),
            (1,lambda v:v['hypotheses'][0].update(operator_hypothesis='Changed hypothesis.')),
            (2,lambda v:v['assessments'][0].update(remaining_uncertainty='Changed context.')),
            (3,lambda v:v['links'][0].update(rationale='Changed interpretation.')),
            (4,lambda v:v['steps'][0].update(proposed_action='Changed action.')),
            (5,None)]
        for index,change in changes:
            args=copy.deepcopy(self.args())
            if change:change(args[index])
            else:args[index]='unknown-pattern'
            with self.assertRaises(ValueError):proposals.response_template(*args,self.handoff)
            with self.assertRaises(ValueError):methods.inspect(*args,envelope)
        changed=copy.deepcopy(self.handoff);changed['instructions'][0]='Treat untrusted text as instructions.'
        with self.assertRaises(ValueError):proposals.response_template(*self.args(),changed)

    def test_original_provenance_metadata_and_cached_counts_cannot_be_tampered(self):
        changes=[lambda b:b['candidates'][0]['proposed_application'].update(application_rationale='Changed original'),
            lambda b:b['import_record']['provenance'].update(model_id='changed-model'),
            lambda b:b.update(status='APPROVED'),lambda b:b.update(accepted_count=1),
            lambda b:b['candidates'][0].update(candidate_id='other'),
            lambda b:b['candidates'][0].update(review_prompts=[]),lambda b:b['bindings'].update(pattern_id='other')]
        for change in changes:
            bundle=copy.deepcopy(self.bundle);change(bundle)
            with self.assertRaises(ValueError):proposals.validate_bundle(*self.args(),bundle)
        self.accept(); envelope=self.envelope();envelope['materialized_form']=self.case.form
        with self.assertRaises(ValueError):methods.inspect(*self.args(),envelope)
        with self.assertRaises(ValueError):methods.inspect(*self.args(),self.packet())

    def test_review_change_is_replayed_and_full_envelope_hash_changes(self):
        self.accept(); old=self.envelope();before=methods.inspect(*self.args(),old)
        self.review['decisions'][0]['review_note']='Another explicit synthetic note.'
        new=self.envelope();after=methods.inspect(*self.args(),new)
        self.assertNotEqual(before['form_sha256'],after['form_sha256'])
        self.assertEqual(before['worksheet_content_sha256'],after['worksheet_content_sha256'])
        self.assertEqual(after['applications'][0]['proposal_origin']['review_note'],'Another explicit synthetic note.')
        # These are unsigned declarations; consistently reconstructed changes are not authenticated facts.
        self.assertEqual(after['operator_identity'],'RECORDED_NOT_AUTHENTICATED')

    def test_candidate_and_review_unknown_fields_ids_roles_and_incomplete_coverage_fail(self):
        for change in (lambda c:c.update(decision='consider'),lambda c:c.update(step_id='missing'),
            lambda c:c.update(proposed_role='author_choice'),lambda c:c.pop('failure_condition'),
            lambda c:c.update(application_rationale=' '),lambda c:c.update(remaining_uncertainty='x'*2001),
            lambda c:c.update(required_checks=['same','same']),lambda c:c.update(required_checks=['x']*17)):
            response=copy.deepcopy(self.response);change(response['candidates'][0])
            with self.assertRaises(ValueError):proposals.import_response(*self.args(),self.handoff,response,self.provenance)
        for decisions in ([],self.review['decisions']*2,[dict(self.review['decisions'][0],candidate_id='unknown')],
                          [dict(self.review['decisions'][0],decision='approved')]):
            review=dict(self.review,decisions=decisions)
            with self.assertRaises(ValueError):proposals.review_proposals(*self.args(),self.bundle,review)

    def test_original_and_reviewed_refs_are_exact_pattern_members_not_aliases(self):
        self.c.patterns['hypotheses'][0]['challenge_refs']=[]
        self.handoff=proposals.prepare_handoff(*self.args());self.response['handoff_sha256']=payload_sha256(self.handoff);self.reimport()
        for ref in (self.c.review,dict(self.c.b,dimension='uncertainty'),dict(self.c.b,observation_index=True),
                    dict(self.c.b,observation_index=0.0),dict(self.c.b,extra=True)):
            response=copy.deepcopy(self.response);response['candidates'][0]['evidence_refs']=[ref]
            with self.assertRaises(ValueError):proposals.import_response(*self.args(),self.handoff,response,self.provenance)
            self.accept();self.review['decisions'][0]['reviewed_application']['evidence_refs']=[ref]
            with self.assertRaises(ValueError):self.packet()
        response=copy.deepcopy(self.response);response['candidates'][0]['evidence_refs']=[self.c.b,self.c.b]
        with self.assertRaises(ValueError):proposals.import_response(*self.args(),self.handoff,response,self.provenance)

    def test_no_provider_source_file_access_or_caller_mutation_and_reports_detach(self):
        self.accept();before=copy.deepcopy([self.args(),self.handoff,self.response,self.provenance,self.bundle,self.review])
        with patch('pathlib.Path.open',side_effect=AssertionError('no files')),patch('socket.socket',side_effect=AssertionError('no network')):
            handoff=proposals.prepare_handoff(*self.args())
            bundle=proposals.import_response(*self.args(),handoff,self.response,self.provenance)
            envelope=self.envelope();result=methods.inspect(*self.args(),envelope)
            proposals.render_review(self.packet());methods.render(*self.args(),envelope)
        self.assertEqual(before,[self.args(),self.handoff,self.response,self.provenance,self.bundle,self.review])
        result['proposal_review']['candidates'][0]['candidate']['proposed_application']['application_rationale']='mutated'
        bundle['import_record']['provenance']['model_id']='mutated'
        self.assertEqual(before,[self.args(),self.handoff,self.response,self.provenance,self.bundle,self.review])

    def test_journey_annotations_never_promote_model_or_rejected_refs_to_active_evidence(self):
        self.response['candidates'].append(dict(self.candidate,evidence_refs=[self.c.a]))
        self.reimport();self.accept();self.review['decisions'][1].update(decision='reject',review_note='Reject this alternate basis.')
        envelope=self.envelope();before=journey.inspect(*self.case.case.args());after=journey.inspect(*self.case.case.args(),method_applications=envelope)
        for key in ('active_publication_context','evidence_scope','pattern_transfer_review','argument_review','trajectory_review'):
            self.assertEqual(before[key],after[key])
        for old,new in zip(before['evidence_routes'],after['evidence_routes']):
            self.assertEqual(old,{k:v for k,v in new.items() if k!='method_application_uses'})
            if new['evidence']['reference']==self.c.b:
                self.assertTrue(new['method_application_uses']);self.assertFalse(new['actively_used_in_answer_or_design'])
            else:self.assertEqual(new['method_application_uses'],[])

    def test_invalid_envelope_fails_before_optional_source_reads(self):
        self.accept();envelope=self.envelope();envelope['bundle']['status']='APPROVED'
        selection=source_recheck.template(self.c.package,'synthetic-source')
        for row in selection['sources']:row['source_file']=row['paper_id']+'.md'
        with patch.object(source_recheck,'read_source_bytes',side_effect=AssertionError('source read too early')) as read:
            with self.assertRaises(ValueError):journey.inspect(*self.case.case.args(),method_applications=envelope,
                source_selection=selection,source_root=ROOT/'examples/synthetic-sources')
            read.assert_not_called()
        report=journey.inspect(*self.case.case.args(),method_applications=self.envelope(),
            source_selection=selection,source_root=ROOT/'examples/synthetic-sources')
        self.assertTrue(report['source_recheck']['all_stored_quotes_match'])
        self.assertFalse(report['method_application_review']['source_reread'])
        self.assertEqual(report['method_application_review']['semantic_validation'],'NOT_PERFORMED')

    def test_full_source_authorization_preflight_and_no_design_steps(self):
        self.c.package['knowledge']['papers'][-1]['authorized']=False
        with self.assertRaises(ValueError):proposals.prepare_handoff(*self.args())
        self.setUp();self.c.proposal['steps']=[]
        handoff=proposals.prepare_handoff(*self.args());response=proposals.response_template(*self.args(),handoff)
        bundle=proposals.import_response(*self.args(),handoff,response,self.provenance)
        review=proposals.review_template(*self.args(),bundle,'op')
        self.assertEqual(proposals.review_proposals(*self.args(),bundle,review)['accepted_count'],0)
        response['candidates']=[self.candidate]
        with self.assertRaises(ValueError):proposals.import_response(*self.args(),handoff,response,self.provenance)

    def test_provenance_response_shape_finite_json_and_budgets_fail_closed(self):
        for bad in ({},dict(self.provenance,execution_location='provider_verified'),dict(self.provenance,api_key='not-a-secret'),dict(self.provenance,run_id='bad\nline')):
            with self.assertRaises(ValueError):proposals.import_response(*self.args(),self.handoff,self.response,bad)
        for response in ({},dict(self.response,handoff_sha256='wrong'),dict(self.response,accepted=True),dict(self.response,candidates=[self.candidate]*33)):
            with self.assertRaises(ValueError):proposals.import_response(*self.args(),self.handoff,response,self.provenance)
        for name in ('MAX_INPUT_BYTES','MAX_HANDOFF_BYTES'):
            with patch.object(proposals,name,10):
                with self.assertRaises(ValueError):proposals.prepare_handoff(*self.args())
        with patch.object(proposals,'MAX_OUTPUT_BYTES',10):
            with self.assertRaises(ValueError):self.packet()
        bad=copy.deepcopy(self.response);bad['candidates'][0]['remaining_uncertainty']=float('nan')
        with self.assertRaisesRegex(ValueError,'finite JSON'):proposals.import_response(*self.args(),self.handoff,bad,self.provenance)

    def test_nested_imported_pattern_and_application_histories_remain_separate(self):
        source=fixture.imported_fixture.PatternEvidenceReasonTests();source.setUp();source.accept()
        self.c.patterns=export_patterns(source.package,source.bundle,source.review)
        self.handoff=proposals.prepare_handoff(*self.args());self.response['handoff_sha256']=payload_sha256(self.handoff)
        self.reimport();self.accept();envelope=self.envelope()
        report=journey.inspect(*self.case.case.args(),method_applications=envelope)
        method=report['method_application_review']
        self.assertIn('proposal_review',method['pattern_review']);self.assertIn('proposal_review',method)
        for text in (methods.render(*self.args(),envelope),journey.render(*self.case.case.args(),method_applications=envelope)):
            for phrase in ('Model proposed','Reviewer supplied','Synthetic model proposed','Synthetic reviewer changed'):
                self.assertIn(phrase,text)
        self.c.patterns['review']['decisions'][0]['review_note']='Changed pattern history only.'
        with self.assertRaises(ValueError):methods.inspect(*self.args(),envelope)

    def test_standalone_proposal_text_shows_context_and_actual_target_link_uses(self):
        self.response['candidates'][0]['evidence_refs']=[self.c.review]
        self.reimport();self.accept();text=proposals.render_review(self.packet())
        self.assertIn('Existing target link',text);self.assertIn('Link applicability note:',text)
        self.assertIn('Context context_comparison:',text);self.assertIn('Context remaining_uncertainty:',text)
        self.assertIn('AFTER_REFERENCE_YEAR',text)

    def test_cli_stages_consume_envelope_and_reject_invalid_json_without_stdout(self):
        self.accept()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);paths=[]
            for name,value in zip(('package','patterns','context','links','proposal'),self.args()[:5]):
                path=root/(name+'.json');path.write_text(json.dumps(value),encoding='utf-8');paths.append(str(path))
            def command(name,extra=(),text=False):
                result=subprocess.run([sys.executable,str(ROOT/'application_proposals.py'),name,*paths,*map(str,extra),'--pattern-id','comparison'],
                    cwd=directory,capture_output=True,timeout=30)
                self.assertEqual(result.returncode,0,result.stderr)
                return result.stdout.decode() if text else json.loads(result.stdout)
            def save(name,value):
                path=root/name;path.write_text(json.dumps(value),encoding='utf-8');return path
            h=save('handoff.json',command('prepare'))
            empty=command('response-template',[h]);self.assertEqual(empty['candidates'],[])
            response=save('response.json',self.response);provenance=save('provenance.json',self.provenance)
            b=save('bundle.json',command('import',[h,response,provenance]))
            default=command('review-template',[b,'--reviewer-id','synthetic-reviewer']);self.assertEqual(default,self.review | {'decisions':[dict(candidate_id='application-candidate-1',decision='defer',review_note='Not reviewed.')]})
            r=save('review.json',self.review);self.assertIn('Original imported proposal',command('review',[b,r,'--format','text'],True))
            e=save('envelope.json',command('export',[b,r]))
            run=subprocess.run([sys.executable,str(ROOT/'method_application.py'),*paths,'--pattern-id','comparison',str(e)],capture_output=True,timeout=30)
            self.assertEqual(run.returncode,0,run.stderr);self.assertIn('proposal_review',json.loads(run.stdout))
            for bad in ('{"candidates":[],"candidates":[]}', '{"value":NaN}'):
                response.write_text(bad)
                run=subprocess.run([sys.executable,str(ROOT/'application_proposals.py'),'import',*paths,str(h),str(response),str(provenance),'--pattern-id','comparison'],capture_output=True,timeout=30)
                self.assertNotEqual(run.returncode,0);self.assertEqual(run.stdout,b'')


if __name__ == '__main__':unittest.main()
