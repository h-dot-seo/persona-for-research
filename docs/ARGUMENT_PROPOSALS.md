# Offline proposals for declared argument links

`argument_proposals.py` prepares a local AI/Codex handoff for tentative links
between **explicitly selected existing answer claims**. It can import bridge
rationales, assumptions and defeaters for explicit review without creating new
answer claim records, selecting evidence, speaking as a researcher or reconstructing private
reasoning. No provider is called. A structurally valid graph is not a logically
valid argument or an approved research plan.

## Try the opt-in synthetic route

```sh
python synthetic_walkthrough.py ../persona-argument-demo --candidate-source offline-import --research-journey --import-arguments
```

This runs 34 real CLI stages. The new flag requires `--research-journey`, adds seven
stages and accepts no external candidate/review file. Fixed invented candidates
link the existing `criterion`, `comparison` and `conclusion` answer claims. Two
explicit fixture steps are adopted and one cyclic alternative rejected. These are
canned demonstrations, never a reusable automatic-review policy. The declaration
places the late step before the early one, while graph review presents early then
late; each retains the correct original proposal and reviewer note.

For the complete source → pattern → method → answer → argument path, run:

```sh
python synthetic_walkthrough.py ../persona-complete-argument-demo --candidate-source offline-import --research-journey --recheck-sources --review-method-use --import-method-use --html-review --import-answers --import-arguments
```

That executes 53 stages with pattern, method-application, answer and argument
proposal histories, fresh invented source-file checks and a passive HTML report. Read the scope first, then `argument-proposals.txt`
and `argument-map.txt`. Final answer decisions remain all-deferred; missing checks
and defeaters stay visible. No assumption or bridge is logically verified.

`--import-arguments` does not require `--import-answers`, method-use or source-check
flags. With mock extraction and only the required journey it runs 32 stages. Earlier
39-stage and imported-answer 46-stage modes remain unchanged without the new flag.
The runner writes only to a new external directory, retains failed-stage diagnostics
and never writes COMPLETE after a failed command. It invokes no provider or browser.
For independently authored material, use the explicit manual workflow below instead
of modifying fixture code into an automatic approval tool.

## Select claims, not an inferred train of thought

Start with the original validated package, an answer draft or reviewed answer
proposal envelope, and an optional separately declared answer review:

```sh
python argument_proposals.py template package.json draft.json --operator-id synthetic-operator --answer-review answer-review.json > argument-scope.json
```

The scope template has empty `selected_claim_ids`. Explicitly select unique existing
claim IDs. No selection is inferred from citation counts, retained decisions,
source stance, method patterns or publication chronology. A selected claim can
still be rejected or deferred in the separate answer review; those labels remain
visible and are not promoted to approval. Supply the same optional answer-review
file on every later command. Absence is a distinct bound state, not an empty review.

```sh
python argument_proposals.py prepare package.json draft.json argument-scope.json --answer-review answer-review.json > argument-handoff.json
python argument_proposals.py response-template package.json draft.json argument-scope.json argument-handoff.json --answer-review answer-review.json > empty-argument-response.json
```

The handoff binds the complete checked package, original draft/envelope, explicit
review presence/content and selection scope. It includes the bound question, selected active claims,
their direct citations and declared review/origin labels. This is a **selected
context subset**, not complete original/rejected answer history, a complete source
corpus, or an account of the researcher's thoughts. Full input histories remain
hash-bound and available in the local review. Wrapper caches are not trusted.

Source quotations, answer prose and all annotations are untrusted data, never
instructions or permission. A handoff can contain private quoted material; creating
it does not authorize provider transmission, source access or redistribution.
Review source rights and data-sharing permission separately. Never put credentials
in artifacts or declared provenance labels.

## Candidate structure and explicit adoption

A response contains exactly `handoff_sha256` and `candidates`; an empty response is
valid. A candidate contains exactly:

- `premise_claim_ids`: explicit existing selected claim IDs, with no duplicates or
  self-premise. An inference never inherits their citations automatically.
- `conclusion_claim_id`: an existing selected `operator_synthesis` claim. A literal
  source quote cannot become an inferred conclusion.
- `bridge_rationale`: a proposed explanation of the connection, not a verified
  derivation or the researcher's own explanation.
- `assumptions`: explicit proposed statements. Empty means not supplied, not that
  the inference needs no assumptions.
- `defeater`: an explicit proposed failure condition or null. Null remains a gap.

The response contract has no fields for a step ID, decision, new answer claim
record or extra source. Free-text bridges and assumptions still need semantic and
attribution review; the code cannot prove they contain only supported assertions.
Prepare separate provenance with `provider_id`, `model_id`, `run_id`, `operator_id`
and `execution_location` (`local`, `remote` or `unknown`). These are bounded,
unauthenticated declarations, not evidence of actual model execution.

```sh
python argument_proposals.py import package.json draft.json argument-scope.json argument-handoff.json argument-response.json declared-provenance.json --answer-review answer-review.json > argument-candidates.json
python argument_proposals.py review-template package.json draft.json argument-candidates.json --reviewer-id synthetic-reviewer --answer-review answer-review.json > argument-adoption.json
```

Every candidate starts at `defer`. Record every decision exactly once:

- Accept requires a complete `reviewed_step`, including all candidate fields plus
  a unique explicit `step_id`. Supply all edited premises, conclusion, rationale,
  assumptions and defeater; there is no fallback to proposed text. Edited endpoints
  must still belong to the explicitly selected claim IDs.
- Reject/defer cannot contain a reviewed step. Original proposals, including rejected
  alternatives, remain in the historical record rather than active argument routes.
- Every decision needs a nonempty review note. Resolve all candidates and accept
  at least one before export. All-rejected, empty or pending reviews remain inspectable.

Individually legal candidates may be mutually inconsistent or jointly cyclic while
unadopted. The complete accepted projection must pass the existing argument map's
acyclic dependency check. That check is mechanical ordering, not logical soundness.
No candidate adoption authenticates a human reviewer or certifies the inference.

```sh
python argument_proposals.py review package.json draft.json argument-candidates.json argument-adoption.json --answer-review answer-review.json --format text
python argument_proposals.py export package.json draft.json argument-candidates.json argument-adoption.json --answer-review answer-review.json > reviewed-argument.json
python argument_map.py package.json draft.json reviewed-argument.json --review answer-review.json --format text
```

There is no new approval schema. `logical_validation` stays `NOT_PERFORMED`, all
conclusions and method choices still need human review, and any separate answer
review remains unchanged. No experiment, source fetch, canonical update or scientific
execution is triggered.

## Preserve origin and both kinds of order

The exported envelope retains the complete bundle and adoption review. Every
consumer rebuilds the original candidates and accepted map; cached inspections,
accepted counts or approval labels are not trusted. Original, rewritten and rejected
bridge text, notes and provider/model/reviewer labels survive JSON/text/passive HTML.
Adopted bridges are labeled `OPERATOR_ADOPTED_IMPORTED_ARGUMENT`, separately from
manual operator-authored maps and imported answer text.

`argument_map_sha256` identifies the full envelope; `argument_content_sha256`
identifies the plain accepted projection. Even a rejected note change alters full
identity and invalidates pinned input files. Changed answer history, package data,
selection scope or declared answer review requires new binding review. Nothing is
silently rebound or migrated.

`declared_step_ids` preserves accepted candidate order. The inspected `steps` use
the existing deterministic topological review order. Those orders are different:
neither is proof of real researcher chronology or reasoning. Reordering the adoption
decision array does not reorder adopted steps. Every reordered step retains the
origin of its own explicit step ID.

Use `reviewed-argument.json` in the argument slot of [research journeys](RESEARCH_JOURNEY.md)
and [input cards](JOURNEY_INPUTS.md). [Two-card comparison](JOURNEY_COMPARISON.md)
compares explicit step fields in declaration order, separately from candidate,
adoption and declared-import history. Manual/imported transitions preserve both full
reports. Rejected graph endpoints do not become direct argument uses. A claim can
still be active answer evidence independently of whether an argument uses it.

Current inspection invokes no provider and reports current `llm_used=false` with an
explicit execution scope. Historical generation stays declared/unauthenticated,
with unknown actual model use in the import record. Hashes, quote equality and
consistent labels do not establish scientific support, individual authorship,
rights clearance, independent corroboration or researcher fidelity.

## Bounds and verification limits

Proposal inputs use finite strict JSON with an 8 MiB combined bound, handoffs a
2 MiB logical UTF-8 JSON bound, and proposal reports a 16 MiB bound. At most 64 claims, 32 candidates,
64 premises per candidate and 32 assumptions per candidate are supported, with
existing 2,000-character rationale/assumption/defeater limits. The proposal CLI
bounds file reads, rejects duplicate JSON keys/nonfinite values and buffers complete
output before stdout. Existing consumers retain their own input/output limits.
Use new private output filenames; shell redirection can overwrite an existing file.

Tests use invented sources and canned proposals only. Missing assumptions,
defeaters, citations and review decisions remain visible. Passive HTML checks cover
escaping, internal structure and exact JSON snapshots, not visual/keyboard/print
behavior. Actual browser QA remains blocked and unverified; no retry or restriction
bypass is attempted.

## Enhanced citation context

Selected answer claims may carry [citation explanations](CITATION_EXPLANATIONS.md).
These remain exact direct-citation declarations with manual/imported origin labels;
they are not verified support or new argument decisions. Legacy answer inputs keep
identical argument handoffs and replay. Enhanced answer inputs have fresh hashes,
so an old map cannot be silently reused or rebound.
