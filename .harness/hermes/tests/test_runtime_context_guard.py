#!/usr/bin/env python3
"""Regression tests for harness runtime project-context guards."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
LOADER_PATH = REPO_ROOT / ".harness" / "hermes" / "loader.py"

spec = importlib.util.spec_from_file_location("harness_hermes_loader", LOADER_PATH)
assert spec is not None and spec.loader is not None
loader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(loader)


class RuntimeContextGuardTests(unittest.TestCase):
    def _base_env(self, workspace: Path, board: str = "harness-starter-project-hermes") -> dict[str, str]:
        return {
            "HERMES_KANBAN_TASK": "t_example",
            "HERMES_KANBAN_DB": str(workspace.parent / "kanban.db"),
            "HERMES_KANBAN_BOARD": board,
            "HERMES_KANBAN_WORKSPACES_ROOT": str(workspace.parent),
            "HERMES_KANBAN_WORKSPACE": str(workspace),
            "HERMES_KANBAN_RUN_ID": "1",
            "HERMES_KANBAN_CLAIM_LOCK": "test:1",
            "HERMES_PROFILE": "harness-starter-project-ptah",
        }

    def test_guard_accepts_matching_workspace_board_and_allowed_scope(self) -> None:
        workspace = REPO_ROOT.resolve()
        env = self._base_env(workspace)
        result = loader.guard_runtime_context(
            cwd=workspace,
            env=env,
            operation="write",
            target_paths=[REPO_ROOT / ".harness" / "hermes" / "sandbox.yaml"],
        )

        self.assertTrue(result["ok"], result)
        self.assertEqual(result["expected"]["workspace"], result["actual"]["cwd"])

    def test_guard_rejects_ambient_cwd_that_conflicts_with_pinned_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp).resolve()
            workspace = base / "worktree"
            other = base / "other"
            workspace.mkdir()
            other.mkdir()
            env = self._base_env(workspace)
            result = loader.guard_runtime_context(cwd=other, env=env, operation="write")

        self.assertFalse(result["ok"])
        self.assertIn("cwd mismatch", "\n".join(result["errors"]))
        self.assertEqual(result["expected"]["workspace"], str(workspace))
        self.assertEqual(result["actual"]["cwd"], str(other))

    def test_guard_rejects_missing_project_context_for_commit_push_and_auth(self) -> None:
        workspace = REPO_ROOT.resolve()
        env = self._base_env(workspace)
        env.pop("HERMES_KANBAN_BOARD")
        for operation in ["branch", "commit", "push", "auth"]:
            result = loader.guard_runtime_context(cwd=workspace, env=env, operation=operation)
            self.assertFalse(result["ok"], operation)
            self.assertIn("missing required env", "\n".join(result["errors"]))
            self.assertIn(operation, result["actual"]["operation"])

    def test_guard_rejects_control_plane_project_root(self) -> None:
        workspace = REPO_ROOT.resolve()
        env = self._base_env(workspace)
        result = loader.guard_runtime_context(
            cwd=workspace,
            env=env,
            operation="write",
            project_root=Path("/Users/kann/.hermes/hermes-agent"),
        )

        self.assertFalse(result["ok"])
        self.assertIn("control-plane", "\n".join(result["errors"]))

    def test_guard_rejects_target_outside_allowed_scope(self) -> None:
        workspace = REPO_ROOT.resolve()
        env = self._base_env(workspace)
        result = loader.guard_runtime_context(
            cwd=workspace,
            env=env,
            operation="write",
            target_paths=[REPO_ROOT / "README.md"],
        )

        self.assertFalse(result["ok"])
        self.assertIn("outside allowed_scope", "\n".join(result["errors"]))


if __name__ == "__main__":
    unittest.main()
