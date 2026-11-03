"""Discover existing exact-topic scopes without semantic merging or ranking."""
import argparse
import json
import sys
from pathlib import Path

from compare_releases import checked_package
from persona import payload_sha256
from reasoning_cards import DIMENSIONS
from research_workflow import validated_source_rules
from review_package import display
from strict_json import load


def inventory(value):
    package = checked_package(value)
    papers = validated_source_rules(package)
    groups = {}
    for paper in papers:
        for index, obs in enumerate(paper['observations']):
            key = obs['topic'].casefold()
            group = groups.setdefault(key, dict(labels=set(), papers={}, observations=[]))
            group['labels'].add(obs['topic'])
            group['papers'][paper['paper_id']] = paper
            group['observations'].append((paper['paper_id'], index, obs))
    topics = []
    for key, group in sorted(groups.items()):
        sources = list(group['papers'].values())
        observations = group['observations']
        component_counts = {dimension: sum(dimension in obs.get('reasoning', {})
            for _, _, obs in observations) for dimension in DIMENSIONS}
        topics.append(dict(topic=key, original_labels=sorted(group['labels']),
            publication_years=sorted({p['year'] for p in sources}),
            paper_ids_by_kind={kind: sorted(p['paper_id'] for p in sources if p['kind'] == kind)
                               for kind in ('research', 'review')},
            supplied_source_hash_count=len({p['source_sha256'] for p in sources}),
            observation_count=len(observations),
            observation_refs=[dict(paper_id=paper_id, observation_index=index, locator=obs['locator'],
                stance=obs.get('stance', 'support'), claim_type=obs.get('claim_type', 'operator_interpretation'),
                supplied_dimensions=[d for d in DIMENSIONS if d in obs.get('reasoning', {})])
                for paper_id, index, obs in sorted(observations, key=lambda row: (row[0], row[1]))],
            stance_counts={stance: sum(obs.get('stance', 'support') == stance for _, _, obs in observations)
                           for stance in ('support', 'challenge')},
            claim_type_counts={claim: sum(obs.get('claim_type', 'operator_interpretation') == claim
                for _, _, obs in observations) for claim in ('explicit_statement', 'operator_interpretation')},
            supplied_component_counts=component_counts,
            missing_dimensions=[dimension for dimension in DIMENSIONS if component_counts[dimension] == 0]))
    persona = package['persona']
    return dict(status='TOPIC_INVENTORY_ONLY' if topics else 'NO_OBSERVATION_TOPICS',
        author_id=persona['author_id'], version=persona['version'], build_id=persona['build_id'],
        persona_sha256=payload_sha256(persona),
        knowledge_papers_sha256=payload_sha256(package['knowledge']['papers']), topics=topics,
        topic_matching='EXACT_CASE_INSENSITIVE', selection_performed=False,
        semantic_validation='NOT_PERFORMED', llm_used=False, canonical_update_performed=False,
        boundary='Topics come from source observations, not paper-level labels or inferred interests. '
                 'Casefold-equivalent labels are grouped; no semantic merging, ranking or recommendation '
                 'is performed. Counts describe supplied records, not quality, confidence, independent '
                 'publications or researcher fidelity. Publication years do not date decisions or career '
                 'stages. Observation indexes are zero-based and bound to these package hashes.')


def render(value):
    result = inventory(value)
    lines = ['Available exact-topic scopes', 'Status: ' + result['status'],
             'Package: ' + ' | '.join(display(result[key]) for key in ('author_id', 'version', 'build_id')),
             'Persona sha256: ' + result['persona_sha256'],
             'Knowledge papers sha256: ' + result['knowledge_papers_sha256']]
    for row in result['topics']:
        lines.append('Topic: ' + display(json.dumps(row['topic'], ensure_ascii=False)))
        lines.append('  Supplied labels: ' + display(json.dumps(row['original_labels'], ensure_ascii=False)))
        lines.append('  Publication years: ' + ', '.join(map(str, row['publication_years'])))
        for kind, ids in row['paper_ids_by_kind'].items():
            lines.append('  ' + kind + ' paper IDs: ' + ', '.join(display(i) for i in ids))
        lines.append(f"  Observations: {row['observation_count']}; support={row['stance_counts']['support']}; "
                     f"challenge={row['stance_counts']['challenge']}; source hashes={row['supplied_source_hash_count']}")
        lines.append(f"  Observation claim labels: explicit_statement={row['claim_type_counts']['explicit_statement']}; "
                     f"operator_interpretation={row['claim_type_counts']['operator_interpretation']}")
        lines.append('  Supplied components: ' + ', '.join(f'{key}={count}' for key, count in row['supplied_component_counts'].items()))
    lines.append('Boundary: ' + result['boundary'])
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package', type=Path)
    parser.add_argument('--format', choices=('json', 'text'), default='json')
    args = parser.parse_args()
    try:
        value = load(args.package)
        output = render(value) if args.format == 'text' else json.dumps(inventory(value), indent=2) + '\n'
    except (ValueError, OSError, KeyError, TypeError, AttributeError) as exc:
        parser.exit(1, str(exc) + '\n')
    sys.stdout.buffer.write(output.encode('utf-8'))


if __name__ == '__main__':
    main()
