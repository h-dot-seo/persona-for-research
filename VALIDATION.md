# Validation record

## Current verification snapshot (2026-11-04, UTC)

Current local source release: v0.45 (live local source and stored-quote recheck).

- `python -m unittest discover -q`: 513 synthetic tests passed locally.
- `python -m compileall -q .`: passed.
- `python audit_publication.py`: passed, 157 text files scanned including the manifest.
- `python verify_manifest.py`: passed, exact allowlisted inventory and file hashes.
- Standalone `synthetic_walkthrough.py --candidate-source offline-import --research-journey --recheck-sources`:
  all 30 CLI stages completed. Two invented local sources and five stored records
  matched the fixed package hashes/sections. Historical labels remained unchanged,
  imported reasoning lineage replay matched, and answer review stayed deferred.
  Existing 15/17-stage and 25/27-stage modes passed their regression tests.

Most recent separately verified remote baseline: v0.44, commit
[`e733b57af4afaf8e0020dbacfdc2da5bc99cd61c`](https://github.com/h-dot-seo/persona-for-research/commit/e733b57af4afaf8e0020dbacfdc2da5bc99cd61c),
with 484 tests. This is a prior-commit record, not a claim of remote CI for v0.45.

- [GitHub Actions run 41774858526](https://github.com/h-dot-seo/persona-for-research/actions/runs/41774858526):
  all four jobs passed for that exact commit, Ubuntu/Windows and Python 3.10/3.12.

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

Fourth increment: CLI end-to-end scenarios and failure recovery added. Local tests: 9 passed. Remote CI status is recorded separately in the private development log.

Cloud methodology chronology increment: 18 standard-library tests passed locally,
including 9 new synthetic cases for research/review separation, duplicate-paper
counting, same-year disagreement, cross-year variation, challenge-only evidence,
exact-condition separation, quote provenance, stable chronological order and input
authorization. Publication scan and byte-manifest verification passed. No remote
CI run or real-scholar validity evaluation is claimed for this uncommitted increment.

Fifth increment: 12 local tests passed. New CLI paths, source boundaries, deterministic output and tamper/no-overwrite checks are covered. See private development log for remote matrix CI.

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
