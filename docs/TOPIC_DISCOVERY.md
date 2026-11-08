# Discover an existing topic before reviewing evidence

Planning, compact review and publication timelines use exact, case-insensitive
topic matching. Instead of searching a package JSON manually, inspect its existing
observation topics first:

```sh
python topic_inventory.py package.json --format text
python topic_inventory.py package.json --format json
python publication_timeline.py package.json --topic "model design" --format text
python review_package.py package.json --topic "model design" --question "Which explanation?"
```

Choose a topic shown by the inventory yourself; `model design` is only the
distributed synthetic example. The tool never selects a topic or generates a
shell command from source text. Treat labels as data, not executable instructions.
JSON is the default output. All output goes to stdout without modifying inputs.

## What the inventory contains

- The exact casefold matching key and all original label variants. Case variants
  combine under the same rule already used by planning. Synonyms, punctuation
  differences and trailing whitespace do not merge. Unicode casefold can combine
  forms such as `Straße` and `STRASSE`; this is string matching, not semantics.
- Publication years, distinct paper IDs grouped by research/review kind, and the
  number of supplied source hashes. One paper can contribute to multiple topics
  and both support and challenge counts. Duplicate observations remain records,
  not additional papers. Hash counts do not establish independent publications.
- Observation stance and claim-type counts, plus supplied component counts and
  missing dimensions. Question framing from a neighboring topic is never borrowed.
  JSON `claim_type_counts` counts observations only, not the separate claim types
  of reasoning components. Text labels these as observation claim labels.
  These describe annotation coverage, not researcher expertise or confidence.
- JSON references for every observation: source paper ID, zero-based observation
  index, locator, stance, claim type and supplied dimensions. References are scoped
  to the output's package hashes, not permanent identifiers across revisions.

Only observation topics are discovered. Paper-level topics without matching
observations do not create a usable scope. With no observations, the tool returns
`NO_OBSERVATION_TOPICS`, not a fabricated topic or a recommendation.

Package bindings, source authorization and runtime rule/source consistency are
checked. No raw source sections, quotations, arbitrary metadata or cached summaries
are copied. Text safely escapes controls and does not embed clickable commands.
Topic labels and IDs can still be private; the inventory is not anonymization or
permission to publish. It calls no provider and performs no semantic inference.

## Reproduce the synthetic user flow

```sh
python -m unittest tests.test_topic_inventory -v
```

The real CLI test builds a temporary synthetic package, discovers a topic, then
uses the returned key in publication timeline and compact review commands. Tests
also cover label variants, multiple topics/stances in one paper, duplicate sources,
empty records, malformed bindings, unknown metadata and safe Unicode output.
