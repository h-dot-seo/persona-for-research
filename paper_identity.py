"""Declare supplied CSL bibliography beside a package; never resolve publication identity."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
from census_import import optional_string, year
from compare_releases import checked_package
from research_workflow import validated_source_rules
from persona import payload_sha256
from human_validation import bindings, _identifier, _date, _hash
from strict_json import read_bounded, loads
from exclusive_output import add_output_argument, preflight, emit

SCHEMA='persona.paper-identity-declaration.v1'
MAP_SCHEMA='persona.paper-identity-mapping.v1'
CHECK_SCHEMA='persona.paper-identity-check.v1'
VERIFY_SCHEMA='persona.paper-identity-replay.v1'
MAX_INPUT_BYTES=8*1024*1024
MAX_OUTPUT_BYTES=16*1024*1024
MAX_ROWS=4096
IDENTIFIERS={'doi':'DOI','pmid':'PMID','pmcid':'PMCID','isbn':'ISBN','url':'URL'}
BOUNDARY=('Operator-declared bibliography, not resolved publication identity, source authenticity, rights '
    'clearance or authenticated review. Exact or ASCII-casefold DOI equality does not prove identical '
    'publications or independence. No lookup, network, source reread, knowledge ingestion, review decision '
    'or canonical update. Titles, identifiers and URLs may be private; URLs can contain account or session '
    'data. Keep local unless separately authorized to share. Hashes are consistency checks, not signatures.')
BINDING_KEYS={'author_id','version','build_id','persona_payload_sha256','knowledge_papers_sha256'}
ROW_KEYS={'paper_id','source_sha256','identifiers','declared_title','declared_year','source_export','status'}
TOP_KEYS=BINDING_KEYS|{'schema','operator_id','declared_at','export_sha256','mapping_sha256','papers','boundary','payload_sha256'}


def encode(value):
    raw=(json.dumps(value,ensure_ascii=True,allow_nan=False,indent=2)+'\n').encode('utf-8')
    if len(raw)>MAX_OUTPUT_BYTES:raise ValueError('paper identity output exceeds 16 MiB')
    return raw


def _keys(value,keys):
    if type(value) is not dict or set(value)!=set(keys):raise ValueError('paper identity fields do not match the closed format')


def _text(value,limit):
    if type(value) is not str or not value.strip() or len(value)>limit:raise ValueError('paper identity text is missing or too long')


def _package(value):
    package=checked_package(value);papers=list(validated_source_rules(package))
    if not 1<=len(papers)<=MAX_ROWS:raise ValueError('paper identity package requires 1 to 4096 papers')
    return package,papers


def _seal(record):
    record['payload_sha256']=payload_sha256(record)
    validate_record(record)
    return record


def _empty(paper):
    return dict(paper_id=paper['paper_id'],source_sha256=paper['source_sha256'],
        identifiers=dict.fromkeys(IDENTIFIERS),declared_title=None,declared_year=None,
        source_export=None,status='NOT_DECLARED')


def template(value,operator_id,declared_at):
    package,papers=_package(value);_identifier(operator_id,'operator_id');_date(declared_at)
    return _seal(dict(schema=SCHEMA,**bindings(package['persona'],package['knowledge']),operator_id=operator_id,
        declared_at=declared_at,export_sha256=None,mapping_sha256=None,papers=[_empty(p) for p in papers],boundary=BOUNDARY))


def _export(raw):
    if type(raw) is not bytes or len(raw)>MAX_INPUT_BYTES:raise ValueError('CSL export exceeds byte limit')
    text=raw.decode('utf-8')
    if '\x00' in text:raise ValueError('NUL is not accepted in CSL UTF-8 JSON')
    records=loads(text[1:] if text.startswith('\ufeff') else text)
    if type(records) is not list or not 1<=len(records)<=MAX_ROWS or any(type(r) is not dict for r in records):
        raise ValueError('CSL export requires 1 to 4096 object occurrences')
    return records,hashlib.sha256(raw).hexdigest()


def _mapping(mapping,records,digest):
    _keys(mapping,{'schema','export_sha256','papers'})
    if mapping['schema']!=MAP_SCHEMA or mapping['export_sha256']!=digest:raise ValueError('mapping is stale for these exact export bytes')
    rows=mapping['papers']
    if type(rows) is not list or not 1<=len(rows)<=MAX_ROWS:raise ValueError('mapping requires 1 to 4096 explicit rows')
    seen=set();result={}
    for row in rows:
        _keys(row,{'paper_id','census_id','entry_sha256'});_text(row['paper_id'],2000)
        occurrence=row['census_id']
        if type(occurrence) is not str or not re.fullmatch(r'census-[0-9]{6}',occurrence):raise ValueError('invalid census occurrence')
        index=int(occurrence[7:])-1
        if not 0<=index<len(records):raise ValueError('census occurrence is not in export')
        if row['paper_id'] in seen:raise ValueError('duplicate package paper mapping')
        seen.add(row['paper_id']);_hash(row['entry_sha256'],'entry_sha256')
        if row['entry_sha256']!=payload_sha256(records[index]):raise ValueError('mapping entry hash differs')
        result[row['paper_id']]=(row,records[index])
    return result


def _copy(entry,mapping_row):
    identifiers={}
    for key,field in IDENTIFIERS.items():
        value=optional_string(entry,field)
        if value is not None:_text(value,2048 if key=='url' else 128)
        identifiers[key]=value
    title=optional_string(entry,'title')
    if title is not None:_text(title,2000)
    supplied_year=year(entry)
    if supplied_year is not None and not 1<=supplied_year<=9999:raise ValueError('declared year outside 1 to 9999')
    return dict(identifiers=identifiers,declared_title=title,declared_year=supplied_year,
        source_export=dict(format='csl-json',census_id=mapping_row['census_id'],entry_sha256=mapping_row['entry_sha256']),
        status='DECLARED_CSL_NOT_RESOLVED')


def from_csl(value,raw,mapping,operator_id,declared_at):
    record=template(value,operator_id,declared_at);records,digest=_export(raw);selected=_mapping(mapping,records,digest)
    known={p['paper_id'] for p in record['papers']}
    if not set(selected)<=known:raise ValueError('mapping contains paper outside supplied runtime package')
    record.pop('payload_sha256');record.update(export_sha256=digest,mapping_sha256=payload_sha256(mapping))
    for paper in record['papers']:
        if paper['paper_id'] in selected:
            row,entry=selected[paper['paper_id']];paper.update(_copy(entry,row))
    return _seal(record)


def validate_record(record):
    _keys(record,TOP_KEYS)
    if record['schema']!=SCHEMA or record['boundary']!=BOUNDARY:raise ValueError('unsupported paper identity declaration')
    for key in ('author_id','version','build_id'):_text(record[key],2000)
    _identifier(record['operator_id'],'operator_id');_date(record['declared_at'])
    for key in ('persona_payload_sha256','knowledge_papers_sha256','payload_sha256'):_hash(record[key],key)
    if record['payload_sha256']!=payload_sha256({k:v for k,v in record.items() if k!='payload_sha256'}):raise ValueError('declaration digest mismatch; manual identity editing is unsupported')
    for key in ('export_sha256','mapping_sha256'):
        if record[key] is not None:_hash(record[key],key)
    if (record['export_sha256'] is None)!=(record['mapping_sha256'] is None):raise ValueError('incomplete export binding')
    rows=record['papers']
    if type(rows) is not list or not 1<=len(rows)<=MAX_ROWS:raise ValueError('declaration requires 1 to 4096 rows')
    seen=set();declared=0
    for row in rows:
        _keys(row,ROW_KEYS);_text(row['paper_id'],2000);_hash(row['source_sha256'],'source_sha256')
        if row['paper_id'] in seen:raise ValueError('duplicate declared paper ID')
        seen.add(row['paper_id']);_keys(row['identifiers'],IDENTIFIERS)
        for key,value in row['identifiers'].items():
            if value is not None:_text(value,2048 if key=='url' else 128)
        if row['declared_title'] is not None:_text(row['declared_title'],2000)
        y=row['declared_year']
        if y is not None and (type(y) is not int or not 1<=y<=9999):raise ValueError('declared year must be integer or null')
        if row['status']=='NOT_DECLARED':
            if any(row['identifiers'].values()) or row['declared_title'] is not None or y is not None or row['source_export'] is not None:
                raise ValueError('undeclared row cannot contain identity values')
        elif row['status']=='DECLARED_CSL_NOT_RESOLVED':
            _keys(row['source_export'],{'format','census_id','entry_sha256'})
            source=row['source_export']
            if source['format']!='csl-json' or type(source['census_id']) is not str or not re.fullmatch(r'census-[0-9]{6}',source['census_id']) or not 1<=int(source['census_id'][7:])<=MAX_ROWS:
                raise ValueError('invalid declared export occurrence')
            _hash(source['entry_sha256'],'entry_sha256');declared+=1
        else:raise ValueError('unsupported declaration status')
    if bool(declared)!=(record['export_sha256'] is not None):raise ValueError('declared rows require export bindings')
    encode(record)
    return record


def verify(record,raw,mapping):
    validate_record(record)
    if record['export_sha256'] is None:raise ValueError('empty template has no CSL copy to replay')
    records,digest=_export(raw);selected=_mapping(mapping,records,digest)
    if digest!=record['export_sha256'] or payload_sha256(mapping)!=record['mapping_sha256']:raise ValueError('declaration export/mapping binding mismatch')
    declared={row['paper_id']:row for row in record['papers'] if row['status']!='NOT_DECLARED'}
    if set(declared)!=set(selected):raise ValueError('declared and mapped paper sets differ')
    for pid,(mapping_row,entry) in selected.items():
        expected=_copy(entry,mapping_row)
        if any(declared[pid][key]!=val for key,val in expected.items()):raise ValueError('declared CSL copy differs from supplied export')
    return dict(schema=VERIFY_SCHEMA,status='CSL_COPY_REPLAY_MATCH_NOT_AUTHENTICATED',declaration_sha256=record['payload_sha256'],
        export_sha256=digest,mapping_sha256=record['mapping_sha256'],replayed_rows=len(selected),
        unmapped_export_occurrences=len(records)-len({row['census_id'] for row,_ in selected.values()}),
        package_binding_verification='NOT_PERFORMED',operator_identity_verification='NOT_PERFORMED',boundary=BOUNDARY)


def _doi_groups(rows,fold):
    groups={}
    for row in rows:
        doi=row.get('identifiers',{}).get('doi')
        if doi:
            key=doi.translate(str.maketrans('ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz')) if fold else doi
            groups.setdefault(key,[]).append(row['paper_id'])
    return [dict(declared_doi=key,paper_ids=pids) for key,pids in sorted(groups.items()) if len(pids)>1]


def check(record,value):
    validate_record(record);package,papers=_package(value);current=bindings(package['persona'],package['knowledge'])
    if record['author_id']!=current['author_id']:raise ValueError('declaration belongs to another declared author')
    by_id={p['paper_id']:p for p in papers};rows=[]
    for row in record['papers']:
        pid=row['paper_id'];paper=by_id.get(pid)
        state='PAPER_ID_ABSENT' if paper is None else 'SOURCE_HASH_MATCH' if row['source_sha256']==paper['source_sha256'] else 'SOURCE_HASH_DIFFERS'
        visible=state=='SOURCE_HASH_MATCH' and row['status']=='DECLARED_CSL_NOT_RESOLVED'
        item=dict(paper_id=pid,source_binding_status=state,declaration_status=row['status'],values_displayed=visible)
        if visible:
            item.update(identifiers=copy.deepcopy(row['identifiers']),declared_title=row['declared_title'],declared_year=row['declared_year'])
            item['prompts']=(['ISSUED_YEAR_NOT_SUPPLIED'] if row['declared_year'] is None else ['DECLARED_YEAR_DIFFERS_FROM_PACKAGE_YEAR'] if row['declared_year']!=paper['year'] else [])
        rows.append(item)
    result=dict(schema=CHECK_SCHEMA,package_binding_status='CURRENT_PACKAGE' if all(record[k]==v for k,v in current.items()) else 'STALE_PACKAGE',
        declaration_sha256=record['payload_sha256'],rows=rows,new_package_papers_not_declared=[p['paper_id'] for p in papers if p['paper_id'] not in {r['paper_id'] for r in record['papers']}],
        exact_declared_doi_groups=_doi_groups(rows,False),ascii_casefold_declared_doi_groups=_doi_groups(rows,True),
        export_copy_replayed='NOT_PERFORMED',source_bytes_reread=False,identity_verified=False,automatic_approval=False,boundary=BOUNDARY)
    encode(result);return result


def render(result):
    from review_package import display
    lines=['Detached bibliography | DECLARED_NOT_RESOLVED',BOUNDARY]
    # JSON ensures absent hidden fields cannot accidentally be formatted from the original record.
    lines.extend(display(line) for line in json.dumps(result,ensure_ascii=True,indent=2).splitlines())
    text='\n'.join(lines)+'\n'
    if len(text.encode('utf-8'))>MAX_OUTPUT_BYTES:raise ValueError('paper identity text exceeds 16 MiB')
    return text


def reader():
    remaining=[MAX_INPUT_BYTES]
    def read(path,raw=False):
        value=read_bounded(path,remaining[0]);remaining[0]-=len(value)
        return value if raw else loads(value)
    return read


def review_package_output(args):
    """Opt-in CLI only: read every declared artifact once under one combined budget."""
    from review_package import render as review_render
    read=reader();package=read(args.package);record=read(args.paper_identities)
    records=[read(path) for path in args.human_validation] if args.human_validation else None
    split=read(args.split) if args.split else None
    if args.split is not None:
        from split_declaration import validate_declaration
        validate_declaration(split,frozen=True)
    challenges=[read(path) for path in args.challenge_record] if args.challenge_record else None
    decision=read(args.release_decision) if args.release_decision else None
    base=review_render(package,args.question,args.topic,evidence_details=args.evidence_details,
        human_validation=records,split_declaration=split,challenge_records=challenges,release_decision=decision)
    output=base+render(check(record,package))
    if len(output.encode('utf-8'))>MAX_OUTPUT_BYTES:raise ValueError('combined bibliography review exceeds 16 MiB')
    return output


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    for name in ('template','from-csl','check','verify'):
        cmd=sub.add_parser(name)
        if name in ('template','from-csl'):cmd.add_argument('package',type=Path)
        else:cmd.add_argument('record',type=Path)
        if name=='check':cmd.add_argument('package',type=Path)
        if name in ('from-csl','verify'):cmd.add_argument('export',type=Path);cmd.add_argument('mapping',type=Path)
        if name in ('template','from-csl'):cmd.add_argument('--operator-id',required=True);cmd.add_argument('--declared-at',required=True)
        else:cmd.add_argument('--format',choices=('json','text'),default='json')
        add_output_argument(cmd)
    args=parser.parse_args()
    if args.command in ('template','from-csl') and args.output is None:parser.error('template/from-csl require --output')
    preflight(parser,args.output)
    try:
        read=reader()
        if args.command=='template':result=template(read(args.package),args.operator_id,args.declared_at)
        elif args.command=='from-csl':result=from_csl(read(args.package),read(args.export,True),read(args.mapping),args.operator_id,args.declared_at)
        elif args.command=='check':result=check(read(args.record),read(args.package))
        else:result=verify(read(args.record),read(args.export,True),read(args.mapping))
        raw=render(result).encode('utf-8') if getattr(args,'format','json')=='text' else encode(result)
    except (ValueError,OSError,KeyError,TypeError,AttributeError,RecursionError,RuntimeError):parser.exit(1,'Invalid paper identity input.\n')
    emit(parser,raw,args.output)

if __name__=='__main__':main()
