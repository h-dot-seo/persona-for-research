# Append reviewed source observations without losing imported history

The first-observation proposal workflow intentionally stops at a review packet.
`observation_revision.py` adds a separate, explicit step: append fully reviewed
observations to a **new candidate manifest and runtime package** using pinned local
source files. It never overwrites the input manifest, changes a canonical persona,
replaces an existing observation or infers an approval.

This closes the practical gap between reviewing a model's proposed method and
using that method's evidence in publication chronology, reasoning links, answers,
method-pattern comparison and context review. Imported origin remains attached
through those downstream views instead of being relabeled as manual curation.

## Prerequisites

1. A training-only, authorized, author-matched local manifest from input preparation
   or manual curation, with explicit file paths and source hashes.
2. An observation-proposal bundle made from that exact manifest with `--source-root`.
3. An explicit complete proposal review: no deferred decisions, at least one
   accepted observation, and original source locator/quote unchanged.
4. A new append card selecting every accepted candidate, its exact source paper,
   and the next available observation index. Both version and build ID must change.

Missing condition, limitation or topic values remain valid in a **proposal**. They
cannot become runtime rules until the reviewer explicitly supplies these fields.
The tool never fills them from a nearby source, a generic default or model output.
Filling a field still does not prove that its interpretation is supported. Read
and assess the source; do not add plausible-sounding text merely to pass validation.

This route uses the existing pinned local-file reader. Every source is preflighted
for authorization and paths, and its bytes must match the supplied hash. The whole
resulting corpus is then verified again, including retained observations and quotes.
The reader's documented stability/race assumptions still apply; this is not an OS
sandbox, independent publication acquisition or source-authentication service.

## Explicit local commands

Keep actual inputs and generated artifacts outside this public repository. These
paths are examples for private local files, not supplied real research data:

```sh
python observation_revision.py template ../manifest.json ../observation-bundle.json ../observation-review.json --source-root ../sources --operator-id local-operator > ../append-card.json
```

The card contains bound manifest/bundle/review hashes, an operator declaration,
empty new identity strings and **an empty operations list**. Nothing is selected
or approved. After inspecting the review and current observation counts, fill the
new identity and add one explicit operation per accepted candidate:

```json
{
  "operation": "append",
  "candidate_id": "observation-candidate-1",
  "target_paper_id": "synthetic-0",
  "target_observation_index": 0
}
```

The identifiers above are illustrative synthetic values. Use the exact candidate
ID and its source-paper ID from your own bundle. Indexes are zero-based; append
index must equal the current count for that paper. When appending two observations
to one paper, the second index must account for the first operation. Operation
order is explicit, not a ranking of evidence or a claim about publication order.
Unknown/rejected candidates, duplicate operations, missing accepted candidates,
wrong-paper targets, replacements and reused version/build identities reject.

```sh
python observation_revision.py prepare ../manifest.json ../observation-bundle.json ../observation-review.json ../append-card.json --source-root ../sources > ../observation-candidate.json
python observation_revision.py audit ../manifest.json ../observation-bundle.json ../observation-review.json ../append-card.json ../observation-candidate.json --source-root ../sources > ../observation-append-audit.json
```

The first result contains:

- `manifest`: a detached new manifest with the appended observations and explicit
  new identity. Existing observations and unrelated metadata remain unchanged.
- `package`: the new source-checked runtime candidate. Whole source bodies are not
  copied into it. Stored verification labels describe the checks just performed.
- `review_packet`: original and reviewed text, including rejected challenges and
  every decision. Its own `runtime_package_created: false` describes the prior
  review operation; the outer candidate reports `runtime_package_created: true`.
- `append_audit`: hashes of all inputs/results, exact additions and the initial
  imported-observation inventory whose earlier adoption history was **not** replayed.

The audit command reconstructs the complete candidate from the original inputs and
current pinned source bytes, then requires exact logical JSON equality. A different
self-consistent package is not the same replay. Keep the original inputs for future
replay; a candidate's metadata alone does not prove who reviewed or generated it.

All commands write stdout only. They do not modify files or promote the candidate.
Choose new output paths yourself: shell redirection can overwrite a file if reused.
CLI inputs and the emitted JSON are limited to 8 MiB; reconstructed handoff sources
to 2 MiB total bytes. Oversized output rejects before printing so it can be read by
the same bounded audit CLI. Invalid JSON, stale bindings and validation errors also
produce no partial stdout artifact.

## Durable observation origin

Each appended observation carries `observation_origin`, preserved in both source
knowledge and derived rules. Its recorded origin is
`operator_reviewed_imported_observation`, separate from a manual observation and
from the origin of any reasoning component added later. It records:

- Candidate, source-paper and source-hash identity.
- Original proposed claim/stance labels, original-proposal hash and reviewed-content
  hash. The reviewed hash covers the eight base fields: method, condition,
  limitation, topic, locator, quote, claim type and stance.
- Full handoff/response/proposal-bundle/review/append-card bindings.
- Declared provider/model/run/location, reviewer and append operator.

Provider and operator identities remain unauthenticated. These are consistency
records, not digital signatures or proof of actual AI use. If a trusted caller
constructs a new consistent origin, that is a new declaration, not verified history.
`manifest_observation_sha256` in the additions audit hashes the full appended
manifest observation. It differs from the runtime observation when the latter
adds a current verification label. `reviewed_observation_sha256` intentionally
excludes verification labels, reasoning components and the origin record itself.

Changing any base content without updating its review binding rejects. Moving the
origin to another paper or source hash also rejects. Adding a separately reviewed
reasoning component does not rewrite the base observation's history. The manual
observation revision gate rejects imported observations rather than silently
stripping provenance. This release does **not** add imported-observation replacement
or source migration. Prepare a separately reviewed candidate rather than manually
removing origin fields.

## Downstream use and remaining boundaries

The candidate is accepted by existing read-only package tools because it includes
an explicit `package` member. For example:

```sh
python publication_timeline.py ../observation-candidate.json --topic "model design" --format text
python review_package.py ../observation-candidate.json --question "Which comparison is justified?" --topic "model design" --evidence-details
python pattern_proposals.py prepare ../observation-candidate.json --topic "model design" --include-evidence-reasons > ../pattern-handoff.json
```

Methodological trajectories, planning steps, reasoning cards, endpoint catalogs,
answers, patterns and text reports retain base-observation origin. Evidence-scope
reports distinguish a directly selected imported observation from a manually
curated component whose enclosing observation has imported history. One does not
establish the other's generation provenance.

Reasoning-component lineage/chain audits do **not** replay observation append
history. They list that history separately and show an unreplayed-history status,
including when the reasoning revision itself matches exactly. Initial history
remains unaudited; the new append audit covers one declared append only, not an
arbitrary chain of earlier observations or a whole research career.

No source check establishes semantic support, independent replication, individual
authorship, scientific validity or researcher fidelity. Research/review dates still
order publications, not private decisions. All generated artifacts may contain
private notes, quotes and identifiers; preservation is not anonymization or
permission to publish. Current execution uses no model or network provider.

## Synthetic verification

```sh
python -m unittest tests.test_observation_revision -v
```

Invented publications and canned proposals exercise empty inputs, explicit append
selection, complete review, null gaps, rejected challenges, same-paper indexes,
source changes, altered metadata, exact replay, inherited history, provenance across
downstream tools, manual-edit rejection, JSON aliases and actual CLI execution.
No real researcher material, external model or scientific validation is used.

For supported result commands, prefer `--output NEW_FILE` to shell redirection; see [exclusive output](EXCLUSIVE_OUTPUT.md). Existing shell blocks above remain valid but retain shell overwrite and re-encoding risks.
