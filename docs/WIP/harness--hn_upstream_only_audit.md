---
title: 업스트림 전용 로직·기록 전수 감사 — 다운스트림 전파 파일 청소
domain: harness
tags: [harness-starter, upstream-only, downstream, contamination, audit]
relates-to:
  - path: harness/hn_generic_contamination_protection.md
    rel: extends
  - path: harness/hn_commit_process_audit.md
    rel: references
  - path: incidents/hn_downstream_name_leak.md
    rel: references
  - path: decisions/hn_doc_naming.md
    rel: references
status: in-progress
created: 2026-04-22
---

# 업스트림 전용 로직·기록 전수 감사

## 배경

harness-starter는 다운스트림에 `harness-upgrade`로 전파된다. 전파 대상
파일 안에 **업스트림 전용 로직·기록**이 섞여 있으면:

- 다운스트림에서는 의미 없거나 오판을 유발
- `is_starter: true` 분기로 매번 스킵해야 함 (런타임 낭비)
- 문서 혼란 (다운스트림 사용자가 "이게 뭐지?" 의문)

2026-04-22 세션에서 `hn_commit_process_audit.md` 항목 #4 검토 중 범위가
commit 스킬을 넘어선다고 판단 → 본 문서로 분리.

## 감사 범위

### 다운스트림 전파 대상 (청소 필요)

| 경로 | 전파 | 비고 |
|------|------|------|
| `.claude/skills/` | ✅ 전체 | `harness-upgrade`가 덮어씀 |
| `.claude/agents/` | ✅ 전체 | 위와 동일 |
| `.claude/rules/` | ✅ 전체 | 위와 동일 |
| `.claude/scripts/` | ✅ 전체 | 위와 동일 |
| `.claude/HARNESS.json` | ⚠ 부분 | `is_starter`·`version` 필드는 다운스트림별 |
| `docs/harness/MIGRATIONS.md` | ✅ 참조 | 다운스트림이 읽는 마이그레이션 가이드 |
| `docs/guides/*.md` | ✅ 선택 | 범용 가이드만 전파 |
| `CLAUDE.md` | ⚠ 부분 | 다운스트림이 자기 프로젝트 용으로 갈아엎음 |

### 업스트림 전용 (다운스트림 무관, 전파 불필요)

| 경로 | 성격 |
|------|------|
| `docs/WIP/` | 업스트림 작업 중 문서 |
| `docs/decisions/hn_*.md` | 업스트림 결정 기록 |
| `docs/incidents/hn_*.md` | 업스트림 사건 기록 |
| `docs/archived/` | 업스트림 폐기 문서 |
| `docs/harness/promotion-log.md` | 업스트림 버전 이력 |
| `docs/clusters/*.md` | 업스트림 문서 인덱스 |

## 감사 대상 키워드·패턴

1. **`is_starter`** 분기 — 전파 대상 파일에서 "starter일 때만 동작"하는 로직
2. **`HARNESS_DEV`** 언급 — 업스트림 개발자 전용 이스케이프 해치
3. **`harness-starter`** 리포 이름 — 문서 본문에서 업스트림 특정
4. **업스트림 버전 범프·promotion-log·starter push 차단** — 업스트림 운영 기능
5. **다운스트림 고유명사** — 업스트림 문서에 실명 박제된 경우 (오염 리스크)

## 1차 파일 목록 (감사 대상)

2026-04-22 grep 결과 (`is_starter|HARNESS_DEV|harness-starter|업스트림 전용`):

### 코드 (`.claude/`)

- `.claude/scripts/pre-commit-check.sh` — 업스트림 버전 체크·거대 변경 경고
- `.claude/scripts/test-pre-commit.sh` — 업스트림 테스트 시나리오
- `.claude/scripts/bash-guard.sh` — `HARNESS_DEV` 이스케이프 해치
- `.claude/scripts/session-start.sh` — 세션 시작 hook
- `.claude/scripts/downstream-readiness.sh` — 다운스트림 전용 (역방향 — 업스트림에선 무의미)
- `.claude/skills/commit/SKILL.md` — Step 3 버전 체크 (commit audit #4와 연계)
- `.claude/skills/harness-upgrade/SKILL.md` — 업그레이드 로직 (이건 정당 — 다운스트림이 실제 호출)
- `.claude/skills/harness-adopt/SKILL.md` — 이식 로직 (위와 동일)
- `.claude/agents/review.md` — `is_starter` 오염 검토 카테고리
- `.claude/agents/threat-analyst.md` — public repo 위협 분석
- `.claude/rules/naming.md` — 도메인 등급·약어 표 (업스트림 시드 + 다운스트림 확장)
- `.claude/HARNESS.json` — 필드 자체 업스트림·다운스트림 구분

### 문서 (`docs/`)

전파되는 문서 중 업스트림 언급 있는 것:

- `docs/harness/MIGRATIONS.md` — 다운스트림이 읽지만 업스트림 버전 용어 포함
- `docs/harness/hn_index_md_removal.md` — 업스트림 결정 기록 (전파 X)
- `docs/harness/hn_contamination_followup.md` — 업스트림 작업
- `docs/harness/hn_commit_review_handoff.md` — 업스트림 작업
- `docs/harness/hn_commit_perf_optimization.md` — 업스트림 작업
- `docs/harness/hn_generic_contamination_protection.md` — 업스트림 설계
- `docs/harness/hn_simplification.md` — 업스트림 설계
- `docs/decisions/hn_doc_naming.md` — 업스트림 결정
- `docs/decisions/hn_frontmatter_graph_spec.md` — 업스트림 결정
- `docs/decisions/hn_gap_analysis.md` — 업스트림 분석
- `docs/decisions/hn_upgrade.md`·`hn_remote_upgrade_strategy.md` — 업스트림 전략
- `docs/incidents/hn_starter_push_skipped.md` — 업스트림 사건
- `docs/incidents/hn_downstream_name_leak.md` — 오염 인시던트 (기록 자체는 정당)
- `docs/guides/project_kickoff.md`·`hn_upgrade_propagation.md`·`hn_eval_security_patch_port.md` — 가이드
- `docs/archived/promotion-log-2026q2-early.md` — 업스트림 이력

**주의**: `docs/decisions/`·`docs/incidents/`·`docs/harness/` 대부분은
**업스트림 전용 기록**이라 다운스트림에 전파 안 됨 (harness-upgrade가
docs/ 덮어쓰지 않음 — 프로젝트별 문서는 보존). 감사 대상은 **전파 대상
파일** 중심.

## 감사 판정 기준

각 파일·섹션마다 3분류:

| 분류 | 판정 기준 | 조치 |
|------|----------|------|
| **정당** | 다운스트림이 실제로 필요로 함 | 유지 |
| **조건부** | `is_starter: true` 분기로 스킵되면 OK | 분리 가능한지 검토 |
| **오염** | 다운스트림이 읽을 이유 없음 | 업스트림 전용 경로로 분리 |

## 각 파일별 감사 결과 (진행 중)

### `.claude/scripts/pre-commit-check.sh`

- **업스트림 버전 체크**: commit audit #4에서 `harness-version-bump.sh`로 분리 예정 — **조건부 → 분리 대상**
- **거대 변경 경고**: "스코프 분리 권장" 메시지는 다운스트림에도 유효 — **정당**
- **tree-hash 캐시**: commit audit #5에서 폐기 예정 — 독립 이슈

### `.claude/skills/commit/SKILL.md`

- **Step 3 하네스 버전 체크**: commit audit #4 — 분리
- **Starter push 보호**: `HARNESS_DEV=1 git push` 가이드 — **정당** (다운스트림도 자기 repo 보호에 쓸 수 있음? 아니면 업스트림 전용? 판단 필요)

### `.claude/agents/review.md`

- **`is_starter` 오염 검토 카테고리**: 다운스트림이 자기 repo를 starter로 쓸 가능성 있으면 정당. 없으면 업스트림 전용
- 다운스트림이 **다른 스타터 프로젝트를 파생**할 수 있음 → **조건부 정당**

### `.claude/HARNESS.json`

- **`is_starter` 필드**: 다운스트림은 `false`. 업스트림만 `true`. **정당한 차이**
- **`version` 필드**: 업스트림 버전. 다운스트림은 자기 버전 관리 필요한가? 아니면 업스트림 버전만 추적? — **설계 결정 필요**

### `.claude/rules/naming.md`

- **도메인 약어 표 시드**: `harness`·`meta` 2개는 업스트림 정의. 다운스트림이 자기 도메인 추가. **정당**
- **도메인 등급 시드**: 업스트림 2개만 예시. 다운스트림이 확장. **정당**

(이하 파일별 판정은 구현 단계에서 진행)

## 결정 방향 (대략)

1. **commit audit #4 선행 처리**: `harness-version-bump.sh` 분리. 본 감사의 첫 실제 정리 케이스
2. **`HARNESS.json` 필드 재설계**: 업스트림 필드 vs 다운스트림 필드 명시 구분. 다운스트림 인스턴스는 업스트림 필드 무시
3. **문서 차원**: `docs/harness/*.md` 중 다운스트림이 읽을 필요 없는 것은 **전파 배제**. harness-upgrade가 자동 필터
4. **review.md·threat-analyst.md**: `is_starter` 조건 로직 유지. 다운스트림도 starter 파생 가능성 있음
5. **HARNESS_DEV 이스케이프 해치**: 업스트림 전용 이름. 다운스트림이 자기 이름으로 쓸 수 있게 일반화? 아니면 유지? — **판단 필요**

## 실행 계획

본 감사는 **기록 우선, 실행은 항목별 독립 커밋**:

1. ✅ 본 WIP 생성 (2026-04-22)
2. 🔲 파일별 감사 완료 (현재 1차 목록만. 각 파일 본문 실측 필요)
3. 🔲 판정 결과 분류표 완성
4. 🔲 commit audit #4 처리와 연계 — 첫 실제 정리
5. 🔲 다운스트림 전파 필터 구현 (harness-upgrade가 업스트림 전용 경로 배제)
6. 🔲 감사 완료 후 본 WIP → `docs/harness/` 이동 + completed

## 관련 SSOT

- `hn_generic_contamination_protection.md` — 오염 방지 설계 (본 감사의 사전 작업)
- `hn_downstream_name_leak.md` — 다운스트림 실명 유출 인시던트
- `hn_commit_process_audit.md` — commit 스킬 재검토 (본 감사와 교차 영역)
- `hn_doc_naming.md` — 문서 네이밍 결정
- `hn_upgrade_propagation.md` — 업그레이드 전파 가이드

## 후속

각 파일 실측 감사는 단독 커밋으로 진행. 본 문서는 감사 기록을 누적
갱신하는 living document. 최종 승격 시 `docs/harness/`로.
