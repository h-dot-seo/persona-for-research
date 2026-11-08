"""Synthetic offline answer candidates and explicit operator adoption only."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import answer_proposals as proposals
import answer_draft
import tests.test_answer_draft as fixture
from persona import payload_sha256

ROOT = Path(__file__).resolve().parents[1]


class AnswerProposalTests(unittest.TestCase):
    def setUp(self):
        case = fixture.AnswerDraftTests(); case.setUp()
        self.package = case.package
        self.quote = {k: copy.deepcopy(v) for k, v in case.quote.items() if k != 'claim_id'}
        self.candidate = {k: copy.deepcopy(v) for k, v in case.synthesis.items() if k != 'claim_id'}
        self.scope = proposals.template(self.package, 'Which synthetic comparison is useful?', 'synthetic-topic', 2020, 'synthetic-operator')
        self.scope['evidence_refs'] = [copy.deepcopy(c['reference']) for c in self.candidate['citations']]
        self.provenance = dict(provider_id='synthetic-no-provider', model_id='synthetic-no-model', run_id='synthetic-run',
            operator_id='synthetic-importer', execution_location='unknown')
        self.handoff = proposals.prepare_handoff(self.package, self.scope)
        self.response = proposals.response_template(self.package, self.scope, self.handoff)
        self.response['candidates'] = [copy.deepcopy(self.candidate)]
        self.reimport()

    def reimport(self):
        self.bundle = proposals.import_response(self.package, self.scope, self.handoff, self.response, self.provenance)
        self.review = proposals.review_template(self.package, self.bundle, 'synthetic-reviewer')

    def accept(self, index=0, claim_id='explicit-claim-1'):
        claim = dict(copy.deepcopy(self.response['candidates'][index]), claim_id=claim_id)
        self.review['decisions'][index].update(decision='accept', review_note='Synthetic explicit adoption, not scientific approval.', reviewed_claim=claim)

    def packet(self): return proposals.review_proposals(self.package, self.bundle, self.review)
    def envelope(self): return proposals.export_reviewed(self.package, self.bundle, self.review)

    def test_empty_scope_is_template_only_no_automatic_selection(self):
        empty = proposals.template(self.package, 'Question?', 'Topic', 2020, 'operator')
        self.assertEqual(empty['evidence_refs'], [])
        self.assertEqual(empty['package_sha256'], payload_sha256(self.package))
        with self.assertRaisesRegex(ValueError, 'explicit references'): proposals.prepare_handoff(self.package, empty)
        self.assertEqual(set(self.handoff['response_contract']['candidate_fields']), proposals.PROPOSAL_FIELDS)
        self.assertEqual(len(self.handoff['evidence']), 2)
        self.assertNotIn('persona', self.handoff); self.assertNotIn('patterns', self.handoff)
        self.assertFalse(self.handoff['processing']['provider_invoked'])
        self.assertIn('untrusted data', ' '.join(self.handoff['instructions']))
        for year in (True, 0, 10000, 2020.0, float('nan')):
            with self.assertRaises(ValueError): proposals.template(self.package, 'Q', 'T', year, 'op')
        for key in ('question', 'topic', 'operator_id'):
            scope = copy.deepcopy(self.scope); scope[key] = ''
            with self.assertRaises(ValueError): proposals.prepare_handoff(self.package, scope)

    def test_scope_unique_exact_refs_and_full_package_binding(self):
        for refs in (self.scope['evidence_refs'] * 2, [dict(self.scope['evidence_refs'][0], observation_index=True)],
                     [dict(self.scope['evidence_refs'][0], dimension='absent')], [dict(self.scope['evidence_refs'][0], extra=1)],
                     self.scope['evidence_refs'] * 33):
            scope = dict(self.scope, evidence_refs=refs)
            with self.assertRaises((ValueError, TypeError)): proposals.prepare_handoff(self.package, scope)
        scope = dict(self.scope, package_sha256='0'*64)
        with self.assertRaises(ValueError): proposals.prepare_handoff(self.package, scope)
        scope = dict(self.scope, topic='Changed declared topic')
        with self.assertRaises(ValueError): proposals.response_template(self.package, scope, self.handoff)

    def test_wrapper_inner_equivalence_ignores_untrusted_summaries(self):
        wrapper = dict(package=self.package, cached_summary={'approval':'DO NOT TRUST'}, applications=['ignored'])
        scope = proposals.template(wrapper, self.scope['question'], self.scope['topic'], self.scope['reference_year'], self.scope['operator_id'])
        self.assertEqual(scope, dict(self.scope, evidence_refs=[]))
        self.assertEqual(proposals.prepare_handoff(wrapper, self.scope), self.handoff)
        self.assertEqual(proposals.validate_bundle(wrapper, self.bundle), self.bundle)
        self.accept(); envelope = self.envelope()
        self.assertEqual(proposals.inspect_reviewed(wrapper, envelope), proposals.inspect_reviewed(self.package, envelope))
        self.assertNotIn('DO NOT TRUST', json.dumps(self.handoff))

    def test_temporal_labels_and_mismatched_topic_do_not_filter_sources(self):
        for year, labels in ((2019,['AFTER_REFERENCE_YEAR','AFTER_REFERENCE_YEAR']),
                             (2020,['SAME_YEAR_ORDER_UNRESOLVED','AFTER_REFERENCE_YEAR']),
                             (2022,['BEFORE_REFERENCE_YEAR','BEFORE_REFERENCE_YEAR'])):
            scope = dict(self.scope, reference_year=year, topic='Explicit mismatched topic retained')
            handoff = proposals.prepare_handoff(self.package, scope)
            self.assertEqual([row['publication_scope'] for row in handoff['evidence']], labels)
            self.assertEqual(len(handoff['evidence']), 2)
        real_endpoint = proposals._endpoint
        for year in (True, 0, 10000, 2020.0):
            def changed_endpoint(ref, papers): return dict(real_endpoint(ref, papers), publication_year=year)
            with patch.object(proposals, '_endpoint', side_effect=changed_endpoint):
                with self.assertRaisesRegex(ValueError, 'publication year'): proposals.prepare_handoff(self.package, self.scope)

    def test_missing_stored_quote_cannot_be_imported(self):
        package = copy.deepcopy(self.package)
        package['knowledge']['papers'][1]['observations'][0]['reasoning']['falsification_check']['evidence_quote'] = None
        package['persona']['knowledge_papers_sha256'] = payload_sha256(package['knowledge']['papers'])
        package['knowledge']['persona_payload_sha256'] = payload_sha256(package['persona'])
        with self.assertRaises(ValueError): proposals.template(package, 'Q', 'T', 2020, 'operator')

    def test_default_defer_empty_and_missing_support_remain_prompts(self):
        self.assertEqual(self.review['decisions'][0]['decision'], 'defer')
        self.assertNotIn('reviewed_claim', self.review['decisions'][0])
        self.assertEqual(self.packet()['status'], 'ANSWER_PROPOSAL_REVIEW_INCOMPLETE')
        with self.assertRaisesRegex(ValueError, 'resolve every'): self.envelope()
        self.response['candidates'][0].update(citations=[], uncertainty=None)
        self.reimport()
        inspected = self.packet()['candidates'][0]['original_inspection']
        self.assertNotIn('claim_id', inspected)
        self.assertIn('NO_CITATIONS_SUPPLIED', inspected['review_prompts'])
        self.assertIn('UNCERTAINTY_NOT_SUPPLIED', inspected['review_prompts'])
        self.accept(); result = proposals.inspect_reviewed(self.package, self.envelope())
        self.assertEqual(result['claims'][0]['citations'], [])
        self.assertEqual(result['semantic_validation'], 'NOT_PERFORMED')
        self.assertNotIn('review', result)
        self.response['candidates'] = []; self.reimport()
        self.assertEqual(self.packet()['status'], 'NO_ACCEPTED_ANSWER_PROPOSALS')
        with self.assertRaises(ValueError): self.envelope()

    def test_exact_quotes_no_normalization_and_all_citations_in_scope(self):
        self.response['candidates'] = [copy.deepcopy(self.quote)]; self.reimport(); self.accept()
        self.assertEqual(proposals.inspect_reviewed(self.package, self.envelope())['claims'][0]['quote_check'], 'EQUALS_STORED_QUOTE_ONLY')
        for text in ('Invented.', self.quote['text']+' ', self.quote['text'][:-1]):
            self.response['candidates'][0]['text'] = text
            with self.assertRaises(ValueError): self.reimport()
        self.response['candidates'] = [copy.deepcopy(self.quote)]
        self.response['candidates'][0]['citations'] = []
        with self.assertRaises(ValueError): self.reimport()
        self.response['candidates'] = [copy.deepcopy(self.candidate)]
        self.response['candidates'][0]['citations'][0]['reference']['dimension'] = None
        with self.assertRaisesRegex(ValueError, 'scope reference'): self.reimport()
        self.response['candidates'] = [copy.deepcopy(self.candidate)]; self.reimport(); self.accept()
        self.review['decisions'][0]['reviewed_claim']['citations'][0]['reference']['dimension'] = None
        with self.assertRaisesRegex(ValueError, 'scope reference'): self.packet()

    def test_exact_candidate_fields_limits_and_no_model_decisions(self):
        for changes in ({'claim_id':'model-id'}, {'decision':'retain'}, {'claim_type':'author_claim'}, {'text':'x'*2001},
                        {'uncertainty':'x'*2001}, {'citations':self.candidate['citations']*17}):
            self.response['candidates'] = [dict(self.candidate, **changes)]
            with self.assertRaises(ValueError): self.reimport()
        for field in proposals.PROPOSAL_FIELDS:
            bad = copy.deepcopy(self.candidate); del bad[field]; self.response['candidates'] = [bad]
            with self.assertRaises(ValueError): self.reimport()
        self.response['candidates'] = [self.candidate]*33
        with self.assertRaises(ValueError): self.reimport()
        self.response['candidates'] = [dict(self.candidate, citations=[dict(self.candidate['citations'][0], role='approval')])]
        with self.assertRaises(ValueError): self.reimport()

    def test_accept_requires_explicit_full_claim_unique_ids_and_complete_review(self):
        self.review['decisions'][0]['decision'] = 'accept'
        with self.assertRaises(ValueError): self.packet()
        self.accept(); del self.review['decisions'][0]['reviewed_claim']['uncertainty']
        with self.assertRaises(ValueError): self.packet()
        self.accept(); self.review['decisions'][0]['decision'] = 'reject'
        with self.assertRaises(ValueError): self.packet()
        self.response['candidates'].append(copy.deepcopy(self.quote)); self.reimport(); self.accept(0); self.accept(1)
        with self.assertRaisesRegex(ValueError, 'unique'): self.packet()
        self.accept(1, 'explicit-claim-2'); self.assertEqual(self.packet()['accepted_count'], 2)
        self.review['decisions'].reverse()
        result = proposals.inspect_reviewed(self.package, self.envelope())
        self.assertEqual([c['claim_id'] for c in result['claims']], ['explicit-claim-1', 'explicit-claim-2'])
        self.review['decisions'][0]['candidate_id'] = self.review['decisions'][1]['candidate_id']
        with self.assertRaises(ValueError): self.packet()

    def test_original_rewritten_rejected_history_and_identity_preserved(self):
        self.response['candidates'].append(dict(self.quote, text=self.quote['text']))
        self.reimport(); self.accept()
        self.review['decisions'][0]['reviewed_claim'].update(text='Explicitly rewritten imported synthesis.', citations=[self.candidate['citations'][0]])
        self.review['decisions'][1].update(decision='reject', review_note='Rejected synthetic quotation.')
        envelope = self.envelope(); result = proposals.inspect_reviewed(self.package, envelope)
        self.assertEqual(result['draft_sha256'], payload_sha256(envelope))
        self.assertEqual(result['historical_model_use'], 'DECLARED_NOT_AUTHENTICATED')
        self.assertFalse(result['llm_used']); self.assertEqual(result['execution_scope'], 'CURRENT_INSPECTION_ONLY'); self.assertFalse(result['processing']['provider_invoked'])
        self.assertEqual(len(result['claims']), 1)
        self.assertEqual(len(result['claims'][0]['citations']), 1)
        self.assertEqual(result['claims'][0]['origin'], 'OPERATOR_ADOPTED_IMPORTED_SYNTHESIS')
        self.assertEqual(result['claims'][0]['proposal_origin']['original_proposal'], self.candidate)
        self.assertNotIn('review', result)
        self.assertNotIn('not model-generated answers', result['boundary'])
        rendered = proposals.render_review(result['proposal_review'])
        for text in ('Rejected synthetic quotation.', self.candidate['text'], 'Explicitly rewritten', 'synthetic-no-model', 'not authenticated'):
            self.assertIn(text, rendered)
        review2 = copy.deepcopy(self.review); review2['decisions'][1]['review_note'] = 'Changed rejection history.'
        result2 = proposals.inspect_reviewed(self.package, proposals.export_reviewed(self.package, self.bundle, review2))
        self.assertEqual(result['draft_content_sha256'], result2['draft_content_sha256'])
        self.assertNotEqual(result['draft_sha256'], result2['draft_sha256'])
        old_answer_review = dict(draft_sha256=result['draft_sha256'], reviewer_id='answer-reviewer', decisions=[dict(claim_id='explicit-claim-1', decision='retain', note='Synthetic only.')])
        with self.assertRaises(ValueError): answer_draft.review(self.package, proposals.export_reviewed(self.package, self.bundle, review2), old_answer_review)

    def test_tampering_stale_hashes_and_provenance_fail(self):
        self.accept()
        for mutate in (lambda b: b['candidates'][0].update(candidate_id='model-claim'),
                       lambda b: b['candidates'][0]['proposed_claim'].update(text='Tampered'),
                       lambda b: b['import_record'].update(response_sha256='0'*64),
                       lambda b: b['import_record']['provenance'].update(model_id='changed-model'),
                       lambda b: b['bindings'].update(scope_sha256='0'*64),
                       lambda b: b['scope'].update(topic='Changed scope'),
                       lambda b: b.update(boundary='Approved')):
            bundle = copy.deepcopy(self.bundle); mutate(bundle)
            with self.assertRaises(ValueError): proposals.validate_bundle(self.package, bundle)
        for changes in ({'model_id':''}, {'run_id':'x'*129}, {'execution_location':'somewhere'}, {'operator_id':'bad\noperator'}, {'unknown':'field'}):
            with self.assertRaises(ValueError): proposals.import_response(self.package, self.scope, self.handoff, self.response, dict(self.provenance, **changes))
        review = dict(self.review, proposal_bundle_sha256='0'*64)
        with self.assertRaises(ValueError): proposals.review_proposals(self.package, self.bundle, review)
        handoff = copy.deepcopy(self.handoff); handoff['instructions'] = []
        with self.assertRaises(ValueError): proposals.import_response(self.package, self.scope, handoff, self.response, self.provenance)

    def test_inputs_outputs_detached_and_finite(self):
        original = copy.deepcopy([self.package, self.scope, self.handoff, self.response, self.provenance, self.bundle, self.review])
        self.packet(); proposals.validate_bundle(self.package, self.bundle)
        self.assertEqual(original, [self.package, self.scope, self.handoff, self.response, self.provenance, self.bundle, self.review])
        returned = self.packet(); returned['scope']['question'] = 'Mutated output'; returned['candidates'][0]['candidate']['proposed_claim']['text'] = 'Mutated output'
        self.assertEqual(original, [self.package, self.scope, self.handoff, self.response, self.provenance, self.bundle, self.review])
        for value in (float('nan'), float('inf'), object()):
            with self.assertRaises(ValueError): proposals._inputs(value)
        with patch.object(proposals, 'MAX_INPUT_BYTES', 20):
            with self.assertRaisesRegex(ValueError, '8 MiB'): proposals.prepare_handoff(self.package, self.scope)
        with patch.object(proposals, 'MAX_HANDOFF_BYTES', 20):
            with self.assertRaisesRegex(ValueError, '2 MiB'): proposals.prepare_handoff(self.package, self.scope)
        with patch.object(proposals, 'MAX_OUTPUT_BYTES', 20):
            with self.assertRaisesRegex(ValueError, '16 MiB'): proposals.import_response(self.package, self.scope, self.handoff, self.response, self.provenance)
        cyclic = []; cyclic.append(cyclic)
        with self.assertRaises(ValueError): proposals._inputs(cyclic)

    def test_real_cli_roundtrip_strict_files_and_no_partial_stdout(self):
        self.accept()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            values = dict(package=self.package, scope=self.scope, handoff=self.handoff, response=self.response,
                provenance=self.provenance, bundle=self.bundle, review=self.review, envelope=self.envelope())
            for key, value in values.items(): (root/key).write_text(json.dumps(value))
            def run(command, *args):
                return subprocess.run([sys.executable, str(ROOT/'answer_proposals.py'), command, str(root/'package'), *map(str,args)], cwd=ROOT, capture_output=True)
            commands = [('template', ['--question','Q','--topic','T','--reference-year','2020','--operator-id','synthetic']),
                ('prepare',[root/'scope']), ('response-template',[root/'scope', root/'handoff']),
                ('import',[root/'scope', root/'handoff', root/'response', root/'provenance']),
                ('review-template',[root/'bundle','--reviewer-id','synthetic']),
                ('review',[root/'bundle',root/'review']), ('export',[root/'bundle',root/'review']), ('inspect',[root/'envelope'])]
            for command, args in commands:
                result = run(command,*args); self.assertEqual(result.returncode,0,result.stderr); self.assertIsInstance(json.loads(result.stdout),dict)
            result = run('review',root/'bundle',root/'review','--format','text')
            self.assertEqual(result.returncode,0,result.stderr); self.assertIn(b'NOT RESEARCHER ANSWERS',result.stdout)
            for bad in ('{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}', '{'):
                (root/'scope').write_text(bad); result = run('prepare',root/'scope')
                self.assertNotEqual(result.returncode,0); self.assertEqual(result.stdout,b'')
            (root/'scope').write_bytes(b' '*(proposals.MAX_INPUT_BYTES+1))
            result = run('prepare',root/'scope'); self.assertNotEqual(result.returncode,0); self.assertEqual(result.stdout,b'')


if __name__ == '__main__': unittest.main()
