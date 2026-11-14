import copy
import hashlib
import html
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch

import human_validation as hv
import package_html as view
import package_overview as overview
from journey_html import STYLE, CSP
from observation_provenance import HASH_FIELDS, ORIGIN, content_sha256
from persona import payload_sha256
from research_workflow import build

ROOT=Path(__file__).resolve().parents[1]
PACKAGE=ROOT/'examples/trajectory-conditions-package.json'
RECORD=ROOT/'examples/manual-human-validation.json'


class Markup(HTMLParser):
    def __init__(self,text):
        super().__init__();self.tags=[];self.ids=[];self.hrefs=[];self.attrs=[];self.feed(text)
    def handle_starttag(self,tag,attrs):
        self.tags.append(tag);self.attrs.extend(attrs)
        for key,value in attrs:
            if key=='id':self.ids.append(value)
            if key=='href':self.hrefs.append(value)


class PackageOverviewTests(unittest.TestCase):
    def setUp(self):
        self.package=json.loads(PACKAGE.read_bytes())
        self.record=json.loads(RECORD.read_bytes())
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)

    def corpus(self):
        return {**{k:self.package['persona'][k] for k in ('author_id','version','build_id')},
                'papers':copy.deepcopy(self.package['knowledge']['papers'])}

    def cli(self,*args,seed=None):
        env=dict(os.environ)
        if seed is not None:env['PYTHONHASHSEED']=str(seed)
        return subprocess.run([sys.executable,str(ROOT/'package_overview.py'),*map(str,args)],
                              cwd=ROOT,env=env,capture_output=True)

    def test_inspector_identity_counts_and_nonclaims(self):
        result=overview.inspect(self.package)
        self.assertEqual(len(result['papers']),5)
        self.assertEqual(sum(len(p['observations']) for p in result['papers']),6)
        self.assertEqual(result['persona_sha256'],payload_sha256(self.package['persona']))
        self.assertEqual(result['current_local_source_check'],'NOT_PERFORMED')
        self.assertEqual(set(result['validation_axis_declarations'].values()),{'NOT_DECLARED'})
        for key in ('llm_used','selection_performed','source_reread','canonical_update_performed'):
            self.assertIs(result[key],False)
        self.assertEqual(result['aggregate_score'],'NOT_COMPUTED')

    def test_human_axis_summary_only(self):
        result=overview.inspect(self.package,[self.record])
        report=result['human_validation']
        self.assertEqual(report['status'],'RECORDED_CURRENT')
        self.assertEqual(set(report['records'][0]),{'record_sha256','binding_status','judgement_counts'})
        serialized=overview.json_text(result)
        self.assertNotIn('"rater_id":',serialized);self.assertNotIn('"rationale":',serialized)
        for rater in self.record['raters']:self.assertNotIn(rater['rater_id'],serialized)
        self.assertEqual(report['boundary'],hv.AXIS_BOUNDARY)

    def test_human_duplicate_invalid_and_stale(self):
        with self.assertRaises(ValueError):overview.inspect(self.package,[self.record,self.record])
        bad=copy.deepcopy(self.record);bad['schema']='wrong'
        with self.assertRaises(ValueError):overview.inspect(self.package,[bad])
        corpus=self.corpus();corpus['version']='new-version';package=build(corpus)
        self.assertEqual(overview.inspect(package,[self.record])['human_validation']['status'],'STALE_PACKAGE')

    def test_validation_declarations_not_derived(self):
        package=copy.deepcopy(self.package)
        package['persona']['validation']={key:'synthetic declaration' for key in overview.AXES}
        package['knowledge']['persona_payload_sha256']=payload_sha256(package['persona'])
        self.assertEqual(overview.inspect(package)['validation_axis_declarations'],package['persona']['validation'])

    def test_wrapper_ignores_application_boundary(self):
        expected=overview.inspect(self.package)
        self.assertEqual(expected,overview.inspect(dict(package=self.package,application={'unsafe':'injected'},boundary='forged')))

    def test_bound_hash_and_rule_forgery(self):
        package=copy.deepcopy(self.package);package['knowledge']['papers'][0]['year']=9999
        with self.assertRaises(ValueError):overview.inspect(package)
        package=copy.deepcopy(self.package);package['persona']['rules'][0]['method']='forged'
        package['knowledge']['persona_payload_sha256']=payload_sha256(package['persona'])
        with self.assertRaises(ValueError):overview.inspect(package)

    def test_source_check_and_authorization_fail_closed(self):
        for field,value in [('authorized',False),('split','holdout'),('source_verification','SUCCESS')]:
            package=copy.deepcopy(self.package);package['knowledge']['papers'][0][field]=value
            package['persona']['knowledge_papers_sha256']=payload_sha256(package['knowledge']['papers'])
            package['knowledge']['persona_payload_sha256']=payload_sha256(package['persona'])
            with self.assertRaises(ValueError):overview.inspect(package)

    def test_no_input_mutation(self):
        before=copy.deepcopy(self.package);record=copy.deepcopy(self.record)
        view.render(overview.inspect(self.package,[self.record]))
        self.assertEqual(self.package,before);self.assertEqual(self.record,record)

    def test_native_order_and_components(self):
        corpus=self.corpus();corpus['papers'].reverse()
        obs=corpus['papers'][0]['observations'][0]
        obs['reasoning']={name:dict(text='Invented '+name,locator='synthetic',evidence_quote='invented',claim_type='operator_interpretation')
                          for name in ('uncertainty','alternative_explanation')}
        result=overview.inspect(build(corpus))
        self.assertEqual([r['recorded_paper']['paper_id'] for r in result['papers']],[p['paper_id'] for p in corpus['papers']])
        row=result['papers'][0]['observations'][0]
        self.assertEqual([c['reference']['dimension'] for c in row['components']],['uncertainty','alternative_explanation'])
        self.assertNotIn('uncertainty',row['coverage']['missing_dimensions'])
        self.assertIn('question_framing',row['coverage']['missing_dimensions'])
        parsed=Markup(view.render(result));self.assertEqual(len(parsed.ids),len(set(parsed.ids)))
        for ref in result['references']:self.assertIn('evidence-'+payload_sha256(ref),parsed.ids)

    def test_topics_casefold_and_coverage_boundaries(self):
        corpus=self.corpus()
        for i,paper in enumerate(corpus['papers']):
            for obs in paper['observations']:obs['topic']='zeta' if i%2 else 'ALPHA'
        result=overview.inspect(build(corpus))
        self.assertEqual([t['topic'] for t in result['topic_inventory']['topics']],['alpha','zeta'])
        self.assertIn('not quality',result['topic_inventory']['boundary'])
        self.assertIn('readiness',result['coverage']['boundary'])

    def test_passive_csp_and_anchors(self):
        text=view.render(overview.inspect(self.package));parsed=Markup(text)
        self.assertFalse(set(parsed.tags)&{'script','form','input','iframe','img','link','object'})
        self.assertFalse(any(key.startswith('on') for key,_ in parsed.attrs))
        self.assertEqual(len(parsed.ids),len(set(parsed.ids)))
        for href in parsed.hrefs:self.assertTrue(href.startswith('#'));self.assertIn(href[1:],parsed.ids)
        self.assertIn(html.escape(CSP,quote=True),text)
        self.assertEqual(re.search(r'<style>(.*?)</style>',text,re.S).group(1),STYLE)

    def test_exact_json_snapshot(self):
        result=overview.inspect(self.package,[self.record]);text=view.render(result)
        snapshot=html.unescape(re.search(r'<pre id="json-snapshot">(.*?)</pre>',text,re.S).group(1))
        self.assertEqual(snapshot,overview.json_text(result));self.assertEqual(json.loads(snapshot),result)

    def test_xss_long_unicode_ids_and_file_labels(self):
        corpus=self.corpus();paper=corpus['papers'][0]
        paper['paper_id']='한국어-'+('x'*150)+'<script>alert(1)</script>'
        paper['source_file']='private-<img src=x>.md'
        paper['observations'][0]['limitation']='<script>alert(1)</script>'
        result=overview.inspect(build(corpus));text=view.render(result);parsed=Markup(text)
        self.assertNotIn('script',parsed.tags);self.assertNotIn('img',parsed.tags)
        self.assertIn('&lt;script&gt;',text);self.assertIn('한국어',text)
        self.assertIn('overflow-wrap:anywhere',STYLE)
        self.assertIn('source_file',text)

    def test_empty_observations_many_records(self):
        corpus=self.corpus()
        for paper in corpus['papers']:paper['observations']=[]
        result=overview.inspect(build(corpus));self.assertEqual(result['references'],[])
        self.assertEqual(result['coverage']['status'],'NO_OBSERVATIONS')
        self.assertIn('Empty list',view.render(result))
        corpus=self.corpus();obs=corpus['papers'][0]['observations'][0]
        corpus['papers'][0]['observations']=[copy.deepcopy(obs) for _ in range(40)]
        result=overview.inspect(build(corpus));parsed=Markup(view.render(result))
        self.assertEqual(len(parsed.ids),len(set(parsed.ids)))

    def test_imported_origins_visible_not_authenticated(self):
        corpus=self.corpus();paper=corpus['papers'][0];obs=paper['observations'][0]
        origin={key:'a'*64 for key in HASH_FIELDS}
        origin.update(schema='persona.observation-origin.v1',origin=ORIGIN,candidate_id='synthetic-candidate',
            paper_id=paper['paper_id'],reviewer_id='synthetic-reviewer',operator_id='synthetic-operator',
            proposed_claim_type=obs['claim_type'],proposed_stance=obs['stance'],source_sha256=paper['source_sha256'],
            reviewed_observation_sha256=content_sha256(obs),import_record=dict(handoff_sha256='b'*64,response_sha256='c'*64,
            provenance=dict(provider_id='synthetic-provider',model_id='synthetic-model',run_id='synthetic-run',
                            operator_id='synthetic-generator',execution_location='local')))
        obs['observation_origin']=origin
        result=overview.inspect(build(corpus))
        self.assertEqual(result['imported_observation_origins'][0]['observation_origin'],origin)
        self.assertEqual(result['imported_observation_origins'][0]['audit_status'],'OBSERVATION_ADOPTION_NOT_REPLAYED')
        self.assertIn('synthetic-provider',view.render(result))

    def test_json_and_html_limits(self):
        result=overview.inspect(self.package)
        size=len(overview.json_text(result).encode())
        with patch.object(overview,'MAX_OUTPUT_BYTES',size):overview.json_text(result)
        with patch.object(overview,'MAX_OUTPUT_BYTES',size-1):
            with self.assertRaises(ValueError):overview.inspect(self.package)
        text=view.render(result)
        with patch.object(view,'MAX_OUTPUT_BYTES',len(text.encode())-1):
            with self.assertRaisesRegex(ValueError,'HTML package overview'):view.render(result)

    def test_input_and_shared_human_budget(self):
        with patch.object(overview,'MAX_INPUT_BYTES',1),patch.object(sys,'argv',['package_overview.py',str(PACKAGE)]):
            with self.assertRaises(SystemExit):overview.main()
        with patch.object(hv,'MAX_INPUT_BYTES',len(RECORD.read_bytes())*2-1):
            reader=hv.bounded_reader();reader(RECORD)
            with self.assertRaises(ValueError):reader(RECORD)

    def test_seed_determinism_json_html(self):
        for format in ('json','html'):
            left=self.cli(PACKAGE,'--format',format,'--human-validation',RECORD,seed=1)
            right=self.cli(PACKAGE,'--format',format,'--human-validation',RECORD,seed=42)
            self.assertEqual(left.returncode,0,left.stderr);self.assertEqual(right.returncode,0,right.stderr)
            self.assertEqual(left.stdout,right.stdout)

    def test_no_partial_stdout_and_exclusive_output(self):
        bad=self.root/'bad.json';bad.write_bytes(b'{"package":null}\n')
        result=self.cli(bad);self.assertNotEqual(result.returncode,0);self.assertEqual(result.stdout,b'')
        target=self.root/'view.html';result=self.cli(PACKAGE,'--format','html','--output',target)
        self.assertEqual(result.returncode,0,result.stderr);before=target.read_bytes()
        result=self.cli(PACKAGE,'--format','html','--output',target)
        self.assertNotEqual(result.returncode,0);self.assertEqual(result.stdout,b'');self.assertEqual(target.read_bytes(),before)

    def test_documented_commands(self):
        text=(ROOT/'docs/PACKAGE_HTML.md').read_text(encoding='utf-8')
        blocks=re.findall(r'```sh\n(.*?)```',text,re.S);self.assertTrue(blocks)
        for block in blocks:
            for line in block.splitlines():
                if not line.strip():continue
                args=shlex.split(line);self.assertNotIn('>',args)
                args=[a.replace('OUTPUT',str(self.root)) for a in args];args[0]=sys.executable
                result=subprocess.run(args,cwd=ROOT,capture_output=True)
                self.assertEqual(result.returncode,0,result.stderr)

    def test_privacy_and_boundaries_at_both_ends(self):
        text=view.render(overview.inspect(self.package))
        for tag in ('header','footer'):
            section=re.search('<'+tag+r'>(.*?)</'+tag+'>',text,re.S).group(1)
            self.assertIn(html.escape(overview.PRIVACY,quote=True),section)
            self.assertIn(html.escape(overview.BOUNDARY,quote=True),section)


if __name__=='__main__':unittest.main()
