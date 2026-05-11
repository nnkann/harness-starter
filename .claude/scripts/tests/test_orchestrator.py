"""orchestrator.py 회귀 가드.

defends: P9
serves: S9
trigger: orchestrator-regression

본 결정: docs/WIP/decisions--hn_orchestrator_mechanism.md
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "orchestrator.py"


def run_orchestrator(payload: dict, env_overrides: dict | None = None) -> subprocess.CompletedProcess:
    """orchestrator.py를 자식 프로세스로 실행. payload를 stdin JSON으로 전달."""
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=env_overrides or None,
    )


def import_orchestrator():
    """테스트마다 fresh import로 module-level 상태 오염을 피한다."""
    import importlib
    if "orchestrator" in sys.modules:
        del sys.modules["orchestrator"]
    sys.path.insert(0, str(SCRIPT.parent))
    return importlib.import_module("orchestrator")


@pytest.mark.orchestrator
def test_script_syntax_valid():
    """python -m py_compile 통과 — 구문 오류 회귀 가드."""
    result = subprocess.run(
        [sys.executable, "-m", "py_compile", str(SCRIPT)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"py_compile 실패: {result.stderr}"


@pytest.mark.orchestrator
def test_empty_stdin_no_crash():
    """빈 stdin이어도 crash 없이 exit 0."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input="",
        text=True,
        capture_output=True,
    )
    # 빈 입력 — 신호 없음 → exit 0
    assert result.returncode == 0, f"빈 입력 crash: {result.stderr}"


@pytest.mark.orchestrator
def test_no_target_path_no_signal():
    """tool_input에 file_path 없으면 P9 신호 없음."""
    payload = {"tool_name": "Bash", "tool_input": {"command": "ls"}}
    result = run_orchestrator(payload)
    assert result.returncode == 0


@pytest.mark.orchestrator
def test_wip_path_skip():
    """WIP 자체 수정은 P9 detect skip (자기 참조 회피)."""
    payload = {
        "tool_name": "Edit",
        "tool_input": {"file_path": "docs/WIP/decisions--hn_test.md"},
    }
    result = run_orchestrator(payload)
    # P1 카운터는 작동하나 P9 자기 참조는 skip → exit 0
    assert result.returncode in (0,)


@pytest.mark.orchestrator
def test_stdout_valid_json_when_signals_present(tmp_path, monkeypatch):
    """신호 발생 시 stdout이 유효 JSON."""
    # signal 파일 깨끗이
    payload = {
        "tool_name": "Edit",
        "tool_input": {"file_path": "src/foo.py"},
    }
    result = run_orchestrator(payload)
    # 신호 없으면 stdout 비어도 OK
    if result.stdout.strip():
        # 출력 있으면 JSON이어야
        data = json.loads(result.stdout)
        assert "hookSpecificOutput" in data


@pytest.mark.orchestrator
def test_signal_upsert_by_key():
    """`key` 필드 보유 신호는 upsert — 같은 key의 기존 신호 교체."""
    try:
        orch = import_orchestrator()

        existing = [
            {"p_id": "P1", "key": "P1:foo.py", "message": "3회"},
        ]
        new = [
            {"p_id": "P1", "key": "P1:foo.py", "message": "4회"},
        ]
        merged = orch.deduplicate_signals(new, existing)
        # upsert — 1개로 유지, message는 갱신
        assert len(merged) == 1
        assert merged[0]["message"] == "4회"
    finally:
        sys.path.pop(0)


@pytest.mark.orchestrator
def test_signal_dedup_without_key():
    """`key` 없는 신호는 (p_id, message) 기준 dedup — 동일 신호 추가 안 됨."""
    try:
        orch = import_orchestrator()

        existing = [{"p_id": "P9", "message": "same msg"}]
        new = [{"p_id": "P9", "message": "same msg"}]
        merged = orch.deduplicate_signals(new, existing)
        assert len(merged) == 1
    finally:
        sys.path.pop(0)


@pytest.mark.orchestrator
def test_gemini_skip_when_cli_absent(monkeypatch):
    """gemini CLI 미설치 환경에서는 detect_solution_change skip — graceful."""
    try:
        orch = import_orchestrator()

        # CLI 미설치 시뮬
        monkeypatch.setattr(orch, "gemini_cli_available", lambda: False)
        # Solutions 변경됐다고 시뮬
        monkeypatch.setattr(orch, "staged_solutions_changed", lambda: True)

        state: dict = {}
        signals = orch.detect_solution_change({}, state)
        # CLI 없으면 skip → 빈 신호
        assert signals == []
        # gemini_solution_review_called 플래그도 안 박힘
        assert not state.get("counter", {}).get("gemini_solution_review_called")
    finally:
        sys.path.pop(0)


@pytest.mark.orchestrator
def test_gemini_skip_when_no_solution_change(monkeypatch):
    """staged Solutions 변경 없으면 detect_solution_change skip."""
    try:
        orch = import_orchestrator()

        monkeypatch.setattr(orch, "gemini_cli_available", lambda: True)
        monkeypatch.setattr(orch, "staged_solutions_changed", lambda: False)

        state: dict = {}
        signals = orch.detect_solution_change({}, state)
        assert signals == []
    finally:
        sys.path.pop(0)


@pytest.mark.orchestrator
def test_gemini_background_uses_cli_oauth_without_api_key(tmp_path, monkeypatch):
    """Gemini 호출은 API key env 주입 없이 CLI 인증(OAuth)을 그대로 사용한다."""
    try:
        orch = import_orchestrator()

        result_path = tmp_path / "gemini-solution-review.md"
        calls = []

        def fake_popen(cmd, **kwargs):
            calls.append((cmd, kwargs))
            return object()

        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.setattr(orch, "GEMINI_RESULT_PATH", result_path)
        monkeypatch.setattr(orch, "gemini_cli_path", lambda: "C:/tools/gemini.cmd")
        monkeypatch.setattr(subprocess, "Popen", fake_popen)

        orch.call_gemini_background("oauth smoke prompt")

        assert calls, "gemini CLI Popen 호출이 발생해야 한다"
        cmd, kwargs = calls[0]
        assert cmd == ["C:/tools/gemini.cmd", "-p", "oauth smoke prompt"]
        assert "env" not in kwargs, "GEMINI_API_KEY 강제 주입 없이 CLI OAuth 컨텍스트를 사용해야 한다"
        assert kwargs["cwd"] == str(orch.REPO_ROOT)
        assert result_path.exists()
        assert "oauth smoke prompt" in result_path.read_text(encoding="utf-8")
    finally:
        sys.path.pop(0)


@pytest.mark.orchestrator
def test_gemini_oauth_live_smoke_opt_in():
    """실제 Gemini OAuth 인증 확인용 opt-in smoke.

    기본 테스트에서는 외부 CLI·quota에 의존하지 않는다. 로컬 검증 시:
    RUN_GEMINI_OAUTH_TEST=1 pytest .claude/scripts/tests/test_orchestrator.py -q
    """
    if os.environ.get("RUN_GEMINI_OAUTH_TEST") != "1":
        pytest.skip("RUN_GEMINI_OAUTH_TEST=1 설정 시에만 실제 gemini CLI를 호출한다")
    gemini_path = shutil.which("gemini")
    if not gemini_path:
        pytest.skip("gemini CLI 미설치")
    oauth_path = Path.home() / ".gemini" / "oauth_creds.json"
    if not oauth_path.exists() and not os.environ.get("GEMINI_API_KEY"):
        pytest.skip("Gemini OAuth credential 또는 GEMINI_API_KEY 없음")

    result = subprocess.run(
        [gemini_path, "-p", "Respond with exactly one short Korean word."],
        capture_output=True,
        text=True,
        timeout=45,
    )
    assert result.returncode == 0, result.stderr[-500:]
    assert result.stdout.strip()


@pytest.mark.orchestrator
def test_gemini_once_per_session(monkeypatch):
    """같은 세션에서 detect_solution_change는 한 번만 호출 — 중복 호출 방지."""
    try:
        orch = import_orchestrator()

        monkeypatch.setattr(orch, "gemini_cli_available", lambda: True)
        monkeypatch.setattr(orch, "staged_solutions_changed", lambda: True)
        # call_gemini_background mock — 실제 호출 안 함
        called = []
        monkeypatch.setattr(orch, "call_gemini_background", lambda p: called.append(p))

        state: dict = {}
        first = orch.detect_solution_change({}, state)
        second = orch.detect_solution_change({}, state)
        assert len(first) == 1
        assert second == []  # 두 번째는 skip
        assert len(called) == 1
    finally:
        sys.path.pop(0)


@pytest.mark.orchestrator
def test_staged_solutions_detects_body_change():
    """Solutions 헤더가 아니라 본문 라인만 바뀌어도 감지한다."""
    try:
        orch = import_orchestrator()
        cps_text = "\n".join([
            "# CPS",
            "",
            "## Problems",
            "",
            "### P1. 문제",
            "",
            "## Solutions",
            "",
            "### S1 (for P1): 기존",
            "",
            "- 해결 기준: old",
            "",
            "## 도메인 목록",
        ])
        diff_text = "\n".join([
            "diff --git a/docs/guides/project_kickoff.md b/docs/guides/project_kickoff.md",
            "@@ -11 +11 @@",
            "-- 해결 기준: old",
            "+- 해결 기준: new",
        ])
        assert orch.staged_solutions_changed_from_diff(diff_text, cps_text) is True
    finally:
        sys.path.pop(0)


@pytest.mark.orchestrator
def test_staged_solutions_ignores_problem_change():
    """Problems 섹션 변경은 Solution 변경 트리거가 아니다."""
    try:
        orch = import_orchestrator()
        cps_text = "\n".join([
            "# CPS",
            "",
            "## Problems",
            "",
            "### P1. 문제",
            "",
            "## Solutions",
            "",
            "### S1 (for P1): 기존",
            "",
            "- 해결 기준: old",
            "",
            "## 도메인 목록",
        ])
        diff_text = "\n".join([
            "diff --git a/docs/guides/project_kickoff.md b/docs/guides/project_kickoff.md",
            "@@ -5 +5 @@",
            "-### P1. 문제",
            "+### P1. 바뀐 문제",
        ])
        assert orch.staged_solutions_changed_from_diff(diff_text, cps_text) is False
    finally:
        sys.path.pop(0)


@pytest.mark.orchestrator
def test_existing_signals_are_not_reemitted(tmp_path):
    """이전 active_signals만 있으면 stdout 주입 없이 침묵한다."""
    signal_path = tmp_path / "session_signal.json"
    signal_path.write_text(json.dumps({
        "session_id": "test",
        "active_signals": [
            {
                "p_id": "P1",
                "severity": "INFO",
                "key": "P1:old.py",
                "message": "오래된 신호",
            }
        ],
        "counter": {"last_modified_files": []},
    }), encoding="utf-8")

    payload = {"tool_name": "Bash", "tool_input": {"command": "ls"}}
    result = run_orchestrator(
        payload,
        env_overrides={
            **os.environ,
            "ORCHESTRATOR_SIGNAL_PATH": str(signal_path),
        },
    )
    assert result.returncode == 0
    assert result.stdout.strip() == ""
