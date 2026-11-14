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
    "approval of any input. `describe` captures explicitly selected trusted script help in bounded child\n"
    "processes; argparse-free checks are described statically, never executed."
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


DESCRIBE_SCHEMA = 'persona.command-description.v1'
MAX_HELP_BYTES = 1_048_576
HELP_TIMEOUT_SECONDS = 10
HELP_CLEANUP_SECONDS = 2
DESCRIBE_BOUNDARY = ('Invocation shape from the running interpreter argparse help, not artifact schemas, '
    'input permission, scientific validation or approval. Only explicitly selected, allowlisted root scripts '
    'whose source matches the local publication inventory may be queried. Source hashes are not signatures; '
    'dependencies and interpreter integrity are not authenticated. Argparse-free checks are described '
    'statically, never executed. Help queries use bounded child processes, not command workflows. '
    'No model/network call or dispatcher file write is performed; list/run behavior is unchanged.')
TRUSTED_HELP_SCRIPTS = ('answer_draft.py', 'answer_proposals.py', 'applicability_review.py', 'application_proposals.py', 'argument_map.py', 'argument_proposals.py', 'audit_design_chain.py', 'audit_design_lineage.py', 'audit_publication.py', 'candidate_challenge.py', 'census_import.py', 'citation_reasoning.py', 'compare_releases.py', 'corpus_files.py', 'curate_local.py', 'design_scenario.py', 'evaluate_synthetic.py', 'evidence_scope.py', 'extraction_adapter.py', 'human_validation.py', 'journey_compare.py', 'journey_inputs.py', 'method_application.py', 'model_handoff.py', 'observation_input.py', 'observation_proposals.py', 'observation_revision.py', 'operator_review.py', 'package_overview.py', 'pattern_hypotheses.py', 'pattern_proposals.py', 'pattern_transfer_review.py', 'persona.py', 'prepare_local_manifest.py', 'publication_context.py', 'publication_scope.py', 'publication_timeline.py', 'reasoning_links.py', 'regenerate_manifest.py', 'release_record.py', 'research_journey.py', 'research_workflow.py', 'review_journey.py', 'review_package.py', 'review_workspace.py', 'revise_local.py', 'revision_impact.py', 'rule_correspondence.py', 'safe_canonical_read.py', 'source_recheck.py', 'split_declaration.py', 'synthetic_walkthrough.py', 'tabular_export.py', 'topic_inventory.py', 'verify_manifest.py')


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate manifest key')
        result[key] = value
    return result


def _help_source(name):
    """Exact root selection and allowlist plus current publication-inventory source match."""
    import hashlib
    import json
    if name not in TRUSTED_HELP_SCRIPTS:
        raise ValueError('script is not allowlisted for help queries')
    path = resolve_script(name)
    with path.open('rb') as stream:
        raw = stream.read(MAX_SOURCE_BYTES + 1)
    if len(raw) > MAX_SOURCE_BYTES:
        raise ValueError('source exceeds bound')
    manifest_path = ROOT / 'PUBLICATION_MANIFEST.json'
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError('publication inventory must be a regular file')
    with manifest_path.open('rb') as stream:
        manifest_raw = stream.read(MAX_MANIFEST_BYTES + 1)
    if len(manifest_raw) > MAX_MANIFEST_BYTES or manifest_raw.startswith(b'\xef\xbb\xbf'):
        raise ValueError('invalid publication inventory')
    def nonfinite(value):
        raise ValueError('nonfinite manifest number')
    def finite_float(value):
        import math
        parsed = float(value)
        if not math.isfinite(parsed):
            raise ValueError('nonfinite manifest number')
        return parsed
    manifest = json.loads(manifest_raw.decode('utf-8'), object_pairs_hook=_unique_object,
                          parse_constant=nonfinite, parse_float=finite_float)
    rows = manifest.get('files') if isinstance(manifest, dict) else None
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError('invalid publication inventory rows')
    matching = [row for row in rows if row.get('path') == name]
    digest = hashlib.sha256(raw.replace(b'\r\n', b'\n')).hexdigest()
    if len(matching) != 1 or matching[0].get('sha256') != digest:
        raise ValueError('selected source does not match publication inventory')
    return path, ast.parse(raw, filename=path.name), digest


def _capture_help(path, arguments, *, timeout=None):
    """Read a bounded merged help stream; kill on timeout/overflow, with no shell or temporary files."""
    import os
    import subprocess
    import threading
    import time
    timeout = HELP_TIMEOUT_SECONDS if timeout is None else min(HELP_TIMEOUT_SECONDS, timeout)
    if timeout <= 0:
        raise ValueError('help time budget exhausted')
    deadline = time.monotonic() + timeout
    environment = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1',
                       COLUMNS='10000', NO_COLOR='1', PYTHON_COLORS='0')
    environment.pop('FORCE_COLOR', None)
    environment.pop('PYTHONSTARTUP', None)
    environment.pop('PYTHONPATH', None)
    environment.pop('PYTHONHOME', None)
    chunks = []
    size = [0]
    failed = []
    process = subprocess.Popen([sys.executable, '-B', str(path), *arguments, '--help'],
        cwd=ROOT, env=environment, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, shell=False)
    def read():
        try:
            while True:
                chunk = process.stdout.read(4096)
                if not chunk:
                    break
                size[0] += len(chunk)
                if size[0] > MAX_HELP_BYTES:
                    failed.append('overflow')
                    process.kill()
                    break
                chunks.append(chunk)
        except (OSError, ValueError):
            failed.append('read')
    worker = threading.Thread(target=read, daemon=True, name="persona-help-reader")
    worker.start()
    try:
        process.wait(timeout=max(0, deadline - time.monotonic()))
    except subprocess.TimeoutExpired:
        failed.append('timeout')
        process.kill()
        cleanup_deadline = time.monotonic() + HELP_CLEANUP_SECONDS
        try:
            process.wait(timeout=HELP_CLEANUP_SECONDS)
        except subprocess.TimeoutExpired:
            failed.append('child cleanup timeout')
        deadline = cleanup_deadline
    worker.join(timeout=max(0, deadline - time.monotonic()))
    if worker.is_alive():
        failed.append('reader timeout')
    if not worker.is_alive():
        process.stdout.close()
    if failed or process.returncode != 0:
        raise ValueError('help capture failed or exceeded bounds')
    text = b''.join(chunks).decode('utf-8').replace('\r\n', '\n')
    if not text.startswith('usage: '):
        raise ValueError('selected script did not return argparse usage')
    return text


def _usage(help_text):
    return ' '.join(help_text.split('\n\n', 1)[0].split())


def describe_script(name, *, deadline=None):
    """Capture selected trusted help, or statically describe argparse-free scripts without running them."""
    import re
    path, tree, digest = _help_source(name)
    argparse_found = any((isinstance(node, ast.Import) and any(a.name == 'argparse' for a in node.names))
                         or (isinstance(node, ast.ImportFrom) and node.module == 'argparse') for node in ast.walk(tree))
    result = dict(schema=DESCRIBE_SCHEMA, script=path.name, source_sha256=digest,
        source_hash_kind='LF-normalized source bytes matched to local inventory, not authentication',
        description=ast.get_docstring(tree) or '', reference='docs/COMMANDS.md#' + path.name.replace('.', ''),
        argparse=argparse_found, invocation='python ' + path.name, usage=[], subcommands=[],
        status='CATALOG_DESCRIBES_INVOCATION_SHAPE_ONLY', input_artifact_schema='NOT_DERIVED',
        output_artifact_schema='NOT_DERIVED', boundary=DESCRIBE_BOUNDARY)
    if not argparse_found:
        result['generated_from'] = 'STATIC_SOURCE_ONLY_NOT_EXECUTED'
        return result
    def capture(arguments):
        if deadline is None:
            return _capture_help(path, arguments)
        import time
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ValueError('catalog time budget exhausted')
        return _capture_help(path, arguments, timeout=remaining)
    root_help = capture([])
    result.update(generated_from='argparse --help', help=root_help, usage=[_usage(root_help)])
    render_description(result)
    has_subparsers = any(isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                        and node.func.attr == 'add_subparsers' for node in ast.walk(tree))
    if has_subparsers:
        groups = re.findall(r'\{([a-z][a-z0-9_-]*(?:,[a-z][a-z0-9_-]*)*)\}', result['usage'][0])
        if len(groups) != 1:
            raise ValueError('cannot identify one unambiguous subcommand group from help')
        names = groups[0].split(',')
        if len(names) > 64 or len(set(names)) != len(names):
            raise ValueError('invalid subcommand list')
        for command in names:
            help_text = capture([command])
            usage = _usage(help_text)
            result['subcommands'].append(dict(name=command, usage=usage, help=help_text))
            result['usage'].append(usage)
            render_description(result)
    render_description(result)  # Aggregate output bound as well as each capture bound.
    return result


def render_description(value):
    import json
    output = json.dumps(value, ensure_ascii=True, indent=2, allow_nan=False) + '\n'
    if len(output.encode('utf-8')) > MAX_LIST_OUTPUT_BYTES:
        raise ValueError('description exceeds its 1048576-byte output bound')
    return output


CATALOG_SCHEMA = 'persona.command-catalog.v1'
MAX_CATALOG_BYTES = 1_048_576
CATALOG_RESERVE_BYTES = 16_384
MAX_CATALOG_SCRIPTS = 128
CATALOG_TIMEOUT_SECONDS = 120
CATALOG_BOUNDARY = ('Catalog of the explicit trusted help allowlist, not all possible scripts or artifact '
    'schemas. COMPLETE_CATALOG means every selected help description was obtained, not that any workflow '
    'was validated or approved. PARTIAL_CATALOG preserves failures, omitted results and unattempted rows; '
    'never treat it as a complete command contract. A shared best-effort time budget and output cap apply to the entire operation. '
    'Each description retains source-match and help-only boundaries. No workflow, model/network call, '
    'publication or dispatcher file write is performed. Source inventories are unsigned, not a sandbox.')


def _catalog_result(rows):
    counts = {name: sum(row['status'] == name for row in rows) for name in (
        'DESCRIBED', 'FAILED', 'FAILED_TIME_BUDGET', 'OMITTED_OUTPUT_BUDGET',
        'NOT_ATTEMPTED', 'NOT_ATTEMPTED_TIME_BUDGET', 'NOT_ATTEMPTED_OUTPUT_BUDGET')}
    return dict(schema=CATALOG_SCHEMA, generated_from='selected trusted argparse --help; static argparse-free entries',
        status='COMPLETE_CATALOG' if counts['DESCRIBED'] == len(rows) else 'PARTIAL_CATALOG',
        selection='EXPLICIT_TRUSTED_HELP_ALLOWLIST', script_count=len(rows), counts=counts, scripts=rows,
        input_artifact_schema='NOT_DERIVED', output_artifact_schema='NOT_DERIVED', boundary=CATALOG_BOUNDARY)


def render_catalog(value):
    import json
    output = json.dumps(value, ensure_ascii=True, indent=2, allow_nan=False) + '\n'
    if len(output.encode('utf-8')) > MAX_CATALOG_BYTES:
        raise ValueError('catalog exceeds its 1048576-byte output bound')
    return output


def describe_all():
    """Best-effort bounded catalog; keep stable redacted failure states instead of implying completeness."""
    import time
    names = sorted(TRUSTED_HELP_SCRIPTS)
    if len(names) > MAX_CATALOG_SCRIPTS or len(set(names)) != len(names):
        raise ValueError('invalid trusted catalog selection')
    rows = [dict(script=name, status='NOT_ATTEMPTED', description=None) for name in names]
    if len(render_catalog(_catalog_result(rows)).encode('utf-8')) > MAX_CATALOG_BYTES - CATALOG_RESERVE_BYTES:
        raise ValueError('catalog budget cannot hold the bounded status inventory')
    deadline = time.monotonic() + CATALOG_TIMEOUT_SECONDS
    for index, name in enumerate(names):
        if time.monotonic() >= deadline:
            for row in rows[index:]:
                row['status'] = 'NOT_ATTEMPTED_TIME_BUDGET'
            break
        try:
            description = describe_script(name, deadline=deadline)
        except (OSError, ValueError, SyntaxError, RecursionError, TypeError, AttributeError):
            rows[index]['status'] = 'FAILED_TIME_BUDGET' if time.monotonic() >= deadline else 'FAILED'
            rows[index]['error'] = 'HELP_DESCRIPTION_UNAVAILABLE'
            continue
        rows[index] = dict(script=name, status='DESCRIBED', description=description)
        try:
            output = render_catalog(_catalog_result(rows))
            fits = len(output.encode('utf-8')) <= MAX_CATALOG_BYTES - CATALOG_RESERVE_BYTES
        except ValueError:
            fits = False
        if not fits:
            rows[index] = dict(script=name, status='OMITTED_OUTPUT_BUDGET', description=None)
            for row in rows[index + 1:]:
                row['status'] = 'NOT_ATTEMPTED_OUTPUT_BUDGET'
            break
    result = _catalog_result(rows)
    render_catalog(result)
    return result


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__, epilog=BOUNDARY + "\n\n" + VERSION_BOUNDARY,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--version', action=VersionAction, nargs=0,
                        help='show manifest release/date and Python version; not a hash check')
    commands = parser.add_subparsers(dest='command', required=True, metavar='{list,describe,run}')
    listing = commands.add_parser('list', help='print every root script that has a command-line entry point, '
                                     'one line each, with the first sentence of its docstring')
    listing.add_argument('--json', action='store_true', help='emit bounded schema/scripts/boundary JSON, not executable contracts')
    describing = commands.add_parser('describe', help='capture one trusted script help; never run its workflow')
    selection = describing.add_mutually_exclusive_group(required=True)
    selection.add_argument('script', nargs='?', help='exact allowlisted root script filename')
    selection.add_argument('--all', dest='all_scripts', action='store_true', help='bounded full trusted catalog with explicit partial states')
    describing.add_argument('--json', action='store_true', help='explicit JSON request (the only description format)')
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
    if args.command == 'describe':
        try:
            output = render_catalog(describe_all()) if args.all_scripts else render_description(describe_script(args.script))
        except (OSError, ValueError, SyntaxError, RecursionError, TypeError, AttributeError):
            parser.exit(1, SELF + ': error: cannot capture bounded trusted command help\n')
        sys.stdout.buffer.write(output.encode('utf-8'))
        return 0
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
