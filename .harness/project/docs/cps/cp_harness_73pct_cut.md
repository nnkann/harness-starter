---
title: 하네스 73% 삭감 + wiki 그래프 모델 발견
domain: cps
c: 통제 룰 누적 1만 줄 — LLM 자가 발화 의존 메커니즘 강제력 0 실측. 가속 자산은 묻혀있음
tags: [redesign, simplify, wiki-graph, tag-policy, cps-case]
p: [P2, P5, P6, P7, P8, P9]
s: [S2, S5, S6, S8, S9]
result: in-progress
commit: pending
wave: v0.47.x 73% 삭감 wave
status: in-progress
created: 2026-05-15
---

# C·P·S 박제

## C (Context)

하네스 starter가 LLM 통제 장치로 자라남. 룰·스킬·스크립트 1만 줄 누적. 자가
발화 의존 메커니즘(BIT Q1/Q2/Q3·debug-specialist 4단계·"1회 실패 즉시 에이전트"
트리거) 강제력 0 실측. 동시에 frontmatter 자산(domain·tags·problem·s)은
116/120 사용률로 누적됐지만 cluster가 평평한 리스트라 wiki 연결망으로 활용
안 됨.

## P (Problems)

- **P8** 자가 발화 의존 규칙 일반 실패 — BIT·debug-guard hook 강제력 0
- **P5** 컨텍스트 팽창 — SKILL.md·rules 1만 줄, 미완독 회피 패턴
- **P2** review 과잉 비용 — staging 5단계 자가 선언 의미 없음
- **P6** 검증망 스킵 패턴 — AC `검증.review` 5단계가 자가 분류라 통과 박제
- **P7** 구성 요소 관계 불투명 — domain 4역할 다중 의미 + cluster 점들로 분리
- **P9** 정보 오염 관성 — tag normalize 약한 강제는 자가 발화라 모순

## S (Solutions)

- **S8** 강제 트리거 우선 — Q1/Q2/Q3 전체 폐기, debug-specialist 1~2단계 압축,
  결정적 신호(test 실패·exit code·git log 동일 수정 2회)만 트리거
- **S5** 압축 + 최소화 — 통제 룰 폐기·축약. anti-defer·bug-interrupt·
  external-experts·pipeline-design 폐기. rules 1,666→931줄
- **S2** 패턴→행동 매핑 단순화 — `/commit --review`/`--no-review` 2단계,
  staging.md 폐기
- **S6** 검증망 위치 정합화 — AC 검증을 implementation 종료로 이동, pre-check은
  사실 게이트만
- **S9** wiki 그래프 모델 — domain=zone, tag=edge(cross-domain), review=속성,
  relates-to=link. cluster 본문에 tag 분포·백링크 자동 생성. tag 정규식
  결정적 차단 (영문 소문자 + 하이픈 + 숫자, 한글 금지)

## 핵심 발견 (본 wave 본질 정렬)

> "wiki처럼 이어지는 거네 — 원래 이걸 원했던 건데 이제야 찾아냈군."
> (사용자, 2026-05-14)

- "그래프 모델"은 **개념 참고**일 뿐 새 도구 도입 아님. 이미 frontmatter에
  있던 것을 wiki 관점으로 이름 붙임
- cluster 폴더 분리(by-domain/by-tag) 폐기 — wiki 본질은 본문 분산 + 메타
  인덱스 단일. 현 폴더 구조 유지하되 cluster 파일에 tag 백링크 섹션 자동 추가
- tag normalize 약한 강제 폐기 — 자가 발화 의존이라 P8 모순. pre-check 결정적
  차단으로 전환
- meta cluster는 빈 상태가 정상 (sample zone). cps도 wave 누적 후 채워짐 —
  본 case가 첫 박제

## 결과 (in-progress)

| 구성 | 시작 | 단기 후 (목표) | 본 commit 실측 |
|------|------|--------------|--------------|
| rules | 1,839 | ~450 | 933줄 (49%) — docs·naming SSOT가 §S-7 자산 흡수 |
| scripts | 5,949 | ~860 | 5,060줄 (15%) |
| skills | 5,124 | ~1,100 | 3,339줄 (35%) — harness-upgrade·adopt·init 본질 자산 보유 |
| agents | 1,583 | ~600 | 1,434줄 (9%) |
| **총** | **14,495** | **~3,010** | **10,766줄 (26%)** |

본 wave 박제(73%)와 갭은 핵심 자산(harness-upgrade·adopt·init·docs_ops·
pre_commit_check·debug-specialist) 보유. 자기 발화 의존 룰과 자가 분류
메커니즘은 일소.

자세히: `docs/WIP/hn_harness_80pct_cut.md` (ADR, in-progress).

## 운용 검증

본 wave completed 전제: 사용자 운용 1~3 세션 체감 OK 판정. 자동 검증 단언 금지.
