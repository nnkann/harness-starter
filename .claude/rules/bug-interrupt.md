# Bug Interrupt 규칙 — 스코프 외 버그 자율 판단

defends: P1

작업 도중 스코프 외 버그를 발견했을 때 "중단 / 기록 후 속행 / 무시"를
즉각 판단하는 절차. anti-defer.md(미루기 차단)·no-speculation.md(추측 금지)·
self-verify.md(완료 전 AC 검증)의 **발견 시점** 갭을 메운다.

판단 기준의 SSOT는 이 파일이 독립 정의하지 않는다:
- Q1 기준 → `rules/security.md` "절대 금지" 범위
- Q2 기준 → 현재 wave의 **AC** (Goal + 검증 묶음을 직접 Read)
- Q3 기준 → 현재 wave의 **CPS P#** (project_kickoff.md Problems 섹션)

## 트리거

스코프 외 버그·이슈를 발견한 **즉시** 이 규칙을 적용한다.
"나중에 처리"·"현재 wave 완료 후"는 anti-defer.md 위반이다.

## 3단계 결정 트리

```
Q1: 이 버그가 조용히 merged되면 최악의 경우
    데이터 손상·보안·인증·시크릿 노출이 발생하는가?
    (security.md "절대 금지" 4개 항목 참조)

  YES → 즉시 현재 wave 중단 + 사용자 알림
  NO  → Q2

Q2: 이 버그가 현재 wave AC의 전제를 파괴하는가?
    현재 WIP의 AC Goal·검증 묶음을 직접 Read한 뒤 판단.
    "이 버그가 있으면 AC 체크박스가 거짓 통과되는 이유: ___"
    — 이유를 한 줄로 채울 수 없으면 NO 강제

  YES → wave 중단 또는 AC 재정의 + 사용자 합의 요청
  NO  → Q3

Q3: 이 버그가 나중에 자동으로 발견되기 어려운가?
    조용한 실패 / 다운스트림 전파 / 재현 어려움 중 하나라도 해당하면 YES

  YES → WIP 즉시 기록 + CPS P# 즉시 매칭 + 현재 wave 속행
  NO  → 무시 가능 (근거 명시 필수)
```

## 판단 블록 형식 (YES 판단 시 필수)

각 Q의 YES 판단은 반드시 근거 한 줄이 있어야 한다.
근거 없으면 판단을 재실행한다.

```
[BIT 판단]
Q1: YES|NO — [근거]
Q2: YES|NO — [근거 또는 "이유 없음 → NO 강제"]
Q3: YES|NO — [근거]
결정: STOP | REDEFINE | NOTE | IGNORE
```

## Q1 인플레이션 방지

Q1 YES가 되려면 다음 중 하나가 반드시 참이어야 한다:

- DB write/delete 경로에 직접 영향
- 인증·권한 검사 우회 가능성
- 외부 시스템으로 데이터 유출 경로
- 시크릿 평문 노출

내부 회귀·UI 버그·테스트 실패는 Q1 대상 아님 → Q2로 이동.

세션당 Q1=YES가 2회 초과하면 정의 좁히기 재확인:
> "Q1=YES가 이번 세션 [N]회째입니다. 위 4개 조건 중 해당 항목을 명시하세요."

## 도메인 컨텍스트 (조건부 분기 재정의)

숫자 가중치 대신 조건부 분기 재정의를 사용한다:

- 변경 파일 경로에 `auth/`, `security/`, `migration/` 포함
  → Q1 YES 조건 중 하나 해당 여부를 먼저 적극 검토 (YES 전제로 시작)
- 버그가 공개 API 경계 또는 다운스트림 직접 사용 경로에 있음
  → Q3 = YES 강제

## Q3 hit — WIP 기록 + CPS P# 즉시 매칭

Q3=YES이면 현재 wave를 속행하면서 아래 두 단계를 즉시 수행한다.

### 1. WIP 섹션 기록

현재 WIP 파일 하단에 `## 발견된 스코프 외 이슈` 섹션이 없으면 추가한다.
항목 형식:

```
## 발견된 스코프 외 이슈

- [버그 설명 1~2줄] | 발견: [Step명/파일명] | P#: [아래 매칭 결과]
```

### 2. CPS P# 즉시 매칭

**HARNESS_MAP.md 우선 진입** (`.claude/HARNESS_MAP.md` CPS 테이블):
- 발생 위치(파일·스킬명)를 MAP의 Rules/Skills/Agents/Scripts 섹션에서 찾는다
- 해당 행의 `defends` 컬럼 → Problem 특정
- 테이블 1행으로 충분 — `project_kickoff.md` 전체 Read 불필요

MAP에서 특정 불가 시에만 `docs/guides/project_kickoff.md` Problems 섹션 Read.

| 매칭 결과 | 기록 형식 |
|----------|----------|
| 기존 P# 해당 | `P#` 명시 (예: `P3`) |
| 모호 — 가장 가까운 P# | `P# (부분)` 명시 |
| 어느 P#에도 해당 없음 | `NEW — "[버그 핵심어]"` 플래그 |

`NEW` 플래그가 있는 항목은 다음 implementation Step 0에서 CPS 신규 P#
등록 후보로 자동 인식된다. P# 추가는 Claude 단독 판단 가능
(docs.md "CPS 변경 권한" 참조). Solution 정의는 owner 승인 필요.

## 결정별 행동

| 결정 | 행동 |
|------|------|
| STOP (Q1=YES) | 현재 wave 즉시 중단. 사용자에게 Q1 근거 알림. wave 재개 여부는 사용자 결정 |
| REDEFINE (Q2=YES) | wave 중단 또는 AC 재정의. "Q2 트리거: [AC 항목] 전제 파괴됨. 중단 또는 AC 재정의?" 사용자 합의 |
| NOTE (Q3=YES) | WIP 기록 + CPS P# 매칭. 현재 wave 속행 |
| IGNORE (전부 NO) | 무시. "Q3=NO: [이유]" 판단 블록에 명시 |

## 순환 루프 연결

BIT는 단방향 작업 흐름을 순환 구조로 연결하는 고리다:

```
작업 중 발견
    ↓ BIT Q1/Q2/Q3 판단
Q3=YES → WIP 기록 + CPS P# 즉시 매칭
    ↓ 세션 시작마다 (session-start.sh — Phase 2 완료)
"## 발견된 스코프 외 이슈" 섹션 감지 → 사용자 알림
    ↓ 다음 implementation Step 0
NEW 플래그 → CPS 신규 P# 등록 후보 인식
    ↓ CPS 갱신 → cluster 갱신
다음 작업이 더 풍부한 유산 위에서 시작  ← 루프
```

## 수동 가이드 (debug-guard.sh — hook 무력화됨)

> **2026-05-13 변경 (hn_harness_recovery_v0_41_baseline Phase 1)**:
> 기존 `debug-guard.sh` UserPromptSubmit hook은 **무력화**됨 (settings.json
> 등록 해제). hook이 LLM 행동을 강제하지 못하는 패턴 실측 — P8/P9 자기
> 증명. 스크립트 파일 자체는 보존되어 수동 호출 또는 후속 재설계에 사용
> 가능.

본 규칙은 "발견 즉시 적용"을 전제로 한다. 자가 발화 의존 한계는 인정하되,
hook 강제력 0이 실측됐으므로 다음을 가이드로 활용:

- **키워드 사전 SSOT**: `.claude/scripts/debug-guard.sh` (수동 참조용)
  Claude가 작업 중 사용자 발화에 이 키워드가 등장하면 BIT Q1/Q2/Q3 적용
  자가 점검 권장
- **자가 인지 의무**: Q1/Q2/Q3 작성·CPS 매칭은 자가 인지 영역 — hook
  유무와 무관하게 본 규칙이 정의한 절차 준수

## 기존 rules와의 관계

| 규칙 | 커버 시점 | BIT와의 관계 |
|------|----------|-------------|
| anti-defer.md | 미루기 결정 후 | BIT가 미루기 결정 자체를 차단 |
| no-speculation.md | 추측 수정 전 | BIT 판단 근거 명시 강제가 추측 차단 |
| self-verify.md | 완료 직전 AC 검증 | BIT는 작업 도중 — 타이밍 다름 |
| security.md | 보안 게이트 | Q1 정의의 SSOT |
| HARNESS_MAP.md | 역추적 지도 | BIT Q3=YES 시 P# 매칭 진입점 — 발생 위치 → defends 컬럼 → Problem 특정 |

## 위반 감지

- `## 발견된 스코프 외 이슈` 섹션 없이 "나중에 처리" 표현 → anti-defer.md 위반
- Q1/Q2/Q3 판단 블록 없이 스코프 외 이슈를 무시 → no-speculation.md 위반
- Q3=YES 기록 후 CPS P# 매칭 없음 → 이 규칙 위반 (순환 루프 단절)
