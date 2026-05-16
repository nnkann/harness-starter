---
title: tag 정규식 누적 부채 auto-fix 도구 (FR-X2)
domain: harness
problem: [P7, P11]
s: [S7]
tags: [tag-policy, normalize, naming, downstream-debt]
relates-to:
  - path: decisions/hn_doc_naming.md
    rel: extends
status: abandoned
created: 2026-05-15
---

# tag 정규식 누적 부채 auto-fix 도구 (FR-X2)

## 사전 준비

- 다운스트림 v0.42.7 → v0.47.4 적용 보고 FR-X2 수신 (2026-05-15)
- 측정값: 다운스트림 docs/ 내 7개 문서 tag 정규식 위반 (대문자·언더바·한글)
  - `[ArtistMatcher, semantic-search, pgvector, embedding]`
  - `[split, commit, review, diff, task_groups]`
  - `[rpc, view_count, migration]`
  - `[melon, csoonId, prodId, 가격재수집]`
  - `[monorepo, lsp, typescript, exports, customConditions]`
  - `[yes24, performance_dates, upsert, rollback]`
  - `[stage2, blog_processing_at, lock, riize]`
- 현재 상태: 본 commit은 통과(미수정 문서), 다음에 해당 문서 수정 시 pre-check 즉시 차단
- SSOT: `.claude/rules/naming.md` "tag 정책 — wiki 간선 정규식" (L251~)
- pre-check: `.claude/scripts/pre_commit_check.py` tag 검사 로직

## 목표

v0.47.1 도입된 tag 정규식 차단이 다운스트림 누적 부채(고유명사·도메인 용어)와
마찰하는 패턴을 auto-fix 도구로 해소. 차단 자체는 유지하되 normalized 제안을
출력해 사용자 1줄 응답으로 수정 가능. P7 S7 "domain·tag·review 3축 분리 정합"
충족 기준의 다운스트림 cascade 영역 보강.

## 작업 목록

### 1. tag-normalize 변환 규칙 정의

**사전 준비**: 현재 정규식 `^[a-z0-9][a-z0-9-]*[a-z0-9]$`. 위반 패턴 분석 — 대문자, 언더바, 한글 3종.
**영향 파일**: `.claude/scripts/docs_ops.py` (또는 별도 `tag_normalize.py`), `.claude/rules/naming.md` (정책 박제)
**Acceptance Criteria**:
- [x] Goal: 위반 tag를 결정적 규칙으로 normalize. 사용자 모호성 없는 변환 규칙만 자동, 모호 케이스(한글)는 prompt (S7 domain·tag 정합 보강)
  검증:
    tests: pytest .claude/scripts/tests/ -m tag_normalize -q (신규 marker)
    실측: 변환 규칙 표가 naming.md 또는 별도 결정 문서에 박제. 7건 측정 케이스 전부 변환 결과 명시
- [x] 변환 규칙:
  - 대문자 → 소문자 (`ArtistMatcher` → `artistmatcher` 또는 분리 제안 `artist-matcher` — camelCase 경계 감지 시 분리 제안)
  - 언더바 → 하이픈 (`task_groups` → `task-groups`)
  - 한글 → **자동 변환 금지** + 매핑 prompt (`가격재수집` → 사용자가 영문 매핑 입력 또는 tag 제거 선택)
- [x] camelCase 분리: `[a-z][A-Z]` 경계에서 하이픈 삽입 후 lowercase (`ArtistMatcher` → `artist-matcher`, `csoonId` → `csoon-id`, `customConditions` → `custom-conditions`)
- [x] 모든 변환은 dry-run 우선. 사용자 confirm 없이 파일 수정 금지

### 2. CLI 도구 — `docs_ops.py tag-normalize`

**사전 준비**: `docs_ops.py`의 기존 subcommand 패턴 (cps, cluster-update, reopen, move 등) 참조.
**영향 파일**: `.claude/scripts/docs_ops.py`
**Acceptance Criteria**:
- [x] Goal: `python .claude/scripts/docs_ops.py tag-normalize [<path>]` 명령으로 위반 tag 검출 + 변환 제안 + 사용자 confirm 후 일괄 수정 (S7 cluster 간선 정합 유지)
  검증:
    tests: pytest .claude/scripts/tests/ -m tag_normalize -q
    실측: `python .claude/scripts/docs_ops.py tag-normalize --help` 출력에 본 subcommand 명시. 샘플 문서로 dry-run 검증
- [x] 인자: path 생략 시 `docs/**/*.md` 전체 스캔. path 지정 시 해당 파일·디렉토리만
- [x] 출력 포맷:
  ```
  docs/incidents/cr_melon_csoon_id_empty.md
    tags: [melon, csoonId, prodId, 가격재수집]
    proposed: [melon, csoon-id, prod-id, ???]
    한글 tag '가격재수집' — 영문 매핑 입력 또는 [s]kip:
  ```
- [x] `--dry-run` 플래그 (기본) / `--apply` 플래그 (실제 수정). apply 시 frontmatter `updated:` 갱신
- [x] `--yes` 플래그로 비대화형 모드 (한글 tag는 자동 skip + 경고)

### 3. pre-check 차단 시 normalize 제안 출력

**사전 준비**: `pre_commit_check.py`가 tag 위반 검출 시 현재는 위반 tag명 + 권장 형식만 출력. normalize 도구 안내 추가.
**영향 파일**: `.claude/scripts/pre_commit_check.py`
**Acceptance Criteria**:
- [x] Goal: pre-check이 tag 위반 차단 시 출력 메시지 끝에 `python .claude/scripts/docs_ops.py tag-normalize <path>` 명령 안내 한 줄 추가. 사용자 즉시 실행 가능
  검증:
    tests: pytest .claude/scripts/tests/test_pre_commit.py -m stage -q
    실측: 위반 tag 포함 문서를 stage 후 pre-check 실행 → 출력 마지막에 tag-normalize 명령 안내 존재
- [x] 안내 메시지는 차단 메시지의 일부로 표시 (별도 줄). 자동 실행은 안 함 (사용자 명시 trigger 원칙)

### 4. 결정 문서 박제

**사전 준비**: 본 wave는 `decisions/hn_doc_naming.md` 확장 또는 별도 `decisions/hn_tag_normalize.md`. naming.md 본문 SSOT 단일 + 결정 근거 별도가 패턴.
**영향 파일**: `docs/decisions/hn_doc_naming.md` (확장 형태)
**Acceptance Criteria**:
- [x] Goal: `hn_doc_naming.md` `## 변경 이력` 또는 신규 섹션에 "tag-normalize 도구 도입 (FR-X2)" 박제. SSOT 위치 + 변환 규칙 표 + 한글 처리 정책
  검증:
    tests: 없음
    실측: `grep -nE "tag-normalize|FR-X2" docs/decisions/hn_doc_naming.md` hit
- [x] 한글 tag 처리 정책 명시: 자동 변환 금지 (transliteration 정보 손실), 사용자 매핑 prompt 또는 tag 제거 선택. naming.md tag 정책 한글 금지 원칙과 정합

## 메모

- 사용자 결정: FR-X1·X2 둘 다 박제 (2026-05-15)
- 본 wave 범위: starter 측 도구 + 정책. 다운스트림 7건 일괄 변환 자체는 다운스트림이 본 도구로 실행
- 한글 tag 자동 변환 금지 이유: `가격재수집` → `price-recollection`? `price-rescrape`? — 도메인 문맥 없이 모호. transliteration `garyeokjaesujip`은 무의미. 사용자 결정 필수
- 별 wave 후보: incident 분류 한정 한글 symptom-keywords 허용은 이미 docs.md에 있음 (`symptom-keywords` 면제). tag는 영문 강제 유지가 정합
- **P11 동형 잠복 후보** (1차 발견 → 다른 위치 후보 자동 탐색 부재):
  본 wave 결함 패턴 = "pre-check 차단 항목이 차단만 하고 auto-fix 도구 없음". 동형 잠복 후보:
  - `pre_commit_check.py` TODO/FIXME 차단 — auto-fix 제안 없음 (단순 차단)
  - `pre_commit_check.py` S# 미인용 차단 (v0.47.4 §S-9) — 가장 가까운 S# 후보 제안 없음
  - `pre_commit_check.py` AC 체크박스 부재 차단 (v0.47.4 §S-8) — auto-convert 도구 없음
  - `pre_commit_check.py` completed 봉인 차단 — `docs_ops.py reopen` 명령 안내는 있음 (긍정 사례 — 본 wave Task 3가 이 패턴 follow)
  - 본 wave는 tag 정규식 1건만 처리. 동형 후보 탐색은 별 wave (P11 정련 시)
