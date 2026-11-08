"""Create a new local review workspace with empty operator-authored artifacts."""
import argparse
import json
import sys
from pathlib import Path
from persona import payload_sha256
from reasoning_links import _sources, _endpoint, template as link_template
from answer_draft import template as answer_template
from design_scenario import template as design_template
from evidence_scope import disclose
from review_journey import assemble, render
from reasoning_cards import DIMENSIONS
from strict_json import load

ROOT=Path(__file__).resolve().parent


def create(value, destination, question, operator_id, reference_year, *, journey_topic=None, target_context=None):
    if (journey_topic is None)!=(target_context is None):
        raise ValueError('journey_topic and target_context must be supplied together')
    package,papers=_sources(value)
    links=link_template(package,operator_id)
    draft=answer_template(package,question,operator_id)
    proposal=design_template(package,links,question,operator_id)
    # Validate all publication years, even unused papers, and reuse existing gap checks.
    scope=disclose(package,links,proposal,draft,reference_year)
    packet=assemble(package,links,proposal,draft,reference_year)
    catalog=[];empty=[]
    for paper in papers.values():
        if not paper['observations']:empty.append(paper['paper_id'])
        for index,obs in enumerate(paper['observations']):
            for dimension in [None]+list(obs.get('reasoning',{})):
                ref=dict(paper_id=paper['paper_id'],observation_index=index,dimension=dimension)
                catalog.append(dict(evidence=_endpoint(ref,papers),
                    missing_reasoning_dimensions=[d for d in DIMENSIONS if d not in obs.get('reasoning',{})]))
    requested=Path(destination).absolute()
    if any(p.is_symlink() for p in (requested,*requested.parents)):
        raise ValueError('workspace output path must not contain symlinks')
    destination=requested.resolve()
    if destination==ROOT or ROOT in destination.parents:
        raise ValueError('choose a new output directory outside the repository')
    if destination.exists():raise ValueError('output already exists; no files are overwritten')
    if not destination.parent.is_dir():raise ValueError('output parent must already exist')
    bindings=dict(persona_sha256=payload_sha256(package['persona']),knowledge_papers_sha256=payload_sha256(package['knowledge']['papers']))
    files={'package.json':package,'links.json':links,'answer.json':draft,'design.json':proposal,
        'reference-catalog.json':dict(**bindings,entries=catalog,papers_without_observations=empty,
            scope='All supplied observations/components, not a relevance ranking or recommendation. Quotes and private input fields may be present.',
            source_reread=False,llm_used=False),
        'initial-review.json':packet,'initial-review.txt':render(package,links,proposal,draft,reference_year),
        'initial-reader-scope.json':scope}
    command=lambda script,args:[sys.executable,str(ROOT/script),*[str(a) for a in args]]
    path=lambda name:destination/name
    files['next-commands.json']=dict(executed=False,commands=[
        dict(purpose='After editing links, generate a NEW empty design template; never overwrite a drafted plan blindly.',
             argv=command('design_scenario.py',[path('package.json'),path('links.json'),'--template','--question='+question,'--operator-id='+operator_id]),output='stdout; save to a new file and manually migrate reviewed steps'),
        dict(purpose='After manual answer/design editing, inspect all current gaps; initial reports are not refreshed automatically.',
             argv=command('review_journey.py',[path('package.json'),path('links.json'),path('design.json'),path('answer.json'),'--reference-year',reference_year,'--format','text']),output='stdout'),
        dict(purpose='Inspect current evidence scope and uncertainty disclosure.',
             argv=command('evidence_scope.py',[path('package.json'),path('links.json'),path('design.json'),path('answer.json'),'--reference-year',reference_year,'--format','text']),output='stdout')])
    files['START_HERE.txt']=('LOCAL REVIEW STARTER: no answer, link or proposed step has been generated.\n'
        'Read initial-review.txt: NO_ANSWER_CLAIMS and NO_PROPOSED_STEPS are intentional.\n'
        'Read initial-reader-scope.json and reference-catalog.json for supplied evidence and missing dimensions.\n'
        'Write answer.json claims and design.json steps explicitly; citation roles are your declarations.\n'
        'Use reference-catalog exact evidence.reference objects. No relevance or support is inferred.\n'
        'Optional links.json edits invalidate the existing design binding. Generate a fresh design template\n'
        'then manually migrate/review any steps; do not simply rewrite its hash.\n'
        'next-commands.json holds argument arrays, not executed commands or shell strings.\n'
        'initial-* reports describe the empty starter only. Rerun review after each edit.\n'
        'All files may contain private source quotes, annotations and identifiers. Keep this folder private.\n'
        'Source bytes are NOT reread; package check labels are historical records, not renewed verification.\n'
        'No LLM, authenticated human review, rights clearance or real researcher validation occurred.\n'
        'READY.json means setup finished, not research complete. If absent, preserve partial files and choose a NEW folder.\n')
    ready=dict(status='EMPTY_REVIEW_WORKSPACE_READY',**bindings,reference_year=reference_year,
               answer_claims=0,design_steps=0,evidence_links=0,llm_used=False,source_reread=False)
    if journey_topic is not None:
        # Existing factories keep all hypotheses and scientific choices explicit.
        from pattern_hypotheses import template as pattern_template
        from applicability_review import template as context_template
        from publication_context import template as relation_template
        from argument_map import template as argument_template
        from source_recheck import template as source_template
        from journey_inputs import template as selection_template
        context=context_template(package,question,target_context,journey_topic,reference_year,operator_id)
        selection=selection_template()
        selection['artifacts'].update(package='package.json',patterns='patterns.json',context='context.json',
            links='links.json',proposal='design.json',draft='answer.json',argument='argument.json',
            publication_relations='publication-relations.json')
        files.update({'patterns.json':pattern_template(package,operator_id),'context.json':context,
            'publication-relations.json':relation_template(package,operator_id),
            'argument.json':argument_template(package,draft,operator_id),
            'source-selection-template.json':source_template(package,operator_id),
            'journey-file-selection.json':selection})
        files['journey-next-commands.json']=dict(executed=False,
            status='INCOMPLETE_SELECTION_NOT_AN_INPUT_CARD',pattern_selection='NOT_SELECTED',
            commands=[
                dict(purpose='Inspect explicitly authored patterns, including missing evidence. Empty hypotheses are intentional.',
                     argv=command('pattern_hypotheses.py',[path('package.json'),path('patterns.json'),'--format','text']),output='stdout'),
                dict(purpose='Inspect source-condition comparisons. All matched observations start deferred; zero matches are valid.',
                     argv=command('applicability_review.py',[path('package.json'),path('context.json'),'--format','text']),output='stdout'),
                dict(purpose='Inspect explicitly supplied publication relationships. Empty relations do not establish independence.',
                     argv=command('publication_context.py',[path('package.json'),path('publication-relations.json'),'--format','text']),output='stdout'),
                dict(purpose='After answer edits, create a NEW empty argument map. If selecting a declared review, add --review with that explicit file.',
                     argv=command('argument_map.py',[path('package.json'),path('answer.json'),'--template','--operator-id='+operator_id]),
                     output='stdout; save to a new file, manually review/migrate steps and update the selection path'),
                dict(purpose='Only after authoring a pattern, selecting its existing ID and reviewing every artifact binding, prepare a NEW input card. This intentionally fails for the unchanged starter.',
                     argv=command('journey_inputs.py',['prepare',path('journey-file-selection.json'),'--input-root',destination]),
                     output='stdout; save to a new private card; add --source-root only after explicitly selecting a completed source form')])
        files['START_JOURNEY.txt']=('INCOMPLETE INTEGRATED STARTER: no pattern or method has been selected.\n'
            'The ordinary initial-* files cover only the empty answer/design review, not an integrated journey.\n'
            'patterns.json has no hypotheses. Author and inspect hypotheses using exact catalog references,\n'
            'then explicitly set one existing pattern_id in journey-file-selection.json. No ID is guessed.\n'
            'context.json matches exact case-insensitive observation topics only, not semantic relevance.\n'
            'Every matched observation is deferred; zero matched observations is valid and remains visible.\n'
            'Review comparisons, counterevidence, uncertainty and publication-relations.json explicitly.\n'
            'Changing topic, target context or question requires fresh context bindings and manual reassessment.\n'
            'The intended question must still match the answer and design question text exactly.\n'
            'Edit links before design steps; changed links require a fresh design template and manual review.\n'
            'Edit the answer, optionally create and fill a separate declared-review form, then create a NEW\n'
            'argument template bound to the intended answer and review. The initial argument has no steps\n'
            'and no declared review. Any answer or selected-review change makes that binding stale.\n'
            'Do not copy hashes or migrate decisions automatically. Update explicit selection paths when\n'
            'saving reviewed replacements under new names; preserve previous files and cards.\n'
            'Optional declared_review, method_applications and source_selection remain null. No method\n'
            'application, prepared input card or integrated journey report is generated during setup.\n'
            'source-selection-template.json has all paths null and is NOT selected. To enable a current\n'
            'source check, explicitly complete every path, select that file and supply --source-root\n'
            'on every prepare/inspect invocation. No source path is copied from package metadata.\n'
            'journey-next-commands.json contains unexecuted argument arrays, never shell commands.\n'
            'Only after all inputs compose, prepare a NEW input card. File edits require new preparation;\n'
            'stale cross-artifact bindings require proper regeneration and review first.\n'
            'READY.json means files were created, not a ready journey, research approval or verified source.\n'
            'Keep this directory private: original package quotes, provenance and annotations are retained.\n'
            'No provider, source reread, browser, researcher-fidelity evaluation or scientific execution occurs.\n')
        files['START_HERE.txt']+='\nOptional integrated starter: read START_JOURNEY.txt. Its file selection is incomplete, not a prepared input card.\n'
        ready.update(integrated_journey_status='NOT_PREPARED_PATTERN_NOT_SELECTED',pattern_hypotheses=0,
            matched_context_observations=len(context['assessments']),context_decisions='ALL_DEFERRED',
            source_selection_activated=False,prepared_input_card=False)
    # Serialize all outputs before the first directory/file write, including READY.
    serialized={name:data if isinstance(data,str) else json.dumps(data,ensure_ascii=True,allow_nan=False,indent=2)+'\n'
        for name,data in files.items()}
    ready_text=json.dumps(ready,ensure_ascii=True,allow_nan=False,indent=2)+'\n'
    destination.mkdir(exist_ok=False)
    def write(name,text):
        with (destination/name).open('x',encoding='utf-8',newline='\n') as stream:stream.write(text)
    try:
        for name,text in serialized.items():write(name,text)
        write('READY.json',ready_text)
    except (OSError,ValueError,TypeError):
        # Preserve evidence of a partial run, never delete or overwrite user files.
        raise
    return ready


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('package',type=Path);p.add_argument('destination',type=Path)
    p.add_argument('--question',required=True);p.add_argument('--operator-id',required=True)
    p.add_argument('--reference-year',type=int,required=True)
    p.add_argument('--journey-topic');p.add_argument('--target-context')
    a=p.parse_args()
    try:r=create(load(a.package),a.destination,a.question,a.operator_id,a.reference_year,
        journey_topic=a.journey_topic,target_context=a.target_context)
    except (ValueError,OSError,KeyError,TypeError,AttributeError) as exc:p.exit(1,str(exc)+'\n')
    print(json.dumps(r,indent=2))


if __name__=='__main__':main()
