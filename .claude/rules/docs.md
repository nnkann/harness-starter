# Docs 규칙

## 폴더 구조

```
docs/
├── clusters/       ← 도메인별 인덱스 (SSOT — 진입점)
├── WIP/            ← 작업 중. 파일 있으면 할 일 있다.
├── decisions/      ← "왜 X를 선택했나?"
├── guides/         ← "X를 어떻게 하나?"
├── incidents/      ← "X가 왜 깨졌고 어떻게 고쳤나?"
├── harness/        ← 하네스 자체 이력 (승격 로그 등)
└── archived/       ← 중단·대체된 문서
```

폴더 판단: "이 문서를 누가 왜 다시 열까?"
- 새 결정 근거 → `decisions/`
- 같은 작업 방법 → `guides/`
- 비슷한 문제 원인 → `incidents/`
- 하네스 자체 변경 이력 → `harness/`

## 프론트매터

```yaml
---
title: 문서 제목                # 필수
domain: harness                 # 필수. naming.md 도메인 목록에서 선택
tags: [keyword1, keyword2]      # 선택. 최대 5개
relates-to:                     # 선택
  - path: decisions/other.md
    rel: extends                # extends|caused-by|implements|supersedes|references|conflicts-with
status: completed               # 필수. pending|in-progress|completed|abandoned|sample
created: 2026-04-16             # 필수
updated: 2026-04-16             # 선택
---
```

- **domain**: naming.md "도메인 목록 > 확정"이 SSOT
- **rel**: 6종만. 새 타입은 스펙 문서 추가 후 사용
- **폴더 = 성격, domain = 의미** (이중 분류)

### incidents/ 전용

```yaml
symptom-keywords:     # 필수. 증상 유발 고유명사·식별자
  - <제품/업체/기능명>
  - <엔티티-ID>
```

tags는 기술 분류, **재발 시 사용자가 입에 올릴 단어**는 symptom-keywords.
미래의 Claude가 "전에 이런 적 있었나?"의 grep 첫 타겟. write-doc 스킬이
incident 생성 시 빈 필드면 재질의.

**오염 면제 범위 (좁게 해석)**:
- `symptom-keywords` **필드 자체만** 다운스트림 고유명사 허용 (검색 키
  목적).
- **본문에는 placeholder 사용**: `<제품명>`·`<업체명>`·`<엔티티-ID>` 등.
  사고 인용이 불가피하면 주석으로 근거 명시.
- incident 외 폴더(`archived/`·`harness/`·`guides/`·`decisions/`)는 **면제
  없음**. 다운스트림 실명 노출 시 review가 [주의] 이상으로 지적.
- 본 리포가 public이면 history 재작성 불가하므로 처음부터 placeholder
  필수. 관련 incident: `docs/incidents/downstream_name_leak_in_archive_260420.md`.

## clusters/

```
탐색: clusters/{domain}.md (문서 목록 + 관계 맵) → 본문 Read
```

- clusters/{domain}.md: 도메인별 문서 목록 + 관계 맵. **진입점 SSOT**.
- 도메인 목록은 `.claude/rules/naming.md`의 "도메인 목록"이 유일한 SSOT.
  (INDEX.md는 2026-04-20 폐기 — 도메인 2개 구조에서 진입 포인터 역할이
  무의미해 관리 드리프트만 발생. 자세한 근거는 `docs/harness/index_md_removal_260420.md`)
- WIP는 clusters 미포함 (완료 후 이동 시 추가)
- commit 스킬이 문서 이동 시 clusters만 갱신

## 문서 탐색

탐색 절차·"없다" 3단계·escalation은 `docs/guides/doc-search-protocol_260420.md` 참조.

핵심: IDE 컨텍스트는 힌트일 뿐, 사용자 원문 고유명사로 Glob → 제목/태그 grep → 본문 grep
3단계 모두 거친 뒤에만 "없다" 결론.

## SSOT 우선 + 분리 판단 (단순 지표 금지)

새 문서·WIP 생성 전에 **항상** 두 질문을 거친다:

1. **이 결정·계획이 기록될 SSOT가 이미 있는가?**
   - 있으면 거기를 갱신 (필요 시 `status: completed` → `in-progress` 재개)
   - 없으면 새로 만들되, 다른 문서에 같은 내용이 생기지 않도록
2. **분리가 정말 필요한가? (판단)**

**분리해야 할 때** (판단 기준 — 지표 아님):
- 결정이 여러 단계로 나뉘어 별도 실행·검증 필요
- 실행 결과가 원래 결정을 뒤집을 수 있는 실측 데이터 생성 (예: advisor
  판정으로 계획 반전)
- 결정 자체가 향후 독립 참조 가치 (ADR급)
- 작업 흐름 중단·재개를 위해 진행 상태 보존 필요

**분리하지 말아야 할 때**:
- 상류 SSOT에 범위·결정 다 있고 **실행만** 남은 경우
- 중간 결과가 상류 문서 갱신으로 흡수 가능한 경우
- 본 작업이 다른 커밋과 함께 묶이는 게 맥락상 자연스러운 경우

**단순 지표로 판단 금지**: "파일 3개 이상이면 WIP 생성" 같은 기계적 규칙
금지. 규모·도메인 flag 만으로 분기하지 말 것.

**완료된 문서 재개**: SSOT를 다시 쓰려면 `docs/X/` → `docs/WIP/` 되돌린 뒤
`status: completed` → `in-progress`. 같은 내용을 새 WIP로 복제하지 마라.

## 문서 생성

- 코드 작업과 함께 → implementation 스킬이 docs/WIP/에 계획 문서 생성
  (단, 위 SSOT 우선·분리 판단 선행)
- 문서만 단독 → write-doc 스킬이 폴더·프론트매터·파일명 강제
- WIP 파일명: `{대상폴더}--{작업내용}_{YYMMDD}.md` (`--`는 라우팅 태그)
- 대상폴더: decisions, guides, incidents, harness 중 하나
- 프론트매터 필수. `relates-to`는 작업 중 비어도 됨

## 문서 이동

- 완료/중단 문서는 docs/WIP/에 남기지 않음
- 이동은 commit 스킬 처리. 수동 이동 금지
- 이동 시 `{대상폴더}--` 접두사 제거 → 최종 `{작업내용}_{YYMMDD}.md`
- 위 구조 폴더만 허용. **새 하위 폴더 만들지 마라**
- 이동 시: status → completed/abandoned, updated 갱신, clusters/{domain}.md에 추가

### 완료 문서 재개 (역방향 이동)

completed로 이동된 SSOT 문서에 후속 실행 결과를 기록해야 하면:
1. `git mv docs/{폴더}/X_{YYMMDD}.md docs/WIP/{원래접두사}--X_{YYMMDD}.md`
2. 프론트매터 `status: completed` → `in-progress`
3. 작업 완료 시 다시 completed 전환 + 원래 폴더로 이동 (commit 스킬)

이 경로를 쓰는 이유: 같은 내용을 새 WIP로 복제하면 SSOT가 둘이 됨.
한 문서가 살아 있다가 완료되는 수명주기를 유지.

## completed 전환 차단

본문에 다음 키워드 남아 있으면 차단 (대소문자 무관):
`TODO`, `FIXME`, `후속`, `미결`, `미결정`, `추후`, `나중에`, `별도로`

차단 시 선택:
1. 미결 항목을 별도 WIP로 분리 (권장). 원본 completed 이동, 새 WIP는 `rel: caused-by` 연결
2. 해결 완료라면 키워드 제거 후 재시도

commit 스킬이 검사. 수동 completed 전환 금지.

## 금지

- docs/ 외 위치 문서 생성 (README/CHANGELOG 등 루트 표준 파일 제외)
- docs/ 하위 임의 폴더 생성 (위 구조만 허용)
- 새 폴더가 필요하면 사용자에게 먼저 확인
- naming.md에 없는 domain 사용
