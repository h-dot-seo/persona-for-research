# Audit consecutive declared mock-review revisions

`audit_design_chain.py` extends the single-revision audit to a supplied linear
sequence. It can verify retained mock-origin components introduced by earlier
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
chain, but inherited mock-origin markers are explicitly unaudited. It cannot be
used to claim that omitted earlier history was verified.

## Two separate coverage results

`final_mock_origin_coverage` describes final component markers only. Each covered
record must match an accepted target, candidate ID, candidate/review hashes and exact
component-content hash from a declared stage. Candidate IDs may repeat between
stages; they are never treated as globally unique. Final design routes show the
stage covering the selected record, without claiming use of nearby components.

`initial_unreplayed_origins` separately records mock-origin markers already present
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

## Offline imported candidates are outside this audit's scope

This legacy audit supports synthetic-mock candidate revisions only. It fails
closed for imported candidate bundles and for any
`operator_reviewed_imported_candidate` component in the final package or any
declared stage's input package. This includes imported history inherited before
the declared chain and imported records later replaced by mock candidates. No
mock-only coverage result is emitted for mixed or imported history.

The normal explicit operator-review workflow and evidence-scope disclosure support
imported candidates independently of this limitation. Evidence-scope disclosure
keeps `recorded_mock_origin_references` restricted to mock records, reports
`recorded_imported_origin_references` separately, and includes both in
`recorded_candidate_origin_references`. Those are recorded declarations, not proof
of actual model invocation or authenticated human review. Execution flags such as
`llm_used=false` describe the current deterministic command only.
