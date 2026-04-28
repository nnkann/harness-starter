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

### Step 5. MIGRATIONS.md 갱신 (버전 범프 동반 시)

버전이 올라가는 커밋과 함께 연동 파일이 변경됐으면 MIGRATIONS.md 해당 버전 섹션에 기록:

```markdown
### 자동 적용 (스킬이 처리)
- <변경 내용 1줄>

### 수동 액션 (다운스트림 필수)
- (필요 시만)
```

### Step 6. 완료 확인

- [ ] h-setup.sh: 새 스크립트 호출이 반영됐는가 (필요 시)
- [ ] README.md: 파일 목록에 추가됐는가
- [ ] HARNESS.json: 올바른 필드(`skills`/`starter_skills`)에 등록됐는가
- [ ] MIGRATIONS.md: 버전 범프 동반 시 섹션 추가됐는가

---

## 주의

- **다운스트림 오염 금지**: h-setup.sh·README.md·MIGRATIONS.md에 다운스트림
  고유명사·프로젝트명을 직접 쓰지 마라 (docs.md "incidents/ 오염 면제" 참조).
- **하나씩**: 여러 스크립트를 한 번에 추가하면 각각 Step 2~5를 반복.
  한 스크립트 = 한 사이클.
- **설명 한 줄**: README 파일 목록 설명은 한 줄 이내. 상세는 SKILL.md/스크립트 주석에.
