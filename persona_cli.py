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

BOUNDARY = (
    "Boundary: the dispatcher only locates a root script and runs it in-process through runpy with\n"
    "the given arguments; it changes none of a script's arguments, outputs or exit codes, and the\n"
    "documented `python <script>.py ...` form remains the primary command. It performs no scientific\n"
    "judgement, calls no model, reads no network and validates no package itself; the dispatcher\n"
    "writes no file, and whatever a script writes is that script's documented behaviour. `list` is a\n"
    "discovery aid over the scripts that have an `if __name__ == '__main__'` entry point, not an\n"
    "approval of any input."
)


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
    raw = path.read_bytes()
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


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__, epilog=BOUNDARY,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest='command', required=True, metavar='{list,run}')
    commands.add_parser('list', help='print every root script that has a command-line entry point, '
                                     'one line each, with the first sentence of its docstring')
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
        except (OSError, ValueError) as exc:
            parser.exit(1, SELF + ': error: ' + str(exc) + '\n')
        sys.stdout.write(render(rows))
        return 0
    try:
        path = resolve_script(args.script)
    except ValueError as exc:
        parser.exit(2, SELF + ': error: ' + str(exc) + '\n')
    execute(path, args.arguments)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
