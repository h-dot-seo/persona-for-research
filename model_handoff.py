"""Prepare or import a local model handoff without invoking or transmitting to a model."""
from exclusive_output import add_output_argument, emit, preflight
from handoff_text import render_handoff

import argparse
import json
import sys
from pathlib import Path

from extraction_adapter import prepare_model_handoff, import_model_response, MAX_HANDOFF_BYTES
from corpus_files import load_segment_corpus
from persona import payload_sha256
from strict_json import loads

MAX_INPUT_BYTES = 8 * 1024 * 1024


def load(path):
    with Path(path).open("rb") as stream:
        raw = stream.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError("input JSON exceeds the 8 MiB file limit")
    return loads(raw)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    prepare = commands.add_parser('prepare', help='Export source-containing local request JSON'); add_output_argument(prepare)
    prepare.add_argument('corpus', type=Path)
    prepare.add_argument('--format', choices=('json', 'text'), default='json')
    response_template = commands.add_parser('response-template', help='Prepare an empty response bound to the current handoff'); add_output_argument(response_template)
    response_template.add_argument('corpus', type=Path)
    response_template.add_argument('handoff', type=Path)
    ingest = commands.add_parser('import', help='Check a bound response and separate declared provenance'); add_output_argument(ingest)
    for name in ('corpus', 'handoff', 'response', 'provenance'):
        ingest.add_argument(name, type=Path)
    for command in (prepare, response_template, ingest):
        command.add_argument('--task', choices=('reasoning', 'observations'), default='reasoning')
        command.add_argument('--source-root', type=Path, help='Read and recheck files from a local manifest instead of supplied segments')
    args = parser.parse_args()
    preflight(parser, getattr(args, 'output', None))
    try:
        corpus = load(args.corpus)
        if args.source_root is not None:
            corpus = load_segment_corpus(corpus, args.source_root, max_total_bytes=MAX_HANDOFF_BYTES)
        prepare_handoff, import_response = prepare_model_handoff, import_model_response
        if args.task == 'observations':
            from observation_proposals import prepare_observation_handoff, import_observation_response
            prepare_handoff, import_response = prepare_observation_handoff, import_observation_response
        if args.command == 'prepare':
            result = prepare_handoff(corpus)
        elif args.command == 'response-template':
            handoff = load(args.handoff)
            if payload_sha256(handoff) != payload_sha256(prepare_handoff(corpus)):
                raise ValueError('model handoff changed or is stale for the complete input corpus')
            result = dict(handoff_sha256=payload_sha256(handoff), candidates=[])
        else:
            result = import_response(corpus, load(args.handoff), load(args.response), load(args.provenance))
    except (ValueError, OSError, KeyError, TypeError, AttributeError) as exc:
        parser.exit(1, str(exc) + '\n')
    output = render_handoff(result) if getattr(args, 'format', 'json') == 'text' else json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    emit(parser, output.encode('utf-8'), getattr(args, 'output', None))


if __name__ == '__main__':
    main()
