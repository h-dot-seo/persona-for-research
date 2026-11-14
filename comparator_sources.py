"""Optional comparator-only local byte and stored-quote recheck; never target source retrieval."""
import hashlib
import json
import stat
from pathlib import PurePosixPath
from comparator_overlap import inspect, validate_corpus, encode, MAX_INPUT_BYTES, BOUNDARY as INVENTORY_BOUNDARY
from corpus_files import read_source_bytes, sections
from journey_inputs import _checked_path
from source_recheck import _relative, MATCH
from persona import payload_sha256
from strict_json import loads

SELECTION_SCHEMA='persona.comparator-source-selection.v1'
SCHEMA='persona.comparator-source-recheck.v1'
MAX_SOURCE_BYTES=8*1024*1024
BOUNDARY=('Only explicitly mapped comparator sources are reread, including unused papers and observations. '
 'Target package source bytes are NOT_PERFORMED. Raw SHA256 equality and exact section substrings '
 'do not establish authenticity, access rights, consent, independence, semantic support or human approval. '
 'No holdout membership check or knowledge inclusion occurs. Supplied labels remain declarations. '
 'Section parsing normalizes line endings. Files may change after this read; descriptor/identity checks '
 'detect some races, not all hostile concurrent changes. This is not an authenticated receipt. '
 'Source bodies are not emitted; filenames, locators and operator labels may be private. '
 'No network, model invocation or external transmission is performed.')


def inspect_sources(package, comparator, topic, selection, root):
    # Detach finite JSON before reading: direct callers also get a combined bound.
    raw=json.dumps(dict(package=package,comparator=comparator,selection=selection),ensure_ascii=True,allow_nan=False).encode()
    if len(raw)>MAX_INPUT_BYTES:raise ValueError('combined comparator inputs exceed budget')
    inputs=loads(raw);package=inputs['package'];comparator=inputs['comparator'];selection=inputs['selection']
    result=inspect(package,comparator,topic)
    papers=validate_corpus(comparator)
    if not isinstance(selection,dict) or set(selection)!={'schema','comparator_corpus_sha256','operator_id','sources'} or selection['schema']!=SELECTION_SCHEMA:
        raise ValueError('invalid comparator source selection')
    if selection['comparator_corpus_sha256']!=payload_sha256(comparator):raise ValueError('stale comparator source selection')
    operator=selection['operator_id']
    if not isinstance(operator,str) or not operator.strip() or len(operator)>128:raise ValueError('invalid declared operator label')
    if not isinstance(selection['sources'],list):raise ValueError('sources must be array')
    ids={p['paper_id'] for p in papers};names={}
    for row in selection['sources']:
        if not isinstance(row,dict) or set(row)!={'paper_id','source_file'}:raise ValueError('invalid source row')
        pid=row['paper_id']
        if not isinstance(pid,str) or pid not in ids or pid in names:raise ValueError('select every comparator paper exactly once')
        names[pid]=_relative(row['source_file'])
    if set(names)!=ids:raise ValueError('select every comparator paper exactly once')
    root,info=_checked_path(root)
    if not stat.S_ISDIR(info.st_mode):raise ValueError('source root must be a plain directory')
    paths=[]
    for paper in papers:
        path,info=_checked_path(root.joinpath(*PurePosixPath(names[paper['paper_id']]).parts))
        if not path.is_relative_to(root) or not stat.S_ISREG(info.st_mode):raise ValueError('source must be a regular file inside root')
        paths.append(path)
    remaining=MAX_SOURCE_BYTES;rows=[];matched=0;count=0;row_bytes=0
    for paper,path in zip(papers,paths):
        raw=read_source_bytes(path,max_bytes=remaining);remaining-=len(raw)
        digest=hashlib.sha256(raw).hexdigest()
        if digest!=paper['source_sha256']:raise ValueError('comparator source byte hash mismatch')
        segments=sections(raw.decode('utf-8'));records=[]
        for index,obs in enumerate(paper['observations']):
            quote=obs['evidence_quote'];locator=obs['locator']
            present=locator in segments
            status=('STORED_QUOTE_MISSING' if not isinstance(quote,str) or not quote.strip() else
                    'LOCATOR_NOT_FOUND' if not present else
                    'STORED_QUOTE_NOT_FOUND_AT_LOCATOR' if quote not in segments[locator] else MATCH)
            record=dict(reference=dict(paper_id=paper['paper_id'],observation_index=index),locator=locator,
                quote_status=status,locator_status='PRESENT' if present else 'NOT_FOUND',
                stored_quote_sha256=hashlib.sha256(quote.encode()).hexdigest() if isinstance(quote,str) else None)
            row_bytes+=len(encode(record))
            if row_bytes>16*1024*1024:raise ValueError('source records exceed output budget')
            records.append(record);count+=1;matched+=status==MATCH
        rows.append(dict(paper_id=paper['paper_id'],source_file=names[paper['paper_id']],source_sha256=digest,
            bytes_read=len(raw),source_check='LOCAL_BYTES_SHA256_MATCH',records=records,
            status='NO_STORED_QUOTES_TO_CHECK' if not records else 'STORED_QUOTE_GAPS_REQUIRE_REVIEW' if any(x['quote_status']!=MATCH for x in records) else 'ALL_STORED_QUOTES_MATCH_SECTION_TEXT'))
    result['source_check']='COMPARATOR_ONLY_RECHECK_PERFORMED'
    result['boundary']=INVENTORY_BOUNDARY.replace(
        'No source bytes are read, quotes or hashes authenticated, network/provider/other-agent calls made, ',
        'Comparator-only byte/quote checks are reported separately; target sources are not read and no authenticity is established. No network/provider/other-agent calls are made, ')
    result['comparator_source_recheck']=dict(schema=SCHEMA,comparator_corpus_sha256=payload_sha256(comparator),
        selection_sha256=payload_sha256(selection),operator_id=operator,operator_identity='DECLARED_NOT_VERIFIED',
        target_source_check='NOT_PERFORMED',source_scope='ALL_MAPPED_COMPARATOR_PAPERS',papers=rows,
        source_bytes_read=MAX_SOURCE_BYTES-remaining,checked_paper_count=len(rows),checked_record_count=count,matched_quote_count=matched,
        boundary=BOUNDARY)
    encode(result)
    return result
