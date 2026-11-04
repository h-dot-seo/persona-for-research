"""Inspect declared publication relationships without inferring influence or independence."""
import argparse
import copy
import json
import sys
from pathlib import Path

from reasoning_links import _sources, _endpoint
from design_scenario import _text
from persona import payload_sha256
from answer_draft import _render_endpoint
from review_package import display
from strict_json import loads

TYPES = ('review_summary_of', 'method_extension_of', 'reanalysis_of', 'shares_material_with', 'version_of', 'challenges')
SYMMETRIC = {'shares_material_with'}
MAX_RELATIONS = 128
MAX_BASIS_REFS = 32
FIELDS = {'relation_id', 'from_paper_id', 'to_paper_id', 'relation_type', 'rationale', 'basis_refs', 'uncertainty'}
BOUNDARY = ('These are operator-declared publication relationships, not verified citations, '
    'researcher speech, private beliefs, intellectual influence or a proven change of mind. '
    'Basis references and stored quotes do not establish the declared relationship. A review '
    'summary, version or reanalysis must not be counted as independent corroboration merely '
    'because its paper ID, source hash or publication year differs. Method extension and '
    'challenge labels do not establish data independence. Missing relationships mean not '
    'declared, not independent. No transitive relationship, dependency group, ranking, approval '
    'or automatic evidence exclusion is inferred. Publication years do not date research '
    'decisions; within-year order is unresolved. Recorded source/quote checks and identities '
    'are not authenticated or repeated. No model, network call, source reread or canonical '
    'update is performed. Quotes and operator text may be private.')


def _checked(value):
    package,papers=_sources(value)
    for paper in papers.values():
        if type(paper['year']) is not int or not 1<=paper['year']<=9999:
            raise ValueError('all publication years must be integers from 1 to 9999')
    return package,papers


def template(value,operator_id):
    package,_=_checked(value);_text(operator_id,'operator_id',128)
    return dict(persona_sha256=payload_sha256(package['persona']),
        knowledge_papers_sha256=payload_sha256(package['knowledge']['papers']),operator_id=operator_id,relations=[])


def _publication(paper):
    return dict(paper_id=paper['paper_id'],publication_year=paper['year'],source_kind=paper['kind'],
        source_sha256=paper['source_sha256'],source_locator=paper['locator'],
        recorded_source_check=paper.get('source_verification','NOT_PERFORMED'),
        attribution='coauthored work; individual ownership not established')


def inspect(value,form):
    if not isinstance(form,dict) or set(form)!={'persona_sha256','knowledge_papers_sha256','operator_id','relations'}:
        raise ValueError('publication relation form has missing or unsupported fields')
    package,papers=_checked(value);expected=template(package,form['operator_id'])
    if any(form[key]!=expected[key] for key in ('persona_sha256','knowledge_papers_sha256')):
        raise ValueError('publication relationships are bound to a different package')
    if not isinstance(form['relations'],list) or len(form['relations'])>MAX_RELATIONS:
        raise ValueError('publication relationships must be an array of at most 128 entries')
    ids=set();edges=set();rows=[]
    for relation in form['relations']:
        if not isinstance(relation,dict) or set(relation)!=FIELDS:
            raise ValueError('publication relationship has missing or unsupported fields')
        for key in ('relation_id','from_paper_id','to_paper_id'):_text(relation[key],key,128)
        _text(relation['rationale'],'rationale')
        if relation['uncertainty'] is not None:_text(relation['uncertainty'],'uncertainty')
        left,right=relation['from_paper_id'],relation['to_paper_id'];kind=relation['relation_type']
        if relation['relation_id'] in ids:raise ValueError('duplicate publication relationship ID')
        ids.add(relation['relation_id'])
        if left not in papers or right not in papers or left==right:
            raise ValueError('publication relationship requires two distinct known papers')
        if kind not in TYPES:raise ValueError('unsupported publication relationship type')
        if kind=='review_summary_of' and papers[left]['kind']!='review':
            raise ValueError('review_summary_of must start from a source labeled review')
        pair=tuple(sorted((left,right))) if kind in SYMMETRIC else (left,right)
        edge=(kind,*pair)
        if edge in edges:raise ValueError('duplicate declared publication relationship')
        edges.add(edge)
        refs=relation['basis_refs']
        if not isinstance(refs,list) or not refs or len(refs)>MAX_BASIS_REFS:
            raise ValueError('provide 1 to 32 explicit relationship basis references')
        seen=set();basis=[];gaps=[]
        for ref in refs:
            node=_endpoint(ref,papers);digest=payload_sha256(ref)
            if node['reference']['paper_id'] not in (left,right):
                raise ValueError('relationship basis references must belong to one of its two papers')
            if digest in seen:raise ValueError('duplicate relationship basis reference')
            seen.add(digest);basis.append(node)
            record=node['component'] or node['observation']
            if not record.get('evidence_quote'):
                gaps.append(dict(reference=copy.deepcopy(ref),code='BASIS_QUOTE_NOT_SUPPLIED'))
        basis_papers={node['reference']['paper_id'] for node in basis}
        if kind not in SYMMETRIC and left not in basis_papers:
            raise ValueError('a directed relationship needs an explicit basis from its from-paper')
        prompts=[]
        if len(basis_papers)<2:prompts.append('BASIS_NOT_SUPPLIED_FROM_BOTH_PAPERS')
        if relation['uncertainty'] is None:prompts.append('RELATIONSHIP_UNCERTAINTY_NOT_SUPPLIED')
        if gaps:prompts.append('BASIS_REFERENCES_WITHOUT_STORED_QUOTES')
        if papers[left]['source_sha256']==papers[right]['source_sha256']:prompts.append('LINKED_PAPERS_SHARE_SOURCE_HASH')
        timing=('SAME_PUBLICATION_YEAR_ORDER_UNRESOLVED' if papers[left]['year']==papers[right]['year'] else
                'FROM_PUBLICATION_PREDATES_TARGET' if papers[left]['year']<papers[right]['year'] else 'FROM_PUBLICATION_POSTDATES_TARGET')
        if timing!='FROM_PUBLICATION_POSTDATES_TARGET' and kind not in SYMMETRIC:prompts.append(timing)
        if kind=='review_summary_of':prompts.append('REVIEW_SUMMARY_IS_NOT_AUTOMATIC_INDEPENDENT_CORROBORATION')
        elif kind in ('reanalysis_of','shares_material_with','version_of'):
            prompts.append('DECLARED_MATERIAL_RELATION_REQUIRES_DEPENDENCY_REVIEW')
        else:prompts.append('METHOD_OR_CLAIM_RELATION_DOES_NOT_ESTABLISH_DATA_INDEPENDENCE')
        rows.append(dict(**copy.deepcopy(relation),claim_type='operator_interpretation',
            status='DECLARED_PUBLICATION_RELATION_REQUIRES_REVIEW',
            direction='SYMMETRIC_COMPARISON' if kind in SYMMETRIC else 'FROM_TO',
            from_publication=_publication(papers[left]),to_publication=_publication(papers[right]),
            publication_order=timing,basis_evidence=basis,basis_gaps=gaps,review_prompts=prompts,
            semantic_validation='NOT_PERFORMED'))
    return dict(status='DECLARED_PUBLICATION_RELATIONS_REQUIRE_REVIEW' if rows else 'NO_DECLARED_PUBLICATION_RELATIONS',
        **{key:expected[key] for key in ('persona_sha256','knowledge_papers_sha256','operator_id')},
        form_sha256=payload_sha256(form),operator_identity='RECORDED_NOT_AUTHENTICATED',
        paper_inventory=[_publication(paper) for paper in sorted(papers.values(),key=lambda p:(p['year'],p['paper_id']))],
        relations=rows,semantic_validation='NOT_PERFORMED',independence_assessment='NOT_PERFORMED',
        automatic_approval=False,transitive_inference=False,llm_used=False,source_reread=False,
        canonical_update_performed=False,boundary=BOUNDARY)


def for_papers(checked_relations,paper_ids,reference_year=None):
    """Project an already checked relation report; never infer edges between unlinked papers."""
    known={paper['paper_id'] for paper in checked_relations['paper_inventory']}
    if not isinstance(paper_ids,list) or any(not isinstance(pid,str) or pid not in known for pid in paper_ids):
        raise ValueError('context selection needs existing paper IDs')
    if reference_year is not None and (type(reference_year) is not int or not 1<=reference_year<=9999):
        raise ValueError('reference year must be an integer from 1 to 9999')
    selected=set(paper_ids);between=[];touching=[];outside=[];linked=set()
    for relation in checked_relations['relations']:
        endpoints={relation['from_paper_id'],relation['to_paper_id']};overlap=selected & endpoints
        if not overlap:outside.append(relation['relation_id']);continue
        linked.update(overlap)
        (between if endpoints<=selected else touching).append(copy.deepcopy(relation))
    result=dict(selected_paper_ids=[p['paper_id'] for p in checked_relations['paper_inventory'] if p['paper_id'] in selected],
        relations_between_selected_papers=between,relations_to_other_supplied_papers=touching,
        selected_papers_without_declared_relationships=sorted(selected-linked),
        outside_selection_relation_ids=outside,
        relation_form_sha256=checked_relations['form_sha256'],
        missing_relationship_meaning='NOT_DECLARED_NOT_EVIDENCE_OF_INDEPENDENCE',
        semantic_validation='NOT_PERFORMED',automatic_exclusion=False,transitive_inference=False)
    if reference_year is not None:
        def timing(year):
            return 'AFTER_REFERENCE_YEAR' if year>reference_year else 'SAME_YEAR_ORDER_UNRESOLVED' if year==reference_year else 'BEFORE_REFERENCE_YEAR'
        for row in between+touching:
            row['publication_reference_scope']={key:timing(row[key]['publication_year']) for key in ('from_publication','to_publication')}
            row['basis_reference_scopes']=[dict(reference=copy.deepcopy(node['reference']),publication_scope=timing(node['publication_year']))
                                           for node in row['basis_evidence']]
            scopes=set(row['publication_reference_scope'].values())
            if 'AFTER_REFERENCE_YEAR' in scopes:row['review_prompts'].append('RELATION_CONTEXT_INCLUDES_AFTER_REFERENCE_YEAR_PUBLICATION')
            if 'SAME_YEAR_ORDER_UNRESOLVED' in scopes:row['review_prompts'].append('RELATION_CONTEXT_INCLUDES_UNRESOLVED_SAME_YEAR_ORDER')
        result.update(reference_year=reference_year,relationship_assertion_time='NOT_SUPPLIED',
            timing_boundary='Publication dates do not establish source availability or when this relationship was known. Operator declarations may be retrospective.')
    return result


def render(result):
    lines=['Declared publication context | NOT VERIFIED INFLUENCE OR INDEPENDENCE',
        'Status: '+result['status'],'Relationship form sha256: '+result['form_sha256'],
        'Declared operator (not authenticated): '+display(result['operator_id'])]
    for row in result['relations']:
        lines.append('Relationship '+display(row['relation_id'])+' ['+row['relation_type']+'; operator_interpretation]: '+
            display(row['from_paper_id'])+(' <-> ' if row['relation_type'] in SYMMETRIC else ' -> ')+display(row['to_paper_id']))
        lines.append('  Direction: '+row['direction']+'; publication labels: '+row['publication_order'])
        lines.append('  Rationale: '+display(row['rationale']))
        lines.append('  Uncertainty: '+('NOT_SUPPLIED' if row['uncertainty'] is None else display(row['uncertainty'])))
        for key in ('from_publication','to_publication'):
            source=row[key];lines.append('  '+key+': '+display(source['paper_id'])+' | '+str(source['publication_year'])+
                ' ['+source['source_kind']+'] | '+display(source['source_locator'])+'; sha256='+source['source_sha256'])
        lines.append('  Review prompts: '+', '.join(row['review_prompts']))
        for node in row['basis_evidence']:
            lines.append('  Declared relationship basis, not a verified relation:')
            _render_endpoint(lines,node)
        for gap in row['basis_gaps']:
            ref=gap['reference'];lines.append('  '+gap['code']+': '+display(ref['paper_id'])+'/'+str(ref['observation_index'])+'/'+display(ref['dimension']))
    lines.append(BOUNDARY)
    return '\n'.join(lines)+'\n'


def _load(path):
    with Path(path).open('rb') as stream:raw=stream.read(8*1024*1024+1)
    if len(raw)>8*1024*1024:raise ValueError('input JSON exceeds the 8 MiB file limit')
    return loads(raw)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('package',type=Path)
    parser.add_argument('form',type=Path,nargs='?');parser.add_argument('--template',action='store_true')
    parser.add_argument('--operator-id');parser.add_argument('--format',choices=('json','text'),default='json');args=parser.parse_args()
    try:
        if args.template and (args.form is not None or args.format!='json'):
            raise ValueError('template requires JSON and no relationship form')
        if not args.template and (args.form is None or args.operator_id is not None):
            raise ValueError('inspection requires an explicit relationship form and no operator override')
        package=_load(args.package)
        result=template(package,args.operator_id) if args.template else inspect(package,_load(args.form))
        output=render(result) if args.format=='text' else json.dumps(result,indent=2)+'\n'
    except (ValueError,OSError,KeyError,TypeError,AttributeError) as exc:parser.exit(1,str(exc)+'\n')
    sys.stdout.buffer.write(output.encode('utf-8'))


if __name__=='__main__':main()
