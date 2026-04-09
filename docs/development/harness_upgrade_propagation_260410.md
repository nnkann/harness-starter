> status: completed

# 하네스 스타터 업그레이드 전파 전략

## 배경

harness-starter가 6단계 업그레이드(7c14536)를 거쳤다. 변경 내용:
- 새 파일 5개: `memory.md`, `stop-guard.sh`, `write-guard.sh`, `advisor/SKILL.md`, `harness-sync/SKILL.md`
- 수정 파일 9개: 스크립트 3개, settings.json, 스킬 4개, h-setup.sh

**문제**: 현재 `h-setup.sh`의 `copy_if_new`는 기존 파일을 덮어쓰지 않으므로, 이미 적용된 프로젝트에 업그레이드를 반영할 방법이 없다.

## 시나리오 분류

| 시나리오 | 설명 | 복잡도 |
|----------|------|--------|
| A. 신규 프로젝트 | h-setup.sh 실행하면 최신 버전 적용 | 없음 (현재 작동) |
| B. 하네스만 적용, 코드 없음 | harness-init 실행 전. 파일 커스터마이징 없음 | 낮음 |
| C. 진행 중인 프로젝트 | harness-init 완료, 코드 작성 중. 파일 커스터마이징 있음 | **높음** |

핵심 난이도는 **시나리오 C**다. 사용자가 스크립트/스킬/settings.json을 커스터마이징했을 수 있다.

## 분석: 파일별 업그레이드 난이도

### 1. 새 파일 (충돌 가능성 0)

| 파일 | 전략 |
|------|------|
| `.claude/rules/memory.md` | 그냥 복사 |
| `.claude/scripts/stop-guard.sh` | 그냥 복사 |
| `.claude/scripts/write-guard.sh` | 그냥 복사 |
| `.claude/skills/advisor/SKILL.md` | 그냥 복사 |
| `.claude/settings.json`의 새 훅 (Stop, Write) | **병합 필요** |

### 2. 수정된 파일 (충돌 가능성 있음)

| 파일 | 변경 내용 | 커스터마이징 가능성 |
|------|----------|-------------------|
| `session-start.sh` | git 상태 출력 개선 | 낮음 (대부분 건드리지 않음) |
| `post-compact-guard.sh` | WIP 결정사항 재주입, compact 카운터 | 낮음 |
| `pre-commit-check.sh` | 동적 패키지 매니저, 향상된 검사 | **중간** (린터 명령 변경 가능) |
| `settings.json` | Stop 훅, Write 훅, prompt 훅 추가 | **높음** (사용자가 커스텀 훅 추가 가능) |
| `commit/SKILL.md` | 마이너 수정 | 낮음 |
| `eval/SKILL.md` | --quick, --deep, --surface 추가 | 낮음 |
| `implementation/SKILL.md` | advisor 연동 추가 | 낮음 |
| `harness-init/SKILL.md` | advisor 연동 추가 | 낮음 |

### 3. 핵심 위험: settings.json

`settings.json`이 가장 위험하다. 이유:
- 사용자가 프로젝트 고유 훅을 추가했을 수 있음
- JSON은 단순 덮어쓰기 시 사용자 설정 소실
- 배열 병합(hooks 배열에 항목 추가)이 필요

## 접근법 후보

### 방안 1: `h-setup.sh --upgrade` 플래그

```bash
bash h-setup.sh --upgrade [타겟_디렉토리]
```

동작:
1. 새 파일 → 바로 복사
2. 스크립트 (.sh) → diff 분석 후 **병합** 시도. 병합 결과 검증(구문 오류 등). 충돌 시 사용자 확인.
3. settings.json → JSON 병합 (jq로 새 훅만 추가, 기존 유지)
4. SKILL.md → diff 분석 후 **병합** 시도. 충돌 시 사용자 확인.
5. CLAUDE.md → `## 환경` 섹션은 보존, `## 절대 규칙` 등 하네스 공통 섹션은 병합. 새 규칙이 추가되었으면 반영.
6. rules/ → diff 분석 후 **병합**. 사용자가 채운 내용(coding.md, naming.md의 도메인/패턴)은 보존. 하네스가 추가한 새 섹션만 병합. 중복/과도한 설정은 사용자 확인.

**장점**: 자동화, 반복 가능
**단점**: jq 의존, 복잡한 병합 로직, 엣지 케이스 많음

### 방안 2: `harness-upgrade` 스킬 (Claude가 수행)

```
/harness-upgrade
```

Claude가 직접:
1. 현재 프로젝트의 하네스 파일과 스타터의 최신 버전을 비교
2. 차이점을 분석하고 사용자에게 보고
3. 사용자 확인 후 파일별로 적용
4. settings.json은 JSON 파싱으로 훅만 추가

**장점**: 유연함, 맥락 이해, 커스터마이징 보존 가능
**단점**: 토큰 비용, 스타터 repo에 접근 필요

### 방안 3: 하이브리드 (추천)

1. `h-setup.sh --upgrade` — 새 파일 복사 + 변경 감지 + 병합 시도까지 자동
2. `harness-upgrade` 스킬 — 자동 병합 실패 항목에 대해 사용자에게 **승인 요청**. 별도 스킬 호출을 요구하지 않고, 업그레이드 흐름 내에서 바로 처리.

흐름:
```
사용자: bash h-setup.sh --upgrade /path/to/project
  → 새 파일 5개 복사됨
  → 자동 병합 성공 3개, 충돌 5개 감지됨
  → 충돌 항목별 diff + 병합 제안을 보여주고 승인 요청

사용자: /harness-upgrade
  → Claude가 diff 분석, 사용자와 대화하며 병합
```

## 세부 설계: 하이브리드 방안

### Part A: `h-setup.sh --upgrade` 추가

```bash
# 새 동작
--upgrade  기존 하네스를 최신으로 업그레이드.
           새 파일은 바로 복사, 수정 파일은 .upgrade/ 에 복사 후 diff 보고.
```

로직:
1. `harness.json` 존재 확인 (하네스 적용된 프로젝트인지)
2. 새 파일 → `copy_if_new` (기존 로직 재활용)
3. 수정 파일 → `$TARGET/.claude/.upgrade/` 에 최신 버전 복사
4. 각 파일에 대해 `diff` 출력하고 요약 리포트 생성
5. `harness.json`에 `upgraded_at` 필드 추가

산출물:
```
.claude/.upgrade/
├── scripts/
│   ├── session-start.sh
│   ├── post-compact-guard.sh
│   └── pre-commit-check.sh
├── settings.json
└── skills/
    ├── commit/SKILL.md
    ├── eval/SKILL.md
    ├── implementation/SKILL.md
    └── harness-init/SKILL.md
```

+ `.claude/.upgrade/UPGRADE_REPORT.md` (diff 요약)

### Part B: `harness-upgrade` 스킬

```
/harness-upgrade
```

전제: `.claude/.upgrade/` 디렉토리가 존재 (h-setup.sh --upgrade 실행 완료)

흐름:
1. `.upgrade/UPGRADE_REPORT.md` 읽기
2. 파일별 순회:
   - 현재 파일과 업그레이드 파일의 diff 분석
   - 사용자 커스터마이징 부분 식별
   - "이 변경을 적용할까요?" 확인
   - settings.json은 특별 처리 (JSON 병합)
3. 적용 완료 후 `.upgrade/` 디렉토리 삭제
4. `harness.json` 업데이트

### Part C: settings.json 병합 전략

가장 까다로운 부분. 전략:

```
현재 settings.json의 훅 목록을 파싱
 → 새 훅 중 현재에 없는 것만 추가
 → 기존 훅의 command/prompt가 변경된 경우 사용자에게 diff 보여주고 선택
 → 사용자가 추가한 커스텀 훅은 보존
```

### Part D: 버전 관리

현재 `harness.json`에는 버전 개념이 없다. **semver** 채택하여 추가:

```json
{
  "profile": "standard",
  "skills": "...",
  "installed_at": "2026-04-08T...",
  "version": "0.6.0",
  "upgraded_at": null
}
```

스타터 repo:
- `.claude/HARNESS_VERSION` 파일에 현재 버전 명시 (예: `0.6.0`)
- `h-setup.sh --upgrade` 실행 시 스타터의 VERSION과 타겟의 harness.json version 비교
- major 변경(1.x): 수동 마이그레이션 필요할 수 있음 경고
- minor 변경(0.x→0.y): 자동 병합 시도
- patch 변경(0.6.x): 안전한 업데이트

## 구현 순서

| 순서 | 작업 | 파일 |
|------|------|------|
| 1 | 버전 체계 도입 | `.claude/HARNESS_VERSION`, `harness.json` 스키마 변경 |
| 2 | `h-setup.sh --upgrade` 구현 | `h-setup.sh` |
| 3 | `harness-upgrade` 스킬 작성 | `.claude/skills/harness-upgrade/SKILL.md` |
| 4 | `.upgrade/` 를 `.gitignore`에 추가 | `.gitignore` 템플릿 |
| 5 | UPGRADE_REPORT.md 생성 로직 | `h-setup.sh` 내부 |
| 6 | settings.json 병합 유틸 | `h-setup.sh` 또는 별도 스크립트 |
| 7 | README.md 업그레이드 내역 반영 | `README.md` |
| 8 | 기존 프로젝트 테스트 | 실제 적용 프로젝트에서 검증 |

## 미결정 사항

- [x] 버전 체계: **semver** 채택. 변경 크기를 시그널링할 수 있어 업그레이드 판단에 유리. 현재 버전: 0.6.0.
- [x] 스타터 repo 연결: **독립 복사 유지**. submodule은 부적합 — h-setup.sh 실행 후 프로젝트 고유 파일(CLAUDE.md 환경, rules 내용)이 스타터와 달라지므로 submodule로 추적할 수 없음. 업그레이드는 `h-setup.sh --upgrade`로 해결.
- [x] CLAUDE.md `## 절대 규칙` 동기화: **한다**. 하네스 공통 규칙이므로 병합 대상. `## 환경` 섹션만 보존.
- [x] `--force` 옵션: **불허**. 사용자 확인 없는 전체 덮어쓰기는 커스터마이징 소실 위험이 너무 큼.
- [x] harness-sync vs harness-upgrade 역할 분리: **확정**. sync = 환경(의존성, 권한), upgrade = 하네스 파일 업데이트.

## 메모

- harness-sync는 **환경 동기화** (의존성 설치, 권한 설정)이고, harness-upgrade는 **하네스 파일 업데이트**. 명확히 다른 책임.
- CLAUDE.md는 `## 환경` 섹션은 보존, `## 절대 규칙` 등 하네스 공통 섹션은 병합.
- rules/ 파일은 사용자가 채운 내용 보존, 하네스가 추가한 새 섹션만 병합.
- **README.md 동기화**: 업그레이드 내역과 반영 내용을 README.md에 항상 반영. 업그레이드 스킬/스크립트 실행 시 README 변경 사항도 포함.