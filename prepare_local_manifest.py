"""Prepare hashes and section inventory for explicitly selected local training files."""
import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

from corpus_files import source_paths, sections, read_source_bytes
from corpus_projection import runtime_papers
from research_workflow import build
from strict_json import load

PAPER_SELECTION_FIELDS = ('paper_id','author_id','split','runtime_knowledge_eligible','authorized','locator','kind','year','topic','source_file','observations')
REQUIRED = set(PAPER_SELECTION_FIELDS)


def prepare(selection, root):
    # Existing full-corpus authorization checks precede filesystem resolution/read.
    runtime_papers(selection)
    if set(selection) != {'author_id','version','build_id','papers'}:
        raise ValueError('selection uses the existing corpus identity and papers fields only')
    provisional=copy.deepcopy(selection)
    for paper in provisional['papers']:
        if not REQUIRED <= set(paper) or set(paper)-REQUIRED-{'source_sha256','input_inventory'}:
            raise ValueError('paper selection has missing or unsupported fields')
        if paper['observations'] != []:
            raise ValueError('preparation requires empty observations; never rebaseline curated evidence')
        if type(paper['year']) is not int or not 1 <= paper['year'] <= 9999:
            raise ValueError('publication year must be an integer from 1 to 9999')
        if 'source_sha256' not in paper: paper['source_sha256']='0'*64
    build(provisional)  # Validate identity, duplicate IDs, kinds and supplied hashes without reading files.
    paths=source_paths(selection,root)
    result={key:copy.deepcopy(selection[key]) for key in ('author_id','version','build_id')}
    result['papers']=[]
    for original,path in zip(selection['papers'],paths):
        raw=read_source_bytes(path);digest=hashlib.sha256(raw).hexdigest()
        if 'source_sha256' in original and original['source_sha256']!=digest:
            raise ValueError('selected file differs from supplied byte hash: '+original['paper_id'])
        indexed=sections(raw.decode('utf-8'))
        paper={key:copy.deepcopy(original[key]) for key in PAPER_SELECTION_FIELDS}
        paper['source_sha256']=digest
        paper['input_inventory']=dict(source_bytes=len(raw),section_count=len(indexed),
            sections=[dict(locator=locator,normalized_characters=len(text),
                normalized_text_sha256=hashlib.sha256(text.encode('utf-8')).hexdigest()) for locator,text in indexed.items()],
            section_normalization='Existing section parser: splitlines then join with LF; raw byte hash remains separate.',
            status='LOCAL_INPUT_PREPARED_NO_OBSERVATIONS',llm_used=False,
            boundary='Section headings/counts only; no body text or quotations copied. Publication metadata and authorization are operator declarations. No researcher attribution, rights clearance or scientific validation.')
        result['papers'].append(paper)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('selection',type=Path);parser.add_argument('--source-root',type=Path,required=True)
    args=parser.parse_args()
    try:result=prepare(load(args.selection),args.source_root)
    except (ValueError,OSError,KeyError,TypeError,AttributeError) as exc:parser.exit(1,str(exc)+'\n')
    sys.stdout.buffer.write((json.dumps(result,indent=2)+'\n').encode('utf-8'))


if __name__=='__main__':main()
