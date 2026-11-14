"""Review explicit method-pattern application to design steps, never infer adoption."""
from exclusive_output import add_output_argument, emit, preflight
import argparse
import copy
import json
import sys
from pathlib import Path

from persona import payload_sha256
from reasoning_links import _sources
from design_scenario import review as review_design, render as render_design, _text
from pattern_hypotheses import inspect as inspect_patterns, render as render_patterns
from applicability_review import inspect as inspect_context, render as render_context
from answer_draft import _render_endpoint
from review_package import display
from strict_json import read_bounded, InputLimitError, loads

SCHEMA='persona.method-application.v1'
DECISIONS=('consider','exclude','defer')
ROLES=('method','constraint','counterargument')
TEXT_FIELDS=('application_rationale','target_condition_comparison','failure_condition','remaining_uncertainty')
FIELDS={'step_id','decision','proposed_role','required_checks','evidence_refs',*TEXT_FIELDS}
MAX_STEPS=128
MAX_REFS=32
MAX_CHECKS=16
MAX_INPUT_BYTES=8*1024*1024
MAX_OUTPUT_BYTES=16*1024*1024
BOUNDARY=('These are operator-declared considerations of one method-pattern hypothesis for each '
    'proposed design step, not evidence that the researcher used, endorsed or would choose the method. '
    'Consider/exclude/defer applies to this pattern-to-step relationship, not permission to execute '
    'or remove the step. Proposed application roles, original source stance, pattern roles and design '
    'link-use roles remain separate. A shared reference does not establish adaptation, applicability '
    'or semantic support; a missing shared reference is a review prompt, not proof of irrelevance. '
    'Context decisions address an enclosing observation, not every component assertion. Excluded '
    'context may legitimately support a counterargument; overlap prompts do not diagnose misuse. Explicit '
    'reasons, checks and failure conditions are operator text; their sufficiency is not evaluated. '
    'No missing condition, falsifier or uncertainty is borrowed from the pattern or sources. Imported '
    'pattern histories remain recorded declarations, not authenticated generation or human review. '
    'No source reread, model call, automatic approval, plan modification, citation transfer, scientific '
    'execution, canonical update or researcher-fidelity evaluation occurs.')


def _detach(value):
    try: raw=json.dumps(value,ensure_ascii=True,allow_nan=False).encode('utf-8')
    except (ValueError,TypeError,RecursionError) as exc: raise ValueError('method application inputs must be finite JSON data') from exc
    if len(raw)>MAX_INPUT_BYTES: raise ValueError('combined method application inputs exceed 8 MiB')
    return loads(raw)


def _prepare(package,patterns,context,links,proposal,pattern_id):
    checked,_=_sources(package);_text(pattern_id,'pattern_id',128)
    pattern_review=inspect_patterns(checked,patterns)
    selected=[row for row in pattern_review['hypotheses'] if row['pattern_id']==pattern_id]
    if len(selected)!=1: raise ValueError('select exactly one existing method-pattern ID')
    contextual=inspect_context(checked,context);design=review_design(checked,links,proposal)
    if contextual['question']!=design['question']: raise ValueError('context and design question text must match exactly')
    if len(design['steps'])>MAX_STEPS: raise ValueError('method application supports at most 128 explicit design steps')
    bindings=dict(package_sha256=payload_sha256(checked),pattern_form_sha256=pattern_review['form_sha256'],
        context_form_sha256=contextual['form_sha256'],link_artifact_sha256=design['link_artifact_sha256'],
        proposal_sha256=design['proposal_sha256'],pattern_id=pattern_id)
    return bindings,pattern_review,selected[0],contextual,design


def template(package,patterns,context,links,proposal,pattern_id,operator_id):
    values=_detach([package,patterns,context,links,proposal,pattern_id,operator_id])
    package,patterns,context,links,proposal,pattern_id,operator_id=values
    bindings,_,_,_,design=_prepare(package,patterns,context,links,proposal,pattern_id)
    _text(operator_id,'operator_id',128)
    return dict(schema=SCHEMA,bindings=bindings,operator_id=operator_id,
        applications=[dict(step_id=step['step_id'],decision='defer',proposed_role=None,
            application_rationale=None,target_condition_comparison=None,required_checks=[],failure_condition=None,
            remaining_uncertainty=None,evidence_refs=[]) for step in design['steps']])


def inspect(package,patterns,context,links,proposal,pattern_id,form):
    package,patterns,context,links,proposal,pattern_id,form=_detach([package,patterns,context,links,proposal,pattern_id,form])
    if isinstance(form,dict) and form.get('schema')=='persona.reviewed-application-proposals.v1':
        from application_proposals import inspect_reviewed
        return inspect_reviewed(package,patterns,context,links,proposal,pattern_id,form)
    bindings,pattern_review,selected,contextual,design=_prepare(package,patterns,context,links,proposal,pattern_id)
    if not isinstance(form,dict) or set(form)!={'schema','bindings','operator_id','applications'} or form['schema']!=SCHEMA:
        raise ValueError('method application form has missing or unsupported fields')
    _text(form['operator_id'],'operator_id',128)
    if not isinstance(form['bindings'],dict) or payload_sha256(form['bindings'])!=payload_sha256(bindings):
        raise ValueError('method application form is stale for the selected pattern, context, links or design')
    if not isinstance(form['applications'],list) or len(form['applications'])>MAX_STEPS:
        raise ValueError('applications must be an array of at most 128 steps')
    steps={row['step_id']:row for row in design['steps']}
    catalog={payload_sha256(row['evidence']['reference']):row for row in selected['evidence']}
    assessments={(row['evidence']['reference']['paper_id'],row['evidence']['reference']['observation_index']):row for row in contextual['assessments']}
    link_records={row['link_id']:row for row in design['evidence_links']['links']}
    seen=set();rows=[];prompts=[]
    for application in form['applications']:
        if not isinstance(application,dict) or set(application)!=FIELDS: raise ValueError('application has missing or unsupported fields')
        sid=application['step_id'];_text(sid,'step_id',128)
        if sid not in steps or sid in seen: raise ValueError('every proposed step must occur exactly once, including deferred/excluded applications')
        seen.add(sid);decision=application['decision'];role=application['proposed_role']
        if decision not in DECISIONS: raise ValueError('application decision must be consider, exclude or defer')
        if role is not None and role not in ROLES: raise ValueError('proposed_role must be method, constraint, counterargument or null')
        if decision!='defer' and role is None: raise ValueError('consider/exclude need an explicit proposed role, not an inferred one')
        for key in TEXT_FIELDS:
            if application[key] is not None:_text(application[key],key)
        if decision!='defer' and any(application[key] is None for key in ('application_rationale','target_condition_comparison','remaining_uncertainty')):
            raise ValueError('consider/exclude require explicit rationale, condition comparison and remaining uncertainty')
        checks=application['required_checks']
        if not isinstance(checks,list) or len(checks)>MAX_CHECKS: raise ValueError('required_checks must contain at most 16 explicit strings')
        for item in checks:_text(item,'required check')
        if len(set(checks))!=len(checks): raise ValueError('duplicate required check text')
        refs=application['evidence_refs']
        if not isinstance(refs,list) or len(refs)>MAX_REFS: raise ValueError('application evidence_refs must contain at most 32 references')
        if decision!='defer' and not refs: raise ValueError('consider/exclude need explicitly selected pattern evidence references')
        evidence=[];keys=set();codes=[]
        if decision=='defer':codes.append('METHOD_APPLICATION_DEFERRED')
        if role is None:codes.append('APPLICATION_ROLE_NOT_SUPPLIED')
        for key in TEXT_FIELDS:
            if application[key] is None:codes.append(key.upper()+'_NOT_SUPPLIED')
        if not checks:codes.append('REQUIRED_CHECKS_NOT_SUPPLIED')
        if not refs:codes.append('APPLICATION_EVIDENCE_REFS_NOT_SUPPLIED')
        target_uses={}
        for use in steps[sid]['link_uses']:
            link=link_records[use['link_id']]
            for direction in ('from','to'):
                node=link[direction+'_evidence'];key=payload_sha256(node['reference'])
                target_uses.setdefault(key,[]).append(dict(link_id=use['link_id'],role=use['role'],
                    relation=link['relation'],endpoint=direction,applicability_note=use['applicability_note']))
        for ref in refs:
            key=payload_sha256(ref)
            if key not in catalog or key in keys: raise ValueError('application references must be unique exact references from the selected pattern')
            keys.add(key);record=catalog[key];node=record['evidence'];ref=node['reference']
            assessment=assessments.get((ref['paper_id'],ref['observation_index']))
            rcodes=[]
            if not target_uses.get(key):rcodes.append('APPLICATION_REFERENCE_NOT_IN_TARGET_STEP_LINKS')
            if assessment is None:rcodes.append('NO_ENCLOSING_OBSERVATION_CONTEXT_ASSESSMENT')
            else:
                if assessment['decision']=='defer':rcodes.append('APPLICATION_SOURCE_CONTEXT_DEFERRED')
                if assessment['missing_fields']:rcodes.append('APPLICATION_SOURCE_CONTEXT_FIELDS_MISSING')
                if decision=='consider' and assessment['decision']=='exclude':rcodes.append('CONSIDERED_APPLICATION_HAS_EXCLUDED_SOURCE_CONTEXT')
            timing=('AFTER_REFERENCE_YEAR' if node['publication_year']>contextual['reference_year'] else
                'SAME_YEAR_ORDER_UNRESOLVED' if node['publication_year']==contextual['reference_year'] else 'BEFORE_REFERENCE_YEAR')
            if timing!='BEFORE_REFERENCE_YEAR':rcodes.append(timing)
            evidence.append(dict(evidence=copy.deepcopy(node),pattern_roles=copy.deepcopy(record['declared_roles']),
                pattern_evidence_uses=copy.deepcopy(record.get('evidence_uses',[])),publication_scope=timing,
                context_assessment=copy.deepcopy(assessment),context_match_basis='NONE' if assessment is None else
                    'EXACT_OBSERVATION' if ref['dimension'] is None else 'ENCLOSING_OBSERVATION_ONLY',
                target_step_link_uses=copy.deepcopy(target_uses.get(key,[])),review_prompts=rcodes))
            prompts.extend(dict(step_id=sid,reference=copy.deepcopy(ref),code=code) for code in rcodes)
        prompts.extend(dict(step_id=sid,code=code) for code in codes)
        rows.append(dict(**copy.deepcopy(application),claim_type='operator_interpretation',
            status='DECLARED_METHOD_APPLICATION_REQUIRES_REVIEW',target_step=copy.deepcopy(steps[sid]),
            evidence=evidence,review_prompts=codes,checks_completion='NOT_RECORDED_OR_EXECUTED',
            semantic_application_validation='NOT_PERFORMED'))
    if seen!=set(steps): raise ValueError('every proposed step must remain present, including deferred/excluded applications')
    by_id={row['step_id']:row for row in rows};rows=[by_id[step['step_id']] for step in design['steps']]
    result=dict(schema='persona.method-application-review.v1',status='METHOD_APPLICATION_REQUIRES_HUMAN_REVIEW' if rows else 'NO_DESIGN_STEPS_TO_REVIEW',
        bindings=bindings,form_sha256=payload_sha256(form),operator_id=form['operator_id'],operator_identity='RECORDED_NOT_AUTHENTICATED',
        question=design['question'],target_context=contextual['target_context'],pattern_id=pattern_id,
        selected_pattern=selected,pattern_review=pattern_review,context_review=contextual,design_review=design,
        applications=rows,review_prompts=prompts,decision_counts={d:sum(row['decision']==d for row in rows) for d in DECISIONS},
        decision_scope='SELECTED_PATTERN_TO_STEP_NOT_STEP_EXECUTION_OR_REMOVAL',
        execution_scope='CURRENT_INSPECTION_ONLY',historical_model_use='NOT_DETERMINED_BY_CURRENT_EXECUTION_FLAGS',
        source_reread=False,llm_used=False,provider_invoked=False,automatic_approval=False,design_modified=False,
        scientific_execution=False,canonical_update_performed=False,semantic_validation='NOT_PERFORMED',boundary=BOUNDARY)
    if len(json.dumps(result,ensure_ascii=True).encode('utf-8'))>MAX_OUTPUT_BYTES: raise ValueError('method application report exceeds 16 MiB')
    return result


def render(package,patterns,context,links,proposal,pattern_id,form):
    result=inspect(package,patterns,context,links,proposal,pattern_id,form)
    lines=['Operator method-pattern application review','Status: '+result['status'],
        'Question: '+display(result['question']),'Target context: '+display(result['target_context']),
        'Selected pattern: '+display(pattern_id),'Declared operator (not authenticated): '+display(result['operator_id']),
        'Form sha256: '+result['form_sha256'],BOUNDARY]
    for row in result['applications']:
        lines.append('Step '+display(row['step_id'])+': '+display(row['target_step']['proposed_action']))
        lines.append('  Pattern-to-step decision: '+row['decision']+'; proposed role='+display(row['proposed_role'])+' (not execution approval)')
        for key in TEXT_FIELDS:lines.append('  '+key+': '+('NOT_SUPPLIED' if row[key] is None else display(row[key])))
        lines.append('  Required checks (not executed): '+(' | '.join(display(item) for item in row['required_checks']) or 'NOT_SUPPLIED'))
        lines.append('  Review prompts: '+(', '.join(row['review_prompts']) or 'none detected; not validation'))
        for evidence in row['evidence']:
            lines.append('  Selected application basis; pattern roles='+', '.join(evidence['pattern_roles'])+'; '+evidence['publication_scope'])
            _render_endpoint(lines,evidence['evidence'])
            lines.append('    Context match: '+evidence['context_match_basis']+'; decision='+
                (evidence['context_assessment']['decision'] if evidence['context_assessment'] else 'NOT_SUPPLIED'))
            lines.append('    Route prompts: '+(', '.join(evidence['review_prompts']) or 'none detected; not validation'))
            for use in evidence['target_step_link_uses']:
                lines.append('    Existing target link '+display(use['link_id'])+': '+use['role']+' / '+use['relation']+' / '+use['endpoint'])
    lines.extend(['Full supplied pattern review and provenance:',render_patterns(result['pattern_review']).rstrip('\n'),
        'Full supplied context decisions and counterevidence:',render_context(result['context_review']).rstrip('\n'),
        'Unchanged design and all supplied links:',render_design(package,links,proposal).rstrip('\n')])
    if 'proposal_review' in result:
        from application_proposals import render_review
        lines.extend(['Full imported application history (candidate decisions are not application decisions):',
            render_review(result['proposal_review']).rstrip('\n')])
    output='\n'.join(lines)+'\n'
    if len(output.encode('utf-8'))>MAX_OUTPUT_BYTES: raise ValueError('method application report exceeds 16 MiB')
    return output


def _load(path):
    try:
        raw = read_bounded(path, MAX_INPUT_BYTES)
    except InputLimitError as exc:
        raise ValueError('method application JSON file exceeds 8 MiB') from exc
    return loads(raw)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('package','patterns','context','links','proposal'):parser.add_argument(name,type=Path)
    parser.add_argument('form',type=Path,nargs='?');parser.add_argument('--pattern-id',required=True)
    parser.add_argument('--template',action='store_true');parser.add_argument('--operator-id')
    parser.add_argument('--format',choices=('json','text'),default='json')
    # Python 3.10 parse_args cannot resume an optional positional after flags.
    # This CLI intentionally accepts the form before or after its named options.
    add_output_argument(parser); args=parser.parse_intermixed_args()
    preflight(parser, getattr(args, 'output', None))
    try:
        values=[_load(getattr(args,name)) for name in ('package','patterns','context','links','proposal')]+[args.pattern_id]
        if args.template:
            if args.form or args.format!='json':raise ValueError('template needs JSON output and no application form')
            output=json.dumps(template(*values,args.operator_id),ensure_ascii=True,indent=2)+'\n'
        else:
            if args.form is None or args.operator_id is not None:raise ValueError('inspection needs a supplied form without an operator override')
            form=_load(args.form);output=render(*values,form) if args.format=='text' else json.dumps(inspect(*values,form),ensure_ascii=True,indent=2)+'\n'
        if len(output.encode('utf-8'))>MAX_OUTPUT_BYTES:raise ValueError('method application output exceeds 16 MiB')
    except (ValueError,OSError,KeyError,TypeError,AttributeError,RecursionError) as exc:parser.exit(1,str(exc)+'\n')
    emit(parser, output.encode('utf-8'), getattr(args, 'output', None))


if __name__=='__main__':main()
