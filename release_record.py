"""Record supplied reopening triggers and declared prior-release impact without approving changes."""
import argparse
import datetime
import json
import re
from pathlib import Path

from candidate_challenge import bounded_reader, MAX_OUTPUT_BYTES
from compare_releases import checked_package, compare
from exclusive_output import add_output_argument, emit, preflight, write_exclusive
from human_validation import bindings, BINDING_KEYS, _keys, _text, _identifier, _hash, axis
from persona import payload_sha256
from research_workflow import validated_source_rules

SCHEMA = 'persona.reopening-record.v1'
TRIGGERS = ('new_paper', 'correction', 'retraction', 'provenance_error', 'counterexample', 'scope_change')
OPERATIONS = ('knowledge_ingestion', 'canonical_policy_revision')
AXES = ('evidence_integrity', 'predictive', 'human', 'runtime')
FIELDS = ('schema_version', *BINDING_KEYS, 'operator_id', 'trigger', 'affected_paper_ids',
          'incoming_paper_ids', 'affected_rule_ids', 'operation', 'revalidation_axes_required',
          'revision_audit_sha256', 'status')
BOUNDARY = ('This detached reopening record stores supplied trigger and revalidation-plan declarations, '
    'not verified correction/retraction facts, a release decision or approval. Prior-package rule IDs '
    'are positional and never interpreted against a candidate. Candidate differences are structural, '
    'not scientific or semantic judgments. Knowledge ingestion may also change built rules: operation '
    'is a declaration only, not a separate policy-layer guarantee. Matching the supplied prior package '
    'does not prove an archive was preserved. Revision audit hashes are declared references, not verified '
    'audit contents. No source lookup, model/API call, automatic rebinding, canonical update or payload '
    'modification is performed. IDs and bindings can be private; output is not sanitization.')


def _package(value):
    package = checked_package(value)
    validated_source_rules(package)
    return package


def _date(value):
    if not isinstance(value, str) or re.fullmatch('[0-9]{4}-[0-9]{2}-[0-9]{2}', value) is None:
        raise ValueError('declared_at must be YYYY-MM-DD')
    datetime.date(int(value[:4]), int(value[5:7]), int(value[8:]))


def _ids(value, name):
    if not isinstance(value, list) or len(value) > 4096:
        raise ValueError(name + ' must be an array of at most 4096 IDs')
    for item in value:
        _identifier(item, name)
    if len(set(value)) != len(value):
        raise ValueError('duplicate ' + name)
    return set(value)


def template(value):
    package = _package(value)
    return dict(schema_version=SCHEMA, **bindings(package['persona'], package['knowledge']),
        operator_id='', trigger=dict(kind=None, declared_source_text='', declared_at=''),
        affected_paper_ids=[], incoming_paper_ids=[], affected_rule_ids=[], operation=None,
        revalidation_axes_required=[], revision_audit_sha256=None, status=None)


def check(record, previous, candidate=None, human_records=()):
    previous = _package(previous)
    _keys(record, FIELDS, 'reopening record')
    if record['schema_version'] != SCHEMA or record['status'] != 'RECORDED':
        raise ValueError('completed reopening schema/status required')
    for key in ('author_id', 'version', 'build_id', 'operator_id'):
        _identifier(record[key], key)
    for key in ('persona_payload_sha256', 'knowledge_papers_sha256'):
        _hash(record[key], key)
    prior_binding = bindings(previous['persona'], previous['knowledge'])
    if any(record[key] != prior_binding[key] for key in BINDING_KEYS):
        raise ValueError('supply the exact prior package bound by the reopening record; do not reinterpret stale IDs')
    trigger = record['trigger']
    _keys(trigger, ('kind', 'declared_source_text', 'declared_at'), 'trigger')
    if trigger['kind'] not in TRIGGERS:
        raise ValueError('unsupported trigger kind')
    _text(trigger['declared_source_text'], 'declared_source_text')
    _date(trigger['declared_at'])
    if record['operation'] not in OPERATIONS:
        raise ValueError('unsupported declared operation')
    affected = _ids(record['affected_paper_ids'], 'affected_paper_ids')
    incoming = _ids(record['incoming_paper_ids'], 'incoming_paper_ids')
    declared_rules = _ids(record['affected_rule_ids'], 'affected_rule_ids')
    required = _ids(record['revalidation_axes_required'], 'revalidation_axes_required')
    if not required.issubset(AXES):
        raise ValueError('unknown revalidation axis')
    papers = {p['paper_id'] for p in previous['knowledge']['papers']}
    rules = {r['rule_id']: r['paper_id'] for r in previous['persona'].get('rules', [])}
    if not affected.issubset(papers) or not declared_rules.issubset(rules):
        raise ValueError('affected IDs must exist in the prior package')
    if incoming & papers:
        raise ValueError('incoming IDs must not exist in the prior package')
    if trigger['kind'] == 'new_paper':
        if not incoming:
            raise ValueError('new_paper requires incoming_paper_ids')
    elif incoming:
        raise ValueError('incoming_paper_ids are reserved for a new_paper trigger')
    if trigger['kind'] in ('correction', 'retraction', 'counterexample') and not affected:
        raise ValueError('this trigger requires affected_paper_ids')
    if record['revision_audit_sha256'] is not None:
        _hash(record['revision_audit_sha256'], 'revision_audit_sha256')
    human = axis(previous['persona'], previous['knowledge'], human_records)
    axes = dict(evidence_integrity='RECOMPUTED_VALID', predictive='NO_RECORD_TYPE',
                human='CURRENT' if human['current_record_count'] else 'STALE' if human['record_count'] else 'NOT_SUPPLIED',
                runtime='NO_RECORD_TYPE')
    comparison = None
    prompts = []
    if candidate is not None:
        candidate = _package(candidate)
        difference = compare(previous, candidate)
        changed = set(difference['removed_paper_ids']) | {p['paper_id'] for p in difference['modified_papers']}
        added = set(difference['added_paper_ids'])
        impacted_rules = {rid for rid, paper_id in rules.items() if paper_id in changed}
        undeclared_papers = (changed - affected) | (added - incoming)
        undeclared_rules = impacted_rules - declared_rules
        if undeclared_papers:
            prompts.append('UNDECLARED_PAPER_CHANGE')
        if undeclared_rules:
            prompts.append('RULES_ON_CHANGED_PAPERS_NOT_DECLARED')
        if difference['rule_payload_changed'] and not difference['evidence_changed']:
            prompts.append('RULE_POSITIONS_CHANGED_WITHOUT_PAPER_CHANGE')
        comparison = dict(candidate=bindings(candidate['persona'], candidate['knowledge']),
            added_paper_ids=sorted(added), changed_prior_paper_ids=sorted(changed),
            prior_rules_on_changed_papers=sorted(impacted_rules),
            undeclared_paper_ids=sorted(undeclared_papers), undeclared_prior_rule_ids=sorted(undeclared_rules),
            declared_incoming_not_added=sorted(incoming - added),
            evidence_changed=difference['evidence_changed'], rule_payload_changed=difference['rule_payload_changed'],
            candidate_rule_ids_interpreted=False)
    return dict(status='REOPENING_RECORD_CHECKED', schema_version=SCHEMA,
        record_sha256=payload_sha256(record), record_hash_kind='logical JSON payload hash, not file bytes',
        prior_package=prior_binding, prior_package_binding='PRIOR_RELEASE_FILE_MATCHES_RECORD',
        trigger_kind=trigger['kind'], trigger_declared_at=trigger['declared_at'], trigger_authenticity='NOT_VERIFIED',
        operation=record['operation'], operation_verification='DECLARED_NOT_VERIFIED',
        affected_paper_ids=sorted(affected), incoming_paper_ids=sorted(incoming), affected_rule_ids=sorted(declared_rules),
        revalidation_axes_required=sorted(required), revalidation_axis_status=axes,
        human_record_hashes=[row['record_sha256'] for row in human['records']],
        revision_audit_sha256=record['revision_audit_sha256'], revision_audit_verification='DECLARED_NOT_VERIFIED',
        candidate_comparison=comparison, review_prompts=prompts,
        verdict='NOT_DERIVED', release_decision='NOT_RECORDED', aggregate_score='NOT_COMPUTED',
        llm_used=False, canonical_update_performed=False, persona_payload_modified=False, boundary=BOUNDARY)


def status(previous, records=(), human_records=()):
    previous = _package(previous)
    human_records = list(human_records)
    axis(previous['persona'], previous['knowledge'], human_records)
    rows = [check(record, previous, human_records=human_records) for record in records]
    if len({row['record_sha256'] for row in rows}) != len(rows):
        raise ValueError('duplicate reopening record')
    return dict(status='RECORDED_CURRENT' if rows else 'NOT_PERFORMED',
        prior_package=bindings(previous['persona'], previous['knowledge']), records=rows,
        record_count=len(rows), verdict='NOT_DERIVED', release_decision='NOT_RECORDED',
        llm_used=False, canonical_update_performed=False, persona_payload_modified=False, boundary=BOUNDARY)


def render(result):
    # ASCII JSON also serves --text: all untrusted controls are escaped.
    output = json.dumps(result, ensure_ascii=True, indent=2) + '\n'
    if len(output.encode('utf-8')) > MAX_OUTPUT_BYTES:
        raise ValueError('reopening output exceeds 16 MiB')
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    blank = sub.add_parser('template', help='Write an incomplete detached reopening declaration')
    blank.add_argument('kind', choices=('reopening',))
    blank.add_argument('package', type=Path)
    blank.add_argument('--output', required=True, type=Path)
    checking = sub.add_parser('check', help='Check prior bindings and optional candidate changes; never approve')
    checking.add_argument('record', type=Path)
    checking.add_argument('package', type=Path)
    checking.add_argument('candidate', type=Path, nargs='?')
    reporting = sub.add_parser('status', help='Report records bound to the exact prior package')
    reporting.add_argument('package', type=Path)
    reporting.add_argument('--reopening', type=Path, action='append', default=[])
    for command in (checking, reporting):
        command.add_argument('--human-validation', type=Path, action='append', default=[])
        command.add_argument('--text', action='store_true')
        add_output_argument(command)
    args = parser.parse_args()
    preflight(parser, args.output)
    read = bounded_reader()
    try:
        package = read(args.package)
        if args.command == 'template':
            value = template(package)
            write_exclusive(render(value).encode('utf-8'), args.output)
            result = dict(status='REOPENING_TEMPLATE_WRITTEN', template_sha256=payload_sha256(value),
                next_step='Supply trigger, IDs, operation and revalidation plan; set status RECORDED, then check.',
                verdict='NOT_DERIVED', llm_used=False, persona_payload_modified=False, boundary=BOUNDARY)
        else:
            human = [read(path) for path in args.human_validation]
            result = check(read(args.record), package, read(args.candidate) if args.candidate else None, human) \
                if args.command == 'check' else status(package, [read(path) for path in args.reopening], human)
        output = render(result)
    except (ValueError, OSError, KeyError, TypeError, AttributeError, RecursionError, RuntimeError):
        parser.exit(1, 'invalid reopening input or unavailable output; no release decision was made\n')
    emit(parser, output.encode('utf-8'), None if args.command == 'template' else args.output)


if __name__ == '__main__':
    main()
