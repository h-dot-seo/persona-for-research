# Correcting a first-observation response before import

## Check the response against its sources

Use the same four files you intend to import. The order is corpus, saved observation handoff, response, then separately declared provenance. These examples run from the repository root with inputs in an adjacent private directory. For a corpus with embedded segments, run the following command.

```sh
python model_handoff.py preflight-observations ../private/corpus.json ../private/observation-handoff.json ../private/response.json ../private/provenance.json
```

For a local manifest, supply the same source root used to prepare the handoff. Add `--format text` for a line per problem.

```sh
python model_handoff.py preflight-observations ../private/manifest.json ../private/observation-handoff.json ../private/response.json ../private/provenance.json --source-root ../private/sources --format text
```

The command prints a report to stdout. Exit 0 means the checks passed for this read. Exit 1 means the report contains problems. Exit 2 covers invalid arguments or an invalid installed schema. Reports use fixed names, codes and zero-based candidate positions. They omit filenames, IDs, hashes, quotes, unexpected keys, source text and raw parser errors.

| Status | What to do |
| --- | --- |
| `STRUCTURE_ERRORS` | Correct the listed response and provenance fields together. An unreadable or ambiguous JSON file is identified by its role. A `NOT_UTF8_ENCODABLE` value contains a lone surrogate. The command stops before opening the corpus or handoff. |
| `CORPUS_REJECTED` | Check the corpus input and its training selection. With local files, also check the source root, filenames, pinned bytes and section structure. The complete corpus must pass authorization before source files are read. |
| `BINDING_ERRORS` | `HANDOFF_NOT_CURRENT` means the saved handoff differs from a fresh observation handoff for this corpus. `RESPONSE_BINDING_MISMATCH` means the response belongs to a different saved handoff. Locate the matching originals or prepare a fresh handoff and response. Editing a digest would discard evidence of which handoff produced the response. |
| `EVIDENCE_ERRORS` | Inspect each reported row in the original response. Check paper membership for `UNKNOWN_PAPER`, the section in that paper for `UNKNOWN_LOCATOR`, and verbatim text in that section for `QUOTE_MISMATCH`. A missing paper or locator suppresses dependent checks for that row. |
| `CHECKS_PASSED` | Run the existing `model_handoff.py import` command with the same four files, `--task observations` and the same source-root choice. Review the resulting proposals separately. An empty response can pass with zero rows checked. |

For example, `/response/candidates/3/evidence_quote` points to the fourth candidate. Evidence checking starts only after both bindings match. It examines rows in their original order and compares each quote only with its named segment. `source_basis` records whether the check used supplied, hash-checked segments or freshly read, pinned local files. `UNVERIFIED` means corpus checking did not complete.

The command accepts bounded strict JSON (8 MiB per file). Local sources share the importer's 2 MiB total raw-source budget, and the reconstructed handoff retains its 2 MiB logical limit. Checks read current inputs each time. No proposal bundle, corrected input, persisted verification receipt, or review decision is produced. A match establishes only that the supplied quote occurs there.

## Check structure alone

Use the standalone schema catalog when only the response or its separately declared provenance is available. It collects multiple **static** errors without opening source files. The demonstrated errors are synthetic.

`schema_catalog.py check observation-response FILE` and `check declared-provenance FILE` use fixed completed-structure profiles. The existing manual profiles and seven editor profiles retain their meanings. These profile URNs identify schema documents, not instance fields: do not add `schema` or `$schema` to a response or provenance declaration. The provenance editor permits placeholders; this completed profile rejects blank strings. Null condition, limitation and topic are valid missing information. An empty candidates list is valid and does not authorize anything.

The response has exactly `handoff_sha256` and `candidates`. Each candidate has exactly paper_id, method, condition, limitation, topic, locator, evidence_quote, proposed_claim_type and proposed_stance. There are at most 128 candidates; text is at most 2,000 characters, except quotes at most 500. Non-null text must contain a non-whitespace character. Claim types are explicit_statement or operator_interpretation; stances support or challenge. Provenance has exactly provider_id, model_id, run_id, operator_id and execution_location: nonblank strings at most 128 characters without C0 or DEL controls; location is local, remote or unknown. These remain operator declarations.

The fixed subset adds only arrays/items/maxItems and string-or-null to the existing checker, plus one exact allowlisted provenance regex. Unsupported schema keywords, arbitrary regex and references fail closed. No schema URI is fetched. Errors contain closed field names, decimal array indices and codes, not unknown keys or private values. An oversized array reports MAX_ITEMS without descending into its elements; this bounds error work, not silent acceptance. Input is strict JSON, at most 8 MiB per check; complete output is at most 16 MiB before emission. There is no file output option. These limits do not imply that the existing importer accepts all such sizes: handoff generation retains its 2 MiB logical bound.

## Synthetic connected example

Run from the repository root with Python. Set `ROOT = Path.cwd()` and `OUTPUT` to an already-created private directory outside the repository. All filenames below must be new. The example uses only the existing synthetic corpus, and writes bytes explicitly as UTF-8 with LF. It does not send a prompt or invoke a provider. This Python example exercises the same APIs as the named CLI stages; it does not invoke a shell.

```python
import copy
import json
from pathlib import Path
from persona import payload_sha256
from handoff_packet import extract, save
from observation_proposals import prepare_observation_handoff, import_observation_response, review_template, review_proposals
from schema_catalog import check

corpus = json.loads((ROOT / 'examples/reasoning-corpus.json').read_text(encoding='utf-8'))
for paper in corpus['papers']:
    paper['observations'] = []
handoff = prepare_observation_handoff(corpus)
response = dict(handoff_sha256=payload_sha256(handoff), candidates=[dict(
    paper_id='synthetic-0', method='Compare competing explanations.',
    condition=None, limitation=None, topic=None, locator='synthetic reasoning',
    evidence_quote='Compare explanations.', proposed_claim_type='explicit_statement',
    proposed_stance='support')])
provenance = dict(provider_id='synthetic', model_id='synthetic', run_id='synthetic',
    operator_id='synthetic', execution_location='unknown')
bad = copy.deepcopy(response)
bad['candidates'][0].update(method='', unexpected_private_field='not echoed')
bad_provenance = dict(provenance, model_id='', execution_location='invalid')
transcript = ('```json\n' + json.dumps(bad) + '\n```\n').encode('utf-8')
files, ready = extract(transcript, json.dumps(handoff).encode('utf-8'))
save(files, OUTPUT / 'literal-extraction')
extracted = json.loads((OUTPUT / 'literal-extraction/response.json').read_bytes())
assert len(check('observation-response', extracted)['errors']) == 2
assert len(check('declared-provenance', bad_provenance)['errors']) == 2
# Explicit synthetic corrections, not automatic quote or binding repair.
assert check('observation-response', response)['structurally_conforms']
assert check('declared-provenance', provenance)['structurally_conforms']
bundle = import_observation_response(corpus, handoff, response, provenance)
review = review_template(corpus, bundle, 'synthetic-reviewer')
packet = review_proposals(corpus, bundle, review)
assert packet['status'] == 'OBSERVATION_PROPOSAL_REVIEW_INCOMPLETE'
assert packet['runtime_package_created'] is False
with (OUTPUT / 'deferred-review.json').open('xb') as stream:
    stream.write((json.dumps(packet, ensure_ascii=True, sort_keys=True, indent=2) + '\n').encode('utf-8'))
```

Literal extraction preserves the selected response bytes and binding to the supplied handoff; it does not validate candidate rows or authenticate the speaker. The existing importer reconstructs the current handoff, checks source membership, locators, exact quotes and freshness. A structurally conforming unknown paper, fabricated quote or stale hash still fails there. Exact quote matching itself is not semantic support. The unchanged deferred review is incomplete, not acceptance, canonical promotion or a runtime package.

No source files or manifests are read by the structural checker. It does not repair hashes, choose labels, normalize text, fill nulls or bypass authorization gates. Inputs and reports may still be private. Multiple static diagnostics are a correction convenience, not an exhaustive account of all later import errors.
