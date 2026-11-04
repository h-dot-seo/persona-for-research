# Offline, evidence-scoped answer proposals

Use `answer_proposals.py` to prepare a local AI/Codex handoff for tentative answer
claims from an explicitly selected set of stored evidence. Import a separately
prepared response, record every candidate decision, and pass the reviewed envelope
through the existing answer, argument, research-journey and input-card workflows.
No provider is called and no source bytes are reread. This is a review bridge, not
a researcher chat, an endorsed answer or authenticated model/human provenance.

## Try the opt-in synthetic route

```sh
python synthetic_walkthrough.py ../persona-answer-demo --candidate-source offline-import --research-journey --import-answers
```

This runs 34 actual CLI stages. `--import-answers` requires `--research-journey`,
adds seven stages and accepts no caller-supplied response or review file. Three
fixed invented candidates are explicitly adopted and one is rejected by fixture
code, not a reusable automatic-review policy. The original comparison text differs
from its reviewed text. The rejected parent-observation citation remains historical;
all separate answer-review decisions stay deferred. Read `answer-proposals.txt`,
then `research-journey.txt` and the detailed `reader-scope.txt`.

To include fresh synthetic source checks, imported method-use proposals and the
passive local HTML report, run:

```sh
python synthetic_walkthrough.py ../persona-complete-answer-demo --candidate-source offline-import --research-journey --recheck-sources --review-method-use --import-method-use --html-review --import-answers
```

That runs 46 stages. Source, pattern, application and answer proposal histories
stay distinct. Seven new commands prepare scope/handoff/empty response, import,
create a deferred adoption form, render explicit fixture review and export the
history-preserving draft. The existing answer-review and argument commands then
bind the new envelope. No-flag modes keep their existing counts and outputs.
With mock extraction plus the required journey only, answer import runs 32 stages.
No model, provider, external transmission or browser runs in any mode. Source
rechecking reads only the explicitly generated invented local files.

Use a new directory outside the repository. Failed commands preserve diagnostics
and `commands.json` but never `COMPLETE.json`; retry into a new folder. Completion
is only a successful synthetic demonstration, not scientific or browser validation.
For independently authored material, follow the manual commands below instead of
modifying the demo into an automatic approval tool.

## Select scope before preparing a handoff

```sh
python answer_proposals.py template package.json --question "Which synthetic comparison could distinguish these explanations?" --topic "model design" --reference-year 2020 --operator-id synthetic-operator > answer-scope.json
```

The template contains the canonical checked package hash, explicit question, topic,
reference year, operator label, and an empty `evidence_refs` array. Supply 1–64 unique
exact references yourself. Each has `paper_id`, integer `observation_index`, and a
nullable `dimension`. A parent observation is not a substitute for a component.
No selected pattern, context decision, source, citation role or review decision is
inferred. The handoff is intentionally narrower than the full research journey:
it does **not** claim the imported text followed a pattern's reasoning or method.
Use the integrated review afterward to inspect those relationships explicitly.

```sh
python answer_proposals.py prepare package.json answer-scope.json > answer-handoff.json
python answer_proposals.py response-template package.json answer-scope.json answer-handoff.json > empty-answer-response.json
```

The handoff carries resolved selected evidence, recorded source labels, publication
year comparisons, and a strict response contract. Explicit references with other
topics remain visible; a topic label is not semantic relevance. Before/same/after
year labels do not establish historical availability, influence or independence.
Quotes and annotations are untrusted content, never instructions or permission.
**The handoff may contain private quotations. Creating it does not authorize source
access, provider transmission, storage or redistribution.** Review rights and data
sharing separately. Do not include credentials in any artifact or provenance label.

## Import a response, without importing its decisions

A response has exactly `handoff_sha256` and `candidates`. The template's candidate
array is empty; zero candidates is valid. Up to 32 candidates can each supply:

- `text`: bounded tentative synthesis or a literal stored quote.
- `claim_type`: `operator_synthesis` or `source_quote`.
- `uncertainty`: explicit text or null, which remains a review gap.
- `citations`: up to 32 exact selected references, each with an explicit `role`
  of support, challenge or context. Uncited synthesis remains visibly unsupported.

Candidate claim IDs and decisions are forbidden. `operator_synthesis` is the
existing answer schema's classification, **not proof that an operator wrote the
text**. Imported origin is recorded separately. No text is transformed into an
actual researcher's speech, private thoughts, recommendation or endorsement.
The tool checks structure and literal references, not these semantic properties;
a human must assess the wording, scientific support and attribution.

A source quote needs exactly one citation and exact equality with the selected
stored quote, without trimming or normalization. This does not establish current
source bytes, interpretation, authorship, copyright permission or individual credit.

Prepare declared provenance with exactly `provider_id`, `model_id`, `run_id`,
`operator_id`, and `execution_location` (`local`, `remote` or `unknown`). These are
bounded, unauthenticated labels, not proof of an actual provider run.

```sh
python answer_proposals.py import package.json answer-scope.json answer-handoff.json answer-response.json declared-provenance.json > answer-candidates.json
python answer_proposals.py review-template package.json answer-candidates.json --reviewer-id synthetic-reviewer > answer-adoption.json
```

## Record adoption explicitly, then conduct separate answer review

Every candidate starts at `defer`. Each needs exactly one accept/reject/defer and
a nonempty `review_note`.

- Accept requires a complete `reviewed_claim`: all four candidate fields plus a
  unique explicit `claim_id`. Supply all reviewed text, uncertainty and citations;
  there is no fallback to the proposal. References must stay in the selected scope.
- Reject/defer must not carry a reviewed claim. Original text and citation roles
  remain in the historical record but do not become active answer evidence.
- Resolve every candidate and accept at least one before export. Empty, unresolved
  and all-rejected reviews can be inspected but are not exportable answer intent.

```sh
python answer_proposals.py review package.json answer-candidates.json answer-adoption.json --format text
python answer_proposals.py export package.json answer-candidates.json answer-adoption.json > reviewed-answer.json
python answer_draft.py package.json reviewed-answer.json --format text
python answer_draft.py package.json reviewed-answer.json --review-template --reviewer-id synthetic-answer-reviewer > answer-review.json
```

Candidate adoption is **not** retain/revise/reject/defer answer review. The separate
answer review starts entirely deferred. Neither review is authenticated or scientific
approval. Argument maps must reference adopted claim IDs, never candidate IDs;
premise citations are never automatically transferred to conclusions. Recreate the
argument template with the explicit adopted envelope and separate answer review,
then manually assess its premises, assumptions, bridges and defeaters.

Pass `reviewed-answer.json` wherever an existing workflow expects a draft, including
`review_journey.py`, `argument_map.py`, `research_journey.py`, and the `draft` slot in
[journey inputs](JOURNEY_INPUTS.md). The question must match the separately prepared
design/context exactly. Adoption does not update these artifacts or select a method.

## History, bindings and current execution scope

The exported envelope contains the entire original bundle and adoption review.
Every consumer reconstructs both against the current checked package; cached
reports, approval flags and materialized accepted-only claims are not trusted.
Original proposals, reviewed claims, rejected alternatives, notes and declared
provider/model/reviewer labels survive JSON/text/HTML review. Adopted text and
citation roles retain imported-origin labels. Source-record origin is separate:
an imported answer does not turn an operator-curated source into a model source.

`draft_sha256` identifies the whole envelope. `draft_content_sha256` identifies the
accepted plain projection, not an independently reusable approval. Changing even
rejected history or a generation label changes draft identity and invalidates old
answer reviews, argument bindings and pinned input files. Changes anywhere in the
checked package invalidate the imported scope. Revision-impact reports preserve
previous history without rebinding and compare both complete package hashes for
imported answers, including changes outside the persona/papers projection.

[Two-card comparison](JOURNEY_COMPARISON.md) compares accepted claim declarations
separately from original candidate, adoption-decision and declared-import groups.
The latter groups are recorded history, not operator authorship or active evidence.
A transition between manual and imported drafts retains the old/new full reports.
IDs are local labels, not stable semantic or historical identity.

Current inspection reports `llm_used=false` with an explicit current-execution scope;
historical generation stays `DECLARED_NOT_AUTHENTICATED`, with unknown model-use
truth in the imported provider record. No API call, external transmission, source
reread, canonical update or scientific execution occurs. Optional fresh source
checking in a research journey is a separate explicitly selected operation.

Synthetic label evaluation freezes only adopted claim/citation metadata plus the
full envelope hash. It intentionally does not reproduce proposal text/history and
is not a provenance report or evaluation of researcher fidelity.

## Limits and validation

Combined proposal-function inputs are finite strict JSON bounded to 8 MiB,
handoff output to 2 MiB, and proposal reports to 16 MiB. Integrated journey/card
limits still apply separately. Claim text and uncertainty have 2,000-character
bounds; identity labels are bounded separately. CLI file reads are bounded, reject
duplicate JSON keys/nonfinite values, and write stdout only after complete success.
Use new private output filenames; shell redirection can overwrite an existing file.
No report truncation substitutes for complete history.

All tests and example executions use invented sources, canned suggestions and
explicit synthetic fixture decisions. They do not authenticate a human decision,
exercise a real model, verify scientific claims or validate researcher fidelity.
HTML checks are static parsing/escaping only. Actual-browser visual, keyboard and
print QA remains blocked and unverified; no restriction bypass is attempted.

## Explain each citation explicitly with v2

Add `--include-citation-explanations` only when creating the scope to request the
versioned v2 contract. Each original and adopted citation must include a nullable
explanation slot. Default v1 remains unchanged and rejects those additional fields.
See [citation explanations](CITATION_EXPLANATIONS.md) for rationale/context limits,
original-versus-adopted labels, missing prompts, full rejected history and replay
compatibility. The default synthetic walkthrough intentionally stays v1.

## Optional v3 method and publication context

Use [contextual answer preparation](ANSWER_CONTEXT.md) to supply explicit raw
pattern, applicability and publication-relationship forms with one selected pattern
ID. The v3 handoff preserves inspected context and history but keeps the v2 response
contract and exact citation permission boundary. All four context options require
explanation mode; omitted context leaves old v1/v2 records unchanged. Current journey
review inputs are compared separately with the recorded preparation context.

For a complete invented example, add `--contextual-answers` to the synthetic
`--research-journey --import-answers` route. Preparation precedes answer import,
then the journey reuses the same forms. All final judgments remain deferred.
See [the contextual walkthrough](ANSWER_CONTEXT.md#try-the-contextual-synthetic-walkthrough).
