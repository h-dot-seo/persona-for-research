import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from review_workspace import create
from corpus_files import load_sources
from research_workflow import build
from prepare_local_manifest import prepare
from curate_local import append_observation
from review_journey import assemble
from strict_json import load

ROOT=Path(__file__).resolve().parents[1]

class ReviewWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.dest=Path(self.tmp.name)/'review'
        manifest=prepare(load(ROOT/'examples/local-selection.json'),ROOT/'examples/synthetic-sources')
        for name in ('research','review'):
            manifest=append_observation(manifest,load(ROOT/f'examples/manual-{name}-card.json'),ROOT/'examples/synthetic-sources')
        self.package=build(load_sources(manifest,ROOT/'examples/synthetic-sources'))

    def start(self):return create(self.package,self.dest,'Which synthetic explanation?','synthetic-operator',2020)

    def test_empty_bound_artifacts_and_all_exact_refs_visible(self):
        ready=self.start();self.assertEqual(ready['status'],'EMPTY_REVIEW_WORKSPACE_READY');self.assertFalse(ready['llm_used'])
        self.assertEqual(load(self.dest/'answer.json')['claims'],[]);self.assertEqual(load(self.dest/'design.json')['steps'],[])
        self.assertEqual(load(self.dest/'links.json')['links'],[])
        catalog=load(self.dest/'reference-catalog.json');self.assertEqual(len(catalog['entries']),4)
        self.assertEqual({r['evidence']['publication_year'] for r in catalog['entries']},{2020,2021})
        self.assertIn('falsification_check',catalog['entries'][0]['missing_reasoning_dimensions'])
        prompts=load(self.dest/'initial-review.json')['review_prompts'];self.assertEqual({p['code'] for p in prompts},{'NO_ANSWER_CLAIMS','NO_PROPOSED_STEPS'})
        self.assertFalse(load(self.dest/'next-commands.json')['executed'])

    def test_empty_paper_and_no_observations_not_successful_modeling(self):
        manifest=prepare(load(ROOT/'examples/local-selection.json'),ROOT/'examples/synthetic-sources')
        self.package=build(load_sources(manifest,ROOT/'examples/synthetic-sources'));self.start()
        cat=load(self.dest/'reference-catalog.json');self.assertEqual(cat['entries'],[]);self.assertEqual(cat['papers_without_observations'],['synthetic-0','synthetic-1'])

    def test_existing_output_missing_parent_and_repository_rejected(self):
        self.dest.mkdir();marker=self.dest/'keep';marker.write_text('synthetic')
        with self.assertRaises(ValueError):self.start()
        self.assertEqual(marker.read_text(),'synthetic')
        for dest in (Path(self.tmp.name)/'missing'/'x',ROOT/'new-review'):
            with self.assertRaises(ValueError):create(self.package,dest,'q','op',2020)
            self.assertFalse(dest.exists())

    def test_invalid_package_or_request_creates_no_directory(self):
        for year in (True,0,10000):
            with self.assertRaises(ValueError):create(self.package,self.dest,'q','op',year)
            self.assertFalse(self.dest.exists())
        self.package['knowledge']['papers'][1]['split']='holdout'
        with self.assertRaises(ValueError):self.start()
        self.assertFalse(self.dest.exists())

    def test_symlink_output_parent_rejected(self):
        real=Path(self.tmp.name)/'real';real.mkdir();link=Path(self.tmp.name)/'link'
        try:link.symlink_to(real,target_is_directory=True)
        except OSError:self.skipTest('symlink unavailable')
        with self.assertRaises(ValueError):create(self.package,link/'out','q','op',2020)
        self.assertFalse((real/'out').exists())

    def test_write_failure_preserves_partial_directory_without_ready(self):
        original=Path.open
        def fail(path,*args,**kwargs):
            if path.name=='answer.json' and args and args[0]=='x':raise OSError('synthetic write failure')
            return original(path,*args,**kwargs)
        with patch.object(Path,'open',fail):
            with self.assertRaises(OSError):self.start()
        self.assertTrue((self.dest/'package.json').exists());self.assertFalse((self.dest/'READY.json').exists())
        with self.assertRaises(ValueError):self.start()

    def test_actual_cli_manual_edit_and_generated_review_command(self):
        source=Path(self.tmp.name)/'intake.json';source.write_text(json.dumps(dict(package=self.package,application={'untrusted':'ignored'})))
        before=source.read_bytes()
        cmd=[sys.executable,str(ROOT/'review_workspace.py'),str(source),str(self.dest),'--question','Synthetic question','--operator-id','synthetic-operator','--reference-year','2020']
        result=subprocess.run(cmd,cwd=self.tmp.name,capture_output=True,text=True,timeout=20);self.assertEqual(result.returncode,0,result.stderr)
        draft=load(self.dest/'answer.json');ref=load(self.dest/'reference-catalog.json')['entries'][2]['evidence']['reference']
        draft['claims']=[dict(claim_id='operator-answer',text='Operator synthetic inference requiring review.',claim_type='operator_synthesis',citations=[dict(reference=ref,role='challenge')],uncertainty=None)]
        (self.dest/'answer.json').write_text(json.dumps(draft))
        proposal=load(self.dest/'design.json');proposal['steps']=[dict(step_id='plan',proposed_action='Compare synthetic predictions.',rationale='Operator supplied rationale.',link_uses=[],hypothesis=None,falsification_check=None,alternative_explanation=None,uncertainty=None)]
        (self.dest/'design.json').write_text(json.dumps(proposal))
        commands=load(self.dest/'next-commands.json')['commands']
        for command in commands:
            result=subprocess.run(command['argv'],cwd=self.tmp.name,capture_output=True,text=True,timeout=20);self.assertEqual(result.returncode,0,result.stderr)
            if command['argv'][1].endswith('review_journey.py'):
                self.assertIn('AFTER_REFERENCE_YEAR',result.stdout);self.assertIn('UNCERTAINTY_NOT_SUPPLIED',result.stdout);self.assertIn('NO_LINKED_EVIDENCE',result.stdout)
        self.assertEqual(before,source.read_bytes())
        self.assertEqual(load(self.dest/'initial-review.json')['answer']['claims'],[])

    def test_control_text_stays_data_and_saved_application_is_not_trusted(self):
        question='Synthetic\nREADY forged; $(touch NOT_EXECUTED)'
        value=dict(package=self.package,application={'text':'SYNTHETIC_UNTRUSTED_ENVELOPE'})
        create(value,self.dest,question,'operator\nnot authenticated',2020)
        self.assertNotIn('SYNTHETIC_UNTRUSTED_ENVELOPE',(self.dest/'package.json').read_text())
        command=load(self.dest/'next-commands.json')['commands'][0]['argv']
        self.assertIn('--question='+question,command)
        self.assertNotIn('\nREADY forged',(self.dest/'initial-review.txt').read_text())
        self.assertFalse((self.dest/'NOT_EXECUTED').exists())
        self.assertEqual(load(self.dest/'answer.json')['question'],question)

    def test_generated_argv_preserves_leading_dash_question_and_operator(self):
        create(self.package,self.dest,'--hypothesis','--operator',2020)
        argv=load(self.dest/'next-commands.json')['commands'][0]['argv']
        result=subprocess.run(argv,cwd=self.tmp.name,capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)
        proposal=json.loads(result.stdout)
        self.assertEqual(proposal['question'],'--hypothesis');self.assertEqual(proposal['operator_id'],'--operator')
