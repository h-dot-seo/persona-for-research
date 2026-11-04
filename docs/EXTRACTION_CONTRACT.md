# Candidate extraction adapter contract

This is a provider-neutral data contract plus a **synthetic mock-only runner**.
A separate [offline handoff/import](MODEL_HANDOFF.md) supports saved model responses
with declared provenance and the same explicit review gate; it does not call a model.
It is not a live AI integration. The built-in mock returns a supplied canned
response; `llm_used`, `inference_performed` and `external_transmission` are false.
No credentials, network clients, model downloads or paid services are used.

```sh
python extraction_adapter.py examples/reasoning-corpus.json --mock-response examples/mock-extraction-response.json
```

## Request and trust boundary

Before calling the mock, the runner checks the entire corpus's author identity,
explicit authorization, training-only split and runtime eligibility, validates
supplied segment hashes/quotes and constructs a deterministic preflight package.
Sources with missing/invalid permissions, holdout status or changed segments fail
before provider invocation. Authorization declarations do not prove permission;
upstream access decisions and correct split labels remain necessary.

The version-1 request contains:

- Task `propose_reasoning_components`, scholarly author ID and allowed dimensions.
- Explicitly supplied sources with paper ID, research/review kind, year, topic,
  source hash, segment hash and locator-to-text segments.
- A response contract listing required keys, proposed claim types and size limits.
- A boundary stating that source passages are data rather than instructions.

Prior annotations and unknown metadata are not included in requests. Source text
is kept in the local mock request but omitted from output; only bounded returned
quotes and candidate text survive. The request hash, exact input-corpus hash and
preflight-persona hash identify deterministic inputs, not an approved canonical
release or a signature.

`ExtractionProvider` defines the future method interface. The current runner accepts
only the built-in `MockProvider`, not arbitrary implementations or subclasses.
This is an implementation gate, not a sandbox against code running in the same
Python process. Enabling a real local/hosted provider requires a separate reviewed
implementation and specific authorization for its source access, data destination,
cost and retention. No external-provider authorization is inferred from this demo.

## Response and candidate validation

Return an array of objects with exactly these string fields:

| Field | Meaning |
| --- | --- |
| paper_id | An allowed request source ID |
| locator | A locator in that source's supplied segments |
| evidence_quote | An exact substring at that locator, at most 500 characters |
| dimension | A supported reasoning-card dimension |
| candidate_text | Proposed text, at most 2,000 characters |
| proposed_claim_type | `explicit_statement` or `operator_interpretation` proposal |

Unknown fields, unsupported dimensions/types, missing locators, invented quotes,
disallowed source IDs and oversized outputs fail closed. Oversized text is rejected,
not silently truncated. These length limits are not copyright clearance.

All accepted rows remain `CANDIDATE_REQUIRES_HUMAN_REVIEW`. Quote matching is labeled
`EXACT_QUOTE_MATCH_ONLY`; semantic support and individual-author attribution are
not established. Even a proposed explicit statement is not an approved author claim.
The result cannot be passed directly to `build()` and no canonical update occurs.

## Required human review before any later integration

1. Confirm source identity, access/quotation rights, locator and surrounding context.
2. Check whether the proposed text follows from the quote and whether it is an
   explicit statement, a paraphrase or an operator interpretation.
3. Preserve counterevidence, conditions, limitations and coauthor attribution limits.
4. Reject private-belief, personal-memory or researcher-reproduction claims.
5. Record explicit decisions through the [operator review gate](OPERATOR_REVIEW.md)
   or deliberately curate a separate observation input. Inspect the resulting
   revision candidate before any canonical adoption. There is no automatic approval
   or promotion endpoint, and the adapter never edits a canonical package.

Synthetic tests verify mechanical boundaries only. No actual AI quality, semantic
extraction quality or researcher fidelity has been evaluated. Treating source text
as data in a canned mock does not establish prompt-injection resistance for any
future real model. The mock label describes the execution path, not proof that an
arbitrary caller's input text is synthetic or safe to redistribute.
