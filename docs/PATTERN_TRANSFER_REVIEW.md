# Keep pattern counterarguments and context gaps visible in a new proposal

A pattern worksheet, context assessment and research proposal can each validate
while a contrary source or unresolved condition is lost between them. This report
joins the **existing artifacts** by exact references. It adds no new proposal or
assessment schema and does not decide whether a pattern was correctly applied.

Using files from the pattern/applicability and review-workspace guides:

```sh
python pattern_transfer_review.py ../my-review/package.json ../patterns.json ../applicability.json ../my-review/links.json ../my-review/design.json ../my-review/answer.json --pattern-id comparison-first --format text
```

Select exactly one existing pattern ID explicitly. Every artifact must validate
against the same package. The context form's question must match the answer/design
question **exactly**; its reference year supplies the shared chronological cutoff.
Create fresh forms with the intended question/package rather than rewriting binding
hashes. Different wording can mean the same thing, but this tool does not infer it.
The pattern's declared scope is preserved and is not automatically equated with the
new question. Pattern/context/answer/design operators remain separate declarations.

## Synthetic failure the report exposes

The automated end-to-end scenario proposes a comparison-first pattern, then declares
that the new system lacks the source method's distinct-outcomes condition. An
operator excludes the source observation in the context worksheet, but a plan still
uses a link containing that exact reference as motivation. The report displays:

- The original condition and limitation, the operator's exclusion reason and
  remaining uncertainty, and the actual plan/link/reference use.
- `EXCLUDED_OBSERVATION_HAS_SHARED_DESIGN_REFERENCE`, a review prompt rather than
  an automatic misuse judgment. An excluded method may legitimately be discussed
  as a negative example or counterargument.
- A later review's date/claim labels and the pattern's challenge role, while showing
  when no exact answer citation is labelled challenge and no shared design link use
  is labelled counterargument.
- Missing pattern falsification criteria and the plan's own missing hypothesis,
  alternatives, falsification and uncertainty. One artifact's text does not fill
  another's missing field.

A second scenario explicitly uses the review reference as an answer challenge.
That structural role match is visible, without declaring the counterargument
scientifically resolved. Link-use roles describe the **whole link**: sharing an
endpoint of a counterargument link is not proof that the individual endpoint is
itself a counterargument. Link relation and from/to direction remain visible.

## How routes are matched

Pattern-to-answer/design uses require the exact paper ID, observation index and
component dimension. An observation and its component are not collapsed. Unused
supplied links stay separate from actual design-step uses. A pattern reference not
used in an answer/design is reported, not automatically inserted or declared vital.

Context assessments are observation-level. For a pattern component, its enclosing
observation's condition decision is displayed with `ENCLOSING_OBSERVATION_ONLY`.
It is **not** approval of each component assertion. If there is no such assessment,
that absence is shown. Merely listing a reference as context counterevidence does
not create a primary condition assessment for it. Explicit counterevidence uses
are separately traceable.

The text report includes the full supplied context review and full answer/design
review after the selected-pattern routes. Therefore unrelated explicit context
counterevidence and evidence outside the selected pattern are not silently removed.
The selected pattern's alternative explanation, falsification criterion, uncertainty
and original support/challenge roles remain visible. Missing routes and deferred
judgments are mechanical prompts, not a score or exhaustive scientific checklist.

This tool does not assert that shared evidence means agreement, applicability,
causal support, faithful researcher thought or actual implementation of the selected
pattern. Chronology describes supplied publication years, not intellectual influence
or precise historical availability. Claim labels, source stance, operator pattern
roles, answer citation roles and design-use roles remain distinct.

## Preservation and review limits

Inputs are read-only. No source bytes are reread, original claims generated, package
bindings changed, recommendations applied or reviewer decisions authenticated.
Input hashes bind the selected pattern ID and supplied forms/packet for inspection;
they are unsigned, not permission or provenance authenticity. Holdout and source
validation boundaries come from the existing artifact validators. Actual source
quote check labels are historical records, not renewed semantic validation.

All reports may contain private target context, quotes and identifiers. Keep them
private; this is not anonymization or rights clearance. No real scholar materials,
LLM, external API or scientific execution are used in the synthetic workflow.

```sh
python -m unittest tests.test_pattern_transfer_review -v
```

## Imported pattern proposals

The same inspector also accepts the versioned reviewed envelope from
[model-assisted pattern proposals](PATTERN_PROPOSALS.md). It replays the bound
original bundle and every explicit decision, rather than trusting cached acceptance.
Imported origin, original/revised text, rejected proposals and unauthenticated
model/run/reviewer provenance remain visible in JSON and text. Current inspection
performs no model call; historical model use is not authenticated. Manual forms are
unchanged, and neither form approves applicability or creates an answer/design.

## Optional publication relationships

Use `--publication-relations ../publication-relations.json` to add separately
[declared publication context](PUBLICATION_CONTEXT.md): review summaries, material
reuse, versions, method extensions and challenges with exact basis references.
The overlay distinguishes selected, one-sided and outside-source relationships,
without changing original counts, roles or decisions. Missing declarations do not
establish independence, and chronology does not prove influence. Omitted context
preserves earlier output; an explicit empty form adds a bound empty context.

## Declared answer review and integrated journey

Pass `--review answer-review.json` to preserve the complete declared answer review
in the detailed answer/design section. The review must match the current draft;
reject/defer decisions remain visible and never approve a pattern or design. With
no review supplied, the original output and bindings remain unchanged.

[Research journey](RESEARCH_JOURNEY.md) joins this transfer review with the same
answer review, argument map and topic chronology, preserving distinct exact-reference
roles and all supplied publication context. It does not replay absent extraction
history or turn context-only references into active evidence.
