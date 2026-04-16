# harness-starter

AI 코딩 에이전트를 위한 하네스(Harness) 템플릿. Claude Code 전용.

> "에이전트가 실수할 때마다, 그 실수가 다시는 일어나지 않도록 엔지니어링 솔루션을 만드는 것" — Mitchell Hashimoto

## 빠른 시작

```bash
# 프로젝트에 하네스 설치
cd my-project
bash /path/to/harness-starter/h-setup.sh .

# Claude Code 실행 → harness-init으로 스택 결정
```

h-setup.sh는 멱등성 보장. 이미 있는 파일은 건드리지 않는다.

```bash
# 기존 프로젝트의 하네스를 최신 버전으로 업그레이드
bash /path/to/harness-starter/h-setup.sh --upgrade /path/to/my-project

# Claude Code에서 충돌 파일 병합
# → /harness-upgrade
```

## 구조

```
CLAUDE.md                        에이전트 루트 인스트럭션 (≤30줄)
.claude/
├── settings.json                hooks 정의
├── HARNESS_VERSION              하네스 버전 (semver)
├── rules/                       자동 로드 규칙 (5개)
│   ├── self-verify.md           [상시] 작업 중 자기 검증
│   ├── coding.md                [상시] 코딩 컨벤션 (플레이스홀더)
│   ├── naming.md                [paths] 네이밍 규칙 (플레이스홀더)
│   ├── docs.md                  [paths] 문서 구조 규칙
│   └── memory.md                [상시] 메모리 활용 규칙
├── skills/                      온디맨드 스킬 (10개)
│   ├── harness-init/            프로젝트 초기화 (CPS + 스택 결정)
│   ├── harness-sync/            클론 후 환경 동기화
│   ├── harness-upgrade/         하네스 버전 업그레이드 + 병합
│   ├── implementation/          작업 문서 라이프사이클
│   ├── commit/                  커밋 + Review (light/strict)
│   ├── eval/                    건강 검진 (--quick/--harness/--surface/--deep)
│   ├── advisor/                 멀티 에이전트 3관점 검증
│   ├── check-existing/          기존 코드 중복 확인
│   ├── naming-convention/       네이밍 규칙 설정
│   └── coding-convention/       코딩 컨벤션 설정
└── scripts/                     hook 스크립트 (6개)
docs/
├── WIP/                         진행 중 (파일 있으면 할 일 있다)
├── setup/                       초기 결정
├── history/                     수정 이력
├── development/                 구현 가이드
├── harness/                     하네스 변경 이력
└── archived/                    종료된 작업
```

## 워크플로우

하네스를 설치한 프로젝트에서 작업하는 흐름:

```
0a. h-setup.sh         하네스 파일 복사. 프로파일 선택(minimal/standard/full).
                     완료 시 docs/WIP/harness_init_pending.md 생성.

0b. /harness-sync    (클론한 머신에서만, 한 번만) 의존성 설치 + 권한 설정.
                     최초 셋업 머신에선 불필요.

1. /harness-init     PRD/아이디어 입력 → CPS 정리, 스택/강도 결정, 하네스 빈 칸 채움.
                     완료 시 docs/WIP/project_kickoff_YYMMDD.md + 첫 작업 문서 생성.

2. docs/WIP/ 확인    파일이 있으면 할 일이 있다.

3. /implementation   작업 시작 전 계획 문서 생성. CPS와 대조.
                     status: pending → in-progress.

4. 구현              코드 작성. 결정 사항과 메모를 계획 문서에 기록.

5. /commit           작업 잔여물 정리, 완료 문서 이동, 커밋+푸시.

6. 반복              docs/WIP/에 다음 작업이 남아있으면 3번으로.

--- 업그레이드 (하네스 스타터 새 버전 출시 시) ---

7. h-setup.sh --upgrade  새 파일 복사 + 변경 파일 .upgrade/에 스테이징.
8. /harness-upgrade    스테이징된 파일을 대화형으로 병합. 사용자 커스터마이징 보존.
```

**docs/WIP/가 비어있으면 할 일이 없다는 뜻이다.**

상태값: `pending` → `in-progress` → `completed` (커밋 시 이동) / `abandoned` (archived로 이동)

## CPS (Context / Problem / Solution)

모든 프로젝트 결정의 출발점. `harness-init`이 대화를 통해 구조화한다.

- **Context**: 배경, 제약, 프로젝트 중요도 → 하네스 강도 결정
- **Problem**: 해결해야 할 핵심 문제 1~3개
- **Solution**: 각 Problem에 대한 대응 방안 + 강제력 설계

CPS 문서는 `docs/guides/project_kickoff_YYMMDD.md`에 저장된다. `docs/guides/project_kickoff_sample.md`에 예제가 포함되어 있으며, `harness-init` 실행 시 실제 내용으로 대체된다.

`/implementation` 스킬은 작업 시작 전 CPS와 대조하여 방향성을 검증한다. init을 아직 실행하지 않았으면 안내 메시지를 표시한다.

## 핵심 원칙

- **CLAUDE.md는 소원 목록이다. Hooks는 법이다. Linter는 물리 법칙이다.**
- 린터가 잡을 수 있는 건 CLAUDE.md에 쓰지 않는다.
- rules/에는 4개까지만. 나머지는 skills/에 온디맨드.
- 하네스는 뜯어내기 쉬워야 한다 (rippable harness).

## 하네스 강도

`harness-init`에서 **사용자가 선택**한다. 기본값 없음. CLAUDE.md `## 환경`의 `하네스 강도:`에 기록.

| 강도 | 기준 | 적용 |
|------|------|------|
| light | 프로토타입, 소규모, 단기 | commit light. 리뷰 최소. |
| strict | 장기 유지보수, 사용자 다수 | commit strict. 전체 리뷰. |

강도가 비어 있으면 `/commit`은 실행을 멈추고 사용자에게 선택을 요청한다.

## 다른 도구

현재 Claude Code 전용. rules/의 마크다운 내용은 Cursor(`.cursor/rules/*.mdc`), Windsurf(`.windsurf/rules/*.md`) 등으로 포맷 변환하면 재사용 가능. skills/와 hooks는 Claude Code 고유 기능.

## 참고

- [Mitchell Hashimoto — My AI Adoption Journey](https://mitchellh.com/writing/my-ai-adoption-journey)
- [OpenAI — Harness Engineering](https://openai.com/index/harness-engineering/)
- [Birgitta Böckeler — Harness Engineering](https://martinfowler.com/articles/harness-engineering.html)

MIT License
