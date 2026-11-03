# persona-for-research

공개 학술 근거의 범위 안에서 연구자 페르소나를 구축·검증·활용하는 프레임워크입니다.
Evidence-bounded scholarly simulations, with explicit provenance and holdout isolation.

**A persona is a scholarly simulation, not the researcher.** Private beliefs,
unpublished opinions, personal memories and private communications are outside scope.
No actual researcher persona, article corpus, knowledge database or validation scores
are included in this repository.

For the complete synthetic CLI round-trip, current UX limits and prerequisites
for real-scholar evaluation, see [workflow review](docs/WORKFLOW_REVIEW.md).

## Included

- Generalized construction lifecycle and separate evidence/predictive/human/runtime validation axes.
- Logical JSON binding validator (`persona.py`) and a holdout-redacting projection helper (`safe_canonical_read.py`).
- Synthetic templates and tests; a portable agent workflow in `SKILL.md`.

This is a framework and mechanical tool release. It is not a trained model, a complete
corpus harvester, a turnkey multi-agent runtime, or proof of scholarly validity.

## Quick start

Python 3.10+, standard library only:

```sh
python3 persona.py examples/persona.json examples/knowledge.json
python3 safe_canonical_read.py examples/persona.json
python3 -m unittest discover -v
```

The synthetic example has no learned rules and no papers. Passing means its
mechanical bindings are consistent, not that any real persona has been validated.

## Two layers

**Persona Core** represents paper-supported question framing, reasoning, judgment,
counterargument, uncertainty and writing policies. **Knowledge Layer** represents
attributable scholarly content. Expanding knowledge does not silently change the
canonical reasoning policy. Training evidence, holdout evidence, comparator-author
evidence and fresh external evidence must remain distinct.

## Binding and retrieval

The example uses a documented **logical JSON payload hash**: SHA-256 of UTF-8 JSON
with sorted keys, compact separators, `ensure_ascii=False`, no NaN and no excluded
fields. This is distinct from an original-file byte hash. The knowledge map binds
to the whole persona payload and matching author/version/build. Runtime papers must
be training-only, explicitly eligible, author-matched and source/locator-linked.
The validator checks hash shape, not whether a source actually exists or supports a claim.

`safe_canonical_read.py` is a conservative convenience projection. It removes many
explicit holdout fields but cannot recognize every possible encoding or mislabeled
record. It is **not** a privacy anonymizer, access-control system or publication filter.
Enforce split authorization before retrieval; never rely on redaction to repair leakage.

See [lifecycle](docs/ARCHITECTURE.md), [workflow](SKILL.md),
[publication boundary](PUBLICATION.md) and [security](SECURITY.md).
No license has been selected by the owner yet; see [rights](RIGHTS.md).

## Paper-to-research-plan workflow

```sh
python research_workflow.py examples/research-corpus.json --question "Which experiment discriminates models?" --topic "model design"
```

The JSON result contains a hash-bound persona/knowledge package, chronological
research/review trajectory and a question-specific planning scaffold. Input papers
must be explicitly authorized, author-matched, training-only and runtime-eligible.
Each operator-curated observation supplies method, topic, condition, limitation and
locator. Exact topic matching determines coverage; unmatched topics abstain.
Applications retain rule/paper/locator links and are labeled system inference.
Coauthor attribution remains uncertain. No LLM, automatic paper extraction,
cross-paper generalization, scientific validation or real researcher data is included.
Synthetic source hashes are placeholders, not receipts for real publications.

### Repetition and counterevidence

Observations may declare `stance: support` (default) or `challenge`. Application
groups exact method/condition pairs, distinguishing a single paper, repetition
across distinct papers, and contested patterns. Each supporting/challenging item
retains paper ID, locator, year and research/review type. Challenge observations
produce challenge prompts, not recommendations. This deterministic grouping is
not semantic synthesis or proof that a method is unique to an individual author.

### Methodology over publication time

Application output also includes `methodology_trajectory`, scoped to the requested
topic. Exact topic/method/condition groups retain every observation with rule and
paper IDs, source locator, limitation, quote, claim type and verification label.
Chronological year buckets separate support from challenge and original research
from reviews. Distinct-paper counts do not imply independent replication.
Within-year disagreement and cross-year stance variation are reported separately;
a later challenge never automatically overwrites earlier evidence. These are
system-generated descriptions of the supplied publication record, not claims of
career stage, personal belief, individual authorship or a change of mind. Missing
years do not establish inactivity. No actual biography or career source is ingested.

### Evidence-linked reasoning cards

```sh
python observation_input.py examples/reasoning-corpus.json --question "Which explanation?" --topic "model design"
```

An observation may include a `reasoning` object with `question_framing`,
`alternative_explanation`, `evidence_standard`, `falsification_check` and/or
`uncertainty`. Each supplied component requires `text`, `locator`, `evidence_quote`
and `claim_type` (`explicit_statement` or `operator_interpretation`). The verified
intake checks each component's quote independently against its own source section.
Application output preserves these labels in `reasoning_cards`, reports missing
dimensions without filling them, and retains challenge/support stance and coauthor
attribution uncertainty. A verified quote does not verify the interpretation.

All cards are manually curated input, not reconstructed private thoughts. Output
`processing` explicitly reports that no LLM or automatic extraction was used.
Use only permitted source text and short authorized quotations; full sections are
not copied into the output. The unverified `research_workflow.py` path performs
structural checks only; verification labels supplied directly to it are not
independent verification receipts and are reset to `NOT_PERFORMED`. Nothing here authenticates a publication or
establishes that a researcher personally endorses a reasoning component.

Verified intake returns an in-process receipt bound to the complete curated input.
Changing that input before building fails. A JSON round-trip loses the receipt;
run the intake again rather than trusting saved status strings. Only the local-file
adapter attests that source bytes were checked. Receipts are not signatures or a
security boundary against Python callers. New packages also bind the complete
knowledge-paper payload into the persona hash, detecting later source metadata,
authorization, quote or observation edits. Legacy packages without this additional
binding retain their previous validation behavior and should be rebuilt.

### Coverage diagnostics

`evidence_coverage` describes the topic-matched input: original/review paper IDs,
observation counts and per-reasoning-dimension evidence links, claim-type counts,
quote-match counts and missing dimensions. It distinguishes no observations from
observations lacking reasoning components. Repeated observations do not multiply
the distinct-paper count. Challenge records retain their own rule links.
`ALL_DIMENSIONS_REPRESENTED` means only that each field has a supplied record, not
that a persona is ready, representative, accurate or scientifically validated.
There is no confidence score, universal corpus-size threshold or automatic source
acquisition. Use the missing dimensions to guide authorized manual evidence review.

Runtime packages now project only documented paper, observation and reasoning
component fields. Full source `segments` and unknown nested metadata are omitted
from both verified and unverified builds. Supported scalar fields are type-checked,
and observation claim types are restricted to statement/interpretation. This closes
accidental export of extra fields; it is not anonymization or detection of sensitive
text placed inside a legitimate quote or other supported string. Source permissions
and split controls remain necessary before intake and before sharing output.

## Review a candidate release

```sh
python compare_releases.py previous-package.json candidate-package.json
```

This read-only comparison accepts bound packages or the wrapper emitted by the
workflow CLIs. It validates both package hashes and scholarly identities, then
lists added, removed and structurally modified paper records, source-hash changes,
observation changes and changes to the rule payload. Evidence or rule changes yield
`REVIEW_REQUIRED`; version/build changes alone do not imply new evidence. It never
uses Python numeric equality to compare payloads: canonical JSON hashes distinguish
integer, floating-point and boolean values while ignoring object-key ordering. It never
updates either package or approves a release. Paper IDs must remain consistently
curated; changed hashes do not establish corrections, retractions or a researcher's
change of mind. Legacy packages without a bound knowledge payload must be rebuilt.

## Verified observation intake

```sh
python observation_input.py examples/observed-corpus.json --question "Which experiment?" --topic "model design"
```

The input adds `segments` (locator-to-text mapping), `segments_sha256` (SHA-256 of
sorted compact UTF-8 JSON with ensure_ascii=False), and observation `evidence_quote`
and `claim_type` (`explicit_statement` or `operator_interpretation`). Only authorized
training segments are inspected. Quotes must occur exactly at their locator; altered
segment hashes and fabricated quotes fail. Full segments are removed before package
construction; observation quotes and their verification labels reach application
steps. Supplied text/hash agreement does not authenticate publications or prove that
the interpretation follows from the quote. No parser, LLM or search service is called.
Only short synthetic text is included in the distributed example.

## End-to-end and CI verification

`test_cli_e2e.py` runs the synthetic workflow through actual CLI subprocesses and
checks failed inputs and reproducible output. GitHub Actions runs standard-library
tests, publication scanning and manifest byte verification on Linux and Windows
with Python 3.10 and 3.12. Actions are commit-pinned; token permissions are read-only,
checkout does not persist credentials, no secrets or deployment steps are used.
The manifest describes LF-normalized published files, enforced by .gitattributes.
External model/search behavior and scientific meaning are not evaluated by CI.

## Read authorized local source files

```sh
python corpus_files.py examples/file-corpus.json --source-root examples/synthetic-sources --question "Which experiment?" --topic "model design"
```

The manifest adds a portable relative `source_file` for each paper and the exact
`source_sha256` of its UTF-8 .md/.txt bytes. Each document must have unique `## Section`
headings; observation locators equal those headings. The adapter preflights identity,
training split and authorization, confines resolved paths to the selected root,
checks actual file bytes, parses sections, checks quotes and constructs the existing
research package/plan. It does not scan directories or download papers. Full sections
are omitted from the output package, but the authorized short observation quotes are
retained. A byte hash proves agreement with a supplied file, not its publisher or
scholarly correctness. PDF/OCR, article acquisition and semantic extraction remain
unimplemented. Keep real inputs and generated packages outside the public repository.
