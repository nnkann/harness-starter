---

title: implementation 스킬 재정의 — 라우터·추적자로 역할 좁히기
domain: harness
tags: [implementation, skill, routing, orchestration]
problem: P7
s: [S7, S9]
status: completed
created: 2026-04-20
updated: 2026-04-20
---

# implementation 스킬 재정의

## 배경

정보 흐름 누수 해소 작업(Phase 1·2) 중 implementation 스킬이 자동 발화
안 한 문제가 드러남. 사용자 지적:

> "이 실행 스킬이 너무 비대해지는 걸 원하지 않아. 역할 분담이 잘
> 되어야지. 이렇게 되면 혼자 다 하는게 되는건데?"

implementation에 분석·검증·판단을 박으면 기존 specialist(advisor, doc-finder,
codebase-analyst, researcher, risk-analyst, review, eval, check-existing)
시스템이 무용지물이 됨.

## 재정의된 책임 (implementation만 하는 것)

implementation = **오케스트레이터(라우터)**. 음악 지휘자처럼 직접 연주 안 하고
누구를 언제 부를지 결정.

| 고유 책임 | 설명 |
|-----------|------|
| 1. 트리거 시점 판단 | "지금이 작업 시작 시점이다" 인식 |
| 2. 라우팅 | "이 작업에 어떤 specialist가 필요한가" 결정 |
| 3. WIP 문서 관리 | 작업 추적 단위 생성·진척 기록 |
| 4. CPS 매핑 | 작업 ↔ Problem 연결 (CPS 갱신은 docs-manager/write-doc) |
| 5. 실행 흐름 조율 | Step 진행, escalate 판단, 완료 신호 |

## implementation이 하지 않는 것 (위임 대상)

| 하지 말 것 | 위임 대상 |
|------------|---------|
| 문서 탐색 | doc-finder |
| 내부 코드 분석 | codebase-analyst |
| 외부 자료 조사 | researcher |
| 접근법 비교·권고 종합 | advisor |
| 위험·반대 논거 | risk-analyst |
| 성능 분석 | performance-analyst |
| 테스트 전략 | test-strategist |
| 중복 함수 확인 | check-existing 스킬 |
| 커밋 전 검증 | review (커밋 시점) |
| 주기적 건강 검진 | eval |
| 문서 정합성 | docs-manager |

## 현재 implementation의 실제 결함

사용자 지적 종합:

### A. 트리거 불완전
- description TRIGGER 키워드에 "진행해줘", "이대로", "OK", "ㅇㅇ", "시작해",
  "해보자" 등 승인 표현 없음
- SKIP의 "설정 변경"이 너무 광범위 (SKILL.md 수정도 포함되어 오분류)
- 연속 작업 시 자동 재발화 가이드 없음

### B. 라우팅 결정 가이드 없음
- "어떤 신호면 advisor 호출 / doc-finder만으로 충분" 같은 분기표 없음
- 작업 규모·위험도에 따른 흐름 분기 없음 (micro vs large 동일 흐름)
- specialist 결과를 어떻게 종합할지 명시 없음

### C. 실행 단계 자체가 공백
- Step 0(CPS 읽기) → Step 1(문서 생성) → Step 2(상태 변경) → Step 3(기록)
- Step 2.5(실제 구현)가 **없음**. LLM이 "이제 뭘 하지?" 시점에 흐름 종료
- Step 3은 "작업 중 기록만" — 실제 코드 수정은 어디서 하는지 명시 없음

**결정 (2026-04-20)**: implementation이 **코드까지 직접 처리**.

검토했던 대안:
- 옵션 B: 별도 `coder` 에이전트(sonnet) 신설 — 단계 추가로 정보 흐름 누수 재발 위험
- 옵션 C: 하이브리드 (작업 규모별 분기) — 라운드트립 견고성 판단할 실측 데이터 부족

채택 사유: 단계 분리 효과를 추측으로 판단하지 마라. 컨텍스트 손실이
sonnet 비용 절감을 초과할 수 있음. Phase 1·2 적용 후 실측 데이터 누적
→ 재평가 (Phase 3 영역).

### D. 관점·중점 가이드 부재
- 문서에서 무엇을 발췌해 어디에 쓸지 명시 없음
- LLM이 "다 읽었습니다"로 끝나거나 의미 없는 요약만 남김

### E. 실패·escalate 흐름 없음
- commit: pre-check 실패 시 차단·재시도 명시
- review: 한도·차단 사유 명시
- implementation: 막히면? 3원칙은 알지만 그 다음은?

## 수정 방향 (라우팅 중심)

### 1. TRIGGER/SKIP 보강

TRIGGER 추가:
- 승인 표현: "진행해줘", "이대로", "OK", "ㅇㅇ", "시작해", "해보자", "고"
- 명시적 사용자 승인 + 직전 턴에 구체 계획 제시됐으면 연속 발화

SKIP 정밀화:
- "단순 설정 변경" → "단일 settings.json 키-값 토글, 스킬/스크립트 로직
  수정 아님"
- 직전 작업이 implementation 영역이었어도 **연속 작업 트리거는 재발화** 명시

### 2. 규모·위험도 분기 (라우팅 표)

```
작업 규모 판정 (사용자 발화 + 예상 변경 범위):

micro (단일 파일, <20줄, 리스크 낮음)
  → 바로 구현, WIP 생략. commit 스킬이 검증.

small (단일 파일, 20~100줄 또는 다중 파일이지만 <3개)
  → WIP 생성. doc-finder 1회 (관련 문서). advisor 생략.

medium (3~10 파일, 또는 1 파일이지만 <300줄 구조 변경)
  → WIP + doc-finder + codebase-analyst (기존 패턴 영향)
  → 위험도 hit 시 risk-analyst 추가

large (10+ 파일 또는 핵심 구조 변경)
  → WIP + advisor 필수 (specialist pool 오케스트레이션)
  → advisor 응답을 WIP ## 메모에 종합
```

### 3. 실행 단계 신설 (Step 2.5) — 단, 위임만 조정

```
### Step 2.5. 실행 흐름

**내가 실행하지 않는다.** 다음을 수행:

1. 작업 단위 분해 (TodoWrite 활용)
2. 단위별 specialist 필요 판단:
   - 새 함수·모듈 직전: check-existing 스킬
   - 외부 라이브러리 도입 직전: researcher
   - 기존 패턴 영향 의심: codebase-analyst
   - 위험 결정 직전: risk-analyst
3. 실제 Read/Edit/Write는 메인 Claude가 수행 (implementation이 트리거만)
4. 단위마다 self-verify (린터/구문/테스트 — pre-commit-check.sh 활용 가능)
5. 막히면 3회 시도 후 사용자 보고 (no-speculation.md 준수)
6. 단위 완료 시 WIP ## 결정 사항 / ## 메모 갱신
```

### 4. 종합 가이드

Step 4 완료 처리 시:
- specialist 호출 결과를 WIP에 모두 보존 (기록 누락 방지)
- CPS 영향 판정 + docs-manager 호출 (전달 규약 따라)
- commit 스킬로 넘김 (완료 이동·커밋은 commit 담당)

## 우선순위

**중간** (P1 수준). 매 세션마다 작업 시작 품질에 영향. 하지만 구조적
변경이라 실측 후 조정 필요.

## 구현 계획

1. description TRIGGER/SKIP 재작성 (위 섹션 1)
2. "규모·위험도 분기" 표 Step 0 또는 Step 1 직전에 삽입
3. Step 2.5 (실행 흐름) 신설 — 위임 중심
4. Step 0의 "무엇을 위해 / 어떤 관점으로 / 무엇을 결정"을 한 단락으로 명시
   (길게 박지 말 것. specialist가 하는 일을 다시 박지 말 것)
5. 실패/escalate 흐름 명시 (사용자 보고 기준)

## 제약

- **스킬 비대화 금지.** 각 Step에 "무엇을 하라"만 쓰고 "어떻게 하라"는
  specialist에게 위임. SKIL.md 전체 길이가 현재 대비 1.5배 넘어가면 과잉.
- **기존 specialist 역할 중복 금지.** 표 `implementation이 하지 않는 것`의
  항목을 박지 말 것.
- **판단·분석·검증 로직 박지 말 것.** implementation은 라우터이지
  실행자·분석가가 아님.

## 성공 지표

개선 후 실측:
- implementation 자동 발화율 증가 (사용자가 "진행해줘", "OK" 같은 발화로
  자동 트리거되는 비율)
- SKILL.md 전체 길이 현재(155줄) 대비 +50% 이내 유지
- 작업 완료 후 WIP에 specialist 호출 기록이 남는 비율 (지금은 거의 0)

## 결정 사항 (2026-04-20)

- **1. TRIGGER/SKIP 재작성 완료** — description을 오케스트레이터 역할 중심으로 재정의.
  승인 표현 6종 + 연속 작업 재발화 명시. SKIP의 "설정 변경" → "단일 settings.json
  키-값 토글" 정밀화.
  → 반영: `.claude/skills/implementation/SKILL.md` 프론트매터 L3-10
- **2. "고유 책임" / "위임 대상" 표 신설** — 흐름 앞에 역할 경계를 명문화해
  판단·분석 로직이 스킬 본문으로 스며드는 것을 차단.
  → 반영: L18-41
- **3. Step 0.7 (규모·위험도 분기 표) 삽입** — micro/small/medium/large 4단계로
  WIP 생성·specialist 호출 강도 차등. 위험도 hit 신호 6종 명시.
  → 반영: L87-101
- **4. Step 2.5 (실행 흐름) 신설** — 라우팅만 수행. 코드 수정은 메인 Claude
  Read/Edit/Write 위임. specialist 트리거 6종 매핑. self-verify와 WIP 갱신
  책임 명시.
  → 반영: L153-169
- **5. Step 0에 "관점" 한 단락 추가** — CPS Problem 연결·Solution 충돌·과거
  결정 재사용 3축. doc-finder는 결과만 소비.
  → 반영: L64-70
- **6. 실패·escalate 흐름 신설** — 관찰/재현/선행사례 → 3회 규칙 →
  사용자 보고 → abandoned 전환. no-speculation.md와 연결.
  → 반영: L204-214

## 메모

- SKILL.md 최종 240줄 (기존 159줄 대비 +51%). 1.5배(238줄) 상한을 2줄 초과.
  원칙 5(핸드오프 계약) 추가로 +11줄 — 역할 분리만으로 생기는 정보 흐름
  누수를 차단하기 위한 필수 블록. Phase 1·2에서 실측된 누수 위험 대비
  허용 가능한 초과로 판단.
- CPS 갱신: 없음. 본 변경은 P1(LLM 추측 수정)·P5(컨텍스트 팽창) Solution의
  실행 경로를 개선하지만 Problem/Solution 문구 자체는 변화 없음.
- Phase 3 실측 대상: description 재작성 후 자동 발화율, specialist 호출
  기록 WIP 기록률, 단계 분리(옵션 B/C) 재평가 근거 수집.
- 파생 WIP `harness--hn_info_flow_leak_phase3.md`가 실측
  담당.
