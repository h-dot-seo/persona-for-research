"""Synthetic offline model-pattern tests. No model/provider is invoked."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import tests.test_pattern_hypotheses as pattern_fixture
import tests.test_pattern_transfer_review as transfer_fixture
from persona import payload_sha256
from research_workflow import build
from observation_input import verified_corpus
from strict_json import load
from pattern_hypotheses import inspect as inspect_patterns, render as render_patterns
from pattern_transfer_review import inspect as inspect_transfer, render as render_transfer
from pattern_proposals import (prepare_handoff, response_template, import_response, validate_bundle,
    review_template, review_proposals, export_reviewed, render_review, ENVELOPE_SCHEMA)

ROOT = Path(__file__).resolve().parents[1]


class PatternProposalTests(unittest.TestCase):
    def setUp(self):
        fixture = pattern_fixture.PatternHypothesisTests(); fixture.setUp()
        self.package, self.manual = fixture.package, fixture.form
        self.a, self.b = fixture.a, fixture.b
        self.proposal = dict(proposed_hypothesis=fixture.h['operator_hypothesis'],
            **{key: copy.deepcopy(value) for key, value in fixture.h.items()
               if key not in ('pattern_id', 'operator_hypothesis')})
        self.provenance = dict(provider_id='synthetic-provider', model_id='synthetic-model',
            run_id='synthetic-run', operator_id='synthetic-generator', execution_location='local')
        self.handoff = prepare_handoff(self.package, 'model design')
        self.response = dict(handoff_sha256=payload_sha256(self.handoff), candidates=[self.proposal])
        self.bundle = import_response(self.package, self.handoff, self.response, self.provenance)
        self.review = review_template(self.package, self.bundle, 'synthetic-reviewer')

    def accept(self, index=0, pattern_id='comparison'):
        decision = self.review['decisions'][index]
        decision.update(decision='accept', review_note='Synthetic explicit decision, not scientific validation.',
            reviewed_pattern=dict(pattern_id=pattern_id, operator_hypothesis='A narrowed synthetic comparison pattern.',
                **{key: copy.deepcopy(value) for key, value in self.proposal.items() if key != 'proposed_hypothesis'}))

    def test_handoff_catalog_preserves_research_review_quotes_conditions_and_chronology(self):
        nodes = self.handoff['evidence_catalog']
        self.assertEqual([n['publication_year'] for n in nodes], [2020, 2021, 2021])
        self.assertEqual({n['source_kind'] for n in nodes}, {'research', 'review'})
        self.assertTrue(all(n['source_sha256'] and n['observation']['condition'] and n['observation']['limitation'] for n in nodes))
        self.assertEqual(nodes[-1]['component']['claim_type'], 'operator_interpretation')
        self.assertIn('missing_reasoning_dimensions', nodes[0])
        self.assertFalse(self.handoff['processing']['source_reread'])
        self.assertEqual(response_template(self.package, self.handoff)['candidates'], [])

    def test_topic_filter_is_exact_and_never_silently_reads_unselected_sources(self):
        missing = prepare_handoff(self.package, 'not present')
        self.assertEqual(missing['evidence_catalog'], [])
        response = dict(handoff_sha256=payload_sha256(missing), candidates=[self.proposal])
        with self.assertRaisesRegex(ValueError, 'outside'): import_response(self.package, missing, response, self.provenance)
        capitalized = prepare_handoff(self.package, 'MODEL DESIGN')
        self.assertEqual(capitalized['evidence_catalog'], self.handoff['evidence_catalog'])
        self.assertNotEqual(payload_sha256(capitalized), payload_sha256(self.handoff))

    def test_empty_default_defer_and_reject_never_export(self):
        packet = review_proposals(self.package, self.bundle, self.review)
        self.assertEqual(packet['status'], 'PATTERN_PROPOSAL_REVIEW_INCOMPLETE')
        self.assertFalse(packet['automatic_approval'])
        with self.assertRaises(ValueError): export_reviewed(self.package, self.bundle, self.review)
        self.review['decisions'][0].update(decision='reject', review_note='Unsupported proposed pattern.')
        with self.assertRaises(ValueError): export_reviewed(self.package, self.bundle, self.review)
        empty = import_response(self.package, self.handoff, response_template(self.package, self.handoff), self.provenance)
        review = review_template(self.package, empty, 'op')
        self.assertEqual(review_proposals(self.package, empty, review)['status'], 'NO_ACCEPTED_PATTERN_PROPOSALS')
        with self.assertRaises(ValueError): export_reviewed(self.package, empty, review)

    def test_accept_requires_complete_explicit_reviewed_fields_and_preserves_nulls(self):
        self.review['decisions'][0]['decision'] = 'accept'
        with self.assertRaises(ValueError): review_proposals(self.package, self.bundle, self.review)
        self.accept(); packet = review_proposals(self.package, self.bundle, self.review)
        row = packet['candidates'][0]
        self.assertEqual(row['original_inspection']['claim_type'], 'imported_proposal')
        self.assertEqual(row['reviewed_inspection']['claim_type'], 'operator_interpretation')
        self.assertNotEqual(row['original_inspection']['operator_hypothesis'], row['reviewed_inspection']['operator_hypothesis'])
        self.assertIsNone(row['reviewed_pattern']['falsification_check'])
        self.assertIn('FALSIFICATION_CHECK_NOT_SUPPLIED', row['reviewed_inspection']['review_prompts'])
        self.assertEqual(packet['status'], 'PATTERN_PROPOSALS_REVIEWED_NOT_APPROVED')
        self.assertFalse(packet['canonical_update_performed'])

    def test_complete_envelope_replays_and_keeps_origin_in_pattern_and_transfer(self):
        self.accept(); envelope = export_reviewed(self.package, self.bundle, self.review)
        result = inspect_patterns(self.package, envelope)
        self.assertEqual(result['form_sha256'], payload_sha256(envelope))
        self.assertNotEqual(result['form_sha256'], result['worksheet_content_sha256'])
        self.assertEqual(result['historical_model_use'], 'DECLARED_NOT_AUTHENTICATED')
        self.assertEqual(result['hypotheses'][0]['proposal_origin']['import_record']['provenance'], self.provenance)
        self.assertIn('synthetic-model', render_patterns(result))
        fixture = transfer_fixture.PatternTransferTests(); fixture.setUp()
        args = fixture.inputs(); args[1] = envelope
        transferred = inspect_transfer(*args)
        self.assertEqual(transferred['pattern_proposal_review']['review_sha256'], payload_sha256(self.review))
        self.assertIn('proposal_origin', transferred['selected_pattern'])
        self.assertIn('EXCLUDED_OBSERVATION_HAS_SHARED_DESIGN_REFERENCE', [p['code'] for p in transferred['trace_review_prompts']])
        self.assertIn('synthetic-model', render_transfer(*args))
        self.assertEqual(transferred['status'], 'PATTERN_TRANSFER_REQUIRES_MANUAL_REVIEW')

    def test_rejected_challenge_and_changed_reference_roles_remain_visible(self):
        second = copy.deepcopy(self.proposal); second['proposed_hypothesis'] = 'Rejected synthetic alternative.'
        self.response['candidates'].append(second)
        self.bundle = import_response(self.package, self.handoff, self.response, self.provenance)
        self.review = review_template(self.package, self.bundle, 'reviewer'); self.accept()
        with self.assertRaises(ValueError): export_reviewed(self.package, self.bundle, self.review)
        self.review['decisions'][1].update(decision='reject', review_note='The proposed interpretation was not supported.')
        # Explicit review can change catalog uses, but both original and reviewed routes survive.
        reviewed = self.review['decisions'][0]['reviewed_pattern']
        reviewed.update(support_refs=[self.a], challenge_refs=[self.b])
        result = inspect_patterns(self.package, export_reviewed(self.package, self.bundle, self.review))
        self.assertEqual(len(result['hypotheses']), 1)
        self.assertEqual(len(result['proposal_review']['candidates']), 2)
        text = render_patterns(result)
        self.assertIn('Rejected synthetic alternative.', text)
        self.assertIn('decision=reject', text)
        self.assertIn('SUPPORT_FROM_FEWER_THAN_TWO_PAPER_IDS', text)
        self.assertEqual(result['hypotheses'][0]['proposal_origin']['original_proposal']['support_refs'], self.proposal['support_refs'])

    def test_two_paper_minimum_and_nonindependence_warning(self):
        row = copy.deepcopy(self.proposal); row.update(support_refs=[self.a], challenge_refs=[])
        response = dict(self.response, candidates=[row])
        with self.assertRaisesRegex(ValueError, 'two distinct'): import_response(self.package, self.handoff, response, self.provenance)
        corpus = load(ROOT/'examples/observed-corpus.json')
        corpus['papers'][1]['source_sha256'] = corpus['papers'][0]['source_sha256']
        package = build(verified_corpus(corpus)); handoff = prepare_handoff(package, 'model design')
        row.update(challenge_refs=[dict(self.b, dimension=None)])
        bundle = import_response(package, handoff, dict(handoff_sha256=payload_sha256(handoff), candidates=[row]), self.provenance)
        self.assertIn('MULTIPLE_PAPER_IDS_SHARE_SOURCE_HASH', bundle['candidates'][0]['review_prompts'])

    def test_missing_quotes_are_visible_not_fabricated_or_rechecked(self):
        corpus = load(ROOT/'examples/research-corpus.json')
        package = build(corpus); handoff = prepare_handoff(package, 'model design')
        row = copy.deepcopy(self.proposal); row.update(support_refs=[self.a, dict(self.b, dimension=None)], challenge_refs=[])
        bundle = import_response(package, handoff, dict(handoff_sha256=payload_sha256(handoff), candidates=[row]), self.provenance)
        self.assertIn('REFERENCES_WITHOUT_SUPPLIED_QUOTES', bundle['candidates'][0]['review_prompts'])
        packet = review_proposals(package, bundle, review_template(package, bundle, 'op'))
        self.assertEqual(len(packet['candidates'][0]['original_inspection']['references_without_supplied_quotes']), 2)
        self.assertIn('NOT_PERFORMED', render_review(packet))

    def test_unknown_duplicate_bool_or_wrong_dimension_references_reject(self):
        mutations = [lambda r:r.update(paper_id='invented'), lambda r:r.update(observation_index=True),
            lambda r:r.update(dimension='invented'), lambda r:r.update(extra='not allowed')]
        for mutate in mutations:
            response = copy.deepcopy(self.response); mutate(response['candidates'][0]['support_refs'][0])
            with self.assertRaises(ValueError): import_response(self.package, self.handoff, response, self.provenance)
        response = copy.deepcopy(self.response); response['candidates'][0]['support_refs'].append(copy.deepcopy(self.a))
        with self.assertRaises(ValueError): import_response(self.package, self.handoff, response, self.provenance)

    def test_stale_handoff_bundle_provenance_review_and_projection_reject(self):
        self.accept()
        for mutate in (lambda b:b.update(status='APPROVED'),
                       lambda b:b['candidates'][0].update(candidate_id='different'),
                       lambda b:b['import_record'].update(response_sha256='0'*64),
                       lambda b:b['provider'].update(llm_used=False)):
            bundle = copy.deepcopy(self.bundle); mutate(bundle)
            with self.assertRaises(ValueError): validate_bundle(self.package, bundle)
        handoff = copy.deepcopy(self.handoff); handoff['instructions'] = []
        with self.assertRaises(ValueError): import_response(self.package, handoff, self.response, self.provenance)
        envelope = export_reviewed(self.package, self.bundle, self.review); envelope['accepted_form'] = self.manual
        with self.assertRaises(ValueError): inspect_patterns(self.package, envelope)
        envelope = export_reviewed(self.package, self.bundle, self.review)
        envelope['bundle']['import_record']['provenance']['model_id'] = 'different-model'
        with self.assertRaises(ValueError): inspect_patterns(self.package, envelope)
        # A newly self-consistent declaration is a new bundle, not authenticated history.
        provenance = dict(self.provenance, model_id='different-model')
        bundle = import_response(self.package, self.handoff, self.response, provenance)
        with self.assertRaises(ValueError): review_proposals(self.package, bundle, self.review)

    def test_full_package_metadata_binds_even_when_omitted_from_projection(self):
        package = copy.deepcopy(self.package); package['private_annotation'] = 'synthetic metadata sentinel'
        handoff = prepare_handoff(package, 'model design')
        self.assertNotIn('synthetic metadata sentinel', json.dumps(handoff))
        self.assertNotEqual(payload_sha256(handoff), payload_sha256(self.handoff))
        with self.assertRaises(ValueError): validate_bundle(package, self.bundle)
        with self.assertRaises(ValueError): import_response(package, self.handoff, self.response, self.provenance)

    def test_full_authorization_and_year_preflight_before_topic_filter(self):
        for field, value in [('authorized', False), ('split', 'holdout'), ('author_id', 'other'), ('year', 0)]:
            package = copy.deepcopy(self.package); package['knowledge']['papers'][1][field] = value
            with self.assertRaises(ValueError): prepare_handoff(package, 'not present')
        envelope = dict(schema=ENVELOPE_SCHEMA, bundle=self.bundle, review=self.review)
        with self.assertRaises(ValueError): inspect_patterns(self.package, envelope)

    def test_bounds_extra_fields_and_declared_provenance(self):
        for mutate in (lambda r:r.update(candidates=[self.proposal]*33),
                       lambda r:r['candidates'][0].update(support_refs=[self.a]*33),
                       lambda r:r['candidates'][0].update(proposed_hypothesis='x'*2001),
                       lambda r:r['candidates'][0].update(claim_type='author_statement'),
                       lambda r:r.update(approved=True)):
            response = copy.deepcopy(self.response); mutate(response)
            with self.assertRaises(ValueError): import_response(self.package, self.handoff, response, self.provenance)
        for field, value in [('execution_location','unverified-location'), ('model_id','bad\nmodel')]:
            with self.assertRaises(ValueError): import_response(self.package, self.handoff, self.response, dict(self.provenance, **{field:value}))
        with patch('pattern_proposals.MAX_HANDOFF_BYTES', 20):
            with self.assertRaisesRegex(ValueError, '2 MiB'): prepare_handoff(self.package, 'model design')

    def test_duplicate_or_missing_decisions_and_pattern_ids_reject(self):
        self.response['candidates'] = [self.proposal, copy.deepcopy(self.proposal)]
        self.bundle = import_response(self.package, self.handoff, self.response, self.provenance)
        self.review = review_template(self.package, self.bundle, 'reviewer'); self.accept(0); self.accept(1)
        with self.assertRaisesRegex(ValueError, 'duplicate reviewed'): review_proposals(self.package, self.bundle, self.review)
        self.review['decisions'][1] = copy.deepcopy(self.review['decisions'][0])
        with self.assertRaisesRegex(ValueError, 'duplicate pattern decision'): review_proposals(self.package, self.bundle, self.review)
        self.review['decisions'].pop()
        with self.assertRaises(ValueError): review_proposals(self.package, self.bundle, self.review)

    def test_deterministic_deep_copies_no_model_source_or_network(self):
        self.accept(); before = copy.deepcopy((self.package, self.handoff, self.response, self.bundle, self.review))
        with patch('socket.socket', side_effect=AssertionError('no network')), patch('pathlib.Path.open', side_effect=AssertionError('no source open')):
            envelope = export_reviewed(self.package, self.bundle, self.review)
            result = inspect_patterns(self.package, envelope)
            self.assertEqual(result, inspect_patterns(self.package, envelope))
        result['proposal_review']['candidates'][0]['original_inspection']['evidence'][0]['evidence']['observation']['method'] = 'changed'
        envelope['review']['decisions'][0]['review_note'] = 'changed'
        self.assertEqual(before, (self.package, self.handoff, self.response, self.bundle, self.review))

    def test_render_escapes_untrusted_text_and_keeps_historical_scope(self):
        self.response['candidates'][0]['proposed_hypothesis'] = 'Synthetic text\x1b[2J\nNot a real scholar quote.'
        self.bundle = import_response(self.package, self.handoff, self.response, self.provenance)
        self.review = review_template(self.package, self.bundle, 'reviewer'); self.accept()
        text = render_patterns(inspect_patterns(self.package, export_reviewed(self.package, self.bundle, self.review)))
        self.assertNotIn('\x1b', text); self.assertIn('Not a real scholar quote.', text)
        self.assertIn('unauthenticated', text); self.assertIn('synthetic-model', text)

    def test_existing_manual_schema_and_render_stay_manual(self):
        result = inspect_patterns(self.package, self.manual)
        self.assertNotIn('proposal_review', result)
        self.assertNotIn('proposal_origin', result['hypotheses'][0])
        self.assertNotIn('synthetic-model', render_patterns(result))
        with self.assertRaises(ValueError): inspect_patterns(self.package, self.bundle)
        self.accept()
        with self.assertRaises(ValueError): build(export_reviewed(self.package, self.bundle, self.review))

    def test_actual_cli_full_handoff_review_export_pattern_and_transfer(self):
        self.accept()
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            def save(name, value):
                path = folder/(name+'.json'); path.write_text(json.dumps(value), encoding='utf-8'); return path
            pp = save('package', self.package); hp = save('handoff', self.handoff); rp = save('response', self.response)
            provenance = save('provenance', self.provenance); bp = save('bundle', self.bundle); rv = save('review', self.review)
            before = {p.name:p.read_bytes() for p in folder.iterdir()}
            def run(script, *arguments, valid=True):
                completed = subprocess.run([sys.executable, str(ROOT/script), *map(str, arguments)], cwd=folder,
                    capture_output=True, text=True, timeout=30)
                if valid: self.assertEqual(completed.returncode, 0, completed.stderr)
                else: self.assertNotEqual(completed.returncode, 0); self.assertEqual(completed.stdout, '')
                return completed.stdout
            self.assertEqual(json.loads(run('pattern_proposals.py','prepare',pp,'--topic','model design')), self.handoff)
            self.assertEqual(json.loads(run('pattern_proposals.py','response-template',pp,hp))['candidates'], [])
            self.assertEqual(json.loads(run('pattern_proposals.py','import',pp,hp,rp,provenance)), self.bundle)
            deferred = json.loads(run('pattern_proposals.py','review-template',pp,bp,'--reviewer-id','op'))
            dp = save('deferred', deferred); run('pattern_proposals.py','export',pp,bp,dp,valid=False)
            self.assertIn('synthetic-model', run('pattern_proposals.py','review',pp,bp,rv,'--format','text'))
            envelope = json.loads(run('pattern_proposals.py','export',pp,bp,rv)); ep = save('envelope', envelope)
            self.assertIn('synthetic-model', run('pattern_hypotheses.py',pp,ep,'--format','text'))
            fixture = transfer_fixture.PatternTransferTests(); fixture.setUp()
            paths = [pp, ep] + [save(name, value) for name, value in zip(('context','links','proposal','draft'),fixture.inputs()[2:-1])]
            self.assertIn('synthetic-model', run('pattern_transfer_review.py',*paths,'--pattern-id','comparison','--format','text'))
            for name, content in before.items(): self.assertEqual((folder/name).read_bytes(), content)
            bad = folder/'bad.json'; bad.write_text('{"topic":"x","topic":"y"}')
            run('pattern_proposals.py','response-template',pp,bad,valid=False)
            bad.write_text('{"topic":NaN}')
            run('pattern_proposals.py','response-template',pp,bad,valid=False)
            bad.write_bytes(b' '*(8*1024*1024+1))
            run('pattern_proposals.py','response-template',pp,bad,valid=False)


if __name__ == '__main__': unittest.main()
