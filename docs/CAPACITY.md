# Synthetic capacity observations

This opt-in maintainer experiment describes one workload, not a production capacity
promise or optimization. Existing product validators, CI, timeouts and replay tests
are unchanged. No real sources, model/provider calls, human judgments or cached
verification are used. All acceptance/rejection decisions are labeled fixed
synthetic fixture declarations.

Run from the repository root; OUTPUT must already exist outside it:

```sh
python -m tests.capacity OUTPUT/capacity --case 1,1,2,1 --case 2,2,3,2
```

Omitting `--case` selects 1,1,1,1. Repeat it for up to 16 distinct cases. Each case
is N,K,C,S: N papers, K observations per paper, C imported argument candidates,
S accepted argument steps. This experiment accepts integers 1–32 for N/K/C and
1 <= S <= C. These are **runner grid bounds, not new product limits**. Larger
approved grids stay opt-in, never part of default unittest discovery. The small
regressions run this guide and fix mechanical counts, not wall-time thresholds.

## Workload

`tests/scale_fixture.py` uses indexes, never random state, to construct unique
invented papers/observations and calls `research_workflow.build`. Public template
APIs create a fixed one-reference pattern, deferred applicability records, empty
links/design/relations, and S+1 answer claims, with the first claim citing the first
observation. Argument template/prepare/response_template/import_response/
review_template/export_reviewed create C candidate bridges; S are explicitly
accepted into a chain and the others rejected. The final fresh journey includes
that imported argument envelope. S is not recursive adoption-history depth.
Imported contextual answer/pattern histories, source reread, HTML, method
applications and dense evidence graphs are **not measured**. This is a representative
bounded path, not an exhaustive model of user workflows.

Each case separately observes fixture construction, journey inspect+JSON encoding,
journey text render, and package review text. Failure in fixture construction ends
that case. Later API rejections are recorded per stage; independent stages still
run. Output byte counts and SHA-256 describe actual public serializers, not an
estimated format. Semantic JSON hashes use sorted compact UTF-8. Current journey
JSON insertion order can vary with PYTHONHASHSEED; canonical content, lengths and
counts are compared across seeds, not its raw JSON hash. Within one process,
observed and unobserved raw output bytes must remain identical. Text byte equality
is checked separately. No product output is reordered to manufacture determinism.

## Counts and bounds

Primary counters: actual `build`, `validated_source_rules`, `apply` invocations.
Secondary: actual `payload_sha256` invocations and total canonical JSON bytes
serialized by those hashes. Loaded root-module aliases are patched by original
function identity, with one shared wrapper rather than stacked aliases. Nested
validation/build/hash calls are distinct real invocations and are counted separately;
these counters must not be summed as independent workload units. Late-loaded aliases
may be missed; current fixture modules are imported before measurement. Wrappers
are restored even on exceptions. Observation adds one canonical serialization per
hash call, so observed wall seconds include overhead and are not uninstrumented
speed measurements. Receipt encoding and summary hashing are outside the counters.

The report records the sum of hypothetical supplied input-file bytes and whether
that calculation exceeds 8 MiB, separately from actual API rejection. It does not
pretend to have executed the product CLI or impose the calculated bound on APIs.
Actual APIs continue enforcing their own serialized-input, handoff (2 MiB),
output (16 MiB), candidate and reference limits. A grid that hits none proves no
capacity ceiling. `_ARGUMENT_RENDER_MAX_NODES=8192` is an optimization work budget,
not an input acceptance limit. Output/input ratios use the supplied-file byte sum
as a clearly labeled denominator, including for package review which consumes only
the package. Compare like workloads, not this ratio across different tools.

## Saved results and failures

A new external directory is required, with an existing plain parent and no symlink
or reparse ancestors. No overwrite or automatic cleanup. Each finished case is
saved exclusively as `case-NNN.json`, bounded to 16 MiB. Receipts contain dimensions,
stage results/counters/seconds and bounded API rejection text from synthetic inputs,
not source contents or local paths. Every case is attempted. `READY.json` is written
last only if all stages succeeded; otherwise `FAILED.json` lists the saved results
and CLI exit is 1. The marker records each case file's raw hash. Unexpected workload exceptions are recorded as failed stages with diagnostics
withheld. Process interruption or I/O failure can leave earlier cases or a partial
current file/marker; an interrupted in-progress stage has no completed receipt. Marker presence alone is not
success: require exit 0, strict JSON and matching recorded case hashes. Keep partial
results for diagnosis and use a new directory on retry. No saved-result verifier
is added. No general speed guarantee or approval follows from a successful run.

## Call-local answer template construction

For eligible plain JSON, `answer_draft.inspect` retains its fresh source/package
validation and constructs expected template fields from that checked value in the
same call. Eligibility is recorded before the first source validation and checked
again afterwards, so a custom value that normalizes itself during validation
still takes the original path. Public `template` still performs fresh validation. No cached package,
receipt, global memoization or caller-supplied verified result is accepted. Reviewed
answer envelope dispatch is unchanged. The guard permits only exact built-in JSON
types, finite floats and surrogate-free text, with no container aliases/cycles,
depth below 64, at most 8192 nodes (keys included), and 65536 total text code points.
These are optimization-work bounds only: ineligible values use the original
validation path, never a new rejection. Replaced source/template functions also
retain the original call path. This is not a concurrent-mutation lock.

For the fixed (8,4,4,2) workload, journey text build replays fall from 79 to 56
with complete text bytes unchanged. This is a deterministic replay-count result,
not a general speed promise. Prior capacity receipts remain historical records;
current small-case count gates reflect the new implementation.
