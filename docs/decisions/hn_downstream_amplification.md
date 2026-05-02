---
title: 다운스트림 증폭 측정 — Phase 4-A baseline 수집·가설 검증
domain: harness
problem: P5
solution-ref:
  - S5 — "서브에이전트 spawn 시 컨텍스트 < 500k 토큰 (부분)"
tags: [downstream, amplification, baseline, measurement]
relates-to:
  - path: harness/hn_harness_efficiency_overhaul.md
    rel: caused-by
status: completed
created: 2026-05-02
updated: 2026-05-02
---

# 다운스트림 증폭 측정 — Phase 4-A

## 사전 준비
- 읽을 문서: `.claude/skills/implementation/SKILL.md` Step 0.3·0.8, `.claude/scripts/docs_ops.py` (clusters)
- 이전 산출물: hn_harness_efficiency_overhaul.md Phase 2-A v0.29.1 (외형 metric 폐기·AC + CPS 도입)

## 목표
다운스트림에서 도메인·CPS·문서 수 증가에 step 비용이 비선형 증가하는지
**실측 검증**. baseline 수집 + 가설 약화·강화 판단까지가 본 wave 산출물.

게이팅 코드 적용(Phase 4-B)은 본 wave에서 분리 — 측정으로 드러난
병목 5개((a)~(e))는 별 wave WIP로 신설.

## 작업 목록

### Phase 4-A — baseline trace 수집

**Acceptance Criteria**:
- [x] Goal: 다운스트림 1개 이상 프로젝트에서 tool call·시간 trace 수집해 baseline 확보
  검증:
    review: skip
    tests: 없음 (측정 작업)
    실측: trace 결과 본 WIP `## 메모` 첨부
- [x] doc-finder fast scan tool call 수 측정 (3 calls / 12.3s / hit 1)
- [x] SSOT 3단계 탐색 시간 측정 (cluster 5.6s / grep 12.6s / read 6.2s)
- [x] clusters 갱신 빈도 측정 (v0.33.0 업그레이드 commit 1건에서 18/18 전 도메인 재생성. v0.27.x 업그레이드 commit은 0건 — 상시 N 비례 아님, docs_ops.py 본체 변경 시 전수 갱신 패턴)
- [x] 도메인 수에 실제로 비례하는지 확인 — 3환경(2/7/18) 측정 후 가설 약화 결론

### Phase 4-B — 게이팅 코드 적용 (별 wave로 분리)

본 wave 측정 결과 드러난 5개 병목은 별 wave WIP로 분리 신설:

- **(a) init check false-block 제거** — `decisions--hn_init_gate_redesign.md` 신설 (본 세션, 우선순위 1)
- **(b) WIP cluster miss 해결** — 별 wave WIP 신설 대기
- **(c) cluster 재생성 게이팅** — 별 wave WIP 신설 대기
- **(d) Glob 패턴 보강** — 별 wave WIP 신설 대기
- **(e) adopt-without-init 차단·유도** — 별 wave WIP 신설 대기

각 wave는 본 wave의 baseline 결과(`## 메모`)를 근거로 시작. 본 wave는
4-A 측정 종료 시점에 completed 이동.

## 결정 사항

### 2026-05-02 — Phase 4-A 결론 (3환경 baseline 종합)

**측정 환경 3건**:
- starter: 도메인 2, meta 단독 시나리오, Step 0 wall 28.55s, drift N
- 다운스트림 N=2: 도메인 7, 코드 작업, Step 0 wall 77.67s, drift Y
- 다운스트림 N=1: 도메인 18, 코드 작업, Step 0 wall 83.4s, drift Y

**원래 가설("도메인 수 비례 비용") — 약화 결론**:
- 도메인 7 vs 18 차이 2.6x인데 Step 0 wall 차이 1.07x — 도메인 수는 약한 변수
- 도메인 9x(2→18) 차이에 Step 0 2.9x — 비례 약함
- cluster 재생성도 상시 N 비례 아님: docs_ops.py 본체 변경 시에만 전수 mtime
  갱신 트리거 (v0.33.0 업그레이드 commit 1건만)

**진짜 변수 (3환경 종합)**:
1. 환경 양식 drift (init check 4.85s vs 15~19s, 3~4x 차이)
2. 문서 수 (SSOT grep 비용)
3. WIP 비중 (cluster scan miss 빈도)
4. CPS 부재·sample만 존재 (Problem 매칭 불가)

**병목 5개 식별** — 별 wave WIP로 분리 (본 wave 종료 후 신설):
- (a) init check 게이트 정밀화 — **본 세션에서 신설**: `decisions--hn_init_gate_redesign.md`
- (b) WIP cluster miss 해결 — 별 wave 신설 대기
- (c) cluster 재생성 게이팅 — 별 wave 신설 대기
- (d) Glob 라우팅 태그 통과 — 별 wave 신설 대기
- (e) adopt-without-init 차단·유도 — 별 wave 신설 대기 (N=2에서 신규 발견)

**우선순위 근거** (별 wave 신설 시 참고):
- (a) starter 4.85s vs 다운스트림 15~19s, 3~4x. 도메인 수 무관. **우선순위 1**
- (c) meta 단독에서 23.7s 절감 검증됨. **우선순위 2**
- (b) 3환경 중 2개 발현. 단순 fast path. **우선순위 3**
- (d) `<abbr>_*` glob 부분 실패 명시 확인. **우선순위 4**
- (e) 신규 발견 (N=2). starter 자기 영향 검토 의무 사례 (incident hn_sealed_migrations_exempt_gap 형제 패턴). **우선순위 5**

### 2026-05-02 — wave 분리 결정

원래 wave 제목 "도메인 수 비례 비용 제거"는 가설 약화 결론과 부정합 →
"baseline 수집·가설 검증"으로 재서술. Phase 4-B 게이팅 코드 작업은
별 wave 5개로 분리. 본 wave는 4-A 측정·결론까지가 산출물, completed 이동.

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

#### 재측정 노트 (2026-05-02, 같은 환경 dev clone, shell 시뮬)

같은 다운스트림 환경(도메인 18, 동일 작업)을 dev clone에서 shell-only로
재측정. 새 baseline 아님 — owner 요청한 중간 규모(5~10) 미충족.

수령 가치 (2개만):
1. **(g) init drift 헛돔 재현 확인** — CLAUDE.md `## 환경`에 `패키지 매니저:`
   키 부재, project_kickoff sample만 존재. 게이트가 차단 신호 없이 통과 →
   기존 4.1x 비용 부풀림 패턴의 환경 조건 재확인
2. **(h) WIP cluster miss 명시 확인** — in-progress WIP가 어떤 cluster에도
   미등록. cluster scan 항상 hit 0. 새 표현: **"WIP 비중 큰 환경일수록 손해"**
   (활동량 많은 다운스트림에서 더 큰 비용)

수령 미가치:
- shell wall 절대값 (1.018s) — LLM round-trip 빠진 하한선. 기존 83.4s와 비교 불가
- 도메인 수 비례 추세 — 같은 18, 새 데이터 포인트 0
- (i) glob 라우팅 태그 통과 — 라우팅 태그 없는 환경이라 핵심 시나리오 미검증

원본 보고서는 starter 로컬 `.measurements/`(gitignore)에 보존.

### baseline — 다운스트림 N=2 (2026-05-02, 도메인 7 환경, 코드 작업)

> 중간 규모(5~10) 첫 데이터 포인트. 양 극단(2, 18) 사이.
> 원본 측정 데이터는 starter 로컬 `.measurements/`에 보존(gitignore).

- **환경**: 도메인 7개, docs 총 113 (in-progress WIP 8개)
- **측정 작업**: 단일 도메인 코드 리팩토링 (in-progress WIP 1개 영향)
- **implementation Step 0 진입**: tool=9회, wall=77.67s
- **시간 분포** (큰 순):
  - doc-finder fast scan: 16.60s (21%) — Agent 1회, 내부 tool_uses 2
  - init check: 15.07s (19%) — drift 통과
  - CPS 점검·sample 판정 간격: 21.13s (27%)
  - SSOT 3단계 합: ~14.86s (19%, cluster·grep 병렬 + 후보 Read)
  - 측정 시각 호출 오버헤드: ~10s (총 ~13%)

**기존 baseline 셋 재현**:
- (g) init drift Y — `패키지 매니저:` 키 부재 + **CPS sample만 존재**.
  본래 차단 트리거 충족이나 baseline 비교 위해 강제 진행
- (h) WIP cluster miss Y — in-progress WIP 8개 모두 cluster 미포함 (정상),
  cluster scan 단독으로는 도달 불가. keyword grep이 유일 경로
- (i) glob 라우팅 태그 N (부분 실패 명시 확인) — `<abbr>_*` glob hit 0,
  `decisions--<abbr>_*` 직접 매칭만 hit. naming.md 직교 파싱은 docs_ops.py
  abbr 추출에만 적용, 단순 glob은 라우팅 태그 통과 못 함

**새 패턴 (양 극단 N=2 사이 첫 발견)**:
1. **adopt-completed-but-init-skipped 상태** — `harness-adopt`만 돌고
   `harness-init` 안 돈 다운스트림. CPS sample만 존재. Problem 매칭 자체
   불가. Phase 4-B 신규 항목 (e) 후보
2. **WIP 비중 큰 환경의 cluster scan 효용 부재** — in-progress 8개 환경에서
   cluster scan 9.68s가 모두 hit 0. WIP fast path 검토 가치
3. **glob 비대칭** — docs_ops.py는 라우팅 태그 통과, 사용자·에이전트 단순
   glob은 막힘. 같은 의도 두 도구 결과 불일치

**도메인 수 비례 가설 추가 약화**:
- 도메인 7 vs 18 차이 2.6x → Step 0 wall 차이 1.07x (77.67 vs 83.4)
- starter 2 vs 다운스트림 N=2 (7) = 2.7x → wall 2.7x (28.55 vs 77.67) **단, 시나리오
  다름** (meta 단독 vs 코드 작업)
- 결론: 도메인 수보다 **시나리오 성격 + 환경 양식 drift**가 지배 변수

**측정 한계 (보고 명시)**:
- N=1
- Step 0 강제 진행 — 본래 차단 시나리오라 "정상 흐름 baseline" 아님
- doc-finder 에이전트 내부 시간 분리 불가
- 시각 측정 Bash 7회 = ~2s 오버헤드

### baseline — harness-starter (2026-05-02, meta 단독 시나리오)

- **환경**: 도메인 2개 (harness, meta), docs ~140
- **측정 작업**: 로컬 측정 디렉토리 신설 + README (meta 단독)
- **Step 0 wall**: 28.55s (5 tool calls)
  - init check: 4.85s (drift 없음 — `패키지 매니저:` 키 존재)
  - doc-finder: 9.96s
  - SSOT 3단계: 13.74s

**3환경 비교** (도메인 2 / 7 / 18):
| 항목 | starter (2) | 다운스트림 N=2 (7) | 다운스트림 N=1 (18) |
|------|-------------|--------------------|---------------------|
| Step 0 wall | 28.55s | 77.67s | 83.4s |
| init check | 4.85s | 15.07s | 19.7s |
| doc-finder | 9.96s | 16.60s | 12.3s |
| SSOT 3단계 | 13.74s | 14.86s | 34.4s |
| 시나리오 | meta 단독 | 코드 작업 | 코드 작업 |
| init drift | N | Y | Y |

**관찰**:
- 도메인 수 9x 차이(2→18)에 Step 0 2.9x — 비례 약함
- 도메인 수 2.6x 차이(7→18)에 Step 0 1.07x — **도메인 수 거의 무관**
- init check는 drift 유무로 갈림: drift 없음(starter) 4.85s vs drift 있음(N=1·N=2) 15~19s. **3~4x 차이**
- SSOT는 starter·N=2 비슷(13.74·14.86), N=1만 34.4s로 큼 — 문서 수(140·113·~360) 영향 추정

**핵심 발견** (3환경 종합):
1. **init drift 게이트 결함 확정** — drift 없음(starter) 4.85s vs drift
   있음(N=2·N=1) 15~19s. 3~4x 차이. 도메인 수 무관, 환경 양식 drift 비용.
   **Phase 4-B (a) 선행 착수 정당화**
2. **meta skip 효과 입증** — meta 단독 변경에서 SSOT(13.74s) + doc-finder(9.96s)
   = 23.7s 절감 가능. 28.55s → 4.85s (~83% 감소)
3. **도메인 수 비례 가설 폐기 수준** — 도메인 7→18(2.6x) Step 0 1.07x.
   본 wave 제목 자체 재검토. 실 변수는 **CPS 부재 + 환경 drift + WIP 비중 +
   문서 수**
4. **doc-finder는 도메인 수 무관 확인** — 9.96·12.3·16.60 (도메인 2·7·18에
   대해 1.2~1.7x). 도메인 수보다 키워드 hit 양이 변수
5. **adopt-without-init 신규 변수** — N=2에서 발견. CPS sample만 존재
   하는 다운스트림 다수 추정. Phase 4-B 신규 항목 (e) 후보

### 운영 메모
- 본 wave는 v0.29.1 hn_harness_efficiency_overhaul.md에서 분리됨
- 측정 게이트 필수 — 추측 기반 적용 금지
- starter 단독 측정으로는 효과 검증 어려움. 다운스트림 1개 이상 필수
- 추가 다운스트림 baseline은 자연 발생 시 본 wave 후속 별 wave 또는 4-B 검증 wave에서 수집
- **starter 운영 데이터 보존 위치**: 로컬 `.measurements/` (gitignore — 다운스트림 오염 회피). 본 WIP·decisions는 placeholder만 사용
- 다운스트림 보고 수령 시 placeholder 일반화 (incident hn_downstream_name_leak 패턴)

## 변경 이력

### 2026-05-02 — v0.34.1 다운스트림 검증 결과 (도메인 18 환경)

다운스트림 1개(도메인 18 / 문서 361 / WIP 5)에서 v0.34.1 4 wave 검증 보고 수령.
`harness-upgrade` 시 충돌 0, 신규 파일 1개(`check_init_done.sh`).

**(c) cluster 재생성 게이팅**:
- 1회차: 갱신 0 / skip 18 (직전 upgrade의 cluster-update가 첫 적용 완료된 상태)
- 2회차: 갱신 0 / skip 18, mtime 완전 일치
- → 결정적 출력 + diff 비교 정상. mtime noise 0 확인 (도메인 18 환경)

**(b) WIP cluster 가시성**:
- `## 진행 중 (WIP)` 섹션 등록: 3 / 18 cluster (WIP 있는 도메인만)
- WIP 5개 중 abbr 매칭 가능 3개 모두 등록 (누락 0)
- 남은 2개는 abbr 없는 전역 마스터형 → cluster 미매핑이 의도된 동작
- WIP 0인 도메인 cluster 15개는 섹션 미생성 (비어있는 섹션 회피 확인)

**(d) Glob 라우팅 태그 비대칭 재현**:
- 단순 glob `WIP/<abbr>_*` → 0 hit (라우팅 태그 prefix `decisions--`에 막힘)
- 양쪽 wildcard `WIP/*<abbr>_*` → 1 hit (통과)
- → 가이드 변경(`docs.md`·`naming.md` 양쪽 wildcard 명시)의 정합성 확인

**참고 baseline (도메인 18 환경)**:
- cluster scan (`cat docs/clusters/<도메인>.md`): 0.016s
- 도메인 한정 grep: 0.104s
- 전체 docs grep: 0.086s
- amplification 본문 baseline의 cluster scan 5.6s와 큰 격차 — 5.6s의
  주된 비용은 cluster scan 자체가 아닌 후속 SSOT 3단계 grep 단계로 추정.
  v0.34.1 결정적 출력은 본문 비대화 방지 효과만, 1차 진입 비용은 원래
  미미했음을 후행 측정으로 확인

**회귀 신호**:
- `/commit` 차단 0, SEALED 회귀 0, validate 오류 0
- cluster의 WIP 링크 dead-link 0
- 사전 dead-link 부채 7건 잔존 (v0.34.1 무관, 별 wave 검토 가치)

**결론**: v0.34.1 4 wave 모두 다운스트림 의도대로 작동. 신규 회귀 0.
(e) adopt 메시지는 다운스트림이 이미 adopt 완료 상태라 본 검증 범위 외.

### 2026-05-02 — `.measurements/` 폴더 폐기

본문 4곳에서 참조한 starter 로컬 `.measurements/` 폴더 폐기. 향후 다운스트림
실측 데이터는 **검증 프롬프트 응답으로만 수령** — 파일·폴더 생성 없이 placeholder
일반화 후 본 문서 변경 이력에 누적. 이유: 로컬 폴더가 gitignore라도 잡파일
누적 + 응답으로 충분히 대체 가능.

본문 참조(라인 104·162·167·253)는 봉인 룰 따라 그대로 두고, 본 항목이 폐기
사실의 SSOT.

### 2026-05-02 — Phase 4-B 별 wave 5개 모두 처리 완료

본 wave에서 분리한 5 병목 모두 후속 wave로 처리. 각 별 wave 결정 문서:

- **(a) init check false-block 제거** — `decisions/hn_init_gate_redesign.md` (v0.34.0)
- **(b) WIP cluster miss 해결** — `decisions/hn_wip_cluster_visibility.md` (v0.34.1)
- **(c) cluster 재생성 게이팅** — `decisions/hn_cluster_update_gating.md` (v0.34.1)
- **(d) Glob 패턴 보강** — `decisions/hn_glob_routing_tag.md` (v0.34.1)
- **(e) adopt-without-init 차단·유도** — `decisions/hn_adopt_without_init_guard.md` (v0.34.1)

본 wave의 baseline 결과는 5 별 wave 결정 문서에서 근거로 인용. 추가 측정·재진행 없음.
