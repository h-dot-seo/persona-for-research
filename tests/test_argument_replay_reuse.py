"""Fresh call-local argument replay reuse; invented fixtures and no provider I/O."""
import unittest
from unittest.mock import patch
import copy,json,hashlib
import answer_draft as ad, argument_map as am, argument_proposals as gp
import tests.test_argument_map as plain
import tests.test_contextual_argument_proposals as contextual
from persona import payload_sha256

def cases():
    p=plain.ArgumentMapTests(); p.setUp()
    c=contextual.ContextualArgumentTests(); c.setUp()
    for name,package,draft,step,version in [('plain',p.package,p.draft,p.map['steps'][0],False),('contextual',c.p,c.d,dict(c.r['candidates'][0],step_id='bridge'),True)]:
        for reviewed in (False,True):
            declared=ad.review_template(package,draft,'synthetic-final-reviewer') if reviewed else None
            scope=gp.template(package,draft,'synthetic-operator',declared,include_recorded_answer_context=version)
            scope['selected_claim_ids']=list(dict.fromkeys(step['premise_claim_ids']+[step['conclusion_claim_id']]))
            handoff=gp.prepare_handoff(package,draft,scope,declared)
            response=gp.response_template(package,draft,scope,handoff,declared)
            candidate={k:copy.deepcopy(v) for k,v in step.items() if k!='step_id'}
            response['candidates']=[candidate,dict(copy.deepcopy(candidate),bridge_rationale='Rejected alternative.')]
            provenance=dict(provider_id='synthetic-provider',model_id='synthetic-model',run_id='synthetic-run',operator_id='synthetic-importer',execution_location='unknown')
            bundle=gp.import_response(package,draft,scope,handoff,response,provenance,declared)
            review=gp.review_template(package,draft,bundle,'synthetic-reviewer',declared)
            review['decisions'][0].update(decision='accept',review_note='Synthetic adoption.',reviewed_step=copy.deepcopy(step))
            review['decisions'][1].update(decision='reject',review_note='Synthetic rejection.')
            envelope=gp.export_reviewed(package,draft,bundle,review,declared)
            yield name+('_reviewed' if reviewed else ''),dict(package=package,draft=draft,declared=declared,scope=scope,step=step,bundle=bundle,review=review,envelope=envelope)

def snapshot(c):
    p,d,r=c['package'],c['draft'],c['declared']
    form=am.template(p,d,'synthetic-operator',r);form['steps']=[copy.deepcopy(c['step'])]
    packet=gp.review_proposals(p,d,c['bundle'],c['review'],r)
    objects=dict(form=form,map=am.inspect(p,d,form,r),packet=packet,envelope=c['envelope'],inspection=am.inspect(p,d,c['envelope'],r))
    texts=dict(map_text=am.render(p,d,form,r),packet_text=gp.render_review(packet),inspection_text=am.render(p,d,c['envelope'],r))
    return dict({k:payload_sha256(v) for k,v in objects.items()},**{k:hashlib.sha256(v.encode()).hexdigest() for k,v in texts.items()})

# Full report and text hashes captured before the replay extraction.
SNAPSHOTS = {'contextual': {'envelope': '8805aba415b244d5bf27d0d5210cad09c23b0c1baca8712f823f4f9bc64b1a37',
                'form': '41069dfc310e94a64701899c907722d58403a33beb2bb866a13965e83a872818',
                'inspection': '47fe509f24ebae885eea048a0ac5cb067f31459d0f8810d6f8f241027fd9db3d',
                'inspection_text': 'e3d7d699727a36b1138ba8c9f36276cd8d96524617f86f0bfb5c70868c486ce7',
                'map': 'ea5d907d97b4f26753816709a4149a9d4d86fa454bfee873afbb8ad276f6bb31',
                'map_text': '9653b977b8c17bde904a40346f441fe4c8eb02db7df014d55147299ca249843f',
                'packet': '8990e11756de00b0ce61836fd950a51460bea684c3ff2dab1e155bb936e08b2a',
                'packet_text': '11256cb43fbce7925fc5c7345fbd786dc2737f1b12de017a61db068bf13c33d4'},
 'contextual_reviewed': {'envelope': 'f2cb17462a8f9abb5875c3bd51d34d6987ab57e928ac8c81ad406260f92bfebb',
                         'form': '5525c9a4d1f8019f6cc5a4bc3044b3d12a616ba7261dc004e90682e9d34bcb11',
                         'inspection': 'de315f1568e9aee628a0c4042d2431479543e7a2516f0f8ffe9487e7b7bb46d0',
                         'inspection_text': 'c32062d160875972a9091967ae3faeaeff928b391920ed112a25bf2947ec02ed',
                         'map': '9bc59ab81e2d4eac6a66cbf87517e3b5bf1d725f9f5997b4de4542922d073cc7',
                         'map_text': '606abaf1b84897ba077d4cb22cd500c742d1a57848b9e6701edb5bda66ff3b9b',
                         'packet': '867e0ffd15de39b87dfe60843ac31f6524238bfe4b7d289930b536b4d5cd2a24',
                         'packet_text': '553d0d06ddf37d9b14a16edd812f1293005261015eb16ff3e1c57fded56c7035'},
 'plain': {'envelope': '5cc003273e6385a472bb025259695ada4a6ab22b46071decb94f1e456bafeadc',
           'form': '11b601e70d64312caa8c08ed8172070d75a55f7fa05b27a7d9e9367092553267',
           'inspection': '863008b63c0aaa2bd44910956b5e8fb75c1ac3761eddd3c73577c82efd3aa817',
           'inspection_text': '04861c3ff6df36d1307d0770801ee396e115e22eb45dd87b4afe5db58a1e0eb0',
           'map': 'a3b1bf09e51619703113fd252a2cb1a2fe8c6b3defe8a3c312009d57a48208a1',
           'map_text': '4f4b94063603e0ca7f24038bab4ba85683a81c20a70663b3f3b24f141b92fce2',
           'packet': 'e125a5ccc95691834e8dc72d1b927eb27667e15111968abec044739a80db5b87',
           'packet_text': '9da7a4d4bf7b0b26ed21a30bea8be3d7c6aad4c772124a6ef6dd3a3138b5e1ee'},
 'plain_reviewed': {'envelope': 'ce34b2f380342023a8b7b7dd1317e47b4c5349758277d941db8e28cf20e644cf',
                    'form': '1da050e6eedec15a71d282a9882ca239ffb1f8a0466cb04a3c74d0f8135d97e0',
                    'inspection': '8fd255944e71d4c3a927284d6bf68a4def45e8b6ab3f1f75169c9e10615b64d2',
                    'inspection_text': 'e09763fc346782d6d46f31548583f968324e49fba9a7425376a80019e1844fbb',
                    'map': 'b0575cbbe4982c5c5adbc852be1f4417c3a910ae3ebf58c8c3f5c5e874c8d525',
                    'map_text': '0af65d46d869a8b3e843371ac4c2ef669433f362ad904651abd6727a0cebf5af',
                    'packet': '896ec34e13f755167164474ed9ad4677102a739ea99d53e73783174080483ad4',
                    'packet_text': '94f26c788a88d45a44ca529d2044276f163b9c2741910780e62d28e3c7d84d5b'}}

class ArgumentReplayReuseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = dict(cases())

    def step(self, c, step=None, operator='synthetic-operator'):
        return gp._inspect_step(c['package'], c['draft'], c['scope'],
            c['step'] if step is None else step, operator, c['declared'])

    def test_complete_json_and_text_snapshots(self):
        for name, c in self.cases.items():
            with self.subTest(case=name):
                self.assertEqual(snapshot(c), SNAPSHOTS[name])

    def test_single_fresh_replay_and_unmodified_local_answer(self):
        for name, c in self.cases.items():
            captured = []
            original = am._answer
            def fresh(*args):
                answer = original(*args)
                captured.append((answer, copy.deepcopy(answer)))
                return answer
            with self.subTest(case=name), patch.object(am, '_answer', side_effect=fresh) as replay:
                first = self.step(c)
                self.assertEqual(replay.call_count, 1)
                second = self.step(c)
                self.assertEqual(replay.call_count, 2)
            self.assertEqual(first, second)
            self.assertIsNot(captured[0][0], captured[1][0])
            for actual, before in captured:
                self.assertEqual(actual, before)

    def test_actual_review_and_inspection_replay_counts(self):
        # N=2 original candidates, A=1 accepted rewrite: 2N+A=5 fewer replays.
        # Pre-extraction inspection captures: v1=18, v2=19.
        # Review omits the final two projection replays. All validate raw answers.
        for name, c in self.cases.items():
            contextual = name.startswith('contextual')
            for operation, expected in ((lambda: gp.review_proposals(c['package'], c['draft'], c['bundle'], c['review'], c['declared']), 12 if contextual else 11),
                                        (lambda: am.inspect(c['package'], c['draft'], c['envelope'], c['declared']), 14 if contextual else 13)):
                with self.subTest(case=name, expected=expected), patch.object(am, '_answer', wraps=am._answer) as replay:
                    operation()
                    self.assertEqual(replay.call_count, expected)

    def test_public_entry_points_always_validate_raw_inputs(self):
        c = self.cases['plain']
        with patch.object(am, '_answer', wraps=am._answer) as replay:
            form = am.template(c['package'], c['draft'], 'operator')
            self.assertEqual(replay.call_count, 1)
            am.inspect(c['package'], c['draft'], form)
            self.assertEqual(replay.call_count, 2)
        bad = copy.deepcopy(c['draft']); bad['claims'][0]['claim_type'] = 'invalid'
        for call in (lambda: am.template(c['package'], bad, 'operator'),
                     lambda: am.inspect(c['package'], bad, form)):
            with self.assertRaises(ValueError): call()
        report = am._answer(c['package'], c['draft'], None)
        with self.assertRaises(ValueError): am.template(c['package'], report, 'operator')

    def test_separate_calls_revalidate_changed_draft_and_review(self):
        c = copy.deepcopy(self.cases['plain_reviewed'])
        self.step(c)
        c['declared']['decisions'][0].update(decision='reject', note='Changed review.')
        result = self.step(c)
        self.assertEqual(result['premises'][0]['declared_review_decision'], 'reject')
        with self.assertRaises(ValueError): am.inspect(c['package'], c['draft'], c['envelope'], c['declared'])
        c['draft']['claims'][0]['uncertainty'] = 'Changed complete draft history.'
        with self.assertRaises(ValueError): self.step(c)  # Review is now stale.
        c['declared'] = None
        self.assertEqual(self.step(c)['premises'][0]['uncertainty'], 'Changed complete draft history.')

    def test_separate_calls_revalidate_context_and_rejected_history(self):
        c = copy.deepcopy(self.cases['contextual'])
        self.step(c)
        old = am._answer(c['package'], c['draft'], None)
        c['draft']['review']['decisions'][-1]['review_note'] = 'Changed rejected history.'
        self.step(c)  # Valid changed history must be replayed, not cached.
        fresh = am._answer(c['package'], c['draft'], None)
        self.assertNotEqual(old['draft_sha256'], fresh['draft_sha256'])
        with self.assertRaises(ValueError): am.inspect(c['package'], c['draft'], c['envelope'])
        c['draft']['bundle']['scope']['research_context']['context']['target_context'] = 'Changed recorded context.'
        with self.assertRaises(ValueError): self.step(c)  # The old import bindings are stale.

    def test_validation_order_fields_operators_and_limits(self):
        c = self.cases['plain']
        for change, message, count in (
            ({'extra': True}, 'all explicit', 0),
            ({'premise_claim_ids': ['q1'] * 65}, 'at most 64', 0),
            ({'assumptions': ['x'] * 33}, 'at most 32', 0),
            ({'conclusion_claim_id': 'absent'}, 'explicit selected', 0),
            ({'premise_claim_ids': []}, 'explicit premise', 1),
            ({'premise_claim_ids': ['q1','q1']}, 'duplicate or self', 1),
            ({'conclusion_claim_id': 'q1'}, 'operator_synthesis', 1),
            ({'bridge_rationale': ' '}, 'bridge_rationale', 1),
            ({'step_id': ' '}, 'step_id', 1),
            ({'assumptions': ['same','same']}, 'duplicate assumption', 1)):
            with self.subTest(change=change), patch.object(am, '_answer', wraps=am._answer) as replay:
                with self.assertRaisesRegex(ValueError, message): self.step(c, dict(c['step'], **change))
                self.assertEqual(replay.call_count, count)
        for operator in (None, '', ' ', 'x' * 129):
            with self.subTest(operator=operator), patch.object(am, '_answer', wraps=am._answer) as replay:
                with self.assertRaisesRegex(ValueError, 'operator_id'): self.step(c, operator=operator)
                self.assertEqual(replay.call_count, 1)
        with patch.object(am, '_answer', side_effect=ValueError('raw answer first')):
            with self.assertRaisesRegex(ValueError, 'raw answer first'): self.step(c, operator=' ')
            with self.assertRaisesRegex(ValueError, 'raw answer first'): am.inspect(c['package'], c['draft'], {})

    def test_input_output_isolation_and_no_io(self):
        from contextlib import ExitStack
        from extraction_adapter import MockProvider
        for name, original in self.cases.items():
            c = copy.deepcopy(original); before = copy.deepcopy(c)
            with self.subTest(case=name), ExitStack() as stack:
                for target in ('builtins.open', 'pathlib.Path.read_text', 'pathlib.Path.read_bytes',
                               'socket.socket', 'subprocess.run'):
                    stack.enter_context(patch(target, side_effect=AssertionError('unexpected I/O')))
                stack.enter_context(patch.object(MockProvider, 'extract', side_effect=AssertionError('provider invoked')))
                result = self.step(c)
                result['assumptions'].append('Changed returned assumptions.')
                result['premise_claim_ids'].append('Changed returned endpoints.')
                result['premises'][0]['uncertainty'] = 'Changed returned metadata.'
                self.assertEqual(c, before)
                again = self.step(c)
                self.assertNotIn('Changed returned assumptions.', again['assumptions'])
                c['step']['assumptions'].append('Changed input after return.')
                self.assertNotIn('Changed input after return.', again['assumptions'])


if __name__ == '__main__':
    unittest.main()
