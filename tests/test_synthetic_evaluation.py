import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from evaluate_synthetic import freeze,evaluate
from persona import payload_sha256
from synthetic_walkthrough import run
from extraction_adapter import MockProvider


class SyntheticEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.root=Path(cls.tmp.name)/'demo';run(cls.root)
        cls.package=json.loads((cls.root/'revision.json').read_text())
        cls.draft=json.loads((cls.root/'draft.json').read_text())
        cls.labels=json.loads(Path('examples/synthetic-holdout-labels.json').read_text())
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def setUp(self):
        self.package=copy.deepcopy(self.__class__.package);self.draft=copy.deepcopy(self.__class__.draft);self.labels=copy.deepcopy(self.__class__.labels)

    def test_quickstart_exact_counts_expose_intentional_missing_conclusion_citation(self):
        result=evaluate(freeze(self.package,self.draft),self.labels)
        self.assertEqual(result['citation_labels'],dict(matched=3,unexpected=0,missing=1,precision=1.0,recall=0.75))
        self.assertEqual(result['answer_claim_type_labels']['matched'],3)
        self.assertEqual(result['challenge_labels'],dict(expected=1,preserved=1,missing=0))
        self.assertEqual(result['claims'][2]['missing_citations'][0]['reference']['paper_id'],'synthetic-1')
        self.assertEqual(result['researcher_fidelity_evaluation'],'NOT_PERFORMED')

    def test_wrong_component_and_extra_role_are_not_correct_citations(self):
        self.draft['claims'][1]['citations'][0]['reference']['dimension']='uncertainty'
        self.draft['claims'][1]['citations'].append(dict(role='context',reference=copy.deepcopy(self.draft['claims'][1]['citations'][1]['reference'])))
        result=evaluate(freeze(self.package,self.draft),self.labels)
        self.assertEqual(result['citation_labels']['matched'],2)
        self.assertEqual(result['citation_labels']['unexpected'],2)
        self.assertEqual(result['citation_labels']['missing'],2)

    def test_missing_counterevidence_detected_without_borrowing_other_claim_citation(self):
        self.draft['claims'][1]['citations'].pop()
        result=evaluate(freeze(self.package,self.draft),self.labels)
        self.assertEqual(result['challenge_labels']['missing'],1)
        self.assertEqual(len(result['claims'][1]['missing_challenge_citations']),1)
        self.assertEqual(result['claims'][0]['matched_citation_count'],1)

    def test_answer_attribution_labels_are_graded_separately_from_source_labels(self):
        claim=self.draft['claims'][1]
        claim.update(claim_type='source_quote',text='Compare explanations.')
        claim['citations']=claim['citations'][:1]
        result=evaluate(freeze(self.package,self.draft),self.labels)
        self.assertEqual(result['answer_claim_type_labels']['matched'],2)
        self.assertFalse(result['claims'][1]['claim_type_label_match'])
        self.assertEqual(result['source_claim_type_labels']['mismatched'],0)
        self.labels['expected_claims'][1]['citations'][0]['source_claim_type']='explicit_statement'
        result=evaluate(freeze(self.package,self.draft),self.labels)
        self.assertEqual(result['source_claim_type_labels']['mismatched'],1)

    def test_missing_and_unexpected_claims_reported_without_semantic_matching(self):
        self.draft['claims'][1]['claim_id']='renamed'
        result=evaluate(freeze(self.package,self.draft),self.labels)
        self.assertEqual(result['answer_claim_type_labels']['missing_claim_ids'],['comparison'])
        self.assertEqual(result['answer_claim_type_labels']['unexpected_claim_ids'],['renamed'])
        self.assertEqual(result['challenge_labels']['missing'],1)

    def test_zero_citations_have_null_precision_not_perfect_score(self):
        self.draft['claims']=[]
        result=evaluate(freeze(self.package,self.draft),self.labels)
        self.assertIsNone(result['citation_labels']['precision']);self.assertEqual(result['citation_labels']['recall'],0.0)
        self.assertEqual(result['citation_labels']['missing'],4)
        self.assertEqual(result['answer_claim_type_labels']['matched'],0)

    def test_holdout_corpus_never_enters_frozen_training_catalog(self):
        package=self.package['package'];package['knowledge']['papers'][0]['split']='holdout'
        package['persona']['knowledge_papers_sha256']=payload_sha256(package['knowledge']['papers'])
        package['knowledge']['persona_payload_sha256']=payload_sha256(package['persona'])
        with self.assertRaises(ValueError):freeze(self.package,self.draft)
        with self.assertRaises(ValueError):freeze(self.labels,self.draft)

    def test_nonholdout_or_nonsynthetic_labels_and_wrong_binding_reject(self):
        submission=freeze(self.package,self.draft)
        for key,value in [('split','training'),('synthetic_only',1),('schema','other'),('question_sha256','0'*64),('persona_sha256','0'*64)]:
            bad=copy.deepcopy(self.labels);bad[key]=value
            with self.assertRaises(ValueError):evaluate(submission,bad)
        bad=copy.deepcopy(self.labels);bad['expected_claims'][0]['citations'][0]['reference']['paper_id']='synthetic-unseen'
        with self.assertRaisesRegex(ValueError,'outside frozen'):evaluate(submission,bad)

    def test_nonsynthetic_empty_paper_cannot_bypass_fixture_identity_guard(self):
        from research_workflow import build
        from answer_draft import template
        corpus=json.loads((self.root/'corpus.json').read_text())
        paper=copy.deepcopy(corpus['papers'][0]);paper['paper_id']='nonfixture-empty-paper';paper['observations']=[]
        corpus['papers'].append(paper)
        package=build(corpus);draft=template(package,'Synthetic question','operator')
        with self.assertRaisesRegex(ValueError,'synthetic fixture paper'):freeze(package,draft)

    def test_gold_source_hash_must_agree_with_bound_catalog(self):
        self.labels['expected_claims'][0]['citations'][0]['source_sha256']='2'*64
        with self.assertRaisesRegex(ValueError,'gold source hash'):evaluate(freeze(self.package,self.draft),self.labels)

    def test_submission_tamper_and_unknown_gold_fields_rejected(self):
        submission=freeze(self.package,self.draft);submission['claims'][1]['claim_type']='source_quote'
        with self.assertRaisesRegex(ValueError,'digest'):evaluate(submission,self.labels)
        submission=freeze(self.package,self.draft);submission['claims'][0]['citations'][0]['source_sha256']='2'*64
        submission['submission_sha256']=payload_sha256({k:v for k,v in submission.items() if k!='submission_sha256'})
        with self.assertRaisesRegex(ValueError,'catalog'):evaluate(submission,self.labels)
        for mode in ('duplicate','extra','empty'):
            bad=copy.deepcopy(self.labels)
            if mode=='duplicate':bad['expected_claims'].append(copy.deepcopy(bad['expected_claims'][0]))
            elif mode=='extra':bad['raw_holdout_text']='SYNTHETIC_UNEXPECTED_FIELD'
            else:bad['expected_claims']=[]
            with self.assertRaises(ValueError):evaluate(freeze(self.package,self.draft),bad)

    def test_no_provider_corpus_reads_mutation_or_rawtext_in_submission(self):
        before=copy.deepcopy((self.package,self.draft,self.labels))
        with patch.object(MockProvider,'extract',side_effect=AssertionError('provider called')), \
             patch.object(Path,'read_text',side_effect=AssertionError('file read')):
            submission=freeze(self.package,self.draft);result=evaluate(submission,self.labels)
        for forbidden in ('A shared prediction does not discriminate','Check where model predictions differ','synthetic reasoning'):
            self.assertNotIn(forbidden,json.dumps(submission))
        result['claims'][2]['missing_citations'][0]['reference']['paper_id']='mutated-output'
        self.assertEqual(before,(self.package,self.draft,self.labels))
        self.assertFalse(result['llm_used']);self.assertFalse(result['canonical_update_performed'])

    def test_actual_two_stage_cli_and_label_option_forbidden_during_freeze(self):
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'submission.json'
            freeze_cmd=[sys.executable,'evaluate_synthetic.py','freeze',str(self.root/'revision.json'),str(self.root/'draft.json')]
            first=subprocess.run(freeze_cmd,capture_output=True,check=True);target.write_bytes(first.stdout)
            before=(self.root/'revision.json').read_bytes()
            result=subprocess.run([sys.executable,'evaluate_synthetic.py','evaluate',str(target),'examples/synthetic-holdout-labels.json'],capture_output=True,check=True)
            self.assertEqual(json.loads(result.stdout)['citation_labels']['missing'],1)
            rejected=subprocess.run(freeze_cmd+['--holdout-labels','examples/synthetic-holdout-labels.json'],capture_output=True)
            self.assertNotEqual(rejected.returncode,0);self.assertEqual(rejected.stdout,b'')
            self.assertEqual(before,(self.root/'revision.json').read_bytes())


if __name__=='__main__':unittest.main()
