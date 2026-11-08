"""Fixed offline publication/condition example, not scientific comparability validation."""
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
from research_workflow import apply, build
from methodology_trajectory import summarize
from extraction_adapter import MockProvider

ROOT = Path(__file__).resolve().parents[1]
NAMES = ('package', 'scope', 'response', 'provenance', 'adoption')


class TrajectoryConditionsExampleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory(prefix='trajectory conditions external ')
        cls.work = Path(cls.directory.name)
        cls.inputs = {}
        for name in NAMES:
            source = ROOT / 'examples' / ('trajectory-conditions-' + name + '.json')
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
            '--publication-relations', 'publication_relations.json', '--pattern-id', 'trajectory-conditions'], 'empty-scope.json')
        run('answer_proposals.py', ['context', 'package.json', 'empty-scope.json'], 'empty-preview.json')
        run('publication_timeline.py', ['package.json', '--topic', scope['topic'], '--publication-relations', 'publication_relations.json'], 'timeline.json')
        run('publication_context.py', ['package.json', 'publication_relations.json'], 'relations.json')
        cls.trajectory = apply(cls.values['package'], scope['question'], scope['topic'])['methodology_trajectory']

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def read(self, name):
        return json.loads((self.work/name).read_text(encoding='utf-8'))

    def test_external_recipe_and_exact_selection_not_context_permission(self):
        self.assertEqual(len(self.commands), 17)
        self.assertNotEqual(self.work.parent, ROOT)
        self.assertEqual(self.read('empty-response.json')['candidates'], [])
        self.assertTrue(all(d['decision'] == 'defer' for d in self.read('deferred-adoption.json')['decisions']))
        scope = self.values['scope']
        self.assertEqual(self.read('empty-scope.json'), dict(scope, evidence_refs=[]))
        self.assertEqual(self.read('empty-preview.json')['exact_selected_evidence'], [])
        with self.assertRaisesRegex(ValueError, 'explicit references'):
            ap.prepare_handoff(self.values['package'], self.read('empty-scope.json'))
        rows = self.read('preview.json')['exact_selected_evidence']
        self.assertEqual([r['evidence']['reference'] for r in rows], scope['evidence_refs'])
        uncitable = dict(scope['evidence_refs'][2], observation_index=1)
        self.assertNotIn(uncitable, scope['evidence_refs'])
        self.assertIn(uncitable, scope['research_context']['publication_relations']['relations'][1]['basis_refs'])
        response = copy.deepcopy(self.values['response'])
        response['candidates'][0]['citations'][2]['reference'] = uncitable
        with self.assertRaisesRegex(ValueError, 'explicit scope reference'):
            ap.import_response(self.values['package'], scope, self.read('handoff.json'), response, self.values['provenance'])
        self.assertFalse(self.read('handoff.json')['reasoning_context']['citable_scope']['context_expands_citation_scope'])

    def test_exact_condition_groups_do_not_establish_scientific_equivalence(self):
        self.assertEqual(len(self.trajectory), 2)
        a, b = self.trajectory
        self.assertEqual([g['method'] for g in self.trajectory], ['Method M', 'Method M'])
        self.assertEqual([g['condition'] for g in self.trajectory],
                         ['Condition A: separated synthetic signals', 'Condition B: overlapping synthetic signals'])
        self.assertEqual(a['evidence_status'], 'MIXED_STANCES')
        self.assertEqual(b['evidence_status'], 'CHALLENGE_ONLY')
        self.assertFalse(b['cross_year_stance_variation'])
        self.assertEqual({e['paper_id'] for e in b['evidence']}, {'synthetic-2022-b', 'synthetic-2023-review'})
        rules = copy.deepcopy(self.values['package']['persona']['rules'])
        rules[0]['condition'] += ' '
        self.assertEqual(len(summarize(rules)), 3)  # Literal condition strings, not semantic merging.
        uncertainty = self.read('answer.json')['claims'][0]['uncertainty']
        self.assertIn('Same recorded A is not sufficient scientific equivalence', uncertainty)
        self.assertIn('do not prove semantic comparability', uncertainty)

    def test_cross_year_flag_and_same_year_display_are_not_directed_reversal(self):
        a = self.trajectory[0]
        self.assertTrue(a['within_year_disagreement'])
        self.assertTrue(a['cross_year_stance_variation'])
        bucket = next(y for y in a['year_buckets'] if y['year'] == 2024)
        self.assertEqual(len(bucket['supporting_rule_ids']), 1)
        self.assertEqual(len(bucket['challenging_rule_ids']), 1)
        rules = copy.deepcopy(self.values['package']['persona']['rules'])
        # Existential cross-year support/challenge flag remains true if years are reflected.
        for rule in rules:
            rule['year'] = 4044 - rule['year']
        self.assertTrue(summarize(rules)[0]['cross_year_stance_variation'])
        self.assertEqual(summarize(list(reversed(self.values['package']['persona']['rules']))), self.trajectory)
        self.assertIn('latest observations do not supersede earlier ones', a['inference_boundary'])
        later = self.read('timeline.json')['years'][-1]['papers']
        self.assertEqual([p['paper_id'] for p in later], ['synthetic-2024-a-challenge', 'synthetic-2024-a-support'])
        routes = self.read('preview.json')['reasoning_context']['selected_pattern_context_routes']
        self.assertEqual([r['publication_scope'] for r in routes if r['evidence']['publication_year'] == 2024],
                         ['SAME_YEAR_ORDER_UNRESOLVED'] * 2)
        self.assertIn('no latest-wins rule', self.read('answer.json')['claims'][0]['text'])

    def test_review_dependency_exact_bases_and_record_counts_not_independence(self):
        report = self.read('relations.json')
        self.assertEqual(report['independence_assessment'], 'NOT_PERFORMED')
        self.assertFalse(report['transitive_inference'])
        self.assertEqual(len(report['relations']), 2)
        raw = self.values['scope']['research_context']['publication_relations']['relations']
        for row, supplied in zip(report['relations'], raw):
            self.assertEqual(row['relation_type'], 'review_summary_of')
            self.assertEqual([b['reference'] for b in row['basis_evidence']], supplied['basis_refs'])
            self.assertIn('REVIEW_SUMMARY_IS_NOT_AUTOMATIC_INDEPENDENT_CORROBORATION', row['review_prompts'])
            self.assertEqual(row['semantic_validation'], 'NOT_PERFORMED')
        self.assertEqual(self.trajectory[0]['distinct_paper_count'], 4)
        self.assertEqual(self.trajectory[1]['distinct_paper_count'], 2)  # Review appears in both groups.
        self.assertEqual(self.read('timeline.json')['paper_count'], 5)  # Not six independent studies.
        for paper in self.values['package']['knowledge']['papers']:
            self.assertEqual(paper['source_verification'], 'NOT_PERFORMED')
            for obs in paper['observations']:
                self.assertEqual(obs['evidence_verification'], 'NOT_PERFORMED')

    def test_source_stance_claim_type_and_ref_role_are_distinct_and_reasons_survive(self):
        refs = self.values['scope']['evidence_refs']
        rows = self.read('preview.json')['exact_selected_evidence']
        self.assertEqual([r['evidence']['source_kind'] for r in rows], ['research', 'research', 'review', 'research', 'research'])
        self.assertEqual({r['evidence']['observation']['claim_type'] for r in rows}, {'explicit_statement'})
        self.assertTrue(all(r['dimension'] is None for r in refs))
        pattern = self.values['scope']['research_context']['patterns']['review']['decisions'][0]['reviewed_pattern']
        use = next(u for u in pattern['evidence_uses'] if u['reference'] == refs[4])
        self.assertEqual(use['role'], 'challenge')
        self.assertEqual(rows[4]['evidence']['observation']['stance'], 'support')
        accepted = self.read('answer.json')['claims'][0]
        self.assertEqual(accepted['claim_type'], 'operator_synthesis')
        self.assertEqual([c['role'] for c in accepted['citations']], ['support'] * 5)
        for filename in ('preview.text', 'adoption-review.text', 'answer.text'):
            text = (self.work/filename).read_text(encoding='utf-8')
            for use in pattern['evidence_uses']:
                self.assertIn(display(use['rationale']), text)
                self.assertIn(display(use['context_boundary']), text)
            for assessment in self.values['scope']['research_context']['context']['assessments']:
                self.assertIn(display(assessment['context_comparison']), text)
                self.assertIn(display(assessment['remaining_uncertainty']), text)
        for citation in self.values['response']['candidates'][0]['citations']:
            for value in citation['explanation'].values():
                self.assertIn(display(value), (self.work/'answer.text').read_text(encoding='utf-8'))

    def test_active_synthesis_keeps_contrary_evidence_and_rejected_history_final_deferred(self):
        answer = self.read('answer.json')
        self.assertEqual([c['text'] for c in answer['claims']], [self.values['response']['candidates'][0]['text']])
        self.assertEqual([c['decision'] for c in answer['proposal_review']['candidates']], ['accept', 'reject', 'reject'])
        for i in (1, 2):
            original = self.values['response']['candidates'][i]['text']
            self.assertEqual(answer['proposal_review']['candidates'][i]['original_inspection']['text'], original)
            self.assertIn(original, (self.work/'answer.text').read_text(encoding='utf-8'))
            self.assertNotIn(original, [c['text'] for c in answer['claims']])
        self.assertEqual([c['evidence']['reference'] for c in answer['claims'][0]['citations']], self.values['scope']['evidence_refs'])
        self.assertEqual(answer['semantic_validation'], 'NOT_PERFORMED')
        self.assertFalse(answer['proposal_review']['automatic_approval'])
        self.assertEqual([d['decision'] for d in self.read('final-review.json')['decisions']], ['defer'])
        self.assertEqual(self.read('final-result.json')['status'], 'DECLARED_REVIEW_INCOMPLETE')

    def test_inputs_rebuild_unchanged_without_provider_network_or_source_access(self):
        for name, data in self.inputs.items():
            self.assertEqual((self.work/(name+'.json')).read_bytes(), data)
            self.assertEqual((ROOT/'examples'/('trajectory-conditions-'+name+'.json')).read_bytes(), data)
        before = copy.deepcopy(self.values)
        package = self.values['package']
        # Reconstruct from the inspectable synthetic records; this checks bindings, not original sources.
        corpus = {k: package['knowledge'][k] for k in ('author_id', 'version', 'build_id', 'papers')}
        self.assertEqual(build(corpus), package)
        with patch.object(Path, 'open', side_effect=AssertionError('unexpected file access')), \
             patch('builtins.open', side_effect=AssertionError('unexpected file access')), \
             patch('socket.socket', side_effect=AssertionError('unexpected network access')), \
             patch.object(MockProvider, 'extract', side_effect=AssertionError('unexpected provider call')):
            preview = ap.inspect_context(package, self.values['scope'])
            handoff = ap.prepare_handoff(package, self.values['scope'])
            bundle = ap.import_response(package, self.values['scope'], handoff, self.values['response'], self.values['provenance'])
            envelope = ap.export_reviewed(package, bundle, self.values['adoption'])
            ad.inspect(package, envelope)
            apply(package, self.values['scope']['question'], self.values['scope']['topic'])
        self.assertEqual(before, self.values)
        for field in ('provider_invoked', 'external_transmission', 'source_reread', 'browser_invoked', 'scientific_execution'):
            self.assertFalse(preview['processing'][field])
        self.assertEqual(self.values['provenance']['provider_id'], 'synthetic-no-provider')
        self.assertEqual(self.values['provenance']['model_id'], 'synthetic-no-model')


if __name__ == '__main__':
    unittest.main()
