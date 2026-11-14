"""Comparator-only source read is opt-in, bounded and separate from knowledge."""
import copy,hashlib,io,json,os,re,shlex,stat,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import comparator_overlap as c
import comparator_sources as s
from persona import payload_sha256
ROOT=Path(__file__).resolve().parents[1]

class ComparatorSourceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.raw=b'## synthetic section\r\nSynthetic comparator passage.\n'
        (self.root/'paper.md').write_bytes(self.raw)
        self.p=json.loads((ROOT/'examples/trajectory-conditions-package.json').read_bytes())
        self.c=json.loads((ROOT/'examples/synthetic-comparator-source-corpus.json').read_bytes())
        self.c['papers'][0]['source_sha256']=hashlib.sha256(self.raw).hexdigest()
        self.m=json.loads((ROOT/'examples/synthetic-comparator-source-selection.json').read_bytes());self.bind()
        self.topic='synthetic method conditions'
    def bind(self):self.m['comparator_corpus_sha256']=payload_sha256(self.c)
    def call(self):return s.inspect_sources(self.p,self.c,self.topic,self.m,self.root)
    def test_match_all_four_quote_states_and_empty_observations(self):
        obs=self.c['papers'][0]['observations'][0]
        self.c['papers'][0]['observations']=[dict(obs,evidence_quote=q,locator=l) for q,l in [('Synthetic comparator passage.','synthetic section'),(None,'absent'),('x','absent'),('not found','synthetic section')]];self.bind()
        before=copy.deepcopy((self.p,self.c,self.m));r=self.call();self.assertEqual((self.p,self.c,self.m),before)
        self.assertEqual([x['quote_status'] for x in r['comparator_source_recheck']['papers'][0]['records']],[s.MATCH,'STORED_QUOTE_MISSING','LOCATOR_NOT_FOUND','STORED_QUOTE_NOT_FOUND_AT_LOCATOR'])
        self.assertNotIn('Synthetic comparator passage.',json.dumps(r['comparator_source_recheck']))
        self.assertEqual(r['comparator_source_recheck']['target_source_check'],'NOT_PERFORMED')
        base=c.inspect(self.p,self.c,self.topic);r.pop('comparator_source_recheck');r['source_check']='NOT_PERFORMED';r['boundary']=base['boundary'];self.assertEqual(r,base)
        self.c['papers'][0]['observations']=[];self.bind();r=self.call()['comparator_source_recheck'];self.assertEqual(r['source_bytes_read'],len(self.raw));self.assertEqual(r['papers'][0]['status'],'NO_STORED_QUOTES_TO_CHECK')
    def test_mapping_all_keys_and_stale_precede_reads(self):
        original=copy.deepcopy(self.m)
        for path in [(),('sources',0)]:
            obj=original
            for k in path:obj=obj[k]
            for key in [*obj,'unknown']:
                self.m=copy.deepcopy(original);o=self.m
                for k in path:o=o[k]
                if key=='unknown':o[key]=True
                else:o.pop(key)
                with patch.object(s,'read_source_bytes',side_effect=AssertionError('read')),self.assertRaises(ValueError):self.call()
        for change in [dict(comparator_corpus_sha256='0'*64),dict(sources=[]),dict(sources=original['sources']*2),dict(sources=[dict(paper_id='unknown',source_file='paper.md')])]:
            self.m=dict(original,**change)
            with patch.object(s,'_checked_path',side_effect=AssertionError('path')),self.assertRaises(ValueError):self.call()
    def test_path_preflight_and_hash_no_partial_report(self):
        for name in ['../x.md','/x.md','C:x.md','x\\y.md','./paper.md','x//y.md','x\n.md','x.pdf','missing.md']:
            self.m['sources'][0]['source_file']=name
            with patch.object(s,'read_source_bytes',side_effect=AssertionError('read')),self.assertRaises((ValueError,OSError)):self.call()
        self.m['sources'][0]['source_file']='paper.md';(self.root/'paper.md').write_bytes(self.raw+b'change')
        with self.assertRaisesRegex(ValueError,'hash mismatch'):self.call()
    def test_symlink_fifo_and_reparse(self):
        link=self.root/'link.md'
        try:link.symlink_to(self.root/'paper.md')
        except OSError:pass
        else:
            self.m['sources'][0]['source_file']='link.md'
            with patch.object(s,'read_source_bytes',side_effect=AssertionError('read')),self.assertRaises(ValueError):self.call()
        if hasattr(os,'mkfifo'):
            os.mkfifo(self.root/'fifo.md');self.m['sources'][0]['source_file']='fifo.md'
            with patch.object(s,'read_source_bytes',side_effect=AssertionError('read')),self.assertRaises(ValueError):self.call()
        self.m['sources'][0]['source_file']='paper.md';target=(self.root/'paper.md').resolve();original=Path.stat;hits=[]
        def stat_fake(path,*a,**kw):
            info=original(path,*a,**kw)
            if path==target and kw.get('follow_symlinks') is False:
                hits.append(True)
                class Proxy:
                    st_file_attributes=0x400
                    def __getattr__(self,key):return getattr(info,key)
                return Proxy()
            return info
        with patch.object(Path,'stat',stat_fake),self.assertRaises(ValueError):self.call()
        self.assertTrue(hits)
    def test_remaining_budget_counts_each_duplicate_file_and_identity_check(self):
        p=copy.deepcopy(self.c['papers'][0]);p['paper_id']='synthetic-second';self.c['papers'].append(p);self.m['sources'].append(dict(paper_id=p['paper_id'],source_file='paper.md'));self.bind()
        with patch.object(s,'MAX_SOURCE_BYTES',2*len(self.raw)):self.assertEqual(self.call()['comparator_source_recheck']['source_bytes_read'],2*len(self.raw))
        with patch.object(s,'MAX_SOURCE_BYTES',2*len(self.raw)-1),self.assertRaises(ValueError):self.call()
        original=s.read_source_bytes
        def replaced(path,**kw):
            path.unlink();path.mkdir();return original(path,**kw)
        with patch.object(s,'read_source_bytes',replaced),self.assertRaises((ValueError,OSError)):self.call()
    def test_cli_pair_errors_budgets_and_output(self):
        a=self.root/'a.json';b=self.root/'b.json';m=self.root/'map.json'
        for p,v in [(a,self.p),(b,self.c),(m,self.m)]:p.write_bytes(json.dumps(v).encode())
        argv=['comparator_overlap.py',str(a),str(b),'--topic',self.topic,'--source-selection',str(m),'--source-root',str(self.root)]
        class Output:
            def __init__(self):self.buffer=io.BytesIO()
        for budget in [1,sum(p.stat().st_size for p in (a,b,m))-1]:
            out=Output()
            with patch.object(sys,'argv',argv),patch.object(sys,'stdout',out),patch.object(sys,'stderr',io.StringIO()),patch.object(c,'MAX_INPUT_BYTES',budget),self.assertRaises(SystemExit):c.main()
            self.assertEqual(out.buffer.getvalue(),b'')
        out=Output()
        with patch.object(sys,'argv',argv),patch.object(sys,'stdout',out),patch.object(sys,'stderr',io.StringIO()),patch.object(c,'MAX_OUTPUT_BYTES',1),self.assertRaises(SystemExit):c.main()
        self.assertEqual(out.buffer.getvalue(),b'')
        with patch.object(sys,'argv',argv[:-2]),patch.object(c,'read_bounded',side_effect=AssertionError('read')),patch.object(sys,'stderr',io.StringIO()),self.assertRaises(SystemExit) as ex:c.main()
        self.assertEqual(ex.exception.code,2)
    def test_explicit_null_mapping_and_later_invalid_path_precede_reads(self):
        with patch.object(s,'_checked_path',side_effect=AssertionError('path')),self.assertRaises(ValueError):
            s.inspect_sources(self.p,self.c,self.topic,None,self.root)
        second=copy.deepcopy(self.c['papers'][0]);second['paper_id']='synthetic-later'
        self.c['papers'].append(second);self.m['sources'].append(dict(paper_id='synthetic-later',source_file='missing.md'));self.bind()
        with patch.object(s,'read_source_bytes',side_effect=AssertionError('read')),self.assertRaises(OSError):self.call()

    @unittest.skipUnless(os.name=='nt','Windows junction/short-name checks require Windows')
    def test_windows_junction_and_available_short_root_alias(self):
        actual=self.root/'actual';actual.mkdir();(actual/'paper.md').write_bytes(self.raw)
        junction=self.root/'junction'
        p=subprocess.run(['cmd','/c','mklink','/J',str(junction),str(actual)],capture_output=True)
        if p.returncode:self.skipTest('junction creation unavailable')
        self.addCleanup(lambda: os.rmdir(junction) if junction.exists() else None)
        self.m['sources'][0]['source_file']='junction/paper.md'
        with patch.object(s,'read_source_bytes',side_effect=AssertionError('read')),self.assertRaises(ValueError):self.call()
        import ctypes
        buf=ctypes.create_unicode_buffer(32768)
        n=ctypes.windll.kernel32.GetShortPathNameW(str(self.root),buf,len(buf))
        if n and n<len(buf):
            self.m['sources'][0]['source_file']='paper.md'
            self.assertEqual(s.inspect_sources(self.p,self.c,self.topic,self.m,Path(buf.value)),self.call())

    def test_frozen_prior_default_cli_bytes(self):
        expected={'json':'2e7cdc15cc5979a3f54ef2d20dcac1e3a07ac4779c6d24d1b44927d75351db28','text':'dcfd12e4a02f2faedbf747b73f0f6c682ae0f8755bc0667cbf1affd94a2075b6'}
        # Captured from actual round41 raw stdout; stdout.buffer keeps LF on Windows.
        for fmt,digest in expected.items():
            p=subprocess.run([sys.executable,str(ROOT/'comparator_overlap.py'),str(ROOT/'examples/trajectory-conditions-package.json'),str(ROOT/'examples/synthetic-comparator-corpus.json'),'--topic',self.topic,'--format',fmt],capture_output=True)
            self.assertEqual((p.returncode,p.stderr),(0,b''));self.assertEqual(hashlib.sha256(p.stdout).hexdigest(),digest)

    def test_guide(self):
        doc=(ROOT/'docs/COMPARATOR_SOURCES.md').read_text();blocks=re.findall(r'```sh\n(.*?)```',doc,re.S)
        self.assertEqual(len(blocks),1)
        for line in blocks[0].splitlines():
            if not line:continue
            args=shlex.split(line)[1:]
            args=[str(ROOT/x) if x=='comparator_overlap.py' or x.startswith('examples/') else x for x in args]
            p=subprocess.run([sys.executable,*args],capture_output=True,cwd=ROOT)
            self.assertEqual((p.returncode,p.stderr),(0,b''));self.assertEqual(json.loads(p.stdout)['source_check'],'COMPARATOR_ONLY_RECHECK_PERFORMED')

if __name__=='__main__':unittest.main()
