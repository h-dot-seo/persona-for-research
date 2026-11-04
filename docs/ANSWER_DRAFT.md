# Review an evidence-bound answer draft

The design-scenario tool records proposed actions and links between sources. This
separate workflow records the actual answer claims a reviewer must assess. It does
not generate prose or consult a model. A synthetic operator can supply mock answer
text and then exercise the same citation and review contract.

```
python answer_draft.py package.json --template --question "How could two synthetic explanations be distinguished?" --operator-id synthetic-operator > draft.json
# Fill claims explicitly, then inspect:
python answer_draft.py package.json draft.json --format text
python answer_draft.py package.json draft.json --review-template --reviewer-id synthetic-reviewer > review.json
# Record every decision and a bounded, nonempty note:
python answer_draft.py package.json draft.json --review review.json --format text
```

Each claim has `claim_id`, `text`, `claim_type`, nullable `uncertainty`, and `citations`.
Each citation has a `reference` (paper ID, observation index, nullable reasoning
dimension) and an explicit operator-assigned role: support, challenge or context.

- `operator_synthesis` is the operator's answer, not an author statement. A claim
  without citations stays visible as `NO_CITATIONS_SUPPLIED`.
- `source_quote` requires exactly one citation and exact equality of the entire
  claim text with that selected record's stored `evidence_quote`. It is not a new
  source-byte check, semantic verification or rights clearance. A stored quote can
  be unverified; its recorded verification status is displayed separately.

References cannot fall back from a missing component to its observation. Bound
package/source/rule consistency and authorization checks apply before inspecting
claims. Source research/review kinds, year, coauthorship warning, claim labels,
conditions, limitations, hashes and locators remain separate from answer types and
citation roles. A review can report another author's work. Neither stored quotation
nor `explicit_statement` proves ownership by the named researcher.

The report retains all uncited observations, including challenges, without
asserting relevance. This is observation-level coverage, **not** an inventory of
unused components: citing one component counts its observation as cited. No search
for missing literature or automatic completeness score is performed.

The review template starts with `defer` for every claim. A completed record must
contain every claim exactly once with retain/revise/reject/defer and a note. Any
change to question, operator, claim text, uncertainty, citation role or references
changes the draft hash and invalidates the saved review. Package bindings are
inside that draft hash. Review records are self-consistent declarations, not
signatures or authenticated reviewers. A caller can author a new review of a new
draft; hashes do not prove a human actually made the judgment.

Retain, revise and reject are all preserved in output. No automatic accepted-answer
extraction or publication occurs. `DECLARED_REVIEW_RECORDED_NOT_VALIDATED` means
there are no deferred decisions, not that every claim was retained or scientifically
verified. Rejected text and contrary evidence remain visible for the audit.

Actual synthetic CLI and negative tests:

```
python -m unittest test_answer_draft -v
```

Real scholarly evaluation requires authorized local sources, quotation rights,
identity checks and independent scientific review. This tool performs no real AI
inference, author-fidelity evaluation, external transmission or source acquisition.

## Explicitly adopted imported answers

Use [answer proposals](ANSWER_PROPOSALS.md) for an offline handoff, candidate review
and history-preserving imported envelope. Supply that envelope in place of a draft.
The `operator_synthesis` type does not claim wholly operator-authored text; origin
and adopted citation-role labels distinguish imported material. Separate answer
review still defaults to defer. Full imported history, even rejected alternatives,
binds the draft hash and survives every inspection. Manual drafts are unchanged.
