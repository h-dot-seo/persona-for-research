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
columns, display markers, limits, omitted fields and boundary as JSON. Only
`reference-catalog` is supported in this release. Agenda/routes and human-validation
items are not silently folded into this table. No CSV import or write-back exists.

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
