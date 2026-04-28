---
title: docs_ops.py move 시 relates-to 역참조 자동 갱신
domain: harness
tags: [docs-ops, relates-to, dead-link, move]
status: completed
created: 2026-04-25
updated: 2026-04-25
---

# docs_ops.py move 시 relates-to 역참조 자동 갱신

## 배경

**실측 계기 (2026-04-25)**: WIP 두 개가 `harness/`로 이동 완료된 후,
다른 문서의 `relates-to`가 이동 전 WIP 경로를 그대로 참조해 dead link가
발생했다. pre-check의 dead link 감지가 커밋 시점에 차단했지만, 이동 직후
즉시 수정되지 않아 다운스트림 이슈로 보고됨.

발생한 dead link:
- `docs/harness/hn_harness_json_cleanup.md` → `WIP/harness--hn_phase_agent_improvements.md` (이동 전 경로)
- `docs/harness/hn_debug_specialist.md` → `WIP/harness--hn_phase_agent_improvements.md` (이동 전 경로)

**구조적 원인**: `docs_ops.py move`가 파일을 이동할 때 **역참조**(다른
문서의 `relates-to`에서 이 파일을 가리키는 포인터)를 갱신하지 않는다.
이동된 파일의 `relates-to`는 수동으로 수정 가능하지만, 이 파일을 참조하는
**다른 문서**의 경로는 자동으로 추적되지 않는다.

## 목표

`docs_ops.py move <파일>` 실행 시:
1. 전체 `docs/**/*.md`에서 이동 전 경로를 `relates-to.path`로 참조하는 문서를 찾는다
2. 해당 문서의 `relates-to.path`를 이동 후 경로로 자동 갱신한다
3. 갱신된 파일을 `git add`한다

## 사전 준비
- 읽을 문서: `.claude/scripts/docs_ops.py` (move 커맨드 구현 위치 파악)
- 이전 산출물: 없음

## 작업 목록

### 1. docs_ops.py move에 역참조 갱신 로직 추가
> kind: feature

**현 상태**: `cmd_move()` 함수가 파일 이동 + status 갱신 + cluster-update만 수행.
역참조 갱신 없음.

**변경 내용**: `cmd_move()` 완료 후 다음 단계 추가.

```python
def rewrite_relates_to(old_rel_path: str, new_rel_path: str) -> list[str]:
    """
    docs/**/*.md 전체에서 relates-to.path가 old_rel_path인 항목을
    new_rel_path로 갱신. 갱신된 파일 경로 목록 반환.
    
    경로 형식: docs/ 기준 상대경로 (예: "WIP/harness--hn_foo.md")
    """
```

탐색 범위: `docs/**/*.md` (이동된 파일 자신 제외)
매칭 조건: frontmatter `relates-to` 블록 내 `path:` 값이 old_rel_path와 일치
갱신 후: `git add <갱신된 파일>` 자동 실행
stdout: `relates_to_rewritten: N개 파일` 출력

**영향 파일**:
- `.claude/scripts/docs_ops.py` (cmd_move 함수 + rewrite_relates_to 신규 함수)

**Acceptance Criteria**:
- [x] `python3 .claude/scripts/docs_ops.py move <WIP파일>` 실행 시 역참조 갱신됨
- [x] 갱신된 파일 수가 stdout에 출력됨 (`relates_to_rewritten: N`)
- [x] 역참조 없으면 변경 없음 (`relates_to_rewritten: 0`)
- [x] `python3 -m pytest .claude/scripts/test_pre_commit.py -q` 51/51 통과

---

### 2. 테스트 케이스 추가 (선택)
> kind: feature

역참조 갱신 동작을 검증하는 테스트. `test_pre_commit.py`가 아닌
`docs_ops.py` 자체 테스트로 추가하거나, 기존 테스트 스위트 확장.

현재 `test_pre_commit.py`는 pre-commit 로직만 다루므로, 별도 테스트
파일(`test_docs_ops.py`) 신설 또는 수동 검증으로 대체 가능.

**Acceptance Criteria**:
- [ ] 역참조 갱신 동작 검증 방법 확정 (자동 테스트 또는 수동 시나리오)

---

## 결정 사항

(작업하면서 채움)

## 메모

- 실측: 2026-04-25 `hn_harness_json_cleanup.md`·`hn_debug_specialist.md` 두 건.
  다운스트림에서 보고됨. pre-check dead link 차단으로 커밋은 막혔으나 수동 수정 필요.
- 경로 형식 주의: `relates-to.path`는 `docs/` 기준 상대경로 (`harness/foo.md`).
  move 시 old = `WIP/harness--foo.md`, new = `harness/foo.md`.
- 탐색 범위: `docs/**/*.md` 전체. 파일 수가 많아도 grep 기반이므로 빠름.
- 작업 규모: small. `docs_ops.py` 1개 함수 추가 (~30줄).
