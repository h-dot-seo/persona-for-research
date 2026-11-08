# Review a proposal's publication-year scope

A synthetic question asks how to distinguish two models. Its proposed comparison
uses a later review's criterion as a constraint on earlier original research.
The existing design report shows years, but does not explicitly flag that this
link reaches beyond a reviewer-specified historical reference year.

Run with the same local package, operator links and proposal used by
`design_scenario.py`:

```
python publication_scope.py package.json links.json proposal.json --reference-year 2001 --format text
```

Reference and linked publication years must be integers from 1 to 9999; invalid
linked years reject the audit even for unused links. The reference year is mandatory and never parsed from question text. JSON is the
default output. The scope request hash binds the explicit year and comparison
policy to the proposal hash; the report also includes all package/link bindings.

For each proposed use, both link endpoints are classified:

- `AFTER_REFERENCE_YEAR`: the supplied publication year is later.
- `SAME_YEAR_ORDER_UNRESOLVED`: year-only metadata cannot order events.
- `BEFORE_REFERENCE_YEAR`: the supplied year is earlier, not proof of access.

Step status prioritizes a later endpoint, then same-year uncertainty; all earlier
endpoints yield `NO_LATER_LINK_ENDPOINTS`, never approval. A step without links is
`NO_LINKED_EVIDENCE_SUPPLIED`. Empty proposals still require review. Link roles do
not exempt an endpoint, and direction does not imply temporal influence.

The reviewer can inspect each endpoint's research/review kind, original claim
label, method, condition, limitation, source and component locators, recorded
checks and hash. Complete design output retains missing falsification/alternative
fields, operator hypotheses and every unreferenced link, including counterevidence.
No link is silently removed, repaired or substituted. Dates do not determine
relevance, and unused records are not an exhaustive audit of contrary evidence.

A review can summarize others' research. Neither source kind nor an
`explicit_statement` label proves the named scholar owns the idea. Publication
order does not reconstruct intellectual influence, actual availability or private
reasoning. Preprints, acceptance dates and access dates are not modeled; a later
publication is not proof an idea was unavailable earlier. This report does not
rebuild a historically restricted persona: the package and proposal may contain
later information, and the whole supplied design remains visible.

All fixtures are synthetic. This feature makes no model/API calls, reads no
original source files, and performs no semantic or historical validation. Real
scholarly evaluation requires authorized local sources, verified identity and
rights, source-date checking and independent domain review; it must not reuse
these mechanical statuses as fidelity scores.

Reproduce the actual CLI experiment and negative cases:

```
python -m unittest tests.test_publication_scope -v
```
