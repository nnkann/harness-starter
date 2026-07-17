---

title: 커밋 프로세스 갭 — 검증 부재·dead code·split 자동화 미완 (2026-04-27)
domain: harness
tags: [commit, split, self-verify, review, dead-code]
problem: P2
s: [S2]
symptom-keywords:
  - split-commit
  - dead code
  - self-verify
  - WIP dead link
  - review 중간 수정
  - 테스트 없이 커밋
status: completed
created: 2026-04-27
updated: 2026-04-27
---

# 커밋 프로세스 갭 — 검증 부재·dead code·split 자동화 미완

## 증상

2026-04-27 세션에서 커밋 진행 중 5개 문제가 연속 발생.
review 단계와 pre-check에서 발견됐으나, 모두 **커밋 호출 이전에 잡혔어야 할** 것들.

## 원인별 상세

### 1. 검증 범위 불일치로 "완료" 선언 (self-verify 위반)

**발생 커밋**: `3a54f9b` (debug-specialist 강화)

`test_pre_commit.py` 54/54 통과를 "검증됐습니다"로 표현했으나,
해당 테스트는 pre-commit 스크립트 로직을 검증하는 것이지
**규칙 텍스트 변경의 효과**(Claude가 에이전트를 실제로 호출하는지)와 무관.

임시 스크립트 `_tmp_verify.py`도 "파일에 텍스트가 존재하는지"만 확인.
자동화할 수 없는 검증을 자동화한 것처럼 포장.

**근본 원인**: "테스트 통과 = 기능 동작 확인"이라는 등식을 검증 없이 적용하는 편향.
이 경우 테스트가 커버하는 것(pre-commit 로직)과 변경한 것(규칙 텍스트)이
완전히 다른 축인데, 그 불일치를 확인하지 않고 통과 = 완료로 단락.

**재발 방지**:
- 자동화 불가한 검증(Claude 행동)이 포함된 경우, 완료 보고 전 사용자에게
  명시적으로 한계를 고지하고 확인을 받는다
- self-verify.md에 강제 조항 추가 필요: "자동화 불가 검증이 있으면
  완료 선언 전 사용자 확인 의무"

---

### 2. 수정 후 테스트 없이 commit 스킬 호출 + AC 스킵

**발생 커밋**: `05a40a2` (split 리팩토링)

`task_groups.py`, `pre_commit_check.py` 수정 완료 후 테스트 실행 없이
바로 `/commit` 호출. review 단계에서 두 가지 문제 발견:
- `detect_abbr` dead code 잔존
- WIP AC 체크박스 미갱신

**근본 원인 1 — AC 스킵**: implementation 스킬 Step 2.5 "Phase 완료 직후 AC 실행"
규칙과 self-verify.md "검증 없이 완료 선언 금지" 두 규칙이 동시에 위반됐다.
commit 스킬을 호출하는 행위 자체가 "이미 완료됐다"는 암묵적 신호로 작동해,
AC 체크 단계가 생략됐다.

**근본 원인 2 — implementation 스킬 미발화**: "WIP 만들자", "문서부터 만들자",
"계획 세우자" 같은 요청에서도 코드 작업이 따라오면 implementation 스킬이
발화됐어야 한다. 스킬이 발화되지 않으면 WIP 생성 → AC 정의 → Phase 완료
검증의 흐름 자체가 없어진다.

**dead code·AC 미체크는 split 흐름과 무관**: split 진행 중이어서 복잡해진 것이지,
두 버그는 수정 직후 테스트·grep으로 잡을 수 있었다. "split 중이어서 어쩔 수
없었다"는 분석은 틀렸다.

**재발 방지**:
- commit 스킬 호출 전 테스트(`pytest`) + 린터 0 + AC 체크박스 확인 필수
- review는 2차 안전망. 1차 검증은 수정 직후 직접 실행
- implementation 스킬 TRIGGER 조건 재검토 — "WIP 생성 요청"도 포함

---

### 3. dead code 잔존 (extract_abbrs, detect_abbr)

**발생 커밋**: 같은 커밋

`abbr` → `char` 교체 시 `extract_abbrs()`, `detect_abbr()` 함수를
`main()`에서 호출 제거했으나 함수 정의는 남겨둠.
review에서 발견 → 커밋 중간 수정.

**근본 원인**: 리팩토링 시 "호출 제거"와 "정의 제거"를 동시에 처리하지 않음.

**재발 방지**:
- 함수 호출을 제거할 때 정의도 함께 제거 + LSP "find references"로 잔재 확인
- grep은 텍스트 매칭만 하므로 "실제로 호출되는가", "어디서 import되는가" 같은
  의미 단위 분석을 못 잡는다. LSP가 dead code·미사용 import·타입 불일치를
  더 정확하게 감지하므로 리팩토링 후 LSP 검증이 1차 수단이어야 함
- grep은 LSP가 커버 못하는 패턴(문자열 내 참조 등) 보완용

---

### 4. WIP 이동 시 역참조 dead link 생성

**발생 커밋**: 같은 커밋

`hn_split_diff_delivery.md`를 WIP → harness/로 이동할 때
`hn_split_commit_review_stage.md`의 `relates-to` 경로
(`WIP/harness--hn_split_diff_delivery.md`)를 갱신하지 않음.
pre-check dead link 감지 → 차단 → 수정 → 재스테이징.

**근본 원인**: WIP 이동 시 역참조 링크 갱신이 commit 스킬 AC에 없음.
`docs_ops.py move`가 역참조 자동 갱신을 지원하지만 이 케이스에서 미동작 또는
호출 누락 — 확인 필요.

**재발 방지**:
- WIP completed 전환은 무조건 역참조 dead link 검사를 AC로 포함해야 함
  ```bash
  grep -r "파일명" docs/  # 역참조 확인
  ```
- `docs_ops.py move`의 역참조 자동 갱신 동작 여부 확인 후,
  미동작이면 수정 (별도 작업)
- commit 스킬 WIP 이동 단계에 "역참조 검사" AC 명시 추가 필요

---

### 5. split-commit.sh 그룹2/3 자동 stage 미동작

**발생**: `05a40a2` 그룹1 커밋 후 그룹2 진행 시

그룹1 커밋 후 `split-commit.sh` 재실행 시 staged가 비어있어
"분리 불필요(single)" 판정. 수동으로 파일을 stage해서 진행.

**원인**: `split-commit.sh`가 두 번째 실행 시 `.claude/memory/split-plan.txt`에서
남은 그룹을 읽어 자동 stage하는 로직이 없음.
재실행 시 pre-check을 다시 호출해 그룹을 재계산하는데,
staged가 비어있으면 그룹이 없어 single 판정.

**재발 방지 (코드 수정 필요)**:
`split-commit.sh` 진입 시 다음 로직 추가:
1. `.claude/memory/split-plan.txt` 존재 여부 확인
2. 있으면 → 다음 그룹 파일 읽어서 `git add`
3. 없으면 → 기존 pre-check 재계산 경로

`split-plan.txt`는 이미 `.claude/memory/split-plan.txt`에 저장되고 있음.
파일을 읽는 로직만 추가하면 됨.

## 공통 패턴

5개 중 3개(1·2·3)가 **"커밋 전 자기 검증 생략"** 패턴.
commit 스킬이 review를 통해 잡아주길 기대하는 구조가 반복됨.

```
[잘못된 흐름] 수정 → commit 호출 → review에서 발견 → 수정
[올바른 흐름] 수정 → 테스트/린터 → AC 직접 확인 → commit 호출 → review는 2차
```

## 구현 이력

### A. split-commit.sh — split-plan.txt 기반 자동 stage
> kind: bug

**영향 파일**: `.claude/scripts/split-commit.sh`

**변경 내용**: 진입 시 `.claude/memory/split-plan.txt` 존재 확인.
있으면 다음 그룹 파일 읽어서 `git add` 후 pre-check 재계산 없이 진행.
없으면 기존 경로(pre-check 재계산).

**Acceptance Criteria**:
- [x] 그룹1 커밋 후 split-commit.sh 재실행 시 그룹2 자동 stage 확인 (split-plan.txt 기반 로직 추가)
- [x] `python3 -m pytest .claude/scripts/test_pre_commit.py -q` 통과 (54/54)

---

### B. self-verify.md — 자동화 불가 검증 강제 조항
> kind: docs

**영향 파일**: `.claude/rules/self-verify.md`

**변경 내용**: "자동화 불가 검증(Claude 행동)이 포함된 경우,
완료 선언 전 사용자 확인 의무" 조항 추가.

**Acceptance Criteria**:
- [x] self-verify.md에 조항 존재 확인 (완료)

---

### C. commit/SKILL.md — WIP 이동 시 docs_ops.py move 사용 강제
> kind: docs

**영향 파일**: `.claude/skills/commit/SKILL.md`

**변경 내용**: Step 2 WIP 이동 단계에 "반드시 `docs_ops.py move` 사용"
명시. `git mv` 직접 사용 금지 — 역참조 자동 갱신이 누락됨.

**Acceptance Criteria**:
- [x] commit/SKILL.md Step 2에 docs_ops.py move 강제 명시 확인 (완료)

---

## 메모

- D 작업 확인 완료: `docs_ops.py move`는 `_rewrite_relates_to()`로 역참조 자동
  갱신을 이미 지원함. 이번 dead link 사고 원인은 `docs_ops.py move` 미사용이고
  `git mv` 직접 실행이 문제. 코드 수정 불필요 — 사용 방법 교정만 필요.
- 문제 1·2는 하네스 규칙에 이미 있는 내용이나 실제 동작에서 반복됨
  → 규칙 강화와 함께 implementation 스킬 TRIGGER 조건 재검토 필요
