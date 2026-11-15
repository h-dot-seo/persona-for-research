"""Passive comparison navigation; exact evidence keys never imply stable identity."""
import copy
import hashlib
import html
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import journey_compare as comparison
import journey_compare_html as view
import journey_html as single
import research_journey as journey
import source_recheck
from tests import test_journey_compare as fixture

ROOT=Path(__file__).resolve().parents[1]

class Markup(HTMLParser):
    def __init__(self,text):
        super().__init__();self.ids=[];self.hrefs=[];self.tags=[];self.attrs=[];self.feed(text)
    def handle_starttag(self,tag,attrs):
        self.tags.append(tag);self.attrs.extend(attrs)
        for key,val in attrs:
            if key=='id':self.ids.append(val)
            if key=='href':self.hrefs.append(val)


def snapshot(text):
    return json.loads(html.unescape(re.search(r'<pre id="json-snapshot">(.*?)</pre>',text,re.S).group(1)))

class ComparisonHtmlTests(unittest.TestCase):
    def setUp(self):
        self.f=fixture.JourneyComparisonTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.a=self.f.card(0);self.b=self.f.card(1)
    def args(self):return self.a,self.f.roots[0],self.b,self.f.roots[1]
    def passive(self,text):
        p=Markup(text);self.assertEqual(len(p.ids),len(set(p.ids)))
        self.assertTrue(all(h.startswith('#') and h[1:] in p.ids for h in p.hrefs))
        self.assertFalse(set(p.tags)&{'script','form','input','iframe','img','link','object','embed','svg','math','button'})
        self.assertFalse(any(k.lower().startswith('on') or k in ('src','style','srcset') for k,v in p.attrs))
        self.assertIn(('content',single.CSP),p.attrs);self.assertIn('<style>'+single.STYLE+'</style>',text)
        self.assertIn('Keep this comparison local',text)
        return p
    def test_exact_snapshot_one_comparison_and_two_fresh_reports(self):
        before=copy.deepcopy((self.a,self.b))
        with patch.object(comparison,'compare',wraps=comparison.compare) as calls,patch.object(journey,'inspect',wraps=journey.inspect) as reads:
            text=comparison.render(*self.args(),format='html')
        self.assertEqual(calls.call_count,1);self.assertEqual(reads.call_count,2)
        self.assertEqual(snapshot(text),comparison.compare(*self.args()));self.assertEqual(before,(self.a,self.b))
        p=self.passive(text)
        refs=snapshot(text)['previous_report']['evidence_routes']
        for row in refs:
            for side in ('previous','current'):
                self.assertIn(side+'-evidence-'+row['reference_sha256'],p.ids)
                self.assertIn('#'+side+'-evidence-'+row['reference_sha256'],p.hrefs)

    def test_changed_korean_long_text_inert_snapshot_and_declared_decisions(self):
        draft=self.f.read(1,'draft');draft['claims'][0]['text']='현재 한국어 '+('긴식별자'*80)+' <script>alert(1)</script> ![](https://example.invalid/x) \u202e'
        self.f.write(1,'draft',draft);self.f.rebind_answer(1);self.b=self.f.card(1)
        result=comparison.compare(*self.args());text=view.render(result);self.passive(text)
        self.assertNotIn('<script>',text);self.assertNotIn('\u202e',text);self.assertIn('현재 한국어',text)
        self.assertEqual(snapshot(text),result)
        self.assertEqual(snapshot(text)['current_report']['review_agenda'],result['current_report']['review_agenda'])
        self.assertIn('CHANGED_AT_DECLARED_ID',text)

    def test_prefix_default_bytes_and_prefix_validation(self):
        ref={'paper_id':'synthetic','observation_index':0,'dimension':None};digest=single.payload_sha256(ref)
        original=''.join(single._tree({'nested':[ref]}, {digest}))
        self.assertEqual(original,''.join(single._tree({'nested':[ref]}, {digest},anchor_prefix='')))
        for side in ('previous-','current-'):
            output=''.join(single._tree({'nested':[ref]}, {digest},anchor_prefix=side))
            self.assertEqual(output,original.replace('#evidence-','#'+side+'evidence-'))
        with self.assertRaises(ValueError):''.join(single._tree(ref,{digest},anchor_prefix='"><script>'))

    def test_empty_route_sections_and_all_report_history_preserved(self):
        # Formatting-only empty-state test, not a claim that this edited dict was freshly validated.
        result=comparison.compare(*self.args());result['exact_reference_comparison']=[]
        for side in ('previous','current'):result[side+'_report']['evidence_routes']=[]
        text=view.render(result);self.passive(text);self.assertEqual(snapshot(text),result)
        self.assertIn('No supplied route comparison entries.',text);self.assertEqual(text.count('No supplied evidence routes.'),2)
        self.assertIn('Both complete fresh reports',text)

    def test_one_sided_current_source_check_reads_once_and_preserves_files(self):
        source=self.f.sources(0);self.a=self.f.card(0,source)
        files={p:p.read_bytes() for root in self.f.roots for p in root.rglob('*') if p.is_file()}
        with patch.object(source_recheck,'audit',wraps=source_recheck.audit) as audit,patch('socket.socket',side_effect=AssertionError('network')):
            text=comparison.render(*self.args(),previous_source_root=source,format='html')
        self.assertEqual(audit.call_count,1);r=snapshot(text)
        self.assertNotEqual(r['source_recheck_scope']['previous'],r['source_recheck_scope']['current'])
        self.assertEqual(files,{p:p.read_bytes() for p in files});self.passive(text)

    def test_imported_rejected_and_observation_histories_remain_exact(self):
        # Reuse existing bound synthetic history builders; no invented bindings.
        for method in ('test_imported_pattern_and_application_histories_survive_both_formats',
                       'test_imported_observation_history_is_preserved_without_claiming_replay',
                       'test_review_decision_and_note_changes_are_not_lost_in_unchanged_claims'):
            case=fixture.JourneyComparisonTests();case.setUp()
            try:
                getattr(case,method)()
                result=case.compare();text=view.render(result)
                self.assertEqual(snapshot(text),result);self.passive(text)
                if 'application' in method:self.assertIn('Rejected synthetic application.',text)
                if 'observation_history' in method:self.assertIn('observation_origin',text)
                self.assertFalse(result['automatic_approval'])
            finally:case.doCleanups()

    def test_bounded_writer_snapshot_and_no_partial_cli_output(self):
        result=comparison.compare(*self.args());text=view.render(result);size=len(text.encode())
        with patch.object(view,'MAX_OUTPUT_BYTES',size):self.assertEqual(view.render(result),text)
        with patch.object(view,'MAX_OUTPUT_BYTES',size-1),self.assertRaises(ValueError):view.render(result)
        with patch.object(view,'MAX_OUTPUT_BYTES',10),self.assertRaises(ValueError):view.render(result)
        with tempfile.TemporaryDirectory() as td:
            a=Path(td)/'a.json';b=Path(td)/'b.json';out=Path(td)/'new.html'
            a.write_bytes(json.dumps(self.a).encode());b.write_bytes(json.dumps(self.b).encode())
            argv=['journey_compare.py',str(a),str(b),'--previous-root',str(self.f.roots[0]),'--current-root',str(self.f.roots[1]),'--format','html','--output',str(out)]
            import io,contextlib
            stdout=io.BytesIO();wrapper=io.TextIOWrapper(stdout,encoding='utf-8')
            with patch.object(sys,'argv',argv),patch.object(sys,'stdout',wrapper),patch.object(view,'MAX_OUTPUT_BYTES',10),contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as e:comparison.main()
                self.assertEqual(e.exception.code,1);wrapper.flush();self.assertEqual(stdout.getvalue(),b'')
            self.assertFalse(out.exists())

    def test_cli_two_seeds_exclusive_and_cached_input_rejection(self):
        paths=[]
        for side,card in enumerate((self.a,self.b)):
            p=self.f.roots[side]/'입력 with spaces.json';p.write_bytes(json.dumps(card).encode());paths.append(p)
        args=[sys.executable,str(ROOT/'journey_compare.py'),*map(str,paths),'--previous-root',str(self.f.roots[0]),'--current-root',str(self.f.roots[1]),'--format','html']
        outputs=[]
        for seed in ('1','99'):
            p=subprocess.run(args,capture_output=True,env=dict(os.environ,PYTHONHASHSEED=seed),timeout=30)
            self.assertEqual((p.returncode,p.stderr),(0,b''));outputs.append(p.stdout)
        self.assertEqual(*outputs);self.passive(outputs[0].decode())
        out=Path(self.f.tmp.name)/'comparison.html'
        p=subprocess.run(args+['--output',str(out)],capture_output=True,timeout=30)
        self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(out.read_bytes(),outputs[0]);self.assertEqual(json.loads(p.stdout)['status'],'SAVED')
        again=subprocess.run(args+['--output',str(out)],capture_output=True,timeout=30)
        self.assertEqual((again.returncode,again.stdout),(1,b''));self.assertEqual(out.read_bytes(),outputs[0])
        paths[1].write_bytes(json.dumps(snapshot(outputs[0].decode())).encode())
        bad=subprocess.run(args,capture_output=True,timeout=30);self.assertEqual((bad.returncode,bad.stdout),(1,b''))

    def test_synthetic_guide_actual_commands(self):
        guide=(ROOT/'docs/JOURNEY_COMPARISON_HTML.md').read_text()
        blocks=re.findall(r'```sh\n(.*?)```',guide,re.S);self.assertEqual(len(blocks),1)
        lines=blocks[0].splitlines();self.assertEqual(len(lines),3)
        with tempfile.TemporaryDirectory(prefix='comparison guide space ') as td:
            root=Path(td).resolve();mapping={name:str(root/name.split('/',1)[1]) for name in ('OUTPUT/demo','OUTPUT/card.json','OUTPUT/demo/synthetic-sources','OUTPUT/comparison.html')}
            mapping['examples/synthetic-journey-inputs.json']=str(ROOT/'examples/synthetic-journey-inputs.json')
            for line in lines:
                tokens=shlex.split(line);self.assertEqual(tokens[0],'python');self.assertIn(tokens[1],('synthetic_walkthrough.py','journey_inputs.py','journey_compare.py'))
                args=[sys.executable,str(ROOT/tokens[1]),*[mapping.get(t,t) for t in tokens[2:]]]
                p=subprocess.run(args,cwd=ROOT,capture_output=True,timeout=90);self.assertEqual(p.returncode,0,p.stderr)
            text=(root/'comparison.html').read_text();self.passive(text);r=snapshot(text)
            self.assertFalse(r['logical_journey_inputs_changed']);self.assertFalse(r['automatic_approval'])
            self.assertEqual(r['previous_report'],r['current_report'])

if __name__=='__main__':unittest.main()
