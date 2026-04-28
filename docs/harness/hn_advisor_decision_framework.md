---
title: advisor 전면 재설계 — 의사결정 프레임 라이브러리 + 판단 경로 명시
domain: harness
tags: [advisor, decision-framework, orchestration, judgment]
status: completed
created: 2026-04-20
updated: 2026-04-20
---

# advisor 전면 재설계 — 판단 엔진으로 승격

## 배경

사용자 지적(2026-04-20):

> advisor 내용이 정말 부실하다. 이걸로 무슨 판단을 할 수 있을까? 4개에서
> 오는 결과를 분석하려면 어떤 내용이 들어올 건지 예측해야 하고, 각 에이
> 전트도 어떤 내용으로 보낸다는 내용이 있어야 하고, 판단성 기준·주제별
> 유연성이 필요하다. 점수를 그냥 조합만 하는 꼴이잖아.

현재 advisor.md의 구조적 결함:
1. **판단 프레임워크 부재** — "종합하라"만 있고 "어떤 프레임으로 판단할지" 없음
2. **specialist 응답 구조 사전 인지 없음** — 즉흥적 종합
3. **점수 남용** — 자가평가 점수를 나열만 하고 가중치·충돌 판단에 활용 X
4. **충돌 해소 규칙 없음** — "충돌 명시" 지시만 있고 해소 기준 공백
5. **판단 경로 기록 없음** — 결론만 나오고 왜 그 결론인지 추적 불가
6. **뒤집힐 조건 명시 없음** — 낙관 편향 방지 장치 부재

## 목표

advisor를 "단순 종합 기계"에서 **"판단 엔진"**으로 승격.

- CPS 연결: P1(LLM 추측 수정)·P2(review 과잉 비용) 양쪽 간접 기여. advisor
  품질이 낮으면 호출자가 다시 추측으로 폴백 (P1 재발)

## 선택지 / 결정

### A + B 병행 (결정)

- **A. advisor 전면 재작성** — 의사결정 프레임 6~7개 내장, 유형별 매핑,
  판단 경로 명시, 충돌 해소 규칙, 뒤집힐 조건 필수
- **B. researcher로 업계 표준 조사 병행** — 의사결정 프레임 외부 자료·탑
  인물 의견 수집 → A 세부 채움. researcher 보강한 업계 탑 인물 기능
  첫 실전 활용.

둘 다 필요. B 결과가 오기 전 A의 **뼈대**만 준비, 결과 오면 세부 완성.

## 결정 사항 (설계 원칙)

### D1. 구조 — 6단계 흐름

1. 질문 수신 + 의사결정 유형 분류
2. 유형별 판단 프레임 선택
3. 예상 specialist 응답 구조 사전 인지
4. specialist 병렬 호출
5. 판단 행렬 조립 + 충돌 해소
6. 판단 경로 + 결론 + 대안 + 뒤집힐 조건 명시

### D2. 의사결정 프레임 라이브러리 (7개 안)

업계 표준 7개. researcher 결과로 정제 예정:

| 프레임 | 언제 | 출력 형태 |
|--------|------|-----------|
| Weighted Decision Matrix | 다차원 옵션 비교 (스택 선택) | 기준·가중치·점수 행렬 |
| Pre-mortem | 되돌리기 어려운 결정 (DB 마이그·공개 API) | 실패 시나리오 + 방어 |
| Trade-off triangle | 3축 상충 (속도·비용·품질) | 어느 축 양보할지 |
| Pros/Cons + 가중치 | 단순 찬반 + 중요도 | 가중 합산 |
| Expected Value | 확률 × 영향 (위험 우선순위) | 기대값 랭킹 |
| ADR (Architecture Decision Record) | 아키텍처 결정 | Context·Decision·Consequences |
| Bayesian update | 새 정보로 이전 결론 수정 | prior → posterior |

### D3. 주제별 프레임 매핑

| 의사결정 유형 | 기본 프레임 | 필수 specialist |
|--------------|-----------|----------------|
| 기술 스택·라이브러리 선택 | Weighted Decision Matrix | researcher + codebase + risk |
| 되돌리기 어려운 변경 | Pre-mortem + Trade-off | risk + threat + codebase |
| 리팩토링 방향 | Pros/Cons + 가중치 | codebase + risk + performance |
| 보안 구조 변경 | Pre-mortem + Attack tree | threat + risk + researcher |
| 성능 최적화 | Expected Value | performance + codebase |
| 아키텍처 결정 | Trade-off triangle + ADR | researcher + codebase + risk |

주제가 모호하면 사용자에게 프레임 제안 ("이 결정은 Pre-mortem이 적절해
보입니다. 계속할까요?").

### D4. specialist 응답 구조 사전 인지표

advisor가 각 specialist에게 **기대하는 출력 필드**를 미리 안다 — 종합이
즉흥 아니라 **구조화된 입력 처리**가 됨:

| specialist | advisor가 기대하는 핵심 필드 |
|-----------|--------------------------|
| researcher | 외부 근거·deprecated 여부·업계 탑 인물 의견·점수 |
| codebase-analyst | 재사용 기회·기존 패턴·충돌 위치·점수 |
| risk-analyst | 핵심 위험·완화 방안·incident 매칭·점수 |
| threat-analyst | 6 시나리오별 발견·조치 우선순위·점수 |
| performance-analyst | 핵심 위험·예상 영향·측정 권장·점수 |
| test-strategist | 핵심 누락·권장 테스트·회귀 방지·점수 |

advisor가 specialist 호출 시 "이 필드로 답해줘" 명시 가능. 실제 응답이
스키마와 다르면 [주의]로 보고.

### D5. 점수의 올바른 사용

- 점수는 **결론 아님**. 판단 입력 변수.
- **근거 강도**는 가중치. 근거 5점 specialist 의견이 3점보다 무거움.
- **점수 충돌 시 규칙**: 차이 2점 이상이면 낮은 쪽의 "사각지대" 섹션을
  advisor가 명시적으로 재검토. 필요 시 재호출·보완 specialist 권고.
- **평균 ≤ 2**: 사용자에게 "이 판단 신뢰도 낮음" 경고 + 추가 조사 권고.

### D6. 충돌 해소 규칙 (판단 기준)

specialist 간 의견이 상충할 때:

1. **근거 강도 비교** (1차) — 높은 점수 쪽 우선. 차이 2점 이상이면 명확.
2. **사각지대 확인** (2차) — 근거 동급이면 사각지대 작은 쪽 우선.
3. **과거 incidents/ 매칭** (3차) — 과거 실패 패턴과 일치하는 경고 우선.
4. **되돌림 가능성** (4차) — 되돌리기 어려운 결정이면 보수적 쪽(위험
   경고) 우선.
5. **사용자 명시 우선순위** — 호출 시 사용자가 "보안 > 성능" 같이 지시
   했으면 그 축 우선.
6. **여전히 tie면** — 사용자에게 선택 요청. advisor가 임의 결정 금지.

### D7. 판단 경로 기록 (필수)

결론만 내지 말고 **판단 경로**를 남긴다:

- 어떤 프레임을 왜 골랐는가
- 어떤 가중치를 왜 부여했는가 (주관이면 "주관" 명시)
- 충돌을 어떤 기준으로 해소했는가
- 이 판단이 뒤집힐 조건은 무엇인가 (**낙관 편향 방지**)

→ 사용자가 "이 판단 믿을만해?" 검증 가능 + 판단이 뒤집혔을 때 왜 뒤집
혔는지 추적 가능.

### D8. 뒤집힐 조건 (Anti-optimism)

모든 판단에 필수:
- "만약 X가 사실이면 이 판단이 뒤집힌다" 1개 이상
- "새 증거 유형 Y가 나오면 재평가" 명시
- "현재 가정 Z가 무효화되면" 명시

낙관 편향 방지·향후 재평가 트리거 제공.

### D9. 출력 형식 (예시)

```
## /advisor 결과

### 의사결정 유형
<유형명> → 프레임: <선택한 프레임>

### 호출한 Specialist
- <목록 + 점수>

### 판단 행렬 (Weighted Decision Matrix 예시)
| 기준 | 가중치 | 옵션 A | 옵션 B | 근거 specialist |
|------|--------|--------|--------|----------------|
| ... | ... | ... | ... | ... |

가중 합: A=X.X / B=Y.Y

### 충돌 해소
- <specialist X는 A 권고, specialist Y는 B 권고> — <규칙 적용 결과>

### 사각지대
- <검증 못 한 영역. specialist 사각지대 합산>

### 권고
<결론 1~3줄>

### 뒤집힐 조건
1. 만약 <X가 사실이면> 이 판단 뒤집힘
2. 새 <Y 증거> 나오면 재평가
3. <Z 가정 무효화 시> 재평가

### 신뢰도 경고 (점수 ≤ 2 관점만)
- <specialist>: <사각지대 요약> — 재호출 또는 보완 specialist 필요
```

## 메모

- **researcher 백그라운드 조사 실행 중** (agent id 내부 관리).
  결과 수신 후 D2·D3 프레임 목록 정제 + D3 매핑 검증 + 인물 의견 반영.
- 이번 advisor 재설계는 eval P0-2 직후의 **연쇄 개선**. eval이 advisor를
  핫 패스로 쓰기 시작했으므로 품질 부실이 곧바로 드러남.
- 본 WIP는 advisor 재작성까지 실행. researcher 결과 수신 → D2 정제 →
  advisor.md 재작성 → self-verify → commit.

### 실행 순서

1. ✅ 설계 원칙 D1~D9 확정 (본 문서)
2. ⏳ researcher 외부 조사 결과 수신
3. D2 프레임 목록 확정 + 각 프레임의 트리거·입력·출력 세부
4. D3 매핑 검증 (주제별로 맞는지)
5. advisor.md 재작성 (뼈대 → 세부)
6. advisor/SKILL.md 간단 업데이트 (description·연동 표)
7. self-verify + commit

## 실측 결과 (2026-04-20 완료)

### 변경된 파일

| 파일 | 변경 |
|------|------|
| `agents/advisor.md` | 171 → 334줄. 판단 엔진으로 전면 재작성 |
| `skills/advisor/SKILL.md` | description + 본문 서두 갱신 (판단 엔진 명시) |
| `.claude/rules/external-experts.md` | 빈 템플릿 → 5명 인물 캐시 등록 (엔지니어링 의사결정 3명·아키텍처 결정 기록 2명) |

### researcher 결과로 정제한 프레임 (10개 → 6개)

**유지**:
- F1 Weighted Decision Matrix (airfocus·Decision Lab)
- F2 Pre-mortem (Kahneman·Klein)
- F3 Trade-off Triangle
- F4 Expected Value
- F5 ADR (Nygard·Fowler 공식 인정)
- F6 Reversibility (Bezos two-way door)

**제외**:
- Pros/Cons + 가중치 → F1에 흡수 (중복)
- Bayesian Update → LLM이 수치 prior·posterior 적용 현실성 낮음
- Disagreement Resolution → 프레임이 아니라 프로세스. 충돌 해소 6단계로 내재화
- RFC/Design Doc → 하네스 docs/decisions/ 흐름과 중복

### 업계 권위자 원칙 반영

- **Nygard**: "결정 맥락이 빠르게 소실" → Step 5 판단 경로 필수 기록
- **Fowler**: "superseded는 새 ADR로 연결" → 뒤집힐 조건 명시 (Step 5)
- **Larson**: "확신보다 투명성" → 낙관 편향 방지·가중치 출처 명시
- **Majors**: "추측이 아니라 운영 데이터" → 사각지대·근거 강도 투명화
- **Fournier**: "프로세스는 지루해야" → 6단계 일관 흐름

### Anthropic 공식 패턴 반영

- **Lead-Subagent** (Opus+Sonnet 90.2%) — 서두 명시
- **LLM-as-Judge 평가 5축**(사실·인용·완결·소스·도구) → specialist 자가평가와 매핑
- **암묵적 수렴(Implicit Consensus)** — 여러 specialist 독립 발견 시 "검증된 사실" 처리 (투표 불필요)

### 핵심 달성

- 단순 "종합 기계" → "판단 엔진" 승격
- 의사결정 프레임 6개 라이브러리 + 주제별 매핑표
- Specialist 응답 구조 사전 인지표 (즉흥 종합 금지)
- 점수 = 가중치 (2점 차 규칙·평균 ≤2 경고)
- 충돌 해소 6단계 tie-breaker
- 판단 경로 + 뒤집힐 조건 필수 (Nygard·Fowler 원칙)
- advisor 자체 산출물 자가 평가

## 실패·escalate

- researcher 결과에서 프레임 6개 중 1~2개가 "실무에선 안 쓰임"으로 판명
  → 제거 or 대체. advisor는 실용성 우선
- 프레임 너무 많아져 advisor.md 비대화 → 핵심 4~5개로 압축
- 주제별 매핑이 실측과 다르면 사용자 피드백으로 조정
