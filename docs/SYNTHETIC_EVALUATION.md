# Compare a frozen synthetic answer with held-out labels

This tool measures **agreement with supplied synthetic labels**, not actual scholar
reasoning, semantic support or a scientific benchmark. The shipped labels are a
small manually specified teaching fixture for the quickstart. They are marked
`holdout` because the modeling/freeze commands do not consume them; they are **not**
a blinded or independently collected evaluation set. Anyone can read the public
fixture, so it cannot establish unseen-label performance.

## Freeze first, evaluate separately

Complete the [quickstart](QUICKSTART.md). In a UTF-8-capable shell (for example POSIX
or PowerShell 7, not default PowerShell 5 UTF-16 redirection), run:

```
python evaluate_synthetic.py freeze ../persona-synthetic-demo/revision.json ../persona-synthetic-demo/draft.json > ../persona-synthetic-demo/frozen-submission.json
python evaluate_synthetic.py evaluate ../persona-synthetic-demo/frozen-submission.json examples/synthetic-holdout-labels.json > ../persona-synthetic-demo/evaluation.json
```

Check exit status after each command; do not proceed on an empty/failed output.
Shell redirection can overwrite a file even when validation fails. Choose new
output filenames if preserving earlier submissions. The evaluation CLI itself
never modifies the package, draft, labels or source files.

`freeze` has no label input or provider option. It validates the package/draft,
authorization, training-only runtime scope and source/rule consistency, then emits
only claim IDs/types, citation references/roles, supplied source hashes and source
claim labels, plus a training reference catalog and package/question/draft hashes.
Answer text, question text, quotations and original source segments are omitted.
This increment accepts only the `synthetic-scholar` identity and `synthetic-` paper
IDs. Those names are safeguards against accidental scope expansion, **not proof**
that data are synthetic or nonprivate. Metadata/hashes can still be sensitive.

`evaluate` reads only the frozen metadata and separate labels, not a corpus or draft.
The labels must declare `synthetic_only: true`, `split: holdout`, an explicit dataset
ID, and the exact frozen package/question bindings. Unknown fields, duplicate claims
or reference/role pairs, bad hashes and references outside the frozen training
catalog are rejected. Every gold source hash must match that reference in the
bound catalog; inconsistent source hashes are label errors, not scored misses. Training/comparator label splits and holdout papers in a
package are rejected. Evaluation errors are not inserted as new training records.

A self-consistent submission hash is not authentication or proof that it was frozen
before anyone saw labels. These local commands cannot detect prior manual exposure,
intentional relabeling of source data or a deliberately forged self-consistent file.
Do not claim technical enforcement of a blinded scientific study.

## What is counted

The claim IDs are fixed benchmark slots, not semantically matched text. Renaming an
ID creates a missing expected claim and an unexpected submitted claim.

- **Citation labels:** exact match within the same claim on paper/observation/
  component reference, operator citation role and supplied source hash. Matches,
  unexpected citations and missing citations are counted. Precision is matched /
  (matched + unexpected); recall is matched / (matched + missing). An empty
  denominator yields JSON null, not a perfect score. Another claim's citation does
  not fill this claim's omission. Duplicate reference/role entries are invalid.
- **Answer claim types:** expected count and matched type count, plus missing and
  unexpected IDs. `source_quote` and `operator_synthesis` stay distinct. This does
  not assess whether a synthesis's wording falsely implies an author's beliefs.
- **Source claim types:** matched/mismatched labels among matched citations, with
  unmatched expected citations counted separately. Gold source labels are not
  silently replaced by the submitted catalog. A disagreement may be an erroneous
  gold label; the tool cannot decide which scholarly interpretation is correct.
- **Counterevidence:** expected `challenge` citations preserved or missing under the
  same exact matching rule. It does not search for unknown contrary literature or
  decide whether a citation actually challenges the answer.

No combined score or pass/fail threshold is emitted. Unexpected uncited claims are
reported under claim presence, not hidden inside a citation score. None of these
metrics measures uncertainty quality, logical validity, correct source interpretation,
rights, author ownership or researcher fidelity.

## Reproduce the intentional gap

For the unchanged quickstart:

- Three expected citations match; the conclusion's expected context citation is
  missing. Citation-label precision is 1.0 and recall is 0.75.
- Three answer claim-type labels match.
- Three matched citations have matching source claim labels; one expected citation
  remains unmatched.
- The one expected challenge citation is preserved.

Precision 1.0 does **not** mean a correct answer: the conclusion is still uncited,
answer review is deferred, applicability is untested and semantic validation was
never performed. The expected missing citation was manually chosen for this
synthetic task, not discovered by the evaluator.

The negative cases alter a component/role, remove the challenge, change a synthesis
into a valid stored quote, rename a claim, omit all claims, tamper with a submission
and attempt holdout/training boundary violations:

```
python -m unittest tests.test_synthetic_evaluation -v
```

Real researcher evaluation would require separately authorized sources, prespecified
independent labels, genuine freeze/split governance and domain reviewers. This tool
implements none of those scientific assurances and makes no actual model calls.
