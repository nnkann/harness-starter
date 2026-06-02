"""스킬 라우팅/문서-도구 계약 회귀 가드.

느슨하게 결합된 스킬 문서와 docs_ops.py 요구사항이 서로 다른 SSOT를 말하면
다운스트림에서 계획 문서·WIP 이동이 뒤늦게 실패한다.
"""

from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]


def _read(rel: str) -> str:
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


@pytest.mark.routing
def test_plan_doc_before_code_routes_to_implementation_not_write_doc():
    """코드·테스트 개선을 앞둔 계획 문서는 implementation 계약으로 고정한다."""
    implementation = _read(".claude/skills/implementation/SKILL.md")
    write_doc = _read(".claude/skills/write-doc/SKILL.md")

    assert "코드·테스트·스크립트·룰 감사/개선을 위한 계획 문서" in implementation
    assert "먼저 계획 문서부터" in implementation
    assert "write-doc은 문서 자체가 최종 산출물" in implementation

    assert "코드 구현·감사·리팩토링·테스트 보강을 앞둔 계획 문서" in write_doc
    assert "write-doc이 아니라 implementation" in write_doc
    assert "문서 자체가 완료" in write_doc


@pytest.mark.routing
def test_wip_filename_contract_matches_docs_ops_move_prefix_requirement():
    """docs_ops.py move가 요구하는 WIP routing prefix를 스킬 문서가 반대로 안내하지 않는다."""
    docs_ops = _read(".claude/scripts/docs_ops.py")
    naming = _read(".claude/rules/naming.md")
    implementation = _read(".claude/skills/implementation/SKILL.md")
    write_doc = _read(".claude/skills/write-doc/SKILL.md")
    commit = _read(".claude/skills/commit/SKILL.md")

    assert "접두사 없음 (decisions--/guides--/cps--/... 필요)" in docs_ops
    assert "{대상폴더}--{abbr}_{slug}.md" in naming

    for text in (implementation, write_doc, commit):
        assert "{대상폴더}--{abbr}_{slug}.md" in text
        assert "라우팅 태그 폐기" not in text


@pytest.mark.routing
def test_cps_agent_learning_contract_is_documented():
    """subagent 호출과 역방향 CPS 신호가 implementation 계약에서 누락되지 않는다."""
    docs_rule = _read(".claude/rules/docs.md")
    memory_rule = _read(".claude/rules/memory.md")
    implementation = _read(".claude/skills/implementation/SKILL.md")
    agents_implementation = _read(".agents/skills/implementation/SKILL.md")
    advisor_skill = _read(".claude/skills/advisor/SKILL.md")
    agents_advisor_skill = _read(".agents/skills/advisor/SKILL.md")
    cps_learn = _read(".claude/skills/cps-learn/SKILL.md")
    agents_cps_learn = _read(".agents/skills/cps-learn/SKILL.md")
    harness_dev = _read(".claude/skills/harness-dev/SKILL.md")
    agents_harness_dev = _read(".agents/skills/harness-dev/SKILL.md")
    harness_upgrade = _read(".claude/skills/harness-upgrade/SKILL.md")
    agents_harness_upgrade = _read(".agents/skills/harness-upgrade/SKILL.md")
    codebase_agent = _read(".claude/agents/codebase-analyst.md")
    debug_agent = _read(".claude/agents/debug-specialist.md")
    review_agent = _read(".claude/agents/review.md")

    assert "### `trigger:`" in docs_rule
    assert "downstream cron 학습 신호" in memory_rule

    for text in (implementation, agents_implementation):
        assert "CPS flow type" in text
        assert "`reverse-solution`" in text
        assert "`reverse-evidence`" in text
        assert "`resume`" in text
        assert "CPS response policy" in text
        assert "새 라우팅 표가 아니라" in text
        assert "복수 `problem`은 중복이 아니라" in text
        assert "문제 차원 증가" in text
        assert "복수 `s`는 중복이 아니라" in text
        assert "실행 구조 증가" in text
        assert "단계화·반복·분리 검증" in text
        assert "호출 폭은 고정하지 않는다" in text
        assert "specialist 폭" in text
        assert "실행 단계·반복·검증 폭" in text
        assert "specialist별 trigger 표를" in text
        assert "runtime 선택 trace" in text
        assert "selected`(codex|agy|both|none)" in text
        assert "post-result`(fit|misfit|overcalled|undercalled)" in text
        assert "advisory-signal" in text
        assert "direct specialist first" in text
        assert "advisor를 관문으로 쓰지" in text
        assert "advisor-only 반복은 `overcalled`" in text
        assert "CPS packet" in text
        assert "downstream cron 학습 신호" in text

    assert "복수 `problem`·복수 `s`" in docs_rule
    assert "복수 `problem`은 문제 차원 증가" in docs_rule
    assert "복수 `s`는" in docs_rule
    assert "단계화·반복·분리 검증" in docs_rule
    assert "P#/S#별 새 라우팅 매트릭스" in docs_rule
    assert "새 metadata" in docs_rule

    for text in (advisor_skill, agents_advisor_skill):
        assert "단일 specialist로 끝나는 작업" in text
        assert "direct specialist first 판정 후" in text
        assert "Step 0.5" not in text

    for text in (cps_learn, agents_cps_learn):
        assert "복수 P# = 문제 차원 증가" in text
        assert "복수 S# = 실행 구조 증가" in text
        assert "P#가 만든 독립 문제 차원 수가 specialist 폭" in text
        assert "S#가 만든 해결 기준 수가 실행 단계·반복·검증 폭" in text
        assert "고정 라우팅 매트릭스 금지" in text

    for text in (codebase_agent, debug_agent, review_agent):
        assert "trigger:" in text
        assert "CPS 영향" in text

    for text in (harness_dev, agents_harness_dev, harness_upgrade, agents_harness_upgrade):
        assert "downstream 학습 신호" in text or "downstream guardian" in text
        assert "candidate-upstream-change" in text
        assert "cron 미진행 신호" in text


@pytest.mark.routing
def test_commit_push_contract_uses_noninteractive_shell_specific_commands():
    """push 단계가 Windows Codex에서 bash 래핑 대기로 빠지지 않게 고정한다."""
    claude_commit = _read(".claude/skills/commit/SKILL.md")
    agents_commit = _read(".agents/skills/commit/SKILL.md")

    for text in (claude_commit, agents_commit):
        assert "$env:GIT_TERMINAL_PROMPT='0'" in text
        assert "$env:GCM_INTERACTIVE='never'" in text
        assert "git push --porcelain origin main" in text
        assert "GIT_TERMINAL_PROMPT=0 GCM_INTERACTIVE=never HARNESS_DEV=1 git push --porcelain origin main" in text
        assert "bash -lc 'HARNESS_DEV=1 git push" in text
        assert "HARNESS_DEV=1 git push origin main" not in text
