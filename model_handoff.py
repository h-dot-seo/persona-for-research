"""Prepare or import a local model handoff without invoking or transmitting to a model."""
import argparse
import json
import sys
from pathlib import Path

from extraction_adapter import prepare_model_handoff, import_model_response
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
    prepare = commands.add_parser('prepare', help='Export source-containing local request JSON')
    prepare.add_argument('corpus', type=Path)
    response_template = commands.add_parser('response-template', help='Prepare an empty response bound to the current handoff')
    response_template.add_argument('corpus', type=Path)
    response_template.add_argument('handoff', type=Path)
    ingest = commands.add_parser('import', help='Check a bound response and separate declared provenance')
    for name in ('corpus', 'handoff', 'response', 'provenance'):
        ingest.add_argument(name, type=Path)
    args = parser.parse_args()
    try:
        corpus = load(args.corpus)
        if args.command == 'prepare':
            result = prepare_model_handoff(corpus)
        elif args.command == 'response-template':
            handoff = load(args.handoff)
            if payload_sha256(handoff) != payload_sha256(prepare_model_handoff(corpus)):
                raise ValueError('model handoff changed or is stale for the complete input corpus')
            result = dict(handoff_sha256=payload_sha256(handoff), candidates=[])
        else:
            result = import_model_response(corpus, load(args.handoff), load(args.response), load(args.provenance))
    except (ValueError, OSError, KeyError, TypeError, AttributeError) as exc:
        parser.exit(1, str(exc) + '\n')
    sys.stdout.buffer.write((json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))


if __name__ == '__main__':
    main()
