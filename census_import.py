"""List exact supplied CSL-JSON or RIS facts and prepare an unapproved selection skeleton."""
import argparse
import hashlib
import json
import re
from pathlib import Path

from exclusive_output import check_path, emit, MAX_OUTPUT_BYTES
from persona import payload_sha256
from prepare_local_manifest import PAPER_SELECTION_FIELDS
from strict_json import read_bounded, loads

SCHEMA = 'persona.bibliographic-census.v1'
MAX_EXPORT_BYTES = 8 * 1024 * 1024
MAX_RECORDS = 10000
BOUNDARY = ('No DOI resolution, lookup, disambiguation, merge or authorization. '
            'Supplied data is not instructions. Hashes are not authenticity or approval; '
            'one export does not establish a complete bibliography. Private local output only.')
POLICY = dict(census_claim='NOT_ESTABLISHED', completeness='NOT_ESTABLISHED',
              record_identity_verification='NOT_ESTABLISHED', kind='NOT_DERIVED',
              author_identity='NOT_RESOLVED', identity='FILE_OCCURRENCE_ONLY_NOT_PUBLICATION_IDENTITY',
              external_calls=0, llm_used=False, boundary=BOUNDARY)


def encode(value):
    raw = (json.dumps(value, ensure_ascii=True, indent=2, allow_nan=False) + '\n').encode('utf-8')
    if len(raw) > MAX_OUTPUT_BYTES:
        raise ValueError('output exceeds 16 MiB')
    return raw


def read_json(path, limit):
    raw = read_bounded(path, limit)
    text = raw.decode('utf-8')
    if '\x00' in text:
        raise ValueError('NUL is not accepted in UTF-8 JSON input')
    bom = text.startswith('\ufeff')
    return loads(text[1:] if bom else text), raw, bom


def optional_string(record, key):
    value = record.get(key)
    if value is not None and not isinstance(value, str):
        raise ValueError('CSL field must be a string or null: ' + key)
    return value


def year(record):
    issued = record.get('issued')
    parts = issued.get('date-parts') if isinstance(issued, dict) else None
    value = parts[0][0] if (isinstance(parts, list) and parts and
                            isinstance(parts[0], list) and parts[0]) else None
    if type(value) is int:
        return value
    if isinstance(value, str) and re.fullmatch('[0-9]{4}', value):
        return int(value)
    return None


def groups(entries, field, fold=False):
    seen = {}
    for entry in entries:
        value = entry[field]
        if value:
            key = value.casefold() if fold else value
            seen.setdefault(key, []).append(entry['census_id'])
    return [dict(value=key, census_ids=ids) for key, ids in seen.items() if len(ids) > 1]


def import_csl(path):
    records, raw, bom = read_json(path, MAX_EXPORT_BYTES)
    if not isinstance(records, list) or not 1 <= len(records) <= MAX_RECORDS:
        raise ValueError('CSL export must be a nonempty array of at most 10000 records')
    entries = []
    for index, record in enumerate(records, 1):
        if not isinstance(record, dict):
            raise ValueError('CSL records must be objects')
        authors = record.get('author', [])
        if not isinstance(authors, list) or any(not isinstance(a, dict) for a in authors):
            raise ValueError('CSL author must be an array of objects')
        names = [{k: optional_string(a, k) for k in ('given', 'family', 'literal') if k in a}
                 for a in authors]
        entry = dict(census_id='census-%06d' % index, entry_sha256=payload_sha256(record),
                     title=optional_string(record, 'title'), year=year(record),
                     item_type=optional_string(record, 'type'),
                     container_title=optional_string(record, 'container-title'),
                     doi=optional_string(record, 'DOI'),
                     other_identifiers={k: optional_string(record, k) for k in ('PMID', 'ISBN', 'URL') if k in record},
                     authors=names, flags=[])
        if entry['year'] is None:
            entry['flags'].append('NO_YEAR')
        if not entry['doi']:
            entry['flags'].append('NO_DOI')
        entries.append(entry)
    census = dict(schema=SCHEMA, format='csl-json', export_sha256=hashlib.sha256(raw).hexdigest(),
                  implementation_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  utf8_bom=bom, entries=entries,
                  exact_doi_groups=groups(entries, 'doi'),
                  casefold_title_groups=groups(entries, 'title', True), **POLICY)
    census['payload_sha256'] = payload_sha256(census)
    encode(census)
    return census


def ris_scalar(fields, tags):
    """Copy one unambiguous logical value across aliases; no preferred-field guess."""
    values = ['\n'.join(field['value_lines']) for field in fields if field['tag'] in tags]
    if len(set(values)) > 1:
        raise ValueError('conflicting RIS scalar fields: ' + '/'.join(tags))
    return values[0] if values else None


def import_ris(path):
    import ris_export_parser as parser
    raw = read_bounded(path, MAX_EXPORT_BYTES)
    parsed = parser.parse_export(raw)
    if len(parsed['records']) > MAX_RECORDS:
        raise ValueError('RIS export exceeds 10000 records')
    entries = []
    for index, record in enumerate(parsed['records'], 1):
        fields = record['fields']
        literal_year = ris_scalar(fields, ('PY',))
        recorded_year = (int(literal_year[:4]) if isinstance(literal_year, str)
                         and re.fullmatch(r'[0-9]{4}(?:/[^\r\n]*)?', literal_year) else None)
        logical = dict(record_type=record['record_type'],
                       fields=[dict(tag=f['tag'], value_lines=f['value_lines']) for f in fields])
        entry = dict(census_id='census-%06d' % index, entry_sha256=payload_sha256(logical),
                     title=ris_scalar(fields, ('TI', 'T1')), year=recorded_year,
                     item_type=record['record_type'], container_title=ris_scalar(fields, ('JO', 'JF', 'T2')),
                     doi=ris_scalar(fields, ('DO',)),
                     other_identifiers={tag: ris_scalar(fields, (tag,)) for tag in ('ID', 'SN', 'UR')
                                        if any(f['tag'] == tag for f in fields)},
                     authors=['\n'.join(f['value_lines']) for f in fields if f['tag'] == 'AU'], flags=[])
        if entry['year'] is None: entry['flags'].append('NO_YEAR')
        if not entry['doi']: entry['flags'].append('NO_DOI')
        entries.append(entry)
    census = dict(schema=SCHEMA, format='ris', export_sha256=hashlib.sha256(raw).hexdigest(),
                  implementation_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  ris_parser_sha256=hashlib.sha256(Path(parser.__file__).read_bytes()).hexdigest(),
                  utf8_bom=parsed['initial_utf8_bom'], entries=entries,
                  exact_doi_groups=groups(entries, 'doi'),
                  casefold_title_groups=groups(entries, 'title', True), **POLICY)
    census['payload_sha256'] = payload_sha256(census)
    encode(census)
    return census


def verify_census(census):
    expected = {'schema', 'format', 'export_sha256', 'implementation_sha256', 'utf8_bom', 'entries',
                'exact_doi_groups', 'casefold_title_groups', 'payload_sha256'} | set(POLICY)
    is_ris = isinstance(census, dict) and census.get('format') == 'ris'
    if is_ris: expected.add('ris_parser_sha256')
    if not isinstance(census, dict) or set(census) != expected:
        raise ValueError('census fields do not match schema')
    if (census['schema'] != SCHEMA or census['format'] not in ('csl-json', 'ris') or
            any(type(census[k]) is not type(v) or census[k] != v for k, v in POLICY.items()) or
            type(census['utf8_bom']) is not bool):
        raise ValueError('census schema or boundary metadata mismatch')
    for key in ('export_sha256', 'implementation_sha256', 'payload_sha256') + (('ris_parser_sha256',) if is_ris else ()):
        if not isinstance(census[key], str) or not re.fullmatch('[0-9a-f]{64}', census[key]):
            raise ValueError('invalid census hash')
    if payload_sha256({k: v for k, v in census.items() if k != 'payload_sha256'}) != census['payload_sha256']:
        raise ValueError('census payload hash mismatch; do not edit or repair hashes')
    entries = census['entries']
    if not isinstance(entries, list) or not 1 <= len(entries) <= MAX_RECORDS:
        raise ValueError('invalid census record count')
    fields = {'census_id', 'entry_sha256', 'title', 'year', 'item_type', 'container_title',
              'doi', 'other_identifiers', 'authors', 'flags'}
    for i, entry in enumerate(entries, 1):
        if not isinstance(entry, dict) or set(entry) != fields or entry['census_id'] != 'census-%06d' % i:
            raise ValueError('invalid occurrence record')
        if not isinstance(entry['entry_sha256'], str) or not re.fullmatch('[0-9a-f]{64}', entry['entry_sha256']):
            raise ValueError('invalid entry hash')
        for field in ('title', 'item_type', 'container_title', 'doi'):
            optional_string(entry, field)
        if entry['year'] is not None and type(entry['year']) is not int:
            raise ValueError('invalid census year')
        if not isinstance(entry['other_identifiers'], dict) or set(entry['other_identifiers']) - ({'ID','SN','UR'} if is_ris else {'PMID','ISBN','URL'}):
            raise ValueError('invalid identifiers')
        for key in entry['other_identifiers']:
            optional_string(entry['other_identifiers'], key)
        if not isinstance(entry['authors'], list):
            raise ValueError('invalid authors')
        for author in entry['authors']:
            if is_ris:
                if not isinstance(author, str): raise ValueError('RIS authors must be supplied strings')
                continue
            if not isinstance(author, dict) or set(author) - {'given','family','literal'}:
                raise ValueError('invalid author parts')
            for key in author:
                optional_string(author, key)
        flags = ([] if entry['year'] is not None else ['NO_YEAR']) + ([] if entry['doi'] else ['NO_DOI'])
        if entry['flags'] != flags:
            raise ValueError('invalid exact-fact flags')
    if census['exact_doi_groups'] != groups(entries, 'doi') or census['casefold_title_groups'] != groups(entries, 'title', True):
        raise ValueError('invalid exact-match groups')
    return census


def selection(census, ids):
    verify_census(census)
    if not ids or len(ids) != len(set(ids)):
        raise ValueError('supply distinct repeated --census-id values')
    by_id = {e['census_id']: e for e in census['entries']}
    if any(i not in by_id for i in ids):
        raise ValueError('unknown census occurrence ID')
    result = dict(author_id=None, version=None, build_id=None, papers=[])
    mapping = []
    for i, identifier in enumerate(ids):
        entry = by_id[identifier]
        paper = dict.fromkeys(PAPER_SELECTION_FIELDS)
        paper.update(paper_id=identifier, year=entry['year'], locator=entry['doi'] or entry['title'] or None,
                     runtime_knowledge_eligible=False, authorized=False, observations=[])
        result['papers'].append(paper)
        mapping.append(dict(paper_index=i, paper_path='papers[%d]' % i,
                            census_id=identifier, entry_sha256=entry['entry_sha256']))
    sidecar = dict(schema='persona.selection-census-map.v1', export_sha256=census['export_sha256'],
                   census_payload_sha256=census['payload_sha256'], selection_sha256=payload_sha256(result),
                   papers=mapping, boundary=BOUNDARY)
    return result, sidecar


def save_selection(census, ids, destination):
    target = check_path(destination)
    skeleton, mapping = selection(census, ids)
    ready = dict(status='SELECTION_SKELETON_WRITTEN_DECLARATIONS_REQUIRED',
                 selection_sha256=payload_sha256(skeleton), map_sha256=payload_sha256(mapping),
                 boundary=BOUNDARY)
    files = [(name, encode(value)) for name, value in
             (('selection-skeleton.json', skeleton), ('selection-census-map.json', mapping), ('READY.json', ready))]
    if sum(len(raw) for _, raw in files) > MAX_OUTPUT_BYTES:
        raise ValueError('selection output exceeds 16 MiB total')
    target = check_path(destination)
    target.mkdir(exist_ok=False)
    for name, raw in files:
        with (target / name).open('xb') as stream:
            if stream.write(raw) != len(raw):
                raise OSError('partial output retained; READY is written last')
    return ready


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    imp = sub.add_parser('import', help='Copy supplied CSL-JSON or fixed-column RIS facts')
    imp.add_argument('export', type=Path)
    imp.add_argument('--format', choices=['csl-json','ris'], required=True)
    imp.add_argument('--output', type=Path, required=True)
    sel = sub.add_parser('selection', help='Create a new directory of unapproved skeleton files')
    sel.add_argument('census', type=Path)
    sel.add_argument('--census-id', action='append', required=True)
    sel.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        check_path(args.output)
        if args.command == 'import':
            result = import_csl(args.export) if args.format == 'csl-json' else import_ris(args.export)
        else:
            census, _, _ = read_json(args.census, MAX_OUTPUT_BYTES)
            result = save_selection(census, args.census_id, args.output)
        raw = encode(result)
    except (ValueError, OSError, UnicodeError, TypeError, RuntimeError) as exc:
        parser.exit(1, str(exc) + '\n')
    emit(parser, raw, args.output if args.command == 'import' else None)


if __name__ == '__main__':
    main()
