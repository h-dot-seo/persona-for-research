# Record human validation as a detached, package-bound document

[The architecture](ARCHITECTURE.md) lists four validation axes. Evidence integrity,
predictive evaluation and runtime validation already have tooling; `human_validation.py`
adds the fourth: a **documented expert/rater assessment** of the rules in one exact
package. Like the predictive axis (`examples/synthetic-holdout-labels.json` with
`evaluate_synthetic.py`), the record is a separate file bound to the package by its two
logical payload hashes. It is never written into the persona payload: the knowledge map
binds to the whole persona payload hash, so any payload edit would break every existing
knowledge binding, and only a new persona version built and re-bound through the normal
lifecycle may carry a changed `validation.human_validation` status. The commands here
never rebind knowledge and never modify a package file.

A recorded assessment is a documented assertion by named rater labels about listed items.
It is not generalization to other topics, not proof of fidelity to the real researcher,
not a score, and rater label distinctness is not verified independence. No model call,
no network, no canonical update.

## Record fields

Exactly these fields, declared as `human-validation-record.v1`:

| Field | Meaning |
|---|---|
| `schema_version` | `human-validation-record.v1` |
| `author_id`, `version`, `build_id` | Copied from the package identity; at most 128 characters each |
| `persona_payload_sha256` | Logical JSON payload hash of the persona (the `persona.py` convention) |
| `knowledge_papers_sha256` | Logical payload hash of the knowledge `papers` array |
| `raters` | 1 to 32 `{rater_id, role}` entries, each string at most 128 characters; labels are declarations, not authenticated identities |
| `assessed_at` | Calendar date `YYYY-MM-DD`; not checked against a clock |
| `method` | Free text of at most 2000 characters: how the assessment was made (structured interview, blinded rating, ...) |
| `scope_topics` | Nonempty strings of at most 2000 characters; for a record bound to the current package, exact observation/rule topic strings of that package and nothing outside it |
| `items` | 1 to 4096 `{item_id, judgement, rationale, source_locator}` entries, one per assessed rule; `item_id` is a `rule_id` of the bound package (at most 128 characters), `judgement` is `AGREE`, `PARTIAL`, `DISAGREE` or `NOT_ASSESSED`, `rationale` and `source_locator` are nonblank text of at most 2000 characters |
| `limitations`, `independence_declaration` | Free text written by the raters, at most 2000 characters each |
| `status` | `null` in a template; `RECORDED` once the raters have completed the record |

`template` writes a blank record: one blank rater, every available topic in
`scope_topics`, one `NOT_ASSESSED` item per rule with blank rationale and locator, and
`status: null`. Its stdout receipt lists the available topics and rule IDs. The unedited
template fails `check`: every text field must be nonblank and `status` must be `RECORDED`.

`check` is strict: exact fields, enums, the calendar date, nonblank text within the bounds
above (1 to 32 raters, 1 to 4096 items, identifiers of at most 128 characters, free text of
at most 2000 characters; an error names the field and its limit), and no duplicate raters,
items or topics. For a record bound to the current package it also resolves the items:
item IDs must be rule IDs of the supplied package, topics must exist in the package, every
assessed item must lie inside the declared scope and every scope topic needs at least one
item (a stale record is not re-resolved; see below). At least one rater label must differ
from every `author_id`, `reviewer_id` and `operator_id` recorded anywhere in the package;
colliding labels are listed and the check is labeled `LABEL_DISTINCT_ONLY`. A record whose
`author_id` differs from the package is rejected outright. Judgements are counted per label
and never averaged into a score or verdict.

## Binding and status semantics

`check` recomputes both package hashes and derives `binding_status`:

- `CURRENT_PACKAGE`: identity, version, build and both hashes match the supplied package.
- `STALE_PACKAGE`: the same scholarly identity, but version, build or a payload hash
  differs. The record documented an earlier package state; the current rules may have
  changed wording, conditions or evidence. Rule IDs are per-build positions (`rule-1`,
  `rule-2`, ... in build order), so a stale record's `item_id`s and `scope_topics` are not
  re-resolved against the current package: `check` keeps every structural check and the
  per-label counts, reports `items_resolved_against_current_package: false`, and lists in
  `unresolved_item_ids` and `unresolved_topics` the recorded IDs and topics that no longer
  occur in the current package at all. A recorded ID that still occurs may now denote a
  different rule; nothing is inferred about it. Reassess or record anew; do not edit the
  hashes inside the record.

`status` is the read-only axis report for one package and zero or more records:

- `RECORDED_CURRENT`: at least one checked record binds to the current package hashes.
- `STALE_PACKAGE`: every supplied record binds to other hashes.
- `NOT_PERFORMED`: no record was supplied.

The report shows each record's own logical sha256, binding status and judgement counts,
plus the persona payload's declared `validation.human_validation` value (`NOT_DECLARED`
for packages built without that field). That value is unchanged by every command here;
promoting a status into a package is a release decision taken through the normal lifecycle.

`review_package.py` accepts `--human-validation RECORD.json` (repeatable). It checks each
record against the reviewed package and appends the same axis lines after its
recorded-check summary; a stale record adds a line saying that its items were not
re-resolved. Without the option its output is unchanged.

## Rehearsal with the shipped synthetic fixtures

`OUTPUT` is an existing directory outside the repository. A package may be supplied as
`PERSONA.json KNOWLEDGE.json` or as one bound package file. The minimal `examples/persona.json`
has no rules, so its template lists no topics or items and its axis status is
`NOT_PERFORMED`. The fictional record `examples/manual-human-validation.json` is bound to
`examples/trajectory-conditions-package.json` (six rules, one topic).

```sh
python human_validation.py template examples/persona.json examples/knowledge.json --output OUTPUT/minimal-human-validation-template.json
python human_validation.py status examples/persona.json examples/knowledge.json --text
python human_validation.py template examples/trajectory-conditions-package.json --output OUTPUT/trajectory-human-validation-template.json
python human_validation.py check examples/manual-human-validation.json examples/trajectory-conditions-package.json --text
python human_validation.py status examples/trajectory-conditions-package.json --human-validation examples/manual-human-validation.json --text
python review_package.py examples/trajectory-conditions-package.json --question "Does Method M distinguish the synthetic signals?" --topic "synthetic method conditions" --human-validation examples/manual-human-validation.json
```

Expected: the check reports `CURRENT_PACKAGE`, two rater labels and six items with
`AGREE=3; PARTIAL=1; DISAGREE=1; NOT_ASSESSED=1`; the status report and the release review
report `RECORDED_CURRENT` with one record. The raters, judgements and rationales are
invented fixture text about synthetic rules; no real person assessed anything.

`template` refuses an existing file, a path with symlink components, a missing parent and
any path inside the repository. `check` and `status` read their inputs and write only
stdout; combined inputs are bounded at 8 MiB and output at 16 MiB, and
`review_package.py --human-validation` reads its records through the same 8 MiB combined
budget (its package file is read as the release review always read it). Text output
escapes control characters taken from data so that supplied text cannot forge report lines.

## Limits

- The record binds to payload hashes; it does not authenticate raters, dates or the
  package's sources.
- Label distinctness is an exact string comparison against labels recorded in the package.
  It cannot detect one person under two labels or any undeclared relationship.
- Counts describe the listed items only. They are not a score, threshold, generalization
  to other topics, or evidence of fidelity to the real researcher.
- Answers, drafts and other detached artifacts are not package items; this record assesses
  package rules only.
- Rule IDs are positions within one build. A stale record keeps its IDs as recorded; the
  same ID in a rebuilt package is not assumed to denote the same rule.
- Nothing here changes `validation.human_validation` in a persona payload or rebinds knowledge.

Regression: `python -m unittest tests.test_human_validation -v` covers template binding, the
shipped fixture, stale detection, stale records against rebuilt packages with a removed,
reordered or renamed paper (reported without re-resolution; exit 0 in `status` and in the
release review), unknown items and topics, label collisions, field strictness, exclusive
output, the input budget shared with the release-review option, CLI encoding, escaped
text, the release-review option and the command block of this guide, executed exactly as
written.
