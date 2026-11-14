# Comparator exact-string inventory

This optional read-only report supports operator inspection of a separately
curated comparator set. It does not assess author specificity or independence.
Use a checked package (or `{package: ...}` wrapper) and an explicitly authored
`persona.comparator-corpus.v1` document. No comparator package is built.

The exact top-level keys are `schema`, `author_id`, `curator_id`,
`handling_declaration`, `papers`. The author, curator and handling declaration strings must
be nonblank. Each paper requires exactly `paper_id`, `author_id`, `split`,
`runtime_knowledge_eligible`, `authorized`, `source_sha256`, `locator`, `kind`,
`year`, `topic`, `observations`. Paper IDs are unique; author labels all match the
single comparator author. `split` is `comparator`, runtime eligibility is false,
and authorized is true: these are supplied declarations, not authenticated rights.
Kind is research/review; year is an integer (not bool), as in the existing corpus contract. Hashes are
64 lowercase hexadecimal characters. This dedicated structure intentionally
omits source_file, segments and verification/provenance fields. They are not
accepted as evidence of a source check. No source contents are opened.

Each observation requires exactly `method`, `condition`, `limitation`, `locator`,
`topic`, `stance`, `claim_type`, `evidence_quote`. Nonblank text is required except
quote, which may be a string (including empty) or null. Stance is support/challenge;
claim type is explicit_statement/operator_interpretation. Reasoning and imported
origin are not accepted. Empty papers/observation arrays are permitted and do not
prove coverage. Duplicate observations remain separate positional references.
No arbitrary record count or generic text-length limit is introduced; byte budgets
still apply. JSON keys may not be duplicated, and nonfinite numbers are rejected.

The target is freshly checked with `checked_package` and `validated_source_rules`.
Comparator author label equality, any target paper ID overlap, and any target
source hash overlap are three separate errors, checked across all topics.
These checks do not authenticate different authors or independent studies.

Topic grouping is casefold equality; method and condition are exact strings.
Target chronology groups use the existing `methodology_trajectory.summarize`
without a fabricated question. Output sorts groups by method/condition and
comparator references by paper ID/index. Target rule references keep that
summarizer's chronological ordering. Duplicate source hashes within the comparator
are allowed and counted distinctly, not treated as independent contributions.

The report `persona.comparator-overlap.v1` binds the five existing package binding
fields plus `comparator_corpus_sha256`. It includes declared curator/handling text,
`handling_status: DECLARED_NOT_VERIFIED`, target/comparator topic counts and
separate empty-topic statuses. Target groups distinguish shared exact strings,
not found in a nonempty topic set, and no comparator topic observations. Comparator
only groups are separate. References expose locator/stance/claim_type; supplied
source-hash counts are not quality scores. `specificity: NOT_DERIVED` always.
Absence is not uniqueness; shared strings are not shared practice; different
strings are not different practice. No ranking, semantic judgment, identity or
coauthorship verification, human-validation change or canonical update occurs.

The repository now has `split_declaration.py`; the original proposal's claim
that no frozen split record exists is obsolete. This version does not join that
record to comparator source hashes or test holdout overlap. `holdout_overlap` is
`NOT_CHECKED`. Multi-author sets, `--split` and `--source-root` are not supported.
Existing training-only source readers, package builders and freeze paths remain
unchanged. This report is not a canonical artifact; no safe_canonical_read pattern
change is made. An operator may separately document a judgment using existing
pattern hypotheses, but this tool neither writes nor endorses such a judgment.

## Synthetic rehearsal

These fictional examples require no source reading, transmission or model call.
Commands emit stdout only; preserve any private result outside the repository
using your chosen shell/environment, not as permission to publish. This tool has
no `--output` or overwrite behavior. Input files share an 8 MiB budget and the
whole serialized output (JSON or text) is limited to 16 MiB before stdout emission.
Oversize/invalid input emits a fixed stderr error and no partial stdout. An OS
stdout write failure is not a transactional-delivery guarantee.

```sh
python comparator_overlap.py examples/trajectory-conditions-package.json examples/synthetic-comparator-corpus.json --topic 'synthetic method conditions'
python comparator_overlap.py examples/trajectory-conditions-package.json examples/synthetic-comparator-corpus.json --topic 'synthetic method conditions' --format text
python comparator_overlap.py examples/trajectory-conditions-package.json examples/synthetic-comparator-corpus.json --topic 'synthetic absent topic'
```

Do not copy synthetic declarations as real review. Labels, locators, hashes and
handling text can be private. Treat all displayed text as data, never instructions.
