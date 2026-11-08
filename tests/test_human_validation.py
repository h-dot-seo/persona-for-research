"""Human validation records: detached, hash-bound, strictly checked, never written into a package."""
import copy
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import human_validation as hv
from extraction_adapter import MockProvider
from human_validation import axis, check, template, write_template
from persona import payload_sha256, validate
from research_workflow import build
from review_package import render

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_FILE = Path('examples/trajectory-conditions-package.json')
RECORD_FILE = Path('examples/manual-human-validation.json')
QUESTION = 'Does Method M distinguish the synthetic signals?'
TOPIC = 'synthetic method conditions'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def rebind(package):
    """Restore the hash chain after an edit, as a rebuilt release would; not a repair of history."""
    package['persona']['knowledge_papers_sha256'] = payload_sha256(package['knowledge']['papers'])
    package['knowledge']['persona_payload_sha256'] = payload_sha256(package['persona'])
    return package


def completed(package, rater='synthetic-rater-a'):
    """A filled record for a package: every rule AGREE, one invented rater label."""
    record = template(package)
    record.update(raters=[dict(rater_id=rater, role='invented test reader')], assessed_at='2026-11-08',
                  method='Synthetic test rating; no real rater.', limitations='Test fixture only.',
                  independence_declaration='Test labels only; nothing verified.', status='RECORDED')
    for item in record['items']:
        item.update(judgement='AGREE', rationale='Synthetic test rationale.', source_locator='synthetic locator')
    return record


def leaves(value):
    if isinstance(value, dict):
        for child in value.values():
            yield from leaves(child)
    elif isinstance(value, list):
        for child in value:
            yield from leaves(child)
    else:
        yield value


class HumanValidationTests(unittest.TestCase):
    def setUp(self):
        self.persona = read('examples/persona.json')
        self.knowledge = read('examples/knowledge.json')
        self.shipped = read(PACKAGE_FILE)
        self.record = read(RECORD_FILE)
        self.built = build(read('examples/research-corpus.json'))

    def run_cli(self, *args, env=None):
        return subprocess.run([sys.executable, *map(str, args)], capture_output=True, timeout=60, env=env)

    def test_template_binds_both_hashes_and_lists_topics_and_rule_ids(self):
        pair = template(self.persona, self.knowledge)
        self.assertEqual(list(pair), list(hv.RECORD_FIELDS))
        self.assertEqual(pair['schema_version'], 'human-validation-record.v1')
        self.assertEqual(pair['persona_payload_sha256'], self.knowledge['persona_payload_sha256'])
        self.assertEqual(pair['persona_payload_sha256'], payload_sha256(self.persona))
        self.assertEqual(pair['knowledge_papers_sha256'], payload_sha256([]))
        self.assertEqual((pair['scope_topics'], pair['items'], pair['status']), ([], [], None))
        self.assertEqual(pair['raters'], [dict(rater_id='', role='')])
        for key in ('assessed_at', 'method', 'limitations', 'independence_declaration'):
            self.assertEqual(pair[key], '')
        single = template(self.built)
        self.assertEqual(single, template({'package': self.built, 'application': {'status': 'READY'}}))
        self.assertEqual(single['scope_topics'], ['model design'])
        self.assertEqual([item['item_id'] for item in single['items']],
                         [rule['rule_id'] for rule in self.built['persona']['rules']])
        self.assertTrue(all(item['judgement'] == 'NOT_ASSESSED' and item['rationale'] == '' and item['source_locator'] == ''
                            for item in single['items']))
        self.assertEqual(single['knowledge_papers_sha256'], self.built['persona']['knowledge_papers_sha256'])
        self.assertEqual(single['persona_payload_sha256'], self.built['knowledge']['persona_payload_sha256'])
        shipped = template(self.shipped)
        self.assertEqual(shipped['scope_topics'], [TOPIC])
        self.assertEqual(len(shipped['items']), 6)
        self.assertEqual(shipped, template(self.shipped['persona'], self.shipped['knowledge']))

    def test_shipped_fictional_record_checks_as_current_with_per_label_counts_only(self):
        self.assertIn('Fictional', json.dumps(self.record))
        result = check(self.record, self.shipped)
        self.assertEqual(result['status'], 'HUMAN_VALIDATION_RECORD_CHECKED')
        self.assertEqual(result['binding_status'], 'CURRENT_PACKAGE')
        self.assertEqual(result['binding_differences'], [])
        self.assertEqual(result['record_sha256'], payload_sha256(self.record))
        self.assertEqual(result['judgement_counts'], dict(AGREE=3, PARTIAL=1, DISAGREE=1, NOT_ASSESSED=1))
        self.assertEqual((result['rater_count'], result['item_count']), (2, 6))
        self.assertEqual(result['colliding_rater_labels'], [])
        self.assertEqual(result['package_labels'], ['synthetic-scholar'])
        self.assertEqual(result['rater_independence'], 'LABEL_DISTINCT_ONLY')
        self.assertEqual((result['aggregate_score'], result['verdict'], result['generalization']),
                         ('NOT_COMPUTED', 'NOT_DERIVED', 'NOT_ESTABLISHED'))
        self.assertEqual(result['researcher_fidelity_evaluation'], 'NOT_PERFORMED')
        self.assertFalse(result['llm_used'] or result['canonical_update_performed'] or result['persona_payload_modified'])
        self.assertFalse(any(type(leaf) is float for leaf in leaves(result)))
        self.assertEqual(check(self.record, self.shipped['persona'], self.shipped['knowledge']), result)

    def test_unedited_template_is_not_a_completed_record(self):
        blank = template(self.shipped)
        with self.assertRaisesRegex(ValueError, 'status must be RECORDED'):
            check(blank, self.shipped)
        blank['status'] = 'RECORDED'
        with self.assertRaisesRegex(ValueError, 'rater_id'):
            check(blank, self.shipped)
        blank['raters'] = [dict(rater_id='synthetic-rater-a', role='invented reader')]
        with self.assertRaisesRegex(ValueError, 'assessed_at'):
            check(blank, self.shipped)
        blank['assessed_at'] = '2026-11-08'
        with self.assertRaisesRegex(ValueError, 'method'):
            check(blank, self.shipped)
        blank.update(method='Synthetic rating.', limitations='Test only.', independence_declaration='Labels only.')
        with self.assertRaisesRegex(ValueError, 'rationale'):
            check(blank, self.shipped)
        for item in blank['items']:
            item.update(rationale='Left unassessed in this synthetic test.', source_locator='synthetic locator')
        result = check(blank, self.shipped)
        self.assertEqual(result['judgement_counts'], dict(AGREE=0, PARTIAL=0, DISAGREE=0, NOT_ASSESSED=6))

    def test_stale_package_detected_after_editing_a_rule_while_tampering_stays_an_error(self):
        record = completed(self.built)
        self.assertEqual(check(record, self.built)['binding_status'], 'CURRENT_PACKAGE')
        edited = copy.deepcopy(self.built)
        edited['persona']['rules'][0]['limitation'] = 'edited synthetic limitation'
        with self.assertRaisesRegex(ValueError, 'payload hash mismatch'):
            check(record, edited)
        rebind(edited)
        result = check(record, edited)
        self.assertEqual(result['binding_status'], 'STALE_PACKAGE')
        self.assertEqual(result['binding_differences'], ['persona_payload_sha256'])
        self.assertEqual(result['judgement_counts']['AGREE'], len(record['items']))
        report = axis(edited, None, [record])
        self.assertEqual((report['status'], report['stale_record_count']), ('STALE_PACKAGE', 1))
        rebuilt = copy.deepcopy(self.built)
        rebuilt['knowledge']['papers'][0]['year'] = 1999
        rebind(rebuilt)
        self.assertEqual(check(record, rebuilt)['binding_differences'], ['persona_payload_sha256', 'knowledge_papers_sha256'])
        released = copy.deepcopy(self.built)
        for part in ('persona', 'knowledge'):
            released[part].update(version='2', build_id='synthetic-rebuilt')
        rebind(released)
        self.assertEqual(check(record, released)['binding_differences'], ['version', 'build_id', 'persona_payload_sha256'])
        other = copy.deepcopy(self.built)
        other['persona']['author_id'] = other['knowledge']['author_id'] = 'other-synthetic-scholar'
        for paper in other['knowledge']['papers']:
            paper['author_id'] = 'other-synthetic-scholar'
        rebind(other)
        with self.assertRaisesRegex(ValueError, 'different scholarly identity'):
            check(record, other)

    def test_unknown_item_or_topic_and_scope_mismatch_rejected(self):
        record = completed(self.shipped)
        bad = copy.deepcopy(record)
        bad['items'][0]['item_id'] = 'rule-99'
        with self.assertRaisesRegex(ValueError, 'not a rule_id'):
            check(bad, self.shipped)
        bad = copy.deepcopy(record)
        bad['scope_topics'] = ['unknown synthetic topic']
        with self.assertRaisesRegex(ValueError, 'scope topic is not'):
            check(bad, self.shipped)
        bad = copy.deepcopy(record)
        bad['scope_topics'] = []
        with self.assertRaisesRegex(ValueError, 'scope_topics'):
            check(bad, self.shipped)
        corpus = read('examples/research-corpus.json')
        corpus['papers'][1]['observations'][0]['topic'] = 'second synthetic topic'
        two = build(corpus)
        topics = {rule['rule_id']: rule['topic'] for rule in two['persona']['rules']}
        record = completed(two)
        self.assertEqual(record['scope_topics'], ['model design', 'second synthetic topic'])
        self.assertEqual(check(record, two)['item_count'], len(topics))
        narrow = copy.deepcopy(record)
        narrow['scope_topics'] = ['model design']
        with self.assertRaisesRegex(ValueError, 'outside the declared scope'):
            check(narrow, two)
        partial = copy.deepcopy(record)
        partial['items'] = [item for item in partial['items'] if topics[item['item_id']] == 'model design']
        with self.assertRaisesRegex(ValueError, 'every scope topic needs'):
            check(partial, two)

    def test_rater_labels_need_one_distinct_from_recorded_author_operator_reviewer_labels(self):
        author = self.shipped['persona']['author_id']
        colliding = completed(self.shipped, rater=author)
        with self.assertRaisesRegex(ValueError, 'no rater label is distinct'):
            check(colliding, self.shipped)
        colliding['raters'].append(dict(rater_id='synthetic-rater-b', role='invented second reader'))
        result = check(colliding, self.shipped)
        self.assertEqual(result['colliding_rater_labels'], [author])
        self.assertEqual(result['rater_independence'], 'LABEL_DISTINCT_ONLY')
        duplicate = completed(self.shipped)
        duplicate['raters'].append(dict(duplicate['raters'][0]))
        with self.assertRaisesRegex(ValueError, 'duplicate rater_id'):
            check(duplicate, self.shipped)
        labelled = copy.deepcopy(self.built)
        labelled['persona']['rules'][0]['operator_id'] = 'synthetic-operator'
        labelled['knowledge']['papers'][0]['observations'][0]['reviewer_id'] = 'synthetic-reviewer'
        rebind(labelled)
        recorded = sorted({labelled['persona']['author_id'], 'synthetic-operator', 'synthetic-reviewer'})
        self.assertEqual(hv.recorded_labels(labelled['persona'], labelled['knowledge']), recorded)
        for label in recorded:
            with self.assertRaisesRegex(ValueError, 'no rater label is distinct'):
                check(completed(labelled, rater=label), labelled)
        self.assertEqual(check(completed(labelled), labelled)['package_labels'], recorded)

    def test_enum_date_and_field_strictness(self):
        record = completed(self.shipped)

        def rejects(pattern, mutate):
            bad = copy.deepcopy(record)
            mutate(bad)
            with self.assertRaisesRegex(ValueError, pattern):
                check(bad, self.shipped)
        rejects('judgement', lambda r: r['items'][0].update(judgement='MAYBE'))
        rejects('judgement', lambda r: r['items'][0].update(judgement='agree'))
        for value in ('2026-1-8', '2026-11-08T00:00:00', '20261108', '2026-13-01', '2026-02-30', '', 20261108, None):
            rejects('assessed_at', lambda r, v=value: r.update(assessed_at=v))
        rejects('missing or unknown', lambda r: r.update(score=1.0))
        rejects('missing or unknown', lambda r: r.pop('limitations'))
        rejects('missing or unknown', lambda r: r['items'][0].update(weight=2))
        rejects('missing or unknown', lambda r: r['raters'][0].pop('role'))
        rejects('schema_version', lambda r: r.update(schema_version='human-validation-record.v2'))
        rejects('raters', lambda r: r.update(raters=[]))
        rejects('raters', lambda r: r.update(raters='synthetic-rater-a'))
        rejects('duplicate item_id', lambda r: r['items'].append(dict(r['items'][0])))
        rejects('rationale', lambda r: r['items'][0].update(rationale='   '))
        rejects('rationale', lambda r: r['items'][0].update(rationale='x' * 2001))
        rejects('source_locator', lambda r: r['items'][0].update(source_locator=''))
        rejects('control characters', lambda r: r['raters'][0].update(rater_id='rater\x1b[2J'))
        rejects('items', lambda r: r.update(items=[]))
        rejects('status must be RECORDED', lambda r: r.update(status='DRAFT'))
        rejects('status must be RECORDED', lambda r: r.update(status=None))
        rejects('persona_payload_sha256', lambda r: r.update(persona_payload_sha256='ABC'))
        rejects('knowledge_papers_sha256', lambda r: r.update(knowledge_papers_sha256=r['knowledge_papers_sha256'].upper()))
        rejects('independence_declaration', lambda r: r.update(independence_declaration=''))
        rejects('method', lambda r: r.update(method=None))
        rejects('duplicate scope topic', lambda r: r.update(scope_topics=[TOPIC, TOPIC]))
        with self.assertRaisesRegex(ValueError, 'missing or unknown'):
            check([record], self.shipped)
        with self.assertRaisesRegex(ValueError, 'one bound package file'):
            check(record, {'persona': self.shipped['persona']})
        with self.assertRaisesRegex(ValueError, 'binding mismatch'):
            check(record, self.shipped['persona'], self.knowledge)
        self.assertEqual(check(record, self.shipped)['judgement_counts']['AGREE'], 6)

    def test_status_cli_reports_each_axis_state_without_modifying_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / 'package.json'
            package.write_bytes(PACKAGE_FILE.read_bytes())
            current = root / 'current.json'
            current.write_bytes(RECORD_FILE.read_bytes())
            earlier = copy.deepcopy(self.record)
            earlier.update(version='0', build_id='synthetic-earlier-build')
            stale = root / 'stale.json'
            stale.write_text(json.dumps(earlier), encoding='utf-8')
            broken = copy.deepcopy(self.record)
            broken['status'] = None
            (root / 'broken.json').write_text(json.dumps(broken), encoding='utf-8')
            before = {path: path.read_bytes() for path in (package, current, stale)}
            none = self.run_cli('human_validation.py', 'status', package)
            self.assertEqual(none.returncode, 0, none.stderr)
            self.assertEqual(json.loads(none.stdout)['status'], 'NOT_PERFORMED')
            one = self.run_cli('human_validation.py', 'status', package, '--human-validation', current)
            self.assertEqual(one.returncode, 0, one.stderr)
            one = json.loads(one.stdout)
            self.assertEqual((one['status'], one['record_count'], one['records'][0]['binding_status']),
                             ('RECORDED_CURRENT', 1, 'CURRENT_PACKAGE'))
            self.assertEqual(one['records'][0]['record_sha256'], payload_sha256(self.record))
            self.assertEqual(one['records'][0]['judgement_counts'], dict(AGREE=3, PARTIAL=1, DISAGREE=1, NOT_ASSESSED=1))
            old = json.loads(self.run_cli('human_validation.py', 'status', package, '--human-validation', stale).stdout)
            self.assertEqual((old['status'], old['stale_record_count']), ('STALE_PACKAGE', 1))
            self.assertEqual(old['records'][0]['binding_differences'], ['version', 'build_id'])
            both = self.run_cli('human_validation.py', 'status', package, '--human-validation', stale,
                                '--human-validation', current, '--text')
            self.assertEqual(both.returncode, 0, both.stderr)
            text = both.stdout.decode('utf-8')
            self.assertIn('Human validation axis: RECORDED_CURRENT (records=2; current=1; stale=1)', text)
            self.assertIn('Binding differences: version, build_id', text)
            self.assertIn('persona payload validation.human_validation=NOT_DECLARED (unchanged)', text)
            twice = self.run_cli('human_validation.py', 'status', package, '--human-validation', current,
                                 '--human-validation', current)
            self.assertNotEqual(twice.returncode, 0)
            self.assertEqual(twice.stdout, b'')
            self.assertIn(b'supplied twice', twice.stderr)
            rejected = self.run_cli('human_validation.py', 'status', package, '--human-validation', root / 'broken.json')
            self.assertNotEqual(rejected.returncode, 0)
            self.assertEqual(rejected.stdout, b'')
            self.assertNotIn(b'Traceback', rejected.stderr)
            self.assertEqual({path: path.read_bytes() for path in before}, before)

    def test_examples_pair_still_validates_and_stays_byte_identical(self):
        files = [Path('examples/persona.json'), Path('examples/knowledge.json'), PACKAGE_FILE, RECORD_FILE]
        before = [path.read_bytes() for path in files]
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / 'minimal.json'
            written = self.run_cli('human_validation.py', 'template', 'examples/persona.json', 'examples/knowledge.json',
                                   '--output', out)
            self.assertEqual(written.returncode, 0, written.stderr)
            receipt = json.loads(written.stdout)
            self.assertEqual((receipt['status'], receipt['available_topics'], receipt['available_item_ids'], receipt['record_status']),
                             ('HUMAN_VALIDATION_TEMPLATE_WRITTEN', [], [], None))
            self.assertEqual(receipt['package']['persona_payload_sha256'], self.knowledge['persona_payload_sha256'])
            self.assertEqual(json.loads(out.read_text(encoding='utf-8')), template(self.persona, self.knowledge))
            self.assertNotIn(b'\r', out.read_bytes())
            status = self.run_cli('human_validation.py', 'status', 'examples/persona.json', 'examples/knowledge.json')
            self.assertEqual(status.returncode, 0, status.stderr)
            status = json.loads(status.stdout)
            self.assertEqual((status['status'], status['persona_payload_human_validation']), ('NOT_PERFORMED', 'NOT_PERFORMED'))
            checked = self.run_cli('human_validation.py', 'check', RECORD_FILE, PACKAGE_FILE)
            self.assertEqual(checked.returncode, 0, checked.stderr)
            self.assertEqual(json.loads(checked.stdout)['binding_status'], 'CURRENT_PACKAGE')
        mechanical = self.run_cli('persona.py', 'examples/persona.json', 'examples/knowledge.json')
        self.assertEqual(mechanical.returncode, 0, mechanical.stderr)
        self.assertTrue(json.loads(mechanical.stdout)['mechanically_valid'])
        self.assertEqual(validate(self.persona, self.knowledge), [])
        self.assertEqual(self.persona['validation']['human_validation'], 'NOT_PERFORMED')
        self.assertEqual([path.read_bytes() for path in files], before)

    def test_exclusive_output_refuses_existing_files_missing_parents_repository_paths_and_symlinks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / 'record.json'
            record = write_template(self.shipped, None, target)
            self.assertEqual(target.read_bytes(), (json.dumps(record, ensure_ascii=True, indent=2) + '\n').encode('utf-8'))
            with self.assertRaisesRegex(ValueError, 'already exists'):
                write_template(self.shipped, None, target)
            with self.assertRaisesRegex(ValueError, 'parent must already exist'):
                write_template(self.shipped, None, root / 'missing' / 'record.json')
            inside = ROOT / 'examples' / 'unlisted-human-validation-template.json'
            with self.assertRaisesRegex(ValueError, 'outside the repository'):
                write_template(self.shipped, None, inside)
            self.assertFalse(inside.exists())
            with self.assertRaisesRegex(ValueError, 'outside the repository'):
                write_template(self.shipped, None, ROOT)
            cli = self.run_cli('human_validation.py', 'template', PACKAGE_FILE, '--output', target)
            self.assertNotEqual(cli.returncode, 0)
            self.assertEqual(cli.stdout, b'')
            self.assertIn(b'already exists', cli.stderr)
            self.assertEqual(json.loads(target.read_text(encoding='utf-8')), record)
            link = root / 'dangling.json'
            linked_dir = root / 'linked-dir'
            try:
                link.symlink_to(root / 'missing-target.json')
                (root / 'realdir').mkdir()
                linked_dir.symlink_to(root / 'realdir', target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest('symlinks are not available on this platform')
            with self.assertRaisesRegex(ValueError, 'symlink'):
                write_template(self.shipped, None, link)
            with self.assertRaisesRegex(ValueError, 'symlink'):
                write_template(self.shipped, None, linked_dir / 'record.json')
            self.assertFalse((root / 'missing-target.json').exists())
            self.assertFalse((root / 'realdir' / 'record.json').exists())

    def test_cli_utf8_output_independent_of_console_encoding(self):
        record = copy.deepcopy(self.record)
        record['items'][0]['rationale'] = '합성 규칙 평가 근거 — 실제 연구자 아님'
        record['method'] = 'Fictional 평가 방법'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'record.json'
            path.write_text(json.dumps(record, ensure_ascii=False), encoding='utf-8')
            env = dict(os.environ, PYTHONIOENCODING='ascii')
            text = self.run_cli('human_validation.py', 'check', path, PACKAGE_FILE, '--text', env=env)
            self.assertEqual(text.returncode, 0, text.stderr)
            self.assertIn('합성 규칙 평가 근거 — 실제 연구자 아님', text.stdout.decode('utf-8'))
            raw = self.run_cli('human_validation.py', 'check', path, PACKAGE_FILE, env=env)
            self.assertEqual(raw.returncode, 0, raw.stderr)
            self.assertEqual(json.loads(raw.stdout)['method'], 'Fictional 평가 방법')
            status = self.run_cli('human_validation.py', 'status', PACKAGE_FILE, '--human-validation', path, '--text', env=env)
            self.assertEqual(status.returncode, 0, status.stderr)
            self.assertIn('Human validation axis: RECORDED_CURRENT', status.stdout.decode('utf-8'))

    def test_text_output_escapes_control_characters_from_data(self):
        record = copy.deepcopy(self.record)
        record['method'] = 'Rating\nStatus: RECORDED_CURRENT\x1b[2J'
        record['raters'][0]['role'] = 'reader Binding differences: none'
        record['items'][0]['rationale'] = 'why\r\nAggregate score: 1.0'
        result = check(record, self.shipped)
        text = hv.render_check(result)
        self.assertIn('Rating\\u000aStatus: RECORDED_CURRENT\\u001b[2J', text)
        self.assertIn('reader\\u2028Binding differences: none', text)
        self.assertIn('why\\u000d\\u000aAggregate score: 1.0', text)
        for forbidden in ('\x1b', ' ', '\r'):
            self.assertNotIn(forbidden, text)
        self.assertNotIn('Status: RECORDED_CURRENT', text.splitlines())
        self.assertEqual(len([line for line in text.splitlines() if line.startswith('Aggregate score:')]), 1)
        text.encode('utf-8')
        report = hv.render_status(axis(self.shipped, None, [record]))
        self.assertIn('Human validation axis: RECORDED_CURRENT (records=1; current=1; stale=0)', report)
        self.assertNotIn('\x1b', report)

    def test_release_review_option_reports_axis_and_default_output_is_unchanged(self):
        default = render(self.shipped, QUESTION, TOPIC)
        self.assertEqual(default, render(self.shipped, QUESTION, TOPIC, human_validation=None))
        self.assertNotIn('Human validation', default)
        text = render(self.shipped, QUESTION, TOPIC, human_validation=[self.record])
        head, boundary = default.rsplit('Boundary:', 1)
        self.assertTrue(text.startswith(head))
        self.assertTrue(text.endswith('Boundary:' + boundary))
        self.assertIn('Human validation axis: RECORDED_CURRENT (records=1; current=1; stale=0); '
                      'persona payload validation.human_validation=NOT_DECLARED (unchanged)', text)
        self.assertIn('  Record sha256=' + payload_sha256(self.record) + ': CURRENT_PACKAGE; raters=2 (LABEL_DISTINCT_ONLY; '
                      'colliding=0); items=6; AGREE=3; PARTIAL=1; DISAGREE=1; NOT_ASSESSED=1; assessed_at=2026-11-08', text)
        self.assertIn('Human validation boundary: ', text)
        self.assertIn('Human validation axis: NOT_PERFORMED (records=0', render(self.shipped, QUESTION, TOPIC, human_validation=[]))
        stale = copy.deepcopy(self.record)
        stale['build_id'] = 'synthetic-earlier-build'
        self.assertIn('Human validation axis: STALE_PACKAGE (records=1; current=0; stale=1)',
                      render(self.shipped, QUESTION, TOPIC, human_validation=[stale]))
        broken = copy.deepcopy(self.record)
        broken['items'][0]['item_id'] = 'rule-99'
        with self.assertRaisesRegex(ValueError, 'not a rule_id'):
            render(self.shipped, QUESTION, TOPIC, human_validation=[broken])
        self.assertEqual(render({'package': self.shipped, 'application': {}}, QUESTION, TOPIC, human_validation=[self.record]), text)
        with tempfile.TemporaryDirectory() as directory:
            broken_path = Path(directory) / 'broken.json'
            broken_path.write_text(json.dumps(broken), encoding='utf-8')
            before = PACKAGE_FILE.read_bytes()
            ok = self.run_cli('review_package.py', PACKAGE_FILE, '--question', QUESTION, '--topic', TOPIC,
                              '--human-validation', RECORD_FILE)
            self.assertEqual(ok.returncode, 0, ok.stderr)
            self.assertEqual(ok.stdout.decode('utf-8'), text)
            plain = self.run_cli('review_package.py', PACKAGE_FILE, '--question', QUESTION, '--topic', TOPIC)
            self.assertEqual(plain.stdout.decode('utf-8'), default)
            failed = self.run_cli('review_package.py', PACKAGE_FILE, '--question', QUESTION, '--topic', TOPIC,
                                  '--human-validation', broken_path)
            self.assertNotEqual(failed.returncode, 0)
            self.assertEqual(failed.stdout, b'')
            self.assertNotIn(b'Traceback', failed.stderr)
            self.assertEqual(PACKAGE_FILE.read_bytes(), before)

    def test_check_and_axis_do_not_mutate_inputs_read_files_or_call_providers(self):
        originals = copy.deepcopy((self.record, self.shipped))
        with patch.object(MockProvider, 'extract', side_effect=AssertionError('provider called')), \
             patch.object(Path, 'read_text', side_effect=AssertionError('file read')), \
             patch.object(Path, 'read_bytes', side_effect=AssertionError('file read')):
            result = check(self.record, self.shipped)
            report = axis(self.shipped, None, [self.record])
            blank = template(self.shipped)
        result['items'][0]['judgement'] = 'DISAGREE'
        result['raters'][0]['rater_id'] = 'mutated-output'
        report['records'][0]['judgement_counts']['AGREE'] = 99
        blank['items'][0]['item_id'] = 'mutated-output'
        self.assertEqual((self.record, self.shipped), originals)
        self.assertEqual(check(self.record, self.shipped),
                         check(json.loads(json.dumps(self.record)), json.loads(json.dumps(self.shipped))))

    def test_input_and_output_byte_bounds_fail_closed(self):
        with patch.object(hv, 'MAX_OUTPUT_BYTES', 10):
            with self.assertRaisesRegex(ValueError, '16 MiB'):
                hv._bounded('x' * 11)
        small = subprocess.run([sys.executable, '-c', 'import human_validation as h; h.MAX_INPUT_BYTES = 64; h.main()',
                                'check', str(RECORD_FILE), str(PACKAGE_FILE)], capture_output=True, timeout=60)
        self.assertNotEqual(small.returncode, 0)
        self.assertEqual(small.stdout, b'')
        self.assertIn(b'exceed 8 MiB', small.stderr)
        narrow = subprocess.run([sys.executable, '-c', 'import human_validation as h; h.MAX_OUTPUT_BYTES = 64; h.main()',
                                 'status', str(PACKAGE_FILE), '--human-validation', str(RECORD_FILE)], capture_output=True, timeout=60)
        self.assertNotEqual(narrow.returncode, 0)
        self.assertEqual(narrow.stdout, b'')
        self.assertIn(b'exceeds 16 MiB', narrow.stderr)
        review = subprocess.run([sys.executable, '-c', 'import human_validation as h; h.MAX_INPUT_BYTES = 64; '
                                 'import review_package; review_package.main()', str(PACKAGE_FILE), '--question', QUESTION,
                                 '--topic', TOPIC, '--human-validation', str(RECORD_FILE)], capture_output=True, timeout=60)
        self.assertNotEqual(review.returncode, 0)
        self.assertEqual(review.stdout, b'')
        self.assertIn(b'exceed 8 MiB', review.stderr)
        self.assertNotIn(b'Traceback', review.stderr)
        read = hv.bounded_reader(RECORD_FILE.stat().st_size)
        self.assertEqual(read(RECORD_FILE), self.record)
        with self.assertRaisesRegex(ValueError, 'exceed 8 MiB'):
            read(RECORD_FILE)

    def test_stale_record_against_rebuilt_package_is_reported_not_re_resolved(self):
        corpus = read('examples/research-corpus.json')
        record = completed(self.built)
        record['items'][0].update(judgement='DISAGREE', rationale='Synthetic disagreement with the rule derived from paper synthetic-0.')
        current = check(record, self.built)
        self.assertTrue(current['items_resolved_against_current_package'])
        self.assertEqual((current['unresolved_item_ids'], current['unresolved_topics']), ([], []))
        self.assertIn('Item resolution: resolved against the current package', hv.render_check(current))
        smaller = copy.deepcopy(corpus)
        smaller['papers'] = smaller['papers'][:-1]
        smaller.update(version='2', build_id='synthetic-rebuilt-smaller')
        smaller = build(smaller)
        self.assertEqual([rule['rule_id'] for rule in smaller['persona']['rules']], ['rule-1'])
        result = check(record, smaller)
        self.assertEqual(result['status'], 'HUMAN_VALIDATION_RECORD_CHECKED')
        self.assertEqual(result['binding_status'], 'STALE_PACKAGE')
        self.assertEqual(result['binding_differences'], ['version', 'build_id', 'persona_payload_sha256', 'knowledge_papers_sha256'])
        self.assertFalse(result['items_resolved_against_current_package'])
        self.assertEqual((result['unresolved_item_ids'], result['unresolved_topics']), (['rule-2'], []))
        self.assertEqual(result['judgement_counts'], dict(AGREE=1, PARTIAL=0, DISAGREE=1, NOT_ASSESSED=0))
        self.assertEqual(result['items'], record['items'])
        text = hv.render_check(result)
        self.assertIn('Item resolution: NOT re-resolved against the current package', text)
        self.assertIn('unresolved item IDs (absent from the current package): rule-2; '
                      'unresolved topics (absent from the current package): none', text)
        report = axis(smaller, None, [record])
        self.assertEqual((report['status'], report['stale_record_count']), ('STALE_PACKAGE', 1))
        self.assertFalse(report['records'][0]['items_resolved_against_current_package'])
        self.assertEqual(report['records'][0]['unresolved_item_ids'], ['rule-2'])
        self.assertIn('    Items not re-resolved against the current package (rule IDs are per-build positions); '
                      'unresolved item IDs (absent from the current package): rule-2', hv.render_status(report))
        reordered = copy.deepcopy(corpus)
        reordered['papers'].reverse()
        reordered.update(version='2', build_id='synthetic-reordered')
        reordered = build(reordered)
        self.assertEqual([rule['paper_id'] for rule in reordered['persona']['rules']], ['synthetic-1', 'synthetic-0'])
        swapped = check(record, reordered)
        self.assertEqual(swapped['binding_status'], 'STALE_PACKAGE')
        self.assertFalse(swapped['items_resolved_against_current_package'])
        self.assertEqual((swapped['unresolved_item_ids'], swapped['unresolved_topics']), ([], []))
        self.assertEqual(swapped['items'], record['items'])
        lines = hv.render_check(swapped).splitlines()
        marker = '  (recorded item IDs of the stale package; not re-resolved against the current rules)'
        self.assertIn(marker, lines)
        self.assertLess(lines.index(marker), lines.index(
            '  rule-1: DISAGREE | synthetic locator | Synthetic disagreement with the rule derived from paper synthetic-0.'))
        self.assertNotIn(marker, hv.render_check(current).splitlines())
        renamed = copy.deepcopy(corpus)
        for paper in renamed['papers']:
            for observation in paper['observations']:
                observation['topic'] = 'renamed synthetic topic'
        renamed = build(renamed)
        result = check(record, renamed)
        self.assertEqual((result['binding_status'], result['binding_differences']),
                         ('STALE_PACKAGE', ['persona_payload_sha256', 'knowledge_papers_sha256']))
        self.assertEqual((result['unresolved_item_ids'], result['unresolved_topics']), ([], ['model design']))
        for pattern, mutate in (('judgement', lambda r: r['items'][0].update(judgement='MAYBE')),
                                ('duplicate item_id', lambda r: r['items'].append(dict(r['items'][0]))),
                                ('rationale', lambda r: r['items'][0].update(rationale='')),
                                ('scope topic', lambda r: r.update(scope_topics=[7])),
                                ('duplicate scope topic', lambda r: r.update(scope_topics=['model design', 'model design'])),
                                ('missing or unknown', lambda r: r['items'][0].update(weight=1))):
            broken = copy.deepcopy(record)
            mutate(broken)
            with self.assertRaisesRegex(ValueError, pattern):
                check(broken, smaller)
        with self.assertRaisesRegex(ValueError, 'no rater label is distinct'):
            check(completed(self.built, rater=self.built['persona']['author_id']), smaller)
        unknown = copy.deepcopy(record)
        unknown['items'][0]['item_id'] = 'rule-99'
        with self.assertRaisesRegex(ValueError, 'not a rule_id'):
            check(unknown, self.built)

    def test_stale_record_cli_exits_zero_for_status_and_release_review(self):
        corpus = read('examples/research-corpus.json')
        record = completed(self.built)
        corpus['papers'] = corpus['papers'][:-1]
        corpus.update(version='2', build_id='synthetic-rebuilt-smaller')
        rebuilt = build(corpus)
        question, topic = 'Synthetic question?', 'model design'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / 'rebuilt-package.json'
            package.write_text(json.dumps(rebuilt), encoding='utf-8')
            stale = root / 'stale-record.json'
            stale.write_text(json.dumps(record), encoding='utf-8')
            before = {path: path.read_bytes() for path in (package, stale)}
            status = self.run_cli('human_validation.py', 'status', package, '--human-validation', stale)
            self.assertEqual(status.returncode, 0, status.stderr)
            status = json.loads(status.stdout)
            self.assertEqual((status['status'], status['current_record_count'], status['stale_record_count']),
                             ('STALE_PACKAGE', 0, 1))
            self.assertIs(status['records'][0]['items_resolved_against_current_package'], False)
            self.assertEqual(status['records'][0]['unresolved_item_ids'], ['rule-2'])
            text = self.run_cli('human_validation.py', 'status', package, '--human-validation', stale, '--text')
            self.assertEqual(text.returncode, 0, text.stderr)
            text = text.stdout.decode('utf-8')
            self.assertIn('Human validation axis: STALE_PACKAGE (records=1; current=0; stale=1)', text)
            self.assertIn('Items not re-resolved against the current package', text)
            checked = self.run_cli('human_validation.py', 'check', stale, package, '--text')
            self.assertEqual(checked.returncode, 0, checked.stderr)
            self.assertIn('Status: HUMAN_VALIDATION_RECORD_CHECKED; binding=STALE_PACKAGE', checked.stdout.decode('utf-8'))
            review = self.run_cli('review_package.py', package, '--question', question, '--topic', topic,
                                  '--human-validation', stale)
            self.assertEqual(review.returncode, 0, review.stderr)
            review = review.stdout.decode('utf-8')
            self.assertIn('Human validation axis: STALE_PACKAGE (records=1; current=0; stale=1)', review)
            self.assertIn('Items not re-resolved against the current package', review)
            self.assertEqual(review, render(rebuilt, question, topic, human_validation=[record]))
            self.assertEqual({path: path.read_bytes() for path in before}, before)

    def test_documented_guide_commands_execute_exactly_as_written(self):
        guide = (ROOT / 'docs' / 'HUMAN_VALIDATION.md').read_text(encoding='utf-8')
        blocks = re.findall(r'```sh\n(.*?)```', guide, re.S)
        self.assertEqual(len(blocks), 1)
        lines = [line for line in blocks[0].splitlines() if line.strip()]
        self.assertEqual(len(lines), 6)
        for line in lines:
            self.assertRegex(line, r'^python [a-z_]+\.py ')
            self.assertNotIn('>', line)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory).as_posix()
            outputs = []
            for line in lines:
                argv = shlex.split(line.replace('OUTPUT', output))
                argv[0] = sys.executable
                result = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=60)
                self.assertEqual(result.returncode, 0, line + '\n' + result.stderr.decode('utf-8', 'replace'))
                outputs.append(result.stdout.decode('utf-8'))
            self.assertIn('"available_topics": []', outputs[0])
            self.assertIn('Human validation axis: NOT_PERFORMED', outputs[1])
            self.assertIn('"rule-6"', outputs[2])
            self.assertIn('binding=CURRENT_PACKAGE', outputs[3])
            self.assertIn('AGREE=3; PARTIAL=1; DISAGREE=1; NOT_ASSESSED=1', outputs[3])
            self.assertIn('Human validation axis: RECORDED_CURRENT (records=1; current=1; stale=0)', outputs[4])
            self.assertIn('CONTESTED: Method M', outputs[5])
            self.assertIn('Human validation axis: RECORDED_CURRENT', outputs[5])
            self.assertEqual(sorted(path.name for path in Path(directory).iterdir()),
                             ['minimal-human-validation-template.json', 'trajectory-human-validation-template.json'])


if __name__ == '__main__':
    unittest.main()
