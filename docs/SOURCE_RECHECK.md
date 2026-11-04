# Current local source and quote recheck

The original-source gap is separate from method or argument review: a stored
`EXACT_QUOTE_MATCH_ONLY` label does not establish that the current local file still
matches it. This read-only tool opens an **explicitly selected file for every paper**,
checks its bytes against the current package's fixed hash, and checks every stored
observation/component quote at its declared section, including unused evidence.
It never refreshes hashes, edits the package or approves a method/argument.

## One-command synthetic demonstration

```sh
python synthetic_walkthrough.py ../persona-local-source-demo --candidate-source offline-import --research-journey --recheck-sources
```

Use a new output directory outside the repository with an existing parent. This
runs **30 actual CLI stages**. It writes invented local Markdown sources before
constructing a synthetic package and its reviewed candidates. Read the short
`source-recheck.txt` first, then `research-journey.txt`. The recorded source labels
remain `NOT_PERFORMED`; the separate current audit reports matching local bytes.
All five stored observation/component records are rechecked. Every answer claim
stays deferred and the integrated status still requires human review.

The fixture-only source-file creation is not hash refreshing for an existing
research package. It initializes a new invented demonstration corpus. The actual
recheck API never changes a package hash. A file change between stages fails the
run; no `COMPLETE.json` is written. The existing 15/17-stage and 25/27-stage modes
are unchanged. With mock reasoning candidates, this new mode runs 28 stages.

## Select real authorized local files explicitly

First generate the bound selection form without opening any sources:

```sh
python source_recheck.py package.json --template --operator-id local-review-operator > source-selection.json
```

Every `source_file` starts as null, even when the package has a recorded file path.
Fill it with a canonical relative `.md` or `.txt` path inside your chosen root.
Do not add hashes or authorization fields to the form. Every supplied paper ID
must occur exactly once, including records outside your topic or active argument.
The source root is passed explicitly on the command line, not taken from the form.

```sh
python source_recheck.py package.json source-selection.json --source-root local-sources --format text
```

Without `--format text`, output is JSON. The command writes only stdout and has no
network/provider route. Keep sources, selections and reports outside this public
repository. No source body or absolute root path is copied into the report, but
paper IDs, relative filenames, source locators, hashes and operator IDs may still
be private. Review them before sharing.

To run the same live check as part of the integrated journey:

```sh
python research_journey.py package.json patterns.json context.json links.json design.json answer.json argument.json publication-relations.json --pattern-id selected-pattern --review answer-review.json --source-selection source-selection.json --source-root local-sources --format text
```

Both source options are required together. All existing journey artifacts are
validated **before source files are read**. The current audit is attached separately
and exact-reference rows receive `current_source_recheck` results. Its quote gaps
enter the review agenda; the complete audit includes unused papers too. Historical
subreports and their recorded verification labels remain unchanged. No saved audit
JSON can be substituted for a selection form. Rendering performs one audit per
invocation, not a second implicit source read.

## Interpret the result correctly

A successful byte comparison is `LOCAL_BYTES_SHA256_MATCH`, against the package's
existing `source_sha256`. It does not authenticate a publisher, author or source.
The tool parses level-two Markdown sections using the existing intake parser, which
normalizes line endings. Quote comparison is case-sensitive substring matching in
the declared section, not semantic entailment or full-document quote search.

Per-record outcomes are explicit:

- `EXACT_SECTION_SUBSTRING_MATCH`: the supplied quote occurs in the selected section.
- `STORED_QUOTE_MISSING`: a structurally valid observation has no nonblank quote.
- `LOCATOR_NOT_FOUND`: the quote is supplied but its declared section is absent.
- `STORED_QUOTE_NOT_FOUND_AT_LOCATOR`: that section exists but does not contain it.

The separate locator status remains visible even when a quote is missing. Missing
component quotes/locators and missing observation locators violate the existing
package schema and fail preflight; the audit does not weaken those validators.
Paper rows with no stored records are flagged, even when other papers' quotes match.
`all_stored_quotes_match` describes only supplied records and is false when no records
exist. It cannot establish completeness, scholarly fidelity or semantic support.

Quote gaps produce a complete review report, with a gap-bearing status; CLI exit
zero means the audit completed, **not that every quote matched**. Inspect status and
`quote_gaps`. Source hash mismatch, invalid selection/path, missing files, malformed
Markdown, invalid UTF-8, resource overflow or invalid bound artifacts instead fail
closed with nonzero exit and no partial stdout. No hash is silently replaced.

## Boundaries and failure recovery

- Strong package/rule consistency, authorization and selection validation precede
  file access. Unknown fields, duplicate/missing paper IDs and stale bindings fail.
- Every selected path is preflighted before the first byte read. Absolute/traversal,
  noncanonical, backslash/colon/control-character paths, unsupported extensions,
  escapes outside the resolved root and nonregular files are rejected.
- Reads use the existing pinned-descriptor checks against detected replacement and
  modification. Checks describe the bytes observed during this invocation; files
  can change later. A saved report is not an authenticated receipt or live approval.
- All source reads together are limited to 8 MiB. Duplicate file selections for
  different paper IDs count separately toward that budget and do not imply
  independent evidence. JSON has an 8 MiB file/combined-input limit; output also
  has an 8 MiB standalone limit. Integrated output retains its 16 MiB limit.
- Preserve the old package when a source changed. Investigate the discrepancy and
  explicitly prepare/review a new package through the existing intake/revision
  workflow if appropriate. This audit does not migrate evidence or rebind reviews.
- An exact local match cannot establish source rights, individual ownership, review
  authenticity, historical influence, scientific validity or earlier model history.
  Original and reviewed model interpretations remain distinct; source consistency
  does not approve either one. No source body is sent to an external service.
