"""Static correction aids are not quote/binding verification or model attestation."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import schema_catalog as c
import observation_proposals as o
import extraction_adapter as e
from declared_provenance import PROVENANCE_FIELDS, validate_declared_provenance
from persona import payload_sha256
from handoff_packet import extract

ROOT=Path(__file__).resolve().parents[1]

def inputs():
    corpus=json.loads((ROOT/'examples/reasoning-corpus.json').read_text(encoding='utf-8'))
    for paper in corpus['papers']: paper['observations']=[]
    h=o.prepare_observation_handoff(corpus)
    row=dict(paper_id='synthetic-0',method='Compare competing explanations.',condition=None,
        limitation=None,topic=None,locator='synthetic reasoning',evidence_quote='Compare explanations.',
        proposed_claim_type='explicit_statement',proposed_stance='support')
    response=dict(handoff_sha256=payload_sha256(h),candidates=[row])
    provenance=dict(provider_id='synthetic',model_id='synthetic',run_id='synthetic',operator_id='synthetic',execution_location='unknown')
    return corpus,h,response,provenance

class ObservationPreflightTests(unittest.TestCase):
    def setUp(self): self.corpus,self.h,self.response,self.prov=inputs()
    def imports(self,response=None,prov=None):
        return o.import_observation_response(self.corpus,self.h,self.response if response is None else response,self.prov if prov is None else prov)
    def test_real_flow_extract_multiple_errors_correct_import_defer(self):
        bad=copy.deepcopy(self.response); bad['candidates'][0].update(method='',private_unknown='PRIVATE')
        prov=dict(self.prov,model_id='',execution_location='PRIVATE')
        files,_=extract(('```json\n'+json.dumps(bad)+'\n```\n').encode(),json.dumps(self.h).encode())
        extracted=json.loads(dict(files)['response.json'])
        a=c.check('observation-response',extracted); b=c.check('declared-provenance',prov)
        self.assertEqual(len(a['errors']),2);self.assertEqual(len(b['errors']),2)
        for report in (a,b):
            for text in (False,True): self.assertNotIn(b'PRIVATE',c.encode(report,text))
        with self.assertRaises(ValueError):self.imports(extracted,prov)
        self.assertTrue(c.check('observation-response',self.response)['structurally_conforms'])
        self.assertTrue(c.check('declared-provenance',self.prov)['structurally_conforms'])
        bundle=self.imports();review=o.review_template(self.corpus,bundle,'synthetic-reviewer')
        packet=o.review_proposals(self.corpus,bundle,review)
        self.assertEqual(packet['status'],'OBSERVATION_PROPOSAL_REVIEW_INCOMPLETE')
        self.assertFalse(packet['runtime_package_created'])
    def test_all_nested_required_and_unknown_fields(self):
        for name,base,paths in [('observation-response',self.response,[(),('candidates',0)]),('declared-provenance',self.prov,[()])]:
            for path in paths:
                def target(v):
                    for key in path:v=v[key]
                    return v
                for key in list(target(base))+[None]:
                    value=copy.deepcopy(base); t=target(value)
                    if key is None:t['SECRET_UNKNOWN']='SECRET_VALUE'
                    else:del t[key]
                    with self.subTest(name=name,path=path,key=key):
                        report=c.check(name,value);self.assertFalse(report['structurally_conforms'])
                        self.assertNotIn('SECRET',json.dumps(report))
                        with self.assertRaises(ValueError):
                            if name=='observation-response':self.imports(value)
                            else:validate_declared_provenance(value)
    def test_live_constant_contract(self):
        schema=c.load_schema('observation-response');a=schema['properties']['candidates'];p=a['items']['properties']
        self.assertEqual(a['maxItems'],e.MAX_IMPORTED_CANDIDATES)
        self.assertEqual(set(p),o.RESPONSE_FIELDS)
        self.assertEqual(set(c.load_schema('declared-provenance')['properties']),PROVENANCE_FIELDS)
        self.assertEqual({k for k,v in p.items() if v['type']==['string','null']},set(o.NULLABLE))
        for k in ('paper_id','method','condition','limitation','topic','locator','evidence_quote'):
            self.assertEqual(p[k]['maxLength'],e.MAX_QUOTE_CHARS if k=='evidence_quote' else e.MAX_CANDIDATE_CHARS)
        h=self.h['response_contract']
        self.assertEqual(p['proposed_claim_type']['enum'],h['proposed_claim_types']);self.assertEqual(p['proposed_stance']['enum'],h['proposed_stances'])
    def test_length_enum_control_type_mutations(self):
        for field in self.response['candidates'][0]:
            spec=c.load_schema('observation-response')['properties']['candidates']['items']['properties'][field]
            values=['',False,{},'x'*(spec.get('maxLength',2000)+1)]
            if field not in o.NULLABLE:values.append(None)
            for value in values:
                bad=copy.deepcopy(self.response);bad['candidates'][0][field]=value
                with self.subTest(field=field,value_type=type(value).__name__):
                    self.assertFalse(c.check('observation-response',bad)['structurally_conforms'])
                    with self.assertRaises(ValueError):self.imports(bad)
        for field in PROVENANCE_FIELDS:
            for value in ('',' ', 'x'*129,'x\x00','x\x1f','x\x7f',None,False,{}):
                bad=dict(self.prov,**{field:value})
                self.assertFalse(c.check('declared-provenance',bad)['structurally_conforms'])
                with self.assertRaises(ValueError):validate_declared_provenance(bad)
    def test_valid_empty_null_and_boundaries(self):
        empty=dict(self.response,candidates=[])
        self.assertTrue(c.check('observation-response',empty)['structurally_conforms'])
        self.assertEqual(self.imports(empty)['status'],'NO_OBSERVATION_PROPOSALS')
        many=dict(self.response,candidates=self.response['candidates']*128)
        self.assertTrue(c.check('observation-response',many)['structurally_conforms']);self.imports(many)
        many['candidates'].append(many['candidates'][0])
        self.assertEqual(c.check('observation-response',many)['errors'],[dict(path=['candidates'],code='MAX_ITEMS')])
        with self.assertRaises(ValueError):self.imports(many)
        for name in ('observation-response','declared-provenance'):
            self.assertFalse(c.check(name,None)['structurally_conforms'])
    def test_exact_static_limits_and_array_types(self):
        props=c.load_schema('observation-response')['properties']['candidates']['items']['properties']
        for field,spec in props.items():
            if 'maxLength' not in spec: continue
            value=copy.deepcopy(self.response);value['candidates'][0][field]='x'*spec['maxLength']
            self.assertTrue(c.check('observation-response',value)['structurally_conforms'])
            value['candidates'][0][field]+='x'
            self.assertFalse(c.check('observation-response',value)['structurally_conforms'])
        for field in PROVENANCE_FIELDS-{'execution_location'}:
            value=dict(self.prov,**{field:'x'*128})
            self.assertTrue(c.check('declared-provenance',value)['structurally_conforms'])
            validate_declared_provenance(value)
        for rows in (None,{},False,'private',[None],[[]],[False]):
            value=dict(self.response,candidates=rows)
            self.assertFalse(c.check('observation-response',value)['structurally_conforms'])
            with self.assertRaises(ValueError):self.imports(value)
        before=copy.deepcopy(self.response)
        c.check('observation-response',self.response)
        self.assertEqual(before,self.response)
    def test_fixed_schema_wrong_types_and_keywords(self):
        schema=c.load_schema('observation-response')
        for field,value in [('items',None),('maxItems',True),('maxItems',-1),('maxItems',1.0)]:
            bad=copy.deepcopy(schema);bad['properties']['candidates'][field]=value
            with self.assertRaises(c.SchemaError):c.validate_schema(bad)
        for kind in (['null','string'],['string','null','object'],'null','number'):
            bad=copy.deepcopy(schema);bad['properties']['candidates']['items']['properties']['method']['type']=kind
            with self.assertRaises(c.SchemaError):c.validate_schema(bad)
    def test_dynamic_authority_not_replaced(self):
        for field,value in [('paper_id','unknown'),('locator','unknown'),('evidence_quote','not in source')]:
            bad=copy.deepcopy(self.response);bad['candidates'][0][field]=value
            self.assertTrue(c.check('observation-response',bad)['structurally_conforms'])
            with self.assertRaises(ValueError):self.imports(bad)
        bad=dict(self.response,handoff_sha256='f'*64)
        self.assertTrue(c.check('observation-response',bad)['structurally_conforms'])
        with self.assertRaises(ValueError):self.imports(bad)
        corpus=copy.deepcopy(self.corpus);corpus['private_note']='changed'
        with self.assertRaises(ValueError):o.import_observation_response(corpus,self.h,self.response,self.prov)
    def test_closed_subset_and_budgets(self):
        base=c.load_schema('observation-response')
        for key,value in [('$ref','private'),('uniqueItems',True),('pattern','arbitrary'),('items',{}),('maxItems',1)]:
            bad=copy.deepcopy(base);bad[key]=value
            with self.assertRaises(c.SchemaError):c.validate_schema(bad)
        with patch.object(c,'MAX_OUTPUT_BYTES',1),self.assertRaises(ValueError):c.encode(c.check('observation-response',self.response))
    def test_cli_private_strict_json_and_native_bytes(self):
        with tempfile.TemporaryDirectory(prefix='preflight space ') as tmp:
            p=Path(tmp)/'한글.json';p.write_text(json.dumps(self.response),encoding='utf-8')
            result=subprocess.run([sys.executable,str(ROOT/'schema_catalog.py'),'check','observation-response',str(p)],capture_output=True)
            self.assertEqual(result.returncode,0);self.assertEqual(result.stderr,b'')
            self.assertEqual(result.stdout,c.encode(c.check('observation-response',self.response)))
            for raw in ('null','{"candidates":[],"candidates":[]}','{"private":NaN}'):
                p.write_text(raw,encoding='utf-8');result=subprocess.run([sys.executable,str(ROOT/'schema_catalog.py'),'check','observation-response',str(p)],capture_output=True)
                self.assertEqual(result.returncode,1);self.assertNotIn(b'Traceback',result.stderr)
                self.assertNotIn(b'private',result.stdout)
    def test_guide_executes_actual_connected_flow(self):
        guide=(ROOT/'docs/OBSERVATION_PREFLIGHT.md').read_text(encoding='utf-8')
        code=guide.split('```python\n')[1].split('\n```')[0]
        with tempfile.TemporaryDirectory(prefix='guide space ') as tmp:
            scope={'ROOT':ROOT,'OUTPUT':Path(tmp).resolve()}
            exec(compile(code,'documented synthetic flow','exec'),scope)
            self.assertEqual(scope['packet']['status'],'OBSERVATION_PROPOSAL_REVIEW_INCOMPLETE')
