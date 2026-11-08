"""Synthetic two-card comparisons; no scientific or researcher-fidelity evaluation."""
import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import journey_compare as comparison
import journey_inputs as inputs
import research_journey as journey
import source_recheck
import test_journey_inputs as fixture
import test_application_proposals as application_fixture
import test_pattern_evidence_reasons as pattern_fixture
import test_observation_revision as observation_fixture
from pattern_proposals import export_reviewed
from persona import payload_sha256
from research_workflow import build
from answer_draft import review_template, template as answer_template
from applicability_review import template as context_template
from argument_map import template as argument_template
from corpus_files import load_sources
from design_scenario import template as design_template
from pattern_hypotheses import template as pattern_template
from publication_context import template as relation_template
from reasoning_links import template as link_template
from method_application import template as method_template

ROOT=Path(__file__).resolve().parent


class JourneyComparisonTests(unittest.TestCase):
    def setUp(self):
        self.case=fixture.JourneyInputTests();self.case.setUp();self.addCleanup(self.case.doCleanups)
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.roots=[self.case.root,Path(self.tmp.name)/'current synthetic'];shutil.copytree(self.roots[0],self.roots[1])
        self.selections=[copy.deepcopy(self.case.selection),copy.deepcopy(self.case.selection)]
    def path(self,side,name):return self.roots[side]/self.selections[side]['artifacts'][name]
    def read(self,side,name):return json.loads(self.path(side,name).read_text(encoding='utf-8'))
    def write(self,side,name,value):
        if self.selections[side]['artifacts'][name] is None:self.selections[side]['artifacts'][name]=name+'.json'
        self.path(side,name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    def card(self,side,source_root=None):return inputs.prepare(self.selections[side],self.roots[side],source_root=source_root)
    def compare(self,**kwargs):return comparison.compare(self.card(0),self.roots[0],self.card(1),self.roots[1],**kwargs)
    def group(self,result,name):return next(row for row in result['declared_record_comparison'] if row['group']==name)
    def rebind_answer(self,side):
        draft=self.read(side,'draft');review=self.read(side,'declared_review');review['draft_sha256']=payload_sha256(draft);self.write(side,'declared_review',review)
        argument=self.read(side,'argument');argument.update(draft_sha256=payload_sha256(draft),review_sha256=payload_sha256(review));self.write(side,'argument',argument)
    def sources(self,side):
        package=self.read(side,'package');selection=source_recheck.template(package,'synthetic-check')
        for row in selection['sources']:row['source_file']=row['paper_id']+'.md'
        self.write(side,'source_selection',selection)
        root=self.roots[side]/'sources';shutil.copytree(ROOT/'examples/synthetic-sources',root)
        return root

    def test_identical_cards_are_not_approval_and_both_reports_are_fresh(self):
        a=self.card(0);b=self.card(1)
        with patch.object(journey,'inspect',wraps=journey.inspect) as inspect:
            result=comparison.compare(a,self.roots[0],b,self.roots[1]);self.assertEqual(inspect.call_count,2)
        for field in ('input_card_changed','logical_journey_inputs_changed','inspected_reports_changed','automatic_approval','scientific_execution','human_review_authenticated'):
            self.assertFalse(result[field])
        self.assertEqual(result['previous_report'],inputs.inspect(a,self.roots[0]))
        self.assertEqual(result['current_report'],inputs.inspect(b,self.roots[1]))
        self.assertEqual(result['status'],'HUMAN_REVIEW_REQUIRED_NOT_RESEARCH_APPROVAL')
        self.assertTrue(all(row['status']=='UNCHANGED_AT_EXACT_REFERENCE' for row in result['exact_reference_comparison']))
        self.assertTrue(all(row['status']=='SAME_EXACT_PROMPT_COUNT' for row in result['exact_prompt_comparison']))

    def test_new_card_for_whitespace_change_separates_raw_and_logical_identity(self):
        a=self.card(0);path=self.path(1,'patterns');path.write_bytes(path.read_bytes()+b'\n')
        result=comparison.compare(a,self.roots[0],self.card(1),self.roots[1])
        row=next(row for row in result['artifact_comparison'] if row['artifact']=='patterns')
        self.assertEqual(row['status'],'RAW_BYTES_CHANGED_LOGICAL_JSON_SAME')
        self.assertTrue(result['input_card_changed']);self.assertFalse(result['logical_journey_inputs_changed'])
        self.assertTrue(result['inspected_reports_changed'])
        self.assertTrue(all(row['status']=='UNCHANGED_AT_EXACT_REFERENCE' for row in result['exact_reference_comparison']))

    def test_relative_path_change_and_root_relocation_are_distinct(self):
        self.assertFalse(self.compare()['input_card_changed'])
        old=self.path(1,'patterns');new=old.with_name('renamed-patterns.json');old.rename(new)
        self.selections[1]['artifacts']['patterns']=new.name
        result=self.compare();row=next(row for row in result['artifact_comparison'] if row['artifact']=='patterns')
        self.assertTrue(row['relative_path_changed']);self.assertEqual(row['status'],'SAME_BYTES_AND_JSON')
        self.assertFalse(result['logical_journey_inputs_changed'])
        self.assertNotIn(str(self.roots[0]),json.dumps(result));self.assertNotIn(str(self.roots[1]),json.dumps(result))

    def test_review_decision_and_note_changes_are_not_lost_in_unchanged_claims(self):
        review=self.read(1,'declared_review');review['decisions'][0].update(decision='reject',note='Synthetic replacement of a declared review, not approval.')
        self.write(1,'declared_review',review);argument=self.read(1,'argument');argument['review_sha256']=payload_sha256(review);self.write(1,'argument',argument)
        result=self.compare();claims=self.group(result,'answer_claims')['records']
        self.assertTrue(all(row['status']=='UNCHANGED_AT_DECLARED_ID' for row in claims))
        decision=self.group(result,'answer_review_decisions')['records'][0]
        self.assertEqual(set(decision['changed_fields']),{'decision','note'})
        self.assertEqual(decision['previous']['decision'],'defer');self.assertEqual(decision['current']['decision'],'reject')
        self.assertTrue(any(row['status']=='ONLY_PREVIOUS_EXACT_PROMPT_NOT_PROOF_RESOLVED' for row in result['exact_prompt_comparison']))
        self.assertFalse(result['automatic_approval'])

    def test_same_claim_id_replacement_and_argument_defeater_stay_declared_changes(self):
        draft=self.read(1,'draft');draft['claims'][0]['text']='Different synthetic statement under the same declared ID.';self.write(1,'draft',draft);self.rebind_answer(1)
        argument=self.read(1,'argument');argument['steps'][0]['defeater']='Synthetic unresolved challenge.';self.write(1,'argument',argument)
        result=self.compare();claim=self.group(result,'answer_claims')['records'][0]
        self.assertEqual(claim['status'],'CHANGED_AT_DECLARED_ID');self.assertEqual(claim['changed_fields'],['text'])
        self.assertEqual(self.group(result,'argument_steps')['records'][0]['changed_fields'],['defeater'])
        self.assertEqual(result['exact_key_correspondence'],'NOT_STABLE_SEMANTIC_IDENTITY')
        conclusion=result['current_report']['argument_review']['steps'][0]['conclusion'];self.assertEqual(conclusion['direct_citation_count'],0)

    def test_changed_design_method_and_relationship_reasons_have_separate_groups(self):
        proposal=self.read(1,'proposal');proposal['steps'][0]['rationale']='Changed synthetic design rationale.';self.write(1,'proposal',proposal)
        relations=self.read(1,'publication_relations');relations['relations'][0]['uncertainty']='Relationship unverified.';self.write(1,'publication_relations',relations)
        for side in (0,1):
            form=method_template(*[self.read(side,name) for name in ('package','patterns','context','links','proposal')],'comparison','synthetic-operator')
            if side==1:form['applications'][0]['application_rationale']='Deferred, with a supplied synthetic reason.'
            self.write(side,'method_applications',form)
        result=self.compare()
        for name,field in [('design_steps','rationale'),('publication_relationships','uncertainty'),('method_applications','application_rationale')]:
            self.assertIn(field,self.group(result,name)['records'][0]['changed_fields'])
        self.assertEqual(self.group(result,'method_applications')['records'][0]['current']['decision'],'defer')

    def test_question_topic_year_and_pattern_switch_are_not_assumed_equivalent(self):
        context=self.read(1,'context');context.update(question='A different synthetic question',reference_year=2025,target_context='Different synthetic target')
        context['context_sha256']=context_template(self.read(1,'package'),*[context[k] for k in ('question','target_context','topic','reference_year','operator_id')])['context_sha256']
        self.write(1,'context',context)
        for name in ('proposal','draft'):
            value=self.read(1,name);value['question']=context['question'];self.write(1,name,value)
        self.rebind_answer(1)
        patterns=self.read(1,'patterns');patterns['hypotheses'][0]['pattern_id']='other-comparison';self.write(1,'patterns',patterns);self.selections[1]['pattern_id']='other-comparison'
        result=self.compare();changed={row['field'] for row in result['context_comparison'] if row['changed']}
        self.assertEqual(changed,{'question','reference_year','selected_pattern_id','target_context'})
        self.assertTrue(any('publication_scope' in row['changed_route_fields'] for row in result['exact_reference_comparison']))
        patterns=self.group(result,'selected_pattern_text')['records'];self.assertEqual({row['status'] for row in patterns},{'ONLY_PREVIOUS_DECLARATION','ONLY_CURRENT_DECLARATION'})

    def test_optional_review_presence_is_not_inherited_in_either_direction(self):
        self.selections[1]['artifacts']['declared_review']=None
        argument=self.read(1,'argument');argument['review_sha256']=None;self.write(1,'argument',argument)
        old,new=self.card(0),self.card(1)
        result=comparison.compare(old,self.roots[0],new,self.roots[1])
        self.assertEqual(result['current_report']['answer_review_status'],'NOT_SUPPLIED')
        self.assertTrue(all(row['status']=='ONLY_PREVIOUS_DECLARATION' for row in self.group(result,'answer_review_decisions')['records']))
        reverse=comparison.compare(new,self.roots[1],old,self.roots[0])
        self.assertTrue(all(row['status']=='ONLY_CURRENT_DECLARATION' for row in self.group(reverse,'answer_review_decisions')['records']))

    def test_route_union_removal_does_not_claim_source_deletion_or_promote_parent(self):
        context=self.read(1,'context');context['topic']='another exact topic';context['assessments']=[]
        context['context_sha256']=context_template(self.read(1,'package'),*[context[k] for k in ('question','target_context','topic','reference_year','operator_id')])['context_sha256']
        self.write(1,'context',context)
        patterns=self.read(1,'patterns');patterns['hypotheses'][0]['support_refs']=[self.case.case.case.a];patterns['hypotheses'][0]['challenge_refs']=[];self.write(1,'patterns',patterns)
        result=self.compare();removed=[row for row in result['exact_reference_comparison'] if row['status']=='ONLY_PREVIOUS_ROUTE']
        self.assertTrue(removed);self.assertTrue(any(row['reference']['dimension'] is not None for row in removed))
        row=next(row for row in result['artifact_comparison'] if row['artifact']=='package');self.assertEqual(row['status'],'SAME_BYTES_AND_JSON')
        self.assertEqual(result['route_scope'],'SUPPLIED_ROUTE_UNION_NOT_ALL_CHANGED_EVIDENCE_OR_LITERATURE')
        reverse=comparison.compare(self.card(1),self.roots[1],self.card(0),self.roots[0])
        added=[row for row in reverse['exact_reference_comparison'] if row['status']=='ONLY_CURRENT_ROUTE']
        self.assertEqual([row['reference'] for row in added],[row['reference'] for row in removed])

    def test_declaration_addition_removal_and_order_changes_are_exact_not_semantic(self):
        draft=self.read(1,'draft');draft['claims'].append(dict(claim_id='new-claim',text='Another synthetic unresolved claim.',claim_type='operator_synthesis',uncertainty=None,citations=[]))
        self.write(1,'draft',draft);review=review_template(self.read(1,'package'),draft,'synthetic-reviewer');self.write(1,'declared_review',review);self.rebind_answer(1)
        result=self.compare();row=next(row for row in self.group(result,'answer_claims')['records'] if row['declared_id']=='new-claim')
        self.assertEqual(row['status'],'ONLY_CURRENT_DECLARATION');self.assertIsNone(row['previous'])
        reverse=comparison.compare(self.card(1),self.roots[1],self.card(0),self.roots[0])
        row=next(row for row in self.group(reverse,'answer_claims')['records'] if row['declared_id']=='new-claim');self.assertEqual(row['status'],'ONLY_PREVIOUS_DECLARATION')
        draft=self.read(0,'draft');draft['claims'].reverse();self.write(1,'draft',draft)
        self.write(1,'declared_review',review_template(self.read(1,'package'),draft,'synthetic-reviewer'));self.rebind_answer(1)
        group=self.group(self.compare(),'answer_claims')
        self.assertTrue(group['order_changed']);self.assertTrue(all(row['status']=='UNCHANGED_AT_DECLARED_ID' for row in group['records']))

    def test_prompt_multiset_preserves_duplicates_targets_and_ignores_order(self):
        a=dict(domain='argument',code='MISSING',claim_id='first');b=dict(a,claim_id='second')
        same=comparison._prompts([a,b,a],[a,a,b]);self.assertTrue(all(row['status']=='SAME_EXACT_PROMPT_COUNT' for row in same))
        different=comparison._prompts([a,a,b],[a,dict(a,claim_id='third')])
        by_target={row['prompt']['claim_id']:row for row in different}
        self.assertEqual((by_target['first']['previous_count'],by_target['first']['current_count']),(2,1))
        self.assertEqual(by_target['second']['status'],'ONLY_PREVIOUS_EXACT_PROMPT_NOT_PROOF_RESOLVED')
        self.assertEqual(by_target['third']['status'],'ONLY_CURRENT_EXACT_PROMPT')

    def test_current_card_bytes_checked_before_any_previous_source_audit(self):
        source=self.sources(0);old=self.card(0,source);new=self.card(1)
        path=self.path(1,'declared_review');path.write_bytes(path.read_bytes()+b'\n')
        with patch.object(source_recheck,'audit',side_effect=AssertionError('no source audit')) as audit:
            with self.assertRaisesRegex(ValueError,'artifact bytes changed'):comparison.compare(old,self.roots[0],new,self.roots[1],previous_source_root=source)
            audit.assert_not_called()

    def test_sources_are_separate_current_reads_once_per_selected_side(self):
        roots=[self.sources(0),self.sources(1)];cards=[self.card(side,roots[side]) for side in (0,1)]
        with patch.object(source_recheck,'audit',wraps=source_recheck.audit) as audit,patch.object(journey,'inspect',wraps=journey.inspect) as inspect:
            text=comparison.render(cards[0],self.roots[0],cards[1],self.roots[1],previous_source_root=roots[0],current_source_root=roots[1],format='text')
            self.assertEqual(audit.call_count,2);self.assertEqual(inspect.call_count,2)
        self.assertIn('BOTH_ARE_CURRENT_READS_NOT_HISTORICAL_SNAPSHOTS',text)
        self.assertIn('LOCAL_BYTES_AND_STORED_QUOTES_MATCH_NOT_VALIDATION',text)
        path=roots[1]/'synthetic-0.md';path.write_bytes(path.read_bytes()+b'Changed synthetic bytes.')
        with self.assertRaisesRegex(ValueError,'bound package hash'):comparison.compare(cards[0],self.roots[0],cards[1],self.roots[1],previous_source_root=roots[0],current_source_root=roots[1])

    def test_one_sided_source_check_and_root_pairing_are_explicit(self):
        source=self.sources(0);old=self.card(0,source);new=self.card(1)
        with patch.object(source_recheck,'audit',wraps=source_recheck.audit) as audit:
            result=comparison.compare(old,self.roots[0],new,self.roots[1],previous_source_root=source);self.assertEqual(audit.call_count,1)
        self.assertTrue(result['source_recheck_scope']['previous']);self.assertFalse(result['source_recheck_scope']['current'])
        for options in ({},{'previous_source_root':source,'current_source_root':source}):
            with patch.object(source_recheck,'audit',side_effect=AssertionError('no source audit')):
                with self.assertRaisesRegex(ValueError,'together'):comparison.compare(old,self.roots[0],new,self.roots[1],**options)

    def test_stale_forms_and_cached_reports_do_not_become_comparison_input(self):
        old=self.card(0);new=self.card(1)
        report=inputs.inspect(old,self.roots[0])
        with self.assertRaises(ValueError):comparison.compare(report,self.roots[0],new,self.roots[1])
        argument=self.read(1,'argument');argument['review_sha256']='0'*64;self.write(1,'argument',argument)
        with patch.object(journey,'inspect',return_value={}):forged=self.card(1)
        with self.assertRaisesRegex(ValueError,'different draft or declared review'):comparison.compare(old,self.roots[0],forged,self.roots[1])

    def replace_package_fixture(self,side,corpus):
        # Explicit synthetic fixture construction, never production auto-rebinding.
        package=build(load_sources(corpus,ROOT/'examples/synthetic-sources'))
        prior={name:self.read(side,name) for name in inputs.REQUIRED if name!='package'}
        links=link_template(package,prior['links']['operator_id']);links['links']=prior['links']['links']
        patterns=pattern_template(package,prior['patterns']['operator_id']);patterns['hypotheses']=prior['patterns']['hypotheses']
        old=prior['context'];context=context_template(package,*[old[k] for k in ('question','target_context','topic','reference_year','operator_id')])
        indexed={payload_sha256(row['reference']):row for row in old['assessments']}
        context['assessments']=[indexed.get(payload_sha256(row['reference']),row) for row in context['assessments']]
        proposal=design_template(package,links,prior['proposal']['question'],prior['proposal']['operator_id']);proposal['steps']=prior['proposal']['steps']
        draft=answer_template(package,prior['draft']['question'],prior['draft']['operator_id']);draft['claims']=prior['draft']['claims']
        old_review=self.read(side,'declared_review');review=review_template(package,draft,old_review['reviewer_id']);review['decisions']=old_review['decisions']
        argument=argument_template(package,draft,prior['argument']['operator_id'],review);argument['steps']=prior['argument']['steps']
        relations=relation_template(package,prior['publication_relations']['operator_id']);relations['relations']=prior['publication_relations']['relations']
        for name,value in [('package',package),('patterns',patterns),('context',context),('links',links),('proposal',proposal),('draft',draft),('declared_review',review),('argument',argument),('publication_relations',relations)]:self.write(side,name,value)

    def corpus(self,side):
        package=self.read(side,'package')
        return dict(author_id=package['persona']['author_id'],version='synthetic-next',build_id='synthetic-next',papers=copy.deepcopy(package['knowledge']['papers']))

    def test_identity_mismatch_rejected_before_either_journey_inspection(self):
        corpus=self.corpus(1);corpus['author_id']='another-synthetic-scholar'
        for paper in corpus['papers']:paper['author_id']=corpus['author_id']
        self.replace_package_fixture(1,corpus);old,new=self.card(0),self.card(1)
        with patch.object(journey,'inspect',side_effect=AssertionError('no inspect')):
            with self.assertRaisesRegex(ValueError,'same declared scholarly identity'):comparison.compare(old,self.roots[0],new,self.roots[1])

    def test_changed_resolved_source_does_not_falsely_change_claim_declarations(self):
        corpus=self.corpus(1);corpus['papers'][0]['observations'][0]['method']='Replaced synthetic observation under the same index.'
        self.replace_package_fixture(1,corpus);result=self.compare()
        route=next(row for row in result['exact_reference_comparison'] if row['reference']==self.case.case.case.a)
        self.assertEqual(route['status'],'CHANGED_AT_EXACT_REFERENCE');self.assertIn('observation',route['changed_evidence_fields'])
        self.assertTrue(all(row['status']=='UNCHANGED_AT_DECLARED_ID' for row in self.group(result,'answer_claims')['records']))
        self.assertTrue(all(row['status']=='UNCHANGED_AT_DECLARED_ID' for row in self.group(result,'argument_steps')['records']))
        self.assertNotEqual(result['previous_report']['argument_review']['answer']['claims'],result['current_report']['argument_review']['answer']['claims'])

    def test_observation_reordering_is_changed_index_correspondence_not_change_of_mind(self):
        corpus=self.corpus(0);copy_record=copy.deepcopy(corpus['papers'][0]['observations'][0]);copy_record['method']='Second synthetic record.'
        corpus['papers'][0]['observations'].append(copy_record)
        self.replace_package_fixture(0,corpus);corpus['papers'][0]['observations'].reverse();self.replace_package_fixture(1,corpus)
        result=self.compare();rows=[row for row in result['exact_reference_comparison'] if row['reference']['paper_id']=='synthetic-0']
        self.assertEqual(len(rows),2);self.assertTrue(all(row['status']=='CHANGED_AT_EXACT_REFERENCE' for row in rows))
        self.assertEqual(result['semantic_comparison'],'NOT_PERFORMED');self.assertIn('reordering',result['boundary'])

    def test_imported_pattern_and_application_histories_survive_both_formats(self):
        c=pattern_fixture.PatternEvidenceReasonTests();c.setUp();c.accept()
        patterns=export_reviewed(c.package,c.bundle,c.review)
        for side in (0,1):self.write(side,'patterns',patterns)
        # Independent application fixture is bound to the original manual pattern.
        # Test each provenance family without changing its bindings implicitly.
        result=self.compare();self.assertIn('pattern_proposal_review',result['previous_report']['pattern_transfer_review'])
        text=comparison.render(self.card(0),self.roots[0],self.card(1),self.roots[1],format='text')
        self.assertIn('Model proposed',text);self.assertIn('Reviewer supplied',text)
        for side in (0,1):self.write(side,'patterns',self.case.case.case.patterns)
        app=application_fixture.ApplicationProposalTests();app.setUp();app.response['candidates'].append(dict(app.candidate,application_rationale='Rejected synthetic application.'))
        app.reimport();app.accept();app.review['decisions'][1].update(decision='reject',review_note='Explicit synthetic rejection.')
        for side in (0,1):self.write(side,'method_applications',app.envelope())
        result=self.compare();self.assertIn('proposal_review',result['current_report']['method_application_review'])
        text=comparison.render(self.card(0),self.roots[0],self.card(1),self.roots[1],format='text')
        self.assertIn('Rejected synthetic application.',text);self.assertIn('Synthetic reviewer changed',text)

    def test_imported_observation_history_is_preserved_without_claiming_replay(self):
        f=observation_fixture.ObservationRevisionTests();f.setUp();package=f.candidate()['package']
        links,proposal,draft=f.bindings(package);review=review_template(package,draft,'synthetic-reviewer')
        argument=argument_template(package,draft,'synthetic-map',review)
        patterns=pattern_template(package,'synthetic-pattern');a=dict(paper_id='synthetic-0',observation_index=0,dimension=None)
        b=dict(a,paper_id='synthetic-1');patterns['hypotheses']=[dict(pattern_id='comparison',operator_hypothesis='Synthetic comparison.',
            scope_note='Synthetic sources only.',support_refs=[a],challenge_refs=[b],alternative_explanation=None,falsification_check=None,uncertainty=None)]
        context=context_template(package,draft['question'],'Synthetic target','model design',2020,'synthetic-context')
        relations=relation_template(package,'synthetic-relations')
        for side in (0,1):
            for name,value in [('package',package),('patterns',patterns),('context',context),('links',links),('proposal',proposal),('draft',draft),('declared_review',review),('argument',argument),('publication_relations',relations)]:self.write(side,name,value)
        result=self.compare()
        for report in (result['previous_report'],result['current_report']):
            self.assertEqual(len(report['evidence_scope']['recorded_imported_observations']),2)
            self.assertTrue(all('observation_origin' in row['evidence']['observation'] for row in report['evidence_routes']))
            self.assertEqual(report['provenance_history_replay'],'NOT_PERFORMED')
        text=comparison.render(self.card(0),self.roots[0],self.card(1),self.roots[1],format='text')
        self.assertIn('observation_origin',text);self.assertIn('NOT_PERFORMED',text)

    def test_text_has_its_own_final_combined_budget_without_truncating_reports(self):
        old,new=self.card(0),self.card(1)
        raw=comparison.render(old,self.roots[0],new,self.roots[1],format='json')
        with patch.object(comparison,'MAX_OUTPUT_BYTES',len(raw.encode('utf-8'))):
            with self.assertRaisesRegex(ValueError,'text journey comparison'):comparison.render(old,self.roots[0],new,self.roots[1],format='text')

    def test_no_mutation_network_writes_or_partial_output_on_budget_error(self):
        old,new=self.card(0),self.card(1);before=copy.deepcopy([old,new])
        files={str(path):path.read_bytes() for root in self.roots for path in root.iterdir() if path.is_file()}
        with patch('socket.socket',side_effect=AssertionError('no network')):
            result=comparison.compare(old,self.roots[0],new,self.roots[1])
        result['previous_report']['review_agenda'].clear();result['declared_record_comparison'][0]['records'][0]['previous']['text']='mutated return'
        self.assertEqual([old,new],before);self.assertEqual(files,{name:Path(name).read_bytes() for name in files})
        with patch.object(comparison,'MAX_OUTPUT_BYTES',10):
            with self.assertRaisesRegex(ValueError,'16 MiB'):comparison.compare(old,self.roots[0],new,self.roots[1])
        with self.assertRaises(ValueError):comparison.render(old,self.roots[0],new,self.roots[1],format='html')

    def test_text_escapes_control_characters_and_keeps_complete_json(self):
        draft=self.read(1,'draft');draft['claims'][0]['text']='Synthetic <script> text\u202e';self.write(1,'draft',draft);self.rebind_answer(1)
        old,new=self.card(0),self.card(1);text=comparison.render(old,self.roots[0],new,self.roots[1],format='text')
        self.assertNotIn('\u202e',text);self.assertIn('\\u202e',text)
        marker='Complete comparison including both fresh reports and all preserved histories:\n'
        result=json.loads(text.split(marker,1)[1]);self.assertEqual(result,comparison.compare(old,self.roots[0],new,self.roots[1]))

    def test_actual_cli_unicode_paths_json_text_and_strict_failure_without_stdout(self):
        cards=[]
        for side in (0,1):
            path=self.roots[side]/'입력 card.json';path.write_text(json.dumps(self.card(side)),encoding='utf-8');cards.append(path)
        command=[sys.executable,str(ROOT/'journey_compare.py'),str(cards[0]),str(cards[1]),'--previous-root',str(self.roots[0]),'--current-root',str(self.roots[1])]
        run=subprocess.run(command,cwd=self.tmp.name,capture_output=True,timeout=30)
        self.assertEqual(run.returncode,0,run.stderr);self.assertEqual(json.loads(run.stdout)['schema'],'persona.journey-comparison.v1')
        run=subprocess.run(command+['--format','text'],capture_output=True,timeout=30);self.assertEqual(run.returncode,0,run.stderr)
        self.assertIn(b'Complete comparison',run.stdout)
        cards[1].write_bytes(b'{"schema":"a","schema":"b"}')
        run=subprocess.run(command,capture_output=True,timeout=30);self.assertNotEqual(run.returncode,0);self.assertEqual(run.stdout,b'')


if __name__=='__main__':unittest.main()
