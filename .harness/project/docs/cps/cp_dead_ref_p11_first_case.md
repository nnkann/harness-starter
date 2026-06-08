---
title: P11 첫 누적 case — dead reference 잠복 (다운스트림 발견 1건 → starter 7건)
domain: cps
c: 다운스트림 StageLink가 harness-upgrade SKILL.md L580 dead reference 1건 보고. starter 본인이 권장 grep 실행 → README 6건 추가 잠복 발견. P11(동형 패턴 잠복) 직격 사례.
tags: [p11, dead-reference, eval-harness, harness-dev, downstream-feedback]
p: [P7, P11]
s: [S5, S6, S9]
result: applied
commit: pending
wave: v0.47.9 dead reference 정비
status: completed
created: 2026-05-16
---

# P11 첫 누적 case — dead reference 잠복

## 발견 경로

1. **다운스트림 1차 발견** (StageLink, 2026-05-16):
   - v0.47.4→v0.47.8 upgrade 후 dead reference 정비 wave 중
   - `harness-upgrade SKILL.md L580` `.claude/rules/anti-defer.md` 1건 발견
   - SKIP 결정 박제 (다운스트림 SKILL.md 수정 시 3-way merge 충돌)
   - upstream FR 보고

2. **starter 2차 탐색** (본 wave):
   - 다운스트림 권장 grep을 starter 본인이 실행
   - **README 6건 추가 잠복 발견**: rules 트리 3건(external-experts·pipeline-design·staging), skills 트리 2건(doc-health·check-existing), self-verify 연계 안내 1건
   - **+L221 staging.md review 단계화 박제 1건** = 총 7건

## P11 본질 실증

> P11: 동형 패턴 잠복 — 1차 발견 시 다른 위치 후보 자동 탐색 부재

**현 흐름의 실패**:
- 73% 삭감 wave에서 `anti-defer.md`·`orchestrator.py` 등 파일 단위 폐기 commit은 정상 완료
- 그러나 파일명을 **본문 예시·트리·안내**로 참조하는 다른 위치 갱신 누락
- 결과: 다운스트림 매 upgrade마다 dead reference 발견 → SKILL.md 본문 수정 불가 → 영구 잠복

**해결 = 결정적 검사 + 절차 의무화**:
- `eval_harness.py:section_dead_reference` 신설 — 폐기 패턴 grep + 박제 표현 면제 정규식
- `harness-dev SKILL.md` "폐기 절차 Step P1~P5" 신설 — 파일 삭제 시 본문 정비 의무화

## 박제 표현 면제 정규식

박제 의도(`폐기·흡수·삭제·removed·deprecated·MIGRATIONS·변경 이력·회고`)는 false positive.
정규식이 라인 단위로 면제 처리 → 결정적 검사가 의도와 일치.

## 다음 wave 후보 (동반 관찰 3건)

다운스트림 보고에 동반된 3건 — 본 wave와 영역 분리, 별 wave로 처리:

1. **AC 헤더 형식 auto-fix 부재** (medium)
   - pre-check이 `## Acceptance Criteria` 거부, `**Acceptance Criteria**:` bold만 인식
   - auto-fix 명령 안내 부재 → 수동 수정 필요
   - 실천: pre-check이 `##` 헤더 발견 시 1줄 sed 명령 안내

2. **docs_ops.py move 라우팅 태그 접두사** (low)
   - `{대상폴더}--` 접두사 없으면 거부 → naming.md "라우팅 태그 폐기" 박제와 표면 모순
   - 실천: frontmatter `domain`으로 자동 추정 + 대화형 확인

3. **WIP move 후 pre-check P#/S# 추출 불가** (low)
   - move 후 pre-check 실행 시 `wip_problem: none` — 추적성 라인 수동 박제 필요
   - 실천: move 직전 pre-check 결과 session-pre-check.txt에 저장, commit_finalize.sh 우선 참조

→ 우선순위 medium 1건 + low 2건. 별 wave 묶음 1건으로 처리 권장.

## 결과

- dead reference 7건 정비 (L580-581 placeholder + README 6건 + L221 review 분기 박제 교체)
- eval_harness 9번째 검사 항목 추가 (test 3건 회귀 보호)
- harness-dev 폐기 절차 5 step 박제
- v0.47.9 박제 commit
