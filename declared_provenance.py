"""Validate bounded declared model identity without authenticating it."""

PROVENANCE_FIELDS = {'provider_id', 'model_id', 'run_id', 'operator_id', 'execution_location'}


def validate_declared_provenance(provenance):
    """Validate a bounded operator declaration, never authenticate its producer."""
    if not isinstance(provenance, dict) or set(provenance) != PROVENANCE_FIELDS:
        raise ValueError('declared provenance has missing or unsupported fields')
    for key in PROVENANCE_FIELDS:
        value = provenance[key]
        if not isinstance(value, str) or not value.strip() or len(value) > 128:
            raise ValueError('declared provenance fields must be nonempty strings of at most 128 characters')
        if any(ord(character) < 32 or ord(character) == 127 for character in value):
            raise ValueError('declared provenance fields cannot contain control characters')
    if provenance['execution_location'] not in ('local', 'remote', 'unknown'):
        raise ValueError('declared execution_location must be local, remote or unknown')

