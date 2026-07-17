#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

_STATE_ORDER = ("staged", "unstaged", "untracked", "deleted")


class SnapshotError(ValueError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _git(repo: Path, *args: str, check: bool = True) -> bytes:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and completed.returncode != 0:
        message = completed.stderr.decode("utf-8", "replace").strip()
        raise SnapshotError(message or f"git {' '.join(args)} failed")
    return completed.stdout


def _validate_repo(repo: str | os.PathLike[str]) -> Path:
    path = Path(repo).expanduser().resolve(strict=True)
    if not path.is_dir():
        raise SnapshotError("repo must be a directory")
    top = Path(_git(path, "rev-parse", "--show-toplevel").decode().strip()).resolve(strict=True)
    if top != path:
        raise SnapshotError("repo must be the repository root")
    return path


def _normalize_scopes(scopes: Iterable[str]) -> tuple[str, ...]:
    normalized: list[str] = []
    for raw in scopes:
        if not isinstance(raw, str) or not raw or "\x00" in raw:
            raise SnapshotError("scope must be a non-empty path string")
        path = PurePosixPath(raw)
        if path.is_absolute() or raw != path.as_posix() or raw in (".", "..") or ".." in path.parts:
            raise SnapshotError(f"scope must be a normalized repo-relative path: {raw!r}")
        if path.parts[0] == ".git":
            raise SnapshotError("scope cannot address .git")
        normalized.append(raw)
    if not normalized:
        raise SnapshotError("at least one scope is required")
    if len(set(normalized)) != len(normalized):
        raise SnapshotError("scopes must be unique")
    return tuple(sorted(normalized))


def _pathspecs(scopes: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(f":(top,literal){scope}" for scope in scopes)


def _split_paths(value: bytes) -> set[str]:
    return {
        item.decode("utf-8", "surrogateescape")
        for item in value.split(b"\x00")
        if item
    }


def _diff_paths(repo: Path, scopes: tuple[str, ...], *, cached: bool, deleted: bool) -> set[str]:
    args = ["diff", "--no-ext-diff", "--name-only", "-z"]
    if cached:
        args.append("--cached")
    args.append("--diff-filter=D" if deleted else "--diff-filter=ACMRTUXB")
    args.extend(("--", *_pathspecs(scopes)))
    return _split_paths(_git(repo, *args))


def _blob(repo: Path, revision: str, path: str) -> bytes:
    return _git(repo, "show", f"{revision}:{path}")


def _worktree_bytes(repo: Path, path: str) -> bytes:
    target = repo / path
    try:
        parent = target.parent.resolve(strict=True)
        parent.relative_to(repo)
    except (FileNotFoundError, ValueError) as exc:
        raise SnapshotError(f"worktree path escapes or is unavailable: {path}") from exc
    if target.is_symlink():
        return os.fsencode(os.readlink(target))
    try:
        return target.read_bytes()
    except OSError as exc:
        raise SnapshotError(f"cannot read worktree path: {path}") from exc


def _content(value: bytes) -> dict[str, Any]:
    return {
        "base64": base64.b64encode(value).decode("ascii"),
        "byte_length": len(value),
        "sha256": _sha256_bytes(value),
    }


def _validate_scope_matches(repo: Path, scopes: tuple[str, ...]) -> None:
    matches = _split_paths(
        _git(
            repo,
            "ls-files",
            "-z",
            "--cached",
            "--others",
            "--deleted",
            "--exclude-standard",
            "--",
            *_pathspecs(scopes),
        )
    )
    if not matches:
        raise SnapshotError("scope does not match any repository path")


def _capture_scoped_state(repo: Path, scopes: tuple[str, ...]) -> dict[str, Any]:
    staged_deleted = _diff_paths(repo, scopes, cached=True, deleted=True)
    unstaged_deleted = _diff_paths(repo, scopes, cached=False, deleted=True)
    staged = _diff_paths(repo, scopes, cached=True, deleted=False) - staged_deleted
    unstaged = _diff_paths(repo, scopes, cached=False, deleted=False) - unstaged_deleted
    untracked = _split_paths(
        _git(repo, "ls-files", "--others", "--exclude-standard", "-z", "--", *_pathspecs(scopes))
    )

    paths = staged | unstaged | untracked | staged_deleted | unstaged_deleted
    entries: list[dict[str, Any]] = []
    for path in sorted(paths):
        states: list[str] = []
        captures: dict[str, Any] = {}
        if path in staged:
            states.append("staged")
            captures["staged"] = _content(_blob(repo, "", path))
        if path in unstaged:
            states.append("unstaged")
            captures["unstaged"] = _content(_worktree_bytes(repo, path))
        if path in untracked:
            states.append("untracked")
            captures["untracked"] = _content(_worktree_bytes(repo, path))
        if path in staged_deleted:
            states.append("deleted")
            captures["deleted_from_head"] = _content(_blob(repo, "HEAD", path))
        if path in unstaged_deleted:
            if "deleted" not in states:
                states.append("deleted")
            captures["deleted_from_index"] = _content(_blob(repo, "", path))
        entries.append(
            {
                "captures": captures,
                "path": path,
                "path_sha256": _sha256_bytes(path.encode("utf-8", "surrogateescape")),
                "states": [state for state in _STATE_ORDER if state in states],
            }
        )
    return {"entries": entries}


def produce_snapshot_packet(
    repo: str | os.PathLike[str], scopes: Iterable[str]
) -> dict[str, Any]:
    repo_path = _validate_repo(repo)
    normalized_scopes = _normalize_scopes(scopes)
    _validate_scope_matches(repo_path, normalized_scopes)

    before = _capture_scoped_state(repo_path, normalized_scopes)
    if not before["entries"]:
        raise SnapshotError("scoped repository state is clean")
    after = _capture_scoped_state(repo_path, normalized_scopes)
    if canonical_json(before) != canonical_json(after):
        raise SnapshotError("scoped repository state changed during capture")

    body = {
        "entries": before["entries"],
        "repo": str(repo_path),
        "scopes": [
            {
                "path": scope,
                "path_sha256": _sha256_bytes(scope.encode("utf-8", "surrogateescape")),
            }
            for scope in normalized_scopes
        ],
        "version": 1,
    }
    return {**body, "packet_sha256": _sha256_bytes(canonical_json(body).encode("utf-8"))}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Produce a stable snapshot of dirty source paths in explicit scopes.")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--scope", action="append", required=True)
    args = parser.parse_args(argv)
    try:
        packet = produce_snapshot_packet(args.repo, args.scope)
    except (OSError, SnapshotError) as exc:
        parser.error(str(exc))
    print(canonical_json(packet))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
