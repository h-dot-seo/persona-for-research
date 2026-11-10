# Validation record

Current release: `0.75-utf8-cli-output`, 2026-11-10. This file is the current
verification snapshot. Every earlier dated entry is preserved verbatim, in its original
order, in [docs/VALIDATION_HISTORY.md](docs/VALIDATION_HISTORY.md), which also receives
the full entry for each new release.

## Latest change

- 2026-11-10 UTF-8 CLI output (`0.75-utf8-cli-output`): ten formerly print-based
  JSON result CLIs write UTF-8/LF bytes directly. Windows result stdout intentionally
  changes from text-mode CRLF and the configured encoding (often an ANSI code page)
  to LF and UTF-8. Existing UTF-8/LF POSIX bytes, JSON escaping and bindings stay the
  same; shell re-encoding and overwrite risks remain.
  Full entry: [docs/VALIDATION_HISTORY.md](docs/VALIDATION_HISTORY.md#2026-11-10-utf-8-cli-output-075-utf8-cli-output).

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

- `python -m unittest discover -q` — the current tree runs 1013 synthetic tests
  (platform-specific cases may skip on other hosts). The 2026-11-10 Python 3.12.14
  local run passed in 339.848 seconds with no failures, errors or skips. One module runs as
  `python -m unittest tests.test_<name> -v`. On restricted Windows hosts, set `TEMP` and
  `TMP` to an authorized writable directory first.
- `python verify_manifest.py` — expects `{"valid": true, "errors": []}` for the 237
  listed files. Regenerate the manifest after every other edit of a release.
- `python audit_publication.py` — expects `"pass": true`; the current tree has 238 text
  files including the manifest. A pass is a limited file-type and secret-pattern scan, not
  proof of anonymity or rights clearance.
- `python -m compileall -q .` — 148 Python files compile cleanly and parse with
  Python 3.10 grammar.
- `python synthetic_walkthrough.py ../persona-synthetic-demo` — the 15-stage demo must exit 0
  and write `COMPLETE.json` into a new directory outside the repository.
- `python persona_cli.py list` — prints the 47 root scripts that have a command-line entry
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
flat root files (six of them resolve the repository root from their own `__file__`), and a
dispatcher listing is not an approval of any script's inputs.
Actual-browser visual, keyboard and print QA of the static HTML view remains
**BLOCKED/unverified**, as recorded in the history.
