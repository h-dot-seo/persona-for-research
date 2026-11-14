# Editor documentation for three optional declaration forms

The three JSON Schema 2020-12 documents in `schemas/` support editing, not import
readiness. They are separate optional workflows, **not a required serial pipeline**:

- `source-recheck-selection.editor.schema.json`: choose explicitly authorized local sources.
- `declared-provenance.editor.schema.json`: transcribe a declared execution identity.
- `human-validation-record.editor.schema.json`: transcribe a named person's assessment.

Their `$id` URNs identify **editor profiles**, not new artifact versions. Do not add
`$schema`, `$id` or another schema field to any instance JSON. Existing exact-key
validators would reject it and hash bindings would change. Associate schemas using
your editor's own file-match settings if desired; this repository installs no
settings, fetches no schema URI and supplies no runtime checker or schema CLI.

Empty text/collections and the actual template nulls are deliberately permitted.
An editor showing no errors does not mean a form is finished, authorized, current,
authenticated, scientifically valid or approved. Python remains authoritative.
`readOnly` is an editor annotation, not a security control. Copy binding values from
the existing template, never repair hashes or reassign stale rule IDs. No judgment,
decision, stance or approval default is supplied by these documents.

## Source selection: synthetic API example

This example reads only shipped invented sources. For real work, independently
obtain authorization and explicitly choose the correct root and every filename.
The template phase itself does not read source bytes. A source_file null is an
editing placeholder; audit rejects it. There are no optional JSON keys: top-level
schema/package_sha256/operator_id/sources and each paper_id/source_file are exact.

```python
from pathlib import Path
from strict_json import load
from corpus_files import load_sources
from research_workflow import build
from source_recheck import template, audit
source_root = Path('examples/synthetic-sources')
package = build(load_sources(load(Path('examples/file-corpus.json')), source_root))
selection = template(package, 'synthetic-editor-operator')
chosen = {'synthetic-0': 'synthetic-0.md', 'synthetic-1': 'synthetic-1.md'}
for row in selection['sources']:
    row['source_file'] = chosen[row['paper_id']]
source_report = audit(package, selection, source_root)
```

For CLI editing, template uses `--template --operator-id` and no selection/root;
audit instead supplies the selection and `--source-root` without operator override.
See [SOURCE_RECHECK.md](SOURCE_RECHECK.md). The root is a CLI argument, not a new
form field. The editor profile describes string/null and length, not full portable
path semantics. Python `_relative` checks canonical relative Markdown/text paths,
backslashes, colons and ASCII controls; this profile does not import other tools'
stricter Unicode policy. Python also checks every known paper exactly once, package
hash freshness, recorded package eligibility flags, filesystem links, UTF-8, file
hashes and quotes. It does not authenticate user approval or establish access or
usage rights: the source read must be independently authorized.
Those dynamic checks are not JSON Schema claims.

## Declared provenance: synthetic API example

There is no standalone provenance template command or CLI. This is an untagged
five-field operator declaration consumed by existing imports. Empty strings are
editor placeholders, but Python requires nonblank text, maximum 128 characters,
no ASCII controls, and local/remote/unknown for execution_location. Never infer a
provider, run ID, execution location or authorization from a transcript.

```python
from pathlib import Path
from strict_json import load
from declared_provenance import validate_declared_provenance
provenance = load(Path('examples/review-attribution-provenance.json'))
validate_declared_provenance(provenance)
```

This checks a shipped invented declaration, not an actual provider execution.
The relevant handoff importer performs its separate replay and candidate checks.
See [MODEL_HANDOFF.md](MODEL_HANDOFF.md) and the chosen proposal-family guide.

## Detached human record: synthetic API example

The template keeps empty rater/text fields, NOT_ASSESSED items and status:null.
The editor profile permits these while `check` rejects an incomplete record.
For real use, only transcribe the named person's explicit choices; do not create
ratings to make the form pass. This example checks an existing invented record,
not an assessment made by the agent.

```python
from pathlib import Path
from strict_json import load
from human_validation import template, check
human_package = load(Path('examples/trajectory-conditions-package.json'))
blank_record = template(human_package)
filled_record = load(Path('examples/manual-human-validation.json'))
human_report = check(filled_record, human_package)
```

All 14 top-level keys, both rater keys and all four item keys are required even
while editing. `judgement` uses the existing four values; only `status` additionally
permits the generated null. Empty arrays/text are editor placeholders, not new
accepted Python inputs. Bounds reflect existing record constants. A template may
copy package identifiers that need correction through the legitimate source
workflow before record checking; the profile is not a promise that every arbitrary
package-derived template is importable.

Python checks real calendar dates, nonblank text, duplicate rater/item IDs, at least
one distinct recorded rater label, package-relative topics/coverage and hash
bindings. For CURRENT_PACKAGE it resolves item IDs/topics against that package.
For STALE_PACKAGE it preserves the recorded IDs without automatic re-resolution
or reassignment. The schema neither decides current/stale nor requires stale IDs
to exist in the current package. Label distinctness is not real-world independence.
See [HUMAN_VALIDATION.md](HUMAN_VALIDATION.md).

## Verification scope

Tests compare exact keys, enums and bounds with available constants and explicit
inline contracts, exercise these three examples, and compare nested structural
mutations with the existing Python checks. A small test-only keyword walker checks
only the documented keyword set; it is not shipped as a user validator or full
JSON Schema implementation. Placeholder acceptance is deliberately tested separately
from completed-input rejection. Duplicate JSON keys, input byte budgets, real
paths, hashes, dates and supported cross-record relations remain mechanical Python
checks. Neither these documents nor the Python checks authenticate user consent,
source rights, human authority or scientific approval.
This is #70 editor documentation, not #88's completed-import subset checker.

Manual append → explicit revision is a separate [two-card editor workflow](MANUAL_EDITOR_SCHEMAS.md), not imported-candidate provenance.
