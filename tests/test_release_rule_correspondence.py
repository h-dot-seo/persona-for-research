"""Opt-in release correspondence never changes the legacy report contract."""
import copy
import io
import json
import shlex
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

import compare_releases as c
import rule_correspondence as r
from persona import payload_sha256
from research_workflow import build

ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT/'examples/trajectory-conditions-package.json'
NEW=ROOT/'examples/synthetic-rule-reordered-package.json'


class ReleaseRuleCorrespondenceTests(unittest.TestCase):
    def setUp(self):
        self.old=json.loads(OLD.read_bytes());self.new=json.loads(NEW.read_bytes())
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)

    def cli(self,*args):
        return subprocess.run([sys.executable,str(ROOT/'compare_releases.py'),*map(str,args)],cwd=ROOT,capture_output=True)

    def save(self,value,name='candidate.json'):
        p=self.root/name;p.write_bytes((json.dumps(value,ensure_ascii=False)+'\n').encode());return p

    def corpus(self):
        return {**{k:self.old['persona'][k] for k in ('author_id','version','build_id')},'papers':copy.deepcopy(self.old['knowledge']['papers'])}

    def test_default_exact_serialized_compare_status_and_keys(self):
        for path,value in ((OLD,self.old),(NEW,self.new)):
            base=c.compare(self.old,value)
            result=self.cli(OLD,path)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(result.stdout,(json.dumps(base,ensure_ascii=False,indent=2)+'\n').encode())
            self.assertNotIn('rule_correspondence',base)
        self.assertEqual(c.compare(self.old,self.old)['status'],'NO_EVIDENCE_OR_RULE_CHANGE')
        self.assertEqual(c.compare(self.old,self.new)['status'],'REVIEW_REQUIRED')

    def test_opt_in_exact_independent_result_and_unchanged_base(self):
        result=json.loads(c.correspondence_output(OLD,NEW))
        self.assertEqual(result.pop('rule_correspondence'),r.compare(self.old,self.new))
        self.assertEqual(result,c.compare(self.old,self.new))
        cli=self.cli(OLD,NEW,'--rule-correspondence')
        self.assertEqual(cli.returncode,0,cli.stderr);self.assertEqual(cli.stdout,c.correspondence_output(OLD,NEW))

    def test_duplicate_and_metadata_results_not_promoted(self):
        for duplicate in (False,True):
            corpus=self.corpus()
            if duplicate:corpus['papers'][0]['observations'].append(copy.deepcopy(corpus['papers'][0]['observations'][0]))
            else:corpus['papers'][0]['year']+=1
            package=build(corpus);path=self.save(package)
            result=json.loads(c.correspondence_output(OLD,path))
            self.assertEqual(result['rule_correspondence'],r.compare(self.old,package))
            self.assertEqual(result['status'],c.compare(self.old,package)['status'])
            self.assertFalse(result['canonical_update_performed'])
            if duplicate:self.assertTrue(result['rule_correspondence']['ambiguous_keys'])
            else:self.assertIn('year',result['rule_correspondence']['matches'][0]['changed_rule_fields'])

    def test_stricter_rule_source_check_only_on_opt_in(self):
        malformed=copy.deepcopy(self.old);malformed['persona']['rules'][0]['method']='inconsistent synthetic rule'
        malformed['knowledge']['persona_payload_sha256']=payload_sha256(malformed['persona'])
        path=self.save(malformed)
        self.assertEqual(self.cli(OLD,path).returncode,0)
        out=self.root/'should-not-exist.json';result=self.cli(OLD,path,'--rule-correspondence','--output',out)
        self.assertEqual(result.returncode,1);self.assertEqual(result.stdout,b'');self.assertFalse(out.exists())
        self.assertIn(b'rules do not match',result.stderr)

    def test_tampered_binding_rejected_in_both_modes(self):
        bad=copy.deepcopy(self.old);bad['knowledge']['papers'][0]['year']+=1;path=self.save(bad)
        for options in ((),('--rule-correspondence',)):
            result=self.cli(OLD,path,*options);self.assertEqual(result.returncode,1);self.assertEqual(result.stdout,b'')

    def test_shared_budget_exact_boundary_and_default_independence(self):
        size=OLD.stat().st_size+NEW.stat().st_size
        with patch.object(r,'MAX_INPUT_BYTES',size):c.correspondence_output(OLD,NEW)
        with patch.object(r,'MAX_INPUT_BYTES',size-1):
            with self.assertRaises(ValueError):c.correspondence_output(OLD,NEW)
        # Legacy main must not consult the new shared reader at all.
        with patch.object(c,'correspondence_output',side_effect=AssertionError('not opted in')),patch.object(c,'emit') as emit,patch.object(sys,'argv',['compare_releases.py',str(OLD),str(NEW)]):
            c.main();self.assertEqual(json.loads(emit.call_args.args[1]),c.compare(self.old,self.new))

    def test_combined_output_budget_not_only_nested_report(self):
        raw=c.correspondence_output(OLD,NEW)
        with patch.object(c,'MAX_CORRESPONDENCE_OUTPUT_BYTES',len(raw)):
            self.assertEqual(c.correspondence_output(OLD,NEW),raw)
        with patch.object(c,'MAX_CORRESPONDENCE_OUTPUT_BYTES',len(raw)-1):
            with self.assertRaisesRegex(ValueError,'combined release'):c.correspondence_output(OLD,NEW)
        with patch.object(c,'MAX_CORRESPONDENCE_OUTPUT_BYTES',1),patch.object(c,'emit') as emit,patch.object(sys,'argv',['compare_releases.py',str(OLD),str(NEW),'--rule-correspondence']),redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):c.main()
            emit.assert_not_called()

    def test_exclusive_save_preflight_and_no_mutation(self):
        before=(OLD.read_bytes(),NEW.read_bytes());out=self.root/'result.json'
        result=self.cli(OLD,NEW,'--rule-correspondence','--output',out)
        self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(out.read_bytes(),c.correspondence_output(OLD,NEW))
        saved=out.read_bytes();result=self.cli('missing-previous','missing-current','--rule-correspondence','--output',out)
        self.assertEqual(result.returncode,1);self.assertEqual(result.stdout,b'');self.assertIn(b'already exists',result.stderr)
        self.assertEqual(out.read_bytes(),saved);self.assertEqual((OLD.read_bytes(),NEW.read_bytes()),before)

    def test_wrapper_and_old_api_not_enriched(self):
        old=self.save({'package':self.old,'application':'ignored'},'wrapper-old.json')
        new=self.save({'package':self.new,'boundary':'ignored'},'wrapper-new.json')
        self.assertEqual(json.loads(c.correspondence_output(old,new))['rule_correspondence'],r.compare(self.old,self.new))
        self.assertNotIn('rule_correspondence',c.compare(self.old,self.new))

    def test_guide_native_paths_after_split(self):
        text=(ROOT/'docs/RULE_CORRESPONDENCE.md').read_text(encoding='utf-8').split('## Optional release-comparison attachment',1)[1]
        count=0
        for block in text.split('```sh\n')[1:]:
            for line in block.split('```',1)[0].splitlines():
                if not line.strip():continue
                parts=shlex.split(line);self.assertNotIn('>',parts)
                args=[part.replace('OUTPUT',str(self.root)) for part in parts];args[0]=sys.executable
                result=subprocess.run(args,cwd=ROOT,capture_output=True)
                self.assertEqual(result.returncode,0,result.stderr);count+=1
        self.assertEqual(count,1)
        native=r'C:\Users\Synthetic Name\Temp'
        args=[part.replace('OUTPUT',native) for part in shlex.split('python compare_releases.py old new --rule-correspondence --output OUTPUT/report.json')]
        self.assertEqual(args[-1],native+'/report.json')


if __name__=='__main__':unittest.main()
