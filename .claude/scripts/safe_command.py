#!/usr/bin/env python3
"""Codex-safe read/validation dispatcher.

This helper keeps repeated Codex approvals focused on one narrow, read-only
entrypoint. It intentionally excludes delete, move, commit, push, install,
network, and config mutation operations.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path.cwd().resolve()

ALLOWED_COMMANDS = {
    "status",
    "diff",
    "log",
    "show",
    "rg",
    "read",
    "docs-list",
    "docs-show",
    "cps-list",
    "cps-show",
    "cps-stats",
    "verify-relates",
    "docs-validate",
    "precheck",
}

BLOCKED_GIT_ARGS = {"--ext-diff", "--output"}
BLOCKED_RG_ARGS = {"--pre", "--pre-glob"}


def run(argv: list[str]) -> int:
    return subprocess.run(argv, check=False).returncode


def reject_blocked_args(tool: str, args: list[str], blocked: set[str]) -> None:
    for arg in args:
        key = arg.split("=", 1)[0]
        if key in blocked:
            raise SystemExit(f"{tool} argument is not allowed in safe_command.py: {arg}")


def workspace_path(value: str) -> Path:
    path = (ROOT / value).resolve() if not Path(value).is_absolute() else Path(value).resolve()
    try:
        path.relative_to(ROOT)
    except ValueError as exc:
        raise SystemExit(f"Path is outside workspace: {value}") from exc
    if not path.exists():
        raise SystemExit(f"Path does not exist: {value}")
    return path


def docs_ops(*args: str) -> int:
    return run([sys.executable, ".claude/scripts/docs_ops.py", *args])


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Run approved read/validation commands for Codex.")
    parser.add_argument("command", choices=sorted(ALLOWED_COMMANDS))
    parser.add_argument("rest", nargs=argparse.REMAINDER)
    ns = parser.parse_args(argv)

    command = ns.command
    rest = ns.rest

    if command == "status":
        if rest:
            raise SystemExit("status does not accept extra arguments.")
        return run(["git", "status", "--short"])

    if command == "diff":
        return run(["git", "diff", "--", *rest])

    if command == "log":
        reject_blocked_args("git log", rest, BLOCKED_GIT_ARGS)
        return run(["git", "log", "--no-ext-diff", *rest])

    if command == "show":
        reject_blocked_args("git show", rest, BLOCKED_GIT_ARGS)
        return run(["git", "show", "--no-ext-diff", *rest])

    if command == "rg":
        if not rest:
            raise SystemExit("rg requires a pattern.")
        reject_blocked_args("rg", rest, BLOCKED_RG_ARGS)
        return run(["rg", *rest])

    if command == "read":
        if len(rest) != 1:
            raise SystemExit("read requires exactly one workspace path.")
        print(workspace_path(rest[0]).read_text(encoding="utf-8"), end="")
        return 0

    if command == "docs-list":
        if rest:
            raise SystemExit("docs-list does not accept extra arguments.")
        return docs_ops("list")

    if command == "docs-show":
        if len(rest) != 1:
            raise SystemExit("docs-show requires one document id/path.")
        return docs_ops("show", rest[0])

    if command == "cps-list":
        if rest:
            raise SystemExit("cps-list does not accept extra arguments.")
        return docs_ops("cps", "list")

    if command == "cps-show":
        if len(rest) != 1:
            raise SystemExit("cps-show requires one P#.")
        return docs_ops("cps", "show", rest[0])

    if command == "cps-stats":
        if rest:
            raise SystemExit("cps-stats does not accept extra arguments.")
        return docs_ops("cps", "stats")

    if command == "verify-relates":
        if rest:
            raise SystemExit("verify-relates does not accept extra arguments.")
        return docs_ops("verify-relates")

    if command == "docs-validate":
        return docs_ops("validate", *rest)

    if command == "precheck":
        if rest:
            raise SystemExit("precheck does not accept extra arguments.")
        return run([sys.executable, ".claude/scripts/pre_commit_check.py"])

    raise SystemExit(f"Unsupported command: {command}")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
