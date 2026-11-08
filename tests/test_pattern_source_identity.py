import json
import unittest
from pathlib import Path

from corpus_files import load_sources
from research_workflow import apply, build


class PatternSourceTests(unittest.TestCase):
    def setUp(self):
        self.corpus = json.loads(Path('examples/research-corpus.json').read_text())

    def pattern(self):
        return apply(build(self.corpus), 'Question', 'model design')['patterns'][0]

    def test_two_verified_ids_sharing_one_file_are_not_repeated_sources(self):
        corpus = json.loads(Path('examples/file-corpus.json').read_text())
        for key in ('source_file', 'source_sha256'):
            corpus['papers'][1][key] = corpus['papers'][0][key]
        package = build(load_sources(corpus, 'examples/synthetic-sources'))
        pattern = apply(package, 'Question', 'model design')['patterns'][0]
        self.assertTrue(all(p['source_verification'] == 'LOCAL_BYTES_SHA256_MATCH'
                            for p in package['knowledge']['papers']))
        self.assertEqual(pattern['classification'], 'MULTIPLE_RECORDS_SAME_SOURCE_HASH')
        self.assertEqual(pattern['distinct_source_hash_count'], 1)
        self.assertEqual(len(pattern['supporting']), 2)
        self.assertEqual(len({r['paper_id'] for r in pattern['supporting']}), 2)

    def test_distinct_hashes_retain_bounded_repetition(self):
        self.assertEqual(self.pattern()['classification'], 'REPEATED_OBSERVATION')
        self.assertEqual(self.pattern()['distinct_source_hash_count'], 2)

    def test_multiple_observations_in_one_paper_are_not_multiple_records(self):
        self.corpus['papers'] = self.corpus['papers'][:1]
        self.corpus['papers'][0]['observations'] *= 2
        self.assertEqual(self.pattern()['classification'], 'SINGLE_PAPER_OBSERVATION')

    def test_contested_same_source_keeps_both_stances(self):
        self.corpus['papers'][1]['source_sha256'] = self.corpus['papers'][0]['source_sha256']
        self.corpus['papers'][1]['observations'][0]['stance'] = 'challenge'
        pattern = self.pattern()
        self.assertEqual(pattern['classification'], 'CONTESTED')
        self.assertEqual(pattern['distinct_source_hash_count'], 1)
        self.assertEqual(len(pattern['supporting']), 1)
        self.assertEqual(len(pattern['challenging']), 1)

    def test_challenge_only_is_not_mislabeled_as_disagreement(self):
        for paper in self.corpus['papers']:
            paper['observations'][0]['stance'] = 'challenge'
        self.assertEqual(self.pattern()['classification'], 'CHALLENGE_ONLY')


if __name__ == '__main__':
    unittest.main()
