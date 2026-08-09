from __future__ import annotations

import hashlib
import json
from typing import Any, Callable, Mapping

REQUIRED_NAMES = frozenset({"SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"})


class ChildExecutionError(ValueError):
    pass


def _digest(plan: dict[str, Any]) -> str:
    value = {key: item for key, item in plan.items() if key != "declaration_digest"}
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(canonical).hexdigest()


def run_scheduled_consumer_child(
    plan: object,
    *,
    source_values: Mapping[str, str],
    child_runner: Callable[[str, dict[str, str]], object],
) -> dict[str, int]:
    if not isinstance(plan, dict) or plan.get("declaration_digest") != _digest(plan):
        raise ChildExecutionError("scheduled consumer plan digest is invalid")
    if frozenset(plan.get("required_names", ())) != REQUIRED_NAMES:
        raise ChildExecutionError("scheduled consumer plan names are invalid")
    source = plan.get("source")
    if not isinstance(source, dict) or source.get("class") not in {
        "injected_fixture",
        "project_instance_adapter",
    }:
        raise ChildExecutionError("scheduled consumer source class is invalid")
    if not isinstance(source_values, Mapping) or frozenset(source_values) != REQUIRED_NAMES or any(
        not isinstance(source_values[name], str) or not source_values[name] for name in REQUIRED_NAMES
    ):
        raise ChildExecutionError("source values must resolve the exact declared names")

    child_env = {name: source_values[name] for name in sorted(REQUIRED_NAMES)}
    try:
        child_result = child_runner(plan["script"]["identity"], child_env)
    except Exception:
        raise ChildExecutionError("scheduled consumer child failed") from None
    exit_code = child_result.get("exit_code") if isinstance(child_result, dict) else None
    if not isinstance(exit_code, int):
        raise ChildExecutionError("scheduled consumer child returned an invalid result")
    return {"exit_code": exit_code}
