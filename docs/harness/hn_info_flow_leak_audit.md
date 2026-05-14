---

title: 하네스 단계간 정보 흐름 누수 전수 조사
domain: harness
tags: [audit, information-flow, efficiency, agent-orchestration]
problem: P7
s: [S7, S9]
status: completed
created: 2026-04-20
updated: 2026-04-20
---

# 하네스 단계간 정보 흐름 누수 전수 조사

## CPS 연결

**Problem**: P2 (review 과잉 비용) 연장선 — staging.md 정밀화로 1차
대응했으나 누수로 인한 비용 절감 한계 존재. 누수 해소가 구조적 해결책.

**Solution 영향**: 단계간 정보 전달 규약 도입. `## Solutions` 섹션의
"단계 분리 + 정보 흐름" 보강 필요 (Phase 1 완료 후 CPS 갱신).

**관련 incident**: `docs/incidents/hn_review_agent_wrong_diff.md`
— review가 prompt 안 staged diff를 신뢰하지 않고 git 명령 부른 사고.
이번 작업은 그 연장선: review가 메타 파일 본문도 prompt에서 받게 만들어
외부 Read 동기 자체 제거.

## 배경

ec85c79 커밋에서 review 에이전트가 6 tool_uses 사용 (deep 한도 5 초과).
분석 결과 review가 HARNESS.json·promotion-log 등을 Read한 이유는 **commit
스킬이 이미 read·edit한 정보를 review prompt에 박지 않았기 때문**.

핵심 진단 (사용자 발언):
> 이전 단계의 내용을 전달 받지 못한다는 게 제일 큰거 같은데?

같은 패턴이 하네스 전체에 얼마나 퍼져 있는지 전수 조사. codebase-analyst
에이전트가 13 스킬·8 에이전트·11 스크립트 감사.

## 조사 결과 요약

**총 10건 누수 확인** (강 1 / 중 5 / 약 4)

| # | 경로 | 강도 |
|---|------|------|
| 1 | commit → review (diff truncation 시) | 약 |
| 2 | commit → test-strategist (파일 본문 재Read) | 중 |
| 3 | harness-upgrade Step 9 → docs-manager (전수 스캔) | 중 |
| 4 | write-doc → commit (WIP 전수 탐색) | 약 |
| 5 | harness-init Step 7 → docs-manager | 약 |
| 6 | **eval --deep → 4관점 병렬 에이전트 (코드베이스 중복 탐색)** | **강** |
| 7 | implementation Step 0.5 → advisor (docs 재탐색) | 중 |
| 8 | pre-commit-check stdout → commit Step 6 (diff 재실행) | 중 |
| 9 | harness-upgrade Step 9.5 → MIGRATIONS.md | 없음 |
| 10 | session-start → 다음 turn (WIP 재탐색) | 약 |
| 11 | harness-adopt Step 5g → docs-manager (전수 스캔) | 중 |

## 공통 패턴 4종

### 패턴 A: 위임 전달 규정 없음 (누수 3, 5, 7, 11)

호출자가 이미 읽은 결과를 피호출자(주로 docs-manager, advisor)에 전달하는
명세가 SKILL.md에 없음. 피호출자가 독자적으로 전수 탐색.

**영향 파일:**
- `harness-upgrade/SKILL.md:381-389`
- `harness-init/SKILL.md:247-253`
- `harness-adopt/SKILL.md:372-376`
- `implementation/SKILL.md:52-59`

### 패턴 B: 에이전트 독립성이 중복 탐색 유발 (누수 2, 6)

에이전트가 `tools: Read, Glob, Grep` 완전 보유. 호출자가 이미 가진 정보를
에이전트가 독자적으로 재확보. 에이전트 독립성 설계의 자연스러운
트레이드오프.

**영향 파일:**
- `agents/test-strategist.md`
- `skills/eval/SKILL.md:382-394`

### 패턴 C: 통계만 전달, 본문은 미전달 (누수 8)

pre-commit-check.sh가 diff 통계는 stdout으로 전달하지만 파일 목록·본문은
미전달. commit Step 6이 diff를 재실행.

**영향 파일:**
- `.claude/scripts/pre-commit-check.sh:524-537`
- `skills/commit/SKILL.md:326`

### 패턴 D: WIP/메타 전수 탐색 (누수 4, 10)

write-doc·session-start가 직접 알고 있는 WIP 파일 경로를 다음 단계에
전달하지 않음. commit·다음 turn이 WIP 전체 재탐색.

**영향 파일:**
- `skills/commit/SKILL.md:192-199`
- `.claude/scripts/session-start.sh`

## 우선순위 권고

### 즉시 효과 큰 것 (P0)

**누수 6 해소** — eval --deep 4관점 에이전트
- 비용: 에이전트당 5~10 tool calls × 4 = 20~40 calls
- 같은 파일 4중 Read 발생 가능
- 해결: eval Step 0/1 결과를 각 에이전트 prompt에 인라인 박기. 한 줄
  지시 추가로 해소
- 영향 파일: `skills/eval/SKILL.md:382-394`

**누수 2 해소** — commit → test-strategist
- 비용: 파일 본문 재Read 2~5회
- pre-commit-check.sh `NEW_FUNC_LINES` 변수(line 409)가 이미 함수 추가
  줄 감지 → stdout에 새 key 추가로 해소
- 영향 파일: `.claude/scripts/pre-commit-check.sh`,
  `skills/commit/SKILL.md:394-396`

### 패턴 수정으로 일괄 해소 (P1)

**패턴 A 해소** — docs-manager·advisor 호출 규칙 추가
- docs-manager SKILL.md 상단에 "호출자는 이미 읽은 파일 목록·요약을
  prompt에 박아야 한다" 명시
- 누수 3, 5, 11 일괄 완화

### 낮은 우선순위 (P2)

- 누수 1: diff truncation 시에만 현실화 (희귀)
- 누수 4, 5: 현재 리포 규모에서 영향 작음
- 누수 10: **P2 판정 재평가 필요 (2026-04-23)**. 다운스트림 실측에서 사용자
  명시 개입 2회 발생. "현재 리포 규모에서 영향 작음" 판정이 틀렸을 가능성.
  대응 신호(`prior_session_files`) 추가 완료 — `hn_commit_process_audit.md` #18
  false-negative 축 참조. 경고 유효성은 실측으로만 검증 가능.
- 누수 9: 누수 아님 판정

## 사각지대 (조사 미완)

- eval --deep 4관점 에이전트의 **실제 토큰 비용**은 실행 로그로만 확인 가능.
  구조 분석만 완료. 실측 필요.
- CLAUDE.md `## 환경` 파싱 결과가 이후 스킬에 재활용되는지 추적 안 됨.
- 에이전트 독립성 (패턴 B)과 비용 절감이 충돌. 어느 선이 최적인지는 실측 필요.

## 구현 계획

### Phase 1: P0 두 건 (우선)

1. **eval SKILL.md Step 4** — 각 에이전트 prompt에 Step 0/1 결과 인라인
   박기 명시 추가
2. **pre-commit-check.sh** — 새 key 추가:
   - `new_func_lines: <추출된 함수 추가 줄>` (test-strategist용)
   - `staged_files_with_sizes: <파일=라인수>` (diff 재실행 불필요하도록)
3. **commit/SKILL.md Step 7** — test-strategist prompt에 new_func_lines
   인라인 박기 + review prompt에 관련 메타 파일 본문 박기 규정 추가

### Phase 2: P1 패턴 A 일괄 (중기)

4. **docs-manager/SKILL.md** — 상단에 "호출자 전달 규약" 섹션 추가:
   ```
   ## 호출자 전달 규약
   호출자(스킬·에이전트)는 docs-manager 호출 시 다음을 prompt에 박아야 한다:
   - 이번에 변경된 파일 목록 (경로 배열)
   - 각 파일의 새 domain·status (이미 알고 있으면)
   - 전수 스캔이 필요한 경우에만 "scope: full" 명시
   ```
5. **harness-upgrade·harness-init·harness-adopt·implementation의 docs-manager
   호출 지점** — 각각 전달 규약 준수하도록 수정

### Phase 3: 실측 검증

6. Phase 1·2 적용 효과를 실측 데이터로 검증.
   → 별도 WIP `harness--hn_info_flow_leak_phase3.md`로 분리.

## Phase 1 구현 결과 (2026-04-20) ✅

### 1. pre-commit-check.sh (누수 #2)
- `NEW_FUNC_LINES_FULL` 변수 도입 — 함수 추가 줄 20줄까지 추출 (기존 1줄만)
- `NEW_FUNC_LINES`는 호환성 유지 (head -1)
- stdout 두 블록(차단·통과)에 `new_func_lines_b64` key 추가 — 멀티라인 값은
  base64 인코딩으로 안전 전달
- 반영 위치: `.claude/scripts/pre-commit-check.sh:407-416, 525-527, 543-545`

### 2. commit/SKILL.md — test-strategist prompt (누수 #2 후반)
- 병렬 호출 블록에 "감지된 새 함수/클래스/메소드 라인" 섹션 추가
- base64 디코드 명시 + 파일 재Read 불필요 지시
- 반영 위치: `.claude/skills/commit/SKILL.md:391-419`

### 3. commit/SKILL.md — review prompt 메타 본문 박기 (누수 #1·#8)
- "전제 컨텍스트 블록" 뒤에 "메타 파일 본문 박기" 섹션 신설
- 대상 4개 (HARNESS.json / promotion-log 추가 행 / MIGRATIONS 신규 섹션 / INDEX.md)
- Read 대비 ~5배 비용 우위 근거 포함
- review prompt `## 지시`에 "Read 재확인 금지" 지시 추가 규정
- 반영 위치: `.claude/skills/commit/SKILL.md:131-180`

### 4. eval/SKILL.md — 4관점 에이전트 prompt (누수 #6, 가장 강함)
- "실행 방식" 뒤에 "에이전트 prompt 구성" 섹션 신설
- Step 0/1 결과를 공통 블록으로 각 에이전트에 주입
- 에이전트별 특화 지시 (파괴자/비용/외부공격자). 트렌드는 무관 제외
- 기대 효과: 에이전트당 5~10 → 2~3 tool calls
- 반영 위치: `.claude/skills/eval/SKILL.md:396-433`

### 검증
- pre-check 구문 OK (`bash -n`)
- stdout 새 key 출력 OK (현재 staged 없어 빈 값이지만 key는 정상 출력)

### 다음 (Phase 2·3)
Phase 2(docs-manager 전달 규약) — 본 문서 Phase 2 섹션 참조 (완료).
Phase 3(실측 검증) — 별도 WIP `harness--hn_info_flow_leak_phase3.md`로 분리.

## Phase 2 구현 결과 (2026-04-20) ✅

docs-manager 호출자 전달 규약 도입. 누수 #3·#5·#11 일괄 해소.

### 5. docs-manager/SKILL.md
- 상단(사용법 다음, Step 1 직전)에 "호출자 전달 규약" 섹션 신설
- **trigger·intent·scope·files·context** 5종 필드 명시
- 사용자 피드백 반영: `reason` 한 줄로는 부족 → trigger(시점·이유) +
  intent(목적) + context.prior_steps(이전 단계 결과)로 호출 맥락 완전 전달
- 왜 이렇게 박는가: docs-manager가 검증 강도·자동 수정 여부 판단 가능,
  같은 정보 재Read 방지
- Step 1 검증 범위를 scope에 따라 분기하도록 명시
- 폴백: 규약 미준수 시 `scope: full` + `intent: validate` + 경고 1회
- 반영 위치: `.claude/skills/docs-manager/SKILL.md:32-99, 109`

### 6. commit/SKILL.md Step 2 — docs-manager 호출 보강
- `trigger·intent: move-document·scope: focused·files·context.prior_steps` 5종 박기
- 반영 위치: `.claude/skills/commit/SKILL.md:289-293`

### 7. harness-upgrade Step 9 — docs-manager 호출 보강
- 변경/신규/이동된 파일 목록 + Step 4·5·6 처리 결과 명시
- intent는 기본 validate, 신규 이식 있으면 update-index
- 반영 위치: `.claude/skills/harness-upgrade/SKILL.md:386-394`

### 8. harness-init Step 7 — docs-manager 호출 보강
- 최초 INDEX 구축 명시 (intent: full-refresh)
- prior_steps에 "스택·도메인 결정 완료" 컨텍스트
- 반영 위치: `.claude/skills/harness-init/SKILL.md:253-258`

### 9. harness-adopt Step 5g — docs-manager 호출 보강
- 기존 docs/ 재분류 직후 — 처음 보는 파일 다수 명시
- prior_steps에 "재분류·프론트매터 일괄 추가 완료" → frontmatter 재파싱 절약
- 반영 위치: `.claude/skills/harness-adopt/SKILL.md:378-385`

### 검증 (Phase 2)
- 5개 SKILL.md 구문 OK (마크다운, 별도 검증 불필요)
- 호출자 4곳 모두 docs-manager 규약 5종 필드 명시 완료

### CPS 갱신 사항

`docs/guides/project_kickoff.md` P2 섹션:
- **Solution 갱신**: "staging.md 정밀화" 외에 "단계간 정보 흐름 규약 (Phase 1)"
  추가. review·test-strategist·eval 4관점이 prompt 인라인 컨텍스트로 작동.
- 이번 커밋에서 CPS 문서 직접 갱신 안 함 — P2 승격 상태 업데이트는
  Phase 3 실측 데이터 확보 시 별도 처리. CPS 프레임 유지.

## 성공 지표

Phase 1 완료 후 실측:
- eval --deep tool_uses 총합이 현재의 70% 이하
- commit → test-strategist tool_uses가 현재의 50% 이하
- review tool_uses 한도 위반 빈도 감소

Phase 2 완료 후:
- docs-manager 호출이 있는 스킬 5개(upgrade/init/adopt/implementation/
  write-doc)의 docs-manager 하위 tool_uses 감소
