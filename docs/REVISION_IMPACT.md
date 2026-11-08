# Trace old answer/design evidence after manual reassessment

After [revising a manual observation](MANUAL_EVIDENCE_REVISION.md), old answer,
link and design bindings must not be edited to make them pass. Before rebuilding
those artifacts, compare their old evidence uses with the new package:

```sh
python revision_impact.py ../my-review/package.json ../manual-reassessed-result.json ../my-review/links.json ../my-review/design.json ../my-review/answer.json --reference-year 2020 --format text
```

The current input can be a package or the existing local-loader envelope. The old
links, design and answer must validate against the **previous** package and use
exactly the same question. Invalid old artifacts reject instead of being treated
as an editable draft. The reference year is supplied explicitly. Both packages
must have the same scholarly identity and valid publication years, including
unused papers. Training/holdout and bound-package checks remain in force.

## What the report tracks

For every exact paper/index/component reference used by the old answer or supplied
links, including unused links, the report shows:

- `CHANGED_AT_SAME_REFERENCE`, `MISSING_AT_REFERENCE`, or
  `UNCHANGED_AT_SAME_REFERENCE`.
- Before/after source hash, publication kind/year, stored quote, observation
  method/condition/limitation, stance, claim label and component provenance.
- Changed endpoint field names and, for missing evidence, whether the paper,
  observation index or component is absent.
- The old answer claims and citation roles that used it; old design steps, link
  relations and proposed-use roles remain separate declarations.
- Before/after publication scope relative to the requested year.

The synthetic regression revises an explicit_statement to operator_interpretation.
A claim using the affected component and a design step using a link to that
component are marked affected even though the component text itself is unchanged:
its enclosing observation's attribution/limitation changed. The review
counterargument remains visible with its old citation/link-use roles, not silently
promoted, discarded or reclassified. Missing components and papers remain visible.

This report detects exact record changes, not whether the old claim is wrong or
the new evidence supports it. Different source bytes may warrant review without
changing meaning. Unchanged bytes and fields may still be scientifically inadequate.
No fields are filled, new claims/citations generated or source bodies reread.

## Scope is deliberately narrow

Matching uses the same **paper ID, observation index and dimension**, not semantic
identity. Reordering or inserting observations can change which record is at that
position; inspect the before/after content. Identical duplicate observations cannot
be disambiguated. There is no automatic alignment, migration or proof that two
records refer to the same scientific proposition.

The catalog in a review workspace lists all available references. This impact
report compares only references actually used by its old answer or links, not all
catalog entries, all changed corpus evidence or all missing counterarguments. An
empty starter therefore produces zero compared references, not an impact clearance.
`affected_*` IDs refer only to detected changed/missing endpoints. An unreferenced
link can be affected without identifying an affected answer claim or design step.

Whole-package binding changes are shown separately. Even when every compared
endpoint is unchanged, a new version/build makes old artifacts stale and requires
fresh bound artifacts and manual review. Do not just replace their hashes. The tool
never writes a new answer, link, plan, review decision or package. Initial and
current package check labels are historical records, not newly verified source or
reviewer claims. Operator IDs and before/after records remain unsigned declarations.

All output may include private quotations, identifiers and annotations already
present in input. Keep it private; this is not sanitization, rights clearance or
permission to republish excerpts. It does not certify a real scholar's thought,
individual authorship or scientific validity, and uses no LLM, network or API.

```sh
python -m unittest tests.test_revision_impact -v
```

## Imported answer scope

For a [reviewed answer envelope](ANSWER_PROPOSALS.md), the previous full proposal
history is included without rebinding to the current package. Stale-binding flags
also compare complete checked-package hashes, because imported scopes bind more
than persona/papers alone. A package metadata change can require binding review
while every compared evidence reference remains unchanged.
