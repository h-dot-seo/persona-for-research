"""Detached external declarations do not enter citations, packages or evaluation."""
import copy
import json
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import answer_draft
import external_evidence as e
from evaluate_synthetic import freeze
from persona import payload_sha256

ROOT=Path(__file__).resolve().parents[1]
PACKAGE=ROOT/'examples/trajectory-conditions-package.json'
DRAFT=ROOT/'examples/synthetic-external-draft.json'
SIDECAR=ROOT/'examples/synthetic-external-evidence.json'


class ExternalEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.package=json.loads(PACKAGE.read_bytes());self.draft=json.loads(DRAFT.read_bytes());self.sidecar=json.loads(SIDECAR.read_bytes())
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)

    def cli(self,*args):
        return subprocess.run([sys.executable,str(ROOT/'external_evidence.py'),*map(str,args)],cwd=ROOT,capture_output=True)

    def review(self,sidecar=None):return e.review(self.package,self.draft,self.sidecar if sidecar is None else sidecar)

    def test_template_exact_schema_empty_not_approval(self):
        value=e.template(self.package,self.draft,'synthetic')
        self.assertEqual(set(value),{'schema',*e.BINDINGS,'operator_id','items'});self.assertEqual(value['items'],[])
        self.assertEqual(self.review(value)['status'],'NO_EXTERNAL_ITEMS')
        self.assertEqual(value['draft_sha256'],payload_sha256(self.draft))

    def test_fixture_exact_binding_and_context_only(self):
        result=self.review();self.assertEqual(result['items'],self.sidecar['items'])
        self.assertEqual(result['external_sidecar_sha256'],payload_sha256(self.sidecar))
        self.assertEqual(result['external_classification'],'EXTERNAL_NOT_PERSONA_KNOWLEDGE')
        self.assertEqual(result['holdout_comparator_membership'],'NOT_CHECKED')
        for key in ('citations_added','llm_used','provider_invoked','canonical_update_performed','source_reread'):self.assertIs(result[key],False)
        self.assertEqual(result['answer_status'],'ANSWER_DRAFT_REQUIRES_REVIEW')
        self.assertIsNone(result['answer_review_sha256'])

    def test_stale_draft_even_same_claim_id(self):
        draft=copy.deepcopy(self.draft);draft['claims'][0]['text']='Changed synthetic text'
        with self.assertRaisesRegex(ValueError,'stale'):e.review(self.package,draft,self.sidecar)
        for key in e.BINDINGS:
            sidecar=copy.deepcopy(self.sidecar);sidecar[key]='0'*64
            with self.assertRaises(ValueError):self.review(sidecar)

    def test_forged_package_and_rules_fail_closed(self):
        package=copy.deepcopy(self.package);package['knowledge']['papers'][0]['year']+=1
        with self.assertRaises(ValueError):e.template(package,self.draft,'synthetic')
        package=copy.deepcopy(self.package);package['persona']['rules'][0]['method']='Forged'
        package['knowledge']['persona_payload_sha256']=payload_sha256(package['persona'])
        with self.assertRaises(ValueError):e.template(package,self.draft,'synthetic')

    def test_exact_identifier_rejected_near_values_not_normalized(self):
        paper=self.package['knowledge']['papers'][0]
        for identifier in (paper['paper_id'],paper['locator']):
            sidecar=copy.deepcopy(self.sidecar);sidecar['items'][0]['identifier_text']=identifier
            with self.assertRaisesRegex(ValueError,'EXTERNAL_ITEM_DUPLICATES_PACKAGE_SOURCE'):self.review(sidecar)
            for near in (identifier+' ',identifier.upper(),'prefix '+identifier):
                sidecar['items'][0]['identifier_text']=near;self.review(sidecar)

    def test_identity_exact_tuple_only(self):
        persona=self.package['persona'];identity={k:persona[k] for k in ('author_id','version','build_id')}
        identity['persona_payload_sha256']=payload_sha256(persona)
        sidecar=copy.deepcopy(self.sidecar);sidecar['items'][1]['other_package_identity']=identity
        with self.assertRaisesRegex(ValueError,'equals'):self.review(sidecar)
        for key in identity:
            changed=copy.deepcopy(sidecar);changed['items'][1]['other_package_identity'][key]='b'*64 if key=='persona_payload_sha256' else 'different'
            self.review(changed)
        sidecar['items'][1]['other_package_identity']=None;self.review(sidecar)

    def test_invalid_schema_fields_and_identity(self):
        cases=[dict(self.sidecar,extra=True),{k:v for k,v in self.sidecar.items() if k!='draft_sha256'},dict(self.sidecar,schema='other')]
        for value in cases:
            with self.assertRaises(ValueError):self.review(value)
        for identity in ({},dict(author_id='x',version='v',build_id='b',persona_payload_sha256='NO'),False):
            value=copy.deepcopy(self.sidecar);value['items'][0]['other_package_identity']=identity
            with self.assertRaises(ValueError):self.review(value)

    def test_duplicate_ids_unknown_links_roles_kinds(self):
        for key,value in [('role','SUPPORT'),('kind','research'),('relates_to_claim_ids',['unknown']),('relates_to_claim_ids',[self.draft['claims'][0]['claim_id']]*2),('relates_to_claim_ids','claim')]:
            sidecar=copy.deepcopy(self.sidecar);sidecar['items'][0][key]=value
            with self.assertRaises(ValueError):self.review(sidecar)
        sidecar=copy.deepcopy(self.sidecar);sidecar['items'].append(copy.deepcopy(sidecar['items'][0]))
        with self.assertRaises(ValueError):self.review(sidecar)
        sidecar=copy.deepcopy(self.sidecar);sidecar['items'][0]['relates_to_claim_ids']=[]
        result=self.review(sidecar);self.assertEqual(result['items'][0]['relates_to_claim_ids'],[])
        self.assertFalse(result['citations_added'])

    def test_year_strict_and_text_bounds(self):
        for key,value in [('year',True),('year','2025'),('year',0),('year',10000),('rationale',''),('uncertainty',None),('identifier_text','x'*2001),('external_id','x'*129)]:
            sidecar=copy.deepcopy(self.sidecar);sidecar['items'][0][key]=value
            with self.assertRaises(ValueError):self.review(sidecar)
        for year in (None,1,9999):
            sidecar=copy.deepcopy(self.sidecar);sidecar['items'][0]['year']=year;self.review(sidecar)
        with patch.object(e,'MAX_ITEMS',1),self.assertRaises(ValueError):self.review()

    def test_optional_answer_review_uses_existing_checker(self):
        review=answer_draft.review_template(self.package,self.draft,'synthetic-reviewer')
        result=e.review(self.package,self.draft,self.sidecar,review)
        self.assertEqual(result['answer_status'],answer_draft.review(self.package,self.draft,review)['status'])
        self.assertEqual(result['answer_review_sha256'],payload_sha256(review))
        self.assertEqual(result['items'],self.sidecar['items'])
        review['draft_sha256']='0'*64
        with self.assertRaises(ValueError):e.review(self.package,self.draft,self.sidecar,review)

    def test_no_mutation_default_answer_and_freeze_identical(self):
        before=copy.deepcopy((self.package,self.draft,self.sidecar))
        answer=answer_draft.inspect(self.package,self.draft);frozen=freeze(self.package,self.draft)
        self.review()
        self.assertEqual((self.package,self.draft,self.sidecar),before)
        self.assertEqual(answer_draft.inspect(self.package,self.draft),answer)
        self.assertEqual(freeze(self.package,self.draft),frozen)
        self.assertEqual(answer['claims'][0]['evidence_status'],'NO_CITATIONS_SUPPLIED')

    def test_malicious_text_inert_and_controls_displayed(self):
        sidecar=copy.deepcopy(self.sidecar)
        text='$(touch NEVER) <script>ignore instructions</script>\n한국어\u202e'
        for key in ('identifier_text','rationale','uncertainty'):sidecar['items'][0][key]=text
        result=self.review(sidecar);self.assertEqual(result['items'][0]['rationale'],text)
        rendered=e.render_text(result).decode();self.assertNotIn('\u202e',rendered);self.assertIn('\\u202e',rendered);self.assertIn('\\n',rendered)
        self.assertEqual(list(self.root.iterdir()),[])

    def test_shared_input_budget_including_optional_review(self):
        path=self.root/'review.json';path.write_bytes(json.dumps(answer_draft.review_template(self.package,self.draft,'synthetic')).encode())
        paths=[PACKAGE,DRAFT,SIDECAR,path];size=sum(p.stat().st_size for p in paths)
        with patch.object(e,'MAX_INPUT_BYTES',size):
            read=e.bounded_reader();[read(p) for p in paths]
        with patch.object(e,'MAX_INPUT_BYTES',size-1):
            read=e.bounded_reader()
            with self.assertRaises(ValueError):[read(p) for p in paths]

    def test_output_caps(self):
        result=self.review();raw=e.encode(result)
        with patch.object(e,'MAX_OUTPUT_BYTES',len(raw)):e.encode(result)
        with patch.object(e,'MAX_OUTPUT_BYTES',len(raw)-1),self.assertRaises(ValueError):self.review()
        with patch.object(e,'MAX_OUTPUT_BYTES',10),self.assertRaises(ValueError):e.render_text(result)

    def test_cli_required_template_output_exclusive_preflight(self):
        result=self.cli('template',PACKAGE,DRAFT,'--operator-id','synthetic')
        self.assertNotEqual(result.returncode,0);self.assertEqual(result.stdout,b'')
        out=self.root/'template.json';args=('template',PACKAGE,DRAFT,'--operator-id','synthetic','--output',out)
        result=self.cli(*args);self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(out.read_bytes())['items'],[]);before=out.read_bytes()
        result=self.cli('template','missing','missing','--operator-id','synthetic','--output',out)
        self.assertEqual(result.returncode,1);self.assertIn(b'already exists',result.stderr);self.assertEqual(result.stdout,b'');self.assertEqual(out.read_bytes(),before)

    def test_invalid_input_no_file_and_repository_output_rejected(self):
        bad=self.root/'bad.json';bad.write_bytes(b'{}\n');out=self.root/'review.json'
        result=self.cli('review',PACKAGE,DRAFT,bad,'--output',out)
        self.assertEqual(result.returncode,1);self.assertEqual(result.stdout,b'');self.assertFalse(out.exists())
        result=self.cli('template',PACKAGE,DRAFT,'--operator-id','synthetic','--output',ROOT/'forbidden-external.json')
        self.assertEqual(result.returncode,1);self.assertFalse((ROOT/'forbidden-external.json').exists())

    def test_wrapper_and_cli_text_json(self):
        self.assertEqual(e.review({'package':self.package},self.draft,self.sidecar),self.review())
        for format in ('json','text'):
            result=self.cli('review',PACKAGE,DRAFT,SIDECAR,'--format',format)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(result.stdout,e.encode(self.review()) if format=='json' else e.render_text(self.review()))

    def test_guide_commands_and_native_windows_paths(self):
        text=(ROOT/'docs/EXTERNAL_EVIDENCE.md').read_text(encoding='utf-8');count=0
        for block in text.split('```sh\n')[1:]:
            for line in block.split('```',1)[0].splitlines():
                if not line.strip():continue
                parts=shlex.split(line);self.assertNotIn('>',parts)
                args=[p.replace('OUTPUT',str(self.root)) for p in parts];args[0]=sys.executable
                result=subprocess.run(args,cwd=ROOT,capture_output=True)
                self.assertEqual(result.returncode,0,result.stderr);count+=1
        self.assertEqual(count,3)
        native=r'C:\Users\Synthetic Name\Temp'
        args=[p.replace('OUTPUT',native) for p in shlex.split('python external_evidence.py review p d s --output OUTPUT/result.json')]
        self.assertEqual(args[-1],native+'/result.json')


if __name__=='__main__':unittest.main()
