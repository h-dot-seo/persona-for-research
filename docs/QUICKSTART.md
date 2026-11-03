# Run the complete synthetic journey

처음에는 이 합성 예제로 전체 흐름을 실행하세요. 실제 연구자 자료나 API 키는 필요하지
않습니다. 결과는 학자 재현이나 과학적 검증이 아니라, 근거를 보존하며 검토 파일을
연결하는 작동 예시입니다. 실제 LLM은 호출하지 않습니다.

Python 3.10+ only; no third-party packages, account or network access required.
From the repository root, choose a **new directory outside this repository** whose
parent already exists. Do not create the final directory first:

```
python synthetic_walkthrough.py ../persona-synthetic-demo
```

The same script works from another working directory when called by its full path.
Spaces and Unicode in the destination are supported. Do not put output under the
repository: the publication inventory deliberately rejects unlisted artifacts.
The runner rejects existing files/directories (even empty ones), missing parents
and symlink path components. It never overwrites or deletes an earlier run.

## What to read first

Open the generated `START_HERE.txt`. Read these files in order:

1. `reader-scope.txt`: answer draft, uncertainty, declared review state, source groups
   and active/unused scope. It is not an approved final answer.
2. `review-packet.txt`: which exact source record each answer claim and design step
   uses, including counterevidence and publication-year warnings.
3. `argument-map.txt`: explicit operator premises, bridge and assumptions. The
   missing defeater and uncited conclusion remain visible.
4. `timeline.txt`: the two synthetic publication dates and research/review labels.
5. `lineage.json`: replay of the single declared mock-candidate review, not full
   history authentication or scientific approval.

Success requires exit code zero **and** `COMPLETE.json`. Its status ends in
`NOT_VALIDATED`; answer review is `ALL_DEFERRED`. These are intentional safeguards,
not missing setup. The demo executes 15 existing CLI commands and records their
actual argument arrays and return codes in `commands.json`. Those arrays are a
reproducibility/debug record, not shell commands to paste blindly.

## What the demo actually does

The bundled corpus contains invented observations and short synthetic quotations.
The runner supplies a later review criterion and a challenge stance, then:

- Runs observation intake with exact stored quote/segment checks.
- Calls the canned-response `MockProvider`, **not an LLM**.
- Shows a deferred candidate review template and available targets.
- Applies two **fixed synthetic fixture decisions** to a new revision. This is not
  a general auto-approval rule; both reviewed claims remain operator interpretations.
- Creates bound link, design, answer and argument templates, then fills them with
  explicitly invented operator text in the runner.
- Leaves every answer review deferred. It preserves missing design falsification
  and alternative explanation, missing argument defeater and an uncited conclusion.
- Executes timeline, integrated review, reader-scope, argument-map and lineage CLIs.

The question asks how to distinguish two synthetic explanations. Its later review
criterion is deliberately used with an earlier reference year so the timing warning
is easy to see. Source hashes are fixture declarations, not new file-byte checks or
proof of scholarly authenticity. No real author corpus or withheld evaluation is used.

## Failures and retry

If a stage fails or times out, the runner exits nonzero, attempts to save `FAILED.txt`
and `commands.json`, and does not write `COMPLETE.json`. A command with a null return
code was attempted but did not return normally. Earlier successful artifacts stay in
place for diagnosis; they do not establish a complete run. No failed stage is retried
automatically. If the filesystem itself prevents error-file writing, stderr remains
the failure report. Choose a different new destination after resolving the error.

An existing destination is always refused. Nothing is cleaned up automatically.
Keep generated outputs private when using related tools on your own authorized
material. This demo accepts **no corpus, provider or credential argument**, so it is
not a shortcut for sending actual research material to a model.

## Move beyond the demo deliberately

The runner is a fixed educational scenario, not a generic corpus wizard. Do not
reuse its synthetic accept decisions for real candidate outputs. For real work,
resolve author identity and source rights, choose training/holdout scope, curate
observations and review each candidate explicitly. Real human review is not
established by writing a reviewer name. Follow the individual module docs linked
from README; external model integration remains disabled.

After changing any draft, link, package or recorded review, regenerate the affected
bindings and review the change. Do not hand-edit hashes merely to bypass stale-input
errors. The full workflow has no automated source acquisition, actual researcher
fidelity benchmark or scientific certification.

Regression checks:

```
python -m unittest test_synthetic_walkthrough -v
```

The suite executes the complete real-CLI journey in a temporary external directory
and checks failures, path safety and input preservation. The symlink test may skip
when the platform does not permit creating symlinks; other path tests still run.
