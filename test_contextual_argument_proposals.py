"""Opt-in replay of recorded answer context; never current argument instructions."""
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import answer_draft as ad
import answer_proposals as ap
import argument_map as am
import argument_proposals as gp
from persona import payload_sha256

ROOT = Path(__file__).resolve().parent


def frozen():
    return json.loads((ROOT/'examples/legacy-contextual-answer-v059.json').read_text(encoding='utf-8'))


def answer(f, scope=None, response=None):
    p = f['package']; scope = scope or f['scope']
    h = ap.prepare_handoff(p, scope)
    r = copy.deepcopy(response or f['response']); r['handoff_sha256'] = payload_sha256(h)
    b = ap.import_response(p, scope, h, r, f['provenance'])
    adoption = ap.review_template(p, b, 'synthetic-reviewer')
    for i, decision in enumerate(adoption['decisions']):
        decision.update(decision='accept', review_note='Synthetic explicit adoption only.',
            reviewed_claim=dict(copy.deepcopy(r['candidates'][i]), claim_id='answer-claim' if i == 0 else 'claim-'+str(i)))
    if len(adoption['decisions']) > 3:
        adoption['decisions'][-1] = dict(candidate_id=adoption['decisions'][-1]['candidate_id'],
            decision='reject', review_note='Rejected answer alternative remains historical.')
    return ap.export_reviewed(p, b, adoption)


class FrozenDefaultArgumentTests(unittest.TestCase):
    def test_v1_over_v3_matches_pre_edit_baseline_exactly(self):
        f = frozen(); p = f['package']; d = answer(f)
        r = ad.review_template(p, d, 'synthetic-final-reviewer')
        s = gp.template(p, d, 'synthetic-argument-operator', r)
        s['selected_claim_ids'] = ['answer-claim']
        h = gp.prepare_handoff(p, d, s, r); response = gp.response_template(p, d, s, h, r)
        b = gp.import_response(p, d, s, h, response, f['provenance'], r)
        adoption = gp.review_template(p, d, b, 'synthetic-argument-reviewer', r)
        packet = gp.review_proposals(p, d, b, adoption, r)
        form = am.template(p, d, 'synthetic-map-operator', r)
        actual = dict(scope=s, handoff=h, response=response, bundle=b, adoption=adoption,
            packet=packet, empty_map=form, map_inspection=am.inspect(p, d, form, r))
        # Captured at d78283cf99c841c6b9cb0d5d9a5f16e937a44cf8 before v0.63 edits.
        expected = {
            'scope':'c004a6e9889722f7b36de7fb085691eaf8f43bb7a05ecb4aa711bc65e6615a69',
            'handoff':'08e2914cecba0e3e267a95d6584a2cd5676ca4f5c2645f6d38b385e0d34b8c1c',
            'response':'acd25ff9552efafdb992d999d945613e41d92f20940ff3481963e56ac2f99b40',
            'bundle':'da72c74731261d86ad9e346a5d91145da55ae70e635ccd0819350f2fb7cf376e',
            'adoption':'911a4ee7d66541c4fa5a113391624dc981b51feee62ac89066cb71d277474fb0',
            'packet':'407e9c7b0d1f78ead1d36133f2347a210c73e6a1279be86e95b574f16f848249',
            'empty_map':'06896a99684ee21e933c4570d7e5196bef84efb8a5355ef3d874b623ba147c82',
            'map_inspection':'368072692741ada0213ab12cdfe863355ee77bb71e04eabbab217b5913b373c6'}
        self.assertEqual({k:payload_sha256(v) for k,v in actual.items()}, expected)
        self.assertEqual(hashlib.sha256(gp.render_review(packet).encode()).hexdigest(),
            '100a79a582bc85e39984a574b4c00c7184d1aea142dfdb35d2117df03d1b88ab')
        self.assertEqual(hashlib.sha256(am.render(p,d,form,r).encode()).hexdigest(),
            '7f4503e46df14c784fdf6328b7a2fce5a04cf4e1be22f616f22e2d126d6c9e03')
        self.assertEqual(gp.SCOPE_SCHEMA, 'persona.argument-proposal-scope.v1')
        self.assertEqual(gp.ENVELOPE_SCHEMA, 'persona.reviewed-argument-proposals.v1')
        self.assertNotIn('include_recorded_answer_context', s)
        self.assertNotIn('recorded_answer_context', h)
        self.assertNotIn('recorded_answer_context', packet)


class ContextualArgumentTests(unittest.TestCase):
    def setUp(self):
        self.f = frozen(); self.p = self.f['package']
        self.answer_scope = copy.deepcopy(self.f['scope'])
        self.outside = dict(paper_id='synthetic-1', observation_index=0, dimension=None)
        self.answer_scope['evidence_refs'].append(self.outside)
        unused = copy.deepcopy(self.answer_scope['research_context']['patterns']['hypotheses'][0])
        unused.update(pattern_id='unselected-pattern', scope_note='Unselected context history remains visible.')
        self.answer_scope['research_context']['patterns']['hypotheses'].append(unused)
        self.answer_response = copy.deepcopy(self.f['response'])
        self.answer_response['candidates'].extend([
            dict(text='Tentative conclusion.', claim_type='operator_synthesis', uncertainty=None, citations=[]),
            dict(text='Unselected answer claim.', claim_type='operator_synthesis', uncertainty=None,
                citations=[dict(reference=self.outside, role='context', explanation=None)]),
            dict(text='Rejected historical answer alternative.', claim_type='operator_synthesis', uncertainty=None, citations=[])])
        self.d = answer(self.f, self.answer_scope, self.answer_response)
        self.final_review = ad.review_template(self.p, self.d, 'synthetic-final-reviewer')
        self.reset()

    def reset(self):
        self.s = gp.template(self.p, self.d, 'synthetic-argument-operator', self.final_review,
            include_recorded_answer_context=True)
        self.s['selected_claim_ids'] = ['answer-claim', 'claim-1']
        self.h = gp.prepare_handoff(self.p, self.d, self.s, self.final_review)
        self.r = gp.response_template(self.p, self.d, self.s, self.h, self.final_review)
        candidate = dict(premise_claim_ids=['answer-claim'], conclusion_claim_id='claim-1',
            bridge_rationale='Original imported bridge.', assumptions=[], defeater=None)
        self.r['candidates'] = [candidate, dict(copy.deepcopy(candidate), bridge_rationale='Rejected bridge alternative.')]
        self.b = gp.import_response(self.p, self.d, self.s, self.h, self.r, self.f['provenance'], self.final_review)
        self.review = gp.review_template(self.p, self.d, self.b, 'synthetic-argument-reviewer', self.final_review)

    def adopt(self):
        self.review['decisions'][0].update(decision='accept', review_note='Explicitly rewritten; not approved.',
            reviewed_step=dict(copy.deepcopy(self.r['candidates'][0]), step_id='bridge', bridge_rationale='Rewritten adopted bridge.'))
        self.review['decisions'][1].update(decision='reject', review_note='Rejected alternative retained.')

    def packet(self):
        return gp.review_proposals(self.p, self.d, self.b, self.review, self.final_review)

    def envelope(self):
        return gp.export_reviewed(self.p, self.d, self.b, self.review, self.final_review)

    def test_opt_in_versions_contract_full_context_and_deferred_review(self):
        self.assertEqual(self.s['schema'], gp.SCHEMAS[2]['scope'])
        self.assertIs(self.s['include_recorded_answer_context'], True)
        self.assertEqual(self.h['schema'], gp.SCHEMAS[2]['handoff'])
        self.assertEqual(self.b['schema'], gp.SCHEMAS[2]['bundle'])
        self.assertEqual(self.packet()['schema'], gp.SCHEMAS[2]['packet'])
        default = gp.template(self.p, self.d, 'synthetic-argument-operator', self.final_review)
        default['selected_claim_ids'] = self.s['selected_claim_ids']
        old = gp.prepare_handoff(self.p, self.d, default, self.final_review)
        self.assertEqual(old['response_contract'], self.h['response_contract'])
        self.assertEqual(old['selected_claims'], self.h['selected_claims'])
        self.assertEqual(self.h['response_contract']['candidate_fields'], sorted(gp.PROPOSAL_FIELDS))
        self.assertTrue(all(x['decision']=='defer' for x in self.review['decisions']))
        self.assertTrue(all(x['decision']=='defer' for x in self.final_review['decisions']))
        with self.assertRaises(ValueError): self.envelope()
        ctx = self.h['recorded_answer_context']
        original = ad.inspect(self.p, self.d)['proposal_review']
        self.assertEqual(ctx['reasoning_context'], original['research_context_review'])
        self.assertEqual(ctx['answer_scope_sha256'], payload_sha256(self.answer_scope))
        self.assertEqual(self.packet()['recorded_answer_context'], ctx)
        self.assertEqual(ctx['reasoning_context']['evidence_refs'], self.answer_scope['evidence_refs'])
        self.assertIn(self.outside, ctx['reasoning_context']['evidence_refs'])
        self.assertEqual(ctx['reasoning_context']['context_review']['decision_counts']['exclude'], 1)
        self.assertEqual(len(ctx['reasoning_context']['pattern_review']['hypotheses']), 2)
        self.assertEqual(json.dumps(self.h).count('"recorded_answer_context"'), 1)
        self.assertEqual(json.dumps(self.packet()).count('"recorded_answer_context"'), 1)

    def test_round_trip_rewritten_rejected_history_and_no_citation_transfer(self):
        self.adopt(); e = self.envelope(); result = am.inspect(self.p, self.d, e, self.final_review)
        self.assertEqual(e['schema'], gp.SCHEMAS[2]['envelope'])
        self.assertEqual(result['steps'][0]['bridge_rationale'], 'Rewritten adopted bridge.')
        self.assertEqual(result['steps'][0]['proposal_origin']['original_proposal']['bridge_rationale'], 'Original imported bridge.')
        self.assertEqual(result['proposal_review']['candidates'][1]['decision'], 'reject')
        self.assertEqual(result['answer']['proposal_review']['candidates'][-1]['decision'], 'reject')
        self.assertEqual(result['steps'][0]['conclusion']['direct_citation_count'], 0)
        self.assertEqual(result['steps'][0]['citation_transfer'], 'NOT_PERFORMED')
        self.assertEqual(result['steps'][0]['conclusion']['declared_review_decision'], 'defer')
        self.assertEqual(result['logical_validation'], 'NOT_PERFORMED')
        text = gp.render_review(self.packet())
        self.assertEqual(text.count('Recorded answer-preparation/import context ('), 1)
        for phrase in ('not newly supplied or current argument context', 'historical',
                       'Rewritten adopted bridge.', 'Rejected bridge alternative.', 'Unselected context history remains visible.'):
            self.assertIn(phrase, text)
        self.assertIn('Recorded answer-preparation/import context (', am.render(self.p,self.d,e,self.final_review))

    def test_opt_in_rejects_other_answer_types_and_nonboolean_flags(self):
        for value in (None, 0, 1, 'true', [], {}):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'boolean'):
                gp.template(self.p, self.d, 'op', include_recorded_answer_context=value)
        manual = ad.template(self.p, 'Question', 'operator')
        for draft in (manual, ad.inspect(self.p,self.d)):
            with self.assertRaises(ValueError):gp.template(self.p,draft,'op',include_recorded_answer_context=True)
        for version in (1,2):
            scope=ap.template(self.p,'Question','model design',2020,'op',include_citation_explanations=version==2)
            scope['evidence_refs']=[copy.deepcopy(self.answer_scope['evidence_refs'][0])]
            response=copy.deepcopy(self.f['response'])
            if version==1:
                for c in response['candidates'][0]['citations']:del c['explanation']
            d=answer(self.f,scope,response)
            with self.assertRaisesRegex(ValueError,'reviewed v3'):gp.template(self.p,d,'op',include_recorded_answer_context=True)

    def test_scope_true_only_and_version_mixing_or_downgrade_rejected(self):
        for value in (False, 1, 'true', None):
            s=dict(self.s,include_recorded_answer_context=value)
            with self.assertRaises(ValueError):gp.prepare_handoff(self.p,self.d,s,self.final_review)
        for edit in ('remove_flag','scope','handoff','bundle','envelope'):
            self.adopt(); e=self.envelope(); s=copy.deepcopy(self.s);h=copy.deepcopy(self.h)
            if edit=='remove_flag':
                del s['include_recorded_answer_context']
                call=lambda:gp.prepare_handoff(self.p,self.d,s,self.final_review)
            elif edit=='scope':
                s['schema']=gp.SCOPE_SCHEMA
                call=lambda:gp.prepare_handoff(self.p,self.d,s,self.final_review)
            elif edit=='handoff':
                h['schema']=gp.SCHEMAS[1]['handoff']
                call=lambda:gp.response_template(self.p,self.d,s,h,self.final_review)
            else:
                target=e if edit=='envelope' else e['bundle'];target['schema']=target['schema'].replace('.v2','.v1')
                call=lambda:gp.inspect_reviewed(self.p,self.d,e,self.final_review)
            with self.subTest(edit=edit), self.assertRaises(ValueError):call()
        b=copy.deepcopy(self.b);b['scope']['schema']=gp.SCOPE_SCHEMA;del b['scope']['include_recorded_answer_context']
        with self.assertRaises(ValueError):gp.validate_bundle(self.p,self.d,b,self.final_review)

    def test_unselected_claim_context_refs_and_extra_citations_are_not_endpoints(self):
        for key in ('claim-2', 'synthetic-1', payload_sha256(self.outside), 'unselected-pattern'):
            for field in ('premise_claim_ids','conclusion_claim_id'):
                r=copy.deepcopy(self.r);r['candidates'][0][field]=[key] if field=='premise_claim_ids' else key
                with self.assertRaisesRegex(ValueError,'explicit selected'):
                    gp.import_response(self.p,self.d,self.s,self.h,r,self.f['provenance'],self.final_review)
        for field in ('citations','source_quote','text','new_claims'):
            r=copy.deepcopy(self.r);r['candidates'][0][field]=[]
            with self.assertRaises(ValueError):gp.import_response(self.p,self.d,self.s,self.h,r,self.f['provenance'],self.final_review)
        self.adopt();self.review['decisions'][0]['reviewed_step']['conclusion_claim_id']='claim-2'
        with self.assertRaisesRegex(ValueError,'explicit selected'):self.packet()

    def test_source_quote_cannot_be_original_or_reviewed_conclusion(self):
        from reasoning_links import _sources, _endpoint
        _, papers = _sources(self.p)
        claim = self.answer_response['candidates'][0]
        claim['claim_type'] = 'source_quote'
        claim['text'] = _endpoint(claim['citations'][0]['reference'], papers)['observation']['evidence_quote']
        self.d = answer(self.f, self.answer_scope, self.answer_response)
        self.final_review = ad.review_template(self.p, self.d, 'synthetic-final-reviewer'); self.reset()
        r = copy.deepcopy(self.r)
        r['candidates'][0].update(premise_claim_ids=['claim-1'], conclusion_claim_id='answer-claim')
        with self.assertRaisesRegex(ValueError, 'operator_synthesis'):
            gp.import_response(self.p,self.d,self.s,self.h,r,self.f['provenance'],self.final_review)
        self.adopt()
        self.review['decisions'][0]['reviewed_step'].update(premise_claim_ids=['claim-1'], conclusion_claim_id='answer-claim')
        with self.assertRaisesRegex(ValueError, 'operator_synthesis'): self.packet()

    def test_stale_full_answer_context_and_rejected_answer_history_rejected(self):
        for mutate in (
            lambda d:d['bundle']['scope']['research_context']['context'].update(target_context='Changed target'),
            lambda d:d['bundle']['scope']['research_context']['patterns']['hypotheses'][1].update(scope_note='Changed unselected history'),
            lambda d:d['review']['decisions'][-1].update(review_note='Changed rejected answer history')):
            d=copy.deepcopy(self.d);mutate(d)
            with self.assertRaises(ValueError):gp.prepare_handoff(self.p,d,self.s,self.final_review)
        scope=copy.deepcopy(self.answer_scope)
        scope['research_context']['patterns']['hypotheses'][1]['scope_note']='Valid changed unselected history.'
        changed=answer(self.f,scope,self.answer_response)
        review=ad.review_template(self.p,changed,'synthetic-final-reviewer')
        with self.assertRaises(ValueError):gp.prepare_handoff(self.p,changed,self.s,review)
        self.assertNotEqual(payload_sha256(changed),payload_sha256(self.d))

    def test_cached_context_reports_are_not_input_and_tampering_rejects(self):
        for key in ('recorded_answer_context','research_context','current_argument_context'):
            s=copy.deepcopy(self.s);s[key]=self.h['recorded_answer_context']
            with self.assertRaises(ValueError):gp.prepare_handoff(self.p,self.d,s,self.final_review)
        h=copy.deepcopy(self.h);h['recorded_answer_context']['reasoning_context']['context_review']['target_context']='Forged cache'
        with self.assertRaisesRegex(ValueError,'handoff changed'):gp.response_template(self.p,self.d,self.s,h,self.final_review)
        b=copy.deepcopy(self.b);b['recorded_answer_context']=self.h['recorded_answer_context']
        with self.assertRaises(ValueError):gp.validate_bundle(self.p,self.d,b,self.final_review)

    def test_all_v2_direct_apis_reject_non_json_before_normalization(self):
        self.adopt(); e=self.envelope()
        for bad in ({1:'non-string key'}, {'tuple':('coerced',)}, {'nonfinite':float('inf')}):
            p=dict(package=self.p, ignored=bad)
            calls=[lambda:gp.template(p,self.d,'op',include_recorded_answer_context=True),
                lambda:gp.prepare_handoff(p,self.d,self.s,self.final_review),
                lambda:gp.response_template(p,self.d,self.s,self.h,self.final_review),
                lambda:gp.import_response(p,self.d,self.s,self.h,self.r,self.f['provenance'],self.final_review),
                lambda:gp.validate_bundle(p,self.d,self.b,self.final_review),
                lambda:gp.review_template(p,self.d,self.b,'reviewer',self.final_review),
                lambda:gp.review_proposals(p,self.d,self.b,self.review,self.final_review),
                lambda:gp.export_reviewed(p,self.d,self.b,self.review,self.final_review),
                lambda:gp.inspect_reviewed(p,self.d,e,self.final_review),
                lambda:am.inspect(p,self.d,e,self.final_review)]
            for call in calls:
                with self.assertRaises(ValueError):call()
        packet=self.packet();packet['scope']['selected_claim_ids']=tuple(packet['scope']['selected_claim_ids'])
        with self.assertRaises(ValueError):gp.render_review(packet)
        # Legacy normalization stays deliberate for the default argument path.
        default=gp.template(dict(package=self.p,ignored={'tuple':('legacy',)}),self.d,'op')
        self.assertEqual(default['schema'],gp.SCOPE_SCHEMA)

    def test_limits_fail_without_truncation_or_downgrade(self):
        for limit, call, phrase in (
            ('MAX_INPUT_BYTES',lambda:gp.prepare_handoff(self.p,self.d,self.s,self.final_review),'8 MiB'),
            ('MAX_HANDOFF_BYTES',lambda:gp.prepare_handoff(self.p,self.d,self.s,self.final_review),'2 MiB'),
            ('MAX_OUTPUT_BYTES',lambda:self.packet(),'16 MiB'),
            ('MAX_OUTPUT_BYTES',lambda:gp.render_review(self.packet()),'16 MiB')):
            with patch.object(gp,limit,100), self.assertRaisesRegex(ValueError,phrase):call()
        packet=self.packet()
        with patch.object(gp,'MAX_OUTPUT_BYTES',100),self.assertRaisesRegex(ValueError,'text report'):gp.render_review(packet)
        huge=dict(package=self.p,ignored='x'*gp.MAX_INPUT_BYTES)
        with self.assertRaisesRegex(ValueError,'8 MiB'):gp.prepare_handoff(huge,self.d,self.s,self.final_review)

    def test_v2_full_pretty_json_output_bound_preserves_legacy_boundary(self):
        self.adopt()
        packet=self.packet();envelope=self.envelope()
        result=am.inspect(self.p,self.d,envelope,self.final_review)
        for value in (self.h,self.b,packet,envelope,result):
            compact=len(json.dumps(value,ensure_ascii=True,allow_nan=False).encode('utf-8'))
            pretty=len((json.dumps(value,ensure_ascii=True,allow_nan=False,indent=2)+'\n').encode('utf-8'))
            self.assertLess(compact,pretty)
            with patch.object(gp,'MAX_OUTPUT_BYTES',(compact+pretty)//2):
                with self.assertRaisesRegex(ValueError,'full JSON'):gp._output(value)
                legacy=copy.deepcopy(value)
                if 'schema' in legacy:legacy['schema']=legacy['schema'].replace('.v2','.v1')
                if 'proposal_review' in legacy:legacy['proposal_review']['schema']=gp.SCHEMAS[1]['packet']
                self.assertEqual(gp._output(legacy),legacy)
        compact=len(json.dumps(packet,ensure_ascii=True,allow_nan=False).encode('utf-8'))
        pretty=len((json.dumps(packet,ensure_ascii=True,allow_nan=False,indent=2)+'\n').encode('utf-8'))
        with patch.object(gp,'MAX_OUTPUT_BYTES',(compact+pretty)//2):
            with self.assertRaisesRegex(ValueError,'full JSON'):self.packet()

    def test_detached_outputs_no_input_mutation_or_io(self):
        self.adopt(); before=copy.deepcopy((self.p,self.d,self.s,self.h,self.r,self.b,self.review,self.final_review))
        with patch.object(Path,'open',side_effect=AssertionError('source I/O')), \
             patch('builtins.open',side_effect=AssertionError('file I/O')), \
             patch('socket.socket',side_effect=AssertionError('network I/O')):
            self.assertEqual(gp.prepare_handoff(self.p,self.d,self.s,self.final_review),self.h)
            result=am.inspect(self.p,self.d,self.envelope(),self.final_review)
            text=gp.render_review(result['proposal_review'])
        result['proposal_review']['recorded_answer_context']['reasoning_context']['context_review']['target_context']='Output edit'
        self.assertEqual((self.p,self.d,self.s,self.h,self.r,self.b,self.review,self.final_review),before)
        self.assertIn('not newly supplied or current argument context',text)
        for key in ('provider_invoked','external_transmission','source_reread'):
            self.assertIs(result['processing'][key],False)

    def test_rejected_pattern_history_replayed_preserved_and_bound(self):
        import test_pattern_evidence_reasons as fixture
        import pattern_proposals
        case=fixture.PatternEvidenceReasonTests();case.setUp()
        case.response['candidates'].append(copy.deepcopy(case.proposal));case.reimport();case.accept()
        case.review['decisions'][1].update(decision='reject',review_note='Rejected pattern <history> remains recorded.')
        self.answer_scope['research_context']['patterns']=pattern_proposals.export_reviewed(case.package,case.bundle,case.review)
        self.d=answer(self.f,self.answer_scope,self.answer_response)
        self.final_review=ad.review_template(self.p,self.d,'synthetic-final-reviewer');self.reset()
        context=self.h['recorded_answer_context']['reasoning_context']
        self.assertEqual(context['pattern_review']['proposal_review']['candidates'][1]['decision'],'reject')
        self.assertIn('Rejected pattern <history> remains recorded.',gp.render_review(self.packet()))
        d=copy.deepcopy(self.d)
        d['bundle']['scope']['research_context']['patterns']['review']['decisions'][1]['review_note']='Changed rejected pattern history'
        with self.assertRaises(ValueError):gp.prepare_handoff(self.p,d,self.s,self.final_review)

    def test_actual_cli_all_stages_and_escaped_context_text(self):
        self.answer_scope['research_context']['patterns']['hypotheses'][1]['scope_note']='Context <tag>\nnext\tfield\x1b[31m'
        self.d=answer(self.f,self.answer_scope,self.answer_response)
        self.final_review=ad.review_template(self.p,self.d,'synthetic-final-reviewer');self.reset();self.adopt()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            def put(name,value):
                path=root/(name+'.json');path.write_text(json.dumps(value),encoding='utf-8');return str(path)
            p=put('package',self.p);d=put('draft',self.d);fr=put('final',self.final_review)
            def cli(command,*args,text=False,ok=True):
                process=subprocess.run([sys.executable,str(ROOT/'argument_proposals.py'),command,p,d,*args,'--answer-review',fr],capture_output=True,text=True)
                if not ok:self.assertNotEqual(process.returncode,0);return process
                self.assertEqual(process.returncode,0,process.stderr)
                return process.stdout if text else json.loads(process.stdout)
            s=cli('template','--operator-id','synthetic-argument-operator','--include-recorded-answer-context')
            s['selected_claim_ids']=self.s['selected_claim_ids'];self.assertEqual(s,self.s);sp=put('scope',s)
            h=cli('prepare',sp);self.assertEqual(h,self.h);hp=put('handoff',h)
            r=cli('response-template',sp,hp);r['candidates']=self.r['candidates'];rp=put('response',r)
            b=cli('import',sp,hp,rp,put('provenance',self.f['provenance']));self.assertEqual(b,self.b);bp=put('bundle',b)
            review=cli('review-template',bp,'--reviewer-id','synthetic-argument-reviewer')
            self.assertTrue(all(x['decision']=='defer' for x in review['decisions']))
            rev=put('review',self.review);packet=cli('review',bp,rev);self.assertEqual(packet,self.packet())
            text=cli('review',bp,rev,'--format','text',text=True)
            self.assertIn('Context <tag>\\u000anext\\u0009field\\u001b[31m',text)
            self.assertNotIn('\x1b',text)
            e=cli('export',bp,rev);self.assertEqual(e,self.envelope());ep=put('envelope',e)
            inspection=cli('inspect',ep);self.assertEqual(inspection,am.inspect(self.p,self.d,e,self.final_review))
            proc=subprocess.run([sys.executable,str(ROOT/'argument_map.py'),p,d,ep,'--review',fr,'--format','text'],capture_output=True,text=True)
            self.assertEqual(proc.returncode,0,proc.stderr);self.assertIn('Recorded answer-preparation/import context',proc.stdout)
            bad=put('bad',dict(s,include_recorded_answer_context=False));cli('prepare',bad,ok=False)


if __name__ == '__main__': unittest.main()
