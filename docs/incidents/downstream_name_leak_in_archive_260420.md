---
title: archived/promotion-log에 다운스트림 제품명 유출 — review 발견
domain: harness
tags: [contamination, review, archive, downstream-name]
symptom-keywords:
  - StageLink
  - stagelink
  - 다운스트림 제품명
  - archived 오염
  - promotion-log 복사
  - review verdict warn
relates-to:
  - path: incidents/matcher_false_block_and_readme_overwrite_260419.md
    rel: references
  - path: harness/generic_contamination_protection_260418.md
    rel: extends
  - path: decisions/code_ssot_audit_260420.md
    rel: references
status: completed
created: 2026-04-20
---

# archived/promotion-log에 다운스트림 제품명 유출

## 증상

2026-04-20 코드 SSOT 서더링 커밋(5ecbed0) 직전 review 에이전트가
`docs/archived/promotion-log-2026q2-early.md:367`에 다운스트림 제품명
(`StageLink`)이 포함됐다고 [주의] 보고. pre-commit push 전에 발견.
<!-- `StageLink` 인용은 사고 대상 특정용 1회 한정. 재발 방지 섹션 및
symptom-keywords 필드 외 본문에는 반복하지 않는다. -->
### 2025-04-20 보완 (review [주의] 반영)

- 본 문서 증상 섹션의 `StageLink` 인용에 근거 주석 첨부 (위 HTML 주석).
  근거: rules/docs.md "사고 인용이 불가피하면 주석으로 근거 명시".
- 재발 방지 #1의 "별도 과제로 분리" 추적 단서 추가: `docs/WIP/
  harness--review_whitelist_autodetect_260420.md`와 같은 범주(commit
  직전 리포 전체 스캔)로 후일 통합 검토.

추가 조사 결과 **4곳**에 같은 제품명이 남아 있었음:
- `.claude/rules/security.md:30` — DB 클라이언트 모듈 예시
- `docs/harness/harness_simplification_260419.md:260` — review 실측 예시
  (`Stagelink`/`ACME Corp`)
- `docs/incidents/matcher_false_block_and_readme_overwrite_260419.md:24, 133`
  — 실제 사고 인용

## 원인

### 1차 원인

하네스 초기 문서 작성 시 다운스트림 실제 사고·실측 사례를 그대로 인용.
`docs/incidents/`는 `symptom-keywords` 필드에 고유명사 허용 규정이 있으나
**본문에 제품명 노출은 별도 검토 없었음**.

### 2차 원인 (구조적)

- `.claude/rules/docs.md`의 오염 면제 규정: `docs/incidents/`만 명시. archived/·harness/ 등 다른 폴더 규정 없음.
- review 에이전트의 오염 검토는 **staged diff**만 대상. 기존에 이미 커밋된 파일은 점검 안 함.
- 본 리포(harness-starter)가 public인데 다운스트림 실명이 오래 남아 있었음.

## 해결

### 즉시 해소 (커밋 5ecbed0 amend)

4곳 모두 일반화 치환:
- `@stagelink/database` → `@<org>/database`
- `Stagelink`/`ACME Corp` → `<제품명>`/`<업체명>`
- `다운스트림(StageLink)` 2건 → `다운스트림 프로젝트`

`grep -rniE "stagelink"` 결과 working tree 0건 확인.

### git history 처리 판단 — 재작성 안 함

리포가 **public GitHub**이므로 이미 mirror·cache·fork에 노출된 상태.
`git filter-branch`·`filter-repo`로 history 재작성해도:
- 원격 force push + 다운스트림 re-clone 강제 부담
- GitHub 클라이언트 다운로드·web cache·타 fork에 남은 데이터는 제거 불가
- 실효성 낮음 대비 사용자 부담 높음

**결정**: 과거 커밋의 흔적은 그대로. 현재 파일에서만 제거 + 본 incident
기록으로 "이미 노출됐으나 이후 차단됨" 상태 명시.

## 재발 방지

### 1. review 오염 검토 대상 확장

**현재**: review는 staged diff만 점검.
**필요**: commit 직전 전체 리포에 대한 오염 스캔 (별도 과제로 분리).

### 2. eval --deep 오염 스캔 카테고리 추가

eval 스킬의 `--deep` 4관점(threat-analyst) 시나리오에 "다운스트림 실명
잔존" 추가 검토. 주기적 전수 점검 경로 확보.

### 3. rules/docs.md 오염 면제 규정 명확화

현재 "`docs/incidents/`는 symptom-keywords 면제" 규정이 "본문도 면제"로
오해될 여지 있음. 명확화 필요:
- **symptom-keywords 필드만** 제품명 허용
- **본문**에는 `<제품명>` 등 placeholder 권장
- incident 성격 인용이 불가피하면 주석으로 근거 명시

### 4. 향후 incident 작성 원칙

다운스트림 사고 인용 시 처음부터 placeholder 사용. 사용자·사고 특정 필요
시 `symptom-keywords`에만 실명 기록.

## 교훈

- **review는 방금 변경분만 본다** — 과거 커밋의 흔적은 별도 검증 체계
  필요. eval --deep이 그 역할.
- **public 리포의 흔적은 지울 수 없다** — 처음부터 오염 금지가 유일한
  안전장치. commit 전 review가 작동한 것은 성공 사례이지만, 더 일찍
  막았어야 했다.
- **symptom-keywords 면제의 좁은 해석** — 필드 자체만 면제이고 본문은
  아니다. 면제 규정 범위를 넓게 해석하지 마라.
