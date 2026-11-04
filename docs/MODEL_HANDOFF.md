# Offline model handoff with explicit review

`model_handoff.py` bridges permitted source material to a separately run coding
assistant or model API. It prepares local JSON and checks an imported response.
It never invokes a provider, loads a model, uploads a file, installs software or
spends money. A source's local `authorized: true` flag does not authorize sending
its contents to an external service. Confirm destination, rights, privacy, cost
and retention separately before any such use.

This is a candidate-extraction workflow, not an impersonation prompt or a claim
that a model reproduces a researcher's thoughts. Original research and reviews
retain their source kinds and years. The prompt asks for question framing,
alternative explanations, evidence standards, falsification checks and uncertainty,
with short exact quotations. It asks models to leave unsupported dimensions empty,
retain limitations and counterarguments, and avoid individual-author attribution.
Prompt instructions are not evidence of model quality or injection resistance.

## Prepare locally

Use the existing segment-containing corpus format, outside this public repository.
The included corpus is synthetic. These commands write only stdout:

```sh
python model_handoff.py prepare examples/reasoning-corpus.json > ../handoff.json
python model_handoff.py response-template examples/reasoning-corpus.json ../handoff.json > ../response.json
```

The complete corpus must pass author identity, training split, runtime eligibility,
explicit authorization, segment hashes and quote checks before any export. The
handoff contains documented source metadata and source segments, not prior
observations or unknown private annotation fields. It nevertheless contains source
text and identifiers and is **not** a privacy filter or redistribution clearance.

The handoff's request and instructions are provider-neutral data. After separately
authorized model execution, retain the response object with exactly:

- `handoff_sha256`: the unchanged value in the response template.
- `candidates`: an array matching `request.response_contract` in the handoff.

The template begins empty. Empty results are valid and do not establish absence
of relevant evidence. Each candidate has exactly `paper_id`, `locator`,
`evidence_quote`, `dimension`, `candidate_text` and `proposed_claim_type`. Quotes
must occur verbatim at their exact supplied source locator. The proposed label is
`explicit_statement` or `operator_interpretation`, never an approved author claim.
Do not put provider metadata, approvals or revised bindings in model output.

## Import a response and separate provenance declaration

Create a separate operator-authored JSON declaration with exactly these fields:

```json
{
  "provider_id": "synthetic-provider",
  "model_id": "synthetic-model",
  "run_id": "synthetic-run",
  "operator_id": "synthetic-operator",
  "execution_location": "unknown"
}
```

These values are example labels, not a real execution record. For an actual run,
record its real nonsecret identifiers; do not include API keys, account credentials,
personal addresses or raw provider logs. `execution_location` is `local`, `remote`
or `unknown`. All fields are nonempty strings of at most 128 characters, with no
control characters. The declaration remains unauthenticated operator input.

```sh
python model_handoff.py import corpus.json handoff.json response.json provenance.json > candidates.json
python operator_review.py corpus.json candidates.json --targets
python operator_review.py corpus.json candidates.json --template --reviewer-id reviewer-reference > review.json
```

The importer reconstructs the entire current handoff and rejects changed source,
annotation, version or prompt content. It binds the exact response and separate
provenance into a version-2 candidate bundle, preserves proposed claim labels, and
requires the same explicit [operator review](OPERATOR_REVIEW.md). All decisions
start deferred. Only explicit accepted decisions with exact targets and prior
component hashes can create a separate revision candidate. No canonical adoption
is automatic.

Imported reviewed components carry `operator_reviewed_imported_candidate`, never
`operator_reviewed_mock_candidate`. Their candidate-bundle hash points to the
retained provenance record. Keep the original corpus, handoff, response, provenance,
bundle and review together in authorized storage. Hashes do not authenticate the
model, prove which prompt it saw or show that any model actually ran. A modified
self-consistent declaration is a new artifact requiring a new bound review.

The provider record's `llm_used: null` means earlier model use is not verified.
`inference_performed: false` and `external_transmission: false` describe this local
import only, not the earlier declared execution. Existing mock version-1 bundles
remain separate and unchanged. Reader-scope reports distinguish the two origins.
The lineage/chain audits replay declared mock and imported revisions with distinct
origin inventories and preserved inherited-history warnings. Imported provider/run
declarations are retained with their bundle hashes, never authenticated by replay.
Current audit execution does not invoke a model or establish historical model use.

## Limits and failure behavior

- Maximum source handoff size: 2 MiB of compact logical JSON.
- Maximum input file size for this CLI: 8 MiB per file, read with a bound.
- At most 128 imported candidates, 500 characters per quote and 2,000 per text.
- Unknown fields, duplicate JSON keys, nonfinite values, stale bindings and invalid
  source references fail without a partial stdout result. Nothing is truncated.
- APIs called directly in Python validate logical artifacts; the file-byte limit
  belongs to this CLI. Already allocated Python input objects are not sandboxed.
- These are resource and integrity limits, not copyright limits or semantic checks.

Tests use canned synthetic responses through the import path. No actual provider,
researcher corpus, extraction-quality evaluation or scientific validation has run.
