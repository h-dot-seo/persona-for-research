"""Run bundled synthetic fixtures through real CLIs into a new external directory."""
import argparse
import copy
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from persona import payload_sha256
from strict_json import loads

ROOT = Path(__file__).resolve().parent
QUESTION = 'Which observation could distinguish two synthetic explanations?'


def run(destination, *, candidate_source='mock', research_journey=False, recheck_sources=False, review_method_use=False, import_method_use=False, html_review=False, import_answers=False):
    if type(import_answers) is not bool:
        raise ValueError('import_answers must be a boolean')
    if import_answers and not research_journey:
        raise ValueError('import_answers requires research_journey')
    if type(html_review) is not bool:
        raise ValueError('html_review must be a boolean')
    if html_review and not research_journey:
        raise ValueError('html_review requires research_journey')
    if type(import_method_use) is not bool:
        raise ValueError('import_method_use must be a boolean')
    if import_method_use and not review_method_use:
        raise ValueError('import_method_use requires review_method_use')
    if type(review_method_use) is not bool:
        raise ValueError('review_method_use must be a boolean')
    if review_method_use and not research_journey:
        raise ValueError('review_method_use requires research_journey')
    if type(recheck_sources) is not bool:
        raise ValueError('recheck_sources must be a boolean')
    if recheck_sources and not research_journey:
        raise ValueError('recheck_sources requires research_journey')
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
        (('Live recheck mode writes invented local source files; source-recheck.txt contains the detailed check.\n' if html_review else
          'Live recheck mode writes invented local source files; read source-recheck.txt first.\n') if recheck_sources else '') +
        ('Method-use mode also writes method-applications.txt; considered use is not scientific approval.\n' if review_method_use else '') +
        ('Imported method-use mode retains original/reviewed/rejected synthetic proposals; no model is called.\n' if import_method_use else '') +
        ('Imported answer mode retains canned original/reviewed/rejected claims; adoption does not retain the final answer.\n' if import_answers else '') +
        ('HTML review mode starts with passive local research-journey.html; open it yourself after completion.\n' if html_review else '') +
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
        if recheck_sources:
            (destination/'synthetic-sources').mkdir()
            for index, source in enumerate(corpus['papers']):
                text = 'INVENTED LOCAL SOURCE FOR SYNTHETIC DEMONSTRATION ONLY.\n\n' + ''.join(
                    '## '+locator+'\n'+content+'\n\n' for locator,content in source['segments'].items())
                source['source_file'] = 'synthetic-source-'+str(index)+'.md'
                source['source_sha256'] = hashlib.sha256(text.encode('utf-8')).hexdigest()
                write('synthetic-sources/'+source['source_file'], text)
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
        if import_answers:
            _import_answer_fixture(command, write, path, package_path, links, draft)
        else:
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
        journey = (_extend_research_journey(command, write, path, package_path, links, recheck_sources=recheck_sources, review_method_use=review_method_use, import_method_use=import_method_use, html_review=html_review) if research_journey else None)
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
        if import_answers:
            receipt.update(answer_candidate_source='offline-import', answer_import_is_synthetic_fixture=True,
                answer_adoption_scope='CANNED_FIXTURE_DECISIONS_NOT_SCIENTIFIC_APPROVAL',
                read_first=['answer-proposals.txt', *receipt['read_first']])
        if review_method_use:
            receipt.update(method_application_status=journey['method_application_review']['status'],
                read_first=['method-applications.txt', *receipt['read_first']])
        if import_method_use:
            receipt.update(method_application_candidate_source='offline-import',
                method_application_import_is_synthetic_fixture=True,
                read_first=['application-proposals.txt', *receipt['read_first']])
        if recheck_sources:
            receipt.update(current_source_recheck_status=journey['source_recheck']['status'],
                current_source_recheck_is_synthetic=True,
                read_first=['source-recheck.txt', *receipt['read_first']])
        if html_review:
            receipt.update(html_review_scope='READ_ONLY_LOCAL_SNAPSHOT_NOT_APPROVAL',
                read_first=['research-journey.html', *receipt['read_first']])
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



def _import_answer_fixture(command, write, path, package_path, links, draft):
    """Only fixed invented inputs; never accept caller-supplied candidates or decisions."""
    scope = command('answer_proposals.py', ['template', package_path, '--question', QUESTION,
        '--topic', 'model design', '--reference-year', '2020', '--operator-id',
        'synthetic-answer-fixture-operator'], 'empty-answer-scope.json')
    earlier = copy.deepcopy(links['links'][0]['to_ref'])
    later = copy.deepcopy(links['links'][0]['from_ref'])
    unused_parent = dict(earlier, dimension=None)
    scope['evidence_refs'] = [earlier, later, unused_parent]
    write('synthetic-answer-scope.json', scope)
    command('answer_proposals.py', ['prepare', package_path, path('synthetic-answer-scope.json')], 'answer-handoff.json')
    response = command('answer_proposals.py', ['response-template', package_path,
        path('synthetic-answer-scope.json'), path('answer-handoff.json')], 'empty-answer-response.json')
    response['candidates'] = [{key:copy.deepcopy(value) for key,value in claim.items() if key != 'claim_id'}
        for claim in draft['claims']]
    response['candidates'][1]['text'] = 'Original canned answer comparison before explicit reviewer rewrite.'
    response['candidates'].append(dict(text='Rejected synthetic answer overgeneralization, kept only as history.',
        claim_type='operator_synthesis', uncertainty='Unsupported invented alternative.',
        citations=[dict(reference=unused_parent, role='support')]))
    write('synthetic-answer-response.json', response)
    write('synthetic-answer-provenance.json', dict(provider_id='synthetic-no-provider', model_id='synthetic-no-model',
        run_id='synthetic-answer-fixture', operator_id='synthetic-fixture-operator', execution_location='unknown'))
    bundle = command('answer_proposals.py', ['import', package_path, path('synthetic-answer-scope.json'),
        path('answer-handoff.json'), path('synthetic-answer-response.json'), path('synthetic-answer-provenance.json')],
        'answer-candidates.json')
    review = command('answer_proposals.py', ['review-template', package_path, path('answer-candidates.json'),
        '--reviewer-id', 'synthetic-answer-adoption-reviewer'], 'deferred-answer-adoption.json')
    ids = ['answer-candidate-'+str(index) for index in range(1,5)]
    if ([row['candidate_id'] for row in bundle['candidates']] != ids or
            [row['proposed_claim'] for row in bundle['candidates']] != response['candidates'] or
            [row['candidate_id'] for row in review['decisions']] != ids or
            any(row['decision'] != 'defer' or 'reviewed_claim' in row for row in review['decisions'])):
        raise ValueError('synthetic answer candidate/template fixture changed; inspect before continuing')
    for index, claim in enumerate(draft['claims']):
        review['decisions'][index].update(decision='accept', reviewed_claim=copy.deepcopy(claim),
            review_note='Fixed invented adoption decision only, not general automatic approval or final answer review.')
    review['decisions'][3].update(decision='reject', review_note='Rejected invented alternative remains historical, not active evidence.')
    write('synthetic-answer-adoption.json', review)
    command('answer_proposals.py', ['review', package_path, path('answer-candidates.json'),
        path('synthetic-answer-adoption.json'), '--format', 'text'], 'answer-proposals.txt', False)
    command('answer_proposals.py', ['export', package_path, path('answer-candidates.json'),
        path('synthetic-answer-adoption.json')], 'draft.json')


def _extend_research_journey(command, write, path, package_path, links, *, recheck_sources=False, review_method_use=False, import_method_use=False, html_review=False):
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
    if review_method_use:
        method_args = [package_path, path('reviewed-patterns.json'), path('synthetic-context.json'),
            path('links.json'), path('proposal.json'), '--pattern-id', 'synthetic-comparison']
        applications = command('method_application.py', [*method_args, '--template', '--operator-id',
            'synthetic-method-operator'], 'deferred-method-applications.json')
        if [row['step_id'] for row in applications['applications']] != ['compare']:
            raise ValueError('synthetic method-use step fixture changed; inspect before continuing')
        applications['applications'][0].update(decision='consider', proposed_role='constraint',
            application_rationale='Consider this synthetic comparison hypothesis as a constraint on the named comparison step.',
            target_condition_comparison='The target has no tested discriminating outcome; the condition remains unmet.',
            required_checks=['Inspect whether synthetic model predictions differ before considering actual use.'],
            failure_condition=None, remaining_uncertainty='This is a fixed invented consideration, not an approved method.',
            evidence_refs=[copy.deepcopy(earlier), copy.deepcopy(later)])
        application_path = path('synthetic-method-applications.json')
        if import_method_use:
            command('application_proposals.py', ['prepare', *method_args], 'application-handoff.json')
            method_response = command('application_proposals.py', ['response-template', *method_args,
                path('application-handoff.json')], 'empty-application-response.json')
            original = {key:copy.deepcopy(value) for key,value in applications['applications'][0].items() if key != 'decision'}
            original['application_rationale'] = 'Canned synthetic model application rationale before explicit reviewer correction.'
            rejected = dict(copy.deepcopy(original), proposed_role='method', evidence_refs=[later_observation],
                application_rationale='Rejected synthetic direct-use alternative; it is not a recommendation.')
            method_response['candidates'] = [original, rejected]
            write('synthetic-application-response.json', method_response)
            write('synthetic-application-provenance.json', dict(provider_id='synthetic-no-provider', model_id='synthetic-no-model',
                run_id='synthetic-application-fixture', operator_id='synthetic-fixture-operator', execution_location='unknown'))
            imported = command('application_proposals.py', ['import', *method_args, path('application-handoff.json'),
                path('synthetic-application-response.json'), path('synthetic-application-provenance.json')], 'application-candidates.json')
            method_review = command('application_proposals.py', ['review-template', *method_args,
                path('application-candidates.json'), '--reviewer-id', 'synthetic-application-reviewer'], 'deferred-application-review.json')
            if [r['candidate_id'] for r in imported['candidates']] != ['application-candidate-1','application-candidate-2'] or any(
                    r['decision'] != 'defer' for r in method_review['decisions']):
                raise ValueError('synthetic application candidate fixture changed; inspect before continuing')
            method_review['decisions'][0].update(decision='accept',
                review_note='Fixed synthetic reviewer correction only, never approval of a method.',
                reviewed_application=copy.deepcopy(applications['applications'][0]))
            method_review['decisions'][1].update(decision='reject', review_note='Rejected synthetic alternative retained as history, not application exclusion.')
            write('synthetic-application-review.json', method_review)
            command('application_proposals.py', ['review', *method_args, path('application-candidates.json'),
                path('synthetic-application-review.json'), '--format', 'text'], 'application-proposals.txt', False)
            command('application_proposals.py', ['export', *method_args, path('application-candidates.json'),
                path('synthetic-application-review.json')], 'reviewed-method-applications.json')
            application_path = path('reviewed-method-applications.json')
        else:
            write('synthetic-method-applications.json', applications)
        command('method_application.py', [*method_args, application_path, '--format', 'text'], 'method-applications.txt', False)
        args.extend(['--method-applications', application_path])
    if recheck_sources:
        selection = command('source_recheck.py', [package_path, '--template', '--operator-id',
            'synthetic-source-operator'], 'empty-source-selection.json')
        if [row['paper_id'] for row in selection['sources']] != ['synthetic-0','synthetic-1']:
            raise ValueError('synthetic source fixture selection changed; inspect before continuing')
        for index,row in enumerate(selection['sources']): row['source_file'] = 'synthetic-source-'+str(index)+'.md'
        write('synthetic-source-selection.json', selection)
        source_args = [package_path, path('synthetic-source-selection.json'), '--source-root', path('synthetic-sources')]
        command('source_recheck.py', source_args, 'source-recheck.json')
        command('source_recheck.py', [*source_args, '--format', 'text'], 'source-recheck.txt', False)
        args.extend(['--source-selection', path('synthetic-source-selection.json'), '--source-root', path('synthetic-sources')])
    result = command('research_journey.py', args, 'research-journey.json')
    command('research_journey.py', [*args, '--format', 'text'], 'research-journey.txt', False)
    if html_review:
        command('research_journey.py', [*args, '--format', 'html'], 'research-journey.html', False)
    decisions = result['pattern_transfer_review']['answer_design_review']['answer']['review']['decisions']
    if any(row['decision'] != 'defer' for row in decisions):
        raise ValueError('synthetic answer review must remain deferred')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('new_output_directory', type=Path)
    parser.add_argument('--candidate-source', choices=('mock', 'offline-import'), default='mock')
    parser.add_argument('--research-journey', action='store_true')
    parser.add_argument('--recheck-sources', action='store_true')
    parser.add_argument('--review-method-use', action='store_true')
    parser.add_argument('--import-method-use', action='store_true')
    parser.add_argument('--html-review', action='store_true')
    parser.add_argument('--import-answers', action='store_true')
    args = parser.parse_args()
    try: result = run(args.new_output_directory, candidate_source=args.candidate_source, research_journey=args.research_journey, recheck_sources=args.recheck_sources, review_method_use=args.review_method_use, import_method_use=args.import_method_use, html_review=args.html_review, import_answers=args.import_answers)
    except (ValueError, OSError, KeyError, IndexError, TypeError, subprocess.SubprocessError) as exc: parser.exit(1, str(exc)+'\n')
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == '__main__': main()
