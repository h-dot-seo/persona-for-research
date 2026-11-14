# Supplied release decisions, not tool approval

A **reopening** record declares a trigger, prior-package impact and revalidation plan.
A **decision** record separately stores a person's supplied release choice for one exact
package. Neither executes publication, changes access, approves the candidate, or writes
canonical validation fields. This is roadmap #79's second, deliberately limited increment.

```sh
python release_record.py template decision examples/trajectory-conditions-package.json --output OUTPUT/blank-decision.json
python release_record.py check examples/manual-release-decision.json examples/trajectory-conditions-package.json --human-validation examples/manual-human-validation.json --text
python release_record.py status examples/trajectory-conditions-package.json --release-decision examples/manual-release-decision.json --human-validation examples/manual-human-validation.json --output OUTPUT/decision-status.json
python review_package.py examples/trajectory-conditions-package.json --question "Synthetic scope question?" --topic "synthetic method conditions" --release-decision examples/manual-release-decision.json --human-validation examples/manual-human-validation.json --output OUTPUT/decision-review.txt
```

These fixtures are fictional. The template has decision/status null and no selected
human record. Fill declarations yourself; no favorable choice is prefilled. Set status
RECORDED only after filling every required field. The unedited template fails check.

## Exact declaration contract

Schema `persona.release-decision-record.v1` has schema_version, author_id, version,
build_id, persona_payload_sha256, knowledge_papers_sha256, axis_records,
declared_thresholds, decision, decided_by, decided_at, rationale and status. Unknown
fields are rejected. Bindings must match the exact supplied package; stale decisions
are not rebound. Candidate comparison is supported only for reopening records.

Decision is exactly NOT_RELEASED, RELEASED_FOR_CONSULTATION or WITHDRAWN. These are
**supplied labels**, never tool-derived statuses. Dates are ISO calendar dates, not clock
verified. Declared thresholds and rationale are nonempty text, not evaluated evidence of
sufficiency. IDs/labels are at most 128 characters; prose is at most 2000 characters.

axis_records has exactly human, predictive and runtime. Evidence integrity has no record
hash: package bindings and source/rule consistency are recomputed as RECOMPUTED_VALID,
not scientific validation. Predictive/runtime references must be null and report
NO_RECORD_TYPE in this increment. Split and candidate challenge are lifecycle stages,
not extra validation axes, and are not accepted as axis references.

The human reference is null or the lowercase **logical JSON payload SHA256** of one
existing human-validation record, not its file-byte hash. Supply that record with
`--human-validation`. At most one human record is accepted for a decision; an unreferenced,
substituted, duplicate, structurally invalid or foreign-identity record is rejected.
A matching hash is not authentication of the rater, date, source or scientific claim.
The existing human validator determines CURRENT or STALE against the decision package.
Without a supplied referenced record, the result is NOT_SUPPLIED, not an inferred pass.
A null human reference is NOT_DECLARED and its axis remains NOT_SUPPLIED.

## Missing evidence does not become a decision gate

Missing/stale human records and unsupported predictive/runtime records are listed in
axes_not_performed and produce DECISION_RECORDED_WITH_UNPERFORMED_AXES (exit 0).
The recorded decision is retained even if it says RELEASED_FOR_CONSULTATION. This is a
warning about the supplied declaration, not tool approval or permission to publish.
Only malformed bindings/records or a mismatched supplied hash are rejected (exit 1).
Because predictive/runtime record types are unavailable, current human evidence cannot
make all axes performed. The tool neither recommends thresholds nor derives a verdict.

With a decision, status reports DETACHED_RELEASE_RECORDS_REPORTED and separately
labels reopening_status and release_decision SUPPLIED_OPERATOR_DECLARATION. It places
supplied_release_decision separately from reopening records. Reopening
rows still say release_decision NOT_RECORDED. `review_package --release-decision` prints
an explicitly supplied-decision summary; without the flag existing output is unchanged.

## Privacy and output boundaries

Outputs omit decided_by, rationale, threshold prose and human assessment prose. Package
bindings, hashes and dates can still be private; output is not sanitization or rights
clearance. `--text` JSON escapes controls, and the compact review includes only checked
choices, hashes, dates, axis states and fixed boundary text.

All files in a decision check/status/review share one 8 MiB strict-JSON budget, including
package, optional human, challenge and split inputs. Outputs are bounded to 16 MiB and
`--output` creates a new file exclusively outside the repository. Existing files and
symlinks are not overwritten. No model/API, network, actual researcher data, automatic
release action, access change or canonical payload modification is involved.
