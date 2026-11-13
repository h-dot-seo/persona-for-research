"""Freeze a detached declared census and compare package training IDs without revealing withheld IDs."""
import argparse
import copy
import datetime
import json
import re
from pathlib import Path

from exclusive_output import add_output_argument, emit, preflight, write_exclusive
from human_validation import _package, bindings
from persona import payload_sha256
from review_package import display
from strict_json import loads

SCHEMA = 'persona.split-declaration.v1'
SPLITS = ('training', 'holdout', 'comparator', 'excluded')
RELATIONS = ('paper', 'duplicate_of', 'notice_of', 'independent_contribution')
FIELDS = ('schema', 'author_id', 'operator_id', 'declared_at', 'census', 'splits',
          'holdout_reading_declaration', 'status')
HASH_FIELDS = ('census_sha256', 'split_sha256', 'declaration_sha256')
ROW_FIELDS = ('record_id', 'author_id', 'record_relation', 'of_record_id', 'kind',
              'year', 'locator', 'authorized', 'access_restriction')
MAX_RECORDS = 4096
MAX_INPUT_BYTES = 8 * 1024 * 1024
MAX_OUTPUT_BYTES = 16 * 1024 * 1024
BOUNDARY = ('This report concerns only the supplied frozen declaration; multiple declarations may exist for '
    'one author. Dates and operator labels are unauthenticated assertions, and freezing does not prove it '
    'preceded holdout reading or that labels were unseen. Exact ID string matching does not detect aliases '
    'such as DOI versus PMID. No census completeness check, duplicate detection, DOI resolution, access '
    'control, anonymization, scientific validation, model call, network access or canonical update is '
    'performed. Counts and hashes do not reveal listed withheld IDs directly, but enumerable IDs can be '
    'guessed: hashes detect changes, not secrecy or authenticity. Declarations contain sensitive IDs and '
    'must remain outside the public repository. Authorization values are declarations, not permission '
    'to acquire, read or transmit sources. Package payloads are never modified.')


def _keys(value, fields, name):
    if not isinstance(value, dict) or set(value) != set(fields):
        raise ValueError(name + ' has missing or unknown fields')


def _text(value, name, maximum=2000):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(name + ' must be a nonempty bounded string')


def _id(value, name):
    _text(value, name, 128)
    if any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError(name + ' cannot contain control characters')


def _label(value, name):
    _id(value, name)
    if '@' in value:
        raise ValueError(name + ' must be a label, not an email address')


def _date(value):
    if not isinstance(value, str) or re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', value) is None:
        raise ValueError('declared_at must be YYYY-MM-DD')
    try:
        datetime.date(int(value[:4]), int(value[5:7]), int(value[8:]))
    except ValueError as exc:
        raise ValueError('declared_at is not a valid calendar date') from exc


def template(author_id, operator_id):
    _label(author_id, 'author_id')
    _label(operator_id, 'operator_id')
    return dict(schema=SCHEMA, author_id=author_id, operator_id=operator_id,
                declared_at='', census=[], splits={name: [] for name in SPLITS},
                holdout_reading_declaration='', status=None)


def validate_declaration(record, frozen=False):
    """Validate structure and declared isolation; errors never repeat supplied IDs or text."""
    _keys(record, FIELDS + HASH_FIELDS if frozen else FIELDS, 'declaration')
    if record['schema'] != SCHEMA:
        raise ValueError('unsupported split declaration schema')
    if record['status'] != ('FROZEN' if frozen else None):
        raise ValueError('unexpected declaration status')
    _label(record['author_id'], 'author_id')
    _label(record['operator_id'], 'operator_id')
    _date(record['declared_at'])
    _text(record['holdout_reading_declaration'], 'holdout_reading_declaration')
    census = record['census']
    if not isinstance(census, list) or not 1 <= len(census) <= MAX_RECORDS:
        raise ValueError('census must contain 1 to 4096 rows')
    rows = {}
    for row in census:
        _keys(row, ROW_FIELDS, 'census row')
        _id(row['record_id'], 'record_id')
        _label(row['author_id'], 'census author_id')
        if row['record_id'] in rows:
            raise ValueError('duplicate census record_id')
        if row['record_relation'] not in RELATIONS:
            raise ValueError('unknown census record_relation')
        _text(row['kind'], 'kind', 128)
        if row['year'] is not None and (type(row['year']) is not int or not 1 <= row['year'] <= 9999):
            raise ValueError('year must be null or an integer from 1 to 9999')
        _text(row['locator'], 'locator')
        _text(row['access_restriction'], 'access_restriction')
        if type(row['authorized']) is not bool:
            raise ValueError('authorized must be boolean')
        rows[row['record_id']] = row
    _keys(record['splits'], SPLITS, 'splits')
    membership = {}
    for name in SPLITS:
        values = record['splits'][name]
        if not isinstance(values, list) or len(values) > MAX_RECORDS:
            raise ValueError('split must be a bounded array')
        for record_id in values:
            _id(record_id, 'split record_id')
            if record_id in membership:
                raise ValueError('splits must be disjoint with no repeated IDs')
            if record_id not in rows:
                raise ValueError('split ID is absent from census')
            row = rows[record_id]
            if name in ('training', 'holdout') and row['author_id'] != record['author_id']:
                raise ValueError('training and holdout author labels must match declaration')
            if name == 'comparator' and row['author_id'] == record['author_id']:
                raise ValueError('comparator author label must differ from declaration')
            if name == 'training' and (row['kind'] not in ('research', 'review') or row['year'] is None):
                raise ValueError('training requires research/review kind and a year')
            membership[record_id] = name
    if set(membership) != set(rows):
        raise ValueError('splits must cover the census exactly')
    groups = {}
    for record_id, row in rows.items():
        target = row['of_record_id']
        if row['record_relation'] == 'paper':
            if target is not None:
                raise ValueError('paper relation requires a null of_record_id')
            root = record_id
        else:
            _id(target, 'of_record_id')
            if target not in rows or rows[target]['record_relation'] != 'paper':
                raise ValueError('related row must refer directly to an existing paper row')
            root = target
        groups.setdefault(root, set()).add(membership[record_id])
    for names in groups.values():
        if 'training' in names and names.intersection(('holdout', 'comparator')):
            raise ValueError('declared relation group crosses training and withheld/comparator splits')
    if frozen:
        if [row['record_id'] for row in census] != sorted(rows):
            raise ValueError('frozen census must be sorted by record_id')
        for name in SPLITS:
            if record['splits'][name] != sorted(record['splits'][name]):
                raise ValueError('frozen split lists must be sorted')
        if record['census_sha256'] != payload_sha256(census):
            raise ValueError('frozen census hash mismatch')
        expected = {name: payload_sha256(record['splits'][name]) for name in SPLITS}
        if record['split_sha256'] != expected:
            raise ValueError('frozen split hash mismatch')
        unsigned = {key: value for key, value in record.items() if key != 'declaration_sha256'}
        if record['declaration_sha256'] != payload_sha256(unsigned):
            raise ValueError('frozen declaration hash mismatch')
    return rows


def freeze(record):
    validate_declaration(record)
    result = copy.deepcopy(record)
    result['census'].sort(key=lambda row: row['record_id'])
    result['splits'] = {name: sorted(result['splits'][name]) for name in SPLITS}
    result['status'] = 'FROZEN'
    result['census_sha256'] = payload_sha256(result['census'])
    result['split_sha256'] = {name: payload_sha256(result['splits'][name]) for name in SPLITS}
    result['declaration_sha256'] = payload_sha256(result)
    validate_declaration(result, frozen=True)
    return result


def summary(record):
    rows = validate_declaration(record, frozen=True)
    training = [rows[key] for key in record['splits']['training']]
    return dict(declaration_sha256=record['declaration_sha256'], census_sha256=record['census_sha256'],
                split_sha256=dict(record['split_sha256']),
                counts={name: len(record['splits'][name]) for name in SPLITS},
                training_policy_counts={
                    'duplicate_of': sum(row['record_relation'] == 'duplicate_of' for row in training),
                    'notice_of': sum(row['record_relation'] == 'notice_of' for row in training),
                    'authorization_not_declared': sum(not row['authorized'] for row in training)},
                policy_counts_are_verdicts=False)


def check(record, persona, knowledge=None):
    rows = validate_declaration(record, frozen=True)
    persona, knowledge = _package(persona, knowledge)
    differences = []
    if record['author_id'] != persona['author_id']:
        differences.append(dict(code='AUTHOR_LABEL_MISMATCH'))
    membership = {record_id: name for name in SPLITS for record_id in record['splits'][name]}
    for paper in knowledge['papers']:
        paper_id = paper['paper_id']
        name = membership.get(paper_id)
        if name != 'training':
            code = {'holdout': 'HOLDOUT_ID_IN_PACKAGE', 'comparator': 'COMPARATOR_ID_IN_PACKAGE'}.get(
                name, 'PACKAGE_PAPER_NOT_IN_TRAINING_SPLIT')
            differences.append(dict(paper_id=paper_id, code=code))
            continue
        row = rows[paper_id]
        for field in ('kind', 'year', 'authorized'):
            if type(paper.get(field)) is not type(row[field]) or paper.get(field) != row[field]:
                differences.append(dict(paper_id=paper_id, code='TRAINING_METADATA_MISMATCH', field=field))
    return dict(schema='persona.split-check.v1',
                status='PACKAGE_OUTSIDE_DECLARED_TRAINING' if differences else 'PACKAGE_WITHIN_DECLARED_TRAINING',
                package=bindings(persona, knowledge), package_paper_count=len(knowledge['papers']),
                differences=differences, declaration=summary(record), boundary=BOUNDARY)


def status(persona, knowledge=None, record=None):
    if record is not None:
        return check(record, persona, knowledge)
    persona, knowledge = _package(persona, knowledge)
    return dict(schema='persona.split-check.v1', status='NOT_DECLARED',
                package=bindings(persona, knowledge), package_paper_count=len(knowledge['papers']),
                differences=[], declaration=None, boundary=BOUNDARY)


def render(result):
    lines = ['Split declaration report', 'Status: ' + result['status']]
    if 'package' in result:
        lines.extend(['Package: ' + ' | '.join(display(result['package'][key]) for key in ('author_id', 'version', 'build_id')),
                      'Package paper count: ' + str(result['package_paper_count'])])
    declared = result.get('declaration')
    if declared is not None:
        lines.append('Declaration sha256: ' + declared['declaration_sha256'])
        lines.append('Census sha256: ' + declared['census_sha256'])
        for name in SPLITS:
            lines.append(name + ': count=' + str(declared['counts'][name]) + '; sha256=' + declared['split_sha256'][name])
        lines.append('Training policy counts (not verdicts): ' + json.dumps(declared['training_policy_counts'], sort_keys=True))
    for difference in result.get('differences', []):
        lines.append('Difference: ' + difference['code'] +
                     ('; package paper=' + display(difference['paper_id']) if 'paper_id' in difference else '') +
                     ('; field=' + difference['field'] if 'field' in difference else ''))
    lines.append('Boundary: ' + BOUNDARY)
    return '\n'.join(lines) + '\n'


def bounded_reader():
    remaining = [MAX_INPUT_BYTES]
    def read(path):
        path = Path(path).absolute()
        if any(item.is_symlink() for item in (path, *path.parents)):
            raise ValueError('input path must not contain symlinks')
        with path.open('rb') as stream:
            raw = stream.read(remaining[0] + 1)
        remaining[0] -= len(raw)
        if remaining[0] < 0:
            raise ValueError('combined split declaration inputs exceed 8 MiB')
        try:
            return loads(raw)
        except (ValueError, TypeError, RecursionError) as exc:
            # Strict parser diagnostics can include arbitrary duplicate object keys.
            # Private input text is never copied into this command's error report.
            raise ValueError('invalid strict JSON input; details withheld') from exc
    return read


def encode(value):
    raw = (json.dumps(value, ensure_ascii=True, indent=2) + '\n').encode('utf-8')
    if len(raw) > MAX_OUTPUT_BYTES:
        raise ValueError('split declaration output exceeds 16 MiB')
    return raw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    blank = sub.add_parser('template', help='Write a blank declaration; no source selection is inferred')
    blank.add_argument('--author-id', required=True)
    blank.add_argument('--operator-id', required=True)
    blank.add_argument('--output', type=Path, required=True)
    freezing = sub.add_parser('freeze', help='Validate, sort and hash a declaration into a new private file')
    freezing.add_argument('declaration', type=Path)
    freezing.add_argument('--output', type=Path, required=True)
    checking = sub.add_parser('check', help='Check frozen declaration against a bound package; differences exit 1')
    checking.add_argument('record', type=Path)
    checking.add_argument('persona', type=Path)
    checking.add_argument('knowledge', type=Path, nargs='?')
    reporting = sub.add_parser('status', help='Report only; no declaration means NOT_DECLARED')
    reporting.add_argument('persona', type=Path)
    reporting.add_argument('knowledge', type=Path, nargs='?')
    reporting.add_argument('--split', type=Path)
    for command in (checking, reporting):
        command.add_argument('--text', action='store_true')
        add_output_argument(command)
    args = parser.parse_args()
    preflight(parser, args.output)
    read = bounded_reader()
    code = 0
    try:
        if args.command == 'template':
            record = template(args.author_id, args.operator_id)
            write_exclusive(encode(record), args.output)
            result = dict(status='SPLIT_TEMPLATE_WRITTEN', template_sha256=payload_sha256(record),
                          next_step='Fill the private declaration; the blank template cannot be frozen.', boundary=BOUNDARY)
        elif args.command == 'freeze':
            record = freeze(read(args.declaration))
            write_exclusive(encode(record), args.output)
            result = dict(status='DECLARATION_FROZEN', declaration=summary(record), boundary=BOUNDARY)
        else:
            persona = read(args.persona)
            knowledge = read(args.knowledge) if args.knowledge else None
            if args.command == 'check':
                result = check(read(args.record), persona, knowledge)
                code = int(result['status'] != 'PACKAGE_WITHIN_DECLARED_TRAINING')
            else:
                result = status(persona, knowledge, read(args.split) if args.split else None)
        raw = render(result).encode('utf-8') if getattr(args, 'text', False) else encode(result)
        if len(raw) > MAX_OUTPUT_BYTES:
            raise ValueError('split declaration output exceeds 16 MiB')
    except (ValueError, OSError, KeyError, TypeError, AttributeError, RecursionError, RuntimeError) as exc:
        parser.exit(1, str(exc) + '\n')
    emit(parser, raw, args.output if args.command in ('check', 'status') else None)
    return code


if __name__ == '__main__':
    raise SystemExit(main())
