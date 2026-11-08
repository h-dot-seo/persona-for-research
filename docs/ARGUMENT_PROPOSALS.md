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

## Review the basis of one bridge

For a worked bridge-first reading path, run the complete command above with
`--contextual-answers` added, in a new output directory. This is the existing
53-stage synthetic contextual walkthrough, not a new generator mode. It uses v3
answer context with default v1 argument artifacts; the [opt-in v2 argument
handoff](#opt-in-recorded-answer-context) is a separate capability. Read
`START_HERE.txt`, then use `research-journey.json` alongside the text reports.
The fixture's accepted bridges demonstrate recorded decisions, not your approval.

For a compact companion to steps 1 and 2 below, set `RUN` to that output directory
and select the active step explicitly:

```sh
python argument_map.py "$RUN/revision.json" "$RUN/draft.json" "$RUN/argument.json" --review "$RUN/answer-review.json" --step-id late --format text
```

The [focused bridge view](ARGUMENT_MAP.md#focus-on-one-active-bridge) puts its endpoint
claims and direct citations beside the bridge. It discloses omitted full histories
and identifies the complete fresh report; it does not replace the journey's exact
routes, method context, current source checks or full proposal review below.

1. **Start at `late`.** Find `argument_review.steps[]` by `step_id`, not array
   position. Its reviewed bridge connects `comparison` to `conclusion`: “The canned
   reviewer proposes choosing an observation only after the synthetic comparison.”
   Its assumption is “The proposed comparison can identify a discriminating
   observation.” The `defeater` is null and remains a missing field. Compare
   `proposal_origin.original_proposal` and `proposal_origin.review_note` with the
   reviewed fields; do not mistake the original canned rationale for the revision.
2. **Read the endpoint claims and their direct citations.** In
   `argument_review.answer.claims[]`, both endpoints are `operator_synthesis`;
   upstream `criterion` is `source_quote`. `comparison` cites
   `synthetic-0` / observation `0` / `alternative_explanation` as `support`, with
   the revised supplied explanation “Revised canned interpretation of this
   synthetic comparison citation only.” Its boundary says applicability remains
   untested. Its `challenge` citation is `synthetic-1` / observation `0` /
   `falsification_check`, with a null explanation. For each citation, inspect
   `evidence.observation.condition`, `evidence.observation.limitation`, source
   kind/year/locator/attribution and `evidence.component.claim_type`. The support
   component is `operator_interpretation`, the challenge component
   `explicit_statement`; neither label establishes applicability.
3. **Follow exact uses, keeping the roles separate.** Match the full citation
   `citations[].evidence.reference` against `evidence_routes[].evidence.reference`,
   then select
   `direct_argument_uses` by all four fields: `step_id=late`,
   `claim_id=comparison`, `argument_role=premise`, and the citation's own
   `citation_role` (`support` or `challenge`). The challenge reference is also
   `criterion`'s context citation. Although that claim is upstream and not a
   `late` endpoint, the same reference **is** a direct late-premise challenge
   through `comparison`. Do not flatten these uses or substitute a parent
   observation for a component. `conclusion` has no citations; no premise citation
   transfers to it and repeated references do not establish independent support.
4. **Consult method context without making a new link.** The routes' pattern,
   context and method-application uses are navigation into the supplied reviews.
   `method_application_review.applications[]` concerns design `step_id=compare`,
   not argument `late`. Read its conditions and proposed checks with the selected
   pattern and applicability review. Shared references do not endorse the bridge
   or create a method-to-argument relationship. Recorded answer-preparation context
   remains historical, even when its hashes match current inputs. Quote/file
   matches do not settle applicability, the missing defeater or the all-deferred
   final answer review.

**Record a bounded assessment without adopting anything.** From the repository,
set `RUN` to that output directory and use a new, unused filename:

```sh
python argument_proposals.py review-template "$RUN/revision.json" "$RUN/draft.json" "$RUN/argument-candidates.json" --reviewer-id reader --answer-review "$RUN/answer-review.json" > "$RUN/reader-argument-review.json"
```

In the fresh template, locate the candidate identified by `late`'s
`proposal_origin.candidate_id` (`argument-candidate-1` in this fixture). Change
only its `review_note`, for example: “Bounded review of the fixture's late bridge:
comparison has separate support and challenge citations; the challenge explanation
and bridge defeater are missing. Applicability remains untested. Keep deferred.”
Leave every decision `defer`; do not add `reviewed_step`. Inspect without export:

```sh
python argument_proposals.py review "$RUN/revision.json" "$RUN/draft.json" "$RUN/argument-candidates.json" "$RUN/reader-argument-review.json" --answer-review "$RUN/answer-review.json" --format text
```

The note changes no decision and creates no new source/citation scope or basis
relationship.
All-deferred review is inspectable and cannot export. Keep the original fixture
adoption, envelope and reports separate. Do not edit an exported envelope and
assume its hashes or pinned inputs remain valid. If you later accept a revision,
supply every `reviewed_step` field explicitly (`step_id`, `premise_claim_ids`,
`conclusion_claim_id`, `bridge_rationale`, `assumptions` and `defeater`), resolve
every candidate, and follow normal review/export and downstream rebinding.
No proposed text is filled in for you.

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

## Opt-in recorded answer context

When the draft is a reviewed **v3 contextual answer**, you may explicitly include
its recorded preparation/import context while proposing argument links:

```sh
python argument_proposals.py template package.json draft.json --operator-id synthetic-operator --answer-review answer-review.json --include-recorded-answer-context > contextual-argument-scope.json
```

Select existing claim IDs yourself, then use the same prepare/import/review/export
commands above and below with that new scope. The template still selects no claims.
The Python option is `include_recorded_answer_context=True`. It creates distinctly
versioned v2 argument artifacts; mixing or downgrading schemas fails. Omission or
false keeps v1 unchanged, even when the answer already contains v3 context. Explicit
inclusion is rejected for drafts without recorded v3 context; none is invented.

The added material is rebuilt from the validated answer envelope. It preserves the
original method-pattern reasoning, applicability assessments, counterevidence,
publication chronology/relationships and excluded/unselected/rejected context,
with their original bindings and historical exact-reference scope. Read it as
**recorded answer-preparation/import context**, not newly supplied or current
argument context. It does not prove that those records influenced an answer or
that a method should govern the proposed argument.

That nested answer scope may contain sources outside the selected argument claims.
It grants no new argument endpoint, citation or source-selection permission. The
candidate contract is unchanged: only explicit existing claim IDs may be premises
or conclusions; no new claims or automatic citation transfer are added. Free-text
bridges and assumptions still require semantic and attribution review.

The local review text preserves the recorded context and complete bridge adoption
history. A later research journey still compares the answer's recorded context
with separately supplied current forms. Different current context is allowed and
disclosed by that existing comparison; it neither replaces the recorded context
nor silently rebinds this argument. To change recorded inputs, create and explicitly
review new bound artifacts. No separate current-argument-context workflow is added.

Additional histories may contain private quotations or annotations. Opting in
requests local inclusion only, not permission to transmit or redistribute them.
No provider, source reread, new source-check receipt, automatic adoption or scientific
execution is attached. All original identity and review declarations remain
unauthenticated. Candidate adoption does not approve the argument or final answer.

The existing 8 MiB combined input, 2 MiB handoff and 16 MiB report/text limits remain.
V2 report checks include the full indented JSON representation, not only compact
data. Including more history can exceed the limits. Failure is explicit; no context
is truncated and no automatic fallback to v1 occurs. Existing synthetic walkthrough
options and stage counts are unchanged.

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
