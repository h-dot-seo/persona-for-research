"""Compare two freshly reopened input cards without inferring research progress or approval."""
import argparse
import copy
import json
import sys
from collections import Counter
from pathlib import Path

import journey_inputs as inputs
import research_journey as journey
from method_application import FIELDS as APPLICATION_FIELDS
from persona import payload_sha256
from reasoning_links import _sources
from review_package import display

MAX_OUTPUT_BYTES=16*1024*1024
BOUNDARY=('Previous/current are caller-selected labels, not authenticated chronology. This compares '
    'two freshly inspected sets of supplied artifacts, not cached reports or historical source snapshots. '
    'The same declared author ID is not authenticated researcher identity. Paper/observation/component '
    'references and claim/step IDs are exact keys only, not stable semantic identities: reordering or '
    'replacement can change their meaning. Route additions/removals describe the supplied route union, '
    'not literature additions/deletions. Declared text is compared separately from resolved evidence '
    'and route uses. No paraphrase matching, causal explanation, researcher change of mind, methodological '
    'improvement, review completion or permission to reuse old bindings is inferred. Prompt counts are '
    'navigation only; an absent prompt is not a resolved scientific issue. Both complete fresh reports '
    'retain original/reviewed/rejected histories and separate current source checks. All review identities '
    'and historical provenance remain unauthenticated. No provider call, source discovery, input write, '
    'automatic rebinding, approval, scientific execution or canonical update occurs.')


def _encode(value):
    raw=(json.dumps(value,ensure_ascii=True,allow_nan=False,indent=2)+'\n').encode('utf-8')
    if len(raw)>MAX_OUTPUT_BYTES:raise ValueError('combined journey comparison exceeds 16 MiB; narrow the supplied artifacts explicitly')
    return raw


def _changed_fields(before,after):
    return sorted(key for key in set(before)|set(after) if key not in before or key not in after
        or payload_sha256(before[key])!=payload_sha256(after[key]))


def _files(before,after):
    rows=[]
    for name in inputs.NAMES:
        old=before['artifacts'][name];new=after['artifacts'][name]
        if old is None and new is None:status='NOT_SUPPLIED_ON_EITHER_SIDE'
        elif old is None:status='ONLY_CURRENT_SELECTION'
        elif new is None:status='ONLY_PREVIOUS_SELECTION'
        elif old['json_sha256']!=new['json_sha256']:status='LOGICAL_JSON_CHANGED'
        elif old['raw_sha256']!=new['raw_sha256'] or old['bytes']!=new['bytes']:status='RAW_BYTES_CHANGED_LOGICAL_JSON_SAME'
        else:status='SAME_BYTES_AND_JSON'
        rows.append(dict(artifact=name,status=status,relative_path_changed=bool(old and new and old['path']!=new['path']),
            previous=copy.deepcopy(old),current=copy.deepcopy(new)))
    return rows


def _routes(before,after):
    old={row['reference_sha256']:row for row in before};new={row['reference_sha256']:row for row in after};rows=[]
    for key in sorted(old.keys()|new.keys()):
        a=old.get(key);b=new.get(key)
        status='ONLY_CURRENT_ROUTE' if a is None else 'ONLY_PREVIOUS_ROUTE' if b is None else ('CHANGED_AT_EXACT_REFERENCE' if payload_sha256(a)!=payload_sha256(b) else 'UNCHANGED_AT_EXACT_REFERENCE')
        changed=_changed_fields(a,b) if a is not None and b is not None else []
        rows.append(dict(reference_sha256=key,reference=copy.deepcopy((a if a is not None else b)['evidence']['reference']),
            status=status,changed_evidence_fields=_changed_fields(a['evidence'],b['evidence']) if a is not None and b is not None else [],
            changed_route_fields=[field for field in changed if field not in ('evidence','reference_sha256')],
            previous_route_sha256=payload_sha256(a) if a is not None else None,
            current_route_sha256=payload_sha256(b) if b is not None else None))
    return rows


def _declarations(args,report):
    values=dict(zip(inputs.REQUIRED,args[:len(inputs.REQUIRED)]));review=args[-1]
    selected=report['pattern_transfer_review']['selected_pattern']
    pattern={key:copy.deepcopy(selected[key]) for key in ('pattern_id','operator_hypothesis','scope_note','alternative_explanation','falsification_check','uncertainty')}
    applications=[{key:copy.deepcopy(row[key]) for key in sorted(APPLICATION_FIELDS)}
        for row in report.get('method_application_review',{}).get('applications',[])]
    return {
        'answer_claims':('claim_id',values['draft']['claims']),
        'answer_review_decisions':('claim_id',[] if review is None else review['decisions']),
        'design_steps':('step_id',values['proposal']['steps']),
        'argument_steps':('step_id',values['argument']['steps']),
        'evidence_links':('link_id',values['links']['links']),
        'publication_relationships':('relation_id',values['publication_relations']['relations']),
        'method_applications':('step_id',applications),
        'selected_pattern_text':('pattern_id',[pattern]),
    }


def _records(before,after):
    groups=[]
    for name,(field,previous) in before.items():
        current=after[name][1];old={row[field]:row for row in previous};new={row[field]:row for row in current};rows=[]
        for key in sorted(old.keys()|new.keys()):
            a=old.get(key);b=new.get(key)
            status='ONLY_CURRENT_DECLARATION' if a is None else 'ONLY_PREVIOUS_DECLARATION' if b is None else ('CHANGED_AT_DECLARED_ID' if payload_sha256(a)!=payload_sha256(b) else 'UNCHANGED_AT_DECLARED_ID')
            rows.append(dict(declared_id=key,status=status,changed_fields=_changed_fields(a,b) if a is not None and b is not None else [],
                previous=copy.deepcopy(a),current=copy.deepcopy(b)))
        groups.append(dict(group=name,id_field=field,
            scope='DECLARED_FIELDS_ONLY_NOT_RESOLVED_EVIDENCE_OR_AUTHENTICATED_REVIEW',
            previous_id_order=[row[field] for row in previous],current_id_order=[row[field] for row in current],
            order_changed=[row[field] for row in previous]!=[row[field] for row in current],records=rows))
    return groups


def _prompts(previous,current):
    old=Counter(payload_sha256(row) for row in previous);new=Counter(payload_sha256(row) for row in current)
    catalog={payload_sha256(row):row for row in previous+current};rows=[]
    for key in sorted(old.keys()|new.keys()):
        if old[key]==new[key]:status='SAME_EXACT_PROMPT_COUNT'
        elif not old[key]:status='ONLY_CURRENT_EXACT_PROMPT'
        elif not new[key]:status='ONLY_PREVIOUS_EXACT_PROMPT_NOT_PROOF_RESOLVED'
        else:status='EXACT_PROMPT_COUNT_CHANGED'
        rows.append(dict(prompt_sha256=key,prompt=copy.deepcopy(catalog[key]),previous_count=old[key],current_count=new[key],status=status))
    return rows


def compare(previous_card,previous_root,current_card,current_root,*,previous_source_root=None,current_source_root=None):
    # Both cards and all selected JSON bytes are checked before either live source audit.
    previous=inputs._load_artifacts(previous_card,previous_root,previous_source_root,bound=True)
    current=inputs._load_artifacts(current_card,current_root,current_source_root,bound=True)
    old_package,_=_sources(previous[2][0]);new_package,_=_sources(current[2][0])
    author=old_package['persona']['author_id']
    if author!=new_package['persona']['author_id']:raise ValueError('journey comparison requires the same declared scholarly identity')
    reports=[]
    for card,records,args,options in (previous,current):
        report=journey.inspect(*args,**options)
        report['local_input_file_check']=inputs._verification(card,records)
        journey.encode_result(report);reports.append(report)
    before,after=reports
    fields=('question','topic','reference_year','selected_pattern_id')
    metadata=[dict(field=key,previous=before[key],current=after[key],changed=before[key]!=after[key]) for key in fields]
    metadata.append(dict(field='target_context',previous=before['pattern_transfer_review']['target_context'],
        current=after['pattern_transfer_review']['target_context'],
        changed=before['pattern_transfer_review']['target_context']!=after['pattern_transfer_review']['target_context']))
    bindings=dict(previous_card_sha256=payload_sha256(previous[0]),current_card_sha256=payload_sha256(current[0]),
        previous_journey_input_sha256=before['journey_input_sha256'],current_journey_input_sha256=after['journey_input_sha256'],
        previous_inspected_snapshot_sha256=payload_sha256(before),current_inspected_snapshot_sha256=payload_sha256(after))
    result=dict(schema='persona.journey-comparison.v1',status='HUMAN_REVIEW_REQUIRED_NOT_RESEARCH_APPROVAL',
        declared_author_id=author,identity_scope='MATCHED_DECLARED_ID_NOT_AUTHENTICATED',bindings=bindings,
        comparison_input_sha256=payload_sha256(bindings),
        input_card_changed=bindings['previous_card_sha256']!=bindings['current_card_sha256'],
        logical_journey_inputs_changed=before['journey_input_sha256']!=after['journey_input_sha256'],
        inspected_reports_changed=bindings['previous_inspected_snapshot_sha256']!=bindings['current_inspected_snapshot_sha256'],
        context_comparison=metadata,artifact_comparison=_files(previous[0],current[0]),
        exact_reference_comparison=_routes(before['evidence_routes'],after['evidence_routes']),
        declared_record_comparison=_records(_declarations(previous[2],before),_declarations(current[2],after)),
        exact_prompt_comparison=_prompts(before['review_agenda'],after['review_agenda']),
        previous_report=before,current_report=after,
        source_recheck_scope=dict(previous=before['source_reread'],current=after['source_reread'],
            timing='BOTH_ARE_CURRENT_READS_NOT_HISTORICAL_SNAPSHOTS'),
        route_scope='SUPPLIED_ROUTE_UNION_NOT_ALL_CHANGED_EVIDENCE_OR_LITERATURE',
        record_scope='SELECTED_DECLARED_GROUPS_NOT_ALL_INPUT_FIELDS_OR_IMPORTED_HISTORY_CHANGES',
        summary_scope='NAVIGATION_ONLY_NOT_EXHAUSTIVE_SEE_FULL_REPORTS_AND_INPUT_ARTIFACTS',
        exact_key_correspondence='NOT_STABLE_SEMANTIC_IDENTITY',prompt_count_scope='NOT_A_SCORE_OR_PROOF_OF_RESOLUTION',
        root_arguments_persisted=False,input_files_modified=False,hashes_refreshed=False,
        semantic_comparison='NOT_PERFORMED',researcher_fidelity_evaluation='NOT_PERFORMED',human_review_authenticated=False,
        provider_invoked=False,external_transmission=False,automatic_rebinding=False,automatic_approval=False,
        scientific_execution=False,canonical_update_performed=False,boundary=BOUNDARY)
    _encode(result)
    return result


def render(previous_card,previous_root,current_card,current_root,*,previous_source_root=None,current_source_root=None,format='json'):
    if format not in ('json','text'):raise ValueError('comparison format must be json or text')
    result=compare(previous_card,previous_root,current_card,current_root,
        previous_source_root=previous_source_root,current_source_root=current_source_root)
    if format=='json':return _encode(result).decode('utf-8')
    lines=['Research journey comparison | human review required, not research approval',BOUNDARY,
        'Comparison input sha256: '+result['comparison_input_sha256'],
        'Logical journey inputs changed: '+str(result['logical_journey_inputs_changed']),
        'Input card changed (paths/bytes included): '+str(result['input_card_changed']),
        'Context changes (not assumed equivalent questions):']
    for row in result['context_comparison']:
        lines.append('  '+row['field']+': '+display(row['previous'])+' -> '+display(row['current'])+' | changed='+str(row['changed']))
    lines.append('Named artifact changes:')
    for row in result['artifact_comparison']:
        lines.append('  '+row['artifact']+': '+row['status']+'; relative path changed='+str(row['relative_path_changed']))
    lines.append('Exact-reference routes (not stable identities or a full corpus comparison):')
    for row in result['exact_reference_comparison']:
        lines.append('  '+display(json.dumps(row['reference'],ensure_ascii=True))+' | '+row['status']+
            '; evidence fields='+','.join(row['changed_evidence_fields'])+'; route fields='+','.join(row['changed_route_fields']))
    lines.append('Declared records (resolved source changes are separate):')
    for group in result['declared_record_comparison']:
        lines.append('  '+group['group']+'; declared ID order changed='+str(group['order_changed']))
        for row in group['records']:
            lines.append('    '+display(row['declared_id'])+': '+row['status']+'; fields='+','.join(row['changed_fields']))
    lines.append('Exact prompt counts (not resolved issues or a score):')
    for row in result['exact_prompt_comparison']:
        lines.append('  '+str(row['previous_count'])+' -> '+str(row['current_count'])+' | '+row['status']+' | '+display(json.dumps(row['prompt'],ensure_ascii=True)))
    lines.extend(['Complete comparison including both fresh reports and all preserved histories:',_encode(result).decode('utf-8')])
    output='\n'.join(lines)+'\n'
    if len(output.encode('utf-8'))>MAX_OUTPUT_BYTES:raise ValueError('text journey comparison exceeds 16 MiB')
    return output


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('previous',type=Path);parser.add_argument('current',type=Path)
    parser.add_argument('--previous-root',type=Path,required=True);parser.add_argument('--current-root',type=Path,required=True)
    parser.add_argument('--previous-source-root',type=Path);parser.add_argument('--current-source-root',type=Path)
    parser.add_argument('--format',choices=('json','text'),default='json');args=parser.parse_args()
    try:
        output=render(inputs._load_card(args.previous),args.previous_root,inputs._load_card(args.current),args.current_root,
            previous_source_root=args.previous_source_root,current_source_root=args.current_source_root,format=args.format)
    except (ValueError,OSError,KeyError,TypeError,AttributeError,RecursionError) as exc:parser.exit(1,str(exc)+'\n')
    sys.stdout.buffer.write(output.encode('utf-8'))


if __name__=='__main__':main()
