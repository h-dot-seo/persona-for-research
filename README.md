# persona-for-research

공개 학술 근거의 범위 안에서 연구자 페르소나를 구축·검증·활용하는 프레임워크입니다.
Evidence-bounded scholarly simulations, with explicit provenance and holdout isolation.

**A persona is a scholarly simulation, not the researcher.** Private beliefs,
unpublished opinions, personal memories and private communications are outside scope.
No actual researcher persona, article corpus, knowledge database or validation scores
are included in this repository.

## Start here: one synthetic command

```sh
python synthetic_walkthrough.py ../persona-synthetic-demo
```

Use a new directory outside this repository; its parent must already exist. The
runner executes 15 real CLI stages, never overwrites a prior run, and leaves answer
review deferred. Read `reader-scope.txt` first, then the generated `START_HERE.txt`
for the full reading order. No LLM or real scholar material is used. See the
[complete quickstart and recovery guide](docs/QUICKSTART.md).

For the integrated source → method → argument route, including imported pattern
review and publication/review context, run:

```sh
python synthetic_walkthrough.py ../persona-research-journey --candidate-source offline-import --research-journey
```

This executes 27 synthetic CLI stages. Read `research-journey.txt`: it joins source
chronology, explicit pattern explanations, target-context judgments, design uses,
answer review and argument roles without inferring citations or approving a plan.
Rejected proposals and deferred answer claims remain visible. See the
[integrated research journey](docs/RESEARCH_JOURNEY.md) for standalone artifact inputs,
limits and the distinction between composed review and complete provenance history.

To also recheck original local bytes and every stored quote, add `--recheck-sources`
to the integrated demo command. This runs 30 synthetic CLI stages. Read the compact
`source-recheck.txt` first: current checks remain separate from historical labels,
quote gaps remain explicit, and source hash changes fail closed. See
[local source recheck](docs/SOURCE_RECHECK.md) to select authorized files explicitly.

Add `--review-method-use` to the extended demo to record how the selected pattern
is considered for a named design step. Combined with source recheck, this runs 32
synthetic stages. `method-applications.txt` shows the step-specific rationale,
conditions, proposed checks and missing failure criteria without modifying the plan
or promoting references into active evidence. See [method application](docs/METHOD_APPLICATION.md).

For the complete synthetic CLI round-trip, current UX limits and prerequisites
for real-scholar evaluation, see [workflow review](docs/WORKFLOW_REVIEW.md).

CLI JSON inputs reject duplicate object keys, non-finite numbers (including
overflowing exponents), and more than 128 nested containers. Ambiguous repeated
authorization/split fields are errors, not a last-value-wins choice. This applies
to source intake, package validation/comparison and the projection helper; it does
not authenticate an authorization declaration or grant source access.

## Compact review

```sh
python review_package.py saved-package.json --question "Which explanation?" --topic "model design"
```

The UTF-8 text view validates both package bindings and recomputes the application
for the explicit question/topic; saved wrapper summaries are ignored. It shows all
matched support/challenge records, author/version/build identity, source IDs and locators, conditions, limitations,
reasoning claim types, missing supplied records and recorded check counts. It never
silently truncates contrary evidence. Larger corpora produce longer views.
Recorded checks are not rerun against source files by this renderer. It is not a
confidence/readiness judgment or a new interpretation of the researcher. Control
characters in supplied text are escaped to prevent forged terminal lines.

## AI-assisted candidate contract (mock only)

```sh
python extraction_adapter.py examples/reasoning-corpus.json --mock-response examples/mock-extraction-response.json
```

The provider-neutral request/response contract is implemented with a synthetic
canned-response mock only. It verifies the full source authorization/split boundary
and supplied segment hashes before invocation, then checks every proposed source,
locator and quote. Results remain candidates requiring human semantic/attribution
review; they cannot automatically enter a canonical package. Actual LLM inference
and external transmission are explicitly false. Real provider adapters are disabled.
See [extraction contract and review requirements](docs/EXTRACTION_CONTRACT.md).

### Bring a separately generated model response

`model_handoff.py` prepares a local source-bounded request and imports a saved
response from a separately authorized coding assistant or model API. Its version-2
bundle records declared provider/model/run provenance without pretending the import
ran a model or authenticated the producer. Exact source/quote checks and deferred
operator review remain mandatory; imported origins stay distinct from synthetic
mocks. No provider is invoked and no data is transmitted by these commands.
See [offline model handoff and limits](docs/MODEL_HANDOFF.md). The complete synthetic
journey also accepts `--candidate-source offline-import` to exercise 17 real CLI
stages without running a model. Mixed mock/imported revision audits preserve each
origin and declared provenance while keeping unaudited initial history explicit.
For existing local-file manifests, add `--source-root` to the handoff and operator
review commands. They recheck the selected source bytes and reconstruct segments
at every stage, avoiding manual text copying and refusing stale evidence.

### Draft the first method observations

For selected papers with no observations yet, the handoff commands accept
`--task observations` to prepare a separate review-only contract. `observation_proposals.py` retains original
support/challenge proposals alongside explicit review judgments, leaving unsupported
conditions/limitations/topics null. It never converts model output to a manual card
or runtime package. See [first-observation proposals](docs/OBSERVATION_PROPOSALS.md).
After complete explicit review, [observation append candidates](docs/OBSERVATION_REVISION.md)
connect those proposals to runtime evidence without losing imported origin. The
separate append card starts empty, pins source files and every accepted target, and
requires a new version/build. Original/reviewed/rejected evidence stays auditable;
existing observations and canonical packages are never overwritten.

### Record operator decisions without automatic promotion

`operator_review.py` creates a deferred review template and applies explicitly
recorded decisions to a separate revision candidate. Decisions bind the complete
candidate bundle and exact input corpus. Targets are explicit, occupied dimensions
require an exact prior-component hash for replacement, and deferred/rejected items
are never silently incorporated. Proposed claim types remain separate from reviewed
classifications, with candidate/review provenance retained in reasoning cards.
Reviewer identity is a recorded declaration, not authenticated proof of human review.
Its `--targets` mode lists all same-paper observations and exact prior-component
hashes without selecting targets or generating approvals, so operators can inspect
both support and challenge records before deciding.
See the [review workflow and schema](docs/OPERATOR_REVIEW.md).

## Included

`audit_design_chain.py` verifies consecutive declared candidate-review revisions and maps
retained final evidence to its introducing stage. Final component coverage remains
separate from unaudited initial history. See [linear revision-chain audit](docs/DESIGN_CHAIN.md).

`audit_design_lineage.py` replays one declared mock or imported candidate review and checks that
it exactly reproduces the package behind a design scenario. It traces selected
evidence and missing proposal fields while flagging inherited origins outside that
replay. See [single-revision lineage audit](docs/DESIGN_LINEAGE.md).

`design_scenario.py` traces operator-authored proposed research steps to explicit
reasoning links, retaining unreferenced counterevidence and missing design fields.
It does not generate experiments or turn source claims into author recommendations.
See [proposal traceability](docs/DESIGN_SCENARIO.md).

`reasoning_links.py` reviews manually supplied links between source observations or
reasoning components, including different methods, topics and publication years.
Links remain operator interpretations, separate from endpoint claim types and
canonical rules. See [cross-publication links](docs/REASONING_LINKS.md).

Use `topic_inventory.py package.json --format text` to discover available exact-topic
scopes before planning or review. It lists existing observation topics and coverage,
without semantic merging, ranking or automatic selection. See [topic discovery](docs/TOPIC_DISCOVERY.md).

`publication_timeline.py` creates a chronological JSON or compact text review of
supplied questions, methods and evidence. It keeps research/review sources,
support/challenge records and explicit-statement/interpretation labels separate,
without inferring a career narrative. See the [timeline workflow](docs/PUBLICATION_TIMELINE.md).

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

Repetition now requires distinct supplied source hashes as well as distinct paper
IDs. Multiple supporting IDs sharing one hash are labeled
`MULTIPLE_RECORDS_SAME_SOURCE_HASH`, and each pattern reports
`distinct_source_hash_count`. Identical hashes flag shared source content; different
hashes do not establish independent publications or experiments. Observations and
IDs remain intact. Patterns containing only challenges are `CHALLENGE_ONLY`, while
mixed support/challenge remains `CONTESTED`. Coverage paper counts are ID counts,
not independently authenticated publication counts.

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
binding lack that tamper check and should be rebuilt. Every runtime paper, including
legacy records, must explicitly declare `authorized: true`; missing values, false
and truthy substitutes such as `1` or `"true"` are rejected at validation/application.
This declaration is a required gate, not proof of permission or source rights.

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
approves a candidate for runtime use. Planning, compact review and timeline views
add a source/rule consistency check, including supported recorded quote labels.
A comparison can diagnose an inconsistent candidate that these runtime views reject.
Fix its source observations and rebuild rather than editing rule copies or hashes.
Hash/label agreement is not source authentication or new semantic verification. It never
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

### Publication-year scope of a proposed design

`publication_scope.py` marks later-publication and same-year unresolved endpoints
for an explicit reference year, preserving the complete design and unused
counterevidence. It distinguishes research/review metadata without assigning
ownership of ideas or claiming historical validity. See
[publication scope review](docs/PUBLICATION_SCOPE.md).

### Evidence-bound answer drafts

`answer_draft.py` ties operator-supplied answer claims to fixed observation/component
references and records hash-bound, per-claim review decisions. Stored-quote equality
is separate from semantic support, source verification and author attribution.
Rejected claims and uncited observations remain visible. See
[answer-draft review](docs/ANSWER_DRAFT.md).

### Integrated answer/design review

`review_journey.py` combines answer claims, design steps and publication-year review
into one packet. Its exact-reference index connects uses without inferring agreement;
mechanical prompts expose missing uncertainty, recorded review decisions and timing
warnings, including answer-only citations. See [integrated review](docs/REVIEW_JOURNEY.md).

### Reader evidence-scope disclosure

`evidence_scope.py` shows the answer/design scope without treating repeated paper
IDs or citations as independent evidence. It groups supplied source hashes, keeps
unused records and recorded mock origin distinct, and preserves missing uncertainty
and review warnings. See [reader scope disclosure](docs/EVIDENCE_SCOPE.md).

### Operator-declared argument steps

`argument_map.py` connects existing answer premises to operator-synthesis conclusions
with explicit bridges, assumptions and defeaters. It rejects circular dependencies,
keeps rejected premises visible and never transfers citations automatically. See
[argument-map review](docs/ARGUMENT_MAP.md).

### Synthetic label evaluation, kept separate from modeling

`evaluate_synthetic.py freeze` captures validated answer/citation metadata without
reading labels. Its separate `evaluate` command measures exact agreement with
explicit synthetic holdout-role labels: citation matches/omissions, challenge
preservation, and answer/source claim-type distinctions. No aggregate score,
researcher-fidelity claim or semantic validation is provided. See
[synthetic evaluation and its limits](docs/SYNTHETIC_EVALUATION.md).

### Prepare authorized local source files

`prepare_local_manifest.py` fills byte hashes and section-locator inventory for an
explicit training-only file selection, leaving observations empty. The result uses
the existing manifest format and feeds `corpus_files.py` after manual curation.
No full body, claim extraction, publication lookup or model call is added. See
[local input preparation](docs/LOCAL_INPUT_PREPARATION.md).

## Manually structure selected local evidence

After local input preparation, [manual observation cards](docs/MANUAL_LOCAL_OBSERVATIONS.md)
let you write one source-bound method/condition/limitation and optional reasoning
component at a time. Explicit stance and attribution choices, full-corpus local
quote checks and stale-card rejection preserve the review boundary. No model or
claim generator runs; the documented synthetic research/review CLI journey is executable.

## Start a local answer/design review

[Create a review workspace](docs/REVIEW_WORKSPACE.md) from an existing package or
local-loader result. One command prepares empty bound answer/link/design templates,
an exact evidence-reference catalog, initial gap reports and next-command argument
arrays. It does not select relevant evidence or generate an answer, link or plan.

## Reassess manually curated evidence

[Manual evidence revision](docs/MANUAL_EVIDENCE_REVISION.md) changes one pinned
observation under unchanged source bytes, records the explicit reason and old/new
claims in a separate audit file, and requires a new version/build. All revised
corpus quotes are checked; scientific correctness and reviewer identity are not.

## Trace evidence-use changes

[Revision impact](docs/REVISION_IMPACT.md) compares old answer/design references
against a revised package, retaining before/after claims, counterarguments and
publication scope. It identifies affected old claims/steps without rebinding them;
same-position correspondence is not semantic identity or scientific validation.

## Compare methods with a new research context

[Applicability review](docs/APPLICABILITY_REVIEW.md) places topic-matched original
research/review observations in time order beside an explicit target context.
Operators record consider/exclude/defer, condition comparisons, uncertainty and
counterevidence; excluded and deferred evidence stays visible. No applicability,
scientific validity or researcher-specific reasoning is inferred.

## Distinguish review context and shared evidence

[Declared publication context](docs/PUBLICATION_CONTEXT.md) connects a review
summary, method extension, reanalysis, shared material, version or challenge to
explicit source references and uncertainty. Add it to timelines or pattern transfer
without changing evidence counts or approval decisions. Later-review and same-year
context remain flagged against the target reference year. Missing relationships
mean unknown, never independent confirmation or a reconstructed change of mind.

## Review tentative method patterns

[Operator pattern hypotheses](docs/PATTERN_HYPOTHESES.md) connect explicitly selected
research/review observations without rewriting their different wording. Original
claims, counterevidence, publication order, rival explanations and missing falsifiers
remain visible. No semantic pattern, distinctive scholar trait or recommendation
is inferred from the evidence inventory.

## Propose method patterns with an offline model

[Model-assisted pattern proposals](docs/PATTERN_PROPOSALS.md) compare the selected
publication/review catalog while preserving conditions, limitations, chronology and
contrary evidence. Imported hypotheses are separate from operator-reviewed
interpretations. All decisions start deferred. An explicit reviewed envelope keeps
original/revised text, rejected proposals and declared model provenance through
existing pattern and context review. Acceptance does not approve a method or create
a design; no model call or external transmission is performed by these tools.
Optional v2 handoffs request a separate rationale and context boundary for each
support/challenge reference. Original and reviewed explanations remain distinct,
and missing boundaries stay visible during new-context review.

## Trace a pattern into a new proposal

[Pattern-to-context review](docs/PATTERN_TRANSFER_REVIEW.md) joins existing manual
pattern, applicability and answer/design artifacts. It exposes unresolved conditions,
missing challenge-role uses and absent falsification criteria without generating or
rebinding any claims. Exact references and enclosing-observation context are distinguished.

For a source-by-source check before selecting a method, use
`review_package.py ... --evidence-details`: exact observation/component references,
individual missing reasoning dimensions and complete candidate-review provenance remain
visible. See [evidence detail walkthrough](docs/EVIDENCE_DETAILS.md). The default
compact rows also preserve the observation's own claim type.
