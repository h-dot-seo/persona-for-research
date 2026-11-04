# Supply method and publication context before answer proposals

The default answer handoff contains explicitly selected evidence, question, topic
and reference year. The optional v3 mode also includes an **inspected operator-supplied
method-pattern, target-context judgments and publication records** before a separately
produced answer is imported. It is a preparation aid, not approved reasoning or
proof that a model used that context.

This differs from [application proposals](APPLICATION_PROPOSALS.md), which propose
how one pattern relates to existing design steps. V3 still proposes only answer
claims. It creates no new method selection, design step, research execution or
researcher speech.

## Select explicit existing artifacts

Supply a valid original pattern form or reviewed pattern-proposal envelope, an
applicability form, a publication-relationship form (empty relations are allowed),
and one existing manual/adopted pattern ID. A cached inspection report is not an
input form. Rejected or unresolved pattern candidates cannot be selected as adopted
patterns, but their complete recorded history remains visible.

```sh
python answer_proposals.py template package.json --question "New synthetic question" --topic "model design" --reference-year 2020 --operator-id synthetic-operator --include-citation-explanations --patterns patterns.json --context context.json --publication-relations publication-relations.json --pattern-id comparison > answer-scope.json
```

Replace the sample values with your own explicit artifact values. Question, topic
and reference year must match the context form exactly, including case. All four
context options are required together and require explanation mode. The scope
still starts with **empty `evidence_refs`**. Fill 1–64 unique exact references yourself;
no pattern, context judgment or relationship selects a citation automatically.

The Python API is `template(..., include_citation_explanations=True,
research_context={"patterns": ..., "context": ..., "publication_relations": ...,
"pattern_id": ...})`. These are raw JSON artifact objects, not file paths or cached
reports. New direct v3 inputs reject non-JSON Python values before normalization.
Omitting context or passing `research_context=None` keeps v1/v2 unchanged.

V3 scope stores detached original context artifacts, not their local file paths.
Every later consumer freshly validates them against the canonical package and
rebuilds the context inspection. Full context and imported history bind the scope,
handoff, bundle and eventual full answer-envelope hash. Editing even a rejected
pattern's review note makes the old handoff stale. No automatic refresh occurs.

## Prepare, import and review with the existing commands

```sh
python answer_proposals.py prepare package.json answer-scope.json > answer-handoff.json
python answer_proposals.py response-template package.json answer-scope.json answer-handoff.json > empty-answer-response.json
# Produce a separate response and review it before importing:
python answer_proposals.py import package.json answer-scope.json answer-handoff.json answer-response.json declared-provenance.json > answer-candidates.json
python answer_proposals.py review-template package.json answer-candidates.json --reviewer-id synthetic-reviewer > deferred-adoption.json
# Explicitly record each accept/reject/defer and the complete reviewed claim:
python answer_proposals.py review package.json answer-candidates.json adoption.json --format text
python answer_proposals.py export package.json answer-candidates.json adoption.json > draft.json
python answer_draft.py package.json draft.json --review-template --reviewer-id synthetic-reviewer > final-answer-review.json
```

The response contract is the v2 citation-explanation contract: no new context-use
claims or automatic decisions are admitted. Every original and adopted citation
requires an explanation slot, which may explicitly be null. Candidate review and
final answer review remain separate and start deferred. Use the existing
[argument workflow](ARGUMENT_PROPOSALS.md) to create a new map bound to this draft;
old answer reviews/maps cannot be silently reused after input changes.

No provider is called. The handoff can include private quotes, annotations and
unselected/rejected history. Preparing it does not authorize transmitting those
materials to a model provider or another recipient. Check rights and sharing
permission separately. Provider/run/reviewer labels remain unauthenticated.

## Context does not grant citation permission

Only exact references in `scope.evidence_refs` are citable. A context passage,
related publication, sibling component, parent observation or rejected-pattern
reference remains uncitable unless that exact reference was explicitly selected.
This applies to both original proposals and accepted/revised claims. Even a literal
quote visible in context is rejected as a citation when outside the explicit scope.

The context report preserves:

- The selected pattern and full pattern inspection, including original, rewritten,
  rejected and unselected history. Inclusion is not relevance or endorsement.
- Every topic-matched applicability assessment, including consider/exclude/defer,
  missing comparisons, uncertainty and counterevidence.
- Selected-pattern routes matched only to the enclosing observation. A component
  does not inherit semantic approval. Exclude does not ban citation for criticism.
- Topic-matched publication chronology and the full declared relationship inventory.
- Three separately named, reference-year-scoped publication projections: papers in
  explicit answer citations, papers in the selected pattern, and topic-timeline
  papers. Each preserves outside-selection relationships. A paper-level projection
  never grants permission to cite every observation/component from that paper.

Before/same/after labels describe publication years only. They do not establish
historical availability, event ordering within a year, career stages, influence,
independence, author ownership, private beliefs or researcher endorsement. Review
articles can describe other people's work. Recorded source/quote checks are not
fresh source verification. Supplying context does not show it actually shaped a
model response or that a method applies.

## Keep recorded preparation context separate from current review

The answer's proposal-review packet labels its context
`RECORDED_IMPORT_CONTEXT_NOT_AUTOMATIC_CURRENT_REVIEW_CONTEXT`. Full text, JSON,
citation audits, argument-map reports and journey histories retain it as recorded
preparation/import context, not verified historical model input.

A later research journey may use different current pattern, applicability,
publication-relationship or selected-pattern inputs. Legitimate reevaluation is not
blocked or automatically rebound. The journey compares only the four logical JSON
artifact hashes and reports `SAME_RECORDED_ARTIFACTS` or
`DIFFERENT_SUPPLIED_ARTIFACTS`, with changed field names. Both contexts remain
separate. The text and passive HTML view display this comparison explicitly.

A hash difference can reflect a note, provenance label, array order or changed
judgment. It does not establish a contradiction, supersession or invalid answer.
Equality does not prove model use or approval. Raw file-byte differences are the
separate concern of pinned input cards. Other artifacts, such as method-application
reviews, retain their existing binding requirements and need explicit review when
their own inputs change.

## Try the contextual synthetic walkthrough

```sh
python synthetic_walkthrough.py ../persona-contextual-demo --candidate-source offline-import --research-journey --import-answers --contextual-answers
```

This opt-in 34-stage route prepares the invented pattern, applicability and
publication forms **before** the v3 answer handoff, then reuses those exact forms
in the later journey. Preparation is reordered, not duplicated. With mock extraction
it has 32 stages. Add the existing source/method/HTML/argument options for the full
53-stage route:

```sh
python synthetic_walkthrough.py ../persona-contextual-full --candidate-source offline-import --research-journey --recheck-sources --review-method-use --import-method-use --html-review --import-answers --import-arguments --contextual-answers
```

Read `answer-handoff.json` for the supplied preparation context and
`answer-proposals.txt` for the complete original/reviewed/rejected answer history.
The example includes explicit citation-explanation slots and an invented rewrite;
missing explanations stay visible. `research-journey.txt` compares the recorded and
current context artifacts. Matching artifacts establish neither model use nor
method applicability. The later parent-observation record visible in pattern
context remains outside the explicit answer citation scope.

`--contextual-answers` requires both `--import-answers` and `--research-journey`;
it does not silently enable them. No external candidate, context, review or provider
inputs are accepted by this demonstration. Its fixed fixture adoption is not a
reusable automatic-review policy. Every final answer decision remains deferred.
Failures preserve diagnostics without a completion marker or automatic retry.
Without the new flag, earlier command order, outputs and stage counts are unchanged.
Static HTML generation does not verify browser layout, keyboard use or printing.

## Compatibility, bounds and verification

V1/v2 scope/handoff/bundle/review/envelope outputs remain unchanged. Frozen synthetic
v1 and v2 artifacts captured before these edits verify complete logical replay and
rendered text hashes, including existing argument wrappers. V3 uses distinct schema
names; mixed-version/downgraded artifacts fail validation. Context output never
adds active citation uses or transfers premise evidence to an uncited conclusion.

Combined inputs are bounded to 8 MiB, the handoff to 2 MiB logical UTF-8 JSON, and
JSON/text reports to 16 MiB. Repeated full histories can reach these limits even
when individual files are small. Failure is explicit; histories, exclusions and
counterevidence are never silently truncated. The default synthetic walkthrough
continues using its original v1 path and counts. The explicitly contextual mode
uses only the fixed invented fixtures described above.

All examples and tests are invented. No real scholar-fidelity or semantic validation,
provider execution, external transmission or automatic scientific approval is
performed. Actual browser layout, keyboard and print QA remains blocked/unverified;
passive HTML checks are structural and snapshot checks only.
