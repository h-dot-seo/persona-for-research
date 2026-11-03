# Disclose evidence scope to the consultation reader

The full review packet is an audit trail. This additional reader view makes its
scope visible without repeating full quote blocks and technical reports. It adds
no answer text, model inference, source search or scientific assessment.

```
python evidence_scope.py package.json links.json proposal.json draft.json --reference-year 2020 --format text
python evidence_scope.py package.json links.json proposal.json draft.json --reference-year 2020 --review review.json --format text
```

The inputs and optional review are checked exactly as for `review_journey.py`.
The report identifies the scholarly simulation, declared operators/reviewer,
question and packet binding; all identity declarations are unauthenticated. Every
answer claim remains visible with its claim type, recorded decision, stored-quote
comparison status and supplied uncertainty. Proposed design actions retain their
uncertainty and missing fields. The view is **not an approved-answer selection**:
rejected and deferred claims are intentionally included in its coverage counts.

## Repeated references do not multiply evidence

All supplied paper IDs are grouped by their **supplied source hash**. The report
separates paper-ID counts, source-hash groups, observation references and exact
observation/component references. Reusing one source in several claims or steps
does not increase the distinct source group count. Multiple IDs with the same hash
stay visible; their conflicting year or research/review labels are flagged, not
resolved or silently deduplicated. Different hashes do not establish independence.
No count is a score for scientific support, literature completeness or fidelity.

An active reference is cited by an answer claim or by a link actually used in a
design step. An unused link alone does not make its endpoints active. A paper with
the same hash as an active paper is still unused if its own ID is not referenced.
Rows may show both active uses and unreferenced-link uses of the same record. The
unused-link-reference list contains only rows without active uses. Observation and
component references stay distinct; selecting one does not imply selecting all
components. All supplied paper years must be integers from 1 to 9999.

## Origin and uncertainty

Each selected record distinguishes a recorded mock-candidate origin from other
curated records whose origin is not authenticated. A mock marker does not prove
an AI call or real human review. Mock candidate/review hashes and proposed versus
recorded claim labels stay visible. Current execution always reports no LLM or
provider invocation, no source reread and no researcher-fidelity evaluation.

Source and selected-record checks are recorded statuses, not new checks. Research
and review labels do not prove an idea belongs to the named scholar; reviews may
summarize others. Missing uncertainty, missing/deferred/revise/reject review,
missing design fields and publication-year warnings remain mechanical prompts,
not an exhaustive scientific critique. No supplied challenge citation does not
mean counterevidence does not exist.

The synthetic experiment represents two paper IDs by one source hash and verifies
that paper count remains two while active hash groups become one. Both original
research and review labels remain present with a mixed-label warning. Another
case adds an unused paper ID sharing a used hash: it stays unused. Mock provenance,
rejected claims, unreferenced challenges, invalid years and the actual CLI are
covered by:

```
python -m unittest test_evidence_scope -v
```

Use the full review packet for detailed quotations and review notes. Real sources,
rights, identities, semantic support and scholarly fidelity require authorized
local material and independent review; none was evaluated by these synthetic tests.
