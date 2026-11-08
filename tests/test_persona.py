import copy
import unittest
from persona import validate, payload_sha256
from safe_canonical_read import sanitize


class PersonaTest(unittest.TestCase):
    def setUp(self):
        self.p = dict(author_id='synthetic-author', version='0.1.0', build_id='demo',
                      identity=dict(simulation_only=True, private_beliefs_inferred=False))
        self.k = {k:self.p[k] for k in ('author_id','version','build_id')}
        self.k.update(persona_payload_sha256=payload_sha256(self.p), papers=[])

    def test_holdout_statistic_strings_cannot_leak_identifiers(self):
        value = {'split': 'holdout', 'source_status': 'secret-paper-id',
                 'score_note': 'secret-doi', 'status': 'PASS', 'count': 3,
                 'nested': {'reasoning_status': 'secret-author'}}
        result = sanitize(value)
        self.assertEqual(result['canonical'], {'status': 'PASS', 'count': 3, 'nested': {}})
        self.assertEqual(result['redacted_fields'], 4)
        self.assertNotIn('secret', str(result))
        self.assertNotIn('blind_papers', sanitize({'blind_papers': {'secret-paper-id': {'score': 4}}})['canonical'])
        self.assertNotIn('split', sanitize({'split': 'holdout secret-paper-id'})['canonical'])

    def test_binding(self):
        self.assertEqual(validate(self.p, self.k), [])
        changed = copy.deepcopy(self.p); changed['identity']['simulation_only'] = False
        self.assertIn('persona logical payload hash mismatch', validate(changed, self.k))
        self.assertIn('simulation_only must be true', validate(changed, self.k))

    def test_holdout_and_cross_author_rejected(self):
        self.k['papers'] = [dict(paper_id='synthetic', author_id='other', split='blind',
                               runtime_knowledge_eligible=True, source_sha256='0'*64, locator='section 1')]
        errors = validate(self.p,self.k)
        self.assertIn('ineligible runtime paper', errors)
        self.assertIn('cross-author runtime record', errors)

    def test_sanitized_projection(self):
        result = sanitize({'blind_papers':['secret-demo'], 'rules':['demo'], 'blind_count':5})
        self.assertNotIn('blind_papers', result['canonical'])
        self.assertEqual(result['canonical']['blind_count'], 5)
        self.assertEqual(result['canonical']['rules'], ['demo'])


if __name__ == '__main__':
    unittest.main()
