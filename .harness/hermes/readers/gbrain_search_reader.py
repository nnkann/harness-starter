"""Bounded read-only binding for GBrain search candidates."""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
from collections.abc import Callable, Mapping
from typing import Any

GBRAIN_EXECUTABLE = "/Users/kann/.bun/bin/gbrain"
DEFAULT_LIMIT = 5
MAX_LIMIT = 10
DEFAULT_TIMEOUT = 10.0
MAX_QUERY_CHARS = 512
_MAX_EXCERPT_CHARS = 256
_HIT = re.compile(r"^\[(?P<score>\d+(?:\.\d+)?)\]\s+(?P<source_ref>.+?)\s+--\s*(?P<excerpt>.*)$")


def create_gbrain_search_reader(
    *,
    limit: int = DEFAULT_LIMIT,
    timeout: float = DEFAULT_TIMEOUT,
    executable: str = GBRAIN_EXECUTABLE,
    runner: Callable[..., Any] = subprocess.run,
) -> Callable[[str], Mapping[str, Any]]:
    """Bind a GBrain keyword search with fixed query, result, and time bounds."""
    if not _valid_limit(limit):
        raise ValueError("limit must be an integer from 1 through 10")
    if not isinstance(timeout, (int, float)) or isinstance(timeout, bool) or not 0 < timeout <= 30:
        raise ValueError("timeout must be greater than zero and at most 30 seconds")
    if not isinstance(executable, str) or not executable:
        raise ValueError("executable must be a non-empty path")

    def read(query: str) -> Mapping[str, Any]:
        if not isinstance(query, str) or query != query.strip() or not query or "\x00" in query or len(query) > MAX_QUERY_CHARS:
            return _failed("query_error", query, limit, "malformed_query")
        command = [executable, "search", query, "--limit", str(limit)]
        try:
            completed = runner(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout,
                stdin=subprocess.DEVNULL,
                env={
                    **os.environ,
                    "PATH": f"/Users/kann/.bun/bin:{os.environ.get('PATH', '')}",
                },
            )
        except subprocess.TimeoutExpired:
            return _failed("unavailable", query, limit, "timeout")
        except (OSError, ValueError):
            return _failed("unavailable", query, limit, "invocation_failure")

        if completed.returncode != 0:
            return _failed("query_error", query, limit, f"exit_{completed.returncode}")
        candidates = _parse_candidates(completed.stdout, limit, query)
        return {
            "status": "match" if candidates else "no_match",
            "query": query,
            "limit": limit,
            "candidates": candidates,
            "evidence": {
                "record_count": len(candidates),
                "source_receipt": _search_receipt(query, limit),
            },
        }

    return read


def _valid_limit(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= MAX_LIMIT


def _parse_candidates(stdout: Any, limit: int, query: str) -> list[dict[str, Any]]:
    if not isinstance(stdout, str):
        return []
    candidates = []
    for line in stdout.splitlines():
        match = _HIT.match(line)
        if match is None:
            continue
        source_ref = match.group("source_ref").strip()
        if not source_ref:
            continue
        candidates.append(
            {
                "source_ref": source_ref,
                "excerpt": match.group("excerpt").strip()[:_MAX_EXCERPT_CHARS],
                "score": float(match.group("score")),
                "lifecycle": "candidate",
                "source_receipt": _search_receipt(query, limit, len(candidates)),
            }
        )
        if len(candidates) == limit:
            break
    return candidates


def _search_receipt(query: str, limit: int, index: int | None = None) -> str:
    digest = hashlib.sha256(query.encode("utf-8")).hexdigest()
    suffix = "" if index is None else f";candidate={index}"
    return f"gbrain-search:query_sha256={digest};limit={limit}{suffix}"


def _failed(status: str, query: Any, limit: int, reason: str) -> Mapping[str, Any]:
    return {
        "status": status,
        "query": query if isinstance(query, str) else "",
        "limit": limit,
        "candidates": [],
        "evidence": {"record_count": 0, "source_receipt": f"gbrain-search:{reason}"},
    }
