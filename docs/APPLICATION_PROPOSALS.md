# Offline proposals for applying a selected method pattern

The researcher-method review can now use a locally prepared AI/Codex handoff for a
concrete question: **how might this selected, evidence-bounded pattern be applied
or adapted to these existing design steps?** It never writes a new design or claims
what the researcher would say or choose. This module makes no model/API calls and
transmits nothing. Actual provider use remains outside this tool's execution scope.

## Run the full synthetic example

```sh
python synthetic_walkthrough.py ../persona-imported-method-demo --candidate-source offline-import --research-journey --recheck-sources --review-method-use --import-method-use
```

This runs **38 real CLI stages** with invented sources, canned responses and explicit
fixture decisions. Read `source-recheck.txt`, `application-proposals.txt`,
`method-applications.txt`, then `research-journey.txt`. The original application
rationale differs from the reviewed rationale; a rejected alternative remains in
the history. Pattern-proposal history and application-proposal history both survive.
All answer claims remain deferred, the application has a missing failure criterion,
and source matches do not establish semantic support or applicability.

The six additional stages prepare a handoff, prepare an empty response, import the
fixed response, create an all-deferred review, render the explicit review and export
a history-preserving envelope. The runner takes no external candidate/review input.
Its fixture acceptance is not a reusable auto-approval policy. Failure prevents
`COMPLETE.json`. Existing demo modes are unchanged. `--import-method-use` requires
`--review-method-use`, which requires `--research-journey`. With offline-import
extraction but no source recheck this mode runs 35 stages; the mock extraction path
has two fewer stages.

## Prepare a handoff, not a provider request

Start with the same validated package, pattern form or reviewed pattern envelope,
context form, links and design used by [method application](METHOD_APPLICATION.md):

```sh
python application_proposals.py prepare package.json patterns.json context.json links.json design.json --pattern-id selected-pattern > application-handoff.json
python application_proposals.py response-template package.json patterns.json context.json links.json design.json application-handoff.json --pattern-id selected-pattern > application-response.json
```

The handoff binds the complete package, selected pattern form/envelope, context,
links, design and pattern ID. It contains the selected pattern and exact evidence,
context decisions/counterevidence and the unchanged design/link review. It explicitly
treats every quotation, earlier model proposal and annotation as untrusted data.
**It may contain private quotes or annotations. Preparing it does not authorize
sending it to a provider.** Check source rights and transmission permission separately.
No current local-source recheck is claimed or embedded as an approval certificate.

The response template has an exact `handoff_sha256` and an empty `candidates` array.
An empty response is valid. Each candidate supplies exactly:

- `step_id`: an existing design step, never a new or renamed target.
- `proposed_role`: method, constraint, counterargument, or null.
- `application_rationale`, `target_condition_comparison`, `failure_condition`,
  `remaining_uncertainty`: explicit strings or null when unsupported.
- `required_checks`: proposed, unexecuted checks; empty is a visible gap.
- `evidence_refs`: unique exact selected-pattern references; empty is a gap.

No candidate `decision` is accepted. The model cannot select an application or
approve its own proposal. Several alternatives may target one step; the reviewer
must explicitly choose at most one. Original proposals are inspected with a local
deferred placeholder, clearly distinguished from a decision made by the model.
Missing fields are not completed from plan-level or source-level falsifiers.

## Import and review explicitly

Prepare a separate declared provenance JSON object with exactly `provider_id`,
`model_id`, `run_id`, `operator_id` and `execution_location` (local, remote or unknown).
These are bounded labels, not credentials or authenticated generation evidence.
Never include API keys, tokens, private identity data or unrelated content.

```sh
python application_proposals.py import package.json patterns.json context.json links.json design.json application-handoff.json application-response.json declared-provenance.json --pattern-id selected-pattern > application-candidates.json
python application_proposals.py review-template package.json patterns.json context.json links.json design.json application-candidates.json --pattern-id selected-pattern --reviewer-id local-reviewer > application-review.json
```

Every candidate defaults to `defer`. Explicitly edit each decision:

- Candidate `accept` requires a **complete** `reviewed_application` with all candidate
  fields plus application `decision` set to `consider` or `exclude`. Supply the
  reviewed rationale, target condition comparison, role, uncertainty and references
  explicitly. There is no fallback to the original proposal. The step ID cannot
  change; references must remain within the selected pattern's exact catalog.
- Candidate `reject` or `defer` must not carry a `reviewed_application`.
- Every candidate needs exactly one decision and a nonempty `review_note`.
- At most one candidate may be accepted per step. Resolve all alternatives and
  accept at least one candidate before exporting. All-rejected, empty and incomplete
  reviews can be inspected, but cannot be exported as application intent.

**Candidate decisions and application decisions are different.** Accepting a
candidate retains an explicit reviewed declaration. It does not approve the method.
A reviewed application can explicitly exclude this pattern-to-step relationship;
that does not remove the step. Rejecting a candidate does not exclude the method.
Unproposed steps, or steps with no accepted candidate, retain fresh blank deferred
rows. Rejected proposal references never become application evidence.

```sh
python application_proposals.py review package.json patterns.json context.json links.json design.json application-candidates.json application-review.json --pattern-id selected-pattern --format text
python application_proposals.py export package.json patterns.json context.json links.json design.json application-candidates.json application-review.json --pattern-id selected-pattern > reviewed-applications.json
python method_application.py package.json patterns.json context.json links.json design.json reviewed-applications.json --pattern-id selected-pattern --format text
```

Use `--method-applications reviewed-applications.json` in an existing
[research journey](RESEARCH_JOURNEY.md). The same input also composes with explicit
live source-selection/root arguments. Every consumer reconstructs the imported
bundle and reviewed projection from the original records. It does not trust a
cached report, accepted count, approval label or supplied materialized worksheet.
Invalid envelopes fail before source bytes are read.

## What remains visible and unverified

JSON and text preserve original and reviewed rationales, rejected alternatives,
review notes, provider/model/run declarations, candidate identities and artifact
hashes. Standalone proposal text includes original source evidence, context judgments
and counterevidence, pattern evidence-use reasons and actual target-step link uses.
Full method/journey reports retain the complete supplied pattern/context/design
reviews, including earlier imported pattern history.

The envelope's full hash is `form_sha256`; a separate `worksheet_content_sha256`
binds the materialized declared intent. Changing only a review note changes the
former even if the latter is unchanged. These are unsigned records: a consistently
reconstructed edited history is not detectable as falsified authorship. Hashes
establish consistency, not identity, source authenticity or genuine human review.
Re-review changed inputs; do not copy new hashes into old records to hide changes.

The existing design, active evidence, answer citations, answer review, publication
scope and argument support remain unchanged. The journey annotates only explicitly
reviewed application references, never original or rejected proposal references.
It does not execute proposed checks, score sufficiency, generate a final answer,
update the canonical persona or authenticate earlier model use. Its status still
requires human review. This supplies concise proposed justifications, never private
reasoning traces or simulated first-person researcher claims.

## Bounds

- 32 candidates, 128 existing design steps, at most one accepted candidate per step.
- Existing per-application limits: 32 references, 16 checks, 2,000 characters per
  explanatory field/check; 128 characters for identifiers.
- 2 MiB logical handoff JSON; 8 MiB per JSON file and combined API input; 16 MiB
  report/output, with additional upstream/journey aggregate limits.
- Strict finite JSON rejects duplicate object keys and excessive nesting. Exact
  schemas reject extra permissions, cached approval fields and forged endpoints.
- Inputs and outputs are detached. Errors produce no partial successful CLI output.

Large artifact collections may require an explicitly narrower review. No silent
truncation, automatic source selection, provider invocation or implicit step choice
is performed to fit the limits.

## Pasteable handoff view

For a separately authorized local or remote assistant, append `--format text` to
`prepare` (default JSON is unchanged). With the corresponding prepared inputs in
`OUTPUT`, an external directory:

```sh
python application_proposals.py prepare OUTPUT/package.json OUTPUT/patterns.json OUTPUT/context.json OUTPUT/links.json OUTPUT/design.json --pattern-id selected-pattern --format text
```

Keep the JSON handoff for import; `response-template` remains JSON-only. The text
is not permission to transmit and makes no model call. See the complete format and
size boundaries in [Model handoff](MODEL_HANDOFF.md#pasteable-local-handoff-view).
