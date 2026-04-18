---
name: eval-deep-secret-scan-enforcement
description: eval --deep 시 archive 후보 폴더도 반드시 시크릿 스캔 + 파일 헤더 1회 검토를 실행
type: feedback
---

eval --deep 시 archive/legacy/cleanup/deprecated로 분류 후보 폴더도
Step 0(시크릿 스캔)과 Step 1(파일 헤더 20줄 훑기)을 반드시 실행한다.
"곧 삭제할 폴더"라는 분류만으로 내부 점검을 건너뛰지 마라.

**Why:** 2026-04-18 tools/dev-tools/ 4개 파일 + tools/setup/ 2개 파일에서
Supabase service_role 키와 admin 비밀번호가 평문 하드코딩된 채로 git history에
영구 노출되었다. eval --deep는 해당 폴더를 "archive 이동 후보"로만 분류하고
내부 파일을 한 번도 열어보지 않아 검출에 완전히 실패했다. archive 후보라는
이유로 오히려 더 위험한 코드가 방치되는 역설.

**How to apply:**
- `/eval --deep` 시작 시 Step 0(gitleaks 또는 grep 폴백으로 working tree +
  git history 스캔)을 선행 실행. 0건이어도 "0건"으로 명시. skip 금지.
- archive 후보 폴더는 삭제 안전성 체크리스트 4개(시크릿 0건 / 외부 참조 0건 /
  cron·CI 호출 0건 / 현행 문서 미참조) 모두 통과해야 "삭제 안전" 판정.
- 사고급 발견(service_role, admin password 등 즉시 rotation 필요) 시 즉시
  사용자에게 보고 + `docs/incidents/`에 인시던트 문서 작성 제안.
- 외부 공격자 페르소나(--deep의 4번째 관점)에서 git history 시크릿을
  내부 관점과 분리해서 재해석한다.
