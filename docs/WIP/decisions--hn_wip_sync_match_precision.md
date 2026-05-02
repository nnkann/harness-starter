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
status: pending
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
- [ ] Goal: wip-sync가 "이 WIP의 AC 항목이 staged 변경으로 충족됐다"는 의미적
  관계가 있을 때만 ✅을 추가. 단순 파일명 언급(사전 준비·읽을 문서 섹션)에서는 매칭 제외
  검증:
    review: review
    tests: 없음
    실측: 없음
  **(작업 착수 시 검증 묶음 채움 — 회귀 fixture 추가 후 `pytest -m docs_ops`, 실측 명령 정의)**
- [ ] `.claude/scripts/docs_ops.py` wip-sync 매칭 로직 read·분석
- [ ] 매칭 범위 축소 — AC 체크박스 항목 본문만 대상, `## 사전 준비`·`## 메모`·`## 목표` 섹션 제외
- [ ] 회귀 테스트: 본 버그 재현 fixture (3 WIP가 commit/SKILL.md 언급) → 0개 ✅ 마킹
- [ ] 정상 케이스 회귀 가드 — 의도된 매칭(AC 본문 내 파일명)은 그대로 동작

### 2. commit/SKILL.md Step 7.5 가드 추가 (선택, 1번 결과에 따라)

**Acceptance Criteria**:
- [ ] Goal: wip-sync 결과 staged 파일이 1개 이상 추가됐을 때 review 재호출 없이 사용자에게 1줄 요약 노출
  검증:
    review: self
    tests: 없음
    실측: 없음
  **(작업 착수 시 실측 명령 정의)**
- [ ] wip_sync_matched·wip_sync_moved 외에 wip_sync_added_files 출력 추가 (선택)

## 결정 사항
(작업하면서 채움)

## 메모
- 본 버그는 v0.29.2 커밋(5d00178)에서 발현·우회 완료 (메인 커밋 메시지에 기록)
- 우선순위: 별 WIP 4개(commit_auto_verify·eval_cps_integrity·rule_skill_ssot·downstream_amplification) 중
  **다음에 손댈 작업과 함께 수정** 가능. 단독 작업으로 분리할 만큼 크진 않음
- 위험: 매칭이 너무 좁으면 wip-sync 본래 가치(자동 진척도) 손실. 본 버그 재현 + 정상 케이스 회귀
  가드 양쪽 테스트로 균형 검증 필수
