"""Opt-in detail lines disclose only closed static keys and parser argument labels."""
import copy,io,json,os,re,shlex,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import curate_local as curate
import revise_local as revise
import rejection_details as detail
from tests import test_curate_local as fixtures
ROOT=Path(__file__).resolve().parents[1]

class RejectionDetailTests(unittest.TestCase):
    def setUp(self):
        f=fixtures.ManualObservationTests();f.setUp();self.m=f.manifest;self.card=f.card();self.root=f.root
        self.ap=curate.append_observation(self.m,self.card,self.root)
        self.rev=revise.template(self.ap,'synthetic-0',0);self.rev.update(operator_id='synthetic',revision_reason='synthetic',new_version='new',new_build_id='new')
        self.rev['observation']['method']+=' revised'
    def test_static_contracts_and_original_exception_text(self):
        self.assertEqual(detail.CONTRACTS['manual-observation'][0],curate.REQUIRED)
        self.assertEqual(detail.CONTRACTS['append-card'][0],set(self.card))
        self.assertEqual(detail.CONTRACTS['revision-card'][0],set(self.rev))
        for contract,(required,optional) in detail.CONTRACTS.items():
            for key in required:
                value={k:None for k in required-{key}};value['PRIVATE\x1b\nHOLDOUT-ID']='PRIVATEVALUE'
                exc=detail.closed_rejection('original',value,contract,'card')
                self.assertIsInstance(exc,ValueError);self.assertEqual(str(exc),'original');self.assertEqual(exc.args,('original',))
                self.assertIn(detail._key_diagnostic(key),exc.detail);self.assertIn('unsupported_count=1',exc.detail)
                self.assertNotIn('PRIVATE',exc.detail);self.assertNotIn('HOLDOUT',exc.detail)
                self.assertTrue(exc.detail.isascii());self.assertLessEqual(len(exc.detail),512)
        value={'private'+str(i):None for i in range(10001)}
        exc=detail.closed_rejection('original',value,'revision-card','card')
        self.assertIn('unsupported_count=9999+',exc.detail);self.assertIn('additional_missing=2',exc.detail)
    def test_wrong_type_enum_and_nonstr_keys_have_no_invented_detail(self):
        for value in (None,[],1,{1:'private'}):
            self.assertIs(type(detail.closed_rejection('original',value,'append-card','card')),ValueError)
        card=dict(self.card,schema='bad')
        with self.assertRaises(ValueError) as ex:curate.append_observation(self.m,card,self.root)
        self.assertFalse(hasattr(ex.exception,'detail'))
        card=copy.deepcopy(self.card);card['observation']['stance']='PRIVATE-ENUM'
        with self.assertRaises(ValueError) as ex:curate.append_observation(self.m,card,self.root)
        self.assertEqual(str(ex.exception),'choose support or challenge explicitly');self.assertFalse(hasattr(ex.exception,'detail'))
    def test_manifest_vs_card_metadata_and_no_extra_validation_read(self):
        card=copy.deepcopy(self.card);del card['observation']['method']
        with patch.object(curate,'_paper',wraps=curate._paper) as paper,patch.object(curate,'load_sources',side_effect=AssertionError('read')):
            with self.assertRaises(detail.InputRejected) as ex:curate.append_observation(self.m,card,self.root)
        self.assertEqual(paper.call_count,1);self.assertIn('input=card',ex.exception.detail)
        # Old observation validation is unambiguously manifest, not card.
        bad=copy.deepcopy(self.ap);bad['papers'][0]['observations'][0]['stance']='support'
        del bad['papers'][0]['observations'][0]['stance']
        with self.assertRaises(detail.InputRejected) as ex:revise.template(bad,'synthetic-0',0)
        self.assertIn('input=manifest',ex.exception.detail)
        # Direct shared validator remains plain ValueError unless attribution is explicitly supplied.
        with self.assertRaises(ValueError) as ex:curate.validate_manual_observation({})
        self.assertIs(type(ex.exception),ValueError)
    def test_nested_components_and_missing_stance(self):
        for key in ('text','locator','evidence_quote','claim_type'):
            card=copy.deepcopy(self.card);component=dict(text='x',locator='x',evidence_quote='x',claim_type='operator_interpretation');del component[key]
            card['observation']['reasoning']={'uncertainty':component}
            with self.assertRaises(detail.InputRejected) as ex:curate.append_observation(self.m,card,self.root)
            self.assertIn(detail._key_diagnostic(key),ex.exception.detail)
        card=copy.deepcopy(self.card);del card['observation']['stance']
        with self.assertRaises(detail.InputRejected) as ex:curate.append_observation(self.m,card,self.root)
        self.assertEqual(str(ex.exception),'choose support or challenge explicitly')
    def test_loader_labels_only_for_valueerrors_not_oserrors(self):
        def fail(path):raise ValueError('old private original')
        with self.assertRaises(detail.InputRejected) as ex:detail.load_input(fail,'private-path','manifest',True)
        self.assertEqual(ex.exception.detail,'  input=manifest');self.assertEqual(str(ex.exception),'old private original')
        with self.assertRaises(ValueError) as ex:detail.load_input(fail,'private-path','manifest',False)
        self.assertIs(type(ex.exception),ValueError)
        def osfail(path):raise OSError('original path')
        with self.assertRaises(OSError):detail.load_input(osfail,'private','card',True)
    def test_actual_cli_exact_native_stderr_and_dispatcher(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td);mp=d/'manifest.json';cp=d/'card.json';mp.write_bytes(json.dumps(self.m).encode());cp.write_bytes(b'{}')
            args=['curate_local.py','append',str(mp),str(cp),'--source-root',str(self.root)]
            def run(args):return subprocess.run([sys.executable,*args],cwd=ROOT,capture_output=True)
            default=run(args);enabled=run(args+['--explain-rejection'])
            first=('manual observation card has missing or unsupported fields'+os.linesep).encode()
            self.assertEqual((default.returncode,default.stdout,default.stderr),(1,b'',first))
            self.assertEqual(enabled.returncode,1);self.assertEqual(enabled.stdout,b'');self.assertTrue(enabled.stderr.startswith(first))
            self.assertEqual(len(enabled.stderr.splitlines()),2);self.assertNotIn(str(d).encode(),enabled.stderr)
            dispatched=run(['persona_cli.py','run',*args,'--explain-rejection'])
            self.assertEqual((dispatched.returncode,dispatched.stdout,dispatched.stderr),(enabled.returncode,enabled.stdout,enabled.stderr))
            mp.write_bytes(json.dumps(self.ap).encode())
            args=['revise_local.py','apply',str(mp),str(cp),str(d/'new'),'--source-root',str(self.root)]
            default=run(args);enabled=run(args+['--explain-rejection'])
            self.assertEqual(default.stderr,('revision card has missing or unsupported fields'+os.linesep).encode());self.assertEqual(default.returncode,1)
            self.assertEqual(enabled.stdout,b'');self.assertTrue(enabled.stderr.startswith(default.stderr));self.assertFalse((d/'new').exists())
            self.assertEqual(len(enabled.stderr.splitlines()),2)
    def test_success_and_cross_binding_do_not_gain_detail(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td);mp=d/'m.json';cp=d/'c.json';mp.write_bytes(json.dumps(self.m).encode());cp.write_bytes(json.dumps(self.card).encode())
            args=[sys.executable,str(ROOT/'curate_local.py'),'append',str(mp),str(cp),'--source-root',str(self.root)]
            a=subprocess.run(args,capture_output=True);b=subprocess.run(args+['--explain-rejection'],capture_output=True)
            self.assertEqual((a.returncode,a.stdout,a.stderr),(b.returncode,b.stdout,b.stderr));self.assertEqual(a.returncode,0)
            self.card['manifest_sha256']='0'*64;cp.write_bytes(json.dumps(self.card).encode())
            a=subprocess.run(args,capture_output=True);b=subprocess.run(args+['--explain-rejection'],capture_output=True)
            self.assertEqual((a.returncode,a.stdout,a.stderr),(b.returncode,b.stdout,b.stderr));self.assertEqual(a.returncode,1)
    def test_actual_documented_rejection_examples(self):
        blocks=re.findall(r'```sh\n(.*?)```',(ROOT/'docs/MANUAL_REJECTION_DETAILS.md').read_text(),re.S)
        self.assertEqual(len(blocks),1)
        with tempfile.TemporaryDirectory() as td:
            for line in blocks[0].splitlines():
                if not line:continue
                args=shlex.split(line)[1:]
                args=[str(Path(td)/'new output') if x=='OUTPUT' else str(ROOT/x) if x.endswith('.py') or x.startswith('examples/') else x for x in args]
                p=subprocess.run([sys.executable,*args],capture_output=True,cwd=ROOT)
                self.assertEqual((p.returncode,p.stdout),(1,b''));self.assertEqual(len(p.stderr.splitlines()),2)
                self.assertIn(b'  input=card;',p.stderr);self.assertFalse((Path(td)/'new output').exists())

    def test_argparse_exit2_is_not_decorated(self):
        for script,command in [('curate_local.py','append'),('revise_local.py','apply')]:
            p=subprocess.run([sys.executable,str(ROOT/script),command,'--explain-rejection'],capture_output=True)
            self.assertEqual(p.returncode,2);self.assertEqual(p.stdout,b'');self.assertNotIn(b'  input=',p.stderr)

if __name__=='__main__':unittest.main()
