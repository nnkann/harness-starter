---
title: harness-starter CPS — C 판단 프롬프트
domain: harness
tags: [cps, kickoff]
status: in-progress
created: 2026-04-20
updated: 2026-05-14
---

# harness-starter CPS (C 판단 프롬프트)

> **자라지 않음**. 새 작업이 들어오면 C(맥락) 판단을 위한 짧은 감각 도구.
> wave별 case 박제는 `docs/cps/cp_{slug}.md` + git history.
> 자세히: `docs/decisions/hn_harness_73pct_cut.md` §S-1.
> 압축 전 491줄 본문: `docs/archived/hn_kickoff_pre_73pct_cut.md`.

## Context (이 프로젝트는 무엇인가)

AI 코딩 에이전트(Claude Code) 행동을 **빠르게 도와주는** 도구 모음.
통제 강제 폐기, 결정적 게이트 + 사용자 가속만 유지. 다운스트림은 이식·
업그레이드해서 사용. 단일 관리자(nnkann), Windows + Git Bash, 실험 단계.

## Problems (해결해야 할 핵심 — 자라는 목록)

| ID | 1줄 요약 |
|----|---------|
| P1 | 근거 없는 추측 실행 |
| P2 | review 과잉 비용 |
| P3 | 다운스트림 사일런트 페일 |
| P4 | 광역 hook 매처 fragility |
| P5 | MCP·플러그인 컨텍스트 팽창 |
| P6 | 검증 책임 우회와 거짓 완료 |
| P7 | 시스템 관계·소유권·출력 계약 불투명 |
| P8 | 자가 발화·memory·reminder 의존 실패 |
| P9 | 정보 오염의 관성 |
| **P10** | **본질 미정 (catch-all, 다음 정련 후보 누적) — 강한 기준 적용** |
| P11 | 동형 패턴 잠복 — 후보 위치 미탐색 + sub-task 분리 우회 금지 (v0.51.4 P12 흡수) |

> 추가는 `python .claude/scripts/docs_ops.py cps add "1줄"`. 새 P# 자유.
> 정의·증상·진입조건 본문: `docs/archived/hn_kickoff_pre_73pct_cut.md`.

## Solutions (자라는 목록)

각 S#의 **해결 기준**은 AC 작성 시 SSOT. AC `검증.실측`은 이 기준에
부합하도록 작성. 단 substring 본문 인용 금지 — wave는 자기 시점 결정만
박제 (자라는 시스템).

| ID | 대상 P# | 1줄 메커니즘 | 해결 기준 |
|----|---------|------------|----------|
| S1 | P1 | 규칙 + 자동 차단 + 우회 장치 | 같은 파일을 근거 없이 3회 이상 수정하는 패턴이 세션당 0건. pre-check이 추측 수정 차단 시 에이전트가 즉시 관찰→재현 흐름으로 전환 |
| S2 | P2 | 패턴 → 행동 매핑 + hard 상한 | review tool call 평균 ≤4회. maxTurns 소진 verdict 누락 0건. docs-only 커밋이 skip/--no-review로 분류 |
| S3 | P3 | 5중 방어 | 새 버전 릴리즈 시 MIGRATIONS.md에 해당 버전 섹션 존재. 다운스트림 permissions.allow가 upstream과 동기화. downstream-readiness.sh 누락 0건 |
| S4 | P4 | 단일 hook + 금지 규칙 | `bash -n` 같은 정당 명령 hook 차단 0건. settings.json diff argument-constraint 패턴 추가 시 review 차단 |
| S5 | P5 | 압축 + 최소화 | 서브에이전트 spawn 컨텍스트 < 500k 토큰. SKILL.md·rules MVR(최소 필수 규칙셋) 적용 |
| S6 | P6 | 검증 책임 위치 고정 + 증거 구분 | AC `검증.tests`·`검증.실측`이 현재 wave에서 닫힘. 무관 테스트 통과·도구 실종·자동 검증 불가가 완료 증거로 포장되지 않음. SKILL.md·rules 변경 커밋은 필요한 pytest 또는 명시적 실측 기록 존재 |
| S7 | P7 | wiki 그래프 + 소유권·출력 계약 명시 | cluster/tag/relates-to 정합. `defends:`·`serves:`가 유효 P/S를 가리킴. upstream/downstream·owner 승인권·hook/stdout/status 출력 의미가 문서나 규칙에 드러남 |
| S8 | P8 | 강제 트리거 우선 + reminder 상태화 | 자가 발화·memory·reminder 의존 신호가 WIP, signal_*, hook 출력, pre-check 중 하나의 상태로 남음. "나중에" 항목은 owner·조건·재호출 지점 없이 사라지지 않음 |
| S9 | P9 | 주관 격리 + 다층 검증 + 회귀 가드 기본값 | 라벨·count·PASS·자가 선언·오래된 memory가 단독 증거로 쓰이지 않음. P9가 primary면 회귀 테스트 또는 재오염 방지 실측이 AC에 존재. frontmatter `problem`·`s` ↔ CPS 번호 매칭 100%. AC 체크박스 형식 강제. 매칭 누락 시 commit 차단 |
| **S10** | **P10** | **본질 의심 — 면밀 비교 + 정련 후보 누적** | **박는 조건 (엄격)**: P1~P9 각각 검토 후 어디에도 명확히 안 맞을 때만. "잘 모르겠음·귀찮음·빠르게 넘기고 싶음"은 부적합. wave 안에서 **의심 근거 1줄 박제 의무** (단순 "안 맞음" 금지) + 가장 가까운 P#·S# 후보 1개 동반 선택. 다음 wave가 패턴 누적 보면 P10 재분류 또는 새 P# 분리. **혼용 시 본질 신호 희석 — 신중 사용** |
| S11 | P11 | 동형 후보 위치 자동 탐색 + 단일 wave 통합 처리 + 코드 SSOT 단일 진입점 강제 | 1차 발견 시 같은 구조의 후보 위치 탐색 의무. **본 wave 영역 안 발견 항목은 본 wave에서 처리 — sub-task 별 WIP 분리 금지** (v0.51.4 P12 흡수). 같은 로직 3곳 이상 → core 모듈 추출. `.claude/rules/code-ssot.md` 규칙 |

## CPS 사용 흐름

1. 새 작업 발화 → C(맥락) 1줄 추출
2. 위 표에서 P# 매칭 (단일/중복/신규)
3. S 결정
4. WIP에 C → P → S → AC 연결 근거 3줄 박제
5. implementation Step 2 정합 substep (자동) — C·P·S 어긋남 감지
6. 확정 후 cascade — implementation → test → /commit
7. /commit 시 `docs/cps/cp_{slug}.md` 박제 (frontmatter c·tags·p·s·result)

### C-P-S-AC 연결 계약

- **C**: 작업이 시작된 날것의 관찰·사용자 발화·실측. 나중에 P#가 바뀌어도
  재분류할 수 있게 보존한다.
- **P**: C에서 드러난 반복 실패 메커니즘. 표면 증상이나 해결책 이름이 아니다.
- **S**: 해당 P를 줄이는 운영·기술 메커니즘. S 정의 변경은 owner 승인 필요.
- **AC**: S가 실제로 작동했다는 증거. 각 S#가 AC 안에 등장해야 하며,
  `검증.tests`·`검증.실측`은 S의 해결 기준을 직접 증명해야 한다.

WIP 본문 권장 형식:

```markdown
## CPS Rationale

- C → P: <왜 이 관찰이 이 P#인가>
- P → S: <왜 이 S#가 해당 P를 줄이는가>
- S → AC: <AC가 S의 해결 기준을 어떻게 증명하는가>
```

## 빠른 조회

```
python .claude/scripts/docs_ops.py cps list           # P# 1줄 요약
python .claude/scripts/docs_ops.py cps show P8        # P# 정의 + 관련 case
python .claude/scripts/docs_ops.py cps cases --p P8   # P8 관련 case
python .claude/scripts/docs_ops.py cps stats          # P# 분포
python .claude/scripts/docs_ops.py cps add "1줄"      # 새 P# 등록
```

## 운영 원칙

- 매칭 강제 없음. 자라는 시스템 — 다음 wave가 새 P# 자유 추가
- frontmatter 인용 50자 박제 검사 폐기 (번호만)
- kickoff 자라지 않음 — 정련은 옵트인 (연 1회 정도)
- `/cps-check` 옵트인 — 사용자 명시 호출 시 정합 검사 단독 실행

### P11 — 동형 패턴 잠복 + sub-task 분리 우회 금지

같은 의미의 로직·필드·결정이 여러 위치에 분산된 상태에서 한 곳만
고치고 나머지 후보 위치를 자동 탐색하지 못하면 drift가 잠복한다.

대표 표면 — field lifecycle:
- field normalization (파싱·정규화가 여러 진입점에 분산)
- representative derivation (Record/배열에서 "현재 대표값" 임시 파생)
- persistence entry points (DB 저장 로직이 호출부마다 흩어짐)

**sub-task 분리 우회 금지** (v0.51.4 P12·S12 흡수):
- 본 wave 영역 안에서 발견된 항목은 본 wave에서 처리. 별 WIP로 분리
  금지 (specification gaming 회피 통로 차단)
- 분리는 **다른 영역·다른 의사결정 단위·다른 시점**일 때만
- LLM 자가 점검("강제 최소화"·"분리 정당") 환각이 P11 게이트 회피
  통로로 작동한 실측 사례: `docs/cps/cp_split_completion_p12.md`

방어: `.claude/rules/code-ssot.md` (3+ reference rule · derived pointer
pattern · new field pre-checklist + Surgical Changes 충돌 해소).
1차 발견 시 동형 후보 위치 탐색 의무 + 본 wave 통합 처리 의무.

<!-- v0.51.4: P12·S12 폐기. P11에 흡수.
사례 박제는 docs/cps/cp_split_completion_p12.md에 잔류 (P11 첫 회피 사례).
폐기 결정 근거: codex·gemini 재검토 — P12 "강제 금지·유도만"이 P11 게이트
("발견=박제+다음 wave 의무") 회피 통로로 작동. P12 박제 직후 후속 wave에서
LLM이 정확히 P11 우회 실측. -->
