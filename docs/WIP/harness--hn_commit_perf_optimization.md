---
title: 커밋 파이프라인 현실화 — CPS·AC 기준 fast path와 side effect 정리
domain: harness
problem: P2
solution-ref:
  - S2 — "review tool call 평균 ≤4회 (부분)"
tags: [commit, performance, review-agent]
status: in-progress
created: 2026-04-18
updated: 2026-05-13
---

## 재개 사유 (2026-05-11)

2026-05-11 Codex 전환 커밋에서 커밋 스킬의 비용과 불안정성이 직접 드러났다.
커밋은 4개 sub-commit으로 분리됐지만, 실제 지연 원인은 분리 수 자체보다
**커밋 파이프라인이 CPS·AC 기준의 논리 단위가 아니라 절차·파일 그룹·hook
부작용에 끌려다닌 것**이었다.

실측된 마찰:

- `split-commit.sh` CRLF로 Bash 실행 실패
- PowerShell env가 Git Bash로 전달되지 않아 `HARNESS_DEV=1` 누락
- `pre_commit_check.py`와 git hook의 시크릿 예외 목록 불일치
- Bash push 경로에서 GitHub credential prompt를 못 읽어 timeout
- `commit_finalize.sh`의 `wip-sync`가 의도 밖 문서 이동·cluster 갱신을 발생시킴
- version bump·MIGRATIONS·README·hook repair가 본 커밋의 본질과 섞임

이 문서는 기존 "커밋 속도 최적화"를 재개해, 단순 시간 단축이 아니라
**CPS·AC 신경망을 기준으로 커밋 단위를 나누고 side effect를 통제하는 구조**로
재정의한다.

# 커밋 파이프라인 현실화

## 원칙

### 0. CPS는 두뇌, AC는 머슬이다

하네스의 지향점은 규칙을 많이 두는 것이 아니라, **CPS를 두뇌로 삼고 AC를
실행 근육으로 삼아 빠르게 판단하는 신경망**을 만드는 것이다.

- CPS: 무엇이 문제이고 어떤 Solution이 그 문제를 푸는지 판단하는 상위 맥락
- frontmatter: 이 작업이 어느 Problem·Solution에 연결되는지 선언하는 신경 접점
- domain/abbr: 문서·코드·cluster를 빠르게 찾게 하는 인덱스 신경
- AC: 판단을 행동과 검증으로 바꾸는 근육
- pre-check/review/hook: 근육이 실제로 움직였는지 확인하는 반사 신경
- commit log: 어떤 판단이 어떤 행동으로 닫혔는지 남기는 기억

따라서 커밋 파이프라인이 느리거나 불안정하다는 것은 단순 UX 문제가 아니다.
**두뇌(CPS)에서 근육(AC)으로 내려간 명령이 side effect와 파일 그룹화에 가려져
제대로 전달되지 않았거나, 실행 결과가 다시 두뇌로 상향 피드백되지 않았다는
신호**다.

### 1. 커밋의 기본 단위는 파일 그룹이 아니라 CPS·AC다

하네스의 목표는 파일을 예쁘게 나누는 것이 아니라, **CPS Problem → Solution
충족 기준 → WIP AC → 검증 흔적 → commit log**가 하나의 신경망으로 이어지게
하는 것이다.

따라서 커밋 분리의 1차 기준은 다음 순서다:

1. 같은 `problem`·`solution-ref`를 충족하는가
2. 같은 AC Goal을 닫는가
3. 검증 명령과 실측 조건이 같은가
4. side effect가 해당 AC의 자연스러운 부산물인가
5. 아니라면 별도 커밋 또는 별도 WIP가 필요한가

파일 경로·성격(`exec/doc/skill/misc`)은 2차 신호다. 파일 그룹은 유용한
힌트지만, 논리 단위를 대신하면 안 된다.

### 2. AC는 커밋 전 체크리스트가 아니라 커밋 경계다

현재 AC는 주로 pre-check 통과 조건으로 쓰인다. 개선 후 AC는 다음 역할을
동시에 가져야 한다:

- 커밋에 포함될 변경의 경계 선언
- 자동 실행할 검증 명령 선언
- side effect 허용 범위 선언
- review stage 결정의 1차 근거
- commit message의 추적성 라인 근거

즉 `/commit`은 "staged 파일을 어떻게 처리할까"가 아니라
"이 staged 변경이 어떤 AC를 닫는가"부터 계산해야 한다.

### 2.5. 하향·상향 cascade가 모두 닫혀야 한다

현재 설계는 이미 하향과 상향을 갖고 있다.

하향 경로:

```text
CPS Problem/Solution
→ Rules/Skills/Agents/Scripts defends·serves·trigger
→ WIP frontmatter problem/solution-ref
→ AC Goal + 검증 묶음
→ staged 변경
→ commit
```

상향 경로:

```text
실행 결과·테스트·hook·pre-check·review
→ side effect ledger
→ WIP AC 체크/미체크
→ incident/decision/harness 문서
→ CPS Problem/Solution 보강 여부 판단
```

이번 커밋 경험은 이 cascade가 충분히 빠르고 정확하게 닫히지 않았다는 증거다.
예를 들어 hook 예외 목록 불일치는 pre-check과 hook이 같은 Solution을
방어한다고 선언했지만 실제 신경 연결이 끊긴 상태였다. `split-commit.sh`
CRLF와 PowerShell→Bash env 전달 실패는 실행 근육이 OS 경계에서 끊긴 사례다.
`wip-sync`의 의도 밖 문서 이동은 side effect가 상향 보고 없이 근육을 움직인
사례다.

개선 후 `/commit`은 다음 질문을 빠르게 통과해야 한다:

1. 하향: 이 변경은 어떤 CPS Problem·Solution에서 내려왔는가
2. 하향: 해당 frontmatter/domain/abbr/cluster 연결이 살아 있는가
3. 실행: 어떤 AC Goal을 닫는가
4. 실행: 자동 검증과 실측이 그 AC에 대응하는가
5. side effect: 자동 변경은 필수·릴리즈·수리 중 무엇인가
6. 상향: 실행 결과가 WIP, commit log, incident/decision, CPS 중 어디로 귀환해야 하는가

이 6문항이 빠르게 계산되지 않으면, 지금 하네스의 신경망 목표가 작동하지
않는 것으로 본다.

### 3. side effect는 숨기지 말고 세 종류로 분류한다

커밋 중 발생하는 자동 변경은 모두 side effect다. side effect를 없애는 것이
목표가 아니라, **어느 CPS·AC에 붙는 부산물인지 명시적으로 분류**해야 한다.

| 분류 | 의미 | 처리 |
|------|------|------|
| 필수 부산물 | AC 충족에 필요한 메타 변경 | 같은 커밋에 포함 |
| 릴리즈 부산물 | version bump, README, MIGRATIONS | release path에서만 자동 포함 |
| 수리 부산물 | hook CRLF, auth/env, SSOT 불일치 fix | 별도 repair 커밋 또는 별도 WIP |

오늘 커밋에서 hook 예외 동기화는 수리 부산물이었다. 이를 Codex agent 브리지
커밋에 섞은 것은 현실적으로 필요했지만, 원칙상 `/commit`이 "수리 부산물
발생"을 별도 신호로 표시했어야 한다.

Gemini 피드백 반영: ledger만으로는 부족하다. `docs_ops.py`가 의도 밖 문서
이동을 만들었다면 "기록했으니 됐다"가 아니라, 왜 이동했는지 root cause를
상향 보고해야 한다.

side effect 분류 기준:

| 질문 | yes면 |
|------|-------|
| 이 변경이 AC Goal을 만족하지 못하면 실패인가 | 필수 부산물 |
| 다운스트림 배포 단위의 버전·마이그레이션 알림인가 | 릴리즈 부산물 |
| 현재 커밋을 가능하게 하려고 파이프라인·hook·환경을 고친 것인가 | 수리 부산물 |
| 위 셋 중 어디에도 안 들어가나 | 스코프 외 변경. stage 제외 또는 별도 WIP |

수리 부산물은 기본적으로 별도 커밋이다. 사용자가 "같이"라고 명시한 경우에도
커밋 메시지에 `repair-side-effect:` 한 줄을 남긴다.

### 4. fast path와 release path를 분리한다

모든 커밋이 release 커밋은 아니다. 기본 커밋은 빠르게 끝나야 한다.

| 경로 | 목적 | 실행 항목 |
|------|------|-----------|
| fast path | 작업 중 자주 쓰는 커밋 | pre-check 핵심, AC 명령, wrapper commit |
| review path | 위험 변경 검증 | fast + review |
| release path | starter 배포 단위 | review + version bump + MIGRATIONS + push |
| repair path | 커밋 파이프라인 자체 고장 수리 | 최소 pre-check + hook/env 수리 기록 |

사용자가 "일단 지금까지 커밋"이라고 하면 기본은 fast/review path다.
starter 버전 bump가 필요하더라도 명확한 patch는 자동 처리하되, 그것이
release path 전체를 강제한다는 뜻은 아니다.

## 개선안

### 구현 단위 요약

이 문서의 변경은 선언이 아니라 아래 파일을 실제로 바꾸는 작업으로 닫는다.

| 파일 | 변경할 내용 | 성공 기준 |
|------|-------------|-----------|
| `.agents/skills/commit/SKILL.md` | Step 순서를 `판정 → 차단/경고 분리 → side effect 분류 → 필요 시 승격`으로 재작성 | 기본 `/commit` 설명에서 자동 split·release·deep review가 기본값처럼 읽히지 않음 |
| `.claude/scripts/pre_commit_check.py` | `commit_mode_recommended`, `blocking_reasons`, `warning_reasons`, `side_effect_candidates` 출력 추가 | 스크립트 1회 실행만으로 commit이 다음 행동을 결정 가능 |
| `.claude/scripts/split-commit.sh` | `split_action_recommended=split`이어도 기본은 계획 출력만 하고 stage 변경하지 않도록 변경 | 사용자가 "지금까지"라고 한 커밋에서 자동 분리로 시간을 쓰지 않음 |
| `.claude/scripts/commit_finalize.sh` | `docs_ops.py wip-sync` 결과를 `side_effects.required`로 감싸서 출력 | WIP 이동·cluster 갱신이 숨은 변경으로 남지 않음 |
| `.claude/scripts/docs_ops.py` | `wip-sync` stdout에 변경 종류를 key-value로 추가 | commit 스킬이 WIP 갱신·이동·cluster 갱신을 ledger로 요약 가능 |
| `.claude/scripts/harness_version_bump.py` | version bump 결과에 release 승격 필요 여부를 출력 | patch bump와 release 문서 갱신이 무조건 한 덩어리로 실행되지 않음 |
| `.claude/scripts/tests/test_pre_commit.py` | 위 출력 스키마와 기본 경로 회귀 테스트 추가 | fast-by-default가 말이 아니라 테스트로 고정됨 |

새 CLI 옵션은 1차 산출물이 아니다. 필요하면 나중에 alias로 붙일 수 있지만,
먼저 고칠 것은 **기본 `/commit`이 한 번의 pre-check 결과를 보고 스스로
가벼운 경로와 무거운 경로를 판정하는 것**이다.

### 기본 판정 알고리즘

`/commit`은 `pre_commit_check.py` stdout을 한 번 읽고 다음 순서로 결정한다.

```text
1. blocking_reasons가 있으면 중단
2. side_effect_candidates를 required/release/repair로 분류
3. repair가 있으면 repair 커밋 제안. 사용자가 "같이"라고 이미 말했으면 진행
4. release가 있고 is_starter=true이면 release 승격
5. split_action_recommended=split이면 split 계획만 출력
6. 사용자가 분리 요청을 명시하지 않았으면 single로 진행
7. review 하향은 정량 risk factor가 모두 낮을 때만 허용
8. 하향·승격·skip된 검증·AC 혼합 여부를 사용자에게 1줄씩 출력
```

출력 예:

```text
commit_route: single
review_route: micro
promotion: none
blocking_reasons: none
warning_reasons: split recommended but user requested current snapshot
skipped_checks: deep-review
risk_factors: files=1, sensitive_paths=none, secret=line-none, side_effects=required-only
commit_tags: AC-MIXED
side_effects.required: docs_ops.wip-sync
side_effects.release: none
side_effects.repair: none
```

이 출력이 없으면 구현 실패다. 사람이 문서를 읽고 추론해야 하는 상태를
끝내는 것이 이번 개선의 목표다. 특히 Gemini 피드백을 반영해, `review-deep`
하향은 에이전트의 감각이 아니라 `risk_factors`가 낮다는 객관 신호로만
허용한다.

### A. 기본 커밋 프로세스 재설계 — fast-by-default

목표: 사용자가 별도 서브 명령어를 외우지 않아도, 일반 커밋의 체감 시간을
1분 안쪽으로 낮춘다.

핵심은 `/commit --fast` 같은 옵션을 추가하는 것이 아니다. 문제는 명령어가
부족한 것이 아니라, 기본 커밋 프로세스가 CPS·AC 판단보다 절차·파일 그룹·리뷰
관성에 먼저 끌려가는 데 있다. 따라서 기본 `/commit` 자체가 다음 순서로
동작해야 한다:

1. staged 변경이 닫는 CPS·AC를 먼저 판정
2. 차단 조건과 경고 조건을 분리
3. side effect를 필수·릴리즈·수리로 분류
4. release/review/repair가 필요한 경우에만 무거운 경로로 승격
5. 승격 사유를 한 줄로 설명

동작:

- `pre_commit_check.py` 1회 실행
- AC `검증.tests`·`검증.실측` 중 화이트리스트 명령 실행
- split은 **권고 출력만** 하고 자동 분리하지 않음
- review는 AC `review: review-deep`이더라도 실제 diff·risk·side effect가
  deep 조건을 만족하지 않으면 `self` 또는 `micro`로 낮춤. 단, 낮춘 이유를
  출력한다.
- version bump는 patch 제안이면 자동 반영할 수 있지만, MIGRATIONS 상세 작성과
  push 검증은 release 승격 조건이 있을 때만 수행한다.

금지:

- 시크릿 line-confirmed, CPS frontmatter 누락, AC 필수 필드 누락은 fast에서도
  우회 불가

### B. release 승격 조건 명시

목표: 다운스트림에 전파되는 starter 배포 커밋만 무거운 절차를 탄다.

release도 사용자에게 서브 명령어를 떠넘기는 방식이 아니라, 커밋 프로세스가
"이 변경은 배포 단위인가?"를 판정하고 필요할 때 명시적으로 승격하는 구조여야
한다.

동작:

- version bump 확정
- MIGRATIONS/README 작성
- review stage 자동 판정 유지
- push까지 수행
- 완료 후 remote SHA 대조

release path는 느려도 된다. 대신 fast path가 release 비용을 매번 떠안지
않아야 한다.

### C. split 정책 재정의 — "CPS·AC 먼저, 파일 성격 나중"

현재 split은 파일 성격과 WIP 매칭에 강하게 의존한다. 개선 후 split 판정은:

1. staged 변경이 여러 WIP의 서로 다른 AC Goal을 닫으면 split
2. 같은 WIP라도 서로 다른 AC Goal이 독립 검증 명령을 가지면 split
3. side effect가 필수 부산물이 아니면 별도 repair/release 커밋 제안
4. 파일 성격 혼재는 경고 신호로만 사용
5. 사용자가 "통째로" 또는 "지금까지"를 말하면 단일 커밋 허용. 단, 차단
   신호는 그대로 차단

이 원칙은 `hn_commit_process_audit.md` #18의 "완전 자동 분리 마찰 증가"와
정합한다. 자동 분리는 조력자여야지 커밋의 주인이 되면 안 된다.

Gemini 피드백 반영: single 허용은 fat commit 위험을 없애지 않는다. 따라서
split 권고가 있었는데도 single로 진행하면 커밋 메시지에 `AC-MIXED` 태그와
혼합 사유를 남긴다.

```text
commit_tags: AC-MIXED
mixed_reason: split recommended, user requested current snapshot
```

이 태그는 차단이 아니라 사후 audit 신호다. 나중에 revert/cherry-pick이
어려웠던 커밋을 찾을 수 있어야 한다.

### D. hook/pre-check SSOT 통합

오늘 가장 명확한 결함은 pre-check과 git hook의 시크릿 예외 목록 불일치였다.

개선 방향:

- 시크릿 패턴과 예외 목록을 `pre_commit_check.py`에만 정의
- hook 설치 스크립트는 그 정의에서 hook block을 생성
- 현재 설치된 `.git/hooks/pre-commit`도 생성물로 취급
- 회귀 테스트: `.codex/agents/**`, `.agents/skills/**`의 문서화된 시크릿
  예시가 pre-check과 hook 양쪽에서 동일하게 면제되는지 검증

### E. Windows/Git Bash 생존성 테스트

커밋 파이프라인은 Windows + Git Bash에서 실제로 살아야 한다.

추가할 smoke:

- `split-commit.sh` CRLF 상태에서도 실행 전 정규화 또는 명확한 실패 메시지
- PowerShell → Git Bash env 전달 경로 검증
- `.git/hooks/pre-commit` shebang CRLF 검사
- Bash push credential 실패 시 Windows Git push fallback 안내
- `commit_finalize.sh`가 author identity 실패 전에 repo-local git config를
  진단

Gemini 피드백 반영: OS 경계 마찰은 repair path로 기록만 해서는 부족하다.
반복되는 CRLF/env/shebang 문제는 `repair`가 아니라 사전 차단 또는 자동
정규화 대상이다.

실행 환경 원칙:

- shell script 실행 전 CRLF 검사. hit 시 실행하지 않고 정규화 안내 또는 자동 정규화.
- PowerShell에서 Bash로 넘기는 `VAR=1 command` 문법 금지. Windows 실행문은
  `$env:VAR='1'; command`로 별도 출력.
- hook shebang CRLF는 pre-check 단계에서 차단.
- push는 Git Bash credential prompt timeout을 감지하면 Windows Git fallback을
  즉시 제안한다.

### F. side effect ledger 출력

`/commit`은 최종 요약 전에 이번 커밋 중 자동 발생한 side effect를 출력한다.

예:

```text
side_effects:
  required:
    - docs_ops wip-sync: docs/clusters/harness.md 갱신
  release:
    - HARNESS.json 0.43.2 → 0.43.3
    - MIGRATIONS.md 새 섹션
  repair:
    - pre-commit hook CRLF 정규화
    - hook secret exempt SSOT 불일치 수정
```

이 ledger가 있어야 사용자가 "왜 이 파일이 같이 들어갔는가"를 즉시 판단할 수
있다. ledger 항목 중 `repair`가 있으면 기본은 별도 커밋 제안이다.

### G. Cascade Integrity Check 추가

커밋 속도 개선은 cascade 검증을 약화시키면 실패다. fast path도 최소한의
신경망 무결성 검사는 통과해야 한다.

검사 항목:

| 축 | 질문 | 실패 시 |
|----|------|---------|
| CPS | `problem`이 CPS Problems에 존재하는가 | 차단 |
| Solution | `solution-ref`가 CPS Solutions 원문과 매칭되는가 | 경고 또는 차단 후보 |
| Domain | `domain`이 naming.md 확정 목록에 있는가 | 차단 |
| Abbr | 파일명 abbr이 domain과 일치하는가 | 차단 |
| Cluster | completed/WIP 문서가 cluster에서 발견 가능한가 | 경고 |
| AC | Goal/review/tests/실측 4필드가 있는가 | 차단 |
| Trigger | 관련 scripts/rules/skills가 `defends`·`serves`·`trigger`로 연결되는가 | 경고 |
| Side effect | 자동 변경이 필수/릴리즈/수리 중 하나로 분류됐는가 | 경고, repair는 별도 커밋 제안 |
| Upward feedback | 새 결함이면 incident 또는 CPS 보강 후보가 기록됐는가 | 경고 |

이 검사는 "더 많이 읽기"가 아니라 **이미 있는 frontmatter와 MAP, naming,
AC를 작은 key-value로 대조하는 빠른 판단**이어야 한다. 목표는 deep review를
대체하는 것이 아니라, deep review가 보기 전에 신경망 단선 여부를 즉시
알려주는 것이다.

### H. 작업 순서

구현은 다음 순서로 한다. 이 순서를 어기면 다시 "문서상 원칙은 맞는데 실제
커밋은 느린" 상태가 된다.

1. `pre_commit_check.py`에 route 출력만 추가한다.
   - 기존 차단 로직은 건드리지 않는다.
   - 새 출력: `commit_route`, `review_route`, `promotion`,
     `blocking_reasons`, `warning_reasons`, `side_effects.*`.
   - 테스트: stdout parser가 새 key를 읽고, 기존 key와 공존하는지 확인.

2. `commit/SKILL.md`를 route 소비 방식으로 줄인다.
   - Step 4 version bump는 무조건 실행 절차가 아니라 `promotion=release`
     일 때 실행하는 절차로 이동한다.
   - Step 5.5 split은 자동 stage 변경이 아니라 계획 출력이 기본이다.
   - review 호출은 `review_route`를 따른다.

3. `split-commit.sh`를 destructive planner에서 non-destructive planner로 바꾼다.
   - 기본 실행은 staged를 비우지 않는다.
   - `--apply`가 있을 때만 기존처럼 첫 그룹 stage 변경을 수행한다.
   - commit 스킬은 사용자 명시 분리 요청이 있을 때만 `--apply`를 쓴다.

4. `commit_finalize.sh`와 `docs_ops.py`에 side effect ledger를 붙인다.
   - `docs_ops.py wip-sync`는 `wip_sync_updated`, `wip_sync_moved`,
     `cluster_updated`, `backrefs_updated`를 stdout으로 낸다.
   - `commit_finalize.sh`는 이를 `side_effects.required`로 다시 출력한다.

5. `harness_version_bump.py`를 release 승격 신호로 제한한다.
   - 문서만 바뀐 커밋에서는 `promotion: none`.
   - starter 배포 영향이 있는 변경에서만 `promotion: release`.
   - release일 때만 MIGRATIONS/README 갱신 절차를 탄다.

6. Windows smoke를 테스트 또는 스크립트로 고정한다.
   - CRLF hook/shebang 검사.
   - PowerShell에서 `HARNESS_DEV=1`이 Git Bash로 전달되는지 검사.
   - Bash push 실패 시 Windows Git fallback 문구 확인.

### I. 이번 경험에서 바로 고칠 판정식

2026-05-11 커밋에서 실제로 터진 문제는 다음 판정식으로 막는다.

| 증상 | 새 판정식 | 결과 |
|------|-----------|------|
| CRLF로 `split-commit.sh` 실행 실패 | `file_has_crlf(.claude/scripts/*.sh)` | `blocking_reasons` 또는 `repair` |
| PowerShell env가 Git Bash로 안 넘어감 | `shell_context=PowerShell && command_prefix contains VAR=1` | Windows 전용 실행문 출력 |
| pre-check과 hook 시크릿 예외 불일치 | `hook_secret_exempt_hash != precheck_secret_exempt_hash` | `repair` |
| Bash push credential timeout | `push_failed && shell=GitBash && auth_prompt_detected` | Windows Git fallback |
| `wip-sync`가 문서 이동 발생 | `wip_sync_moved > 0` | `side_effects.required` 출력 |
| version bump와 본 커밋 혼재 | `version_bump != none && promotion != release` | bump만 stage하지 않음 |
| Gemini CLI argv/stdin/도구 mismatch | `gemini_result contains run_shell_command not found or quota/capacity` | `warning_reasons` + 결과 파일 확인 |

### J. Gemini 피드백 흡수 방식

기존 SSOT는 `docs/decisions/hn_gemini_delegation_pipeline.md`다. 이 문서는 이미
다음 제약을 박제하고 있었다.

- Q4: Gemini CLI는 컨텍스트 한도가 커도 argv/stdin shell 제한이 있으므로
  큰 컨텍스트는 임시 파일 경유가 필요하다.
- Q6: timeout·quota·무용 응답은 커밋을 막지 않고 graceful degradation으로
  처리한다.
- 사각지대: Gemini CLI 비결정성, OAuth quota 미실측, CLI 미설치 환경,
  false-positive detect.

이번 실측은 그 제약을 더 구체화한다. 단, 중요한 것은 Gemini 원문을 남기는
것이 아니라 **반영할 판단만 WIP의 판정식과 AC로 흡수하는 것**이다.

```text
Ripgrep is not available. Falling back to GrepTool.
Error executing tool run_shell_command: Tool "run_shell_command" not found.
Attempt 1 failed: You have exhausted your capacity on this model...
```

해석:

- `Ripgrep is not available`은 Gemini CLI 실행 환경의 검색 도구 경고다.
  하네스의 `rg` 사용 가능 여부와 별개로, Gemini 내부가 `GrepTool`로 fallback한
  상태다.
- `run_shell_command not found`는 Gemini가 기대한 shell tool 이름과 현재
  CLI/확장 도구 목록이 맞지 않는 상태다. 이는 하네스 hook failure가 아니라
  Gemini CLI agent runtime/tool schema mismatch다.
- `capacity` 메시지는 Gemini 모델 quota/용량 재시도 신호다. 자동 위임은 이
  상태를 차단으로 올리면 안 되고, 결과 파일에 실패 근거를 남긴 뒤 진행해야
  한다.

따라서 commit route에서 Gemini 결과는 다음처럼 소비한다.

| 결과 상태 | commit 영향 | 기록 |
|-----------|-------------|------|
| 정상 응답 | 피드백 중 채택 항목만 WIP 판정식·AC에 반영 | 원문 보존 없음 |
| `run_shell_command not found` | 차단하지 않음 | Gemini tool mismatch 경고 |
| quota/capacity | 차단하지 않음 | Gemini quota 경고 |
| timeout | 차단하지 않음 | `[gemini-timeout]` |
| 결과 파일 없음 | 차단하지 않음 | Gemini skip |

이 원칙은 `hn_session_false_completion` incident의 교훈과도 맞다. 자동 Gemini
트리거는 보조 신호일 뿐이며, "Gemini를 불렀다"를 "검증이 끝났다"로 말하면
다시 거짓 완료가 된다.

이번 Gemini 피드백에서 WIP에 반영한 항목:

| Gemini 지적 | 문서 반영 위치 |
|-------------|----------------|
| review 하향은 주관 판단이면 위험 | 기본 판정 알고리즘 `risk_factors` 조건 |
| single 강행은 fat commit 위험 | split 정책 `AC-MIXED` 태그 |
| side effect ledger만으로는 부족 | side effect root cause 상향 보고 |
| OS 경계 문제는 논리 재설계만으로 해결 안 됨 | Windows smoke의 사전 차단·정규화 원칙 |
| Fast Path는 skip된 검증을 알려야 함 | route 출력 `skipped_checks` |

세션 scratch 정책:

- Gemini 자동 리뷰는 영속 문서가 아니다.
- 결과와 prompt는 `.claude/memory/session-gemini-*`에만 저장한다.
- `session-*`는 기존 `.gitignore` 대상이므로 커밋에 섞이지 않는다.
- 매 호출은 같은 파일을 덮어쓴다. 누적 파일을 만들지 않는다.
- hook 경로는 원문 저장을 필수로 하지 않는다. 장기 목표는 Gemini 자동 호출을
  PreToolUse에서 빼고, 필요 시 commit/review 단계에서 명시 실행하는 것이다.
- 현재 구현도 같은 방향으로 둔다. PreToolUse 기본값은 Gemini 자동 호출·신호
  모두 off이고, `HARNESS_GEMINI_AUTO=1`일 때만 백그라운드 worker와 INFO
  신호를 띄운다. 기본 hook은 조용해야 한다.
- commit 스킬은 Gemini 원문을 자동 첨부하지 않는다. 채택한 판단만 WIP 또는
  commit warning에 반영한다.

## 현재 분리된 작업을 어떻게 나눌 것인가

이번 개선은 한 커밋으로 묶으면 다시 같은 문제가 난다. 다음 WIP 또는
sub-task로 분리한다.

### 1. 기본 route 출력 도입

범위:

- `.claude/scripts/pre_commit_check.py`
  - 기존 stdout 아래에 `commit_route`, `review_route`, `promotion`,
    `blocking_reasons`, `warning_reasons`, `side_effects.*` 추가
  - `recommended_stage=deep`이어도 docs-only·단일 WIP·side effect 없음이면
    `review_route=micro` 또는 `self`를 낼 수 있게 판정식 추가
- `.claude/scripts/tests/test_pre_commit.py`
  - docs-only WIP 1건 → `commit_route=single`, `promotion=none`
  - split 추천 케이스 → `warning_reasons`에만 남고 차단하지 않음
  - 시크릿 line-confirmed → 여전히 `blocking_reasons`로 차단

AC:

- docs-only 또는 단일 WIP 커밋에서 pre-check 1회만으로 route가 결정된다
- 시크릿·CPS·AC 필수 필드는 계속 차단

### 2. commit 스킬 route 소비

범위:

- `.agents/skills/commit/SKILL.md`
  - Step 4를 "항상 version bump 확인"에서 "`promotion=release`일 때 release
    갱신"으로 이동
  - Step 5.5 split을 "자동 분리 실행"에서 "계획 출력, 사용자 명시 시 적용"으로 변경
  - Step 7 review 호출은 `review_route`를 따른다고 명시
  - push 전 요약에 route와 승격 사유를 출력하도록 명시

AC:

- 일반 `/commit` 문서 경로에서 version bump·MIGRATIONS·README가 자동 필수처럼
  읽히지 않는다
- release 승격 시에만 `origin/main` SHA 대조가 최종 요약에 포함된다

### 3. split-commit 비파괴화

범위:

- `.claude/scripts/split-commit.sh`
  - 기본 실행: split plan만 출력하고 staged 상태 유지
  - `--apply`: 기존처럼 첫 그룹만 stage하는 destructive 동작 수행
  - CRLF 감지 시 실행 전에 명확한 오류 또는 자동 정규화 안내
- `.claude/scripts/tests/test_pre_commit.py`
  - 기본 split 실행 후 `git diff --cached --name-only`가 변하지 않는지 확인
  - `--apply`에서만 staged set이 바뀌는지 확인

AC:

- split 추천이 있어도 사용자가 명시하지 않으면 staged 변경이 바뀌지 않는다
- "지금까지 커밋" 요청은 single route로 진행 가능하다

### 4. Side Effect Ledger

범위:

- `.claude/scripts/docs_ops.py`
  - `wip-sync` stdout에 `wip_sync_updated`, `wip_sync_moved`,
    `cluster_updated`, `backrefs_updated` 추가
- `.claude/scripts/commit_finalize.sh`
  - 위 출력을 받아 `side_effects.required`로 재출력
- `.agents/skills/commit/SKILL.md`
  - ledger에 `required/release/repair`가 하나라도 있으면 최종 요약에 표시

AC:

- wip-sync, version bump, hook repair가 서로 다른 줄로 출력된다
- repair side effect가 발생하면 별도 커밋 제안 또는 사용자 명시 포함 근거가 남는다

### 5. Hook/Pre-check SSOT

범위:

- `.claude/scripts/pre_commit_check.py`
  - 시크릿 패턴·예외 목록을 함수로 노출
- `.claude/scripts/install-starter-hooks.sh`
  - hook block을 위 SSOT에서 생성하거나 동일 fixture를 사용
- `scripts/install-secret-scan-hook.sh`
  - 같은 예외 목록 사용
- `.claude/scripts/tests/test_pre_commit.py`
  - `.codex/agents/**` 예시 패턴 면제 테스트 추가
  - hook 생성물과 pre-check 예외 hash가 같은지 확인

AC:

- pre-check 통과 후 hook에서 같은 사유로 차단되는 사례 0건
- 예외 목록 변경 시 테스트가 깨진다

### 6. Windows Commit Smoke

범위:

- 새 스크립트 후보: `.claude/scripts/commit_smoke_windows.sh`
  - CRLF, hook shebang, git identity, PowerShell→Git Bash env 전달 검사
  - push credential 실패 메시지에 Windows Git fallback 안내 포함
- `.claude/scripts/tests/test_pre_commit.py`
  - 최소한 CRLF/shebang/env 문자열 검증은 단위 테스트로 고정

AC:

- Windows + Git Bash에서 commit dry-run smoke 통과
- 실패 시 사용자가 취할 다음 행동이 한 줄로 출력

### 7. Cascade Integrity Check

범위:

- `.claude/scripts/pre_commit_check.py`
  - CPS/frontmatter/domain/abbr/cluster/AC/trigger/side effect/upward feedback
    대조 결과를 기존 검사와 중복 없이 `warning_reasons`에 추가
  - 차단/경고/제안 세 등급으로 분리
- `.claude/HARNESS_MAP.md`
  - 필요한 경우 commit 관련 `defends-by`·`enforced-by` edge 보강

AC:

- 문서 WIP 1건, 코드+문서 혼합 1건, hook repair 1건에서 cascade check 결과가
  사람이 납득 가능한 요약으로 출력
- 기존 `pre_commit_check.py`의 CPS·AC 검사를 중복하지 않고 확장 신호로 제공

**Acceptance Criteria**:

- [ ] Goal: 커밋 파이프라인을 CPS·AC 기준의 빠른 기본 경로와 명시적 release 경로로 나누고, side effect를 숨기지 않고 분류한다.
  검증:
    review: review-deep
    tests: 없음
    실측: python .claude/scripts/pre_commit_check.py
- [ ] `pre_commit_check.py`가 `commit_route`·`review_route`·`promotion`·`side_effects.*`를 출력한다. ✅
- [ ] `commit/SKILL.md`가 route 출력 소비 방식으로 재작성된다. ✅
- [ ] `split-commit.sh` 기본 실행이 staged 상태를 바꾸지 않는 non-destructive planner가 된다. ✅
- [ ] split 판정이 파일 성격보다 CPS·AC Goal을 우선하도록 재정의된다.
- [ ] hook/pre-check 시크릿 예외 목록이 단일 SSOT에서 생성되도록 설계된다.
- [ ] side effect ledger 포맷이 정해지고, wip-sync/version bump/hook repair가 구분된다.
- [ ] Windows + Git Bash 실행 안정성 smoke 항목이 문서화된다.
- [ ] Cascade Integrity Check가 CPS·frontmatter·domain·abbr·cluster·AC·trigger·side effect·상향 피드백 누락을 빠르게 대조하도록 정의된다.

## 변경 이력

- 2026-05-11: Codex 전환 커밋 실측을 근거로 기존 속도 최적화 문서를 재개.
  단순 review 비용 문제가 아니라 CPS·AC 경계, side effect 분류, fast/release
  path 분리가 핵심임을 반영.
- 2026-05-11: CPS=두뇌, AC=머슬 관점과 하향·상향 cascade 무결성 검증을
  핵심 개선 범위에 추가.

---

## ✅ 완료 (2026-04-19)

- §2 pre-check → 리뷰 데이터 전달 (커밋 11fe9f2, v1.4.1)
- §1 단계 조건부 실행 + §3 모델 스위치는 **review staging 시스템(v1.6.0,
  84ad413)이 흡수**:
  - Stage 0~3 분기로 단계 조건부 실행 일반화
  - Stage 1~3별 시간·tool 한도가 모델 선택과 같은 효과
- §4 시간 리포팅은 **별도 후속으로 분리** →
  `WIP/harness--hn_commit_process_audit.md` #13(5커밋 측정)으로 통합

# 커밋 속도 최적화

## 배경

v1.3.2에서 pre-check을 Step 5로 조기 실행하면서 "LLM 호출 전 정적 차단" 경로를
확보. 그러나 다음 경로에서 여전히 불필요한 비용/중복이 발생한다:

1. **불필요한 단계 진입**: WIP이 없는 커밋도 Step 2(계획 문서 처리)가 전수 검사
2. **중복 검증**: pre-check이 이미 잡은 항목(린터, TODO 등)을 리뷰 agent가 재확인할 위험.
   현재는 review.md 문서 지시로만 막음 — 데이터로 강제되지 않음
3. **리뷰의 포커스 부재**: 위험 요인을 pre-check이 감지해도 리뷰 agent는 그 힌트 없이
   전체 diff를 일반 검증 — 집중 지점이 불명확
4. **모델 오버스펙**: 작은 문서 수정에도 `model: sonnet` 고정

## 제안

### 1. 단계 조건부 실행 (gate)

각 단계 진입 전 필요성 검사. 미해당 시 스킵.

| 단계 | 실행 조건 |
|------|-----------|
| 2. 계획 문서 완료 처리 | `git diff --cached --name-only`에 `docs/WIP/` 포함 |
| 3. 하네스 버전 체크 | `.claude/*`, `scripts/*` 변경이 있을 때 (harness-starter 한정) |
| 7. 리뷰 Agent | strict 모드 또는 pre-check 위험 감지 hit 시 |

### 2. pre-check → 리뷰 데이터 전달 (인메모리 전달)

**방식**: 파일/환경변수 저장 없이, commit 스킬이 pre-check을 Bash로 실행한 후
**그 stdout/stderr 출력을 메모리(스킬 컨텍스트)에 담고 바로 리뷰 agent prompt에 포함**.

근거: 리뷰 호출은 같은 커밋 시퀀스 내에서 이어지는 단일 흐름. 파일 경유는
I/O 낭비 + 크로스플랫폼 경로 고민 + 잔여 파일 정리 부담.

**pre-check이 stdout으로 출력할 요약 포맷** (stderr는 사용자 노출용, stdout은
스킬 전달용으로 분리):

```
pre_check_passed: true
already_verified: lint, todo_fixme, test_location, wip_cleanup
risk_factors: 핵심 설정 파일 변경 (.claude/settings.json), 보안 패턴 감지 (token), 삭제 67줄
diff_stats: files=3, +42 -67
```

단순 key-value 라인 형식. JSON도 가능하지만 셸에서 더 간단한 문자열이 빠름.
Agent tool prompt에 그대로 붙여넣기만 하면 agent가 읽어낼 수 있음.

**commit 스킬 Step 7에서**: Agent tool 호출 prompt에 다음 블록 삽입:
```
## pre-check 결과
<pre-check stdout 내용 그대로 붙여넣기>

## 지시
위 risk_factors에 우선순위를 두고 3관점(회귀/계약/스코프) 검증하라.
already_verified 항목은 재검사 마라.
```

### 3. 리뷰 모델 스위치

리뷰 agent의 모델을 diff 규모 + 위험 요인 기반으로 동적 지정.

| 조건 | 모델 |
|------|------|
| 문서만 변경 (*.md, docs/) 또는 ≤ 50줄 | haiku |
| 일반 코드 변경 ≤ 200줄, 위험 요인 없음 | haiku |
| > 200줄, 또는 risk_factors 비어있지 않음 | sonnet |

**구현**: review.md frontmatter의 `model: sonnet` 제거. 커밋 스킬이 Agent tool 호출 시
`model` 파라미터 동적 지정. Agent tool이 이 파라미터를 받는지 먼저 확인 필요.

## 의존성

- pre-commit-check.sh에 **요약 라인을 stdout으로 추가 출력**. 기존 stderr(사용자
  대상 에러 메시지)는 그대로 두고 stdout 채널을 요약 전달용으로 분리.
- SKILL.md Step 5: pre-check을 Bash로 실행할 때 stdout을 변수에 캡처하도록 명시
- SKILL.md Step 7: 캡처한 stdout을 Agent tool prompt에 삽입하도록 명시
- review.md: "prompt에 pre-check 결과 블록이 있으면 already_verified 재검사 금지"
  명시

### 4. 전체 소요 시간 리포팅

커밋 완료 후 스킬이 전체/단계별 소요 시간을 간결히 표시:

```
⏱  전체 1m 2s (pre-check 0.3s / review 58s / commit 3.7s)
```

**구현**:
- commit 스킬의 각 Step 진입 시 `date +%s` 또는 SECONDS 변수로 타임스탬프
- Step 종료 시 차이 계산 누적
- 최종 요약에 포맷 `Nm Ns` (분이 0이면 `Ns`만)

**측정 대상 단계**:
- pre-check (Step 5)
- review (Step 7 병렬, advisor 포함 시 advisor도 분리 표기)
- git commit (Step 8, hook 재실행 포함)
- 기타 긴 단계가 생기면 추가

**효과**:
- 사용자가 어디서 시간 많이 쓰는지 바로 파악
- 최적화 효과를 수치로 확인 가능
- 숨은 병목 드러남

## 검증 방법

1. 문서만 수정하는 커밋 1건 → Step 2/3 스킵되는지 + haiku로 리뷰되는지
2. 일반 코드 수정 1건 → 정상 경로
3. 핵심 설정 변경 1건 → risk_factors 감지 → sonnet 리뷰
4. 각 경로에서 소요 시간 측정 (§4 시간 리포팅으로 자동 확보)

## 우선순위

P1. 체감 속도 개선에 직접적. 단 데이터 전달(2번)은 리뷰 품질 유지의 전제 조건이라
gate(1번)보다 먼저 구현하는 게 안전.

구현 순서 제안:
1. pre-commit-check.sh에 결과 JSON 출력 추가
2. SKILL.md Step 5·7 수정 (데이터 경로 + prompt 포함)
3. review.md에 "already_verified 재검사 금지" 명시
4. Step 2·3 gate 조건 명시
5. 모델 스위치 (Agent tool 파라미터 확인 후)
