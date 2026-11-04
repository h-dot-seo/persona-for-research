# Declared method-pattern application to design steps

A shared citation does not say **how a method-pattern hypothesis is being proposed
for a particular design step**. This review layer records that missing declaration:
the operator's application/adaptation rationale, step-specific condition comparison,
proposed checks, failure condition, uncertainty and selected evidence references.
It neither creates another plan nor claims that the researcher would choose it.

The existing design rationale and link-level applicability notes remain unchanged.
The existing context form compares source observations with the overall target.
This form asks a narrower question: how is this selected pattern being considered,
excluded or left unresolved for this particular already-proposed step?

## Synthetic integrated demonstration

```sh
python synthetic_walkthrough.py ../persona-method-use-demo --candidate-source offline-import --research-journey --recheck-sources --review-method-use
```

This runs **32 real CLI stages** using invented sources, canned imported proposals
and fixed operator fixture text. Read `source-recheck.txt`, `method-applications.txt`
and `research-journey.txt`. The source files and five stored quotes match, yet the
considered pattern application still conflicts with an excluded source context and
has no supplied failure condition. Both remain review prompts. Every answer claim
stays deferred; proposed checks are not executed. Matching bytes/quotes is never
converted into approval of a method or adaptation.

The two new stages create an all-deferred method-application template and render
one explicitly invented considered constraint. The runner accepts no external
candidate/form input. A failure in this stage prevents `COMPLETE.json`; earlier
artifacts remain diagnostic only. Existing modes are unchanged. Adding
`--review-method-use` to the 27-stage imported journey without live source checks
runs 29 stages; it always requires `--research-journey`.

## Create a bound all-deferred form

```sh
python method_application.py package.json patterns.json context.json links.json design.json --pattern-id selected-pattern --template --operator-id local-review-operator > method-applications.json
```

All existing artifacts are validated. Context and design must have exactly equal
question text. The form binds the complete package, pattern form/envelope, context
form, links artifact, design proposal and selected pattern ID. Changes to a context
assessment, plan action, link rationale or imported-review note invalidate the old
form. Re-review rather than manually copying old hashes to hide changed inputs.

Every design step gets one row, including unlinked steps, with decision `defer`,
null fields, no selected references and no copied default rationale. The row fields
are:

- `step_id`: the exact existing design step. Keep every step exactly once.
- `decision`: `consider`, `exclude` or `defer` for this pattern-to-step relationship.
- `proposed_role`: `method`, `constraint` or `counterargument`, or null while deferred.
- `application_rationale`: how the selected pattern is proposed to apply or adapt
  to this step, rather than repeating the step's general rationale.
- `target_condition_comparison`: the step-specific condition comparison. It does
  not replace the separately displayed enclosing-observation context assessment.
- `required_checks`: an explicit array of proposed checks, never executed/complete
  checks. An empty array remains a review gap.
- `failure_condition`: an operator-supplied stopping/failure condition, or null.
  A null value is not borrowed from a source limitation, pattern falsifier or plan.
- `remaining_uncertainty`: the operator's remaining uncertainty, or null if deferred.
- `evidence_refs`: unique exact references already in the selected pattern's
  support/challenge evidence. A component and its parent observation are distinct.

Consider/exclude require a proposed role, nonempty application rationale, condition
comparison, remaining uncertainty and at least one selected reference. They may
still have missing checks or failure criteria; these remain visible and the result
still requires human review. Filling every field does not resolve a deferred row or
validate the application. `exclude` does not remove the design step; it records an
excluded use of the selected pattern for that step.

This is a bounded **one-role summary per step for one selected pattern**, not a
complete inventory of all possible method/constraint combinations. It does not infer
additional roles. Existing multiple design link uses remain distinct and unchanged.

## Inspect or include in the research journey

```sh
python method_application.py package.json patterns.json context.json links.json design.json method-applications.json --pattern-id selected-pattern --format text
```

JSON is the default output. Both formats retain the selected sources, full supplied
pattern review/provenance, context decisions/counterevidence and unchanged design.
Imported pattern envelopes keep original versus reviewed explanations and rejected
candidate history. Current no-model flags do not authenticate earlier model use.

Add `--method-applications method-applications.json` to an existing
[research-journey command](RESEARCH_JOURNEY.md). It can be combined with explicit
live-source selection/root options. Application inputs are validated before any
source reread and are included in the full journey input hash.

The journey adds a `method_application_uses` annotation to exact reference routes
and merges domain-labeled prompts. It does **not** add answer citations, design link
uses, active evidence, active publication IDs or inferred argument support. A
pattern-only reference stays inactive even when an application row selects it.
The no-application journey payload and text retain their existing behavior.

## Read the prompts without treating them as verdicts

- Target-step membership uses only that step's actual `link_uses`, not another step
  or an unused supplied link. A missing route stays a prompt; no citation is copied.
- Context matching is exact at the observation level; for a component it is explicitly
  `ENCLOSING_OBSERVATION_ONLY`, not component-specific semantic approval.
- Considered use with excluded context, deferred context, missing fields, future
  publication dates and unresolved same-year order remain visible. An excluded
  source may legitimately support a counterargument; an overlap is not automatically
  misuse. No decision or source stance is silently changed.
- Original source stance, pattern support/challenge role, proposed application role
  and design link role may differ. None overwrites another.
- Proposed checks and failure conditions are not evaluated for adequacy, run,
  considered completed or inferred from source text.

Limits: 128 design steps, 32 unique evidence references per row, 16 unique required
checks, 2,000 characters per text field, 8 MiB combined/file JSON input and 16 MiB
output. Invalid/stale forms fail with no partial stdout; nothing is truncated or
silently selected. The API is read-only and makes no provider/network/source call.
Keep generated forms outside the public repository and review their contents before
sharing. No source authenticity, semantic support, actual researcher reasoning,
authenticated human review or scientific validity is established.
