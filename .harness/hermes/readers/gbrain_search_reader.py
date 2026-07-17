"""Source-neutral binding for the GBrain search reader."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Callable, Mapping, Sequence
from typing import Any

_GBRAIN = "/Users/kann/.bun/bin/gbrain"


def create_gbrain_search_reader(
    *,
    timeout: float | None = None,
) -> Callable[[str, Sequence[str] | None], Mapping[str, Any]]:
    """Create a source-neutral reader bound exclusively to the GBrain CLI."""

    def read(query: str, args: Sequence[str] | None = None) -> Mapping[str, Any]:
        command = [_GBRAIN, "search", query, *(args or ())]
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
            env={
                **os.environ,
                "PATH": f"/Users/kann/.bun/bin:{os.environ.get('PATH', '')}",
            },
        )
        return {
            "query": query,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "returncode": completed.returncode,
        }

    return read
