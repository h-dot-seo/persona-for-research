# Audit consecutive declared candidate-review revisions

`audit_design_chain.py` extends the single-revision audit to a supplied linear
sequence. It can verify retained candidate-origin components introduced by earlier
declared stages without pretending that all pre-chain history was audited.

## Input and command

Create a separate local JSON file with one nonempty ordered `stages` array. Each
stage has exactly:

```json
{
  "original_corpus": {},
  "candidate_bundle": {},
  "operator_review": {},
  "target_version": "2",
  "target_build_id": "reviewed-build"
}
```

Replace empty objects with the exact artifacts used for that review. Keep raw
corpora and real review data outside the public repository. The next stage's input
must retain source segments locally and carry the exact preceding accepted runtime
annotations and identity. A projected package alone lacks raw segments and is not
a substitute for the original corpus. This tool does not create, edit or rebase
stage inputs automatically.

```sh
python audit_design_chain.py final-package.json links.json proposal.json chain.json
```

The output is JSON. Inputs are not modified. Links and the proposal must bind the
final package. A normal workflow wrapper containing `package` is accepted.

## Continuity requirements

1. Every stage independently validates source authorization, candidate bindings and
   explicit review decisions, then replays `prepare_revision()` without a provider.
2. The validated preflight package for each stage after the first must equal the
   previous replay output in canonical JSON. This is **projected-package continuity**,
   not raw-file or raw-corpus byte equality. Ignored metadata can differ without
   changing runtime evidence; each candidate bundle still binds its own exact input.
3. Skipped intermediate stages, forks, reordered stages, new runtime sources and
   untargeted annotation changes fail rather than being silently reconciled.
   Reusing an earlier author/version/build identity within the chain also fails.
4. Every stage must produce a reviewed revision. Deferred or all-rejected decisions
   do not establish a transition. Replacements require the exact prior-component hash.
5. The last output must exactly match the supplied final package.

A shorter declaration beginning at a later revision is allowed as its own bounded
chain, but inherited candidate-origin markers are explicitly unaudited. It cannot be
used to claim that omitted earlier history was verified.

## Two separate coverage results

`final_candidate_origin_coverage` describes final component markers only. Each covered
record must match an accepted target, candidate ID, candidate/review hashes and exact
component-content hash from a declared stage. Candidate IDs may repeat between
stages; they are never treated as globally unique. Final design routes show the
stage covering the selected record, without claiming use of nearby components.

`initial_unreplayed_origins` separately records candidate-origin markers already present
before the first declared stage. Its warning persists even if all those components
are later replaced. A chain can therefore cover every final marker while still
reporting `DECLARED_CHAIN_MATCH_WITH_UNREPLAYED_HISTORY`. An initial corpus with no
markers is labeled only as having no such markers, not authenticated original history.

This is a mechanical audit of the declared chain, not complete scientific provenance,
publisher authenticity, individual author ownership or genuine human-review proof.
Missing proposal falsification/uncertainty fields remain missing. No semantic
applicability, experimental quality, actual LLM performance or researcher fidelity
is established. Raw sections, candidate text and review notes are not dumped, but
IDs, locators and the research question can still be private. No external transmission
or canonical update occurs.

## Synthetic iterative workflow

```sh
python -m unittest test_design_chain -v
```

The scenario explicitly accepts mock alternative/uncertainty components, then adds
question framing or replaces uncertainty in a second review. It audits final proposal
routes using retained first-stage evidence and distinguishes repeated candidate IDs.
Tests also replace an inherited pre-chain component while retaining the unaudited
history warning, reject changed counterevidence/new sources, preserve JSON-equivalent
alias behavior, and run two actual review CLIs followed by the chain-audit CLI.

## Mixed mock and imported stages

Each stage may use a synthetic mock bundle or an offline imported response bundle.
Every stage's `candidate_provenance` binds its bundle hash, contract and recorded
origin; imported stages preserve the complete hash-bound `import_record`, including
operator-declared provider/model/run metadata. Those declarations are not authenticated
and do not prove actual model use. Stage summaries survive even if all components
from an imported stage are replaced later.

`final_candidate_origins` includes both supported recorded origins.
`final_mock_origins` and `final_imported_origins` are filtered arrays, never aliases
that mislabel imported rows as mock. Every final row includes `origin`, exact component
hash, candidate and review bindings, replay status and the covering stage index.
`final_mock_origin_coverage` remains strictly about final mock records; use
`final_candidate_origin_coverage` to assess all final candidate markers. An empty
mock array does not imply that imported history was covered.

`initial_unreplayed_origins` records both kinds with their original provenance
hashes; `initial_unreplayed_mock_origins` and `initial_unreplayed_imported_origins`
provide explicit subsets. `initial_candidate_history_status` reports generic initial
history. The old `initial_history_status` retains its existing values for mock-only
chains and uses candidate-origin wording for mixed/imported chains. Initial warnings
remain even after full replacement. Missing initial artifacts are not fabricated
from origin hashes or from a later bundle with the same candidate ID.

Generic routes expose `candidate_origin_audit`, `recorded_candidate_origin` and
`replay_stage_index`. Their `mock_origin_audit` remains mock-only. Candidate IDs may
repeat even across mock/imported stages: proofs require the exact position, origin,
content and bundle/review hashes, not the ID alone. No nearby record is implicitly
included. Mixed chains use `DECLARED_CONSECUTIVE_CANDIDATE_REVIEW_REVISIONS`; existing
mock-only scope and status values remain supported.

Execution flags and `execution_scope` describe the current deterministic audit,
not historical model use. No provider is called, no model is inferred to have run,
and no provider/model/run identity or human review is authenticated. Imported
provenance cannot turn consistency hashes into signatures or scientific validation.

Run `python -m unittest test_imported_provenance -v` for imported-only, mixed-stage,
repeated-ID, inherited/replaced-history and tamper regressions. All use synthetic
local fixtures, without actual model/source data or network calls.

## Base-observation proposal boundary

Candidate-origin coverage here applies to recorded reasoning components, not an
authenticated history of base observations. An observation-level reference with no
component origin does not establish manual authorship or absence of earlier model
assistance. [First-observation proposal packets](OBSERVATION_PROPOSALS.md) deliberately
remain noncanonical and cannot enter these audits. Canonical support would require
observation-level provenance and a separate validated append/revision replay path.
