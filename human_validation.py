"""Record and check a detached human validation assessment bound to one persona package."""
import argparse
import datetime
import json
import re
import sys
from pathlib import Path

from persona import payload_sha256, validate
from review_package import display
from strict_json import loads

ROOT = Path(__file__).resolve().parent
SCHEMA = 'human-validation-record.v1'
COMPLETED = 'RECORDED'
JUDGEMENTS = ('AGREE', 'PARTIAL', 'DISAGREE', 'NOT_ASSESSED')
BINDING_KEYS = ('author_id', 'version', 'build_id', 'persona_payload_sha256', 'knowledge_papers_sha256')
RECORD_FIELDS = ('schema_version', *BINDING_KEYS, 'raters', 'assessed_at', 'method', 'scope_topics',
                 'items', 'limitations', 'independence_declaration', 'status')
RATER_FIELDS = ('rater_id', 'role')
ITEM_FIELDS = ('item_id', 'judgement', 'rationale', 'source_locator')
LABEL_KEYS = ('author_id', 'reviewer_id', 'operator_id')
MAX_INPUT_BYTES = 8 * 1024 * 1024
MAX_OUTPUT_BYTES = 16 * 1024 * 1024
MAX_RATERS = 32
MAX_ITEMS = 4096
MAX_ID_CHARS = 128
MAX_TEXT_CHARS = 2000
BOUNDARY = ('A recorded human assessment is a documented assertion by the named rater labels about the '
    'listed items of this exact package. It is not generalization to other topics or items, not proof '
    'of fidelity to the real researcher, not a score or verdict, and label distinctness is not verified '
    'independence, expertise or blinding. Hashes bind the record to a package payload; they do not '
    'authenticate raters or dates. Judgement counts are reported per label and never averaged. No LLM, '
    'provider call, network access or canonical update is performed; the persona payload is never modified. '
    'Rule IDs are per-build positions: a STALE_PACKAGE record keeps its recorded item IDs and counts, which are '
    'not re-resolved against the current package.')
AXIS_BOUNDARY = ('Detached records are checked against the current package hashes only; the persona payload '
    'value validation.human_validation is unchanged by this report. RECORDED_CURRENT means at least one '
    'checked record binds to this exact package, STALE_PACKAGE means every supplied record binds to other '
    'hashes, NOT_PERFORMED means no record was supplied. Promoting a status into a package is a release '
    'decision taken through the normal lifecycle, not an effect of this report. Counts per judgement label '
    'are not a score, verdict, generalization or proof of researcher fidelity; rater label distinctness is '
    'not verified independence. Rule IDs are per-build positions, so a stale record keeps its recorded item IDs '
    'and topics, which are not re-resolved against the current package. No LLM, provider call, network access '
    'or canonical update is performed.')


def _keys(value, keys, name):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValueError(name + ' has missing or unknown fields')


def _text(value, name, maximum=MAX_TEXT_CHARS):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(name + ' must be a nonempty string of at most %d characters' % maximum)


def _identifier(value, name):
    _text(value, name, MAX_ID_CHARS)
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise ValueError(name + ' cannot contain control characters')


def _hash(value, name):
    if not isinstance(value, str) or re.fullmatch('[0-9a-f]{64}', value) is None:
        raise ValueError(name + ' must be a lowercase SHA256 hex digest')


def _date(value):
    """Accept only a calendar date YYYY-MM-DD; identical on every supported Python version."""
    if not isinstance(value, str) or re.fullmatch('[0-9]{4}-[0-9]{2}-[0-9]{2}', value) is None:
        raise ValueError('assessed_at must be an ISO calendar date YYYY-MM-DD')
    try:
        datetime.date(int(value[:4]), int(value[5:7]), int(value[8:]))
    except ValueError as exc:
        raise ValueError('assessed_at is not a valid calendar date') from exc


def _package(persona, knowledge=None):
    """Accept PERSONA+KNOWLEDGE, a {persona, knowledge} package or a {package: ...} wrapper."""
    if knowledge is None:
        if not isinstance(persona, dict):
            raise ValueError('package must be an object')
        package = persona.get('package', persona)
        if not isinstance(package, dict) or 'persona' not in package or 'knowledge' not in package:
            raise ValueError('supply PERSONA.json and KNOWLEDGE.json, or one bound package file with persona and knowledge')
        persona, knowledge = package['persona'], package['knowledge']
    errors = validate(persona, knowledge)
    if errors:
        raise ValueError('; '.join(errors))
    return persona, knowledge


def bindings(persona, knowledge):
    return dict(author_id=persona['author_id'], version=persona['version'], build_id=persona['build_id'],
                persona_payload_sha256=payload_sha256(persona),
                knowledge_papers_sha256=payload_sha256(knowledge['papers']))


def _rules(persona):
    rules = persona.get('rules', [])
    if not isinstance(rules, list):
        raise ValueError('persona rules must be an array')
    topics = {}
    for rule in rules:
        if not isinstance(rule, dict) or not isinstance(rule.get('rule_id'), str) or not isinstance(rule.get('topic'), str):
            raise ValueError('package rules need rule_id and topic strings')
        if rule['rule_id'] in topics:
            raise ValueError('duplicate rule_id in package')
        topics[rule['rule_id']] = rule['topic']
    return topics


def available_topics(persona, knowledge):
    """Exact observation/rule topic strings of the package; nothing is merged or inferred."""
    topics = set(_rules(persona).values())
    for paper in knowledge['papers']:
        observations = paper.get('observations', []) if isinstance(paper, dict) else []
        if not isinstance(observations, list):
            raise ValueError('paper observations must be an array')
        for observation in observations:
            if isinstance(observation, dict) and isinstance(observation.get('topic'), str):
                topics.add(observation['topic'])
    return sorted(topics)


def recorded_labels(persona, knowledge):
    """Every author/reviewer/operator label string recorded anywhere in the package."""
    labels = set()
    pending = [persona, knowledge]
    while pending:
        value = pending.pop()
        if isinstance(value, dict):
            for key, child in value.items():
                if key in LABEL_KEYS and isinstance(child, str):
                    labels.add(child)
                pending.append(child)
        elif isinstance(value, list):
            pending.extend(value)
    return sorted(labels)


def template(persona, knowledge=None):
    """Blank record bound to the package; lists available topics and rule IDs, assesses nothing."""
    persona, knowledge = _package(persona, knowledge)
    record = {'schema_version': SCHEMA}
    record.update(bindings(persona, knowledge))
    record.update(raters=[dict(rater_id='', role='')], assessed_at='', method='',
                  scope_topics=available_topics(persona, knowledge),
                  items=[dict(item_id=rule_id, judgement='NOT_ASSESSED', rationale='', source_locator='')
                         for rule_id in _rules(persona)],
                  limitations='', independence_declaration='', status=None)
    return record


def write_template(persona, knowledge, destination):
    record = template(persona, knowledge)
    requested = Path(destination).absolute()
    if any(p.is_symlink() for p in (requested, *requested.parents)):
        raise ValueError('record output path must not contain symlinks')
    target = requested.resolve()
    if target == ROOT or ROOT in target.parents:
        raise ValueError('write the record outside the repository; the publication inventory rejects unlisted files')
    if target.exists():
        raise ValueError('output already exists; no files are overwritten')
    if not target.parent.is_dir():
        raise ValueError('output parent must already exist')
    with target.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(record, ensure_ascii=True, indent=2) + '\n')
    return record


def check(record, persona, knowledge=None):
    """Strictly validate one record against the package; derive binding status, count judgements."""
    persona, knowledge = _package(persona, knowledge)
    _keys(record, RECORD_FIELDS, 'human validation record')
    if record['schema_version'] != SCHEMA:
        raise ValueError('unsupported human validation record schema_version')
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
    raters = record['raters']
    if not isinstance(raters, list) or not 1 <= len(raters) <= MAX_RATERS:
        raise ValueError('raters must list between 1 and %d entries' % MAX_RATERS)
    labels = []
    for rater in raters:
        _keys(rater, RATER_FIELDS, 'rater')
        _identifier(rater['rater_id'], 'rater_id')
        _text(rater['role'], 'rater role', MAX_ID_CHARS)
        if rater['rater_id'] in labels:
            raise ValueError('duplicate rater_id')
        labels.append(rater['rater_id'])
    recorded = recorded_labels(persona, knowledge)
    colliding = [label for label in labels if label in recorded]
    if len(colliding) == len(labels):
        raise ValueError('no rater label is distinct from the author/operator/reviewer labels recorded in the package')
    _date(record['assessed_at'])
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
    items = record['items']
    if not isinstance(items, list) or not 1 <= len(items) <= MAX_ITEMS:
        raise ValueError('items must list between 1 and %d assessed rules' % MAX_ITEMS)
    seen, covered = set(), set()
    counts = {judgement: 0 for judgement in JUDGEMENTS}
    for item in items:
        _keys(item, ITEM_FIELDS, 'item')
        _identifier(item['item_id'], 'item_id')
        if resolved and item['item_id'] not in rules:
            raise ValueError('item_id is not a rule_id of the supplied package')
        if item['item_id'] in seen:
            raise ValueError('duplicate item_id')
        seen.add(item['item_id'])
        if item['judgement'] not in JUDGEMENTS:
            raise ValueError('judgement must be AGREE, PARTIAL, DISAGREE or NOT_ASSESSED')
        _text(item['rationale'], 'rationale')
        _text(item['source_locator'], 'source_locator')
        if resolved:
            if rules[item['item_id']] not in scope:
                raise ValueError('assessed item topic is outside the declared scope_topics')
            covered.add(rules[item['item_id']])
        counts[item['judgement']] += 1
    if resolved and any(topic not in covered for topic in scope):
        raise ValueError('every scope topic needs at least one assessed item')
    # Recorded IDs and topics absent from the current package; the remaining ones are not re-resolved either.
    unresolved_items = [item['item_id'] for item in items if item['item_id'] not in rules]
    unresolved_topics = [topic for topic in scope if topic not in topics]
    result = dict(status='HUMAN_VALIDATION_RECORD_CHECKED', binding_status=binding,
        record_sha256=payload_sha256(record), record_hash_kind='logical JSON payload hash, not a file byte hash',
        package=current, recorded_bindings={key: record[key] for key in BINDING_KEYS},
        binding_differences=differences, items_resolved_against_current_package=resolved,
        unresolved_item_ids=unresolved_items, unresolved_topics=unresolved_topics, raters=raters, rater_count=len(raters),
        colliding_rater_labels=colliding, package_labels=recorded, rater_independence='LABEL_DISTINCT_ONLY',
        assessed_at=record['assessed_at'], method=record['method'], scope_topics=scope,
        item_count=len(items), judgement_counts=counts, items=items,
        limitations=record['limitations'], independence_declaration=record['independence_declaration'],
        aggregate_score='NOT_COMPUTED', verdict='NOT_DERIVED', generalization='NOT_ESTABLISHED',
        scientific_validation='NOT_PERFORMED', researcher_fidelity_evaluation='NOT_PERFORMED',
        llm_used=False, canonical_update_performed=False, persona_payload_modified=False, boundary=BOUNDARY)
    return json.loads(json.dumps(result))  # Detach from the supplied record.


def axis(persona, knowledge=None, records=()):
    """Read-only human-validation axis report for one package and zero or more checked records."""
    persona, knowledge = _package(persona, knowledge)
    rows = []
    for record in records:
        result = check(record, persona, knowledge)
        if any(row['record_sha256'] == result['record_sha256'] for row in rows):
            raise ValueError('the same human validation record was supplied twice')
        rows.append({key: result[key] for key in ('record_sha256', 'binding_status', 'binding_differences',
            'items_resolved_against_current_package', 'unresolved_item_ids', 'unresolved_topics',
            'assessed_at', 'rater_count', 'colliding_rater_labels', 'item_count', 'judgement_counts')})
    current = sum(row['binding_status'] == 'CURRENT_PACKAGE' for row in rows)
    declared = persona.get('validation')
    declared = declared.get('human_validation') if isinstance(declared, dict) else None
    result = dict(status='NOT_PERFORMED' if not rows else 'RECORDED_CURRENT' if current else 'STALE_PACKAGE',
        axis='human_validation', package=bindings(persona, knowledge),
        persona_payload_human_validation=declared if isinstance(declared, str) else 'NOT_DECLARED',
        record_count=len(rows), current_record_count=current, stale_record_count=len(rows) - current,
        records=rows, rater_independence='LABEL_DISTINCT_ONLY', aggregate_score='NOT_COMPUTED',
        verdict='NOT_DERIVED', scientific_validation='NOT_PERFORMED',
        researcher_fidelity_evaluation='NOT_PERFORMED', llm_used=False, canonical_update_performed=False,
        persona_payload_modified=False, boundary=AXIS_BOUNDARY)
    return json.loads(json.dumps(result))


def _counts(counts):
    return '; '.join(key + '=' + str(counts[key]) for key in JUDGEMENTS)


def _unresolved(result):
    """Recorded IDs and topics absent from the current package; a stale record's other IDs are not re-resolved either."""
    return ('unresolved item IDs (absent from the current package): '
            + (', '.join(display(x) for x in result['unresolved_item_ids']) or 'none')
            + '; unresolved topics (absent from the current package): '
            + (', '.join(display(x) for x in result['unresolved_topics']) or 'none'))


def axis_lines(result, prefix=''):
    """Compact axis lines for the release review; records keep their own hashes and counts."""
    lines = [prefix + f"Human validation axis: {result['status']} (records={result['record_count']}; "
             f"current={result['current_record_count']}; stale={result['stale_record_count']}); "
             'persona payload validation.human_validation=' + display(result['persona_payload_human_validation']) + ' (unchanged)']
    for row in result['records']:
        lines.append(prefix + f"  Record sha256={row['record_sha256']}: {row['binding_status']}; raters={row['rater_count']} "
                     f"(LABEL_DISTINCT_ONLY; colliding={len(row['colliding_rater_labels'])}); items={row['item_count']}; "
                     + _counts(row['judgement_counts']) + '; assessed_at=' + display(row['assessed_at']))
        if row['binding_differences']:
            lines.append(prefix + '    Binding differences: ' + ', '.join(row['binding_differences']))
        if not row['items_resolved_against_current_package']:
            lines.append(prefix + '    Items not re-resolved against the current package (rule IDs are per-build positions); '
                         + _unresolved(row))
    lines.append(prefix + 'Human validation boundary: ' + AXIS_BOUNDARY)
    return lines


def _package_lines(package):
    return ['Package: ' + ' | '.join(display(package[key]) for key in ('author_id', 'version', 'build_id')),
            'Persona payload sha256: ' + package['persona_payload_sha256'],
            'Knowledge papers sha256: ' + package['knowledge_papers_sha256']]


def render_check(result):
    lines = ['Human validation record check', 'Status: ' + result['status'] + '; binding=' + result['binding_status'],
             'Record sha256: ' + result['record_sha256'] + ' (' + result['record_hash_kind'] + ')', *_package_lines(result['package']),
             'Recorded bindings: ' + '; '.join(key + '=' + display(result['recorded_bindings'][key]) for key in BINDING_KEYS[1:]),
             'Binding differences: ' + (', '.join(result['binding_differences']) if result['binding_differences'] else 'none'),
             'Item resolution: ' + ('resolved against the current package' if result['items_resolved_against_current_package']
                                    else 'NOT re-resolved against the current package (rule IDs are per-build positions; the record '
                                         'documents an earlier package state); ' + _unresolved(result)),
             'Raters (LABEL_DISTINCT_ONLY): ' + '; '.join(display(r['rater_id']) + ' [' + display(r['role']) + ']' for r in result['raters']),
             'Rater labels colliding with package labels: ' + (', '.join(display(x) for x in result['colliding_rater_labels'])
                                                             if result['colliding_rater_labels'] else 'none'),
             'Assessed at: ' + display(result['assessed_at']), 'Method: ' + display(result['method']),
             'Scope topics: ' + '; '.join(display(t) for t in result['scope_topics']),
             f"Items: {result['item_count']}; " + _counts(result['judgement_counts'])]
    if not result['items_resolved_against_current_package']:
        lines.append('  (recorded item IDs of the stale package; not re-resolved against the current rules)')
    for item in result['items']:
        lines.append('  ' + display(item['item_id']) + ': ' + item['judgement'] + ' | ' + display(item['source_locator']) + ' | ' + display(item['rationale']))
    lines.extend(['Limitations: ' + display(result['limitations']),
                  'Independence declaration: ' + display(result['independence_declaration']),
                  'Aggregate score: ' + result['aggregate_score'] + '; verdict: ' + result['verdict'],
                  'Boundary: ' + result['boundary']])
    return '\n'.join(lines) + '\n'


def render_status(result):
    return '\n'.join(['Human validation axis report', *_package_lines(result['package']), *axis_lines(result)]) + '\n'


def _bounded(output):
    if len(output.encode('utf-8')) > MAX_OUTPUT_BYTES:
        raise ValueError('human validation output exceeds 16 MiB')
    return output


def bounded_reader(budget=None):
    """Strict JSON reader whose files share one input budget (MAX_INPUT_BYTES unless given); fails closed."""
    remaining = [MAX_INPUT_BYTES if budget is None else budget]

    def read(path):
        raw = Path(path).read_bytes()
        remaining[0] -= len(raw)
        if remaining[0] < 0:
            raise ValueError('combined human validation inputs exceed 8 MiB')
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
    status = sub.add_parser('status', help='Read-only axis report; NOT_PERFORMED without records')
    status.add_argument('persona', type=Path)
    status.add_argument('knowledge', type=Path, nargs='?')
    status.add_argument('--human-validation', type=Path, action='append', default=[],
                        help='Checked record(s) to report; repeatable')
    status.add_argument('--text', action='store_true')
    args = parser.parse_args()
    read = bounded_reader()
    try:
        persona = read(args.persona)
        knowledge = read(args.knowledge) if args.knowledge is not None else None
        if args.command == 'template':
            record = write_template(persona, knowledge, args.output)
            result = dict(status='HUMAN_VALIDATION_TEMPLATE_WRITTEN', template_sha256=payload_sha256(record),
                package={key: record[key] for key in BINDING_KEYS}, available_topics=record['scope_topics'],
                available_item_ids=[item['item_id'] for item in record['items']], record_status=None,
                next_step='Fill every blank field, keep only the assessed topics and items, set status to RECORDED, '
                          'then run check. The unedited template fails check and records no assessment.',
                llm_used=False, canonical_update_performed=False, boundary=BOUNDARY)
            output = json.dumps(result, indent=2) + '\n'
        elif args.command == 'check':
            result = check(read(args.record), persona, knowledge)
            output = render_check(result) if args.text else json.dumps(result, indent=2) + '\n'
        else:
            result = axis(persona, knowledge, [read(path) for path in args.human_validation])
            output = render_status(result) if args.text else json.dumps(result, indent=2) + '\n'
        output = _bounded(output)
    except (ValueError, OSError, KeyError, TypeError, AttributeError, RecursionError) as exc:
        parser.exit(1, str(exc) + '\n')
    sys.stdout.buffer.write(output.encode('utf-8'))


if __name__ == '__main__':
    main()
