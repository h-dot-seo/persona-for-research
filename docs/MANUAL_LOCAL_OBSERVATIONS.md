# One observation at a time, without editing the full manifest

After local input preparation, the missing work is scientific reading and explicit
manual structuring. `curate_local.py` makes a small editable card for one paper,
then appends it only after checking its exact manifest binding and the full corpus.
It generates no claim, quote, method, counterargument or attribution.

## Runnable synthetic journey

Use a UTF-8 shell and new output filenames in an existing directory outside the
repository. Redirection can overwrite files or leave empty files on failure; check
each exit status before proceeding. These two prewritten cards are **synthetic
operator fixtures**, not model responses or records of a real human review:

```sh
python prepare_local_manifest.py examples/local-selection.json --source-root examples/synthetic-sources > ../manual-prepared.json
python curate_local.py append ../manual-prepared.json examples/manual-research-card.json --source-root examples/synthetic-sources > ../manual-research.json
python curate_local.py append ../manual-research.json examples/manual-review-card.json --source-root examples/synthetic-sources > ../manual-complete.json
python corpus_files.py ../manual-complete.json --source-root examples/synthetic-sources --question "Which synthetic explanation?" --topic "model design" > ../manual-result.json
```

The result contains a research observation supporting model comparison and a
review observation challenging overinterpretation. Both fixtures have the same
short invented sentence. The review counterargument is explicitly **operator
interpretation**, not a counterargument actually stated in that sentence. Its
exact quote match does not validate its meaning. Question framing, an alternative
explanation and uncertainty are optional explicitly supplied reasoning components.
Research/review kind and publication year come from the selected paper, not guesses.

Inspect the result's `application.steps` and its bound package. Each step preserves
paper, stance, claim type and exact-quote check; publication year remains in the
bound paper/rule records. Inspect reasoning components
and their separate claim types. Missing dimensions remain missing. These fields
are review aids, not evidence of an individual author's private reasoning process.

## Make your own card from the current manifest

```sh
python curate_local.py template ../manual-prepared.json --paper synthetic-0 > ../my-observation.json
```

Read the authorized source yourself. Edit only `observation` in this small file:

- Fill method, condition, limitation, topic and exact section locator.
- Supply a short exact evidence quote that you are permitted to process. Quotes
  are deliberately included in the resulting manifest/package; full unselected
  source bodies are not newly copied from the files. Existing manifest fields are
  preserved, including any pre-existing text or private annotations. This is not
  sanitization, anonymization or publication permission.
- Choose `claim_type`: `explicit_statement` or `operator_interpretation`. No default
  attribution is provided. Choose `stance`: `support` or `challenge` explicitly.
- Optional `reasoning` maps question_framing, alternative_explanation,
  evidence_standard, falsification_check or uncertainty to an object containing
  exactly `text`, `locator`, `evidence_quote`, `claim_type`. Omit unsupported dimensions.
  Each component quote is checked at its own locator in that same paper.

Then use `append` with that card and the same current manifest. The untouched
blank template is intentionally invalid. Successful output is another ordinary
manifest, usable by the existing loader. The target paper's preparation-only empty
inventory annotation is removed; other papers and observations remain unchanged.
No verification/model-review provenance can be injected through the manual card.

To add another observation, generate a **fresh template from the new output**.
The binding covers the entire manifest, including other papers and annotations.
Changing any content or reusing a card after append rejects. It is an unsigned
content binding, not authentication, consent or an append-once global ledger.
Repeatedly applying a card to the same unchanged input can yield the same output.
Preserve prior versions yourself and explicitly choose version/build identity for
new releases before creating their cards. This command does not edit or remove
prior observations or migrate existing package-bound links/reviews.

## Checks and limits

Authorization, author matching and training/runtime-only selection are checked
before source reads, including papers not targeted by the card. A holdout anywhere
rejects. Unknown manual fields and forged verification/mock-review annotations
reject. All existing and new observations are checked against current pinned local
bytes, not only the new quote. Changed source hashes, missing quote/locator and
invalid reasoning fail without emitting result JSON. Source files are never edited.
The manifest contains no durable verification receipt; the existing loader checks
bytes and quotations again when building a package. The shared file-reader's
stable-filesystem assumptions still apply.

No API, LLM, source retrieval, metadata inference, rights check or semantic judgment
runs. A source quote may not support the method you wrote; a reviewer must decide.
An explicit_statement label is the operator's declaration, not automatic author
attribution. The synthetic example cannot establish real researcher representation.

```sh
python -m unittest tests.test_curate_local -v
```

## Continue to an answer/design review

Use [the review workspace starter](REVIEW_WORKSPACE.md) with `manual-result.json`
to create empty bound answer/link/design files, a complete exact-reference catalog,
and visible missing-work reports in one new private folder.

For an existing manually authored observation that needs correction, use
[explicit evidence revision](MANUAL_EVIDENCE_REVISION.md): a pinned old observation,
new version/build, full local checks and a separate before/after audit artifact.

For supported result commands, prefer `--output NEW_FILE` to shell redirection; see [exclusive output](EXCLUSIVE_OUTPUT.md). Existing shell blocks above remain valid but retain shell overwrite and re-encoding risks.
