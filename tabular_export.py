"""Export freshly checked package references as private, non-authoritative CSV or TSV."""
import argparse
import csv
import io
import json
from pathlib import Path

from exclusive_output import add_output_argument, emit, preflight
from observation_provenance import KEY as OBSERVATION_ORIGIN
from persona import payload_sha256
from reasoning_cards import DIMENSIONS
from reasoning_links import _endpoint, _sources
from review_package import display
from strict_json import load

MAX_INPUT_BYTES = 8 * 1024 * 1024
MAX_OUTPUT_BYTES = 16 * 1024 * 1024
MAX_CELL_CHARS = 32767
NOT_SUPPLIED = 'NOT_SUPPLIED (null)'
NOT_APPLICABLE = 'NOT_APPLICABLE'
EMPTY_STRING = 'EMPTY_STRING'
CATALOG_SCOPE = ('All supplied observations/components, not a relevance ranking or recommendation. '
                 'Quotes and private input fields may be present.')
BOUNDARY = (CATALOG_SCOPE + ' Private local display, not permission to share. No source reread, '
            'semantic validation, identity inference, authorization or canonical update. '
            'Recorded checks are historical, not renewed verification. Controls are escaped and '
            "formula-like cells receive a leading apostrophe; JSON remains authoritative. "
            'CSV/TSV is not input to any tool here; pivots and averages are not scores. '
            'References are package-bound positions, not stable cross-build identities.')
OBS_FIELDS = ('topic', 'method', 'condition', 'limitation', 'locator', 'stance', 'claim_type', 'evidence_quote')
COMP_FIELDS = ('claim_type', 'text', 'locator', 'evidence_quote', 'origin', 'proposed_claim_type')
COLUMNS = ('row_kind', 'paper_id', 'observation_index', 'dimension', 'reference_json',
           'source_kind', 'publication_year', 'source_sha256', 'source_locator', 'recorded_source_check',
           *('observation_' + key for key in OBS_FIELDS), 'observation_quote_check',
           *('component_' + key for key in COMP_FIELDS), 'component_quote_check',
           'has_observation_origin', 'missing_reasoning_dimensions', 'attribution',
           'persona_sha256', 'knowledge_papers_sha256', 'boundary')
OMITTED = ('persona metadata, rules and validation-axis declarations',
           'package wrapper/application/boundary metadata',
           'paper title, source_file, split and other paper metadata not named in columns',
           'observation-origin contents (presence only)',
           'component review fields beyond origin/proposed_claim_type',
           'all fields not explicitly named by the fixed columns')

AGENDA_COLUMNS = ('domain', 'code', 'target_json', 'journey_input_sha256', 'status',
                  'input_card_sha256', 'source_reread', 'boundary')
AGENDA_BOUNDARY = ('Private local display, not permission to share. This agenda is neither exhaustive '
                   'nor a score or approval. Controls are escaped and formula-like cells receive a '
                   'leading apostrophe; JSON remains authoritative. CSV/TSV is not input to any tool '
                   'here; pivots and averages are not scores. No provider call or write-back occurs. '
                   'Source reread requires both an explicitly selected source form and source root.')
AGENDA_OMITTED = ('all nested reports and evidence routes', 'question, topic and reference year',
                  'full artifact-file verification records (card hash retained)',
                  'all fields outside review_agenda except the listed binding/status/source flag columns')


ROUTE_USES = ('pattern_evidence_uses', 'context_uses', 'publication_relationship_basis_uses',
              'answer_uses', 'design_uses', 'unused_link_uses', 'direct_argument_uses')
ROUTE_COLUMNS = ('row_kind', 'paper_id', 'observation_index', 'dimension', 'reference_json',
    'reference_sha256', 'evidence_json', 'source_kind', 'publication_year', 'source_sha256',
    'source_locator', 'recorded_source_check',
    *('observation_' + key for key in OBS_FIELDS), 'observation_quote_check',
    *('component_' + key for key in COMP_FIELDS), 'component_quote_check',
    'has_observation_origin', 'attribution', 'publication_scope', 'in_topic_timeline',
    'actively_used_in_answer_or_design', 'pattern_roles_json',
    *(column for name in ROUTE_USES for column in (name + '_count', name + '_json')))
ROUTE_TRAILER = ('journey_input_sha256', 'input_card_sha256', 'status', 'source_reread', 'boundary')
ROUTE_BOUNDARY = ('Private route display, not permission to share. Routes are the union of supplied review '
    'routes, not the complete corpus or literature, a ranking, recommendation or approval. Observation and '
    'component labels remain separate. Counts, pivots and averages are not scores. Controls are escaped '
    'and formula-like cells receive a leading apostrophe; exact JSON remains authoritative. CSV/TSV is '
    'not input to any tool here. No provider call or write-back. Current source reread requires the '
    'explicit pinned selection and supplied root; recorded labels are not renewed verification.')
ROUTE_OMITTED = ('nested journey reports, full artifact-file checks, question/topic/reference year',
    'package metadata and complete corpus outside the supplied route union',
    'route fields outside the documented columns; evidence and each listed use retain complete JSON')


def route_columns(method_applications=False, source_recheck=False):
    if type(method_applications) is not bool or type(source_recheck) is not bool:
        raise ValueError('route column options must be boolean')
    return (ROUTE_COLUMNS +
            (('method_application_uses_count', 'method_application_uses_json') if method_applications else ()) +
            (('current_source_recheck_json',) if source_recheck else ()) + ROUTE_TRAILER)


def _compact(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':'))


def cell(value):
    """Display first, guard second; reject rather than truncate a rendered cell."""
    if value is None:
        text = NOT_SUPPLIED
    elif value == '':
        text = EMPTY_STRING
    elif isinstance(value, (dict, list, bool)):
        text = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':'))
    else:
        text = str(value)
    text = display(text)
    if text.startswith(('=', '+', '-', '@')):
        text = "'" + text
    if len(text) > MAX_CELL_CHARS:
        raise ValueError('tabular cell exceeds 32767 characters; narrow supplied artifacts explicitly')
    return text


def describe(table='reference-catalog'):
    if table == 'evidence-routes':
        from journey_inputs import MAX_CARD_BYTES, MAX_ARTIFACT_BYTES
        return dict(schema='persona.tabular-description.v1', table=table,
            input='explicit bound journey CARD plus input-root, never a saved report',
            column_sets=[dict(method_applications=method, source_selection=source,
                             columns=list(route_columns(method, source)))
                         for method, source in ((False,False),(True,False),(False,True),(True,True))],
            option_selection='Column sets follow non-null pinned method_applications/source_selection card slots, not row contents.',
            omitted_fields=list(ROUTE_OMITTED), row_order='fresh journey evidence_routes order; one row per route',
            empty='header only using the selected option columns; not review completion or approval',
            markers=dict(null=NOT_SUPPLIED, not_applicable=NOT_APPLICABLE, empty_string=EMPTY_STRING),
            marker_boundary='Display markers can collide with literal strings; exact evidence/use JSON preserves null, absence and false.',
            max_card_bytes=MAX_CARD_BYTES, max_combined_artifact_bytes=MAX_ARTIFACT_BYTES,
            max_output_bytes=MAX_OUTPUT_BYTES, max_cell_chars=MAX_CELL_CHARS, boundary=ROUTE_BOUNDARY)
    if table == 'review-agenda':
        from journey_inputs import MAX_CARD_BYTES, MAX_ARTIFACT_BYTES
        return dict(schema='persona.tabular-description.v1', table=table,
                    input='explicit bound journey CARD plus input-root, never a saved report',
                    columns=list(AGENDA_COLUMNS), omitted_fields=list(AGENDA_OMITTED),
                    row_order='fresh journey review_agenda order; no sort, deduplication or ranking',
                    empty='header only; no rows is not review completion or approval',
                    markers=dict(null=NOT_SUPPLIED, not_applicable=NOT_APPLICABLE, empty_string=EMPTY_STRING),
                    marker_boundary='Display markers are not a reversible encoding; literal strings may collide.',
                    max_card_bytes=MAX_CARD_BYTES, max_combined_artifact_bytes=MAX_ARTIFACT_BYTES,
                    max_output_bytes=MAX_OUTPUT_BYTES, max_cell_chars=MAX_CELL_CHARS,
                    boundary=AGENDA_BOUNDARY)
    if table != 'reference-catalog':
        raise ValueError('unsupported table')
    return dict(schema='persona.tabular-description.v1', table='reference-catalog',
                input='freshly checked bound PACKAGE, not a saved reference catalog or report',
                columns=list(COLUMNS), omitted_fields=list(OMITTED),
                row_order='supplied paper order; observation order; observation then supplied component order',
                markers=dict(null=NOT_SUPPLIED, not_applicable=NOT_APPLICABLE, empty_string=EMPTY_STRING),
                marker_boundary='Display markers are not a reversible encoding; literal strings may collide.',
                max_input_bytes=MAX_INPUT_BYTES, max_output_bytes=MAX_OUTPUT_BYTES,
                max_cell_chars=MAX_CELL_CHARS, boundary=BOUNDARY)


def reference_rows(value):
    package, papers = _sources(value)
    bindings = dict(persona_sha256=payload_sha256(package['persona']),
                    knowledge_papers_sha256=payload_sha256(package['knowledge']['papers']))
    for paper in papers.values():
        base = dict.fromkeys(COLUMNS, NOT_APPLICABLE)
        base.update(bindings, paper_id=paper['paper_id'], source_kind=paper['kind'],
                    publication_year=paper['year'], source_sha256=paper['source_sha256'],
                    source_locator=paper['locator'],
                    recorded_source_check=paper.get('source_verification', 'NOT_PERFORMED'),
                    attribution='coauthored work; individual ownership not established', boundary=BOUNDARY)
        if not paper['observations']:
            yield dict(base, row_kind='PAPER_WITHOUT_OBSERVATIONS')
        for index, obs in enumerate(paper['observations']):
            for dimension in [None] + list(obs.get('reasoning', {})):
                ref = dict(paper_id=paper['paper_id'], observation_index=index, dimension=dimension)
                node = _endpoint(ref, papers)
                observation = node['observation']
                row = dict(base, row_kind='OBSERVATION' if dimension is None else 'COMPONENT',
                           observation_index=index, dimension=dimension,
                           reference_json=json.dumps(ref, ensure_ascii=True, sort_keys=True),
                           has_observation_origin=OBSERVATION_ORIGIN in observation,
                           missing_reasoning_dimensions=[d for d in DIMENSIONS if d not in obs.get('reasoning', {})],
                           observation_quote_check=observation['evidence_verification'])
                row.update({'observation_' + key: observation[key] for key in OBS_FIELDS})
                component = node['component']
                if component is not None:
                    row.update({'component_' + key: component.get(key) for key in COMP_FIELDS})
                    row['component_quote_check'] = component.get('evidence_verification', 'NOT_PERFORMED')
                yield row


def _render_rows(rows, columns, *, format='csv', excel_bom=False):
    if format not in ('csv', 'tsv') or type(excel_bom) is not bool:
        raise ValueError('choose csv or tsv and a boolean BOM option')
    output = bytearray(b'\xef\xbb\xbf' if excel_bom else b'')
    # Limit the accumulated UTF-8 output before emitting any stdout/file payload.
    def append(values):
        stream = io.StringIO(newline='')
        writer = csv.writer(stream, delimiter=',' if format == 'csv' else '\t', lineterminator='\n')
        writer.writerow([cell(item) for item in values])
        raw = stream.getvalue().encode('utf-8')
        if len(output) + len(raw) > MAX_OUTPUT_BYTES:
            raise ValueError('tabular output exceeds 16 MiB; narrow supplied artifacts explicitly')
        output.extend(raw)
    append(columns)
    for row in rows:
        append([row[key] for key in columns])
    return bytes(output)


def render(value, *, format='csv', excel_bom=False):
    return _render_rows(reference_rows(value), COLUMNS, format=format, excel_bom=excel_bom)


def agenda_rows(card, root, *, source_root=None):
    from journey_inputs import inspect, BOUNDARY as INPUT_BOUNDARY
    result = inspect(card, root, source_root=source_root)
    boundary = AGENDA_BOUNDARY + ' ' + result['boundary'] + ' ' + INPUT_BOUNDARY
    for item in result['review_agenda']:
        yield dict(domain=item['domain'], code=item['code'],
                   target_json=json.dumps({k:v for k,v in item.items() if k not in ('domain','code')},
                                          ensure_ascii=True, sort_keys=True, separators=(',', ':')),
                   journey_input_sha256=result['journey_input_sha256'], status=result['status'],
                   input_card_sha256=result['local_input_file_check']['input_card_sha256'],
                   source_reread=result['source_reread'], boundary=boundary)


def render_agenda(card, root, *, source_root=None, format='csv', excel_bom=False):
    return _render_rows(agenda_rows(card, root, source_root=source_root), AGENDA_COLUMNS,
                        format=format, excel_bom=excel_bom)


def _route_rows(result):
    from journey_inputs import BOUNDARY as INPUT_BOUNDARY
    boundary = ROUTE_BOUNDARY + ' ' + result['boundary'] + ' ' + INPUT_BOUNDARY
    for route in result['evidence_routes']:
        node = route['evidence']; ref = node['reference']; obs = node['observation']; comp = node['component']
        row = dict(row_kind='OBSERVATION' if ref['dimension'] is None else 'COMPONENT',
            paper_id=ref['paper_id'], observation_index=ref['observation_index'], dimension=ref['dimension'],
            reference_json=_compact(ref), reference_sha256=route['reference_sha256'], evidence_json=_compact(node),
            has_observation_origin=OBSERVATION_ORIGIN in obs,
            observation_quote_check=obs.get('evidence_verification', 'NOT_PERFORMED'),
            component_quote_check=comp.get('evidence_verification', 'NOT_PERFORMED') if comp is not None else NOT_APPLICABLE,
            pattern_roles_json=_compact(route['pattern_roles']),
            journey_input_sha256=result['journey_input_sha256'],
            input_card_sha256=result['local_input_file_check']['input_card_sha256'], status=result['status'],
            source_reread=result['source_reread'], boundary=boundary)
        row.update({key:node[key] for key in ('source_kind','publication_year','source_sha256',
                                           'source_locator','recorded_source_check','attribution')})
        row.update({key:route[key] for key in ('publication_scope','in_topic_timeline','actively_used_in_answer_or_design')})
        row.update({'observation_'+key:obs.get(key,NOT_APPLICABLE) for key in OBS_FIELDS})
        row.update({'component_'+key:comp.get(key,NOT_APPLICABLE) if comp is not None else NOT_APPLICABLE for key in COMP_FIELDS})
        for key in ROUTE_USES + (('method_application_uses',) if 'method_application_uses' in route else ()):
            row[key+'_count']=len(route[key]);row[key+'_json']=_compact(route[key])
        if 'current_source_recheck' in route:
            row['current_source_recheck_json']=_compact(route['current_source_recheck'])
        yield row


def render_routes(card, root, *, source_root=None, format='csv', excel_bom=False):
    from journey_inputs import inspect
    result = inspect(card, root, source_root=source_root)
    # Only inspect() validates the card. Choose the header from pinned options even
    # when the inspected route list is empty; never infer it from the first row.
    columns = route_columns(card['artifacts']['method_applications'] is not None,
                            card['artifacts']['source_selection'] is not None)
    return _render_rows(_route_rows(result), columns, format=format, excel_bom=excel_bom)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('table', choices=('reference-catalog', 'review-agenda', 'evidence-routes'))
    parser.add_argument('package', type=Path, nargs='?')
    parser.add_argument('--format', choices=('csv', 'tsv'), default='csv')
    parser.add_argument('--excel-bom', action='store_true')
    parser.add_argument('--describe', action='store_true')
    parser.add_argument('--input-root', type=Path)
    parser.add_argument('--source-root', type=Path)
    add_output_argument(parser)
    args = parser.parse_args()
    preflight(parser, args.output)
    try:
        if args.describe:
            if (args.package is not None or args.excel_bom or args.format != 'csv'
                    or args.input_root is not None or args.source_root is not None):
                raise ValueError('describe takes no package, BOM or nondefault format')
            raw = (json.dumps(describe(args.table), ensure_ascii=True, sort_keys=True, indent=2) + '\n').encode('utf-8')
        else:
            if args.package is None:
                raise ValueError('supply a bound package or request --describe')
            if args.table == 'reference-catalog':
                if args.input_root is not None or args.source_root is not None:
                    raise ValueError('reference-catalog takes no input-root or source-root')
                raw = render(load(args.package, max_bytes=MAX_INPUT_BYTES),
                             format=args.format, excel_bom=args.excel_bom)
            else:
                if args.input_root is None:
                    raise ValueError(args.table + ' requires an explicit input-root')
                from journey_inputs import _load_card
                renderer = render_agenda if args.table == 'review-agenda' else render_routes
                raw = renderer(_load_card(args.package), args.input_root, source_root=args.source_root,
                                    format=args.format, excel_bom=args.excel_bom)
    except (ValueError, OSError, KeyError, TypeError, AttributeError, RuntimeError, RecursionError) as exc:
        parser.exit(1, str(exc) + '\n')
    emit(parser, raw, args.output)


if __name__ == '__main__':
    main()
