---
title: starter 전용 스킬 격리 — harness-dev 스킬 신설
domain: harness
tags: [skill, starter, isolation, harness-dev]
relates-to:
  - path: harness/hn_upstream_only_audit.md
    rel: extends
status: completed
updated: 2026-04-28
created: 2026-04-28
---

# starter 전용 스킬 격리 — harness-dev 스킬 신설

## 배경

### 발단 (2026-04-28 세션)

`install-starter-hooks.sh` 신설 시 `h-setup.sh`와 `README.md`를 수동으로
별도 커밋해야 했다. starter에 스크립트·hook을 추가할 때마다 이 두 파일을
손으로 수정해야 하는 반복 작업이 발생.

### 현재 구분 방식의 문제

HARNESS.json `skills` 목록으로 starter 전용 스킬을 구분하려 했으나
실제 파일 복사는 막지 못한다.

```
HARNESS.json skills 목록 (다운스트림 전달 표시용):
  harness-upgrade, implementation, commit, advisor, ...  ← 9개

실제 .claude/skills/ 폴더:
  위 9개 + harness-adopt, harness-init, harness-sync  ← 3개 추가
```

`harness-adopt`, `harness-init`, `harness-sync`는 목록에서 빠졌지만
harness-upgrade가 `.claude/` 전체를 복사하므로 다운스트림에 그대로 전달된다.
"목록 제외 = 전달 안 됨"이 아닌 구조적 허점.

### 격리가 필요한 스킬 목록 (현재 파악)

| 스킬 | 이유 |
|------|------|
| `harness-init` | 신규 프로젝트 초기화 — 다운스트림이 쓸 수 없음 (starter 구조 전제) |
| `harness-adopt` | 기존 프로젝트 이식 — 동일 |
| `harness-sync` | 클론 후 환경 동기화 — 다운스트림도 쓰지만 starter 전용 hook 설치 포함 |
| `harness-dev` (신설) | h-setup.sh·README·HARNESS.json 갱신 — starter 개발자 전용 |

## 선택지

### A. `.claude/skills/starter-only/` 별도 폴더

starter 전용 스킬을 별도 하위 폴더로 분리. harness-upgrade가 이 폴더를
복사 제외.

```
.claude/skills/
├── starter-only/          ← harness-upgrade 복사 제외
│   ├── harness-init/
│   ├── harness-adopt/
│   └── harness-dev/
├── harness-sync/          ← 공용 (다운스트림도 필요)
├── commit/
└── ...
```

**장점**: 폴더 구조만으로 명확히 구분. harness-upgrade 로직 단순.
**단점**: 폴더 이동 필요 (기존 스킬 경로 변경). 다운스트림 MIGRATIONS 필요.

### B. HARNESS.json `starter_skills` 필드 추가

```json
{
  "skills": "harness-upgrade,implementation,...",
  "starter_skills": "harness-init,harness-adopt,harness-dev"
}
```

harness-upgrade가 `starter_skills` 목록의 스킬 폴더를 복사 제외.

**장점**: 폴더 이동 없음. 기존 경로 유지.
**단점**: harness-upgrade 로직 추가 필요. HARNESS.json 스키마 변경.

### C. 스킬 frontmatter `audience: starter`

각 스킬 SKILL.md에 `audience: starter` 추가. harness-upgrade가 이를 읽어 필터링.

```yaml
---
name: harness-init
audience: starter   # ← 이 필드 있으면 복사 제외
---
```

**장점**: 스킬별 세밀한 제어. HARNESS.json 스키마 불변.
**단점**: harness-upgrade가 SKILL.md를 파싱해야 함. 누락 시 silent fail.

## 결정

**B안 채택** — HARNESS.json `starter_skills` 필드 추가.

**근거**:
- 폴더 이동 없음 → 기존 스킬 경로 유지, 다운스트림 breaking change 최소
- HARNESS.json이 이미 메타데이터 허브 역할 → 스킬 목록 관리 SSOT 일관성
- harness-upgrade가 이미 HARNESS.json을 읽는 구조 → 파싱 로직 추가 부담 낮음
- C안(frontmatter)은 스킬 파일 내부를 파싱해야 해 취약성 높음

**뒤집힐 조건**: harness-upgrade 로직이 복잡해져 유지보수 부담이 커지면 A안 재검토.

## 구현 범위

### Phase 1: harness-dev 스킬 신설

**역할**: starter 개발자가 스크립트·hook·에이전트를 추가할 때 연동 파일을
자동 갱신하는 스킬.

**담당 작업**:
1. `h-setup.sh` — 새 스크립트 설치 단계 자동 추가
2. `README.md` — 파일 목록 + 설치 안내 자동 갱신
3. `HARNESS.json` — `skills`/`starter_skills` 목록 동기화
4. `docs/harness/MIGRATIONS.md` — 버전별 변경 이력 추가

**트리거**: "스크립트 추가", "에이전트 추가", "스킬 추가" 등 starter 구조
변경 요청 시.

**SKIP**: 코드 구현·문서 작업·커밋 — 각자 해당 스킬로.

### Phase 2: HARNESS.json `starter_skills` 필드 + harness-upgrade 필터링

```json
{
  "skills": "harness-upgrade,implementation,commit,...",
  "starter_skills": "harness-init,harness-adopt,harness-dev"
}
```

harness-upgrade Step에서 `starter_skills` 목록의 스킬 폴더를 복사 제외.
`harness-sync`는 공용 유지 (다운스트림도 클론 후 환경 동기화에 필요).

### Phase 3: 기존 starter 전용 스킬 정리

`harness-init`, `harness-adopt`를 `starter_skills`에 등록.
MIGRATIONS.md에 수동 액션 안내 추가.

## 실행 순서

1. Phase 1: `harness-dev` SKILL.md 작성 (스킬 신설)
2. Phase 2: HARNESS.json 스키마 확장 + harness-upgrade 필터링 로직
3. Phase 3: 기존 스킬 등록 + MIGRATIONS.md

Phase 1만 먼저 해도 h-setup.sh·README 수동 수정 반복 문제는 해결됨.

## 관련 작업 (이 결정에서 파생, 별도 진행)

### 1. 기존 다운스트림 마이그레이션 안내 (MIGRATIONS.md)

이미 harness-upgrade를 통해 `harness-init`, `harness-adopt` 폴더를 받은 다운스트림:
- 기능상 문제 없음 (스킬이 있어도 실행 안 하면 무해)
- 하지만 깔끔하게 정리하고 싶다면 삭제 가능
- MIGRATIONS.md에 안내 추가 필요:
  ```
  선택적 정리: .claude/skills/harness-init/, harness-adopt/ 폴더 삭제 가능
  (이 스킬들은 harness-starter 개발용, 일반 프로젝트에서는 불필요)
  ```
- 구버전 HARNESS.json(`starter_skills` 필드 없음)의 다운스트림은
  upgrade 시 여전히 이 스킬들을 받게 됨 → h-setup.sh upgrade 경로가
  `starter_skills`를 읽지 못해 필터링 안 됨. 해결: upgrade 경로에서
  `starter_skills` 필드 없으면 기본값(`harness-init,harness-adopt,harness-dev`)
  하드코딩 폴백 추가.

### 2. harness-adopt / harness-sync / harness-upgrade 역할 중복 분석 (완료)

**분석 결과: 분리 유지. 병합 불가.**

세 스킬은 생명주기 3단계를 각각 담당하며 교차하지 않는다:

| | adopt | sync | upgrade |
|--|------|------|---------|
| 언제 | 기존 프로젝트 이식 1회 | 클론 후 머신당 1회 | 업스트림 갱신 주기적 |
| 무엇을 | `.claude/` 이식 + `docs/` 재분류 | 의존성·권한·hook 설치만 (파일 내용 안 건드림) | 업스트림 diff → 3-way merge |
| 전제 조건 | `adopted_at` 없음 | `adopted_at` 있음 | `adopted_at` 있음 |

adopt와 upgrade가 "파일 병합"이라는 겉모습은 비슷하나 방향이 반대:
- adopt: 기존 프로젝트 → 하네스 구조로 변환
- upgrade: 업스트림 변경 → 다운스트림에 적용

upgrade가 adopt를 내부에서 호출하는 위임 계층이 이미 설계됨 (upgrade SKILL.md L53~61).

**사용자가 "비슷해 보인다"고 느끼는 원인**: README 설명이 차이를 명확히 표현하지 않음.
→ README에서 세 스킬의 생명주기 단계를 명시적으로 구분하는 것이 실용적 해결책.
   (별도 커밋으로 처리 — 이 WIP 범위 밖)

## 메모

- `harness-sync`는 공용 유지. 다운스트림도 클론 후 hook 설치 등에 사용.
  단 starter 전용 hook(install-starter-hooks.sh)은 is_starter 가드로 자체 격리.
- 이 결정 자체가 starter 전용이므로 다운스트림 오염 없음.
- 관련 incident: 2026-04-28 install-starter-hooks.sh 신설 시 h-setup.sh·README
  수동 수정 2회 발생이 직접 동기.
