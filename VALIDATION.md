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
