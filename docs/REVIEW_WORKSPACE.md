# Start a review workspace from curated local evidence

The [manual observation journey](MANUAL_LOCAL_OBSERVATIONS.md) ends with
`manual-result.json`: a package plus an application summary. Previously, starting
an answer/design review required separate template commands and manually finding
paper/observation/component references. This command creates the existing bound
artifacts and a complete reference catalog together:

```sh
python review_workspace.py ../manual-result.json ../my-review --question "Which synthetic explanation?" --operator-id synthetic-operator --reference-year 2020
```

The output directory must be **new**, outside this repository, with an existing
parent and no symlink path components. Existing empty directories also reject.
Use a private destination: stored quotations, paths, identifiers, operator text and
pre-existing package annotations may be copied. This is not a sanitization tool.
No original source file is read or modified; recorded local-byte/quote checks in
the package are historical labels, not renewed verification.

## What is ready, and what remains your work

Read `START_HERE.txt`, then `initial-review.txt` and `initial-reader-scope.json`.
The starter intentionally has `NO_ANSWER_CLAIMS` and `NO_PROPOSED_STEPS`. A
`READY.json` marker confirms only that all starter files were written. It is not
an answer, a complete research design, human review or scientific validation.

- `package.json`: the checked bound package, detached from the intake envelope.
  A saved `application` summary in that envelope is ignored, not trusted.
- `reference-catalog.json`: all observation/component endpoints with exact
  `evidence.reference` objects, publication kind/year, claim labels, limitation,
  stored quote and recorded checks. Missing reasoning dimensions and papers with
  no observations remain explicit. Entries are **not** relevance-ranked or selected
  for your question. An observation and its components have different references.
- `answer.json`: the existing answer template with no claims. Write your own claim
  text, operator_synthesis/source_quote type, explicit citation roles and uncertainty.
  Copy exact reference objects from the catalog; matching a stored quote does not
  establish semantic support or individual author ownership.
- `links.json`: the existing link template with no edges. Any relation/rationale
  must be explicitly supplied by you. Nothing infers a challenge from publication
  kind or a claim label, or intellectual influence from publication dates.
- `design.json`: the existing design template with no steps. Actions, rationale,
  hypothesis, falsification check, alternatives, uncertainty and link-use roles
  remain your responsibility. Do not fill unknown fields with invented assertions.

See the existing [answer draft workflow](../README.md#evidence-bound-answer-drafts),
`answer_draft.py --help`, `reasoning_links.py --help`, and
`design_scenario.py --help` for the existing contracts. The starter adds no new
answer/plan schema and calls no model.

## Edit, then rerun review

`next-commands.json` contains argument arrays with the current Python executable,
absolute script/output paths and your exact question/operator/year. These are
instructions, **not executed actions or shell strings**. Run the relevant script
with those arguments in your normal terminal/process environment. For example:

```sh
python review_journey.py ../my-review/package.json ../my-review/links.json ../my-review/design.json ../my-review/answer.json --reference-year 2020 --format text
python evidence_scope.py ../my-review/package.json ../my-review/links.json ../my-review/design.json ../my-review/answer.json --reference-year 2020 --format text
```

The `initial-*` files remain the original empty-starter snapshots. Editing answers
or plans does not refresh them. Current reports can expose absent citations,
uncertainty, proposed fields, review decisions and later/same-year evidence without
certifying relevance or design validity. Filled fields do not remove the need for
scientific review. The reference year is an explicit comparison cutoff, not proof
that a paper was available at a particular date.

**Editing links changes the design binding.** Generate a fresh empty design template
using the first entry in `next-commands.json`, save it under a new name and manually
migrate/review any proposed steps against the changed links. Do not overwrite a
completed draft blindly or simply replace its binding hash. After reviewing the
migration, use the intended `design.json` path in the review commands. A package
change similarly requires fresh bound artifacts and re-review, not hash editing.

## Failure and privacy boundaries

All package, authorization/holdout, year and request checks finish before directory
creation. No holdout content can be included by choosing a different question.
Filesystem writes use exclusive creation. An I/O failure can leave a partial
folder; `READY.json` is written last. Preserve it for diagnosis and choose a new
folder. The tool never removes partial outputs or overwrites an existing run.
Keep the destination stable while creating it; this is not a hostile-filesystem
race defense, crash-atomic transaction, or durable signed execution log.

No new source bodies, claims, links, decisions or steps are generated. Existing
package content is copied, including quotations and any private annotations; access
and publication permission remain separate. No LLM, network, real scholar corpus,
scientific execution or authenticated reviewer is used by this synthetic example.

```sh
python -m unittest test_review_workspace -v
```
