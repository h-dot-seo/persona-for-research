"""Append explicitly reviewed imported observations to a separate local candidate."""
import argparse
import copy
import json
import sys
from pathlib import Path

from corpus_files import load_segment_corpus, load_sources
from extraction_adapter import MAX_HANDOFF_BYTES
from observation_proposals import review_proposals, _load
from observation_provenance import (KEY, ORIGIN, CONTENT_FIELDS, content_sha256,
                                    inventory, validate_origin)
from persona import payload_sha256
from research_workflow import build
from design_scenario import _text

SCHEMA = 'persona.observation-append-card.v1'
CARD_FIELDS = {'schema', 'manifest_sha256', 'proposal_bundle_sha256', 'operator_review_sha256',
               'operator_id', 'new_version', 'new_build_id', 'operations'}
OPERATION_FIELDS = {'operation', 'candidate_id', 'target_paper_id', 'target_observation_index'}
MAX_OUTPUT_BYTES = 8 * 1024 * 1024
BOUNDARY = ('This is a separate reviewed observation-append candidate, not a canonical update '
    'or authenticated human approval. Source bytes and exact quotes are checked against the '
    'explicit pinned local files; semantic support, rights clearance, source authenticity and '
    'individual author ownership remain unverified. Provider/model/run, reviewer and append '
    'operator identities are recorded declarations. Initial imported-observation history is '
    'retained but not replayed by this append. Existing observations are never replaced. No '
    'model call, external transmission, source acquisition, source hash refresh or input-file '
    'modification is performed.')


def _reviewed(manifest, bundle, review, root):
    corpus = load_segment_corpus(manifest, root, max_total_bytes=MAX_HANDOFF_BYTES)
    packet = review_proposals(corpus, bundle, review)
    if any(row['decision']=='defer' for row in packet['candidates']) or not packet['accepted_proposal_count']:
        raise ValueError('resolve every proposal and explicitly accept at least one before an append candidate')
    accepted = {row['candidate']['candidate_id']: row for row in packet['candidates'] if row['decision']=='accept'}
    return corpus, packet, accepted


def template(manifest, bundle, review, root, operator_id):
    _reviewed(manifest, bundle, review, root); _text(operator_id, 'operator_id', 128)
    return dict(schema=SCHEMA, manifest_sha256=payload_sha256(manifest),
        proposal_bundle_sha256=payload_sha256(bundle), operator_review_sha256=payload_sha256(review),
        operator_id=operator_id, new_version='', new_build_id='', operations=[])


def prepare_candidate(manifest, bundle, review, card, root):
    # Validate card shape and declared bindings before opening local sources.
    if not isinstance(card, dict) or set(card)!=CARD_FIELDS or card['schema']!=SCHEMA:
        raise ValueError('observation append card has missing or unsupported fields')
    for key, expected in [('manifest_sha256',payload_sha256(manifest)),
                          ('proposal_bundle_sha256',payload_sha256(bundle)),
                          ('operator_review_sha256',payload_sha256(review))]:
        if card[key]!=expected: raise ValueError('append card is stale; inspect the current manifest and review')
    for key in ('operator_id','new_version','new_build_id'): _text(card[key], key, 128)
    if card['new_version']==manifest['version'] or card['new_build_id']==manifest['build_id']:
        raise ValueError('append requires both a new version and a new build ID')
    if not isinstance(card['operations'],list) or not card['operations'] or len(card['operations'])>128:
        raise ValueError('append requires one explicit operation per accepted candidate, at most 128')
    for operation in card['operations']:
        if not isinstance(operation,dict) or set(operation)!=OPERATION_FIELDS or operation['operation']!='append':
            raise ValueError('only explicit observation append operations are supported')
        for key in ('candidate_id','target_paper_id'): _text(operation[key],key,128)
        if type(operation['target_observation_index']) is not int or operation['target_observation_index']<0:
            raise ValueError('append index must be a nonnegative integer')
    corpus, packet, accepted = _reviewed(manifest, bundle, review, root)
    result = json.loads(json.dumps(manifest,ensure_ascii=False,allow_nan=False))
    papers = {paper['paper_id']:paper for paper in result['papers']}
    seen=set(); additions=[]
    for operation in card['operations']:
        cid=operation['candidate_id']
        if cid not in accepted or cid in seen: raise ValueError('unknown, rejected or duplicate append candidate')
        seen.add(cid); row=accepted[cid]; candidate=row['candidate']; paper_id=operation['target_paper_id']
        if paper_id!=candidate['paper_id'] or paper_id not in papers:
            raise ValueError('append target must be the candidate source paper')
        paper=papers[paper_id]; index=operation['target_observation_index']
        if index!=len(paper['observations']):
            raise ValueError('append index must equal the current observation count in explicit operation order')
        observation=copy.deepcopy(row['reviewed_observation'])
        if any(not isinstance(observation[key],str) or not observation[key].strip()
               for key in ('method','condition','limitation','topic','locator','evidence_quote')):
            raise ValueError('runtime observations require explicitly reviewed method, condition, limitation, topic and evidence; missing fields are never filled')
        observation[KEY]=dict(schema='persona.observation-origin.v1',origin=ORIGIN,
            candidate_id=cid,paper_id=paper_id,source_sha256=paper['source_sha256'],
            reviewer_id=review['reviewer_id'],operator_id=card['operator_id'],
            proposal_bundle_sha256=payload_sha256(bundle),operator_review_sha256=payload_sha256(review),
            adoption_card_sha256=payload_sha256(card),input_corpus_sha256=payload_sha256(corpus),
            proposed_observation_sha256=payload_sha256(candidate['proposed_observation']),
            reviewed_observation_sha256=content_sha256(observation),
            proposed_claim_type=candidate['proposed_observation']['claim_type'],
            proposed_stance=candidate['proposed_observation']['stance'],
            import_record=copy.deepcopy(bundle['import_record']))
        validate_origin(observation,paper)
        paper['observations'].append(observation);paper.pop('input_inventory',None)
        additions.append(dict(candidate_id=cid,paper_id=paper_id,observation_index=index,
            manifest_observation_sha256=payload_sha256(observation),observation_origin=copy.deepcopy(observation[KEY])))
    if seen!=set(accepted): raise ValueError('every accepted proposal needs exactly one explicit append operation')
    result['version']=card['new_version'];result['build_id']=card['new_build_id']
    # Verify the whole new corpus again, including all retained observations and source bytes.
    package=build(load_sources(result,root))
    audit=dict(scope='ONE_DECLARED_OBSERVATION_APPEND_ONLY',
        original_manifest_sha256=payload_sha256(manifest),revised_manifest_sha256=payload_sha256(result),
        proposal_bundle_sha256=payload_sha256(bundle),operator_review_sha256=payload_sha256(review),
        append_card_sha256=payload_sha256(card),package_sha256=payload_sha256(package),
        additions=additions,initial_unreplayed_observation_origins=inventory(build(manifest)),
        source_checks='PINNED_LOCAL_BYTES_AND_EXACT_QUOTES_FOR_COMPLETE_RESULT',
        operator_identity='RECORDED_NOT_AUTHENTICATED',semantic_validation='NOT_PERFORMED')
    return dict(schema='persona.observation-append-candidate.v1',status='REVIEWED_OBSERVATION_APPEND_CANDIDATE',
        manifest=result,package=package,review_packet=packet,append_audit=audit,
        execution_scope='CURRENT_APPEND_ONLY; HISTORICAL_MODEL_USE_NOT_AUTHENTICATED',
        provider_invoked=False,llm_used=False,external_transmission=False,
        runtime_package_created=True,canonical_update_performed=False,boundary=BOUNDARY)


def audit_candidate(manifest,bundle,review,card,candidate,root):
    expected=prepare_candidate(manifest,bundle,review,card,root)
    if payload_sha256(candidate)!=payload_sha256(expected):
        raise ValueError('replayed append does not exactly match the supplied candidate')
    return dict(status='OBSERVATION_APPEND_REPLAY_MATCH',
        replayed_candidate_sha256=payload_sha256(expected),append_audit=copy.deepcopy(expected['append_audit']),
        historical_model_use='DECLARED_NOT_AUTHENTICATED',semantic_validation='NOT_PERFORMED',
        provider_invoked=False,llm_used=False,canonical_update_performed=False,boundary=BOUNDARY)


def encode_result(result):
    output=(json.dumps(result,indent=2)+'\n').encode('utf-8')
    if len(output)>MAX_OUTPUT_BYTES:
        raise ValueError('output exceeds the 8 MiB replayable JSON file limit; reduce the input scope')
    return output


def main():
    parser=argparse.ArgumentParser(description=__doc__);commands=parser.add_subparsers(dest='command',required=True)
    for name in ('template','prepare','audit'):
        command=commands.add_parser(name)
        for field in ('manifest','bundle','review'):command.add_argument(field,type=Path)
        if name=='template':command.add_argument('--operator-id',required=True)
        else:command.add_argument('card',type=Path)
        if name=='audit':command.add_argument('candidate',type=Path)
        command.add_argument('--source-root',type=Path,required=True)
    args=parser.parse_args()
    try:
        manifest,bundle,review=(_load(getattr(args,key)) for key in ('manifest','bundle','review'))
        if args.command=='template':result=template(manifest,bundle,review,args.source_root,args.operator_id)
        elif args.command=='prepare':result=prepare_candidate(manifest,bundle,review,_load(args.card),args.source_root)
        else:result=audit_candidate(manifest,bundle,review,_load(args.card),_load(args.candidate),args.source_root)
        output=encode_result(result)
    except (ValueError,OSError,KeyError,TypeError,AttributeError) as exc:parser.exit(1,str(exc)+'\n')
    sys.stdout.buffer.write(output)


if __name__=='__main__':main()
