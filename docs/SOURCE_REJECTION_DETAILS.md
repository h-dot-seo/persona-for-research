# Repair local source selections with opt-in rejection details

`prepare_local_manifest.py` and `source_recheck.py` accept
`--explain-rejection`. This completes a local preparation-to-recheck editing
workflow alongside [manual card diagnostics](MANUAL_REJECTION_DETAILS.md).
It does not inspect every possible cause of a rejection.

For existing processing commands without the flag, stdout, stderr and exit
behavior remain unchanged; help now documents the new option. With it,
only an individually failing JSON loader or an existing closed-field check can
add a second stderr line. The line identifies the static argument `selection`
or `package`, lists at most eight missing known keys, and counts unsupported
keys without revealing their names. It is bounded to 512 ASCII bytes. No
paper ID, local path, unknown key or supplied value is added. The original
error line remains unchanged and **may still contain private data**; this is
not whole-stderr anonymization. Native stderr line endings can be CRLF on
Windows; successful saved JSON uses UTF-8/LF through exclusive output.

Covered checks are the preparation selection's root and paper fields, and the
recheck selection's root and source-row fields. Optional preparation
`source_sha256` and `input_inventory` are not reported as missing. The existing
training declaration gate runs first: for example, missing `authorized` still
gets only the earlier gate error. This is not authentication of permission.
Wrong types or a wrong schema with otherwise exact keys receive no invented
missing-key explanation. Cross-input stale bindings, quote/hash mismatches,
path failures and unknown paper IDs receive no guessed attribution. Argparse
usage errors remain exit 2. The diagnostic does not reread files or rerun
validation. Python APIs retain plain original errors by default; their optional
`rejection_label` keyword is diagnostic metadata, not input validation authority.

## Synthetic repair workflow

Use a fresh directory outside this checkout as `OUTPUT`. Before command 1,
copy `examples/local-selection.json` to `OUTPUT/selection.json` and deliberately
remove the first paper's `kind` key. Command 1 must fail with exit 1, empty
stdout, no prepared output, and a detail naming `kind`. Before command 2,
restore that exact key/value (`"kind": "research"`) from the synthetic fixture.
No real classification or permission decision is supplied by this exercise.

Commands 3 and 4 append the already-authored, hash-bound synthetic research
card and build a package wrapper. The second selected paper remains without
observations; it is not silently filled. Command 5 makes a fresh recheck form
with null source paths, not an approved or executable selection.

Before command 6, copy `OUTPUT/template.json` to `OUTPUT/bad-recheck.json`
and remove the first row's `source_file`. Command 6 must fail with exit 1 and
no report. Before command 7, copy the **unchanged template** to
`OUTPUT/recheck-selection.json` and explicitly set paths by paper ID:
`synthetic-0` to `synthetic-0.md`, `synthetic-1` to `synthetic-1.md`.
These paths are relative to the supplied synthetic source root. This manual
step does not grant permission for unrelated files.

```sh
python prepare_local_manifest.py OUTPUT/selection.json --source-root examples/synthetic-sources --explain-rejection --output OUTPUT/prepared.json
python prepare_local_manifest.py OUTPUT/selection.json --source-root examples/synthetic-sources --explain-rejection --output OUTPUT/prepared.json
python curate_local.py append OUTPUT/prepared.json examples/manual-research-card.json --source-root examples/synthetic-sources --output OUTPUT/curated.json
python corpus_files.py OUTPUT/curated.json --source-root examples/synthetic-sources --question "Which synthetic controls matter?" --topic "model design" --output OUTPUT/package.json
python source_recheck.py OUTPUT/package.json --template --operator-id synthetic-source-operator --output OUTPUT/template.json
python source_recheck.py OUTPUT/package.json OUTPUT/bad-recheck.json --source-root examples/synthetic-sources --explain-rejection --output OUTPUT/report.json
python source_recheck.py OUTPUT/package.json OUTPUT/recheck-selection.json --source-root examples/synthetic-sources --explain-rejection --output OUTPUT/report.json
```

The final report checks both selected files, includes the paper with no stored
quotes, and does not mean complete quote coverage, semantic support, source
authenticity, independent evidence, human validation or approval. It does not
modify the package, prepared manifest, source bytes or historical verification
labels. Keep all outputs private and review them before any authorized sharing.
The test executes these seven commands with the stated synthetic edits between
commands; it is not a generic shell runner or an authentication test.

See [preparation](LOCAL_INPUT_PREPARATION.md), [manual observations](MANUAL_LOCAL_OBSERVATIONS.md)
and [source recheck](SOURCE_RECHECK.md) for the unchanged underlying contracts.
