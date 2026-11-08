# Reassess a manually structured observation

A local quote can match exactly while the method or counterargument you wrote is
unsupported. The manual append command intentionally cannot edit old observations.
`revise_local.py` adds an explicit correction path for a **manual** observation,
without changing its source bytes or silently migrating downstream artifacts.

## Synthetic reassessment after the manual journey

First run the [manual observation journey](MANUAL_LOCAL_OBSERVATIONS.md), producing
`manual-complete.json`. Then use this prewritten **synthetic operator** revision:

```sh
python revise_local.py apply ../manual-complete.json examples/manual-revision-card.json ../manual-reassessed --source-root examples/synthetic-sources
python corpus_files.py ../manual-reassessed/manifest.json --source-root examples/synthetic-sources --question "Which synthetic explanation?" --topic "model design" > ../manual-reassessed-result.json
python review_workspace.py ../manual-reassessed-result.json ../reassessed-review --question "Which synthetic explanation?" --operator-id synthetic-operator --reference-year 2020
```

Both output directories must be new and outside this repository. The fixture
reclassifies the first research observation from explicit_statement to
operator_interpretation and adds explicit uncertainty. It does **not** claim the
new classification is scientifically correct. The supplied short sentence does
not establish an individual researcher's complete reasoning or methods.

Read `revision-audit.json` side by side with `manifest.json`. The audit preserves
old/new observation text, claim labels, quotes, reasoning components, declared
operator and reason, old/new manifest and observation hashes, unchanged source
hash and old/new version/build identity. Old material may be wrong: it is retained
as the superseded record, not endorsed or verified again. The source quote and
byte checks apply to the **new complete corpus** only. An old invalid quote can
therefore be explicitly corrected against the same pinned bytes.

## Prepare a specific correction yourself

```sh
python revise_local.py template ../manual-complete.json --paper synthetic-0 --observation-index 0 > ../my-revision-card.json
```

The template copies the selected old observation for editing. It is not a proposed
correction. Edit the `observation` yourself and fill `operator_id`,
`revision_reason`, `new_version` and `new_build_id`. Both version and build ID must
change; this is not automatic version assignment or a globally unique release ID.
No-op revisions and untouched templates reject. Leave schema, manifest binding,
old observation binding, paper ID and index unchanged.

The card can change method, condition, limitation, topic, locator, exact quote,
claim type, stance and supported reasoning components under the existing manual
schema. The observation index and all other observations stay in place. It cannot
change source files/hashes, paper identity, publication kind/year or authorization.
A source change requires a new prepared selection and explicit new curation.

Apply with the same manifest and chosen new directory. The command validates full
corpus authorization/holdout boundaries before source reads, rejects stale cards,
checks all new/current observations against pinned local bytes, then writes:

- `manifest.json`: new ordinary manifest for the existing loader.
- `revision-audit.json`: unsigned local before/after review aid, not a canonical
  decision or authenticated human review log.
- `READY.json`: written last, meaning files were written, not evidence approved.

The selected old observation must satisfy the manual-card field contract, including
explicit stance. Records carrying generated verification fields or mock-review
provenance are rejected rather than silently stripping that provenance. Use the
original manual input manifest; this tool is not a replacement for candidate review.
An existing source manifest remains untouched. The target preparation-only inventory
annotation is removed if present; unrelated input fields are otherwise retained.
All output may contain quotes and private annotations. This is not sanitization,
rights clearance or permission to publish old/new excerpts.

## Rebuild, do not rewrite old bindings

The new version/build and changed observations produce a different bound package.
Old answer drafts, links, design plans and reviews must not be reused by just
changing their hashes. Build the revised package, create a new review workspace,
and manually reconsider your answer, counterarguments and design. Nothing
transfers claims, generates new citations, approves the revision or deletes prior
artifacts. Preserve the previous package and audit if you need to compare them.
The audit is one revision only, not an authenticated complete lineage history.

Existing output directories, symlink output path components and repository-local
outputs reject. Files use exclusive creation. An I/O failure may leave a partial
folder without READY; preserve it and choose a new directory. Keep both sources and
destination stable: this is not a crash-atomic write or hostile-filesystem defense.
No real corpus, model, API, network, scientific execution or actual reviewer is
used in the synthetic demonstration.

```sh
python -m unittest tests.test_revise_local -v
```

Before migrating existing answer/design work, use the read-only
[revision impact report](REVISION_IMPACT.md) to trace old citation and link uses to
changed or missing same-position evidence. It does not automatically rebind them.

Imported base observations are intentionally rejected by the manual revision gate.
Do not remove their origin to make a manual card. The separate
[reviewed observation append](OBSERVATION_REVISION.md) route creates a new candidate
and retains imported provenance; imported-observation replacement/source migration
is not supported by this release.
