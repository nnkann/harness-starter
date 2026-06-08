---

title: debug-specialist 에이전트 신설 — 막힐 때 자동 위임처 확보
domain: harness
tags: [agent, debug, escalation]
problem: P1
s: [S1]
status: completed
created: 2026-04-25
updated: 2026-04-25
---

# debug-specialist 에이전트 신설

## 배경

에이전트 풀 8개 중 "구현 중 막혔을 때" 쓸 에이전트가 없음. 분석·조사·위험·
성능·문서 탐색은 있는데 디버그 전담이 빠져 있어 "사용자 보고"로 직행.

1회 실패 후 같은 접근법이 반복 실패하는 케이스가 많으므로 **1회 실패 즉시 호출**.

## codebase-analyst와의 구분

통합하지 않는다. 목적·시점이 다르다.

| | codebase-analyst | debug-specialist |
|--|-----------------|-----------------|
| 시점 | 작업 **시작 전** | 작업 **중** 막혔을 때 |
| 목적 | 기존 패턴 파악·재사용 기회 발굴 | 에러 원인 특정·해결 방향 제시 |
| 출발점 | 설계 질문 | 실패한 실행 결과 |
| 외부 참조 | 없음 | 없음 (외부 API → researcher) |

researcher는 WebSearch/WebFetch 전용. 코드베이스 내부를 보지 않음.
debug-specialist는 내부 코드·로그·git history만 본다는 점에서 codebase-analyst와
같은 축이지만, **진입 조건과 출력 목표가 다름**.

## 역할 정의

| 항목 | 내용 |
|------|------|
| 핵심 역할 | 에러·테스트 실패·예상 외 동작을 체계적으로 조사해 근본 원인과 해결 방향 제시 |
| 행동 원칙 | `no-speculation.md` "첫 행동 3원칙" 전담 실행 |
| 도구 | Read, Glob, Grep, Bash |
| 모델 | sonnet |

## TRIGGER / SKIP

**TRIGGER** (1회 실패 즉시):
- 에러·테스트 실패 원인이 출력만으로 특정 불가할 때
- 수정 후에도 같은 에러가 반복될 때
- 예상 외 동작이 관찰됐을 때 (기대와 다른 출력, 사이드이펙트, 환경 차이)

**SKIP**:
- 원인이 이미 명확한 단순 버그 → 직접 수정
- 에러 원인이 외부 라이브러리 API 변경으로 **확인된** 경우 → researcher
  (단, "의심"만 있는 단계에서는 debug-specialist가 먼저 판단)
- 기존 패턴과의 구조적 충돌이 **확인된** 경우 → codebase-analyst
  (단, 마찬가지로 "의심" 단계에서는 debug-specialist가 먼저)
- 보안·인증 경로 취약점 → threat-analyst + risk-analyst

> **SKIP 판단 원칙**: 막힌 시점에서 원인이 이미 확인된 경우에만 다른 에이전트로.
> "의심"이나 "불명확"이면 debug-specialist가 먼저 진단하고 필요 시 내부에서
> researcher/codebase-analyst 위임을 결정한다.

## 에이전트 본문 구조

에이전트 파일에 내재화할 핵심 흐름:

```
1. 선행 사례 조사 (항상 첫 번째 — no-speculation "선행 사례 확인")
   → doc-finder fast scan: 에러 키워드로 incidents/ 탐색
   → 같은 에러의 과거 해결 사례 있으면 즉시 활용

2. 현재 상태 관찰 (no-speculation "관찰")
   → 에러 메시지·스택 트레이스 원문 Read/Bash로 읽기
   → 재현 가능한 최소 케이스 특정 시도

3. 가설 2개 이하 (no-speculation "추측 차단")
   → 가설당 Grep/Read 1회로 검증
   → 검증 안 된 가설로 수정 시작 금지

4. 결과 보고
   → 원인 특정 성공: 수정 방향 + 영향 파일 명시
   → 원인 특정 실패: 시도 내역 + 다음 탐색 제안
     (외부 API 변경 확인 필요 → researcher 위임 제안)
     (기존 패턴 구조 분석 필요 → codebase-analyst 위임 제안)
```

**`no-speculation.md` 직접 내재화**: 에이전트는 독립 컨텍스트에서 실행되므로
rules/ 참조보다 본문에 원칙을 박는 것이 자기완결성 보장에 유리.

## 작업 목록

### 1. 에이전트 파일 생성
> kind: feature

**사전 준비**:
- 읽을 문서: `.claude/agents/codebase-analyst.md` (구조 참고),
  `.claude/rules/no-speculation.md` (내재화할 원칙)
- 이전 산출물: 없음

**영향 파일**:
- `.claude/agents/debug-specialist.md` (신규)

**Acceptance Criteria**:
- [x] `.claude/agents/debug-specialist.md` 생성됨
- [x] frontmatter: name, description(TRIGGER/SKIP 포함), model=sonnet, tools 포함
- [x] 에이전트 본문: 선행 사례 → 관찰 → 가설 검증 → 보고 4단계 명시
- [x] "의심 단계에서는 debug-specialist가 먼저" 원칙 명시
- [x] doc-finder를 첫 번째 행동으로 내재화

---

### 2. advisor.md specialist 풀 표 갱신
> kind: chore

**사전 준비**:
- 읽을 문서: `.claude/agents/advisor.md` (specialist 풀 표 섹션)
- 이전 산출물: 작업 1 완료 후 진행

**영향 파일**:
- `.claude/agents/advisor.md`

**Acceptance Criteria**:
- [x] specialist 풀 표에 `debug-specialist (sonnet)` 행 추가됨
- [x] 역할·호출 시점 명시됨

---

## 결정 사항

- codebase-analyst와 통합하지 않음. 시점·목적이 다름.
- researcher와도 무관. WebSearch/WebFetch 전용 vs 내부 코드 분석.
- SKIP 판단 원칙: "확인된" 경우에만 다른 에이전트로. "의심" 단계에서는 먼저 진단.
- 트리거 조건: 1회 실패 즉시.
- doc-finder를 첫 번째 행동으로 내재화 (no-speculation 선행 사례 확인 연동).
- no-speculation.md 본문 직접 내재화.

## 메모

- 에이전트 총 수: 8 → 9개
- 작업 순서: 이 WIP 작업 1 완료 → `hn_phase_agent_improvements.md` 작업 5(escalate 흐름)
- task·phase 연계: AC 미달성 → debug-specialist 즉시 호출 → AC 재시도.
  Phase 단위 AC가 있으면 "어느 Phase에서 막혔는가"가 명확해짐.
