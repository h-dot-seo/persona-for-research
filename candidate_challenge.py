"""Record and check a detached candidate challenge assessment bound to one persona package."""
import argparse
from exclusive_output import add_output_argument, emit, preflight, write_exclusive
import datetime
import json
import re
from pathlib import Path

from persona import payload_sha256
from strict_json import loads

ROOT = Path(__file__).resolve().parent
SCHEMA = 'persona.candidate-challenge.v1'
COMPLETED = 'RECORDED'
KINDS = ('NOT_EXAMINED', 'NO_FINDING', 'OVERSTATED_STATEMENT', 'MISSING_COUNTEREVIDENCE',
         'ATTRIBUTION_DOUBT', 'SCOPE_EXCEEDED', 'PROVENANCE_GAP', 'OTHER')
BINDING_KEYS = ('author_id', 'version', 'build_id', 'persona_payload_sha256', 'knowledge_papers_sha256')
RECORD_FIELDS = ('schema_version', *BINDING_KEYS, 'challengers', 'challenged_at', 'method', 'holdout_inspected', 'scope_topics',
                 'findings', 'limitations', 'independence_declaration', 'status')
CHALLENGER_FIELDS = ('challenger_id', 'role')
FINDING_FIELDS = ('finding_id', 'item_id', 'kind', 'rationale', 'source_locator')
LABEL_KEYS = ('author_id', 'reviewer_id', 'operator_id')
MAX_INPUT_BYTES = 8 * 1024 * 1024
MAX_OUTPUT_BYTES = 16 * 1024 * 1024
MAX_CHALLENGERS = 32
MAX_FINDINGS = 4096
MAX_ID_CHARS = 128
MAX_TEXT_CHARS = 2000
BOUNDARY = ('This detached record documents supplied findings about one candidate, not human-validation '
    'judgements or an additional validation axis. Counts are not scores, verdicts or candidate approval. '
    'LABEL_DISTINCT_ONLY compares labels, not verified independence, expertise or blinding. '
    'holdout_inspected=false is a declaration only: unseen holdout, dates and pre-evaluation ordering '
    'are not authenticated. Hashes bind content, not identities. Stale rule IDs are not re-resolved. '
    'No operator disposition, scientific validation, LLM, network call or canonical update is performed. '
    'The persona payload is never modified. Record prose may be private; summaries are not rights clearance.')
STAGE_BOUNDARY = BOUNDARY


from human_validation import (_package, bindings, recorded_labels, available_topics, _rules,
                              _keys, _text, _identifier, _hash)


def _date(value):
    if not isinstance(value, str) or re.fullmatch('[0-9]{4}-[0-9]{2}-[0-9]{2}', value) is None:
        raise ValueError('challenged_at must be an ISO calendar date YYYY-MM-DD')
    try:
        datetime.date(int(value[:4]), int(value[5:7]), int(value[8:]))
    except ValueError as exc:
        raise ValueError('challenged_at is not a valid calendar date') from exc


def template(persona, knowledge=None):
    """Blank record bound to the package; lists available topics and rule IDs, assesses nothing."""
    persona, knowledge = _package(persona, knowledge)
    record = {'schema_version': SCHEMA}
    record.update(bindings(persona, knowledge))
    record.update(challengers=[dict(challenger_id='', role='')], challenged_at='', method='', holdout_inspected=False,
                  scope_topics=available_topics(persona, knowledge),
                  findings=[dict(finding_id='finding-%d' % (i + 1), item_id=rule_id, kind='NOT_EXAMINED',
                                 rationale='', source_locator='') for i, rule_id in enumerate(_rules(persona))],
                  limitations='', independence_declaration='', status=None)
    return record


def write_template(persona, knowledge, destination):
    record = template(persona, knowledge)
    write_exclusive(_bounded(json.dumps(record, ensure_ascii=True, indent=2) + '\n').encode('utf-8'), destination)
    return record


def check(record, persona, knowledge=None):
    """Strictly validate one record against the package; derive binding status, count kinds."""
    persona, knowledge = _package(persona, knowledge)
    _keys(record, RECORD_FIELDS, 'candidate challenge record')
    if record['schema_version'] != SCHEMA:
        raise ValueError('unsupported candidate challenge record schema_version')
    for key in ('author_id', 'version', 'build_id'):
        _identifier(record[key], key)
    for key in ('persona_payload_sha256', 'knowledge_papers_sha256'):
        _hash(record[key], key)
    current = bindings(persona, knowledge)
    if record['author_id'] != current['author_id']:
        raise ValueError('record belongs to a different scholarly identity')
    differences = [key for key in BINDING_KEYS if record[key] != current[key]]
    binding = 'STALE_PACKAGE' if differences else 'CURRENT_PACKAGE'
    if record['status'] != COMPLETED:
        raise ValueError('record status must be RECORDED; a template with null status is not a completed assessment')
    if record['holdout_inspected'] is not False:
        raise ValueError('holdout_inspected must be false: this is a declared pre-holdout record')
    challengers = record['challengers']
    if not isinstance(challengers, list) or not 1 <= len(challengers) <= MAX_CHALLENGERS:
        raise ValueError('challengers must list between 1 and %d entries' % MAX_CHALLENGERS)
    labels = []
    for challenger in challengers:
        _keys(challenger, CHALLENGER_FIELDS, 'challenger')
        _identifier(challenger['challenger_id'], 'challenger_id')
        _text(challenger['role'], 'challenger role', MAX_ID_CHARS)
        if challenger['challenger_id'] in labels:
            raise ValueError('duplicate challenger_id')
        labels.append(challenger['challenger_id'])
    recorded = recorded_labels(persona, knowledge)
    colliding = [label for label in labels if label in recorded]
    if len(colliding) == len(labels):
        raise ValueError('no challenger label is distinct from the author/operator/reviewer labels recorded in the package')
    _date(record['challenged_at'])
    for key in ('method', 'limitations', 'independence_declaration'):
        _text(record[key], key)
    # Rule IDs are per-build positions: only a record bound to the current package has its item IDs and
    # topics resolved against it. A stale record keeps its recorded IDs; the same ID in a rebuilt package
    # may denote a different rule, so nothing is re-resolved and nothing is raised for it.
    resolved = binding == 'CURRENT_PACKAGE'
    topics = available_topics(persona, knowledge)
    scope = record['scope_topics']
    if not isinstance(scope, list) or not scope:
        raise ValueError('scope_topics must list at least one package topic')
    for topic in scope:
        _text(topic, 'scope topic')
        if resolved and topic not in topics:
            raise ValueError('scope topic is not an observation/rule topic of the supplied package')
    if len(set(scope)) != len(scope):
        raise ValueError('duplicate scope topic')
    rules = _rules(persona)
    findings = record['findings']
    if not isinstance(findings, list) or not 1 <= len(findings) <= MAX_FINDINGS:
        raise ValueError('findings must list between 1 and %d assessed rules' % MAX_FINDINGS)
    seen, by_item = set(), {}
    counts = {kind: 0 for kind in KINDS}
    for item in findings:
        _keys(item, FINDING_FIELDS, 'item')
        _identifier(item['finding_id'], 'finding_id')
        if item['item_id'] is not None:
            _identifier(item['item_id'], 'item_id')
        if resolved and item['item_id'] is not None and item['item_id'] not in rules:
            raise ValueError('item_id is not a rule_id of the supplied package')
        if item['finding_id'] in seen:
            raise ValueError('duplicate finding_id')
        seen.add(item['finding_id'])
        if item['kind'] not in KINDS:
            raise ValueError('unsupported finding kind')
        _text(item['rationale'], 'rationale')
        _text(item['source_locator'], 'source_locator')
        by_item.setdefault(item['item_id'], set()).add(item['kind'])
        if resolved and item['item_id'] is not None:
            if rules[item['item_id']] not in scope:
                raise ValueError('assessed item topic is outside the declared scope_topics')
        counts[item['kind']] += 1
    if any('NO_FINDING' in kinds and len(kinds) > 1 for kinds in by_item.values()):
        raise ValueError('NO_FINDING cannot coexist with other kinds for the same item_id')
    # Recorded IDs and topics absent from the current package; the remaining ones are not re-resolved either.
    unresolved_items = [item['item_id'] for item in findings if item['item_id'] is not None and item['item_id'] not in rules]
    unresolved_topics = [topic for topic in scope if topic not in topics]
    result = dict(status='CANDIDATE_CHALLENGE_RECORD_CHECKED', binding_status=binding,
        record_sha256=payload_sha256(record), record_hash_kind='logical JSON payload hash, not a file byte hash',
        package=current, recorded_bindings={key: record[key] for key in BINDING_KEYS},
        binding_differences=differences, findings_resolved_against_current_package=resolved,
        unresolved_item_ids=unresolved_items, unresolved_topics=unresolved_topics,
        challenger_count=len(challengers), colliding_challenger_count=len(colliding),
        challenger_independence='LABEL_DISTINCT_ONLY', challenged_at=record['challenged_at'],
        finding_count=len(findings), kind_counts=counts,
        substantive_finding_count=sum(counts[k] for k in KINDS if k not in ('NO_FINDING', 'NOT_EXAMINED')),
        stage='pre_holdout_challenge', candidate_approval='NOT_DERIVED',
        aggregate_score='NOT_COMPUTED', verdict='NOT_DERIVED', generalization='NOT_ESTABLISHED',
        scientific_validation='NOT_PERFORMED', researcher_fidelity_evaluation='NOT_PERFORMED',
        llm_used=False, canonical_update_performed=False, persona_payload_modified=False, boundary=BOUNDARY)
    return json.loads(json.dumps(result))  # Detach from the supplied record.


def status(persona, knowledge=None, records=()):
    """Read-only challenge-record stage report for one package and zero or more checked records."""
    persona, knowledge = _package(persona, knowledge)
    rows = []
    for record in records:
        result = check(record, persona, knowledge)
        if any(row['record_sha256'] == result['record_sha256'] for row in rows):
            raise ValueError('the same candidate challenge record was supplied twice')
        rows.append({key: result[key] for key in ('record_sha256', 'binding_status', 'binding_differences',
            'findings_resolved_against_current_package', 'unresolved_item_ids', 'unresolved_topics',
            'challenged_at', 'challenger_count', 'colliding_challenger_count', 'finding_count', 'kind_counts', 'substantive_finding_count')})
    current = sum(row['binding_status'] == 'CURRENT_PACKAGE' for row in rows)
    result = dict(status='NOT_PERFORMED' if not rows else 'RECORDED_CURRENT' if current else 'STALE_PACKAGE',
        stage='pre_holdout_challenge', package=bindings(persona, knowledge), candidate_approval='NOT_DERIVED',
        record_count=len(rows), current_record_count=current, stale_record_count=len(rows) - current,
        records=rows, challenger_independence='LABEL_DISTINCT_ONLY', aggregate_score='NOT_COMPUTED',
        verdict='NOT_DERIVED', scientific_validation='NOT_PERFORMED',
        researcher_fidelity_evaluation='NOT_PERFORMED', llm_used=False, canonical_update_performed=False,
        persona_payload_modified=False, boundary=STAGE_BOUNDARY)
    return json.loads(json.dumps(result))


def status_lines(result, prefix=''):
    lines = [prefix + 'Pre-holdout challenge record(s): ' + result['status'] +
             ' (records=%d; current=%d; stale=%d)' %
             (result['record_count'], result['current_record_count'], result['stale_record_count'])]
    for row in result['records']:
        lines.append(prefix + '  Record sha256=' + row['record_sha256'] + ': ' + row['binding_status'] +
                     '; ' + '; '.join(k + '=' + str(row['kind_counts'][k]) for k in KINDS))
    lines.append(prefix + 'Pre-holdout candidate challenge boundary: ' + BOUNDARY)
    return lines


def render_check(result):
    # JSON escapes untrusted strings in --text too; no raw terminal prose is echoed.
    return json.dumps(result, ensure_ascii=True, indent=2) + '\n'


def render_status(result):
    return '\n'.join(status_lines(result)) + '\n'


def _bounded(output):
    if len(output.encode('utf-8')) > MAX_OUTPUT_BYTES:
        raise ValueError('candidate challenge output exceeds 16 MiB')
    return output


def bounded_reader(budget=None):
    """Strict JSON reader whose files share one input budget (MAX_INPUT_BYTES unless given); fails closed."""
    remaining = [MAX_INPUT_BYTES if budget is None else budget]

    def read(path):
        with Path(path).open('rb') as stream:
            raw = stream.read(remaining[0] + 1)
        remaining[0] -= len(raw)
        if remaining[0] < 0:
            raise ValueError('combined candidate challenge inputs exceed 8 MiB')
        return loads(raw)
    return read


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    blank = sub.add_parser('template', help='Write a blank record bound to the package; never overwrites')
    blank.add_argument('persona', type=Path, help='PERSONA.json, or one bound package file when KNOWLEDGE.json is omitted')
    blank.add_argument('knowledge', type=Path, nargs='?')
    blank.add_argument('--output', type=Path, required=True, help='New record file outside the repository')
    checking = sub.add_parser('check', help='Strictly validate a record against the package')
    checking.add_argument('record', type=Path)
    checking.add_argument('persona', type=Path)
    checking.add_argument('knowledge', type=Path, nargs='?')
    checking.add_argument('--text', action='store_true')
    reporting = sub.add_parser('status', help='Read-only stage report; NOT_PERFORMED without records')
    reporting.add_argument('persona', type=Path)
    reporting.add_argument('knowledge', type=Path, nargs='?')
    reporting.add_argument('--challenge-record', type=Path, action='append', default=[],
                        help='Checked record(s) to report; repeatable')
    reporting.add_argument('--text', action='store_true')
    add_output_argument(checking)
    add_output_argument(reporting)
    args = parser.parse_args()
    preflight(parser, args.output)
    read = bounded_reader()
    try:
        persona = read(args.persona)
        knowledge = read(args.knowledge) if args.knowledge is not None else None
        if args.command == 'template':
            record = write_template(persona, knowledge, args.output)
            result = dict(status='CANDIDATE_CHALLENGE_TEMPLATE_WRITTEN', template_sha256=payload_sha256(record),
                package={key: record[key] for key in BINDING_KEYS}, available_topics=record['scope_topics'],
                available_item_ids=[item['item_id'] for item in record['findings']], record_status=None,
                next_step='Fill every blank field, keep only the assessed topics and findings, set status to RECORDED, '
                          'then run check. The unedited template fails check and records no assessment.',
                llm_used=False, canonical_update_performed=False, boundary=BOUNDARY)
            output = json.dumps(result, indent=2) + '\n'
        elif args.command == 'check':
            result = check(read(args.record), persona, knowledge)
            output = render_check(result) if args.text else json.dumps(result, indent=2) + '\n'
        else:
            result = status(persona, knowledge, [read(path) for path in args.challenge_record])
            output = render_status(result) if args.text else json.dumps(result, indent=2) + '\n'
        output = _bounded(output)
    except (ValueError, OSError, KeyError, TypeError, AttributeError, RecursionError) as exc:
        parser.exit(1, ('candidate challenge input/output could not be read or written' if isinstance(exc, OSError)
                        else 'invalid candidate challenge input') + '\n')
    emit(parser, output.encode('utf-8'), None if args.command == 'template' else args.output)


if __name__ == '__main__':
    main()
