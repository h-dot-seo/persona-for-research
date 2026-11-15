# Compare two freshly reopened journeys in local HTML

`journey_compare.py --format html` formats the existing comparison calculation.
It does not compare cached reports, infer semantic correspondence or promote a
review. Both cards are freshly opened under their explicitly supplied roots;
optional source roots retain the existing exact pairing requirements. See
[journey comparison](JOURNEY_COMPARISON.md) and [input cards](JOURNEY_INPUTS.md).

The view provides context and selected-file changes, exact-reference routes,
declared record changes, prompt counts, and previous/current evidence targets.
Both complete fresh reports (including imported histories and declared reviews)
and a sorted, complete comparison JSON snapshot remain available. List order,
null/absent values and all statuses are preserved. Same-reference links never
establish stable semantic identity across builds. Changes have no improvement or
regression score. Lower prompt counts do not prove resolved scientific issues.

## Synthetic example

Choose an existing private external OUTPUT directory and new targets. These three
commands generate only shipped synthetic data, pin its inputs, then compare the
same card twice. This deliberately demonstrates unchanged inputs, not chronology,
progress, independent evidence or approval. Supply distinct independently prepared
cards and roots for an actual before/current comparison; do not edit hashes to
make old cards accept changed files.

```sh
python synthetic_walkthrough.py OUTPUT/demo --candidate-source offline-import --research-journey --recheck-sources --review-method-use --import-method-use --html-review
python journey_inputs.py prepare examples/synthetic-journey-inputs.json --input-root OUTPUT/demo --source-root OUTPUT/demo/synthetic-sources --output OUTPUT/card.json
python journey_compare.py OUTPUT/card.json OUTPUT/card.json --previous-root OUTPUT/demo --current-root OUTPUT/demo --previous-source-root OUTPUT/demo/synthetic-sources --current-source-root OUTPUT/demo/synthetic-sources --format html --output OUTPUT/comparison.html
```

Successful `--output` prints the existing saved-output receipt and exclusively
creates UTF-8/LF HTML. Existing files, repository destinations and unsafe paths
remain rejected. Without `--output`, HTML bytes go to stdout. Inputs, package
fields, source hashes and review decisions are not modified. Formatting invokes
one comparison and does not add source rereads. Both source checks, when selected,
are **current reads, not historical source snapshots**.

## Navigation and limits

Open the file locally. Use the section links and previous/current exact-evidence
links; their targets have separate prefixes even when both sides use the same
reference hash. Evidence headings remain visible; details expand the records.
Full reports and the complete JSON snapshot have separate disclosure controls.
The view uses the existing passive style/CSP, escaped text, no scripts, forms,
external resources or generated remote links. Malicious input remains inert
quoted data. Responsive columns collapse to one column on narrow screens.

The existing comparison input budgets and JSON/text behavior remain unchanged.
HTML and its JSON snapshot are each bounded to 16 MiB; additional markup can hit
that limit earlier than JSON. No entries are silently dropped. Rendering completes
before emission, so formatting rejection prints no partial stdout or saved file;
a later I/O failure may still leave a partial newly created file under the existing
exclusive-output contract. This is not a hostile-filesystem or wall-time sandbox.

Outputs may contain private quotes, filenames and operator declarations. Keep
local unless separately authorized to share. They are not anonymized, cleared for
publication or authenticated historical receipts. Browser visual, keyboard and
print QA is separate from parser/snapshot tests; this guide makes no completed
browser-QA claim. Tests verify CSP, escaping, unique targets, complete snapshots,
source-check behavior, output limits and deterministic HTML across hash seeds.
