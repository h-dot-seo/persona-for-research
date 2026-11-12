"""Execute the synthetic teaching guide, not a scientific validation workflow."""
import copy
import json
import re
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from prepare_local_manifest import prepare
from curate_local import append_observation, template
from journey_inputs import prepare as prepare_journey

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / 'examples/teaching-sources'
CARDS = ROOT / 'examples/teaching-cards'
ORDER = ('models-research', 'models-review', 'sampling-research', 'sampling-review',
         'calibration-research', 'calibration-review')


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def regenerate_cards():
    """Test-only binding replay; retain explicit fixture observations, never infer them.

    Maintainers can use the returned cards after reviewing source/prepare changes.
    This function does not write fixtures or hide drift from assertions.
    """
    manifest = prepare(read(ROOT / 'examples/teaching-selection.json'), SOURCES)
    cards = []
    for name in ORDER:
        supplied = read(CARDS / (name + '.json'))
        card = template(manifest, supplied['paper_id'])
        card['observation'] = copy.deepcopy(supplied['observation'])
        cards.append(card)
        manifest = append_observation(manifest, card, SOURCES)
    return cards


def execute_guide(output):
    """Run literal argv without a shell, then apply the marked top-level JSON edits."""
    guide = (ROOT / 'docs/TUTORIAL_OWN_FILES.md').read_text(encoding='utf-8')
    blocks = re.findall(r'(?:<!-- edit: ([^\n]+) -->\n)?```(sh|json)\n(.*?)```', guide, re.S)
    commands, edits = [], []
    for target, language, body in blocks:
        if language == 'json':
            if not target.startswith('OUTPUT/'):
                raise AssertionError('Every edit needs an explicit output target')
            path = output / target[len('OUTPUT/'):]
            if not path.is_file() or output.resolve() not in path.resolve().parents:
                raise AssertionError('Edit must target an existing external artifact')
            value = read(path)
            changes = json.loads(body)
            if not set(changes) <= set(value):
                raise AssertionError('Edits may only replace existing top-level fields')
            value.update(changes)
            path.write_bytes((json.dumps(value, indent=2, ensure_ascii=True) + '\n').encode('utf-8'))
            edits.append(target)
        else:
            if target:
                raise AssertionError('Unexpected shell edit marker')
            for line in body.splitlines():
                if not line.strip():
                    continue
                if not re.match(r'^python [a-z_]+\.py ', line) or '>' in line:
                    raise AssertionError('Use direct Python commands and --output')
                argv = shlex.split(line)
                argv = [str(output / arg[len('OUTPUT/'):]) if arg.startswith('OUTPUT/') else arg for arg in argv]
                argv[0] = sys.executable
                result = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=60)
                if result.returncode:
                    raise AssertionError(line + '\n' + result.stderr.decode('utf-8', 'replace'))
                commands.append(line)
    return commands, edits


class TeachingTutorialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory(prefix='teaching files external ')
        cls.addClassCleanup(cls.directory.cleanup)
        cls.output = Path(cls.directory.name)
        cls.before = {p: p.read_bytes() for p in [ROOT / 'examples/teaching-selection.json',
                     *SOURCES.glob('*.md'), *CARDS.glob('*.json')]}
        cls.commands, cls.edits = execute_guide(cls.output)

    def result(self, name):
        return read(self.output / name)

    def test_exact_guide_executes_once_with_explicit_edits_and_preserves_fixtures(self):
        self.assertEqual(len(self.commands), 15)
        self.assertEqual(self.edits, ['OUTPUT/first-card.json', 'OUTPUT/workspace/patterns.json',
                                    'OUTPUT/workspace/journey-file-selection.json'])
        self.assertEqual(self.result('first-card.json'), read(CARDS / 'models-research.json'))
        self.assertEqual({p: p.read_bytes() for p in self.before}, self.before)
        self.assertTrue((self.output / 'workspace/READY.json').is_file())
        for path in self.output.rglob('*'):
            if path.is_file():
                self.assertNotIn(b'\r', path.read_bytes())
                self.assertFalse(path.read_bytes().startswith(b'\xef\xbb\xbf'))

    def test_cards_replay_exactly_and_sources_are_unmistakably_synthetic(self):
        self.assertEqual(regenerate_cards(), [read(CARDS / (name + '.json')) for name in ORDER])
        selection = read(ROOT / 'examples/teaching-selection.json')
        self.assertEqual(selection['author_id'], 'synthetic-scholar')
        self.assertEqual(len(selection['papers']), 6)
        for paper in selection['papers']:
            self.assertTrue(paper['paper_id'].startswith('synthetic-teach-'))
            text = (SOURCES / paper['source_file']).read_bytes().decode('ascii')
            self.assertTrue(text.startswith('SYNTHETIC TEACHING FIXTURE'))
            self.assertEqual(text.count('\n## '), 2)
        self.assertEqual({p['year'] for p in selection['papers']}, {2019, 2020, 2021, 2022, 2023})

    def test_three_topics_and_review_kind_survive_source_intake(self):
        topics = self.result('topics.json')
        self.assertEqual(topics['status'], 'TOPIC_INVENTORY_ONLY')
        self.assertEqual(len(topics['topics']), 3)
        for row in topics['topics']:
            self.assertEqual(row['observation_count'], 2)
            self.assertEqual(len(row['paper_ids_by_kind']['research']), 1)
            self.assertEqual(len(row['paper_ids_by_kind']['review']), 1)
        papers = self.result('intake.json')['package']['knowledge']['papers']
        self.assertEqual(sum(len(p['observations']) for p in papers), 6)
        self.assertEqual(sum(p['kind'] == 'review' for p in papers), 3)
        self.assertIn('invented Cedar group', papers[1]['observations'][0]['evidence_quote'])
        self.assertEqual(papers[1]['observations'][0]['claim_type'], 'operator_interpretation')

    def test_declared_disagreement_is_visible_without_semantic_approval(self):
        trajectory = self.result('intake.json')['application']['methodology_trajectory']
        rendered = json.dumps(trajectory)
        self.assertIn('MIXED_STANCES', rendered)
        self.assertIn('"within_year_disagreement": true', rendered)
        evidence = (self.output / 'evidence.txt').read_text(encoding='utf-8')
        for marker in ('CONTESTED: Compare toy models', '[support]', '[challenge]'):
            self.assertIn(marker, evidence)

    def test_journey_remains_unapproved_and_all_later_authoring_empty(self):
        journey = self.result('research-journey.json')
        self.assertEqual(journey['status'], 'HUMAN_REVIEW_REQUIRED_NOT_RESEARCH_APPROVAL')
        self.assertFalse(journey['automatic_approval'])
        self.assertFalse(journey['source_reread'])
        for name, field in (('answer', 'claims'), ('design', 'steps'), ('links', 'links'), ('argument', 'steps')):
            self.assertEqual(self.result('workspace/' + name + '.json')[field], [])
        self.assertTrue(all(row['decision'] == 'defer' for row in self.result('workspace/context.json')['assessments']))
        html = (self.output / 'research-journey.html').read_text(encoding='utf-8')
        for marker in ('HUMAN_REVIEW_REQUIRED_NOT_RESEARCH_APPROVAL', 'NO_ANSWER_CLAIMS',
                       'NO_PROPOSED_STEPS', 'NO_SUPPLIED_LINKS', 'NO_DECLARED_ARGUMENT_STEPS',
                       'REASONING_DIMENSION_NOT_SUPPLIED', 'SAME_YEAR_ORDER_UNRESOLVED'):
            self.assertIn(marker, html)

    def test_required_manual_pattern_selection_and_stale_cards_reject(self):
        selection = self.result('workspace/journey-file-selection.json')
        selection['pattern_id'] = None
        with self.assertRaisesRegex(ValueError, 'pattern_id'):
            prepare_journey(selection, self.output / 'workspace')
        with self.assertRaisesRegex(ValueError, 'stale manifest'):
            append_observation(self.result('curated-1.json'), read(CARDS / 'models-research.json'), SOURCES)
        manifest = self.result('prepared.json')
        manifest['papers'][-1]['split'] = 'holdout'
        with self.assertRaises(ValueError):
            append_observation(manifest, read(CARDS / 'models-research.json'), SOURCES)


if __name__ == '__main__':
    unittest.main()
