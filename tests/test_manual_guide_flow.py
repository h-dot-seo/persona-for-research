"""Execute four existing manual-guide blocks, not arbitrary shell or every guide block."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from persona import payload_sha256, validate
from curate_local import append_observation
from revise_local import revise

ROOT=Path(__file__).resolve().parents[1]
GUIDES=('MANUAL_LOCAL_OBSERVATIONS.md','MANUAL_EVIDENCE_REVISION.md')
SCRATCH=('manual-prepared.json','manual-research.json','manual-complete.json','manual-result.json',
         'my-observation.json','manual-reassessed','manual-reassessed/manifest.json',
         'manual-reassessed-result.json','reassessed-review','my-revision-card.json')
SCRIPTS={'prepare_local_manifest.py','curate_local.py','corpus_files.py','revise_local.py','review_workspace.py'}
EXAMPLES=('examples/local-selection.json','examples/synthetic-sources','examples/manual-research-card.json',
          'examples/manual-review-card.json','examples/manual-revision-card.json')


def command(line,destination):
    """Only this pair of guides: token mapping after shlex, one final raw capture."""
    tokens=shlex.split(line)
    if len(tokens)<2 or tokens[0]!='python' or tokens[1] not in SCRIPTS:raise ValueError('unexpected manual-guide command')
    output=None
    if '>' in tokens:
        if tokens.count('>')!=1 or len(tokens)<4 or tokens[-2]!='>':raise ValueError('only one trailing capture supported')
        output=tokens[-1];tokens=tokens[:-2]
        if output not in {'../'+name for name in SCRATCH}:raise ValueError('unregistered capture path')
    if any(x in ('>','>>','<','|','||','&&',';') or '$' in x for x in tokens):raise ValueError('shell syntax is not supported')
    mapping={'../'+name:str(destination/name) for name in SCRATCH}
    mapping.update({name:str(ROOT/name) for name in EXAMPLES})
    for token in tokens:
        if token.startswith('../') and token not in mapping:raise ValueError('unregistered scratch path')
    args=[sys.executable,str(ROOT/tokens[1]),*[mapping.get(x,x) for x in tokens[2:]]]
    return args,Path(mapping[output]) if output else None


class ManualGuideFlowTests(unittest.TestCase):
    def test_four_blocks_nine_commands_form_one_manual_flow(self):
        source=ROOT/'examples/synthetic-sources'
        protected=[ROOT/'docs'/name for name in GUIDES]+[ROOT/name for name in EXAMPLES if (ROOT/name).is_file()]+[p for p in source.iterdir() if p.is_file()]
        original={p:p.read_bytes() for p in protected}
        blocks={name:re.findall(rb'```sh\r?\n(.*?)```',original[ROOT/'docs'/name],re.S) for name in GUIDES}
        self.assertEqual([len(blocks[name]) for name in GUIDES],[3,3])
        # Explicit exclusions: unittest invocations are already independent suite tests.
        for name,module in zip(GUIDES,('tests.test_curate_local','tests.test_revise_local')):
            self.assertEqual(shlex.split(blocks[name][2].decode().strip()),['python','-m','unittest',module,'-v'])
        registry=json.loads((ROOT/'tests/doc_block_evidence.json').read_bytes())
        owned=[row for row in registry if row['path'] in {'docs/'+n for n in GUIDES}]
        self.assertEqual({(x['path'],x['ordinal']) for x in owned},{('docs/'+n,i) for n in GUIDES for i in (1,2)})
        for row in owned:self.assertEqual(row['raw_sha256'],hashlib.sha256(blocks[Path(row['path']).name][row['ordinal']-1]).hexdigest())
        count=0;previous={};captures={}
        with tempfile.TemporaryDirectory(prefix='manual guide space ') as td:
            out=Path(td)
            for name in GUIDES:
                for block in blocks[name][:2]:
                    for line in block.decode('utf-8').splitlines():
                        if not line.strip():continue
                        args,capture=command(line,out)
                        result=subprocess.run(args,cwd=ROOT,capture_output=True,timeout=30)
                        self.assertEqual((result.returncode,result.stderr),(0,b''),line)
                        self.assertEqual(previous,{p:p.read_bytes() for p in previous},line)
                        if capture is not None:
                            self.assertFalse(capture.exists())
                            # Raw stdout.buffer bytes, never text=True or shell re-encoding.
                            with capture.open('xb') as stream:stream.write(result.stdout)
                            self.assertEqual(capture.read_bytes(),result.stdout)
                            self.assertNotIn(b'\r',result.stdout);self.assertTrue(result.stdout.endswith(b'\n'))
                            captures[capture.name]=result.stdout
                        previous={p:p.read_bytes() for p in out.rglob('*') if p.is_file()}
                        count+=1
            self.assertEqual(count,9)
            read=lambda name:json.loads((out/name).read_bytes())
            prepared=read('manual-prepared.json');complete=read('manual-complete.json')
            self.assertEqual([p['observations'] for p in prepared['papers']],[[],[]])
            observations=[p['observations'][0] for p in complete['papers']]
            self.assertEqual([o['stance'] for o in observations],['support','challenge'])
            self.assertEqual([o['claim_type'] for o in observations],['explicit_statement','operator_interpretation'])
            before=read('manual-result.json')['package'];after=read('manual-reassessed-result.json')['package']
            revised=read('manual-reassessed/manifest.json');audit=read('manual-reassessed/revision-audit.json')
            self.assertNotEqual((complete['version'],complete['build_id']),(revised['version'],revised['build_id']))
            self.assertNotEqual(complete['version'],revised['version']);self.assertNotEqual(complete['build_id'],revised['build_id'])
            self.assertEqual([p['source_sha256'] for p in complete['papers']],[p['source_sha256'] for p in revised['papers']])
            self.assertEqual(complete['papers'][1],revised['papers'][1])
            self.assertEqual(audit['previous_observation'],complete['papers'][0]['observations'][0])
            self.assertEqual(audit['revised_observation'],revised['papers'][0]['observations'][0])
            self.assertEqual(audit['previous_manifest_sha256'],payload_sha256(complete));self.assertEqual(audit['revised_manifest_sha256'],payload_sha256(revised))
            self.assertEqual(audit['status'],'MANUAL_REVISION_REQUIRES_REVIEW')
            self.assertEqual(validate(before['persona'],before['knowledge']),[]);self.assertEqual(validate(after['persona'],after['knowledge']),[])
            self.assertNotEqual(payload_sha256(before['persona']),payload_sha256(after['persona']))
            self.assertEqual(read('reassessed-review/package.json'),after)
            self.assertTrue((out/'manual-reassessed/READY.json').is_file());self.assertTrue((out/'reassessed-review/READY.json').is_file())
            from answer_draft import inspect
            self.assertIsInstance(inspect(after,read('reassessed-review/answer.json')),dict)
            with self.assertRaises(ValueError):inspect(before,read('reassessed-review/answer.json'))
            blank=read('my-observation.json');revision_blank=read('my-revision-card.json')
            self.assertIsNone(blank['observation']['claim_type']);self.assertIsNone(blank['observation']['stance'])
            self.assertEqual(blank['manifest_sha256'],payload_sha256(prepared))
            self.assertTrue(all(revision_blank[k]=='' for k in ('operator_id','revision_reason','new_version','new_build_id')))
            self.assertEqual(revision_blank['manifest_sha256'],payload_sha256(complete))
            with patch('curate_local.load_sources',side_effect=AssertionError('blank must fail before reads')):
                with self.assertRaises(ValueError):append_observation(prepared,blank,source)
            with patch('revise_local.load_sources',side_effect=AssertionError('blank must fail before reads')):
                with self.assertRaises(ValueError):revise(complete,revision_blank,source)
        self.assertEqual(original,{p:p.read_bytes() for p in protected})

    def test_token_mapping_is_not_a_shell_and_preserves_spaces(self):
        out=Path('temporary output with spaces')
        args,target=command('python curate_local.py template ../manual-prepared.json --paper synthetic-0 > ../my-observation.json',out)
        self.assertEqual(args[3],str(out/'manual-prepared.json'));self.assertEqual(target,out/'my-observation.json')
        for line in ('python unknown.py x','python curate_local.py x > ../unknown.json',
                     'python curate_local.py x > ../my-observation.json extra','python curate_local.py x >> ../my-observation.json',
                     'python curate_local.py $PRIVATE','python curate_local.py ../unknown.json','python curate_local.py x | cat'):
            with self.assertRaises(ValueError):command(line,out)

if __name__=='__main__':unittest.main()
