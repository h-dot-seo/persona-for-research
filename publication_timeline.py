"""Review publication-dated question and method records, without career inference."""
import argparse
import copy
import json
import sys
from pathlib import Path

from compare_releases import checked_package
from corpus_projection import runtime_papers
from persona import payload_sha256
from reasoning_cards import DIMENSIONS
from research_workflow import build
from review_package import display
from strict_json import load

BOUNDARY = ('Publication years order supplied records, not research decisions or career stages. '
    'Within-year ordering is by identifier, not event time. '
    'Missing years are not inactivity, later records do not supersede earlier ones, and '
    'review articles are not independent replication. Claim types are recorded declarations; '
    'coauthored work does not establish individual ownership or private beliefs. Recorded '
    'quote/byte checks are not rechecked here. No semantic support or researcher fidelity '
    'is established. No LLM, external transmission or canonical update is performed.')


def _without_quote_labels(value):
    if isinstance(value, dict):
        return {key: _without_quote_labels(item) for key, item in value.items()
                if key != 'evidence_verification'}
    if isinstance(value, list):
        return [_without_quote_labels(item) for item in value]
    return value


def _check_label(value, verified):
    if not isinstance(value, str) or value not in ('NOT_PERFORMED', verified):
        raise ValueError('unsupported recorded verification label')
    return value


def timeline(value, topic):
    package = checked_package(value)
    if not isinstance(topic, str) or not topic.strip():
        raise ValueError('an explicit nonempty topic is required')
    persona = package['persona']
    corpus = {key: persona[key] for key in ('author_id', 'version', 'build_id')}
    corpus['papers'] = package['knowledge']['papers']
    papers = runtime_papers(corpus)
    rebuilt = build(corpus)  # Validate source observations, without inventing a verification receipt.
    if payload_sha256(_without_quote_labels(persona.get('rules'))) != payload_sha256(
            _without_quote_labels(rebuilt['persona']['rules'])):
        raise ValueError('persona rules do not match the bound source observations')
    years = {}
    matching_papers = []
    for paper in sorted(papers, key=lambda p: (p['year'], p['paper_id'])):
        _check_label(paper.get('source_verification', 'NOT_PERFORMED'), 'LOCAL_BYTES_SHA256_MATCH')
        observations = []
        for index, obs in enumerate(paper['observations']):
            _check_label(obs.get('evidence_verification', 'NOT_PERFORMED'), 'EXACT_QUOTE_MATCH_ONLY')
            for component in obs.get('reasoning', {}).values():
                _check_label(component.get('evidence_verification', 'NOT_PERFORMED'), 'EXACT_QUOTE_MATCH_ONLY')
            if obs['topic'].casefold() != topic.casefold():
                continue
            components = copy.deepcopy(obs.get('reasoning', {}))
            observations.append(dict(observation_index=index,
                method=obs['method'], condition=obs['condition'], limitation=obs['limitation'],
                topic=obs['topic'], locator=obs['locator'], stance=obs.get('stance', 'support'),
                claim_type=obs.get('claim_type', 'operator_interpretation'),
                evidence_quote=obs.get('evidence_quote'),
                recorded_quote_check=obs.get('evidence_verification', 'NOT_PERFORMED'),
                reasoning=components, missing_dimensions=[d for d in DIMENSIONS if d not in components]))
        if observations:
            row = dict(paper_id=paper['paper_id'], source_kind=paper['kind'],
                source_sha256=paper['source_sha256'], source_locator=paper['locator'],
                recorded_source_check=_check_label(paper.get('source_verification', 'NOT_PERFORMED'), 'LOCAL_BYTES_SHA256_MATCH'),
                observations=observations,
                attribution='coauthored work; individual ownership not established')
            years.setdefault(paper['year'], []).append(row)
            matching_papers.append(paper)
    return dict(status='PUBLICATION_TIMELINE_REQUIRES_REVIEW' if years else 'NO_MATCHING_RECORDS',
        author_id=persona['author_id'], version=persona['version'], build_id=persona['build_id'],
        persona_sha256=payload_sha256(persona), knowledge_papers_sha256=payload_sha256(corpus['papers']),
        topic=topic, topic_matching='EXACT_CASE_INSENSITIVE',
        paper_count=len(matching_papers),
        missing_dimensions=[dimension for dimension in DIMENSIONS if not any(
            dimension in obs['reasoning'] for rows in years.values() for paper in rows for obs in paper['observations'])],
        supplied_source_hash_count=len({p['source_sha256'] for p in matching_papers}),
        years=[dict(publication_year=year, papers=years[year]) for year in sorted(years)],
        semantic_validation='NOT_PERFORMED', canonical_update_performed=False, llm_used=False,
        boundary=BOUNDARY)


def render(value, topic):
    result = timeline(value, topic)
    lines = ['Publication record timeline | ' + display(result['topic']),
        'Package: ' + ' | '.join(display(result[key]) for key in ('author_id', 'version', 'build_id')),
        'Persona sha256: ' + result['persona_sha256'],
        'Knowledge papers sha256: ' + result['knowledge_papers_sha256'],
        'Status: ' + result['status'],
        f"Evidence: {result['paper_count']} paper IDs; {result['supplied_source_hash_count']} supplied source hashes"]
    for year in result['years']:
        lines.append('Publication year: ' + str(year['publication_year']))
        for paper in year['papers']:
            lines.append(f"  {display(paper['paper_id'])} [{display(paper['source_kind'])}] | "
                         f"{display(paper['source_locator'])} | sha256={paper['source_sha256']}")
            lines.append('    recorded source check: ' + paper['recorded_source_check'])
            for obs in paper['observations']:
                lines.append(f"    Observation {obs['observation_index']} [{display(obs['stance'])}; "
                             f"{display(obs['claim_type'])}] | {display(obs['locator'])}")
                for key in ('method', 'condition', 'limitation'):
                    lines.append(f'      {key}: ' + display(obs[key]))
                lines.append('      supplied quote: ' + display(obs['evidence_quote']))
                lines.append('      recorded quote check: ' + obs['recorded_quote_check'])
                for dimension, component in obs['reasoning'].items():
                    lines.append(f"      {display(dimension)} [{display(component['claim_type'])}]: "
                                 f"{display(component['text'])} | {display(component['locator'])}")
                    lines.append('        supplied quote: ' + display(component['evidence_quote']))
                    lines.append('        recorded quote check: ' + component.get('evidence_verification', 'NOT_PERFORMED'))
                    if 'origin' in component:
                        lines.append(f"        origin={display(component['origin'])}; "
                                     f"proposed={display(component['proposed_claim_type'])}")
                lines.append('      missing supplied dimensions: ' + ', '.join(obs['missing_dimensions']))
    lines.append('Overall missing supplied dimensions: ' + (', '.join(result['missing_dimensions']) or 'none (coverage only)'))
    lines.append('Boundary: ' + BOUNDARY)
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package', type=Path)
    parser.add_argument('--topic', required=True)
    parser.add_argument('--format', choices=('json', 'text'), default='json')
    args = parser.parse_args()
    try:
        value = load(args.package)
        output = render(value, args.topic) if args.format == 'text' else json.dumps(timeline(value, args.topic), indent=2) + '\n'
    except (ValueError, OSError, KeyError, TypeError, AttributeError) as exc:
        parser.exit(1, str(exc) + '\n')
    sys.stdout.buffer.write(output.encode('utf-8'))


if __name__ == '__main__':
    main()
