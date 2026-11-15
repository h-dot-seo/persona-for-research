# Correcting a first-observation response before import

This optional correction aid collects multiple **static** errors in a supplied first-observation response and its separately declared provenance. It is not a new extraction method, import acceptance, model authentication, permission, or scientific validation. The demonstrated errors are synthetic, not a claim about their frequency in actual use.

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
