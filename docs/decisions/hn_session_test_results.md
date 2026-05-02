---
title: 본 세션 시험 결과 종합 — review verdict + wip-sync false positive 누적 데이터
domain: harness
problem: P2
solution-ref:
  - S2 — "review tool call 평균 ≤4회 (부분)"
tags: [review, verdict, wip-sync, json-schema, test-results, session-summary]
relates-to:
  - path: decisions/hn_review_verdict_compliance.md
    rel: extends
  - path: decisions/hn_wip_sync_match_precision.md
    rel: extends
status: completed
created: 2026-05-02
updated: 2026-05-02
---

# 본 세션 시험 결과 종합

다음 컨텍스트로 넘기기 전 8 커밋 누적 시험 데이터 정리. v0.29.2 →
v0.30.6 사이 적용한 해결책의 실측 결과 + 미해결 문제 목록.

**Acceptance Criteria**:
- [x] Goal: 본 세션 시험 결과 + 미해결 우선순위 인계 문서 작성
  검증:
    review: self
    tests: 없음
    실측: 없음
- [x] 우선순위 1 (review verdict leak) — v0.31.0에서 해결 마킹
- [x] 우선순위 2 (wip-sync 의미 매칭) — v0.31.0에서 해결 마킹
- [x] 우선순위 3 (다운스트림 amplification) — 별 WIP로 일원화 마킹
- [x] 사전 결함(T40 회귀·운영/테스트 폴더 혼재) 인계 추가

## 본 세션 누적 커밋

| SHA | 버전 | 내용 |
|-----|------|------|
| `5d00178` | v0.29.2 | commit 5.3 자동 실행 코드 구체화 |
| `acdb877` | v0.30.0 | eval --harness CPS 무결성 감시 신설 |
| `1748215` | v0.30.1 | wip-sync 매칭 정밀화 + 위임 트리거 강화 |
| `4b17d71` | v0.30.2 | MIGRATIONS·README 슬림화 + archive 자동화 |
| `27e5bf7` | v0.30.3 | review verdict prefill 패턴 |
| `7d7548c` | v0.30.4 | eval_cps_integrity 본문 인용 grep 보강 |
| `658b807` | v0.30.5 | review 응답 JSON 규격화 + AC 매핑 의무 |
| `8db0134` | v0.30.6 | Step 7.5 Stage 0 skip 우회 결함 수정 |

## 시험 1 — review verdict 형식 준수율

### 문제
review 에이전트 응답 첫 2줄 `## 리뷰 결과 / verdict: X` markdown 형식이
본 세션 시작 4 커밋(v0.29.2~v0.30.2) 모두 누락 → 1차 재호출로 회복.
매번 5~10초 + tool call 1~2 비용.

### 해결책 시도 추적

| 시도 | 버전 | 방법 | 1차 시험 결과 |
|------|------|------|------|
| markdown 헤더 강제 | 기존 | review.md SSOT 강제 메시지 | ❌ 4/4 누락 |
| prefill 패턴 | v0.30.3 | prompt 끝 `verdict: ` | ❌ v0.30.4 응답 1줄로 끊김 |
| JSON 스키마 + AC 매핑 | v0.30.5 | raw JSON 1개 객체, ac_check 1:1, dup key reject | ⚠️ v0.30.6에서 부분 성공 |

### v0.30.6 review 1차 응답 (JSON 스키마 첫 시험)

```
## 리뷰 결과
verdict: pass

{"verdict":"pass","ac_check":[{...}],"blockers":[],...}
```

- ✅ JSON 객체 출력 + 스키마 준수 (verdict·ac_check·blockers·warnings·axis_check·solution_regression·early_stop·conclusion)
- ✅ AC 2개 ↔ ac_check 2개 1:1 매핑 작동
- ✅ fallback regex로 파싱 성공 → 실용 통과
- ❌ **markdown 머릿말 `## 리뷰 결과 / verdict: pass` leak** — 첫 토큰 `{` 의무 위반
- ❌ 본 세션 5/5 review 응답 모두 markdown 머릿말 leak (JSON 도입 후에도)

### 현 진단

prefill·prompt 강제·JSON 스키마 모두 sub-agent의 markdown 머릿말 leak을
못 막음. 가설:
1. sub-agent가 reasoning 단계에서 markdown으로 사고 → 출력 첫 부분에 leak
2. prefill `{"verdict":"`이 prompt 마지막 줄에 있어도 sub-agent는 응답
   시작점을 자유롭게 선택
3. 시스템 프롬프트나 반환 형식 강제 메커니즘이 sub-agent 호출에선 작동 약함

### 미해결 — 다음 컨텍스트 작업 후보

- **A**: review.md frontmatter에 `output_format: json` 같은 명시 시도
  (Anthropic SDK 표준 — sub-agent에서 작동하는지 미확인)
- **B**: commit 스킬이 응답에서 첫 `{` 이전 텍스트를 무조건 strip — 머릿말
  leak 무시 정책 (현재 fallback regex가 사실상 이 동작 — 문서화만)
- **C**: review를 main agent에서 직접 호출하지 않고 별 스크립트로 후처리
  (과한 변경)

권고: B로 명시 — fallback regex가 의도된 동작이라고 SSOT에 박음. 머릿말
leak은 무시. JSON 객체만 추출 성공하면 통과.

## 시험 2 — wip-sync false positive

### 문제
docs_ops.py wip-sync가 staged 파일명을 무관 WIP 본문에서 부분 매칭해
잘못된 ✅ 추가.

### 본 세션 발생 횟수

| commit | false positive | 처리 |
|--------|-------|------|
| v0.29.2 (5d00178) | 3 WIP (downstream_amplification·eval_cps_integrity·rule_skill_ssot) | 수동 revert |
| v0.30.0 (acdb877) | 3 WIP + 본 신규 WIP frontmatter | 수동 revert + WIP 정정 |
| v0.30.1 (1748215) | 0 (정밀화 적용) | — |
| v0.30.2 ~ v0.30.5 | 0 (대부분 staged WIP 직접 작업) | — |
| v0.30.6 (8db0134) | 1 (rule_skill_ssot AC 본문 commit/SKILL.md 매칭) | 수동 revert |
| v0.30.7 (의미 게이트 도입) | — | problem 메타데이터 게이트로 차단 |

### 해결책 시도

| 시도 | 버전 | 방법 | 결과 |
|------|------|------|------|
| 정규식 정밀화 | v0.30.1 | `^\s*[-*]\s+\[[ xX]\]\s` (체크박스 한정) | ✅ 사전 준비·frontmatter false positive 차단 |
| frontmatter 영역 스킵 | v0.30.1 | `_fm_end` 인덱스 | ✅ relates-to YAML false positive 차단 |
| body_referenced 정밀화 | v0.30.1 | `[x]` 체크박스 + staged 파일 언급 | ✅ 자동 이동 false positive 차단 |

### v0.30.6 발견 — 의미 매칭 한계

`hn_rule_skill_ssot.md`의 AC `Goal: commit/SKILL.md에서 룰 본문 재진술
제거 → SSOT link만`. v0.30.6 commit이 commit/SKILL.md 수정한다고 staging
하면 매칭 — **단어 grep 의미는 정합**이지만 **작업 의도는 다름**.

본질: 단어 매칭은 **어휘적 일치**만 잡고 **의미 일치**는 못 잡음. AC 본문의
파일명이 staged 파일과 일치해도 그 작업이 그 AC를 충족하는 것은 아님.

### 미해결 — 다음 컨텍스트 작업 후보

- **A**: AC 매칭에 의미 일치 신호 추가 (예: WIP frontmatter `problem` ==
  현 작업 problem) — 메타데이터 기반 추가 게이트
- **B**: 수동 확인 단계 추가 — wip_sync_matched > 0이면 사용자 확인 후
  진행 (현재 자동 진행 → 사용자가 못 알아챔)
- **C**: AC가 staged 파일을 커버한다는 명시 신호만 인정 (예: AC가 `pytest
  -m X` 지정하고 그 marker가 본 commit으로 통과해야)

권고: B — 가장 보수적. 자동 매칭 신뢰도가 낮으니 사용자 검토 1단계 추가.
v0.30.1·v0.30.6 false positive는 수동 revert로 회복했으나 매번 작업자
부담.

## 시험 3 — Stage 0 skip wip-sync 우회

### 문제
v0.30.5 commit이 review 영역 변경이라 `recommended_stage: skip` →
Step 7.5 "Stage 0 skip도 스킵" 조건이 wip-sync를 가로챔 → AC 모두 [x]
였던 hn_review_verdict_compliance.md가 자동 이동 안 됨.

### 해결책 (v0.30.6에서 즉시 처리)

- Step 7.5 분기를 verdict 기반으로 재정의
- block만 차단, skip·pass·warn 모두 wip-sync 실행
- 본 commit이 자기증명 — v0.30.6에서 실제 wip-sync 실행 확인 (단 false
  positive 1건도 동시에 발생, 시험 2 참조)

### 평가
**해결됨**. v0.30.6에서 실제 동작 확인.

## 시험 4 — eval_cps_integrity proxy 한계

### 문제
v0.30.0에서 P1·P3·P4·P6 frontmatter 인용 0건 → 정체 의심 출력.
사용자 검토(hn_cps_problem_inflation_review.md) 결과 P1·P6는 false
positive (본문 인용 활발), P3·P4는 진짜 정체이나 다운스트림 영향.

### 해결책 (v0.30.4)

`CPS_REF_PATTERNS` 4종 정규식으로 본문 인용까지 카운트:
- "CPS 연결: P#"
- "P#(추측|review|...)"
- "P# → S#"
- "P# (충족|재발|연관|해결)"

### 결과 (실측)

| Problem | 이전 (frontmatter only) | 본 보강 후 |
|---------|---------|---------|
| P1 | 0 ⚠ | **4** ✅ false positive 해소 |
| P2 | 2 | **8** |
| P3 | 0 | 0 (다운스트림 사안 — 폐기 시기상조) |
| P4 | 0 | 0 (다운스트림 사안) |
| P5 | 4 | **9** |
| P6 | 0 ⚠ | **2** ✅ |

### 평가
**해결됨** (proxy 정밀화 + 사용자 검토 결합으로 인플레이션 신호 신뢰도
회복).

## 시험 5 — MIGRATIONS·README 비대화

### 문제
사용자 지적 — MIGRATIONS.md 759줄(24개 섹션), README 변경 이력 31개로
매번 로딩·갱신 비용 누적.

### 해결책 (v0.30.2)

- "최신 5개만 본문" 정책
- `harness_version_bump.py --archive [keep=5]` 신설 — 멱등성 보장
- commit/SKILL.md Step 4에 자동 호출
- MIGRATIONS-archive.md 분리

### 결과
- MIGRATIONS.md: 759 → 240줄 (68% 감소)
- README.md: 420 → 297줄 (29% 감소)
- 다음 commit부터 자동 — v0.30.3 이후 매 commit에서 6번째 섹션 자동 archive 이동 확인

### 평가
**해결됨**. 자동화 작동 확인.

## 시험 6 — debug-specialist 위임 자동 트리거

### 문제
본 세션 wip-sync false positive 2회(v0.29.2·v0.30.0) 발생 동안
`no-speculation.md` "동일 수정 2회 이상" 룰이 자동 발화 안 됨. 사용자가
직접 지적해 debug-specialist 호출.

### 해결책 (v0.30.1)

- session-start.sh: fix prefix 의존 → "공통 파일 2 커밋 연속 수정"으로 확장
- 메타 파일(HARNESS.json·README·MIGRATIONS·clusters) 노이즈 제외
- no-speculation.md 호출 조건표에 "동일 시스템 동작 이슈 2회 이상" 행 추가

### 평가
**부분 해결**. 다음 세션 시작 시 동작 확인 필요. 본 세션은 변경 후 추가
재발 없어 검증 불가 (단 v0.30.6 false positive 1건은 다른 패턴이라
무관).

## 미해결 누적 (다음 컨텍스트 작업 후보)

### 우선순위 1 — review JSON 머릿말 leak ✅ **해결 (v0.30.7)**

- 5/5 응답에 `## 리뷰 결과 / verdict: X` markdown 머릿말 leak
- debug-specialist 진단: Agent tool sub-agent prefill 미작동 (H1 확정)
- **해결책**: JSON 스키마·AC 매핑 의무 폐기 + verdict 단어 추출만으로 단순화
  - 신규 `.claude/scripts/extract_review_verdict.py` (정규식 추출)
  - review.md 출력 형식 SSOT 자유화 (verdict 단어만 포함)
  - commit/SKILL.md inline 80줄 heredoc → 1줄 호출
  - 테스트 6/6 통과 (markdown leak 케이스 포함)
- 상세: `docs/decisions/hn_review_verdict_compliance.md` v0.30.7 변경 이력

### 우선순위 2 — wip-sync 의미 매칭 한계 ✅ **해결 (v0.30.7 — D 옵션)**

- v0.30.6에서 `hn_rule_skill_ssot.md` AC 본문 우연 일치 false positive
- 단어 grep으로는 의미 매칭 못 함
- **해결책 (D 옵션)**: frontmatter `problem` 메타데이터 게이트
  - staged WIP의 `problem` 집합 수집 → 후보 WIP의 `problem`이 그 집합에 있으면 인정
  - 직접 체크박스 매칭·body_referenced·abbr 매칭 모두 게이트 적용
  - 본 WIP가 직접 staged면 자기 자신이라 게이트 skip (작성자 의도 명시)
  - staged WIP에 `problem`이 하나도 없으면 게이트 skip (코드 단독 commit)
- **부수 수정**: T40 wip-sync abbr 회귀 fixture 결함 수정
  - `wipsync_repo` fixture가 starter repo의 docs/WIP 비우고 시작
  - `_run_wip_sync` 반환값에 stdout 합쳐 Windows subprocess stderr 흡수 대응
- **테스트**: TestWipSyncProblemGate 3 케이스 추가 (mismatch 차단·match
  통과·staged WIP 없음 skip), 기존 9개 회귀 모두 통과

### 우선순위 3 — `hn_downstream_amplification` ⏭ **별 WIP 일원화**

별도 WIP `decisions--hn_downstream_amplification.md`가 이미 존재 (problem
P5, solution-ref S5). 본 문서에서는 이관만 하고 작업은 그쪽으로 단일화.
다음 컨텍스트는 그 WIP 직접 Read.

### 우선순위 4 — `hn_rule_skill_ssot` (룰-스킬 중복)

- advisor 폭주 위험 경고 명시
- 6개월 운용 측정 후 commit/SKILL.md 한정 1단계 적용 권고
- 본 wave는 측정만 — 매트릭스 작성 (룰 12 × 스킬 13)

### 우선순위 4.5 — T40 wip-sync abbr 매칭 회귀 (사전 결함, 우선순위 2와 묶기)

`test_pre_commit.py::TestWipSyncAbbrMatch` 2 케이스 fail (v0.30.6 시점부터
존재 — v0.30.7 작업 시 인지). stderr 빈 문자열 → "skip"·"2개" 경고 메시지
누락:

- `test_abbr_match_no_checklist`: abbr 매칭으로 자동 이동 케이스
- `test_abbr_multi_wip_skip`: 같은 abbr WIP 2개 skip 경고 케이스

**왜 남았나**:
- AC 명시 요구가 없어서 self-verify에서 안 잡힘
- pre-check이 `pytest -m docs_ops`를 자동 실행 안 함 → commit 시점 인지 못 함
- v0.30.1 wip-sync 정밀화 사이드 이펙트 의심 (검증 안 됨)

**방향**: 우선순위 2 (wip-sync 의미 매칭 한계)와 같은 영역 — 묶어서 진단·
수정. 별도 처리하면 스코프 이탈.

### 우선순위 4.6 — `.claude/scripts/` 운영/테스트 혼재

현재 `.claude/scripts/`에 운영 코드(`pre_commit_check.py`·`docs_ops.py`)와
테스트 코드(`test_*.py`·`conftest.py`)가 같은 폴더. 다운스트림 배포 단순성
때문에 의도적으로 보이나 분리 원칙 위반:

- 운영/테스트 폴더 분리 원칙 위반
- IDE에서 scripts/ 열면 노이즈
- 다운스트림이 `pytest .claude/scripts/`로 회귀 돌릴 때 명령 어색

**옵션**:
- A: 그대로 둠 (현행 — 다운스트림 단순성 우선)
- B: `.claude/scripts/tests/` 하위 분리
- C: `.claude/tests/`로 완전 분리

**방향**: ADR 1개로 결정 후 일괄 이동 (commit 1회). 본 WIP 우선순위 2 이후
처리 권고.

### 우선순위 5 — review 1차 응답 끊김 (v0.30.4 사례)

- 본 세션 1회 발생 — "지시 1~3 확인 완료. 이제 archive 자동화 확인" 한 줄
- maxTurns 소진 또는 응답 절단 추정 — 명확 원인 미확인
- JSON 스키마 적용 후 재발 안 함 → 일단 보류, 누적 추적

## 성공한 영역

- **시험 3** (Stage 0 skip 우회) — 즉시 해결됨
- **시험 4** (eval proxy) — 정밀화 + 사용자 검토 결합으로 신뢰도 회복
- **시험 5** (MIGRATIONS·README 슬림화) — 자동화 + 5개 정책 작동
- **시험 2 부분** — frontmatter·사전 준비 false positive 차단 완전 (의미 매칭만 잔존)

## 핵심 교훈 (다음 컨텍스트 인계)

1. **markdown 형식 강제는 sub-agent에서 신뢰도 낮음** — JSON 스키마조차
   머릿말 leak. fallback regex 같은 관용적 파싱이 실용적
2. **단어 매칭은 의미 매칭이 아님** — wip-sync false positive처럼 어휘
   일치를 의미 일치로 오인하는 패턴 반복. 메타데이터 게이트 또는 사용자
   확인 단계 필요
3. **자기증명 사고 패턴 유효** — v0.30.5 → v0.30.6에서 결함 노출 → 즉시
   수정 + 결정 문서 누적. 같은 세션 처리가 누락 방지
4. **사용자 지적이 정밀화 트리거** — "verdict 중복은?" "AC 매핑은?"
   같은 질문이 스키마 v1 → v2 개선 추진. Claude 자가 검토만으론 발견
   못 한 결함 다수
5. **본 세션은 미해결 누적이 핵심 정보** — 8 커밋 모두 운용 검증 미완.
   다음 commit부터 5+ 데이터 누적 후 효과 재평가 필요

## 다음 컨텍스트 시작점 권고

- 본 문서 1차 Read → 시험 결과 + 미해결 5개 우선순위 파악
- `hn_review_verdict_compliance.md`·`hn_wip_sync_match_precision.md` 참조
- 우선순위 1·2가 본 세션 미완료 핵심 — 둘 다 review/wip-sync 영역
- 우선순위 3은 다운스트림 작업 시점에 자연 처리
- 본 WIP는 정보 인계용 — 작업 완료 시 결정 문서로 이동, 그 외 신규 작업
  시작 시 별 WIP 분리
