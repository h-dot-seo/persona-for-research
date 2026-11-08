"""Inspect a source-to-method-to-argument journey without generating or approving research."""
from answer_draft import explanation_fields

import argparse
import copy
import json
import math
import sys
from pathlib import Path

from persona import payload_sha256
from reasoning_links import _sources, _endpoint
from publication_timeline import timeline, render as render_timeline
from publication_context import for_papers
from pattern_transfer_review import inspect as inspect_transfer, render as render_transfer
from argument_map import inspect as inspect_argument, render as render_argument, _render_inspected as _render_argument_inspected
from evidence_scope import disclose, render as render_scope
from review_package import display
from strict_json import loads

INPUT_NAMES = ('package', 'patterns', 'context', 'links', 'proposal', 'draft', 'argument', 'publication_relations')
MAX_INPUT_BYTES = 8 * 1024 * 1024
MAX_OUTPUT_BYTES = 16 * 1024 * 1024
_ARGUMENT_RENDER_MAX_NODES = 8192
BOUNDARY = ('This is a mechanical review journey over supplied artifacts, not a generated answer, '
    'researcher voice, private reasoning trace, career explanation or recommended method. The topic '
    'comes from the explicit context form; matching is exact case-insensitive, not semantic retrieval. '
    'A shared exact reference connects records, not meanings. Timeline inclusion, pattern roles, '
    'context judgments, relationship bases, source stance, answer citations, design uses and argument '
    'roles remain separate. Argument routes use direct citations only; premise evidence is never '
    'inherited by a conclusion. Context-only and pattern-only evidence is not active answer/design '
    'use. Rejected and deferred claims remain visible. Publication years do not establish availability, '
    'influence, independence or changes of mind. Imported proposal histories are declarations, not '
    'authenticated model use or human review. No source reread, provenance-history replay, provider '
    'call, scientific execution, automatic approval or canonical update is performed. All conclusions '
    'and method choices still need human review; the checklist is neither exhaustive nor a score.')


def _encoded(value):
    try:
        return (json.dumps(value, ensure_ascii=True, allow_nan=False, indent=2) + '\n').encode('utf-8')
    except (ValueError, TypeError, RecursionError) as exc:
        raise ValueError('journey artifacts must be finite JSON data') from exc


def _inputs(values):
    # Detach all reports from callers and bound aggregate input before composition.
    encoded = _encoded(values)
    if len(encoded) > MAX_INPUT_BYTES:
        raise ValueError('combined journey inputs exceed 8 MiB')
    return loads(encoded.decode('utf-8'))


def encode_result(value):
    result = _encoded(value)
    if len(result) > MAX_OUTPUT_BYTES:
        raise ValueError('journey report exceeds 16 MiB; narrow supplied artifacts explicitly')
    return result


def inspect(package, patterns, context, links, proposal, draft, argument, publication_relations,
            pattern_id, declared_review=None, *, source_selection=None, source_root=None, method_applications=None):
    if (source_selection is None) != (source_root is None):
        raise ValueError('live source recheck needs both source_selection and source_root')
    supplied = dict(zip(INPUT_NAMES, (package, patterns, context, links, proposal, draft, argument,
        publication_relations)), pattern_id=pattern_id, declared_review=declared_review)
    if source_selection is not None: supplied['source_selection'] = source_selection
    if method_applications is not None: supplied['method_applications'] = method_applications
    values = _inputs(supplied)
    package, patterns, context, links, proposal, draft, argument, publication_relations = [values[k] for k in INPUT_NAMES]
    declared_review = values['declared_review']; pattern_id = values['pattern_id']
    if publication_relations is None:
        raise ValueError('supply an explicit publication relationship form, even when its relations are empty')
    transfer = inspect_transfer(package, patterns, context, links, proposal, draft, pattern_id,
        publication_relations, declared_review)
    argument_result = inspect_argument(package, draft, argument, declared_review)
    year = transfer['context_review']['reference_year']; topic = transfer['context_review']['topic']
    history = timeline(package, topic, publication_relations)
    scope = disclose(package, links, proposal, draft, year, declared_review)
    packet = transfer['answer_design_review']; answer = packet['answer']
    recorded_context_comparison = None
    if answer.get('proposal_review', {}).get('schema') == 'persona.answer-proposal-review.v3':
        recorded = answer['proposal_review']['scope']['research_context']
        current = dict(patterns=patterns, context=context, publication_relations=publication_relations, pattern_id=pattern_id)
        fields = ('patterns', 'context', 'publication_relations', 'pattern_id')
        hashes = [dict(field=field, recorded_sha256=payload_sha256(recorded[field]),
            current_sha256=payload_sha256(current[field])) for field in fields]
        changed = [row['field'] for row in hashes if row['recorded_sha256'] != row['current_sha256']]
        recorded_context_comparison = dict(
            status='DIFFERENT_SUPPLIED_ARTIFACTS' if changed else 'SAME_RECORDED_ARTIFACTS',
            changed_fields=changed, artifacts=hashes,
            scope='LOGICAL_JSON_INPUTS_NOT_SOURCE_BYTES_OR_SEMANTIC_JUDGMENTS',
            both_contexts_preserved=True, automatic_rebinding=False, model_use_verified=False,
            boundary='Recorded answer-preparation/import context and current journey review inputs remain separate. '
                'Different hashes do not establish conflicting judgments, supersession or invalidity. '
                'Equal hashes do not prove model use, applicability or approval. No citation scope changes.')
    relations = transfer['publication_context_review']
    _, papers = _sources(package)
    application_review = None
    if method_applications is not None:
        from method_application import inspect as inspect_applications
        application_review = inspect_applications(package, patterns, context, links, proposal, pattern_id, values['method_applications'])
    routes = {}

    def route(node):
        ref = node['reference']; key = payload_sha256(ref)
        if key not in routes:
            routes[key] = dict(reference_sha256=key, evidence=copy.deepcopy(node),
                publication_scope=('AFTER_REFERENCE_YEAR' if node['publication_year'] > year else
                    'SAME_YEAR_ORDER_UNRESOLVED' if node['publication_year'] == year else 'BEFORE_REFERENCE_YEAR'),
                in_topic_timeline=False, pattern_roles=[], pattern_evidence_uses=[],
                context_uses=[], publication_relationship_basis_uses=[], answer_uses=[], design_uses=[],
                unused_link_uses=[], direct_argument_uses=[])
        return routes[key]

    for group in history['years']:
        for paper in group['papers']:
            for obs in paper['observations']:
                for dimension in [None, *obs['reasoning']]:
                    ref = dict(paper_id=paper['paper_id'], observation_index=obs['observation_index'], dimension=dimension)
                    route(_endpoint(ref, papers))['in_topic_timeline'] = True
    for row in transfer['evidence_routes']:
        r = route(row['evidence']); r['pattern_roles'] = copy.deepcopy(row['pattern_roles'])
        r['pattern_evidence_uses'] = copy.deepcopy(row.get('pattern_evidence_uses', []))
    for row in transfer['context_review']['assessments']:
        ref = row['evidence']['reference']
        route(row['evidence'])['context_uses'].append(dict(role='assessment', decision=row['decision'], reference=copy.deepcopy(ref)))
        for counter in row['counterevidence']:
            route(counter['evidence'])['context_uses'].append(dict(role='counterevidence', for_reference=copy.deepcopy(ref)))
    for row in relations['relations']:
        for node in row['basis_evidence']:
            route(node)['publication_relationship_basis_uses'].append(dict(relation_id=row['relation_id'],
                relation_type=row['relation_type'], role='OPERATOR_DECLARED_RELATIONSHIP_BASIS_NOT_ACTIVE_USE'))
    for row in packet['evidence_routes']:
        r = route(row['evidence'])
        for source, target in [('answer_uses', 'answer_uses'), ('design_uses', 'design_uses'), ('unreferenced_link_uses', 'unused_link_uses')]:
            r[target] = copy.deepcopy(row[source])
    claims = {claim['claim_id']: claim for claim in answer['claims']}
    decisions = {d['claim_id']: d['decision'] for d in answer.get('review', {}).get('decisions', [])}
    for step in argument_result['steps']:
        for role, ids in [('premise', step['premise_claim_ids']), ('conclusion', [step['conclusion_claim_id']])]:
            for claim_id in ids:
                for citation in claims[claim_id]['citations']:
                    route(citation['evidence'])['direct_argument_uses'].append(dict(step_id=step['step_id'],
                        claim_id=claim_id, argument_role=role, citation_role=citation['role'],
                        declared_review_decision=decisions.get(claim_id, 'NOT_SUPPLIED'), **explanation_fields(citation)))
    for row in routes.values():
        row['actively_used_in_answer_or_design'] = bool(row['answer_uses'] or row['design_uses'])
        for use in row['answer_uses']:
            use['declared_review_decision'] = decisions.get(use['claim_id'], 'NOT_SUPPLIED')
    ordered = sorted(routes.values(), key=lambda row: (row['evidence']['publication_year'],
        row['evidence']['reference']['paper_id'], row['evidence']['reference']['observation_index'],
        row['evidence']['reference']['dimension'] or ''))
    active_ids = sorted({row['evidence']['reference']['paper_id'] for row in ordered if row['actively_used_in_answer_or_design']})
    active_context = for_papers(relations, active_ids, year)
    agenda = []

    def prompt(domain, code, **target):
        agenda.append(dict(domain=domain, code=code, **copy.deepcopy(target)))

    if recorded_context_comparison is not None and recorded_context_comparison['changed_fields']:
        prompt('answer_preparation_context', 'DIFFERENT_SUPPLIED_CONTEXT_ARTIFACTS',
            changed_fields=recorded_context_comparison['changed_fields'])
    if not history['years']: prompt('timeline', 'NO_TOPIC_MATCHING_RECORDS')
    for dimension in history['missing_dimensions']: prompt('timeline', 'REASONING_DIMENSION_NOT_SUPPLIED', dimension=dimension)
    for code in transfer['selected_pattern_review_prompts']: prompt('pattern', code, pattern_id=pattern_id)
    for row in transfer['trace_review_prompts']: prompt('pattern_transfer', **row)
    for row in packet['review_prompts']: prompt('answer_design', **row)
    for row in transfer['context_review']['assessments']:
        ref = row['evidence']['reference']
        if row['decision'] == 'defer': prompt('context', 'CONTEXT_DECISION_DEFERRED', reference=ref)
        for field in row['missing_fields']: prompt('context', 'NOT_SUPPLIED', reference=ref, field=field)
    if not relations['relations']: prompt('publication_context', 'NO_DECLARED_RELATIONSHIPS_INDEPENDENCE_NOT_ESTABLISHED')
    # Full relationship inventory, including context outside the selected pattern/topic.
    timed = for_papers(relations, list(papers), year)
    for row in timed['relations_between_selected_papers']:
        for code in row['review_prompts']: prompt('publication_context', code, relation_id=row['relation_id'])
    if not argument_result['steps']: prompt('argument', 'NO_DECLARED_ARGUMENT_STEPS')
    for claim_id in argument_result['unmapped_claim_ids']: prompt('argument', 'UNMAPPED_CLAIM', claim_id=claim_id)
    for step in argument_result['steps']:
        for field in step['missing_fields']: prompt('argument', 'NOT_SUPPLIED', step_id=step['step_id'], field=field)
        for role, nodes in [('premise', step['premises']), ('conclusion', [step['conclusion']])]:
            for node in nodes:
                if not node['direct_citation_count']:
                    prompt('argument', 'NO_DIRECT_CITATIONS_CITATION_TRANSFER_NOT_PERFORMED', step_id=step['step_id'], claim_id=node['claim_id'], argument_role=role)
                if node['declared_review_decision'] != 'retain':
                    prompt('argument', 'DECLARED_' + node['declared_review_decision'].upper(), step_id=step['step_id'], claim_id=node['claim_id'], argument_role=role)
    bindings = {name + '_sha256': payload_sha256(value) for name, value in values.items() if name != 'pattern_id'}
    bindings['pattern_id'] = pattern_id
    result = dict(schema='persona.research-journey.v1', status='HUMAN_REVIEW_REQUIRED_NOT_RESEARCH_APPROVAL',
        question=packet['question'], topic=topic, reference_year=year, selected_pattern_id=pattern_id,
        bindings=bindings, journey_input_sha256=payload_sha256(bindings),
        answer_review_status=answer['status'] if declared_review is not None else 'NOT_SUPPLIED',
        trajectory_review=history, pattern_transfer_review=transfer, argument_review=argument_result,
        evidence_scope=scope, active_publication_context=active_context, evidence_routes=ordered,
        review_agenda=agenda, route_scope='UNION_OF_SUPPLIED_REVIEW_ROUTES_NOT_COMPLETE_CORPUS_OR_LITERATURE',
        agenda_scope='MECHANICAL_PROMPTS_NOT_EXHAUSTIVE_NOT_A_SCORE',
        source_reread=False, provider_invoked=False, llm_used=False, external_transmission=False,
        execution_scope='CURRENT_COMPOSITION_ONLY', historical_model_use='NOT_DETERMINED_BY_CURRENT_EXECUTION_FLAGS',
        provenance_history_replay='NOT_PERFORMED', human_review_authenticated=False,
        scientific_validation='NOT_PERFORMED', researcher_fidelity_evaluation='NOT_PERFORMED',
        automatic_approval=False, scientific_execution=False, canonical_update_performed=False, boundary=BOUNDARY)
    if recorded_context_comparison is not None:
        result['recorded_answer_context_comparison'] = recorded_context_comparison
    if application_review is not None:
        by_reference = {row['reference_sha256']: row for row in result['evidence_routes']}
        for row in result['evidence_routes']: row['method_application_uses'] = []
        for application in application_review['applications']:
            for basis in application['evidence']:
                by_reference[payload_sha256(basis['evidence']['reference'])]['method_application_uses'].append(
                    dict(step_id=application['step_id'], decision=application['decision'],
                        proposed_role=application['proposed_role'], claim_type='operator_interpretation',
                        scope='DECLARED_APPLICATION_BASIS_NOT_ACTIVE_ANSWER_OR_DESIGN_USE'))
        result['review_agenda'].extend(dict(domain='method_application', **copy.deepcopy(prompt)) for prompt in application_review['review_prompts'])
        result.update(method_application_review=application_review,
            method_application_scope='DECLARED_PATTERN_TO_STEP_INTENT_NOT_EXECUTION_OR_CITATION_TRANSFER')
    encode_result(result)
    if source_selection is not None:
        from source_recheck import audit as recheck_sources
        current = recheck_sources(package, values['source_selection'], source_root)
        by_ref = {payload_sha256(row['reference']): row for paper in current['papers'] for row in paper['records']}
        for row in result['evidence_routes']:
            row['current_source_recheck'] = copy.deepcopy(by_ref[row['reference_sha256']])
        result['review_agenda'].extend(dict(domain='current_source_recheck', **copy.deepcopy(gap))
            for gap in current['quote_gaps'] + current['source_review_prompts'])
        result.update(source_recheck=current, source_reread=True,
            source_recheck_scope='ALL_SUPPLIED_PAPERS_AND_STORED_QUOTES_NOT_ONLY_ACTIVE_ROUTES',
            current_checks_replace_recorded_labels=False,
            boundary=BOUNDARY.replace('No source reread, provenance-history replay, provider',
                'Selected local files were reread in the separate current source check; historical subreport labels remain unchanged. No provenance-history replay, provider'))
        encode_result(result)
    return result


def _argument_render_reusable(result, package, draft, argument, declared_review):
    """Conservatively match current raw inputs to this call's fresh inspection.

    JSON normalization can change raw validation behavior. Ineligible inputs use
    the original renderer, never a new rejection. This is not a concurrency lock.
    """
    values = dict(package=package, draft=draft, argument=argument, declared_review=declared_review)
    seen = set()
    pending = [(value, 0) for value in values.values()]
    remaining = _ARGUMENT_RENDER_MAX_NODES - len(pending)
    try:
        while pending:
            value, depth = pending.pop()
            kind = type(value)
            if kind is str:
                if any(0xD800 <= ord(char) <= 0xDFFF for char in value):
                    return False
            elif kind is float:
                if not math.isfinite(value): return False
            elif kind is type(None) or kind is bool or kind is int:
                pass
            elif kind is dict or kind is list:
                # A deliberately conservative depth/alias bound, not a new input limit.
                if depth >= 64 or id(value) in seen: return False
                seen.add(id(value))
                # Count keys as well as values before allocating any child entries.
                # This bounds optimization work only; larger inputs use the raw path.
                children = len(value) * (2 if kind is dict else 1)
                if children > remaining: return False
                remaining -= children
                if kind is dict:
                    if any(type(key) is not str for key in value): return False
                    pending.extend((key, depth + 1) for key in value)
                    pending.extend((child, depth + 1) for child in value.values())
                else:
                    pending.extend((child, depth + 1) for child in value)
            else:
                return False
        return all(payload_sha256(value) == result['bindings'][name + '_sha256']
                   for name, value in values.items())
    except (ValueError, TypeError, KeyError, RuntimeError, RecursionError, OverflowError):
        return False


def render(package, patterns, context, links, proposal, draft, argument, publication_relations,
           pattern_id, declared_review=None, *, source_selection=None, source_root=None, method_applications=None):
    result = inspect(package, patterns, context, links, proposal, draft, argument, publication_relations, pattern_id, declared_review,
        source_selection=source_selection, source_root=source_root, method_applications=method_applications)
    lines = ['Source-to-method-to-argument review journey', 'Status: ' + result['status'],
        'Question: ' + display(result['question']), 'Topic: ' + display(result['topic']),
        'Reference year: ' + str(result['reference_year']), 'Journey input sha256: ' + result['journey_input_sha256'],
        'Declared answer review: ' + result['answer_review_status'] + ' (not authenticated approval)', result['boundary'],
        'Review agenda (domain-specific prompts, not severity ranks or a readiness score):']
    if 'recorded_answer_context_comparison' in result:
        comparison = result['recorded_answer_context_comparison']
        lines.insert(6, 'Recorded answer-preparation context versus current review: '+comparison['status']+
            '; changed logical inputs='+(', '.join(comparison['changed_fields']) or 'none')+'. '+comparison['boundary'])
    if 'method_application_review' in result:
        lines.insert(6, 'Declared method application: ' + result['method_application_review']['status'] + ' (proposed checks are not executed)')
    if 'source_recheck' in result:
        lines.insert(6, 'Current local source recheck: ' + result['source_recheck']['status'] + ' (separate from recorded historical labels)')
    for row in result['review_agenda']:
        lines.append('  ' + row['domain'] + ': ' + row['code'] + ' | ' +
            display(json.dumps({key: value for key, value in row.items() if key not in ('domain', 'code')}, ensure_ascii=True)))
    if not result['review_agenda']: lines.append('  None detected; human review and scientific validation still required.')
    lines.append('Exact-reference journey index (context inclusion is not evidence use):')
    for row in result['evidence_routes']:
        ref = row['evidence']['reference']
        lines.append('  ' + display(ref['paper_id']) + ' / ' + str(ref['observation_index']) + ' / ' + display(ref['dimension']) +
            ' | ' + row['publication_scope'] + '; topic timeline=' + str(row['in_topic_timeline']) +
            '; active answer/design=' + str(row['actively_used_in_answer_or_design']))
        if 'current_source_recheck' in row:
            lines.append('    Current local quote check: ' + row['current_source_recheck']['quote_status'] +
                '; locator=' + row['current_source_recheck']['locator_status'])
        lines.append('    Pattern roles: ' + (', '.join(row['pattern_roles']) or 'none supplied'))
        for use in row.get('method_application_uses', []):
            lines.append('    Declared application basis (not active evidence): ' + display(json.dumps(use, ensure_ascii=True)))
        for field in ('context_uses', 'publication_relationship_basis_uses', 'answer_uses', 'design_uses', 'unused_link_uses', 'direct_argument_uses'):
            for use in row[field]: lines.append('    ' + field + ': ' + display(json.dumps(use, ensure_ascii=True)))
    lines.extend(['Full trajectory and declared publication context:', render_timeline(package, result['topic'], publication_relations).rstrip('\n'),
        'Full pattern, target context and answer/design review (all supplied decisions retained):',
        render_transfer(package, patterns, context, links, proposal, draft, pattern_id, publication_relations, declared_review).rstrip('\n'),
        'Full operator argument map (no premise-to-conclusion citation transfer):',
        (_render_argument_inspected(result['argument_review'])
         if _argument_render_reusable(result, package, draft, argument, declared_review)
         else render_argument(package, draft, argument, declared_review)).rstrip('\n'),
        'Full reader evidence-scope disclosure:', render_scope(package, links, proposal, draft, result['reference_year'], declared_review).rstrip('\n')])
    if 'method_application_review' in result:
        from method_application import render as render_applications
        lines.extend(['Full declared method-pattern application intent:',
            render_applications(package, patterns, context, links, proposal, pattern_id, method_applications).rstrip('\n')])
    if 'source_recheck' in result:
        from source_recheck import render as render_source_recheck
        lines.extend(['Full current local source recheck, including unused papers:', render_source_recheck(result['source_recheck']).rstrip('\n')])
    output = '\n'.join(lines) + '\n'
    if len(output.encode('utf-8')) > MAX_OUTPUT_BYTES: raise ValueError('journey report exceeds 16 MiB; narrow supplied artifacts explicitly')
    return output


def _load(path):
    with Path(path).open('rb') as stream: raw = stream.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES: raise ValueError('journey input file exceeds 8 MiB')
    return loads(raw.decode('utf-8'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in INPUT_NAMES: parser.add_argument(name, type=Path)
    parser.add_argument('--pattern-id', required=True); parser.add_argument('--review', type=Path)
    parser.add_argument('--source-selection', type=Path); parser.add_argument('--source-root', type=Path)
    parser.add_argument('--method-applications', type=Path)
    parser.add_argument('--format', choices=('json', 'text', 'html'), default='json'); args = parser.parse_args()
    try:
        values = [_load(getattr(args, name)) for name in INPUT_NAMES] + [args.pattern_id, _load(args.review) if args.review else None]
        if (args.source_selection is None) != (args.source_root is None):
            raise ValueError('live source recheck needs both --source-selection and --source-root')
        options = dict(source_selection=_load(args.source_selection) if args.source_selection else None, source_root=args.source_root,
            method_applications=_load(args.method_applications) if args.method_applications else None)
        if args.format == 'html':
            from journey_html import render as render_html
            output = render_html(*values, **options).encode('utf-8')
        else:
            output = render(*values, **options).encode('utf-8') if args.format == 'text' else encode_result(inspect(*values, **options))
    except (ValueError, OSError, KeyError, TypeError, AttributeError, RecursionError) as exc:
        parser.exit(1, str(exc) + '\n')
    sys.stdout.buffer.write(output)


if __name__ == '__main__': main()
