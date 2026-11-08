# Review explicit relationships between different approaches

Exact method/condition groups cannot express a relationship between differently
worded or differently scoped observations. `reasoning_links.py` provides a separate
artifact for an operator's explicit interpretation of such relationships. It does
not find connections, judge their validity or attribute them to a researcher.

## Workflow

1. Inspect available sources with `topic_inventory.py` and `publication_timeline.py`.
   Keep the package and all actual source material outside this public repository.
2. Create an empty, hash-bound link template:

   ```sh
   python reasoning_links.py package.json --template --operator-id reviewer-reference
   ```

   Save stdout to a separate local JSON file. No links, references or rationale
   are inferred. The operator ID is a declared local audit reference, not proof
   that a human reviewed the evidence.
3. Explicitly fill `links` after inspecting both endpoint records. Each entry has:

   ```json
   {
     "link_id": "link-1",
     "relation": "qualifies",
     "from_ref": {"paper_id": "review-paper", "observation_index": 0, "dimension": "falsification_check"},
     "to_ref": {"paper_id": "research-paper", "observation_index": 0, "dimension": "alternative_explanation"},
     "rationale": "Record the operator's specific interpretation and its limits here.",
     "claim_type": "operator_interpretation"
   }
   ```

   IDs above illustrate the schema; they must be replaced with actual IDs in the
   bound package. `dimension: null` selects the observation itself. A named reasoning
   dimension must exist on that exact observation, with no fallback to another node.
4. Review the resulting artifact in JSON or text:

   ```sh
   python reasoning_links.py package.json links.json --format text
   python reasoning_links.py package.json links.json --format json
   ```

Neither command modifies the package, stores canonical links or promotes a relation.
Retain the original link artifact: its hash identifies it but is not a signature.
If the package changes or observations move, regenerate the template and re-review
references instead of merely replacing hashes to force acceptance.

## Meaning and evidence boundaries

- `supports`, `challenges` and `qualifies` read **from → to**. `contrasts` is a
  comparison, not a causal or chronological direction. No relation means “proves.”
- All relation rationales are `operator_interpretation`. Endpoint observations and
  components retain their separate claim types, quotes, locators and recorded checks.
  An explicit statement at an endpoint does not turn the edge into an author claim.
- Cross-topic and backward-publication-year links are allowed only as supplied
  interpretations. They establish neither transferability nor intellectual influence,
  career progression or change of mind.
- Contradictory relations and cycles remain visible. No transitive edges are added,
  conflicts resolved, coherence scored or missing content inferred.
- Identical source hashes are flagged without removing endpoints. Different hashes
  do not prove independent publications, replication or individual authorship.
- Source limitations, stances, publication kinds and component-specific locators
  remain attached to each endpoint. JSON preserves documented candidate-review provenance.
- Duplicate IDs, duplicate same-relation endpoint pairs, self-links, missing nodes,
  unsupported author-attributed edge claims and unknown fields are rejected. For
  contrast links, reversing endpoints is still the same duplicate comparison.
- Package authorization, training-only eligibility, source/rule consistency and
  exact bindings are checked. Original files and quote semantics are not rechecked.
  No provider, network transmission, credentials or model inference is involved.

Only documented endpoint fields are shown, not raw sections or arbitrary metadata.
The retained quotes, operator ID and rationale can still be sensitive or restricted;
this is not anonymization, permission to publish, or evidence of researcher fidelity.

## Synthetic end-to-end scenario

```sh
python -m unittest tests.test_reasoning_links -v
```

The test builds an earlier synthetic research observation containing an alternative
explanation and a later review with a different method, condition and topic plus a
falsification criterion. An explicitly simulated operator supplies a `qualifies`
link from the review criterion to the earlier alternative. Actual intake, empty
template and JSON/text review CLIs run. Source claims, operator interpretation and
counterevidence remain separate; originals are unchanged. No real researcher or
genuine human review is asserted.
