# Review citation explanations without rewriting old artifacts

Use the standalone citation reasoning audit to inspect why each current answer
claim cites a source. It accepts existing manual drafts and valid reviewed answer
proposal envelopes, including v1 records that never requested explanation fields.
It does not upgrade a draft, edit an envelope, change review decisions, or modify
ordinary answer, argument, journey or handoff output.

```sh
python citation_reasoning.py package.json draft.json --format text
python citation_reasoning.py package.json draft.json --review final-answer-review.json --format text
```

Omit `--format text` for structured JSON. Inputs are explicit files; output goes
only to stdout. To inspect the standard synthetic walkthrough without regenerating
or changing it:

```sh
python citation_reasoning.py ../persona-synthetic-demo/revision.json ../persona-synthetic-demo/draft.json --review ../persona-synthetic-demo/answer-review.json --format text
```

These paths assume the existing walkthrough directory and its generated artifacts.
The command does not create that directory or discover files. Do not publish a
real audit containing private quotations without checking access and quotation
rights separately. No source acquisition or provider transmission is authorized
by preparing or inspecting the report.

## Three different declaration states

Each current citation use is identified by **claim ID + exact reference + role**.
The reference includes paper ID, observation index and nullable reasoning dimension.
An observation and its component are distinct references. The same passage used
for another claim or role has a separate row and identity hash.

- `LEGACY_KEY_ABSENT`: the old citation has no explanation slot. This audit surfaces
  that absence without changing its original inspection or handoff. It does not
  claim the source use was justified or reviewed.
- `EXPLICITLY_NOT_SUPPLIED`: an enhanced citation explicitly supplies null.
- `DECLARED_INTERPRETATION_NOT_VALIDATED`: a rationale/context object was supplied.
  It remains a declaration, not verified semantic support.

Null context boundary is displayed separately; a supplied rationale with null
context is not classified as a missing rationale. The report never invents an
explanation, assigns a quality score, or estimates evidence completeness. Counts
cover supplied current-draft records only. Uncited claims are listed separately,
and empty drafts are explicit rather than appearing as successful coverage.

Each row retains claim text/type, uncertainty, direct source metadata, stored-quote
comparison and the actual final-review label and note, or `NOT_SUPPLIED`. Retained,
revised, rejected and deferred claims remain visible. Retain does not resolve an
absent or null explanation. Declared human/operator identities are not authenticated.

## Keep imported history separate

For valid imported answer envelopes, original, revised and rejected candidate
history appears in a separate, non-active section. Original imported interpretations
remain untrusted. Adopted interpretations retain their imported origin instead of
being relabeled wholly operator-authored. Historical citations are not added to
current-use counts or promoted into active evidence.

This audit consumes a draft, not an unfinished candidate-review packet. Existing
export rules still require all candidate decisions resolved and at least one
accepted claim. To inspect deferred candidate adoption, use the existing
`answer_proposals.py review` command. Final answer-review defer is supported here;
that is a distinct decision stage.

The report binds the full canonical checked package, persona/knowledge data, full
draft and optional final-review hashes. For an imported draft, the binding covers
the entire envelope, including rejected history, rather than only its adopted
claim projection. A stale review fails. No automatic rebinding, migration or
reconstruction of approval is performed.

## Source and interpretation limits

Research/review kind, observation stance, selected claim labels, locators, source
hashes, recorded verification and recorded imported provenance remain separate from
citation roles and explanations. A review article can report others' work. Neither
a role, an explanation nor a stored quote establishes the named researcher's
ownership, beliefs or endorsement.

`source_quote` equality compares only the stored evidence record. This audit does
not reread source bytes or verify a rationale's meaning. Use
[source recheck](SOURCE_RECHECK.md) separately for explicit local byte/quote checks.
Citations and explanations never transfer from premises to uncited conclusions.

The CLI and API reject malformed or non-finite JSON, invalid source/draft bindings,
invalid versions, and missing required explanation fields. Combined logical inputs
are limited to 8 MiB; CLI input bytes are also bounded collectively. JSON and text
reports are bounded to 16 MiB and never truncated into apparent success. Text
escapes untrusted controls and retains complete records/history.

No provider/model invocation, external transmission, browser access, source reread,
canonical update, scientific execution or automatic approval occurs. Historical
model claims are unauthenticated declarations; current no-provider flags do not
prove a historical absence of AI. Human scientific review remains required.

To add an explanation deliberately, follow [citation explanations](CITATION_EXPLANATIONS.md)
and re-review the resulting changed artifacts. This audit has no apply, repair,
accept or auto-upgrade command. Existing outputs remain unchanged unless the caller
independently supplies a different input.
