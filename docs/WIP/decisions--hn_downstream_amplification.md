---
title: 다운스트림 증폭 완화 — 도메인 수 비례 비용 제거
domain: harness
problem: P5
solution-ref:
  - S5 — "서브에이전트 spawn 시 컨텍스트 < 500k 토큰 (부분)"
tags: [downstream, amplification, scale-gating, doc-finder]
relates-to:
  - path: harness/hn_harness_efficiency_overhaul.md
    rel: caused-by
status: pending
created: 2026-05-02
---

# 다운스트림 증폭 완화

## 사전 준비
- 읽을 문서: `.claude/skills/implementation/SKILL.md` Step 0.3·0.8, `.claude/scripts/docs_ops.py` (clusters)
- 이전 산출물: hn_harness_efficiency_overhaul.md Phase 2-A v0.29.1 (외형 metric 폐기·AC + CPS 도입)

## 목표
다운스트림에서 도메인·CPS·문서 수 증가에 step 비용이 비선형 증가하는 문제 해결.
실측 baseline 확보 후 단계 적용.

## 작업 목록

### 1. Phase 4-A — baseline trace 수집 (선행, 코드 변경 0)

**Acceptance Criteria**:
- [x] Goal: 다운스트림 1개 프로젝트에서 동일 작업 1건의 tool call·시간 trace 수집해 baseline 확보
  검증:
    review: skip
    tests: 없음 (측정 작업)
    실측: trace 결과 본 WIP `## 메모` 첨부
- [x] doc-finder fast scan tool call 수 측정 (3 calls / 12.3s / hit 1)
- [x] SSOT 3단계 탐색 시간 측정 (cluster 5.6s / grep 12.6s / read 6.2s)
- [x] clusters 갱신 빈도 측정 (v0.33.0 업그레이드 commit 1건에서 18/18 전 도메인 재생성. v0.27.x 업그레이드 commit은 0건 — 상시 N 비례 아님, docs_ops.py 본체 변경 시 전수 갱신 패턴)
- [x] 도메인 수에 실제로 비례하는지 확인 — N=1 한정 (cluster I/O는 비례, 그러나 진짜 병목은 init drift·WIP miss·glob 미스매치)

### 2. Phase 4-B — 게이팅 코드 적용 (Phase 4-A 결과 후)

> **재설계됨 (2026-05-02, baseline N=1 반영)**: 원안의 "도메인 수 비례 cluster I/O 절감"은
> 실측에서 부분 확인됐으나(18/18 재생성 → 6x I/O), Issen baseline에서 더 큰 비용원 셋이
> 드러남. AC를 그 셋 중심으로 재구성. 원래 항목은 (c)로 흡수.

**Acceptance Criteria**:
- [ ] Goal: Issen baseline 대비 implementation Step 0 진입 wall ≤50% 감소 (83.4s → 40s 이하)
  검증:
    review: review-deep
    tests: pytest -m stage
    실측: 같은 작업(lk DB 마이그레이션) 재측정으로 절감 확인
- [ ] (a) init check false-block 제거 — CLAUDE.md drift 게이트가 19.7s 헛돔. drift 감지 로직 정밀화 또는 게이트 자체 재검토
- [ ] (b) WIP cluster miss 해결 — WIP 파일도 cluster scan에서 hit 되도록 (현재 in-progress 작업이 항상 cluster scan miss → grep으로 폴백)
- [ ] (c) cluster 재생성 게이팅 — docs_ops.py 본체 변경 시 18/18 전수 mtime 갱신 패턴 발견(v0.33.0 업그레이드 commit). 신규 문서·이동·rename 시 영향 도메인만 갱신하도록 incremental update + 본체 변경은 별 트리거
- [ ] (d) Glob 패턴 보강 — `lk_*` glob이 `decisions--lk_*` WIP 못 잡는 문제. naming.md 라우팅 태그 직교 파싱과 정합

## 결정 사항

### 2026-05-02 — Phase 4-A baseline N=1 반영, Phase 4-B 재설계

**판단**: B (다른 병목이 진짜 원인) + A 부분 (cluster I/O 비례도 사실).

원래 가설("도메인 수 비례 cluster 비용")은 18/18 재생성으로 부분 확인.
그러나 Issen baseline에서 cluster I/O보다 큰 비용원 셋(init drift 19.7s,
WIP cluster miss, glob 미스매치)이 드러남. Phase 4-B AC를 (a)~(d)로
재구성 — 원안의 cluster 게이팅은 (c)로 흡수, 나머지 셋이 신규 항목.

**샘플 한계 명시**: 다운스트림 N=1 (도메인 18 환경). 중간 규모(5~10)
baseline 부재. 자연 발생 대기.

### 2026-05-02 — starter baseline 측정 (meta 단독 시나리오)

원본 측정 데이터는 starter 로컬 `.measurements/`(gitignore)에 보존.
다운스트림 오염 회피 위해 본문에 핵심 수치만 인라인.

**판단 갱신**:
- **(a) init drift 게이트 결함 확정** — starter 4.85s vs 다운스트림 19.7s
  = 4.1x. 도메인 수 무관. **선행 착수 우선순위 1** (다운스트림 추가 보고 무관)
- **(c) meta skip 효과 입증** — meta 단독 변경에서 23.7s 절감 가능
  (28.55s → 4.85s). **선행 착수 우선순위 2**
- **(b) WIP cluster miss·(d) glob 미스매치** — meta 시나리오에서 미발현.
  중간 규모 다운스트림 baseline 1건 추가 후 우선순위 확정
- **도메인 수 비례 가설 약화** — 본 wave 제목("도메인 수 비례") 자체
  재검토 필요. 실 변수는 문서 수 + 환경 drift. 4-B 종료 후 wave 제목·
  목표 재서술 검토

## 메모

### baseline — 다운스트림 N=1 (2026-05-02, 도메인 18 환경)

> 다운스트림 고유명사 면제 범위는 incidents `symptom-keywords`만.
> 본 WIP는 decisions/로 전파되므로 placeholder(`<도메인 N>` 등) 사용.
> 원본 측정 데이터는 starter 로컬 `.measurements/`에 보존(gitignore).

- **환경**: 도메인 18개, docs 총 ~360
- **측정 작업**: 단일 도메인 DB 스키마 마이그레이션 (실제 차기 작업)
- **implementation Step 0 진입**: tool=8회, wall=83.4s
- **시간 분포** (큰 순):
  - SSOT 3단계: 34.4s (41%)
  - init check false-block: 19.7s (24%)
  - doc-finder fast scan: 12.3s (15%)
  - 나머지: 측정 오버헤드
- **doc-finder fast scan**: 3 calls (Glob×2 + Grep×1) / 12.3s / hit 1
- **SSOT 3단계**:
  - cluster scan: 5.6s, hit 0 (해당 도메인 cluster 비어 있음 — WIP 미포함 설계)
  - keyword grep (본문 2회): 12.6s, unique hit 6
  - 후보 Read: 6.2s, 1 파일 (50줄)
- **commit clusters 갱신** (최근 5 commit):
  - v0.33.0 업그레이드 commit: 18/18 전 도메인 재생성
  - v0.27.x 업그레이드·기타: 0건
  - **결론**: 상시 N 비례 갱신 아님. docs_ops.py 본체 변경 시에만 전수 mtime 갱신 트리거

**관찰 — 가장 비싼 단계 셋**:
1. **SSOT 3단계 (34.4s, 41%)** — 가장 큰 wall time 소비
2. **init check false-block (19.7s, 24%)** — CLAUDE.md `## 환경`의
   `패키지 매니저:` 키 부재(다운스트림 자체 양식). project_kickoff.md도
   sample만 존재. starter 양식 강제 vs 다운스트림 자유도 트레이드오프
3. **WIP cluster miss** — WIP가 cluster 미포함 설계라 in-progress 작업은
   cluster scan 항상 miss → grep으로 폴백
4. **Glob 패턴 미스매치** — `<abbr>_*` glob이 `decisions--<abbr>_*` WIP
   못 잡음. 라우팅 태그 `--` 때문

**체감 — 도메인 수 비례 비용**: 부분 Y.
- **Y**: cluster 재생성 비용(N개 파일 I/O), cluster scan hit rate 저하
- **N**: keyword grep(ripgrep 효율), doc-finder fast scan(고정 호출 수)
- **추정 amplification**: SSOT 34.4s vs 추정 starter 12s = 약 2.8x

**측정 한계**:
- N=1 단일 작업
- wall에 Bash 타임스탬프 오버헤드 포함
- 인간 사고·LLM reasoning 시간 미포함

### baseline — harness-starter (2026-05-02, meta 단독 시나리오)

- **환경**: 도메인 2개 (harness, meta), docs ~140
- **측정 작업**: 로컬 측정 디렉토리 신설 + README (meta 단독)
- **Step 0 wall**: 28.55s (5 tool calls)
  - init check: 4.85s (drift 없음 — `패키지 매니저:` 키 존재)
  - doc-finder: 9.96s
  - SSOT 3단계: 13.74s

**다운스트림 N=1 대비 비교**:
| 항목 | starter | 다운스트림 | 비율 | 도메인 수 비율 |
|------|---------|------------|------|---------------|
| Step 0 wall | 28.55s | 83.4s | 2.9x | 9x |
| init check | 4.85s | 19.7s | **4.1x** | 9x |
| doc-finder | 9.96s | 12.3s | 1.2x | 9x |
| SSOT | 13.74s | 34.4s | 2.5x | 9x |

**핵심 발견**:
1. **init drift 게이트 결함 확정** — 4.1x 차이는 도메인 수(9x) 무관한 환경 양식 drift 비용. **Phase 4-B (a) 선행 착수 정당화**
2. **meta skip 효과 입증** — meta 단독 변경에서 SSOT(13.74s) + doc-finder(9.96s) = 23.7s 절감 가능. 28.55s → 4.85s (~83% 감소)
3. **도메인 수 비례 가설 약화** — 도메인 9x인데 SSOT만 2.5x. ripgrep 효율 + 빈 cluster 즉시 종료가 buffer. 실 변수는 **문서 수 + 환경 drift**
4. **doc-finder는 도메인 수 무관 확인** — 1.2x

### 운영 메모
- 본 wave는 v0.29.1 hn_harness_efficiency_overhaul.md에서 분리됨
- 측정 게이트 필수 — 추측 기반 적용 금지
- starter 단독 측정으로는 효과 검증 어려움. 다운스트림 1개 이상 필수
- 다음 다운스트림 보고 수령 시 본 섹션에 `### baseline — 다운스트림 N=N` 형식으로 추가 (고유명사 박지 마라 — incident hn_downstream_name_leak 패턴)
- 추가 시나리오 측정 후보: meta 도메인 단독 변경 (README 수정·메모리 인덱스 갱신 등) — Phase 4-B (a) `meta skip` 효과 검증용
- **starter 운영 데이터 보존 위치**: 로컬 `.measurements/` (gitignore — 다운스트림 오염 회피). 본 WIP·decisions는 placeholder만 사용
