# First-observation proposals: review without canonical adoption

The reasoning-candidate gate needs an existing observation target. This optional
workflow helps draft the first method observations when selected papers still have
`observations: []`. It produces **review-only proposal packets**, not manual cards,
curated manifests, persona packages or experimental recommendations. No model is
called by these commands; model responses come from a separately authorized run.

It reuses local source loading, authorization/split checks, hash binding, declared
provenance and bounded import. The default `model_handoff.py` reasoning mode is
unchanged. Observation mode is explicit, and the two contracts cannot cross-import.

## Prepare the empty synthetic corpus

```sh
python prepare_local_manifest.py examples/local-selection.json --source-root examples/synthetic-sources > ../prepared-observation-sources.json
python model_handoff.py prepare ../prepared-observation-sources.json --task observations --source-root examples/synthetic-sources > ../observation-handoff.json
python model_handoff.py response-template ../prepared-observation-sources.json ../observation-handoff.json --task observations --source-root examples/synthetic-sources > ../observation-response.json
```

The handoff contains source text. Local permission declarations do not authorize
external transmission. Confirm source rights, destination, privacy, cost and
retention before using it with a provider. Source passages are data, not commands.
The prompt's boundaries are not evidence of prompt-injection resistance.

The response template retains the exact handoff hash and starts with an empty
`candidates` array. An example **synthetic candidate row**, not a real model result:

```json
{
  "paper_id": "synthetic-0",
  "method": "Compare competing models before choosing an observation.",
  "condition": null,
  "limitation": null,
  "topic": "model design",
  "locator": "synthetic section 1",
  "evidence_quote": "Compare competing models",
  "proposed_claim_type": "operator_interpretation",
  "proposed_stance": "support"
}
```

Every candidate requires an explicit method, source ID, locator, exact short quote,
proposed claim label and support/challenge stance. `condition`, `limitation` and
`topic` must be present but may be null. Unsupported information stays missing; it
is never filled from another paper or inferred as an author's private judgment.
No nested reasoning components are proposed in this first-observation mode.

Exact quote matching does **not** establish that the method or its condition,
limitation, stance or classification follows from the quote. `explicit_statement`
is a proposed source-label classification, not proof of individual author ownership.
Original research/review labels and publication years remain supplied metadata.

## Import with a separate provenance declaration

Use the same bounded provider/model/run/operator/execution-location declaration
as the [reasoning handoff](MODEL_HANDOFF.md). These identifiers are unauthenticated;
do not store credentials, account secrets or raw provider logs in them.

```sh
python model_handoff.py import ../prepared-observation-sources.json ../observation-handoff.json ../observation-response.json provenance.json --task observations --source-root examples/synthetic-sources > ../observation-proposals.json
python observation_proposals.py ../prepared-observation-sources.json ../observation-proposals.json --template --reviewer-id reviewer-reference --source-root examples/synthetic-sources > ../observation-review.json
```

All decisions start deferred. Every candidate requires exactly one explicit
`accept`, `reject` or `defer`, with a nonempty review note. `accept` additionally
requires a complete `reviewed_observation` object with these keys:

- method, condition, limitation, topic, locator and evidence_quote.
- claim_type: `explicit_statement` or `operator_interpretation`.
- stance: `support` or `challenge`.

Null condition/limitation/topic values remain permitted and visibly incomplete.
The reviewed locator and quote must equal the original candidate's evidence.
Changed evidence needs a new import. Paper identity is fixed by the candidate.
Reviewers may revise the method, stance and claim label, but the original proposal
is retained beside the reviewed version rather than overwritten. Nothing silently
chooses a target, stance, interpretation, reviewer or acceptance decision.

```sh
python observation_proposals.py ../prepared-observation-sources.json ../observation-proposals.json ../observation-review.json --source-root examples/synthetic-sources > ../reviewed-observation-proposals.json
python observation_proposals.py ../prepared-observation-sources.json ../observation-proposals.json ../observation-review.json --source-root examples/synthetic-sources --format text
```

Both output formats retain every candidate, including rejected and deferred
challenges. Text shows escaped provider/model/run declarations, artifact hashes,
source metadata, proposed/reviewed labels, missing fields and review notes. JSON
retains the full bound declaration. Keep source artifacts and the JSON packet;
text is a readable view, not a signature or independently authenticated provenance.

## Deliberate stopping point

Acceptance means **reviewed proposal**, not acceptance into a persona. Any deferred
decision yields `OBSERVATION_PROPOSAL_REVIEW_INCOMPLETE`; with accepted proposals
and none deferred the result is `OBSERVATION_PROPOSALS_REVIEWED_NOT_CANONICAL`.
All rejected or empty input produces `NO_ACCEPTED_OBSERVATION_PROPOSALS`. Original
proposals are retained in every outcome. Field completeness is not a quality score.

No output is compatible with the manual-card append or reasoning-candidate review
gate, and no runtime package is created. Do not strip provenance to pass it through
manual intake. To create a separate runtime candidate, use the explicit
[reviewed observation append](OBSERVATION_REVISION.md) workflow. It requires pinned
local files, complete review, a new identity and an explicit append card, preserves
observation-level provenance and provides exact append replay. It never promotes a
canonical persona. Current design lineage audits cover **reasoning-component**
revisions and separately disclose unreplayed observation history. Missing origin
markers do not prove manual authorship.

## Bounds and reproducibility

The current 2 MiB logical handoff, 2 MiB combined local raw-source, 8 MiB per JSON
input file, 128-candidate, 500-character quote and 2,000-character text limits apply.
Unsupported keys, wrong task, stale corpus/response/review bindings, altered evidence,
duplicate decisions and invalid labels fail without a partial stdout result.
Nothing is ranked, deduplicated, truncated, promoted or transmitted automatically.

```sh
python -m unittest tests.test_observation_proposals -v
```

Tests use invented local text and canned responses, including empty observations,
accepted missing fields, conflicting labels, rejected challenges and failure paths.
No actual model, researcher corpus, authenticated human review or scientific
validation has been evaluated.
