from __future__ import annotations

import hashlib
import json
import os
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

TOOL_ID = "harness-project-binding"
BINDING_SCHEMA = "harness.project-binding.v1"
LOCK_SCHEMA = "harness.runtime-lock.v1"
CAPABILITY_GRAPH_SCHEMA = "harness.capability-graph.v1"
RUNTIME_ROOT = Path(__file__).resolve().parents[1]
MANAGED_PATHS = (
    ".harness/bin/harness-binding",
    ".harness/bin/harness-sandbox-run",
    ".harness/project-binding.json",
    ".harness/runtime.lock.json",
)


class BindingError(ValueError):
    pass


@dataclass(frozen=True)
class BindingInputs:
    project_id: str
    project_root: Path
    protected_branch: str
    railway_service: str
    runtime_version: str = "1"
    railway_project_id: str | None = None
    railway_environment_id: str | None = None
    railway_service_id: str | None = None
    vercel_org_id: str | None = None
    vercel_project_id: str | None = None
    vercel_target: str | None = None
    supabase_project_ref: str | None = None
    supabase_schema_migration_scope_id: str | None = None
    supabase_privileged_data_mutation_boundary_id: str | None = None
    n8n_instance_host: str | None = None
    n8n_workflow_id: str | None = None
    n8n_webhook_endpoint_sha256: str | None = None
    n8n_webhook_path_sha256: str | None = None
    n8n_callback_consumer_id: str | None = None

    def normalized(self) -> "BindingInputs":
        root = self.project_root.expanduser().resolve()
        values = (self.project_id, self.protected_branch, self.railway_service, self.runtime_version)
        if any(not isinstance(value, str) or not value.strip() for value in values):
            raise BindingError("project id, protected branch, Railway service, and runtime version are required")
        if not root.is_dir():
            raise BindingError(f"project root does not exist: {root}")

        def optional(value: str | None) -> str | None:
            if value is None:
                return None
            if not isinstance(value, str):
                raise BindingError("provider target identity values must be strings")
            return value.strip() or None

        endpoint_sha256 = optional(self.n8n_webhook_endpoint_sha256)
        path_sha256 = optional(self.n8n_webhook_path_sha256)
        for value in (endpoint_sha256, path_sha256):
            if value is not None and (
                len(value) != 64
                or any(character not in "0123456789abcdef" for character in value)
            ):
                raise BindingError("n8n webhook SHA256 values must be 64 lowercase hexadecimal characters")
        instance_host = optional(self.n8n_instance_host)
        if instance_host is not None and any(marker in instance_host for marker in ("://", "/", "?", "#", "@")):
            raise BindingError("n8n instance host must not contain a URL, path, query, fragment, or user info")
        return BindingInputs(
            project_id=self.project_id.strip(),
            project_root=root,
            protected_branch=self.protected_branch.strip(),
            railway_service=self.railway_service.strip(),
            runtime_version=self.runtime_version.strip(),
            railway_project_id=optional(self.railway_project_id),
            railway_environment_id=optional(self.railway_environment_id),
            railway_service_id=optional(self.railway_service_id),
            vercel_org_id=optional(self.vercel_org_id),
            vercel_project_id=optional(self.vercel_project_id),
            vercel_target=optional(self.vercel_target),
            supabase_project_ref=optional(self.supabase_project_ref),
            supabase_schema_migration_scope_id=optional(self.supabase_schema_migration_scope_id),
            supabase_privileged_data_mutation_boundary_id=optional(
                self.supabase_privileged_data_mutation_boundary_id
            ),
            n8n_instance_host=instance_host,
            n8n_workflow_id=optional(self.n8n_workflow_id),
            n8n_webhook_endpoint_sha256=endpoint_sha256,
            n8n_webhook_path_sha256=path_sha256,
            n8n_callback_consumer_id=optional(self.n8n_callback_consumer_id),
        )


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def source_snapshot_identity(project_root: Path) -> dict[str, str]:
    completed = subprocess.run(
        ["git", "-C", str(project_root), "rev-parse", "HEAD"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={"LANG": "C", "LC_ALL": "C", "PATH": os.defpath},
    )
    revision = completed.stdout.strip()
    if completed.returncode or not revision:
        raise BindingError("project root must have a committed Git HEAD")
    return {"kind": "git_commit", "revision": revision}


def _provider_targets(inputs: BindingInputs) -> dict[str, dict[str, str | None]]:
    return {
        "railway": {
            "project_id": inputs.railway_project_id,
            "environment_id": inputs.railway_environment_id,
            "service_id": inputs.railway_service_id,
            "service_name": inputs.railway_service,
        },
        "vercel": {
            "org_id": inputs.vercel_org_id,
            "project_id": inputs.vercel_project_id,
            "target": inputs.vercel_target,
        },
        "supabase_schema_migration": {
            "project_ref": inputs.supabase_project_ref,
            "schema_migration_scope_id": inputs.supabase_schema_migration_scope_id,
        },
        "supabase_privileged_data_mutation": {
            "project_ref": inputs.supabase_project_ref,
            "privileged_data_mutation_boundary_id": inputs.supabase_privileged_data_mutation_boundary_id,
        },
        "n8n": {
            "instance_host": inputs.n8n_instance_host,
            "workflow_id": inputs.n8n_workflow_id,
            "webhook_endpoint_sha256": inputs.n8n_webhook_endpoint_sha256,
            "webhook_path_sha256": inputs.n8n_webhook_path_sha256,
            "callback_consumer_id": inputs.n8n_callback_consumer_id,
        },
    }


def _capability_graph(
    inputs: BindingInputs,
    provider_targets: dict[str, dict[str, str | None]],
) -> dict[str, Any]:
    snapshot = source_snapshot_identity(inputs.project_root)

    def capability(
        capability_id: str,
        kind: str,
        provider: str,
        operation: str,
        target_identity: dict[str, str | None],
        credential_refs: list[str],
        dependencies: list[str],
    ) -> dict[str, Any]:
        actions = ["discovery", "plan", "status"]
        if kind == "local_operation":
            actions.append("apply")
        return {
            "capability_id": capability_id,
            "kind": kind,
            "provider": provider,
            "operation": operation,
            "source_snapshot": snapshot,
            "target_identity": target_identity,
            "credential_refs": credential_refs,
            "dependencies": dependencies,
            "allowed_actions": actions,
            "profiles": {
                "preflight": f"{capability_id}.preflight.v1",
                "receipt": f"{capability_id}.receipt.v1",
                "consumer": f"{capability_id}.consumer.v1",
            },
        }

    capabilities = [
        capability(
            "railway.deploy", "local_operation", "railway", "deploy",
            provider_targets["railway"],
            ["railway.cli-session"], [],
        ),
        capability(
            "vercel.deploy", "local_operation", "vercel", "deploy",
            provider_targets["vercel"], ["vercel.cli-session"], [],
        ),
        capability(
            "supabase.schema-migration", "local_operation", "supabase", "schema_migration",
            provider_targets["supabase_schema_migration"], ["supabase.cli-session"], [],
        ),
        capability(
            "supabase.privileged-data-mutation", "local_operation", "supabase", "bounded_privileged_data_mutation",
            provider_targets["supabase_privileged_data_mutation"], ["supabase.privileged-resolver"],
            ["supabase.schema-migration"],
        ),
        capability(
            "n8n.workflow-publish-activation", "local_operation", "n8n", "workflow_publish_activation",
            provider_targets["n8n"], ["n8n.credential-resolver"], [],
        ),
        capability(
            "n8n.async-effects-runtime", "runtime_contract", "n8n", "async_effects",
            provider_targets["n8n"], ["n8n.runtime-credential-resolver"],
            ["n8n.workflow-publish-activation"],
        ),
        capability(
            "vercel.revalidate-runtime", "runtime_contract", "vercel", "revalidate",
            provider_targets["vercel"], ["vercel.runtime-credential-resolver"],
            ["vercel.deploy"],
        ),
        capability(
            "deployed-api.db-write-runtime", "runtime_contract", "deployed-api", "db_write",
            {
                "railway_project_id": inputs.railway_project_id,
                "railway_environment_id": inputs.railway_environment_id,
                "railway_service_id": inputs.railway_service_id,
                "railway_service_name": inputs.railway_service,
                "supabase_project_ref": inputs.supabase_project_ref,
                "supabase_schema_migration_scope_id": inputs.supabase_schema_migration_scope_id,
            },
            ["deployed-api.runtime-credential-resolver"], ["railway.deploy", "supabase.schema-migration"],
        ),
    ]
    graph: dict[str, Any] = {
        "schema": CAPABILITY_GRAPH_SCHEMA,
        "source_snapshot": snapshot,
        "capabilities": capabilities,
    }
    graph["digest"] = hashlib.sha256(_canonical(graph)).hexdigest()
    return graph


def _desired(inputs: BindingInputs) -> dict[str, tuple[bytes, int]]:
    normalized = inputs.normalized()
    project = {
        "id": normalized.project_id,
        "root": str(normalized.project_root),
        "protected_branch": normalized.protected_branch,
        "railway_service": normalized.railway_service,
    }
    runtime_root = str(RUNTIME_ROOT)
    provider_targets = _provider_targets(normalized)
    capability_graph = _capability_graph(normalized, provider_targets)
    digest = hashlib.sha256(
        _canonical({
            "project": project,
            "runtime_root": runtime_root,
            "runtime_version": normalized.runtime_version,
            "capability_graph_digest": capability_graph["digest"],
        })
    ).hexdigest()
    lock = {
        "schema": LOCK_SCHEMA,
        "managed_by": TOOL_ID,
        "version": normalized.runtime_version,
        "root": runtime_root,
        "digest": digest,
        "provider_targets": provider_targets,
        "capability_graph": {
            "schema": capability_graph["schema"],
            "digest": capability_graph["digest"],
            "source_snapshot": capability_graph["source_snapshot"],
        },
    }
    binding = {
        "schema": BINDING_SCHEMA,
        "managed_by": TOOL_ID,
        "project": project,
        "provider_targets": provider_targets,
        "runtime_lock": {
            "path": ".harness/runtime.lock.json",
            "version": normalized.runtime_version,
            "digest": digest,
        },
        "capability_graph": capability_graph,
        "verification": {
            "clean_worktree_required": True,
            "external_state_dir_required": True,
            "sandbox_backend": "macos-sandbox-exec",
            "network_default": "deny",
        },
        "managed_files": list(MANAGED_PATHS),
    }
    launcher_prefix = (
        "#!/bin/sh\n"
        "# managed-by: harness-project-binding\n"
        f"RUNTIME_ROOT={shlex.quote(runtime_root)}\n"
        'PYTHONPATH="$RUNTIME_ROOT${PYTHONPATH:+:$PYTHONPATH}"\n'
        "export PYTHONPATH\n"
    )
    binding_launcher = (launcher_prefix + 'exec "${PYTHON:-python3.11}" -m harness_runtime.binding_cli "$@"\n').encode()
    sandbox_launcher = (
        launcher_prefix + 'exec "${PYTHON:-python3.11}" -m harness_runtime.binding_cli sandbox "$@"\n'
    ).encode()
    return {
        MANAGED_PATHS[0]: (binding_launcher, 0o755),
        MANAGED_PATHS[1]: (sandbox_launcher, 0o755),
        MANAGED_PATHS[2]: (_json_bytes(binding), 0o644),
        MANAGED_PATHS[3]: (_json_bytes(lock), 0o644),
    }


def _owned(path: Path) -> bool:
    if path.name not in {"project-binding.json", "runtime.lock.json"}:
        try:
            return b"\n# managed-by: harness-project-binding\n" in path.read_bytes()[:128]
        except OSError:
            return False
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return value.get("managed_by") == TOOL_ID


def inspect_binding(project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve()
    binding_path = root / ".harness/project-binding.json"
    if not binding_path.exists():
        return {"status": "unbound", "project_root": str(root)}
    if not _owned(binding_path):
        return {"status": "conflict", "project_root": str(root), "path": ".harness/project-binding.json"}
    try:
        binding = json.loads(binding_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BindingError(f"cannot inspect binding: {exc}") from exc
    missing = [path for path in binding.get("managed_files", []) if not (root / path).is_file()]
    return {"status": "drifted" if missing else "bound", "project_root": str(root), "binding": binding, "missing": missing}


def plan_binding(inputs: BindingInputs) -> dict[str, Any]:
    normalized = inputs.normalized()
    actions: list[dict[str, str]] = []
    for relative, (content, _) in _desired(normalized).items():
        path = normalized.project_root / relative
        if not path.exists():
            operation = "create"
        elif path.is_file() and path.read_bytes() == content:
            operation = "noop"
        elif _owned(path):
            operation = "update"
        else:
            operation = "conflict"
        actions.append({"operation": operation, "path": relative})
    return {"project_root": str(normalized.project_root), "actions": actions, "changed": any(a["operation"] in {"create", "update"} for a in actions)}


def _write(path: Path, content: bytes, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(content)
    os.chmod(temporary, mode)
    temporary.replace(path)


def apply_binding(inputs: BindingInputs) -> dict[str, Any]:
    normalized = inputs.normalized()
    plan = plan_binding(normalized)
    conflicts = [action["path"] for action in plan["actions"] if action["operation"] == "conflict"]
    if conflicts:
        raise BindingError("refusing to overwrite unmanaged files: " + ", ".join(conflicts))
    desired = _desired(normalized)
    for action in plan["actions"]:
        if action["operation"] in {"create", "update"}:
            content, mode = desired[action["path"]]
            _write(normalized.project_root / action["path"], content, mode)
    return plan


def reconcile_legacy(project_root: str | Path, *, apply: bool = False) -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve()
    manifest_path = root / ".harness/legacy-files.json"
    if not manifest_path.exists():
        return {"project_root": str(root), "actions": [], "changed": False}
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BindingError(f"cannot read legacy ownership manifest: {exc}") from exc
    files = manifest.get("files")
    if manifest.get("managed_by") != TOOL_ID or not isinstance(files, dict):
        raise BindingError("legacy ownership manifest is not tool-managed")

    actions: list[dict[str, str]] = []
    retained: dict[str, str] = {}
    removable: list[Path] = []
    for relative, expected_digest in files.items():
        if not isinstance(relative, str) or not isinstance(expected_digest, str):
            raise BindingError("legacy ownership manifest contains invalid entries")
        path = (root / relative).resolve()
        if path == root or root not in path.parents:
            actions.append({"operation": "retain-invalid", "path": relative})
            retained[relative] = expected_digest
        elif not path.is_file():
            actions.append({"operation": "retire-missing", "path": relative})
        elif hashlib.sha256(path.read_bytes()).hexdigest() == expected_digest:
            actions.append({"operation": "remove", "path": relative})
            removable.append(path)
        else:
            actions.append({"operation": "retain-modified", "path": relative})
            retained[relative] = expected_digest

    if apply:
        for path in removable:
            path.unlink()
        if retained:
            _write(manifest_path, _json_bytes({"managed_by": TOOL_ID, "files": retained}), 0o644)
        else:
            manifest_path.unlink()
    return {
        "project_root": str(root),
        "actions": actions,
        "changed": bool(removable or any(action["operation"] == "retire-missing" for action in actions)),
    }