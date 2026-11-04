"""Join answer and design reviews by exact evidence reference, never semantic inference."""
import argparse
import copy
import json
import sys
from pathlib import Path

from answer_draft import inspect as inspect_answer, review as review_answer, render as render_answer, explanation_fields, _render_explanation
from publication_scope import audit as audit_scope, render as render_scope
from persona import payload_sha256
from review_package import display
from strict_json import load

BOUNDARY = ('This packet joins operator-supplied artifacts with exactly equal question text and '
    'the same bound package. Equal wording is not proof of equal intent. Shared references mean '
    'the same paper/observation/component only, not agreement, independent support or scientific '
    'coherence. An observation and its component are different references. Citation roles, link '
    'relations and proposed-use roles remain separate operator declarations; none is inferred '
    'from another. Checklist entries are mechanical review prompts, not exhaustive faults or '
    'a readiness score. Source research/review kinds and claim labels do not prove individual '
    'ownership. All supplied evidence remains in the detailed sections. No answer, plan, '
    'author attribution, human approval or scientific result is generated or validated. '
    'No LLM, external call, source reread or canonical update is performed.')


def assemble(package, links, proposal, draft, reference_year, declared_review=None):
    answer = (inspect_answer(package, draft) if declared_review is None else
              review_answer(package, draft, declared_review))
    scope = audit_scope(package, links, proposal, reference_year)
    if answer['question'] != scope['design']['question']:
        raise ValueError('answer and design question text must match exactly; review their intended scope')
    routes, prompts = {}, []
    def route(node):
        year = node['publication_year']
        if type(year) is not int or not 1 <= year <= 9999:
            raise ValueError('indexed publication year must be an integer from 1 to 9999')
        timing = ('AFTER_REFERENCE_YEAR' if year > reference_year else
                  'SAME_YEAR_ORDER_UNRESOLVED' if year == reference_year else 'BEFORE_REFERENCE_YEAR')
        key = payload_sha256(node['reference'])
        if key not in routes:
            routes[key] = dict(reference_sha256=key, publication_scope=timing, evidence=copy.deepcopy(node),
                answer_uses=[], design_uses=[], unreferenced_link_uses=[])
        return routes[key]
    decisions = {d['claim_id']: d for d in answer.get('review', {}).get('decisions', [])}
    for claim in answer['claims']:
        claim_scopes = set()
        for citation in claim['citations']:
            claim_scopes.add(route(citation['evidence'])['publication_scope'])
            route(citation['evidence'])['answer_uses'].append(dict(claim_id=claim['claim_id'],
                claim_type=claim['claim_type'], role=citation['role'], **explanation_fields(citation)))
            for code in citation.get('explanation_review_prompts', []):
                prompts.append(dict(target='answer_citation', target_id=claim['claim_id'],
                    reference=copy.deepcopy(citation['evidence']['reference']), role=citation['role'], code=code))
        for timing in ('AFTER_REFERENCE_YEAR', 'SAME_YEAR_ORDER_UNRESOLVED'):
            if timing in claim_scopes:
                prompts.append(dict(target='answer_claim', target_id=claim['claim_id'], code=timing))
        if not claim['citations']: prompts.append(dict(target='answer_claim', target_id=claim['claim_id'], code='NO_CITATIONS_SUPPLIED'))
        if claim['missing_uncertainty']: prompts.append(dict(target='answer_claim', target_id=claim['claim_id'], code='UNCERTAINTY_NOT_SUPPLIED'))
        decision = decisions.get(claim['claim_id'])
        if decision is None or decision['decision'] != 'retain':
            prompts.append(dict(target='answer_claim', target_id=claim['claim_id'],
                code='NO_DECLARED_REVIEW' if decision is None else 'DECLARED_' + decision['decision'].upper()))
    for step in scope['steps']:
        for field in step['missing_proposal_fields']:
            prompts.append(dict(target='design_step', target_id=step['step_id'], code='NOT_SUPPLIED', field=field))
        if step['status'] != 'NO_LATER_LINK_ENDPOINTS':
            prompts.append(dict(target='design_step', target_id=step['step_id'], code=step['status']))
        for use in step['link_uses']:
            link = use['evidence']
            for endpoint in link['endpoints']:
                route(endpoint['evidence'])['design_uses'].append(dict(step_id=step['step_id'],
                    link_id=link['link_id'], role=use['role'], relation=link['relation'],
                    direction=endpoint['direction'], publication_scope=endpoint['publication_scope']))
    for link in scope['unreferenced_links']:
        for endpoint in link['endpoints']:
            route(endpoint['evidence'])['unreferenced_link_uses'].append(dict(link_id=link['link_id'],
                relation=link['relation'], direction=endpoint['direction'], publication_scope=endpoint['publication_scope']))
    if not answer['claims']: prompts.append(dict(target='answer', target_id=None, code='NO_ANSWER_CLAIMS'))
    if not scope['steps']: prompts.append(dict(target='design', target_id=None, code='NO_PROPOSED_STEPS'))
    bindings = dict(persona_sha256=answer['persona_sha256'], knowledge_papers_sha256=answer['knowledge_papers_sha256'],
        draft_sha256=answer['draft_sha256'], proposal_sha256=scope['proposal_sha256'],
        link_artifact_sha256=scope['link_artifact_sha256'], scope_request_sha256=scope['scope_request_sha256'],
        review_sha256=answer.get('review_sha256'))
    return dict(status='INTEGRATED_REVIEW_REQUIRED', question=answer['question'], bindings=bindings,
        packet_input_sha256=payload_sha256(bindings), reference_year=reference_year,
        review_prompts=prompts, evidence_routes=list(routes.values()), answer=answer, publication_scope=scope,
        route_scope='EXACT_REFERENCES_IN_ANSWER_OR_LINKS_NOT_COMPLETE_CORPUS_INVENTORY',
        semantic_validation='NOT_PERFORMED', llm_used=False, canonical_update_performed=False, boundary=BOUNDARY)


def render(package, links, proposal, draft, reference_year, declared_review=None):
    result = assemble(package, links, proposal, draft, reference_year, declared_review)
    lines = ['Integrated scholarly review packet', 'Status: ' + result['status'],
        'Question: ' + display(result['question']), 'Packet input sha256: ' + result['packet_input_sha256'],
        'Mechanical review prompts (not a score or complete scientific review):']
    for prompt in result['review_prompts']:
        lines.append('  ' + prompt['target'] + ' ' + display(prompt['target_id']) + ': ' + prompt['code'] +
            (' / ' + prompt['field'] if 'field' in prompt else ''))
    if not result['review_prompts']: lines.append('  None detected by this checklist; validation remains NOT_PERFORMED.')
    lines.append('Exact evidence reference index (shared reference does not establish agreement):')
    for route in result['evidence_routes']:
        node = route['evidence']; ref = node['reference']; obs = node['observation']
        lines.append('  ' + display(ref['paper_id']) + ' / observation ' + str(ref['observation_index']) + ' / ' +
            display(ref['dimension']) + ' | ' + str(node['publication_year']) + ' [' + node['source_kind'] + '] | ' + route['publication_scope'])
        lines.append('    Observation stance/claim: ' + obs['stance'] + ' / ' + obs['claim_type'])
        if node['component'] is not None: lines.append('    Component claim: ' + node['component']['claim_type'])
        for use in route['answer_uses']:
            lines.append('    Answer ' + display(use['claim_id']) + ' [' + use['claim_type'] + ']: citation role=' + use['role'])
            _render_explanation(lines, use)
        for use in route['design_uses']:
            lines.append('    Design ' + display(use['step_id']) + ': ' + display(use['link_id']) + ' / ' + use['direction'] +
                '; use role=' + use['role'] + '; link relation=' + use['relation'] + '; ' + use['publication_scope'])
        for use in route['unreferenced_link_uses']:
            lines.append('    Unreferenced link ' + display(use['link_id']) + ' / ' + use['direction'] +
                ': ' + use['relation'] + '; ' + use['publication_scope'])
    lines.append('Packet boundary: ' + BOUNDARY)
    lines.append('Detailed answer, review decisions and uncited observations:')
    lines.append(render_answer(result['answer']).rstrip('\n'))
    lines.append('Detailed publication scope, design and all supplied links:')
    lines.append(render_scope(package, links, proposal, reference_year).rstrip('\n'))
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('package', 'links', 'proposal', 'draft'): parser.add_argument(name, type=Path)
    parser.add_argument('--reference-year', required=True, type=int)
    parser.add_argument('--review', type=Path)
    parser.add_argument('--format', choices=('json', 'text'), default='json')
    args = parser.parse_args()
    try:
        inputs = (load(args.package), load(args.links), load(args.proposal), load(args.draft),
                  args.reference_year, load(args.review) if args.review else None)
        output = render(*inputs) if args.format == 'text' else json.dumps(assemble(*inputs), indent=2) + '\n'
    except (ValueError, OSError, KeyError, TypeError, AttributeError) as exc: parser.exit(1, str(exc) + '\n')
    sys.stdout.buffer.write(output.encode('utf-8'))


if __name__ == '__main__': main()
