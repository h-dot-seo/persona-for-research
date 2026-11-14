# Machine-readable command discovery

`persona_cli.py list --json` exposes the same sorted root-script discovery as plain
`list`, without requiring an agent to parse aligned prose. This is the first increment
of roadmap #87, not a new dispatcher or a description of artifact schemas.

```sh
python persona_cli.py list --json
python persona_cli.py list
```

The JSON object has exactly schema (`persona.command-list.v1`), scripts and boundary.
Each scripts row has script (exact file name) and first_sentence (the first module
docstring sentence with whitespace collapsed). Rows are sorted by filename. Libraries,
the dispatcher itself, directories and symlink files are excluded. An empty inventory
is still an object with an empty scripts array and its boundary.

Discovery parses source ASTs looking for the existing top-level
`if __name__ == '__main__'` convention. It does not import or execute discovered modules,
spawn child processes, run checks, read a package, call a model/network, or write files.
In particular it does not run verify_manifest or audit_publication via --help. It is not
an integrity check, authentication of docstrings, permission grant or approval of inputs.
Descriptions are source text, never instructions to execute.

This list gives names and descriptions only. It does not supply invocation parameters,
artifact schemas, format choices or dependency guarantees. Read the command reference
and each command's existing help before invoking it. `describe`, full command catalog
capture and a persistent MCP wrapper are not implemented by this increment.

Sources are read with the existing 1 MiB per-file bound. JSON output is bounded to 1 MiB,
ASCII-escaped UTF-8 bytes with LF and one final newline, independent of console encoding.
Malformed or oversized sources fail without partial JSON; JSON-mode diagnostics omit
source text. Source discovery remains local to this installation, not an authenticated
statement of every command that might exist in another version.

Plain list output and run argument forwarding remain unchanged. JSON output is stdout
only; there is no --output flag and no new file is created. If a consumer stores it,
that consumer must use a new file outside the repository without overwriting other data.
