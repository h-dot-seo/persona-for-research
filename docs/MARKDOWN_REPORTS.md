# Private Markdown review notes

These are three optional ways to save an existing inspection in a local note,
not a required sequence, a new analysis, or permission to share. Keep the output
private. Human-review rationales and identifiers, source filenames and quotes
may be sensitive. No record is authenticated and no new judgment is derived.
The existing package overview already provides a package HTML view; this feature
does not replace it or add another package/release HTML renderer.

`human_validation.py check/status --markdown` is mutually exclusive with
`--text`. `source_recheck.py --format markdown` is for audits, not templates.
`journey_compare.py --format markdown` preserves both fresh reports, including
v1/v2 external-context distinctions. Defaults and existing JSON/text/HTML formats
remain unchanged. These are display options, not new input schemas or records.

## Exact content and limited rendering guarantees

Each note begins with a private-use warning, displays every result field, then
includes a complete sorted JSON snapshot. Remove exactly four leading spaces
from each line after `## Complete JSON snapshot` and parse the remaining JSON to
recover the inspection result. This preserves JSON meaning, not original input
bytes, whitespace, key order or numeric lexical spelling. It is not a signature.

The display tree applies the existing terminal-control escaping, then escapes
**every ASCII punctuation character** with a backslash. Private field names and
scalar content cannot supply unescaped heading/link/image/table/fence syntax in
that display subset. Newlines/control characters are visible escapes rather than
new Markdown lines. The snapshot uses ensure_ascii JSON and four-space indented
code, not a backtick fence: literal HTML, URLs and arbitrarily long backtick runs
remain JSON data in that code block. Escaping is not applied to snapshot contents
because doing so would change the JSON values. Strings containing actual controls
are JSON-escaped and round-trip as the same controls.

These claims concern the generated text and conventional CommonMark parsing,
not every renderer. Markdown has no CSP; extensions, automatic URL linking and
unsafe renderer settings may behave differently. This tool does not load URLs,
fetch resources, publish notes or promise rendering/network isolation. Review
before sharing. No browser/rendering-engine QA is implied by source-level tests.

Source audit retains its 8 MiB JSON input/report/output and separate 8 MiB source
budget. HV and comparison retain their existing 16 MiB output limits and input
budgets. Markdown duplication/escaping can exceed the output limit when JSON
fits; it then fails before stdout/file emission. Exclusive output still requires
a new path outside the repository. Read/check counts and source-root authority
are unchanged. Current/stale labels never imply scientific approval or automatic
reassignment of old rule IDs.

## Synthetic preparation

Run from the repository root. Replace `OUTPUT` below and in the commands with
one existing private directory outside the repository. It may contain spaces.
This prepares fictional inputs with public APIs and exclusive binary writes;
it does not create or fill a real human assessment. The supplied manual record
is only the repository's synthetic example. Existing files are never replaced.

```python
import copy, json, shutil
from pathlib import Path
from research_workflow import build
from corpus_files import load_sources
import source_recheck, journey_inputs
from pattern_hypotheses import template as pattern_template
from applicability_review import template as context_template
from reasoning_links import template as link_template
from design_scenario import template as design_template
from argument_map import template as argument_template
from publication_context import template as relation_template
work = Path('OUTPUT').resolve()
assert work.is_dir()
def write(path, value):
    with path.open('xb') as stream:
        stream.write((json.dumps(value, ensure_ascii=False) + '\n').encode('utf-8'))
source_root = work / 'synthetic sources'
shutil.copytree(Path('examples/synthetic-sources'), source_root)
manifest = json.loads(Path('examples/file-corpus.json').read_bytes())
source_package = build(load_sources(manifest, source_root))
selection = source_recheck.template(source_package, 'synthetic-source-operator')
for row in selection['sources']:
    row['source_file'] = row['paper_id'] + '.md'
write(work / 'source-package.json', source_package)
write(work / 'source-selection.json', selection)
package = json.loads(Path('examples/trajectory-conditions-package.json').read_bytes())
draft = json.loads(Path('examples/synthetic-external-draft.json').read_bytes())
operator = 'synthetic-note-operator'
patterns = pattern_template(package, operator)
patterns['hypotheses'] = [dict(pattern_id='synthetic-pattern', operator_hypothesis='Explicit fictional exercise', scope_note='No scientific claim', support_refs=[dict(paper_id='synthetic-2020-a', observation_index=0, dimension=None)], challenge_refs=[], alternative_explanation=None, falsification_check=None, uncertainty=None)]
context = context_template(package, draft['question'], 'Explicit fictional context', 'synthetic method conditions', 2025, operator)
links = link_template(package, operator)
proposal = design_template(package, links, draft['question'], operator)
argument = argument_template(package, draft, operator)
relations = relation_template(package, operator)
values = dict(package=package, patterns=patterns, context=context, links=links, proposal=proposal, draft=draft, argument=argument, publication_relations=relations)
previous_root = work / 'previous inputs'
previous_root.mkdir()
file_selection = journey_inputs.template()
file_selection['pattern_id'] = 'synthetic-pattern'
for name, value in values.items():
    filename = name + '.json'
    file_selection['artifacts'][name] = filename
    write(previous_root / filename, value)
previous = journey_inputs.prepare(file_selection, previous_root)
current_root = work / 'current inputs'
shutil.copytree(previous_root, current_root)
# Explicit synthetic whitespace-only edit, then a new card, never old-card repair.
with (current_root / 'patterns.json').open('ab') as stream:
    stream.write(b'\n')
current = journey_inputs.prepare(file_selection, current_root)
write(work / 'previous-card.json', previous)
write(work / 'current-card.json', current)
```

## Four independent note commands

```sh
python human_validation.py check examples/manual-human-validation.json examples/trajectory-conditions-package.json --markdown --output OUTPUT/human-check.md
python human_validation.py status examples/trajectory-conditions-package.json --human-validation examples/manual-human-validation.json --markdown --output OUTPUT/human-status.md
python source_recheck.py OUTPUT/source-package.json OUTPUT/source-selection.json --source-root "OUTPUT/synthetic sources" --format markdown --output OUTPUT/source-note.md
python journey_compare.py OUTPUT/previous-card.json OUTPUT/current-card.json --previous-root "OUTPUT/previous inputs" --current-root "OUTPUT/current inputs" --format markdown --output OUTPUT/comparison-note.md
```

The comparison records changed raw bytes with equal logical JSON. No changed
scientific finding is inferred. Actual source recheck reads only the selected
synthetic files; the other notes add no source or network reads. Tests execute
this preparation and all four commands, decode each snapshot and compare it to
the corresponding fresh JSON result. They also test stale/current human records,
absent records, malformed inputs, escaping, output limits and default byte parity.
