"""Canned argument import walkthrough: local CLI history, not logical approval."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import argument_map
import argument_proposals
import synthetic_walkthrough as demo
from persona import payload_sha256
from tests.test_answer_walkthrough import inventory
from tests.test_journey_html import Document


class ArgumentWalkthroughTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.root = Path(cls.directory.name)/'합성 argument history'
        result = subprocess.run([sys.executable, str(demo.ROOT/'synthetic_walkthrough.py'), str(cls.root),
            '--candidate-source', 'offline-import', '--research-journey', '--recheck-sources',
            '--review-method-use', '--import-method-use', '--html-review', '--import-answers', '--import-arguments'],
            cwd=cls.directory.name, capture_output=True, timeout=120)
        if result.returncode:
            cls.directory.cleanup()
            raise AssertionError(result.stderr.decode('utf-8'))
        cls.receipt = json.loads(result.stdout)

    @classmethod
    def tearDownClass(cls): cls.directory.cleanup()

    def read(self, name): return json.loads((self.root/name).read_text(encoding='utf-8'))

    def test_full_route_has_53_real_commands_and_explicit_selected_existing_claims(self):
        self.assertEqual(self.receipt['command_count'], 53)
        self.assertEqual(self.receipt['argument_candidate_source'], 'offline-import')
        self.assertTrue(self.receipt['argument_import_is_synthetic_fixture'])
        self.assertEqual(self.receipt['argument_adoption_scope'], 'CANNED_FIXTURE_DECISIONS_NOT_LOGICAL_APPROVAL')
        self.assertEqual(self.receipt['read_first'][0], 'research-journey.html')
        self.assertIn('argument-proposals.txt', self.receipt['read_first'])
        commands = self.read('commands.json')
        self.assertEqual(len(commands), 53)
        self.assertTrue(all(row['returncode'] == 0 for row in commands))
        stages = [row['argv'][2] for row in commands if Path(row['argv'][1]).name == 'argument_proposals.py']
        self.assertEqual(stages, ['template', 'prepare', 'response-template', 'import', 'review-template', 'review', 'export'])
        self.assertEqual(self.read('empty-argument-scope.json')['selected_claim_ids'], [])
        self.assertEqual(self.read('synthetic-argument-scope.json')['selected_claim_ids'], ['criterion', 'comparison', 'conclusion'])
        selected = self.read('argument-handoff.json')['selected_claims']
        self.assertEqual([row['claim_id'] for row in selected], ['criterion', 'comparison', 'conclusion'])
        self.assertTrue(all('imported_answer_origin' in row for row in selected))
        self.assertEqual(self.read('empty-argument.json')['steps'], [])
        envelope = self.read('argument.json')
        self.assertEqual(set(envelope), {'schema', 'bundle', 'review'})
        self.assertEqual(envelope['schema'], argument_proposals.ENVELOPE_SCHEMA)
        self.assertEqual(envelope['bundle'], self.read('argument-candidates.json'))
        self.assertEqual(envelope['review'], self.read('synthetic-argument-adoption.json'))
        self.assertFalse((self.root/'FAILED.txt').exists())

    def test_declaration_order_topology_and_each_original_origin_are_preserved(self):
        result = self.read('research-journey.json')['argument_review']
        self.assertEqual(result['declared_step_ids'], ['late', 'early'])
        self.assertEqual([row['step_id'] for row in result['steps']], ['early', 'late'])
        self.assertEqual(result['review_order_claim_ids'], ['criterion', 'comparison', 'conclusion'])
        bundle = self.read('argument-candidates.json')
        decisions = self.read('synthetic-argument-adoption.json')['decisions']
        for step, index in zip(result['steps'], (1, 0)):
            with self.subTest(step=step['step_id']):
                origin = step['proposal_origin']
                self.assertEqual(origin['candidate_id'], bundle['candidates'][index]['candidate_id'])
                self.assertEqual(origin['original_proposal'], bundle['candidates'][index]['proposed_step'])
                self.assertEqual(origin['proposal_bundle_sha256'], payload_sha256(bundle))
                self.assertEqual(origin['review_sha256'], payload_sha256(self.read('synthetic-argument-adoption.json')))
                self.assertEqual(step['bridge_rationale'], decisions[index]['reviewed_step']['bridge_rationale'])
                self.assertNotEqual(step['bridge_rationale'], origin['original_proposal']['bridge_rationale'])
                self.assertEqual(step['origin'], 'OPERATOR_ADOPTED_IMPORTED_ARGUMENT')
                self.assertTrue(step['assumptions'])
                self.assertNotEqual(step['conclusion']['claim_type'], 'source_quote')
        self.assertIsNone(result['steps'][1]['defeater'])
        self.assertIn('defeater', result['steps'][1]['missing_fields'])

    def test_rejected_cycle_stays_history_and_would_fail_if_adopted(self):
        package, draft, envelope, final_review = (self.read(name) for name in
            ('revision.json', 'draft.json', 'argument.json', 'answer-review.json'))
        packet = argument_map.inspect(package, draft, envelope, final_review)['proposal_review']
        self.assertEqual([row['decision'] for row in packet['candidates']], ['accept', 'accept', 'reject'])
        self.assertIsNone(packet['candidates'][2]['reviewed_step'])
        rejected = envelope['bundle']['candidates'][2]['proposed_step']
        self.assertEqual((rejected['premise_claim_ids'], rejected['conclusion_claim_id']), (['conclusion'], 'comparison'))
        envelope['review']['decisions'][2].update(decision='accept', reviewed_step=dict(copy.deepcopy(rejected), step_id='reverse'))
        with self.assertRaisesRegex(ValueError, 'cycl'): argument_map.inspect(package, draft, envelope, final_review)

    def test_all_histories_survive_json_text_and_passive_static_html(self):
        report = self.read('research-journey.json')
        html = (self.root/'research-journey.html').read_text(encoding='utf-8')
        self.assertEqual(json.loads(Document(html).saved['complete-json']), report)
        self.assertTrue(report['source_recheck']['all_stored_quotes_match'])
        self.assertIn('proposal_review', report['method_application_review'])
        self.assertIn('proposal_review', report['method_application_review']['pattern_review'])
        self.assertIn('proposal_review', report['argument_review']['answer'])
        for output in (json.dumps(report), html, (self.root/'research-journey.txt').read_text(encoding='utf-8')):
            for phrase in ('Original canned late bridge', 'Original canned early bridge',
                    'The canned reviewer proposes', 'Rejected canned reverse bridge',
                    'Original canned answer comparison', 'Rejected synthetic answer overgeneralization',
                    'Canned synthetic model application rationale', 'Canned imported'):
                self.assertIn(phrase, output)

    def test_adoption_does_not_review_answers_or_transfer_citations_or_approve(self):
        self.assertEqual(self.receipt['answer_review_status'], 'ALL_DEFERRED')
        self.assertEqual(self.receipt['research_journey_answer_status'], 'DECLARED_REVIEW_INCOMPLETE')
        self.assertFalse(self.receipt['llm_used']); self.assertFalse(self.receipt['external_transmission'])
        self.assertTrue(all(row['decision'] == 'defer' for row in self.read('answer-review.json')['decisions']))
        self.assertTrue(all(row['decision'] == 'defer' and 'reviewed_step' not in row
            for row in self.read('deferred-argument-adoption.json')['decisions']))
        report = self.read('research-journey.json'); argument = report['argument_review']
        self.assertFalse(report['automatic_approval']); self.assertFalse(report['scientific_execution'])
        self.assertEqual(argument['logical_validation'], 'NOT_PERFORMED')
        packet = argument['proposal_review']
        self.assertFalse(packet['automatic_approval']); self.assertFalse(packet['scientific_execution'])
        self.assertFalse(packet['processing']['provider_invoked']); self.assertFalse(packet['processing']['external_transmission'])
        self.assertEqual(packet['logical_validation'], 'NOT_PERFORMED')
        self.assertEqual([row['claim_id'] for row in argument['answer']['claims']], ['criterion', 'comparison', 'conclusion'])
        for step in argument['steps']:
            self.assertEqual(step['citation_transfer'], 'NOT_PERFORMED')
            self.assertEqual(step['logical_validation'], 'NOT_PERFORMED')
            self.assertTrue(all(row['declared_review_decision'] == 'defer' for row in [*step['premises'], step['conclusion']]))
        self.assertEqual(argument['steps'][1]['conclusion']['direct_citation_count'], 0)

    def test_minimal_mock_32_and_offline_34_routes_use_manual_answer(self):
        for source, count in (('mock', 32), ('offline-import', 34)):
            with self.subTest(source=source), tempfile.TemporaryDirectory() as directory:
                target = Path(directory)/'minimal'; receipt = demo.run(target, candidate_source=source, research_journey=True, import_arguments=True)
                self.assertEqual(receipt['command_count'], count)
                self.assertNotIn('answer_candidate_source', receipt)
                self.assertNotIn('method_application_status', receipt)
                self.assertNotIn('current_source_recheck_status', receipt)
                self.assertFalse((target/'synthetic-sources').exists()); self.assertFalse((target/'research-journey.html').exists())
                handoff = json.loads((target/'argument-handoff.json').read_text())
                self.assertTrue(all('imported_answer_origin' not in row for row in handoff['selected_claims']))
                self.assertEqual([row['claim_id'] for row in handoff['selected_claims']], ['criterion', 'comparison', 'conclusion'])

    def test_flag_validation_precedes_writes_and_no_external_response_option(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)/'invalid'
            for options, message in ((dict(import_arguments=True), 'requires research_journey'),
                    (dict(research_journey=True, import_arguments='yes'), 'boolean'),
                    (dict(research_journey=True, import_arguments=1), 'boolean')):
                with self.assertRaisesRegex(ValueError, message): demo.run(target, **options)
                self.assertFalse(target.exists())
            for option in ('--argument-response', '--argument-review'):
                result = subprocess.run([sys.executable, str(demo.ROOT/'synthetic_walkthrough.py'), str(target),
                    '--research-journey', '--import-arguments', option, 'external.json'], capture_output=True)
                self.assertNotEqual(result.returncode, 0); self.assertFalse(target.exists())

    def test_all_seven_stage_failures_leave_no_complete_or_final_argument(self):
        original = demo.subprocess.run
        for stage in ('template', 'prepare', 'response-template', 'import', 'review-template', 'review', 'export'):
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as directory:
                target = Path(directory)/'failed'
                def fail(argv, **kwargs):
                    if Path(argv[1]).name == 'argument_proposals.py' and argv[2] == stage:
                        return subprocess.CompletedProcess(argv, 1, stdout=b'', stderr=b'Synthetic argument-stage failure')
                    return original(argv, **kwargs)
                with patch.object(demo.subprocess, 'run', side_effect=fail):
                    with self.assertRaisesRegex(ValueError, 'argument-stage failure'):
                        demo.run(target, research_journey=True, import_arguments=True)
                self.assertFalse((target/'COMPLETE.json').exists()); self.assertFalse((target/'argument.json').exists())
                self.assertTrue((target/'FAILED.txt').exists())
                commands = json.loads((target/'commands.json').read_text())
                self.assertEqual(commands[-1]['returncode'], 1); self.assertEqual(commands[-1]['argv'][2], stage)

    def test_fixture_guard_checks_every_candidate_field_and_template_row(self):
        changes = [('candidate_id', None), ('missing_candidate', None), ('missing_decision', None)]
        changes += [('proposal', field) for field in argument_proposals.PROPOSAL_FIELDS]
        changes += [(kind, index) for kind in ('decision', 'review_id', 'reviewed_step') for index in range(3)]
        for kind, field in changes:
            with self.subTest(kind=kind, field=field):
                writes = {}
                def command(script, args, output, json_output=True):
                    value = self.read(output) if json_output else (self.root/output).read_text(encoding='utf-8')
                    if output == 'argument-candidates.json':
                        if kind == 'candidate_id': value['candidates'][0]['candidate_id'] = 'other'
                        if kind == 'missing_candidate': value['candidates'].pop()
                        if kind == 'proposal': value['candidates'][0]['proposed_step'][field] = 'changed'
                    if output == 'deferred-argument-adoption.json':
                        if kind == 'missing_decision': value['decisions'].pop()
                        if kind == 'decision': value['decisions'][field]['decision'] = 'accept'
                        if kind == 'review_id': value['decisions'][field]['candidate_id'] = 'other'
                        if kind == 'reviewed_step': value['decisions'][field]['reviewed_step'] = None
                    return value
                with self.assertRaisesRegex(ValueError, 'fixture changed'):
                    demo._import_argument_fixture(command, lambda name, value: writes.update({name:value}), Path, 'revision.json')
                self.assertNotIn('synthetic-argument-adoption.json', writes)
                self.assertNotIn('argument.json', writes)

    def test_previous_39_and_46_stage_normalized_inventories_are_unchanged(self):
        # Independently captured before argument import. HTML comparison covers saved JSON and structure, never browser layout.
        golden = {False:'d89c01a04314f55a80b9c6eae57c70b215ab73a4a77a4ae70b0f7f94750c5b53',
                  True:'ed29b35f2b149758504893f7e49ccb3e0c56fb7fb1feea77629539dc54e87c19'}
        for import_answers, expected in golden.items():
            with self.subTest(import_answers=import_answers), tempfile.TemporaryDirectory() as directory:
                target = Path(directory)/'legacy'; receipt = demo.run(target, candidate_source='offline-import',
                    research_journey=True, recheck_sources=True, review_method_use=True, import_method_use=True,
                    html_review=True, import_answers=import_answers)
                self.assertEqual(receipt['command_count'], 46 if import_answers else 39)
                self.assertNotIn('argument_candidate_source', receipt)
                self.assertEqual(payload_sha256(inventory(target)), expected)


if __name__ == '__main__': unittest.main()
