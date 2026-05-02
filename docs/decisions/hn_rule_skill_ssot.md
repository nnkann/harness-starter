---
title: 룰-스킬 중복 제거 — 룰 SSOT 강제 (Phase 5)
domain: harness
problem: P5
solution-ref:
  - S5 — "원인이 특정되면 해당 항목 제거 + 실측 재측정 (부분)"
tags: [rules, skills, ssot, duplication]
relates-to:
  - path: harness/hn_harness_efficiency_overhaul.md
    rel: caused-by
status: completed
created: 2026-05-02
updated: 2026-05-02
---

# 룰-스킬 중복 제거

## 사전 준비
- 읽을 문서: `.claude/rules/*.md` (12개), `.claude/skills/*/SKILL.md` (13개)
- 이전 산출물: hn_harness_efficiency_overhaul.md (룰·에이전트 메타데이터 추가됨)
- 자기증명 사례: hn_upstream_anomalies.md Phase 1 — install-starter-hooks.sh와 pre_commit_check.py의 시크릿 면제 패턴이 별개 SSOT라 한쪽 갱신 시 다른 쪽 동기화 누락

## 목표
룰(`.claude/rules/*.md`)을 SSOT로 강제. 스킬 step에서 룰 본문 재진술 금지,
진입점·link만. 룰 갱신 시 스킬 동기화 누락 사고 방지.

## 작업 목록

### 1. 룰-스킬 중복 매핑 (선행 측정)

**Acceptance Criteria**:
- [x] Goal: 어느 스킬이 어느 룰을 재진술하는지 전수 매핑
  검증:
    review: skip
    tests: 없음 (측정 작업)
    실측: 매핑 결과 본 WIP `## 결정 사항` 첨부
- [x] 12개 룰 × 13개 스킬 매트릭스
- [x] 재진술 빈도 높은 top 5 추출 (top 10이 아닌 5 — R 단독 셀 0개로 핫스팟 적음)

### 2·3. 적용 wave 분리 (별 WIP)

본 wave는 **측정만 완료**. Task 2(commit/SKILL.md 1단계 적용)·Task 3(점진
확대)는 측정 결과 평가 후 별 wave로 진행.

→ 별 WIP `decisions--hn_rule_skill_ssot_apply.md` 신설 (Task 2 시작 시점에).
본 wave가 caused-by 관계로 그곳 frontmatter 명시.

## 결정 사항

### Task 1 측정 결과 (2026-05-02)

**측정 방법**: 각 스킬 SKILL.md에서 룰 파일명·rules/X.md 경로 grep + 인접
컨텍스트 분류. 분류 키:

- `-`: 언급 없음
- `L`: SSOT link만 (`SSOT`·`참조`·`상세는 X` 표현)
- `R`: 본문 재진술 (조건·금지 패턴·절차를 SKILL.md 본문에 다시 적음)
- `L+R`: 둘 다 (link도 있고 일부 재진술도 있음)
- `*`: 룰을 생성·관리하는 책임 스킬 (예: naming-convention → naming.md)

### 룰-스킬 매트릭스 (12 룰 × 13 스킬 = 156 셀)

| 스킬 \ 룰 | coding | docs | ext-exp | hooks | int-1st | memory | naming | no-spec | pipe | sec | self-v | staging |
|-----------|:------:|:----:|:-------:|:-----:|:-------:|:------:|:------:|:-------:|:----:|:---:|:------:|:-------:|
| advisor | L | - | - | - | - | - | L | - | - | - | - | - |
| check-existing | - | - | - | - | - | - | - | - | - | - | - | - |
| coding-convention | * | - | - | - | - | - | - | - | - | - | - | - |
| commit | - | L | - | - | - | L | L | - | - | - | L | L+R |
| eval | L | - | - | - | - | - | L | - | - | L | - | - |
| harness-adopt | - | L+R | - | - | - | - | L+R | - | - | - | L | - |
| harness-dev | - | L | - | - | - | - | - | - | - | - | - | - |
| harness-init | - | - | - | - | - | - | L+R | - | - | - | - | - |
| harness-sync | - | - | - | - | - | - | - | - | - | - | - | - |
| harness-upgrade | L | L | - | L | - | - | L | - | - | - | - | - |
| implementation | - | L+R | - | - | - | - | L | L | - | - | L | L |
| naming-convention | - | - | - | - | - | - | * | - | - | - | - | - |
| write-doc | - | L+R | - | - | - | L | L+R | - | - | - | - | - |

### 재진술 (R) 핫스팟 — top 5

| 스킬 × 룰 | 재진술 위치 | 영향 |
|-----------|-----------|------|
| `commit × staging` | Step 7 Stage별 행동 요약 (`staging.md` 본문 Stage 정의 일부 인라인) | 룰 본문 갱신 시 SKILL.md 동기화 필요 |
| `harness-adopt × docs` | "분류 기준 (docs.md에 정의)" 섹션 본문 일부 인라인 | docs.md 갱신 시 동기화 누락 위험 |
| `harness-adopt × naming` | 도메인 등록 절차·날짜 suffix 처리 본문 | naming.md 갱신 시 동기화 누락 위험 |
| `implementation × docs` | "의무 절차 (docs.md에서 상세)" 본문 단계 나열 | docs.md SSOT 우선 + 분리 판단 변경 시 영향 |
| `write-doc × docs/naming` | 프론트매터 절차·도메인 등록 절차 본문 | docs.md·naming.md 갱신 시 동기화 누락 |

### 측정 통계

- 전체 셀 156개 중 언급 ≥ 1: 30개 (19%)
- L 단독: 19 셀 (61%)
- L+R: 6 셀 (19%)
- R 단독: 0 셀
- `*` 책임 스킬: 3 셀 (coding-convention·naming-convention·*)
- 재진술 양은 **link 표현이 압도적**. R 단독 셀 0개 — 이미 SSOT 우선 패턴 정착

### 위험도 평가

**고위험 (자기증명 사고 발생 가능)**: top 5 핫스팟 위주. SKILL.md 본문이
룰 본문 일부를 인용하면 룰 갱신 시 SKILL.md 동기화 누락 → install-starter-
hooks.sh ↔ pre_commit_check.py S1_LINE_EXEMPT 동일 패턴 재발 가능.

**저위험**: 단독 link만 있는 셀(19개)은 자동 동기화. 룰 갱신 → SKILL.md가
참조하는 SSOT가 그대로 갱신됨.

### Task 2 우선 적용 후보 (상위 5개 핫스팟)

핵심 원칙: SKILL.md 본문에서 룰 본문 일부 인용 제거 → 한 줄 link로 단순화.
1패스 모두 처리하지 말고 1개씩 점진 적용 + 6 commit 누적 효과 측정.

순서 권고:
1. **commit × staging** (Step 7 Stage별 행동) — 본 wave 1단계 SSOT가 명시한 1순위
2. **implementation × docs** (의무 절차 본문) — staging Step 7 절차와 같은 결
3. **write-doc × docs/naming** (프론트매터·도메인 절차) — 유사 패턴 묶음 처리
4. **harness-adopt × docs/naming** (분류 기준·도메인 절차) — 사용 빈도 낮음 (initial setup만), 후순위

### 결정

본 wave는 **측정만 완료** 후 commit. Task 2(commit/SKILL.md 적용)·Task 3
(점진 확대)는 별 wave로 분리 — 본 wave에서 측정 후 효과 평가 데이터
누적이 다음 작업 전제.

이유:
- 1패스 적용은 advisor 폭주 위험 (사전 보강 지적)
- R 단독 셀 0개 → 시급도 낮음. 핫스팟 5개도 모두 L+R로 link 절반 이상
- Task 2 적용 후 효과 측정에 6 commit 권고. starter 단독으로 의미 있는
  효과 측정은 한 wave에 안 끝남
- 본 wave는 의사결정 자료 확보가 본질

## 메모
- 본 wave는 v0.29.1 hn_harness_efficiency_overhaul.md에서 분리됨
- 폭주 위험 (advisor 사전 보강에서 지적): 1단계로 끝나지 않고 N단계 폭주 가능 — incremental 정리도 옵션
- 자기증명 사례 발생: install-starter-hooks.sh ↔ pre_commit_check.py S1_LINE_EXEMPT 동기화 누락 (이미 발현됨)
- v0.31.0 자기증명 사례: hn_rule_skill_ssot.md AC 본문 "commit/SKILL.md" 어휘 hit으로 wip-sync false positive 발생 → wip-sync 의미 게이트로 차단됨 (어휘 매칭의 근본 한계 노출)
