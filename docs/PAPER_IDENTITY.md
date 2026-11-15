# Detached CSL bibliography for runtime papers

`paper_identity.py` keeps supplied bibliography beside, not inside, a validated
package. Existing census import already preserves bibliography and prefills a
selection locator. This tool instead binds a declaration to final package paper
IDs and source hashes, replays the selected CSL copies, and optionally displays
current-source-matching rows in package review. It never resolves publication or
researcher identity, fetches URLs, authenticates permission or changes knowledge.

## Synthetic complete flow

Use an existing external OUTPUT directory and new files. The fixtures are invented
bibliography bound to the existing five-paper trajectory package. Two occurrences
are explicitly mapped; three package papers remain undeclared. The export has a
third unmapped occurrence and duplicate CSL IDs on the two selected occurrences.
The template is empty, not a manual identity-editing form or approval. The supported
filled-record writer is `from-csl`; regenerate instead of editing identities or
refreshing hashes. No source, existing fixture or package file is modified.

```sh
python paper_identity.py template examples/trajectory-conditions-package.json --operator-id synthetic-bibliography-operator --declared-at 2026-11-15 --output OUTPUT/empty.json
python paper_identity.py from-csl examples/trajectory-conditions-package.json examples/synthetic-paper-identity-export.csl.json examples/synthetic-paper-identity-mapping.json --operator-id synthetic-bibliography-operator --declared-at 2026-11-15 --output OUTPUT/declared.json
python paper_identity.py verify OUTPUT/declared.json examples/synthetic-paper-identity-export.csl.json examples/synthetic-paper-identity-mapping.json --output OUTPUT/replay.json
python paper_identity.py check OUTPUT/declared.json examples/trajectory-conditions-package.json --output OUTPUT/check.json
python review_package.py examples/trajectory-conditions-package.json --question "Synthetic bibliography review" --topic "model design" --paper-identities OUTPUT/declared.json --output OUTPUT/review.txt
```

Creation requires `--output` and uses exclusive creation outside the repository.
Check/verify can emit JSON or `--format text`, with optional exclusive output.
Successful saved output prints the standard receipt, not the saved artifact.
Errors emit no partial result stdout; I/O failure may retain a partial new file.
Original export and mapping must be kept privately for later copy replay.

## Explicit occurrence mapping

The exact mapping is `schema: persona.paper-identity-mapping.v1`, `export_sha256`
and `papers`. Each row has exactly `paper_id`, `census_id`, `entry_sha256`.
Use the occurrence IDs and full-entry hashes from the existing
[census import](CENSUS_IMPORT.md), together with the raw export SHA256. A census
selection map is not this mapping: it binds a pre-edit skeleton, not final runtime
paper IDs. Supply the final paper ID explicitly; do not infer it from title/DOI.

`census-000001` means the first object occurrence in those exact export bytes,
not a stable publication identity. Duplicate CSL `id` values are allowed because
no CSL ID is used for matching or copied to the declaration. Export reorder,
whitespace/newline changes and changed full-entry hashes reject the old mapping;
there is no automatic matching or rebinding. Package-unknown paper IDs, duplicate
paper mapping rows and invalid occurrences reject. A partial mapping leaves
other package papers `NOT_DECLARED`. Multiple paper IDs may explicitly select the
same occurrence; this is preserved, never evidence of independent publications.
Unmapped export occurrences are reported only as a count, not titles or IDs.

## Record, limits and copied fields

The declaration schema is `persona.paper-identity-declaration.v1`. Exact top keys:
`schema`, author_id/version/build_id/persona_payload_sha256/knowledge_papers_sha256,
`operator_id`, `declared_at`, `export_sha256`, `mapping_sha256`, `papers`, `boundary`,
`payload_sha256`. The final digest covers the record without its own digest key.
It is self-consistency, not a signature. Empty templates have null export/mapping
hashes. Every package paper has one row containing exactly `paper_id`,
`source_sha256`, `identifiers`, `declared_title`, `declared_year`, `source_export`,
`status`. Identifier keys are doi/pmid/pmcid/isbn/url, always present and nullable.
Unmapped values/source_export are null and status is `NOT_DECLARED`; mapped status
is `DECLARED_CSL_NOT_RESOLVED` with source_export exactly format=`csl-json`,
census_id and entry_sha256.

Only DOI/PMID/PMCID/ISBN/URL/title and issued.date-parts[0][0] are copied. Full-entry
hashes include other fields, but abstract/note/authors/CSL ID are not copied.
Missing/null strings stay null; supplied strings must be nonblank and are preserved
verbatim. DOI/PMID/PMCID/ISBN are limited to 128 characters, URL to 2048, title to
2000. Package paper IDs and binding identity text have a declaration-specific 2000
character limit; operator ID uses the existing 128-character identifier check.
The declared date uses the existing exact ISO-calendar-date check, not a clock.
Year uses the census int or four ASCII digits conversion, rejects supplied integer
years outside 1..9999 and leaves unavailable/non-supported year representations
null. Boolean is not an integer year. No free-text year inference occurs.

Every CLI invocation shares **8 MiB raw input bytes across all inputs**, including
export. CSL must be UTF-8, with optional UTF-8 BOM; NUL/UTF-16, strict-JSON duplicate
keys and nonfinite numbers reject. Both export objects and declaration/mapping
rows are limited to **4096**, deliberately narrower than the census tool's 10000.
Outputs are bounded to 16 MiB, not truncated. Generated declarations pass the
record shape checker, but that is not an all-sizes CLI roundtrip guarantee:
a large valid output alone, or plus its original export/mapping/package, can
exceed the next invocation's shared 8 MiB input limit. Creation does not add a new
8 MiB output ceiling or reserve a future replay budget. Retain originals and
choose smaller explicit inputs when planning replay; no automatic splitting or
truncation is performed. The test suite distinguishes small complete roundtrips
from this declared output/input budget asymmetry. Raw-byte
checks and strict JSON are reused; direct Python callers must separately bound
their supplied in-memory inputs. No claim of a hostile-memory/filesystem sandbox.

## Three different evidence levels

1. `from-csl` checks the supplied package and mapping and copies the supplied
   fields. It does not prove the export came from a publisher or reference manager.
2. `verify RECORD EXPORT MAPPING` replays those copies and exact hashes. Success
   is `CSL_COPY_REPLAY_MATCH_NOT_AUTHENTICATED`, not identity or rights clearance.
   It does **not** verify initial package bindings, source bytes, operator identity,
   declaration date authenticity or a current package. An empty template has no
   copy to replay. Its output schema is `persona.paper-identity-replay.v1`.
3. `check RECORD PACKAGE` and the review option validate the supplied declaration's
   structure/self-digest and current package/source bindings, **without original
   export/mapping**. They explicitly report `export_copy_replayed: NOT_PERFORMED`.
   A person can edit a value and recompute the self-digest: check can then display
   that supplied value on a source-matching row, while verify rejects it against
   the original export. “Manual editing unsupported” is a workflow restriction,
   not tamper resistance. No saved verify report is trusted as authority.

Check's schema is `persona.paper-identity-check.v1`. Package CURRENT/STALE is
separate from each row's `SOURCE_HASH_MATCH`, `SOURCE_HASH_DIFFERS` or
`PAPER_ID_ABSENT`. Another declared author rejects. Package-only STALE with a
source-matching row may display supplied bibliography, **with both labels**;
this does not make the package current. Source-differing/absent rows omit old
identifier/title/year values, including from DOI groups. New package papers are
listed as undeclared. Matching source hashes do not establish identical studies,
researcher identity, source authenticity, permission or actual file rereading.

The check exposes exact declared-DOI groups separately from ASCII-only casefold
DOI groups. It performs no Unicode casefold, URL-prefix stripping, trimming or
normalization. Equal identifiers are prompts to inspect, not deduplication or
publication authentication. Missing year and difference from the current package's
year produce explicit prompts, not corrections to either input.

## Review and privacy boundaries

`review_package --paper-identities` appends a separate declaration section after
the unchanged ordinary review. Existing rules, source groups, coverage, judgments,
HV and four-axis data receive no bibliography values. Without the option the
existing API/CLI output and loading branches are unchanged. With the option, the
package, declaration and every explicitly requested detached review/split/challenge/
release artifact share the 8 MiB budget; the entire appended text is bounded to
16 MiB. Prior option validation is not relaxed. Explicit null bibliography records and
split records reject. The existing release-decision option treats JSON null as
no decision; this legacy behavior is retained, not described as a checked release
record. Other supplied records continue through their existing validators.

Text escapes control/directional characters. URLs remain text, never fetched or
made into generated HTML links. They may contain account numbers, proxy hosts or
session information; titles and identifiers can also be private. Do not share
without separate authorization. No real bibliography, credentials, model call,
external transmission, runtime knowledge ingestion or approval is introduced.
RIS, publication-timeline, HTML and journey integration are outside this increment.
