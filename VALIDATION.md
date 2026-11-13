# Validation record

Current release: `0.80-split-review`, 2026-11-13. This file is the current
verification snapshot. Every earlier dated entry is preserved verbatim, in its original
order, in [docs/VALIDATION_HISTORY.md](docs/VALIDATION_HISTORY.md), which also receives
the full entry for each new release.

## Latest change

- 2026-11-13 Optional read-only package-review split summary (`0.80-split-review`).
  Default output, canonical payload and source-intake behavior remain unchanged.

- 2026-11-13 Detached split declaration (`0.79-split-declaration`): private census/split
  template, sorted/hash-bound freeze and exact package training comparison. Counts/hashes
  omit withheld IDs except conflicts already in the supplied package. No intake gate,
  payload schema change or unseen-holdout claim. Full entry: [docs/VALIDATION_HISTORY.md](docs/VALIDATION_HISTORY.md#2026-11-13-detached-split-declaration-079-split-declaration).

## What CI runs

`.github/workflows/tests.yml` runs on every push to `main` (and to the
`codex/core-workflows-20261103` branch) and on every pull request, with a matrix of
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

## Verify locally

From the repository root, with Python 3.10 or later and no third-party packages:

- `python -m unittest discover -q` — the current tree runs 1076 synthetic tests
  (platform-specific cases may skip on other hosts). The final local verification result is recorded in the release history. One module runs as
  `python -m unittest tests.test_<name> -v`. On restricted Windows hosts, set `TEMP` and
  `TMP` to an authorized writable directory first.
- `python verify_manifest.py` — expects `{"valid": true, "errors": []}` for the 261
  listed files. Regenerate the manifest after every other edit of a release.
- `python audit_publication.py` — expects `"pass": true`; the current tree has 262 text
  files including the manifest. A pass is a limited file-type and secret-pattern scan, not
  proof of anonymity or rights clearance.
- `python -m compileall -q .` — 155 Python files compile cleanly and parse with
  Python 3.10 grammar.
- `python synthetic_walkthrough.py ../persona-synthetic-demo` — the 15-stage demo must exit 0
  and write `COMPLETE.json` into a new directory outside the repository.
- `python persona_cli.py --version` — shows unauthenticated manifest labels and Python
  version only; it does not check hashes. Use `verify_manifest.py` separately.
- `python persona_cli.py list` — prints the 48 root scripts that have a command-line entry
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
