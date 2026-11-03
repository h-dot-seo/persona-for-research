# From mock proposals to a separate revision candidate

The review gate records explicit operator decisions. It does not authenticate a
human identity, evaluate semantic correctness, overwrite a canonical package or
approve deployment. Only synthetic mock candidate bundles are currently supported.

## Workflow

1. Generate candidates with `extraction_adapter.py` and retain the exact input
   corpus and candidate bundle outside this public repository.
2. Generate a hash-bound deferred template:

   ```sh
   python operator_review.py corpus.json candidates.json --template --reviewer-id reviewer-reference
   ```

   Every decision is `defer`. No approval or target is inferred. Save the JSON,
   inspect source context and the candidate bundle, then explicitly edit decisions.
   Do not automatically fill accept decisions for real evidence.
3. Submit the operator-authored review as a separate file:

   ```sh
   python operator_review.py corpus.json candidates.json review.json --new-version 2 --new-build-id reviewed-candidate
   ```

4. Retain the resulting separate JSON artifact. If it contains `package`, inspect
   it with `review_package.py` and compare it with the previous package using
   `compare_releases.py`. Canonical adoption remains a separate explicit decision.

The tool writes only stdout and never overwrites input files. Keep the original
corpus, candidate bundle and review record: hashes identify those artifacts but
do not replace them or function as signatures. Existing bundles lacking the new
exact `input_corpus_sha256` binding must be regenerated before review.

## Review fields

The top-level review has exactly `candidate_bundle_sha256`, `input_corpus_sha256`,
`reviewer_id` and `decisions`. The template supplies hashes of the full candidate
bundle and exact logical JSON input, including observation order. JSON object-key
ordering does not affect hashes. Changed evidence, annotations, targets or candidate
text requires a newly bound review.

Each candidate needs exactly one explicit decision:

- `reject` or `defer`: `candidate_id`, `decision`, and a nonempty `review_note`.
- `accept`: those fields plus `target_rule_id`, `target_paper_id`, `operation`,
  `expected_component_sha256`, `reviewed_text`, and `reviewed_claim_type`.

Acceptance names an existing rule in the exact preflight package and the same
paper as the candidate. The candidate's reasoning dimension is retained. Creating
an initial method/condition/limitation observation remains a separate manual task.
The tool does not infer a target or silently select among ambiguous records.

For `operation: add`, the dimension must be empty and the prior hash must be null.
For `operation: replace`, the supplied hash must equal `persona.payload_sha256` of
the existing component in the input corpus. This explicitly confirms replacement
of that exact content. Two accepted candidates cannot target one component.

`reviewed_text` may revise the proposal, but its source locator and quote are
rechecked and retained. `reviewed_claim_type` must be `explicit_statement` or
`operator_interpretation`; the original `proposed_claim_type` remains separate.
This is an operator declaration, not proof that the quote supports the claim or
that an individual author endorses it.

## Outcomes and boundaries

- Missing/duplicate/unknown decisions and stale bindings fail without output.
- Any `defer` yields `REVIEW_INCOMPLETE` and no package, even if other candidates
  were accepted. Rejected candidates never enter the revision.
- All rejected, or no candidates, yields `NO_ACCEPTED_CANDIDATES` without a package.
- Complete review with accepted items yields `REVIEWED_REVISION_CANDIDATE` with a
  new version/build identity, a decision trail and a separate bound `package`.
- Reviewed components retain candidate/bundle/review references, mock origin,
  proposed type and reviewed type. Raw source sections and unknown metadata are
  excluded by runtime projection. Preserve the referenced sidecar artifacts.
- Authorization, training splits, segment/source metadata and quoted locators are
  rechecked. Validation calls no provider and performs no external transmission.
- Reviewer identity is `RECORDED_NOT_AUTHENTICATED`, semantic validation remains
  `NOT_PERFORMED`, and `canonical_update_performed` remains false.

The declared reviewer ID and notes are local review data, not authorization to
share them or source material with a service. Real-source rights, genuine human
review and later publication/transfer permission remain separate requirements.

## Synthetic end-to-end demonstration

```sh
python -m unittest test_operator_review -v
```

This executes the real mock extraction, deferred-template, operator-review,
compact-view and release-comparison CLIs with temporary synthetic inputs. Decisions
are explicitly simulated, not genuine human review, and originals remain unchanged.
Adversarial tests cover stale sources/targets, rejected/deferred rows, conflicting
targets, explicit replacement, fabricated quotes, unsupported fields, provider
isolation and shared Python references. No real researcher is evaluated.
