"""Synthetic reviewed-observation append and downstream provenance tests."""
import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from corpus_files import load_segment_corpus, load_sources
from observation_proposals import prepare_observation_handoff, import_observation_response, review_template
from observation_revision import template, prepare_candidate, audit_candidate, encode_result
from observation_provenance import KEY, ORIGIN, content_sha256
from research_workflow import build, apply, validated_source_rules
from persona import payload_sha256
from strict_json import load
from reasoning_links import template as link_template, _sources, _endpoint
from design_scenario import template as design_template
from answer_draft import template as answer_template, inspect as inspect_answer, render as render_answer
from evidence_scope import disclose, render as render_scope
from review_package import render as render_package
from publication_timeline import timeline, render as render_timeline
from pattern_hypotheses import template as pattern_template, inspect as inspect_patterns, render as render_patterns
from pattern_proposals import prepare_handoff as pattern_handoff
from extraction_adapter import MockProvider, extract_candidates
from operator_review import review_template as reasoning_review, prepare_revision, target_inventory
from audit_design_lineage import audit as audit_reasoning
from audit_design_chain import audit as audit_chain
from curate_local import validate_manual_observation
from revise_local import template as manual_revision_template

ROOT=Path(__file__).resolve().parent


class ObservationRevisionTests(unittest.TestCase):
    def setUp(self):
        self.root=ROOT/'examples/synthetic-sources'
        self.manifest=load(ROOT/'examples/file-corpus.json')
        self.rows=[]
        for i,paper in enumerate(self.manifest['papers']):
            obs=paper['observations'][0]
            self.rows.append(dict(paper_id=paper['paper_id'],**{key:copy.deepcopy(obs[key]) for key in
                ('method','condition','limitation','topic','locator','evidence_quote')},
                proposed_claim_type=obs['claim_type'],proposed_stance='support' if i==0 else 'challenge'))
            paper['observations']=[]
        self.provenance=dict(provider_id='synthetic-provider',model_id='synthetic-model',run_id='synthetic-run',
                            operator_id='synthetic-generator',execution_location='local')
        self.rebuild()

    def rebuild(self):
        self.corpus=load_segment_corpus(self.manifest,self.root,max_total_bytes=2*1024*1024)
        self.handoff=prepare_observation_handoff(self.corpus)
        self.bundle=import_observation_response(self.corpus,self.handoff,
            dict(handoff_sha256=payload_sha256(self.handoff),candidates=self.rows),self.provenance)
        self.review=review_template(self.corpus,self.bundle,'synthetic-reviewer')
        for decision,candidate in zip(self.review['decisions'],self.bundle['candidates']):
            decision.update(decision='accept',review_note='Explicit synthetic review; semantic support not validated.',
                reviewed_observation=copy.deepcopy(candidate['proposed_observation']))
        self.card=template(self.manifest,self.bundle,self.review,self.root,'synthetic-append-operator')
        self.card.update(new_version=self.manifest['version']+'-next',new_build_id=self.manifest['build_id']+'-next')
        counts={p['paper_id']:len(p['observations']) for p in self.manifest['papers']}
        for candidate in self.bundle['candidates']:
            paper=candidate['paper_id'];self.card['operations'].append(dict(operation='append',candidate_id=candidate['candidate_id'],
                target_paper_id=paper,target_observation_index=counts[paper]));counts[paper]+=1

    def candidate(self):
        return prepare_candidate(self.manifest,self.bundle,self.review,self.card,self.root)

    def bindings(self,package,*,component=False):
        links=link_template(package,'synthetic-links')
        refs=[dict(paper_id='synthetic-0',observation_index=0,dimension=None),
              dict(paper_id='synthetic-1',observation_index=0,dimension=None)]
        links['links']=[dict(link_id='contrast',relation='contrasts',from_ref=refs[0],to_ref=refs[1],
                           rationale='Synthetic comparison only.',claim_type='operator_interpretation')]
        proposal=design_template(package,links,'Synthetic question','synthetic-design')
        proposal['steps']=[dict(step_id='inspect',proposed_action='Inspect the differing evidence.',rationale='Operator proposal only.',
            hypothesis=None,falsification_check=None,alternative_explanation=None,uncertainty=None,
            link_uses=[dict(link_id='contrast',role='constraint',applicability_note='Not validated.')])]
        draft=answer_template(package,'Synthetic question','synthetic-answer')
        citations=[dict(reference=refs[0],role='support'),dict(reference=refs[1],role='challenge')]
        if component:citations.append(dict(reference=dict(refs[0],dimension='uncertainty'),role='context'))
        draft['claims']=[dict(claim_id='tentative',text='Tentative synthetic interpretation.',claim_type='operator_synthesis',
                             uncertainty=None,citations=citations)]
        return links,proposal,draft

    def test_empty_sources_append_explicit_records_with_full_origin_and_current_checks(self):
        result=self.candidate();package=result['package']
        self.assertEqual(result['status'],'REVIEWED_OBSERVATION_APPEND_CANDIDATE')
        self.assertFalse(result['canonical_update_performed']);self.assertFalse(result['provider_invoked'])
        self.assertTrue(result['runtime_package_created'])
        self.assertEqual(len(result['append_audit']['additions']),2)
        self.assertEqual(result['append_audit']['initial_unreplayed_observation_origins'],[])
        for paper,rule in zip(package['knowledge']['papers'],package['persona']['rules']):
            obs=paper['observations'][0];origin=obs[KEY]
            self.assertEqual(rule['evidence_type'],ORIGIN);self.assertEqual(rule[KEY],origin)
            self.assertEqual(origin['import_record']['provenance'],self.provenance)
            self.assertEqual(origin['reviewed_observation_sha256'],content_sha256(obs))
            self.assertEqual(origin['adoption_card_sha256'],payload_sha256(self.card))
            self.assertEqual(paper['source_verification'],'LOCAL_BYTES_SHA256_MATCH')
            self.assertEqual(obs['evidence_verification'],'EXACT_QUOTE_MATCH_ONLY')
            self.assertNotIn('segments',paper)
        self.assertEqual([p['observations'][0]['stance'] for p in result['manifest']['papers']],['support','challenge'])
        self.assertEqual(validated_source_rules(package),package['knowledge']['papers'])

    def test_template_does_not_select_operations_or_identity(self):
        card=template(self.manifest,self.bundle,self.review,self.root,'operator')
        self.assertEqual(card['operations'],[]);self.assertEqual(card['new_version'],'');self.assertEqual(card['new_build_id'],'')
        with self.assertRaises(ValueError):prepare_candidate(self.manifest,self.bundle,self.review,card,self.root)

    def test_unresolved_or_no_accepted_reviews_cannot_create_append_card(self):
        for decision in ('defer','reject'):
            review=copy.deepcopy(self.review)
            review['decisions']=[dict(candidate_id=d['candidate_id'],decision=decision,review_note='Not accepted.') for d in review['decisions']]
            with self.assertRaises(ValueError):template(self.manifest,self.bundle,review,self.root,'op')

    def test_missing_fields_stay_missing_until_explicit_review_fills_them(self):
        self.rows[0]['condition']=None;self.rebuild()
        with self.assertRaisesRegex(ValueError,'missing fields'):self.candidate()
        self.review['decisions'][0]['reviewed_observation']['condition']='A separately reviewed synthetic condition.'
        self.card['operator_review_sha256']=payload_sha256(self.review)
        result=self.candidate()
        self.assertIsNone(result['review_packet']['candidates'][0]['candidate']['proposed_observation']['condition'])
        self.assertEqual(result['manifest']['papers'][0]['observations'][0]['condition'],'A separately reviewed synthetic condition.')

    def test_rejected_counterevidence_stays_in_packet_but_is_not_appended(self):
        self.review['decisions'][1]=dict(candidate_id=self.review['decisions'][1]['candidate_id'],decision='reject',review_note='Synthetic unsupported interpretation.')
        self.card['operator_review_sha256']=payload_sha256(self.review);self.card['operations'].pop()
        result=self.candidate()
        self.assertEqual(result['manifest']['papers'][1]['observations'],[])
        self.assertEqual(result['review_packet']['candidates'][1]['candidate']['proposed_observation']['stance'],'challenge')
        self.assertEqual(result['review_packet']['candidates'][1]['decision'],'reject')

    def test_target_operation_index_identity_and_complete_acceptance_gates(self):
        for mutate in (lambda c:c['operations'][0].update(operation='replace'),
                       lambda c:c['operations'][0].update(target_paper_id='synthetic-1'),
                       lambda c:c['operations'][0].update(target_observation_index=True),
                       lambda c:c['operations'][0].update(target_observation_index=1),
                       lambda c:c['operations'][0].update(candidate_id='unknown'),
                       lambda c:c['operations'].pop(),
                       lambda c:c['operations'].append(copy.deepcopy(c['operations'][0])),
                       lambda c:c.update(new_version=self.manifest['version']),
                       lambda c:c.update(new_build_id=self.manifest['build_id'])):
            card=copy.deepcopy(self.card);mutate(card)
            with self.assertRaises(ValueError):prepare_candidate(self.manifest,self.bundle,self.review,card,self.root)

    def test_same_paper_multiple_operations_require_explicit_sequential_indexes(self):
        self.rows.append(copy.deepcopy(self.rows[0]));self.rebuild();result=self.candidate()
        self.assertEqual(len(result['manifest']['papers'][0]['observations']),2)
        self.card['operations'][2]['target_observation_index']=0
        with self.assertRaises(ValueError):self.candidate()

    def test_stale_shape_and_authorization_reject_without_source_reads(self):
        card=copy.deepcopy(self.card);card['manifest_sha256']='0'*64
        with patch('corpus_files.read_source_bytes',side_effect=AssertionError('source opened')):
            with self.assertRaises(ValueError):prepare_candidate(self.manifest,self.bundle,self.review,card,self.root)
        manifest=copy.deepcopy(self.manifest);manifest['papers'][1]['authorized']=False
        with patch('corpus_files.read_source_bytes',side_effect=AssertionError('source opened')):
            with self.assertRaises(ValueError):template(manifest,self.bundle,self.review,self.root,'op')
        manifest=copy.deepcopy(self.manifest);manifest['private_annotation']='synthetic metadata changed'
        with self.assertRaises(ValueError):prepare_candidate(manifest,self.bundle,self.review,self.card,self.root)

    def test_changed_local_bytes_and_refreshed_hash_cannot_reuse_old_bundle(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for path in self.root.iterdir():shutil.copyfile(path,root/path.name)
            path=root/self.manifest['papers'][0]['source_file'];path.write_bytes(b'Synthetic preamble changed.\n'+path.read_bytes())
            with self.assertRaises(ValueError):prepare_candidate(self.manifest,self.bundle,self.review,self.card,root)
            import hashlib
            manifest=copy.deepcopy(self.manifest);manifest['papers'][0]['source_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
            with self.assertRaises(ValueError):template(manifest,self.bundle,self.review,root,'op')

    def test_exact_replay_rejects_tampering_even_self_consistent_package_changes(self):
        candidate=self.candidate()
        audit=audit_candidate(self.manifest,self.bundle,self.review,self.card,candidate,self.root)
        self.assertEqual(audit['status'],'OBSERVATION_APPEND_REPLAY_MATCH')
        for mutate in (lambda c:c.update(status='APPROVED'),lambda c:c['append_audit']['additions'].pop(),
                       lambda c:c['review_packet']['candidates'].pop(),
                       lambda c:c['manifest'].update(private_annotation='changed')):
            bad=copy.deepcopy(candidate);mutate(bad)
            with self.assertRaises(ValueError):audit_candidate(self.manifest,self.bundle,self.review,self.card,bad,self.root)
        bad=copy.deepcopy(candidate);obs=bad['manifest']['papers'][0]['observations'][0]
        obs['method']='A different synthetic interpretation.';obs[KEY]['reviewed_observation_sha256']=content_sha256(obs)
        bad['package']=build(load_sources(bad['manifest'],self.root))
        with self.assertRaises(ValueError):audit_candidate(self.manifest,self.bundle,self.review,self.card,bad,self.root)

    def test_origin_fields_source_binding_and_reviewed_content_are_validated(self):
        manifest=self.candidate()['manifest']
        for mutate in (lambda o:o[KEY].pop('operator_id'),lambda o:o[KEY].update(extra='unknown'),
                       lambda o:o[KEY].update(source_sha256='0'*64),lambda o:o[KEY].update(paper_id='other'),
                       lambda o:o[KEY].update(adoption_card_sha256='not a digest'),
                       lambda o:o[KEY]['import_record']['provenance'].update(execution_location='invalid'),
                       lambda o:o.update(method='Unreviewed changed text.')):
            changed=copy.deepcopy(manifest);mutate(changed['papers'][0]['observations'][0])
            with self.assertRaises(ValueError):build(changed)
        # A serialized historical status does not issue a fresh verification receipt.
        package=build(manifest)
        self.assertEqual(package['knowledge']['papers'][0]['source_verification'],'NOT_PERFORMED')
        self.assertEqual(package['persona']['rules'][0]['evidence_verification'],'NOT_PERFORMED')

    def test_rule_source_origin_mismatch_rejects_even_rebound_package_hashes(self):
        package=copy.deepcopy(self.candidate()['package']);package['persona']['rules'][0].pop(KEY)
        package['knowledge']['persona_payload_sha256']=payload_sha256(package['persona'])
        with self.assertRaisesRegex(ValueError,'do not match'):apply(package,'Question','model design')

    def test_every_base_content_field_requires_new_review_binding(self):
        manifest=self.candidate()['manifest']
        for key in ('method','condition','limitation','topic','locator','evidence_quote','claim_type','stance'):
            changed=copy.deepcopy(manifest);obs=changed['papers'][0]['observations'][0]
            obs[key]='operator_interpretation' if key=='claim_type' else 'challenge' if key=='stance' else 'Changed synthetic '+key
            with self.assertRaises(ValueError):build(changed)

    def test_origins_survive_application_trajectory_timeline_links_answers_and_patterns(self):
        package=self.candidate()['package'];application=apply(package,'Question','model design')
        self.assertIn(KEY,application['steps'][0]);self.assertIn(KEY,application['methodology_trajectory'][0]['evidence'][0])
        self.assertEqual(application['processing']['historical_model_use'],'DECLARED_NOT_AUTHENTICATED')
        chronology=timeline(package,'model design');self.assertIn(KEY,chronology['years'][0]['papers'][0]['observations'][0])
        _,papers=_sources(package);ref=dict(paper_id='synthetic-0',observation_index=0,dimension=None)
        self.assertIn(KEY,_endpoint(ref,papers)['observation'])
        links,proposal,draft=self.bindings(package)
        answer=inspect_answer(package,draft)
        self.assertIn(KEY,answer['claims'][0]['citations'][0]['evidence']['observation'])
        form=pattern_template(package,'operator');form['hypotheses']=[dict(pattern_id='comparison',operator_hypothesis='Tentative synthetic comparison.',
            scope_note='These sources only.',support_refs=[ref],challenge_refs=[dict(ref,paper_id='synthetic-1')],
            alternative_explanation=None,falsification_check=None,uncertainty=None)]
        patterns=inspect_patterns(package,form)
        self.assertIn(KEY,patterns['hypotheses'][0]['evidence'][0]['evidence']['observation'])
        handoff=pattern_handoff(package,'model design',include_evidence_reasons=True)
        self.assertIn(KEY,handoff['evidence_catalog'][0]['observation'])
        for text in (render_package(package,'Question','model design',evidence_details=True),render_timeline(package,'model design'),
                     render_answer(answer),render_patterns(patterns),render_scope(package,links,proposal,draft,2022)):
            self.assertIn('synthetic-model',text);self.assertIn(ORIGIN,text)

    def test_component_origin_is_not_confused_with_imported_observation_context(self):
        manifest=self.candidate()['manifest'];obs=manifest['papers'][0]['observations'][0]
        obs['reasoning']=dict(uncertainty=dict(text='A manually declared uncertainty.',locator=obs['locator'],
            evidence_quote=obs['evidence_quote'],claim_type='operator_interpretation'))
        package=build(load_sources(manifest,self.root));links,proposal,draft=self.bindings(package,component=True)
        result=disclose(package,links,proposal,draft,2022)
        self.assertEqual(result['coverage']['active_exact_references'],3)
        self.assertEqual(len(result['recorded_imported_observation_references']),2)
        self.assertEqual(len(result['active_references_with_imported_observation_context']),3)
        self.assertEqual(len(result['other_curated_references']),1)
        self.assertEqual(result['other_curated_references'][0]['dimension'],'uncertainty')
        self.assertEqual(result['recorded_imported_origin_references'],[])
        self.assertIn(KEY,apply(package,'Question','model design')['reasoning_cards'][0])

    def test_reasoning_revisions_preserve_base_history_without_claiming_to_replay_it(self):
        manifest=self.candidate()['manifest'];corpus=load_segment_corpus(manifest,self.root)
        obs=manifest['papers'][0]['observations'][0]
        response=[dict(paper_id='synthetic-0',locator=obs['locator'],evidence_quote=obs['evidence_quote'],
            dimension='uncertainty',candidate_text='Synthetic declared uncertainty.',proposed_claim_type='operator_interpretation')]
        bundle=extract_candidates(corpus,MockProvider(response));review=reasoning_review(corpus,bundle,'reviewer')
        review['decisions'][0].update(decision='accept',review_note='Synthetic only.',target_rule_id='rule-1',target_paper_id='synthetic-0',
            operation='add',expected_component_sha256=None,reviewed_text='Explicit synthetic uncertainty.',reviewed_claim_type='operator_interpretation')
        self.assertIn(KEY,target_inventory(corpus,bundle)['candidates'][0]['targets'][0]['observation'])
        package=prepare_revision(corpus,bundle,review,'next-reasoning','next-reasoning-build')['package']
        links,proposal,_=self.bindings(package)
        inputs=dict(original_corpus=corpus,candidate_bundle=bundle,operator_review=review)
        one=audit_reasoning(package,links,proposal,inputs)
        chain=audit_chain(package,links,proposal,dict(stages=[dict(**inputs,target_version='next-reasoning',target_build_id='next-reasoning-build')]))
        for result in (one,chain):
            self.assertEqual(result['observation_adoption_history_status'],'NOT_REPLAYED_BY_REASONING_REVISION_AUDIT')
            self.assertEqual(len(result['initial_unreplayed_observation_origins']),2)
            self.assertEqual(result['candidate_origin_coverage_scope'],'REASONING_COMPONENTS_ONLY')
            self.assertEqual(result['initial_history_status'],'UNREPLAYED_OBSERVATION_ORIGINS_PRESENT')
        self.assertEqual(one['status'],'CURRENT_REVISION_MATCH_WITH_UNREPLAYED_OBSERVATION_HISTORY')
        self.assertEqual(chain['status'],'DECLARED_CHAIN_MATCH_WITH_UNREPLAYED_HISTORY')
        endpoint=one['step_evidence_routes'][0]['uses'][0]['endpoints'][0]
        self.assertEqual(endpoint['observation_origin_audit'],'OBSERVATION_ADOPTION_NOT_REPLAYED')

    def test_repeated_append_retains_initial_history_and_explicit_positions(self):
        first=self.candidate();self.manifest=first['manifest'];self.rebuild();second=self.candidate()
        self.assertEqual(len(second['append_audit']['initial_unreplayed_observation_origins']),2)
        self.assertTrue(all(row['observation_index']==1 for row in second['append_audit']['additions']))
        self.assertEqual(second['manifest']['papers'][0]['observations'][0],first['manifest']['papers'][0]['observations'][0])
        self.assertEqual(len(second['package']['persona']['rules']),4)

    def test_manual_edit_gates_cannot_strip_imported_origin(self):
        manifest=self.candidate()['manifest'];obs=manifest['papers'][0]['observations'][0]
        with self.assertRaises(ValueError):validate_manual_observation(obs)
        with self.assertRaises(ValueError):manual_revision_template(manifest,'synthetic-0',0)

    def test_aliased_inputs_detach_and_no_provider_network_or_file_mutation(self):
        shared=[]
        for p in self.manifest['papers']:p['observations']=shared
        self.rebuild();before=copy.deepcopy((self.manifest,self.bundle,self.review,self.card))
        files={p:p.read_bytes() for p in self.root.iterdir()}
        with patch('socket.socket',side_effect=AssertionError('network used')),patch.object(MockProvider,'extract',side_effect=AssertionError('provider used')):
            result=self.candidate()
            audit_candidate(self.manifest,self.bundle,self.review,self.card,result,self.root)
        self.assertEqual([len(p['observations']) for p in result['manifest']['papers']],[1,1])
        result['manifest']['papers'][0]['observations'][0][KEY]['import_record']['provenance']['model_id']='changed'
        self.assertEqual(before,(self.manifest,self.bundle,self.review,self.card))
        self.assertEqual(files,{p:p.read_bytes() for p in self.root.iterdir()})

    def test_actual_cli_template_prepare_audit_and_downstream_render(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory)
            def save(name,value):
                p=folder/(name+'.json');p.write_text(json.dumps(value),encoding='utf-8');return p
            mp=save('manifest',self.manifest);bp=save('bundle',self.bundle);rp=save('review',self.review);cp=save('card',self.card)
            before={p.name:p.read_bytes() for p in folder.iterdir()}
            def run(script,*args,valid=True):
                completed=subprocess.run([sys.executable,str(ROOT/script),*map(str,args)],cwd=folder,capture_output=True,text=True,timeout=30)
                if valid:self.assertEqual(completed.returncode,0,completed.stderr)
                else:self.assertNotEqual(completed.returncode,0);self.assertEqual(completed.stdout,'')
                return completed.stdout
            empty=json.loads(run('observation_revision.py','template',mp,bp,rp,'--source-root',self.root,'--operator-id','op'))
            self.assertEqual(empty['operations'],[])
            candidate=json.loads(run('observation_revision.py','prepare',mp,bp,rp,cp,'--source-root',self.root))
            output=save('candidate',candidate)
            self.assertEqual(json.loads(run('observation_revision.py','audit',mp,bp,rp,cp,output,'--source-root',self.root))['status'],'OBSERVATION_APPEND_REPLAY_MATCH')
            self.assertIn('synthetic-model',run('publication_timeline.py',output,'--topic','model design','--format','text'))
            invalid=save('invalid',dict(self.card,operations=[]))
            run('observation_revision.py','prepare',mp,bp,rp,invalid,'--source-root',self.root,valid=False)
            duplicate=folder/'duplicate.json';duplicate.write_text('{"schema":1,"schema":2}')
            run('observation_revision.py','prepare',mp,bp,rp,duplicate,'--source-root',self.root,valid=False)
            for name,value in before.items():self.assertEqual((folder/name).read_bytes(),value)

    def test_output_budget_matches_replay_input_limit(self):
        result=self.candidate()
        self.assertEqual(json.loads(encode_result(result)),result)
        with patch('observation_revision.MAX_OUTPUT_BYTES',100):
            with self.assertRaisesRegex(ValueError,'8 MiB'):encode_result(result)


if __name__=='__main__':unittest.main()
