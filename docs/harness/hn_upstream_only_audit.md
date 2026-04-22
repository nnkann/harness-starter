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
status: completed
created: 2026-04-22
updated: 2026-04-22
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

## 각 파일별 감사 결과 (2026-04-22 codebase-analyst 실측)

grep + 본문 Read 기반 실측. 판정은 3분류(정당/조건부/오염).

### `.claude/scripts/pre-commit-check.sh`

- **L324 S10 반복 면제 regex · L413 S5 메타 면제 regex**: `docs/harness/promotion-log.md` 경로 하드코딩 → **오염**
  - 다운스트림 리포에 이 경로가 없어 현재는 무해하지만, 우연히 같은 경로가 생기면 오탐 면제. 업스트림 전용 파일이 범용 regex에 박제됨
  - 수정 방향: `IS_STARTER` 조건부로 regex 구성. `is_starter: true`일 때만 promotion-log 포함
- **clusters/ 면제**: 다운스트림에도 유효 → **정당**
- **업스트림 버전 체크 · tree-hash 캐시**: 이 파일에는 없음 (commit audit #4·#5에서 다룸 — 본 감사 범위 밖)

### `.claude/scripts/test-pre-commit.sh`

- **L266·L270·L405·L623 `HARNESS_DEV=1` prep commit**: pre-push hook(starter guard) 격리 목적 → **조건부**
  - 다운스트림에는 pre-push hook 자체가 없어 무해하지만, 업스트림 전용 격리 의도가 주석 없이 섞임
  - 수정 방향: 주석 보강("업스트림 pre-push hook 격리용. 다운스트림 무해")
- **L599-L605 T30 케이스**: `docs/harness/promotion-log.md` 경로 생성해 S5 skip 테스트 → **조건부**
  - 다운스트림 실행 시 경로가 우연히 매칭되면 테스트 의미 흐려짐. pre-check 오염(위) 정리와 연계

### `.claude/scripts/bash-guard.sh`

- **L68 `HARNESS_DEV starter 가드` 주석**: 설계 의도 기록. 실 분기 로직은 별도 hook → **정당**

### `.claude/scripts/session-start.sh`

- **L91 업그레이드 알림 문자열 "harness-starter에서 실행:"**: 다운스트림 사용자를 위한 UX 안내 (어디서 업그레이드 작업을 하는지 알려줌) → **정당**

### `.claude/scripts/downstream-readiness.sh`

- **L39-L43 `is_starter` 필드 검증**: 다운스트림 자가 진단 도구. 필드 설계의 정당한 사용 → **정당**

### `.claude/skills/commit/SKILL.md`

- **L385-L410 Step 3 하네스 버전 체크**: "harness-starter 리포에서만 실행" 텍스트 조건만 있고 **자동 스킵 코드 없음** → **조건부 → 분리 대상**
  - Claude가 매번 텍스트를 읽고 판단 → 실수 여지, 런타임 낭비
  - 수정 방향: **commit audit #4와 연계**. Step 3 진입 시 `IS_STARTER` 체크 후 false면 명시적 skip. 또는 `harness-version-bump.sh`로 분리
- **L665-L675 `HARNESS_DEV=1 git push` 가이드**: `is_starter: true` 분기 코드 명확. else는 일반 push → **정당**

### `.claude/skills/harness-upgrade/SKILL.md`

- **L17·L32-33·L55·L66 `is_starter` 분기 전체**: 업스트림은 origin, 다운스트림은 harness-upstream remote. 정당한 구분 → **정당**

### `.claude/skills/harness-adopt/SKILL.md`

- **L441 URL 예시 `harness-starter.git`**: 사용자 입력 URL의 예시 문자열 → **정당**

### `.claude/agents/review.md`

- **L129-L135·L406-L419 "오염 검토" 카테고리**: `is_starter: true`일 때만 활성화. commit 스킬이 prompt 컨텍스트에 주입 → **정당** (완전 격리)

### `.claude/agents/threat-analyst.md`

- **L33 `is_starter` Pass 계약 필드**: 호출자가 맥락으로 전달, 다운스트림 false도 정상 동작 → **정당**

### `.claude/rules/naming.md`

- **L97 "이 레포(harness-starter)는 코드 폴더가 거의 없어 정의 생략"**: → **조건부**
  - 다운스트림이 자기 프로젝트 경로 매핑을 추가해야 함에도 "생략"이 정당하다고 오해할 수 있음
  - 수정 방향: "업스트림 기본값: 생략. 다운스트림은 자기 경로 매핑 추가 권장"으로 교체

### `.claude/HARNESS.json`

- **L5 `is_starter: true`**: 업스트림 전용 값. 다운스트림은 harness-adopt 시 false로 덮어씀. 필드 설계 자체는 정당 → **정당**

## 요약 판정표

| 파일 | 정당 | 조건부 | 오염 |
|------|------|--------|------|
| `pre-commit-check.sh` | clusters/ 면제 | — | **promotion-log S5/S10 면제 regex** |
| `test-pre-commit.sh` | — | HARNESS_DEV prep · T30 경로 | — |
| `bash-guard.sh` | 주석 | — | — |
| `session-start.sh` | UX 문자열 | — | — |
| `downstream-readiness.sh` | 필드 검증 | — | — |
| `commit/SKILL.md` | push 분기(L665) | **Step 3 자동 스킵 없음** | — |
| `harness-upgrade/SKILL.md` | is_starter 분기 | — | — |
| `harness-adopt/SKILL.md` | URL 예시 | — | — |
| `review.md` | is_starter 격리 | — | — |
| `threat-analyst.md` | Pass 계약 | — | — |
| `naming.md` | — | **L97 맥락 주석** | — |
| `HARNESS.json` | 필드 설계 | — | — |

## 우선 정리 대상 (Top 3)

### 1. `pre-commit-check.sh` promotion-log 하드코딩 제거 (오염, 유일)

- **위치**: L324 `REPEAT_EXEMPT_REGEX`, L413 S5 메타 면제 awk regex
- **수정**: 두 regex에서 `docs/harness/promotion-log\.md` 부분을 `IS_STARTER` 조건부로 구성
- **방법 A (최소 변경)**: 스크립트 상단에서 `IS_STARTER=$(jq -r '.is_starter' .claude/HARNESS.json 2>/dev/null)` 읽고, false/미존재면 regex에서 promotion-log 빼기
- **방법 B (경로 일반화)**: promotion-log는 업스트림 전용 파일이므로 경로 자체를 `.claude/HARNESS.json`처럼 `is_starter`일 때만 접근하는 구조로 재편. 다운스트림 기준에서는 이 파일이 없으니 regex 면제 불필요
- **검증**: T30 테스트가 여전히 통과하는지 (is_starter=true 환경에서)

### 2. `commit/SKILL.md` Step 3 자동 스킵 (조건부, commit audit #4 연계)

- **위치**: L385-L410 Step 3 진입부
- **수정**: `is_starter: true` 체크 명시. false면 "Step 3 skip" 출력 후 Step 4로
- **commit audit #4 연계**: `harness-version-bump.sh`로 분리 시 본 조치는 자동 충족 (스크립트 자체가 is_starter 체크 내장)
- **우선순위**: commit audit #4가 선행되면 본 항목 흡수

### 3. `naming.md` L97 주석 교체 (조건부, 문서 한 줄)

- **위치**: L97 "이 레포(harness-starter)는 코드 폴더가 거의 없어 정의 생략"
- **수정**: "업스트림 기본값: 생략. 다운스트림은 자기 경로 매핑 추가 권장"
- **영향**: 다운스트림 사용자가 이 섹션에서 억제 신호 받지 않음

## 실측 커버리지 한계

감사 자체의 경계를 기록. 아래 3건은 본 감사 범위 밖이며 재발 시 별도
WIP에서 다룬다.

1. `test-pre-commit.sh` T30은 업스트림(is_starter=true) 환경에서만 PASS
   확인. 다운스트림 실제 실행은 다운스트림 repo에서 검증되어야 하며 본
   리포 감사 범위 밖
2. `session-start.sh` 본문 전체 Read는 수행하지 않음 — L91 UX 문자열만
   hit. 추가 is_starter 분기가 본문 뒤쪽에 있어도 본 감사의 판정(정당)을
   바꾸지 않음이 확인됨
3. `pre-commit-check.sh` 조건부 regex는 IS_STARTER 값만으로 분기하며
   파일 존재 여부와 독립적. 다운스트림이 우연히 같은 경로 파일을 만드는
   경우는 그 다운스트림의 설계 선택이며 본 감사가 보호할 대상이 아님

## 결정 방향 (실측 반영, 2026-04-22)

실측 결과 12개 파일 중 **오염 1건·조건부 3건·정당 8건**. 대규모 감사 필요 없음 — 타겟 정리 3건으로 끝남.

1. **오염 1건(pre-check promotion-log) 우선 정리**: Top 3의 #1. 독립 커밋 가능
2. **commit audit #4와 자연 연계**: Top 3의 #2는 audit #4(`harness-version-bump.sh` 분리)로 흡수. 별도 작업 불필요
3. **naming.md L97 한 줄 교체**: Top 3의 #3. 독립 커밋 가능
4. **HARNESS.json 필드 재설계 불필요**: `is_starter` 필드 자체는 정당. 추가 구분 축 필요 없음
5. **HARNESS_DEV 일반화 불필요**: 업스트림 전용 pre-push hook 격리용. 다운스트림에 pre-push hook 없으니 무해
6. **문서 전파 필터**: 별도 이슈 — harness-upgrade가 `docs/harness/*.md`·`docs/decisions/*.md` 중 업스트림 전용을 어떻게 배제할지는 설계 여지. 본 감사 결과로는 **다운스트림은 docs/를 덮어쓰지 않음**이 확인돼(본 문서 L105-L108) 전파 필터 긴급도 낮음

## 실행 계획 (실측 반영)

1. ✅ 본 WIP 생성 (2026-04-22)
2. ✅ 파일별 실측 감사 완료 (2026-04-22 codebase-analyst)
3. ✅ 판정 결과 분류표 완성
4. ✅ **Top 3 #1 정리**: `pre-commit-check.sh` promotion-log regex 조건부화 (2026-04-22)
   - `IS_STARTER` 변수 도입 (HARNESS.json에서 `"is_starter": true` grep)
   - L324 `REPEAT_EXEMPT_REGEX`·awk meta 매칭(L413) 둘 다 조건 분기
   - 검증: test-pre-commit 59/59 PASS, downstream 시뮬레이션에서 promotion-log가 doc으로 분류됨 확인
5. ✅ **Top 3 #3 정리**: `naming.md` L97 주석 교체 (2026-04-22)
   - "업스트림 기본값: 생략. 다운스트림은 자기 경로 매핑 추가 권장"으로 교체
6. ✅ **Top 3 #2 정리**: `commit/SKILL.md` Step 3 진입 가드 명시 (2026-04-22)
   - 자연어 조건 → 실행 가능한 grep 판정으로 교체
   - commit audit #4(`harness-version-bump.sh` 스크립트 분리)는 별도 진행. 본 감사 정리로는 조건 명시화로 충분
7. ✅ 본 WIP → `docs/harness/` 이동 + completed (2026-04-22)

## 관련 SSOT

- `hn_generic_contamination_protection.md` — 오염 방지 설계 (본 감사의 사전 작업)
- `hn_downstream_name_leak.md` — 다운스트림 실명 유출 인시던트
- `hn_commit_process_audit.md` — commit 스킬 재검토 (본 감사와 교차 영역)
- `hn_doc_naming.md` — 문서 네이밍 결정
- `hn_upgrade_propagation.md` — 업그레이드 전파 가이드

## 결과

12개 파일 실측 감사 + Top 3 정리(v0.18.8, `d884e68`) 완료. 오염 1건
제거, 조건부 2건 명시화, 조건부 1건(commit/SKILL.md Step 3)은 commit
audit #4의 `harness-version-bump.sh` 분리 시 자연 흡수 예정이나 본 감사
범위 내 조건 명시화는 이번에 처리됨.
