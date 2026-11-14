"""Opt-in synthetic capacity observations; no optimization, cached validation or product limits."""
import argparse
from contextlib import ExitStack, contextmanager
import hashlib
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch

import persona
import research_workflow as rw
import research_journey as journey
import review_package
from exclusive_output import check_path
from journey_inputs import _plain_components
from tests import scale_fixture

ROOT=Path(__file__).resolve().parents[1]
BOUNDARY=('Index-generated synthetic declarations only; no real data, provider, source reread or research approval. '
    'S counts accepted argument steps, not recursive adoption history depth. No imported contextual answer/pattern '
    'history is modeled. Timing includes observer overhead and is not a speed guarantee. Hash observation adds '
    'one canonical serialization per actual hash invocation; nested calls count as actual separate invocations. '
    'Module aliases sharing the same original function receive one wrapper, not stacked wrappers. Dynamically '
    'loaded aliases after observer entry may be missed. No caching, optimization, CI or timeout changes. '
    'Grid dimensions are experiment bounds, not product input limits. Failed writes retain partial files; '
    'READY existence alone is not success and may itself be partial.')
MAX_RESULT_BYTES=16*1024*1024
MAX_CASES=16


def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')


def encoded(value):
    return (json.dumps(value,ensure_ascii=True,sort_keys=True,indent=2,allow_nan=False)+'\n').encode('utf-8')


@contextmanager
def counter():
    originals={'build':rw.build,'validated_source_rules':rw.validated_source_rules,'apply':rw.apply,'payload_sha256':persona.payload_sha256}
    counts={k:0 for k in originals};counts['hash_serialized_bytes']=0
    wrappers={}
    for name,original in originals.items():
        def wrapper(*args,_name=name,_original=original,**kwargs):
            counts[_name]+=1
            if _name=='payload_sha256':counts['hash_serialized_bytes']+=len(canonical(args[0] if args else kwargs['value']))
            return _original(*args,**kwargs)
        wrappers[name]=wrapper
    with ExitStack() as stack:
        for module in list(sys.modules.values()):
            file=getattr(module,'__file__',None)
            if not file:continue
            try:local=Path(file).resolve().parent==ROOT
            except (OSError,RuntimeError):continue
            if not local:continue
            for attribute,value in list(vars(module).items()):
                for name,original in originals.items():
                    if value is original:stack.enter_context(patch.object(module,attribute,wrappers[name]));break
        yield counts


def stage(name, operation, serializer):
    start=time.perf_counter();value=None;raw=None
    with counter() as counts:
        try:
            value=operation();raw=serializer(value)
            row=dict(stage=name,success=True,output_bytes=len(raw),output_sha256=hashlib.sha256(raw).hexdigest(),
                     semantic_sha256=hashlib.sha256(canonical(value)).hexdigest() if not isinstance(value,str) else None)
        except Exception as exc:
            # Only generated synthetic inputs reach these APIs. Preserve bounded API rejection text, not traceback.
            reason=str(exc)[:512] if isinstance(exc,(ValueError,TypeError,RecursionError)) else 'Unexpected workload failure; diagnostics withheld'
            row=dict(stage=name,success=False,error_type=type(exc).__name__,reason=reason)
    row.update(counts=dict(counts),seconds=time.perf_counter()-start)
    return row,value


def observe(n,k,c,s):
    scale_fixture.dimensions(n,k,c,s)
    rows=[]
    row,args=stage('fixture',lambda:scale_fixture.build(n,k,c,s),encoded);rows.append(row)
    result=dict(schema='persona.capacity-observation.v1',dimensions=dict(N=n,K=k,C=c,S=s),stages=rows,
                success=False,boundary=BOUNDARY)
    if not row['success']:return result
    # This models file byte load totals only; APIs have their own serialization contracts.
    file_bytes=sum(len(encoded(value)) for value in args if value is not None and not isinstance(value,str))
    result['supplied_file_bytes']=file_bytes
    result['computed_cli_combined_8mib_exceeded']=file_bytes>8*1024*1024
    result['computed_cli_limit_is_not_an_api_rejection']=True
    operations=[('journey_inspect',lambda:journey.inspect(*args),journey.encode_result),
                ('journey_render',lambda:journey.render(*args),lambda v:v.encode('utf-8')),
                ('package_review',lambda:review_package.render(args[0],scale_fixture.QUESTION,scale_fixture.TOPIC),lambda v:v.encode('utf-8'))]
    for name,operation,serializer in operations:
        row,_=stage(name,operation,serializer);rows.append(row)
        if row['success']:row['output_input_ratio']=row['output_bytes']/file_bytes
    result['success']=all(r['success'] for r in rows)
    return result


def destination(path):
    _plain_components(Path(path).absolute().parent)
    return check_path(path)


def run(cases,output):
    if not 1<=len(cases)<=MAX_CASES:raise ValueError('runner allows 1 to 16 cases')
    if len({tuple(case) for case in cases})!=len(cases):raise ValueError('duplicate cases are not allowed')
    for case in cases:scale_fixture.dimensions(*case)
    target=destination(output);target.mkdir(exist_ok=False)
    summary=[]
    for i,case in enumerate(cases):
        result=observe(*case);raw=encoded(result)
        if len(raw)>MAX_RESULT_BYTES:raise ValueError('capacity receipt exceeds 16 MiB')
        name=f'case-{i+1:03d}.json'
        with (target/name).open('xb') as stream:
            if stream.write(raw)!=len(raw):raise OSError('partial capacity receipt retained')
        summary.append(dict(file=name,sha256=hashlib.sha256(raw).hexdigest(),success=result['success']))
    success=all(row['success'] for row in summary)
    final=dict(schema='persona.capacity-run.v1',success=success,results=summary,boundary=BOUNDARY)
    raw=encoded(final)
    # Every stage rejection is retained in its case file. A failed grid has no READY.
    name='READY.json' if success else 'FAILED.json'
    with (target/name).open('xb') as stream:
        if stream.write(raw)!=len(raw):raise OSError('partial completion marker retained')
    return final


def case_value(text):
    try:
        values=tuple(int(x) for x in text.split(','))
        if len(values)!=4:raise ValueError()
        scale_fixture.dimensions(*values)
        return values
    except ValueError:raise argparse.ArgumentTypeError('case must be N,K,C,S with 1<=N,K,C<=32 and 1<=S<=C')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('output',type=Path,metavar='NEW_DIR')
    p.add_argument('--case',type=case_value,action='append',metavar='N,K,C,S')
    args=p.parse_args()
    try:result=run(args.case or [(1,1,1,1)],args.output)
    except (ValueError,OSError,RuntimeError,TypeError,RecursionError):
        p.exit(1,'Capacity run failed; any partial directory/files are retained.\n')
    print(encoded(result).decode('utf-8'),end='')
    return 0 if result['success'] else 1


if __name__=='__main__':raise SystemExit(main())
