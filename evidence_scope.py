"""Disclose actual answer/design evidence scope without scoring researcher fidelity."""
import argparse
import copy
import json
import sys
from pathlib import Path

from reasoning_links import _sources
from review_journey import assemble
from review_package import display
from strict_json import load

BOUNDARY = ('Counts describe supplied authorized records, not independent studies, literature '
    'coverage, answer correctness or researcher fidelity. Equal supplied hashes are grouped to '
    'expose repeated source representations, not to deduplicate or authenticate publications. '
    'Different hashes do not prove independence. Only citations in answer claims and links used '
    'by design steps count as active use; unused supplied links are disclosed separately. '
    'All draft claims count, including rejected or deferred ones; this is not an approved-answer '
    'selection. A selected component does not establish use of every component in its observation. '
    'Curated records have unauthenticated origin; candidate-origin markers and imported model/provider '
    'identities are declarations, '
    'not proof of actual AI use or human review. Checks are recorded statuses, not repeated here. '
    'Research/review labels and explicit statements do not establish individual author ownership. '
    'Publication-year comparisons do not establish availability or influence. Missing uncertainty '
    'and counterevidence cannot be inferred away. No LLM, external call, source reread, scientific '
    'validation or canonical update is performed by this command. Execution flags describe this command only.')


def disclose(package, links, proposal, draft, reference_year, declared_review=None):
    packet = assemble(package, links, proposal, draft, reference_year, declared_review)
    checked, papers = _sources(package)
    groups = {}
    for paper in papers.values():
        if type(paper['year']) is not int or not 1 <= paper['year'] <= 9999:
            raise ValueError('supplied publication year must be an integer from 1 to 9999')
        digest = paper['source_sha256']
        groups.setdefault(digest, dict(source_sha256=digest, papers=[], active_references=[], unused_link_references=[]))
        groups[digest]['papers'].append(dict(paper_id=paper['paper_id'], publication_year=paper['year'],
            source_kind=paper['kind'], source_locator=paper['locator'], observation_count=len(paper['observations']),
            recorded_source_check=paper.get('source_verification', 'NOT_PERFORMED')))
    active_papers, active_observations, active_hashes = set(), set(), set()
    mock_refs, imported_refs, other_refs = [], [], []
    for route in packet['evidence_routes']:
        node = route['evidence']; ref = node['reference']; component = node['component']
        record = component if component is not None else node['observation']
        row = dict(reference=copy.deepcopy(ref), reference_sha256=route['reference_sha256'],
            publication_scope=route['publication_scope'], selected_claim_type=record['claim_type'],
            observation_stance=node['observation']['stance'], selected_locator=record['locator'],
            recorded_selected_check=record.get('evidence_verification', 'NOT_PERFORMED'),
            origin_status=({'operator_reviewed_mock_candidate': 'RECORDED_MOCK_CANDIDATE_ORIGIN',
                'operator_reviewed_imported_candidate': 'RECORDED_IMPORTED_CANDIDATE_ORIGIN'}.get(component.get('origin'),
                'CURATED_RECORD_ORIGIN_NOT_AUTHENTICATED')) if component is not None else
                          'CURATED_RECORD_ORIGIN_NOT_AUTHENTICATED',
            answer_uses=copy.deepcopy(route['answer_uses']), design_uses=copy.deepcopy(route['design_uses']),
            unreferenced_link_uses=copy.deepcopy(route['unreferenced_link_uses']))
        if component is not None and 'origin' in component:
            row['recorded_origin'] = {key: component[key] for key in ('origin', 'candidate_id',
                'candidate_bundle_sha256', 'operator_review_sha256', 'proposed_claim_type')}
        group = groups[node['source_sha256']]
        if route['answer_uses'] or route['design_uses']:
            group['active_references'].append(row)
            active_papers.add(ref['paper_id']); active_observations.add((ref['paper_id'], ref['observation_index']))
            active_hashes.add(node['source_sha256'])
            (mock_refs if row['origin_status'] == 'RECORDED_MOCK_CANDIDATE_ORIGIN' else
             imported_refs if row['origin_status'] == 'RECORDED_IMPORTED_CANDIDATE_ORIGIN' else other_refs).append(copy.deepcopy(ref))
        else:
            group['unused_link_references'].append(row)
    for group in groups.values():
        group['multiple_paper_ids_share_hash'] = len(group['papers']) > 1
        group['mixed_year_labels'] = len({p['publication_year'] for p in group['papers']}) > 1
        group['mixed_kind_labels'] = len({p['source_kind'] for p in group['papers']}) > 1
    answer = packet['answer']; design = packet['publication_scope']['design']
    decisions = {d['claim_id']: d['decision'] for d in answer.get('review', {}).get('decisions', [])}
    claims = [dict(claim_id=c['claim_id'], text=c['text'], claim_type=c['claim_type'], uncertainty=c['uncertainty'],
        declared_review_decision=decisions.get(c['claim_id'], 'NOT_SUPPLIED'),
        evidence_status=c['evidence_status'], quote_check=c['quote_check'], challenge_citation_supplied=c['challenge_citation_supplied']) for c in answer['claims']]
    steps = [dict(step_id=s['step_id'], proposed_action=s['proposed_action'], uncertainty=s['uncertainty'],
        missing_fields=copy.deepcopy(s['missing_fields']), claim_type='operator_proposal') for s in design['steps']]
    return dict(status='EVIDENCE_SCOPE_DISCLOSURE_NOT_VALIDATION', question=packet['question'],
        identity={key: checked['persona'][key] for key in ('author_id', 'version', 'build_id')},
        simulation_only=True,
        declared_operators=dict(answer=answer['operator_id'], design=design['operator_id'], links=design['evidence_links']['operator_id']),
        declared_reviewer=answer.get('review', {}).get('reviewer_id'),
        declared_identity_status='RECORDED_NOT_AUTHENTICATED', packet_input_sha256=packet['packet_input_sha256'], bindings=packet['bindings'],
        reference_year=reference_year, answer_claims=claims, design_steps=steps,
        coverage=dict(supplied_paper_ids=len(papers), supplied_observations=sum(len(p['observations']) for p in papers.values()),
            supplied_source_hash_groups=len(groups), actively_referenced_paper_ids=len(active_papers),
            actively_referenced_observations=len(active_observations), active_source_hash_groups=len(active_hashes),
            active_exact_references=len(mock_refs)+len(imported_refs)+len(other_refs)),
        unused_paper_ids=[paper_id for paper_id in papers if paper_id not in active_papers],
        source_groups=list(groups.values()),
        recorded_mock_origin_references=mock_refs, recorded_imported_origin_references=imported_refs,
        recorded_candidate_origin_references=mock_refs + imported_refs, other_curated_references=other_refs,
        review_prompts=copy.deepcopy(packet['review_prompts']),
        llm_used=False, provider_invoked=False, source_checks_repeated=False,
        scientific_validation='NOT_PERFORMED', researcher_fidelity_evaluation='NOT_PERFORMED',
        canonical_update_performed=False, boundary=BOUNDARY)


def render(package, links, proposal, draft, reference_year, declared_review=None):
    result = disclose(package, links, proposal, draft, reference_year, declared_review)
    lines = ['Reader evidence-scope disclosure | scholarly simulation only',
        'Question: ' + display(result['question']), 'Status: ' + result['status'],
        'Declared scholarly identity: ' + display(result['identity']['author_id']),
        'Packet input sha256: ' + result['packet_input_sha256'],
        'Declared operators (not authenticated): answer=' + display(result['declared_operators']['answer']) +
        '; design=' + display(result['declared_operators']['design']) + '; links=' + display(result['declared_operators']['links']),
        'Declared reviewer (not authenticated): ' + display(result['declared_reviewer']) +
        '; review sha256=' + display(result['bindings']['review_sha256']),
        'Current execution: no LLM/provider call; no source recheck; no researcher-fidelity evaluation.',
        'Record coverage (not independent studies or literature completeness):']
    for key, value in result['coverage'].items(): lines.append('  ' + key + ': ' + str(value))
    lines.append('Unused paper IDs: ' + (', '.join(display(p) for p in result['unused_paper_ids']) or 'none (not complete literature)'))
    lines.append('Answer draft claims (including rejected/deferred; not an approved selection):')
    for claim in result['answer_claims']:
        lines.append('  ' + display(claim['claim_id']) + ' [' + claim['claim_type'] + '; declared review=' +
            claim['declared_review_decision'] + ']: ' + display(claim['text']))
        lines.append('    Uncertainty: ' + ('NOT_SUPPLIED' if claim['uncertainty'] is None else display(claim['uncertainty'])))
        lines.append('    Evidence: ' + claim['evidence_status'] + '; challenge citation supplied=' + str(claim['challenge_citation_supplied']))
        lines.append('    Quote check: ' + claim['quote_check'])
    lines.append('Operator-proposed design steps:')
    for step in result['design_steps']:
        lines.append('  ' + display(step['step_id']) + ': ' + display(step['proposed_action']))
        lines.append('    Uncertainty: ' + ('NOT_SUPPLIED' if step['uncertainty'] is None else display(step['uncertainty'])))
        lines.append('    Missing supplied fields: ' + (', '.join(step['missing_fields']) or 'none (not validation)'))
    lines.append('Source hash groups (different hashes do not establish independence):')
    for group in result['source_groups']:
        lines.append('  sha256=' + group['source_sha256'] + '; multiple paper IDs=' + str(group['multiple_paper_ids_share_hash']) +
            '; mixed year/kind labels=' + str(group['mixed_year_labels']) + '/' + str(group['mixed_kind_labels']))
        for paper in group['papers']:
            lines.append('    ' + display(paper['paper_id']) + ' | ' + str(paper['publication_year']) + ' [' + paper['source_kind'] +
                '] | ' + display(paper['source_locator']) + '; recorded source check=' + paper['recorded_source_check'])
        for category in ('active_references', 'unused_link_references'):
            for row in group[category]:
                ref = row['reference']
                lines.append('    ' + category + ': ' + display(ref['paper_id']) + ' / ' + str(ref['observation_index']) +
                    ' / ' + display(ref['dimension']) + ' | ' + row['publication_scope'] + ' | ' + row['origin_status'])
                lines.append('      Selected [' + row['selected_claim_type'] + '] ' + display(row['selected_locator']) +
                    '; recorded selected check=' + row['recorded_selected_check'] + '; observation stance=' + row['observation_stance'])
                for use in row['answer_uses']:
                    lines.append('      Answer ' + display(use['claim_id']) + ': ' + use['role'] + ' [operator citation role]')
                for use in row['design_uses']:
                    lines.append('      Design ' + display(use['step_id']) + ': ' + use['role'] + ' via ' + display(use['link_id']) +
                        '; relation=' + use['relation'] + '; direction=' + use['direction'])
                for use in row['unreferenced_link_uses']:
                    lines.append('      Unreferenced link ' + display(use['link_id']) + ': ' + use['relation'])
                if 'recorded_origin' in row:
                    origin = row['recorded_origin']
                    lines.append('      Recorded ' + ('mock' if origin['origin'] == 'operator_reviewed_mock_candidate' else 'imported candidate') + ' origin; proposed label=' + origin['proposed_claim_type'] +
                        '; candidate bundle sha256=' + origin['candidate_bundle_sha256'] + '; review sha256=' + origin['operator_review_sha256'])
    lines.append('Mechanical review prompts (not exhaustive):')
    for p in result['review_prompts']:
        lines.append('  ' + p['target'] + ' ' + display(p['target_id']) + ': ' + p['code'] + (' / ' + p['field'] if 'field' in p else ''))
    if not result['review_prompts']: lines.append('  None detected; scientific validation remains NOT_PERFORMED.')
    lines.append('Boundary: ' + BOUNDARY)
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('package', 'links', 'proposal', 'draft'): parser.add_argument(name, type=Path)
    parser.add_argument('--reference-year', required=True, type=int); parser.add_argument('--review', type=Path)
    parser.add_argument('--format', choices=('json', 'text'), default='json'); args = parser.parse_args()
    try:
        inputs = (load(args.package), load(args.links), load(args.proposal), load(args.draft),
                  args.reference_year, load(args.review) if args.review else None)
        output = render(*inputs) if args.format == 'text' else json.dumps(disclose(*inputs), indent=2) + '\n'
    except (ValueError, OSError, KeyError, TypeError, AttributeError) as exc: parser.exit(1, str(exc) + '\n')
    sys.stdout.buffer.write(output.encode('utf-8'))


if __name__ == '__main__': main()
