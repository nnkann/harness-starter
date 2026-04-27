---
title: split 성격 기반 그룹화 + commit 흐름 내 diff 참조 최적화
domain: harness
tags: [split, commit, review, diff, task_groups]
relates-to:
  - path: harness/hn_split_commit_review_stage.md
    rel: supersedes
status: completed
created: 2026-04-27
---

# split 성격 기반 그룹화 + commit 흐름 내 diff 참조 최적화

## 사전 준비

- 읽을 문서:
  - `.claude/scripts/task_groups.py` (그룹화 SSOT)
  - `.claude/scripts/pre_commit_check.py` (split 판정·stdout 스키마)
  - `.claude/scripts/split-commit.sh` (그룹 소비)
  - `.claude/skills/commit/SKILL.md` (Step 5.5, diff 전달 섹션)
  - `docs/harness/hn_split_commit_review_stage.md` (sub-커밋 stage 재판정 배경)
- 이전 산출물: 없음

## 목표

- **split 근거 강화**: WIP 없는 파일도 변경 성격(exec/agent-rule/skill/doc)으로 자동 그룹화
- **commit 흐름 내 diff 참조 최적화**: commit 스킬이 diff를 참조하는 모든 지점(Step 6 변경 내역 분석, review 호출)에서 그룹 성격에 따라 전처리해 전달
  - 공통: unified=1 + 노이즈 제거 (`index` 줄, `diff --git` 헤더)
  - exec/agent-rule/skill: 전처리된 full diff
  - doc (docs/**, *.md): stat만 전달 + 필요 시 Read 지시
- **실측 근거**: f35b6c0(4032줄) 기준 37% 감소(4032 → 2513줄) 확인됨

## 설계 원칙

### 그룹별 전달 방식 = review 강도 결정

그룹 성격이 전달 방식을 결정하고, 전달 방식이 review가 할 수 있는 것을 제한한다:

| 그룹 | 전달 방식 | review가 할 수 있는 것 |
|------|----------|----------------------|
| exec/agent-rule/skill | full diff | 줄 단위 패턴 감지, 시크릿·스코프 검증 |
| doc | stat + Read 지시 | 파일 존재·프론트매터 정합성, 선별적 본문 확인 |

모델 선택은 별도 설계 대상이 아님 — 그룹 성격과 전달 방식이 결정되면 자연히 따라오는 것.

### WIP task 계층화 (신규)

기존: WIP task = 그룹 1:1 매핑 → task 내 exec + doc 혼재 시 한 그룹으로 뭉침.

변경: **WIP task를 1차 분류, 성격을 2차 분류**로 계층화.

```
wip:<slug>:<abbr>:<kind>  →  wip:<slug>:<char>:<kind>
                               char = exec | agent-rule | skill | doc | misc
```

같은 WIP task 안의 파일이라도 성격이 다르면 별도 그룹으로 분리된다.

### WIP 없는 파일 허용 (작업 후 문서 패턴)

WIP 없이 작업 후 나중에 문서를 쓰는 패턴을 허용한다.
이 경우 성격 기반 폴백(char:*)이 작동하므로 분리는 정상적으로 이루어진다.
"WIP 없으면 한 그룹" 제약 해소.

## 범위 제한 (건드리지 않는 것)

- pre-check stdout 키 이름 변경 — 최소화 (하위 호환)
- split-commit.sh 파싱 로직 — `char:` prefix 인식 추가 외 변경 없음

## 작업 목록

### 1. task_groups.py + pre_commit_check.py — 성격 기반 분류 + split 조건
> kind: refactor

**사전 준비**:
- 읽을 문서: `.claude/scripts/task_groups.py`, `.claude/scripts/pre_commit_check.py` (split 판정 섹션)
- 이전 산출물: 없음

**현 상태**:
- WIP 매칭 성공 파일 → `wip:<slug>:<abbr>:<kind>` (abbr만 2차 분류, 성격 구분 없음)
- WIP 매칭 실패 파일 → `path:기타:<abbr>:feature` 단일 그룹 폴백 (WIP 없으면 분리 안 됨)
- split 조건: `split_plan >= 2` (그룹 수 기준) — 성격 혼재 여부와 무관

**변경 내용**:

1. **`detect_char()` 추가** — 경로 → 성격 분류:

| char | 경로 패턴 |
|------|----------|
| `exec` | `.claude/scripts/**, .claude/hooks/**` |
| `agent-rule` | `.claude/agents/**, .claude/rules/**` |
| `skill` | `.claude/skills/**` |
| `doc` | `docs/**, *.md` |
| `misc` | 나머지 |

2. **그룹 키 교체**: `<abbr>` → `<char>` (WIP 매칭 성공·실패 모두)
   - 같은 WIP task 안의 파일도 char가 다르면 다른 그룹으로 분리
   - WIP 없는 파일: `char:<type>` 폴백 (성격별 자동 분리)

3. **split 조건 명시** (`pre_commit_check.py`):
   - 성격이 다른 char가 2종 이상 섞이면 → `split_action: split`
   - 단일 char 그룹이면 → `split_action: single` (WIP 수와 무관)

meta 파일 흡수 정책 유지.

**영향 파일**:
- `.claude/scripts/task_groups.py`
- `.claude/scripts/pre_commit_check.py` (split 판정 조건)

**Acceptance Criteria**:
- [x] WIP 없는 staged 파일이 성격별로 분리되는지 수동 테스트 (완료)
- [x] WIP 있는 파일도 task 내 성격 차이로 분리되는지 확인 (완료)
- [x] `python3 -m pytest .claude/scripts/test_pre_commit.py -q` 통과 (완료)
- [x] pre_commit_check.py split 조건 성격 기반으로 교체 + 테스트 통과 (완료)

---

### 2. commit/SKILL.md — diff 참조 전처리 로직 교체
> kind: refactor

**사전 준비**:
- 읽을 문서: `.claude/skills/commit/SKILL.md` diff 전달 섹션
- 이전 산출물: Phase 1 완료

**이득/실**:

| 항목 | 이득 | 실 |
|------|------|-----|
| unified=1 | context 50% 감소, 변경 줄 집중 | enclosing function 경계 일부 손실 |
| doc→stat | 2340줄 → 31줄 (98% 감소) | review Read 호출 추가 (~200줄 추정) |
| 노이즈 제거 | index/diff --git 줄 제거 (~1%) | 없음 |
| 전체 | 4032 → 2513줄 (37% 감소) | doc Read 추가 비용 |

**현 상태**: 줄 수 기준 분기 — "앞 2000줄만" 방식으로 31파일 중 13파일(42%) 누락 실측.

**변경 내용**: 줄 수 기준 → 그룹 성격 기반 분기로 교체. (완료)

**영향 파일**:
- `.claude/skills/commit/SKILL.md`

**Acceptance Criteria**:
- [x] "앞 2000줄만" 방식 제거 (완료)
- [x] 그룹별 분기 명시 (완료)
- [x] 5001줄+ stat 전용 경로 char:doc으로 통합 (완료)

---

## 결정 사항

- task_groups.py: abbr 2차 분류 → char(exec/agent-rule/skill/doc/misc) 2차 분류로 교체
  - WIP 매칭 성공·실패 모두 char 적용. 같은 WIP task 내 성격 다르면 다른 그룹
  - WIP 없는 파일도 char 폴백으로 자동 분리
- pre_commit_check.py: split 조건을 `split_plan >= 2` → 서로 다른 char 2종 이상으로 교체
  - 그룹 정렬도 PRIO 딕셔너리 → CHAR_PRIO(exec:1, agent-rule:2, skill:3, misc:4, doc:9)
- commit/SKILL.md: 줄 수 기준 분기("앞 2000줄만") → 그룹 성격 기반 분기로 교체
  - 공통 전처리: unified=1 + index/diff --git 헤더 제거
  - char:doc → stat만 + Read 지시 (2340줄 → 31줄, 98% 감소)
- 시뮬레이션(f35b6c0, 4032줄): 5그룹 자동 분리 확인, doc stat 대체 시 37% 감소

## 메모

- 실측 배경: f35b6c0(4032줄, 31파일) 기준 현재 "앞 2000줄" 방식으로 31파일 중 13파일(42%) 누락 확인
- PR-Agent 방식 적용 내용:
  - PR-Agent: PR 전체를 청크 분할 + 파일 성격별 컨텍스트 비대칭 부여 (변경 전 more, 변경 후 less) + unified=2 수준
  - 우리 적용: unified=1(PR-Agent보다 한 단계 더 축소) + 파일 경로 기반 성격 분류(exec/agent-rule/skill/doc) + doc 그룹은 stat만 전달
  - PR-Agent와 차이: PR-Agent는 청크당 32k 토큰 + 최대 3회 호출로 대형 PR 처리. 우리는 split으로 커밋 자체를 쪼개므로 청크 분할 불필요 — split이 PR-Agent의 청크 분할 역할을 대신함
- LAURA 논문(arXiv:2512.01356): context lines보다 enclosing function 전체가 유효. unified=1이 절충점
- WIP task 계층화 배경: 같은 task 안에 exec + doc 혼재 시 기존 방식으로는 한 그룹 뭉침 → 성격 2차 분류로 해소
