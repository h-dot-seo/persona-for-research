"""Describe curated publication chronology, never a researcher's private beliefs."""
from observation_provenance import attach


def summarize(rules):
    """Group exact topic/method/condition tuples without semantic generalization.

    Call only after package validation. Years order publications, not decisions;
    distinct papers need not represent independent experiments or contributions.
    """
    groups = {}
    for rule in rules:
        key = (rule['topic'].casefold(), rule['method'], rule['condition'])
        group = groups.setdefault(key, dict(topic=key[0], method=key[1],
                                           condition=key[2], evidence=[]))
        group['evidence'].append({key: rule.get(key) for key in (
            'rule_id', 'paper_id', 'locator', 'year', 'source_kind', 'stance',
            'claim_type', 'evidence_quote', 'evidence_verification', 'limitation',
            'attribution')})
        attach(group['evidence'][-1], rule)
    result = []
    for key in sorted(groups):
        group = groups[key]
        evidence = sorted(group['evidence'], key=lambda e: (
            e['year'], e['paper_id'], e['locator'], e['rule_id']))
        group['evidence'] = evidence
        years = sorted({e['year'] for e in evidence})
        group['year_range'] = [years[0], years[-1]]
        group['year_buckets'] = [dict(year=year,
            supporting_rule_ids=[e['rule_id'] for e in evidence
                                 if e['year'] == year and e['stance'] == 'support'],
            challenging_rule_ids=[e['rule_id'] for e in evidence
                                  if e['year'] == year and e['stance'] == 'challenge'])
            for year in years]
        kinds = {}
        for kind in ('research', 'review'):
            kinds[kind] = sorted({e['paper_id'] for e in evidence if e['source_kind'] == kind})
        group['papers_by_kind'] = kinds
        group['distinct_paper_count'] = len({e['paper_id'] for e in evidence})
        support = {e['year'] for e in evidence if e['stance'] == 'support'}
        challenge = {e['year'] for e in evidence if e['stance'] == 'challenge'}
        group['within_year_disagreement'] = bool(support & challenge)
        group['cross_year_stance_variation'] = any(a != b for a in support for b in challenge)
        group['evidence_status'] = ('MIXED_STANCES' if support and challenge else
                                    'CHALLENGE_ONLY' if challenge else 'SUPPORT_ONLY')
        group['status'] = 'SYSTEM_INFERENCE_REQUIRES_REVIEW'
        group['inference_boundary'] = (
            'Publication chronology only; no inferred career stage, change of mind, '
            'independent replication, or individual authorship. Missing years are not '
            'evidence of inactivity; latest observations do not supersede earlier ones.')
        result.append(group)
    return result
