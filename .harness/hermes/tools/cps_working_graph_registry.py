#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
from copy import deepcopy
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import fcntl

from cps_runtime_navigation import SEMANTIC_PROVENANCE_FIELDS, validate_semantic_provenance

ADDENDUM_KEYS = {"observations", "source_refs"}
EXECUTION_INSTRUCTION = "Perform only the scoped Git closure described by this packet: run verification_command if present; stage only scoped_paths; create the exact commit_message; push only repository.branch to repository.upstream; then report facts."
SEMANTIC_ADDENDUM_KEYS = {
    "maat_body", "verdict", "C", "P", "S", "AC", "ordered_P", "ordered_S",
    "selected_agents", "audit_scope", "edge", "order", "actor", "closure",
    "task_AC", "evidence",
}
EXECUTION_RECEIPT_REQUIRED_FIELDS = {
    "parent_edge_ref", "status", "changed_paths", "return_to_node_ref",
}
EXECUTION_RECEIPT_IDENTITY_FIELDS = {
    "work_id", "graph_ref", "graph_revision", "graph_digest", "stage_ref",
    "owner_ref", "run_handle", "attempt", "immutable_body_digest",
}
EXECUTION_RECEIPT_W2_IDENTITY_FIELDS = EXECUTION_RECEIPT_IDENTITY_FIELDS - {"work_id"}
EXECUTION_RECEIPT_STATUSES = {"observed", "pass", "fail", "blocked"}
EXECUTION_RECEIPT_PARTIAL_MUTATION_DISPOSITIONS = {"reconcile", "revert", "owner_hold"}
EXECUTION_RECEIPT_SEMANTIC_KEYS = {
    "C", "C_boundary", "P", "P_order", "S", "S_mapping", "AC", "task_AC",
    "graph_delta", "semantic_verdict", "owner_selection", "route_selection",
}
RETURN_EDGE_FIELDS = {"kind", "id", "from", "to", "parent_edge_ref", "resume_if", "status"}
RETURN_EDGE_STATUSES = {"pending", "eligible", "satisfied", "blocked"}
RESUME_IF_KINDS = {
    "evidence_ref", "derived_c_ac_satisfied", "execution_terminal_unblocked",
}
RESUME_IF_FIELDS = {"kind", "ref"}
DERIVED_C_LINEAGE_FIELDS = {
    "issued_by", "status", "derived_c_ref", "parent_work_id", "parent_graph_ref",
    "parent_graph_revision", "parent_graph_digest", "blocked_receipt_ref",
    "parent_edge_ref", "return_to_node_ref",
}
PREAUTHORIZED_TRANSITION_FIELDS = {
    "id", "issued_by", "authority_revision", "authority_digest",
    "source_state_ref", "source_lifecycle", "trigger", "target",
    "allowed_delta_paths", "forbidden_delta_paths", "expires_on_revision_change",
    "replay_policy", "failure_disposition",
}
PREAUTHORIZED_TRIGGER_FIELDS = {
    "predicate_id", "predicate_version", "execution_case_refs",
    "required_lane_B_AC_refs", "required_evidence_refs",
}
PREAUTHORIZED_TARGET_FIELDS = {"target_state_ref", "target_lifecycle"}
MATERIALIZED_TRANSITION_FIELDS = {
    "transition_id", "authorization_digest", "predicate_id", "predicate_version",
    "source_state_ref", "source_lifecycle", "target_lifecycle", "evidence_digests",
    "authority_revision", "authority_digest", "resulting_revision", "resulting_digest",
    "materialization_ref",
}


class RegistryError(RuntimeError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def _parse_scalar(text: str) -> Any:
    value = text.strip()
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value.strip("'\"")


def load_json_or_yaml(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        value = {}
        for raw in text.splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if ":" not in line or raw[:1].isspace():
                raise RegistryError("YAML fallback supports flat mappings only")
            key, scalar = line.split(":", 1)
            value[key.strip()] = _parse_scalar(scalar)
    if not isinstance(value, dict):
        raise RegistryError("document must be an object")
    return value


def _validate_maat_body(body: Any) -> None:
    if not isinstance(body, dict):
        raise RegistryError("maat_body must be an object")
    if "returns_to" not in body:
        return
    edges = body["returns_to"]
    if not isinstance(edges, list):
        raise RegistryError("HOLD_RETURN_EDGE_SCHEMA")
    ids: set[str] = set()
    for edge in edges:
        if not isinstance(edge, dict) or set(edge) != RETURN_EDGE_FIELDS:
            raise RegistryError("HOLD_RETURN_EDGE_SCHEMA")
        if edge["kind"] != "returns_to" or edge["status"] not in RETURN_EDGE_STATUSES:
            raise RegistryError("HOLD_RETURN_EDGE_SCHEMA")
        if any(not isinstance(edge[field], str) or not edge[field] for field in (
            "id", "from", "to", "parent_edge_ref",
        )):
            raise RegistryError("HOLD_RETURN_EDGE_SCHEMA")
        if edge["id"] in ids:
            raise RegistryError("HOLD_RETURN_EDGE_SCHEMA")
        ids.add(edge["id"])
        resume_if = edge["resume_if"]
        if not isinstance(resume_if, list) or len(resume_if) != len(RESUME_IF_KINDS):
            raise RegistryError("HOLD_RETURN_EDGE_SCHEMA")
        if any(
            not isinstance(condition, dict)
            or set(condition) != RESUME_IF_FIELDS
            or condition.get("kind") not in RESUME_IF_KINDS
            or not isinstance(condition.get("ref"), str)
            or not condition["ref"]
            for condition in resume_if
        ) or {condition["kind"] for condition in resume_if} != RESUME_IF_KINDS:
            raise RegistryError("HOLD_RETURN_EDGE_SCHEMA")
    if "derived_c_lineage" in body:
        lineage = body.get("derived_c_lineage")
        validate_accepted_derived_c_lineage(body, {
            field: lineage.get(field) if isinstance(lineage, dict) else None
            for field in DERIVED_C_LINEAGE_FIELDS - {"issued_by", "status", "derived_c_ref"}
        })


def validate_accepted_derived_c_lineage(body: Any, parent_binding: Any) -> bool:
    if not isinstance(body, dict) or not isinstance(parent_binding, dict):
        raise RegistryError("HOLD_RETURN_EDGE")
    lineage = body.get("derived_c_lineage")
    binding_fields = DERIVED_C_LINEAGE_FIELDS - {"issued_by", "status", "derived_c_ref"}
    edges = body.get("returns_to")
    if (
        not isinstance(lineage, dict)
        or set(lineage) != DERIVED_C_LINEAGE_FIELDS
        or lineage.get("issued_by") != "maat"
        or lineage.get("status") != "accepted"
        or set(parent_binding) != binding_fields
        or any(lineage.get(field) != parent_binding.get(field) for field in binding_fields)
        or not isinstance(lineage.get("derived_c_ref"), str)
        or not lineage["derived_c_ref"]
        or type(lineage.get("parent_graph_revision")) is not int
        or lineage["parent_graph_revision"] < 1
        or not _is_sha256(lineage.get("parent_graph_digest"))
        or not isinstance(edges, list)
        or not edges
        or any(
            edge.get("from") != lineage["derived_c_ref"]
            or edge.get("parent_edge_ref") != lineage["parent_edge_ref"]
            or edge.get("to") != lineage["return_to_node_ref"]
            for edge in edges if isinstance(edge, dict)
        )
    ):
        raise RegistryError("HOLD_RETURN_EDGE")
    return True


def validate_return_status_transition(source: Any, target: Any) -> tuple[str, str]:
    if (source, target) not in {("pending", "eligible"), ("eligible", "satisfied")}:
        raise RegistryError("HOLD_RETURN_EDGE")
    return source, target


def _provenance_body(body: dict[str, Any]) -> dict[str, Any]:
    value = deepcopy(body)
    value.pop("returns_to", None)
    value.pop("derived_c_lineage", None)
    return value


def _valid_semantic_provenance(binding: Any, body: dict[str, Any]) -> bool:
    return validate_semantic_provenance(binding, _provenance_body(body))["status"] == "pass"


def _contains_keys(value: Any, keys: set[str]) -> bool:
    if isinstance(value, dict):
        return bool(set(value).intersection(keys)) or any(
            _contains_keys(item, keys) for item in value.values()
        )
    if isinstance(value, (list, tuple, set, frozenset)):
        return any(_contains_keys(item, keys) for item in value)
    return False


def _contains_semantic_key(value: Any) -> bool:
    return _contains_keys(value, SEMANTIC_ADDENDUM_KEYS)


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _unique_strings(value: Any, *, allow_empty: bool = False) -> bool:
    return (
        isinstance(value, list)
        and (allow_empty or bool(value))
        and all(isinstance(item, str) and item for item in value)
        and len(value) == len(set(value))
    )


def _validate_preauthorization(authorization: Any) -> None:
    if not isinstance(authorization, dict) or set(authorization) != PREAUTHORIZED_TRANSITION_FIELDS:
        raise RegistryError("HOLD_PREAUTH_SCOPE")
    trigger = authorization.get("trigger")
    target = authorization.get("target")
    if (
        authorization.get("issued_by") != "maat"
        or not isinstance(authorization.get("id"), str) or not authorization["id"]
        or type(authorization.get("authority_revision")) is not int
        or authorization["authority_revision"] < 1
        or not _is_sha256(authorization.get("authority_digest"))
        or not isinstance(authorization.get("source_state_ref"), str)
        or not authorization["source_state_ref"]
        or not isinstance(authorization.get("source_lifecycle"), str)
        or not authorization["source_lifecycle"]
        or not isinstance(trigger, dict)
        or set(trigger) != PREAUTHORIZED_TRIGGER_FIELDS
        or trigger.get("predicate_id") not in {
            "lane_b_exact_pass_v1", "blocked_parent_exact_resume_v1",
        }
        or trigger.get("predicate_version") != "1"
        or any(not _unique_strings(trigger.get(field)) for field in (
            "execution_case_refs", "required_lane_B_AC_refs", "required_evidence_refs",
        ))
        or not isinstance(target, dict)
        or set(target) != PREAUTHORIZED_TARGET_FIELDS
        or not isinstance(target.get("target_state_ref"), str)
        or not target["target_state_ref"]
        or not isinstance(target.get("target_lifecycle"), str)
        or not target["target_lifecycle"]
        or not _unique_strings(authorization.get("allowed_delta_paths"))
        or not _unique_strings(authorization.get("forbidden_delta_paths"), allow_empty=True)
        or authorization.get("expires_on_revision_change") is not True
        or authorization.get("replay_policy") != "idempotent"
        or authorization.get("failure_disposition") != "hold_no_write"
    ):
        raise RegistryError("HOLD_PREAUTH_SCOPE")


def _resolve_pointer(document: dict[str, Any], pointer: str) -> tuple[Any, str]:
    if not pointer.startswith("/"):
        raise RegistryError("HOLD_PREAUTH_SCOPE")
    tokens = [token.replace("~1", "/").replace("~0", "~") for token in pointer[1:].split("/")]
    parent: Any = document
    for token in tokens[:-1]:
        if isinstance(parent, dict) and token in parent:
            parent = parent[token]
        elif isinstance(parent, list) and token.isdigit() and int(token) < len(parent):
            parent = parent[int(token)]
        else:
            raise RegistryError("HOLD_PREAUTH_SCOPE")
    if not tokens or not isinstance(parent, dict) or tokens[-1] not in parent:
        raise RegistryError("HOLD_PREAUTH_SCOPE")
    return parent, tokens[-1]


def _valid_transition_state(graph: dict[str, Any]) -> bool:
    authorizations = graph.get("pre_authorized_transitions")
    materialized = graph.get("materialized_transitions")
    if not isinstance(authorizations, list) or not isinstance(materialized, list):
        return False
    try:
        for authorization in authorizations:
            _validate_preauthorization(authorization)
    except RegistryError:
        return False
    authorization_ids = [item["id"] for item in authorizations]
    transition_ids: list[str] = []
    for item in materialized:
        if not isinstance(item, dict) or set(item) != MATERIALIZED_TRANSITION_FIELDS:
            return False
        transition_id = item.get("transition_id")
        reference_body = dict(item)
        materialization_ref = reference_body.pop("materialization_ref", None)
        if (
            not isinstance(transition_id, str) or not transition_id
            or item.get("predicate_id") not in {"lane_b_exact_pass_v1", "blocked_parent_exact_resume_v1"}
            or item.get("predicate_version") != "1"
            or any(not isinstance(item.get(field), str) or not item[field] for field in (
                "source_state_ref", "source_lifecycle", "target_lifecycle",
            ))
            or any(not _is_sha256(item.get(field)) for field in (
                "authorization_digest", "authority_digest", "resulting_digest",
            ))
            or type(item.get("authority_revision")) is not int
            or type(item.get("resulting_revision")) is not int
            or item["authority_revision"] < 1
            or item["resulting_revision"] != item["authority_revision"] + 1
            or not isinstance(item.get("evidence_digests"), dict)
            or not item["evidence_digests"]
            or any(not isinstance(ref, str) or not ref or not _is_sha256(digest) for ref, digest in item["evidence_digests"].items())
            or materialization_ref != f"preauth:{graph.get('work_id')}:{_digest(reference_body)}"
        ):
            return False
        transition_ids.append(transition_id)
    return len(authorization_ids) == len(set(authorization_ids)) and len(transition_ids) == len(set(transition_ids))


def _validate_execution_receipt_identity(work_id: str, receipt: dict[str, Any]) -> bool:
    if not set(receipt).intersection(EXECUTION_RECEIPT_W2_IDENTITY_FIELDS):
        return False
    missing = EXECUTION_RECEIPT_IDENTITY_FIELDS.difference(receipt)
    if missing:
        raise RegistryError(f"execution receipt missing identity fields: {', '.join(sorted(missing))}")
    if receipt["work_id"] != work_id:
        raise RegistryError("execution receipt work_id mismatch")
    if any(
        not isinstance(receipt[field], str) or not receipt[field]
        for field in ("work_id", "graph_ref", "stage_ref", "owner_ref", "run_handle")
    ):
        raise RegistryError("execution receipt identity refs must be non-empty strings")
    if any(
        type(receipt[field]) is not int or receipt[field] < 1
        for field in ("graph_revision", "attempt")
    ):
        raise RegistryError("execution receipt identity revisions must be positive integers")
    if not _is_sha256(receipt["graph_digest"]) or not _is_sha256(receipt["immutable_body_digest"]):
        raise RegistryError("execution receipt identity digests must be lowercase sha256")
    return True


class WorkingGraphRegistry:
    def __init__(self, graph_root: Path):
        self.root = Path(graph_root)

    def _path(self, work_id: str) -> Path:
        if not work_id or "/" in work_id or work_id in {".", ".."}:
            raise RegistryError("invalid work_id")
        return self.root / f"{work_id}.yaml"

    def _execution_receipts_path(self, work_id: str) -> Path:
        self._path(work_id)
        return self.root / f"{work_id}.execution-receipts.json"

    @contextmanager
    def _graph_lock(self):
        descriptor = os.open(self.root, os.O_RDONLY)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)

    def append_execution_receipt(self, work_id: str, receipt: dict[str, Any]) -> dict[str, Any]:
        graph = self.load(work_id)
        if not isinstance(receipt, dict):
            raise RegistryError("execution receipt must be an object")
        missing = EXECUTION_RECEIPT_REQUIRED_FIELDS.difference(receipt)
        if missing:
            raise RegistryError(f"execution receipt missing required fields: {', '.join(sorted(missing))}")
        if _contains_keys(receipt.get("facts"), EXECUTION_RECEIPT_W2_IDENTITY_FIELDS):
            raise RegistryError("execution receipt facts cannot contain W2 identity fields")
        if receipt.get("work_id") not in (None, work_id):
            raise RegistryError("execution receipt work_id mismatch")
        has_w2_identity = _validate_execution_receipt_identity(work_id, receipt)
        if has_w2_identity and (
            receipt["graph_ref"] != str(self._path(work_id).resolve())
            or receipt["graph_revision"] != graph.get("revision")
            or receipt["graph_digest"] != graph.get("maat_body_digest")
        ):
            raise RegistryError("execution receipt graph binding mismatch")
        if _contains_keys(receipt, EXECUTION_RECEIPT_SEMANTIC_KEYS):
            raise RegistryError("execution receipt cannot contain semantic fields")
        if any(not isinstance(receipt[field], str) or not receipt[field] for field in (
            "parent_edge_ref", "return_to_node_ref",
        )):
            raise RegistryError("execution receipt continuity refs must be non-empty strings")
        if not isinstance(receipt["status"], str) or receipt["status"] not in EXECUTION_RECEIPT_STATUSES:
            raise RegistryError("invalid execution receipt status")
        if not isinstance(receipt["changed_paths"], list) or any(
            not isinstance(path, str) for path in receipt["changed_paths"]
        ):
            raise RegistryError("execution receipt changed_paths must be a list of strings")
        if receipt["status"] == "blocked" and receipt["changed_paths"] and (
            receipt.get("partial_mutation_disposition")
            not in EXECUTION_RECEIPT_PARTIAL_MUTATION_DISPOSITIONS
        ):
            raise RegistryError("blocked execution receipt with changed_paths requires a valid partial_mutation_disposition")

        stored_receipt = deepcopy(receipt)
        stored_receipt.setdefault("family", "execution_receipt")
        stored_receipt.setdefault("work_id", work_id)
        stored_receipt.setdefault(
            "receipt_ref",
            f"execution_receipt:{work_id}:{_digest(stored_receipt)}",
        )
        path = self._execution_receipts_path(work_id)
        sidecar = load_json_or_yaml(path) if path.is_file() else {"work_id": work_id, "receipts": []}
        if sidecar.get("work_id") != work_id or not isinstance(sidecar.get("receipts"), list):
            raise RegistryError("invalid execution receipt sidecar")
        sidecar["receipts"].append(stored_receipt)
        _write(path, sidecar)
        return deepcopy(stored_receipt)

    def append_continuation_receipt(
        self,
        work_id: str,
        *,
        parent_receipt_ref: str,
        parent_edge_ref: str,
        returns_to_ref: str,
        return_to_node_ref: str,
    ) -> dict[str, Any]:
        refs = (parent_receipt_ref, parent_edge_ref, returns_to_ref, return_to_node_ref)
        if any(not isinstance(ref, str) or not ref for ref in refs):
            raise RegistryError("continuation receipt refs must be non-empty strings")
        with self._graph_lock():
            return self._append_continuation_receipt_unlocked(
                work_id,
                parent_receipt_ref=parent_receipt_ref,
                parent_edge_ref=parent_edge_ref,
                returns_to_ref=returns_to_ref,
                return_to_node_ref=return_to_node_ref,
            )

    def _append_continuation_receipt_unlocked(
        self,
        work_id: str,
        *,
        parent_receipt_ref: str,
        parent_edge_ref: str,
        returns_to_ref: str,
        return_to_node_ref: str,
    ) -> dict[str, Any]:
        self.load(work_id)
        path = self._execution_receipts_path(work_id)
        if not path.is_file():
            raise RegistryError("execution receipt unavailable")
        sidecar = load_json_or_yaml(path)
        receipts = sidecar.get("receipts")
        if sidecar.get("work_id") != work_id or not isinstance(receipts, list):
            raise RegistryError("invalid execution receipt sidecar")
        parent = next(
            (item for item in receipts if isinstance(item, dict) and item.get("receipt_ref") == parent_receipt_ref),
            None,
        )
        if parent is None or parent.get("family") != "execution_receipt":
            raise RegistryError("execution receipt unavailable")
        duplicate = next(
            (
                item for item in receipts
                if isinstance(item, dict)
                and item.get("family") == "continuation_receipt"
                and item.get("parent_receipt_ref") == parent_receipt_ref
                and item.get("returns_to_ref") == returns_to_ref
            ),
            None,
        )
        if duplicate is not None:
            return deepcopy(duplicate)
        identity = {
            "parent_receipt_ref": parent_receipt_ref,
            "returns_to_ref": returns_to_ref,
        }
        continuation = {
            "family": "continuation_receipt",
            "receipt_ref": f"continuation_receipt:{work_id}:{_digest(identity)}",
            "parent_receipt_ref": parent_receipt_ref,
            "work_id": work_id,
            "parent_edge_ref": parent_edge_ref,
            "returns_to_ref": returns_to_ref,
            "return_to_node_ref": return_to_node_ref,
            "disposition": "continue",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
        receipts.append(continuation)
        _write(path, sidecar)
        return deepcopy(continuation)

    def resume_parent_edge(self, work_id: str, parent_edge_ref: str) -> dict[str, str]:
        self.load(work_id)
        if not isinstance(parent_edge_ref, str) or not parent_edge_ref:
            raise RegistryError("parent_edge_ref must be a non-empty string")
        path = self._execution_receipts_path(work_id)
        if not path.is_file():
            raise RegistryError("execution receipt unavailable")
        sidecar = load_json_or_yaml(path)
        receipts = sidecar.get("receipts")
        if sidecar.get("work_id") != work_id or not isinstance(receipts, list):
            raise RegistryError("invalid execution receipt sidecar")
        receipt = next(
            (item for item in reversed(receipts) if isinstance(item, dict) and item.get("parent_edge_ref") == parent_edge_ref),
            None,
        )
        if receipt is None:
            raise RegistryError("execution receipt unavailable")
        status = receipt.get("status")
        if status == "blocked":
            disposition = "reconcile_or_return" if receipt.get("changed_paths") else "resume_or_retry"
        elif status == "pass":
            disposition = "continue"
        else:
            disposition = "resume_or_retry"
        return {"parent_edge_ref": parent_edge_ref, "disposition": disposition}

    def load(self, work_id: str) -> dict[str, Any]:
        path = self._path(work_id)
        if not path.is_file():
            raise RegistryError("HOLD_SOURCE_UNAVAILABLE")
        return load_json_or_yaml(path)

    def create(self, work_id: str, maat_body: dict[str, Any], *, split_from: str | None = None, semantic_provenance_binding: dict[str, Any] | None = None, pre_authorized_transitions: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        _validate_maat_body(maat_body)
        if not _valid_semantic_provenance(semantic_provenance_binding, maat_body):
            raise RegistryError("HOLD_UNMAPPED_SEMANTIC_FIELD")
        authorizations = [] if pre_authorized_transitions is None else pre_authorized_transitions
        if not isinstance(authorizations, list):
            raise RegistryError("HOLD_PREAUTH_SCOPE")
        for authorization in authorizations:
            _validate_preauthorization(authorization)
            if (
                authorization["authority_revision"] != 1
                or authorization["authority_digest"] != _digest(maat_body)
            ):
                raise RegistryError("HOLD_PREAUTH_STALE")
        if len({authorization["id"] for authorization in authorizations}) != len(authorizations):
            raise RegistryError("HOLD_PREAUTH_SCOPE")
        path = self._path(work_id)
        if path.exists():
            raise RegistryError("current graph source already exists")
        graph = {
            "family": "cps_working_graph",
            "work_id": work_id,
            "revision": 1,
            "maat_body": deepcopy(maat_body),
            "maat_body_digest": _digest(maat_body),
            "pre_authorized_transitions": deepcopy(authorizations),
            "materialized_transitions": [],
            "hermes_kann_addendum": {"observations": [], "source_refs": []},
        }
        if split_from:
            graph["split_from"] = split_from
        graph["semantic_provenance_binding"] = deepcopy(semantic_provenance_binding)
        _write(path, graph)
        if not self.verify_readback(work_id, maat_body, semantic_provenance_binding):
            path.unlink(missing_ok=True)
            raise RegistryError("HOLD_WRITE_READBACK")
        return graph

    def materialize_pre_authorized_transition(
        self,
        work_id: str,
        transition_id: str,
        materialization_binding: dict[str, Any],
        ref_loader: Callable[[str], dict[str, Any]],
    ) -> dict[str, Any]:
        with self._graph_lock():
            path = self._path(work_id)
            graph = self.load(work_id)
            materialized = graph.get("materialized_transitions")
            if not isinstance(materialized, list):
                raise RegistryError("HOLD_PREAUTH_READBACK")
            replay = next(
                (
                    item for item in materialized
                    if isinstance(item, dict) and item.get("transition_id") == transition_id
                ),
                None,
            )
            if replay is not None:
                return deepcopy(replay)

            authorizations = graph.get("pre_authorized_transitions")
            matches = [
                item for item in authorizations or []
                if isinstance(item, dict) and item.get("id") == transition_id
            ]
            if not isinstance(authorizations, list) or len(matches) != 1:
                raise RegistryError("HOLD_PREAUTH_MISSING")
            authorization = matches[0]
            _validate_preauthorization(authorization)

            current_identity = {
                "graph_ref": str(path.resolve()),
                "graph_revision": graph.get("revision"),
                "graph_digest": graph.get("maat_body_digest"),
            }
            if (
                not isinstance(materialization_binding, dict)
                or any(materialization_binding.get(key) != value for key, value in current_identity.items())
                or authorization["authority_revision"] != graph.get("revision")
                or authorization["authority_digest"] != graph.get("maat_body_digest")
            ):
                raise RegistryError("HOLD_PREAUTH_STALE")

            source_ref = authorization["source_state_ref"]
            target_ref = authorization["target"]["target_state_ref"]
            forbidden = {part.lower() for part in target_ref.split("/")}
            common_scope_invalid = (
                source_ref != target_ref
                or authorization["allowed_delta_paths"] != [target_ref]
                or target_ref in authorization["forbidden_delta_paths"]
                or forbidden.intersection({"goal", "root_goal", "owner", "route", "c", "p"})
            )
            if common_scope_invalid or not (target_ref.endswith("/lifecycle") or target_ref.endswith("/status")):
                raise RegistryError("HOLD_PREAUTH_SCOPE")
            parent, scalar = _resolve_pointer(graph, source_ref)
            if (
                not isinstance(parent.get(scalar), str)
                or parent[scalar] != authorization["source_lifecycle"]
            ):
                raise RegistryError("HOLD_PREAUTH_STALE")

            trigger = authorization["trigger"]
            expected_refs = (
                trigger["execution_case_refs"]
                + trigger["required_lane_B_AC_refs"]
                + trigger["required_evidence_refs"]
            )
            evidence_digests = materialization_binding.get("evidence_digests")
            if not isinstance(evidence_digests, dict) or set(evidence_digests) != set(expected_refs):
                raise RegistryError("HOLD_PREAUTH_PREDICATE")
            documents: dict[str, dict[str, Any]] = {}
            try:
                for ref in expected_refs:
                    document = ref_loader(ref)
                    if (
                        not isinstance(document, dict)
                        or document.get("ref") != ref
                        or evidence_digests.get(ref) != _digest(document)
                        or any(document.get(key) != value for key, value in current_identity.items())
                    ):
                        raise RegistryError("HOLD_PREAUTH_PREDICATE")
                    documents[ref] = document
            except RegistryError:
                raise
            except Exception as error:
                raise RegistryError("HOLD_PREAUTH_PREDICATE") from error

            execution_cases = [documents[ref] for ref in trigger["execution_case_refs"]]
            lane_b_ac = [documents[ref] for ref in trigger["required_lane_B_AC_refs"]]
            predicate_id = trigger["predicate_id"]
            return_transition = target_ref.endswith("/status")
            if return_transition:
                try:
                    validate_return_status_transition(authorization["source_lifecycle"], authorization["target"]["target_lifecycle"])
                except RegistryError as error:
                    raise RegistryError("HOLD_PREAUTH_SCOPE") from error
                predicate_passed = (
                    predicate_id == "lane_b_exact_pass_v1"
                    and all(item.get("event_kind") == "terminal" and item.get("status") == "pass" for item in execution_cases)
                )
            elif predicate_id == "lane_b_exact_pass_v1":
                predicate_passed = (
                    authorization["target"]["target_lifecycle"] == "satisfied"
                    and all(item.get("event_kind") == "terminal" and item.get("status") == "pass" for item in execution_cases)
                )
            else:
                predicate_passed = (
                    authorization["source_lifecycle"] == "blocked"
                    and authorization["target"]["target_lifecycle"] == "resumable"
                    and all(item.get("event_kind") == "terminal" and item.get("status") == "blocked" for item in execution_cases)
                )
            if not predicate_passed or any(item.get("status") != "satisfied" for item in lane_b_ac):
                raise RegistryError("HOLD_PREAUTH_PREDICATE")

            preimage = path.read_bytes()
            next_body = deepcopy(graph["maat_body"])
            if return_transition:
                lineage = next_body.get("derived_c_lineage")
                validate_accepted_derived_c_lineage(next_body, {
                    field: lineage.get(field) if isinstance(lineage, dict) else None
                    for field in DERIVED_C_LINEAGE_FIELDS - {"issued_by", "status", "derived_c_ref"}
                })
            target_parent, target_scalar = _resolve_pointer({"maat_body": next_body}, target_ref)
            target_parent[target_scalar] = authorization["target"]["target_lifecycle"]
            next_digest = _digest(next_body)
            result = {
                "transition_id": transition_id,
                "authorization_digest": _digest(authorization),
                "predicate_id": predicate_id,
                "predicate_version": trigger["predicate_version"],
                "source_state_ref": source_ref,
                "source_lifecycle": authorization["source_lifecycle"],
                "target_lifecycle": authorization["target"]["target_lifecycle"],
                "evidence_digests": deepcopy(evidence_digests),
                "authority_revision": graph["revision"],
                "authority_digest": graph["maat_body_digest"],
                "resulting_revision": graph["revision"] + 1,
                "resulting_digest": next_digest,
            }
            result["materialization_ref"] = f"preauth:{work_id}:{_digest(result)}"
            graph["revision"] = result["resulting_revision"]
            graph["maat_body"] = next_body
            graph["maat_body_digest"] = next_digest
            materialized.append(result)
            try:
                _write(path, graph)
                readback = self.load(work_id)
                valid = (
                    readback.get("revision") == result["resulting_revision"]
                    and readback.get("maat_body_digest") == result["resulting_digest"]
                    and readback.get("materialized_transitions", [])[-1:] == [result]
                    and self.verify_readback(work_id, next_body)
                )
            except Exception:
                valid = False
            if not valid:
                temporary = path.with_suffix(".tmp")
                temporary.write_bytes(preimage)
                temporary.replace(path)
                raise RegistryError("HOLD_PREAUTH_READBACK")
            return deepcopy(result)

    def verify_readback(self, work_id: str, issued_maat_body: dict[str, Any] | None = None, semantic_provenance_binding: dict[str, Any] | None = None) -> bool:
        graph = self.load(work_id)
        body = graph.get("maat_body")
        if not isinstance(body, dict):
            return False
        if graph.get("work_id") != work_id or graph.get("maat_body_digest") != _digest(body):
            return False
        if not _valid_transition_state(graph):
            return False
        persisted_provenance = graph.get("semantic_provenance_binding")
        try:
            _validate_maat_body(body)
        except RegistryError:
            return False
        if not _valid_semantic_provenance(persisted_provenance, body):
            return False
        if issued_maat_body is None:
            return True
        body_matches = _canonical(body) == _canonical(issued_maat_body) and graph["maat_body_digest"] == _digest(issued_maat_body)
        provenance_matches = semantic_provenance_binding is None or persisted_provenance == semantic_provenance_binding
        return body_matches and provenance_matches

    def update_addendum(self, work_id: str, addendum: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(addendum, dict) or set(addendum) != ADDENDUM_KEYS or any(
            not isinstance(addendum[key], list) for key in ADDENDUM_KEYS
        ):
            raise RegistryError("addendum must contain observations and source_refs only")
        if _contains_semantic_key(addendum):
            raise RegistryError("addendum cannot contain semantic keys")
        graph = self.load(work_id)
        path = self._path(work_id)
        preimage = path.read_bytes()
        issued_body = deepcopy(graph["maat_body"])
        issued_digest = graph["maat_body_digest"]
        graph["hermes_kann_addendum"] = deepcopy(addendum)
        _write(path, graph)
        try:
            readback = self.load(work_id)
            valid = self.verify_readback(work_id, issued_body) and readback.get("maat_body_digest") == issued_digest
        except Exception:
            valid = False
        if not valid:
            temporary = path.with_suffix(".tmp")
            temporary.write_bytes(preimage)
            temporary.replace(path)
            raise RegistryError("HOLD_WRITE_READBACK")
        return graph

    def apply_maat_delta(
        self,
        work_id: str,
        maat_body: dict[str, Any],
        semantic_provenance_binding: dict[str, Any] | None = None,
        *,
        expected_revision: int | None = None,
        expected_digest: str | None = None,
    ) -> dict[str, Any]:
        _validate_maat_body(maat_body)
        if not _valid_semantic_provenance(semantic_provenance_binding, maat_body):
            raise RegistryError("HOLD_UNMAPPED_SEMANTIC_FIELD")
        path = self._path(work_id)
        with self._graph_lock():
            preimage = path.read_bytes()
            graph = self.load(work_id)
            if graph.get("revision") != expected_revision or graph.get("maat_body_digest") != expected_digest:
                raise RegistryError("HOLD_PREAUTH_CAS")
            graph.update({
                "revision": graph["revision"] + 1,
                "maat_body": deepcopy(maat_body),
                "maat_body_digest": _digest(maat_body),
            })
            graph["semantic_provenance_binding"] = deepcopy(semantic_provenance_binding)
            try:
                _write(path, graph)
                valid = self.verify_readback(work_id, maat_body, semantic_provenance_binding)
            except Exception:
                valid = False
            if not valid:
                temporary = path.with_suffix(".tmp")
                temporary.write_bytes(preimage)
                temporary.replace(path)
                raise RegistryError("HOLD_WRITE_READBACK")
            return graph

    def split(self, work_id: str, new_work_id: str, maat_body: dict[str, Any], split: dict[str, Any], semantic_provenance_binding: dict[str, Any] | None = None) -> dict[str, Any]:
        self.load(work_id)
        if split.get("issued_by") != "maat" or not split.get("split_id") or not split.get("reason"):
            raise RegistryError("explicit Maat split required")
        return self.create(new_work_id, maat_body, split_from=work_id, semantic_provenance_binding=semantic_provenance_binding)

    def consume_return_edge(
        self,
        work_id: str,
        *,
        returns_to_ref: str,
        parent_receipt_ref: str,
        parent_edge_ref: str,
        return_to_node_ref: str,
    ) -> dict[str, Any]:
        graph = self.load(work_id)
        body = graph.get("maat_body")
        _validate_maat_body(body)
        if not isinstance(body, dict):
            raise RegistryError("HOLD_RETURN_EDGE_SCHEMA")
        lineage = body.get("derived_c_lineage")
        validate_accepted_derived_c_lineage(body, {
            field: lineage.get(field) if isinstance(lineage, dict) else None
            for field in DERIVED_C_LINEAGE_FIELDS - {"issued_by", "status", "derived_c_ref"}
        })
        edges = body.get("returns_to", [])
        matches = [edge for edge in edges if edge["id"] == returns_to_ref]
        if (
            len(matches) != 1
            or matches[0]["parent_edge_ref"] != parent_edge_ref
            or matches[0]["to"] != return_to_node_ref
            or matches[0]["status"] != "satisfied"
        ):
            raise RegistryError("HOLD_RETURN_EDGE")
        path = self._execution_receipts_path(work_id)
        if not path.is_file():
            raise RegistryError("HOLD_RETURN_EDGE")
        sidecar = load_json_or_yaml(path)
        receipts = sidecar.get("receipts")
        parents = [
            receipt for receipt in receipts
            if isinstance(receipt, dict) and receipt.get("receipt_ref") == parent_receipt_ref
        ] if isinstance(receipts, list) else []
        if (
            sidecar.get("work_id") != work_id
            or len(parents) != 1
            or parents[0].get("family") != "execution_receipt"
            or parents[0].get("parent_edge_ref") != parent_edge_ref
            or parents[0].get("return_to_node_ref") != return_to_node_ref
        ):
            raise RegistryError("HOLD_RETURN_EDGE")
        return self.append_continuation_receipt(
            work_id,
            parent_receipt_ref=parent_receipt_ref,
            parent_edge_ref=parent_edge_ref,
            returns_to_ref=returns_to_ref,
            return_to_node_ref=return_to_node_ref,
        )

    def checkpoint(
        self,
        work_id: str,
        repository: dict[str, str],
        scoped_paths: list[str],
        excluded_dirty_paths: list[str],
        closure_AC_ref: str,
        CPS_refs: dict[str, Any],
        prohibited_actions: list[str],
        owner_approval: bool,
        commit_message: str,
        verification_command: str | None,
        *,
        dispatcher: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    ):
        if owner_approval is not True:
            raise RegistryError("checkpoint owner_approval must be true")
        if not isinstance(commit_message, str) or not commit_message:
            raise RegistryError("checkpoint commit_message is required")
        if verification_command is not None and not isinstance(verification_command, str):
            raise RegistryError("checkpoint verification_command must be a string or null")
        graph = self.load(work_id)
        revision = graph["revision"]
        packet = {
            "schema": "harness.cps.semantic-checkpoint-git-closure.v1",
            "checkpoint_id": f"{work_id}@r{revision}",
            "work_id": work_id,
            "graph_source": {
                "ref": str(self._path(work_id)),
                "digest": graph["maat_body_digest"],
                "expected_prior_revision": revision - 1 or None,
            },
            "repository": deepcopy(repository),
            "scoped_paths": deepcopy(scoped_paths),
            "excluded_dirty_paths": deepcopy(excluded_dirty_paths),
            "closure_AC_ref": closure_AC_ref,
            "CPS_refs": deepcopy(CPS_refs),
            "prohibited_actions": deepcopy(prohibited_actions),
            "owner_approval": owner_approval,
            "execution_instruction": EXECUTION_INSTRUCTION,
            "commit_message": commit_message,
            "verification_command": verification_command,
        }
        return packet, dispatcher(packet) if dispatcher else None


def materialize_maat_body(
    maat_body: dict[str, Any] | None,
    operational_binding: dict[str, Any] | None,
    *,
    semantic_provenance_binding: dict[str, Any] | None = None,
    addendum: dict[str, Any] | None = None,
    checkpoint_settings: dict[str, Any] | None = None,
    dispatcher: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    if not isinstance(maat_body, dict) or not isinstance(operational_binding, dict):
        return None
    work_id = operational_binding.get("work_id")
    graph_root = operational_binding.get("graph_root")
    if not isinstance(work_id, str) or not work_id or not isinstance(graph_root, (str, Path)) or not str(graph_root):
        raise RegistryError("explicit work_id and graph_root binding required")

    _validate_maat_body(maat_body)
    if not isinstance(semantic_provenance_binding, dict) or not _valid_semantic_provenance(semantic_provenance_binding, maat_body):
        raise RegistryError("HOLD_UNMAPPED_SEMANTIC_FIELD")
    store = WorkingGraphRegistry(Path(graph_root))
    path = store._path(work_id)
    graph = (
        store.apply_maat_delta(
            work_id,
            maat_body,
            semantic_provenance_binding,
            expected_revision=operational_binding.get("expected_revision"),
            expected_digest=operational_binding.get("expected_digest"),
        )
        if path.exists()
        else store.create(work_id, maat_body, semantic_provenance_binding=semantic_provenance_binding)
    )
    if addendum is not None:
        graph = store.update_addendum(work_id, addendum)

    checkpoint_packet = None
    checkpoint_receipt = None
    if checkpoint_settings is not None:
        checkpoint_packet, checkpoint_receipt = store.checkpoint(
            work_id,
            dispatcher=dispatcher,
            **checkpoint_settings,
        )
    return {
        "graph_ref": str(path),
        "source_digest": graph["maat_body_digest"],
        "revision": graph["revision"],
        "checkpoint_packet": checkpoint_packet,
        "checkpoint_receipt": checkpoint_receipt,
    }
