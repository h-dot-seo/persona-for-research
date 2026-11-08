# Bounded review-attribution example

This fixed, fully invented offline example preserves a distinction that source-kind and claim-type labels alone cannot express. It adds no schema, runtime policy, inference engine, or workflow. No actual scholar, group, publication, provider, browser, or external source is involved.

## The two focal passages

One invented review, `synthetic-review`, contains two distinct observations:

1. `observation_index: 0`: “The synthetic Lantern Group used method M to compare two simulated signals.” This reports another invented group's method. It does not establish the synthetic scholar's own practice, development, or implementation. The original paper is absent.
2. `observation_index: 1`: “This review recommends testing alternative N before choosing between the simulated signals.” This is the review's recommendation to test an alternative. It still does not establish an individual's practice, development, or implementation. Individual ownership remains unestablished.

Both have `source_kind=review`, `claim_type=explicit_statement`, and `dimension=null`. Their exact reference/quote pairs remain separate. `explicit_statement` describes the stored passage, not verified personal authorship or adoption.

Existing observation limitations, per-reference pattern `rationale` / `context_boundary`, citation explanations, and uncertainties carry the distinction. Support/challenge reasons and uncertainties are explicit operator judgments, not source-author endorsements. The pattern is an operator's bounded reading hypothesis, not an individual researcher's habit.

Reason-bearing reviewed pattern proposals require two distinct paper IDs. A separate invented `synthetic-context-review` therefore supplies a context-only caution about reporting versus implementation. It is **not** the absent original paper, independent verification, or personal-use evidence. It is excluded in the applicability context and never selected as an exact answer citation. No `review_summary_of` relationship is fabricated; the publication-relations list is empty.

## Five complete fixtures

- `examples/review-attribution-package.json`: two synthetic review records, including the two focal passages; no source file or URL. Recorded source/quote checks remain `NOT_PERFORMED`.
- `examples/review-attribution-scope.json`: existing v3 answer scope, raw reviewed pattern/context/publication-relation artifacts, and exactly the two focal observation references.
- `examples/review-attribution-response.json`: canned bounded candidate plus unsupported candidate.
- `examples/review-attribution-provenance.json`: explicit `synthetic-no-provider` / `synthetic-no-model` provenance. No model execution is claimed.
- `examples/review-attribution-adoption.json`: fixed operator decisions that accept “The review reports M and recommends testing N.” and reject “The scholar uses M.”

The rejected statement survives only as explicitly rejected imported-candidate history, not an active answer claim. Its source reference legitimately remains active for the bounded accepted claim. Candidate rejection does not erase shared evidence. The accepted artifact records an operator adopting wording, **not** the scholar adopting a method. This fixed fixture decision is not a general automatic review policy. A separately generated final answer review remains all-deferred with `DECLARED_REVIEW_INCOMPLETE`.

## Reproduce with existing CLIs

Run from an external temporary directory; set `REPO` to the absolute checkout path. These commands require only Python and the existing repository. No source reread, provider, browser, or network step is requested.

```sh
REPO=/absolute/path/to/persona-cloud
WORK=$(mktemp -d)
cd "$WORK"
for name in package scope response provenance adoption; do
  cp "$REPO/examples/review-attribution-$name.json" "$name.json"
done
python "$REPO/answer_proposals.py" context package.json scope.json > preview.json
python "$REPO/answer_proposals.py" context package.json scope.json --format text > preview.txt
python "$REPO/answer_proposals.py" prepare package.json scope.json > handoff.json
python "$REPO/answer_proposals.py" response-template package.json scope.json handoff.json > empty-response.json
python "$REPO/answer_proposals.py" import package.json scope.json handoff.json response.json provenance.json > bundle.json
python "$REPO/answer_proposals.py" review-template package.json bundle.json --reviewer-id synthetic-reviewer > deferred-adoption.json
python "$REPO/answer_proposals.py" review package.json bundle.json adoption.json > adoption-review.json
python "$REPO/answer_proposals.py" review package.json bundle.json adoption.json --format text > adoption-review.txt
python "$REPO/answer_proposals.py" export package.json bundle.json adoption.json > draft.json
python "$REPO/answer_draft.py" package.json draft.json > answer.json
python "$REPO/answer_draft.py" package.json draft.json --format text > answer.txt
python "$REPO/answer_draft.py" package.json draft.json --review-template --reviewer-id synthetic-final-reviewer > final-review.json
python "$REPO/answer_draft.py" package.json draft.json --review final-review.json > final-result.json
```

The regression additionally unpacks the three raw context objects into temporary UTF-8 JSON files, invokes the existing `answer_proposals.py template` CLI with those contexts, and previews the resulting empty selection. That makes **15 successful CLI stages**. Empty selection stays empty, and `prepare` rejects it. Context exposure does not silently expand citation authority.

```sh
cd "$REPO"
python -m unittest tests.test_review_attribution_example -v
```

The nine tests cover the real external-directory CLI sequence, exact distinct passage identities, retained rationale/boundaries, exact citation scope, rejection of a context-only citation, empty selection, rejected history versus active claims, all-deferred final review, input immutability, escaped operator control characters, and in-memory operations with file/network access guarded. Existing snapshots and runtime modules are unchanged.

This demonstrates **preservation of supplied distinctions**, not automated semantic inference, attribution detection, source authentication, or author-fidelity validation. The tools do not establish that the statements entail the bounded answer; the fixed acceptance/rejection is an explicit synthetic operator judgment.
