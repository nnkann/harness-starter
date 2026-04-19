# Docs 규칙

## 폴더 구조

```
docs/
├── INDEX.md        ← 도메인 목록 + 진입 포인터 (경량)
├── clusters/       ← 도메인별 상세 인덱스
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

## INDEX.md + clusters/

```
탐색: INDEX.md (어떤 도메인?) → clusters/해당.md (어떤 문서?) → 본문 Read
```

- INDEX.md: 도메인 목록 + 진입 포인터 (경량, 고정 크기)
- clusters/{domain}.md: 도메인별 문서 목록 + 관계 맵
- WIP는 INDEX/clusters 미포함 (완료 후 이동 시 추가)
- commit 스킬이 문서 이동 시 cluster + INDEX 갱신

## 문서 탐색

탐색 절차·"없다" 3단계·escalation은 `docs/guides/doc-search-protocol_260420.md` 참조.

핵심: IDE 컨텍스트는 힌트일 뿐, 사용자 원문 고유명사로 Glob → 제목/태그 grep → 본문 grep
3단계 모두 거친 뒤에만 "없다" 결론.

## 문서 생성

- 코드 작업과 함께 → implementation 스킬이 docs/WIP/에 계획 문서 생성
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
