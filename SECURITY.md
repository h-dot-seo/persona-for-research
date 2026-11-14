# Security and publication boundary

Keep actual user/research data outside this public repository. The examples are
synthetic and contain no real conversations, participants or researcher corpus.
Do not commit credentials, cookies, profiles, authentication bundles, SSH keys,
private hosts, personal account configuration, logs, original documents or databases.
Encrypted private material is also excluded from this code-only release.

The repository has a new public history; it does not import a private repository's
commit graph, deleted files, branches, tags or Git LFS objects. The publication
manifest enumerates the reviewed files. Review future diffs and staged files, not
only the current working tree. A .gitignore is not a data-loss prevention system.

`audit_publication.py` detects a small set of prohibited file types and common secret
patterns. A pass is not proof of anonymity, copyright clearance or absence of all
secrets. Human review of the actual selected files remains required. It does not
redact source material or turn a private corpus into a safe public release.

Do not disclose a vulnerability containing private information in a public issue.
Use an owner-configured private security channel when available. No contact address
or account-specific reporting endpoint is bundled in this release.

## Duplicate-key diagnostics

The shared strict JSON loader rejects duplicate object keys during JSON decoding,
before downstream processing. Its error message shows an ASCII-escaped, JSON-quoted
key prefix of at most 128 Unicode code points, with an explicit truncation notice
for longer keys. This keeps newline, terminal-control and bidirectional characters
from being emitted
literally through that diagnostic. It is not a general terminal sandbox or a claim
that every third-party error is safe.

Only the diagnostic display is shortened. Duplicate detection still compares the
complete decoded keys exactly; distinct long keys are not merged, and valid input
keys/values or original-byte hashes are not rewritten. Rejection does not grant
authorization, choose between duplicate values or certify source content.

## Bounded shared JSON reads

Shared file JSON loading defaults to 8 MiB; projection stdin uses the same limit.
Budget errors display only an ASCII-escaped, length-limited basename (or `<stdin>`),
not the parent directory. See [WORKFLOWS.md](docs/WORKFLOWS.md#shared-json-input-byte-budget)
for scope and compatibility: this is not a timeout, decoded-memory limit or source-size policy.
