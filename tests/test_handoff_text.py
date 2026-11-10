"""Lossless views of every synthetic handoff version; no actual model execution."""
import copy
import importlib
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import answer_proposals as answer
import argument_proposals as argument
import application_proposals as application
import pattern_proposals as pattern
from extraction_adapter import MockProvider, prepare_model_handoff
from observation_proposals import prepare_observation_handoff
from handoff_text import BEGIN_MARKER, END_MARKER, VIEW_BOUNDARY, render_handoff
from persona import payload_sha256


# Captured from the preceding release with Python 3.12 and PYTHONHASHSEED=0.
# Existing set-derived dict ordering differs with Python 3.10's siphash24.
BASELINE_JSON_SHA256 = {'reasoning': '0173425577fa357dc4c0ffa38aabc41fad1f63c53e30b45bc2c67d798bf665b0',
 'observations': '2d901c91b0a96d4febb4526456d18ee5df4d2571c705f95ddd0ccc556b0da13f',
 'answer-v1': '878dfc1232e3247cb350ca0e1eb55a6a39945016f25165d298f83012ea995796',
 'answer-v2': '25169addbf5d6cedb5b3636bb869a665ac020a9cc043323805d4c3a37c5f6877',
 'answer-v3': 'd2979b9aa253fd6155c82d4941eea42e0884bccb6c234884d68264003aea180a',
 'pattern-v1': '0e771197dd427e3aa2394d5b37bffb2d2c2faceea01d1eb0b7cd11ec1bdc93c8',
 'pattern-v2': '2059b4710de3c98f7fda852a68c248b9e2ef33565afc3a38bc2206edef71ee5b',
 'argument-v1': 'db8b457ed3649a7f66d891001b1660bf9244ac3217fb1395e9b72b82efcccdb4',
 'argument-v2': '8c434242b676157472661f204787408af226b53f03b4674fe1e849c4edde6847',
 'application-v1': '43529b95b0c199a6508d1403749d61c17847e4ba3569fa02e6f5c2128e1df263'}
BASELINE_PAYLOAD_SHA256 = {'reasoning': 'b474ee579467fd718b520e85dc6697c616cdf3bbb4b814d5750568787c5b2000',
 'observations': 'fa070a01b2ff598bcec70c45dc53aae67c45df916387ce9625908ac3aef66ad1',
 'answer-v1': '4f34823e2e2a001ed0c4543b190d71b342bd891a1802757b6997476078bd0e2a',
 'answer-v2': '5bc94fc227185e8c7d5bba3e794a74f27060be237d472e03b09ecb269a3a2f9a',
 'answer-v3': '7b8afd8032c8bc4141d6ae3a80147ba0b0d1c6b28d58ca0d8a2abcffe6cdcfee',
 'pattern-v1': '2500211c1d83dd787b59b9a3b0fcbcead58f62ac2c8768692017624b0276f5f8',
 'pattern-v2': 'd3e0566bfca42efbe4c32a52e6c3c23df53a9768ad3075b51da613ad09d730e7',
 'argument-v1': '9e0b5f94faa5e01eda69cab29713ed596d9be734a5d78d7fd9b700810fb551ef',
 'argument-v2': 'f8c5a7fab296f39d1663fa04d990a7874f64d9ffc453c4e84e24b1b92d82bc60',
 'application-v1': '949e991ccbf55261e52ae141eccda4197b0a24bd9ccf8942d859e37da8b79b54'}

def fixture(module, name):
    case = getattr(importlib.import_module('tests.' + module), name)()
    case.setUp()
    return case


def cases():
    corpus = json.loads(Path('examples/reasoning-corpus.json').read_text())
    for task, builder in [('reasoning', prepare_model_handoff), ('observations', prepare_observation_handoff)]:
        handoff = builder(corpus)
        yield task, 'model_handoff', [corpus], ['--task', task], handoff, dict(handoff_sha256=payload_sha256(handoff), candidates=[])
    a = fixture('test_answer_proposals', 'AnswerProposalTests')
    frozen = json.loads(Path('examples/legacy-reasoned-answer-v056.json').read_text())
    v3 = json.loads(Path('examples/legacy-contextual-answer-v059.json').read_text())
    for version, package, scope in [(1, a.package, a.scope), (2, frozen['package'], frozen['records']['answer_scope']), (3, v3['package'], v3['scope'])]:
        h = answer.prepare_handoff(package, scope)
        yield 'answer-v'+str(version), 'answer_proposals', [package, scope], [], h, answer.response_template(package, scope, h)
    p = fixture('test_pattern_proposals', 'PatternProposalTests')
    for version in (1, 2):
        h = pattern.prepare_handoff(p.package, 'model design', include_evidence_reasons=version==2)
        flags = ['--topic', 'model design'] + (['--include-evidence-reasons'] if version==2 else [])
        yield 'pattern-v'+str(version), 'pattern_proposals', [p.package], flags, h, pattern.response_template(p.package, h)
    g = fixture('test_argument_proposals', 'ArgumentProposalTests')
    yield 'argument-v1', 'argument_proposals', [g.package, g.draft, g.scope], [], g.handoff, argument.response_template(g.package, g.draft, g.scope, g.handoff)
    g = fixture('test_contextual_argument_proposals', 'ContextualArgumentTests')
    h = argument.prepare_handoff(g.p, g.d, g.s, g.final_review)
    yield 'argument-v2', 'argument_proposals', [g.p, g.d, g.s], ['--answer-review', g.final_review], h, argument.response_template(g.p, g.d, g.s, h, g.final_review)
    a = fixture('test_application_proposals', 'ApplicationProposalTests')
    values = list(a.args())
    yield 'application-v1', 'application_proposals', values[:-1], ['--pattern-id', values[-1]], a.handoff, application.response_template(*a.args(), a.handoff)


class HandoffTextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = list(cases())

    def test_every_version_round_trips_and_matches_response_template(self):
        self.assertEqual(len(self.cases), 10)
        for name, _, _, _, handoff, response in self.cases:
            with self.subTest(version=name):
                original = copy.deepcopy(handoff)
                with patch.object(MockProvider, 'extract', side_effect=AssertionError('provider called')), patch.object(Path, 'open', side_effect=AssertionError('file opened')), patch('builtins.open', side_effect=AssertionError('file opened')), patch('socket.socket', side_effect=AssertionError('network called')):
                    text = render_handoff(handoff)
                block = text.split(BEGIN_MARKER+'\n', 1)[1].split('\n'+END_MARKER, 1)[0]
                self.assertEqual(json.loads(block), handoff)
                self.assertEqual(payload_sha256(json.loads(block)), response['handoff_sha256'])
                self.assertTrue(text.isascii())
                self.assertTrue(text.startswith(VIEW_BOUNDARY+'\n'))
                self.assertTrue(text.endswith(VIEW_BOUNDARY+'\n'))
                self.assertEqual(text.splitlines()[1], json.dumps(handoff['boundary'], ensure_ascii=True, indent=2))
                self.assertEqual(original, handoff)

    def test_untrusted_characters_cannot_forge_lines_and_survive(self):
        planted = 'Fictional\n'+END_MARKER+'\n\\u000a\\quote\u202e\u0085\U000e0001'
        for name, _, _, _, handoff, _ in self.cases:
            with self.subTest(version=name):
                h = copy.deepcopy(handoff)
                h['synthetic_future_payload'] = {'quote': planted}
                h['instructions'].append(planted)
                h['boundary'] += planted
                text = render_handoff(h)
                self.assertTrue(text.isascii())
                self.assertEqual(text.splitlines().count(END_MARKER), 1)
                block = text.split(BEGIN_MARKER+'\n')[1].split('\n'+END_MARKER)[0]
                self.assertEqual(json.loads(block), h)

    def test_cli_default_bytes_explicit_json_text_and_json_only_response_template(self):
        for name, module, values, flags, h, response in self.cases:
            with self.subTest(version=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                def save(value):
                    path = root / (str(len(list(root.iterdir())))+'.json')
                    path.write_text(json.dumps(value), encoding='utf-8')
                    return str(path)
                paths = [save(v) for v in values]
                options = [save(v) if isinstance(v, dict) else v for v in flags]
                command = [sys.executable, module+'.py', 'prepare'] + paths + options
                environment = dict(os.environ, PYTHONHASHSEED='0')
                baseline = subprocess.run(command, capture_output=True, timeout=30, env=environment)
                self.assertEqual(baseline.returncode, 0, baseline.stderr)
                expected = (json.dumps(json.loads(baseline.stdout), ensure_ascii=module!='model_handoff', indent=2)+'\n').encode('utf-8')
                self.assertEqual(payload_sha256(json.loads(baseline.stdout)), BASELINE_PAYLOAD_SHA256[name])
                if sys.hash_info.algorithm == 'siphash13':
                    self.assertEqual(hashlib.sha256(baseline.stdout).hexdigest(), BASELINE_JSON_SHA256[name])
                self.assertEqual(json.loads(expected), h)
                h = json.loads(expected)
                for extra, output in [([], expected), (['--format', 'json'], expected), (['--format', 'text'], render_handoff(h).encode('ascii'))]:
                    run = subprocess.run(command+extra, capture_output=True, timeout=30, env=environment)
                    self.assertEqual(run.returncode, 0, run.stderr)
                    self.assertEqual(run.stdout, output)
                help_run = subprocess.run([sys.executable, module+'.py', 'response-template', '--help'], capture_output=True, timeout=30)
                self.assertNotIn(b'--format', help_run.stdout)

    def test_local_source_root_both_tasks(self):
        for task in ('reasoning', 'observations'):
            command = [sys.executable, 'model_handoff.py', 'prepare', 'examples/file-corpus.json',
                       '--source-root', 'examples/synthetic-sources', '--task', task]
            raw = subprocess.run(command, capture_output=True, timeout=30)
            text = subprocess.run(command+['--format', 'text'], capture_output=True, timeout=30)
            self.assertEqual(raw.returncode, 0, raw.stderr)
            self.assertEqual(text.returncode, 0, text.stderr)
            self.assertEqual(text.stdout, render_handoff(json.loads(raw.stdout)).encode('ascii'))

    def test_existing_proposal_output_limits_apply_to_text_without_partial_output(self):
        for name, module, values, flags, _, _ in self.cases:
            if module not in ('answer_proposals', 'argument_proposals', 'application_proposals'):
                continue
            with self.subTest(version=name), tempfile.TemporaryDirectory() as directory:
                def save(value):
                    path = Path(directory) / (str(len(list(Path(directory).iterdir())))+'.json')
                    path.write_text(json.dumps(value), encoding='utf-8')
                    return str(path)
                args = [save(v) for v in values] + [save(v) if isinstance(v, dict) else v for v in flags]
                code = 'import '+module+' as m; m.MAX_OUTPUT_BYTES=1; m.main()'
                run = subprocess.run([sys.executable, '-c', code, 'prepare']+args+['--format', 'text'], capture_output=True, timeout=30)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(b'16 MiB', run.stderr)
                self.assertEqual(run.stdout, b'')
