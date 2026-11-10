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

## Use verified local files without copying their text into JSON

The same commands accept `--source-root` when the first argument is a local-file
manifest rather than a segment-containing corpus:

```sh
python model_handoff.py prepare examples/file-corpus.json --source-root examples/synthetic-sources > ../local-handoff.json
python model_handoff.py response-template examples/file-corpus.json ../local-handoff.json --source-root examples/synthetic-sources > ../local-response.json
python model_handoff.py import manifest.json handoff.json response.json provenance.json --source-root permitted-source-folder > candidates.json
python operator_review.py manifest.json candidates.json --targets --source-root permitted-source-folder
python operator_review.py manifest.json candidates.json --template --reviewer-id reviewer-reference --source-root permitted-source-folder > review.json
python operator_review.py manifest.json candidates.json review.json --new-version 2 --new-build-id reviewed-candidate --source-root permitted-source-folder
```

The first two commands use existing synthetic files. Their source locators differ
from the inline mock fixture; a response must cite the actual local-file request.
Never copy a quotation or source locator merely because another example used it.

Each command reopens the whole selected source set through the existing path and
pinned-descriptor checks, verifies every declared original-file byte hash, parses
sections, and reconstructs the same full input corpus before checking handoff,
response, bundle and review bindings. Changed bytes fail even if the change is only
in a preamble outside parsed sections. Updating a changed file's manifest hash does
not make its old handoff or review current. No hash is silently refreshed.

The reconstructed `segments`, `segments_sha256` and `source_verification` fields
replace embedded copies. All other manifest metadata remains part of the input
binding, including unknown local annotations, while only documented source fields
enter the model request. Resolved absolute paths are not added to that request.
This binds reconstructed data, not the physical directory identity; identical
permitted files may reside under another explicitly selected root.

Local mode caps the combined **raw source bytes** at 2 MiB, in addition to the
handoff JSON and candidate limits below. It does not truncate. Structural and
whole-corpus authorization checks precede file reads. Path checks assume reasonably
stable local files; they are not a complete hostile-filesystem sandbox.

The raw helper returns ordinary detached data, not a serialized verification
receipt. Generic model bundles/revision packages keep their existing segment/quote
verification semantics; do not treat their unsigned `source_verification` strings
as a new local-byte attestation. For a package carrying the existing in-process
local-file receipt, run `corpus_files.py` on the appropriately curated manifest.
No handoff command writes source files, edits the input manifest, calls a model or
sends data. The exported handoff still contains source text and needs appropriate
permission before any external use. An empty-observation manifest can be exported,
but accepted reasoning candidates still need an explicitly curated observation
target. This bridge does not invent initial methods, conditions or limitations.

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

## First-observation mode

The default task remains `reasoning`. Use `--task observations` consistently for
prepare, response-template and import to propose initial method observations from
empty-observation corpora. These outputs use a deliberately separate review-only
packet and cannot enter the reasoning or manual-card gates. Missing conditions,
limitations and topics remain null. See [the complete workflow and stopping point](OBSERVATION_PROPOSALS.md).

## Pasteable local handoff view

Use `prepare --format text` for one pasteable text for a separately authorized
assistant, local or remote. Default `--format json` is unchanged; `response-template`
remains JSON-only. Both reasoning and observations support this view, including
`--source-root`. This is not permission to transmit source text: confirm destination,
rights, privacy, cost and retention separately. No model or network is called.

```sh
python model_handoff.py prepare examples/reasoning-corpus.json --format text
```

The view repeats the boundary and the JSON handoff's recomputed SHA-256, includes
its numbered instructions, response contract and empty response skeleton, and embeds
the complete handoff between `BEGIN LOCAL HANDOFF JSON` and `END LOCAL HANDOFF JSON`.
All embedded JSON uses ASCII escapes, preserving exact quotes, backslashes, controls,
non-ASCII characters and references when parsed. This is not prompt-injection
resistance. Import still binds the original JSON handoff, never the rendered text;
keep a JSON handoff for response-template and import. Builders, adoption and validation
semantics are unchanged. No source payload or version-specific field is omitted.

Views can be large: the synthetic contextual answer v3 walkthrough handoff is about
145 KB, including about 92 KB of reasoning context, and its text view about 152 KB.
Actual size depends on the inputs. Existing 16 MiB proposal output limits still apply;
text is never truncated. This command writes stdout; exclusive file output is a
separate capability, not supplied by this format option.
