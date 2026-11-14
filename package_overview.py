"""Inspect all supplied records in one bound package without selection or recommendations."""
import argparse
import copy
import json
from pathlib import Path

from compare_releases import checked_package
from evidence_coverage import coverage
from exclusive_output import add_output_argument, emit, preflight
from human_validation import axis, bounded_reader
from observation_provenance import inventory as origins
from persona import payload_sha256
from research_workflow import validated_source_rules
from strict_json import load
from topic_inventory import inventory as topics

MAX_INPUT_BYTES = 8 * 1024 * 1024
MAX_OUTPUT_BYTES = 16 * 1024 * 1024
AXES = ('evidence_integrity', 'persona_predictive', 'human_validation', 'runtime_validation')
BOUNDARY = ('Descriptive supplied records only: no ranking, selection, recommendation, source reread, '
            'semantic validation or canonical update. Mechanical package prerequisites are not validation-axis '
            'success. Counts and recorded checks are not confidence, authenticity, readiness or approval.')
PRIVACY = ('Private corpus-wide view: copies all stored quotes, locators, source_file labels and imported '
           'reviewer/operator/provider/model/run/execution-location labels. Not anonymized or permission '
           'to share. Detached human-review rationales and rater identifiers are not included.')


def json_text(result):
    output = json.dumps(result, ensure_ascii=True, sort_keys=True, indent=2, allow_nan=False) + '\n'
    if len(output.encode('utf-8')) > MAX_OUTPUT_BYTES:
        raise ValueError('JSON package overview exceeds 16 MiB')
    return output


def inspect(value, human_records=()):
    package = checked_package(value)
    papers = validated_source_rules(package)
    persona = package['persona']
    human = axis(persona, package['knowledge'], records=human_records)
    # axis() intentionally provides only summary data, but some of its summaries
    # still contain colliding rater labels. Do not copy those into this view.
    human_summary = {k: copy.deepcopy(human[k]) for k in
                     ('status', 'record_count', 'current_record_count', 'stale_record_count', 'boundary')}
    human_summary['records'] = [{k: copy.deepcopy(row[k]) for k in
                                ('record_sha256', 'binding_status', 'judgement_counts')}
                               for row in human['records']]
    declared = persona.get('validation')
    declarations = {key: copy.deepcopy(declared[key]) if isinstance(declared, dict) and key in declared
                    else 'NOT_DECLARED' for key in AXES}
    rows = []
    refs = []
    rules = iter(persona['rules'])
    for paper in papers:
        row = dict(recorded_paper={k: copy.deepcopy(v) for k,v in paper.items() if k != 'observations'},
                   recorded_source_check=paper.get('source_verification', 'NOT_PERFORMED'), observations=[])
        for index, observation in enumerate(paper['observations']):
            rule = next(rules)
            reference = dict(paper_id=paper['paper_id'], observation_index=index, dimension=None)
            refs.append(reference)
            components = []
            for dimension, component in observation.get('reasoning', {}).items():
                ref = dict(paper_id=paper['paper_id'], observation_index=index, dimension=dimension)
                refs.append(ref)
                components.append(dict(reference=ref, recorded_component=copy.deepcopy(component),
                    recorded_quote_check=component.get('evidence_verification', 'NOT_PERFORMED')))
            row['observations'].append(dict(reference=reference,
                recorded_observation={k:copy.deepcopy(v) for k,v in observation.items() if k != 'reasoning'},
                recorded_quote_check=observation.get('evidence_verification', 'NOT_PERFORMED'),
                coverage=coverage([rule]), components=components))
        rows.append(row)
    result = dict(schema='persona.package-overview.v1',
        identity={k:persona[k] for k in ('author_id','version','build_id')},
        persona_sha256=payload_sha256(persona), knowledge_papers_sha256=payload_sha256(package['knowledge']['papers']),
        validation_axis_declarations=declarations,
        validation_axis_boundary='Payload declarations unchanged, not checked by this view; intake builders do not populate these axes.',
        mechanical_prerequisites='checked_package and validated_source_rules completed; prerequisites only, not axis outcomes.',
        human_validation=human_summary, topic_inventory=topics(package), papers=rows,
        coverage=coverage(persona['rules']), imported_observation_origins=origins(package), references=refs,
        current_local_source_check='NOT_PERFORMED', llm_used=False, semantic_validation='NOT_PERFORMED',
        selection_performed=False, source_reread=False, canonical_update_performed=False,
        aggregate_score='NOT_COMPUTED', boundary=BOUNDARY, privacy=PRIVACY)
    json_text(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package', type=Path)
    parser.add_argument('--human-validation', type=Path, action='append', default=[])
    parser.add_argument('--format', choices=('json','html'), default='json')
    add_output_argument(parser)
    args = parser.parse_args()
    preflight(parser, args.output)
    try:
        value = load(args.package, max_bytes=MAX_INPUT_BYTES)
        read = bounded_reader()
        result = inspect(value, [read(path) for path in args.human_validation])
        if args.format == 'html':
            from package_html import render
            output = render(result)
        else:
            output = json_text(result)
    except (ValueError, OSError, KeyError, TypeError, AttributeError, RuntimeError) as exc:
        parser.exit(1, str(exc) + '\n')
    emit(parser, output.encode('utf-8'), args.output)


if __name__ == '__main__':
    main()
