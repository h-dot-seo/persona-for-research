import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import regenerate_manifest as generator
from audit_publication import audit
from verify_manifest import verify, inventory, file_digest


class RegenerationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'selected tree'
        self.root.mkdir()
        (self.root / 'a.txt').write_bytes('synthetic 한글\n'.encode())
        self.output = self.base / 'new.json'
        self.manifest = dict(project='synthetic', release='0.1-old', date='2026-01-01',
                             private_history_imported=False, actual_corpora_included=False,
                             synthetic_examples_only=True, license_status='Undecided',
                             file_count=1, files=[self.row('a.txt')])
        self.save()

    def row(self, name):
        raw = (self.root/name).read_bytes()
        return dict(path=name, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())

    def save(self):
        self.original = (json.dumps(self.manifest, indent=2)+'\n').encode()
        (self.root/'PUBLICATION_MANIFEST.json').write_bytes(self.original)

    def run_gen(self, **kwargs):
        return generator.regenerate(self.root, release='0.2-new', date='2026-11-14',
                                    output=self.output, **kwargs)

    def test_deterministic_raw_bytes_and_preserved_declarations(self):
        result = self.run_gen()
        generated = self.output.read_bytes()
        expected = copy.deepcopy(self.manifest)
        expected['release'], expected['date'] = '0.2-new', '2026-11-14'
        self.assertEqual(generated, (json.dumps(expected,indent=2)+'\n').encode())
        self.assertEqual(result['rehashed'], ['a.txt'])
        self.assertEqual(result['changed'], [])
        self.assertEqual(result['sha256'], hashlib.sha256(generated).hexdigest())
        self.assertEqual((self.root/'PUBLICATION_MANIFEST.json').read_bytes(),self.original)
        self.output = self.base/'another.json'
        self.run_gen()
        self.assertEqual(self.output.read_bytes(),generated)
        # Explicit human replacement in a synthetic fixture only.
        (self.root/'PUBLICATION_MANIFEST.json').write_bytes(generated)
        self.assertEqual(verify(self.root),[])
        self.assertTrue(audit(self.root)['pass'])

    def test_rehash_and_explicit_add_remove(self):
        (self.root/'a.txt').unlink()
        (self.root/'z.txt').write_bytes(b'synthetic\n')
        with self.assertRaisesRegex(ValueError, 'missing.*a.txt.*unlisted.*z.txt'):
            self.run_gen()
        self.assertFalse(self.output.exists())
        result=self.run_gen(add=['z.txt'],remove=['a.txt'])
        self.assertEqual(result['added'],['z.txt']);self.assertEqual(result['removed'],['a.txt'])
        self.assertEqual(json.loads(self.output.read_bytes())['files'],[self.row('z.txt')])

    def test_changed_bytes_and_sorted_inventory(self):
        (self.root/'a.txt').write_bytes(b'changed\n')
        (self.root/'0.txt').write_bytes(b'new\n')
        result=self.run_gen(add=['0.txt'])
        self.assertEqual(result['changed'],['a.txt'])
        self.assertEqual([r['path'] for r in json.loads(self.output.read_bytes())['files']],['0.txt','a.txt'])

    def test_add_remove_validation_no_output(self):
        for args in [dict(add=['a.txt']),dict(remove=['missing']),dict(add=['x','x']),
                     dict(add=['x'],remove=['x']),dict(add=['../outside']),
                     dict(add=['.git/config']),dict(add=['__pycache__/x']),
                     dict(add=['PUBLICATION_MANIFEST.json']),dict(remove=['a.txt'])]:
            with self.subTest(args=args), self.assertRaises(ValueError):self.run_gen(**args)
            self.assertFalse(self.output.exists())

    def test_cr_and_audit_rejection(self):
        for raw in [b'synthetic\r\n',b'contact synthetic'+b'@'+b'example.invalid\n']:
            (self.root/'a.txt').write_bytes(raw)
            with self.assertRaises(ValueError):self.run_gen()
            self.assertFalse(self.output.exists())

    def test_metadata_full_serialization_scan_and_validation(self):
        for name,value in [('release','0.2-BAD'),('release','../../x'),('date','2026-02-30'),
                           ('date','2026-2-01')]:
            kwargs=dict(release='0.2-new',date='2026-11-14');kwargs[name]=value
            with self.subTest(name=name,value=value),self.assertRaises(ValueError):
                generator.regenerate(self.root,output=self.output,**kwargs)
            self.assertFalse(self.output.exists())
        self.manifest['license_status']='contact synthetic'+'@'+'example.invalid'
        self.save()
        with self.assertRaisesRegex(ValueError,'pattern scan'):self.run_gen()
        self.assertFalse(self.output.exists())
        self.manifest['license_status']='Undecided'
        self.manifest['extra']={'note':'Bearer '+'a'*30};self.save()
        with self.assertRaisesRegex(ValueError,'pattern scan'):self.run_gen()

    def test_invalid_old_rows_and_declared_flags(self):
        original=copy.deepcopy(self.manifest)
        for mutate in [lambda m:m.update(file_count=2),lambda m:m.update(synthetic_examples_only='yes'),
                       lambda m:m['files'].append(m['files'][0]),
                       lambda m:m['files'][0].update(path='../outside'),
                       lambda m:m['files'][0].update(sha256='bad')]:
            self.manifest=copy.deepcopy(original);mutate(self.manifest);self.save()
            with self.assertRaises(ValueError):self.run_gen()
            self.assertFalse(self.output.exists())

    def test_output_preflight_and_exclusive_collision(self):
        for output in [self.root/'new.json',self.root/'PUBLICATION_MANIFEST.json',
                       self.base/'missing'/'new.json',generator.ROOT/'new.json']:
            with self.subTest(output=output),self.assertRaises(ValueError):
                generator.regenerate(self.root,release='0.2-new',date='2026-11-14',output=output)
        self.output.write_bytes(b'keep')
        with self.assertRaisesRegex(ValueError,'already exists'):self.run_gen()
        self.assertEqual(self.output.read_bytes(),b'keep')

    def test_symlink_inputs_outputs_and_parents_rejected(self):
        real=self.root/'a.txt';link=self.root/'link.txt'
        try:link.symlink_to(real)
        except (OSError,NotImplementedError):self.skipTest('symlinks unavailable')
        with self.assertRaisesRegex(ValueError,'symlink'):self.run_gen(add=['link.txt'])
        link.unlink()
        outlink=self.base/'outlink';outlink.symlink_to(self.base,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'symlink'):
            generator.regenerate(self.root,release='0.2-new',date='2026-11-14',output=outlink/'new.json')
        self.output.symlink_to(self.base/'missing')
        with self.assertRaisesRegex(ValueError,'symlink'):self.run_gen()

    def test_stale_files_manifest_and_inventory_rejected_before_output(self):
        real_audit=generator.audit
        for what in ('bytes','manifest','inventory'):
            def changing(root):
                result=real_audit(root)
                if what=='bytes':(root/'a.txt').write_bytes(b'late\n')
                elif what=='manifest':(root/'PUBLICATION_MANIFEST.json').write_bytes(self.original+b' ')
                else:(root/'extra.txt').write_bytes(b'late')
                return result
            with self.subTest(what=what),patch.object(generator,'audit',side_effect=changing):
                with self.assertRaisesRegex(ValueError,'changed during generation'):self.run_gen()
            self.assertFalse(self.output.exists())
            (self.root/'a.txt').write_bytes('synthetic 한글\n'.encode());self.save()
            (self.root/'extra.txt').unlink(missing_ok=True)

    def test_target_code_is_data_and_summary_has_no_absolute_paths(self):
        script=self.root/'regenerate_manifest.py';script.write_bytes(b'raise RuntimeError("MUST_NOT_EXECUTE")\n')
        command=[sys.executable,str(generator.ROOT/'regenerate_manifest.py'),str(self.root),
                 '--release','0.2-new','--date','2026-11-14','--add',script.name,'--output',str(self.output)]
        result=subprocess.run(command,cwd=self.root,capture_output=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr)
        summary=json.loads(result.stdout)
        self.assertIn('not content review',summary['boundary'])
        self.assertNotIn(str(self.base),result.stdout.decode())
        again=subprocess.run(command,cwd=self.root,capture_output=True,timeout=30)
        self.assertNotEqual(again.returncode,0);self.assertEqual(again.stdout,b'')
        self.assertNotIn(b'Traceback',again.stderr)

    def test_shared_inventory_and_digest_are_exact(self):
        actual,errors,enumerated=inventory(self.root)
        self.assertTrue(enumerated);self.assertEqual(errors,[]);self.assertEqual(actual,{'a.txt','PUBLICATION_MANIFEST.json'})
        raw=b'a\r\nb';self.assertEqual(file_digest(raw),(len(raw),hashlib.sha256(raw).hexdigest()))


if __name__=='__main__':unittest.main()
