# Validation history

This file preserves every dated verification entry of this repository, in the order in
which the former single `VALIDATION.md` held them: the verification snapshot written for
v0.68 on 2026-11-04 first, then the prior per-release records from v0.67 back to v0.49, then
the historical incremental records from 2026-11-02 onward, with later dated entries appended
at the end. The text is unchanged apart from two relative link targets
(`docs/LOCAL_HTML_REVIEW.md` became `LOCAL_HTML_REVIEW.md`, because this file now lives in
`docs/`). The counts in each entry describe that entry's own snapshot, not the current
test-suite size; [VALIDATION.md](../VALIDATION.md) holds the current snapshot and the local
verification steps. Old local-pass statements do not establish later remote CI results, and
no entry claims scientific validation, real researcher data or model use.

## Current verification snapshot (2026-11-04, UTC)

Current local source release: v0.68 (bounded escaped duplicate-key diagnostics).

- `python -m unittest discover -q`: 961 synthetic tests passed locally in 888.833 seconds.
- `python -m compileall -q .`: passed; 138 Python files also parse with 3.10 grammar.
- `python audit_publication.py`: passed, 222 text files scanned including the manifest.
- `python verify_manifest.py`: passed, 221 exact allowlisted entries and file hashes.

Most recent separately verified remote baseline: v0.67, commit
[`488e90f8cef782116840233f670bd7ca46a8c178`](https://github.com/h-dot-seo/persona-for-research/commit/488e90f8cef782116840233f670bd7ca46a8c178),
with 957 tests. This is a prior-commit record, not a claim of remote CI for v0.68.

- [GitHub Actions run 41847274021](https://github.com/h-dot-seo/persona-for-research/actions/runs/41847274021):
  all four jobs passed for that exact commit, Ubuntu/Windows and Python 3.10/3.12.

The only changed runtime module is `strict_json.py`; the other 55 non-test modules
match v0.67. A pre-change synthetic duplicate key reproduced literal newline,
terminal escape and bidirectional characters in the shared loader's exception;
ordinary argument-map stderr emitted the escape while focused mode already escaped
it. Duplicate JSON rejection itself was not bypassed, and no command execution is
claimed. The shared diagnostic is now escaped at its source.

Duplicate detection still compares complete decoded keys exactly. Only after a
duplicate is found does its diagnostic show an ASCII JSON-quoted prefix of at most
128 Unicode code points, followed by an explicit truncation notice when needed.
The decoded diagnostic string is bounded at 1,613 printable ASCII characters even
for non-BMP code points; enclosing CLI/JSON error formats have their own additional
syntax. No valid input is shortened or normalized, no new input cap is imposed,
and distinct long keys sharing a preview remain distinct. Rejection occurs during
JSON decoding before downstream processing, not before all object values are parsed.

Four new tests cover controls, newlines, bidi and line-separator characters, lone
surrogates, non-BMP characters, the exact/over-128 boundary, long distinct keys,
escape-equivalent duplicate keys, valid nested Unicode data and representative
ordinary CLI error paths. The persona CLI's structured stdout error is checked
explicitly; its existing output contract is preserved. Raw stderr checks remove
only one final LF or CRLF, then require the exact printable-ASCII payload, without
normalizing any embedded control characters.

The final strict-JSON focused run passed all ten tests in 2.987 seconds; the
focused argument CLI regression passed in 0.449 seconds. Its expected malformed-key
message now follows the shared JSON-quoted representation. That regression also
now has explicit 30-second subprocess budgets where it previously had no timeout;
this is a tightening, not a timeout relaxation. Existing strict-JSON subprocess
budgets remain 20 seconds. A separate read-only final source/test/doc audit found
no concrete remaining defect; it performed no tests or browser actions.

A separate compatibility check parsed all 26 existing public JSON fixture files
with both immutable v0.67 and current loaders. Parsed values matched and original
file-byte hashes were unchanged. Existing raw-byte hashing, authorization/split
rejection, non-finite number rejection, nesting checks and valid report snapshots
are also covered by the complete aggregate above. This is diagnostic-output safety,
not source authentication, general terminal sandboxing or a guarantee about every
other error path or external tool.

Only synthetic inputs were used. No researcher data, source download, provider
execution, external transmission, scientific execution or approval behavior was
introduced. Browser visual/keyboard/print QA remains **BLOCKED/unverified**, with
no retry or restriction bypass. Earlier attempts and boundaries remain recorded below.

## Prior v0.67 single-active-argument-step companion

Current local source release: v0.67 (explicit single-active-argument-step companion).

- `python -m unittest discover -q`: 957 synthetic tests passed locally in 824.274 seconds.
- `python -m compileall -q .`: passed; 138 Python files also parse with 3.10 grammar.
- `python audit_publication.py`: passed, 222 text files scanned including the manifest.
- `python verify_manifest.py`: passed, 221 exact allowlisted entries and file hashes.

Most recent separately verified remote baseline: v0.66, commit
[`18f0bdae5c7d7c6ce2f3df1d2c53f36974c41dda`](https://github.com/h-dot-seo/persona-for-research/commit/18f0bdae5c7d7c6ce2f3df1d2c53f36974c41dda),
with 942 tests. This is a prior-commit record, not a claim of remote CI for v0.67.

- [GitHub Actions run 41840652118](https://github.com/h-dot-seo/persona-for-research/actions/runs/41840652118):
  all four jobs passed for that exact commit, Ubuntu/Windows and Python 3.10/3.12.
- A separate read-only v0.66 audit became available after its publication. It found
  no concrete defect in the example, documented distinctions or local file digests;
  it did not run tests, authenticate sources or inspect a browser. The earlier
  publication-time statement that no separate audit was recorded is preserved below.

The only changed runtime module is `argument_map.py`; the other 55 non-test modules
match v0.66. Existing full inspection/rendering APIs and default outputs remain
unchanged. New raw-input `inspect_step` / `render_step` and opt-in `--step-id` select
an exact active manual/adopted step only after complete ordinary inspection.
Unknown, rejected-candidate and empty-map selections fail. Invalid unselected
active graphs and stale complete-history bindings still reject.

The companion preserves the selected inspected step and original imported proposal,
complete endpoint claim/citation/explanation records, separate answer-review
judgments/notes, premise order, declaration versus review order and same-conclusion
alternatives. Uncited conclusions remain uncited; upstream nonendpoint claims are
not silently treated as premises. Accepted argument adoption does not approve
endpoint claims, source interpretations or logical inference.

The view identifies the complete fresh inspection and all original JSON-compatible
inputs by logical-content hashes, with absent/supplied review distinguished. These
are not raw file-byte hashes, authentication or a verified companion-file link.
Other step/claim IDs and known omitted history/context containers are explicit;
complete histories are not embedded. Regeneration requires the same raw files and
options without the selector. Recorded context is either absent or historical;
current journey context, method use and source recheck are NOT_EVALUATED_HERE.
The view is not an archival replacement, an accepted map or a review decision.

Focused mode alone bounds complete indented inspection JSON including its newline
before selection, then both focused JSON/text encodings, at 16 MiB. It does not
regenerate the complete text report just to inspect JSON. Existing legacy input
acceptance and output limits are unchanged. Raw objects are not silently normalized
before ordinary validation, projected data is detached, and text fields and focused
inspection errors are escaped.

Fifteen new tests and nine existing map tests passed in final serial focused runs:
11 manual tests in 0.795 seconds, four imported tests in 18.313 seconds, and nine
existing tests in 0.306 seconds. Sixteen complete pre-edit default JSON/text
snapshots remain equivalent. Legacy contextual JSON key ordering can vary across
processes; expected JSON hashes were canonicalized from the saved pre-edit outputs,
not replaced with new expectations. Text hashes remain exact.
One earlier combined focused run was stopped by an external 30-second whole-suite
wrapper (exit 124 after two tests, during the imported cases). This was not a
repository CLI timeout or evidence of a runtime failure; final serial runs used
normal process completion. Actual per-command 30-second CLI limits are unchanged,
and no concurrency cause is asserted.

A separate final static re-review found no remaining concrete defect. Its focused
stderr concern was addressed with conditional escaping that preserves default
errors. An early claim that extra source-component metadata could cause a public
history-inventory crash was withdrawn after tracing the existing runtime projection,
which strips those extras. The inventory now uses explicit report-owned paths and
accurate context-presence labels; regression tests preserve parity with the actual
full report rather than claiming an unreachable public reproduction. The audit
ran no tests, provider calls or browser checks.

Independent external-directory CLI checks passed four complete default-output
comparisons, four focused v1/v2 JSON/text commands, and three expected rejections,
all within unchanged 30-second command limits. Full JSON objects match the pre-edit
baseline and full text bytes are identical. The complete synthetic text reports
were 103,834 / 181,646 bytes; their selected-step companions were 19,650 / 22,149
bytes, with explicit omission disclosures. This illustrates a navigation-size
reduction for these fixtures, not a general performance or completeness guarantee.
Full-report/input digests, exact endpoints, deferred review, absent conclusion
citations, orders, history paths and escaped malformed-input stderr were checked.

Only synthetic fixtures were used. No real researcher data, source reread, provider
execution, external transmission or scientific execution was introduced. Browser
visual/keyboard/print QA remains **BLOCKED/unverified**, with no retry or restriction
bypass. Earlier failures and limits remain recorded below.

## Prior v0.66 worked publication-trajectory and conditions example

Current local source release: v0.66 (worked publication-trajectory and conditions example).

- `python -m unittest discover -q`: 942 synthetic tests passed locally in 1064.988 seconds.
- `python -m compileall -q .`: passed; 137 Python files also parse with 3.10 grammar.
- `python audit_publication.py`: passed, 221 text files scanned including the manifest.
- `python verify_manifest.py`: passed, 220 exact allowlisted entries and file hashes.

Most recent separately verified remote baseline: v0.65, commit
[`417be1d101288c1b5383002ad61b91360e7e69bf`](https://github.com/h-dot-seo/persona-for-research/commit/417be1d101288c1b5383002ad61b91360e7e69bf),
with 935 tests. This is a prior-commit record, not a claim of remote CI for v0.66.

- [GitHub Actions run 41835063532](https://github.com/h-dot-seo/persona-for-research/actions/runs/41835063532):
  all four jobs passed for that exact commit, Ubuntu/Windows and Python 3.10/3.12.

All 56 existing non-test Python modules match the v0.65 publication hashes.
This increment adds five fixed synthetic JSON inputs, one worked guide, one seven-test
integration class and a README link. No runtime, schema, provider, generator mode,
individual command timeout or workflow job budget changed.

The five invented publication records contain six observations: early research
supports M under A, later research challenges M under B, a review summarizes each
with separate exact passages, and two same-year research records disagree under A.
The existing trajectory groups case-folded topic and exact method/condition strings.
A has cross-year stance variation and same-year disagreement; B remains challenge-only.
Cross-year variation is an existential support/challenge flag, not a directed reversal.
Identical recorded conditions do not prove scientific comparability; deterministic
same-year display order does not establish chronology or a latest-wins rule.

Two declared review-summary relationships preserve exact basis references from
both endpoints and dependency-review warnings. The A and B groups contain four
and two distinct paper IDs, respectively; the corpus has five papers because the
review appears in both groups. These are record counts, not independent-evidence
counts. Missing relationships do not establish independence.

Exactly five observation references are selected for answer citation. The review's
second observation remains visible as relationship basis and excluded contextual
evidence but cannot be cited without explicit selection, even though its paper is
already selected. Source stance, pattern role and answer citation role stay distinct:
the later supporting source challenges a replacement narrative while supporting
the bounded description of disagreement. All per-reference explanations and limits
remain supplied operator judgments, not automatically validated entailment.

Fixed synthetic adoption accepts one bounded publication-record synthesis and
rejects personal-change-of-mind and independent-review-confirmation alternatives.
Rejected wording remains explicit proposal history; shared sources and contrary
evidence remain visible in the accepted claim. Separate final answer review stays
all-deferred, and semantic validation remains NOT_PERFORMED.

The focused seven-test run passed in 16.437 seconds, running 17 real CLI stages
once with unchanged 30-second per-command limits. The written external-directory
POSIX shell recipe was also executed separately. Tests cover grouping and temporal
boundaries, declared dependencies, exact citation permission, preserved rationales,
rejected versus active claims, deferred final review, immutable input bytes, package
reconstruction and in-memory operations guarded against file, socket and mock-provider
access. The complete final aggregate is recorded above; wall time is environment-
dependent, and no performance claim is made. No separate independent code audit
is recorded for this increment.

All source hashes are explicitly documented deterministic synthetic placeholders,
not checked original-source digests. Source and quote checks remain NOT_PERFORMED.
No real researcher data, source download, provider execution, external transmission
or scientific execution was used. This checks preservation of authored distinctions,
not attribution detection, source authentication or researcher fidelity.
Actual-browser visual/keyboard/print QA remains **BLOCKED/unverified**; no retry or
restriction bypass was attempted. Earlier failures remain recorded below.

## Prior v0.65 guarded call-local argument rendering

Current local source release: v0.65 (guarded call-local argument text rendering).

- `python -m unittest discover -q`: 935 synthetic tests passed locally in 824.115 seconds.
- `python -m compileall -q .`: passed; 136 Python files also parse with 3.10 grammar.
- `python audit_publication.py`: passed, 214 text files scanned including the manifest.
- `python verify_manifest.py`: passed, 213 exact allowlisted entries and file hashes.

Most recent separately verified remote baseline: v0.64, commit
[`4f14d63e9c89c31530741e80fe2e8443ab5049e5`](https://github.com/h-dot-seo/persona-for-research/commit/4f14d63e9c89c31530741e80fe2e8443ab5049e5),
with 919 tests. This is a prior-commit record, not a claim of remote CI for v0.65.

- [GitHub Actions run 41828282054](https://github.com/h-dot-seo/persona-for-research/actions/runs/41828282054):
  all four jobs passed for that exact commit, Ubuntu/Windows and Python 3.10/3.12.

The integrated text renderer can reuse its own freshly inspected argument map at
its original formatting position. A private conservative guard requires exact
built-in JSON types, finite numbers, no surrogate code points, no container aliases,
limited depth and a bounded amount of guard work. Current full package, draft,
argument and separate-review hashes must still match the current call's bindings.
The 8,192-node guard-work budget is checked before adding child entries; it limits
only this optimization, not which otherwise valid inputs the public API accepts.
Ineligible, changed or uncertain inputs retain the original raw rendering path.

Every public argument or journey call still validates original inputs. No persistent
cache, public inspected-report input, new source access or atomicity guarantee is
introduced. The argument formatter body, nested full history renderers and final
size checks are preserved; other journey renderers and JSON/HTML behavior are not
changed. Review declarations are still not authenticated approval.

Sixteen added tests cover ten pre-change complete JSON/text snapshot pairs, one
outer argument inspection on eligible renders, fresh later calls, legacy tuple
coercion and contextual tuple rejection, exact types, aliases, nesting, surrogates,
full wrapper/absent-review bindings, changed inputs during source-path callbacks or
preceding rendering, rejected histories, input/output limits, no provider or implicit
I/O, immutability and bounded-work fallback. The initial 15-test focused run and a
39-test existing map/replay/journey run passed; the added budget test and updated
snapshot/ordering checks also passed before the complete final run above.
A separate read-only audit of the final source and tests found no concrete defect;
it did not run tests, timings or browser QA.

Instrumented full synthetic v1 and v2 journeys each reduced outer inspections of
the supplied argument from two to one, preserving exact complete text bytes and
lengths. Two serial before/after timing pairs preserved all output hashes, but
wall timings varied, including a slower v2 sample. The deterministic inspection
count and exact output equivalence are the regression gates, not a speed threshold.
The earlier v0.63 timeout cause remains unestablished. Neither individual 30-second
CLI limits nor the 15-minute full workflow budget changed in this increment.

Four real CLI commands passed within their existing 30-second limits: full v1/v2
journey text, standalone v2 argument text and v2 journey JSON. Their outputs match
pre-change saved outputs exactly (canonical JSON comparison for the JSON report).
Explicit current checks used only existing synthetic local sources and remained
separate from recorded context. No new provider invocation, external transmission,
scientific execution, source interpretation or researcher speech was introduced.
Actual-browser visual/keyboard/print QA remains **BLOCKED/unverified**, with no retry
or restriction bypass. Earlier failures remain recorded below.

## Prior v0.64 worked bridge-basis reading path

Current local source release: v0.64 (worked bridge-basis reading path).

- `python -m unittest discover -q`: 919 synthetic tests passed locally in 618.163 seconds.
- `python -m compileall -q .`: passed; 135 Python files also parse with 3.10 grammar.
- `python audit_publication.py`: passed, 213 text files scanned including the manifest.
- `python verify_manifest.py`: passed, 212 exact allowlisted entries and file hashes.

Most recent separately verified remote baseline: v0.63, commit
[`34d1db98047a0e2808bbc1840f1822841c598917`](https://github.com/h-dot-seo/persona-for-research/commit/34d1db98047a0e2808bbc1840f1822841c598917),
with 916 tests. This is a prior-commit record, not a claim of remote CI for v0.64.

- [GitHub Actions run 41823750537](https://github.com/h-dot-seo/persona-for-research/actions/runs/41823750537):
  all four jobs passed for that exact commit, Ubuntu/Windows and Python 3.10/3.12.

All 56 existing non-test Python modules match the v0.63 publication hashes.
This increment changes documentation and three regression tests, not runtime,
schemas, defaults, generator modes, stage counts or approval behavior.

The worked guide follows the existing synthetic `late` bridge from `comparison`
to the uncited `conclusion`. It identifies the reviewed rationale, assumption and
missing defeater; exact support/challenge reference identities; source conditions,
limitations and claim labels; and the supplied versus absent citation explanations.
The review reference used upstream by `criterion` as context is also a direct
`late` premise challenge through `comparison`. Exact source, claim, argument and
citation roles remain distinct. Design method use on `compare` is not a method
endorsement of argument `late`, and recorded answer context remains historical.
The guide distinguishes the existing v3-answer/v1-argument fixture from the separate
opt-in v2 argument handoff. No new machine-addressable basis relationship is added.

Three tests reuse the existing 53-stage contextual fixture setup. The focused class
passed all 20 tests in 89.529 seconds. Assertions cover the bridge and exact routes,
role separation, unchanged uncited conclusion/final deferred review, and a fresh
note-only all-deferred review that preserves original inputs/files and cannot export.
A separate read-only source/documentation audit found no substantive discrepancy;
it did not execute tests or a browser.

A standalone external-directory check executed the guide's fresh review template,
JSON and text inspection commands successfully, and confirmed export rejects the
unresolved review with no partial stdout. All three candidates remained deferred;
original input bytes were unchanged. A note does not approve a bridge, transfer
citations, authenticate a source or create a method-to-argument relationship.
Revisions still require explicit complete reviewed steps and ordinary rebinding.

Only invented data and existing offline commands were used. Source/file matches
remain mechanical checks, not semantic support or researcher fidelity. No provider,
source reread, external transmission or scientific execution was added. Actual-browser
visual/keyboard/print QA remains **BLOCKED/unverified**; no retry or restriction
bypass was attempted. Earlier timeout attempts remain recorded in the v0.63 history.

## Prior v0.63 recorded answer context in arguments


Current local source release: v0.63 (explicit recorded-answer-context argument preparation).

- `python -m unittest discover -q`: final complete run passed all 916 synthetic tests in 613.787 seconds.
- `python -m compileall -q .`: passed; 135 Python files also parse with 3.10 grammar.
- `python audit_publication.py`: passed, 213 text files scanned including the manifest.
- `python verify_manifest.py`: passed, 212 exact allowlisted entries and file hashes.

Most recent separately verified remote baseline: v0.62, commit
[`d78283cf99c841c6b9cb0d5d9a5f16e937a44cf8`](https://github.com/h-dot-seo/persona-for-research/commit/d78283cf99c841c6b9cb0d5d9a5f16e937a44cf8),
with 887 tests. This is a prior-commit record, not a claim of remote CI for v0.63.

- [GitHub Actions run 41816254697](https://github.com/h-dot-seo/persona-for-research/actions/runs/41816254697):
  all four jobs passed for that exact commit, Ubuntu/Windows and Python 3.10/3.12.

Explicit inclusion creates v2 argument artifacts only for a validated reviewed v3
contextual answer. The complete original recorded pattern/context history is rebuilt
from that envelope, with its original answer bindings and exact-reference scope.
Excluded, unselected and rejected histories remain visible. They are historical
answer-preparation/import context, not current argument context, authenticated model
use, proof of influence or permission to adopt a method. Different current journey
forms stay separately compared and do not rebind the recorded argument.

Existing selected claim IDs still bind every premise and conclusion. Wider nested
answer references grant no new endpoint, citation, source-access or transmission
permission. Source quotations cannot be conclusions. Candidate templates stay
deferred; export requires explicit complete adoption. Original/revised/rejected
bridge history and separate final-answer review remain preserved. No automatic
scientific or logical approval, researcher speech, provider execution or source
reread is introduced.

The full workflow job budget is 15 minutes for the expanded suite, raised from
10 minutes after the local aggregate exceeded ten minutes. Individual assertions
and CLI timeout checks are unchanged. This is a bounded job budget change, not
a performance improvement or a claim that the new CI has passed.

The first aggregate attempt ran 891 tests in 640.419 seconds but failed during
`test_contextual_walkthrough.setUpClass`: its existing full-context text-rendering
subprocess exceeded 30 seconds, so that class's 17 tests did not run. This matches
the previously recorded v0.60 timeout location; the cause is not established. No
individual timeout was changed.
The affected class passed all 17 tests separately in 118.636 seconds without any
source or timeout edits. Static inspection confirms that this walkthrough omits
the new option; context reconstruction, strict JSON replay and full pretty-output
serialization are v2-guarded. These observations do not establish the timeout's
cause. A second aggregate attempt also timed out at that same step, running
891 tests in 657.180 seconds with the same 17 tests blocked. Both failures are
retained. Repeated retries were stopped to investigate redundant answer replay.

A narrow local reuse change removes only the second identical full answer replay
inside each private argument-step inspection. Public entry points still validate
original inputs on every call; no persistent cache or supplied inspected-answer
input is accepted. Instrumented full synthetic inspections with three candidates
and two accepted steps decreased from 24 to 16 replays for v1 and 25 to 17 for v2,
with identical complete inspection hashes. This structural reduction does not
establish the earlier timeout's cause.

Eight added replay-reuse tests cover fresh validation on separate calls, changed
histories/reviews, error order, detached results and no-I/O behavior. All 32
pre-change full JSON/text snapshots for plain/contextual answers with and without
separate review match. The 23-test replay/contextual-argument run and 22-test plain
map/proposal run passed. An initial test assumed every legitimate changed history
must be rejected even by a direct private step check; the corrected test requires
fresh hashes for that legal change and rejection of stale public envelopes.

A separate read-only audit of the reuse diff found no concrete defect; it did not
rerun tests or timings. Four measurement passes preserved all eight complete
import/review/inspection/text hashes. Wall timings varied, including a slower v1
inspection sample, so no general speed guarantee is claimed. A separately paired
full default journey text command took 16.267 seconds before and 13.835 seconds
after, with identical text bytes. The deterministic replay-count reduction, not
a timing threshold, is the regression gate. The original timeout cause remains
unestablished; the complete final rerun is recorded above.

Twenty-one recorded-context tests cover default compatibility, explicit flags and
version mixing, strict JSON direct APIs, full history bindings, stale/cached context rejection,
source-quote restrictions, no citation transfer, input immutability and no-I/O
operations. Near-boundary tests cover complete indented v2 JSON and text limits;
legacy compact-only API limits remain unchanged. Frozen v1 artifacts over a v3
answer match hashes captured before this increment; earlier frozen answer and
argument fixtures remain checked.

The six integration tests exercise argument maps, current-versus-recorded journey
context, visible passive HTML outside the saved JSON snapshot, and pinned comparison
of v1/v2 and rejected-history changes. Initial focused assertions incorrectly assumed
an escaping spelling and provenance equality after changing an answer bundle; those
test assumptions were corrected without changing runtime behavior. Before replay
reuse, a 31-test focused run and an additional 32-test existing argument map/
integration/walkthrough run passed. The corrected integration test also passed.
The final aggregate rechecks these after reuse. The implementation and integration
tests were developed separately. A separate
read-only source/test audit found no concrete correctness, permission, privacy,
bounds or compatibility defect. That audit did not run tests or establish the cause
of the aggregate timeout.

The standalone external-directory run was repeated after replay reuse. Both runs
completed 13 real CLI stages plus two expected failures for empty scope and mixed envelope versions, with no partial stdout on
failure. It covered scope, handoff, response/import, deferred adoption template,
review JSON/text, export, argument inspection/map text and full journey JSON/text/HTML.
Recorded context matched across the handoff, review packet and map. Six complete
JSON outputs and three text outputs matched exactly before/after the reuse change.
Two explicitly adopted synthetic bridges and one rejected alternative stayed distinct, original
inputs/source bytes stayed unchanged, and final answer decisions remained deferred.
The complete passive HTML JSON snapshot matched the fresh journey JSON. Existing
optional journey source checks remained separate from the recorded context.

These checks establish bounded reconstruction and preserved declarations, not
semantic entailment, attribution accuracy, authenticity or researcher fidelity.
Human scientific and source-rights review remains required. Actual-browser
visual/keyboard/print QA remains **BLOCKED/unverified**; no browser retry or
restriction bypass was attempted.

## Prior v0.62 bounded review-attribution example


Current local source release: v0.62 (bounded synthetic review-attribution example).

- `python -m unittest discover -q`: 887 synthetic tests passed locally in 343.946 seconds.
- `python -m compileall -q .`: passed; 132 Python files also parse with 3.10 grammar.
- `python audit_publication.py`: passed, 210 text files scanned including the manifest.
- `python verify_manifest.py`: passed, 209 exact allowlisted entries and file hashes.
- All 56 existing non-test Python modules match the v0.61 publication hashes.
  This increment adds examples, a guide and regression tests, not runtime behavior.

Most recent separately verified remote baseline: v0.61, commit
[`c45349f0ef1cc3ffe00889ba96f1067f1037da70`](https://github.com/h-dot-seo/persona-for-research/commit/c45349f0ef1cc3ffe00889ba96f1067f1037da70),
with 878 tests. This is a prior-commit record, not a claim of remote CI for v0.62.

- [GitHub Actions run 41814621592](https://github.com/h-dot-seo/persona-for-research/actions/runs/41814621592):
  all four jobs passed for that exact commit, Ubuntu/Windows and Python 3.10/3.12.

Five complete invented JSON fixtures run through existing context, handoff, import,
adoption and final-answer-review commands. Nine focused tests passed, including
15 successful real CLI stages from an external temporary directory. An independent
read-only audit reran all nine tests and separately executed the documented shell
recipe successfully. No runtime module or existing snapshot was modified.

The two focal observations share review/explicit-statement labels but retain
separate exact quotations, reference identities, limitations and declared reasons:
one reports another invented group's method; the other states the review's
recommendation to test an alternative. Neither establishes individual method
ownership, personal practice, development or implementation. A second invented
review supplies only context for the existing pattern contract; it is excluded
from exact answer citations and is not the absent original paper or independent
corroboration. Publication relationships remain empty.

The bounded active answer says the review reports M and recommends testing N.
The unsupported personal-use assertion remains explicitly rejected import history.
Its source reference can still support the bounded active claim; rejecting one
candidate does not erase shared evidence. Fixed fixture adoption records an
operator's wording choice, not the scholar adopting a method. Separate final
answer review remains deferred and incomplete. Empty exact citation scope stays
empty, and a context-only reference cannot be added as an answer citation.

The tests cover preserved reasons/boundaries, original versus active history,
input immutability, escaping and guarded in-memory operations without file/network
access. These are preservation and explicit-review checks, not automatic semantic
inference, entailment, attribution detection, source authentication or researcher
fidelity. Recorded source/quote checks remain NOT_PERFORMED; no source reread,
provider or browser step is requested. Human scientific review remains required.
Actual-browser visual/keyboard/print QA remains **BLOCKED/unverified**; no browser
retry or restriction bypass was attempted.

## Prior v0.61 current-source preview checks

Current local source release: v0.61 (optional current-source checks in answer preview).

- `python -m unittest discover -q`: 878 synthetic tests passed locally in 355.893 seconds.
- `python -m compileall -q .`: passed; 131 Python files also parse with 3.10 grammar.
- `python audit_publication.py`: passed, 203 text files scanned including the manifest.
- `python verify_manifest.py`: passed, 202 exact allowlisted entries and file hashes.
- A standalone ten-command CLI check produced four JSON/text source-checked
  previews for empty and selected citation scopes. Both supplied papers were checked
  in each successful invocation; the complete inner context matched the default
  preview and exact selected records matched the appended audit. Six negative
  commands rejected missing option partners, changed bytes, an escaping path,
  a cached audit passed as selection, and a legacy scope, with no partial stdout.
  Original input/source hashes stayed unchanged. No provider or browser was invoked.

Most recent separately verified remote baseline: v0.60, commit
[`c2880f2b2c691dff75c1d0769e264ff40618f2e3`](https://github.com/h-dot-seo/persona-for-research/commit/c2880f2b2c691dff75c1d0769e264ff40618f2e3),
with 861 tests. This is a prior-commit record, not a claim of remote CI for v0.61.

- [GitHub Actions run 41813204845](https://github.com/h-dot-seo/persona-for-research/actions/runs/41813204845):
  all four jobs passed for that exact commit, Ubuntu/Windows and Python 3.10/3.12.

Seventeen new tests cover strict paired inputs, all-paper checking with zero or
selected citations, exact-reference associations, complete quote-gap reports,
unchanged historical labels and context, invocation-only roots, and one bounded
read per selected source per invocation. Invalid scope/history, selection and path
cases fail before source bytes are read. Rendering completed reports performs no
new read. Combined input, source and final full JSON/text limits fail closed.
Default empty/selected preview hashes were captured before these edits and remain
exact; v1/v2/v3 handoff/review replay and prior walkthrough contracts are unchanged.

Focused checks passed 133 tests across seven modules plus two explicit frozen v1
replay tests. An independent read-only audit passed 68 tests and additional checks
for per-reference text display, rights-neutral wording, audit/record copy isolation
and text-preflight failure before audit invocation. Two initial test-harness
references (canonical digest calculation and stored proposal field name) were
corrected without changing expected baselines or production validation.

The existing source-recheck and file-reader modules were not changed. Full package,
scope and raw-context validation plus base-report bounds precede the optional audit;
that audit retains all-paper selection/path preflight, author-matched authorization
rules, pinned bounded file reads and byte-hash checks. This does not establish a
broader race-proof filesystem guarantee. Current results are appended separately;
recorded labels, source hashes, review decisions and handoff bindings are not updated.

Current matches establish only the mechanical byte/section/quote checks described
in the report, not authenticity, authorship, rights, semantic support or scientific
approval. A selection requests a local read; it does not establish rights or allow
provider transmission. Missing quotes/locators remain gaps, while requested checks
that fail never silently fall back to an unchecked preview. All fixtures remain
synthetic and human scientific review is required. Actual-browser visual/keyboard/
print QA remains **BLOCKED/unverified**; no retry or restriction bypass was attempted.

## Prior v0.60 answer context preview checks

Current local source release: v0.60 (readable pre-answer context preview).

- Final `python -m unittest discover -q`: 861 synthetic tests passed locally in
  384.161 seconds, with the existing timeout limits unchanged.
- `python -m compileall -q .`: passed; 130 Python files also parse with 3.10 grammar.
- `python audit_publication.py`: passed, 202 text files scanned including the manifest.
- `python verify_manifest.py`: passed, 201 exact allowlisted entries and file hashes.
- A standalone six-command CLI check produced four JSON/text previews for empty
  and selected v3 scopes, each matching its API result. Two negative commands
  rejected empty handoff preparation and a legacy scope preview without partial
  stdout. All supplied input-file hashes remained unchanged. No provider or
  browser was invoked, and the preview did not reread source files.

Most recent separately verified remote baseline: v0.59, commit
[`b859ab3116bf7e5fb0860610e2e85a547d4a2890`](https://github.com/h-dot-seo/persona-for-research/commit/b859ab3116bf7e5fb0860610e2e85a547d4a2890),
with 839 tests. This is a prior-commit record, not a claim of remote CI for v0.60.

- [GitHub Actions run 41810919950](https://github.com/h-dot-seo/persona-for-research/actions/runs/41810919950):
  all four jobs passed for that exact commit, Ubuntu/Windows and Python 3.10/3.12.

Twenty-two new tests cover zero-reference inspection without relaxing preparation,
exact selected passages inside/outside the chosen pattern, exclusions and full
unselected/rejected context, canonical package/scope hashes, strict versions and
JSON types, stale forms, immutable/detached outputs, current-only execution flags,
control escaping, output/input bounds and CLI parity/failures. A frozen synthetic
v3 fixture was captured before these edits; its handoff, import, review, envelope,
inspection and text hashes remain unchanged. Frozen v1/v2 tests also pass. The
preview has its own 16 MiB report limit and does not invoke handoff preparation or
inherit its separate 2 MiB limit. Existing walkthrough stages are unchanged.

Focused checks passed 25 tests including frozen v1/v2/v3 replay and 42 existing
context tests. An independent read-only audit ran all 22 new tests and found no
remaining blocker. Initial new tests attempted to edit a detached fixture copy;
the mutation target was corrected so the intended changed-context cases execute.

The first aggregate run completed 844 tests with one setup error: the existing
contextual walkthrough's research-journey text subprocess exceeded its 30-second
limit, preventing that class's 17 tests from running. The affected 17-test suite
then passed separately in 105.740 seconds, followed by the complete passing run
above. No timeout or production validation was weakened. A separate source review
confirmed that preview functions are not called by the old journey path and add no
shared mutable state or repeated validation there. The timeout cause remains
unestablished; it is not attributed to load or treated as a successful run.

The preview does not generate a handoff, claim, decision or permission to transmit.
Empty citation scope stays empty. Stored passages and recorded checks are not new
source verification, rights clearance, semantic support, researcher agreement or
scientific approval. Every fixture remains synthetic and human scientific review
is required. Actual-browser visual/keyboard/print QA remains **BLOCKED/unverified**;
no browser retry or restriction bypass was attempted.

## Prior v0.59 contextual walkthrough checks

Current local source release: v0.59 (opt-in contextual synthetic walkthrough).

- `python -m unittest discover -q`: 839 synthetic tests passed locally in 317.869 seconds.
- `python -m compileall -q .`: passed; 129 Python files also parse with 3.10 grammar.
- `python audit_publication.py`: passed, 200 text files scanned including the manifest.
- `python verify_manifest.py`: passed, 199 exact allowlisted entries and file hashes.
- A separate actual CLI invocation ran the full 53-stage contextual route with
  imported source, pattern, method-application, answer and argument histories,
  fresh invented-source checks and passive HTML. Its saved JSON snapshot matched
  the fresh report exactly. Recorded/current context artifacts matched, source
  quotes matched, and all three final answer judgments remained deferred.
- Minimal contextual routes passed at 32 stages with mock extraction and 34 with
  offline-import extraction. Preparation moved before answer import without
  duplicating stages. No provider or browser was invoked.

Most recent separately verified remote baseline: v0.58, commit
[`d88c22fba76cde93c4d04a64faaac5c314f33fa7`](https://github.com/h-dot-seo/persona-for-research/commit/d88c22fba76cde93c4d04a64faaac5c314f33fa7),
with 822 tests. This is a prior-commit record, not a claim of remote CI for v0.59.

- [GitHub Actions run 41809403848](https://github.com/h-dot-seo/persona-for-research/actions/runs/41809403848):
  all four jobs passed for that exact commit, Ubuntu/Windows and Python 3.10/3.12.

Seventeen new tests cover explicit dependencies before writes, preparation order,
exact shared raw forms, full explanation/import histories, context-only citation
rejection, uncited conclusions, passive HTML snapshots, injected stage failures,
and fixture mutations before canned adoption or completion. Pattern candidate
payloads and deferred review rows, applicability targets/default state, empty
relationship forms and the exact final three deferred claim IDs are checked.
Empty/missing/extra final decisions cannot pass vacuously. No external response,
context, review, provider or browser arguments are accepted by the demo.

The existing walkthrough suites passed 46 tests, retaining the 39/46-stage golden
inventories. Before editing, a fresh v0.58 full 53-stage output was captured and
matched its prior v0.55 inventory; the no-new-flag route retains that same hash.
These comparisons normalize execution paths and JSON formatting. HTML comparison
covers the saved JSON and structural inventory, not bytes or browser layout.

An independent read-only implementation audit ran all 17 new tests in 118.173
seconds and found no remaining blocking issue. Its one stale documentation sentence
was corrected to say the default walkthrough remains v1. A preliminary new test
used an incorrect expected schema name; the assertion was corrected without a
production contract change. No real research data or external model execution was
used. Fixed invented adoption decisions are not a reusable automatic-review policy.

Matching recorded/current artifacts does not prove model use, applicability,
researcher agreement or scientific approval. Current source matches remain
mechanical checks of invented bytes and quotes. Human scientific review is still
required. Actual-browser visual/keyboard/print QA remains **BLOCKED/unverified**;
no browser retry or restriction bypass was attempted.

## Prior v0.58 contextual answer preparation checks

Current local source release: v0.58 (explicit research context for answer preparation).

- `python -m unittest discover -q`: 822 synthetic tests passed locally in 245.875 seconds.
- `python -m compileall -q .`: passed; all Python files also parse with 3.10 grammar.
- `python audit_publication.py`: passed, 199 text files scanned including the manifest.
- `python verify_manifest.py`: passed, 198 exact allowlisted entries and file hashes.
- A standalone 24-command CLI route prepared a v3 answer handoff with selected
  pattern, applicability and declared publication context; imported canned answers;
  recorded explicit synthetic adoption/rejection; and kept final answer review
  deferred. It composed an imported argument map, fresh invented-source checks,
  JSON/text/passive HTML, pinned reopening and a two-card comparison. A deliberately
  changed current publication annotation remained separate from the recorded
  answer-preparation context. The complete HTML JSON snapshot matched the report.
  No provider or browser was invoked.

Most recent separately verified remote baseline: v0.57, commit
[`2773d9186874f654facd78441aac49aae8391fe1`](https://github.com/h-dot-seo/persona-for-research/commit/2773d9186874f654facd78441aac49aae8391fe1),
with 772 tests. This is a prior-commit record, not a claim of remote CI for v0.58.

- [GitHub Actions run 41804884773](https://github.com/h-dot-seo/persona-for-research/actions/runs/41804884773):
  all four jobs passed for that exact commit, Ubuntu/Windows and Python 3.10/3.12.

Fifty new tests cover explicit v3 selection, exact question/topic/year bindings,
selected-pattern and applicability routes, year-scoped publication relationships,
full original/revised/rejected histories, immutable inputs, strict finite JSON,
collective input/output bounds and fail-closed CLI arguments. Context-only quotes,
sibling observations and rejected/unselected references never become citable unless
explicitly selected. Changed recorded context invalidates dependent review/map
bindings. Different current context is disclosed with both versions preserved,
not treated as automatic conflict, supersession, approval or model-use evidence.

Frozen v1 and v2 answer/argument artifacts retain their existing canonical hashes.
The v2 fixture was captured before this implementation, not regenerated to match it.
An independent read-only implementation audit ran 110 focused tests and identified
one low-severity direct-Python input-coercion inconsistency: template normalization
could turn tuples into JSON arrays before the strict context validator. The v3
entry points now check original inputs before normalization; a regression covers
that case and non-string keys. Thirty-eight focused tests and the full aggregate
passed after this fix. There was no independent post-fix re-audit. Two initial new
fixtures changed a target context without updating its existing binding; the
fixtures were corrected without weakening the production stale-context guard.

Supplied context is inspected operator input, not verified researcher reasoning,
source authorship, independence, influence, applicability or approval. Recorded
preparation context does not establish what any model actually received or used.
No source permissions expand, no decisions are automatically adopted, and human
scientific review remains required. All fixtures are synthetic. Actual-browser
visual/keyboard/print QA remains **BLOCKED/unverified**; no browser retry or
restriction bypass was attempted.

## Prior v0.57 citation reasoning audit checks

Current local source release: v0.57 (standalone citation reasoning audit).

- `python -m unittest discover -q`: 772 synthetic tests passed locally.
- `python -m compileall -q .`: passed; all Python files also parse with 3.10 grammar.
- `python audit_publication.py`: passed, 193 text files scanned including the manifest.
- `python verify_manifest.py`: passed, exact allowlisted inventory and file hashes.
- A standalone eight-command CLI check covered manual legacy, imported v1 and
  imported v2 drafts in JSON and readable text, with explicit final-review files.
  Six successful commands matched API reports; two negative commands rejected a
  stale final review and an unexported candidate bundle with empty stdout.
  Input-file hashes remained unchanged. No source bytes beyond explicit input
  artifacts were read by the audit, and no provider or browser was invoked.

Most recent separately verified remote baseline: v0.56, commit
[`6b309ffa65d2957e6efdfa65448e27b39a20962e`](https://github.com/h-dot-seo/persona-for-research/commit/6b309ffa65d2957e6efdfa65448e27b39a20962e),
with 748 tests. This is a prior-commit record, not a claim of remote CI for v0.57.

- [GitHub Actions run 41802919074](https://github.com/h-dot-seo/persona-for-research/actions/runs/41802919074):
  all four jobs passed for that exact commit, Ubuntu/Windows and Python 3.10/3.12.

Twenty-four new tests cover the absent/null/declared distinction, exact use identity,
full canonical package and imported-envelope bindings, null context boundaries,
retained/rejected/deferred final reviews, separate uncited/empty states, complete
non-active original/revised/rejected import history, and stale-history rejection.
Finite/strict JSON, malformed quotes/references/explanations, collective raw and
logical input bounds, text/JSON output bounds, immutable inputs, deterministic
output, terminal-control escaping and actual CLI failures are exercised. Frozen
v0.55 answer/argument replay remains exact after explicitly requesting this audit.

An independent read-only design assessment identified the legacy inventory gap and
recommended a separate report rather than changes to existing inspectors. Source
review and 41 focused tests (24 new plus 17 explanation/frozen regressions) passed.
This is not a claim of an independent post-implementation audit.

The audit adds no explanation, decision, schema upgrade, rebinding or citation
transfer. Counts describe supplied declarations, not support quality or completeness.
Unfinished candidate-review packets remain outside the valid-draft contract;
final-answer defer remains supported. Human scientific review is still required.
No real researcher data, model execution or current source verification is included.
Actual-browser visual/keyboard/print QA remains **BLOCKED/unverified**; no browser
retry or restriction bypass was attempted.

## Prior v0.56 citation explanation checks

Current local source release: v0.56 (opt-in claim-specific citation explanations).

- `python -m unittest discover -q`: 748 synthetic tests passed locally.
- `python -m compileall -q .`: passed; all Python files also parse with 3.10 grammar.
- `python audit_publication.py`: passed, 189 text files scanned including the manifest.
- `python verify_manifest.py`: passed, exact allowlisted inventory and file hashes.
- A standalone 21-command CLI route prepared v2 answer scope/handoff, imported
  invented explanations, recorded explicit synthetic adoption and rejection,
  prepared a separately deferred answer review, built a fresh imported argument
  map, and composed JSON/text/passive HTML with current synthetic source checks.
  It then pinned and reopened the same inputs. The complete HTML JSON snapshot
  matched exactly, source quotes matched, and the uncited conclusion stayed uncited.

Most recent separately verified remote baseline: v0.55, commit
[`30dbde6fa0a9b40ef1d48648a79e452d3403b067`](https://github.com/h-dot-seo/persona-for-research/commit/30dbde6fa0a9b40ef1d48648a79e452d3403b067),
with 721 tests. This is a prior-commit record, not a claim of remote CI for v0.56.

- [GitHub Actions run 41798951744](https://github.com/h-dot-seo/persona-for-research/actions/runs/41798951744):
  all four jobs passed for that exact commit, Ubuntu/Windows and Python 3.10/3.12.

Twenty-seven new tests cover bounded exact explanation fields, null versus legacy
absence, strict v1/v2 input contracts and downgrade rejection, full original/edited/
rejected histories, literal source-quote equality, stale reviews/maps, per-claim
reference/role isolation, missing prompts after retain, and declaration/route changes
without changed stored evidence. A frozen synthetic fixture was captured from v0.55
before production edits. Saved manual and imported answer inspections/text hashes,
answer and argument handoffs/bundles/envelopes replay identically; expected outputs
were not regenerated from the new implementation.

An independent read-only audit found no confirmed defect and executed 126 focused
tests. Separate adversarial checks exercised opposite roles at the same reference,
retained-but-missing explanations, uncited conclusions, terminal-control escaping,
and passive HTML tag/attribute/CSP safety. These are not browser/layout checks.
A preliminary new integration test called a nonexistent revision-impact API; its
call was corrected to the existing inspect API without changing production behavior.

No actual researcher data, provider call, external source transmission or browser
execution was used. All adoption choices were invented test fixtures. Supplied
explanations remain declared interpretations, not verified semantic support, source
authorship or approval. Actual-browser visual/keyboard/print QA remains
**BLOCKED/unverified**; no browser retry or restriction bypass was attempted.

## Prior v0.55 imported-argument walkthrough checks

Current local source release: v0.55 (opt-in synthetic imported-argument walkthrough).

- `python -m unittest discover -q`: 721 synthetic tests passed locally.
- `python -m compileall -q .`: passed; all Python files also parse with 3.10 grammar.
- `python audit_publication.py`: passed, 185 text files scanned including the manifest.
- `python verify_manifest.py`: passed, exact allowlisted inventory and file hashes.
- A standalone full 53-stage CLI route passed with recorded imported source-component
  origins, full pattern/method-application/answer/argument proposal histories, fresh
  invented source checks and JSON/text/passive HTML. Its complete HTML JSON snapshot matched the
  freshly produced report. All final answer decisions remained deferred.
- Minimal argument-import routes passed at 32 stages with mock extraction and 34
  with offline-import extraction, without requiring imported answers or other flags.
- Existing 39/46-stage routes retained their normalized golden inventories. HTML
  compatibility compares saved JSON and structural inventory, not byte identity
  or browser/layout behavior.

Most recent separately verified remote baseline: v0.54, commit
[`5614908d71d558a4764d8a164f6929bfcc7653af`](https://github.com/h-dot-seo/persona-for-research/commit/5614908d71d558a4764d8a164f6929bfcc7653af),
with 711 tests. This is a prior-commit record, not a claim of remote CI for v0.55.

- [GitHub Actions run 41796841090](https://github.com/h-dot-seo/persona-for-research/actions/runs/41796841090):
  all four jobs passed for that exact commit, Ubuntu/Windows and Python 3.10/3.12.

Ten new tests cover complete/minimal real CLI routes, seven injected new-stage
failures, 17 altered candidate/template fixtures, boolean/dependency checks before
writes, rejection of external response/review arguments, and normalized prior-mode
compatibility. Every candidate field and deferred review row is checked before
fixed fixture adoption. Failed stages preserve diagnostics and never produce the
final argument or COMPLETE marker. Declaration order late/early stays separate from
review topology early/late, with each step's original candidate matched by ID.
The rejected reverse bridge remains in history; adopting it instead is proven to
fail the accepted-cycle check. No new answer records or inherited citations appear.
Separate final answer review stays entirely deferred, with no logical/scientific
approval or execution.

An independent read-only source audit found no blocker in fixture gating, history,
preflight, failure handling, final defer or the documented routes. That audit did
not rerun tests; the full 721-test result above is the separate execution record.
The new 10-test suite and existing 10-test answer walkthrough suite also passed
as focused checks before the aggregate run.

No actual researcher data, provider call, external source transmission or browser
execution was used. Fixture adoption is not a general automatic-review policy.
Claims, assumptions and bridge text still need semantic and attribution review.
Actual-browser visual/keyboard/print QA remains **BLOCKED/unverified**; no browser
retry or restriction bypass was attempted.

## Prior v0.54 argument proposal checks

Local source release at this snapshot: v0.54 (offline argument proposals with explicit adoption history).

- `python -m unittest discover -q`: 711 synthetic tests passed locally.
- `python -m compileall -q .`: passed; all Python files also parse with 3.10 grammar.
- `python audit_publication.py`: passed, 184 text files scanned including the manifest.
- `python verify_manifest.py`: passed, exact allowlisted inventory and file hashes.
- A standalone 16-command CLI route prepared an explicit claim scope/handoff,
  imported canned argument bridges, created a deferred adoption form, rendered
  explicit synthetic review and exported the complete-history map. It composed
  imported argument/answer/pattern/application histories in JSON/text/passive HTML,
  reread selected invented source files, prepared/reopened an input card and
  compared the manual and imported maps. The accepted late-before-early declaration
  order remained separate from early-before-late topological review order.
- Final answer review stayed entirely deferred; all logical/scientific validation
  remained NOT_PERFORMED. Passive HTML's complete JSON snapshot matched exactly.

Most recent separately verified remote baseline: v0.53, commit
[`f305daa6b1df8bac5d893cbc929950bccf488091`](https://github.com/h-dot-seo/persona-for-research/commit/f305daa6b1df8bac5d893cbc929950bccf488091),
with 685 tests. This is a prior-commit record, not a claim of remote CI for v0.54.

- [GitHub Actions run 41794122820](https://github.com/h-dot-seo/persona-for-research/actions/runs/41794122820):
  all four jobs passed for that exact commit, Ubuntu/Windows and Python 3.10/3.12.

Twenty-six new module/integration tests cover explicit selected claim IDs, canonical
wrapper/inner package binding, exact inherited question context, original/edited
endpoint restrictions, source-quote conclusion rejection, individually legal rejected
alternatives versus jointly cyclic accepted maps, complete default-deferred review,
unique reviewed step IDs, and strict JSON/aggregate bounds. Declared candidate order
survives decision-list reordering; origin is matched by explicit step ID after
sorting for graph review. Manual declaration-order changes are not mistaken for
unchanged topology. Manual/imported comparisons separate adopted declarations from
full candidate/adoption/import history. Changed rejected graph history alters full
identity but not adopted content; changed rejected answer history or explicit answer
review presence/content invalidates the graph's scope. Invalid envelopes fail before
current source audits. Rejected graph endpoints do not become direct argument uses,
even when the same claims remain independently active in the answer.

An independent read-only design review identified declaration-order and imported-
authorship labeling as release-critical constraints. Implementation review
and regression tests cover those constraints and the inherited-question omission
found during review. The complete suite also retains the previous no-flag 39-stage
normalized-inventory check. This record does not claim a separate independent
post-implementation audit or broad resource stress testing.

No actual researcher data, provider call, external source transmission, new answer
claim record, inferred researcher speech or automatic citation transfer was used.
Free-text bridge/assumption content still needs semantic and attribution review;
structural checks cannot prove supported assertions or sound inference. Actual-
browser visual/keyboard/print QA remains **BLOCKED/unverified**; no browser retry
or restriction bypass was attempted.

## Prior v0.53 imported-answer walkthrough checks

Local source release at this snapshot: v0.53 (opt-in synthetic imported-answer walkthrough).

- `python -m unittest discover -q`: 685 synthetic tests passed locally.
- `python -m compileall -q .`: passed; all Python files also parse with 3.10 grammar.
- `python audit_publication.py`: passed, 180 text files scanned including the manifest.
- `python verify_manifest.py`: passed, exact allowlisted inventory and file hashes.
- A standalone complete 46-command CLI route passed with imported extraction,
  pattern, method-application and answer histories, current invented source-file
  checks, JSON/text and passive HTML. Answer-review decisions remained all deferred.
- The minimal mock-extraction + journey + answer-import route passed at 32 commands.
  The existing no-answer-import full route remains 39 commands.

Most recent separately verified remote baseline: v0.52, commit
[`c5d00385397e27719b14e267d83434d6d9a54e2b`](https://github.com/h-dot-seo/persona-for-research/commit/c5d00385397e27719b14e267d83434d6d9a54e2b),
with 675 tests. This is a prior-commit record, not a claim of remote CI for v0.53.

- [GitHub Actions run 41792621542](https://github.com/h-dot-seo/persona-for-research/actions/runs/41792621542):
  all four jobs passed for that exact commit, Ubuntu/Windows and Python 3.10/3.12.

Ten new tests cover actual full/minimal CLI routes, seven separately injected stage
failures, option/type validation before writes, rejection of external-response
arguments, canned-candidate/deferred-template contract guards, complete history
through passive HTML, separate final answer review, inactive rejected references,
non-inherited conclusion citations, and stale review/argument bindings after a
history-only edit. Each failed new stage leaves diagnostics but no COMPLETE marker.

The previous 39-stage inventory is compared with an independently captured v0.52
baseline. Only runtime paths and JSON formatting are normalized. Because legacy
report dictionary order varies across subprocess hash seeds, the HTML comparison
uses its exact JSON snapshot and tag/ID/href/attribute inventory, not byte equality
or visual layout. Dedicated normalization coverage includes Windows separators
and preserves unrelated backslashes. No expected scientific data is altered.

An independent read-only review passed 62 focused/adjacent tests and found no
blocker in fixture gating, default compatibility, history, defer or failure handling.

This demo accepts no external candidate/review files and invokes no provider. Its
three adopted/one rejected answer candidates are fixed invented fixture decisions,
not a general automatic approval policy. The final answer review is separate and
entirely deferred. Source matches do not establish semantic support, rights,
researcher fidelity or authenticated human review. Actual-browser visual/keyboard/
print QA remains **BLOCKED/unverified**; no browser retry or bypass was attempted.

## Prior v0.52 answer proposal checks

Local source release at this snapshot: v0.52 (offline answer proposals with full adoption history).

- `python -m unittest discover -q`: 675 synthetic tests passed locally.
- `python -m compileall -q .`: passed; all Python files also parse with 3.10 grammar.
- `python audit_publication.py`: passed, 179 text files scanned including the manifest.
- `python verify_manifest.py`: passed, exact allowlisted inventory and file hashes.
- The existing complete 39-stage synthetic CLI walkthrough passed unchanged.
- A separate 15-command real CLI route prepared/imported/reviewed/exported canned
  answer proposals, created an entirely deferred answer review and fresh argument
  bindings, rendered JSON/text/passive HTML with all three imported histories,
  reread explicitly selected synthetic source files, prepared an input card and
  reopened it. The full fresh JSON survived the static HTML snapshot exactly.
  Candidate adoption remained separate from answer review and research approval.

Most recent separately verified remote baseline: v0.51, commit
[`ccbe966ade6c329faeeefb3c04d584fd81e6ba40`](https://github.com/h-dot-seo/persona-for-research/commit/ccbe966ade6c329faeeefb3c04d584fd81e6ba40),
with 649 tests. This is a prior-commit record, not a claim of remote CI for v0.52.

- [GitHub Actions run 41789822962](https://github.com/h-dot-seo/persona-for-research/actions/runs/41789822962):
  all four jobs passed for that exact commit, Ubuntu/Windows and Python 3.10/3.12.

Twenty-six new synthetic tests cover exact evidence scoping, canonical inner-package
binding, temporal labels, no implicit source selection, strict quote equality,
finite/bounded JSON, stale/tampered envelopes and provenance, all-deferred templates,
complete explicit adoption and distinct final answer review. Original/rewritten/
rejected histories survive answer, evidence-scope, revision-impact, research-journey,
input-card, comparison and passive HTML paths. Rejected references do not become
active claims or argument premises; conclusion citations are not inherited.
Imported text/citation-role origin remains separate from source-record origin.
History-only changes invalidate answer reviews, argument maps and pinned files
without falsely reporting changed accepted prose. Comparison keeps imported-history
groups distinct from accepted declarations, including manual/imported transitions.
Synthetic evaluation freezes active metadata and full draft identity, not raw history.

An independent read-only audit passed 69 focused tests and found a revision-impact
binding gap: imported scopes bind the full checked package, while stale flags had
compared only persona/paper hashes. The imported path now exposes/compares both full
package hashes; a regression proves a metadata-only change is stale despite zero
changed reference endpoints. No additional blocker was found in the reviewed paths.
Resource limits were inspected and boundary-tested, not broadly stress-tested.

No actual researcher material, provider call or external source transmission was
used. No authorship, scientific validity, rights clearance or authenticated human
review is established. Actual-browser visual/keyboard/print QA remains
**BLOCKED/unverified**. No browser retry or restriction bypass was attempted.

## Prior v0.51 integrated starter checks

Local source release at this snapshot: v0.51 (optional incomplete integrated review starter).

- `python -m unittest discover -q`: 649 synthetic tests passed locally.
- `python -m compileall -q .`: passed.
- `python audit_publication.py`: passed, 175 text files scanned including the manifest.
- `python verify_manifest.py`: passed, exact allowlisted inventory and file hashes.
- A standalone CLI route passed from synthetic local intake to the optional starter,
  intentional rejection of the unchanged incomplete selection, explicit canned
  hypothesis authorship, new input-card preparation and fresh journey inspection.
  All answer/design/argument content stayed empty, all context decisions deferred,
  and source checking inactive in the new journey. No browser was invoked.

Most recent separately verified remote baseline: v0.50, commit
[`c9d27317fb33d5039c1ba20d881dfb1f1ce240ed`](https://github.com/h-dot-seo/persona-for-research/commit/c9d27317fb33d5039c1ba20d881dfb1f1ce240ed),
with 635 tests. This is a prior-commit record, not a claim of remote CI for v0.51.

- [GitHub Actions run 41787414641](https://github.com/h-dot-seo/persona-for-research/actions/runs/41787414641):
  all four jobs passed for that exact commit, Ubuntu/Windows and Python 3.10/3.12.

Fourteen new synthetic tests cover default-mode golden compatibility (normalizing
only runtime executable/repository/destination paths), exact reuse of existing
factories, both-or-neither options, invalid requests before writes, explicit relative
selection, null pattern/optional fields, inactive null-path source forms, zero-topic
matches and empty observation packages. The unchanged selection rejects before
artifact byte reads; arbitrary pattern IDs are not invented. Answer/review/link/
context edits preserve stale-binding failures. Every new artifact's write-failure
case preserves partial files without READY; all output serialization precedes mkdir.
No provider, network, source read, command execution or card preparation occurs in
setup. Real CLI commands preserve leading-dash/shell-looking values as data and
complete only after explicit synthetic authorship. Independent read-only review
passed 135 focused/adjacent tests, found no blocker, and prompted clearer context
regeneration and filesystem-scope guidance. Python 3.10 grammar was checked locally;
actual Windows/Python 3.10 execution is established only by separate remote CI.

READY confirms setup files, not a preparable journey or research approval. No
hypothesis, method choice, reviewer decision or source permission is inferred.
Actual-browser visual/keyboard/print QA remains **BLOCKED/unverified**; no retry or
restriction bypass was attempted.

The initial v0.51 remote run passed both Ubuntu jobs but exposed a Windows-only
golden-fixture decoding failure. The new test read UTF-8 text using the platform's
default encoding; the legacy report contains a non-ASCII arrow. Golden reads now
explicitly use UTF-8 and identify the exact failing filename without changing any
expected digest or production output. The initial attempt is preserved in
[run 41788952122](https://github.com/h-dot-seo/persona-for-research/actions/runs/41788952122).
This local correction is not a claim that corrected remote CI has passed.

## Prior v0.50 two-card comparison checks

Local source release at this snapshot: v0.50 (fresh comparison of two pinned research journeys).

- `python -m unittest discover -q`: 635 synthetic tests passed locally.
- `python -m compileall -q .`: passed.
- `python audit_publication.py`: passed, 173 text files scanned including the manifest.
- `python verify_manifest.py`: passed, exact allowlisted inventory and file hashes.
- The complete 39-stage synthetic journey, two separately prepared input cards and
  actual JSON/text comparison commands passed. One explicitly changed synthetic
  argument defeater was identified separately from unchanged claim declarations.
  Both full reports, current source checks, imported pattern/application histories
  and deferred answer decisions survived exact JSON/text round-trip. No browser ran.

Separately verified remote baseline at the v0.50 snapshot: v0.49, commit
[`0cc0115f64d7a256945fb377de8a62f88dae847c`](https://github.com/h-dot-seo/persona-for-research/commit/0cc0115f64d7a256945fb377de8a62f88dae847c),
with 611 tests. This is a prior-commit record, not a claim of remote CI for v0.50.

- [GitHub Actions run 41785421413](https://github.com/h-dot-seo/persona-for-research/actions/runs/41785421413):
  all four jobs passed for that exact commit, Ubuntu/Windows and Python 3.10/3.12.

Twenty-four new synthetic cases cover identical/relocated inputs, path-only and
raw-byte-only changes, explicit optional presence, question/context/year/pattern
switches, declared identity mismatch, both-card preflight before source audits,
separate current source roots, one source audit per selected side, changed source
bytes, stale artifacts and cached-report rejection. Declared claim/review/design/
argument/application changes remain distinct from resolved evidence changes;
reference and declaration additions/removals, reused IDs, observation reordering,
order-only edits and exact prompt multiplicities are covered. Imported pattern,
application and observation histories stay visible. Tests also cover no mutation or
network use, output limits without truncation, escaped text and real CLI failures.
Independent read-only review passed 23 initial comparison tests and 59 adjacent
journey/input-card/revision tests, with no blocker. Its suggested addition/removal
and order-only coverage is included in the final 24-case comparison suite.

No semantic comparison, change-of-mind inference, improvement score, scientific
validation, source authentication or human review authentication is claimed.
Disappeared prompts are not resolved issues. Actual-browser visual/keyboard/print
QA remains **BLOCKED/unverified**, with no retry or restriction bypass.

## Prior v0.49 input-card checks and compatibility repairs

Local source release at this snapshot: v0.49 (explicit pinned local journey inputs).

- `python -m unittest discover -q`: 611 synthetic tests passed locally.
- `python -m compileall -q .`: passed.
- `python audit_publication.py`: passed, 170 text files scanned including the manifest.
- `python verify_manifest.py`: passed, exact allowlisted inventory and file hashes.
- The complete 39-stage synthetic journey plus explicit input-card preparation and
  HTML reopen passed. All eleven selected JSON artifacts matched the card. The
  reopened journey remained exactly equal to the direct result except for the added
  per-file consistency record. Optional live source checks and imported histories
  stayed intact; all answer claims remained deferred. No browser was invoked.

Separately verified remote baseline at the v0.49 snapshot: v0.48, commit
[`c9aea40d7e7866bffa580a2201ba16249c65851c`](https://github.com/h-dot-seo/persona-for-research/commit/c9aea40d7e7866bffa580a2201ba16249c65851c),
with 585 tests. This is a prior-commit record, not a claim of remote CI for v0.49.

- [GitHub Actions run 41782036589](https://github.com/h-dot-seo/persona-for-research/actions/runs/41782036589):
  all four jobs passed for that exact commit, Ubuntu/Windows and Python 3.10/3.12.

Twenty-six new synthetic cases cover explicit null/default selection, raw and
logical JSON hashes, changed-file/whitespace rejection, no silent rebind, stale
cross-artifact validation, complete path preflight, symlink/root/directory/FIFO
checks, detected replacement during resolution/reading, bounded card loading,
same-object canonical path spelling and Windows reparse-point rejection,
aggregate byte limits, explicit source-root pairing, changed sources, preserved
optional imported history, relocation of identical files, no input mutation or
network call, strict CLI failures and all three render formats. The final HTML
snapshot retains all inspected fields plus the separate input-file check.
Independent read-only review of the initial implementation passed 44 focused
tests and prompted bounded regular card-file loading plus alias-detection
hardening. The subsequent Windows compatibility fix passed 26 focused local tests;
a second independent review was unavailable. Stable-filesystem and unsigned
history limits are explicit; no atomic multi-file snapshot or hostile-filesystem
proof is claimed.

The first v0.49 remote attempt passed both Ubuntu jobs but failed both Windows jobs
when lexical path comparisons mistook normal canonicalization for replacement.
The failed attempt remains visible in
[run 41783936703](https://github.com/h-dot-seo/persona-for-research/actions/runs/41783936703).
Preflight now checks device/inode/type identity across canonicalization and rejects
symlinks and Windows reparse points in both spellings, rather than requiring
identical path spelling. Same-object normalization and different-object substitution
have separate regressions. A second Windows run reached only a regression-fixture
failure: its synthetic reparse attribute was attached to the pre-canonical spelling,
so it never reached the tested artifact. The fixture now targets the canonical file
without weakening the production reparse rejection or the no-read assertion. That
attempt remains visible in
[run 41784964842](https://github.com/h-dot-seo/persona-for-research/actions/runs/41784964842).
Corrected v0.49 subsequently passed all four jobs in run 41785421413, separately
verified above before the v0.50 changes.

**Actual-browser visual, keyboard and print QA remains BLOCKED/unverified.** No
browser retry or restriction workaround was attempted in this increment. The
previous Chromium OS-socket failure and the distinction between static/CLI checks
and actual presentation behavior remain documented in
[local HTML review](LOCAL_HTML_REVIEW.md). Input-card checks are not source
authentication, semantic support, human review authentication or research approval.

Twenty-three new synthetic cases cover inert HTML/strict element and attribute
allowlists, escaped source/model/operator content, controls and Unicode, unique
hashed internal anchors, complete JSON round-trip and distinct snapshot digest,
full proposal and imported-observation history, current/recorded source separation,
unused-source and missing-excerpt gaps, one fresh inspection and one read per selected
file, invalid inputs before reads, final UTF-8 limits, CLI failures without partial
output, unchanged legacy formats, and the 39-stage demonstration with late failure.
Independent read-only inspection found no security/schema/history blocker and
prompted consistent reading-order guidance. These are parser/logic/CLI checks.

**Actual-browser visual, keyboard and print QA: BLOCKED, not passed.** Installed
Chromium failed before opening the synthetic local file because OS socket creation
was denied. The normal attempt and an approved expanded execution both failed.
No screenshot, responsive-geometry result, keyboard result or print-completeness
claim was produced. CSS and native disclosure controls are included, but static
checks do not establish their real-browser behavior. No browser dependency or
external resource was added to hide this limitation. See
[local HTML review](LOCAL_HTML_REVIEW.md) for the explicit presentation scope.

Twenty-four new synthetic cases cover bounded offline application handoff/import,
all-deferred review, explicit complete rewrites, multiple alternatives with at most
one accepted candidate per step, no retargeting, separate candidate/application
decisions, blank defer for rejected/unproposed steps, original/reviewed/rejected
history, unsigned provenance, exact references, stale bindings, strict JSON, no
network/source access and detached reports. Nested imported pattern/application
histories survive text and JSON. An invalid envelope fails before source reads
using a valid source selection; the valid flow composes with current byte/quote
rechecks without changing the method's no-source-read scope. Existing active evidence,
answer/design uses and argument/transfer reviews stay unchanged. Real CLI import,
review/export/consumption, 38-stage walkthrough and failure/no-completion behavior
pass. Independent read-only review found no blockers and prompted stronger source
read-order and nested-history regressions. No provider was called or authenticated,
checks were not executed, and accepted declarations did not become method approval.

Twenty-five new synthetic cases cover explicit method-pattern application: every-step
default defer, consider/exclude prerequisites, missing checks/failure criteria, exact
selected references, parent/component distinction, target-step-only link membership,
full stale-input bindings, imported original/reviewed/rejected history, separate
source/pattern/design/application roles, future/same-year context and no inherited
conditions. All nine decision/role combinations preserve previous journey semantics
and active evidence exactly. Optional annotations validate before source rereads;
legacy no-option snapshots remain exact. Real CLI template/inspection/composition,
32-stage demonstration and late failure/no-completion behavior pass. Independent
read-only review found no blockers. Proposed checks were not executed, filled text
was not scored, and no researcher recommendation or method validation was inferred.

The first v0.46 remote run exposed an optional-positional CLI parsing difference
on Python 3.10 (both operating systems); Python 3.12 jobs passed. The method-application
CLI now uses explicit intermixed argument parsing, with regression cases for flags
before, between and after positional inputs. This fixes the observed command-order
compatibility failure without changing review semantics. The failed attempt remains
visible in [run 41778017967](https://github.com/h-dot-seo/persona-for-research/actions/runs/41778017967);
the corrected commit subsequently passed all four jobs in run 41778499568 (the separately verified v0.46 baseline).

Twenty-nine new source-recheck and walkthrough cases cover exact all-paper selection,
full preflight before reads, stale/invalid source forms and package/rule disagreement,
path escapes, nonregular files, detected replacement, hash mismatches without refresh,
aggregate budgets, malformed UTF-8/sections, missing and unmatched quotes, separate
component checks, no-record coverage, unused-paper gaps and unchanged recorded labels.
Live journey rendering reads each selected file once, rejects cached reports as
selections and preserves exact v0.44 no-source JSON/text snapshots. The 30-stage
synthetic demo retains default-defer review and fails without completion if source
bytes change. Independent read-only review found no blockers and prompted added
unused-quote and simultaneous missing-quote/locator cases. These are current local
consistency checks, not authenticity, semantic support or extraction-history replay.

Twenty-six new synthetic cases cover the integrated research journey and extended
CLI walkthrough: consistent draft review across domains, rejected/deferred claims,
exact parent/component separation, outside-topic relationship-only and context-only
references, multiple uses and dual roles, no premise-to-conclusion citation transfer,
future review context, full input bindings, imported pattern/observation provenance,
strict input/output limits, immutability, no source/provider calls, real CLI JSON/text,
legacy default modes and late-stage failure without a completion marker. Independent
read-only review found no blocking issue and prompted the outside-scope/multiple-use
cases. This composes current artifacts, not absent extraction history: prior lineage
stage bundles are not accepted or replayed by the research-journey report.

Eighteen publication-context regressions cover typed/directional/symmetric source
relationships, strict basis refs, recorded-check validation, missing quotes and
uncertainty, selected/one-sided/outside scopes, later/same-year context, unchanged
roles/decisions, imported observation and model-pattern provenance, strict CLI input
and exact v0.42 no-context payload/text snapshots. Independent review confirmed
provenance and role preservation and prompted a missing-relationship wording fix.
No relationship, independence, intellectual influence or author belief is inferred.

Twenty-one observation-append regressions cover explicit selection/new identity,
complete review, null gaps, rejected counterevidence, local-source changes, exact
replay, all base-field bindings, origin tampering/transplants, retained history,
projection/rule/endpoint/reader continuity, reasoning-only audit scope, manual-edit
rejection, JSON aliases, bounded output and real CLI execution. Independent review
found a broad reasoning-chain status that understated inherited observation history;
both chain and single-revision summaries now explicitly disclose that history.
All checks use invented sources and canned responses, not actual inference.

Twelve additional evidence-use regressions cover exact reference/role coverage,
source-specific null boundaries, explicit reviewed explanations, removed/dual-role
references, rejected reasons, version isolation, tampering, rendering and the v2
CLI. Verified v0.40 canonical payload/text snapshots remain unchanged. Changing
only a reviewed rationale changes envelope and transfer identity, while the plain
worksheet projection hash intentionally excludes explanations. Independent probes
confirmed the complete binding, source-gap preservation and no automatic approval.

Eighteen model-pattern regressions cover the complete real CLI route from topic
handoff to import, default-deferred review, explicit envelope export, pattern
inspection and context transfer. Original imported versus reviewed interpretation
labels remain distinct. Rejected counterevidence, reference edits, missing quotes,
null gaps, stale/tampered history, unselected-source authorization, source identity,
bounded inputs and deep-copy isolation are checked. Independent read-only review
also exercised adversarial artifacts, out-of-topic package changes and forbidden
source/provider operations. No actual model or researcher source was used.

Twelve first-observation regressions cover empty source observations, preserved null
gaps, default defer, original/reviewed label separation, rejected challenges, fixed
evidence, stale/tampered artifacts, task isolation, escaped provenance text and local
CLI execution. These outputs cannot enter manual-card or reasoning-candidate gates;
acceptance never creates a runtime package.

Thirteen file-backed regressions cover all handoff/review CLI modes, stale bytes
and metadata, preamble-only changes, bounded source reads, authorization/path
preflight, poisoned embedded text, alias/receipt detachment and input preservation.
No source hash is silently refreshed. Generic candidate packages retain their
existing segment/quote semantics rather than manufacturing local-file receipts.

These checks include offline model-request preparation/import, complete input and
response bindings, declared provenance, default-deferred review, explicit target
replacement, imported-versus-mock attribution, mixed-origin revision chains and both
the 15-stage default and 17-stage imported-fixture CLI journeys. Initial provenance
remains explicitly unaudited even after replacement; replay is artifact consistency
only. No inherited import metadata is invented from a hash.
They use synthetic/canned responses, not an actual model. No real author source,
paid API, authenticated provider provenance, semantic support, scholarly fidelity
or scientific validation was evaluated. Permission declarations and hashes are not
authentication or rights clearance.

## Historical incremental records

The counts below record earlier snapshots, not the current test-suite size. They
are retained as development history; use the current snapshot above for present
verification status. Old local-pass statements do not establish later remote CI.

Release preparation date: 2026-11-02 (Asia/Seoul).

- Python standard-library unittest: 3 synthetic tests passed.
- Limited public-file/type/secret-pattern scan: passed.
- Manual selected-content review: no actual conversation, researcher corpus, private
  configuration, credential, real experiment or article/book/figure asset selected.
- Examples: synthetic; no scientific or persona-predictive validation claimed.
- Private history import: none; new public repository with a separate initial history.

The scanner is not a complete secret detector, anonymizer or legal clearance tool.
Framework-level code/tests and general methods were selected; private source DBs
and third-party source materials were excluded rather than redacted and republished.
Remote publication is verified separately after committing; this file does not
claim an upload has succeeded merely because local tests passed.

## 2026-11-03 increment

Run `python -m unittest discover -v` and `python audit_publication.py`.
New tests exercise the documented synthetic workflow and rejection boundaries.
On restricted Windows hosts, set TEMP and TMP to an authorized writable directory.
No real corpus, account data, or scientific fidelity evaluation was used.

Second increment: 6 tests passed; failure boundaries and deterministic repeated results covered.

Third increment: 8 tests passed, including supplied-evidence rejection and deterministic output. No external model/search integration tested.

Fourth increment: CLI end-to-end scenarios and failure recovery added. Local tests: 9 passed. Remote CI status is recorded in the repository's GitHub Actions history.

Cloud methodology chronology increment: 18 standard-library tests passed locally,
including 9 new synthetic cases for research/review separation, duplicate-paper
counting, same-year disagreement, cross-year variation, challenge-only evidence,
exact-condition separation, quote provenance, stable chronological order and input
authorization. Publication scan and byte-manifest verification passed. No remote
CI run or real-scholar validity evaluation is claimed for this uncommitted increment.

Fifth increment: 12 local tests passed. New CLI paths, source boundaries, deterministic output and tamper/no-overwrite checks are covered. Remote matrix CI results are in the GitHub Actions history.

Combined cloud verification: local-file intake and chronology integration passed 21 tests; source ZIP and per-file hashes matched the handoff. No real corpus was used.

Reasoning-card increment: 29 local standard-library tests passed. Eight new cases
cover per-component quote/locator checks, claim-type separation, missing dimensions,
challenge stance, holdout rejection, malformed dimensions, tamper detection and
deterministic nonmutating output. Publication and manifest checks passed. Inputs
are synthetic; no LLM, automatic extraction or semantic assessment was performed.

Verification-receipt increment: 36 local tests passed, including forged JSON labels,
quote-only versus local-byte verification, changed intake rejection, serialized
receipt loss, knowledge payload tampering and caller-data isolation. Publication,
manifest and compilation checks passed. The receipt is an in-process integrity
mechanism, not authentication against a Python caller or source authenticity proof.

Coverage-diagnostic increment: 42 local tests passed. Six new cases verify partial
and absent coverage, statement/interpretation and quote-match counts, duplicate-paper
counting, challenge links and complete-field boundaries. Publication scan, manifest
verification and compilation passed. Counts are descriptive, not scholarly scores.

Runtime-projection hardening: independent adversarial review found unknown nested
metadata could escape into knowledge and reasoning cards, including explicitly
labeled holdout extras. A supported-field projection and scalar-type checks close
that structural path. Seven regression cases cover both intake routes, each nesting
level, retained legitimate quotes, raw-section omission, claim types, malformed
shapes and preflight ordering. All 49 local tests, publication/manifest checks and
compilation pass. No semantic privacy detection is claimed.

Read-only release comparison: 59 local tests passed. Ten new cases cover identical
and wrapped packages, build-only changes, added/removed sources, changed source
hashes and observations, cross-identity/tamper/legacy rejection, nonmutation and the
CLI success/error paths. Publication scan, manifest verification and compilation
passed. Comparisons are structural and do not approve canonical policy changes.
Independent review identified a numeric-type equality gap before publication;
canonical JSON hashing and an integer/float regression close it.

End-to-end/invalid-input review: 63 local tests passed. Invalid corpus/paper/observation
container types and selected metadata shapes now fail common preflight before
source-file access; this is not complete annotation validation. Tested CLI rejection
cases emit no traceback or partial JSON. A real subprocess
round-trip covers local byte/quote checks, reasoning/coverage, candidate disagreement,
release comparison, source tampering and unchanged prior packages. Publication,
manifest and compilation checks passed. See docs/WORKFLOW_REVIEW.md for user-facing
limitations and real-corpus evaluation prerequisites; no model or real corpus used.

Strict JSON boundaries: 69 local tests passed. Duplicate authorization/split keys,
non-finite/overflowing numbers and excessive container nesting are rejected. Tests
exercise all six CLI boundaries, Unicode/finite inputs and preserved original-byte
hash checks. Publication scan, manifest and compilation checks passed. Parsing
guards remove ambiguity; they do not authenticate declared permissions.

Legacy runtime authorization: 73 local tests passed. The shared validator now
requires exact boolean authorization for every runtime paper, including packages
without the newer knowledge binding. Four regression cases cover missing, false
and truthy nonboolean values, allowed legacy/current packages and standalone CLI
rejection. Publication scan, manifest and compilation checks passed. Declared
authorization remains an input contract, not independently verified permission.

Source-repetition classification: 78 local tests passed. Independent review
reproduced two byte-verified IDs pointing to one file being counted as repeated
paper evidence. Five new cases verify same-file grouping, distinct hashes,
single-paper repeated observations, mixed stances and challenge-only patterns.
All observations remain available; hash differences do not imply independence.
Publication scan, manifest verification and compilation passed.

Compact-review increment: 86 local tests passed. The real CLI renders a bound
synthetic candidate in 17 lines rather than its roughly 16 KB JSON package, with
all matched support/challenge records preserved. Eight tests cover wrapper-summary
forgery, absent topic, tampering/legacy rejection, nonmutation, terminal controls,
UTF-8 output and CLI failure without partial output. The end-to-end subprocess
test includes the renderer. Publication scan, manifest and compilation passed.
The renderer reports recorded checks only and does not reverify source bytes.

Mock extraction contract and exact publication inventory: 103 local tests passed.
Ten adapter cases verify pre-invocation authorization/holdout/hash gates, allowed
request fields, response schema/quote limits, candidate-only status, absent automatic
promotion, rejected external providers and real CLI success/failure. Seven manifest
cases cover unlisted ordinary/cache files, missing/changed files, canonical paths,
duplicate/case aliases, narrow metadata exclusions and symlink read rejection.
The synthetic mock performs no AI inference or external transmission. Independent
code review passed; real-model quality and prompt-injection resistance are not evaluated.

Operator-review gate: 115 local tests passed. Twelve new cases cover exact bundle/
corpus binding, target isolation, explicit replacement, rejected/deferred decisions,
unknown/oversized fields, fabricated quotes, provider isolation, default-defer
templates and the real CLI extraction-to-revision-to-view/comparison chain.
Independent adversarial review found and verified a fix for shared Python-reference
aliasing that could otherwise alter untargeted counterevidence. No canonical update,
actual human authentication, external model call or real-scholar evaluation occurred.

Read-only target inventory: 120 local tests passed. Five new cases exercise all
same-paper support/challenge targets without selection, projected component fields
with exact original replacement hashes, stale corpus/invalid source rejection,
empty target lists, no provider calls or mutation, and actual CLI mode conflicts.
The inventory is not a signature: changed valid candidate text produces a new
bundle hash, while an existing review remains bound to its original bundle.

Publication timeline: 129 local tests passed. Nine new cases cover chronological
support/challenge and research/review records, duplicate source hashes, independent
component locators and missing question framing, exact topic filtering, mismatched
rules/bindings/authorization, raw metadata exclusion, recorded-check label types,
stable paper ordering, UTF-8/control handling, and a real intake-to-JSON/text CLI
round-trip. No actual researcher, external inference or career narrative is tested.
Independent review found identical text for raw versus quote-verified inputs;
recorded source/observation/component labels now distinguish them, with a regression
test and the explicit not-rechecked boundary retained.

Runtime source/rule consistency: 136 local tests passed. Seven new cases reject
rehashed source/rule mismatches, added/removed/reordered rules and inconsistent
recorded quote labels across planning, compact review and timeline. Comparisons
remain diagnostic; legacy authorized planning with matching source observations
still works. Tests verify no input mutation, provider/source-file access or partial
CLI output. This does not authenticate consistently rewritten inputs.
Independent review also found that planning returned a cached trajectory without
checking it; planning now reconstructs that summary from validated source fields.

Topic discovery: 144 local tests passed. Eight new cases cover exact/Unicode
casefold groups, whitespace and synonym separation, observation-only scopes,
component/claim/stance coverage, multiple topics and both stances in one paper,
duplicate hashes, empty topics, tampering/holdout rejection, no mutation/provider
or source reads, and safe text output. Actual CLI intake → discovery → timeline/
compact review uses a returned topic key. No semantic retrieval or ranking occurs.

Explicit cross-publication links: 154 local tests passed. Ten new cases cover
different methods/topics and backward-year links, separate source/edge claim types,
empty templates, endpoint indexes and missing dimensions, stale bindings/reordered
records, authorization, strict schema/duplicates/self-links, preserved conflicts
and cycles, same-source flags, metadata exclusion, recorded checks and safe text.
Actual CLI intake → empty template → explicitly simulated link → JSON/text review
runs without mutation, source rereads or provider calls. No link validity or real
researcher reasoning process is inferred.

Design-scenario traceability: 164 local tests passed. Ten new cases cover source
versus proposal attribution, missing criteria not borrowed from sources, unlinked
steps and unreferenced challenges, package/link binding changes, strict schema,
explicit conflicting roles and distinct-link counts, empty templates, alias-safe
nonmutation, no provider/source access and escaped text. Real CLI intake → links →
empty proposal template → explicitly simulated design → JSON/text review succeeds.
No experimental design quality, source applicability or researcher fidelity is scored.

One-revision design lineage: 172 local tests passed. Eight new cases exercise the
actual mock→operator-review→design→audit CLI sequence, proposed/reviewed claim labels,
selected evidence routes and missing criteria, exact replay despite recomputed
hashes, stale sources/candidates/reviews, rejected/deferred reviews and inherited
origins on unused dimensions. Read-only/provider isolation, JSON equivalence and raw
text exclusion are checked. Independent probes confirmed unused inherited origins
remain incomplete even with no proposed steps. No complete historical provenance,
authenticated review or scientific validity is asserted.

Declared revision-chain audit: 180 local tests passed. Eight new cases cover
two-stage add/replace replay, repeated candidate IDs, exact projected continuity,
skipped/reordered stages, changed counterevidence/new sources, stale replacements,
identity reuse, and initial history warnings surviving replacement. Final marker
coverage is separate from pre-chain history. Actual two-review CLI → chain audit,
JSON-equivalent aliases, no provider/source access and raw-text exclusion are tested.

## 2026-11-08 Public boundary cleanup (0.69-public-boundary-cleanup)

Removed references to a private development log from this record; remote CI
results are the public GitHub Actions history. The test workflow now also runs on
`main`, and this cleanup precedes merging the workflow branch into `main`. No code
path, test or fixture changed; the manifest was regenerated for the edited text files.

## 2026-11-08 Human validation records (0.70-human-validation-records)

Current local source release: v0.70 (detached human validation records).

- `python -m unittest discover -q`: 980 synthetic tests passed locally in 636.393 seconds
  (3 pre-existing platform-conditional skips in `test_journey_inputs`: the FIFO and
  Unix-unlink cases; none in the new module). The v0.69 tree discovers 962 tests with the
  same loader.
- `python -m compileall -q .`: passed; 140 Python files also parse with 3.10 grammar.
- `python audit_publication.py`: passed, 226 text files scanned including the manifest.
- `python verify_manifest.py`: passed, 225 exact allowlisted entries and file hashes.

The architecture's fourth validation axis, human validation, previously had no tooling: a
persona payload could only ever carry `validation.human_validation: NOT_PERFORMED`. The new
`human_validation.py` records a rater assessment as a detached document bound to both
logical payload hashes (`persona_payload_sha256`, `knowledge_papers_sha256`), the way the
predictive axis keeps its holdout labels outside the package. `template` writes a blank
record (one blank rater, every available topic, one `NOT_ASSESSED` item per rule,
`status: null`) with exclusive creation outside the repository. `check` validates exact
fields, the `AGREE`/`PARTIAL`/`DISAGREE`/`NOT_ASSESSED` enum, a strict `YYYY-MM-DD` date,
bounded nonblank text (1 to 32 raters, 1 to 4096 items, identifiers of at most 128 and free
text of at most 2000 characters; every error names the field and its limit) and the
mechanical `LABEL_DISTINCT_ONLY` rater check, then derives `CURRENT_PACKAGE` or
`STALE_PACKAGE` by recomputing the hashes; a record for a different `author_id` is an
error, not a stale record. Only a record bound to the current package has its items
resolved against it (rule IDs and topics that exist in the supplied package, scope
consistency). Rule IDs are per-build positions, so a stale record's items and topics are
not re-resolved: `check` keeps the structural checks and per-label counts, reports
`items_resolved_against_current_package: false` and lists the recorded IDs and topics that
are absent from the current package, instead of failing or re-attributing a recorded
judgement to whichever current rule now carries the same ID. `status` reports
`RECORDED_CURRENT`, `STALE_PACKAGE` or `NOT_PERFORMED` with per-label judgement counts and
each record's own logical sha256, and names the persona payload's declared value as
unchanged. `review_package.py --human-validation RECORD.json` (repeatable) appends the same
read-only axis lines and reads its records through the same 8 MiB combined input budget as
`check` and `status`; without the option its output is byte-identical to v0.69. Packages
may be supplied as the `PERSONA.json KNOWLEDGE.json` pair or as one bound package/wrapper
file. Combined inputs are bounded at 8 MiB, output at 16 MiB, and text output escapes
control characters taken from data.

No persona payload field changed and no knowledge binding was rewritten: the shipped
`examples/persona.json` and `examples/knowledge.json` are byte-identical and still validate.
The new fictional record `examples/manual-human-validation.json` binds to
`examples/trajectory-conditions-package.json` (two invented rater labels, six rules on one
topic, `AGREE=3; PARTIAL=1; DISAGREE=1; NOT_ASSESSED=1`), because the minimal example
package has no rules to assess and no bound knowledge payload for the release review.

Eighteen new tests in `test_human_validation.py` cover template bindings and listings for
the pair, package and wrapper forms; the shipped fixture; an unedited template failing
`check`; stale detection after a rebound rule edit versus hash tampering as an error;
identity mismatch; stale records against packages rebuilt with a removed, reordered or
renamed paper, reported without re-resolution and exiting 0 from `check`, `status` and the
release review while structural errors in such a record still fail; unknown items, unknown
topics and scope mismatches; author, operator and reviewer label collisions; enum, date and
field strictness; the status CLI for all three states with byte-identical inputs; the
unchanged example pair; exclusive output against existing files, missing parents,
repository paths and symlinks; UTF-8 output under `PYTHONIOENCODING=ascii`; escaped control
characters; the release-review option with unchanged default output; no input mutation,
file reads or provider calls; input and output byte bounds including the release-review
record budget; and the guide's command block executed exactly as written. The focused
module and its neighbours passed in a serial run of 47 tests in 4.612 seconds; the 15-stage
synthetic walkthrough still completes with `COMPLETE.json`; the six documented commands were
also run by hand into a fresh external directory. `docs/HUMAN_VALIDATION.md`, README,
SKILL.md, the architecture axes note and a quickstart pointer were added or extended, and
the manifest was regenerated for 225 files.

Review round 1 (same release): a skeptic reproduced that a stale record failed `check`,
`status` and the release review whenever one of its item IDs or topics no longer occurred in
the rebuilt package, and that a rebuilt package with the same rule count re-resolved a stale
record's items against different rules. Both are fixed as described above and covered by
the two rebuilt-package tests; the release-review record path now shares the 8 MiB input
budget, and the guide states the numeric bounds that `check` enforces.

Not claimed: a recorded assessment is a documented assertion by named labels about listed
items of one exact package. It is not generalization to other topics, not fidelity to the
real researcher, not a score or verdict, and label distinctness is not verified
independence, expertise or blinding. Hashes bind a record to a payload but do not
authenticate raters or dates. A stale record's item IDs that still occur in a rebuilt
package do not establish that they denote the same rules. No real rater, researcher, model
call, network access or canonical update was involved, and promoting a status into a
package remains a release decision taken through the normal lifecycle.

## 2026-11-08 Documentation restructure (0.71-documentation-restructure)

Current local source release: 0.71 (documentation restructure). No Python module, test,
fixture or example changed: every `.py` file and every file under `examples/` is
byte-identical to v0.70, and the edited existing text files are `README.md`,
`VALIDATION.md`, `SKILL.md` and one link target in `docs/REVIEW_WORKSPACE.md`.

- `python -m unittest discover -q`: 980 synthetic tests passed locally in 695.315 seconds
  (3 pre-existing platform-conditional skips in `test_journey_inputs`: the FIFO and
  Unix-unlink cases). The count is unchanged from v0.70.
- `python -m compileall -q .`: passed; 140 Python files.
- `python audit_publication.py`: passed, 230 text files scanned including the manifest.
- `python verify_manifest.py`: passed, 229 exact allowlisted entries and file hashes.

`README.md` shrank from 37,822 to 11,841 bytes. It keeps, in this order: the title and
both taglines, a link to the Korean guide, the scope statement and the implemented-features
list, the "Start here" section with its two command blocks byte-identical, the "Quick start"
section with its command block byte-identical, a twelve-row "Commands at a glance" table, a
"Documentation" index with one line per guide, the design/boundary links and the rights
sentence. Four files were added under `docs/`. `WORKFLOWS.md` holds every moved README
section verbatim (the walkthrough-flag narrative and the strict JSON-input statement, the
two-layer and binding explanations, the research-plan, intake, local-file, release-review,
candidate-contract, operator-review, audit/link/timeline, answer/argument and pattern
sections, including all seven moved command blocks), demoted one heading level and grouped
under ten task headings that name their topic guides, with link targets rewritten for the
new location. `COMMANDS.md` lists all 45 argparse command-line scripts plus
`audit_publication.py` and `verify_manifest.py` with the exact `usage:` line printed by
`--help`, all 47 subcommands with a one-line purpose, the ten library modules without a
command line, and the guide for each script. `README.ko.md` is a Korean guide (purpose,
publication scope, installation and quick start, main commands, boundaries and non-claims,
document index) that keeps every command, file name and identifier in its original form.
`VALIDATION_HISTORY.md` holds every dated entry of the former `VALIDATION.md` verbatim, in
the same order, under a one-paragraph preface; only two relative link targets were rewritten
for the `docs/` location. `VALIDATION.md` is now a short current snapshot: release, CI
matrix, local verification steps, non-claims and a latest-change pointer. `SKILL.md` changed
one paragraph so that it points to `docs/COMMANDS.md` and `docs/WORKFLOWS.md` instead of a
README section that no longer exists, and `docs/REVIEW_WORKSPACE.md` now links the moved
"Evidence-bound answer drafts" section in `WORKFLOWS.md` instead of the README anchor; its
command blocks are unchanged. The manifest was regenerated for 229 files.

Verification specific to this change: a local link checker resolved every relative Markdown
link, with or without a heading anchor, in all root and `docs/` Markdown files (544
links in 57 files) to an existing file and every anchor to an existing heading
(URLs with a scheme were skipped), confirmed that every
`docs/*.md` file is linked from the README index and that the guides named by `SKILL.md`
exist at their paths; each of the ten fenced `sh` blocks of the previous README was found
byte-identical in the new README or in `docs/WORKFLOWS.md`, and the "Start here" and "Quick
start" sections kept exactly their blocks; every existing guide other than the one link in
`docs/REVIEW_WORKSPACE.md` is byte-identical to v0.70 (the only guide whose command block a
test executes is `docs/HUMAN_VALIDATION.md`, and `synthetic_walkthrough.py` reads no guide);
all Markdown files are UTF-8 without BOM and LF-only; the start-here and quick-start
commands were run by hand once, the 15-stage demo into a fresh external directory.

Not claimed: this is a documentation change. It adds no behaviour, no test and no fixture,
and does not re-verify scientific meaning, source authenticity, browser QA or remote CI; the
GitHub Actions history for the merged commit is the remote record. The Korean guide is a
translation of documented behaviour, not an additional specification, and the one-line
purposes in `COMMANDS.md` summarize the guides without adding guarantees.

## 2026-11-08 Test package and dispatcher (0.72-test-package-and-dispatcher)

Current local source release: 0.72 (test package and dispatcher). The 83 `test_*.py` modules
moved from the repository root into the `tests/` package (`tests/__init__.py` holds one
docstring line); the root gained the dispatcher `persona_cli.py` and the package gained
`tests/test_dispatcher.py`. No implementation module, fixture or example changed: every
non-test `.py` file other than the new dispatcher and every file under `examples/` is
byte-identical to v0.71, `.github/workflows/tests.yml` is unchanged, and the documented
`python <script>.py ...` commands, including every fenced `sh` block of the tested guide
`docs/HUMAN_VALIDATION.md`, are unchanged.

- `python -m unittest discover -q`: 989 synthetic tests passed locally in 626.384 seconds
  (3 pre-existing platform-conditional skips in `tests/test_journey_inputs.py`: the FIFO and
  Unix-unlink cases). Before the move the same loader discovered 980 tests, which passed in
  694.145 seconds on a byte-identical copy of the v0.71 tree; after the move it discovers the
  same 980 tests under their `tests.` names plus the 9 new dispatcher tests, with no load
  error.
- `python -m compileall -q .`: passed; 143 Python files. `persona_cli.py`,
  `tests/__init__.py` and `tests/test_dispatcher.py` also parse with 3.10 grammar, and the
  dispatcher tests also passed under a second local interpreter (3.13).
- `python audit_publication.py`: passed, 233 text files scanned including the manifest.
- `python verify_manifest.py`: passed, 232 exact allowlisted entries and file hashes.

Moved tests. In the moved modules every `ROOT = Path(__file__).resolve().parent` that meant
the repository root became `Path(__file__).resolve().parents[1]` (35 module constants and one
inline path in `tests/test_journey_argument_render_reuse.py`; each occurrence was checked and
none used the parent as a scratch base), and the 80 cross-test import statements (`import
test_x as alias` and `from test_x import name`, including three function-local ones) became
`tests.test_x`. Tests that address scripts and examples relative to the current directory
keep working because `python -m unittest discover` runs from the repository root, exactly as
CI does. The 41 documentation lines that named `python -m unittest test_x -v` across 30
guides now name `python -m unittest tests.test_x -v`, and `docs/WORKFLOWS.md` names
`tests/test_cli_e2e.py`; `docs/VALIDATION_HISTORY.md` keeps its earlier entries verbatim.

Dispatcher. `python persona_cli.py list` parses the root `*.py` files with `ast`, without
importing them, and prints one line per script that has an `if __name__ == '__main__'` entry
point: the file name and the first sentence of its docstring, in name order, 47 lines that
match the script entries of `docs/COMMANDS.md`. `python persona_cli.py run <script>
[args...]` resolves the exact file name against the dispatcher's own directory, sets
`sys.argv` and executes the script in-process through `runpy.run_path(...,
run_name='__main__')`, so arguments, output, `--help` and exit code are the script's own; a
name that is not an existing root script with an entry point (a path, a library module, the
dispatcher itself, a case alias, a test module) is rejected with exit code 2 and no stdout. No
shell is involved and the dispatcher writes no file. The nine tests cover the list format and
its agreement with the command reference and with an independent text search for the guard;
byte-identical stdout, stderr and exit codes for six direct-versus-dispatched invocations
(`verify_manifest.py`, a passing and a failing `persona.py` validation, an argparse error,
`--help` and a `human_validation.py status` text report); help forwarding; every rejection
class; the boundary text of `--help`; that `list` imports no repository module and neither
path imports `subprocess`; that a `__file__`-relative module (`human_validation.py template`)
still refuses an output inside the repository and writes one outside it; and that nothing is
created in the current directory, which is a temporary one in every test.

Deliberately not moved: the implementation modules stay flat at the repository root. Six of
them resolve files relative to their own location (`human_validation.py`,
`review_workspace.py`, `revise_local.py` and `synthetic_walkthrough.py` define a module-level
`ROOT`; `verify_manifest.py` and `audit_publication.py` locate the repository in their
`__main__` block), the documented commands are `python <script>.py ...` at the root, and
packaging would have changed bytes, paths and bindings for no documented gain. `README.md`
(one feature bullet, a "Commands at a glance" row and a layout note), `SKILL.md` (one
paragraph), `docs/COMMANDS.md` (dispatcher entry, layout paragraph and the closing note on
the `tests/` package and the `__file__`-relative modules), `docs/README.ko.md` (one sentence
and one table row) and `docs/WORKFLOWS.md` (the `tests/test_cli_e2e.py` path) were updated;
`docs/ARCHITECTURE.md` is unchanged because it describes the lifecycle, not the file layout.
The manifest was regenerated for 232 files.

Verification specific to this change: the 15-stage demo was run by hand into a fresh
external directory, and the 27-stage research-journey route through `python persona_cli.py
run synthetic_walkthrough.py ...` from a different current directory; both wrote
`COMPLETE.json`. A local link checker resolved every relative Markdown link and heading
anchor in the root and `docs/` Markdown files (548 links in 57 files), and all
text files are UTF-8 without BOM and LF-only.

Not claimed: this is a layout change plus a discovery aid. It adds no scientific behaviour,
does not re-verify source authenticity, browser QA or remote CI (the GitHub Actions history
for the merged commit is the remote record), and a dispatcher listing is not an approval of
any script's inputs. Local passes under Python 3.15 (the full suite) and 3.13 (the dispatcher
module only) do not establish the 3.10 and 3.12 CI results.

## 2026-11-10 Onboarding defect report (0.73-onboarding-defect-report)

Added `prepare_local_manifest.py --report-defects`: shared whole-selection preflight,
unchanged parser outcomes, invalid-UTF-8 offsets, BOM/near-miss/invisible-character
findings, splitlines break counts, preamble counts and bounded heading/finding rows.
The report is read-only, caps output at 8 MiB, and fails closed on read or hash errors.
Normal preparation and existing payload/fixture bindings are unchanged. Expanded
SKILL routing with actual offline proposal families, run markers and agent boundaries;
static contract tests check its size, frontmatter, paths and documented subcommands.

Validation: focused suite ran 26 tests successfully. Full discovery: `Ran 1003 tests in 298.973s`, `OK` on Python 3.12.14,
with no failures, errors or skips. The documented report command completed with ALL_SELECTED_FILES_WOULD_PARSE.
`python -m compileall -q .` covers 145 Python files; manifest verification and publication
audit cover 234 listed files and 235 text files respectively. All outputs and temporary
fixtures remain outside the repository. Existing executable guide blocks are unchanged.
No model/network calls, source conversion, scientific assessment, researcher identity
verification, real-person evaluation or user-persona publication readiness is claimed.

## 2026-11-10 Pasteable handoff text (0.74-handoff-text)

Added `prepare --format json|text` to the five offline handoff command families,
with complete ASCII-escaped JSON between fixed markers, the original instructions,
response contract, bound empty skeleton and repeated boundary/hash. A shared pure
renderer preserves every field; response-template remains JSON-only.

Verification: `python -m unittest discover -q` ran 1008 tests successfully;
`python -m compileall -q .`, `python verify_manifest.py` and
`python audit_publication.py` passed. Five new tests cover ten handoff versions,
lossless control/backslash/bidi/non-BMP round trips, no renderer file/provider/socket
access, default and explicit JSON bytes, source-root with both model tasks, and
unchanged proposal output limits without partial output. Default CLI JSON bytes were
also compared directly against the previous release for all ten versions. Documented
model preparation was spot-run; existing guide command blocks are unchanged.

This is a local derived view, not permission to transmit, proof of model execution,
prompt-injection resistance, scientific judgment, authentication, or scholarly
validation. No builder, import, persona payload, fixture hash, walkthrough stage,
adoption rule or review decision changes. Exclusive output files are outside this change.

## 2026-11-10 UTF-8 CLI output (0.75-utf8-cli-output)

Converted the final JSON result write in ten scripts from `print()` to
`sys.stdout.buffer.write(...encode('utf-8'))`: audit_design_chain,
audit_design_lineage, compare_releases, corpus_files, curate_local,
extraction_adapter, observation_input, operator_review, research_workflow and
revise_local. Each retains its existing JSON escaping, indentation and one final LF.
The only runtime changes are `import sys` and that final emission in each script;
builders, validators, argparse usage and error handling are unchanged.

Windows result stdout intentionally changes from CRLF and the configured console
encoding, often an ANSI code page, to LF and UTF-8 without a BOM. Existing UTF-8/LF
POSIX result bytes are preserved. Help and stderr remain argparse text streams.
This does not prevent a shell from re-encoding native stdout: default PowerShell 5
redirection is still unsuitable for the UTF-8-first input route. Shell redirection
can still overwrite files or leave empty output after failure. No shared output
helper, new `--output`, `--version`, packaging or license decision is included.

Before the change, a successful synthetic observation input containing Greek,
Korean and the micro sign failed at `print()` with `UnicodeEncodeError` under
`PYTHONIOENCODING=ascii`, leaving empty stdout. Five new tests now cover:

- Fourteen real successful modes across all ten CLIs, using an ASCII text stdout
  wrapper with explicit CRLF translation to exercise the Windows text-mode hazard
  on every host. Raw output must match the original JSON formatting plus one LF,
  decode as UTF-8, contain no BOM/CR, and preserve input files.
- The same modes under a UTF-8/LF wrapper, including existing JSON escaping and
  the exclusive revision directory's final `READY.json` marker.
- Invalid-input exit 1 with empty stdout, no traceback and no revision directory.
- Six real subprocess successes under `PYTHONIOENCODING=ascii`: all five unescaped
  JSON writers plus the revision-template subcommand. Fictional Greek/Korean/micro
  content survives both source-quote intake and result parsing.
- A structural inventory of the ten converted entry points, each with one binary
  stdout write and no remaining `print()` in `main()`.

Verification on Python 3.12.14: the new suite passed 5 tests in 0.359 seconds;
the affected-module/dispatcher/skill focused suite passed 105 tests in 5.340 seconds.
Full discovery: `Ran 1013 tests in 339.848s`, `OK`, with no failures, errors or skips.
Separate comparisons against the preceding release found byte-identical UTF-8/LF
successful outputs in all 14 modes, and identical exit code, empty stdout and stderr
on the same invalid inputs. All 59 existing Markdown files retain their executable
`sh` blocks; example bytes and synthetic walkthrough command arrays are unchanged.
The documented mock extraction command and 15-stage synthetic walkthrough also
completed manually under ASCII console encoding, with `COMPLETE.json` and all
answer reviews deferred. Relative link destinations in changed guides resolve.

`python -m compileall -q .` and Python 3.10 grammar checks pass for 148 Python files.
The final regenerated manifest lists 237 files for this release and date;
`python verify_manifest.py` and `python audit_publication.py` pass, with 238 text
files including the manifest. Every published file is UTF-8 without BOM and LF-only.
Local checks and the emulated CRLF wrapper do not establish native Windows or
remote CI results; the exact-commit GitHub Actions matrix remains the remote record.
Only fictional fixtures were used. No persona payload or binding, model/network
call, real researcher data, scientific judgment, source authentication or human
review behavior was added or changed.

## 2026-11-10 Exclusive CLI output (0.76-exclusive-cli-output)

Added `exclusive_output.py` and optional `--output NEW_FILE` on the 40 existing
stdout-result CLIs, plus human-validation check/status. The 76 output-capable leaf
commands include the pre-existing human-validation template writer, whose required
flag, file bytes and original receipt remain. The template reuses the shared writer.
`revise_local apply`, directory writers, validators, dispatcher, synthetic walkthrough,
fixtures, package bindings and existing stdout bytes are unchanged. No --version,
packaging, tag or license decision is included.

The helper checks the destination before inputs are read, rechecks before binary
exclusive creation, refuses existing paths, dangling/symlink components, repository
paths and missing parents, and never deletes partial output. Saved files have a
16 MiB ceiling, retain tighter command limits, and produce only a bounded 64 KiB
ASCII-safe receipt with path, bytes, raw hash, optional strict-JSON payload hash and
negative claims. Text/HTML have a raw hash; receipt paths can be private. Trusted,
stable ancestors are required: this is not a race-proof directory sandbox or a
Windows junction/reparse security boundary. macOS is not in the CI matrix.

Verification on Python 3.12.14:
- Final full discovery: `Ran 1029 tests in 316.185s`, `OK`, no failures/errors/skips.
- Final focused output, UTF-8, human-validation, dispatcher, manifest preparation,
  structural report, local curation and skill contract checks: 86 tests / 4.743s / OK.
- New helper/CLI tests cover exact existing bytes for converted result modes, parser
  coverage and actual helper bindings, every documented usage line, ASCII console,
  raw/logical hashes, text/HTML, direct research-journey HTML, saved input-card
  prepare/inspect, refusal before input reads, existing/dangling/ancestor paths,
  final-create collision, short write, write/close errors and retained partial files.
- New guide commands were also executed manually under ASCII console encoding;
  both saved receipts/hashes verified and repeating each refused the existing path.
- All 144 pre-existing Markdown sh blocks remain byte-identical; bundled examples,
  validators and synthetic walkthrough remain unchanged.
- Python 3.10 grammar parsing, compileall, whitespace checks, publication manifest
  (240 entries) and limited audit (241 files) pass after final documentation updates.

The initial full run (1025 tests / 330.609s) had 3 failures and 2 errors. Four
preparation/structure failures shared a helper import collision with the existing
`prepare_local_manifest.preflight`; the output helper now uses a distinct alias and
all selected modules have a binding regression test. The other failure was the
existing 8192-byte skill limit; the obsolete writer-boundary paragraph was replaced
rather than relaxing the limit (8168 bytes). A new direct-journey test initially
omitted its fixture's declared review and correctly failed binding; the test now
supplies that exact review. These failed intermediate checks are not final passes.

Only fictional/synthetic data was exercised. Hashes and mechanical checks do not
establish source authenticity, rights, scientific validity, researcher fidelity,
human approval or permission to share. No model/network call or canonical update
occurred. Local success does not claim exact-head Ubuntu/Windows CI success; that
must be verified separately before merge.

## 2026-11-10 Version-label display (0.77-version-labels)

Added `python persona_cli.py --version`: lazily read the adjacent manifest's
release/date labels and display the running Python major/minor/micro version.
The read is bounded to 1 MiB from a regular non-symlink file; strict UTF-8 JSON
rejects BOMs, duplicate keys, non-finite numbers and excessive nesting. Release
labels are bounded printable strings displayed with ASCII JSON escaping; dates
must be valid exact YYYY-MM-DD calendar dates. Invalid metadata exits 1 without
stdout or untrusted diagnostic text. Stable trusted repository files are assumed,
not a race-proof filesystem sandbox.

The output explicitly says this is not an integrity check or signature, that the
manifest excludes itself from its hashes and that labels are unauthenticated.
No file hashes are checked. It directs readers to `python verify_manifest.py` for
separate inventory/hash consistency checks, not publisher authentication.
`list` still imports no repository module; help/list do not read the manifest;
`run SCRIPT --version` is forwarded unchanged. No packaging, tag or license
decision was made. Existing result stdout paths and all 145 prior Markdown sh
blocks remain unchanged. English/Korean documentation and the agent skill were
updated within the existing 8192-byte skill limit (8183 bytes).

Verification on Python 3.12.14:
- Full discovery: `Ran 1036 tests in 327.414s`, `OK`, no failures/errors/skips.
- Focused dispatcher/version, skill contract and exclusive-output checks:
  35 tests / 3.096s / OK. After strengthening help assertions and tightening skill
  wording, dispatcher/version and skill checks: 19 tests / 2.264s / OK. Final
  35-test focused rerun after documentation and manifest updates: 3.017s / OK.
- Synthetic edge cases cover malformed encodings/JSON, duplicate and nested keys,
  non-finite numbers, nesting limits, invalid types/dates, control/bidi/surrogate
  labels, inclusive byte/label bounds, growing-file bounded reads, missing files,
  directories, symlinks, unreadable paths, safe diagnostics, ASCII console output,
  CWD independence, lazy reads and unchanged run argument forwarding.
- The documented version command and an absolute-path invocation from an external
  empty directory were executed manually; labels and boundary text matched.
- Compileall and Python 3.10 grammar parsing pass for 151 Python files. Publication
  manifest (241 entries), limited audit (242 files), LF and whitespace checks pass.
- An initial focused invocation named nonexistent `tests.test_skill`; it failed
  import, then the corrected `tests.test_skill_contract` invocation passed.

Only fictional/synthetic inputs were exercised. No model/network call or canonical
update occurred. Passing mechanical checks does not establish source authenticity,
rights, scientific validity, researcher fidelity or human approval. Local success
is not an exact-commit Ubuntu/Windows CI result; verify those jobs before merge.


## 2026-11-10 Multi-topic teaching walkthrough (0.78-teaching-walkthrough)

- Added six ASCII-only invented Markdown sources across three topics, with one
  research/review pair per topic and publication labels spanning 2019-2023; each
  opens with SYNTHETIC TEACHING FIXTURE. Six synthetic operator cards bind the full
  prepared manifest chain. Existing fixtures and runtime modules are unchanged.
- Added docs/TUTORIAL_OWN_FILES.md: 15 literal CLI commands using exclusive
  `--output`, plus three marked JSON edits tested in order. The guide reaches
  source intake, topic/evidence review, explicit hypothesis authoring and selection,
  and a pinned JSON/HTML journey. Answer/link/design/argument forms remain empty,
  context decisions deferred and approval explicitly false. README/Korean entry,
  quickstart, workflow index, architecture and agent guidance link the route.
- `python -m unittest discover -q`: 1042 synthetic tests passed on Python 3.12.14
  in 324.677 seconds, with no failures, errors or skips. An earlier full run found
  SKILL.md exceeded its existing 8192-byte bound; its guidance was shortened and
  the full suite rerun successfully. No size limit was relaxed.
- `python -m unittest tests.test_tutorial_own_files tests.test_skill_contract -q`:
  9 tests passed, including the six new tutorial tests. The pipeline executes once
  per class in an external directory with spaces. Tests check exact card replay,
  three topics, research/review labels, declared disagreement, missing-work status,
  required pattern selection, stale-card/holdout rejection and fixture preservation.
  A separate exact-guide rehearsal passed all 15 commands and three JSON edits.
- `python -m compileall -q .`: passed; all 152 Python files parse with Python 3.10
  grammar. Changed guides retain every pre-existing sh block byte-for-byte.
  UTF-8 without BOM and LF-only checks passed for the publication inventory.
- `python verify_manifest.py`: passed, 256 exact entries.
  `python audit_publication.py`: passed, 257 text files including the manifest.
  Manifest release/date are 0.78-teaching-walkthrough / 2026-11-10.
- These checks establish synthetic mechanical behavior, not semantic support,
  source authenticity, rights, independent human review, model behavior or real
  researcher fidelity. CONTESTED groups declared exact-string stances only;
  same-year chronology cannot order decisions. No schema or license change.
  Browser visual/keyboard/print QA and remote CI for this release are not claimed.

## 2026-11-13 Detached split declaration (0.79-split-declaration)

Added a detached census/split declaration with template, freeze, check and status.
The package payload and existing intake paths are unchanged. Structural checks cover
exact fields, census uniqueness/coverage, disjoint splits, author labels, direct
relations, declared training-to-withheld relation leakage and sorted logical hashes.
Policy counts do not reject duplicate/notice training records. Reports expose only
counts/hashes and conflicts already in a package, not withheld lists.

- New focused suite: 23 tests passed, including the exact guide commands and private
  output preflight, no-overwrite, symlink, shared byte budget and exit-code boundaries.
- Independent review found a strict-JSON diagnostic privacy leak; parser details are
  now redacted. Duplicate private keys, malformed UTF-8 and malformed JSON are covered.
- Final full discovery: 1065 tests passed in 286.868 seconds, with no failures,
  errors or skips. Independent re-review found no remaining blockers.
- Manifest verification: 260 entries; publication audit: 261 text files, passed.
  All 154 Python files compile and parse under Python 3.10 grammar. SKILL.md is
  8188 bytes. Protected existing shell blocks are unchanged.
- After recording these results, the manifest was regenerated and manifest/audit,
  focused tests and compilation were rechecked. Remote CI is tracked by exact commit.
- No real scholar/source corpus, provider calls, source acquisition, canonical updates,
  semantic validation, proven freeze timing or unseen-holdout claim. Intake gating and
  review_package integration remain later work. Existing protected guide shell blocks
  and existing synthetic fixtures are unchanged.

- Initial PR CI passed both Linux jobs, but Windows found a guide-replay test
  quoting defect: POSIX shlex consumed native path backslashes. The replay now
  tokenizes the documented command before substituting native output paths.
  Application behavior and documented commands are unchanged.

## 2026-11-13 Optional split review summary (0.80-split-review)

Added `review_package --split` using the existing detached status/text renderer.
Default rendering remains unchanged. Split-enabled input shares an 8 MiB budget
across declaration/package/human records, rejects symlink components and redacts
strict-JSON errors. Output has a 16 MiB bound and existing exclusive preflight.
Mismatches are report-only, malformed records fail closed. No payload, source
acquisition, intake gate, CURRENT label or actual unseen-holdout claim is introduced.
The summary spans the package, not only its displayed topic; existing package
quotes remain potentially private and are not sanitized by this option.

Independent review found that an explicit JSON null declaration could bypass the
optional renderer sentinel. CLI declarations now receive immediate frozen-schema
validation; regression confirms exit 1 with no stdout or output file. Independent
re-review passed 19 review tests and 23 split tests, including the new guide command.
Initial full discovery found one stale CLI usage line in COMMANDS.md; it was updated
to include --split. Final full discovery passed 1076 tests in 285.895 seconds,
no failures/errors/skips. Manifest has 261 entries; audit passed 262 text files.
All 155 Python files compile and parse under Python 3.10 grammar; existing guide
shell blocks are unchanged. After recording results, manifest/audit and 42 focused
review/split tests were rechecked. No remote CI outcome is claimed in this record.

## 2026-11-13 Detached pre-holdout candidate findings (0.81-candidate-challenge)

- Added `candidate_challenge.py template/check/status` for roadmap lifecycle step 11.
  Exact detached schema, neutral NOT_EXAMINED templates, caller-supplied finding kinds,
  label-distinct-only challengers and declared holdout noninspection. No disposition,
  split binding, payload change, extra validation axis or candidate approval is derived.
- Current records resolve rule IDs within scope; stale records retain positional IDs
  without reinterpretation. Duplicate finding/record IDs and contradictory NO_FINDING
  declarations are rejected. Reports omit finding prose/labels, but JSON stale diagnostics
  can contain unresolved private IDs/topics; outputs are not sanitization.
- Optional repeatable `review_package --challenge-record` uses one 8 MiB reader for the
  package and all challenge/human/split inputs; bounded 16 MiB results and exclusive
  output. Existing default, evidence-details and human-validation CLI bytes match the
  previous release in independent comparisons. No model or network calls are introduced.
- Final local full suite: **Ran 1097 tests in 286.930s — OK**. Focused candidate/split/
  dispatcher suite: **41 tests — OK**. Independent review found no blocking issue.
  New guide commands execute exactly as written using synthetic fixtures and paths with
  spaces. Manifest verifies 265 files; limited publication audit passes 266 files.
  All 157 Python files compile and parse with Python 3.10 grammar. SKILL.md is 8140 bytes.
- These checks establish mechanical record/binding/output behavior only, not scholarly
  validity, authenticated independence, unseen holdout, chronological ordering, or
  approval of any actual candidate. Remote CI is recorded separately for exact commits.

## 2026-11-14 Controlled reopening declarations (0.82-reopening-record)

- Added roadmap #79's first increment: `release_record.py template reopening/check/status`.
  Detached strict records capture supplied trigger, exact prior bindings, affected prior
  paper/rule IDs, incoming IDs and required revalidation axes. Existing comparison code
  supplies read-only candidate changes; undeclared changes prompt review without approval.
- Prior IDs never resolve against candidate positions. Human records are checked even
  without reopening records; duplicate/invalid inputs are rejected. Supplied audit hashes
  remain explicitly unverified references. No release decision, payload rewrite, fifth
  validation axis, actual source notice verification or canonical change is introduced.
- Synthetic reopened fixture is exactly rebuilt from the declared fictional limitation
  correction. Executable guide tests include paths with spaces and exclusive outputs.
- Final local full suite: **Ran 1120 tests in 288.596s — OK**. Focused reopening/candidate/
  dispatcher suite: **53 tests — OK**. Independent review identified a no-record human
  input validation gap; it was fixed and regression tested. Final review found no blocker.
- Manifest 270 files verifies; limited publication audit passes 271 files. All 159 Python
  files compile and parse with Python 3.10 grammar; SKILL.md is 8089 bytes. Existing guide
  shell blocks and review_package code remain unchanged. No actual researcher data or
  external model/API calls were used. Remote CI is tracked separately for exact commits.
- Mechanical consistency is not scientific validation, authentic correction/retraction,
  preserved archive proof, candidate revalidation or approval. IDs/bindings may be private;
  omission of notice prose and operator labels is not sanitization or rights clearance.

## 2026-11-14 Supplied release decision records (0.83-release-decision)

- Added roadmap #79's second limited increment: `release_record.py template decision`,
  schema-dispatched check, distinct status field and optional `review_package --release-decision`.
  Supplied NOT_RELEASED/RELEASED_FOR_CONSULTATION/WITHDRAWN labels are retained, never derived
  or executed. No approval, access change, publication, new validation axis or payload update.
- Exact package bindings and logical human-record references are checked. Current/stale/
  missing human evidence is explicit; predictive/runtime references must be null and remain
  NO_RECORD_TYPE. Missing evidence prompts review without making a release gate. Supplied
  thresholds, dates, rationale and identities are not scientifically evaluated/authenticated.
- Final local full suite: **Ran 1140 tests in 308.616s — OK**. Focused decision/reopening/
  candidate/split/dispatcher suite: **84 tests — OK**. Independent review caught a top-level
  status contradiction in decision-only reports; separate reopening/supplied-decision states
  now have regression tests. Final review found no blocker; new 20 tests passed independently.
- Actual default/evidence-details/human-validation/challenge CLI stdout and stderr matched
  the previous release byte-for-byte in independent comparisons. New guide executes exactly
  as written, with spaces in output paths. Existing guide shell blocks remain unchanged.
- Manifest verifies 273 files; limited publication audit passes 274. All 160 Python files
  compile and parse with Python 3.10 grammar; SKILL.md is 8148 bytes. Synthetic fixtures only,
  no model/API/network calls. Remote CI is tracked separately for the exact commit.
- Mechanical checks do not authenticate operator decisions or prove candidate quality.
  Omitted prose/labels are not sanitization; hashes, package bindings and dates can be private.

## 2026-11-14 Machine-readable command discovery (0.84-command-list)

- Added roadmap #87's first increment, `persona_cli.py list --json`: deterministic
  schema/scripts/boundary discovery from the existing AST entry-point scanner. Names and
  first docstring sentences are not an invocation/schema contract, integrity check or
  approval. No discovered script is imported/executed and no subprocess/model/network call
  or output-file write is introduced. Describe/catalog capture remains a separate increment.
- Source reads enforce the existing 1 MiB bound while reading; JSON output has a 1 MiB
  bound, ASCII-escaped UTF-8/LF bytes and redacted failures without partial JSON. Plain list
  formatting and run forwarding are unchanged; no --output flag is added to the dispatcher.
- Final local full suite: **Ran 1153 tests in 289.738s — OK**. Focused JSON-list/dispatcher:
  **22 tests — OK**. Independent review found no blocker and verified round11 plain list,
  run persona and run release_record exit-code/stdout/stderr byte equivalence.
- Executable guide and 13 new tests cover discovery shape, deterministic escaping, empty
  lists, bounds, failure redaction, source nonexecution, external cwd, symlink exclusion,
  no repository imports/subprocess and no writes. Existing guide shell blocks are preserved.
- Manifest verifies 275 files; limited publication audit passes 276. All 161 Python files
  compile and parse with Python 3.10 grammar; SKILL.md is 8180 bytes. No actual researcher
  records or external API calls. Remote CI is recorded separately for exact commits.

## 2026-11-14 Selected trusted command descriptions (0.85-command-description)

- Added roadmap #87's next increment: `persona_cli.py describe SCRIPT --json` captures
  actual root/subcommand argparse help for one explicitly selected trusted source. Exact
  filename allowlist and selected-source publication hash matching precede capture. Scripts
  without argparse, including verification/audit checks, are described statically, not run.
- Lazy subprocess capture uses shell=False, fixed UTF-8/color/width/bytecode environment,
  10-second per-help timeout, 1 MiB per-capture and aggregate JSON bounds. Dynamic subcommands
  come from unambiguous actual root usage. No full-catalog flag, persistent server, workflow
  execution or artifact-schema inference. Source inventory is not a signature or sandbox.
- A preliminary static-only approach was replaced before publication with actual bounded
  help capture, matching the roadmap. Independent review found numeric overflow in local
  manifest parsing; finite-float validation and valid-inventory regression cases now reject
  1e999/-1e999/NaN/Infinity. Final independent review found no blocker.
- Final local full suite: **Ran 1173 tests in 292.518s — OK**. Focused description/list/
  dispatcher suite: **42 tests — OK**. Actual usage lines for all 50 allowlisted scripts
  match COMMANDS.md, including dynamically declared subcommands. New guide executes exactly
  as written; old guide shell blocks remain unchanged. Plain list/run behavior is preserved.
- Manifest verifies 277 files; limited publication audit passes 278. All 162 Python files
  compile and parse with Python 3.10 grammar; SKILL.md is 8177 bytes. No actual researcher
  data or external model/API calls. Remote CI is tracked separately for exact commits.
- Help describes invocation shape, not data validity, permission, output safety, scientific
  truth or approval. Trusted script imports/parser setup execute before help exits; the
  selected source hash does not authenticate imported dependencies or interpreter state.

## 2026-11-14 Bounded trusted command catalog (0.86-command-catalog)

- Added roadmap #87 aggregate `persona_cli.py describe --all --json`, reusing the explicit
  trust allowlist/source matching and actual help capture. COMPLETE_CATALOG means every
  description was obtained, not workflow validation or approval. PARTIAL_CATALOG preserves
  redacted failures, omitted output and unattempted rows instead of claiming completeness.
- Shared best-effort 120-second deadline and 1 MiB JSON cap, 16 KiB status reserve, at most
  128 selected scripts. Remaining time limits each child query. Timeout cleanup has a bounded
  2-second grace; direct child/reader cleanup is regression tested. Filesystem/serialization
  and descendant-held pipes are not a hard real-time sandbox. No MCP or new trust rules.
- Final local full suite: **Ran 1189 tests in 300.405s — OK**. Focused catalog/description/
  list/dispatcher suite: **58 tests — OK**. Independent review found no blocking issue and
  verified round13 plain/JSON list, selected describe and run exit/stdout/stderr equivalence.
- New 16 tests cover partial/error states, shared deadline, cumulative output exhaustion,
  redaction, selection exclusivity, direct child cleanup and actual full-catalog guide/usage
  conformance. Existing guide shell blocks are unchanged; new guide executes as written.
- Manifest verifies 279 files; limited publication audit passes 280. All 163 Python files
  compile and parse with Python 3.10 grammar; SKILL.md is 8179 bytes. No actual researcher
  records or external model/API calls. Remote CI is recorded separately for exact commits.
- Catalog exit 0 alone does not prove completeness. Help is invocation shape only, never
  artifact schema, permission, scientific validity or approval; canonical payload unchanged.

## 2026-11-14 Shared bounded JSON reads (0.87-bounded-json)

- First bounded increment of roadmap #81: strict_json.load defaults to 8 MiB with
  limit + 1 reads; explicit Python limits and runtime-patchable default are supported.
  Original-byte and binary-stream helpers handle short reads, preserve encoding bytes,
  and never close caller streams. ASCII-escaped bounded basename diagnostics omit directories.
- Human-validation-dependent readers retain their combined budget and existing error
  message but now enforce it before reading entire files. Projection file and stdin
  inputs are bounded before original-byte hashing. This deliberately newly rejects
  oversized inputs in previously unbounded shared-loader callers; no CLI override.
- Final local full suite: **Ran 1196 tests in 306.120s — OK**. Focused strict JSON,
  human validation, dispatcher and package review: **52 tests — OK**. Independent review
  found no blockers, independently ran all 17 strict JSON tests and verified old/new
  CRLF and UTF-16 original-byte projection exit/stdout/stderr byte equivalence.
- Seven new tests plus the expanded CLI sweep cover exact limit/+1, patched defaults,
  invalid limits, short reads, stream ownership, aggregate budgets, escaped diagnostics,
  original encodings/hash and manifest rejection. Existing guide shell blocks unchanged.
- Manifest verifies 279 files; limited publication audit passes 280. All 163 Python files
  compile and parse with Python 3.10 grammar. No real researcher data or external API calls.
  Remote CI results are recorded separately for exact commits.
- Private bounded-loader consolidation and raw-source sizing remain future increments.
  No total corpus/output, decoded-memory or I/O-time bound is claimed. Payload, four axes,
  acquisition gate and approval behavior are unchanged.


## 2026-11-14 Shared private bounded readers (`0.88-shared-private-readers`)

Eleven existing JSON wrappers now reuse `strict_json.read_bounded` without introducing
new path policy, module, command or input ceiling. Thin wrappers preserve exact size
errors, patchable module constants, citation audit's original-byte combined budget and
research journey's UTF-8-first rejection of UTF-16/BOM. Shared short-read accumulation
now applies to these wrappers too. Candidate/split readers and raw source policy are
not part of this change. Canonical payloads, four validation axes and approval rules
are unchanged; fixtures remain synthetic.

- Full local suite: 1200 tests, 331.361 seconds, OK.
- Focused strict JSON: 21 tests, OK; independent focused suite: 71 tests, OK.
- Independent old/new differential: 132 result/error/type comparisons identical,
  including exact and over-budget, UTF-16/BOM, strict malformed JSON, symlink/missing paths.
- Manifest: 279 selected files; audit: 280 files; compile and Python 3.10 grammar: 163.
- Local results do not establish remote CI; exact-head PR and main runs are checked
  separately before completion. No browser, model, external data or scientific validation.
- Final focused invocation initially named the nonexistent `tests.test_checkout_smoke`;
  this was a selection error, not a product test failure. Corrected invocation below
  uses strict JSON, manifest, dispatcher and model-handoff modules.
