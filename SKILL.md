---
name: persona-for-research
description: Plan, build, review or consult an evidence-bounded scholarly simulation using operator-supplied authorized sources and explicit identity, provenance, holdout and validation boundaries.
---

# Research persona workflow

Read README.md and docs/ARCHITECTURE.md. Identify whether the task is build, profile,
consultation, comparison or update. Do not collect a corpus from an ambiguous name.

For building: resolve identity and scope; establish source permissions; freeze split;
parse/QC; extract per-paper evidence; synthesize bounded cross-paper rules; challenge
independently; freeze candidate; evaluate holdout; bind training-only knowledge;
test runtime; record separate validation statuses. Perform only available operations
and report missing backends instead of fabricating artifacts or validation scores.

For consultation: require an exact usable canonical package and authorized knowledge.
Verify identity/version/build/hash binding; deny holdout/comparator retrieval; state
the simulation boundary. Ground answers in rule/source IDs. Label current external
evidence separately. Preserve disagreement and admit uncovered questions.

For human validation: when named raters have assessed listed rules of one exact package,
write the assessment with `python human_validation.py template PERSONA.json KNOWLEDGE.json
--output RECORD.json` (or one bound package file), fill raters, date, method, scope topics,
per-rule judgements, limitations and the independence declaration, set `status` to
`RECORDED`, then run `check`; report the axis with `status` or `review_package.py
--human-validation`. The record is a detached document bound by both package hashes. It
establishes a documented assertion by named labels about listed items only: not
generalization to other topics, not fidelity to the real researcher, not a score, and label
distinctness is not verified independence. Never edit `validation.human_validation` inside
a persona payload or rebind knowledge to carry a status; a changed status needs a new
persona version through the normal lifecycle. See docs/HUMAN_VALIDATION.md.

The mechanical validator is not a scientific reviewer. The projection helper does
not confer access permission or guarantee removal of sensitive content. Keep real
researcher packages and source corpora outside this public repository.

## Executable increment

See docs/COMMANDS.md for every local CLI with its exact usage line and docs/WORKFLOWS.md
for the documented workflows and their explicit limitations; README.md keeps only the
start-here commands and the documentation index. Use only authorized inputs; shipped
examples are entirely synthetic.

`python persona_cli.py list` prints every root command-line script with the first sentence of
its docstring, and `python persona_cli.py run <script> [args...]` runs one of them from any
directory without changing its arguments, output or exit code; the documented
`python <script>.py ...` form stays primary. The unittest suite is the `tests/` package, run
with `python -m unittest discover` from the repository root.
