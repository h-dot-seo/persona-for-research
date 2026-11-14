#!/usr/bin/env python3
"""Discover and run the root command-line scripts from any directory, without changing what any script does."""
import argparse
import ast
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SELF = Path(__file__).name
NAME_WIDTH = 28
MAX_SOURCE_BYTES = 1_048_576
MAX_MANIFEST_BYTES = 1_048_576
MAX_RELEASE_CHARACTERS = 128
MAX_LIST_OUTPUT_BYTES = 1_048_576
LIST_SCHEMA = 'persona.command-list.v1'
LIST_BOUNDARY = ('AST-discovered root entry points and their first docstring sentences only; '
    'not an invocation/schema contract, integrity check, package validation or approval. '
    'No discovered script is imported or executed, no subprocess/model/network call is made and no file is written. '
    'Descriptions are repository source text, not authenticated claims or instructions.')

VERSION_BOUNDARY = (
    "Boundary: manifest labels only; NOT an integrity check or signature.\n"
    "The manifest excludes itself from its hashes; these labels are not authenticated.\n"
    "No file hashes checked, scientific judgement, model call, network access or file writes.\n"
    "For inventory and file-hash checks, run: python verify_manifest.py\n"
)

BOUNDARY = (
    "Boundary: the dispatcher only locates a root script and runs it in-process through runpy with\n"
    "the given arguments; it changes none of a script's arguments, outputs or exit codes, and the\n"
    "documented `python <script>.py ...` form remains the primary command. It performs no scientific\n"
    "judgement, calls no model, reads no network and validates no package itself; the dispatcher\n"
    "writes no file, and whatever a script writes is that script's documented behaviour. `list` is a\n"
    "discovery aid over the scripts that have an `if __name__ == '__main__'` entry point, not an\n"
    "approval of any input."
)


def version_text():
    """Read bounded manifest labels only when requested; never verify file hashes."""
    import datetime
    import json
    import stat
    import strict_json

    manifest_path = ROOT / 'PUBLICATION_MANIFEST.json'
    try:
        info = manifest_path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_MANIFEST_BYTES:
            raise ValueError('not a bounded regular file')
        with manifest_path.open('rb') as stream:
            raw = stream.read(MAX_MANIFEST_BYTES + 1)
        if len(raw) > MAX_MANIFEST_BYTES:
            raise ValueError('manifest too large')
        manifest = strict_json.loads(raw.decode('utf-8'))
        if not isinstance(manifest, dict):
            raise ValueError('not an object')
        release, date = manifest.get('release'), manifest.get('date')
        if (not isinstance(release, str) or not 1 <= len(release) <= MAX_RELEASE_CHARACTERS
                or not release.isprintable() or release.strip() != release):
            raise ValueError('invalid release label')
        if (not isinstance(date, str) or len(date) != 10
                or datetime.date.fromisoformat(date).isoformat() != date):
            raise ValueError('invalid date label')
    except (OSError, ValueError, RecursionError):
        # Never echo untrusted JSON keys, labels, paths or parser diagnostics.
        raise ValueError('cannot read version labels: PUBLICATION_MANIFEST.json must be a '
                         'regular UTF-8 JSON file (no BOM), at most 1048576 bytes, with no '
                         'duplicate keys or non-finite numbers, a printable release label '
                         '(1-128 characters, no edge whitespace) and a YYYY-MM-DD date') from None
    python = '.'.join(str(part) for part in sys.version_info[:3])
    return ('persona-for-research release: ' + json.dumps(release, ensure_ascii=True)
            + '\nManifest date: ' + date + '\nPython: ' + python + '\n' + VERSION_BOUNDARY)


class VersionAction(argparse.Action):
    """Like argparse's version action, but defer all manifest reads until invoked."""

    def __call__(self, parser, namespace, values, option_string=None):
        try:
            text = version_text()
        except ValueError as exc:
            parser.exit(1, SELF + ': error: ' + str(exc) + '\n')
        sys.stdout.write(text)
        parser.exit(0)


def first_sentence(docstring):
    """First sentence of a docstring with whitespace collapsed; empty when there is no docstring."""
    text = ' '.join((docstring or '').split())
    for index, char in enumerate(text):
        if char == '.' and (index + 1 == len(text) or text[index + 1] == ' '):
            return text[:index + 1]
    return text


def has_entry_point(tree):
    """True when the module body has an `if __name__ == '__main__':` block."""
    for node in tree.body:
        if not isinstance(node, ast.If) or not isinstance(node.test, ast.Compare):
            continue
        test = node.test
        if (isinstance(test.left, ast.Name) and test.left.id == '__name__'
                and len(test.ops) == 1 and isinstance(test.ops[0], ast.Eq)
                and len(test.comparators) == 1 and isinstance(test.comparators[0], ast.Constant)
                and test.comparators[0].value == '__main__'):
            return True
    return False


def script_record(path):
    """(name, first docstring sentence) for a root command-line script; None for a library module."""
    with path.open('rb') as stream:
        raw = stream.read(MAX_SOURCE_BYTES + 1)
    if len(raw) > MAX_SOURCE_BYTES:
        raise ValueError(path.name + ' exceeds the ' + str(MAX_SOURCE_BYTES) + '-byte source bound')
    try:
        tree = ast.parse(raw, filename=str(path))
    except (SyntaxError, ValueError) as exc:
        raise ValueError('cannot parse ' + path.name + ': ' + str(exc)) from exc
    if not has_entry_point(tree):
        return None
    return path.name, first_sentence(ast.get_docstring(tree))


def root_files():
    """Exact-case names of the regular `*.py` files at the repository root, other than this dispatcher."""
    return {path.name: path for path in ROOT.glob('*.py')
            if path.name != SELF and path.is_file() and not path.is_symlink()}


def root_scripts():
    """Sorted (name, first sentence) rows for every root script with a command-line entry point."""
    rows = []
    for name in sorted(root_files()):
        record = script_record(ROOT / name)
        if record is not None:
            rows.append(record)
    return rows


def resolve_script(name):
    """Path of one root command-line script named exactly by its file name; ValueError otherwise."""
    if (not isinstance(name, str) or not name or '/' in name or '\\' in name or name.startswith('.')
            or not name.endswith('.py') or name != Path(name).name):
        raise ValueError('run needs the exact file name of a root script, such as persona.py; '
                         'see `python persona_cli.py list`')
    if name == SELF:
        raise ValueError(SELF + ' does not run itself; see `python persona_cli.py list`')
    files = root_files()
    if name not in files:
        raise ValueError(name + ' is not a root script of this repository; see `python persona_cli.py list`')
    if script_record(files[name]) is None:
        raise ValueError(name + ' is a library module without a command-line entry point; '
                         'see `python persona_cli.py list`')
    return files[name]


def execute(path, arguments):
    """Run one root script as `__main__` with its own argv; SystemExit and exit codes pass through."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    sys.argv = [str(path), *arguments]
    runpy.run_path(str(path), run_name='__main__')


def render(rows):
    return ''.join((name.ljust(NAME_WIDTH) + ' ' + sentence).rstrip() + '\n' for name, sentence in rows)


def render_json(rows):
    """Bounded deterministic machine-readable discovery; preserve the plain list contract."""
    import json
    value = dict(schema=LIST_SCHEMA,
                 scripts=[dict(script=name, first_sentence=sentence) for name, sentence in rows],
                 boundary=LIST_BOUNDARY)
    output = json.dumps(value, ensure_ascii=True, indent=2, allow_nan=False) + '\n'
    if len(output.encode('utf-8')) > MAX_LIST_OUTPUT_BYTES:
        raise ValueError('command list JSON exceeds its 1048576-byte output bound')
    return output


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__, epilog=BOUNDARY + "\n\n" + VERSION_BOUNDARY,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--version', action=VersionAction, nargs=0,
                        help='show manifest release/date and Python version; not a hash check')
    commands = parser.add_subparsers(dest='command', required=True, metavar='{list,run}')
    listing = commands.add_parser('list', help='print every root script that has a command-line entry point, '
                                     'one line each, with the first sentence of its docstring')
    listing.add_argument('--json', action='store_true', help='emit bounded schema/scripts/boundary JSON, not executable contracts')
    runner = commands.add_parser('run', help='run one root script in-process: '
                                             'python persona_cli.py run <script> [args...]')
    runner.add_argument('script', help='exact file name of a root script, such as persona.py')
    runner.add_argument('arguments', nargs=argparse.REMAINDER, help='passed to the script unchanged')
    return parser


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    if argv[:1] == ['run'] and len(argv) >= 2 and not argv[1].startswith('-'):
        # Everything after the script name belongs to the script, including -h and --help.
        try:
            path = resolve_script(argv[1])
        except ValueError as exc:
            sys.stderr.write(SELF + ': error: ' + str(exc) + '\n')
            return 2
        execute(path, argv[2:])
        return 0
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == 'list':
        try:
            rows = root_scripts()
            output = render_json(rows) if args.json else render(rows)
        except (OSError, ValueError, RecursionError) as exc:
            message = 'cannot produce bounded command list JSON' if args.json else str(exc)
            parser.exit(1, SELF + ': error: ' + message + '\n')
        if args.json:
            sys.stdout.buffer.write(output.encode('utf-8'))
        else:
            sys.stdout.write(output)
        return 0
    try:
        path = resolve_script(args.script)
    except ValueError as exc:
        parser.exit(2, SELF + ': error: ' + str(exc) + '\n')
    execute(path, args.arguments)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
