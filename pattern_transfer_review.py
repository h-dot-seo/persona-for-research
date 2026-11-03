"""Join one explicitly selected pattern with context review and answer/design evidence uses."""
import argparse
import json
import sys
from pathlib import Path
from persona import payload_sha256
from pattern_hypotheses import inspect as inspect_patterns
from applicability_review import inspect as inspect_context, render as render_context
from review_journey import assemble,render as render_packet
from answer_draft import _render_endpoint
from review_package import display
from strict_json import load

BOUNDARY=('Shared references are mechanical trace routes, not proof that a pattern was implemented, a method is applicable or a proposal is scientifically valid. '
    'Context decisions attach to the enclosing observation, not every semantic assertion in its components. Excluded/deferred evidence can be cited for '
    'criticism; a flagged overlap is not automatically a misuse. Pattern support/challenge roles, source stance, answer citation roles and design link-use '
    'roles remain separate. Missing routes are review prompts, not a requirement to cite everything. No author-thought inference, source reread, '
    'LLM/API call, automatic plan generation, rebinding or canonical update is performed.')


def inspect(package,patterns,context,links,proposal,draft,pattern_id):
    patterns_result=inspect_patterns(package,patterns)
    selected=[p for p in patterns_result['hypotheses'] if p['pattern_id']==pattern_id]
    if len(selected)!=1:raise ValueError('select exactly one existing operator pattern ID')
    selected=selected[0];context_result=inspect_context(package,context)
    packet=assemble(package,links,proposal,draft,context_result['reference_year'])
    if context_result['question']!=packet['question']:raise ValueError('context and answer/design question text must match exactly')
    contexts={(r['evidence']['reference']['paper_id'],r['evidence']['reference']['observation_index']):r for r in context_result['assessments']}
    packet_routes={r['reference_sha256']:r for r in packet['evidence_routes']}
    rows=[];prompts=[]
    for route in selected['evidence']:
        node=route['evidence'];ref=node['reference'];key=payload_sha256(ref)
        assessment=contexts.get((ref['paper_id'],ref['observation_index']))
        uses=packet_routes.get(key,{})
        answer_uses=uses.get('answer_uses',[]);design_uses=uses.get('design_uses',[])
        counter_uses=[]
        for r in context_result['assessments']:
            if any(payload_sha256(c['evidence']['reference'])==key for c in r['counterevidence']):
                counter_uses.append(r['evidence']['reference'])
        codes=[]
        if assessment is None:codes.append('NO_ENCLOSING_OBSERVATION_CONTEXT_ASSESSMENT')
        else:
            if assessment['decision']=='defer':codes.append('CONTEXT_DECISION_DEFERRED')
            if assessment['missing_fields']:codes.append('CONTEXT_COMPARISON_OR_UNCERTAINTY_MISSING')
            if assessment['decision']=='exclude' and design_uses:codes.append('EXCLUDED_OBSERVATION_HAS_SHARED_DESIGN_REFERENCE')
        if not answer_uses and not design_uses:codes.append('PATTERN_REFERENCE_NOT_USED_IN_ANSWER_OR_DESIGN')
        if 'challenge' in route['declared_roles'] and not any(u['role']=='challenge' for u in answer_uses) and not any(u['role']=='counterargument' for u in design_uses):
            codes.append('NO_DECLARED_CHALLENGE_USE_FOR_PATTERN_CHALLENGE')
        timing='AFTER_REFERENCE_YEAR' if node['publication_year']>context_result['reference_year'] else 'SAME_YEAR_ORDER_UNRESOLVED' if node['publication_year']==context_result['reference_year'] else 'BEFORE_REFERENCE_YEAR'
        if timing!='BEFORE_REFERENCE_YEAR':codes.append(timing)
        row=dict(evidence=node,pattern_roles=route['declared_roles'],publication_scope=timing,
            context_assessment=assessment,context_match_basis='ENCLOSING_OBSERVATION_ONLY' if assessment else 'NONE',
            declared_context_counterevidence_for=counter_uses,answer_uses=answer_uses,design_uses=design_uses,
            unused_link_uses=uses.get('unreferenced_link_uses',[]),review_prompts=codes)
        rows.append(row)
        prompts.extend(dict(reference=ref,code=code) for code in codes)
    bindings=dict(pattern_form_sha256=patterns_result['form_sha256'],context_form_sha256=context_result['form_sha256'],packet_input_sha256=packet['packet_input_sha256'],pattern_id=pattern_id)
    return dict(status='PATTERN_TRANSFER_REQUIRES_MANUAL_REVIEW',**bindings,report_input_sha256=payload_sha256(bindings),
        question=packet['question'],target_context=context_result['target_context'],selected_pattern=selected,
        declared_pattern_operator_id=patterns_result['operator_id'],
        selected_pattern_review_prompts=selected['review_prompts'],context_review=context_result,answer_design_review=packet,
        evidence_routes=rows,trace_review_prompts=prompts,source_reread=False,llm_used=False,
        semantic_validation='NOT_PERFORMED',boundary=BOUNDARY)


def render(package,patterns,context,links,proposal,draft,pattern_id):
    result=inspect(package,patterns,context,links,proposal,draft,pattern_id);pattern=result['selected_pattern']
    lines=['Operator pattern-to-context trace review', 'Status: '+result['status'],
        'Selected operator hypothesis: '+display(pattern['pattern_id'])+' | '+display(pattern['operator_hypothesis']),
        'Declared pattern operator (not authenticated): '+display(result['declared_pattern_operator_id']),
        'Report input sha256: '+result['report_input_sha256'],
        'Scope: '+display(pattern['scope_note']),'Question: '+display(result['question']),
        'Target context: '+display(result['target_context']),
        'Pattern review prompts: '+(', '.join(result['selected_pattern_review_prompts']) or 'none detected; not validation')]
    for field in ('alternative_explanation','falsification_check','uncertainty'):
        lines.append('Pattern '+field+': '+('NOT_SUPPLIED' if pattern[field] is None else display(pattern[field])))
    for route in result['evidence_routes']:
        lines.append('Pattern declared roles: '+', '.join(route['pattern_roles'])+' | '+route['publication_scope'])
        _render_endpoint(lines,route['evidence']);obs=route['evidence']['observation']
        lines.append('  Observation topic: '+display(obs['topic'])+'; quote: '+display(obs['evidence_quote']))
        lines.append('  Trace prompts: '+(', '.join(route['review_prompts']) or 'none detected; not validation'))
        assessment=route['context_assessment']
        if assessment:
            lines.append('  Enclosing-observation context decision: '+assessment['decision']+' (not component semantic approval)')
            for key in ('context_comparison','remaining_uncertainty'):
                lines.append('  '+key+': '+('NOT_SUPPLIED' if assessment[key] is None else display(assessment[key])))
        for ref in route['declared_context_counterevidence_for']:lines.append('  Declared context counterevidence for '+display(ref['paper_id'])+'/'+str(ref['observation_index']))
        for use in route['answer_uses']:lines.append('  Shared answer reference: '+display(use['claim_id'])+' role='+use['role'])
        for use in route['design_uses']:lines.append('  Shared design reference: '+display(use['step_id'])+' link='+display(use['link_id'])+' role='+use['role']+' relation='+use['relation']+' endpoint='+use['direction'])
        for use in route['unused_link_uses']:lines.append('  Unused link: '+display(use['link_id'])+' endpoint='+use['direction'])
    lines.append(BOUNDARY)
    lines.append('Full supplied context review (includes counterevidence outside the selected pattern):')
    lines.append(render_context(result['context_review']).rstrip('\n'))
    lines.append('Full supplied answer/design review (includes evidence outside the selected pattern):')
    lines.append(render_packet(package,links,proposal,draft,context['reference_year']).rstrip('\n'))
    return '\n'.join(lines)+'\n'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('package','patterns','context','links','proposal','draft'):p.add_argument(name,type=Path)
    p.add_argument('--pattern-id',required=True);p.add_argument('--format',choices=('json','text'),default='json');a=p.parse_args()
    try:
        inputs=[load(getattr(a,n)) for n in ('package','patterns','context','links','proposal','draft')]+[a.pattern_id]
        output=render(*inputs) if a.format=='text' else json.dumps(inspect(*inputs),indent=2)+'\n'
    except (ValueError,OSError,KeyError,TypeError,AttributeError) as exc:p.exit(1,str(exc)+'\n')
    sys.stdout.buffer.write(output.encode('utf-8'))


if __name__=='__main__':main()
