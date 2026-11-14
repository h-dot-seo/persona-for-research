"""Recheck every supplied source file and stored quote without changing a package."""
from exclusive_output import add_output_argument, emit, preflight
import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path, PurePosixPath

from corpus_files import source_paths, read_source_bytes, sections
from reasoning_links import _sources
from reasoning_cards import DIMENSIONS
from design_scenario import _text
from persona import payload_sha256
from review_package import display
from strict_json import read_bounded, InputLimitError, loads

SCHEMA = 'persona.source-recheck-selection.v1'
MAX_JSON_BYTES = 8 * 1024 * 1024
MAX_SOURCE_BYTES = 8 * 1024 * 1024
MATCH = 'EXACT_SECTION_SUBSTRING_MATCH'
BOUNDARY = ('This invocation rereads explicitly selected local files, checks their bytes against the '
    'current package hashes and compares every stored observation/component quote with its declared '
    'Markdown section. Section parsing normalizes line endings; matching is an exact case-sensitive '
    'substring test, not semantic support, source authenticity, authorship, rights clearance or review '
    'quality. All supplied papers and records are checked, including unused evidence. Missing quotes '
    'or locators remain gaps. Different files or hashes do not establish independent studies. No '
    'package field, source hash, stored verification label, review decision or canonical file is '
    'changed. Earlier model/extraction histories are not replayed. No provider call, external '
    'transmission, research execution or automatic approval occurs. Checks describe this read only; '
    'files may change later. A saved JSON report is not an authenticated verification receipt.')


def _detach(value):
    try: raw = json.dumps(value, ensure_ascii=True, allow_nan=False).encode('utf-8')
    except (ValueError, TypeError, RecursionError) as exc: raise ValueError('source recheck input must be finite JSON data') from exc
    if len(raw) > MAX_JSON_BYTES: raise ValueError('combined source recheck JSON exceeds 8 MiB')
    return loads(raw)


def template(value, operator_id):
    package, papers = _sources(value); _text(operator_id, 'operator_id', 128)
    return dict(schema=SCHEMA, package_sha256=payload_sha256(package), operator_id=operator_id,
        sources=[dict(paper_id=paper_id, source_file=None) for paper_id in papers])


def _relative(name):
    if not isinstance(name, str) or not name.strip() or len(name) > 1024 or '\\' in name or ':' in name or any(ord(c)<32 or ord(c)==127 for c in name):
        raise ValueError('source_file must be a bounded portable relative path')
    path=PurePosixPath(name)
    if path.is_absolute() or path.as_posix()!=name or name=='.' or '..' in path.parts:
        raise ValueError('source_file must be a canonical relative path inside the selected root')
    if path.suffix.lower() not in ('.md', '.txt'): raise ValueError('only UTF-8 Markdown/text sources are supported')
    return name


def audit(value, selection, source_root):
    inputs=_detach(dict(package=value, selection=selection))
    package, papers=_sources(inputs['package']);selection=inputs['selection']
    if not isinstance(selection, dict) or set(selection)!={'schema','package_sha256','operator_id','sources'} or selection['schema']!=SCHEMA:
        raise ValueError('source selection has missing or unsupported fields; cached reports are not source selections')
    _text(selection['operator_id'], 'operator_id', 128)
    if selection['package_sha256']!=payload_sha256(package): raise ValueError('source selection is stale for this package')
    if not isinstance(selection['sources'], list): raise ValueError('sources must be an array')
    selected={}
    for row in selection['sources']:
        if not isinstance(row, dict) or set(row)!={'paper_id','source_file'}: raise ValueError('source selection row requires paper_id and source_file only')
        pid=row['paper_id']
        if not isinstance(pid, str) or pid not in papers or pid in selected: raise ValueError('source selection needs every known paper exactly once')
        selected[pid]=_relative(row['source_file'])
    if set(selected)!=set(papers): raise ValueError('source selection needs every supplied paper, including unused papers')
    # Full package/form authorization and path validation precede every file read.
    manifest={key:package['persona'][key] for key in ('author_id','version','build_id')}
    manifest['papers']=copy.deepcopy(list(papers.values()))
    for paper in manifest['papers']: paper['source_file']=selected[paper['paper_id']]
    paths=source_paths(manifest, source_root)
    remaining=MAX_SOURCE_BYTES; rows=[]; gaps=[]; total_records=0; matched=0
    for paper, path in zip(manifest['papers'], paths):
        raw=read_source_bytes(path, max_bytes=remaining);remaining-=len(raw)
        digest=hashlib.sha256(raw).hexdigest()
        if digest!=paper['source_sha256']: raise ValueError('source bytes differ from bound package hash: '+display(paper['paper_id']))
        segments=sections(raw.decode('utf-8'))
        records=[]
        for index, observation in enumerate(paper['observations']):
            components=observation.get('reasoning', {})
            for dimension, record in [(None, observation), *[(d,components[d]) for d in DIMENSIONS if d in components]]:
                quote=record.get('evidence_quote');locator=record['locator']
                locator_present=locator in segments
                if not isinstance(quote,str) or not quote.strip(): status='STORED_QUOTE_MISSING'
                elif not locator_present: status='LOCATOR_NOT_FOUND'
                elif quote not in segments[locator]: status='STORED_QUOTE_NOT_FOUND_AT_LOCATOR'
                else: status=MATCH
                ref=dict(paper_id=paper['paper_id'], observation_index=index, dimension=dimension)
                row=dict(reference=ref, locator=locator, locator_status='PRESENT' if locator_present else 'NOT_FOUND',
                    quote_status=status, stored_quote_sha256=hashlib.sha256(quote.encode('utf-8')).hexdigest() if isinstance(quote,str) else None,
                    recorded_quote_check_before=record.get('evidence_verification','NOT_PERFORMED'))
                records.append(row);total_records+=1
                if status==MATCH: matched+=1
                else: gaps.append(dict(reference=copy.deepcopy(ref),code=status))
        rows.append(dict(paper_id=paper['paper_id'], source_file=selected[paper['paper_id']], source_sha256=digest,
            bytes_read=len(raw), source_check='LOCAL_BYTES_SHA256_MATCH',
            recorded_source_check_before=paper.get('source_verification','NOT_PERFORMED'), records=records,
            quote_scope='ALL_STORED_OBSERVATIONS_AND_COMPONENTS',
            status='NO_STORED_QUOTES_TO_CHECK' if not records else 'STORED_QUOTE_GAPS_REQUIRE_REVIEW' if any(r['quote_status']!=MATCH for r in records) else 'ALL_STORED_QUOTES_MATCH_SECTION_TEXT'))
    empty_papers=[row['paper_id'] for row in rows if not row['records']]
    bindings=dict(package_sha256=payload_sha256(package),selection_sha256=payload_sha256(selection))
    result=dict(schema='persona.source-recheck.v1',
        status='LOCAL_BYTES_MATCH_QUOTE_GAPS_REQUIRE_REVIEW' if gaps else 'LOCAL_BYTES_MATCH_NO_STORED_QUOTES' if not total_records else 'LOCAL_BYTES_MATCH_PARTIAL_QUOTE_COVERAGE_REQUIRES_REVIEW' if empty_papers else 'LOCAL_BYTES_AND_STORED_QUOTES_MATCH_NOT_VALIDATION',
        **bindings,report_input_sha256=payload_sha256(bindings),operator_id=selection['operator_id'],
        declared_operator_identity='RECORDED_NOT_AUTHENTICATED',papers=rows,quote_gaps=gaps,
        checked_paper_count=len(rows),checked_record_count=total_records,matched_quote_count=matched,
        papers_without_stored_quotes=empty_papers,
        source_review_prompts=[dict(paper_id=pid,code='NO_STORED_QUOTE_RECORDS_FOR_PAPER') for pid in empty_papers],
        all_stored_quotes_match=bool(total_records) and matched==total_records,
        source_bytes_rechecked=True,source_quotes_rechecked=bool(total_records),source_bytes_read=MAX_SOURCE_BYTES-remaining,
        semantic_validation='NOT_PERFORMED',source_authenticity='NOT_ESTABLISHED',
        provenance_history_replay='NOT_PERFORMED',llm_used=False,provider_invoked=False,external_transmission=False,
        automatic_approval=False,canonical_update_performed=False,package_modified=False,boundary=BOUNDARY)
    if len(json.dumps(result,ensure_ascii=True).encode('utf-8'))>MAX_JSON_BYTES: raise ValueError('source recheck report exceeds 8 MiB')
    return result


def render(result):
    """Format a supplied report only; this function never reads or verifies sources."""
    lines=['Current local source and stored-quote recheck', 'Status: '+result['status'],
        'Package sha256: '+result['package_sha256'], 'Selection sha256: '+result['selection_sha256'],
        'Declared operator (not authenticated): '+display(result['operator_id']),
        'Checked '+str(result['checked_paper_count'])+' supplied paper IDs; matched '+str(result['matched_quote_count'])+
        ' / '+str(result['checked_record_count'])+' stored records (not independent studies or validity).']
    for paper in result['papers']:
        lines.append('Paper '+display(paper['paper_id'])+' | '+display(paper['source_file'])+' | '+paper['status'])
        lines.append('  Current bytes: '+paper['source_check']+'; sha256='+paper['source_sha256']+
            '; prior recorded source check='+paper['recorded_source_check_before'])
        for row in paper['records']:
            ref=row['reference']
            lines.append('  Observation '+str(ref['observation_index'])+' / '+display(ref['dimension'])+' | '+row['quote_status']+
                ' | locator='+display(row['locator'])+' ('+row['locator_status']+'); prior recorded quote check='+row['recorded_quote_check_before'])
    lines.append(BOUNDARY)
    return '\n'.join(lines)+'\n'


def _load(path):
    try:
        raw = read_bounded(path, MAX_JSON_BYTES)
    except InputLimitError as exc:
        raise ValueError('source recheck JSON file exceeds 8 MiB') from exc
    return loads(raw)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('package',type=Path);parser.add_argument('selection',type=Path,nargs='?')
    parser.add_argument('--template',action='store_true');parser.add_argument('--operator-id');parser.add_argument('--source-root',type=Path)
    parser.add_argument('--format',choices=('json','text'),default='json');add_output_argument(parser); args=parser.parse_args()
    preflight(parser, getattr(args, 'output', None))
    try:
        package=_load(args.package)
        if args.template:
            if args.selection or args.source_root or args.format!='json': raise ValueError('template needs JSON output and no source selection/root')
            result=template(package,args.operator_id)
        else:
            if args.selection is None or args.source_root is None or args.operator_id is not None: raise ValueError('recheck needs explicit source selection and source root, without operator override')
            result=audit(package,_load(args.selection),args.source_root)
        output=render(result) if args.format=='text' else json.dumps(result,ensure_ascii=True,indent=2)+'\n'
        if len(output.encode('utf-8'))>MAX_JSON_BYTES: raise ValueError('source recheck output exceeds 8 MiB')
    except (ValueError,OSError,KeyError,TypeError,AttributeError,RecursionError) as exc: parser.exit(1,str(exc)+'\n')
    emit(parser, output.encode('utf-8'), getattr(args, 'output', None))


if __name__=='__main__':main()
