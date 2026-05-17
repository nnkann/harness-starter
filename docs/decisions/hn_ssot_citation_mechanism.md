---
title: SSOT 인용 원칙 — CPS 채널 적용 + verify-relates 스코프 확장 설계
domain: harness
problem: [P6, P8, P11]
s: [S6, S8, S9]
tags: [ssot-citation, cps, verify-relates, p11, rel-references]
relates-to:
  - path: decisions/hn_p11_gate_promotion.md
    rel: extends
status: completed
created: 2026-05-17
updated: 2026-05-17
---

# SSOT 인용 원칙 — 적용·작동 설계

## 0. 박제 — v0.48.0 한계 직시

v0.48.0이 박은 것:
- ✅ `rules/docs.md`에 "SSOT 인용 원칙" 원칙문 박제
- ✅ 본문 복제 9곳 1회 정리 (drift 한 번 청소)
- ❌ **CPS `rel: references` 그래프에 실제로 박힌 link 0개**
- ❌ **verify-relates가 `docs/` 폴더만 검사 — 본 wave 변경 8 file 추적 불가**
- ❌ **미래 본문 복제 재발 시 잡을 메커니즘 0**

= 원칙 선언만, 작동 메커니즘 0. 본 wave는 v0.48.0 박제의 **메커니즘 활성화**.

## 1. Goal

SSOT 인용 원칙을 CPS 채널과 실제로 연결해 결정적 작동시킨다.

## 2. CPS 적용 — 어떻게 CPS인가

### 2.1 기존 CPS 필드 매핑

| 필드 | 기존 의미 | SSOT 인용 적용 |
|---|---|---|
| `problem: P11` | 동형 패턴 잠복 | 본문 복제 = P11 재발 원인 (frontmatter 명시) |
| `s: [S9]` | 주관 격리 다층 검증 | rel: references 그래프 = 다층 검증 채널 |
| `relates-to: rel: references` | SSOT 참조 link | **본 메커니즘 본체**. 본문 복제 대신 박는 곳 |
| `rel: extends` | 본문 확장 | 다른 SSOT 본문을 확장할 때 (cascade 영향 명시) |

### 2.2 새 필드·새 규칙 없음 — 기존 채널 활성화만

본 wave는 **새 메커니즘 신설 X**. 이미 존재하는 4개 자산 활성화:

1. **`relates-to: rel: references`** — frontmatter 필드 (이미 정의됨, rules/docs.md)
2. **`verify-relates`** — cascade 검사 게이트 (이미 존재, docs_ops.py L590)
3. **`rules/docs.md` "SSOT 인용 원칙"** — 작성 규칙 (v0.48.0 박제)
4. **wiki 그래프 모델** — domain·tag·relates-to 본질 박제 (v0.47.5)

### 2.3 사용자 행동 흐름 (작동 시나리오)

**시나리오 1**: 새 문서 작성 시 SSOT 본문 인용
```yaml
# README.md 또는 SKILL.md frontmatter (장기적으로 frontmatter 도입)
relates-to:
  - path: .claude/rules/docs.md
    rel: references
    section: "프론트매터 — wiki 그래프 모델"
```
```markdown
# 본문
문서 간 관계는 `relates-to` 필드로 명시. 정의는 위 references SSOT.
```

**시나리오 2**: SSOT 위치 이동·이름 변경
- 사용자가 `rules/docs.md` 섹션 rename
- `verify-relates` 실행 → `rel: references` 박힌 모든 문서의 `path`·`section`
  검증 → 깨진 link 표시
- 사용자가 cascade 갱신

**시나리오 3**: 본문에 복제 시도
- LLM/사용자가 "4종 (X·Y·Z·W)" 복제 박으려 함
- (a) `rules/docs.md` "SSOT 인용 원칙" 본문이 시스템 프롬프트에 적재 → LLM 회피
- (b) 미래 review agent가 검사 (옵션) — 본 wave 스코프 외

## 3. verify-relates 스코프 확장 (§A)

### 3.1 현재 한계

```python
# docs_ops.py L592
for md in sorted(DOCS_DIR.rglob("*.md")):
```

`DOCS_DIR = "docs"` — `docs/` 외부 파일 검사 안 됨. 본 wave 변경 8 file
(`.claude/rules/`·`.claude/agents/`·`.claude/skills/`·`README.md`)는 전부
검사 대상 밖. **wiki 그래프 일원인데 그래프 추적에서 배제됨**.

### 3.2 확장 설계

**스코프**:
```python
SCAN_ROOTS = [
    DOCS_DIR,                           # 기존
    REPO_ROOT / ".claude" / "rules",    # 9개 rule
    REPO_ROOT / ".claude" / "skills",   # 12개 skill
    REPO_ROOT / ".claude" / "agents",   # 8개 agent
    REPO_ROOT / "README.md",            # root
    REPO_ROOT / "CLAUDE.md",            # root
]
```

**필터**: frontmatter `---` 블록 있는 파일만 (relates-to 박을 수 있는 형식).
agents description 같은 frontmatter는 이미 있음 (advisor.md L1-6).

**resolve 경로**:
- `docs/X.md` (현재) — 기존 동작 유지
- `.claude/rules/X.md` — 절대 prefix
- `rules/X.md` (단순) — `.claude/rules/X.md`로 해석 (관행)

### 3.3 게이트 동작

- starter (`is_starter: true`): 깨진 references 1건이라도 commit 차단
- 다운스트림 (`is_starter: false`): warn-only (v0.47.11 격리 사상 정합)

### 3.4 회귀 보호

- `@pytest.mark.docs_ops` 신규 케이스 3건:
  - `.claude/rules/`에 frontmatter + rel: references 박힌 파일 → 검사 작동
  - 깨진 references → 차단 (starter) / 경고 (다운스트림)
  - frontmatter 없는 파일 → skip (false positive 0)

## 4. 본 wave 변경 8 file에 실제 `rel: references` 박제 — 보류

본 wave 스코프에는 **메커니즘 활성화만**. 실제 link 박제는 다음 wave 또는
운용 중 자연 진화:

| 위치 | 이유 |
|---|---|
| `README.md`·`SKILL.md` frontmatter 도입 | 분량 큼, 다운스트림 cascade 영향 — 별 wave |
| agents description frontmatter `relates-to` 추가 | description 라인 수 증가 — 검토 필요 |

본 wave는 "메커니즘이 존재하고 작동한다" 증명까지. 실제 8 file 박제는
v0.48.x 추가 wave에서.

## 5. 한계 박제 (§C — 정직)

본 wave도 완전한 P11 해결 아님:

1. **`rel: references` 박제 강제 메커니즘 부재**: 사용자/LLM이 본문 복제
   대신 frontmatter 박제를 의식적으로 선택해야 함. 자동 강제 0.
2. **본문 표현 단속 폐기 결정 유지** (v0.48.0 §C): `_DEAD_REF_PATTERNS`에
   본문 표현 등록 안 함. SSOT 원칙 + verify-relates만으로 단속.
3. **운용 데이터 누적 필요**: 본 메커니즘 활성화 후 1~3 wave 운용 → drift
   재발 빈도 측정 → 추가 강제 필요성 판정.
4. **다운스트림 적합도 미검증**: starter에서 활성화 후 다운스트림 실측 보고
   기다림.

## 6. Acceptance Criteria

**Acceptance Criteria**:
- [x] Goal: SSOT 인용 원칙 메커니즘 활성화 — S6·S8·S9 cascade 충족.
  - verify-relates 스코프 확장 (`.claude/` + README + CLAUDE)
  - frontmatter 검사 필터 (없으면 skip — false positive 0)
  - is_starter 분기 (starter 차단 / 다운스트림 warn-only)
  - test 회귀 보호 3건
  검증:
    tests: pytest .claude/scripts/tests/test_pre_commit.py -m docs_ops -q
    실측: verify-relates 실행 후 결과 출력 + starter에 임의 깨진 reference
          박제 후 차단 시연 + 다운스트림 모드 시뮬레이션 후 warn-only 확인
- [x] docs_ops.py `cmd_verify_relates` 스코프 확장 + frontmatter 필터
- [x] is_starter 분기 추가 (HARNESS.json 참조)
- [x] test 3건 신규 (정상·깨진 reference·frontmatter 없음 skip)
- [x] pre-check이 verify-relates 결과 흡수 (이미 §3.5에서 호출하면 자동)
- [x] 본 wave 변경 8 file 박제는 별 wave로 분리 (메모에 명시)
- [x] 한계 4건 정직하게 박제 (§5)

## 8. 적용 결과

- `docs_ops.py cmd_verify_relates`가 `docs/` 외에 `.claude/rules`, `.claude/skills`, `.claude/agents`, `README.md`, `CLAUDE.md`를 스캔한다.
- frontmatter 없는 파일은 `relates-to` 본문이 있어도 skip한다.
- `rules/...`, `skills/...`, `agents/...` 단축 경로는 `.claude/...`로 해석한다.
- pre-check 전수 게이트는 starter에서 차단, 다운스트림에서 warn-only로 분기한다.
- 회귀 테스트 추가:
  - `.claude/rules` 정상 reference 통과
  - `.claude/rules` broken reference starter 차단
  - 다운스트림 broken reference warn-only
  - frontmatter 없는 `.claude` 파일 skip

## 9. 검증

- `python -m pytest .claude/scripts/tests/test_pre_commit.py::TestVerifyRelatesPrecheck -q` → 6 passed
- `python -m pytest .claude/scripts/tests/test_pre_commit.py -m docs_ops -q` → 31 passed, 76 deselected
- `python .claude/scripts/docs_ops.py verify-relates` → 미연결 relates-to 0건

## 7. 다음 wave 후보 (CPS case에 박제, 본 wave 분리)

- 본 wave 8 file에 실제 `rel: references` frontmatter 박제 (분량 큼)
- `_DEAD_REF_PATTERNS` 파일/경로 등록도 SSOT 자동 추출(`git ls-tree`) 검토
- review agent prompt에 "본문 list 복제 검사" 추가 (옵트인 메커니즘)
