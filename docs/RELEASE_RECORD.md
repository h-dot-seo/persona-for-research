# Controlled reopening declarations

Updates already have `revise_local`, observation revision, comparison and old-artifact
impact tools. This guide adds the missing **supplied trigger, prior-package impact and
revalidation plan** record. It does not replace those tools or implement a release decision.
`release_record.py template reopening/check/status` is the first increment of roadmap #79.

The record is detached and immutable once referenced by hash. Its five bindings identify
the exact prior package. Always supply that package, not a rebuilt candidate in its place.
Stale records are rejected, not repaired or reinterpreted. A matching prior file does not
prove it was archived or preserved elsewhere. The tool never overwrites a prior release.

## Synthetic rehearsal

All examples below are fictional. The candidate changes only a declared synthetic
limitation and release labels, rebuilt through the existing builder.

```sh
python release_record.py template reopening examples/trajectory-conditions-package.json --output OUTPUT/blank-reopening.json
python release_record.py check examples/manual-reopening-record.json examples/trajectory-conditions-package.json examples/trajectory-conditions-reopened-package.json --human-validation examples/manual-human-validation.json --text
python release_record.py status examples/trajectory-conditions-package.json --reopening examples/manual-reopening-record.json --output OUTPUT/reopening-status.json
```

The blank template has no selected trigger, operation or completion status. Fill every
blank declaration yourself, then set status RECORDED. Nothing is inferred from a date,
notice text or a changed paper. The unedited template fails checking.

## Strict record fields

Schema `persona.reopening-record.v1` uses `schema_version`, author_id, version, build_id,
persona_payload_sha256, knowledge_papers_sha256, operator_id, trigger,
affected_paper_ids, incoming_paper_ids, affected_rule_ids, operation,
revalidation_axes_required, revision_audit_sha256 and status. Unknown fields are rejected.
Trigger has exactly kind, declared_source_text and declared_at (ISO calendar date).
Kinds: new_paper, correction, retraction, provenance_error, counterexample, scope_change.
Dates and notices are supplied assertions, not clock-checked or externally authenticated.

Affected paper and rule IDs must exist in the prior package. Incoming IDs must be absent
from it and are allowed only with new_paper, which requires at least one incoming ID.
Correction, retraction and counterexample require at least one affected paper. Scope and
provenance declarations may have empty ID lists. Lists reject duplicates and have at most
4096 entries; IDs have at most 128 characters and notice text at most 2000.

Operation is exactly knowledge_ingestion or canonical_policy_revision. It is declared,
not checked against a separate policy layer: the builder derives rules from observations,
so knowledge ingestion can change rules too. Neither operation executes a change.
`revision_audit_sha256` is null or a lowercase SHA256 declared reference. It is not a
claim that a revision-audit file was loaded, checked, or preserved.

## Read-only impact prompts

An optional candidate must have the same scholarly identity. The existing `compare`
function supplies added/removed/modified paper IDs. The report maps changed or removed
papers only to **prior** rules. It does not map candidate rule IDs back to old positions.
Undeclared changes produce UNDECLARED_PAPER_CHANGE and
RULES_ON_CHANGED_PAPERS_NOT_DECLARED prompts, not approval or failure (exit 0).
Declared incoming IDs absent from the candidate's added IDs are also listed.
Rule-payload change without paper change has a separate structural prompt; package/source
consistency checks still reject malformed packages before comparison. Reordering is not
semantic equivalence, a change of mind or evidence that a previous answer remains valid.

`revalidation_axes_required` is a declared subset of evidence_integrity, predictive,
human, runtime. Evidence/source consistency is recomputed as RECOMPUTED_VALID, not
scientific validation. Optional `--human-validation` records are checked with the existing
human axis, yielding CURRENT, STALE or NOT_SUPPLIED against the prior package only.
Predictive/runtime report NO_RECORD_TYPE in this increment. Split and candidate-challenge
records are lifecycle stages, not additional validation axes. These observations do not
satisfy a candidate's revalidation plan or make a release decision.

## Boundaries

Check/status omit the operator label and supplied notice prose; IDs, dates and bindings
may still be private. Results are not sanitization or rights clearance. `--text` retains
ASCII JSON with escaped controls. No canonical validation field is read as an approval,
no payload is modified, and no model, API, source lookup or paid service is called.

All CLI input files share an 8 MiB strict-JSON budget; output is bounded to 16 MiB.
`--output` uses exclusive creation outside the repository and rejects existing paths,
dangling symlinks and missing parents. Invalid supplied records are rejected even when
no reopening record accompanies them. Status rejects duplicate reopening hashes and
requires each record to match the exact prior package. Release decisions, candidate
approval and review_package integration are deliberately deferred to a separate increment.
