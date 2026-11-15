# Detached external context declarations

This tool checks supplied declarations against one bound package and answer draft.
It does not judge external evidence, retrieve a source, add knowledge or satisfy a
citation. The sidecar is independent: core answer_draft/evidence_scope calculations, journeys,
human-validation axes, handoff scopes and input-card schemas are unchanged. Optional
top-level display in the two CLIs is described at the end of this guide.
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
new judgments. A stale/invalid review fails; defer is not promoted to retain. An explicitly supplied
review file containing JSON null is rejected, not treated as an omitted option.
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

## Optional answer and scope display

`answer_draft.py` and `evidence_scope.py` accept --external SIDECAR for a detached
display only. It is freshly checked against the current package/draft and optional
--review artifact. JSON adds only top-level external_evidence_review, exactly the
independent sidecar review result. Text appends an explicitly labeled External
evidence (not persona knowledge) section after the unchanged normal report.

No nested calculations receive the sidecar. Existing status, decisions, claims,
citations, coverage, active references, source groups and freeze output are
unchanged, even with this option. Reject/defer decisions are never promoted to
retain. Without the option, both CLI outputs and input-budget policies are unchanged.
The core Python inspect/review/disclose/render functions remain unchanged.

These synthetic commands reuse the existing package/draft/sidecar and explicitly
create empty links/design artifacts for scope inspection. Empty artifacts are not
approvals. Use a new existing OUTPUT directory; no generated files are published.
Tokenize with shlex before substituting native paths, as above.

```sh
python reasoning_links.py examples/trajectory-conditions-package.json --template --operator-id synthetic-external-operator --output OUTPUT/display-links.json
python design_scenario.py examples/trajectory-conditions-package.json OUTPUT/display-links.json --template --question "What can the invented synthetic record illustrate?" --operator-id synthetic-external-operator --output OUTPUT/display-design.json
python answer_draft.py examples/trajectory-conditions-package.json examples/synthetic-external-draft.json --external examples/synthetic-external-evidence.json --output OUTPUT/answer-with-external.json
python evidence_scope.py examples/trajectory-conditions-package.json OUTPUT/display-links.json OUTPUT/display-design.json examples/synthetic-external-draft.json --reference-year 2025 --external examples/synthetic-external-evidence.json --format text --output OUTPUT/scope-with-external.txt
```

The opt-in path shares 8 MiB across **all** selected inputs: package, draft, external
sidecar, optional declared answer review, and for evidence scope also links/design.
The complete combined JSON or text output is bounded to 16 MiB before any emission.
This cap includes the normal report and detached section, not just the sidecar.
Exclusive output semantics remain unchanged. Stale draft/package/review bindings or
invalid source/rule consistency fail closed, with no partial stdout or new output.

For answer_draft, --external requires draft inspection/review mode and rejects
--template, --review-template, absent draft and question/operator/reviewer overrides
before reading inputs. Optional --review still invokes the existing checker; explicitly supplying a JSON
null review is rejected in the new display paths. Omitting --review is supported. No
journey/card-v2, model adapter, external-file import, human-validation integration,
other-agent contact, source acquisition or attribution policy is added. Keeping
external declarations visible is not knowledge admission or transmission approval.

A later opt-in increment now supports external context through explicit v2 cards and fresh mixed-version comparison: [EXTERNAL_JOURNEY.md](EXTERNAL_JOURNEY.md). The original v1/default path above remains unchanged.
