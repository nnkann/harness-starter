# harness-starter

AI 코딩 에이전트를 위한 하네스(Harness) 템플릿. Claude Code 전용.

> "에이전트가 실수할 때마다, 그 실수가 다시는 일어나지 않도록 엔지니어링 솔루션을 만드는 것" — Mitchell Hashimoto

## 빠른 시작

```bash
# 프로젝트에 하네스 설치
cd my-project
bash /path/to/harness-starter/setup.sh .

# Claude Code 실행 → harness-init으로 스택 결정
```

setup.sh는 멱등성 보장. 이미 있는 파일은 건드리지 않는다.

## 구조

```
CLAUDE.md                        에이전트 루트 인스트럭션 (≤30줄)
.claude/
├── settings.json                hooks 정의
├── rules/                       자동 로드 규칙
│   ├── self-verify.md           [상시] 작업 중 자기 검증
│   ├── coding.md                [상시] 코딩 컨벤션 (플레이스홀더)
│   ├── naming.md                [paths] 네이밍 규칙 (플레이스홀더)
│   └── docs.md                  [paths] 문서 구조 규칙
├── skills/                      온디맨드 스킬 (7개)
│   ├── harness-init/            프로젝트 초기화 (CPS + 스택 결정)
│   ├── implementation/          작업 문서 라이프사이클
│   ├── commit/                  커밋 + Review (light/strict)
│   ├── eval/                    건강 검진 (3모드 + --deep)
│   ├── check-existing/          기존 코드 중복 확인
│   ├── naming-convention/       네이밍 규칙 설정
│   └── coding-convention/       코딩 컨벤션 설정
└── scripts/                     hook 스크립트 (4개)
docs/
├── wip/                         진행 중 (파일 있으면 할 일 있다)
├── setup/                       초기 결정
├── history/                     수정 이력
├── development/                 구현 가이드
├── harness/                     하네스 변경 이력
└── archived/                    종료된 작업
```

## 핵심 원칙

- **CLAUDE.md는 소원 목록이다. Hooks는 법이다. Linter는 물리 법칙이다.**
- 린터가 잡을 수 있는 건 CLAUDE.md에 쓰지 않는다.
- rules/에는 4개까지만. 나머지는 skills/에 온디맨드.
- 하네스는 뜯어내기 쉬워야 한다 (rippable harness).

## 하네스 강도

| 강도 | 기준 | 적용 |
|------|------|------|
| light | 프로토타입, 학습용, 소규모 | commit light. 리뷰 최소. |
| strict | 장기 유지보수, 사용자 다수 | commit --strict. 전체 리뷰. |

## 다른 도구

현재 Claude Code 전용. rules/의 마크다운 내용은 Cursor(`.cursor/rules/*.mdc`), Windsurf(`.windsurf/rules/*.md`) 등으로 포맷 변환하면 재사용 가능. skills/와 hooks는 Claude Code 고유 기능.

## 참고

- [Mitchell Hashimoto — My AI Adoption Journey](https://mitchellh.com/writing/my-ai-adoption-journey)
- [OpenAI — Harness Engineering](https://openai.com/index/harness-engineering/)
- [Birgitta Böckeler — Harness Engineering](https://martinfowler.com/articles/harness-engineering.html)

MIT License
