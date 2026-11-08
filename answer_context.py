"""Inspect explicit research context before an answer, without selecting citation sources.

Imports of review modules are deliberately lazy: their renderers depend on answer_draft.
"""
import copy
import json
import math

MAX_INPUT_BYTES = 8 * 1024 * 1024
MAX_OUTPUT_BYTES = 16 * 1024 * 1024
SCHEMA = 'persona.answer-research-context.v1'
BOUNDARY = ('Inspected context is not approved evidence, researcher thoughts or endorsement. '
    'Only the caller-selected exact evidence_refs are citable; context quotes, component siblings, '
    'parent observations, relationship bases and selected/unselected/rejected pattern references '
    'never expand that scope. Other-topic, unselected and rejected history remains context-only, '
    'not relevant, approved or citable by inclusion. Consider/exclude/defer attaches only to the '
    'enclosing observation; component semantic approval is not inherited. Exclude does not ban '
    'citation for criticism. Context exposure proves neither model use nor method applicability, '
    'author ownership, historical influence, availability, career, private beliefs or independence. '
    'Identities and imported generation/review histories are unauthenticated declarations; current '
    'execution flags say nothing about historical model use. Recorded source checks are not reread. '
    'No provider, browser, external transmission, scientific execution, automatic approval or '
    'canonical update is performed. Human review and scientific validation remain required.')


def _encoded(value):
    """Reject non-JSON Python values rather than silently coercing keys or tuples."""
    pending = [(value, 0)]
    while pending:
        item, depth = pending.pop()
        if type(item) in (dict, list):
            if depth >= 128:
                raise ValueError('research context JSON nesting exceeds supported depth')
            if type(item) is dict:
                if any(type(key) is not str for key in item):
                    raise ValueError('research context JSON object keys must be strings')
                children = item.values()
            else:
                children = item
            pending.extend((child, depth + 1) for child in children)
        elif type(item) not in (str, int, float, bool, type(None)):
            raise ValueError('research context must contain strict JSON data')
        elif type(item) is float and not math.isfinite(item):
            raise ValueError('research context must contain finite JSON data')
    try:
        return (json.dumps(value, ensure_ascii=True, allow_nan=False, indent=2) + '\n').encode('utf-8')
    except (ValueError, TypeError, RecursionError, UnicodeError) as exc:
        raise ValueError('research context must contain finite JSON data') from exc


def encode_result(result):
    encoded = _encoded(result)
    if len(encoded) > MAX_OUTPUT_BYTES:
        raise ValueError('research context report exceeds 16 MiB; narrow inputs explicitly')
    return encoded


def _timing(year, reference_year):
    return ('AFTER_REFERENCE_YEAR' if year > reference_year else
            'SAME_YEAR_ORDER_UNRESOLVED' if year == reference_year else 'BEFORE_REFERENCE_YEAR')


def inspect(package, raw, question, topic, reference_year, evidence_refs):
    from strict_json import loads
    from persona import payload_sha256
    from reasoning_links import _sources, _endpoint
    from pattern_hypotheses import inspect as inspect_patterns
    from applicability_review import inspect as inspect_context
    from publication_context import inspect as inspect_relations, for_papers
    from publication_timeline import timeline

    supplied = dict(package=package, raw=raw, question=question, topic=topic,
                    reference_year=reference_year, evidence_refs=evidence_refs)
    encoded = _encoded(supplied)
    if len(encoded) > MAX_INPUT_BYTES:
        raise ValueError('combined research context inputs exceed 8 MiB')
    values = loads(encoded.decode('utf-8'))
    package, raw = values['package'], values['raw']
    question, topic, reference_year = values['question'], values['topic'], values['reference_year']
    evidence_refs = values['evidence_refs']
    if type(raw) is not dict or set(raw) != {'patterns', 'context', 'publication_relations', 'pattern_id'}:
        raise ValueError('research context needs exactly patterns, context, publication_relations and pattern_id raw forms')
    for name, value in [('question', question), ('topic', topic), ('pattern_id', raw['pattern_id'])]:
        if type(value) is not str or not value.strip():
            raise ValueError(name + ' must be nonblank text')
    if type(reference_year) is not int or not 1 <= reference_year <= 9999:
        raise ValueError('reference_year must be an integer from 1 to 9999')
    if type(evidence_refs) is not list or len(evidence_refs) > 64:
        raise ValueError('evidence_refs must be an explicit array of 0 to 64 exact references')
    package, papers = _sources(package)
    seen = set()
    for ref in evidence_refs:
        _endpoint(ref, papers)
        digest = payload_sha256(ref)
        if digest in seen:
            raise ValueError('evidence_refs must contain unique exact references')
        seen.add(digest)
    context = raw['context']
    if type(context) is not dict or any(context.get(k) != v for k, v in
            [('question', question), ('topic', topic), ('reference_year', reference_year)]):
        raise ValueError('raw context question/topic/reference_year must match answer bindings exactly')
    pattern_review = inspect_patterns(package, raw['patterns'])
    selected = [p for p in pattern_review['hypotheses'] if p['pattern_id'] == raw['pattern_id']]
    if len(selected) != 1:
        raise ValueError('select exactly one existing adopted or manual operator pattern ID')
    selected = selected[0]
    context_review = inspect_context(package, context)
    relations = inspect_relations(package, raw['publication_relations'])
    history = timeline(package, topic)  # Never request the unscoped relation projection.
    assessments = {(r['evidence']['reference']['paper_id'], r['evidence']['reference']['observation_index']): r
                   for r in context_review['assessments']}
    routes = []
    for route in selected['evidence']:
        node = route['evidence']; ref = node['reference']; digest = payload_sha256(ref)
        assessment = assessments.get((ref['paper_id'], ref['observation_index']))
        prompts = []
        if assessment is None:
            prompts.append('NO_ENCLOSING_OBSERVATION_CONTEXT_ASSESSMENT')
        else:
            if assessment['decision'] == 'defer': prompts.append('CONTEXT_DECISION_DEFERRED')
            for field in assessment['missing_fields']:
                prompts.append(field.upper() + '_NOT_SUPPLIED')
        timing = _timing(node['publication_year'], reference_year)
        if timing != 'BEFORE_REFERENCE_YEAR': prompts.append(timing)
        uses = copy.deepcopy(route.get('evidence_uses', []))
        if any(use.get('context_boundary') is None for use in uses):
            prompts.append('PATTERN_EVIDENCE_USE_CONTEXT_BOUNDARY_NOT_SUPPLIED')
        routes.append(dict(reference_sha256=digest, evidence=copy.deepcopy(node),
            pattern_roles=copy.deepcopy(route['declared_roles']), pattern_evidence_uses=uses,
            pattern_reason_status='DECLARED_REASONS_NOT_VALIDATED' if uses else 'NOT_SUPPLIED',
            context_assessment=copy.deepcopy(assessment),
            context_decision=assessment['decision'] if assessment else 'NOT_SUPPLIED',
            context_match_basis='ENCLOSING_OBSERVATION_ONLY' if assessment else 'NONE',
            component_approval_inherited=False, citation_prohibited_by_exclude=False,
            declared_context_counterevidence_for=[copy.deepcopy(row['evidence']['reference'])
                for row in context_review['assessments'] if any(
                    payload_sha256(counter['evidence']['reference']) == digest for counter in row['counterevidence'])],
            publication_scope=timing, explicitly_selected_for_answer_citation=digest in seen,
            review_prompts=prompts))
    bindings = dict(package_sha256=payload_sha256(package), raw_sha256=payload_sha256(raw),
        pattern_form_sha256=payload_sha256(raw['patterns']), context_form_sha256=payload_sha256(context),
        publication_relation_form_sha256=payload_sha256(raw['publication_relations']),
        pattern_id=raw['pattern_id'], question=question, topic=topic, reference_year=reference_year,
        evidence_refs_sha256=payload_sha256(evidence_refs))
    answer_ids = sorted({ref['paper_id'] for ref in evidence_refs})
    pattern_ids = sorted({r['evidence']['reference']['paper_id'] for r in selected['evidence']})
    topic_ids = [p['paper_id'] for group in history['years'] for p in group['papers']]
    result = dict(schema=SCHEMA, status='INSPECTED_NOT_APPROVED_RESEARCH_CONTEXT',
        question=question, topic=topic, reference_year=reference_year, selected_pattern_id=raw['pattern_id'],
        bindings=bindings, report_input_sha256=payload_sha256(bindings),
        evidence_refs=copy.deepcopy(evidence_refs),
        citable_scope=dict(scope='CALLER_EXPLICIT_EXACT_REFERENCES_ONLY', evidence_refs=copy.deepcopy(evidence_refs),
            evidence_refs_sha256=payload_sha256(evidence_refs), reference_sha256=[payload_sha256(r) for r in evidence_refs],
            context_expands_citation_scope=False, context_quote_requires_explicit_exact_reference=True),
        selected_pattern=copy.deepcopy(selected), pattern_review=pattern_review, context_review=context_review,
        publication_timeline=history, publication_context_review=relations,
        answer_citation_publication_scope=for_papers(relations, answer_ids, reference_year),
        selected_pattern_publication_scope=for_papers(relations, pattern_ids, reference_year),
        topic_publication_scope=for_papers(relations, topic_ids, reference_year),
        selected_pattern_context_routes=routes,
        human_review_required=True, human_review_authenticated=False,
        scientific_validation='NOT_PERFORMED', semantic_validation='NOT_PERFORMED',
        source_reread=False, provider_invoked=False, browser_used=False, llm_used=False,
        external_transmission=False, canonical_update_performed=False, scientific_execution=False,
        automatic_approval=False, source_selection_performed=False,
        execution_scope='CURRENT_INSPECTION_ONLY', historical_model_use='NOT_DETERMINED_BY_CURRENT_EXECUTION_FLAGS',
        boundary=BOUNDARY)
    # Return a fully detached report, including structures shared by subordinate reports.
    return loads(encode_result(result).decode('utf-8'))


def render(result):
    from strict_json import loads
    from review_package import display
    from pattern_hypotheses import render as render_patterns
    from applicability_review import render as render_context
    from publication_context import render as render_relations
    result = loads(encode_result(result).decode('utf-8'))
    if type(result) is not dict or result.get('schema') != SCHEMA:
        raise ValueError('expected an inspected answer research context report')
    lines = ['Answer research context | inspected, not approved',
        'Status: ' + display(result['status']), 'Question: ' + display(result['question']),
        'Topic: ' + display(result['topic']), 'Reference year: ' + str(result['reference_year']),
        'Selected pattern: ' + display(result['selected_pattern_id']), BOUNDARY,
        'Full pattern inspection, including unselected and rejected history (context only):',
        render_patterns(result['pattern_review']).rstrip('\n'),
        'Full applicability inspection, including excluded/deferred assessments and counterevidence:',
        render_context(result['context_review']).rstrip('\n'),
        'Full publication relationship inspection (not citation selection):',
        render_relations(result['publication_context_review']).rstrip('\n')]
    # Preserve every field not already rendered, especially scoped relations and route reasons.
    # ASCII JSON plus display escaping prevents controls, bidi and formatting spoofing.
    appendix = {k: v for k, v in result.items() if k not in
                ('pattern_review', 'context_review', 'publication_context_review', 'selected_pattern', 'boundary')}
    lines.extend(['Full chronology, exact citation scope, selected context routes, three publication scopes and bindings:',
                  '\n'.join(display(line) for line in json.dumps(appendix, ensure_ascii=True, allow_nan=False, indent=2).splitlines())])
    output = '\n'.join(lines) + '\n'
    if len(output.encode('utf-8')) > MAX_OUTPUT_BYTES:
        raise ValueError('research context text exceeds 16 MiB; narrow inputs explicitly')
    return output
