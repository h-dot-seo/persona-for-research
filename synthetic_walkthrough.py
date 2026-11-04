"""Run bundled synthetic fixtures through real CLIs into a new external directory."""
import argparse
import copy
import json
import os
import subprocess
import sys
from pathlib import Path

from persona import payload_sha256
from strict_json import loads

ROOT = Path(__file__).resolve().parent
QUESTION = 'Which observation could distinguish two synthetic explanations?'


def run(destination, *, candidate_source='mock', research_journey=False):
    if type(research_journey) is not bool:
        raise ValueError('research_journey must be a boolean')
    if candidate_source not in ('mock', 'offline-import'):
        raise ValueError('candidate_source must be mock or offline-import')
    requested = Path(destination).absolute()
    if any(p.is_symlink() for p in (requested, *requested.parents)):
        raise ValueError('demo output path must not contain symlinks')
    destination = requested.resolve()
    if destination == ROOT or ROOT in destination.parents:
        raise ValueError('choose a new output directory outside the repository')
    if destination.exists(): raise ValueError('output already exists; choose a new directory, no files are overwritten')
    if not destination.parent.is_dir(): raise ValueError('output parent must already exist')
    destination.mkdir(exist_ok=False)
    commands = []
    def write(name, value):
        with (destination/name).open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(value if isinstance(value, str) else json.dumps(value, indent=2) + '\n')
    def command(script, args, output, json_output=True):
        argv = [sys.executable, str(ROOT/script), *[str(x) for x in args]]
        entry = dict(argv=argv, output=output, returncode=None)
        commands.append(entry)
        result = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=30,
            env=dict(os.environ, PYTHONIOENCODING='utf-8'), check=False)
        entry['returncode'] = result.returncode
        if result.returncode:
            raise ValueError('synthetic stage failed: ' + script + ': ' + result.stderr.decode('utf-8', errors='replace').strip())
        text = result.stdout.decode('utf-8')
        value = loads(text) if json_output else text
        write(output, text)
        return value
    write('START_HERE.txt', 'SYNTHETIC DEMO ONLY. Completion requires COMPLETE.json.\n'
        'No real scholar, LLM, external provider or scientific validation is used.\n'
        'Candidate accept decisions are fixed invented fixture decisions, not a general approval workflow.\n'
        'Answer review stays deferred. Missing falsification and defeater remain intentional.\n'
        'Read after completion: reader-scope.txt, review-packet.txt, argument-map.txt, timeline.txt, lineage.json.\n' +
        ('Extended mode also writes research-journey.txt with pattern, relationship, context and argument review.\n' if research_journey else '') +
        'commands.json records actual CLI argument arrays (not shell commands).\n'
        'If any stage fails, keep this folder for diagnosis and rerun into a NEW directory.\n')
    try:
        corpus = loads((ROOT/'examples/reasoning-corpus.json').read_text(encoding='utf-8'))
        corpus['papers'][0]['observations'][0]['reasoning'] = {}
        paper = corpus['papers'][1]
        paper['segments']['synthetic criterion'] = 'A shared prediction does not discriminate the models.'
        paper['segments_sha256'] = payload_sha256(paper['segments'])
        paper['observations'][0]['stance'] = 'challenge'
        paper['observations'][0]['reasoning'] = dict(falsification_check=dict(
            text='Check whether predictions differ.', locator='synthetic criterion',
            evidence_quote='A shared prediction does not discriminate the models.', claim_type='explicit_statement'))
        response = loads((ROOT/'examples/mock-extraction-response.json').read_text(encoding='utf-8'))
        write('corpus.json', corpus); write('mock-response.json', response)
        path = lambda name: destination/name
        command('observation_input.py', [path('corpus.json'), '--question', QUESTION, '--topic', 'model design'], 'baseline.json')
        if candidate_source == 'mock':
            bundle = command('extraction_adapter.py', [path('corpus.json'), '--mock-response', path('mock-response.json')], 'candidates.json')
        else:
            command('model_handoff.py', ['prepare', path('corpus.json')], 'handoff.json')
            imported_response = command('model_handoff.py', ['response-template', path('corpus.json'), path('handoff.json')], 'empty-imported-response.json')
            imported_response['candidates'] = response
            write('imported-response.json', imported_response)
            write('declared-provenance.json', dict(provider_id='synthetic-no-provider', model_id='synthetic-no-model',
                run_id='synthetic-offline-import-fixture', operator_id='synthetic-fixture-operator', execution_location='unknown'))
            bundle = command('model_handoff.py', ['import', path('corpus.json'), path('handoff.json'),
                path('imported-response.json'), path('declared-provenance.json')], 'candidates.json')
        command('operator_review.py', [path('corpus.json'), path('candidates.json'), '--targets'], 'candidate-targets.json')
        review = command('operator_review.py', [path('corpus.json'), path('candidates.json'), '--template', '--reviewer-id', 'synthetic-fixture-reviewer'], 'deferred-candidate-review.json')
        if [(c['candidate_id'], c['paper_id'], c['dimension']) for c in bundle['candidates']] != [
            ('candidate-1', 'synthetic-0', 'alternative_explanation'), ('candidate-2', 'synthetic-0', 'uncertainty')]:
            raise ValueError('bundled candidate fixture changed; review the demo script before continuing')
        review['decisions'] = [dict(candidate_id=c['candidate_id'], decision='accept', review_note='Fixed synthetic demonstration decision only.',
            target_rule_id='rule-1', target_paper_id='synthetic-0', operation='add', expected_component_sha256=None,
            reviewed_text=c['candidate_text'], reviewed_claim_type='operator_interpretation') for c in bundle['candidates']]
        write('synthetic-candidate-review.json', review)
        command('operator_review.py', [path('corpus.json'), path('candidates.json'), path('synthetic-candidate-review.json'),
            '--new-version', '2', '--new-build-id', 'synthetic-demo-reviewed'], 'revision.json')
        package_path = path('revision.json')
        links = command('reasoning_links.py', [package_path, '--template', '--operator-id', 'synthetic-link-operator'], 'empty-links.json')
        links['links'] = [dict(link_id='criterion-link', relation='qualifies',
            from_ref=dict(paper_id='synthetic-1', observation_index=0, dimension='falsification_check'),
            to_ref=dict(paper_id='synthetic-0', observation_index=0, dimension='alternative_explanation'),
            rationale='Operator proposes using the later criterion to qualify a comparison.', claim_type='operator_interpretation')]
        write('links.json', links)
        proposal = command('design_scenario.py', [package_path, path('links.json'), '--template', '--question', QUESTION,
            '--operator-id', 'synthetic-design-operator'], 'empty-proposal.json')
        proposal['steps'] = [dict(step_id='compare', proposed_action='Compare synthetic model predictions before choosing an observation.',
            rationale='Inspect whether the proposed comparison can discriminate explanations.', hypothesis='Predicted outcomes differ.',
            falsification_check=None, alternative_explanation=None, uncertainty='No actual predictions have been evaluated.',
            link_uses=[dict(link_id='criterion-link', role='constraint', applicability_note='An operator-proposed criterion, not proof of transferability.')])]
        write('proposal.json', proposal)
        draft = command('answer_draft.py', [package_path, '--template', '--question', QUESTION, '--operator-id', 'synthetic-answer-operator'], 'empty-draft.json')
        draft['claims'] = [dict(claim_id='criterion', claim_type='source_quote',
            text='A shared prediction does not discriminate the models.', uncertainty=None,
            citations=[dict(role='context', reference=links['links'][0]['from_ref'])]),
            dict(claim_id='comparison', claim_type='operator_synthesis', text='Check where model predictions differ.',
                uncertainty='Applicability remains untested.', citations=[dict(role='support', reference=links['links'][0]['to_ref']),
                    dict(role='challenge', reference=links['links'][0]['from_ref'])]),
            dict(claim_id='conclusion', claim_type='operator_synthesis', text='Choose an observation only after checking discriminating predictions.',
                uncertainty='Synthetic proposal, not empirical evidence.', citations=[])]
        write('draft.json', draft)
        command('answer_draft.py', [package_path, path('draft.json'), '--review-template', '--reviewer-id', 'synthetic-review-pending'], 'answer-review.json')
        argument = command('argument_map.py', [package_path, path('draft.json'), '--review', path('answer-review.json'),
            '--template', '--operator-id', 'synthetic-map-operator'], 'empty-argument.json')
        argument['steps'] = [dict(step_id='combine', premise_claim_ids=['criterion', 'comparison'], conclusion_claim_id='conclusion',
            bridge_rationale='The operator proposes applying the criterion to the comparison.',
            assumptions=['The synthetic models have distinguishable predictions.'], defeater=None)]
        write('argument.json', argument)
        command('publication_timeline.py', [package_path, '--topic', 'model design', '--format', 'text'], 'timeline.txt', False)
        common = [package_path, path('links.json'), path('proposal.json'), path('draft.json'),
                  '--reference-year', '2020', '--review', path('answer-review.json'), '--format', 'text']
        command('review_journey.py', common, 'review-packet.txt', False)
        command('evidence_scope.py', common, 'reader-scope.txt', False)
        command('argument_map.py', [package_path, path('draft.json'), path('argument.json'), '--review', path('answer-review.json'),
            '--format', 'text'], 'argument-map.txt', False)
        write('revision-inputs.json', dict(original_corpus=corpus, candidate_bundle=bundle, operator_review=review))
        lineage = command('audit_design_lineage.py', [package_path, path('links.json'), path('proposal.json'), path('revision-inputs.json')], 'lineage.json')
        journey = (_extend_research_journey(command, write, path, package_path, links) if research_journey else None)
        write('commands.json', commands)
        receipt = dict(status='SYNTHETIC_WALKTHROUGH_COMPLETE_NOT_VALIDATED', llm_used=False, external_transmission=False,
            human_review_authenticated=False, answer_review_status='ALL_DEFERRED',
            candidate_source=candidate_source, imported_response_is_synthetic_fixture=candidate_source == 'offline-import',
            scientific_validation='NOT_PERFORMED', command_count=len(commands), lineage_status=lineage['status'],
            read_first=['reader-scope.txt','review-packet.txt','argument-map.txt','timeline.txt','lineage.json'])
        if journey is not None:
            receipt.update(research_journey_status=journey['status'],
                research_journey_answer_status=journey['answer_review_status'],
                research_journey_is_synthetic=True,
                read_first=['research-journey.txt', 'pattern-review.txt', *receipt['read_first']])
        write('COMPLETE.json', receipt)
        return dict(receipt, output_directory=str(destination))
    except (ValueError, OSError, KeyError, IndexError, TypeError, subprocess.SubprocessError) as exc:
        # Never mask the stage failure or overwrite files while reporting it.
        for name, value in [('FAILED.txt', 'INCOMPLETE SYNTHETIC DEMO. Inspect stage error below.\n' + str(exc) + '\n'),
                            ('commands.json', commands)]:
            try:
                write(name, value)
            except OSError:
                pass
        raise



def _extend_research_journey(command, write, path, package_path, links):
    """Fixed invented decisions only, never accept external candidate material."""
    command('pattern_proposals.py', ['prepare', package_path, '--topic', 'model design',
        '--include-evidence-reasons'], 'pattern-handoff.json')
    response = command('pattern_proposals.py', ['response-template', package_path,
        path('pattern-handoff.json')], 'empty-pattern-response.json')
    earlier = copy.deepcopy(links['links'][0]['to_ref'])
    later = copy.deepcopy(links['links'][0]['from_ref'])
    later_observation = dict(later, dimension=None)
    candidate = dict(proposed_hypothesis='A tentative synthetic comparison-before-measurement pattern.',
        scope_note='Two invented records only, not a real researcher method or independent support.',
        support_refs=[earlier, later], challenge_refs=[later_observation],
        alternative_explanation='A generic convention could explain the shared wording.',
        falsification_check=None, uncertainty='No actual study or researcher fidelity has been evaluated.',
        evidence_uses=[dict(reference=copy.deepcopy(ref), role=role,
            rationale='Canned imported '+role+' explanation for '+ref['paper_id']+'.', context_boundary=None)
            for refs, role in [([earlier, later], 'support'), ([later_observation], 'challenge')] for ref in refs])
    rejected = copy.deepcopy(candidate)
    rejected['proposed_hypothesis'] = 'A rejected synthetic overgeneralization from the same records.'
    response['candidates'] = [candidate, rejected]
    write('synthetic-pattern-response.json', response)
    write('synthetic-pattern-provenance.json', dict(provider_id='synthetic-no-provider', model_id='synthetic-no-model',
        run_id='synthetic-pattern-fixture', operator_id='synthetic-fixture-operator', execution_location='unknown'))
    bundle = command('pattern_proposals.py', ['import', package_path, path('pattern-handoff.json'),
        path('synthetic-pattern-response.json'), path('synthetic-pattern-provenance.json')], 'pattern-candidates.json')
    review = command('pattern_proposals.py', ['review-template', package_path, path('pattern-candidates.json'),
        '--reviewer-id', 'synthetic-pattern-reviewer'], 'deferred-pattern-review.json')
    if len(bundle['candidates']) != 2 or any(row['decision'] != 'defer' for row in review['decisions']):
        raise ValueError('synthetic pattern template contract changed; inspect before continuing')
    reviewed = dict(pattern_id='synthetic-comparison', operator_hypothesis='Explicit synthetic reviewer comparison hypothesis.',
        **{key:copy.deepcopy(value) for key,value in candidate.items() if key != 'proposed_hypothesis'})
    for use in reviewed['evidence_uses']:
        use['rationale'] = 'Fixed synthetic reviewer '+use['role']+' explanation for '+use['reference']['paper_id']+'.'
    review['decisions'][0].update(decision='accept', review_note='Fixed invented fixture decision, not general automatic approval.', reviewed_pattern=reviewed)
    review['decisions'][1].update(decision='reject', review_note='Synthetic overgeneralization retained for review visibility.')
    write('synthetic-pattern-review.json', review)
    command('pattern_proposals.py', ['review', package_path, path('pattern-candidates.json'),
        path('synthetic-pattern-review.json'), '--format', 'text'], 'pattern-review.txt', False)
    command('pattern_proposals.py', ['export', package_path, path('pattern-candidates.json'),
        path('synthetic-pattern-review.json')], 'reviewed-patterns.json')
    context = command('applicability_review.py', [package_path, '--template', '--question', QUESTION,
        '--target-context', 'Synthetic target without measured discriminating predictions.', '--topic', 'model design',
        '--reference-year', '2020', '--operator-id', 'synthetic-context-operator'], 'deferred-context.json')
    context['assessments'][0].update(decision='exclude',
        context_comparison='The synthetic target has no tested discriminating observation.',
        remaining_uncertainty='The comparison may still be useful as a criticism, not an applicable method.',
        counterevidence_refs=[later])
    write('synthetic-context.json', context)
    relations = command('publication_context.py', [package_path, '--template', '--operator-id',
        'synthetic-relation-operator'], 'empty-publication-relations.json')
    relations['relations'] = [dict(relation_id='synthetic-review-context', from_paper_id='synthetic-1',
        to_paper_id='synthetic-0', relation_type='review_summary_of',
        rationale='A synthetic operator-declared comparison, not an established citation or influence.',
        basis_refs=[later], uncertainty=None)]
    write('synthetic-publication-relations.json', relations)
    args = [package_path, path('reviewed-patterns.json'), path('synthetic-context.json'), path('links.json'),
        path('proposal.json'), path('draft.json'), path('argument.json'), path('synthetic-publication-relations.json'),
        '--pattern-id', 'synthetic-comparison', '--review', path('answer-review.json')]
    result = command('research_journey.py', args, 'research-journey.json')
    command('research_journey.py', [*args, '--format', 'text'], 'research-journey.txt', False)
    decisions = result['pattern_transfer_review']['answer_design_review']['answer']['review']['decisions']
    if any(row['decision'] != 'defer' for row in decisions):
        raise ValueError('synthetic answer review must remain deferred')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('new_output_directory', type=Path)
    parser.add_argument('--candidate-source', choices=('mock', 'offline-import'), default='mock')
    parser.add_argument('--research-journey', action='store_true')
    args = parser.parse_args()
    try: result = run(args.new_output_directory, candidate_source=args.candidate_source, research_journey=args.research_journey)
    except (ValueError, OSError, KeyError, IndexError, TypeError, subprocess.SubprocessError) as exc: parser.exit(1, str(exc)+'\n')
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == '__main__': main()
