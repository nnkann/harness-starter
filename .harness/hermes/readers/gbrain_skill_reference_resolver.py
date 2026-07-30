"""Resolve GBrain hits only through canonical Harness Brain readback."""

from __future__ import annotations

import hashlib
import os
import stat
import subprocess
from collections.abc import Callable, Mapping
from pathlib import Path, PurePosixPath
from typing import Any

from gbrain_search_reader import create_gbrain_search_reader

HARNESS_BRAIN_ROOT = Path("/Users/kann/projects/harness-brain")
CANONICAL_REPO = "harness-brain"
DEFAULT_MAX_BYTES = 64 * 1024
_GIT_TIMEOUT = 5.0


def resolve_skill_live_reference(
    query: str,
    *,
    search_reader: Callable[[str], Mapping[str, Any]] | None = None,
    harness_brain_root: str | Path = HARNESS_BRAIN_ROOT,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> dict[str, Any]:
    """Search candidates, then expose clues only after canonical readback."""
    reader = search_reader or create_gbrain_search_reader()
    try:
        search = reader(query)
    except Exception:
        search = _search_failure(query, "reader_failure")
    if not isinstance(search, Mapping):
        search = _search_failure(query, "malformed_response")

    hits = search.get("candidates")
    if search.get("status") not in {"match", "no_match"} or not isinstance(hits, list):
        return {
            "status": search.get("status", "unavailable"),
            "query": query,
            "observations": [_observation("search_unavailable", search.get("evidence"))],
            "usable_clues": [],
        }

    observations = []
    usable_clues = []
    for hit in hits:
        if not isinstance(hit, Mapping) or hit.get("lifecycle") != "candidate":
            observations.append(_observation("malformed_hit"))
            continue
        readback = dereference_harness_brain_source(
            hit.get("source_ref"), harness_brain_root=harness_brain_root, max_bytes=max_bytes
        )
        observation = {
            "lifecycle": "candidate",
            "gbrain_source_receipt": hit.get("source_receipt"),
            **readback,
        }
        observations.append(observation)
        if readback["status"] == "available":
            usable_clues.append(readback)

    return {
        "status": "match" if usable_clues else "no_match",
        "query": query,
        "observations": observations,
        "usable_clues": usable_clues,
    }


def dereference_harness_brain_source(
    source_ref: Any,
    *,
    harness_brain_root: str | Path = HARNESS_BRAIN_ROOT,
    max_bytes: int = DEFAULT_MAX_BYTES,
    revision_reader: Callable[[Path], str | None] | None = None,
) -> dict[str, Any]:
    """Fail closed unless one candidate resolves to a bounded canonical file."""
    failure = {"status": "unavailable", "source_ref": source_ref, "usable_clue": None}
    if not isinstance(max_bytes, int) or isinstance(max_bytes, bool) or max_bytes < 1:
        return {**failure, "reason": "invalid_bound"}
    reason = _malformed_reason(source_ref)
    if reason:
        return {**failure, "reason": reason}

    try:
        lexical_root = Path(harness_brain_root).expanduser().absolute()
        root = lexical_root.resolve(strict=True)
    except (OSError, RuntimeError, TypeError, ValueError):
        return {**failure, "reason": "canonical_repo_unavailable"}
    if not root.is_dir():
        return {**failure, "reason": "canonical_repo_unavailable"}

    requested = Path(source_ref)
    if requested.is_absolute():
        try:
            requested.relative_to(lexical_root)
        except ValueError:
            return {**failure, "reason": "absolute_escape"}
        lexical = requested
    else:
        lexical = root.joinpath(*PurePosixPath(source_ref).parts)

    if not lexical.exists() and not lexical.suffix:
        lexical = lexical.with_suffix(".md")
    try:
        canonical = lexical.resolve(strict=True)
    except FileNotFoundError:
        return {**failure, "reason": "missing_target"}
    except (OSError, RuntimeError, ValueError):
        return {**failure, "reason": "unreadable_target"}
    try:
        relative = canonical.relative_to(root)
    except ValueError:
        return {**failure, "reason": "symlink_escape"}
    if not canonical.is_file():
        return {**failure, "reason": "malformed_target"}

    try:
        descriptor = os.open(canonical, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode):
                return {**failure, "reason": "malformed_target"}
            with os.fdopen(descriptor, "rb", closefd=False) as source:
                content = source.read(max_bytes + 1)
        finally:
            os.close(descriptor)
    except OSError:
        return {**failure, "reason": "unreadable_target"}
    if len(content) > max_bytes:
        return {**failure, "reason": "source_too_large"}
    try:
        clue = content.decode("utf-8")
    except UnicodeDecodeError:
        return {**failure, "reason": "malformed_content"}

    revision = (revision_reader or _current_revision)(root)
    if not isinstance(revision, str) or not revision.strip():
        return {**failure, "reason": "source_revision_unavailable"}
    revision = revision.strip()
    digest = hashlib.sha256(content).hexdigest()
    relative_path = relative.as_posix()
    byte_count = len(content)
    receipt = (
        f"canonical-source:repo={CANONICAL_REPO};path={relative_path};revision={revision};"
        f"sha256={digest};bytes={byte_count}"
    )
    return {
        "status": "available",
        "source_ref": source_ref,
        "canonical_repo": CANONICAL_REPO,
        "repo_relative_path": relative_path,
        "current_source_revision": revision,
        "content_digest": digest,
        "byte_count": byte_count,
        "source_receipt": receipt,
        "usable_clue": clue,
    }


def _malformed_reason(source_ref: Any) -> str | None:
    if (
        not isinstance(source_ref, str)
        or not source_ref
        or source_ref != source_ref.strip()
        or any(ord(character) < 32 for character in source_ref)
        or "://" in source_ref
    ):
        return "malformed_ref"
    if "\\" in source_ref:
        return "malformed_ref"
    parts = source_ref.split("/")
    if source_ref.startswith("/"):
        parts = parts[1:]
    if ".." in parts:
        return "traversal_ref"
    if not parts or any(part in {"", "."} for part in parts):
        return "malformed_ref"
    return None


def _current_revision(root: Path) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
            timeout=_GIT_TIMEOUT,
            stdin=subprocess.DEVNULL,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return completed.stdout.strip() if completed.returncode == 0 else None


def _observation(reason: str, evidence: Any = None) -> dict[str, Any]:
    observation = {
        "status": "unavailable",
        "reason": reason,
        "lifecycle": "candidate",
        "usable_clue": None,
    }
    if isinstance(evidence, Mapping):
        observation["gbrain_evidence"] = dict(evidence)
    return observation


def _search_failure(query: str, reason: str) -> dict[str, Any]:
    return {
        "status": "unavailable",
        "query": query,
        "candidates": [],
        "evidence": {"record_count": 0, "source_receipt": f"gbrain-search:{reason}"},
    }
