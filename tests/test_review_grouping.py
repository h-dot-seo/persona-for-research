"""Call-local grouping: unchanged rendering and bounded conservative eligibility."""
import copy
import inspect
import itertools
import os
import subprocess
import json
import math
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import review_package as r
from research_workflow import build

ROOT = Path(__file__).resolve().parents[1]


def synthetic(size):
    corpus = json.loads((ROOT / 'examples/reasoning-corpus.json').read_bytes())
    base = corpus['papers'][0]
    corpus['papers'] = []
    for i in range(size):
        paper = copy.deepcopy(base)
        paper['paper_id'] = 'synthetic-group-%06d' % i
        paper['source_sha256'] = '%064x' % i
        paper['observations'][0]['method'] = 'synthetic method %06d' % i
        corpus['papers'].append(paper)
    # Build through the public path; no invented rules or saved application.
    return build(corpus)


def measured(package, *, fallback=False):
    """Line-event work counts, not elapsed time or a speed claim."""
    sources = inspect.getsourcelines(r._plain_json_tree)
    node_line = sources[1] + next(i for i, s in enumerate(sources[0]) if 'item = pending.pop()' in s)
    key_line = sources[1] + next(i for i, s in enumerate(sources[0]) if 'if type(key) is not str:' in s)
    sources = inspect.getsourcelines(r._ordered_rule_groups)
    index_line = sources[1] + next(i for i, s in enumerate(sources[0]) if 'groups.setdefault' in s)
    sources = inspect.getsourcelines(r.render)
    candidate_line = sources[1] + next(i for i, s in enumerate(sources[0]) if "if (rule['method']" in s)
    counts = dict(guard_nodes=0, guard_keys=0, index_rules=0, candidate_rules=0)
    locations = {(r._plain_json_tree.__code__, node_line): 'guard_nodes',
                 (r._plain_json_tree.__code__, key_line): 'guard_keys',
                 (r._ordered_rule_groups.__code__, index_line): 'index_rules',
                 (r.render.__code__, candidate_line): 'candidate_rules'}
    # The key-type generator performs exactly two row-key visits for each rule
    # and pattern. Account for them separately from bucket construction.
    original = sys.gettrace()
    def trace(frame, event, arg):
        if event == 'line':
            name = locations.get((frame.f_code, frame.f_lineno))
            if name:
                counts[name] += 1
        return trace
    try:
        sys.settrace(trace)
        if fallback:
            with patch.object(r, '_plain_json_tree', return_value=False):
                text = r.render(package, 'synthetic question', 'model design')
        else:
            text = r.render(package, 'synthetic question', 'model design')
    finally:
        sys.settrace(original)
    counts['row_type_checks'] = (2 * len(package['persona']['rules']) if counts['index_rules'] else 0)
    counts['key_shape_fields'] = (4 * len(package['persona']['rules']) if counts['index_rules'] else 0)
    return text, counts


class ReviewGroupingTests(unittest.TestCase):
    def setUp(self):
        self.package = synthetic(4)

    def test_small_actual_work_counts_include_guards_and_index(self):
        old, before = measured(self.package, fallback=True)
        new, after = measured(self.package)
        self.assertEqual(old.encode('utf-8'), new.encode('utf-8'))
        self.assertEqual(before['candidate_rules'], 16)
        self.assertEqual(after['candidate_rules'], 4)
        self.assertEqual(after['index_rules'], 4)
        self.assertEqual(after['key_shape_fields'], 16)
        self.assertGreater(after['guard_nodes'], 0)
        self.assertGreater(after['guard_keys'], 0)
        # No claim that the extra guards pay for themselves on tiny inputs.

    def test_groups_preserve_duplicate_rule_order_and_exact_keys(self):
        rows = [dict(method=m, condition=c, position=i) for i, (m, c) in enumerate([
            ('A', 'x'), ('B', 'x'), ('A', 'x'), ('a', 'x'), ('A', 'X')])]
        grouped = r._ordered_rule_groups(rows, [])
        self.assertEqual([v['position'] for v in grouped['A', 'x']], [0, 2])
        self.assertEqual(len(grouped), 4)
        self.assertIs(grouped['A', 'x'][0], rows[0])
        self.assertIsNone(r._ordered_rule_groups([dict(method=[], condition='x')], []))

    def test_actual_conflicts_empty_topics_details_wrapper_and_input_unchanged(self):
        corpus = json.loads((ROOT / 'examples/reasoning-corpus.json').read_bytes())
        corpus['papers'][0]['observations'][0]['stance'] = 'challenge'
        package = build(corpus)
        for value in (package, dict(package=package, application={'ignored': True})):
            before = copy.deepcopy(value)
            for topic in ('model design', 'MODEL DESIGN', 'absent'):
                for details in (False, True):
                    with patch.object(r, '_plain_json_tree', return_value=False):
                        expected = r.render(value, '한국어\nquestion', topic, evidence_details=details)
                    self.assertEqual(r.render(value, '한국어\nquestion', topic, evidence_details=details), expected)
            self.assertEqual(value, before)

    def test_imported_origin_exact_output_and_no_source_reads(self):
        from observation_provenance import HASH_FIELDS, ORIGIN, content_sha256
        corpus = json.loads((ROOT / 'examples/reasoning-corpus.json').read_bytes())
        paper = corpus['papers'][0]; obs = paper['observations'][0]
        obs['stance'] = 'support'
        origin = {key: 'a' * 64 for key in HASH_FIELDS}
        origin.update(schema='persona.observation-origin.v1', origin=ORIGIN,
                      candidate_id='synthetic-candidate', paper_id=paper['paper_id'],
                      reviewer_id='synthetic-reviewer', operator_id='synthetic-operator',
                      proposed_claim_type=obs['claim_type'], proposed_stance=obs['stance'],
                      source_sha256=paper['source_sha256'], reviewed_observation_sha256=content_sha256(obs),
                      import_record=dict(handoff_sha256='b' * 64, response_sha256='c' * 64,
                          provenance=dict(provider_id='synthetic-provider', model_id='synthetic-model',
                              run_id='synthetic-run', operator_id='synthetic-generator', execution_location='local')))
        obs['observation_origin'] = origin
        package = build(corpus)
        with patch('pathlib.Path.open', side_effect=AssertionError('no source reads')):
            with patch.object(r, '_plain_json_tree', return_value=False):
                expected = r.render(package, 'q', 'model design', evidence_details=True)
            actual = r.render(package, 'q', 'model design', evidence_details=True)
        self.assertEqual(actual, expected)
        self.assertIn('synthetic-provider', actual)
        self.assertIn('recorded, not authenticated', actual)

    def test_guard_never_calls_custom_hooks_and_rejects_uncertain_shapes(self):
        class Dangerous(dict):
            def items(self): raise AssertionError('hook')
            def __len__(self): raise AssertionError('hook')
            def __iter__(self): raise AssertionError('hook')
        class Text(str):
            def __eq__(self, other): raise AssertionError('equality hook')
            __hash__ = str.__hash__
        class Meta(type):
            def __eq__(self, other): raise AssertionError('metaclass hook')
        class Odd(metaclass=Meta): pass
        self.assertFalse(r._plain_json_tree(Odd()))
        shared = []
        cycle = []; cycle.append(cycle)
        for value in (Dangerous(), Text('x'), {Text('x'): 1}, {1: 'x'},
                      [shared, shared], cycle, float('inf'), float('nan'), (), object(), [0] * 100_001):
            self.assertFalse(r._plain_json_tree(value))
        self.assertTrue(r._plain_json_tree({'a': [None, 1, False, 1.0, 'x']}))
        self.assertTrue(r._plain_json_tree(10 ** 400))

    def test_initial_custom_value_cannot_normalize_into_optimization(self):
        class Custom(str): pass
        value = {'original': Custom('private')}
        def checked(actual):
            actual['original'] = 'plain after validation'
            return self.package
        with patch.object(r, 'checked_package', side_effect=checked), patch.object(r, '_ordered_rule_groups') as grouped:
            r.render(value, 'q', 'model design')
        grouped.assert_not_called()
        self.assertEqual(value, {'original': 'plain after validation'})

    def test_real_wrapper_custom_get_normalization_keeps_original_path(self):
        class Wrapper(dict):
            calls = 0
            def get(self, key, default=None):
                self.calls += 1
                return super().get(key, default)
        outputs = []
        for fallback in (False, True):
            wrapper = Wrapper(package=copy.deepcopy(self.package))
            guard = r._plain_json_tree
            with patch.object(r, '_plain_json_tree', side_effect=(lambda v: False) if fallback else guard), patch.object(r, '_ordered_rule_groups') as groups:
                result = r.render(wrapper, 'q', 'model design')
            groups.assert_not_called()
            outputs.append((result, wrapper.calls))
        self.assertEqual(outputs[0], outputs[1])
        self.assertEqual(outputs[0][1], 1)

    def test_post_validation_custom_values_do_not_enable_index(self):
        class Custom(str): pass
        original = r.checked_package
        def checked(value):
            result = original(value)
            result['unused'] = Custom('private')
            return result
        with patch.object(r, 'checked_package', side_effect=checked), patch.object(r, '_ordered_rule_groups') as grouped:
            r.render(self.package, 'q', 'model design')
        grouped.assert_not_called()

    def test_validation_order_counts_and_error_strings_unchanged(self):
        for edit in (lambda p: None, lambda p: p['knowledge']['papers'][0].update(source_sha256='f' * 64),
                     lambda p: p['persona'].pop('knowledge_papers_sha256'), lambda p: p.clear()):
            outputs = []
            for fallback in (False, True):
                value = copy.deepcopy(self.package); edit(value)
                calls = []
                checked, apply = r.checked_package, r.apply
                def check(v): calls.append('checked_package'); return checked(v)
                def application(*args): calls.append('apply'); return apply(*args)
                with patch.object(r, 'checked_package', side_effect=check), patch.object(r, 'apply', side_effect=application):
                    guard = r._plain_json_tree
                    with patch.object(r, '_plain_json_tree', side_effect=(lambda v: False) if fallback else guard):
                        try: result = ('OK', r.render(value, 'q', 'model design'))
                        except Exception as exc: result = (type(exc).__name__, str(exc))
                outputs.append((result, calls))
            self.assertEqual(outputs[0], outputs[1])
            self.assertEqual(outputs[0][1][0], 'checked_package')

    def test_all_detached_api_options_preserve_text_and_failures(self):
        package = json.loads((ROOT / 'examples/trajectory-conditions-package.json').read_bytes())
        options = [('human_validation', [json.loads((ROOT / 'examples/manual-human-validation.json').read_bytes())]),
                   ('split_declaration', json.loads((ROOT / 'examples/synthetic-split-declaration.json').read_bytes())),
                   ('challenge_records', [json.loads((ROOT / 'examples/manual-candidate-challenge.json').read_bytes())]),
                   ('release_decision', json.loads((ROOT / 'examples/manual-release-decision.json').read_bytes()))]
        for bits in itertools.product((False, True), repeat=4):
            kwargs = {key: value for (key, value), enabled in zip(options, bits) if enabled}
            outputs = []
            for fallback in (False, True):
                guard = r._plain_json_tree
                with patch.object(r, '_plain_json_tree', side_effect=(lambda v: False) if fallback else guard):
                    try: result = ('OK', r.render(copy.deepcopy(package), 'q', 'model design', evidence_details=True, **copy.deepcopy(kwargs)))
                    except Exception as exc: result = (type(exc).__name__, str(exc))
                outputs.append(result)
            self.assertEqual(outputs[0], outputs[1], bits)

    def test_cli_raw_bytes_two_seeds_and_fallback(self):
        code = "import sys; import review_package as r; r._plain_json_tree=lambda v:False; r.main()"
        args = ['examples/trajectory-conditions-package.json', '--question', '한국어 question', '--topic', 'model design']
        previous = None
        for seed in ('7', '97'):
            for extra in ([], ['--evidence-details'], ['--paper-identities', 'examples/synthetic-paper-identities.json']):
                outcomes = []
                for entry in (['review_package.py'], ['-c', code]):
                    proc = subprocess.run([sys.executable, *entry, *args, *extra], cwd=ROOT,
                                          env=dict(os.environ, PYTHONHASHSEED=seed), capture_output=True, timeout=30)
                    outcomes.append((proc.returncode, proc.stdout, proc.stderr))
                self.assertEqual(outcomes[0], outcomes[1]); self.assertEqual(outcomes[0][0], 0)
                if not extra:
                    if previous is not None: self.assertEqual(previous, outcomes[0])
                    previous = outcomes[0]

    def test_malformed_replacement_apply_preserves_original_error_order(self):
        actual = r.apply(self.package, 'q', 'model design')
        variants = [None, [], 'plain', {}, {'patterns': [None]}]
        for rows in (None, 'plain', {}, [None], ['plain'], [[]], [{}]):
            for missing_status in (False, True):
                value = copy.deepcopy(actual); value['patterns'] = rows
                if missing_status: value.pop('status')
                variants.append(value)
        value = copy.deepcopy(actual); value.pop('patterns'); variants.append(value)
        for value in variants:
            outcomes = []
            for fallback in (False, True):
                guard = r._plain_json_tree
                with patch.object(r, 'apply', return_value=copy.deepcopy(value)) as apply, patch.object(r, '_plain_json_tree', side_effect=(lambda v: False) if fallback else guard):
                    try: result = ('OK', r.render(copy.deepcopy(self.package), 'q', 'model design'))
                    except Exception as exc: result = (type(exc).__name__, str(exc))
                self.assertEqual(apply.call_count, 1)
                outcomes.append(result)
            self.assertEqual(outcomes[0], outcomes[1], repr(value))
        class Dangerous(list):
            def __iter__(self): raise AssertionError('custom iteration')
            def __len__(self): raise AssertionError('custom length')
        for rules, patterns in (([], None), ([], Dangerous()), ([None], []), ([], ['x']), ([], [[]]), ([], [0] * 100_001)):
            self.assertIsNone(r._ordered_rule_groups(rules, patterns))

    def test_actual_custom_question_effect_count_is_unchanged(self):
        class Question(str):
            calls = 0
            def __str__(self): self.calls += 1; return super().__str__()
        results = []
        for fallback in (False, True):
            question = Question('question')
            guard = r._plain_json_tree
            with patch.object(r, '_plain_json_tree', side_effect=(lambda v: False) if fallback else guard), patch.object(r, '_ordered_rule_groups') as grouped:
                text = r.render(self.package, question, 'model design')
            grouped.assert_not_called()
            results.append((text, question.calls))
        self.assertEqual(results[0], results[1])


if __name__ == '__main__':
    unittest.main()
