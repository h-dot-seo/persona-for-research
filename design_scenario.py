"""Trace an operator's proposed design to supplied reasoning links, without inference."""
from exclusive_output import add_output_argument, emit, preflight
import argparse
import copy
import json
import sys
from pathlib import Path

from persona import payload_sha256
from reasoning_links import review as review_links, render as render_links
from review_package import display
from strict_json import load

OPTIONAL_FIELDS = ('hypothesis', 'falsification_check', 'alternative_explanation', 'uncertainty')
STEP_KEYS = {'step_id', 'proposed_action', 'rationale', 'link_uses'} | set(OPTIONAL_FIELDS)
BINDINGS = ('persona_sha256', 'knowledge_papers_sha256', 'link_artifact_sha256')
PROPOSAL_KEYS = set(BINDINGS) | {'operator_id', 'question', 'steps'}
ROLES = ('motivation', 'constraint', 'counterargument')
BOUNDARY = ('This is an operator-authored design scenario, not an author recommendation, '
    'model-generated experiment, or validated reconstruction of researcher reasoning. '
    'The question, actions and applicability notes are not semantically interpreted. '
    'Link-use roles describe proposed uses, not original author claims or proof that '
    'evidence applies to the proposal. Filled fields do not establish sound design; '
    'listed gaps describe supplied records only. Unused links are not automatically '
    'irrelevant, and listed links need not exhaust contrary evidence. Source challenges, '
    'limitations and publication dates remain unresolved. No external call, LLM, '
    'canonical update, scientific execution or human-review authentication is performed.')


def _text(value, field, limit=2000):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(field + ' must be a bounded nonempty string')


def template(package, links, question, operator_id):
    evidence = review_links(package, links)
    _text(question, 'question')
    _text(operator_id, 'operator_id', 128)
    return dict(**{key: evidence[key] for key in BINDINGS}, question=question,
                operator_id=operator_id, steps=[])


def review(package, links, proposal):
    evidence = review_links(package, links)
    if not isinstance(proposal, dict) or set(proposal) != PROPOSAL_KEYS:
        raise ValueError('proposal has missing or unknown fields')
    if any(proposal[key] != evidence[key] for key in BINDINGS):
        raise ValueError('proposal is bound to different evidence; re-review its uses')
    _text(proposal['question'], 'question')
    _text(proposal['operator_id'], 'operator_id', 128)
    if not isinstance(proposal['steps'], list):
        raise ValueError('proposal steps must be an array')
    known = {link['link_id'] for link in evidence['links']}
    seen, referenced, steps = set(), set(), []
    for step in proposal['steps']:
        if not isinstance(step, dict) or set(step) != STEP_KEYS:
            raise ValueError('step has missing or unknown fields')
        for field in ('step_id', 'proposed_action', 'rationale'):
            _text(step[field], field, 128 if field == 'step_id' else 2000)
        if step['step_id'] in seen:
            raise ValueError('duplicate step ID')
        seen.add(step['step_id'])
        for field in OPTIONAL_FIELDS:
            if step[field] is not None:
                _text(step[field], field)
        if not isinstance(step['link_uses'], list):
            raise ValueError('link_uses must be an array')
        uses = set()
        for use in step['link_uses']:
            if not isinstance(use, dict) or set(use) != {'link_id', 'role', 'applicability_note'}:
                raise ValueError('link use must contain only ID, role and applicability_note')
            _text(use['link_id'], 'link_id', 128)
            _text(use['applicability_note'], 'applicability_note')
            if use['link_id'] not in known or use['role'] not in ROLES:
                raise ValueError('unknown link or unsupported proposed-use role')
            key = (use['link_id'], use['role'])
            if key in uses:
                raise ValueError('duplicate link/role use in a step')
            uses.add(key); referenced.add(use['link_id'])
        row = copy.deepcopy(step)
        row.update(claim_type='operator_proposal', status='PROPOSED_STEP_REQUIRES_REVIEW',
            authorship='OPERATOR_AUTHORED_ACTION_RATIONALE_FIELDS_AND_USES',
            missing_fields=[field for field in OPTIONAL_FIELDS if step[field] is None],
            evidence_status='LINK_USES_SUPPLIED_NOT_VALIDATED' if uses else 'NO_LINKED_EVIDENCE_SUPPLIED',
            distinct_link_count=len({use['link_id'] for use in step['link_uses']}))
        steps.append(row)
    return dict(status='DESIGN_SCENARIO_REQUIRES_REVIEW' if steps else 'NO_PROPOSED_STEPS',
        question=proposal['question'], operator_id=proposal['operator_id'],
        operator_identity='RECORDED_NOT_AUTHENTICATED', proposal_sha256=payload_sha256(proposal),
        **{key: evidence[key] for key in BINDINGS}, steps=steps, evidence_links=evidence,
        unreferenced_link_ids=[link['link_id'] for link in evidence['links'] if link['link_id'] not in referenced],
        semantic_validation='NOT_PERFORMED', llm_used=False, canonical_update_performed=False,
        boundary=BOUNDARY)


def render(package, links, proposal):
    result = review(package, links, proposal)
    lines = ['Operator research-design scenario', 'Status: ' + result['status'],
        'Question: ' + display(result['question']),
        'Declared operator: ' + display(result['operator_id']) + ' (not authenticated)',
        'Proposal sha256: ' + result['proposal_sha256']]
    for step in result['steps']:
        lines.append('Step ' + display(step['step_id']) + ' [operator_proposal]: ' + display(step['proposed_action']))
        lines.append('  Rationale: ' + display(step['rationale']))
        for field in OPTIONAL_FIELDS:
            lines.append('  ' + field + ': ' + ('NOT_SUPPLIED' if step[field] is None else display(step[field])))
        lines.append('  Evidence status: ' + step['evidence_status'])
        for use in step['link_uses']:
            lines.append('  Link use ' + display(use['link_id']) + ' [' + use['role'] + ']: ' + display(use['applicability_note']))
    lines.append('Unreferenced supplied links: ' + (', '.join(display(i) for i in result['unreferenced_link_ids']) or 'none (not proof of complete evidence)'))
    lines.append('Design boundary: ' + BOUNDARY)
    lines.append('All supplied evidence links, including unreferenced links:')
    lines.append(render_links(package, links).rstrip('\n'))
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package', type=Path)
    parser.add_argument('links', type=Path)
    parser.add_argument('proposal', type=Path, nargs='?')
    parser.add_argument('--template', action='store_true')
    parser.add_argument('--question')
    parser.add_argument('--operator-id')
    parser.add_argument('--format', choices=('json', 'text'), default='json')
    add_output_argument(parser); args = parser.parse_args()
    preflight(parser, getattr(args, 'output', None))
    try:
        package, links = load(args.package), load(args.links)
        if args.template:
            if args.proposal is not None or args.format != 'json':
                raise ValueError('empty template mode requires no proposal and JSON output')
            output = json.dumps(template(package, links, args.question, args.operator_id), indent=2) + '\n'
        else:
            if args.proposal is None or args.question is not None or args.operator_id is not None:
                raise ValueError('review requires an explicit proposal; question/operator come from it')
            proposal = load(args.proposal)
            output = render(package, links, proposal) if args.format == 'text' else json.dumps(review(package, links, proposal), indent=2) + '\n'
    except (ValueError, OSError, KeyError, TypeError, AttributeError) as exc:
        parser.exit(1, str(exc) + '\n')
    emit(parser, output.encode('utf-8'), getattr(args, 'output', None))


if __name__ == '__main__':
    main()
