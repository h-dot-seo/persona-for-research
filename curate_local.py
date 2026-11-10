"""Append one explicitly authored observation to a pinned local manifest."""
from exclusive_output import add_output_argument, emit, preflight
import argparse
import copy
import json
import sys
from pathlib import Path
from persona import payload_sha256
from research_workflow import build
from corpus_files import load_sources
from strict_json import load

SCHEMA = 'persona.manual-observation.v1'
REQUIRED = {'method','condition','limitation','locator','topic','evidence_quote','claim_type'}


def _paper(manifest, paper_id):
    build(manifest)  # Full authorization/shape validation before filesystem access.
    matches = [p for p in manifest['papers'] if p['paper_id'] == paper_id]
    if len(matches) != 1:
        raise ValueError('paper_id must identify exactly one selected paper')
    return matches[0]


def template(manifest, paper_id):
    _paper(manifest, paper_id)
    return dict(schema=SCHEMA, manifest_sha256=payload_sha256(manifest), paper_id=paper_id,
                observation={**{key:'' for key in sorted(REQUIRED)}, 'claim_type':None,
                             'stance':None, 'reasoning':{}})


def validate_manual_observation(obs):
    if not isinstance(obs,dict) or not REQUIRED <= set(obs) or set(obs)-REQUIRED-{'stance','reasoning'}:
        raise ValueError('manual observation needs explicit fields; verification or model provenance cannot be supplied')
    if any(not isinstance(obs[k],str) or not obs[k].strip() for k in REQUIRED):
        raise ValueError('fill every required observation field explicitly')
    if 'stance' not in obs or obs['stance'] not in ('support','challenge'):
        raise ValueError('choose support or challenge explicitly')
    for component in obs.get('reasoning',{}).values() if isinstance(obs.get('reasoning',{}),dict) else ():
        if not isinstance(component,dict) or set(component) != {'text','locator','evidence_quote','claim_type'}:
            raise ValueError('manual reasoning components accept only text, locator, evidence_quote and claim_type')


def append_observation(manifest, card, root):
    if not isinstance(card, dict) or set(card) != {'schema','manifest_sha256','paper_id','observation'} or card['schema'] != SCHEMA:
        raise ValueError('manual observation card has missing or unsupported fields')
    _paper(manifest, card['paper_id'])
    if card['manifest_sha256'] != payload_sha256(manifest):
        raise ValueError('stale manifest binding; create a fresh card and inspect the current evidence')
    obs=card['observation']
    validate_manual_observation(obs)
    result=json.loads(json.dumps(manifest,ensure_ascii=False,allow_nan=False))  # JSON value semantics detach shared lists.
    paper=next(p for p in result['papers'] if p['paper_id']==card['paper_id'])
    paper['observations'].append(copy.deepcopy(obs))
    paper.pop('input_inventory',None)  # Preparation-only empty-evidence annotation is no longer current.
    # Validate the whole resulting corpus, including pre-existing observations.
    build(result)
    build(load_sources(result,root))
    # Preserve input manifest fields; add no freshly read source bodies or verification claims.
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    make=sub.add_parser('template'); add_output_argument(make);make.add_argument('manifest',type=Path);make.add_argument('--paper',required=True)
    add=sub.add_parser('append'); add_output_argument(add);add.add_argument('manifest',type=Path);add.add_argument('card',type=Path);add.add_argument('--source-root',type=Path,required=True)
    args=parser.parse_args()
    preflight(parser, getattr(args, 'output', None))
    try:
        manifest=load(args.manifest)
        result=template(manifest,args.paper) if args.command=='template' else append_observation(manifest,load(args.card),args.source_root)
    except (ValueError,OSError,KeyError,TypeError,AttributeError) as exc:parser.exit(1,str(exc)+'\n')
    emit(parser, (json.dumps(result,ensure_ascii=True,indent=2) + '\n').encode('utf-8'), getattr(args, 'output', None))


if __name__=='__main__':main()
