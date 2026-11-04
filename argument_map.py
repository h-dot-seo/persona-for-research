"""Review operator-declared premise/conclusion steps without reconstructing private reasoning."""
import argparse
import copy
import json
import sys
from pathlib import Path

from answer_draft import inspect as inspect_answer, review as review_answer, render as render_answer
from design_scenario import _text
from persona import payload_sha256
from review_package import display
from strict_json import load

BOUNDARY = ('This is an operator-declared argument map, not private researcher thoughts, '
    'a model reasoning trace or a validated derivation. Premise/conclusion connections, bridge '
    'rationales, assumptions and defeaters are supplied by the operator. Acyclic order is only '
    'a deterministic review aid, not scientific validity or chronological influence. Source '
    'quotes cannot be inferred conclusions; all conclusions remain operator_synthesis. '
    'Premise citations are not automatically transferred to conclusions, and multiple paths '
    'are not independent corroboration. Missing assumptions or defeaters mean not supplied, '
    'not absent. Retained, rejected and deferred source claims remain visible; recorded review '
    'does not certify logical steps. No LLM, external call, source reread, canonical update or '
    'researcher-fidelity evaluation is performed.')


def _answer(package, draft, declared_review):
    return inspect_answer(package, draft) if declared_review is None else review_answer(package, draft, declared_review)


def template(package, draft, operator_id, declared_review=None):
    return _template_from_answer(_answer(package, draft, declared_review), operator_id)


def _template_from_answer(answer, operator_id):
    """Build a form from a fresh, local validation result; never a public input."""
    _text(operator_id, 'operator_id', 128)
    return dict(draft_sha256=answer['draft_sha256'], review_sha256=answer.get('review_sha256'),
                operator_id=operator_id, steps=[])


def inspect(package, draft, supplied, declared_review=None):
    if isinstance(supplied, dict) and supplied.get('schema') in ('persona.reviewed-argument-proposals.v1', 'persona.reviewed-argument-proposals.v2'):
        from argument_proposals import inspect_reviewed
        return inspect_reviewed(package, draft, supplied, declared_review)
    return _inspect_from_answer(_answer(package, draft, declared_review), supplied)


def _inspect_from_answer(answer, supplied):
    """Inspect a plain map against a fresh, local validation result."""
    if not isinstance(supplied, dict) or set(supplied) != {'draft_sha256', 'review_sha256', 'operator_id', 'steps'}:
        raise ValueError('argument map has missing or unknown fields')
    _text(supplied['operator_id'], 'operator_id', 128)
    if supplied['draft_sha256'] != answer['draft_sha256'] or supplied['review_sha256'] != answer.get('review_sha256'):
        raise ValueError('argument map is bound to a different draft or declared review')
    if not isinstance(supplied['steps'], list): raise ValueError('steps must be an array')
    claims = {c['claim_id']: c for c in answer['claims']}
    decisions = {d['claim_id']: d['decision'] for d in answer.get('review', {}).get('decisions', [])}
    ids, covered, conclusions, rows = set(), set(), set(), []
    incoming = {key: set() for key in claims}
    for step in supplied['steps']:
        if not isinstance(step, dict) or set(step) != {'step_id', 'premise_claim_ids', 'conclusion_claim_id', 'bridge_rationale', 'assumptions', 'defeater'}:
            raise ValueError('step has missing or unknown fields')
        _text(step['step_id'], 'step_id', 128); _text(step['bridge_rationale'], 'bridge_rationale')
        if step['step_id'] in ids: raise ValueError('duplicate step ID')
        ids.add(step['step_id'])
        conclusion = step['conclusion_claim_id']; _text(conclusion, 'conclusion_claim_id', 128)
        if conclusion not in claims or claims[conclusion]['claim_type'] != 'operator_synthesis':
            raise ValueError('conclusion must reference an operator_synthesis claim')
        premises = step['premise_claim_ids']
        if not isinstance(premises, list) or not premises: raise ValueError('each step needs explicit premise claim IDs')
        seen = set()
        for premise in premises:
            _text(premise, 'premise_claim_id', 128)
            if premise not in claims or premise in seen or premise == conclusion:
                raise ValueError('unknown, duplicate or self-referencing premise')
            seen.add(premise); covered.add(premise)
            incoming[conclusion].add(premise)
        assumptions = step['assumptions']
        if not isinstance(assumptions, list): raise ValueError('assumptions must be an explicit array')
        for assumption in assumptions: _text(assumption, 'assumption')
        if len(set(assumptions)) != len(assumptions): raise ValueError('duplicate assumption text')
        if step['defeater'] is not None: _text(step['defeater'], 'defeater')
        covered.add(conclusion); conclusions.add(conclusion)
        def endpoint(claim_id):
            return dict(claim_id=claim_id, claim_type=claims[claim_id]['claim_type'],
                declared_review_decision=decisions.get(claim_id, 'NOT_SUPPLIED'),
                direct_citation_count=len(claims[claim_id]['citations']),
                evidence_status=claims[claim_id]['evidence_status'], uncertainty=claims[claim_id]['uncertainty'])
        rows.append(dict(**copy.deepcopy(step), claim_type='operator_interpretation',
            premises=[endpoint(key) for key in premises], conclusion=endpoint(conclusion),
            missing_fields=(['assumptions'] if not assumptions else []) + (['defeater'] if step['defeater'] is None else []),
            citation_transfer='NOT_PERFORMED', logical_validation='NOT_PERFORMED'))
    # Stable Kahn order by original answer order, without recursion or implied priority.
    remaining = {key: set(values) for key, values in incoming.items() if key in covered}
    order = []
    while remaining:
        ready = [key for key in claims if key in remaining and not remaining[key]]
        if not ready: raise ValueError('circular premise/conclusion dependency; this contract requires an acyclic declared map')
        for key in ready:
            order.append(key); remaining.pop(key)
        for values in remaining.values(): values.difference_update(ready)
    rank = {key: index for index, key in enumerate(order)}
    rows.sort(key=lambda row: rank[row['conclusion_claim_id']])
    return dict(status='ARGUMENT_MAP_REQUIRES_REVIEW' if rows else 'NO_DECLARED_ARGUMENT_STEPS',
        draft_sha256=answer['draft_sha256'], review_sha256=answer.get('review_sha256'),
        argument_map_sha256=payload_sha256(supplied), operator_id=supplied['operator_id'],
        operator_identity='RECORDED_NOT_AUTHENTICATED', steps=rows,
        review_order_claim_ids=order, unmapped_claim_ids=[key for key in claims if key not in covered],
        premise_only_claim_ids=[key for key in claims if key in covered and key not in conclusions],
        answer=answer, logical_validation='NOT_PERFORMED', llm_used=False,
        canonical_update_performed=False, boundary=BOUNDARY)


def render(package, draft, supplied, declared_review=None):
    return _render_inspected(inspect(package, draft, supplied, declared_review))


def _render_inspected(result):
    """Format a fresh internal inspection; public callers still supply raw inputs."""
    lines = ['Operator-declared argument map', 'Status: ' + result['status'],
        'Argument map sha256: ' + result['argument_map_sha256'],
        'Declared map operator: ' + display(result['operator_id']) + ' (not authenticated)',
        'Deterministic review order (not actual researcher reasoning): ' + ', '.join(display(x) for x in result['review_order_claim_ids']),
        'Unmapped claims: ' + (', '.join(display(x) for x in result['unmapped_claim_ids']) or 'none (not completeness)'),
        'Premise-only claims: ' + (', '.join(display(x) for x in result['premise_only_claim_ids']) or 'none')]
    if 'proposal_review' in result:
        lines.append('Map origin: operator-adopted imported bridges, not wholly operator-authored text or researcher reasoning.')
        lines.append('Declared step order (separate from review topology): '+', '.join(display(key) for key in result['declared_step_ids']))
        lines.append('Current inspection invokes no provider. Historical generation and reviewer identity are declared, not authenticated.')
    for row in result['steps']:
        lines.append('Step ' + display(row['step_id']) + ' [operator_interpretation]: ' +
            ', '.join(display(x) for x in row['premise_claim_ids']) + ' -> ' + display(row['conclusion_claim_id']))
        if 'proposal_origin' in row:
            lines.append('  Bridge origin: '+display(row['origin'])+'; recorded candidate='+display(row['proposal_origin']['candidate_id']))
        lines.append('  Bridge rationale: ' + display(row['bridge_rationale']))
        lines.append('  Assumptions: ' + (' | '.join(display(x) for x in row['assumptions']) or 'NOT_SUPPLIED'))
        lines.append('  Defeater: ' + ('NOT_SUPPLIED' if row['defeater'] is None else display(row['defeater'])))
        for role, nodes in (('Premise', row['premises']), ('Conclusion', [row['conclusion']])):
            for node in nodes:
                lines.append('  ' + role + ' ' + display(node['claim_id']) + ' [' + node['claim_type'] + ']: declared review=' +
                    node['declared_review_decision'] + '; direct citations=' + str(node['direct_citation_count']) + '; ' + node['evidence_status'])
                lines.append('    Uncertainty: ' + ('NOT_SUPPLIED' if node['uncertainty'] is None else display(node['uncertainty'])))
        lines.append('  Citation transfer: NOT_PERFORMED; logical validation: NOT_PERFORMED')
    lines.append('Map boundary: ' + result.get('boundary', BOUNDARY))
    lines.append('Full answer claims, source citations and recorded review decisions:')
    lines.append(render_answer(result['answer']).rstrip('\n'))
    if 'proposal_review' in result:
        from argument_proposals import render_review, MAX_OUTPUT_BYTES
        lines.append('Full imported argument proposal/adoption history:')
        lines.append(render_review(result['proposal_review']).rstrip('\n'))
    output='\n'.join(lines) + '\n'
    if 'proposal_review' in result and len(output.encode('utf-8'))>MAX_OUTPUT_BYTES:
        raise ValueError('imported argument text report exceeds 16 MiB')
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package', type=Path); parser.add_argument('draft', type=Path)
    parser.add_argument('map', type=Path, nargs='?'); parser.add_argument('--review', type=Path)
    parser.add_argument('--template', action='store_true'); parser.add_argument('--operator-id')
    parser.add_argument('--format', choices=('json', 'text'), default='json'); args = parser.parse_args()
    try:
        package, draft = load(args.package), load(args.draft); declared = load(args.review) if args.review else None
        if args.template:
            if args.map or args.format != 'json': raise ValueError('empty map template needs JSON and no map input')
            output = json.dumps(template(package, draft, args.operator_id, declared), indent=2) + '\n'
        else:
            if args.map is None or args.operator_id is not None: raise ValueError('supply a map without operator override')
            supplied = load(args.map)
            output = render(package, draft, supplied, declared) if args.format == 'text' else json.dumps(inspect(package, draft, supplied, declared), indent=2) + '\n'
            if isinstance(supplied, dict) and supplied.get('schema') in ('persona.reviewed-argument-proposals.v1', 'persona.reviewed-argument-proposals.v2'):
                from argument_proposals import MAX_OUTPUT_BYTES
                if len(output.encode('utf-8'))>MAX_OUTPUT_BYTES: raise ValueError('imported argument output exceeds 16 MiB')
    except (ValueError, OSError, KeyError, TypeError, AttributeError, RecursionError) as exc: parser.exit(1, str(exc) + '\n')
    sys.stdout.buffer.write(output.encode('utf-8'))


if __name__ == '__main__': main()
