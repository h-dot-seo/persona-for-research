# Optional manual-input rejection details

`curate_local.py template/append` and `revise_local.py template/apply` accept
`--explain-rejection`. Default output and exception text are unchanged. Success
outputs, validation order, source reads and decisions are unchanged. This is not
an input repair tool, schema validator or approval mechanism.

For covered failures, the original error is followed by one bounded ASCII line:
`  input=card; missing=["observation"]; unsupported_count=0`
The label is the static parser argument `card` or `manifest`, never a filename.
Missing names come only from closed, known manual-card/observation/component keys.
At most eight names are shown, plus additional_missing. Unsupported names are never
shown, even escaped: only their count (capped as 9999+) is displayed. The added
line is at most 512 ASCII bytes before the native stderr newline.

Covered schema failures are the manual append/revision input-card root, required
manual observation fields, missing stance and the exact four-key manual reasoning
component. Non-object values do not manufacture missing-key explanations. Empty objects can report the known missing keys;
wrong schema or enum values with valid key sets receive no key explanation.
The old observation checked by revision belongs to `manifest`; its proposed
replacement belongs to `card`. No array index, JSON pointer, dynamic dimension,
paper/holdout ID, enum value, path or arbitrary key is included in the added line.
A ValueError while loading one JSON input can add its static argument label only.
Cross-input stale bindings, quote/hash failures, authorization gates and ordinary
OSError/TypeError/KeyError/AttributeError do not gain guessed attribution.

The internal ValueError subclass retains its original message and args; str(exc)
is not reformatted. The CLI alone appends optional metadata. Direct calls of the
shared manual observation validator without attribution retain plain ValueError.
Some covered append/revision errors are ValueError subclasses; callers should use
the documented ValueError family rather than exact exception-class identity.
The helper does not rerun validators or reread files to explain an error.

This protects only the **new detail line**, not all existing stderr. Existing
parser messages, duplicate-key diagnostics or operating-system errors can already
contain supplied text or paths. They are preserved, not silently redacted here.
Argparse usage errors remain exit 2 and are not decorated. Covered validation
failures remain exit 1 with empty stdout; stderr uses native LF/CRLF, while
successful UTF-8 stdout.buffer output retains LF. Existing --output preflight
failures remain outside this detail mechanism.

## Deliberate fictional shape failures

These examples deliberately use a corpus as the wrong input-card shape. They
must exit 1 with empty stdout and a second detail line; they do not read source
bytes or create revision output. Replace OUTPUT with a new external path whose
parent already exists. These are diagnostics demonstrations, not valid authoring
recipes; follow the linked manual authoring guides to write real cards.

```sh
python curate_local.py append examples/file-corpus.json examples/file-corpus.json --source-root examples/synthetic-sources --explain-rejection
python revise_local.py apply examples/file-corpus.json examples/file-corpus.json OUTPUT --source-root examples/synthetic-sources --explain-rejection
```

See [manual observations](MANUAL_LOCAL_OBSERVATIONS.md),
[manual revision](MANUAL_EVIDENCE_REVISION.md), and
[editor profiles](MANUAL_EDITOR_SCHEMAS.md). Never infer an author's intent or
replace a missing declaration with a guessed value from an error explanation.
