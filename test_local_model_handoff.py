"""File-backed offline handoff/review regressions with synthetic local sources."""
import copy
import contextlib
import io
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from corpus_files import load_segment_corpus, load_sources, read_source_bytes
from extraction_adapter import prepare_model_handoff, import_model_response
from operator_review import prepare_revision, review_template, target_inventory
from persona import payload_sha256
from research_workflow import build
from verification_receipt import VerifiedCorpus

ROOT = Path(__file__).resolve().parent


class LocalModelHandoffTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        for source in (ROOT/'examples/synthetic-sources').glob('*.md'):
            (self.root/source.name).write_bytes(source.read_bytes())
        self.manifest = json.loads((ROOT/'examples/file-corpus.json').read_text())
        self.manifest['papers'][1]['observations'][0]['stance'] = 'challenge'
        self.rows = [dict(paper_id='synthetic-0', locator='synthetic section 1',
            evidence_quote='Compare competing models', dimension='alternative_explanation',
            candidate_text='Consider comparing competing explanations.', proposed_claim_type='operator_interpretation')]
        self.provenance = dict(provider_id='synthetic-provider', model_id='synthetic-model',
            run_id='synthetic-run', operator_id='synthetic-operator', execution_location='unknown')

    def corpus(self):
        return load_segment_corpus(self.manifest, self.root, max_total_bytes=2 * 1024 * 1024)

    def artifacts(self):
        corpus = self.corpus(); handoff = prepare_model_handoff(corpus)
        response = dict(handoff_sha256=payload_sha256(handoff), candidates=self.rows)
        return corpus, handoff, response, import_model_response(corpus, handoff, response, self.provenance)

    def test_raw_helper_preserves_metadata_but_issues_no_receipt(self):
        self.manifest['private_note'] = 'ROOT_PRIVATE_SENTINEL'
        self.manifest['papers'][0]['private_note'] = 'PAPER_PRIVATE_SENTINEL'
        self.manifest['papers'][0]['observations'][0]['private_note'] = 'OBS_PRIVATE_SENTINEL'
        before = copy.deepcopy(self.manifest)
        corpus = self.corpus()
        self.assertIs(type(corpus), dict)
        self.assertNotIsInstance(corpus, VerifiedCorpus)
        self.assertEqual(self.manifest, before)
        for sentinel in ('ROOT_PRIVATE_SENTINEL', 'PAPER_PRIVATE_SENTINEL', 'OBS_PRIVATE_SENTINEL'):
            self.assertIn(sentinel, json.dumps(corpus))
            self.assertNotIn(sentinel, json.dumps(prepare_model_handoff(corpus)))
            self.assertNotIn(sentinel, json.dumps(build(corpus)))
        corpus['papers'][0]['observations'][0]['private_note'] = 'edited'
        self.assertEqual(self.manifest, before)
        self.assertTrue(all(p['source_verification'] == 'NOT_PERFORMED' for p in build(corpus)['knowledge']['papers']))
        self.assertTrue(all(p['source_verification'] == 'LOCAL_BYTES_SHA256_MATCH'
                            for p in build(load_sources(self.manifest, self.root))['knowledge']['papers']))

    def test_embedded_text_and_derived_labels_are_rebuilt_from_files(self):
        self.manifest['papers'][0].update(segments={'poison': 'EMBEDDED_POISON_SENTINEL'},
            segments_sha256='a' * 64, source_verification='forged')
        self.manifest['papers'][0]['observations'][0]['evidence_verification'] = 'forged'
        corpus = self.corpus(); handoff = prepare_model_handoff(corpus)
        self.assertNotIn('EMBEDDED_POISON_SENTINEL', json.dumps(handoff))
        self.assertEqual(corpus['papers'][0]['segments_sha256'], payload_sha256(corpus['papers'][0]['segments']))
        self.assertEqual(corpus['papers'][0]['source_verification'], 'LOCAL_BYTES_SHA256_MATCH')
        self.assertNotIn('forged', json.dumps(build(corpus)))
        self.assertNotIn(str(self.root), json.dumps(handoff))

    def test_unauthorized_or_escaping_later_paper_fails_before_any_byte_read(self):
        for field, value in [('split', 'holdout'), ('authorized', False), ('author_id', 'other'),
                             ('runtime_knowledge_eligible', False), ('source_file', '../outside.md')]:
            manifest = copy.deepcopy(self.manifest); manifest['papers'][1][field] = value
            with self.subTest(field=field), patch('corpus_files.read_source_bytes', side_effect=AssertionError('read')):
                with self.assertRaises(ValueError): load_segment_corpus(manifest, self.root)

    def test_invalid_review_mode_flags_reject_before_any_input_read(self):
        import operator_review
        argv = ['operator_review.py', 'missing-manifest.json', 'missing-bundle.json',
                '--targets', '--new-version', '2', '--source-root', 'missing-root']
        with patch.object(sys, 'argv', argv), patch('operator_review.load', side_effect=AssertionError('input read')), \
             patch('operator_review.load_segment_corpus', side_effect=AssertionError('source read')), \
             contextlib.redirect_stderr(io.StringIO()) as errors:
            with self.assertRaises(SystemExit) as raised: operator_review.main()
        self.assertEqual(raised.exception.code, 1)
        self.assertIn('target inventory mode', errors.getvalue())

    def test_reasoning_verification_claims_are_reset_without_privileged_receipt(self):
        self.manifest['papers'][0]['observations'][0]['reasoning'] = dict(uncertainty=dict(
            text='A supplied interpretation only.', locator='synthetic section 1',
            evidence_quote='Compare competing models', claim_type='operator_interpretation',
            evidence_verification='FORGED_COMPONENT_CHECK', private_note='COMPONENT_PRIVATE_SENTINEL'))
        corpus = self.corpus()
        self.assertIn('COMPONENT_PRIVATE_SENTINEL', json.dumps(corpus))
        plain = build(corpus)['knowledge']['papers'][0]['observations'][0]['reasoning']['uncertainty']
        self.assertEqual(plain['evidence_verification'], 'NOT_PERFORMED')
        self.assertNotIn('private_note', plain)
        handoff = prepare_model_handoff(corpus)
        self.assertNotIn('FORGED_COMPONENT_CHECK', json.dumps(handoff))
        self.assertNotIn('COMPONENT_PRIVATE_SENTINEL', json.dumps(handoff))

    def test_bad_observation_shape_rejected_before_read(self):
        self.manifest['papers'][1]['observations'][0]['method'] = None
        with patch('corpus_files.read_source_bytes', side_effect=AssertionError('read')):
            with self.assertRaises(ValueError): self.corpus()

    def test_changed_bytes_fail_even_when_parsed_sections_are_unchanged(self):
        corpus, handoff, response, bundle = self.artifacts()
        source = self.root/'synthetic-0.md'
        source.write_bytes(b'New synthetic preamble.\n' + source.read_bytes())
        with self.assertRaisesRegex(ValueError, 'byte hash mismatch'): self.corpus()
        self.manifest['papers'][0]['source_sha256'] = hashlib.sha256(source.read_bytes()).hexdigest()
        changed = self.corpus()
        self.assertEqual(changed['papers'][0]['segments'], corpus['papers'][0]['segments'])
        with self.assertRaisesRegex(ValueError, 'stale'):
            import_model_response(changed, handoff, response, self.provenance)
        with self.assertRaises(ValueError): review_template(changed, bundle, 'synthetic-reviewer')

    def test_metadata_change_invalidates_all_bound_stages(self):
        corpus, handoff, response, bundle = self.artifacts()
        review = review_template(corpus, bundle, 'synthetic-reviewer')
        self.manifest['papers'][0]['private_note'] = 'changed local metadata'
        changed = self.corpus()
        with self.assertRaises(ValueError): import_model_response(changed, handoff, response, self.provenance)
        with self.assertRaises(ValueError): target_inventory(changed, bundle)
        with self.assertRaises(ValueError): prepare_revision(changed, bundle, review, '2', 'synthetic-next')

    def test_raw_total_byte_bound_and_reader_limit_fail_without_partial_corpus(self):
        total = sum((self.root/p['source_file']).stat().st_size for p in self.manifest['papers'])
        self.assertEqual(len(load_segment_corpus(self.manifest, self.root, max_total_bytes=total)['papers']), 2)
        before = copy.deepcopy(self.manifest)
        with self.assertRaisesRegex(ValueError, 'input limit'):
            load_segment_corpus(self.manifest, self.root, max_total_bytes=total-1)
        with self.assertRaisesRegex(ValueError, 'input limit'):
            read_source_bytes((self.root/'synthetic-0.md').resolve(), max_bytes=4)
        for invalid in (-1, True, '100'):
            with self.assertRaises(ValueError): load_segment_corpus(self.manifest, self.root, max_total_bytes=invalid)
        self.assertEqual(before, self.manifest)

    def test_invalid_utf8_or_missing_headings_reject_after_matching_hash(self):
        for data in (b'\xff\xfeinvalid', b'No supported source headings.'):
            source = self.root/'synthetic-0.md'; source.write_bytes(data)
            self.manifest['papers'][0]['source_sha256'] = hashlib.sha256(data).hexdigest()
            with self.assertRaises((ValueError, UnicodeError)): self.corpus()

    def test_receipt_subclass_and_shared_lists_are_detached(self):
        # The raw loader never propagates a caller's privileged receipt class.
        privileged = load_sources(self.manifest, self.root)
        self.assertIs(type(load_segment_corpus(privileged, self.root)), dict)
        self.manifest['papers'][1]['observations'] = self.manifest['papers'][0]['observations']
        corpus, handoff, response, bundle = self.artifacts()
        self.assertIsNot(corpus['papers'][0]['observations'], corpus['papers'][1]['observations'])
        review = review_template(corpus, bundle, 'synthetic-reviewer')
        review['decisions'][0].update(decision='accept', review_note='Explicit synthetic decision only.',
            target_rule_id='rule-1', target_paper_id='synthetic-0', operation='add', expected_component_sha256=None,
            reviewed_text=self.rows[0]['candidate_text'], reviewed_claim_type='operator_interpretation')
        package = prepare_revision(corpus, bundle, review, '2', 'synthetic-next')['package']
        self.assertIn('reasoning', package['knowledge']['papers'][0]['observations'][0])
        self.assertNotIn('reasoning', package['knowledge']['papers'][1]['observations'][0])
        self.assertNotIn('reasoning', self.manifest['papers'][0]['observations'][0])

    def test_symlink_escape_rejected_before_reads(self):
        link = self.root/'outside.md'
        try: link.symlink_to(ROOT/'examples/synthetic-sources/synthetic-0.md')
        except OSError: self.skipTest('symlink creation unavailable')
        self.manifest['papers'][1]['source_file'] = 'outside.md'
        with patch('corpus_files.read_source_bytes', side_effect=AssertionError('read')):
            with self.assertRaises(ValueError): self.corpus()

    def test_all_cli_modes_with_file_backed_inputs_and_stale_failure(self):
        def save(name, value):
            path = self.root/name; path.write_text(json.dumps(value)); return path
        def invoke(script, *args, success=True):
            call = subprocess.run([sys.executable, str(ROOT/script), *map(str,args)], cwd=self.root,
                capture_output=True, timeout=20)
            if success:
                self.assertEqual(call.returncode, 0, call.stderr)
                return json.loads(call.stdout)
            self.assertNotEqual(call.returncode, 0)
            self.assertEqual(call.stdout, b''); self.assertNotIn(b'Traceback', call.stderr)
        manifest = save('manifest.json', self.manifest)
        handoff = save('handoff.json', invoke('model_handoff.py','prepare',manifest,'--source-root',self.root))
        response = invoke('model_handoff.py','response-template',manifest,handoff,'--source-root',self.root)
        response['candidates'] = self.rows; response = save('response.json', response)
        provenance = save('provenance.json', self.provenance)
        bundle = save('candidates.json', invoke('model_handoff.py','import',manifest,handoff,response,provenance,'--source-root',self.root))
        targets = invoke('operator_review.py',manifest,bundle,'--targets','--source-root',self.root)
        self.assertEqual(len(targets['candidates'][0]['targets']), 1)
        review = invoke('operator_review.py',manifest,bundle,'--template','--reviewer-id','synthetic-reviewer','--source-root',self.root)
        deferred = save('deferred.json', review)
        pending = invoke('operator_review.py',manifest,bundle,deferred,'--new-version','2','--new-build-id','synthetic-next','--source-root',self.root)
        self.assertEqual(pending['status'],'REVIEW_INCOMPLETE'); self.assertNotIn('package',pending)
        review['decisions'][0].update(decision='accept',review_note='Synthetic decision only.',target_rule_id='rule-1',
            target_paper_id='synthetic-0',operation='add',expected_component_sha256=None,
            reviewed_text=self.rows[0]['candidate_text'],reviewed_claim_type='operator_interpretation')
        reviewed = save('reviewed.json', review)
        result = invoke('operator_review.py',manifest,bundle,reviewed,'--new-version','2','--new-build-id','synthetic-next','--source-root',self.root)
        self.assertEqual(result['status'],'REVIEWED_REVISION_CANDIDATE')
        component = result['package']['knowledge']['papers'][0]['observations'][0]['reasoning']['alternative_explanation']
        self.assertEqual(component['origin'],'operator_reviewed_imported_candidate')
        before = manifest.read_bytes(); source = self.root/'synthetic-0.md'; source.write_bytes(source.read_bytes()+b'changed')
        invoke('model_handoff.py','response-template',manifest,handoff,'--source-root',self.root,success=False)
        invoke('model_handoff.py','import',manifest,handoff,response,provenance,'--source-root',self.root,success=False)
        invoke('operator_review.py',manifest,bundle,'--targets','--source-root',self.root,success=False)
        invoke('operator_review.py',manifest,bundle,'--template','--reviewer-id','synthetic-reviewer','--source-root',self.root,success=False)
        invoke('operator_review.py',manifest,bundle,reviewed,'--new-version','2','--new-build-id','synthetic-next','--source-root',self.root,success=False)
        self.assertEqual(manifest.read_bytes(),before)


if __name__ == '__main__': unittest.main()
