"""Synthetic compatibility and history integration for an explicit audit only."""
import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch

import answer_draft
import argument_map
import argument_proposals
import citation_reasoning as audit
import test_citation_explanations as enhanced_fixture
from persona import payload_sha256

ROOT=Path(__file__).resolve().parent


class CitationReasoningIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.frozen=json.loads((ROOT/'examples/legacy-answer-argument-v055.json').read_text(encoding='utf-8'))
        self.package=self.frozen['package']

    def test_frozen_v055_current_and_historical_citations_not_mixed(self):
        for case in self.frozen['cases']:
            with self.subTest(case=case['label']):
                result=audit.audit(self.package,case['draft'],case['review'])
                self.assertEqual(result['inventory']['citation_uses'],3)
                self.assertEqual(result['inventory']['explanation_states'],dict(LEGACY_KEY_ABSENT=3,EXPLICITLY_NOT_SUPPLIED=0,DECLARED_INTERPRETATION_NOT_VALIDATED=0))
                self.assertEqual([row['claim_id'] for row in result['uncited_claims']],['conclusion'])
                self.assertTrue(all(row['final_review']['decision']=='defer' for row in result['current_claims']))
                self.assertFalse(result['proposal_history']['active']);self.assertFalse(result['proposal_history']['counted_as_current_citation_uses'])
                if case['label']=='imported':
                    packet=result['proposal_history']['packet'];self.assertEqual(len(packet['candidates']),4)
                    self.assertEqual(packet['candidates'][-1]['decision'],'reject')
                    rejected=packet['candidates'][-1]['original_inspection']['citations'][0]['evidence']['reference']
                    self.assertNotIn(rejected,[r['use_key']['reference'] for r in result['citation_uses']])
                else:self.assertNotIn('packet',result['proposal_history'])

    def test_audit_does_not_change_frozen_answer_or_argument_replay(self):
        for case in self.frozen['cases']:
            before=copy.deepcopy((self.package,case));draft=case['draft'];review=case['review']
            audit.audit(self.package,draft,review)
            values=dict(answer_inspection=answer_draft.inspect(self.package,draft),
                answer_reviewed=answer_draft.review(self.package,draft,review),
                argument_handoff=argument_proposals.prepare_handoff(self.package,draft,case['argument_scope'],review),
                argument_bundle=argument_proposals.validate_bundle(self.package,draft,case['argument_bundle'],review),
                argument_packet=argument_proposals.review_proposals(self.package,draft,case['argument_bundle'],case['argument_adoption'],review),
                argument_inspection=argument_map.inspect(self.package,draft,case['argument_envelope'],review))
            self.assertEqual({k:payload_sha256(v) for k,v in values.items()},case['expected_sha256'])
            self.assertEqual((self.package,case),before)

    def test_v2_adopted_original_and_rejected_reasoning_stays_separate(self):
        fixture=enhanced_fixture.ReasonedAnswerProposalTests();fixture.setUp();c=fixture.c
        rejected=copy.deepcopy(c.response['candidates'][0]);rejected['citations'][0]['explanation']=dict(enhanced_fixture.EXPLANATION,rationale='Rejected original explanation.')
        c.response['candidates'].append(rejected);c.reimport();c.accept(0,'synthetic-claim')
        c.review['decisions'][0]['reviewed_claim']['citations'][0]['explanation']=dict(enhanced_fixture.EXPLANATION,rationale='Adopted edited explanation.')
        c.review['decisions'][1].update(decision='reject',review_note='Synthetic exclusion only.')
        envelope=c.envelope();review=answer_draft.review_template(c.package,envelope,'synthetic-final-reviewer')
        result=audit.audit(c.package,envelope,review)
        self.assertEqual(result['bindings']['draft_sha256'],payload_sha256(envelope))
        self.assertNotEqual(result['bindings']['draft_sha256'],answer_draft.inspect(c.package,envelope)['draft_content_sha256'])
        self.assertEqual(result['inventory']['citation_uses'],2)
        self.assertEqual(result['inventory']['explanation_states'],dict(LEGACY_KEY_ABSENT=0,EXPLICITLY_NOT_SUPPLIED=1,DECLARED_INTERPRETATION_NOT_VALIDATED=1))
        uses=result['citation_uses'];self.assertEqual(uses[0]['explanation']['origin'],'OPERATOR_ADOPTED_IMPORTED_INTERPRETATION')
        self.assertEqual(uses[0]['explanation']['declaration']['rationale'],'Adopted edited explanation.')
        packet=result['proposal_history']['packet'];self.assertIsNone(packet['candidates'][0]['original_inspection']['citations'][0]['explanation'])
        self.assertEqual(packet['candidates'][1]['original_inspection']['citations'][0]['explanation']['rationale'],'Rejected original explanation.')
        self.assertIn('Rejected original explanation.',audit.render(result))
        self.assertFalse(result['processing']['source_reread']);self.assertFalse(result['processing']['automatic_approval'])

    def test_new_final_review_is_distinct_from_candidate_adoption(self):
        case=next(c for c in self.frozen['cases'] if c['label']=='imported');review=copy.deepcopy(case['review'])
        review['decisions'][0].update(decision='retain',note='A declaration does not justify the citation.')
        review['decisions'][1].update(decision='reject',note='Current claim rejected, still visible.')
        result=audit.audit(self.package,case['draft'],review)
        self.assertEqual(result['inventory']['explanation_states']['LEGACY_KEY_ABSENT'],3)
        self.assertEqual([r['final_review']['decision'] for r in result['current_claims']],['retain','reject','defer'])
        self.assertEqual(result['proposal_history']['packet']['accepted_count'],3)
        self.assertEqual(result['proposal_history']['packet']['deferred_count'],0)

    def test_changed_rejected_history_stales_old_final_review_without_upgrade(self):
        case=next(c for c in self.frozen['cases'] if c['label']=='imported');changed=copy.deepcopy(case['draft'])
        changed['review']['decisions'][-1]['review_note']+=' Changed historical rejection note.'
        with self.assertRaisesRegex(ValueError,'stale'):audit.audit(self.package,changed,case['review'])
        fresh=audit.audit(self.package,changed)
        self.assertNotEqual(fresh['bindings']['draft_sha256'],payload_sha256(case['draft']))
        self.assertEqual(fresh['inventory']['explanation_states']['LEGACY_KEY_ABSENT'],3)
        self.assertEqual(fresh['final_review'],'NOT_SUPPLIED')

    def test_pending_proposal_packets_are_not_drafts_or_exportable_audits(self):
        fixture=enhanced_fixture.ReasonedAnswerProposalTests();fixture.setUp();c=fixture.c
        for draft in (c.bundle,c.packet(),dict(schema='persona.reviewed-answer-proposals.v2',bundle=c.bundle,review=c.review)):
            with self.assertRaises(ValueError):audit.audit(c.package,draft)

    def test_no_source_access_even_with_recorded_locators_and_provenance(self):
        case=next(c for c in self.frozen['cases'] if c['label']=='imported')
        with patch.object(Path,'open',side_effect=AssertionError('source file accessed')):
            result=audit.audit(self.package,case['draft'],case['review'])
        for use in result['citation_uses']:
            self.assertIn('source_sha256',use['evidence']);self.assertIn('recorded_source_check',use['evidence'])
        self.assertEqual(result['bindings']['package_sha256'],payload_sha256(self.package))
        self.assertEqual(result['semantic_validation'],'NOT_PERFORMED')


if __name__=='__main__':unittest.main()
