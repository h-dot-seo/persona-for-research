# Extract one literal response

`handoff_packet.py extract-response` saves a bound JSON fence from **one message
text file**. Copy the intended assistant message yourself. It is not a conversation
export parser or a role detector; no ChatGPT/Codex account export is supported.
Existing prepare `--format text` views already serve the render use case and are
unchanged. Their un-fenced skeletons are not extracted as responses.

## Synthetic roundtrip

OUTPUT must already exist outside the repository. The example message is invented,
not evidence of model execution. Existing declared provenance remains an explicit
synthetic fixture; extraction does not create or populate provenance.

```sh
python answer_proposals.py prepare examples/review-attribution-package.json examples/review-attribution-scope.json --output OUTPUT/handoff.json
python handoff_packet.py extract-response examples/review-attribution-transcript.md OUTPUT/handoff.json --output-dir OUTPUT/extracted
python answer_proposals.py import examples/review-attribution-package.json examples/review-attribution-scope.json OUTPUT/handoff.json OUTPUT/extracted/response.json examples/review-attribution-provenance.json --output OUTPUT/candidates.json
```

## Literal grammar and selection

Input must be UTF-8 without BOM or NUL. LF and CRLF, including mixed line endings,
are accepted without normalization; bare CR is rejected. Only exact standalone
opening ` ```json ` and closing ` ``` ` lines (without the spaces shown here) are
supported. Indentation, other languages, tilde fences, longer fences, nesting and
unclosed fences are rejected. This intentionally narrow grammar is not CommonMark.
Other prose is inert. A quoted JSON string containing escaped newlines/backticks
cannot introduce a standalone delimiter. Every JSON fence is parsed with strict
JSON: duplicate keys, non-finite numbers and excess nesting fail closed, even in
unrelated fences. A matching object must contain exactly `handoff_sha256` and a
`candidates` list. Candidate semantics are left to the existing importer.

The matching hash is `persona.payload_sha256` of the supplied handoff object.
The extractor does **not** reconstruct that handoff from package/scope/corpus.
Zero matching objects gives `NO_BOUND_RESPONSE`. Multiple matches give
`AMBIGUOUS_BOUND_RESPONSES` unless `--occurrence N` explicitly chooses one; N is
1-based among matching objects in document order, not among all fences. No latest,
best, nonempty or semantic preference is inferred. Out-of-range selection fails.
A single matching empty list may be extracted: it proves neither a model answer
nor successful execution. A user can write any matching object themselves.

## Output and boundaries

The two inputs together are bounded to 8 MiB. All three outputs together are
bounded to 16 MiB and fully prepared before creating the directory. Output is a
new external directory with an existing plain parent; symlink/reparse ancestors,
repository destinations and existing paths are rejected. Files are exclusively
created in order: `response.json`, `extraction-receipt.json`, then `READY.json`.
The response preserves exactly the bytes between delimiter lines, including its
line endings and trailing whitespace. No reserialization, hash repair or adoption
occurs. Success prints the READY JSON; extraction errors print no partial stdout.
I/O failure can leave a directory and partial files. They are deliberately retained,
not automatically deleted. READY is written last but can itself be partial on
write failure; require successful exit and complete files, never its mere presence.
When inspecting saved artifacts, strictly parse the marker and receipt and compare
their recorded receipt/response SHA-256 values with the actual file bytes. These
checks detect mismatches, not authenticity; this tool does not offer a saved-bundle
verification command.
Retry with a new directory after inspecting the failed one.

Receipt schema is `persona.response-extraction.v1`, status
`LITERAL_FENCE_EXTRACTED_NOT_MODEL_ATTESTATION`. It records transcript raw hash,
handoff payload hash, selected entire-fence raw hash, response raw hash, occurrence,
bound response count and selection reason (`ONLY_BOUND_RESPONSE` or
`EXPLICIT_OCCURRENCE`). `fence_byte_start/end` include both delimiter lines and their
line endings; `response_byte_start/end` exclude delimiters. Offsets are zero-based
UTF-8 byte offsets with exclusive ends, not Unicode character or line indexes.
It records no conversation/message identity, provider, run_id or inferred provenance.
Negative claims explicitly leave model execution, role/transcript authenticity and
semantic validation unverified. READY only reports files written, not approval.

Private messages and source text must not be published or transmitted without
permission. This tool performs no model/network call or command execution. Continue
through the relevant unchanged importer, which reconstructs current-input bindings
and checks candidates. Extraction itself cannot authenticate a fabricated message.
See [answer proposals](ANSWER_PROPOSALS.md), [argument proposals](ARGUMENT_PROPOSALS.md),
[pattern proposals](PATTERN_PROPOSALS.md), [application proposals](APPLICATION_PROPOSALS.md)
and [model handoff](MODEL_HANDOFF.md) for their distinct review/adoption loops.
