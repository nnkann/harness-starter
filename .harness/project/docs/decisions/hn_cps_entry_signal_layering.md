---
title: CPS 진입 신호 계층화 — 3층 책임 분리 + 도구 frontmatter trigger + HARNESS_MAP 역생성
domain: harness
problem: P7
solution-ref:
  - S1 — "규칙 + 자동 차단 + 우회 장치"
tags: [cps, layering, trigger, harness-map, frontmatter, cascade, meta-decision]
relates-to:
  - path: guides/hn_harness_organism_design.md
    rel: extends
  - path: decisions/hn_frontmatter_graph_spec.md
    rel: references
status: completed
created: 2026-05-11
updated: 2026-05-11
---

# CPS 진입 신호 계층화 — 3층 책임 분리 + 도구 frontmatter trigger + HARNESS_MAP 역생성

## 배경

`bit_cascade_objectification` 결정에서 발견된 메타 문제: CPS Problem
정의가 "증상·영향·승격 상태"만 있고 **"어느 도구가 어느 P에 진입해야
하는지" 객관 명시가 부재**. 결과로 cascade(P → 진입 → 행동)가 자가
발화에 의존 → P8 (자가 발화 의존 규칙의 일반 실패) 재현.

### 사용자 검토 흐름

1. 1차 아이디어: P 정의에 "진입 후보군" 목록 추가 (debug-specialist·
   pre-check 등 명시)
2. 사용자 우려: 새 도구 추가마다 갱신 부담. 가치 vs 비용 검증 필요
3. Gemini 외부 시각: 후보 목록은 **Double Entry 문제** — HARNESS_MAP
   중복 + 다운스트림 충돌 (업스트림 P 정의 수정 권한 모호) + 운전사
   부재 (목록 정교화만으로 cascade 보장 안 됨)
4. 합의: 후보 목록 박지 않음. 진입 조건만 박음. 후보는 도구
   frontmatter에서 자기 선언 + HARNESS_MAP 자동 역생성

### Gemini 외부 시각 핵심 비판

> 보강안이 가치를 가지려면 "진입 후보군" 목록보다 **"진입 조건의
> 객관화"가 핵심**. 후보 목록만 적어두는 것은 단순히 HARNESS_MAP을
> P 정의로 옮긴 것에 불과.

> 보강안은 '지도'를 정교하게 만들 뿐, '운전사'의 졸음 운전을 막지
> 못함.

> '누가 진입하는가(Who)'는 도구의 속성으로 관리하고, '언제 발생하는가
> (When)'만 P 정의에 담아라.

## 선택지

### 후보 1 — P 정의에 후보 목록 직접 박기 (Gemini 거부)

```markdown
### P1. ...
**진입 후보**:
  - debug-specialist
  - pre_commit_check.py
**진입 조건**: ...
```

거부 이유:
- Double Entry (HARNESS_MAP 중복)
- 새 도구 추가 시 P 정의 갱신 부담
- 다운스트림이 업스트림 P 정의 수정해야 → 프레임워크 자격 상실
- "운전사" 강제 못 함 (목록만으로 cascade 안 됨)

### 후보 2 — 3층 책임 분리 (Gemini 권고, 사용자 합의) ★ 채택

3개 계층이 명확히 분리된 책임:

```
[Layer 1 — CPS Problem 정의]
  내용: 진입 조건(Signal)만. "언제 활성화되나"
  변경 빈도: 매우 낮음 (프로젝트 owner)
  예: "P1 진입 조건: 동일 파일 3회 수정 / 같은 에러 반복"

[Layer 2 — 도구 frontmatter]
  내용: defends/serves + trigger (자격 요건). "나는 P1의 X 조건에 진입"
  변경 빈도: 도구 추가/수정 시 (도구 작성자)
  예: debug-specialist frontmatter
      defends: P1
      trigger: error-repeat

[Layer 3 — WIP AC]
  내용: problem·solution-ref + 검증 묶음. "이 작업은 P1·S1에 진입"
  변경 빈도: 매 작업 (작업자)
  검증: pre-check이 frontmatter ↔ CPS 매칭 객관 검증
```

흐름:
```
Layer 1 (P 정의 진입 조건) → 도구 작성자가 Layer 2에서 자기 자격 선언
Layer 2 (도구 frontmatter trigger) → HARNESS_MAP 역생성 스크립트가 수집
Layer 3 (WIP AC) → pre-check 객관 검증
```

### 후보 3 — HARNESS_MAP만 강화 (P 정의 무변경)

- P 정의는 그대로
- HARNESS_MAP에 trigger 컬럼 추가 + 역방향 인덱스 자동 생성

거부 이유:
- Layer 1 진입 조건 객관화 효과 누락 (P 정의가 여전히 추상)
- HARNESS_MAP은 도구 측 정보 — P 자체의 진입 정의가 빠짐
- 본 결정의 핵심 가치 (P9 정보 오염의 관성 해소)와 미흡

## 결정

**후보 2 (3층 책임 분리) 채택**.

### Layer별 명세

#### Layer 1 — CPS Problem 정의에 "진입 조건" 추가

`docs/guides/project_kickoff.md` Problems 섹션 각 P에 다음 필드 추가:

```markdown
### P#. 제목
**증상**: ... (기존)
**영향**: ... (기존)
**승격 상태**: ... (기존)
**진입 조건** (객관 신호):    ← 신규
  - <객관 detect 가능 신호 1>
  - <객관 detect 가능 신호 2>
```

원칙:
- **후보 목록 박지 않음** — Layer 2에 위임
- **객관 detect 가능 신호만** — git history·frontmatter 매칭·diff
  grep·log 검증 등
- **자가 발화 의존 신호 금지** — "Claude가 X라 판단" 형태 거부

다운스트림 권한:
- Layer 1은 업스트림 소유. 다운스트림 직접 수정 금지
- 다운스트림이 새 P 필요 시 자체 도구 frontmatter `defends:`로 cascade
  자동 작동 (Layer 2 경로)

#### Layer 2 — 도구 frontmatter에 `trigger` 필드 추가

rules·skills·agents·scripts frontmatter:

```yaml
---
defends: P1                      # 기존
trigger: error-repeat            # 신규 — 자격 요건
---
```

또는 다중 trigger:
```yaml
defends: P1
trigger:
  - error-repeat
  - same-file-edit-gt-3
```

원칙:
- **trigger는 Layer 1 진입 조건 중 자기가 담당하는 것 선언**
- **자기 자격 선언이지 강제 명령 아님** — 실제 진입은 작업 흐름에서
- **다운스트림 도구도 같은 형식** — cascade 자동 작동

#### Layer 3 — WIP AC (기존 유지)

WIP frontmatter `problem`·`solution-ref` + AC 검증 묶음. 기존 docs.md
규정 그대로. pre-check이 Layer 3 ↔ Layer 1 매칭 객관 검증.

### HARNESS_MAP 자동 역생성

`docs/clusters/` 또는 `.claude/HARNESS_MAP.md`를 다음으로 격상:

- **이전**: 사람이 작성·갱신하는 양방향 관계 지도
- **이후**: 도구 frontmatter `defends:`·`serves:`·`trigger:` 필드를 긁어서
  자동 생성하는 역방향 인덱스

생성 트리거:
- `pre-commit` 또는 별 스크립트 (`scripts/regenerate_harness_map.py`)
- 사람 갱신 의무 없음 — 정합성 항상 보장

생성 결과 예:
```markdown
## P1. LLM 추측 수정 반복

**진입 조건** (Layer 1에서 가져옴):
- 동일 파일 3회 수정
- 같은 에러 반복

**진입 도구** (Layer 2 frontmatter 자동 수집):
| 도구 | trigger |
|------|---------|
| debug-specialist | error-repeat |
| pre_commit_check.py | same-file-edit-gt-3 |
| review | speculation-pattern |
```

### 다운스트림 cascade

```
[업스트림] P 정의 (Layer 1) — 다운스트림 수정 금지
    ↓
[다운스트림] 자체 도구 frontmatter trigger 선언 (Layer 2)
    ↓
[다운스트림] HARNESS_MAP 역생성 — 자동으로 다운스트림 도구 포함
    ↓
P → 도구 cascade 자동 작동, 업스트림 변경 없음
```

업스트림이 새 P 추가 시 → 다운스트림은 자체 trigger 선언만 갱신.
업스트림 P 정의를 다운스트림이 안 건드림 → 프레임워크 자격 유지.

## 구현 순서

1. **Layer 1 보강** — `docs/guides/project_kickoff.md` P1~P8 각각에
   "진입 조건" 필드 추가. 후보 목록 박지 않음. 객관 detect 가능 신호만.

2. **Layer 2 스키마 정의** — `rules/docs.md`에 도구 frontmatter `trigger:`
   필드 정의. 사용 예시·금지 패턴 명시.

3. **기존 도구 frontmatter 보강** — rules·skills·agents·scripts의
   기존 `defends:`·`serves:` 옆에 `trigger:` 추가. 점진 적용 가능
   (한 번에 다 안 해도 됨).

4. **HARNESS_MAP 역생성 스크립트** — `scripts/regenerate_harness_map.py`
   (또는 기존 docs_ops.py 확장). pre-commit hook 등록.

5. **pre-check 검증 보강** — `pre_commit_check.py`에 Layer 1 ↔ Layer 3
   매칭 검증 추가 (이미 부분 존재 — frontmatter `problem` 필드 검증).

6. **다운스트림 마이그레이션 가이드** — `MIGRATIONS.md`에 본 결정 반영.
   다운스트림 도구 frontmatter에 trigger 추가 권장.

## 검증 기준

본 결정 구현 후:

- P1~P8 모두 "진입 조건" 필드 보유, 객관 detect 가능 신호 명시
- 도구 frontmatter `trigger:` 필드 스키마 정의 + 기존 도구 보강률
  (점진 — 첫 라운드 50% 이상 목표)
- HARNESS_MAP 자동 역생성 스크립트 작동, pre-commit 통합
- 사람이 HARNESS_MAP 수동 갱신 의무 0건
- 다운스트림이 업스트림 P 정의 수정 없이 자체 도구 cascade 가능
- pytest 회귀 가드 — Layer 1 진입 조건 변경 시 Layer 2 정합 검증

## P9 정의에의 적용

본 결정 합의 후 `bit_cascade_objectification` WIP의 P9 정의를 본 구조로
재작성:

```markdown
### P9. 정보 오염의 관성 (Information Inertia)

**증상**: ...
**영향**: ...
**진입 조건**:
  - WIP frontmatter `problem` 필드와 CPS Problems 매칭 실패
  - `## 발견된 스코프 외 이슈` 섹션 P# 매칭 누락
  - BIT trigger 신호 발생 후 BIT 판단 블록 미작성
  - 자동 트리거 신호가 자가 발화에 의존하는 패턴 감지
```

후보 목록(4+2+3) 명시 제거 — Layer 2 도구 frontmatter에 위임.

S9 정의도 진입 조건·해소 메커니즘 중심 (도구 frontmatter `serves: S9,
trigger: ...`로 cascade).

## 관련 결정

- `guides/hn_harness_organism_design.md` (extends) — HARNESS_MAP 양방향
  read 강제 결정. 본 결정은 그 위에 trigger 필드 + 자동 역생성 메타 층
- `decisions/hn_frontmatter_graph_spec.md` (references) — 문서 frontmatter
  스키마. 본 결정은 도구 frontmatter 확장
- `WIP/decisions--hn_bit_cascade_objectification.md` (precedes) — 본
  결정 합의 후 P9 정의를 본 구조로 재작성
- `WIP/decisions--hn_gemini_delegation_pipeline.md` (precedes) — Phase
  1 객관 신호 트리거는 본 결정과 평행 진행 가능. Phase 3 의미 신호
  트리거는 본 결정 + bit_cascade 합의 후

## 사각지대

- **Layer 1 진입 조건 정의의 객관성 자체** — "동일 파일 3회 수정" 같은
  신호는 객관이지만 "추측 패턴 감지"는 여전히 자가 발화 의존 가능성.
  진입 조건 작성 시 자가 발화 신호 금지 룰 명시 필요
- **trigger 필드 스키마의 다운스트림 확장성** — 다운스트림이 자체
  trigger 명칭 추가 시 충돌 방지 (namespace 또는 prefix 규칙 필요)
- **HARNESS_MAP 자동 역생성의 성능** — 도구 수 100개+ 시 pre-commit
  지연 가능. 캐싱·증분 생성 검토
- **Layer 1 진입 조건 변경 시 Layer 2 정합 깨짐** — 진입 조건이
  변경되면 도구 trigger 필드도 일괄 갱신 필요. 자동 검증 도구 필요
- **P9·S9 정의의 본 결정 의존** — 본 결정 합의 안 되면 P9 정의 박제
  불가. `bit_cascade_objectification` 결정도 동시 동결

## 메모

본 결정은 **세 결정의 선제 메타 결정**:
1. `bit_cascade_objectification` — P9 정의를 본 구조로 재작성
2. `gemini_delegation_pipeline` — Phase 3 의미 신호 트리거의 객관 신호
   기반
3. 미래의 모든 자동 트리거 결정 — 본 결정 구조 적용

본 결정 합의 후 진행 순서:
1. 본 결정 구현 (Layer 1·2 보강 + HARNESS_MAP 역생성)
2. `bit_cascade_objectification` P9 재작성 + 구현
3. `gemini_delegation_pipeline` Phase 1 진행 (평행), Phase 3 합의 후 진행
