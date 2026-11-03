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


def create(value, destination, question, operator_id, reference_year):
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
    destination.mkdir(exist_ok=False)
    def write(name,data):
        with (destination/name).open('x',encoding='utf-8',newline='\n') as stream:
            stream.write(data if isinstance(data,str) else json.dumps(data,ensure_ascii=True,indent=2)+'\n')
    try:
        for name,data in files.items():write(name,data)
        ready=dict(status='EMPTY_REVIEW_WORKSPACE_READY',**bindings,reference_year=reference_year,
                   answer_claims=0,design_steps=0,evidence_links=0,llm_used=False,source_reread=False)
        write('READY.json',ready)
    except (OSError,ValueError,TypeError):
        # Preserve evidence of a partial run, never delete or overwrite user files.
        raise
    return ready


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('package',type=Path);p.add_argument('destination',type=Path)
    p.add_argument('--question',required=True);p.add_argument('--operator-id',required=True)
    p.add_argument('--reference-year',type=int,required=True)
    a=p.parse_args()
    try:r=create(load(a.package),a.destination,a.question,a.operator_id,a.reference_year)
    except (ValueError,OSError,KeyError,TypeError,AttributeError) as exc:p.exit(1,str(exc)+'\n')
    print(json.dumps(r,indent=2))


if __name__=='__main__':main()
