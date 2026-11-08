import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from design_scenario import review, render, template
from extraction_adapter import MockProvider
from observation_input import verified_corpus
from persona import payload_sha256
from reasoning_links import template as link_template
from research_workflow import build


class DesignScenarioTests(unittest.TestCase):
    def setUp(self):
        self.corpus = json.loads(Path('examples/reasoning-corpus.json').read_text())
        paper = self.corpus['papers'][1]
        paper['segments']['synthetic criterion'] = 'A shared prediction does not discriminate the models.'
        paper['segments_sha256'] = payload_sha256(paper['segments'])
        paper['observations'][0]['stance'] = 'challenge'
        paper['observations'][0]['reasoning'] = dict(falsification_check=dict(
            text='Check whether predictions are distinguishable.', locator='synthetic criterion',
            evidence_quote='A shared prediction does not discriminate the models.', claim_type='explicit_statement'))
        self.package = build(verified_corpus(self.corpus))
        self.links = link_template(self.package, 'synthetic-link-operator')
        self.links['links'] = [dict(link_id='criterion-link', relation='qualifies',
            from_ref=dict(paper_id='synthetic-1', observation_index=0, dimension='falsification_check'),
            to_ref=dict(paper_id='synthetic-0', observation_index=0, dimension='alternative_explanation'),
            rationale='The later synthetic criterion limits the discriminating value of the earlier comparison.',
            claim_type='operator_interpretation')]
        self.proposal = template(self.package, self.links, 'Which observation would distinguish two synthetic models?', 'synthetic-design-operator')
        self.step = dict(step_id='design-1', proposed_action='Compare the two models on a synthetic observation with different predicted outcomes.',
            rationale='Use the supplied contrast criterion to inspect the proposed comparison.',
            hypothesis='The models predict different observable outcomes.', falsification_check=None,
            alternative_explanation=None, uncertainty='No actual model outputs have been evaluated.',
            link_uses=[dict(link_id='criterion-link', role='constraint',
                applicability_note='The operator proposes checking that the selected observation could discriminate the two models.')])
        self.proposal['steps'] = [self.step]

    def test_design_uses_later_criterion_without_attributing_proposal_to_author(self):
        result = review(self.package, self.links, self.proposal)
        step = result['steps'][0]
        self.assertEqual(step['claim_type'], 'operator_proposal')
        self.assertEqual(step['link_uses'][0]['role'], 'constraint')
        evidence = result['evidence_links']['links'][0]
        self.assertEqual(evidence['relation'], 'qualifies')
        self.assertEqual(evidence['claim_type'], 'operator_interpretation')
        self.assertEqual(evidence['from_evidence']['component']['claim_type'], 'explicit_statement')
        self.assertEqual(evidence['to_evidence']['component']['claim_type'], 'operator_interpretation')
        self.assertEqual(result['operator_id'], 'synthetic-design-operator')
        self.assertEqual(result['evidence_links']['operator_id'], 'synthetic-link-operator')
        self.assertFalse(result['llm_used'])
        self.assertFalse(result['canonical_update_performed'])

    def test_missing_falsification_is_not_borrowed_from_cited_source(self):
        result = review(self.package, self.links, self.proposal)
        step = result['steps'][0]
        self.assertIsNone(step['falsification_check'])
        self.assertIn('falsification_check', step['missing_fields'])
        self.assertIn('alternative_explanation', step['missing_fields'])
        self.assertIsNotNone(result['evidence_links']['links'][0]['from_evidence']['component'])
        self.assertIn('Filled fields do not establish sound design', result['boundary'])

    def test_unlinked_steps_and_unreferenced_counterevidence_are_visible(self):
        challenge = copy.deepcopy(self.links['links'][0])
        challenge.update(link_id='challenge-link', relation='challenges')
        self.links['links'].append(challenge)
        self.proposal = template(self.package, self.links, self.proposal['question'], 'synthetic-design-operator')
        self.proposal['steps'] = [self.step]
        result = review(self.package, self.links, self.proposal)
        self.assertEqual(result['unreferenced_link_ids'], ['challenge-link'])
        self.assertEqual(result['evidence_links']['links'][1]['relation'], 'challenges')
        self.step['link_uses'] = []
        result = review(self.package, self.links, self.proposal)
        self.assertEqual(result['steps'][0]['evidence_status'], 'NO_LINKED_EVIDENCE_SUPPLIED')
        self.assertEqual(result['unreferenced_link_ids'], ['criterion-link', 'challenge-link'])
        text = render(self.package, self.links, self.proposal)
        self.assertIn('challenge-link: challenges [operator_interpretation]', text)

    def test_changed_package_or_link_artifact_rejects_stale_proposal(self):
        links = copy.deepcopy(self.links)
        links['links'][0]['rationale'] += ' Changed interpretation.'
        with self.assertRaises(ValueError):
            review(self.package, links, self.proposal)
        package = copy.deepcopy(self.package)
        package['persona']['build_id'] = package['knowledge']['build_id'] = 'new-build'
        package['knowledge']['persona_payload_sha256'] = payload_sha256(package['persona'])
        with self.assertRaises(ValueError):
            review(package, self.links, self.proposal)
        package = copy.deepcopy(self.package)
        package['knowledge']['papers'][0]['split'] = 'holdout'
        package['persona']['knowledge_papers_sha256'] = payload_sha256(package['knowledge']['papers'])
        package['knowledge']['persona_payload_sha256'] = payload_sha256(package['persona'])
        with self.assertRaises(ValueError):
            template(package, self.links, 'Question', 'synthetic-operator')

    def test_strict_schema_unknown_ids_roles_duplicate_steps_and_bounds(self):
        for key, value in [('proposed_action', ''), ('falsification_check', ''),
                           ('rationale', 'x' * 2001), ('author_claim', 'invented')]:
            bad = copy.deepcopy(self.proposal); bad['steps'][0][key] = value
            with self.assertRaises(ValueError):
                review(self.package, self.links, bad)
        for key, value in [('link_id', 'unknown'), ('role', 'author_recommends'), ('applicability_note', None), ('extra', 'unlisted')]:
            bad = copy.deepcopy(self.proposal); bad['steps'][0]['link_uses'][0][key] = value
            with self.assertRaises(ValueError):
                review(self.package, self.links, bad)
        for mode in ('steps', 'uses'):
            bad = copy.deepcopy(self.proposal)
            if mode == 'steps': bad['steps'].append(copy.deepcopy(bad['steps'][0]))
            else: bad['steps'][0]['link_uses'].append(copy.deepcopy(bad['steps'][0]['link_uses'][0]))
            with self.assertRaises(ValueError):
                review(self.package, self.links, bad)

    def test_roles_remain_explicit_and_multiple_roles_are_not_independent_evidence(self):
        self.step['link_uses'][0]['role'] = 'motivation'
        other = copy.deepcopy(self.step['link_uses'][0]); other['role'] = 'counterargument'
        self.step['link_uses'].append(other)
        result = review(self.package, self.links, self.proposal)
        self.assertEqual([u['role'] for u in result['steps'][0]['link_uses']], ['motivation', 'counterargument'])
        self.assertEqual(result['steps'][0]['distinct_link_count'], 1)
        self.assertEqual(result['evidence_links']['links'][0]['relation'], 'qualifies')

    def test_empty_template_has_no_inferred_design(self):
        proposal = template(self.package, self.links, 'Question', 'synthetic-operator')
        self.assertEqual(proposal['steps'], [])
        result = review(self.package, self.links, proposal)
        self.assertEqual(result['status'], 'NO_PROPOSED_STEPS')
        self.assertEqual(result['unreferenced_link_ids'], ['criterion-link'])

    def test_aliases_json_equivalence_and_read_only_no_provider_or_source_access(self):
        second = self.step.copy(); second['step_id'] = 'design-2'
        self.proposal['steps'].append(second)
        before = copy.deepcopy((self.package, self.links, self.proposal))
        with patch.object(MockProvider, 'extract', side_effect=AssertionError('provider called')), \
             patch.object(Path, 'read_text', side_effect=AssertionError('source opened')):
            result = review(self.package, self.links, self.proposal)
            equivalent = review(self.package, self.links, json.loads(json.dumps(self.proposal)))
        self.assertEqual(result, equivalent)
        result['steps'][0]['link_uses'][0]['applicability_note'] = 'edited output'
        self.assertNotEqual(result['steps'][1]['link_uses'][0]['applicability_note'], 'edited output')
        self.assertEqual((self.package, self.links, self.proposal), before)

    def test_text_preserves_missing_fields_and_escapes_controls(self):
        self.proposal['question'] = '합성 질문\nFORGED\x1b[31m'
        text = render(self.package, self.links, self.proposal)
        self.assertIn('합성 질문\\u000aFORGED\\u001b[31m', text)
        self.assertNotIn('\x1b', text)
        self.assertIn('falsification_check: NOT_SUPPLIED', text)
        self.assertIn('Link use criterion-link [constraint]', text)
        self.assertIn('synthetic-1 / observation 0 / falsification_check', text)
        self.assertIn('Component [explicit_statement]', text)
        self.assertIn('not rechecked here', text)

    def test_cli_intake_links_to_empty_template_explicit_design_and_review(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            corpus, package, links, proposal = [root / name for name in ('corpus.json', 'package.json', 'links.json', 'proposal.json')]
            corpus.write_text(json.dumps(self.corpus))
            intake = subprocess.run([sys.executable, 'observation_input.py', str(corpus), '--question', 'Question', '--topic', 'model design'],
                capture_output=True, text=True, timeout=20)
            self.assertEqual(intake.returncode, 0, intake.stderr); package.write_text(intake.stdout)
            empty_links = subprocess.run([sys.executable, 'reasoning_links.py', str(package), '--template', '--operator-id', 'synthetic-link-operator'],
                capture_output=True, text=True, timeout=20)
            self.assertEqual(empty_links.returncode, 0, empty_links.stderr)
            supplied = json.loads(empty_links.stdout); supplied['links'] = self.links['links']; links.write_text(json.dumps(supplied))
            command = [sys.executable, 'design_scenario.py', str(package), str(links)]
            empty = subprocess.run(command + ['--template', '--question', self.proposal['question'], '--operator-id', 'synthetic-design-operator'],
                capture_output=True, text=True, timeout=20)
            self.assertEqual(empty.returncode, 0, empty.stderr)
            design = json.loads(empty.stdout); self.assertEqual(design['steps'], [])
            design['steps'] = [self.step]; proposal.write_text(json.dumps(design))
            for format in ('json', 'text'):
                output = subprocess.run(command + [str(proposal), '--format', format], capture_output=True, text=True, timeout=20)
                self.assertEqual(output.returncode, 0, output.stderr)
                self.assertIn('criterion-link', output.stdout); self.assertIn('synthetic-1', output.stdout)
            for extras in ([], [str(proposal), '--template'], [str(proposal), '--question', 'other'], ['--template', '--format', 'text']):
                failed = subprocess.run(command + extras, capture_output=True, text=True, timeout=20)
                self.assertNotEqual(failed.returncode, 0); self.assertEqual(failed.stdout, '')
            design['steps'][0]['link_uses'][0]['link_id'] = 'unknown'; proposal.write_text(json.dumps(design))
            failed = subprocess.run(command + [str(proposal)], capture_output=True, text=True, timeout=20)
            self.assertNotEqual(failed.returncode, 0); self.assertEqual(failed.stdout, '')


if __name__ == '__main__':
    unittest.main()
