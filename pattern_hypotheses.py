"""Review explicitly proposed cross-publication method patterns, never discover them."""
import argparse
import json
import sys
from pathlib import Path
from persona import payload_sha256
from reasoning_links import _sources,_endpoint
from design_scenario import _text
from answer_draft import _render_endpoint
from review_package import display
from strict_json import load

OPTIONAL=('alternative_explanation','falsification_check','uncertainty')
BOUNDARY=('Every pattern is an operator hypothesis, not a discovered semantic regularity or an individual researcher trait. '
    'Supporting/challenging uses are operator declarations, separate from source stance and claim labels. Distinct papers, hashes and years do not '
    'establish independent publications, replication, causal reasoning, historical influence or author ownership. Missing counterevidence is not absence '
    'of counterevidence. Alternatives and falsification criteria are operator text, not validated tests. No meaning judgment, LLM, source reread, '
    'external call, canonical update or automatic application to a new study is performed. Stored quotes and private annotations may be displayed.')


def template(package,operator_id):
    checked,papers=_sources(package);_text(operator_id,'operator_id')
    for paper in papers.values():
        if type(paper['year']) is not int or not 1<=paper['year']<=9999:raise ValueError('all publication years must be integers from 1 to 9999')
    return dict(persona_sha256=payload_sha256(checked['persona']),knowledge_papers_sha256=payload_sha256(checked['knowledge']['papers']),
                operator_id=operator_id,hypotheses=[])


def inspect(package,form):
    if isinstance(form,dict) and form.get('schema')=='persona.reviewed-pattern-proposals.v1':
        from pattern_proposals import inspect_reviewed
        return inspect_reviewed(package,form)
    if not isinstance(form,dict) or set(form)!={'persona_sha256','knowledge_papers_sha256','operator_id','hypotheses'}:
        raise ValueError('pattern form has missing or unsupported fields')
    checked,papers=_sources(package);expected=template(checked,form['operator_id'])
    if any(form[k]!=expected[k] for k in ('persona_sha256','knowledge_papers_sha256')):raise ValueError('pattern form is stale for this package')
    for paper in papers.values():
        if type(paper['year']) is not int or not 1<=paper['year']<=9999:raise ValueError('all publication years must be integers from 1 to 9999')
    if not isinstance(form['hypotheses'],list):raise ValueError('hypotheses must be an array')
    ids=set();results=[];used_observations=set()
    for hypothesis in form['hypotheses']:
        fields={'pattern_id','operator_hypothesis','scope_note','support_refs','challenge_refs'}|set(OPTIONAL)
        if not isinstance(hypothesis,dict) or set(hypothesis)!=fields:raise ValueError('pattern hypothesis has missing or unsupported fields')
        for key in ('pattern_id','operator_hypothesis','scope_note'):_text(hypothesis[key],key)
        if hypothesis['pattern_id'] in ids:raise ValueError('duplicate pattern ID')
        ids.add(hypothesis['pattern_id'])
        for key in OPTIONAL:
            if hypothesis[key] is not None:_text(hypothesis[key],key)
        routes={}
        for field,role in (('support_refs','support'),('challenge_refs','challenge')):
            refs=hypothesis[field]
            if not isinstance(refs,list):raise ValueError('support/challenge references must be arrays')
            seen=set()
            for ref in refs:
                key=payload_sha256(ref)
                if key in seen:raise ValueError('duplicate reference within a declared role')
                seen.add(key);node=_endpoint(ref,papers)
                used_observations.add((ref['paper_id'],ref['observation_index']))
                if key not in routes:routes[key]=dict(evidence=node,declared_roles=[])
                routes[key]['declared_roles'].append(role)
        if not hypothesis['support_refs']:raise ValueError('a pattern hypothesis requires at least one explicit supporting reference')
        evidence=sorted(routes.values(),key=lambda r:(r['evidence']['publication_year'],r['evidence']['reference']['paper_id'],r['evidence']['reference']['observation_index'],r['evidence']['reference']['dimension'] or ''))
        support_papers={r['evidence']['reference']['paper_id'] for r in evidence if 'support' in r['declared_roles']}
        hashes={}
        for route in evidence:
            node=route['evidence'];hashes.setdefault(node['source_sha256'],set()).add(node['reference']['paper_id'])
        gaps=[key.upper()+'_NOT_SUPPLIED' for key in OPTIONAL if hypothesis[key] is None]
        if len(support_papers)<2:gaps.append('SUPPORT_FROM_FEWER_THAN_TWO_PAPER_IDS')
        if not hypothesis['challenge_refs']:gaps.append('NO_CHALLENGE_REFERENCES_SUPPLIED')
        if any(len(r['declared_roles'])>1 for r in evidence):gaps.append('SAME_REFERENCE_DECLARED_IN_BOTH_ROLES')
        if any(len(p)>1 for p in hashes.values()):gaps.append('MULTIPLE_PAPER_IDS_SHARE_SOURCE_HASH')
        results.append(dict(pattern_id=hypothesis['pattern_id'],operator_hypothesis=hypothesis['operator_hypothesis'],
            scope_note=hypothesis['scope_note'],claim_type='operator_interpretation',
            **{k:hypothesis[k] for k in OPTIONAL},evidence=evidence,review_prompts=gaps,
            distinct_support_paper_id_count=len(support_papers),distinct_source_hash_count=len(hashes),
            source_hash_groups=[dict(source_sha256=digest,paper_ids=sorted(group)) for digest,group in sorted(hashes.items())],
            publication_years=sorted({r['evidence']['publication_year'] for r in evidence}),
            status='OPERATOR_PATTERN_HYPOTHESIS_REQUIRES_REVIEW'))
    unused=[dict(paper_id=p['paper_id'],observation_index=i,dimension=None) for p in papers.values() for i in range(len(p['observations'])) if (p['paper_id'],i) not in used_observations]
    return dict(status='PATTERN_HYPOTHESES_REQUIRE_REVIEW' if results else 'NO_PATTERN_HYPOTHESES',
        **{k:expected[k] for k in ('persona_sha256','knowledge_papers_sha256','operator_id')},form_sha256=payload_sha256(form),
        hypotheses=results,unreferenced_observations=unused,unreferenced_scope='OBSERVATION_LEVEL_NOT_UNUSED_COMPONENT_INVENTORY',
        semantic_validation='NOT_PERFORMED',llm_used=False,source_reread=False,automatic_pattern_discovery=False,boundary=BOUNDARY)


def render(result, *, imported_proposal=False):
    lines=['Imported proposal evidence comparison' if imported_proposal else 'Operator method-pattern hypotheses',
        'Status: '+result['status'],
        ('Reviewing operator (not original proposal author; not authenticated): ' if imported_proposal else
         'Declared operator (not authenticated): ')+display(result['operator_id'])]
    if 'proposal_review' in result:
        lines.insert(1,'Origin: operator-reviewed imported proposals. No model call during this inspection; historical model use is declared, not authenticated.')
    for pattern in result['hypotheses']:
        lines.append('Pattern '+display(pattern['pattern_id'])+(' [imported_proposal]: ' if imported_proposal else
            ' [operator_interpretation]: ')+display(pattern['operator_hypothesis']))
        if 'proposal_origin' in pattern:
            origin=pattern['proposal_origin']
            lines.append('  Origin: operator-reviewed imported proposal '+display(origin['candidate_id'])+
                '; bundle='+origin['proposal_bundle_sha256']+'; review='+origin['review_sha256'])
        lines.append('  Declared scope: '+display(pattern['scope_note']))
        for key in OPTIONAL:lines.append('  '+key+': '+('NOT_SUPPLIED' if pattern[key] is None else display(pattern[key])))
        lines.append('  Review prompts: '+(', '.join(pattern['review_prompts']) or 'none detected; not validation'))
        lines.append('  Supporting paper IDs: '+str(pattern['distinct_support_paper_id_count'])+'; all source hashes: '+str(pattern['distinct_source_hash_count'])+' (neither means independent support)')
        for route in pattern['evidence']:
            lines.append('  Declared use: '+', '.join(route['declared_roles']))
            for use in route.get('evidence_uses', []):
                lines.append('    '+use['role']+' rationale ['+('imported_proposal' if imported_proposal else 'operator_interpretation')+']: '+display(use['rationale']))
                lines.append('    Context boundary: '+('NOT_SUPPLIED' if use['context_boundary'] is None else display(use['context_boundary'])))
            node=route['evidence'];_render_endpoint(lines,node)
            obs=node['observation'];lines.append('    Observation topic: '+display(obs['topic']))
            lines.append('    Observation stored quote: '+display(obs['evidence_quote'])+'; recorded check: '+display(obs['evidence_verification']))
    lines.append('Unreferenced observations (not proof of irrelevance):')
    for ref in result['unreferenced_observations']:lines.append('  '+display(ref['paper_id'])+' / '+str(ref['observation_index']))
    lines.append(('This original imported proposal is not an operator-authored or accepted hypothesis. '
        'References and checks are historical records, not semantic validation. No model call occurs in this inspection.'
        if imported_proposal else BOUNDARY))
    if 'proposal_review' in result:
        from pattern_proposals import render_review
        lines.append('Full imported proposal/review history, including rejected candidates:')
        lines.append(render_review(result['proposal_review']).rstrip('\n'))
    return '\n'.join(lines)+'\n'


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('package',type=Path);p.add_argument('form',type=Path,nargs='?')
    p.add_argument('--template',action='store_true');p.add_argument('--operator-id');p.add_argument('--format',choices=('json','text'),default='json');a=p.parse_args()
    try:
        package=load(a.package)
        if a.template:
            if a.form is not None or a.format!='json':raise ValueError('template requires JSON and no form')
            output=json.dumps(template(package,a.operator_id),indent=2)+'\n'
        else:
            if a.form is None or a.operator_id is not None:raise ValueError('review requires a form without operator override')
            result=inspect(package,load(a.form));output=render(result) if a.format=='text' else json.dumps(result,indent=2)+'\n'
    except (ValueError,OSError,KeyError,TypeError,AttributeError) as exc:p.exit(1,str(exc)+'\n')
    sys.stdout.buffer.write(output.encode('utf-8'))


if __name__=='__main__':main()
