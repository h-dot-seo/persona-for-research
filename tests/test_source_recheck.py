"""Synthetic local-source consistency checks, never source authenticity tests."""
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import source_recheck as check
import research_journey as journey
import tests.test_research_journey as journey_fixture
from research_workflow import build
from persona import payload_sha256
from corpus_files import read_source_bytes
from design_scenario import template as design_template
from answer_draft import review_template
from argument_map import template as argument_template
from publication_context import template as relation_template

ROOT=Path(__file__).resolve().parents[1]


class _SourceFixture:
    def setUp(self):
        self.case=journey_fixture.ResearchJourneyTests();self.case.setUp()
        self.package=self.case.case.package
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/'sources';shutil.copytree(ROOT/'examples/synthetic-sources',self.root)
        self.selection=self.form(self.package)

    def form(self,package):
        form=check.template(package,'synthetic-recheck-operator')
        for row in form['sources']:row['source_file']=row['paper_id']+'.md'
        return form

    def audit(self):return check.audit(self.package,self.selection,self.root)

    def rebuilt(self,mutate):
        corpus={key:self.package['persona'][key] for key in ('author_id','version','build_id')}
        corpus['papers']=copy.deepcopy(self.package['knowledge']['papers']);mutate(corpus['papers'])
        self.package=build(corpus);self.selection=self.form(self.package)

    def replace_source(self,raw):
        (self.root/'synthetic-0.md').write_bytes(raw)
        self.rebuilt(lambda papers:papers[0].update(source_sha256=hashlib.sha256(raw).hexdigest()))



class SourceRecheckTests(_SourceFixture, unittest.TestCase):
    def test_template_never_selects_inherited_paths_or_accesses_sources(self):
        with patch.object(check,'source_paths',side_effect=AssertionError('no source paths')):
            form=check.template(self.package,'operator')
        self.assertEqual([row['source_file'] for row in form['sources']],[None,None])
        self.assertEqual(form['package_sha256'],payload_sha256(self.package))

    def test_every_observation_and_component_rechecked_without_label_mutation(self):
        before=copy.deepcopy((self.package,self.selection));result=self.audit()
        self.assertEqual(result['status'],'LOCAL_BYTES_AND_STORED_QUOTES_MATCH_NOT_VALIDATION')
        self.assertEqual(result['checked_record_count'],3);self.assertEqual(result['matched_quote_count'],3)
        self.assertTrue(result['all_stored_quotes_match']);self.assertFalse(result['package_modified'])
        self.assertFalse(result['automatic_approval']);self.assertEqual(result['source_authenticity'],'NOT_ESTABLISHED')
        self.assertNotIn('segments',json.dumps(result));self.assertNotIn(str(self.root),json.dumps(result))
        self.assertEqual(before,(self.package,self.selection))
        result['papers'][0]['records'][0]['reference']['paper_id']='changed'
        self.assertEqual(before,(self.package,self.selection))

    def test_missing_blank_quotes_and_missing_locator_are_independent_gaps(self):
        for quote in (None,'','   '):
            self.rebuilt(lambda papers:papers[0]['observations'][0].update(evidence_quote=quote))
            result=self.audit();self.assertEqual(result['quote_gaps'][0]['code'],'STORED_QUOTE_MISSING')
            self.assertFalse(result['all_stored_quotes_match'])
        self.rebuilt(lambda papers:papers[0]['observations'][0].update(evidence_quote='Compare competing models',locator='absent section'))
        row=self.audit()['papers'][0]['records'][0]
        self.assertEqual(row['quote_status'],'LOCATOR_NOT_FOUND');self.assertEqual(row['locator_status'],'NOT_FOUND')

    def test_missing_quote_and_missing_section_keep_both_signals(self):
        self.rebuilt(lambda papers:papers[0]['observations'][0].update(evidence_quote=None,locator='absent synthetic section'))
        row=self.audit()['papers'][0]['records'][0]
        self.assertEqual(row['quote_status'],'STORED_QUOTE_MISSING')
        self.assertEqual(row['locator_status'],'NOT_FOUND')

    def test_wrong_section_case_and_whitespace_are_not_semantically_repaired(self):
        self.replace_source(b'## wrong section\nCompare competing models\n\n## synthetic section 1\nDifferent text.\n')
        self.assertEqual(self.audit()['quote_gaps'][0]['code'],'STORED_QUOTE_NOT_FOUND_AT_LOCATOR')
        for quote in ('compare competing models','Compare  competing models'):
            self.rebuilt(lambda papers:papers[0]['observations'][0].update(evidence_quote=quote))
            self.assertEqual(self.audit()['quote_gaps'][0]['code'],'STORED_QUOTE_NOT_FOUND_AT_LOCATOR')

    def test_component_mismatch_does_not_hide_matching_parent_observation(self):
        self.rebuilt(lambda papers:papers[1]['observations'][0]['reasoning']['alternative_explanation'].update(evidence_quote='Unmatched synthetic quote'))
        result=self.audit();records=result['papers'][1]['records']
        self.assertEqual(records[0]['quote_status'],check.MATCH)
        self.assertEqual(records[1]['quote_status'],'STORED_QUOTE_NOT_FOUND_AT_LOCATOR')
        self.assertEqual(result['quote_gaps'][0]['reference']['dimension'],'alternative_explanation')

    def test_no_records_and_partial_paper_coverage_never_report_complete_quote_coverage(self):
        self.rebuilt(lambda papers:papers[0].update(observations=[]))
        result=self.audit();self.assertEqual(result['status'],'LOCAL_BYTES_MATCH_PARTIAL_QUOTE_COVERAGE_REQUIRES_REVIEW')
        self.assertEqual(result['papers_without_stored_quotes'],['synthetic-0'])
        self.rebuilt(lambda papers:papers[1].update(observations=[]))
        result=self.audit();self.assertEqual(result['status'],'LOCAL_BYTES_MATCH_NO_STORED_QUOTES')
        self.assertFalse(result['all_stored_quotes_match']);self.assertEqual(result['checked_record_count'],0)
        self.assertFalse(result['source_quotes_rechecked'])

    def test_source_change_with_same_quote_fails_hash_and_never_refreshes(self):
        path=self.root/'synthetic-1.md';path.write_bytes(path.read_bytes()+b'\nUnrelated appended synthetic text.\n')
        before=copy.deepcopy((self.package,self.selection))
        with self.assertRaisesRegex(ValueError,'bound package hash'):self.audit()
        self.assertEqual(before,(self.package,self.selection))

    def test_invalid_last_selection_row_and_schema_fail_before_any_source_read(self):
        variants=[]
        for mutate in (lambda f:f['sources'].pop(),lambda f:f['sources'].append(copy.deepcopy(f['sources'][0])),
            lambda f:f['sources'][-1].update(paper_id='unknown'),lambda f:f['sources'][-1].update(source_file=None),
            lambda f:f['sources'][-1].update(source_sha256='0'*64),lambda f:f.update(package_sha256='0'*64),
            lambda f:f.update(authorized=True),lambda f:f.update(schema='cached-approved-report')):
            form=copy.deepcopy(self.selection);mutate(form);variants.append(form)
        with patch.object(check,'read_source_bytes',side_effect=AssertionError('must not read')):
            for form in variants:
                with self.assertRaises(ValueError):check.audit(self.package,form,self.root)

    def test_unauthorized_unused_paper_malformed_components_and_rule_mismatch_preflight(self):
        for mutate in (lambda p:p['knowledge']['papers'][-1].update(authorized=False),
            lambda p:p['knowledge']['papers'][-1]['observations'][0]['reasoning']['alternative_explanation'].update(evidence_quote=None),
            lambda p:p['persona']['rules'][0].update(method='Changed unsupported rule')):
            package=copy.deepcopy(self.package);mutate(package)
            package['persona']['knowledge_papers_sha256']=payload_sha256(package['knowledge']['papers'])
            package['knowledge']['persona_payload_sha256']=payload_sha256(package['persona'])
            selection=copy.deepcopy(self.selection);selection['package_sha256']=payload_sha256(package)
            with patch.object(check,'read_source_bytes',side_effect=AssertionError('must not read')):
                with self.assertRaises(ValueError):check.audit(package,selection,self.root)

    def test_all_paths_are_preflighted_before_read_with_portable_path_restrictions(self):
        for value in ('../outside.md','/tmp/source.md','folder\\source.md','C:source.md','./synthetic-1.md',
                      'folder//source.md','source.pdf','source\n.md','missing.md','.'):
            form=copy.deepcopy(self.selection);form['sources'][-1]['source_file']=value
            with patch.object(check,'read_source_bytes',side_effect=AssertionError('must not read')):
                with self.assertRaises((ValueError,OSError)):check.audit(self.package,form,self.root)
        directory=self.root/'directory.md';directory.mkdir();self.selection['sources'][-1]['source_file']='directory.md'
        with patch.object(check,'read_source_bytes',side_effect=AssertionError('must not read')):
            with self.assertRaises(ValueError):self.audit()

    def test_symlink_escape_and_nonregular_fifo_fail_before_read(self):
        outside=Path(self.tmp.name)/'outside.md';outside.write_text('Synthetic outside source.')
        link=self.root/'link.md'
        try:link.symlink_to(outside)
        except OSError:self.skipTest('symlink creation unavailable')
        self.selection['sources'][-1]['source_file']='link.md'
        with patch.object(check,'read_source_bytes',side_effect=AssertionError('must not read')):
            with self.assertRaises(ValueError):self.audit()
        if hasattr(os,'mkfifo'):
            fifo=self.root/'fifo.md';os.mkfifo(fifo);self.selection['sources'][-1]['source_file']='fifo.md'
            with patch.object(check,'read_source_bytes',side_effect=AssertionError('must not read')):
                with self.assertRaises(ValueError):self.audit()

    def test_source_path_replacement_after_preflight_is_rejected(self):
        original=check.source_paths
        outside=Path(self.tmp.name)/'replacement.md';outside.write_text('Synthetic replacement.')
        probe=self.root/'symlink-probe.md'
        try:probe.symlink_to(outside);probe.unlink()
        except OSError:self.skipTest('symlink creation unavailable')
        def replaced(*args):
            paths=original(*args);paths[0].unlink();paths[0].symlink_to(outside);return paths
        with patch.object(check,'source_paths',side_effect=replaced):
            with self.assertRaisesRegex(ValueError,'changed after preflight'):self.audit()

    def test_aggregate_budget_exact_boundary_and_duplicate_source_reads(self):
        total=sum((self.root/row['source_file']).stat().st_size for row in self.selection['sources'])
        with patch.object(check,'MAX_SOURCE_BYTES',total):self.assertEqual(self.audit()['source_bytes_read'],total)
        with patch.object(check,'MAX_SOURCE_BYTES',total-1):
            with self.assertRaisesRegex(ValueError,'input limit'):self.audit()
        digest=self.package['knowledge']['papers'][0]['source_sha256']
        self.rebuilt(lambda papers:papers[1].update(source_sha256=digest))
        self.selection['sources'][1]['source_file']='synthetic-0.md'
        size=(self.root/'synthetic-0.md').stat().st_size
        with patch.object(check,'MAX_SOURCE_BYTES',2*size),patch.object(check,'read_source_bytes',wraps=read_source_bytes) as reads:
            result=self.audit();self.assertEqual(reads.call_count,2);self.assertEqual(result['source_bytes_read'],2*size)

    def test_invalid_utf8_duplicate_and_empty_sections_fail_without_report(self):
        for raw in (b'## synthetic section 1\n\xff',b'## a\nx\n## a\ny\n',b'## \nx\n',b'No Markdown sections.'):
            self.replace_source(raw)
            with self.assertRaises(ValueError):self.audit()

    def test_section_line_endings_normalized_but_raw_bytes_hash_checked(self):
        self.replace_source(b'## synthetic section 1\r\nCompare competing models\r\n')
        result=self.audit();self.assertEqual(result['papers'][0]['records'][0]['quote_status'],check.MATCH)
        self.assertEqual(result['papers'][0]['source_sha256'],hashlib.sha256((self.root/'synthetic-0.md').read_bytes()).hexdigest())

    def test_json_limits_and_saved_report_cannot_be_reused_as_selection(self):
        report=self.audit()
        with patch.object(check,'read_source_bytes',side_effect=AssertionError('must not read')):
            with self.assertRaises(ValueError):check.audit(self.package,report,self.root)
        with patch.object(check,'MAX_JSON_BYTES',10):
            with self.assertRaisesRegex(ValueError,'JSON exceeds'):self.audit()
        with self.assertRaisesRegex(ValueError,'finite JSON'):check._detach({'bad':float('nan')})

    def test_cli_template_recheck_gap_report_and_failure_emit_no_partial_json(self):
        pp=Path(self.tmp.name)/'package.json';sp=Path(self.tmp.name)/'selection.json'
        pp.write_text(json.dumps(self.package));sp.write_text(json.dumps(self.selection))
        base=[sys.executable,str(ROOT/'source_recheck.py'),str(pp)]
        run=lambda args:subprocess.run(base+args,cwd=self.tmp.name,capture_output=True,timeout=20)
        t=run(['--template','--operator-id','synthetic']);self.assertEqual(t.returncode,0,t.stderr)
        self.assertTrue(all(row['source_file'] is None for row in json.loads(t.stdout)['sources']))
        args=[str(sp),'--source-root',str(self.root)]
        r=run(args);self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(json.loads(r.stdout)['checked_record_count'],3)
        text=run(args+['--format','text']);self.assertEqual(text.returncode,0,text.stderr);self.assertIn(b'Current local source',text.stdout)
        (self.root/'synthetic-1.md').write_text('Changed source with no matching hash.')
        fail=run(args);self.assertNotEqual(fail.returncode,0);self.assertEqual(fail.stdout,b'');self.assertNotIn(b'Traceback',fail.stderr)
        sp.write_text('{"sources":[],"sources":[]}');fail=run(args)
        self.assertNotEqual(fail.returncode,0);self.assertEqual(fail.stdout,b'')


class JourneySourceRecheckTests(_SourceFixture, unittest.TestCase):
    def test_legacy_no_source_payload_and_text_remain_exact(self):
        self.assertEqual(payload_sha256(journey.inspect(*self.case.args())),'a4405809c8fde162293d6e73dd2ca8083329570d44ac9e2428f0607fa7d23350')
        self.assertEqual(payload_sha256(journey.render(*self.case.args())),'b21be5e06cde18dfd52a0c6d065d6161b857ba6c42f8921594f03bcfe8605d95')

    def test_live_recheck_is_separate_and_covers_each_route_once(self):
        before=copy.deepcopy(self.case.args());base=journey.inspect(*self.case.args())
        result=journey.inspect(*self.case.args(),source_selection=self.selection,source_root=self.root)
        self.assertTrue(result['source_reread']);self.assertFalse(result['current_checks_replace_recorded_labels'])
        self.assertNotEqual(result['journey_input_sha256'],base['journey_input_sha256'])
        for key in ('trajectory_review','pattern_transfer_review','argument_review','evidence_scope'):
            self.assertEqual(result[key],base[key])
        self.assertTrue(all(row['current_source_recheck']['quote_status']==check.MATCH for row in result['evidence_routes']))
        self.assertEqual(before,self.case.args());self.assertEqual(result['status'],'HUMAN_REVIEW_REQUIRED_NOT_RESEARCH_APPROVAL')

    def test_existing_artifacts_fail_before_source_reads_and_options_need_both(self):
        args=copy.deepcopy(self.case.args());args[6]['review_sha256']='0'*64
        with patch.object(check,'read_source_bytes',side_effect=AssertionError('must not read')):
            with self.assertRaises(ValueError):journey.inspect(*args,source_selection=self.selection,source_root=self.root)
        for options in (dict(source_selection=self.selection),dict(source_root=self.root)):
            with self.assertRaisesRegex(ValueError,'both'):journey.inspect(*self.case.args(),**options)

    def test_text_reads_each_selected_source_only_once_and_keeps_current_labels_separate(self):
        with patch.object(check,'read_source_bytes',wraps=read_source_bytes) as reads:
            text=journey.render(*self.case.args(),source_selection=self.selection,source_root=self.root)
        self.assertEqual(reads.call_count,2)
        self.assertIn('Current local source recheck:',text);self.assertIn('historical subreport labels remain unchanged',text)
        self.assertIn('Current local quote check: EXACT_SECTION_SUBSTRING_MATCH',text)

    def test_unmatched_component_and_unused_paper_gap_remain_explicit(self):
        # Rebuild all bound journey forms through its outside-paper helper.
        ref=self.case.add_outside_paper();self.package=self.case.case.package
        paper=self.package['knowledge']['papers'][-1]
        shutil.copyfile(self.root/'synthetic-0.md',self.root/'synthetic-outside.md')
        self.selection=self.form(self.package)
        result=journey.inspect(*self.case.args(),source_selection=self.selection,source_root=self.root)
        self.assertEqual(result['source_recheck']['checked_paper_count'],3)
        self.assertNotIn(ref,[row['evidence']['reference'] for row in result['evidence_routes']])
        path=self.root/'synthetic-outside.md';path.write_bytes(path.read_bytes()+b'Changed outside source.')
        with self.assertRaisesRegex(ValueError,'bound package hash'):
            journey.inspect(*self.case.args(),source_selection=self.selection,source_root=self.root)

    def rebind_journey(self):
        c=self.case.case;c.package=self.package
        for form in (c.patterns,c.context,c.links,c.draft):
            form.update(persona_sha256=payload_sha256(self.package['persona']),knowledge_papers_sha256=payload_sha256(self.package['knowledge']['papers']))
        old=c.proposal['steps'];c.proposal=design_template(self.package,c.links,c.context['question'],'synthetic-plan');c.proposal['steps']=old
        self.case.review=review_template(self.package,c.draft,'synthetic-reviewer')
        old=self.case.argument['steps'];self.case.argument=argument_template(self.package,c.draft,'synthetic-map',self.case.review);self.case.argument['steps']=old
        old=self.case.relations['relations'];self.case.relations=relation_template(self.package,'synthetic-relations');self.case.relations['relations']=old

    def test_unused_quote_gap_enters_agenda_even_without_exact_journey_route(self):
        ref=self.case.add_outside_paper();self.package=self.case.case.package
        shutil.copyfile(self.root/'synthetic-0.md',self.root/'synthetic-outside.md')
        self.rebuilt(lambda papers:papers[-1]['observations'][0].update(evidence_quote=None))
        self.rebind_journey()
        result=journey.inspect(*self.case.args(),source_selection=self.selection,source_root=self.root)
        self.assertNotIn(ref,[row['evidence']['reference'] for row in result['evidence_routes']])
        gap=next(row for row in result['review_agenda'] if row['domain']=='current_source_recheck')
        self.assertEqual(gap['reference'],ref);self.assertEqual(gap['code'],'STORED_QUOTE_MISSING')
        self.assertEqual(result['source_recheck']['checked_paper_count'],3)

    def test_current_quote_gaps_enter_agenda_without_rewriting_historical_labels(self):
        self.rebuilt(lambda papers:papers[1]['observations'][0]['reasoning']['alternative_explanation'].update(evidence_quote='Unmatched synthetic current quote.'))
        self.rebind_journey()
        before=journey.inspect(*self.case.args())
        result=journey.inspect(*self.case.args(),source_selection=self.selection,source_root=self.root)
        gaps=[row for row in result['review_agenda'] if row['domain']=='current_source_recheck']
        self.assertEqual(len(gaps),1);self.assertEqual(gaps[0]['code'],'STORED_QUOTE_NOT_FOUND_AT_LOCATOR')
        self.assertEqual(gaps[0]['reference']['dimension'],'alternative_explanation')
        self.assertEqual(result['pattern_transfer_review'],before['pattern_transfer_review'])
        self.assertFalse(result['source_recheck']['all_stored_quotes_match'])

    def test_cli_live_and_no_source_runs_and_mismatched_flags(self):
        paths=[]
        for name,value in zip(journey.INPUT_NAMES,self.case.args()[:8]):
            p=Path(self.tmp.name)/(name+'.json');p.write_text(json.dumps(value));paths.append(p)
        review=Path(self.tmp.name)/'review.json';review.write_text(json.dumps(self.case.review))
        selection=Path(self.tmp.name)/'selection.json';selection.write_text(json.dumps(self.selection))
        base=[sys.executable,str(ROOT/'research_journey.py'),*map(str,paths),'--pattern-id','comparison','--review',str(review)]
        for suffix in ([],['--source-selection',str(selection),'--source-root',str(self.root)],
                       ['--source-selection',str(selection),'--source-root',str(self.root),'--format','text']):
            run=subprocess.run(base+suffix,cwd=self.tmp.name,capture_output=True,timeout=30)
            self.assertEqual(run.returncode,0,run.stderr)
            if '--format' not in suffix:self.assertEqual(json.loads(run.stdout)['source_reread'],bool(suffix))
            else:self.assertIn(b'Current local source recheck',run.stdout)
        run=subprocess.run(base+['--source-selection',str(selection)],cwd=self.tmp.name,capture_output=True,timeout=30)
        self.assertNotEqual(run.returncode,0);self.assertEqual(run.stdout,b'')



if __name__=='__main__':unittest.main()
