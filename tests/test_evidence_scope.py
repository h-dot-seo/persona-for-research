import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import tests.test_review_journey as fixture
import tests.test_design_lineage as lineage_fixture
from answer_draft import template as answer_template, review_template
from design_scenario import template as design_template
from reasoning_links import template as link_template
from research_workflow import build
from extraction_adapter import MockProvider
from persona import payload_sha256
from evidence_scope import disclose, render


class EvidenceScopeTests(unittest.TestCase):
    def setUp(self):
        case = fixture.ReviewJourneyTests(); case.setUp()
        self.package, self.links, self.proposal, self.draft, self.year = case.package, case.links, case.proposal, case.draft, case.year

    def disclose(self, reviewed=None):
        return disclose(self.package, self.links, self.proposal, self.draft, self.year, reviewed)

    def rebind(self):
        self.package = build(dict(author_id='synthetic-scholar', version='1', build_id='synthetic-build',
                                  papers=self.package['knowledge']['papers']))
        links = link_template(self.package, 'synthetic-operator'); links['links'] = self.links['links']; self.links = links
        proposal = design_template(self.package, links, self.proposal['question'], 'synthetic-operator')
        proposal['steps'] = self.proposal['steps']; self.proposal = proposal
        draft = answer_template(self.package, proposal['question'], 'synthetic-operator')
        draft['claims'] = self.draft['claims']; self.draft = draft

    def test_repeated_hash_does_not_count_as_independent_sources(self):
        self.package['knowledge']['papers'][1]['source_sha256'] = self.package['knowledge']['papers'][0]['source_sha256']
        self.rebind()
        result = self.disclose()
        self.assertEqual(result['coverage']['actively_referenced_paper_ids'], 2)
        self.assertEqual(result['coverage']['active_source_hash_groups'], 1)
        group = result['source_groups'][0]
        self.assertTrue(group['multiple_paper_ids_share_hash'])
        self.assertTrue(group['mixed_year_labels']); self.assertTrue(group['mixed_kind_labels'])
        self.assertEqual(len(group['active_references']), 2)
        self.assertIn('not independent studies', render(self.package, self.links, self.proposal, self.draft, self.year))
        self.assertEqual(result['researcher_fidelity_evaluation'], 'NOT_PERFORMED')

    def test_multiple_roles_and_steps_do_not_inflate_exact_reference_coverage(self):
        before = self.disclose()['coverage']
        step = copy.deepcopy(self.proposal['steps'][0]); step['step_id'] = 'second'; self.proposal['steps'].append(step)
        cite = copy.deepcopy(self.draft['claims'][1]['citations'][0]); cite['role'] = 'context'
        self.draft['claims'][1]['citations'].append(cite)
        self.assertEqual(before, self.disclose()['coverage'])

    def test_uncited_paper_same_hash_is_not_inferred_as_used(self):
        paper = copy.deepcopy(self.package['knowledge']['papers'][0]); paper['paper_id'] = 'synthetic-unused'
        self.package['knowledge']['papers'].append(paper); self.rebind()
        result = self.disclose()
        self.assertIn('synthetic-unused', result['unused_paper_ids'])
        self.assertEqual(result['coverage']['supplied_paper_ids'], 3)
        self.assertEqual(result['coverage']['actively_referenced_paper_ids'], 2)
        self.assertEqual(result['coverage']['active_source_hash_groups'], 2)

    def test_unused_links_do_not_count_as_active_but_challenges_visible(self):
        self.proposal['steps'] = []; self.draft['claims'] = []
        self.links['links'][0]['relation'] = 'challenges'
        self.proposal = design_template(self.package, self.links, self.proposal['question'], 'operator')
        result = self.disclose()
        self.assertEqual(result['coverage']['active_exact_references'], 0)
        self.assertEqual(len(result['unused_paper_ids']), 2)
        self.assertEqual(sum(len(g['unused_link_references']) for g in result['source_groups']), 2)
        text = render(self.package, self.links, self.proposal, self.draft, self.year)
        self.assertIn('Unreferenced link criterion-link: challenges', text)
        self.assertIn('NO_ANSWER_CLAIMS', text)

    def test_rejected_claims_and_missing_uncertainty_remain_visible(self):
        reviewed = review_template(self.package, self.draft, 'synthetic-reviewer')
        reviewed['decisions'][0].update(decision='reject', note='Synthetic rejection.')
        result = self.disclose(reviewed)
        self.assertEqual(result['answer_claims'][0]['declared_review_decision'], 'reject')
        self.assertIsNone(result['answer_claims'][0]['uncertainty'])
        self.assertEqual(len(result['answer_claims']), 2)
        self.assertEqual(result['coverage'], self.disclose()['coverage'])
        text = render(self.package, self.links, self.proposal, self.draft, self.year, reviewed)
        self.assertIn('declared review=reject', text); self.assertIn('Uncertainty: NOT_SUPPLIED', text)

    def test_mock_origin_not_actual_model_call_or_authenticated_human_review(self):
        case = lineage_fixture.DesignLineageTests(); case.setUp()
        draft = answer_template(case.package, case.proposal['question'], 'operator')
        draft['claims'] = [dict(claim_id='synthetic-answer', text='Consider uncertainty.', claim_type='operator_synthesis',
            uncertainty='Synthetic only.', citations=[dict(role='context', reference=dict(paper_id='synthetic-0', observation_index=0, dimension='uncertainty'))])]
        result = disclose(case.package, case.links, case.proposal, draft, 2020)
        self.assertEqual(len(result['recorded_mock_origin_references']), 1)
        self.assertFalse(result['llm_used']); self.assertFalse(result['provider_invoked'])
        row = next(row for group in result['source_groups'] for row in group['active_references'] if 'recorded_origin' in row)
        self.assertEqual(row['selected_claim_type'], 'operator_interpretation')
        self.assertEqual(row['recorded_origin']['proposed_claim_type'], 'explicit_statement')
        self.assertEqual(row['recorded_origin']['candidate_bundle_sha256'], payload_sha256(case.bundle))

    def test_stale_review_and_unauthorized_package_reject(self):
        reviewed = review_template(self.package, self.draft, 'reviewer')
        self.draft['claims'][1]['text'] += ' Changed.'
        with self.assertRaises(ValueError): self.disclose(reviewed)
        self.package['knowledge']['papers'][0]['authorized'] = False
        with self.assertRaises(ValueError): self.disclose()

    def test_no_source_access_mutation_or_unknown_fields_in_disclosure(self):
        self.package['knowledge']['papers'][0]['raw_unknown'] = 'PRIVATE_UNKNOWN_SENTINEL'
        self.package['persona']['knowledge_papers_sha256'] = payload_sha256(self.package['knowledge']['papers'])
        self.package['knowledge']['persona_payload_sha256'] = payload_sha256(self.package['persona'])
        links = link_template(self.package, 'operator'); links['links'] = self.links['links']; self.links = links
        proposal = design_template(self.package, links, self.proposal['question'], 'operator')
        proposal['steps'] = self.proposal['steps']; self.proposal = proposal
        draft = answer_template(self.package, proposal['question'], 'operator')
        draft['claims'] = self.draft['claims']; self.draft = draft
        before = copy.deepcopy((self.package, self.links, self.proposal, self.draft))
        with patch.object(MockProvider, 'extract', side_effect=AssertionError('provider called')), \
             patch.object(Path, 'read_text', side_effect=AssertionError('source read')):
            result = self.disclose()
        self.assertNotIn('PRIVATE_UNKNOWN_SENTINEL', json.dumps(result))
        self.assertEqual(before, (self.package, self.links, self.proposal, self.draft))

    def test_invalid_year_in_unused_paper_rejects_scope_overview(self):
        paper = copy.deepcopy(self.package['knowledge']['papers'][0]); paper['paper_id'] = 'synthetic-unused'; paper['year'] = 0
        self.package['knowledge']['papers'].append(paper); self.rebind()
        with self.assertRaisesRegex(ValueError, 'supplied publication year'): self.disclose()

    def test_actual_cli_reader_disclosure_json_text_and_failclosed(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = []
            for name, value in [('package', self.package), ('links', self.links), ('proposal', self.proposal), ('draft', self.draft)]:
                p = Path(directory)/(name+'.json'); p.write_text(json.dumps(value), encoding='utf-8'); paths.append(str(p))
            cmd = [sys.executable, 'evidence_scope.py', *paths, '--reference-year', str(self.year)]
            result = subprocess.run(cmd, capture_output=True, check=True)
            self.assertEqual(json.loads(result.stdout), self.disclose())
            text = subprocess.run(cmd+['--format','text'], capture_output=True, check=True).stdout.decode('utf-8')
            for value in ('scholarly simulation only', 'active_source_hash_groups: 2', 'AFTER_REFERENCE_YEAR',
                          'Uncertainty: NOT_SUPPLIED', 'CURATED_RECORD_ORIGIN_NOT_AUTHENTICATED',
                          'recorded selected check=', 'Answer s1: challenge', 'Design design-1: constraint'):
                self.assertIn(value, text)
            bad = subprocess.run(cmd+['--reference-year','0'], capture_output=True)
            self.assertNotEqual(bad.returncode, 0); self.assertEqual(bad.stdout, b'')


if __name__ == '__main__': unittest.main()
