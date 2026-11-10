# Save CLI results without shell redirection

The stdout-result commands listed in COMMANDS support `--output NEW_FILE`.
The file contains exactly the UTF-8 result bytes the same execution would have sent
to stdout, including its final LF. JSON escaping and payload schemas are unchanged.
No shell decoding, BOM insertion or newline translation is involved. Without the
flag, existing stdout behaviour and command-specific bounds remain unchanged.

## Fictional local example

Create an empty directory outside the repository and replace `OUTPUT` with that
path. These commands use only bundled synthetic examples and produce new files:

```sh
python research_workflow.py examples/observed-corpus.json --question "Fictional comparison" --topic "model design" --output OUTPUT/package-result.json
python journey_inputs.py template --output OUTPUT/input-selection.json
```

The template records no selected files and is not a completed input card. Fill it
explicitly before `journey_inputs.py prepare`; a saved preparation card can then be
passed directly to `journey_inputs.py inspect --output NEW_FILE`. Existing JSON,
text and HTML format flags select the file content, not the receipt format.

## Receipt and boundaries

Stdout contains only an ASCII-safe JSON `persona.saved-output.v1` receipt: `status`
(`SAVED`), absolute `path`, `bytes`, raw `sha256`, `payload_sha256`, and `boundary`.
The payload hash uses the existing sorted-key compact UTF-8 JSON convention when
the bytes decode as strict JSON; text and HTML use null. Hashes bind bytes/values,
not authenticity, rights, scientific validity, approval or permission to share.
The receipt exposes the destination path but does not repeat document contents.
Both the document and its path may be private. No model, network, canonical update,
or publication occurs. JSON field order can vary between processes for some
existing builders; raw hashes identify the exact saved bytes, not a canonical file.

A supplied output path is checked before reading command inputs, then checked again
before binary exclusive creation (`xb`). Existing files/directories, dangling links,
symlink path components, repository paths and missing parents are refused. Parent
directories are never created. Choosing an existing output cannot overwrite it,
even if another writer creates that file between the final check and open.

The parent directory and ancestors must remain trusted and stable while the command
runs. This is not protection against an attacker swapping ancestor directories or
Windows junction/reparse points concurrently. Symlink components also mean that
macOS paths through `/var` may be refused; choose an explicit real directory instead.
Native macOS is not in the CI matrix.

Saved files are bounded to 16 MiB, with any tighter existing command limit retained.
Receipts are bounded to 64 KiB before writing. Files are not staged atomically: a
write or close failure can leave a partial output, which is never deleted. Failure
emits no success receipt. A later stdout delivery failure can occur after the file
has been saved; inspect the existing file rather than retrying to the same path.
No durability guarantee beyond normal file close is made.

## Coverage and exceptions

All 40 previously stdout-only result CLIs now accept the option on their result
modes. `human_validation.py check/status` also accept it; `template` keeps its
required output and original template receipt, using the same exclusive writer.
`revise_local.py apply`, `review_workspace.py`, and `synthetic_walkthrough.py` retain
their existing directory writers. Validators (`persona.py`, `safe_canonical_read.py`,
`verify_manifest.py`, `audit_publication.py`) and the dispatcher retain their existing
contracts. There is no `--version` addition or packaging/license decision here.
Existing guide shell blocks remain unchanged; shell redirection can still overwrite
files and re-encode output. Prefer the explicit option where available.
