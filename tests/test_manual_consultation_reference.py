"""Synthetic hash/path checks for prose-only manual cross-repository references."""
import hashlib
import json
from pathlib import Path
import unittest
import answer_draft
import answer_proposals as answers
import argument_map
from declared_provenance import PROVENANCE_FIELDS, validate_declared_provenance
from persona import payload_sha256
from tests.scale_fixture import build

ROOT=Path(__file__).resolve().parents[1]


def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')


class ManualConsultationReferenceTests(unittest.TestCase):
    def check_reference(self,package,envelope,reported,content_hash):
        before=canonical([package,envelope])
        self.assertEqual(reported,payload_sha256(envelope))
        self.assertEqual(reported,hashlib.sha256(canonical(envelope)).hexdigest())
        package_hash=payload_sha256(package)
        self.assertEqual(package_hash,hashlib.sha256(canonical(package)).hexdigest())
        self.assertNotEqual(package_hash,payload_sha256(package['persona']))
        self.assertNotEqual(package_hash,payload_sha256(package['knowledge']['papers']))
        self.assertNotEqual(package_hash,payload_sha256({'package':package}))
        self.assertNotEqual(reported,content_hash)
        self.assertNotEqual(reported,hashlib.sha256(json.dumps(envelope,indent=2).encode()).hexdigest())
        provenance=envelope['bundle']['import_record']['provenance']
        self.assertEqual(set(provenance),set(PROVENANCE_FIELDS))
        validate_declared_provenance(provenance)
        self.assertEqual(canonical([package,envelope]),before)

    def test_adopted_answer_reference(self):
        read=lambda name:json.loads((ROOT/'examples'/('review-attribution-'+name+'.json')).read_text())
        package=read('package');scope=read('scope')
        handoff=answers.prepare_handoff(package,scope)
        bundle=answers.import_response(package,scope,handoff,read('response'),read('provenance'))
        envelope=answers.export_reviewed(package,bundle,read('adoption'))
        result=answer_draft.inspect(package,envelope)
        self.check_reference(package,envelope,result['draft_sha256'],result['draft_content_sha256'])
        self.assertFalse(result['processing']['external_transmission'])

    def test_adopted_argument_reference(self):
        package,_,_,_,_,draft,envelope,_,_,review=build(1,1,1,1)
        result=argument_map.inspect(package,draft,envelope,review)
        self.check_reference(package,envelope,result['argument_map_sha256'],result['argument_content_sha256'])
        self.assertFalse(result['processing']['external_transmission'])

    def test_prose_scope_is_manual_and_conditional(self):
        text=(ROOT/'docs/WORKFLOWS.md').read_text().split('### Cite an adopted consultation by hand\n',1)[1].split('\n### ',1)[0]
        for term in ('Check the installed','bundle.import_record.provenance','DECLARED_NOT_VERIFIED',
                     'raw file-byte hash','private author identifier','required sharing permission',
                     'no exporter','recording review','INTERPRETIVE_SIMULATION'):
            self.assertIn(term,text)
        self.assertNotIn('```',text)


if __name__=='__main__':unittest.main()
