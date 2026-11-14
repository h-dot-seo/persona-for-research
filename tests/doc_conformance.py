"""Read-only, fixed-repository Markdown subset audit; not a CommonMark parser or execution proof."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit
from strict_json import read_bounded, loads

ROOT=Path(__file__).resolve().parents[1]
MAX_INPUT_BYTES=8*1024*1024
MAX_OUTPUT_BYTES=16*1024*1024
BOUNDARY=('Fixed repository documentation only. Supported Markdown subset, not full CommonMark or GitHub rendering. '
 'External URLs are not fetched or verified. Unresolved syntax is not a passed link. Block evidence records '
 'describe reviewed test ownership, not a test run or proof that every command executes. No shell, script, '
 'network call or file write is performed. Existing command/usage, SKILL and CHANGELOG checks remain separate.')


def _unescape(value):
    return re.sub(r'\\([!"#$%&\'()*+,\-./:;<=>?@\[\]\\^_`{|}~])',r'\1',value)


def _norm(value):return ' '.join(_unescape(value).split()).casefold()


def _inline_mask(line):
    """Mask backtick spans and escaped punctuation while preserving offsets."""
    out=list(line);i=0;unclosed=False
    while i<len(line):
        if line[i]=='\\' and i+1<len(line):out[i]=out[i+1]=' ';i+=2;continue
        if line[i]=='`':
            j=i
            while j<len(line) and line[j]=='`':j+=1
            run=line[i:j];end=line.find(run,j)
            while end>=0 and ((end and line[end-1]=='`') or (end+len(run)<len(line) and line[end+len(run)]=='`')):end=line.find(run,end+len(run))
            if end<0:unclosed=True;i=j;continue
            out[i:end+len(run)]=['\n' if c=='\n' else ' ' for c in line[i:end+len(run)]];i=end+len(run);continue
        i+=1
    return ''.join(out),unclosed


def _balanced(text,start,left,right):
    depth=0;i=start
    while i<len(text):
        if text[i]=='\\':i+=2;continue
        if text[i]==left:depth+=1
        elif text[i]==right:
            depth-=1
            if depth==0:return i
        i+=1
    return None


def _destination(raw):
    raw=raw.strip()
    if raw.startswith('<'):
        end=raw.find('>')
        if end<0:return None
        dest=raw[1:end];tail=raw[end+1:].strip()
    else:
        depth=0;end=len(raw)
        for i,c in enumerate(raw):
            if c=='\\':continue
            if c=='(':depth+=1
            elif c==')':depth-=1
            elif c.isspace() and depth==0:end=i;break
        dest=raw[:end];tail=raw[end:].strip()
    if tail and not ((tail[0:1]==tail[-1:] and tail[0:1] in ('"',"'")) or (tail.startswith('(') and tail.endswith(')'))):return None
    return _unescape(dest)


def parse_markdown(text):
    """Return supported local-link candidates, headings, fenced sh blocks and explicit gaps."""
    lines=text.splitlines(keepends=True);visible=[];blocks=[];issues=[];fence=None;start=0;body=[];language=''
    for n,line in enumerate(lines,1):
        stripped=line.rstrip('\r\n')
        if fence:
            if re.fullmatch(r' {0,3}'+re.escape(fence[0])+r'{'+str(len(fence))+r',}[ \t]*',stripped):
                if language=='sh':blocks.append(dict(ordinal=len(blocks)+1,line=start,raw_sha256=hashlib.sha256(''.join(body).encode('utf-8')).hexdigest()))
                fence=None
            else:body.append(line)
            visible.append((n,''));continue
        m=re.match(r'^ {0,3}(`{3,}|~{3,})([^\r\n]*)$',stripped)
        if m:
            fence=m[1];language=m[2].strip();start=n;body=[];visible.append((n,''));continue
        if stripped.startswith(('    ','\t')):
            visible.append((n,''));continue  # supported indented code, not list-nested Markdown
        if re.match(r'^ {0,3}>',stripped):issues.append(dict(line=n,code='UNRESOLVED_BLOCKQUOTE_SYNTAX'));visible.append((n,''));continue
        visible.append((n,stripped))
    if fence:issues.append(dict(line=start,code='UNRESOLVED_UNCLOSED_FENCE'))
    # Mask supported multiline code and comments BEFORE gathering definitions.
    all_masked,unclosed=_inline_mask('\n'.join(line for _,line in visible))
    masked_lines=all_masked.split('\n')
    if unclosed:issues.append(dict(line=1,code='UNRESOLVED_INLINE_CODE'))
    definitions={};content=[];content_masks=[];comment=False
    for i,(n,line) in enumerate(visible):
        masked=masked_lines[i]
        if comment or '<!--' in masked:
            issues.append(dict(line=n,code='UNRESOLVED_HTML_COMMENT'))
            comment='-->' not in masked
            content.append((n,''));content_masks.append('');continue
        m=re.match(r'^ {0,3}\[([^\]]+)\]:\s*(.*)$',line)
        prefix=re.match(r'^ {0,3}\[([^\]]+)\]:',masked)
        if m and prefix:
            dest=_destination(m[2]);key=_norm(m[1])
            if dest is None or key in definitions:issues.append(dict(line=n,code='UNRESOLVED_REFERENCE_DEFINITION'))
            else:definitions[key]=dest
            content.append((n,''));content_masks.append('');continue
        content.append((n,line));content_masks.append(masked)
    links=[];headings=[];slugs=Counter();used_slugs=set()
    for i,(n,line) in enumerate(content):
        masked=content_masks[i]
        if not masked.strip():continue
        heading=re.match(r'^ {0,3}#{1,6}\s+(.+?)\s*#*\s*$',line)
        title=heading[1] if heading else None
        if not title and line.strip() and i+1<len(content) and re.fullmatch(r' {0,3}(?:=+|-+)\s*',content[i+1][1]):title=line.strip()
        if title:
            # Limited plain/inline-code/emphasis headings. Complex link/HTML headings are unresolved.
            if re.search(r'<|\[|&(?:#[xX][0-9a-fA-F]+|#[0-9]+|[A-Za-z][A-Za-z0-9]+);',title):issues.append(dict(line=n,code='UNRESOLVED_COMPLEX_HEADING'))
            else:
                slug=re.sub(r'[^\w\- ]','',_unescape(title).lower()).replace(' ','-')
                index=slugs[slug];candidate=slug+('-'+str(index) if index else '')
                while candidate in used_slugs:index+=1;candidate=slug+'-'+str(index)
                slugs[slug]=index+1;used_slugs.add(candidate);headings.append(candidate)
        for auto in re.finditer(r'<([A-Za-z][A-Za-z0-9+.-]*:[^<>\s]*)>',masked):links.append(dict(line=n,destination=auto[1]))
        masked=re.sub(r'<[A-Za-z][A-Za-z0-9+.-]*:[^<>\s]*>',lambda m:' '*len(m[0]),masked)
        if '<!--' in masked or re.search(r'<[A-Za-z/!]',masked):
            issues.append(dict(line=n,code='UNRESOLVED_HTML'));continue
        pos=0
        while pos<len(masked):
            start=masked.find('[',pos)
            if start<0:break
            end=_balanced(line,start,'[',']')
            if end is None:issues.append(dict(line=n,code='UNRESOLVED_BRACKET'));break
            label=line[start+1:end];after=end+1;dest=None
            if after<len(line) and line[after]=='(':
                close=_balanced(line,after,'(',')')
                if close is None:issues.append(dict(line=n,code='UNRESOLVED_INLINE_LINK'));break
                dest=_destination(line[after+1:close]);pos=close+1
                if dest is None:issues.append(dict(line=n,code='UNRESOLVED_LINK_DESTINATION'))
            elif after<len(line) and line[after]=='[':
                close=_balanced(line,after,'[',']')
                if close is None:issues.append(dict(line=n,code='UNRESOLVED_REFERENCE'));break
                key=_norm(line[after+1:close] or label);dest=definitions.get(key);pos=close+1
                if dest is None:issues.append(dict(line=n,code='UNRESOLVED_REFERENCE'))
            else:
                dest=definitions.get(_norm(label));pos=end+1
                # Ordinary bracket prose is not assumed to be a broken reference.
            if dest is not None:links.append(dict(line=n,destination=dest))
    return dict(links=links,headings=headings,blocks=blocks,unresolved=issues)


def _files():
    result=sorted([*ROOT.glob('*.md'),*(ROOT/'docs').glob('*.md')])
    if len(result)>4096:raise ValueError('too many documentation files')
    return result


def audit():
    remaining=MAX_INPUT_BYTES;documents={};parsed={}
    for path in _files():
        if path.is_symlink() or path.resolve().parent not in (ROOT.resolve(),(ROOT/'docs').resolve()):raise ValueError('documentation path outside fixed scope')
        raw=read_bounded(path,remaining);remaining-=len(raw)
        name=path.relative_to(ROOT).as_posix();documents[name]=raw;parsed[name]=parse_markdown(raw.decode('utf-8'))
    registry_path=ROOT/'tests/doc_block_evidence.json'
    if registry_path.is_symlink() or registry_path.resolve().parent!=(ROOT/'tests').resolve():raise ValueError('registry outside fixed scope')
    registry_raw=read_bounded(registry_path,remaining);remaining-=len(registry_raw);registry=loads(registry_raw)
    if not isinstance(registry,list):raise ValueError('invalid block evidence registry')
    indexed={};errors=[];unresolved=[];external=0;checked=0;blocks=[]
    for row in registry:
        if set(row)!={'path','ordinal','raw_sha256','test','test_ast_sha256','coverage','substitution','manual_steps','note'}:raise ValueError('invalid block evidence row')
        if (type(row['ordinal']) is not int or row['ordinal']<1 or row['coverage'] not in ('FULL_BLOCK','FULL_BLOCK_EXPECTED_REJECTION','PARTIAL_BLOCK')
                or any(not isinstance(row[k],str) for k in ('path','raw_sha256','test','test_ast_sha256','substitution','manual_steps','note'))
                or any(re.fullmatch('[0-9a-f]{64}',row[k]) is None for k in ('raw_sha256','test_ast_sha256'))):raise ValueError('invalid block evidence metadata')
        key=(row['path'],row['ordinal'])
        if key in indexed:raise ValueError('duplicate block evidence')
        indexed[key]=row
    used=set()
    for name,p in parsed.items():
        unresolved.extend(dict(path=name,**item) for item in p['unresolved'])
        for link in p['links']:
            dest=link['destination'];u=urlsplit(dest)
            if u.scheme or u.netloc:external+=1;continue
            if u.query:unresolved.append(dict(path=name,line=link['line'],code='UNRESOLVED_LOCAL_QUERY'));continue
            relative=unquote(u.path);target=(ROOT/name).parent/relative if relative else ROOT/name
            target=target.resolve()
            if not target.is_relative_to(ROOT.resolve()):errors.append(dict(path=name,line=link['line'],code='LINK_OUTSIDE_REPOSITORY'));continue
            if not target.exists():errors.append(dict(path=name,line=link['line'],code='MISSING_LINK_TARGET',target=target.relative_to(ROOT).as_posix()));continue
            key=target.relative_to(ROOT).as_posix()
            if u.fragment:
                if key not in parsed:unresolved.append(dict(path=name,line=link['line'],code='UNRESOLVED_NON_MARKDOWN_ANCHOR'));continue
                if parsed[key]['unresolved']:
                    unresolved.append(dict(path=name,line=link['line'],code='UNRESOLVED_ANCHOR_TARGET',target=key));continue
                if unquote(u.fragment) not in parsed[key]['headings']:errors.append(dict(path=name,line=link['line'],code='MISSING_ANCHOR',target=key,fragment=u.fragment));continue
            checked+=1
        for block in p['blocks']:
            key=(name,block['ordinal']);evidence=indexed.get(key);state='NOT_REVIEWED'
            if evidence:
                used.add(key);state='EXISTING_TEST_RECORD'
                if evidence['raw_sha256']!=block['raw_sha256']:state='STALE_EVIDENCE';errors.append(dict(path=name,code='STALE_BLOCK_EVIDENCE',ordinal=block['ordinal']))
                test=evidence['test'];parts=test.split('.')
                if len(parts)!=4 or parts[0]!='tests' or not all(x.isidentifier() for x in parts):raise ValueError('invalid test identifier')
                import ast
                path=ROOT/'tests'/(parts[1]+'.py')
                if path.is_symlink() or path.resolve().parent!=(ROOT/'tests').resolve():raise ValueError('test evidence outside fixed scope')
                raw=read_bounded(path,remaining);remaining-=len(raw)
                tree=ast.parse(raw.decode());classes=[n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==parts[2]]
                functions=[n for cl in classes for n in cl.body if isinstance(n,ast.FunctionDef) and n.name==parts[3]]
                if len(functions)!=1:errors.append(dict(path=name,code='MISSING_EVIDENCE_TEST'));state='STALE_EVIDENCE'
                elif hashlib.sha256(ast.dump(functions[0],include_attributes=False).encode()).hexdigest()!=evidence['test_ast_sha256']:
                    errors.append(dict(path=name,code='CHANGED_EVIDENCE_TEST'));state='STALE_EVIDENCE'
            blocks.append(dict(path=name,**block,state=state,evidence=evidence))
    for key in indexed.keys()-used:errors.append(dict(path=key[0],ordinal=key[1],code='MISSING_REGISTERED_BLOCK'))
    result=dict(status='REVIEW_REQUIRED' if errors or unresolved else 'SUPPORTED_CHECKS_PASS',documents=len(documents),checked_local_links=checked,
        external_links_not_checked=external,error_count=len(errors),unresolved_count=len(unresolved),
        coverage='PARTIAL_SUPPORTED_MARKDOWN_SUBSET',errors=errors,unresolved=unresolved,blocks=blocks,
        block_counts=dict(Counter(row['state'] for row in blocks)),guide_execution_performed=False,boundary=BOUNDARY)
    encoded(result)
    return result


def encoded(value):
    raw=(json.dumps(value,ensure_ascii=True,sort_keys=True,indent=2)+'\n').encode('utf-8')
    if len(raw)>MAX_OUTPUT_BYTES:raise ValueError('documentation report exceeds 16 MiB')
    return raw


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.parse_args()
    try:result=audit();raw=encoded(result)
    except (ValueError,OSError,TypeError,KeyError,RecursionError):parser.exit(1,'Documentation audit failed.\n')
    sys.stdout.buffer.write(raw)
    return int(result['status']!='SUPPORTED_CHECKS_PASS')

if __name__=='__main__':raise SystemExit(main())
