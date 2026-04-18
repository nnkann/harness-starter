# Security 규칙

"실수를 코드화" — 시크릿 노출은 사람이 아니라 도구로 막는다.

## 절대 금지

### 1. 시크릿 평문 하드코딩

다음을 코드에 **평문으로** 쓰지 마라. 파일 위치 불문, `tools/`, `scripts/`,
`dev-tools/` 같은 "일회성" 폴더도 예외 없음.

- Supabase: `sb_secret_*`, `service_role` 키
- AWS: access key, secret access key
- Stripe: `sk_live_*`, `sk_test_*`, `rk_live_*`
- GitHub/GitLab PAT: `ghp_*`, `glpat-*`
- Slack: `xox[baprs]-*`
- 모든 평문 비밀번호, admin 계정 비밀번호, DB 접속 문자열

대신: `process.env.FOO`로만 접근. `.env.local` 또는 시크릿 매니저에서 주입.
`.env`는 `.gitignore`에 있어야 한다.

### 2. service_role 키 클라이언트 노출

`createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)`는
**서버 전용 경로에서만** 호출한다. 아래 경로는 금지:

- `'use client'` 지시어가 있는 파일
- `components/` 하위 (client component)
- 브라우저에서 import되는 공유 모듈

권장: `@stagelink/database` (또는 프로젝트의 공용 DB 클라이언트 모듈)에서
생성된 싱글톤만 사용. 직접 `createClient(URL, SERVICE_ROLE)`를 부르지 마라.

### 3. admin/debug 엔드포인트 production 노출

`/api/admin/*`, `/api/debug/*`, `/api/_dev/*` 류 엔드포인트는
`NODE_ENV !== 'production'` 가드 또는 인증 미들웨어 없이 배포 금지.

## 방어 레이어

### 레이어 1: pre-commit hook (로컬)

gitleaks 또는 grep 기반 스캔을 pre-commit에 등록.
설치: `bash scripts/install-secret-scan-hook.sh` (본 레포 scripts/ 참조)

staged 파일에서 시크릿 패턴 발견 시 커밋 차단.

### 레이어 2: CI 스캔

PR 단계에서 `gitleaks detect --log-opts="-log <base>..<head>"` 실행.
노출 의심 건은 머지 차단.

### 레이어 3: eval --deep

주기적으로 `/eval --deep` 실행. Step 0 시크릿 스캔으로 working tree +
git history 전체를 스캔. 이미 들어간 시크릿이 있는지 확인.

### 레이어 4: 즉시 rotation 플레이북

시크릿이 git history에 한 번이라도 커밋되었다면:

1. **해당 키를 즉시 발급 기관에서 rotation** (Supabase 대시보드,
   AWS IAM, Stripe 대시보드 등). "history만 지우면 된다" 착각 금지.
2. git history 재작성: BFG Repo-Cleaner 또는 `git filter-repo`로
   해당 파일/패턴 제거 후 force push.
3. 팀 전체에 re-clone 지시 (로컬 reflog에 남아있을 수 있음).
4. `docs/incidents/`에 인시던트 문서 작성.

## 참고

- 2026-04-18 사고: `tools/dev-tools/` 4개 파일 + `tools/setup/` 2개 파일에
  service_role 키와 admin 비밀번호 평문 하드코딩, git history 영구 노출.
  eval --deep가 폴더를 "archive 후보"로만 분류하고 내부를 검사하지 않아
  검출 실패. 이 문서는 해당 사고 후 신설됨.
