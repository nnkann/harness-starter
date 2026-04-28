---
title: pipeline-design 규칙 업스트림 이식 계획
domain: harness
tags: [pipeline, rule, upstream-rule, review-pattern]
status: completed
created: 2026-04-21
updated: 2026-04-21
---

# pipeline-design 규칙 업스트림 이식 계획

## 배경

다운스트림(Issen) 프로젝트가 detection pipeline 재편 중 "T0 어텐션 스코어를
병합 결정에만 쓰고 폐기 → T1·T3가 색 거리만으로 같은 판단 3회 재계산"이라는
설계 실수를 한 달간 draft1→2→3 재편하면서도 알아채지 못함. 이 경험으로
`.claude/rules/pipeline-design.md` 신규 규칙 작성 (100줄, 7항목 체크리스트).

규칙의 핵심 통찰 — **"좋은 도구 한 번 쓰고 버림"과 "상류 출력 암묵적 폐기"
는 LLM + 인간 조합의 공통 맹점**. ML 파이프라인뿐 아니라 ETL·빌드·에이전트
체인 등 **다단 처리 전반에 적용 가능**하므로 업스트림 반영 가치 큼.

## 문제 — 현재 파일은 Issen 고유 맥락이 본문에 박혀 있음

1. **L7-10 배경**: `color_separation`·`T0 어텐션`·`draft1→2→3`·
   `cs_detection_pipeline.md` Issen 고유명사/경로
2. **L96-97 관련**: `cs_pipeline_redesign.md`·`cs_detection_pipeline.md`
   특정 도메인 파일 참조
3. **L84 "샘플"**: ML 도메인 용어. ETL·빌드에선 "입력 케이스"가 더 중립
4. **파이프라인 정의 없음**: Issen의 T0→T1→... 전제. 다른 프로젝트는
   `stage_1`·`extract/transform/load`·단계 네이밍 상이
5. **review 감지 규정 모호**: "파이프라인 단계 문서·코드 변경 시" 조건만
   있고 review가 무엇으로 감지하는지 불명확 → **본 이식에서는 review
   패턴 추가를 채택하지 않음** (review 과잉 사용 지적, 2026-04-21). 감지는
   rule 자체의 체크리스트 강제 + 사용자 트리거 질문으로 충분.

## 결정 — 범용화 + 업스트림 이식

### A. 업스트림 규칙 파일 신설

경로: `.claude/rules/pipeline-design.md`

범용화 원칙:
- 배경은 **문제 패턴**만 기술 (프로젝트 고유명사 없이)
- "실제 발생 사례는 각 프로젝트의 pipeline-origin-incident 문서 참조"
  포인터
- 4개 금지 패턴·7항목 체크리스트는 그대로 유지 (이미 범용)
- "샘플" → "입력 케이스", "T0/T1" → "단계 N/N+1" 추상화

### B. 파이프라인 정의 명시

서두에 "본 규칙이 적용되는 '파이프라인'의 정의" 섹션:

> 다단 처리 구조 — 여러 단계가 **입력 → 중간 신호 → 출력**으로 연결되고,
> 각 단계가 다음 단계가 재사용 가능한 신호를 계산하는 구조.
>
> 예시:
> - 데이터 변환 (ETL: extract → transform → load)
> - ML/신호 처리 (전처리 → 특징 추출 → 분류 → 후처리)
> - 에이전트 체인 (분석 → 판단 → 실행)
> - 빌드 (컴파일 → 링크 → 패키징)
> - 사용자 정의 단계 (T0→T1→... 같은 프로젝트별 네이밍)
>
> 단순 함수 호출 체인(같은 축 판단을 반복하지 않음)은 대상 아님.

### C. CLAUDE.md 트리거 문구

범용:
```
<important if="다단 처리 파이프라인(여러 단계가 입력→중간신호→출력으로
연결되는 구조)을 설계·재편할 때">
.claude/rules/pipeline-design.md를 먼저 읽어라. 상류 신호 재사용·
하류 보존 책임·전제 검증을 체크리스트로 강제한다.
</important>
```

다운스트림이 자기 네이밍(T0→T1 등)을 `<important if>` 조건에 추가하고
싶으면 CLAUDE.md 로컬 커스터마이징 (harness-upgrade 화이트리스트 보호
영역).

### D. review 패턴 추가 — 채택 안 함 (폐기)

**2026-04-21 결정**: review 에이전트 패턴 10번 추가는 **채택하지 않음**.

이유:
- 사용자 실측 "review deep 과잉 호출로 커밋 속도 5배 이상 저하" 피드백
- pipeline-design 위반은 **의도 설계 문제** — 자동 diff 감지가 적합하지
  않음 (키워드 매칭은 오탐 다수, 실제 설계 맥락 판단은 사람/rule 체크
  리스트 몫)
- rule 자체의 체크리스트(7항목)가 이미 "강제 도구" 역할 수행

대신:
- **rule 본문의 체크리스트 강제** — 설계 문서 작성 시 7항목 명시 의무
- **사용자 트리거 질문** — "같은 판단이 여러 단계에서 반복되는 패턴"을
  사람이 발견하면 rule 참조
- **self-verify.md 연계** — 파이프라인 단계 설계·재편 시 "체크리스트
  7항목 다 채웠는가" 자가 검증 단계에 포함

review 재조정은 별도 WIP로 파야 할 주제 (아래 "## 별도 이슈"에 기록).

### E. rules_metadata 등록

`docs/decisions/hn_rules_metadata.md`에 pipeline-design.md 추가. REFERENCED_DOCS
동적 탐색 대상에 포함되려면 다른 rules가 참조하면 됨 (naming·no-speculation
·internal-first와 같은 방식).

### F. 다운스트림 마이그레이션

Issen 프로젝트의 다음 액션:
1. `docs/archived/cs_detection_pipeline.md`·`docs/decisions/cs_pipeline_redesign.md`
   는 프로젝트 고유 사료로 유지 (rename 없음)
2. 로컬 `.claude/rules/pipeline-design.md`는 업스트림 버전으로 덮어쓰되,
   프로젝트 고유 사례 링크는 파일 하단 **"## 프로젝트 고유 사례 (로컬)"**
   섹션에 추가 — harness-upgrade는 업스트림 소유 섹션만 덮어쓰므로 보존
3. CLAUDE.md에 자기 네이밍(T0→T1) 조건을 추가하고 싶으면 업스트림 블록
   **아래**에 별도 `<important if>` 추가

### G. 업스트림 사료 기록

`docs/incidents/hn_pipeline_design_rule_origin.md` 생성 — 다운스트림에서
규칙이 어떻게 올라왔는지 기록:
- 다운스트림 발생 맥락 (고유명사는 `<프로젝트 사례>` placeholder)
- 한 달간 재편에도 못 본 이유 (LLM 공통 맹점)
- 업스트림 범용화 판단 근거

## 실행 계획

1. ✅ 본 WIP 문서 (결정 SSOT)
2. `.claude/rules/pipeline-design.md` 신설 (범용 버전, ~110줄)
3. `docs/decisions/hn_rules_metadata.md`에 pipeline-design 등록
4. CLAUDE.md 템플릿 — `<important if>` 블록 추가
   - 업스트림 이 레포 CLAUDE.md 수정
   - `harness-init` 템플릿(project_kickoff_sample.md 또는 CLAUDE.md 생성 로직)에도 반영
5. `.claude/rules/self-verify.md`에 "파이프라인 단계 설계·재편 시 체크
   리스트 7항목" 항목 추가 (review 패턴 대신 self-verify로 강제)
6. `docs/incidents/hn_pipeline_design_rule_origin.md` 신설
7. `docs/harness/MIGRATIONS.md` v0.17.0 섹션
   - 자동 적용: rules·rules_metadata·self-verify·CLAUDE.md 템플릿
   - 수동 액션: 프로젝트 고유 pipeline-origin-incident 작성 (권장)
   - 다운스트림 로컬 `pipeline-design.md` 커스터마이징 보존 방법
8. `docs/harness/promotion-log.md` v0.17.0 이력
9. `.claude/HARNESS.json` 0.16.1 → 0.17.0 (minor — 신 rule 도입)
10. `docs/clusters/harness.md`에 신규 rule·incident 추가
11. 본 WIP completed 전환 → `decisions/hn_pipeline_design_rule.md` 이동

## 범용화 체크 — 새 규칙 파일 구조

```
# Pipeline Design 규칙

## 정의 — 본 규칙이 적용되는 "파이프라인"
(위 B항 내용)

## 원칙 — 단계 설계의 양방향 책임
### 받는 쪽 (upstream 활용) — 3항목
### 넘기는 쪽 (downstream 보존) — 3항목

## 금지 패턴
1. 좋은 도구 한 번 쓰고 버림
2. 상류 출력 암묵적 폐기
3. 전제 미검증 재편
4. 단일 케이스 over-fit  # "샘플" → "케이스" 추상화

## 설계 리뷰 체크리스트 (7항목)
- 입력 / 중간 계산 / 출력 / 폐기 / 보존 책임 / 전제 / 검증 케이스

## 위반 감지
- **rule 체크리스트 강제** — 단계 설계 문서에 7항목 명시 의무. 누락
  시 self-verify.md가 "완료 보고 금지" 적용
- **사용자 질문 트리거** — 같은 판단이 여러 단계에서 반복되는 패턴 발견
  시 즉시 "상류에 이 판단 신호가 있지 않나?" 질문
- (review 자동 감지는 본 규칙에 도입하지 않음 — 과잉 호출 회피)

## 관련
- 프로젝트 고유 사례: 각 프로젝트의 `docs/incidents/*_pipeline_origin*`
- 업스트림 사료: `docs/incidents/hn_pipeline_design_rule_origin.md`
- `.claude/rules/no-speculation.md`
- `.claude/rules/internal-first.md`
```

## 회귀 위험

- **파이프라인 없는 프로젝트** — rule 파일 자체가 로드되지만 `<important
  if>` 조건 미발동으로 행동 영향 0. rules/ 용량만 ~3KB 증가
- **다운스트림 커스터마이징 충돌** — 업스트림이 덮어쓰는 영역 vs 로컬
  "프로젝트 고유 사례" 섹션을 naming convention으로 명확히 분리. 위 F항
- **review 자동 감지 없음 → 실제 위반 놓침 가능성** — 사람이 눈치 못
  채면 rule이 있어도 위반이 커밋됨. 완화책: rule 체크리스트 강제 +
  self-verify 연계 + 본 규칙 원인 자체가 "한 달간 재편하면서도 못 봤다"
  라 review 자동화가 있었어도 잡았을지 불확실. 인지 도구(rule)로 사람
  질문 품질 향상이 더 효과적이라 판단

## 다운스트림이 받을 것 (충돌 없음)

| 항목 | OK 사유 |
|---|---|
| 범용 rule 파일 | Issen 현재 파일 100줄을 일반화. 기능 유지 |
| CLAUDE.md `<important if>` | 조건 트리거, 파이프라인 작업 아니면 무시 |
| self-verify 연계 | 기존 self-verify.md 흐름에 체크리스트 추가만 |
| 업스트림 사료 참조 | 역사적 맥락 공유 |

## 별도 이슈 (본 WIP 스코프 밖)

**review 과잉 사용 재검토** — 2026-04-21 사용자 피드백:
- deep 호출이 너무 잦아 커밋 속도 5배+ 저하 체감
- 최근 커밋 대부분 deep이지만 실제 block 비율 낮음
- `S2 단독`(문서형 rules 수정)도 deep 강제인 게 원인 추정

별도 WIP(`harness--hn_review_staging_rebalance.md`) 파서:
1. 최근 10~20 커밋 review verdict 통계
2. deep 호출 중 실제 block 비율 측정
3. staging 룰 재조정 (예: S2 단독은 standard로 강등, S2 + 로직 변경만
   deep)

본 pipeline-design 이식과는 독립 주제이므로 분리.

## 메모

### 업스트림 rule 파일의 배경 섹션 후보 문구

```
## 배경

다단 처리 파이프라인에서 자주 발생하는 설계 실수:
어떤 단계가 풍부한 중간 신호(여러 축을 통합한 스코어 등)를 계산해
**한 번의 결정**에만 사용하고 **출력 구조에서 폐기**. 뒷 단계가 같은
축의 판단을 다시 해야 할 때 **열등한 정보로 재계산**하게 됨.

이 실수는 여러 차례 재설계를 거쳐도 발견하기 어렵다. 각 재편이 독립적
으로 합리적으로 보이지만, 공통 전제("상류에서 계산된 풍부한 신호는
이 단계에 필요 없다")가 틀렸기 때문. 한 달 이상 재편하면서도 이 패턴
을 의심하지 않은 실측 사례가 여러 프로젝트에서 관찰됨.

실제 발생 사례는 각 프로젝트의 `docs/incidents/*_pipeline_origin*`
참조. 업스트림이 이 규칙을 정립한 최초 사례: `docs/incidents/
hn_pipeline_design_rule_origin.md`.
```

### 파일명·도메인 판정

- 파일명: `hn_pipeline_design_rule.md` (본 WIP). decisions/로 이동 시
  같은 이름
- 도메인: `harness` (규칙 자체가 하네스 영역)
- 신설 규칙 파일 위치: `.claude/rules/pipeline-design.md` (rule은 파일명
  prefix 없음 — rules/ 하위는 이미 도메인 함축)
- review agent 파일: `.claude/agents/review.md` (기존 파일 수정)

### 결정 F의 "프로젝트 고유 사례" 섹션 규약

harness-upgrade는 업스트림 소유 섹션만 덮어씀. rules/pipeline-design.md
하단에 다음과 같이 명시:

```
## 프로젝트 고유 사례 (로컬, harness-upgrade 보존)

<!-- 이 섹션 아래는 프로젝트별 커스터마이징 영역.
     harness-upgrade는 덮어쓰지 않는다. -->

- (다운스트림이 자기 사례·파일 링크 추가)
```

naming.md의 "파일명 — 확장 (프로젝트 고유)" 섹션과 같은 패턴.

### 미확정 — 별도 질문 필요

- pipeline을 naming.md에 신 도메인(`pl`)으로 등록할지 vs `harness` tag로
  둘지. 현재는 `harness` 도메인 + `pipeline` tag 권장 (rule은 하네스
  영역, 내용이 파이프라인 주제)
- review 패턴 10번의 구체 감지 로직 — 현재는 개념만. 실제 구현은 이식
  단계에서 review.md Read 후 결정
