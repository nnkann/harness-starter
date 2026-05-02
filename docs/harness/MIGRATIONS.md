---
title: 다운스트림 마이그레이션 가이드
domain: harness
tags: [migration, upgrade, downstream]
status: completed
created: 2026-04-19
updated: 2026-04-28
---

# 다운스트림 마이그레이션 가이드

`harness-upgrade` 스킬이 각 버전 업그레이드 시 이 문서를 읽어 다운스트림에
표시한다. **upstream 소유 — 다운스트림은 읽기만.**

**현재 버전 섹션 1개만 유지.** harness-upgrade 완료 후 해당 섹션 삭제.
버전 히스토리는 upstream git log가 SSOT (`git log --oneline --grep "(v0\."` 로 조회).

업그레이드 과정에서 발생한 충돌·이상 소견·수동 결정은 `docs/harness/migration-log.md`에
별도 기록한다 (다운스트림 소유, upstream은 읽기만).

## migration-log.md — 다운스트림 기록 문서

다운스트림 프로젝트 `docs/harness/migration-log.md`에 업그레이드마다 누적한다.
harness-upgrade 완료 시 버전 헤더를 자동 생성하며, **나머지는 다운스트림이 직접 채운다.**
upstream은 이 파일을 **절대 덮어쓰지 않는다.** 문제 발생 시 이 파일을 upstream에 전달.

```markdown
# migration-log

## v0.X → v0.Y (YYYY-MM-DD)

### 충돌·수동 결정
<!-- 3-way merge 충돌 해소 결정, theirs/ours 선택 이유 -->
- (없으면 생략)

### 이상 소견
<!-- 예상 밖 동작, 확인 필요 항목, upgrade 후 달라진 점 -->
- (없으면 생략)

### 수동 적용 결과
<!-- MIGRATIONS.md 수동 적용 항목 완료 여부 -->
- (없으면 생략)
```

기록할 것이 없는 버전은 헤더만 남겨도 된다.

---

## v0.29.1 — Phase 2-A 2단계: AC + CPS 시스템 강제 (efficiency overhaul)

### 변경 파일

| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/scripts/pre_commit_check.py` | 3-way merge | frontmatter `problem`·`solution-ref` 검증 + AC `Goal:` + 검증 묶음 추출 + CPS 박제 감지 (normalize_quote·verify_solution_ref·parse_ac_block 신설). 외형 룰 (UPSTREAM_PAT·META_M_PAT·rename/meta/WIP/docs-5줄 단독 skip) 폐기. `wip_kind`·`has_impact_scope` 폐기, `wip_problem`·`wip_solution_ref`·`ac_review`·`ac_tests`·`ac_actual` 출력 |
| `.claude/scripts/test_pre_commit.py` | 3-way merge | 외형 metric 테스트 (TestStageBasic 4개·TestIntegMoveCommit 전체) deprecate. 시크릿 게이트·standard 폴백 테스트만 유지 |
| `docs/WIP/harness--hn_harness_efficiency_overhaul.md` | 사용자 전용 (skip) | 자기증명 적용 — solution-ref list + 검증 묶음 |

### 적용 방법
자동. `harness-upgrade` 실행 시 3-way merge로 적용.

**다운스트림 필수 작업**:
- 신규 WIP·decisions·incidents·guides 작성 시 frontmatter `problem: P#`·`solution-ref:` (list) + AC `Goal:` + `검증:` 묶음 (review·tests·실측 3 키) 작성. 누락 시 commit 차단.
- 기존 50개 문서는 본 wave 밖 — 별 wave에서 backfill (점진).

### 자기증명 통과
본 commit 자체가 새 검증 시스템 통과:
```
pre_check_passed: true
wip_problem: P2
wip_solution_ref: S2 — "review tool call 평균 ≤4회 (부분)"; S2 — "docs-only 커밋이 skip 또는 micro로 분류됨"
ac_review: review-deep
ac_tests: pytest -m secret
ac_actual: AKIA 더미 staged + HARNESS_DEV=1 git commit → exit 1, 차단 확인
recommended_stage: deep
```

### 주의 — 외형 metric 폐기 영향
- `.claude/scripts/**` → deep 자동 격상 → 폐기. AC `검증.review` 작성자 선언이 결정
- `docs 5줄 이하` skip → 폐기. 줄 수 무관, AC 기반
- `WIP 단독`·`meta 단독`·`rename 단독` skip → 폐기. AC 기반
- 기존 WIP의 `> kind:` 마커, AC `영향 범위:` 항목 → 코드에서 더 이상 읽지 않음. 다운스트림 그대로 둬도 동작 무관

### 한계 (별 wave)
- eval/SKILL.md CPS 무결성 감시 (`--harness` 박제 발견) — 본 wave 밖
- commit 스킬 5.3 자동 실행 코드 (tests·실측 화이트리스트 실행) — 본 wave 밖, 1단계에 SSOT 정의는 됨
- legacy 50개 문서 frontmatter backfill — 별 wave (다운스트림 영향)
- AC 미작성 진입점 결함 audit (write-doc·implementation 진입점) — 별 WIP

### 회귀 위험
- upstream 격리 환경 검증:
  - `pytest -m "secret or stage"` 6/6 통과 + 4 skip (TestIntegMoveCommit deprecate)
  - 본 commit 자체 자기증명 통과 (위 출력 참조)
- staged WIP 없는 hot-fix 케이스: standard 폴백 (이전 외형 metric 추정 대신 보수)

### 검증
```bash
python3 .claude/scripts/pre_commit_check.py
pytest -m "secret or stage"
```

---

## v0.29.0 — Phase 2-A 1단계: AC + CPS 시스템 정의 (efficiency overhaul)

### 변경 파일 (24개 — 시스템 정의 문서만, 코드 변경 0)

| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/rules/docs.md` | 3-way merge | frontmatter `problem`·`solution-ref` SSOT 신설. AC 포맷 통합 (`Goal` + `검증` 묶음). CPS 면제 룰. 박제 감지 룰 |
| `.claude/rules/staging.md` | 자동 덮어쓰기 | 단일 룰 재작성 — AC `검증.review` 그대로 stage 결정. 외형 metric 룰 폐기 (kind 라벨·줄 수·경로) |
| `.claude/rules/naming.md` | 3-way merge | 메타데이터 SSOT 참조 추가 (docs.md로 위임) |
| `.claude/rules/coding.md`·`external-experts.md`·`hooks.md`·`internal-first.md`·`memory.md`·`no-speculation.md`·`pipeline-design.md`·`security.md`·`self-verify.md` | 3-way merge | 각 룰 상단에 `defends: P#` 추가 (어느 Problem 막는지 추적) |
| `.claude/skills/implementation/SKILL.md` | 3-way merge | Step 0 강화 — CPS 매칭 + AC 묶음 1차 제안. WIP 템플릿 갱신 |
| `.claude/skills/commit/SKILL.md` | 3-way merge | Step 5 책임 재정의. Step 5.3 신설 — tests·실측 자동 실행 (화이트리스트만). 핸드오프 계약 갱신 |
| `.claude/agents/review.md` | 3-way merge | `serves: S2` + Solution 회귀 검증 루프 + 입력 블록 `wip_problem`·`wip_solution_ref` |
| `.claude/agents/{advisor,codebase-analyst,debug-specialist,doc-finder,performance-analyst,researcher,risk-analyst,threat-analyst}.md` | 3-way merge | 각 에이전트 frontmatter에 `serves: S#` 추가 |
| `docs/WIP/harness--hn_harness_efficiency_overhaul.md` | 사용자 전용 (skip) | starter 자체 WIP — AC 1단계 ✅ |

### 적용 방법
자동. `harness-upgrade` 실행 시 3-way merge로 적용.

### 주의 — 동작 변경 없음 (정의만)
- 본 버전은 **시스템 정의 SSOT만 갱신**. pre_commit_check.py 등 강제 코드는 변경 없음.
- 강제는 v0.29.1 (Phase 2-A 2단계)에서 — pre_commit_check이 새 SSOT 따라 frontmatter 검증·외형 metric 폐기.
- 다운스트림은 본 버전 적용 후 신규 문서 작성 시 새 형식 권장. **차단은 v0.29.1부터**.

### 폐기 마커 호환성
- 기존 WIP의 `> kind:` 마커, AC `영향 범위:` 항목은 무시 (코드에서 더 이상 읽지 않음 — v0.29.1부터)
- 다운스트림이 그대로 둬도 동작 무관. 점진 마이그레이션

### 회귀 위험
- 코드 변경 0 — 동작 회귀 위험 없음
- 문서 SSOT 변경 — 다운스트림이 신규 문서 작성 시 새 형식 학습 부담

### 검증
```bash
# 룰 12개에 defends: 적용 확인
grep -L "^defends:" .claude/rules/*.md  # 0건 expect

# 에이전트 9개에 serves: 적용 확인
grep -L "^serves:" .claude/agents/*.md  # 0건 expect

# CPS 면제 (project_kickoff.md에 problem·solution-ref 없음)
grep -E "^(problem|solution-ref):" docs/guides/project_kickoff.md  # 0건 expect
```

---

## v0.28.9 — Phase 3 split 옵트인 강등 + AC [x] 자동 이동 (efficiency overhaul)

### 변경 파일
| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/scripts/pre_commit_check.py` | 3-way merge | split 결정 로직 옵트인 강등. char 다양성 ≥ 2 + (HARNESS_SPLIT_OPT_IN=1 OR 거대 커밋) + non-skip stage 모두 만족 시에만 split. 5/5 skip 케이스 자동 single |
| `.claude/scripts/docs_ops.py` | 3-way merge | wip-sync 자동 이동 트리거 확장. body_referenced 신호 추가 — 이미 [x] 상태 WIP에서도 staged 파일 본문 언급 시 자동 이동. 미완료 검사를 체크박스 패턴(`- [ ]`)으로 정밀화 |
| `.claude/rules/staging.md` | 3-way merge | "split 옵트인 정책" 섹션 신설. 기본 single, 분할은 명시 트리거 시에만 |

### 적용 방법
자동. `harness-upgrade` 실행 시 3-way merge로 적용.

### 주의
- **이전 동작 변경**: char 다양성 ≥ 2면 무조건 split → 이제는 거대 커밋 OR `HARNESS_SPLIT_OPT_IN=1` 명시 시에만. 다운스트림이 split 동작에 의존하지 않으면 자연 흡수
- **AC [x] 자동 이동**: 사용자가 미리 [x] 마킹한 WIP가 commit 시 자동 completed 이동. 차단 키워드(`TODO:`·빈 체크박스 등) 검사 통과 시에만
- **회고 영향**: "단일 결정 = 단일 커밋" atomic 원칙 적용. 다운스트림이 char별 selective fetch하지 않는 경우만 안전 (확인됨)
- 한계: `HARNESS_SPLIT_OPT_IN=1` 미지원 다운스트림 환경에선 자동 분할 의존이 불가능 — 거대 커밋 시 자동 분할은 동작

### 회귀 위험
- upstream 격리 환경(Windows + Git Bash):
  - `pytest -m "secret or stage"` 12/12 통과
  - 실측: 본 commit 자체 — char 다양성 2 + non-huge → split_action: single (이전엔 split)
  - T40.1 wip-sync abbr 테스트는 본 환경 fixture 격리 갭으로 fail (본 fix 무관, MIGRATIONS v0.28.4 주의 참조)

### 검증
```bash
pytest -m "secret or stage"
HARNESS_SPLIT_OPT_IN=1 /commit  # 명시 분할 옵트인
```

---

## v0.28.8 — Phase 1 시크릿 hook 이중화 (efficiency overhaul)

### 변경 파일
| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/scripts/install-starter-hooks.sh` | 3-way merge | hook 본문에 시크릿 패턴 풀 grep 추가 (sb_secret·service_role·AKIA·sk_live·ghp·glpat·xox·AIza·sk-ant·PRIVATE KEY 등). `HARNESS_DEV=1` 분기 이전에 시크릿 검사 실행 — 우회 불가. HARNESS.json hook_installed 자동 갱신 |
| `scripts/install-secret-scan-hook.sh` | 자동 덮어쓰기 | HARNESS.json hook_installed 자동 갱신 추가 (다운스트림용). 패턴 풀 변경 없음 |
| `.claude/scripts/pre_commit_check.py` | 3-way merge | json import + hook 미설치 경고 stderr 출력 (`HARNESS.json hook_installed` 체크). starter/다운스트림별 설치 명령 안내 |
| `.claude/scripts/bash-guard.sh` | 3-way merge | `git commit` 차단 메시지에 "시크릿 line-confirmed 가드는 git pre-commit hook이 항상 실행 — 우회 불가" 추가. 안내 톤 갱신 |
| `.claude/HARNESS.json` | 사용자 전용 (skip) | starter 자체에서 `hook_installed: true` 추가. 다운스트림은 install 스크립트가 자동 추가 |
| `README.md` | 사용자 전용 (skip) | secret-scan hook "선택" → "필수" 격상 + 우회 경로 안내 |

### 적용 방법
자동. `harness-upgrade` 실행 시 3-way merge로 적용.

**다운스트림 추가 작업 (필수)**:
1. `bash scripts/install-secret-scan-hook.sh` 실행 — 시크릿 hook 설치 (`HARNESS.json` `hook_installed` 자동 갱신)
2. 미설치 상태에서 commit 시 `pre_commit_check.py`가 stderr 경고 출력

### 주의
- **threat-analyst 발견**: 이전까지 `HARNESS_DEV=1 git commit` 경로가 시크릿 가드 완전 우회. bash-guard 통과(L101-103) + pre_commit_check 미호출 + hook도 통과. 본 버전이 hook 본문에 시크릿 검사 박아 우회 차단 (안전망 5/10 → 7.5/10).
- **`git commit --no-verify` 한계**: hook 자체 우회 — Phase 1으로 막을 수 없음. README 경고 + bash-guard 차단(Claude Code 내)으로 대응.
- **면제 위치**: `^\.claude/(scripts|agents|rules|skills|memory)/` 경로는 시크릿 패턴 SSOT 문서화 위치이므로 면제 (S1_LINE_EXEMPT와 동일).

### 회귀 위험
- upstream 격리 환경(Windows + Git Bash) 검증:
  - `pytest -m "secret or stage"` 12/12 통과
  - 실측: `HARNESS_DEV=1 git commit` + AKIA 더미 시크릿 → exit 1 차단 확인
  - 실측: `hook_installed=false` 시 stderr 경고 출력 확인
- PowerShell·WSL 환경 미테스트 (운용 검증 필요)
- 다운스트림이 secret-scan hook 미설치 시 안전망 부재 — pre-check 경고가 유일 알림

### 검증
```bash
bash .claude/scripts/install-starter-hooks.sh   # starter용
bash scripts/install-secret-scan-hook.sh        # 다운스트림용
pytest -m "secret or stage"
```

---

## v0.28.7 — HARNESS_UPGRADE 환경변수 폐기 (C 항목 — 옵션 B)

### 변경 파일
| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/scripts/pre_commit_check.py` | 3-way merge | L108 `HARNESS_UPGRADE` 정의 제거, L549 룰 0 분기 제거. 환경변수 의존 0 |
| `.claude/settings.json` | 3-way merge | `permissions.allow`에서 `Bash(HARNESS_UPGRADE=1 bash *)` 제거 |
| `.claude/rules/staging.md` | 3-way merge | 1단계 룰 0번 제거 + 폐기 안내 블록. review skip은 commit 스킬 `--no-review`로 흡수 |
| `.claude/skills/harness-upgrade/SKILL.md` | 3-way merge | Step 10 커밋 분기 — `HARNESS_UPGRADE=1 git commit` → `/commit --no-review`. "다른 스킬과의 관계" 표 commit 항목 갱신 |

### 적용 방법
자동. `harness-upgrade` 실행 시 3-way merge로 적용.

### 주의
- **다운스트림 영향**: 기존에 `HARNESS_UPGRADE=1` 환경변수를 쓰던 스크립트·alias가 있다면 **자연 무시**(분기 제거됨). 명시적 정리 권장 — `git grep HARNESS_UPGRADE`로 확인 후 제거.
- **review skip 대체**: harness-upgrade 자체는 본 버전부터 `/commit --no-review` 호출. 사용자가 직접 review skip 필요하면 동일하게 `--no-review` 플래그 사용.
- 회고적 기록(README v0.26.9 변경 이력, MIGRATIONS L398, hn_upstream_anomalies.md 본문)은 당시 상태 보존 — 변경 안 함.

### 회귀 위험
- upstream 격리 환경(Windows + Git Bash)에서 검증:
  - `python3 -c "import json; json.load(open('.claude/settings.json'))"` JSON 유효
  - `from pre_commit_check import ENOENT_PATTERNS` import OK
  - `pytest -m "secret or stage"` 12/12 통과
- 활성 코드 잔여 참조 0 (회고적 기록 5건만).

### 검증
```bash
python3 -c "import json; json.load(open('.claude/settings.json'))"
python3 -m pytest .claude/scripts/test_pre_commit.py -m "secret or stage"
grep -l HARNESS_UPGRADE .claude/scripts/ .claude/rules/ .claude/skills/  # 활성 코드 0건
```

---

## v0.28.6 — upstream anomalies B·D·E·F 일괄 wave (보안·LF·worktree·sanity)

### 변경 파일
| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/settings.json` | 3-way merge | `permissions.allow`에서 `Bash(rm *)`·`Bash(export *)` 제거. 와일드카드 삭제·임의 export는 starter 기본 권한에서 빠짐 (B) |
| `.gitattributes` | 신규 | `* text=auto eol=lf` + 바이너리 제외. Windows + Git Bash 환경에서 3-way merge 통째 충돌 방지 (D) |
| `.claude/scripts/bash-guard.sh` | 3-way merge | 검증 2.5 추가 — `git worktree add` 차단. CLAUDE.md 절대 규칙 코드 강제. list/remove/prune은 통과 (E) |
| `.claude/skills/harness-upgrade/SKILL.md` | 3-way merge | Step 0.1 worktree 잔여 자동 정리(clean 자동/dirty 안내) + Step 1 fetch 후 installed_from_ref sanity check + Step 5 ours `tr -d '\r'` LF 정규화 + Step 8.1 위험 패턴 명시 승인 강제 + Step 10 갱신 후 sanity check (B·D·E·F) |
| `docs/WIP/harness--hn_upstream_anomalies.md` | 사용자 전용 (skip) | starter 자체 WIP 갱신 — 다운스트림은 건드리지 않음 |

### 적용 방법
자동. `harness-upgrade` 실행 시 3-way merge로 적용.

### 주의
- **B 위험 권한 제거**: 다운스트림이 `Bash(rm *)`·`Bash(export *)`를 이전 업그레이드에서 받았다면 Step 8.1이 자동 제거하지 않는다 (사용자 추가로 분류). 직접 `.claude/settings.json`에서 제거 검토.
- **D LF 정규화**: 신규 클론은 `.gitattributes`로 보호. 기존 워킹트리(autocrlf 환경)는 `git add --renormalize .` 1회 실행 권장. harness-upgrade 자체는 Step 5에서 `tr -d '\r'`로 런타임 보호.
- **E worktree 차단**: `git worktree add` 시도 시 exit 2. 잔여가 있으면 harness-upgrade Step 0.1이 clean한 것만 자동 제거. dirty는 안내만 — 사용자 직접 정리.
- **F sanity check**: Step 1 fetch 직후 + Step 10 갱신 후 양쪽. 한 지점만으로는 다음 업그레이드 시점까지 stale ref가 묻혀 ADDED 부풀림 발생.
- C(HARNESS_UPGRADE 환경변수 의미 일관화)는 미해결 — 별 wave.

### 회귀 위험
- upstream 격리 환경(Windows + Git Bash)에서 검증 범위:
  - `python3 -c "import json; json.load(open('.claude/settings.json'))"` JSON 유효
  - `bash -n .claude/scripts/bash-guard.sh` 구문 OK
  - `echo '{"tool_input":{"command":"git worktree add foo"}}' | bash bash-guard.sh` → exit 2 차단 실측
  - `echo '{"tool_input":{"command":"git worktree list"}}' | bash bash-guard.sh` → exit 0 통과 실측
- harness-upgrade SKILL.md 변경분은 자동 검증 불가 — 다운스트림 업그레이드 사이클에서 운용 검증 필요.
- `.gitattributes` 첫 도입 — 기존 워킹트리에서 `git add` 시 CRLF→LF 정규화 경고 발생 (의도된 동작).

### 검증
```bash
python3 -c "import json; json.load(open('.claude/settings.json'))"
bash -n .claude/scripts/bash-guard.sh
echo '{"tool_input":{"command":"git worktree add foo"}}' | bash .claude/scripts/bash-guard.sh  # exit 2
echo '{"tool_input":{"command":"git worktree list"}}' | bash .claude/scripts/bash-guard.sh    # exit 0
```

---

## v0.28.5 — docs_ops·harness_version_bump·task_groups encoding="utf-8" 일괄 (G Phase 3)

### 변경 파일
| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/scripts/docs_ops.py` | 3-way merge | `git()` helper에 `encoding="utf-8"` 추가. 한글 git 출력에서 cp949 디코딩 실패 방지 |
| `.claude/scripts/harness_version_bump.py` | 3-way merge | `run()` helper에 `encoding="utf-8"` + `or ""` 방어 |
| `.claude/scripts/task_groups.py` | 3-way merge | 동일 |

### 적용 방법
자동. `harness-upgrade` 실행 시 3-way merge로 적용.

### 주의
- G 항목(Windows + 한글 환경 무한 막힘) 마지막 wave. Phase 1·2가 `pre_commit_check.py`의 갈래 1·2를 해소했고, 본 Phase 3은 같은 패턴이 다른 스크립트에 반복돼 있던 것을 일괄 정리.
- 세 파일 모두 `def main()` + `if __name__ == "__main__":` 구조는 이미 적용돼 있어 추가 리팩토링 불필요.
- WIP `harness--hn_upstream_anomalies.md` G 항목 ✅ 해결로 마킹. B·C·D·E·F는 미해결 — 별 wave로 진행.

### 회귀 위험
- upstream 격리 환경(Windows + Git Bash)에서 `pytest -m "secret or gate or stage or enoent"` 27/27 통과.
- 세 파일의 subprocess 호출 변경 — 한글 미포함 출력은 기존과 동일 동작. UTF-8 디코딩 가능한 모든 입력 처리.

### 검증
```bash
pytest -m "secret or gate or stage or enoent"
```

---

## v0.28.4 — pre_commit_check.py main 함수화 (G Phase 2 — script-as-module 결함 해소)

### 변경 파일
| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/scripts/pre_commit_check.py` | 3-way merge | 580줄 module-level main 로직 → `def main() -> int:` 함수화 + `if __name__ == "__main__": sys.exit(main())` 보호. ENOENT_PATTERNS만 module-level 유지 (test가 import). 입력 수집·검사·출력 전부 main() 안으로 이동 |
| `.claude/scripts/test_pre_commit.py` | 3-way merge | `TestModuleImportSafe::test_import_does_not_exit` 신규 — staged 변경 유무 무관 import 후 sys.exit 발생 안 함 검증 (`enoent` marker) |

### 적용 방법
자동. `harness-upgrade` 실행 시 3-way merge로 적용.

### 주의
- **import 시 main 로직 미실행**: `from pre_commit_check import X`가 모듈 import만 수행. 기존 module-level mutable 변수(staged_files·name_status_raw 등)에 outer scope에서 직접 접근하던 코드가 있다면 → 본 변경으로 영향. test_pre_commit.py 외 import 사용처 없음 확인.
- ENOENT_PATTERNS 정규식만 module-level 유지. 다른 정규식(S1_LINE_PAT·SKIP_TODO 등)은 main() 안에 있음 — main 호출당 1회 컴파일. 미미.
- Phase 1(v0.28.3)의 `encoding="utf-8"` fix와 함께 동작. 둘 다 갈래 1·2 결함 해소.

### 회귀 위험
- upstream 격리 환경(Windows + Git Bash)에서 `pytest -m "secret or gate or stage or enoent"` 27/27 통과 확인.
- Linux/macOS·다운스트림 환경 미테스트. 580줄 들여쓰기 변경이라 실측 회귀 모니터링 권장.
- T40.1 wip-sync abbr 매칭 테스트는 본 작업 sandbox 환경에서 fixture 격리 갭으로 fail (본 fix 무관) — fixture가 starter repo clone 시 작업 중 WIP가 따라가서 같은 abbr 충돌. 별 issue.

### 검증
```bash
pytest -m "secret or gate or stage or enoent"  # 27/27 통과
python -c "import sys; sys.path.insert(0, '.claude/scripts'); from pre_commit_check import ENOENT_PATTERNS; print(ENOENT_PATTERNS)"  # import 후 sys.exit 없음
```

---

## v0.28.3 — pre_commit_check.py run() encoding="utf-8" (G Phase 1)

### 변경 파일
| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/scripts/pre_commit_check.py` | 3-way merge | `run()`에 `encoding="utf-8"` + `or ""` 방어 추가. Windows + 한글 staged diff에서 system locale(cp949) 디코딩 실패로 `stdout=None` 되던 결함 해소 |
| `docs/WIP/harness--hn_upstream_anomalies.md` | 신규 | 다운스트림 발견 이상 징후 묶음 SSOT (B·C·D·E·F·G) — G Phase 1만 해결, 나머지 미해결 |

### 적용 방법
자동. `harness-upgrade` 실행 시 3-way merge로 적용.

### 주의
- Phase 1만으론 `from pre_commit_check import X` 회귀 가드 미적용 — Phase 2(main 함수화) 후 박을 예정.
- staged 변경이 없을 때 직접 호출(`python pre_commit_check.py`)은 PYTHONUTF8 없이도 정상 동작 확인.
- 다운스트림 영향: Windows 사용자가 한글 commit 메시지·diff에서 겪던 무한 차단 부분 해소 (직접 호출 경로). Linux/macOS 미영향.

### 회귀 위험
- upstream 격리 환경(Windows + Git Bash, 한글 staged diff)에서 직접 호출 통과 실측 확인.
- import 경로(staged 시 sys.exit)는 Phase 2까지 미해소 — 회귀 가드 테스트 추가도 Phase 2 의존.

### 검증
```bash
unset PYTHONUTF8; python .claude/scripts/pre_commit_check.py  # cp949 실패 안 함
pytest -m secret  # 기존 회귀 가드 통과
```

---

## v0.28.2 — pre-check 시크릿 line 면제 갭 + docs_ops untracked move 갭

### 변경 파일
| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/scripts/pre_commit_check.py` | 3-way merge | `S1_LINE_EXEMPT` 정규식을 `^\.claude/(scripts\|agents\|rules\|skills\|memory)/`로 확장. 하네스 자체가 시크릿 패턴을 SSOT로 문서화하는 위치(agents·rules·skills·memory)가 line-confirmed로 잘못 차단되던 문제 해소 |
| `.claude/scripts/docs_ops.py` | 3-way merge | `cmd_move` fallback에서 `git ls-files --error-unmatch`로 src 인덱스 존재 여부 확인 후 `git rm --cached` 시도. untracked WIP 이동이 매번 returncode 1로 실패하던 갭 해소 |
| `.claude/scripts/test_pre_commit.py` | 3-way merge | 회귀 테스트 2건 추가 — `TestSecretScan::test_harness_doc_line_exempt`, `TestMoveUntrackedWip::test_untracked_move_succeeds` |

### 적용 방법
자동. `harness-upgrade` 실행 시 3-way merge로 적용.

### 주의
- 다운스트림에서 `.claude/agents/threat-analyst.md` 같은 패턴 SSOT 문서를 수정하면
  `🚫 pre-check 차단 — 시크릿 line-confirmed (s1_level)` 메시지가 발생하던 false-positive 해소.
- 면제 범위는 `.claude/(scripts|agents|rules|skills|memory)/`로 한정. `docs/`·사용자 코드(`src/` 등)는 여전히 line 스캔 적용.
- untracked WIP fallback fix로 implementation→commit 흐름의 잠재 결함 해소.

### 회귀 위험
- upstream 격리 환경(Windows/Git Bash)에서 관찰된 범위 내에서는 영향 없음.
  `pytest -m secret` 4/4 통과, untracked move 직접 sandbox 검증 통과.
- 별개 환경 결함(Windows cp949 디코딩 + module-level main 로직 import)으로
  `pytest -m docs_ops`는 본 환경에서 실행 불가 → 관련 테스트는 `PYTHONIOENCODING=utf-8`
  + 임시 repo subprocess로 우회 검증. 별도 추적 필요.

### 검증
```bash
pytest -m secret
PYTHONIOENCODING=utf-8 pytest .claude/scripts/test_pre_commit.py::TestMoveUntrackedWip
```

---

## v0.28.1 — completed 전환 차단 — 코드블록 안 면제

### 변경 파일
| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/scripts/docs_ops.py` | 3-way merge | `_extract_body`에 코드블록(``` ```·`~~~`) 추적 추가. 코드블록 안 라인은 차단 검사 대상 아님 |
| `.claude/rules/docs.md` | 3-way merge | "completed 전환 차단" 섹션에 "코드블록 안 면제" 룰 명시 |

### 적용 방법
자동. `harness-upgrade` 실행 시 3-way merge로 적용.

### 주의
- AC 포맷 예시·문법 설명을 코드블록에 박은 WIP들이 completed 이동 시 거짓 차단되던 문제 해소.
- 회고형 차단(v0.27.6) + 코드블록 면제(이번)로 차단 룰 정밀도가 두 단계 향상.

### 검증
```bash
python3 .claude/scripts/docs_ops.py move <테스트용 WIP>
```

---

## v0.27.3 — Karpathy 원칙 적용 (Phase 1): 코딩 컨벤션·행동 원칙·AC 기반 검증 구조

### 변경 파일
| 파일 | 처리 | 비고 |
|------|------|------|
| `CLAUDE.md` | 3-way merge | `## 행동 원칙` 섹션 추가 (Think Before Coding + Goal-Driven) |
| `.claude/rules/coding.md` | 3-way merge | Surgical Changes 원칙·금지 패턴 추가 |
| `.claude/rules/self-verify.md` | 3-way merge | Goal-Driven 원칙, AC 완료 기준, TDD/fail-first |
| `.claude/rules/docs.md` | 3-way merge | WIP AC 포맷 확장 (`Goal:` + `영향 범위:`) |
| `.claude/rules/staging.md` | 3-way merge | AC 기반 검증 원칙 추가, 연결 규칙 B·C에 AC 조건 추가 |
| `.claude/skills/commit/SKILL.md` | 3-way merge | Stage별 행동 직접 서술 → staging.md 포인터로 교체 |

### 변경 내용
- CLAUDE.md에 구현 전 사고 원칙(Think Before Coding, Goal-Driven) 추가
- coding.md에 Surgical Changes 원칙 5개 + 금지 패턴 5개 명문화
- self-verify.md: AC 체크박스가 완료 기준임을 명시, TDD/fail-first 원칙 추가
- docs.md: WIP AC에 `Goal:` + `영향 범위:` 항목 포맷 추가
- staging.md: AC 기반 검증 원칙 추가, `영향 범위:` → deep 트리거, AC 전부 [x] → micro 완화
- commit/SKILL.md: staging SSOT 충돌 해소 (Stage별 행동 재서술 제거)

### 적용 방법

**자동 적용**: harness-upgrade가 처리. 확인만.

### 회귀 위험
- staging.md 연결 규칙 B·C에 AC 기반 조건 추가됨 — 기존 신호 체계는 유지
- 다운스트림 CLAUDE.md에 `## 행동 원칙` 섹션이 추가됨 (기존 절대 규칙 위치 변경 없음)

---

## 포맷

```markdown
## vX.Y — 한 줄 요약

### 변경 파일
| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/skills/foo/SKILL.md` | 3-way merge | 변경 이유 한 줄 |
| `.claude/scripts/bar.py` | 자동 덮어쓰기 | |
| `.claude/agents/baz.md` | 신규 추가 | |

처리 값: `자동 덮어쓰기` · `3-way merge` · `신규 추가` · `삭제`

### 변경 내용
이번 버전에서 달라진 것. 다운스트림이 맥락 파악용.

### 적용 방법

**자동 적용**: harness-upgrade가 처리. 확인만.
- ...

**수동 적용**: upgrade 후 직접 실행. 안 하면 미동작.
- 없음  ← 없을 때도 명시

### 검증
적용 후 확인 방법.
```

---

## v0.27.2 — 도메인 시스템 갭 수정 및 문서 참조 정합성 복구

### 변경 파일
| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/scripts/pre_commit_check.py` | 3-way merge | docs_ops 함수 import + S9 WIP 도메인 추출 수정 + 경로→도메인 3단계 구현 |
| `.claude/scripts/docs_ops.py` | 3-way merge | extract_path_domain_map 예시 블록 오파싱 수정 |
| `.claude/scripts/task_groups.py` | 자동 덮어쓰기 | NAMING_MD dead code 제거 |
| `.claude/scripts/test_pre_commit.py` | 3-way merge | _add_path_domain_map 헬퍼 실제 매핑 블록 참조로 수정 |
| `.claude/rules/naming.md` | 3-way merge | docs-ops.sh → docs_ops.py 참조 수정 + 실제 매핑 코드블록 추가 |
| `.claude/rules/docs.md` | 자동 덮어쓰기 | docs-ops.sh → docs_ops.py 참조 수정 (4곳) |
| `.claude/rules/staging.md` | 자동 덮어쓰기 | pre-commit-check.sh → pre_commit_check.py 참조 수정 (3곳) |
| `.claude/rules/security.md` | 자동 덮어쓰기 | install-secret-scan-hook.sh → install-starter-hooks.sh |
| `.claude/agents/review.md` | 3-way merge | pre-commit-check.sh → pre_commit_check.py, docs-ops.sh → docs_ops.py |
| `.claude/agents/doc-finder.md` | 자동 덮어쓰기 | docs-ops.sh → docs_ops.py |
| `.claude/agents/threat-analyst.md` | 3-way merge | pre-commit-check.sh → pre_commit_check.py + bash 스니펫 S1_LINE_PAT 기반으로 교체 |

### 변경 내용

**갭 1 — WIP 도메인 추출 오류 수정**: `pre_commit_check.py` S9 블록에서 WIP 파일
도메인을 라우팅 태그(`decisions`, `guides`)로 잘못 추출하던 문제 수정.
`docs_ops.detect_abbr()` + abbr→domain 역매핑으로 실제 도메인(`harness`, `meta`) 추출.
WIP-only 커밋에서 critical 도메인이 deep으로 격상되지 않던 문제 해소.

**갭 2 — naming.md 파싱 중복 제거**: `pre_commit_check.py`가 `docs_ops.py`의
`extract_abbrs`, `detect_abbr`, `extract_path_domain_map`, `path_to_domain`을
동적 import해 재사용. naming.md를 두 스크립트가 별도 파싱하던 중복 제거.

**갭 3 — 경로→도메인 매핑 3단계 구현**: staging.md 명세 4단계 중 3단계
(naming.md 경로→도메인 매핑)가 구현되지 않던 문제 수정. naming.md에
`실제 매핑` 코드블록 영역 추가 — 다운스트림이 여기에 경로 매핑 등록 시 S9에 반영.

**문서 참조 정합성**: 존재하지 않는 `docs-ops.sh`, `pre-commit-check.sh`,
`install-secret-scan-hook.sh` 참조를 실제 파일명으로 일괄 수정 (총 14곳).

### 적용 방법

**자동 적용**: harness-upgrade가 처리. 확인만.

**수동 적용**: naming.md `## 경로 → 도메인 매핑` 섹션 하단 `실제 매핑` 코드블록에
프로젝트 코드 폴더 경로 매핑 추가 권장 (S9 도메인 등급 신호 정확도 향상).
예: `src/payment/**     → payment`

### 검증
`python3 -m pytest .claude/scripts/test_pre_commit.py -q` → 56 passed.

---

## v0.27.1 — eval 기본 모드 보고 구조 개선 (거시/미시 계층 + memory 저장)

### 변경 파일
| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/skills/eval/SKILL.md` | 3-way merge | 기본 모드 절차 4→6단계 확장 |

### 변경 내용

`/eval` 기본 모드 절차에 분류(4)·보고(5)·저장(6) 단계 추가.

- 발견된 간극을 **거시**(CPS 방향 이탈) / **단기 블로커**(다음 작업 차단) / **장기 부채**(방치 시 위험) 세 층으로 분류
- 대화 출력은 거시 요약 + 단기 블로커만 간결하게, 장기 부채 상세는 memory 참조로 압축
- eval 완료 시 항상 `.claude/memory/project_eval_last.md`에 전체 상세를 덮어쓰기 저장 + `MEMORY.md` 인덱스 갱신 (0건이어도 실행)

### 적용 방법

**자동 적용**: harness-upgrade가 처리. 확인만.

**수동 적용**: 없음

### 검증
`/eval` 실행 후 `.claude/memory/project_eval_last.md` 생성 여부 확인.

---

## v0.27.0 — UserPromptSubmit debug-guard 훅 신설

### 변경 파일
| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/scripts/debug-guard.sh` | 신규 추가 | UserPromptSubmit 키워드 감지 스크립트 |

### 변경 내용
사용자 메시지에 "에러", "버그", "오류", "원인" 등 키워드가 감지되면
`debug-specialist` 에이전트를 먼저 호출하도록 Claude 컨텍스트에 주입.
Claude가 직접 추측 수정으로 진행하는 패턴을 시스템 레벨에서 차단.

### 적용 방법

**자동 적용**: harness-upgrade가 처리. 확인만.

**수동 적용**: 없음

### 검증
`echo '{"prompt":"에러났어 원인을 찾아"}' | bash .claude/scripts/debug-guard.sh`
→ `⚠️ [debug-guard]` 메시지 출력되면 정상.

---

## v0.26.9 — harness-upgrade 커밋 분기 + MIGRATIONS 변경 파일 섹션

### 변경 파일
| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/skills/harness-upgrade/SKILL.md` | 3-way merge | Step 10 커밋 분기 + Step 3 변경 파일 표 참조 추가 |
| `docs/harness/MIGRATIONS.md` | 자동 덮어쓰기 | `### 변경 파일` 섹션 포맷 추가 |

### 변경 내용

- `harness-upgrade/SKILL.md` Step 10: 커밋 시 `CONFLICT_RESOLVED` 유무로 분기. 충돌 해소 파일 없으면 `HARNESS_UPGRADE=1`로 review skip, 있으면 해당 파일만 `--quick` review
- `harness-upgrade/SKILL.md` Step 3: MIGRATIONS.md `### 변경 파일` 표를 git diff보다 우선 참조해 처리 방식 결정
- `MIGRATIONS.md` 포맷에 `### 변경 파일` 섹션 추가 — 파일별 처리 방식(`자동 덮어쓰기`·`3-way merge`·`신규 추가`·`삭제`) 명시

### 적용 방법

**자동 적용**: harness-upgrade가 처리

**수동 적용**: 없음

---

## v0.26.8 — commit Step 4 다운스트림 skip 명시

### 변경 내용

- `commit/SKILL.md` Step 4: `is_starter` 값을 먼저 확인해 `false`(다운스트림)이면 Step 4 전체를 건너뛰도록 명시. 기존에는 스크립트가 내부적으로 exit했지만 Step 자체는 실행됐음

### 적용 방법

**자동 적용**: harness-upgrade가 처리

**수동 적용**: 없음

---

## v0.26.7 — harness_version_bump.py HEAD 버전 기준 수정

### 변경 내용

- `harness_version_bump.py`: `current` 버전을 디스크(HARNESS.json)가 아닌 HEAD에서 읽도록 수정. commit Step 4에서 HARNESS.json을 디스크에 먼저 쓰고 staged하면 `current`가 이미 범프된 버전을 가리켜 "범프 필요" 오탐 발생하던 버그 수정

### 적용 방법

**자동 적용**: 스크립트 갱신

**수동 적용**: 없음

---

## v0.26.6 — harness-upgrade Step 9.7 오탐 수정 + Step 10.4 제거

### 변경 내용

- harness-upgrade Step 9.7: `grep "- \[ \]"` 패턴이 백틱 인라인 코드(`` `- [ ]` ``)까지 오탐하던 문제 수정 — `grep -v` 추가
- harness-upgrade Step 10.4 제거: MIGRATIONS.md는 Step 3 자동 덮어쓰기로 이미 단일 섹션 유지됨. Claude가 섹션을 수동 삭제하는 불안정한 단계 제거

### 적용 방법

**자동 적용**: harness-upgrade SKILL.md 갱신

**수동 적용**: 없음

---

## v0.26.5 — hook 버전 체크 제거 + pre-check 경고로 이전

### 변경 내용

- `install-starter-hooks.sh`: hook의 버전 범프 체크 로직 제거. 버전 판단은 commit Step 4(Claude)가 담당
- `pre_commit_check.py`: is_starter 전용 버전 미범프 경고 추가 (차단 아님 — `risk_factors`에 기록)

### 적용 방법

**자동 적용**: 스크립트 갱신. hook은 `harness-sync` 또는 `bash .claude/scripts/install-starter-hooks.sh` 재실행으로 갱신.

**수동 적용**: 없음

---

