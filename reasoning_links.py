"""Review explicitly supplied cross-publication links, never infer author reasoning."""
import argparse
import copy
import json
import sys
from pathlib import Path

from compare_releases import checked_package
from persona import payload_sha256
from reasoning_cards import DIMENSIONS
from research_workflow import validated_source_rules
from review_package import display
from strict_json import load

RELATIONS = ('supports', 'challenges', 'qualifies', 'contrasts')
LINK_KEYS = {'link_id', 'relation', 'from_ref', 'to_ref', 'rationale', 'claim_type'}
REF_KEYS = {'paper_id', 'observation_index', 'dimension'}
BOUNDARY = ('Links are supplied operator interpretations, not author-attributed claims, '
    'semantic verification, causal history or a reconstructed private reasoning process. '
    'Source claim labels remain separate. Publication order does not date intellectual '
    'influence, and different hashes do not establish independence. No implicit, transitive '
    'or missing links are inferred. Recorded quote/byte checks are not rechecked here. '
    'Supports/challenges/qualifies read from→to; contrast is a comparison, not causation. '
    'Cross-topic or backward-year links do not establish transferability or change of mind. '
    'Operator identity is a recorded declaration, not authenticated human review. '
    'No LLM, external transmission or canonical update is performed.')


def _sources(value):
    package = checked_package(value)
    return package, {paper['paper_id']: paper for paper in validated_source_rules(package)}


def template(value, operator_id):
    package, _ = _sources(value)
    _operator(operator_id)
    return dict(persona_sha256=payload_sha256(package['persona']),
                knowledge_papers_sha256=payload_sha256(package['knowledge']['papers']),
                operator_id=operator_id, links=[])


def _operator(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 128:
        raise ValueError('operator_id must be a bounded nonempty recorded identifier')


def _endpoint(ref, papers):
    if not isinstance(ref, dict) or set(ref) != REF_KEYS:
        raise ValueError('endpoint must contain only paper_id, observation_index and dimension')
    paper_id, index, dimension = ref['paper_id'], ref['observation_index'], ref['dimension']
    if not isinstance(paper_id, str) or paper_id not in papers:
        raise ValueError('unknown endpoint paper')
    paper = papers[paper_id]
    if type(index) is not int or not 0 <= index < len(paper['observations']):
        raise ValueError('endpoint observation index is invalid')
    obs = paper['observations'][index]
    if dimension is not None and (dimension not in DIMENSIONS or dimension not in obs.get('reasoning', {})):
        raise ValueError('endpoint reasoning dimension is unknown or missing')
    return dict(reference=copy.deepcopy(ref), publication_year=paper['year'], source_kind=paper['kind'],
        source_sha256=paper['source_sha256'], source_locator=paper['locator'],
        recorded_source_check=paper.get('source_verification', 'NOT_PERFORMED'),
        observation={key: copy.deepcopy(obs.get(key, default)) for key, default in (
            ('method', None), ('condition', None), ('limitation', None), ('locator', None), ('topic', None),
            ('stance', 'support'), ('claim_type', 'operator_interpretation'), ('evidence_quote', None),
            ('evidence_verification', 'NOT_PERFORMED'))},
        component=copy.deepcopy(obs['reasoning'][dimension]) if dimension is not None else None,
        attribution='coauthored work; individual ownership not established')


def review(value, supplied):
    package, papers = _sources(value)
    if not isinstance(supplied, dict) or set(supplied) != {'persona_sha256', 'knowledge_papers_sha256', 'operator_id', 'links'}:
        raise ValueError('link artifact must contain only package bindings, operator_id and links')
    _operator(supplied['operator_id'])
    bindings = dict(persona_sha256=payload_sha256(package['persona']),
                    knowledge_papers_sha256=payload_sha256(package['knowledge']['papers']))
    if any(supplied[key] != digest for key, digest in bindings.items()):
        raise ValueError('links are bound to a different package; re-review references')
    if not isinstance(supplied['links'], list):
        raise ValueError('links must be an array')
    ids, edges, result = set(), set(), []
    for link in supplied['links']:
        if not isinstance(link, dict) or set(link) != LINK_KEYS:
            raise ValueError('link has missing or unknown fields')
        for key, maximum in (('link_id', 128), ('rationale', 2000)):
            if not isinstance(link[key], str) or not link[key].strip() or len(link[key]) > maximum:
                raise ValueError('link ID and rationale must be bounded nonempty strings')
        if link['link_id'] in ids:
            raise ValueError('duplicate link ID')
        ids.add(link['link_id'])
        if link['relation'] not in RELATIONS or link['claim_type'] != 'operator_interpretation':
            raise ValueError('link needs a supported relation and operator_interpretation claim type')
        left, right = _endpoint(link['from_ref'], papers), _endpoint(link['to_ref'], papers)
        endpoints = [payload_sha256(link['from_ref']), payload_sha256(link['to_ref'])]
        if endpoints[0] == endpoints[1]:
            raise ValueError('self-links do not compare distinct evidence records')
        if link['relation'] == 'contrasts':
            endpoints.sort()
        key = (link['relation'], *endpoints)
        if key in edges:
            raise ValueError('duplicate relation between the same endpoints')
        edges.add(key)
        result.append(dict(link_id=link['link_id'], relation=link['relation'],
            rationale=link['rationale'], claim_type='operator_interpretation',
            from_evidence=left, to_evidence=right,
            same_source_hash=left['source_sha256'] == right['source_sha256'],
            status='OPERATOR_LINK_REQUIRES_REVIEW'))
    persona = package['persona']
    return dict(status='LINKS_REQUIRE_REVIEW' if result else 'NO_SUPPLIED_LINKS',
        author_id=persona['author_id'], version=persona['version'], build_id=persona['build_id'],
        **bindings, link_artifact_sha256=payload_sha256(supplied), links=result,
        operator_id=supplied['operator_id'], operator_identity='RECORDED_NOT_AUTHENTICATED',
        semantic_validation='NOT_PERFORMED', canonical_update_performed=False, llm_used=False,
        boundary=BOUNDARY)


def render(value, supplied):
    result = review(value, supplied)
    lines = ['Supplied reasoning links | ' + display(result['author_id']),
        'Package: ' + display(result['version']) + ' | ' + display(result['build_id']),
        'Status: ' + result['status'], 'Persona sha256: ' + result['persona_sha256'],
        'Declared operator: ' + display(result['operator_id']) + ' (not authenticated)',
        'Knowledge papers sha256: ' + result['knowledge_papers_sha256'],
        'Link artifact sha256: ' + result['link_artifact_sha256']]
    for link in result['links']:
        lines.append(f"Link {display(link['link_id'])}: {link['relation']} [operator_interpretation]")
        lines.append('  Rationale: ' + display(link['rationale']))
        lines.append('  Same supplied source hash: ' + str(link['same_source_hash']))
        for role in ('from', 'to'):
            node = link[role + '_evidence']; ref = node['reference']; obs = node['observation']
            lines.append(f"  {role}: {display(ref['paper_id'])} / observation {ref['observation_index']} / "
                         f"{display(ref['dimension'])} | {node['publication_year']} [{node['source_kind']}]")
            lines.append(f"    Source: {display(node['source_locator'])}; sha256={node['source_sha256']}; "
                         f"recorded check={node['recorded_source_check']}")
            lines.append(f"    Observation [{obs['stance']}; {obs['claim_type']}]: "
                         f"{display(obs['method'])} | {display(obs['locator'])}")
            lines.append('    Topic: ' + display(obs['topic']))
            lines.append('    Condition: ' + display(obs['condition']) + '; limitation: ' + display(obs['limitation']))
            lines.append('    Supplied quote: ' + display(obs['evidence_quote']) + '; recorded check=' + obs['evidence_verification'])
            component = node['component']
            if component is not None:
                lines.append(f"    Component [{component['claim_type']}]: {display(component['text'])} | {display(component['locator'])}")
                lines.append('    Component quote: ' + display(component['evidence_quote']) +
                             '; recorded check=' + component.get('evidence_verification', 'NOT_PERFORMED'))
                if 'origin' in component:
                    lines.append('    Component origin: ' + display(component['origin']) +
                                 '; proposed=' + display(component['proposed_claim_type']))
    lines.append('Boundary: ' + BOUNDARY)
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package', type=Path)
    parser.add_argument('links', type=Path, nargs='?')
    parser.add_argument('--template', action='store_true')
    parser.add_argument('--operator-id')
    parser.add_argument('--format', choices=('json', 'text'), default='json')
    args = parser.parse_args()
    try:
        value = load(args.package)
        if args.template:
            if args.links is not None or args.format != 'json':
                raise ValueError('template requires no links file and JSON output')
            output = json.dumps(template(value, args.operator_id), indent=2) + '\n'
        else:
            if args.links is None or args.operator_id is not None:
                raise ValueError('supply an explicit links artifact or request an empty template')
            supplied = load(args.links)
            output = render(value, supplied) if args.format == 'text' else json.dumps(review(value, supplied), indent=2) + '\n'
    except (ValueError, OSError, KeyError, TypeError, AttributeError) as exc:
        parser.exit(1, str(exc) + '\n')
    sys.stdout.buffer.write(output.encode('utf-8'))


if __name__ == '__main__':
    main()
