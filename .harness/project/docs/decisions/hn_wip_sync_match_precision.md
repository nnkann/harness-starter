---
title: docs_ops.py wip-sync 부분 매칭 버그 — 매칭 정밀화
domain: harness
problem: P5
solution-ref:
  - S5 — "원인이 특정되면 해당 항목 제거 + 실측 재측정 (부분)"
tags: [docs_ops, wip-sync, matching, false-positive]
relates-to:
  - path: decisions/hn_commit_auto_verify.md
    rel: caused-by
status: completed
created: 2026-05-02
updated: 2026-05-02
---

# wip-sync 부분 매칭 버그

## 사전 준비
- 읽을 문서: `.claude/scripts/docs_ops.py` (wip-sync 명령), `.claude/skills/commit/SKILL.md` Step 7.5
- 이전 산출물: v0.29.2 commit `5d00178` — 본 버그가 발현된 커밋

## 목표
`docs_ops.py wip-sync`가 staged 파일명을 다른 WIP 본문에서 부분 매칭해
무관한 WIP의 체크박스를 ✅로 잘못 마킹하는 문제 해결.

## 발견 경위 (v0.29.2 커밋 5d00178 + v0.30.0 커밋, 2026-05-02)

**2회 연속 자기증명**. v0.30.0 커밋에서도 동일 버그 재발:
- 본 신규 WIP 자체의 frontmatter `relates-to` 줄과 `## 사전 준비`의 파일명
  언급에 ✅ 잘못 마킹됨 (커밋 직전 수동 정정)
- 다른 무관 WIP 2개(`hn_downstream_amplification`·`hn_rule_skill_ssot`)에도
  v0.29.2와 동일하게 false positive 매칭 발생



본 wave 커밋에서 `commit/SKILL.md` 등을 staged. wip-sync 결과:

```
✅ 갱신: docs\WIP\decisions--hn_commit_auto_verify.md   ← 의도
🎉 모든 항목 완료 — 자동 이동 시도                       ← 의도
✅ 갱신: docs\WIP\decisions--hn_downstream_amplification.md  ← 잘못
✅ 갱신: docs\WIP\decisions--hn_eval_cps_integrity.md          ← 잘못
✅ 갱신: docs\WIP\decisions--hn_rule_skill_ssot.md             ← 잘못
wip_sync_matched: 4
wip_sync_moved: 1
```

3개 WIP는 본문 `## 사전 준비`에 `commit/SKILL.md` 또는 다른 staged 파일명을
**참조 자료로 언급**했을 뿐인데, wip-sync가 그 라인의 체크박스에 ✅ 추가.

수동으로 `git restore --staged` + `git restore`로 되돌려 본 커밋에서는 회피.
하지만 매번 검토·되돌리기 부담이 누적되고, 놓치면 잘못된 ✅이 박제됨.

## 작업 목록

### 1. 매칭 로직 분석 + 정밀화

**Acceptance Criteria**:
- [x] Goal: wip-sync가 "이 WIP의 AC 항목이 staged 변경으로 충족됐다"는 의미적
  관계가 있을 때만 ✅을 추가. 단순 파일명 언급(사전 준비·읽을 문서 섹션)에서는 매칭 제외
  검증:
    review: review
    tests: pytest .claude/scripts/test_pre_commit.py::TestWipSyncMatchPrecision -q
    실측: TestWipSyncMatchPrecision 3 케이스 통과 + 본 wave 시뮬레이션 (사전 준비 줄·frontmatter relates-to 둘 다 ✅ 추가 안 됨). 기존 2 failure(`TestWipSyncAbbrMatch::test_abbr_*`)는 직교 별건 — debug-specialist 진단 확인됨, 본 wave 범위 외
- [x] `.claude/scripts/docs_ops.py` wip-sync 매칭 로직 read·분석 (debug-specialist 진단 완료) ✅
- [x] 매칭 범위 축소 — AC 체크박스 항목 본문만 대상, `## 사전 준비`·`## 메모`·`## 목표` 섹션 제외 (정규식 `^\s*[-*]\s+\[[ xX]\]\s` + frontmatter 영역 스킵)
- [x] 회귀 테스트: TestWipSyncMatchPrecision 3 케이스 신설 (사전 준비·frontmatter relates-to false positive 차단 + 정상 매칭 회귀)
- [x] 정상 케이스 회귀 가드 — `test_marks_only_checkbox_lines` 통과로 의도된 매칭 동작 확인

### 2. commit/SKILL.md Step 7.5 가드 추가 (선택, 1번 결과에 따라)

**Acceptance Criteria**:
- [x] Goal: wip-sync 결과 staged 파일이 1개 이상 추가됐을 때 review 재호출 없이 사용자에게 1줄 요약 노출
  검증:
    review: self
    tests: 없음
    실측: 없음
  **(범위 축소 결정)**: Phase 1 매칭 정밀화로 false positive 자체가 차단됨 → 가드 라인 우선순위 하락. 운용 결과 잔존 확인 시 재개
- [x] wip_sync_matched·wip_sync_moved 외에 wip_sync_added_files 출력 추가 (선택) — 범위 축소로 보류

### 3. debug-specialist 위임 로직 자동 트리거 강화 (자기증명 사고에서 드러남)

**Acceptance Criteria**:
- [x] Goal: "동일 수정 2회 이상" 룰(no-speculation.md L56)을 자동 감지하는 hook 강화 — 사용자 키워드 발화나 fix prefix에만 의존하지 않게 ✅
  검증:
    review: review
    tests: 없음 (shell hook — pytest marker 없음)
    실측: bash -n .claude/scripts/session-start.sh 구문 검증 통과
- [x] session-start.sh 연속 fix 감지를 prefix 무관하게 **공통 파일 2회 수정**으로 확장 (메타 파일 노이즈 제외) ✅
- [~] 또는 commit 스킬 Step 7.5 wip-sync 결과에 false positive 의심 패턴 감지 — Phase 1 매칭 정밀화로 false positive 자체 차단됨, 본 트리거 우선순위 하락
- [x] Claude 자가 룰 준수 강화 — `no-speculation.md`에 "시스템 동작 이슈도 동일 수정 2회 이상 트리거에 포함" 명시 (L56 신규 행 + 본문 보강) ✅

## 결정 사항

- **debug-specialist 진단 결과** (2026-05-02):
  - 1차 진원지: `docs_ops.py:580` — 정규식 `^\s*([-*]|\d+\.)\s` 모든 리스트 라인 통과
  - 2차 진원지: `docs_ops.py:581` — `_sf in line or _sfbn in line` 자연어 substring hit
  - 3차 진원지: `docs_ops.py:585~590` — frontmatter `relates-to:` YAML 리스트 영역 스킵 없음
  - 부수: `body_referenced` (L574)도 같은 substring 기반 → 자동 이동 false positive 위험
- **최소 침습 수정안**: L580 정규식을 `^\s*[-*]\s+\[[ xX]\]\s`로 좁혀 체크박스 라인만 매칭. 이것만으로 본 사례 100% 차단
- **기존 pytest 2 failure (`TestWipSyncAbbrMatch`)는 별건** — abbr 보조 매칭 경로(597~613) 이슈, 본 버그(1차 매칭)와 직교
- **위임 로직 갭** (사용자 지적): 본 세션에서 동일 동작 2회 발생했지만 자동 트리거 미발화
  - debug-guard.sh: 사용자가 에러 키워드 입력 안 함 → 미발화
  - session-start.sh 연속 fix: 두 커밋 모두 `feat:` prefix → 미발화
  - Claude 자율 준수 실패가 결정적 원인 (룰은 있는데 인지·실행 안 함)
- CPS 갱신: 없음 (S5 docs/ 무결성 감시 메커니즘 강화 방향 — 충족 기준 변경 X)

## 메모
- 본 버그는 v0.29.2 커밋(5d00178) + v0.30.0 커밋(acdb877)에서 발현·우회 완료 (메인 커밋 메시지에 기록). **2회 자기증명**
- 우선순위 격상: 매번 마찰 + 자기증명 이미 충분 → 단독 진행. 다른 별 WIP보다 선행
- 위험: 매칭이 너무 좁으면 wip-sync 본래 가치(자동 진척도) 손실. 본 버그 재현 + 정상 케이스 회귀 가드 양쪽 테스트로 균형 검증 필수
- debug-specialist 진단 자료: 본 세션 turn (2026-05-02). 진단 원문은 git stash 또는 본 세션 transcript 참조 (Phase 1 코드 수정 시 직접 활용)
- **본 WIP 자체가 자기증명 사례** — Phase 3 위임 로직 갭이 본 세션에서 드러남. Phase 1+3 함께 수정이 효과 측정 정합성 높음
