# persona-for-research

공개 학술 근거의 범위 안에서 연구자 페르소나를 구축·검증·활용하는 프레임워크입니다.
Evidence-bounded scholarly simulations, with explicit provenance and holdout isolation.

한국어 안내: [docs/README.ko.md](docs/README.ko.md)

**A persona is a scholarly simulation, not the researcher.** Private beliefs,
unpublished opinions, personal memories and private communications are outside scope.
No actual researcher persona, article corpus, knowledge database or validation scores
are included in this repository.

## Purpose and scope

The tools build, validate and consult a simulation of one scholar's **published**
reasoning. Every observation is curated by an operator and bound to an authorized
source, locator, quote and hash; the validators check that binding, not whether a
source exists, supports a claim or may be redistributed. Published here are framework
concepts, standard-library Python CLIs, synthetic examples, tests, empty record
templates, agent instructions and publication checks ([PUBLICATION.md](PUBLICATION.md));
source corpora, real persona packages and real validation results are kept out.

- Generalized construction lifecycle and separate evidence/predictive/human/runtime validation axes.
- Logical JSON binding validator (`persona.py`) and a holdout-redacting projection helper (`safe_canonical_read.py`).
- Detached human validation records (`human_validation.py`): a blank template, a strict check and a read-only axis status bound to both package hashes, never written into the persona payload.
- Read-only whole-selection structural reports (`prepare_local_manifest.py --report-defects`) before local preparation.
- Lossless, ASCII-escaped pasteable handoff views with `prepare --format text`; JSON bindings and imports stay unchanged.
- Synthetic templates and tests; a portable agent workflow in `SKILL.md`.
- A `tests/` package for the unittest suite and a root dispatcher, `persona_cli.py`, that lists and runs the root CLIs without changing them.

This is a framework and mechanical tool release. It is not a trained model, a complete
corpus harvester, a turnkey multi-agent runtime, or proof of scholarly validity.

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

The optional flags `--recheck-sources`, `--review-method-use`, `--import-method-use`,
`--html-review`, `--import-answers`, `--import-arguments` and `--contextual-answers`
extend the same demo to between 30 and 53 stages. Each is explained, with what to
read first, in [docs/WORKFLOWS.md](docs/WORKFLOWS.md#synthetic-walkthrough-routes) and
the [quickstart](docs/QUICKSTART.md). No route calls a model, and every final answer
judgment stays deferred.

## Quick start

Python 3.10+, standard library only:

```sh
python3 persona.py examples/persona.json examples/knowledge.json
python3 safe_canonical_read.py examples/persona.json
python3 -m unittest discover -v
```

The synthetic example has no learned rules and no papers. Passing means its
mechanical bindings are consistent, not that any real persona has been validated.
Keep real inputs and generated packages outside this public repository.

## Commands at a glance

| Command | Purpose | Reference |
|---|---|---|
| `synthetic_walkthrough.py` | Run the bundled synthetic fixtures through 15 to 53 real CLI stages into a new external directory | [Quickstart](docs/QUICKSTART.md) |
| `persona.py`, `safe_canonical_read.py` | Validate persona/knowledge hash bindings; project canonical JSON without holdout identifiers | [Architecture](docs/ARCHITECTURE.md) |
| `observation_input.py` | Verify curated observations and quotes against supplied segments, then build the planning scaffold | [Workflows](docs/WORKFLOWS.md#verified-intake-and-authorized-local-source-files) |
| `prepare_local_manifest.py`, `corpus_files.py` | Report structural defects with `--report-defects`, then prepare and load authorized local files with byte hashes | [Local input preparation](docs/LOCAL_INPUT_PREPARATION.md) |
| `research_workflow.py` | Apply operator-curated observations as a bounded, question-specific planning scaffold | [Workflow review](docs/WORKFLOW_REVIEW.md) |
| `review_package.py` | Compact read-only review of a bound package (`--evidence-details`, `--human-validation`) | [Evidence details](docs/EVIDENCE_DETAILS.md) |
| `compare_releases.py` | Read-only comparison of two bound packages; never approves a release | [Workflows](docs/WORKFLOWS.md#review-a-candidate-release-and-a-bound-package) |
| `human_validation.py` | Detached rater assessment bound to both package hashes: `template`, `check`, `status` | [Human validation](docs/HUMAN_VALIDATION.md) |
| `extraction_adapter.py`, `model_handoff.py` | Mock-only extraction contract; offline handoff and import of a separately produced response | [Model handoff](docs/MODEL_HANDOFF.md) |
| `operator_review.py` | Record explicit operator decisions into a separate revision candidate | [Operator review](docs/OPERATOR_REVIEW.md) |
| `answer_proposals.py`, `argument_proposals.py` | Offline, evidence-scoped answer and argument proposals with explicit adoption | [Answer proposals](docs/ANSWER_PROPOSALS.md) |
| `research_journey.py`, `journey_inputs.py` | Integrated source-to-method-to-argument report (JSON/text/HTML) and pinned input cards | [Research journey](docs/RESEARCH_JOURNEY.md) |
| `persona_cli.py` | Discover the root scripts (`list`) and run one in-process from any directory (`run <script> [args...]`); the `python <script>.py` form stays primary | [Commands](docs/COMMANDS.md#persona_clipy) |

Every script and subcommand, with its exact usage line, is listed in
[docs/COMMANDS.md](docs/COMMANDS.md); the per-feature narrative with its limits and
boundaries is in [docs/WORKFLOWS.md](docs/WORKFLOWS.md).

Layout: every script is a flat file at the repository root, and `python persona_cli.py list`
prints the ones with a command-line entry point. The unittest suite is the `tests/` package:
`python -m unittest discover` from the root runs it, and one module runs as
`python -m unittest tests.test_<name> -v`.

## Documentation

**Start and overview**

- [Quickstart](docs/QUICKSTART.md) — run, read and recover the synthetic journey.
- [Workflows](docs/WORKFLOWS.md) — documented behaviour grouped by task.
- [Commands](docs/COMMANDS.md) — every script and subcommand with its usage line.
- [한국어 안내](docs/README.ko.md) — purpose, scope, quick start and index in Korean.
- [Architecture](docs/ARCHITECTURE.md) — lifecycle, validation axes, runtime contract.
- [Workflow review](docs/WORKFLOW_REVIEW.md) — CLI round-trip and evaluation boundary.
- [Validation history](docs/VALIDATION_HISTORY.md) — every dated verification entry.

**Sources, intake and manual curation**

- [Local input preparation](docs/LOCAL_INPUT_PREPARATION.md) — hashes and section inventory for selected files.
- [Manual local observations](docs/MANUAL_LOCAL_OBSERVATIONS.md) — one source-bound observation card at a time.
- [Manual evidence revision](docs/MANUAL_EVIDENCE_REVISION.md) — revise one observation with an audit file.
- [Revision impact](docs/REVISION_IMPACT.md) — which old evidence uses a revision affects.
- [Source recheck](docs/SOURCE_RECHECK.md) — current local bytes and stored quotes.
- [Topic discovery](docs/TOPIC_DISCOVERY.md) — exact-topic scopes before review.
- [Evidence details](docs/EVIDENCE_DETAILS.md) — source-by-source check before selecting a method.

**Candidates, provenance and operator review**

- [Extraction contract](docs/EXTRACTION_CONTRACT.md) — mock-only request/response contract.
- [Model handoff](docs/MODEL_HANDOFF.md) — offline handoff and import of a saved response.
- [Observation proposals](docs/OBSERVATION_PROPOSALS.md) — first-observation proposals, review only.
- [Observation revision](docs/OBSERVATION_REVISION.md) — append reviewed observations to a candidate.
- [Operator review](docs/OPERATOR_REVIEW.md) — recorded decisions into a revision candidate.
- [Design lineage](docs/DESIGN_LINEAGE.md) — replay one candidate-review revision.
- [Design chain](docs/DESIGN_CHAIN.md) — audit consecutive revisions.

**Answers, designs and arguments**

- [Review workspace](docs/REVIEW_WORKSPACE.md) — empty bound answer/link/design templates.
- [Answer draft](docs/ANSWER_DRAFT.md) — evidence-bound claims and per-claim review.
- [Answer proposals](docs/ANSWER_PROPOSALS.md) — offline answer candidates, explicit adoption.
- [Answer context](docs/ANSWER_CONTEXT.md) — method/publication context before proposals.
- [Citation explanations](docs/CITATION_EXPLANATIONS.md) — why one passage is cited for one claim.
- [Citation reasoning audit](docs/CITATION_REASONING_AUDIT.md) — explanation states in old records.
- [Argument map](docs/ARGUMENT_MAP.md) — declared premise-to-conclusion steps.
- [Argument proposals](docs/ARGUMENT_PROPOSALS.md) — offline bridge suggestions, explicit adoption.
- [Design scenario](docs/DESIGN_SCENARIO.md) — proposed design traced to reasoning links.
- [Reasoning links](docs/REASONING_LINKS.md) — operator links between observations.
- [Publication scope](docs/PUBLICATION_SCOPE.md) — publication-year scope of a proposal.
- [Review journey](docs/REVIEW_JOURNEY.md) — one packet for answer and design review.
- [Evidence scope](docs/EVIDENCE_SCOPE.md) — reader disclosure of actual evidence scope.
- [Synthetic evaluation](docs/SYNTHETIC_EVALUATION.md) — frozen answer versus holdout labels.

**Patterns, context and timelines**

- [Pattern hypotheses](docs/PATTERN_HYPOTHESES.md) — operator method patterns across publications.
- [Pattern proposals](docs/PATTERN_PROPOSALS.md) — model-assisted patterns, explicit review.
- [Applicability review](docs/APPLICABILITY_REVIEW.md) — source conditions beside a new context.
- [Publication context](docs/PUBLICATION_CONTEXT.md) — declared relationships between publications.
- [Pattern transfer review](docs/PATTERN_TRANSFER_REVIEW.md) — a pattern traced into a new proposal.
- [Method application](docs/METHOD_APPLICATION.md) — declared pattern use for design steps.
- [Application proposals](docs/APPLICATION_PROPOSALS.md) — offline application proposals, explicit review.
- [Publication timeline](docs/PUBLICATION_TIMELINE.md) — questions, methods and evidence by year.

**Integrated journeys**

- [Research journey](docs/RESEARCH_JOURNEY.md) — source-to-method-to-argument report.
- [Local HTML review](docs/LOCAL_HTML_REVIEW.md) — passive read-only HTML view.
- [Journey inputs](docs/JOURNEY_INPUTS.md) — pin and reopen explicit input files.
- [Journey comparison](docs/JOURNEY_COMPARISON.md) — compare two pinned journeys.
- [Integrated workspace](docs/INTEGRATED_WORKSPACE.md) — starter with empty pattern/context/argument forms.

**Validation and worked examples**

- [Human validation](docs/HUMAN_VALIDATION.md) — detached rater record bound to package hashes.
- [Review attribution example](docs/REVIEW_ATTRIBUTION_EXAMPLE.md) — reported method versus own recommendation.
- [Trajectory and conditions example](docs/TRAJECTORY_CONDITIONS_EXAMPLE.md) — publication change versus changed conditions.

## Design and boundaries

See [lifecycle](docs/ARCHITECTURE.md), [workflow](SKILL.md),
[publication boundary](PUBLICATION.md) and [security](SECURITY.md). The
[validation record](VALIDATION.md) is the current verification snapshot; every dated
entry is in [docs/VALIDATION_HISTORY.md](docs/VALIDATION_HISTORY.md).
No license has been selected by the owner yet; see [rights](RIGHTS.md).

See [local input preparation](docs/LOCAL_INPUT_PREPARATION.md) for converter-neutral text requirements and bounded defect reports.

See [pasteable offline handoffs](docs/MODEL_HANDOFF.md#pasteable-local-handoff-view) for separately authorized assistants.
