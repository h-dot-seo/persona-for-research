import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import tests.test_answer_draft as fixture
from answer_draft import review_template
from argument_map import template, inspect, render
from extraction_adapter import MockProvider


class ArgumentMapTests(unittest.TestCase):
    def setUp(self):
        case = fixture.AnswerDraftTests(); case.setUp(); self.package, self.draft = case.package, case.draft
        self.draft['claims'].append(dict(claim_id='conclusion', text='Choose a comparison only after checking discriminating predictions.',
            claim_type='operator_synthesis', uncertainty='Synthetic inference, not empirically tested.', citations=[]))
        self.map = template(self.package, self.draft, 'synthetic-map-operator')
        self.map['steps'] = [dict(step_id='combine', premise_claim_ids=['q1', 's1'], conclusion_claim_id='conclusion',
            bridge_rationale='Operator proposes applying the quoted criterion to the earlier comparison idea.',
            assumptions=['The chosen observable differs between the synthetic models.'], defeater=None)]

    def inspect(self, reviewed=None): return inspect(self.package, self.draft, self.map, reviewed)

    def test_inference_is_operator_only_and_citations_do_not_transfer(self):
        result = self.inspect(); step = result['steps'][0]
        self.assertEqual(step['claim_type'], 'operator_interpretation')
        self.assertEqual(step['conclusion']['claim_type'], 'operator_synthesis')
        self.assertEqual(step['conclusion']['direct_citation_count'], 0)
        self.assertEqual(step['conclusion']['evidence_status'], 'NO_CITATIONS_SUPPLIED')
        self.assertEqual(step['citation_transfer'], 'NOT_PERFORMED')
        self.assertIn('defeater', step['missing_fields'])
        self.assertEqual(result['review_order_claim_ids'], ['q1', 's1', 'conclusion'])
        self.assertEqual(result['logical_validation'], 'NOT_PERFORMED')

    def test_multistep_input_order_not_treated_as_derivation_order(self):
        first = dict(step_id='first', premise_claim_ids=['q1'], conclusion_claim_id='s1',
                     bridge_rationale='Operator bridge.', assumptions=[], defeater='A non-discriminating observation.')
        self.map['steps'].append(first)
        result = self.inspect()
        self.assertEqual([s['step_id'] for s in result['steps']], ['first', 'combine'])
        self.assertEqual(result['premise_only_claim_ids'], ['q1'])
        self.assertEqual(result['steps'][0]['missing_fields'], ['assumptions'])

    def test_cycles_self_premises_and_inferred_source_quote_reject(self):
        for mode in ('cycle', 'self', 'quote'):
            bad = copy.deepcopy(self.map)
            if mode == 'cycle': bad['steps'].append(dict(step_id='back', premise_claim_ids=['conclusion'], conclusion_claim_id='s1',
                bridge_rationale='Circular claim.', assumptions=[], defeater=None))
            elif mode == 'self': bad['steps'][0]['premise_claim_ids'].append('conclusion')
            else: bad['steps'][0]['conclusion_claim_id'] = 'q1'
            with self.assertRaises(ValueError): inspect(self.package, self.draft, bad)

    def test_unknown_duplicate_empty_schema_and_assumptions_reject(self):
        for mode in ('unknown', 'duplicate', 'empty', 'extra', 'assumption', 'blank'):
            bad = copy.deepcopy(self.map)
            if mode == 'unknown': bad['steps'][0]['premise_claim_ids'] = ['unknown']
            elif mode == 'duplicate': bad['steps'][0]['premise_claim_ids'] = ['q1','q1']
            elif mode == 'empty': bad['steps'][0]['premise_claim_ids'] = []
            elif mode == 'extra': bad['steps'][0]['author_reasoning'] = True
            elif mode == 'assumption': bad['steps'][0]['assumptions'] = ['same','same']
            else: bad['steps'][0]['bridge_rationale'] = ' '
            with self.assertRaises(ValueError): inspect(self.package, self.draft, bad)

    def test_draft_and_declared_review_changes_make_map_stale(self):
        self.draft['claims'][1]['uncertainty'] += ' Changed.'
        with self.assertRaises(ValueError): self.inspect()
        steps = self.map['steps']; declared = review_template(self.package, self.draft, 'reviewer')
        self.map = template(self.package, self.draft, 'operator', declared); self.map['steps'] = steps
        self.inspect(declared)
        declared['decisions'][0]['note'] += ' Updated.'
        with self.assertRaises(ValueError): self.inspect(declared)
        with self.assertRaises(ValueError): self.inspect()

    def test_rejected_or_unreviewed_premise_not_silently_promoted(self):
        reviewed = review_template(self.package, self.draft, 'reviewer')
        reviewed['decisions'][0].update(decision='reject', note='Synthetic rejection.')
        steps = self.map['steps']; self.map = template(self.package, self.draft, 'operator', reviewed); self.map['steps'] = steps
        result = self.inspect(reviewed)
        self.assertEqual(result['steps'][0]['premises'][0]['declared_review_decision'], 'reject')
        self.assertEqual(result['steps'][0]['premises'][1]['declared_review_decision'], 'defer')
        self.assertIn('declared review=reject', render(self.package, self.draft, self.map, reviewed))

    def test_multiple_paths_and_unmapped_claims_not_independent_support(self):
        other = copy.deepcopy(self.map['steps'][0]); other['step_id'] = 'alternative'; other['premise_claim_ids'] = ['q1']
        self.map['steps'] = [other, dict(other, step_id='another')]
        result = self.inspect()
        self.assertEqual(result['review_order_claim_ids'], ['q1','conclusion'])
        self.assertEqual(result['unmapped_claim_ids'], ['s1'])
        self.assertEqual(len(result['steps']), 2)
        self.assertEqual(result['logical_validation'], 'NOT_PERFORMED')

    def test_no_calls_aliasing_mutation_and_empty_map(self):
        before = copy.deepcopy((self.package,self.draft,self.map))
        with patch.object(MockProvider,'extract',side_effect=AssertionError('provider called')), \
             patch.object(Path,'read_text',side_effect=AssertionError('source read')):
            result = self.inspect()
        result['steps'][0]['assumptions'].append('Changed output')
        self.assertEqual(before,(self.package,self.draft,self.map))
        empty = template(self.package,self.draft,'operator')
        result = inspect(self.package,self.draft,empty)
        self.assertEqual(result['status'],'NO_DECLARED_ARGUMENT_STEPS')
        self.assertEqual(len(result['unmapped_claim_ids']),3)

    def test_actual_cli_template_and_argument_review(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for name,value in [('package',self.package),('draft',self.draft),('map',self.map)]:
                (root/(name+'.json')).write_text(json.dumps(value),encoding='utf-8')
            cmd=[sys.executable,'argument_map.py',str(root/'package.json'),str(root/'draft.json')]
            created=json.loads(subprocess.run(cmd+['--template','--operator-id','synthetic-map-operator'],capture_output=True,check=True).stdout)
            self.assertEqual(created['steps'],[])
            cmd.append(str(root/'map.json'))
            self.assertEqual(json.loads(subprocess.run(cmd,capture_output=True,check=True).stdout),self.inspect())
            text=subprocess.run(cmd+['--format','text'],capture_output=True,check=True).stdout.decode('utf-8')
            for value in ('q1, s1 -> conclusion','Defeater: NOT_SUPPLIED','NO_CITATIONS_SUPPLIED','Citation transfer: NOT_PERFORMED',
                          'synthetic criterion','operator_synthesis','[review]','[research]'):
                self.assertIn(value,text)


if __name__=='__main__':unittest.main()
