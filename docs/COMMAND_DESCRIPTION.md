# Selected command help descriptions

`persona_cli.py describe SCRIPT --json` captures the **actual argparse help** of one
explicitly chosen trusted script, including its subcommand help. Unlike list --json,
it gives real usage lines and help text instead of only names and first sentences.
This is roadmap #87's next bounded increment, not an artifact-schema registry.

```sh
python persona_cli.py describe release_record.py --json
python persona_cli.py describe verify_manifest.py --json
```

Only exact root-script names from an explicit maintained allowlist are accepted. The
selected source must match its SHA256 entry in the local PUBLICATION_MANIFEST.json.
This rejects unlisted/new scripts and locally modified selected sources; regenerate the
publication inventory only through the normal reviewed development workflow. The inventory
is not signed, and imported dependencies/interpreter integrity are not authenticated.
Do not use this command on an untrusted checkout as if the allowlist were a sandbox.

## Output and execution boundary

Schema persona.command-description.v1 includes script, source_sha256 (LF-normalized),
source description (module docstring), a mechanical command-reference anchor, argparse,
invocation, usage and subcommands. For argparse scripts, root help and each subcommand's
full help are captured from the running Python interpreter. Subcommand names are extracted
from one unambiguous choice group in root usage after checking that the source declares
subparsers; dynamic parser-building loops therefore use actual help, not invented AST
metadata. Unknown/ambiguous shapes fail rather than guessing. Usage whitespace is joined
for comparison with docs/COMMANDS.md. Subcommand help can contain no per-command prose.

For scripts without argparse import syntax, including verify_manifest.py and
audit_publication.py, no process runs: usage/subcommands are empty and generated_from is
STATIC_SOURCE_ONLY_NOT_EXECUTED. Their invocation is described, not executed with --help
(which would run their checks). The dispatcher itself and libraries cannot be selected.

The description is CATALOG_DESCRIBES_INVOCATION_SHAPE_ONLY. It does not prove accepted
artifact schemas, input permissions, model behavior, output-file safety or scientific
validity. input_artifact_schema/output_artifact_schema remain NOT_DERIVED. Consult the
linked command reference and feature guide for input/output and privacy contracts.

## Bounded help capture

Only the selected allowlisted script receives --help, using sys.executable, shell=False,
a 10-second timeout per help query and a 1 MiB merged output cap. On overflow, timeout,
nonzero exit or unexpected output, capture fails with no partial JSON. At most 64 explicit
subcommands are permitted; combined JSON is capped at 1 MiB after each capture. No
workflow command is run. This is a subprocess help query, not a claim that no Python code
executes: the trusted script's imports and argument-parser setup run before help exits.

The child environment fixes UTF-8, COLUMNS=10000 and disables color and bytecode writes.
No temporary output file is used. JSON uses ASCII-escaped UTF-8/LF independent of console
encoding. Errors omit source/parser diagnostics. Source/manifest reads are each limited
to 1 MiB; duplicate/nonfinite manifest JSON and mismatched source hashes are rejected.
The source hash is a local byte comparison, not a signature or guarantee of safety.

Plain list and run outputs/argument forwarding are unchanged; list still imports no
repository module or subprocess. Describe defaults to JSON, with --json accepted
explicitly. There is no --all, --output or persistent MCP server in this increment.
The dispatcher writes no files; consumers storing stdout must use a new external file
without overwriting other data. Help text is source material, not trusted instructions.
