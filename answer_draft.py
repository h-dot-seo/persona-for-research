"""Inspect evidence-bound answer drafts and declared reviews, without generating answers."""
import argparse
import copy
import json
import sys
from pathlib import Path

from persona import payload_sha256
from reasoning_links import _sources, _endpoint
from design_scenario import _text
from review_package import display
from strict_json import load
from observation_provenance import lines as origin_lines, KEY as OBSERVATION_ORIGIN

BINDINGS = ('persona_sha256', 'knowledge_papers_sha256')
ROLES = ('support', 'challenge', 'context')
BOUNDARY = ('Draft text and citation roles are operator supplied, not model-generated answers '
    'or verified scholar reasoning. Operator synthesis never becomes an author claim. '
    'A source_quote is compared only with the stored quote record, not reread source bytes; '
    'equality does not verify interpretation, individual authorship or quotation rights. '
    'Research/review kinds and original claim labels remain separate; reviews may report '
    "other people's work. Citation presence does not establish semantic support. Uncited "
    'observations are listed without claiming relevance or complete counterevidence. '
    'Declared retain/revise/reject decisions are not authenticated human or scientific '
    'validation, publication permission or canonical updates. No LLM or external call is used.')


def template(package, question, operator_id):
    checked, _ = _sources(package)
    _text(question, 'question'); _text(operator_id, 'operator_id', 128)
    return dict(persona_sha256=payload_sha256(checked['persona']),
        knowledge_papers_sha256=payload_sha256(checked['knowledge']['papers']),
        question=question, operator_id=operator_id, claims=[])


def inspect(package, draft):
    checked, papers = _sources(package)
    if not isinstance(draft, dict) or set(draft) != set(BINDINGS) | {'question', 'operator_id', 'claims'}:
        raise ValueError('draft has missing or unknown fields')
    expected = template(checked, draft['question'], draft['operator_id'])
    if any(draft[k] != expected[k] for k in BINDINGS):
        raise ValueError('draft is bound to a different package')
    if not isinstance(draft['claims'], list): raise ValueError('claims must be an array')
    ids, cited, claims = set(), set(), []
    for claim in draft['claims']:
        if not isinstance(claim, dict) or set(claim) != {'claim_id', 'text', 'claim_type', 'citations', 'uncertainty'}:
            raise ValueError('claim has missing or unknown fields')
        _text(claim['claim_id'], 'claim_id', 128); _text(claim['text'], 'claim text')
        if claim['claim_id'] in ids: raise ValueError('duplicate claim ID')
        ids.add(claim['claim_id'])
        if claim['claim_type'] not in ('operator_synthesis', 'source_quote'):
            raise ValueError('answer claim must be operator_synthesis or source_quote')
        if claim['uncertainty'] is not None: _text(claim['uncertainty'], 'uncertainty')
        if not isinstance(claim['citations'], list): raise ValueError('citations must be an array')
        citations, seen = [], set()
        for citation in claim['citations']:
            if not isinstance(citation, dict) or set(citation) != {'reference', 'role'} or citation['role'] not in ROLES:
                raise ValueError('citation requires a reference and supported operator role')
            node = _endpoint(citation['reference'], papers)
            key = (payload_sha256(citation['reference']), citation['role'])
            if key in seen: raise ValueError('duplicate reference/role citation')
            seen.add(key)
            ref = node['reference']; cited.add((ref['paper_id'], ref['observation_index']))
            citations.append(dict(role=citation['role'], role_origin='OPERATOR_SUPPLIED', evidence=node))
        quote_check = 'NOT_APPLICABLE_OPERATOR_SYNTHESIS'
        if claim['claim_type'] == 'source_quote':
            if len(citations) != 1: raise ValueError('source_quote requires exactly one citation')
            node = citations[0]['evidence']; record = node['component'] if node['component'] is not None else node['observation']
            if claim['text'] != record.get('evidence_quote'):
                raise ValueError('source_quote must exactly equal the selected stored evidence_quote')
            quote_check = 'EQUALS_STORED_QUOTE_ONLY'
        claims.append(dict(claim_id=claim['claim_id'], text=claim['text'], claim_type=claim['claim_type'],
            uncertainty=claim['uncertainty'], citations=citations, quote_check=quote_check,
            evidence_status='CITATIONS_SUPPLIED_NOT_VALIDATED' if citations else 'NO_CITATIONS_SUPPLIED',
            missing_uncertainty=claim['uncertainty'] is None,
            challenge_citation_supplied=any(c['role'] == 'challenge' for c in citations)))
    uncited = []
    for paper in papers.values():
        for index, obs in enumerate(paper['observations']):
            if (paper['paper_id'], index) not in cited:
                uncited.append(_endpoint(dict(paper_id=paper['paper_id'], observation_index=index, dimension=None), papers))
    return dict(status='ANSWER_DRAFT_REQUIRES_REVIEW' if claims else 'NO_ANSWER_CLAIMS',
        **{k: expected[k] for k in BINDINGS}, question=draft['question'], operator_id=draft['operator_id'],
        draft_sha256=payload_sha256(draft), claims=claims, uncited_observations=uncited,
        uncited_scope='OBSERVATION_LEVEL_ONLY_NOT_UNUSED_COMPONENT_INVENTORY',
        semantic_validation='NOT_PERFORMED', llm_used=False, canonical_update_performed=False, boundary=BOUNDARY)


def review_template(package, draft, reviewer_id):
    result = inspect(package, draft); _text(reviewer_id, 'reviewer_id', 128)
    return dict(draft_sha256=result['draft_sha256'], reviewer_id=reviewer_id,
        decisions=[dict(claim_id=c['claim_id'], decision='defer', note='Not reviewed.') for c in result['claims']])


def review(package, draft, supplied):
    result = inspect(package, draft)
    if not isinstance(supplied, dict) or set(supplied) != {'draft_sha256', 'reviewer_id', 'decisions'}:
        raise ValueError('review has missing or unknown fields')
    if supplied['draft_sha256'] != result['draft_sha256']: raise ValueError('review is stale for this draft')
    _text(supplied['reviewer_id'], 'reviewer_id', 128)
    if not isinstance(supplied['decisions'], list): raise ValueError('decisions must be an array')
    known = {c['claim_id'] for c in result['claims']}; seen = set()
    for decision in supplied['decisions']:
        if not isinstance(decision, dict) or set(decision) != {'claim_id', 'decision', 'note'}:
            raise ValueError('decision has missing or unknown fields')
        _text(decision['claim_id'], 'claim_id', 128); _text(decision['note'], 'review note')
        if decision['claim_id'] not in known or decision['claim_id'] in seen: raise ValueError('unknown or duplicate reviewed claim')
        seen.add(decision['claim_id'])
        if decision['decision'] not in ('retain', 'revise', 'reject', 'defer'): raise ValueError('unsupported decision')
    if seen != known: raise ValueError('review must record every claim exactly once')
    result.update(review=copy.deepcopy(supplied), review_sha256=payload_sha256(supplied),
        reviewer_identity='RECORDED_NOT_AUTHENTICATED',
        status='NO_ANSWER_CLAIMS' if not known else
        'DECLARED_REVIEW_INCOMPLETE' if any(d['decision'] == 'defer' for d in supplied['decisions']) else
        'DECLARED_REVIEW_RECORDED_NOT_VALIDATED')
    return result


def render(result):
    lines = ['Evidence-bound answer draft', 'Status: ' + result['status'],
        'Question: ' + display(result['question']), 'Draft sha256: ' + result['draft_sha256'],
        'Persona sha256: ' + result['persona_sha256'],
        'Knowledge papers sha256: ' + result['knowledge_papers_sha256'],
        'Declared draft operator: ' + display(result['operator_id']) + ' (not authenticated)']
    if 'review' in result:
        lines.append('Declared reviewer: ' + display(result['review']['reviewer_id']) + ' (not authenticated)')
        lines.append('Review sha256: ' + result['review_sha256'])
    decisions = {d['claim_id']: d for d in result.get('review', {}).get('decisions', [])}
    for claim in result['claims']:
        lines.append('Claim ' + display(claim['claim_id']) + ' [' + claim['claim_type'] + ']: ' + display(claim['text']))
        lines.append('  Evidence: ' + claim['evidence_status'] + '; quote check=' + claim['quote_check'])
        lines.append('  Uncertainty: ' + ('NOT_SUPPLIED' if claim['uncertainty'] is None else display(claim['uncertainty'])))
        decision = decisions.get(claim['claim_id'])
        if decision: lines.append('  Declared decision: ' + decision['decision'] + ' | ' + display(decision['note']))
        for citation in claim['citations']:
            lines.append('  Citation role: ' + citation['role'] + ' [operator supplied]')
            _render_endpoint(lines, citation['evidence'])
    lines.append('Uncited observations (not an inventory of unused components):')
    for node in result['uncited_observations']: _render_endpoint(lines, node)
    lines.append('Boundary: ' + BOUNDARY)
    return '\n'.join(lines) + '\n'


def _render_endpoint(lines, node):
    ref = node['reference']; obs = node['observation']; component = node['component']
    lines.append('    ' + display(ref['paper_id']) + ' / observation ' + str(ref['observation_index']) +
        ' / ' + display(ref['dimension']) + ' | ' + str(node['publication_year']) + ' [' + node['source_kind'] + ']')
    lines.append('    Source: ' + display(node['source_locator']) + '; sha256=' + node['source_sha256'])
    lines.append('    Observation [' + obs['stance'] + '; ' + obs['claim_type'] + ']: ' + display(obs['method']))
    lines.append('    Condition: ' + display(obs['condition']) + '; limitation: ' + display(obs['limitation']))
    lines.append('    Observation locator: ' + display(obs['locator']))
    if OBSERVATION_ORIGIN in obs: lines.extend(origin_lines(obs[OBSERVATION_ORIGIN], display))
    record = component if component is not None else obs
    if component is not None: lines.append('    Component [' + component['claim_type'] + ']: ' + display(component['text']))
    if component is not None and 'origin' in component:
        lines.append('    Component origin: ' + display(component['origin']) +
            '; proposed claim label=' + display(component['proposed_claim_type']) +
            '; candidate=' + display(component['candidate_id']))
        lines.append('    Candidate bundle sha256: ' + component['candidate_bundle_sha256'] +
            '; operator review sha256: ' + component['operator_review_sha256'])
    lines.append('    Selected locator: ' + display(record['locator']) + '; stored quote: ' + display(record['evidence_quote']))
    lines.append('    Recorded checks (not rechecked): source=' + node['recorded_source_check'] +
        '; selected=' + record.get('evidence_verification', 'NOT_PERFORMED'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package', type=Path); parser.add_argument('draft', type=Path, nargs='?')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--template', action='store_true'); mode.add_argument('--review-template', action='store_true')
    mode.add_argument('--review', type=Path)
    parser.add_argument('--question'); parser.add_argument('--operator-id'); parser.add_argument('--reviewer-id')
    parser.add_argument('--format', choices=('json', 'text'), default='json')
    args = parser.parse_args()
    try:
        package = load(args.package)
        if args.template:
            if args.draft or args.reviewer_id or args.format != 'json': raise ValueError('draft template requires JSON and no draft/reviewer')
            result = template(package, args.question, args.operator_id)
        else:
            if args.draft is None or args.question is not None or args.operator_id is not None: raise ValueError('supply a draft, without question/operator overrides')
            draft = load(args.draft)
            if args.review_template:
                if args.format != 'json': raise ValueError('review template requires JSON')
                result = review_template(package, draft, args.reviewer_id)
            else:
                if args.reviewer_id is not None: raise ValueError('reviewer comes from review artifact')
                result = review(package, draft, load(args.review)) if args.review else inspect(package, draft)
        output = render(result) if args.format == 'text' else json.dumps(result, indent=2) + '\n'
    except (ValueError, OSError, KeyError, TypeError, AttributeError) as exc: parser.exit(1, str(exc) + '\n')
    sys.stdout.buffer.write(output.encode('utf-8'))


if __name__ == '__main__': main()
