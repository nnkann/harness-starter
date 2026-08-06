from __future__ import annotations

import json
import sys
from pathlib import Path

_RUNTIME = Path(__file__).resolve().parents[3] / "runtime"
if _RUNTIME.is_dir() and str(_RUNTIME) not in sys.path:
    sys.path.insert(0, str(_RUNTIME))

from harness_runtime.capability_transport import consume_capability, repair_envelope


_TOOL_SCHEMA = {
    "name": "harness_capability_consume",
    "description": "Consume an opaque bound capability readiness reference.",
    "parameters": {
        "type": "object",
        "required": ["capability_ref"],
        "additionalProperties": False,
        "properties": {
            "capability_ref": {"type": "string", "minLength": 1, "maxLength": 256},
        },
    },
}


def register(ctx) -> None:
    profile = ctx.profile_name

    def handler(args, **host_kwargs):
        capability_ref = args.get("capability_ref") if isinstance(args, dict) else None
        if not isinstance(args, dict) or set(args) != {"capability_ref"}:
            result = repair_envelope(
                capability_ref,
                "tool_arguments_invalid",
                host_context={
                    "profile": profile,
                    "session_id": host_kwargs.get("session_id"),
                    "task_id": host_kwargs.get("task_id"),
                },
            )
        else:
            result = consume_capability(
                capability_ref,
                host_context={
                    "profile": profile,
                    "session_id": host_kwargs.get("session_id"),
                    "task_id": host_kwargs.get("task_id"),
                },
            )
        return json.dumps(result, sort_keys=True, separators=(",", ":"))

    ctx.register_tool(
        name="harness_capability_consume",
        toolset="harness-capability-transport",
        schema=_TOOL_SCHEMA,
        handler=handler,
        is_async=False,
    )
