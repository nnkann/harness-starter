---
title: commit Step 2 후속 — write-doc symptom-keywords 재질의 + completed 미결 차단 자동화
domain: harness
tags: [commit, write-doc, completion-gate]
relates-to:
  - path: ../harness/search_and_completion_gaps_260418.md
    rel: extends
status: pending
created: 2026-04-19
---

# commit Step 2 후속

원본 WIP `harness--search_and_completion_gaps_260418.md`의 Part A 후속 항목.

## 잔여 작업

1. **write-doc 스킬: incident 생성 시 `symptom-keywords` 재질의**
   - 현재 docs.md 규칙에는 명시됐지만 write-doc 스킬이 자동 강제 안 함
   - 사용자가 incident 생성 시 symptom-keywords 누락하면 스킬이 묻기

2. **commit 스킬: completed 전환 시 본문 미결 패턴 차단 자동화**
   - 2026-04-19 v1.6.x에서 Step 2를 재설계하면서 차단 조건이 SKILL.md에
     명시됨 (TODO/FIXME/후속/미결/미결정/추후/나중에/별도로)
   - 그러나 실제 키워드 검사 로직은 docs-manager 스킬이 수행해야 함
   - docs-manager Step 2(문서 이동)에 차단 검사 추가 필요

## 우선순위

P2. 둘 다 안전성 강화 — 현재 사람이 신경 쓰면 동작은 함.

## 검증

- write-doc으로 incident 생성 시 symptom-keywords 없으면 묻는지
- WIP에 "TODO" 남긴 채 commit Step 2가 [c] completed로 전환 시도 시 차단되는지
