"""Fixed completed-structure subset, not an authority or general schema engine."""
import copy
import json
import io
from contextlib import redirect_stderr
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import schema_catalog as s
import curate_local as c
import revise_local as r
from tests import test_manual_editor_schemas as manual_fixture
from tests.test_editor_schemas import conforms

ROOT=Path(__file__).resolve().parents[1]

class SchemaCatalogTests(unittest.TestCase):
    def setUp(self):
        f=manual_fixture.ManualEditorSchemaTests();f.setUp();self.f=f
        self.rows=[('manual-append',f.card,f.calls()[0][2]),('manual-revision',f.rev,f.calls()[1][2])]
    def test_filled_and_placeholders_and_unchanged(self):
        for name,card,call in self.rows:
            before=copy.deepcopy(card);self.assertTrue(s.check(name,card)['structurally_conforms']);call(card);self.assertEqual(card,before)
        for name,card,editor,call in [('manual-append',c.template(self.f.manifest,'synthetic-0'),self.f.schemas[0],self.rows[0][2]),('manual-revision',r.template(self.f.appended,'synthetic-0',0),self.f.schemas[1],self.rows[1][2])]:
            conforms(editor,card);self.assertFalse(s.check(name,card)['structurally_conforms'])
            with self.assertRaises(ValueError):call(card)
    def test_contract_constants_and_optional_reasoning(self):
        for name,card,call in self.rows:
            schema=s.load_schema(name);self.assertEqual(set(schema['properties']),set(card));self.assertEqual(set(schema['required']),set(card))
            self.assertEqual(schema['properties']['schema']['const'],c.SCHEMA if name=='manual-append' else r.SCHEMA)
            obs=schema['properties']['observation'];self.assertEqual(set(obs['required']),c.REQUIRED|{'stance'})
            self.assertEqual(obs['properties']['stance']['enum'],['support','challenge'])
            self.assertEqual(obs['properties']['claim_type']['enum'],['explicit_statement','operator_interpretation'])
            for k in c.REQUIRED-{'claim_type'}: self.assertNotIn('maxLength',obs['properties'][k])
            for empty in (False,True):
                value=copy.deepcopy(card)
                if empty:value['observation']['reasoning']={}
                else:value['observation'].pop('reasoning')
                self.assertTrue(s.check(name,value)['structurally_conforms']);call(value)
        schema=s.load_schema('manual-revision')
        for k in ('operator_id','revision_reason','new_version','new_build_id'):self.assertEqual(schema['properties'][k]['maxLength'],2000)
    def test_every_nested_key_mutations_and_privacy(self):
        def nodes(schema,value,path=()):
            if schema['type']=='object':
                yield schema,path
                for k,sub in schema['properties'].items():
                    if k in value:yield from nodes(sub,value[k],(*path,k))
        for name,card,call in self.rows:
            for schema,path in nodes(s.load_schema(name),card):
                for key in [*schema['required'],'SECRET_UNKNOWN_PATH']:
                    v=copy.deepcopy(card);target=v
                    for k in path:target=target[k]
                    if key=='SECRET_UNKNOWN_PATH':target[key]='PRIVATE_VALUE'
                    else:target.pop(key)
                    result=s.check(name,v);self.assertFalse(result['structurally_conforms'],(name,path,key))
                    self.assertNotIn('SECRET_UNKNOWN_PATH',s.encode(result).decode());self.assertNotIn('PRIVATE_VALUE',s.encode(result,True).decode())
                    with self.assertRaises((ValueError,KeyError,TypeError)):call(v)
    def test_multifault_determinism_and_wrongtype(self):
        v=copy.deepcopy(self.f.card);v.pop('paper_id');v['observation']['method']='  ';v['observation']['stance']='SECRET';v['SECRET']='path'
        result=s.check('manual-append',v);self.assertEqual(len(result['errors']),4)
        reversed_keys=dict(reversed(list(v.items())));self.assertEqual(s.encode(result),s.encode(s.check('manual-append',reversed_keys)))
        self.assertNotIn('SECRET',s.encode(result).decode())
        self.assertEqual(s.check('manual-append',None)['errors'],[{'path':[],'code':'TYPE'}])
    def test_enum_lengths_nonblank_and_index_boundaries(self):
        for name,card,call in self.rows:
            for key,value in [('stance',None),('claim_type','unsupported'),('method','\t\r\n\u2003')]:
                v=copy.deepcopy(card);v['observation'][key]=value;self.assertFalse(s.check(name,v)['structurally_conforms'])
                with self.assertRaises(ValueError):call(v)
        for key in ('operator_id','revision_reason','new_version','new_build_id'):
            v=copy.deepcopy(self.f.rev);v[key]='x'*2000;self.assertTrue(s.check('manual-revision',v)['structurally_conforms'])
            v[key]+='x';self.assertFalse(s.check('manual-revision',v)['structurally_conforms'])
            with self.assertRaises(ValueError):self.rows[1][2](v)
        for index in (-1,True,float('inf'),float('nan')):
            v=copy.deepcopy(self.f.rev);v['observation_index']=index;self.assertFalse(s.check('manual-revision',v)['structurally_conforms'])
        for index in (0.0,1e300,10**400):
            v=copy.deepcopy(self.f.rev);v['observation_index']=index;self.assertTrue(s.check('manual-revision',v)['structurally_conforms'])
            with self.assertRaises(ValueError):self.rows[1][2](v)
    def test_structural_pass_is_not_authority(self):
        for name,card,call in self.rows:
            v=copy.deepcopy(card);v['manifest_sha256']='0'*64;self.assertTrue(s.check(name,v)['structurally_conforms'])
            with self.assertRaises(ValueError):call(v)
            v=copy.deepcopy(card);v['observation']['evidence_quote']='Synthetic missing quotation';self.assertTrue(s.check(name,v)['structurally_conforms'])
            with self.assertRaises(ValueError):call(v)
        v=copy.deepcopy(self.f.rev);v['observation']=copy.deepcopy(self.f.appended['papers'][0]['observations'][0]);self.assertTrue(s.check('manual-revision',v)['structurally_conforms'])
        with self.assertRaises(ValueError):self.rows[1][2](v)
        _,audit=self.rows[1][2](self.f.rev);self.assertFalse(s.check('manual-revision',audit)['structurally_conforms'])
    def test_schema_failclosed_keywords_regex_and_shapes(self):
        base=s.load_schema('manual-append')
        for key,value in [('$ref','https://example.invalid/private'),('oneOf',[]),('pattern','(a+)+$'),('type','array'),('additionalProperties',True),('required',['unknown']),('enum',[True]),('maxLength',True)]:
            v=copy.deepcopy(base);v[key]=value
            with self.assertRaises(s.SchemaError):s.validate_schema(v)
        v=copy.deepcopy(base);v['properties']['PRIVATE_FIELD']={'type':'string'}
        with self.assertRaises(s.SchemaError):s.validate_schema(v)
    def test_output_budget_no_leak(self):
        result=s.check('manual-append',{'PRIVATE_PATH':'secret'})
        with patch.object(s,'MAX_OUTPUT_BYTES',1):
            with self.assertRaises(ValueError):s.encode(result)
        with patch('builtins.open',side_effect=AssertionError('no body access')):
            self.assertTrue(s.check('manual-append',self.f.card)['structurally_conforms'])
    def cli(self,*args):return subprocess.run([sys.executable,str(ROOT/'schema_catalog.py'),*map(str,args)],capture_output=True)
    def test_cli_and_fixed_errors(self):
        with tempfile.TemporaryDirectory(prefix='schema flow spaces ') as tmp:
            path=Path(tmp)/'private card.json';path.write_bytes(json.dumps(self.f.card).encode())
            for mode in ([],['--text']):
                p=self.cli('check','manual-append',path,*mode);self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(p.stderr,b'')
            for raw in (b'null',b'{"PRIVATE":1}',b'{}'):
                path.write_bytes(raw);p=self.cli('check','manual-append',path);self.assertEqual(p.returncode,1);self.assertEqual(p.stderr,b'');self.assertFalse(json.loads(p.stdout)['structurally_conforms']);self.assertNotIn(b'PRIVATE',p.stdout)
            for raw in (b'{',b'{"x":1,"x":2}',b'NaN',b'x'*(s.MAX_INPUT_BYTES+1)):
                path.write_bytes(raw);p=self.cli('check','manual-append',path);self.assertEqual(p.returncode,1);self.assertEqual(p.stdout,b'');self.assertEqual(p.stderr,('Invalid structural preflight input or output.'+os.linesep).encode())
            self.assertEqual(self.cli('check','unknown',path).returncode,2)
        for command in [('list',),('list','--text'),('show','manual-append'),('show','manual-revision')]:self.assertEqual(self.cli(*command).returncode,0)
    def test_deployed_schema_error_precedes_private_input_and_no_stdout(self):
        with patch.object(s,'load_schema',side_effect=s.SchemaError('PRIVATE_SCHEMA_DETAIL')), patch.object(s,'read_bounded',side_effect=AssertionError('input must not open')), patch.object(sys,'argv',['schema_catalog.py','check','manual-append','PRIVATE_PATH']), redirect_stderr(io.StringIO()) as err:
            with self.assertRaises(SystemExit) as caught:s.main()
        self.assertEqual(caught.exception.code,2)
        self.assertEqual(err.getvalue(),'Invalid fixed catalog schema.\n')
    def test_schema_node_limits_and_nested_unsupported(self):
        v=s.load_schema('manual-append');v['properties']['observation']['properties']['method']['format']='secret-format'
        with self.assertRaises(s.SchemaError):s.validate_schema(v)
        v={'type':'string'}
        for _ in range(18):v={'type':'object','properties':{'observation':v},'required':['observation'],'additionalProperties':False}
        with self.assertRaises(s.SchemaError):s.validate_schema(v)
        for pattern in ([],None,'^.*$'):
            v={'type':'string','pattern':pattern}
            with self.assertRaises(s.SchemaError):s.validate_schema(v)
    def test_hash_format_and_nonobject_subtree_no_guess(self):
        for name,card,_ in self.rows:
            for value in ('0'*63,'A'*64,'0'*64+'\n'):
                v=copy.deepcopy(card);v['manifest_sha256']=value
                self.assertFalse(s.check(name,v)['structurally_conforms'])
            v=copy.deepcopy(card);v['observation']=['PRIVATE_VALUE']
            self.assertEqual(s.check(name,v)['errors'],[{'path':['observation'],'code':'TYPE'}])
    def test_guide(self):
        source=(ROOT/'docs/SCHEMA_CATALOG.md').read_text(encoding='utf-8')
        blocks=re.findall(r'```python\n(.*?)\n```',source,re.S);self.assertEqual(len(blocks),1)
        sh=re.findall(r'```sh\n(.*?)\n```',source,re.S);self.assertEqual(len(sh),1)
        for line in sh[0].splitlines():
            argv=shlex.split(line);argv[0]=sys.executable
            argv=[str(ROOT/token) if token=='schema_catalog.py' or token.startswith('examples/') else token for token in argv]
            proc=subprocess.run(argv,capture_output=True);self.assertEqual(proc.returncode,0,proc.stderr)
        old=Path.cwd()
        try:os.chdir(ROOT);exec(compile(blocks[0],'synthetic-guide','exec'),{})
        finally:os.chdir(old)
