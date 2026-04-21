---
title: eval --deep 보안 강화 패치 타 프로젝트 이식 가이드
domain: harness
tags: [eval, security, secret-scan, port]
status: completed
created: 2026-04-18
updated: 2026-04-18
---

# eval --deep 보안 강화 패치 이식 가이드

2026-04-18 harness-starter에서 적용한 `/eval --deep` 강화를
다른 하네스 프로젝트로 옮기는 절차.

## 이식 대상 파일

소스: `d:\Work\Claude.AI\harness-starter\`

1. `.claude/skills/eval/SKILL.md` — 전체 교체 (스코프 경계 + Step 0/1 + 4관점 포함)
2. `.claude/agents/review.md` — 전체 교체 (스코프 경계 + 3관점 추가)
3. `.claude/rules/security.md` — 신설
4. `.claude/memory/MEMORY.md` — 신설(또는 1줄 추가)
5. `.claude/memory/feedback_eval_secret_scan.md` — 신설
6. `scripts/install-secret-scan-hook.sh` — 신설

## 변경 요약

### eval --deep 강화
- `--deep`에 **Step 0 (시크릿 스캔)** 선행 단계 추가. gitleaks working tree + history, grep 폴백.
- `--deep`에 **Step 1 (archive 후보 폴더 강제 1회 점검)** 추가. 삭제 안전성 체크리스트 4항목.
- 2차 검증 **3관점 → 4관점** 확장. `외부 공격자` 페르소나 신설 (git history 시크릿, 클라이언트 번들 inline env, admin 엔드포인트, RLS bypass 등 6개 시나리오).
- Step 마무리 단계 추가. 사고급 발견 시 feedback 메모리 + rules/security.md + incidents 문서 자동 제안.
- description 갱신.

### review/eval 역할 분리 + review 3관점 추가
- eval 상단과 review 상단에 **스코프 경계** 명시 (diff vs 누적/전체).
- review에서 "코드 품질 3곳 이상 반복", "과도한 추상화" 등 **전체 코드 기반 판단 항목을 삭제** → eval 비용/과잉 관점으로 이관.
- review에 **3관점 독립 검증** 추가: 회귀 탐지자 / 계약 위반 / 스코프 이탈. 모두 diff에서 답이 나오는 질문만.
  - eval의 4관점과 의도적으로 구분: review는 "이 변경이 안전한가", eval은 "전체에서 놓치고 있는 것".
- 관점은 프롬프트로만 정의(A안). 서브에이전트 파일 분리 없음.

## 이식 절차

### 1. 파일 복사

대상 프로젝트 루트에서:

```bash
SRC=/d/Work/Claude.AI/harness-starter
DST=.  # 대상 프로젝트 루트

cp "$SRC/.claude/skills/eval/SKILL.md" "$DST/.claude/skills/eval/SKILL.md"
cp "$SRC/.claude/agents/review.md"    "$DST/.claude/agents/review.md"
cp "$SRC/.claude/rules/security.md"   "$DST/.claude/rules/security.md"
mkdir -p "$DST/.claude/memory" "$DST/scripts"
cp "$SRC/.claude/memory/MEMORY.md"                    "$DST/.claude/memory/MEMORY.md"
cp "$SRC/.claude/memory/feedback_eval_secret_scan.md" "$DST/.claude/memory/feedback_eval_secret_scan.md"
cp "$SRC/scripts/install-secret-scan-hook.sh"         "$DST/scripts/install-secret-scan-hook.sh"
chmod +x "$DST/scripts/install-secret-scan-hook.sh"
```

### 2. 충돌 확인

- 대상에 이미 `.claude/memory/MEMORY.md`가 있으면 덮어쓰지 말고,
  `- [eval-deep-secret-scan-enforcement](feedback_eval_secret_scan.md) — archive 후보도 시크릿 스캔 필수 (2026-04-18 사고 기반)` 한 줄만 추가.
- 대상에 이미 `.claude/rules/security.md`가 있으면 두 파일의 절 제목(절대 금지 / 방어 레이어 / 참고)을 기준으로 머지. "절대 금지" 3개 항목과 "방어 레이어 4개" 구조는 유지.
- 대상에 이미 `scripts/install-secret-scan-hook.sh`가 있으면 skip.

### 3. pre-commit hook 등록

```bash
bash scripts/install-secret-scan-hook.sh
```

gitleaks가 설치되어 있으면 `gitleaks protect --staged` 사용, 없으면 grep 폴백. `# >>> secret-scan (managed) >>>` 마커로 멱등.

주의: 하네스 스타터 레포의 경우 기존 pre-commit에 `HARNESS_DEV=1` 가드가 있으므로 스크립트가 그 아래에 섹션을 덧붙인다. 일반 프로젝트는 가드 없이 바로 시크릿 스캔만 남는다.

### 4. 검증

대상 프로젝트에서 즉시 1회 실행:

```
/eval --deep
```

실행 후 보고에 다음 4개 섹션이 모두 나와야 정상:

- `### 시크릿 스캔 (Step 0)`
- `### archive 후보 폴더 점검 (Step 1)`
- `### 외부 공격자` (4관점 중 하나)
- 기존 파괴자/트렌드/비용 관점

### 5. 사고 기록 갱신(옵션)

이식하는 프로젝트가 2026-04-18 사고의 당사자(tools/dev-tools 노출 프로젝트)라면,
`docs/incidents/`에 인시던트 문서를 write-doc 스킬로 생성하는 것을 권장.
sample title: `service_role 키 git history 노출 사고_260418`.

## 역참조

- 본 패치의 원본 변경: harness-starter `/eval --deep` 개선 (2026-04-18)
- 관련 사고: Supabase service_role 키 + admin 비밀번호 평문 하드코딩 + git history 노출
- 관련 문서: `.claude/rules/security.md`, `.claude/memory/feedback_eval_secret_scan.md`
