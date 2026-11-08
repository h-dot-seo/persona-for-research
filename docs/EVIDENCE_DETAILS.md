# Inspect the evidence before selecting a method

The short planning review groups exact method/condition strings. It is useful for
finding supplied alternatives and challenge stances, but does not select a method
for the question. Its default rows now include each **observation's own claim type**;
a component's explicit-statement label must not stand in for an operator-interpreted
observation, or the reverse.

For a source-by-source check, use the same command with `--evidence-details`. No new
form or schema is required. From the repository root, run this synthetic journey
with a new destination whose parent exists:

```sh
python synthetic_walkthrough.py ../evidence-detail-demo
python review_package.py ../evidence-detail-demo/revision.json --question "Which explanation should guide the synthetic comparison?" --topic "model design" --evidence-details
```

The first command performs the existing 15-stage mock-only question, answer,
hypothesis/argument, design and counterargument workflow. The second command uses
its revised package to inspect possible evidence for a question. It does **not**
read, revise or approve the existing answer/design. Its question need not equal the
other artifacts' question because it does not claim they were linked; use the
[review journey](REVIEW_JOURNEY.md) for bound answer/design comparison.

## What to check

1. The synthetic original research observation and later review observation share
   method/condition wording, but have different support/challenge stances. Read both
   conditions and limitations. A `CONTESTED` group is a mechanical exact-string
   grouping, not proof of a scientific dispute or a reason to choose either side.
2. Each observation shows its own claim type, quote, locator, recorded quote check,
   source kind/year/hash and recorded byte check. `NOT_PERFORMED` is not a failure
   hidden by a positive aggregate count. Quote matches are not semantic validation.
3. Each component has a separate exact reference and claim label. Mock candidates
   retain the complete proposed-versus-reviewed provenance fields. The synthetic
   uncertainty candidate was proposed as explicit but reviewed as an operator
   interpretation: the proposed label does not overwrite the reviewed one.
4. `Missing for this observation` is local to that observation. A review's supplied
   falsification criterion does not fill the original research observation's gap.
   Even when all dimensions occur somewhere in the corpus, individual records may
   remain incomplete. No missing hypothesis, criterion or uncertainty is invented.
5. The reference object is the existing paper ID / zero-based observation index /
   dimension contract. An observation uses null dimension. Indices stay those of
   the unfiltered package, not positions in this topic-filtered display. Copy only
   references you explicitly intend to use into compatible existing worksheets.

The report includes unsigned package bindings. Rebuilds, reordered observations or
revisions may invalidate copied references; use fresh forms and existing revision
impact checks, never rewrite hashes to force compatibility. No automatic relevance
ranking, author attribution, historical cutoff or method selection is performed.
Only observation topics are matched case-insensitively; paper-level topic metadata
and the free-text question do not broaden that match. Stored years describe source
metadata, not intellectual influence or a historical availability guarantee.

The compact view remains the default. Detailed output is intentionally longer and
includes stored quotations, identifiers and annotations. It is **not** redaction,
rights clearance or evidence that publishing a report is allowed. Sources are not
reopened or reverified, and source authorization remains subject to the existing
package/holdout validators. Explicit-statement labels are curator declarations
about coauthored records, not authenticated ownership by an individual scholar.
No real scholar corpus, LLM, external transmission or scientific validation is used.
