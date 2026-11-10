"""Static checks only: the agent contract must not promise absent tools."""
import json
import re
import unittest
from pathlib import Path
from tests.test_dispatcher import entry_point_scripts

ROOT=Path(__file__).resolve().parents[1]


class SkillContractTests(unittest.TestCase):
    def setUp(self):
        self.raw=(ROOT/'SKILL.md').read_bytes();self.text=self.raw.decode('utf-8')

    def test_frontmatter_size_and_boundaries(self):
        self.assertTrue(self.text.startswith('---\nname: persona-for-research\n'))
        self.assertEqual(json.loads((ROOT/'PUBLICATION_MANIFEST.json').read_text())['project'],'persona-for-research')
        self.assertLessEqual(len(self.raw),8192)
        for sentinel in ('report missing backends instead of fabricating','Never edit `validation.human_validation`'):
            self.assertIn(sentinel,self.text)
        self.assertNotIn('```sh',self.text)

    def test_all_named_scripts_and_documents_exist(self):
        entries=set(entry_point_scripts())|{'persona_cli.py'}
        for name in set(re.findall(r'\b[a-z_]+\.py\b',self.text)):
            self.assertTrue((ROOT/name).is_file(),name)
            # Library references are allowed; entry points must appear in COMMANDS.
            if name in entries:self.assertIn('### `'+name+'`',(ROOT/'docs/COMMANDS.md').read_text())
        for name in set(re.findall(r'(?<![\w/])(?:docs/)?[A-Z_]+\.md\b',self.text)):
            self.assertTrue((ROOT/name).is_file(),name)

    def test_explicit_script_subcommands_are_documented(self):
        commands=(ROOT/'docs/COMMANDS.md').read_text()
        for script,command in re.findall(r'\b([a-z_]+\.py) ([a-z][a-z-]*)\b',self.text):
            self.assertIn('usage: '+script+' '+command,commands)
