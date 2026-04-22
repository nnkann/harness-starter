---
title: 다운스트림 마이그레이션 가이드
domain: harness
tags: [migration, upgrade, downstream]
status: completed
created: 2026-04-19
---

# 다운스트림 마이그레이션 가이드

각 하네스 버전이 다운스트림 프로젝트에 요구하는 **수동 액션**을 정리한다.
`harness-upgrade` 스킬이 자동 병합하지만, **다음 항목은 사람이 직접
판단·입력**해야 한다.

스킬이 업그레이드 마지막 단계에서 본 문서를 읽고 새 버전 섹션을 사용자
에게 보여준다. 자동 채워지는 항목과 수동 액션이 명확히 분리되어야 silent
fail을 막는다.

> **버전 다운그레이드 노트 (2026-04-19):** 1.6.x~1.9.0으로 표기됐던
> 버전을 0.x로 리셋. semver 0.x가 "공개 API 불안정·실험 단계"이며
> 현재 상태와 정확히 일치. 섹션 헤더를 실제 적용 버전으로 갱신:
>
> | 구 표기 | 현 표기 | 내용 |
> |---|---|---|
> | v1.7.0 | v0.6.0 | 하네스 단순화 P0 |
> | v1.8.0 | v0.6.1 | 다운스트림 마이그레이션 인프라 |
> | v1.8.1 | v0.6.2 | pre-check lint stdout 오염 수정 |
> | v1.9.0 | v0.7.0 | Bash matcher 광역 패턴 폐기 |

## 포맷

각 버전 섹션은 다음 구조를 따른다:

```
## vX.Y.Z (요약)

### 자동 적용 (스킬이 처리)
- 어떤 파일이 자동 덮어씌워지는지

### 수동 액션 (사용자 필수)
- [ ] 체크박스 항목. 각 항목에 명령·예시·위치 포함

### 검증
- 적용 후 무엇으로 확인하는지 (test 스크립트·grep 등)

### 회귀 위험
- 기존 동작이 바뀌는 부분
```

---

## v0.20.7 — promotion-log.md 폐기

**호환성 변화 있음. 수동 액션 필요.**

### 왜

`docs/harness/promotion-log.md`는 매 커밋마다 Claude가 수동으로 row를
append해야 하는 관리 비용이 높은 파일이었다. commit 메시지 제목의
`(v0.X.Y)` 패턴이 이미 버전 이력 SSOT 역할을 하므로, 수동 요약 파일은
SSOT 원칙(코드에서 읽을 수 있는 것은 memory에 저장하지 않는다, `git log`
로 알 수 있는 것은 중복 저장하지 않는다)에 반한다.

### 자동 (harness-upgrade)

- `docs/harness/promotion-log.md` — upstream에서 삭제됨. 3-way merge 모드
  (`installed_from_ref` 유효)에서는 "삭제 제안"으로 표시
- `docs/archived/promotion-log-2026q2-early.md` — 동일
- `.claude/scripts/pre-commit-check.sh` — `IS_STARTER` 변수 제거 (orphan),
  S5 awk 두 분기 → 단일 regex, S10 REPEAT_EXEMPT_REGEX에서 promotion-log
  경로 제거
- `.claude/scripts/task-groups.sh` — `is_meta_file()` case에서 제거
- `.claude/scripts/harness-version-bump.sh` — 주석 수정
- `.claude/scripts/test-pre-commit.sh` — T30을 `HARNESS.json 단독 → skip`
  으로 대체 (S5 skip 검증 공백 방지)
- `.claude/rules/memory.md`·`staging.md` — promotion-log 언급 제거
- `.claude/skills/commit/SKILL.md` — Step 3 버전 범프 절차에서 promotion-log
  갱신 단계 삭제, 메타 자동 병합 목록에서 제거
- `h-setup.sh` — 이식 시 promotion-log 복사 줄 제거
- `docs/clusters/harness.md` — 전역 마스터 · archived · 관계 맵 7줄 제거
- 7개 결정·하네스 문서 frontmatter — `relates-to.path: harness/promotion-log.md`
  블록 제거

### 수동 액션 (사용자 필수)

- [ ] **`docs/harness/promotion-log.md` 존재하면 삭제**:
  ```bash
  git rm docs/harness/promotion-log.md
  git rm docs/archived/promotion-log-*.md  # (있는 경우)
  ```
  `h-setup.sh`의 `copy_if_new`는 기존 파일을 덮어쓰지 않으므로 업그레이드
  후에도 다운스트림 리포에 고아로 남을 수 있다. 수동 삭제 필요.

- [ ] **two-way 모드 upgrade인 경우**: `installed_from_ref`가 없어 "삭제
  제안"이 뜨지 않는다. 위 수동 삭제로 대응.

- [ ] **버전 이력 회고 방법 전환**:
  - 이전: `docs/harness/promotion-log.md` 열기
  - 이후: `git log --oneline --grep "(v0\."` 또는 MIGRATIONS.md
  - commit 메시지 제목에 반드시 `(v0.X.Y)` 포함 — 이것이 새 SSOT

- [ ] **자동화 스크립트가 promotion-log.md를 읽던 경우** 전수 검사:
  ```bash
  grep -rn "promotion-log" . --include='*.sh' --include='*.md' --include='*.js'
  ```
  hit 있으면 git log 기반으로 전환.

### 검증

- `bash .claude/scripts/test-pre-commit.sh` → 64/64 (T30 대체 케이스 통과)
- `bash .claude/scripts/pre-commit-check.sh` — promotion-log 관련 dead link
  감지 0건

### 회귀 위험

- **T30 케이스 재정의**: 기존 `promotion-log 단독 → skip`이 `HARNESS.json
  단독 → skip`으로 대체됨. 다운스트림이 test 결과를 참조하는 외부 스크립트
  가 있으면 T30 fixture 이름 변경 확인 필요
- **IS_STARTER 변수 제거**: `pre-commit-check.sh`에서 orphan 제거. 다운
  스트림이 이 변수를 참조하는 커스텀 확장이 있었다면 깨짐. 본 업스트림
  에서는 사용 0 확인
- **git log 규율 의존**: 회고가 commit 메시지 품질에 의존. `(v0.X.Y)`
  패턴 누락 시 이력 추적 공백 발생. commit 스킬 Step 3가 규칙화

---

## v0.20.5 — 커밋 이스케이프 단일화 (HARNESS_COMMIT_SKILL 폐기)

**요약**: `git commit` 직접 호출 차단(audit #8)의 이스케이프가 기존
`HARNESS_COMMIT_SKILL=1`·`HARNESS_DEV=1` 2개였으나 `HARNESS_DEV=1` 단일
로 축소. `HARNESS_COMMIT_SKILL=1`은 더 이상 bash-guard를 통과시키지
못한다 (exit 2 차단).

### 배경

Claude가 `HARNESS_COMMIT_SKILL=1 git commit`을 **수동으로 쓰는 경로**가
commit 스킬 우회 창구가 됐다. prefix의 존재 이유는 "commit 스킬이 호출
했다는 증거"였는데, Claude가 그 prefix를 직접 타이핑하면 bash-guard는
구별할 방법 없이 통과시켰다. Claude의 자기 절제에 의존하는 메커니즘은
규율이 되지 못한다는 판단.

### 자동 (harness-upgrade)

- `.claude/scripts/bash-guard.sh` 검증 4 — `HARNESS_(DEV|COMMIT_SKILL)`
  정규식에서 `COMMIT_SKILL` 제거. `HARNESS_DEV=1` 단일 매칭
- `.claude/scripts/split-commit.sh` 안내 문구 `HARNESS_SPLIT_SUB=1
  HARNESS_DEV=1`로 축소
- `.claude/scripts/test-bash-guard.sh` G2 케이스 expected 0 → 2 (의미
  역전: 과거 "통과" → 현재 "차단")
- `.claude/skills/commit/SKILL.md` 커밋 실행 문법 `HARNESS_DEV=1 git commit`

### 수동 액션 (사용자 필수)

- [ ] **자동화 스크립트·CI에서 `HARNESS_COMMIT_SKILL=1` 쓰는 곳 전수
      검사**. 있으면 `HARNESS_DEV=1`로 교체. 다운스트림이 커스텀 커밋
      스크립트를 갖고 있었다면 v0.20.5 업그레이드 직후 exit 2 발생

### 검증

- `bash .claude/scripts/test-bash-guard.sh` → 18/18 (G2 의미 역전 반영)
- 다운스트림: `grep -r "HARNESS_COMMIT_SKILL" .` 으로 잔재 검색 후 교체

### 회귀 위험

- **이스케이프 하나 남음**: `HARNESS_DEV=1`. Claude가 이것도 수동으로
  쓸 수 있어 완전 차단은 아님. "최소 수정" 목표에 따른 현실적 타협
  — 사용자가 명시적으로 긴급 시에만 쓰는 경로로 유지. 근본 차단을
  원하면 pre-commit hook으로 책임 이전 구조 재설계 필요 (별도 WIP)
- **설계 버그는 별도 커밋(v0.20.6)**: 이 버전은 이스케이프 **정책**만
  변경. bash-guard의 `^git commit` 매칭이 `HARNESS_X=1 git commit`
  형태에서 블록 진입조차 못 하던 설계 버그는 다음 커밋에서 fix

---

## v0.20.0 — 커밋 프로세스 감사 P2 반영 (audit #4·#8·#10·#17)

### 자동 적용 (스킬이 처리)

- `.claude/scripts/harness-version-bump.sh` **신설** (audit #4): 하네스
  스타터 전용 버전 체크 스크립트. is_starter 가드 내장 — 다운스트림은
  즉시 exit 0. staged 변경 분석해 `version_bump: minor|patch|none` 출력
  (안내만, 실제 범프는 Claude/사용자 수동)
- `.claude/skills/commit/SKILL.md` Step 3: 기존 35줄 설명 → `bash .claude/
  scripts/harness-version-bump.sh` 호출 + 범프 기준 표만 유지
- `.claude/scripts/bash-guard.sh` **검증 4 신설** (audit #8): `git commit`
  직접 호출 차단. `HARNESS_DEV=1` prefix 없으면 exit 2. `--help`·`--dry-run`
  읽기 전용은 통과 (v0.20.5 업데이트: `HARNESS_COMMIT_SKILL=1` 이스케이프
  폐기, `HARNESS_DEV=1` 단일화)
- `.claude/scripts/test-bash-guard.sh` G1~G5 5케이스 신설 (18/18 통과)
- `.claude/skills/commit/SKILL.md` 커밋 실행 라인에 `HARNESS_DEV=1`
  prefix 명시
- `.claude/skills/docs-manager/` **삭제** (audit #10): 332줄 스킬 폐기
- `.claude/scripts/docs-ops.sh` **신설** (audit #10): 5개 서브커맨드
  - `validate`: 프론트매터·약어 검증
  - `move <wip-file>`: WIP 접두사 기반 이동 + status=completed +
    차단 키워드 검사
  - `reopen <completed-file>`: 완료 문서를 WIP로 되돌림 + status=in-progress
  - `cluster-update`: naming.md 약어 표 기반 `docs/clusters/*.md` 자동 재생성
  - `verify-relates`: 전수 relates-to.path 정합성 검사
- `.claude/HARNESS.json` `skills` 목록에서 `docs-manager` 제거
- 호출자 모두 포인터 교체:
  - `.claude/skills/commit/SKILL.md` Step 2
  - `.claude/skills/implementation/SKILL.md`
  - `.claude/skills/harness-init/SKILL.md` Step 7
  - `.claude/skills/harness-adopt/SKILL.md` Step 5g
  - `.claude/skills/harness-upgrade/SKILL.md` Step 9
  - `.claude/agents/review.md` 주석
  - `.claude/agents/doc-finder.md` SKIP 섹션
  - `.claude/rules/naming.md` / `.claude/rules/docs.md`
- `.claude/scripts/pre-commit-check.sh` 룰 3 S6 자동화 (audit #17):
  "S6 단독 + TOTAL_LINES ≤5 → skip". 단 `.claude/skills/`·`agents/`
  경로는 예외 (1줄 수정도 동작 규약 변경 가능, standard 유지)
- `.claude/scripts/pre-commit-check.sh` dead link 검사 2종 **근본 수정**
  (v0.20.0 커밋 실측으로 발견):
  - 검사 A: basename grep 결과를 **경로 해석 후 실제 삭제 경로와 일치**
    할 때만 dead 판정 (이전: basename 일치만으로 dead → 같은 이름 다른
    경로 md 오탐)
  - 검사 C: `rules/docs.md` 원본 규칙(`docs/` 루트 기준)에 맞춰 해석
    (이전: `dirname(file)/rt_path` → WIP 파일 기준 해석 오류)
- `.claude/scripts/test-pre-commit.sh` T36.7·T36.8·T37(3건)·T38.1 추가
  (65/65 통과)

### 수동 액션 (사용자 필수)

- [ ] **커밋 시 `HARNESS_DEV=1` prefix 필수화**. 이전에 Bash
      `git commit`을 직접 호출하던 흐름은 bash-guard 검증 4로 차단됨.
      (v0.20.5부터 이스케이프 `HARNESS_DEV=1` 단일 — 과거 `HARNESS_COMMIT_SKILL=1`
      은 폐기)
- [ ] **docs-manager 스킬을 직접 Skill tool로 호출하던 커스텀 흐름이
      있으면 `docs-ops.sh` 서브커맨드로 교체**. 서브커맨드 매핑:
  - `docs-manager --validate` → `bash .claude/scripts/docs-ops.sh validate`
  - `docs-manager --move` → `bash .claude/scripts/docs-ops.sh move <file>`
  - `docs-manager --reopen` → `bash .claude/scripts/docs-ops.sh reopen <file>`
  - `docs-manager` cluster 갱신 → `bash .claude/scripts/docs-ops.sh cluster-update`
  - `docs-manager` 관계 검증 → `bash .claude/scripts/docs-ops.sh verify-relates`
- [ ] 기존 `docs/clusters/*.md`에 frontmatter가 없으면 `docs-ops.sh
      cluster-update` 한 번 실행해 재생성 (validate가 "title 누락"
      경고할 것)
- [ ] 다운스트림 CPS 로직이 docs-manager Step 6에 의존했다면 implementation·
      write-doc 상위 흐름에서 처리됐는지 확인 (audit #10 재정의 — CPS는
      스크립트화된 반영만 담당)

### 검증

- `bash .claude/scripts/test-pre-commit.sh` → 62/62 통과
- `bash .claude/scripts/test-bash-guard.sh` → 18/18 통과
- `bash .claude/scripts/docs-ops.sh validate` → 기존 docs/ 규칙 위반
  감지 (clusters frontmatter 누락 등)
- `bash .claude/scripts/docs-ops.sh verify-relates` → 기존 relates-to
  경로 오류 보고 (실측상 60+건 존재 — 별도 정리 대상)
- `grep -r "docs-manager" .claude/` → 폐기 안내 주석 외 0 hit

### 회귀 위험

- **`git commit` 직접 호출이 전부 차단됨**. 자동화 스크립트·CI에서
  prefix 없이 `git commit`을 호출하면 exit 2. `HARNESS_DEV=1` prefix
  추가 필요 (v0.20.5 이후 단일 이스케이프)
- docs-manager 스킬을 Skill tool로 명시 호출하던 흐름은 전부 깨짐.
  스킬이 존재하지 않음
- S6 자동화로 docs-only ≤5줄 커밋이 skip됨. 이전에 standard였던
  경미 문서 수정은 review 호출 없이 바로 커밋. `.claude/skills/`·
  `agents/` 제외 조건은 upstream 격리 T37.3으로 검증됨
- docs-ops.sh 스크립트는 Windows Git Bash 환경에서 개발됨. Linux/macOS
  sed 호환성은 `-i.bak` 패턴으로 방어했으나 미테스트
- 실측 사례: 기존 `docs/clusters/harness.md`·`meta.md`에 frontmatter
  없음 → validate 오류. cluster-update로 재생성 권장

---

## v0.19.0 — 커밋 프로세스 감사 반영 (audit #1·#3·#5·#6·#7·#12·#14·#15·#2·9)

### 자동 적용 (스킬이 처리)

- `.claude/scripts/pre-commit-check.sh`
  - `--lint-only` 모드 제거 (audit #1). 린트+전체 검사 1회로 통합
  - 검사 C 신설 (audit #12): frontmatter `relates-to.path` dead link
    증분 검사. `awk`로 frontmatter 블록 추출 후 멀티라인 YAML 리스트
    순회. 앵커·missing path 처리 T35와 동형
  - test-strategist stdout key 제거 (audit #7·#15): `needs_test_strategist`
    ·`test_targets`·`new_func_lines_b64` 3개 key 전부 폐기
  - `HARNESS_LEVEL` 파싱 제거 (audit #2·9): 위험도 수집 블록은 유지하되
    light 모드 조건 해제. `risk_factors`는 staging 자동 판정과 무관하게
    review prompt 우선순위 가중치로 계속 사용
  - stderr 정책 (audit #14): 실패·위험·경고만 출력. `HARNESS_EXPAND`
    통과 알림은 `VERBOSE=1` 가드
- `.claude/scripts/test-pre-commit.sh` T11·T12·T20 제거, T36 6케이스 신설
- `.claude/scripts/downstream-readiness.sh` `needs_test_strategist:` 검사 제거
- `.claude/agents/test-strategist.md` 삭제 (audit #15 — 114초 실측 대비
  효용 부족)
- `.claude/skills/commit/SKILL.md`
  - Step 0 린트 조기 체크 제거 (audit #1). 린트는 Step 5에서만
  - "메타 파일 본문 박기" 섹션 전체 삭제 (audit #6). review가 Read로
    직접 조회하는 편이 정확
  - light/strict 모드 섹션 전면 제거 (audit #2·9). `--light`·`--strict`
    플래그 제거. staging 자동 판정 + `--quick`/`--deep`/`--no-review`만
    유지
  - test-strategist 병렬 호출 섹션 삭제 (audit #7)
  - Step 2 "진척도 자동 갱신" → Step 7.5 (review pass 직후, `git commit`
    직전)로 재배치 (audit #3)
  - Step 5 tree-hash 캐시 분기 삭제 (audit #5). Bash 변수 중심 + 필요
    시 background 파일 기록
- `.claude/skills/implementation/SKILL.md` test-strategist 참조 2곳 제거
- `.claude/skills/harness-init/SKILL.md` 하네스 강도 선택 단계 제거
- `.claude/skills/advisor/SKILL.md` / `.claude/agents/advisor.md`
  specialist 풀에서 test-strategist 삭제
- `.claude/rules/self-verify.md` test-strategist 연계 섹션 → Claude 직접
  판단 원칙으로 교체
- `.claude/rules/memory.md` 동적 snapshot 3개 → `session-pre-check.txt`
  1개로 축소 (audit #5)
- `.claude/agents/review.md` strict 언급 → `--deep`으로 수정

### 수동 액션 (사용자 필수)

- [ ] **CLAUDE.md**에서 `- 하네스 강도: light|strict` 줄 제거
      (`## 환경` 섹션). harness-upgrade가 자동 제거하지 않음 — 다운스트림
      내용 보존 원칙
- [ ] **`/commit --light`·`/commit --strict` 사용 중단**. 대신
      `/commit`(자동) / `/commit --quick` / `/commit --deep` /
      `/commit --no-review` 사용
- [ ] `.claude/memory/session-staged-diff.txt`·`session-tree-hash.txt`
      남아 있으면 삭제: `rm -f .claude/memory/session-staged-diff.txt
      .claude/memory/session-tree-hash.txt`
- [ ] test-strategist를 직접 호출하던 커스텀 hook·스킬 있으면 제거
- [ ] commit 메시지 템플릿에 "light 모드"·"strict 모드" 용어 있으면 삭제.
      `recommended_stage`(skip/micro/standard/deep) 기준으로 재작성

### 검증

- `bash .claude/scripts/test-pre-commit.sh` → 59/59 통과
- `bash .claude/scripts/test-bash-guard.sh` → 13/13 통과
- `grep -r "하네스 강도" .claude/ CLAUDE.md` → 0 hit
- `grep -r "test-strategist\|--light\|--strict" .claude/ CLAUDE.md` →
  폐기 안내(주석·MIGRATIONS) 외 0 hit

### 회귀 위험

- **`/commit --light`·`--strict` 플래그 사용 중이던 스크립트·문서는
  깨짐**. 플래그 자체가 제거되어 커밋 스킬이 무시. 대체 플래그로 교체
  필요
- `needs_test_strategist`·`test_targets`·`new_func_lines_b64` stdout key
  파싱하던 커스텀 도구는 값을 못 받음. 해당 도구 수정 필요
- tree-hash 캐시 재사용하던 외부 도구 있으면 재commit 시 매번 pre-check
  재실행 (설계 의도)
- upstream 격리 환경(Windows/Git Bash)에서 T36 6케이스 + 기존 T35 회귀
  확인 완료. 다른 OS/패키지 매니저 미테스트

---

## v0.18.6 — dead link 검사 pre-check 이식 (증분)

### 자동 적용 (스킬이 처리)

- `.claude/scripts/pre-commit-check.sh` Step 3.5 신설 — dead link 증분 감지
  - **검사 A**: 삭제·rename된 md를 가리키는 기존 md 링크 감지. basename
    기반 grep, 같은 커밋에 포함된 소스 파일은 skip
  - **검사 B**: 추가·수정된 md의 새 링크 대상 존재 검증. staged diff의
    `+` 라인에서 `](path.md)` 패턴만 awk로 추출 → 경로 정규화 → `test -f`
  - 증분 검사 (O(변경 규모)). (과거 전수 검사는 `bulk-commit-guards.sh` 4b에 있었으나 bulk 스테이지 자체가 2026-04-22 폐기됨)
- `.claude/scripts/test-pre-commit.sh` T35 회귀 테스트 3케이스 추가
  - T35.1: 파일 삭제 + cluster 옛 경로 유지 → 차단 기대
  - T35.2: 새 md의 링크가 없는 파일 가리킴 → 차단 기대
  - T35.3: 링크 대상도 같이 staged 추가 → 통과 기대
  - 결과: 60/60 (기존 57 + T35 3)

### 왜

v0.18.5 커밋 review deep이 `docs/clusters/harness.md`의 dead link 2건을
잡아 block. 이후 사용자 지적:
> "dead link는 pre-check에서 걸러야 하는게 아닌가?"

설계 원칙 위반이 발견됨:
- staging.md: "정적 검사는 pre-check, 의미는 review"
- dead link는 구조적 정합성 (파일 존재 여부) → 정적 검사 영역
- (v0.18.6 시점) bulk-commit-guards.sh 4b에만 있음 → `--bulk` 경로만 커버. 일반
  커밋은 비싼 LLM review에 의존
- review deep(30초+, 58k tokens)이 떠맡던 일을 pre-check(수 초)이 대신
  → 사용자 체감 속도 개선 + 설계 정합성 복구

### 수동 액션 (다운스트림)

- [ ] **업그레이드 후 기존 커밋 흐름 확인 (권장)**

  기존 커밋에 의도적으로 dead link가 있었다면 (예: 임시 참조) 새
  pre-check이 차단할 수 있음. 링크를 수정하거나 별도 우회 필요 시 보고.

- [ ] **다운스트림 cluster 정합성 점검 (권장)**

  `docs/clusters/*.md`가 실제 파일 경로와 일치하는지 확인. 옛 파일·이동된
  파일을 가리키는 링크가 있으면 수정. 현 pre-check은 "이번 커밋이 유발한"
  dead link만 잡지만, 기존 dead link는 **다음 관련 커밋에서 차단될 수 있음**.

### 검증

```bash
bash .claude/scripts/test-pre-commit.sh 2>&1 | tail -5
# 통과 60 / 실패 0 — T35 3 케이스 포함
```

**검증 범위**: Windows/Git Bash에서 T35 fixture 실측 (60/60). basename
기반 매칭의 오탐 여지는 실측 관찰 필요.

### 회귀 위험

- **basename 매칭의 오탐 가능성** — 다른 폴더에 같은 이름 md가 있으면
  "잘못된 dead link" 경고 가능. 다운스트림에서 실측 관찰 필요. 엄밀 경로
  매칭은 비용 크고, 1차 방어 취지라 수용
- **증분 검사의 miss** — 이번 커밋이 직접 건드리지 않은 기존 dead link는
  감지 안 함. 기존 dead link가 누적된 레포에선 한 번 전수 점검 권장
  (수동으로 `grep -rE '\]\([^)]*\.md[^)]*\)' docs .claude` 후 `test -f`
  등으로 확인).

---

## v0.18.5 — SSOT 선행 탐색 3층 방어 구조화

### 자동 적용 (스킬이 처리)

- `CLAUDE.md` `<important if="docs/ 하위에 새 문서·WIP 파일을 만들려
  할 때 (스킬 발동 여부 무관)">` 블록 추가 — 경로 불문 트리거
- `.claude/rules/docs.md` "## SSOT 우선 + 분리 판단" 섹션 확장:
  - **3단계 탐색** 절차 의무화: cluster 스캔 → 키워드 grep → 후보 본문 Read
  - **실패 모드 체크리스트** 5개: cluster만 봄 / 제목만 봄 / 동격 선택지
    제시 / completed라고 건너뜀 / 일단 새 WIP 쓰고 병합
  - "기본값은 기존 SSOT 갱신" 명시
- `.claude/skills/write-doc/SKILL.md` Step 2 재작성 — docs.md 참조 +
  분기표 + 완료 문서 재개 경로 (중복 서술 제거)
- `.claude/skills/implementation/SKILL.md` Step 0.8에 3단계 탐색·실패
  모드 체크리스트 명시 인용 (이미 docs.md 참조하던 위치에 보강)

### 왜

v0.18.4 커밋 직후 같은 세션에서 Claude가 기존 SSOT 3건이 이미 해당
주제를 커버 중인 상태에서 중복 WIP를 즉흥 생성. 사용자 지적으로 재발
패턴 자인.

원인 분석:
- **write-doc SKILL.md Step 2 부실**: cluster 1회 스캔만, 본문 Read 없음
- **CLAUDE.md 트리거 부재**: 스킬 발동하지 않는 "즉흥적 Write" 경로
  (논의 중 그냥 파일 생성) 미커버
- **docs.md 규정 자체는 정합하나 스킬 절차가 규정을 인용 안 함**

3층 방어 구조:

| 층 | 위치 | 역할 |
|---|------|------|
| 1 | `CLAUDE.md` `<important if>` | 경로 불문 트리거 — Write tool 호출 전 |
| 2 | `.claude/rules/docs.md` | 규정 SSOT — 절차·체크리스트·완료 재개 경로 |
| 3 | 스킬 SKILL.md | 스킬 진입점 — docs.md 참조 + 분기 흐름 |

원칙: **절차는 한 곳에만** (docs.md). 스킬·CLAUDE.md는 참조·트리거만.

### 수동 액션 (다운스트림)

- [ ] **업그레이드 후 기존 쓰기 흐름 점검 (권장)**

  다운스트림이 CLAUDE.md를 커스터마이징했으면 새 `<important if>` 블록이
  병합되는지 확인. `harness-upgrade` 스킬이 처리하지만 수동 확인 권장.

- [ ] **다음 문서 생성 시 3단계 탐색이 실제로 돌아가는지 관찰**

  수정의 실효성은 실측으로 확인. 다음 5건의 문서/WIP 생성에서 Claude가
  cluster·grep·본문 Read 3단계를 밟는지, SSOT 후보를 놓치지 않는지 관찰.

### 검증

- 업스트림에서 본 커밋 자체가 새 절차를 실측 (기존 SSOT 재개해 append,
  신규 WIP 생성 안 함)
- 완료 문서 재개 경로 (`git mv` → status in-progress) 실동작 확인
- write-doc·implementation 스킬의 docs.md 참조 링크 정합성 (Grep 확인)

**검증 범위**: 본 커밋의 자기 적용 흐름만. 다음 5건 실측은 다운스트림·
업스트림 누적 관찰 필요.

### 회귀 위험

- **docs.md "SSOT 우선 + 분리 판단" 섹션 확장** — 기존 두 질문은 유지,
  3단계 탐색·체크리스트가 **선행 절차로 추가**. 기존 호출자(write-doc
  Step 2·implementation Step 0.8)가 두 질문만 인용하던 경우 새 절차를
  놓칠 가능성 → 이번 커밋에서 두 스킬 모두 명시 인용으로 보강함
- **실효성은 실측 필요** — 규정·스킬 정합성은 확보했으나 Claude가 실제로
  준수하는지는 "다음 5건" 관찰에 달림. 규정만으로 재발 방지 보장 없음

---

## v0.18.4 — 린터 ENOENT 패턴 정교화 (오탐·OS 커버리지 fix)

### 자동 적용 (스킬이 처리)

- `.claude/scripts/pre-commit-check.sh` 린터 단계 ENOENT 패턴 재작성
  - **제거** (ESLint 내부 crash와 구분 불가): `No such file or directory`,
    `Cannot find module`, `ENOENT`
  - **추가** (OS 커버리지): zsh `command not found: X$`, Alpine
    `exec: X: not found$`, Dash `sh: N: X: not found$`, pnpm
    `ERR_PNPM_RECURSIVE_EXEC_FIRST_FAIL`
- `.claude/scripts/test-pre-commit.sh` T33·T34 회귀 테스트 신설 (12 케이스)
  - T33: 7개 shell 실종 형식 매칭 (Windows cmd · bash · zsh · sh ·
    Alpine · Dash · pnpm)
  - T34: 5개 crash·rule 위반 차단 유지 (import resolver ENOENT · 플러그인
    missing · rule 위반 · node trace · syntax error)
  - 패턴 SSOT는 `ENOENT_PATTERN` 변수로 pre-check과 동기화
- `.claude/rules/no-speculation.md` "MIGRATIONS.md 회귀 위험 섹션 작성
  원칙" 추가 — `겹치지 않음`·`영향 없음` 같은 근거 없는 단정 금지,
  검증 범위 명시 의무

### 왜

v0.18.3 fix 이후 다운스트림 review 에이전트가 MIGRATIONS.md의 단정
("실제 ESLint·Ruff 출력과 겹치지 않음")을 **역으로 검증**해 오탐과 OS
커버리지 갭을 지적:

- **오탐**: `No such file or directory`·`Cannot find module`·`ENOENT`는
  ESLint `import/no-unresolved` crash와 플러그인 missing 에러에도 등장.
  rule 위반이 warn으로 격하되는 오분류 위험
- **갭**: Alpine Docker·Dash/POSIX sh·pnpm에서 쓰이는 실종 메시지 형식
  미커버. CI/CD가 `node:alpine` 이미지를 쓰면 도구 실종이 차단으로 회귀

실측 과정에서 **다운스트림 제안 A안의 zsh 형식도 T33.3이 FAIL로 잡음**.
제안을 그대로 반영하지 않고 회귀 테스트로 검증한 것이 결과적으로 옳았음.

### 수동 액션 (다운스트림)

- [ ] **v0.18.3 이하 다운스트림은 즉시 upgrade 권장**

  v0.18.3 패턴이 Alpine CI/CD에서 **매 커밋 차단** 회귀를 일으킬 수 있음.
  v0.18.4로 해결.

- [ ] **MIGRATIONS.md "회귀 위험" 단정 감사 (권장)**

  로컬 하네스 문서에 `겹치지 않음`·`영향 없음` 단정이 있으면 근거 추가
  또는 범위 명시로 교체. no-speculation.md 새 섹션 참조.

### 검증

upstream 격리 환경(Windows/Git Bash)에서 실측:

```bash
bash .claude/scripts/test-pre-commit.sh 2>&1 | tail -5
# 통과 57 / 실패 0 — T33·T34 12 케이스 포함

# 패턴 오탐 테스트 — 정상 ESLint crash는 차단 유지
echo "Error: Cannot find module 'eslint-plugin-react'" \
  | grep -qE "$ENOENT_PATTERN" && echo "❌ 오탐" || echo "✅ 차단 유지"
```

**검증 범위**: Windows/Git Bash에서 T33·T34 fixture 실측. Linux/macOS
실기기 테스트는 미수행 — 패턴 자체는 shell prompt 고유 형식 기반이라
OS 독립적일 것으로 **추정**하나 실측 아님.

### 회귀 위험

- **Windows/Git Bash 환경에서 T33·T34 통과 확인됨** — 다른 OS 미테스트.
  Alpine/macOS/Linux 실환경 실측은 다운스트림이 보고하면 fixture 확장
- **`Cannot find module` block 유지 결정** — 플러그인 missing을 warn으로
  격하하면 다운스트림이 린트가 실제로 돌지 않는 걸 모름. 정책적으로
  block. 플러그인 설치 안내를 더 명확히 하고 싶다면 별도 개선

---

## v0.18.3 — 린터 도구 실종 구분 (T13.1 원인 확정)

### 자동 적용 (스킬이 처리)

- `.claude/scripts/pre-commit-check.sh` 린터 단계에 **ENOENT 구분** 추가
  - 도구 실종 패턴(`is not recognized as an internal or external command`·
    `command not found`·`No such file or directory`·`Cannot find module`·
    `ENOENT`) 감지 시 → **warn + skip** (ERRORS 증가 없음, 커밋 계속)
  - 실제 rule 위반 → 기존대로 **차단**
- `docs/incidents/hn_test_isolation_git_log_leak.md` 전면 재작성
  - 제목: `T13 격리 실패 — 다운스트림 git log 교차 오염` → `린터 도구
    실종 — T13이 우연히 가시화한 환경 이슈`
  - status: in-progress → **completed**
  - v0.18.1·0.18.2 가설 이력 + 진짜 원인 확정 과정 + 교훈 본문화
  - 파일명 `git_log_leak`은 초기 가설 유래라 보존(링크 깨짐 방지) + 상단
    주석으로 명시

### 왜

다운스트림 `TEST_DEBUG=1` dump 결과:
```
'eslint' is not recognized as an internal or external command
'next' is not recognized as an internal or external command
```

**진짜 원인은 `node_modules` 누락/PATH 문제** — `npm run lint`가 ENOENT로
exit 2 → pre-check exit 2 → T13.1 FAIL. 다른 테스트가 PASS로 보인 건
run_case가 stderr를 버리고 stdout key-value만 봐서 린터 실패를 감지 못한
구조적 은폐. T13이 유일하게 `exit_code`를 직접 체크해서 가시화.

"실수를 코드화" 원칙: **환경 문제와 rule 위반을 동일 처리하면 매 커밋
차단 마찰 발생**. 분리해 환경은 warn, rule은 block.

### 수동 액션 (다운스트림 필수·권장)

- [ ] **`npm install` 실행 (근본 해결)**

  ```bash
  cd <downstream-repo>
  npm install   # 또는 pnpm install / yarn / bun install
  ```

  node_modules 복구 후 pre-check이 정상 린터 실행. upstream fix는 환경
  마찰 완화이지 근본 해결 아님.

- [ ] **lint 설정 확인**

  `package.json`의 `"lint"` 스크립트가 실제 린터를 참조하는지 확인.
  ESLint를 쓰면 `eslint`가 dependencies에 있어야 하고, `node_modules/.bin/
  eslint`가 있어야 npm run이 찾을 수 있음.

- [ ] **v0.18.1·0.18.2 incident 문서 참조 중단**

  이전 버전의 "git log 교차 = 원인" 서술은 철회된 가설. 현재 incident
  본문이 진짜 원인·해결·교훈 담음.

### 검증

```bash
# 1. 린터 정상 작동 시 rule 위반이 기존대로 차단되는지
echo 'const unused = 1' > src/test.js   # ESLint no-unused-vars 트리거 가정
git add src/test.js
bash .claude/scripts/pre-commit-check.sh 2>&1 | grep "❌ 린터 에러"
# 라인 나오면 정상 (rule 위반 차단)

# 2. 도구 실종 시 warn만 나오는지
PATH="/usr/bin" bash .claude/scripts/pre-commit-check.sh 2>&1 | grep "⚠ 린터 도구 미설치"
# 라인 나오면 정상 (warn + skip)

# 3. 전체 회귀
bash .claude/scripts/test-pre-commit.sh 2>&1 | tail -5
# 45/45 기대 (upstream 격리 기준)
```

### 회귀 위험

- **오탐 가능성** — ESLint 출력에 우연히 ENOENT 문자열이 섞이면 rule
  위반이 warn으로 격하될 수 있음. 완화: 패턴을 **엄격한 문자열 매칭**
  으로 제한 (위 5개만). 실제 ESLint·Ruff 출력과 겹치지 않음
- **환경 문제가 은폐됨** — warn으로 스킵되므로 다운스트림이 node_modules
  문제를 방치할 수 있음. 완화: warn 메시지에 `npm install` 검토 안내
  명시 + MIGRATIONS.md 수동 액션으로 강조

---

## v0.18.2 — T13 재진단 훅 (원인 미확정)

### 자동 적용 (스킬이 처리)

- `.claude/scripts/test-pre-commit.sh` T13 FAIL 분기에 `TEST_DEBUG=1`
  옵트인 훅 추가 — 캡처된 `$output`(pre-check stdout+stderr)을 dump
- `docs/incidents/hn_test_isolation_git_log_leak.md` 정정
  - status: completed → **in-progress** (원인 미확정 자인)
  - v0.18.1의 "git log 교차" 가설은 **한 측면만 해결**이었다고 명시
  - 재진단 프로토콜(`TEST_DEBUG=1`) 본문에 추가

### 왜

v0.18.1 fix(파일명 unique화) 적용 후에도 다운스트림(`<프로젝트 사례>`)
에서 T13.1 exit 2 지속. unique 파일명이면 git history 교차 자체가
불가능 → **최초 가설이 원인이 아님** 자인. 실제 exit 2 사유는 스위트
내부 FAIL 분기가 stderr를 캡처만 하고 출력하지 않아 미확인 상태.

A안(unique 파일명)은 "고정 경로 교차 가능성" 봉쇄라는 별개 가치가 있어
유지. 하지만 **다운스트림 실제 실패의 원인은 별건으로 재조사 필요**.

### 수동 액션 (다운스트림 필수)

- [ ] **T13 FAIL 지속 시 TEST_DEBUG=1로 재실행**

  ```bash
  cd <downstream-repo>
  TEST_DEBUG=1 bash .claude/scripts/test-pre-commit.sh 2>&1 \
    | sed -n '/\[T13\]/,/\[T14\]/p'
  ```

  출력된 `[pre-check 출력 dump]` 섹션의 `❌ ...` 라인이 exit 2 이유.
  upstream에 공유해주시면 v0.18.3에 실제 fix 반영.

- [ ] **이전 incident 문서(0.18.1 버전) 참조 중단**

  `docs/incidents/hn_test_isolation_git_log_leak.md` 본문이 진행 중 상태
  로 정정됨. v0.18.1의 "git log 교차 = 원인" 서술은 철회된 가설.

### 검증

```bash
# upstream starter에서 훅 동작 확인 (기본은 비활성)
bash .claude/scripts/test-pre-commit.sh 2>&1 | grep -c "pre-check 출력 dump"
# 0이어야 함 (TEST_DEBUG=0이 기본)

# TEST_DEBUG=1로 훅 활성화 확인
TEST_DEBUG=1 bash .claude/scripts/test-pre-commit.sh 2>&1 | grep "T13.1"
# upstream에서는 T13.1 PASS라 dump 안 나옴 — 정상
```

### 회귀 위험

- **운영 로직·테스트 본체 무변경** — pre-commit-check.sh·staging.md·
  review.md 등 운영 스크립트 및 rules 건드리지 않음. 훅은 FAIL 시에만
  동작하는 옵트인 디버그 출력
- **incident 문서 재작성** — 다운스트림이 이전 버전을 참조 중이었으면
  "git log 교차 = 원인" 서술이 혼란을 줄 수 있음. 정정된 버전으로 교체

---

## v0.18.1 — T13 테스트 격리 fix

### 자동 적용 (스킬이 처리)

- `.claude/scripts/test-pre-commit.sh` T13 파일명 unique화 — 고정
  `docs/WIP/test--scenario_260419.md` → `test--scenario_$$_$(date +%s).md`

### 왜

v0.18.0 병합 후 다운스트림(`<프로젝트 사례>`)에서 T13.1만 FAIL (44/45).
업스트림 격리 clone은 45/45. 원인은 T13이 만드는 prep 커밋의 **고정 파일
경로**가 다운스트림 repo 히스토리와 교차 오염 → `git log -5 <file>` S10
카운트가 예상 범위 이탈.

상세: `docs/incidents/hn_test_isolation_git_log_leak.md`.

### 수동 액션 (다운스트림 필수·권장)

- [ ] **T13 FAIL 보고 있었으면 재실행**

  ```bash
  bash .claude/scripts/test-pre-commit.sh | tail -5
  # 기대: 통과 45 / 실패 0
  ```

  여전히 실패 시 incident symptom-keywords(`T13.1 repeat_count 다운스트림
  격리 실패`)로 추가 조사.

- [ ] **잔재 파일 정리 (선택)**

  이전 실패로 `docs/WIP/test--scenario_260419.md`가 untracked로 남아 있을
  수 있음. git status로 확인 후 수동 삭제 (reset 함수는 git tracked만
  정리).

### 검증

```bash
bash .claude/scripts/test-pre-commit.sh 2>&1 | grep -E "T13|결과|통과:"
# T13.1 PASS · T13.2 max=2 PASS · 통과 45 실패 0 기대
```

### 회귀 위험

- **운영 로직 무변경** — pre-commit-check.sh·staging.md·review.md 등 운영
  스크립트 및 rules 건드리지 않음. 테스트 파일 5줄 수정만
- **exempt regex 추가 방향 철회** — 초기에 pre-check `REPEAT_EXEMPT_REGEX`
  에 테스트 경로 추가했으나 T13.2가 측정하는 `repeat_count: max=2`가
  exempt로 0이 되어 회귀 의미 붕괴. 운영에는 영향 없음

---

## v0.18.0 — pipeline-design 규칙 업스트림 이식

### 자동 적용 (스킬이 처리)

- `.claude/rules/pipeline-design.md` **신규** (~120줄, 범용 버전)
  - 7항목 체크리스트 (입력·중간계산·출력·폐기·보존 책임·전제·검증 케이스)
  - 4개 금지 패턴 (좋은 도구 버림·상류 출력 폐기·전제 미검증·단일 케이스 over-fit)
  - 파일 하단 "프로젝트 고유 사례 (로컬)" 섹션 — harness-upgrade 보존 영역
- `CLAUDE.md` — `<important if="다단 처리 파이프라인..."/>` 블록 추가
- `.claude/rules/self-verify.md` — "pipeline-design 체크리스트 연계" 섹션 추가
- `docs/decisions/hn_rules_metadata.md` — pipeline-design.md 섹션 추가
- `docs/incidents/hn_pipeline_design_rule_origin.md` **신규** — 업스트림 사료

### 왜

다운스트림 프로젝트에서 "상류 단계가 계산한 풍부한 중간 신호를 한 번의
결정에만 쓰고 **출력 구조에서 폐기** → 하류 단계들이 같은 축의 판단을
**열등한 정보로 재계산**"하는 구조가 **한 달간 draft1→2→3 재편에도
발견되지 않음**.

이 실수는 ML 파이프라인뿐 아니라 ETL·빌드·에이전트 체인 등 **다단 처리
전반에 적용**되므로 업스트림 범용 규칙으로 승격.

**review 자동 감지는 미도입** (의도 설계 문제 특성상 diff 키워드 매칭
어려움 + 오탐 다수). rule 체크리스트 강제 + self-verify 연계가 더 효과적.
v0.17.0·0.17.1의 review 축소 방향과 정합.

### 수동 액션 (다운스트림 필수·권장)

- [ ] **파이프라인 프로젝트는 로컬 사례 추가 (권장)**

  `docs/incidents/`에 `{abbr}_pipeline_origin*.md` 형식으로 자기 프로젝트
  고유 사례 기록. pipeline-design.md 하단 "프로젝트 고유 사례 (로컬)"
  섹션에 링크 추가 — harness-upgrade가 덮어쓰지 않음.

- [ ] **프로젝트별 단계 네이밍 추가 (선택)**

  자기 네이밍 체계(T0→T1, stage_1→stage_2 등)를 로컬 CLAUDE.md에 추가
  `<important if>` 조건으로 정의 가능. 업스트림 블록은 건드리지 말고
  로컬 블록으로 확장.

- [ ] **자기 파이프라인 코드/문서에 7항목 체크리스트 적용 (확인 권장)**

  기존 파이프라인 설계 문서를 열어 7항목 중 누락된 항목 확인. 특히:
  - 4번 "폐기" 근거가 명시되어 있는지
  - 5번 "보존 책임"이 인터페이스 문서에 있는지
  - 6번 "전제" 목록이 최근 재편에도 유효한지

### 검증

```bash
# rule 파일 생성 확인
ls -la .claude/rules/pipeline-design.md
# CLAUDE.md 트리거 확인
grep -c "pipeline-design" CLAUDE.md  # 1 이상
# self-verify 연계 확인
grep -c "pipeline-design 체크리스트" .claude/rules/self-verify.md  # 1 이상
```

### 회귀 위험

- **파이프라인 없는 프로젝트** — rule 파일이 로드되지만 `<important if>`
  조건 미발동으로 행동 영향 0. rules/ 용량 ~3KB 증가
- **다운스트림 커스터마이징 충돌** — 업스트림 덮어쓰기 영역 vs 로컬
  "프로젝트 고유 사례" 섹션을 명확히 분리 (naming.md의 로컬 확장 섹션
  패턴과 동일)
- **review 자동 감지 없음 → 실제 위반 놓침 가능성** — 사람이 눈치 못
  채면 rule이 있어도 위반 커밋됨. 완화: 원인 자체가 "한 달 재편해도 못
  봤다"라 review 자동화로도 해결 불확실. rule + self-verify가 "인지
  도구"로 사람 질문 품질을 높이는 게 더 효과적

---

## v0.17.1 — review tool call 예산 재설계 (2축 + 조기 중단)

### 자동 적용 (스킬이 처리)

- `.claude/agents/review.md` — "3관점(회귀·계약·스코프)" → **"계약·스코프
  2축 + 회귀 알파(S7·S8 hit 시만)"** 전면 재구성
- 신호 매핑 표에 **알파 발동 조건** 열 추가 (13개 신호, 각각 "이것이
  있을 때만" 실행 조건 정의)
- Stage 모드 표 재작성 — tool call 목표 **범위**로 정의 (0~2, 1~4, 3~5)
- **조기 중단 모든 stage 허용** — 필수 단계 완료 후 의심점 없으면 종료
- "한도" 섹션 보강 — 5회 이후 여유 1회 보존, verdict 출력 의무 재강조
- 출력 템플릿에 "조기 중단 응답" 형식 신설

### 왜

v0.17.0에서 Stage 결정을 5줄로 단순화했지만 review 에이전트 자체는
여전히 "Stage별 tool 고정 하한"으로 동작. 실측 warn 6건 축 분포:
- 계약 위반 50% (3건) · 스코프 이탈 33% (2건) · 회귀 0% (0건)
- 회귀 축은 S7·S8 hit 없으면 의미 없음 → 기본 검사에서 제외하고 **알파
  (조건부 추가 실행)**로 이동

딥 모드에서도 "추가 확인할 게 없는데 형식적으로 돌림" 문제. 조기 중단
허용으로 tool call 평균 ~5회 → ~3회 절감 기대. 단, "의심점 있는데 중단"
= 검증 회피로 명시 금지.

### 수동 액션 (다운스트림 필수·권장)

- [ ] **커스텀 review.md 오버라이드한 프로젝트**

  다운스트림이 review.md를 로컬 수정했으면, 업스트림 2축 구조와 병합
  필요. 주요 변경점:
  - L156~: "3관점" → "2축 + 회귀 알파"
  - L260~: 신호 매핑 표에 발동 조건 열 신설
  - L282~: Stage 모드 표에 필수 실행 단계 + 범위
  - L183~: 한도 섹션 verdict 의무 강화
  - L208~ (신설): 조기 중단 섹션
  - 출력 템플릿: "3관점 독립 검증" → "2축 검사 + 회귀 알파"

- [ ] **review 호출자(commit 스킬 등) 파싱 코드 확인**

  출력 템플릿이 `[조기 중단]` 섹션을 포함할 수 있음. 기존 파싱이
  `verdict:` 라인만 보면 무해. `### 3관점 독립 검증` 헤더를 하드코딩
  매칭하는 경우만 `### 2축 검사`로 변경 필요.

### 검증

```bash
# review.md 본문에 2축 구조 반영됐는지
grep -c "2축 검사\|회귀 알파\|조기 중단" .claude/agents/review.md
# 3 이상이어야 정상

# 실측 — 다음 /commit 호출 시 tool call 수 관찰
# 기대: 평균 3~4회 (이전 ~5회), maxTurns 소진 빈도 0
```

### 회귀 위험

- **조기 중단이 너무 공격적일 때**: 계약 pass 확인 후 스코프 안 보고
  종료. 완화책: 필수 실행 단계를 stage별로 고정 (micro=계약, standard=
  계약+스코프, deep=계약+스코프+알파) — 이 단계 건너뛰는 중단은 금지
- **알파 발동 조건 복잡성**: 에이전트가 조건을 잘못 해석할 위험. 조건은
  diff·pre-check 필드 기준으로만 정의 (주관 판단 배제)
- **회귀 놓침**: S7·S8 hit 없는 변경에서 내부 함수 동작 변경이 놓칠 수
  있음. 실측상 0건이지만 도메인별로 차이 가능 — 다운스트림에서 발견 시
  알파 발동 조건 재조정

---

## v0.17.0 — review staging 5줄 룰 (경로 기반 이진 판정)

### 자동 적용 (스킬이 처리)

- `.claude/rules/staging.md` — Stage 결정 1단계 전면 대체. 기존 16줄 룰
  → 경로 기반 **5줄 룰**. 2단계 격상 룰 중 다중 도메인 격상(A) 폐기
- `.claude/scripts/pre-commit-check.sh` — RECOMMENDED_STAGE 계산 블록
  (L462~545) 교체. 신호 계산(S1~S15)은 그대로 유지 — review prompt용
- `.claude/scripts/test-pre-commit.sh` — T21~T32 회귀 케이스 12개 추가
  + clone 시 워킹 트리 스크립트 cp 보정(로컬 변경 테스트 가능)

### 왜

업스트림 실측: staging 도입 후 52커밋 중 deep 22건(42%), standard 0건.
**4단계 중 1단계가 완전히 안 쓰임**. deep 22건 전수 분석 시 41%(9건)는
standard 이하로 내려가도 warn 놓침 없음 (실측 warn은 모두 grep/Read 1회
수준 → standard 커버). 16줄 룰이 복잡도·드리프트 유발, 사용자 "왜 deep
인지 설명 불가" 피드백.

5줄 룰 구조:
```
1. .claude/scripts|agents|hooks|settings.json  → deep
2. S1 line-confirmed OR S14 OR S8             → deep
3. docs/** rename ≥30% OR 파일 ≥20            → bulk
4. S5 OR S4 단독                              → skip
5. 나머지                                     → standard
```

### 수동 액션 (다운스트림 필수·권장)

- [ ] **다운스트림 영향 확인**

  4줄(룰 1·2·3·4)이 `.claude/*` 경로 기반이라 `src/*`·`tests/*` 주력
  다운스트림은 대부분 룰 5(standard)로 폴백. 기존 행동 크게 안 바뀜.
  다만 과거 `deep`으로 잡혔던 `.claude/rules/` 단독 변경은 이제 `standard`.

- [ ] **`--deep` 수동 오버라이드 여전히 유효**

  애매한 케이스(예: rules 본문 대폭 재작성)는 명시적 `--deep`으로 격상
  가능. 5줄 룰은 기본값일 뿐.

- [ ] **다중 도메인 격상 폐기 재검토**

  기존 "다중 도메인 + critical → deep 격상" 룰 폐기. 다운스트림이
  `src/payment/` + `src/auth/` 같은 혼합 변경을 deep로 유지하고 싶으면
  CLAUDE.md 또는 local staging 확장 섹션에 커스텀 룰 추가 필요.

### 검증

```bash
# 회귀 테스트 — T21~T32 12케이스 통과 확인
bash .claude/scripts/test-pre-commit.sh | grep -E "T(2[1-9]|3[0-2])"

# 실측 — 최근 커밋을 대상으로 stage 분포 확인
git log -20 --format='%h %s' | grep -oE "review: [a-z]+" | sort | uniq -c
```

### 회귀 위험

- **룰 1 오탐 가능성** — `.claude/rules/` 아래 하위 경로(예: `.claude/rules/
  subdir/*`)는 룰 1에 안 들어감(정확한 경로만 매칭). 룰 5 standard로 폴백
- **다중 도메인 커버리지 약화** — 다중 도메인 격상 폐기로 혼합 변경이
  standard가 될 수 있음. review.md가 signal 기반 카테고리 추가로 커버
- **docs rename bulk 임계 (20 파일 / 30%)** — 임계 미달 대량 변경은 여전히
  standard. 사용자가 `--bulk` 수동 지정

---

## v0.16.1 — `/commit --bulk` 플래그 (거대 변경 review 대체)

### 자동 적용 (스킬이 처리)

- `.claude/scripts/bulk-commit-guards.sh` 신설 — 정량 가드 4종 통합 실행
  (test-pre-commit·test-bash-guard·downstream-readiness·파일명/참조 정합성)
- `.claude/rules/staging.md` — Stage 5단계 확장 (bulk 추가), 결정 우선순위 F(bulk)
- `.claude/skills/commit/SKILL.md` — Step 7 Stage 분기에 `--bulk` 추가,
  가드 실행 로직 + `[bulk]` 태그·`🔍 review: skip-bulk` 로그 강제
- `.claude/scripts/pre-commit-check.sh` — 대규모 변경 감지 시 stderr에
  `--bulk` 제안 경고 (강제 아님)

### 왜

v0.16.0 커밋(파일 61개, diff 2353줄)에서 review 에이전트가 maxTurns(6)
상한 소진 시 verdict 미출력으로 `SendMessage` 재호출이 필요했음
(incident `hn_review_maxturns_verdict_miss`).

거대 일괄 변경(rename·본문 치환 등)은 review가 설계상 커버하기 어렵고,
사람이 의도 설계로 진행 + 정량 검증(테스트·grep·dead link)이 더 확실.
`--bulk`는 이를 공식 경로로 만든다.

### 수동 액션 (다운스트림 필수·권장)

- [ ] **업그레이드 후 첫 거대 커밋 시 `--bulk` 인식**

  파일 30+ 또는 diff 1500줄+ 변경을 커밋하려 할 때 pre-check이 stderr에
  경고를 출력한다:
  ```
  ⚠ 대규모 변경 감지 (files=X, +Y, -Z).
    review maxTurns 한계로 verdict 신뢰도 저하 가능. `/commit --bulk` 고려.
  ```
  사용자가 판단해 `--bulk`로 재실행. 자동 전환은 안 함 (오탐 방지).

- [ ] **정량 가드 실패 시 원인 확인**

  `--bulk` 실행 후 가드 실패 시 stderr에 어느 가드가 왜 실패했는지
  출력됨. 예:
  ```
  [FAIL] dead link 존재
         대응: 위 링크들이 실제 파일을 가리키도록 수정
             (rename 후 참조 치환 누락일 가능성)
  ```
  **가드는 우회 불가**. review의 warn/block과 달리 block-only. 원인 해결
  후 재시도.

- [ ] **(선택) 프로젝트별 테스트 스크립트 확장**

  `bulk-commit-guards.sh`가 호출하는 테스트 3종(test-pre-commit·test-bash-guard
  ·downstream-readiness)은 하네스 기본. 다운스트림에 프로젝트 고유
  회귀 테스트가 있으면 `bulk-commit-guards.sh`의 가드 섹션에 추가 가능.
  수정 시 incident `hn_review_maxturns_verdict_miss` 근거 인용.

### 검증

```bash
# 가드 스크립트 단독 실행
bash .claude/scripts/bulk-commit-guards.sh
# exit 0: 4개 가드 모두 PASS
# exit 2: 어느 가드가 실패했는지 stderr에 상세 출력

# pre-check 대규모 감지 테스트 (staged 많을 때 경고 출력 확인)
git diff --cached --stat | tail -1  # files·라인 확인
bash .claude/scripts/pre-commit-check.sh 2>&1 | grep "대규모 변경"
```

### 회귀 위험

- **기존 `/commit` 사용자 영향 없음** — `--bulk`는 명시 플래그, 자동 분류
  안 됨. 기존 `--quick`·`--deep`·`--no-review`와 독립 동작
- **가드가 review의 "의도 일관성" 검증을 못 함** — 정책 모순·결정문과
  문서 불일치는 가드로 안 잡힘. 거대 변경 전 설계 단계에서 사용자가 확보
  해야 함 (v0.16.0에서 이 문제가 발생해 review가 L226 잔재 잡았지만,
  원래는 설계 시점에 막혔어야 함)
- **정량 가드 비용** — 4개 가드 실행에 5~15초 소요. review(60~180초)보다
  빠르지만 작은 커밋에는 불필요 → 명시 플래그로만 활성

---

## v0.16.0 — 문서 네이밍 전면 개편 (도메인 약어 + 통합 원칙)

### 자동 적용 (스킬이 처리)

**규칙 갱신**:
- `.claude/rules/naming.md` — "왜 — 파일명이 곧 인덱스다" 섹션 신설,
  "도메인 약어" 표 신설, "파일명 — 문서/WIP" 섹션 채움, "Cluster 자동
  매핑" 직교 파싱 규칙 추가. **날짜 suffix 전면 금지 (incidents 포함)**
- `.claude/rules/docs.md` — "핵심 원칙" 섹션 최상단 추가(탐색 체인),
  "문서 탐색" 섹션을 `ls`/`grep` 우선 경로로 재구성, 파일명 규칙 +
  주제 분할 기준, 금지 목록에 날짜 suffix·미등록 abbr 추가

**스킬 갱신**:
- `.claude/skills/write-doc/SKILL.md` — Step 1에 abbr 조회·검증 + 누락
  시 사용자 입력 요청, Step 3 파일명 생성이 신 형식, 날짜 suffix 요청
  거부 로직
- `.claude/skills/docs-manager/SKILL.md` — Step 3 cluster 매핑이 파일명
  abbr 직교 파싱(불투명 prefix·라우팅 태그·레거시 `_p2_` 통과), `--validate`
  에 약어 중복·도메인 1:1 대응·파일명 날짜 suffix 검사 추가

**업스트림 파일 rename (40개 + cluster + 결정문)**:
- `docs/decisions/*` 10개: 날짜 suffix 제거 + `hn_` abbr 부착
- `docs/guides/*` 6개: 동일 (전역 마스터 2개는 abbr 없음)
- `docs/harness/*` 19개: 동일 (`MIGRATIONS.md`는 전역 마스터)
- `docs/incidents/*` 6개: 날짜 suffix 제거 + `hn_` abbr 부착
- `docs/clusters/harness.md` 재생성 (신 파일명 기준 + 폴더별 분류)
- 본문 참조 173건 전수 치환 (마크다운 링크·relates-to·rules 본문)

### 왜

- 파일명이 곧 인덱스 → `ls docs/**/{abbr}_*`로 도메인 문서 즉시 목록화
- 같은 주제 = 같은 파일 → 날짜 suffix로 인한 SSOT 분열 차단
- docs-manager가 파일명만으로 cluster 자동 매핑 → 수동 인덱스 관리 제거
- 다운스트림이 앞에 `m3-`·`s12-` 같은 불투명 prefix를 붙여도 직교 파싱
  이 abbr만 추출해 cluster 매핑 유지
- tags 프론트매터로 세분화 (`skill`·`rule`·`agent` 등) → 도메인을 여러
  개로 쪼개지 않고도 축 분리 가능

자세한 결정 근거: `docs/decisions/hn_doc_naming.md`

### 수동 액션 (다운스트림 필수)

- [ ] **`.claude/rules/naming.md` "도메인 약어" 표 채우기**

  업그레이드 후 naming.md에 "도메인 약어" 섹션이 추가됐지만 표에는
  하네스 시드(`hn`·`mt`)만 있음. **"도메인 목록 > 확정"의 모든 도메인
  에 대해 abbr을 등록**해야 함.

  규칙:
  - 2~3자 소문자 영문
  - 도메인당 1개
  - 기존 약어와 충돌 금지
  - 원 이름의 첫 자·자음 조합 선호 (`payment → pm`, `migration → mg`)

  예:
  ```
  | 도메인 | abbr | cluster 파일 |
  |--------|------|--------------|
  | harness | hn | clusters/harness.md |
  | meta    | mt | clusters/meta.md    |
  | payment | pm | clusters/payment.md |
  | auth    | au | clusters/auth.md    |
  | api     | ap | clusters/api.md     |
  ```

  등록 안 하면 `docs-manager --validate`가 "도메인-약어 1:1 대응 누락"
  경고. 파일명 prefix 매칭도 실패해 cluster 자동 매핑 안 됨.

- [ ] **(선택) 기존 문서 이름 마이그레이션 정책 결정**

  현재 문서가 날짜 suffix(`hn_memory_260420.md` 같은)를 가지고 있을
  수 있음. 기존 파일 처리는 다운스트림 자율:

  **옵션 A — 점진 이동 (권장)**
  갱신 시점마다 같은 커밋에서 파일명도 신 규칙으로 변경 (`git mv`).
  본문 내 마크다운 링크·relates-to path 함께 갱신. 소규모·저위험.

  **옵션 B — 일괄 이동**
  자체 스크립트로 한 번에 이동. 업스트림이 v0.16.0에서 자기 40개 파일을
  이렇게 이동했음. 참조 대량 치환 필수. 프로젝트마다 참조 구조가 달라
  업스트림은 범용 스크립트 제공 안 함.

  업스트림 일괄 이동 절차 참고 (템플릿):
  ```bash
  # 1. rename 매핑 파일 작성 (src dst 쌍)
  # 2. 일괄 git mv
  # 3. 본문 참조 sed 치환 (옛 파일명 basename → 신 basename)
  # 4. dead link 검사
  # 5. clusters/* 재생성
  # 6. 회귀 테스트 (test-pre-commit.sh 등)
  ```

  **옵션 C — 현상 유지**
  옛 이름 그대로. 직교 파싱 규칙이 구 파일명도 abbr 추출 성공하므로
  cluster 매핑은 동작. 신규만 신 규칙 준수.

- [ ] **(선택) 마일스톤·Phase prefix 등 프로젝트 고유 확장 정의**

  Phase/Milestone/Sprint 기반 개발 구조를 가진 프로젝트는 `naming.md`
  하단에 `### 파일명 — 확장 (프로젝트 고유)` 섹션을 추가하고 자기
  문법 정의:
  ```
  ### 파일명 — 확장 (프로젝트 고유)

  m{N}-{abbr}_t{NN}_{slug}.md       마일스톤-task
  m{N}_{slug}.md                    마일스톤 횡단
  ```

  업스트림 직교 파싱은 앞쪽 `m{N}-`을 **불투명 prefix로 통과**시키고
  abbr만 추출하므로 cluster 매핑은 그대로 동작. `harness-upgrade`는
  업스트림 소유 섹션만 덮어쓰므로 이 확장 섹션은 보존됨.

### 검증

```bash
# 도메인-약어 1:1 대응 확인
grep -A20 "도메인 약어" .claude/rules/naming.md

# 파일명 규칙 위반 스캔
find docs -name "*.md" | grep -vE "(incidents/|^docs/WIP/)" \
  | grep -E "_[0-9]{6}\.md$"
# 출력 있으면: incidents 외 날짜 suffix 남은 파일

# docs-manager 정합성 검사
# (Claude에게 /docs-manager --validate 실행 요청)
```

### 회귀 위험

- **기존 파일 이름 혼재 기간** — 구 이름(`hn_memory_260420.md`)과 신
  이름(`hn_memory.md`) 공존. 직교 파싱으로 매핑은 둘 다 성공하나, 사용자
  ·LLM 모두 당분간 두 패턴 동시 노출
- **abbr 표 누락 시 조용한 실패** — 도메인 추가하고 약어 등록 안 하면
  그 도메인 문서는 cluster에 등록 안 됨. `--validate` 정기 실행 필요
- **마일스톤 확장 섹션 관리 책임** — 업스트림이 의미 해석 안 하므로
  다운스트림 자체 규율 필요. `m{N}-`이 무엇인지 그 프로젝트에서 정의

---

## v0.9.3 — stage 격상 면제 버그 수정

### 자동 적용 (스킬이 처리)

- `.claude/scripts/pre-commit-check.sh` — 2단계 격상(MULTI_DOMAIN + critical → deep)에
  IS_DOC_ONLY 면제 추가. S5/S6 단독(코드/핵심설정/마이그레이션/빌드 미동반)은
  multi-domain critical이어도 deep 격상 안 함.
- `.claude/rules/staging.md` — 룰 A에 면제 ※ 명시.

### 수동 액션

없음.

### 검증

다운스트림에서 doc-only commit이 multi-domain critical 환경에서도 적절히 분류되는지:

```bash
# 더미: docs/만 변경된 staged 상태에서
bash .claude/scripts/pre-commit-check.sh | grep recommended_stage
# 기대: skip 또는 micro (이전엔 deep으로 격상되곤 함)
```

### 회귀 위험

- 정상 deep 격상(S7+S9 critical, S6+S7+S9 critical 혼합 등)은 그대로 작동.
  코드/핵심설정 동반 시 IS_DOC_ONLY="" 이라 면제 미발동.
- 시뮬레이션 검증: starter 측에서 두 케이스 통과 확인.

---

## v0.9.1 — rules 다이어트 + harness-upgrade 화이트리스트

### 자동 적용 (스킬이 처리)

- `.claude/rules/*.md` 7개 파일 재구조화 (본문 압축, 포인터 추가). 매 세션
  시스템 프롬프트 용량 약 15KB 절감.
- `.claude/skills/harness-upgrade/SKILL.md` — "하네스 파일 범위"에
  rules가 참조하는 docs/ 화이트리스트 추가. 이후 업그레이드는 이 목록을
  자동 이식.

### 수동 액션 (다운스트림 필수)

v0.9.1로 처음 업그레이드하는 다운스트림은 **rules가 docs/를 참조하는데 그
docs/가 존재하지 않는 dead link**가 발생한다. 이전 버전의 harness-upgrade
가 `docs/guides/*`·`docs/decisions/*`를 "사용자 전용"으로 분류해 전혀
이식하지 않았기 때문이다.

- [ ] **rules 참조 문서 4개를 다운스트림에 수동 복사**

  ```bash
  cd <다운스트림 프로젝트>

  # starter 리포에서 직접 복사 (harness-upstream remote 활용)
  for f in \
    docs/guides/hn_doc_search_protocol.md \
    docs/guides/hn_external_research_patterns.md \
    docs/decisions/hn_staging_governance.md \
    docs/decisions/hn_rules_metadata.md; do
    mkdir -p "$(dirname "$f")"
    MSYS_NO_PATHCONV=1 git show harness-upstream/main:"$f" > "$f"
  done

  # INDEX.md·clusters/harness.md 수동 갱신 (docs-manager 위임 권장)
  ```

  복사 후 해당 도메인이 `harness`인지 확인. 다운스트림이 starter 관리
  문서로 인식하면 업그레이드 때 건드리지 않도록 화이트리스트 자동 보호.

### 검증

```bash
# rules의 dead link 재확인
grep -nE "docs/(guides|decisions)/[a-z_-]+_260420\.md" .claude/rules/*.md

# 위 출력의 각 경로가 실제 존재하는지
ls docs/guides/hn_doc_search_protocol.md \
   docs/guides/hn_external_research_patterns.md \
   docs/decisions/hn_staging_governance.md \
   docs/decisions/hn_rules_metadata.md
```

### 회귀 위험

- 없음. 본문 축약·포인터 추가만. 행동 로직 변경 없음.
- 단, 후속 업그레이드에서 rules가 새 docs/ 파일을 참조하면 SKILL.md 화이트
  리스트에도 등록해야 dead link 재발 안 함. (review 자동 감지는 후속 과제)

---

## v0.8.0 — review 패턴 매핑 + CPS 복원

### 자동 적용 (스킬이 처리)

- `.claude/agents/review.md` 전면 재작성 — "카테고리 설명" → "diff 패턴 →
  검증 행동" 9개 매핑. 각 패턴별 tool 선택·호출 횟수 명시.
  frontmatter `maxTurns: 6` 추가 (agentic turn hard 상한).
- `.claude/agents/review.md`에 CPS 감지 패턴 9번 추가 — 새 도메인·규칙·
  스킬·에이전트 신설 시 CPS 문서 갱신 누락 감지.

### 수동 액션 (권장)

- [ ] **프로젝트 CPS 문서 확인·작성**

  `harness-init` 실행한 프로젝트면 `docs/guides/project_kickoff_*.md`가
  이미 있음. **없으면** (또는 `status: sample`만 있으면) CPS 무너진 상태 —
  review의 9번 패턴·implementation Step 0 모두 제대로 작동 안 함.

  조치:
  ```bash
  # CPS 확인
  ls docs/guides/project_kickoff_*.md
  # 없거나 sample만 있으면 /harness-init 다시 실행
  ```

  CPS는 Context(배경·제약)·Problems(해결할 핵심 문제)·Solutions(접근법)
  3섹션. 한 번 만들면 새 Problem 발견 시마다 갱신 (review 9번이 검증).

### 회귀 위험

- review가 이전엔 카테고리 전체 돌았는데 이제 패턴 hit한 것만 돔 → 특정
  회귀 누락 가능성. 발견 시 review.md에 패턴 추가.

---

## v0.7.2 — settings.json schema 검증 자동화

### 자동 적용 (스킬이 처리)

- `.claude/scripts/validate-settings.sh` 신설 — Claude Code 재로드 전
  schema 사전 검증. 실패 시 구체 에러 stderr.
- `.claude/scripts/auto-format.sh`에 settings.json 변경 시 자동 호출 추가.
- `.claude/scripts/downstream-readiness.sh`에 검증 항목 추가.

### 배경

사용자 실측: 한 세션에 settings.json validation 에러 2회 발생 → 40k 토큰
허비 (에러 응답에 전체 schema 덤프). 다음 실수 방지 위해 **Claude Code
재로드 전** 사전 검증.

### 수동 액션

없음. 자동 패치만.

### 회귀 위험

- validate-settings.sh가 모르는 새 공식 필드는 "알 수 없는 이벤트" 경고
  낼 수 있음 (에러 아닌 경고). 공식 스키마 변경 시 스크립트 갱신.

---

## v0.7.1 — review 토큰 과소비 수정 + MCP 다운스트림 최소화 권장

### 자동 적용 (스킬이 처리)

- `.claude/rules/staging.md` 룰 1번 정밀화 — S9(critical) + 메타·문서
  단독(S5/S6만)일 때 deep 강제 안 함
- `.claude/scripts/pre-commit-check.sh` 동일 수정 (HAS_CODE_OR_CORE 가드)
- `.claude/agents/review.md` Stage 2/3 Read 상한 축소 — "10+" 폐기,
  Stage 3 최대 5회. 과도한 Read 경계 규정 추가

### 수동 액션 (사용자 필수·권장)

- [ ] **MCP 서버 설정 점검** (spawn 시 토큰 과소비 방지)

  `~/.claude/settings.json`에 MCP 서버가 전역 등록돼 있으면 **모든 프로젝트**
  에 상속. 프로젝트별로 필요한 것만 `.mcp.json`(프로젝트 루트)에 정의 권장.

  현재 상태 확인:
  ```bash
  # 전역 (영향 큼)
  grep -A10 mcpServers ~/.claude/settings.json 2>/dev/null

  # 프로젝트별 (권장)
  cat .mcp.json 2>/dev/null
  ```

  조치:
  - **전역에 있는 MCP 중 프로젝트 무관한 것은 제거** (예: 일부 프로젝트만
    Supabase 사용하면 전역에서 빼고 해당 프로젝트 `.mcp.json`에만)
  - 서브에이전트는 `tools` allowlist로 이미 MCP 차단하지만, 메인 세션에는
    MCP 스키마가 계속 로드됨 → review 호출 시 상속되는지는 claude-code
    내부 구현 따라 다름. 실측으로 확인 필요.

  **주의:** `.mcp.json`은 프로젝트별 MCP 정의. 팀 공유 대상이라 민감한
  서버(개인 Gmail·Slack 등)는 팀 리포에 체크인 금지. 팀용은 `.mcp.json`,
  개인용은 `~/.claude/settings.json`.

### 회귀 위험

- **review 품질 저하 가능성** — Read 횟수 줄였으므로 복잡한 케이스에서
  검증 놓칠 수 있음. incident 발생 시 Stage 3 Read 상한 재검토.

---

## v0.7.0 — Bash matcher 광역 패턴 폐기 + 단일 hook 통합

### 자동 적용 (스킬이 처리)

- `.claude/rules/hooks.md` 신설 — argument-constraint 매처 금지 규칙.
- `.claude/settings.json` 단순화 — 모든 `Bash(... -X ...)` 광역 매처 제거.
  Bash matcher 1개 (단일 `bash-guard.sh` 호출).
- `harness-upgrade` Step 8.2 신규 — 구버전 starter 소유 hook(광역 매처)을
  다운스트림에서 감지·제거 제안. 사용자 커스텀 hook은 보존.
- `downstream-readiness.sh` argument-constraint 매처 전수 감지 추가.
- `.claude/scripts/bash-guard.sh` 신규 — jq로 명령 파싱 후 토큰 단위 검증.
  공식 권장 패턴 (https://code.claude.com/docs/en/permissions 인용).
- `.claude/scripts/test-bash-guard.sh` 신규 — 13건 회귀 테스트.
- `.claude/scripts/test-hooks.sh` **삭제** — bash glob로 매처 모사가 공식
  matcher와 달라 거짓 안전감 제공. test-bash-guard.sh가 실제 hook
  입력 형식(JSON via stdin)으로 검증.
- `.claude/scripts/pre-commit-check.sh` 핵심 설정 연속 수정 차단 복원 —
  `settings.json`·`rules/*`·`scripts/*`·`CLAUDE.md`가 5커밋 중 3회 이상
  변경되면 차단. `[expand]` 태그로 우회. 일반 코드는 차단 없이 카운트만.
- `.claude/scripts/downstream-readiness.sh` v1.9.0 신호 갱신.

### 수동 액션 (사용자 필수)

없음. 자동 패치만.

### 검증

```bash
bash .claude/scripts/test-pre-commit.sh   # 21/21
bash .claude/scripts/test-bash-guard.sh   # 13/13
bash .claude/scripts/downstream-readiness.sh  # 0/0
```

이전(v1.7~v1.8) 광역 매처가 잘못 차단했던 정당 명령 7가지(`bash -n`,
`head -n`, `git push origin main` 등) 모두 통과 검증됨.

### 회귀 위험

- **차단 메시지 변경** — 이전 "❌ git commit -n 금지" → "❌ git commit -n
  금지 (verify 우회). bash -n 같은 다른 -n은 영향 없음." (대안 명시 추가)
- **메시지 안 -n 통과** — `git commit -m "fix -n bug"` 같이 quote 안의
  -n은 토큰 분리 후 인자가 아니라고 판단해 통과. 이전엔 잘못 차단.
- **핵심 설정 3회 차단 복원** — settings.json·rules/·scripts/를 같은 영역
  3회 연속 수정하면 차단. 정당한 점진 확장이면 커밋 메시지에 `[expand]`
  태그 포함.

### 배경

이번 세션 중 사용자 지적: "이전에 수정한 내역이 있는데 어느 것도 참조
하지 않고 또 추측해서 수정". 1·2차 수정(1a50efd, 88f1ff2, 3468fb5)이
모두 공식 문서 미확인 + 추측 기반. 공식 문서 확인 결과 매처 `*`가
공백 포함 모든 문자에 매칭되며 "argument constraint는 fragile" 명시
경고 + jq 기반 hook 권장 발견. 이에 따라 매처 자체를 폐기.

incident: `docs/incidents/hn_bash_n_flag_overblock.md` 3차 섹션.

---

## v0.6.2 — pre-check lint stdout 오염 수정 + commit push 보강

### 자동 적용 (스킬이 처리)

- `.claude/scripts/pre-commit-check.sh` 패치 — lint 명령의 stdout/stderr
  모두 캡처 후 종료 코드만 평가. 이전엔 stdout만 흘려 신호 줄과 섞임.
- `.claude/skills/commit/SKILL.md` 푸시 섹션 강화 — `is_starter: true`
  분기 + `HARNESS_DEV=1 git push` 명시.
- `.claude/scripts/test-hooks.sh` push 회귀 케이스 추가 (S1).
  **※ v0.7.0에서 test-hooks.sh 자체 폐기. 본 케이스는 test-bash-guard.sh로 이전됨.**

### 수동 액션 (사용자 필수)

없음. 자동 패치만으로 완료.

### 검증

```bash
# 다운스트림(lint 있는 프로젝트)에서 21/21 통과 확인
bash .claude/scripts/test-pre-commit.sh
```

이전(v1.7.0~v1.8.0)에서 다운스트림이 12/21 같은 부분 통과로 떨어졌다면
본 패치 후 21/21로 복원됨.

### 회귀 위험

- lint 실패 시 출력 형식 변경 — 이전엔 명령만 stderr, 이제는 명령 + 마지막
  20줄 stderr. 더 자세해짐 (개선).

---

## v0.6.1 — 다운스트림 마이그레이션 인프라 (본 문서 도입)

MIGRATIONS.md 자체 도입 + `harness-upgrade` Step 9.5(사용자 액션 표시)
+ `downstream-readiness.sh`(자가 진단). 수동 액션 없음 (자동 패치만).

---

## v0.6.0 — 하네스 단순화 (마찰 회수)

### 자동 적용 (스킬이 처리)

- `.claude/scripts/pre-commit-check.sh` 교체 — 연속수정 차단·contamination
  검출 블록 제거, S1 file-only/line-confirmed 분리, S8 언어별 시그니처,
  needs_test_strategist 신호, S6 ≤5줄 → skip
- `.claude/agents/review.md` 교체 — "전제 컨텍스트" 신뢰 규칙, "오염 검토",
  "허위 후속 감지" 카테고리
- `.claude/skills/commit/SKILL.md` 교체 — Step 2 자동 본문 갱신 보수화,
  review prompt 전제 컨텍스트 주입, test-strategist 병렬 호출 절차
- `.claude/skills/write-doc/SKILL.md` 교체 — incidents/ symptom-keywords
  필수 재질의
- `.claude/skills/docs-manager/SKILL.md` 교체 — Step 2 차단 검사 실행
  절차 (awk + grep)
- `.claude/rules/staging.md` 교체 — S1 강도 분리, stdout 13 keys, Stage
  결정 우선순위 정렬
- `.claude/rules/contamination.md` **삭제** — review.md "오염 검토"
  카테고리로 이전
- `.claude/settings.json` Bash 매처 갱신 — `Bash(* -n *)` 광역 제거,
  `Bash(git commit -n*)` + `Bash(git commit* -n*)`로 한정
- `.claude/scripts/test-pre-commit.sh` 신규 — 21건 회귀 테스트
- `.claude/scripts/test-hooks.sh` 신규 — 11건 매처 회귀 테스트
  **※ v0.7.0에서 폐기(bash glob 모사가 공식 matcher와 달라 거짓 안전감).
     test-bash-guard.sh가 실제 hook JSON 입력으로 검증.**

### 수동 액션 (사용자 필수)

- [ ] **`.claude/rules/naming.md` "도메인 등급" 채우기**
  - 현재 다운스트림 도메인이 critical/normal/meta 어디에도 분류 안 됐으면
    staging 시스템이 무력화됨 (S9 신호 무시 → 전부 normal로 폴백).
  - 위치: `## 도메인 등급 (review staging)` 섹션
  - 분류 기준:
    - **critical**: 사고 시 데이터·돈·접근 제어 영향 (예: payment, auth,
      database, infra, admin, ticketing)
    - **normal**: 기능 영역, 격리됨 (예: api, ui, crawler, blog)
    - **meta**: docs·changelog 같은 회고용
  - 검증: `grep -A2 "도메인 등급" .claude/rules/naming.md`로 확정 도메인
    전체가 셋 중 하나에 들어갔는지 확인

- [ ] **`.claude/rules/naming.md` "경로 → 도메인 매핑" 채우기**
  - 코드 파일(`src/`·`apps/` 등) 변경 시 도메인 추출 위해 필요.
  - 비어 있으면 staging이 코드 변경에 도메인 등급 적용 안 함.
  - 예시:
    ```
    src/payment/**     → payment
    src/auth/**        → auth
    apps/admin/**      → admin
    migrations/**      → migration
    ```

- [ ] **`.claude/HARNESS.json` `is_starter` 확인**
  - 다운스트림이면 `false`여야 함. `true`면 review "오염 검토" 카테고리가
    잘못 활성화됨.
  - `grep is_starter .claude/HARNESS.json`

- [ ] **이전 contamination 면제 설정 정리** (해당 시)
  - 이전 버전에서 `.claude/rules/contamination.md` 면제 리스트를 커스터마이징
    했으면, 그 내용을 review.md "오염 검토" 카테고리 본문(다운스트림은
    `is_starter: false`라 비활성)에 옮길 필요 없음. 그냥 삭제로 충분.

### 검증

```bash
# 회귀 테스트 (다운스트림에서도 실행 가능)
bash .claude/scripts/test-pre-commit.sh    # 21/21 통과 기대
# v0.7.0+ 에서는 test-hooks.sh 대신 test-bash-guard.sh 사용:
bash .claude/scripts/test-bash-guard.sh    # 13/13 통과 기대

# 도메인 등급 확정 도메인 전체 분류 검증
DOMAINS=$(grep -E '^확정:' .claude/rules/naming.md | sed 's/확정://' | tr ',' '\n' | sed 's/^ *//;s/ *$//')
for d in $DOMAINS; do
  if ! grep -qE "(critical|normal|meta).*\*?\*?:?.*$d" .claude/rules/naming.md; then
    echo "[누락] $d 등급 미분류"
  fi
done
```

### 회귀 위험

- **연속 수정 차단 사라짐** — 같은 파일 3회 수정해도 차단 안 됨. 의도적
  완화. 정보는 `repeat_count` stdout으로만 흐름.
- **contamination 셸 검출 사라짐** — `is_starter: true` 리포에서만 review가
  대신 검토. 다운스트림은 영향 없음.
- **commit Step 2 4지선다 사라짐** — 자동 본문 갱신만. status 변경·이동은
  사용자 명시 요청 필요.
- **`bash -n script.sh` 등 `-n` 옵션 정당 사용 통과** — 이전엔 차단됐음
  (incident bash_n_flag_overblock).

---

## v0.6.0 이전

기록 없음. v0.6.0이 본 마이그레이션 가이드 도입 시점. 이전 버전은
`git log --oneline --grep "(v0\."` 또는 `git log --all --oneline` 참조.
