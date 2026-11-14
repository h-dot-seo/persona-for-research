# Prepare an explicitly selected local source

The existing local loader requires a byte hash and exact section locators before
curated observations can be checked. `prepare_local_manifest.py` removes that
manual hashing/heading-discovery step. It does not extract scholarly claims,
collect articles, parse PDFs or call an external metadata/model service.

Use only local files you are authorized to read and process. The supplied selection
must explicitly declare author identity, publication kind/year, intended topic,
training split and permission. These fields are not inferred from filenames or
headers and are not authenticated by this tool. The optional [CSL-JSON/RIS census](CENSUS_IMPORT.md)
copies year and locator from an export; the operator must confirm these pre-filled
values. It does not derive kind, identity, permission, topic or split.

## Start with the bundled synthetic selection

Choose an existing private scratch directory outside the repository and use a
UTF-8-capable shell. Redirection can overwrite an existing file, so choose a new
filename and check exit status before opening it:

```
python prepare_local_manifest.py examples/local-selection.json --source-root examples/synthetic-sources > ../prepared-local.json
```

The output is the **existing corpus manifest format**, with byte hashes filled and
per-paper `input_inventory` annotations. No new corpus schema or wrapper is required.
Each paper still has `observations: []`. The inventory contains only:

- Raw source byte count and the existing paper-level raw-byte SHA256.
- Exact section heading/locator, normalized text character count and text hash.
- An explicit no-observations/no-LLM status and scope warning.

No section body or quote is copied to the output. Headings, paths and hashes can
still be private; this is not anonymization or permission to publish the manifest.
Empty observations mean no modeled evidence, not a successful scholarly extraction.

## Curate, then use the existing loader

Inspect the source yourself and add explicit observations under each appropriate
paper. An observation needs method, condition, limitation, exact section locator,
topic, selected evidence quote and a claim type (`explicit_statement` or
`operator_interpretation`). Attribution remains a separate scientific judgment.
For this **synthetic demo only**, the observations in `examples/file-corpus.json`
correspond to the same bundled files and can be copied into the prepared manifest.
Do not transfer those invented observations to real documents.

Then run the unchanged loader interface:

```
python corpus_files.py ../prepared-local.json --source-root examples/synthetic-sources --question "Which synthetic explanation?" --topic "model design"
```

It rereads the selected bytes, checks the prepared hash, verifies supplied quotations
at their exact locators and builds the bound runtime package. `input_inventory` is
removed by the existing runtime projection: it is not a reasoning record or author
claim. Unquoted source bodies are not added to the runtime package.

## Selecting your own authorized local files

Use the same fields as `examples/local-selection.json`. Every paper must have
`observations: []`; `source_sha256` may be omitted for a new selection. The tool
accepts only explicitly listed `.md`/`.txt` files inside the chosen source root,
not a directory scan or a URL. Paths must be portable relative paths, without
absolute roots, `..`, backslashes or drive prefixes. Resolved paths that escape
the root, including symlink escapes, are rejected. Existing loader path policy is
shared rather than duplicated.

Text must be UTF-8 with unique nonempty `## ` headings. The existing section parser
uses `splitlines()` and joins section lines with LF; a section text hash is therefore
**not the raw file hash**. CRLF/LF changes alter raw-byte identity even if normalized
section content stays the same. Section character counts are Unicode code points.
Plain text without those headings, duplicate headings, invalid UTF-8 and unsupported
file types fail. Do not assume a `.txt` suffix means arbitrary text is supported.

No DOI resolution, author disambiguation, PDF conversion, OCR, publication lookup,
rights checking or full-text download is performed. Prepare only authorized local
material in the documented format; do not copy protected full texts into this public
repository to make the example work.

## Holdout, change and failure boundaries

The **entire selected corpus** must be author-matched, authorized, runtime-eligible
training evidence. A holdout, comparator, unauthorized or cross-author entry rejects
before filesystem resolution or any source-byte read, even if an earlier entry is
valid. All listed path checks finish before any source bytes are read. Unlisted
files are not read or enumerated. Keep holdout sources in a separate workflow.

The shared reader pins a regular file descriptor, checks resolved path and file
identity before reading, uses no-follow opening where supported, and rejects detected
size/timestamp changes during the read. A simple symlink replacement after preflight
is rejected before body reading. Each selected paper entry is read into one byte
snapshot for its hash and inventory;
this is not an atomic snapshot across multiple files or entries, nor protection
against a hostile concurrent filesystem modifier. Keep selected sources stable.
A supplied `source_sha256` must already match: preparation cannot silently update a
stale hash. Re-preparing a manifest with curated observations is also rejected so
old observations cannot be rebound to new bytes by this convenience command.
For an intentional source revision, create a new empty selection, preserve the old
record, then curate/review the new evidence explicitly.

The tool writes only its stdout. On failure no result JSON is emitted, but shell
redirection may leave an empty file. It never rewrites source files, assigns a
publication identity, authenticates consent or creates a verification receipt for
scientific meaning. Actual local-byte/quote checks still happen in `corpus_files.py`.

Synthetic regression and real CLI round-trip:

```
python -m unittest tests.test_prepare_local_manifest -v
```

Instead of editing the entire prepared manifest, use the
[manual observation cards](MANUAL_LOCAL_OBSERVATIONS.md) to append one explicitly
written observation at a time, with a runnable research/review synthetic journey.

## Bring your own text: report before preparing

Any external converter is acceptable if its output meets the UTF-8 Markdown contract
above. This tool never converts PDF, DOCX or HTML; extraction remains your own step.
Keep converted files outside this repository. Closing `##` and converter `{#id}`
attributes remain literal parts of locators. Re-converting changes bytes: preserve the
old record and follow the intentional-revision route, not hash replacement.

Run the read-only report on the bundled synthetic selection:

```sh
python prepare_local_manifest.py examples/local-selection.json --source-root examples/synthetic-sources --report-defects
```

Capture stdout to a new file in an external OUTPUT directory if desired. Exit 0 means
that the report completed, not that every source parses or that evidence is valid.
The report has schema `persona.source-structure-report.v1`, not a usable manifest.
`ALL_SELECTED_FILES_WOULD_PARSE` or `SOME_SELECTED_FILES_WOULD_NOT_PARSE` summarizes the
unchanged parser outcomes (`WOULD_SUCCEED`, `WOULD_RAISE`, `INVALID_UTF8`). The exact
parser error is included for structural failures. Informational findings such as empty
sections and whitespace trimming do not themselves imply a parser failure.

Each decoded source reports exact headings, 1-based `splitlines()` line numbers,
normalized section character counts, and capped findings. Near-miss headings, a BOM
hiding the first heading and invisible format characters are flagged. Preamble lines
are discarded by the parser; `preamble_characters` counts their LF-joined text, without
a trailing newline. Deeper heading lines remain in section bodies. Break counts cover
LF, CRLF, CR and all other separators recognized by `splitlines()` (including form feed
from PDF extraction). Line numbers match an LF-based editor only if CR and other
counts are zero. JSON escapes invisible and non-ASCII characters.

Invalid UTF-8 reports only the first invalid byte offset, never source bytes. No section
bodies are copied. Headings and paths may still be private. Each paper caps headings and
findings separately at 1,000 rows with omitted counts; parser status still covers the
whole file. Output exceeding 8 MiB fails with empty stdout rather than truncating JSON.
Authorization and every path check finish before reading any selected source. Any
preflight or safe-reader failure, including detected concurrent changes, aborts with
nonzero status and empty stdout. A supplied hash mismatch also aborts, exactly as in
normal preparation. No files are modified, no manifest is written, and conversion
fidelity and scholarly quality remain `NOT_ASSESSED`. No model or network is used.

For supported result commands, prefer `--output NEW_FILE` to shell redirection; see [exclusive output](EXCLUSIVE_OUTPUT.md). Existing shell blocks above remain valid but retain shell overwrite and re-encoding risks.


## Per-file local source byte bound

`prepare_local_manifest.prepare` and `corpus_files.load_segment_corpus` now read at
most 8 MiB + 1 bytes from each selected source and reject any file over 8 MiB. This
intentionally rejects previously accepted larger Markdown/text sources. Exactly
8 MiB can pass when encoding, headings, supplied hashes and authorization are valid.
No new corpus-total ceiling is added: several individually valid files can exceed
8 MiB together. Callers that already supply `max_total_bytes` retain that stricter
aggregate budget; each read is bounded by the smaller of the per-file ceiling and
remaining total. No CLI override is added. The low-level `read_source_bytes` API is
unchanged; its regular-descriptor, identity, mutation and hash callers' checks remain.

The whole selection is still preflighted before reading source bytes; files, supplied
manifests, canonical payloads and validation axes are not modified. Output size is not
newly capped: a multi-file producer can still create a package over a downstream
JSON reader's 8 MiB limit. The bound is bytes read, not a wall-clock, memory-allocation
or scientific-validation guarantee. No source authentication or approval is implied.
