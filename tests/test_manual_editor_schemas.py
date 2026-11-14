"""Editor documentation only; actual manual APIs retain validation authority."""
import copy
import json
from pathlib import Path
import re
import unittest
from unittest.mock import patch
import curate_local as curate
import revise_local as revision
from prepare_local_manifest import prepare
from reasoning_cards import DIMENSIONS
from tests.test_editor_schemas import conforms

ROOT=Path(__file__).resolve().parents[1]

class ManualEditorSchemaTests(unittest.TestCase):
    def setUp(self):
        self.source=ROOT/'examples/synthetic-sources'
        self.manifest=prepare(json.loads((ROOT/'examples/local-selection.json').read_bytes()),self.source)
        self.card=curate.template(self.manifest,'synthetic-0')
        self.card['observation']=json.loads((ROOT/'examples/file-corpus.json').read_bytes())['papers'][0]['observations'][0]
        obs=self.card['observation'];obs['stance']='support'
        obs['reasoning']={dimension:dict(text='Synthetic '+dimension,locator=obs['locator'],evidence_quote=obs['evidence_quote'],claim_type='operator_interpretation') for dimension in DIMENSIONS}
        self.appended=curate.append_observation(self.manifest,self.card,self.source)
        self.rev=revision.template(self.appended,'synthetic-0',0)
        self.rev.update(operator_id='synthetic',revision_reason='Synthetic revision',new_version='new-synthetic',new_build_id='new-synthetic-build')
        self.rev['observation']['method']+=' revised'
        self.schemas=[json.loads((ROOT/'schemas'/f'{n}.editor.schema.json').read_bytes()) for n in ('manual-observation-card','manual-observation-revision-card')]

    def calls(self):
        return [(self.schemas[0],self.card,lambda c:curate.append_observation(self.manifest,c,self.source)),(self.schemas[1],self.rev,lambda c:revision.revise(self.appended,c,self.source))]

    def test_exact_contracts_roles_and_no_invented_limits(self):
        for schema,card,_ in self.calls():
            self.assertEqual(set(schema['required']),set(card));self.assertEqual(set(schema['properties']),set(card))
            self.assertIn(':editor-profile:',schema['$id']);self.assertIn('INPUT CARD',schema['title'])
            self.assertNotIn('"default":',json.dumps(schema))
            self.assertEqual(schema['properties']['schema']['const'],card['schema'])
            obs=schema['properties']['observation'];self.assertEqual(set(obs['required']),curate.REQUIRED|{'stance'})
            self.assertEqual(set(obs['properties']['reasoning']['properties']),set(DIMENSIONS))
            self.assertEqual(obs['properties']['claim_type']['enum'],[None,'explicit_statement','operator_interpretation'])
            self.assertEqual(obs['properties']['stance']['enum'],[None,'support','challenge'])
            for k in curate.REQUIRED-{'claim_type'}:self.assertEqual(obs['properties'][k],{'type':'string'})
            self.assertTrue(schema['properties']['manifest_sha256']['readOnly'])
        for k in ('operator_id','revision_reason','new_version','new_build_id'):
            self.assertEqual(self.schemas[1]['properties'][k]['maxLength'],2000)
        for k in ('previous_observation_sha256','observation_index'):self.assertTrue(self.schemas[1]['properties'][k]['readOnly'])
        _,audit=revision.revise(self.appended,self.rev,self.source)
        self.assertEqual(audit['schema'],self.rev['schema'])
        with self.assertRaises(AssertionError):conforms(self.schemas[1],audit)
        with self.assertRaises(ValueError):revision.revise(self.appended,audit,self.source)

    def test_placeholders_and_real_flow_inputs_unchanged(self):
        for s,c,call in self.calls():
            before=copy.deepcopy((self.manifest,self.appended,c));conforms(s,c);call(c)
            self.assertEqual((self.manifest,self.appended,c),before)
        for s,c,call in [(self.schemas[0],curate.template(self.manifest,'synthetic-0'),self.calls()[0][2]),(self.schemas[1],revision.template(self.appended,'synthetic-0',0),self.calls()[1][2])]:
            conforms(s,c)
            with self.assertRaises(ValueError):call(c)
        for s,c,call in self.calls():
            for mode in ('omit','empty'):
                v=copy.deepcopy(c)
                if mode=='omit':v['observation'].pop('reasoning')
                else:v['observation']['reasoning']={}
                conforms(s,v);call(v)

    def test_every_nested_required_key_and_unknown_both_reject(self):
        def objects(s,v,path=()):
            if s.get('type')=='object':
                yield s,v,path
                for k,child in v.items():
                    if k in s['properties']:yield from objects(s['properties'][k],child,path+(k,))
        for schema,card,call in self.calls():
            for node,value,path in objects(schema,card):
                for key in [*node['required'],'__unknown__']:
                    v=copy.deepcopy(card);target=v
                    for p in path:target=target[p]
                    if key=='__unknown__':target[key]='unexpected'
                    else:target.pop(key)
                    with self.subTest(role=card['schema'],path=path,key=key):
                        with self.assertRaises(AssertionError):conforms(schema,v)
                        with self.assertRaises((ValueError,KeyError,TypeError)):call(v)

    def test_enums_integer_and_actual_revision_limits(self):
        for schema,card,call in self.calls():
            for path,value in [(('observation','stance'),'retain'),(('observation','claim_type'),'inferred'),(('observation','reasoning','uncertainty','claim_type'),'inferred')]:
                v=copy.deepcopy(card);target=v
                for p in path[:-1]:target=target[p]
                target[path[-1]]=value
                with self.assertRaises(AssertionError):conforms(schema,v)
                with self.assertRaises(ValueError):call(v)
        for k in ('operator_id','revision_reason','new_version','new_build_id'):
            v=copy.deepcopy(self.rev);v[k]='x'*2000;conforms(self.schemas[1],v);revision.revise(self.appended,v,self.source)
            v[k]+='x'
            with self.assertRaises(AssertionError):conforms(self.schemas[1],v)
            with self.assertRaises(ValueError):revision.revise(self.appended,v,self.source)
        for index in (-1,True):
            v=copy.deepcopy(self.rev);v['observation_index']=index
            with self.assertRaises(AssertionError):conforms(self.schemas[1],v)
            with self.assertRaises(ValueError):revision.revise(self.appended,v,self.source)
        # JSON Schema integer describes mathematical values, unlike Python's exact int API.
        for index in (0.0,1.0):
            v=copy.deepcopy(self.rev);v['observation_index']=index
            conforms(self.schemas[1],v)
            with self.assertRaises(ValueError):revision.revise(self.appended,v,self.source)
        conforms({'type':'integer','minimum':0},1.0)
        conforms({'type':'integer','minimum':0},1e300)
        conforms({'type':'integer','minimum':0},10**400)
        for value in (float('inf'),float('-inf'),float('nan'),0.5,True,-1.0):
            with self.assertRaises(AssertionError):conforms({'type':'integer','minimum':0},value)
        with self.assertRaises(AssertionError):conforms({'type':'integer','exclusiveMinimum':0},1)

    def test_dynamic_checks_remain_python_only(self):
        for schema,card,call in self.calls():
            for key,value in [('manifest_sha256','0'*64),('paper_id','missing')]:
                v=copy.deepcopy(card);v[key]=value;conforms(schema,v)
                with self.assertRaises(ValueError):call(v)
            for key in ('evidence_quote','locator'):
                v=copy.deepcopy(card);v['observation'][key]='missing synthetic';conforms(schema,v)
                with self.assertRaises(ValueError):call(v)
        for key,value in [('previous_observation_sha256','0'*64),('observation_index',999),('new_version',self.appended['version']),('new_build_id',self.appended['build_id']),('observation',copy.deepcopy(self.appended['papers'][0]['observations'][0]))]:
            v=copy.deepcopy(self.rev);v[key]=value;conforms(self.schemas[1],v)
            with self.assertRaises(ValueError):revision.revise(self.appended,v,self.source)
        altered=copy.deepcopy(self.appended);altered['papers'][0]['source_sha256']='0'*64
        c=revision.template(altered,'synthetic-0',0);c.update({k:self.rev[k] for k in ('operator_id','revision_reason','new_version','new_build_id','observation')});conforms(self.schemas[1],c)
        with self.assertRaises(ValueError):revision.revise(altered,c,self.source)

    def test_old_wrong_quote_can_be_corrected_not_revalidated(self):
        old=copy.deepcopy(self.appended);old['papers'][0]['observations'][0]['evidence_quote']='Old wrong fictional quote'
        c=revision.template(old,'synthetic-0',0);c.update({k:copy.deepcopy(self.rev[k]) for k in ('operator_id','revision_reason','new_version','new_build_id','observation')})
        conforms(self.schemas[1],c);before=copy.deepcopy(old);result,audit=revision.revise(old,c,self.source)
        self.assertEqual(old,before);self.assertEqual(audit['previous_observation']['evidence_quote'],'Old wrong fictional quote')
        self.assertEqual(result['papers'][0]['observations'][0],self.rev['observation'])

    def test_actual_documented_python_flow(self):
        blocks=re.findall(r'```python\n(.*?)```',(ROOT/'docs/MANUAL_EDITOR_SCHEMAS.md').read_text(),re.S)
        self.assertEqual(len(blocks),1)
        with patch('socket.socket',side_effect=AssertionError('no network')):
            scope={};exec(compile(blocks[0],'manual-editor-guide','exec'),scope)
        conforms(self.schemas[0],scope['card']);conforms(self.schemas[1],scope['revision'])

if __name__=='__main__':unittest.main()
