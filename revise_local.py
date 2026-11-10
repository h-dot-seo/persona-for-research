"""Revise one manual observation against unchanged local source bytes, with an audit artifact."""
import argparse
import copy
import json
import sys
from pathlib import Path
from curate_local import _paper, validate_manual_observation
from research_workflow import build
from corpus_files import load_sources
from persona import payload_sha256
from strict_json import load

SCHEMA='persona.manual-observation-revision.v1'
ROOT=Path(__file__).resolve().parent


def _target(manifest,paper_id,index):
    paper=_paper(manifest,paper_id)
    if type(index) is not int or not 0<=index<len(paper['observations']):
        raise ValueError('observation index must identify one existing observation')
    old=paper['observations'][index]
    validate_manual_observation(old)
    return old


def template(manifest,paper_id,index):
    old=_target(manifest,paper_id,index)
    return dict(schema=SCHEMA,manifest_sha256=payload_sha256(manifest),paper_id=paper_id,
        observation_index=index,previous_observation_sha256=payload_sha256(old),observation=copy.deepcopy(old),
        operator_id='',revision_reason='',new_version='',new_build_id='')


def revise(manifest,card,root):
    fields={'schema','manifest_sha256','paper_id','observation_index','previous_observation_sha256',
            'observation','operator_id','revision_reason','new_version','new_build_id'}
    if not isinstance(card,dict) or set(card)!=fields or card['schema']!=SCHEMA:
        raise ValueError('revision card has missing or unsupported fields')
    old=_target(manifest,card['paper_id'],card['observation_index'])
    if card['manifest_sha256']!=payload_sha256(manifest) or card['previous_observation_sha256']!=payload_sha256(old):
        raise ValueError('stale revision binding; inspect the current manifest and observation')
    for field in ('operator_id','revision_reason','new_version','new_build_id'):
        if not isinstance(card[field],str) or not card[field].strip() or len(card[field])>2000:
            raise ValueError('revision requires an explicit bounded '+field)
    if card['new_version']==manifest['version'] or card['new_build_id']==manifest['build_id']:
        raise ValueError('choose a new version and build ID explicitly')
    validate_manual_observation(card['observation'])
    if payload_sha256(card['observation'])==payload_sha256(old):
        raise ValueError('no observation change supplied')
    result=json.loads(json.dumps(manifest,ensure_ascii=False,allow_nan=False))
    paper=next(p for p in result['papers'] if p['paper_id']==card['paper_id'])
    paper['observations'][card['observation_index']]=copy.deepcopy(card['observation'])
    paper.pop('input_inventory',None)
    result['version']=card['new_version'];result['build_id']=card['new_build_id']
    build(result)
    build(load_sources(result,root))  # New complete corpus, not the superseded quote, is checked.
    audit=dict(schema=SCHEMA,status='MANUAL_REVISION_REQUIRES_REVIEW',
        previous_manifest_sha256=payload_sha256(manifest),revised_manifest_sha256=payload_sha256(result),
        revision_card_sha256=payload_sha256(card),paper_id=card['paper_id'],observation_index=card['observation_index'],
        source_sha256=paper['source_sha256'],operator_id=card['operator_id'],revision_reason=card['revision_reason'],
        previous_observation=copy.deepcopy(old),revised_observation=copy.deepcopy(card['observation']),
        previous_observation_sha256=payload_sha256(old),revised_observation_sha256=payload_sha256(card['observation']),
        previous_identity={k:manifest[k] for k in ('author_id','version','build_id')},
        revised_identity={k:result[k] for k in ('author_id','version','build_id')},llm_used=False,
        boundary='Unsigned operator revision record, not authenticated human review, semantic correction, author attribution or source authenticity. Only the revised corpus byte hashes and exact quotes were checked. Prior observation may be wrong; downstream packages and bound artifacts must be rebuilt and reviewed.')
    return result,audit


def save_revision(manifest,card,root,destination):
    requested=Path(destination).absolute()
    if any(p.is_symlink() for p in (requested,*requested.parents)):
        raise ValueError('revision output path must not contain symlinks')
    destination=requested.resolve()
    if destination==ROOT or ROOT in destination.parents or destination.exists() or not destination.parent.is_dir():
        raise ValueError('choose a new directory outside the repository with an existing parent')
    result,audit=revise(manifest,card,root)
    destination.mkdir(exist_ok=False)
    for name,value in (('manifest.json',result),('revision-audit.json',audit),
                       ('READY.json',dict(status='REVISION_FILES_WRITTEN_REVIEW_REQUIRED',revised_manifest_sha256=audit['revised_manifest_sha256']))):
        with (destination/name).open('x',encoding='utf-8',newline='\n') as stream:
            stream.write(json.dumps(value,ensure_ascii=True,indent=2)+'\n')
    return audit


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    t=sub.add_parser('template');t.add_argument('manifest',type=Path);t.add_argument('--paper',required=True);t.add_argument('--observation-index',type=int,required=True)
    a=sub.add_parser('apply');a.add_argument('manifest',type=Path);a.add_argument('card',type=Path);a.add_argument('destination',type=Path);a.add_argument('--source-root',type=Path,required=True)
    args=p.parse_args()
    try:
        manifest=load(args.manifest)
        if args.command=='template':result=template(manifest,args.paper,args.observation_index)
        else:
            audit=save_revision(manifest,load(args.card),args.source_root,args.destination)
            result={k:audit[k] for k in ('status','previous_manifest_sha256','revised_manifest_sha256')}
    except (ValueError,OSError,KeyError,TypeError,AttributeError) as exc:p.exit(1,str(exc)+'\n')
    sys.stdout.buffer.write((json.dumps(result,ensure_ascii=True,indent=2) + '\n').encode('utf-8'))


if __name__=='__main__':main()
