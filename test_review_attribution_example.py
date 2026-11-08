"""Fixed offline attribution preservation example, not semantic/author validation."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import answer_proposals as ap
import answer_draft as ad
from review_package import display

ROOT = Path(__file__).resolve().parent
NAMES = ('package', 'scope', 'response', 'provenance', 'adoption')


class ReviewAttributionExampleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory(prefix='review attribution external ')
        cls.work = Path(cls.directory.name)
        cls.inputs = {}
        for name in NAMES:
            source = ROOT / 'examples' / ('review-attribution-' + name + '.json')
            data = source.read_bytes()
            (cls.work / (name + '.json')).write_bytes(data)
            cls.inputs[name] = data
        cls.values = {name: json.loads(data) for name, data in cls.inputs.items()}
        cls.commands = []
        def run(script, args, output):
            result = subprocess.run([sys.executable, str(ROOT/script), *args], cwd=cls.work,
                                    capture_output=True, text=True, encoding='utf-8', timeout=30)
            if result.returncode:
                raise AssertionError(result.stderr)
            (cls.work/output).write_text(result.stdout, encoding='utf-8')
            cls.commands.append((script, args, output))
        cls.run_cli = staticmethod(run)
        for fmt in ('json', 'text'):
            run('answer_proposals.py', ['context', 'package.json', 'scope.json', '--format', fmt], 'preview.'+fmt)
        run('answer_proposals.py', ['prepare', 'package.json', 'scope.json'], 'handoff.json')
        run('answer_proposals.py', ['response-template', 'package.json', 'scope.json', 'handoff.json'], 'empty-response.json')
        run('answer_proposals.py', ['import', 'package.json', 'scope.json', 'handoff.json', 'response.json', 'provenance.json'], 'bundle.json')
        run('answer_proposals.py', ['review-template', 'package.json', 'bundle.json', '--reviewer-id', 'synthetic-reviewer'], 'deferred-adoption.json')
        for fmt in ('json', 'text'):
            run('answer_proposals.py', ['review', 'package.json', 'bundle.json', 'adoption.json', '--format', fmt], 'adoption-review.'+fmt)
        run('answer_proposals.py', ['export', 'package.json', 'bundle.json', 'adoption.json'], 'draft.json')
        for fmt in ('json', 'text'):
            run('answer_draft.py', ['package.json', 'draft.json', '--format', fmt], 'answer.'+fmt)
        run('answer_draft.py', ['package.json', 'draft.json', '--review-template', '--reviewer-id', 'synthetic-final-reviewer'], 'final-review.json')
        run('answer_draft.py', ['package.json', 'draft.json', '--review', 'final-review.json'], 'final-result.json')
        scope = cls.values['scope']
        for key in ('patterns', 'context', 'publication_relations'):
            (cls.work/(key+'.json')).write_text(json.dumps(scope['research_context'][key]), encoding='utf-8')
        run('answer_proposals.py', ['template', 'package.json', '--question', scope['question'], '--topic', scope['topic'],
            '--reference-year', str(scope['reference_year']), '--operator-id', scope['operator_id'],
            '--include-citation-explanations', '--patterns', 'patterns.json', '--context', 'context.json',
            '--publication-relations', 'publication_relations.json', '--pattern-id', 'review-attribution'], 'empty-scope.json')
        run('answer_proposals.py', ['context', 'package.json', 'empty-scope.json'], 'empty-preview.json')

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def read(self, name):
        return json.loads((self.work/name).read_text(encoding='utf-8'))

    def test_real_external_cli_recipe_has_fifteen_successful_stages(self):
        self.assertEqual(len(self.commands), 15)
        self.assertNotEqual(self.work.parent, ROOT)
        self.assertEqual(self.read('empty-response.json')['candidates'], [])
        self.assertTrue(all(d['decision']=='defer' for d in self.read('deferred-adoption.json')['decisions']))

    def test_two_distinct_exact_passages_share_kind_and_label_not_attribution(self):
        rows = self.read('preview.json')['exact_selected_evidence']
        self.assertEqual([r['evidence']['reference'] for r in rows], self.values['scope']['evidence_refs'])
        self.assertEqual([r['evidence']['reference']['observation_index'] for r in rows], [0, 1])
        self.assertEqual({r['evidence']['source_kind'] for r in rows}, {'review'})
        self.assertEqual({r['evidence']['observation']['claim_type'] for r in rows}, {'explicit_statement'})
        quotes = [r['evidence']['observation']['evidence_quote'] for r in rows]
        self.assertEqual(quotes, [o['evidence_quote'] for o in self.values['package']['knowledge']['papers'][0]['observations']])
        self.assertEqual(len(set(quotes)), 2)
        for row in rows:
            self.assertIn('individual ownership not established', row['evidence']['attribution'])

    def test_per_reference_reasons_boundaries_and_citation_explanations_survive(self):
        pattern = self.values['scope']['research_context']['patterns']['review']['decisions'][0]['reviewed_pattern']
        for filename in ('preview.text', 'adoption-review.text', 'answer.text'):
            text = (self.work/filename).read_text(encoding='utf-8')
            for use in pattern['evidence_uses']:
                self.assertIn(display(use['rationale']), text)
                self.assertIn(display(use['context_boundary']), text)
        for citation in self.values['response']['candidates'][0]['citations']:
            for value in citation['explanation'].values():
                self.assertIn(display(value), (self.work/'adoption-review.text').read_text(encoding='utf-8'))

    def test_context_record_is_not_an_original_paper_or_exact_citation(self):
        scope = self.values['scope']
        self.assertEqual(scope['research_context']['publication_relations']['relations'], [])
        self.assertEqual(len(self.values['package']['knowledge']['papers']), 2)
        context_rows = scope['research_context']['context']['assessments']
        context_row = next(r for r in context_rows if r['reference']['paper_id']=='synthetic-context-review')
        self.assertEqual(context_row['decision'], 'exclude')
        self.assertIn('Context-only', context_row['context_comparison'])
        context_paper = self.values['package']['knowledge']['papers'][1]
        self.assertIn('independent verification', context_paper['observations'][0]['limitation'])
        self.assertTrue(all(p['kind']=='review' for p in self.values['package']['knowledge']['papers']))
        self.assertEqual({r['paper_id'] for r in scope['evidence_refs']}, {'synthetic-review'})
        self.assertEqual(self.read('handoff.json')['reasoning_context']['citable_scope']['evidence_refs'], scope['evidence_refs'])
        response = copy.deepcopy(self.values['response'])
        response['candidates'][0]['citations'][0]['reference']['paper_id'] = 'synthetic-context-review'
        with self.assertRaisesRegex(ValueError, 'explicit scope reference'):
            ap.import_response(self.values['package'], scope, self.read('handoff.json'), response, self.values['provenance'])

    def test_empty_selection_stays_empty_despite_populated_raw_context(self):
        empty = self.read('empty-scope.json')
        self.assertEqual(empty, dict(self.values['scope'], evidence_refs=[]))
        preview = self.read('empty-preview.json')
        self.assertEqual(preview['exact_selected_evidence'], [])
        self.assertEqual(preview['citation_selection_status'], 'NO_EXACT_CITATIONS_SELECTED')
        with self.assertRaisesRegex(ValueError, 'explicit references'):
            ap.prepare_handoff(self.values['package'], empty)

    def test_rejected_overstatement_is_history_only_shared_refs_stay_active(self):
        answer = self.read('answer.json')
        self.assertEqual([c['text'] for c in answer['claims']], ['The review reports M and recommends testing N.'])
        history = answer['proposal_review']['candidates']
        self.assertEqual([c['decision'] for c in history], ['accept', 'reject'])
        self.assertEqual(history[1]['original_inspection']['text'], 'The scholar uses M.')
        self.assertIn('The scholar uses M.', (self.work/'answer.text').read_text(encoding='utf-8'))
        active = [c['evidence']['reference'] for c in answer['claims'][0]['citations']]
        rejected_ref = self.values['response']['candidates'][1]['citations'][0]['reference']
        self.assertIn(rejected_ref, active)
        self.assertEqual(active, self.values['scope']['evidence_refs'])

    def test_fixed_adoption_is_not_method_adoption_and_final_review_deferred(self):
        answer = self.read('answer.json')
        self.assertEqual(answer['semantic_validation'], 'NOT_PERFORMED')
        self.assertIn('remain unestablished', answer['claims'][0]['uncertainty'])
        self.assertFalse(answer['proposal_review']['automatic_approval'])
        review = self.read('final-review.json')
        self.assertEqual([d['decision'] for d in review['decisions']], ['defer'])
        self.assertEqual(self.read('final-result.json')['status'], 'DECLARED_REVIEW_INCOMPLETE')

    def test_inputs_unchanged_and_no_source_provider_browser_or_network_access(self):
        for name, data in self.inputs.items():
            self.assertEqual((self.work/(name+'.json')).read_bytes(), data)
            self.assertEqual((ROOT/'examples'/('review-attribution-'+name+'.json')).read_bytes(), data)
        before = copy.deepcopy(self.values)
        with patch.object(Path, 'open', side_effect=AssertionError('unexpected file access')), \
             patch('builtins.open', side_effect=AssertionError('unexpected file access')), \
             patch('socket.socket', side_effect=AssertionError('unexpected network access')):
            preview = ap.inspect_context(self.values['package'], self.values['scope'])
            handoff = ap.prepare_handoff(self.values['package'], self.values['scope'])
            bundle = ap.import_response(self.values['package'], self.values['scope'], handoff, self.values['response'], self.values['provenance'])
            envelope = ap.export_reviewed(self.values['package'], bundle, self.values['adoption'])
            ad.inspect(self.values['package'], envelope)
        self.assertEqual(before, self.values)
        for field in ('provider_invoked', 'external_transmission', 'source_reread', 'browser_invoked', 'scientific_execution'):
            self.assertFalse(preview['processing'][field])
        self.assertEqual(self.values['provenance']['provider_id'], 'synthetic-no-provider')

    def test_operator_control_text_escaped_in_preview_and_review(self):
        scope = copy.deepcopy(self.values['scope'])
        marker = 'operator\nFORGED\x1b[31m\u202e'
        scope['research_context']['context']['assessments'][0]['remaining_uncertainty'] = marker
        preview = ap.inspect_context(self.values['package'], scope)
        handoff = ap.prepare_handoff(self.values['package'], scope)
        response = ap.response_template(self.values['package'], scope, handoff)
        response['candidates'] = copy.deepcopy(self.values['response']['candidates'])
        bundle = ap.import_response(self.values['package'], scope, handoff, response, self.values['provenance'])
        review = ap.review_template(self.values['package'], bundle, 'synthetic-reviewer')
        for text in (ap.render_context(preview), ap.render_review(ap.review_proposals(self.values['package'], bundle, review))):
            self.assertIn(display(marker), text)
            self.assertNotIn(marker, text)


if __name__ == '__main__':
    unittest.main()
