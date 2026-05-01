---
title: "harness-starter 이상 징후 묶음 (다운스트림 발견)"
domain: harness
tags: [upstream, anomaly, secret-scan, permissions, upgrade]
relates-to:
  - path: harness/hn_migrations_version_gap.md
    rel: extends
  - path: incidents/hn_secret_line_exempt_gap.md
    rel: references
status: in-progress
created: 2026-05-01
updated: 2026-05-01
---

# harness-starter 이상 징후 묶음 (다운스트림 발견)

다운스트림 Issen 프로젝트에서 harness-upgrade를 진행하다가 발견한
업스트림(harness-starter) 측 처리 미비·정책 불일치를 모아 starter PR로
이관하기 위한 단일 SSOT.

미래에 또 다른 anomaly가 나오면 같은 파일에 `## v0.X` 섹션을 누적한다.

---

## v0.28.1 (2026-05-01 발견)

발견 컨텍스트: Issen 다운스트림에서 v0.26.8 → v0.28.1 업그레이드 후
`/commit` 시도 → pre-check이 starter 자체 콘텐츠를 false positive로 차단.

### A. 시크릿 스캔 false positive — 차단 발생 [✅ v0.28.2 해결]

> **상태**: starter v0.28.2에서 해결 완료. SSOT는
> [`incidents/hn_secret_line_exempt_gap.md`](../incidents/hn_secret_line_exempt_gap.md)
> 참조. 다운스트림은 다음 `harness-upgrade`에서 자동 흡수. 아래 본문은
> 발견 당시(v0.28.1) 컨텍스트 보존용.

**증상**: `pre_commit_check.py`의 시크릿 line-confirmed 검사가
`.claude/agents/threat-analyst.md`에서 hit. 다운스트림 커밋 차단(exit 2).

**hit 위치 (모두 false positive 검증 완료)**:
- `.claude/agents/threat-analyst.md:53-54` — 시크릿 패턴 설명문 + grep 명령 예시 (에이전트가 하는 일을 본문에서 설명)
- `.claude/scripts/pre_commit_check.py:421` — 정규식 정의 자체 (S1_LINE_PAT)
- `.claude/scripts/test_pre_commit.py` — 테스트 픽스처 (시크릿 패턴 더미 문자열)

**원인**: `S1_LINE_EXEMPT` 정규식이 `^\.claude/scripts/`로만 한정. 시크릿 검출
에이전트인 `threat-analyst.md`가 본문에서 패턴을 설명하는 게 자연스러운데
면제 룰에 빠져 있음.

**채택된 해결**: 옵션 1 확장판 — `S1_LINE_EXEMPT`를
`^\.claude/(scripts|agents|rules|skills|memory)/`로 확장 (agents 외에도
rules/skills/memory가 같은 패턴 SSOT 문서화 위치). v0.28.2 commit `f0e7a2c`.

**검토 후 폐기**: 옵션 2 (HARNESS_UPGRADE secret 우회)는 채택 안 함.
이유: 면제 범위를 코드(정규식)로 명확히 하는 게 환경변수 분기보다
검증·디버깅이 쉽고, starter release/다운스트림 upgrade 둘 다 같은 룰
적용 가능 (일관성). 다만 HARNESS_UPGRADE 환경변수의 의미 일관화 자체는
별 issue로 → C로 이관.

**검증 갭 (당시 의문)**: starter 측에서도 같은 release 시 동일 차단을
받았어야 정상인데 v0.28.1이 release된 점은 — starter가 그 release 시점
threat-analyst.md를 직접 수정 안 했기에 통과한 것이지 우회 메커니즘이
있던 게 아님. 본 v0.28.2 fix wave에서 직접 수정 시도 → 차단 재현 → fix
→ 실측 검증 완료.

---

### B. 위험 권한 신규 (Bash(rm *), Bash(export *))

**증상**: 업그레이드 시 `permissions.allow`에 `Bash(rm *)`, `Bash(export *)`
가 자동 추가 후보로 잡힘. 다운스트림에서 무비판 동기화 시 와일드카드 `rm`
허용으로 어떤 경로든 삭제 가능.

**원인**: starter `settings.json`에 starter 기본 권한으로 포함됨.

**제안**:
- `Bash(rm *)`는 starter 기본 권한에서 제거. 정말 필요하면 더 좁은 패턴
  (예: `Bash(rm tests/output/*)`, `Bash(rm /tmp/*)`)으로 한정.
- 또는 starter `settings.json`에서 빼고, 사용자가 프로젝트별 필요에 따라
  추가하도록 가이드.
- `harness-upgrade` 스킬의 Step 8.1에서 위험 패턴(`rm `, `--force`, `reset --hard`)
  은 자동 추가 대신 사용자 명시 승인 강제.

**다운스트림 처리**: 이번 Issen 다운스트림은 `Bash(rm *)`를 그대로 받았으나,
별도 정리 PR로 settings.json에서 제거 검토.

---

### C. HARNESS_UPGRADE 환경변수 의미 일관화

> **재포지셔닝**: A가 `S1_LINE_EXEMPT` 확장으로 해결돼 secret 우회는
> 불필요해짐. 본 항목은 "HARNESS_UPGRADE=1이 어디까지 우회하는가"의
> 의미 정의 일관성 issue로 한정.

**증상**: `HARNESS_UPGRADE=1` 환경변수가 일부 차단 경로만 우회하는
비대칭 동작. 현재 처리:

| 차단 경로 | HARNESS_UPGRADE=1 동작 |
|-----------|------------------------|
| review stage (`recommended_stage`) | `skip`으로 강제 ✅ |
| secret line-confirmed (`s1_level`) | 우회 안 함 (sys.exit 2) |
| 거대 커밋 경고 / split 권장 | 동작 미확인 — 검증 필요 |
| WIP completed 잔재 차단 | 동작 미확인 — 검증 필요 |

**원인**: 환경변수 도입 시 "review만 skip한다"는 좁은 의도였으나,
다운스트림이 starter 콘텐츠를 mirror하는 시나리오에서 다른 차단 경로도
의미상 우회 대상. 정의가 코드 곳곳에 흩어져 SSOT 부재.

**제안**:
- `pre_commit_check.py`에 `HARNESS_UPGRADE=1`이 어떤 차단 경로를 우회하는지
  표 또는 SSOT 주석 한 곳에 정리.
- 결정: secret은 `S1_LINE_EXEMPT`로 정확히 면제(이미 v0.28.2). 그 외
  차단 경로는 case-by-case로 우회 여부 결정 + 결정을 SSOT 문서화.
- 또는 `HARNESS_UPGRADE` 환경변수 자체를 폐기하고 review stage skip은
  staging.md 룰 0번(`HARNESS_UPGRADE=1` → skip)에 한정한 채, 다른 차단은
  사용자 명시 승인으로 처리.

---

### D. CRLF/LF 정규화 미비 — 3-way merge 첫 시도 통째 충돌

**증상**: `harness-upgrade` 스킬 Step 5에서 3-way merge 12개 파일이 모두
"충돌 1개" 판정. 충돌 마커가 파일 1번부터 끝까지 통째로 박힘 — base/theirs는
LF, 다운스트림 워킹트리(ours)는 CRLF + LF 혼합.

**우회**: 다운스트림에서 ours를 `tr -d '\r'`로 LF 정규화 후 재머지하면
11/12 clean.

**제안**:
- `harness-upgrade` 스킬 Step 5에서 ours를 `git merge-file` 호출 전 LF로
  정규화하는 단계 추가. 예:
  ```bash
  tr -d '\r' < "$f" > "$TMPDIR/ours"
  ```
- 또는 starter `.gitattributes`에 `* text=auto eol=lf` 추가하고
  `h-setup.sh` 또는 `harness-sync`에서 다운스트림 워킹트리 정규화 강제.
- Windows에서 Git Bash + autocrlf 환경이 흔하므로 이 처리는 필수.

---

### E. worktree 정책-실태 불일치

**증상**: 다운스트림 CLAUDE.md `## 절대 규칙`에 "worktree 생성 금지" 명시
+ "Agent 호출 시 isolation: worktree 사용 금지" 명시. 그런데 실제 다운스트림
워킹트리에 `.claude/worktrees/adoring-hofstadter-3f334e/` 잔여가 있음
(4월 17일 생성, `git worktree list`에 등록됨).

**원인**: 정책은 규칙 문서에만 있고 강제 메커니즘 없음.

**제안 — 차단 우선** (`.gitignore` 추가는 모순이라 폐기):

`.gitignore`에 `.claude/worktrees/` 추가하면 "거기 만들어도 ignore된다"는
신호 → CLAUDE.md "worktree 생성 금지" 절대 규칙을 약화시킴. 모순.

대신 **차단 + 자동 정리 메커니즘**으로 해결:

#### 1. `bash-guard.sh`에 `git worktree add` 차단 (시도 자체를 막음)

신규 생성 차단 룰 추가 (rules/hooks.md 차단 패턴 형식). 잔여가 더
쌓이지 않게 원천 봉쇄.

#### 2. `harness-upgrade` Step 0에 잔여 자동 정리 (안내만이 아니라 실질 정리)

```bash
STRAY=$(git worktree list --porcelain | awk '/^worktree / && NR>1 {print $2}')
if [ -n "$STRAY" ]; then
  echo "⚠ worktree 잔여 발견 — CLAUDE.md 절대 규칙 위반 상태:"
  echo "$STRAY"
  for wt in $STRAY; do
    # uncommitted 변경 체크 — 변경 있으면 자동 정리 안 함, 사용자 승인 필요
    DIRTY=$(git -C "$wt" status --porcelain 2>/dev/null)
    if [ -n "$DIRTY" ]; then
      echo "  ⚠ $wt: uncommitted 변경 있음 — 자동 정리 skip"
      echo "     변경 목록:"
      echo "$DIRTY" | sed 's/^/       /'
      echo "     정리하려면: 변경 commit/stash 후 git worktree remove $wt"
    else
      echo "  ✓ $wt: clean → 자동 정리"
      git worktree remove "$wt" 2>&1
      [ -d "$wt" ] && rm -rf "$wt"  # git이 디렉토리 못 지운 경우 강제 제거
    fi
  done
  # prune으로 stale 메타데이터까지 청소
  git worktree prune
fi
```

**원칙:**
- clean worktree는 자동 정리 (사용자 승인 불필요 — CLAUDE.md 절대 규칙
  위반 상태이고 변경 없으니 손실 없음)
- dirty worktree는 변경 목록 표시 + 사용자 직접 정리 안내 (자동 force
  remove는 절대 금지 — 사용자 작업 손실 위험)
- `git worktree prune`으로 stale 메타데이터까지 청소

#### 3. starter 자체

starter엔 worktree 없음 (`git worktree list`로 확인). starter 측 정리
작업은 없음. 본 fix는 다운스트림 보호 메커니즘.

---

### F. installed_from_ref stale (다운스트림에서 발견)

**증상**: 다운스트림 `HARNESS.json`의 `installed_from_ref`가 0.26.8 시점이
아닌 한참 이전 값(`4ec2a98`). 이걸 base로 3-way merge 시 ADDED 60+개로
부풀려져 분류됨. 실제 0.26.8 starter 커밋(`f7463ce`)으로 재지정해야
ADDED 3개로 정확.

**원인 추정**: 이전 업그레이드 시 `installed_from_ref` 갱신이 누락됐을
가능성. starter `harness-upgrade` Step 10에서 갱신은 하지만, 어떤 시점에
꼬였는지 추적 불가.

**제안**:
- `harness-upgrade` Step 10에서 `installed_from_ref` 갱신 후 sanity check
  추가: `git cat-file -e $UPSTREAM_REMOTE/main` + 해당 ref가 upstream
  history에 실재하는지 확인. 없으면 경고.
- 또는 Step 1에서 `installed_from_ref`가 stale인지 확인하는 단계 추가
  — `git merge-base $UPSTREAM_REMOTE/main $installed_from_ref`가 통하는지
  체크. 통하지 않으면 사용자에게 재지정 요청.

---

## 정리

| ID | 이슈 | 우선순위 | 제안 |
|----|------|----------|------|
| A | threat-analyst.md secret false positive | ✅ v0.28.2 해결 | `S1_LINE_EXEMPT` 확장 — `incidents/hn_secret_line_exempt_gap.md` SSOT |
| B | `Bash(rm *)` 위험 권한 자동 추가 | 🟡 보안 | starter settings.json에서 제거 + 위험 패턴 사용자 승인 강제 |
| C | HARNESS_UPGRADE 환경변수 의미 일관화 | 🟠 일관성 | 우회 경로 SSOT 정리 — secret은 코드 면제로 분리됨 |
| D | CRLF/LF normalization 미비 | 🟡 호환성 | merge 전 LF 정규화 + .gitattributes |
| E | worktree 정책-실태 불일치 | 🟡 청결 | bash-guard 차단 + upgrade 시 clean 자동 정리 + dirty 안내 (.gitignore 추가는 정책 약화라 폐기) |
| F | installed_from_ref stale 감지 부재 | 🟢 안정성 | upgrade 시작 시 sanity check |
| G | Windows + 한글 환경 무한 막힘 | 🔴 회귀 차단 | 갈래 2 채택 — main 로직 함수화 + `if __name__ == "__main__":` 보호 (갈래 1 encoding="utf-8" 포함) |

## 메모

- 이 문서는 starter PR 작성용 입력 자료. 변경 적용은 starter 측이며,
  다운스트림은 후속 업그레이드에서 자연 흡수.
- **A는 v0.28.2 commit `f0e7a2c`로 해결됨** — 다운스트림은 fetch 후
  자연 해소. SSOT는 `incidents/hn_secret_line_exempt_gap.md`.
- B·D·E·F는 미해결. 영역별 logical unit이 다르므로 wave 단위 별 commit
  분리 권장 (security / encoding+hygiene / upgrade-safety).
- E·F는 다운스트림에서 자체 정리도 가능하나, starter 측 강제가 더 본질적.

### G. Windows + 한글 환경 무한 막힘 — script-as-module 결함

**증상**:
1. `pre_commit_check.py` import가 `subprocess.run(text=True, capture_output=True)`로 ✅
   git diff를 읽다가 cp949 디코딩 실패 → `stdout=None` → `splitlines()`
   AttributeError로 collection 단계 사망.
2. 디코딩이 통과해도 module-level main 로직이 staged 차단 검사를 돌려
   `sys.exit(2)`로 import가 끝남 → 모든 import 경로가 막힘.

본 sandbox에서 `pytest -m docs_ops` 등 import 경로가 전부 막혀 회귀
테스트 직접 실행 불가. `PYTHONUTF8=1` + 임시 repo subprocess로만 우회.

**원인 — 두 갈래**:

- **갈래 1 (디코딩 결함)**: `run()` 함수가 `encoding="utf-8"` 명시 없이
  `text=True`만 사용 → Windows에서 system locale(cp949) 적용. 한글
  staged diff에서 디코딩 실패.
- **갈래 2 (script-as-module 결함, 더 본질적)**: `pre_commit_check.py`가 ✅
  module-level에서 main 로직(staged 분석·차단 검사·sys.exit)을 직접 실행.
  test가 `from pre_commit_check import ENOENT_PATTERNS`만 해도 main이 돌고
  sys.exit. 갈래 1만 fix해도 staged 변경 있는 상태에서 import는 여전히 죽음.

**채택된 해결 — 갈래 2 (근본 리팩토링)**:

갈래 1만 적용하면 staged 변경 없을 때만 정상. 변경 있으면 import 시 main이
차단 검사 돌려 sys.exit. **갈래 2가 진짜 해소** — 갈래 1은 갈래 2 안에
포함시켜 같이 처리.

```python
# 정의만 module-level (test가 import 가능)
ENOENT_PATTERNS = ...
S1_LINE_PAT = ...
S1_LINE_EXEMPT = ...
# (run·err 등 helper도 module-level 유지)

def main() -> int:
    # 580줄의 main 로직 전부 이 안으로 (TEST_MODE 분기·git diff 호출·
    # 차단 검사·stdout 출력·return exit code)
    ...
    return 2 if ERRORS else 0

if __name__ == "__main__":
    sys.exit(main())
```

**작업 순서:**
1. ✅ **[Phase 1 완료, commit ab4c30c]** `run()` 함수에 `encoding="utf-8"` + `or ""` 방어 추가 (갈래 1). 검증: PYTHONUTF8 없이 한글 staged diff 처리 통과.
2. ✅ **[Phase 2 완료]** `pre_commit_check.py` main 로직 → `def main() -> int:` 함수화 + `if __name__ == "__main__": sys.exit(main())` 보호 (갈래 2).
   - ENOENT_PATTERNS만 module-level 유지 (test가 import). 입력 수집·검사·출력 580줄은 main() 안으로.
   - 회귀 가드: `TestModuleImportSafe::test_import_does_not_exit` 신규. staged 변경 유무 무관 import 후 sys.exit 발생 안 함 검증.
   - 종합 검증: `pytest -m "secret or gate or stage or enoent"` 27/27 통과.
3. **[Phase 3 예정]** 같은 패턴 일괄 점검:
   - `docs_ops.py`의 `subprocess.run` 호출 — encoding 누락? main 로직 module-level?
   - `harness_version_bump.py`·`task_groups.py`·기타 `.claude/scripts/*.py`

**위험도**: 2번이 main 로직 580줄 리팩토링 — 들여쓰기 변경 + 변수 스코프
영향. 변수가 `ERRORS += 1` 같이 module-level mutable에 의존하면 함수
스코프로 옮길 때 `nonlocal`/`global`/return 패턴 정리 필요. 회귀 가드
없이 진행 위험 → Phase 1(갈래 1) 별 commit + Phase 2(갈래 2) 별 commit
권장. Phase 1로 import 회귀 가드 테스트 먼저 추가 가능한지 확인.

---

## 메모 (보충)
