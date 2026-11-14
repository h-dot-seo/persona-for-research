# Public extraction record

Release scope: framework concepts and executable generic code only.

Included by explicit allowlist: documentation, source code, synthetic examples,
tests, empty record templates, agent instructions and publication checks.
Excluded: source corpora, actual conversations, person-specific persona packages,
research/experimental databases, project evidence tables, real validation results,
books/articles/figures, private configurations, profiles, cookies, keys, logs,
authentication bundles, backups, and all private Git history/LFS objects.

No claim is made that a real persona or scientific project was validated by this
release. Runtime test results concern only the generic code and synthetic fixtures.
See README for implemented versus specified behavior and known integration limits.

The manifest binds this release's file bytes and exact case-sensitive file inventory.
Unlisted files are rejected, never automatically added to the allowlist. The manifest
excludes itself to avoid a recursive hash dependency. Only root `.git` metadata and
`.pyc` bytecode files beneath `__pycache__` directories are ignored as nonpublication
metadata. Other cache contents, hidden files, symlink files/directories and noncanonical
portable paths are rejected. Ignored metadata must not be included in release payloads.

A source hash identifies supplied bytes; it does not authenticate a publication or
establish scholarly support, personal consent or redistribution rights. Exact inventory
and pattern scanning do not replace manual selection, rights or sensitive-content review.


## Inspect another tree without executing its code

Use the scripts from a checkout you trust and explicitly select an existing directory:

```text
python /trusted/persona/verify_manifest.py /selected/unpacked-tree
python /trusted/persona/audit_publication.py /selected/unpacked-tree
```

The selected tree is read as data; its scripts and modules are not imported or executed.
Without ROOT, both commands still inspect the directory containing their own script,
not the working directory. JSON output and normal check exit codes remain unchanged:
0 for passing, 1 for reported check failures. Missing/non-directory ROOT and malformed
arguments exit 2 with a usage diagnostic; --help does not inspect any tree. No files are
written, targets are not repaired, and the two checks remain separate.

A manifest check proves only internal agreement with the selected tree's own declared
inventory and bytes, not authenticity or a signature. Audit is a limited pattern/type
scan, not rights clearance, anonymity or publication approval. Existing symlink/path
checks are unchanged; this is not a hostile-filesystem sandbox or a new resource/time
bound. Filenames and existing diagnostics may contain private information. No claim
is made about untested tag/archive byte equivalence.


## Regenerate an explicit file inventory

Run the generator from a trusted checkout, with an explicit release and calendar date.
`--release` accepts a dotted numeric version (two or three numeric components) and an
optional lowercase hyphen-separated suffix. `--date` must be an actual YYYY-MM-DD date.
For example (replace the illustrative paths with your selected tree and a new external file):

```text
python /trusted/persona/regenerate_manifest.py /selected/tree --release 0.92-manifest-regeneration --date 2026-11-14 --output /outside/new-manifest.json
```

The generator copies existing declaration fields and key order, sorts file rows by POSIX
path, and hashes raw file bytes. It does not normalize line endings: CR-containing selected
files are rejected. Existing files are rehashed, never silently added or removed. Repeat
`--add PATH` for each newly selected file and `--remove PATH` for each deleted file. A
removed file still present in the tree is unlisted and therefore rejected. Unnamed extras,
missing listed files, symlinks, unsafe paths, invalid metadata or duplicate selections fail
before output creation. Both the candidate manifest (including preserved metadata) and the
selected tree undergo the existing publication pattern scan; this does not replace human
review. No license/flag/project change option is provided.

The new UTF-8 JSON file uses indent=2, escaped JSON text and a final LF. The original
manifest is unchanged. Output must be a new file outside both trees with an existing parent
and no symlink components. Exclusive text creation prevents ordinary overwrites. The JSON
stdout summary lists added, removed, rehashed and changed relative paths and a boundary;
paths and file names may themselves be private. Do not redirect stdout over the original
manifest: the shell can truncate it before the generator reads it. Review the generated file,
then replace the committed manifest yourself and run the trusted verify and audit commands.
The generator never performs that replacement, commits, tags, changes permissions or publishes.

Source bytes, inventory and original manifest are rechecked before creation. This is not an
atomic filesystem snapshot or protection against all concurrent/hostile path replacements.
No new file-size, runtime or memory bound is claimed for inventory files. Write failure may
leave a partial new output; it is not removed. Hash agreement is not authenticity, rights
clearance, anonymity or release approval. Audit and human review remain separate gates.
