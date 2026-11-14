"""Static release-index checks; never execute the documented commands."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENTRY = re.compile(r'^## (0\.(\d+)-[a-z0-9-]+) — (\d{4}-\d{2}-\d{2})$', re.M)


def heading_anchor(heading):
    # These history titles use ASCII letters, digits, spaces, hyphens and punctuation.
    return re.sub(r'[^\w\- ]', '', heading.lower()).replace(' ', '-')


class ChangelogTests(unittest.TestCase):
    def setUp(self):
        self.index = (ROOT/'CHANGELOG.md').read_text(encoding='utf-8')
        self.history = (ROOT/'docs/VALIDATION_HISTORY.md').read_text(encoding='utf-8')
        self.entries = list(ENTRY.finditer(self.index))

    def test_top_entry_matches_manifest_release_and_date(self):
        self.assertTrue(self.entries)
        manifest = json.loads((ROOT/'PUBLICATION_MANIFEST.json').read_text(encoding='utf-8'))
        self.assertEqual(self.entries[0][1], manifest['release'])
        self.assertEqual(self.entries[0][3], manifest['date'])

    def test_each_entry_links_its_exact_history_title(self):
        titles = re.findall(r'^## (.+)$', self.history, re.M)
        for i, entry in enumerate(self.entries):
            end = self.entries[i+1].start() if i+1 < len(self.entries) else len(self.index)
            block = self.index[entry.end():end]
            matching = [title for title in titles if re.search(r'(?<![\w.-])'+re.escape(entry[1])+r'(?![\w.-])', title)]
            with self.subTest(release=entry[1]):
                self.assertEqual(len(matching), 1)
                self.assertTrue(matching[0].startswith(entry[3]+' '))
                expected = 'docs/VALIDATION_HISTORY.md#'+heading_anchor(matching[0])
                self.assertEqual(re.findall(r'\]\((docs/VALIDATION_HISTORY\.md#[^)]+)\)', block), [expected])

    def test_all_dated_releases_since_069_have_one_descending_entry(self):
        numbers = [int(entry[2]) for entry in self.entries]
        self.assertEqual(numbers, list(range(max(numbers), 68, -1)))
        releases = [entry[1] for entry in self.entries]
        self.assertEqual(len(set(releases)), len(releases))
        history_releases = []
        for title in re.findall(r'^## \d{4}-\d{2}-\d{2} (.+)$', self.history, re.M):
            match = re.search(r'\b(0\.(\d+)-[a-z0-9-]+)', title)
            if match and int(match[2]) >= 69: history_releases.append(match[1])
        self.assertEqual(set(releases), set(history_releases))

    def test_readme_links_and_documented_scripts_exist(self):
        self.assertIn('](CHANGELOG.md)', (ROOT/'README.md').read_text(encoding='utf-8'))
        self.assertIn('](../CHANGELOG.md)', (ROOT/'docs/README.ko.md').read_text(encoding='utf-8'))
        for name in set(re.findall(r'\b[a-z_]+\.py\b', self.index)):
            self.assertTrue((ROOT/name).is_file(), name)
        self.assertNotIn('```sh', self.index)
        self.assertIn('not Git tags, signatures, rights clearance or persona approval', self.index)

    def test_known_heading_punctuation_and_backticks(self):
        self.assertEqual(heading_anchor('2026-11-08 Public boundary cleanup (0.69-public-boundary-cleanup)'),
                         '2026-11-08-public-boundary-cleanup-069-public-boundary-cleanup')
        self.assertEqual(heading_anchor('2026-11-14 Release change index (`0.93-change-index`)'),
                         '2026-11-14-release-change-index-093-change-index')


if __name__ == '__main__':
    unittest.main()
