import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from persona import payload_sha256, validate
from research_workflow import apply, build


class RuntimeAuthorizationTests(unittest.TestCase):
    def setUp(self):
        corpus = json.loads(Path('examples/research-corpus.json').read_text())
        self.package = build(corpus)
        del self.package['persona']['knowledge_papers_sha256']
        self.package['knowledge']['persona_payload_sha256'] = payload_sha256(self.package['persona'])

    def test_legacy_package_requires_explicit_true(self):
        for value in (False, None, 0, 1, 'true'):
            package = copy.deepcopy(self.package)
            package['knowledge']['papers'][0]['authorized'] = value
            self.assertIn('runtime paper authorization required', validate(package['persona'], package['knowledge']))
            with self.assertRaisesRegex(ValueError, 'authorization required'):
                apply(package, 'Question', 'model design')

    def test_missing_authorization_rejected(self):
        del self.package['knowledge']['papers'][0]['authorized']
        with self.assertRaisesRegex(ValueError, 'authorization required'):
            apply(self.package, 'Question', 'model design')

    def test_authorized_legacy_and_current_packages_work(self):
        self.assertEqual(validate(self.package['persona'], self.package['knowledge']), [])
        self.assertEqual(apply(self.package, 'Question', 'model design')['status'], 'PLANNING_SCAFFOLD')
        current = build(json.loads(Path('examples/research-corpus.json').read_text()))
        self.assertEqual(validate(current['persona'], current['knowledge']), [])

    def test_standalone_validator_rejects_legacy_unauthorized_source(self):
        self.package['knowledge']['papers'][0]['authorized'] = False
        with tempfile.TemporaryDirectory() as directory:
            paths = [Path(directory) / (name + '.json') for name in ('persona', 'knowledge')]
            for name, path in zip(('persona', 'knowledge'), paths):
                path.write_text(json.dumps(self.package[name]))
            result = subprocess.run([sys.executable, 'persona.py', *map(str, paths)],
                                    capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 1)
            self.assertFalse(json.loads(result.stdout)['mechanically_valid'])
            self.assertIn('runtime paper authorization required', json.loads(result.stdout)['errors'])


if __name__ == '__main__':
    unittest.main()
