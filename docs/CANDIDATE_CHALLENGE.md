# Detached pre-holdout candidate challenge records

This lifecycle step 11 record stores supplied **finding kinds**, not the human-validation
AGREE/PARTIAL/DISAGREE judgments. It is not a fifth validation axis. It is distinct from
observation stance, citation role, pattern `challenge_refs`, reasoning `challenges`,
publication `challenges`, and Sensei's `challenge_intake.py` workflow.

`candidate_challenge.py` binds a separate immutable record to persona and knowledge
hashes. It does not alter payload fields, source acquisition or a release gate. A blank
template uses NOT_EXAMINED, never a prefilled positive NO_FINDING conclusion. Fill all
blank declarations, select findings yourself, and set status RECORDED before checking.
The shipped record and package below are fictional synthetic fixtures.

```sh
python candidate_challenge.py template examples/trajectory-conditions-package.json --output OUTPUT/candidate-blank.json
python candidate_challenge.py check examples/manual-candidate-challenge.json examples/trajectory-conditions-package.json --text
python candidate_challenge.py status examples/trajectory-conditions-package.json --challenge-record examples/manual-candidate-challenge.json --text
python review_package.py examples/trajectory-conditions-package.json --question "Synthetic scope question?" --topic "trajectory" --challenge-record examples/manual-candidate-challenge.json --output OUTPUT/candidate-review.txt
```

## Record contract

Schema `persona.candidate-challenge.v1` requires exact fields: schema_version, author_id,
version, build_id, persona_payload_sha256, knowledge_papers_sha256, challengers,
challenged_at, method, holdout_inspected, scope_topics, findings, limitations,
independence_declaration and status. Unknown fields are rejected. No split binding or
operator disposition is accepted in v1; later responses belong in a separate record,
not edits to a previously referenced hash.

Each of 1–32 challengers supplies challenger_id and role. At least one label must differ
from every author/operator/reviewer label recorded in the package. This only establishes
LABEL_DISTINCT_ONLY, not independence, expertise, blinding or authenticated identity.
`challenged_at` is an ISO calendar date. `holdout_inspected` must be exactly false; this
is a declaration, not verified unseen holdout or pre-evaluation chronology.

Each of 1–4096 findings supplies a unique finding_id, item_id (rule ID or null for the
whole package), kind, nonempty rationale and source_locator. Kinds are NOT_EXAMINED,
NO_FINDING, OVERSTATED_STATEMENT, MISSING_COUNTEREVIDENCE, ATTRIBUTION_DOUBT,
SCOPE_EXCEEDED, PROVENANCE_GAP and OTHER. Multiple findings per rule are allowed;
NO_FINDING cannot coexist with another kind on the same item_id. IDs are at most 128
characters, ordinary prose at most 2000. Current rule-level rows must fall within the
declared nonempty scope_topics; package-level rows do not resolve to a rule.

## Status and privacy

Check derives CURRENT_PACKAGE or STALE_PACKAGE. Stale positional rule IDs are never
re-resolved; absent IDs/topics are reported as unresolved. Do not repair a stale record's
hashes: make a new record for the new candidate. Status is NOT_PERFORMED with no records,
RECORDED_CURRENT with at least one current record, otherwise STALE_PACKAGE. Mixed records
keep individual hashes, counts and bindings. Duplicate logical record hashes are rejected.

Outputs omit finding prose, source locators and challenger labels. JSON checks still
include package bindings and unresolved IDs/topics, which may be private. The compact
review prints only hashes, binding status and kind counts. Neither is sanitization or
rights clearance. Never publish actual private records with these synthetic examples.
Counts are not scores, verdicts or approval; no open/closed disposition is derived.

CLI inputs share an 8 MiB budget and strict JSON parsing. Outputs are limited to 16 MiB.
`--challenge-record` is repeatable in status and review; all review inputs, including
human-validation records and an optional private split, share the same budget. Without
this option the review's existing output is unchanged. Outputs use exclusive creation,
refuse existing paths/dangling links, and never overwrite a package. No LLM, network,
scientific validation, canonical update or persona payload modification occurs.
