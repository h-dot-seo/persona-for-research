"""Call-local journey formatting reuse preserves raw public validation and text."""
import copy
import hashlib
import json
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import argument_map as am
import argument_proposals as gp
import research_journey as journey
import source_recheck
import test_research_journey as plain_fixture
import test_contextual_argument_integration as imported_fixture
import test_argument_proposal_integration as topology_fixture
from answer_draft import review_template
from persona import payload_sha256


def cases():
    f = plain_fixture.ResearchJourneyTests(); f.setUp()
    yield 'plain', copy.deepcopy(f.args())
    f.argument['steps'] = []
    yield 'empty', copy.deepcopy(f.args())
    f.setUp(); f.review = None; f.argument['review_sha256'] = None
    yield 'no_review', copy.deepcopy(f.args())
    f.setUp()
    f.argument['steps'][0]['bridge_rationale'] = 'Synthetic 한글 😀 \\ path\nline\tcontrol\x01'
    yield 'unicode_control', copy.deepcopy(f.args())
    f.setUp()
    f.case.draft['claims'].append(dict(claim_id='last', text='Last synthetic claim.',
        claim_type='operator_synthesis', uncertainty=None, citations=[]))
    f.review = review_template(f.case.package, f.case.draft, 'synthetic-reviewer')
    f.argument.update(draft_sha256=payload_sha256(f.case.draft), review_sha256=payload_sha256(f.review))
    f.argument['steps'].insert(0, dict(step_id='last-step', premise_claim_ids=['conclusion'],
        conclusion_claim_id='last', bridge_rationale='Declared before its premise bridge.', assumptions=[], defeater=None))
    yield 'topology', copy.deepcopy(f.args())
    ordered = topology_fixture.ArgumentProposalIntegrationTests(); ordered.setUp()
    yield 'v1_topology', copy.deepcopy(ordered.case.args())
    c = imported_fixture.ContextualArgumentIntegrationTests(); c.setUp()
    for reviewed in (True, False):
        if not reviewed: c.f.review = None
        for contextual in (False, True):
            c.f.argument = c.argument(contextual)[-1]
            yield ('v2' if contextual else 'v1') + ('_review' if reviewed else '_no_review'), copy.deepcopy(c.f.args())


def snapshot(args):
    report = journey.inspect(*args)
    text = journey.render(*args)
    return dict(report=payload_sha256(report), text=hashlib.sha256(text.encode()).hexdigest())


# Full JSON/text hashes captured from the unmodified v0.64 implementation.
SNAPSHOTS = {
    "v1_topology": {"report": "ba61da2e1417ab60efe5f1342e9f279fbc8401eafdd164474f5e8d6e9c969d09", "text": "eb07ed54367b72e96f013998ba9dc4d0fab34e2dbd13ba71495b1d8ce561861a"},
    "plain": {
        "report": "a4405809c8fde162293d6e73dd2ca8083329570d44ac9e2428f0607fa7d23350",
        "text": "6c531ddd79d77355034a2932dc9529e53474358298639a3671767035ecfdde11"
    },
    "empty": {
        "report": "83832cff04c276d7c04e6ca0b688b3907228e133acc4edcc67eb72e1fbbb6867",
        "text": "9eb177880b7adea3c330fffd93b0997497bbc99329b54951c9b501322398663a"
    },
    "no_review": {
        "report": "83837ed78e3aa1db8fad092c38cd1df46819da059dfa9da822bc9450aca66250",
        "text": "013e276bb74b5096702ca86230528563ca9258f5a35e7879b2530317c32b08cd"
    },
    "unicode_control": {
        "report": "bc773cd3e739ddf6e8779482fc14c6de28f84206c3b451a86b36b6e2b3d772f1",
        "text": "80e7983de823c1879803d22eae38c6e72384fb9ef26474502b7eaddf2e13e76b"
    },
    "topology": {
        "report": "aa67c8bc9b6e138ceb9842f04327d1e33dda8ccfb5fbbda5a0a84bb2849f35a3",
        "text": "b34eef87bfadc51c0f2dfc954bdb069d7673e0b371378cb9e8fde0fdc2c162fd"
    },
    "v1_review": {
        "report": "628937f31361dcd7c4ef13565b1600d6b3f7cf8dc03a3e417c3972cf69e71c09",
        "text": "622dcf829e3d7ba28a785b44d6b6957c71a5a0a22e48f4e401e364fb00dd671c"
    },
    "v2_review": {
        "report": "20691904f2a3f746252ea88254e15374c66cde05b75f1642bdb9cef8f21e8c3d",
        "text": "98f4ba8e1f5afd7e64e79a2f901a96cc64bb726f897c33943cd5cb6e8af71271"
    },
    "v1_no_review": {
        "report": "5597883bdaa8bd375e76f94268b73d5d07afc33a9746a438db18d85edae9b9ef",
        "text": "e0695efc0b7b29bb393fba23d3c168f2576124c42e8394e2cdf841d5ae8af2db"
    },
    "v2_no_review": {
        "report": "d5ad59b98bfb697f4bbf8c7fc4747c7a4c563a74d0f0f637017cb86632433469",
        "text": "c93f726fa8d2287ba3df4817533a7b53df4ffdfc218435912cf0569b83157215"
    }
}


class JourneyArgumentRenderReuseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # JSON fixture inputs also model actual file-based callers without aliases.
        cls.fixtures = json.loads(json.dumps(dict(cases())))

    def args(self, name='plain'):
        return copy.deepcopy(self.fixtures[name])

    def reusable(self, args, result=None):
        if result is None: result = journey.inspect(*args)
        return journey._argument_render_reusable(result, args[0], args[5], args[6], args[9])

    def test_complete_prechange_json_and_text_snapshots(self):
        for name, args in self.fixtures.items():
            with self.subTest(case=name):
                report = journey.inspect(*args)
                text = journey.render(*args)
                self.assertEqual(dict(report=payload_sha256(report),
                    text=hashlib.sha256(text.encode()).hexdigest()), SNAPSHOTS[name])
                self.assertTrue(self.reusable(args, report))

    def test_outer_inspection_once_and_public_render_always_fresh(self):
        for name in ('plain', 'v1_review', 'v2_review'):
            args = self.args(name)
            # Count the supplied outer map, not internal accepted-map projections.
            original = am.inspect
            outer = []
            def inspected(package, draft, supplied, declared_review=None):
                if supplied == args[6]: outer.append(supplied)
                return original(package, draft, supplied, declared_review)
            with self.subTest(case=name), patch.object(am, 'inspect', side_effect=inspected), \
                    patch.object(journey, 'inspect_argument', side_effect=inspected):
                journey.render(*args)
                self.assertEqual(len(outer), 1)
                am.render(args[0], args[5], args[6], args[9])
                self.assertEqual(len(outer), 2)
            with patch.object(journey, '_argument_render_reusable', return_value=False), \
                    patch.object(am, 'inspect', side_effect=inspected), \
                    patch.object(journey, 'inspect_argument', side_effect=inspected):
                journey.render(*args)
                self.assertEqual(len(outer), 4)  # Old path adds two outer inspections.

    def test_next_journey_call_revalidates_and_rejects_cached_reports(self):
        args = self.args()
        journey.render(*args)
        args[6]['steps'][0]['bridge_rationale'] = 'Changed valid bridge.'
        self.assertIn('Changed valid bridge.', journey.render(*args))
        args[6]['steps'][0]['conclusion_claim_id'] = 'absent'
        with self.assertRaisesRegex(ValueError, 'operator_synthesis'): journey.render(*args)
        args = self.args()
        args[6] = am.inspect(args[0], args[5], args[6], args[9])
        for call in (lambda: journey.render(*args), lambda: am.render(args[0], args[5], args[6], args[9])):
            with self.assertRaisesRegex(ValueError, 'missing or unknown fields'): call()

    def test_plain_tuple_falls_back_and_preserves_raw_error(self):
        args = self.args(); args[6]['steps'] = tuple(args[6]['steps'])
        self.assertFalse(self.reusable(args))
        with patch.object(journey, 'render_argument', wraps=am.render) as raw:
            with self.assertRaisesRegex(ValueError, 'steps must be an array'): journey.render(*args)
        self.assertEqual(raw.call_count, 1)

    def test_legacy_tuple_coercion_is_still_accepted(self):
        args = self.args('v1_review')
        step = args[6]['review']['decisions'][0]['reviewed_step']
        step['assumptions'] = tuple(step['assumptions'])
        expected = SNAPSHOTS['v1_review']['text']
        self.assertFalse(self.reusable(args))
        with patch.object(journey, 'render_argument', wraps=am.render) as raw:
            text = journey.render(*args)
        self.assertEqual(raw.call_count, 1)
        self.assertEqual(hashlib.sha256(text.encode()).hexdigest(), expected)

    def test_contextual_tuple_coercion_is_still_rejected(self):
        args = self.args('v2_review')
        step = args[6]['review']['decisions'][0]['reviewed_step']
        step['assumptions'] = tuple(step['assumptions'])
        self.assertFalse(self.reusable(args))
        with patch.object(journey, 'render_argument', wraps=am.render) as raw:
            with self.assertRaisesRegex(ValueError, 'research context must contain strict JSON data'): journey.render(*args)
        self.assertEqual(raw.call_count, 1)

    def test_nonstring_keys_subclasses_aliases_and_depth_use_old_path(self):
        class String(str): pass
        class Mapping(dict): pass
        class Array(list): pass
        modifications = [
            lambda args: args[0].update(ignored={1: 'legacy extra wrapper data'}),
            lambda args: args[6].update(operator_id=String(args[6]['operator_id'])),
            lambda args: args.__setitem__(6, Mapping(args[6])),
            lambda args: args[6].update(steps=Array(args[6]['steps'])),
            lambda args: args[0].update(ignored=[args[6]['steps'], args[6]['steps']]),
        ]
        deep = []
        for _ in range(65): deep = [deep]
        modifications.append(lambda args: args[0].update(ignored=deep))
        for modify in modifications:
            args = self.args(); modify(args)
            self.assertFalse(self.reusable(args))
            with patch.object(journey, '_argument_render_reusable', return_value=False):
                expected = journey.render(*args)
            with patch.object(journey, 'render_argument', wraps=am.render) as raw:
                self.assertEqual(journey.render(*args), expected)
            self.assertEqual(raw.call_count, 1)

    def test_eligibility_is_nonraising_and_does_not_normalize(self):
        args = self.args(); result = journey.inspect(*args)
        class Hostile(dict):
            def items(self): raise AssertionError('must not inspect subclass')
            def __iter__(self): raise AssertionError('must not inspect subclass')
        cycle = []; cycle.append(cycle)
        for value in (Hostile(), object(), (1,), {1: 'key'}, float('nan'), float('inf'), cycle,
                      '\ud83d\ude00', '\ud800', {'\udc00': 1}):
            with self.subTest(kind=type(value)):
                self.assertFalse(journey._argument_render_reusable(result, value, args[5], args[6], args[9]))

    def test_nonbmp_scalar_eligible_surrogates_preserve_rejection(self):
        args = self.args('unicode_control')
        self.assertTrue(self.reusable(args))
        with patch.object(journey, 'render_argument', side_effect=AssertionError('eligible scalar fell back')):
            journey.render(*args)
        args = self.args(); args[6]['steps'][0]['bridge_rationale'] = 'paired \ud83d\ude00'
        self.assertFalse(self.reusable(args))
        with patch.object(journey, 'render_argument', wraps=am.render) as raw:
            with self.assertRaises(UnicodeEncodeError): journey.render(*args)
        self.assertEqual(raw.call_count, 1)
        args[6]['steps'][0]['bridge_rationale'] = 'lone \ud800'
        with patch.object(journey, 'render_argument', wraps=am.render) as raw:
            with self.assertRaises(UnicodeEncodeError): journey.render(*args)
        self.assertEqual(raw.call_count, 0)  # Initial inspection already rejects.

    def test_full_binding_checks_include_wrapper_and_none_review(self):
        args = self.args('no_review'); report = journey.inspect(*args)
        self.assertEqual(report['bindings']['declared_review_sha256'], payload_sha256(None))
        self.assertTrue(self.reusable(args, report))
        for index in (0, 5, 6, 9):
            changed = copy.deepcopy(args)
            if index == 9: changed[index] = {}
            else: changed[index]['ignored-new-field'] = 'changed full raw object'
            self.assertFalse(self.reusable(changed, report))
        for name in ('package', 'draft', 'argument', 'declared_review'):
            changed = copy.deepcopy(report); changed['bindings'][name + '_sha256'] = '0' * 64
            self.assertFalse(self.reusable(args, changed))
        with patch.object(journey, 'payload_sha256', side_effect=ValueError('uncertain hash')):
            self.assertFalse(self.reusable(args, report))

    def test_source_path_callback_changed_map_keeps_old_output_and_errors(self):
        root = str(Path(__file__).resolve().parent / 'examples/synthetic-sources')
        for valid in (True, False):
            def run(force_old):
                args = self.args()
                selection = source_recheck.template(args[0], 'synthetic-source')
                for row in selection['sources']: row['source_file'] = row['paper_id'] + '.md'
                class MutatingRoot:
                    def __fspath__(self):
                        if valid: args[6]['steps'][0]['bridge_rationale'] = 'Changed during source audit.'
                        else: args[6]['steps'] = ()
                        return root
                with ExitStack() as stack:
                    if force_old: stack.enter_context(patch.object(journey, '_argument_render_reusable', return_value=False))
                    raw = stack.enter_context(patch.object(journey, 'render_argument', wraps=am.render))
                    try:
                        result = ('text', journey.render(*args, source_selection=selection, source_root=MutatingRoot()))
                    except ValueError as exc:
                        result = (type(exc).__name__, str(exc))
                    self.assertEqual(raw.call_count, 1)
                    return result
            with self.subTest(valid=valid):
                expected = run(True)
                self.assertEqual(run(False), expected)
                if valid: self.assertIn('Changed during source audit.', expected[1])
                else: self.assertEqual(expected, ('ValueError', 'steps must be an array'))

    def test_transfer_render_mutation_checked_at_original_argument_point(self):
        args = self.args(); original = journey.render_transfer
        def mutate(*a, **kw):
            text = original(*a, **kw)
            args[6]['steps'][0]['bridge_rationale'] = 'Changed after transfer rendering.'
            return text
        with patch.object(journey, 'render_transfer', side_effect=mutate), \
                patch.object(journey, 'render_argument', wraps=am.render) as raw:
            text = journey.render(*args)
        self.assertEqual(raw.call_count, 1)
        self.assertIn('Changed after transfer rendering.', text)

    def test_stale_bindings_and_rejected_history_are_revalidated(self):
        for index, field in ((6, 'review_sha256'), (9, 'draft_sha256')):
            args = self.args(); args[index][field] = '0' * 64
            with self.assertRaises(ValueError): journey.render(*args)
        args = self.args('v1_review')
        args[6]['review']['decisions'][1]['review_note'] = 'Changed rejected bridge history.'
        self.assertIn('Changed rejected bridge history.', journey.render(*args))
        args[6]['bundle']['scope']['draft_sha256'] = '0' * 64
        with self.assertRaises(ValueError): journey.render(*args)

    def test_limits_and_invalid_input_precede_source_reads(self):
        args = self.args()
        for field, message in (('MAX_INPUT_BYTES', 'combined journey'), ('MAX_OUTPUT_BYTES', 'journey report')):
            with patch.object(journey, field, 10):
                with self.assertRaisesRegex(ValueError, message): journey.render(*args)
        # Keep the initial JSON report below the limit, force the final text limit.
        with patch.object(journey, 'encode_result', return_value=b'validated'), patch.object(journey, 'MAX_OUTPUT_BYTES', 10):
            with self.assertRaisesRegex(ValueError, 'journey report'): journey.render(*args)
        args[6]['steps'][0]['conclusion_claim_id'] = 'absent'
        with patch.object(source_recheck, 'audit', side_effect=AssertionError('source access before validation')):
            with self.assertRaisesRegex(ValueError, 'operator_synthesis'):
                journey.render(*args, source_selection={}, source_root='not-read')
        imported = self.args('v1_review')
        inspected = am.inspect(imported[0], imported[5], imported[6], imported[9])
        with patch.object(gp, 'MAX_OUTPUT_BYTES', 10):
            with self.assertRaisesRegex(ValueError, 'report exceeds'): am._render_inspected(inspected)
        # Specifically exercise the map formatter's own final text-size guard.
        with patch.object(gp, 'render_review', return_value=''), patch.object(gp, 'MAX_OUTPUT_BYTES', 10):
            with self.assertRaisesRegex(ValueError, 'imported argument text report exceeds'): am._render_inspected(inspected)

    def test_formatter_does_not_mutate_report_inputs_or_call_providers(self):
        from extraction_adapter import MockProvider
        args = self.args(); before = copy.deepcopy(args)
        report = journey.inspect(*args); saved = copy.deepcopy(report)
        with ExitStack() as stack:
            for target in ('builtins.open', 'pathlib.Path.open', 'socket.socket', 'subprocess.run'):
                stack.enter_context(patch(target, side_effect=AssertionError('unexpected I/O')))
            stack.enter_context(patch.object(MockProvider, 'extract', side_effect=AssertionError('provider invoked')))
            text = am._render_inspected(report['argument_review'])
            self.assertTrue(text.endswith('\n')); self.assertFalse(text.endswith('\n\n'))
            journey.render(*args)
        self.assertEqual(args, before); self.assertEqual(report, saved)


class JourneyArgumentRenderBudgetTests(unittest.TestCase):
    def test_wide_and_cumulative_node_budgets_fall_back_without_new_rejection(self):
        f = plain_fixture.ResearchJourneyTests(); f.setUp()
        original = json.loads(json.dumps(f.args()))
        budget = journey._ARGUMENT_RENDER_MAX_NODES
        for extra in ([None] * (budget + 1),
                      {str(index): None for index in range(budget // 2 + 1)},
                      [[None] * 128 for _ in range(budget // 128)]):
            args = copy.deepcopy(original); args[0]['ignored-wrapper-data'] = extra
            report = journey.inspect(*args)
            with patch.object(journey, 'payload_sha256', side_effect=AssertionError('ineligible data must not be hashed')):
                self.assertFalse(journey._argument_render_reusable(report, args[0], args[5], args[6], args[9]))
            with patch.object(journey, '_argument_render_reusable', return_value=False):
                expected = journey.render(*args)
            with patch.object(journey, 'render_argument', wraps=am.render) as raw:
                self.assertEqual(journey.render(*args), expected)
            self.assertEqual(raw.call_count, 1)
        report = journey.inspect(*original)
        self.assertTrue(journey._argument_render_reusable(report, original[0], original[5], original[6], original[9]))


if __name__ == '__main__': unittest.main()
