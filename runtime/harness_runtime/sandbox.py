from __future__ import annotations

import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Sequence


class SandboxError(ValueError):
    pass


def _literal(path: Path) -> str:
    return str(path).replace("\\", "\\\\").replace('"', '\\"')


def build_sandbox_profile(
    worktree: str | Path,
    state_dir: str | Path,
    *,
    network: bool,
    allow_write: Sequence[str | Path] = (),
) -> str:
    writable = [Path(worktree).expanduser().resolve(), Path(state_dir).expanduser().resolve()]
    writable.extend(Path(path).expanduser().resolve() for path in allow_write)
    rules = [
        "(version 1)",
        "(deny default)",
        "(allow process*)",
        "(allow file-read*)",
        "(allow sysctl-read)",
        "(allow mach-lookup)",
        "(allow ipc-posix-shm)",
        "(allow network*)" if network else "(deny network*)",
    ]
    rules.extend(f'(allow file-write* (subpath "{_literal(path)}"))' for path in writable)
    return "\n".join(rules) + "\n"


def build_sandbox_argv(executable: str, profile_text: str, command: Sequence[str]) -> list[str]:
    argv = list(command)
    if not argv or any(not isinstance(value, str) or not value for value in argv):
        raise SandboxError("sandbox command must contain non-empty arguments")
    return [executable, "-p", profile_text, *argv]


def _network_command(command: Sequence[str]) -> list[str]:
    argv = list(command)
    if not argv or any(not isinstance(value, str) or not value for value in argv):
        raise SandboxError("sandbox command must contain non-empty arguments")
    approved_name = shutil.which("railway")
    if not approved_name:
        raise SandboxError("approved Railway CLI executable is unavailable")
    approved = Path(approved_name).resolve()
    candidate_name = shutil.which(argv[0]) if Path(argv[0]).name == argv[0] else argv[0]
    if not candidate_name:
        raise SandboxError("network access is restricted to the approved Railway CLI executable")
    candidate = Path(candidate_name).expanduser().resolve()
    if not approved.is_file() or not candidate.is_file() or not os.access(approved, os.X_OK) or not os.path.samefile(approved, candidate):
        raise SandboxError("network access is restricted to the approved Railway CLI executable")
    argv[0] = str(approved)
    return argv


def _git(worktree: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(worktree), *args],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={"LANG": "C", "LC_ALL": "C", "PATH": os.defpath},
    )
    if completed.returncode:
        raise SandboxError("worktree must be a Git repository with a committed HEAD")
    return completed.stdout.strip()


def prepare_sandbox(
    worktree: str | Path,
    state_dir: str | Path,
    *,
    network: bool = False,
    allow_write: Sequence[str | Path] = (),
    platform_name: str | None = None,
    sandbox_executable: str | None = None,
) -> tuple[Path, Path, str, str]:
    if (platform_name or platform.system()) != "Darwin":
        raise SandboxError("sandbox-exec backend is supported only on macOS; no unsandboxed fallback is allowed")
    executable = sandbox_executable or shutil.which("sandbox-exec")
    if not executable or not Path(executable).is_file():
        raise SandboxError("macOS sandbox-exec is unavailable; refusing unsandboxed execution")
    root = Path(worktree).expanduser().resolve()
    state = Path(state_dir).expanduser().resolve()
    if not root.is_dir() or Path(_git(root, "rev-parse", "--show-toplevel")).resolve() != root:
        raise SandboxError("worktree must be the Git worktree root")
    _git(root, "rev-parse", "HEAD")
    if _git(root, "status", "--porcelain", "--untracked-files=all"):
        raise SandboxError("worktree must be clean before sandbox execution")
    if state == root or root in state.parents or state in root.parents:
        raise SandboxError("HARNESS_STATE_DIR must be outside and non-overlapping with the worktree")
    profile_text = build_sandbox_profile(root, state, network=network, allow_write=allow_write)
    return root, state, executable, profile_text


def run_sandbox(
    worktree: str | Path,
    state_dir: str | Path,
    command: Sequence[str],
    *,
    network: bool = False,
    allow_write: Sequence[str | Path] = (),
) -> int:
    resolved_command = _network_command(command) if network else command
    root, state, executable, profile_text = prepare_sandbox(
        worktree,
        state_dir,
        network=network,
        allow_write=allow_write,
    )
    state.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    environment["HARNESS_STATE_DIR"] = str(state)
    completed = subprocess.run(
        build_sandbox_argv(executable, profile_text, resolved_command),
        cwd=root,
        env=environment,
        check=False,
    )
    return completed.returncode