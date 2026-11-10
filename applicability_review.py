"""Record operator comparisons of source conditions with a new research context."""
from exclusive_output import add_output_argument, emit, preflight
import argparse
import json
import sys
from pathlib import Path
from persona import payload_sha256
from reasoning_links import _sources,_endpoint
from design_scenario import _text
from answer_draft import _render_endpoint as _render_base_endpoint
from review_package import display
from strict_json import load
from reasoning_cards import DIMENSIONS

BOUNDARY=('Consider/exclude/defer are unauthenticated operator judgments, not recommended methods, source author claims or scientific validation. '
    'The tool does not compare meanings or infer applicability. Exact case-insensitive observation-topic selection is not semantic relevance; '
    'all matched observations remain visible, including excluded and deferred records. Counterevidence roles are operator supplied and need not agree '
    'with original source stance. Publication years do not prove historical availability or intellectual influence. No new claim, citation, plan, '
    'LLM call, source reread, external transmission or canonical update is performed. Quotes and private context may be present.')


def _inventory(package,topic,year):
    checked,papers=_sources(package)
    _text(topic,'topic')
    if type(year) is not int or not 1<=year<=9999:raise ValueError('reference year must be an integer from 1 to 9999')
    refs=[];omitted=0
    for paper in papers.values():
        if type(paper['year']) is not int or not 1<=paper['year']<=9999:raise ValueError('all publication years must be integers from 1 to 9999')
        for i,obs in enumerate(paper['observations']):
            if obs['topic'].casefold()==topic.casefold():refs.append(dict(paper_id=paper['paper_id'],observation_index=i,dimension=None))
            else:omitted+=1
    refs.sort(key=lambda r:(papers[r['paper_id']]['year'],r['paper_id'],r['observation_index']))
    return checked,papers,refs,omitted


def template(package,question,target_context,topic,reference_year,operator_id):
    checked,papers,refs,_=_inventory(package,topic,reference_year)
    for field,value in [('question',question),('target_context',target_context),('operator_id',operator_id)]:_text(value,field)
    context=dict(question=question,target_context=target_context,topic=topic,reference_year=reference_year,operator_id=operator_id)
    return dict(context_sha256=payload_sha256(context),persona_sha256=payload_sha256(checked['persona']),knowledge_papers_sha256=payload_sha256(checked['knowledge']['papers']),
        question=question,target_context=target_context,topic=topic,reference_year=reference_year,operator_id=operator_id,
        assessments=[dict(reference=ref,decision='defer',context_comparison=None,remaining_uncertainty=None,counterevidence_refs=[]) for ref in refs])


def inspect(package,form):
    fields={'context_sha256','persona_sha256','knowledge_papers_sha256','question','target_context','topic','reference_year','operator_id','assessments'}
    if not isinstance(form,dict) or set(form)!=fields:raise ValueError('applicability form has missing or unsupported fields')
    expected=template(package,*[form[k] for k in ('question','target_context','topic','reference_year','operator_id')])
    for k in ('context_sha256','persona_sha256','knowledge_papers_sha256'):
        if form[k]!=expected[k]:raise ValueError('applicability form is stale for this package or context')
    checked,papers,refs,omitted=_inventory(package,form['topic'],form['reference_year'])
    if not isinstance(form['assessments'],list):raise ValueError('assessments must be an array')
    expected_refs={payload_sha256(r) for r in refs};seen=set();rows=[]
    timing=lambda year:'AFTER_REFERENCE_YEAR' if year>form['reference_year'] else 'SAME_YEAR_ORDER_UNRESOLVED' if year==form['reference_year'] else 'BEFORE_REFERENCE_YEAR'
    for row in form['assessments']:
        if not isinstance(row,dict) or set(row)!={'reference','decision','context_comparison','remaining_uncertainty','counterevidence_refs'}:
            raise ValueError('assessment has missing or unsupported fields')
        key=payload_sha256(row['reference'])
        if key not in expected_refs or key in seen:raise ValueError('each topic-selected observation must appear exactly once')
        seen.add(key);node=_endpoint(row['reference'],papers)
        if row['decision'] not in ('consider','exclude','defer'):raise ValueError('decision must be consider, exclude or defer')
        for name in ('context_comparison','remaining_uncertainty'):
            if row[name] is not None:_text(row[name],name)
            elif row['decision']!='defer':raise ValueError('consider/exclude require explicit context comparison and remaining uncertainty')
        if not isinstance(row['counterevidence_refs'],list):raise ValueError('counterevidence refs must be an array')
        counters=[];counterkeys=set()
        for ref in row['counterevidence_refs']:
            ckey=payload_sha256(ref)
            if ckey in counterkeys or ckey==key:raise ValueError('duplicate or identical self counterevidence reference')
            counterkeys.add(ckey);counter=_endpoint(ref,papers)
            counters.append(dict(evidence=counter,publication_scope=timing(counter['publication_year']),role_origin='OPERATOR_SUPPLIED_NOT_SOURCE_STANCE'))
        ref=row['reference'];components=papers[ref['paper_id']]['observations'][ref['observation_index']].get('reasoning',{})
        rows.append(dict(evidence=node,publication_scope=timing(node['publication_year']),decision=row['decision'],
            reasoning_component_records=[_endpoint(dict(ref,dimension=d),papers) for d in DIMENSIONS if d in components],
            missing_reasoning_dimensions=[d for d in DIMENSIONS if d not in components],
            context_comparison=row['context_comparison'],remaining_uncertainty=row['remaining_uncertainty'],counterevidence=counters,
            missing_fields=[name for name in ('context_comparison','remaining_uncertainty') if row[name] is None],
            counterevidence_status='DECLARED_REFERENCES_NOT_VALIDATED' if counters else 'NO_COUNTEREVIDENCE_REFERENCES_SUPPLIED'))
    if seen!=expected_refs:raise ValueError('all topic-selected observations must remain present, including excluded/deferred')
    rows.sort(key=lambda r:(r['evidence']['publication_year'],r['evidence']['reference']['paper_id'],r['evidence']['reference']['observation_index']))
    return dict(status='APPLICABILITY_REQUIRES_REVIEW' if rows else 'NO_TOPIC_MATCHED_OBSERVATIONS',
        **{k:form[k] for k in fields-{'assessments'}},form_sha256=payload_sha256(form),assessments=rows,
        omitted_other_topic_observation_count=omitted,decision_counts={d:sum(r['decision']==d for r in rows) for d in ('consider','exclude','defer')},
        llm_used=False,semantic_validation='NOT_PERFORMED',source_reread=False,boundary=BOUNDARY)


def _render_endpoint(lines,node):
    _render_base_endpoint(lines,node)
    lines.append('    Observation topic: '+display(node['observation']['topic']))


def render(result):
    lines=['Source-to-context applicability review', 'Status: '+result['status'],
        'Question: '+display(result['question']),'Target context (operator supplied): '+display(result['target_context']),
        'Topic: '+display(result['topic'])+'; reference year: '+str(result['reference_year']),
        'Declared operator (not authenticated): '+display(result['operator_id']),
        'Omitted other-topic observations: '+str(result['omitted_other_topic_observation_count'])]
    for row in result['assessments']:
        lines.append('Operator decision: '+row['decision']+' | '+row['publication_scope'])
        _render_endpoint(lines,row['evidence'])
        lines.append('  Missing supplied reasoning dimensions: '+(', '.join(row['missing_reasoning_dimensions']) or 'none (not a completeness or validity judgment)'))
        for component in row['reasoning_component_records']:
            lines.append('  Supplied reasoning component:');_render_endpoint(lines,component)
        lines.append('  Context comparison: '+('NOT_SUPPLIED' if row['context_comparison'] is None else display(row['context_comparison'])))
        lines.append('  Remaining uncertainty: '+('NOT_SUPPLIED' if row['remaining_uncertainty'] is None else display(row['remaining_uncertainty'])))
        lines.append('  Counterevidence: '+row['counterevidence_status'])
        for counter in row['counterevidence']:
            lines.append('  Operator-selected counterevidence | '+counter['publication_scope']);_render_endpoint(lines,counter['evidence'])
    lines.append(BOUNDARY)
    return '\n'.join(lines)+'\n'


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('package',type=Path);p.add_argument('form',type=Path,nargs='?')
    p.add_argument('--template',action='store_true');p.add_argument('--question');p.add_argument('--target-context');p.add_argument('--topic');p.add_argument('--reference-year',type=int);p.add_argument('--operator-id');p.add_argument('--format',choices=('json','text'),default='json')
    add_output_argument(p); a=p.parse_args()
    preflight(p, getattr(a, 'output', None))
    try:
        package=load(a.package)
        if a.template:
            if a.form is not None or a.format!='json':raise ValueError('template requires JSON and no form')
            output=json.dumps(template(package,a.question,a.target_context,a.topic,a.reference_year,a.operator_id),indent=2)+'\n'
        else:
            if a.form is None or any(getattr(a,k) is not None for k in ('question','target_context','topic','reference_year','operator_id')):raise ValueError('review requires a form and no context overrides')
            result=inspect(package,load(a.form));output=render(result) if a.format=='text' else json.dumps(result,indent=2)+'\n'
    except (ValueError,OSError,KeyError,TypeError,AttributeError) as exc:p.exit(1,str(exc)+'\n')
    emit(p, output.encode('utf-8'), getattr(a, 'output', None))


if __name__=='__main__':main()
