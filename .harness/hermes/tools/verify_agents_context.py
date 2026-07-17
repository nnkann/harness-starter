#!/usr/bin/env python3
"""Verify the harness-starter repository project entry source.

This is intentionally not part of validate-reference. It verifies the local
reader contract without loading Hermes core or AGENTS.md-style context.
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
ENTRY_SOURCE = REPO_ROOT / "README.md"
ROOT_AGENTS = REPO_ROOT / "AGENTS.md"
LOADER = REPO_ROOT / ".harness" / "hermes" / "loader.py"
ENTRY_HEADING = "## Project entry point"
ENTRY_AUTHORITY = "프로젝트 진입·규칙·도메인·cluster의 canonical authority는 `harness-brain`이다."
PROJECT_READERS = [
    REPO_ROOT / ".harness" / "project" / "scripts" / "router" / "read_context_probe.py",
    REPO_ROOT / ".harness" / "project" / "scripts" / "router" / "seed_honcho_project_context.py",
]
REQUIRED_PROJECT_ENTRY_FIELDS = ["project_entry_source", "project_entry_source_preview"]
FORBIDDEN_LEGACY_FIELDS = ["agents_md_", "agents_policy_excerpt"]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def run_loader(command: str) -> dict:
    result = subprocess.run(
        [sys.executable, str(LOADER), command],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"loader {command} failed with exit code {result.returncode}: "
            f"{result.stderr.strip()}"
        )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"loader {command} returned invalid JSON: {exc}") from exc
    require(isinstance(payload, dict), f"loader {command} did not return an object")
    return payload


def main() -> int:
    require(ENTRY_SOURCE.is_file(), f"project entry source missing: {ENTRY_SOURCE}")
    entry_text = ENTRY_SOURCE.read_text(encoding="utf-8", errors="replace")
    require(ENTRY_HEADING in entry_text, f"project entry heading missing: {ENTRY_HEADING}")
    require(ENTRY_AUTHORITY in entry_text, "project entry authority declaration missing")
    require(not ROOT_AGENTS.exists(), f"root AGENTS.md must not exist: {ROOT_AGENTS}")

    for reader in PROJECT_READERS:
        reader_text = reader.read_text(encoding="utf-8", errors="replace")
        require("project_entry_source" in reader_text, f"project entry source missing from: {reader}")
        for forbidden_field in FORBIDDEN_LEGACY_FIELDS:
            require(forbidden_field not in reader_text, f"legacy field in reader: {reader}")

    summary = run_loader("summary")
    require(summary.get("gateway") == ".harness/hermes/gateway.yaml", "unexpected gateway")
    require(
        summary.get("board_assignees") == ".harness/hermes/board-assignees.yaml",
        "unexpected board_assignees",
    )
    require(
        summary.get("cps_profile_routing") == ".harness/hermes/cps-profile-routing.yaml",
        "unexpected cps_profile_routing",
    )

    validation = run_loader("validate-reference")
    require(validation.get("ok") is True, "reference validation failed")

    print("PASS project entry context verification")
    print("project_entry_source=README.md")
    print("project_entry_authority=harness-brain")
    print("loader_reference=validated")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL project entry context verification: {exc}", file=sys.stderr)
        raise SystemExit(1)
