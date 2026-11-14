"""One-call plain-JSON template construction reuse retains fresh public validation."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
import answer_draft as ad
import research_journey as journey
import research_workflow as rw
from tests import capacity, scale_fixture

ROOT=Path(__file__).resolve().parents[1]


class AnswerTemplateReuseTests(unittest.TestCase):
    def setUp(self):
        self.args=scale_fixture.build(1,1,2,1)
        self.package,self.draft=self.args[0],self.args[5]

    def original(self,p=None,d=None):
        with patch.object(ad,'_plain_template_inputs',return_value=False):
            return ad.inspect(self.package if p is None else p,self.draft if d is None else d)

    def test_complete_results_and_text_identical_to_original_path(self):
        original=self.original();result=ad.inspect(self.package,self.draft)
        self.assertEqual(original,result);self.assertEqual(ad.render(original),ad.render(result))
        with patch.object(ad,'_plain_template_inputs',return_value=False):
            report=journey.encode_result(journey.inspect(*self.args));text=journey.render(*self.args)
        self.assertEqual(report,journey.encode_result(journey.inspect(*self.args)))
        self.assertEqual(text,journey.render(*self.args))

    def test_public_calls_remain_fresh_and_repeat_does_not_cache(self):
        with capacity.counter() as counts:
            ad.inspect(self.package,self.draft);self.assertEqual(counts['build'],1)
            ad.inspect(self.package,self.draft);self.assertEqual(counts['build'],2)
            ad.template(self.package,'Question','operator');self.assertEqual(counts['build'],3)
        self.package['persona']['rules'][0]['method']='changed'
        with self.assertRaises(ValueError):ad.inspect(self.package,self.draft)

    def test_custom_inputs_and_budget_use_unchanged_fallback(self):
        class Custom(dict):pass
        draft=Custom(self.draft)
        with patch.object(ad,'_template_checked',wraps=ad._template_checked) as helper,capacity.counter() as counts:
            ad.inspect(self.package,draft)
            self.assertEqual(counts['build'],2);self.assertEqual(helper.call_count,1)
        for key in ('_TEMPLATE_MAX_NODES','_TEMPLATE_MAX_TEXT'):
            with patch.object(ad,key,0),capacity.counter() as counts:
                self.assertEqual(ad.inspect(self.package,self.draft),self.original())
                self.assertEqual(counts['build'],4)

    def test_guard_rejects_eligibility_not_inputs(self):
        class Text(str):pass
        alias={};cycle=[];cycle.append(cycle)
        for value in (Text('x'),{1:'x'},[alias,alias],cycle,float('nan'),float('inf'),'\ud800',('tuple',)):
            self.assertFalse(ad._plain_template_inputs(value))
        deep=[];node=deep
        for _ in range(65):child=[];node.append(child);node=child
        self.assertFalse(ad._plain_template_inputs(deep))
        self.assertTrue(ad._plain_template_inputs({'a':[None,True,1,1.0,'text']}))

    def test_initial_custom_leaf_normalizes_during_validation_still_falls_back(self):
        knowledge=self.package['knowledge'];seen=[]
        class Normalizing(str):
            def __ne__(value,other):
                seen.append('normalized')
                knowledge['author_id']=str(value)
                return str.__ne__(value,other)
        knowledge['author_id']=Normalizing(knowledge['author_id'])
        self.assertFalse(ad._plain_template_inputs(self.package,self.draft))
        self.assertEqual(seen,[])  # eligibility never calls custom comparison methods
        with capacity.counter() as counts:
            result=ad.inspect(self.package,self.draft)
        self.assertTrue(seen);self.assertIs(type(knowledge['author_id']),str)
        self.assertEqual(counts['build'],2)
        self.assertEqual(result,self.original())

    def test_guard_never_invokes_custom_metaclass_or_container_methods(self):
        class Meta(type):
            def __eq__(cls,other):raise AssertionError('custom metaclass comparison')
        class Custom(metaclass=Meta):pass
        class Mapping(dict):
            def __iter__(self):raise AssertionError('custom iteration')
            def values(self):raise AssertionError('custom values')
        self.assertFalse(ad._plain_template_inputs(Custom()))
        self.assertFalse(ad._plain_template_inputs(Mapping()))

    def test_replaced_sources_preserves_second_validation_and_mutation_rejection(self):
        original=ad._sources;calls=[]
        def changed(value):
            calls.append(1);checked,papers=original(value)
            if len(calls)==1:checked['persona']['rules'][0]['method']='tampered'
            return checked,papers
        with patch.object(ad,'_sources',side_effect=changed),self.assertRaises(ValueError):
            ad.inspect(self.package,self.draft)
        self.assertEqual(len(calls),2)  # second original validation rejects the mutation
        with patch.object(ad,'_sources',side_effect=ValueError('first validation')),self.assertRaisesRegex(ValueError,'first validation'):
            ad.inspect({},None)

    def test_replaced_template_keeps_original_call_contract(self):
        with patch.object(ad,'template',side_effect=ValueError('template hook')) as public:
            with self.assertRaisesRegex(ValueError,'template hook'):ad.inspect(self.package,self.draft)
            self.assertEqual(public.call_count,1)

    def test_reviewed_envelope_dispatch_is_unchanged(self):
        import answer_proposals
        for version in (1,2,3):
            envelope={'schema':f'persona.reviewed-answer-proposals.v{version}'}
            marker=object()
            with patch.object(answer_proposals,'inspect_reviewed',return_value=marker) as reviewed, \
                 patch.object(ad,'_sources',side_effect=AssertionError('plain path entered')):
                self.assertIs(ad.inspect(self.package,envelope),marker)
                reviewed.assert_called_once_with(self.package,envelope)

    def test_error_order_and_messages_match_original(self):
        variants=[]
        for change in (lambda d:d.update(question=''),lambda d:d.update(persona_sha256='0'*64),lambda d:d.update(claims='wrong'),lambda d:d.update(extra=1)):
            value=copy.deepcopy(self.draft);change(value);variants.append(value)
        variants.extend([None,[]])
        for draft in variants:
            with self.subTest(draft=draft):
                messages=[]
                for enabled in (False,True):
                    with patch.object(ad,'_plain_template_inputs',return_value=enabled):
                        try:ad.inspect(self.package,draft)
                        except Exception as exc:messages.append((type(exc),str(exc)))
                self.assertEqual(len(messages),2);self.assertEqual(*messages)

    def test_representative_render_build_count_reduction(self):
        args=scale_fixture.build(8,4,4,2)
        with patch.object(ad,'_plain_template_inputs',return_value=False),capacity.counter() as before:
            old=journey.render(*args)
        with capacity.counter() as after:new=journey.render(*args)
        self.assertEqual(old,new);self.assertEqual(before['build'],79);self.assertEqual(after['build'],56)

    def test_two_seeds_baseline_equivalence(self):
        code='''import json
from unittest.mock import patch
import answer_draft as a, research_journey as j
from tests.scale_fixture import build
from tests.capacity import canonical
x=build(1,1,2,1)
with patch.object(a,'_plain_template_inputs',return_value=False):
 old=j.encode_result(j.inspect(*x)); text=j.render(*x)
assert old==j.encode_result(j.inspect(*x)) and text==j.render(*x)
print(canonical(j.inspect(*x)).hex())
'''
        outputs=[]
        for seed in ('1','73'):
            p=subprocess.run([sys.executable,'-c',code],cwd=ROOT,env=dict(os.environ,PYTHONHASHSEED=seed),capture_output=True)
            self.assertEqual(p.returncode,0,p.stderr);outputs.append(p.stdout)
        self.assertEqual(*outputs)


if __name__=='__main__':unittest.main()
