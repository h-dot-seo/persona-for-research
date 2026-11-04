"""Validate operator-curated reasoning components without inventing missing content."""
import copy

DIMENSIONS = ('question_framing', 'alternative_explanation', 'evidence_standard',
              'falsification_check', 'uncertainty')
REVIEW_FIELDS = ('origin', 'candidate_id', 'candidate_bundle_sha256',
                 'operator_review_sha256', 'proposed_claim_type')


def validate_components(components):
    if not isinstance(components, dict) or any(k not in DIMENSIONS for k in components):
        raise ValueError('reasoning must map supported dimensions to evidence records')
    for dimension, record in components.items():
        if not isinstance(record, dict):
            raise ValueError('reasoning component must be an object')
        for field in ('text', 'locator', 'evidence_quote'):
            if not isinstance(record.get(field), str) or not record[field].strip():
                raise ValueError('reasoning component needs text, locator and evidence_quote')
        if record.get('claim_type') not in ('explicit_statement', 'operator_interpretation'):
            raise ValueError('reasoning component must distinguish statement from interpretation')
        if any(k in record for k in REVIEW_FIELDS):
            if any(k not in record for k in REVIEW_FIELDS):
                raise ValueError('review provenance must be complete')
            if record['origin'] not in ('operator_reviewed_mock_candidate', 'operator_reviewed_imported_candidate'):
                raise ValueError('unsupported reviewed candidate origin')
            if not isinstance(record['candidate_id'], str) or not record['candidate_id'].strip():
                raise ValueError('review provenance needs a candidate ID')
            for field in ('candidate_bundle_sha256', 'operator_review_sha256'):
                digest = record[field]
                if not isinstance(digest, str) or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
                    raise ValueError('review provenance needs valid payload hashes')
            if record['proposed_claim_type'] not in ('explicit_statement', 'operator_interpretation'):
                raise ValueError('review provenance needs a supported proposed claim type')


def card(rule):
    components = rule.get('reasoning', {})
    validate_components(components)
    if not components:
        return None
    return dict(rule_id=rule['rule_id'], paper_id=rule['paper_id'],
                source_kind=rule['source_kind'], year=rule['year'],
                evidence_stance=rule['stance'], condition=rule['condition'],
                limitation=rule['limitation'], components=copy.deepcopy(components),
                missing_dimensions=[d for d in DIMENSIONS if d not in components],
                attribution=rule['attribution'], status='CURATED_REASONING_REQUIRES_REVIEW',
                inference_boundary='These are paper-linked curated records, not private thoughts '
                'or proof of an individual author reasoning process. Quote matching does not '
                'establish semantic support. No missing component is inferred.')
