# Private spreadsheet exports

`tabular_export.py reference-catalog PACKAGE.json` rechecks the bound package with
`_sources`/`validated_source_rules` and recomputes every `_endpoint`. A saved catalog
or report is not an accepted input. The current table covers all supplied observations
and components, not a question, topic filter, relevance ranking or recommendation.
It does not reread source files, resolve identity or rights, approve use, execute a model,
change the payload/four validation axes, or transmit anything. Keep the output private:
quotes, locators and imported component-origin labels may disclose private information.

Use a pre-existing directory outside the repository in place of `OUTPUT`:

```sh
python tabular_export.py reference-catalog examples/trajectory-conditions-package.json --output OUTPUT/references.csv
python tabular_export.py reference-catalog examples/trajectory-conditions-package.json --format tsv --excel-bom --output OUTPUT/references.tsv
python tabular_export.py reference-catalog --describe --output OUTPUT/reference-columns.json
```

Without `--output`, the result is UTF-8 bytes on stdout. `--output` writes exactly
those bytes to a new file and prints the existing saved-output receipt, with a raw
byte hash (CSV/TSV has no JSON payload hash). Existing files, symlink components,
repository destinations and missing parents are rejected. A failed write may leave
partial output; it is never removed. Preflight precedes input reading. Invalid input,
a cell over the limit or a result over the limit emits no partial result.

## Fixed columns and rows

`--describe` takes no package or formatting options and emits the exact ordered
columns, display markers, limits, omitted fields and boundary as JSON.
`reference-catalog`, `review-agenda` and `evidence-routes` are separate tables.
Evidence routes expose four optional column sets, described below. Human-validation
items are not exported. No CSV import or write-back exists.

Rows follow supplied paper order, observation order, then the observation itself
followed by that observation's supplied component order. An observation reference has
`dimension: null`; a component reference has its exact dimension. Papers without
observations get a `PAPER_WITHOUT_OBSERVATIONS` row, not an invented reference.

Columns in order:

- `row_kind`, `paper_id`, `observation_index`, `dimension`, `reference_json`.
- `source_kind`, `publication_year`, `source_sha256`, `source_locator`, `recorded_source_check`.
- `observation_topic`, `observation_method`, `observation_condition`,
  `observation_limitation`, `observation_locator`, `observation_stance`,
  `observation_claim_type`, `observation_evidence_quote`, `observation_quote_check`.
- `component_claim_type`, `component_text`, `component_locator`,
  `component_evidence_quote`, `component_origin`, `component_proposed_claim_type`,
  `component_quote_check`.
- `has_observation_origin`, `missing_reasoning_dimensions`, `attribution`,
  `persona_sha256`, `knowledge_papers_sha256`, `boundary`.

Observation labels never become component labels or vice versa. Components repeat
observation context rather than replace it. `reference_json` uses the existing review
format (`json.dumps(ensure_ascii=True, sort_keys=True)`), so the parsed JSON cell is the
exact reference for that package. Spreadsheet CSV quoting is not JSON quoting: copy the
parsed cell, not a slice of the raw CSV file. The two hashes bind position-based references
to their package, not to stable cross-build identities. Every data row carries both
hashes and the full boundary. A hypothetical empty table has a header only; consult
this guide or `--describe` for its boundary.

Omissions: persona metadata/rules/validation-axis declarations, package wrapper metadata,
paper title/source_file/split and other paper metadata outside the columns, full
observation-origin contents (only presence is shown), and component review fields beyond
origin/proposed_claim_type. This is a fixed reference table, not a lossless package backup.
No field omitted here is implied absent or approved. Use authoritative JSON for details.

## Cell and byte contract

Null is `NOT_SUPPLIED (null)`, an inapplicable column is `NOT_APPLICABLE`, and an empty
string is `EMPTY_STRING`. Lists use compact JSON, including `[]`; booleans are `true` or
`false`. These display markers can collide with literal strings and are not a reversible
encoding. For rows without observations all observation/component/reference columns are
inapplicable. Missing optional component values are null markers, not inferred values.

Each cell passes the existing `review_package.display` control/directional escaping
first. Then a cell beginning with `=`, `+`, `-` or `@` receives one leading apostrophe.
TAB/CR have already become literal `\u0009`/`\u000d`. The apostrophe intentionally
changes displayed cell text; original JSON remains authoritative. This is a conservative
text export, not a guarantee about every spreadsheet application's import/typing options.
CSV commas/quotes use standard-library quoting; TSV uses tabs. Record terminators are
explicit LF on every platform. Korean and other ordinary Unicode remain UTF-8.
`--excel-bom` explicitly adds UTF-8 BOM bytes and therefore changes the raw byte hash;
it is off by default. It does not attest a particular Excel installation's behavior.

Input is bounded to 8 MiB before parsing. Output including any BOM is bounded to 16 MiB.
Every rendered cell (after escaping and apostrophe) is at most 32,767 Unicode code points;
this is not a UTF-16 code-unit guarantee for every spreadsheet. Oversized cells/results
fail rather than truncate. Narrow supplied artifacts explicitly and regenerate a valid
package; do not edit package bindings to evade checks. Counts, pivots and averages are
not confidence scores, semantic validity or human approval. Recorded source/quote checks
are historical declarations, not renewed checks. No decisions are read back from sheets.

## Fresh journey review agenda

`tabular_export.py review-agenda CARD --input-root INPUTS` accepts an existing explicit
`persona.journey-input-card.v1`, not a selection template or saved JSON/HTML report.
Prepare the card with [journey_inputs.py](JOURNEY_INPUTS.md) after reviewing the selected
files; this command does not discover files, refresh hashes or choose a pattern.
Substitute the preserved card file for `CARD`, its explicit artifact directory for
`INPUTS`, and a pre-existing external output directory for `OUTPUT`:

```sh
python tabular_export.py review-agenda CARD --input-root INPUTS --output OUTPUT/agenda.csv
python tabular_export.py review-agenda --describe --output OUTPUT/agenda-columns.json
```

The command reruns `journey_inputs.inspect` over the exact byte/hash-pinned current
artifacts before rendering. Stale/edited files, incomplete selection cards, symlinks,
reparse paths and unsupported roots fail through the existing card contract. Card files
are limited to **128 KiB**, a tighter limit than reference packages, and the selected
JSON artifacts share an **8 MiB combined budget**. The existing fresh journey report
and this CSV/TSV result each have their own 16 MiB output cap, not a combined budget.
Cell safety, LF, optional BOM and exclusive output semantics are the same as above.

The fixed ordered columns are `domain`, `code`, `target_json`,
`journey_input_sha256`, `status`, `input_card_sha256`, `source_reread`, `boundary`.
There is one row per freshly generated `review_agenda` entry, in original order.
`target_json` is compact sorted ASCII JSON containing **every remaining key** of that
entry, excluding only domain/code. This retains heterogeneous target fields without
assuming a fixed target schema. The two hashes distinguish logical journey inputs and
the preserved file-binding card; neither authenticates a person, source or permission.
The current journey status is copied literally, never promoted to research approval.
`HUMAN_REVIEW_REQUIRED_NOT_RESEARCH_APPROVAL` is a review requirement, not readiness.

No rows yields **header only**, not a fabricated success row or proof that the review
is complete. Consult this guide or `--describe` for boundaries on an empty table.
The agenda is not exhaustive; sorting or counting prompts in a spreadsheet cannot
establish validity, approval, source quality or a score. Nested reports, evidence routes,
question/topic/year and detailed artifact verification records are omitted; use the
fresh full journey report for them. No sheet edits are imported.

Optional `--source-root DIR` is accepted **only together with** a source-selection form
already explicitly pinned in the card. Such a selected form also requires the explicit
source root. The command inherits the existing current source reread, without discovery
or standing authorization; its `source_reread` column is `true` and the row boundary
includes the fresh report's corresponding reread explanation. Without that pair the
column is `false` and source bytes are not reread. Method-application and declared-review
options are taken only from their pinned card slots, not inferred. Neither option grants
approval, model execution or semantic validation. The row boundary combines the export,
fresh journey and input-file-card limitations. Paths/source quotes/identifiers or other
private target fields may be present; exporting does not grant permission to share.

## Fresh journey evidence routes

Use the same explicitly preserved CARD and INPUTS as the agenda. This route never
accepts cached journey reports or selects artifacts. Tokenize these commands with
shlex before substituting native paths, so Windows backslashes/spaces survive.

```sh
python tabular_export.py evidence-routes CARD --input-root INPUTS --output OUTPUT/routes.csv
python tabular_export.py evidence-routes --describe --output OUTPUT/route-columns.json
```

Each row is one freshly inspected `evidence_routes` item in the journey's order.
That union is not the complete corpus or literature. Empty routes yield only the
selected header, never an approval row. All card/combined-artifact/report, cell,
BOM, formula-guard and exclusive-output limits above apply unchanged.

The base ordered columns are: row_kind, paper_id, observation_index, dimension,
reference_json, reference_sha256, evidence_json, source_kind, publication_year,
source_sha256, source_locator, recorded_source_check; observation_topic,
observation_method, observation_condition, observation_limitation,
observation_locator, observation_stance, observation_claim_type,
observation_evidence_quote, observation_quote_check; component_claim_type,
component_text, component_locator, component_evidence_quote, component_origin,
component_proposed_claim_type, component_quote_check; has_observation_origin,
attribution, publication_scope, in_topic_timeline, actively_used_in_answer_or_design,
pattern_roles_json. Then each of pattern_evidence_uses, context_uses,
publication_relationship_basis_uses, answer_uses, design_uses, unused_link_uses,
direct_argument_uses contributes its `_count` followed by `_json` column.

Four fixed contracts are exposed in full by `--describe` without reading inputs:

- Neither optional pinned artifact: base columns, then trailer.
- Pinned method_applications only: base, method_application_uses_count,
  method_application_uses_json, then trailer.
- Pinned source_selection only: base, current_source_recheck_json, then trailer.
- Both: base, method_application_uses_count, method_application_uses_json,
  current_source_recheck_json, then trailer.

The trailer is journey_input_sha256, input_card_sha256, status, source_reread,
boundary. Options mean non-null pinned card slots, never the presence of a first
row or a nonempty use list. A selected source form requires --source-root and vice
versa. This explicit pair causes fresh selected source rereads, not discovery or
standing permission. Recorded source and quote labels remain separate from the
current_source_recheck_json; a current check does not replace historical labels.

Observation and component scalar labels do not stand in for each other. Missing
component fields use NOT_APPLICABLE, except a missing recorded quote-check label
on an existing component uses NOT_PERFORMED, matching the existing catalog. An
absent component has NOT_APPLICABLE for its quote check; exact evidence_json still
preserves the original absence of the label. Explicit null uses NOT_SUPPLIED (null), false
uses false, and empty strings use EMPTY_STRING. Literal marker strings may collide,
so `evidence_json` retains the exact full node, including field presence and nested
observation origins; reference_json, pattern_roles_json and every use JSON are
compact sorted ASCII JSON. JSON escaping precedes display escaping: JSON controls
and directional Unicode round-trip through json.loads after CSV/TSV parsing.
These nested JSON cells preserve absent keys versus null/false/empty values. They
remain authoritative over display markers and formula-prefixed scalar cells.
Oversized evidence/use cells fail without truncation or partial stdout.

Use lists preserve distinct context, publication-relationship basis, answer,
design, unused-link and direct-argument roles. Method-application intent is not
active answer/design use or execution. Declared reject/defer decisions and direct
citation roles are copied, not promoted to retain or support. No premise citation
transfer, ranking, decision inference, spreadsheet import or new approval axis.
Counts are only list lengths, not scores. Full nested journey reports, complete
corpus metadata, question/topic/reference year and detailed artifact checks are
omitted; consult the fresh full report. Exact evidence and use cells can contain
private quotes, file labels and operator/provenance IDs. Row boundary combines
export, fresh journey and input-card limitations; export is not sharing consent.
