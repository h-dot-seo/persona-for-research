import copy
import json
import unittest
from pathlib import Path

from corpus_files import load_sources
from observation_input import verified_corpus
from research_workflow import apply, build


class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.corpus = json.loads(Path('examples/reasoning-corpus.json').read_text())

    def test_json_verification_labels_are_downgraded(self):
        for paper in self.corpus['papers']:
            paper['source_verification'] = 'LOCAL_BYTES_SHA256_MATCH'
            for obs in paper['observations']:
                obs['evidence_verification'] = 'EXACT_QUOTE_MATCH_ONLY'
                for component in obs.get('reasoning', {}).values():
                    component['evidence_verification'] = 'EXACT_QUOTE_MATCH_ONLY'
        self.corpus['receipt_sha256'] = 'fake-json-receipt'
        package = build(self.corpus)
        self.assertEqual(package['persona']['rules'][0]['evidence_verification'], 'NOT_PERFORMED')
        self.assertEqual(package['knowledge']['papers'][0]['source_verification'], 'NOT_PERFORMED')
        self.assertEqual(package['persona']['rules'][0]['reasoning']['uncertainty']['evidence_verification'], 'NOT_PERFORMED')

    def test_quote_intake_does_not_attest_local_bytes(self):
        self.corpus['papers'][0]['source_verification'] = 'LOCAL_BYTES_SHA256_MATCH'
        package = build(verified_corpus(self.corpus))
        self.assertEqual(package['persona']['rules'][0]['evidence_verification'], 'EXACT_QUOTE_MATCH_ONLY')
        self.assertEqual(package['knowledge']['papers'][0]['source_verification'], 'NOT_PERFORMED')

    def test_file_intake_retains_actual_byte_checks(self):
        manifest = json.loads(Path('examples/file-corpus.json').read_text())
        package = build(load_sources(manifest, Path('examples/synthetic-sources')))
        self.assertEqual(package['knowledge']['papers'][0]['source_verification'], 'LOCAL_BYTES_SHA256_MATCH')

    def test_modified_verified_corpus_is_rejected(self):
        corpus = verified_corpus(self.corpus)
        corpus['papers'][0]['observations'][0]['evidence_quote'] = 'altered'
        with self.assertRaisesRegex(ValueError, 'changed after intake'):
            build(corpus)

    def test_serialized_receipt_does_not_survive_roundtrip(self):
        corpus = json.loads(json.dumps(verified_corpus(self.corpus)))
        self.assertEqual(build(corpus)['persona']['rules'][0]['evidence_verification'], 'NOT_PERFORMED')

    def test_knowledge_mutation_is_rejected(self):
        for field, value in [('year', 1900), ('source_sha256', 'f' * 64),
                             ('authorized', False), ('source_verification', 'forged')]:
            package = build(verified_corpus(self.corpus))
            package['knowledge']['papers'][0][field] = value
            with self.assertRaisesRegex(ValueError, 'knowledge papers payload hash mismatch'):
                apply(package, 'Question', 'model design')

    def test_build_does_not_alias_caller_or_mutate_it(self):
        original = copy.deepcopy(self.corpus)
        package = build(self.corpus)
        self.assertEqual(self.corpus, original)
        self.corpus['papers'][0]['year'] = 1900
        self.assertEqual(package['knowledge']['papers'][0]['year'], original['papers'][0]['year'])
        apply(package, 'Question', 'model design')


if __name__ == '__main__':
    unittest.main()
