# Model-assisted method-pattern proposals, with explicit review

`pattern_proposals.py` prepares an offline request to compare supplied scholarly
records, imports a separately obtained response, and preserves its origin through
pattern and new-context review. It does not call a model, authenticate a provider,
automatically approve a method or speak as the researcher.

Unlike a plain manual pattern form, the reviewed artifact contains the original
proposal bundle and every recorded accept/reject decision. Both pattern inspection
and pattern-to-context transfer replay that history against the current package.
No imported proposal is converted into an origin-free manual form.

## What the model can compare

The handoff takes an existing authorized, author-matched, training-only package.
It validates the entire package before selecting observations by exact,
case-insensitive topic. All publication years and source/rule agreement are checked,
including unselected records. It projects an explicit catalog of observations and
reasoning components, keeping:

- Original research versus review and publication year, without implying the time
  of an idea, independence, individual authorship or a change of mind.
- Methods, conditions, limitations, topic, source stance and claim labels.
- Recorded quotes, locators, hashes and verification labels. These are historical
  records; no original source file is reread and no quote match is renewed.
- Supplied question framing and other reasoning dimensions, missing dimensions,
  and any existing reviewed-candidate component provenance.

Every proposed reference must be an exact catalog reference. The model cannot add
new quotes, papers or evidence fields. A proposal needs at least two distinct paper
IDs across support and challenge roles, and at least one supporting reference.
This is a comparison requirement, not evidence of recurrence: one supporting paper
plus one challenge is allowed and the single-support warning remains. Distinct
paper IDs or hashes never establish independent confirmation. Shared hashes,
missing quotes, absent challenges, missing alternatives/falsifiers/uncertainty and
same-reference dual roles remain explicit review prompts.

A model can propose a tentative relationship between differently worded methods,
with a scope, rival explanation, possible falsifier and uncertainty. This is an
unapproved hypothesis. The prompt forbids invented researcher speech, private
thoughts and individual ownership claims, and treats all passages and annotations
as untrusted data. Prompt wording and schema validation are not proof of model
quality, injection resistance or semantic truth.

## Local workflow

Keep actual packages and generated artifacts outside this public repository. For
a synthetic package, first follow the [offline imported walkthrough](MODEL_HANDOFF.md)
or existing intake examples. In commands below, `../package.json` is an existing
bound package. Save each output to a new private file; stdout redirection is the
operator's responsibility and can overwrite a file if reused.

```sh
python pattern_proposals.py prepare ../package.json --topic "model design" > ../pattern-handoff.json
python pattern_proposals.py response-template ../package.json ../pattern-handoff.json > ../pattern-response.json
```

The response template contains the exact handoff hash and an empty `candidates`
array. Preparing a source-containing handoff is **not permission to transmit it**.
Use a separately authorized local model, Codex task or API workflow if appropriate.
This CLI has no credentials, automatic upload or provider invocation. An empty
response is valid when no supported comparison can be proposed.

Each candidate has exactly these fields, using reference objects from the catalog:

```json
{
  "proposed_hypothesis": "A tentative comparison-first pattern in these synthetic records.",
  "scope_note": "Only these selected synthetic records, not a real scholar trait.",
  "support_refs": [
    {"paper_id": "synthetic-0", "observation_index": 0, "dimension": null}
  ],
  "challenge_refs": [
    {"paper_id": "synthetic-1", "observation_index": 0, "dimension": null}
  ],
  "alternative_explanation": "A shared disciplinary convention could explain the similarity.",
  "falsification_check": null,
  "uncertainty": "One supporting record does not establish a recurring method."
}
```

The identifiers above belong to repository synthetic fixtures. Never fabricate
references for a real package. Null means not supplied, not absent. Support and
challenge here describe proposed uses, separate from the original source stance.

Record declared generation information in a separate provenance JSON file with
exactly `provider_id`, `model_id`, `run_id`, `operator_id` and `execution_location`.
The location must be `local`, `remote` or `unknown`. For tests, all identifiers must
clearly say synthetic. These declarations do not authenticate actual model use.

```sh
python pattern_proposals.py import ../package.json ../pattern-handoff.json ../pattern-response.json ../provenance.json > ../pattern-bundle.json
python pattern_proposals.py review-template ../package.json ../pattern-bundle.json --reviewer-id local-reviewer > ../pattern-review.json
```

Every decision defaults to `defer`. Read the original sources before recording
judgments. Each candidate requires exactly one `accept`, `reject` or `defer`, and
a nonempty `review_note`. Acceptance additionally requires a complete
`reviewed_pattern`, with an explicit unique `pattern_id`, `operator_hypothesis`,
`scope_note`, `support_refs`, `challenge_refs`, `alternative_explanation`,
`falsification_check` and `uncertainty`. These are the ordinary pattern fields.
They are not silently copied from the model response. The reviewer may correct
text and reference roles, but every reviewed reference must remain in the original
topic catalog. Original and reviewed references/text are retained side by side.
To use a different topic or changed package, prepare a new handoff and review.

```sh
python pattern_proposals.py review ../package.json ../pattern-bundle.json ../pattern-review.json --format text
python pattern_proposals.py export ../package.json ../pattern-bundle.json ../pattern-review.json > ../reviewed-patterns.json
```

Export rejects if any candidate is deferred or if none was explicitly accepted.
The result is a versioned provenance-bearing **review worksheet**, not a runtime
persona, approval certificate or design. The bundle retains rejected candidates,
contrary evidence and their review notes. Review identities are recorded, not
human-authenticated. Hash bindings prevent accidental mismatches; someone who
constructs a new consistent artifact has made new declarations, not proven history.

## Continue to existing evidence and context review

```sh
python pattern_hypotheses.py ../package.json ../reviewed-patterns.json --format text
python pattern_transfer_review.py ../package.json ../reviewed-patterns.json ../context.json ../links.json ../design.json ../answer.json --pattern-id reviewed-comparison --format text
```

Use the explicit reviewed pattern ID you supplied. Context, links, design and
answer files must already exist and be independently authored/inspected under the
[pattern transfer workflow](PATTERN_TRANSFER_REVIEW.md). Nothing generates or
approves them from an accepted pattern. Context exclusions, deferred assessments,
unresolved applicability and missing counterargument use remain visible.

JSON and text preserve imported origin, full original/reviewed content, all
recorded decisions, model/run/operator declarations and handoff/response/bundle/
review hashes. The selected pattern carries its own origin, while the full review
history remains attached. The imported-origin qualifier appears at the top of
pattern and transfer text. `llm_used: false` in these deterministic inspectors is
scoped to the current inspection; historical model use remains declared and
unauthenticated. Manual forms remain supported unchanged.

The full checked package hash also binds unknown metadata that is omitted from the
request projection. Projection is not anonymization: supported quotes, annotations
and identifiers can still be private or copyrighted. Source/provider identity,
semantic support, researcher fidelity and rights clearance remain unevaluated.

## Limits and synthetic verification

Requests are limited to 2 MiB of logical JSON; each CLI input to 8 MiB; responses
to 32 candidates and 32 references per role. Text fields are bounded to 2,000
characters, identifiers according to their documented validators. Strict JSON
rejects duplicate keys and nonfinite numbers. No outputs are partially printed on
validation errors, and input files are never modified.

```sh
python -m unittest test_pattern_proposals -v
```

Tests use invented publications and canned responses only. They cover real CLI
prepare/import/default-defer/review/export/pattern/transfer execution, original and
reviewed roles, rejected counterevidence, stale and tampered history, authorization,
bounds, missing quotes, deep-copy isolation and model/network/source-read absence.
No actual model, real researcher material or scientific validation is involved.
