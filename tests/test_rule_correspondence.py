"""Exact correspondence and ambiguity, not semantic IDs or review rebinding."""
import copy
import json
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import rule_correspondence as r
from observation_provenance import content_sha256
from persona import payload_sha256
from research_workflow import build

ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT/'examples/trajectory-conditions-package.json'
NEW=ROOT/'examples/synthetic-rule-reordered-package.json'


class RuleCorrespondenceTests(unittest.TestCase):
    def setUp(self):
        self.old=json.loads(OLD.read_bytes());self.new=json.loads(NEW.read_bytes())
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)

    def corpus(self,package=None):
        p=package or self.old
        return {**{k:p['persona'][k] for k in ('author_id','version','build_id')},'papers':copy.deepcopy(p['knowledge']['papers'])}

    def cli(self,*args):
        return subprocess.run([sys.executable,str(ROOT/'rule_correspondence.py'),*map(str,args)],cwd=ROOT,capture_output=True)

    def bind(self,p):
        p['persona']['knowledge_papers_sha256']=payload_sha256(p['knowledge']['papers'])
        p['knowledge']['persona_payload_sha256']=payload_sha256(p['persona'])
        return p

    def test_exact_hash_definitions_and_input_forms(self):
        inv=r.inventory(self.old);paper=self.old['knowledge']['papers'][0];rule=self.old['persona']['rules'][0]
        payload={k:v for k,v in rule.items() if k!='rule_id'}
        self.assertEqual(inv['rules'][0]['rule_payload_sha256'],payload_sha256(dict(rule=payload,source_sha256=paper['source_sha256'])))
        self.assertEqual(inv['rules'][0]['observation_content_sha256'],payload_sha256(dict(content_sha256=content_sha256(paper['observations'][0]),paper_id=paper['paper_id'],source_sha256=paper['source_sha256'])))
        self.assertEqual(inv,r.inventory(dict(package=self.old,application='ignored')))
        self.assertEqual(inv,r.inventory(self.old['persona'],self.old['knowledge']))
        self.assertEqual(len(inv['rules']),6)

    def test_same_positions_reorder_and_insertion(self):
        same=r.compare(self.old,self.old)
        self.assertTrue(all(row['status']=='SAME_RULE_PAYLOAD_SAME_POSITION' for row in same['matches']))
        result=r.compare(self.old,self.new)
        self.assertEqual(len(result['matches']),6)
        self.assertTrue(any(row['status']=='SAME_RULE_PAYLOAD_DIFFERENT_POSITION' for row in result['matches']))
        self.assertEqual([row['status'] for row in result['unmatched']],['ONLY_CURRENT_PACKAGE'])
        self.assertTrue(all(not row['changed_rule_fields'] for row in result['matches']))

    def test_changed_year_kind_and_components_visible(self):
        corpus=self.corpus();corpus['papers'][0]['year']=2021;corpus['papers'][0]['kind']='review'
        corpus['papers'][0]['observations'][0]['reasoning']={'uncertainty':dict(text='Invented uncertainty',locator='invented',evidence_quote='synthetic',claim_type='operator_interpretation')}
        result=r.compare(self.old,build(corpus));row=result['matches'][0]
        self.assertEqual(row['status'],'SAME_OBSERVATION_CONTENT_OTHER_FIELDS_CHANGED')
        self.assertEqual(row['changed_rule_fields'],['reasoning','source_kind','year'])
        self.assertEqual(row['changed_component_dimensions'],['uncertainty'])
        self.assertIn('year',row['changed_paper_fields'])
        entry=result['current']['rules'][0]
        component=entry['rule_payload']['reasoning']['uncertainty']
        self.assertEqual(entry['component_sha256']['uncertainty'],payload_sha256(component))

    def test_recorded_quote_and_source_check_not_hidden(self):
        current=copy.deepcopy(self.old)
        current['knowledge']['papers'][0]['observations'][0]['evidence_verification']='EXACT_QUOTE_MATCH_ONLY'
        current['persona']['rules'][0]['evidence_verification']='EXACT_QUOTE_MATCH_ONLY'
        current['knowledge']['papers'][0]['source_verification']='LOCAL_BYTES_SHA256_MATCH';self.bind(current)
        row=r.compare(self.old,current)['matches'][0]
        self.assertEqual(row['status'],'SAME_OBSERVATION_CONTENT_OTHER_FIELDS_CHANGED')
        self.assertIn('evidence_verification',row['changed_rule_fields']);self.assertIn('source_verification',row['changed_paper_fields'])
        self.assertFalse(r.compare(self.old,current)['source_reread'])

    def test_unchanged_rule_hash_still_reports_paper_metadata_changes(self):
        current=copy.deepcopy(self.old)
        current['knowledge']['papers'][0]['source_verification']='LOCAL_BYTES_SHA256_MATCH'
        current['knowledge']['papers'][0]['source_file']='synthetic-private-label.md'
        self.bind(current)
        row=r.compare(self.old,current)['matches'][0]
        self.assertEqual(row['status'],'SAME_RULE_PAYLOAD_SAME_POSITION')
        self.assertEqual(row['changed_rule_fields'],[])
        self.assertEqual(row['changed_paper_fields'],['source_file','source_verification'])

    def test_source_hash_change_is_not_correspondence(self):
        corpus=self.corpus();corpus['papers'][0]['source_sha256']='a'*64
        result=r.compare(self.old,build(corpus))
        self.assertEqual(len(result['matches']),5)
        self.assertEqual({x['status'] for x in result['unmatched']},{'ONLY_PREVIOUS_PACKAGE','ONLY_CURRENT_PACKAGE'})
        group=result['manual_locator_candidates'][0]
        self.assertNotEqual(group['previous_positions'][0]['source_sha256'],group['current_positions'][0]['source_sha256'])

    def test_content_changed_manual_groups_not_inferred(self):
        corpus=self.corpus();obs=corpus['papers'][0]['observations'][0];obs['limitation']='Different supplied limitation'
        duplicate=copy.deepcopy(obs);duplicate['method']='Another supplied method';corpus['papers'][0]['observations'].append(duplicate)
        result=r.compare(self.old,build(corpus))
        self.assertEqual(len(result['matches']),5)
        group=result['manual_locator_candidates'][0]
        self.assertEqual(len(group['previous_positions']),1);self.assertEqual(len(group['current_positions']),2)
        self.assertEqual(group['status'],'MANUAL_REVIEW_CANDIDATE_GROUP_NOT_IDENTITY')

    def test_duplicate_either_side_blocks_all_involved_positions(self):
        corpus=self.corpus();corpus['papers'][0]['observations'].append(copy.deepcopy(corpus['papers'][0]['observations'][0]))
        duplicated=build(corpus)
        for a,b in ((self.old,duplicated),(duplicated,self.old),(duplicated,duplicated)):
            result=r.compare(a,b);self.assertEqual(len(result['matches']),5)
            self.assertEqual(len(result['ambiguous_keys']),2)
            for group in result['ambiguous_keys']:
                self.assertEqual(group['status'],'AMBIGUOUS_DUPLICATE_KEY')
                self.assertTrue(len(group['previous_positions'])>1 or len(group['current_positions'])>1)
            self.assertFalse(result['unmatched'])

    def test_observation_duplicate_conservatively_blocks_unique_full_keys(self):
        corpus=self.corpus();obs=copy.deepcopy(corpus['papers'][0]['observations'][0])
        obs['reasoning']={'uncertainty':dict(text='Invented',locator='invented',evidence_quote='invented',claim_type='operator_interpretation')}
        corpus['papers'][0]['observations'].append(obs);package=build(corpus)
        result=r.compare(package,package)
        self.assertEqual(len(result['matches']),5)
        self.assertEqual([g['key_type'] for g in result['ambiguous_keys']],['observation_content_sha256'])
        self.assertNotEqual(result['previous']['rules'][0]['rule_payload_sha256'],result['previous']['rules'][1]['rule_payload_sha256'])
        self.assertEqual(len(result['ambiguous_keys'][0]['previous_positions']),2)

    def test_grouped_large_duplicate_locations_not_cartesian_pairs(self):
        corpus=self.corpus();base=corpus['papers'][0]['observations'][0]
        corpus['papers'][0]['observations']=[dict(base,method='Invented '+str(i)) for i in range(100)]
        package=build(corpus);result=r.compare(package,package)
        group=result['manual_locator_candidates'][0]
        self.assertEqual(len(group['previous_positions']),100);self.assertEqual(len(group['current_positions']),100)
        self.assertNotIn('candidates',group)

    def test_invalid_bindings_rules_sources_and_catalog_rejected(self):
        with self.assertRaises(ValueError):r.inventory(r.inventory(self.old))
        bad=copy.deepcopy(self.old);bad['persona']['rules'][0]['method']='forged';self.bind(bad)
        with self.assertRaises(ValueError):r.inventory(bad)
        bad=copy.deepcopy(self.old);del bad['knowledge']['papers'][0]['source_sha256'];self.bind(bad)
        with self.assertRaises((ValueError,KeyError)):r.inventory(bad)
        bad=copy.deepcopy(self.old);bad['knowledge']['papers'][0]['authorized']=False;self.bind(bad)
        with self.assertRaises(ValueError):r.inventory(bad)
        with self.assertRaises(ValueError):r.inventory(self.old['persona'])

    def test_author_mismatch_rejected(self):
        corpus=self.corpus();corpus['author_id']='other'
        for paper in corpus['papers']:paper['author_id']='other'
        with self.assertRaises(ValueError):r.compare(self.old,build(corpus))

    def test_no_mutation_and_text_controls(self):
        before=copy.deepcopy(self.old);current=copy.deepcopy(self.new)
        r.compare(self.old,self.new);self.assertEqual(self.old,before);self.assertEqual(self.new,current)
        corpus=self.corpus();corpus['papers'][0]['observations'][0]['method']='synthetic\n\u202e<text>'
        raw=r.render_text(r.inventory(build(corpus)))
        self.assertNotIn('\u202e',raw.decode());self.assertIn('\\u202e',raw.decode())
        self.assertIn('synthetic\\n',raw.decode())

    def test_combined_input_budget_two_and_four_files(self):
        paths=[]
        for i,value in enumerate((self.old['persona'],self.old['knowledge'],self.new['persona'],self.new['knowledge'])):
            path=self.root/str(i);path.write_bytes(json.dumps(value).encode());paths.append(path)
        total=sum(p.stat().st_size for p in paths)
        with patch.object(r,'MAX_INPUT_BYTES',total):
            read=r.bounded_reader();[read(p) for p in paths]
        with patch.object(r,'MAX_INPUT_BYTES',total-1):
            read=r.bounded_reader()
            with self.assertRaises(ValueError):[read(p) for p in paths]
        size=OLD.stat().st_size+NEW.stat().st_size
        with patch.object(r,'MAX_INPUT_BYTES',size-1):
            read=r.bounded_reader();read(OLD)
            with self.assertRaises(ValueError):read(NEW)

    def test_output_limits_before_emission(self):
        result=r.inventory(self.old);size=len(r._encoded(result))
        with patch.object(r,'MAX_OUTPUT_BYTES',size):r._encoded(result)
        with patch.object(r,'MAX_OUTPUT_BYTES',size-1):
            with self.assertRaises(ValueError):r.inventory(self.old)
        with patch.object(r,'MAX_OUTPUT_BYTES',10):
            with self.assertRaises(ValueError):r.render_text(result)

    def test_cli_split_files_exclusive_and_no_partial_error(self):
        paths=[]
        for i,value in enumerate((self.old['persona'],self.old['knowledge'],self.new['persona'],self.new['knowledge'])):
            path=self.root/(str(i)+'.json');path.write_bytes(json.dumps(value).encode());paths.append(path)
        result=self.cli('compare',paths[0],paths[2],'--previous-knowledge',paths[1],'--current-knowledge',paths[3])
        self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(json.loads(result.stdout),r.compare(self.old,self.new))
        target=self.root/'inventory.json';result=self.cli('inventory',OLD,'--output',target)
        self.assertEqual(result.returncode,0,result.stderr);before=target.read_bytes()
        result=self.cli('inventory',OLD,'--output',target);self.assertEqual(result.returncode,1);self.assertEqual(result.stdout,b'');self.assertEqual(target.read_bytes(),before)
        result=self.cli('inventory',target);self.assertEqual(result.returncode,1);self.assertEqual(result.stdout,b'')

    def test_documented_commands_native_paths(self):
        text=(ROOT/'docs/RULE_CORRESPONDENCE.md').read_text(encoding='utf-8').split('## Optional release-comparison attachment',1)[0];count=0
        for block in text.split('```sh\n')[1:]:
            for line in block.split('```',1)[0].splitlines():
                if not line.strip():continue
                parts=shlex.split(line);self.assertNotIn('>',parts)
                argv=[p.replace('OUTPUT',str(self.root)) for p in parts];argv[0]=sys.executable
                result=subprocess.run(argv,cwd=ROOT,capture_output=True)
                self.assertEqual(result.returncode,0,result.stderr);count+=1
        self.assertEqual(count,2)
        native=r'C:\Users\Synthetic Name\Temp'
        args=[p.replace('OUTPUT',native) for p in shlex.split('python rule_correspondence.py inventory sample --output OUTPUT/view.json')]
        self.assertEqual(args[-1],native+'/view.json')


if __name__=='__main__':unittest.main()
