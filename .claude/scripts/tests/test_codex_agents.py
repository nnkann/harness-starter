"""Codex/Gemini agent bridge 회귀 가드.

`.codex/agents/*.toml`은 외부 agent 런타임이 직접 읽는 얇은 bridge다.
파싱 실패·이름 불일치·금지 도구명 박제는 런타임에서 늦게 터지므로
pytest에서 먼저 잡는다.
"""

from __future__ import annotations

from pathlib import Path
import json
import re
try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 official harness runtime
    tomllib = None

import pytest


REPO = Path(__file__).resolve().parents[3]
CODEX_AGENTS = REPO / ".codex" / "agents"
CLAUDE_AGENTS = REPO / ".claude" / "agents"
CODEX_HOOKS = REPO / ".codex" / "hooks.json"

REQUIRED_AGENTS = {
    "advisor",
    "codebase-analyst",
    "debug-specialist",
    "doc-finder",
    "performance-analyst",
    "researcher",
    "review",
    "risk-analyst",
    "threat-analyst",
}

FORBIDDEN_TOOL_NAMES = {
    # Gemini CLI 0.41.2 로그에서 실제 미지원으로 확인된 이름.
    "run_shell_command",
}

SUPPORTED_HOOK_EVENTS = {
    "PreToolUse",
    "PostToolUse",
    "PostCompact",
    "SessionStart",
    "Stop",
}


def _load_toml(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if tomllib is not None:
        return tomllib.loads(text)

    # Python 3.10 fallback. 현재 bridge TOML은 top-level string 3개만 쓴다.
    data: dict[str, str] = {}
    for key in ("description", "developer_instructions", "name"):
        triple = re.search(rf'{key}\s*=\s*"""(.*?)"""', text, re.DOTALL)
        if triple:
            data[key] = triple.group(1)
            continue
        triple_single = re.search(rf"{key}\s*=\s*'''(.*?)'''", text, re.DOTALL)
        if triple_single:
            data[key] = triple_single.group(1)
            continue
        single = re.search(rf"{key}\s*=\s*'([^']*)'", text, re.DOTALL)
        if single:
            data[key] = single.group(1)
            continue
        double = re.search(rf'{key}\s*=\s*"([^"]*)"', text, re.DOTALL)
        if double:
            data[key] = double.group(1)
    return data


@pytest.mark.orchestrator
def test_codex_agent_set_matches_claude_agents():
    """Codex bridge agent 목록은 Claude agent SSOT와 1:1이어야 한다."""
    codex = {p.stem for p in CODEX_AGENTS.glob("*.toml")}
    claude = {p.stem for p in CLAUDE_AGENTS.glob("*.md")}

    assert codex == REQUIRED_AGENTS
    assert codex == claude


@pytest.mark.orchestrator
@pytest.mark.parametrize("path", sorted(CODEX_AGENTS.glob("*.toml")))
def test_codex_agent_toml_contract(path: Path):
    """모든 bridge agent는 Codex TOML 계약을 만족해야 한다."""
    data = _load_toml(path)

    assert data.get("name") == path.stem
    assert isinstance(data.get("description"), str) and data["description"].strip()
    assert (
        isinstance(data.get("developer_instructions"), str)
        and len(data["developer_instructions"].strip()) > 200
    )


@pytest.mark.orchestrator
@pytest.mark.parametrize("path", sorted(CODEX_AGENTS.glob("*.toml")))
def test_codex_agents_do_not_reference_unsupported_gemini_tools(path: Path):
    """Gemini/Codex bridge 문서에 실제 미지원 tool 이름을 박제하지 않는다."""
    text = path.read_text(encoding="utf-8")
    for tool_name in FORBIDDEN_TOOL_NAMES:
        assert tool_name not in text


@pytest.mark.orchestrator
@pytest.mark.parametrize("path", sorted(CODEX_AGENTS.glob("*.toml")))
def test_codex_agent_preserves_core_routing_language(path: Path):
    """각 agent는 라우팅에 필요한 TRIGGER/SKIP 또는 역할 계약을 보존한다."""
    text = path.read_text(encoding="utf-8")
    assert any(token in text for token in ("TRIGGER", "SKIP", "호출", "목표"))


@pytest.mark.orchestrator
def test_codex_hooks_contract():
    """Codex hooks bridge는 opt-in이며, 활성화된 항목만 형식 계약을 검증한다."""
    data = json.loads(CODEX_HOOKS.read_text(encoding="utf-8"))
    hooks = data.get("hooks")

    assert isinstance(hooks, dict)
    assert set(hooks).issubset(SUPPORTED_HOOK_EVENTS)
    for event, entries in hooks.items():
        assert isinstance(entries, list) and entries, event
        for entry in entries:
            assert "matcher" in entry, f"{event} matcher 누락"
            assert isinstance(entry.get("hooks"), list) and entry["hooks"], event
            for hook in entry["hooks"]:
                assert hook.get("type") == "command", f"{event} hook type"
                command = hook.get("command")
                assert isinstance(command, str) and command.strip(), f"{event} command"
