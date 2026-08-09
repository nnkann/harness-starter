from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .project_binding import inspect_binding

DECLARATION_SCHEMA = "harness.scheduled-readonly-consumer.v1"
REQUIRED_NAMES = frozenset({"SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"})
REGISTERED_SOURCE_CLASSES = frozenset({"injected_fixture", "project_instance_adapter"})
TOP_LEVEL_FIELDS = frozenset(
    {"schema", "project", "job", "script", "no_agent", "capability", "required_names", "source"}
)


class ScheduledConsumerError(ValueError):
    pass


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _object(value: object, fields: set[str] | frozenset[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or frozenset(value) != frozenset(fields):
        raise ScheduledConsumerError(f"{label} fields are invalid")
    return value


def _required_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_scheduled_consumer(project_root: str | Path, declaration: object) -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve()
    inspected = inspect_binding(root)
    if inspected["status"] != "bound":
        raise ScheduledConsumerError("project binding must be bound and undrifted")
    if not isinstance(declaration, dict) or frozenset(declaration) != TOP_LEVEL_FIELDS:
        raise ScheduledConsumerError("scheduled consumer declaration fields are invalid")
    if declaration.get("schema") != DECLARATION_SCHEMA:
        raise ScheduledConsumerError("scheduled consumer declaration schema is unsupported")

    binding_project = inspected["binding"].get("project")
    project = _object(declaration.get("project"), {"id", "root"}, "project identity")
    expected_project = {"id": binding_project.get("id"), "root": str(root)} if isinstance(binding_project, dict) else None
    if project != expected_project:
        raise ScheduledConsumerError("project identity does not match the bound project")

    capability = _object(declaration.get("capability"), {"class", "access"}, "capability")
    if capability != {"class": "scheduled_readonly_consumer", "access": "read_only"}:
        raise ScheduledConsumerError("scheduled consumer requires the read-only capability class")
    if declaration.get("no_agent") is not True:
        raise ScheduledConsumerError("no_agent must be true")

    names = declaration.get("required_names")
    if not isinstance(names, list) or len(names) != len(REQUIRED_NAMES) or frozenset(names) != REQUIRED_NAMES:
        raise ScheduledConsumerError("declaration must use the exact required names")

    job = declaration.get("job")
    script = declaration.get("script")
    identity_valid = (
        isinstance(job, dict)
        and frozenset(job) == {"identity", "schedule", "delivery"}
        and all(_required_string(job.get(key)) for key in ("identity", "schedule", "delivery"))
        and isinstance(script, dict)
        and frozenset(script) == {"identity", "digest"}
        and _required_string(script.get("identity"))
        and isinstance(script.get("digest"), str)
        and script["digest"].startswith("sha256:")
        and len(script["digest"]) == 71
        and all(character in "0123456789abcdef" for character in script["digest"][7:])
    )
    if not identity_valid:
        raise ScheduledConsumerError("stable job and script identity and digest are required")

    source = _object(declaration.get("source"), {"class", "ref", "availability"}, "source")
    if source.get("class") not in REGISTERED_SOURCE_CLASSES:
        raise ScheduledConsumerError("source class is not registered")
    if not _required_string(source.get("ref")) or not source["ref"].startswith(project["id"] + ":"):
        raise ScheduledConsumerError("source ref must belong to the bound project")
    availability = source.get("availability")
    if not isinstance(availability, dict) or frozenset(availability) != REQUIRED_NAMES or any(
        availability[name] is not True for name in REQUIRED_NAMES
    ):
        raise ScheduledConsumerError("source availability must be true for the exact required names")

    normalized = json.loads(json.dumps(declaration))
    normalized["required_names"] = sorted(REQUIRED_NAMES)
    normalized["source"]["availability"] = {name: True for name in sorted(REQUIRED_NAMES)}
    normalized["declaration_digest"] = "sha256:" + hashlib.sha256(_canonical(normalized)).hexdigest()
    return normalized
