# Persona construction and runtime contract

## Identity and scope

Resolve one scholarly identity using public identifiers and disambiguate names,
affiliations and fields before collection. Confirm consequential scope choices.
The simulation label and `private_beliefs_inferred: false` are mandatory.

## Construction lifecycle

1. Define a charter, identity, intended scope, modes and excluded claims.
2. Build a bibliographic census; distinguish papers from duplicates, notices and independent contributions.
3. Select a review-centered behavioral corpus; use original research where its role is justified.
4. Freeze holdout selection before substantive holdout reading. Record split and authorization.
5. Acquire only authorized sources; preserve bytes, hashes, locators and access restrictions.
6. Parse deterministically and assess structural defects separately from scientific interpretation.
7. Extract each training paper with question, argument, evidence hierarchy, conditions, counterevidence and limitations.
8. Synthesize rules across papers; preserve contradictory papers, topic dependence and temporal change.
9. Check author specificity against independently handled comparator evidence.
10. Build a versioned canonical candidate with separate reasoning, judgment, uncertainty, writing and dialogue policies.
11. Conduct an independent pre-holdout challenge; bind findings to the current candidate.
12. Freeze the candidate hash and evaluate on withheld material; record actual methods and limits.
13. Build a training-only knowledge projection bound to the released candidate.
14. Run runtime boundary tests; publish a release decision with separate validation axes.

These stages are a workflow specification; this repository's Python utilities do not
automate corpus acquisition, semantic extraction, independent evaluation or dialogue.

The detached `split_declaration.py` tools lifecycle steps 2/4 as operator declarations:
a sorted/hash-bound census, disjoint splits and package training comparison. It does
not establish real freeze timing, unseen holdout or census completeness. No canonical
payload or intake path changes. See [split declarations](SPLIT_DECLARATION.md).

## Validation axes

| Axis | What it establishes | What it cannot establish alone |
|---|---|---|
| Evidence integrity | IDs, hashes, locators and source/rule linkage | Semantic support or researcher agreement |
| Predictive persona evaluation | Performance on a declared withheld evaluation | Human agreement or actual personal beliefs |
| Human validation | A documented expert/rater assessment | Automatic generalization to all topics |
| Runtime validation | Retrieval, binding and mode boundaries | Scientific correctness of every answer |

The human-validation axis is tooled as a detached record (`human_validation.py`, see
[human validation records](HUMAN_VALIDATION.md)): raters, date, method, scope topics and
per-rule judgements bound to the persona and knowledge payload hashes. Its status report
(`RECORDED_CURRENT`, `STALE_PACKAGE`, `NOT_PERFORMED`) never edits `validation.human_validation`
inside a persona payload; a changed status is carried only by a new persona version built
and re-bound through the lifecycle above.

Numerical acceptance thresholds are versioned operating choices, not universal
scientific standards. Do not publish historical internal scores as general benchmarks.
Data quantity targets should be justified for the scholar and scope; this public
framework imposes no universal minimum paper count or score threshold.

## Rule record

Keep stable rule ID, category, bounded statement, conditions, exceptions, supporting
and contradicting paper IDs, provenance locators, topic/time dependence, specificity,
confidence and status. Author order can guide selection but does not prove ownership
of individual sentences or ideas in a coauthored paper.

## Runtime

Resolve the exact author/version/build; verify binding using the package's documented
hash convention; retrieve only authorized non-holdout material. Separate paper facts
from persona-rule inference. Fresh literature is external evidence, not retrospective
knowledge of the researcher. Apply writing style after reasoning and judgment.
Return `OUTSIDE_PERSONA_COVERAGE` or `NEED_MORE_EVIDENCE` when appropriate.

JSON result emission in the ten formerly text-mode CLIs writes UTF-8/LF bytes
directly, without changing logical payloads or their bindings. Console encoding
and newline conversion are bypassed; shell capture is a separate boundary. See
[stdout and shell capture](COMMANDS.md#stdout-and-shell-capture).

Discussion among personas is interpretive consultation, not new empirical evidence.
Do not mix identities or treat consultation output as training data automatically.

## Updates

New papers, corrections, retractions, provenance errors, counterexamples and scope
changes trigger controlled reopening. Preserve prior releases and record affected
rules and revalidation. Knowledge ingestion and canonical policy revision are
separate operations. No model or platform-specific backend is required by the design.

Structural intake uses `prepare_local_manifest.py --report-defects` behind the same whole-selection authorization and path preflight as preparation. It reports unchanged parser outcomes and lexical surprises without changing source bytes, writing a manifest or assessing conversion fidelity or scholarly quality. See [local input preparation](LOCAL_INPUT_PREPARATION.md).

Offline handoff text is a pure derived view (`handoff_text.py`), not a new artifact
contract. The complete ASCII-escaped JSON preserves every version and quote; imports
remain bound to the original handoff payload hash. No builder or import path changes.

## Exclusive result files

Use `--output NEW_FILE` on result CLIs to save their exact UTF-8 bytes without shell re-encoding or overwrite. The destination is checked before input reads; stdout carries only a save receipt with hashes and a potentially private path. Existing directory writers and validators keep their contracts. See [exclusive output](EXCLUSIVE_OUTPUT.md) for coverage, bounds, stable-parent assumptions and retained partial files on write failure. No scientific approval, network call or canonical update is implied.

## Release-label display

`persona_cli.py --version` lazily reads bounded, strict UTF-8 JSON from the adjacent
manifest and displays its release/date labels with the running Python version.
It checks display syntax, not inventory or file hashes. The manifest excludes itself
from its hashes: labels are not authenticated and the display is not a signature or
integrity check. Use `python verify_manifest.py` separately. `list` still imports no
repository module; existing script dispatch is unchanged. See
[version labels](COMMANDS.md#version-labels) for limits and failure behaviour.

The [own-file tutorial](TUTORIAL_OWN_FILES.md) is an additive synthetic source-file
rehearsal of existing contracts. It ends after explicit pattern authoring and
selection; empty downstream forms and deferred context judgments remain visible.
It adds no payload fields, inference, validation axis or automated research approval.

Lifecycle step 11 uses [detached candidate findings](CANDIDATE_CHALLENGE.md): `candidate_challenge.py` records supplied kinds bound to candidate hashes. It is a stage, not an additional validation axis; no payload, split binding or operator disposition is changed.

Updates: [reopening declarations](RELEASE_RECORD.md) bind supplied triggers, prior-paper/rule impact and required revalidation axes to the exact previous package. Candidate comparisons use prior rules only. No release decision, canonical update or candidate approval is derived.
