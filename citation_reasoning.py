"""Explicit, offline inventory of declared reasoning for each current citation use."""
from exclusive_output import add_output_argument, emit, preflight
import argparse
import copy
import json
import sys
from pathlib import Path

import answer_draft
from persona import payload_sha256
from reasoning_links import _sources
from review_package import display
from strict_json import loads, MAX_CONTAINER_DEPTH

SCHEMA = 'persona.citation-reasoning-audit.v1'
MAX_INPUT_BYTES = 8 * 1024 * 1024
MAX_OUTPUT_BYTES = 16 * 1024 * 1024
STATES = ('LEGACY_KEY_ABSENT', 'EXPLICITLY_NOT_SUPPLIED',
          'DECLARED_INTERPRETATION_NOT_VALIDATED')
BOUNDARY = (
    'This is an inventory, not a score, completeness assessment or approval. Every explanation '
    'is a declared interpretation, not validated semantic support, source authorship or quotation rights. '
    'Review articles may report other people\'s work. Source_quote equality compares only the stored '
    'quote, not current source bytes. Citations never transfer to uncited conclusions. A null context '
    'boundary is descriptive only, not a missing rationale. Final retain/revise/reject/defer decisions '
    'preserve current draft claims; retain does not resolve a missing explanation. Proposal history '
    'is non-active, separate from current citation uses, and unauthenticated. Historical generation '
    'claims and identities are not authenticated; current llm_used=False does not establish historical '
    'absence of AI. No model/provider invocation, external transmission, browser access, source reread, '
    'canonical update, scientific execution or automatic approval occurs. Human scientific review '
    'is still required.')


def _json(value):
    return json.dumps(value, ensure_ascii=True, allow_nan=False, sort_keys=True, indent=2) + '\n'


def _inputs(value):
    # Do not silently coerce Python tuples or non-string object keys into JSON.
    pending = [(value, 0)]
    while pending:
        item, depth = pending.pop()
        if type(item) in (dict, list):
            if depth >= MAX_CONTAINER_DEPTH:
                raise ValueError('JSON nesting exceeds supported depth')
            if isinstance(item, dict):
                if any(type(key) is not str for key in item):
                    raise ValueError('inputs must have string JSON object keys')
                children = item.values()
            else:
                children = item
            pending.extend((child, depth + 1) for child in children)
        elif item is not None and type(item) not in (str, int, float, bool):
            raise ValueError('inputs must be finite JSON data')
    try:
        raw = json.dumps(value, ensure_ascii=True, allow_nan=False).encode('utf-8')
    except (ValueError, TypeError, RecursionError) as exc:
        raise ValueError('inputs must be finite JSON data') from exc
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError('combined citation audit inputs exceed 8 MiB')
    return loads(raw)


def _bounded(output):
    if len(output.encode('utf-8')) > MAX_OUTPUT_BYTES:
        raise ValueError('citation audit output exceeds 16 MiB')
    return output


def audit(package, draft, declared_review=None):
    """Validate supplied artifacts and return detached, deterministic inventory only."""
    package, draft, declared_review = _inputs([package, draft, declared_review])
    checked, _ = _sources(package)
    inspected = (answer_draft.inspect(checked, draft) if declared_review is None else
                 answer_draft.review(checked, draft, declared_review))
    decisions = {d['claim_id']: d for d in inspected.get('review', {}).get('decisions', [])}
    claims, uses, uncited = [], [], []
    for claim in inspected['claims']:
        record = {key: copy.deepcopy(claim[key]) for key in
                  ('claim_id', 'text', 'claim_type', 'uncertainty', 'quote_check')}
        record['final_review'] = copy.deepcopy(decisions.get(claim['claim_id'],
            dict(decision='NOT_SUPPLIED', note='NOT_SUPPLIED')))
        record['citation_use_count'] = len(claim['citations'])
        record['origin'] = claim.get('origin', 'OPERATOR_SUPPLIED_DRAFT')
        if 'proposal_origin' in claim:
            record['proposal_origin'] = copy.deepcopy(claim['proposal_origin'])
        claims.append(record)
        if not claim['citations']:
            uncited.append(copy.deepcopy(record))
        for citation in claim['citations']:
            key = dict(claim_id=claim['claim_id'], reference=copy.deepcopy(citation['evidence']['reference']),
                       role=citation['role'])
            explanation = dict(key_present='explanation' in citation,
                state=citation.get('explanation_status', 'LEGACY_KEY_ABSENT'),
                origin=citation.get('explanation_origin', 'NOT_SUPPLIED'))
            if 'explanation' in citation:
                explanation['declaration'] = copy.deepcopy(citation['explanation'])
            uses.append(dict(use_key=key, citation_use_sha256=payload_sha256(key),
                claim=copy.deepcopy(record), role_origin=citation['role_origin'],
                evidence=copy.deepcopy(citation['evidence']), explanation=explanation))
    history = dict(status='NOT_SUPPLIED', active=False, counted_as_current_citation_uses=False)
    if 'proposal_review' in inspected:
        history.update(status='DECLARED_UNAUTHENTICATED_HISTORY',
            packet=copy.deepcopy(inspected['proposal_review']))
    result = dict(schema=SCHEMA,
        status='NO_CURRENT_DRAFT_CLAIMS' if not claims else
            'NO_CURRENT_CITATION_USES' if not uses else 'CITATION_REASONING_INVENTORY_NOT_VALIDATED',
        bindings=dict(package_sha256=payload_sha256(checked),
            persona_sha256=payload_sha256(checked['persona']),
            knowledge_papers_sha256=payload_sha256(checked['knowledge']['papers']),
            draft_sha256=payload_sha256(draft),
            review_sha256=None if declared_review is None else payload_sha256(declared_review)),
        question=inspected['question'], declared_operator_id=inspected['operator_id'],
        operator_identity='RECORDED_NOT_AUTHENTICATED',
        final_review=copy.deepcopy(inspected.get('review', 'NOT_SUPPLIED')),
        current_claims=claims, citation_uses=uses, uncited_claims=uncited, proposal_history=history,
        inventory=dict(scope='CURRENT_DRAFT_ONLY_COUNTS_NOT_SCORES', claims=len(claims),
            citation_uses=len(uses), uncited_claims=len(uncited),
            explanation_states={state: sum(u['explanation']['state'] == state for u in uses) for state in STATES}),
        semantic_validation='NOT_PERFORMED', llm_used=False,
        human_review_required=True, human_review_authenticated=False,
        processing=dict(scope='CURRENT_AUDIT_ONLY', provider_invoked=False, external_transmission=False,
            browser_access=False, source_reread=False, canonical_update_performed=False,
            scientific_execution=False, automatic_approval=False), boundary=BOUNDARY)
    _bounded(_json(result))
    return result


def render(result):
    """Render an already computed report; this function does not validate artifacts."""
    lines = ['Citation reasoning audit | declared interpretations only',
        'Schema: ' + display(result['schema']), 'Status: ' + display(result['status']),
        'Question: ' + display(result['question']),
        'Declared draft operator: ' + display(result['declared_operator_id']) + ' (not authenticated)',
        'Inventory counts only, not scores, completeness or approval:']
    for key in ('claims', 'citation_uses', 'uncited_claims'):
        lines.append('  ' + key + ': ' + display(result['inventory'][key]))
    for state, count in result['inventory']['explanation_states'].items():
        lines.append('  ' + display(state) + ': ' + display(count))
    for key, digest in result['bindings'].items():
        lines.append(key + ': ' + ('NOT_SUPPLIED' if digest is None else display(digest)))
    final = result['final_review']
    lines.append('Final review: ' + ('NOT_SUPPLIED' if final == 'NOT_SUPPLIED' else
        'declared reviewer ' + display(final['reviewer_id']) + ' (not authenticated)'))
    lines.append('Current draft claims and citation uses (including rejected/revised/deferred claims):')
    if not result['current_claims']:
        lines.append('  NO_CURRENT_DRAFT_CLAIMS')
    uses = {}
    for use in result['citation_uses']:
        uses.setdefault(use['use_key']['claim_id'], []).append(use)
    for claim in result['current_claims']:
        lines.append('Claim ' + display(claim['claim_id']) + ' [' + display(claim['claim_type']) + ']: ' + display(claim['text']))
        lines.append('  Origin: ' + display(claim['origin']))
        if 'proposal_origin' in claim:
            lines.append('  Adopted candidate: ' + display(claim['proposal_origin']['candidate_id']))
        lines.append('  Uncertainty: ' + ('NOT_SUPPLIED' if claim['uncertainty'] is None else display(claim['uncertainty'])))
        lines.append('  Quote check: ' + display(claim['quote_check']))
        lines.append('  Final-review decision: ' + display(claim['final_review']['decision']) +
                     '; note: ' + display(claim['final_review']['note']))
        if not uses.get(claim['claim_id']):
            lines.append('  NO_CITATIONS_SUPPLIED; no citation transfer from other claims.')
        for use in uses.get(claim['claim_id'], []):
            lines.append('  Citation use sha256: ' + display(use['citation_use_sha256']))
            lines.append('  Role: ' + display(use['use_key']['role']) + ' [' + display(use['role_origin']) + ']')
            explanation = use['explanation']
            lines.append('  Explanation: ' + display(explanation['state']) + ' [' + display(explanation['origin']) + ']')
            if explanation['key_present'] and explanation['declaration'] is not None:
                declaration = explanation['declaration']
                lines.append('    Declared rationale: ' + display(declaration['rationale']))
                lines.append('    Context boundary: ' + ('NOT_SUPPLIED (descriptive only)' if declaration['context_boundary'] is None
                             else display(declaration['context_boundary'])))
            answer_draft._render_endpoint(lines, use['evidence'])
    lines.append('Uncited current claims (separate inventory):')
    if not result['uncited_claims']:
        lines.append('  NONE')
    for claim in result['uncited_claims']:
        lines.append('  ' + display(claim['claim_id']) + ': ' + display(claim['text']))
    lines.append('Imported proposal history | NON-ACTIVE, UNAUTHENTICATED; excluded from current citation counts:')
    if 'packet' in result['proposal_history']:
        from answer_proposals import render_review
        lines.append(render_review(result['proposal_history']['packet']).rstrip('\n'))
    else:
        lines.append('  NOT_SUPPLIED (manual draft)')
    lines.append('Human scientific review required; human review not authenticated.')
    lines.append('Current audit: no model/provider, external transmission, browser, source reread, canonical update, scientific execution or automatic approval.')
    lines.append('Boundary: ' + display(result['boundary']))
    return _bounded('\n'.join(lines) + '\n')


def _load(path, budget):
    with Path(path).open('rb') as stream:
        raw = stream.read(budget + 1)
    if len(raw) > budget:
        raise ValueError('combined citation audit input files exceed 8 MiB')
    return loads(raw), len(raw)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package', type=Path)
    parser.add_argument('draft', type=Path)
    parser.add_argument('--review', type=Path)
    parser.add_argument('--format', choices=('json', 'text'), default='json')
    add_output_argument(parser); args = parser.parse_args()
    preflight(parser, getattr(args, 'output', None))
    try:
        budget = MAX_INPUT_BYTES
        package, size = _load(args.package, budget); budget -= size
        draft, size = _load(args.draft, budget); budget -= size
        declared = None
        if args.review is not None:
            declared, _ = _load(args.review, budget)
            if declared is None:
                raise ValueError('review file must contain a declared review object')
        result = audit(package, draft, declared)
        output = render(result) if args.format == 'text' else _bounded(_json(result))
    except (ValueError, OSError, KeyError, TypeError, AttributeError, RecursionError) as exc:
        parser.exit(1, str(exc) + '\n')
    emit(parser, output.encode('utf-8'), getattr(args, 'output', None))


if __name__ == '__main__':
    main()
