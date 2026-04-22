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

## 후속

본 문서는 **결정 방향 기록**. 각 항목은 독립 커밋·후속 WIP으로 실행.
결정 뒤집기 필요 시 본 문서 갱신 + `## 변경 이력`.
