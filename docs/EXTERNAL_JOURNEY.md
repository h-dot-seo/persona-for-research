# External context through pinned journey replay

Existing external declarations can now accompany a journey without becoming persona
knowledge. The complete path is explicit authoring, separate external review, v2
file selection/card, folder relocation, fresh inspection and mixed-version comparison.
No model, provider, external agent, network or source discovery is invoked.

`journey_inputs.py template` and `template()` still produce the exact v1 eleven-slot
shape. Explicit `template --include-external` or `template(include_external=True)`
produces persona.journey-file-selection.v2 with the twelfth `external` slot; prepare
returns persona.journey-input-card.v2. V1 rejects even an extra external:null key.
V2 requires every slot: external:null means not supplied, but a selected file whose
JSON value is null is rejected. There is no automatic migration, discovery or hash
repair. Unchanged v1 selection/card APIs and outputs retain their old behavior.

For direct original-input composition, research_journey.py accepts --external FILE;
inspect/render accept keyword external. Existing external_evidence.review validates
the package/draft bindings and optional declared answer review afresh. A selected
null answer review is rejected on this external path, unlike an absent optional
review. A v2 card with no external file retains the old optional-review semantics.

Only supplied external data adds bindings.external_sha256, changes the journey input
hash, appends top-level external_evidence_review and one navigation prompt per item
in the external_evidence agenda domain. Empty items still yield the separate report
but no item prompts. Nothing flows into assemble, evidence routes, source-hash groups,
coverage, active uses, citations, freeze, proposals, model handoffs or judgments.
External items never satisfy citations or establish that a source was used. Their
holdout/comparator membership remains NOT_CHECKED; do not contaminate evaluation
with withheld material. Identity, rights, authenticity and permission are not inferred.

The JSON/text/HTML views keep this report separate. Comparison uses exact external_id
keys for declared additions/removals/field changes, not semantic identity. When either
card is v2, external_slot_comparison separately records both card versions and
NOT_SUPPORTED_BY_CARD_VERSION / NOT_SUPPLIED / SUPPLIED. V1 absence is not silently
rewritten as v2 null; v1/v1 comparison receives no new keys. The full reports and HTML
snapshot preserve all data; private labels/quotes are not sanitized for sharing.

Existing path, symlink/reparse, regular-file, raw/logical hash and source-root pairing
checks apply to the new slot. Cards remain at most 128 KiB; selected JSON files share
8 MiB, including the sidecar. Direct --external composition shares an 8 MiB raw file
budget, then the existing 8 MiB detached logical-input check. Complete reports stay
within 16 MiB before stdout emission; two-card comparison retains its existing input
budgets per side and combined 16 MiB output bound. Source recheck remains separately
explicit: no root or ongoing permission is stored. Checks are not a complete defense
against a hostile concurrently changing filesystem. Existing error messages can name
paths; this feature does not promise global diagnostic anonymization.

## Synthetic connected rehearsal

Run the following Python block from the repository root. It uses shipped fictional
artifacts and a temporary external directory which is removed at the end. It writes
new files with exclusive binary creation, copies them to a different Korean/space
path, then checks current bytes again. It is a demonstration, not a recipe for copying
its synthetic choices into research. Real operators author choices and independently
authorize access; rebuilding downstream artifacts does not authenticate approval.

```python
import copy, json, shutil, tempfile
from pathlib import Path
import journey_inputs as cards
import journey_compare as comparison
import external_evidence
from pattern_hypotheses import template as pattern_template
from applicability_review import template as context_template
from reasoning_links import template as link_template
from design_scenario import template as design_template
from argument_map import template as argument_template
from publication_context import template as relation_template
package = json.loads(Path('examples/trajectory-conditions-package.json').read_bytes())
draft = json.loads(Path('examples/synthetic-external-draft.json').read_bytes())
operator = 'synthetic-journey-operator'
patterns = pattern_template(package, operator)
patterns['hypotheses'] = [dict(pattern_id='synthetic-pattern', operator_hypothesis='Explicit fictional exercise', scope_note='No scientific claim', support_refs=[dict(paper_id='synthetic-2020-a', observation_index=0, dimension=None)], challenge_refs=[], alternative_explanation=None, falsification_check=None, uncertainty=None)]
context = context_template(package, draft['question'], 'Explicit fictional context', 'synthetic method conditions', 2025, operator)
links = link_template(package, operator)
proposal = design_template(package, links, draft['question'], operator)
argument = argument_template(package, draft, operator)
relations = relation_template(package, operator)
sidecar = external_evidence.template(package, draft, operator)
sidecar['items'] = [dict(external_id='invented-external-1', kind='other', identifier_text='invented reference; not a publication', year=None, other_package_identity=None, relates_to_claim_ids=[], role='EXTERNAL_CONTEXT_ONLY', rationale='Explicit synthetic context, not a citation', uncertainty='Synthetic uncertainty not resolved')]
external_evidence.review(package, draft, sidecar)
values = dict(package=package, patterns=patterns, context=context, links=links, proposal=proposal, draft=draft, argument=argument, publication_relations=relations, external=sidecar)
with tempfile.TemporaryDirectory(prefix='external journey ') as temporary:
    root = Path(temporary) / 'original'
    root.mkdir()
    selection = cards.template(include_external=True)
    selection['pattern_id'] = 'synthetic-pattern'
    for name, value in values.items():
        filename = name + '.json'
        selection['artifacts'][name] = filename
        with (root / filename).open('xb') as stream:
            stream.write((json.dumps(value, ensure_ascii=False) + '\n').encode('utf-8'))
    legacy = copy.deepcopy(selection)
    legacy['schema'] = cards.SELECTION_SCHEMA
    legacy['artifacts'].pop('external')
    previous = cards.prepare(legacy, root)
    current = cards.prepare(selection, root)
    report = cards.inspect(current, root)
    moved = Path(temporary) / '이동된 공백 폴더'
    shutil.copytree(root, moved)
    assert cards.inspect(current, moved) == report
    result = comparison.compare(previous, root, current, moved)
    assert result['external_slot_comparison']['previous'] == 'NOT_SUPPORTED_BY_CARD_VERSION'
    assert result['external_slot_comparison']['current'] == 'SUPPLIED'
    assert result['previous_report']['evidence_routes'] == result['current_report']['evidence_routes']
    html = comparison.render(previous, root, current, moved, format='html')
    assert 'External evidence (not persona knowledge)' in html
```

Synthetic regressions additionally cover stale bindings, changed bytes, copied hash
tampering, selected nulls, exact slot sets, sidecar changes/removal, budgets, passive
HTML and old v1 behavior. DOM/escaping/snapshot checks are not browser visual,
keyboard or print QA; that validation is recorded separately rather than assumed.
