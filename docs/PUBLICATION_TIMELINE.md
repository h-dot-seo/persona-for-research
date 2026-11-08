# Review questions, methods and evidence across publication years

`publication_timeline.py` makes a read-only artifact from a bound package. It
connects each supplied question-framing or other reasoning record to its own
method, condition, limitation, source locator, paper kind and publication year.
It does not reconstruct private thought, a career narrative or a change of mind.

## Synthetic CLI example

Save generated artifacts outside this public repository:

```sh
python observation_input.py examples/reasoning-corpus.json --question "Which explanation?" --topic "model design" > /tmp/synthetic-package.json
python publication_timeline.py /tmp/synthetic-package.json --topic "model design" --format text
python publication_timeline.py /tmp/synthetic-package.json --topic "model design" --format json
```

`/tmp` is an example temporary directory on Unix-like systems. On Windows, use
an existing temporary directory. Output is stdout; the tool does not overwrite
the package. JSON is the default format. The portable automated demonstration is:

```sh
python -m unittest tests.test_publication_timeline -v
```

The subprocess demonstration constructs temporary synthetic sources, builds their
package with the real intake CLI, then exercises both timeline formats and a
rejected input. No actual researcher, external service or model is used.

## How to read the artifact

- Topic matching is exact and case-insensitive, not semantic search. All counts
  and displayed records use that topic. An absent topic yields `NO_MATCHING_RECORDS`.
- Years are publication years. Same-year paper ordering is by ID, not event time.
  Original observation indexes are zero-based within the paper and meaningful
  only with the artifact's bound package hashes.
- Earlier support and later challenges both remain. Same-year research/review
  disagreement is retained. No latest record supersedes another automatically.
- Each observation has its own stance, claim type, method, condition and limitation.
  `explicit_statement` is a recorded classification, not verified individual
  author ownership. `operator_interpretation` remains distinct from it.
- Supplied reasoning components keep their own quotes, locators and claim types.
  Reviewed mock/imported-origin components also retain candidate/review provenance in JSON.
  A missing question-framing record stays missing; nothing is borrowed from another
  paper or invented. Overall missing dimensions summarize coverage, not quality.
- Every paper retains its supplied source hash and source locator. Duplicate hashes
  do not remove records, and distinct hashes do not prove independent publications.
- Text output escapes terminal controls and keeps Unicode. JSON retains documented
  record fields and bindings. Neither format truncates contrary evidence.

## Validation and limits

The tool checks package hashes, authorization and training-only eligibility, then
validates source observations. It checks saved rules against rebuilt source-derived
rules, including agreement of supported recorded quote-verification labels, and
rejects conflicting source IDs, years, paper kinds or method records. The same
consistency check protects planning and compact review. It ignores cached trajectory/application
summaries and derives its timeline from knowledge observations. Hashes establish
self-consistency, not authenticity of the source or producer.

Recorded byte/quote checks are explicitly not rechecked. No original source file
is opened. Only documented fields are projected into the artifact; arbitrary
metadata and raw source sections are not copied. Existing quotes and interpreted
text can still be sensitive or subject to rights restrictions, so projection is
not anonymization or authorization to publish. Keep actual scholarly packages
outside this public repository and obtain appropriate permission before sharing.

Publication dates do not date the underlying experiments, choices or ideas. Missing
years do not establish inactivity. Reviews are not independent replication, and
coauthorship does not establish individual ownership. Semantic support, genuine
researcher fidelity and career-stage interpretation remain unevaluated.

## Optional publication relationships

Use `--publication-relations ../publication-relations.json` to add separately
[declared publication context](PUBLICATION_CONTEXT.md): review summaries, material
reuse, versions, method extensions and challenges with exact basis references.
The overlay distinguishes selected, one-sided and outside-source relationships,
without changing original counts, roles or decisions. Missing declarations do not
establish independence, and chronology does not prove influence. Omitted context
preserves earlier output; an explicit empty form adds a bound empty context.
