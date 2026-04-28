---
title: 하네스 자잘한 버그 묶음 — MIGRATIONS 누락·starter_skills 오염·permissions.allow 미전파·h-setup.sh 오분류·신규설치 필터 누락·harness-sync 경계 불명확·docs/harness 전달 오염
domain: harness
tags: [migration, harness-dev, harness-upgrade, bug]
relates-to:
  - path: decisions/hn_starter_skill_isolation.md
    rel: caused-by
status: completed
created: 2026-04-28
updated: 2026-04-28
---

# 하네스 자잘한 버그 묶음

## 사전 준비
- 읽을 문서:
  - `docs/decisions/hn_starter_skill_isolation.md` — MIGRATIONS 안내 추가 미완 항목
  - `docs/harness/MIGRATIONS.md` — 현재 최신 엔트리 v0.22 (실제 v0.25.0)
  - `.claude/skills/harness-dev/SKILL.md` — Step 5 "버전 범프 동반 시" 조건부 기술
  - `.claude/skills/harness-upgrade/SKILL.md` — Step 8 (settings.json 동기화)
  - `.claude/scripts/pre_commit_check.py` — S11_PAT, UPSTREAM_PAT
- 이전 산출물: 없음

## 목표

버그 9개를 한 WIP로 관리. 각각 독립적으로 수정 가능.

- **버그 1**: harness-dev에 버전 범프 절차 없음 → MIGRATIONS.md 누락 반복
- **버그 2**: MIGRATIONS.md v0.23~v0.25 공백 → 다운스트림 수동 액션 안내 불가
- **버그 3**: starter_skills에 harness-dev 포함 → 자기 자신을 다운스트림 전달
- **버그 4**: harness-upgrade Step 8이 permissions.allow를 동기화 안 함 → 필수 항목 미전파
- **버그 5**: h-setup.sh가 UPSTREAM_PAT에 없음 → S7/standard로 오분류 (deep이어야 함)
- **버그 6**: h-setup.sh 신규 설치 경로에 starter_skills 필터 없음 → harness-init/adopt가 다운스트림에 복사됨 (업그레이드 경로는 b75963d에서 이미 수정)
- **버그 7**: harness-sync가 HARNESS.json skills/starter_skills 어디에도 없음 → 경계 불명확
- **버그 8**: docs/harness/hn_*.md가 harness-upgrade Step 6 신규 파일 추가 제안 대상 → 다운스트림에 upstream 내부 이력 문서가 제안됨
- **버그 9**: MIGRATIONS.md가 기록물처럼 쌓이는 구조 → "이번에 뭘 해야 하는가" 지시 역할 못함, 포맷 불명확
- **신규 10**: migration-log.md 없음 → 다운스트림이 업그레이드 과정을 기록할 곳이 없고, upstream에 문제 전달 경로도 없음

## 작업 목록

### 1. harness-dev SKILL.md — 버전 범프 Step 명시
> kind: bug

**영향 파일**: `.claude/skills/harness-dev/SKILL.md`

**문제**: Step 5가 `"버전 범프 동반 시"` 조건부로만 안내 → 버전 올릴 때 명시적 절차 없어 누락 반복.

**수정 방향**:
- Step 5를 "버전 범프 절차" Step으로 격상: 언제 올리는지(semver 기준) + 어떻게(`harness_version_bump.py`) + MIGRATIONS.md에 뭘 써야 하는지 명시
- MIGRATIONS.md 포맷 템플릿(Task 9)을 인용

**Acceptance Criteria**:
- [ ] semver 판단 기준 명시 (patch/minor/major)
- [ ] `python3 .claude/scripts/harness_version_bump.py` 호출 방법 포함
- [ ] Task 9에서 정의한 3단 포맷 템플릿 인용
- [ ] "버전 범프 없이 스킬 완료" 케이스 SKIP 조건 명시

---

### 2. MIGRATIONS.md — v0.23.x ~ v0.25.0 누락분 채우기
> kind: docs

**영향 파일**: `docs/harness/MIGRATIONS.md`

**방법**: git log 분석 → 다운스트림 수동 액션 필요 여부 판단 → Task 9 새 포맷으로 섹션 추가

**대상 버전 (git log 기반)**:
- `v0.23.x` — debug-specialist 강화, split 자동 stage, 버전 체크 스테이징 이후 이동
- `v0.24.0` — `install-starter-hooks.sh` 신설, hooks.md 적용 범위 명확화
- `v0.25.0` — harness-dev 신설, HARNESS.json `starter_skills` 필드 추가

**Acceptance Criteria**:
- [ ] v0.23, v0.24, v0.25 섹션 추가 (Task 9 포맷 적용)
- [ ] v0.25.0 — `starter_skills` 필드 신설 안내 + harness-init/adopt 폴더 선택적 삭제 안내 포함

---

### 3. HARNESS.json starter_skills — harness-dev 제거
> kind: bug

**영향 파일**: `.claude/HARNESS.json`

**문제**: `"starter_skills": "harness-init,harness-adopt,harness-dev"` — harness-dev가 자기 자신을 다운스트림에 전달.

**수정**: starter_skills에서 `harness-dev` 제거.

**Acceptance Criteria**:
- [ ] `starter_skills` 값이 `"harness-init,harness-adopt"`로 변경됨

---

### 4. harness-upgrade Step 8 — permissions.allow 동기화 추가
> kind: bug

**영향 파일**: `.claude/skills/harness-upgrade/SKILL.md`

**문제**: Step 8이 hooks 블록만 동기화. `permissions.allow`는 전체를 "사용자 커스텀"으로 간주 → upstream 신규 항목이 다운스트림에 전파 안 됨. v0.23 이전 설치 다운스트림은 업그레이드 후에도 매 명령마다 승인 프롬프트가 뜨는 상태.

**수정 방향**:
- upstream allow 목록 vs 현재 allow 목록 diff
- upstream에만 있는 항목 = starter 신규 추가 → 추가 제안
- 현재에만 있는 항목 = 사용자 추가 → 보존

**Acceptance Criteria**:
- [ ] Step 8에 `permissions.allow` 동기화 절차 추가
- [ ] "starter 신규 항목 추가 제안" / "사용자 항목 보존" 구분 명시
- [ ] 실제 사례 (`"Bash(HARNESS_DEV=1 git *)"` 등) 예시 포함

---

### 5. pre_commit_check.py — h-setup.sh UPSTREAM_PAT 추가
> kind: bug

**영향 파일**: `.claude/scripts/pre_commit_check.py`

**문제**: `UPSTREAM_PAT`에 `h-setup.sh` 없음 → S7/standard 오분류.

**수정**:
```python
UPSTREAM_PAT = re.compile(
    r"^(?:\.claude/scripts/|\.claude/agents/|\.claude/hooks/|\.claude/settings\.json$|h-setup\.sh$)"
)
```

**Acceptance Criteria**:
- [ ] `h-setup.sh` 단독 수정 커밋 시 `recommended_stage: deep` 출력
- [ ] 기존 테스트 통과 (`python3 -m pytest .claude/scripts/test_pre_commit.py -q`)
- [ ] staging.md "업스트림 위험 경로" 근거에 `h-setup.sh` 추가

---

### 6. h-setup.sh 신규 설치 경로 — starter_skills 필터 추가
> kind: bug

**영향 파일**: `h-setup.sh`

**문제**: 업그레이드 경로(L276-284)는 `STARTER_SKILLS` 필터 있으나, 신규 설치 경로(L481-485)에는 없음. harness-init/adopt가 다운스트림 신규 설치 시 그대로 복사됨.

**수정**: 업그레이드 경로의 필터 패턴을 신규 설치 경로에도 동일하게 적용.

**Acceptance Criteria**:
- [ ] 신규 설치 시 `starter_skills` 목록의 스킬 폴더가 복사되지 않음
- [ ] 업그레이드/신규설치 양쪽 필터 로직이 동일한 패턴 사용

---

### 7. HARNESS.json — harness-sync skills 등록
> kind: chore

**영향 파일**: `.claude/HARNESS.json`

**문제**: harness-sync가 `skills`/`starter_skills` 어디에도 없어 경계 불명확.

**판단**: 다운스트림도 클론 후 환경 동기화에 필요 → `skills`에 추가.

**수정**: `skills` 목록에 `harness-sync` 추가.

**Acceptance Criteria**:
- [ ] HARNESS.json `skills`에 `harness-sync` 포함됨

---

### 8. harness-upgrade Step 3 — docs/harness/ 사용자 전용 목록 추가
> kind: bug

**영향 파일**: `.claude/skills/harness-upgrade/SKILL.md`

**문제**: Step 3 사용자 전용 목록에 `docs/harness/*` 없음 → upstream에 새 `hn_*.md` 생길 때마다 Step 6에서 다운스트림에 추가 제안됨.

**수정**: Step 3 사용자 전용 목록에 `docs/harness/*` 추가. 단 `docs/harness/MIGRATIONS.md`는 제외 (다운스트림 필수).

**Acceptance Criteria**:
- [ ] Step 3 사용자 전용 카테고리에 `docs/harness/*` (MIGRATIONS.md 제외) 명시
- [ ] Step 6에서 `docs/harness/hn_*.md` 추가 제안 안 뜸

---

### 9. MIGRATIONS.md 재설계 — 지시 문서로 재정의 + 포맷 표준화
> kind: refactor

**영향 파일**: `docs/harness/MIGRATIONS.md`, `.claude/skills/harness-upgrade/SKILL.md`

**문제**: MIGRATIONS.md가 현재 "과거 기록물"처럼 쌓이는 구조. 다운스트림 입장에서
"이번 업그레이드에서 내가 뭘 해야 하는가"를 직접 알기 어려움.
적용 방식이 버전마다 달라 까다로운 경우 안내가 부족.

**재정의**:
- MIGRATIONS.md = upstream 소유·관리. 다운스트림은 읽기만.
- 역할: 버전별 "이번에 뭐가 바뀌었고 어떻게 적용하는가" 지시 문서
- 적용이 까다로운 항목은 상세 가이드 포함
- harness-upgrade Step 9.5가 현재 버전 → 최신 버전 사이 섹션만 추출해 표시

**표준 포맷**:
```markdown
## v0.X — 한 줄 요약

### 변경 내용
이번 버전에서 달라진 것. 다운스트림이 맥락을 파악하기 위한 최소 설명.

### 적용 방법
harness-upgrade가 자동 처리하는 것과 직접 해야 하는 것을 명확히 구분.

**자동 적용**: harness-upgrade가 처리. 확인만.
- ...

**수동 적용**: upgrade 후 직접 실행. 안 하면 미동작.
- 없음  ← 없을 때도 명시
```

- "수동 적용 없음" 버전도 생략 말고 `없음` 명시 (누락인지 없는 건지 구분)
- 기존 누적된 배경 설명·긴 이력은 제거. 지시에 필요한 내용만 남김

**수정 범위**:
1. MIGRATIONS.md 상단 포맷 정의 섹션 추가
2. 기존 v0.8~v0.22 섹션 → 새 포맷으로 변환 (내용 압축, 지시 중심으로)
3. harness-dev SKILL.md(Task 1)에 이 포맷 템플릿 인용
4. harness-upgrade Step 9.5 — "현재~최신 사이 섹션만 추출" 로직 명시 보강

**Acceptance Criteria**:
- [ ] MIGRATIONS.md 상단에 포맷 정의 섹션 추가
- [ ] 기존 v0.8~v0.22 섹션이 새 포맷으로 변환됨 (지시 중심, 불필요한 배경 제거)
- [ ] harness-dev SKILL.md(Task 1)에서 이 포맷 인용
- [ ] harness-upgrade Step 9.5에 버전 범위 추출 로직 명시

---

### 10. migration-log.md 신설 — 다운스트림 업그레이드 기록 문서
> kind: feature

**영향 파일**: `.claude/skills/harness-upgrade/SKILL.md`, `docs/harness/MIGRATIONS.md` (설명 추가)

**설계**:
- `migration-log.md` = downstream 소유·작성. upstream은 읽기만(덮어쓰기 금지).
- 위치: 다운스트림 프로젝트 루트 또는 `docs/` — harness-upgrade가 없으면 자동 생성
- 기록 대상: 업그레이드 중 **주목할 만한 것만** — 충돌·수동 결정·이상 소견·실패한 것
  - 정상 자동 적용된 항목은 기록 안 해도 됨
- 문제 발생 시 이 파일을 upstream에 그대로 전달 → upstream이 맥락 파악 가능

**포맷**:
```markdown
# migration-log

## v0.X → v0.Y (YYYY-MM-DD)

### 충돌·수동 결정
- `.claude/rules/staging.md`: theirs 적용. 로컬 S9 커스텀 섹션 제거함.

### 이상 소견
- Step 8 완료 후 `Bash(python3 *)` 항목이 추가 안 됨 — 확인 필요.

### 수동 적용 결과
- naming.md 도메인 등급: payment=critical, api=normal 설정 완료.
```

**harness-upgrade 연동**:
- Step 완료 시 migration-log.md에 버전 섹션 자동 생성 (날짜·버전 헤더만)
- 나머지는 다운스트림이 직접 채움
- harness-upgrade가 migration-log.md를 **절대 덮어쓰지 않음** — append only

**Acceptance Criteria**:
- [ ] harness-upgrade SKILL.md Step 10(완료 처리)에 migration-log.md 섹션 자동 생성 추가
- [ ] "upstream은 이 파일을 덮어쓰지 않는다" 보장 명시
- [ ] MIGRATIONS.md 상단에 migration-log.md 존재와 역할 한 줄 안내 추가

---

## 실행 순서

3 → 7 → 5 → 6 → 9 → 10 → 1 → 4 → 8 → 2

- **3** (1줄): HARNESS.json starter_skills에서 harness-dev 제거
- **7** (1줄): HARNESS.json skills에 harness-sync 추가
- **5** (1줄+테스트): pre_commit_check.py UPSTREAM_PAT에 h-setup.sh 추가
- **6** (코드): h-setup.sh 신규 설치 경로 starter_skills 필터 추가
- **9** (설계+문서): MIGRATIONS.md 재설계 — Task 1·2·10이 의존
- **10** (문서): migration-log.md 신설 설계 — harness-upgrade Step 10 연동
- **1** (문서): harness-dev 버전 범프 절차 추가 (Task 9 포맷 인용)
- **4** (문서): harness-upgrade Step 8 permissions.allow 동기화 추가
- **8** (문서): harness-upgrade Step 3 docs/harness/* 추가
- **2** (분析+문서): MIGRATIONS.md 누락분 채우기 — 새 포맷으로 작성, git log 분析 필요해 마지막

## 결정 사항

- 새 WIP 분리 근거: 독립적인 신규 버그들, 기존 SSOT 없음
- Task 4 설계: 별도 HARNESS.json 필드 없이 upstream diff로 판단 — 단순함 우선
- Task 5 scope: UPSTREAM_PAT 한 줄 + staging.md 텍스트 동반 갱신
- Task 9 → Task 1 연동: 포맷 템플릿을 MIGRATIONS.md에 먼저 정의, harness-dev가 인용
- codebase-analyst 감사: 위반 8개 확인. 정상 영역 — install-starter-hooks.sh(is_starter 체크로 다운스트림 안전), docs/WIP 보호(Step 3 사용자 전용 목록 명시), hooks 블록 동기화 정상

## 메모

- Task 4: hooks.md "금지" 섹션과 혼동 주의 — `permissions.allow`의 `Bash(...)` 패턴은 허용 목록이라 hooks.md 규칙 적용 안 됨
- Task 6: `harness-init`/`harness-adopt`가 다운스트림 최초 설치 후 필요한지 여부 — starter_skills 등록 자체가 설계 오류일 수 있음. 현재는 "전달 의도 아님"으로 판단
- Task 9 소급 범위: v0.8~v0.22 (기존 섹션 전부). 내용 손실 없이 구조만 변환
