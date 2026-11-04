# Audit one candidate-review revision behind a design scenario

`audit_design_lineage.py` checks whether declared candidate and review inputs
reproduce the exact package used by a design scenario. Displaying plausible
provenance hashes alone is not this check. The scope is **one declared revision**,
not complete history, source authentication or genuine human review.

## Inputs and command

Retain the final package, original reasoning-link artifact, original proposal and
a separate local revision-input file with exactly:

```json
{
  "original_corpus": {},
  "candidate_bundle": {},
  "operator_review": {}
}
```

Replace the empty objects with the exact artifacts used by `extraction_adapter.py`
and `operator_review.py`. The original corpus may contain restricted source text;
keep this file outside the public repository and do not upload it without permission.
These are supplied replay inputs, not an authenticated receipt.

```sh
python audit_design_lineage.py package.json links.json proposal.json revision-inputs.json
```

The command emits JSON only. It validates the package, links and proposal, validates
the candidate bundle against the original corpus, and runs `prepare_revision()`
again using the final package's version/build. No provider is called. A deferred
or all-rejected review cannot establish a revision. Canonical JSON of the resulting
package must exactly match the supplied final package, including its identity and
recorded provenance. Changed bindings or a different replayed package fail without
partial output. Hashes remain consistency checks, not signatures.

## What the audit reports

- Hashes of the original corpus, candidate bundle, operator review, replayed package,
  original link artifact and proposal. Keep those artifacts to inspect their content.
- Every final candidate-origin component, including unused papers/dimensions, with its
  candidate ID, proposed and reviewed claim types, and review/bundle hashes.
- `REPLAYED_CURRENT_REVISION` only for components at the exact accepted targets
  covered by this replay. Inherited components are `INHERITED_ORIGIN_NOT_REPLAYED`.
  Their presence yields `CURRENT_REVISION_MATCH_WITH_INHERITED_ORIGINS` rather than
  silently implying coverage. Even `CURRENT_REVISION_REPLAY_MATCH` is not a claim
  that all prior history has been audited.
- Per-step proposal field availability, explicit link-use roles and source relations.
  Selected endpoint records retain paper/index/dimension references, source kind,
  publication year, source and record locators, observation stance, source hash,
  method/condition/limitation hashes and original claim types.
- A selected component's candidate-origin audit status. Nearby question framing,
  falsification or uncertainty components are not inferred to have been used.
  A missing proposal falsification field stays `NOT_SUPPLIED` even when cited source
  evidence contains a criterion. Field presence does not validate scientific design.
- Unreferenced link IDs remain visible, without declaring those links relevant,
  irrelevant or exhaustive. The bound design artifact retains their full evidence.

Raw source sections, candidate text and review notes are not dumped into the audit.
It still contains the research question, IDs and locators, which can be private.
This is not anonymization or permission to publish. Source quote matching is replayed
against supplied segments, not independently retrieved publications. Actual source
file bytes, authorship, semantic support, applicability and experimental quality are
not verified. No model inference, experiment execution or canonical change occurs.

## Synthetic end-to-end check

```sh
python -m unittest test_design_lineage -v
```

This runs actual mock extraction → explicit operator review → reviewed package →
linked design scenario → lineage audit CLIs. A proposed explicit-statement label
is changed to an operator interpretation during the simulated review, and both
labels remain auditable. Additional tests cover inherited unused origins, stale
inputs, exact replay mismatches despite recomputed hashes, deferred/rejected reviews,
no provider/source reads, JSON-equivalent inputs and exclusion of raw source text.
No real researcher, actual LLM extraction or authenticated human review is tested.

## Offline imported candidates and mixed origins

Both synthetic mock bundles (contract version 1) and offline imported response
bundles (contract version 2) are replayed deterministically. The imported path
reconstructs and checks the handoff/response bindings through the same candidate
validator used by operator review. It does not call a provider or run a model.

`candidate_origin_components` covers both recorded origin types.
`mock_origin_components` contains only `operator_reviewed_mock_candidate` rows;
`imported_origin_components` contains only `operator_reviewed_imported_candidate`
rows. Every row includes its exact `origin`, component-content hash, candidate ID,
bundle/review hashes, proposed/reviewed claim types and replay status. Inherited
records retain their original hash-bound provenance and remain explicitly unreplayed.

`initial_unreplayed_origins` separately inventories every candidate-origin component
in the input package, with `retained_exactly_in_final` and `initial_history_status`.
This warning survives even when all initial imported or mock components are replaced.
The legacy `status` and `inherited_origin_count` describe final components only: a
`CURRENT_REVISION_REPLAY_MATCH` with count zero does not erase initial history.
Inspect both results rather than treating current revision coverage as full lineage.

`candidate_provenance` binds the supplied bundle and its contract/origin. Imported
bundles additionally include the complete `import_record`: handoff and response
hashes plus operator-declared provider, model, run, operator and execution location.
These are **recorded, not authenticated**. An inherited component's bundle hash is
not enough to reconstruct its missing import record; retain its original artifacts
and supply earlier stages to the chain audit when available.

Routes use `candidate_origin_audit` and `recorded_candidate_origin` for generic
coverage. The legacy `mock_origin_audit` is strictly mock-only: an imported selected
record has `NO_MOCK_ORIGIN_ON_SELECTED_RECORD`, even when its generic replay succeeds.
Existing mock-only audit scope/status values remain available. Imported or mixed
history uses `ONE_DECLARED_CANDIDATE_REVIEW_REVISION` for `audit_scope`.

`llm_used=false`, `provider_invoked=false` and `execution_scope` describe the current
deterministic audit only. They neither establish nor deny prior actual model use.
No provider/model/run identity, execution location or human reviewer is authenticated.
A successful replay proves consistency of supplied artifacts, not their truth.
Run `python -m unittest test_imported_provenance -v` for synthetic imported and
mixed-stage regression coverage. No actual model/source data or network is used.

## Base-observation proposal boundary

Candidate-origin coverage here applies to recorded reasoning components, not an
authenticated history of base observations. An observation-level reference with no
component origin does not establish manual authorship or absence of earlier model
assistance. [First-observation proposal packets](OBSERVATION_PROPOSALS.md) deliberately
remain noncanonical and cannot enter these audits. Canonical support would require
observation-level provenance and a separate validated append/revision replay path.
