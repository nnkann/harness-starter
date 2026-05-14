---
title: Wiki 그래프 자산 생성 wave — frontmatter·tag·relates-to 일제 정비
domain: harness
problem: P7
s: [S7, S9]
tags: [wiki-graph, frontmatter, cluster, relates-to]
relates-to:
  - path: WIP/hn_harness_80pct_cut.md
    rel: extends
status: in-progress
created: 2026-05-15
---

# Wiki 그래프 자산 생성 wave

## 0. 박제

본 wave는 73% 삭감 wave(`hn_harness_80pct_cut.md`) §S-7에서 박제한 **별
wave 후보 3건**의 단일 묶음. 메커니즘은 본 wave에서 신설됐고(`docs_ops.py
cluster-update` tag 백링크·pre-check tag 정규식·S# 인용 게이트), 자산
생성·검토는 분량 큼·사람 검토 필요라 별 wave 박제.

**관점**: "신설된 wiki 그래프 모델"이 실제 자산(118개 문서·30+ tag·N개
relates-to)으로 채워지는 단계. 메커니즘 → 데이터 누적.

## 1. 영역 (3개 묶음)

| 영역 | 작업 | 분량 | 검증 |
|------|------|------|------|
| §A. problem 인용률 보강 | 118개 문서 frontmatter `problem`·`s` 누락 일제 검토 + 보강 | 대량 (사람 검토) | 100% 인용률 (현 39%) |
| §B. by-tag cluster 30개 검토 | tag 빈도 5+ tag의 cluster 백링크 자동 생성 (이미 작동 중) + 30개 hit 검토 | 자동 + 사람 검토 | tag 분포 정합 + 노이즈 0 |
| §C. relates-to 측정·폐기 검토 | 사용 빈도 측정 → 폐기 vs 유지 결정 | 조사 + 결정 | 빈도 데이터 + 결정 박제 |

## 2. 영역 순서 + 의존성

§A → §B → §C 순서:

- §A 먼저: problem 인용률 보강하면 tag normalize도 동시 발견·정정 (frontmatter 보강 흐름)
- §B 다음: tag 자산 안정화 후 cluster 검토
- §C 마지막: relates-to는 frontmatter·tag 정비 후 본질 가치 측정 (의존성 약함)

영역 안 폐기·신설·갱신 즉시 완료. 영역 미루기 금지 (본 wave §3 원칙
상속).

## 3. §A. problem 인용률 보강 흐름

```
1. 현 인용률 측정 — frontmatter `problem` 누락 문서 list
2. 도메인별 분류 (decisions/incidents/guides/harness)
3. 사용자 인터랙티브 검토:
   - 각 문서에 적절한 P# 매칭 (kickoff cps list 참조)
   - "어디에도 안 맞음" → P10·S10 (엄격 기준 적용)
   - 명백한 도메인은 일괄 처리
4. frontmatter 일제 보강
5. pre-check 회귀 점검
```

## 4. §B. by-tag cluster 검토

```
1. docs_ops.py cluster-update 실행 → 현 tag 분포 출력
2. 빈도 5+ tag list 추출
3. 각 tag 백링크 의미 확인 — 노이즈 vs 본질 클러스터 분류
4. 노이즈 tag → 문서 frontmatter에서 제거 (낮은 빈도면 자연 소멸)
5. 본질 클러스터 → 명시 박제 (cluster 본문 또는 docs 참조)
```

## 5. §C. relates-to 측정·폐기 검토

```
1. 전체 docs/에서 relates-to 사용 빈도 grep
2. rel 6종(extends·caused-by·implements·supersedes·references·conflicts-with)별 사용 카운트
3. 결정 분기:
   - 빈도 < 임계 (예: 도메인당 3건 이하) → 폐기 후보
   - 빈도 충분 + 의미 있음 → 유지
4. 결정 박제 (docs/decisions/ ADR 또는 본 WIP 결과 섹션)
```

## 6. Acceptance Criteria

**Acceptance Criteria**:
- [x] Goal: wiki 그래프 자산 생성 — S7·S9 cascade 충족.
  - §A problem 인용률 100% (현 39% → 보강)
  - §B by-tag cluster 30+ tag 검토 + 노이즈 정리
  - §C relates-to 빈도 측정 + 폐기/유지 결정 박제
  검증:
    tests: 없음
    실측: 운용 검증 (1~2 wave 후 wiki 그래프 사용성 체감)
- [x] §A 완료 — 113/113 인용 (면제 5건 제외 100%)
- [x] §B 완료 — tag 271→정리. 5+ tag 20개. 단복수 통합 + p# tag 제거 (13파일 수정)
- [x] §C 완료 — rel 6종→4종 (extends·caused-by·references·supersedes 유지, implements·precedes·conflicts-with 폐기)
- [x] 본 wave commit + push 완료
- [ ] 사용자 운용 1~2 wave 후 체감 OK 판정

## 7. 결과 박제

### §A 결과
- 자동 분류기 + 사용자 검토 7건 정정 + L 22건 본문 검토
- 적용: 42 + 25 = 67 (이미 박힌 46 - 5 면제 = 41 추가 의무, 실측 42 처리 후 71 누적)
- 최종 인용률 113/118 = 95.8% (5 면제: sample 3 + MIGRATIONS 2)

### §B 결과
- tag 271 unique → 단복수 통합 + p# 제거 = 13 파일 수정
- 5+ tag: 20개 (review 18·commit 13·downstream 13·cps 12·skill 11 등)
- p# tag 7개(p3/p4/p5/p7/p8/p9/p9-candidate) 제거 — frontmatter problem cascade와 이중 박제 회피

### §C 결과
- relates-to 보유율 47% (57/121 문서, 75 rel 인스턴스)
- rel 4종 수렴: extends 35 + caused-by 22 + references 15 + supersedes 1 = 73
- 폐기 3종: implements(2 → extends 흡수)·precedes(2 → 제거)·conflicts-with(0 사용)
- docs.md rel SSOT 4종으로 갱신

## 8. 메모

- 본 wave 73% 삭감 wave §S-7 박제의 자산화 단계 — 메커니즘 → 데이터 누적
- §A가 가장 크고 (자동 분류기 + 사용자 검토), §C가 가장 작음 (측정·결정)
- relates-to rel 폐기 3종은 frontmatter 스키마 변경 cascade. 다운스트림 영향:
  - implements·precedes·conflicts-with 사용 다운스트림이 있다면 첫 commit 차단
    (다만 다운스트림에서 실측 0건 — 본 starter도 사용 빈도 매우 낮음)
- §A 자동 분류기 false-positive 7건 발견 — `karpathy`·`pipeline-design`·
  `starter_push_skipped`·`test_diet`·`simplification`·`upgrade`는 tag 키워드
  매칭이 의미와 불일치. 다음 wave에서 분류기 정련 후보
