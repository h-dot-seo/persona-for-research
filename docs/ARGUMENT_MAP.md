# Inspect a declared premise-to-conclusion argument

An answer claim can cite a paper without explaining the proposed bridge from that
paper to a new conclusion. This map makes the **operator's** bridge, assumptions
and possible defeater inspectable. It is not an author's private reasoning, a model
chain of thought, or an automatically generated argument.

```
python argument_map.py package.json draft.json --template --operator-id synthetic-operator > argument.json
# Add explicit steps, then inspect them:
python argument_map.py package.json draft.json argument.json --format text
```

If the draft has a recorded review, use `--review review.json` for **both** template
and inspection. The map binds the draft hash and optional review hash; modifying a
claim, question, citation or recorded review requires a new map binding and review.
A null review hash means no review was supplied, not that the claims were approved.

Each step has exactly these fields (claim IDs must already exist in the draft):

```json
{
  "step_id": "synthetic-step",
  "premise_claim_ids": ["criterion-quote", "comparison-idea"],
  "conclusion_claim_id": "proposed-conclusion",
  "bridge_rationale": "The operator proposes applying the criterion to this comparison.",
  "assumptions": ["The synthetic models predict different observable outcomes."],
  "defeater": null
}
```

A step needs a nonempty premise list and bridge rationale. Premises can be stored
source quotations or operator syntheses. A conclusion must be `operator_synthesis`:
a derived inference cannot manufacture an original source quotation. Unknown,
duplicate or self-referencing premises and duplicate step IDs are rejected.
Assumptions must be an explicit list (possibly empty); a defeater may be null.
Empty/null means **not supplied**, never that no assumptions or counterexample exist.

The declared dependency graph must be acyclic. Circular dependencies reject rather
than receiving a misleading review order. The deterministic order uses original
answer order for ties; it is not importance, chronology, causal influence or proof
of deduction. Several steps may propose alternative bridges to the same conclusion.
They stay separate and do not increase an evidence or confidence score. Identical
premise/conclusion paths under different step IDs are not deduplicated or scored.

For each step, the reviewer sees premise and conclusion claim types, recorded
retain/revise/reject/defer decisions, direct citation-entry counts, uncertainty and
missing assumptions/defeater. The complete answer follows with source locators,
research/review kind, publication year, claim labels, mock provenance and quote
checks. Direct citation counts count supplied entries, not independent sources.

Citations in a premise are **not automatically transferred** to a conclusion. An
uncited conclusion remains `NO_CITATIONS_SUPPLIED` even when its premise has a
citation; the supplied bridge still needs semantic review. Rejected/deferred
premises remain visible, not silently removed or promoted. Claims outside the map
are listed as unmapped; premise-only claims are not declared axioms or facts.
A retain decision about an answer claim does not approve the new logical step.

The synthetic CLI journey combines a later review's criterion with an earlier
research interpretation and a proposed third answer claim. It exposes the missing
defeater and uncited conclusion while preserving each source claim's actual label:

```
python -m unittest test_argument_map -v
```

No LLM, source reread, external API, real scholar corpus or fidelity evaluation is
used. Real logical and scientific assessment requires authorized sources and
independent review. An acyclic, fully filled map is not a scientific certification.

## Explicitly adopted imported bridges

[Argument proposals](ARGUMENT_PROPOSALS.md) prepare an offline handoff over explicit
existing answer claim IDs, import tentative bridges and preserve complete adoption
history. Use its reviewed envelope as the map input. Accepted bridge origin is
separate from manual authorship and imported answer origin. Declaration order is
kept apart from topological review order; cycles are rejected only for the accepted
map, not treated as proof of logical validity. Rejected suggestions never become
direct argument uses. Manual maps retain their original behavior and output shape.
