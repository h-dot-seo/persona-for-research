# persona-for-research 한국어 안내

이 저장소는 공개 학술 근거의 범위 안에서 연구자 페르소나를 구축·검증·활용하는
프레임워크입니다. 영어 README는 [../README.md](../README.md)이고, 이 문서는 같은 내용을
한국어로 안내합니다. 코드, 명령, 파일 이름, 식별자는 원문 그대로 씁니다.

**페르소나는 학술적 시뮬레이션이며 연구자 본인이 아닙니다.** 사적인 믿음, 발표되지 않은
의견, 개인적 기억, 사적 통신은 범위 밖입니다. 이 저장소에는 실제 연구자의 페르소나, 논문
코퍼스, 지식 데이터베이스, 검증 점수가 들어 있지 않습니다.

## 목적

- 한 학자의 **발표된** 추론 방식(질문 설정, 추론, 판단, 반론, 불확실성, 글쓰기 정책)을
  근거에 묶어 표현하는 Persona Core와, 출처가 분명한 학술 내용을 담는 Knowledge Layer를
  분리합니다. 지식을 늘려도 정본(canonical) 추론 정책이 조용히 바뀌지 않습니다.
- 모든 관찰(observation)은 운영자가 직접 큐레이션한 입력이며, 논문 ID, 로케이터, 인용문,
  해시로 출처에 묶입니다. 도구는 해시의 형태와 바인딩의 일관성을 검사할 뿐, 출처가 실제로
  존재하는지, 주장을 뒷받침하는지는 판단하지 않습니다.
- 학습용(training) 근거, 홀드아웃(holdout) 근거, 비교 저자의 근거, 새 외부 근거는 서로
  구분되어야 하며, 검증은 근거 무결성, 예측 평가, 사람 검증, 런타임 검증의 네 축으로 따로
  기록합니다. 설계는 [ARCHITECTURE.md](ARCHITECTURE.md)에, 에이전트용 작업 절차는
  [../SKILL.md](../SKILL.md)에 있습니다.

## 공개 범위

[../PUBLICATION.md](../PUBLICATION.md)의 공개 기록을 요약하면 다음과 같습니다.

- 포함: 프레임워크 개념, 표준 라이브러리만 쓰는 Python 코드, 합성(synthetic) 예제, 테스트,
  빈 기록 템플릿, 에이전트 지침, 공개 검사 도구.
- 제외: 원문 코퍼스, 실제 대화, 특정인의 페르소나 패키지, 연구·실험 데이터베이스, 실제
  검증 결과, 책·논문·그림, 비공개 설정, 자격 증명, 로그, 비공개 Git 이력.
- `PUBLICATION_MANIFEST.json`은 공개 파일의 정확한 목록과 SHA-256을 묶습니다. 목록에 없는
  파일은 거부되며 자동으로 추가되지 않습니다. `python verify_manifest.py`와
  `python audit_publication.py`로 확인합니다. 검사 통과는 익명성이나 저작권 정리의 증명이
  아니며, 사람이 실제 파일을 검토하는 일은 여전히 필요합니다.
- 라이선스는 아직 선택되지 않았습니다. 공개되어 있다는 것만으로 복제, 수정, 재배포 권리가
  생기지 않습니다. [../RIGHTS.md](../RIGHTS.md)와 [../SECURITY.md](../SECURITY.md)를 보세요.

## 설치와 빠른 시작

Python 3.10 이상이면 됩니다. 추가 패키지, 계정, 네트워크 접속은 필요하지 않습니다. 저장소
루트에서, **저장소 밖의 새 디렉터리**를 지정해 합성 데모를 실행합니다. 상위 디렉터리는 이미
있어야 하고, 대상 디렉터리는 미리 만들지 않습니다.

```sh
python synthetic_walkthrough.py ../persona-synthetic-demo
```

이 명령은 실제 CLI 15단계를 실행하고, 이전 실행 결과를 덮어쓰지 않으며, 답변 검토는
보류(deferred) 상태로 남겨 둡니다. 먼저 `reader-scope.txt`를, 그다음 생성된
`START_HERE.txt`를 읽으세요. LLM이나 실제 학자 자료는 사용되지 않습니다. 종료 코드 0과
`COMPLETE.json`이 성공의 기준이며, 상태가 `NOT_VALIDATED`로 끝나는 것은 빠진 설정이 아니라
의도된 안전장치입니다. 자세한 읽기 순서와 실패 시 대처는 [QUICKSTART.md](QUICKSTART.md)에
있습니다.

두 번째 시작 경로인 [내 파일로 첫 검토 여정 만들기](TUTORIAL_OWN_FILES.md)는
세 주제의 합성 원문 여섯 개를 준비하고, 관찰 카드와 패턴을 직접 작성·선택한 뒤
HTML 검토 화면까지 진행합니다. 영어 안내이며 답변·설계·논증 작성은 후속 작업입니다.

출처 → 방법 → 논증을 잇는 통합 경로(27단계)는 다음과 같이 실행합니다.

```sh
python synthetic_walkthrough.py ../persona-research-journey --candidate-source offline-import --research-journey
```

`--recheck-sources`, `--review-method-use`, `--import-method-use`, `--html-review`,
`--import-answers`, `--import-arguments`, `--contextual-answers` 옵션을 더하면 같은 데모가
30단계에서 최대 53단계까지 늘어납니다. 각 옵션의 의미와 먼저 읽을 파일은
[QUICKSTART.md](QUICKSTART.md)와 [WORKFLOWS.md](WORKFLOWS.md#synthetic-walkthrough-routes)에
있습니다. 어떤 경로도 모델을 호출하지 않으며, 최종 답변 판단은 모두 보류 상태로 남습니다.

최소 예제의 바인딩 검사와 테스트는 다음과 같습니다.

```sh
python3 persona.py examples/persona.json examples/knowledge.json
python3 safe_canonical_read.py examples/persona.json
python3 -m unittest discover -v
```

합성 예제에는 학습된 규칙도 논문도 없습니다. 통과했다는 것은 기계적 바인딩이 일관된다는
뜻이며, 어떤 실제 페르소나가 검증되었다는 뜻이 아닙니다. 실제 입력과 생성된 패키지는 이
공개 저장소 밖에 두세요. Windows에서 임시 디렉터리 권한이 제한되어 있으면 `TEMP`와 `TMP`를
쓰기 가능한 디렉터리로 지정한 뒤 테스트를 실행합니다.

기존에 텍스트 모드로 JSON 결과를 출력하던 10개 CLI는 이제 콘솔 코드 페이지와 무관하게
UTF-8(BOM 없음)·LF 바이트를 출력합니다. Windows의 기존 ANSI 인코딩·CRLF 출력은 의도적으로
변경되며, UTF-8·LF를 쓰던 POSIX 출력은 같습니다. 셸 자체의 재인코딩과 덮어쓰기 위험은
남아 있으므로 기본 PowerShell 5 리디렉션을 안전한 저장 방식으로 간주하지 마세요.
이번 변경에는 새 `--output`·`--version` 옵션이 없습니다.
대상 명령과 저장 시 주의점은 [표준 출력 안내](COMMANDS.md#stdout-and-shell-capture)를 보세요.

## 주요 명령

모든 명령은 저장소 루트에서 `python <스크립트>.py ...` 형태로 실행합니다. 입력을 거부하면
0이 아닌 종료 코드로 끝나며, 각 안내서가 정확한 실패 동작과 한계를 설명합니다. 전체 목록과
하위 명령의 정확한 사용법은 [COMMANDS.md](COMMANDS.md)에, 기능별 서술과 경계는
[WORKFLOWS.md](WORKFLOWS.md)에 있습니다. 테스트는 `tests/` 패키지에 있으며 저장소 루트에서
`python -m unittest discover`로 실행합니다(모듈 하나는 `python -m unittest tests.test_<이름> -v`).

| 명령 | 하는 일 | 안내서 |
|---|---|---|
| `synthetic_walkthrough.py` | 번들된 합성 픽스처를 실제 CLI 15~53단계로 실행해 새 외부 디렉터리에 결과를 남김 | [QUICKSTART.md](QUICKSTART.md) |
| `persona.py`, `safe_canonical_read.py` | 페르소나/지식 해시 바인딩 검증, 홀드아웃 식별자를 제거한 투영 | [ARCHITECTURE.md](ARCHITECTURE.md) |
| `observation_input.py` | 제공된 텍스트 구간에 대해 관찰과 인용문을 검증한 뒤 계획 스캐폴드 생성 | [WORKFLOWS.md](WORKFLOWS.md#verified-intake-and-authorized-local-source-files) |
| `prepare_local_manifest.py`, `corpus_files.py` | 명시적으로 허가된 로컬 원문 파일의 해시·섹션 목록 준비와 적재 | [LOCAL_INPUT_PREPARATION.md](LOCAL_INPUT_PREPARATION.md) |
| `research_workflow.py` | 운영자가 큐레이션한 관찰을 질문별 계획 스캐폴드로 적용 | [WORKFLOW_REVIEW.md](WORKFLOW_REVIEW.md) |
| `review_package.py` | 바인딩된 패키지의 읽기 전용 요약 검토 (`--evidence-details`, `--human-validation`) | [EVIDENCE_DETAILS.md](EVIDENCE_DETAILS.md) |
| `compare_releases.py` | 두 패키지의 읽기 전용 비교, 릴리스를 승인하지 않음 | [WORKFLOWS.md](WORKFLOWS.md#review-a-candidate-release-and-a-bound-package) |
| `split_declaration.py` | 분리형 census·split 선언 동결과 패키지 training 대조. 비훈련 ID는 출력하지 않고 개수·해시로 보고 | [SPLIT_DECLARATION.md](SPLIT_DECLARATION.md) |
| `human_validation.py` | 두 패키지 해시에 묶인 분리형 사람 검증 기록: `template`, `check`, `status` | [HUMAN_VALIDATION.md](HUMAN_VALIDATION.md) |
| `extraction_adapter.py`, `model_handoff.py` | 목(mock) 전용 추출 계약과, 별도로 생성된 모델 응답의 오프라인 핸드오프·가져오기 | [MODEL_HANDOFF.md](MODEL_HANDOFF.md) |
| `operator_review.py` | 운영자의 명시적 결정을 별도의 수정 후보에 기록 | [OPERATOR_REVIEW.md](OPERATOR_REVIEW.md) |
| `answer_proposals.py`, `argument_proposals.py` | 근거 범위가 정해진 오프라인 답변·논증 제안과 명시적 채택 | [ANSWER_PROPOSALS.md](ANSWER_PROPOSALS.md), [ARGUMENT_PROPOSALS.md](ARGUMENT_PROPOSALS.md) |
| `research_journey.py`, `journey_inputs.py` | 출처→방법→논증 통합 보고서(JSON/text/HTML)와 고정된 입력 카드 | [RESEARCH_JOURNEY.md](RESEARCH_JOURNEY.md) |
| `persona_cli.py` | 매니페스트 레이블과 Python 버전 표시(`--version`), 루트 스크립트 목록(`list`)과 그중 하나를 어느 디렉터리에서든 그대로 실행(`run <스크립트> [인자...]`); 문서화된 `python <스크립트>.py` 형태가 기본 | [COMMANDS.md](COMMANDS.md#persona_clipy) |

## 경계와 하지 않는 것

- **모델 호출도, 네트워크 접속도 없습니다.** 추출 어댑터는 미리 준비된 응답을 쓰는 목(mock)만
  구현하며, 실제 공급자 어댑터는 비활성화되어 있습니다. `model_handoff.py`는 별도로 허가받은
  도구가 만든 응답 파일을 가져올 뿐, 모델을 실행했다거나 생산자를 인증했다고 주장하지 않습니다.
- **해시는 인증이 아닙니다.** 원문 바이트 해시는 제공된 파일과 일치함을 보여 줄 뿐, 그 파일이
  실제 출판물인지, 학술적으로 옳은지, 재배포 권리가 있는지는 말해 주지 않습니다.
  `authorized: true` 선언은 필수 관문이지 권리의 증명이 아닙니다.
- **의미 검증을 하지 않습니다.** 인용문이 로케이터 위치에 정확히 있는지는 검사하지만, 해석이
  인용문에서 따라 나오는지, 연구자가 그 해석에 동의하는지는 판단하지 않습니다. 반대 근거와
  거부·보류된 항목은 숨겨지지 않고 그대로 보입니다.
- **자동 승인이 없습니다.** 후보 제안은 사람이 명시적으로 검토해야 하며, 보류·거부된 항목은
  조용히 채택되지 않습니다. 검토자 이름은 기록된 선언일 뿐, 사람이 검토했다는 인증이 아닙니다.
- **코퍼스 수집, PDF/OCR, 논문 획득, 의미 추출은 구현되어 있지 않습니다.** 디렉터리를
  스캔하거나 논문을 내려받지 않습니다. 실제 입력과 생성된 패키지는 공개 저장소 밖에 둡니다.
- `safe_canonical_read.py`는 보수적인 편의 투영이며, 익명화 도구나 접근 제어, 공개 필터가
  **아닙니다**. 홀드아웃 분리는 조회 전에 강제해야 하며, 누출을 편집으로 복구하려 하지 마세요.
- 사람 검증 기록(`human_validation.py`)은 이름 붙인 평가자 레이블이 특정 패키지의 나열된
  항목에 대해 남긴 문서화된 주장입니다. 다른 주제로의 일반화, 실제 연구자에 대한 충실도,
  점수가 아니며, 레이블이 서로 다르다는 것이 독립성의 검증은 아닙니다. 페르소나 페이로드의
  `validation.human_validation` 값은 어떤 명령으로도 바뀌지 않습니다.
- 합성 데모의 결과 상태(`NOT_VALIDATED`, `ALL_DEFERRED`, `NOT_PERFORMED`)는 빠진 설정이 아니라
  의도된 경계입니다. 테스트 통과는 기계적 동작만 보여 주며, 과학적 타당성이나 실제 학자
  재현의 증거가 아닙니다. 현재 검증 상태는 [../VALIDATION.md](../VALIDATION.md)에, 날짜별
  전체 이력은 [VALIDATION_HISTORY.md](VALIDATION_HISTORY.md)에 있습니다.

## 문서 색인

**시작과 개요**

- [QUICKSTART.md](QUICKSTART.md) — 합성 데모 실행, 읽는 순서, 실패 시 대처.
- [WORKFLOWS.md](WORKFLOWS.md) — 기능별 서술과 경계를 작업 단위로 묶은 안내.
- [COMMANDS.md](COMMANDS.md) — 모든 스크립트와 하위 명령의 정확한 사용법.
- [ARCHITECTURE.md](ARCHITECTURE.md) — 구축 생애주기, 네 검증 축, 런타임 계약.
- [WORKFLOW_REVIEW.md](WORKFLOW_REVIEW.md) — 합성 CLI 왕복 재현과 실제 학자 평가 전 조건.
- [VALIDATION_HISTORY.md](VALIDATION_HISTORY.md) — 날짜가 붙은 모든 검증 기록.

**원문, 입력, 수동 큐레이션**

- [LOCAL_INPUT_PREPARATION.md](LOCAL_INPUT_PREPARATION.md) — 선택한 로컬 파일의 해시와 섹션 목록 준비.
- [MANUAL_LOCAL_OBSERVATIONS.md](MANUAL_LOCAL_OBSERVATIONS.md) — 출처에 묶인 관찰 카드를 한 번에 하나씩 작성.
- [MANUAL_EVIDENCE_REVISION.md](MANUAL_EVIDENCE_REVISION.md) — 관찰 하나를 감사 파일과 함께 수정.
- [REVISION_IMPACT.md](REVISION_IMPACT.md) — 수정이 과거 답변·설계의 어떤 근거 사용에 영향을 주는지 추적.
- [SOURCE_RECHECK.md](SOURCE_RECHECK.md) — 현재 로컬 바이트와 저장된 인용문 재검사.
- [TOPIC_DISCOVERY.md](TOPIC_DISCOVERY.md) — 검토 전에 존재하는 정확한 주제 범위 확인.
- [EVIDENCE_DETAILS.md](EVIDENCE_DETAILS.md) — 방법을 고르기 전 출처별 근거 점검.

**후보, 출처 이력, 운영자 검토**

- [EXTRACTION_CONTRACT.md](EXTRACTION_CONTRACT.md) — 목(mock) 전용 요청/응답 계약과 필수 사람 검토.
- [MODEL_HANDOFF.md](MODEL_HANDOFF.md) — 저장된 모델 응답의 오프라인 핸드오프와 가져오기.
- [OBSERVATION_PROPOSALS.md](OBSERVATION_PROPOSALS.md) — 첫 관찰 제안, 검토만 하고 정본에 넣지 않음.
- [OBSERVATION_REVISION.md](OBSERVATION_REVISION.md) — 검토된 관찰을 별도 후보에 추가.
- [OPERATOR_REVIEW.md](OPERATOR_REVIEW.md) — 기록된 결정을 별도 수정 후보에 적용.
- [DESIGN_LINEAGE.md](DESIGN_LINEAGE.md) — 후보 검토 수정 하나를 재생해 설계의 근거 경로 추적.
- [DESIGN_CHAIN.md](DESIGN_CHAIN.md) — 연속된 수정 사슬 감사.

**답변, 설계, 논증**

- [REVIEW_WORKSPACE.md](REVIEW_WORKSPACE.md) — 빈 답변·링크·설계 템플릿이 있는 검토 작업 공간.
- [ANSWER_DRAFT.md](ANSWER_DRAFT.md) — 근거에 묶인 답변 주장과 주장별 검토.
- [ANSWER_PROPOSALS.md](ANSWER_PROPOSALS.md) — 오프라인 답변 후보와 명시적 채택.
- [ANSWER_CONTEXT.md](ANSWER_CONTEXT.md) — 답변 제안 전에 방법·출판 맥락 제공.
- [CITATION_EXPLANATIONS.md](CITATION_EXPLANATIONS.md) — 한 주장에 한 구절을 인용한 이유 기록.
- [CITATION_REASONING_AUDIT.md](CITATION_REASONING_AUDIT.md) — 과거 기록의 인용 설명 상태 감사.
- [ARGUMENT_MAP.md](ARGUMENT_MAP.md) — 운영자가 선언한 전제→결론 단계 검토.
- [ARGUMENT_PROPOSALS.md](ARGUMENT_PROPOSALS.md) — 오프라인 논증 연결 제안과 명시적 채택.
- [DESIGN_SCENARIO.md](DESIGN_SCENARIO.md) — 제안된 설계를 추론 링크로 추적.
- [REASONING_LINKS.md](REASONING_LINKS.md) — 관찰 사이의 운영자 링크.
- [PUBLICATION_SCOPE.md](PUBLICATION_SCOPE.md) — 제안의 출판 연도 범위 검토.
- [REVIEW_JOURNEY.md](REVIEW_JOURNEY.md) — 답변과 설계 검토를 한 묶음으로.
- [EVIDENCE_SCOPE.md](EVIDENCE_SCOPE.md) — 독자에게 실제 근거 범위 공개.
- [SYNTHETIC_EVALUATION.md](SYNTHETIC_EVALUATION.md) — 고정된 합성 답변과 홀드아웃 레이블 비교.

**패턴, 맥락, 연대기**

- [PATTERN_HYPOTHESES.md](PATTERN_HYPOTHESES.md) — 출판물을 가로지르는 운영자의 방법 패턴 가설.
- [PATTERN_PROPOSALS.md](PATTERN_PROPOSALS.md) — 모델 보조 패턴 제안과 명시적 검토.
- [APPLICABILITY_REVIEW.md](APPLICABILITY_REVIEW.md) — 출처의 조건을 새 연구 맥락과 나란히 비교.
- [PUBLICATION_CONTEXT.md](PUBLICATION_CONTEXT.md) — 출판물 사이의 선언된 관계.
- [PATTERN_TRANSFER_REVIEW.md](PATTERN_TRANSFER_REVIEW.md) — 패턴을 새 제안으로 옮길 때의 반론과 공백.
- [METHOD_APPLICATION.md](METHOD_APPLICATION.md) — 설계 단계에 대한 패턴 적용 선언.
- [APPLICATION_PROPOSALS.md](APPLICATION_PROPOSALS.md) — 오프라인 적용 제안과 명시적 검토.
- [PUBLICATION_TIMELINE.md](PUBLICATION_TIMELINE.md) — 연도별 질문·방법·근거.

**통합 여정**

- [RESEARCH_JOURNEY.md](RESEARCH_JOURNEY.md) — 출처→방법→논증 통합 보고서.
- [LOCAL_HTML_REVIEW.md](LOCAL_HTML_REVIEW.md) — 읽기 전용 로컬 HTML 보기.
- [JOURNEY_INPUTS.md](JOURNEY_INPUTS.md) — 입력 파일을 고정하고 다시 열기.
- [JOURNEY_COMPARISON.md](JOURNEY_COMPARISON.md) — 고정된 두 여정 비교.
- [INTEGRATED_WORKSPACE.md](INTEGRATED_WORKSPACE.md) — 빈 패턴·맥락·논증 양식으로 시작하는 통합 검토.

**검증과 예제**

- [HUMAN_VALIDATION.md](HUMAN_VALIDATION.md) — 패키지 해시에 묶인 분리형 평가자 기록.
- [REVIEW_ATTRIBUTION_EXAMPLE.md](REVIEW_ATTRIBUTION_EXAMPLE.md) — 리뷰가 보고한 방법과 자체 권고의 구별.
- [TRAJECTORY_CONDITIONS_EXAMPLE.md](TRAJECTORY_CONDITIONS_EXAMPLE.md) — 출판 변화와 조건 변화의 구별.

**저장소 루트 문서**

- [../README.md](../README.md) — 영어 개요와 문서 색인.
- [../SKILL.md](../SKILL.md) — 에이전트용 작업 절차.
- [../PUBLICATION.md](../PUBLICATION.md) — 공개 추출 기록과 매니페스트 규칙.
- [../SECURITY.md](../SECURITY.md) — 보안과 공개 경계.
- [../RIGHTS.md](../RIGHTS.md) — 권리와 제3자 자료.
- [../VALIDATION.md](../VALIDATION.md) — 현재 검증 스냅숏.

로컬 입력을 준비하기 전에 `prepare_local_manifest.py --report-defects`로 선택 파일 전체의 구조를 읽기 전용으로 확인할 수 있습니다. [안내](LOCAL_INPUT_PREPARATION.md).

오프라인 핸드오프의 `prepare --format text`는 별도로 승인된 로컬·원격 도우미에 붙여넣을 수 있는 전체 JSON 기반 텍스트를 만듭니다. 전송 허가가 아니며 모델을 호출하지 않습니다. 기본 JSON과 import 바인딩은 그대로이고 `response-template`은 JSON 전용입니다. [형식과 크기 경계](MODEL_HANDOFF.md#pasteable-local-handoff-view)를 확인하세요.

## 결과 파일의 배타 저장

결과 명령의 `--output NEW_FILE`은 기존 파일을 덮어쓰지 않고 UTF-8 바이트를 저장하며, stdout에는 해시·경로가 담긴 영수증만 냅니다. 경로도 개인정보일 수 있습니다. [범위와 실패 경계](EXCLUSIVE_OUTPUT.md)를 확인하세요. 검증기·기존 디렉터리 writer는 그대로입니다.

## 버전 레이블 확인

`python persona_cli.py --version`은 스크립트 옆 매니페스트의 `release`·`date`와
실행 중인 Python 버전을 읽기 전용으로 표시합니다. 현재 디렉터리와 무관하며,
`list`와 도움말에서는 매니페스트를 읽지 않습니다. 잘못된 UTF-8/JSON, 중복 키,
비유한 수, 크기·깊이 한도 초과, 잘못된 레이블은 종료 코드 1로 거부합니다.
릴리스 레이블은 ASCII 이스케이프된 JSON 문자열로 표시합니다.

**무결성 검사나 서명이 아닙니다.** 매니페스트는 자신의 해시를 포함하지 않으므로
레이블은 인증되지 않았습니다. 파일 해시도 검사하지 않습니다. 저장소 루트에서
`python verify_manifest.py`로 별도의 파일 목록·해시 일치 검사를 실행하세요.
이 검사도 게시자 인증이나 과학적 타당성을 입증하지 않습니다. 모델·네트워크 호출과
파일 쓰기는 없으며, 패키징·태그·라이선스 결정은 바꾸지 않습니다.
자세한 한도와 동작은 [버전 레이블](COMMANDS.md#version-labels)을 보세요.
