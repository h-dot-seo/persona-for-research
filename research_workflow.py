"""Apply operator-curated paper observations as a bounded research planning scaffold."""
import argparse
import copy
import json
from pathlib import Path
from persona import payload_sha256, validate
from methodology_trajectory import summarize
from reasoning_cards import card, validate_components
from verification_receipt import VerifiedCorpus
from evidence_coverage import coverage
from corpus_projection import runtime_papers
from strict_json import load


def build(corpus):
    verified = isinstance(corpus, VerifiedCorpus)
    if verified and not corpus.unchanged():
        raise ValueError('verified corpus changed after intake; verify again')
    papers = runtime_papers(corpus)
    author = corpus['author_id']
    for paper in papers:
        paper['source_verification'] = ('LOCAL_BYTES_SHA256_MATCH'
            if verified and paper.get('paper_id') in corpus.local_source_ids else 'NOT_PERFORMED')
        for observation in paper['observations']:
            observation['evidence_verification'] = 'EXACT_QUOTE_MATCH_ONLY' if verified else 'NOT_PERFORMED'
            components = observation.get('reasoning', {})
            validate_components(components)
            for component in components.values():
                component['evidence_verification'] = 'EXACT_QUOTE_MATCH_ONLY' if verified else 'NOT_PERFORMED'
    if not papers:
        raise ValueError('at least one authorized training paper is required')
    rules = []
    trajectory = []
    for paper in papers:
        if paper.get('authorized') is not True:
            raise ValueError('source authorization required')
        if paper.get('kind') not in ('research', 'review') or type(paper.get('year')) is not int:
            raise ValueError('paper kind and integer year required')
        trajectory.append(dict(paper_id=paper['paper_id'], year=paper['year'], kind=paper['kind'], topic=paper['topic']))
        for observation in paper['observations']:
            required = ('method', 'condition', 'limitation', 'locator', 'topic')
            if any(not isinstance(observation.get(k), str) or not observation[k].strip() for k in required):
                raise ValueError('observation needs method, condition, limitation, locator and topic')
            rules.append(dict(rule_id=f'rule-{len(rules)+1}', **{k: observation[k] for k in required},
                              stance=observation.get('stance', 'support'),
                              source_kind=paper['kind'], year=paper['year'],
                              claim_type=observation.get('claim_type', 'operator_interpretation'),
                              evidence_quote=observation.get('evidence_quote'),
                              evidence_verification=observation.get('evidence_verification', 'NOT_PERFORMED'),
                              paper_id=paper['paper_id'], evidence_type='operator_curated_paper_observation',
                              attribution='coauthored work; individual ownership not established'))
            if rules[-1]['stance'] not in ('support', 'challenge'):
                raise ValueError('observation stance must be support or challenge')
            if 'reasoning' in observation:
                validate_components(observation['reasoning'])
                rules[-1]['reasoning'] = copy.deepcopy(observation['reasoning'])
    persona = dict(author_id=author, version=corpus['version'], build_id=corpus['build_id'],
                   identity=dict(simulation_only=True, private_beliefs_inferred=False),
                   knowledge_papers_sha256=payload_sha256(papers),
                   rules=rules, trajectory=sorted(trajectory, key=lambda r: (r['year'], r['paper_id'])),
                   semantic_validation='NOT_PERFORMED')
    knowledge = dict(author_id=author, version=corpus['version'], build_id=corpus['build_id'],
                     persona_payload_sha256=payload_sha256(persona), papers=papers)
    errors = validate(persona, knowledge)
    if errors:
        raise ValueError('; '.join(errors))
    return dict(persona=persona, knowledge=knowledge)


def validated_source_rules(package):
    """Check runtime rule/source agreement; hashes and recorded labels are not signatures.

    Call after package hash/authorization validation. Rebuild structural rules from
    source observations, then restore only supported recorded quote labels. This
    does not reopen sources or manufacture a current verification receipt.
    """
    persona = package['persona']
    corpus = {key: persona[key] for key in ('author_id', 'version', 'build_id')}
    corpus['papers'] = package['knowledge']['papers']
    papers = runtime_papers(corpus)
    expected = build(corpus)['persona']['rules']
    records = [(paper, obs) for paper in papers for obs in paper['observations']]
    for paper in papers:
        if paper.get('source_verification', 'NOT_PERFORMED') not in ('NOT_PERFORMED', 'LOCAL_BYTES_SHA256_MATCH'):
            raise ValueError('unsupported recorded source verification label')
    for rule, (paper, obs) in zip(expected, records):
        label = obs.get('evidence_verification', 'NOT_PERFORMED')
        if label not in ('NOT_PERFORMED', 'EXACT_QUOTE_MATCH_ONLY'):
            raise ValueError('unsupported recorded quote verification label')
        rule['evidence_verification'] = label
        for dimension, component in obs.get('reasoning', {}).items():
            label = component.get('evidence_verification', 'NOT_PERFORMED')
            if label not in ('NOT_PERFORMED', 'EXACT_QUOTE_MATCH_ONLY'):
                raise ValueError('unsupported recorded quote verification label')
            rule['reasoning'][dimension]['evidence_verification'] = label
    if payload_sha256(persona.get('rules')) != payload_sha256(expected):
        raise ValueError('persona rules do not match the bound source observations and recorded checks')
    return papers


def apply(package, question, topic):
    if not question.strip() or not topic.strip():
        raise ValueError('question and explicit topic required')
    persona, knowledge = package['persona'], package['knowledge']
    errors = validate(persona, knowledge)
    if errors:
        raise ValueError('; '.join(errors))
    source_papers = validated_source_rules(package)
    trajectory = sorted([{key: paper[key] for key in ('paper_id', 'year', 'kind', 'topic')}
                         for paper in source_papers], key=lambda row: (row['year'], row['paper_id']))
    known = {p['paper_id']: p for p in knowledge['papers']}
    steps = []
    patterns = {}
    for rule in persona['rules']:
        if rule['paper_id'] not in known:
            raise ValueError('unbound rule evidence')
        if rule['topic'].casefold() == topic.casefold():
            key = (rule['method'], rule['condition'])
            pattern = patterns.setdefault(key, dict(method=rule['method'], condition=rule['condition'], supporting=[], challenging=[]))
            pattern['supporting' if rule.get('stance', 'support') == 'support' else 'challenging'].append(
                dict(paper_id=rule['paper_id'], locator=rule['locator'], year=rule.get('year'),
                     source_kind=rule.get('source_kind'), source_sha256=known[rule['paper_id']]['source_sha256']))
            steps.append(dict(rule_id=rule['rule_id'], paper_id=rule['paper_id'], locator=rule['locator'],
                              planning_prompt=f"For {question}: {'challenge' if rule.get('stance') == 'challenge' else 'consider'} {rule['method']}",
                              evidence_stance=rule.get('stance', 'support'),
                              claim_type=rule.get('claim_type', 'operator_interpretation'),
                              evidence_quote=rule.get('evidence_quote'),
                              evidence_verification=rule.get('evidence_verification', 'NOT_PERFORMED'),
                              applicability_to_check=rule['condition'], limitation=rule['limitation'],
                              status='SYSTEM_INFERENCE_REQUIRES_REVIEW'))
    for pattern in patterns.values():
        pattern['distinct_source_hash_count'] = len({r['source_sha256']
            for r in pattern['supporting'] + pattern['challenging']})
        if not pattern['supporting']:
            pattern['classification'] = 'CHALLENGE_ONLY'
        elif pattern['challenging']:
            pattern['classification'] = 'CONTESTED'
        elif len({r['paper_id'] for r in pattern['supporting']}) == 1:
            pattern['classification'] = 'SINGLE_PAPER_OBSERVATION'
        elif pattern['distinct_source_hash_count'] == 1:
            pattern['classification'] = 'MULTIPLE_RECORDS_SAME_SOURCE_HASH'
        else:
            pattern['classification'] = 'REPEATED_OBSERVATION'
        pattern['inference_boundary'] = ('Exact method/condition grouping; no claim of author-specific or causal validity. '
            'Identical hashes flag shared source content; different hashes do not establish independent publications or replication.')
    return dict(question=question, status='PLANNING_SCAFFOLD' if steps else 'OUTSIDE_PERSONA_COVERAGE',
                simulation_only=True, steps=steps, patterns=list(patterns.values()), trajectory=trajectory,
                methodology_trajectory=summarize([rule for rule in persona['rules']
                    if rule['topic'].casefold() == topic.casefold()]),
                reasoning_cards=[result for rule in persona['rules']
                    if rule['topic'].casefold() == topic.casefold()
                    for result in [card(rule)] if result is not None],
                evidence_coverage=coverage([rule for rule in persona['rules']
                    if rule['topic'].casefold() == topic.casefold()]),
                processing=dict(mode='DETERMINISTIC_OPERATOR_CURATED', llm_used=False,
                                automatic_extraction=False),
                semantic_validation='NOT_PERFORMED')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('corpus', type=Path); p.add_argument('--question', required=True); p.add_argument('--topic', required=True)
    a = p.parse_args()
    try:
        package = build(load(a.corpus))
        result = dict(package=package, application=apply(package, a.question, a.topic))
    except (ValueError, OSError, KeyError, TypeError) as e:
        p.exit(1, str(e) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
