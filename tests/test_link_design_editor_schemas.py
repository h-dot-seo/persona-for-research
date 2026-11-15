"""Two editor input profiles for an existing linked-writing flow; no product checker."""
import copy
import json
from pathlib import Path
import re
import unittest
from unittest.mock import patch
import reasoning_links as links_api
import design_scenario as design_api
from reasoning_cards import DIMENSIONS
from tests.test_editor_schemas import conforms

ROOT=Path(__file__).resolve().parents[1]

class LinkDesignEditorTests(unittest.TestCase):
    def setUp(self):
        self.link_schema=json.loads((ROOT/'schemas/reasoning-links.editor.schema.json').read_bytes())
        self.design_schema=json.loads((ROOT/'schemas/design-scenario.editor.schema.json').read_bytes())
        guide=(ROOT/'docs/LINK_DESIGN_EDITOR_SCHEMAS.md').read_text(encoding='utf-8')
        blocks=re.findall(r'```python\n(.*?)```',guide,re.S)
        self.assertEqual(len(blocks),2)
        self.scope={}
        # The fixed guide example, not a generic runner or arbitrary private input.
        with patch('socket.socket',side_effect=AssertionError('no network')):
            for block in blocks:exec(compile(block,'synthetic-link-design-editor-example','exec'),self.scope)
        self.package=self.scope['package'];self.links=self.scope['links'];self.design=self.scope['design']

    def checks(self):
        return [(self.link_schema,self.links,lambda v:links_api.review(self.package,v),[(),('links',0),('links',0,'from_ref'),('links',0,'to_ref')]),
                (self.design_schema,self.design,lambda v:design_api.review(self.package,self.links,v),[(),('steps',0),('steps',0,'link_uses',0)])]

    def test_exact_constant_and_inline_contracts_no_defaults_or_invented_bounds(self):
        lp=self.link_schema['properties'];dp=self.design_schema['properties']
        self.assertEqual(set(lp),{'persona_sha256','knowledge_papers_sha256','operator_id','links'})
        li=lp['links']['items'];ref=li['properties']['from_ref'];step=dp['steps']['items'];use=step['properties']['link_uses']['items']
        self.assertEqual(set(li['properties']),links_api.LINK_KEYS)
        self.assertEqual(set(ref['properties']),links_api.REF_KEYS)
        self.assertEqual(li['properties']['relation']['enum'],list(links_api.RELATIONS))
        self.assertEqual(li['properties']['claim_type']['const'],'operator_interpretation')
        self.assertEqual(ref['properties']['dimension']['enum'],[None,*DIMENSIONS])
        self.assertEqual(ref['properties']['observation_index']['minimum'],0)
        self.assertEqual(ref,li['properties']['to_ref'])
        self.assertEqual(set(dp),design_api.PROPOSAL_KEYS);self.assertEqual(set(step['properties']),design_api.STEP_KEYS)
        self.assertEqual(set(use['properties']),{'link_id','role','applicability_note'})
        self.assertEqual(use['properties']['role']['enum'],list(design_api.ROLES))
        for key in design_api.OPTIONAL_FIELDS:self.assertEqual(step['properties'][key]['type'],['string','null'])
        for schema in (self.link_schema,self.design_schema):
            self.assertIn(':editor-profile:',schema['$id']);self.assertTrue(schema['$schema'].endswith('/2020-12/schema'))
            self.assertNotIn('schema',schema['properties']);self.assertNotIn('version',schema['properties']);self.assertNotIn('$schema',schema['properties'])
            def walk(node):
                if isinstance(node,dict):
                    self.assertNotIn('default',node);self.assertNotIn('maxItems',node);self.assertNotIn('uniqueItems',node)
                    if node.get('type')=='object':self.assertEqual(set(node['required']),set(node['properties']));self.assertIs(node['additionalProperties'],False)
                    for child in node.values():walk(child)
                elif isinstance(node,list):
                    for child in node:walk(child)
            walk(schema)
        for key in design_api.BINDINGS:self.assertTrue(dp[key]['readOnly'])
        for key in ('persona_sha256','knowledge_papers_sha256'):self.assertTrue(lp[key]['readOnly'])
        for node in (lp['operator_id'],li['properties']['link_id'],dp['operator_id'],step['properties']['step_id'],use['properties']['link_id']):self.assertEqual(node['maxLength'],128)
        for node in (li['properties']['rationale'],dp['question'],step['properties']['proposed_action'],step['properties']['rationale'],use['properties']['applicability_note']):self.assertEqual(node['maxLength'],2000)
        for key in design_api.OPTIONAL_FIELDS:self.assertEqual(step['properties'][key]['maxLength'],2000)
        self.assertNotIn('maxLength',ref['properties']['paper_id'])

    def test_actual_connected_guide_templates_filled_and_input_immutability(self):
        before=copy.deepcopy((self.package,self.links,self.design))
        for schema,value,check,_ in self.checks():conforms(schema,value);check(value)
        conforms(self.link_schema,self.scope['blank_links']);conforms(self.design_schema,self.scope['blank_design'])
        self.assertEqual(links_api.review(self.package,self.scope['blank_links'])['status'],'NO_SUPPLIED_LINKS')
        self.assertEqual(design_api.review(self.package,self.links,self.scope['blank_design'])['status'],'NO_PROPOSED_STEPS')
        result=design_api.review(self.package,self.links,self.design)
        self.assertEqual(result['link_artifact_sha256'],links_api.payload_sha256(self.links))
        self.assertNotEqual(result['link_artifact_sha256'],links_api.payload_sha256(self.scope['link_report']))
        self.assertIsNone(result['evidence_links']['links'][0]['from_evidence']['component'])
        self.assertEqual(result['steps'][0]['missing_fields'],list(design_api.OPTIONAL_FIELDS))
        self.assertNotEqual(result['operator_id'],result['evidence_links']['operator_id'])
        self.assertEqual(before,(self.package,self.links,self.design))
        for schema,report,check in ((self.link_schema,self.scope['link_report'],lambda v:links_api.review(self.package,v)),
                (self.design_schema,self.scope['design_report'],lambda v:design_api.review(self.package,self.links,v))):
            with self.assertRaises(AssertionError):conforms(schema,report)
            with self.assertRaises(ValueError):check(report)

    def test_every_required_key_and_unknown_key_at_every_object_level(self):
        for schema,value,check,paths in self.checks():
            for path in paths:
                target=value
                for k in path:target=target[k]
                for key in [*target,None]:
                    bad=copy.deepcopy(value);obj=bad
                    for k in path:obj=obj[k]
                    if key is None:obj['unsupported']='synthetic'
                    else:del obj[key]
                    with self.subTest(path=path,key=key):
                        with self.assertRaises(AssertionError):conforms(schema,bad)
                        with self.assertRaises(ValueError):check(bad)

    def test_enum_type_length_mutations_and_no_new_discriminators(self):
        cases=[(0,('operator_id',),'x'*129),(0,('links',0,'link_id'),'x'*129),(0,('links',0,'rationale'),'x'*2001),
            (0,('links',0,'relation'),'author_agrees'),(0,('links',0,'claim_type'),'explicit_statement'),
            (0,('links',0,'from_ref','dimension'),'invented'),(0,('links',0,'from_ref','observation_index'),-1),
            (0,('links',0,'from_ref','observation_index'),True),(0,('links',0,'from_ref','paper_id'),None),
            (1,('operator_id',),'x'*129),(1,('question',),'x'*2001),(1,('steps',0,'step_id'),'x'*129),
            (1,('steps',0,'proposed_action'),'x'*2001),(1,('steps',0,'rationale'),'x'*2001),
            (1,('steps',0,'link_uses',0,'link_id'),'x'*129),(1,('steps',0,'link_uses',0,'role'),'approved'),
            (1,('steps',0,'link_uses',0,'applicability_note'),'x'*2001)]
        cases += [(1,('steps',0,key),'x'*2001) for key in design_api.OPTIONAL_FIELDS]
        for index,path,replacement in cases:
            schema,value,check,_=self.checks()[index];bad=copy.deepcopy(value);obj=bad
            for k in path[:-1]:obj=obj[k]
            obj[path[-1]]=replacement
            with self.subTest(path=path):
                with self.assertRaises(AssertionError):conforms(schema,bad)
                with self.assertRaises(ValueError):check(bad)
        for schema,value,check,_ in self.checks():
            for key in ('$schema','schema','version'):
                bad=dict(value,**{key:'invented'})
                with self.assertRaises(AssertionError):conforms(schema,bad)
                with self.assertRaises(ValueError):check(bad)

    def test_valid_null_empty_and_editing_blanks_are_distinct(self):
        plain=copy.deepcopy(self.design);plain['steps'][0]['link_uses']=[]
        conforms(self.design_schema,plain);r=design_api.review(self.package,self.links,plain)
        self.assertEqual(r['steps'][0]['evidence_status'],'NO_LINKED_EVIDENCE_SUPPLIED')
        for schema,value,check,paths in self.checks():
            targets=[('operator_id',)]
            if schema is self.link_schema:targets += [('links',0,'link_id'),('links',0,'rationale')]
            else:targets += [('question',),('steps',0,'proposed_action'),('steps',0,'rationale'),('steps',0,'falsification_check'),('steps',0,'link_uses',0,'applicability_note')]
            for path in targets:
                for blank in ('',' \t'):
                    bad=copy.deepcopy(value);obj=bad
                    for k in path[:-1]:obj=obj[k]
                    obj[path[-1]]=blank;conforms(schema,bad)
                    with self.assertRaises(ValueError):check(bad)
        floatref=copy.deepcopy(self.links);floatref['links'][0]['from_ref']['observation_index']=0.0
        conforms(self.link_schema,floatref)
        with self.assertRaises(ValueError):links_api.review(self.package,floatref)

    def test_dynamic_endpoint_bindings_and_link_duplicate_rules(self):
        mutations=[lambda x:x.update(persona_sha256='0'*64),
            lambda x:x['links'][0]['from_ref'].update(paper_id='absent'),
            lambda x:x['links'][0]['from_ref'].update(observation_index=999),
            lambda x:x['links'][0]['from_ref'].update(dimension='falsification_check'),
            lambda x:x['links'][0].update(to_ref=copy.deepcopy(x['links'][0]['from_ref'])),
            lambda x:x['links'].append(copy.deepcopy(x['links'][0])),
            lambda x:x['links'].append(dict(copy.deepcopy(x['links'][0]),link_id='different-id'))]
        for mutate in mutations:
            bad=copy.deepcopy(self.links);mutate(bad);conforms(self.link_schema,bad)
            with self.assertRaises(ValueError):links_api.review(self.package,bad)
        contrast=copy.deepcopy(self.links);edge=contrast['links'][0];edge['relation']='contrasts'
        contrast['links'].append(dict(edge,link_id='reverse',from_ref=copy.deepcopy(edge['to_ref']),to_ref=copy.deepcopy(edge['from_ref'])))
        conforms(self.link_schema,contrast)
        with self.assertRaises(ValueError):links_api.review(self.package,contrast)
        distinct=copy.deepcopy(self.links)
        distinct['links'].append(dict(copy.deepcopy(distinct['links'][0]),link_id='same-endpoints-other-relation',relation='challenges'))
        conforms(self.link_schema,distinct);self.assertEqual(len(links_api.review(self.package,distinct)['links']),2)
        # Directed opposite links and distinct relations are not silently merged or inferred.
        for relation in ('qualifies','challenges'):
            good=copy.deepcopy(self.links);edge=good['links'][0]
            good['links'].append(dict(edge,link_id='explicit-second',relation=relation,from_ref=copy.deepcopy(edge['to_ref']),to_ref=copy.deepcopy(edge['from_ref'])))
            conforms(self.link_schema,good);self.assertEqual(len(links_api.review(self.package,good)['links']),2)

    def test_dynamic_design_link_hash_membership_duplicates_and_roles(self):
        mutations=[lambda x:x.update(link_artifact_sha256='0'*64),
            lambda x:x['steps'][0]['link_uses'][0].update(link_id='absent'),
            lambda x:x['steps'].append(copy.deepcopy(x['steps'][0])),
            lambda x:x['steps'][0]['link_uses'].append(copy.deepcopy(x['steps'][0]['link_uses'][0]))]
        for mutate in mutations:
            bad=copy.deepcopy(self.design);mutate(bad);conforms(self.design_schema,bad)
            with self.assertRaises(ValueError):design_api.review(self.package,self.links,bad)
        changed=copy.deepcopy(self.links);changed['links'][0]['rationale']+=' revised';conforms(self.link_schema,changed)
        with self.assertRaises(ValueError):design_api.review(self.package,changed,self.design)
        good=copy.deepcopy(self.design);use=good['steps'][0]['link_uses'][0]
        good['steps'][0]['link_uses'] += [dict(use,role='motivation'),dict(use,role='counterargument')]
        conforms(self.design_schema,good);r=design_api.review(self.package,self.links,good)
        self.assertEqual(r['steps'][0]['distinct_link_count'],1);self.assertEqual(len(r['steps'][0]['link_uses']),3)
        self.assertEqual(r['evidence_links']['links'][0]['relation'],'qualifies')

if __name__=='__main__':unittest.main()
