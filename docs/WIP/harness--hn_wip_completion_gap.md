---
title: WIP 완료 자동화 구조적 결함 — Step 7.5 미동작 + SSOT 드리프트 + 이동 미연결
domain: harness
tags: [commit, wip, step7.5, ssot, completion]
relates-to:
  - path: harness/hn_commit_process_audit.md
    rel: references
  - path: incidents/hn_review_maxturns_verdict_miss.md
    rel: caused-by
status: in-progress
created: 2026-04-25
---

# WIP 완료 자동화 구조적 결함

## 발견 경위

2026-04-25 세션. `docs/WIP/incidents--hn_review_maxturns_verdict_miss.md`가
대책 실행(f82713d, 5a3d051) 후에도 WIP에 남아 있어 별도 이동 커밋(9809ff6)이
필요했다. git log 추적 결과 세 가지 결함이 겹쳐 있음을 확인.

## 결함 1: Step 7.5 매칭 미동작

**설계**: commit 스킬 Step 7.5가 staged 파일 경로를 WIP 본문에서 찾아 ✅ 추가.

**실제**: f82713d(staged: `commit/SKILL.md`, `review.md`) 커밋 시 WIP 본문에
해당 경로가 명시된 항목이 있었음에도 ✅ 갱신이 일어나지 않았다.

```
# WIP 실행 계획 (당시)
11. commit/SKILL.md split 동적 키 명시 + REVIEW_PRECHECK allowlist 추가
10. review.md:240 드리프트 수정
```

**미동작 원인 가설** (미검증):
- Stage가 deep이었는데 Step 7.5가 실제로 실행됐는지 불명확
- 매칭 로직("경로가 언급된 줄")이 정확히 어떤 패턴으로 grep하는지 스킬 명세에 미정의
- Step 7.5 자체가 실측 검증된 적 없음 — 설계만 존재

## 결함 2: SSOT 드리프트

WIP 문서가 실제 진행 상태의 SSOT여야 하는데, 구현이 완료된 시점에 WIP가
갱신되지 않으면 WIP는 실제보다 항상 뒤처진다.

결과: "WIP에 남아 있는 것 = 할 일 있다"는 전제 자체가 깨진다. WIP를 신뢰할
수 없으면 매 세션 시작마다 WIP를 열어 git log와 대조해야 한다.

## 결함 3: "전부 완료 → 이동" 연결 부재

설령 Step 7.5가 정상 동작해 ✅가 모두 채워지더라도, "전부 ✅ → docs-ops.sh
move 자동 실행"으로 이어지는 로직이 없다. 이동은 항상 수동(사용자 명시 요청).

**핸드오프 계약 단절**: implementation 스킬 핸드오프 계약에
`Pass (나→commit): WIP 파일 경로·status`가 명시되어 있지만, commit 스킬
Step 2는 "사용자 명시 요청만"으로 막혀 있어 수신측 구현이 없다.

## 반복 패턴

별도 WIP 이동 커밋이 빈번하게 발생하고 있다:
- `733b2bb` docs(harness): hn_review_tool_budget WIP → decisions/ 완료 이동
- `9809ff6` docs(harness): hn_review_maxturns_verdict_miss WIP → incidents/ 완료 이동
- `a8f42e3` docs(harness): hn_commit_process_audit completed 이동 + cluster 갱신
- `1960d90` docs(harness): hn_test_suite_perf WIP → completed + cluster 갱신

매번 사용자가 "WIP 남아있네" → 확인 → 별도 커밋으로 처리하는 흐름.

## 이동 커밋의 review 오버헤드

추가 문제: 이동 커밋은 rename + 메타 필드(status, updated) 2개만 바꾸는
순수 문서 이동인데, S9(harness=critical) hit으로 standard review가 돈다.
내용 변경이 없는 이동 커밋에 review는 실질적으로 잡을 게 없다.

pre-check이 "staged 전체가 rename + clusters/meta만"인 이동 커밋을 감지해
skip 판정하는 로직이 없다. 경우의 수 추가(archived+wip, clusters+wip 등)로
해결하면 조합 폭증.

## 해결 방향

### A. Step 7.5 실측 검증 (선행 필수)

현재 설계대로 매칭이 실제로 되는지 검증하지 않은 상태. 먼저 동작 여부
확인 후 결함 확정.

검증 방법: staged 파일 경로가 WIP 본문에 명시된 커밋을 만들어 Step 7.5
실행 후 ✅ 추가 여부 확인.

### B. "전부 ✅ → 자동 이동" 연결

Step 7.5에서 ✅ 갱신 후 해당 WIP의 모든 항목이 ✅이면 `docs-ops.sh move`
자동 실행. 차단 키워드 있으면 이동 대신 사용자 알림.

자동 실행 vs 사용자 confirm 선택 필요.

### C. 이동 커밋 review skip

pre-check에서 "staged 전체가 R(rename) + clusters/meta M만"인 패턴을 이동
커밋으로 감지 → `recommended_stage: skip`. 조합 열거 없이 git rename 비율로
판정.

## 우선순위

1. A (Step 7.5 실측 검증) — 결함 확정 전에 B는 설계 불가
2. C (이동 커밋 skip) — 독립적, 즉시 가능
3. B (자동 이동 연결) — A 검증 후

## 메모

- 이동 커밋 review 문제는 사용자 지적: "incidents 내용 수정인데 리뷰가 뜨는 것도 오바"
- "조합 열거(archived+wip, clusters+wip 등)는 허접" — git rename 비율 방식으로 합의
- Step 7.5 미검증 사실은 이번 세션에서 처음 확인
