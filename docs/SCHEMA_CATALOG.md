# Completed-structure preflight for manual cards

This optional, read-only tool checks the **manual append → manual revision**
input-card authoring flow before the existing consumer runs. It reports multiple
static errors without reading a manifest or any source body. It does not replace
the existing APIs, execute an append/revision, repair hashes, or authenticate
permission, source rights, identity, science or human approval.

The two fixed documents are [append](../schemas/manual-observation-card.completed.schema.json)
and [revision](../schemas/manual-observation-revision-card.completed.schema.json).
Their completed-structure URNs are catalog identifiers, not new instance fields.
Choose `manual-append` or `manual-revision` explicitly. Never add `$schema` or a
catalog identifier to a card. The revision audit shares a schema string with its
input card but is not that input shape and fails this preflight.

```sh
python schema_catalog.py list
python schema_catalog.py show manual-append
python schema_catalog.py check manual-append examples/manual-research-card.json
python schema_catalog.py check manual-revision examples/manual-revision-card.json --text
```

These supplied cards are fictional examples only. A successful structural check
does not make their bindings current for another manifest or authorize reuse of
their choices. Exit 0 means structure conforms; exit 1 with a report means structure
does not conform. Invalid JSON, unreadable/oversized input or output-budget failure
uses exit 1 and a fixed stderr message, with no result stdout. Invalid deployed
catalog schema uses exit 2 and a different fixed stderr message. Argparse usage
errors also use exit 2. Neither unknown keys nor input values appear in check
reports; known field paths and fixed codes identify errors. This does not promise
that argparse will conceal a user-supplied invalid command argument.

## Deliberately restricted implementation

The JSON Schema 2020-12 documents describe completed **structure**, not import-ready
acceptance. The stdlib checker supports only their object/string/integer types,
properties, required, additionalProperties:false, string const/enum, maxLength,
integer minimum and two fixed patterns: `\S` and
`^[0-9a-f]{64}(?![\s\S])`. The latter is the existing exact lowercase SHA-256 shape.
`\S` requires a non-whitespace character using Python Unicode regex semantics.
Annotations are `$schema`, `$id`, title, description and readOnly. No other keyword,
arbitrary regex, external/local reference, URI retrieval, array or composition
support is claimed. Unsupported deployed schema fails closed. The small subset
is not a general JSON Schema implementation. ReadOnly is an annotation only.

The checker opens only its fixed schema and the explicitly supplied card, not
paths named inside the card. The card's raw input budget is 8 MiB; each fixed schema
is independently bounded to 8 MiB and 512 schema nodes/depth 16. Reports are bounded
to 16 MiB before any stdout write. Fixed schema depth and closed property paths
bound error traversal; unknown subtrees are not walked. No output file option,
shell execution, network, provider, clock or hidden editor configuration is added.

Empty template strings and null claim/stance choices fail this completed profile,
although the seven existing editor profiles deliberately allow editing placeholders.
Absent reasoning or an empty reasoning object is valid, not unfinished by itself.
No generic observation text length limit is invented. Revision's four authoring
strings retain their existing 2000-character maximum. Schemas do not derive choices.

Python still checks fresh manifest/previous-observation hashes, selected paper and
index membership, source bytes/locator/quote, changed content, and both new identity
labels. An unchanged or stale card can pass structure. JSON Schema integer includes
`0.0`; the revision API rejects it because that API requires an exact int. A very
large integral index can likewise pass static shape but fail actual membership.
No result means import validation, semantic validation or hash binding was run.
The existing Python consumers remain authoritative. Prior wrong quotes may be
corrected by revision; preflight does not change that behavior.

## Synthetic connected rehearsal

Run from the repository root. This single Python block uses only fictional shipped
sources and returns detached values, without writing files. In real work source
access requires independent authorization and all choices must be explicitly authored.
The two `check` calls precede the actual append/revise APIs; their success alone
never executes those APIs. Existing examples and editor documents remain unchanged.

```python
import copy, json
from pathlib import Path
from prepare_local_manifest import prepare
from curate_local import template, append_observation
from revise_local import template as revision_template, revise
from schema_catalog import check
root = Path('examples/synthetic-sources')
manifest = prepare(json.loads(Path('examples/local-selection.json').read_bytes()), root)
card = template(manifest, 'synthetic-0')
assert not check('manual-append', card)['structurally_conforms']
card['observation'] = copy.deepcopy(json.loads(Path('examples/file-corpus.json').read_bytes())['papers'][0]['observations'][0])
card['observation']['stance'] = 'support'  # Explicit fictional choice, not a default.
assert check('manual-append', card)['structurally_conforms']
appended = append_observation(manifest, card, root)
revision = revision_template(appended, 'synthetic-0', 0)
assert not check('manual-revision', revision)['structurally_conforms']
revision.update(operator_id='synthetic-operator', revision_reason='Explicit synthetic wording change', new_version='synthetic-new-version', new_build_id='synthetic-new-build')
revision['observation']['method'] += ' (synthetic revision)'
assert check('manual-revision', revision)['structurally_conforms']
revised, audit = revise(appended, revision, root)
assert manifest['papers'][0]['observations'] == []
assert appended['papers'][0]['observations'][0] != revised['papers'][0]['observations'][0]
assert audit['status'] == 'MANUAL_REVISION_REQUIRES_REVIEW'
```

The dedicated tests exercise this flow, the four CLI commands, nested mutations,
placeholder rejection, control/private-value non-disclosure and structural-pass /
authoritative-rejection counterexamples. They are not a claim of whole-product
validation or a guarantee that an arbitrary JSON Schema engine implements the same
restricted support policy. Existing consumers perform their normal checks again.

The [first-observation correction flow](OBSERVATION_PREFLIGHT.md) adds observation-response and declared-provenance profiles. Arrays, bounded items, string-or-null and the fixed provenance control pattern are supported; this is still not a general JSON Schema implementation. Oversized arrays report MAX_ITEMS without inspecting their rows.
