# Repository choices and coordinated changes

This is a maintainer checklist for future owner decisions, not an operator
adoption/review decision, a license recommendation or a change of policy.
The authoritative rights position is [RIGHTS](../RIGHTS.md). This page deliberately
does not create another copy of that position. Public availability alone is not
an instruction to change rights, branches, tags or repository settings.

## Rights decision procedure

The owner decides whether and how to license the code, documentation and examples,
whether their terms should be the same, how contributions would be accepted, and
whether the three repositories should be considered together or separately.
Questions about notices, attribution and patent provisions belong to that decision;
this checklist does not choose candidates or provide legal advice. Check ownership
and any third-party material separately. Mechanical consistency is not legal review.

When an owner-authorized decision changes the rights state, coordinate these five
existing locations in the same reviewed change:

- [RIGHTS](../RIGHTS.md)
- [English README](../README.md)
- [Korean README](README.ko.md)
- [Workflows](WORKFLOWS.md)
- [Publication manifest](../PUBLICATION_MANIFEST.json), including its status label
  and inventory entry for the corresponding license/copying file

Do not change only the label or add only a license file. A future license file
must also pass the existing inventory/publication checks. For example, the public
email-pattern audit also applies to newly added notices; satisfying this test does
not waive that audit or prove the notice is legally correct. Current publication
verification and manual review remain separate steps; see
[Publication](../PUBLICATION.md) and [Security](../SECURITY.md).

## What the test does, and does not do

`tests/test_rights_consistency.py` is a test-only drift check, not a product API or
CLI. It compares four existing normalized statement signals with the manifest's
exact `NOT_SELECTED` sentinel and listed/actual license file paths. The absence of
that sentinel requires a nonblank string label and exactly one identical listed
and actual license/copying path. Removing one statement, changing only metadata,
or adding a file alone cannot silently complete a transition.

Filename recognition is intentionally mechanical: basename `LICENSE` or `COPYING`,
or either followed by a dot and suffix, case-insensitively, at any relative tree
location. For example, `terms/COPYING.txt` is recognized; `LICENSE_NOTES.md` is not.
Listed and actual paths must match exactly, even on a case-insensitive system.
The check reuses the publication verifier's inventory and portable-relative-path
rules, rejects duplicate/case-colliding manifest paths and inventory errors, and
reads the manifest with strict JSON. It is not a new filesystem security boundary
or a content-based search for all possible legal documents. Generic inventory/hash
validity remains the publication verifier's responsibility.

Whitespace normalization permits wrapping existing prose without requiring exact
line breaks. The test deliberately does not interpret replacement prose, validate
SPDX identifiers, read legal meaning into license contents, establish ownership or
authenticate approval. Its selected-state fixtures use an explicitly fictional
label and text, not a real selected license. Passing either state establishes only
mechanical consistency of these signals, not legal validity or permission.

## Layout and branch/tag choices remain separate

For the intentional flat module layout, consult the existing
[command reference](COMMANDS.md) and [validation notes](../VALIDATION.md) rather
than duplicating their rationale. A demonstrated packaging/distribution need or
changed resource-location requirement would justify revisiting that choice; a new
format or dependency should not be inferred from this checklist.

Tag naming and release-to-tag mapping need an explicit owner decision before a tag
trigger or tag is introduced. Any later proposal should state its exact relationship
to the manifest release and verified commit, and preserve the existing private-
history boundary in Security. This page does not select a spelling or create a
release. The obsolete branch push trigger has already been removed; it is not a
new action requested here. Deleting merged branches or changing automatic deletion
settings is a separate maintainer action, not a side effect of publication.

No private maintenance procedure, environment detail or new executable recipe is
included here. This checklist neither changes scientific judgments nor grants
access to research inputs.
