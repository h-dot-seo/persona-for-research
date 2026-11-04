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

## Focus on one active bridge

Use `--step-id` to co-locate one existing active bridge with its complete endpoint
claim records and their **direct** citations:

```sh
python argument_map.py package.json draft.json argument.json --step-id synthetic-step --format text
python argument_map.py package.json draft.json argument.json --step-id synthetic-step > selected-step.json
```

Supply the same `--review review.json` used by the map when applicable. Selection
uses the exact adopted/manual step ID, not a candidate ID, array position or rejected
proposal ID. It cannot be combined with `--template`. Unknown IDs and empty maps
fail explicitly. Several bridges can share a conclusion; selecting one gives it no
priority or approval.

The focused view is a **navigation companion, not a complete report or archive**.
It retains the selected step's rationale, assumptions, defeater, missing fields
and imported original/reviewed origin; premise order; full endpoint claim text,
uncertainty and exact source/citation/explanation records; and separately labeled
answer-review decisions and notes. Original declaration order remains separate
from deterministic review order. Upstream nonendpoint claims are not silently
included as premises. An uncited conclusion stays `NO_CITATIONS_SUPPLIED`.

Explicit omitted-scope information identifies the other steps and claims and
notes that complete answer/argument proposal, rejected-candidate, review and
recorded-preparation histories are not embedded. A full-report reference binds
the complete fresh inspection and all original JSON-compatible inputs, including
absent versus supplied answer review. These are JSON-content hashes, not raw file-byte
hashes. A digest identifies content but does not make it available,
authenticate it or approve it. No companion file is created or guessed. To read or
save the complete report, repeat the command with the **same raw input files** and
without `--step-id`:

```sh
python argument_map.py package.json draft.json argument.json --format text
python argument_map.py package.json draft.json argument.json > complete-argument.json
```

Include the same review option on those commands too. Retain the original raw
inputs and the ordinary complete report when durable history is needed. Do not
feed the focused view back as an argument map, adoption decision or cached
inspection. Public `inspect_step(...)` and `render_step(...)` take raw package,
draft, map, exact step ID and optional declared review, not a saved report.

The complete ordinary map is freshly inspected **before** selection. Invalid
unselected active steps and stale full-history bindings still fail. The focused
mode also caps the complete indented inspection JSON, including its final newline,
at 16 MiB before projection, and separately caps focused JSON/text at 16 MiB.
Both companion encodings are checked even when JSON is requested.
These are focused-mode bounds; existing default map behavior is unchanged. It does
not generate the entire text report merely to make a JSON selection. Nothing is
silently truncated.

The view performs no source reread, current journey-context comparison or method-use
review. Recorded answer-preparation context remains historical. It does not infer
journey routes, a method-to-argument link, citation inheritance, source independence,
logical validity or researcher agreement. Use the full journey for those supplied
contexts and keep its review boundaries in force.

## Read one bridge back to its basis

Follow [Review the basis of one bridge](ARGUMENT_PROPOSALS.md#review-the-basis-of-one-bridge)
for the contextual walkthrough's `late` step. It follows exact claim/reference/role
uses, distinguishes the design step `compare`, and records a fresh note-only,
all-deferred assessment without treating fixture adoption as reader approval.
