# Compare an operator's tentative method pattern across publications

Exact method/condition grouping already describes repeated identical strings.
It cannot establish that differently worded observations reflect a recurring way
of reasoning. The new worksheet lets an operator explicitly propose such a pattern
and expose its source uses, rival explanation, potential falsifier and uncertainty.
It performs **no automatic pattern discovery or semantic grouping**.

Start with a bound package, such as the output of the manual local journey:

```sh
python pattern_hypotheses.py ../manual-result.json --template --operator-id synthetic-operator > ../patterns.json
```

The template has an empty `hypotheses` list. Use exact references from the review
workspace's reference catalog and write each hypothesis yourself. Each entry has:

```json
{
  "pattern_id": "comparison-first",
  "operator_hypothesis": "A tentative comparison-first method pattern in these selected synthetic records.",
  "scope_note": "Only the cited synthetic records; no claim about a real author's distinctive thought.",
  "support_refs": [
    {"paper_id": "synthetic-0", "observation_index": 0, "dimension": null}
  ],
  "challenge_refs": [
    {"paper_id": "synthetic-1", "observation_index": 0, "dimension": null}
  ],
  "alternative_explanation": "This could be a generic convention rather than a distinctive researcher method.",
  "falsification_check": null,
  "uncertainty": "One selected supporting paper cannot establish a recurring pattern."
}
```

This illustrative hypothesis intentionally has only one supporting paper and no
falsification criterion. Add the entry to the existing template without changing
its bindings, then review it:

```sh
python pattern_hypotheses.py ../manual-result.json ../patterns.json --format text
```

The output flags the single-paper support and missing falsifier. It does not find
or generate another supporting paper to complete the pattern. An empty template
reports NO_PATTERN_HYPOTHESES, not a modeled researcher's reasoning.

## What a person can compare

Each pattern remains labelled `operator_interpretation`. Selected observations and
components are ordered by supplied publication year, with original research/review
kind, source hash/locator, method, condition, limitation, topic, quotes, recorded
checks, original claim labels and any recorded candidate-review provenance. Differing method
wording stays separate rather than being rewritten into a shared author claim.

The operator's support/challenge roles are shown separately from source stance.
A source marked `challenge` can be explicitly selected as supporting a different
higher-level hypothesis, but the source stance is not changed and the tool does not
validate that reasoning. The same exact reference can appear in both roles; both
are retained and a review prompt highlights the overlap. Duplicate references
within one role reject.

A component and its enclosing observation remain separate references. Multiple
components from one paper count as one supporting paper ID. Two paper IDs with the
same supplied source hash are grouped and flagged. Different hashes, kinds and
years do not prove independent publications or independent confirmation. Counts
are descriptive inventory, not a pattern score, replication test or confidence.
Publication chronology does not establish when the researcher acquired an idea,
changed their mind or influenced another work. Later reviews do not supersede
original research automatically, and coauthored sources do not establish individual
ownership of a claimed method.

## Expose alternatives and missing evidence

A pattern requires at least one explicit supporting reference. Its `scope_note`
should state what body of work and conditions the hypothesis is intended to cover.
`alternative_explanation`, `falsification_check` and `uncertainty` may remain null,
but each missing field stays visible. A generic shared disciplinary practice,
selection bias or dependent reports may be alternatives an operator chooses to
consider; the tool does not invent or assess them.

No challenge references produces a visible gap, not a conclusion that opposing
evidence is absent. Unreferenced observations are listed separately and may contain
important contrary evidence. This inventory is observation-level only: selecting
one component marks its observation as referenced and does not mean every component
was considered. The full package is not claimed to be representative or exhaustive.

Unknown endpoints, duplicate pattern IDs, invalid publication years and stale
package bindings reject. Holdout and author boundaries remain in force. Existing
answer/design links are not generated or updated from the hypothesis. To apply a
possible method to a new question, first use the separate applicability worksheet
and explicitly review conditions, counterarguments and uncertainty. A declared
pattern is not an approved recommendation or an authenticated review decision.

All input/output may contain private operator text, source quotations and
identifiers. Nothing rereads source files or sends data externally. Keep reports
private; a stored quote match is neither semantic support nor rights clearance.
No real scholar material, LLM, external API or scientific validation is used in
the synthetic tests.

```sh
python -m unittest test_pattern_hypotheses -v
```

When a proposed pattern informs a new question, use
[pattern-to-context trace review](PATTERN_TRANSFER_REVIEW.md) to compare its exact
evidence routes with an existing applicability form and answer/design artifacts.
It preserves missing counterarguments and conditions without migrating any fields.
