# Memory 활용 규칙

defends: P8

세션 간 지속 정보 저장소. 세션 내 동적 snapshot은 별도.
memory는 판단의 원자료가 아니라 reminder·회상 보조 신호다. memory count,
라벨, 오래된 reminder/signal을 근거로 사실을 단정하지 않는다.

## 두 종류

### 실제 Claude memory (`~/.claude/`, Anthropic 관리)

사용자 개인 성향·선호 + Claude 자체 실수 패턴. **프로젝트 repo에 저장 X**.

### 프로젝트 memory (`.claude/memory/`, git 추적)

조건: **다른 사람·다른 Claude 세션이 읽어야 의미 있음**.
- 프로젝트 관행·hard-won lessons
- 다운스트림이 상속받아야 할 운영 교훈

**사용자 개인 성향은 여기에 저장 X**.

## 경로

- 디렉토리: `.claude/memory/`
- 인덱스: `.claude/memory/MEMORY.md` (세션 시작 자동 로드)
- 동적 snapshot: `.claude/memory/session-*.txt` (gitignore)

## 동적 snapshot — 3개 파일 (확장 금지)

| 파일 | 내용 | write | read |
|------|------|-------|------|
| `session-pre-check.txt` | pre-check stdout | Step 5 직후 background | git hook 커밋 메시지 주입 |
| `session-start-unstaged.txt` | SessionStart `git diff --name-only` | SessionStart hook | pre_commit_check.py prior_session_files |
| `session-moved-docs.txt` | `docs_ops.py move` 완료 경로 | move 완료 직후 | pre_commit_check.py 봉인 면제 판정 |

**라이프사이클**: commit 성공 → 스킬 끝에서 `rm -f .claude/memory/session-*.txt`.

## reminders/reminder_* 파일 스키마

`reminder`는 독립 기능이 아니라 project memory의 **1급 하위 타입**이다.
역할은 "사실 저장"이 아니라 현재 작업에서 다시 떠올릴 후보를 제한적으로
노출하는 것. SSOT는 이 문서이며, session-start.py는 이 계약의 실행부다.

`.claude/memory/reminders/reminder_*.md` — 반복 패턴·후속 판단 회상 리마인더.
frontmatter 필드:

```yaml
---
reminder: <1줄 — 다시 떠올릴 판단/패턴 본질>
domain: harness
keywords: [회상-키워드]
strength: weak | medium | strong
candidate_p: P#  # 가까운 CPS Problem (없으면 P10)
kv_group: <domain>/<candidate_p>/<workflow-or-risk-family>  # 선택. routing hint 전용
status: active | suppressed | archived
source: docs/decisions/... | docs/incidents/... | user | audit
owner: human | codex | harness
last_validated: YYYY-MM-DD  # 권장. 마지막으로 현재 코드/문서와 대조한 날
valid_until: YYYY-MM-DD     # 권장. 이 날짜 이후 stale 후보
---
```

본문은 자유 형식. 루트 `reminder_*.md`와 `signal_*.md`는 기존 이름과 호환되는
legacy alias로 읽는다. 새 항목은 `reminders/reminder_*.md` + `reminder:` 필드를 사용한다. 운용 로그 누적
(`reminder_defense_success.md` 패턴)도 허용 — strength·candidate_p가 메타로
작동. `last_validated`·`valid_until` 없는 기존 reminder/signal은 허용하되,
오래된 항목은 사실이 아니라 재확인 후보로 읽는다.

`kv_group`은 Phase 1.5 grouped active reminder용 선택 필드다. Transformer
GQA/MQA 비유처럼 여러 현재 작업 query가 같은 memory bucket을 공유하게 하지만,
하네스에서는 **필터가 아니라 boost/rank/cap hint**로만 쓴다. group이 맞지
않는 eligible reminder를 숨기면 P8 방어가 깨진다.

권장 형식:

```text
<domain>/<candidate_p>/<workflow-or-risk-family>
```

예:

- `harness/P8/review-commit`
- `harness/P9/stale-memory`
- `harness/P8/session-start`
- `harness/P9/ssot-validation`

피할 것:

- `harness/P8`처럼 너무 큰 group
- 파일 경로 기반 group
- `review-skip-is-dangerous` 같은 결론형 group

### 하네스 레이어별 KV 계약

하네스의 KV는 attention 구현이 아니라 운영 key 전달 계약이다. K는 여러 레이어가
공유해도 되지만, V 판단은 각 레이어에서 새로 계산한다.

| Layer | 역할 | 공유 가능한 K | V |
|------|------|---------------|---|
| L0 SessionStart | 현재 세션 상태 수집 | git 상태, WIP domain | 출력 snapshot |
| L1 CPS | 문제·해결 기준 선택 | `P#`, `S#`, domain | 해결 기준 |
| L2 Docs graph | SSOT 후보 찾기 | domain, tags, relates-to | owner 문서 경로 |
| L3 WIP/AC | 이번 wave 완료 기준 | problem, s, AC | 실행·검증 약속 |
| L4 Reminder | 회상 후보 선택 | `kv_group`, candidate_p, keywords | reminder 1줄 |
| L5 Skill/Agent | 처리자 선택 | trigger, risk type | skill/agent 계약 |
| L6 Verification | 완료 증거 판정 | staged files, AC, P/S | pass/block/stage |
| L7 Commit | 영속화·전파 | changed component | commit log, downstream 안내 |
| L8 Eval/Promotion | 반복 패턴 판단 | incidents, audit, stale signals | promote/archive 후보 |

구분:

- structural KV: `domain`, `P#`, `S#`, `tags`, owner path
- routing KV: `kv_group`, workflow, risk-family
- evidence KV: tests 결과, pre-check 결과, review 결과, 실측

evidence KV는 reminder cache나 `kv_group`으로 공유하지 않는다. reminder가 뜬 것은
SSOT 확인 후보이지 검증 결론이 아니다.

### reminder lifecycle

| 단계 | 의미 | 처리 |
|------|------|------|
| 생성 | 반복 위험·후속 판단 후보 발생 | `reminders/reminder_*.md`, `status: active` |
| 승격 | 반복 발생·incident 연결·강한 노출 필요 | `strength` 상향, `source` 보강 |
| 만료 | 날짜·코드 변경으로 stale 가능 | `valid_until` 경과 시 stale 후보 표시 |
| 폐기 | 현재 코드/문서와 불일치 또는 무효 | `status: archived` |
| 병합 | 같은 회상 조건 중복 | 넓은 reminder 하나로 합치고 기존 archived |
| 억제 | 맞지만 현재 작업 노이즈가 큼 | `status: suppressed` 또는 keywords 축소 |

reminder가 장기 규칙이 되면 정식 WIP를 거쳐 `.claude/rules/*.md`나
decision/incident가 SSOT가 되고, reminder는 그 SSOT를 떠올리는 얇은 포인터로
축소한다.

### 관련 작업 흡수 + WIP 승격 계약

reminder는 backlog가 아니라 routing signal이다. 다음 조건이면 reminder 본문을
키우지 않고 관련 작업에 흡수하거나 `docs/WIP/` 정식 작업으로 승격한다.

- 본문이 길어져 결정 근거·사례·후속 조치가 섞인다.
- `strength: strong`인데 `source: user|audit` 또는 source 없음이라 owner SSOT가 약하다.
- 같은 `kv_group` active reminder가 4건 이상이라 병합/분리 판단이 필요하다.
- 같은 reminder가 반복 hit되어 규칙·결정·사고 중 하나로 승격해야 한다.

처리 우선순위:

1. **관련 WIP 흡수**: 현재 작업의 domain/problem/kv_group과 맞는 WIP가 이미 있으면
   새 WIP를 만들지 않는다. 해당 WIP의 AC·`## 메모`·`## 결정 사항` 중 맞는 위치에
   reminder 경로와 재확인 결과를 기록한다.
2. **새 WIP 승격**: 관련 WIP가 없고 독립 판단·검증 단위이면 `/implementation` 또는
   `/write-doc`로 WIP를 만든다.
3. WIP frontmatter `c:`에 reminder 경로와 관찰 1줄 기록
4. `problem`/`s`는 reminder의 `candidate_p`와 가장 가까운 S#에서 시작
5. 완료 후 `docs_ops.py move`로 decision/incident/guides 중 owner SSOT로 이동
6. 원 reminder는 `source`를 새 SSOT로 갱신하고, 필요하면 `status: archived` 또는
   얇은 pointer로 축소

`eval --harness` memory/reminder lint는 관련 WIP 흡수 또는 WIP 승격 후보를 warning/report로 출력한다.

### reminder 사용 계약

reminder·legacy signal·incident·audit 로그는 회귀 증거가 아니라 **환기 신호**다. 현재 작업에
적용하려면 3단계를 거친다.

1. **환기**: domain·keywords·candidate_p가 현재 C와 가까운 후보를 보여준다.
2. **재확인**: 현재 코드·문서·git log와 대조해 stale 여부를 판정한다.
3. **검증 선택**: 여전히 맞는 경우에만 AC `tests` 또는 `실측` 범위에 반영한다.

금지:

- stale reminder를 근거로 테스트 범위를 넓히기
- reminder count를 근거로 위험도를 단정하기
- "과거에 회귀가 있었음"만으로 현재 변경의 실패를 단정하기
- memory에 없다는 이유로 회귀 위험이 없다고 단정하기

memory/reminder가 과거 회귀를 띄웠지만 현재 코드와 맞지 않으면 P9 정보 오염
후보로 기록하고, 필요한 경우 signal의 `last_validated`·`valid_until`을 갱신한다.
과거 회귀가 문서에 있는데 작업 시점에 전혀 떠오르지 않았으면 P8 누락 후보로
보고 reminder·incident 키워드 또는 출력 조건을 보강한다.

### 2단계 운용

reminder는 무거운 지식 저장소가 아니라 SSOT 확인을 부르는 얇은 신호다.

1. **Light reminder**: SessionStart가 현재 WIP domain·status·strength·stale 여부로
   짧은 후보만 노출한다.
2. **SSOT 확인**: reminder를 근거로 바로 행동하지 않고, rules/skills/scripts/
   decisions/incidents/CPS owner를 확인한 뒤 AC·검증·구현에 반영한다.

긴 설명, 반복 로그, 영구 규칙은 reminder에 쌓지 않는다. 장기화되면 rules,
decision, incident 중 owner SSOT로 승격하고 reminder는 그 위치를 떠올리는 포인터로
축소한다.

### SessionStart 노출 규칙

- 기본 노출: `status: active`이고 현재 WIP `domain`과 일치하는 reminder.
- `strength: strong`: domain 불일치여도 최대 2건까지 보조 노출 가능.
- `kv_group`: 현재 WIP의 domain·problem·tags·변경 경로에서 파생한 query
  group과 일치하면 먼저 정렬한다. 최종 eligibility는 기존 status/domain/
  valid_until/strength 규칙으로 다시 계산한다.
- `status: suppressed | archived`: 기본 노출 금지.
- `valid_until` 경과: stale 후보로 표시하고 사실 증거로 쓰지 않는다.
- 루트 `reminder_*.md`와 `signal_*.md`: legacy alias로 읽되 신규 생성 금지.

### query group 계산

SessionStart는 WIP `domain`, `problem`의 `P#`, `tags`, WIP 파일명 token,
staged/unstaged 변경 경로 token에서 query group 후보를 파생한다.

기본 workflow/risk-family:

- `review-commit`
- `stale-memory`
- `session-start`
- `ssot-validation`

정렬은 group hit → non-stale → strength 순이다. 후보가 많을 때만 group별 cap을
적용하고, group mismatch는 숨김 사유가 아니다.

### frontmatter 보강 운영

기존 reminder/signal에 `kv_group`, `status`, `valid_until`, `last_validated`를
일괄 강제하지 않는다. 신규 reminder와 strong/active reminder부터 보강한다.
starter 본체의 legacy `signal_*.md`는 2026-05-21 memory cleanup에서
`reminders/reminder_*.md`로 승격했지만, downstream 호환을 위해 루트
`reminder_*.md`/`signal_*.md` 읽기 fallback은 유지한다.

누락·오타·과대 group·과소 group·stale 후보는 `eval --harness`의
memory/reminder lint에서 먼저 추천/경고로 보고한다. pre-check hard block은
오탐이 충분히 낮아진 뒤 별도 wave에서 검토한다.

## 출력 의미 계약

SessionStart·StopGuard가 memory를 노출할 때 count 단독 출력 금지.

- ✅ "reminder 3건: validated 1 / stale 후보 2"
- ✅ "memory 없음 — 자동 주입된 사실 없음"
- ❌ "메모리 4개 항목 로드됨"만 출력

count는 본문·검증 상태·stale 여부 없이 단독 근거가 될 수 없다.

## 누적 감사 로그 (snapshot과 별개)

snapshot은 commit마다 정리되지만 감사 로그는 **세션 횡단 누적**. gitignore.

| 파일 | 내용 | write | read |
|------|------|-------|------|
| `stop_hook_audit.log` | Stop hook A·B·C 신호 hit (timestamp + reason + WIP 경로) | stop-guard.py | eval --quick (누적 빈도 보고) |

확장 금지 — 새 누적 감사 로그는 본 표 추가 후 도입.

## 저장 대상

| 우선순위 | 타입 | 예시 |
|---|---|---|
| 1 | feedback | 사용자가 수정한 접근법 |
| 2 | project | 프로젝트 맥락·마감 |
| 3 | user | 사용자 역할·전문 분야 |
| 4 | reference | 외부 시스템 포인터 |

## 저장하지 않는 것

- 코드에서 읽을 수 있는 것 (구조·패턴·아키텍처)
- `git log`로 알 수 있는 것
- `CLAUDE.md`·`rules/`에 이미 있는 것
- 사용자 개인 성향 (→ 실제 Claude memory)

## 트리거

- 세션 시작: `MEMORY.md` 자동 로드
- 사용자 "기억해" 명시: 즉시 저장
- 세션 종료 직전: `stop-guard.sh`가 1줄 환기

memory와 현재 코드 충돌 시 현재 코드 신뢰, memory 업데이트.
memory가 현재 코드·git log·docs와 충돌하면 memory는 stale이다. stale 신호는
P9 정보 오염 후보로 보고, 현재 코드/문서 확인 없이 판단 baseline으로 쓰지 않는다.
