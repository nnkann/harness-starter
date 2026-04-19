# 범용성 오염 방지

harness-starter는 **범용 하네스 템플릿**이다. 다운스트림 프로젝트에 전파
되는 기반 코드/문서이므로 다운스트림 고유명사(제품명·업체명·엔티티 ID·
도메인 특화 용어)가 박히면 다른 프로젝트에 전파 시 오염된다.

## 활성 조건

이 규칙은 **`is_starter: true`인 리포에서만 적용된다.** 다운스트림
프로젝트에는 적용 안 됨. `.claude/HARNESS.json`의 `is_starter` 필드로
판정.

## 허용어 리스트 (대문자 시작 단어)

다음 단어는 고유명사 검출에서 제외 — 하네스 도메인의 정당한 용어.

### Claude·Anthropic 생태계
```
Claude  Anthropic  CLAUDE  HARNESS  README  CHANGELOG
Bash  Read  Glob  Grep  Edit  Write  Agent  Task  TodoWrite
PreToolUse  PostToolUse  SessionStart  SessionEnd  Stop  PostCompact
UserPromptSubmit  PreCompact  Notification  SubagentStop
Context7  WebSearch  WebFetch  MCP  SDK
Opus  Sonnet  Haiku
```

### 일반 기술 용어
```
TODO  FIXME  HACK  NOTE  XXX  BUG  WIP
JSON  YAML  XML  HTML  CSS  URL  URI  API  CLI  GUI  IDE  CI  CD
HTTP  HTTPS  TCP  UDP  TLS  SSL  DNS  REST  GraphQL  RPC  SQL  NoSQL
OAuth  JWT  CSRF  XSS  CORS  CSP  CVE  OWASP
Git  GitHub  GitLab  Docker  Kubernetes  Linux  Windows  macOS  Ubuntu
Node  Python  Java  Go  Rust  Ruby  PHP  TypeScript  JavaScript
React  Vue  Angular  Svelte  Next  Nuxt  Express  Django  Flask  Rails
PostgreSQL  MySQL  MongoDB  Redis  SQLite
```

### 하네스 자체 용어 (영문)
```
Stage  Signal  Skill  Hook  Matcher  Tool  Subagent  Permission
Workflow  Pipeline  Manifest  Lock  Migration  Frontmatter
Step  Part  SKILL  INDEX  LLM  ALLOWLIST  YYMMDD
```

### 한글 허용어
```
일반  사용자  하네스  스킬  에이전트  훅  매처  도구  서브에이전트
권한  워크플로  파이프라인  매니페스트  락  마이그레이션  프론트매터
도메인  메타  코드  문서  파일  폴더  경로  변수  함수  클래스  모듈
프로젝트  레포  리포  세션  메시지  명령  옵션  플래그  버전
검토  통합  적용  사용  설정  실행  처리  관리  수정  변경  추가  제거
생성  삭제  확인  검증  필요  가능  불가능  상태  결과  입력  출력
호출  응답  요청  단계  방법  기준  구조  설계  구현  테스트  배포
```

## 검출 패턴

`pre-commit-check.sh`가 staged diff에서 다음 패턴을 추출:

```bash
git diff --cached -U0 | grep -E '^\+' | \
  grep -oE '[A-Z][a-zA-Z0-9]{2,}|[가-힣]{2,}' | \
  sort -u
```

- 대문자 시작 + 3자 이상 영문/숫자
- 또는 한글 2자 이상

위 허용어에 없으면 의심 고유명사로 경고.

## 행동

- **경고 수준** (현재): 의심 단어 출력, 차단 안 함. 사용자가 판단.
- **차단 격상** (후속): 같은 파일에 의심 단어가 연속 커밋(2회 이상)
  추가되면 차단. 구현은 staging.md의 S10 연속수정과 결합.

## 회피 패턴 (정당한 사용)

다운스트림 프로젝트 이름이 진짜 필요한 경우:
- **placeholder 우선**: `<제품명>`, `<업체명>`, `<DOMAIN>` 같이 표기
- **실명이 필수면 근거 명시**: 문서에 "이 이름은 X 때문에 그대로 유지"
  주석 추가
- **incidents/에 사례로 박는 경우**는 검출 면제 — 사고는 실제 이름이
  검색 키여야 의미 있음

## 알려진 한계

- **오탐**: 사람 이름·일반 영문 단어가 잡힐 수 있음. 허용어 추가로 보정.
- **미탐**: 소문자로 시작하는 고유명사(`stagelink`, `acme` 등)는 못 잡음.
  현재 패턴은 대문자 시작만 검출. 후속 정밀화에서 케이스 추가.
- **면제 파일** (검출에서 제외 — git pathspec exclude):
  - `docs/incidents/**` (사고 기록은 실명이 검색 키)
  - `docs/harness/promotion-log.md` (이력 표 본문에 다운스트림·고유명사 같은
    메타 단어 자주 등장)
  - `.claude/HARNESS.json` (스키마 단어가 잡힘)
  - `.claude/scripts/**`, `.claude/hooks/**` (셸 변수명·heredoc 마커 오탐)
  - `.claude/rules/contamination.md` (허용어 리스트 자체가 잡힘)

## 참조

- `pre-commit-check.sh`: 검출 로직
- `.claude/HARNESS.json`: `is_starter` 활성 조건
- `docs/incidents/`: 과거 오염 사례 (있으면)
