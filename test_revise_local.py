import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from revise_local import template,revise,save_revision
from strict_json import load
from research_workflow import build
from corpus_files import load_sources
from answer_draft import template as answer_template,inspect

ROOT=Path(__file__).resolve().parent

class ReviseLocalTests(unittest.TestCase):
    def setUp(self):
        self.manifest=load(ROOT/'examples/file-corpus.json')
        for paper in self.manifest['papers']:
            for obs in paper['observations']:obs['stance']='support'
        self.root=ROOT/'examples/synthetic-sources'
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.dest=Path(self.tmp.name)/'revision'

    def card(self):
        c=template(self.manifest,'synthetic-1',0)
        c.update(operator_id='synthetic-reviewer',revision_reason='The sentence does not state this counterargument; mark it as an operator interpretation.',new_version='2',new_build_id='synthetic-revised')
        c['observation']['claim_type']='operator_interpretation';c['observation']['stance']='challenge'
        c['observation']['limitation']='Synthetic interpretation; no evidence that an individual author stated it.'
        return c

    def test_before_after_and_explicit_attribution_change_preserved(self):
        before=copy.deepcopy(self.manifest);card=self.card();result,audit=revise(self.manifest,card,self.root)
        self.assertEqual(self.manifest,before);self.assertEqual(result['papers'][0],before['papers'][0])
        self.assertEqual(result['papers'][1]['source_sha256'],before['papers'][1]['source_sha256'])
        self.assertEqual(audit['previous_observation']['claim_type'],'explicit_statement');self.assertEqual(audit['revised_observation']['claim_type'],'operator_interpretation')
        self.assertEqual(audit['revised_observation']['stance'],'challenge');self.assertEqual(result['version'],'2')
        result['papers'][1]['observations'][0]['method']='mutated'
        self.assertNotEqual(audit['revised_observation']['method'],'mutated');self.assertNotEqual(card['observation']['method'],'mutated')

    def test_blank_noop_stale_wrong_index_and_unchanged_identity_reject(self):
        cards=[template(self.manifest,'synthetic-1',0)]
        for field,value in [('manifest_sha256','0'*64),('previous_observation_sha256','0'*64),('observation_index',True),('observation_index',9),('new_version','1'),('new_build_id',self.manifest['build_id'])]:
            c=self.card();c[field]=value;cards.append(c)
        c=self.card();c['observation']=copy.deepcopy(self.manifest['papers'][1]['observations'][0]);cards.append(c)
        for card in cards:
            with patch('revise_local.load_sources',side_effect=AssertionError('read')):
                with self.assertRaises(ValueError):revise(self.manifest,card,self.root)

    def test_prior_bad_quote_can_be_corrected_but_new_bad_quote_rejected(self):
        self.manifest['papers'][1]['observations'][0]['evidence_quote']='SYNTHETIC WRONG QUOTE'
        card=self.card();card['observation']['evidence_quote']='Compare competing models'
        result,audit=revise(self.manifest,card,self.root)
        self.assertEqual(audit['previous_observation']['evidence_quote'],'SYNTHETIC WRONG QUOTE')
        card['observation']['evidence_quote']='ALSO WRONG'
        with self.assertRaises(ValueError):revise(self.manifest,card,self.root)

    def test_holdout_forged_provenance_or_changed_source_rejected(self):
        card=self.card();self.manifest['papers'][0]['split']='holdout'
        with patch('revise_local.load_sources',side_effect=AssertionError('read')):
            with self.assertRaises(ValueError):revise(self.manifest,card,self.root)
        self.manifest['papers'][0]['split']='training';card=self.card();card['observation']['evidence_verification']='EXACT_QUOTE_MATCH_ONLY'
        with self.assertRaises(ValueError):revise(self.manifest,card,self.root)
        self.manifest['papers'][0]['source_sha256']='0'*64
        with self.assertRaises(ValueError):revise(self.manifest,self.card(),self.root)

    def test_aliases_do_not_change_untargeted_observation(self):
        self.manifest['papers'][1]['observations']=self.manifest['papers'][0]['observations']
        card=self.card();result,_=revise(self.manifest,card,self.root)
        self.assertEqual(result['papers'][0]['observations'][0]['claim_type'],'explicit_statement')
        self.assertEqual(result['papers'][1]['observations'][0]['claim_type'],'operator_interpretation')
        self.assertEqual(result,revise(json.loads(json.dumps(self.manifest)),card,self.root)[0])

    def test_new_package_rejects_old_answer_binding(self):
        old=build(load_sources(self.manifest,self.root));draft=answer_template(old,'q','op')
        revised,_=revise(self.manifest,self.card(),self.root);new=build(load_sources(revised,self.root))
        with self.assertRaises(ValueError):inspect(new,draft)

    def test_actual_cli_template_apply_reload_and_no_overwrite(self):
        mp=Path(self.tmp.name)/'original.json';mp.write_text(json.dumps(self.manifest));before=mp.read_bytes()
        def run(*args):return subprocess.run([sys.executable,str(ROOT/'revise_local.py'),*map(str,args)],cwd=self.tmp.name,capture_output=True,text=True,timeout=20)
        result=run('template',mp,'--paper','synthetic-1','--observation-index',0);self.assertEqual(result.returncode,0,result.stderr)
        c=json.loads(result.stdout);c.update(self.card());cp=Path(self.tmp.name)/'card.json';cp.write_text(json.dumps(c))
        result=run('apply',mp,cp,self.dest,'--source-root',self.root);self.assertEqual(result.returncode,0,result.stderr)
        self.assertTrue((self.dest/'READY.json').exists());audit=load(self.dest/'revision-audit.json')
        new=build(load_sources(load(self.dest/'manifest.json'),self.root));self.assertEqual(new['persona']['version'],'2')
        self.assertEqual(audit['status'],'MANUAL_REVISION_REQUIRES_REVIEW');self.assertEqual(mp.read_bytes(),before)
        result=run('apply',mp,cp,self.dest,'--source-root',self.root);self.assertEqual(result.returncode,1);self.assertNotIn('Traceback',result.stderr)

    def test_write_failure_has_no_ready_and_preserves_partial(self):
        original=Path.open
        def fail(path,*args,**kwargs):
            if path.name=='revision-audit.json' and args and args[0]=='x':raise OSError('synthetic write failure')
            return original(path,*args,**kwargs)
        with patch.object(Path,'open',fail):
            with self.assertRaises(OSError):save_revision(self.manifest,self.card(),self.root,self.dest)
        self.assertTrue((self.dest/'manifest.json').exists());self.assertFalse((self.dest/'READY.json').exists())
        with self.assertRaises(ValueError):save_revision(self.manifest,self.card(),self.root,self.dest)

    def test_bundled_manual_reassessment_fixture(self):
        from prepare_local_manifest import prepare
        from curate_local import append_observation
        manifest=prepare(load(ROOT/'examples/local-selection.json'),self.root)
        for name in ('research','review'):
            manifest=append_observation(manifest,load(ROOT/f'examples/manual-{name}-card.json'),self.root)
        result,audit=revise(manifest,load(ROOT/'examples/manual-revision-card.json'),self.root)
        self.assertEqual(audit['previous_observation']['claim_type'],'explicit_statement')
        self.assertEqual(result['papers'][0]['observations'][0]['claim_type'],'operator_interpretation')
        self.assertIn('uncertainty',result['papers'][0]['observations'][0]['reasoning'])
        self.assertEqual(result['papers'][1],manifest['papers'][1])

    def test_existing_verified_or_mock_component_cannot_be_silently_reclassified(self):
        self.manifest['papers'][1]['observations'][0]['evidence_verification']='EXACT_QUOTE_MATCH_ONLY'
        with self.assertRaises(ValueError):template(self.manifest,'synthetic-1',0)
        del self.manifest['papers'][1]['observations'][0]['evidence_verification']
        component=dict(text='Synthetic candidate',locator='synthetic section 1',evidence_quote='Compare competing models',claim_type='operator_interpretation',origin='operator_reviewed_mock_candidate',candidate_id='synthetic-candidate',candidate_bundle_sha256='a'*64,operator_review_sha256='b'*64,proposed_claim_type='explicit_statement')
        self.manifest['papers'][1]['observations'][0]['reasoning']={'uncertainty':component}
        with self.assertRaises(ValueError):template(self.manifest,'synthetic-1',0)

    def test_bad_new_quote_creates_no_directory_and_output_path_guards(self):
        card=self.card();card['observation']['evidence_quote']='SYNTHETIC WRONG QUOTE'
        with self.assertRaises(ValueError):save_revision(self.manifest,card,self.root,self.dest)
        self.assertFalse(self.dest.exists())
        for dest in (ROOT/'new-revision',Path(self.tmp.name)/'missing'/'out'):
            with self.assertRaises(ValueError):save_revision(self.manifest,self.card(),self.root,dest)
            self.assertFalse(dest.exists())
        real=Path(self.tmp.name)/'real';real.mkdir();link=Path(self.tmp.name)/'link'
        try:link.symlink_to(real,target_is_directory=True)
        except OSError:return
        with self.assertRaises(ValueError):save_revision(self.manifest,self.card(),self.root,link/'out')
        self.assertFalse((real/'out').exists())
