"""Test-only editor documentation drift checks, not a product JSON Schema validator."""
import copy
import json
from pathlib import Path
import re
import unittest
from unittest.mock import patch
import human_validation as hv
import source_recheck as sr
from declared_provenance import PROVENANCE_FIELDS, validate_declared_provenance
from tests import test_source_recheck as source_fixture

ROOT=Path(__file__).resolve().parents[1]
SUPPORTED={'$schema','$id','title','description','type','properties','required','additionalProperties','maxLength','maxItems','enum','const','pattern','anyOf','items','uniqueItems','readOnly'}


def conforms(schema,value):
    """Small assertion walker for these three documents only; no URI resolution."""
    assert not set(schema)-SUPPORTED, 'unsupported test keyword'
    kind=schema.get('type')
    types=kind if isinstance(kind,list) else [kind] if kind else []
    matches={'object':type(value) is dict,'array':type(value) is list,'string':type(value) is str,'null':value is None}
    if types:assert any(matches[t] for t in types),'type'
    if 'const' in schema:assert value==schema['const'],'const'
    if 'enum' in schema:assert value in schema['enum'],'enum'
    if 'anyOf' in schema:
        options=[]
        for sub in schema['anyOf']:
            try:conforms(sub,value);options.append(True)
            except AssertionError:options.append(False)
        assert any(options),'anyOf'
    if type(value) is str:
        if 'maxLength' in schema:assert len(value)<=schema['maxLength'],'maxLength'
        if 'pattern' in schema:assert re.search(schema['pattern'],value) is not None,'pattern'
    if type(value) is dict:
        assert set(schema.get('required',()))<=set(value),'missing'
        props=schema.get('properties',{})
        if schema.get('additionalProperties') is False:assert set(value)<=set(props),'unknown'
        for k,v in value.items():
            if k in props:conforms(props[k],v)
    if type(value) is list:
        if 'maxItems' in schema:assert len(value)<=schema['maxItems'],'maxItems'
        if schema.get('uniqueItems'):assert len({json.dumps(v,sort_keys=True) for v in value})==len(value),'uniqueItems'
        for v in value:conforms(schema['items'],v)


class EditorSchemaTests(unittest.TestCase):
    def setUp(self):
        read=lambda name:json.loads((ROOT/'schemas'/(name+'.editor.schema.json')).read_bytes())
        self.source=read('source-recheck-selection');self.prov=read('declared-provenance');self.human=read('human-validation-record')
        fixture=source_fixture.SourceRecheckTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        self.package,self.selection,self.root=fixture.package,fixture.selection,fixture.root
        self.provenance=json.loads((ROOT/'examples/review-attribution-provenance.json').read_bytes())
        self.hpackage=json.loads((ROOT/'examples/trajectory-conditions-package.json').read_bytes())
        self.record=json.loads((ROOT/'examples/manual-human-validation.json').read_bytes())

    def test_exact_constants_and_inline_contracts(self):
        self.assertEqual(set(self.source['required']),{'schema','package_sha256','operator_id','sources'})
        self.assertEqual(self.source['properties']['schema']['const'],sr.SCHEMA)
        self.assertEqual(self.source['properties']['operator_id']['maxLength'],128)
        self.assertEqual(set(self.source['properties']['sources']['items']['required']),{'paper_id','source_file'})
        self.assertEqual(self.source['properties']['sources']['items']['properties']['source_file']['maxLength'],1024)
        self.assertEqual(set(self.prov['required']),PROVENANCE_FIELDS)
        self.assertEqual(self.prov['properties']['execution_location']['enum'],['','local','remote','unknown'])
        self.assertEqual(set(self.human['required']),set(hv.RECORD_FIELDS))
        props=self.human['properties'];self.assertEqual(set(props),set(hv.RECORD_FIELDS))
        self.assertEqual(set(props['raters']['items']['required']),set(hv.RATER_FIELDS))
        self.assertEqual(set(props['items']['items']['required']),set(hv.ITEM_FIELDS))
        self.assertEqual(props['items']['items']['properties']['judgement']['enum'],list(hv.JUDGEMENTS))
        self.assertEqual(props['status']['enum'],[None,hv.COMPLETED])
        self.assertEqual(props['raters']['maxItems'],hv.MAX_RATERS);self.assertEqual(props['items']['maxItems'],hv.MAX_ITEMS)
        for key in ('method','limitations','independence_declaration'):self.assertEqual(props[key]['maxLength'],hv.MAX_TEXT_CHARS)
        for key in hv.BINDING_KEYS:self.assertTrue(props[key]['readOnly'])
        def closed_objects(node):
            if isinstance(node,dict):
                if node.get('type')=='object':
                    self.assertEqual(set(node['properties']),set(node['required']))
                    self.assertIs(node['additionalProperties'],False)
                for child in node.values():closed_objects(child)
            elif isinstance(node,list):
                for child in node:closed_objects(child)
        for s in (self.source,self.prov,self.human):
            closed_objects(s)
            self.assertIn(':editor-profile:',s['$id']);self.assertTrue(s['$schema'].endswith('/2020-12/schema'))
            self.assertNotIn('\"default\":',json.dumps(s))

    def test_templates_placeholders_are_editor_only(self):
        blank=sr.template(self.package,'synthetic');conforms(self.source,blank)
        with patch.object(sr,'read_source_bytes',side_effect=AssertionError('no read')):
            with self.assertRaises(ValueError):sr.audit(self.package,blank,self.root)
        blank=hv.template(self.hpackage);conforms(self.human,blank)
        with self.assertRaises(ValueError):hv.check(blank,self.hpackage)
        blank=dict.fromkeys(PROVENANCE_FIELDS,'');conforms(self.prov,blank)
        with self.assertRaises(ValueError):validate_declared_provenance(blank)

    def test_filled_examples_and_input_immutability(self):
        before=copy.deepcopy((self.selection,self.provenance,self.record))
        conforms(self.source,self.selection);sr.audit(self.package,self.selection,self.root)
        conforms(self.prov,self.provenance);validate_declared_provenance(self.provenance)
        conforms(self.human,self.record);self.assertEqual(hv.check(self.record,self.hpackage)['binding_status'],'CURRENT_PACKAGE')
        self.assertEqual(before,(self.selection,self.provenance,self.record))

    def test_nested_missing_and_unknown_rejected_by_both(self):
        cases=[(self.source,self.selection,lambda v:sr.audit(self.package,v,self.root),[(),('sources',0)]),
               (self.prov,self.provenance,validate_declared_provenance,[()]),
               (self.human,self.record,lambda v:hv.check(v,self.hpackage),[(),('raters',0),('items',0)])]
        for schema,value,check,paths in cases:
            for path in paths:
                original=value
                for key in path:original=original[key]
                for removed in [*original, None]:
                    with self.subTest(path=path,removed=removed):
                        bad=copy.deepcopy(value);target=bad
                        for key in path:target=target[key]
                        if removed is None:target['unexpected']=True
                        else:target.pop(removed)
                        with self.assertRaises(AssertionError):conforms(schema,bad)
                        with self.assertRaises(ValueError):check(bad)

    def test_enum_length_and_type_mutations_rejected_by_both(self):
        cases=[(self.source,self.selection,lambda v:sr.audit(self.package,v,self.root),('operator_id',),'x'*129),
               (self.source,self.selection,lambda v:sr.audit(self.package,v,self.root),('sources',0,'source_file'),'x'*1025),
               (self.prov,self.provenance,validate_declared_provenance,('execution_location',),'invented'),
               (self.prov,self.provenance,validate_declared_provenance,('model_id',),'x'*129),
               (self.prov,self.provenance,validate_declared_provenance,('model_id',),'x\n'),
               (self.human,self.record,lambda v:hv.check(v,self.hpackage),('raters',0,'rater_id'),'x\n'),
               (self.human,self.record,lambda v:hv.check(v,self.hpackage),('items',0,'judgement'),'APPROVED'),
               (self.human,self.record,lambda v:hv.check(v,self.hpackage),('raters',0,'role'),'x'*129),
               (self.human,self.record,lambda v:hv.check(v,self.hpackage),('items',0,'rationale'),'x'*2001)]
        for schema,value,check,path,replacement in cases:
            bad=copy.deepcopy(value);target=bad
            for key in path[:-1]:target=target[key]
            target[path[-1]]=replacement
            with self.assertRaises(AssertionError):conforms(schema,bad)
            with self.assertRaises(ValueError):check(bad)

    def test_dynamic_checks_are_not_claimed_by_editor(self):
        bad=copy.deepcopy(self.selection);bad['package_sha256']='0'*64;conforms(self.source,bad)
        with self.assertRaises(ValueError):sr.audit(self.package,bad,self.root)
        bad=copy.deepcopy(self.record);bad['assessed_at']='2026-02-31';conforms(self.human,bad)
        with self.assertRaises(ValueError):hv.check(bad,self.hpackage)
        stale=copy.deepcopy(self.record);stale['build_id']='older-synthetic-build';stale['items'][0]['item_id']='old-rule';conforms(self.human,stale)
        result=hv.check(stale,self.hpackage);self.assertEqual(result['binding_status'],'STALE_PACKAGE')
        self.assertFalse(result['items_resolved_against_current_package']);self.assertIn('old-rule',result['unresolved_item_ids'])

    def test_three_documented_api_examples(self):
        guide=(ROOT/'docs/EDITOR_SCHEMAS.md').read_text(encoding='utf-8')
        blocks=re.findall(r'```python\n(.*?)```',guide,re.S);self.assertEqual(len(blocks),3)
        scope={}
        with patch('socket.socket',side_effect=AssertionError('no network')):
            for block in blocks:exec(compile(block,'documented-synthetic-editor-example','exec'),scope)
        conforms(self.source,scope['selection']);conforms(self.prov,scope['provenance'])
        conforms(self.human,scope['blank_record']);conforms(self.human,scope['filled_record'])
        self.assertEqual(scope['human_report']['binding_status'],'CURRENT_PACKAGE')

    def test_test_walker_rejects_unsupported_keywords(self):
        with self.assertRaises(AssertionError):conforms({'type':'string','unknownKeyword':1},'x')


if __name__=='__main__':unittest.main()
