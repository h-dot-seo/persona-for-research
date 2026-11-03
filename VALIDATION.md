# Validation record

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
