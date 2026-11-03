# Prepare an explicitly selected local source

The existing local loader requires a byte hash and exact section locators before
curated observations can be checked. `prepare_local_manifest.py` removes that
manual hashing/heading-discovery step. It does not extract scholarly claims,
collect articles, parse PDFs or call an external metadata/model service.

Use only local files you are authorized to read and process. The supplied selection
must explicitly declare author identity, publication kind/year, intended topic,
training split and permission. These fields are not inferred from filenames or
headers and are not authenticated by this tool.

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
python -m unittest test_prepare_local_manifest -v
```
