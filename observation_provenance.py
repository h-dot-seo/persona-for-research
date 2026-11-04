"""Validate and display declared imported-observation history, not its authenticity."""
import copy
from persona import payload_sha256
from declared_provenance import validate_declared_provenance

KEY = 'observation_origin'
ORIGIN = 'operator_reviewed_imported_observation'
CONTENT_FIELDS = ('method', 'condition', 'limitation', 'topic', 'locator', 'evidence_quote', 'claim_type', 'stance')
HASH_FIELDS = ('proposal_bundle_sha256', 'operator_review_sha256', 'adoption_card_sha256',
               'input_corpus_sha256', 'proposed_observation_sha256', 'reviewed_observation_sha256', 'source_sha256')
FIELDS = {'schema', 'origin', 'candidate_id', 'paper_id', 'reviewer_id', 'operator_id',
          'proposed_claim_type', 'proposed_stance', 'import_record', *HASH_FIELDS}


def content_sha256(observation):
    return payload_sha256({key:observation.get(key) for key in CONTENT_FIELDS})


def _hash(value):
    if not isinstance(value,str) or len(value)!=64 or any(c not in '0123456789abcdef' for c in value):
        raise ValueError('observation provenance requires lowercase SHA256 values')


def validate_origin(observation, paper=None):
    if KEY not in observation: return
    origin=observation[KEY]
    if not isinstance(origin,dict) or set(origin)!=FIELDS or origin['schema']!='persona.observation-origin.v1' or origin['origin']!=ORIGIN:
        raise ValueError('observation origin has missing or unsupported fields')
    for key in ('candidate_id','paper_id','reviewer_id','operator_id'):
        value=origin[key]
        if not isinstance(value,str) or not value.strip() or len(value)>128:
            raise ValueError('observation provenance identifiers must be bounded nonempty strings')
    for key in HASH_FIELDS:_hash(origin[key])
    if origin['proposed_claim_type'] not in ('explicit_statement','operator_interpretation') or origin['proposed_stance'] not in ('support','challenge'):
        raise ValueError('observation origin needs proposed statement/interpretation and stance labels')
    record=origin['import_record']
    if not isinstance(record,dict) or set(record)!={'handoff_sha256','response_sha256','provenance'}:
        raise ValueError('observation origin needs a complete declared import record')
    _hash(record['handoff_sha256']);_hash(record['response_sha256']);validate_declared_provenance(record['provenance'])
    if origin['reviewed_observation_sha256']!=content_sha256(observation):
        raise ValueError('observation content changed without a new reviewed origin record')
    if paper is not None and (origin['paper_id']!=paper['paper_id'] or origin['source_sha256']!=paper['source_sha256']):
        raise ValueError('observation origin is bound to a different source paper')


def attach(target, source):
    if KEY in source:target[KEY]=copy.deepcopy(source[KEY])
    return target


def inventory(package):
    return [dict(paper_id=paper['paper_id'],observation_index=index,
        observation_origin=copy.deepcopy(observation[KEY]),audit_status='OBSERVATION_ADOPTION_NOT_REPLAYED')
        for paper in package['knowledge']['papers'] for index,observation in enumerate(paper['observations']) if KEY in observation]


def lines(origin, display, prefix='    '):
    result=[prefix+'Observation origin: '+ORIGIN+' (recorded, not authenticated)',
        prefix+'Candidate: '+display(origin['candidate_id'])+'; original proposed labels='+origin['proposed_claim_type']+'/'+origin['proposed_stance'],
        prefix+'Declared reviewer='+display(origin['reviewer_id'])+'; append operator='+display(origin['operator_id']),
        prefix+'Proposal bundle sha256='+origin['proposal_bundle_sha256']+'; review sha256='+origin['operator_review_sha256'],
        prefix+'Append card sha256='+origin['adoption_card_sha256']+'; reviewed content sha256='+origin['reviewed_observation_sha256']]
    record=origin['import_record']
    result.append(prefix+'Declared generation (not authenticated): '+'; '.join(key+'='+display(record['provenance'][key])
        for key in ('provider_id','model_id','run_id','operator_id','execution_location')))
    result.append(prefix+'Handoff sha256='+record['handoff_sha256']+'; response sha256='+record['response_sha256'])
    return result
