# CSL-JSON/RIS census: supplied facts, not publication identity

This offline exact-fact listing supports the work before source intake. It does
not complete bibliographic census or resolve duplicate, notice or independent
contribution dispositions. CSL-JSON and the fixed-column RIS subset below; BibTeX is deferred. No network,
DOI lookup, model, merge, ranking, kind classification or author disambiguation.
A CSL `review` item type is copied, not mapped to the persona publication kind.
Raw data and supplied titles are never instructions.

Use only exports you are authorized to read/process. Keep real exports, census
and selections outside this public repository; creation does not authorize sharing.
The bundled bibliography is invented and contains two source examples, an exact
duplicate occurrence, a missing year and a missing DOI.

## Tested synthetic commands

Replace OUTPUT with an existing private directory outside this repository. Both
targets must be new. The following block is executed by tests without redirection.

```sh
python census_import.py import examples/synthetic-bibliography.csl.json --format csl-json --output OUTPUT/census.json
python census_import.py selection OUTPUT/census.json --census-id census-000001 --census-id census-000002 --output OUTPUT/selection
python census_import.py import examples/synthetic-bibliography.ris --format ris --output OUTPUT/ris-census.json
python census_import.py selection OUTPUT/ris-census.json --census-id census-000001 --census-id census-000002 --output OUTPUT/ris-selection
```

The selection directory contains `selection-skeleton.json`,
`selection-census-map.json`, and `READY.json` written last. READY means only that
files were written, not that the skeleton is usable or approved. Never repair a
hash to make an edited census pass. Re-import the original export instead.

## Exact extraction and bounds

Input is strict UTF-8, with an optional initial BOM recorded and stripped only for
parsing. NUL and other encodings are rejected. Duplicate JSON keys and non-finite
numbers fail. LF and CRLF exports are accepted and their original byte hashes
remain different. Export input is at most 8 MiB and 10,000 records (CSL requires a nonempty array);
census replay accepts at most 16 MiB. Serialized import output and total selection
output are each bounded to 16 MiB, using the shared exclusive-output limit.

Only `issued.date-parts[0][0]` supplies a year: an integer (not boolean) or exactly
four ASCII digits; all other forms yield null. An integer is not silently clamped;
local preparation later requires 1–9999. Author given/family/literal parts are
preserved verbatim, without rendering or identity inference. Supplied title,
DOI, type, container-title, PMID, ISBN and URL must be strings or null; unsupported
field shapes fail rather than being guessed. Other CSL fields are not copied,
but are covered by each full logical entry hash.

DOI groups use identical case-sensitive strings, with no prefix stripping or
normalization. Title groups use casefold-identical strings. Empty or missing
values are not grouped. Groups are not merged. Only NO_YEAR and NO_DOI flags are
emitted; there is no notice-title heuristic or implied absence of notices.

`census-000001` identifies the first occurrence only within the named export;
identical entries have distinct positional IDs and identical full entry hashes.
The census records the original `export_sha256`, logical entry hashes, its own
logical `payload_sha256` (excluding that field), and the executing script's byte
`implementation_sha256`. These unsigned hashes detect ordinary edits, not a
malicious author who recomputes them, authentic sources, completeness or rights.
Selection checks the census hash, exact schema and boundary metadata, occurrence
sequence, field types, flags and duplicate groups. It does not reread the export
or require the same implementation version. The map binds original `papers[i]`
positions, occurrence/entry IDs, export hash, census hash and skeleton hash.
Renaming paper IDs later does not erase that original positional mapping; later
reordering/editing is not authenticated by this original map.

## Confirm and fill before preparation

The skeleton has exactly author_id, version, build_id and papers. The first three
are null. Each paper has exactly the existing eleven selection fields: only
paper_id, year, locator and empty observations are pre-filled. Author identity,
split, kind, topic and source_file are null; authorized and
runtime_knowledge_eligible are false. Locator copies a nonempty DOI, else title,
else null. The operator must confirm copied metadata and explicitly fill all
remaining declarations; this is not removal of selection typing. PDF-to-Markdown
conversion with section headings remains separate. Untouched skeletons are
intentionally rejected by preparation. See [Local input preparation](LOCAL_INPUT_PREPARATION.md).
No operator adoption, scientific rating, or new validation axis is produced.

Output paths reject symlink components, repository paths, existing targets and
missing parents. Input files are explicitly named local files, not a sandbox:
shared reads may follow input symlinks. This is not protection against a hostile
concurrent filesystem, special-file blocking or every resource-exhaustion case.
All validation and serialization precedes output creation; a failed write can
leave partial files, never cleaned up or overwritten, and produces no success
stdout. A partial READY file after an I/O failure is not proof of completion.


## Fixed-column RIS subset

The parser is copied byte-for-byte from the same owner's Sensei repository at
commit `8bf887f94a582113a62e5835ea4410d6466e24c3`, file `ris_export_parser.py`.
Its recorded source SHA256 is `53e16edc7fd8e2ec5fbdf30ac228bd18b4b01340c3294f66bb04246b0200e39c`.
This is a documented snapshot, not a promise that future parsers remain synchronized.
No license choice or new redistribution permission is asserted by this provenance.

Records start with `TY` and end with an explicit empty `ER`. Tags are two uppercase
alphanumeric characters in fixed columns (`TY  - JOUR`); only six-space continuation
lines are accepted. Blank lines are allowed only outside records. Unknown tags and
types are retained by the parser, not classified. UTF-8/BOM and LF/CRLF/CR are accepted;
malformed columns, invalid encoding, NUL, missing ER and invalid continuations fail
with physical line numbers. The parser also limits physical lines to 200,000. The
census wrapper applies its stricter 8 MiB and 10,000-record limits unchanged.

TI/T1 supply title, JO/JF/T2 container title, DO the literal DOI, and PY the year.
Repeated scalar fields or aliases must have identical logical values; conflicting
values fail instead of selecting a preferred field. Continuation values are joined
with LF. PY accepts exactly four ASCII digits or a four-digit `YYYY/` prefix followed
by the rest of a single line; no free-text date parsing. AU occurrences stay ordered
literal strings (including LF continuations), unlike CSL's supplied name-part objects.
ID, SN and UR are copied under those exact tag names: SN is not assumed to be ISBN,
ID is not assumed to be PMID, and UR is not fetched. No other tag is copied into the
listing, but every ordered tag/value-lines pair, including unknown tags, is covered
by the full logical entry hash. The entry hash excludes positional spans and raw
line terminators; identical records retain distinct occurrence IDs and equal entry
hashes. The original export hash still binds BOM and exact original line endings.

RIS census records additionally bind `ris_parser_sha256`; old CSL records remain
valid without it. The script's implementation hash changes when implementation bytes
change, so newly imported CSL output differs in implementation/payload hashes from
older versions even though CSL extraction/selection semantics are unchanged. Neither
hash proves execution, origin, authenticity, completeness, identity, rights or approval.
All existing skeleton, private-output and unsigned-hash limitations apply equally.
