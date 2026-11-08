# Start an integrated review without choosing a method for the operator

The [review workspace](REVIEW_WORKSPACE.md) can optionally create the existing
pattern, context, publication-relationship and argument forms together. This avoids
assembling their empty templates separately. It still generates **no hypothesis,
claim, link, design step, method choice or review decision**.

```sh
python review_workspace.py ../curated-package.json ../new-integrated-review --question "Which synthetic explanation?" --operator-id synthetic-operator --reference-year 2020 --journey-topic "model design" --target-context "Synthetic target with unresolved conditions."
```

Supply `--journey-topic` and `--target-context` together. The normal workspace
command without them retains its prior output files and behavior. The destination
must be new, outside the repository, with an existing parent and no symlink path
components. Keep it private: the package and its quotes, identifiers, annotations
and provenance are copied, not anonymized.

For a runnable synthetic starting package, first use the existing fixture intake:

```sh
python corpus_files.py examples/file-corpus.json --source-root examples/synthetic-sources --question "Which synthetic explanation?" --topic "model design" > ../synthetic-intake.json
python review_workspace.py ../synthetic-intake.json ../new-integrated-review --question "Which synthetic explanation?" --operator-id synthetic-operator --reference-year 2020 --journey-topic "model design" --target-context "Synthetic target with unresolved conditions."
```

Choose fresh output paths. The first command performs its normal synthetic source
intake. The workspace command itself does not reread those source files or renew
historical verification labels.

## Read the starter correctly

Read `START_HERE.txt`, then `START_JOURNEY.txt`. `READY.json` means only that all
starter files were written. Its extended status is
`NOT_PREPARED_PATTERN_NOT_SELECTED`, and `prepared_input_card` is false.
The ordinary `initial-*` reports still cover only the empty answer/design review;
they are not complete integrated journey reports and do not refresh after edits.

The optional mode adds eight files:

- `patterns.json`: existing empty hypothesis form. No pattern is generated or
  selected from the researcher name, question or publication dates.
- `context.json`: existing applicability form for the explicit topic and target.
  Exact case-insensitive observation-topic matching is not semantic relevance.
  Every matched observation starts deferred, with null comparison/uncertainty and
  no counterevidence selections. Zero matches is valid, not silently repaired.
- `publication-relations.json`: empty relationship form. Publication kinds/years
  do not imply independent studies, review authorship or intellectual influence.
- `argument.json`: empty map bound to the initial empty answer and no declared
  review. No researcher reasoning or private thoughts are reconstructed.
- `source-selection-template.json`: existing all-paper source-selection form with
  **every source path null**, even when the package contains old source filenames.
  Its mere presence grants no file-reading permission and activates no source check.
- `journey-file-selection.json`: relative filenames for the eight required artifacts
  this workspace just created. `pattern_id` and all three optional slots
  (`declared_review`, `method_applications`, `source_selection`) remain null.
- `journey-next-commands.json`: unexecuted argument arrays for inspecting the forms,
  preparing a new argument template and, later, preparing a new input card.
- `START_JOURNEY.txt`: the dependency and review sequence below.

The selection is **not** a prepared input card. Trying to prepare it unchanged
fails before any selected artifact bytes are opened because no pattern ID is set.
An invented ID also fails while the hypotheses array is empty. No integrated
report, method-application form or ready-to-run research plan is produced at setup.

## Author, review and bind in order

1. Inspect `reference-catalog.json`. Author and inspect pattern hypotheses using
   exact reference objects; keep uncertainty, alternatives and missing evidence
   explicit. Then set one existing ID in the selection yourself. A package with
   no observations cannot support a hypothesis merely because files were created.
2. Review the deferred condition comparisons in `context.json` and any explicit
   relationships in `publication-relations.json`. Changing topic, target context or
   question requires fresh context bindings and manual reassessment. The intended
   question must still match the answer/design question text exactly. Do not infer meaning from the
   chronology or require a relationship just to eliminate a mechanical prompt.
3. Edit links before design steps. A link change invalidates the design binding.
   Generate a new empty design template, save to a new filename and manually
   review/migrate intended steps. Do not patch a hash to force an old plan through.
4. Author the answer. If using a declared answer review, generate its fresh template
   from the current answer and record explicit decisions separately. Generate a
   new argument-map template against that exact answer and optional review, then
   author premise/conclusion steps. Editing even an initially empty answer makes
   the starter argument stale. Selecting or changing a review also invalidates it.
5. Whenever a reviewed replacement is saved under a new filename, explicitly update
   that path in `journey-file-selection.json`. Optional method application requires
   a selected pattern and current context/design bindings; it is not generated here.
6. Only when all selected artifacts compose, prepare a **new** [input card](JOURNEY_INPUTS.md)
   and inspect it. Preserve previous files/cards. Each selected-file edit needs new
   card preparation; a stale cross-artifact binding needs regeneration and review
   first. Card preparation validates consistency, not scientific validity.

For the unchanged starter, the generated argument command deliberately has no
`--review`. If you choose a review file later, add `--review` with that explicit file
before creating the new map, and select the same review in the file selection.
The commands are data, not a dependency runner: nothing executes them or changes
their arguments automatically.

Once the selection is intentionally complete:

```sh
python journey_inputs.py prepare ../new-integrated-review/journey-file-selection.json --input-root ../new-integrated-review > ../new-input-card.json
python journey_inputs.py inspect ../new-input-card.json --input-root ../new-integrated-review --format text > ../new-journey-review.txt
```

An empty answer/design can still be inspected after an explicit supported pattern
is supplied; the result reports those gaps and remains human-review-required.
Preparing a card does not fill a single claim, approve a method or execute a study.
For changes between two preserved states, use [journey comparison](JOURNEY_COMPARISON.md).

## Source checking stays separately opt-in

To activate current source checking, complete every path in the source template,
explicitly select that file in the `source_selection` slot and supply `--source-root`
on both preparation and every later inspection. Null paths cannot be used. No root
is copied from the package or saved as standing permission in an input card.
See [source recheck](SOURCE_RECHECK.md) for byte, quotation, path and budget limits.
A byte/quote match is not semantic support, authenticity, rights clearance or approval.

## Failure and verification scope

Every input factory and all output serialization complete before directory creation.
Writes are exclusive; `READY.json` is last. A write failure preserves the partial
folder without a completion marker. Do not reuse it or overwrite files automatically;
choose a new folder. This remains a stable-filesystem convenience, not a crash-atomic
transaction, hostile-filesystem sandbox or authenticated execution log. The output
path check rejects symlinks but does not newly guarantee rejection of every Windows
reparse-point type; input-card loading retains its separate stricter path checks.

Default-mode golden tests normalize only runtime executable/repository/destination
paths. Extended tests compare outputs directly with the existing template factories,
exercise incomplete-selection failures, optional nulls, stale dependencies, each new
file-write failure, and the real CLI transition after explicit synthetic authorship.
All examples are invented. No provider, network, original-source reread, scientific
execution or researcher-fidelity validation occurs during workspace setup.
Actual-browser visual/keyboard/print QA remains blocked and unverified; this increment
makes no browser attempt or workaround.
