"""Supported subset tests and fixed read-only audit, not a whole-guide execution claim."""
import copy,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from tests import doc_conformance as d

class DocConformanceTests(unittest.TestCase):
    def test_codes_escapes_fences_and_multiline_spans_are_not_links(self):
        text='''# Heading
`[fake](missing.md)`
``multiline
[fake](missing.md)``
\\[escaped](missing.md)
    [indented](missing.md)
~~~sh
python ignored.py
[fake](missing.md)
~~~
[real](README.md)
'''
        r=d.parse_markdown(text)
        self.assertEqual(r['links'],[dict(line=11,destination='README.md')]);self.assertEqual(len(r['blocks']),1)
        self.assertEqual(r['unresolved'],[])
    def test_references_nested_parentheses_titles_images_and_autolinks(self):
        r=d.parse_markdown('[label][ref]\n[ref]: <docs/a%20b.md#part> "title"\n![x](image.png)\n[paren](a(b).md)\n[ref][]\n[ref]\n<https://example.invalid/path>\n')
        self.assertEqual([x['destination'] for x in r['links']],['docs/a%20b.md#part','image.png','a(b).md','docs/a%20b.md#part','docs/a%20b.md#part','https://example.invalid/path'])
        self.assertEqual(r['unresolved'],[])
    def test_unicode_duplicate_heading_collisions_and_percent_anchor(self):
        r=d.parse_markdown('# 한글 제목\n# Same\n# Same\n# Same-1\nTitle\n-----\n')
        self.assertEqual(r['headings'],['한글-제목','same','same-1','same-1-1','title'])
        self.assertEqual(d.parse_markdown('# `code` and *emphasis*\n')['headings'],['code-and-emphasis'])
    def test_multiline_html_comment_is_unresolved_not_a_real_link(self):
        result=d.parse_markdown('<!-- comment\n[fake](missing.md)\n# Fake heading\n-->\n[real](README.md)\n')
        self.assertEqual(result['links'],[dict(line=5,destination='README.md')])
        self.assertEqual(result['headings'],[])
        self.assertTrue(result['unresolved'])

    def test_unresolved_not_silent_success(self):
        for text,code in [('[x][missing]','UNRESOLVED_REFERENCE'),('[x](bad','UNRESOLVED_INLINE_LINK'),('<a id="custom">x</a>','UNRESOLVED_HTML'),('```sh\nx','UNRESOLVED_UNCLOSED_FENCE'),('# [title](a.md)','UNRESOLVED_COMPLEX_HEADING')]:
            self.assertIn(code,[x['code'] for x in d.parse_markdown(text)['unresolved']])
    def test_complex_reference_entity_headings_do_not_invent_slugs(self):
        for heading in ('# [Label][ref]', '# [ref]', '# A &amp; B', '# A &#38; B', '# A &#x26; B'):
            result=d.parse_markdown(heading+'\n[ref]: README.md\n')
            self.assertEqual(result['headings'],[])
            self.assertIn('UNRESOLVED_COMPLEX_HEADING',[x['code'] for x in result['unresolved']])
        with tempfile.TemporaryDirectory() as td:
            root=Path(td).resolve();self.make_root(root)
            (root/'README.md').write_text('[anchor](docs/a.md#label)\n')
            (root/'docs/a.md').write_text('# [Label][ref]\n[ref]: ../README.md\n')
            with patch.object(d,'ROOT',root):report=d.audit()
            self.assertNotIn('MISSING_ANCHOR',[x['code'] for x in report['errors']])
            self.assertIn('UNRESOLVED_ANCHOR_TARGET',[x['code'] for x in report['unresolved']])

    def test_blockquote_references_shortcuts_and_autolinks_are_unresolved(self):
        for quote in ('> [x][ref]', '> [ref]', '> [ref][]', '> <https://example.invalid>', '> [x](missing.md)'):
            result=d.parse_markdown('[ref]: missing.md\n'+quote+'\n')
            self.assertEqual(result['links'],[])
            self.assertIn('UNRESOLVED_BLOCKQUOTE_SYNTAX',[x['code'] for x in result['unresolved']])

    def test_definitions_inside_multiline_code_or_comments_are_not_adopted(self):
        for prefix in ('`example\n[ref]: missing.md\n`\n','<!--\n[ref]: missing.md\n-->\n','``example\n[ref]: missing.md\n``\n'):
            result=d.parse_markdown(prefix+'[x][ref]\n')
            self.assertEqual(result['links'],[])
            self.assertIn('UNRESOLVED_REFERENCE',[x['code'] for x in result['unresolved']])
        result=d.parse_markdown('`example\n# Fake heading\n[ref]: missing.md\n`\n[ref]: real.md\n[x][ref]\n')
        self.assertEqual(result['headings'],[])
        self.assertEqual([x['destination'] for x in result['links']],['real.md'])

    def make_root(self,path):
        (path/'docs').mkdir();(path/'tests').mkdir();(path/'tests/doc_block_evidence.json').write_bytes(b'[]\n')
        (path/'README.md').write_bytes('# Root\n[ok](docs/a.md#%ED%95%9C%EA%B8%80)\n[bad](missing.md)\n[anchor](docs/a.md#missing)\n[network](https://example.invalid)\n'.encode())
        (path/'docs/a.md').write_bytes('# 한글\n```sh\npython synthetic.py\n```\n'.encode())
    def test_real_resolution_and_budget_no_external_calls(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td).resolve();self.make_root(root)
            with patch.object(d,'ROOT',root),patch('socket.socket',side_effect=AssertionError('network')),patch('subprocess.run',side_effect=AssertionError('execution')):
                report=d.audit()
                self.assertEqual(report['status'],'REVIEW_REQUIRED');self.assertEqual(report['checked_local_links'],1)
                self.assertEqual(report['external_links_not_checked'],1)
                self.assertEqual({x['code'] for x in report['errors']},{'MISSING_LINK_TARGET','MISSING_ANCHOR'})
                self.assertEqual(report['block_counts'],{'NOT_REVIEWED':1});self.assertFalse(report['guide_execution_performed'])
                with patch.object(d,'MAX_INPUT_BYTES',1),self.assertRaises(ValueError):d.audit()
                with patch.object(d,'MAX_OUTPUT_BYTES',1),self.assertRaises(ValueError):d.audit()
    def test_stale_block_or_test_never_inherits_execution_evidence(self):
        import ast,hashlib
        with tempfile.TemporaryDirectory() as td:
            root=Path(td).resolve();self.make_root(root)
            test='class Owner:\n    def test_guide(self):\n        pass\n';(root/'tests/test_owner.py').write_text(test)
            node=ast.parse(test).body[0].body[0]
            block=d.parse_markdown((root/'docs/a.md').read_text(encoding='utf-8'))['blocks'][0]
            row=dict(path='docs/a.md',ordinal=1,raw_sha256=block['raw_sha256'],test='tests.test_owner.Owner.test_guide',test_source_sha256=d.method_source_sha256(test,node),coverage='PARTIAL_BLOCK',substitution='Synthetic declared partial fixture',manual_steps='Explicit fixture step',note='Test existence alone is not proof; this is a synthetic registry test.')
            reg=root/'tests/doc_block_evidence.json';reg.write_text(json.dumps([row]))
            with patch.object(d,'ROOT',root):
                self.assertEqual(d.audit()['blocks'][0]['state'],'EXISTING_TEST_RECORD')
                (root/'docs/a.md').write_text('# Heading\n```sh\npython changed.py\n```\n')
                self.assertEqual(d.audit()['blocks'][0]['state'],'STALE_EVIDENCE')
                (root/'tests/test_owner.py').write_text(test.replace('pass','return 1'))
                self.assertIn('CHANGED_EVIDENCE_TEST',[e['code'] for e in d.audit()['errors']])
    def test_method_source_digest_ignores_python_ast_fields_not_formatting(self):
        import ast
        source='class Owner:\n    def test_guide(self):\n        return "한글"\n'
        node=ast.parse(source).body[0].body[0]
        digest=d.method_source_sha256(source,node)
        old_fields=node._fields
        # Simulate Python3.12's extra type_params versus Python3.10 AST layout.
        node._fields=tuple(k for k in old_fields if k!='type_params')
        self.assertNotIn('type_params',dict(ast.iter_fields(node)))
        self.assertEqual(digest,d.method_source_sha256(source,node))
        node._fields=node._fields+('type_params',);node.type_params=[]
        self.assertIn('type_params',dict(ast.iter_fields(node)))
        self.assertEqual(digest,d.method_source_sha256(source,node))
        for raw in (source.replace('\n','\r\n'),source.replace('\n','\r')):
            normalized=raw.replace('\r\n','\n').replace('\r','\n')
            selected=ast.parse(normalized).body[0].body[0]
            self.assertEqual(digest,d.method_source_sha256(raw,selected))
        moved='\n'+source
        self.assertEqual(digest,d.method_source_sha256(moved,ast.parse(moved).body[0].body[0]))
        changed=source.replace('return "한글"','return  "한글"')
        self.assertNotEqual(digest,d.method_source_sha256(changed,ast.parse(changed).body[0].body[0]))

    def test_fixed_repository_audit_is_deterministic_read_only(self):
        files=[*d._files(),d.ROOT/'tests/doc_block_evidence.json'];before={p:p.read_bytes() for p in files}
        with patch('socket.socket',side_effect=AssertionError('network')),patch('subprocess.run',side_effect=AssertionError('execution')):
            a=d.audit();b=d.audit()
        self.assertEqual(a,b);self.assertEqual(before,{p:p.read_bytes() for p in files})
        self.assertFalse(a['guide_execution_performed']);self.assertGreater(a['block_counts']['NOT_REVIEWED'],0)
        self.assertEqual(a['block_counts']['EXISTING_TEST_RECORD'],7)
    def test_fixed_root_and_fixture_alias_are_canonical_before_patch(self):
        self.assertEqual(d.ROOT,d.ROOT.resolve())
        with tempfile.TemporaryDirectory() as td:
            root=Path(td).resolve();self.make_root(root);(root/'child').mkdir()
            alias=(Path(td)/'child'/'..').resolve()
            self.assertEqual(alias,root)
            with patch.object(d,'ROOT',root):expected=d.audit()
            with patch.object(d,'ROOT',alias):self.assertEqual(d.audit(),expected)

    def test_maintainer_cli_accepts_no_private_path(self):
        p=subprocess.run([sys.executable,'-m','tests.doc_conformance','private.md'],cwd=d.ROOT,capture_output=True)
        self.assertEqual(p.returncode,2);self.assertEqual(p.stdout,b'')

if __name__=='__main__':unittest.main()
