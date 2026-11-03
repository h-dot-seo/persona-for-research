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
4. `review_package.py` renders the bound candidate with explicit support/challenge
   and limitations, recomputing the view rather than trusting a saved summary.
5. Tampered source bytes are rejected without emitting a partial package.

Expected checkpoints: two byte-checked sources, one reasoning card, partial
dimension coverage, a contested candidate and `REVIEW_REQUIRED` comparison.
`llm_used` and `canonical_update_performed` remain false. Temporary test files
are removed. No real publication, private corpus or external service is used.

The same tools can be run directly with authorized files:

```sh
python corpus_files.py examples/file-corpus.json --source-root examples/synthetic-sources --question "Which experiment?" --topic "model design"
python observation_input.py examples/reasoning-corpus.json --question "Which explanation?" --topic "model design"
python compare_releases.py previous-package.json candidate-package.json
python review_package.py candidate-package.json --question "Which explanation?" --topic "model design"
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
  produces roughly 16 KB for a single reasoning card. The read-only review renderer
  provides a compact text view without adding interpretation or suppressing
  contrary evidence. There is still no conversational scholar simulation.
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

## Publication-year review

Run `python -m unittest test_publication_timeline -v` for a second real CLI scenario:
an earlier synthetic question-framing/method record, a later review challenge and
a same-year research support record. The JSON and text timeline retain all three,
their locators and separate claim types. Missing question framing is not copied
between records. This adds a reviewable chronological artifact, not an inferred
intellectual biography. See [PUBLICATION_TIMELINE.md](PUBLICATION_TIMELINE.md).

## Reject inconsistent runtime copies

Run `python -m unittest test_rule_source_consistency -v` to reproduce a candidate
whose rule copies differ from its source observations despite recomputed package
hashes. Release comparison still reports structural differences for diagnosis;
planning, compact review and timeline reject the inconsistent candidate without
partial output. Supported recorded quote checks must also agree between source
observations/components and their rule copies. This is a structural consistency
check. Planning reconstructs its all-paper trajectory from validated source fields
instead of relaying a saved summary. This is
not a signature, source-file recheck or semantic validation. Consistently
altered source annotations still require real review.

## Discover a scope first

`python -m unittest test_topic_inventory -v` exercises a real intake → topic
discovery → publication timeline/compact review sequence. The operator chooses
an existing matching key rather than needing to inspect the full package manually.
Labels are grouped only by the same casefold rule used at runtime, with no topic
recommendation or semantic search. See [TOPIC_DISCOVERY.md](TOPIC_DISCOVERY.md).

## Link different approaches explicitly

`python -m unittest test_reasoning_links -v` exercises a later synthetic review's
falsification criterion qualifying an earlier research observation's alternative
explanation, despite different methods and topics. An operator-authored, hash-bound
sidecar links existing nodes; it is not automated synthesis or an author-attributed
reasoning chain. No new canonical policy is created. See [REASONING_LINKS.md](REASONING_LINKS.md).

## Trace a design proposal

`python -m unittest test_design_scenario -v` connects a research question and an
explicitly simulated model-comparison proposal to a later review's criterion link.
The source criterion remains separate from a missing proposal falsification field,
and unused counterevidence stays visible. This is an operator-authored scenario,
not generated experimental advice. See [DESIGN_SCENARIO.md](DESIGN_SCENARIO.md).

## Replay the candidate provenance

`python -m unittest test_design_lineage -v` connects the mock candidate and declared
review flow to the final design and replays the exact package transition without
calling a provider. Source claim labels, reviewed interpretations, selected evidence
routes and missing proposal criteria remain distinct. Inherited mock origins stay
outside the one-revision audit scope. See [DESIGN_LINEAGE.md](DESIGN_LINEAGE.md).

## Review iterative provenance

`python -m unittest test_design_chain -v` performs two explicit review transitions
before auditing the final design. Earlier retained components can be covered by
their own declared stage, while pre-chain inherited history remains unaudited even
if later replaced. Missing intermediate changes are not automatically bridged.
See [DESIGN_CHAIN.md](DESIGN_CHAIN.md).
