# Exact rule-record correspondence, not stable semantic identity

A rebuilt rule-N is a position, not an identity or priority. This read-only tool
shows exact supplied content hashes and positions after reordering/insertion.
It does not solve stable IDs across edits or infer semantic equivalence, withdrawal,
literature additions or changes of mind. Human judgments, links and answer citations
are not rebound, transferred or declared valid. No human-record integration is
included, and compare_releases/revision_impact outputs are unchanged.

## Synthetic commands

Choose an existing private external OUTPUT directory. The second fixture is a
rebuild of the first with reversed paper order and one invented inserted
observation; the original fixture is unchanged. Explicit LF bytes are used in the
new fixture. Guide tests shlex-split commands before substituting native paths,
so Windows backslashes and spaces are preserved.

```sh
python rule_correspondence.py inventory examples/trajectory-conditions-package.json --output OUTPUT/rules.json
python rule_correspondence.py compare examples/trajectory-conditions-package.json examples/synthetic-rule-reordered-package.json --format text --output OUTPUT/correspondence.txt
```

`inventory PACKAGE [KNOWLEDGE]` accepts one bound package, a `{package: ...}` wrapper,
or separate persona and knowledge files. `compare PREVIOUS CURRENT` accepts the
same package forms; use --previous-knowledge and --current-knowledge for separate
persona/knowledge pairs. Both sides must have identical supplied author_id strings;
this is not verified identity. Inventory/compare output schemas are
persona.rule-inventory.v1 and persona.rule-correspondence.v1. They are stdout views,
not accepted catalog inputs. Input validation always runs checked_package (including
persona.validate) and validated_source_rules before deriving position mappings.

## Hash definitions and visible records

For each rule, rule_payload_sha256 is payload_sha256 of the exact object
`{rule: <entire rule except rule_id>, source_sha256: <bound paper hash>}`.
It omits only position; reasoning, origin, year, kind, recorded quote verification
and every other rule field remain included. observation_content_sha256 is
payload_sha256 of `{content_sha256: observation_provenance.content_sha256(observation),
paper_id: <paper ID>, source_sha256: <bound paper hash>}`. The inner helper's existing
CONTENT_FIELDS semantics are unchanged. Each component hash is payload_sha256 of
the whole component, not a selected semantic subset.

Inventory includes package identity and both binding hashes, native build-order
rule/observation positions, these keys, full position-free rule payloads and recorded
paper metadata. Quoted evidence and source labels may be private. Nothing rereads
sources or authenticates recorded quote/source labels. Changed quote verification,
year, kind, reasoning or provenance fields are not suppressed by the coarser
observation key. Paper metadata changes are separately listed even if the full rule
key is unchanged. Rule indexes and observation indexes are zero-based; rule-N is
the existing builder label. No canonical fields are added.

## Comparison rules and ambiguity

- SAME_RULE_PAYLOAD_SAME_POSITION: unique exact full-rule key and same build position.
- SAME_RULE_PAYLOAD_DIFFERENT_POSITION: unique exact full-rule key at a different position.
- SAME_OBSERVATION_CONTENT_OTHER_FIELDS_CHANGED: unique observation key but changed
  full rule payload. changed_rule_fields and changed_component_dimensions name all
  differences, including key absence. changed_paper_fields separately names metadata
  differences; no meaning or correctness is inferred.
- ONLY_PREVIOUS_PACKAGE / ONLY_CURRENT_PACKAGE: unmatched nonambiguous positions,
  not deletion/retraction, new literature, adoption or changed beliefs.
- AMBIGUOUS_DUPLICATE_KEY: either key duplicated on either side. All positions on
  both sides are shown in key groups and none is automatically paired. This
  deliberately conservative rule also blocks otherwise unique full-rule matches
  when their coarser observation key is duplicated. Full hashes remain visible in
  each inventory; ambiguity is not hidden by a convenient one-to-one assignment.

Full-rule matches are considered first, then unique observation-content matches.
Manual paper_id+locator candidates are grouped as both complete position lists,
not Cartesian pair records or inferred identity. Every matching location group is
shown, even if exact matches also exist. Exact rule/observation/source hashes in
those lists let an operator inspect candidates. Shared locators alone do not show
that one rule changed into another. Grouping avoids quadratic pair materialization;
counts describe groups/records, never scores or readiness. Ambiguous positions are
not also mislabeled ONLY_*.

## Limits, output and privacy

All input files share one 8 MiB budget, including four files in split compare mode.
Strict JSON rejects duplicate keys/non-finite values. Output JSON and text each
have a 16 MiB cap; growing inventory rows are checked incrementally before a large
inventory is accumulated, then complete reports are bounded. Oversize results fail
rather than truncate. These are byte bounds, not a hostile filesystem/time sandbox.
JSON uses sorted keys; lists retain native package order or documented hash-group
order. Text includes every report field and uses display() escaping for control and
directional characters. Both formats contain the boundary. No LLM/network calls.

Without --output, only the complete result is emitted to stdout. --output uses the
shared exclusive external-path helper: no existing file, repository path, symlink
component or missing parent. Preflight happens before reads. Input/formatting errors
emit no partial stdout; filesystem write failures may retain a partial new file.
Original files, payloads, validation axes, citations and human records are unchanged.
No sharing permission is implied: stored quotations and operator/provenance labels
may appear in this private view. Export is not approval or a release decision.
