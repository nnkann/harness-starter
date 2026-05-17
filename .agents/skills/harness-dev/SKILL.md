---
name: harness-dev
description: harness-starter 개발자 전용. 스크립트·에이전트·스킬 추가 시 h-setup.sh·README.md·HARNESS.json·MIGRATIONS.md를 자동 갱신. 다운스트림 전달 안 됨 (starter_skills).
audience: starter
---

# harness-dev 스킬

**harness-starter 개발자 전용.** 새 스크립트·에이전트·스킬을 추가할 때
연동 파일들을 자동 갱신한다. 코드 구현·커밋은 각자 해당 스킬로.

## 트리거

- 새 `.claude/scripts/*.sh` 또는 `*.py` 추가
- 새 `.claude/agents/*.md` 추가
- 새 `.claude/skills/*/SKILL.md` 추가
- 위 항목의 역할·설명 변경으로 README 갱신이 필요할 때

## SKIP

- 코드 구현·수정 (→ implementation)
- 문서 작성 (→ write-doc)
- 커밋 (→ commit)
- 기존 파일 내용만 변경 (h-setup.sh·README 갱신 불필요)

---

## 흐름

### Step 1. 변경 유형 파악

사용자 발화에서 추가/변경 대상을 확인한다:

- **스크립트** (`scripts/*.sh` / `scripts/*.py`): h-setup.sh + README 갱신
- **에이전트** (`agents/*.md`): README 갱신
- **스킬** (`skills/*/SKILL.md`): HARNESS.json `skills` 또는 `starter_skills` + README 갱신
- **버전 범프 동반** 시: MIGRATIONS.md 갱신

### Step 2. h-setup.sh 갱신 (스크립트 추가 시)

새 스크립트가 설치·실행돼야 하면 h-setup.sh에 호출 추가.

**신설 경로** (L475 `# .claude/scripts/` 섹션):
```bash
copy_if_new "$src" "$TARGET/.claude/scripts/$(basename "$src")"
```
- `copy_if_new` 루프가 이미 `scripts/*.sh`를 전체 복사하므로 **별도 추가 불필요**.
- 단, 설치 후 **실행이 필요한** 스크립트(예: hook 설치)는 chmod 블록 아래에 호출 추가:
  ```bash
  bash "$TARGET/.claude/scripts/<new-script>.sh" 2>/dev/null || true
  ```

**업그레이드 경로** (L265 `# scripts` 섹션):
- `stage_or_copy` 루프가 전체 복사. 별도 추가 불필요.

### Step 3. README.md 갱신

**파일 목록** (`scripts/` 또는 `agents/` 트리):
- 기존 항목과 일관된 형식으로 한 줄 추가
- 위치: 알파벳·기능 순서 유지

```
    ├── <filename>  <한 줄 설명>
```

**설치 안내** (필요 시):
- 0a(h-setup.sh) 또는 0b(harness-sync) 단계 설명 갱신

### Step 4. HARNESS.json 갱신 (스킬 추가 시)

| 스킬 유형 | 대상 필드 |
|----------|----------|
| 다운스트림도 사용 | `skills` |
| starter 전용 | `starter_skills` |

```json
{
  "skills": "...,<new-skill>",
  "starter_skills": "...,<new-starter-skill>"
}
```

**판단 기준**:
- 다운스트림 프로젝트가 독립적으로 사용할 수 있는가? → `skills`
- harness-starter 구조(h-setup.sh·MIGRATIONS.md 등)를 전제로 하는가? → `starter_skills`

### Step 5. 버전 범프 + MIGRATIONS.md 갱신

**코드·동작 변경이 있으면 반드시 버전을 올린다.**

#### semver 판단 기준

| 변경 유형 | 범프 |
|----------|------|
| 다운스트림 breaking change (스킬 삭제·동작 역전·필드 제거) | minor |
| 새 기능·스킬·스크립트 추가, 동작 개선 | minor |
| 버그 수정·내부 리팩토링 (동작 무변경) | patch |
| **SKILL.md·rules/*.md Step 절차·체크리스트 변경** (Claude 행동에 영향) | **patch** |
| MIGRATIONS.md·README·주석·오타만 변경 | 범프 불필요 |

#### 버전 범프 실행

```bash
python3 .claude/scripts/harness_version_bump.py
# 출력 예: version_bump: minor → 0.25.0 → 0.26.0
```

스크립트가 HARNESS.json `version` 필드를 갱신한다.

#### MIGRATIONS.md 섹션 작성

버전 범프 후 `docs/harness/MIGRATIONS.md`에 새 버전 섹션 추가.
**포맷 SSOT는 MIGRATIONS.md 상단 "## 포맷" 섹션.** 반드시 그 포맷을 따른다.

```markdown
## v0.X — 한 줄 요약

### 변경 내용
이번 버전에서 달라진 것. 다운스트림이 맥락 파악용 최소 설명.

### 적용 방법

**자동 적용**: harness-upgrade가 처리. 확인만.
- ...

**수동 적용**: upgrade 후 직접 실행. 안 하면 미동작.
- 없음  ← 수동 액션 없을 때도 이 줄 명시

### 검증
적용 후 확인 방법. 생략 가능.
```

**작성 원칙**:
- "수동 적용 없음"도 `없음`으로 명시 (누락인지 없는 건지 구분)
- 배경 설명·긴 이력은 제거. 다운스트림이 "뭘 해야 하는가"에만 집중
- 다운스트림 고유명사 금지 (docs.md "오염 면제" 참조)

### Step 6. 완료 확인

- [ ] h-setup.sh: 새 스크립트 호출이 반영됐는가 (필요 시)
- [ ] README.md: 파일 목록에 추가됐는가
- [ ] HARNESS.json: 올바른 필드(`skills`/`starter_skills`)에 등록됐는가
- [ ] 버전 범프: `harness_version_bump.py` 실행하고 HARNESS.json `version` 갱신됐는가
- [ ] MIGRATIONS.md: 새 버전 섹션 추가됐는가 (포맷 준수)
- [ ] **테스트**: AC가 명시 요구하면 그 marker만 실행 (`pytest -m <marker>`). 무조건 전체 실행 금지. 회귀 가드 가치 있는 변경이면 작업 task의 AC `영향 범위:` 항목에 marker 명시
- [ ] **CPS**: `docs/guides/project_kickoff.md` Solutions 항목 중 이번 변경과 관련된 것 갱신했는가 (새 방어 레이어 추가·기존 Solution 구조 변경 시)
- [ ] **CPS 무결성**: `python3 .claude/scripts/eval_cps_integrity.py` 실행 — Problem 인용 빈도·Solution 충족 분포 확인
- [ ] **폐기 동반 본문 정비** (rules·skills·scripts 파일 삭제 시): 아래 폐기 절차 실행

---

## 폐기 절차 — 파일 삭제 시 본문 dead reference 동반 정비

defends P11 (동형 패턴 잠복 — 1차 발견 시 다른 위치 후보 자동 탐색 부재).
파일을 폐기하면 starter 본문(예시·트리·안내)이 dead reference로 잠복할
위험이 있다. 폐기 commit 안에서 본문 정비를 의무화한다.

### Step P1. 폐기 파일명 확정

삭제 대상 파일 basename·디렉토리 경로를 정리:
```
.claude/rules/<rule-name>.md
.claude/scripts/<script-name>.py
.claude/skills/<skill-name>/
```

### Step P2. 본문 전수 grep

```bash
git grep -nE "(<file1>|<file2>|...)" .claude/skills/ .claude/agents/ \
  .claude/rules/ README.md
```

hit 분류:
- **dead reference**: 살아있는 안내·예시·트리 구조 → 정비 의무
- **박제 표현 (면제)**: `폐기`·`흡수`·`삭제`·MIGRATIONS·`변경 이력` 키워드
  동반 → 의도적 잔존, 정비 불필요

### Step P3. 정비 옵션

| 라인 성격 | 처리 |
|---|---|
| 예시 (placeholder 가능) | `<deprecated-rule>.md` 같은 일반화 placeholder로 교체 |
| 안내·트리 (실재 항목 나열) | 줄 제거 |
| 다른 살아있는 항목으로 대체 가능 | 실재 파일명으로 교체 |
| 박제 표현 | 면제 — `(폐기됨, vXX.YY)` 한 줄 보강 권장 |

### Step P4. eval_harness 회귀 확인

```bash
python3 .claude/scripts/eval_harness.py 2>&1 | grep -A 5 "dead reference"
```

`검출 0건 ✅`이면 정비 완료. hit 잔존 시 Step P2부터 재실행.

### Step P5. eval_harness 패턴 등록

`eval_harness.py:_DEAD_REF_PATTERNS` 리스트에 폐기 파일명 추가 (재발 방지).
박제 표현 면제는 `_DEAD_REF_EXEMPT` 정규식이 자동 처리.

---

## 주의

- **다운스트림 오염 금지**: h-setup.sh·README.md·MIGRATIONS.md에 다운스트림
  고유명사·프로젝트명을 직접 쓰지 마라 (docs.md "incidents/ 오염 면제" 참조).
- **하나씩**: 여러 스크립트를 한 번에 추가하면 각각 Step 2~5를 반복.
  한 스크립트 = 한 사이클.
- **설명 한 줄**: README 파일 목록 설명은 한 줄 이내. 상세는 SKILL.md/스크립트 주석에.

