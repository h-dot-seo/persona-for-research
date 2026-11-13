# Detached census and frozen split declaration

`split_declaration.py` records an operator's declared census and training, holdout,
comparator and excluded split lists. It never edits the persona payload, acquires
sources or claims that a holdout was unseen. This is the first bounded part of roadmap
split governance: intake gating, release-review integration, split comparison and
actual holdout evaluation are not implemented here.

## Synthetic rehearsal

Create a new `OUTPUT` directory outside this repository before running these exact
commands. Its parent and the directory must already exist. The included declaration
contains eight invented records: the five training IDs of the existing synthetic
trajectory package, plus one invented ID in each other split. It is not a real census.

```sh
python split_declaration.py template --author-id synthetic-scholar --operator-id synthetic-operator --output OUTPUT/blank-declaration.json
python split_declaration.py freeze examples/synthetic-split-declaration.json --output OUTPUT/synthetic-frozen.json
python split_declaration.py check OUTPUT/synthetic-frozen.json examples/trajectory-conditions-package.json --text
python split_declaration.py status examples/trajectory-conditions-package.json --split OUTPUT/synthetic-frozen.json --output OUTPUT/split-status.json
python split_declaration.py status examples/persona.json examples/knowledge.json --text
```

The blank template is deliberately not freezable. Fill a private copy with the actual
operator's declarations; do not reuse synthetic source selection or reading claims.
`freeze` validates and writes a new frozen document, never modifying its input. Check
stdout for `DECLARATION_FROZEN`, then compare the intended package. `check` accepts
`FROZEN PERSONA [KNOWLEDGE]`: either two bound documents, a single `{persona, knowledge}`
package, or a `{package: ...}` wrapper. `status` uses `PERSONA [KNOWLEDGE] --split FROZEN`.

## Record contract

The draft has exactly these fields, all required:

- `schema`: `persona.split-declaration.v1`.
- `author_id`, `operator_id`: nonempty labels, at most 128 characters, no control
  characters or email addresses. Labels are not authenticated identities.
- `declared_at`: a valid calendar date `YYYY-MM-DD`, not an authenticated timestamp.
- `holdout_reading_declaration`: a nonempty assertion of at most 2,000 characters.
  The tool checks its presence, not its truth, timing or adequacy.
- `census`: 1 to 4,096 rows; unique exact `record_id` strings.
- `splits`: exactly `training`, `holdout`, `comparator`, `excluded`, each a list of IDs.
  The lists must be disjoint, contain no repetitions and cover the census exactly.
- `status`: null for a draft, `FROZEN` in an output frozen document.

Each census row contains exactly `record_id`, `author_id`, `record_relation`,
`of_record_id`, `kind`, `year`, `locator`, `authorized`, `access_restriction`.
IDs and author labels have the same 128-character limit. `kind` is a nonempty
128-character string. `locator` and `access_restriction` are nonempty strings of at
most 2,000 characters; explicitly state no restriction if that is the declaration.
`authorized` is a boolean declaration, not an access grant. `year` is an integer
1..9999 or null for a nontraining record. Training requires `research` or `review`
kind and an integer year. Notice and other nontraining kinds remain expressible.

`record_relation` is `paper`, `duplicate_of`, `notice_of` or
`independent_contribution`. A paper has null `of_record_id`. Every other relation
must refer directly to an existing paper row: no chains, self-reference or cycles.
Training and holdout author labels must match the declaration; comparator labels must
differ. Excluded rows may have either label.

A declared relation group (paper plus related rows) cannot span training and holdout
or comparator. This is a contradiction in the supplied isolation declaration, not an
automatic duplicate detector. Duplicate/notice rows in training and undeclared training
authorization are allowed structurally and reported as **policy counts, not verdicts**.
For example, a permitted preprint copy may be declared a duplicate. Decide that policy
outside this mechanical check.

## Hashes and frozen state

Freeze sorts census rows by ID and each split list lexically. It adds `census_sha256`,
`split_sha256` (one digest per sorted ID list) and `declaration_sha256` (all other frozen
fields, including the first two hashes). Hashes use the repository's logical JSON
convention: UTF-8, sorted object keys, compact separators, no excluded keys except the
declaration's own digest. Check revalidates structure, order and every digest.

Changing authorization metadata changes the census and declaration digests, but not
the unchanged ID-list digests. Never edit an old frozen file. Preserve it and create a
new draft/frozen record. `FROZEN` means mechanically sorted and hashed, not immutable
storage, trusted timestamp or cryptographic identity authentication.

## Comparison and exit codes

- `PACKAGE_WITHIN_DECLARED_TRAINING`: the author label matches and every package paper
  ID is in declared training with exactly matching kind, year and authorization.
  This allows a training subset and even an empty package (paper count is shown); no
  minimum corpus size or completeness is claimed.
- `PACKAGE_OUTSIDE_DECLARED_TRAINING`: author, membership or metadata differences.
  `HOLDOUT_ID_IN_PACKAGE`, `COMPARATOR_ID_IN_PACKAGE`,
  `PACKAGE_PAPER_NOT_IN_TRAINING_SPLIT`, `AUTHOR_LABEL_MISMATCH` and
  `TRAINING_METADATA_MISMATCH` identify the kind of difference.
- `NOT_DECLARED`: no split document was supplied to `status`.

`check` returns 1 for any reported difference, including holdout/comparator conflicts,
and still emits the report. `status` reports differences with exit 0. Structural or
hash failures return 1 without a result; argument errors return 2. No result certifies
scientific quality, author fidelity or blinding. A declaration is bound only by author
label, not to an evolving canonical package: there is deliberately no `CURRENT` status.

## Privacy and file boundaries

Frozen documents contain the full private ID lists. Keep declarations and results
outside the public repository. Reports and freeze receipts show split counts and
hashes only, never withheld/comparator/excluded IDs from the declaration. The sole
exception is a conflicting ID already present in the supplied package. Supplied
metadata, operator labels and reading assertions are not repeated in those reports.
A declaration hash is not anonymization: enumerable IDs may be guessed.

Only exact ID strings are compared. DOI/PMID aliases and undeclared relationships are
not discovered. There is no DOI lookup, census completeness check, deduplication,
source reading, access control or evidence that freezing preceded holdout reading.
Several different frozen declarations may exist for one author; this report concerns
only the one supplied. No model/network call or canonical modification occurs.

Inputs share an 8 MiB byte budget, use strict JSON and reject symlink path components.
Saved output is bounded to 16 MiB, exclusive UTF-8/LF, outside the repository, with an
existing nonsymlink parent. Check paths are preflighted before reading inputs. Ordinary
filesystem paths must be under the operator's control; these checks are not a defence
against hostile concurrent filesystem replacement. `check/status --output NEW_FILE`
use the existing private save receipt. A partial write is retained on failure and no
file is removed or overwritten. See [exclusive output](EXCLUSIVE_OUTPUT.md).
