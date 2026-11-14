# Detached external context declarations

This tool checks supplied declarations against one bound package and answer draft.
It does not judge external evidence, retrieve a source, add knowledge or satisfy a
citation. The sidecar is independent: answer_draft, evidence_scope, journeys,
human-validation axes, handoff scopes and input-card schemas are unchanged.
No HTML or interactive UI is provided.

## Synthetic commands

Choose an existing private external OUTPUT directory; every target must be new.
The draft fixture is a small operator synthesis with no citations bound to the
existing trajectory-conditions package. The sidecar fixture uses clearly invented
non-DOI identifiers, not real publications or personas. Both new files use explicit
LF bytes. Tests tokenize with shlex before native-path replacement, preserving
Windows backslashes and spaces.

```sh
python external_evidence.py template examples/trajectory-conditions-package.json examples/synthetic-external-draft.json --operator-id synthetic-external-operator --output OUTPUT/external-template.json
python external_evidence.py review examples/trajectory-conditions-package.json examples/synthetic-external-draft.json examples/synthetic-external-evidence.json --output OUTPUT/external-review.json
python external_evidence.py review examples/trajectory-conditions-package.json examples/synthetic-external-draft.json examples/synthetic-external-evidence.json --format text --output OUTPUT/external-review.txt
```

Template output is exactly the empty sidecar below, not approval or evidence
addition. Review accepts the operator-filled sidecar, never its review report as
an alternative input. A bound package or its `{package: ...}` wrapper is accepted;
separate persona/knowledge files are not a CLI input form in this release.

## Exact schema and declarations

The sidecar has exactly: schema (`persona.external-evidence.v1`), persona_sha256,
knowledge_papers_sha256, draft_sha256, operator_id, items. All three hashes must
match the validated inputs. Editing a draft while keeping claim IDs invalidates
the sidecar. No hash repair or automatic rebinding is performed. Package validation
uses checked_package and validated_source_rules, then existing answer_draft.inspect.

Each item has exactly these fields:

- external_id: unique nonempty string, at most 128 characters.
- kind: fresh_literature, other_persona_consultation or other, an operator label.
- identifier_text: supplied nonempty text, at most 2,000 characters; never looked up.
- year: null or an integer from 1 through 9999, never boolean or parsed free text.
- other_package_identity: null or exactly author_id, version, build_id (each a
  nonempty string up to 128 characters) and persona_payload_sha256 (64 lowercase
  hexadecimal characters).
- relates_to_claim_ids: distinct known draft claim IDs, each nonempty and at most
  128 characters. An empty list means no declared links; it is not applied to the
  entire draft or all citations. Maximum 1,000 links per item.
- role: the fixed literal EXTERNAL_CONTEXT_ONLY.
- rationale and uncertainty: nonempty supplied text, each at most 2,000 characters.

The operator_id is a nonempty string up to 128 characters. At most 1,000 items are
accepted. Empty items is permitted and yields NO_EXTERNAL_ITEMS, not success or
approval. Nonempty review status is EXTERNAL_CONTEXT_DECLARATIONS_ONLY. Missing or
extra fields and malformed types fail closed. Text is preserved in JSON; displayed
text escapes controls and directional characters. Malicious strings stay inert
input data, not commands, instructions or evaluated expressions.

Only exact identifier_text equality with a supplied package paper_id or locator
is rejected as EXTERNAL_ITEM_DUPLICATES_PACKAGE_SOURCE. There is no trimming,
casefolding, substring comparison, DOI normalization or title matching. A nonmatch
does not prove a different publication or that an item is outside the package.

Only an other_package_identity exactly equal to the current four-field package
identity is rejected. Other identities are not opened or authenticated. Null means
undeclared, not successful identity verification. Any kind may use null or an
explicit identity; kind and identity are not combined to infer who produced text.
Year and kind are not validation of publication, influence, availability, rights
or permission. No relative-year classifications are added.

## Optional answer-review check

`--review ANSWER_REVIEW` uses the existing answer_draft.review checker, including
its exact draft binding and complete claim-decision requirements. Output reports
that checker's answer_status and the review hash, not copied review rationales or
new judgments. A stale/invalid review fails; defer is not promoted to retain.
This option does not make external items citations or validate their relation to
a claim. Without it the existing draft inspection status is reported and the
review hash is null. The output schema is persona.external-evidence-review.v1.

## Limits and strict separation

All inputs, including optional answer review, share an 8 MiB strict-JSON budget.
Output JSON/text is capped at 16 MiB before emission. Template --output is required;
review defaults to stdout with optional exclusive --output. The shared helper rejects
existing targets, repository paths, symlink components and missing parents before
reads. Invalid inputs/formatting emit no partial stdout; I/O failure can retain a
partial new file. Byte limits are not a hostile filesystem or wall-time sandbox.

External declarations are EXTERNAL_NOT_PERSONA_KNOWLEDGE. They do not enter package
knowledge, evidence routes, distinct source-hash groups, coverage, citations or
scores. The unchanged freeze(package,draft) has no sidecar argument, and regression
tests confirm its output stays identical after this review. No adoption or release
approval, validation-axis mutation or canonical update occurs. No source reread,
network, provider, model or other-agent call takes place. Existing answer/model
handoff and evaluation APIs are not extended.

The tool does not read or check holdout/comparator membership. An operator can
therefore record withheld material as external context without detection; doing
so during predictive evaluation can contaminate the evaluation. This warning is
not permission to access such material. Identifiers, rationales and identity labels
may be private. Keep the outputs local unless separately authorized to share them;
writing a sidecar is not rights clearance or transmission authorization.
