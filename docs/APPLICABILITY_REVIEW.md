# Compare source methods with a new research context

A source may propose a method under conditions your new study does not satisfy.
The planning scaffold lists those conditions, but does not decide whether they
hold. `applicability_review.py` creates a complete, deferred worksheet for an
operator to compare topic-matched observations with an explicitly supplied context.

After the [manual observation journey](MANUAL_LOCAL_OBSERVATIONS.md), run:

```sh
python applicability_review.py ../manual-result.json --template --question "Which comparison could distinguish the new synthetic explanations?" --target-context "The new synthetic system has shared predictions and no discriminating measurement yet." --topic "model design" --reference-year 2020 --operator-id synthetic-operator > ../applicability.json
python applicability_review.py ../manual-result.json ../applicability.json --format text
```

Choose new output names and check exit status; shell redirection can overwrite a
file or leave an empty file on failure. Both commands use only the supplied package.
The target context is operator text, not extracted from private data or inferred
from the question. No source files, network or models are accessed.

## Read sources before making a judgment

Each observation whose **observation topic** exactly matches, ignoring case, gets
one row. Paper-level topic is not substituted. Rows are shown in supplied publication
year order, with research/review kind, source hash and locator, method, condition,
limitation, stance, original claim type and quote. All supplied reasoning components
are displayed with their own claim labels and provenance; missing framing,
alternatives, evidence standards, falsification checks and uncertainty remain missing.

The year cutoff flags before/same-year/after-year evidence. It does not date the
researcher's awareness, establish availability within a year, infer career stages,
or make later reviews supersede earlier research. Research/review labels are
operator metadata; a review may describe others' work rather than its author's
individual position.

The worksheet initially sets every decision to `defer` with no context comparison,
uncertainty or counterevidence refs. It does not select a method or fill a proposal.
Edit each assessment explicitly:

- `consider`: keep it under consideration, **not** approved/applicable/validated.
- `exclude`: do not apply this observation in this stated context. It remains in
  the report rather than disappearing.
- `defer`: leave the applicability judgment unresolved.
- `context_comparison`: explain how source conditions/limitations compare with the
  target situation. State both similarities and mismatches that matter.
- `remaining_uncertainty`: state what remains unresolved. `consider` and `exclude`
  require nonempty comparison and uncertainty text; the tool cannot judge whether
  that text is substantive or correct.
- `counterevidence_refs`: optional exact references from the bound package, using
  paper_id, observation_index and dimension. A reference can point to an observation
  or component, including another topic. It must be selected by the operator.

For example, an operator might write that a method requiring distinct predictions
cannot discriminate explanations in a new system with shared predictions, then
leave the decision deferred or explicitly exclude that use. This is illustrative
operator reasoning, not an automatically generated conclusion or an author's claim.

Counterevidence is shown in full with its original stance/claim labels, reasoning
component provenance and temporal scope. Selecting it as counterevidence does not
change those labels or establish that it contradicts anything. There is no automatic
selection based on a review label, challenge stance, wording similarity or recency.
The absence of counterevidence refs is visible and is not proof that none exists.
Duplicate or identical self references reject; no independence is inferred for
other references, including components of the same observation.

## Preserve the comparison set and review boundary

All topic-matched observations must appear exactly once, including excluded/deferred
ones. Dropping a row, adding an unrelated primary row or repeating one fails. This
prevents accidental hiding within the declared topic scope, not cherry-picking by
choosing a narrow topic. Other-topic observation counts remain visible. Empty topic
matches return NO_TOPIC_MATCHED_OBSERVATIONS, never a positive readiness signal.

Package bindings reject a stale worksheet. A separate context binding covers the
question, target context, topic, reference year and declared operator. Changing one
requires a fresh template and manual reconsideration of judgments, not rewriting a
hash to reuse them. Bindings and operator IDs are unsigned, not access controls or
proof of authenticated human review. Decision counts are descriptive, never a score.

Nothing automatically promotes a `consider` row into a plan or migrates it into
answer citations. Use the existing answer/design artifacts to write and review the
specific new proposal yourself. Exact quote checks remain historical package labels;
no source byte or semantic validation is renewed here. The report cannot establish
real researcher representation, causal transferability or scientific validity.
All output may contain private context, source quotes and identifiers. It is not
sanitization, rights clearance or permission to publish excerpts.

```sh
python -m unittest test_applicability_review -v
```

For a tentative recurring method across publications, first record an explicit
[operator pattern hypothesis](PATTERN_HYPOTHESES.md) with rival explanations and
falsification criteria. Such a pattern does not automatically make it applicable
to the new context or populate this worksheet.
