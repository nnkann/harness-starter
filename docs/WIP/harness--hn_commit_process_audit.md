---
title: 커밋 프로세스 재검토 — 중복·모호 영역 10항목 정리
domain: harness
tags: [commit, review, pre-check, audit, simplification]
relates-to:
  - path: harness/hn_commit_perf_optimization.md
    rel: extends
  - path: WIP/harness--hn_search_and_completion_gaps.md
    rel: references
  - path: WIP/harness--hn_staging_followup.md
    rel: references
  - path: decisions/hn_review_staging_rebalance.md
    rel: references
status: in-progress
created: 2026-04-22
---

# 커밋 프로세스 재검토 — 중복·모호 영역 10항목 정리

## 배경

2026-04-22 세션에서 bulk 스테이지 폐기 후 커밋 흐름 전체 검토. 사용자
지적: "린터 2회 실행이 과한 것 같다", "light/strict 구분이 모호하다",
"docs-manager의 실제 효용 불명" 등 구조적 중복·불명확 지점 발견.

본 문서는 **검토 결과 10항목의 결정 방향**을 기록. 실제 구현은 각
항목별 후속 작업으로 분리.

## 검토 관점

- **중복 제거**: 같은 일을 두 번 하는 구간
- **개념 정합성**: 모드/플래그/스테이지 축이 겹치는가
- **실측 가치**: 설계만 있고 실제 발동 흔적 없는 기능
- **책임 위치**: 해당 기능이 이 단계에 있는 게 맞는가

## 항목별 결정

### 1. 린터 2회 실행 → Step 5로 통합

**현 상태**:
- Step 0: `pre-commit-check.sh --lint-only`
- Step 5: `pre-commit-check.sh` (린터부터 다시 실행)
- 린터가 npm/pnpm이면 실측 초 단위 × 2회

**결정**: Step 0 삭제. Step 5에서만 린트.

**근거**:
- "시작 시점 린트"는 Claude 작업 *전* 상태 검사 = 이미 통과한 걸 재확인
- "수정 완료 시점" = 실제 새 이슈만 검출
- Step 1~4(잔여물·WIP·버전·스테이징)는 1초 이하. 린트 실패 시 되돌리기
  비용 싸다 — 조기 종료 이점 미미
- pre-check 캐시가 있으면 재커밋 시 린트 자체가 캐시됨

**리스크**:
- 린트 실패 시 Step 1~4 결과(버전 범프·promotion-log 행 등)가 staged로
  남음. 해결: Step 5 실패 시 **staged 유지**. 사용자가 린트 수정 후
  재커밋하면 기존 staged + 린트 수정분이 함께 커밋됨

**영향 파일**: `.claude/skills/commit/SKILL.md` Step 0 섹션 삭제,
`pre-commit-check.sh --lint-only` 모드 제거

---

### 2·9. light/strict 모드 폐기 + 플래그 통합

**현 상태**:
- 모드: light/strict (CLAUDE.md "하네스 강도" 필드)
- 플래그: `--light` / `--strict` / `--quick` / `--deep` / `--no-review`
- strict = 항상 review, light = 위험도 hit 시만 review
- 플래그 일부는 모드 오버라이드, 일부는 stage 오버라이드 → 개념 2개 섞임

**결정**: light/strict 완전 폐기. 플래그만 유지 (`--quick`/`--deep`/`--no-review`).

**근거**:
- staging이 `skip/micro/standard/deep` 4단계 + `recommended_stage` 판정으로
  강도 조절 축 이미 완비
- light(위험도 hit 시 review) = staging의 `recommended_stage: skip/standard`
  판정과 **완전히 같은 일**
- strict(항상 review)의 역할은 사용자가 `--deep` 명시로 대체
- 모드 개념 자체 사라지면 "모드 오버라이드 플래그" 개념도 불필요 → 플래그는
  모두 stage 오버라이드로 단일화

**제약**:
- 사용자 선호 축을 새로 만드는 건 **이번 폐기의 의미를 뒤집는 것**. 선호는
  플래그 사용 빈도로 자연 표현되게 둠

**영향 파일**:
- `CLAUDE.md` "하네스 강도" 필드 제거
- `commit/SKILL.md` 모드 결정 규칙·위험도 게이트·light/strict 섹션 전면 삭제
- `--light`/`--strict` 플래그 제거
- `harness-init/SKILL.md` 하네스 강도 설정 단계 제거

---

### 3. 진척도 갱신 위치 재배치 (Step 2 → Step 4 직후)

**현 상태**:
- Step 2: docs/WIP/ 본문에서 staged 파일 경로 매칭 → ✅ 표시
- 실제 동작 흔적 거의 없음. 매칭 실패 시 조용히 스킵 → 디버깅 불가

**결정 (재정정 2026-04-22)**: review pass 직후, `git commit` 직전에 실행.

**근거**:
- 제 이전 제안("Step 4 직후")은 틀림. review block 시 수정·재staging 사이클에서 ✅ 덮어쓰기 발생
- review pass가 "staged 확정된 최종 상태" → 이 시점에 진척도 갱신
- 갱신 → 갱신된 WIP 파일 `git add` → `git commit`
- pre-check 재호출 없음. 커밋 메시지 가공과 동일 단계에서 처리
- 매칭 결과 stderr 명시: "WIP N개 중 M개 매칭, 갱신됨" or "매칭 없음"

**리스크**:
- WIP 본문에 staged 경로가 안 쓰여 있으면 여전히 매칭 실패 — 로그로 사용자 인지
- 이 시점 staged 변경이 pre-check 결과와 미세하게 불일치 (✅ 표시만 추가된 WIP 파일은 재검증 대상 아님 — 안전)

**영향 파일**: `commit/SKILL.md` Step 2 → 커밋 직전 단계로 이동

---

### 4. 하네스 버전 체크 범위 분리

**현 상태**: commit 스킬 Step 3 중앙에 "harness-starter 리포 전용" 로직

**결정**: 별도 스크립트(예: `.claude/scripts/harness-version-bump.sh`)로
분리. `is_starter: true`일 때만 commit 스킬이 호출.

**범위 제한**: 이 항목은 **commit 스킬 Step 3 분리**로 한정. 업스트림 전용 로직 전수 감사는 **별도 문서** `hn_upstream_only_audit.md`에서 처리 (다운스트림 전파 파일 중 `is_starter`·`HARNESS_DEV`·업스트림 전용 내용 전수). 범위가 commit 프로세스를 넘어서므로 분리.

**근거**:
- 범용 스킬 본문에 업스트림 전용 로직 섞이면 다운스트림이 매번 스킵 판정
  부담
- 분리하면 다운스트림은 아예 모르는 영역

**영향 파일**: `commit/SKILL.md` Step 3 → 스크립트 호출 한 줄,
`harness-version-bump.sh` 신설

---

### 5. session 캐시 3개 → 1개 (or 0개)

**현 상태**:
- `session-staged-diff.txt` — Step 6·7 diff 재사용 (연계 목적)
- `session-pre-check.txt` — review prompt 주입 (연계 목적)
- `session-tree-hash.txt` — 캐시 유효성 판정 (캐싱 목적)

**결정**: 캐싱 목적 폐기. 연계는 **변수 or 최소 파일**로.

**옵션 A (파일 0개)**:
- commit 스킬이 pre-check를 Bash로 돌린 직후 stdout을 변수에 보관
- diff도 변수로 보관
- Step 6·7에서 변수 참조
- 재commit 시 재실행 (캐싱 없음)

**옵션 B (파일 1개 + 변수 병행)**:
- `session-pre-check.txt`만 유지 (hook 전달용)
- commit 스킬 내부 경로는 **Bash 변수**. 파일 대기 없음
- 파일 저장은 **background (`&`)** — commit 스킬은 기다리지 않음
- hook이 나중에 파일 읽어 커밋 메시지에 주입
- diff도 변수로

**결정 (재정정 2026-04-22)**: 옵션 B. 단 **"캐싱 대기" 폐기, 변수 기본 경로 + 백그라운드 파일 기록**.

**근거**:
- 사용자 지적: "캐싱을 하기 위해서 대기한다는 건 진짜 멍청한 짓". 맞음 — 파일 I/O가 대기 포인트가 되면 무의미
- 변수만으로는 hook에 전달 못함 → 파일 1개는 유지
- 핵심: **파일을 non-blocking으로 기록**. commit 스킬은 변수 사용, hook은 파일 사용. 둘이 서로 기다리지 않음
- tree-hash 기반 재commit 캐싱은 실측 가치 낮음 → 완전 폐기

**검증 필요 (구현 시 실측)**:
- Windows Git Bash에서 `command &`가 실제 non-blocking인가
- background write가 hook 실행 전에 flush되는가
- 안 되면 **옵션 B 폐기 + 재커밋 시 pre-check 재실행** (더 단순한 경로)

**영향 파일**:
- `pre-commit-check.sh` tree-hash 로직 제거
- `commit/SKILL.md` Step 5 캐시 분기 제거, 변수 + background 기록으로 재작성
- `rules/memory.md` "동적 snapshot" 섹션 재작성 (3개 → 1개, 목적 변경)
- `.gitignore` 정합성 유지

---

### 6. 메타 파일 본문 박기 삭제

**현 상태**: commit 스킬이 review prompt에 `.claude/HARNESS.json`·
`promotion-log.md`·`MIGRATIONS.md` 본문을 `## commit 처리 결과` 블록으로 박음

**결정**: 해당 블록 삭제.

**근거**:
- review가 해당 파일 직접 Read하는 편이 더 정확
- prompt 부피만 늘리고 실측 효용 확인 안 됨 (v0.18.4~v0.18.7 실측에서
  review가 이 블록 활용한 증거 없음)
- "정보 흐름 누수 #8·#1 해소" 명분으로 추가됐지만, 실제로는 review Read
  패턴이 prompt 블록보다 효율적

**영향 파일**: `commit/SKILL.md` "메타 파일 본문 박기" 섹션 전면 삭제

---

### 7. test-strategist 병렬 호출 삭제 + 책임 이관

**현 상태**:
- pre-check이 `needs_test_strategist`·`test_targets`·`new_func_lines_b64`
  stdout key 출력
- commit 스킬 Step 7이 review와 병렬로 test-strategist 호출
- 실측: 업스트림 발동 기록 없음. 다운스트림도 기억 없음

**결정 (재정정 2026-04-22)**: commit 스킬에서 test-strategist 호출 로직 **전면 삭제**. implementation 스킬로 이관. 단 **옵션 플래그로만 호출**.

**호출 방식**:
- implementation 기본 흐름에서는 호출 안 함 (기본 침묵)
- 사용자가 `implementation --test` 명시 시만 호출
- 플래그 이름은 단일 `--test`. `--with-tests` 같은 이중 수식 금지 (중복 수식은 플래그 네이밍 오염)

**근거**:
- 테스트 전략은 설계·구현 단계 결정 사항. 커밋 시점엔 이미 코드 완성 → 너무 늦음
- implementation 기본 호출은 **토큰·시간 낭비 우려**. 실측으로 효용성 확인 후 기본화 여부 결정
- 커밋 단계 병렬 호출은 책임 위치 오류

**후속**:
- `--test` 플래그 실측 사용 빈도·효용성 관찰
- 자주 쓰이면 기본화 검토, 안 쓰이면 test-strategist 에이전트 자체 폐기 검토

**영향 파일**:
- `commit/SKILL.md` test-strategist 병렬 호출 섹션 삭제 (~30줄)
- `pre-commit-check.sh` 해당 stdout key 제거
- `implementation/SKILL.md` `--test` 플래그로 호출 로직 추가
- **`README.md`** `--test` 플래그 사용법 안내 (implementation 스킬 섹션에 한 줄). 플래그가 있어도 README에 없으면 사용자가 모름

**구현 체크리스트**:
- [ ] implementation/SKILL.md `--test` 플래그 파싱·호출 로직
- [ ] README.md implementation 섹션에 플래그 언급
- [ ] 실측 관찰 기록 (`hn_commit_process_audit.md` 본 항목에 append)

---

### 8. review 로그 라인 자동 주입 (git hook)

**현 상태**:
- 커밋 메시지 본문에 `🔍 review: <stage> | signals: ... | domains: ...` 한
  줄 수동 포함
- 스킬 우회 시 누락 가능

**결정 (재정의 2026-04-22)**: 항목 #8을 "hook 메시지 주입"이 아니라 **"커밋 발화 강제 경유"**로 재정의.

**재구조**:
- 이전 제안(hook이 조용히 skip)은 **우회 경로를 설계에 박제**하는 오류. 사용자 지적: "이미 커밋 발화에서 해결되어야 함"
- `bash-guard.sh`가 `git commit` 발화 감지 시 개입 → commit 스킬 경유 여부 확인
- commit 스킬이 최종 커밋 시 환경변수(예: `HARNESS_COMMIT_SKILL=1`) 세팅
- Bash 직접 `git commit` 시 변수 없음 → bash-guard가 차단 + "commit 스킬 사용" 메시지
- 우회 불가 구조 → Part E 구멍 5 **완전 대응**

**자동 메시지 주입은 부산물**: 강제 경유가 확보되면 commit 스킬이 반드시 실행 → 스킬이 직접 메시지에 박음. hook 자동 주입 불필요.

**이스케이프 해치**: `HARNESS_DEV=1` 유지 (스킬 버그 등 긴급 상황용). 기존 `.git/hooks/pre-commit` 보호 로직과 일치.

**영향 파일**:
- `.claude/scripts/bash-guard.sh` `git commit` 발화 차단 로직 추가
- `commit/SKILL.md` 최종 커밋 시 `HARNESS_COMMIT_SKILL=1` 세팅
- `commit/SKILL.md` "git log 추적성" 섹션은 현재대로 유지 (수동 주입, 스킬이 박음)
- Part E 구멍 5 본 항목으로 흡수 완료 표시

---

### 10. docs-manager 스킬 폐기 → 스크립트화

**현 상태** (332줄 스킬):
- Step 1: 프론트매터 검증 — 규칙 체크
- Step 2: 문서 이동 — `git mv` + 접두사 제거
- Step 2.5: 완료 문서 재개 — `git mv` 역방향
- Step 3: clusters 갱신 — 파일명 파싱 + append/remove
- Step 5: 관계 맵 정합성 — relates-to 경로 검증
- Step 6: CPS 문서 갱신

**결정**: 스킬 폐기. 실제 동작은 `.claude/scripts/docs-ops.sh` (서브커맨드
기반)로 이관.

**근거**:
- 전부 **규칙 기반 작업**. LLM 판단·분석·조언 필요 없음
- "매니저"가 아니라 **규칙 실행기**. 실제 매니저처럼 동작한 흔적 없음
- 스킬 문서 332줄 유지 비용 > 스크립트화의 단순성

**구현 방향**:
- `docs-ops.sh validate` — 프론트매터·약어 검증
- `docs-ops.sh move <wip-file>` — 접두사 제거 + `git mv`
- `docs-ops.sh reopen <completed-file>` — 역방향 이동
- `docs-ops.sh cluster-update` — clusters 갱신
- `docs-ops.sh verify-relates` — 관계 맵 정합성

**CPS 관련 재정의 (사용자 명시, 2026-04-22)**:

"CPS 문서 갱신"은 단순 문서 작업이 아니라 **프로젝트에 작동하는 원칙**.
고도의 LLM 판단 요구 — 이전 작업·현재 작업·이후 작업을 연결하는 **맥락
원칙**이며 이 프로젝트의 존재 이유. 따라서:

- CPS 처리는 **더 높은 단계에서 체크**되어야 하고, 자연스럽게 docs-manager
  수준까지 유입되어야 함. 예외적 분리 처리 대상이 아님
- docs-manager 폐기 시 CPS 로직은 **implementation·write-doc 상위 흐름
  에서 이미 다뤄진 결과**를 스크립트화된 `docs-ops.sh`가 반영만 하면 됨
- Step 6 "CPS 문서 갱신"은 별도 LLM 판단 유지할 지점이 아님 — 상위에서
  이미 판단된 내용을 규칙 기반으로 반영
- 결론: **전 Step 스크립트화 가능**. CPS 예외 조항 삭제

**영향 파일**:
- `docs-manager/SKILL.md` 폐기 (archived로 이동)
- `docs-ops.sh` 신설
- `commit/SKILL.md`·`write-doc/SKILL.md`·`implementation/SKILL.md`에서
  docs-manager 호출 → 스크립트 호출로 교체
- SKILL 개수 1개 감소 → `.claude/HARNESS.json skills` 필드 갱신

---

## 연관 미해결 항목 (본 문서 범위 밖, 추적용)

사용자 확정(2026-04-22): 아래 3건 모두 동의된 추적 대상.

- **Part E 구멍 5** (commit 스킬 우회 가능): #8 hook 자동 주입으로 부분
  대응. 완전 대응은 pre-check 강제 실행 구조 필요 → 별도 작업
- **커밋 분리 전략** (`hn_staging_followup.md`): pre-check 1회 판정 원칙
  과 #5 session 파일 단순화가 정합. 설계 진행 시 본 감사 결과 반영
- **하네스 강도 폐기의 다운스트림 영향**: 다운스트림 CLAUDE.md 갱신 필요.
  마이그레이션 가이드 필요

## 실행 계획 (우선순위)

측정·영향·난이도 기준 제안. 사용자 조정 필요.

| P | 항목 | 난이도 | 효과 |
|---|------|--------|------|
| P0 | #1 린터 2회 | 낮음 | 체감 속도 |
| P0 | #5 session 캐시 단순화 | 중간 | 복잡도 감소 |
| P0 | #6 메타 박기 삭제 | 낮음 | prompt 부피 |
| P1 | #2·9 light/strict 폐기 | 중간 | 개념 단순화 |
| P1 | #7 test-strategist 삭제 | 낮음 | 규모 감소 |
| P1 | #3 진척도 재배치 | 낮음 | 실제 동작 |
| P2 | #4 버전 체크 분리 | 낮음 | 다운스트림 정합 |
| P2 | #10 docs-manager 폐기 | 높음 | 큰 구조 변경 |
| P2 | #8 hook 자동 주입 | 중간 | 추적성 |

---

## 2026-04-22 세션 자기 실측에서 추가 발견 (#12·#13·#14·#15)

커밋 직후 이번 커밋 흐름 자체를 관찰해 드러난 항목. 본 감사 방법론
부실성(실측 없이 작성)의 교훈과 함께 기록.

### #12. pre-check dead link 범위 확장 — 프론트매터 `relates-to.path`

**현 상태**: pre-check Step 3.5(v0.18.6) dead link 검사는 md 본문의
마크다운 링크만 검사. 프론트매터 `relates-to.path` 필드는 검사 안 함.

**증상**: 이번 커밋(`c9568df`) 1차 review가 잡은 warn 3건 중 2건이
`relates-to.path` dead link. pre-check이 잡았어야 할 정적 오류.

**결정**: pre-check Step 3.5 검사 범위에 프론트매터 `relates-to.path`
추가. 앵커(`#`)는 기존 로직 재사용, 같은 커밋 staged 파일은 skip.

**근거**:
- v0.18.6에서 "review가 잡던 dead link를 pre-check으로 이식"한 선례와
  동형. 실측 근거 있음
- 이번 warn 2건은 같은 패턴 → 반복 방지 가치

**리스크**:
- 앵커만 있는 relates-to·code block 속 예시의 오탐 가능성. 기존 T35와
  동일 패턴 재사용으로 완화

**영향 파일**:
- `.claude/scripts/pre-commit-check.sh` Step 3.5 검사 B에 frontmatter
  파싱 추가
- `.claude/scripts/test-pre-commit.sh` T36 신설 (relates-to dead link
  케이스 + 앵커 케이스 + 같은 커밋 동반 케이스)

### #13. review 2번 호출 구조의 불합리 — 실측 후 결정

**현 상태**: 1차 warn → 수정 → pre-check 재실행 → **2차 review 자동
호출**. 이번 커밋 실측: 2차 review 30초 + 실질 이슈 0건 발견.

**사용자 원칙**: CPS(이전·현재·이후 작업 맥락)는 프로젝트 핵심. 2차
review 자체 생략·축소는 **정합성 위험**. 답은 "2번 돌아야 하는 상황
자체를 없애는" 것.

**test-strategist 검증 결과 (2026-04-22)**:

내 초기 제안 "A(pre-check 확장) + C(사용자 판단 분기)"는 실측 근거 부족.
판정:
- "2번 review가 반복 패턴"이라는 전제의 실측 데이터 1건(v0.18.6)뿐
- v0.18.6의 warn 원인이 docs에 **상세 기록되지 않음** → 반복 패턴
  확정 불가
- A+C 결론이 단정형으로 제시된 것 자체가 no-speculation.md 위반 징후

**추가 발견 방향 (test-strategist 제안)**:
- **D. warn 기준 재정의**: 1차 review가 "참고 1건"까지 warn으로 분류
  해서 2차가 유발될 수 있음. `hn_review_tool_budget.md` 조기 중단
  설계가 이미 이 방향 다룸 — pre-check 복잡도 증가 없음
- **E. pre-check 재실행 건너뛰기 경로 확인**: SKILL.md `verdict: warn →
  경고 표시 후 진행` 이미 존재. 이 경로가 실제로 사용되는지 실측 확인
- **F. review 자체 분류**: B의 분류 주체 모호 문제를 review.md 출력
  형식에 명시 필드 추가로 해결. LLM 분류 일관성은 T35류 테스트로 고정

**결정 방향 (재정의)**:
1. **선행**: "2번 review 발생 빈도" 실측 기록 시작. 다음 5~10 커밋에서
   1차 warn의 성격·원인·2차 필요성 기록. 없으면 반복 패턴 확정 불가
2. **병행**: #12(pre-check relates-to 확장)는 v0.18.6 선례와 동형이라
   독립 구현 가능. 이 자체로 A의 일부
3. **결정 보류**: C는 실측 전 섣부름. D·E·F 중 어느 게 답인지 실측
   데이터 누적 후 재판단
4. **CPS 원칙 고수**: 2차 review 자동 호출 자체는 유지. 정합성 우선

**영향 파일 (현재 단계)**:
- `commit/SKILL.md` 응답 처리 섹션 — 현재 구조 유지. 실측 기록 섹션
  추가("warn 발생 시 원인·성격·재호출 결과 기록")
- test-strategist 호출 선례 기록 (본 항목) — 설계·판단 단계 specialist
  호출 경로의 첫 실측 사례

### #14. pre-check stderr 기본 침묵 — 성공 흐름 과잉 출력 축소

**현 상태**: pre-check이 실행 중 "변경 이력 패턴 분석"·"연속 수정
카운트"·"14 keys stdout" 등을 화면에 흘림. 성공 흐름에서도 사용자가
"뭔가 작업 엄청 하는" 체감.

**결정**: pre-check stderr 기본 침묵. 실패·위험 경고만 출력. 정상 상태
알림은 silent.

**근거**:
- 실측: commit 스킬 시작 ~ review 호출 직전 ~3~5초 실행. 사용자 체감
  불일치 → **출력량이 시간감을 부풀림**
- 위험 경고("⚡ 위험도 감지"·"⚠ 대규모 변경")는 유지 필요 — 사용자
  상황 인지
- 단순 상태 알림(린트 OK·TODO 없음 등)은 silent화

**리스크**: 디버깅 시 silent로 인한 원인 추적 어려움 → `VERBOSE=1` 환경
변수로 기존 출력 복구 경로 유지

**영향 파일**:
- `.claude/scripts/pre-commit-check.sh` stderr 출력 분류 (경고 vs 정상)
- 정상 경로 `[ -n "$VERBOSE" ]` 가드 추가

### #15. test-strategist 존재 가치 재평가 — 폐기 후보

**현 상태**: test-strategist 에이전트 정의됨. 이번 세션 호출 실측:
- 소요: **114초 (2분)**, tool_uses 16, tokens 104k
- 결과 품질: 좋음 (추측 판정·D·E·F 방향 발견·회귀 케이스 제시)

**판정**: 결과 품질과 **실행 시간이 교환 불가**. 114초는:
- commit 스킬 본 흐름(pre-check + review × 2회 ~60~90초)의 1.5~2배
- "빠르게 결정해야 하는 순간"의 실용 영역 밖
- 판단이 이 시간 안에 맥락 휘발. 결과가 늦어 활용 못함

**사용자 실측 지적**: "가뜩이나 커밋 스킬 느린데 이거 넣으면 돌아버리겠네".
정당. 내가 앞서 "호출 정당"이라 평가한 것은 **시간 무시한 오판**.

**결정 방향**:

1. **커밋 단계 호출**: 기존 #7 확정 — 삭제 유지
2. **implementation `--test` 플래그**: **도입 재고**. 플래그 누를 때마다
   2분이면 플래그 자체가 방해물. 실제 구현 전 "사용 빈도 0" 가능성 높음
3. **설계·판단 단계 호출**: 폐기. 114초 검증은 실용 영역 밖
4. **에이전트 자체 존속**: 폐기 후보. `.claude/agents/test-strategist.md`
   삭제 + 관련 로직 정리

**대안 (판단 검증 필요할 때)**:
- Claude 본인이 직접 실측 (grep·Read). 2분 걸리지만 **비동기 진행** 가능
- 핵심 근거 1~2건만 빠르게 확인하고 판정 — 완전 검증보다 부분 검증
- specialist 호출이 아니라 **사용자에게 추측 여부 명시**하고 진행 — 책임
  사용자가 가져감

**리스크**:
- 에이전트 폐기 후 "판단 검증 필요한데 도구 없음" 상황. 완화: Claude가
  "이건 실측 아님, 추측임" 명시 습관화 (no-speculation 강화)
- 다운스트림이 test-strategist 쓰고 있을 가능성. MIGRATIONS에 폐기 안내
  필수

**영향 파일**:
- `.claude/agents/test-strategist.md` 삭제 (archived로 이동)
- `.claude/skills/commit/SKILL.md` test-strategist 호출 섹션 삭제
  (#7과 동시 처리)
- `.claude/scripts/pre-commit-check.sh` `needs_test_strategist`·
  `test_targets`·`new_func_lines_b64` stdout key 제거 (#7과 동시)
- `docs/harness/MIGRATIONS.md` 다운스트림 폐기 안내

**메타 교훈**:
- 본 세션에서 **내 자신이 "결과 품질"만 보고 "시간"을 무시**한 평가 오류.
  감사는 시간 예산을 항상 측정해야 함
- "감사의 검증 장치로 specialist 편입" 같은 일반론은 **실측 시간 없이
  쓰면 설계 비용 폭증 유발**. 이번이 그 실측 사례
- 이 감사 문서 다른 항목들도 **시간 영향 누락 가능성** — 재검토 대상

---

## 실행 계획 갱신 (P0~P2 재조정)

| P | 항목 | 난이도 | 효과 | 근거 |
|---|------|--------|------|------|
| P0 | #12 pre-check relates-to 확장 | 낮음 | 정적 warn 감소 | v0.18.6 선례 동형, 실측 근거 |
| P0 | #1 린터 2회 | 낮음 | 체감 속도 | 실측 중복 |
| P0 | #14 stderr 침묵 | 낮음 | 체감 부하 | 실측 출력량 과잉 |
| P0 | #6 메타 박기 삭제 | 낮음 | prompt 부피 | 실측 효용 없음 |
| P1 | #5 session 캐시 단순화 | 중간 | 복잡도 감소 | 실측 가치 불명 |
| P1 | #7 test-strategist 이관 | 중간 | 토큰 절감 | #15와 함께 재정의 |
| P1 | #3 진척도 재배치 | 낮음 | 실제 동작 | 위치 오판 수정 |
| P1 | #2·9 light/strict 폐기 | 중간 | 개념 단순화 | 개념 중복 |
| P2 | #13 2번 review 구조 | **실측 선행** | 불합리 해소 | test-strategist 검증 결과 |
| P2 | #4 버전 체크 분리 | 낮음 | 다운스트림 정합 | upstream audit 연계 |
| P1 | #15 test-strategist 폐기 | 낮음 | 복잡도 대폭 감소 | 114초 실측 |
| P2 | #10 docs-manager 폐기 | 높음 | 큰 구조 변경 | CPS 재정의 반영 |
| P2 | #8 bash-guard 강제 경유 | 중간 | 우회 불가 | Part E 구멍 5 흡수 |

## 후속

본 문서는 **결정 방향 기록**. 각 항목은 독립 커밋·후속 WIP으로 실행.
결정 뒤집기 필요 시 본 문서 갱신 + `## 변경 이력`.

**이번 세션 자기 실측의 핵심 교훈**:
- 감사·결정 문서 작성은 **실측 없이 쓰면 추측의 집합**이 됨
- no-speculation.md "단정형 추측 금지" 원칙이 감사 문서에도 적용되어야
- specialist 호출이 감사의 검증 장치로 편입될 때 감사 품질 향상 확인됨
