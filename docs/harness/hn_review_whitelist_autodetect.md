---
title: rules → docs 참조 화이트리스트 — 동적 탐색으로 대체
domain: harness
tags: [review, harness-upgrade, whitelist, dead-link, dynamic-resolution]
status: completed
created: 2026-04-20
updated: 2026-04-20
---

# rules → docs 참조 화이트리스트 — 동적 탐색으로 대체

## 당초 문제

v0.9.1 사고: rules/*.md가 `docs/guides`·`docs/decisions`를 본문에서
참조하는데 harness-upgrade가 그 docs를 "사용자 전용"으로 분류해 다운
스트림에 이식하지 않아 dead link 발생. v0.9.2에서 harness-upgrade
SKILL.md에 화이트리스트 목록을 정적으로 추가해 해소.

## 당초 해법(폐기)과 그 한계

원 계획: review 에이전트 또는 pre-commit-check이 rules 본문에 새 docs
참조가 추가됐는데 SKILL.md 화이트리스트에 없으면 **차단**.

재검토 결과 **설계 자체가 거꾸로**였음:

- 정상 논리: rules가 docs를 참조한다 → 그 docs는 rules와 **함께 이식되어야** 동작
- 실제 설계: docs는 기본 제외 + 화이트리스트로 "예외적으로 끼워주는" 수동 관리
- 결과: 기본값이 틀려있어 수동 등록 의무가 필연적으로 드리프트. 차단
  장치를 붙여도 매 참조 추가마다 사람 수작업 강제 → 본질 해결 X

## 채택 해법 — 동적 탐색 + 2단 오탐 방어

harness-upgrade가 Step 3 실행 전 **upstream의 rules 파일** 본문에서
`docs/(guides|decisions)/[a-z0-9_-]+\.md` 패턴을 grep으로 추출하고,
**upstream에 실제 존재하는 파일만** 필터링해 "하네스 파일 범위"에 포함.

```bash
REFERENCED_DOCS=$(
  git show harness-upstream/main -- .claude/rules/ 2>/dev/null \
    | grep -hoE 'docs/(guides|decisions)/[a-z0-9_-]+\.md' \
    | sort -u \
    | while read p; do
        git cat-file -e "harness-upstream/main:$p" 2>/dev/null && echo "$p"
      done
)
```

**SSOT 일원화**: rules 본문이 참조의 유일한 진실. 정적 목록 유지 의무
제거. review·pre-check에 감지 로직 추가 불필요 (원천 해소).

**왜 upstream 기준 grep인가**: harness-upgrade 자체가 upstream을 이식하는
맥락. 다운스트림 rules에는 없는 참조가 upstream에 추가됐을 수 있으므로
기준은 upstream이 맞음.

## 기존 화이트리스트와의 대체 검증

현재 SKILL.md L157-160에 명시된 4개 파일 모두 rules 본문 grep으로 100%
발견됨:

| 대상 docs | 참조하는 rules |
|-----------|---------------|
| `docs/guides/hn_doc_search_protocol.md` | `rules/docs.md` |
| `docs/guides/hn_external_research_patterns.md` | `rules/internal-first.md` |
| `docs/decisions/hn_staging_governance.md` | `rules/staging.md` |
| `docs/decisions/hn_rules_metadata.md` | `rules/security.md`·`internal-first.md`·`no-speculation.md` |

동적 탐색이 수동 목록을 **누락 없이** 대체함을 확인.

## 유지되는 명시적 목록

`docs/guides/project_kickoff_sample.md`는 rules에서 참조되지 않는
sample/template 카테고리. 동적 탐색에서 잡히지 않으므로 **명시적 목록
유지**. 혼합 구조:

- **명시적 목록**: sample/template 류 (rules 무관, 항상 이식)
- **동적 탐색**: rules가 참조하는 docs (항상 자동 발견)

## 오탐 방어

**위험**: rules 본문에 예시·반례로 등장하는 가상 경로(`docs/guides/bad_example.md`
같은 금지 예시)가 grep에 잡히면 "존재하지 않는 파일 이식 시도" 에러 가능.

**방어 2단**:
1. `git cat-file -e "harness-upstream/main:$path"` 체크로 **upstream에
   실제 존재하는 파일만** 통과. 가상 경로는 여기서 자동 탈락.
2. 통과한 경로가 다운스트림에 없으면 정상적 "신규" 이식 제안으로 처리
   (Step 3 "신규" 카테고리).

단순 grep만 하면 "파일 하나 더 이식"이 아니라 에러로 터지므로 위 2단
방어 필수.

## 구현

- `harness-upgrade/SKILL.md` "하네스 파일 범위" 블록: 정적 화이트리스트
  4줄 제거 + "rules 참조 docs 동적 확장" 섹션 신설 + grep 예시 포함
