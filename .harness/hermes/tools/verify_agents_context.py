#!/usr/bin/env python3
"""Optional diagnostic: verify which AGENTS.md-style context Hermes loads.

This is intentionally not part of validate-reference because it depends on the
local Hermes source checkout. It exists to prevent root/profile-doc context
mixups when operating the harness-starter baseline branch.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def find_repo_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / ".harness" / "hermes" / "loader.py").exists():
            return candidate
    raise RuntimeError("could not find harness-starter-hermes-adapter repo root")


REPO_ROOT = find_repo_root(Path(__file__).resolve())
HERMES_SOURCE = Path("/Users/kann/.hermes/hermes-agent")
PROFILE_DOCS = REPO_ROOT / ".harness" / "hermes" / "profile-docs"

CANARIES = [
    "MAAT judges first",
    "THOTH compiles the contract before fan-out",
    "Failure is a CPS event",
    "Truthful reporting rules",
    "Hermes context-loading reality",
]
PROFILE_DOCS_ONLY = "This file is profile documentation and template source"


def load_prompt(cwd: Path) -> str:
    sys.path.insert(0, str(HERMES_SOURCE))
    from agent.prompt_builder import build_context_files_prompt  # type: ignore

    return build_context_files_prompt(cwd=str(cwd), skip_soul=True)


def run_loader(command: str) -> dict:
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / ".harness" / "hermes" / "loader.py"), command],
        cwd=str(REPO_ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"loader {command} did not return JSON: {proc.stdout}") from exc
    if proc.returncode != 0:
        raise AssertionError(f"loader {command} failed: {payload.get('errors') or proc.stderr}")
    return payload


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    if not HERMES_SOURCE.exists():
        print(f"SKIP agents context verification: Hermes source missing at {HERMES_SOURCE}")
        return 0
    summary = run_loader("summary")
    validation = run_loader("validate-reference")
    require(validation.get("ok") is True, f"loader validate-reference failed: {validation.get('errors')}")
    require(summary.get("gateway") == ".harness/hermes/gateway.yaml", "summary missing gateway contract")
    require(summary.get("board_assignees") == ".harness/hermes/board-assignees.yaml", "summary missing board assignees contract")
    require(summary.get("cps_profile_routing") == ".harness/hermes/cps-profile-routing.yaml", "summary missing CPS profile routing contract")

    root_prompt = load_prompt(REPO_ROOT)
    profile_prompt = load_prompt(PROFILE_DOCS)

    require("## AGENTS.md" in root_prompt, "root AGENTS.md was not loaded from adapter root cwd")
    for canary in CANARIES:
        require(canary in root_prompt, f"missing root AGENTS.md canary in effective prompt: {canary}")
    if PROFILE_DOCS_ONLY in root_prompt:
        raise AssertionError("profile-docs AGENTS.md unexpectedly loaded from adapter root cwd")
    if PROFILE_DOCS_ONLY not in profile_prompt:
        print("WARN profile-docs AGENTS.md did not load from profile-docs cwd; root context isolation still holds")

    print("PASS agents context verification")
    print(f"repo_root={REPO_ROOT}")
    print(f"canonical_branch=hermes/harness-starter-baseline")
    print(f"loader_validate_reference_ok={validation.get('ok')}")
    print(f"loader_gateway={summary.get('gateway')}")
    print(f"loader_board_assignees={summary.get('board_assignees')}")
    print("loaded_from_root=AGENTS.md")
    print("profile_docs_auto_loaded_from_root=false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL agents context verification: {exc}", file=sys.stderr)
        raise SystemExit(1)
