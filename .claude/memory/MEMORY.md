# MEMORY

## feedback / project

- [eval-deep-secret-scan-enforcement](feedback_eval_secret_scan.md) — archive 후보도 시크릿 스캔 필수 (2026-04-18 dev-tools 사고 기반)
- [posix-path-in-write-tool](feedback_posix_path_in_write_tool.md) — Windows에서 Write/Edit/Read tool에 `/tmp` 같은 POSIX 경로 금지 (Bash tool만 shim 통해 치환됨)
- [마지막 eval 결과](project_eval_last.md) — 2026-05-08 실행 (--harness)

## reminder — 반복 패턴 회상

`reminders/reminder_*.md`가 신규 표준. 루트 `reminder_*.md`와 `signal_*.md`는 legacy alias로 읽되 신규 생성하지 않는다.
SessionStart는 상태·domain·stale 여부를 보고 제한적으로 노출한다. `kv_group`이
있으면 현재 WIP query와 맞는 bucket을 먼저 정렬하지만, 사실 판단이나 검증 결론은
캐시하지 않는다.

- [/commit AC 체크박스 갱신 생략](reminders/reminder_ac_skip_on_commit.md) — "이미 완료" 암묵 신호로 작동
- [/commit 스킬 우회 → commit_finalize.sh 직접 호출 반복](reminders/reminder_commit_skill_bypass.md)
- [리팩토링 후 dead code 잔존 반복](reminders/reminder_dead_code_after_refactor.md)
- [bash-guard 차단 성공 기록 (P4 방어 활성)](reminders/reminder_defense_success.md) — eval_harness section_defense_record 참조
- [review 기본 skip 정책 재검토](reminders/reminder_review_default_skip_risk.md)
- [review 에이전트 verdict 단어 누락 반복](reminders/reminder_review_verdict_omission.md)
- [자동화 불가 검증을 자동화한 듯 포장하는 단락 패턴](reminders/reminder_unautomatable_check_shortcircuit.md)
- [WIP 이동 시 역참조 dead link 생성 반복](reminders/reminder_wip_move_dead_link.md)
