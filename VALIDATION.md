# Validation record

Current release: `0.71-documentation-restructure`, 2026-11-08. This file is the current
verification snapshot. Every earlier dated entry is preserved verbatim, in its original
order, in [docs/VALIDATION_HISTORY.md](docs/VALIDATION_HISTORY.md), which also receives
the full entry for each new release.

## Latest change

- 2026-11-08 Documentation restructure (`0.71-documentation-restructure`): README reduced to
  a one-screen overview; the per-feature narrative moved verbatim to `docs/WORKFLOWS.md`, the
  command tables to `docs/COMMANDS.md`, a Korean guide added as `docs/README.ko.md`, and the
  validation record split into this snapshot and `docs/VALIDATION_HISTORY.md`. No Python
  module, test, fixture or example changed. Full entry:
  [docs/VALIDATION_HISTORY.md](docs/VALIDATION_HISTORY.md#2026-11-08-documentation-restructure-071-documentation-restructure).

## What CI runs

`.github/workflows/tests.yml` runs on every push to `main` (and to the
`codex/core-workflows-20261103` branch) and on every pull request, with a matrix of
`ubuntu-latest` and `windows-latest` under Python 3.10 and 3.12: four jobs,
`fail-fast: false`, 15-minute job timeout. Each job runs, in order:

1. `python -m unittest discover -v`
2. `python audit_publication.py`
3. `python verify_manifest.py`

Actions are pinned to commit hashes, the token permission is `contents: read`, checkout
does not persist credentials, and no secrets or deployment steps are used. The manifest
describes LF-normalized published files, enforced by `.gitattributes`. CI does not evaluate
external model/search behaviour or scientific meaning.

## Verify locally

From the repository root, with Python 3.10 or later and no third-party packages:

- `python -m unittest discover -q` — the current tree runs 980 synthetic tests
  (3 platform-conditional skips in `test_journey_inputs`: the FIFO and Unix-unlink
  cases). The 2026-11-08 local run passed in 695.315 seconds. On restricted Windows
  hosts, set `TEMP` and `TMP` to an authorized writable directory first.
- `python verify_manifest.py` — expects `{"valid": true, "errors": []}` for the 229
  listed files. Regenerate the manifest after every other edit of a release.
- `python audit_publication.py` — expects `"pass": true`; the current tree has 230 text
  files including the manifest. A pass is a limited file-type and secret-pattern scan, not
  proof of anonymity or rights clearance.
- `python -m compileall -q .` — 140 Python files compile cleanly.
- `python synthetic_walkthrough.py ../persona-synthetic-demo` — the 15-stage demo must exit 0
  and write `COMPLETE.json` into a new directory outside the repository.

## What this record does not claim

Only synthetic inputs are used. Passing tests establish the mechanical behaviour of the
generic code and fixtures: exact bindings, rejections, bounded outputs and documented
command blocks. They do not establish scientific validity, fidelity to any real
researcher, source authenticity, rights clearance, human review or model behaviour; no
model call, network access or real researcher data is involved. Local pass statements do
not establish remote CI results; the GitHub Actions history for the exact commit does.
Actual-browser visual, keyboard and print QA of the static HTML view remains
**BLOCKED/unverified**, as recorded in the history.
