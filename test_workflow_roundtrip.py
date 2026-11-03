"""Exercise the complete synthetic local-source workflow through real CLI calls."""
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class WorkflowRoundtripTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, *map(str, args)],
                              capture_output=True, text=True, timeout=20)

    def test_local_sources_to_candidate_release_review(self):
        corpus = json.loads(Path('examples/reasoning-corpus.json').read_text())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for paper in corpus['papers']:
                raw = ('# Synthetic only\n\n' + '\n'.join(
                    '## ' + k + '\n' + v + '\n' for k, v in paper.pop('segments').items())).encode()
                name = paper['paper_id'] + '.md'
                (root / name).write_bytes(raw)
                paper['source_file'] = name
                paper['source_sha256'] = hashlib.sha256(raw).hexdigest()
                paper.pop('segments_sha256')
            manifest = root / 'manifest.json'
            manifest.write_text(json.dumps(corpus))
            args = ('corpus_files.py', manifest, '--source-root', root,
                    '--question', 'Which competing explanation?', '--topic', 'model design')
            before = self.run_cli(*args)
            self.assertEqual(before.returncode, 0, before.stderr)
            previous = json.loads(before.stdout)
            application = previous['application']
            self.assertFalse(application['processing']['llm_used'])
            self.assertEqual(len(application['reasoning_cards']), 1)
            self.assertEqual(application['evidence_coverage']['status'], 'PARTIAL_DIMENSION_COVERAGE')
            for paper in previous['package']['knowledge']['papers']:
                self.assertEqual(paper['source_verification'], 'LOCAL_BYTES_SHA256_MATCH')
                self.assertNotIn('segments', paper)
            old_path = root / 'previous.json'
            old_path.write_text(before.stdout)
            corpus['version'] = '2'
            corpus['build_id'] = 'synthetic-candidate'
            corpus['papers'][0]['observations'][0]['stance'] = 'challenge'
            manifest.write_text(json.dumps(corpus))
            after = self.run_cli(*args)
            self.assertEqual(after.returncode, 0, after.stderr)
            self.assertEqual(json.loads(after.stdout)['application']['patterns'][0]['classification'], 'CONTESTED')
            new_path = root / 'candidate.json'
            new_path.write_text(after.stdout)
            compared = self.run_cli('compare_releases.py', old_path, new_path)
            self.assertEqual(compared.returncode, 0, compared.stderr)
            result = json.loads(compared.stdout)
            self.assertEqual(result['status'], 'REVIEW_REQUIRED')
            self.assertFalse(result['canonical_update_performed'])
            self.assertTrue(result['modified_papers'][0]['observations_changed'])
            self.assertEqual(old_path.read_text(), before.stdout)
            self.assertEqual(new_path.read_text(), after.stdout)
            for paper in corpus['papers']:
                self.assertEqual(hashlib.sha256((root / paper['source_file']).read_bytes()).hexdigest(), paper['source_sha256'])
            (root / corpus['papers'][0]['source_file']).write_text('synthetic tampering')
            rejected = self.run_cli(*args)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertEqual(rejected.stdout, '')
            self.assertIn('byte hash mismatch', rejected.stderr)
            self.assertEqual(old_path.read_text(), before.stdout)


if __name__ == '__main__':
    unittest.main()
