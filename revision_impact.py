"""Trace old answer/design evidence uses across two bound packages without rebinding."""
from exclusive_output import add_output_argument, emit, preflight
import argparse
import json
import sys
from pathlib import Path
from persona import payload_sha256
from reasoning_links import _sources,_endpoint
from review_journey import assemble
from answer_draft import _render_endpoint
from review_package import display
from strict_json import load

BOUNDARY=('Index-based correspondence only: the same paper ID, observation index and dimension may refer to a different curated record after reordering. '
    'Unchanged content is not semantic validation or permission to reuse stale bindings. Only references used by the supplied old answer/links are compared, '
    'not all changed evidence or missing counterevidence. Old artifacts are validated solely against the old package; no new answer, link, design, attribution, '
    'human decision or scientific claim is generated. No source bytes are reread, LLM/API called or artifact rebound. Quotes and private fields may be displayed.')


def inspect(previous,current,links,proposal,draft,reference_year):
    old,old_papers=_sources(previous);new,new_papers=_sources(current)
    if old['persona']['author_id']!=new['persona']['author_id']:
        raise ValueError('impact comparison requires the same scholarly identity')
    for paper in list(old_papers.values())+list(new_papers.values()):
        if type(paper['year']) is not int or not 1<=paper['year']<=9999:
            raise ValueError('all publication years must be integers from 1 to 9999')
    prior=assemble(old,links,proposal,draft,reference_year)
    bindings=lambda p:dict(persona_sha256=payload_sha256(p['persona']),knowledge_papers_sha256=payload_sha256(p['knowledge']['papers']))
    before_bindings,after_bindings=bindings(old),bindings(new)
    rows=[];affected_claims=set();affected_steps=set()
    for route in prior['evidence_routes']:
        before=route['evidence'];ref=before['reference'];paper=new_papers.get(ref['paper_id'])
        after=None
        if paper is None:reason='PAPER_NOT_PRESENT'
        elif ref['observation_index']>=len(paper['observations']):reason='OBSERVATION_INDEX_NOT_PRESENT'
        elif ref['dimension'] is not None and ref['dimension'] not in paper['observations'][ref['observation_index']].get('reasoning',{}):reason='COMPONENT_NOT_PRESENT'
        else:
            reason=None;after=_endpoint(ref,new_papers)
        changed=[] if after is None else [k for k in before if payload_sha256(before[k])!=payload_sha256(after[k])]
        status='MISSING_AT_REFERENCE' if after is None else 'CHANGED_AT_SAME_REFERENCE' if changed else 'UNCHANGED_AT_SAME_REFERENCE'
        if status!='UNCHANGED_AT_SAME_REFERENCE':
            affected_claims.update(u['claim_id'] for u in route['answer_uses'])
            affected_steps.update(u['step_id'] for u in route['design_uses'])
        rows.append(dict(reference=ref,status=status,missing_reason=reason,changed_endpoint_fields=changed,
            previous_evidence=before,current_evidence=after,
            previous_publication_scope=route['publication_scope'],
            current_publication_scope=None if after is None else ('AFTER_REFERENCE_YEAR' if after['publication_year']>reference_year else 'SAME_YEAR_ORDER_UNRESOLVED' if after['publication_year']==reference_year else 'BEFORE_REFERENCE_YEAR'),
            answer_uses=route['answer_uses'],design_uses=route['design_uses'],unreferenced_link_uses=route['unreferenced_link_uses']))
    result=dict(status='REVISION_IMPACT_REQUIRES_MANUAL_REVIEW',question=prior['question'],reference_year=reference_year,
        previous_package_bindings=before_bindings,current_package_bindings=after_bindings,
        old_artifacts_stale_for_current_package=before_bindings!=after_bindings,
        previous_packet_input_sha256=prior['packet_input_sha256'],
        compared_reference_count=len(rows),changed_reference_count=sum(r['status']=='CHANGED_AT_SAME_REFERENCE' for r in rows),
        missing_reference_count=sum(r['status']=='MISSING_AT_REFERENCE' for r in rows),
        unchanged_reference_count=sum(r['status']=='UNCHANGED_AT_SAME_REFERENCE' for r in rows),
        affected_answer_claim_ids=sorted(affected_claims),affected_design_step_ids=sorted(affected_steps),
        references=rows,previous_review_prompts=prior['review_prompts'],
        all_artifacts_require_binding_review=before_bindings!=after_bindings,
        source_reread=False,llm_used=False,automatic_rebinding=False,semantic_validation='NOT_PERFORMED',boundary=BOUNDARY)
    if 'proposal_review' in prior['answer']:
        from answer_proposals import MAX_OUTPUT_BYTES
        result.update(previous_full_package_sha256=payload_sha256(old),current_full_package_sha256=payload_sha256(new),
            old_artifacts_stale_for_current_package=payload_sha256(old)!=payload_sha256(new),
            all_artifacts_require_binding_review=payload_sha256(old)!=payload_sha256(new),
            previous_answer_origin=prior['answer']['origin'],
            previous_answer_proposal_review=prior['answer']['proposal_review'],
            previous_answer_history_scope='PREVIOUS_DRAFT_ONLY_NOT_REBOUND_TO_CURRENT_PACKAGE',
            historical_model_use='DECLARED_NOT_AUTHENTICATED',execution_scope='CURRENT_IMPACT_INSPECTION_ONLY')
        if len(json.dumps(result,ensure_ascii=True,allow_nan=False).encode('utf-8'))>MAX_OUTPUT_BYTES:
            raise ValueError('imported-answer revision impact exceeds 16 MiB')
    return result


def render(result):
    lines=['Evidence revision impact (manual review required)',
        'Question: '+display(result['question']),
        'Old artifacts stale for current package: '+str(result['old_artifacts_stale_for_current_package']),
        'Compared references: '+str(result['compared_reference_count'])+'; changed: '+str(result['changed_reference_count'])+'; missing: '+str(result['missing_reference_count']),
        'Affected old answer claims: '+(', '.join(display(x) for x in result['affected_answer_claim_ids']) or 'none detected in compared references'),
        'Affected old design steps: '+(', '.join(display(x) for x in result['affected_design_step_ids']) or 'none detected in compared references')]
    def endpoint(node):
        _render_endpoint(lines,node)
        obs=node['observation']
        lines.append('    Observation topic: '+display(obs['topic']))
        lines.append('    Observation stored quote: '+display(obs['evidence_quote']))
        lines.append('    Observation recorded check (not rechecked): '+display(obs['evidence_verification']))
    for row in result['references']:
        lines.append(row['status']+' | changed fields: '+(', '.join(row['changed_endpoint_fields']) or 'none'))
        lines.append('  Previous evidence:');endpoint(row['previous_evidence'])
        if row['current_evidence'] is None:lines.append('  Current: '+row['missing_reason'])
        else:
            lines.append('  Current evidence:');endpoint(row['current_evidence'])
        lines.append('  Publication scope: '+str(row['previous_publication_scope'])+' -> '+str(row['current_publication_scope']))
        for use in row['answer_uses']:lines.append('  Old answer '+display(use['claim_id'])+' citation role='+use['role'])
        for use in row['design_uses']:lines.append('  Old design '+display(use['step_id'])+' link='+display(use['link_id'])+' use='+use['role']+' relation='+use['relation']+' endpoint='+use['direction'])
        for use in row['unreferenced_link_uses']:lines.append('  Unused old link '+display(use['link_id'])+' relation='+use['relation']+' endpoint='+use['direction'])
    if 'previous_answer_proposal_review' in result:
        lines.append('Previous full package sha256: '+result['previous_full_package_sha256'])
        lines.append('Current full package sha256: '+result['current_full_package_sha256'])
        from answer_proposals import render_review, MAX_OUTPUT_BYTES
        lines.append('Previous answer-candidate history only; not rebound to the current package:')
        lines.append(render_review(result['previous_answer_proposal_review']).rstrip('\n'))
    lines.append(BOUNDARY)
    output='\n'.join(lines)+'\n'
    if 'previous_answer_proposal_review' in result and len(output.encode('utf-8'))>MAX_OUTPUT_BYTES:
        raise ValueError('imported-answer revision impact text exceeds 16 MiB')
    return output


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('previous','current','links','proposal','draft'):p.add_argument(name,type=Path)
    p.add_argument('--reference-year',type=int,required=True);p.add_argument('--format',choices=('json','text'),default='json')
    add_output_argument(p); a=p.parse_args()
    preflight(p, getattr(a, 'output', None))
    try:
        result=inspect(*[load(getattr(a,n)) for n in ('previous','current','links','proposal','draft')],a.reference_year)
        output=render(result) if a.format=='text' else json.dumps(result,indent=2)+'\n'
    except (ValueError,OSError,KeyError,TypeError,AttributeError) as exc:p.exit(1,str(exc)+'\n')
    emit(p, output.encode('utf-8'), getattr(a, 'output', None))


if __name__=='__main__':main()
