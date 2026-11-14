# Private folder byte inventory

Use `folder_inventory.py declare` before handing over or archiving a review folder,
then `verify` to detect later edits, missing files or additional files. Review
workspaces are meant to be edited: differences are not scientific judgments.
This tool does not validate a persona, content bindings, permissions or completion.
Enumeration is not selection or authorization. `READY.json`, `COMPLETE.json`,
`commands.json` and next-command files are ordinary bytes, never instructions.
Commands are not executed; argv and file contents are not copied into the inventory.

## Synthetic example

Start with an existing external OUTPUT directory. These commands create only
synthetic artifacts. The inventory must be **outside both the repository and the
inventoried folder**; keep it or its hash separately. Never publish private filenames.

```sh
python synthetic_walkthrough.py OUTPUT/demo
python folder_inventory.py declare OUTPUT/demo --output OUTPUT/inventory.json
python folder_inventory.py verify OUTPUT/inventory.json --root OUTPUT/demo
python folder_inventory.py verify OUTPUT/inventory.json --root OUTPUT/demo --format text --output OUTPUT/check.txt
```

A successful declare prints the standard saved-output receipt, not the inventory.
Verify prints JSON by default, or plain text with `--format text`; `--output` saves
exclusively and prints a receipt. A mismatch still writes the report and exits 1.
Malformed input, unsafe trees or exceeded limits exit 1 without report stdout.
Existing destinations are never overwritten, parents must already exist, and
symlink/reparse path components are rejected. An I/O failure may leave a partial
output file; it is not removed or evidence of success.

## Format and limits

The `persona.folder-inventory.v1` declaration has `schema`,
`status: DECLARED_INVENTORY_NOT_APPROVAL`,
`input_root: EXPLICIT_CURRENT_ARGUMENT_NOT_PERSISTED`, `files`, `boundary`, and
fixed `llm_used: false`, `commands_executed: false`,
`content_bindings_verified: NOT_PERFORMED`. Each sorted file row contains exactly
`path` (relative path under the lexical restrictions below), `bytes` (nonnegative integer), and `sha256`
(lowercase raw-byte SHA-256). No clock, absolute root, contents or implementation
hash is persisted. Empty directories are not inventoried. CRLF and LF are different
bytes. Unchanged trees produce identical serialized declarations.

Limits: 4096 regular files, 256 MiB aggregate raw file bytes, 1024 characters per
relative path (Unicode code points), 4096 directories including the root, and 16 MiB for **both declaration input and report output**, so a
produced declaration can be verified without a smaller input ceiling. Reads use
the remaining aggregate budget. The directory cap also bounds empty-tree traversal.
This is not streaming hashing: one file is read into memory at a time, potentially
up to 256 MiB (plus a one-byte overflow probe). No silent truncation or exclusions are performed.
Symlinks (including dangling links), Windows reparse points/junctions and special
files fail closed. `.git`, `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`,
`.pyc` and `.pyo` entries are rejected, not silently omitted. Paths reject traversal,
noncanonical spelling, backslashes, colons and Unicode Cc/Cf/Cs/Zl/Zp characters.
These lexical checks do not guarantee copying to every operating system: Windows
reserved names, trailing dots, other forbidden characters and case-insensitive name
collisions are not comprehensively validated. Verification compares the explicit
current filesystem; it does not normalize names or establish cross-OS equivalence.

Verification validates the exact schema, fixed metadata, sorted unique paths and
size/hash types, then compares current bytes. It returns `valid`, `errors`, and
sorted `missing`, `unlisted`, `changed` lists. Errors use `PATH: missing`,
`PATH: size/hash mismatch`, or `PATH: unlisted file`. Status is
`DECLARED_INVENTORY_MATCH_NOT_APPROVAL` or
`DECLARED_INVENTORY_MISMATCH_NOT_APPROVAL`; the same boundary/negative claims remain.

This is not a signature or authenticated receipt. A person able to replace both
folder and declaration can conceal changes. Keep the original declaration or its
hash separately. File identity/read checks and a second enumeration detect some
concurrent changes, but do not provide an atomic snapshot or guarantee defense
against a hostile filesystem racing every check. Use a quiescent folder.
Use `journey_inputs.py` and `persona.py` for their separate content-binding checks.
Shared declare/verify vocabulary is maintenance consistency, not equivalence to
other repositories' validation or recovery tools.
