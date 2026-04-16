---
title: 하네스 스타터 개선 계획
domain: harness
tags: [improvement, profile, sync]
relates-to:
  - path: harness/promotion-log.md
    rel: references
status: completed
created: 2026-04-08
---

# 하네스 스타터 개선 계획

실제 셋업 사용 중 발견된 4가지 이슈를 정리한다. 각 항목은 독립 작업으로 구현 가능.

## 배경

하네스 스타터로 프로젝트를 셋업한 뒤 실사용하면서 드러난 문제들. 초기 설계 당시 예상하지 못했던 사용 흐름에서 마찰이 발생.

---

## 이슈 1. "학습모드" 기본 활성화 제거

### 현상
세션 시작 시 학습/교육 성격의 내용이 기본으로 주입되고 있음. 필요한 사람이 켜는 건 괜찮지만 **기본값으로 강제되는 것은 오류**.

### 확인 필요 (사용자 확인 요망)
"학습모드"가 구체적으로 어느 것을 가리키는지 확정해야 함. 후보:

1. **SessionStart hook의 RULES 자동 출력** — [session-start.sh:38-44](.claude/scripts/session-start.sh#L38-L44)
   매 세션 시작마다 4개 규칙을 무조건 출력. 초보자용 리마인드 성격.
2. **harness 강도 `light`가 기본** — [harness-init/SKILL.md:56-59](.claude/skills/harness-init/SKILL.md#L56-L59)
   `light` 기준에 "학습용"이 포함됨. 셋업 시 기본 추천일 가능성.//이게 맞는 것 같아. light모드라도 학습모드는 선택에 맞겨야 해.
3. **다른 후보** — 사용자가 실제로 본 메시지/동작 확인 필요.

### 방향
- 해당 위치 찾아서 기본값에서 제거. //setting.json에 들어가니까 이를 찾아서 막아야 함
- 옵션으로는 남겨두기(필요한 사람이 켤 수 있게). //어짜피 필요하다면 충분히 추가할 수 있음.
- README와 skill 설명에 "기본 OFF, 필요 시 활성화" 명시.

---

## 이슈 2. 첫 프로젝트 셋업 후 WIP 시작 문서 누락

### 현상
`h-setup.sh` 실행 → `docs/WIP/`가 비어 있음. `.gitkeep`만 생성. 사용자가 다음에 뭘 해야 할지 문서로 존재하지 않음.

### 현재 상태
- [harness-init/SKILL.md:197-254](.claude/skills/harness-init/SKILL.md#L197-L254)에 Step 8 "첫 번째 작업 생성"이 이미 정의돼 있음 — 도메인별 작업 문서를 만들게 돼 있음.
- 하지만 **그 이전**, `h-setup.sh` 직후 `harness-init`을 돌리기 전까지의 공백이 문제. 사용자는 `docs/WIP/`를 봤는데 아무것도 없으니 "다음에 뭘 해야 하는지" 모름.

### 방향
두 가지 선택지:

**A. `h-setup.sh`가 직접 시작 문서를 생성**
- `docs/WIP/harness_init_pending.md` 같은 파일을 만들고 내용은 "harness-init 스킬을 실행하세요" + 안내.
- `h-setup.sh` 완료 메시지와 중복이지만, 세션을 새로 켰을 때 session-start hook이 이 문서를 "진행 중인 작업"으로 보여줌 → 자연스럽게 유도됨. //실제 클로드 코드에서 하네스-스타터 프로젝트를 실행하면 자연스럽게 단계별로 필요 문서 요청하고 그에 맞는 스펙과 문서들을 정리하게 되는데 이 과정으로 인해 결정된 사안과 처음 시작해야 하는 간단한 시작 문서가 필요하다는 거야. 이는 프로젝트의 시작점을 알리는 문서이기도 하고 이후의 작업들을 생성하게 되는 첫 시작점이 되는거지.

**B. session-start hook에서 wip 비어 있고 하네스 초기화 안 된 상태 감지 → 안내 출력**
- CLAUDE.md의 `## 환경` 섹션 비어 있음 등을 플래그로 사용.
- 문서를 만들지 않고 메시지로만 처리.

**추천: A.** 하네스 철학(`docs/WIP/`에 파일 있으면 할 일 있다)과 일치. hook 로직 복잡도 감소.

---

## 이슈 3. 클론 후 환경 동기화 부재

### 현상
하네스 셋업된 프로젝트를 다른 머신에 클론 → 의존성/도구 미설치 상태로 돌리면 오류. 필요한 걸 하나씩 찾아서 깔아야 함.

### 원인
`h-setup.sh`는 **하네스 파일 복사**만 함. 프로젝트 의존성 설치는 사용자가 각 스택 기본 명령어(`npm i`, `pip install`, 등)로 해야 하는데, 하네스가 이걸 "클론 후 첫 실행" 흐름으로 통합해주지 않음.
//맞아. PRD문서등을 통해서 스펙이 정해지면서 여러가지 필요 프로그램들을 설치하게 되는데 이를 저장하고 다른 곳에서 클론햇을 경우 이를 감지하고 설치해 주는 프로세스가 필요해.
`CLAUDE.md`의 `## 환경` 섹션에 패키지 매니저/빌드 명령어가 적혀 있긴 하지만, 읽는 주체가 **Claude**이지 **사람/자동화**가 아님.

### 방향

**A. `harness-init` 재실행 모드로 "환경 체크"**
- 이미 초기화된 프로젝트에서 다시 실행 시 "재셋업 모드" 진입.
- `CLAUDE.md`의 환경 섹션 파싱 → 명시된 패키지 매니저로 의존성 설치 여부 확인 → 누락된 것 설치 제안.

**B. 별도 스킬 `harness-sync` (또는 `harness-bootstrap`)**
- 클론 직후 이걸 돌림.
- 역할: 하네스 파일 존재 확인 + 환경 의존성 설치 + 스크립트 권한 설정(`chmod +x .claude/scripts/*.sh`). //다만 맨 처음 설치한 프로젝트에서 이걸 다시 돌릴 이유는 없고, 다른 곳에서도 한번만 돌리면 되는거니까. 이 부분만 확실히 체크해주면 좋을듯.

**C. `h-setup.sh`에 `--sync` 플래그**
- 기존 파일이 있으면 복사 스킵 + 환경 명령어 실행.
- 가장 간단하지만 h-setup.sh가 "하네스 스타터 repo 안에" 있어야 함 → 클론한 프로젝트에선 접근 불가. **이 옵션은 부적합.**

**추천: B (별도 스킬 + 문서화) + A (보조).**
- 스킬 이름은 `harness-sync`. SKILL.md 1개로 충분.
- `CLAUDE.md`의 `## 환경` 섹션이 소스 오브 트루스가 되도록 파싱 포맷을 살짝 구조화(`패키지 매니저: pnpm` 같은 key-value).
- 추가로, 프로젝트 루트에 `bootstrap.sh` 같은 얇은 스크립트를 하네스가 셋업 시 자동 생성 → 클론한 사람이 그거 한 번 돌리면 끝.

### 고려사항
- OS별 차이(Windows bash vs POSIX). 현재 CLAUDE.md에 "Shell: bash (Unix 문법)" 규칙이 있으므로 bash 전제로 작성 가능.
- 설치 실패 시 에러 핸들링 — 추측으로 넘어가지 말고 사용자에게 보고.

---

## 이슈 4. 하네스 비대화 — 스킬/에이전트 선별

### 현상
기본으로 따라오는 것들 중 **이 프로젝트에 불필요한 것**이 섞여 있음. 관리 비용이 늘고, 매 세션 로드되는 컨텍스트가 커짐.

### 현재 스타터 포함 스킬
- check-existing
- coding-convention
- commit
- eval
- harness-init
- implementation
- naming-convention

### 분석 필요
각 스킬/스크립트/hook이 **모든 프로젝트에 필수**인지 vs **선택적**인지 구분:

| 항목 | 필수? | 메모 |
|------|------|------|
| harness-init | 필수 | 초기화 진입점 |
| commit | 필수 | 커밋 흐름 |
| implementation | 필수 | WIP 문서 흐름 |
| check-existing | 선택 | 중복 방지 — 소규모 프로젝트엔 과함 |
| coding-convention | 선택 | 린터 설정과 중복 가능 |
| naming-convention | 선택 | 규모 큰 프로젝트용 |
| eval | 선택 | 주기적 건강 체크 — light 프로젝트엔 불필요 |
| session-start hook | 선택 | RULES 주입 — 이슈 1과 연관 |
| pre-commit agent 검증 | 선택 | 커밋마다 에이전트 호출 → 비용 |

### 방향

**핵심 원칙: 기본은 최소, 필요 시 추가.**

1. **h-setup.sh에 프로파일 개념 도입**
   - `bash h-setup.sh --profile minimal|standard|full`
   - minimal: harness-init, commit, implementation, CLAUDE.md, rules만.
   - standard: + check-existing, naming-convention.
   - full: 전부.
   - 기본값은 `minimal`.

2. **harness-init에서 강도(light/strict)에 따라 스킬 선택**
   - light → minimal + 필요한 것 1~2개.
   - strict → 전부 + pre-commit 에이전트 검증.

3. **"필요하면 스타터 repo에서 가져오기" 흐름 공식화**
   - `harness-add <skill-name>` 유틸(스크립트 또는 스킬) — 나중에 필요해지면 추가.
   - 스타터 repo를 ref로 남겨두고 cherry-pick 식으로 가져옴.

**추천: 1번 + 3번.** 
2번은 프로파일과 충돌 가능성 있어 복잡해짐. 일단 프로파일로 컷 라인 만들고, 나중에 추가 매커니즘만 제공. //동의해.

### 영향
- 이슈 3(`harness-sync`)와 연결: sync 시 "이 프로파일로 셋업됨" 메타데이터가 필요할 수 있음.
- README 업데이트 필요.

---

## 작업 순서 제안

1. **이슈 1**: 간단. 위치 확정 후 즉시 수정. (사용자 확인 선행)
2. **이슈 2**: A안 채택 시 `h-setup.sh` 10줄 추가 수준.
3. **이슈 4**: 프로파일 개념 도입. h-setup.sh 구조 변경.
4. **이슈 3**: `harness-sync` 스킬 + `bootstrap.sh` 템플릿. 가장 큼.

각각 별도 WIP 문서로 분리할지, 이 문서에서 in-progress로 이어갈지는 사용자 결정.

## 결정 사항

### 이슈 1
- **확정**: `light` 강도가 기본으로 주입되는 것이 문제. 학습모드는 선택이어야 함.
- 구현: grep으로 "light" 기본값/자동추천 로직 전수조사 → 제거. `settings.json` 포함 전체 스캔.
- 옵션으로 남기지 않음. 필요하면 나중에 추가하면 됨.

### 이슈 2
- **확정**: A안. `h-setup.sh` 직후가 아니라 **harness-init 완료 시점**에 생성되는 "프로젝트 출범 문서".
- 역할: 대화로 결정된 CPS/스택/스펙을 담는 **첫 시작점 문서**. 이후 모든 작업 문서의 발원지.
- 기존 Step 8(도메인별 작업 문서)과는 별개. 순서: 출범 문서 → 첫 도메인 작업 문서.
- 파일명 후보: `project_kickoff.md` 또는 `project_start_{YYMMDD}.md`.

### 이슈 3
- **확정**: B안 (`harness-sync` 스킬).
- **핵심 제약**: 최초 셋업 머신에서는 재실행 불필요. 클론한 머신에서는 **단 한 번만** 실행.
- 구현: 상태 마커 파일(예: `.claude/.env_synced`) 또는 `docs/setup/env_lock.md` 같은 잠금 기록으로 "이미 동기화됨" 감지. 멱등성 + 스킵 로직 필수.
- `CLAUDE.md ## 환경` 섹션을 key-value로 구조화(`패키지 매니저: pnpm` 형식) → 파싱 용이.
- PRD 단계에서 결정된 의존성/도구 목록을 이 섹션에 누적 기록하는 규칙 추가.

### 이슈 4
- **확정**: 프로파일(1번) + `harness-add`(3번). 2번은 제외.
- 프로파일 기본값 `minimal`. harness-init이 필수 3개(harness-init, commit, implementation) + CLAUDE.md + rules만 복사.
- standard/full은 명시적 선택.
- 이슈 3과 연동: sync 시 프로파일 메타데이터 참조.

## 구현 결과 (2026-04-08)

### 이슈 1 ✅
- [commit/SKILL.md](.claude/skills/commit/SKILL.md): "기본은 light" 제거. CLAUDE.md `하네스 강도:` 읽어서 분기. 비어 있으면 실행 중단 + 사용자 질의.
- [CLAUDE.md](CLAUDE.md): `## 환경`에 `하네스 강도:` 라인 추가.
- [harness-init/SKILL.md](.claude/skills/harness-init/SKILL.md): "기본값 없음, 반드시 선택" 명시. Step 7 반영 표에 강도 추가.
- [README.md](README.md): 하네스 강도 섹션 업데이트, "학습용" 제거.

### 이슈 2 ✅
- [h-setup.sh](h-setup.sh): `docs/WIP/harness_init_pending.md` placeholder 자동 생성. session-start hook이 자연스럽게 유도.
- [harness-init/SKILL.md:148-200](.claude/skills/harness-init/SKILL.md#L148-L200): Step 7-1을 "프로젝트 출범 문서 생성"으로 구체화. `project_kickoff_YYMMDD.md` 템플릿 포함. 프로젝트가 존재하는 한 유지되는 **living document**.

### 이슈 3 ✅
- [.claude/skills/harness-sync/SKILL.md](.claude/skills/harness-sync/SKILL.md) 신규 스킬.
- 멱등성: `.claude/.env_synced` 마커로 "한 번만" 보장. 최초 머신 재실행 불필요.
- CLAUDE.md `## 환경` 파싱 → 패키지 매니저별 설치 명령 매핑 → 사용자 확인 후 실행.
- h-setup.sh가 `.gitignore`에 `.claude/.env_synced` 자동 추가.

### 이슈 4 ✅
- [h-setup.sh](h-setup.sh): `--profile minimal|standard|full` 도입. **기본 minimal**(harness-init/commit/implementation만).
- `--add <skill>` 옵션으로 후속 추가 가능.
- `.claude/harness.json` 메타데이터 생성(프로파일, 스킬 목록, 설치 시각).
- harness-sync가 이 메타데이터 참조해 무결성 검사.

### 공통 변경
- **폴더명 대문자화**: `docs/wip` → `docs/WIP` (git mv). 모든 참조 치환 완료.

## 남은 것
- 수동 테스트: 빈 디렉토리에서 `h-setup.sh --profile minimal` 실제 실행 확인.
- harness-sync 스킬의 실제 동작 검증 (클론 시뮬레이션).
- 커밋은 사용자 승인 후.

## 메모
- 이 문서는 개선 **계획 + 결과**이다. 커밋 시 `docs/harness/`로 이동(접두사 `harness_`).
