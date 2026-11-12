# From local files to a first review journey

An hour-one teaching path, not a completed research workflow. Six invented sources
cover three topics, with one research and one review file per topic, dated 2019-2023.
They demonstrate source-file intake rather than a prebuilt package. Every source
starts with SYNTHETIC TEACHING FIXTURE; every prewritten card is a **synthetic
operator fixture**, not a model response or a real person's review. No real
researcher data, network, model call or scientific approval is involved.

Run from the repository root with Python 3.10+. Replace `OUTPUT` with an existing,
empty directory outside this repository. Use a UTF-8 shell (Git Bash, WSL or
PowerShell 7). Quote paths containing spaces. The commands use exclusive `--output`
files instead of shell redirection; stdout is only a save receipt. A workspace
creates its own new subdirectory. Do not rerun into existing destinations. On a
failure, inspect retained partial files, then choose a fresh output directory.

## 1. Inspect the selection and prepare sources (10 minutes)

Read `examples/teaching-selection.json` and the six files in
`examples/teaching-sources/`. Identity, rights, split, kind, year and topic are
operator declarations, not metadata inferred or authenticated by these tools.

```sh
python prepare_local_manifest.py examples/teaching-selection.json --source-root examples/teaching-sources --output OUTPUT/prepared.json
python curate_local.py template OUTPUT/prepared.json --paper synthetic-teach-models-research --output OUTPUT/first-card.json
```

Produces `prepared.json` with six pinned files and two section locators per file,
and `first-card.json`, a deliberately incomplete observation. No method or quote
has been extracted. Keep the source bytes unchanged throughout this exercise.

## 2. Curate and append explicit observations (15 minutes)

Edit `OUTPUT/first-card.json`: replace only its `observation` field with the object
shown below, keeping the schema, paper ID and manifest hash untouched. In all
marked edit blocks in this guide, replace only the listed top-level fields of the
named existing JSON file. The tests apply these exact blocks in reading order.
This first card reproduces `examples/teaching-cards/models-research.json`.

<!-- edit: OUTPUT/first-card.json -->
```json
{
  "observation": {
    "method": "Compare toy models",
    "condition": "Separated toy signals",
    "limitation": "Synthetic operator fixture; no semantic validation or real author attribution.",
    "locator": "Teaching method",
    "topic": "model comparison",
    "evidence_quote": "Compare separated toy models.",
    "claim_type": "operator_interpretation",
    "stance": "support",
    "reasoning": {}
  }
}
```

These method/condition/stance choices are synthetic operator interpretations,
not conclusions extracted from the quote. The review challenge deliberately uses
the same condition label as the research support, although its passage describes
overlapping signals. The mismatch is a teaching warning, not scientific equivalence.

```sh
python curate_local.py append OUTPUT/prepared.json OUTPUT/first-card.json --source-root examples/teaching-sources --output OUTPUT/curated-1.json
python curate_local.py append OUTPUT/curated-1.json examples/teaching-cards/models-review.json --source-root examples/teaching-sources --output OUTPUT/curated-2.json
python curate_local.py append OUTPUT/curated-2.json examples/teaching-cards/sampling-research.json --source-root examples/teaching-sources --output OUTPUT/curated-3.json
python curate_local.py append OUTPUT/curated-3.json examples/teaching-cards/sampling-review.json --source-root examples/teaching-sources --output OUTPUT/curated-4.json
python curate_local.py append OUTPUT/curated-4.json examples/teaching-cards/calibration-research.json --source-root examples/teaching-sources --output OUTPUT/curated-5.json
python curate_local.py append OUTPUT/curated-5.json examples/teaching-cards/calibration-review.json --source-root examples/teaching-sources --output OUTPUT/curated-6.json
```

Produces six successive manifests; the last has one observation in each of six
papers. Cards bind the entire preceding manifest, including preparation inventory
boundary and section-normalization text. Source bytes, metadata, observations and
append order matter. For different files, generate a fresh template after each
append, read the source, and fill your own observation. Never repair a stale card
by copying a new hash. These fixtures are not default acceptance decisions.

## 3. Build and inspect topics and evidence (10 minutes)

```sh
python corpus_files.py OUTPUT/curated-6.json --source-root examples/teaching-sources --question "How should toy models be compared?" --topic "model comparison" --output OUTPUT/intake.json
python topic_inventory.py OUTPUT/intake.json --output OUTPUT/topics.json
python review_package.py OUTPUT/intake.json --question "How should toy models be compared?" --topic "model comparison" --evidence-details --output OUTPUT/evidence.txt
```

Produces `intake.json`, `topics.json` and `evidence.txt`. Expect
`TOPIC_INVENTORY_ONLY` with three topics and two observations per topic.
In `application.methodology_trajectory`, model comparison has `MIXED_STANCES`,
`within_year_disagreement: true` for 2020.
The evidence view shows `CONTESTED: Compare toy models` with [support] and
[challenge] rows. **CONTESTED is exact-string grouping of operator-declared
stances, not a verdict on a dispute.** Topic, review kind, same-year disagreement
and attribution are supplied fixture choices. Review summaries of another group's
method are not the review writer's recommendation or independent corroboration.
See [evidence details](EVIDENCE_DETAILS.md) for the full boundary.

## 4. Create a review workspace (5 minutes)

```sh
python review_workspace.py OUTPUT/intake.json OUTPUT/workspace --question "How should toy models be compared?" --operator-id synthetic-operator --reference-year 2020 --journey-topic "model comparison" --target-context "Synthetic target with unresolved signal separation."
```

Produces `workspace/READY.json`, `reference-catalog.json`, empty bound forms,
`journey-file-selection.json` and reading instructions. READY means files were
written, not research readiness. Read `START_JOURNEY.txt` and
`reference-catalog.json`: its exact `evidence.reference` objects are the only
references used below. The source-selection template remains inactive; the final
journey does not reread sources unless you explicitly configure that later.

## 5. Author and select one hypothesis (10 minutes)

Edit `OUTPUT/workspace/patterns.json` as below. Compare both references with the
catalog first. This explicitly records one synthetic hypothesis; it does not make
it accepted or scientifically supported. Do not copy it into real research.

<!-- edit: OUTPUT/workspace/patterns.json -->
```json
{
  "hypotheses": [
    {
      "pattern_id": "synthetic-teaching-pattern",
      "operator_hypothesis": "Toy model comparison may depend on signal separation.",
      "scope_note": "Synthetic operator hypothesis over two invented passages; not a scholar trait.",
      "support_refs": [
        {
          "paper_id": "synthetic-teach-models-research",
          "observation_index": 0,
          "dimension": null
        }
      ],
      "challenge_refs": [
        {
          "paper_id": "synthetic-teach-models-review",
          "observation_index": 0,
          "dimension": null
        }
      ],
      "alternative_explanation": "The shared condition label hides differing signal conditions.",
      "falsification_check": null,
      "uncertainty": "Meaning and applicability remain unreviewed."
    }
  ]
}
```

Edit the selection's `pattern_id` too. Leaving it null rejects preparation; the
tool will not choose a method for you. Keep every existing artifact path unchanged.

<!-- edit: OUTPUT/workspace/journey-file-selection.json -->
```json
{
  "pattern_id": "synthetic-teaching-pattern"
}
```

## 6. Pin and reopen the journey (10 minutes)

```sh
python journey_inputs.py prepare OUTPUT/workspace/journey-file-selection.json --input-root OUTPUT/workspace --output OUTPUT/input-card.json
python journey_inputs.py inspect OUTPUT/input-card.json --input-root OUTPUT/workspace --output OUTPUT/research-journey.json
python journey_inputs.py inspect OUTPUT/input-card.json --input-root OUTPUT/workspace --format html --output OUTPUT/research-journey.html
```

Produces the pinned input card and JSON/HTML review views. Open
`research-journey.html` locally. Expect
`HUMAN_REVIEW_REQUIRED_NOT_RESEARCH_APPROVAL` and a review agenda showing
`NO_ANSWER_CLAIMS`, `NO_PROPOSED_STEPS`, `NO_SUPPLIED_LINKS`,
`NO_DECLARED_ARGUMENT_STEPS` and `REASONING_DIMENSION_NOT_SUPPLIED`.
These are useful missing-work signals, not successful answer or design validation.
The selected 2020 sources also show `SAME_YEAR_ORDER_UNRESOLVED` relative to the
reference year 2020; publication years cannot order events within that year.
Context judgments remain deferred. HTML is a passive view, not an editor or approval.
The tests check generated HTML content, not browser visual/keyboard/print behavior.

## Now substitute your own files

Keep real sources and all outputs outside this public repository. Before reading,
declare and check the author identity and disambiguation, your rights to process
the exact files, `authorized`, training/runtime eligibility and split, publication
kind, year and topic. The tools check declaration shape and allowed values, not
the truth of identity, rights, attribution, dates or meaning. A holdout entry
anywhere rejects the whole selection, even if your chosen card uses another paper.

Use UTF-8 Markdown with unique `## ` headings and exact quote substrings. Prepare
a new selection and fresh cards in sequence; inspect each source and use explicit
claim types and stances. A matching quote proves a mechanical binding only.
Rebuild the package, read the topic inventory and evidence, then author your own
hypothesis with exact new catalog references and select its ID before pinning.
Changed sources require new preparation and downstream bindings, not hash edits.
No source discovery, conversion fidelity, semantic review or real persona validation
is automated. The existing [trajectory example](TRAJECTORY_CONDITIONS_EXAMPLE.md)
already illustrates richer chronology in a bound package; this guide adds multiple
topics and one runnable source-file route.

Answer, link, design and argument authoring are later work; start with
[the integrated workspace](INTEGRATED_WORKSPACE.md). A links edit requires a fresh
`design_scenario.py --template` output under a new filename. An answer edit requires
a fresh `argument_map.py --template`. Update any renamed artifact path in the
selection, then prepare a new input card and inspect again. Never replace binding
hashes by hand, and never present these synthetic fixtures as real review decisions.
