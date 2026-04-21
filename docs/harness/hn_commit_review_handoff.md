---
title: commit + review 핸드오프 계약 이식 + 중복 제거
domain: harness
tags: [skill, agent, commit, review, handoff, refactor]
relates-to:
  - path: decisions/hn_skill_agent_role_audit.md
    rel: implements
  - path: harness/hn_implementation_router.md
    rel: extends
status: completed
created: 2026-04-20
updated: 2026-04-20
---

# commit + review 핸드오프 계약 이식 + 중복 제거

## 목표

감사 문서(`decisions--hn_skill_agent_role_audit.md`) 실행 순서 1단계
**P0-1 commit + P1-2 review 쌍**을 실행.

- CPS 연결: P1(추측 수정)·P2(review 과잉 비용)·P5(컨텍스트 팽창) 모두에
  간접 기여. commit·review는 매 커밋마다 도는 핫 패스 → 비대화·중복은
  누적 비용.

## 범위

| 대상 | 현재 | 목표 | 변경 유형 |
|------|------|------|-----------|
| `.claude/skills/commit/SKILL.md` | 566줄 | ~400줄 | review/test-strategist 호출 규약 중복 제거 + 핸드오프 계약 이식 |
| `.claude/agents/review.md` | 432줄 | ~400줄 | "eval로 위임" 6회 반복 통합 + 핸드오프 계약 이식 |

합계 998줄 → ~800줄 (20% 감축 목표).

## 원칙 (감사 문서 SSOT 상속)

implementation/SKILL.md "## 핸드오프 계약 (SSOT)"의 축·기호·엄수 규칙을
그대로 상속. commit/review는 자기 축 값만 구체화.

## 결정 사항

### D0. 계획 수정 (2026-04-20, advisor 실측 반영)

**advisor 호출 결과 감사 문서의 D3 권고가 안티패턴으로 판명.** 계획 전면
재조정.

교정된 방향:
- **L56-162 포인터화 취소** — staged diff 캡처·HARNESS.json 파싱·메타 파일
  본문 박기는 호출자(commit) 전용 실행 로직. review.md는 "계약"만 보유
  하므로 commit이 포인터로 내용을 받아올 수 없음. 포인터화 시 정보 손실.
- **L419-476 부분 포인터화만 유지** — test-strategist.md L44-49와 실제
  겹치는 ~15줄 prompt 본문만 이관. 병렬 강제·base64·분담 로직은 commit
  유지.
- **commit 줄수 다이어트는 별도 WIP로 분리** — 감축 대상이 "호출 규약"이
  아니라 "S-신호 중복 설명·Step 산문"이라 별도 감사·실행 필요.
- **핸드오프 계약 이식 + review "eval 위임" 통합은 계획대로 실행.**

Anthropic Agent Skills 공식 지침 해석:
- SKILL.md는 self-contained. 스킬 내부 bundled reference로 progressive
  disclosure는 OK, 다른 에이전트 파일로 점프는 비권장.
- agent description이 입력 SSOT. 호출자가 agent 파일을 Read해야 prompt를
  조립할 수 있다면 설계 오류.

### D1 (유효). commit 핸드오프 계약

### D1-legacy (초안 원문 보존)

감사 문서 L77-87 권고 기반 초안:

| 축 | 내용 |
|----|------|
| Pass (implementation→commit) | WIP 파일 경로 · status · CPS 갱신 여부 |
| Pass (pre-check→commit) | `s1_level` · `signals` · `stage` · `domains` · `needs_test_strategist` |
| Pass (commit→review) | diff (base64) · HARNESS.json · pre-check signals · stage · CPS 참조 |
| Pass (commit→test-strategist) | 새 함수 line 블록(`new_func_lines_b64`) · 영향 파일 |
| Preserve | S1·S2·S9 위험 신호 원본 · 도메인 등급 · 연속 수정 이력(S10) |
| Signal risk | ⛔ pre-check 3회 연속 차단·시크릿 감지 · ⚠️ stage 격상 사유 · 🔍 검증 흔적 |
| Record | commit log `🔍 review: <stage> \| signals \| domains` 한 줄 (Stage 0 포함) |

### D2. review 핸드오프 계약 (실행 시 확정)

감사 문서 L204-211 권고 기반 초안:

| 축 | 내용 |
|----|------|
| Pass (commit→review) | D1 commit→review 블록 수용 (파생 가공 금지) |
| Pass (review→commit) | 발견 항목 + 3기호 + 카테고리 + 인용 (diff line·파일명) |
| Preserve | 스코프 경계(이번 diff만) — 경계 외는 "eval 권고" 꼬리표 |
| Signal risk | ⛔ 차단 사유 · ⚠️ 권고 · 🔍 관찰 기록 (commit이 그대로 사용자에게 표시) |
| Record | review 자체는 문서 생성 안 함. commit이 log로 영속화 |

### D3 (수정). commit 중복 제거 대상

- ~~L56-162 review 호출 규약 포인터화~~ — **취소**, self-containment 원칙
  위반. L56-162는 commit 고유 실행 로직이므로 유지.
- **L419-476 중 ~15줄만 포인터화** — test-strategist.md와 실제 겹치는
  prompt 본문. 병렬 강제·base64 로직은 commit 유지.
- **"고유 책임 / 위임 대상 표" 서두 삽입** — 유효.
- **호출 규약 SSOT는 계약 레벨(무엇을)에 한정**, 실행 레벨(어떻게 추출·
  포맷)은 commit에 내재화. review.md·test-strategist.md는 "이 입력을
  받는다"만 명시하면 commit이 상호 링크 보유.

### D4. review 중복 제거 대상 (L13-17, L268-270, L311, L364-366, L374-375, L382-384, L391-392)

- "이 경계 외는 모두 eval로 위임"을 맨 위 "## 작동 모델" 아래 **한 줄**로
  통합
- 본문 각 섹션의 반복 경계 선언 제거

## 메모

### advisor 응답 원문 (2026-04-20, 핸드오프 계약 Preserve 축 준수)

> 실제 파일을 모두 확인했다. 종합한다.
>
> **권고**: 계획 부분 승인. commit L56-162는 포인터화 안 됨 — 내재화 유지.
> L419-476은 부분 포인터화 가능.
>
> **질문 1 결론 (코드 분석)**: L56-162는 중복이 아니다. 포인터화 시 정보
> 손실.
> - L56-91: staged diff를 prompt에 박는 메커니즘(DIFF 캡처·2000라인 가드·
>   6블록 구조) — review.md L166-198은 "박혀 있다고 가정"만 명시. 호출자
>   측 실행 로직은 commit에만 있다.
> - L93-113: 전제 컨텍스트 블록 작성 규약(is_starter bash 추출, HARNESS.json
>   파싱) — review.md L170-180은 "신뢰하라"만 있고 무엇을·어떻게 박는지는
>   commit에만.
> - L115-162: 메타 파일 본문 박기(HARNESS.json/promotion-log/MIGRATIONS/
>   INDEX.md 규칙, 500토큰 vs 3회 Read 트레이드오프) — review.md 어디에도
>   없음.
>
> L419-476은 부분 중복. test-strategist.md L44-49 "호출 전제" 세 줄과
> commit L443-457 prompt 본문이 겹침. 다만 L429-432 병렬 강제·L460-467
> base64 디코드 로직은 commit 고유(pre-check stdout 의존).
>
> **수정안**: L419-476 중 prompt 본문 템플릿(~15줄)만 test-strategist.md로
> 이관하고 commit은 "test-strategist.md 입력 스키마 따름 + pre-check 필드
> 매핑"으로 포인터. 병렬 강제·base64·분담 로직은 commit에 유지.
>
> **질문 2 결론 (리서치)**: "핫 패스에서 호출 규약 포인터 이동"은 명시적
> 안티패턴은 아니나, Anthropic 공식 가이드는 self-containment를 권장.
> - Anthropic Agent Skills 문서: SKILL.md는 self-contained하되 상세는
>   bundled reference 파일로 progressive disclosure 권장.
> - Claude Code subagent 가이드: agent frontmatter의 description이 입력
>   스키마 SSOT. 호출자가 agent 파일을 Read해야 prompt를 조립할 수 있다면
>   설계 오류.
> - 프롬프트 DRY 실패 사례 일반: 공유 프롬프트 조각이 호출 컨텍스트를
>   흡수하지 못해 맥락 손실 → 환각/오판 빈번.
>
> **권고**: commit은 호출자로서 스스로 조립 가능해야 한다. review.md·
> test-strategist.md는 "이 입력을 받는다"(계약)만 명시, commit은 그 계약을
> 내재화된 템플릿으로 충족.
>
> **사각지대**: researcher 미호출 — Context7/웹 실시간 확인 없이 기억 기반
> 답변. CVE·최신 Anthropic 블로그 변동은 미반영.

### 교차 검증 결과

- `new_func_lines_b64`·`needs_test_strategist` 둘 다 [pre-commit-check.sh:522-546](.claude/scripts/pre-commit-check.sh#L522-L546)
  에 실재 확인. D1 Pass 축 유효.

### 실측 결과 (2026-04-20 완료)

| 파일 | 원본 | 최종 | 차이 | 핸드오프 계약 | 비고 |
|------|------|------|------|---------------|------|
| implementation/SKILL.md | 159 | 245 | +86 | ✅ SSOT | 이전 세션에서 완료 |
| commit/SKILL.md | 566 | 598 | +32 | ✅ 상속 | 고유 책임 표·핸드오프 계약 추가, L419-476 부분 압축 |
| review.md | 432 | 445 | +13 | ✅ 상속 | 경계 표·핸드오프 계약 추가, `→ /eval` 위임 화살표 8개 제거 |
| test-strategist.md | 112 | 121 | +9 | ✅ 입력 계약 | "호출 전제" → "입력 계약"으로 승격, 축 표 삽입 |

**감사 목표 vs 실측:**
- commit `~400줄 목표`: **미달** (598줄). advisor 판정으로 호출 규약 포인터
  화 취소 → self-containment 유지. 줄수 감축은 별도 WIP(S-신호 중복·Step
  산문 공략)에서 진행.
- review `~400줄 목표`: **미달** (445줄). 반복 위임 선언은 제거했으나 경계
  표·핸드오프 계약 추가분이 더 큼. 정보 밀도는 개선됨.

**달성한 핵심:**
- 호출 규약 2파일 중복 존재: 0건 (감사 목표)
- 핸드오프 계약 SSOT 상속: 3파일 모두 완료
- review 반복 위임 화살표: 10건 → 0건 (경계 표가 SSOT)
- self-containment 원칙 보존 (Anthropic Agent Skills 공식 지침 준수)

### 분리 진행 대상 (별도 경로)

- commit 줄수 감축 (S-신호 중복 설명·Step 산문 압축)
- P0-2 eval (`--deep` 4관점 named agent 분리)
- P0-3 harness-adopt (핸드오프 계약 이식 우선)
- P1-1 advisor (SKILL.md 슬림화)

### 실행 흐름 (D0 수정 반영)

1. ✅ advisor 호출 완료 — 계획 수정됨
2. ✅ pre-check stdout 스키마 교차 검증 완료
3. **test-strategist.md 먼저 수정** — commit L443-457 prompt 본문을 흡수할
   "## 입력" 섹션 신설 (or 기존 섹션 확장)
4. **review.md 수정** — ① "eval 위임" 6회 반복을 맨 위 한 줄로 통합
   ② 핸드오프 계약 표 이식 (SSOT 상속 명시)
5. **commit/SKILL.md 수정** — ① "고유 책임 / 위임 대상 표" 서두 삽입
   ② 핸드오프 계약 표 이식 ③ L419-476 중 ~15줄만 test-strategist.md 포인터로
   대체 ④ L56-162는 건드리지 않음
6. self-verify: 핸드오프 계약 표 3개 파일 모두 삽입 확인 + review.md "eval
   위임" 중복 문장 수 측정 (목표: 1건)
7. Step 4 완료 처리 + 별도 WIP 기록 ("commit 줄수 다이어트는 S-신호·Step
   산문 공략으로 후행")

### 허용 범위

- 줄수 목표(~400/~400)는 가이드일 뿐, **SSOT·중복 제거·핸드오프 계약 이식**
  3개 조건을 만족하면 줄수 초과 허용 (implementation 선례: 240/238)

### 상속 관계 명시

- commit/review 서두에 "핸드오프 계약은 implementation/SKILL.md SSOT 상속"
  한 줄 명시. 축·기호 변경 금지 규칙 확인.

## 실패·escalate

- `new_func_lines_b64` 키가 pre-check에 없으면 D1 재설계 → advisor 재호출
- review.md 포인터 대상 섹션("## 입력")이 review.md에 없으면 먼저 해당
  섹션 신설 후 commit 포인터화
- 3회 시도 실패 시 본 WIP abandoned + 감사 문서에 실측 결과 반영
