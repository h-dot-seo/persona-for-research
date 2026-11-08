# Trace a proposed design to evidence links

`design_scenario.py` records how an operator proposes using supplied reasoning
links for a research question. It is proposal traceability, not automated research
design, an individual author's recommendation, or scientific validation.

## Workflow

Start with a bound package and an explicitly curated link artifact from
`reasoning_links.py`. Create an empty proposal template:

```sh
python design_scenario.py package.json links.json --template --question "Which observation would distinguish the models?" --operator-id reviewer-reference
```

Save stdout to a separate local file and write your proposed steps explicitly.
The template contains no actions, hypothesis, roles or automatic choices. It binds
both package hashes and the hash of the original supplied link artifact.

Each step has exactly these fields:

```json
{
  "step_id": "design-1",
  "proposed_action": "Describe the operator's proposed comparison or test.",
  "rationale": "Explain why the operator proposes it and its limits.",
  "hypothesis": null,
  "falsification_check": null,
  "alternative_explanation": null,
  "uncertainty": null,
  "link_uses": [
    {
      "link_id": "existing-link-id",
      "role": "constraint",
      "applicability_note": "Explain how the operator proposes using this particular evidence relationship."
    }
  ]
}
```

Replace the illustrative ID with an existing link and write only a design you
intend to propose. Missing optional fields remain null; empty strings are rejected
rather than treated as meaningful content. Use an empty `link_uses` list for an
unlinked draft step. Do not insert acceptance or author-attribution flags.

Review without modifying any inputs:

```sh
python design_scenario.py package.json links.json proposal.json --format text
python design_scenario.py package.json links.json proposal.json --format json
```

Keep real artifacts outside this public repository. After evidence or link changes,
re-review applicability and references using a new template; changing hashes alone
does not establish that a previous design remains appropriate.

## What the output establishes

- Every action, rationale, nullable design field and use role is operator-authored.
  Steps are labeled `operator_proposal`, not original-author statements.
- `motivation`, `constraint` and `counterargument` describe the operator's proposed
  use of a link. They are not inferred from `supports`, `challenges`, `qualifies`
  or `contrasts`, which still describe the original endpoint relationship.
- One link can have several explicit roles in a step. Duplicate identical link/role
  pairs are rejected; several roles do not count as independent evidence.
- Source claims, component-specific quotes, paper kinds, publication years,
  counterevidence, limitations and recorded checks remain in the evidence section.
  Link-operator and design-operator identities remain separate declarations.
- Missing hypothesis, falsification, alternative explanation or uncertainty fields
  are listed and rendered as `NOT_SUPPLIED`. A source falsification component is
  never copied into a missing proposed-design criterion. Missing proposal fields
  do not prove that scientific evidence is missing, and filled fields do not prove
  a sound or discriminating design.
- An unlinked step is marked `NO_LINKED_EVIDENCE_SUPPLIED`. Linked steps remain
  `LINK_USES_SUPPLIED_NOT_VALIDATED`; citations do not prove applicability.
- All supplied links are retained, including unreferenced counterevidence. The
  unreferenced list does not decide which links are relevant or claim that the
  supplied corpus contains every important objection.
- The question is retained as supplied, not semantically interpreted. No experiments
  are generated or executed, no author viewpoint is authenticated, and no canonical
  rule is updated. Hashes check consistency, not source authenticity or review quality.

The output can contain restricted quotations and operator information. It is not
anonymization or permission to share. No provider call, external transmission or
actual researcher validation occurs.

## Synthetic end-to-end scenario

```sh
python -m unittest tests.test_design_scenario -v
```

A later synthetic review supplies a discriminating-test criterion that qualifies
an earlier research record's alternative explanation. An explicitly simulated
operator proposes a model comparison and cites that link as a constraint. The
proposal's falsification field is deliberately left absent even though the source
contains a criterion. Another case keeps an unused challenge link visible. Actual
intake, link template, design template and JSON/text review CLIs run; no genuine
human review, experiment quality or real researcher's reasoning is asserted.
