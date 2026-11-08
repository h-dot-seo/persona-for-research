"""Audit publication-year scope of an operator proposal without historical inference."""
import argparse
import copy
import json
import sys
from pathlib import Path

from design_scenario import review as review_design, render as render_design
from persona import payload_sha256
from review_package import display
from strict_json import load

BOUNDARY = ('This compares supplied publication years with an explicit reference year only. '
    'Before-year records are not proof of access, influence, author ownership or scientific validity. '
    'Same-year ordering and actual availability are unresolved; later publication does not prove '
    'the idea was unavailable earlier. No question dates are inferred. A review may report other '
    "people's work; research/review labels do not establish who originated a claim. "
    'An entire link is used by a proposal, so both endpoints are checked, irrespective of role or '
    'edge direction. Nothing is filtered, approved, repaired or automatically substituted. '
    'Unreferenced links remain visible, without claiming relevance or corpus completeness. '
    'All links and proposals remain operator interpretations, separate from source claim labels. '
    'No LLM, source reread, external call or historical/scientific validation is performed.')


def audit(package, links, proposal, reference_year):
    if type(reference_year) is not int or not 1 <= reference_year <= 9999:
        raise ValueError('reference_year must be an integer from 1 to 9999')
    design = review_design(package, links, proposal)
    evidence = {}
    for link in design['evidence_links']['links']:
        endpoints = []
        for direction in ('from', 'to'):
            node = link[direction + '_evidence']
            year = node['publication_year']
            if type(year) is not int or not 1 <= year <= 9999:
                raise ValueError('endpoint publication year must be an integer from 1 to 9999')
            scope = ('AFTER_REFERENCE_YEAR' if year > reference_year else
                     'SAME_YEAR_ORDER_UNRESOLVED' if year == reference_year else
                     'BEFORE_REFERENCE_YEAR')
            endpoints.append(dict(direction=direction, publication_scope=scope,
                                  evidence=copy.deepcopy(node)))
        evidence[link['link_id']] = dict(link_id=link['link_id'], relation=link['relation'],
            claim_type=link['claim_type'], same_source_hash=link['same_source_hash'], endpoints=endpoints)
    steps = []
    for step in design['steps']:
        uses = []
        for use in step['link_uses']:
            uses.append(dict(**copy.deepcopy(use), evidence=copy.deepcopy(evidence[use['link_id']])))
        scopes = {node['publication_scope'] for use in uses for node in use['evidence']['endpoints']}
        status = ('NO_LINKED_EVIDENCE_SUPPLIED' if not uses else
                  'AFTER_REFERENCE_YEAR_LINK_USED' if 'AFTER_REFERENCE_YEAR' in scopes else
                  'SAME_YEAR_ORDER_UNRESOLVED' if 'SAME_YEAR_ORDER_UNRESOLVED' in scopes else
                  'NO_LATER_LINK_ENDPOINTS')
        steps.append(dict(step_id=step['step_id'], claim_type='operator_proposal', status=status,
            missing_proposal_fields=copy.deepcopy(step['missing_fields']), link_uses=uses))
    request = dict(proposal_sha256=design['proposal_sha256'], reference_year=reference_year,
                   policy='PUBLICATION_YEAR_COMPARISON_V1')
    return dict(status='PUBLICATION_SCOPE_REQUIRES_REVIEW', **request,
        scope_request_sha256=payload_sha256(request),
        persona_sha256=design['persona_sha256'], knowledge_papers_sha256=design['knowledge_papers_sha256'],
        link_artifact_sha256=design['link_artifact_sha256'], steps=steps,
        unreferenced_links=[copy.deepcopy(evidence[key]) for key in design['unreferenced_link_ids']],
        design=design, historical_validation='NOT_PERFORMED', semantic_validation='NOT_PERFORMED',
        llm_used=False, canonical_update_performed=False, boundary=BOUNDARY)


def render(package, links, proposal, reference_year):
    result = audit(package, links, proposal, reference_year)
    lines = ['Publication-year scope review', 'Status: ' + result['status'],
             'Reference year: ' + str(reference_year),
             'Scope request sha256: ' + result['scope_request_sha256']]
    def append_link(link):
        lines.append('  Link ' + display(link['link_id']) + ': ' + link['relation'] + ' [operator_interpretation]')
        for node in link['endpoints']:
            ev = node['evidence']; ref = ev['reference']
            lines.append('    ' + node['direction'] + ': ' + display(ref['paper_id']) +
                ' / observation ' + str(ref['observation_index']) + ' / ' + display(ref['dimension']) +
                ' | ' + str(ev['publication_year']) + ' [' + ev['source_kind'] + '] | ' + node['publication_scope'])
    for step in result['steps']:
        lines.append('Step ' + display(step['step_id']) + ' [operator_proposal]: ' + step['status'])
        lines.append('  Missing proposal fields: ' + (', '.join(step['missing_proposal_fields']) or 'none (not scientific validation)'))
        for use in step['link_uses']:
            lines.append('  Proposed use: ' + use['role'] + ' | ' + display(use['applicability_note']))
            append_link(use['evidence'])
    lines.append('Unreferenced supplied links (not filtered):')
    for link in result['unreferenced_links']:
        append_link(link)
    lines.append('Scope boundary: ' + BOUNDARY)
    lines.append('Complete design and evidence, including claim labels, quotes and source locators:')
    lines.append(render_design(package, links, proposal).rstrip('\n'))
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package', type=Path)
    parser.add_argument('links', type=Path)
    parser.add_argument('proposal', type=Path)
    parser.add_argument('--reference-year', required=True, type=int)
    parser.add_argument('--format', choices=('json', 'text'), default='json')
    args = parser.parse_args()
    try:
        inputs = (load(args.package), load(args.links), load(args.proposal), args.reference_year)
        output = render(*inputs) if args.format == 'text' else json.dumps(audit(*inputs), indent=2) + '\n'
    except (ValueError, OSError, KeyError, TypeError, AttributeError) as exc:
        parser.exit(1, str(exc) + '\n')
    sys.stdout.buffer.write(output.encode('utf-8'))


if __name__ == '__main__':
    main()
