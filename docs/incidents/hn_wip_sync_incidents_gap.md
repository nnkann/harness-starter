---
title: wip-sync incidents WIP 자동 완료 미동작 — 체크리스트 없는 문서 abbr 매칭 누락
domain: harness
tags: [wip-sync, docs-ops, commit, incidents]
relates-to:
  - path: harness/hn_wip_completion_gap.md
    rel: caused-by
status: completed
created: 2026-04-27
updated: 2026-04-27
---

# wip-sync incidents WIP 자동 완료 미동작

## 사전 준비

- 읽을 문서: docs/harness/hn_wip_completion_gap.md (completed — B 해결책 배경)
- 이전 산출물: docs_ops.py wip-sync 구현 (2026-04-25, hn_wip_completion_gap B)

## 목표

`docs_ops.py wip-sync`에 abbr 기반 보조 매칭 경로를 추가해,
체크리스트가 없는 incidents WIP도 staged 파일로부터 자동 completed 이동까지 연결한다.

## 작업 목록

### 1. naming.md 경로→도메인 매핑 파싱 함수 추가
> kind: feature

**영향 파일**: `.claude/scripts/docs_ops.py`

**내용**: `extract_path_domain_map()` 함수. naming.md "경로 → 도메인 매핑" 섹션에서
`{경로패턴} → {도메인}` 매핑을 파싱해 반환. 섹션이 없으면 빈 dict.

**Acceptance Criteria**:
- [ ] `extract_path_domain_map()` 존재
- [ ] naming.md 섹션 없으면 `{}` 반환 (에러 없음)

### 2. abbr 기반 보조 매칭 경로 추가
> kind: bug

**영향 파일**: `.claude/scripts/docs_ops.py` (`cmd_wip_sync`)

**설계**:
```
staged 파일 경로
  → extract_path_domain_map() 으로 도메인 추출
  → extract_abbrs() + 도메인→abbr 역매핑으로 abbr 획득
  → WIP 파일명에서 detect_abbr() 결과와 대조
  → 일치하면 "abbr 매칭 WIP"로 표시
```

abbr 매칭된 WIP 처리:
- 체크리스트 항목이 1개라도 있으면: 기존 로직(✅ 마킹) 그대로
- 체크리스트 항목이 0개이면: 직접 move 시도 (✅ 마킹 없이)
- 같은 abbr WIP가 복수이면: stderr 경고만, 자동 이동 skip (사용자 확인 필요)

**Acceptance Criteria**:
- [ ] `python3 docs_ops.py wip-sync src/services/fooService.ts` 가 `foo` abbr WIP를 매칭
- [ ] 체크리스트 없는 WIP가 abbr 매칭 → 차단 키워드 없음 → 자동 이동
- [ ] 같은 abbr WIP 복수이면 stderr 경고 + skip (오탐 방지)
- [ ] 기존 체크리스트 매칭 동작 회귀 없음

### 3. 테스트 추가
> kind: feature

**영향 파일**: `.claude/scripts/test_pre_commit.py`

**추가 테스트 케이스**:
- T_wip_sync_abbr_match: 체크리스트 없는 incidents WIP + abbr 매칭 staged 파일 → 자동 이동
- T_wip_sync_abbr_multi: 같은 abbr WIP 2개 → 이동 skip, stderr 경고
- T_wip_sync_abbr_no_map: 경로→도메인 매핑 없는 경우 → abbr 매칭 skip, 기존 동작 유지

**Acceptance Criteria**:
- [ ] `python3 -m pytest .claude/scripts/test_pre_commit.py -q` 전체 통과

## 결정 사항

- `extract_path_domain_map()` 신설 — naming.md 코드블록에서 `{패턴} → {도메인}` 파싱
- `path_to_domain()` 신설 — fnmatch 기반 staged 파일 → 도메인 변환
- `cmd_wip_sync` 2차 매칭 경로 추가 — abbr 일치 WIP를 직접 이동 시도
- 복수 abbr WIP → stderr 경고 + skip (오탐 방지 가드)
- trailing newline 버그 수정 — `splitlines()` 비교로 오탐 방지 (기존 로직에도 적용)
- 클로저 캡처 버그 수정 — `_mark_line` 기본 파라미터로 루프 변수 바인딩
- T40 테스트 3케이스 추가 (test_pre_commit.py): 단일 매칭·복수 skip·매핑 없음 폴백

## 다운스트림 적용 방법

abbr 매칭이 동작하려면 다운스트림 프로젝트의 `naming.md` `## 경로 → 도메인 매핑` 섹션
코드블록에 **실제 경로 매핑**을 등록해야 한다.

```
# .claude/rules/naming.md  ← 다운스트림 프로젝트의 파일

## 경로 → 도메인 매핑 (선택, 코드 영역용)

...

업스트림 기본값: 생략. 다운스트림은 자기 프로젝트의 코드 폴더에 맞춰
위 예시를 참고해 경로 매핑을 추가 권장.

### 경로 매핑 — 확장 (프로젝트 고유)
```
src/services/performanceDates**  → pipeline
src/crawlers/**                  → crawler
packages/core/**                 → pipeline
packages/crawlers/**             → crawler
```
```

- `{경로패턴}` — glob 형식 (`**` 포함). fnmatch로 staged 파일 경로에 대조
- `{도메인}` — `naming.md` "도메인 목록 > 확정"에 있는 도메인 이름
- 도메인에 대응하는 abbr이 약어 표에 등록되어 있어야 WIP 파일명 매칭 성공

위 예시에서 `packages/crawlers/src/crawlers/MelonTicketCrawler.ts` staged 시:
`packages/crawlers/**` → `crawler` → abbr `cr` → `incidents--cr_*.md` WIP 자동 이동

## 메모

- trailing newline 버그: `"\n".join(splitlines())`가 trailing `\n` 제거해 `new_text != marked`
  → 모든 WIP가 체크리스트 0개이면 자동 이동됐던 기존 버그. 이번에 함께 수정
- naming.md 업스트림은 예시 코드블록만 있어 `extract_path_domain_map()`이 예시 도메인(payment 등)
  을 반환하지만 `domain_to_abbr`에 없어 무해. 다운스트림이 실제 매핑 추가 시 동작
- T40 fixture: function-scope 필수 — module-scope 공유 시 naming.md 상태 오염 발생 확인
