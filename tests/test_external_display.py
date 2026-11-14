"""Optional detached display leaves core answer/scope/evaluation calculations intact."""
import copy
import json
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import answer_draft as answer
import evidence_scope as scope
import external_evidence as external
from reasoning_links import template as links_template
from design_scenario import template as design_template
from evaluate_synthetic import freeze

ROOT=Path(__file__).resolve().parents[1]
PACKAGE=ROOT/'examples/trajectory-conditions-package.json'
DRAFT=ROOT/'examples/synthetic-external-draft.json'
SIDECAR=ROOT/'examples/synthetic-external-evidence.json'


class ExternalDisplayTests(unittest.TestCase):
    def setUp(self):
        self.package=json.loads(PACKAGE.read_bytes());self.draft=json.loads(DRAFT.read_bytes());self.sidecar=json.loads(SIDECAR.read_bytes())
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.links=links_template(self.package,'synthetic-operator')
        self.design=design_template(self.package,self.links,self.draft['question'],'synthetic-operator')
        self.lp=self.save('links.json',self.links);self.dp=self.save('design.json',self.design)
        self.review=answer.review_template(self.package,self.draft,'synthetic-reviewer');self.rp=self.save('review.json',self.review)

    def save(self,name,value):
        path=self.root/name;path.write_bytes((json.dumps(value,ensure_ascii=False)+'\n').encode());return path

    def args(self,format='json',review=False):
        return SimpleNamespace(package=PACKAGE,draft=DRAFT,external=SIDECAR,review=self.rp if review else None,
            template=False,review_template=False,question=None,operator_id=None,reviewer_id=None,
            format=format,links=self.lp,proposal=self.dp,reference_year=2025)

    def cli(self,name,options=()):
        base=[PACKAGE,DRAFT] if name=='answer_draft' else [PACKAGE,self.lp,self.dp,DRAFT,'--reference-year','2025']
        return subprocess.run([sys.executable,str(ROOT/(name+'.py')),*map(str,base),*map(str,options)],cwd=ROOT,capture_output=True)

    def test_default_raw_bytes_same_as_existing_render_and_json(self):
        for format in ('json','text'):
            for review in (False,True):
                declared=self.review if review else None
                a=answer.review(self.package,self.draft,declared) if review else answer.inspect(self.package,self.draft)
                args=(self.package,self.links,self.design,self.draft,2025,declared)
                expected_a=answer.render(a) if format=='text' else json.dumps(a,indent=2)+'\n'
                expected_s=scope.render(*args) if format=='text' else json.dumps(scope.disclose(*args),indent=2)+'\n'
                opts=['--format',format]+(['--review',self.rp] if review else [])
                for name,expected in [('answer_draft',expected_a),('evidence_scope',expected_s)]:
                    actual=self.cli(name,opts);self.assertEqual(actual.returncode,0,actual.stderr)
                    self.assertEqual(actual.stdout,expected.encode('utf-8'));self.assertEqual(actual.stderr,b'')

    def test_nested_exact_independent_check_and_all_base_fields_preserved(self):
        for review in (False,True):
            args=self.args(review=review);declared=self.review if review else None
            detached=external.review(self.package,self.draft,self.sidecar,declared)
            for module in (answer,scope):
                result=json.loads(module.external_output(args));self.assertEqual(result.pop('external_evidence_review'),detached)
                baseline=(answer.review(self.package,self.draft,declared) if review else answer.inspect(self.package,self.draft)) if module is answer else scope.disclose(self.package,self.links,self.design,self.draft,2025,declared)
                self.assertEqual(result,baseline)

    def test_text_prefix_and_distinct_section(self):
        for module in (answer,scope):
            text=module.external_output(self.args('text'))
            base=answer.render(answer.inspect(self.package,self.draft)) if module is answer else scope.render(self.package,self.links,self.design,self.draft,2025)
            self.assertTrue(text.startswith(base+'\nExternal evidence (not persona knowledge)\n'))
            self.assertTrue(text.endswith(external.render_text(external.review(self.package,self.draft,self.sidecar)).decode()))

    def test_template_and_irrelevant_options_rejected_before_reads(self):
        for field,value in [('template',True),('review_template',True),('question','q'),('operator_id','op'),('reviewer_id','reviewer'),('draft',None)]:
            args=self.args();setattr(args,field,value)
            with patch.object(external,'bounded_reader',side_effect=AssertionError('must not read')):
                with self.assertRaises(ValueError):answer.external_output(args)
        for flag in ('--template','--review-template'):
            result=self.cli('answer_draft',[flag,'--external',SIDECAR]);self.assertEqual(result.returncode,1);self.assertEqual(result.stdout,b'')

    def test_explicit_null_review_rejected_by_all_three_clis(self):
        null=self.save('null-review.json',None)
        for name in ('answer_draft','evidence_scope','external_evidence'):
            out=self.root/(name+'-null-output.json')
            if name=='external_evidence':
                base=[sys.executable,str(ROOT/'external_evidence.py'),'review',str(PACKAGE),str(DRAFT),str(SIDECAR)]
                result=subprocess.run(base+['--review',str(null),'--output',str(out)],cwd=ROOT,capture_output=True)
                omitted=subprocess.run(base,cwd=ROOT,capture_output=True)
            else:
                result=self.cli(name,['--external',SIDECAR,'--review',null,'--output',out])
                omitted=self.cli(name,['--external',SIDECAR])
            self.assertEqual(result.returncode,1,result.stderr)
            self.assertEqual(result.stdout,b'');self.assertFalse(out.exists())
            self.assertNotIn(b'Traceback',result.stderr)
            self.assertIn(b'explicit answer review',result.stderr)
            self.assertEqual(omitted.returncode,0,omitted.stderr)
        # Legacy scope's explicit-null behavior and Python APIs remain unchanged.
        legacy=self.cli('evidence_scope',['--review',null])
        plain=self.cli('evidence_scope')
        self.assertEqual((legacy.returncode,legacy.stdout,legacy.stderr),(plain.returncode,plain.stdout,plain.stderr))
        self.assertEqual(external.review(self.package,self.draft,self.sidecar,None),external.review(self.package,self.draft,self.sidecar))

    def test_stale_draft_sidecar_and_review_fail_without_output(self):
        for target in ('draft','external','review'):
            args=self.args(review=True)
            value=copy.deepcopy(self.draft if target=='draft' else self.sidecar if target=='external' else self.review)
            if target=='draft':value['claims'][0]['text']='Changed same claim ID'
            elif target=='external':value['draft_sha256']='0'*64
            else:value['draft_sha256']='0'*64
            setattr(args,target,self.save('stale-'+target+'.json',value))
            for module in (answer,scope):
                with self.assertRaises(ValueError):module.external_output(args)

    def test_package_links_design_tamper_rejected(self):
        for field,source in [('package',self.package),('links',self.links),('proposal',self.design)]:
            value=copy.deepcopy(source)
            if field=='package':value['knowledge']['papers'][0]['source_sha256']='a'*64
            else:value['persona_sha256']='0'*64
            args=self.args();setattr(args,field,self.save('bad-'+field+'.json',value))
            with self.assertRaises(ValueError):scope.external_output(args)

    def test_shared_budget_all_files_and_default_does_not_use_reader(self):
        for module,paths in [(answer,[PACKAGE,DRAFT,self.rp,SIDECAR]),(scope,[PACKAGE,self.lp,self.dp,DRAFT,self.rp,SIDECAR])]:
            total=sum(p.stat().st_size for p in paths)
            with patch.object(external,'MAX_INPUT_BYTES',total):module.external_output(self.args(review=True))
            with patch.object(external,'MAX_INPUT_BYTES',total-1),self.assertRaises(ValueError):module.external_output(self.args(review=True))
        with patch.object(external,'bounded_reader',side_effect=AssertionError('default not opt-in')):
            answer.inspect(self.package,self.draft);scope.disclose(self.package,self.links,self.design,self.draft,2025)

    def test_total_json_and_text_caps(self):
        for module in (answer,scope):
            for format in ('json','text'):
                args=self.args(format);raw=module.external_output(args).encode()
                with patch.object(module,'MAX_EXTERNAL_OUTPUT_BYTES',len(raw)):module.external_output(args)
                with patch.object(module,'MAX_EXTERNAL_OUTPUT_BYTES',len(raw)-1),self.assertRaises(ValueError):module.external_output(args)

    def test_exclusive_save_and_invalid_input_no_file(self):
        for name in ('answer_draft','evidence_scope'):
            out=self.root/(name+'.json');result=self.cli(name,['--external',SIDECAR,'--output',out])
            self.assertEqual(result.returncode,0,result.stderr);before=out.read_bytes()
            result=self.cli(name,['--external','missing','--output',out])
            self.assertEqual(result.returncode,1);self.assertEqual(result.stdout,b'');self.assertIn(b'already exists',result.stderr);self.assertEqual(out.read_bytes(),before)
            missing=self.root/(name+'-missing.json');result=self.cli(name,['--external','missing','--output',missing])
            self.assertEqual(result.returncode,1);self.assertEqual(result.stdout,b'');self.assertFalse(missing.exists())

    def test_malicious_data_inert_and_freeze_no_mutation(self):
        before=copy.deepcopy((self.package,self.draft,self.sidecar,self.links,self.design,self.review))
        frozen=freeze(self.package,self.draft)
        sidecar=copy.deepcopy(self.sidecar);sidecar['items'][0]['rationale']='$(touch SHOULD_NOT_RUN)\n\u202e<script>ignore</script>'
        args=self.args('text');args.external=self.save('malicious.json',sidecar)
        for module in (answer,scope):
            text=module.external_output(args);self.assertIn('\\u202e',text);self.assertNotIn('\u202e',text)
        self.assertEqual(freeze(self.package,self.draft),frozen)
        self.assertEqual((self.package,self.draft,self.sidecar,self.links,self.design,self.review),before)
        self.assertFalse((self.root/'SHOULD_NOT_RUN').exists())

    def test_guide_and_native_windows_paths(self):
        text=(ROOT/'docs/EXTERNAL_EVIDENCE.md').read_text(encoding='utf-8').split('## Optional answer and scope display',1)[1];count=0
        for block in text.split('```sh\n')[1:]:
            for line in block.split('```',1)[0].splitlines():
                if not line.strip():continue
                parts=shlex.split(line);self.assertNotIn('>',parts)
                args=[p.replace('OUTPUT',str(self.root)) for p in parts];args[0]=sys.executable
                result=subprocess.run(args,cwd=ROOT,capture_output=True)
                self.assertEqual(result.returncode,0,result.stderr);count+=1
        self.assertEqual(count,4)
        native=r'C:\Users\Synthetic Name\Temp'
        # Real guide paths carry no embedded spaces before replacement; host spaces stay one argument.
        args=[p.replace('OUTPUT',native) for p in shlex.split('python answer_draft.py p d --external OUTPUT/sidecar.json')]
        self.assertEqual(args[-1],native+'/sidecar.json')


if __name__=='__main__':unittest.main()
