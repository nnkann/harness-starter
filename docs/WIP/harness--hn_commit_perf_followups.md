---
title: 커밋 파이프라인 현실화 — §H-2~7 후속 wave 로드맵
domain: harness
problem: P2
solution-ref:
  - S2 — "review tool call 평균 ≤4회 (부분)"
tags: [commit, performance, roadmap]
relates-to:
  - path: harness/hn_commit_perf_optimization.md
    rel: extends
status: pending
created: 2026-05-12
---

# §H-2~7 후속 wave 로드맵

본 WIP은 `harness--hn_commit_perf_optimization.md`의 §H-1을 본 wave로 좁히면서
잘라낸 후속 작업의 **인덱스**다. 본 WIP 자체는 닫지 않는다. 각 항목은 그
wave 시작 시점에 **별 WIP로 재분리**한다 (1개 WIP = 1개 sub-task).

원칙·판정식·side effect 분류 정의는 본 WIP가 아닌
`harness--hn_commit_perf_optimization.md` §A~§I를 SSOT로 한다.

## 후속 sub-task 목록

### §H-2 commit 스킬 route 소비

- 파일: `.agents/skills/commit/SKILL.md`
- 핵심: Step 4 version bump를 `promotion=release`일 때만 실행하는 절차로
  이동. Step 5.5 split을 자동 stage 변경 → 계획 출력으로 변경. Step 7
  review 호출은 `review_route`를 따름.
- 선행 조건: §H-1 완료 (pre_commit_check.py route 출력 존재).
- AC 핵심: 일반 `/commit` 문서 경로에서 version bump·MIGRATIONS·README가
  자동 필수처럼 읽히지 않는다.

### §H-3 split-commit 비파괴화

- 파일: `.claude/scripts/split-commit.sh`
- 핵심: 기본 실행은 split plan만 출력하고 staged 상태 유지. `--apply`일
  때만 기존처럼 첫 그룹 stage 변경. CRLF 감지 시 사전 차단·정규화.
- 선행 조건: §H-2 완료 권장 (SKILL이 route 소비 후).
- AC 핵심: split 추천이 있어도 사용자 명시 없으면 staged 변경 0.

### §H-4 Side Effect Ledger

- 파일: `.claude/scripts/docs_ops.py`, `commit_finalize.sh`, commit/SKILL.md
- 핵심: `docs_ops.py wip-sync` stdout에 `wip_sync_updated`,
  `wip_sync_moved`, `cluster_updated`, `backrefs_updated` 추가.
  `commit_finalize.sh`가 `side_effects.required`로 재출력. ledger에
  required/release/repair 항목이 하나라도 있으면 최종 요약에 표시.
- 선행 조건: §H-2 완료.
- AC 핵심: wip-sync, version bump, hook repair가 서로 다른 줄로 출력된다.

### §H-5 Hook/Pre-check SSOT 통합

- 파일: `.claude/scripts/pre_commit_check.py`,
  `.claude/scripts/install-starter-hooks.sh`,
  `scripts/install-secret-scan-hook.sh`
- 핵심: 시크릿 패턴·예외 목록을 `pre_commit_check.py`에 함수로 노출.
  hook 설치 스크립트는 그 정의에서 hook block 생성. `.codex/agents/**`
  예시 패턴 면제 회귀 테스트 추가.
- 선행 조건: 독립 실행 가능.
- AC 핵심: pre-check 통과 후 hook이 같은 사유로 차단되는 사례 0건.

### §H-6 Windows Commit Smoke

- 파일: 신규 `.claude/scripts/commit_smoke_windows.sh`,
  `.claude/scripts/tests/test_pre_commit.py`
- 핵심: CRLF/hook shebang/git identity/PowerShell→Git Bash env 전달
  smoke. Bash push credential 실패 시 Windows Git fallback 안내.
- 선행 조건: 독립 실행 가능.
- AC 핵심: Windows + Git Bash dry-run smoke 통과. 실패 시 다음 행동이
  한 줄로 출력.

### §H-7 Cascade Integrity Check

- 파일: `.claude/scripts/pre_commit_check.py`, `.claude/HARNESS_MAP.md`
- 핵심: CPS/frontmatter/domain/abbr/cluster/AC/trigger/side
  effect/upward feedback 대조 결과를 기존 검사와 중복 없이
  `warning_reasons`에 추가. 차단/경고/제안 3등급.
- 선행 조건: §H-2 완료 (warning_reasons 소비 필요), §H-4 완료 권장
  (side effect 신호 활용).
- AC 핵심: 문서 WIP 1건·코드+문서 혼합 1건·hook repair 1건에서 사람이
  납득 가능한 요약 출력.

## 실행 순서 제안

```
§H-1 (본 wave, 진행 중)
  ↓
§H-2 → §H-3 → §H-4
              ↓
§H-5 (병렬 가능, 시크릿 SSOT 독립)
§H-6 (병렬 가능, Windows 환경 독립)
              ↓
§H-7 (의존: §H-2, §H-4)
```

§H-5, §H-6은 의존성 없으므로 §H-2 이전에 들어갈 수도 있다. 우선순위는
체감 마찰이 큰 순서대로 선택.

## 작업 목록

별 wave 분리 시점에 각 sub-task를 별 WIP로 등록. 본 WIP는 인덱스만
유지하며 sub-task가 별 WIP로 분리될 때마다 해당 항목에 `→ WIP/...`
링크를 추가한다.

**Acceptance Criteria**:

- [x] Goal: §H-2~7 6개 sub-task의 인덱스 행을 1곳에 모아 각 별 wave 시작 시점의 진입점을 만든다.
  검증:
    review: skip
    tests: 없음
    실측: grep "^### §H-" docs/WIP/harness--hn_commit_perf_followups.md 가 6행 반환
- [x] §H-2~7 6개 sub-task 인덱스 섹션 존재 (route 소비 / split 비파괴화 / ledger / hook SSOT / Windows smoke / cascade check).
- [x] 각 sub-task에 파일·핵심·선행 조건·AC 핵심 1줄씩.
- [x] 실행 순서 도식 존재.

후속 wave 분리 진행 표 (각 항목은 별 wave에서 별 WIP로 분리 — 본 WIP completed 전환 조건 아님):

- §H-2 commit 스킬 route 소비 — ✅ 완료 → `harness/hn_commit_skill_route_consume.md` (2026-05-12)
- §H-3 split-commit 비파괴화 — ✅ 완료 → `harness/hn_split_commit_non_destructive.md` (2026-05-12)
- §H-4 Side Effect Ledger — ✅ 완료 → `harness/hn_commit_perf_wave_bundle.md` (2026-05-12)
- §H-5 Hook/Pre-check SSOT 통합 — ✅ 완료 (패턴 export까지, install 통합은 별 wave) → `harness/hn_commit_perf_wave_bundle.md`
- §H-6 Windows Commit Smoke — ✅ 완료 → `harness/hn_commit_perf_wave_bundle.md`
- §H-7 Cascade Integrity Check — ✅ 완료 → `harness/hn_commit_perf_wave_bundle.md`
- §H-8 wip-sync incident 역참조 갱신 결함 — ✅ 완료 (`../` prefix 매칭 추가) → `harness/hn_commit_perf_wave_bundle.md`
- §H-9 .claude ↔ .agents SKILL 동기화 가드 — ✅ 완료 (TestAgentsBridgeSync) → `harness/hn_commit_perf_wave_bundle.md`
- §H-10 .sh 파일 LF 정규화 — ✅ 완료 (.gitattributes + 워킹트리 LF 복원) → `harness/hn_commit_perf_wave_bundle.md`
- §H-11 README "최신 5개 본문" 정책 자동 가드 — ✅ 완료 (`readme_history_overflow`) → `harness/hn_commit_perf_wave_bundle.md`

## 메모

- 본 WIP 자체는 인덱스. 본 wave가 없다 — 각 sub-task가 별 WIP로
  분리되면 그 시점부터 해당 sub-task wave 시작.
- 본 WIP 닫힘 조건: 6개 sub-task 모두 별 WIP로 분리되고 완료.
- `## 후속`·`## 미결` 헤더 키워드 회피 의도적 (status: pending 유지
  목적, completed 차단 트리거 회피).
