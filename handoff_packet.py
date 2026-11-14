#!/usr/bin/env python3
"""Extract a literal bound JSON fence from one supplied message, without model attestation."""
import argparse
import hashlib
import json
from pathlib import Path

from corpus_files import read_source_bytes
from exclusive_output import check_path
from journey_inputs import _checked_path, _plain_components
from persona import payload_sha256
from strict_json import loads

MAX_INPUT_BYTES = 8 * 1024 * 1024
MAX_OUTPUT_BYTES = 16 * 1024 * 1024
BOUNDARY = ('Private message/source text: not permission to publish or transmit. Literal extraction only: '
            'no model execution, role or transcript authentication, semantic validation, approval or '
            'provenance inference. Import must reconstruct and validate the handoff against current inputs. '
            'A bound empty response is not proof that a model answered. READY means files were written, '
            'not acceptance. Failed writes may leave partial files; nothing is automatically deleted.')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def utf8(raw):
    if raw.startswith(b'\xef\xbb\xbf') or b'\0' in raw:
        raise ValueError('UTF-8 without BOM or NUL is required')
    text = raw.decode('utf-8')
    if '\r' in text.replace('\r\n', ''):
        raise ValueError('bare CR is not supported; use LF or CRLF')
    return text


def encode(value):
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf-8')


def extract(transcript, handoff_raw, occurrence=None):
    if len(transcript) + len(handoff_raw) > MAX_INPUT_BYTES:
        raise ValueError('combined input exceeds 8 MiB')
    utf8(transcript)
    handoff = loads(utf8(handoff_raw))
    if not isinstance(handoff, dict):
        raise ValueError('handoff must be a JSON object; current-input validity is not checked here')
    bound = payload_sha256(handoff)
    if occurrence is not None and (type(occurrence) is not int or occurrence < 1):
        raise ValueError('occurrence must be a positive integer')
    matches = []
    opened = None
    offset = 0
    for line in transcript.splitlines(keepends=True):
        body = line[:-2] if line.endswith(b'\r\n') else line[:-1] if line.endswith(b'\n') else line
        if body.lstrip().startswith((b'```', b'~~~')):
            if body not in (b'```json', b'```'):
                raise ValueError('unsupported fence syntax; only exact standalone ```json and ``` lines are supported')
            if body == b'```json':
                if opened is not None:
                    raise ValueError('nested JSON fence is not supported')
                opened = (offset, offset + len(line))
            else:
                if opened is None:
                    raise ValueError('closing fence without an opening JSON fence')
                start, content_start = opened
                raw = transcript[content_start:offset]
                value = loads(utf8(raw))
                if isinstance(value, dict) and value.get('handoff_sha256') == bound:
                    if set(value) != {'handoff_sha256', 'candidates'} or not isinstance(value['candidates'], list):
                        raise ValueError('bound response requires exactly handoff_sha256 and candidates list')
                    matches.append((start, offset + len(line), content_start, offset))
                opened = None
        offset += len(line)
    if opened is not None:
        raise ValueError('unclosed JSON fence')
    if not matches:
        raise ValueError('NO_BOUND_RESPONSE')
    if occurrence is None and len(matches) != 1:
        raise ValueError('AMBIGUOUS_BOUND_RESPONSES: supply --occurrence explicitly')
    selected = 1 if occurrence is None else occurrence
    if selected > len(matches):
        raise ValueError('occurrence exceeds the bound response count')
    start, end, content_start, content_end = matches[selected-1]
    response = transcript[content_start:content_end]
    receipt = dict(schema='persona.response-extraction.v1',
                   status='LITERAL_FENCE_EXTRACTED_NOT_MODEL_ATTESTATION',
                   transcript_sha256=digest(transcript), handoff_sha256=bound,
                   selected_fence_sha256=digest(transcript[start:end]), response_sha256=digest(response),
                   occurrence=selected, bound_response_count=len(matches),
                   selection='EXPLICIT_OCCURRENCE' if occurrence is not None else 'ONLY_BOUND_RESPONSE',
                   fence_byte_start=start, fence_byte_end=end,
                   response_byte_start=content_start, response_byte_end=content_end,
                   model_execution_verified=False, transcript_authenticated=False,
                   role_authenticated=False, semantic_validation='NOT_PERFORMED', boundary=BOUNDARY)
    ready = dict(status='EXTRACTION_FILES_WRITTEN_NOT_APPROVAL', response_sha256=digest(response),
                 receipt_sha256=digest(encode(receipt)), boundary=BOUNDARY)
    files = [('response.json', response), ('extraction-receipt.json', encode(receipt)), ('READY.json', encode(ready))]
    if sum(len(raw) for _, raw in files) > MAX_OUTPUT_BYTES:
        raise ValueError('combined output exceeds 16 MiB')
    return files, ready


def destination(path):
    _plain_components(Path(path).absolute().parent)
    return check_path(path)


def save(files, path):
    target = destination(path)
    target.mkdir(exist_ok=False)
    for name, raw in files:
        with (target/name).open('xb') as stream:
            if stream.write(raw) != len(raw):
                raise OSError('partial output retained; READY is written last')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('extract-response', help='Extract one literal bound JSON fence')
    p.add_argument('transcript', type=Path)
    p.add_argument('handoff', type=Path)
    p.add_argument('--output-dir', type=Path, required=True, metavar='NEW_DIR')
    p.add_argument('--occurrence', type=int)
    args = parser.parse_args()
    try:
        destination(args.output_dir)
        remaining = MAX_INPUT_BYTES
        inputs = []
        for path in (args.transcript, args.handoff):
            path, _ = _checked_path(path)
            raw = read_source_bytes(path, max_bytes=remaining)
            remaining -= len(raw)
            inputs.append(raw)
        files, ready = extract(*inputs, occurrence=args.occurrence)
        save(files, args.output_dir)
    except (ValueError, OSError, RuntimeError, TypeError, RecursionError) as exc:
        parser.exit(1, str(exc) + '\n')
    print(encode(ready).decode('utf-8'), end='')


if __name__ == '__main__':
    main()
