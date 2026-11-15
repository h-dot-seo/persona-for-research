# Descriptive artifact contract index

The public interface includes JSON files, not only CLI flags. This index connects
identifiers and selected workflows without becoming another validator. It is **not
JSON Schema** and accepts no private artifact input. Existing Python consumers and
the bound handoff's `response_contract` remain authoritative. No schema field,
conversion, new support-period promise or retirement policy is introduced.

```sh
python artifact_schemas.py --format json
python artifact_schemas.py --workflow answer --format text
python artifact_schemas.py --workflow observations --format json
```

The tool reads only the fixed published `docs/artifact-schema-index.json` and emits
at most 16 MiB to stdout. `--workflow` accepts an exact indexed workflow, never a
file path. It does not import/run producer implementations, inspect user artifacts,
call a model/network service or write a file. A matching index row is not proof of
binding freshness, authenticity, permission, semantic validity or approval.

## Evidence and coverage

Each record has workflow/role/variant, nullable schema_id, category, mode,
selection_flags, producer, consumer, guide, source_mentions, response_contract and
note. selection_flags are mode-selection references, not executable command recipes
for every workflow stage; consult the relevant command help and guide for arguments. Workflow/role/variant is the row key: schema_id alone cannot describe untagged
response, provenance and review forms. Never insert a catalog label into such forms.

`source_mentions` records identifier occurrence, including dynamic SCHEMAS tables.
It is **not production or consumption attribution**. A null producer/consumer means
unknown in this index, not that no producer/consumer exists. Many report identifiers
are inventoried but have deliberately unestablished relationships. `SOURCE_REVIEWED`
links describe inspected code; `SYNTHETIC_EXERCISED` links have a named synthetic
production regression. Neither means every operation, input or scientific outcome
has been validated. A function's existence alone is not a producer proof.

The completeness test unions root Python literal identifiers with the actual
answer_proposals.SCHEMAS and argument_proposals.SCHEMAS tables. The current index
also includes the explicit tests/timing.py and tests/capacity.py output identifiers
as **maintainer** artifacts. Two synthetic legacy wrapper identifiers are
**fixture-only**, not public contracts. Negative-test-only identifiers are excluded.
This discovery rule is explicit and bounded; arbitrary schema-looking strings in
all files are not treated as supported contracts. New source identifiers or changed
mention locations fail the drift test until the index is reviewed.

Ten actual handoff production scenarios are exercised: reasoning, observations,
answer v1/v2/v3, argument v1/v2, pattern v1/v2 and application v1. Their real CLI
response-template outputs have exactly handoff_sha256 and candidates and no schema
field. Candidate details belong to each generated response_contract, not a copied
nested specification here. A filled review-attribution answer v3 fixture is also
prepared, imported and replay-validated using its existing consumer. These limited
checks are not a claim that all indexed artifacts have end-to-end tests here.

## Parallel modes, not retirement

Answer v1 is default; citation explanations select v2 and supplied research context
together with explicit citation-explanations mode selects v3. Supplying research
context without `--include-citation-explanations` is rejected. Argument recorded-answer-context mode and pattern evidence-reasons mode
are opt-in variants. Existing versions continue to be explicitly produced and
replayed by their current consumers. A label alone never makes arbitrary JSON
acceptable, and no silent up/down conversion is implied. This describes current
code and regression evidence, not a new future compatibility guarantee.

Reasoning/observation handoffs have no schema identifier: contract_version=1 is a
request/handoff marker. Extraction bundles use contract_version for a different
purpose: imported provenance-bearing versus mock-generated structure. Do not infer
schema generations from that field or rename it. Adoption decisions and provenance
remain operator-authored declarations; no decision, rater identity or provider/run
provenance is inferred by the index. Empty templates are not completed assessments.

## Relation to editor and completed-structure schemas

An editor-oriented document permitting empty template placeholders and a
completed-structure preflight describe different acceptance sets. This descriptive
index implements neither; it now links the separate [manual-card preflight](SCHEMA_CATALOG.md).
That limited checker does not guarantee import acceptance and leaves existing
Python consumers authoritative. Open corpus forms and the seven editor profiles
remain unchanged; no editor configuration or hidden integration is installed.

The completed-structure workflow has two untagged output rows: the list catalog
(produced by schema_catalog.main in its list branch) and the check report (produced
by schema_catalog.check). Their producer relationships are SOURCE_REVIEWED; no
downstream report consumer is asserted. The show command returns a fixed JSON
Schema document. The two completed-structure URNs identify those documents, not
instance schema IDs, and are not added to the identifier inventory below. An
instance must never gain a catalog label or $schema field. The check report
performs neither binding validation nor source reading, and is not an approval.
The index remains descriptive rather than adopting the checker as its validator.

## Identifier inventory

The following set is checked against the machine index. Workflow rows and evidence
status remain in the JSON/text output rather than duplicating a large second table.

- `human-validation-record.v1`
- `persona.answer-context-preview.v1`
- `persona.answer-handoff.v1`
- `persona.answer-handoff.v2`
- `persona.answer-handoff.v3`
- `persona.answer-proposal-review.v1`
- `persona.answer-proposal-review.v2`
- `persona.answer-proposal-review.v3`
- `persona.answer-proposal-scope.v1`
- `persona.answer-proposal-scope.v2`
- `persona.answer-proposal-scope.v3`
- `persona.answer-proposals.v1`
- `persona.answer-proposals.v2`
- `persona.answer-proposals.v3`
- `persona.answer-research-context.v1`
- `persona.application-handoff.v1`
- `persona.application-proposal-review.v1`
- `persona.application-proposals.v1`
- `persona.argument-handoff.v1`
- `persona.argument-handoff.v2`
- `persona.argument-proposal-review.v1`
- `persona.argument-proposal-review.v2`
- `persona.argument-proposal-scope.v1`
- `persona.argument-proposal-scope.v2`
- `persona.argument-proposals.v1`
- `persona.argument-proposals.v2`
- `persona.argument-step-view.v1`
- `persona.artifact-schema-index.v1`
- `persona.bibliographic-census.v1`
- `persona.candidate-challenge.v1`
- `persona.capacity-observation.v1`
- `persona.capacity-run.v1`
- `persona.citation-reasoning-audit.v1`
- `persona.command-catalog.v1`
- `persona.command-description.v1`
- `persona.command-list.v1`
- `persona.external-evidence-review.v1`
- `persona.external-evidence.v1`
- `persona.folder-inventory-verification.v1`
- `persona.folder-inventory.v1`
- `persona.journey-comparison.v1`
- `persona.journey-file-selection.v1`
- `persona.journey-input-card.v1`
- `persona.journey-input-file-check.v1`
- `persona.manifest-regeneration.v1`
- `persona.manual-observation-revision.v1`
- `persona.manual-observation.v1`
- `persona.method-application-review.v1`
- `persona.method-application.v1`
- `persona.observation-append-candidate.v1`
- `persona.observation-append-card.v1`
- `persona.observation-origin.v1`
- `persona.observation-proposal-review-packet.v1`
- `persona.observation-proposals.v1`
- `persona.package-overview.v1`
- `persona.pattern-handoff.v1`
- `persona.pattern-handoff.v2`
- `persona.pattern-proposal-review.v1`
- `persona.pattern-proposals.v1`
- `persona.pattern-proposals.v2`
- `persona.release-decision-record.v1`
- `persona.reopening-record.v1`
- `persona.research-journey.v1`
- `persona.response-extraction.v1`
- `persona.reviewed-answer-proposals.v1`
- `persona.reviewed-answer-proposals.v2`
- `persona.reviewed-answer-proposals.v3`
- `persona.reviewed-application-proposals.v1`
- `persona.reviewed-argument-proposals.v1`
- `persona.reviewed-argument-proposals.v2`
- `persona.reviewed-pattern-proposals.v1`
- `persona.rule-correspondence.v1`
- `persona.rule-inventory.v1`
- `persona.saved-output.v1`
- `persona.selection-census-map.v1`
- `persona.source-recheck-selection.v1`
- `persona.source-recheck.v1`
- `persona.source-structure-report.v1`
- `persona.split-check.v1`
- `persona.split-declaration.v1`
- `persona.synthetic-legacy-replay-fixture.v1`
- `persona.synthetic-reasoned-legacy-replay.v1`
- `persona.tabular-description.v1`
- `persona.test-timing.v1`
- `synthetic-answer-holdout-labels.v1`
- `synthetic-answer-submission.v1`

## Optional editor documentation

Three separate optional authoring profiles now cover source selection, declared provenance and detached human records. See [EDITOR_SCHEMAS.md](EDITOR_SCHEMAS.md). They permit placeholders and are not the completed-input checker discussed above; no index row or existing validator is replaced.

Comparator structural inventory: `persona.comparator-corpus.v1` is operator-authored input; `persona.comparator-overlap.v1` is a detached report. See [guide](COMPARATOR_OVERLAP.md); no specificity or independence assessment is produced.

Optional comparator-only source mapping `persona.comparator-source-selection.v1` and report `persona.comparator-source-recheck.v1`: [source guide](COMPARATOR_SOURCES.md).

Detached bibliography identifiers (see [contract](PAPER_IDENTITY.md)):

- `persona.paper-identity-mapping.v1`
- `persona.paper-identity-declaration.v1`
- `persona.paper-identity-check.v1`
- `persona.paper-identity-replay.v1`
