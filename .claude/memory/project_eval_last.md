---
name: eval-last-result
description: 마지막 /eval --harness 실행 결과 (덮어쓰기, 누적 아님)
type: project
---
실행: 2026-05-08 (모드: --harness)

## 거시

방향 유지 ✅ — P5 과집중(16건)·P7 미완독은 이미 CPS 본문에 명시됨 (Wave B 대상).

## 단기 블로커

1. **박제 의심 — `incidents/hn_sealed_reopen_false_block.md` S6 인용**:
   `"pre-check이 AC 필수 필드 누락·completed 봉인 위반·dead link를 commit 전에 차단 (부분)"`
   - CPS S6 본문에 "pre-check"·"completed 봉인" 표현 부재 → substring 매칭 실패
   - 출처: 직전 v0.38.4(28ef587) 작성. 이번 finalize commit이 잔여 상속
   - 처리 옵션:
     - (a) 인용을 S6 실제 substring으로 교체 (예: "review 카테고리 8 — ...")
     - (b) CPS S6에 7번째 방어 레이어로 본 사고 추가 (Solution 메커니즘 변경 — owner 승인 필요)

2. **`eval_cps_integrity.py` Windows cp949 인코딩 결함**:
   - `PYTHONIOENCODING=utf-8` 없이 실행 시 emoji `✅` 출력에서 `UnicodeEncodeError` 즉시 fail
   - CLAUDE.md `## 환경` "Windows + Git Bash 주 개발 환경" 전제 위반
   - 위치: `.claude/scripts/eval_cps_integrity.py:323` (`print(f"- NEW 플래그 미처리: 0건 ✅")`)
   - 해결 방향: 스크립트 진입점에서 `sys.stdout.reconfigure(encoding='utf-8')` 강제 (또는 emoji 제거)

## 장기 부채

- **CPS Problem 인플레이션 (7개 > 임계 6)** — P5(컨텍스트 팽창)·P7(미완독 회피)가 "상호 악화" 관계. 진단 가치는 분리 시 더 크지만, 임계 초과 자체는 모니터링 신호. 6개월 단위 병합 검토.
- **인용 0건 Problem: P4** — bash-guard.sh 차단 성공이 너무 잘 작동해 인용 안 됨(역설). CPS 본문에 운용 약점으로 명시됨. signal_defense_success.md 8건 기록이 활성 증명. 정상 정체.

## 다음 행동

- 블로커 1: `/write-doc` — 박제 인용 정정 결정. owner(nnkann) 판단 필요 (옵션 a vs b)
- 블로커 2: `/implementation` — `eval_cps_integrity.py` Windows 인코딩 별 wave 신설. CPS P# 매칭 후보: P3(다운스트림 사일런트 페일)·P6(검증망 스킵) 또는 NEW
