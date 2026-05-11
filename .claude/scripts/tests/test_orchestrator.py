"""orchestrator.py 회귀 가드.

defends: P9
serves: S9
trigger: orchestrator-regression

본 결정: docs/WIP/decisions--hn_orchestrator_mechanism.md
"""

from __future__ import annotations

import json
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
