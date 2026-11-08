"""Passive synthetic HTML views, not researcher-fidelity or semantic validation."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch

import journey_html as view
import research_journey as journey
import source_recheck
import tests.test_research_journey as fixture
import tests.test_source_recheck as source_fixture
import shutil
import tests.test_application_proposals as applications
from persona import payload_sha256
from answer_draft import review_template
from argument_map import template as argument_template
from applicability_review import template as context_template

ROOT=Path(__file__).resolve().parents[1]


class Document(HTMLParser):
    def __init__(self,text):
        super().__init__(convert_charrefs=True);self.tags=[];self.ids=[];self.hrefs=[];self.attributes=[]
        self.current=None;self.saved={};self.plain=[];self.feed(text)
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs);self.tags.append(tag);self.attributes.append((tag,attrs))
        if 'id' in attrs:self.ids.append(attrs['id'])
        if 'href' in attrs:self.hrefs.append(attrs['href'])
        if attrs.get('id') in ('complete-json','snapshot-sha256'):
            self.current=tag;self.saved[attrs['id']]='';self.key=attrs['id']
    def handle_endtag(self,tag):
        if self.current==tag:self.current=None
    def handle_data(self,text):
        self.plain.append(text)
        if self.current:self.saved[self.key]+=text


class JourneyHtmlTests(unittest.TestCase):
    def setUp(self):self.case=fixture.ResearchJourneyTests();self.case.setUp();self.c=self.case.case
    def args(self):return self.case.args()
    def render(self,**kwargs):return view.render(*self.args(),**kwargs)
    def snapshot(self,text):return json.loads(Document(text).saved['complete-json'])

    def test_complete_snapshot_exact_hash_and_visible_review_boundary(self):
        text=self.render();doc=Document(text);result=journey.inspect(*self.args())
        self.assertEqual(self.snapshot(text),result)
        self.assertEqual(doc.saved['snapshot-sha256'],payload_sha256(result))
        for phrase in ('HUMAN_REVIEW_REQUIRED_NOT_RESEARCH_APPROVAL','Human review required.',
                       'No source files were reread','not confidence, readiness','not a complete corpus'):
            if phrase=='not confidence, readiness':phrase='never confidence, readiness'
            self.assertIn(phrase,text)
        self.assertIn('scientific_validation',text);self.assertIn('NOT_PERFORMED',text)

    def assert_passive(self,doc):
        self.assertTrue(set(doc.tags)<=set('html head meta title style body a header p h1 h2 h3 nav ul li main section div dl dt dd span details summary ol article br blockquote code pre footer strong'.split()))
        for tag,attrs in doc.attributes:
            for name,value in attrs.items():
                self.assertFalse(name.lower().startswith('on'));self.assertNotIn(name,('src','srcdoc','action','formaction','style'))
            if tag=='a':self.assertTrue(attrs['href'].startswith('#'))
        self.assertEqual(len(doc.ids),len(set(doc.ids)))
        self.assertTrue(all(href[1:] in doc.ids for href in doc.hrefs))
        csp=[a['content'] for tag,a in doc.attributes if tag=='meta' and a.get('http-equiv')=='Content-Security-Policy']
        self.assertEqual(csp,[view.CSP])
        self.assertIn("default-src 'none'",csp[0]);self.assertIn("form-action 'none'",csp[0])
        self.assertNotIn('unsafe-inline',csp[0]);self.assertIn("style-src 'sha256-"+view.STYLE_SHA256+"'",csp[0])

    def test_passive_allowlist_unique_internal_anchors_and_no_external_urls(self):
        text=self.render();doc=Document(text);self.assert_passive(doc)
        import base64,hashlib,re
        stylesheet=re.search(r'<style>(.*?)</style>',text,re.S).group(1)
        self.assertEqual(base64.b64encode(hashlib.sha256(stylesheet.encode()).digest()).decode(),view.STYLE_SHA256)
        result=journey.inspect(*self.args())
        for row in result['evidence_routes']:
            self.assertIn('evidence-'+row['reference_sha256'],doc.ids)
            self.assertIn('#evidence-'+row['reference_sha256'],doc.hrefs)
        self.assertNotIn('input',doc.tags);self.assertNotIn('button',doc.tags)

    def test_untrusted_text_markup_urls_entities_and_controls_stay_inert(self):
        bad='</pre><script>globalThis.pwned=1</script><img src="https://example.invalid/x" onerror="alert(1)"><svg onload="alert(1)"><style>body{background:url(https://example.invalid)}</style> javascript:alert(1) file:///private &quot; \u202e \x00 한글'
        self.c.patterns['hypotheses'][0]['operator_hypothesis']=bad
        self.c.links['links'][0]['rationale']=bad
        self.c.proposal['link_artifact_sha256']=payload_sha256(self.c.links)
        self.c.proposal['steps'][0]['rationale']=bad
        self.case.argument['steps'][0]['bridge_rationale']=bad
        self.case.relations['relations'][0]['rationale']=bad
        self.case.review['decisions'][0]['note']=bad
        self.case.argument['review_sha256']=payload_sha256(self.case.review)
        text=self.render();doc=Document(text);self.assert_passive(doc)
        self.assertEqual(self.snapshot(text),journey.inspect(*self.args()))
        self.assertNotIn('<script>',text);self.assertNotIn('<img',text);self.assertNotIn('<svg',text)
        self.assertNotIn('\u202e',text);self.assertNotIn('\x00',text)
        self.assertIn('\\u202e',text);self.assertIn('한글',text)
        self.assertIn('globalThis.pwned=1',''.join(doc.plain))

    def test_source_excerpt_and_identifiers_are_escaped_not_link_targets(self):
        # Exercise the presentation primitive with hostile source/identifier strings;
        # public rendering still starts with inspect, never with this formatting helper.
        result=journey.inspect(*self.args());row=result['evidence_routes'][0]
        hostile='</blockquote><iframe src="https://example.invalid"></iframe>'
        row['evidence']['observation']['evidence_quote']=hostile
        row['evidence']['reference']['paper_id']='paper" onclick="alert(1)'
        row['reference_sha256']=payload_sha256(row['evidence']['reference'])
        text=view._format(result);doc=Document(text);self.assert_passive(doc)
        self.assertIn(hostile,self.snapshot(text)['evidence_routes'][0]['evidence']['observation']['evidence_quote'])
        self.assertNotIn('<iframe',text)
        self.assertTrue(all('onclick' not in identity for identity in doc.ids))

    def test_one_inspection_no_files_or_network_and_no_input_mutation(self):
        before=copy.deepcopy(self.args())
        with patch.object(view,'inspect_journey',wraps=journey.inspect) as inspect, \
             patch('pathlib.Path.open',side_effect=AssertionError('no files')),patch('socket.socket',side_effect=AssertionError('no network')):
            text=self.render();self.assertEqual(inspect.call_count,1)
        self.assertEqual(before,self.args());self.assertEqual(self.snapshot(text),journey.inspect(*self.args()))

    def test_live_source_recheck_reads_once_per_file_and_preserves_historical_labels(self):
        selection=source_recheck.template(self.c.package,'synthetic-source')
        for row in selection['sources']:row['source_file']=row['paper_id']+'.md'
        with patch.object(source_recheck,'read_source_bytes',wraps=source_recheck.read_source_bytes) as reads, \
             patch.object(view,'inspect_journey',wraps=journey.inspect) as inspect:
            text=self.render(source_selection=selection,source_root=ROOT/'examples/synthetic-sources')
            self.assertEqual(reads.call_count,2);self.assertEqual(inspect.call_count,1)
        snapshot=self.snapshot(text);self.assertTrue(snapshot['source_recheck']['all_stored_quotes_match'])
        self.assertTrue(snapshot['source_reread']);self.assertFalse(snapshot['current_checks_replace_recorded_labels'])
        self.assertIn('Separate current quote check:',text)
        for row in snapshot['evidence_routes']:self.assertIn(row['evidence']['recorded_source_check'],text)
        self.assertIn('not establish authenticity or semantic support',text)

    def test_source_gap_and_unused_paper_are_visible_without_promotion(self):
        ref=self.case.add_outside_paper()
        self.c.context['assessments'][0]['counterevidence_refs'].append(ref)
        text=self.render();snapshot=self.snapshot(text)
        row=next(r for r in snapshot['evidence_routes'] if r['evidence']['reference']==ref)
        self.assertFalse(row['actively_used_in_answer_or_design']);self.assertFalse(row['in_topic_timeline'])
        self.assertIn('synthetic-outside',text);self.assertIn('unused_paper_ids',text)

    def test_missing_and_blank_stored_excerpts_are_visible_gaps(self):
        c=source_fixture.JourneySourceRecheckTests();c.setUp();self.addCleanup(c.doCleanups)
        for quote in (None,'   '):
            c.rebuilt(lambda papers:papers[0]['observations'][0].update(evidence_quote=quote));c.rebind_journey()
            text=view.render(*c.case.args(),source_selection=c.selection,source_root=c.root)
            self.assertIn('NOT_SUPPLIED (missing or blank stored excerpt)',text)
            self.assertIn('STORED_QUOTE_MISSING',text)
            self.assertEqual(self.snapshot(text)['evidence_routes'][0]['evidence']['observation']['evidence_quote'],quote)

    def test_unused_live_source_gap_is_retained_outside_route_index(self):
        c=source_fixture.JourneySourceRecheckTests();c.setUp();self.addCleanup(c.doCleanups)
        ref=c.case.add_outside_paper();c.package=c.case.case.package
        shutil.copyfile(c.root/'synthetic-0.md',c.root/'synthetic-outside.md')
        c.rebuilt(lambda papers:papers[-1]['observations'][0].update(evidence_quote=None));c.rebind_journey()
        text=view.render(*c.case.args(),source_selection=c.selection,source_root=c.root);snapshot=self.snapshot(text)
        self.assertFalse(snapshot['source_recheck']['all_stored_quotes_match'])
        self.assertEqual(snapshot['source_recheck']['checked_paper_count'],3)
        self.assertNotIn(ref,[r['evidence']['reference'] for r in snapshot['evidence_routes']])
        self.assertIn('STORED_QUOTE_MISSING',text);self.assertIn('outside the displayed route index',text)
        self.assertIn('Human review required.',text)

    def test_imported_observation_origin_remains_visible_but_history_not_replayed(self):
        f=fixture.observation_fixture.ObservationRevisionTests();f.setUp();package=f.candidate()['package']
        links,proposal,draft=f.bindings(package);review=review_template(package,draft,'synthetic-reviewer')
        argument=argument_template(package,draft,'synthetic-map',review)
        patterns=fixture.pattern_template(package,'synthetic-pattern')
        a=dict(paper_id='synthetic-0',observation_index=0,dimension=None);b=dict(a,paper_id='synthetic-1')
        patterns['hypotheses']=[dict(pattern_id='comparison',operator_hypothesis='Synthetic comparison.',scope_note='Synthetic only.',
            support_refs=[a],challenge_refs=[b],alternative_explanation=None,falsification_check=None,uncertainty=None)]
        context=context_template(package,draft['question'],'Synthetic target','model design',2020,'synthetic-context')
        relations=fixture.relation_template(package,'synthetic-relations')
        text=view.render(package,patterns,context,links,proposal,draft,argument,relations,'comparison',review)
        snapshot=self.snapshot(text)
        self.assertEqual(len(snapshot['evidence_scope']['recorded_imported_observations']),2)
        self.assertEqual(snapshot['provenance_history_replay'],'NOT_PERFORMED')
        self.assertIn('operator_reviewed_imported_observation',text);self.assertIn('synthetic-generator',text)

    def test_parent_component_roles_active_rejected_claims_and_direct_only_argument_preserved(self):
        self.case.review['decisions'][0].update(decision='reject',note='Rejected premise remains a supplied citation, not accepted evidence.')
        self.case.argument['review_sha256']=payload_sha256(self.case.review)
        text=self.render();snapshot=self.snapshot(text)
        parent=next(r for r in snapshot['evidence_routes'] if r['evidence']['reference']==self.c.review)
        component=next(r for r in snapshot['evidence_routes'] if r['evidence']['reference']==self.c.b)
        self.assertNotEqual(parent['reference_sha256'],component['reference_sha256'])
        self.assertEqual(parent['pattern_roles'],['challenge']);self.assertEqual(component['pattern_roles'],['support'])
        self.assertIn('DECLARED_REJECT',text)
        self.assertEqual(snapshot['argument_review']['steps'][0]['conclusion']['direct_citation_count'],0)
        self.assertIn('including rejected or deferred claims',text)

    def test_imported_pattern_and_application_original_reviewed_rejected_history_survives(self):
        c=applications.ApplicationProposalTests();c.setUp()
        pattern=fixture.imported_fixture.PatternEvidenceReasonTests();pattern.setUp();pattern.accept()
        c.c.patterns=fixture.export_reviewed(pattern.package,pattern.bundle,pattern.review)
        c.handoff=applications.proposals.prepare_handoff(*c.args());c.response['handoff_sha256']=payload_sha256(c.handoff)
        c.response['candidates'].append(dict(c.candidate,application_rationale='Rejected synthetic HTML alternative.'))
        c.reimport();c.accept();c.review['decisions'][1].update(decision='reject',review_note='Keep for review visibility only.')
        envelope=c.envelope();text=view.render(*c.case.case.args(),method_applications=envelope)
        snapshot=self.snapshot(text);self.assertIn('proposal_review',snapshot['method_application_review'])
        for phrase in ('Synthetic model proposed','Synthetic reviewer changed','Rejected synthetic HTML alternative.',
                       'Model proposed','Reviewer supplied','not authenticated','checks_completion'):
            self.assertIn(phrase,text)
        self.assert_passive(Document(text))

    def test_all_retained_and_no_mechanical_prompts_never_mean_approval(self):
        for row in self.case.review['decisions']:row.update(decision='retain',note='Synthetic recorded retain only.')
        self.case.argument['review_sha256']=payload_sha256(self.case.review)
        text=self.render();self.assertIn('Human review required.',text)
        result=journey.inspect(*self.args());result['review_agenda']=[]
        empty=view._format(result)
        self.assertIn('No mechanical prompts detected. Human review and scientific validation are still required.',empty)
        self.assertFalse(self.snapshot(empty)['automatic_approval'])

    def test_missing_optional_sections_no_review_and_absent_topic_are_explicit(self):
        self.case.argument['review_sha256']=None
        args=self.args();args[-1]=None
        text=view.render(*args);self.assertIn('Answer review: NOT_SUPPLIED',text)
        self.assertNotIn('<p>Method application:',text)
        self.c.context=context_template(self.c.package,self.c.context['question'],'Synthetic target','absent topic',2020,'op')
        text=view.render(*self.args()[:-1],None);self.assertIn('NO_TOPIC_MATCHING_RECORDS',text)
        self.assertEqual(self.snapshot(text)['trajectory_review']['years'],[])

    def test_invalid_upstream_artifacts_reject_instead_of_rendering_cached_report(self):
        for index,mutate in [(7,lambda v:v.update(persona_sha256='0'*64)),
            (6,lambda v:v.update(review_sha256='0'*64)),(9,lambda v:v.update(draft_sha256='0'*64)),
            (0,lambda v:v['knowledge']['papers'][-1].update(authorized=False)),
            (0,lambda v:v['knowledge']['papers'][-1].update(split='holdout'))]:
            args=copy.deepcopy(self.args());mutate(args[index])
            with self.assertRaises(ValueError):view.render(*args)
        with self.assertRaises(TypeError):view.render(journey.inspect(*self.args()))
        with self.assertRaises(ValueError):self.render(source_selection={})
        with self.assertRaises(ValueError):self.render(source_root=ROOT)

    def test_invalid_application_and_source_selection_fail_before_any_source_read(self):
        selection=source_recheck.template(self.c.package,'synthetic-source')
        for row in selection['sources']:row['source_file']=row['paper_id']+'.md'
        with patch.object(source_recheck,'read_source_bytes',side_effect=AssertionError('must not read')) as reads:
            with self.assertRaises(ValueError):self.render(method_applications={'schema':'forged'},source_selection=selection,source_root=ROOT/'examples/synthetic-sources')
            bad=copy.deepcopy(selection);bad['sources'][-1]['source_file']='../escape.md'
            with self.assertRaises(ValueError):self.render(source_selection=bad,source_root=ROOT/'examples/synthetic-sources')
            reads.assert_not_called()

    def test_output_budget_counts_final_utf8_after_escaping_and_not_partial_document(self):
        text=self.render();size=len(text.encode('utf-8'))
        with patch.object(view,'MAX_OUTPUT_BYTES',size):self.assertEqual(self.render(),text)
        with patch.object(view,'MAX_OUTPUT_BYTES',size-1):
            with self.assertRaisesRegex(ValueError,'HTML journey exceeds'):self.render()
        self.assertIn('한글',view._escape('한글'))
        d=view._Document()
        with patch.object(view,'MAX_OUTPUT_BYTES',2):
            with self.assertRaises(ValueError):d.add('한')

    def test_unmapped_reference_remains_visible_without_new_route_or_url(self):
        result=journey.inspect(*self.args());ref=dict(paper_id='outside-history',observation_index=0,dimension=None)
        result['pattern_transfer_review']['extra_synthetic_reference']=ref
        text=view._format(result);doc=Document(text);self.assert_passive(doc)
        self.assertIn('outside the displayed route index',text)
        self.assertNotIn('evidence-'+payload_sha256(ref),doc.ids)

    def test_json_and_text_legacy_outputs_unchanged(self):
        self.assertEqual(payload_sha256(journey.inspect(*self.args())),'a4405809c8fde162293d6e73dd2ca8083329570d44ac9e2428f0607fa7d23350')
        self.assertEqual(payload_sha256(journey.render(*self.args())),'b21be5e06cde18dfd52a0c6d065d6161b857ba6c42f8921594f03bcfe8605d95')

    def test_cli_html_strict_json_unicode_paths_and_no_partial_failure_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);paths=[]
            for index,value in enumerate(self.args()[:8]+[self.case.review]):
                path=root/('합성 input '+str(index)+'.json');path.write_text(json.dumps(value),encoding='utf-8');paths.append(path)
            argv=[sys.executable,str(ROOT/'research_journey.py'),*map(str,paths[:8]),'--pattern-id','comparison','--review',str(paths[8]),'--format','html']
            run=subprocess.run(argv,cwd=directory,capture_output=True,timeout=30)
            self.assertEqual(run.returncode,0,run.stderr);self.assertTrue(run.stdout.startswith(b'<!doctype html>'))
            self.assertEqual(self.snapshot(run.stdout.decode()),journey.inspect(*self.args()))
            for bad in ('{"key":1,"key":2}','{"key":NaN}'):
                paths[8].write_text(bad)
                run=subprocess.run(argv,cwd=directory,capture_output=True,timeout=30)
                self.assertNotEqual(run.returncode,0);self.assertEqual(run.stdout,b'');self.assertNotIn(b'Traceback',run.stderr)


if __name__=='__main__':unittest.main()
