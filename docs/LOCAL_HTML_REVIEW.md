# Read-only local research-journey view

Large JSON/text reviews are hard to navigate. The optional HTML view presents the
same inspected source-to-method-to-argument journey as one passive local file:
verification scope, grouped review prompts, exact-reference navigation, source
records with separate uses, full nested histories and a complete copyable snapshot.
It is a **review interface**, not an authored scientific report, editable document,
researcher recommendation or approval workflow.

## Try the complete synthetic flow

```sh
python synthetic_walkthrough.py ../persona-html-demo --candidate-source offline-import --research-journey --recheck-sources --review-method-use --import-method-use --html-review
```

This runs **39 actual CLI stages** with invented source files and fixed synthetic
proposal/review decisions. After a successful exit and `COMPLETE.json`, open
`research-journey.html` yourself in a browser. Nothing opens automatically. Both
pattern and application proposal histories, original/reviewed rationales, rejected
alternatives and all-deferred answer claims remain visible. Source matches still
do not validate method applicability. The complete JSON snapshot inside the HTML
matches `research-journey.json` for this unchanged synthetic run.

`--html-review` requires `--research-journey` and adds one stage to any existing
extended mode. All prior modes retain their stage counts and behavior. An HTML
stage failure leaves diagnostics and earlier artifacts, but no completion marker.
The runner takes no external candidate/review input and offers no general automatic
acceptance policy. Every standalone production review still requires explicit input.

## Render your explicitly supplied artifacts

Use the existing [research journey](RESEARCH_JOURNEY.md) inputs and options:

```sh
python research_journey.py package.json patterns.json context.json links.json design.json answer.json argument.json publication-relations.json --pattern-id selected-pattern --review answer-review.json --format html > research-journey.html
```

Optional `--method-applications reviewed-applications.json` retains imported method
application history. Optional `--source-selection selected-sources.json --source-root
../authorized-sources` performs the same separate current source check as the JSON
and text modes. Both source options are required together.

The HTML renderer calls the complete inspector **once per invocation**, then formats
that detached result. It does not call the text renderer, rerun subreports, or read
source files a second time. Separate JSON, text and HTML CLI invocations each perform
their own requested source checks. Opening the file later does not recheck anything.
No arbitrary cached report is accepted as validated input. Invalid/stale artifacts
fail before rendering; invalid application envelopes fail before source reads.

CLI output is stdout only. Use a new private output path: shell redirection can
replace an existing file even when the application itself never writes inputs.
No browser, local server, account or third-party Python package is required to
create the view. Supported CLI platforms remain Python 3.10+ on Linux and Windows.

## Reading order and boundaries

1. **Verification scope:** separates current local byte/quote consistency from
   recorded historical labels. Without explicit source options it prominently
   says no source reread was performed. A byte/quote match does not establish source
   authenticity, semantic support, independence or rights clearance.
2. **Review prompts:** native disclosure groups by domain, without severity scores
   or recommendations. Counts are navigation aids only. No detected prompts still
   requires human/scientific review; the list is not exhaustive.
3. **Exact-reference route index:** links to deterministic SHA-256 anchors. Parent
   observations and reasoning components remain distinct. A shared reference connects
   records, not meanings. Active use means a supplied answer citation/design use,
   including a rejected or deferred claim, never accepted evidence.
4. **Source records:** keeps the stored excerpt, locator, source attribution,
   enclosing condition/limitation, selected component, recorded/current checks and
   all separate source/pattern/context/answer/design/application/argument uses.
5. **Full review histories:** expandable complete fields preserve original, reviewed,
   rejected and deferred proposals and operator declarations. A history reference
   outside the route index stays visible but does not create a new route or active use.
   Unused-source quote gaps remain in the agenda and source report.
6. **Exact structured snapshot:** escaped, copyable JSON retains every inspected
   field, including data not highlighted in the view. `journey_input_sha256` binds
   supplied artifacts; a separate snapshot hash binds the inspected JSON result,
   not HTML presentation bytes. Neither is a signature or authenticated history.

Human review, source meaning and researcher fidelity remain unverified. Required
checks are proposed, not executed. Candidate acceptance, application consideration,
context judgments and answer decisions keep their separate meanings. Viewing,
expanding, copying, printing or editing the browser DOM cannot change a review
artifact, execute a plan, update a canonical persona or approve research.

## Passive rendering and privacy

The file contains fixed CSS and escaped data only. It has no JavaScript, forms,
buttons, embedded media, external assets, network URLs as links, editable controls
or auto-saving. All links are internal fragments. Native `details` disclosures do
not run application code. A restrictive Content Security Policy denies resources,
scripts, frames, form actions and base-URL changes. Its stylesheet hash permits only the exact fixed inline
stylesheet, without a general unsafe-inline allowance. No source/model/operator string becomes markup, a style, an ID or an
external URL. Control and directional-format characters are shown as escapes in
reader-facing text; the complete JSON uses reversible JSON escaping.

These controls limit active page behavior; they do not authenticate the source
text or make it safe to publish. The file may contain private quotations, source
filenames and annotations. It is not anonymized. Keep it local and apply the same
sharing permissions as the original artifacts. Browser extensions or manual editing
are outside this renderer's control.

The final UTF-8 HTML, after escaping and retained histories, is capped at 16 MiB.
Existing upstream 8 MiB input and 16 MiB inspected-report bounds still apply. HTML
expansion can exceed the output bound even when JSON fits; narrow the review
explicitly rather than relying on truncation. Failures produce no partial stdout.

## Verification status

Synthetic automated tests cover injection strings, passive element/attribute
allowlists, fragment targets, unique deterministic IDs, exact JSON snapshot/hash,
control/Unicode handling, original/reviewed/rejected and imported-observation
history, stale/unauthorized inputs, source-read ordering, one-inspection behavior,
unused-source gaps, final-byte budgets, strict CLI errors and unchanged legacy JSON
and text. The full synthetic demonstration exercises the HTML CLI and late failure.

**Actual-browser visual, keyboard and print QA is not verified in the current
cloud environment.** Installed Chromium cannot start because OS socket creation
is denied, including an approved expanded execution attempt. Static parsing does
not establish responsive geometry, focus behavior or print layout. Responsive and
print styles are included, but inspect the view and print preview in an authorized
browser before relying on those presentation behaviors. No browser dependency was
added to the runtime or CI to hide this limitation.

## Reopen explicitly pinned inputs

[Journey input cards](JOURNEY_INPUTS.md) bind the exact relative JSON file choices,
raw bytes and logical payloads so a later inspection needs only the card and an
explicit input root. Any artifact change fails rather than refreshing hashes or
migrating decisions. A selected live-source check still requires an explicit source
root on every command. Text/JSON/HTML retain the same review semantics, with an added
per-file consistency record. The browser presentation verification limit remains
unchanged; this is a local input convenience, not approval or source authority.

The optional synthetic `--import-answers` mode also displays the complete answer
proposal/adoption history, alongside pattern and method-application history. With
all extensions the runner executes 46 CLI stages. This changes no browser QA
claim: parsing, escaping and exact JSON snapshots are not visual/keyboard/print
verification. No browser retry or restriction bypass is performed.
