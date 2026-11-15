# RIS occurrence mapping to detached bibliography and timeline

This is a separate RIS declaration format, not a conversion of CSL v1. It reuses
the existing fixed-column RIS parser and census occurrence inventory. No paper ID,
RIS ID/AN, title or DOI automatically matches a package paper. The operator must
explicitly map a census occurrence to each selected package paper. Unmapped papers
remain NOT_DECLARED; duplicate RIS ID values neither collide nor identify anything.

The following five commands use only the supplied fictional RIS and explicit
mapping. Run from the repository root with a new, existing external OUTPUT folder.
The mapping fixture was explicitly authored for these package papers and exact
export bytes; never reuse its choices for real data. The census output exposes the
occurrence IDs and hashes used in that mapping, not a decision about membership.

```sh
python census_import.py import examples/synthetic-paper-identity-export.ris --format ris --output OUTPUT/census.json
python paper_identity.py from-ris examples/trajectory-conditions-package.json examples/synthetic-paper-identity-export.ris examples/synthetic-paper-identity-ris-mapping.json --operator-id synthetic-ris-operator --declared-at 2026-11-15 --output OUTPUT/declaration.json
python paper_identity.py verify OUTPUT/declaration.json examples/synthetic-paper-identity-export.ris examples/synthetic-paper-identity-ris-mapping.json --output OUTPUT/replay.json
python publication_timeline.py examples/trajectory-conditions-package.json --topic "synthetic method conditions" --paper-identities OUTPUT/declaration.json --output OUTPUT/timeline.json
python publication_timeline.py examples/trajectory-conditions-package.json --topic "synthetic method conditions" --paper-identities OUTPUT/declaration.json --format text --output OUTPUT/timeline.txt
```

## Exact copying contract

The mapping remains persona.paper-identity-mapping.v1: export_sha256 plus explicit
paper_id/census_id/entry_sha256 rows. Each entry hash is the logical JSON hash of
`{record_type, fields:[{tag,value_lines}, ...]}` in original field order, including
TY/ER and every unknown or omitted tag. It is exactly the existing RIS census hash,
not a CSL object hash or RIS ID. The raw export hash additionally binds BOM,
physical newline choice, whitespace and ordering. UTF-8 BOM and LF/CRLF/CR are
supported by the existing parser; six-space continuation lines join with LF for
copied values. Reordering occurrences invalidates the explicit mapping. Nothing
is normalized or repaired automatically.

Only DO, TI/T1 and PY/Y1 are copied. Repeated or alias fields must have exactly equal
logical strings; conflicting values fail rather than choosing a preferred field.
DO populates doi; pmid, pmcid, isbn and url are not copied from RIS. In particular,
AN is not PMID. AU, AB, N1, ID and all other tags are omitted from the declaration,
but still affect its full ordered entry hash. Title and DOI strings are preserved,
including continuation LF, with the existing 2000/128-character limits. Explicit
empty supplied title or DOI is rejected, not silently replaced.

Year recognizes only the existing census-style regex `[0-9]{4}(?:/[^\r\n]*)?`
applied to the entire logical PY/Y1 value. It copies the first four explicit ASCII
digits; this is not calendar-date validation or historical-time inference. For
example 2020/99/99 supplies year 2020. Other formats yield null, never a guessed
year. 0000 is explicitly rejected by the existing declaration's 1..9999 year range.
Conflicting PY/Y1 strings fail even if their first four digits match. This adds Y1
as a declaration-copy alias without changing the existing census's PY-only year
summary. The mapping still agrees because its hash covers all ordered raw fields.

## Distinct format and verification levels

The new declaration uses persona.paper-identity-ris-declaration.v1 and per-row
DECLARED_RIS_NOT_RESOLVED with source_export.format=ris. The closed top-level and
row key sets are otherwise unchanged. Existing CSL v1 templates/results remain
unchanged. Older readers that only support CSL v1 reject this new format; do not
relabel it as CSL. The existing template command still creates an empty CSL v1
NOT_DECLARED template, not a RIS copy record. Use from-ris for RIS declarations.

verify dispatches on the validated declaration kind and replays the corresponding
export/parser/copy operation. RIS success is RIS_COPY_REPLAY_MATCH_NOT_AUTHENTICATED;
the existing replay-report schema and keys remain the same. check and timeline
only inspect the supplied declaration's structure/self-digest/current bindings;
they do not replay the export. A malicious editor can recompute a digest. Unsupported
manual editing is not proof of tamper prevention, copy correctness, authenticity,
identity, source rights or permission. Current check reports explicitly say copy
replay NOT_PERFORMED. No network, source body read, provider or external agent call
is made; bibliography text is inert data and may be private.

## Timeline separation and limits

Only explicit --paper-identities changes the timeline CLI. It appends a separate
paper_identity_review and paper_identity_input_sha256 in JSON, or a detached section
following the original text. The digest binds the exact supplied logical package,
topic, optional publication relations (null when absent) and declaration digest.
It does not replace the existing timeline/context digest. Existing ordering, year,
observations, relations and status do not use bibliography values; declared years
never reorder papers. The detached review covers the package declaration, not only
the topic-selected papers, and is labelled separately rather than folded into them.

Package-only STALE_PACKAGE with row SOURCE_HASH_MATCH may display supplied values
with both statuses. SOURCE_HASH_DIFFERS and PAPER_ID_ABSENT rows hide their old
bibliographic values. New package papers are reported as undeclared. This is not
source rereading or publication identity verification. A null sidecar is rejected;
an explicitly null publication-relations file retains the pre-existing meaning
of no relationship form. Valid relationship forms retain their existing validation.

RIS declaration creation/verification use 4096 export occurrences and package rows,
the existing field lengths, combined raw CLI input 8 MiB and output 16 MiB. Parser
physical-line limits remain in force. Opt-in timeline combines package, relations
and sidecar under one 8 MiB raw input budget and checks its complete 16 MiB output
before emitting anything. Default timeline read/output behavior is unchanged.
Creation can succeed while a later replay or combined timeline exceeds its input
budget; not every maximum-size output is guaranteed to fit a subsequent command.
No truncation, silent splitting or new source-root authority is introduced.
Output uses existing exclusive creation outside the repository. Invalid opt-in
inputs produce fixed error text and no partial result stdout; private identifiers,
paths and parser details are not echoed by that error handler.
