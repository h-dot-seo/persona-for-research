"""Run bundled synthetic fixtures through real CLIs into a new external directory."""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from persona import payload_sha256
from strict_json import loads

ROOT = Path(__file__).resolve().parent
QUESTION = 'Which observation could distinguish two synthetic explanations?'


def run(destination):
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
        'Read after completion: reader-scope.txt, review-packet.txt, argument-map.txt, timeline.txt, lineage.json.\n'
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
        bundle = command('extraction_adapter.py', [path('corpus.json'), '--mock-response', path('mock-response.json')], 'candidates.json')
        command('operator_review.py', [path('corpus.json'), path('candidates.json'), '--targets'], 'candidate-targets.json')
        review = command('operator_review.py', [path('corpus.json'), path('candidates.json'), '--template', '--reviewer-id', 'synthetic-fixture-reviewer'], 'deferred-candidate-review.json')
        if [(c['candidate_id'], c['paper_id'], c['dimension']) for c in bundle['candidates']] != [
            ('candidate-1', 'synthetic-0', 'alternative_explanation'), ('candidate-2', 'synthetic-0', 'uncertainty')]:
            raise ValueError('bundled mock fixture changed; review the demo script before continuing')
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
        write('commands.json', commands)
        receipt = dict(status='SYNTHETIC_WALKTHROUGH_COMPLETE_NOT_VALIDATED', llm_used=False, external_transmission=False,
            human_review_authenticated=False, answer_review_status='ALL_DEFERRED',
            scientific_validation='NOT_PERFORMED', command_count=len(commands), lineage_status=lineage['status'],
            read_first=['reader-scope.txt','review-packet.txt','argument-map.txt','timeline.txt','lineage.json'])
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('new_output_directory', type=Path); args = parser.parse_args()
    try: result = run(args.new_output_directory)
    except (ValueError, OSError, KeyError, IndexError, TypeError, subprocess.SubprocessError) as exc: parser.exit(1, str(exc)+'\n')
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == '__main__': main()
