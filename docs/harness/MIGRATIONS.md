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

**현재 버전 섹션 1개만 유지.** harness-upgrade 완료 후 해당 섹션 삭제.
버전 히스토리는 upstream git log가 SSOT (`git log --oneline --grep "(v0\."` 로 조회).

업그레이드 과정에서 발생한 충돌·이상 소견·수동 결정은 `docs/harness/migration-log.md`에
별도 기록한다 (다운스트림 소유, upstream은 읽기만).

## migration-log.md — 다운스트림 기록 문서

다운스트림 프로젝트 `docs/harness/migration-log.md`에 업그레이드마다 누적한다.
harness-upgrade 완료 시 버전 헤더를 자동 생성하며, **나머지는 다운스트림이 직접 채운다.**
upstream은 이 파일을 **절대 덮어쓰지 않는다.** 문제 발생 시 이 파일을 upstream에 전달.

```markdown
# migration-log

## v0.X → v0.Y (YYYY-MM-DD)

### 충돌·수동 결정
<!-- 3-way merge 충돌 해소 결정, theirs/ours 선택 이유 -->
- (없으면 생략)

### 이상 소견
<!-- 예상 밖 동작, 확인 필요 항목, upgrade 후 달라진 점 -->
- (없으면 생략)

### 수동 적용 결과
<!-- MIGRATIONS.md 수동 적용 항목 완료 여부 -->
- (없으면 생략)
```

기록할 것이 없는 버전은 헤더만 남겨도 된다.

---

## 포맷

```markdown
## vX.Y — 한 줄 요약

### 변경 파일
| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/skills/foo/SKILL.md` | 3-way merge | 변경 이유 한 줄 |
| `.claude/scripts/bar.py` | 자동 덮어쓰기 | |
| `.claude/agents/baz.md` | 신규 추가 | |

처리 값: `자동 덮어쓰기` · `3-way merge` · `신규 추가` · `삭제`

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

## v0.27.2 — 도메인 시스템 갭 수정 및 문서 참조 정합성 복구

### 변경 파일
| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/scripts/pre_commit_check.py` | 3-way merge | docs_ops 함수 import + S9 WIP 도메인 추출 수정 + 경로→도메인 3단계 구현 |
| `.claude/scripts/docs_ops.py` | 3-way merge | extract_path_domain_map 예시 블록 오파싱 수정 |
| `.claude/scripts/task_groups.py` | 자동 덮어쓰기 | NAMING_MD dead code 제거 |
| `.claude/scripts/test_pre_commit.py` | 3-way merge | _add_path_domain_map 헬퍼 실제 매핑 블록 참조로 수정 |
| `.claude/rules/naming.md` | 3-way merge | docs-ops.sh → docs_ops.py 참조 수정 + 실제 매핑 코드블록 추가 |
| `.claude/rules/docs.md` | 자동 덮어쓰기 | docs-ops.sh → docs_ops.py 참조 수정 (4곳) |
| `.claude/rules/staging.md` | 자동 덮어쓰기 | pre-commit-check.sh → pre_commit_check.py 참조 수정 (3곳) |
| `.claude/rules/security.md` | 자동 덮어쓰기 | install-secret-scan-hook.sh → install-starter-hooks.sh |
| `.claude/agents/review.md` | 3-way merge | pre-commit-check.sh → pre_commit_check.py, docs-ops.sh → docs_ops.py |
| `.claude/agents/doc-finder.md` | 자동 덮어쓰기 | docs-ops.sh → docs_ops.py |
| `.claude/agents/threat-analyst.md` | 3-way merge | pre-commit-check.sh → pre_commit_check.py + bash 스니펫 S1_LINE_PAT 기반으로 교체 |

### 변경 내용

**갭 1 — WIP 도메인 추출 오류 수정**: `pre_commit_check.py` S9 블록에서 WIP 파일
도메인을 라우팅 태그(`decisions`, `guides`)로 잘못 추출하던 문제 수정.
`docs_ops.detect_abbr()` + abbr→domain 역매핑으로 실제 도메인(`harness`, `meta`) 추출.
WIP-only 커밋에서 critical 도메인이 deep으로 격상되지 않던 문제 해소.

**갭 2 — naming.md 파싱 중복 제거**: `pre_commit_check.py`가 `docs_ops.py`의
`extract_abbrs`, `detect_abbr`, `extract_path_domain_map`, `path_to_domain`을
동적 import해 재사용. naming.md를 두 스크립트가 별도 파싱하던 중복 제거.

**갭 3 — 경로→도메인 매핑 3단계 구현**: staging.md 명세 4단계 중 3단계
(naming.md 경로→도메인 매핑)가 구현되지 않던 문제 수정. naming.md에
`실제 매핑` 코드블록 영역 추가 — 다운스트림이 여기에 경로 매핑 등록 시 S9에 반영.

**문서 참조 정합성**: 존재하지 않는 `docs-ops.sh`, `pre-commit-check.sh`,
`install-secret-scan-hook.sh` 참조를 실제 파일명으로 일괄 수정 (총 14곳).

### 적용 방법

**자동 적용**: harness-upgrade가 처리. 확인만.

**수동 적용**: naming.md `## 경로 → 도메인 매핑` 섹션 하단 `실제 매핑` 코드블록에
프로젝트 코드 폴더 경로 매핑 추가 권장 (S9 도메인 등급 신호 정확도 향상).
예: `src/payment/**     → payment`

### 검증
`python3 -m pytest .claude/scripts/test_pre_commit.py -q` → 56 passed.

---

## v0.27.1 — eval 기본 모드 보고 구조 개선 (거시/미시 계층 + memory 저장)

### 변경 파일
| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/skills/eval/SKILL.md` | 3-way merge | 기본 모드 절차 4→6단계 확장 |

### 변경 내용

`/eval` 기본 모드 절차에 분류(4)·보고(5)·저장(6) 단계 추가.

- 발견된 간극을 **거시**(CPS 방향 이탈) / **단기 블로커**(다음 작업 차단) / **장기 부채**(방치 시 위험) 세 층으로 분류
- 대화 출력은 거시 요약 + 단기 블로커만 간결하게, 장기 부채 상세는 memory 참조로 압축
- eval 완료 시 항상 `.claude/memory/project_eval_last.md`에 전체 상세를 덮어쓰기 저장 + `MEMORY.md` 인덱스 갱신 (0건이어도 실행)

### 적용 방법

**자동 적용**: harness-upgrade가 처리. 확인만.

**수동 적용**: 없음

### 검증
`/eval` 실행 후 `.claude/memory/project_eval_last.md` 생성 여부 확인.

---

## v0.27.0 — UserPromptSubmit debug-guard 훅 신설

### 변경 파일
| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/scripts/debug-guard.sh` | 신규 추가 | UserPromptSubmit 키워드 감지 스크립트 |

### 변경 내용
사용자 메시지에 "에러", "버그", "오류", "원인" 등 키워드가 감지되면
`debug-specialist` 에이전트를 먼저 호출하도록 Claude 컨텍스트에 주입.
Claude가 직접 추측 수정으로 진행하는 패턴을 시스템 레벨에서 차단.

### 적용 방법

**자동 적용**: harness-upgrade가 처리. 확인만.

**수동 적용**: 없음

### 검증
`echo '{"prompt":"에러났어 원인을 찾아"}' | bash .claude/scripts/debug-guard.sh`
→ `⚠️ [debug-guard]` 메시지 출력되면 정상.

---

## v0.26.9 — harness-upgrade 커밋 분기 + MIGRATIONS 변경 파일 섹션

### 변경 파일
| 파일 | 처리 | 비고 |
|------|------|------|
| `.claude/skills/harness-upgrade/SKILL.md` | 3-way merge | Step 10 커밋 분기 + Step 3 변경 파일 표 참조 추가 |
| `docs/harness/MIGRATIONS.md` | 자동 덮어쓰기 | `### 변경 파일` 섹션 포맷 추가 |

### 변경 내용

- `harness-upgrade/SKILL.md` Step 10: 커밋 시 `CONFLICT_RESOLVED` 유무로 분기. 충돌 해소 파일 없으면 `HARNESS_UPGRADE=1`로 review skip, 있으면 해당 파일만 `--quick` review
- `harness-upgrade/SKILL.md` Step 3: MIGRATIONS.md `### 변경 파일` 표를 git diff보다 우선 참조해 처리 방식 결정
- `MIGRATIONS.md` 포맷에 `### 변경 파일` 섹션 추가 — 파일별 처리 방식(`자동 덮어쓰기`·`3-way merge`·`신규 추가`·`삭제`) 명시

### 적용 방법

**자동 적용**: harness-upgrade가 처리

**수동 적용**: 없음

---

## v0.26.8 — commit Step 4 다운스트림 skip 명시

### 변경 내용

- `commit/SKILL.md` Step 4: `is_starter` 값을 먼저 확인해 `false`(다운스트림)이면 Step 4 전체를 건너뛰도록 명시. 기존에는 스크립트가 내부적으로 exit했지만 Step 자체는 실행됐음

### 적용 방법

**자동 적용**: harness-upgrade가 처리

**수동 적용**: 없음

---

## v0.26.7 — harness_version_bump.py HEAD 버전 기준 수정

### 변경 내용

- `harness_version_bump.py`: `current` 버전을 디스크(HARNESS.json)가 아닌 HEAD에서 읽도록 수정. commit Step 4에서 HARNESS.json을 디스크에 먼저 쓰고 staged하면 `current`가 이미 범프된 버전을 가리켜 "범프 필요" 오탐 발생하던 버그 수정

### 적용 방법

**자동 적용**: 스크립트 갱신

**수동 적용**: 없음

---

## v0.26.6 — harness-upgrade Step 9.7 오탐 수정 + Step 10.4 제거

### 변경 내용

- harness-upgrade Step 9.7: `grep "- \[ \]"` 패턴이 백틱 인라인 코드(`` `- [ ]` ``)까지 오탐하던 문제 수정 — `grep -v` 추가
- harness-upgrade Step 10.4 제거: MIGRATIONS.md는 Step 3 자동 덮어쓰기로 이미 단일 섹션 유지됨. Claude가 섹션을 수동 삭제하는 불안정한 단계 제거

### 적용 방법

**자동 적용**: harness-upgrade SKILL.md 갱신

**수동 적용**: 없음

---

## v0.26.5 — hook 버전 체크 제거 + pre-check 경고로 이전

### 변경 내용

- `install-starter-hooks.sh`: hook의 버전 범프 체크 로직 제거. 버전 판단은 commit Step 4(Claude)가 담당
- `pre_commit_check.py`: is_starter 전용 버전 미범프 경고 추가 (차단 아님 — `risk_factors`에 기록)

### 적용 방법

**자동 적용**: 스크립트 갱신. hook은 `harness-sync` 또는 `bash .claude/scripts/install-starter-hooks.sh` 재실행으로 갱신.

**수동 적용**: 없음

---

