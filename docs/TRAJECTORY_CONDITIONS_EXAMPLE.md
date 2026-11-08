# Publication change versus changed conditions

This fully invented, offline worked case uses existing APIs and fixed operator decisions. It adds no runtime inference engine. It describes publication records, not researcher speech, private beliefs, personal practice, or an individual's change of mind. No real person, publication, source download, model call, or scientific experiment is involved.

## Read the conditions before reading a reversal

All observations use the exact method string `Method M` and one of two exact condition strings:

- A: `Condition A: separated synthetic signals`
- B: `Condition B: overlapping synthetic signals`

The compact corpus has five publication records and six observations:

1. `synthetic-2020-a`: research supporting M under A.
2. `synthetic-2022-b`: research challenging M under B. A-to-B differences are not an A-to-A reversal.
3. `synthetic-2023-review`: a review with two separate passages summarizing the early A support (observation 0) and B challenge (observation 1). Two explicitly declared `review_summary_of` relationships carry exact basis references from both endpoints. These are operator declarations, not verified citations or automatic semantic validation.
4. `synthetic-2024-a-challenge`: research challenging M under the recorded A string.
5. `synthetic-2024-a-support`: research supporting M under the same recorded A string, in the same publication year as the challenge.

The existing `methodology_trajectory` groups by case-folded topic plus **exact method and condition strings**. Two groups are not proof of semantic comparability. Even the same recorded A is not sufficient scientific equivalence: unrecorded design details, measurement, sampling, or implementation may differ. The fixture does not decide which result is scientifically right.

A has cross-year support/challenge variation and within-2024 disagreement. B is challenge-only. `cross_year_stance_variation` is an existential flag for support and challenge in different years, not a directed temporal reversal. Same-year paper-ID sorting is deterministic display order, not chronology. Publication dates do not date research decisions, and there is no latest-wins rule. Neither 2024 result erases the other or the earlier evidence.

The A group contains four distinct paper IDs; B contains two; the corpus contains five, since the review occurs in both groups. These are record counts, **not independent-evidence counts**. Different hashes or years do not prove independence. The review is a dependent summary, not independent corroboration. Undeclared relationships elsewhere do not establish independence either.

## Exact references, roles, and judgments

The v3 answer scope includes reason-bearing reviewed pattern proposals, applicability assessments, and publication relationships. It selects exactly observation 0 from each of the five papers for answer citation. The review's observation 1 remains visible as a relationship basis and excluded context-only assessment, but is **not** an authorized answer citation. Context cannot widen that exact selection, even when the paper ID is already selected. The empty-scope CLI exercise confirms that populated context alone grants no citations.

Every source observation has `claim_type=explicit_statement`. That describes the stored synthetic statement, not its truth or personal authorship. The review has `source_kind=review`; the other records have `source_kind=research`. All selected references have `dimension=null` and retain exact paper/observation identities.

Source stance, pattern role, and answer-citation role are different declarations. In particular, the 2024 supporting source has source stance `support` but pattern role `challenge`: it challenges a simple replacement narrative. It has answer-citation role `support` because it supports the accepted synthesis's description of unresolved disagreement, not universal effectiveness of M. The B challenge similarly supports the bounded description of the B record. Per-reference rationales and boundaries explain these uses; they are not source-author endorsements or automatically validated entailment.

The fixed response proposes three alternatives. Fixed synthetic operator decisions accept the bounded publication-record synthesis and reject claims of an individual's change of mind and independent review confirmation. Original rejected wording remains explicitly rejected proposal history, not an active answer claim. Shared references remain available to the accepted synthesis. Contrary evidence, record limits, context reasons, and original history stay visible in the rendered review and answer.

Acceptance here adopts wording only. It does not validate the science or approve a final answer. The separate final answer review remains all-deferred with `DECLARED_REVIEW_INCOMPLETE`.

## Five inspectable inputs

- `examples/trajectory-conditions-package.json`: five synthetic records and their bound persona payload. Source hashes are deterministic SHA-256 placeholders for `synthetic placeholder ` followed by the paper ID, not checked original-source digests. All source and quote checks remain `NOT_PERFORMED`.
- `examples/trajectory-conditions-scope.json`: v3 exact answer scope plus raw reviewed pattern/context/publication-relation artifacts.
- `examples/trajectory-conditions-response.json`: bounded synthesis and two rejected canned alternatives, bound to the prepared handoff.
- `examples/trajectory-conditions-provenance.json`: `synthetic-no-provider` and `synthetic-no-model`; no historical model execution is claimed.
- `examples/trajectory-conditions-adoption.json`: fixed accept/reject/reject decisions bound to the imported bundle.

All hashes and bindings are validated by the existing APIs. Package reconstruction from its stored synthetic records produces the same package, but does not authenticate any original source. The fixture author supplied all statements, reasons, and decisions. The tools preserve these distinctions; they do not infer or establish them.

## Complete external-directory CLI recipe

Set `REPO` to an absolute checkout path. The recipe below uses a POSIX shell, Python and this repository. The Python regression runs the same repository commands without requiring that shell. No provider credentials, source files, browser, or network are used. The first 13 CLI stages execute the answer workflow; the final four demonstrate empty-selection behavior and inspect publication timeline/context independently.

```sh
REPO=/absolute/path/to/persona-cloud
WORK=$(mktemp -d)
cd "$WORK"
for name in package scope response provenance adoption; do
  cp "$REPO/examples/trajectory-conditions-$name.json" "$name.json"
done
python "$REPO/answer_proposals.py" context package.json scope.json > preview.json
python "$REPO/answer_proposals.py" context package.json scope.json --format text > preview.text
python "$REPO/answer_proposals.py" prepare package.json scope.json > handoff.json
python "$REPO/answer_proposals.py" response-template package.json scope.json handoff.json > empty-response.json
python "$REPO/answer_proposals.py" import package.json scope.json handoff.json response.json provenance.json > bundle.json
python "$REPO/answer_proposals.py" review-template package.json bundle.json --reviewer-id synthetic-reviewer > deferred-adoption.json
python "$REPO/answer_proposals.py" review package.json bundle.json adoption.json > adoption-review.json
python "$REPO/answer_proposals.py" review package.json bundle.json adoption.json --format text > adoption-review.text
python "$REPO/answer_proposals.py" export package.json bundle.json adoption.json > draft.json
python "$REPO/answer_draft.py" package.json draft.json > answer.json
python "$REPO/answer_draft.py" package.json draft.json --format text > answer.text
python "$REPO/answer_draft.py" package.json draft.json --review-template --reviewer-id synthetic-final-reviewer > final-review.json
python "$REPO/answer_draft.py" package.json draft.json --review final-review.json > final-result.json
python - <<'PY'
import json
from pathlib import Path
scope = json.loads(Path('scope.json').read_text(encoding='utf-8'))
for key in ('patterns', 'context', 'publication_relations'):
    Path(key + '.json').write_text(json.dumps(scope['research_context'][key]), encoding='utf-8')
PY
python "$REPO/answer_proposals.py" template package.json \
  --question 'What differs across these publication records, and what remains conditional or unresolved?' \
  --topic 'synthetic method conditions' --reference-year 2024 --operator-id synthetic-operator \
  --include-citation-explanations --patterns patterns.json --context context.json \
  --publication-relations publication_relations.json --pattern-id trajectory-conditions > empty-scope.json
python "$REPO/answer_proposals.py" context package.json empty-scope.json > empty-preview.json
python "$REPO/publication_timeline.py" package.json --topic 'synthetic method conditions' \
  --publication-relations publication_relations.json > timeline.json
python "$REPO/publication_context.py" package.json publication_relations.json > relations.json
# Inspect the existing methodology trajectory API without changing the package:
PYTHONPATH="$REPO" python - <<'PY'
import json
from pathlib import Path
from research_workflow import apply
package = json.loads(Path('package.json').read_text(encoding='utf-8'))
scope = json.loads(Path('scope.json').read_text(encoding='utf-8'))
print(json.dumps(apply(package, scope['question'], scope['topic'])['methodology_trajectory'], indent=2))
PY
```

The seven-test regression runs the **17 repository CLI stages once in `setUpClass`**, with a 30-second limit per command, and uses the trajectory API directly. It checks two exact condition groups; existential cross-year variation; unresolved same-year order; dependency warnings and exact bases; source/claim/reference-role distinctions; retained reasons and context limits; exact-only citation authority; rejected history versus active synthesis; deferred final judgment; byte-for-byte input immutability; and in-memory processing guarded against file, socket, and mock-provider access. The guards accompany explicit processing flags, not a claim to sandbox arbitrary external providers.

```sh
cd "$REPO"
python -m unittest test_trajectory_conditions_example -v
```

This is a preservation/regression example, not source authentication, semantic validation, a scientist simulation, or a rule for deciding when research has reversed.
