# Edit supplied evidence links and a linked design scenario

These two optional JSON Schema 2020-12 documents help an editor check keys,
types and closed choices across **one existing authoring flow**. They add no
analysis, validator command, model, experiment, decision or authenticated review:

- [Reasoning links INPUT profile](../schemas/reasoning-links.editor.schema.json)
- [Design scenario INPUT profile](../schemas/design-scenario.editor.schema.json)

Use the existing [reasoning links](REASONING_LINKS.md) and
[design scenario](DESIGN_SCENARIO.md) tools as the mechanical validators of
record. These profiles are not generated review-report schemas or the future
completed-input checker. Existing [editor profiles](EDITOR_SCHEMAS.md) remain
separate. An editor's schema support is optional; no dependency is installed.

## Select the input profile explicitly

Neither input has a schema/version discriminator. Associate the input filenames
with the respective local schema file in your editor, for example
`my-links.json` with `schemas/reasoning-links.editor.schema.json` and
`my-design.json` with `schemas/design-scenario.editor.schema.json`. The profile
URN's `v1` identifies this documentation, not a new version field in the input.
Never insert `$schema`, `schema` or `version` into these exact-key inputs. No
schema URI is fetched by the repository's test-only assertion walker.

Both package hashes are copied from templates. Design also binds the hash of the
**original supplied link artifact**, not the generated link-review report.
`readOnly` is an editor annotation, not enforced access control. After changes,
create a fresh template and explicitly re-review choices; do not repair hashes
to force acceptance. Keep actual artifacts outside the public checkout.

## Empty, null and unfinished values are different

- Empty `links` is valid `NO_SUPPLIED_LINKS`; empty `steps` is valid
  `NO_PROPOSED_STEPS`. Neither is an approval or a claim of completeness.
- Endpoint `dimension: null` validly selects the observation itself. A named
  dimension selects a component and must exist on that exact observation.
- Every design step must contain `hypothesis`, `falsification_check`,
  `alternative_explanation` and `uncertainty`. Each value may legitimately be
  null, meaning explicitly not supplied. Omitting the key is invalid.
- Empty `link_uses` is a valid unlinked proposal, not inferred evidence.
- Profiles permit unfinished empty/whitespace strings within documented bounds.
  Python rejects them where it requires nonblank text. This editing allowance
  does not invent null choices for relation, role or claim type.
- JSON Schema `integer` admits `0.0`; Python requires exact int and rejects
  floats and booleans for observation indexes. The endpoint must also exist.

No role is inferred from a relation. One link may explicitly have multiple roles
in a step, but the same `(link_id, role)` pair cannot repeat. Neither multiple
roles nor different source hashes establish independent evidence. Operators
supply relations, rationales, actions and applicability notes; assistants must
not fabricate those choices or genuine review. The following choices are fixed
synthetic teaching declarations only.

## Synthetic linked writing example

Run these two Python blocks in order from the repository root. They use only a
shipped synthetic corpus, keep all generated artifacts in memory, and write no
files. The first creates an empty link template, explicitly supplies one link
from a review observation to a research component, then checks it. It does not
resolve a scholar's actual reasoning or reread source files.

```python
import copy
import json
from pathlib import Path
from observation_input import verified_corpus
from research_workflow import build
import reasoning_links
import design_scenario

corpus = json.loads(Path('examples/reasoning-corpus.json').read_bytes())
package = build(verified_corpus(corpus))
blank_links = reasoning_links.template(package, 'synthetic-link-operator')
assert reasoning_links.review(package, blank_links)['status'] == 'NO_SUPPLIED_LINKS'
links = copy.deepcopy(blank_links)
links['links'] = [{
    'link_id': 'synthetic-qualification', 'relation': 'qualifies',
    'from_ref': {'paper_id': 'synthetic-1', 'observation_index': 0, 'dimension': None},
    'to_ref': {'paper_id': 'synthetic-0', 'observation_index': 0, 'dimension': 'alternative_explanation'},
    'rationale': 'Fixed synthetic operator interpretation for this editing exercise, not scientific evidence.',
    'claim_type': 'operator_interpretation'
}]
link_report = reasoning_links.review(package, links)
assert link_report['semantic_validation'] == 'NOT_PERFORMED'
```

The second creates an empty design template bound to those supplied links. It
explicitly proposes one linked step while leaving all four nullable design
fields undeclared. No missing field is borrowed from the source. The declared
link operator and design operator remain separate, unauthenticated identities.

```python
blank_design = design_scenario.template(
    package, links, 'Which synthetic distinction should be examined?', 'synthetic-design-operator')
assert design_scenario.review(package, links, blank_design)['status'] == 'NO_PROPOSED_STEPS'
design = copy.deepcopy(blank_design)
design['steps'] = [{
    'step_id': 'synthetic-step',
    'proposed_action': 'Inspect a proposed synthetic comparison; no experiment is executed.',
    'rationale': 'Fixed synthetic operator proposal, not an author recommendation.',
    'hypothesis': None, 'falsification_check': None,
    'alternative_explanation': None, 'uncertainty': None,
    'link_uses': [{'link_id': 'synthetic-qualification', 'role': 'constraint',
                   'applicability_note': 'Explicit synthetic use only; applicability is not established.'}]
}]
design_report = design_scenario.review(package, links, design)
assert len(design_report['steps'][0]['missing_fields']) == 4
assert design_report['steps'][0]['evidence_status'] == 'LINK_USES_SUPPLIED_NOT_VALIDATED'
assert design_report['llm_used'] is False
assert design_report['canonical_update_performed'] is False
```

## What shape cannot establish

Python validates package/source-rule consistency, exact binding freshness,
endpoint membership, observation index range and component presence. It rejects
self-links, duplicate link IDs, duplicate same-relation endpoint pairs and
reversed duplicate `contrasts`; it does not reject cycles or infer transitive
links. Design checks step-ID uniqueness, actual link membership and repeated
link/role pairs. The schemas do not approximate these relational checks using
`uniqueItems` or impose new array-count bounds. Same endpoints under distinct
relations and the same link under distinct explicitly declared roles remain
allowed.

The test suite compares exact constants and nested key sets, exercises every
required-key deletion and unsupported-key insertion, and runs the writing
example. It also demonstrates schema-compatible but Python-invalid stale,
missing-reference and duplicate records. The small test walker supports only
its explicitly listed keywords, is not a product JSON Schema validator, and
performs no schema fetching. Passing a shape check is never import readiness.

Neither Python mechanical checks nor editor checks authenticate identity,
source authenticity, actual user permission, human/scientific validation or
semantic support. Quotes and operator declarations may remain private. No
publication permission, canonical update or external transmission follows from
this workflow.
