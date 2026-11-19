"""Read-only correction report for first-observation imports."""
import json

from corpus_files import load_segment_corpus
from extraction_adapter import MAX_HANDOFF_BYTES
from observation_proposals import prepare_observation_handoff, quote_issue
from persona import payload_sha256
from schema_catalog import check
from strict_json import load


# All input paths, values, and upstream exception messages stay out of reports.
INPUT_ERRORS = (ValueError, OSError, KeyError, TypeError, AttributeError,
                IndexError, OverflowError, RuntimeError)
BOUNDARY = ('Preflight checks only. Import and human review are separate steps. '
            'Semantic support and declared identities remain unverified.')


def _report(status, errors, checked=0, source_basis='UNVERIFIED'):
    return dict(status=status, errors=errors, evidence_rows_checked=checked, source_basis=source_basis,
                import_performed=False, boundary=BOUNDARY)


def _error(code, *path):
    return dict(path=list(path), code=code)


def _encoding_errors(value, path):
    # Only traverse a conforming closed profile. Every emitted key is schema-owned.
    if isinstance(value, dict):
        for key in sorted(value):
            yield from _encoding_errors(value[key], (*path, key))
    elif isinstance(value, list):
        for index, row in enumerate(value):
            yield from _encoding_errors(row, (*path, str(index)))
    elif isinstance(value, str):
        try:
            value.encode('utf-8')
        except UnicodeEncodeError:
            yield _error('NOT_UTF8_ENCODABLE', *path)


def _read_profile(path, label, profile, errors):
    try:
        value = load(path)
    except INPUT_ERRORS:
        errors.append(_error('INPUT_UNREADABLE_OR_INVALID', label))
        return None
    structural_errors = check(profile, value)['errors']
    for error in structural_errors:
        errors.append(_error(error['code'], label, *error['path']))
    if not structural_errors:
        # The actual import hashes the response and emits the declaration as UTF-8.
        # Escaped lone surrogates can survive JSON parsing and the structure check.
        errors.extend(_encoding_errors(value, (label,)))
    return value


def inspect_files(corpus_path, handoff_path, response_path, provenance_path, *, source_root=None):
    """Stop at the first failed stage, collecting independent errors within it."""
    errors = []
    response = _read_profile(response_path, 'response', 'observation-response', errors)
    _read_profile(provenance_path, 'provenance', 'declared-provenance', errors)
    if errors:
        return _report('STRUCTURE_ERRORS', errors)

    try:
        corpus = load(corpus_path)
    except INPUT_ERRORS:
        return _report('CORPUS_REJECTED', [_error('INPUT_UNREADABLE_OR_INVALID', 'corpus')])
    try:
        if source_root is not None:
            corpus = load_segment_corpus(corpus, source_root, max_total_bytes=MAX_HANDOFF_BYTES)
        expected = prepare_observation_handoff(corpus)
    except INPUT_ERRORS:
        return _report('CORPUS_REJECTED', [_error('CORPUS_OR_SOURCE_CHECK_FAILED', 'corpus')])

    source_basis = 'SUPPLIED_SEGMENTS' if source_root is None else 'PINNED_LOCAL_FILES'
    try:
        supplied_digest = payload_sha256(load(handoff_path))
    except INPUT_ERRORS:
        return _report('BINDING_ERRORS', [_error('INPUT_UNREADABLE_OR_INVALID', 'handoff')],
                       source_basis=source_basis)
    if supplied_digest != payload_sha256(expected):
        errors.append(_error('HANDOFF_NOT_CURRENT', 'handoff'))
    if response['handoff_sha256'] != supplied_digest:
        errors.append(_error('RESPONSE_BINDING_MISMATCH', 'response', 'handoff_sha256'))
    if errors:
        return _report('BINDING_ERRORS', errors, source_basis=source_basis)

    papers = {paper['paper_id']: paper for paper in expected['sources']}
    for index, row in enumerate(response['candidates']):
        path = ('response', 'candidates', str(index))
        paper = papers.get(row['paper_id'])
        if paper is None:
            errors.append(_error('UNKNOWN_PAPER', *path, 'paper_id'))
            continue
        issue = quote_issue(paper['segments'], row['locator'], row['evidence_quote'])
        if issue:
            field, code = issue
            errors.append(_error(code, *path, field))
    return _report('EVIDENCE_ERRORS' if errors else 'CHECKS_PASSED',
                   errors, len(response['candidates']), source_basis)


def render(report, format):
    if format == 'json':
        return (json.dumps(report, ensure_ascii=True, indent=2) + '\n').encode('ascii')
    lines = [report['status'], 'Source basis: ' + report['source_basis'],
             'Evidence rows checked: ' + str(report['evidence_rows_checked'])]
    lines.extend('/' + '/'.join(e['path']) + ': ' + e['code'] for e in report['errors'])
    lines.append(BOUNDARY)
    return ('\n'.join(lines) + '\n').encode('ascii')
