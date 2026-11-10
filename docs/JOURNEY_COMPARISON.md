# Compare two explicitly pinned research journeys

`journey_compare.py` reopens two [input cards](JOURNEY_INPUTS.md), validates their
current selected artifacts and shows what changed in the supplied evidence routes,
declarations and review prompts. It does not infer how a researcher thinks, why a
method changed, which version is better, or whether either is ready to use.

Both sides remain `HUMAN_REVIEW_REQUIRED_NOT_RESEARCH_APPROVAL`. **Previous/current
are labels you choose**, not verified dates or a claim of intellectual chronology.
The validated packages must have the same declared author ID, which is still not
authenticated researcher identity.

## Use preserved inputs, not cached reports

Keep each card's original files available under its own explicitly supplied root.
After independently reviewing changed inputs and their bindings, prepare a new card
rather than overwriting the old one or copying its hashes. The tool cannot compare
an old card against files that no longer match it, and it never repairs stale forms.
A saved journey JSON/HTML report is not a card or an authenticated historical receipt.

```sh
python journey_compare.py previous-input-card.json current-input-card.json --previous-root ../previous-review --current-root ../current-review --format text > new-comparison.txt
```

The default format is JSON. Output is stdout only; choose a new private filename,
because shell redirection can overwrite an existing file. Nothing is written back
to a card, source, review, design, or canonical persona package.

For each side whose card selects a source-check form, provide that side's source root:

```sh
python journey_compare.py previous-input-card.json current-input-card.json --previous-root ../previous-review --current-root ../current-review --previous-source-root ../previous-review/synthetic-sources --current-source-root ../current-review/synthetic-sources > new-comparison.json
```

Either side may omit source checking, but a selected source form requires its root;
an extraneous root for an unselected side rejects. Both selected checks read files
**now**, once per side. They do not recover historical source bytes or establish
when the files were available. Shared files may be read on both sides; matching
hashes or two successful reads do not establish independent evidence.

Both cards and all selected JSON bytes are loaded and hash-checked before either
journey inspection or live source audit begins. Both package identities are then
validated. Each side's artifact structure, bindings and source-selection/path rules
are checked by its normal journey inspector. This is not an atomic transaction:
a later artifact-structure or source failure can occur after an earlier authorized
source read. There is no partial stdout result, auto-repair or input modification.
Meaning, source authenticity, permissions and research validity are not evaluated.

## Read the comparison

Start with the compact text summary, then the complete embedded comparison JSON.
Both formats retain the two full freshly inspected reports, including rejected and
deferred records, imported original/reviewed/rejected proposal histories, inherited
observation provenance, and separate current versus recorded source checks.

- **Context:** exact question text, topic, reference year, selected pattern ID and
  target context. Different questions are displayed, not assumed comparable or
  blocked solely for differing wording. Equal wording is not semantic equivalence.
- **Named artifacts:** optional selection presence, relative path, raw bytes and
  logical JSON identity. Whitespace-only changes under an explicitly prepared new
  card differ from logical changes. Identical files under a new explicit root do not
  change the card. Input-root and source-root arguments are not persisted.
- **Exact references:** the union of the two supplied route indexes, with changed
  source-record fields separate from changed roles, uses and checks. A route found
  only on one side may simply leave the selected topic or pattern. It is not a
  missing or newly discovered publication. Parent observations and components stay
  distinct. The same paper ID, observation index and dimension can point to a
  different curated record after reordering or replacement.
- **Declared records:** answer text/citations, answer review decisions **and notes**,
  design steps, argument steps, evidence links, publication relationships, method
  applications, and selected pattern text. Resolved evidence is excluded from these
  declaration rows, so a source change does not masquerade as edited answer text.
  IDs and their order are compared exactly, not matched by meaning. Reused IDs do
  not establish a stable claim or step identity. Consider/defer/exclude and
  retain/revise/reject/defer keep their separate meanings.
- **Exact prompts:** full prompt objects and duplicate counts, ignoring list order.
  The same code for a different target is a different prompt. A previous-only prompt
  is explicitly **not proof that an issue was resolved**. Counts do not score risk,
  progress, research readiness, fidelity or review quality.

The declared groups are a navigation aid, not an exhaustive field-by-field diff.
For example, operator metadata and imported historical edits may appear in the
artifact hashes and complete reports without changing one of these groups. The
selected-pattern text group excludes evidence-use reasons, which remain visible
in the reference routes and full pattern histories. Do not use an unchanged group
as proof that its source package or provenance is unchanged.

`comparison_input_sha256` binds both card hashes, both logical journey-input hashes
and both fresh inspected-snapshot hashes. It is unsigned consistency metadata,
not an authenticated review, historical receipt or authorization to reuse bindings.
The tool never edits, migrates, approves, ranks or executes either version.

For a different scope, [package comparison](../compare_releases.py) inventories
supplied paper changes, while [revision impact](REVISION_IMPACT.md) traces old
answer/design uses into a different package without rebinding them. This comparison
instead validates two complete, independently bound journeys.

## Limits and validation scope

- Only explicit local card files and their selected JSON/source inputs are read.
  No filesystem discovery, model/provider call, network, browser or scientific run.
- Card files retain the regular-file, no-symlink/reparse, strict-JSON and 128 KiB
  bounds. Selected artifact bytes are at most 8 MiB **per side**, at most 16 MiB
  across both. Each existing journey's logical-input limits also apply.
- The entire comparison, including both full reports, must fit within 16 MiB.
  Text has the same final limit. Large valid individual journeys can exceed the
  combined limit; the command fails rather than truncating histories. Explicitly
  narrow inputs before creating new cards if necessary.
- Live source-byte limits are separate and apply per selected side. Stable-file
  limitations remain: no atomic multi-file snapshot, filesystem sandbox or complete
  hostile concurrent-filesystem protection is claimed.
- Text escapes controls and directional characters; the complete JSON preserves
  their exact values through JSON escapes. Outputs can contain private filenames,
  quotes and annotations. They are not anonymized or cleared for sharing.
- Tests and examples use invented evidence and canned proposals only. No real
  researcher, scholarly semantic support or fidelity has been evaluated. Existing
  actual-browser visual/keyboard/print QA remains blocked and unverified; this
  JSON/text increment neither retries nor bypasses that restriction.

## Imported answer history

For [reviewed answer proposals](ANSWER_PROPOSALS.md), accepted claims are compared
as declarations separately from candidate, adoption-decision and declared-import
groups. These extra groups exist only when either side has imported history and
are labeled as recorded imports, not operator authorship or active evidence.
Rejected-history changes can alter the full draft identity while accepted claim
fields remain unchanged. Full before/after reports preserve the complete history;
manual/imported transitions never silently discard it.

## Imported argument declarations

For [argument proposals](ARGUMENT_PROPOSALS.md), step fields are compared in their
declared order, not the graph's deterministic topological review order. Manual
raw declaration order and imported candidate-adoption order remain distinct from
review topology. Additional original-candidate, adoption-decision and declared-import
groups retain full history without calling it operator authorship or active evidence.
Changing a rejected bridge can alter argument identity without changing any adopted
step; manual/imported transitions keep both complete reports.

For supported result commands, prefer `--output NEW_FILE` to shell redirection; see [exclusive output](EXCLUSIVE_OUTPUT.md). Existing shell blocks above remain valid but retain shell overwrite and re-encoding risks.
