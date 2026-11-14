# Release change index

A concise command and behavior index from 0.69 onward, newest first. Detailed
verification, failures and limitations remain in [validation history](docs/VALIDATION_HISTORY.md).
Earlier releases are retained there, not reconstructed here. These are repository
release labels, not Git tags, signatures, rights clearance or persona approval.
No artifact-schema inventory is inferred by this index.

## 0.93-change-index — 2026-11-14

Release change index and static consistency checks added; README entry points link this index. No runtime command, schema or behavior change.

[Validation record](docs/VALIDATION_HISTORY.md#2026-11-14-release-change-index-093-change-index).

## 0.92-manifest-regeneration — 2026-11-14

`regenerate_manifest.py` creates an external candidate with explicit add/remove, raw-byte hashes, CR rejection and preserved declarations. It never replaces the original manifest or grants publication approval.

[Validation record](docs/VALIDATION_HISTORY.md#2026-11-14-explicit-public-inventory-regeneration-092-manifest-regeneration).

## 0.91-main-pr-ci — 2026-11-14

CI retires one historical development-branch push trigger; main pushes and all PRs retain the same four read-only test jobs. No branch deletion or tag trigger.

[Validation record](docs/VALIDATION_HISTORY.md#2026-11-14-main-and-pr-ci-091-main-pr-ci).

## 0.90-selected-publication-root — 2026-11-14

`verify_manifest.py [ROOT]` and `audit_publication.py [ROOT]` inspect another tree using trusted code. Defaults are unchanged; invalid ROOT exits 2 and help performs no inspection.

[Validation record](docs/VALIDATION_HISTORY.md#2026-11-14-trusted-checks-on-selected-root-090-selected-publication-root).

## 0.89-source-file-bound — 2026-11-14

Local source preparation/segment loading reject individual source files over 8 MiB. Existing total budgets remain; no new corpus-total default or output cap.

[Validation record](docs/VALIDATION_HISTORY.md#2026-11-14-per-file-local-source-bound-089-source-file-bound).

## 0.88-shared-private-readers — 2026-11-14

Eleven private JSON readers reuse `strict_json.read_bounded`; size errors, module limits, combined citation budgets and journey encoding rules are preserved. No new command or ceiling.

[Validation record](docs/VALIDATION_HISTORY.md#2026-11-14-shared-private-bounded-readers-088-shared-private-readers).

## 0.87-bounded-json — 2026-11-14

Shared JSON readers and projection stdin enforce an 8 MiB default before parsing; previously unbounded oversized inputs are now rejected. Combined budgets and original-byte hashes are preserved.

[Validation record](docs/VALIDATION_HISTORY.md#2026-11-14-shared-bounded-json-reads-087-bounded-json).

## 0.86-command-catalog — 2026-11-14

`persona_cli.py describe --all --json` adds an aggregate help catalog with shared budgets and explicit partial-failure states.

[Validation record](docs/VALIDATION_HISTORY.md#2026-11-14-bounded-trusted-command-catalog-086-command-catalog).

## 0.85-command-description — 2026-11-14

`persona_cli.py describe SCRIPT --json` captures bounded actual help from explicitly trusted sources; no workflow execution or schema inference.

[Validation record](docs/VALIDATION_HISTORY.md#2026-11-14-selected-trusted-command-descriptions-085-command-description).

## 0.84-command-list — 2026-11-14

`persona_cli.py list --json` adds bounded AST-based command discovery; no discovered script executes and plain list/run behavior is preserved.

[Validation record](docs/VALIDATION_HISTORY.md#2026-11-14-machine-readable-command-discovery-084-command-list).

## 0.83-release-decision — 2026-11-14

`release_record.py template decision` and `review_package.py --release-decision` record supplied release choices and human-record references without executing decisions.

[Validation record](docs/VALIDATION_HISTORY.md#2026-11-14-supplied-release-decision-records-083-release-decision).

## 0.82-reopening-record — 2026-11-14

`release_record.py template reopening/check/status` records supplied triggers and prior-package impact plans; candidate changes prompt review without approval.

[Validation record](docs/VALIDATION_HISTORY.md#2026-11-14-controlled-reopening-declarations-082-reopening-record).

## 0.81-candidate-challenge — 2026-11-13

`candidate_challenge.py template/check/status` and `review_package.py --challenge-record` add detached supplied findings, not disposition, scores or approval.

[Validation record](docs/VALIDATION_HISTORY.md#2026-11-13-detached-pre-holdout-candidate-findings-081-candidate-challenge).

## 0.80-split-review — 2026-11-13

`review_package.py --split` adds an optional read-only detached split summary; default rendering is unchanged, mismatches are report-only.

[Validation record](docs/VALIDATION_HISTORY.md#2026-11-13-optional-split-review-summary-080-split-review).

## 0.79-split-declaration — 2026-11-13

`split_declaration.py template/freeze/check/status` records detached declared splits without altering intake gates or proving unseen holdout.

[Validation record](docs/VALIDATION_HISTORY.md#2026-11-13-detached-split-declaration-079-split-declaration).

## 0.78-teaching-walkthrough — 2026-11-10

A synthetic multi-topic tutorial covers source intake and review with empty/deferred human forms. Existing runtime modules and fixtures are unchanged.

[Validation record](docs/VALIDATION_HISTORY.md#2026-11-10-multi-topic-teaching-walkthrough-078-teaching-walkthrough).

## 0.77-version-labels — 2026-11-10

`persona_cli.py --version` displays bounded manifest labels and Python version, explicitly not integrity verification or a signature.

[Validation record](docs/VALIDATION_HISTORY.md#2026-11-10-version-label-display-077-version-labels).

## 0.76-exclusive-cli-output — 2026-11-10

Result CLIs gain `--output NEW_FILE` for exclusive external files and hash receipts. Default stdout is preserved; failed writes may leave partial new files.

[Validation record](docs/VALIDATION_HISTORY.md#2026-11-10-exclusive-cli-output-076-exclusive-cli-output).

## 0.75-utf8-cli-output — 2026-11-10

Ten result CLIs emit UTF-8/LF bytes rather than console-dependent text; Windows JSON stdout changes from CRLF/console encoding. Help and stderr are unchanged.

[Validation record](docs/VALIDATION_HISTORY.md#2026-11-10-utf-8-cli-output-075-utf8-cli-output).

## 0.74-handoff-text — 2026-11-10

Offline handoff families add `prepare --format text`; default JSON is unchanged and response-template stays JSON-only. Rendering does not authorize transmission.

[Validation record](docs/VALIDATION_HISTORY.md#2026-11-10-pasteable-handoff-text-074-handoff-text).

## 0.73-onboarding-defect-report — 2026-11-10

`prepare_local_manifest.py --report-defects` adds bounded whole-selection diagnostics; normal preparation is unchanged. Agent task routing and static contract checks added.

[Validation record](docs/VALIDATION_HISTORY.md#2026-11-10-onboarding-defect-report-073-onboarding-defect-report).

## 0.72-test-package-and-dispatcher — 2026-11-08

`persona_cli.py list/run` adds a root-script dispatcher; tests move into the `tests/` package without changing direct CLI invocation.

[Validation record](docs/VALIDATION_HISTORY.md#2026-11-08-test-package-and-dispatcher-072-test-package-and-dispatcher).

## 0.71-documentation-restructure — 2026-11-08

README, workflow and validation documentation reorganized. No Python, fixture or command behavior change.

[Validation record](docs/VALIDATION_HISTORY.md#2026-11-08-documentation-restructure-071-documentation-restructure).

## 0.70-human-validation-records — 2026-11-08

`human_validation.py` adds detached package-bound rater records; human assertions remain separate from canonical payloads.

[Validation record](docs/VALIDATION_HISTORY.md#2026-11-08-human-validation-records-070-human-validation-records).

## 0.69-public-boundary-cleanup — 2026-11-08

Documentation boundary cleanup; CI also runs on main. No command or runtime change.

[Validation record](docs/VALIDATION_HISTORY.md#2026-11-08-public-boundary-cleanup-069-public-boundary-cleanup).
