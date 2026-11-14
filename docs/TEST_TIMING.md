# Opt-in synthetic test timing

This is a maintainer/contributor observation tool, not a speed claim, public input
capacity guarantee or replacement for the full suite. The CI matrix, normal
`python -m unittest discover -v`, test bodies and timeouts remain unchanged.

```sh
python -m tests.timing tests.test_skill_contract
```

The guide command runs the three real static skill-contract tests. Omit module
arguments to observe all published `tests.test_*` modules, or supply distinct
published module names in the intended execution order. Arbitrary paths, modules
and individual test selectors are rejected. The publication manifest supplies
this local allowlist, not an authenticity guarantee. Run from the repository root.

One fresh worker runs selected modules sequentially, each as a top-level unittest
suite. Module import and module/class fixture setup/teardown are included in module
time; each startTest/stopTest interval includes individual setup/teardown. Per-test
rows use sequential indexes, not potentially private test identifiers. Fixture
lifetime and suite ordering are preserved. The worker total excludes process
startup, but includes orchestration. Tests retain their existing temporary-file
behavior; no receipt file is created by the observer. No cache is introduced.

A temporary subprocess.run wrapper observes attempts through that function during
each module, with counts, completed returns and elapsed time. Labels are restricted
to a small fixed script-name list; everything else is OTHER. It does not report
argv, paths, environment, hostnames, platform builds or failure text. An observed
attempt is not proof a child executed, and a completed return need not mean exit 0.
Mocks that replace the wrapper, prebound aliases, subprocess.Popen and subprocesses
inside children bypass it. Stage times overlap test/module times; do not add them.
The original function is restored in finally, including on interruption.

Python stdout/stderr are real binary-backed streams during execution, so tests
using stdout.buffer still work. Python and fd output, including inherited child
output, is discarded in the worker; the parent also privately captures worker
output and validates the final strict JSON receipt before emitting anything.
Malformed or incomplete worker receipts produce only a fixed non-success message.
No test diagnostics are forwarded. The runner is not a security sandbox for
malicious test code and does not stop tests from performing their documented work.

Receipt `persona.test-timing.v1` contains Python major.minor and OS family only,
module/test/stage timings, aggregate unittest counts and complete/success flags.
Failures, errors, unexpected successes and partial execution produce nonzero exit.
Skips and expected failures are counted according to unittest semantics and do not
alone fail a completed run. Keyboard interruption can produce a partial report;
missing modules or failed fixture setup appear as unittest errors. Partial reports
are never successful. Local wall-clock observations are environment-dependent;
no duration threshold, performance promise, scientific judgment or approval follows.
