"""In-process check receipt, not a signature or a Python security boundary."""
from persona import payload_sha256


class VerifiedCorpus(dict):
    """Preserve which checks ran while rejecting JSON-supplied status labels.

    Trusted Python callers can construct objects; this is not authentication.
    The digest detects mutations after intake and the receipt is lost on JSON
    serialization. Serialized corpora must pass intake again to regain status.
    """
    def __init__(self, corpus, local_source_ids=()):
        super().__init__(corpus)
        self.receipt_sha256 = payload_sha256(corpus)
        self.local_source_ids = frozenset(local_source_ids)

    def unchanged(self):
        return self.receipt_sha256 == payload_sha256(self)
