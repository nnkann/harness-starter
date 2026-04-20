---
title: memory 재설계 — tmp 폐기 + 동적 snapshot 도입 + 트리거 재정의
domain: harness
tags: [memory, snapshot, ssot, simplification, trigger]
relates-to:
  - path: harness/harness_simplification_260419.md
    rel: extends
  - path: harness/index_md_removal_260420.md
    rel: extends
status: completed
created: 2026-04-20
updated: 2026-04-21
---

# memory 재설계

## 배경

### 현황 진단

**`.claude/memory/` 실태** (2026-04-20 기준):
- `MEMORY.md` 인덱스 + `feedback_eval_secret_scan.md` 단 1개 항목
- 이번 세션 내내 **단 한 번도 참조 안 됨** — 정당한 skip (관련 작업 없었음)
- 사용자 지적: "지금 메모리가 사용법이 유명무실한데"

**`.claude/tmp/` 실태**:
- `staged-diff.txt` 1개 (9.7KB, Claude가 디버깅 중 만든 잔재)
- 생성 코드는 코드베이스 어디에도 없음 — 세션 중 수동 실행 후 정리 안 된 것
- `.gitignore`에 등록되어 있지만 폴더 자체의 존재 이유 불명

**문제의 본질**:
1. 현재 `rules/memory.md`가 "정적 feedback 저장"만 다룸. 동적 snapshot·세션 간 컨텍스트 전달·에이전트 호출 prompt 조립 재료 기능이 설계 자체에 없음
2. "현재 세션에서만 유효한 임시 정보 → 저장 금지" 규칙이 동적 snapshot을 원천 차단
3. 트리거 부재 → Claude가 자율 판단에 의존 → 판단 미발생 → 영원히 비어있음
4. tmp는 개념 불명 폴더로 전락. Claude가 수시로 잔재 생성

### 외부 조사 결과 요약

researcher 조사(`docs/harness/external_experts.md`에 Charles Packer 등록):
- **Anthropic Auto Memory 공식**: MEMORY.md 인덱스 세션 시작 자동 로드, 토픽 파일은 on-demand
- **Letta (MemGPT 창안자)**: Core/Recall/Archival 3계층 — 우리 규모엔 과함
- **Devin**: "writes its own notes across sessions" — 작업 중 snapshot 패턴
- **Letta sleep-time compute**: 세션 종료 전 memory 정제 트리거가 자연스러움

우리 프로젝트에 **차용**: "세션 시작 읽기 + 세션 종료 정제" 트리거 + "동적 snapshot" 개념.
**기각**: MemGPT 3계층 분리 (규모 과함).

## 선택지

### A. 현 구조 유지 + tmp만 정리

- 장점: 변경 최소
- 단점: 근본 문제(트리거 부재·동적 snapshot 지원 부재) 미해결. memory는 계속 유명무실

### B. 계층형 메모리 전면 도입 (MemGPT식)

- 장점: 업계 최신 패턴 반영
- 단점: 우리 규모에 과함. 파일 수 폭증. 관리 부담 역증가

### C. **채택** — 최소 설계로 4용도 모두 대응

- tmp 폐기 + `.claude/memory/`로 흡수 (폴더 분리 없이 flat, `session-` 접두사로 구분)
- 트리거 3개만 확정 구현
- 동적 snapshot은 파일 3개 flat으로 제한
- commit 스킬 수정 최소 (12줄 이하)

## 결정

### 실제 Claude memory vs 프로젝트 memory 경계

**실제 Claude 메모리 (Anthropic 관리, 사용자 머신 로컬)**:
- Claude Code의 auto memory 시스템이 자율 관리
- 저장 대상: 이 사용자·이 Claude 세션 페어에만 의미 있는 것
  - 사용자 성향·선호 (예: 근본 해결 선호, 비유 선호)
  - Claude 실수 패턴
- **프로젝트 repo에 저장 X**

**프로젝트 memory (`.claude/memory/`, git 추적)**:
- 조건: **다른 사람·다른 Claude 세션이 읽어야 의미 있음**
- 저장 대상:
  - 프로젝트 관행 (예: "eval --deep은 archive도 검사" — 이미 있음)
  - 다운스트림이 상속받아야 할 hard-won lessons
- **사용자 개인 성향은 여기에 저장 X**

### 4가지 용도와 대응

사용자 정의 4용도:
1. **작업 중 동적 snapshot** — commit 사이사이 staged diff·상태 저장
2. **세션 간 컨텍스트 전달** — 지난 세션 결정을 다음 세션이 즉시 알게
3. **스킬/에이전트 호출 prompt 조립 재료** — 매번 재조립 대신 memory 참조
4. **정적 feedback 학습** — 우선순위 최저

매핑:
| 용도 | 대응 |
|------|------|
| (1) 동적 snapshot | `.claude/memory/session-*.txt` 3개 파일 (gitignore) |
| (2) 세션 간 컨텍스트 | `MEMORY.md` 인덱스 자동 로드 (세션 시작 hook 이미 구현) |
| (3) prompt 조립 재료 | commit 스킬이 session-* 파일 경로를 review/test-strategist prompt에 전달 |
| (4) 정적 feedback | 기존 `feedback_*.md` 유지 |

### 트리거 3개 (확정)

8개 제안 중 실제 구현은 3개. 나머지는 과잉 설계로 판단.

| 시점 | 동작 | 구현 위치 |
|------|------|----------|
| **세션 시작** | `MEMORY.md` 자동 로드 (이미 Claude Code 기본 동작) | (구현 이미 존재, 변경 없음) |
| **사용자 "기억해" 명시** | 요청 내용 즉시 저장 | Claude 행동 (rules/memory.md에 명시) |
| **세션 종료 직전** | "저장할 것 있나?" 환기 1줄 출력 | `stop-guard.sh` |

**자동 저장 강제 안 함**. 환기만. 사용자가 /clear 전에 눈으로 판단 가능.

### 동적 snapshot 설계

**목적**: commit → review → (실패 시) 재commit 사이클에서 diff·pre-check 결과 재사용.

**위치**: `.claude/memory/` 루트 (폴더 분리 없음). 파일명 `session-` 접두사로 세션 전용 표시.

**파일 3개 (확장 금지)**:

| 파일 | 내용 | write 시점 | read 시점 |
|------|------|-----------|-----------|
| `session-staged-diff.txt` | `git diff --cached` 결과 | commit Step 5 직전 | Step 6·7에서 Bash 재실행 대신 Read |
| `session-pre-check.txt` | pre-check stdout 14 keys | Step 5 직후 | Step 7 review prompt 조립 |
| `session-tree-hash.txt` | `git write-tree` 결과 | Step 5 직전 | 재호출 시 "staged 같은가?" 판정 |

**tree-hash 기반 캐시 유효성 판정** (핵심):

```bash
CURRENT_TREE=$(git write-tree)
if [ -f .claude/memory/session-tree-hash.txt ] \
   && [ "$CURRENT_TREE" = "$(cat .claude/memory/session-tree-hash.txt)" ]; then
  # 재사용 가능 — diff·pre-check Read
else
  # 폐기 후 재생성
  rm -f .claude/memory/session-*.txt
  git diff --cached > .claude/memory/session-staged-diff.txt
  bash .claude/scripts/pre-commit-check.sh > .claude/memory/session-pre-check.txt
  echo "$CURRENT_TREE" > .claude/memory/session-tree-hash.txt
fi
```

**라이프사이클**:
- commit 성공 → post-commit에서 `rm -f .claude/memory/session-*.txt`
- commit 실패 → 유지. 재시도 시 tree-hash 일치하면 재사용

**효용 추정**:
- 재시도 시나리오 (이번 세션 3회 발생): 재시도당 ~100~200ms 절감
- 일반 커밋: git 호출 수 감소로 ~100ms 절감
- test-strategist 병렬 호출 시 두 Agent가 같은 파일 경로 공유 → prompt 토큰 절반

### 오염·stale 방어

- tree-hash 불일치 = 즉시 폐기 후 재생성. stale 원천 차단
- `.claude/memory/session-*` 전부 `.gitignore` (개인 세션 작업 상태)
- `.claude/tmp/` 폐기 + `bash-guard.sh`에 `.claude/tmp/` 생성 차단 hook — 잔재 재발 영구 방지

## 구체 작업 목록

### 1. tmp 폐기
- [x] `.claude/tmp/staged-diff.txt` 삭제 ✅
- [x] `.claude/tmp/` 폴더 제거 ✅
- [x] `.gitignore`에서 `.claude/tmp/` 제거, `.claude/memory/session-*` 추가 ✅
- [x] `bash-guard.sh`에 `.claude/tmp/` 명령 사용 차단 hook 추가 ✅

### 2. rules/memory.md 재작성 ✅ (커밋 1)
제약 전부 충족:
- "실제 Claude 메모리 vs 프로젝트 memory" 경계 명시 ✅
- 중복 금지 규칙 (git log·promotion-log·CLAUDE.md·rules에 있으면 저장 X) ✅
- 3트리거 (세션 시작 읽기 / "기억해" / 세션 종료 환기) ✅
- "세션 임시 정보 저장 금지" 규칙 삭제 ✅
- 동적 snapshot 3파일 용도·수명 명시 ✅

### 3. commit 스킬 Step 5 수정 ✅ (커밋 2)
12줄 블록 삽입 완료. 기존 로직 불변.

```bash
# Step 5 진입 직후 삽입 (12줄)
CURRENT_TREE=$(git write-tree)
HASH_FILE=".claude/memory/session-tree-hash.txt"
if [ -f "$HASH_FILE" ] && [ "$CURRENT_TREE" = "$(cat $HASH_FILE)" ]; then
  PRE_CHECK_OUTPUT=$(cat .claude/memory/session-pre-check.txt)
else
  rm -f .claude/memory/session-*.txt
  git diff --cached > .claude/memory/session-staged-diff.txt
  PRE_CHECK_OUTPUT=$(bash .claude/scripts/pre-commit-check.sh \
    | tee .claude/memory/session-pre-check.txt)
  echo "$CURRENT_TREE" > "$HASH_FILE"
fi
```

Step 6·7의 `git diff --cached` 호출은 `Read .claude/memory/session-staged-diff.txt`로 교체.

### 4. post-commit 정리 ✅ (커밋 2)
commit 스킬 "푸시" 섹션 뒤 "세션 snapshot 정리" 소섹션 신설. `rm -f
.claude/memory/session-*.txt` 1줄.

### 5. stop-guard.sh 환기 1줄 ✅ (커밋 1)
```bash
# Stop hook 끝에 추가
if [ -d ".claude/memory" ]; then
  echo "💭 이번 세션에서 memory에 저장할 feedback·project 있나? (/clear 전 확인)" >&2
fi
```

### 6. external-experts.md 갱신 ✅ (커밋 1)
"LLM 에이전트 메모리 아키텍처" 카테고리 신설 + Charles Packer 등록.

### 7. 회귀 테스트 ✅ (커밋 2)
`test-pre-commit.sh` T20 추가 (3 케이스: tree-hash 동일성·민감성·snapshot
생성). 전체 33/33 PASS. 성능 T19 1321ms (≤2500ms 방어선).

## 하지 않을 것 (범위 고정)

- **MemGPT식 Core/Recall/Archival 계층 분리** — 우리 규모에 과함
- **implementation 스킬 자동 발화 트리거** — 사용자 명시 제약
- **commit 스킬 대대적 수정** — 12줄 이하 추가만
- **session-*.txt 파일 3개 초과 확장** — 다른 용도 생기면 이 문서 수정 후 재합의
- **`.claude/memory/session/` 하위 폴더 신설** — flat 구조 유지
- **세션 중 중간 상태 자동 저장** — 현재 snapshot 3개 외 추가 금지

## 실행 순서 (다음 세션)

```
커밋 1 (필수):
  - tmp 폐기 + gitignore 수정 + bash-guard 차단 hook
  - rules/memory.md 재작성
  - stop-guard.sh 환기
  - external-experts.md Charles Packer

커밋 2 (선택 — 분리 가능):
  - commit 스킬 Step 5 tree-hash 캐시 로직
  - test-pre-commit.sh T20 추가

분리 이유: 커밋 1은 동적 snapshot과 독립. 커밋 2는 실제 캐싱 도입이라
회귀 테스트 충분히 돈 뒤 실환경 커밋 필요.
```

## 메모

이 문서 자체가 "실수를 코드화"의 메타 사례 — "memory 유명무실"이라는
사용자의 정성 관찰을 근본 재설계로 흡수. 단순 기능 추가 아닌 **SSOT
관계 재정립**(실제 Claude memory vs 프로젝트 memory 경계, tmp→memory
흡수, 트리거 축소)이 핵심.
