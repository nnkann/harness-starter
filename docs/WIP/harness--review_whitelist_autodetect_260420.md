---
title: review 에이전트가 rules → docs 참조 화이트리스트 등록 여부 자동 감지
domain: harness
tags: [review, harness-upgrade, whitelist, dead-link]
relates-to:
  - path: harness/promotion-log.md
    rel: references
status: pending
created: 2026-04-20
---

# review 에이전트가 rules → docs 참조 화이트리스트 자동 감지

## 배경

v0.9.1에서 rules/*.md가 docs/guides·docs/decisions를 본문에서 참조하는데
harness-upgrade 스킬이 그 docs 파일을 "사용자 전용"으로 분류해 다운스트림에
이식하지 않아 dead link 발생. v0.9.2에서 SKILL.md에 화이트리스트 목록을
명시 추가해 해소.

**남은 위험**: 앞으로 rules가 새 docs 파일을 참조할 때마다 사람이
SKILL.md 화이트리스트에 등록해야 함. 빼먹으면 같은 dead link 재발.

## 목표

커밋 diff에 rules/*.md의 `docs/(guides|decisions)/*.md` 참조가 추가됐는데
SKILL.md 화이트리스트에 해당 파일이 없으면 review 에이전트가 경고.

## 구현 아이디어

### 감지 로직 (review.md의 패턴 매핑에 추가)

```
패턴: staged diff 중 .claude/rules/*.md에서 + 라인에
  docs/(guides|decisions)/[a-z0-9_-]+\.md 경로가 새로 등장

행동:
  1. 해당 경로들을 추출
  2. .claude/skills/harness-upgrade/SKILL.md Read
  3. "하네스 파일 범위" 섹션에 해당 경로들이 모두 명시됐는지 확인
  4. 누락 있으면 [차단] — "rules에 추가된 docs 참조가 SKILL.md 화이트
     리스트에 없음. 다운스트림 dead link 재발 위험."
```

### 대안: pre-commit-check.sh에서 감지

셸로도 구현 가능. 더 빠르고 결정적. 단점은 review의 자연어 경고 메시지보다
사용자 이해도 낮을 수 있음.

```bash
# rules에서 추가된 docs 참조 추출
ADDED_REFS=$(git diff --cached .claude/rules/*.md \
  | grep -E "^\+.*docs/(guides|decisions)/[a-z0-9_-]+\.md" \
  | grep -oE "docs/(guides|decisions)/[a-z0-9_-]+\.md" \
  | sort -u)

# SKILL.md 화이트리스트와 대조
for ref in $ADDED_REFS; do
  if ! grep -q "$ref" .claude/skills/harness-upgrade/SKILL.md; then
    echo "⚠️ $ref: rules 추가됐으나 harness-upgrade 화이트리스트 누락" >&2
    exit 2
  fi
done
```

## 결정 필요

- review vs pre-check: 어느 쪽에 넣을지 (또는 둘 다)
- 차단 vs 경고: 다운스트림 dead link는 필연 회귀이므로 차단이 안전
- 기존 참조 변경(파일명 변경)도 감지할지 — 추가만 감지하면 rename 누락

## 우선순위

중. rules에서 docs를 참조하는 일이 빈번하지 않지만, 한 번 빼먹으면
전체 다운스트림이 dead link를 겪음. v0.9.2가 이미 한 번 겪었음.
