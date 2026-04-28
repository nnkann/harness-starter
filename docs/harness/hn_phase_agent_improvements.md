---
title: Phase 구조 보강 — WIP AC 섹션 + Phase 6원칙 + escalate 에이전트 트리거 + WIP 실행 순서
domain: harness
tags: [implementation, phase, escalation, wip-template]
status: completed
created: 2026-04-25
updated: 2026-04-25
---

# Phase 구조 보강 — WIP AC 섹션 + Phase 6원칙 + escalate 에이전트 트리거 + WIP 실행 순서

## 배경

다른 하네스 구조(스킬 발화 → 에이전트 컨트롤 + `run-phases.py` 자동 실행)와
비교 분석에서 도출한 개선 항목.

**발행 주체**: implementation 스킬. 사용자 작업 요청 → implementation이 WIP
문서 생성 → WIP 문서가 Phase 구조를 따름. WIP 문서 자체가 Phase 파일 역할.

확인된 간극:

1. **WIP 문서에 AC가 없다** — 완료 기준이 없어 검증 실패 시점 불명확.
   에스컬레이션 트리거가 생기지 않음. AC를 "누가 언제 어떻게 실행하는가"도
   없음.
2. **Phase 분리·순서 기준이 추상적이다** — 실제 판단에 적용하기 어려운
   표 형태. "하나의 Phase = 하나의 레이어/모듈" 같은 단순 규칙이 없음.
3. **여러 WIP 존재 시 실행 순서를 정하는 주체가 없다** — WIP를 여러 개로
   분리한 뒤 어떤 순서로 진행할지 implementation 스킬에 기준이 없음.
   사용자가 매번 물어봐야 하는 상황.
4. **막힐 때 에이전트 활용 경로가 약하다** — "3회 시도 후 specialist 재호출"
   이지만 어떤 에이전트를 쓸지 불명확. "사용자 보고"가 실제 기본 경로.

연관 작업 (별도 WIP):
- `debug-specialist` 에이전트 신설 → `harness--hn_debug_specialist.md`
- HARNESS.json `skills` 목록 정리 → `harness--hn_harness_json_cleanup.md`

## 목표

1. WIP 문서 템플릿에 `## 사전 준비`·`## Acceptance Criteria` 추가 + AC 실행 주체 명시
2. `implementation/SKILL.md` Step 0에 `doc-finder` 의무 호출 강제 (기획 시 자산 확인)
3. `implementation/SKILL.md`에 Phase 6대 원칙 추가 (분리·순서 기준)
4. `implementation/SKILL.md`에 여러 WIP 간 실행 순서 결정 단계 추가
5. `implementation/SKILL.md` escalate 흐름에 에이전트 트리거 매핑 추가

## 작업 목록

### 1. WIP 문서 템플릿 보강 + AC 실행 주체 명시
> kind: feature

**현 상태**: Step 1 문서 구조에 `## 목표` / `## 결정 사항` / `## 메모` 3개 섹션만.
AC 없음. 누가 언제 검증하는지 없음.

**변경 내용 — 템플릿**:

```markdown
## 사전 준비
- 읽을 문서: (경로 목록 또는 "없음")
- 이전 산출물: (이전 Phase 결과물 또는 "없음")

## 목표
- 이 작업에서 결정하거나 만들 것
- CPS 연결: Problem #{번호} (있으면)

## 작업 목록
### 1. {Phase 제목}
> kind: feature|bug|refactor|docs|chore

**사전 준비**: ...
**영향 파일**: ...
**Acceptance Criteria**:
- [ ] {실행 가능한 커맨드 또는 직접 확인 가능한 조건}

## 결정 사항
## 메모
```

**AC 실행 주체 명시 (self-verify.md 연동)**:

```
AC 실행 규칙:
- Claude가 각 Phase 완료 직후 AC 항목을 직접 실행해서 확인한다.
  (명령어면 Bash 실행, 사람 확인 조건이면 사용자에게 결과 제시)
- AC 미통과 → 즉시 debug-specialist 호출. "완료" 선언 금지.
- 전체 AC ✅ → commit 스킬 호출. docs_ops.py wip-sync가 자동 이동.
```

**`사전 준비` 원칙**:
- 에이전트가 이전 대화 없이 자기완결적으로 실행할 컨텍스트.
- 비어도 되지만 "없음"으로 명시 (묵시적 생략 금지).

**`Acceptance Criteria` 원칙**:
- 추상 서술 금지. `python3 -m pytest tests/`, "린터 에러 0" 같은 실행·확인 가능 형태.
- PR 연동: 이번 스코프 밖. 커밋 메시지 AC 달성 기록 방식은 별도 WIP로 분리.

**영향 파일**:
- `.claude/skills/implementation/SKILL.md` (Step 1 문서 구조 + Step 2.5 self-verify 연동)

**Acceptance Criteria**:
- [ ] Step 1 문서 구조 코드블록에 `## 사전 준비` / `## Acceptance Criteria` 추가됨
- [ ] "AC 실행 규칙" (Claude가 직접 실행, 미통과 시 debug-specialist) 명시됨
- [ ] self-verify.md 연동 언급 포함됨

---

### 2. Step 0 — doc-finder 의무 호출 강제 (fast scan)
> kind: feature

**현 상태**: Step 0에서 doc-finder 호출이 "필요하면" 조건부. 선택적.

**변경 내용**: Step 0 CPS 대조 직후 Step 0.3 신설. fast scan 의무.

```
Step 0.3 — 기존 자산 확인 (doc-finder fast scan, skip 금지)

doc-finder에 작업 키워드를 넘기고 fast scan 요청:
  → 파일명·태그 Grep만 (본문 Read 없음, tool calls 3회 이내)
  → 반환: hit 파일 경로 목록 또는 "없음"

hit 있으면 → deep scan으로 전환 (기존 doc-finder 탐색 절차)
hit 없으면 → "없음" 기록 후 즉시 종료

결과를 WIP ## 사전 준비에 기록. 탐색 사실 자체가 기록 대상.
```

**영향 파일**:
- `.claude/skills/implementation/SKILL.md` (Step 0 섹션)
- `.claude/agents/doc-finder.md` (fast scan 모드 — 이미 반영 완료)

**Acceptance Criteria**:
- [ ] Step 0.3 섹션 추가됨
- [ ] fast scan이 "tool calls 3회 이내"로 명시됨
- [ ] hit/no-hit 분기 명시됨

---

### 3. Phase 6대 원칙 추가
> kind: feature

**현 상태**: Phase 분리 기준이 추상적인 표 형태. 적용 어려움.

**변경 내용**: implementation/SKILL.md Step 2.5 앞에 Phase 설계 6대 원칙 추가.
참고 하네스의 6대 원칙을 우리 구조에 맞게 재해석.

```
Phase 6대 원칙:

1. 자기완결성 — 각 Phase는 이전 대화 참조 없이 실행 가능해야 한다.
   ## 사전 준비에 필요한 모든 맥락을 기록.

2. 사전 준비 명시 — 읽어야 할 문서 경로 + 이전 Phase 산출물을 반드시 기록.
   "없음"도 명시 (묵시적 생략 금지).

3. 하나의 Phase = 하나의 레이어/모듈 — 한 Phase에서 여러 레이어(UI + API + DB)를
   동시에 건드리지 않는다. 영향 파일이 서로 다른 도메인이면 분리.

4. 실행 가능한 AC — 추상 서술 금지. Claude가 직접 실행하거나 사람이 화면으로
   확인할 수 있는 조건만. AC 없는 Phase는 완료 선언 불가.

5. Scope 최소화 — 단일 파일 5줄 이하 변경은 같은 도메인 Phase에 묶음.
   Phase가 길어지면 분리 신호.

6. 구체적 주의사항 — "조심해라" 금지. "X를 하지 마라. 이유는 Y다" 형식.
   Phase 본문에 직접 박는다.
```

**실행 순서 원칙** (Phase 간 우선순위):

1. **의존성 우선** — 다른 Phase가 전제로 쓰는 것을 먼저.
2. **위험도 높은 것 먼저** — 되돌리기 어려운 변경(설정·공개 API)을 앞에.
   실패 시 뒤 작업이 아직 시작 전이므로 피해 최소화.
3. **검증 빠른 것 먼저** — AC 실행이 빠른 Phase를 앞에. 막힘 조기 감지.

**영향 파일**:
- `.claude/skills/implementation/SKILL.md` (Step 2.5 앞 신규 섹션)

**Acceptance Criteria**:
- [ ] Phase 6대 원칙 섹션 추가됨
- [ ] 실행 순서 3원칙 추가됨
- [ ] 기존 추상적 분리 기준 표 제거됨

---

### 4. 여러 WIP 간 실행 순서 결정 단계 추가
> kind: feature

**현 상태**: implementation 스킬이 여러 WIP를 생성한 뒤 어떤 순서로 진행할지
기준이 없음. 사용자가 매번 물어보는 상황.

**문제 시나리오**: 현재 이 작업 자체가 WIP 3개(`phase_improvements`,
`debug_specialist`, `harness_json_cleanup`)로 분리됐지만, 어떤 순서로 실행할지
WIP 문서 안에 명시된 곳이 없음. 사용자가 직접 물어봐야 알 수 있음.

**변경 내용**: Step 0.8(SSOT·분리 판단) 직후 Step 0.9 신설.

```
Step 0.9 — 여러 WIP 실행 순서 결정 (WIP 2개 이상일 때만)

분리 판단 후 WIP가 2개 이상이면:
1. 의존성 맵 작성 — 어떤 WIP가 다른 WIP의 결과물을 전제로 쓰는가
2. 순서 결정 (Phase 실행 순서 원칙 적용)
3. 각 WIP의 ## 메모에 "실행 순서: N번째, 선행 조건: <WIP명>" 기록
4. 사용자에게 순서 제시 + 확인 (되돌리기 어려운 변경 포함 시)

단일 WIP이면 이 단계 skip.
```

**영향 파일**:
- `.claude/skills/implementation/SKILL.md` (Step 0.8 직후 Step 0.9 추가)

**Acceptance Criteria**:
- [ ] Step 0.9 섹션 추가됨
- [ ] "WIP ## 메모에 실행 순서 기록" 명시됨
- [ ] 단일 WIP skip 조건 명시됨

---

### 5. escalate 흐름 보강
> kind: feature

**선행 조건**: `hn_debug_specialist.md` 작업 1 완료 후 진행.

**현 상태**:
```
1. 관찰·재현·선행 사례 확인
2. 3회 시도 규칙 → specialist 재호출 또는 advisor 전환
3. 사용자 보고
4. 중단
```

**변경 내용**: AC 미달성 → 유형 분류 → 에이전트 즉시 위임.

```
AC 미달성 시 escalate 흐름:

막힘 유형                        → 에이전트          조건
에러·테스트 실패 (원인 불명)     → debug-specialist   1회 실패 즉시
접근법 자체가 막막할 때          → advisor            방향이 보이지 않을 때
에이전트 위임 후에도 미해결      → 사용자 보고

"3회 규칙" 재정의:
  기존: "같은 접근법 3회 실패 → specialist 호출"
  변경: "에이전트 위임 사이클(위임→시도→실패) 3회 → 사용자 보고"
```

**영향 파일**:
- `.claude/skills/implementation/SKILL.md` (실패·escalate 흐름 섹션)

**Acceptance Criteria**:
- [ ] 에이전트 트리거 표 추가됨 (debug-specialist 1회 즉시 명시)
- [ ] "3회 규칙" 재정의 반영됨
- [ ] AC와 escalate 흐름이 연결됨 ("AC 미달성 → 유형 분류 → 위임")

---

## 결정 사항

- [완료] 작업 1: WIP 템플릿 보강 + AC 실행 규칙 → `implementation/SKILL.md` 반영.
  테스트 51/51 통과.
- [완료] 작업 2: Step 0.3 신설 — doc-finder 의무 fast scan (tool calls 3회 이내,
  hit/no-hit 분기 명시). `implementation/SKILL.md` L94 반영. 테스트 51/51 통과.
- [완료] 작업 3: Phase 6대 원칙 + 실행 순서 3원칙 → Step 2.5 앞에 삽입.
  `implementation/SKILL.md` L255 반영. 테스트 51/51 통과.
- [완료] 작업 4: Step 0.9 신설 — 여러 WIP 간 실행 순서 결정 (Step 0.8 직후).
  `implementation/SKILL.md` L165 반영. 테스트 51/51 통과.
- [완료] 작업 5: escalate 흐름 보강 — debug-specialist 1회 즉시 트리거, advisor 전환,
  "3회 규칙" → 에이전트 위임 사이클 3회로 재정의. `implementation/SKILL.md`
  `## 실패·escalate 흐름` 섹션 교체. 테스트 51/51 통과.
- AC 실행 주체: Claude가 각 Phase 완료 직후 직접 실행. 미통과 시 완료 선언 금지.
- doc-finder fast scan: tool calls 3회 이내 강제. 파일명·태그 Grep만.
  `doc-finder.md` 이미 반영 완료.
- Phase 6대 원칙: 참고 하네스 6대 원칙을 우리 구조에 맞게 재해석.
- WIP 간 순서: Step 0.9로 명시화. 각 WIP ## 메모에 순서 기록.
- "3회 규칙": 삭제 아님. "에이전트 위임 사이클 3회"로 의미 재정의.
- PR 체크리스트: 이번 스코프 밖.

## 메모

- 작업 순서 (이 WIP 내부):
  1→2→3→4 독립 실행 가능.
  5(escalate)는 `hn_debug_specialist.md` 작업 1 완료 후.
- 전체 WIP 간 순서:
  `hn_debug_specialist` → 본 WIP 작업 5
  `hn_harness_json_cleanup` → 독립 (언제든 가능)
- Phase 6대 원칙은 참고 하네스의 원칙을 직수입한 것이 아니라,
  우리 하네스의 WIP 문서 구조에 맞게 재해석한 것.
