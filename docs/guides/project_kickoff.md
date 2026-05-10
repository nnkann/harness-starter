---
title: harness-starter CPS
domain: harness
tags: [cps, meta, starter]
status: in-progress
created: 2026-04-20
updated: 2026-04-28
---

# harness-starter CPS

> starter는 다운스트림에 전파되는 메타 프로젝트. CPS 자체가 하네스 품질의
> 기준점.

## Context

**역할**: AI 코딩 에이전트(Claude Code) 행동을 예측 가능·안전하게 만드는
템플릿. 다운스트림 프로젝트가 이식·업그레이드해서 사용.

**제약:**
- 단일 관리자(nnkann) 운영 — 팀 협업 수단 불필요, 간결함 우선
- Claude Code 전용 — 다른 AI 도구 호환 고려 안 함
- Windows + Git Bash가 주 개발 환경 — POSIX 가정 금지
- 실험 단계 (v0.x) — 공개 API 불안정, 다운스트림 실측 누적 후 1.0.0

**공급:**
- 스킬 14 + 에이전트 8 + 규칙 10 + 스크립트 11 + docs 구조
- `~/.claude/` (사용자 전역) 아닌 프로젝트별 `.claude/`에 설치

## Problems

해결해야 할 핵심 문제. 우선순위 순.

### P1. LLM 추측 수정 반복

**증상**: LLM이 공식 문서·git log·기존 결정 확인 없이 같은 파일을 여러 번
"추측 기반"으로 수정.

**영향**:
- 잘못된 수정 → 추가 수정 → 누적
- 실제 원인은 못 잡고 증상 완화만

**승격 상태**: `rules/no-speculation.md` + `rules/internal-first.md` 활성.
pre-check 핵심 설정 연속 수정 차단. HARNESS_EXPAND 우회.

### P2. review 과잉 비용

**증상**: review 에이전트가 단순 커밋(docs 이동·1줄 수정)에도 deep stage
선택하고 불필요한 Read 반복.

**영향**: 매 커밋 수십 초 대기, 토큰 낭비 누적.

**승격 상태**: `rules/staging.md` 경로 기반 5줄 룰, review.md 2축 + 회귀
알파 구조, `maxTurns: 6`.

### P3. 다운스트림 사일런트 페일

**증상**: 다운스트림 업그레이드 시 사용자 수동 액션 누락 감지 못 함.
permissions.allow 미전파, MIGRATIONS.md 공백, starter_skills 오염 등
경계 관리 구멍이 여러 곳에서 발생.

**영향**: 업그레이드했는데 하네스 일부 기능 무력화 (silent). 매 명령마다
승인 프롬프트가 뜨는 등 하네스 효과를 못 받음.

**승격 상태**: 5중 방어 (아래 S3 참조).

### P4. 광역 hook 매처 fragility

**증상**: Claude Code `Bash(* ... *)` 매처가 공백 포함 모든 문자 매칭이라
정당 명령 오차단.

**영향**: LLM이 작업 중 의도 외 차단 → 우회 시도 → 매처 추가 수정 루프.

**승격 상태**: `rules/hooks.md` 금지 규칙 + `bash-guard.sh` 단일 hook
통합 + `test-bash-guard.sh` 회귀.

**운용 약점 (2026-05-06 식별)**: bash-guard.sh가 차단에 성공해도 그 사실이
기록되지 않음. 방어 기전이 살아있는지 박제됐는지 판단 불가. eval --harness
P4 인용 0건이 이를 방증 — "너무 잘 막혀서 존재를 잊는" 역설. S4에 "차단
성공 기록" 레이어 추가 필요.

### P5. MCP·플러그인 컨텍스트 팽창

**증상**: 서브에이전트 spawn 시 컨텍스트 3545k 토큰 보고.

**영향**: 모든 review 호출이 비싸짐.

**승격 상태**: 조사 진행 중. review.md `tools` allowlist 이미 적용.

**구조적 원인 (2026-05-06 식별)**: MCP·플러그인 외에 업스트림 발 원인이
있음. 하네스가 정교해질수록 에이전트가 읽어야 할 파일(MAP, Rules, SKILL.md)이
증가하고, 이것이 다시 P5를 악화시키는 역설적 순환. "더 많은 문서화"로
문제를 해결하려는 관성이 에이전트의 **미완독 회피 패턴**을 유발하는 근본
원인. 해결 방향: 전체 문서 대신 "현재 작업에 필요한 최소 규칙셋(MVR)"만
주입하는 압축 전략 (S5 방향 전환).

### P6. 검증망 스킵 패턴

**증상**: SKILL.md·rules 변경이 "단순 문서 변경"으로 분류되어 테스트·CPS
갱신이 암묵적으로 건너뛰어짐. harness-dev 절차에 테스트·CPS 강제 없음.

**영향**: 행동 정의 문서 변경 효과가 검증 없이 커밋됨. MIGRATIONS.md 3개
버전 누락 같은 버그가 오래 방치됨 (2026-04-28 실측).

**승격 상태**: 4중 방어 (아래 S6 참조).

### P7. 시스템 구성 요소 간 관계 불투명

**증상**:
- 규칙·스킬·에이전트·스크립트가 서로를 모름
- 새 구성요소 추가 시 어디에 위치하는지 판단 기준 없음
- defends/serves 오매핑이 수개월 방치됨 (anti-defer·docs·memory·naming이 P5를 defends 선언했으나 내용 무관)
- 작업 전 어떤 문서를 읽어야 하는지 단일 진입점 없음

**영향**:
- P1 유발 — Claude가 규칙 간 관계를 추측으로 채움
- P6 유발 — 잘못된 매핑이 검증 없이 커밋됨
- 미완독 유발 — Read 강제 수단 없음 (SKILL.md 700줄+ 후반부 규칙이 묻힘)

**승격 상태**: HARNESS_MAP.md 설계 완료 (2026-05-05~06 전수 조사). P7은 P1·P6의 구조적 원인.

**Solution 의도적 미정의 (2026-05-11)**: P7의 메커니즘 자체가 `HARNESS_MAP.md`다.
별도 S7 Solution 정의 시 중복 추상화 — MAP 갱신 의무가 곧 S7 충족. eval --harness
관계 그래프 점검(항목 5 일부)이 사실상 S7 검증 채널 역할.

**미완독 회피 패턴 (2026-05-06 식별)**: SKILL.md·Rules 파일이 수백 줄을
넘으면서 에이전트가 "전체를 읽었다"고 응답하지만 실제로는 후반부 규칙을
무시하는 패턴 발생. P5(컨텍스트 팽창)와 상호 악화 — P7 해결(MAP 설계)이
P5를 악화시키는 역설. 해결 방향: HARNESS_MAP에 작업유형별 MVR(최소 필수
규칙셋) 매핑 컬럼 추가 (Wave B 대상).

### P8. 자가 발화 의존 규칙의 일반 실패

**증상**:
- 규칙·스킬·문서가 "Claude가 알아서 발화·준수한다"는 자가 의존 메커니즘에
  의존할 때, 다운스트림에서 사실상 비활성된다
- 강제 트리거(hook·pre-tool 차단·UserPromptSubmit) 없는 규칙은 starter에서
  "사용자·Claude가 그 규칙을 떠올리는 빈도"에 비례할 뿐 메커니즘 자체가
  작동하는 게 아님 (가시성 착시)
- 다운스트림 작업 성격(앱 코드)에서는 그 규칙을 "떠올릴 단서"가 부재 →
  규칙은 배포됐지만 발화 0건

**실측 사례 (2026-05-10)**:
- BIT(bug-interrupt) 다운스트림 발화 0건 — LSP stale dist 결함이 Q3=YES
  명백한 케이스(조용한 실패 + 다운스트림 전파 + 자동 발견 어려움)에서도
  메커니즘 0 작동. "에러 무지하게 나는" 상태에서도 트리거 0
- 다운스트림 write-doc 스킬 우회 빈발 — CLAUDE.md `<important>` 블록 +
  docs.md 강제 절차 있음에도 종종 우회
- CLAUDE.md 명시 사항 무시 빈발 — 텍스트 규칙이 자가 준수에 의존

**영향**:
- P1 유발 — 자가 발화 실패 → 발견된 결함이 추측 수정으로 진행
- P6 유발 — 발견 단계 누락 → 검증망 자체가 도달 안 됨
- 다운스트림 보고 채널이 비어 있어 starter 측에서도 결함 인식 지연
  (가시성 착시로 "잘 작동 중"으로 박제)

**starter 자기 적용 (2026-05-10 자기증명)**: P8은 다운스트림 한정 문제가
아니다. **starter 자체가 가시성 착시 영역에 포함**된다. P8 등록 wave
(`hn_self_invocation_failure.md`) commit 흐름 진행 중에 같은 자가 발화
의존 패턴 3건이 starter에서 발생:

1. **wip-sync 자동 move 미작동** — `/commit` 발화 + AC 자가 마킹 의존.
   commit 흐름 메커니즘은 있으나 사용자가 "완료처리는?" 묻기 전엔 발동 안 함
2. **status `completed` 자동 전환 부재** — implementation Step 4의 "변경
   한다" 텍스트 규칙이 자가 준수에 의존. Phase 종료 시 강제 트리거 0
3. **README 갱신 누락 + 메모리 자가 회상 의존** — `feedback_readme_update.md`
   메모리 박제 + `feedback_commit_skill_bypass.md` 박제됐음에도 회상 안 됨.
   `/commit` 발화 단일 트리거에 직렬 연결돼 있어 사용자 발화가 늦으면 전부
   누락

**`/commit` 발화 의존도 P8 변종**: BIT·write-doc 우회·CLAUDE.md 무시와
같은 카테고리. 사용자 자각에 의존하는 단일 발화 트리거는 모두 자가 의존
메커니즘 — starter라고 예외 아님. "사용자·Claude가 떠올리는 빈도에 비례"
한다는 본 P8 정의가 starter `/commit` 흐름에도 그대로 적용된다.

**선행 사례 회상 의존도 같은 패턴**: `docs/incidents/hn_commit_process_gaps.md`
(2026-04-27)가 거의 동일한 5건 패턴을 박제했으나 14일 후 재발. incident
박제 자체도 자가 회상 의존이라 starter 본인이 자기 증례를 회상 안 함.

**구조적 불균형**: P1을 defends하는 다른 규칙(no-speculation·internal-first)
은 hook(`debug-guard.sh` UserPromptSubmit) 강제력 보유. BIT(bug-interrupt)·
스킬 발화·CLAUDE.md 준수·`/commit` 발화는 강제력 0.

**승격 상태**: 본 Problem 등록 시점(2026-05-10)에서 메커니즘 결함 진단
완료. 1차 보강(debug-guard.sh BIT 트리거 키워드 추가) 진행 완료
(v0.39.0). starter 자기 적용 사례 박제(2026-05-10, 본 절). 강제 트리거
메커니즘 보강(`/commit` 흐름·write-doc 우회 등)은 별 wave 후보 — Solution
메커니즘 변경이라 owner 승인 필수.

**관련 사례 문서**: `docs/decisions/hn_self_invocation_failure.md` (P8/S8
1차 등록 wave), `docs/WIP/decisions--hn_p8_starter_self_application.md`
(starter 자기 적용 + 강제 트리거 메커니즘 설계 wave),
`docs/incidents/hn_commit_process_gaps.md` (선행 박제 — 회상 의존 실패의
결정적 증거), `docs/decisions/hn_bug_interrupt_triage.md` (BIT 설계 의도).

## Solutions

각 Problem의 현 접근. **해결 기준**: 이 조건이 충족돼야 Solution이 작동하는 것으로 판단.
기준 미달이 관찰되면 Problem이 재발한 것 — 새 WIP로 대응.

### S1 (for P1): 규칙 + 자동 차단 + 우회 장치

- **규칙**: no-speculation·internal-first·hooks — 원칙 명시
- **자동 차단**: pre-check의 핵심 설정 연속 수정 차단
- **우회**: `HARNESS_DEV=1 git commit` (정당 점진 확장 시)
- **검증 수단**: review 카테고리 8 CPS 갱신 누락 감지

**해결 기준**:
- 같은 파일을 근거 없이 3회 이상 수정하는 패턴이 세션당 0건
- pre-check이 추측 수정을 차단한 경우 에이전트가 즉시 관찰→재현 흐름으로 전환

**제약**: LLM이 규칙을 읽고도 위반함. 자동 차단이 마지막 안전망.

### S2 (for P2): 패턴 → 행동 매핑 + hard 상한

- **행동 가이드**: review.md 2축(계약·스코프) + 회귀 알파(S7·S8 hit 시만)
- **hard 상한**: `maxTurns: 6` frontmatter
- **Stage 차등**: staging.md 경로 기반 5줄 룰

**해결 기준**:
- review tool call 평균 ≤4회 (micro: 0~2, standard: 1~4, deep: 3~6)
- maxTurns 소진으로 verdict 누락 0건
- docs-only 커밋이 skip 또는 micro로 분류됨

**검증됨 (2026-04-20)**: starter 격리 벤치마크 3시나리오 실측.
상세: `docs/incidents/hn_review_v080_benchmark.md`.

**제약**: 다운스트림은 환경 요인(플러그인·MCP) 추가로 기준선이 다름.

### S3 (for P3): 5중 방어

1. **MIGRATIONS.md** — upstream 소유 지시 문서. 버전별 "이번에 뭘 해야 하는가" 명시
2. **harness-upgrade Step 8** — permissions.allow 동기화 (starter 신규 항목 추가 제안)
3. **harness-upgrade Step 9.5** — 업그레이드 시 수동 액션 섹션 자동 표시
4. **migration-log.md** — 다운스트림 소유 기록 문서. 업그레이드 충돌·이상 소견 + **피드백 리포트** 기록 → upstream 전달 가능. 피드백 포맷: "관점 + 약점 + 실천" 구조로 규격화 (MIGRATIONS.md `## Feedback Reports` 섹션 SSOT)
5. **downstream-readiness.sh** — 적용 후 누락 자가 진단

**해결 기준**:
- 새 버전 릴리즈 시 MIGRATIONS.md에 해당 버전 섹션 존재 (수동 적용 없음도 `없음` 명시)
- 다운스트림 업그레이드 후 permissions.allow 항목이 upstream과 동기화됨
- 업그레이드 후 `downstream-readiness.sh` 실행 시 누락 항목 0건

**구조 변경 (2026-04-28)**:
- MIGRATIONS.md: 기록물 → 지시 문서로 재설계. 자동/수동 적용 명확히 분리
- migration-log.md 신설: 다운스트림이 작성, upstream은 읽기만
- h-setup.sh 신규 설치 경로 starter_skills 필터 추가
- HARNESS.json starter_skills 경계 정비: harness-dev 제거, harness-sync skills 등록

**제약**: 사용자가 수동 액션을 건너뛰면 무력. migration-log.md를 채우지
않으면 이상 소견 추적 불가.

### S4 (for P4): 단일 hook + 금지 규칙

- **통합**: bash-guard.sh 하나로 모든 argument-constraint 검증
- **금지 규칙**: rules/hooks.md + review가 settings.json diff 보면 감지

**해결 기준**:
- `bash -n` 같은 정당 명령이 hook에 의해 차단되는 사례 0건
- settings.json diff에 argument-constraint 패턴 추가 시 review가 [차단] 발행
- `test-bash-guard.sh` 전 케이스 통과

**제약**: claude-code matcher 동작이 공식 문서와 실측이 다를 때 있음.
incident `hn_bash_n_flag_overblock` 참조.

**추가 방어 레이어 (v0.38.3)**:
6. **차단 성공 기록** — bash-guard.sh 차단 시 `.claude/memory/signal_defense_success.md`에 자동 append. "이 규칙은 여전히 유효하다"는 데이터 축적. eval --harness 항목 6번이 기록 확인.

### S5 (for P5): 압축 + 최소화

**현재 가설 (미확정)**:
- claude.ai 웹 통합 7개 → 사용자가 웹에서 해제 가능
- enabledPlugins 5개 → 필요한 것만 on
- 서브에이전트 `tools` allowlist → 이미 적용 (효과 실측 중)

**방향 전환 (2026-05-06)**: MCP·플러그인 제거(외부 원인)와 별도로,
업스트림 발 구조적 원인 대응 필요. 핵심 전략:
- **MVR(Minimum Viable Rules)**: HARNESS_MAP `## MVR` 섹션 구현 완료
  (v0.38.2). 7개 작업유형별 Rules 2~3개로 압축. MAP 상단 "⚡ 빠른 진입"
  가이드 추가 — MAP 전체 Read 금지.
- **문서 밀도 우선**: 문서 양 증가 대신 구조화·세그멘팅. 거대 SKILL.md
  섹션 분리 또는 에이전트가 필요할 때만 읽는 구조 검토 (진행 중).

**해결 기준**:
- 서브에이전트 spawn 시 컨텍스트 < 500k 토큰 (현재 3545k)
- 원인이 특정되면 해당 항목 제거 + 실측 재측정

**제약**: 정확한 원인을 사용자 환경에서만 측정 가능.

### S6 (for P6): 4중 방어

1. **self-verify.md SKIP 조건 명확화** — SKILL.md·rules/*.md는 "단순 문서"가 아님. 테스트 + "자동화 불가 검증" 명시 의무
2. **harness-dev Step 5 semver 표** — SKILL.md·rules 절차 변경 = patch 범프 대상으로 명시
3. **harness-dev Step 6 체크리스트** — 테스트 통과 + CPS 갱신 항목 추가
4. **review 카테고리 8** — 기존 SKILL.md·rules 실질 변경(M, ≥3줄)도 CPS 갱신 감지 대상 추가
5. **commit Step 4 MIGRATIONS.md 자동 작성** — 버전 범프 확정 후 MIGRATIONS.md 섹션 작성 절차 추가 (v0.26.2)
6. **implementation Step 2.5 AC 강제화** — 자동화 가능 AC 실행 기록 의무, 불가 항목 명시 의무 (v0.26.2)
7. **implementation Step 4 CPS 갱신 명시 의무** — "없음"도 WIP ## 결정 사항에 명기 (v0.26.2)
8. **docs_ops.py move 신호 → pre-check 봉인 면제** — `docs_ops.py move`가 완료 시 `.claude/memory/session-moved-docs.txt`에 경로 기록. pre-check이 대조해 reopen→수정→move 정상 절차 경유 파일의 봉인 위반 오탐 차단 (v0.38.4)

**해결 기준**:
- SKILL.md·rules 변경 커밋에 `python3 -m pytest .claude/scripts/test_pre_commit.py -q` 실행 기록이 있음
- SKILL.md 절차 변경 시 MIGRATIONS.md 해당 버전 섹션 동반
- WIP AC 완료 후 CPS Solution 항목 갱신 여부가 명시적으로 확인됨
- reopen→수정→move 정상 절차 경유 파일이 봉인 오탐 없이 통과 (T42.9·T42.10 회귀 테스트로 보장)

**구현 완료 (2026-04-28, v0.26.2)**: 5·6·7번 방어 레이어 추가. 해결 기준 3개 모두 스킬 절차에 강제화됨.
**구현 완료 (2026-05-08, v0.38.4)**: 8번 방어 레이어 추가. reopen→move 봉인 면제 메커니즘 — 정상 절차 인식 신호로 false-block 차단.
실제 Claude 행동 변화는 운용에서 확인 필요 — "테스트 통과 = 검증됨"으로 포장 금지.

**제약**: SKILL.md 변경의 실제 Claude 행동 변화는 자동 검증 불가 — 운용에서
확인 필요. "테스트 통과 = 검증됨"으로 포장 금지.

### S8 (for P8): 강제 트리거 우선 + 자가 의존 보조 [1차 초안]

> **상태**: 1차 초안 (2026-05-10). 충족 기준 확정은 owner 승인 후. cascade
> 영향 검토 완료 전까지 본 Solution 인용은 `(부분)` 마커 권장.

**원칙**: 자가 발화·자가 준수에 의존하는 규칙은 강제 트리거(hook·pre-tool
차단·UserPromptSubmit) 한 겹을 우선 깔고, 자가 의존은 그 위 보조 레이어로
배치한다. 강제 트리거 없는 규칙은 starter 가시성 착시 영역으로 가정한다.

**1차 보강 (구현 진행 중)**:
1. **debug-guard.sh BIT 트리거 키워드 확장** — 사용자 발화에 "버그·이상·
   왜 안 돼·이거 깨졌네·에러 무지하게·작동 안 함" 류 키워드 감지 시 BIT
   Q1/Q2/Q3 블록 적용 안내 출력 (`docs/WIP/decisions--hn_self_invocation_failure.md`)
2. **bug-interrupt.md 강제 트리거 절 추가** — 자가 발화 한계 + hook 보강
   메커니즘 명시. 키워드 SSOT는 debug-guard.sh로 위임 (룰에 박지 않음)

**해결 기준 (1차 초안 — owner 승인 필요)**:
- 자가 발화 의존 규칙(BIT 등) 미발화 패턴이 다운스트림 운용에서 실측될 때
  강제 트리거(hook)가 보강 안내 출력
- debug-guard.sh가 기존 debug-specialist 트리거 + BIT 트리거 둘 다 커버
- 다운스트림 운용에서 자가 의존 규칙 발화 빈도가 측정 가능 (signal 파일
  또는 로그)

**스코프 외 (별 wave 후보)**:
- write-doc 스킬 우회 강제 트리거 (PreToolUse Write hook — scope 정의 복잡)
- CLAUDE.md 무시 패턴 메커니즘 보강 (구조 자체 재설계 필요)

**제약**:
- 강제 트리거가 false-positive 유발 시 사용자 마찰 (P4 hook fragility 학습)
- hook 키워드 매칭은 자연어의 "발견" 자체를 보강할 뿐 — Claude 자가 인지
  의무는 여전히 잔존

## 도메인 목록

현재 확정: harness, meta.

다운스트림은 `naming.md`에서 자기 도메인 추가. starter는 자체 도메인
확장 계획 없음.

## 하네스 강도

strict (본 CLAUDE.md `## 환경`에 기록됨).

이유: starter의 변경은 다운스트림 전파되는 메타 변경. 검증 약화 시
다운스트림 전체에 영향.

## 메모

- 본 문서는 **starter 자체 CPS** — 다운스트림에 전파 안 됨 (`is_starter: true` 전용)
- `project_kickoff_sample.md`는 다운스트림이 `harness-init` 실행 시 템플릿으로 사용
- P1~P5는 2026-04-19~20 실측 기반. P6는 2026-04-28 실측 추가. P7은 2026-05-05 실측 추가. P8은 2026-05-10 다운스트림 LSP 결함 BIT 미발화 실측 기반
- Solution은 현 시점 최선. 다운스트림 실측 누적 후 재평가
- S8은 1차 초안 — 충족 기준 확정은 owner 승인 후 (cascade 영향 검토 동반)
