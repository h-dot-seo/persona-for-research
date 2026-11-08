# Review publication relationships beside methods and chronology

A review can summarize an earlier paper rather than provide a second independent
observation. Different source hashes and publication dates do not resolve that
question. `publication_context.py` records explicit, evidence-linked publication
relationships so an operator can examine this context alongside a timeline or
method-pattern transfer. It does not discover relationships or reconstruct the
researcher's private reasoning.

The artifact is separate from canonical paper metadata and from observation-level
reasoning links. All relationships remain **operator interpretations requiring
review**, with exact basis references and uncertainty. No relationship approves a
method, establishes independence, changes a source stance or rewrites an answer.

## Create an empty form

Use an existing authorized, author-matched training package, including a separate
reviewed observation candidate if appropriate. Save generated artifacts outside
this public repository:

```sh
python publication_context.py ../package.json --template --operator-id local-operator > ../publication-relations.json
```

The template binds the persona and knowledge-paper hashes and contains
`relations: []`. It does not select sources, fill links or infer missing edges.
For each relationship you wish to examine, supply:

```json
{
  "relation_id": "synthetic-review-context",
  "from_paper_id": "synthetic-1",
  "to_paper_id": "synthetic-0",
  "relation_type": "review_summary_of",
  "rationale": "A synthetic operator hypothesis that this review summarizes the earlier comparison, rather than providing an independent test.",
  "basis_refs": [
    {"paper_id": "synthetic-1", "observation_index": 0, "dimension": null}
  ],
  "uncertainty": "The stored quote alone does not verify this relationship."
}
```

This invented example demonstrates the structure, not a scientifically verified
relationship. Use exact references from your package's evidence catalog. Source
records may contain incomplete or mistaken interpretations; matching a stored
quote does not establish the relationship asserted in the rationale.

Each entry requires its ID, both paper IDs, type, nonempty bounded rationale,
nonempty `basis_refs` and an explicit `uncertainty` value. Uncertainty may be null,
but the missing field remains a visible review prompt. Every basis reference must
belong to one of the two linked papers. Directed relations require at least one
basis from the `from_paper_id`; evidence from both papers is not required, but a
one-sided basis is flagged. References resolve to observations or supported
reasoning components, retaining their own quotes, labels, conditions, limitations,
source checks and imported origin where present.

## Relationship directions

- `review_summary_of`: A is declared to summarize B. A must carry the existing
  source-kind label `review`. This is a supplied publication label, not evidence
  that A is a peer-review report, an authenticated reviewer judgment or replication.
- `method_extension_of`: A is declared to extend a method in B. This does not
  establish individual ownership, influence, new data or empirical independence.
- `reanalysis_of`: A is declared to reanalyze material from B. Data dependence
  still needs examination; the tool does not inspect datasets or calculate it.
- `shares_material_with`: A and B are declared to share material. This is symmetric,
  displayed with a two-way connector. It neither proves identical datasets nor
  authorizes deduplication or exclusion.
- `version_of`: A is declared to be a version of B. Neither document automatically
  supersedes the other, and the tool does not check version history or retractions.
- `challenges`: A is declared to challenge B. This publication-level interpretation
  is separate from each observation's stance and a pattern's support/challenge role.

Distinct relationship types can coexist for the same pair, without the tool
resolving their consistency. Duplicate IDs and duplicate type/endpoint pairs
reject. Reversing a symmetric pair is still a duplicate; reversing a directional
pair is a separate explicit declaration. Self-links and unknown papers reject.

## Inspect the context

```sh
python publication_context.py ../package.json ../publication-relations.json --format text
```

The report preserves all declared relationships and their evidence, including
uncertainty, missing quotes and any original imported-observation/component origin.
Source and quote verification labels are validated as supported recorded labels,
not freshly rechecked. Review prompts flag:

- No relationship basis from both papers, or missing uncertainty/quotes.
- Identical source hashes, without deleting either record.
- Directional links whose from-paper publication year precedes the target, or
  shares its year. These are review prompts, not proof of an error. Publication
  years do not date ideas or decisions; within-year order remains unresolved.
- Review summaries and material/version relationships that need dependency review.
  Method/claim relationships likewise do not establish independent data.

Missing declarations mean **not supplied**. They establish neither dependence nor
independence. There are no inferred reverse edges, transitive paths, dependency
clusters, effective evidence counts, confidence scores or automatic approvals.

## Add context to a publication timeline

```sh
python publication_timeline.py ../package.json --topic "model design" --publication-relations ../publication-relations.json --format text
```

Topic matching and chronology remain unchanged. JSON includes a separate context
review and a scope view distinguishing:

- Relationships with both endpoints in the topic-selected papers.
- Relationships touching one selected paper and another supplied paper. The latter
  paper is **not** silently added to the topic timeline.
- Relationship IDs entirely outside the selected timeline.
- Selected papers without any declared relationship, whose independence is unknown.

Text includes the complete supplied context, including outside-topic basis records,
with that scope made explicit. An absent topic stays empty even if relationships
exist. A `timeline_input_sha256` binds the original package, requested topic and
relationship form. Editing a rationale or uncertainty changes this full identity.

## Add context to method-pattern transfer

```sh
python pattern_transfer_review.py ../package.json ../patterns.json ../context.json ../links.json ../design.json ../answer.json --pattern-id comparison --publication-relations ../publication-relations.json --format text
```

The same option works with a provenance-bearing reviewed model-pattern envelope.
The report preserves the original/reviewed model reasons, rejected candidates,
review provenance, evidence-use gaps and existing context exclusions. Relationship
context does not change support counts, citation roles, source stance, missing
counterarguments or applicability decisions.

The transfer view also compares each contextual publication and basis reference
with the target context's reference year. Later publications and unresolved
same-year order receive explicit prompts, including when a relation reaches a
paper outside the selected pattern. This does not prove when a source was
available or when the declared relationship was known. Assertion time is explicitly
`NOT_SUPPLIED`; an operator's explanation may be retrospective. These flags do not
silently remove evidence or approve historical applicability.

Matching is by exact publication ID. A relationship basis may use a different
observation/component than the selected pattern's references; it is displayed as
**separately declared relationship evidence**, never automatically a new answer
citation or supporting pattern observation. Relationships to other supplied papers
are likewise context, not additional selected evidence. The full relationship-form
hash participates in the transfer input hash, so context edits require a new report.

Omitting `--publication-relations` preserves the earlier JSON and text outputs.
Explicitly supplying an empty form instead adds a bound `NO_DECLARED_PUBLICATION_RELATIONS`
section and its distinct report identity. Empty declarations do not establish that
no relationship exists.

## Safety and verification limits

The complete package is validated before selecting sources, including unselected
paper authorization, source/rule consistency, all publication years and supported
recorded checks. Relations are limited to 128 entries, each with 1–32 basis
references. Identifiers are at most 128 characters; rationale and non-null
uncertainty at most 2,000. New relation CLI inputs are bounded to 8 MiB and strict
JSON rejects duplicate keys and nonfinite numbers. Text escapes control characters
while preserving ordinary Unicode. The tools do not modify input files; invalid
input produces no partial stdout result.

No source acquisition, provider call, source reread, real-author evaluation or
canonical update occurs. Data can still contain private quotes and operator notes;
projection is not anonymization or rights clearance. Hashes establish artifact
consistency, not authentic authorship, genuine review or semantic truth.

```sh
python -m unittest tests.test_publication_context -v
```

Tests use invented publications only. They cover all relation types, scopes,
chronology warnings, source-hash and quote gaps, strict references, historical
check labels, imported provenance, versioned legacy-output snapshots, no mutation,
and actual CLI inspection/timeline/transfer paths. Human scholarly review remains
necessary.
