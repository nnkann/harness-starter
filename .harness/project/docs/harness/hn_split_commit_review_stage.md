---

title: split 커밋 sub-group review stage 재판정 — 그룹별 신호 기반 강도 결정
domain: harness
tags: [commit, review, staging, split]
problem: P2
s: [S2]
status: completed
created: 2026-04-25
updated: 2026-04-25
---

# split 커밋 sub-group review stage 재판정

## 배경

split 커밋(`split_action_recommended: split`) 흐름에서 각 sub-커밋이
`HARNESS_SPLIT_SUB=1`로 실행되는데, 현재 pre-check이 sub-커밋에 대해서도
**staged 파일 전체**를 기준으로 stage를 판정한다.

**실측 사례 (2026-04-25)**:
- 그룹 1: `docs/harness/hn_harness_json_cleanup.md` 1개 (문서 이동, S3·S6)
  → pre-check `recommended_stage: standard` ✅ 적절
- 그룹 2: `HARNESS.json`, `doc-finder.md`, `implementation/SKILL.md` (harness critical, S9·S7)
  → pre-check `recommended_stage: deep` ✅ 적절

이번은 그룹별 staged 파일이 달라서 우연히 맞았다. 그러나 **split 전 통합
stage가 deep으로 판정된 경우, 각 sub-커밋에도 deep이 적용**될 수 있는
구조적 위험이 있다. 문서 이동 1개 파일에 deep review가 붙으면 낭비.

**핵심 문제**: sub-커밋은 이미 논리 단위로 분리된 상태이므로, 그 그룹의
파일만 보고 stage를 재판정해야 한다. 현재는 그룹 staged 파일만 남아 있어
실제로는 재판정이 이뤄지지만, 이 동작이 commit/SKILL.md에 **명시적으로
보장돼 있지 않다**.

## 목표

- commit/SKILL.md split 흐름 설명에 "sub-커밋은 그룹 파일만으로 stage 재판정"
  명시
- pre-check이 `HARNESS_SPLIT_SUB=1`일 때 stage 판정 방식이 올바른지 확인
- 필요 시 `staging.md` 또는 `pre_commit_check.py`에 sub-커밋 stage 재판정
  명시 추가

## 작업 목록

### 1. 현재 동작 검증
> kind: chore

**사전 준비**:
- 읽을 문서: `.claude/skills/commit/SKILL.md` (Step 5.5 split 흐름),
  `.claude/scripts/pre_commit_check.py` (HARNESS_SPLIT_SUB 처리 경로)
- 이전 산출물: 없음

**확인 사항**:
- split 흐름에서 첫 그룹만 stage 후 pre-check 재실행 시, staged 파일이
  그룹 파일만인 상태에서 stage 판정이 이뤄지는지
- `HARNESS_SPLIT_SUB=1` 환경변수가 pre-check 내부에서 어떻게 쓰이는지

**영향 파일**: 없음 (읽기만)

**Acceptance Criteria**:
- [x] "sub-커밋 시 staged = 그룹 파일만 → stage 자동 재판정" 동작 확인
- [x] 또는 "동작 안 함 → 수정 필요" 판정

---

### 2. commit/SKILL.md 명시 보강 (작업 1 결과에 따라)
> kind: feature

**사전 준비**:
- 읽을 문서: `.claude/skills/commit/SKILL.md` Step 5.5
- 이전 산출물: 작업 1 결과

**현 상태**: Step 5.5 split 흐름 설명에 sub-커밋의 stage 재판정에 대한
명시가 없음. "sub-커밋은 pre-check 분리 판정 skip, 정상 review·커밋 흐름"
이라고만 돼 있음.

**변경 내용 (작업 1이 "동작 확인"인 경우)**:
Step 5.5에 한 줄 추가:
```
sub-커밋의 recommended_stage는 그룹 staged 파일만으로 재판정된다.
문서 이동 단독 그룹은 standard 이하, harness critical 변경 그룹은 deep.
```

**변경 내용 (작업 1이 "동작 안 함"인 경우)**:
`pre_commit_check.py` 또는 commit/SKILL.md에 명시적 재판정 로직 추가.

**영향 파일**:
- `.claude/skills/commit/SKILL.md` (Step 5.5)
- (필요 시) `.claude/scripts/pre_commit_check.py`

**Acceptance Criteria**:
- [x] commit/SKILL.md Step 5.5에 sub-커밋 stage 재판정 동작 명시됨
- [x] 테스트 통과 (`python3 -m pytest .claude/scripts/test_pre_commit.py -q`) — 51/51 통과

---

## 결정 사항

### 작업 1 검증 결과 (2026-04-25)

**동작 확인**: sub-커밋의 stage 재판정은 구조적으로 이미 올바르게 동작함.

**근거**:
- `pre_commit_check.py` 줄 88: `HARNESS_SPLIT_SUB = os.environ.get("HARNESS_SPLIT_SUB", "0") == "1"`
- 줄 761-763: `HARNESS_SPLIT_SUB=1`이면 `split_action = "sub"` 설정만 하고, stage 판정 로직(줄 683~743)은 그대로 실행됨
- stage 판정은 `staged_files`(= `git diff --cached --name-status` 기반)를 입력으로 함
- `commit/SKILL.md` Step 5.5 split 흐름: `split-commit.sh`가 전체 staged를 비우고 **첫 그룹만 다시 stage**하므로, sub-커밋 실행 시점에 staged = 그룹 파일만
- 따라서 pre-check이 그룹 신호만 감지해 stage를 재판정함 — 구조적으로 보장됨

**실측과 정합**: 2026-04-25 실측 (그룹 1: 문서 1개 → standard, 그룹 2: harness critical → deep)은 추측이 아닌 구조적 동작의 결과였음.

### 작업 2 결과 (2026-04-25)

`commit/SKILL.md` Step 5.5 sub-커밋 설명에 stage 재판정 동작 명시 완료:
- 위치: "sub-커밋은 pre-check 분리 판정 skip, 정상 review·커밋 흐름" 다음 줄
- 내용: 그룹 staged 파일만으로 자동 재판정되는 구조적 근거와 예시 추가

## 메모

- 실측 계기: 2026-04-25 HARNESS.json 정리 커밋에서 split 2그룹 각각 review
  2회 실행. 그룹 1(문서 1개)에 standard, 그룹 2(핵심 설정)에 deep — 우연히
  적절했으나 구조적 보장 없음.
- 관련 incident: `docs/incidents/hn_review_maxturns_verdict_miss.md`
  (review maxTurns 소진 — 과도한 review 예방의 동기와 연결)
- 작업 규모: small. commit/SKILL.md 수정 + 확인 1~2회.
- 실행 순서: 독립. 다른 WIP와 의존성 없음.
