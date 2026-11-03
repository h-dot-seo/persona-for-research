"""Freeze synthetic answer metadata, then compare separately supplied holdout labels."""
import argparse
import json
import re
import sys
from pathlib import Path

from answer_draft import inspect as inspect_answer
from reasoning_links import _sources, _endpoint
from reasoning_cards import DIMENSIONS
from persona import payload_sha256
from strict_json import load

SUBMISSION_SCHEMA = 'synthetic-answer-submission.v1'
LABEL_SCHEMA = 'synthetic-answer-holdout-labels.v1'
BOUNDARY = ('Agreement with supplied synthetic labels only. No semantic entailment, quote '
    'authenticity, literature completeness, human judgment or researcher fidelity is evaluated. '
    'Synthetic IDs and flags are declarations, not authenticated data provenance. Submission '
    'hashes detect inconsistency, not deliberate forgery or proof that labels were unseen. '
    'Freeze reads no labels; evaluation reads no corpus and cannot update a package. Holdout '
    'labels and resulting errors must not be treated as training evidence. No LLM, provider '
    'call, source reread or external transmission is performed.')


def _keys(value, keys, name):
    if not isinstance(value, dict) or set(value) != set(keys): raise ValueError(name + ' has missing or unknown fields')


def _id(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 128: raise ValueError('bounded nonempty ID required')


def _hash(value):
    if not isinstance(value, str) or re.fullmatch('[0-9a-f]{64}', value) is None: raise ValueError('lowercase SHA256 required')


def _record(value):
    _keys(value, ('reference','source_sha256','source_claim_type'), 'source record')
    ref=value['reference']; _keys(ref, ('paper_id','observation_index','dimension'), 'reference')
    _id(ref['paper_id'])
    if not ref['paper_id'].startswith('synthetic-'): raise ValueError('only synthetic fixture paper IDs are supported')
    if type(ref['observation_index']) is not int or ref['observation_index'] < 0: raise ValueError('invalid observation index')
    if ref['dimension'] is not None and ref['dimension'] not in DIMENSIONS: raise ValueError('invalid reasoning dimension')
    _hash(value['source_sha256'])
    if value['source_claim_type'] not in ('explicit_statement','operator_interpretation'): raise ValueError('invalid source claim label')
    return payload_sha256(ref)


def _claims(values, catalog=None):
    if not isinstance(values,list): raise ValueError('claims must be an array')
    seen=set()
    for claim in values:
        _keys(claim, ('claim_id','claim_type','citations'), 'claim'); _id(claim['claim_id'])
        if claim['claim_id'] in seen: raise ValueError('duplicate claim ID')
        seen.add(claim['claim_id'])
        if claim['claim_type'] not in ('source_quote','operator_synthesis'): raise ValueError('invalid answer claim type')
        if not isinstance(claim['citations'],list): raise ValueError('citations must be an array')
        if claim['claim_type']=='source_quote' and len(claim['citations'])!=1: raise ValueError('source_quote needs one citation')
        cited=set()
        for citation in claim['citations']:
            _keys(citation, ('reference','role','source_sha256','source_claim_type'), 'citation')
            record={k:v for k,v in citation.items() if k!='role'}; key=_record(record)
            if citation['role'] not in ('support','challenge','context'): raise ValueError('invalid citation role')
            if (key,citation['role']) in cited: raise ValueError('duplicate reference/role citation')
            cited.add((key,citation['role']))
            if catalog is not None and (key not in catalog or record != catalog[key]):
                raise ValueError('submission citation differs from its frozen training catalog')


def freeze(package, draft):
    checked,papers=_sources(package)
    if checked['persona']['author_id']!='synthetic-scholar': raise ValueError('only synthetic-scholar fixtures are supported')
    answer=inspect_answer(checked,draft)
    catalog=[]
    for paper in papers.values():
        _id(paper['paper_id'])
        if not paper['paper_id'].startswith('synthetic-'): raise ValueError('only synthetic fixture paper IDs are supported')
        for index,obs in enumerate(paper['observations']):
            for dimension in [None,*obs.get('reasoning',{})]:
                node=_endpoint(dict(paper_id=paper['paper_id'],observation_index=index,dimension=dimension),papers)
                record=node['component'] if node['component'] is not None else node['observation']
                row=dict(reference=node['reference'],source_sha256=node['source_sha256'],source_claim_type=record['claim_type'])
                _record(row);catalog.append(row)
    claims=[]
    for claim in answer['claims']:
        citations=[]
        for citation in claim['citations']:
            node=citation['evidence']; record=node['component'] if node['component'] is not None else node['observation']
            citations.append(dict(reference=node['reference'],role=citation['role'],source_sha256=node['source_sha256'],source_claim_type=record['claim_type']))
        claims.append(dict(claim_id=claim['claim_id'],claim_type=claim['claim_type'],citations=citations))
    payload=dict(schema=SUBMISSION_SCHEMA,synthetic_only=True,synthetic_author_id='synthetic-scholar',
        persona_sha256=answer['persona_sha256'],knowledge_papers_sha256=answer['knowledge_papers_sha256'],
        draft_sha256=answer['draft_sha256'],question_sha256=payload_sha256(answer['question']),
        training_reference_catalog=catalog,claims=claims)
    return dict(payload,submission_sha256=payload_sha256(payload))


def evaluate(submission,labels):
    keys={'schema','synthetic_only','synthetic_author_id','persona_sha256','knowledge_papers_sha256',
          'draft_sha256','question_sha256','training_reference_catalog','claims','submission_sha256'}
    _keys(submission,keys,'submission')
    if submission['schema']!=SUBMISSION_SCHEMA or submission['synthetic_only'] is not True or submission['synthetic_author_id']!='synthetic-scholar':
        raise ValueError('only declared synthetic submissions are supported')
    for key in ('persona_sha256','knowledge_papers_sha256','draft_sha256','question_sha256','submission_sha256'): _hash(submission[key])
    if submission['submission_sha256']!=payload_sha256({k:v for k,v in submission.items() if k!='submission_sha256'}):
        raise ValueError('submission digest mismatch')
    if not isinstance(submission['training_reference_catalog'],list): raise ValueError('reference catalog must be an array')
    catalog={}
    for row in submission['training_reference_catalog']:
        key=_record(row)
        if key in catalog: raise ValueError('duplicate catalog reference')
        catalog[key]=row
    _claims(submission['claims'],catalog)
    _keys(labels,('schema','dataset_id','synthetic_only','split','persona_sha256','knowledge_papers_sha256','question_sha256','expected_claims'),'labels')
    _id(labels['dataset_id'])
    if labels['schema']!=LABEL_SCHEMA or labels['synthetic_only'] is not True or labels['split']!='holdout':
        raise ValueError('separate synthetic holdout labels required')
    for key in ('persona_sha256','knowledge_papers_sha256','question_sha256'):
        _hash(labels[key])
        if labels[key]!=submission[key]: raise ValueError('labels belong to a different frozen package/question')
    _claims(labels['expected_claims'])
    if not labels['expected_claims']: raise ValueError('empty gold claim set is not an evaluation')
    # Gold labels may disagree with source labels; that disagreement is measured,
    # not silently overwritten from submission metadata. References must exist.
    for claim in labels['expected_claims']:
        for citation in claim['citations']:
            ref_key=payload_sha256(citation['reference'])
            if ref_key not in catalog: raise ValueError('gold reference is outside frozen training catalog')
            if citation['source_sha256']!=catalog[ref_key]['source_sha256']:
                raise ValueError('gold source hash contradicts its bound training catalog')
    actual={c['claim_id']:c for c in submission['claims']}; expected={c['claim_id']:c for c in labels['expected_claims']}
    def key(c): return (payload_sha256(c['reference']),c['role'],c['source_sha256'])
    matches=extras=missing=claim_matches=source_matches=source_mismatches=challenge_expected=challenge_matches=0
    rows=[]
    for cid in list(expected)+[cid for cid in actual if cid not in expected]:
        gold=expected.get(cid); found=actual.get(cid)
        wanted={key(c):c for c in gold['citations']} if gold else {}
        got={key(c):c for c in found['citations']} if found else {}
        common=wanted.keys() & got.keys()
        matches+=len(common);extras+=len(got.keys()-wanted.keys());missing+=len(wanted.keys()-got.keys())
        type_match=gold is not None and found is not None and gold['claim_type']==found['claim_type']
        claim_matches+=int(type_match)
        for k in common:
            if wanted[k]['source_claim_type']==got[k]['source_claim_type']:source_matches+=1
            else:source_mismatches+=1
        challenges={k for k,c in wanted.items() if c['role']=='challenge'}
        challenge_expected+=len(challenges);challenge_matches+=len(challenges & got.keys())
        rows.append(dict(claim_id=cid,presence='MATCHED_ID' if gold and found else 'MISSING_CLAIM' if gold else 'UNEXPECTED_CLAIM',
            expected_claim_type=gold['claim_type'] if gold else None,actual_claim_type=found['claim_type'] if found else None,
            claim_type_label_match=type_match,matched_citation_count=len(common),
            missing_citations=[c for k,c in wanted.items() if k not in got],unexpected_citations=[c for k,c in got.items() if k not in wanted],
            source_claim_label_mismatches=[dict(reference=wanted[k]['reference'],role=wanted[k]['role'],expected=wanted[k]['source_claim_type'],actual=got[k]['source_claim_type'])
                for k in wanted if k in got and wanted[k]['source_claim_type']!=got[k]['source_claim_type']],
            missing_challenge_citations=[c for k,c in wanted.items() if k in challenges and k not in got]))
    result = dict(status='SYNTHETIC_LABEL_COMPARISON_ONLY',dataset_id=labels['dataset_id'],
        submission_sha256=submission['submission_sha256'],labels_sha256=payload_sha256(labels),
        citation_labels=dict(matched=matches,unexpected=extras,missing=missing,
            precision=matches/(matches+extras) if matches+extras else None,
            recall=matches/(matches+missing) if matches+missing else None),
        answer_claim_type_labels=dict(expected=len(expected),matched=claim_matches,missing_claim_ids=[x for x in expected if x not in actual],
            unexpected_claim_ids=[x for x in actual if x not in expected]),
        source_claim_type_labels=dict(matched=source_matches,mismatched=source_mismatches,unmatched_expected_citations=missing),
        challenge_labels=dict(expected=challenge_expected,preserved=challenge_matches,missing=challenge_expected-challenge_matches),
        claims=rows,question_semantics_evaluated=False,scientific_validation='NOT_PERFORMED',
        researcher_fidelity_evaluation='NOT_PERFORMED',llm_used=False,canonical_update_performed=False,boundary=BOUNDARY)
    return json.loads(json.dumps(result))


def main():
    parser=argparse.ArgumentParser(description=__doc__); sub=parser.add_subparsers(dest='command',required=True)
    freezing=sub.add_parser('freeze');freezing.add_argument('package',type=Path);freezing.add_argument('draft',type=Path)
    evaluation=sub.add_parser('evaluate');evaluation.add_argument('submission',type=Path);evaluation.add_argument('holdout_labels',type=Path)
    args=parser.parse_args()
    try:
        result=freeze(load(args.package),load(args.draft)) if args.command=='freeze' else evaluate(load(args.submission),load(args.holdout_labels))
    except (ValueError,OSError,KeyError,TypeError,AttributeError) as exc:parser.exit(1,str(exc)+'\n')
    sys.stdout.buffer.write((json.dumps(result,indent=2)+'\n').encode('utf-8'))


if __name__=='__main__':main()
