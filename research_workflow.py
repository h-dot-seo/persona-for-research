"""Apply operator-curated paper observations as a bounded research planning scaffold."""
import argparse
import json
from pathlib import Path
from persona import payload_sha256, validate


def build(corpus):
    author = corpus['author_id']
    papers = corpus['papers']
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
                              paper_id=paper['paper_id'], evidence_type='operator_curated_paper_observation',
                              attribution='coauthored work; individual ownership not established'))
    persona = dict(author_id=author, version=corpus['version'], build_id=corpus['build_id'],
                   identity=dict(simulation_only=True, private_beliefs_inferred=False),
                   rules=rules, trajectory=sorted(trajectory, key=lambda r: (r['year'], r['paper_id'])),
                   semantic_validation='NOT_PERFORMED')
    knowledge = dict(author_id=author, version=corpus['version'], build_id=corpus['build_id'],
                     persona_payload_sha256=payload_sha256(persona), papers=papers)
    errors = validate(persona, knowledge)
    if errors:
        raise ValueError('; '.join(errors))
    return dict(persona=persona, knowledge=knowledge)


def apply(package, question, topic):
    if not question.strip() or not topic.strip():
        raise ValueError('question and explicit topic required')
    persona, knowledge = package['persona'], package['knowledge']
    errors = validate(persona, knowledge)
    if errors:
        raise ValueError('; '.join(errors))
    known = {p['paper_id'] for p in knowledge['papers']}
    steps = []
    for rule in persona['rules']:
        if rule['paper_id'] not in known:
            raise ValueError('unbound rule evidence')
        if rule['topic'].casefold() == topic.casefold():
            steps.append(dict(rule_id=rule['rule_id'], paper_id=rule['paper_id'], locator=rule['locator'],
                              planning_prompt=f"For {question}: consider {rule['method']}",
                              applicability_to_check=rule['condition'], limitation=rule['limitation'],
                              status='SYSTEM_INFERENCE_REQUIRES_REVIEW'))
    return dict(question=question, status='PLANNING_SCAFFOLD' if steps else 'OUTSIDE_PERSONA_COVERAGE',
                simulation_only=True, steps=steps, trajectory=persona['trajectory'],
                semantic_validation='NOT_PERFORMED')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('corpus', type=Path); p.add_argument('--question', required=True); p.add_argument('--topic', required=True)
    a = p.parse_args()
    try:
        package = build(json.loads(a.corpus.read_text(encoding='utf-8')))
        result = dict(package=package, application=apply(package, a.question, a.topic))
    except (ValueError, OSError, KeyError, TypeError) as e:
        p.exit(1, str(e) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
