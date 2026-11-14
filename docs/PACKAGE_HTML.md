# Bound package overview and passive HTML

`package_overview.py` inspects one bound package, or a workflow wrapper containing
`package`. Stored wrapper application/boundary fields are ignored. This view does
not require a question, apply a plan, select, rank, recommend or narrow topics.
`package_html.py` is a library formatter with no CLI. Mechanical prerequisites
are `checked_package` and `validated_source_rules`; failure produces no output.
They are not evidence-integrity or other validation-axis success declarations.

## Synthetic example

Replace OUTPUT with an existing private directory outside the repository. Each
output must be new; no overwrite or symlink output paths. These shell commands
are tested without redirection.

```sh
python package_overview.py examples/trajectory-conditions-package.json --human-validation examples/manual-human-validation.json --format json --output OUTPUT/package-overview.json
python package_overview.py examples/trajectory-conditions-package.json --human-validation examples/manual-human-validation.json --format html --output OUTPUT/package-overview.html
```

The fixture has five papers and six observations. With the supplied detached
record, human-validation status is RECORDED_CURRENT: a hash-bound record exists,
not a scientific verdict. Opening the saved HTML is optional and local. Output
receipts describe saved bytes, not permission to share or publish them.

## What is displayed

Identity and both payload hashes; recorded paper/source checks; every stored
observation, quote, locator, stance/claim labels and reasoning components; exact
casefold topic groups; per-observation and aggregate missing dimensions; and
recorded imported-observation origins. Papers, observations and components retain
package order. Topics use casefold order. No count-based ordering or highlighting.
Coverage and topic boundaries appear with their counts: complete dimensions do
not establish readiness or independent evidence. Missing values are not inferred.

Four axis values are copied from persona.validation when supplied and otherwise
NOT_DECLARED. Intake builders do not populate this object. This page does not
verify those declarations. Detached records are checked through human_validation
axis(); only record hash, binding status and judgement counts are copied into
record rows, not individual rationales, rater IDs or colliding-rater labels.
No aggregate score is computed. Repeated records or malformed records fail;
stale valid records remain labeled stale, not silently rebound.

Current local source check is always NOT_PERFORMED. Recorded source/quote labels
are historical supplied data; source files are never reopened. Imported origins
are copied as recorded, not authenticated or adoption-replayed. No semantic
validation, LLM call, canonical update or selection takes place.

## Privacy and passive rendering

This is a corpus-wide private page, not an anonymizer. It copies all stored
quotes, locators, source_file names, reviewer_id/operator_id and imported
provider_id/model_id/run_id/execution_location labels. Keep it local unless the
necessary sharing authorization exists. Privacy and nonclaims appear at the top
and footer. Detached human-record rater identifiers and rationales are excluded;
that does not remove other identities already present in package evidence.

HTML uses the unchanged journey stylesheet and hash-based CSP. There are no
scripts, forms or external resources. All links target internal fragments.
Evidence targets use the full payload hash of a paper/observation/dimension
reference; repeated links point to one unique target. Supplied text is escaped,
not executable instructions. The exact escaped, sorted JSON snapshot at the end
matches the inspector's JSON output, including its trailing newline. Two Python
hash seeds are tested for byte-identical JSON and HTML. Snapshot key sorting does
not reorder paper, observation or component lists.

Package input is bounded to 8 MiB; all detached human records share a separate
8 MiB budget. JSON and HTML each have a 16 MiB output cap before any emission.
Validation/formatting failure has no partial stdout. Exclusive output follows
the shared helper: filesystem write failure may leave a partial new file and
never overwrites it. Input readers are not a hostile-filesystem sandbox or a
wall-time limit. Hashes do not prove authorship, authenticity, rights or approval.

## Browser QA status

Actual visual, keyboard and print QA remains BLOCKED in this environment.
A Chromium launch was attempted but failed before page creation with
`socket() failed: Operation not permitted` and SIGABRT; no permission bypass was
attempted. DOM tests cover passive tags/attributes, unique anchors, fragment
resolution, escaping, long identifiers, Korean text, empty observations and
larger record lists. Shared CSS has wrapping and print/mobile rules, but these
static tests are not screenshots or proof of visual usability. Browser QA needs
a working browser environment before claiming those checks passed.
