from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
LOADER = Path(".harness/hermes/loader.py")
SANDBOX = Path(".harness/hermes/sandbox.yaml")


class ContextMixupGuardTests(unittest.TestCase):
    def copy_reference(self) -> Path:
        tmp = Path(tempfile.mkdtemp(prefix="harness-context-guard-"))
        shutil.copytree(REPO_ROOT / ".harness", tmp / ".harness")
        return tmp

    def validate_reference(self, root: Path) -> dict:
        result = subprocess.run(
            [sys.executable, str(LOADER), "validate-reference"],
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as exc:  # pragma: no cover
            raise AssertionError(
                f"loader did not emit JSON; exit={result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}"
            ) from exc
        payload["returncode"] = result.returncode
        payload["stderr"] = result.stderr
        return payload

    def rewrite_sandbox(self, root: Path, old: str, new: str) -> None:
        path = root / SANDBOX
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text)
        path.write_text(text.replace(old, new), encoding="utf-8")

    def assert_validation_error_contains(self, payload: dict, expected: str) -> None:
        self.assertFalse(payload["ok"], payload)
        self.assertNotEqual(payload["returncode"], 0, payload)
        self.assertIn(expected, "\n".join(payload["errors"]))

    def test_valid_channel_bound_pinned_worktree_context_is_accepted(self) -> None:
        root = self.copy_reference()
        payload = self.validate_reference(root)
        self.assertEqual(payload["returncode"], 0, payload)
        self.assertTrue(payload["ok"], payload)
        self.assertEqual(payload["errors"], [])

    def test_cwd_project_mismatch_guard_is_required(self) -> None:
        root = self.copy_reference()
        self.rewrite_sandbox(root, "block_on_cwd_project_mismatch: true", "block_on_cwd_project_mismatch: false")
        payload = self.validate_reference(root)
        self.assert_validation_error_contains(payload, "block_on_cwd_project_mismatch: true")

    def test_blocked_operations_must_be_declared(self) -> None:
        root = self.copy_reference()
        self.rewrite_sandbox(root, "blocked_operations", "operations_no_longer_blocked")
        payload = self.validate_reference(root)
        self.assert_validation_error_contains(payload, "blocked_operations")

    def test_valid_pinned_worktree_case_must_be_explicitly_accepted(self) -> None:
        root = self.copy_reference()
        self.rewrite_sandbox(root, "pinned_worktree_context_accepted: true", "pinned_worktree_context_accepted: false")
        payload = self.validate_reference(root)
        self.assert_validation_error_contains(payload, "pinned_worktree_context_accepted: true")


if __name__ == "__main__":
    unittest.main()
