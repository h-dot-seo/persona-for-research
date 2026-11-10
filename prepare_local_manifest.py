"""Prepare hashes and section inventory for explicitly selected local training files."""
from exclusive_output import add_output_argument, emit, preflight as preflight_output
import argparse
import copy
import hashlib
import json
import sys
import re
import unicodedata
from pathlib import Path

from corpus_files import source_paths, sections, read_source_bytes
from corpus_projection import runtime_papers
from research_workflow import build
from strict_json import load

PAPER_SELECTION_FIELDS = ('paper_id','author_id','split','runtime_knowledge_eligible','authorized','locator','kind','year','topic','source_file','observations')
REQUIRED = set(PAPER_SELECTION_FIELDS)


def preflight(selection, root):
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
    return source_paths(selection,root)


def prepare(selection, root):
    paths=preflight(selection,root)
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


MAX_REPORT_BYTES = 8 * 1024 * 1024
MAX_REPORT_ROWS = 1000


def scan_structure(text):
    """Describe lexical surprises; the unchanged parser alone decides success."""
    lines = text.splitlines()
    headings = []
    findings = []
    locators = []
    seen = set()
    preamble = []
    current = None
    body = []
    deeper = 0
    heading_count = 0
    finding_count = 0

    def finding(code, number):
        nonlocal finding_count
        finding_count += 1
        if len(findings) < MAX_REPORT_ROWS:
            findings.append(dict(code=code, line_number=number))

    def finish():
        if current is not None:
            current['characters'] = len('\n'.join(body))
            if not current['characters']:
                finding('EMPTY_SECTION', current['line_number'])

    for number, line in enumerate(lines, 1):
        if number == 1 and line.startswith('\ufeff## '):
            finding('FIRST_LINE_HEADING_HIDDEN_BY_BOM', number)
        if line.startswith('## '):
            finish()
            locator = line[3:].strip()
            flags = []
            if not locator: flags.append('EMPTY_HEADING')
            if locator in seen: flags.append('DUPLICATE_HEADING')
            if line[3:] != locator: finding('WHITESPACE_TRIMMED', number)
            if any(unicodedata.category(c) == 'Cf' for c in locator):
                finding('INVISIBLE_FORMAT_CHARACTER_IN_LOCATOR', number)
            seen.add(locator)
            locators.append(locator)
            heading_count += 1
            current = dict(locator=locator, line_number=number, characters=0, flags=flags)
            if len(headings) < MAX_REPORT_ROWS: headings.append(current)
            body = []
        else:
            if re.match(r'^(?: {1,3}##|##(?:$|[^ #])|##[\t\u00a0])', line):
                finding('NEAR_MISS_HEADING', number)
            if current is None:
                preamble.append(line)
            else:
                body.append(line)
                if line.startswith('###'): deeper += 1
    finish()
    try:
        parsed = sections(text)
    except ValueError as exc:
        outcome = 'WOULD_RAISE'
        error = str(exc)
    else:
        if list(parsed) != locators:
            raise ValueError('internal section scanner/parser disagreement')
        outcome = 'WOULD_SUCCEED'
        error = None
    breaks = re.findall(r'\r\n|[\n\r\v\f\x1c-\x1e\x85\u2028\u2029]', text)
    return dict(section_parse=outcome, section_error=error,
        line_breaks=dict(LF=breaks.count('\n'), CRLF=breaks.count('\r\n'),
            CR=breaks.count('\r'), other=sum(b not in ('\n','\r\n','\r') for b in breaks)),
        preamble_lines=len(preamble), preamble_characters=len('\n'.join(preamble)),
        headings=headings, headings_omitted=heading_count-len(headings),
        findings=findings, findings_omitted=finding_count-len(findings),
        deeper_heading_lines_in_body=deeper)


def report_defects(selection, root):
    paths = preflight(selection, root)
    papers = []
    for original, path in zip(selection['papers'], paths):
        raw = read_source_bytes(path)
        digest = hashlib.sha256(raw).hexdigest()
        if 'source_sha256' in original and original['source_sha256'] != digest:
            raise ValueError('selected file differs from supplied byte hash: '+original['paper_id'])
        row = dict(paper_id=original['paper_id'], source_file=original['source_file'],
            source_bytes=len(raw), source_sha256=digest)
        try:
            text = raw.decode('utf-8')
        except UnicodeDecodeError as exc:
            row.update(encoding='INVALID_UTF8', section_parse='INVALID_UTF8',
                invalid_utf8_byte_offset=exc.start)
        else:
            row.update(encoding='UTF8_BOM' if text.startswith('\ufeff') else 'UTF8')
            row.update(scan_structure(text))
        papers.append(row)
    result = dict(schema='persona.source-structure-report.v1', papers=papers,
        status='ALL_SELECTED_FILES_WOULD_PARSE' if all(p['section_parse']=='WOULD_SUCCEED' for p in papers)
            else 'SOME_SELECTED_FILES_WOULD_NOT_PARSE',
        llm_used=False, manifest_written=False, source_files_modified=False,
        conversion_fidelity='NOT_ASSESSED', scholarly_quality='NOT_ASSESSED',
        boundary='Structural and lexical checks only. No body text or quotations copied; headings and paths may be private. No scientific judgment, researcher authentication, rights clearance, model call or network access. NOT_VALIDATED.')
    if len((json.dumps(result, indent=2, ensure_ascii=True)+'\n').encode('utf-8')) > MAX_REPORT_BYTES:
        raise ValueError('source structure report exceeds 8 MiB output limit')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('selection',type=Path);parser.add_argument('--source-root',type=Path,required=True)
    parser.add_argument('--report-defects',action='store_true',help='report source structure without preparing a manifest')
    add_output_argument(parser); args=parser.parse_args()
    preflight_output(parser, getattr(args, 'output', None))
    try:result=(report_defects if args.report_defects else prepare)(load(args.selection),args.source_root)
    except (ValueError,OSError,KeyError,TypeError,AttributeError) as exc:parser.exit(1,str(exc)+'\n')
    emit(parser, (json.dumps(result,indent=2)+'\n').encode('utf-8'), getattr(args, 'output', None))


if __name__=='__main__':main()
