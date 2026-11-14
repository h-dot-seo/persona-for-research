"""Opt-in maintainer timing observations; no test, CI or timeout changes."""
import contextlib
import io
import json
import math
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import time
import unittest
from strict_json import loads

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'persona.test-timing.v1'
COUNTS = ('tests', 'failures', 'errors', 'skipped', 'expected_failures', 'unexpected_successes')
STAGES = ('synthetic_walkthrough.py', 'research_journey.py', 'answer_draft.py', 'argument_map.py',
          'review_package.py', 'persona.py', 'observation_input.py', 'model_handoff.py', 'OTHER')
BOUNDARY = ('Local synthetic-test observations, not a speed guarantee or approval. One fresh worker; '
            'module seconds include import and module/class fixtures, test seconds include setUp/tearDown. '
            'Observed subprocess.run calls are attempts, not proof of child execution; nested child-process '
            'calls, prebound aliases and replacement mocks may bypass observation. Stage times overlap '
            'test/module times and must not be added to them. No argv, paths, environment or diagnostics '
            'are reported. No receipt file is saved; tests keep their existing temporary-file behavior. '
            'No caching, timeout changes, skipped coverage or CI changes. Wall time is environment-dependent.')


def module_names():
    manifest = loads((ROOT/'PUBLICATION_MANIFEST.json').read_bytes())
    return sorted('tests.' + Path(row['path']).stem for row in manifest['files']
                  if re.fullmatch(r'tests/test_[a-z0-9_]+\.py', row['path']))


def select_modules(args):
    allowed = module_names()
    if not args: return allowed
    if len(set(args)) != len(args) or any(name not in allowed for name in args):
        raise ValueError('select distinct published tests.test_* modules')
    return list(args)


@contextlib.contextmanager
def quiet_output():
    """Discard Python, buffer and fd writes, while retaining ordinary binary streams."""
    oldout, olderr = sys.stdout, sys.stderr
    descriptors = [os.dup(1), os.dup(2)]
    streams = []
    try:
        with open(os.devnull, 'wb') as sink:
            os.dup2(sink.fileno(), 1); os.dup2(sink.fileno(), 2)
        streams = [io.TextIOWrapper(os.fdopen(os.dup(fd), 'wb'), encoding='utf-8') for fd in (1, 2)]
        sys.stdout, sys.stderr = streams
        yield
    finally:
        for stream in streams:
            try: stream.flush()
            except (OSError, ValueError): pass
        sys.stdout, sys.stderr = oldout, olderr
        for fd, saved in zip((1, 2), descriptors):
            os.dup2(saved, fd); os.close(saved)
        for stream in streams: stream.close()


def elapsed(clock, start):
    value = clock() - start
    if not math.isfinite(value) or value < 0: raise ValueError('invalid clock')
    return value


class TimedResult(unittest.TestResult):
    def __init__(self, clock):
        super().__init__(); self.clock = clock; self.rows = []; self.started = None
    def startTest(self, test):
        super().startTest(test); self.started = self.clock()
    def stopTest(self, test):
        self.rows.append(dict(index=len(self.rows)+1, seconds=elapsed(self.clock, self.started)))
        super().stopTest(test)


def stage_name(args):
    # Only fixed labels, never stringify arbitrary supplied argument objects.
    if isinstance(args, (list, tuple)) and len(args) > 1 and type(args[1]) is str:
        name = args[1].replace('\\', '/').rsplit('/', 1)[-1]
        if name in STAGES: return name
    return 'OTHER'


def observe(modules, loader=None, clock=time.perf_counter):
    loader = loader or unittest.TestLoader()
    started = clock(); rows = []; partial = False
    with quiet_output():
        for name in modules:
            begin = clock(); result = TimedResult(clock)
            stages = {key: dict(calls=0, completed=0, seconds=0.0) for key in STAGES}
            original = subprocess.run
            def observed(*args, **kwargs):
                stage = stages[stage_name(args[0] if args else kwargs.get('args'))]
                stage['calls'] += 1; start = clock()
                try:
                    value = original(*args, **kwargs); stage['completed'] += 1
                    return value
                finally: stage['seconds'] += elapsed(clock, start)
            try:
                subprocess.run = observed
                suite = loader.loadTestsFromName(name)
                suite.run(result)  # One top-level module suite preserves unittest fixture lifetime.
                if result.shouldStop: partial = True
            except BaseException:
                partial = True
            finally:
                subprocess.run = original
            row = dict(module=name, seconds=elapsed(clock, begin), tests=result.testsRun,
                       failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped),
                       expected_failures=len(result.expectedFailures), unexpected_successes=len(result.unexpectedSuccesses),
                       test_times=result.rows, stages=stages, complete=not partial)
            rows.append(row)
            if partial: break
    totals = {key: sum(row[key] for row in rows) for key in COUNTS}
    success = not partial and not any(totals[k] for k in ('failures', 'errors', 'unexpected_successes'))
    return dict(schema=SCHEMA, python=f'{sys.version_info.major}.{sys.version_info.minor}',
                os_family=platform.system() if platform.system() in ('Linux', 'Windows', 'Darwin') else 'OTHER',
                modules=rows, total=dict(totals, seconds=elapsed(clock, started)),
                complete=not partial, success=success, boundary=BOUNDARY)


def fixed_error():
    return dict(schema=SCHEMA, success=False, error='Timing observation could not be completed', boundary=BOUNDARY)


def valid(receipt, modules, code):
    if not isinstance(receipt, dict) or set(receipt) != {'schema','python','os_family','modules','total','complete','success','boundary'}: return False
    if receipt['schema'] != SCHEMA or receipt['boundary'] != BOUNDARY or receipt['python'] != f'{sys.version_info.major}.{sys.version_info.minor}': return False
    if receipt['os_family'] not in ('Linux','Windows','Darwin','OTHER') or type(receipt['complete']) is not bool or type(receipt['success']) is not bool: return False
    rows=receipt['modules']
    if not isinstance(rows,list) or len(rows)>len(modules):return False
    def seconds(v):
        if type(v) not in (int,float): return False
        try: return math.isfinite(v) and v>=0
        except (OverflowError,ValueError): return False
    def counts(row):return all(type(row[k]) is int and row[k]>=0 for k in COUNTS)
    for row,name in zip(rows,modules):
        if not isinstance(row,dict) or set(row)!=set(COUNTS)|{'module','seconds','test_times','stages','complete'} or row['module']!=name:return False
        if not counts(row) or not seconds(row['seconds']) or type(row['complete']) is not bool:return False
        times=row['test_times']
        if not isinstance(times,list) or len(times)>row['tests']:return False
        if row['complete'] and len(times)!=row['tests']:return False
        for i,t in enumerate(times,1):
            if not isinstance(t,dict) or set(t)!={'index','seconds'} or type(t['index']) is not int or t['index']!=i or not seconds(t['seconds']):return False
        stages=row['stages']
        if not isinstance(stages,dict) or set(stages)!=set(STAGES):return False
        for s in stages.values():
            if not isinstance(s,dict) or set(s)!={'calls','completed','seconds'}:return False
            if any(type(s[k]) is not int or s[k]<0 for k in ('calls','completed')) or s['completed']>s['calls'] or not seconds(s['seconds']):return False
    total=receipt['total']
    if not isinstance(total,dict) or set(total)!=set(COUNTS)|{'seconds'} or not counts(total) or not seconds(total['seconds']):return False
    if any(total[k]!=sum(r[k] for r in rows) for k in COUNTS):return False
    complete=len(rows)==len(modules) and all(r['complete'] for r in rows)
    success=complete and not any(total[k] for k in ('failures','errors','unexpected_successes'))
    return receipt['complete']==complete and receipt['success']==success and code==(0 if success else 1)


def worker(modules):
    receipt=observe(select_modules(modules))
    print('\n'+json.dumps(receipt,ensure_ascii=True,allow_nan=False))
    return 0 if receipt['success'] else 1


def main(argv=None):
    try:
        modules=select_modules(list(sys.argv[1:] if argv is None else argv))
        code='import sys; from tests.timing import worker; sys.exit(worker(sys.argv[1:]))'
        process=subprocess.run([sys.executable,'-c',code,*modules],cwd=ROOT,capture_output=True)
        receipt=loads(process.stdout.splitlines()[-1].decode('utf-8'))
        if not valid(receipt,modules,process.returncode):raise ValueError('invalid receipt')
    except (OSError,ValueError,IndexError,KeyError,TypeError,RecursionError):receipt=fixed_error()
    print(json.dumps(receipt,ensure_ascii=True,allow_nan=False))
    return 0 if receipt['success'] else 1


if __name__=='__main__':raise SystemExit(main())
