"""Descriptive coverage and evidenced production, never replacement validation."""
import ast
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import answer_proposals as answer
import argument_proposals as argument
import artifact_schemas as catalog
from persona import payload_sha256
from tests.test_handoff_text import cases

ROOT=Path(__file__).resolve().parents[1]
PATTERN=re.compile(r'^(?:persona\.[a-z0-9-]+|human-validation-record|synthetic-answer-[a-z-]+)\.v[0-9]+$')


def inventory():
    found={}
    for path in list(ROOT.glob('*.py'))+[ROOT/'tests/timing.py',ROOT/'tests/capacity.py']:
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
            if isinstance(node,ast.Constant) and isinstance(node.value,str) and PATTERN.fullmatch(node.value):
                found.setdefault(node.value,set()).add(path.relative_to(ROOT).as_posix())
    for module,name in ((answer,'answer_proposals.py'),(argument,'argument_proposals.py')):
        for table in module.SCHEMAS.values():
            for value in table.values():found.setdefault(value,set()).add(name)
    return found


class ArtifactSchemaTests(unittest.TestCase):
    def setUp(self):self.rows=catalog.catalog()['records']

    def test_identifier_completeness_dynamic_and_mentions_not_attribution(self):
        found=inventory()
        rows={r['schema_id']:r for r in self.rows if r['schema_id'] is not None and r['category']!='fixture-only'}
        self.assertEqual(set(found),set(rows))
        for key,mentions in found.items():self.assertEqual(sorted(mentions),rows[key]['source_mentions'])
        for module in (answer,argument):
            for version,table in module.SCHEMAS.items():
                for role,schema in table.items():
                    row=rows[schema];self.assertEqual(row['role'],role)
                    self.assertEqual(row['mode'],'default' if version==1 else 'opt-in')
        self.assertIsNone(rows['persona.saved-output.v1']['producer'])

    def test_unique_role_keys_paths_and_source_reviewed_api_names(self):
        keys=[(r['workflow'],r['role'],r['variant']) for r in self.rows]
        self.assertEqual(len(keys),len(set(keys)))
        for row in self.rows:
            for path in row['source_mentions']:self.assertTrue((ROOT/path).is_file(),path)
            if row['guide']:self.assertTrue((ROOT/row['guide']).is_file(),row)
            for relation in (row['producer'],row['consumer']):
                if relation is None:continue
                path=ROOT/relation['module'];self.assertTrue(path.is_file())
                if relation['api'].isidentifier():
                    names={n.name for n in ast.walk(ast.parse(path.read_text())) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
                    self.assertIn(relation['api'],names,row)
                self.assertIn(relation['evidence'],('SOURCE_REVIEWED','SYNTHETIC_EXERCISED'))

    def test_ten_actual_handoffs_and_cli_response_templates(self):
        scenarios=list(cases());self.assertEqual(len(scenarios),10)
        for name,module,values,flags,handoff,response in scenarios:
            with self.subTest(name=name),tempfile.TemporaryDirectory(prefix='schema space ') as temp:
                def save(value,label):
                    path=Path(temp)/(label+'.json');path.write_bytes((json.dumps(value,ensure_ascii=True)+'\n').encode());return str(path)
                paths=[save(v,str(i)) for i,v in enumerate(values)]
                converted=[save(v,'flag-'+str(i)) if isinstance(v,dict) else v for i,v in enumerate(flags)]
                prepared=subprocess.run([sys.executable,str(ROOT/(module+'.py')),'prepare',*paths,*converted],cwd=ROOT,capture_output=True)
                self.assertEqual(prepared.returncode,0,prepared.stderr)
                actual=json.loads(prepared.stdout);self.assertEqual(payload_sha256(actual),payload_sha256(handoff))
                hpath=save(actual,'handoff')
                # Preparation-only switches are represented by the bound handoff thereafter.
                response_flags=converted if module in ('model_handoff','argument_proposals','application_proposals') else []
                run=subprocess.run([sys.executable,str(ROOT/(module+'.py')),'response-template',*paths,hpath,*response_flags],cwd=ROOT,capture_output=True)
                self.assertEqual(run.returncode,0,run.stderr)
                self.assertEqual(json.loads(run.stdout),response)
                workflow=name if name in ('reasoning','observations') else name.rsplit('-v',1)[0]
                variant='v1' if workflow in ('reasoning','observations') else 'v'+name.rsplit('-v',1)[1]
                rows=[r for r in self.rows if r['workflow']==workflow and r['variant']==variant]
                hrow=next(r for r in rows if r['role']=='handoff');rrow=next(r for r in rows if r['role']=='response')
                self.assertEqual(hrow['schema_id'],actual.get('schema'));self.assertIsNone(rrow['schema_id'])
                self.assertEqual(set(response),{'handoff_sha256','candidates'})
                self.assertIn('response_contract',actual)

    def test_answer_v3_requires_explicit_explanation_flag(self):
        package=json.loads((ROOT/'examples/review-attribution-package.json').read_bytes())
        scope=json.loads((ROOT/'examples/review-attribution-scope.json').read_bytes())
        args=[package,*[scope[key] for key in ('question','topic','reference_year','operator_id')]]
        with self.assertRaisesRegex(ValueError,'research context requires explicit citation explanation mode'):
            answer.template(*args,research_context=scope['research_context'])
        actual=answer.template(*args,include_citation_explanations=True,research_context=scope['research_context'])
        self.assertEqual(actual['schema'],answer.SCHEMAS[3]['scope'])
        rows=[r for r in self.rows if r['workflow']=='answer' and r['variant']=='v3']
        self.assertEqual(len(rows),6)
        for row in rows:
            self.assertEqual(row['selection_flags'],['--include-citation-explanations','--patterns','--context','--publication-relations','--pattern-id'])

    def test_existing_attribution_producer_consumer_roundtrip(self):
        read=lambda n:json.loads((ROOT/'examples'/('review-attribution-'+n+'.json')).read_bytes())
        package,scope=read('package'),read('scope')
        handoff=answer.prepare_handoff(package,scope)
        bundle=answer.import_response(package,scope,handoff,read('response'),read('provenance'))
        self.assertEqual(handoff['schema'],answer.SCHEMAS[3]['handoff'])
        self.assertEqual(bundle['schema'],answer.SCHEMAS[3]['bundle'])
        self.assertEqual(answer.validate_bundle(package,bundle),bundle)

    def test_maintainer_fixture_and_untagged_separate(self):
        maintainer={r['schema_id'] for r in self.rows if r['category']=='maintainer'}
        self.assertEqual(maintainer,{'persona.test-timing.v1','persona.capacity-observation.v1','persona.capacity-run.v1'})
        self.assertEqual(sum(r['category']=='fixture-only' for r in self.rows),2)
        self.assertEqual(sum(r['role']=='response' and r['schema_id'] is None for r in self.rows),10)

    def test_document_identifier_sets_and_guide(self):
        guide=(ROOT/'docs/SCHEMAS.md').read_text(encoding='utf-8')
        identifiers=set(re.findall(r'`((?:persona\.[a-z0-9-]+|human-validation-record|synthetic-answer-[a-z-]+)\.v[0-9]+)`',guide))
        self.assertEqual(identifiers,{r['schema_id'] for r in self.rows if r['schema_id']})
        blocks=re.findall(r'```sh\n(.*?)```',guide,re.S);self.assertEqual(len(blocks),1)
        for line in blocks[0].splitlines():
            if not line.strip():continue
            args=shlex.split(line);self.assertEqual(args[0],'python');self.assertNotIn('>',args)
            run=subprocess.run([sys.executable,str(ROOT/args[1]),*args[2:]],cwd=ROOT,capture_output=True)
            self.assertEqual(run.returncode,0,run.stderr)

    def test_read_only_no_private_input_output_limit_and_unknown(self):
        with patch('socket.socket',side_effect=AssertionError('network')):
            self.assertTrue(catalog.encode(catalog.catalog()))
        with patch.object(catalog,'MAX_OUTPUT_BYTES',1),self.assertRaises(ValueError):catalog.encode(catalog.catalog())
        run=subprocess.run([sys.executable,str(ROOT/'artifact_schemas.py'),'private.json'],capture_output=True)
        self.assertNotEqual(run.returncode,0);self.assertEqual(run.stdout,b'')
        with self.assertRaises(ValueError):catalog.catalog('unknown')
        self.assertIn(b'not JSON Schema',catalog.encode(catalog.catalog('answer'),'text'))


if __name__=='__main__':unittest.main()
