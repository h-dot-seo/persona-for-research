# Bounded trusted command catalog

`persona_cli.py describe --all --json` collects the existing selected-command descriptions
into one machine-readable catalog. It closes roadmap #87's aggregate-discovery gap without
adding MCP, new trust rules or a new command execution mechanism.

```sh
python persona_cli.py describe --all --json
```

Selection is exactly the sorted, explicitly maintained TRUSTED_HELP_SCRIPTS allowlist,
not arbitrary discovered modules. Existing source-inventory matching, actual bounded
argparse help and static handling of argparse-free checks remain unchanged. See
[Selected command descriptions](COMMAND_DESCRIPTION.md) for those trust limitations.
`--all` is an explicit request to inspect that whole allowlist. It cannot accompany a
single script argument. Existing single describe/list/run outputs are unchanged.

## Complete and partial results

Schema persona.command-catalog.v1 includes selection, script_count, scripts, counts,
status and boundary. Each row has script, status and description. Successful rows are
DESCRIBED with the existing description object; unsuccessful rows have description null.

- COMPLETE_CATALOG: every selected description was obtained, including static entries.
  This is not workflow validation, input approval or an artifact-schema guarantee.
- PARTIAL_CATALOG: one or more rows failed, were omitted or were not attempted.
  Never use this result as if it described the complete selected surface.
- FAILED: description failed; the fixed error is HELP_DESCRIPTION_UNAVAILABLE. Private
  exception messages, parser errors and local paths are not copied into the catalog.
- FAILED_TIME_BUDGET: an attempted description failed after the shared deadline.
- OMITTED_OUTPUT_BUDGET: a description was obtained but could not fit the aggregate budget.
- NOT_ATTEMPTED_TIME_BUDGET / NOT_ATTEMPTED_OUTPUT_BUDGET: remaining rows were not queried.
  Earlier successful descriptions are retained. NOT_ATTEMPTED is an internal initial
  state; normal completed catalogs resolve it into a concrete result or budget state.

A partial catalog is valid JSON and exits 0 so callers can inspect its status/counts and
retry a selected script. Exit 0 alone does **not** establish completeness. Failure to
construct even the bounded status inventory is an error with no partial JSON (exit 1).
No runtime error text is emitted as evidence about what a command supports.

## Aggregate resource limits

The catalog has a shared 120-second monotonic deadline. Every help query receives the
remaining time capped at the existing 10-second per-query limit. No new description is
started after the shared deadline; operating-system scheduling/cleanup is not a real-time
guarantee. Timeout cleanup has a separate best-effort 2-second grace for the direct child
and reader. Slow filesystem reads and serialization are not preempted. A trusted help
script that spawns descendants retaining the pipe can outlive reader cleanup; this is
not a process-tree sandbox. COMPLETE means descriptions were obtained, not a timing
certification. The maximum selection is 128 scripts. Output is bounded to 1 MiB, with 16 KiB
reserved for status bookkeeping, so a budget limit can be reported without dropping rows.
Each successful description is checked against the cumulative output budget immediately.
Per-source, per-help and single-description limits still apply. No timestamps/durations
are inserted into complete output; partial results can vary when available time differs.

JSON is ASCII-escaped UTF-8 with LF. The dispatcher writes no output files, calls no model
or network and executes no workflow. Trusted script imports/parser setup still execute
inside help subprocesses; the local unsigned inventory is not a sandbox or signature.
Argparse-free scripts are never launched. The publication checks now expose safe argparse
help, so their ROOT usage is captured without running the checks. There is no --output flag,
MCP server, new validation axis, canonical payload update or approval mechanism.
