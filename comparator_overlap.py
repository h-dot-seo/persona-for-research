"""Inventory exact strings in separately declared comparator observations, not specificity."""
import argparse
import json
import re
import sys
from pathlib import Path
from compare_releases import checked_package
from research_workflow import validated_source_rules
from methodology_trajectory import summarize
from human_validation import bindings
from persona import payload_sha256
from review_package import display
from strict_json import read_bounded, loads

CORPUS_SCHEMA='persona.comparator-corpus.v1'
SCHEMA='persona.comparator-overlap.v1'
MAX_INPUT_BYTES=8*1024*1024
MAX_OUTPUT_BYTES=16*1024*1024
FIELDS=('schema','author_id','curator_id','handling_declaration','papers')
PAPER_FIELDS=('paper_id','author_id','split','runtime_knowledge_eligible','authorized','source_sha256','locator','kind','year','topic','observations')
OBSERVATION_FIELDS=('method','condition','limitation','locator','topic','stance','claim_type','evidence_quote')
BOUNDARY=('Exact supplied strings only: absence in the supplied comparator set is not uniqueness; '
 'exact string sharing is not shared practice, and string differences do not establish different practice. '
 'Author and curator labels are not authenticated identities; coauthorship and independent handling are not verified. '
 'Distinct supplied source hashes are not independent studies. Holdout membership/overlap is NOT_CHECKED. '
 'No source bytes are read, quotes or hashes authenticated, network/provider/other-agent calls made, '
 'or scientific judgment, ranking, human-validation promotion or canonical update performed. '
 'Rule IDs are build-local positions. Comparator observations never become persona knowledge. '
 'Text, labels and hashes may be private; this report grants no transmission permission.')


def _keys(value,fields):
    if not isinstance(value,dict) or set(value)!=set(fields):raise ValueError('missing or unsupported comparator fields')


def _text(value):
    if not isinstance(value,str) or not value.strip():raise ValueError('comparator text must be nonblank')


def validate_corpus(value):
    _keys(value,FIELDS)
    if value['schema']!=CORPUS_SCHEMA:raise ValueError('unsupported comparator schema')
    for key in ('author_id','curator_id','handling_declaration'):_text(value[key])
    if not isinstance(value['papers'],list):raise ValueError('comparator papers must be an array')
    seen=set()
    for p in value['papers']:
        _keys(p,PAPER_FIELDS)
        for key in ('paper_id','author_id','locator','topic'):_text(p[key])
        if p['paper_id'] in seen:raise ValueError('duplicate comparator paper_id')
        seen.add(p['paper_id'])
        if p['author_id']!=value['author_id']:raise ValueError('single comparator author label required')
        if p['split']!='comparator' or p['runtime_knowledge_eligible'] is not False or p['authorized'] is not True:
            raise ValueError('explicit authorized non-runtime comparator declaration required')
        if p['kind'] not in ('research','review') or type(p['year']) is not int:
            raise ValueError('comparator kind/year invalid')
        if not isinstance(p['source_sha256'],str) or re.fullmatch('[0-9a-f]{64}',p['source_sha256']) is None:
            raise ValueError('comparator source hash invalid')
        if not isinstance(p['observations'],list):raise ValueError('observations must be an array')
        for obs in p['observations']:
            _keys(obs,OBSERVATION_FIELDS)
            for key in OBSERVATION_FIELDS:
                if key!='evidence_quote':_text(obs[key])
            if obs['evidence_quote'] is not None and not isinstance(obs['evidence_quote'],str):raise ValueError('quote must be string or null')
            if obs['stance'] not in ('support','challenge') or obs['claim_type'] not in ('explicit_statement','operator_interpretation'):
                raise ValueError('explicit comparator stance/claim_type required')
    return value['papers']


def inspect(value,comparator,topic):
    _text(topic)
    package=checked_package(value);papers=validated_source_rules(package)
    others=validate_corpus(comparator)
    if comparator['author_id']==package['persona']['author_id']:raise ValueError('COMPARATOR_AUTHOR_LABEL_EQUALS_TARGET')
    ids={p['paper_id'] for p in papers};hashes={p['source_sha256'] for p in papers}
    if any(p['paper_id'] in ids for p in others):raise ValueError('COMPARATOR_SHARES_TARGET_PAPER_ID')
    if any(p['source_sha256'] in hashes for p in others):raise ValueError('COMPARATOR_SHARES_TARGET_SOURCE_HASH')
    topic=topic.casefold();groups={};lookup={p['paper_id']:p for p in papers}
    for g in summarize(package['persona']['rules']):
        if g['topic']!=topic:continue
        refs=[{k:e[k] for k in ('rule_id','paper_id','locator','stance','claim_type')} for e in g['evidence']]
        groups[(g['method'],g['condition'])]=dict(target=dict(rule_refs=refs,
            supporting_rule_ids=[e['rule_id'] for e in refs if e['stance']=='support'],
            challenging_rule_ids=[e['rule_id'] for e in refs if e['stance']=='challenge'],
            distinct_source_hash_count=len({lookup[e['paper_id']]['source_sha256'] for e in refs})),comparator_rows=[])
    total=0
    for p in others:
        for i,obs in enumerate(p['observations']):
            if obs['topic'].casefold()!=topic:continue
            total+=1
            groups.setdefault((obs['method'],obs['condition']),dict(target=None,comparator_rows=[]))['comparator_rows'].append((p,i,obs))
    target_count=sum(len(g['target']['rule_refs']) for g in groups.values() if g['target'])
    output=[];only=[];row_bytes=0
    for (method,condition),g in sorted(groups.items()):
        rows=sorted(g['comparator_rows'],key=lambda x:(x[0]['paper_id'],x[1]))
        other=dict(observation_refs=[dict(paper_id=p['paper_id'],observation_index=i,locator=o['locator'],stance=o['stance'],claim_type=o['claim_type']) for p,i,o in rows],
            paper_ids=sorted({p['paper_id'] for p,_,_ in rows}),years=sorted({p['year'] for p,_,_ in rows}),
            stance_counts={s:sum(o['stance']==s for _,_,o in rows) for s in ('support','challenge')},
            distinct_source_hash_count=len({p['source_sha256'] for p,_,_ in rows}))
        status=('COMPARATOR_ONLY_EXACT_STRING' if g['target'] is None else 'SHARED_EXACT_STRING_WITH_COMPARATOR' if rows else
                'NO_TOPIC_MATCHED_COMPARATOR_OBSERVATIONS' if not total else 'NOT_FOUND_IN_SUPPLIED_COMPARATOR_SET')
        row=dict(method=method,condition=condition,target=g['target'],comparator=other,status=status)
        row_bytes+=len(encode(row))
        if row_bytes>MAX_OUTPUT_BYTES:raise ValueError('comparator rows exceed output budget')
        (only if g['target'] is None else output).append(row)
    result=dict(schema=SCHEMA,package=bindings(package['persona'],package['knowledge']),comparator_corpus_sha256=payload_sha256(comparator),
        comparator_author_id=comparator['author_id'],curator_id=comparator['curator_id'],handling_declaration=comparator['handling_declaration'],handling_status='DECLARED_NOT_VERIFIED',
        topic=topic,target_topic_rule_count=target_count,comparator_topic_observation_count=total,
        target_topic_status='TARGET_TOPIC_PRESENT' if target_count else 'NO_TARGET_TOPIC_RULES',
        comparator_topic_status='COMPARATOR_TOPIC_PRESENT' if total else 'NO_TOPIC_MATCHED_COMPARATOR_OBSERVATIONS',
        groups=output,comparator_only_groups=only,specificity='NOT_DERIVED',source_check='NOT_PERFORMED',holdout_overlap='NOT_CHECKED',
        llm_used=False,canonical_update_performed=False,package_modified=False,boundary=BOUNDARY)
    encode(result)
    return result


def encode(value,format='json'):
    raw=(json.dumps(value,ensure_ascii=True,sort_keys=True,indent=2,allow_nan=False)+'\n').encode('utf-8')
    if format=='text':
        # Display every report field; JSON escaping keeps supplied controls inert.
        raw=('Comparator exact-string inventory (not specificity)\n'+'\n'.join(display(line) for line in raw.decode('utf-8').splitlines())+'\n').encode('utf-8')
    if len(raw)>MAX_OUTPUT_BYTES:raise ValueError('comparator report exceeds output budget')
    return raw


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('package',type=Path);p.add_argument('comparator',type=Path)
    p.add_argument('--topic',required=True);p.add_argument('--format',choices=('json','text'),default='json')
    p.add_argument('--source-selection',type=Path);p.add_argument('--source-root',type=Path)
    args=p.parse_args()
    if (args.source_selection is None)!=(args.source_root is None):p.error('source selection and root are required together')
    try:
        a=read_bounded(args.package,MAX_INPUT_BYTES)
        b=read_bounded(args.comparator,MAX_INPUT_BYTES-len(a))
        if args.source_selection is not None:
            mapping=read_bounded(args.source_selection,MAX_INPUT_BYTES-len(a)-len(b))
            from comparator_sources import inspect_sources
            result=inspect_sources(loads(a),loads(b),args.topic,loads(mapping),args.source_root)
        else:
            result=inspect(loads(a),loads(b),args.topic)
        raw=encode(result,args.format)
    except (ValueError,OSError,TypeError,KeyError,AttributeError,RecursionError):p.exit(1,'Comparator inventory failed.\n')
    sys.stdout.buffer.write(raw)


if __name__=='__main__':main()
