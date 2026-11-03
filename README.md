# persona-for-research

공개 학술 근거의 범위 안에서 연구자 페르소나를 구축·검증·활용하는 프레임워크입니다.
Evidence-bounded scholarly simulations, with explicit provenance and holdout isolation.

**A persona is a scholarly simulation, not the researcher.** Private beliefs,
unpublished opinions, personal memories and private communications are outside scope.
No actual researcher persona, article corpus, knowledge database or validation scores
are included in this repository.

## Included

- Generalized construction lifecycle and separate evidence/predictive/human/runtime validation axes.
- Logical JSON binding validator (`persona.py`) and a holdout-redacting projection helper (`safe_canonical_read.py`).
- Synthetic templates and tests; a portable agent workflow in `SKILL.md`.

This is a framework and mechanical tool release. It is not a trained model, a complete
corpus harvester, a turnkey multi-agent runtime, or proof of scholarly validity.

## Quick start

Python 3.10+, standard library only:

```sh
python3 persona.py examples/persona.json examples/knowledge.json
python3 safe_canonical_read.py examples/persona.json
python3 -m unittest discover -v
```

The synthetic example has no learned rules and no papers. Passing means its
mechanical bindings are consistent, not that any real persona has been validated.

## Two layers

**Persona Core** represents paper-supported question framing, reasoning, judgment,
counterargument, uncertainty and writing policies. **Knowledge Layer** represents
attributable scholarly content. Expanding knowledge does not silently change the
canonical reasoning policy. Training evidence, holdout evidence, comparator-author
evidence and fresh external evidence must remain distinct.

## Binding and retrieval

The example uses a documented **logical JSON payload hash**: SHA-256 of UTF-8 JSON
with sorted keys, compact separators, `ensure_ascii=False`, no NaN and no excluded
fields. This is distinct from an original-file byte hash. The knowledge map binds
to the whole persona payload and matching author/version/build. Runtime papers must
be training-only, explicitly eligible, author-matched and source/locator-linked.
The validator checks hash shape, not whether a source actually exists or supports a claim.

`safe_canonical_read.py` is a conservative convenience projection. It removes many
explicit holdout fields but cannot recognize every possible encoding or mislabeled
record. It is **not** a privacy anonymizer, access-control system or publication filter.
Enforce split authorization before retrieval; never rely on redaction to repair leakage.

See [lifecycle](docs/ARCHITECTURE.md), [workflow](SKILL.md),
[publication boundary](PUBLICATION.md) and [security](SECURITY.md).
No license has been selected by the owner yet; see [rights](RIGHTS.md).

## Paper-to-research-plan workflow

```sh
python research_workflow.py examples/research-corpus.json --question "Which experiment discriminates models?" --topic "model design"
```

The JSON result contains a hash-bound persona/knowledge package, chronological
research/review trajectory and a question-specific planning scaffold. Input papers
must be explicitly authorized, author-matched, training-only and runtime-eligible.
Each operator-curated observation supplies method, topic, condition, limitation and
locator. Exact topic matching determines coverage; unmatched topics abstain.
Applications retain rule/paper/locator links and are labeled system inference.
Coauthor attribution remains uncertain. No LLM, automatic paper extraction,
cross-paper generalization, scientific validation or real researcher data is included.
Synthetic source hashes are placeholders, not receipts for real publications.
