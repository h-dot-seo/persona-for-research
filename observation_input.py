"""Verify curated observations against explicitly supplied text segments."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
from research_workflow import build, apply
from reasoning_cards import validate_components
from verification_receipt import VerifiedCorpus
from corpus_projection import runtime_papers


def verified_corpus(corpus, *, _local_source_ids=()):
    runtime_papers(corpus)  # Validate selected shapes and the full authorization boundary first.
    result = copy.deepcopy(corpus)
    # Reject unauthorized identity/split boundaries before inspecting any source text.
    for paper in result['papers']:
        if (paper.get('authorized') is not True or paper.get('split') != 'training'
                or paper.get('runtime_knowledge_eligible') is not True
                or paper.get('author_id') != result.get('author_id')):
            raise ValueError('only author-matched authorized runtime training evidence may be inspected')
    for paper in result['papers']:
        if paper.get('authorized') is not True or paper.get('split') != 'training':
            raise ValueError('only authorized training evidence may be inspected')
        segments = paper['segments']
        if not isinstance(segments, dict) or not segments or any(not isinstance(k, str) or not isinstance(v, str) for k,v in segments.items()):
            raise ValueError('segments must map locators to text')
        payload = json.dumps(segments, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()
        if paper.get('segments_sha256') != hashlib.sha256(payload).hexdigest():
            raise ValueError('segment payload hash mismatch')
        for obs in paper['observations']:
            quote = obs.get('evidence_quote')
            if not isinstance(quote, str) or not quote.strip() or quote not in segments.get(obs['locator'], ''):
                raise ValueError('observation quote not found at its source locator')
            if obs.get('claim_type') not in ('explicit_statement', 'operator_interpretation'):
                raise ValueError('claim_type must distinguish statement from interpretation')
            obs['evidence_verification'] = 'EXACT_QUOTE_MATCH_ONLY'
            components = obs.get('reasoning', {})
            validate_components(components)
            for component in components.values():
                if component['evidence_quote'] not in segments.get(component['locator'], ''):
                    raise ValueError('reasoning quote not found at its source locator')
                component['evidence_verification'] = 'EXACT_QUOTE_MATCH_ONLY'
        # The downstream package carries observation evidence; supplied text is not copied wholesale.
        del paper['segments']
    return VerifiedCorpus(result, _local_source_ids)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('corpus',type=Path); p.add_argument('--question',required=True); p.add_argument('--topic',required=True)
    a=p.parse_args()
    try:
        package=build(verified_corpus(json.loads(a.corpus.read_text(encoding='utf-8'))))
        result=dict(package=package,application=apply(package,a.question,a.topic),
                    boundary='Exact quote and supplied segment hash checked; source authenticity and semantic support unverified')
    except (ValueError,OSError,KeyError,TypeError) as e:
        p.exit(1,str(e)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__': main()
