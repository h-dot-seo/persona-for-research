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


def describe():
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


def render(value, *, format='csv', excel_bom=False):
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
    append(COLUMNS)
    for row in reference_rows(value):
        append([row[key] for key in COLUMNS])
    return bytes(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('table', choices=('reference-catalog',))
    parser.add_argument('package', type=Path, nargs='?')
    parser.add_argument('--format', choices=('csv', 'tsv'), default='csv')
    parser.add_argument('--excel-bom', action='store_true')
    parser.add_argument('--describe', action='store_true')
    add_output_argument(parser)
    args = parser.parse_args()
    preflight(parser, args.output)
    try:
        if args.describe:
            if args.package is not None or args.excel_bom or args.format != 'csv':
                raise ValueError('describe takes no package, BOM or nondefault format')
            raw = (json.dumps(describe(), ensure_ascii=True, sort_keys=True, indent=2) + '\n').encode('utf-8')
        else:
            if args.package is None:
                raise ValueError('supply a bound package or request --describe')
            raw = render(load(args.package, max_bytes=MAX_INPUT_BYTES),
                         format=args.format, excel_bom=args.excel_bom)
    except (ValueError, OSError, KeyError, TypeError, AttributeError, RuntimeError, RecursionError) as exc:
        parser.exit(1, str(exc) + '\n')
    emit(parser, raw, args.output)


if __name__ == '__main__':
    main()
