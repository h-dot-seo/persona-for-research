import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import test_design_scenario as design_fixture
import test_answer_draft as answer_fixture
from answer_draft import review_template, template
from design_scenario import template as design_template
from extraction_adapter import MockProvider
from review_journey import assemble, render


class ReviewJourneyTests(unittest.TestCase):
    def setUp(self):
        d = design_fixture.DesignScenarioTests(); d.setUp()
        a = answer_fixture.AnswerDraftTests(); a.setUp()
        self.package, self.links, self.proposal, self.draft = d.package, d.links, d.proposal, a.draft
        self.draft['question'] = self.proposal['question']
        self.year = min(p['year'] for p in self.package['knowledge']['papers'])

    def assemble(self, reviewed=None):
        return assemble(self.package, self.links, self.proposal, self.draft, self.year, reviewed)

    def test_shared_reference_keeps_answer_design_and_source_roles_separate(self):
        result = self.assemble()
        node = next(r for r in result['evidence_routes'] if r['evidence']['reference']['paper_id'] == 'synthetic-1')
        self.assertEqual([u['role'] for u in node['answer_uses']], ['context', 'challenge'])
        self.assertEqual(node['design_uses'][0]['role'], 'constraint')
        self.assertEqual(node['design_uses'][0]['relation'], 'qualifies')
        self.assertEqual(node['evidence']['component']['claim_type'], 'explicit_statement')
        codes = [p['code'] for p in result['review_prompts']]
        self.assertIn('AFTER_REFERENCE_YEAR_LINK_USED', codes)
        self.assertIn('UNCERTAINTY_NOT_SUPPLIED', codes)
        self.assertIn('NO_DECLARED_REVIEW', codes)
        self.assertEqual(result['status'], 'INTEGRATED_REVIEW_REQUIRED')

    def test_observation_and_component_never_collapsed(self):
        self.draft['claims'][1]['citations'][0]['reference']['dimension'] = None
        result = self.assemble()
        refs = [r['evidence']['reference'] for r in result['evidence_routes'] if r['evidence']['reference']['paper_id'] == 'synthetic-0']
        self.assertEqual({r['dimension'] for r in refs}, {None, 'alternative_explanation'})

    def test_question_and_hash_changes_reject_not_join_approximately(self):
        self.draft['question'] += ' '
        with self.assertRaisesRegex(ValueError, 'match exactly'): self.assemble()
        self.draft['question'] = self.proposal['question']
        reviewed = review_template(self.package, self.draft, 'synthetic-reviewer')
        self.draft['claims'][1]['text'] += ' Changed.'
        with self.assertRaisesRegex(ValueError, 'stale'): self.assemble(reviewed)
        self.links['links'][0]['rationale'] += ' Changed.'
        with self.assertRaises(ValueError): self.assemble()

    def test_review_revise_reject_preserved_and_changes_packet_binding(self):
        reviewed = review_template(self.package, self.draft, 'synthetic-reviewer')
        before = self.assemble(reviewed)
        reviewed['decisions'][0].update(decision='reject', note='Not responsive.')
        reviewed['decisions'][1].update(decision='revise', note='More uncertainty needed.')
        result = self.assemble(reviewed)
        codes = [p['code'] for p in result['review_prompts']]
        self.assertIn('DECLARED_REJECT', codes); self.assertIn('DECLARED_REVISE', codes)
        self.assertNotEqual(before['packet_input_sha256'], result['packet_input_sha256'])
        self.assertEqual(len(result['answer']['claims']), 2)

    def test_unreferenced_challenge_routes_retained_with_no_inferred_use(self):
        link = copy.deepcopy(self.links['links'][0]); link.update(link_id='unused-challenge', relation='challenges')
        self.links['links'].append(link)
        steps = self.proposal['steps']
        self.proposal = design_template(self.package, self.links, self.proposal['question'], 'synthetic-operator')
        self.proposal['steps'] = steps
        result = self.assemble()
        self.assertTrue(any(r['unreferenced_link_uses'] for r in result['evidence_routes']))
        self.assertFalse(any(u['link_id'] == 'unused-challenge' for r in result['evidence_routes'] for u in r['design_uses']))
        self.assertIn('Unreferenced link unused-challenge', render(self.package, self.links, self.proposal, self.draft, self.year))

    def test_answer_only_future_citation_is_flagged_without_design_links(self):
        self.links['links'] = []
        self.proposal = design_template(self.package, self.links, self.proposal['question'], 'operator')
        result = self.assemble()
        self.assertTrue(any(p['target'] == 'answer_claim' and p['target_id'] == 'q1' and
                            p['code'] == 'AFTER_REFERENCE_YEAR' for p in result['review_prompts']))
        node = next(r for r in result['evidence_routes'] if r['evidence']['reference']['paper_id'] == 'synthetic-1')
        self.assertEqual(node['publication_scope'], 'AFTER_REFERENCE_YEAR')
        self.assertEqual(node['design_uses'], [])

    def test_empty_or_filled_checklist_is_never_scientific_approval(self):
        self.draft = template(self.package, self.proposal['question'], 'operator')
        self.proposal['steps'] = []
        result = self.assemble()
        self.assertIn('NO_ANSWER_CLAIMS', [p['code'] for p in result['review_prompts']])
        self.assertIn('NO_PROPOSED_STEPS', [p['code'] for p in result['review_prompts']])
        self.assertEqual(result['semantic_validation'], 'NOT_PERFORMED')

    def test_no_calls_mutation_or_cross_section_aliasing(self):
        before = copy.deepcopy((self.package, self.links, self.proposal, self.draft))
        with patch.object(MockProvider, 'extract', side_effect=AssertionError('provider called')), \
             patch.object(Path, 'read_text', side_effect=AssertionError('source read')):
            result = self.assemble()
        result['evidence_routes'][0]['evidence']['component']['text'] = 'changed'
        self.assertNotEqual(result['answer']['claims'][0]['citations'][0]['evidence']['component']['text'], 'changed')
        self.assertEqual(before, (self.package, self.links, self.proposal, self.draft))
        self.assertFalse(result['llm_used'])

    def test_actual_cli_combined_packet_json_and_text(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); paths = []
            for name, value in [('package', self.package), ('links', self.links), ('proposal', self.proposal), ('draft', self.draft)]:
                p = root/(name+'.json'); p.write_text(json.dumps(value), encoding='utf-8'); paths.append(str(p))
            cmd = [sys.executable, 'review_journey.py', *paths, '--reference-year', str(self.year)]
            output = subprocess.run(cmd, check=True, capture_output=True).stdout
            self.assertEqual(json.loads(output), self.assemble())
            text = subprocess.run(cmd+['--format','text'], check=True, capture_output=True).stdout.decode('utf-8')
            for value in ('Exact evidence reference index', 'Answer s1', 'Design design-1', 'citation role=challenge',
                          'use role=constraint', 'AFTER_REFERENCE_YEAR', 'falsification_check: NOT_SUPPLIED',
                          '[operator_synthesis]', '[explicit_statement]', 'synthetic criterion'):
                self.assertIn(value, text)


if __name__ == '__main__': unittest.main()
