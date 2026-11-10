"""Pure, lossless text view of an already prepared local JSON handoff; no CLI."""
import json

from persona import payload_sha256

BEGIN_MARKER = "BEGIN LOCAL HANDOFF JSON"
END_MARKER = "END LOCAL HANDOFF JSON"
VIEW_BOUNDARY = (
    "Local JSON handoff text view; not permission to transmit. "
    "Import binds the JSON handoff, not this text. No model call or network transmission."
)


def render_handoff(handoff):
    """Render without validating, changing or authorizing the supplied handoff."""
    def encoded(value):
        return json.dumps(value, ensure_ascii=True, indent=2, allow_nan=False)
    boundary = encoded(handoff['boundary'])
    digest = payload_sha256(handoff)
    lines = [VIEW_BOUNDARY, boundary, 'handoff_sha256: ' + digest]
    lines.extend(str(index) + '. ' + encoded(instruction)
                 for index, instruction in enumerate(handoff['instructions'], 1))
    lines.extend(['response_contract:', encoded(handoff['response_contract']),
                  'response skeleton:', encoded(dict(handoff_sha256=digest, candidates=[])),
                  BEGIN_MARKER, encoded(handoff), END_MARKER,
                  'handoff_sha256: ' + digest, boundary, VIEW_BOUNDARY])
    return '\n'.join(lines) + '\n'
