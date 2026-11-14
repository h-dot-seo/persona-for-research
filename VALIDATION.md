# Validation record

Current release: `0.99-route-tables`, 2026-11-14. This file is the current
verification snapshot. Every earlier dated entry is preserved verbatim, in its original
order, in [docs/VALIDATION_HISTORY.md](docs/VALIDATION_HISTORY.md), which also receives
the full entry for each new release.

## Latest change

- 2026-11-14 Bound evidence route tables (`0.99-route-tables`): exact evidence/use JSON and separate route roles as private CSV/TSV, with four pinned-option column contracts.

- 2026-11-14 Bound journey agenda tables (`0.98-agenda-tables`): fresh pinned-input review agendas as private CSV/TSV without cached reports or automatic approval.

- 2026-11-14 Reference catalog tables (`0.97-reference-tables`): fresh checked package references in private bounded CSV/TSV, without cached report input or spreadsheet decisions.

- 2026-11-14 Fixed-column RIS census (`0.96-ris-census`): explicit supplied RIS occurrence listing using a byte-identical parser snapshot, with old CSL selection semantics retained.

- 2026-11-14 Bound package overview (`0.95-package-overview`): passive whole-package JSON/HTML inspection, declarations and detached summaries only; no source reread or recommendation.

- 2026-11-14 Supplied CSL census (`0.94-csl-census`): exact-fact occurrence listing and explicitly selected unapproved skeleton, without identity/kind derivation or transmission.

- 2026-11-14 Release change index (`0.93-change-index`): concise command/behavior history from 0.69, linked to unchanged verification entries, with static drift checks.

- 2026-11-14 Explicit public inventory regeneration (`0.92-manifest-regeneration`): raw-byte rehash, explicit add/remove, audited metadata and exclusive external candidate output; no automatic replacement or approval.

- 2026-11-14 Main and PR CI (`0.91-main-pr-ci`): retire the old development-branch push trigger; preserve all four read-only test jobs.

- 2026-11-14 Trusted publication checks on selected ROOT (`0.90-selected-publication-root`): optional target directory without executing target code; default output preserved.

- 2026-11-14 Per-file local source bound (`0.89-source-file-bound`): 8 MiB per selected source, existing aggregate budgets preserved, no new corpus-total default.

- 2026-11-14 Shared private readers (`0.88-shared-private-readers`): eleven thin wrappers reuse bounded bytes, preserving limits, exact size errors, collective accounting and UTF-8-first journey parsing.

- 2026-11-14 Shared bounded JSON reads (`0.87-bounded-json`): limit reads before parsing, preserve combined budgets and original-byte hashes.

- 2026-11-14 Bounded trusted command catalog (`0.86-command-catalog`): aggregate actual help with shared time/output budgets and explicit partial states.

- 2026-11-14 Selected command descriptions (`0.85-command-description`): actual bounded help for trusted explicit sources; no argparse-free check execution.

- 2026-11-14 Machine-readable command list (`0.84-command-list`): bounded AST-derived JSON names/descriptions; no discovered script import or execution.

- 2026-11-14 Supplied release decisions (`0.83-release-decision`): explicit human record references, missing-axis reports and optional reviews; no tool approval.

- 2026-11-14 Detached reopening declarations (`0.82-reopening-record`): prior impact and revalidation plans; read-only candidate prompts, no release decision.

- 2026-11-13 Detached pre-holdout candidate findings (`0.81-candidate-challenge`): neutral templates, strict bound records, counts-only review, no approval.

- 2026-11-13 Optional read-only package-review split summary (`0.80-split-review`).
  Default output, canonical payload and source-intake behavior remain unchanged.

- 2026-11-13 Detached split declaration (`0.79-split-declaration`): private census/split
  template, sorted/hash-bound freeze and exact package training comparison. Counts/hashes
  omit withheld IDs except conflicts already in the supplied package. No intake gate,
  payload schema change or unseen-holdout claim. Full entry: [docs/VALIDATION_HISTORY.md](docs/VALIDATION_HISTORY.md#2026-11-13-detached-split-declaration-079-split-declaration).

## What CI runs

`.github/workflows/tests.yml` runs on every push to `main` and on every pull request,
with a matrix of
`ubuntu-latest` and `windows-latest` under Python 3.10 and 3.12: four jobs,
`fail-fast: false`, 15-minute job timeout. Each job runs, in order:

1. `python -m unittest discover -v` (discovery from the repository root loads the `tests/`
   package, so the command did not change with the layout)
2. `python audit_publication.py`
3. `python verify_manifest.py`

Actions are pinned to commit hashes, the token permission is `contents: read`, checkout
does not persist credentials, and no secrets or deployment steps are used. The manifest
describes LF-normalized published files, enforced by `.gitattributes`. CI does not evaluate
external model/search behaviour or scientific meaning.

Development branches are temporary PR workspaces: open or update a PR to run CI
on their changes. A branch push without a PR does not trigger this workflow.
The retired historical development branch has no special trigger. No branches are
deleted automatically by this workflow. Tag naming remains undecided; no tag
trigger or release-publishing step is configured.

## Verify locally

From the repository root, with Python 3.10 or later and no third-party packages:

- `python -m unittest discover -q` — the current tree runs 1311 synthetic tests
  (platform-specific cases may skip on other hosts). The final local verification result is recorded in the release history. One module runs as
  `python -m unittest tests.test_<name> -v`. On restricted Windows hosts, set `TEMP` and
  `TMP` to an authorized writable directory first.
- `python verify_manifest.py` — expects `{"valid": true, "errors": []}` for the 299
  listed files. Regenerate the manifest after every other edit of a release using
  `python regenerate_manifest.py --release REL --date YYYY-MM-DD --output ../NEW.json`,
  explicitly naming new/deleted paths with --add/--remove. Review the external candidate
  before manually replacing the original manifest; see PUBLICATION.md.
- `python audit_publication.py` — expects `"pass": true`; the current tree has 300 text
  files including the manifest. A pass is a limited file-type and secret-pattern scan, not
  proof of anonymity or rights clearance.
- `python -m compileall -q .` — 177 Python files compile cleanly and parse with
  Python 3.10 grammar.
- `python synthetic_walkthrough.py ../persona-synthetic-demo` — the 15-stage demo must exit 0
  and write `COMPLETE.json` into a new directory outside the repository.
- `python persona_cli.py --version` — shows unauthenticated manifest labels and Python
  version only; it does not check hashes. Use `verify_manifest.py` separately.
- `python persona_cli.py list` — prints the 54 root scripts that have a command-line entry
  point, one line each; `python persona_cli.py run verify_manifest.py` prints exactly what
  `python verify_manifest.py` prints and exits with the same code.

## What this record does not claim

Only synthetic inputs are used. Passing tests establish the mechanical behaviour of the
generic code and fixtures: exact bindings, rejections, bounded outputs and documented
command blocks. They do not establish scientific validity, fidelity to any real
researcher, source authenticity, rights clearance, human review or model behaviour; no
model call, network access or real researcher data is involved. Local pass statements do
not establish remote CI results; the GitHub Actions history for the exact commit does.
The `tests/` package and the dispatcher are a layout change and a discovery aid: no
documented command, fixture binding or behaviour changed, the implementation modules remain
flat root files (seven of them resolve the repository root from their own `__file__`), and a
dispatcher listing is not an approval of any script's inputs.
Actual-browser visual, keyboard and print QA of the static HTML view remains
**BLOCKED/unverified**, as recorded in the history.
