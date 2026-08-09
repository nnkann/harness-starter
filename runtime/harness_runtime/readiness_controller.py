from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import TypeVar


Result = TypeVar("Result")


class ReadinessError(ValueError):
    pass


def run_ready(readiness: Mapping[str, object], run: Callable[[], Result]) -> Result:
    if frozenset(readiness) != {"ready"} or readiness["ready"] is not True:
        raise ReadinessError("complete readiness input is required")
    return run()
