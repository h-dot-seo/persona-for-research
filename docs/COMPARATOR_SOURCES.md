# Optional comparator-only source recheck

`comparator_overlap.py` remains a structure-only exact-string inventory by default.
Supply **both** `--source-selection MAP` and `--source-root ROOT` to reread only
comparator files. Neither flag alone is accepted, before reading JSON inputs.
`comparator_sources.inspect_sources` is the supporting library, not a new CLI.
The target package is mechanically checked but its source files are **not read**.
Use the separate target `source_recheck.py` workflow when independently authorized.

The comparator v1 strict structure is unchanged: source_file cannot be inserted
into that corpus. Instead author a separate exact four-key mapping:
`schema: persona.comparator-source-selection.v1`, `comparator_corpus_sha256`,
`operator_id`, and `sources`. The hash is the logical complete comparator JSON
hash (`persona.payload_sha256`), not a signature. Operator is a nonblank label up
to 128 characters, not authenticated identity. Every source row contains exactly
`paper_id` and `source_file`. Include every comparator paper once, including papers
outside the requested topic and papers without observations. No automatic path
selection or mapping-template CLI is provided. Independently authorize access;
this mapping and the corpus's authorization flags do not authenticate consent.

Relative paths use existing source_recheck canonical portable Markdown/text rules:
1024-character maximum, no absolute path, backslash, colon, dot/traversal components,
redundant separators or ASCII controls. Existing journey path checks reject links
and Windows reparse points in the root or ancestors and selected files. Paths are
regular files inside the explicit root. Windows normal 8.3 aliases are compared by
filesystem identity, not assumed to be links. The complete mapping and all paths
are checked before any source bytes are opened. Existing training-only source_paths
and its gate remain unchanged; no fourth path-policy implementation is introduced.

Raw bytes are read through the existing pinned-descriptor reader. A mismatch with
any declared source_sha256 rejects the report. Bytes are decoded as UTF-8 and
parsed by existing `sections`; section parsing normalizes line endings. Stored
observations, not just matched-topic ones, receive exactly one of:
`EXACT_SECTION_SUBSTRING_MATCH`, `STORED_QUOTE_MISSING`, `LOCATOR_NOT_FOUND`,
`STORED_QUOTE_NOT_FOUND_AT_LOCATOR`. Quote gaps are reported, not acceptance failures.
Missing/blank quote takes precedence over absent locator. Empty observation lists
are explicitly `NO_STORED_QUOTES_TO_CHECK`, not a claim of full evidence coverage.
Bodies and quote strings are not emitted in the source-check object, but locators,
filenames and hashes may be private. The original inventory retains its own fields.

Only the opt-in result changes: its boundary describes comparator-only reading, source_check becomes
`COMPARATOR_ONLY_RECHECK_PERFORMED`, and `comparator_source_recheck` is added with
schema `persona.comparator-source-recheck.v1`, corpus/selection hashes, declared
operator, per-paper byte counts and quote records. `target_source_check` is
`NOT_PERFORMED`. No grouping, stance, specificity, holdout, human-validation or
canonical decision changes. Existing inspect()/default JSON and text stay unchanged.
The default structural boundary remains unchanged; the opt-in boundary no longer
claims that no source bytes were read.

JSON file bytes share 8 MiB across package, comparator and mapping. The library also
bounds a detached finite JSON encoding of those inputs to 8 MiB, which can be larger
than compact input due to escaping/wrapping. Comparator raw bytes separately share
8 MiB; selecting one file for two paper IDs reads/counts it twice. Final combined
JSON/text output is bounded to 16 MiB before stdout emission, with fixed error text
and no partial report for validation errors. OS stdout failures are not transactional.
The reader holds a bounded whole file in memory; it is not a streaming hash reader.

Identity checks detect some replacements and changes, not all hostile concurrent
filesystem activity. Files may change after reading. Hash/quote matches are not
source authenticity, rights clearance, independence, semantic support, review,
holdout membership verification or approval. No network, model or transmission
occurs. Keep outputs outside the repository and do not publish private paths.

## Fictional rehearsal

The new source fixture is separate from existing synthetic-sources. Its mapping
and corpus were explicitly authored for this invented text; never copy them as
real operator declarations. No pre-existing fixture or target package was changed.

```sh
python comparator_overlap.py examples/trajectory-conditions-package.json examples/synthetic-comparator-source-corpus.json --topic 'synthetic method conditions' --source-selection examples/synthetic-comparator-source-selection.json --source-root examples/synthetic-comparator-sources
```
