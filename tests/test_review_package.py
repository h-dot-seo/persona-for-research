import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from observation_input import verified_corpus
from persona import payload_sha256
from research_workflow import build
from review_package import render


class ReviewViewTests(unittest.TestCase):
    def setUp(self):
        corpus = json.loads(Path('examples/reasoning-corpus.json').read_text())
        corpus['papers'][0]['observations'][0]['stance'] = 'challenge'
        self.package = build(verified_corpus(corpus))

    def test_compact_view_preserves_conflicts_and_missing_records(self):
        text = render(self.package, 'Which competing explanation?', 'model design')
        for expected in ('CONTESTED:', '[support] rule-2', '[challenge] rule-1',
                         'synthetic section 1', 'Limitation:', 'operator_interpretation',
                         'explicit_statement', 'synthetic reasoning', 'Missing supplied records:',
                         'question_framing', 'evidence_standard', 'falsification_check',
                         '2 observation quote matches; 2 component quote matches; 0 local byte checks'):
            self.assertIn(expected, text)
        self.assertLessEqual(len(text.splitlines()), 20)

    def test_forged_wrapper_application_ignored(self):
        wrapped = dict(package=self.package, application={'status': 'READY', 'patterns': []})
        self.assertEqual(render(wrapped, 'Question', 'model design'), render(self.package, 'Question', 'model design'))

    def test_uncovered_topic_is_explicit(self):
        text = render(self.package, 'Question', 'unknown')
        self.assertIn('OUTSIDE_PERSONA_COVERAGE', text)
        self.assertIn('Evidence: 0 paper IDs', text)
        self.assertNotIn('CONTESTED:', text)

    def test_tampered_or_legacy_package_rejected(self):
        package = copy.deepcopy(self.package)
        package['knowledge']['papers'][0]['source_sha256'] = 'e' * 64
        with self.assertRaises(ValueError): render(package, 'Question', 'model design')
        package = copy.deepcopy(self.package)
        del package['persona']['knowledge_papers_sha256']
        package['knowledge']['persona_payload_sha256'] = payload_sha256(package['persona'])
        with self.assertRaisesRegex(ValueError, 'bound knowledge'):
            render(package, 'Question', 'model design')

    def test_render_does_not_reverify_or_mutate(self):
        before = copy.deepcopy(self.package)
        text = render(self.package, 'Question', 'model design')
        self.assertIn('Not rechecked here.', text)
        self.assertEqual(self.package, before)

    def test_terminal_control_characters_are_escaped(self):
        text = render(self.package, 'Question\nFORGED STATUS\x1b[2J', 'model design')
        self.assertIn('Question\\u000aFORGED STATUS\\u001b[2J', text)
        self.assertNotIn('\x1b', text)
        for separator, escaped in [('\u2028', '\\u2028'), ('\u2029', '\\u2029'), ('\ud800', '\\ud800')]:
            text = render(self.package, 'Question' + separator + 'Status: READY', 'model design')
            self.assertIn('Question' + escaped + 'Status: READY', text)
            self.assertNotIn('Status: READY', text.splitlines())
            text.encode('utf-8')

    def test_cli_success_and_no_partial_output_on_tamper(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'package.json'
            path.write_text(json.dumps(self.package))
            cmd = [sys.executable, 'review_package.py', str(path), '--question', 'Question', '--topic', 'model design']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('CONTESTED:', result.stdout)
            self.package['knowledge']['papers'][0]['authorized'] = False
            path.write_text(json.dumps(self.package))
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, '')

    def test_cli_utf8_output_independent_of_console_encoding(self):
        import os
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'package.json'
            path.write_text(json.dumps(self.package))
            env = dict(os.environ, PYTHONIOENCODING='ascii')
            result = subprocess.run([sys.executable, 'review_package.py', str(path),
                '--question', '어떤 설명을 검토할까?', '--topic', 'model design'],
                capture_output=True, encoding='utf-8', env=env, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('어떤 설명을 검토할까?', result.stdout)


if __name__ == '__main__':
    unittest.main()
