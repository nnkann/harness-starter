---
name: write-doc
description: >-
  코드 작업 없이 문서만 단독 생성할 때 사용. 폴더 판단, 프론트매터 검증, WIP 파일명 규칙을 강제한다.
  TRIGGER when: "기록해줘", "문서 만들어", "결정 남겨", "가이드 작성해", "인시던트 정리해",
  "회고 작성" 등 문서 생성 의도가 있는 요청.
  SKIP: 코드 구현과 함께 문서가 만들어지는 경우(→ implementation), 기존 문서 수정, 탐색/검색.
---

# write-doc

문서 단독 생성 흐름. 프론트매터·파일명·폴더 라우팅 강제.

## implementation 스킬과의 관계

| 상황 | 담당 |
|------|------|
| 코드 부산물 문서 | implementation Step 3 |
| 문서 자체가 목적 | **write-doc** |
| 문서 이동 (WIP → 최종) | commit |
| 문서 탐색 | doc-finder |

## Step 1. 대상 폴더 + domain·abbr 결정

| 핵심 질문 | 폴더 |
|----------|------|
| "왜 이렇게 했나?" | decisions/ |
| "어떻게 하나?" | guides/ |
| "무엇이 왜 깨졌나?" | incidents/ |
| 하네스 자체 변경 이력 | harness/ |
| wave case 박제 | cps/ |

판단 모호하면 사용자에게 묻는다. 추측 금지.

**domain·abbr** — `.claude/rules/naming.md` SSOT:
- "도메인 목록 > 확정"에서 domain 결정
- "도메인 약어" 표에서 abbr 조회
- 새 domain 필요하면 abbr 함께 등록 (2~3자 소문자, 충돌 없게)
- 전역 마스터 문서는 abbr 생략 (`{slug}.md`)

## Step 2. SSOT 선행 탐색 (강제)

`.claude/rules/docs.md` "## SSOT 우선 + 분리 판단" SSOT 적용:

1. **3단계 탐색** — cluster 스캔 → 키워드 grep → 후보 본문 Read
2. **두 질문** — SSOT 존재 / 분리 필요성
3. **실패 모드 5개** 중 하나라도 해당하면 재실행

| 결과 | 경로 |
|------|------|
| hit 0건 | Step 3 (새 WIP) |
| hit + 갱신 적절 (WIP) | 그 파일 Edit. Step 3 스킵 |
| hit + 갱신 적절 (completed) | `docs_ops.py reopen <경로>` 후 갱신 |
| hit + 분리 근거 충족 | Step 3 + `relates-to` 기록 |

**동격 선택지 금지** ("새로 만들까요, 갱신할까요?"). 기본은 갱신. 분리 근거
명확하면 분리.

## Step 3. WIP 생성

**파일명** (`.claude/rules/naming.md` SSOT): `{abbr}_{slug}.md`

- abbr: Step 1 조회한 약어
- slug: snake_case, 30자 이내
- 라우팅 태그 `{폴더}--` 폐기 (§S-4 73% 삭감). frontmatter `domain` + 폴더는
  commit 스킬이 결정
- **날짜 suffix 전면 금지** — 같은 주제 = 같은 파일 갱신. 사용자 명시 요구도 거부

**frontmatter** (`docs.md` SSOT):
```yaml
---
title: ...
domain: ...           # naming.md 도메인 목록
problem: [P3]         # CPS 인용 번호만
s: [S2, S6]
tags: []              # 영문 소문자+하이픈+숫자 (naming.md tag 정책)
status: in-progress
created: YYYY-MM-DD
---
```

**incidents/ 전용 필수 추가 필드**:
```yaml
symptom-keywords:
  - <증상 유발 고유명사·식별자>
```

질의 예: "이 사고를 미래에 누가 다시 검색할 때 어떤 단어를 입에 올릴까요?"
비우고 넘어가지 마라.

**본문 — 자유 형식**: 폴더별 6종 템플릿 폐기 (§S-4 73% 삭감). 사용자 의도에
맞춰 자유 작성. 자기완결성 1원칙: 다른 문서 안 읽어도 본문만으로 의미 전달.

## Step 4. 작성 + 완료

- 사용자가 내용 제공하면 정리
- "알아서 정리" 요청 시 세션 맥락에서 수집
- relates-to 명확해지면 frontmatter 추가
- 충분하면 `status: completed`

이후 `/commit`이 자동:
- WIP에서 대상 폴더로 이동
- cluster 갱신 (파일명 abbr 자동 매핑 + tag 백링크)

## 규칙

- `docs.md`·`naming.md` 모든 규칙 준수
- docs/ 외 위치 문서 생성 금지
- docs/ 하위 새 폴더 금지
- naming.md에 없는 domain·abbr 금지
- 프론트매터 필수 필드 누락 시 생성 금지

