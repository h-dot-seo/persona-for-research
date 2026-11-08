import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import test_design_scenario as fixture
from design_scenario import template
from extraction_adapter import MockProvider
from publication_scope import audit, render
from persona import payload_sha256


class PublicationScopeTests(unittest.TestCase):
    def setUp(self):
        case = fixture.DesignScenarioTests(); case.setUp()
        self.package, self.links, self.proposal = case.package, case.links, case.proposal
        self.years = [p['year'] for p in self.package['knowledge']['papers']]

    def run_audit(self, year):
        return audit(self.package, self.links, self.proposal, year)

    def test_later_review_checked_even_when_link_points_backwards(self):
        result = self.run_audit(min(self.years))
        step = result['steps'][0]
        self.assertEqual(step['status'], 'AFTER_REFERENCE_YEAR_LINK_USED')
        nodes = step['link_uses'][0]['evidence']['endpoints']
        self.assertEqual(nodes[0]['publication_scope'], 'AFTER_REFERENCE_YEAR')
        self.assertEqual(nodes[0]['evidence']['source_kind'], 'review')
        self.assertEqual(nodes[1]['publication_scope'], 'SAME_YEAR_ORDER_UNRESOLVED')
        self.assertEqual(nodes[0]['evidence']['component']['claim_type'], 'explicit_statement')
        self.assertEqual(nodes[1]['evidence']['component']['claim_type'], 'operator_interpretation')
        self.assertIn('falsification_check', step['missing_proposal_fields'])
        self.assertEqual(result['design']['steps'][0]['claim_type'], 'operator_proposal')

    def test_year_boundaries_never_return_validation(self):
        same = self.run_audit(max(self.years))
        before = self.run_audit(max(self.years) + 1)
        self.assertEqual(same['steps'][0]['status'], 'SAME_YEAR_ORDER_UNRESOLVED')
        self.assertEqual(before['steps'][0]['status'], 'NO_LATER_LINK_ENDPOINTS')
        self.assertEqual(before['historical_validation'], 'NOT_PERFORMED')
        self.assertNotEqual(same['scope_request_sha256'], before['scope_request_sha256'])

    def test_unreferenced_challenge_is_preserved_without_changing_used_status(self):
        challenge = copy.deepcopy(self.links['links'][0]); challenge.update(link_id='unused', relation='challenges')
        self.links['links'].append(challenge)
        steps = self.proposal['steps']
        self.proposal = template(self.package, self.links, self.proposal['question'], 'synthetic-operator')
        self.proposal['steps'] = steps
        steps[0]['link_uses'] = []
        result = self.run_audit(min(self.years))
        self.assertEqual(result['steps'][0]['status'], 'NO_LINKED_EVIDENCE_SUPPLIED')
        self.assertEqual(len(result['unreferenced_links']), 2)
        self.assertEqual(result['unreferenced_links'][1]['relation'], 'challenges')
        self.assertIn('unused: challenges', render(self.package, self.links, self.proposal, min(self.years)))

    def test_roles_never_exempt_endpoints_or_infer_question_date(self):
        self.proposal['question'] = 'At year 9999, what should the synthetic researcher do?'
        for role in ('motivation', 'constraint', 'counterargument'):
            self.proposal['steps'][0]['link_uses'][0]['role'] = role
            result = self.run_audit(min(self.years))
            self.assertEqual(result['steps'][0]['status'], 'AFTER_REFERENCE_YEAR_LINK_USED')
            self.assertEqual(result['reference_year'], min(self.years))

    def test_invalid_years_rejected_and_empty_steps_not_pass(self):
        for year in (True, False, 1.0, '2000', None, 0, 10000):
            with self.assertRaises(ValueError): self.run_audit(year)
        self.proposal['steps'] = []
        result = self.run_audit(2000)
        self.assertEqual(result['steps'], [])
        self.assertEqual(result['status'], 'PUBLICATION_SCOPE_REQUIRES_REVIEW')
        self.assertEqual(len(result['unreferenced_links']), 1)

    def test_binding_and_holdout_checks_reused(self):
        original = copy.deepcopy(self.links)
        self.links['links'][0]['rationale'] += ' Changed.'
        with self.assertRaises(ValueError): self.run_audit(2000)
        self.links = original
        self.package['knowledge']['papers'][0]['split'] = 'holdout'
        self.package['persona']['knowledge_papers_sha256'] = payload_sha256(self.package['knowledge']['papers'])
        self.package['knowledge']['persona_payload_sha256'] = payload_sha256(self.package['persona'])
        with self.assertRaises(ValueError): self.run_audit(2000)

    def test_invalid_endpoint_years_rejected_even_for_unreferenced_links(self):
        from observation_input import verified_corpus
        from research_workflow import build
        from reasoning_links import template as link_template
        for year in (0, -1, 10000):
            case = fixture.DesignScenarioTests(); case.setUp()
            case.corpus['papers'][1]['year'] = year
            package = build(verified_corpus(case.corpus))
            links = link_template(package, 'synthetic-operator')
            links['links'] = case.links['links']
            proposal = template(package, links, 'Synthetic question', 'synthetic-operator')
            with self.assertRaisesRegex(ValueError, 'endpoint publication year'):
                audit(package, links, proposal, 2000)

    def test_no_calls_mutation_aliasing_or_overclaimed_checks(self):
        self.proposal['steps'].append(copy.deepcopy(self.proposal['steps'][0]))
        self.proposal['steps'][1]['step_id'] = 'second'
        original = copy.deepcopy((self.package, self.links, self.proposal))
        with patch.object(MockProvider, 'extract', side_effect=AssertionError('provider called')), \
             patch.object(Path, 'read_text', side_effect=AssertionError('source read')):
            result = self.run_audit(2000)
        result['steps'][0]['link_uses'][0]['evidence']['endpoints'][0]['evidence']['publication_year'] = 1
        self.assertNotEqual(result['steps'][1]['link_uses'][0]['evidence']['endpoints'][0]['evidence']['publication_year'], 1)
        self.assertEqual(original, (self.package, self.links, self.proposal))
        self.assertFalse(result['llm_used']); self.assertFalse(result['canonical_update_performed'])

    def test_actual_cli_json_and_text_preserve_evidence_and_missing_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = []
            for name, value in zip(('package', 'links', 'proposal'), (self.package, self.links, self.proposal)):
                path = Path(directory) / (name + '.json'); path.write_text(json.dumps(value), encoding='utf-8'); paths.append(str(path))
            command = [sys.executable, 'publication_scope.py', *paths, '--reference-year', str(min(self.years))]
            output = subprocess.run(command, capture_output=True, check=True).stdout
            self.assertEqual(json.loads(output), self.run_audit(min(self.years)))
            output = subprocess.run(command + ['--format', 'text'], capture_output=True, check=True).stdout.decode('utf-8')
            for value in ('AFTER_REFERENCE_YEAR', '[review]', '[research]', 'falsification_check: NOT_SUPPLIED',
                          'synthetic criterion', 'operator_interpretation', 'explicit_statement', 'recorded check='):
                self.assertIn(value, output)
            failed = subprocess.run(command + ['--reference-year', '0'], capture_output=True)
            self.assertNotEqual(failed.returncode, 0); self.assertEqual(failed.stdout, b'')


if __name__ == '__main__': unittest.main()
