"""Opt-in static-label rejection details for manual cards and local source selections; not a general diagnostic API."""
from strict_json import _key_diagnostic

MAX_DETAIL_BYTES=512
LABELS=('manifest','card','selection','package')
CONTRACTS={
 'local-selection':({'author_id','version','build_id','papers'},set()),
 'paper-selection':({'paper_id','author_id','split','runtime_knowledge_eligible','authorized','locator','kind','year','topic','source_file','observations'},{'source_sha256','input_inventory'}),
 'source-selection':({'schema','package_sha256','operator_id','sources'},set()),
 'source-selection-row':({'paper_id','source_file'},set()),
 'append-card':({'schema','manifest_sha256','paper_id','observation'},set()),
 'revision-card':({'schema','manifest_sha256','paper_id','observation_index','previous_observation_sha256','observation','operator_id','revision_reason','new_version','new_build_id'},set()),
 'manual-observation':({'method','condition','limitation','locator','topic','evidence_quote','claim_type'},{'stance','reasoning'}),
 'manual-stance':({'stance'},{'method','condition','limitation','locator','topic','evidence_quote','claim_type','reasoning'}),
 'manual-component':({'text','locator','evidence_quote','claim_type'},set()),
}

class InputRejected(ValueError):
    """ValueError text/args remain unchanged; only explicit CLI use adds a detail line."""
    def __init__(self,message,detail):
        super().__init__(message)
        self.detail=detail


def closed_rejection(message,value,contract,label):
    if type(value) is not dict or label not in LABELS:return ValueError(message)
    required,optional=CONTRACTS[contract]
    # Never stringify or sort untrusted keys. Non-string Python API keys get no detail.
    if any(type(key) is not str for key in value):return ValueError(message)
    missing=sorted(required-value.keys());unsupported=sum(key not in required|optional for key in value)
    if not missing and not unsupported:return ValueError(message)
    line='  input='+label+'; missing=['+', '.join(_key_diagnostic(k) for k in missing[:8])+']'
    if len(missing)>8:line+='; additional_missing='+str(len(missing)-8)
    line+='; unsupported_count='+str(min(unsupported,9999))+('+' if unsupported>9999 else '')
    assert line.isascii() and len(line.encode('ascii'))<=MAX_DETAIL_BYTES
    return InputRejected(message,line)


def load_input(loader,path,label,explain):
    try:return loader(path)
    except ValueError as exc:
        if not explain:raise
        # Only the individual loader is running here; no cross-input attribution.
        if label not in LABELS:raise
        raise InputRejected(str(exc),'  input='+label) from exc


def exit_rejected(parser,exc,explain):
    message=str(exc)+'\n'
    if explain and isinstance(exc,InputRejected):message+=exc.detail+'\n'
    parser.exit(1,message)
