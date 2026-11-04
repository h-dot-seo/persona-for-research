"""Synthetic declared evidence-use explanations, not semantic entailment tests."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import test_pattern_proposals as proposal_fixture
import test_pattern_transfer_review as transfer_fixture
from persona import payload_sha256
from pattern_proposals import (prepare_handoff, import_response, validate_bundle, review_template,
    review_proposals, export_reviewed, render_review)
from pattern_hypotheses import inspect, render
from pattern_transfer_review import inspect as inspect_transfer, render as render_transfer

ROOT = Path(__file__).resolve().parent


class PatternEvidenceReasonTests(unittest.TestCase):
    def setUp(self):
        fixture = proposal_fixture.PatternProposalTests(); fixture.setUp()
        self.package, self.provenance = fixture.package, fixture.provenance
        self.a, self.b = fixture.a, fixture.b
        self.proposal = copy.deepcopy(fixture.proposal)
        self.proposal['evidence_uses'] = [dict(reference=copy.deepcopy(ref), role=role,
            rationale='Model proposed '+role+' bridge for '+ref['paper_id']+'.', context_boundary=None)
            for key, role in [('support_refs','support'),('challenge_refs','challenge')] for ref in self.proposal[key]]
        self.handoff = prepare_handoff(self.package, 'model design', include_evidence_reasons=True)
        self.response = dict(handoff_sha256=payload_sha256(self.handoff), candidates=[self.proposal])
        self.reimport()

    def reimport(self):
        self.bundle = import_response(self.package, self.handoff, self.response, self.provenance)
        self.review = review_template(self.package, self.bundle, 'synthetic-reviewer')

    def accept(self):
        pattern = dict(pattern_id='comparison', operator_hypothesis='Explicit reviewed comparison hypothesis.',
            **{key:copy.deepcopy(value) for key,value in self.proposal.items() if key!='proposed_hypothesis'})
        for use in pattern['evidence_uses']:
            use['rationale'] = 'Reviewer supplied '+use['role']+' explanation for '+use['reference']['paper_id']+'.'
        self.review['decisions'][0].update(decision='accept', review_note='Explicit synthetic explanation review.', reviewed_pattern=pattern)
        return pattern

    def test_version_two_contract_requires_role_specific_explanations(self):
        self.assertEqual(self.handoff['schema'], 'persona.pattern-handoff.v2')
        self.assertEqual(self.bundle['schema'], 'persona.pattern-proposals.v2')
        self.assertIn('evidence_uses', self.handoff['response_contract']['candidate_fields'])
        packet = review_proposals(self.package, self.bundle, self.review)
        original = packet['candidates'][0]['original_inspection']
        self.assertEqual(len(original['evidence_use_gaps']), 3)
        self.assertTrue(all(gap['role'] in ('support','challenge') for gap in original['evidence_use_gaps']))
        self.assertEqual(original['evidence_use_validation'], 'REFERENCE_ROLE_COVERAGE_ONLY_NOT_SEMANTIC_SUPPORT')
        self.assertEqual(packet['status'], 'PATTERN_PROPOSAL_REVIEW_INCOMPLETE')
        self.assertIn('Context boundary: NOT_SUPPLIED', render_review(packet))

    def test_original_and_reviewed_reasons_survive_pattern_and_context_transfer(self):
        self.accept(); envelope = export_reviewed(self.package, self.bundle, self.review)
        result = inspect(self.package, envelope)
        selected = result['hypotheses'][0]
        self.assertEqual(len(selected['evidence_use_gaps']), 3)
        self.assertIn('EVIDENCE_USE_CONTEXT_BOUNDARY_NOT_SUPPLIED', selected['review_prompts'])
        self.assertTrue(all('Reviewer supplied' in use['rationale'] for row in selected['evidence'] for use in row['evidence_uses']))
        self.assertTrue(all('Model proposed' in use['rationale'] for use in selected['proposal_origin']['original_proposal']['evidence_uses']))
        fixture = transfer_fixture.PatternTransferTests(); fixture.setUp(); args = fixture.inputs(); args[1] = envelope
        transferred = inspect_transfer(*args)
        self.assertEqual(sum(len(row['pattern_evidence_uses']) for row in transferred['evidence_routes']), 3)
        self.assertEqual(sum(len(row['pattern_evidence_use_gaps']) for row in transferred['evidence_routes']), 3)
        self.assertIn('PATTERN_EVIDENCE_USE_CONTEXT_BOUNDARY_NOT_SUPPLIED', [prompt['code'] for prompt in transferred['trace_review_prompts']])
        text = render_transfer(*args)
        for phrase in ['Model proposed', 'Reviewer supplied', '[imported_proposal]', '[operator_interpretation]',
                       'EXCLUDED_OBSERVATION_HAS_SHARED_DESIGN_REFERENCE', 'Context boundary: NOT_SUPPLIED']:
            self.assertIn(phrase, text)
        self.assertFalse(transferred['llm_used'])

    def test_same_reference_both_roles_needs_two_separate_uses(self):
        self.proposal['challenge_refs'].append(copy.deepcopy(self.a))
        with self.assertRaisesRegex(ValueError, 'exactly one'): self.reimport()
        self.proposal['evidence_uses'].append(dict(reference=copy.deepcopy(self.a), role='challenge',
            rationale='A separate synthetic counterargument using the same source.', context_boundary='A different comparison scope.'))
        self.reimport(); self.accept()
        report = inspect(self.package, export_reviewed(self.package, self.bundle, self.review))
        row = next(row for row in report['hypotheses'][0]['evidence'] if row['evidence']['reference']==self.a)
        self.assertEqual([use['role'] for use in row['evidence_uses']], ['support','challenge'])
        self.assertIn('SAME_REFERENCE_DECLARED_IN_BOTH_ROLES', report['hypotheses'][0]['review_prompts'])

    def test_missing_duplicate_extraneous_and_wrong_role_pairs_reject(self):
        for mutate in (lambda uses:uses.pop(), lambda uses:uses.append(copy.deepcopy(uses[0])),
                       lambda uses:uses.__setitem__(1,copy.deepcopy(uses[0])),
                       lambda uses:uses[0].update(role='challenge'),
                       lambda uses:uses[0]['reference'].update(paper_id='unknown'),
                       lambda uses:uses[0]['reference'].update(observation_index=True),
                       lambda uses:uses[0]['reference'].update(extra='unknown'),
                       lambda uses:uses[0].update(role='author_claim')):
            response = copy.deepcopy(self.response); mutate(response['candidates'][0]['evidence_uses'])
            with self.assertRaises(ValueError): import_response(self.package, self.handoff, response, self.provenance)

    def test_nonempty_bounded_reasons_and_explicit_nullable_boundary(self):
        for mutate in (lambda use:use.update(rationale=' '), lambda use:use.update(rationale='x'*2001),
                       lambda use:use.pop('context_boundary'), lambda use:use.update(context_boundary=''),
                       lambda use:use.update(context_boundary=False), lambda use:use.update(context_boundary='x'*2001),
                       lambda use:use.update(semantic_validation='PASS')):
            response = copy.deepcopy(self.response); mutate(response['candidates'][0]['evidence_uses'][0])
            with self.assertRaises(ValueError): import_response(self.package, self.handoff, response, self.provenance)
        self.proposal['evidence_uses'][0]['context_boundary'] = 'Only when a discriminating measurement is available.'
        self.reimport(); self.accept()
        report = inspect(self.package, export_reviewed(self.package, self.bundle, self.review))
        self.assertEqual(len(report['hypotheses'][0]['evidence_use_gaps']), 2)
        self.assertIn('discriminating measurement', render(report))

    def test_accepted_review_cannot_inherit_missing_reasons_or_leave_removed_role(self):
        pattern = self.accept(); pattern.pop('evidence_uses')
        with self.assertRaises(ValueError): review_proposals(self.package, self.bundle, self.review)
        pattern = self.accept(); pattern['challenge_refs'] = []
        with self.assertRaises(ValueError): review_proposals(self.package, self.bundle, self.review)
        pattern['evidence_uses'] = [use for use in pattern['evidence_uses'] if use['role']=='support']
        packet = review_proposals(self.package, self.bundle, self.review)
        original, reviewed = packet['candidates'][0]['original_inspection'], packet['candidates'][0]['reviewed_inspection']
        self.assertEqual(sum(len(r['evidence_uses']) for r in original['evidence']),3)
        self.assertEqual(sum(len(r['evidence_uses']) for r in reviewed['evidence']),2)
        self.assertIn('NO_CHALLENGE_REFERENCES_SUPPLIED',reviewed['review_prompts'])
        self.assertIn('Model proposed challenge', render_review(packet))

    def test_versions_cannot_downgrade_or_silently_add_reasons(self):
        bad = copy.deepcopy(self.handoff); bad['schema']='persona.pattern-handoff.v1'
        with self.assertRaises(ValueError): import_response(self.package,bad,self.response,self.provenance)
        bad = copy.deepcopy(self.bundle); bad['schema']='persona.pattern-proposals.v1'
        with self.assertRaises(ValueError): validate_bundle(self.package,bad)
        handoff = prepare_handoff(self.package,'model design')
        response = copy.deepcopy(self.response);response['handoff_sha256']=payload_sha256(handoff)
        with self.assertRaises(ValueError): import_response(self.package,handoff,response,self.provenance)
        response = copy.deepcopy(self.response);response['candidates'][0].pop('evidence_uses')
        with self.assertRaises(ValueError): import_response(self.package,self.handoff,response,self.provenance)
        with self.assertRaises(ValueError): prepare_handoff(self.package,'model design',include_evidence_reasons='true')

    def test_reason_changes_rebind_review_and_do_not_mutate_inputs(self):
        self.accept(); before = copy.deepcopy((self.package,self.bundle,self.review))
        report = inspect(self.package,export_reviewed(self.package,self.bundle,self.review))
        report['hypotheses'][0]['evidence'][0]['evidence_uses'][0]['rationale']='changed'
        self.assertEqual(before,(self.package,self.bundle,self.review))
        self.response['candidates'][0]['evidence_uses'][0]['rationale']='Different model explanation.'
        updated = import_response(self.package,self.handoff,self.response,self.provenance)
        with self.assertRaises(ValueError): review_proposals(self.package,updated,self.review)

    def test_reviewed_reason_changes_complete_transfer_identity_not_plain_projection(self):
        pattern=self.accept();before=export_reviewed(self.package,self.bundle,self.review)
        pattern['evidence_uses'][0]['rationale']='A different explicit reviewer explanation.'
        after=export_reviewed(self.package,self.bundle,self.review)
        a,b=inspect(self.package,before),inspect(self.package,after)
        self.assertEqual(a['worksheet_content_sha256'],b['worksheet_content_sha256'])
        self.assertNotEqual(a['form_sha256'],b['form_sha256'])
        fixture=transfer_fixture.PatternTransferTests();fixture.setUp();args=fixture.inputs()
        args[1]=before;first=inspect_transfer(*args)
        args[1]=after;second=inspect_transfer(*args)
        self.assertNotEqual(first['report_input_sha256'],second['report_input_sha256'])

    def test_rejected_reasons_are_retained_and_controls_escaped(self):
        rejected = copy.deepcopy(self.proposal);rejected['evidence_uses'][0]['rationale']='Rejected model reason\x1b[2J\nkept.'
        self.response['candidates'].append(rejected);self.reimport();self.accept()
        self.review['decisions'][1].update(decision='reject',review_note='This synthetic bridge is unsupported.')
        text=render(inspect(self.package,export_reviewed(self.package,self.bundle,self.review)))
        self.assertIn('Rejected model reason',text);self.assertIn('decision=reject',text);self.assertNotIn('\x1b',text)

    def test_v040_canonical_payload_and_text_snapshots_unchanged(self):
        fixture=proposal_fixture.PatternProposalTests();fixture.setUp();fixture.accept()
        packet=review_proposals(fixture.package,fixture.bundle,fixture.review)
        envelope=export_reviewed(fixture.package,fixture.bundle,fixture.review)
        report=inspect(fixture.package,envelope)
        # Captured from exact published v0.40 eca37da8, verified allowlisted snapshot.
        expected={'handoff':'2500211c1d83dd787b59b9a3b0fcbcead58f62ac2c8768692017624b0276f5f8',
          'bundle':'07388165a1e108773ef704870ea027d8d7b3b263462d28187616d662e1d759ae',
          'review':'ae499f9e843d2b8858df964e95d942a0366671001e4c0cc116a6a48b5c147078',
          'packet':'c5c0e89ba7f06ec163a1218b507e4d2e23d8294f1d9fe4e2a397ac415052363a',
          'envelope':'62e4a273fd7367fa91b9f6f17aa443033ef1a3df0d47b694fb2bcded87629f24',
          'report':'7ea8a6d1cea382581040698f3de2d919bb1def2448bd479a64abfb9f1fe4f9d1',
          'text':'3734b16c42333e3cf48510b2cb8f917d2310c0dd05ac9e638e90c1179fea80c3'}
        actual={key:payload_sha256(value) for key,value in [('handoff',fixture.handoff),('bundle',fixture.bundle),
          ('review',fixture.review),('packet',packet),('envelope',envelope),('report',report),('text',render(report))]}
        self.assertEqual(actual,expected)

    def test_actual_cli_version_two_prepare_import_review_and_export(self):
        self.accept()
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory)
            def save(name,value):
                path=folder/(name+'.json');path.write_text(json.dumps(value),encoding='utf-8');return path
            pp=save('package',self.package);hp=save('handoff',self.handoff);rp=save('response',self.response)
            bp=save('bundle',self.bundle);vp=save('review',self.review);pr=save('provenance',self.provenance)
            before={p.name:p.read_bytes() for p in folder.iterdir()}
            def run(*args):
                completed=subprocess.run([sys.executable,str(ROOT/'pattern_proposals.py'),*map(str,args)],cwd=folder,capture_output=True,text=True,timeout=30)
                self.assertEqual(completed.returncode,0,completed.stderr);return completed.stdout
            self.assertEqual(json.loads(run('prepare',pp,'--topic','model design','--include-evidence-reasons')),self.handoff)
            self.assertEqual(json.loads(run('import',pp,hp,rp,pr)),self.bundle)
            self.assertIn('Model proposed',run('review',pp,bp,vp,'--format','text'))
            self.assertIn('Reviewer supplied',run('review',pp,bp,vp,'--format','text'))
            exported=json.loads(run('export',pp,bp,vp));self.assertIn('evidence_uses',exported['review']['decisions'][0]['reviewed_pattern'])
            for name,content in before.items():self.assertEqual((folder/name).read_bytes(),content)


if __name__=='__main__':unittest.main()
