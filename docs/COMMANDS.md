# Command reference

Every command-line script of this repository, grouped by task. Each entry gives the exact
`usage:` line printed by `python <script>.py --help` (argparse continuation lines joined
with single spaces), the one-line purpose from the script's own description, every
subcommand, and the guide that documents the behaviour. The two publication checks,
`audit_publication.py` and `verify_manifest.py`, use no argparse and print no usage line;
their entries state how they are run instead. Run commands from the repository
root with Python 3.10 or later; only the standard library is used, and no command calls a
model, reads the network or modifies a canonical package. Results go to stdout or to an
explicitly named new path outside the repository (the guides write `OUTPUT` for such a
directory); rejected inputs exit nonzero, and each guide states the exact failure
behaviour, bounds and non-claims of its commands. The shipped `examples/` are entirely
synthetic. The per-feature narrative is in [WORKFLOWS.md](WORKFLOWS.md).

Scripts in alphabetical order: [`answer_draft.py`](#answer_draftpy), [`answer_proposals.py`](#answer_proposalspy), [`applicability_review.py`](#applicability_reviewpy), [`application_proposals.py`](#application_proposalspy), [`argument_map.py`](#argument_mappy), [`argument_proposals.py`](#argument_proposalspy), [`audit_design_chain.py`](#audit_design_chainpy), [`audit_design_lineage.py`](#audit_design_lineagepy), [`audit_publication.py`](#audit_publicationpy), [`citation_reasoning.py`](#citation_reasoningpy), [`compare_releases.py`](#compare_releasespy), [`corpus_files.py`](#corpus_filespy), [`curate_local.py`](#curate_localpy), [`design_scenario.py`](#design_scenariopy), [`evaluate_synthetic.py`](#evaluate_syntheticpy), [`evidence_scope.py`](#evidence_scopepy), [`extraction_adapter.py`](#extraction_adapterpy), [`human_validation.py`](#human_validationpy), [`journey_compare.py`](#journey_comparepy), [`journey_inputs.py`](#journey_inputspy), [`method_application.py`](#method_applicationpy), [`model_handoff.py`](#model_handoffpy), [`observation_input.py`](#observation_inputpy), [`observation_proposals.py`](#observation_proposalspy), [`observation_revision.py`](#observation_revisionpy), [`operator_review.py`](#operator_reviewpy), [`pattern_hypotheses.py`](#pattern_hypothesespy), [`pattern_proposals.py`](#pattern_proposalspy), [`pattern_transfer_review.py`](#pattern_transfer_reviewpy), [`persona.py`](#personapy), [`prepare_local_manifest.py`](#prepare_local_manifestpy), [`publication_context.py`](#publication_contextpy), [`publication_scope.py`](#publication_scopepy), [`publication_timeline.py`](#publication_timelinepy), [`reasoning_links.py`](#reasoning_linkspy), [`research_journey.py`](#research_journeypy), [`research_workflow.py`](#research_workflowpy), [`review_journey.py`](#review_journeypy), [`review_package.py`](#review_packagepy), [`review_workspace.py`](#review_workspacepy), [`revise_local.py`](#revise_localpy), [`revision_impact.py`](#revision_impactpy), [`safe_canonical_read.py`](#safe_canonical_readpy), [`source_recheck.py`](#source_recheckpy), [`synthetic_walkthrough.py`](#synthetic_walkthroughpy), [`topic_inventory.py`](#topic_inventorypy), [`verify_manifest.py`](#verify_manifestpy).

## Start, validate and publish

### `synthetic_walkthrough.py`

Run bundled synthetic fixtures through real CLIs into a new external directory.

```text
usage: synthetic_walkthrough.py [-h] [--candidate-source {mock,offline-import}] [--research-journey] [--recheck-sources] [--review-method-use] [--import-method-use] [--html-review] [--import-answers] [--import-arguments] [--contextual-answers] new_output_directory
```

Guide: [Quickstart](QUICKSTART.md), [Workflows: synthetic walkthrough routes](WORKFLOWS.md#synthetic-walkthrough-routes).

### `persona.py`

Validate mechanical persona release boundaries; never score scholarly fidelity.

```text
usage: persona.py [-h] persona knowledge
```

Guide: [Architecture](ARCHITECTURE.md), [Workflows: build and validate a bound package](WORKFLOWS.md#build-and-validate-a-bound-package).

### `safe_canonical_read.py`

Project canonical JSON into runtime context without holdout identifiers. Read raw JSON from stdin or a file; never mutate canonical input. This helper checks only structured boundaries, not scientific validation.

```text
usage: safe_canonical_read.py [-h] [--source-kind {library-read,original-bytes}] [--expected-original-sha256 EXPECTED_ORIGINAL_SHA256] [input]
```

Guide: [Architecture](ARCHITECTURE.md), [Workflows: build and validate a bound package](WORKFLOWS.md#build-and-validate-a-bound-package).

### `verify_manifest.py`

Verify the exact selected public file inventory and its LF-normalized bytes against PUBLICATION_MANIFEST.json.

```text
python verify_manifest.py    (no argparse and no usage line: takes no arguments, verifies the repository that contains the script, prints a JSON result)
```

Guide: [Public extraction record](../PUBLICATION.md), [Validation record](../VALIDATION.md).

### `audit_publication.py`

Check a deliberately selected public file set for prohibited file types and common secret patterns; not an anonymizer or legal audit.

```text
python audit_publication.py    (no argparse and no usage line: takes no arguments, scans the repository that contains the script, prints a JSON result)
```

Guide: [Security and publication boundary](../SECURITY.md), [Validation record](../VALIDATION.md).

## Intake, local sources and manual curation

### `observation_input.py`

Verify curated observations against explicitly supplied text segments.

```text
usage: observation_input.py [-h] --question QUESTION --topic TOPIC corpus
```

Guide: [Workflows: verified intake and authorized local source files](WORKFLOWS.md#verified-intake-and-authorized-local-source-files), [Workflow review](WORKFLOW_REVIEW.md).

### `research_workflow.py`

Apply operator-curated paper observations as a bounded research planning scaffold.

```text
usage: research_workflow.py [-h] --question QUESTION --topic TOPIC corpus
```

Guide: [Workflows: paper-to-research-plan workflow](WORKFLOWS.md#paper-to-research-plan-workflow), [Workflow review](WORKFLOW_REVIEW.md).

### `prepare_local_manifest.py`

Prepare hashes and section inventory for explicitly selected local training files.

```text
usage: prepare_local_manifest.py [-h] --source-root SOURCE_ROOT selection
```

Guide: [Local input preparation](LOCAL_INPUT_PREPARATION.md).

### `corpus_files.py`

Load explicitly authorized local UTF-8 Markdown evidence with byte hashes.

```text
usage: corpus_files.py [-h] --source-root SOURCE_ROOT --question QUESTION --topic TOPIC manifest
```

Guide: [Local input preparation](LOCAL_INPUT_PREPARATION.md), [Workflows: verified intake and authorized local source files](WORKFLOWS.md#verified-intake-and-authorized-local-source-files).

### `curate_local.py`

Append one explicitly authored observation to a pinned local manifest.

```text
usage: curate_local.py [-h] {template,append} ...
usage: curate_local.py template [-h] --paper PAPER manifest
usage: curate_local.py append [-h] --source-root SOURCE_ROOT manifest card
```

Subcommands:

- `template` — Write an empty observation card for one paper of a pinned local manifest.
- `append` — Append one explicitly authored card after checking every current local quote; writes the new manifest to stdout.

Guide: [Manual local observations](MANUAL_LOCAL_OBSERVATIONS.md).

### `revise_local.py`

Revise one manual observation against unchanged local source bytes, with an audit artifact.

```text
usage: revise_local.py [-h] {template,apply} ...
usage: revise_local.py template [-h] --paper PAPER --observation-index OBSERVATION_INDEX manifest
usage: revise_local.py apply [-h] --source-root SOURCE_ROOT manifest card destination
```

Subcommands:

- `template` — Write a revision card for one pinned observation of a manifest.
- `apply` — Apply the revision under unchanged source bytes into a new destination folder, with an audit artifact.

Guide: [Manual evidence revision](MANUAL_EVIDENCE_REVISION.md).

### `revision_impact.py`

Trace old answer/design evidence uses across two bound packages without rebinding.

```text
usage: revision_impact.py [-h] --reference-year REFERENCE_YEAR [--format {json,text}] previous current links proposal draft
```

Guide: [Revision impact](REVISION_IMPACT.md).

### `source_recheck.py`

Recheck every supplied source file and stored quote without changing a package.

```text
usage: source_recheck.py [-h] [--template] [--operator-id OPERATOR_ID] [--source-root SOURCE_ROOT] [--format {json,text}] package [selection]
```

Guide: [Source recheck](SOURCE_RECHECK.md).

### `topic_inventory.py`

Discover existing exact-topic scopes without semantic merging or ranking.

```text
usage: topic_inventory.py [-h] [--format {json,text}] package
```

Guide: [Topic discovery](TOPIC_DISCOVERY.md).

## Release review and validation axes

### `review_package.py`

Render a compact read-only review from a validated bound scholarly package.

```text
usage: review_package.py [-h] --question QUESTION --topic TOPIC [--evidence-details] [--human-validation HUMAN_VALIDATION] package
```

Guide: [Evidence details](EVIDENCE_DETAILS.md), [Human validation](HUMAN_VALIDATION.md), [Workflows: review a candidate release and a bound package](WORKFLOWS.md#review-a-candidate-release-and-a-bound-package).

### `compare_releases.py`

Read-only comparison of bound evidence packages; never update canonical policy.

```text
usage: compare_releases.py [-h] previous candidate
```

Guide: [Workflows: review a candidate release and a bound package](WORKFLOWS.md#review-a-candidate-release-and-a-bound-package), [Workflow review](WORKFLOW_REVIEW.md).

### `human_validation.py`

Record and check a detached human validation assessment bound to one persona package.

```text
usage: human_validation.py [-h] {template,check,status} ...
usage: human_validation.py template [-h] --output OUTPUT persona [knowledge]
usage: human_validation.py check [-h] [--text] record persona [knowledge]
usage: human_validation.py status [-h] [--human-validation HUMAN_VALIDATION] [--text] persona [knowledge]
```

Subcommands:

- `template` — Write a blank record bound to the package; never overwrites.
- `check` — Strictly validate a record against the package and derive CURRENT_PACKAGE or STALE_PACKAGE.
- `status` — Read-only axis report; NOT_PERFORMED without records.

Guide: [Human validation](HUMAN_VALIDATION.md).

### `evaluate_synthetic.py`

Freeze synthetic answer metadata, then compare separately supplied holdout labels.

```text
usage: evaluate_synthetic.py [-h] {freeze,evaluate} ...
usage: evaluate_synthetic.py freeze [-h] package draft
usage: evaluate_synthetic.py evaluate [-h] submission holdout_labels
```

Subcommands:

- `freeze` — Capture validated answer/citation metadata without reading any labels.
- `evaluate` — Measure exact agreement between a frozen submission and explicit synthetic holdout-role labels.

Guide: [Synthetic evaluation](SYNTHETIC_EVALUATION.md).

## Candidate proposals from a mock or an offline model, and operator review

### `extraction_adapter.py`

Bounded extraction candidates from a mock or declared offline model response.

```text
usage: extraction_adapter.py [-h] --mock-response MOCK_RESPONSE corpus
```

Guide: [Extraction contract](EXTRACTION_CONTRACT.md).

### `model_handoff.py`

Prepare or import a local model handoff without invoking or transmitting to a model.

```text
usage: model_handoff.py [-h] {prepare,response-template,import} ...
usage: model_handoff.py prepare [-h] [--task {reasoning,observations}] [--source-root SOURCE_ROOT] corpus
usage: model_handoff.py response-template [-h] [--task {reasoning,observations}] [--source-root SOURCE_ROOT] corpus handoff
usage: model_handoff.py import [-h] [--task {reasoning,observations}] [--source-root SOURCE_ROOT] corpus handoff response provenance
```

Subcommands:

- `prepare` — Export source-containing local request JSON.
- `response-template` — Prepare an empty response bound to the current handoff.
- `import` — Check a bound response and separate declared provenance.

Guide: [Model handoff](MODEL_HANDOFF.md).

### `observation_proposals.py`

Import and review first-observation proposals without creating runtime records.

```text
usage: observation_proposals.py [-h] [--template] [--reviewer-id REVIEWER_ID] [--source-root SOURCE_ROOT] [--format {json,text}] corpus bundle [review]
```

Guide: [Observation proposals](OBSERVATION_PROPOSALS.md).

### `observation_revision.py`

Append explicitly reviewed imported observations to a separate local candidate.

```text
usage: observation_revision.py [-h] {template,prepare,audit} ...
usage: observation_revision.py template [-h] --operator-id OPERATOR_ID --source-root SOURCE_ROOT manifest bundle review
usage: observation_revision.py prepare [-h] --source-root SOURCE_ROOT manifest bundle review card
usage: observation_revision.py audit [-h] --source-root SOURCE_ROOT manifest bundle review card candidate
```

Subcommands:

- `template` — Write an empty append card bound to the manifest, proposal bundle and review.
- `prepare` — Build the separate candidate manifest from the reviewed proposals named in the card.
- `audit` — Reconstruct the candidate from its inputs and report the append audit.

Guide: [Observation revision](OBSERVATION_REVISION.md).

### `operator_review.py`

Apply declared operator decisions to a separate, hash-bound revision candidate.

```text
usage: operator_review.py [-h] [--new-version NEW_VERSION] [--new-build-id NEW_BUILD_ID] [--template | --targets] [--reviewer-id REVIEWER_ID] [--source-root SOURCE_ROOT] corpus candidates [review]
```

Guide: [Operator review](OPERATOR_REVIEW.md).

### `audit_design_lineage.py`

Replay one declared candidate-review revision and trace a design's evidence routes.

```text
usage: audit_design_lineage.py [-h] package links proposal revision_inputs
```

Guide: [Design lineage](DESIGN_LINEAGE.md).

### `audit_design_chain.py`

Replay an explicitly supplied linear chain of candidate-review revisions.

```text
usage: audit_design_chain.py [-h] package links proposal chain
```

Guide: [Design chain](DESIGN_CHAIN.md).

## Timelines, links, designs and publication scope

### `publication_timeline.py`

Review publication-dated question and method records, without career inference.

```text
usage: publication_timeline.py [-h] --topic TOPIC [--format {json,text}] [--publication-relations PUBLICATION_RELATIONS] package
```

Guide: [Publication timeline](PUBLICATION_TIMELINE.md).

### `reasoning_links.py`

Review explicitly supplied cross-publication links, never infer author reasoning.

```text
usage: reasoning_links.py [-h] [--template] [--operator-id OPERATOR_ID] [--format {json,text}] package [links]
```

Guide: [Reasoning links](REASONING_LINKS.md).

### `design_scenario.py`

Trace an operator's proposed design to supplied reasoning links, without inference.

```text
usage: design_scenario.py [-h] [--template] [--question QUESTION] [--operator-id OPERATOR_ID] [--format {json,text}] package links [proposal]
```

Guide: [Design scenario](DESIGN_SCENARIO.md).

### `publication_scope.py`

Audit publication-year scope of an operator proposal without historical inference.

```text
usage: publication_scope.py [-h] --reference-year REFERENCE_YEAR [--format {json,text}] package links proposal
```

Guide: [Publication scope](PUBLICATION_SCOPE.md).

### `publication_context.py`

Inspect declared publication relationships without inferring influence or independence.

```text
usage: publication_context.py [-h] [--template] [--operator-id OPERATOR_ID] [--format {json,text}] package [form]
```

Guide: [Publication context](PUBLICATION_CONTEXT.md).

## Answers, citations and arguments

### `review_workspace.py`

Create a new local review workspace with empty operator-authored artifacts.

```text
usage: review_workspace.py [-h] --question QUESTION --operator-id OPERATOR_ID --reference-year REFERENCE_YEAR [--journey-topic JOURNEY_TOPIC] [--target-context TARGET_CONTEXT] package destination
```

Guide: [Review workspace](REVIEW_WORKSPACE.md), [Integrated workspace](INTEGRATED_WORKSPACE.md).

### `answer_draft.py`

Inspect evidence-bound answer drafts and declared reviews, without generating answers.

```text
usage: answer_draft.py [-h] [--template | --review-template | --review REVIEW] [--question QUESTION] [--operator-id OPERATOR_ID] [--reviewer-id REVIEWER_ID] [--format {json,text}] package [draft]
```

Guide: [Answer draft](ANSWER_DRAFT.md), [Citation explanations](CITATION_EXPLANATIONS.md).

### `review_journey.py`

Join answer and design reviews by exact evidence reference, never semantic inference.

```text
usage: review_journey.py [-h] --reference-year REFERENCE_YEAR [--review REVIEW] [--format {json,text}] package links proposal draft
```

Guide: [Review journey](REVIEW_JOURNEY.md).

### `evidence_scope.py`

Disclose actual answer/design evidence scope without scoring researcher fidelity.

```text
usage: evidence_scope.py [-h] --reference-year REFERENCE_YEAR [--review REVIEW] [--format {json,text}] package links proposal draft
```

Guide: [Evidence scope](EVIDENCE_SCOPE.md).

### `citation_reasoning.py`

Explicit, offline inventory of declared reasoning for each current citation use.

```text
usage: citation_reasoning.py [-h] [--review REVIEW] [--format {json,text}] package draft
```

Guide: [Citation reasoning audit](CITATION_REASONING_AUDIT.md).

### `answer_proposals.py`

Prepare and explicitly review offline, evidence-scoped answer proposals.

```text
usage: answer_proposals.py [-h] {template,prepare,response-template,import,review-template,review,export,inspect,context} ...
usage: answer_proposals.py template [-h] --question QUESTION --topic TOPIC --operator-id OPERATOR_ID --reference-year REFERENCE_YEAR [--include-citation-explanations] [--patterns PATTERNS] [--context CONTEXT] [--publication-relations PUBLICATION_RELATIONS] [--pattern-id PATTERN_ID] package
usage: answer_proposals.py prepare [-h] package scope
usage: answer_proposals.py response-template [-h] package scope handoff
usage: answer_proposals.py import [-h] package scope handoff response provenance
usage: answer_proposals.py review-template [-h] --reviewer-id REVIEWER_ID package bundle
usage: answer_proposals.py review [-h] [--format {json,text}] package bundle review
usage: answer_proposals.py export [-h] package bundle review
usage: answer_proposals.py inspect [-h] package envelope
usage: answer_proposals.py context [-h] [--source-selection SOURCE_SELECTION] [--source-root SOURCE_ROOT] [--format {json,text}] package scope
```

Subcommands:

- `template` — Write an empty evidence-scope form for one question, topic, reference year and operator; optional v2 citation explanations and v3 pattern/context/publication-relation context.
- `prepare` — Prepare the offline handoff request from a validated scope; no provider is called.
- `response-template` — Write an empty response bound to the handoff, to be filled by a separately authorized tool.
- `import` — Import a separately produced response with its declared provenance into a candidate bundle; decisions are not imported.
- `review-template` — Write an all-deferred adoption review for a candidate bundle.
- `review` — Inspect a bundle together with its explicit adoption decisions (JSON or text).
- `export` — Export the complete-history answer draft from a reviewed bundle for the separate answer review.
- `inspect` — Inspect an exported envelope and its candidate history.
- `context` — Read the exact selected passages and recorded context of a scope before preparing a handoff; optional current local source checks.

Guide: [Answer proposals](ANSWER_PROPOSALS.md), [Answer context](ANSWER_CONTEXT.md).

### `argument_map.py`

Review operator-declared premise/conclusion steps without reconstructing private reasoning.

```text
usage: argument_map.py [-h] [--review REVIEW] [--template] [--operator-id OPERATOR_ID] [--step-id STEP_ID] [--format {json,text}] package draft [map]
```

Guide: [Argument map](ARGUMENT_MAP.md).

### `argument_proposals.py`

Prepare and explicitly adopt offline argument suggestions among selected existing claims.

```text
usage: argument_proposals.py [-h] {template,prepare,response-template,import,review-template,review,export,inspect} ...
usage: argument_proposals.py template [-h] [--answer-review ANSWER_REVIEW] --operator-id OPERATOR_ID [--include-recorded-answer-context] package draft
usage: argument_proposals.py prepare [-h] [--answer-review ANSWER_REVIEW] package draft scope
usage: argument_proposals.py response-template [-h] [--answer-review ANSWER_REVIEW] package draft scope handoff
usage: argument_proposals.py import [-h] [--answer-review ANSWER_REVIEW] package draft scope handoff response provenance
usage: argument_proposals.py review-template [-h] [--answer-review ANSWER_REVIEW] --reviewer-id REVIEWER_ID package draft bundle
usage: argument_proposals.py review [-h] [--answer-review ANSWER_REVIEW] [--format {json,text}] package draft bundle review
usage: argument_proposals.py export [-h] [--answer-review ANSWER_REVIEW] package draft bundle review
usage: argument_proposals.py inspect [-h] [--answer-review ANSWER_REVIEW] package draft envelope
```

Subcommands:

- `template` — Write an empty claim-selection scope over existing answer claims; optionally include the recorded answer context.
- `prepare` — Prepare the offline handoff over the selected claims; no provider is called.
- `response-template` — Write an empty response bound to the handoff.
- `import` — Import a response with its declared provenance into a candidate bundle.
- `review-template` — Write an all-deferred adoption review for the bundle.
- `review` — Inspect the bundle together with its explicit adoption decisions (JSON or text).
- `export` — Export the full-history argument map from a reviewed bundle.
- `inspect` — Inspect an exported argument envelope and its candidate history.

Guide: [Argument proposals](ARGUMENT_PROPOSALS.md).

## Method patterns, context and applicability

### `applicability_review.py`

Record operator comparisons of source conditions with a new research context.

```text
usage: applicability_review.py [-h] [--template] [--question QUESTION] [--target-context TARGET_CONTEXT] [--topic TOPIC] [--reference-year REFERENCE_YEAR] [--operator-id OPERATOR_ID] [--format {json,text}] package [form]
```

Guide: [Applicability review](APPLICABILITY_REVIEW.md).

### `pattern_hypotheses.py`

Review explicitly proposed cross-publication method patterns, never discover them.

```text
usage: pattern_hypotheses.py [-h] [--template] [--operator-id OPERATOR_ID] [--format {json,text}] package [form]
```

Guide: [Pattern hypotheses](PATTERN_HYPOTHESES.md).

### `pattern_proposals.py`

Prepare, import and explicitly review offline cross-publication method hypotheses.

```text
usage: pattern_proposals.py [-h] {prepare,response-template,import,review-template,review,export} ...
usage: pattern_proposals.py prepare [-h] --topic TOPIC [--include-evidence-reasons] package
usage: pattern_proposals.py response-template [-h] package handoff
usage: pattern_proposals.py import [-h] package handoff response provenance
usage: pattern_proposals.py review-template [-h] --reviewer-id REVIEWER_ID package bundle
usage: pattern_proposals.py review [-h] [--format {json,text}] package bundle review
usage: pattern_proposals.py export [-h] package bundle review
```

Subcommands:

- `prepare` — Prepare a topic-bound catalog handoff; --include-evidence-reasons requests the v2 contract.
- `response-template` — Write an empty response bound to the handoff.
- `import` — Import a response with its declared provenance into a candidate bundle.
- `review-template` — Write an all-deferred review for the bundle.
- `review` — Inspect the bundle together with its explicit review decisions (JSON or text).
- `export` — Export the reviewed pattern envelope for pattern_hypotheses.py and pattern_transfer_review.py.

Guide: [Pattern proposals](PATTERN_PROPOSALS.md).

### `pattern_transfer_review.py`

Join one explicitly selected pattern with context review and answer/design evidence uses.

```text
usage: pattern_transfer_review.py [-h] --pattern-id PATTERN_ID [--format {json,text}] [--publication-relations PUBLICATION_RELATIONS] [--review REVIEW] package patterns context links proposal draft
```

Guide: [Pattern transfer review](PATTERN_TRANSFER_REVIEW.md).

### `method_application.py`

Review explicit method-pattern application to design steps, never infer adoption.

```text
usage: method_application.py [-h] --pattern-id PATTERN_ID [--template] [--operator-id OPERATOR_ID] [--format {json,text}] package patterns context links proposal [form]
```

Guide: [Method application](METHOD_APPLICATION.md).

### `application_proposals.py`

Prepare and explicitly review offline method-application proposals, without applying them.

```text
usage: application_proposals.py [-h] {prepare,response-template,import,review-template,review,export} ...
usage: application_proposals.py prepare [-h] --pattern-id PATTERN_ID package patterns context links proposal
usage: application_proposals.py response-template [-h] --pattern-id PATTERN_ID package patterns context links proposal handoff
usage: application_proposals.py import [-h] --pattern-id PATTERN_ID package patterns context links proposal handoff response provenance
usage: application_proposals.py review-template [-h] --pattern-id PATTERN_ID --reviewer-id REVIEWER_ID package patterns context links proposal bundle
usage: application_proposals.py review [-h] --pattern-id PATTERN_ID [--format {json,text}] package patterns context links proposal bundle review
usage: application_proposals.py export [-h] --pattern-id PATTERN_ID package patterns context links proposal bundle review
```

Subcommands:

- `prepare` — Prepare the offline handoff for applying one selected pattern to the design steps.
- `response-template` — Write an empty response bound to the handoff.
- `import` — Import a response with its declared provenance into a candidate bundle.
- `review-template` — Write an all-deferred review for the bundle.
- `review` — Inspect the bundle together with its explicit review decisions (JSON or text).
- `export` — Export the reviewed method-application form for method_application.py.

Guide: [Application proposals](APPLICATION_PROPOSALS.md).

## Integrated journeys

### `research_journey.py`

Inspect a source-to-method-to-argument journey without generating or approving research.

```text
usage: research_journey.py [-h] --pattern-id PATTERN_ID [--review REVIEW] [--source-selection SOURCE_SELECTION] [--source-root SOURCE_ROOT] [--method-applications METHOD_APPLICATIONS] [--format {json,text,html}] package patterns context links proposal draft argument publication_relations
```

Guide: [Research journey](RESEARCH_JOURNEY.md), [Local HTML review](LOCAL_HTML_REVIEW.md).

### `journey_inputs.py`

Bind explicit local JSON inputs, then rerun a research journey without rebinding changes.

```text
usage: journey_inputs.py [-h] {template,prepare,inspect} ...
usage: journey_inputs.py template [-h]
usage: journey_inputs.py prepare [-h] --input-root INPUT_ROOT [--source-root SOURCE_ROOT] input
usage: journey_inputs.py inspect [-h] --input-root INPUT_ROOT [--source-root SOURCE_ROOT] [--format {json,text,html}] input
```

Subcommands:

- `template` — Write an empty input-selection form.
- `prepare` — Bind explicit relative JSON inputs into a card with raw-byte and logical payload hashes.
- `inspect` — Reopen the complete journey from a card and an explicit input root (JSON, text or HTML).

Guide: [Journey inputs](JOURNEY_INPUTS.md).

### `journey_compare.py`

Compare two freshly reopened input cards without inferring research progress or approval.

```text
usage: journey_compare.py [-h] --previous-root PREVIOUS_ROOT --current-root CURRENT_ROOT [--previous-source-root PREVIOUS_SOURCE_ROOT] [--current-source-root CURRENT_SOURCE_ROOT] [--format {json,text}] previous current
```

Guide: [Journey comparison](JOURNEY_COMPARISON.md).

## Library modules without a command line

These modules are imported by the scripts above and have no `__main__` entry point; their first docstring line states their boundary.

- `answer_context.py` — Inspect explicit research context before an answer, without selecting citation sources (used by `answer_proposals.py context` and the v3 preparation route).
- `corpus_projection.py` — Project only documented runtime fields; not an anonymizer or access control.
- `declared_provenance.py` — Validate bounded declared model identity without authenticating it.
- `evidence_coverage.py` — Descriptive coverage counts, never confidence or a readiness decision.
- `journey_html.py` — Read-only local HTML navigation over one freshly inspected research journey.
- `methodology_trajectory.py` — Describe curated publication chronology, never a researcher's private beliefs.
- `observation_provenance.py` — Validate and display declared imported-observation history, not its authenticity.
- `reasoning_cards.py` — Validate operator-curated reasoning components without inventing missing content.
- `strict_json.py` — Reject ambiguous keys and non-finite numbers at JSON input boundaries.
- `verification_receipt.py` — In-process check receipt, not a signature or a Python security boundary.

The `test_*.py` modules are the unittest suite run by `python -m unittest discover`; see [../VALIDATION.md](../VALIDATION.md) for the current verification snapshot.
