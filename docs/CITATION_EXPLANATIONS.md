# Explain why a source is cited for one claim

A support/challenge/context label does not explain **why that passage bears on this
particular claim**. Optional citation explanations record that interpretation and
its context boundary. They never verify support, source authorship, historical
availability, quotation rights or researcher agreement.

This is separate from the source observation's stance, a method-pattern rationale,
a method application's conditions, and an argument bridge between claims. None of
those fields is inferred from, or overwritten by, a citation explanation.

## Manual drafts: explicit opt-in per citation

Existing citations with exactly `reference` and `role` remain valid and unchanged.
To opt in, add `explanation` to a citation:

```json
{
  "reference": {
    "paper_id": "synthetic-0",
    "observation_index": 0,
    "dimension": "alternative_explanation"
  },
  "role": "support",
  "explanation": {
    "rationale": "The recorded alternative motivates comparing distinct predictions.",
    "context_boundary": "Invented comparison only; transfer to this question is untested."
  }
}
```

`explanation` is either null or an object containing exactly `rationale` and
`context_boundary`. Rationale is a nonblank string of at most 2,000 characters.
Context boundary is null or a nonblank string with the same limit. An explicit
null explanation is allowed; do not invent reasoning to fill the form.

Three states remain distinct:

- Legacy key absent: the old contract did not request an explanation. Ordinary
  inspection adds neither an explanation field nor a new missing-explanation prompt.
  Absence is **not** evidence that the citation was justified.
- Explicit null: `EXPLICITLY_NOT_SUPPLIED`, with a
  `CITATION_EXPLANATION_NOT_SUPPLIED` prompt for the exact claim, reference and role.
- Supplied object: `DECLARED_INTERPRETATION_NOT_VALIDATED`, never verified support.

Null context boundary is displayed as not supplied; it does not create an extra
missing-explanation prompt. A filled rationale is not a complete review checklist.
Manual explanations are labeled `OPERATOR_SUPPLIED_INTERPRETATION`.

Existing duplicate reference/role and literal source-quote equality rules still
apply. The same passage can have different roles or explanations for different
claims; these uses remain separate. Different explanations cannot bypass duplicate
reference/role rejection within one claim. Editing an explanation changes the
entire draft hash, invalidating the old declared answer review and argument map.
Explicitly review and bind new artifacts; there is no automatic migration.

## Offline proposals: versioned v2 contract

The default proposal API and CLI still emit v1 with exactly two-field citations.
V1 rejects explanation fields, preserving previously recorded handoffs, imports,
reviews and argument envelopes. Request v2 explicitly:

```sh
python answer_proposals.py template package.json --question "Which synthetic comparison helps?" --topic "model design" --reference-year 2020 --operator-id synthetic-operator --include-citation-explanations > answer-scope.json
```

The Python equivalent is `template(..., include_citation_explanations=True)`;
non-boolean values are rejected. Selection remains empty until the operator supplies
exact evidence references. Then use the existing prepare, response-template,
import, review-template, review and export commands from
[answer proposals](ANSWER_PROPOSALS.md).

V2 scope, handoff, candidate bundle, review packet and exported answer envelope use
`.v2` schema names. Every citation in both an original proposal and an accepted,
rewritten claim must explicitly include `explanation`, even when null. An uncited
synthesis can still have an empty citation array and remains unsupported. Mixed
versions, missing slots, schema downgrades and changed handoffs fail validation.
No inference or upgrade occurs merely because extra fields appear.

Original candidate interpretations are labeled `UNTRUSTED_IMPORTED_INTERPRETATION`.
Accepted/revised interpretations are `OPERATOR_ADOPTED_IMPORTED_INTERPRETATION`, not
necessarily operator-authored text. Original, edited and rejected explanations all
remain in the full candidate/adoption history. Candidate review starts entirely
deferred and still requires explicit decisions. It is separate from final answer
review, which also starts deferred. No provider call or external transmission is
performed by these tools, and a prepared handoff grants no permission to send it.

## Follow the explanation through review

Answer text, proposal history, integrated source routes, reader disclosure and
passive HTML retain the explanation on its **specific citation use**, not on the
shared source record. Missing-explanation agenda entries identify claim ID, exact
reference and role. A declared `retain` never removes that missing prompt or
establishes scientific approval.

Argument source routes carry only each claim's own direct citation explanations.
Premise explanations do not transfer to an uncited conclusion. An argument handoff
over an enhanced answer includes those selected direct citations; existing v1
argument artifacts over legacy answers replay unchanged.

Pinned input cards hash the full new artifacts. Two-journey comparison shows an
explanation change in claim declarations and route uses, without calling the stored
source evidence changed. A missing prompt in the next report is not proof that the
scientific concern was resolved. Fresh source rechecking remains a separate local
byte/quote comparison and never verifies the explanation's meaning.

## Verification boundaries

Synthetic tests cover literal quote preservation, strict versions and fields,
original/adopted/rejected histories, stale bindings, exact reference/role isolation,
retained-but-missing explanations, direct-citation nontransfer, output escaping and
passive HTML snapshots. A frozen fixture captured from v0.55, before these edits,
checks exact legacy inspection/handoff/bundle/envelope replay and text hashes.

The standard synthetic walkthrough's v1 routes and outputs are unchanged. The new
v2 route is exercised separately through the actual CLI; no new automatic fixture
adoption flag is added. No real scholar data, semantic evaluation, model execution
or authenticated human review is included. Actual browser layout, keyboard and
print QA remains blocked/unverified; HTML checks are structural and snapshot only.

## Audit old and new declarations without changing them

The separately invoked [citation reasoning audit](CITATION_REASONING_AUDIT.md)
accepts legacy manual and imported v1 drafts as well as enhanced v2 drafts. It
surfaces the absent/null/declared distinction without inserting fields or prompts
into existing inspections. Final rejected/deferred claims remain current records;
original candidate history stays separate from use counts. No draft, review, argument
map or handoff is upgraded or rebound.
