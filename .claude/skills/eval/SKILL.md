---
name: eval
description: 하네스·코드 건강 검진. --quick은 30초 헬스체크. --harness는 하네스 문서 품질 평가 + 레거시 문서 정비 안내 (doc-health 흡수). 주기적으로 돌리는 건강 체크.
---

# /eval 스킬

"놓치고 있는 것"을 찾는다. 본 wave §S-4 (73% 삭감)에서 모드 축소:
**--quick** (30초 헬스체크) + **--harness** (하네스 품질 + 레거시 정비) 2개만.

폐기 (§S-4): --surface 암묵지 발견, --deep 4관점 병렬 에이전트, --deep
시크릿 스캔(commit pre-check가 라인 단위 차단), --deep archive 폴더 점검.

| 사용법 | 설명 |
|--------|------|
| `/eval --quick` | 30초 헬스체크 |
| `/eval --harness` | 하네스 문서 품질 + 레거시 정비 안내 |

## /eval --quick (30초 헬스체크)

작업 중간 "지금 괜찮은가?" 빠른 확인.

### 점검 항목 (30초 이내)

1. 린터 에러 수
2. 미완료 WIP 문서 수 (`docs/WIP/` pending/in-progress)
3. TODO/FIXME/HACK 수 (`src/` 카운트)
4. 마지막 커밋 경과 시간 (`git log -1 --format="%ar"`)
5. 미커밋 변경 파일 수 (`git status --porcelain | wc -l`)

### 보고

```
## /eval --quick

✅ 린터: 에러 0
📋 WIP: 2개 (1 in-progress, 1 pending)
⚠️ TODO/FIXME: 3개
🕐 마지막 커밋: 2시간 전
📦 미커밋 변경: 5개 파일
```

문제없으면 "헬스체크 통과. ✅" 한 줄.

## /eval --harness (하네스 문서 품질 + 레거시 정비)

하네스 문서가 **모호·모순·부패**한 부분 + CPS 무결성 + 레거시 문서 정비
안내까지 통합.

### 점검 대상

CLAUDE.md, `.claude/rules/`, `.claude/skills/` 전체.

### 항목 1~4 — LLM 해석 영역

**1. 모호성** — AI가 해석을 달리할 수 있는 표현

위험 신호:
- "적절한", "상황에 따라", "알아서" (판단 기준 부재)
- 수치 없는 기준 ("짧게", "간결하게")
- "등", "기타"로 끝나는 목록 (열거 불완전)

**조건문은 모호성 아님** — "X가 필요하면", "X가 가능하면" 등 조건분기는
false-positive. 제외.

발견 시 구체 대안 제시 ("짧게" → "30줄 이하").

**2. 모순** — 문서 간 충돌하는 지시

- CLAUDE.md와 rules/ 사이 같은 주제를 다른 기준으로 다루는 곳
- rules/ 간 상충
- skills/ 절차가 rules/와 안 맞는 곳

발견 시 사용자에게 질문. 임의 해결 금지.

**3. 부패** — 현재 프로젝트 상태와 안 맞는 규칙

- 존재 안 하는 파일/폴더 참조
- 린터가 잡고 있는데 rules/에도 남은 중복
- 최근 3개월 방어 0건 강등 후보

**4. 강제력 배치 오류** — 린터가 잡을 수 있는 건 린터에. rules/에 있지만
린터 가능하면 승격 제안.

### 항목 5~7 — 결정적 (CLI)

```bash
python3 .claude/scripts/eval_harness.py
```

**5. CPS 무결성** — `eval_cps_integrity.py` 위임. Problem 인용 빈도·인플레이션·
Solution 충족 인용 분포.

**6. 방어 활성 기록** — `.claude/memory/signal_defense_success.md` 최근 3개.

**7. 피드백 리포트** — 다운스트림 `migration-log.md` `## Feedback Reports`
4필드(관점·약점·실천·심각도) 검증.

### 보고

```
## /eval --harness 결과

### 모호성
- coding.md: "함수는 짧게" → 기준 없음. "30줄 이하" 제안

### 모순
- 없음 ✅

### 부패
- 없음 ✅

### 강제력 배치
- 없음 ✅

### CPS 무결성
- 스캔 문서: 88개
- Problem 수: 9개
- 박제 의심: 0건 ✅

### 방어 활성 기록
- 총 3건 | 최근: 2026-05-15 ...

### 피드백 리포트
- 없음 ✅
```

### 레거시 문서 정비 안내 (doc-health 흡수)

CPS 무결성 스캔에서 다음 중 하나라도 해당하면 정비 흐름 안내:

- abbr 없는 파일 5개 이상
- CPS frontmatter(`problem`·`s`) 없는 파일 10개 이상
- 박제 의심 3건 이상

해당 시 보고 마지막에:

```
⚠️ 레거시 문서 정비 권장. 아래 3단계 진행:

1. abbr 없는 파일 rename
   - `naming.md` 약어 표에서 abbr 조회
   - `docs_ops.py move` 명령으로 이동·rename 처리

2. CPS frontmatter 추가
   - 누락 파일 목록 grep → 사용자 결정 후 frontmatter 보강

3. 구 문서 archived 이동
   - 도메인별 문서 목록 제시 → 사용자 keep/archive 결정
   - `docs_ops.py move <파일> --target archived`

상세 절차: `.claude/scripts/docs_ops.py` 도움말 + 사용자 인터랙티브 진행.
```

문제 없으면 "하네스 정상. ✅".

## 스코프 경계

- **eval** = 프로젝트 전체 / 누적. 변경 없이도 돈다
- **review** = 이번 diff만. 커밋 직전 commit 스킬이 호출
- **commit pre-check** = staged 시크릿 line-confirmed 차단 (보안 게이트)

같은 질문 중복 금지.
