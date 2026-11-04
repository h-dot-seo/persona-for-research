"""Fixed, offline contextual answer demonstration and fail-closed fixture guards."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import answer_proposals
import argument_proposals
import synthetic_walkthrough as demo
from persona import payload_sha256
from test_answer_walkthrough import inventory
from test_journey_html import Document


FULL = dict(candidate_source='offline-import', research_journey=True, recheck_sources=True,
    review_method_use=True, import_method_use=True, html_review=True, import_answers=True,
    import_arguments=True, contextual_answers=True)


class ContextualWalkthroughTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.root = Path(cls.directory.name)/'contextual full'
        cls.receipt = demo.run(cls.root, **FULL)

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def read(self, name):
        return json.loads((self.root/name).read_text(encoding='utf-8'))

    def test_full_route_keeps_53_commands_and_deferred_review(self):
        self.assertEqual(self.receipt['command_count'], 53)
        self.assertEqual(self.receipt['recorded_answer_context_status'], 'SAME_RECORDED_ARTIFACTS')
        self.assertEqual(self.receipt['answer_review_status'], 'ALL_DEFERRED')
        self.assertEqual(self.receipt['research_journey_answer_status'], 'DECLARED_REVIEW_INCOMPLETE')
        self.assertFalse(self.receipt['llm_used'])
        self.assertFalse(self.receipt['external_transmission'])
        self.assertTrue(all(row['decision'] == 'defer' for row in self.read('answer-review.json')['decisions']))
        self.assertIn('equality is not approval or model use', (self.root/'START_HERE.txt').read_text(encoding='utf-8'))
        self.assertFalse((self.root/'FAILED.txt').exists())

    def test_preparation_precedes_answer_template_and_is_not_repeated(self):
        commands = self.read('commands.json')
        outputs = [row['output'] for row in commands]
        self.assertEqual(len(outputs), len(set(outputs)))
        for name in ('reviewed-patterns.json', 'deferred-context.json', 'empty-publication-relations.json'):
            self.assertLess(outputs.index('empty-proposal.json'), outputs.index(name))
            self.assertLess(outputs.index(name), outputs.index('empty-draft.json'))
        self.assertLess(outputs.index('empty-draft.json'), outputs.index('empty-answer-scope.json'))
        self.assertLess(outputs.index('draft.json'), outputs.index('research-journey.json'))
        args = next(row['argv'] for row in commands if row['output'] == 'empty-answer-scope.json')
        for option in ('--include-citation-explanations', '--patterns', '--context', '--publication-relations', '--pattern-id'):
            self.assertEqual(args.count(option), 1)
        self.assertTrue(all(row['returncode'] == 0 for row in commands))

    def test_raw_context_equals_exact_later_files_and_no_approval(self):
        scope = self.read('synthetic-answer-scope.json')
        self.assertEqual(scope['schema'], 'persona.answer-proposal-scope.v3')
        raw = scope['research_context']
        self.assertEqual(raw, dict(patterns=self.read('reviewed-patterns.json'), context=self.read('synthetic-context.json'),
            publication_relations=self.read('synthetic-publication-relations.json'), pattern_id='synthetic-comparison'))
        comparison = self.read('research-journey.json')['recorded_answer_context_comparison']
        self.assertEqual(comparison['status'], 'SAME_RECORDED_ARTIFACTS')
        self.assertEqual(comparison['changed_fields'], [])
        self.assertFalse(comparison['model_use_verified']); self.assertFalse(comparison['automatic_rebinding'])
        self.assertTrue(all(row['recorded_sha256'] == row['current_sha256'] for row in comparison['artifacts']))

    def test_three_explicit_refs_unchanged_and_context_parent_uncitable(self):
        link = self.read('links.json')['links'][0]
        refs = [link['to_ref'], link['from_ref'], dict(link['to_ref'], dimension=None)]
        scope = self.read('synthetic-answer-scope.json')
        self.assertEqual(scope['evidence_refs'], refs)
        parent = dict(link['from_ref'], dimension=None)
        self.assertNotIn(parent, refs)
        response = self.read('synthetic-answer-response.json')
        response['candidates'][1]['citations'][0]['reference'] = parent
        with self.assertRaises(ValueError):
            answer_proposals.import_response(self.read('revision.json'), scope, self.read('answer-handoff.json'),
                response, self.read('synthetic-answer-provenance.json'))

    def test_explanation_slots_and_original_revised_history(self):
        original = self.read('synthetic-answer-response.json')['candidates']
        adopted = [row['reviewed_claim'] for row in self.read('synthetic-answer-adoption.json')['decisions'][:3]]
        for claim in original + adopted:
            self.assertTrue(all('explanation' in citation for citation in claim['citations']))
        self.assertIsNone(original[0]['citations'][0]['explanation'])
        self.assertIsNone(original[3]['citations'][0]['explanation'])
        self.assertIn('Original canned', original[1]['citations'][0]['explanation']['rationale'])
        self.assertIn('Revised canned', adopted[1]['citations'][0]['explanation']['rationale'])
        for name in ('answer-proposals.txt', 'research-journey.txt', 'research-journey.html'):
            text = (self.root/name).read_text(encoding='utf-8')
            self.assertIn('Original canned interpretation', text)
            self.assertIn('Revised canned interpretation', text)
            self.assertIn('Rejected synthetic answer overgeneralization', text)

    def test_history_never_promotes_citations_or_conclusion(self):
        report = self.read('research-journey.json')
        self.assertTrue(report['source_recheck']['all_stored_quotes_match'])
        answer = report['argument_review']['answer']
        self.assertEqual(answer['claims'][0]['origin'], 'OPERATOR_ADOPTED_IMPORTED_SOURCE_QUOTE')
        self.assertEqual(answer['claims'][-1]['citations'], [])
        self.assertEqual(answer['proposal_review']['candidates'][-1]['decision'], 'reject')
        rejected = self.read('synthetic-answer-response.json')['candidates'][-1]['citations'][0]['reference']
        route = next(row for row in report['evidence_routes'] if row['evidence']['reference'] == rejected)
        self.assertFalse(route['actively_used_in_answer_or_design'])
        self.assertEqual(route['direct_argument_uses'], [])
        self.assertFalse(report['automatic_approval']); self.assertFalse(report['scientific_execution'])

    def test_late_bridge_basis_keeps_claim_types_and_citation_roles(self):
        report = self.read('research-journey.json')
        argument = report['argument_review']
        late = next(row for row in argument['steps'] if row['step_id'] == 'late')
        self.assertEqual(late['premise_claim_ids'], ['comparison'])
        self.assertEqual(late['conclusion_claim_id'], 'conclusion')
        self.assertEqual(late['bridge_rationale'],
            'The canned reviewer proposes choosing an observation only after the synthetic comparison.')
        self.assertEqual(late['assumptions'],
            ['The proposed comparison can identify a discriminating observation.'])
        self.assertIsNone(late['defeater'])
        self.assertEqual(late['missing_fields'], ['defeater'])
        self.assertNotEqual(late['bridge_rationale'], late['proposal_origin']['original_proposal']['bridge_rationale'])
        self.assertEqual(late['citation_transfer'], 'NOT_PERFORMED')
        self.assertEqual(late['logical_validation'], 'NOT_PERFORMED')
        claims = {row['claim_id']: row for row in argument['answer']['claims']}
        self.assertEqual({key: row['claim_type'] for key, row in claims.items()},
            dict(criterion='source_quote', comparison='operator_synthesis', conclusion='operator_synthesis'))
        citations = {row['role']: row for row in claims['comparison']['citations']}
        self.assertEqual(set(citations), {'support', 'challenge'})
        for role, paper, dimension, kind, component_type in (
                ('support', 'synthetic-0', 'alternative_explanation', 'research', 'operator_interpretation'),
                ('challenge', 'synthetic-1', 'falsification_check', 'review', 'explicit_statement')):
            evidence = citations[role]['evidence']
            self.assertEqual(evidence['reference'], dict(paper_id=paper, observation_index=0, dimension=dimension))
            self.assertEqual(evidence['source_kind'], kind)
            self.assertEqual(evidence['observation']['condition'], 'models predict distinct outcomes')
            self.assertEqual(evidence['observation']['limitation'], 'simulation only; no real author attribution')
            self.assertEqual(evidence['component']['claim_type'], component_type)
        self.assertEqual(citations['support']['explanation'], dict(
            rationale='Revised canned interpretation of this synthetic comparison citation only.',
            context_boundary='Invented demonstration only; applicability remains untested.'))
        self.assertIsNone(citations['challenge']['explanation'])
        self.assertEqual(claims['criterion']['citations'][0]['evidence']['reference'],
            citations['challenge']['evidence']['reference'])
        self.assertEqual(claims['conclusion']['citations'], [])
        self.assertTrue(all(row['decision'] == 'defer' for row in self.read('answer-review.json')['decisions']))

    def test_late_routes_match_exact_reference_claim_and_roles(self):
        report = self.read('research-journey.json')
        claims = {row['claim_id']: row for row in report['argument_review']['answer']['claims']}
        all_late_uses = []
        for citation in claims['comparison']['citations']:
            reference = citation['evidence']['reference']
            route = next(row for row in report['evidence_routes'] if row['evidence']['reference'] == reference)
            uses = [row for row in route['direct_argument_uses'] if row['step_id'] == 'late']
            self.assertEqual([(row['step_id'], row['claim_id'], row['argument_role'], row['citation_role'])
                for row in uses], [('late', 'comparison', 'premise', citation['role'])])
            self.assertEqual(uses[0]['explanation'], citation['explanation'])
            self.assertEqual(uses[0]['declared_review_decision'], 'defer')
            self.assertEqual([row['step_id'] for row in route['method_application_uses']], ['compare'])
            all_late_uses.extend(uses)
        self.assertEqual(len(all_late_uses), 2)
        self.assertEqual([row for route in report['evidence_routes'] for row in route['direct_argument_uses']
            if row['claim_id'] == 'conclusion'], [])
        self.assertEqual({row['step_id'] for row in report['method_application_review']['applications']}, {'compare'})
        parent = dict(claims['comparison']['citations'][0]['evidence']['reference'], dimension=None)
        route = next(row for row in report['evidence_routes'] if row['evidence']['reference'] == parent)
        self.assertEqual(route['direct_argument_uses'], [])

    def test_fresh_note_only_bridge_review_stays_deferred_and_preserves_files(self):
        before = {path.name: path.read_bytes() for path in self.root.iterdir() if path.is_file()}
        package, draft = self.read('revision.json'), self.read('draft.json')
        bundle, answer_review = self.read('argument-candidates.json'), self.read('answer-review.json')
        original_inputs = copy.deepcopy([package, draft, bundle, answer_review])
        review = argument_proposals.review_template(package, draft, bundle, 'reader', answer_review)
        late = next(row for row in self.read('research-journey.json')['argument_review']['steps'] if row['step_id'] == 'late')
        decision = next(row for row in review['decisions'] if row['candidate_id'] == late['proposal_origin']['candidate_id'])
        decision['review_note'] = ('Bounded review of the fixture late bridge: separate support and challenge citations; '
            'challenge explanation and bridge defeater missing. Applicability untested. Keep deferred.')
        packet = argument_proposals.review_proposals(package, draft, bundle, review, answer_review)
        self.assertEqual(packet['status'], 'ARGUMENT_PROPOSAL_REVIEW_INCOMPLETE')
        self.assertEqual(packet['accepted_count'], 0)
        self.assertEqual(packet['deferred_count'], len(bundle['candidates']))
        self.assertTrue(all(row['decision'] == 'defer' and row['reviewed_step'] is None for row in packet['candidates']))
        self.assertIn(decision['review_note'], argument_proposals.render_review(packet))
        self.assertFalse(packet['automatic_approval'])
        self.assertEqual(packet['logical_validation'], 'NOT_PERFORMED')
        with self.assertRaisesRegex(ValueError, 'resolve every candidate'):
            argument_proposals.export_reviewed(package, draft, bundle, review, answer_review)
        self.assertEqual([package, draft, bundle, answer_review], original_inputs)
        self.assertEqual({path.name: path.read_bytes() for path in self.root.iterdir() if path.is_file()}, before)

    def test_html_is_passive_snapshot(self):
        document = Document((self.root/'research-journey.html').read_text(encoding='utf-8'))
        self.assertEqual(json.loads(document.saved['complete-json']), self.read('research-journey.json'))
        self.assertNotIn('form', document.tags); self.assertNotIn('iframe', document.tags)
        self.assertTrue(all(not key.lower().startswith('on') for _, attrs in document.attributes for key in attrs))
        self.assertTrue(all(href.startswith('#') for href in document.hrefs))

    def test_minimal_mock_and_offline_routes(self):
        for source, count in (('mock', 32), ('offline-import', 34)):
            with self.subTest(source=source), tempfile.TemporaryDirectory() as directory:
                target = Path(directory)/'minimal'
                receipt = demo.run(target, candidate_source=source, research_journey=True, import_answers=True, contextual_answers=True)
                self.assertEqual(receipt['command_count'], count)
                self.assertEqual(receipt['recorded_answer_context_status'], 'SAME_RECORDED_ARTIFACTS')
                self.assertNotIn('current_source_recheck_status', receipt)
                self.assertFalse((target/'synthetic-sources').exists())

    def test_validation_is_prewrite(self):
        cases = [dict(contextual_answers=value) for value in (None, 0, 1, 'yes', [], {})]
        cases += [dict(contextual_answers=True), dict(contextual_answers=True, research_journey=True),
            dict(contextual_answers=True, import_answers=True)]
        for name in ('research_journey', 'import_answers', 'import_arguments', 'html_review', 'recheck_sources', 'review_method_use', 'import_method_use'):
            cases.append(dict(FULL, **{name:'yes'}))
        cases.append(dict(FULL, candidate_source='provider'))
        for options in cases:
            with self.subTest(options=options), tempfile.TemporaryDirectory() as directory:
                target = Path(directory)/'invalid'
                with self.assertRaises(ValueError): demo.run(target, **options)
                self.assertFalse(target.exists())

    def test_cli_rejects_external_inputs_and_missing_prerequisites_prewrite(self):
        cases = [[], ['--research-journey'], ['--import-answers']]
        cases += [['--research-journey', '--import-answers', option, 'external.json'] for option in
            ('--answer-response', '--patterns', '--context', '--publication-relations', '--provider', '--browser')]
        for args in cases:
            with self.subTest(args=args), tempfile.TemporaryDirectory() as directory:
                target = Path(directory)/'invalid'
                result = subprocess.run([sys.executable, str(demo.ROOT/'synthetic_walkthrough.py'), str(target),
                    '--contextual-answers', *args], capture_output=True)
                self.assertNotEqual(result.returncode, 0); self.assertFalse(target.exists())

    def replay(self, target, *, fail_output=None, mutation=None):
        commands = iter(self.read('commands.json'))
        def replay_command(argv, **kwargs):
            row = next(commands)
            self.assertEqual(Path(argv[1]).name, Path(row['argv'][1]).name)
            if row['output'] == fail_output:
                return subprocess.CompletedProcess(argv, 1, stdout=b'', stderr=b'Injected fixture failure')
            text = (self.root/row['output']).read_text(encoding='utf-8')
            if mutation and row['output'] == mutation[0]:
                value = json.loads(text); mutation[1](value); text = json.dumps(value)
            return subprocess.CompletedProcess(argv, 0, stdout=text.encode(), stderr=b'')
        with patch.object(demo.subprocess, 'run', side_effect=replay_command):
            return demo.run(target, **FULL)

    def test_every_preparation_and_answer_stage_failure_prevents_completion(self):
        outputs = [row['output'] for row in self.read('commands.json') if Path(row['argv'][1]).name in
            ('pattern_proposals.py', 'applicability_review.py', 'publication_context.py', 'answer_proposals.py')]
        for output in outputs:
            with self.subTest(output=output), tempfile.TemporaryDirectory() as directory:
                target = Path(directory)/'failed'
                with self.assertRaisesRegex(ValueError, 'Injected fixture failure'): self.replay(target, fail_output=output)
                self.assertFalse((target/'COMPLETE.json').exists()); self.assertFalse((target/'draft.json').exists())
                self.assertTrue((target/'FAILED.txt').exists())
                commands = json.loads((target/'commands.json').read_text(encoding='utf-8'))
                self.assertEqual(commands[-1]['output'], output); self.assertEqual(commands[-1]['returncode'], 1)

    def test_comparison_mismatch_blocks_complete(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)/'mismatch'
            with self.assertRaisesRegex(ValueError, 'must match'):
                self.replay(target, mutation=('research-journey.json', lambda value:
                    value['recorded_answer_context_comparison'].update(status='DIFFERENT_SUPPLIED_ARTIFACTS')))
            self.assertFalse((target/'COMPLETE.json').exists()); self.assertTrue((target/'FAILED.txt').exists())

    def test_every_preparation_guard_rejects_mutations_before_canned_write(self):
        mutations = [
            ('pattern-candidates.json', lambda v:v['candidates'].pop(), 'synthetic-pattern-review.json'),
            ('pattern-candidates.json', lambda v:v['candidates'][0].update(candidate_id='other'), 'synthetic-pattern-review.json'),
            ('pattern-candidates.json', lambda v:v['candidates'][0]['proposed_pattern'].update(uncertainty='changed'), 'synthetic-pattern-review.json'),
            ('deferred-pattern-review.json', lambda v:v['decisions'].pop(), 'synthetic-pattern-review.json'),
            ('deferred-pattern-review.json', lambda v:v['decisions'].reverse(), 'synthetic-pattern-review.json'),
            ('deferred-pattern-review.json', lambda v:v['decisions'][0].update(decision='accept'), 'synthetic-pattern-review.json'),
            ('deferred-pattern-review.json', lambda v:v['decisions'][0].update(review_note='changed'), 'synthetic-pattern-review.json'),
            ('deferred-pattern-review.json', lambda v:v['decisions'][0].update(reviewed_pattern=None), 'synthetic-pattern-review.json'),
            ('deferred-context.json', lambda v:v['assessments'].pop(), 'synthetic-context.json'),
            ('deferred-context.json', lambda v:v['assessments'].reverse(), 'synthetic-context.json'),
            ('deferred-context.json', lambda v:v['assessments'][0]['reference'].update(dimension='uncertainty'), 'synthetic-context.json'),
            ('deferred-context.json', lambda v:v['assessments'][0].update(decision='include'), 'synthetic-context.json'),
            ('deferred-context.json', lambda v:v['assessments'][0].update(context_comparison='changed'), 'synthetic-context.json'),
            ('deferred-context.json', lambda v:v['assessments'][0].update(remaining_uncertainty='changed'), 'synthetic-context.json'),
            ('deferred-context.json', lambda v:v['assessments'][0].update(counterevidence_refs=[{}]), 'synthetic-context.json'),
            ('empty-publication-relations.json', lambda v:v['relations'].append({}), 'synthetic-publication-relations.json')]
        for field in self.read('pattern-candidates.json')['candidates'][0]['proposed_pattern']:
            mutations.append(('pattern-candidates.json', lambda v, field=field:
                v['candidates'][0]['proposed_pattern'].update({field:'Unexpected fixture field'}),
                'synthetic-pattern-review.json'))
        for name, mutate, blocked in mutations:
            with self.subTest(name=name, blocked=blocked):
                writes = {}
                def command(script, args, output, json_output=True):
                    value = self.read(output) if json_output else (self.root/output).read_text(encoding='utf-8')
                    if output == name: mutate(value)
                    return value
                with self.assertRaisesRegex(ValueError, 'fixture changed|contract changed'):
                    demo._prepare_research_context_fixture(command, lambda n,v:writes.update({n:copy.deepcopy(v)}),
                        Path, 'revision.json', self.read('links.json'))
                self.assertNotIn(blocked, writes)

    def test_missing_extra_or_nondeferred_final_claims_block_complete(self):
        mutations = [lambda rows:rows.clear(), lambda rows:rows.pop(),
            lambda rows:rows.append(copy.deepcopy(rows[0])), lambda rows:rows[0].update(claim_id='other'),
            lambda rows:rows[0].update(decision='retain')]
        for mutate in mutations:
            with self.subTest(mutation=mutate), tempfile.TemporaryDirectory() as directory:
                target = Path(directory)/'bad-final-review'
                def change(value):
                    mutate(value['pattern_transfer_review']['answer_design_review']['answer']['review']['decisions'])
                with self.assertRaisesRegex(ValueError, 'synthetic contextual answer review|remain deferred'):
                    self.replay(target, mutation=('research-journey.json', change))
                self.assertFalse((target/'COMPLETE.json').exists())
                self.assertTrue((target/'FAILED.txt').exists())

    def test_answer_helper_rejects_nonboolean_before_commands(self):
        with self.assertRaisesRegex(ValueError, 'boolean'):
            demo._import_answer_fixture(None, None, None, None, None, None, contextual_answers=1)

    def test_contextual_answer_fixture_guards_keep_adoption_unwritten(self):
        manual = self.read('empty-draft.json')
        manual['claims'] = [copy.deepcopy(row['reviewed_claim']) for row in
            self.read('synthetic-answer-adoption.json')['decisions'][:3]]
        mutations = [
            ('answer-candidates.json', lambda v:v['candidates'][0].update(candidate_id='other')),
            ('answer-candidates.json', lambda v:v['candidates'][1]['proposed_claim']['citations'][0].update(explanation=None)),
            ('deferred-answer-adoption.json', lambda v:v['decisions'].pop()),
            ('deferred-answer-adoption.json', lambda v:v['decisions'][0].update(candidate_id='other')),
            ('deferred-answer-adoption.json', lambda v:v['decisions'][0].update(decision='accept')),
            ('deferred-answer-adoption.json', lambda v:v['decisions'][0].update(reviewed_claim=None))]
        for name, mutate in mutations:
            with self.subTest(name=name):
                writes = {}
                def command(script, args, output, json_output=True):
                    value = self.read(output) if json_output else (self.root/output).read_text(encoding='utf-8')
                    if output == name: mutate(value)
                    return value
                with self.assertRaisesRegex(ValueError, 'fixture changed'):
                    demo._import_answer_fixture(command, lambda n,v:writes.update({n:copy.deepcopy(v)}),
                        Path, 'revision.json', self.read('links.json'), manual, contextual_answers=True)
                self.assertNotIn('synthetic-answer-adoption.json', writes)

    def test_legacy_full_53_inventory_is_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)/'legacy'
            receipt = demo.run(target, **dict(FULL, contextual_answers=False))
            self.assertEqual(receipt['command_count'], 53)
            self.assertNotIn('contextual_answers', receipt)
            self.assertEqual(payload_sha256(inventory(target)), '9094cc2777d40d4ab460ed7bae0b08ef007683d44619e4ded9730857cdb78aad')


if __name__ == '__main__': unittest.main()
