# Private reference-catalog spreadsheet export

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
`reference-catalog` and the separate `review-agenda` table below are supported.
Evidence routes and human-validation items are not folded into either table. No CSV import or write-back exists.

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
