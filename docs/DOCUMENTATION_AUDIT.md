# Maintainer documentation subset audit

Run `python -m tests.doc_conformance` from the repository root. It reads only root
Markdown files, immediate `docs/*.md`, the fixed test evidence registry and the
named test source files. It never executes guide commands, imports recorded tests,
queries URLs, accepts a private input path, or writes files. stdout is a bounded
JSON report, not a new public artifact schema or release approval.

The report always says `PARTIAL_SUPPORTED_MARKDOWN_SUBSET`. `SUPPORTED_CHECKS_PASS`
means only that the supported checks found no errors/unresolved syntax, not full
Markdown validity or command execution. `REVIEW_REQUIRED` means detected broken
links, stale evidence, or unsupported syntax remains. Exit 0/1 follows that status;
invalid CLI arguments use exit 2. The initial maintained tree includes unsupported
syntax, so exit 1 is expected and must not be described as a complete link pass.
`checked_local_links`, `external_links_not_checked`, `error_count`,
`unresolved_count` and block-state counts are separate. External URLs are never
verified. Unregistered blocks are `NOT_REVIEWED`, not unconditionally untested:
there may be bespoke tests whose ownership has not been reviewed into the registry.

## Supported parsing scope

The state-based subset handles ordinary inline links/images with balanced brackets
and parentheses, optional quoted titles, angle-bracket destinations, reference
links/definitions, scheme autolinks, backslash escapes, backtick inline spans
(including multiline spans), backtick/tilde fences, indented code, and plain ATX or
setext headings. Code contents are not link candidates. Heading slugs lowercase,
remove punctuation outside Unicode word characters/hyphen/space, turn spaces into
hyphens, and disambiguate duplicates/collisions. Percent-encoded paths/fragments
are decoded before lookup; Unicode headings are preserved under that subset rule.
This is not a complete GitHub slugger or CommonMark parser. Complex formatted/link/reference/entity
headings, HTML/comment constructs, all blockquote lines, multiline
links/reference destinations, and ambiguous/unclosed constructs can be unresolved.
List-indented Markdown is not fully parsed; indented code classification is a
subset limitation. Ordinary unmatched shortcut-reference-like prose is not assumed
to be a link. Unsupported syntax must not be inferred to have valid destinations.
Local links with query components or anchors into non-Markdown files are unresolved.
Anchor lookups into a Markdown document with any unresolved syntax are conservatively
UNRESOLVED_ANCHOR_TARGET, not a definite missing-anchor error. Code/comment masking
precedes reference-definition collection; definitions inside them are not adopted.
Relative links escaping the repository are errors, not permission to read elsewhere.

Raw regex matches are not used as evidence that code samples are real links. Parser
regressions use synthetic strings; they do not establish complete renderer parity.
The audit preserves all existing documentation; no source guide blocks are rewritten.
Input reads share 8 MiB (including registry and evidence test source reads), files
are limited to 4096 Markdown documents, and output is limited to 16 MiB. Registered
test source may be read more than once and each read counts toward the budget.

## Block ownership is reviewed metadata, not execution

Each sh block is identified by document path, one-based sh-block ordinal and SHA256
of its exact UTF-8 body bytes, including original line endings. Fences themselves
are not in that hash. The registry `tests/doc_block_evidence.json` contains only
manually inspected mappings. Current entries cover five guides:

- COMPARATOR_OVERLAP: all three commands, repository paths after shlex parsing,
  supplied fictional declarations; expected successful reports, including no-topic.
- COMPARATOR_SOURCES: its one full command using separately shipped fictional source
  bytes and an explicit supplied mapping; expected comparator-only check status.
- MANUAL_REJECTION_DETAILS: both full commands intentionally reject wrong card
  shapes. OUTPUT maps after shlex to a fresh temporary path with spaces. Required
  outcome is exit 1, empty stdout, two stderr lines and no output directory. This
  is **not** successful manual authoring or real operator review.

- MANUAL_LOCAL_OBSERVATIONS and MANUAL_EVIDENCE_REVISION: the first two sh
  blocks in each guide execute as one four-block/nine-command chain through a new
  review workspace. Fixed scratch-path tokens are replaced only after shlex. A
  single trailing `>` is captured as unchanged stdout bytes, not shell emulation.
  Success stdout uses LF even on Windows; native stderr is checked separately.
  The two third blocks invoking unittest are explicitly excluded to avoid nested
  test execution; they remain NOT_REVIEWED in the block registry. Prewritten
  synthetic operator cards are not actual review. Blank templates are generated
  but remain incomplete and are checked to reject without extra source reads.

Each entry records the exact test method, full/partial/expected-rejection coverage,
substitution and manual-step description. Test method source hashes use the exact `ast.get_source_segment` definition/body
after CRLF/CR-to-LF normalization. AST is used only to select the named method;
Python-version-specific AST fields do not enter the hash. Formatting changes inside
the selected segment become stale; moving it to another line alone does not. This is a reviewed
ownership pointer, not proof of runtime behavior: decorators, transitively called helper bodies, imports and fixture changes are not bound by the
method source hash. These changes and an incorrectly authored registry entry require
separate review. Existence of the
method or a Markdown filename in source is not sufficient evidence of execution.
Changed block body or test method source becomes `STALE_EVIDENCE`; deleted/moved registered
blocks produce errors. No new block automatically inherits an execution claim.
Other guides and evolving release/validation metadata remain `NOT_REVIEWED`.
The report always has `guide_execution_performed: false`.

## Existing complementary tests

Do not duplicate or weaken the existing checks. `tests.test_dispatcher` already
compares COMMANDS CLI headings against real entry points; libraries must not use
those reserved headings. `tests.test_command_catalog` executes trusted help and
compares usage lines. `tests.test_skill_contract` checks SKILL paths/size, while
`tests.test_changelog` binds release-index anchors. Run these separately when the
corresponding contract changes. This audit does not run them or claim their result.
No CI timeout, generic guide runner, shell redirection emulation, README coverage mandate, language
heading policy, or cross-repository shared implementation is introduced.
