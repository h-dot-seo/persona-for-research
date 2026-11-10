"""Synthetic CLI bytes do not depend on console encoding or newline translation."""
import ast
import copy
import hashlib
import importlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import tests.test_design_chain as chain_fixture
from corpus_files import load_sources
from observation_input import verified_corpus
from persona import payload_sha256
from research_workflow import build


ROOT = Path(__file__).resolve().parents[1]
UNICODE = 'Fictional α/β 한국어 µ'
MODULES = (
    'audit_design_chain', 'audit_design_lineage', 'compare_releases', 'corpus_files',
    'curate_local', 'extraction_adapter', 'observation_input', 'operator_review',
    'research_workflow', 'revise_local',
)
UNESCAPED = {
    'compare_releases', 'corpus_files', 'extraction_adapter', 'observation_input',
    'research_workflow',
}


class CliUtf8OutputTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.cases = []
        self.inputs = []
        self.modules = {name: importlib.import_module(name) for name in MODULES}

        corpus = json.loads((ROOT / 'examples/observed-corpus.json').read_bytes())
        corpus['version'] = UNICODE
        for paper in corpus['papers']:
            paper['segments'] = {'synthetic section 1': UNICODE}
            paper['segments_sha256'] = payload_sha256(paper['segments'])
            observation = paper['observations'][0]
            observation.update(evidence_quote=UNICODE, method=UNICODE, stance='support')
        cp = self.save(corpus)
        question_flags = ['--question', UNICODE, '--topic', 'model design']
        for name, package in (
            ('observation_input', build(verified_corpus(corpus))),
            ('research_workflow', build(corpus)),
        ):
            result = dict(package=package,
                          application=self.modules['research_workflow'].apply(
                              package, UNICODE, 'model design'))
            if name == 'observation_input':
                result['boundary'] = ('Exact quote and supplied segment hash checked; '
                                      'source authenticity and semantic support unverified')
            self.add(name, [cp, *question_flags], result)

        package = build(verified_corpus(corpus))
        pp = self.save(package)
        self.add('compare_releases', [pp, pp],
                 self.modules['compare_releases'].compare(package, package))
        response = [dict(paper_id=corpus['papers'][0]['paper_id'],
                         locator='synthetic section 1', evidence_quote=UNICODE,
                         dimension='uncertainty', candidate_text=UNICODE,
                         proposed_claim_type='operator_interpretation')]
        extractor = self.modules['extraction_adapter']
        bundle = extractor.extract_candidates(corpus, extractor.MockProvider(response))
        self.add('extraction_adapter', [cp, '--mock-response', self.save(response)], bundle)
        operator = self.modules['operator_review']
        bp = self.save(bundle)
        self.add('operator_review', [cp, bp, '--template', '--reviewer-id', UNICODE],
                 operator.review_template(corpus, bundle, UNICODE))
        self.add('operator_review', [cp, bp, '--targets'],
                 operator.target_inventory(corpus, bundle))

        manifest = copy.deepcopy(corpus)
        source_root = self.root / 'sources'
        source_root.mkdir()
        for index, paper in enumerate(manifest['papers']):
            raw = ('## synthetic section 1\n' + UNICODE + '\n').encode('utf-8')
            paper['source_file'] = 'synthetic-' + str(index) + '.md'
            (source_root / paper['source_file']).write_bytes(raw)
            paper['source_sha256'] = hashlib.sha256(raw).hexdigest()
            del paper['segments'], paper['segments_sha256']
        mp = self.save(manifest)
        local_package = build(load_sources(manifest, source_root))
        self.add('corpus_files', [mp, '--source-root', source_root, *question_flags],
                 dict(package=local_package,
                      application=self.modules['research_workflow'].apply(
                          local_package, UNICODE, 'model design'),
                      boundary='Local bytes and quoted sections verified; publication authenticity and semantic support unverified'))
        curator = self.modules['curate_local']
        card = curator.template(manifest, 'synthetic-0')
        self.add('curate_local', ['template', mp, '--paper', 'synthetic-0'], card)
        card['observation'] = copy.deepcopy(manifest['papers'][0]['observations'][0])
        self.add('curate_local', ['append', mp, self.save(card), '--source-root', source_root],
                 curator.append_observation(manifest, card, source_root))
        reviser = self.modules['revise_local']
        revision = reviser.template(manifest, 'synthetic-0', 0)
        self.add('revise_local', ['template', mp, '--paper', 'synthetic-0',
                                 '--observation-index', '0'], revision)
        revision['observation']['limitation'] = UNICODE
        revision.update(operator_id=UNICODE, revision_reason=UNICODE,
                        new_version='2', new_build_id='synthetic-revised')
        _, audit = reviser.revise(manifest, revision, source_root)
        self.add('revise_local', ['apply', mp, self.save(revision), self.root / 'revision',
                                 '--source-root', source_root],
                 {key: audit[key] for key in
                  ('status', 'previous_manifest_sha256', 'revised_manifest_sha256')})

        # Reuse the existing fully bound two-review synthetic fixture, without
        # replacing any builder or validator while exercising each real main().
        chain = chain_fixture.DesignChainTests()
        chain.setUp()
        self.add('audit_design_chain', [self.save(value) for value in
                 (chain.package, chain.links, chain.proposal, chain.chain)], chain.run_audit())
        self.add('audit_design_lineage', [self.save(value) for value in
                 (chain.package, chain.links, chain.proposal,
                  {key: chain.chain['stages'][-1][key] for key in
                   ('original_corpus', 'candidate_bundle', 'operator_review')})],
                 self.modules['audit_design_lineage'].audit(
                     chain.package, chain.links, chain.proposal,
                     {key: chain.chain['stages'][-1][key] for key in
                      ('original_corpus', 'candidate_bundle', 'operator_review')}))
        stage = chain.chain['stages'][0]
        self.add('operator_review', [self.save(stage[key]) for key in
                 ('original_corpus', 'candidate_bundle', 'operator_review')] +
                 ['--new-version', stage['target_version'], '--new-build-id', stage['target_build_id']],
                 operator.prepare_revision(stage['original_corpus'], stage['candidate_bundle'],
                     stage['operator_review'], stage['target_version'], stage['target_build_id']))

    def save(self, value):
        path = self.root / (str(len(self.inputs)) + '.json')
        path.write_bytes((json.dumps(value, ensure_ascii=False) + '\n').encode('utf-8'))
        self.inputs.append(path)
        return path

    def add(self, name, args, expected):
        self.cases.append((name, list(map(str, args)), copy.deepcopy(expected)))

    def expected_bytes(self, name, expected):
        return (json.dumps(expected, ensure_ascii=name not in UNESCAPED, indent=2) + '\n').encode('utf-8')

    def run_main(self, name, args, encoding='ascii', newline='\r\n'):
        raw = io.BytesIO()
        # Explicit CRLF translation also reproduces Windows text stdout on POSIX.
        stream = io.TextIOWrapper(raw, encoding=encoding, newline=newline)
        errors = io.StringIO()
        try:
            with patch.object(sys, 'argv', [name + '.py', *args]), \
                 patch.object(sys, 'stdout', stream), patch.object(sys, 'stderr', errors):
                code = 0
                try:
                    self.modules[name].main()
                except SystemExit as exc:
                    code = exc.code
            stream.flush()
            return code, raw.getvalue(), errors.getvalue()
        finally:
            stream.detach()

    def test_all_ten_clis_and_modes_emit_exact_utf8_lf_bytes(self):
        self.assertEqual({name for name, _, _ in self.cases}, set(MODULES))
        self.assertEqual(len(self.cases), 14)
        before = {path: path.read_bytes() for path in self.inputs}
        for name, args, expected in self.cases:
            with self.subTest(script=name, mode=args[0]):
                code, raw, errors = self.run_main(name, args)
                self.assertEqual((code, errors), (0, ''))
                self.assertEqual(raw, self.expected_bytes(name, expected))
                self.assertEqual(json.loads(raw.decode('utf-8')), expected)
                self.assertTrue(raw.endswith(b'\n'))
                self.assertFalse(raw.endswith(b'\n\n'))
                self.assertNotIn(b'\r', raw)
                self.assertFalse(raw.startswith(b'\xef\xbb\xbf'))
        self.assertEqual(before, {path: path.read_bytes() for path in self.inputs})
        self.assertTrue((self.root / 'revision' / 'READY.json').is_file())

    def test_posix_utf8_output_keeps_existing_json_escaping_and_final_lf(self):
        for name, args, expected in self.cases:
            with self.subTest(script=name, mode=args[0]):
                code, raw, errors = self.run_main(name, args, encoding='utf-8', newline='\n')
                self.assertEqual((code, errors), (0, ''))
                self.assertEqual(raw, self.expected_bytes(name, expected))

    def test_invalid_input_exits_one_without_stdout_or_revision_directory(self):
        bad = self.save({})
        for name, args, _ in self.cases:
            with self.subTest(script=name, mode=args[0]):
                args = args.copy()
                args[1 if name in ('curate_local', 'revise_local') else 0] = str(bad)
                code, raw, errors = self.run_main(name, args)
                self.assertEqual(code, 1)
                self.assertEqual(raw, b'')
                self.assertTrue(errors.endswith('\n'))
                self.assertNotIn('Traceback', errors)
        self.assertFalse((self.root / 'revision').exists())

    def test_real_cli_success_with_greek_korean_micro_under_ascii_encoding(self):
        selected = [(name, args, expected) for name, args, expected in self.cases
                    if name in UNESCAPED or (name == 'revise_local' and args[0] == 'template')]
        self.assertEqual(len(selected), 6)
        for name, args, expected in selected:
            with self.subTest(script=name):
                run = subprocess.run([sys.executable, str(ROOT / (name + '.py')), *args],
                    cwd=ROOT, capture_output=True, timeout=20,
                    env=dict(os.environ, PYTHONIOENCODING='ascii'))
                self.assertEqual((run.returncode, run.stderr), (0, b''))
                # Some builders use sets for dictionary insertion; retain the
                # process's key order while checking its exact serialized bytes.
                decoded = json.loads(run.stdout.decode('utf-8'))
                self.assertEqual(decoded, expected)
                self.assertEqual(run.stdout, self.expected_bytes(name, decoded))
                self.assertIn(UNICODE, json.dumps(decoded, ensure_ascii=False))
                if name in UNESCAPED:
                    self.assertIn(UNICODE.encode('utf-8'), run.stdout)

    def test_each_converted_main_has_one_shared_binary_emitter_and_no_print(self):
        for name in MODULES:
            with self.subTest(script=name):
                tree = ast.parse((ROOT / (name + '.py')).read_text(encoding='utf-8'))
                main = next(node for node in tree.body
                            if isinstance(node, ast.FunctionDef) and node.name == 'main')
                calls = [node for node in ast.walk(main) if isinstance(node, ast.Call)]
                self.assertFalse(any(isinstance(node.func, ast.Name) and node.func.id == 'print'
                                     for node in calls))
                writes = [node for node in calls if isinstance(node.func, ast.Attribute)
                          and node.func.attr == 'write']
                self.assertEqual(writes, [])
                emissions = [node for node in calls if isinstance(node.func, ast.Name)
                             and node.func.id == 'emit']
                self.assertEqual(len(emissions), 1)



if __name__ == '__main__':
    unittest.main()
