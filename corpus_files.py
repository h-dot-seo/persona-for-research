"""Load explicitly authorized local UTF-8 Markdown evidence with byte hashes."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
from observation_input import verified_corpus
from research_workflow import build, apply
from corpus_projection import runtime_papers


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


def load_sources(manifest, root):
    runtime_papers(manifest)  # Reject selected shape errors and unauthorized input before filesystem access.
    corpus=copy.deepcopy(manifest)
    root=Path(root).resolve(strict=True)
    # Check the entire corpus boundary before opening any supplied paper.
    seen=set(); paths=[]
    for paper in corpus['papers']:
        if (paper.get('authorized') is not True or paper.get('split')!='training'
                or paper.get('runtime_knowledge_eligible') is not True
                or paper.get('author_id')!=corpus.get('author_id')):
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
    for paper,path in zip(corpus['papers'],paths):
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=paper.get('source_sha256'):
            raise ValueError('source byte hash mismatch: '+paper['paper_id'])
        segment_map=sections(raw.decode('utf-8'))
        paper['segments']=segment_map
        paper['segments_sha256']=hashlib.sha256(json.dumps(segment_map,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
        paper['source_verification']='LOCAL_BYTES_SHA256_MATCH'
    return verified_corpus(corpus, _local_source_ids=[p['paper_id'] for p in corpus['papers']])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('manifest',type=Path); p.add_argument('--source-root',type=Path,required=True)
    p.add_argument('--question',required=True); p.add_argument('--topic',required=True)
    a=p.parse_args()
    try:
        corpus=load_sources(json.loads(a.manifest.read_text(encoding='utf-8')),a.source_root)
        package=build(corpus)
        result=dict(package=package,application=apply(package,a.question,a.topic),
                    boundary='Local bytes and quoted sections verified; publication authenticity and semantic support unverified')
    except (ValueError,OSError,KeyError,TypeError) as e: p.exit(1,str(e)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__': main()
