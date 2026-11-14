# Manual observation authoring editor profiles

These optional JSON Schema 2020-12 documents support one manual authoring flow:
[`manual-observation-card`](../schemas/manual-observation-card.editor.schema.json)
for `curate_local.template` / `append_observation`, followed when needed by
[`manual-observation-revision-card`](../schemas/manual-observation-revision-card.editor.schema.json)
for `revise_local.template` / `revise`. They are editor documentation, not a new
runtime checker or the completed-import checker proposed separately in roadmap #88.
Associate an editor profile externally; do not add `$schema` or any payload field.

The profile URNs identify **input-card roles**. Revision output audit uses the same
`persona.manual-observation-revision.v1` string as its input, but has a different
shape and is rejected by the input profile. Matching that string alone is insufficient.

Template empty strings and observation `claim_type: null` / `stance: null` are
editing placeholders, not executable declarations. No default decision is supplied.
`reasoning` may be omitted or `{}`; each present dimension has exactly `text`,
`locator`, `evidence_quote`, `claim_type`. The five dimensions are question_framing,
alternative_explanation, evidence_standard, falsification_check, uncertainty.
Component claim types require an explicit choice; component null is not a template
placeholder. Manual observations cannot carry imported provenance or verification.
Imported `observation_revision.py` append is a different reviewed-candidate flow.

Bindings and index have `readOnly` editor annotations, not access controls.
Python remains responsible for manifest/previous-observation hash freshness,
selected paper and index membership, nonblank text, source byte/locator/exact quote
checks, changed observation and both new identity labels. Revision's operator_id,
revision_reason, new_version and new_build_id have the actual 2000-character limit.
No generic observation-text length limit is invented. The index is zero-based. JSON Schema `integer` accepts mathematical integer
values such as `1.0`; Python requires an exact `int` and rejects float values
even when mathematically integral. This is another editor/runtime distinction.
A syntactically valid profile can still be stale, a no-op or quote-invalid.
Revision checks the **new complete corpus**, allowing correction of a superseded
wrong quote; it does not require the old quote to match. Source reading needs
independent authorization. Neither profile nor Python authenticates consent,
source rights, operator identity, scientific correctness or human approval.

## Synthetic API rehearsal

Run this Python block from the repository root. It uses only the shipped fictional
sources. A real operator must author their own choices and independently authorize
source access. The API returns detached values; this rehearsal writes no files.
For exclusive external CLI outputs see [manual observations](MANUAL_LOCAL_OBSERVATIONS.md)
and [manual revision](MANUAL_EVIDENCE_REVISION.md). Rebuild/review downstream artifacts;
the revision audit and READY marker do not approve the changed content.

```python
import copy, json
from pathlib import Path
from prepare_local_manifest import prepare
from curate_local import template, append_observation
from revise_local import template as revision_template, revise
root = Path('examples/synthetic-sources')
manifest = prepare(json.loads(Path('examples/local-selection.json').read_bytes()), root)
card = template(manifest, 'synthetic-0')
card['observation'] = copy.deepcopy(json.loads(Path('examples/file-corpus.json').read_bytes())['papers'][0]['observations'][0])
card['observation']['stance'] = 'support'  # Explicit fictional operator choice.
appended = append_observation(manifest, card, root)
revision = revision_template(appended, 'synthetic-0', 0)
revision.update(operator_id='synthetic-editor', revision_reason='Explicit synthetic wording revision', new_version='synthetic-revised', new_build_id='synthetic-revised-build')
revision['observation']['method'] += ' (synthetic revision)'
revised, audit = revise(appended, revision, root)
assert manifest['papers'][0]['observations'] == []
assert revised['papers'][0]['observations'][0] != appended['papers'][0]['observations'][0]
assert audit['status'] == 'MANUAL_REVISION_REQUIRES_REVIEW'
```

The test-only supported-keyword walker checks these documents against synthetic
examples and mechanical mutations. It is not a general JSON Schema implementation,
does not fetch `$schema`/URNs, and adds no product validation API or new authority.
