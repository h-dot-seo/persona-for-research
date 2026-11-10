"""Load explicitly authorized local UTF-8 Markdown evidence with byte hashes."""
from exclusive_output import add_output_argument, emit, preflight
import argparse
import hashlib
import json
import sys
import os
import stat
from pathlib import Path
from observation_input import verified_corpus
from research_workflow import build, apply
from corpus_projection import runtime_papers
from strict_json import load


def sections(text):
    result={}; current=None; lines=[]
    for line in text.splitlines():
        if line.startswith('## '):
            if current is not None:
                result[current]='\n'.join(lines)
            current=line[3:].strip(); lines=[]
            if not current or current in result:
                raise ValueError('section headings must be nonempty and unique')
        elif current is not None:
            lines.append(line)
    if current is not None:
        if current in result: raise ValueError('duplicate section heading')
        result[current]='\n'.join(lines)
    if not result: raise ValueError('source requires level-two Markdown headings')
    return result


def source_paths(manifest, root):
    """Preflight the entire authorized selection before any source-byte read."""
    runtime_papers(manifest)  # Reject selected shape errors and unauthorized input before filesystem access.
    root=Path(root).resolve(strict=True)
    # Check the entire corpus boundary before opening any supplied paper.
    seen=set(); paths=[]
    for paper in manifest['papers']:
        if (paper.get('authorized') is not True or paper.get('split')!='training'
                or paper.get('runtime_knowledge_eligible') is not True
                or paper.get('author_id')!=manifest.get('author_id')):
            raise ValueError('only author-matched authorized training files are allowed')
        pid=paper.get('paper_id')
        if not isinstance(pid,str) or not pid or pid in seen:
            raise ValueError('unique paper IDs required')
        seen.add(pid)
        name=paper.get('source_file')
        if not isinstance(name,str) or not name or '\\' in name or ':' in name:
            raise ValueError('source_file must be a portable relative path')
        relative=Path(name)
        if name.startswith('/') or relative.is_absolute() or '..' in relative.parts:
            raise ValueError('source_file must stay inside the selected source root')
        resolved=(root/relative).resolve(strict=True)
        if not resolved.is_relative_to(root) or not resolved.is_file():
            raise ValueError('source file escapes selected root or is not a file')
        if resolved.suffix.lower() not in ('.md','.txt'):
            raise ValueError('only UTF-8 Markdown/text sources are supported')
        paths.append(resolved)
    return paths


def read_source_bytes(path, *, max_bytes=None):
    """Pin a regular descriptor and reject detected replacements before reading."""
    if max_bytes is not None and (type(max_bytes) is not int or max_bytes < 0):
        raise ValueError('source byte limit must be a nonnegative integer')
    path=Path(path)
    if path.resolve(strict=True)!=path:
        raise ValueError('selected source path changed after preflight')
    flags=os.O_RDONLY | getattr(os,'O_BINARY',0) | getattr(os,'O_NOFOLLOW',0) | getattr(os,'O_NONBLOCK',0)
    descriptor=os.open(path,flags)
    try:
        opened=os.fstat(descriptor);current=path.stat(follow_symlinks=False)
        if (path.resolve(strict=True)!=path or not stat.S_ISREG(opened.st_mode)
                or not stat.S_ISREG(current.st_mode)
                or (opened.st_dev,opened.st_ino)!=(current.st_dev,current.st_ino)):
            raise ValueError('selected source identity changed after preflight')
        with os.fdopen(descriptor,'rb') as stream:
            descriptor=None
            raw=stream.read() if max_bytes is None else stream.read(max_bytes + 1)
            if max_bytes is not None and len(raw) > max_bytes:
                raise ValueError('selected source bytes exceed the configured input limit')
            after=os.fstat(stream.fileno())
            if (opened.st_size,opened.st_mtime_ns,opened.st_ctime_ns)!=(after.st_size,after.st_mtime_ns,after.st_ctime_ns):
                raise ValueError('selected source changed while reading')
            return raw
    finally:
        if descriptor is not None:os.close(descriptor)


def load_segment_corpus(manifest, root, *, max_total_bytes=None):
    """Read pinned local bytes into segments; no persisted verification receipt.

    Returned text is source data, not a publication-ready or anonymized artifact.
    Downstream intake must verify observations/quotes before building a package.
    """
    if max_total_bytes is not None and (type(max_total_bytes) is not int or max_total_bytes < 0):
        raise ValueError('total source byte limit must be a nonnegative integer')
    build(manifest)  # Full structural/authorization preflight before resolving files.
    paths=source_paths(manifest, root)
    corpus=json.loads(json.dumps(manifest,ensure_ascii=False,allow_nan=False))
    remaining=max_total_bytes
    for paper,path in zip(corpus['papers'],paths):
        raw=read_source_bytes(path) if remaining is None else read_source_bytes(path, max_bytes=remaining)
        if remaining is not None:remaining-=len(raw)
        if hashlib.sha256(raw).hexdigest()!=paper.get('source_sha256'):
            raise ValueError('source byte hash mismatch: '+paper['paper_id'])
        segment_map=sections(raw.decode('utf-8'))
        paper['segments']=segment_map
        paper['segments_sha256']=hashlib.sha256(json.dumps(segment_map,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
        paper['source_verification']='LOCAL_BYTES_SHA256_MATCH'
    return corpus


def load_sources(manifest, root):
    corpus=load_segment_corpus(manifest, root)
    return verified_corpus(corpus, _local_source_ids=[p['paper_id'] for p in corpus['papers']])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('manifest',type=Path); p.add_argument('--source-root',type=Path,required=True)
    p.add_argument('--question',required=True); p.add_argument('--topic',required=True)
    add_output_argument(p); a=p.parse_args()
    preflight(p, getattr(a, 'output', None))
    try:
        corpus=load_sources(load(a.manifest),a.source_root)
        package=build(corpus)
        result=dict(package=package,application=apply(package,a.question,a.topic),
                    boundary='Local bytes and quoted sections verified; publication authenticity and semantic support unverified')
    except (ValueError,OSError,KeyError,TypeError) as e: p.exit(1,str(e)+'\n')
    emit(p, (json.dumps(result,ensure_ascii=False,indent=2) + '\n').encode('utf-8'), getattr(a, 'output', None))


if __name__=='__main__': main()
