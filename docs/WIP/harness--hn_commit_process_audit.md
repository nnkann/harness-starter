---
title: 커밋 프로세스 재검토 — 중복·모호 영역 + 흡수 항목 통합
domain: harness
tags: [commit, review, pre-check, audit, simplification, staging, ssot]
relates-to:
  - path: harness/hn_commit_perf_optimization.md
    rel: extends
  - path: decisions/hn_review_staging_rebalance.md
    rel: references
  - path: decisions/hn_review_tool_budget.md
    rel: references
  - path: harness/hn_commit_review_staging.md
    rel: extends
status: in-progress
created: 2026-04-22
updated: 2026-04-22
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

### 1. 린터 2회 실행 → Step 5로 통합 (✅ 완료 2026-04-22)

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

### 2·9. light/strict 모드 폐기 + 플래그 통합 (✅ 완료 2026-04-22)

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

### 3. 진척도 갱신 위치 재배치 (Step 2 → Step 4 직후) (✅ 완료 2026-04-22)

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

### 4. 하네스 버전 체크 범위 분리 (✅ 완료 2026-04-22)

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

### 5. session 캐시 3개 → 1개 (or 0개) (✅ 완료 2026-04-22)

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

### 6. 메타 파일 본문 박기 삭제 (✅ 완료 2026-04-22)

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

### 7. test-strategist 병렬 호출 삭제 + 책임 이관 (✅ 완료 2026-04-22 — #15와 통합)

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

### 8. 커밋 발화 강제 경유 — bash-guard 차단 + 환경변수 표시 (✅ 완료 2026-04-22)

**(흡수: `search_and_completion_gaps` Part E 구멍 5 — v0.18.7 발견)**

**발견 경로 (v0.18.7)**:
- 사용자 관찰: "커밋 스킬도 이제 패스하네". 실측: v0.18.4~v0.18.7 중
  스킬 호출은 v0.18.4·v0.18.5 뿐. v0.18.6·v0.18.7은 수동 절차 + Bash
  `git commit` 직접 호출
- `git pre-commit` hook은 `HARNESS_DEV=1` 체크만. pre-check·review 미호출
- 스킬 우회 시 안전장치(pre-check·review·log line) 통째로 miss

**구조적 원인 — Part E 구멍 1·4와 동형**:

| 구멍 | 우회 대상 | 우회 경로 | 방어 위치 |
|------|----------|----------|-----------|
| 1 (v0.18.5) | SSOT 선행 탐색 | Write로 즉흥 문서 생성 | CLAUDE.md `<important if>` |
| 4 (v0.18.6) | dead link 감지 | review만 돌다 block | pre-check Step 3.5 |
| **5 (v0.18.7)** | **pre-check·review 전체** | **Bash `git commit` 직접** | **bash-guard + 환경변수** |

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

### 10. docs-manager 스킬 폐기 → 스크립트화 (✅ 완료 2026-04-22)

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

## 연관 추적 항목

- **하네스 강도 폐기의 다운스트림 영향** (#2·9 관련): 다운스트림
  CLAUDE.md 갱신 필요. 마이그레이션 가이드 필요 — MIGRATIONS.md 처리 대상

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

### #12. pre-check dead link 범위 확장 — 프론트매터 `relates-to.path` (✅ 완료 + 근본 수정 2026-04-22)

**v0.20.0 커밋 실측으로 발견된 2종 버그 근본 수정**:

1. **검사 A basename 과탐**: 파일 삭제 시 같은 이름의 다른 md 링크를
   전부 dead로 잡음 (SKILL.md 같은 흔한 이름에서 재앙적). 수정:
   basename grep은 1차 후보 수집만, 2차로 매치 링크 경로 해석 → 실제
   삭제 경로와 일치할 때만 dead. T38.1 회귀 추가
2. **검사 C 경로 기준 불일치**: `rules/docs.md` 원본 규칙은 `path:
   decisions/other.md` (docs/ 루트 기준)인데 초기 구현은 `dirname(src)/
   rt_path` (파일 기준). 수정: docs/ 루트 기준, `../`·`./`로 시작하면만
   파일 기준 (다운스트림 기존 `../harness/...` 호환). T36.7·T36.8 추가

**원 구현 내용** (이하 변경 없음):


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
- `.claude/scripts/test-pre-commit.sh` T36 신설

**T36 회귀 테스트 케이스 (test-strategist 검증 결과 반영)**:

1. `relates-to.path: decisions/hn_X.md`가 존재 파일 → 통과
2. `relates-to.path: decisions/hn_X.md`가 미존재 파일 → 차단
3. `relates-to.path: decisions/hn_X.md#section`(앵커) → 앵커 제거 후
   파일 존재 확인. Step 3.5 검사 B 기존 로직 재사용
4. 대상 md가 같은 커밋에 staged add → 통과 (오탐 방지, Step 3.5
   검사 A의 "같은 커밋 소스 skip" 패턴 재사용)
5. code block 안의 `relates-to: path:` 예시 → 검출 안 됨 (오탐 방지)
6. 멀티라인 YAML 리스트 (`relates-to:\n  - path: ...\n    rel: ...`) →
   첫 `path:`만 추출하지 말고 전 항목 순회
7. `rel:` 필드만 있고 `path:` 없는 항목 → skip (파싱 오류 회피)
8. T35 기존 케이스가 T36 추가로 깨지지 않는지 회귀 확인

**잠금 테스트 원칙** (`hn_lint_enoent_pattern_gaps.md` 교훈 동형 적용):
- T33·T34처럼 "차단/통과 짝"을 명시 케이스로 고정
- 오탐 케이스(5·6번)가 정탐 케이스(1~4번)와 같은 정규식에서 구분되는지
  테스트

**구현 시 주의 (test-strategist 사각지대 지적)**:
- YAML 파싱은 단순 정규식으로 충분하지 않을 수 있음. 안전한 방법:
  frontmatter 블록(`^---$` ~ `^---$`)만 추출한 뒤 그 안에서 `^  - path:`
  패턴만 awk 매칭
- TODO/FIXME 검사(pre-check 섹션 1)는 md 제외 중. 본 항목은 frontmatter
  검사라 md 포함 — 두 검사의 파일 범위 구분 명시 필요

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

**D·E·F 세부 평가 (test-strategist 제안)**:

- **D (warn 기준 재정의) — 가장 유력**:
  - `hn_review_tool_budget.md` "조기 중단·알파 발동 조건" 설계가 이미
    이 방향. review가 "참고 1건"을 warn으로 분류하지 않고 pass 내 메모
    로 처리하면 2차 review 자체 발생 안 함
  - **pre-check 복잡도 증가 없음** — review.md 출력 형식만 조정
  - 구현 위치: `.claude/agents/review.md` "## 출력 형식" + 판정 기준

- **E (pre-check 재실행 건너뛰기) — 현재 존재하나 사용 실측 필요**:
  - `commit/SKILL.md` 응답 처리 섹션에 이미 `verdict: warn → 경고 표시
    후 진행` 규정 존재
  - 실제 운영에서 이 경로가 얼마나 쓰이는지 **실측 누락** 상태
  - 검증: 다음 5 커밋에서 warn 시 "진행" vs "재review" 빈도 기록

- **F (review 자체 분류) — B와 분리, 실현 가능**:
  - B(Claude가 분류)와 달리 F는 **review 자신**이 warn에 "정적/의미론"
    플래그 붙임
  - LLM 분류 일관성 문제는 **T35류 회귀 테스트로 고정** 가능 (test-
    strategist 지적)
  - 구현 위치: `review.md` 출력 형식에 플래그 필드 추가

**D·E·F 우선순위 (판단 대기)**:
- D가 가장 적은 구현 비용 + 근본 원인 해결 (warn 기준 완화)
- E는 이미 있는 경로 실측 확인만 — **선행 필수**
- F는 B의 대안. D·E로 안 되면 검토

**영향 파일 (현재 단계)**:
- `commit/SKILL.md` 응답 처리 섹션 — 현재 구조 유지. 실측 기록 섹션
  추가("warn 발생 시 원인·성격·재호출 결과 기록")
- test-strategist 호출 선례 기록 (본 항목)

**test-strategist가 지적한 사각지대 (반영 필수)**:

1. **v0.18.6 1차 warn 원인 docs 미기록**: 2번 review 발생 유일 실측
   사례인데 상세 원인이 `promotion-log.md`·incident 어디에도 없음.
   `hn_staging_followup.md` 실측 테이블에 "재호출 포함 80초+, warn"
   한 줄뿐. 따라서 "반복 패턴" 확정 불가 → **D·E·F 선택 전 실측 5~10
   건 필수**
2. **CPS와 정적 검사의 교환 관계**: pre-check 확장(#12·A)은 **정적
   오류**만 잡음. CPS 맥락 이해는 여전히 review 담당. A가 2차 review를
   없앨 수 있는 범위는 **정적 warn 비율만**. 의미론적 warn은 여전히
   재호출 필요
3. **C의 전제 부실**: "사용자가 warn 받았을 때 정적/의미론 즉각 판단
   가능" 전제의 실측 근거 없음. C 폐기 근거 추가

### #14. pre-check stderr 기본 침묵 — 성공 흐름 과잉 출력 축소 (✅ 완료 2026-04-22)

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

### #15. test-strategist 존재 가치 재평가 — 폐기 후보 (✅ 완료 2026-04-22 — 에이전트 삭제)

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
| P0 | ✅ #12 pre-check relates-to 확장 | 낮음 | 정적 warn 감소 | v0.18.6 선례 동형, 실측 근거 |
| P0 | ✅ #1 린터 2회 | 낮음 | 체감 속도 | 실측 중복 |
| P0 | ✅ #14 stderr 침묵 | 낮음 | 체감 부하 | 실측 출력량 과잉 |
| P0 | ✅ #6 메타 박기 삭제 | 낮음 | prompt 부피 | 실측 효용 없음 |
| P1 | ✅ #5 session 캐시 단순화 | 중간 | 복잡도 감소 | 실측 가치 불명 |
| P1 | ✅ #7 test-strategist 이관 | 중간 | 토큰 절감 | #15와 함께 재정의 |
| P1 | ✅ #3 진척도 재배치 | 낮음 | 실제 동작 | 위치 오판 수정 |
| P1 | ✅ #2·9 light/strict 폐기 | 중간 | 개념 단순화 | 개념 중복 |
| P1 | ✅ #15 test-strategist 폐기 | 낮음 | 복잡도 대폭 감소 | 114초 실측 |
| P2 | 🔲 #13 2번 review 구조 | **실측 선행 (1건 더)** | 불합리 해소 | 4건 누적 실측 완료 |
| P2 | ✅ #4 버전 체크 분리 | 낮음 | 다운스트림 정합 | `harness-version-bump.sh` 신설 |
| P2 | ✅ #8 bash-guard 강제 경유 | 중간 | 우회 불가 | 검증 4 + G1~G5 테스트 |
| P2 | 부분 ✅ #17 S6 자동화 | 중간 | staging 정밀화 | S8·폭증 게이트는 #13 대기 |
| P2 | ✅ #10 docs-manager 폐기 | 높음 | 큰 구조 변경 | `docs-ops.sh` 5 서브커맨드 |
| P2 | 🔲 #18 커밋 분리 전략 | 높음 | 원자적 커밋 | 실측 5건 누적 후 결정 |
| P3 | 🔲 #16 세션 파일명 규칙 | 낮음 | naming 정합 | harness-adopt 실측 대기 |

---

## 흡수 항목 (2026-04-22, 하위 WIP 병합)

본 감사를 최상위 SSOT로 확정하고 아래 두 하위 WIP를 흡수. 중복 제거
후 미완 항목만 남김.

- `harness--hn_search_and_completion_gaps.md` (Part A·B·구멍 1·2b·4 완료.
  구멍 5 → 본 문서 #8, 구멍 2 잔여 → #16)
- `harness--hn_staging_followup.md` (P1 완료. 잔여는 #13 측정 계획·#17·#18로)

### #16. harness-init/adopt/upgrade 세션 파일명 규칙 — 실측 대기

**(흡수: `search_and_completion_gaps` Part E 구멍 2 잔여 — v0.18.7
부분 처리)**

**현 상태 (v0.18.7 단순 예시 교체 완료)**:
- `implementation/SKILL.md` Step 1, `naming-convention/SKILL.md`,
  `commit/SKILL.md` Step 2.3, `docs-manager/SKILL.md` Step 2.5·317 →
  `{abbr}_{slug}` 형식 + "날짜 suffix 전면 금지" 명시 완료

**미처리 (깊은 판단 대기)**: harness-init/adopt/upgrade의 세션·마이그
레이션 파일명은 "같은 주제 반복" 원칙과 충돌 가능. 각 세션/버전이
독립 리포트 가치를 가지는 특수 케이스.

| 파일 | 쟁점 |
|------|------|
| `project_kickoff_{YYMMDD}.md` | 개시 시점 1회만. 단일 파일 가능? |
| `adopt-session_{YYMMDD}.md` | 이식 세션마다 독립 결정. 누적 vs 세션별? |
| `migration_v{X}_{YYMMDD}.md` | `{X}` 버전이 이미 분리 키. 날짜 중복? |

**판단 옵션**:
- A. 같은 주제 1파일 + `## 변경 이력` (naming.md 원칙 유지)
- B. naming.md에 "세션 리포트" 예외 조항 추가
- C. `session_{N}` 순차 번호로 대체

**결정 방향**: 3개 스킬은 초기 플로우로 실행 빈도 낮음. **다음
harness-adopt 실행 사례 대기 후 결정**. 선제 변경은 추측 수정 위험.

**영향 파일 (결정 후)**:
- `.claude/skills/harness-init/SKILL.md`
- `.claude/skills/harness-adopt/SKILL.md`
- `.claude/skills/harness-upgrade/SKILL.md`
- `.claude/rules/naming.md` (옵션 B 채택 시)

---

### #17. staging 신호 잔여 정밀화 — S8·S6 자동화·폭증 게이트 (부분 ✅ 2026-04-22)

**완료**: S6 ≤5줄 → Stage 0 자동화 (pre-check 룰 3에 구현, `.claude/skills/`·
`agents/` 예외). T37 3케이스 추가, 62/62 통과.

**보류** (실측 선행): S8 export 검출 정밀화, 폭증 차단 게이트 코드 강제.
둘 다 #13 측정 결과 (5커밋 실측)에 따라 결정.

**(흡수: `staging_followup` 6단계·폭증 게이트)**

v0.17.x에서 S1 오탐 보정·S6 완화 자동화 P1 완료. 잔여:

**S8 export 검출 정밀화**:
- 현재 휴리스틱 `grep -E '^[+-].*export'` — 문자열·주석에도 잡힘
- 언어별 시그니처(TypeScript export / Python def / Go func) 분리 검토

**S6 ≤5줄 → Stage 0 자동화**:
- staging.md "C. 완화"에 명시됐지만 `pre-commit-check.sh`에서 미구현
- 구현 위치: pre-check Stage 결정 블록

**폭증 차단 게이트 코드 강제 (장기)**:
- 현재 staging.md "신호 추가 4질문"·"연결 규칙 5케이스"는 텍스트 규범
- pre-check이 신호 수 13 초과 시 경고 로직 추가 검토
- 1인 운영이면 후순위

**우선순위**: #13 5커밋 측정 결과에 따라 결정. 측정이 "deep 과잉"을
확인하면 S8/S6 정밀화가 해결책(옵션 A·B) 중 하나로 선택됨.

**영향 파일**:
- `.claude/scripts/pre-commit-check.sh`
- `.claude/rules/staging.md` (신호 정의 갱신 시)

---

### #18. 커밋 분리 전략 — 글로벌 원칙, 1회 판정

**(흡수: `staging_followup` "거대 커밋 분리 전략" + 2026-04-22 정정)**

#### 관점 (2026-04-22 정정)

분리는 **거대 커밋 전용이 아니라 모든 커밋에 적용되는 글로벌 원칙**.
bulk 폐기(2026-04-22)로 정량 처리 방향이 전체로 확장됨.

- 목적: **원자적 커밋 강제** (1 커밋 = 1 논리 단위)
- 판정은 **커밋 시도 시작 시점 1회만**. sub-커밋은 재판정 SKIP

#### 분리 판정 흐름

```
사용자 커밋 시도
  ↓
pre-check (분리 판정 포함) — 1회만
  ↓
분리 필요? → sub-staging 재구성 → N개 sub-커밋
              각 sub-커밋은 HARNESS_SPLIT_SUB=1 (분리 판정 SKIP)
분리 불필요? → 그대로 커밋
```

#### 설계 공간 (사용자 제안 축)

- **A. 분리 축**: `naming.md` "경로 → 도메인 매핑" 재활용 (SSOT 존재)
  - 폴백: 도메인 매핑 없는 파일은 폴더 1단계 prefix로 그룹화
- **B. 임계·재분리**: 그룹 내 파일 N개 초과 시 재분리 (N 초안: 10)
- **C. 내용별 묶음**: subject 키워드 + diff hunk 패턴 유사성
- **D. hunk 분리 (사용자 제안 H)**: 같은 파일 내 독립 주제 hunk
  `git add -p` 식 분리. 파일 단위 정립 후 확장
- **E. 속도 최적화**: sub-커밋은 사이즈 작아져 stage 자동 재판정
  (standard → skip까지). bulk의 실질 목적(빠른 커밋) 계승
- **F. 구현 위치**: pre-check = 판정, `split-commit.sh` = 실행
  (commit 스킬 아님 — staging/pre-check 영역)

#### 필요한 구조적 요소

1. **sub-커밋 신호**: `split-commit.sh`가 환경변수
   `HARNESS_SPLIT_SUB=1` 설정. pre-check이 감지 시 분리 판정 블록 전체
   스킵
2. **stdout 스키마**: pre-check이 `split_plan`·`split_group_N`·
   `split_action_recommended` 등 key 출력
3. **실행 스크립트**: `split-commit.sh` — pre-check stdout 읽어
   `git reset` + 그룹별 `git add` + commit 반복

#### 제약

- **속도**: 1회 판정이라 빠듯한 예산 불필요. 일반 pre-check 수준(~수 초)
- **정확성**: 1회로 끝나므로 오판 시 분리 전체가 틀림. **규칙 기반**이
  LLM보다 안전 (같은 입력 → 같은 출력)
- **절대 원칙**: pre-check 원래 기능 보존. 분리 판정은 추가 블록

#### 예외

- **rename-only 대량 커밋**: 원자적, 분리 불가 → 예외. dead link 이식
  (v0.18.6)으로 방어
- **의존성 있는 변경**: sub-staging 각각에 pre-check·빌드 통과 확인.
  실패 시 롤백
- **사용자 수동 오버라이드**: `--no-split` 같은 플래그

#### 선행 조건 + 상위 SSOT

- #13 5커밋 측정 누적 (staging rebalance 재평가)
- commit 스킬 stage별 경과시간 로그 (`hn_commit_perf_optimization.md` §4)
- 거대 커밋 발생 케이스 관찰
- 상위 SSOT: `hn_review_staging_rebalance` / `hn_review_tool_budget` /
  `hn_review_maxturns_verdict_miss` (bulk 폐기 근거) / `hn_commit_perf_optimization`

**결정 문서 승격 대상**: 실측 누적 후 `decisions/` 로.

---

### #13 보강 — 측정 스키마 + 세션 누적 4건 실측

**(흡수: `staging_followup` 7단계 보강 + 2026-04-22 추가 실측)**

#### 측정 항목 (구체화)

| 지표 | 기존 | 보강 |
|------|------|------|
| review 시간 | 평균 | **p50·p90·p100, 커밋별 기록** |
| tool_uses | 평균 | 평균 + stage별 분포 |
| 입력 토큰 | 평균 | 평균 + prompt 크기와의 상관 |
| Stage 분포 | 빈도 | 빈도 + 각 stage의 p90 경과시간 |
| **체감 임계** | (없음) | 사용자 불만 발화 시점의 실측 값 기록 |

**체감 임계**: 사용자가 "느리다"고 발화한 커밋의 경과시간을 기록해
**허용 상한**을 데이터로 확보. 추측 말고 관찰.

#### 세션 누적 실측 (2026-04-22, bulk 폐기 세션)

| 커밋 | signals | stage | 실측 | 판정 |
|------|---------|-------|------|------|
| v0.18.4 | S2,S9,S10,S7 | deep | 4 calls, ~30초, pass | 과잉 (실질 이슈 0) |
| v0.18.5 | S2,S9,S10,S7 | deep | 7 calls, ~60초, block→pass | 값어치 (cluster dead link) |
| v0.18.6 | S2,S9,S10,S7 | deep | 재호출 포함 80초+, warn | 과잉 (참고 1건) |
| v0.18.7 | S9,S10,S7 | deep | 1 call, ~27초, pass | 과잉 (문자열 drift fix) |
| v0.20.0 | S2,S9,S10,S7 | deep | — (커밋 전 실측, review 측정 대기) | 31파일·+1530/-1394 거대 커밋 실측. pre-check 2종 근본 버그 발견·수정 (검사 A 과탐·검사 C 경로 기준). 분리 없이 단일 커밋 시도 |

**4/4 중 3건 deep 과잉 (75%)**. 유일한 값어치 건(v0.18.5)이 잡은
cluster dead link는 v0.18.6에서 pre-check Step 3.5로 이식됨 → 이후
deep 값어치 추가 감소 예상.

**공통 패턴**: `.claude/scripts/**` 수정 → 5줄 룰 1번으로 무조건 deep.
S10 max=5 격상 겹치면 룰 1 miss 커밋도 deep 강제.

**`hn_review_staging_rebalance.md` (v0.17.0) 재검토**:
- 22 deep 중 scripts 10건·warn 2건으로 "scripts는 deep 유지" 결정
- 이번 4건도 scripts 변경, warn 1건 (25%) — 당시 20%와 비슷
- 단 이번 warn은 pre-check Step 3.5로 이미 이식 → 남은 deep 값어치 더 낮아짐

#### 해결책 설계 공간 (측정 5건 누적 후 결정)

- **A**: `.claude/scripts/**` deep 강제 완화 — 회귀 테스트 동반 +
  녹색이면 standard 격하. 리스크: 커버리지 가정 과신
- **B**: deep 내부 조기 중단 공격적 — tool_budget 원칙 2 강화. "계약
  Step 1에서 신호별 알파 미hit이면 즉시 pass". 리스크: 놓침
- **C**: review 병렬화 — tool 호출 간 대기 단축. 리스크: 에이전트 스펙 외
- **D**: 현상 유지 — "이 정도 시간은 허용 범위"로 나오면 개선 불필요

**1건 더 누적 후(5건) D·E·F(본 문서 원 #13) 중 채택 결정**.

---

## 변경 이력

- 2026-04-22: 10항목 + 자기 실측 4항목 초안 (`#1`~`#15`)
- 2026-04-22: 하위 WIP 2개 흡수 → `#16`·`#17`·`#18` 추가, `#8`·`#13`
  보강. 두 WIP는 in-progress 유지, 중복 섹션만 audit 포인터로 교체
- 2026-04-22: **P0 4개 구현 완료** (#12·#1·#14·#6)
  - #12: `pre-commit-check.sh` 검사 C 추가 (frontmatter `relates-to.path`
    dead link), `test-pre-commit.sh` T36 6케이스 신설, 65/65 통과
  - #1: Step 0 `--lint-only` 조기 체크 제거, `pre-commit-check.sh`
    `--lint-only` 모드 폐기. 린트는 Step 5에서만 1회 실행
  - #14: pre-check stderr 정책 헤더 주석 명시. `HARNESS_EXPAND` 통과 메시지
    `VERBOSE=1` 가드 추가
  - #6: commit/SKILL.md "메타 파일 본문 박기" 섹션 삭제 (prompt 부피 감소)
- 2026-04-22: **P1 5개 구현 완료** (#15·#7·#3·#5·#2·9) — v0.19.0
  - #15+#7: `.claude/agents/test-strategist.md` 삭제, pre-check 신호 3종
    (`needs_test_strategist`·`test_targets`·`new_func_lines_b64`) 제거,
    self-verify.md·advisor.md·implementation.md·commit SKILL 참조 정리.
    T11·T12 테스트 제거 후 59/59 통과
  - #3: Step 2 자동 매칭 → Step 7.5(review pass 직후, `git commit` 직전)
    재배치. review block 시 ✅ 덮어쓰기 방지
  - #5: `session-staged-diff.txt`·`session-tree-hash.txt` 폐기, tree-hash
    캐싱 로직 제거. Bash 변수 기본 + 필요 시 background 파일 기록. T20 제거
  - #2·9: CLAUDE.md `하네스 강도` 필드 제거, `--light`·`--strict` 플래그
    폐기. staging 자동 판정 + `--quick`/`--deep`/`--no-review`로 단일화.
    pre-check `HARNESS_LEVEL` 파싱 제거, 위험도 수집 블록은 모드 불문 실행
  - MIGRATIONS.md v0.19.0 섹션 신설 (자동 적용 + 수동 액션 + 검증 + 회귀 위험)
  - HARNESS.json 0.18.8 → 0.19.0 minor 범프, promotion-log 행 추가
- 2026-04-22: **P0+P1+P2 일괄 커밋 실측 (audit #18·#12 실증)**
  - 31파일 일괄 staged 커밋 시도 → pre-check에서 **2종 오탐** 발견:
    1. **검사 A basename 과탐**: `docs-manager/SKILL.md` 삭제 시 다른
       `SKILL.md` 링크 전부 dead로 잡음. `removed_base=SKILL.md` →
       모든 `SKILL.md` grep 매치. **근본 수정**: basename grep은 1차
       후보 수집만, 2차로 매치 링크 경로 해석 → 실제 삭제 경로와
       일치할 때만 dead. T38.1 신설
    2. **검사 C 경로 해석 기준 불일치**: `rules/docs.md` 원본 규칙은
       `path: decisions/other.md` (docs/ 루트 기준). 초기 구현은
       `dirname(wip_file)/rt_path` (WIP 파일 기준) → `docs/WIP/harness/X.md`
       식으로 해석 오류. **근본 수정**: docs/ 루트 기준 해석, `../`·`./`
       로 시작하는 경우만 파일 기준. T36.7·T36.8 신설
  - 회귀 62 → 65 (T36.7·T36.8·T38.1). 최종 31파일 staged pre-check pass.
    `recommended_stage: deep`, signals `S2,S9,S10,S7`, 대규모 변경 경고
    stderr 출력 확인
  - **#18 실증 데이터**: 현재 상태로 자동 분리 판정 스크립트 없음.
    사용자 판단으로 분리 여부 결정. pre-check stderr 경고가 "분리 권장"
    메시지 역할. 자동화 필요 시 실측 5건 중 1건으로 본 커밋 기록
- 2026-04-22: **P2 구현 — 5개 완료 + 3개 실측 대기**
  - ✅ **#4 버전 체크 분리**: `harness-version-bump.sh` 신설 (is_starter
    가드 내장, 범프 타입 후보 제안만 — 실제 수정은 Claude/사용자).
    commit SKILL Step 3를 호출 한 줄로 축약
  - ✅ **#8 bash-guard 강제 경유**: 검증 4 추가 (`git commit` 직접 호출
    차단, `HARNESS_COMMIT_SKILL=1` or `HARNESS_DEV=1` prefix 필요,
    `--help`·`--dry-run` 통과). G1~G5 5케이스 신설 (18/18 통과).
    commit SKILL 커밋 실행 라인에 prefix 명시
  - ✅ **#10 docs-manager 폐기**: 332줄 스킬 삭제, `.claude/scripts/docs-ops.sh`
    신설 (validate / move / reopen / cluster-update / verify-relates 5개
    서브커맨드). HARNESS.json skills 목록에서 제거. 호출자(commit·review·
    implementation·harness-init/adopt/upgrade·doc-finder·rules/naming·
    rules/docs) 전부 포인터 교체
  - 부분 ✅ **#17 S6 자동화**: pre-check 룰 3에 "S6 단독 + ≤5줄 →
    skip" 추가. `.claude/skills/`·`agents/` 예외 (동작 규약 문서라 1줄도
    standard 유지). T37 3케이스 (62/62 통과). S8 정밀화·폭증 게이트는
    #13 실측 대기
  - 🔲 **#13 2번 review 구조**: 실측 5건 누적 중 (4건 완료). 1건 더 후
    A/B/C/D/E/F 중 채택
  - 🔲 **#16 세션 파일명 규칙**: harness-adopt 실행 사례 대기
  - 🔲 **#18 커밋 분리 전략**: 실측 5건 + `hn_commit_perf_optimization` §4
    시간 리포팅 후 결정

## 후속

본 문서는 **결정 방향 기록**. 각 항목은 독립 커밋·후속 WIP으로 실행.
결정 뒤집기 필요 시 본 문서 갱신 + `## 변경 이력`.

**이번 세션 자기 실측의 핵심 교훈**:
- 감사·결정 문서 작성은 **실측 없이 쓰면 추측의 집합**이 됨
- no-speculation.md "단정형 추측 금지" 원칙이 감사 문서에도 적용되어야
- specialist 호출이 감사의 검증 장치로 편입될 때 감사 품질 향상 확인됨
