"""Inspect exact rule-content correspondence across bound packages, not semantic identity."""
import argparse
import copy
import json
from pathlib import Path

from compare_releases import checked_package
from exclusive_output import add_output_argument, emit, preflight
from observation_provenance import content_sha256
from persona import payload_sha256
from research_workflow import validated_source_rules
from review_package import display
from strict_json import read_bounded, loads

MAX_INPUT_BYTES = 8 * 1024 * 1024
MAX_OUTPUT_BYTES = 16 * 1024 * 1024
KEYS = ('rule_payload_sha256', 'observation_content_sha256')
BOUNDARY = ('Exact supplied record hashes, not stable rule IDs or semantic identity. Position changes '
    'are not priority changes. ONLY_PREVIOUS_PACKAGE and ONLY_CURRENT_PACKAGE do not mean withdrawal, '
    'literature addition or a change of mind. No proof that human judgments, links or answer citations '
    'remain valid. No rebinding, transfer, source reread, LLM or network call; canonical files are '
    'unchanged. Explicit output only saves this private view, not permission to share. Quotes may be '
    'included. Manual locator candidates are not inferred correspondences or approval.')


def bounded_reader():
    remaining = [MAX_INPUT_BYTES]
    def read(path):
        raw = read_bounded(path, remaining[0])
        remaining[0] -= len(raw)
        return loads(raw)
    return read


def _package(value, knowledge=None):
    package = checked_package(dict(persona=value, knowledge=knowledge) if knowledge is not None else value)
    papers = validated_source_rules(package)
    return package, papers


def _positions(rows):
    return [{key:row[key] for key in ('rule_id','rule_index','paper_id','observation_index')} for row in rows]


def _groups(rows, key):
    groups = {}
    for row in rows:
        groups.setdefault(row[key], []).append(row)
    return groups


def inventory(value, knowledge=None):
    package, papers = _package(value, knowledge)
    persona = package['persona']; records = []; row_bytes = 0
    rules = iter(persona['rules'])
    for paper in papers:
        for index, observation in enumerate(paper['observations']):
            rule = next(rules)
            payload = {k:copy.deepcopy(v) for k,v in rule.items() if k != 'rule_id'}
            records.append(dict(rule_id=rule['rule_id'], rule_index=len(records), paper_id=paper['paper_id'],
                observation_index=index, source_sha256=paper['source_sha256'],
                rule_payload_sha256=payload_sha256(dict(rule=payload, source_sha256=paper['source_sha256'])),
                observation_content_sha256=payload_sha256(dict(content_sha256=content_sha256(observation),
                    paper_id=paper['paper_id'], source_sha256=paper['source_sha256'])),
                component_sha256={dimension:payload_sha256(component)
                                  for dimension,component in observation.get('reasoning',{}).items()},
                rule_payload=payload, paper_metadata={k:copy.deepcopy(v) for k,v in paper.items() if k != 'observations'}))
            row_bytes += len(_encoded(records[-1]))
            if row_bytes > MAX_OUTPUT_BYTES:
                raise ValueError('rule inventory rows exceed 16 MiB; no truncation')
    duplicate_keys = []
    for key in KEYS:
        for digest, rows in _groups(records,key).items():
            if len(rows)>1:
                duplicate_keys.append(dict(status='AMBIGUOUS_DUPLICATE_KEY', key_type=key,
                                           key_sha256=digest, positions=_positions(rows)))
    result = dict(schema='persona.rule-inventory.v1',
        package=dict(author_id=persona['author_id'],version=persona['version'],build_id=persona['build_id'],
                     persona_payload_sha256=payload_sha256(persona),
                     knowledge_papers_sha256=payload_sha256(package['knowledge']['papers'])),
        rules=records, duplicate_keys=duplicate_keys,
        position_scope='ZERO_BASED_RULE_AND_OBSERVATION_INDEXES_WITHIN_THIS_BUILD_ONLY',
        semantic_validation='NOT_PERFORMED', canonical_update_performed=False, source_reread=False,
        llm_used=False, network_calls=0, boundary=BOUNDARY)
    _encoded(result)
    return result


def _changed(a,b):
    return sorted(key for key in a.keys() | b.keys()
                  if key not in a or key not in b or payload_sha256(a[key]) != payload_sha256(b[key]))


def compare(previous, current, previous_knowledge=None, current_knowledge=None):
    before = inventory(previous, previous_knowledge); after = inventory(current, current_knowledge)
    if before['package']['author_id'] != after['package']['author_id']:
        raise ValueError('rule comparison requires the same supplied author_id, not verified identity')
    old, new = before['rules'], after['rules']
    groups = [(_groups(old,key), _groups(new,key)) for key in KEYS]
    blocked_old, blocked_new = set(), set()
    ambiguous = []
    for key,(left,right) in zip(KEYS,groups):
        for digest in sorted(left.keys() | right.keys()):
            a,b = left.get(digest,[]),right.get(digest,[])
            if len(a)>1 or len(b)>1:
                ambiguous.append(dict(status='AMBIGUOUS_DUPLICATE_KEY',key_type=key,key_sha256=digest,
                                      previous_positions=_positions(a),current_positions=_positions(b)))
                blocked_old.update(row['rule_index'] for row in a)
                blocked_new.update(row['rule_index'] for row in b)
    used_old,used_new=set(blocked_old),set(blocked_new)
    matches=[]
    for key,(left,right) in zip(KEYS,groups):
        for row in old:
            if row['rule_index'] in used_old:continue
            candidates=right.get(row[key],[])
            if len(candidates)!=1 or len(left[row[key]])!=1:continue
            other=candidates[0]
            if other['rule_index'] in used_new:continue
            status=('SAME_RULE_PAYLOAD_SAME_POSITION' if row['rule_index']==other['rule_index'] else
                    'SAME_RULE_PAYLOAD_DIFFERENT_POSITION') if key==KEYS[0] else 'SAME_OBSERVATION_CONTENT_OTHER_FIELDS_CHANGED'
            matches.append(dict(status=status,matching_key=key,key_sha256=row[key],
                previous_position=_positions([row])[0],current_position=_positions([other])[0],
                changed_rule_fields=_changed(row['rule_payload'],other['rule_payload']),
                changed_paper_fields=_changed(row['paper_metadata'],other['paper_metadata']),
                changed_component_dimensions=_changed(row['component_sha256'],other['component_sha256']),
                previous_rule_payload_sha256=row[KEYS[0]],current_rule_payload_sha256=other[KEYS[0]]))
            used_old.add(row['rule_index']);used_new.add(other['rule_index'])
    unmatched=[]
    for rows,used,status in ((old,used_old,'ONLY_PREVIOUS_PACKAGE'),(new,used_new,'ONLY_CURRENT_PACKAGE')):
        for row in rows:
            if row['rule_index'] not in used:
                unmatched.append(dict(status=status,position=_positions([row])[0],
                                      rule_payload_sha256=row[KEYS[0]],observation_content_sha256=row[KEYS[1]]))
    # Group both sides instead of materializing a Cartesian candidate product.
    # Every position and exact hash stays visible, including already matched rows.
    locator_groups = {}
    for side, rows in (('previous_positions',old),('current_positions',new)):
        for row in rows:
            key=(row['paper_id'],row['rule_payload']['locator'])
            group=locator_groups.setdefault(key,dict(previous_positions=[],current_positions=[]))
            group[side].append(dict(**_positions([row])[0],rule_payload_sha256=row[KEYS[0]],
                                    observation_content_sha256=row[KEYS[1]],source_sha256=row['source_sha256']))
    manual=[dict(status='MANUAL_REVIEW_CANDIDATE_GROUP_NOT_IDENTITY',paper_id=key[0],locator=key[1],**group)
            for key,group in locator_groups.items() if group['previous_positions'] and group['current_positions']]
    result=dict(schema='persona.rule-correspondence.v1',previous=before,current=after,
        matches=sorted(matches,key=lambda row:row['previous_position']['rule_index']),
        ambiguous_keys=ambiguous,unmatched=unmatched,manual_locator_candidates=manual,
        counts=dict(exact_correspondences=len(matches),ambiguous_keys=len(ambiguous),
                    unmatched_positions=len(unmatched),manual_candidate_groups=len(manual)),
        duplicate_policy='Either key duplicated on either side blocks all involved positions from automatic pairing.',
        semantic_validation='NOT_PERFORMED',canonical_update_performed=False,source_reread=False,
        llm_used=False,network_calls=0,boundary=BOUNDARY)
    _encoded(result)
    return result


def _encoded(result):
    raw=(json.dumps(result,ensure_ascii=True,sort_keys=True,indent=2,allow_nan=False)+'\n').encode('utf-8')
    if len(raw)>MAX_OUTPUT_BYTES:raise ValueError('rule correspondence output exceeds 16 MiB')
    return raw


def render_text(result):
    # Preserve every field; display escapes controls/directional characters in data.
    lines=['Exact rule-record view (not semantic identity)',BOUNDARY]
    def visit(value, prefix=''):
        if isinstance(value,dict):
            for key in sorted(value):
                lines.append(prefix+display(key)+':');visit(value[key],prefix+'  ')
        elif isinstance(value,list):
            if not value:lines.append(prefix+'[]')
            for index,item in enumerate(value):
                lines.append(prefix+'['+str(index)+']');visit(item,prefix+'  ')
        else:lines.append(prefix+display(json.dumps(value,ensure_ascii=False,allow_nan=False)))
    visit(result)
    raw=('\n'.join(lines)+'\n').encode('utf-8')
    if len(raw)>MAX_OUTPUT_BYTES:raise ValueError('rule correspondence text exceeds 16 MiB')
    return raw


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    inv=sub.add_parser('inventory');inv.add_argument('package',type=Path);inv.add_argument('knowledge',type=Path,nargs='?')
    cmp=sub.add_parser('compare');cmp.add_argument('previous',type=Path);cmp.add_argument('current',type=Path)
    cmp.add_argument('--previous-knowledge',type=Path);cmp.add_argument('--current-knowledge',type=Path)
    for p in (inv,cmp):
        p.add_argument('--format',choices=('json','text'),default='json');add_output_argument(p)
    args=parser.parse_args();preflight(parser,args.output)
    try:
        read=bounded_reader()
        if args.command=='inventory':
            result=inventory(read(args.package),read(args.knowledge) if args.knowledge else None)
        else:
            result=compare(read(args.previous),read(args.current),
                read(args.previous_knowledge) if args.previous_knowledge else None,
                read(args.current_knowledge) if args.current_knowledge else None)
        raw=render_text(result) if args.format=='text' else _encoded(result)
    except (ValueError,OSError,KeyError,TypeError,AttributeError,RuntimeError,RecursionError) as exc:
        parser.exit(1,str(exc)+'\n')
    emit(parser,raw,args.output)


if __name__=='__main__':main()
