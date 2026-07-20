from __future__ import annotations

import os
import platform
import pwd
import shutil
import subprocess
from pathlib import Path
from typing import Sequence


class SandboxError(ValueError):
    pass


def _credential_stores() -> dict[str, Path]:
    home = Path(pwd.getpwuid(os.getuid()).pw_dir).resolve()
    return {
        "railway": home / ".railway",
        "supabase": home / ".supabase",
        "vercel": home / "Library/Application Support/com.vercel.cli",
    }


def _literal(path: Path) -> str:
    return str(path).replace("\\", "\\\\").replace('"', '\\"')


def build_sandbox_profile(
    worktree: str | Path,
    state_dir: str | Path,
    *,
    network: bool,
    allow_write: Sequence[str | Path] = (),
) -> str:
    root = Path(worktree).expanduser().resolve()
    state = Path(state_dir).expanduser().resolve()
    requested = [Path(path).expanduser().resolve() for path in allow_write]
    if any(not (path == root or root in path.parents or path == state or state in path.parents) for path in requested):
        raise SandboxError("allow-write paths must be within the worktree or HARNESS_STATE_DIR")
    writable = [root, state, *requested]
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
    rules.extend(
        f'(deny file-write* (subpath "{_literal(store)}"))'
        for store in _credential_stores().values()
    )
    rules.extend(f'(allow file-write* (subpath "{_literal(path)}"))' for path in writable)
    return "\n".join(rules) + "\n"


def _build_provider_readonly_profile(worktree: str | Path, state_dir: str | Path, provider: str) -> str:
    stores = _credential_stores()
    if provider not in stores:
        raise SandboxError(f"unsupported provider credential profile: {provider}")
    allowed = stores[provider]
    if not allowed.is_dir():
        raise SandboxError(f"fixed {provider.title()} credential store is unavailable")
    profile = build_sandbox_profile(worktree, state_dir, network=True)
    deny = f'(deny file-write* (subpath "{_literal(allowed)}"))\n'
    return profile.replace(deny, "") + f'(allow file-write* (subpath "{_literal(allowed)}"))\n'


def build_sandbox_argv(executable: str, profile_text: str, command: Sequence[str]) -> list[str]:
    argv = list(command)
    if not argv or any(not isinstance(value, str) or not value for value in argv):
        raise SandboxError("sandbox command must contain non-empty arguments")
    return [executable, "-p", profile_text, *argv]


def resolve_provider_readonly_command(command: Sequence[str]) -> list[str]:
    argv = list(command)
    if not argv or any(not isinstance(value, str) or not value for value in argv):
        raise SandboxError("sandbox command must contain non-empty arguments")
    provider = Path(argv[0]).name
    allowed = {
        "railway": {("status",)},
        "vercel": {("whoami",)},
        "supabase": {("projects", "list")},
    }
    restriction = (
        "network access is restricted to read-only discovery/status with the approved "
        "Railway CLI, Vercel CLI, or Supabase CLI"
    )
    if provider not in allowed or tuple(argv[1:]) not in allowed[provider]:
        raise SandboxError(restriction)
    approved_name = shutil.which(provider)
    if not approved_name:
        raise SandboxError(f"approved {provider.title()} CLI executable is unavailable")
    approved = Path(approved_name).resolve()
    candidate_name = shutil.which(argv[0]) if Path(argv[0]).name == argv[0] else argv[0]
    if not candidate_name:
        raise SandboxError(restriction)
    candidate = Path(candidate_name).expanduser().resolve()
    if not approved.is_file() or not candidate.is_file() or not os.access(approved, os.X_OK) or not os.path.samefile(approved, candidate):
        raise SandboxError(
            f"network access is restricted to the approved {provider.title()} CLI executable "
            "for read-only discovery/status"
        )
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
    credential_provider: str | None = None,
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
    if credential_provider is not None:
        if not network or allow_write:
            raise SandboxError("provider credential profiles require fixed read-only network mode")
        profile_text = _build_provider_readonly_profile(root, state, credential_provider)
    else:
        profile_text = build_sandbox_profile(root, state, network=network, allow_write=allow_write)
    return root, state, executable, profile_text


def run_sandbox(
    worktree: str | Path,
    state_dir: str | Path,
    command: Sequence[str],
    *,
    network: bool = False,
    allow_write: Sequence[str | Path] = (),
    suppress_output: bool = False,
) -> int:
    provider = Path(command[0]).name if network and command else None
    resolved_command = resolve_provider_readonly_command(command) if network else command
    root, state, executable, profile_text = prepare_sandbox(
        worktree,
        state_dir,
        network=network,
        allow_write=allow_write,
        credential_provider=provider,
    )
    state.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    environment["HARNESS_STATE_DIR"] = str(state)
    environment["HOME"] = pwd.getpwuid(os.getuid()).pw_dir
    environment["VERCEL_TELEMETRY_DISABLED"] = "1"
    for name in (
        "RAILWAY_API_TOKEN",
        "RAILWAY_TOKEN",
        "SUPABASE_ACCESS_TOKEN",
        "VERCEL_TOKEN",
        "XDG_CONFIG_HOME",
        "XDG_DATA_HOME",
    ):
        environment.pop(name, None)
    output = subprocess.DEVNULL if suppress_output else None
    completed = subprocess.run(
        build_sandbox_argv(executable, profile_text, resolved_command),
        cwd=root,
        env=environment,
        check=False,
        stdout=output,
        stderr=output,
    )
    return completed.returncode