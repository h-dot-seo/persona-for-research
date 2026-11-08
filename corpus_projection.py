"""Project only documented runtime fields; not an anonymizer or access control."""
import copy
from reasoning_cards import validate_components, REVIEW_FIELDS
from observation_provenance import validate_origin, KEY as OBSERVATION_ORIGIN

PAPER_FIELDS = ('paper_id', 'author_id', 'split', 'runtime_knowledge_eligible',
    'authorized', 'source_sha256', 'locator', 'kind', 'year', 'topic',
    'source_file', 'source_verification', 'segments_sha256')
OBSERVATION_FIELDS = ('method', 'condition', 'limitation', 'locator', 'topic',
    'stance', 'claim_type', 'evidence_quote', 'evidence_verification', OBSERVATION_ORIGIN)
COMPONENT_FIELDS = ('text', 'locator', 'evidence_quote', 'claim_type', 'evidence_verification') + REVIEW_FIELDS


def runtime_papers(corpus):
    """Reject corpus authorization failures before projecting observation records."""
    if not isinstance(corpus, dict):
        raise ValueError('corpus must be an object')
    for field in ('author_id', 'version', 'build_id'):
        if not isinstance(corpus.get(field), str) or not corpus[field].strip():
            raise ValueError('corpus author_id, version and build_id must be nonempty strings')
    papers = corpus.get('papers')
    if not isinstance(papers, list) or not papers:
        raise ValueError('at least one authorized training paper is required')
    for paper in papers:
        if not isinstance(paper, dict):
            raise ValueError('paper must be an object')
        if (paper.get('authorized') is not True or paper.get('split') != 'training'
                or paper.get('runtime_knowledge_eligible') is not True
                or paper.get('author_id') != corpus.get('author_id')):
            raise ValueError('only author-matched authorized runtime training evidence is allowed')
    result = []
    for paper in papers:
        for field in ('locator', 'topic'):
            if not isinstance(paper.get(field), str) or not paper[field].strip():
                raise ValueError('paper locator and topic must be nonempty strings')
        for field in ('source_file', 'segments_sha256'):
            if field in paper and not isinstance(paper[field], str):
                raise ValueError('optional source metadata must be strings')
        if not isinstance(paper.get('observations'), list):
            raise ValueError('observations must be an array')
        projected = {k: copy.deepcopy(paper[k]) for k in PAPER_FIELDS if k in paper}
        projected['observations'] = []
        for obs in paper['observations']:
            if not isinstance(obs, dict):
                raise ValueError('observation must be an object')
            if obs.get('claim_type', 'operator_interpretation') not in ('explicit_statement', 'operator_interpretation'):
                raise ValueError('observation claim_type must distinguish statement from interpretation')
            if obs.get('evidence_quote') is not None and not isinstance(obs['evidence_quote'], str):
                raise ValueError('observation evidence_quote must be a string or null')
            validate_origin(obs, paper)
            row = {k: copy.deepcopy(obs[k]) for k in OBSERVATION_FIELDS if k in obs}
            if 'reasoning' in obs:
                validate_components(obs['reasoning'])
                row['reasoning'] = {dimension: {k: copy.deepcopy(record[k])
                    for k in COMPONENT_FIELDS if k in record}
                    for dimension, record in obs['reasoning'].items()}
            projected['observations'].append(row)
        result.append(projected)
    return result
