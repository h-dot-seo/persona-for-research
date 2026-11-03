"""Descriptive coverage counts, never confidence or a readiness decision."""
from reasoning_cards import DIMENSIONS


def coverage(rules):
    dimensions = []
    for dimension in DIMENSIONS:
        rows = [(rule, rule.get('reasoning', {})[dimension]) for rule in rules
                if dimension in rule.get('reasoning', {})]
        dimensions.append(dict(dimension=dimension, component_count=len(rows),
            paper_ids=sorted({r['paper_id'] for r, _ in rows}),
            source_kinds=sorted({r['source_kind'] for r, _ in rows}),
            explicit_statement_count=sum(c['claim_type'] == 'explicit_statement' for _, c in rows),
            operator_interpretation_count=sum(c['claim_type'] == 'operator_interpretation' for _, c in rows),
            quote_matched_count=sum(c.get('evidence_verification') == 'EXACT_QUOTE_MATCH_ONLY' for _, c in rows),
            supporting_rule_ids=[r['rule_id'] for r, _ in rows if r['stance'] == 'support'],
            challenging_rule_ids=[r['rule_id'] for r, _ in rows if r['stance'] == 'challenge'],
            evidence=[dict(rule_id=r['rule_id'], paper_id=r['paper_id'], locator=c['locator'])
                      for r, c in rows]))
    missing = [d['dimension'] for d in dimensions if not d['component_count']]
    status = ('NO_OBSERVATIONS' if not rules else
              'NO_REASONING_COMPONENTS' if len(missing) == len(DIMENSIONS) else
              'PARTIAL_DIMENSION_COVERAGE' if missing else 'ALL_DIMENSIONS_REPRESENTED')
    return dict(status=status, observation_count=len(rules),
        distinct_paper_count=len({r['paper_id'] for r in rules}),
        papers_by_kind={kind: sorted({r['paper_id'] for r in rules if r['source_kind'] == kind})
                        for kind in ('research', 'review')},
        dimensions=dimensions, missing_dimensions=missing,
        boundary='Counts describe only supplied topic-matched records. Paper IDs are not '
                 'independently authenticated publications. Repetition and complete coverage '
                 'do not establish confidence, scientific validity, representativeness, '
                 'independent replication or readiness for use.')
