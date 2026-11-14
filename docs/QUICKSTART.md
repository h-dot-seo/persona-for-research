# Run the complete synthetic journey

처음에는 이 합성 예제로 전체 흐름을 실행하세요. 실제 연구자 자료나 API 키는 필요하지
않습니다. 결과는 학자 재현이나 과학적 검증이 아니라, 근거를 보존하며 검토 파일을
연결하는 작동 예시입니다. 실제 LLM은 호출하지 않습니다.

Python 3.10+ only; no third-party packages, account or network access required.
From the repository root, choose a **new directory outside this repository** whose
parent already exists. Do not create the final directory first:

```
python synthetic_walkthrough.py ../persona-synthetic-demo
```

The same script works from another working directory when called by its full path.
Spaces and Unicode in the destination are supported. Do not put output under the
repository: the publication inventory deliberately rejects unlisted artifacts.
The runner rejects existing files/directories (even empty ones), missing parents
and symlink path components. It never overwrites or deletes an earlier run.

## What to read first

Open the generated `START_HERE.txt`. Read these files in order:

1. `reader-scope.txt`: answer draft, uncertainty, declared review state, source groups
   and active/unused scope. It is not an approved final answer.
2. `review-packet.txt`: which exact source record each answer claim and design step
   uses, including counterevidence and publication-year warnings.
3. `argument-map.txt`: explicit operator premises, bridge and assumptions. The
   missing defeater and uncited conclusion remain visible.
4. `timeline.txt`: the two synthetic publication dates and research/review labels.
5. `lineage.json`: replay of the single declared candidate review, not full
   history authentication or scientific approval.

Success requires exit code zero **and** `COMPLETE.json`. Its status ends in
`NOT_VALIDATED`; answer review is `ALL_DEFERRED`. These are intentional safeguards,
not missing setup. The demo executes 15 existing CLI commands and records their
actual argument arrays and return codes in `commands.json`. Those arrays are a
reproducibility/debug record, not shell commands to paste blindly.

## What the demo actually does

The bundled corpus contains invented observations and short synthetic quotations.
The runner supplies a later review criterion and a challenge stance, then:

- Runs observation intake with exact stored quote/segment checks.
- Calls the canned-response `MockProvider`, **not an LLM**.
- Shows a deferred candidate review template and available targets.
- Applies two **fixed synthetic fixture decisions** to a new revision. This is not
  a general auto-approval rule; both reviewed claims remain operator interpretations.
- Creates bound link, design, answer and argument templates, then fills them with
  explicitly invented operator text in the runner.
- Leaves every answer review deferred. It preserves missing design falsification
  and alternative explanation, missing argument defeater and an uncited conclusion.
- Executes timeline, integrated review, reader-scope, argument-map and lineage CLIs.

The question asks how to distinguish two synthetic explanations. Its later review
criterion is deliberately used with an earlier reference year so the timing warning
is easy to see. Source hashes are fixture declarations, not new file-byte checks or
proof of scholarly authenticity. No real author corpus or withheld evaluation is used.

## Failures and retry

If a stage fails or times out, the runner exits nonzero, attempts to save `FAILED.txt`
and `commands.json`, and does not write `COMPLETE.json`. A command with a null return
code was attempted but did not return normally. Earlier successful artifacts stay in
place for diagnosis; they do not establish a complete run. No failed stage is retried
automatically. If the filesystem itself prevents error-file writing, stderr remains
the failure report. Choose a different new destination after resolving the error.

An existing destination is always refused. Nothing is cleaned up automatically.
Keep generated outputs private when using related tools on your own authorized
material. This demo accepts **no corpus, provider or credential argument**, so it is
not a shortcut for sending actual research material to a model.

## Move beyond the demo deliberately

The runner is a fixed educational scenario, not a generic corpus wizard. Do not
reuse its synthetic accept decisions for real candidate outputs. For real work,
resolve author identity and source rights, choose training/holdout scope, curate
observations and review each candidate explicitly. Real human review is not
established by writing a reviewer name. Start with the tested
[own-file teaching tutorial](TUTORIAL_OWN_FILES.md) for multiple topics, source-file
intake and manual pattern selection through HTML review. Then follow the individual
module docs linked from README; direct model invocation remains disabled. A separately authorized
[offline model handoff](MODEL_HANDOFF.md) can import saved responses for review.

After changing any draft, link, package or recorded review, regenerate the affected
bindings and review the change. Do not hand-edit hashes merely to bypass stale-input
errors. The full workflow has no automated source acquisition, actual researcher
fidelity benchmark or scientific certification.

Regression checks:

```
python -m unittest tests.test_synthetic_walkthrough -v
```

The suite executes the complete real-CLI journey in a temporary external directory
and checks failures, path safety and input preservation. The symlink test may skip
when the platform does not permit creating symlinks; other path tests still run.

## Exercise the offline response path with synthetic fixtures

```sh
python synthetic_walkthrough.py ../persona-imported-demo --candidate-source offline-import
```

This alternative runs 17 real CLI stages, including local handoff preparation, an
empty response template and saved-response import. It fills that response with the
same bundled invented candidate rows and an explicitly synthetic provenance
declaration. **No model ran**; the demo receipt says the imported response is a
synthetic fixture. It is not an extraction-quality evaluation or a provider receipt.

Reader scope identifies imported origins rather than mocks, and lineage replays
the exact imported bundle plus explicit fixture review. Proposed/reviewed labels,
review counterevidence, later-publication warnings and missing design criteria remain
visible. Answer review stays deferred. All existing no-overwrite/path/failure rules
apply. The default command still uses the 15-stage mock route.

## Extended source-to-method-to-argument route

```sh
python synthetic_walkthrough.py ../persona-research-journey --candidate-source offline-import --research-journey
```

This 27-stage synthetic route adds reviewed imported pattern proposals with exact
reference-specific explanations, declared review/publication relationships and a
target-context form, then composes them with the same answer review and argument
map. Read `research-journey.txt` first. Rejected proposals, deferred claims, missing
falsifiers and an uncited conclusion remain visible. No research is approved or
executed. The fixed fixture decisions accept no external material. Completion is
written only after all added stages succeed. The original 15/17-stage modes are
unchanged. See [the full research-journey guide](RESEARCH_JOURNEY.md).

## Current local source recheck

Add `--recheck-sources` to the extended command above to run 30 synthetic stages.
The runner materializes invented local source files and checks every stored quote
against them. Read `source-recheck.txt` before the full integrated report. Existing
recorded checks remain unchanged; current file/quote checks are separate. Answer
review stays deferred. Source changes fail closed with no completion marker. See
[the source-recheck guide](SOURCE_RECHECK.md) for standalone selection and CLI use.

## Explicit method application intent

Add `--review-method-use` to an extended journey. With offline-import reasoning and
source recheck this runs 32 stages. Read `method-applications.txt` after the compact
source report: a fixed synthetic constraint is considered for a named step, while
excluded source context and missing failure criteria stay visible. The template is
all-deferred, proposed checks are not executed, and answer review remains deferred.
See [method application](METHOD_APPLICATION.md). Earlier modes are unchanged.

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
CLI stage (39 with the preceding options, 46 with answer imports, or 53 with both answer and argument imports). Existing JSON/text modes are unchanged.
The static/security/CLI checks are automated; actual-browser visual, keyboard and
print QA is currently blocked by the cloud environment's socket restriction.
See [local HTML review](LOCAL_HTML_REVIEW.md) for the reading order, privacy limits
and precise verification scope.

## Reopen explicitly pinned inputs

[Journey input cards](JOURNEY_INPUTS.md) bind the exact relative JSON file choices,
raw bytes and logical payloads so a later inspection needs only the card and an
explicit input root. Any artifact change fails rather than refreshing hashes or
migrating decisions. A selected live-source check still requires an explicit source
root on every command. Text/JSON/HTML retain the same review semantics, with an added
per-file consistency record. The browser presentation verification limit remains
unchanged; this is a local input convenience, not approval or source authority.

## Compare two pinned journeys

[Journey comparison](JOURNEY_COMPARISON.md) freshly inspects two explicit input cards
with separate roots. It distinguishes file changes, declared argument/method/review
changes and resolved source/route changes while retaining both full histories.
Unchanged text is not stable semantic identity; disappeared prompts are not proof
of resolution. No automatic rebinding, approval or source-history reconstruction
occurs. JSON/text output is bounded; browser QA remains unverified.

## Optional integrated starter

[Start an integrated review workspace](INTEGRATED_WORKSPACE.md) with explicit topic
and target context to create the existing empty pattern, relationship and argument
forms plus deferred context assessments. Its relative-file selection has no chosen
pattern or optional source/review/method inputs, so it is intentionally not a ready
input card. Follow the documented dependency order and preserve old files; no
scientific choices, automatic rebinding or source reads are added.

## Imported answer intent, with separate final review

Add `--import-answers` to a `--research-journey` demo. Seven real commands create
an explicit evidence scope, prepare/import canned proposals, record fixed invented
adoption decisions, render their review and export a complete-history answer draft.
The original, rewritten and rejected text survives answer/design, argument,
evidence-scope, research-journey and optional passive HTML reports. No final answer
is retained automatically: the independent answer review remains all-deferred.

The minimal offline-import extraction route has 34 stages. The preceding extensions
plus answer imports have 46 stages; use the command in [answer proposals](ANSWER_PROPOSALS.md).
Adding the argument-import extension below increases the full route to 53.
The mode accepts no external response/review files, creates no provider request,
and leaves unsupported conclusions, method conditions and argument defeaters visible.
Source-checking, method-use and HTML flags remain independent explicit options.
Earlier modes and failure/no-overwrite rules are unchanged. Actual browser QA is
still blocked and unverified, even when a static HTML report is written.

## Imported argument intent, without private reasoning reconstruction

Add `--import-arguments` to a `--research-journey` demo. Seven real CLI stages use
explicitly selected existing answer claim IDs, canned bridge suggestions and fixed
invented adoption decisions. Two steps are adopted and a cyclic alternative rejected.
Original/reviewed/rejected bridge histories stay visible; accepted declaration order
is separate from topological review order. Final answer review stays all-deferred,
and no logical validity or researcher thought process is certified.

The minimal offline-import extraction route has 34 stages; every extension together
has 53. The flag also works without imported answers or method/source/HTML flags.
See [argument proposals](ARGUMENT_PROPOSALS.md) for the complete command and manual
workflow. No external candidate/review arguments, provider calls or browser actions
are accepted. Failed new stages leave diagnostics, never COMPLETE. Earlier 39/46-
stage modes retain their existing behavior. Static HTML output does not establish
visual, keyboard or print QA, which remains blocked and unverified.

## Prepare research context before synthetic answers

Add `--contextual-answers` together with `--research-journey --import-answers` to
exercise the v3 contextual preparation route. The same invented pattern, target
context and publication relationship forms are prepared before the answer handoff
and reused later. Counts stay 32 with minimal mock extraction, 34 with minimal
offline-import extraction, or 53 with every existing extension. Citation scope
remains the explicitly selected references, even when other records appear in
context. Candidate adoption is fixed fixture data; final answer review is deferred.

See [contextual answer preparation](ANSWER_CONTEXT.md#try-the-contextual-synthetic-walkthrough)
for complete commands and how to inspect recorded versus current context. This
mode adds no model call, real researcher reconstruction, general auto-review or
browser execution. Omit the flag to retain the earlier v1 answer route unchanged.

## Record a human assessment separately

Every synthetic demo leaves the human-validation axis at `NOT_PERFORMED`. To document a
rater assessment of one exact package without touching its payload, use the detached
[human validation record](HUMAN_VALIDATION.md): `human_validation.py template`, `check`
and `status`, plus `review_package.py --human-validation`. The shipped fictional record
binds to `examples/trajectory-conditions-package.json`; a record for a demo package needs
a new template bound to that package's own hashes. Nothing in it is a score, a verified
independence claim or a change to `validation.human_validation`.

For lifecycle step 11, see [detached pre-holdout candidate findings](CANDIDATE_CHALLENGE.md).

For a supplied update trigger, see [controlled reopening declarations](RELEASE_RECORD.md).

For an operator-supplied release choice, see [decision records](RELEASE_DECISION.md), not an automatic approval path.

For agent-friendly command discovery without executing scripts, see [JSON command list](COMMAND_LIST.md).

Before invoking one trusted command, inspect [its bounded help description](COMMAND_DESCRIPTION.md).
