import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from corpus_files import load_sources
from observation_input import verified_corpus
from research_workflow import build


class IntakeErrorTests(unittest.TestCase):
    def cases(self):
        corpus = json.loads(Path('examples/observed-corpus.json').read_text())
        yield []
        yield None
        yield {}
        for field, value in [('papers', {}), ('papers', [None]), ('version', []), ('author_id', '')]:
            c = copy.deepcopy(corpus)
            c[field] = value
            yield c
        for value in ({}, [None]):
            c = copy.deepcopy(corpus)
            c['papers'][0]['observations'] = value
            yield c

    def test_all_intake_apis_reject_malformed_shapes_cleanly(self):
        for corpus in self.cases():
            for function in (build, verified_corpus):
                with self.subTest(corpus=corpus, function=function.__name__):
                    with self.assertRaises(ValueError): function(corpus)

    def test_file_preflight_precedes_filesystem_access(self):
        with patch.object(Path, 'resolve', side_effect=AssertionError('filesystem reached')):
            for corpus in self.cases():
                with self.assertRaises(ValueError): load_sources(corpus, 'unused-root')

    def test_cli_malformed_input_has_no_traceback_or_partial_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'invalid.json'
            for corpus in self.cases():
                path.write_text(json.dumps(corpus))
                for script in ('research_workflow.py', 'observation_input.py', 'corpus_files.py'):
                    cmd = [sys.executable, script, str(path), '--question', 'Question', '--topic', 'model design']
                    if script == 'corpus_files.py': cmd += ['--source-root', directory]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
                    with self.subTest(script=script, corpus=corpus):
                        self.assertNotEqual(result.returncode, 0)
                        self.assertEqual(result.stdout, '')
                        self.assertNotIn('Traceback', result.stderr)


if __name__ == '__main__':
    unittest.main()
