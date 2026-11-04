"""Synthetic publication relationships, never proof of historical influence."""
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
from publication_context import template,inspect,render,for_papers,TYPES
from publication_timeline import timeline,render as render_timeline
from pattern_transfer_review import inspect as inspect_transfer,render as render_transfer
from pattern_proposals import export_reviewed
from persona import payload_sha256
from research_workflow import build

ROOT=Path(__file__).resolve().parent


class PublicationContextTests(unittest.TestCase):
    def setUp(self):
        self.case=fixture.PatternTransferTests();self.case.setUp()
        self.package=self.case.package;self.form=template(self.package,'synthetic-context-operator')
        self.ref0=dict(paper_id='synthetic-0',observation_index=0,dimension=None)
        self.ref1=dict(paper_id='synthetic-1',observation_index=0,dimension=None)
        self.row=dict(relation_id='review-context',from_paper_id='synthetic-1',to_paper_id='synthetic-0',
            relation_type='review_summary_of',rationale='Synthetic operator hypothesis of a review summary, not verified by quote matching.',
            basis_refs=[self.ref1],uncertainty=None)
        self.form['relations']=[self.row]

    def rebuilt(self,mutate):
        corpus={key:self.package['persona'][key] for key in ('author_id','version','build_id')}
        corpus['papers']=copy.deepcopy(self.package['knowledge']['papers']);mutate(corpus)
        return build(corpus)

    def rebound(self,package):
        form=template(package,'synthetic-operator');form['relations']=copy.deepcopy(self.form['relations']);return form

    def test_empty_template_and_explicit_basis_keep_review_only_status(self):
        self.assertEqual(template(self.package,'op')['relations'],[])
        empty=inspect(self.package,template(self.package,'op'))
        self.assertEqual(empty['status'],'NO_DECLARED_PUBLICATION_RELATIONS')
        report=inspect(self.package,self.form);row=report['relations'][0]
        self.assertEqual(row['claim_type'],'operator_interpretation')
        self.assertFalse(report['automatic_approval']);self.assertFalse(report['transitive_inference'])
        self.assertEqual(report['independence_assessment'],'NOT_PERFORMED')
        self.assertEqual(row['from_publication']['source_kind'],'review')
        self.assertEqual(row['basis_evidence'][0]['observation']['stance'],'challenge')
        self.assertIn('REVIEW_SUMMARY_IS_NOT_AUTOMATIC_INDEPENDENT_CORROBORATION',row['review_prompts'])
        self.assertIn('RELATIONSHIP_UNCERTAINTY_NOT_SUPPLIED',row['review_prompts'])
        self.assertIn('BASIS_NOT_SUPPLIED_FROM_BOTH_PAPERS',row['review_prompts'])
        self.assertIn('EXACT_QUOTE_MATCH_ONLY',render(report))

    def test_all_types_coexist_without_deducing_agreement_or_dependency_groups(self):
        self.form['relations']=[dict(self.row,relation_id=kind,relation_type=kind) for kind in TYPES]
        result=inspect(self.package,self.form)
        self.assertEqual(len(result['relations']),len(TYPES))
        self.assertNotIn('dependency_groups',result);self.assertNotIn('effective_support_count',result)
        self.assertTrue(all(row['status']=='DECLARED_PUBLICATION_RELATION_REQUIRES_REVIEW' for row in result['relations']))

    def test_symmetric_duplicate_rejects_but_directed_reverse_is_distinct(self):
        self.row['relation_type']='shares_material_with'
        self.form['relations'].append(dict(self.row,relation_id='reverse',from_paper_id='synthetic-0',to_paper_id='synthetic-1',basis_refs=[self.ref0]))
        with self.assertRaisesRegex(ValueError,'duplicate declared'):inspect(self.package,self.form)
        for row in self.form['relations']:row['relation_type']='challenges'
        result=inspect(self.package,self.form)
        self.assertEqual(len(result['relations']),2)
        self.assertIn('FROM_PUBLICATION_PREDATES_TARGET',result['relations'][1]['review_prompts'])

    def test_self_unknown_duplicate_identifiers_and_unsupported_fields_reject(self):
        for mutate in (lambda r:r.update(to_paper_id='synthetic-1'),lambda r:r.update(to_paper_id='unknown'),
                       lambda r:r.update(relation_type='proven_influence'),lambda r:r.update(claim_type='author_statement'),
                       lambda r:r.update(rationale=''),lambda r:r.update(uncertainty=False)):
            form=copy.deepcopy(self.form);mutate(form['relations'][0])
            with self.assertRaises(ValueError):inspect(self.package,form)
        self.form['relations'].append(copy.deepcopy(self.row))
        with self.assertRaises(ValueError):inspect(self.package,self.form)

    def test_basis_must_be_exact_nonempty_bounded_and_from_linked_papers(self):
        for mutate in (lambda r:r.update(basis_refs=[]),lambda r:r['basis_refs'].append(copy.deepcopy(r['basis_refs'][0])),
                       lambda r:r['basis_refs'][0].update(observation_index=True),
                       lambda r:r['basis_refs'][0].update(dimension='missing'),
                       lambda r:r['basis_refs'][0].update(extra='field'),
                       lambda r:r.update(basis_refs=[self.ref0]),
                       lambda r:r.update(basis_refs=[self.ref1]*33)):
            form=copy.deepcopy(self.form);mutate(form['relations'][0])
            with self.assertRaises(ValueError):inspect(self.package,form)
        def add(c):
            paper=copy.deepcopy(c['papers'][0]);paper['paper_id']='synthetic-2';c['papers'].append(paper)
        package=self.rebuilt(add);form=self.rebound(package)
        form['relations'][0]['basis_refs']=[dict(self.ref0,paper_id='synthetic-2')]
        with self.assertRaisesRegex(ValueError,'two papers'):inspect(package,form)

    def test_review_kind_direction_and_publication_year_are_not_influence_claims(self):
        self.row.update(from_paper_id='synthetic-0',to_paper_id='synthetic-1',basis_refs=[self.ref0])
        with self.assertRaisesRegex(ValueError,'labeled review'):inspect(self.package,self.form)
        self.row['relation_type']='method_extension_of'
        report=inspect(self.package,self.form)
        self.assertIn('FROM_PUBLICATION_PREDATES_TARGET',report['relations'][0]['review_prompts'])
        package=self.rebuilt(lambda c:c['papers'][1].update(year=2020))
        same=inspect(package,self.rebound(package))
        self.assertIn('SAME_PUBLICATION_YEAR_ORDER_UNRESOLVED',same['relations'][0]['review_prompts'])
        self.assertIn('not verified citations',same['boundary'])

    def test_shared_hash_and_missing_quotes_stay_explicit_without_deduplication(self):
        def mutate(c):
            c['papers'][1]['source_sha256']=c['papers'][0]['source_sha256']
            c['papers'][1]['observations'][0]['evidence_quote']=None
        package=self.rebuilt(mutate);report=inspect(package,self.rebound(package));row=report['relations'][0]
        self.assertIn('LINKED_PAPERS_SHARE_SOURCE_HASH',row['review_prompts'])
        self.assertIn('BASIS_REFERENCES_WITHOUT_STORED_QUOTES',row['review_prompts'])
        self.assertEqual(row['basis_gaps'][0]['reference'],self.ref1)
        self.assertEqual(len(report['paper_inventory']),2)
        self.assertEqual(row['semantic_validation'],'NOT_PERFORMED')

    def test_full_authorization_year_and_recorded_check_validation(self):
        for field,value in [('split','holdout'),('authorized',False),('author_id','another')]:
            package=copy.deepcopy(self.package);package['knowledge']['papers'][0][field]=value
            with self.assertRaises(ValueError):template(package,'op')
        package=self.rebuilt(lambda c:c['papers'][0].update(year=0))
        with self.assertRaises(ValueError):template(package,'op')
        for target,field in [('paper','source_verification'),('observation','evidence_verification'),('component','evidence_verification')]:
            package=copy.deepcopy(self.package);paper=package['knowledge']['papers'][1]
            record=paper if target=='paper' else paper['observations'][0] if target=='observation' else paper['observations'][0]['reasoning']['alternative_explanation']
            record[field]='SEMANTIC_APPROVAL'
            package['persona']['knowledge_papers_sha256']=payload_sha256(package['knowledge']['papers'])
            package['knowledge']['persona_payload_sha256']=payload_sha256(package['persona'])
            with self.assertRaises(ValueError):template(package,'op')

    def test_stale_bindings_and_resource_limits_reject(self):
        for key in ('persona_sha256','knowledge_papers_sha256'):
            form=copy.deepcopy(self.form);form[key]='0'*64
            with self.assertRaises(ValueError):inspect(self.package,form)
        for mutate in (lambda f:f.update(relations=[self.row]*129),lambda f:f['relations'][0].update(rationale='x'*2001),
                       lambda f:f['relations'][0].update(uncertainty='x'*2001),lambda f:f.update(operator_id='x'*129)):
            form=copy.deepcopy(self.form);mutate(form)
            with self.assertRaises(ValueError):inspect(self.package,form)

    def test_exact_selected_touching_and_outside_scopes_do_not_infer_transitive_edges(self):
        def add(c):
            for pid,year in [('synthetic-2',2022),('synthetic-3',2023)]:
                p=copy.deepcopy(c['papers'][0]);p.update(paper_id=pid,year=year,kind='research')
                for observation in p['observations']:observation['topic']='outside topic'
                c['papers'].append(p)
        package=self.rebuilt(add);form=self.rebound(package)
        for rid,left,right in [('one-sided','synthetic-2','synthetic-1'),('outside','synthetic-3','synthetic-2')]:
            form['relations'].append(dict(self.row,relation_id=rid,from_paper_id=left,to_paper_id=right,
                relation_type='method_extension_of',basis_refs=[dict(self.ref0,paper_id=left)]))
        checked=inspect(package,form);scope=for_papers(checked,['synthetic-0','synthetic-1'])
        self.assertEqual([r['relation_id'] for r in scope['relations_between_selected_papers']],['review-context'])
        self.assertEqual([r['relation_id'] for r in scope['relations_to_other_supplied_papers']],['one-sided'])
        self.assertEqual(scope['outside_selection_relation_ids'],['outside'])
        self.assertFalse(scope['transitive_inference']);self.assertFalse(scope['automatic_exclusion'])
        chronology=timeline(package,'model design',form)
        self.assertEqual(chronology['paper_count'],2)
        self.assertEqual(sum(len(y['papers']) for y in chronology['years']),2)
        self.assertEqual(chronology['publication_context_scope'],scope)
        self.assertIn('outside',render_timeline(package,'model design',form))
        absent=timeline(package,'missing topic',form)
        self.assertEqual(absent['paper_count'],0)
        self.assertEqual(len(absent['publication_context_scope']['outside_selection_relation_ids']),3)
        empty=for_papers(inspect(package,template(package,'op')),['synthetic-0','synthetic-1'])
        self.assertEqual(empty['selected_papers_without_declared_relationships'],['synthetic-0','synthetic-1'])
        self.assertEqual(empty['missing_relationship_meaning'],'NOT_DECLARED_NOT_EVIDENCE_OF_INDEPENDENCE')

    def test_context_changes_bind_reports_without_changing_existing_roles_or_decisions(self):
        args=self.case.inputs();base=inspect_transfer(*args);first=inspect_transfer(*args,self.form)
        self.assertEqual(first['selected_pattern'],base['selected_pattern'])
        self.assertEqual(first['evidence_routes'],base['evidence_routes'])
        self.assertEqual(first['context_review'],base['context_review'])
        self.assertEqual(first['trace_review_prompts'],base['trace_review_prompts'])
        chronology=timeline(self.package,'model design',self.form)
        changed=copy.deepcopy(self.form);changed['relations'][0]['rationale']='A revised operator relation explanation.'
        second=inspect_transfer(*args,changed)
        self.assertNotEqual(first['report_input_sha256'],second['report_input_sha256'])
        self.assertNotEqual(chronology['timeline_input_sha256'],timeline(self.package,'model design',changed)['timeline_input_sha256'])
        self.assertEqual(first['selected_paper_pattern_roles'],[
            dict(paper_id='synthetic-0',declared_roles=['support']),dict(paper_id='synthetic-1',declared_roles=['support','challenge'])])

    def test_paper_level_challenge_does_not_rewrite_source_stance_or_pattern_use(self):
        self.row['relation_type']='challenges'
        result=inspect_transfer(*self.case.inputs(),self.form)
        route=next(r for r in result['evidence_routes'] if r['evidence']['reference']==self.case.b)
        self.assertEqual(route['pattern_roles'],['support'])
        self.assertEqual(route['evidence']['observation']['stance'],'challenge')
        self.assertIn('paper-level challenges do not change',render_transfer(*self.case.inputs(),self.form))

    def test_relation_context_cannot_hide_future_or_same_year_publications(self):
        result=inspect_transfer(*self.case.inputs(),self.form);scope=result['publication_context_scope']
        relation=scope['relations_between_selected_papers'][0]
        self.assertEqual(scope['reference_year'],2020)
        self.assertEqual(scope['relationship_assertion_time'],'NOT_SUPPLIED')
        self.assertIn('RELATION_CONTEXT_INCLUDES_AFTER_REFERENCE_YEAR_PUBLICATION',relation['review_prompts'])
        self.assertIn('RELATION_CONTEXT_INCLUDES_UNRESOLVED_SAME_YEAR_ORDER',relation['review_prompts'])
        self.assertEqual(relation['basis_reference_scopes'][0]['publication_scope'],'AFTER_REFERENCE_YEAR')
        self.assertIn('possibly retrospective',render_transfer(*self.case.inputs(),self.form))
        with self.assertRaises(ValueError):for_papers(inspect(self.package,self.form),['synthetic-0'],True)

    def test_imported_pattern_reasons_and_rejected_model_proposals_remain(self):
        imported=imported_fixture.PatternEvidenceReasonTests();imported.setUp()
        imported.response['candidates'].append(copy.deepcopy(imported.proposal));imported.reimport();imported.accept()
        imported.review['decisions'][1].update(decision='reject',review_note='Rejected synthetic pattern retained.')
        envelope=export_reviewed(imported.package,imported.bundle,imported.review)
        args=self.case.inputs();args[1]=envelope
        form=template(imported.package,'op');form['relations']=[self.row]
        result=inspect_transfer(*args,form)
        self.assertIn('proposal_origin',result['selected_pattern'])
        self.assertEqual(len(result['pattern_proposal_review']['candidates']),2)
        self.assertIn('pattern_evidence_uses',result['evidence_routes'][0])
        text=render_transfer(*args,form)
        for phrase in ('Model proposed','Reviewer supplied','Rejected synthetic pattern retained.','synthetic-model'):
            self.assertIn(phrase,text)

    def test_imported_observation_origin_survives_relationship_basis_and_timeline(self):
        observation=observation_fixture.ObservationRevisionTests();observation.setUp();package=observation.candidate()['package']
        form=template(package,'op');form['relations']=[self.row]
        result=inspect(package,form)
        self.assertIn('observation_origin',result['relations'][0]['basis_evidence'][0]['observation'])
        self.assertIn('synthetic-model',render(result))
        self.assertIn('synthetic-model',render_timeline(package,'model design',form))

    def test_v042_no_argument_payloads_and_text_are_unchanged(self):
        # Captured from the exact published v0.42 source at 7a046e346e4307289436ecff2c6298cc5519be3a.
        expected=['afeb9cb6f912c68fa15f7347aa227a1a85ce9f8f05f5cf78fa2cbc6648d02dc1',
            'f5e0d8814b3a0b76085d0016b2865b79562f5ae9a5ba0bb6c96fd7c7d41ac070',
            'b2b50dfcee29c649b7795a09724c0b638e6cd2643616285f0bd0dc2db0111e28',
            '89efbb2e546641a0288a4c607a906b5fc76fbc7872a17247aae30dbe841c3dfa']
        values=[timeline(self.package,'model design'),render_timeline(self.package,'model design'),
                inspect_transfer(*self.case.inputs()),render_transfer(*self.case.inputs())]
        self.assertEqual([payload_sha256(value) for value in values],expected)
        empty=template(self.package,'op');result=inspect_transfer(*self.case.inputs(),empty)
        self.assertEqual(result['publication_context_review']['status'],'NO_DECLARED_PUBLICATION_RELATIONS')
        self.assertNotEqual(result['report_input_sha256'],values[2]['report_input_sha256'])
        self.assertIn('independence not established',render_transfer(*self.case.inputs(),empty))
        self.assertIn('independence not established',render_timeline(self.package,'model design',empty))

    def test_reports_detach_inputs_and_no_source_provider_or_network_execution(self):
        before=copy.deepcopy((self.package,self.form,self.case.inputs()))
        with patch('pathlib.Path.open',side_effect=AssertionError('source opened')),patch('socket.socket',side_effect=AssertionError('network used')):
            result=inspect_transfer(*self.case.inputs(),self.form)
            chronology=timeline(self.package,'model design',self.form)
        result['publication_context_review']['relations'][0]['basis_evidence'][0]['observation']['method']='changed'
        chronology['publication_context_scope']['relations_between_selected_papers'][0]['rationale']='changed'
        self.assertEqual(before,(self.package,self.form,self.case.inputs()))
        self.assertFalse(result['publication_context_review']['llm_used'])

    def test_controls_escape_unicode_preserved_and_cli_exercises_both_integrations(self):
        self.row['rationale']='합성 관계 설명\x1b[2J\nnot a command'
        text=render(inspect(self.package,self.form));self.assertIn('합성 관계 설명',text);self.assertNotIn('\x1b',text)
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory)
            def save(name,value):
                p=folder/(name+'.json');p.write_text(json.dumps(value),encoding='utf-8');return p
            paths=[save(name,value) for name,value in zip(('package','patterns','context','links','proposal','draft'),self.case.inputs()[:-1])]
            relations=save('relations',self.form);before={p.name:p.read_bytes() for p in folder.iterdir()}
            def run(script,*args,valid=True):
                completed=subprocess.run([sys.executable,str(ROOT/script),*map(str,args)],cwd=folder,capture_output=True,text=True,encoding='utf-8',timeout=30)
                if valid:self.assertEqual(completed.returncode,0,completed.stderr)
                else:self.assertNotEqual(completed.returncode,0);self.assertEqual(completed.stdout,'')
                return completed.stdout
            made=json.loads(run('publication_context.py',paths[0],'--template','--operator-id','op'));self.assertEqual(made['relations'],[])
            self.assertIn('review_summary_of',run('publication_context.py',paths[0],relations,'--format','text'))
            self.assertIn('review-context',run('publication_timeline.py',paths[0],'--topic','model design','--publication-relations',relations,'--format','text'))
            self.assertIn('review-context',run('pattern_transfer_review.py',*paths,'--pattern-id','comparison','--publication-relations',relations,'--format','text'))
            bad=folder/'bad.json';bad.write_text('{"operator_id":1,"operator_id":2}')
            run('publication_context.py',paths[0],bad,valid=False)
            run('publication_timeline.py',paths[0],'--topic','model design','--publication-relations',bad,valid=False)
            bad.write_text('{"relations":NaN}');run('publication_context.py',paths[0],bad,valid=False)
            bad.write_bytes(b' '*(8*1024*1024+1));run('publication_context.py',paths[0],bad,valid=False)
            for name,content in before.items():self.assertEqual((folder/name).read_bytes(),content)


if __name__=='__main__':unittest.main()
