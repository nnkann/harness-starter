# Security 규칙

"실수를 코드화" — 시크릿 노출은 사람이 아니라 도구로 막는다.

## 절대 금지

### 1. 시크릿 평문 하드코딩

위치 불문 (`tools/`, `scripts/`, `dev-tools/` 같은 "일회성" 폴더도 예외 없음):

- Supabase: `sb_secret_*`, `service_role` 키
- AWS: access key, secret access key
- Stripe: `sk_live_*`, `sk_test_*`, `rk_live_*`
- GitHub/GitLab PAT: `ghp_*`, `glpat-*`
- Slack: `xox[baprs]-*`
- 평문 비밀번호, admin 비밀번호, DB 접속 문자열

대신: `process.env.FOO`로만 접근. `.env.local` 또는 시크릿 매니저에서 주입.
`.env`는 `.gitignore`에 있어야 함.

### 2. service_role 키 클라이언트 노출

`createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)`는 **서버 전용 경로
에서만**. 금지 경로:

- `'use client'` 지시어 파일
- `components/` 하위 (client component)
- 브라우저에서 import되는 공유 모듈

권장: 공용 DB 클라이언트 모듈(`@<org>/database` 등)의 싱글톤만 사용.
직접 `createClient(URL, SERVICE_ROLE)` 호출 금지.

### 3. admin/debug 엔드포인트 production 노출

`/api/admin/*`, `/api/debug/*`, `/api/_dev/*`는 `NODE_ENV !== 'production'`
가드 또는 인증 미들웨어 없이 배포 금지.

## 방어 레이어

4단(로컬 hook → CI → eval --deep → rotation 플레이북). 상세·rotation 절차·
2026-04-18 사고 참고는 `docs/decisions/hn_rules_metadata.md` 참조.

요약:
- 로컬 pre-commit hook (`scripts/install-starter-hooks.sh`)
- CI gitleaks
- 주기적 `/eval --deep`
- 노출 시 즉시 rotation → history 재작성 → re-clone → incident 문서
