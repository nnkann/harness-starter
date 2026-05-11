---
name: doc-health
description: 하네스 도입 이전 레거시 문서를 정비한다. eval --harness 진단 결과를 받아 abbr 없는 파일 rename, CPS frontmatter 추가, 구 문서 archived 이동을 반자동화. "doc-health", "문서 건강 진단", "레거시 문서 정비" 요청 시 사용.
serves: S3
---

# doc-health 스킬

하네스 도입 이전 레거시 문서를 정비한다. eval --harness가 진단한 문제를
받아 3단계 정비를 반자동으로 진행한다.

## 언제 사용하나

- `eval --harness` 결과에서 "doc-health 실행 권장" 안내가 표시됐을 때
- `harness-adopt` 완료 후 레거시 문서가 많은 프로젝트
- 직접 "doc-health", "문서 건강 진단", "레거시 문서 정비" 요청 시

## 전제

- `harness-adopt` 완료 (`.claude/` 이식 후)
- `docs/guides/project_kickoff.md` (CPS)가 존재하고 Problems/Solutions 정의됨
- `naming.md`에 도메인·약어 표 등록됨

---

## Step 0. eval --harness 진단 실행

```bash
python3 .claude/scripts/eval_cps_integrity.py
```

추가로 abbr 없는 파일 목록을 수집한다:

```bash
# naming.md에서 등록된 abbr 목록 추출
ABBRS=$(grep -oP '(?<=\| )[a-z]{2,3}(?= \|)' .claude/rules/naming.md | sort -u | tr '\n' '|' | sed 's/|$//')

# abbr 패턴이 없는 문서 파일 목록
python3 -c "
import os, re, sys
abbrs = '$ABBRS'.split('|')
pattern = re.compile(r'(^|[_-])(' + '|'.join(abbrs) + r')_')
missing = []
for root, dirs, files in os.walk('docs'):
    dirs[:] = [d for d in dirs if d not in ('archived', 'clusters')]
    for f in files:
        if f.endswith('.md'):
            if not any(pattern.search(f) for _ in [None]):
                missing.append(os.path.join(root, f))
for f in sorted(missing):
    print(f)
"
```

진단 결과 요약을 사용자에게 먼저 보고한다:

```
## doc-health 진단 결과

- abbr 없는 파일: N개
- CPS frontmatter 없는 파일: N개
- 박제 의심: N건

3단계 정비를 진행합니다. 언제든 중단 가능합니다.
```

---

## Step 1. SSOT 선별 + archived 이동 (인터랙티브)

**이 단계는 사람이 결정한다.** 스킬은 목록 제시·실행만 담당.

### 1.1 도메인별 문서 목록 제시

decisions/, guides/, incidents/ 각 폴더를 도메인별로 묶어 제시한다.
한 도메인씩 처리. 16개+ 있으면 도메인 단위로 끊어서 처리.

```
### [도메인명] 문서 목록 (N개)

1. foo_bar.md — "제목" (created: YYYY-MM-DD)
2. baz_qux.md — "제목" (created: YYYY-MM-DD)
...

각 파일에 대해 결정:
  k = keep (유지)
  a = archive (docs/archived/로 이동)
  s = skip (나중에 결정)

입력 형식: "1:k 2:a 3:s ..."
```

### 1.2 archived 이동 실행

```bash
python3 .claude/scripts/docs_ops.py move <파일경로> --target archived
```

이동 후 CPS 언급 자동 grep (commit SKILL.md Step 2.1.1 패턴 동일):

```bash
ARCHIVED_SLUG=$(basename "<파일>" .md)
CPS_FILE=$(grep -rl "tags:.*cps" docs/ 2>/dev/null | head -1)
[ -n "$CPS_FILE" ] && grep -n "$ARCHIVED_SLUG" "$CPS_FILE" && echo "→ CPS 링크 갱신 필요할 수 있음"
```

모든 도메인 처리 완료 후 Step 2로.

---

## Step 2. abbr 없는 파일 rename (반자동)

Step 0에서 수집한 abbr 없는 파일 목록 처리.

### 2.1 파일별 rename 제안

각 파일에 대해:
1. 파일명·제목·도메인을 읽어 적합한 abbr 추론
2. 새 파일명 제안: `{abbr}_{slug}.md`
3. 사용자 확인 후 실행

```
rename 제안:
  old: docs/decisions/concert-schema.md
  new: docs/decisions/co_concert_schema.md
  (abbr: co = concert 도메인)

확인? [y/n/skip]
```

### 2.2 실행

```bash
git mv docs/decisions/concert-schema.md docs/decisions/co_concert_schema.md
```

rename 후 역참조 갱신:

```bash
python3 .claude/scripts/docs_ops.py cluster-update
```

---

## Step 3. CPS frontmatter 추가 (반자동)

frontmatter에 `problem`·`solution-ref`가 없는 파일 처리.

### 3.1 파일별 분류

각 파일 본문을 읽어 CPS Problem/Solution과 매칭:
- 파일 내용 요약 → 주된 Problem 1개 추론
- 관련 Solution 충족 기준 추론

```
frontmatter 제안:
  파일: docs/decisions/co_concert_schema.md
  제목: "Concert 스키마 설계"

  problem: P2
  solution-ref:
    - S2 — "review tool call 평균 ≤4회"

  적용? [y/수정/skip]
```

수정 입력 시 → 사용자가 직접 값 입력 후 적용.

### 3.2 적용

frontmatter `problem`·`solution-ref` 삽입:

```python
# docs.md CPS 인용 규칙 준수:
# - 50자 이내: 원문 그대로
# - 50자 초과: (부분) 마커 + substring
```

### 3.3 CPS 면제 파일

본문이 CPS와 무관한 파일(디자인 에셋 설명, 외부 API 참조 문서 등)은
사용자 확인 후 `problem: none` 표시 또는 archived 이동.

---

## Step 4. cluster 갱신 + 진단 재실행

```bash
python3 .claude/scripts/docs_ops.py cluster-update
python3 .claude/scripts/eval_cps_integrity.py
```

### 결과 비교 보고

```
## doc-health 정비 완료

| 항목 | 정비 전 | 정비 후 |
|------|---------|---------|
| abbr 없는 파일 | N개 | M개 |
| CPS frontmatter 없는 파일 | N개 | M개 |
| archived 이동 | — | N개 |
| 박제 의심 | N건 | M건 |
```

---

## 주의

- **SSOT 선별은 사람이 결정한다.** 스킬이 자의적으로 archived 이동하지 않는다.
- 한 단계씩 끊어서 진행. 16개+ 파일은 도메인 단위로 분할 처리.
- rename 후 always `cluster-update` — 탐색 체인 정합성 유지.
- CPS 인용은 `docs.md` "## CPS 인용" 규칙 준수 (50자 이내 원문 / 초과 시 `(부분)` 마커).
