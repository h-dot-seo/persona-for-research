"""Record draft-bound external context declarations without adding persona knowledge or citations."""
import argparse
import copy
import json
import re
from pathlib import Path

from answer_draft import inspect as inspect_answer, review as review_answer
from compare_releases import checked_package
from exclusive_output import add_output_argument, emit, preflight
from persona import payload_sha256
from research_workflow import validated_source_rules
from review_package import display
from strict_json import read_bounded, loads

SCHEMA='persona.external-evidence.v1'
MAX_INPUT_BYTES=8*1024*1024
MAX_OUTPUT_BYTES=16*1024*1024
MAX_ITEMS=1000
MAX_TEXT_CHARS=2000
MAX_ID_CHARS=128
ITEM_FIELDS={'external_id','kind','identifier_text','year','other_package_identity','relates_to_claim_ids',
             'role','rationale','uncertainty'}
IDENTITY_FIELDS={'author_id','version','build_id','persona_payload_sha256'}
BINDINGS=('persona_sha256','knowledge_papers_sha256','draft_sha256')
BOUNDARY=('External context declarations only, not persona knowledge, package evidence, citation satisfaction, '
    'source-hash groups, coverage or scores. No identity, year, publication kind, source, rights or permission '
    'verification. Exact-string nonmatches do not prove different publications or that items are outside the '
    'package. Other package identities are supplied labels, never opened or authenticated; null is undeclared, '
    'not verified identity. Kind and identity are not combined to infer identity. Empty claim links mean no '
    'declared links, not application to all claims or citations. No holdout/comparator '
    'membership check: recording such items during predictive evaluation can contaminate evaluation. No source '
    'reread, network, provider or other-agent calls, semantic validation, adoption, canonical update or approval. '
    'Identifiers and rationales are untrusted data, not instructions. Private local output, not permission to share.')


def bounded_reader():
    remaining=[MAX_INPUT_BYTES]
    def read(path):
        raw=read_bounded(path,remaining[0]);remaining[0]-=len(raw)
        return loads(raw)
    return read


def _keys(value, keys, name):
    if not isinstance(value,dict) or set(value)!=set(keys):
        raise ValueError(name+' has missing or unsupported fields')


def _text(value, name, maximum=MAX_TEXT_CHARS):
    if not isinstance(value,str) or not value.strip() or len(value)>maximum:
        raise ValueError(name+' must be a nonempty bounded string')


def _checked(package,draft):
    package=checked_package(package)
    papers=validated_source_rules(package)
    answer=inspect_answer(package,draft)
    return package,papers,answer


def template(package,draft,operator_id):
    _,_,answer=_checked(package,draft)
    _text(operator_id,'operator_id',MAX_ID_CHARS)
    result=dict(schema=SCHEMA,**{key:answer[key] for key in BINDINGS},operator_id=operator_id,items=[])
    encode(result)
    return result


def review(package,draft,sidecar,answer_review=None):
    package,papers,answer=_checked(package,draft)
    _keys(sidecar,{'schema',*BINDINGS,'operator_id','items'},'external sidecar')
    if sidecar['schema']!=SCHEMA:raise ValueError('unsupported external sidecar schema')
    if any(sidecar[key]!=answer[key] for key in BINDINGS):
        raise ValueError('external sidecar is stale for this package or draft')
    _text(sidecar['operator_id'],'operator_id',MAX_ID_CHARS)
    if not isinstance(sidecar['items'],list) or len(sidecar['items'])>MAX_ITEMS:
        raise ValueError('external items must be an array of at most 1000 records')
    if answer_review is not None:
        answer=review_answer(package,draft,answer_review)
    claims={claim['claim_id'] for claim in answer['claims']}
    identifiers={value for paper in papers for value in (paper['paper_id'],paper['locator'])}
    persona=package['persona']
    current={key:persona[key] for key in ('author_id','version','build_id')}
    current['persona_payload_sha256']=payload_sha256(persona)
    seen=set();rows=[]
    for item in sidecar['items']:
        _keys(item,ITEM_FIELDS,'external item')
        _text(item['external_id'],'external_id',MAX_ID_CHARS)
        if item['external_id'] in seen:raise ValueError('duplicate external_id')
        seen.add(item['external_id'])
        if item['kind'] not in ('fresh_literature','other_persona_consultation','other'):
            raise ValueError('unsupported external kind label')
        if item['role']!='EXTERNAL_CONTEXT_ONLY':raise ValueError('external role must be EXTERNAL_CONTEXT_ONLY')
        for key in ('identifier_text','rationale','uncertainty'):_text(item[key],key)
        if item['identifier_text'] in identifiers:raise ValueError('EXTERNAL_ITEM_DUPLICATES_PACKAGE_SOURCE')
        year=item['year']
        if year is not None and (type(year) is not int or not 1<=year<=9999):
            raise ValueError('external year must be null or an integer from 1 to 9999')
        identity=item['other_package_identity']
        if identity is not None:
            _keys(identity,IDENTITY_FIELDS,'other package identity')
            for key in ('author_id','version','build_id'):_text(identity[key],key,MAX_ID_CHARS)
            digest=identity['persona_payload_sha256']
            if not isinstance(digest,str) or not re.fullmatch('[0-9a-f]{64}',digest):
                raise ValueError('other package identity requires a lowercase SHA256')
            if identity==current:raise ValueError('other package identity equals the current package')
        links=item['relates_to_claim_ids']
        if not isinstance(links,list) or len(links)>MAX_ITEMS:
            raise ValueError('claim links must be an array of at most 1000 IDs')
        linked=set()
        for identifier in links:
            _text(identifier,'claim_id',MAX_ID_CHARS)
            if identifier not in claims or identifier in linked:raise ValueError('unknown or duplicate related claim_id')
            linked.add(identifier)
        rows.append(copy.deepcopy(item))
    result=dict(schema='persona.external-evidence-review.v1',
        status='EXTERNAL_CONTEXT_DECLARATIONS_ONLY' if rows else 'NO_EXTERNAL_ITEMS',
        **{key:answer[key] for key in BINDINGS},external_sidecar_sha256=payload_sha256(sidecar),
        operator_id=sidecar['operator_id'],items=rows,item_count=len(rows),
        answer_status=answer['status'],answer_review_sha256=answer.get('review_sha256'),
        answer_review_boundary='Existing answer checker status only; no external item validates, satisfies or changes a citation or decision.',
        external_classification='EXTERNAL_NOT_PERSONA_KNOWLEDGE',holdout_comparator_membership='NOT_CHECKED',
        semantic_validation='NOT_PERFORMED',source_reread=False,network_calls=0,provider_invoked=False,
        other_agent_calls=0,llm_used=False,canonical_update_performed=False,citations_added=False,
        aggregate_score='NOT_COMPUTED',boundary=BOUNDARY)
    encode(result)
    return result


def encode(result):
    raw=(json.dumps(result,ensure_ascii=True,sort_keys=True,indent=2,allow_nan=False)+'\n').encode('utf-8')
    if len(raw)>MAX_OUTPUT_BYTES:raise ValueError('external evidence output exceeds 16 MiB')
    return raw


def render_text(result):
    lines=['External context (not persona knowledge)',BOUNDARY]
    def visit(value,prefix=''):
        if isinstance(value,dict):
            for key in sorted(value):lines.append(prefix+display(key)+':');visit(value[key],prefix+'  ')
        elif isinstance(value,list):
            if not value:lines.append(prefix+'[]')
            for index,item in enumerate(value):lines.append(prefix+'['+str(index)+']');visit(item,prefix+'  ')
        else:lines.append(prefix+display(json.dumps(value,ensure_ascii=False,allow_nan=False)))
    visit(result)
    raw=('\n'.join(lines)+'\n').encode('utf-8')
    if len(raw)>MAX_OUTPUT_BYTES:raise ValueError('external evidence text exceeds 16 MiB')
    return raw


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    create=sub.add_parser('template');create.add_argument('package',type=Path);create.add_argument('draft',type=Path)
    create.add_argument('--operator-id',required=True);create.add_argument('--output',type=Path,required=True)
    check=sub.add_parser('review');check.add_argument('package',type=Path);check.add_argument('draft',type=Path)
    check.add_argument('sidecar',type=Path);check.add_argument('--review',type=Path)
    check.add_argument('--format',choices=('json','text'),default='json');add_output_argument(check)
    args=parser.parse_args();preflight(parser,args.output)
    try:
        read=bounded_reader();package=read(args.package);draft=read(args.draft)
        if args.command=='template':result=template(package,draft,args.operator_id)
        else:result=review(package,draft,read(args.sidecar),read(args.review) if args.review else None)
        raw=render_text(result) if getattr(args,'format','json')=='text' else encode(result)
    except (ValueError,OSError,KeyError,TypeError,AttributeError,RuntimeError,RecursionError) as exc:
        parser.exit(1,str(exc)+'\n')
    emit(parser,raw,args.output)


if __name__=='__main__':main()
