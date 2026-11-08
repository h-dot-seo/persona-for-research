"""Recorded answer context in real argument/journey views, without new permissions."""
import copy
import json
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

import answer_draft as ad
import answer_proposals as ap
import argument_map as am
import argument_proposals as gp
import journey_compare
import journey_html
import journey_inputs
import pattern_proposals
import research_journey
import tests.test_contextual_answer_proposals as answer_fixture
import tests.test_pattern_evidence_reasons as pattern_fixture
import tests.test_journey_html as html_fixture
from persona import payload_sha256


class RenderedText(HTMLParser):
    """Human-readable disclosure content, excluding snapshot JSON and head/style."""
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.excluded = None
        self.parts = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag == 'head' or dict(attrs).get('id') == 'complete-json':
            self.excluded = tag

    def handle_endtag(self, tag):
        if tag == self.excluded:
            self.excluded = None

    def handle_data(self, data):
        if self.excluded is None:
            self.parts.append(data)


class ContextualArgumentIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.c = answer_fixture.ContextualAnswerTests()
        self.c.setUp()
        c = self.c
        self.f = c.f
        self.p = c.p
        pattern = pattern_fixture.PatternEvidenceReasonTests()
        pattern.setUp()
        pattern.response['candidates'].append(copy.deepcopy(pattern.proposal))
        pattern.reimport()
        pattern.accept()
        pattern.review['decisions'][1].update(decision='reject', review_note='Rejected historical context interpretation.')
        c.raw['patterns'] = pattern_proposals.export_reviewed(pattern.package, pattern.bundle, pattern.review)
        self.f.case.patterns = copy.deepcopy(c.raw['patterns'])
        c.scope = c.scope_for(c.raw)
        c.scope['evidence_refs'] = [copy.deepcopy(c.c.a), copy.deepcopy(c.c.review)]
        c.reset()
        extra = copy.deepcopy(c.response['candidates'][0])
        extra['text'] = 'Active answer claim outside selected argument endpoints.'
        extra['citations'][0]['reference'] = copy.deepcopy(c.c.review)
        c.response['candidates'].extend([
            dict(text='Uncited answer conclusion.', claim_type='operator_synthesis', uncertainty=None, citations=[]),
            extra,
            dict(text='Rejected answer alternative.', claim_type='operator_synthesis', uncertainty=None, citations=[]),
        ])
        c.reimport()
        for index, claim_id in enumerate(('claim', 'conclusion', 'outside')):
            c.accept(index, claim_id)
        c.review['decisions'][3].update(decision='reject', review_note='Rejected answer history retained.')
        self.draft = c.envelope()
        self.f.case.draft = self.draft
        self.f.review = ad.review_template(self.p, self.draft, 'synthetic-final-reviewer')
        self.scope, self.handoff, self.bundle, self.adoption, self.f.argument = self.argument(True)

    def argument(self, recorded):
        scope = gp.template(self.p, self.draft, 'synthetic-operator', self.f.review,
                            include_recorded_answer_context=recorded)
        scope['selected_claim_ids'] = ['claim', 'conclusion']
        handoff = gp.prepare_handoff(self.p, self.draft, scope, self.f.review)
        response = gp.response_template(self.p, self.draft, scope, handoff, self.f.review)
        response['candidates'] = [dict(premise_claim_ids=['claim'], conclusion_claim_id='conclusion',
            bridge_rationale=text, assumptions=['Original declared assumption.'], defeater=None)
            for text in ('Original imported bridge.', 'Rejected imported bridge.')]
        bundle = gp.import_response(self.p, self.draft, scope, handoff, response, self.c.provenance, self.f.review)
        adoption = gp.review_template(self.p, self.draft, bundle, 'synthetic-adopter', self.f.review)
        adoption['decisions'][0].update(decision='accept', review_note='Explicit bridge revision.',
            reviewed_step=dict(response['candidates'][0], step_id='bridge',
                               bridge_rationale='Reviewed bridge rationale.', assumptions=['Reviewed assumption.']))
        adoption['decisions'][1].update(decision='reject', review_note='Rejected bridge history retained.')
        envelope = gp.export_reviewed(self.p, self.draft, bundle, adoption, self.f.review)
        return scope, handoff, bundle, adoption, envelope

    def test_full_context_and_bridge_histories_survive_actual_journey(self):
        report = self.f.report()
        argument = report['argument_review']
        packet = argument['proposal_review']
        self.assertEqual(packet['schema'], gp.SCHEMAS[2]['packet'])
        context = packet['recorded_answer_context']
        self.assertEqual(context, self.handoff['recorded_answer_context'])
        self.assertEqual(context['reasoning_context'], self.c.handoff['reasoning_context'])
        self.assertEqual(context['answer_scope_sha256'], payload_sha256(self.c.scope))
        self.assertEqual(context['answer_proposal_bundle_sha256'], payload_sha256(self.c.bundle))
        self.assertEqual(context['answer_adoption_review_sha256'], payload_sha256(self.c.review))
        self.assertEqual(context['role'], 'RECORDED_ANSWER_PREPARATION_IMPORT_CONTEXT_NOT_CURRENT_ARGUMENT_CONTEXT')
        self.assertEqual(packet['candidates'][0]['original_inspection']['bridge_rationale'], 'Original imported bridge.')
        self.assertEqual(packet['candidates'][0]['reviewed_inspection']['bridge_rationale'], 'Reviewed bridge rationale.')
        self.assertEqual(packet['candidates'][1]['decision'], 'reject')
        self.assertEqual(argument['answer']['proposal_review']['candidates'][3]['decision'], 'reject')
        self.assertEqual(context['reasoning_context']['pattern_review']['proposal_review']['candidates'][1]['decision'], 'reject')
        self.assertEqual(report['answer_review_status'], 'DECLARED_REVIEW_INCOMPLETE')
        self.assertTrue(all(row['decision'] == 'defer' for row in self.f.review['decisions']))
        self.assertEqual(json.loads(json.dumps(report)), report)
        text = research_journey.render(*self.f.args())
        for phrase in ('Original imported bridge.', 'Reviewed bridge rationale.', 'Rejected imported bridge.',
                       'Rejected historical context interpretation.', 'Rejected answer alternative.',
                       'Recorded answer-preparation/import context (not newly supplied or current argument context):'):
            self.assertIn(phrase, text)

    def test_wider_recorded_scope_adds_no_argument_endpoints_or_citation_transfer(self):
        argument = am.inspect(self.p, self.draft, self.f.argument, self.f.review)
        self.assertEqual(len(argument['answer']['claims']), 3)
        self.assertEqual(len(self.handoff['recorded_answer_context']['reasoning_context']['evidence_refs']), 2)
        step = argument['steps'][0]
        self.assertEqual(step['premise_claim_ids'], ['claim'])
        self.assertEqual(step['conclusion_claim_id'], 'conclusion')
        self.assertEqual(step['conclusion']['direct_citation_count'], 0)
        self.assertEqual(step['citation_transfer'], 'NOT_PERFORMED')
        report = self.f.report()
        uses = [u for route in report['evidence_routes'] for u in route['direct_argument_uses']]
        self.assertEqual({u['claim_id'] for u in uses}, {'claim'})
        for claim_id in ('outside', 'not-an-existing-claim'):
            adoption = copy.deepcopy(self.adoption)
            adoption['decisions'][0]['reviewed_step']['premise_claim_ids'] = [claim_id]
            with self.assertRaises(ValueError):
                gp.export_reviewed(self.p, self.draft, self.bundle, adoption, self.f.review)
        legacy = self.argument(False)[-1]
        legacy_args = self.f.args()
        legacy_args[6] = legacy
        self.assertEqual(report['evidence_routes'], research_journey.inspect(*legacy_args)['evidence_routes'])

    def test_current_context_difference_does_not_rebind_imported_argument(self):
        old_argument = copy.deepcopy(self.f.argument)
        recorded = copy.deepcopy(self.handoff['recorded_answer_context'])
        self.f.case.context['assessments'][0]['remaining_uncertainty'] = 'Current journey reconsideration only.'
        self.f.relations['relations'][0]['rationale'] = 'Current relationship annotation only.'
        report = self.f.report()
        comparison = report['recorded_answer_context_comparison']
        self.assertEqual(comparison['status'], 'DIFFERENT_SUPPLIED_ARTIFACTS')
        self.assertEqual(comparison['changed_fields'], ['context', 'publication_relations'])
        self.assertFalse(comparison['automatic_rebinding'])
        self.assertEqual(self.f.argument, old_argument)
        self.assertEqual(report['argument_review']['proposal_review']['recorded_answer_context'], recorded)
        self.assertIn('Current journey reconsideration only.', research_journey.render(*self.f.args()))

    def test_rejected_context_edit_stales_full_draft_binding(self):
        self.c.scope['research_context']['patterns']['review']['decisions'][1]['review_note'] += ' Revised rejection note.'
        self.c.handoff = ap.prepare_handoff(self.p, self.c.scope)
        self.c.response['handoff_sha256'] = payload_sha256(self.c.handoff)
        prior_review = copy.deepcopy(self.c.review)
        self.c.reimport()
        prior_review['proposal_bundle_sha256'] = payload_sha256(self.c.bundle)
        self.c.review = prior_review
        changed = self.c.envelope()
        self.assertEqual(
            [row['reviewed_claim'] for row in changed['review']['decisions'] if row['decision'] == 'accept'],
            [row['reviewed_claim'] for row in self.draft['review']['decisions'] if row['decision'] == 'accept'])
        self.assertNotEqual(payload_sha256(changed), payload_sha256(self.draft))
        fresh_review = ad.review_template(self.p, changed, 'synthetic-final-reviewer')
        with self.assertRaises(ValueError):
            gp.prepare_handoff(self.p, changed, self.scope, fresh_review)
        with self.assertRaises(ValueError):
            am.inspect(self.p, changed, self.f.argument, fresh_review)

    def test_passive_html_renders_history_and_role_outside_json_snapshot(self):
        self.f.case.context['assessments'][0]['remaining_uncertainty'] = '<script>current annotation</script>\u202e'
        html = journey_html.render(*self.f.args())
        doc = html_fixture.Document(html)
        html_fixture.JourneyHtmlTests().assert_passive(doc)
        report = self.f.report()
        self.assertEqual(json.loads(doc.saved['complete-json']), report)
        self.assertEqual(doc.saved['snapshot-sha256'], payload_sha256(report))
        visible = '\n'.join(RenderedText(html).parts)
        for phrase in ('Original imported bridge.', 'Reviewed bridge rationale.', 'Rejected imported bridge.',
                       'Rejected historical context interpretation.', 'Rejected answer alternative.',
                       'RECORDED_ANSWER_PREPARATION_IMPORT_CONTEXT_NOT_CURRENT_ARGUMENT_CONTEXT',
                       'DIFFERENT_SUPPLIED_ARTIFACTS', 'NOT_PERFORMED'):
            self.assertIn(phrase, visible)
        self.assertIn('<script>current annotation</script>', visible)
        self.assertNotIn('<script>', html)
        self.assertNotIn('\u202e', html)

    def test_pinned_comparison_keeps_opt_in_and_changed_history_in_full_reports(self):
        previous = copy.deepcopy(self.f.args())
        previous[6] = self.argument(False)[-1]
        self.adoption['decisions'][1]['review_note'] += ' Later rejection annotation.'
        self.f.argument = gp.export_reviewed(self.p, self.draft, self.bundle, self.adoption, self.f.review)
        self.f.case.context['assessments'][0]['remaining_uncertainty'] = 'Current comparison annotation.'
        with tempfile.TemporaryDirectory() as temp:
            roots = [Path(temp)/'previous', Path(temp)/'current']
            cards = []
            for root, args in zip(roots, (previous, self.f.args())):
                root.mkdir()
                selection = journey_inputs.template()
                selection['pattern_id'] = args[8]
                for name, value in zip(journey_inputs.REQUIRED, args[:8]):
                    selection['artifacts'][name] = name+'.json'
                    (root/(name+'.json')).write_text(json.dumps(value), encoding='utf-8')
                selection['artifacts']['declared_review'] = 'review.json'
                (root/'review.json').write_text(json.dumps(args[9]), encoding='utf-8')
                cards.append(journey_inputs.prepare(selection, root))
            result = journey_compare.compare(cards[0], roots[0], cards[1], roots[1])
        before = result['previous_report']['argument_review']['proposal_review']
        after = result['current_report']['argument_review']['proposal_review']
        self.assertNotIn('recorded_answer_context', before)
        self.assertEqual(after['recorded_answer_context'], self.handoff['recorded_answer_context'])
        self.assertIn('Later rejection annotation.', after['candidates'][1]['review_note'])
        self.assertEqual(result['current_report']['recorded_answer_context_comparison']['status'], 'DIFFERENT_SUPPLIED_ARTIFACTS')
        decisions = next(g for g in result['declared_record_comparison'] if g['group'] == 'argument_proposal_decisions')
        self.assertTrue(any(row['status'] != 'UNCHANGED_AT_DECLARED_ID' for row in decisions['records']))
        self.assertFalse(result['automatic_approval'])


if __name__ == '__main__':
    unittest.main()
