---
title: eval 4관점 advisor 이관 + specialist 품질 보강 (threat-analyst 신설·산출물 점수·업계 탑 인물)
domain: harness
tags: [eval, advisor, specialist, threat-analyst, quality, scoring]
relates-to:
  - path: decisions/skill_agent_role_audit_260420.md
    rel: implements
  - path: harness/implementation_router_redesign_260420.md
    rel: extends
  - path: harness/commit_review_handoff_refactor_260420.md
    rel: references
status: completed
created: 2026-04-20
updated: 2026-04-20
---

# eval 4관점 advisor 이관 + specialist 품질 보강

## 목표

감사 문서 P0-2(eval/SKILL.md 508줄 4관점 내재화)를 **옵션 B(advisor 대체)** +
품질 보강으로 해결.

- CPS 연결: P2(review/검증 과잉 비용) + P5(컨텍스트 팽창)

## 결정 사항

### D1. 옵션 B 채택 — 4관점을 specialist에 1:1 매핑

| eval 4관점 | 매핑 specialist | 신규? |
|-----------|----------------|-------|
| 비용/과잉 | codebase-analyst | 기존 |
| 트렌드 | researcher | 기존 |
| 파괴자 | risk-analyst | 기존 |
| 외부공격자 | **threat-analyst** | 신규 |

**이전 advisor 권고(옵션 C 현행 유지)를 뒤집는 근거:**
- 사용자 제안으로 **품질 보강** 축 추가 (점수 평가 + 업계 탑 인물 반영)
  → 단순 다이어트가 아니라 specialist 시스템 자체의 품질 향상
- codebase-analyst만 있고 threat-analyst가 없던 **대칭 불균형**을 이번에 해소
- 4관점 → 4 specialist 1:1 매핑이 되므로 누수·중복 없음

### D2. 신규 에이전트: threat-analyst

**네이밍**: `threat-analyst` (기존 `-analyst` 형식 준수). 외부위협(threat)
분석가. 보안 업계 용어(threat modeling)와 일치.

**역할**: 외부 공격자 관점. GitHub public·전직자 클론·클라이언트 번들 공개
가정하에 6개 시나리오 점검:
1. git history 시크릿
2. 공개 README/docs의 prod URL·어드민 이메일·테스트 계정
3. 클라이언트 번들 서버 전용 env inline
4. CORS/CSP/security headers 누락
5. service_role 키 브라우저 경로 노출
6. admin/debug 엔드포인트 production 가드 부재

### D3. researcher 보강 — 업계 탑 인물 반영

**의도**: 외부 조사 시 "공식 문서 + 업계 합의"만으로 끝내지 말고 해당
분야 레퍼런스 인물의 최근 의견을 논거 강화용으로 추가.

**구조**: 사용자 우려("매번 탐색 비용")를 반영한 **하이브리드 + 저비용**:
- `.claude/rules/external-experts.md` 캐시 (빈 상태로 시작, 점진 축적)
- 조회 순서: 캐시 먼저 → 없으면 1회 메타 검색으로 1~2명 식별 → 자료 수집
  (**최대 2개 소스**) → 캐시 자동 추가
- 신뢰 마킹: "최초 식별 (미검증)" / "다회 사용됨 (신뢰)" / "사용자 확정"
- 분야 없으면 스킵 — 일반 researcher 흐름 폴백
- 인물 의견은 **2~3문장 요약 + 링크**. 사용예 가져오기 의무 없음 (논거
  강화용이지 대체 자료 아님)

### D4. 산출물 자가 평가 — 5 specialist 공통

모든 specialist 응답 끝에 자가 평가 블록:

```
### 산출물 자가 평가
- 근거 강도 (1~5): 인용한 출처·파일·라인의 신뢰성
- 커버리지 (1~5): 요청받은 범위를 얼마나 포괄했는가
- 실행 가능성 (1~5): 호출자가 바로 행동 가능한 구체성
- 사각지대 명시 (필수): 이번 답변이 놓친 영역
- 종합 (1~5): 평균 + 주관 가중
```

**점수 기준 (모호성 차단):**
- 5: 공식 문서·파일 라인·최근 업계 권위 인물 1차 자료
- 4: 공식 문서 또는 파일 라인만
- 3: 간접 근거 (커뮤니티 논의·업계 합의)
- 2: 일반론·관례 기반
- 1: 추측

**적용 대상 5 agent**: codebase-analyst, researcher, risk-analyst,
performance-analyst, test-strategist. 신규 threat-analyst도 포함.

**호출자 활용**: 점수 낮은 영역(근거 강도 ≤2·커버리지 ≤2)은 재호출
또는 보완 specialist 호출 판단 근거.

### D5. eval/SKILL.md — 4관점 인라인 제거

L317-432(4관점 섹션 + Step 0/1 주입 블록)를 **advisor 호출 1개**로 대체:

```
eval --deep → advisor 호출 (병렬 4 specialist: codebase-analyst,
researcher, risk-analyst, threat-analyst)
  → 각 specialist는 Step 0/1 결과 + eval 맥락(--deep 모드·--harness 분기
    여부)을 prompt로 받음
  → advisor가 4개 결과를 점수 포함해 종합 → eval이 사용자에게 보고
```

eval/SKILL.md 예상 줄수: 508 → ~420줄 (~85줄 절감). 감사 목표 ~400줄에
근접.

### D6. advisor 확장 — eval 4-specialist 패턴 지원

advisor 기존 rule("2~3개 기본")에 예외 명시: eval `--deep` 호출 시 **4개
필수 병렬** (4관점 완전 매핑 필요). 다른 호출자는 기존 rule.

advisor가 4개 결과 종합 시 산출물 점수도 함께 집계해 "신뢰도 낮은 영역"
을 사용자에게 표시.

## 메모

### advisor 응답 원문 (2026-04-20, Preserve 축 준수)

> **권고: C (현행 인라인 유지)** — 4관점은 eval 전용 체크리스트이지
> 재사용 가능한 역할이 아니다. 분리 시 self-containment 원칙 재위반 +
> 파일 4개 증가 비용이 절감(~100줄) 대비 크다.

advisor 권고를 뒤집은 이유: 사용자 추가 요구사항(품질 보강 — 점수 평가·
업계 탑 인물)이 단순 다이어트 차원을 넘어섬. 품질 보강을 기존 인라인
구조에 박으면 eval/SKILL.md가 오히려 비대해짐. specialist에 분산해야
재사용 가능.

**사용자 지적 결정적 포인트**: "codebase-analyst는 있으니까, 외부공격자만
추가하면 된다" — 4개 신설 대비 1개 신설로 75% 절감. advisor의 "파일 4개
증가 비용" 근거가 이 설계에서는 적용 안 됨.

### 실행 순서

1. threat-analyst.md 신설 (기존 6시나리오 그대로 이식 + 산출물 자가 평가 포함)
2. external-experts.md 빈 템플릿 신설
3. researcher.md 보강 (캐시 로직 + 업계 탑 인물 섹션 + 산출물 자가 평가)
4. codebase-analyst·risk-analyst·performance-analyst·test-strategist 산출물
   자가 평가 블록 추가
5. advisor 에이전트/스킬: eval 4-specialist 패턴 명시 + 점수 종합
6. eval/SKILL.md L317-432 삭제 → advisor 호출 단일 섹션으로 대체
7. self-verify + commit

### 핸드오프 계약 (상속)

implementation SKILL.md SSOT 상속. 본 작업에서 각 신규/보강 에이전트가
자기 계약 표를 보유하게 하고, eval → advisor → 4 specialist 체인의
Pass 축 명시.

### 우려

- **researcher 캐시 초기값 무**: 처음 몇 호출은 "최초 식별 (미검증)"만
  쌓임. 정상. 사용자가 확인 후 "사용자 확정"으로 격상.
- **점수 자가 평가 객관성**: LLM이 자기 응답에 점수 매김 → 과대 평가
  우려. 완화책: 점수 기준 명시 (근거 종류별 5/4/3/2/1 1대1 대응).
  그래도 절대 지표가 아닌 **상대 비교·재호출 판단**용으로 쓸 것.
- **threat-analyst 탐색 범위**: eval 스코프(전체 코드베이스)라 tool calls
  많을 수 있음. Step 0/1 결과 인라인 전달로 재스캔 방지 (누수 #6 해소
  패턴 그대로).

## 실측 결과 (2026-04-20 완료)

| 항목 | 변경 |
|------|------|
| 신규 `agents/threat-analyst.md` | 189줄 (6시나리오 + 입력 계약 + 자가평가) |
| 신규 `.claude/rules/external-experts.md` | 32줄 (빈 템플릿) |
| `agents/researcher.md` | +34줄 (업계 탑 인물 섹션 + 자가평가) |
| `agents/codebase-analyst.md` | +13줄 (자가평가) |
| `agents/risk-analyst.md` | +13줄 (자가평가) |
| `agents/performance-analyst.md` | +13줄 (자가평가) |
| `agents/test-strategist.md` | +13줄 (자가평가) |
| `agents/advisor.md` | +15줄 (threat-analyst 추가, 대칭 관계, 점수 집계, eval 예외) |
| `skills/advisor/SKILL.md` | description + eval --deep 행 갱신, 중복 "언제" 섹션 제거 |
| `skills/eval/SKILL.md` | 508 → 458줄 (-50줄). 4관점 인라인 115줄 → advisor 호출 70줄 |

**핵심 달성:**
- eval 4관점 → 4 specialist 1:1 매핑 (B 옵션)
- threat-analyst 신설로 외부공격자 대응 specialist pool에 확보 (codebase-analyst와 대칭)
- 7개 specialist 공통 산출물 자가평가 블록 (1~5점 + 사각지대 필수)
- researcher 업계 탑 인물 반영 + `external-experts.md` 캐시 (저비용 하이브리드)
- advisor가 점수 집계·신뢰도 경고 지원
- self-containment 원칙 유지 (commit→review와 동일 패턴)

## 실패·escalate

- threat-analyst 신설이 기존 external-attacker 인라인 블록과 의미 충돌
  → 인라인 블록 제거 + threat-analyst로 일원화 (혼재 금지)
- researcher 캐시 로직이 기존 Step 2(공식 문서 조사)와 충돌 → 캐시는
  **인물 조회용**만, 공식 문서·코드 예제는 기존 흐름 유지
- 산출물 점수가 과잉 보고로 이어지면 → 기본 출력에서 생략, 호출자
  요청 시에만 포함하는 옵션 고려 (실측 후 조정)
