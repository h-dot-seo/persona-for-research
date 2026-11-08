"""Invented offline argument candidates, never researcher data or provider calls."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import argument_proposals as p
import argument_map
import answer_draft
import test_argument_map as fixture
import test_answer_proposals as answer_fixture
import answer_proposals
from persona import payload_sha256

ROOT = Path(__file__).resolve().parent


class ArgumentProposalTests(unittest.TestCase):
    def setUp(self):
        case = fixture.ArgumentMapTests(); case.setUp()
        self.package, self.draft = case.package, case.draft
        self.candidate = {k: copy.deepcopy(v) for k, v in case.map['steps'][0].items() if k != 'step_id'}
        self.provenance = dict(provider_id='synthetic-provider', model_id='synthetic-model', run_id='synthetic-run',
            operator_id='synthetic-importer', execution_location='unknown')
        self.declared = None
        self.reset()

    def reset(self):
        self.scope = p.template(self.package, self.draft, 'synthetic-operator', self.declared)
        self.scope['selected_claim_ids'] = [c['claim_id'] for c in answer_draft.inspect(self.package, self.draft)['claims']]
        self.handoff = p.prepare_handoff(self.package, self.draft, self.scope, self.declared)
        self.response = p.response_template(self.package, self.draft, self.scope, self.handoff, self.declared)
        self.response['candidates'] = [copy.deepcopy(self.candidate)]
        self.reimport()

    def reimport(self):
        self.bundle = p.import_response(self.package, self.draft, self.scope, self.handoff, self.response, self.provenance, self.declared)
        self.review = p.review_template(self.package, self.draft, self.bundle, 'synthetic-reviewer', self.declared)

    def accept(self, index=0, step_id='explicit-step'):
        self.review['decisions'][index].update(decision='accept', review_note='Synthetic explicit adoption '+step_id,
            reviewed_step=dict(copy.deepcopy(self.response['candidates'][index]), step_id=step_id))

    def packet(self): return p.review_proposals(self.package, self.draft, self.bundle, self.review, self.declared)
    def envelope(self): return p.export_reviewed(self.package, self.draft, self.bundle, self.review, self.declared)
    def inspect(self): return p.inspect_reviewed(self.package, self.draft, self.envelope(), self.declared)

    def test_empty_scope_selection_and_canonical_wrapper(self):
        empty = p.template(self.package, self.draft, 'op')
        self.assertEqual(empty['selected_claim_ids'], [])
        with self.assertRaisesRegex(ValueError, 'explicit selected'): p.prepare_handoff(self.package, self.draft, empty)
        wrapper = dict(package=self.package, cached_summary='untrusted')
        self.assertEqual(p.template(wrapper, self.draft, 'op'), empty)
        self.assertEqual(p.prepare_handoff(wrapper, self.draft, self.scope), self.handoff)
        self.assertEqual(p.validate_bundle(wrapper, self.draft, self.bundle), self.bundle)
        self.accept(); self.assertEqual(p.inspect_reviewed(wrapper, self.draft, self.envelope()), self.inspect())
        for selected in (['q1','q1'], ['absent'], ['q1']*65, [''], [True], [], 'q1'):
            with self.assertRaises(ValueError): p.prepare_handoff(self.package, self.draft, dict(self.scope, selected_claim_ids=selected))
        self.assertEqual(set(self.handoff['response_contract']['candidate_fields']), p.PROPOSAL_FIELDS)
        self.assertTrue(all(c['declared_review_decision']=='NOT_SUPPLIED' for c in self.handoff['selected_claims']))
        self.assertIn('NOT_COMPLETE', self.handoff['context_scope'])
        self.assertNotIn('proposal_review', self.handoff)

    def test_default_review_and_empty_response(self):
        self.assertEqual(self.review['decisions'][0]['decision'], 'defer')
        row = self.packet()['candidates'][0]
        self.assertNotIn('step_id', row['original_inspection'])
        self.assertIsNone(row['reviewed_step'])
        self.assertIn('defeater', row['original_inspection']['missing_fields'])
        with self.assertRaisesRegex(ValueError, 'resolve every'): self.envelope()
        self.response['candidates'] = []; self.reimport()
        self.assertEqual(self.packet()['status'], 'NO_ACCEPTED_ARGUMENT_PROPOSALS')
        with self.assertRaises(ValueError): self.envelope()

    def test_exact_candidate_fields_and_bounds(self):
        for change in ({'step_id':'model'}, {'decision':'accept'}, {'bridge_rationale':'x'*2001},
                       {'bridge_rationale':' '}, {'defeater':'x'*2001}, {'assumptions':['x'*2001]},
                       {'assumptions':[str(i) for i in range(33)]}, {'premise_claim_ids':['q1']*65}):
            self.response['candidates'] = [dict(self.candidate, **change)]
            with self.assertRaises(ValueError): self.reimport()
        for key in p.PROPOSAL_FIELDS:
            value=copy.deepcopy(self.candidate); del value[key]; self.response['candidates']=[value]
            with self.assertRaises(ValueError): self.reimport()
        self.response['candidates']=[self.candidate]*33
        with self.assertRaises(ValueError): self.reimport()

    def test_endpoints_both_original_and_reviewed(self):
        for change in ({'premise_claim_ids':['absent']}, {'conclusion_claim_id':'absent'},
                       {'conclusion_claim_id':'q1'}, {'premise_claim_ids':['q1','q1']},
                       {'premise_claim_ids':['conclusion']}, {'premise_claim_ids':[]}):
            self.response['candidates']=[dict(self.candidate, **change)]
            with self.assertRaises(ValueError): self.reimport()
            self.response['candidates']=[copy.deepcopy(self.candidate)]; self.reimport(); self.accept()
            self.review['decisions'][0]['reviewed_step'].update(change)
            with self.assertRaises(ValueError): self.packet()
        # An existing but unselected endpoint is also forbidden.
        self.scope['selected_claim_ids']=['q1','conclusion']
        self.handoff=p.prepare_handoff(self.package,self.draft,self.scope)
        self.response=p.response_template(self.package,self.draft,self.scope,self.handoff)
        self.response['candidates']=[copy.deepcopy(self.candidate)]
        with self.assertRaisesRegex(ValueError,'selected claim'):self.reimport()
        self.response['candidates'][0]['premise_claim_ids']=['q1'];self.reimport();self.accept()
        self.review['decisions'][0]['reviewed_step']['premise_claim_ids']=['s1']
        with self.assertRaisesRegex(ValueError,'selected claim'):self.packet()

    def test_complete_review_and_unique_explicit_steps(self):
        self.review['decisions'][0]['decision']='accept'
        with self.assertRaises(ValueError):self.packet()
        self.accept();del self.review['decisions'][0]['reviewed_step']['defeater']
        with self.assertRaises(ValueError):self.packet()
        self.accept();self.review['decisions'][0]['decision']='reject'
        with self.assertRaises(ValueError):self.packet()
        self.response['candidates']*=2;self.reimport();self.accept(0);self.accept(1)
        with self.assertRaisesRegex(ValueError,'unique'):self.packet()
        self.accept(1,'second');self.assertEqual(self.packet()['accepted_count'],2)
        self.review['decisions'][1]['candidate_id']=self.review['decisions'][0]['candidate_id']
        with self.assertRaises(ValueError):self.packet()
        self.review['decisions']=[]
        with self.assertRaises(ValueError):self.packet()

    def test_joint_cycles_only_accepted_projection(self):
        back=dict(self.candidate,premise_claim_ids=['conclusion'],conclusion_claim_id='s1')
        self.response['candidates'].append(back);self.reimport()
        self.assertEqual(self.packet()['deferred_count'],2)
        self.accept(0);self.accept(1,'back')
        with self.assertRaisesRegex(ValueError,'circular'):self.packet()
        self.review['decisions'][1]=dict(candidate_id='argument-candidate-2',decision='reject',review_note='Rejected circular alternative.')
        result=self.inspect();self.assertEqual(len(result['steps']),1)
        self.assertEqual(result['proposal_review']['candidates'][1]['original_inspection']['conclusion_claim_id'],'s1')
        self.assertIn('Rejected circular alternative.',p.render_review(result['proposal_review']))

    def test_order_and_correct_origin_survive_topological_sort(self):
        self.response['candidates'][0]['premise_claim_ids']=['s1']
        self.response['candidates'].append(dict(self.candidate,premise_claim_ids=['q1'],conclusion_claim_id='s1',bridge_rationale='Early original bridge.'))
        self.reimport();self.accept(0,'late');self.accept(1,'early')
        self.review['decisions'][0]['reviewed_step']['bridge_rationale']='Late revised bridge.'
        self.review['decisions'].reverse()
        result=self.inspect()
        self.assertEqual(result['declared_step_ids'],['late','early'])
        self.assertEqual([s['step_id'] for s in result['steps']],['early','late'])
        self.assertEqual(result['steps'][0]['proposal_origin']['candidate_id'],'argument-candidate-2')
        self.assertEqual(result['steps'][1]['proposal_origin']['original_proposal']['bridge_rationale'],self.candidate['bridge_rationale'])
        self.assertEqual(result['argument_map_sha256'],payload_sha256(self.envelope()))
        plain=argument_map.template(self.package,self.draft,'synthetic-reviewer')
        plain['steps']=[self.review['decisions'][1]['reviewed_step'],self.review['decisions'][0]['reviewed_step']]
        self.assertEqual(result['argument_content_sha256'],payload_sha256(plain))
        self.assertFalse(result['llm_used']);self.assertIsNone(result['provider']['llm_used'])
        self.assertEqual(result['historical_model_use'],'DECLARED_NOT_AUTHENTICATED')
        self.assertEqual(result['execution_scope'],'CURRENT_INSPECTION_ONLY')
        self.assertEqual(result['logical_validation'],'NOT_PERFORMED')
        self.assertTrue(result['human_review_required'])
        text=p.render_review(result['proposal_review'])
        for value in ('Late revised bridge.','Early original bridge.','not necessarily operator-authored','candidate decision=accept'):
            self.assertIn(value,text)

    def test_explicit_answer_review_presence_and_history_binding(self):
        self.accept();envelope=self.envelope()
        declared=answer_draft.review_template(self.package,self.draft,'answer-reviewer')
        with self.assertRaises(ValueError):p.inspect_reviewed(self.package,self.draft,envelope,declared)
        self.declared=declared;self.declared['decisions'][0].update(decision='reject',note='Rejected quote interpretation.')
        self.reset();self.accept();envelope=self.envelope()
        self.assertEqual(self.handoff['selected_claims'][0]['declared_review_decision'],'reject')
        self.assertEqual(self.inspect()['steps'][0]['premises'][0]['declared_review_decision'],'reject')
        with self.assertRaises(ValueError):p.inspect_reviewed(self.package,self.draft,envelope)
        self.declared['decisions'][0]['note']+='Changed.'
        with self.assertRaises(ValueError):self.inspect()

    def test_imported_answer_rejected_history_bound_not_embedded(self):
        case=answer_fixture.AnswerProposalTests();case.setUp()
        case.response['candidates']=[copy.deepcopy(case.candidate),dict(case.candidate,text='Synthetic rejected answer history.')]
        case.reimport();case.accept(0,'a')
        case.review['decisions'][1].update(decision='reject',review_note='Synthetic rejection.')
        self.package=case.package;self.draft=case.envelope()
        # Add a second adopted claim so a legal relation is possible.
        case.response['candidates'].append(dict(case.candidate,text='Synthetic second adopted claim.'));case.reimport()
        case.accept(0,'a');case.accept(2,'b');case.review['decisions'][1].update(decision='reject',review_note='Synthetic rejection.')
        self.draft=case.envelope();self.candidate=dict(premise_claim_ids=['a'],conclusion_claim_id='b',bridge_rationale='Tentative synthetic relation.',assumptions=[],defeater=None)
        self.reset();self.accept();envelope=self.envelope();result=self.inspect()
        self.assertNotIn('Synthetic rejected answer history.',json.dumps(self.handoff))
        self.assertIn('Synthetic rejected answer history.',json.dumps(result['answer']))
        self.assertIn('imported_answer_origin',self.handoff['selected_claims'][0])
        case.response['candidates'][1]['text']='Changed rejected answer history.';case.reimport();case.accept(0,'a');case.accept(2,'b')
        case.review['decisions'][1].update(decision='reject',review_note='Synthetic rejection.')
        changed=case.envelope()
        with self.assertRaises(ValueError):p.inspect_reviewed(self.package,changed,envelope)

    def test_tampering_provenance_and_stale_full_inputs(self):
        self.accept();envelope=self.envelope()
        for path in ('provider','record','candidate','review','extra'):
            bad=copy.deepcopy(envelope)
            if path=='provider':bad['bundle']['provider']['llm_used']=False
            elif path=='record':bad['bundle']['import_record']['response_sha256']='0'*64
            elif path=='candidate':bad['bundle']['candidates'][0]['proposed_step']['bridge_rationale']='Tamper'
            elif path=='review':bad['review']['proposal_bundle_sha256']='0'*64
            else:bad['cached_approval']=True
            with self.assertRaises(ValueError):p.inspect_reviewed(self.package,self.draft,bad)
        self.draft['claims'][0]['uncertainty']='Changed unselected input history.'
        with self.assertRaises(ValueError):p.inspect_reviewed(self.package,self.draft,envelope)
        for provenance in (dict(self.provenance,execution_location='elsewhere'),dict(self.provenance,run_id='\n'),dict(self.provenance,extra=True)):
            self.setUp();self.provenance=provenance
            with self.assertRaises(ValueError):self.reimport()

    def test_handoff_response_scope_and_review_tampering(self):
        for key in ('package_sha256', 'draft_sha256', 'review_sha256'):
            scope = copy.deepcopy(self.scope); scope[key] = '0'*64
            with self.assertRaises(ValueError): p.prepare_handoff(self.package, self.draft, scope)
        handoff = copy.deepcopy(self.handoff); handoff['selected_claims'][0]['text'] = 'Changed handoff text.'
        with self.assertRaisesRegex(ValueError, 'handoff changed'):
            p.response_template(self.package, self.draft, self.scope, handoff)
        for response in (dict(self.response, handoff_sha256='0'*64), dict(self.response, extra=True)):
            with self.assertRaises(ValueError):
                p.import_response(self.package, self.draft, self.scope, self.handoff, response, self.provenance)
        for key in ('reviewer_id',):
            review=copy.deepcopy(self.review);review[key]=' '
            with self.assertRaises(ValueError):p.review_proposals(self.package,self.draft,self.bundle,review)
        self.review['decisions'][0]['review_note']=' '
        with self.assertRaises(ValueError):self.packet()
        self.setUp();self.accept();self.review['decisions'][0]['reviewed_step']['step_id']=' '
        with self.assertRaises(ValueError):self.packet()

    def test_finite_combined_limits_output_and_immutability(self):
        self.accept();before=copy.deepcopy((self.package,self.draft,self.scope,self.handoff,self.response,self.bundle,self.review))
        result=self.inspect();result['steps'][0]['assumptions'].append('Mutation')
        self.assertEqual(before,(self.package,self.draft,self.scope,self.handoff,self.response,self.bundle,self.review))
        with self.assertRaises(ValueError):p._inputs([float('nan')])
        with patch.object(p,'MAX_INPUT_BYTES',1):
            with self.assertRaisesRegex(ValueError,'combined'):self.packet()
        with patch.object(p,'MAX_HANDOFF_BYTES',1):
            with self.assertRaisesRegex(ValueError,'handoff exceeds'):p.prepare_handoff(self.package,self.draft,self.scope)
        packet=self.packet()
        with patch.object(p,'MAX_OUTPUT_BYTES',1):
            with self.assertRaises(ValueError):p._output(packet)
            with self.assertRaises(ValueError):p.render_review(packet)
        with patch.object(Path,'read_text',side_effect=AssertionError('source reread')):
            self.inspect()

    def test_actual_cli_all_stages_and_strict_json(self):
        self.declared=answer_draft.review_template(self.package,self.draft,'reviewer');self.reset();self.accept()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            files=dict(package=self.package,draft=self.draft,scope=self.scope,handoff=self.handoff,response=self.response,
                provenance=self.provenance,bundle=self.bundle,review=self.review,envelope=self.envelope(),declared=self.declared)
            for name,value in files.items():(root/(name+'.json')).write_text(json.dumps(value),encoding='utf-8')
            def run(command,names=(),extra=()):
                args=[sys.executable,str(ROOT/'argument_proposals.py'),command,str(root/'package.json'),str(root/'draft.json')]
                args += [str(root/(name+'.json')) for name in names]
                args += ['--answer-review',str(root/'declared.json'),*extra]
                return subprocess.run(args,capture_output=True,cwd=ROOT)
            for command,names,extra,expected in (
                ('template',(),('--operator-id','synthetic-operator'),dict(self.scope,selected_claim_ids=[])),
                ('prepare',('scope',),(),self.handoff),('response-template',('scope','handoff'),(),dict(self.response,candidates=[])),
                ('import',('scope','handoff','response','provenance'),(),self.bundle),
                ('review-template',('bundle',),('--reviewer-id','synthetic-reviewer'),p.review_template(self.package,self.draft,self.bundle,'synthetic-reviewer',self.declared)),
                ('review',('bundle','review'),(),self.packet()),('export',('bundle','review'),(),self.envelope()),
                ('inspect',('envelope',),(),self.inspect())):
                result=run(command,names,extra);self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(json.loads(result.stdout),expected)
            self.assertIn(b'Original imported proposal',run('review',('bundle','review'),('--format','text')).stdout)
            (root/'scope.json').write_text('{"schema":1,"schema":2}')
            result=run('prepare',('scope',));self.assertNotEqual(result.returncode,0);self.assertEqual(result.stdout,b'');self.assertIn(b'duplicate JSON',result.stderr)
            (root/'scope.json').write_bytes(b' '* (p.MAX_INPUT_BYTES+1))
            result=run('prepare',('scope',));self.assertNotEqual(result.returncode,0);self.assertEqual(result.stdout,b'')


if __name__=='__main__':unittest.main()
