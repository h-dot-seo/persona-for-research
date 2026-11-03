# End-to-end workflow and evaluation boundary

## Reproduce the synthetic CLI round-trip

From the repository root, run:

```sh
python -m unittest test_workflow_roundtrip -v
```

This test creates temporary synthetic Markdown sources from the distributed
reasoning fixture and invokes actual CLI subprocesses, not just Python functions:

1. `corpus_files.py` checks local source bytes and component-specific quotes,
   then constructs a bound package, planning scaffold, chronology, reasoning cards
   and coverage diagnostic.
2. A second invocation changes a synthetic curated observation's stance. The
   resulting exact method/condition group becomes contested.
3. `compare_releases.py` compares the original and candidate outputs, requests
   review and leaves both packages unchanged.
4. Tampered source bytes are rejected without emitting a partial package.

Expected checkpoints: two byte-checked sources, one reasoning card, partial
dimension coverage, a contested candidate and `REVIEW_REQUIRED` comparison.
`llm_used` and `canonical_update_performed` remain false. Temporary test files
are removed. No real publication, private corpus or external service is used.

The same tools can be run directly with authorized files:

```sh
python corpus_files.py examples/file-corpus.json --source-root examples/synthetic-sources --question "Which experiment?" --topic "model design"
python observation_input.py examples/reasoning-corpus.json --question "Which explanation?" --topic "model design"
python compare_releases.py previous-package.json candidate-package.json
```

The first two commands demonstrate different supplied fixtures. They do not
automatically extract reasoning from unannotated articles. Save real input and
generated packages outside this public repository; review content before sharing.

## What the current user experience establishes

- Source loading, quote checks, provenance, evidence gaps, contradictions and
  candidate-release comparison form a reproducible local workflow.
- A question is inserted into planning prompts; its meaning is not analyzed.
  Topic matching is exact and case-insensitive, not semantic retrieval.
- Reasoning components are operator-written. Missing components remain missing.
- Raw JSON is useful for auditing but verbose: the two-source demonstration
  produces roughly 16 KB for a single reasoning card. There is no conversational
  scholar simulation or compact human-facing review interface yet.
- Chronology orders publications. It does not establish career stages, personal
  beliefs, author-specific causation or intellectual change.

This is an evidence-curation and integrity framework, not evidence that the
simulation reasons like an actual researcher. Passing the synthetic workflow
establishes mechanical behavior only.

## Conditions before real-scholar evaluation

1. Select an unambiguous scholarly identity, research question and evaluation
   scope. Specify what would count as useful behavior and what is out of scope.
2. Confirm permission to access each source and use/store its text and quotations.
   Keep restricted article text and researcher-specific packages out of this repo.
3. Freeze training and held-out splits before substantive held-out inspection;
   keep evaluation and runtime evidence separate.
4. Record who curated each interpretation, source locator and attribution limits.
   Arrange independent review of semantic support and conflicting evidence.
5. Decide evaluation criteria before inspecting results. Do not treat field
   completeness, quote matching or corpus size as a fidelity score.
6. If any model or hosted service is proposed later, obtain specific authorization
   for the provider, data to transmit, cost and retention terms before use. Current
   tools do not require such transmission. No credentials or paid API are needed.

No real-scholar validation has been performed or authorized by this demo.
