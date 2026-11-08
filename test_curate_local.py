import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from curate_local import template, append_observation
from prepare_local_manifest import prepare
from corpus_files import load_sources
from research_workflow import build, apply

ROOT=Path(__file__).resolve().parent

class ManualObservationTests(unittest.TestCase):
    def setUp(self):
        self.root=ROOT/'examples/synthetic-sources'
        self.manifest=prepare(json.loads((ROOT/'examples/local-selection.json').read_text()),self.root)
        self.obs=json.loads((ROOT/'examples/file-corpus.json').read_text())['papers'][0]['observations'][0]
        self.obs['stance']='support'

    def card(self,paper='synthetic-0'):
        card=template(self.manifest,paper);card['observation']=copy.deepcopy(self.obs);return card

    def test_template_has_no_copied_source_or_default_attribution(self):
        card=template(self.manifest,'synthetic-0')
        self.assertIsNone(card['observation']['claim_type']);self.assertIsNone(card['observation']['stance'])
        self.assertNotIn('Compare competing models',json.dumps(card))
        with self.assertRaises(ValueError):append_observation(self.manifest,card,self.root)

    def test_append_detached_preserves_metadata_and_no_verification_claims(self):
        card=self.card();result=append_observation(self.manifest,card,self.root)
        self.assertEqual(result['papers'][0]['observations'],[self.obs]);self.assertEqual(self.manifest['papers'][0]['observations'],[])
        self.assertNotIn('evidence_verification',result['papers'][0]['observations'][0])
        result['papers'][0]['observations'][0]['method']='changed';self.assertNotEqual(card['observation']['method'],'changed')
        self.assertEqual(result['papers'][1],self.manifest['papers'][1])

    def test_stale_or_wrong_paper_rejected_before_reads(self):
        for mutate in (lambda c:c.update(paper_id='missing'),lambda c:c.update(manifest_sha256='0'*64)):
            card=self.card();mutate(card)
            with patch('curate_local.load_sources',side_effect=AssertionError('read')):
                with self.assertRaises(ValueError):append_observation(self.manifest,card,self.root)
        updated=append_observation(self.manifest,self.card(),self.root)
        with self.assertRaisesRegex(ValueError,'stale'):append_observation(updated,self.card(),self.root)

    def test_holdout_rejected_before_io_even_in_unselected_paper(self):
        card=self.card();self.manifest['papers'][1]['split']='holdout'
        with patch('curate_local.load_sources',side_effect=AssertionError('read')):
            with self.assertRaises(ValueError):append_observation(self.manifest,card,self.root)

    def test_bad_quote_locator_and_reasoning_quote_rejected(self):
        for key,value in [('evidence_quote','Not present synthetic quote'),('locator','absent')]:
            card=self.card();card['observation'][key]=value
            with self.assertRaises(ValueError):append_observation(self.manifest,card,self.root)
        card=self.card();card['observation']['reasoning']={'falsification_check':dict(text='Synthetic check',locator=self.obs['locator'],evidence_quote='Not present',claim_type='operator_interpretation')}
        with self.assertRaises(ValueError):append_observation(self.manifest,card,self.root)

    def test_forged_provenance_unknown_fields_and_incomplete_cards_rejected(self):
        for key in ('evidence_verification','origin','candidate_id','unknown'):
            card=self.card();card['observation'][key]='forged'
            with self.assertRaises(ValueError):append_observation(self.manifest,card,self.root)
        for value in (None,[],{'unknown':{}},{'uncertainty':{'text':'x'}}):
            card=self.card();card['observation']['reasoning']=value
            with self.assertRaises(ValueError):append_observation(self.manifest,card,self.root)

    def test_existing_bad_observation_cannot_be_preserved_unchecked(self):
        manifest=copy.deepcopy(self.manifest);bad=copy.deepcopy(self.obs);bad['evidence_quote']='missing'
        manifest['papers'][1]['observations']=[bad]
        card=template(manifest,'synthetic-0');card['observation']=self.obs
        with self.assertRaises(ValueError):append_observation(manifest,card,self.root)

    def test_actual_cli_prepare_template_append_research_review_apply(self):
        def run(*args):
            result=subprocess.run([sys.executable,*map(str,args)],cwd=ROOT,capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stderr);return json.loads(result.stdout)
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'prepared.json';path.write_text(json.dumps(run('prepare_local_manifest.py','examples/local-selection.json','--source-root',self.root)))
            source_before={p:p.read_bytes() for p in self.root.glob('*.md')}
            for paper,stance in [('synthetic-0','support'),('synthetic-1','challenge')]:
                card=run('curate_local.py','template',path,'--paper',paper)
                card['observation']=copy.deepcopy(self.obs);card['observation']['stance']=stance
                card['observation']['claim_type']='operator_interpretation' if stance=='challenge' else 'explicit_statement'
                card['observation']['reasoning']={'alternative_explanation':dict(text='Operator proposes comparing another synthetic explanation.',locator=self.obs['locator'],evidence_quote=self.obs['evidence_quote'],claim_type='operator_interpretation')}
                cp=Path(d)/'card.json';cp.write_text(json.dumps(card));result=run('curate_local.py','append',path,cp,'--source-root',self.root);path.write_text(json.dumps(result))
            package=build(load_sources(json.loads(path.read_text()),self.root));answer=apply(package,'Which synthetic explanation?','model design')
            self.assertEqual(len(answer['steps']),2)
            self.assertEqual([s['evidence_verification'] for s in answer['steps']],['EXACT_QUOTE_MATCH_ONLY']*2)
            self.assertEqual([r['stance'] for r in package['persona']['rules']],['support','challenge'])
            self.assertEqual(source_before,{p:p.read_bytes() for p in source_before})

    def test_bundled_documented_cards_build_review_interpretation(self):
        result=self.manifest
        for name in ('research','review'):
            card=json.loads((ROOT/f'examples/manual-{name}-card.json').read_text())
            result=append_observation(result,card,self.root)
        rules=build(load_sources(result,self.root))['persona']['rules']
        self.assertEqual([r['source_kind'] for r in rules],['research','review'])
        self.assertEqual([r['year'] for r in rules],[2020,2021])
        self.assertEqual([r['claim_type'] for r in rules],['explicit_statement','operator_interpretation'])
        self.assertEqual(rules[1]['reasoning']['uncertainty']['claim_type'],'operator_interpretation')
        self.assertNotIn('input_inventory',result['papers'][0]);self.assertNotIn('input_inventory',result['papers'][1])

    def test_cli_bad_quote_emits_no_json_and_preserves_input_files(self):
        with tempfile.TemporaryDirectory() as d:
            mp=Path(d)/'manifest.json';cp=Path(d)/'card.json';card=self.card();card['observation']['evidence_quote']='MISSING_SYNTHETIC'
            mp.write_text(json.dumps(self.manifest));cp.write_text(json.dumps(card));before=(mp.read_bytes(),cp.read_bytes())
            result=subprocess.run([sys.executable,str(ROOT/'curate_local.py'),'append',str(mp),str(cp),'--source-root',str(self.root)],capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,1);self.assertEqual(result.stdout,'');self.assertNotIn('Traceback',result.stderr)
            self.assertEqual(before,(mp.read_bytes(),cp.read_bytes()))

    def test_aliased_empty_lists_only_target_paper_changes(self):
        self.manifest['papers'][1]['observations']=self.manifest['papers'][0]['observations']
        card=self.card();result=append_observation(self.manifest,card,self.root)
        detached=json.loads(json.dumps(self.manifest))
        self.assertEqual(result,append_observation(detached,card,self.root))
        self.assertEqual([len(p['observations']) for p in result['papers']],[1,0])
        self.assertEqual([len(p['observations']) for p in self.manifest['papers']],[0,0])

    def test_existing_annotations_preserved_not_a_sanitization_boundary(self):
        self.manifest['operator_note']='SYNTHETIC_EXISTING_PRIVATE_ANNOTATION'
        card=self.card();result=append_observation(self.manifest,card,self.root)
        self.assertEqual(result['operator_note'],self.manifest['operator_note'])
        package=build(load_sources(result,self.root))
        self.assertNotIn('SYNTHETIC_EXISTING_PRIVATE_ANNOTATION',json.dumps(package))
