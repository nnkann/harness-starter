from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, Callable, Mapping

from .project_binding import CAPABILITY_GRAPH_SCHEMA, BINDING_SCHEMA, source_snapshot_identity
from .sandbox import SandboxError, run_sandbox

PLAN_SCHEMA = "harness.capability-plan.v1"
DISCOVERY_SCHEMA = "harness.capability-discovery.v1"
STATUS_SCHEMA = "harness.capability-status.v1"
APPROVAL_SCHEMA = "harness.capability-approval.v1"
RECEIPT_SCHEMA = "harness.capability-execution-receipt.v1"

IDENTITY_FIELDS = {
    "railway": frozenset({"project_id", "environment_id", "service_id", "service_name"}),
    "vercel": frozenset({"org_id", "project_id"}),
    "supabase": frozenset({"project_ref", "boundary_id"}),
    "n8n": frozenset({"instance_id", "workflow_id", "contract_id"}),
    "deployed-api": frozenset({"deployment_id", "database_project_ref", "contract_id"}),
}

PROVIDER_STATUS_COMMANDS = {
    "railway.deploy": ["railway", "status"],
    "vercel.deploy": ["vercel", "whoami"],
    "supabase.schema-migration": ["supabase", "projects", "list"],
    "supabase.privileged-data-mutation": ["supabase", "projects", "list"],
}


class CapabilityError(ValueError):
    pass


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _load_binding(project_root: str | Path) -> tuple[Path, dict[str, Any]]:
    root = Path(project_root).expanduser().resolve()
    path = root / ".harness/project-binding.json"
    try:
        binding = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CapabilityError("project binding is missing") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise CapabilityError(f"project binding cannot be read: {exc}") from exc
    if binding.get("schema") != BINDING_SCHEMA:
        raise CapabilityError("project binding schema is unsupported")
    graph = binding.get("capability_graph")
    if not isinstance(graph, dict) or graph.get("schema") != CAPABILITY_GRAPH_SCHEMA:
        raise CapabilityError("typed capability graph is missing")
    claimed_digest = graph.get("digest")
    digest_input = {key: value for key, value in graph.items() if key != "digest"}
    if not isinstance(claimed_digest, str) or claimed_digest != _digest(digest_input):
        raise CapabilityError("capability graph digest mismatch")
    return root, binding


def _find_capability(binding: dict[str, Any], capability_id: str) -> dict[str, Any]:
    if not isinstance(capability_id, str) or not capability_id:
        raise CapabilityError("capability ID is required")
    capabilities = binding["capability_graph"].get("capabilities")
    if not isinstance(capabilities, list):
        raise CapabilityError("capability graph is invalid")
    matches = [item for item in capabilities if isinstance(item, dict) and item.get("capability_id") == capability_id]
    if len(matches) != 1:
        raise CapabilityError(f"unknown capability ID: {capability_id}")
    return matches[0]


def validate_provider_identity(provider: str, identity: object) -> dict[str, str]:
    if provider not in IDENTITY_FIELDS or not isinstance(identity, dict):
        raise CapabilityError(f"unsupported provider identity: {provider}")
    allowed = IDENTITY_FIELDS[provider]
    keys = frozenset(identity)
    if keys != allowed:
        raise CapabilityError(f"{provider} identity must use exact fields: {', '.join(sorted(allowed))}")
    if any(not isinstance(value, str) or not value for value in identity.values()):
        raise CapabilityError("provider identity values must be non-empty strings")
    return {key: identity[key] for key in sorted(identity)}


def _capability_result(
    project_root: str | Path,
    capability_id: str,
    *,
    state_dir: str | Path | None,
    schema: str,
    executable_resolver: Callable[[str], str | None],
    sandbox_runner: Callable[..., int] | None,
) -> dict[str, Any]:
    root, binding = _load_binding(project_root)
    if state_dir is None:
        raise CapabilityError("external state directory is required for provider discovery/status")
    state = Path(state_dir).expanduser().resolve()
    if state == root or root in state.parents or state in root.parents:
        raise CapabilityError("state directory must be external and non-overlapping with the project root")
    capability = _find_capability(binding, capability_id)
    provider = capability["provider"]
    identity = validate_provider_identity(provider, capability["target_identity"])
    holds: list[str] = []
    provider_status = None
    command = PROVIDER_STATUS_COMMANDS.get(capability_id)
    if command is not None:
        executable = executable_resolver(provider)
        provider_client = {"mode": "readonly_cli", "executable": str(Path(executable).resolve()) if executable else None}
        if not executable:
            holds.extend(("provider_client_unavailable", "credential_linkage_unresolved"))
        else:
            try:
                exit_code = (sandbox_runner or run_sandbox)(
                    root,
                    state,
                    command,
                    network=True,
                    suppress_output=True,
                )
            except SandboxError:
                holds.extend(("provider_sandbox_unavailable", "credential_linkage_unresolved"))
            else:
                provider_status = {"command": command, "exit_code": exit_code}
                if exit_code:
                    holds.extend(("provider_status_failed", "credential_linkage_unresolved"))
    else:
        provider_client = {"mode": "source_config_only", "executable": None}
        holds.append("credential_linkage_unresolved")
    credential_refs = capability["credential_refs"]
    return {
        "schema": schema,
        "capability_id": capability_id,
        "provider": provider,
        "operation": capability["operation"],
        "status": "hold" if holds else "ready",
        "holds": holds,
        "source_snapshot": capability["source_snapshot"],
        "target_identity": identity,
        "credential_refs": credential_refs,
        "provider_client": provider_client,
        "provider_status": provider_status,
    }


def discover_capability(
    project_root: str | Path,
    capability_id: str,
    *,
    state_dir: str | Path | None,
    executable_resolver: Callable[[str], str | None] = shutil.which,
    sandbox_runner: Callable[..., int] | None = None,
) -> dict[str, Any]:
    return _capability_result(
        project_root,
        capability_id,
        state_dir=state_dir,
        schema=DISCOVERY_SCHEMA,
        executable_resolver=executable_resolver,
        sandbox_runner=sandbox_runner,
    )


def status_capability(
    project_root: str | Path,
    capability_id: str,
    *,
    state_dir: str | Path | None,
    executable_resolver: Callable[[str], str | None] = shutil.which,
    sandbox_runner: Callable[..., int] | None = None,
) -> dict[str, Any]:
    return _capability_result(
        project_root,
        capability_id,
        state_dir=state_dir,
        schema=STATUS_SCHEMA,
        executable_resolver=executable_resolver,
        sandbox_runner=sandbox_runner,
    )


def plan_capability(project_root: str | Path, capability_id: str) -> dict[str, Any]:
    root, binding = _load_binding(project_root)
    capability = _find_capability(binding, capability_id)
    binding_scope = {
        "project": binding.get("project"),
        "runtime_lock_digest": binding.get("runtime_lock", {}).get("digest"),
        "capability": {
            "capability_id": capability["capability_id"],
            "kind": capability["kind"],
            "provider": capability["provider"],
            "operation": capability["operation"],
            "target_identity": capability["target_identity"],
            "dependencies": capability["dependencies"],
            "allowed_actions": capability["allowed_actions"],
        },
    }
    plan: dict[str, Any] = {
        "schema": PLAN_SCHEMA,
        "capability_id": capability_id,
        "kind": capability["kind"],
        "provider": capability["provider"],
        "operation": capability["operation"],
        "source_snapshot": source_snapshot_identity(root),
        "binding_scope_digest": _digest(binding_scope),
        "target_identity": capability["target_identity"],
        "dependencies": capability["dependencies"],
        "preflight_profile": capability["profiles"]["preflight"],
        "receipt_profile": capability["profiles"]["receipt"],
        "consumer_profile": capability["profiles"]["consumer"],
    }
    plan["plan_digest"] = _digest(plan)
    return plan


def _validate_approval(approval: object, plan: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(approval, dict):
        raise CapabilityError("approval receipt is required")
    expected = {
        "schema": APPROVAL_SCHEMA,
        "capability_id": plan["capability_id"],
        "operation": plan["operation"],
        "plan_digest": plan["plan_digest"],
        "binding_scope_digest": plan["binding_scope_digest"],
        "target_identity": plan["target_identity"],
    }
    if any(approval.get(key) != value for key, value in expected.items()):
        raise CapabilityError("approval receipt does not match capability scope and plan digest")
    if not isinstance(approval.get("approval_receipt_id"), str) or not approval["approval_receipt_id"]:
        raise CapabilityError("approval receipt ID is required")
    return approval


def apply_capability(
    project_root: str | Path,
    capability_id: str,
    *,
    approval: object,
    executors: Mapping[str, Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]],
) -> dict[str, Any]:
    _, binding = _load_binding(project_root)
    capability = _find_capability(binding, capability_id)
    if capability["kind"] == "runtime_contract":
        raise CapabilityError("runtime contracts cannot be applied")
    plan = plan_capability(project_root, capability_id)
    approved = _validate_approval(approval, plan)
    executor = executors.get(capability_id)
    if executor is None:
        raise CapabilityError(f"capability-specific executor is unavailable: {capability_id}")
    validate_provider_identity(capability["provider"], plan["target_identity"])
    receipt = executor(plan, approved)
    if not isinstance(receipt, dict) or receipt.get("schema") != RECEIPT_SCHEMA:
        raise CapabilityError("executor returned an invalid receipt")
    if receipt.get("capability_id") != capability_id or receipt.get("plan_digest") != plan["plan_digest"]:
        raise CapabilityError("executor receipt does not match the approved plan")
    return receipt
