---
title: review 에이전트 verdict 헤더 형식 준수율 — 100% 누락 패턴
domain: harness
problem: P2
solution-ref:
  - S2 — "review tool call 평균 ≤4회 (부분)"
tags: [review, verdict, format, compliance]
relates-to:
  - path: harness/hn_harness_efficiency_overhaul.md
    rel: caused-by
status: completed
created: 2026-05-02
updated: 2026-05-02
---

# review verdict 형식 100% 누락

## 사전 준비
- 읽을 문서: `.claude/agents/review.md` (line 10~15 헤더 + line 201~ "출력 형식" SSOT), `.claude/skills/commit/SKILL.md` (review 호출 prompt 조립부)
- 이전 산출물: 본 세션 v0.29.2·v0.30.0·v0.30.1 commit 3건 — 모두 verdict 누락 → 1차 재호출로 회복

## 목표
review 에이전트 응답 첫 2줄 `## 리뷰 결과\nverdict: X` 형식 1패스 준수율
0% → 90% 이상. 매번 1차 재호출 비용 누적 + 차단 위험.

## 현재 상황 분석 (본 세션 실측)

review.md에 강제는 충분:
- frontmatter 직후 line 10~15: 인용 박스로 "응답 첫 2줄 무조건"
- line 158~160: maxTurns·verdict 필수
- line 201~: "## 출력 형식 (SSOT)" 전체 템플릿

commit/SKILL.md prompt 끝에도 명시. 그럼에도 100% 누락.

원인 가설:
1. review가 **분석 자유 서술 본문을 먼저 출력**하는 경향 (chain-of-thought
   leak) — 첫 토큰부터 헤더가 나오게 강제 안 됨
2. 강제 메시지가 review.md 두 군데 분산 (line 10·201) — 일관성 떨어짐
3. commit prompt의 "지시" 블록이 다른 지시(파일 Read·git diff)와 섞여
   verdict 형식 우선순위가 묻힘

## 작업 목록

### 1. 원인 진단

**Acceptance Criteria**:
- [x] Goal: 본 세션 4 누락 케이스 패턴 특정 (분석 서술 → 결론 verdict 순? 또는 verdict 누락 후 본문만?)
  검증:
    review: skip
    tests: 없음
    실측: 본 세션 transcript에서 4/4 모두 "분석 본문 먼저 출력 → 1차 재호출에 verdict 헤더 부착" 패턴 일관 관찰
- [x] 패턴 결론: review 에이전트가 reasoning과 출력을 분리 안 함 — 분석 사고를 본문에 leak. verdict는 결론부 후반에 출현

### 2. prompt 재설계 (prefill 패턴)

**Acceptance Criteria**:
- [x] Goal: commit/SKILL.md prompt 마지막 줄을 `## 리뷰 결과 / verdict: `로 끝내 prefill 효과. 모델이 다음 토큰부터 verdict 값 강제 출력
  검증:
    review: review
    tests: 없음 (운용 검증)
    실측: 본 wave 이후 5 commit 연속 1패스 성공 추적 — 자동 검증 불가, 운용에서 확인
- [x] commit/SKILL.md "지시" 블록 끝에 "출력 형식 — 절대 규칙" 섹션 추가. prompt 자체가 `verdict: `로 끝나도록 재배치

### 3. review.md 구조 정리

**Acceptance Criteria**:
- [x] Goal: 상단 헤더 박스를 더 강하게 — 자주 나오는 실수 명시 + "분석은 reasoning에서, 출력은 결론부터" 행동 가이드
  검증:
    review: review
    tests: 없음
    실측: review.md line 10~ 강화 확인
- [x] 두 군데 분산 메시지 정리 — 상단 헤더는 행동 가이드, line 201 SSOT는 형식 정의 (역할 분리)

## 결정 사항

- **prefill 패턴 채택**: commit/SKILL.md prompt 마지막 줄을 `## 리뷰 결과 / verdict: `로
  끝내 모델 다음 토큰을 verdict 값으로 강제. Anthropic prefill 권장 패턴 활용.
  → 반영: commit/SKILL.md "## 출력 형식 — 절대 규칙" 섹션 + prompt 끝 `verdict: ` prefill
- **review.md 헤더 강화**: 자주 나오는 실수 명시(분석 머릿말·"AC 항목 검증한다") +
  "분석은 reasoning에서, 출력은 결론부터" 행동 가이드. 두 군데 분산 메시지의
  역할 분리 — 상단(line 10~)은 행동 가이드, line 201은 형식 SSOT.
  → 반영: review.md 상단 인용 박스 확장
- **자동 검증 불가 영역 정직 고지**: prefill 효과는 운용에서 5 commit 1패스
  성공률로 측정. 본 wave에서 자동 검증 불가 — 다음 commit부터 추적
- CPS 갱신: 없음 (S2 메커니즘 강화 — 충족 기준 변경 X, prompt 패턴 개선)

### Phase 4 결정 (2026-05-02, prefill 1차 시험 후) — JSON 규격화

**prefill 1차 시험 결과 (v0.30.4 commit)**:
- 1차 응답 "지시 1~3 확인 완료. 이제 archive 자동화 확인" 한 줄로 끊김
- prefill로 응답 시작 형식은 영향이 약함 — 응답 절단·길이 폭주 별 패턴
- 본 세션 5/5 markdown 강제 실패 누적 → markdown으론 안 통한다는 강한 신호

**JSON 규격화 채택 (v0.30.5)**:
- review.md 출력 형식 SSOT 변경 — markdown 템플릿 → raw JSON 1개 객체
- 스키마 v2 (사용자 지적 반영 — AC 매핑 명확화):
  ```
  {verdict, ac_check[{goal, result, evidence}], blockers[{ac_index}],
   warnings, axis_check, solution_regression, early_stop, conclusion}
  ```
- `ac_check`가 **AC 항목별 객체 배열** — 인덱스 의존 폐기, 텍스트 매칭으로 자동
- `blockers[].ac_index`로 어느 AC와 연결되는지 명시 (사용자 즉시 확인 가능)
- duplicate key 감지 (`object_pairs_hook`) — `{"verdict":"pass","verdict":"block"}` 같은 모델 실수 reject
- prompt prefill `{"verdict":"`로 변경 (markdown 헤더 → JSON 시작 토큰)
- commit/SKILL.md 종료 코드별 재호출 메시지 분기:
  - exit 1: JSON 파싱 실패
  - exit 2: verdict 필드 누락·enum 위반
  - exit 3: ac_check 정합성 위반 (필드 누락·배열 아님·항목 goal/result 누락)
- 5+5 케이스 dry test 통과 (raw·코드 블록·서론·dup key·ac_check 정합성)

**중첩 호출 영향 확인 (사용자 질문 1)**:
- review의 `tools: Read, Glob, Grep, Bash` — Agent tool 없음. sub-agent의 sub-agent 없음
- verdict 흐름 단방향 1-hop: review → commit. 다른 sub-agent로 전달 안 됨
- 변경 영향 범위 review.md + commit/SKILL.md 둘만

**중복 verdict 시나리오 (사용자 질문 2)**:
- 본문에 verdict 단어 산재: 영향 없음 (regex `\{...\}` 매칭으로 JSON 객체만 추출)
- JSON 객체 2개 출현: 첫 매칭만 사용 (`re.search` 단방향)
- duplicate key: `object_pairs_hook`으로 reject → 재호출 트리거
- nested JSON: 본 스키마 1단계까지만 — 안전. 미래 깊어지면 강건 파서 필요

**AC 매핑 의무 (사용자 질문 3)**:
- 이전 스키마 약점: `ac_check.items: ["pass", "fail"]` 인덱스 의존
- v2: `ac_check: [{goal, result, evidence}]` AC 항목별 객체
- AC 추가/삭제 시 인덱스 어긋남 차단 — `goal` 텍스트로 매핑
- `evidence` 필드로 검증 근거 명시 (자가 보고 신뢰도 추적 가능)
- review가 AC 하나씩 채우는 구조화된 사고 — verdict 결정 전 모든 AC 처리 강제

## 메모

- 본 세션 4 commit (v0.29.2·v0.30.0·v0.30.1·v0.30.2) 모두 verdict 누락 → 1차 재호출 통과 패턴 100% 일관
- 영향: 매번 review 재호출 1회 비용 (tool call 1~2 + 시간 5~10초 + prompt 토큰)
- 차단으로 이어진 적 없음 — 1차 재호출이 작동. 단 비용 누적 부담
- prefill 패턴 근거: Anthropic API에서 assistant 메시지 prefill로 응답 시작
  토큰 강제하는 표준 기법. sub-agent prompt에서도 마지막 줄이 다음 응답
  시작점에 영향 — 실측 필요하나 강한 prior
- 작은 변경 — review.md 인용 박스 1개·commit/SKILL.md "지시" 블록 1개 수정
  (15~20줄). 작업 규모 small

## 변경 이력

### v0.30.6 (2026-05-02) — Stage 0 skip 우회 결함 수정

본 문서가 v0.30.5 commit에서 AC 모두 [x]였음에도 자동 이동되지 않은 사고
발견. 원인:

- commit/SKILL.md Step 7.5 "Stage 0 skip도 스킵" 명시
- v0.30.5는 review 영역 자체 변경이라 `recommended_stage: skip`
- skip이 wip-sync 흐름을 가로채 본 문서 자동 이동 누락 → 수동 `docs_ops.py move` 필요

**원인 분석**:
- wip-sync는 staged 확정 상태 기반 — review 호출 여부와 독립
- Stage 0 skip은 "review LLM 호출 안 함"이지 "진척도 갱신 안 함"이 아님
- 둘이 conflate된 설계 결함

**수정 (v0.30.6)**:
- Step 7.5를 verdict 기반 분기로 재정의
  - `block`만 차단 (커밋 자체 불가)
  - `pass`·`warn`·skip(verdict 미설정) 모두 wip-sync 실행
- 본 문서 자체가 자기증명 사례 — v0.30.5 후속 v0.30.6에서 수동 이동 + 결함 수정 함께 처리


### v0.30.7 (2026-05-02) — JSON 스키마 폐기, verdict 단어 추출 단순화

본 세션 v0.30.5~v0.30.6 운용 결과: JSON 스키마·AC 매핑 의무·duplicate
key 강제에도 **5/5 markdown 머릿말 leak 지속**. fallback regex가 첫
`{...}` 블록을 추출해 실용 통과 중이었으나 SSOT "첫 토큰 `{`" 박제
유지가 부담.

debug-specialist 진단 (2026-05-02):
- **H1 확정**: Anthropic Agent tool sub-agent 호출에서 assistant prefill
  미작동. prompt 끝 `{"verdict":"`은 user message 텍스트 일부일 뿐
- **보조 H3 확정**: commit/SKILL.md prefill 위치가 prompt 본문 중간
  (line 166, line 168~ 평문 계속)으로 prompt 끝조차 아님
- 형식 강제 메커니즘 자체가 무력 → 강제 박제 폐기

**v0.30.7 단순화**:
- review.md 출력 형식 SSOT: "raw JSON 1개 객체" 강제 → "verdict:
  pass|warn|block 한 단어 포함" (형식 자유)
- AC 매핑 의무·duplicate key 검증·ac_check 정합성·early_stop 등 스키마
  필드 다 폐기 (호출자 commit이 파싱 안 함)
- 신규 스크립트 `.claude/scripts/extract_review_verdict.py` (10줄):
  정규식 `\b(pass|warn|block)\b` 첫 매칭 추출
- commit/SKILL.md Step 7 inline python heredoc (~80줄) → 1줄 호출
- 테스트 `test_extract_review_verdict.py` (`pytest -m review`) — markdown
  leak 5종 + verdict 미존재 케이스 6/6 통과

**부가 정보 처리**:
- blockers·warnings 같은 부가 정보는 review가 응답 본문에 자유 형식 서술
- commit이 파싱하지 않고 그대로 사용자에게 노출 (block 차단 사유·warn
  경고 사유로 git log 본문 인용)

**원칙**: 형식 강제 ≪ 의미 추출. sub-agent 호출에서 형식 강제는 메커니즘
자체가 약함 — 추출 가능한 시그널 1개에 집중하고 형식 자유.
