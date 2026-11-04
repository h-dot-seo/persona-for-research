"""Optional synthetic integrated starters remain empty, deferred and unprepared."""
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import review_workspace as workspace
import journey_inputs as inputs
import research_journey as journey
import source_recheck
import test_review_workspace as fixture
from applicability_review import template as context_template, inspect as inspect_context
from argument_map import template as argument_template, inspect as inspect_argument
from pattern_hypotheses import template as pattern_template
from publication_context import template as relation_template
from answer_draft import review_template
from design_scenario import review as inspect_design
from research_workflow import build

ROOT=Path(__file__).resolve().parent
EXTRA={'patterns.json','context.json','publication-relations.json','argument.json','source-selection-template.json',
       'journey-file-selection.json','journey-next-commands.json','START_JOURNEY.txt'}
GOLDEN={'READY.json': 'd98928571b96277563a6cd5c1747365bdc4ddb95851d3a8855f882f539d91dd3', 'START_HERE.txt': '46e98639a91fbe020030bdcd079394977735d1c5f8bf49cfac9de24fdd84356c', 'answer.json': '1d527910ea312e26096109881a0f9e8562fcc4e58ce4393c19ad502ef52129ca', 'design.json': 'dca98791f0b02606f4f788d29443a1a4ac52a39eb950bdf22452301a264b5b5b', 'initial-reader-scope.json': '17a0bc6999d69fd4861c0ebbd58e89e2bca8edb4c2520c0e27c30e4f3b7f03c4', 'initial-review.json': '465bb6de61930e32326a189314efd675c9daf923b2675970c4e40f30f8a98ace', 'initial-review.txt': 'a54ba32ac41976c7cff01b96bc1207b3383eae949066c1100241a2956f0b0e83', 'links.json': 'cb10724b9f8b2d9671364a065ba903840d3ce12862a57549d1393955cde445ec', 'next-commands.json': '66c5aa57daeaab7f8be5cb6eeb94030275c350b29c183f6256cf8597c16a3649', 'package.json': 'e158757d88ec94d8ccb85fee0665da1d8d80e0ceac3c4f1e49f2045c2ac7bbcf', 'reference-catalog.json': 'b1c8f92a2b145be2cc09634f05dbda9e12604137edf5d1f96e37bbe97e38a38a'}


class IntegratedWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.case=fixture.ReviewWorkspaceTests();self.case.setUp();self.addCleanup(self.case.doCleanups)
        self.package=self.case.package;self.dest=self.case.dest
    def start(self,**overrides):
        options=dict(journey_topic='model design',target_context='Synthetic target with unresolved conditions.');options.update(overrides)
        return workspace.create(self.package,self.dest,'Which synthetic explanation?','synthetic-operator',2020,**options)
    def read(self,name):return json.loads((self.dest/name).read_text(encoding='utf-8'))
    def write(self,name,value):(self.dest/name).write_text(json.dumps(value,ensure_ascii=True,indent=2)+'\n',encoding='utf-8')
    def author_pattern(self):
        form=self.read('patterns.json');ref=self.read('reference-catalog.json')['entries'][0]['evidence']['reference']
        form['hypotheses']=[dict(pattern_id='explicit-synthetic',operator_hypothesis='Explicit synthetic pattern hypothesis.',
            scope_note='Only selected invented records; not a scholar trait.',support_refs=[ref],challenge_refs=[],
            alternative_explanation=None,falsification_check=None,uncertainty=None)]
        self.write('patterns.json',form);selection=self.read('journey-file-selection.json');selection['pattern_id']='explicit-synthetic';self.write('journey-file-selection.json',selection)
        return selection

    def test_default_mode_matches_prior_golden_outputs_and_ready_exactly(self):
        ready=self.case.start();dest=self.dest.resolve()
        def normalize(value):
            if isinstance(value,dict):return {key:normalize(v) for key,v in value.items()}
            if isinstance(value,list):return [normalize(v) for v in value]
            if isinstance(value,str):
                if value==sys.executable:return '<PYTHON>'
                for prefix,label in [(str(dest),'<DESTINATION>'),(str(workspace.ROOT),'<REPOSITORY>')]:
                    if value.startswith(prefix):return label+value[len(prefix):].replace('\\','/')
            return value
        actual={}
        for path in self.dest.iterdir():
            value=json.dumps(normalize(json.loads(path.read_text())),sort_keys=True,ensure_ascii=True,separators=(',',':')) if path.suffix=='.json' else path.read_text()
            actual[path.name]=hashlib.sha256(value.encode('utf-8')).hexdigest()
        self.assertEqual(actual,GOLDEN);self.assertEqual(ready,self.read('READY.json'))
        self.assertNotIn('prepared_input_card',ready)

    def test_generated_artifacts_equal_existing_factories_without_new_schema_rules(self):
        ready=self.start();question='Which synthetic explanation?';operator='synthetic-operator'
        expected={'patterns.json':pattern_template(self.package,operator),
            'context.json':context_template(self.package,question,'Synthetic target with unresolved conditions.','model design',2020,operator),
            'publication-relations.json':relation_template(self.package,operator),
            'argument.json':argument_template(self.package,self.read('answer.json'),operator),
            'source-selection-template.json':source_recheck.template(self.package,operator)}
        for name,value in expected.items():self.assertEqual(self.read(name),value)
        self.assertEqual(set(path.name for path in self.dest.iterdir()),set(GOLDEN)|EXTRA)
        self.assertFalse(ready['prepared_input_card']);self.assertFalse(ready['source_selection_activated'])
        self.assertEqual(ready['integrated_journey_status'],'NOT_PREPARED_PATTERN_NOT_SELECTED')
        self.assertEqual(ready['matched_context_observations'],len(expected['context.json']['assessments']))
        self.assertEqual(self.read('journey-next-commands.json')['executed'],False)

    def test_all_choices_stay_empty_deferred_or_null_and_selection_is_relative(self):
        self.start();selection=self.read('journey-file-selection.json')
        self.assertIsNone(selection['pattern_id'])
        for name in inputs.OPTIONAL:self.assertIsNone(selection['artifacts'][name])
        for name in inputs.REQUIRED:
            relative=selection['artifacts'][name];self.assertEqual(inputs._relative(relative),relative);self.assertTrue((self.dest/relative).is_file())
        self.assertEqual(len(set(selection['artifacts'][name] for name in inputs.REQUIRED)),8)
        for name,key in [('patterns.json','hypotheses'),('publication-relations.json','relations'),('argument.json','steps'),('links.json','links'),('answer.json','claims'),('design.json','steps')]:self.assertEqual(self.read(name)[key],[])
        for row in self.read('context.json')['assessments']:
            self.assertEqual(row['decision'],'defer');self.assertIsNone(row['context_comparison']);self.assertIsNone(row['remaining_uncertainty']);self.assertEqual(row['counterevidence_refs'],[])
        self.assertTrue(all(row['source_file'] is None for row in self.read('source-selection-template.json')['sources']))
        self.assertIsNone(self.read('argument.json')['review_sha256'])
        self.assertFalse((self.dest/'input-card.json').exists());self.assertFalse((self.dest/'research-journey.json').exists())

    def test_missing_pattern_rejects_before_artifact_reads_and_unknown_id_not_invented(self):
        self.start();selection=self.read('journey-file-selection.json')
        with patch.object(inputs,'read_source_bytes',side_effect=AssertionError('no input reads')) as read:
            with self.assertRaisesRegex(ValueError,'pattern_id'):inputs.prepare(selection,self.dest)
            read.assert_not_called()
        selection['pattern_id']='not-authored'
        with self.assertRaisesRegex(ValueError,'existing operator pattern ID'):inputs.prepare(selection,self.dest)

    def test_optional_pair_and_invalid_values_reject_before_directory_creation(self):
        for options in ({'journey_topic':'model design'},{'target_context':'target'},
            {'journey_topic':'','target_context':'target'},{'journey_topic':'topic','target_context':'  '},
            {'journey_topic':False,'target_context':'target'},{'journey_topic':{},'target_context':'target'},
            {'journey_topic':'topic','target_context':[]},{'journey_topic':'x'*2001,'target_context':'target'},
            {'journey_topic':'topic','target_context':'x'*2001}):
            with self.assertRaises(ValueError):workspace.create(self.package,self.dest,'q','op',2020,**options)
            self.assertFalse(self.dest.exists())

    def test_unmatched_topic_and_no_observations_stay_valid_empty_starters(self):
        self.start(journey_topic='unmatched synthetic topic');self.assertEqual(self.read('context.json')['assessments'],[])
        self.assertEqual(self.read('READY.json')['matched_context_observations'],0)
        corpus={key:self.package['persona'][key] for key in ('author_id','version','build_id')};corpus['papers']=copy.deepcopy(self.package['knowledge']['papers'])
        for paper in corpus['papers']:paper['observations']=[]
        self.package=build(corpus);self.dest=self.dest.with_name('empty-source-starter');self.start()
        self.assertEqual(self.read('context.json')['assessments'],[]);self.assertEqual(self.read('reference-catalog.json')['entries'],[])
        self.assertEqual(len(self.read('source-selection-template.json')['sources']),2)

    def test_manually_authored_pattern_prepares_fresh_journey_without_source_activation(self):
        self.start();selection=self.author_pattern()
        with patch.object(source_recheck,'audit',side_effect=AssertionError('no source audit')):
            card=inputs.prepare(selection,self.dest);result=inputs.inspect(card,self.dest)
        self.assertEqual(result['status'],'HUMAN_REVIEW_REQUIRED_NOT_RESEARCH_APPROVAL');self.assertFalse(result['automatic_approval'])
        self.assertEqual(result['answer_review_status'],'NOT_SUPPLIED');self.assertFalse(result['source_reread'])
        self.assertEqual(result['argument_review']['steps'],[])
        self.assertEqual(result['pattern_transfer_review']['answer_design_review']['answer']['claims'],[])
        self.assertEqual(result['pattern_transfer_review']['context_review']['decision_counts']['consider'],0)
        self.assertIsNone(card['artifacts']['source_selection'])

    def test_answer_review_links_and_context_edits_do_not_refresh_bindings(self):
        self.start();argument=self.read('argument.json');draft=self.read('answer.json');draft['claims']=[dict(claim_id='synthetic-claim',text='Unverified operator synthesis.',claim_type='operator_synthesis',uncertainty=None,citations=[])]
        with self.assertRaisesRegex(ValueError,'different draft'):inspect_argument(self.package,draft,argument)
        review=review_template(self.package,self.read('answer.json'),'synthetic-reviewer')
        with self.assertRaisesRegex(ValueError,'different draft or declared review'):inspect_argument(self.package,self.read('answer.json'),argument,review)
        links=self.read('links.json');links['operator_id']='changed-synthetic-operator'
        with self.assertRaisesRegex(ValueError,'different evidence'):inspect_design(self.package,links,self.read('design.json'))
        context=self.read('context.json');context['target_context']='Changed target without fresh binding.'
        with self.assertRaisesRegex(ValueError,'stale'):inspect_context(self.package,context)
        self.assertEqual(self.read('argument.json'),argument);self.assertEqual(self.read('answer.json')['claims'],[])

    def test_source_form_does_not_copy_inherited_paths_or_grant_future_read_access(self):
        self.assertTrue(all(paper.get('source_file') for paper in self.package['knowledge']['papers']))
        self.start();selection=self.author_pattern();source=self.read('source-selection-template.json')
        self.assertTrue(all(row['source_file'] is None for row in source['sources']))
        selection['artifacts']['source_selection']='source-selection-template.json'
        with self.assertRaisesRegex(ValueError,'together'):inputs.prepare(selection,self.dest)
        with patch.object(source_recheck,'read_source_bytes',side_effect=AssertionError('no source bytes')):
            with self.assertRaises(ValueError):inputs.prepare(selection,self.dest,source_root=ROOT/'examples/synthetic-sources')

    def test_creation_does_not_prepare_inspect_sources_call_provider_or_run_commands(self):
        before=copy.deepcopy(self.package)
        with patch.object(inputs,'prepare',side_effect=AssertionError('no prepared card')),patch.object(journey,'inspect',side_effect=AssertionError('no integrated journey')),patch.object(source_recheck,'audit',side_effect=AssertionError('no source audit')),patch('corpus_files.read_source_bytes',side_effect=AssertionError('no source bytes')),patch('socket.socket',side_effect=AssertionError('no network')),patch('subprocess.run',side_effect=AssertionError('no command execution')):
            self.start()
        self.assertEqual(self.package,before);self.assertEqual(self.read('package.json'),self.package)

    def test_every_new_artifact_write_failure_preserves_partial_run_without_ready(self):
        original=Path.open
        for index,name in enumerate(sorted(EXTRA)):
            self.dest=self.case.dest.with_name('failed-'+str(index))
            def fail(path,*args,**kwargs):
                if path.name==name and args and args[0]=='x':raise OSError('synthetic write failure')
                return original(path,*args,**kwargs)
            with patch.object(Path,'open',fail):
                with self.assertRaises(OSError):self.start()
            self.assertTrue((self.dest/'package.json').exists());self.assertFalse((self.dest/'READY.json').exists())
            before={path.name:path.read_bytes() for path in self.dest.iterdir()}
            with self.assertRaises(ValueError):self.start()
            self.assertEqual(before,{path.name:path.read_bytes() for path in self.dest.iterdir()})

    def test_all_serialization_finishes_before_directory_or_file_creation(self):
        original=source_recheck.template
        def poison(*args,**kwargs):
            value=original(*args,**kwargs);value['synthetic_unserializable']=object();return value
        with patch.object(source_recheck,'template',side_effect=poison):
            with self.assertRaises(TypeError):self.start()
        self.assertFalse(self.dest.exists())

    def test_shell_like_topic_context_operator_remain_data_and_argument_arrays(self):
        topic='--topic\n$(touch NOT_EXECUTED)';context='--context\n; create-not-authorized';operator='--operator'
        workspace.create(self.package,self.dest,'--question',operator,2020,journey_topic=topic,target_context=context)
        form=self.read('context.json');self.assertEqual(form['topic'],topic);self.assertEqual(form['target_context'],context)
        self.assertNotIn(topic,(self.dest/'START_JOURNEY.txt').read_text());self.assertFalse((self.dest/'NOT_EXECUTED').exists())
        commands=self.read('journey-next-commands.json')['commands'];argv=next(row['argv'] for row in commands if row['argv'][1].endswith('argument_map.py'))
        self.assertIn('--operator-id='+operator,argv)
        run=subprocess.run(argv,cwd=self.case.tmp.name,capture_output=True,timeout=20);self.assertEqual(run.returncode,0,run.stderr)
        self.assertEqual(json.loads(run.stdout)['operator_id'],operator)

    def test_actual_cli_options_generated_commands_and_manual_minimal_completion(self):
        source=Path(self.case.tmp.name)/'synthetic-package.json';source.write_text(json.dumps(self.package),encoding='utf-8')
        base=[sys.executable,str(ROOT/'review_workspace.py'),str(source),str(self.dest),'--question','Which synthetic explanation?','--operator-id','synthetic-operator','--reference-year','2020']
        for flags in (['--journey-topic','model design'],['--target-context','target']):
            run=subprocess.run(base+flags,cwd=self.case.tmp.name,capture_output=True,timeout=20)
            self.assertNotEqual(run.returncode,0);self.assertEqual(run.stdout,b'');self.assertFalse(self.dest.exists())
        run=subprocess.run(base+['--journey-topic','model design','--target-context','Synthetic unresolved target'],cwd=self.case.tmp.name,capture_output=True,timeout=20)
        self.assertEqual(run.returncode,0,run.stderr);self.assertFalse(json.loads(run.stdout)['prepared_input_card'])
        commands=self.read('journey-next-commands.json')['commands']
        for row in commands[:-1]:
            run=subprocess.run(row['argv'],cwd=self.case.tmp.name,capture_output=True,timeout=20);self.assertEqual(run.returncode,0,run.stderr)
        run=subprocess.run(commands[-1]['argv'],capture_output=True,timeout=20);self.assertNotEqual(run.returncode,0);self.assertEqual(run.stdout,b'')
        self.author_pattern();run=subprocess.run(commands[-1]['argv'],capture_output=True,timeout=20);self.assertEqual(run.returncode,0,run.stderr)
        card=json.loads(run.stdout);result=inputs.inspect(card,self.dest);self.assertFalse(result['automatic_approval'])
        self.assertEqual(self.read('initial-review.json')['answer']['claims'],[])


if __name__=='__main__':unittest.main()
