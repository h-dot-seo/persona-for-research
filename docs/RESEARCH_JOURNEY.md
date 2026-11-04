# Source-to-method-to-argument review journey

The integrated reader connects an explicit question and target context to supplied
publication chronology, source/review relationships, a selected method-pattern
hypothesis, proposed design steps, draft claims and an operator argument map.
It **does not generate research or speak as the researcher**. Every result remains
`HUMAN_REVIEW_REQUIRED_NOT_RESEARCH_APPROVAL`, including fully retained claims.

## Try the complete synthetic route

```sh
python synthetic_walkthrough.py ../persona-research-journey --candidate-source offline-import --research-journey
```

Choose a new directory outside the repository with an existing parent. The runner
never overwrites a prior run. It executes **27 actual CLI stages**, with argument
arrays and return codes in `commands.json`. Start with `research-journey.txt` and
`pattern-review.txt`; `research-journey.json` contains the structured report.
Completion requires exit code zero and `COMPLETE.json`. A late failure leaves
`FAILED.txt` and partial artifacts, never a completion marker. Retry in a new folder.

The extended route adds ten stages to the existing 17-stage offline-import demo:

1. Prepare a topic-bounded pattern handoff with reference-specific evidence reasons.
2. Create an empty response, fill it with two **canned invented** proposals and
   import it with clearly synthetic, unauthenticated provenance.
3. Generate an all-deferred pattern-review template. Explicit fixture decisions
   accept one synthetic proposal and reject the other. Both original explanations
   and the separately supplied reviewed explanations remain visible. These fixed
   demo decisions are not a general auto-approval implementation.
4. Render that review and export its complete replayable pattern-review envelope.
5. Create a target-context form, retaining one synthetic exclusion and one defer.
6. Create a publication-relationship form and add an explicitly unverified
   review-summary relation based on the later synthetic source. A supplied review
   article label is not evidence of an authenticated peer-review report.
7. Compose the integrated JSON and text reports using the same declared answer
   review and argument map. Every answer claim remains deferred.

The records intentionally retain a missing pattern/design falsifier, missing
argument defeater, an uncited conclusion, excluded/deferred applicability and
later-publication context. They are not silently repaired. No actual LLM, source
provider, real publication, scholar, empirical study or scientific execution is
used. The shorter existing 15/17-stage modes remain unchanged. Omitting
`--candidate-source offline-import` with the extension runs 25 stages using the
original mock reasoning candidate route; pattern candidates are still canned.

## Compose your own supplied artifacts

```sh
python research_journey.py package.json patterns.json context.json links.json design.json answer.json argument.json publication-relations.json --pattern-id selected-pattern --review answer-review.json --format text
```

Without `--format text`, output is JSON. The command reads explicit paths and writes
only stdout. Keep artifacts outside the public repository and review privacy and
quotation rights before sharing them. Without explicit live-source options it does not follow paths stored in the JSON
or open source files. It never contacts a provider or executes scientific steps.

- `package`: a current bound package, including supported imported-observation or
  reasoning-component origin markers. A supported package wrapper is also allowed.
- `patterns`: a manual pattern form or reviewed imported-pattern envelope. Imported
  envelopes are replayed, not flattened into apparently manual text. Original and
  reviewed explanations plus rejected proposals are retained when supplied.
- `context`: an explicit applicability form. Its topic and reference year define
  the trajectory view. Topic matching is exact case-insensitive; no fuzzy retrieval
  or inference about the intended topic occurs. A no-match topic remains no-match.
- `links`, `design`, `answer`: existing bound forms. Links bind to the package;
  context, design and answer must have exactly equal question text. Equal text is
  only an integration constraint, not proof of equal intended meaning.
- `argument`: the operator argument map bound to the exact draft and optional review.
  Use an explicit empty map to disclose no supplied argument steps.
- `publication-relations`: an explicit bound relation form. An empty relations array
  is allowed and disclosed. Missing relations do not establish independence.
- `--review`: optional complete declared answer review. When omitted, the argument
  must also be bound to no review. Stale or mismatched review artifacts fail closed.

Prepare these forms with the respective template CLIs documented in
[pattern proposals](PATTERN_PROPOSALS.md), [context review](APPLICABILITY_REVIEW.md),
[reasoning links](REASONING_LINKS.md), [design scenario](DESIGN_SCENARIO.md),
[answer drafts](ANSWER_DRAFT.md), [argument maps](ARGUMENT_MAP.md) and
[publication context](PUBLICATION_CONTEXT.md). No form is silently rebound or filled.
The existing pattern-transfer CLI also accepts `--review answer-review.json`, so
its detailed answer/design section no longer needs to lose the supplied decisions.

## What the joined index means

`evidence_routes` is a deterministic union of exact paper/observation/component
references present in the supplied review views. Parent observations and their
components are different references. Each route retains its resolved source record,
original claim/stance, quote/locator, conditions, limitations, date, recorded checks
and supported provenance. It separately lists:

- Topic-timeline inclusion, selected pattern roles and reviewed evidence reasons.
- Exact observation assessments and explicitly supplied context counterevidence.
- Publication-relationship basis uses, including references outside the selected
  topic or pattern. A relationship basis is not active answer/design evidence.
- Draft citation uses with declared retain/revise/reject/defer decisions, design
  link uses and unused links. Rejected/deferred draft claims remain in this supplied
  use inventory. Nothing is presented as a selected approved answer.
- Argument premise/conclusion roles **only through direct citations of that claim**.
  An uncited conclusion stays uncited even if every premise has citations. Multiple
  uses, dual support/challenge roles and several steps remain separate entries.

`actively_used_in_answer_or_design` is true only for an actual supplied answer
citation or used design link. Timeline/pattern/context/relationship inclusion alone
cannot set it. The active-publication context, selected-pattern context and topic
context keep their different paper selections; none adds independent corroboration.
Publication/reference-year warnings do not date the relationship assertion or prove
historical availability, influence, personal beliefs or a change of mind.

`review_agenda` collects domain-specific missing fields, deferred/rejected review,
missing citations, contextual gaps and publication-year prompts. It is a navigation
aid, not an exhaustive review, fault list, severity ordering or readiness score.
The full subreports remain available; nothing is approved when the agenda is empty.

## Integrity and limits

All forms undergo their existing complete package, authorization, recorded-check
and schema validation. A hash of every supplied input, including the answer review,
argument, relationships and selected pattern ID, identifies the composed request.
Hashes establish byte/content consistency, not truth, authenticated identity,
semantic support, rights clearance or review quality. Changing notes or relationship
uncertainty changes the request hash even when evidence references stay the same.

Inputs are detached JSON data, with an 8 MiB file limit and an 8 MiB aggregate
serialized request limit. Duplicate keys, non-finite numbers and excessive nesting
are rejected. Output is capped at 16 MiB with no partial stdout on failure. Narrow
artifacts explicitly rather than expecting silent truncation. Text fields are
escaped; shell-looking instructions remain text, not executed commands.

This report is **not a complete provenance archive**. It preserves origin markers
and the complete imported pattern review that are actually supplied. It does not
receive or replay prior observation/reasoning extraction stage bundles. Use the
separate observation/reasoning lineage audits for those stages and keep their inputs.
`provenance_history_replay` remains `NOT_PERFORMED`; current no-provider flags cannot
establish whether an earlier model was used. Identities and review decisions are
recorded declarations, not authenticated human review. Real-researcher fidelity and
scientific validity remain unevaluated.

## Optional current original-source check (v0.45)

Use `--source-selection source-selection.json --source-root local-sources` together
to reread explicitly selected source files during this invocation. The selection
must bind to the current package and cover every supplied paper. The separate
current check is shown near the top and on each exact-reference route; gaps remain
in the agenda. Historical subreports and recorded labels are not rewritten.

Without these options, the original no-source path and bindings remain unchanged.
A cached audit report is not an input option. Byte mismatches fail closed; valid
missing/unmatched quote records generate review gaps, not approval. See
[current local source recheck](SOURCE_RECHECK.md) for templates, limits and the
30-stage synthetic demonstration. This new check still does not replay prior
extraction history, establish authenticity or evaluate scientific support.

## Optional declared method-pattern use (v0.46)

Pass `--method-applications method-applications.json` to include an explicit,
bound pattern-to-step application form. It records considered/excluded/deferred
intent, step-specific conditions, proposed checks and failure criteria. A shared
reference alone does not supply this declaration. Application annotations never add
answer citations, design uses, active evidence or inherited argument support.
Existing decisions remain unchanged, including conflicts with excluded context.

Application validation precedes optional live source reads. No-application behavior
is unchanged. See [method application](METHOD_APPLICATION.md) for the all-deferred
template, exact-reference rules and 32-stage synthetic source-plus-application demo.

## Imported method-application intent

For the practical pattern-to-design proposal/review path, add `--import-method-use`
to the extended demo with `--review-method-use`. Combined with offline-import
extraction, the integrated journey and live synthetic source recheck, this executes
38 CLI stages. Read `source-recheck.txt`, then `application-proposals.txt` to compare
original versus explicitly reviewed rationale and rejected alternatives. Both
pattern and application histories remain visible. Checks are proposed, not executed;
source matches do not approve methods and all answer claims remain deferred.
See [application proposals](APPLICATION_PROPOSALS.md) for standalone commands,
separate candidate/application decisions, export conditions and verification bounds.

## Passive local review view

Use `research_journey.py ... --format html` with the same original inputs for a
single read-only local view. It inspects once, preserves every field in a reversible
snapshot, links only exact references, and has no scripts, external resources or
approval controls. Add `--html-review` to the synthetic extended demo for one extra
CLI stage (39 with all current options). Existing JSON/text modes are unchanged.
The static/security/CLI checks are automated; actual-browser visual, keyboard and
print QA is currently blocked by the cloud environment's socket restriction.
See [local HTML review](LOCAL_HTML_REVIEW.md) for the reading order, privacy limits
and precise verification scope.
