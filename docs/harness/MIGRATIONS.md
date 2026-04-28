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

업그레이드 과정에서 발생한 충돌·이상 소견·수동 결정은 `migration-log.md`에
별도 기록한다 (다운스트림 소유, upstream은 읽기만).

## 포맷

```markdown
## vX.Y — 한 줄 요약

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

## v0.26 — 버그 묶음: MIGRATIONS 시스템 재설계 + starter_skills 경계 정비

### 변경 내용

- MIGRATIONS.md 재설계 — 기록물 → 지시 문서. migration-log.md 신설 (다운스트림 기록용)
- `starter_skills` 경계 정비: harness-dev 제거, harness-sync skills 등록
- `permissions.allow` 동기화 — harness-upgrade Step 8 확장
- h-setup.sh 신규 설치 경로 starter_skills 필터 추가
- `h-setup.sh` UPSTREAM_PAT 등록 → 변경 시 deep review 판정

### 적용 방법

**자동 적용**:
- MIGRATIONS.md 새 포맷으로 교체 (이 파일)
- `HARNESS.json` `starter_skills` 필드에서 `harness-dev` 제거, `skills`에 `harness-sync` 추가
- harness-upgrade Step 8 `permissions.allow` 동기화 로직 추가
- h-setup.sh 신규 설치 경로 starter_skills 필터 추가
- pre_commit_check.py `UPSTREAM_PAT`에 `h-setup.sh` 추가

**수동 적용**:
- [ ] **permissions.allow 동기화** — harness-upgrade Step 8이 upstream 항목을 제안한다. 
  승인하면 누락된 starter 필수 항목이 추가됨:
  ```bash
  # 확인: upgrade 실행 후 Step 8에서 추가 제안 항목 승인
  ```
- [ ] **harness-init/adopt 스킬 폴더 선택적 삭제** — 이미 복사된 경우 불필요:
  ```bash
  rm -rf .claude/skills/harness-init .claude/skills/harness-adopt .claude/skills/harness-dev
  ```
  삭제 안 해도 기능에 영향 없음 (스킬이 있어도 실행하지 않으면 무해).

### 검증
```bash
# starter_skills 확인
python3 -c "import json; d=json.load(open('.claude/HARNESS.json')); print(d['starter_skills'])"
# 기대: harness-init,harness-adopt (harness-dev 없음)

# skills에 harness-sync 확인
python3 -c "import json; d=json.load(open('.claude/HARNESS.json')); print('harness-sync' in d['skills'])"
# 기대: True
```

---

## v0.25 — harness-dev 스킬 신설 + starter_skills 필드

### 변경 내용

starter 개발 전용 스킬 `harness-dev` 신설. `HARNESS.json`에 `starter_skills`
필드 추가 — 다운스트림에 전달하지 않을 스킬 목록.

### 적용 방법

**자동 적용**:
- `HARNESS.json`에 `starter_skills` 필드 추가
- harness-upgrade가 `starter_skills` 목록의 스킬을 복사 제외
- `harness-dev/SKILL.md` 복사 제외 (starter 전용)

**수동 적용**:
- 없음 (단, v0.26 업그레이드 시 harness-init/adopt 폴더 선택적 삭제 권장)

### 검증
```bash
python3 -c "import json; d=json.load(open('.claude/HARNESS.json')); print(d.get('starter_skills'))"
# 기대: harness-init,harness-adopt
```

---

## v0.24 — install-starter-hooks.sh 신설 + hooks.md 적용 범위 명확화

### 변경 내용

pre-commit 버전 범프 hook을 설치하는 `install-starter-hooks.sh` 신설.
`hooks.md` "적용 범위" 섹션 추가 — `permissions.allow`의 `Bash(...)` 패턴은
허용 목록이라 hooks.md 금지 규칙 적용 대상이 아님을 명확히.

### 적용 방법

**자동 적용**:
- `.claude/scripts/install-starter-hooks.sh` 추가
- `.claude/rules/hooks.md` 적용 범위 섹션 갱신

**수동 적용**:
- 없음 (`install-starter-hooks.sh`는 `is_starter` 체크로 다운스트림 자동 스킵)

### 검증
```bash
grep -c "적용 범위" .claude/rules/hooks.md  # 1 이상
```

---

## v0.23 — debug-specialist 강화 + split 자동 stage + 버전 체크 이동

### 변경 내용

- debug-specialist 에이전트: 연속 fix 자동 감지 추가
- split 커밋: split-plan.txt 기반 자동 stage (그룹 2·3 수동 stage 버그 수정)
- 버전 체크: 스테이징 이후로 이동 (`--no-review` 시 누락 수정 포함)
- task_groups.py: abbr→char 성격 분류 + pre-check split 조건 교체

### 적용 방법

**자동 적용**:
- `.claude/agents/debug-specialist.md` 갱신
- `.claude/scripts/task_groups.py` 갱신
- `.claude/scripts/pre_commit_check.py` split 조건 갱신
- `.claude/skills/commit/SKILL.md` 버전 체크 순서 갱신

**수동 적용**:
- 없음

### 검증
```bash
python3 -m pytest .claude/scripts/test_pre_commit.py -q 2>&1 | tail -3
```

---

## v0.22 — bash 스크립트 전면 Python 전환 + 래퍼 완전 제거

### 변경 내용

핵심 스크립트 5개 bash → Python 전환. `.sh` 래퍼 삭제. 모든 호출자는
`python3 *.py` 직접 실행.

| 삭제 | 대체 |
|------|------|
| `pre-commit-check.sh` | `pre_commit_check.py` |
| `docs-ops.sh` | `docs_ops.py` |
| `task-groups.sh` | `task_groups.py` |
| `harness-version-bump.sh` | `harness_version_bump.py` |
| `test-pre-commit.sh` | `test_pre_commit.py` (pytest) |

성능: pre-check 84% 단축(1,953ms→310ms), 테스트 스위트 90% 단축.

### 적용 방법

**자동 적용**:
- 구 `.sh` 파일 삭제, 신 `.py` 파일 추가
- `split-commit.sh`, `downstream-readiness.sh`, `commit/SKILL.md` 호출자 갱신

**수동 적용**:
- [ ] **Python 3.8 이상 PATH 확인**:
  ```bash
  python3 --version
  ```
  없으면: https://python.org/downloads  
  Windows Git Bash: `~/.bashrc`에 `alias python3=python` 추가
- [ ] **구 `.sh`를 직접 호출하던 커스텀 스크립트·hook 갱신**:
  ```bash
  # 예: bash .claude/scripts/pre-commit-check.sh
  # →   python3 .claude/scripts/pre_commit_check.py
  ```

### 검증
```bash
python3 --version  # 3.8+
python3 -m pytest .claude/scripts/test_pre_commit.py -q 2>&1 | tail -3
```

---

## v0.20.11 — 세션 파일명 날짜 suffix 제거

### 변경 내용

harness-init/adopt/upgrade 생성 세션 파일의 날짜 suffix 제거. 같은 주제는
같은 파일에 `## 변경 이력`으로 누적.

### 적용 방법

**자동 적용**:
- 스킬 SKILL.md 파일명 생성 로직 갱신

**수동 적용**:
- [ ] **기존 날짜 suffix 파일 rename** (있는 경우):
  ```bash
  git mv docs/guides/project_kickoff_260401.md docs/guides/project_kickoff.md
  git mv docs/harness/adopt-session_260401.md docs/harness/hn_adopt_session.md
  # harness--migration_v*_*.md → harness--migration_followup.md
  ```

### 검증
```bash
ls docs/guides/project_kickoff*.md  # project_kickoff.md + _sample.md 2개만
```

---

## v0.20.7 — promotion-log.md 폐기

### 변경 내용

`docs/harness/promotion-log.md` 폐기. 버전 이력은 `git log --oneline --grep "(v0\."` 사용.

### 적용 방법

**자동 적용**:
- upstream에서 파일 삭제. three-way 모드에서 "삭제 제안"으로 표시.

**수동 적용**:
- [ ] **파일 직접 삭제** (two-way 모드 또는 자동 제안 미수락 시):
  ```bash
  git rm docs/harness/promotion-log.md
  git rm docs/archived/promotion-log-*.md  # 있는 경우
  ```
- [ ] **자동화 스크립트에 promotion-log 참조 있으면 git log 기반으로 전환**:
  ```bash
  grep -rn "promotion-log" . --include='*.sh' --include='*.md'
  ```

### 검증
```bash
ls docs/harness/promotion-log.md 2>/dev/null && echo "❌ 잔재" || echo "✅ 삭제됨"
```

---

## v0.20.5 — 커밋 이스케이프 단일화 (HARNESS_COMMIT_SKILL 폐기)

### 변경 내용

`git commit` 이스케이프가 `HARNESS_COMMIT_SKILL=1`·`HARNESS_DEV=1` 2개에서
`HARNESS_DEV=1` 단일로 축소. `HARNESS_COMMIT_SKILL=1`은 bash-guard exit 2.

### 적용 방법

**자동 적용**:
- `bash-guard.sh` 검증 4 — `HARNESS_COMMIT_SKILL` 제거
- `commit/SKILL.md` 커밋 실행 구문 갱신

**수동 적용**:
- [ ] **`HARNESS_COMMIT_SKILL=1` 사용 중인 커스텀 스크립트·CI를 `HARNESS_DEV=1`로 교체**:
  ```bash
  grep -r "HARNESS_COMMIT_SKILL" .
  ```

### 검증
```bash
grep -r "HARNESS_COMMIT_SKILL" .claude/  # 0 hit (폐기 주석 외)
```

---

## v0.20.0 — 커밋 프로세스 감사 반영 (audit #4·#8·#10·#17)

### 변경 내용

- `harness_version_bump.py` 신설 (audit #4)
- `git commit` 직접 호출 차단 — `HARNESS_DEV=1` prefix 필수 (audit #8)
- `docs-manager` 스킬 폐기 → `docs_ops.py` 5개 서브커맨드로 대체 (audit #10)
- S6 단독 ≤5줄 → skip 자동화 (audit #17)

### 적용 방법

**자동 적용**:
- `harness_version_bump.py` 신설
- `bash-guard.sh` 검증 4 — `git commit` 직접 호출 차단
- `docs-manager/SKILL.md` 삭제, `docs_ops.py` 추가
- `commit/SKILL.md` 전면 갱신

**수동 적용**:
- [ ] **`git commit` 직접 호출 → `HARNESS_DEV=1 git commit`으로 교체** (CI·스크립트 포함)
- [ ] **docs-manager 직접 호출 → docs_ops.py 서브커맨드로 교체**:
  ```bash
  # docs-manager --validate     → python3 .claude/scripts/docs_ops.py validate
  # docs-manager --move <file>  → python3 .claude/scripts/docs_ops.py move <file>
  # docs-manager cluster-update → python3 .claude/scripts/docs_ops.py cluster-update
  ```
- [ ] **`docs/clusters/*.md`에 frontmatter 없으면 재생성**:
  ```bash
  python3 .claude/scripts/docs_ops.py cluster-update
  ```

### 검증
```bash
python3 -m pytest .claude/scripts/test_pre_commit.py -q 2>&1 | tail -3
grep -r "docs-manager" .claude/ | grep -v "폐기\|#"  # 0 hit
```

---

## v0.19.0 — 커밋 프로세스 감사 반영 (audit #1·#3·#5·#6·#7·#12·#14·#15)

### 변경 내용

- `--lint-only` 모드 제거 (audit #1)
- `relates-to.path` dead link 검사 신설 (audit #12)
- test-strategist 폐기 (audit #7·#15)
- `HARNESS_LEVEL` 파싱 제거 (audit #2·9)
- `--light`·`--strict` 플래그 제거 → `--quick`/`--deep`/`--no-review`

### 적용 방법

**자동 적용**:
- `pre_commit_check.py` 다수 갱신
- `commit/SKILL.md` 전면 갱신
- `test-strategist.md` 삭제

**수동 적용**:
- [ ] **CLAUDE.md `## 환경`에서 `하네스 강도: light|strict` 줄 제거**
- [ ] **`/commit --light`·`/commit --strict` → `/commit`·`/commit --quick`·`/commit --deep`으로 교체**
- [ ] **세션 파일 잔재 삭제**:
  ```bash
  rm -f .claude/memory/session-staged-diff.txt .claude/memory/session-tree-hash.txt
  ```

### 검증
```bash
grep -r "하네스 강도\|--light\|--strict" CLAUDE.md .claude/  # 0 hit (주석 외)
```

---

## v0.18.6 — dead link 검사 pre-check 이식

### 변경 내용

`docs/clusters/*.md` dead link 검사를 review → pre-check으로 이식.
증분 검사 (O(변경 규모)). T35 회귀 3케이스 추가.

### 적용 방법

**자동 적용**:
- `pre_commit_check.py` Step 3.5 신설

**수동 적용**:
- [ ] **기존 dead link 점검 (권장)**:
  ```bash
  python3 .claude/scripts/docs_ops.py verify-relates
  ```
  기존 dead link는 다음 관련 커밋에서 차단될 수 있음.

### 검증
```bash
python3 -m pytest .claude/scripts/test_pre_commit.py -q -k "T35" 2>&1
```

---

## v0.18.4 — 린터 ENOENT 패턴 정교화

### 변경 내용

린터 실종(ENOENT)과 rule 위반 구분 정교화. Alpine·Dash·pnpm 형식 추가.
`no-speculation.md` "MIGRATIONS.md 회귀 위험 단정 금지" 원칙 추가.

### 적용 방법

**자동 적용**:
- `pre_commit_check.py` ENOENT 패턴 갱신
- `no-speculation.md` 섹션 추가

**수동 적용**:
- 없음 (v0.18.3 이하면 즉시 upgrade 권장 — Alpine CI에서 매 커밋 차단 가능)

### 검증
```bash
python3 -m pytest .claude/scripts/test_pre_commit.py -q -k "T33 or T34" 2>&1
```

---

## v0.18.3 — 린터 도구 실종 구분

### 변경 내용

도구 실종(ENOENT) → warn+skip. rule 위반 → 기존대로 차단. 환경 마찰 완화.

### 적용 방법

**자동 적용**:
- `pre_commit_check.py` ENOENT 구분 추가

**수동 적용**:
- [ ] **node_modules 복구 (근본 해결)**:
  ```bash
  npm install  # 또는 pnpm/yarn/bun install
  ```

### 검증
```bash
python3 -m pytest .claude/scripts/test_pre_commit.py -q 2>&1 | tail -3
```

---

## v0.18.0 — pipeline-design 규칙 업스트림 이식

### 변경 내용

다단 처리 파이프라인 설계 규칙(`pipeline-design.md`) 신설. 7항목 체크리스트.

### 적용 방법

**자동 적용**:
- `.claude/rules/pipeline-design.md` 신설
- `CLAUDE.md` `<important if>` 블록 추가
- `self-verify.md` 체크리스트 연계 섹션 추가

**수동 적용**:
- [ ] **파이프라인 프로젝트 — 로컬 사례 추가 (권장)**:
  `docs/incidents/{abbr}_pipeline_origin.md` 작성 후
  `pipeline-design.md` 하단 "프로젝트 고유 사례" 섹션에 링크 추가.

### 검증
```bash
ls .claude/rules/pipeline-design.md  # 존재 확인
grep -c "pipeline-design" CLAUDE.md  # 1 이상
```

---

## v0.17.1 — review tool call 예산 재설계

### 변경 내용

review 에이전트: 3관점 → 2축(계약·스코프) + 회귀 알파(S7·S8 hit 시만).
조기 중단 허용. tool call 평균 ~5회 → ~3회.

### 적용 방법

**자동 적용**:
- `.claude/agents/review.md` 전면 재구성

**수동 적용**:
- [ ] **커스텀 review.md 오버라이드한 경우 병합 필요** — 주요 변경: "3관점 → 2축 + 회귀 알파", 조기 중단 섹션 추가, 신호 매핑 표에 발동 조건 열 추가

### 검증
```bash
grep -c "2축\|회귀 알파\|조기 중단" .claude/agents/review.md  # 3 이상
```

---

## v0.17.0 — review staging 5줄 룰 (경로 기반 이진 판정)

### 변경 내용

Stage 결정 1단계 전면 대체. 기존 16줄 룰 → 경로 기반 5줄 룰.
다중 도메인 격상(룰 A) 폐기.

### 적용 방법

**자동 적용**:
- `staging.md` Stage 결정 1단계 교체
- `pre_commit_check.py` RECOMMENDED_STAGE 계산 블록 교체
- T21~T32 회귀 케이스 12개 추가

**수동 적용**:
- [ ] **다중 도메인 deep 유지 원할 시** — CLAUDE.md 또는 로컬 staging 섹션에 커스텀 룰 추가:
  ```
  # 예: src/payment/ + src/auth/ 혼합 → deep 유지
  ```

### 검증
```bash
python3 -m pytest .claude/scripts/test_pre_commit.py -q -k "T2" 2>&1
```

---

## v0.16.1 — `/commit --bulk` 플래그

### 변경 내용

거대 변경(파일 30+ / diff 1500줄+) 전용 `--bulk` 플래그 신설. review 대신
정량 가드 4종 실행. **v0.22에서 폐기됨** — bulk 스테이지 자체 제거, 커밋 분리 권장.

### 적용 방법

**자동 적용**:
- `bulk-commit-guards.sh` 신설 (v0.22에서 폐기)
- `staging.md` bulk 스테이지 추가 (v0.22에서 제거)

**수동 적용**:
- 없음 (v0.22 이상 upgrade 시 bulk 스테이지 자동 제거)

### 검증
v0.22 이상 upgrade 완료 시 자동 해소.

---

## v0.16.0 — 문서 네이밍 전면 개편 (도메인 약어 + 통합 원칙)

### 변경 내용

파일명에 도메인 약어(abbr) 체계 도입. 날짜 suffix 전면 금지. cluster 자동 매핑.

### 적용 방법

**자동 적용**:
- `naming.md`·`docs.md` 규칙 갱신
- `write-doc/SKILL.md` abbr 검증 추가
- `docs_ops.py` cluster 매핑 직교 파싱

**수동 적용**:
- [ ] **naming.md "도메인 약어" 표에 프로젝트 도메인 abbr 등록** (필수):
  ```
  | 도메인  | abbr | cluster 파일 |
  |---------|------|--------------|
  | payment | pm   | clusters/payment.md |
  | auth    | au   | clusters/auth.md    |
  ```
  미등록 시 `docs_ops.py validate` 경고 + cluster 매핑 실패.
- [ ] **기존 문서 파일명 마이그레이션 (선택)**:
  - A안 (권장): 갱신 시점마다 `git mv`로 점진 변경
  - B안: 일괄 스크립트로 한 번에 변경
  - C안: 현상 유지 (cluster 매핑은 동작, 신규만 신 규칙)

### 검증
```bash
python3 .claude/scripts/docs_ops.py validate  # 약어 누락·중복 경고 없어야 함
```

---

## v0.9.3 ~ v0.8.0

패치·보강 레벨 변경. 다운스트림 수동 액션 없음.

**자동 적용 요약**:
- v0.9.3: stage 격상 면제 버그 수정
- v0.9.1: rules 파일 다이어트, harness-upgrade 화이트리스트 보강
- v0.8.0: review 패턴 매핑 재설계, CPS 복원

---

## v0.6.0 이전

초기 인프라 구성. 현재 `harness-upgrade` 지원 범위 밖.
`harness-adopt`로 새로 이식 권장.
