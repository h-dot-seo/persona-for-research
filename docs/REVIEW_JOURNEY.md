# One review packet for an answer and research design

```
python review_journey.py package.json links.json proposal.json draft.json --reference-year 2020 --format text
# Include an existing hash-bound per-claim review:
python review_journey.py package.json links.json proposal.json draft.json --reference-year 2020 --review review.json --format text
```

Use the same package and exactly the same question text for `answer_draft.py` and
`design_scenario.py`. A mismatch rejects rather than assuming two questions mean the
same thing. The packet hash binds the answer, design, links, publication-year policy,
package and optional declared review. All normal authorization/source/rule and stale
review checks are rerun; saved summaries are not accepted as evidence.

The text starts with mechanical review prompts: uncited claims, missing uncertainty,
missing or deferred/revise/reject claim decisions, missing design fields, no linked
evidence, and later-year or same-year-unresolved evidence. Answer-only citations are
also checked against the explicit reference year, even when no design link uses
them. All indexed publication years must be integers from 1 to 9999. These prompts
are not exhaustive scientific errors, recommendations or a readiness score. Absence
of prompts never means approval.

An exact-reference index lets the reviewer move between:

- An answer claim and its operator-assigned support/challenge/context citation role.
- A design step, its motivation/constraint/counterargument use, link relation and direction.
- Unreferenced links, whose evidence is retained but never assigned an inferred use.

Each row refers to one paper ID, observation index and optional reasoning dimension.
Observation-level and component-level references are deliberately different rows.
Shared references are not independent evidence and do not establish agreement. A
source's own support/challenge stance and explicit-statement/operator-interpretation
label remain separate from these proposed uses. The index includes only references
present in the answer or links, not the entire corpus; the full answer section retains
its uncited-observation inventory, which is not an unused-component inventory.

Complete answer/review and design/publication-scope reports follow the index, preserving
quotes, source locators and hashes, missing fields, rejected claims, unreferenced
counterevidence and candidate-origin provenance. These details intentionally repeat some
source records so the packet can be reviewed without external files. They contain
operator-supplied prose, not generated researcher answers.

The synthetic two-model journey includes an earlier original research interpretation
and a later review criterion. One review endpoint is used as answer context and
challenge and as a proposed design constraint; those labels stay separate. The CLI
exercise flags the later date and missing design falsification rather than silently
borrowing a criterion from the citation or claiming to know the author's reasoning.

```
python -m unittest tests.test_review_journey -v
```

No LLM, external search, actual author corpus, source reread or scientific evaluation
is performed. Publication years do not prove access or intellectual influence;
reviews may discuss others' work. Real evaluation still needs authorized sources,
quotation rights, verified identity and independent scholarly assessment.
