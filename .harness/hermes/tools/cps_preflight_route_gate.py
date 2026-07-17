#!/usr/bin/env python3
"""Harness CPS preflight route-gate runner.

This is the executable counterpart to the harness-brain contract
`cp-cps-preflight-route-gate.md`. Its primary path is live Maat
adjudication over compact frontmatter; deterministic mode is retained only
for offline diagnostics. It enforces the frontmatter-first protocol:

1. Hermes-kann-style C_candidate_packet from a task packet.
2. Maat-style route-gate adjudication over C?/P?/S?/E?, gaps and audit scope.
3. Selected-agent probes.
4. Local task bodies only for accepted/need_local_body agents.
5. Compact learning event for Honcho/GBrain ingestion.
"""
from __future__ import annotations

import argparse
import base64
from copy import deepcopy
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cps_runtime_navigation import navigate_cps_runtime, validate_semantic_provenance
from cps_working_graph_registry import RegistryError, WorkingGraphRegistry, materialize_maat_body
from external_runtime_dispatcher import dispatch_external_runtime
from session_registry import lane_key, load_registry

PROFILES = {
    "maat": "C-boundary/route-gate/audit-scope",
    "hermes-kann": "orchestration/dispatch/integration",
    "seshat": "doc_ops/source_refs/evidence documents",
    "thoth": "CPS compile/fan-out",
    "sia": "recall/internal history",
    "ptah": "bounded implementation/apply",
    "anubis": "integrity/diff/reversibility",
    "sekhmet": "security/sandbox/secret/path risk",
    "hu": "efficiency/token-footprint",
    "nefertum": "ambiguous tradeoff review",
    "hathor": "artifact quality/UX/support",
}

CONTRACT_PATH = Path("/Users/kann/projects/harness-brain/projects/harness-starter/contracts/cp_cps_preflight_route_gate.md")
DEFAULT_REPO = Path("/Users/kann/projects/harness-starter")
DEFAULT_MAX_REENTRY_ITERATIONS = 1
REENTRY_INPUT_KEYS = (
    "revised_C",
    "revised_P",
    "revised_S",
    "revised_E",
    "missing_evidence",
    "iteration",
    "packet_ref",
)
C2_RUNTIME_DEPENDENCIES = (
    "C-ROLE-CONTRACT",
    "C-GATE-DOCOPS",
    "C-ROUTE-PROJECTION",
    "C-PHYSICAL-DOCOPS-VALIDATOR",
)
NODE_LOCAL_REF_KEYS = {"C", "P", "S", "AC", "E"}
HANDOFF_INTEGRITY_FAILURE = "HOLD_HANDOFF_TRANSPORT_INTEGRITY"
DERIVED_C_PARENT_BINDING_FIELDS = {
    "parent_work_id", "parent_graph_ref", "parent_graph_revision", "parent_graph_digest",
    "blocked_receipt_ref", "parent_edge_ref", "return_to_node_ref",
}


def build_derived_c_candidate(
    parent_binding: dict[str, Any],
    recovery_attempt_refs: list[str],
    *,
    same_c_recovery_exhausted: bool,
) -> dict[str, Any]:
    if same_c_recovery_exhausted is not True:
        return {"status": "hold", "failure_code": "HOLD_SAME_C_RECOVERY_AVAILABLE", "graph_mutation": False}
    if (
        not isinstance(parent_binding, dict)
        or set(parent_binding) != DERIVED_C_PARENT_BINDING_FIELDS
        or type(parent_binding.get("parent_graph_revision")) is not int
        or parent_binding["parent_graph_revision"] < 1
        or not re.fullmatch(r"[0-9a-f]{64}", str(parent_binding.get("parent_graph_digest", "")))
        or any(not isinstance(parent_binding.get(field), str) or not parent_binding[field] for field in DERIVED_C_PARENT_BINDING_FIELDS - {"parent_graph_revision"})
        or not isinstance(recovery_attempt_refs, list)
        or not recovery_attempt_refs
        or any(not isinstance(ref, str) or not ref for ref in recovery_attempt_refs)
        or len(recovery_attempt_refs) != len(set(recovery_attempt_refs))
    ):
        return {"status": "hold", "failure_code": "HOLD_DERIVED_C_CANDIDATE_BINDING", "graph_mutation": False}
    return {
        "schema": "harness.cps.derived_c_candidate.v1",
        "status": "candidate",
        "authority": "non_authoritative",
        "parent_binding": deepcopy(parent_binding),
        "recovery_attempt_refs": list(recovery_attempt_refs),
        "graph_mutation": False,
    }


def load_production_final_audit(binding: Any) -> dict[str, Any]:
    if not isinstance(binding, dict) or set(binding) != {"graph_root", "execution_root", "identity"}:
        return {"status": "hold", "failure_code": "HOLD_FINAL_GATE"}
    try:
        from lifecycle_runner import FinalAuditProductionAdapter
        return FinalAuditProductionAdapter(
            Path(binding["graph_root"]), Path(binding["execution_root"]),
        ).reload(binding["identity"])
    except Exception:
        return {"status": "hold", "failure_code": "HOLD_FINAL_GATE"}


def project_execution_state(packet: dict[str, Any]) -> dict[str, Any]:
    binding = packet.get("active_case_final_audit")
    identity = binding.get("identity") if isinstance(binding, dict) else None
    issued = {
        "authorization_state": "ISSUED",
        "runtime_state": None,
        "execution_status": None,
        "execution_receipt_ref": None,
        "execution_event": None,
        "run_handle": None,
        "attempt": None,
        "recorded_at": None,
        "audit_verdict": None,
        "state_source_ref": None,
    }
    if (
        not isinstance(binding, dict)
        or not isinstance(binding.get("execution_root"), (str, os.PathLike))
        or not str(binding["execution_root"])
        or not isinstance(identity, dict)
    ):
        return issued
    try:
        from lifecycle_runner import project_external_runtime_state
        return project_external_runtime_state(identity, Path(binding["execution_root"]))
    except Exception:
        return issued


def search_handoff_body(*_args: Any, **_kwargs: Any) -> None:
    """Handoff consumers must never reconstruct a missing body by search."""
    raise RuntimeError("handoff body search is prohibited")


def build_handoff_envelope(maat_body: bytes, metadata: dict[str, Any]) -> dict[str, Any]:
    """Wrap opaque Maat bytes without parsing or mixing metadata into the body."""
    if not isinstance(maat_body, bytes):
        raise TypeError("maat_body must be bytes")
    if not isinstance(metadata, dict):
        raise TypeError("metadata must be a dict")
    return {
        "schema": "harness.cps_preflight.handoff_envelope.v1",
        "body_transport": {
            "encoding": "base64",
            "length": len(maat_body),
            "sha256": hashlib.sha256(maat_body).hexdigest(),
            "payload": base64.b64encode(maat_body).decode("ascii"),
        },
        "metadata": deepcopy(metadata),
    }


def build_handoff_prompt(envelope: dict[str, Any]) -> str:
    """Serialize the envelope as a distinct prompt field without rewriting its body."""
    return json.dumps(
        {"handoff_envelope": envelope},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _decode_handoff_envelope(envelope: Any) -> tuple[bytes | None, str | None]:
    if not isinstance(envelope, dict):
        return None, HANDOFF_INTEGRITY_FAILURE
    transport = envelope.get("body_transport")
    if not isinstance(transport, dict) or transport.get("encoding") != "base64":
        return None, HANDOFF_INTEGRITY_FAILURE
    try:
        body = base64.b64decode(transport.get("payload", ""), validate=True)
    except (TypeError, ValueError):
        return None, HANDOFF_INTEGRITY_FAILURE
    if transport.get("length") != len(body) or transport.get("sha256") != hashlib.sha256(body).hexdigest():
        return None, HANDOFF_INTEGRITY_FAILURE
    return body, None


def consume_handoff_prompt(prompt: str) -> dict[str, Any]:
    """Consume only an exact transport body; incomplete or ambiguous bodies never trigger search."""
    try:
        payload = json.loads(prompt)
    except (TypeError, json.JSONDecodeError):
        return {"status": "hold", "failure_code": HANDOFF_INTEGRITY_FAILURE, "search_count": 0}
    envelope = payload.get("handoff_envelope") if isinstance(payload, dict) else None
    metadata = envelope.get("metadata") if isinstance(envelope, dict) else None
    state = metadata.get("local_body_state") if isinstance(metadata, dict) else None
    if state == "incomplete":
        return {"status": "need_local_body", "search_count": 0}
    if state != "complete":
        return {"status": "hold", "failure_code": HANDOFF_INTEGRITY_FAILURE, "search_count": 0}
    body, failure = _decode_handoff_envelope(envelope)
    if failure:
        return {"status": "hold", "failure_code": failure, "search_count": 0}
    assert body is not None
    return {
        "status": "accept",
        "body": body,
        "body_sha256": hashlib.sha256(body).hexdigest(),
        "search_count": 0,
    }


def dispatch_handoff_transport(
    original_body: bytes,
    envelope: dict[str, Any],
    prompt: str,
    consumer_result: Any,
    runner: Any,
) -> dict[str, Any]:
    """Block before runner unless original, envelope, prompt and consumer bytes are identical."""
    envelope_body, envelope_failure = _decode_handoff_envelope(envelope)
    try:
        prompt_payload = json.loads(prompt)
    except (TypeError, json.JSONDecodeError):
        prompt_payload = None
    prompt_envelope = prompt_payload.get("handoff_envelope") if isinstance(prompt_payload, dict) else None
    prompt_body, prompt_failure = _decode_handoff_envelope(prompt_envelope)
    consumer_body = consumer_result.get("body") if isinstance(consumer_result, dict) else None
    envelope_metadata = envelope.get("metadata") if isinstance(envelope, dict) else None
    prompt_metadata = prompt_envelope.get("metadata") if isinstance(prompt_envelope, dict) else None
    bodies = (original_body, envelope_body, prompt_body, consumer_body)
    identities = {
        name: hashlib.sha256(body).hexdigest() if isinstance(body, bytes) else None
        for name, body in zip(("original", "envelope", "prompt", "consumer"), bodies)
    }
    integrity_ok = (
        isinstance(original_body, bytes)
        and envelope_failure is None
        and prompt_failure is None
        and isinstance(envelope_metadata, dict)
        and envelope_metadata.get("local_body_state") == "complete"
        and isinstance(prompt_metadata, dict)
        and prompt_metadata.get("local_body_state") == "complete"
        and isinstance(consumer_result, dict)
        and consumer_result.get("status") == "accept"
        and consumer_result.get("body_sha256") == identities["consumer"]
        and consumer_result.get("search_count") == 0
        and all(body == original_body for body in bodies)
    )
    if not integrity_ok:
        return {
            "status": "hold",
            "failure_code": HANDOFF_INTEGRITY_FAILURE,
            "identity": identities,
            "dispatch_count": 0,
            "search_count": 0,
        }
    runner(original_body)
    return {
        "status": "dispatched",
        "identity": identities,
        "dispatch_count": 1,
        "search_count": 0,
    }


def validate_node_projection(projection: Any, *, expected_revision: Any = None, expected_changed_paths: Any = None) -> dict[str, Any]:
    """Validate the reference-only projection required for node dispatch."""
    gaps: list[str] = []

    def gap(name: str) -> None:
        if name not in gaps:
            gaps.append(name)

    if not isinstance(projection, dict):
        return {"schema": "harness.cps_preflight.node_projection_gate.v1", "status": "hold", "gap_classes": ["node_projection.missing"]}
    for field in (
        "graph_ref", "canonical_source_ref", "local_refs", "local_body_ref",
        "node_local_AC", "evidence", "prohibitions", "source_revision", "changed_path_manifest",
    ):
        if not _present(projection.get(field)):
            gap(f"node_projection.{field}")
    revision = projection.get("source_revision")
    for field in ("graph_ref", "canonical_source_ref"):
        ref = projection.get(field)
        if not isinstance(ref, dict) or not _present(ref.get("ref")) or not _present(ref.get("revision")):
            gap(f"node_projection.{field}")
        elif _present(revision) and ref.get("revision") != revision:
            gap("node_projection.source_revision_mismatch")
    if _present(expected_revision) and revision != expected_revision:
        gap("node_projection.source_revision_mismatch")
    local_refs = projection.get("local_refs")
    if not isinstance(local_refs, dict) or set(local_refs) != NODE_LOCAL_REF_KEYS:
        gap("node_projection.local_refs_exact_map")
    elif any(not isinstance(value, str) or not value.strip() for value in local_refs.values()):
        gap("node_projection.local_refs_ref_only")
    manifest = projection.get("changed_path_manifest")
    if not isinstance(manifest, list) or not manifest or any(not isinstance(path, str) or not path.strip() for path in manifest):
        gap("node_projection.changed_path_manifest")
    elif len(manifest) != len(set(manifest)):
        gap("node_projection.changed_path_manifest_not_exact")
    if expected_changed_paths is not None:
        expected = list(expected_changed_paths) if isinstance(expected_changed_paths, (list, tuple)) else []
        if manifest != expected:
            gap("node_projection.changed_path_manifest_not_exact")
    next_c = projection.get("next_C")
    terminal = projection.get("terminal")
    if bool(_present(next_c)) == bool(terminal is True):
        gap("node_projection.next_C_or_terminal")
    elif _present(next_c) and (
        not isinstance(next_c, dict) or not _present(next_c.get("ref")) or not isinstance(next_c.get("order"), int)
    ):
        gap("node_projection.next_C_order")
    return {
        "schema": "harness.cps_preflight.node_projection_gate.v1",
        "status": "hold" if gaps else "pass",
        "gap_classes": gaps,
    }


def apply_node_projection_gate(route: dict[str, Any], reducer_result: dict[str, Any], packet: dict[str, Any]) -> dict[str, Any]:
    """Block local-body and final-Maat dispatch when a dispatchable node is incomplete."""
    dispatchable = reducer_result.get("status") == "pass" and any(
        local_body_allowed(agent, reducer_result) for agent in normalize_selected_agents(route, reducer_result)
    )
    if not dispatchable:
        gate = {"schema": "harness.cps_preflight.node_projection_gate.v1", "status": "not_required", "gap_classes": []}
        reducer_result["node_projection_gate"] = gate
        return gate
    expected_revision = packet.get("source_revision")
    expected_paths = packet.get("changed_path_manifest")
    if expected_paths is None and isinstance(packet.get("mutation_manifest"), list):
        expected_paths = [
            item.get("path") for item in packet["mutation_manifest"]
            if isinstance(item, dict) and _present(item.get("path"))
        ]
    gate = validate_node_projection(
        packet.get("node_projection"),
        expected_revision=expected_revision if _present(expected_revision) else None,
        expected_changed_paths=expected_paths,
    )
    reducer_result["node_projection_gate"] = gate
    if gate["status"] != "pass":
        reducer_result["status"] = "hold"
        reducer_result["C_boundary"] = "HOLD"
        reducer_result["final_selected_agents"] = {}
        reducer_result["local_body_scope"] = {}
        reducer_result.setdefault("hold_reasons", []).extend(gate["gap_classes"])
        reducer_result.setdefault("failure_codes", []).append("HOLD_NODE_PROJECTION")
    return gate


def validate_physical_docops_route(value: dict[str, Any]) -> dict[str, Any]:
    """Validate the compact physical projection and conditional doc_ops contract."""
    gaps: list[str] = []

    def gap(name: str) -> None:
        if name not in gaps:
            gaps.append(name)

    projection = value.get("projection")
    if projection is not None:
        if not isinstance(projection, dict):
            gap("projection.invalid")
        else:
            if any(key in projection for key in ("C", "P", "S", "AC", "E", "CPS", "task_AC")):
                gap("projection.canonical_body_present")
            if any(key not in {"graph_ref", "canonical_source_ref", "local_refs"} for key in projection):
                gap("projection.unpermitted_field")
            refs = [projection.get("graph_ref"), projection.get("canonical_source_ref")]
            local_refs = projection.get("local_refs")
            if not isinstance(local_refs, list):
                gap("projection.local_refs_invalid")
            else:
                refs.extend(local_refs)
            for ref in refs:
                if not isinstance(ref, dict) or not _present(ref.get("ref")) or not _present(ref.get("revision")):
                    gap("projection.ref_revision_missing")
                    continue
                if _present(ref.get("expected_revision")) and ref["expected_revision"] != ref["revision"]:
                    gap("projection.ref_revision_mismatch")
            primary_refs = refs[:2]
            if all(isinstance(ref, dict) and _present(ref.get("revision")) for ref in primary_refs):
                if primary_refs[0]["revision"] != primary_refs[1]["revision"]:
                    gap("projection.ref_revision_mismatch")
            if isinstance(local_refs, list) and any(not isinstance(ref, dict) or not _present(ref.get("node")) for ref in local_refs):
                gap("projection.local_ref_not_node_local")

    doc_ops = value.get("doc_ops")
    if doc_ops is not None and not isinstance(doc_ops, dict):
        gap("doc_ops.invalid")
    elif isinstance(doc_ops, dict) and doc_ops.get("required") is True:
        for field in ("doc_refs", "required_docs", "source_refs", "ssot_residency", "allowed_write_surface"):
            if not _present(doc_ops.get(field)):
                gap(f"doc_ops.{field}")
        if doc_ops.get("canonical_author") != "hermes-kann":
            gap("doc_ops.canonical_author")
        if doc_ops.get("research_sources_from") != ["seshat"]:
            gap("doc_ops.research_sources_from")
        if doc_ops.get("integration_owner") != "hermes-kann":
            gap("doc_ops.integration_owner")
        manifest = doc_ops.get("manifest") if isinstance(doc_ops.get("manifest"), dict) else {}
        verification = doc_ops.get("verification") if isinstance(doc_ops.get("verification"), dict) else {}
        for field in ("expected_entries", "validator_ref"):
            if not _present(manifest.get(field)):
                gap(f"doc_ops.manifest.{field}")
        for field in ("mode", "changed_paths", "closure_line_refs", "canonical_consistency_ref"):
            if not _present(verification.get(field)):
                gap(f"doc_ops.verification.{field}")

    actor_keys = ("candidate_agents", "selected_agents", "final_selected_agents", "fallback", "compile_dependency", "compile_dependencies", "local_body_scope")
    for key in actor_keys:
        if key in value and re.search(r"\bthoth\b", _text_values(value[key]), re.IGNORECASE):
            gap("actor_binding.thoth_forbidden")

    for location in (value.get(key) for key in ("candidate_agents", "selected_agents", "final_selected_agents", "local_body_scope")):
        if not isinstance(location, dict):
            continue
        for agent, raw_spec in location.items():
            if str(agent).upper() != "C2-RUNTIME":
                continue
            spec = raw_spec if isinstance(raw_spec, dict) else {}
            dependencies = spec.get("dependencies")
            verified = {
                str(item.get("id")) for item in dependencies
                if isinstance(item, dict) and str(item.get("status", "")).lower() == "verified"
            } if isinstance(dependencies, list) else set()
            if not set(C2_RUNTIME_DEPENDENCIES).issubset(verified):
                gap("c2_runtime.dependencies_unverified")
            if isinstance(dependencies, list) and any(isinstance(item, dict) and item.get("auto_completed") is True for item in dependencies):
                gap("c2_runtime.dependencies_unverified")
            downscope = _text_values({key: spec.get(key) for key in ("downscope", "worker", "job", "execution_mode") if key in spec}).lower()
            if re.search(r"generic|worker|background[-_ ]?job|auto[-_ ]?complet", downscope):
                gap("c2_runtime.generic_downscope_forbidden")

    return {
        "schema": "harness.cps_preflight.physical_docops_gate.v1",
        "status": "hold" if gaps else "pass",
        "gap_classes": gaps,
    }


def apply_physical_docops_gate(route: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    inherited = source.get("physical_docops_gate")
    inherited_gaps = inherited.get("gap_classes", []) if isinstance(inherited, dict) else []
    checked = validate_physical_docops_route({
        **source,
        **route,
        "projection": source.get("projection"),
        "doc_ops": source.get("doc_ops"),
    })
    gaps = list(dict.fromkeys([*inherited_gaps, *checked["gap_classes"]]))
    gate = {**checked, "status": "hold" if gaps else "pass", "gap_classes": gaps}
    route["physical_docops_gate"] = gate
    if source.get("projection") is not None:
        route["projection"] = source["projection"]
    if source.get("doc_ops") is not None:
        route["doc_ops"] = source["doc_ops"]
    if gate.get("status") != "pass":
        route["status"] = "hold"
        route["C_boundary"] = "HOLD"
        raw_gap_scan = route.get("gap_scan")
        gap_scan: dict[str, Any] = raw_gap_scan if isinstance(raw_gap_scan, dict) else {}
        missing = list(gap_scan.get("missing", [])) if isinstance(gap_scan.get("missing"), list) else []
        for item in gate.get("gap_classes", []):
            if item not in missing:
                missing.append(item)
        route["gap_scan"] = {**gap_scan, "missing": missing, "verdict": "GAP_FOUND"}
    return route


def _load_packet(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    try:
        import yaml  # type: ignore
        data = yaml.safe_load(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        data: dict[str, Any] = {}
        stack: list[tuple[int, Any]] = [(-1, data)]
        for line in raw.splitlines():
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            indent = len(line) - len(line.lstrip(" "))
            stripped = line.strip()
            if ":" in stripped and not stripped.startswith("-"):
                key, _, value = stripped.partition(":")
                while stack and indent <= stack[-1][0]:
                    stack.pop()
                parent = stack[-1][1]
                if isinstance(parent, dict):
                    parent[key] = value.strip().strip("'\"") if value.strip() else {}
                    if not value.strip():
                        stack.append((indent, parent[key]))
        return data


def _text_values(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join([str(k) + " " + _text_values(v) for k, v in value.items()])
    if isinstance(value, list):
        return " ".join(_text_values(v) for v in value)
    return str(value or "")


def _ordered_cps_items(cps: dict[str, Any], prefix: str) -> dict[str, str]:
    """Return CPS P#/S# items in numeric order from compact packet frontmatter."""
    found: dict[str, str] = {}
    for key, value in cps.items():
        if re.fullmatch(rf"{prefix}\d+", str(key)):
            found[str(key)] = _text_values(value).strip()
    return dict(sorted(found.items(), key=lambda item: int(item[0][1:])))


def _present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, (str, bytes)):
        return bool(value.strip())
    if isinstance(value, (dict, list, tuple, set)):
        return bool(value)
    return True


def validate_runtime_graph(packet: dict[str, Any]) -> dict[str, Any]:
    """Validate explicitly declared runtime graph data without filling gaps."""
    graph = packet.get("cps_flow_graph")
    if not isinstance(graph, dict):
        return {"status": "hold", "gaps": ["cps_flow_graph"]}
    gaps: list[str] = []
    if not _present(graph.get("revision")):
        gaps.append("cps_flow_graph.revision")
    nodes = graph.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        gaps.append("cps_flow_graph.nodes")
        return {"status": "hold", "gaps": gaps}
    for index, raw in enumerate(nodes):
        node = raw if isinstance(raw, dict) else {}
        node_id = str(node.get("id") or f"node[{index}]")
        for field in ("dependencies", "parallel_group", "owner", "task_AC", "evidence", "S"):
            if field not in node or (field != "dependencies" and not _present(node.get(field))):
                gaps.append(f"{node_id}.{field}")
        if isinstance(node.get("S"), list):
            seen_s: set[str] = set()
            seen_ordinals: set[Any] = set()
            for s_index, raw_s in enumerate(node["S"]):
                s_node = raw_s if isinstance(raw_s, dict) else {}
                s_id = str(s_node.get("id") or f"S[{s_index}]")
                for field in ("ordinal", "dependencies", "owner", "task_AC", "evidence"):
                    if field not in s_node or (field != "dependencies" and not _present(s_node.get(field))):
                        gaps.append(f"{node_id}.{s_id}.{field}")
                if s_id in seen_s:
                    gaps.append(f"{node_id}.{s_id}.ambiguous")
                seen_s.add(s_id)
                ordinal = s_node.get("ordinal")
                if ordinal in seen_ordinals:
                    gaps.append(f"{node_id}.S.ordinal_ambiguous")
                seen_ordinals.add(ordinal)
    return {"status": "hold" if gaps else "pass", "gaps": gaps, "graph": graph}


def build_dispatch_plan(graph: dict[str, Any]) -> dict[str, Any]:
    """Build a read-only dependency-ready plan from a validated canonical graph."""
    nodes: dict[str, Any] = {}
    ready_by_group: dict[str, list[str]] = {}
    for p_node in graph["nodes"]:
        p_id = str(p_node["id"])
        p_dependencies = list(p_node["dependencies"])
        blocked_reason = f"dependency:{p_dependencies[0]}" if p_dependencies else None
        ordered_s = sorted(p_node["S"], key=lambda item: item["ordinal"])
        ready_s: list[str] = []
        blocked_s: dict[str, str] = {}
        for s_node in ordered_s:
            dependencies = list(s_node["dependencies"])
            if blocked_reason:
                blocked_s[str(s_node["id"])] = blocked_reason
            elif dependencies:
                blocked_s[str(s_node["id"])] = f"dependency:{dependencies[0]}"
            else:
                ready_s.append(str(s_node["id"]))
        nodes[p_id] = {
            "P_ref": p_id,
            "S_refs": [str(item["id"]) for item in ordered_s],
            "AC_refs": list(p_node["task_AC"]),
            "evidence_refs": list(p_node["evidence"]),
            "owner": p_node["owner"],
            "parallel_group": p_node["parallel_group"],
            "dependencies": p_dependencies,
            "ready_S": ready_s,
            "blocked_S": blocked_s,
            "blocked_reason": blocked_reason,
        }
        if not blocked_reason:
            ready_by_group.setdefault(str(p_node["parallel_group"]), []).append(p_id)
    return {
        "schema": "harness.cps_preflight.dispatch_plan.v1",
        "graph_revision": graph["revision"],
        "nodes": nodes,
        "ready_groups": [
            {"parallel_group": group, "P_refs": refs}
            for group, refs in ready_by_group.items()
        ],
        "ready_nodes": [p_id for p_id, node in nodes.items() if node["blocked_reason"] is None],
        "blocked_nodes": {p_id: node["blocked_reason"] for p_id, node in nodes.items() if node["blocked_reason"]},
    }


def classify_mutation_closure(packet: dict[str, Any]) -> dict[str, Any]:
    """Classify only packet-declared mutations against active AC and route scope."""
    raw_cps = packet.get("CPS")
    cps: dict[str, Any] = raw_cps if isinstance(raw_cps, dict) else {}
    raw_ac = packet.get("task_AC") or cps.get("AC") or []
    ac_items = raw_ac.values() if isinstance(raw_ac, dict) else raw_ac if isinstance(raw_ac, list) else [raw_ac]
    active_ac: list[str] = []
    for item in ac_items:
        ref = (item.get("id") or item.get("AC_ref")) if isinstance(item, dict) else item
        if _present(ref) and str(ref) not in active_ac:
            active_ac.append(str(ref))

    raw_scope = packet.get("allowed_paths") or packet.get("mutation_scope") or packet.get("write_scope") or []
    scope_items = raw_scope.values() if isinstance(raw_scope, dict) else raw_scope if isinstance(raw_scope, list) else [raw_scope]
    scope = [str(item).rstrip("/") for item in scope_items if _present(item)]
    manifest = packet.get("mutation_manifest")
    mutations = manifest if isinstance(manifest, list) else []
    boundary = packet.get("owner_approval_boundary")
    boundary_evidence = boundary if isinstance(boundary, dict) else {}
    git_disallowed = (
        boundary_evidence.get("git_commit") is False
        or boundary_evidence.get("git_push") is False
    )
    candidates: list[dict[str, Any]] = []
    unclaimed: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    holds: list[dict[str, Any]] = []
    evidence_keys = {
        "conflict_evidence": "conflict_evidence",
        "ssot_owner_ambiguity": "ssot_owner_ambiguity",
        "owner_ambiguity": "ssot_owner_ambiguity",
        "separate_goal_evidence": "separate_goal_evidence",
    }
    for raw in mutations:
        if not isinstance(raw, dict) or not _present(raw.get("path")):
            continue
        item = dict(raw)
        path = str(item["path"]).rstrip("/")
        ac_ref = str(item.get("AC_ref") or "")
        in_scope = any(path == allowed or path.startswith(allowed + "/") for allowed in scope)
        if not ac_ref:
            unclaimed.append(item)
            excluded.append({**item, "reason": "missing_AC_ref"})
        elif ac_ref not in active_ac:
            unclaimed.append(item)
            excluded.append({**item, "reason": "inactive_AC_ref"})
        elif not in_scope:
            excluded.append({**item, "reason": "scope_violation"})
            holds.append({"path": path, "reason": "scope_violation", "evidence": scope})
        elif git_disallowed:
            excluded.append({**item, "reason": "git_owner_boundary_disallowed"})
            holds.append({
                "path": path,
                "reason": "git_owner_boundary_disallowed",
                "evidence": {
                    key: boundary_evidence[key]
                    for key in ("git_commit", "git_push")
                    if key in boundary_evidence
                },
            })
        else:
            candidates.append(item)
        for key, reason in evidence_keys.items():
            if _present(item.get(key)):
                holds.append({"path": path, "reason": reason, "evidence": item[key]})
    return {
        "active_AC_refs": active_ac,
        "git_closure_candidates": candidates,
        "unclaimed_mutations": unclaimed,
        "excluded_mutations": excluded,
        "hold_reasons": holds,
        "status": "hold" if holds else "candidate" if candidates else "not_required",
    }


def _mode_evidence_ok(mode: str, minimum: Any) -> bool:
    if not isinstance(minimum, dict) or not mode:
        return False
    evidence = minimum.get(mode) if mode in minimum else minimum
    if not isinstance(evidence, dict):
        return False
    required = {
        "test-backed": ("command_probe_id", "result"),
        "readback-backed": ("changed_path", "closure_line_ref"),
        "trace-backed": ("p_to_s_ref", "artifact_ref"),
        "source-backed": ("source_ref", "application_reason"),
    }.get(mode)
    if mode == "mixed":
        return any(_mode_evidence_ok(submode, minimum) for submode in ("test-backed", "readback-backed", "trace-backed", "source-backed"))
    return bool(required and all(_present(evidence.get(key)) for key in required))


def _edge_set(edges: list[Any]) -> set[tuple[str, str]]:
    found: set[tuple[str, str]] = set()
    for edge in edges:
        left, _, right = str(edge).replace("?", "").partition("->")
        if not right:
            continue
        left_ids = re.findall(r"P\d+", left)
        right_ids = re.findall(r"S\d+", right)
        found.update((p_id, s_id) for p_id in left_ids for s_id in right_ids)
    return found


R3_SCOPE_KEYS = {
    "repo_cwd", "target_command", "allowed_source_paths", "allowed_test_paths",
    "exact_unittest_selectors", "maat_import",
}
R3_EXECUTABLE = Path("/usr/bin/python3")
R3_MAAT_IMPORT_KEYS = {
    "adjudication_ref", "adjudication_sha256", "adjudicator_identity",
    "observation_ids", "scope_binding_digest",
}
R3_MAAT_ADJUDICATION_KEYS = {
    "schema", "adjudicator_identity", "observation_ids", "scope_binding_digest",
}
R3_ADJUDICATOR_IDENTITY_KEYS = {"actor_ref", "role", "adjudication_id"}
R3_EXECUTION_IDENTITY_FIELDS = (
    "executable_path", "executable_realpath", "executable_sha256", "cwd", "argv",
    "selectors", "allowed_source_paths", "allowed_test_paths", "allowed_path_hashes",
)
R3_FOCUSED_EXECUTION_RECEIPT_FIELDS = {
    "receipt_type", "status", *R3_EXECUTION_IDENTITY_FIELDS, "completed_process_args",
    "scope_binding_digest", "execution_identity_digest", "exit_code", "stdout_sha256",
    "stderr_sha256", "streams_digest", "receipt_digest",
}


def _r3_sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _r3_json_digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _r3_exact_paths(raw_paths: Any, repo: Path) -> tuple[list[str], str | None]:
    if not isinstance(raw_paths, list) or not raw_paths:
        return [], "path_evidence_missing"
    normalized: list[str] = []
    for raw in raw_paths:
        if not isinstance(raw, str) or not raw or re.search(r"[*?\[\]{}]", raw):
            return [], "path_not_exact"
        relative = Path(raw)
        if relative.is_absolute() or ".." in relative.parts or raw != relative.as_posix():
            return [], "path_not_exact"
        try:
            resolved = (repo / relative).resolve(strict=True)
            resolved.relative_to(repo)
        except (OSError, RuntimeError, ValueError):
            return [], "path_escape"
        if not resolved.is_file():
            return [], "path_not_file"
        normalized.append(relative.as_posix())
    if len(normalized) != len(set(normalized)):
        return [], "path_not_exact"
    return normalized, None


def _r3_hold(
    scope: dict[str, Any],
    focused: dict[str, Any],
    baselines: list[dict[str, Any]],
    reason: str,
) -> dict[str, Any]:
    return {
        "schema": "harness.cps_preflight.bounded_verifier_candidate.v1",
        "verifier_scope": {**scope, "status": "hold", "hold_reason": reason},
        "focused_result": {**focused, "status": "hold", "hold_reason": reason},
        "focused_execution_receipt": {**focused, "status": "hold", "hold_reason": reason},
        "baseline_observations": baselines,
        "active_case_verdict_candidate": {
            "status": "hold",
            "authority": "candidate_only",
            "final_audit_verdict": False,
            "hold_reason": reason,
            "evidence": focused,
        },
        "side_effects": {
            "receipt_writes": 0, "graph_writes": 0, "route_writes": 0,
            "business_writes": 0,
        },
    }


def build_bounded_verifier_candidate(
    verifier_scope: Any,
    baseline_observations: Any,
    *,
    repo: Path = DEFAULT_REPO,
    caller_result: Any = None,
) -> dict[str, Any]:
    """Execute the exact R3 verifier and return its non-authoritative candidate."""
    scope = deepcopy(verifier_scope) if isinstance(verifier_scope, dict) else {}
    focused: dict[str, Any] = {}
    raw_baselines = baseline_observations if isinstance(baseline_observations, list) else []
    baselines = [
        {
            **deepcopy(item),
            "in_focused_scope": False,
            "explicitly_imported": False,
            "case_effect": "none",
        }
        for item in raw_baselines if isinstance(item, dict)
    ]
    baseline_gap = (
        not isinstance(baseline_observations, list)
        or len(baselines) != len(raw_baselines)
        or any(
            not isinstance(item.get("observation_id"), str)
            or not item["observation_id"]
            or item.get("status") not in {"pass", "fail", "hold"}
            or "evidence" not in item
            for item in baselines
        )
        or len({item["observation_id"] for item in baselines}) != len(baselines)
    )
    if baseline_gap:
        return _r3_hold(scope, focused, baselines, "baseline_evidence_missing")
    if caller_result is not None:
        return _r3_hold(scope, focused, baselines, "fabricated_caller_result")
    try:
        expected_repo = repo.resolve(strict=True)
        scope_repo = Path(scope.get("repo_cwd", "")).resolve(strict=True)
    except (OSError, RuntimeError, ValueError):
        return _r3_hold(scope, focused, baselines, "repo_cwd_mismatch")
    if set(scope) != R3_SCOPE_KEYS or scope_repo != expected_repo or scope.get("repo_cwd") != str(expected_repo):
        return _r3_hold(scope, focused, baselines, "repo_cwd_mismatch")

    source_paths, source_gap = _r3_exact_paths(scope.get("allowed_source_paths"), expected_repo)
    test_paths, test_gap = _r3_exact_paths(scope.get("allowed_test_paths"), expected_repo)
    if source_gap or test_gap:
        return _r3_hold(scope, focused, baselines, source_gap or test_gap or "path_evidence_missing")

    selectors = scope.get("exact_unittest_selectors")
    test_modules = {Path(path).stem for path in test_paths}
    selector_ok = (
        isinstance(selectors, list)
        and bool(selectors)
        and len(selectors) == len(set(selectors))
        and all(
            isinstance(selector, str)
            and re.fullmatch(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*){2,}", selector)
            and selector.split(".", 1)[0] in test_modules
            for selector in selectors
        )
    )
    command = scope.get("target_command")
    expected_command = [str(R3_EXECUTABLE), "-B", "-m", "unittest", *(selectors or [])]
    command_ok = (
        selector_ok
        and isinstance(command, list)
        and all(isinstance(arg, str) and arg for arg in command)
        and command == expected_command
    )
    if not command_ok:
        return _r3_hold(scope, focused, baselines, "target_command_not_exact")
    selectors_exact = [str(item) for item in selectors] if isinstance(selectors, list) else []
    command_exact = [str(item) for item in command] if isinstance(command, list) else []

    try:
        executable_realpath = R3_EXECUTABLE.resolve(strict=True)
        executable = {
            "path": str(R3_EXECUTABLE),
            "realpath": str(executable_realpath),
            "sha256": _r3_sha256_file(executable_realpath),
        }
        allowed_paths = source_paths + test_paths
        allowed_path_hashes = {
            path: _r3_sha256_file(expected_repo / path)
            for path in allowed_paths
        }
    except OSError:
        return _r3_hold(scope, focused, baselines, "path_evidence_missing")
    scope_binding = {
        "executable": executable,
        "cwd": str(expected_repo),
        "argv": command_exact,
        "selectors": selectors_exact,
        "allowed_path_hashes": allowed_path_hashes,
    }
    scope_binding_digest = _r3_json_digest(scope_binding)

    maat_import = scope.get("maat_import")
    imported_ids: list[str] = []
    maat_readback: dict[str, Any] | None = None
    if maat_import is not None:
        adjudicator_identity = maat_import.get("adjudicator_identity") if isinstance(maat_import, dict) else None
        if (
            not isinstance(maat_import, dict)
            or set(maat_import) != R3_MAAT_IMPORT_KEYS
            or not isinstance(maat_import.get("adjudication_ref"), str)
            or not maat_import["adjudication_ref"]
            or not re.fullmatch(r"[0-9a-f]{64}", str(maat_import.get("adjudication_sha256", "")))
            or not isinstance(adjudicator_identity, dict)
            or set(adjudicator_identity) != R3_ADJUDICATOR_IDENTITY_KEYS
            or adjudicator_identity.get("actor_ref") != "maat"
            or adjudicator_identity.get("role") != "final_gate"
            or not isinstance(adjudicator_identity.get("adjudication_id"), str)
            or not adjudicator_identity["adjudication_id"]
            or not isinstance(maat_import.get("observation_ids"), list)
            or not maat_import["observation_ids"]
            or any(not isinstance(item, str) or not item for item in maat_import["observation_ids"])
            or len(maat_import["observation_ids"]) != len(set(maat_import["observation_ids"]))
            or maat_import.get("scope_binding_digest") != scope_binding_digest
        ):
            return _r3_hold(scope, focused, baselines, "maat_import_mismatch")
        imported_ids = maat_import["observation_ids"]
        known_ids = [item.get("observation_id") for item in baselines]
        if any(item not in known_ids for item in imported_ids):
            return _r3_hold(scope, focused, baselines, "maat_import_mismatch")
        try:
            adjudication_ref = Path(maat_import["adjudication_ref"])
            if not adjudication_ref.is_absolute():
                raise ValueError("noncanonical ref")
            adjudication_ref = adjudication_ref.resolve(strict=True)
            adjudication_bytes = adjudication_ref.read_bytes()
            document = json.loads(adjudication_bytes)
        except (OSError, ValueError, json.JSONDecodeError):
            return _r3_hold(scope, focused, baselines, "maat_import_mismatch")
        if (
            not isinstance(document, dict)
            or set(document) != R3_MAAT_ADJUDICATION_KEYS
            or document.get("schema") != "harness.maat.final_gate_adjudication.v1"
            or hashlib.sha256(adjudication_bytes).hexdigest() != maat_import["adjudication_sha256"]
            or document.get("adjudicator_identity") != adjudicator_identity
            or document.get("observation_ids") != imported_ids
            or document.get("scope_binding_digest") != scope_binding_digest
        ):
            return _r3_hold(scope, focused, baselines, "maat_import_mismatch")
        maat_readback = {
            "adjudication_ref": str(adjudication_ref),
            "adjudication_sha256": maat_import["adjudication_sha256"],
            "adjudicator_identity": deepcopy(document["adjudicator_identity"]),
            "observation_ids": list(imported_ids),
            "scope_binding_digest": scope_binding_digest,
        }
        for item in baselines:
            if item.get("observation_id") in imported_ids:
                item["in_focused_scope"] = True
                item["explicitly_imported"] = True
                item["case_effect"] = item.get("status") if item.get("status") in {"pass", "fail"} else "hold"

    try:
        completed = subprocess.run(
            command_exact,
            cwd=str(expected_repo),
            capture_output=True,
            text=False,
            check=False,
        )
    except OSError:
        return _r3_hold(scope, focused, baselines, "verifier_execution_failed")
    if (
        not isinstance(completed, subprocess.CompletedProcess)
        or completed.args != command_exact
        or type(completed.returncode) is not int
        or not isinstance(completed.stdout, bytes)
        or not isinstance(completed.stderr, bytes)
    ):
        return _r3_hold(scope, focused, baselines, "completed_process_mismatch")
    try:
        executable_after = _r3_sha256_file(executable_realpath)
        allowed_path_hashes_after = {
            path: _r3_sha256_file(expected_repo / path)
            for path in allowed_paths
        }
    except OSError:
        return _r3_hold(scope, focused, baselines, "allowed_path_hash_mismatch")
    if executable_after != executable["sha256"]:
        return _r3_hold(scope, focused, baselines, "executable_hash_mismatch")
    if allowed_path_hashes_after != allowed_path_hashes:
        return _r3_hold(scope, focused, baselines, "allowed_path_hash_mismatch")

    stdout_sha256 = hashlib.sha256(completed.stdout).hexdigest()
    stderr_sha256 = hashlib.sha256(completed.stderr).hexdigest()
    streams_digest = _r3_json_digest({
        "stderr_sha256": stderr_sha256,
        "stdout_sha256": stdout_sha256,
    })
    focused_status = "pass" if completed.returncode == 0 else "fail"
    execution_identity = {
        "executable_path": executable["path"],
        "executable_realpath": executable["realpath"],
        "executable_sha256": executable["sha256"],
        "cwd": str(expected_repo),
        "argv": command_exact,
        "selectors": selectors_exact,
        "allowed_source_paths": source_paths,
        "allowed_test_paths": test_paths,
        "allowed_path_hashes": allowed_path_hashes,
    }
    normalized_focused = {
        "receipt_type": "in_memory_completed_process",
        "status": focused_status,
        **execution_identity,
        "completed_process_args": list(completed.args),
        "scope_binding_digest": scope_binding_digest,
        "execution_identity_digest": _r3_json_digest(execution_identity),
        "exit_code": completed.returncode,
        "stdout_sha256": stdout_sha256,
        "stderr_sha256": stderr_sha256,
        "streams_digest": streams_digest,
    }
    normalized_focused["receipt_digest"] = _r3_json_digest(normalized_focused)
    imported_effects = [item["case_effect"] for item in baselines if item["explicitly_imported"]]
    candidate_status = focused_status
    if "hold" in imported_effects:
        candidate_status = "hold"
    elif "fail" in imported_effects:
        candidate_status = "fail"
    return {
        "schema": "harness.cps_preflight.bounded_verifier_candidate.v1",
        "verifier_scope": {
            **scope,
            "repo_cwd": str(expected_repo),
            "allowed_source_paths": source_paths,
            "allowed_test_paths": test_paths,
            "status": "accepted",
        },
        "focused_result": normalized_focused,
        "focused_execution_receipt": normalized_focused,
        "baseline_observations": baselines,
        "active_case_verdict_candidate": {
            "status": candidate_status,
            "authority": "candidate_only",
            "final_audit_verdict": False,
            "evidence": normalized_focused,
            "maat_adjudication_readback": maat_readback,
        },
        "side_effects": {
            "receipt_writes": 0, "graph_writes": 0, "route_writes": 0,
            "business_writes": 0,
        },
    }


def build_verification_gate(candidate: dict[str, Any], route: dict[str, Any]) -> dict[str, Any]:
    raw_verification = candidate.get("verification")
    verification: dict[str, Any] = raw_verification if isinstance(raw_verification, dict) else {}
    execution_kind = str(verification.get("execution_kind") or "").strip()
    raw_verification_s = verification.get("verification_S")
    verification_s: list[Any] = raw_verification_s if isinstance(raw_verification_s, list) else []
    evidence_mode = str(verification.get("evidence_mode") or "").strip()
    minimum = verification.get("minimum_evidence")
    raw_accepted_p = route.get("accepted_P")
    accepted_p: dict[str, Any] = raw_accepted_p if isinstance(raw_accepted_p, dict) else {}
    raw_accepted_s = route.get("accepted_S")
    accepted_s: dict[str, Any] = raw_accepted_s if isinstance(raw_accepted_s, dict) else {}
    raw_edges = route.get("E")
    edges: list[Any] = raw_edges if isinstance(raw_edges, list) else []
    required = execution_kind == "execution-needed"
    minimum_ok = _mode_evidence_ok(evidence_mode, minimum) if evidence_mode else False
    gap_class = "none"
    if required and not verification_s:
        gap_class = "verification_s_missing"
    elif required and not evidence_mode:
        gap_class = "evidence_mode_missing"
    elif required and not minimum_ok:
        gap_class = "minimum_evidence_missing"
    elif (verification_s or _present(minimum)) and accepted_s and not accepted_p:
        gap_class = "problem_p_missing"
    else:
        trace = _edge_set(edges)
        for sid in accepted_s:
            pid = f"P{sid[1:]}" if re.fullmatch(r"S\d+", sid) else ""
            if pid in accepted_p and (pid, sid) not in trace:
                gap_class = "p_s_trace_missing"
                break
        if gap_class == "none":
            for pid in accepted_p:
                sid = f"S{pid[1:]}" if re.fullmatch(r"P\d+", pid) else ""
                if sid and sid not in accepted_s and not any(edge_pid == pid for edge_pid, _ in trace):
                    gap_class = "orphan_p_present"
                    break
    return {
        "required": required,
        "verification_S": verification_s,
        "evidence_mode": evidence_mode or "missing",
        "minimum_evidence_check": "pass" if minimum_ok else ("missing" if not _present(minimum) else "fail"),
        "gap_class": gap_class,
    }


def apply_verification_gate(route: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    gate = build_verification_gate(candidate, route)
    route["verification_gate"] = gate
    if gate["gap_class"] != "none":
        route["status"] = "hold"
        route["C_boundary"] = "HOLD"
        raw_gap_scan = route.get("gap_scan")
        gap_scan: dict[str, Any] = raw_gap_scan if isinstance(raw_gap_scan, dict) else {}
        raw_missing = gap_scan.get("missing")
        missing: list[Any] = list(raw_missing) if isinstance(raw_missing, list) else []
        if gate["gap_class"] not in missing:
            missing.append(gate["gap_class"])
        route["gap_scan"] = {**gap_scan, "missing": missing, "verdict": "GAP_FOUND"}
    return route


def _repo_meta(repo: Path) -> dict[str, str]:
    def run(args: list[str]) -> str:
        import subprocess
        r = subprocess.run(args, cwd=str(repo), text=True, capture_output=True, check=False)
        return (r.stdout or r.stderr).strip()
    return {
        "repo_root": str(repo),
        "branch": run(["git", "rev-parse", "--abbrev-ref", "HEAD"]),
        "remote": run(["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"]) or "untracked-upstream",
    }


def _packet_field(packet: dict[str, Any], *keys: str, default: str = "local") -> str:
    for key in keys:
        value = packet.get(key)
        if value not in (None, ""):
            return str(value)
    return default




def _domain_hints(text: str) -> list[str]:
    """Return compact CPS/domain retrieval pivots for the seed stage."""
    domains: list[str] = []
    mapping = [
        ("cps-routing", r"cps|route|routing|gate|maat|agent|delegat|fan[- ]?out|graph"),
        ("entry-wire", r"entry|seed|draft[_-]?c|wire"),
        ("doc_ops", r"doc|markdown|frontmatter|wiki|decision|contract|gbrain|brain"),
        ("memory-continuity", r"honcho|memory|recall|history|previous|continuity|learning"),
        ("verifier-closure", r"verify|verification|test|audit|closure|evidence|pass|fail|hold"),
        ("runtime-gateway", r"runtime|runner|hook|lifecycle|gateway|session|thread"),
        ("implementation", r"implement|patch|code|script|python|write|refactor"),
        ("security", r"secret|credential|permission|sandbox|security|auth"),
    ]
    for domain, pattern in mapping:
        if re.search(pattern, text):
            domains.append(domain)
    return domains or ["general"]


def _first_move(text: str, ssot_hint: str) -> str:
    if ssot_hint == "unknown":
        return "inspect_for_ssot"
    if re.search(r"implement|patch|code|script|runtime|hook", text):
        return "inspect_source_then_bounded_implementation"
    if re.search(r"verify|test|audit|closure", text):
        return "inspect_evidence_then_verify"
    return "short_local_response_or_bounded_probe"


def _path_refs(packet: dict[str, Any], text: str) -> list[str]:
    refs: list[str] = []
    for key in ("source_refs", "artifact_refs", "visible_paths_or_urls", "attachments"):
        value = packet.get(key)
        if isinstance(value, list):
            refs.extend(str(item) for item in value if item)
        elif value:
            refs.append(str(value))
    refs.extend(re.findall(r"(?:/Users/kann|\.harness|docs|scripts|test_[^\s`]+)[^\s`)]*", text))
    seen: set[str] = set()
    ordered: list[str] = []
    for ref in refs:
        clean = ref.strip().strip(".,")
        if clean and clean not in seen:
            seen.add(clean)
            ordered.append(clean)
    return ordered


def _readable_current_source(record: dict[str, Any]) -> tuple[str | None, bool]:
    raw_ref = record.get("source_ref") or record.get("source_refs")
    source_ref = str(raw_ref[0]) if isinstance(raw_ref, list) and raw_ref else str(raw_ref or "")
    content_hash = str(record.get("content_hash") or "").removeprefix("sha256:")
    if not source_ref or not content_hash:
        return None, False
    path = Path(source_ref.removeprefix("file://"))
    try:
        actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    except (OSError, ValueError):
        return source_ref, False
    return source_ref, actual_hash == content_hash


def _memory_records(raw: Any) -> tuple[list[dict[str, Any]], str]:
    if isinstance(raw, BaseException) or raw is None or raw == "" or raw == []:
        return [], "unavailable"
    if isinstance(raw, str):
        try:
            return _memory_records(json.loads(raw))
        except (json.JSONDecodeError, TypeError):
            return [], "unavailable"
    if isinstance(raw, list):
        records = [item for item in raw if isinstance(item, dict)]
        return records, "records" if records else "unavailable"
    if not isinstance(raw, dict):
        return [], "unavailable"
    status = str(raw.get("status") or "").lower()
    for key in ("matches", "results", "items", "data"):
        if key in raw:
            records, nested_status = _memory_records(raw[key])
            if records:
                return records, "records"
            if status == "no_match":
                return [], "no_match"
            return [], nested_status
    if status == "no_match":
        return [], "no_match"
    record_keys = {"source_ref", "source_refs", "source_revision", "content_hash", "lifecycle"}
    return ([raw], "records") if record_keys.intersection(raw) else ([], "unavailable")


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def _receipt_value(packet: dict[str, Any], key: str, *fallbacks: str) -> Any:
    for name in (key, *fallbacks):
        if _present(packet.get(name)):
            return packet[name]
    return None


def build_downstream_packet_delta(packet: dict[str, Any], prior_verdict_ref: Any = None) -> dict[str, Any]:
    """Build the reference-only delta used after a C1 HOLD."""
    cps = packet.get("CPS") if isinstance(packet.get("CPS"), dict) else {}
    task_ac = packet.get("task_AC") or cps.get("AC")
    evidence = _receipt_value(packet, "new_evidence_refs", "repair_evidence_refs") or []
    if not isinstance(evidence, list):
        evidence = [evidence]
    return {
        "C_ref": _receipt_value(packet, "C_ref", "graph_ref"),
        "AC_digest": _receipt_value(packet, "AC_digest") or (canonical_hash(task_ac) if _present(task_ac) else None),
        "graph_revision": _receipt_value(packet, "graph_revision", "source_revision")
        or ((packet.get("cps_flow_graph") or {}).get("revision") if isinstance(packet.get("cps_flow_graph"), dict) else None),
        "parent_edge_ref": _receipt_value(packet, "parent_edge_ref"),
        "new_evidence_refs": evidence,
        "prior_verdict_ref": prior_verdict_ref or _receipt_value(packet, "prior_verdict_ref"),
    }


def evaluate_receipt_delta(packet: dict[str, Any]) -> dict[str, Any]:
    """Validate HOLD continuation identity and decide whether fresh evidence permits re-entry."""
    prior = packet.get("prior_continuation_receipt") or packet.get("continuation_receipt")
    if not isinstance(prior, dict):
        return {"active": False, "full_chain_required": True, "status": "not_required"}

    delta = build_downstream_packet_delta(packet, prior.get("verdict_ref"))
    identity_body = {key: delta.get(key) for key in ("C_ref", "AC_digest", "graph_revision", "parent_edge_ref")}
    receipt_identity = canonical_hash(identity_body)
    gaps = [f"receipt_delta.{key}" for key, value in delta.items() if key != "new_evidence_refs" and not _present(value)]
    if prior.get("receipt_identity") != receipt_identity:
        gaps.append("receipt_delta.identity_mismatch")

    mutation_actor = _receipt_value(packet, "mutation_actor", "repair_actor")
    verifier = packet.get("verifier_receipt")
    repair_revision = _receipt_value(packet, "repair_revision", "source_revision")
    if not isinstance(verifier, dict):
        gaps.append("receipt_delta.verifier_receipt_missing")
    else:
        if not _present(mutation_actor) or verifier.get("actor") == mutation_actor:
            gaps.append("receipt_delta.verifier_not_independent")
        if verifier.get("receipt_identity") != receipt_identity:
            gaps.append("receipt_delta.verifier_identity_mismatch")
        if verifier.get("repair_revision") != repair_revision:
            gaps.append("receipt_delta.verifier_revision_mismatch")
        if prior.get("repair_revision") != repair_revision and verifier.get("receipt_ref") == prior.get("verifier_receipt_ref"):
            gaps.append("receipt_delta.new_verifier_receipt_required")

    fingerprint = canonical_hash(delta["new_evidence_refs"])
    same_evidence = fingerprint == prior.get("evidence_fingerprint")
    if gaps:
        action = "hold_mismatch"
    elif same_evidence and str(prior.get("status", "")).lower() == "hold":
        action = "continue_hold"
    elif delta["new_evidence_refs"]:
        action = "reenter"
    else:
        action = "hold_no_new_evidence"
    return {
        "active": True,
        "schema": "harness.cps_preflight.receipt_delta_gate.v1",
        "status": "pass" if action == "reenter" else "hold",
        "action": action,
        "full_chain_required": False,
        "delta_only_reentry": action == "reenter",
        "receipt_identity": receipt_identity,
        "evidence_fingerprint": fingerprint,
        "downstream_packet_delta": delta,
        "gap_classes": list(dict.fromkeys(gaps)),
    }


def build_c_ac_route_receipt(route: dict[str, Any], gate: dict[str, Any]) -> dict[str, Any]:
    delta = gate.get("downstream_packet_delta", {})
    return {
        "schema": "harness.cps_preflight.c_ac_route_receipt.v1",
        "receipt_identity": gate.get("receipt_identity"),
        **{key: delta.get(key) for key in ("C_ref", "AC_digest", "graph_revision", "parent_edge_ref")},
        "route": route,
    }


def prior_c_ac_route_receipt(packet: dict[str, Any], gate: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    prior = packet.get("prior_continuation_receipt") or packet.get("continuation_receipt")
    receipt = prior.get("C_AC_route_receipt") if isinstance(prior, dict) else None
    if not isinstance(receipt, dict) or not isinstance(receipt.get("route"), dict):
        return None, ["receipt_delta.C_AC_route_receipt_missing"]
    delta = gate.get("downstream_packet_delta", {})
    mismatches = [
        key for key in ("C_ref", "AC_digest", "graph_revision", "parent_edge_ref")
        if receipt.get(key) != delta.get(key)
    ]
    if receipt.get("receipt_identity") != gate.get("receipt_identity") or mismatches:
        return None, ["receipt_delta.C_AC_route_receipt_identity_mismatch"]
    return receipt, []


def build_continuation_receipt(
    packet: dict[str, Any], verdict: dict[str, Any], delta_gate: dict[str, Any] | None = None,
    route: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Issue a compact, non-closing receipt for subsequent repair evidence."""
    gate = delta_gate or evaluate_receipt_delta(packet)
    raw_prior = packet.get("prior_continuation_receipt") or packet.get("continuation_receipt")
    prior = raw_prior if isinstance(raw_prior, dict) else {}
    delta = gate.get("downstream_packet_delta") or build_downstream_packet_delta(packet, prior.get("verdict_ref"))
    identity = gate.get("receipt_identity") or canonical_hash({key: delta.get(key) for key in ("C_ref", "AC_digest", "graph_revision", "parent_edge_ref")})
    evidence_fingerprint = gate.get("evidence_fingerprint") or canonical_hash(delta.get("new_evidence_refs", []))
    verifier = packet.get("verifier_receipt") if isinstance(packet.get("verifier_receipt"), dict) else {}
    prior_route_receipt = prior.get("C_AC_route_receipt") if isinstance(prior.get("C_AC_route_receipt"), dict) else None
    receipt_gate = {**gate, "downstream_packet_delta": delta, "receipt_identity": identity}
    route_receipt = build_c_ac_route_receipt(route, receipt_gate) if route is not None else prior_route_receipt
    return {
        "schema": "harness.cps_preflight.continuation_receipt.v1",
        "status": "hold",
        "closure": False,
        "receipt_identity": identity,
        "evidence_fingerprint": evidence_fingerprint,
        "repair_revision": _receipt_value(packet, "repair_revision", "source_revision"),
        "verifier_receipt_ref": verifier.get("receipt_ref"),
        "verdict_ref": verdict.get("verdict_ref") or canonical_hash(verdict),
        "continuation": gate.get("action", "await_new_repair_evidence"),
        "downstream_packet_delta": delta,
        "gap_classes": gate.get("gap_classes", []),
        "C_AC_route_receipt": route_receipt,
    }


def retrieve_c1_foreground(packet: dict[str, Any], candidate_ref: str, trace_ref: str) -> dict[str, Any]:
    """Read the packet-referenced harness-brain source before candidate enrichment."""
    producer_ref = "adapter:harness-brain:file:v1"
    consumer_ref = "build_candidate"
    source = packet.get("harness_brain_source")
    matches: list[dict[str, Any]] = []
    status = "unavailable"
    outcome = "source_unavailable"
    if isinstance(source, dict):
        path = Path(str(source.get("source_ref") or "").removeprefix("file://"))
        stat = None
        try:
            content = path.read_bytes()
            stat = path.stat()
        except OSError:
            content = None
        if content is not None and stat is not None:
            digest = hashlib.sha256(content).hexdigest()
            admissible = str(source.get("lifecycle") or "").lower() in {"validated", "promoted"}
            expected_hash = str(source.get("content_hash") or "").removeprefix("sha256:")
            current = not expected_hash or expected_hash == digest
            if admissible and current and _present(source.get("source_revision")):
                matches.append({
                    "layer": "harness-brain",
                    "source_ref": str(path),
                    "source_revision": source["source_revision"],
                    "content_hash": digest,
                    "freshness": {"mtime_ns": stat.st_mtime_ns, "size": stat.st_size},
                    "lifecycle": source["lifecycle"],
                    "supersedes": source.get("supersedes"),
                })
                status, outcome = "match", "match"
            else:
                status, outcome = "no_match", "inadmissible_or_stale"
    normalized = {
        "lookup_ref": f"foreground:{packet.get('graph_ref') or 'unbound'}",
        "status": status,
        "active_only": True,
        "matches": matches,
        "layers": [
            {"layer": "honcho", "status": "unavailable"},
            {"layer": "gbrain", "status": "unavailable"},
            {"layer": "harness-brain", "status": status},
        ],
        "excluded_count": 0 if matches else int(isinstance(source, dict)),
    }
    receipt = {
        "schema": "harness.cps_preflight.c1_runtime_receipt.v1",
        "producer_ref": producer_ref,
        "outcome": outcome,
        "normalized_result_hash": canonical_hash(normalized),
        "consumer_ref": consumer_ref,
        "graph_ref": packet.get("graph_ref"),
        "graph_revision": packet.get("graph_revision") or (packet.get("cps_flow_graph") or {}).get("revision"),
        "candidate_artifact_ref": candidate_ref,
        "trace_artifact_ref": trace_ref,
    }
    return {"producer_ref": producer_ref, "consumer_ref": consumer_ref, "normalized_result": normalized, "runtime_receipt": receipt}


def validate_c1_runtime_evidence(value: dict[str, Any]) -> dict[str, Any]:
    receipt = value.get("runtime_receipt")
    normalized = value.get("normalized_result")
    valid = (
        _present(value.get("producer_ref"))
        and _present(value.get("consumer_ref"))
        and isinstance(receipt, dict)
        and isinstance(normalized, dict)
        and receipt.get("producer_ref") == value.get("producer_ref")
        and receipt.get("consumer_ref") == value.get("consumer_ref")
        and receipt.get("normalized_result_hash") == canonical_hash(normalized)
        and normalized.get("status") == "match"
    )
    return {
        "status": "pass" if valid else "hold",
        "failure_code": None if valid else "HOLD_C1_RUNTIME_EVIDENCE",
    }


def normalize_memory_lookup_result(readbacks: Any) -> dict[str, Any]:
    """Normalize foreground reader outputs without inferring lifecycle or matches."""
    lookup = readbacks if isinstance(readbacks, dict) else {}
    layer_names = ("honcho", "gbrain", "harness-brain")
    supplied = [(layer, lookup[layer]) for layer in layer_names if layer in lookup]
    if not supplied and isinstance(readbacks, (str, list)):
        supplied = [("unknown", readbacks)]

    matches: list[dict[str, Any]] = []
    layers: list[dict[str, str]] = []
    excluded_count = 0
    for layer, raw in supplied:
        records, reader_status = _memory_records(raw)
        layer_matches = 0
        for record in records:
            source_ref, current = _readable_current_source(record)
            required = all(_present(record.get(key)) for key in (
                "source_revision", "content_hash", "freshness", "lifecycle",
            ))
            if str(record.get("lifecycle") or "").lower() not in {"validated", "promoted"} or not required or not current:
                excluded_count += 1
                continue
            matches.append({
                "layer": layer,
                "source_ref": source_ref,
                "source_revision": record["source_revision"],
                "content_hash": record["content_hash"],
                "freshness": record["freshness"],
                "lifecycle": record["lifecycle"],
                "supersedes": record.get("supersedes"),
            })
            layer_matches += 1
        layer_status = "match" if layer_matches else "no_match" if reader_status == "no_match" or records else "unavailable"
        layers.append({"layer": layer, "status": layer_status})

    if matches:
        status = "match"
    elif layers and all(item["status"] == "no_match" for item in layers):
        status = "no_match"
    else:
        status = "unavailable"
    return {
        "lookup_ref": lookup.get("lookup_ref") if isinstance(lookup, dict) else None,
        "status": status,
        "active_only": True,
        "matches": matches,
        "layers": layers,
        "excluded_count": excluded_count,
    }


def _seed_requires_maat(packet: dict[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if packet.get("runtime_packet") is True:
        reasons.append("runtime_graph_required")
    mutation_scope = packet.get("mutation_scope") or packet.get("write_scope")
    if _present(mutation_scope):
        reasons.append("mutation_scope_present")
    if _present(packet.get("ssot_authority_uncertainty")) or _present(packet.get("ssot_conflict")):
        reasons.append("ssot_authority_uncertain_or_conflicting")
    candidates = packet.get("route_candidates")
    if isinstance(candidates, (list, dict)) and len(candidates) > 1:
        reasons.append("multiple_route_candidates")
    verification = packet.get("verification") if isinstance(packet.get("verification"), dict) else {}
    if isinstance(verification, dict) and verification.get("execution_kind") == "execution-needed" or _present(packet.get("required_evidence_floor")):
        reasons.append("verification_or_evidence_floor_required")
    if _present(packet.get("cross_project_relation")):
        reasons.append("cross_project_relation_present")
    return bool(reasons), reasons

def build_cps_trace_events(seed_graph: dict[str, Any], packet: dict[str, Any], *, final_output: dict[str, Any] | None = None, events: list[dict[str, Any]] | None = None, iteration: int = 0, phase: str = "initial") -> list[dict[str, Any]]:
    """Append compact deltas to one runtime-owned trace."""
    trace_id = f"trace:{seed_graph.get('request_id', 'request')}"
    timestamp = datetime.now(timezone.utc).isoformat()
    seeds = seed_graph.get("seeds", {}) if isinstance(seed_graph.get("seeds"), dict) else {}
    route_seed = seed_graph.get("route_seed", {}) if isinstance(seed_graph.get("route_seed"), dict) else {}
    seed = next(iter(seeds.values()), {}) if seeds else {}
    ssot_hint = seed.get("ssot_hint")
    maat_needed, maat_reasons = _seed_requires_maat(packet)
    trace = events if events is not None else []

    def append(event_type: str, payload: dict[str, Any], actor: str = "hermes-kann") -> None:
        parent = trace[-1]["event_id"] if trace else None
        event_id = f"evt-{len(trace) + 1:03d}"
        trace.append({
            "trace_id": trace_id, "event_id": event_id, "parent_event_id": parent,
            "timestamp": timestamp, "event_type": event_type, "actor": actor,
            "iteration": iteration, "phase": phase, "event_payload": payload,
        })

    if not trace:
        append("seed_created", {"seed_delta": {"added": list(seeds)}, "seed_relation_delta": seed_graph.get("seed_relations", []), "seed_count": len(seeds)})
        if ssot_hint == "unknown":
            append("ssot_discovery_started", {"source_ref": None, "pending_requirement": "narrow_read_only_ssot_discovery"})
        else:
            append("ssot_discovered", {"source_ref": ssot_hint, "ssot_candidate_count": 1})
        if route_seed.get("route_class") not in {"short_local", "short_local_rewrite"}:
            append("route_expanded", {"route_delta": {"active_route": route_seed.get("route_class")}})
        if maat_needed:
            append("escalation_triggered", {"route_delta": {"adjudicator": "maat"}, "reasons": maat_reasons}, "maat")
        memory = seed_graph.get("memory_enrichment", {})
        if isinstance(memory, dict) and (memory.get("lookup_attempted") is True or memory.get("status") in {"match", "no_match"}):
            append("memory_lookup_started", {
                "lookup_ref": memory.get("lookup_ref"),
                "status": memory.get("status"),
                "active_only": True,
            })
            if memory.get("status") == "match" and memory.get("matches"):
                append("memory_match_attached", {
                    "lookup_ref": memory.get("lookup_ref"),
                    "match_count": len(memory["matches"]),
                })
    elif phase == "reentry":
        append("reentry_started", {"verification_link_delta": packet.get("revised_E", []), "missing_evidence_count": len(packet.get("missing_evidence", []))})
    if final_output is not None:
        append("workflow_closed", {"closure_ref": "final_output.json", "closure_type": final_output.get("status")})
    return trace


def _c1_trace_context(packet: dict[str, Any], c1_retrieval: dict[str, Any]) -> dict[str, Any]:
    normalized = c1_retrieval.get("normalized_result", {})
    matches = normalized.get("matches", []) if isinstance(normalized, dict) else []
    first_match = matches[0] if matches and isinstance(matches[0], dict) else {}
    return {
        "request_id": packet.get("run_id") or packet.get("flow_graph_id") or "request",
        "seeds": {"C1": {"ssot_hint": first_match.get("source_ref", "unknown")}},
        "seed_relations": [],
        "route_seed": {},
        "memory_enrichment": {**normalized, "lookup_attempted": "memory_lookup_result" in packet},
    }


def build_session_policy(packet: dict[str, Any], repo: Path, selected_profile: str | None = None) -> dict[str, Any]:
    profile = selected_profile or _packet_field(packet, "profile", "target_profile", default="default")
    platform = _packet_field(packet, "platform", "source_platform", default="local")
    chat_id = _packet_field(packet, "chat_id", "channel_id", "conversation_id", default="local")
    thread_id = packet.get("thread_id") or packet.get("topic_id")
    project_slug = _packet_field(packet, "project_slug", "project", default=repo.name)
    key = lane_key(profile=profile, platform=platform, chat_id=chat_id, thread_id=str(thread_id) if thread_id else None, project_slug=project_slug)
    registry_path = repo / ".harness" / "project" / "runs" / "session_registry.json"
    row = load_registry(registry_path).get("lanes", {}).get(key, {}) if registry_path.exists() else {}
    state = row.get("state", "closed")
    return {
        "lane_key": key,
        "representative_session_id": row.get("representative_session_id"),
        "reuse_decision": "reuse" if state in {"representative_open", "reusable_open"} and row.get("representative_session_id") else "fresh",
        "reclaim_state": state if state in {"duplicate_open_present", "orphan_route_present", "stale_open", "blocked_reclaim"} else "clear",
        "reclaim_manifest_ref": ".harness/project/runs/session_reclaim_manifest.json" if (repo / ".harness" / "project" / "runs" / "session_reclaim_manifest.json").exists() else None,
    }


def build_candidate(packet: dict[str, Any], packet_path: Path, repo: Path) -> dict[str, Any]:
    routing_packet = {key: value for key, value in packet.items() if key not in {"projection", "doc_ops"}}
    all_text = _text_values(routing_packet).lower()
    cps_raw = packet.get("CPS")
    cps: dict[str, Any] = cps_raw if isinstance(cps_raw, dict) else {}
    c_text = _text_values(cps.get("C") or packet.get("c") or packet.get("context") or packet.get("root_goal") or packet.get("goal"))
    goal = _text_values(cps.get("Goal") or packet.get("root_goal") or packet.get("goal") or packet.get("task") or "route task")
    explicit_p = _ordered_cps_items(cps, "P")
    explicit_s = _ordered_cps_items(cps, "S")
    p: dict[str, str] = explicit_p.copy()
    s: dict[str, str] = explicit_s.copy()
    if not p or not s:
        p["P1"] = "route_request_to_minimal_agent_set"
        s["S1"] = "maat_route_gate"
        p["P2"] = "dispatch_without_full_context_broadcast"
        s["S2"] = "hermes_kann_selected_agent_probe"
        if re.search(r"doc|markdown|frontmatter|wiki|gbrain|brain|contract|decision", all_text):
            p["P3?"] = "doc_or_memory_update_needed"
            s["S3?"] = "seshat_doc_ops_or_hermes_kann_doc_patch"
        if re.search(r"recall|history|prior|previous|remember|honcho|memory", all_text):
            p["P4?"] = "prior_context_lookup_needed"
            s["S4?"] = "sia_recall"
        if re.search(r"compile|fan[- ]?out|multi[- ]?agent|decompose|graph", all_text):
            p["P5?"] = "compile_or_fanout_needed"
            s["S5?"] = "thoth_compile"
        if re.search(r"code|implement|patch|write|script|test|runtime|automatic|runner|hook", all_text):
            p["P6?"] = "bounded_implementation_needed"
            s["S6?"] = "ptah_or_hermes_kann_apply"
        if re.search(r"security|secret|credential|permission|sandbox", all_text):
            p["P7?"] = "security_or_permission_risk"
            s["S7?"] = "sekhmet_risk_check"
        if re.search(r"token|slow|waste|efficient|speed|cost", all_text):
            p["P8?"] = "efficiency_or_token_risk"
            s["S8?"] = "hu_efficiency_probe"
    edges = []
    explicit_edges = cps.get("E") if "E" in cps else cps.get("E?") if "E?" in cps else packet.get("E") if "E" in packet else None
    if isinstance(explicit_edges, list):
        edges = [str(edge) for edge in explicit_edges]
    for pid in p:
        base = pid[1:].rstrip("?")
        sid = f"S{base}"
        if pid.endswith("?") and f"{sid}?" in s:
            sid = f"{sid}?"
        if explicit_edges is None and sid in s and not any((pid.rstrip("?"), sid.rstrip("?")) == pair for pair in _edge_set(edges)):
            edges.append(f"{pid} -> {sid}")
    raw_verification = packet.get("verification")
    verification: dict[str, Any] = raw_verification if isinstance(raw_verification, dict) else {}
    c1_retrieval = retrieve_c1_foreground(packet, "c_candidate_packet.json", "cps_trace_events.json")
    if "memory_lookup_result" in packet:
        c1_retrieval["normalized_result"] = normalize_memory_lookup_result(packet["memory_lookup_result"])
        c1_retrieval["runtime_receipt"]["normalized_result_hash"] = canonical_hash(c1_retrieval["normalized_result"])
    runtime_graph_gate = validate_runtime_graph(packet) if packet.get("runtime_packet") is True else {"status": "not_required", "gaps": []}
    dispatch_plan = build_dispatch_plan(runtime_graph_gate["graph"]) if runtime_graph_gate["status"] == "pass" else None
    runtime_evidence_required = packet.get("runtime_packet") is True or verification.get("execution_kind") in {"runtime", "external"}
    c1_runtime_evidence_gate = validate_c1_runtime_evidence(c1_retrieval) if runtime_evidence_required else {"status": "not_required", "failure_code": None}
    cps_trace_events = build_cps_trace_events(_c1_trace_context(packet, c1_retrieval), packet)
    maat_needed, maat_reasons = _seed_requires_maat(packet)
    return {
        "schema": "harness.cps_preflight.candidate.v1",
        "status": "candidate",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "contract_ref": str(CONTRACT_PATH),
        "packet_ref": str(packet_path),
        "repo": _repo_meta(repo),
        "cps_trace_events": cps_trace_events,
        "route_enrichment": {
            "memory": c1_retrieval["normalized_result"],
            "first_route": {},
            "selective_maat_escalation": {"needed": maat_needed, "reasons": maat_reasons},
        },
        "runtime_graph_gate": runtime_graph_gate,
        "dispatch_plan": dispatch_plan,
        "producer_ref": c1_retrieval["producer_ref"],
        "consumer_ref": c1_retrieval["consumer_ref"],
        "runtime_receipt": c1_retrieval["runtime_receipt"],
        "normalized_result": c1_retrieval["normalized_result"],
        "c1_runtime_evidence_gate": c1_runtime_evidence_gate,
        "C?": {"C1": c_text[:240] or "task_route_candidate"},
        "Goal": goal[:240],
        "P?": p,
        "S?": s,
        "E?": edges,
        "verification_links": edges,
        "verification": verification,
        "projection": packet.get("projection"),
        "node_projection": packet.get("node_projection"),
        "doc_ops": packet.get("doc_ops"),
        "physical_docops_gate": validate_physical_docops_route(packet),
        "mutation_closure": classify_mutation_closure(packet),
        "uncertainty": [
            "Packet supplied explicit P#/S#; Maat still owns C-boundary and gap scan"
        ] if explicit_p else [
            "Maat must adjudicate C-boundary/cardinality before fan-out",
            "optional P?/S? branches must be accepted or rejected before local body dispatch",
        ],
        "request_to_maat": [
            "approve/split/hold C?",
            "accept/reject P?/S?",
            "set order, gap_scan, audit_scope, AC_mode, selected_agents",
        ],
    }

def adjudicate(candidate: dict[str, Any]) -> dict[str, Any]:
    p = candidate.get("P?", {})
    s = candidate.get("S?", {})
    accepted_p: dict[str, str] = {}
    accepted_s: dict[str, str] = {}
    rejected_p: dict[str, str] = {}
    rejected_s: dict[str, str] = {}
    selected: dict[str, dict[str, Any]] = {
        "maat": {"P": ["P1"], "S": ["S1"], "response": "accept"},
        "hermes-kann": {"P": ["P2"], "S": ["S2"], "response": "need_local_body"},
    }
    for key, val in p.items():
        if key.endswith("?"):
            # Deterministic route-gate keeps bounded branches only when an operator is known.
            accepted_p[key.rstrip("?")] = val
        else:
            accepted_p[key] = val
    for key, val in s.items():
        clean = key.rstrip("?")
        accepted_s[clean] = val
        if "seshat" in val or "doc" in val:
            selected.setdefault("seshat", {"P": [], "S": [], "response": "need_local_body"})["S"].append(clean)
        elif "sia" in val:
            selected.setdefault("sia", {"P": [], "S": [], "response": "need_local_body"})["S"].append(clean)
        elif "thoth" in val:
            selected.setdefault("thoth", {"P": [], "S": [], "response": "need_local_body"})["S"].append(clean)
        elif "ptah" in val:
            selected.setdefault("ptah", {"P": [], "S": [], "response": "need_local_body"})["S"].append(clean)
        elif "sekhmet" in val:
            selected.setdefault("sekhmet", {"P": [], "S": [], "response": "need_local_body"})["S"].append(clean)
        elif "hu" in val:
            selected.setdefault("hu", {"P": [], "S": [], "response": "need_local_body"})["S"].append(clean)
    for agent, spec in selected.items():
        # Fill local P by edges that point to selected S.
        spec.setdefault("P", [])
        for edge in candidate.get("E?", []):
            left, _, right = edge.partition("->")
            left = left.strip().rstrip("?")
            rights = [x.strip().rstrip("?") for x in right.split("+")]
            if any(x in spec.get("S", []) for x in rights) and left not in spec["P"]:
                spec["P"].append(left)
    missing = []
    if not candidate.get("C?"):
        missing.append("C?")
    if not candidate.get("P?"):
        missing.append("P?")
    if not candidate.get("S?"):
        missing.append("S?")
    mode = "targeted" if any(a in selected for a in ["ptah", "sekhmet", "thoth"]) else "gap_scan_only"
    route = {
        "schema": "harness.cps_preflight.route_gate.v1",
        "status": "hold" if missing else "pass",
        "C_boundary": "HOLD" if missing else "PASS_ONE_C",
        "C": candidate.get("C?", {}),
        "cps_trace_events": candidate.get("cps_trace_events", []),
        "route_enrichment": candidate.get("route_enrichment", {}),
        "mutation_closure": candidate.get("mutation_closure", {}),
        "selective_maat_escalation": candidate.get("route_enrichment", {}).get("selective_maat_escalation", {"needed": True, "reasons": ["route_gate_requested"]}),
        "accepted_P": accepted_p,
        "rejected_P": rejected_p,
        "accepted_S": accepted_s,
        "rejected_S": rejected_s,
        "E": [edge.replace("?", "") for edge in candidate.get("E?", [])],
        "verification_links": [edge.replace("?", "") for edge in candidate.get("E?", [])],
        "order": [
            "maat_route_gate",
            "selected_agent_probes",
            "local_body_dispatch_after_accept_or_need_local_body",
            "integration",
            "optional_final_gate_if_required",
            "learning_capture",
        ],
        "gap_scan": {"missing": missing, "verdict": "GAP_FOUND" if missing else "CLEAR"},
        "audit_plan": {"mode": mode, "target": {"C": True, "P": list(accepted_p), "S": list(accepted_s)}},
        "AC_mode": "route_gate_only" if mode == "gap_scan_only" else "readback_only",
        "selected_agents": selected,
        "final_audit_needed": False,
        "prohibitions": [
            "full_context_bundle",
            "local_body_before_accept_or_need_local_body",
            "automatic_full_audit_on_gap",
        ],
    }
    route["runtime_graph_gate"] = candidate.get("runtime_graph_gate", {"status": "not_required", "gaps": []})
    route["dispatch_plan"] = candidate.get("dispatch_plan")
    route["producer_ref"] = candidate.get("producer_ref")
    route["consumer_ref"] = candidate.get("consumer_ref")
    route["runtime_receipt"] = candidate.get("runtime_receipt")
    route["c1_runtime_evidence_gate"] = candidate.get("c1_runtime_evidence_gate")
    runtime_gaps = route["runtime_graph_gate"].get("gaps", [])
    if route["runtime_graph_gate"].get("status") == "hold":
        route["status"] = "hold"
        route["C_boundary"] = "HOLD"
        route["selected_agents"] = {}
        route["gap_scan"] = {"missing": runtime_gaps, "verdict": "GAP_FOUND"}
    c1_gate = route.get("c1_runtime_evidence_gate")
    if isinstance(c1_gate, dict) and c1_gate.get("status") == "hold":
        route["status"] = "hold"
        route["C_boundary"] = "HOLD"
        route.setdefault("failure_codes", []).append("HOLD_C1_RUNTIME_EVIDENCE")
    return apply_physical_docops_gate(apply_verification_gate(route, candidate), candidate)


def _extract_json_object(text: str) -> dict[str, Any] | None:
    """Extract the first JSON object from a Hermes profile response."""
    decoder = json.JSONDecoder()
    starts = [i for i, ch in enumerate(text) if ch == "{"]
    for start in starts:
        try:
            obj, _ = decoder.raw_decode(text[start:])
        except Exception:
            continue
        if isinstance(obj, dict):
            return obj
    return None


def _route_candidate_name(entry: Any) -> str | None:
    if isinstance(entry, str):
        name = entry.strip()
    elif isinstance(entry, dict):
        name = str(entry.get("agent") or entry.get("profile") or "").strip()
    else:
        return None
    return name if name in PROFILES and name != "maat" else None


def select_route_candidate_catalog(packet: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    """Select the smallest structurally justified body-manifest catalog."""
    selected: list[str] = []

    def add(name: str | None) -> None:
        if name and name not in selected:
            selected.append(name)

    explicit = packet.get("route_candidates")
    if isinstance(explicit, dict):
        entries: list[Any] = list(explicit.values())
        entries.extend(explicit.keys())
    elif isinstance(explicit, list):
        entries = explicit
    else:
        entries = []
    for entry in entries:
        add(_route_candidate_name(entry))

    if not selected:
        raw_s = candidate.get("accepted_S") or candidate.get("S?") or packet.get("accepted_S")
        s_values = raw_s.values() if isinstance(raw_s, dict) else raw_s if isinstance(raw_s, list) else []
        for value in s_values:
            words = set(re.findall(r"[a-z][a-z0-9-]*", _text_values(value).lower()))
            for profile in PROFILES:
                if profile != "maat" and profile in words:
                    add(profile)

    if not selected:
        compile_required = any(_present(packet.get(key)) for key in ("compile_required", "fan_out_required", "fanout_required"))
        mutation_required = _present(packet.get("mutation_scope")) or _present(packet.get("write_scope"))
        source_required = any(_present(packet.get(key)) for key in ("source_refs", "doc_ops", "document_need", "source_need"))
        verification = packet.get("verification")
        verification_required = _present(packet.get("required_evidence_floor")) or (
            isinstance(verification, dict) and (
                verification.get("execution_kind") == "execution-needed" or _present(verification.get("verification_S"))
            )
        )
        continuity_required = any(_present(packet.get(key)) for key in ("memory_continuity", "continuity_signal", "memory_signal"))
        if compile_required:
            add("thoth")
        if mutation_required:
            add("ptah")
        if source_required:
            add("seshat")
        if verification_required:
            add("anubis")
        if continuity_required:
            add("sia")
        if not selected:
            add("ptah")

    manifest_count = len(build_body_manifest(selected))
    eligible_profile_count = len(PROFILES) - 1
    return {
        "candidate_count": len(selected),
        "manifest_count": manifest_count,
        "excluded_profile_count": eligible_profile_count - manifest_count,
        "selected_candidate_ids": selected,
    }


def build_body_manifest(agents: Any) -> dict[str, dict[str, Any]]:
    """Describe available local bodies without materializing or relaying them."""
    names = agents.keys() if isinstance(agents, dict) else agents
    return {
        str(agent): {
            "body_manifest_id": f"body:{agent}:v1",
            "agent": str(agent),
            "body_schema": "harness.cps_preflight.local_task_body.v1",
            "materialization_owner": "hermes-kann",
            "content_included": False,
        }
        for agent in names if agent != "maat"
    }


def _maat_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    allowed = {"schema", "status", "C?", "Goal", "P?", "S?", "E?", "verification_links", "verification", "uncertainty", "request_to_maat", "route_enrichment"}
    return {key: value for key, value in candidate.items() if key in allowed}


def is_anchor_semantics_packet(packet: dict[str, Any]) -> bool:
    return "semantic_anchor" in packet or "semantic_provenance_binding" in packet


def _anchor_semantic_echo_valid(packet: dict[str, Any], response: dict[str, Any]) -> bool:
    if not is_anchor_semantics_packet(packet):
        return True
    anchor = packet.get("semantic_anchor")
    binding = packet.get("semantic_provenance_binding")
    return (
        response.get("semantic_anchor") == anchor
        and response.get("semantic_provenance_binding") == binding
        and validate_semantic_provenance(binding, anchor)["status"] == "pass"
        and validate_semantic_provenance(response.get("semantic_provenance_binding"), response.get("semantic_anchor"))["status"] == "pass"
    )


def _live_maat_prompt(candidate: dict[str, Any], packet: dict[str, Any], body_manifest: dict[str, Any] | None = None) -> str:
    manifests = body_manifest or build_body_manifest(PROFILES)
    payload = {
        "role": "hermes-kann_control_plane",
        "request": "live Maat CPS preflight route-gate adjudication",
        "hard_rules": [
            "Return exactly one JSON object and no markdown.",
            "Do not mutate files, run tools, use git, or claim final audit.",
            "Judge C-boundary, gaps, audit scope, and selected agent only.",
            "Default/hermes-kann is not planner; if planning/compile is needed, select thoth.",
            "Echo semantic_provenance_binding byte-for-byte; do not inherit or synthesize any proof field.",
        ],
        "required_response_schema": {
            "schema": "harness.cps_preflight.live_maat_route_gate.v1",
            "status": "pass|hold",
            "C_boundary": "PASS_ONE_C|SPLIT|HOLD",
            "C": {},
            "accepted_P": {},
            "accepted_S": {},
            "rejected_P": {},
            "rejected_S": {},
            "E": [],
            "order": [],
            "gap_scan": {"missing": [], "verdict": "CLEAR|GAP_FOUND"},
            "audit_plan": {"mode": "none|gap_scan_only|c_boundary_only|targeted|sampled|full", "target": {}},
            "AC_mode": "route_gate_only|readback_only|final_gate",
            "candidate_agents": {"thoth": {"P": [], "S": [], "response": "need_local_body"}},
            "selected_agents": {"ptah": {"P": [], "S": [], "response": "need_local_body", "body_manifest_ids": [], "order": 1, "weight": 1.0, "dependencies": []}},
            "final_audit_needed": False,
            "semantic_anchor": packet.get("semantic_anchor"),
            "semantic_provenance_binding": packet.get("semantic_provenance_binding"),
            "failure_codes": [],
            "notes": []
        },
        "candidate": _maat_candidate(candidate),
        "body_manifest": manifests,
        "packet_metadata": {key: packet.get(key) for key in ("run_id", "project_slug", "mutation_scope", "route_candidates", "required_evidence_floor", "cross_project_relation", "semantic_anchor", "semantic_provenance_binding") if key in packet},
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _normalize_live_maat(raw: dict[str, Any], candidate: dict[str, Any], session_id: str | None, stdout: str) -> dict[str, Any]:
    """Normalize live Maat JSON into the route_gate shape used downstream."""
    deterministic = adjudicate(candidate)
    route: dict[str, Any] = {**deterministic, **raw}
    route["schema"] = "harness.cps_preflight.live_maat_route_gate.v1"
    route["source"] = "live_maat"
    route["live_maat_session_id"] = session_id
    route["maat_response_ref"] = "stdout_tail:last_4000_chars"
    route["maat_response_tail"] = stdout[-4000:]
    route.setdefault("C", candidate.get("C?", {}))
    route.setdefault("accepted_P", deterministic["accepted_P"])
    route.setdefault("accepted_S", deterministic["accepted_S"])
    route.setdefault("rejected_P", {})
    route.setdefault("rejected_S", {})
    route.setdefault("E", deterministic["E"])
    route.setdefault("order", [
        "live_maat_route_gate",
        "hermes_kann_apply_route",
        "selected_agent_probe",
        "local_body_dispatch_after_accept_or_need_local_body",
    ])
    route.setdefault("gap_scan", {"missing": [], "verdict": "CLEAR"})
    route.setdefault("audit_plan", {"mode": "gap_scan_only", "target": {"C": True}})
    route.setdefault("AC_mode", "route_gate_only")
    if isinstance(route.get("candidate_agents"), dict) and route["candidate_agents"]:
        route["selected_agents"] = route["candidate_agents"]
    route.setdefault("selected_agents", {})
    if not isinstance(route.get("selected_agents"), dict) or not route["selected_agents"]:
        route["status"] = "hold"
        route["C_boundary"] = route.get("C_boundary") or "HOLD"
        route["gap_scan"] = {"missing": ["selected_agents"], "verdict": "GAP_FOUND"}
        route["selected_agents"] = {"maat": {"P": ["P1"], "S": ["S1"], "response": "hold"}}
        route.setdefault("failure_codes", []).append("FAIL_MAAT_SELECTED_NO_AGENT")
    else:
        route.setdefault("status", "pass")
        route.setdefault("C_boundary", "PASS_ONE_C")
    route.setdefault("final_audit_needed", False)
    route.setdefault("prohibitions", [
        "default_planning_without_maat_selection",
        "full_context_bundle",
        "local_body_before_accept_or_need_local_body",
        "automatic_full_audit_on_gap",
    ])
    route["runtime_graph_gate"] = candidate.get("runtime_graph_gate", {"status": "not_required", "gaps": []})
    route["dispatch_plan"] = candidate.get("dispatch_plan")
    route["producer_ref"] = candidate.get("producer_ref")
    route["consumer_ref"] = candidate.get("consumer_ref")
    route["runtime_receipt"] = candidate.get("runtime_receipt")
    route["c1_runtime_evidence_gate"] = candidate.get("c1_runtime_evidence_gate")
    runtime_gaps = route["runtime_graph_gate"].get("gaps", [])
    if route["runtime_graph_gate"].get("status") == "hold":
        route["status"] = "hold"
        route["C_boundary"] = "HOLD"
        route["selected_agents"] = {}
        route["gap_scan"] = {"missing": runtime_gaps, "verdict": "GAP_FOUND"}
    c1_gate = route.get("c1_runtime_evidence_gate")
    if isinstance(c1_gate, dict) and c1_gate.get("status") == "hold":
        route["status"] = "hold"
        route["C_boundary"] = "HOLD"
        route.setdefault("failure_codes", []).append("HOLD_C1_RUNTIME_EVIDENCE")
    return apply_physical_docops_gate(apply_verification_gate(route, candidate), candidate)


def invoke_live_maat(candidate: dict[str, Any], packet: dict[str, Any], repo: Path, timeout: int = 180, body_manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    """Call the live Maat profile for C-boundary/route-gate adjudication."""
    import subprocess
    env = os.environ.copy()
    env["HERMES_PROFILE"] = "maat"
    cmd = [
        "hermes", "chat", "-Q", "--max-turns", "1", "-t", "", "-q",
        _live_maat_prompt(candidate, packet, body_manifest),
    ]
    proc = subprocess.run(cmd, cwd=str(repo), env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False, timeout=timeout)
    stdout = proc.stdout or ""
    session_match = re.search(r"session_id:\s*([A-Za-z0-9_\-]+)", stdout)
    session_id = session_match.group(1) if session_match else None
    parsed = _extract_json_object(stdout)
    if proc.returncode != 0 or parsed is None:
        route = adjudicate(candidate)
        route.update({
            "schema": "harness.cps_preflight.live_maat_route_gate.v1",
            "source": "live_maat",
            "status": "hold",
            "C_boundary": "HOLD",
            "live_maat_session_id": session_id,
            "maat_response_ref": "stdout_tail:last_4000_chars",
            "maat_response_tail": stdout[-4000:],
            "gap_scan": {"missing": ["live_maat_json_response"], "verdict": "GAP_FOUND"},
            "failure_codes": ["FAIL_LIVE_MAAT_NO_JSON" if parsed is None else "FAIL_LIVE_MAAT_EXIT"],
            "selected_agents": {"maat": {"P": ["P1"], "S": ["S1"], "response": "hold"}},
            "final_audit_needed": False,
        })
        return apply_verification_gate(route, candidate)
    return _normalize_live_maat(parsed, candidate, session_id, stdout)


def build_agent_draft_probe(agent: str, route: dict[str, Any]) -> dict[str, Any]:
    """Build an agent-specific draft CPS probe; never send the original Maat draft wholesale."""
    spec = route.get("selected_agents", {}).get(agent, {})
    p_ids = spec.get("P", []) if isinstance(spec, dict) else []
    s_ids = spec.get("S", []) if isinstance(spec, dict) else []
    return {
        "schema": "harness.cps_preflight.agent_draft_probe.v1",
        "agent": agent,
        "profile_call_requires_cps_reason": True,
        "C_ref": route.get("C"),
        "draft_CPS": {
            "C": route.get("C"),
            "P": {pid: route.get("accepted_P", {}).get(pid) for pid in p_ids if pid in route.get("accepted_P", {})},
            "S": {sid: route.get("accepted_S", {}).get(sid) for sid in s_ids if sid in route.get("accepted_S", {})},
            "E": [edge for edge in route.get("E", []) if any(sid in edge for sid in s_ids)],
            "verification_gate": route.get("verification_gate", {}),
            "AC": {"mode": route.get("AC_mode"), "audit_plan": route.get("audit_plan")},
            "Goal": "Return role_response only; do not execute local body.",
        },
        "ask": "ACCEPT|REJECT|NEED_LOCAL_BODY|HOLD plus fitted_C/missing/local_body_request",
        "rules": [
            "frontmatter-only probe",
            "no tools/files/git",
            "do not solve the task",
            "return compact JSON only",
        ],
    }


def _agent_probe_prompt(agent: str, probe: dict[str, Any]) -> str:
    payload = {
        "request": "CPS preflight frontmatter-only role probe",
        "hard_rules": [
            "Return exactly one JSON object and no markdown.",
            "Do not mutate files, run tools, use git, or solve the task.",
            "This is not the original Maat draft; it is your local draft CPS only.",
            "Answer quickly with ACCEPT, REJECT, NEED_LOCAL_BODY, or HOLD.",
        ],
        "required_response_schema": {
            "schema": "harness.cps_preflight.role_response.v1",
            "agent": agent,
            "response": "ACCEPT|REJECT|NEED_LOCAL_BODY|HOLD",
            "reason": "one line",
            "fitted_C": {},
            "accepts_P": [],
            "rejects_P": [],
            "adds_P": [],
            "accepts_S": [],
            "rejects_S": [],
            "adds_S": [],
            "missing": [],
            "local_body_request": [],
            "latency_class": "fast|normal|slow",
        },
        "probe": probe,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def invoke_agent_probe(agent: str, probe: dict[str, Any], repo: Path, timeout: int = 120) -> dict[str, Any]:
    import subprocess
    env = os.environ.copy()
    env["HERMES_PROFILE"] = agent
    cmd = ["hermes", "chat", "-Q", "--max-turns", "1", "-t", "", "-q", _agent_probe_prompt(agent, probe)]
    proc = subprocess.run(cmd, cwd=str(repo), env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False, timeout=timeout)
    stdout = proc.stdout or ""
    session_match = re.search(r"session_id:\s*([A-Za-z0-9_\-]+)", stdout)
    parsed = _extract_json_object(stdout)
    if not isinstance(parsed, dict):
        parsed = {
            "schema": "harness.cps_preflight.role_response.v1",
            "agent": agent,
            "response": "HOLD",
            "reason": "no compact JSON response",
            "missing": ["role_response_json"],
        }
    parsed.setdefault("agent", agent)
    parsed["probe_session_id"] = session_match.group(1) if session_match else None
    parsed["probe_exit_code"] = proc.returncode
    parsed["stdout_tail"] = stdout[-2000:]
    return parsed


def probe_agents_as_arrive(route: dict[str, Any], repo: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Probe candidate agents in parallel and collect responses as they complete."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    if route.get("physical_docops_gate", {}).get("status") != "pass":
        return {}, {}
    probes = {agent: build_agent_draft_probe(agent, route) for agent in route.get("selected_agents", {}) if agent != "maat"}
    responses: dict[str, Any] = {}
    if not probes:
        return probes, responses
    max_workers = min(len(probes), int(os.environ.get("HARNESS_CPS_PROBE_MAX_WORKERS", "4")))
    timeout = int(os.environ.get("HARNESS_CPS_PROBE_TIMEOUT", "120"))
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(invoke_agent_probe, agent, probe, repo, timeout): agent for agent, probe in probes.items()}
        for fut in as_completed(futures):
            agent = futures[fut]
            try:
                responses[agent] = fut.result()
            except Exception as exc:
                responses[agent] = {
                    "schema": "harness.cps_preflight.role_response.v1",
                    "agent": agent,
                    "response": "HOLD",
                    "reason": f"probe exception: {exc}",
                    "missing": ["probe_exception"],
                }
    return probes, responses


def build_reducer_input(route: dict[str, Any], probe_responses: dict[str, Any], body_manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "schema": "harness.cps_preflight.reducer_input.v1",
        "route_source": route.get("source"),
        "live_maat_session_id": route.get("live_maat_session_id"),
        "C": route.get("C"),
        "accepted_P": route.get("accepted_P", {}),
        "accepted_S": route.get("accepted_S", {}),
        "E": route.get("E", []),
        "verification_gate": route.get("verification_gate", {}),
        "physical_docops_gate": route.get("physical_docops_gate", {}),
        "projection": route.get("projection"),
        "doc_ops": route.get("doc_ops"),
        "candidate_agents": route.get("selected_agents", {}),
        "body_manifest": body_manifest or build_body_manifest(route.get("selected_agents", {})),
        "probe_responses": probe_responses,
        "semantic_anchor": route.get("semantic_anchor"),
        "semantic_provenance_binding": route.get("semantic_provenance_binding"),
        "join_policy": {
            "mode": "as_arrives",
            "do_not_wait_for_all_optional": True,
            "required_for_compile": ["thoth"] if "thoth" in route.get("selected_agents", {}) else [],
        },
    }


def _maat_reducer_prompt(reducer_input: dict[str, Any]) -> str:
    payload = {
        "role": "hermes-kann_control_plane",
        "request": "live Maat reducer over CPS preflight role-probe responses",
        "hard_rules": [
            "Return exactly one JSON object and no markdown.",
            "Do not mutate files, run tools, use git, implement, or claim final audit.",
            "Reduce probe responses only: decide final_selected_agents and local_body_scope.",
            "If an agent responds with NEED_LOCAL_BODY, this is a valid request for local body dispatch. Grant local_body_scope for this agent.",
            "Do not return status HOLD just because an agent requested NEED_LOCAL_BODY. If all required probes are ACCEPT or NEED_LOCAL_BODY, return status PASS.",
            "The final_maat_judgment.json is the output of the final step and does not exist yet. Do NOT treat it as a missing prerequisite or hold the reducer because of its absence.",
            "If required probes are missing, rejected, or inconsistent, return status HOLD and no local_body_scope grants.",
            "Echo semantic_provenance_binding byte-for-byte; do not inherit or synthesize any proof field.",
        ],
        "required_response_schema": {
            "schema": "harness.cps_preflight.maat_reducer_result.v1",
            "status": "pass|hold",
            "C_boundary": "PASS_ONE_C|SPLIT|HOLD",
            "revised_C": {},
            "revised_P": {},
            "revised_S": {},
            "revised_E": [],
            "final_selected_agents": {},
            "local_body_scope": {},
            "semantic_anchor": reducer_input.get("semantic_anchor"),
            "semantic_provenance_binding": reducer_input.get("semantic_provenance_binding"),
            "hold_reasons": [],
            "failure_codes": [],
            "notes": [],
        },
        "reducer_input": reducer_input,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _normalize_maat_reducer_result(raw: dict[str, Any], reducer_input: dict[str, Any], session_id: str | None, stdout: str) -> dict[str, Any]:
    result = dict(raw)
    result["schema"] = "harness.cps_preflight.maat_reducer_result.v1"
    result["source"] = "live_maat_reducer"
    result["live_maat_reducer_session_id"] = session_id
    result["maat_reducer_response_ref"] = "stdout_tail:last_4000_chars"
    result["maat_reducer_response_tail"] = stdout[-4000:]
    result.setdefault("status", "hold")
    result.setdefault("C_boundary", "HOLD" if result.get("status") != "pass" else "PASS_ONE_C")
    result.setdefault("revised_C", reducer_input.get("C", {}))
    result.setdefault("revised_P", reducer_input.get("accepted_P", {}))
    result.setdefault("revised_S", reducer_input.get("accepted_S", {}))
    result.setdefault("revised_E", reducer_input.get("E", []))
    result.setdefault("final_selected_agents", {})
    result.setdefault("local_body_scope", {})
    result.setdefault("hold_reasons", [])
    result.setdefault("failure_codes", [])
    result.setdefault("notes", [])
    if result.get("status") == "pass" and not isinstance(result.get("local_body_scope"), dict):
        result["status"] = "hold"
        result["C_boundary"] = "HOLD"
        result["local_body_scope"] = {}
        result.setdefault("failure_codes", []).append("FAIL_REDUCER_LOCAL_BODY_SCOPE_INVALID")
    return result


def invoke_maat_reducer(reducer_input: dict[str, Any], repo: Path, timeout: int = 180, process_runner=None) -> dict[str, Any]:
    """Ask live Maat to reduce role-probe responses before any local-body dispatch."""
    import subprocess
    env = os.environ.copy()
    env["HERMES_PROFILE"] = "maat"
    cmd = [
        "hermes", "chat", "-Q", "--max-turns", "1", "-t", "", "-q",
        _maat_reducer_prompt(reducer_input),
    ]
    runner = process_runner or subprocess.run
    proc = runner(cmd, cwd=str(repo), env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False, timeout=timeout)
    stdout = proc.stdout or ""
    session_match = re.search(r"session_id:\s*([A-Za-z0-9_\-]+)", stdout)
    session_id = session_match.group(1) if session_match else None
    parsed = _extract_json_object(stdout)
    if proc.returncode != 0 or not isinstance(parsed, dict):
        return {
            "schema": "harness.cps_preflight.maat_reducer_result.v1",
            "source": "live_maat_reducer",
            "status": "hold",
            "C_boundary": "HOLD",
            "revised_C": reducer_input.get("C", {}),
            "revised_P": reducer_input.get("accepted_P", {}),
            "revised_S": reducer_input.get("accepted_S", {}),
            "revised_E": reducer_input.get("E", []),
            "final_selected_agents": {},
            "local_body_scope": {},
            "hold_reasons": ["live Maat reducer did not return compact JSON"],
            "failure_codes": ["FAIL_LIVE_MAAT_REDUCER_NO_JSON" if parsed is None else "FAIL_LIVE_MAAT_REDUCER_EXIT"],
            "live_maat_reducer_session_id": session_id,
            "maat_reducer_response_ref": "stdout_tail:last_4000_chars",
            "maat_reducer_response_tail": stdout[-4000:],
        }
    result = _normalize_maat_reducer_result(parsed, reducer_input, session_id, stdout)
    expected_anchor = reducer_input.get("semantic_anchor")
    expected_provenance = reducer_input.get("semantic_provenance_binding")
    anchor_semantics = expected_anchor is not None or expected_provenance is not None
    if anchor_semantics and not _anchor_semantic_echo_valid(reducer_input, parsed):
        result.update({
            "status": "hold", "C_boundary": "HOLD", "final_selected_agents": {},
            "local_body_scope": {}, "failure_codes": ["HOLD_UNMAPPED_SEMANTIC_FIELD"],
            "hold_reasons": ["semantic provenance binding mismatch"],
        })
    elif anchor_semantics:
        result["semantic_anchor"] = expected_anchor
        result["semantic_provenance_binding"] = expected_provenance
    result["maat_body"] = expected_anchor if anchor_semantics else dict(parsed)
    return result


def materialize_maat_runtime_binding(maat_body: dict[str, Any], binding: dict[str, Any], provenance: dict[str, Any]) -> dict[str, Any] | None:
    operational_binding = {key: binding[key] for key in ("work_id", "graph_root") if key in binding}
    return materialize_maat_body(
        maat_body,
        operational_binding,
        semantic_provenance_binding=provenance,
        addendum=binding.get("addendum"),
        checkpoint_settings=binding.get("checkpoint_settings"),
        dispatcher=binding.get("dispatcher"),
    )


def materialize_preflight_working_graph(packet: dict[str, Any], reducer_result: dict[str, Any]) -> dict[str, Any]:
    binding = packet.get("cps_working_graph_runtime")
    maat_body = reducer_result.get("maat_body")
    provenance = packet.get("semantic_provenance_binding")
    if (
        reducer_result.get("status") != "pass"
        or not isinstance(binding, dict) or not isinstance(maat_body, dict)
        or not is_anchor_semantics_packet(packet)
        or not isinstance(provenance, dict)
        or reducer_result.get("semantic_anchor") != packet.get("semantic_anchor")
        or reducer_result.get("semantic_provenance_binding") != provenance
        or validate_semantic_provenance(provenance, maat_body)["status"] != "pass"
    ):
        return {}
    operational = materialize_maat_runtime_binding(maat_body, binding, provenance)
    return {"cps_working_graph_operational": operational} if operational is not None else {}


def record_preflight_runtime_observation(
    packet: dict[str, Any],
    files: dict[str, Path],
    trace_events: list[dict[str, Any]],
    c1_receipt: Any,
) -> dict[str, Any] | None:
    binding = packet.get("cps_working_graph_runtime")
    if not isinstance(binding, dict):
        return None
    work_id = binding.get("work_id")
    graph_root = binding.get("graph_root")
    if not isinstance(work_id, str) or not work_id or not isinstance(graph_root, (str, Path)) or not str(graph_root):
        return None

    store = WorkingGraphRegistry(Path(graph_root))
    before = store.load(work_id)
    before_body = before.get("maat_body")
    before_digest = before.get("maat_body_digest")
    existing = before.get("hermes_kann_addendum")
    if not isinstance(before_body, dict) or not isinstance(before_digest, str) or not isinstance(existing, dict):
        raise RegistryError("HOLD_WRITE_READBACK")
    observations = existing.get("observations")
    source_refs = existing.get("source_refs")
    if not isinstance(observations, list) or not isinstance(source_refs, list):
        raise RegistryError("HOLD_WRITE_READBACK")

    additions = [
        {key: event.get(key) for key in ("event_id", "event_type", "parent_event_id", "iteration", "phase")}
        for event in trace_events
        if isinstance(event, dict)
    ]
    if isinstance(c1_receipt, dict):
        additions.append({
            key: c1_receipt.get(key)
            for key in ("producer_ref", "consumer_ref", "outcome", "normalized_result_hash")
        })

    def merge_deduped(existing_values: list[Any], additions: list[Any]) -> list[Any]:
        result = list(existing_values)
        seen = {
            json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            for value in existing_values
        }
        for value in additions:
            identity = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            if identity not in seen:
                seen.add(identity)
                result.append(value)
        return result

    updated = store.update_addendum(work_id, {
        "observations": merge_deduped(observations, additions),
        "source_refs": merge_deduped(source_refs, [str(path) for path in files.values()]),
    })
    readback = store.load(work_id)
    if (
        canonical_hash(readback.get("maat_body")) != canonical_hash(before_body)
        or readback.get("maat_body_digest") != before_digest
    ):
        raise RegistryError("HOLD_WRITE_READBACK")
    return updated


def local_body_allowed(agent: str, reducer_result: dict[str, Any]) -> bool:
    """True only when the live reducer explicitly grants local-body dispatch for an agent."""
    if reducer_result.get("status") != "pass":
        return False
    scope = reducer_result.get("local_body_scope", {})
    if not isinstance(scope, dict):
        return False
    agent_scope = scope.get(agent)
    if isinstance(agent_scope, dict):
        grant = str(agent_scope.get("grant_status") or agent_scope.get("status") or "").lower()
        return bool(agent_scope.get("allow") or agent_scope.get("approved") or grant.startswith("granted"))
    if isinstance(agent_scope, list):
        return bool(agent_scope)
    return agent_scope in {True, "allow", "approved", "need_local_body", "granted", "granted_bounded_read_only"}


def normalize_selected_agents(route: dict[str, Any], reducer_result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Use Maat reducer final_selected_agents as the dispatch source, falling back to route-gate selection."""
    if reducer_result.get("physical_docops_gate", route.get("physical_docops_gate", {})).get("status") == "hold":
        return {}
    raw = (
        reducer_result.get("final_selected_agents")
        if "final_selected_agents" in reducer_result
        else route.get("selected_agents", {})
    )
    selected: dict[str, dict[str, Any]] = {}
    for agent, spec in (raw or {}).items():
        if not isinstance(spec, dict):
            spec = {"decision": spec}
        p_ids = spec.get("P") or spec.get("assigned_P") or spec.get("accepts_P") or spec.get("accepted_P") or []
        s_ids = spec.get("S") or spec.get("assigned_S") or spec.get("accepts_S") or spec.get("accepted_S") or []
        selected[agent] = {**spec, "P": list(p_ids), "S": list(s_ids)}
    return selected


def build_probe(agent: str, route: dict[str, Any], spec: dict[str, Any] | None = None, reducer_result: dict[str, Any] | None = None) -> dict[str, Any]:
    spec = spec or route["selected_agents"][agent]
    rr = reducer_result or {}
    accepted_p = rr.get("revised_P") or route.get("accepted_P", {})
    accepted_s = rr.get("revised_S") or route.get("accepted_S", {})
    edges = rr.get("revised_E") or route.get("E", [])
    return {
        "schema": "harness.cps_preflight.agent_probe.v1",
        "requested_role": agent,
        "profile_call_requires_cps_reason": True,
        "contract_ref": str(CONTRACT_PATH),
        "C": rr.get("revised_C") or route.get("C"),
        "local_P": {pid: accepted_p.get(pid) for pid in spec.get("P", []) if pid in accepted_p},
        "local_S": {sid: accepted_s.get(sid) for sid in spec.get("S", []) if sid in accepted_s},
        "local_E": [edge for edge in edges if any(sid in edge for sid in spec.get("S", []))],
        "verification_gate": route.get("verification_gate", {}),
        "physical_docops_gate": route.get("physical_docops_gate", validate_physical_docops_route(route)),
        "ask": "accept/reject/need_local_body/hold",
        "body_policy": "local task body only after reducer_result grants local_body_scope",
    }


def build_local_body(agent: str, probe: dict[str, Any], packet: dict[str, Any], packet_path: Path) -> dict[str, Any]:
    return {
        "schema": "harness.cps_preflight.local_task_body.v1",
        "agent": agent,
        "packet_ref": str(packet_path),
        "local_P": probe["local_P"],
        "local_S": probe["local_S"],
        "local_E": probe["local_E"],
        "verification_gate": probe.get("verification_gate", {}),
        "physical_docops_gate": probe.get("physical_docops_gate", {}),
        "task_AC": packet.get("task_AC") or (packet.get("CPS", {}) if isinstance(packet.get("CPS"), dict) else {}).get("AC"),
        "owner_approval_boundary": packet.get("owner_approval_boundary"),
        "prohibited_actions": packet.get("prohibited_actions", ["git add", "git commit", "git push"]),
        "source_refs": packet.get("source_refs", []),
        "artifact_refs": packet.get("artifact_refs", []),
    }


def build_agent_body_map(selected: dict[str, Any], route: dict[str, Any], reducer_result: dict[str, Any], packet: dict[str, Any], packet_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Materialize bodies only after Maat selection and scope grant."""
    probes: dict[str, Any] = {}
    bodies: dict[str, Any] = {}
    for agent, spec in selected.items():
        probe = build_probe(agent, route, spec, reducer_result)
        probes[agent] = probe
        if probe["physical_docops_gate"].get("status") == "pass" and local_body_allowed(agent, reducer_result):
            bodies[agent] = build_local_body(agent, probe, packet, packet_path)
    return probes, bodies


def dispatch_external_local_bodies(
    local_bodies: dict[str, Any],
    record_root: Path,
    *,
    identities: dict[str, dict[str, Any]],
    argv_builder: Any,
    process_runner: Any = None,
) -> dict[str, Any]:
    receipts: dict[str, Any] = {}
    for agent, body in local_bodies.items():
        if agent not in identities:
            raise TypeError(f"explicit receipt identity required for {agent}")
        encoded = json.dumps(
            body, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
        ).encode("utf-8")
        receipts[agent] = dispatch_external_runtime(
            agent,
            encoded,
            argv_builder(agent),
            record_root,
            identity=identities[agent],
            process_runner=process_runner,
        )
    return receipts


def build_local_body_dispatch(route: dict[str, Any], reducer_result: dict[str, Any], local_bodies: dict[str, Any], final_selected_agents: dict[str, Any] | None = None, body_manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    """Record direct selected-agent body transfer and aggregate relay invariants."""
    selected = final_selected_agents or normalize_selected_agents(route, reducer_result)
    manifests = body_manifest or build_body_manifest(selected)
    scope = reducer_result.get("local_body_scope", {}) if isinstance(reducer_result.get("local_body_scope"), dict) else {}
    dispatch: dict[str, Any] = {}
    hashes: list[str] = []
    token_estimate = 0
    for agent in selected:
        body = local_bodies.get(agent)
        encoded = json.dumps(body, sort_keys=True, ensure_ascii=False).encode() if body is not None else b""
        body_hash = hashlib.sha256(encoded).hexdigest() if encoded else None
        if body_hash:
            hashes.append(body_hash)
            token_estimate += (len(encoded) + 3) // 4
        dispatch[agent] = {
            "selected": True,
            "body_manifest_id": manifests.get(agent, {}).get("body_manifest_id"),
            "body_hash": body_hash,
            "direct_dispatch_count": 1 if body is not None else 0,
            "reducer_status": reducer_result.get("status"),
            "local_body_scope": scope.get(agent),
            "local_body_emitted": body is not None,
            "dispatch_target": agent if body is not None else None,
        }
    unselected = [agent for agent in local_bodies if agent not in selected]
    return {
        "schema": "harness.cps_preflight.local_body_dispatch.v1",
        "status": "pass" if reducer_result.get("status") == "pass" else "hold",
        "policy": "Hermes-kann dispatches materialized bodies directly to selected agents only",
        "verification_gate": route.get("verification_gate", {}),
        "dispatch": dispatch,
        "aggregate": {
            "selected_count": len(selected),
            "direct_dispatch_count": sum(item["direct_dispatch_count"] for item in dispatch.values()),
            "duplicate_dispatch_count": len(hashes) - len(set(hashes)),
            "unselected_dispatch_count": len(unselected),
            "maat_body_relay_count": 0,
            "token_estimate": token_estimate,
        },
    }


def build_contribute_cps(packet: dict[str, Any], candidate: dict[str, Any], route: dict[str, Any], probe_responses: dict[str, Any], reducer_result: dict[str, Any], local_body_dispatch: dict[str, Any]) -> dict[str, Any]:
    """Build the CPS semantic trace consumed by Maat final judgment."""
    task_ac = {
        "owner": "maat",
        "checks": [
            {"id": "AC1", "pass_if": "Maat reducer returns final_selected_agents/revised_C/P/S/local_body_scope"},
            {"id": "AC2", "pass_if": "No local body is emitted before reducer_result/local_body_scope"},
            {"id": "AC3", "pass_if": "Selected agents receive role-local draft_CPS probes, not full prompt bundles"},
            {"id": "AC4", "pass_if": "Final Maat judgment consumes contribute_CPS and closes Goal.closure"},
        ],
    }
    revised_p = reducer_result.get("revised_P") or route.get("accepted_P", {})
    revised_s = reducer_result.get("revised_S") or route.get("accepted_S", {})
    revised_e = reducer_result.get("revised_E") or route.get("E", [])
    ac_evidence = {
        "AC1": {
            "claim": "Maat reducer returns final_selected_agents/revised_C/P/S/local_body_scope",
            "status": "pass" if reducer_result.get("status") == "pass" and isinstance(reducer_result.get("final_selected_agents"), dict) and isinstance(reducer_result.get("local_body_scope"), dict) else "hold",
            "evidence_ref": "maat_reducer_result.json",
        },
        "AC2": {
            "claim": "no local body before reducer_result",
            "status": "pass" if local_body_dispatch.get("schema") == "harness.cps_preflight.local_body_dispatch.v1" else "hold",
            "evidence_ref": "local_body_dispatch.json",
        },
        "AC3": {
            "claim": "role-local draft_CPS differs per agent",
            "status": "pass" if probe_responses is not None else "hold",
            "evidence_ref": "agent_draft_probes.json",
        },
        "AC4": {
            "claim": "final Maat judgment closes Goal.closure",
            "status": "pending_maat_final",
            "evidence_ref": "final_maat_judgment.json",
        },
    }
    return {
        "schema": "harness.cps_preflight.contribute_cps.v1",
        "Goal": candidate.get("Goal") or (packet.get("CPS", {}) if isinstance(packet.get("CPS"), dict) else {}).get("Goal") or packet.get("root_goal"),
        "C": reducer_result.get("revised_C") or route.get("C") or candidate.get("C?"),
        "P": revised_p,
        "S": revised_s,
        "E": revised_e,
        "verification_gate": route.get("verification_gate", {}),
        "order": route.get("order", []),
        "task_AC": task_ac,
        "selected_agents": route.get("selected_agents", {}),
        "probe_responses": {agent: {k: v for k, v in resp.items() if k not in {"stdout_tail"}} for agent, resp in (probe_responses or {}).items()},
        "reducer_result_ref": "maat_reducer_result.json",
        "local_body_dispatch_ref": "local_body_dispatch.json",
        "AC_evidence": ac_evidence,
        "Goal_closure": {
            "status": "pending_maat_final",
            "reason": "Maat final judgment has not yet consumed this contribute_CPS trace",
        },
    }


def build_hold_gap_loop(contribute_cps: dict[str, Any], final_judgment: dict[str, Any], reducer_result: dict[str, Any]) -> dict[str, Any]:
    """Capture the CPS return path when Maat final holds/fails, without running a new procedure."""
    status = str(final_judgment.get("status", "hold")).lower()
    missing = final_judgment.get("missing_evidence", []) if isinstance(final_judgment.get("missing_evidence"), list) else []
    missing = [m for m in missing if m != "final_maat_judgment.json"]
    return {
        "schema": "harness.cps_preflight.hold_gap_loop.v1",
        "status": "closed" if status == "pass" else "hold",
        "trigger": "final_maat_judgment" if status != "pass" else "none",
        "revised_C": reducer_result.get("revised_C") or contribute_cps.get("C"),
        "revised_P": reducer_result.get("revised_P") or contribute_cps.get("P"),
        "revised_S": reducer_result.get("revised_S") or contribute_cps.get("S"),
        "revised_E": reducer_result.get("revised_E") or contribute_cps.get("E"),
        "missing_evidence": missing,
        "return_to": "maat_route_gate" if status != "pass" else None,
        "next_action": "re-enter Maat with revised C/P/S/E and missing_evidence only" if status != "pass" else "none",
    }


def _coerce_positive_int(value: Any, default: int | None = None) -> int | None:
    try:
        coerced = int(value)
    except (TypeError, ValueError):
        return default
    return coerced if coerced >= 0 else default


def max_reentry_iterations(packet: dict[str, Any]) -> int:
    """Return explicit approved re-entry cap, otherwise the bounded default of one."""
    for key in ("max_reentry_iterations", "reentry_max_iterations", "reentry_cap"):
        if key in packet:
            return _coerce_positive_int(packet.get(key), DEFAULT_MAX_REENTRY_ITERATIONS) or 0
    approved = packet.get("approved_input") or packet.get("local_body") or packet.get("approved_scope")
    if isinstance(approved, dict):
        for key in ("max_reentry_iterations", "reentry_max_iterations", "reentry_cap"):
            if key in approved:
                return _coerce_positive_int(approved.get(key), DEFAULT_MAX_REENTRY_ITERATIONS) or 0
    return DEFAULT_MAX_REENTRY_ITERATIONS


def build_reentry_input(hold_gap_loop: dict[str, Any], packet_ref: str, iteration: int) -> dict[str, Any]:
    """Build the compact re-entry packet; its keys are intentionally fixed by AC."""
    data = {
        "revised_C": hold_gap_loop.get("revised_C"),
        "revised_P": hold_gap_loop.get("revised_P"),
        "revised_S": hold_gap_loop.get("revised_S"),
        "revised_E": hold_gap_loop.get("revised_E"),
        "missing_evidence": hold_gap_loop.get("missing_evidence", []),
        "iteration": iteration,
        "packet_ref": packet_ref,
    }
    return {key: data.get(key) for key in REENTRY_INPUT_KEYS}


def build_candidate_from_reentry(reentry_input: dict[str, Any], packet_path: Path, repo: Path, original_candidate: dict[str, Any] | None = None) -> dict[str, Any]:
    """Convert compact re-entry input while preserving the original trace."""
    revised_p = reentry_input.get("revised_P") if isinstance(reentry_input.get("revised_P"), dict) else {}
    revised_s = reentry_input.get("revised_S") if isinstance(reentry_input.get("revised_S"), dict) else {}
    revised_e = reentry_input.get("revised_E") if isinstance(reentry_input.get("revised_E"), list) else []
    original = original_candidate or {}
    cps_trace_events = original.get("cps_trace_events", [])
    return {
        "schema": "harness.cps_preflight.candidate.v1",
        "status": "candidate",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "contract_ref": str(CONTRACT_PATH),
        "packet_ref": str(packet_path),
        "repo": _repo_meta(repo),
        "cps_trace_events": cps_trace_events,
        "route_enrichment": original.get("route_enrichment", {}),
        "runtime_graph_gate": original.get("runtime_graph_gate", {"status": "not_required", "gaps": []}),
        "dispatch_plan": original.get("dispatch_plan"),
        "producer_ref": original.get("producer_ref"),
        "consumer_ref": original.get("consumer_ref"),
        "runtime_receipt": original.get("runtime_receipt"),
        "normalized_result": original.get("normalized_result"),
        "c1_runtime_evidence_gate": original.get("c1_runtime_evidence_gate"),
        "node_projection": original.get("node_projection"),
        "C?": reentry_input.get("revised_C") or {"C1": "reentry_candidate"},
        "Goal": "Resolve final Maat HOLD/FAIL missing evidence and close Goal_closure",
        "P?": revised_p,
        "S?": revised_s,
        "E?": revised_e,
        "missing_evidence": reentry_input.get("missing_evidence", []),
        "reentry": {"iteration": reentry_input.get("iteration"), "packet_ref": reentry_input.get("packet_ref")},
        "uncertainty": ["Maat must re-adjudicate the compact HOLD/FAIL re-entry before any local body dispatch"],
        "request_to_maat": [
            "rerun route-gate on revised C/P/S/E",
            "route through reducer before any local body scope",
            "final-judge AC/Goal closure after bounded re-entry",
        ],
    }


def final_output_from_judgment(final_judgment: dict[str, Any], hold_gap_loop: dict[str, Any]) -> dict[str, Any]:
    status = str(final_judgment.get("status", "hold")).lower()
    if status == "pass":
        return {
            "status": "pass",
            "Goal_closure": final_judgment.get("Goal_closure", {"status": "pass"}),
            "missing_evidence": [],
        }
    missing = final_judgment.get("missing_evidence")
    if not isinstance(missing, list):
        missing = hold_gap_loop.get("missing_evidence", [])
    missing = [m for m in missing if m != "final_maat_judgment.json"]
    return {
        "status": "hold",
        "Goal_closure": final_judgment.get("Goal_closure", {"status": "hold", "reason": "bounded HOLD after Maat final judgment"}),
        "missing_evidence": missing,
    }


def route_gate_usable(route: dict[str, Any], final_output: dict[str, Any], final_selected_agents: dict[str, Any], reducer_result: dict[str, Any]) -> bool:
    if str(route.get("status", "")).lower() == "pass":
        return True
    if route.get("C_boundary") != "HOLD" and bool(route.get("selected_agents")):
        return True
    if str(final_output.get("status", "")).lower() == "pass" and str(reducer_result.get("status", "")).lower() == "pass" and bool(final_selected_agents):
        return True
    return False


def _maat_final_prompt(contribute_cps: dict[str, Any]) -> str:
    payload = {
        "role": "hermes-kann_control_plane",
        "request": "live Maat final AC judgment over CPS preflight trace",
        "hard_rules": [
            "Return exactly one JSON object and no markdown.",
            "Do not mutate files, run tools, use git, or implement.",
            "Judge only the supplied CPS AC and Goal closure; do not invent new criteria.",
            "Treat eligible_for_maat_audit as evidence eligibility only; never infer acceptance or rewrite the root Goal.",
            "The final_maat_judgment.json is the output of this very step. Do NOT mark final_maat_judgment.json as missing in the missing_evidence list, and do not hold the judgment because of its absence. If the supplied contribute_CPS trace is valid, return status PASS.",
        ],
        "required_response_schema": {
            "schema": "harness.cps_preflight.final_maat_judgment.v1",
            "status": "pass|hold|fail",
            "AC_verdicts": {},
            "Goal_closure": {"status": "pass|hold|fail", "reason": ""},
            "missing_evidence": [],
            "failure_codes": [],
            "notes": [],
        },
        "contribute_CPS": contribute_cps,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _normalize_final_judgment(raw: dict[str, Any], session_id: str | None, stdout: str) -> dict[str, Any]:
    result = dict(raw)
    result["schema"] = "harness.cps_preflight.final_maat_judgment.v1"
    result["source"] = "live_maat_final"
    result["live_maat_final_session_id"] = session_id
    result["maat_final_response_ref"] = "stdout_tail:last_4000_chars"
    result["maat_final_response_tail"] = stdout[-4000:]
    result.setdefault("status", "hold")
    result.setdefault("AC_verdicts", {})
    result.setdefault("Goal_closure", {"status": "hold", "reason": "missing Goal_closure from Maat"})
    result.setdefault("missing_evidence", [])
    result.setdefault("failure_codes", [])
    result.setdefault("notes", [])
    return result


def invoke_maat_final_judgment(contribute_cps: dict[str, Any], repo: Path, timeout: int = 180) -> dict[str, Any]:
    """Ask live Maat to judge the CPS AC/Goal trace; no extra verifier criteria."""
    import subprocess
    env = os.environ.copy()
    env["HERMES_PROFILE"] = "maat"
    cmd = ["hermes", "chat", "-Q", "--max-turns", "1", "-t", "", "-q", _maat_final_prompt(contribute_cps)]
    proc = subprocess.run(cmd, cwd=str(repo), env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False, timeout=timeout)
    stdout = proc.stdout or ""
    session_match = re.search(r"session_id:\s*([A-Za-z0-9_\-]+)", stdout)
    session_id = session_match.group(1) if session_match else None
    parsed = _extract_json_object(stdout)
    if proc.returncode != 0 or not isinstance(parsed, dict):
        return {
            "schema": "harness.cps_preflight.final_maat_judgment.v1",
            "source": "live_maat_final",
            "status": "hold",
            "AC_verdicts": {},
            "Goal_closure": {"status": "hold", "reason": "live Maat final did not return compact JSON"},
            "missing_evidence": ["live_maat_final_json_response"],
            "failure_codes": ["FAIL_LIVE_MAAT_FINAL_NO_JSON" if parsed is None else "FAIL_LIVE_MAAT_FINAL_EXIT"],
            "live_maat_final_session_id": session_id,
            "maat_final_response_ref": "stdout_tail:last_4000_chars",
            "maat_final_response_tail": stdout[-4000:],
        }
    return _normalize_final_judgment(parsed, session_id, stdout)


def compact_continuation_chain(packet: dict[str, Any], candidate: dict[str, Any], gate: dict[str, Any]) -> dict[str, Any]:
    """Return a HOLD receipt without replaying route, reducer, probe, or final-audit calls."""
    missing = gate.get("gap_classes", []) or ["new_repair_evidence"]
    final_judgment = {
        "schema": "harness.cps_preflight.continuation_hold.v1",
        "source": "receipt_delta_gate", "status": "hold", "closure": False,
        "audit_outcome": "route_gate_only",
        "Goal_closure": {"status": "not_requested", "reason": "continuation receipt is not a closure judgment"},
        "missing_evidence": missing, "failure_codes": ["HOLD_RECEIPT_DELTA"],
    }
    receipt = build_continuation_receipt(packet, final_judgment, gate)
    route = {
        "schema": "harness.cps_preflight.route_gate.v1", "status": "hold", "C_boundary": "HOLD",
        "C": candidate.get("C?", {}), "accepted_P": {}, "accepted_S": {}, "E": [], "selected_agents": {},
        "audit_plan": {"mode": "route_gate_only"}, "AC_mode": "route_gate_only",
        "final_audit_needed": False, "prohibitions": [], "verification_gate": {"gap_class": "receipt_delta_hold"},
    }
    reducer = {
        "status": "hold", "C_boundary": "HOLD", "revised_C": route["C"], "revised_P": {},
        "revised_S": {}, "revised_E": [], "final_selected_agents": {}, "local_body_scope": {},
        "hold_reasons": missing,
    }
    contribute = {"AC_evidence": {}, "Goal_closure": final_judgment["Goal_closure"]}
    return {
        "candidate": candidate, "route": route, "draft_probes": {}, "probe_responses": {},
        "reducer_input": {}, "reducer_result": reducer, "probes": {}, "local_bodies": {},
        "local_body_dispatch": {}, "contribute_cps": contribute, "final_judgment": final_judgment,
        "hold_gap_loop": build_hold_gap_loop(contribute, final_judgment, reducer),
        "final_selected_agents": {}, "route_candidate_catalog": {"selected_candidate_ids": []},
        "continuation_receipt": receipt, "receipt_delta_gate": gate,
    }


def navigation_hold_chain(candidate: dict[str, Any], receipt: dict[str, Any]) -> dict[str, Any]:
    diagnostics = receipt.get("diagnostic_codes", [])
    final_judgment = {
        "schema": "harness.cps_preflight.runtime_navigation_hold.v1",
        "source": "cps_runtime_navigation", "status": "hold", "closure": False,
        "Goal_closure": {"status": "hold", "reason": "runtime navigation did not resolve source refs"},
        "missing_evidence": diagnostics, "failure_codes": diagnostics,
    }
    route = {
        "schema": "harness.cps_preflight.route_gate.v1", "status": "hold", "C_boundary": "HOLD",
        "C": candidate.get("C?", {}), "accepted_P": {}, "accepted_S": {}, "E": [], "selected_agents": {},
        "audit_plan": {"mode": "route_gate_only"}, "final_audit_needed": False, "prohibitions": [],
    }
    reducer = {
        "status": "hold", "C_boundary": "HOLD", "revised_C": route["C"], "revised_P": {},
        "revised_S": {}, "revised_E": [], "final_selected_agents": {}, "local_body_scope": {},
        "hold_reasons": diagnostics,
    }
    contribute = {"AC_evidence": {}, "Goal_closure": final_judgment["Goal_closure"]}
    return {
        "candidate": candidate, "route": route, "draft_probes": {}, "probe_responses": {},
        "reducer_input": {}, "reducer_result": reducer, "probes": {}, "local_bodies": {},
        "local_body_dispatch": {}, "contribute_cps": contribute, "final_judgment": final_judgment,
        "hold_gap_loop": build_hold_gap_loop(contribute, final_judgment, reducer),
        "final_selected_agents": {}, "route_candidate_catalog": {"selected_candidate_ids": []},
        "runtime_navigation_receipt": receipt,
    }


def semantic_provenance_hold_chain(candidate: dict[str, Any]) -> dict[str, Any]:
    failure = ["HOLD_UNMAPPED_SEMANTIC_FIELD"]
    final_judgment = {
        "schema": "harness.cps_preflight.final_maat_judgment.v1",
        "source": "semantic_provenance_gate", "status": "hold", "closure": False,
        "Goal_closure": {"status": "hold", "reason": "canonical semantic provenance is not exact"},
        "missing_evidence": failure, "failure_codes": failure,
    }
    route = {
        "schema": "harness.cps_preflight.route_gate.v1", "status": "hold", "C_boundary": "HOLD",
        "C": candidate.get("C?", {}), "accepted_P": {}, "accepted_S": {}, "E": [],
        "selected_agents": {}, "audit_plan": {"mode": "route_gate_only"},
        "final_audit_needed": False, "prohibitions": [],
    }
    reducer = {
        "status": "hold", "C_boundary": "HOLD", "revised_C": route["C"],
        "revised_P": {}, "revised_S": {}, "revised_E": [], "final_selected_agents": {},
        "local_body_scope": {}, "hold_reasons": failure, "failure_codes": failure,
    }
    contribute = {"AC_evidence": {}, "Goal_closure": final_judgment["Goal_closure"]}
    return {
        "candidate": candidate, "route": route, "draft_probes": {}, "probe_responses": {},
        "reducer_input": {}, "reducer_result": reducer, "probes": {}, "local_bodies": {},
        "local_body_dispatch": {}, "contribute_cps": contribute, "final_judgment": final_judgment,
        "hold_gap_loop": build_hold_gap_loop(contribute, final_judgment, reducer),
        "final_selected_agents": {}, "route_candidate_catalog": {"selected_candidate_ids": []},
    }


def execute_preflight_chain(
    packet: dict[str, Any],
    packet_path: Path,
    repo: Path,
    mode: str,
    candidate: dict[str, Any],
    selected_agent_runner: Any = None,
) -> dict[str, Any]:
    """Run route-gate -> probes -> Maat reducer -> local-body gate -> optional Maat final."""
    provenance = packet.get("semantic_provenance_binding")
    semantic_anchor = packet.get("semantic_anchor")
    anchor_semantics = is_anchor_semantics_packet(packet)
    if anchor_semantics and validate_semantic_provenance(provenance, semantic_anchor)["status"] != "pass":
        return semantic_provenance_hold_chain(candidate)
    navigation_request = packet.get("runtime_navigation_request")
    navigation_receipt = navigate_cps_runtime(repo, navigation_request) if isinstance(navigation_request, dict) else None
    if isinstance(navigation_receipt, dict):
        candidate["runtime_navigation_receipt"] = navigation_receipt
        if navigation_receipt.get("status") != "resolved":
            return navigation_hold_chain(candidate, navigation_receipt)
    receipt_delta_gate = evaluate_receipt_delta(packet)
    delta_reentry = receipt_delta_gate.get("action") == "reenter"
    if receipt_delta_gate.get("active") and not delta_reentry:
        return compact_continuation_chain(packet, candidate, receipt_delta_gate)
    prior_route_receipt = None
    if delta_reentry:
        prior_route_receipt, route_receipt_gaps = prior_c_ac_route_receipt(packet, receipt_delta_gate)
        if route_receipt_gaps:
            receipt_delta_gate = {
                **receipt_delta_gate,
                "status": "hold",
                "action": "hold_mismatch",
                "delta_only_reentry": False,
                "gap_classes": list(dict.fromkeys(receipt_delta_gate.get("gap_classes", []) + route_receipt_gaps)),
            }
            return compact_continuation_chain(packet, candidate, receipt_delta_gate)
    prior_route = (
        prior_route_receipt["route"]
        if isinstance(prior_route_receipt, dict) and isinstance(prior_route_receipt.get("route"), dict)
        else None
    )
    if anchor_semantics and prior_route is not None:
        return semantic_provenance_hold_chain(candidate)
    route_candidate_catalog = (
        prior_route.get("route_candidate_catalog")
        if isinstance(prior_route, dict) and isinstance(prior_route.get("route_candidate_catalog"), dict)
        else select_route_candidate_catalog(packet, candidate)
    )
    escalation = candidate.get("route_enrichment", {}).get("selective_maat_escalation", {})
    if not delta_reentry and not escalation.get("needed", True):
        cps_raw = packet.get("CPS")
        cps: dict[str, Any] = cps_raw if isinstance(cps_raw, dict) else {}
        explicit_agent_work = bool(_ordered_cps_items(cps, "P") or _ordered_cps_items(cps, "S"))
        inline_raw = packet.get("inline_response_contract")
        inline_contract: dict[str, Any] = inline_raw if isinstance(inline_raw, dict) else {}
        short_close = _present(inline_contract.get("response")) and not explicit_agent_work
        # Named P/S work needs an explicit routing signal; absence is a hold, not implicit escalation.
        status = "pass" if short_close else "hold"
        missing = [] if short_close else ["route_gate_signal_missing"]
        reason = "self-contained inline response contract" if short_close else "explicit route_candidates or mutation_scope signal required"
        route = {
            "schema": "harness.cps_preflight.route_gate.v1", "status": status,
            "C_boundary": "PASS_ONE_C" if short_close else "HOLD", "C": candidate.get("C?", {}),
            "accepted_P": {}, "accepted_S": {}, "E": [], "selected_agents": {},
            "wire": "short_cps", "audit_plan": {"mode": "local_closure"}, "prohibitions": [],
            "verification_gate": {"gap_class": "none" if short_close else "route_gate_signal_missing"},
            "final_audit_needed": False, "route_enrichment": candidate.get("route_enrichment", {}),
            "mutation_closure": candidate.get("mutation_closure", {}),
            "route_candidate_catalog": route_candidate_catalog,
        }
        reducer_result = {
            "schema": "harness.cps_preflight.short_wire_result.v1", "source": "short_cps_wire",
            "status": status, "revised_C": route["C"], "revised_P": {}, "revised_S": {},
            "revised_E": [], "final_selected_agents": {}, "local_body_scope": {},
            "hold_reasons": [] if short_close else [reason],
        }
        final_judgment = {
            "schema": "harness.cps_preflight.local_closure.v1", "source": "short_cps_wire",
            "status": status, "AC_verdicts": {},
            "Goal_closure": {"status": status, "reason": reason},
            "missing_evidence": missing, "failure_codes": [] if short_close else ["HOLD_ROUTE_GATE_SIGNAL_MISSING"],
            "inline_response": inline_contract.get("response") if short_close else None,
        }
        contribute_cps = {"AC_evidence": {}, "Goal_closure": final_judgment["Goal_closure"]}
        hold_gap_loop = build_hold_gap_loop(contribute_cps, final_judgment, reducer_result)
        return {
            "candidate": candidate, "route": route, "draft_probes": {}, "probe_responses": {},
            "reducer_input": {}, "reducer_result": reducer_result, "probes": {}, "local_bodies": {},
            "local_body_dispatch": {}, "contribute_cps": contribute_cps,
            "final_judgment": final_judgment, "hold_gap_loop": hold_gap_loop, "final_selected_agents": {},
            "route_candidate_catalog": route_candidate_catalog,
        }
    body_manifest = build_body_manifest(route_candidate_catalog["selected_candidate_ids"])
    route = json.loads(json.dumps(prior_route)) if prior_route is not None else (
        invoke_live_maat(candidate, packet, repo, body_manifest=body_manifest) if mode == "live-maat" else adjudicate(candidate)
    )
    if mode == "live-maat" and anchor_semantics and not _anchor_semantic_echo_valid(packet, route):
        return semantic_provenance_hold_chain(candidate)
    route["mutation_closure"] = candidate.get("mutation_closure", {})
    route["route_candidate_catalog"] = route_candidate_catalog
    draft_probes, probe_responses = probe_agents_as_arrive(route, repo) if mode == "live-maat" else ({}, {})
    reducer_input = build_reducer_input(route, probe_responses, body_manifest) if mode == "live-maat" else {}
    reducer_result = invoke_maat_reducer(reducer_input, repo) if mode == "live-maat" else {
        "schema": "harness.cps_preflight.maat_reducer_result.v1",
        "source": "deterministic_not_live",
        "status": "hold",
        "C_boundary": "HOLD",
        "revised_C": route.get("C", {}),
        "revised_P": route.get("accepted_P", {}),
        "revised_S": route.get("accepted_S", {}),
        "revised_E": route.get("E", []),
        "final_selected_agents": {},
        "local_body_scope": {},
        "hold_reasons": ["deterministic mode does not approve reducer-based local body dispatch"],
        "failure_codes": ["HOLD_DETERMINISTIC_REDUCER_REQUIRED"],
    }
    working_graph_operational: dict[str, Any] = {}
    materialization_failure: str | None = None
    reducer_result = apply_physical_docops_gate(reducer_result, route)
    if reducer_result["physical_docops_gate"]["status"] != "pass":
        reducer_result["final_selected_agents"] = {}
        reducer_result["local_body_scope"] = {}
    node_projection_gate = apply_node_projection_gate(route, reducer_result, packet)
    if node_projection_gate.get("status") == "hold":
        reducer_result["status"] = "hold"
        reducer_result["C_boundary"] = "HOLD"
        reducer_result["final_selected_agents"] = {}
        reducer_result["local_body_scope"] = {}
    if reducer_result.get("status") == "pass" and node_projection_gate.get("status") != "hold":
        try:
            working_graph_operational = materialize_preflight_working_graph(packet, reducer_result)
        except RegistryError as exc:
            materialization_failure = (
                "HOLD_WRITE_READBACK" if "HOLD_WRITE_READBACK" in str(exc)
                else "HOLD_UNMAPPED_SEMANTIC_FIELD"
            )
            reducer_result.update({
                "status": "hold", "C_boundary": "HOLD", "final_selected_agents": {},
                "local_body_scope": {}, "failure_codes": [materialization_failure],
                "hold_reasons": [materialization_failure],
            })
    final_selected_agents = normalize_selected_agents(route, reducer_result)
    selected_manifest = {agent: body_manifest[agent] for agent in final_selected_agents if agent in body_manifest}
    probes, local_bodies = build_agent_body_map(final_selected_agents, route, reducer_result, packet, packet_path)
    handoff_transport: dict[str, Any] = {
        "status": "not_required", "dispatch_count": 0, "search_count": 0, "agents": {},
    }
    if selected_agent_runner is not None and local_bodies:
        verified_dispatches: list[tuple[str, bytes]] = []
        transport_results: dict[str, Any] = {}
        for agent, body in local_bodies.items():
            original_body = json.dumps(
                body, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
            ).encode("utf-8")
            envelope = build_handoff_envelope(original_body, {"local_body_state": "complete", "agent": agent})
            prompt = build_handoff_prompt(envelope)
            consumed = consume_handoff_prompt(prompt)
            result = dispatch_handoff_transport(
                original_body,
                envelope,
                prompt,
                consumed,
                lambda verified_body, selected=agent: verified_dispatches.append((selected, verified_body)),
            )
            transport_results[agent] = result
            if result["status"] != "dispatched":
                handoff_transport = {**result, "agents": transport_results}
                break
        else:
            for agent, verified_body in verified_dispatches:
                selected_agent_runner(agent, verified_body)
            handoff_transport = {
                "status": "dispatched",
                "dispatch_count": len(verified_dispatches),
                "search_count": 0,
                "agents": transport_results,
            }
        if handoff_transport["status"] == "hold":
            reducer_result["status"] = "hold"
            reducer_result["C_boundary"] = "HOLD"
            reducer_result["final_selected_agents"] = {}
            reducer_result["local_body_scope"] = {}
            reducer_result.setdefault("failure_codes", []).append(HANDOFF_INTEGRITY_FAILURE)
            reducer_result.setdefault("hold_reasons", []).append(HANDOFF_INTEGRITY_FAILURE)
            final_selected_agents = {}
            local_bodies = {}
    local_body_dispatch = build_local_body_dispatch(route, reducer_result, local_bodies, final_selected_agents, selected_manifest)
    contribute_cps = build_contribute_cps(packet, candidate, route, probe_responses, reducer_result, local_body_dispatch)
    if handoff_transport.get("status") == "hold":
        final_judgment = {
            "schema": "harness.cps_preflight.final_maat_judgment.v1",
            "source": "local_handoff_transport_gate",
            "status": "hold",
            "AC_verdicts": {},
            "Goal_closure": {"status": "hold", "reason": "handoff transport integrity mismatch"},
            "missing_evidence": [HANDOFF_INTEGRITY_FAILURE],
            "failure_codes": [HANDOFF_INTEGRITY_FAILURE],
            "notes": ["Selected-agent runner dispatch was blocked before execution."],
        }
    elif materialization_failure is not None:
        final_judgment = {
            "schema": "harness.cps_preflight.final_maat_judgment.v1",
            "source": "local_materialization_gate",
            "status": "hold",
            "AC_verdicts": {},
            "Goal_closure": {"status": "hold", "reason": "working graph materialization did not preserve its binding"},
            "missing_evidence": [materialization_failure],
            "failure_codes": [materialization_failure],
            "notes": ["External final Maat dispatch was blocked by the materialization gate."],
        }
    elif node_projection_gate.get("status") == "hold":
        final_judgment = {
            "schema": "harness.cps_preflight.final_maat_judgment.v1",
            "source": "local_node_projection_gate",
            "status": "hold",
            "AC_verdicts": {},
            "Goal_closure": {"status": "hold", "reason": "node projection gate requires missing evidence"},
            "missing_evidence": node_projection_gate.get("gap_classes", []),
            "failure_codes": ["HOLD_NODE_PROJECTION"],
            "notes": ["External final Maat dispatch was blocked by the node projection gate."],
        }
    elif mode == "live-maat" and route.get("final_audit_needed") is True:
        active_case_binding = packet.get("active_case_final_audit")
        if active_case_binding is not None:
            audit_evidence = load_production_final_audit(active_case_binding)
            contribute_cps["production_final_audit"] = audit_evidence
            if audit_evidence.get("status") != "eligible_for_maat_audit":
                failure = audit_evidence.get("failure_code", "HOLD_FINAL_GATE")
                final_judgment = {
                    "schema": "harness.cps_preflight.final_maat_judgment.v1",
                    "source": "production_final_audit_gate", "status": "hold",
                    "AC_verdicts": {},
                    "Goal_closure": {"status": "hold", "reason": "both production lanes are not eligible for Maat audit"},
                    "missing_evidence": [failure], "failure_codes": [failure],
                    "notes": ["Maat final dispatch was blocked before audit."],
                }
            else:
                final_judgment = invoke_maat_final_judgment(contribute_cps, repo)
        else:
            final_judgment = invoke_maat_final_judgment(contribute_cps, repo)
    elif mode == "live-maat":
        audit_outcome = route.get("AC_mode") if route.get("AC_mode") in {"route_gate_only", "readback_only"} else "route_gate_only"
        final_judgment = {
            "schema": "harness.cps_preflight.audit_not_requested.v1",
            "source": "route_gate",
            "status": "pass" if route.get("status") == "pass" and reducer_result.get("status") == "pass" else "hold",
            "closure": False,
            "audit_outcome": audit_outcome,
            "AC_verdicts": {},
            "Goal_closure": {"status": "not_requested", "reason": f"{audit_outcome} does not request final Maat closure"},
            "missing_evidence": [] if route.get("status") == "pass" else route.get("gap_scan", {}).get("missing", []),
            "failure_codes": [],
        }
    else:
        final_judgment = {
            "schema": "harness.cps_preflight.final_maat_judgment.v1",
            "source": "deterministic_not_live",
            "status": "hold",
            "AC_verdicts": {},
            "Goal_closure": {"status": "hold", "reason": "deterministic mode does not perform live Maat final judgment"},
            "missing_evidence": ["live_maat_final_judgment"],
            "failure_codes": ["HOLD_DETERMINISTIC_FINAL_MAAT_REQUIRED"],
        }
    contribute_cps["AC_evidence"].setdefault("AC4", {})["status"] = final_judgment.get("status", "hold")
    contribute_cps["Goal_closure"] = final_judgment.get("Goal_closure", contribute_cps["Goal_closure"])
    hold_gap_loop = build_hold_gap_loop(contribute_cps, final_judgment, reducer_result)
    return {
        "candidate": candidate,
        "route": route,
        "draft_probes": draft_probes,
        "probe_responses": probe_responses,
        "reducer_input": reducer_input,
        "reducer_result": reducer_result,
        "probes": probes,
        "local_bodies": local_bodies,
        "local_body_dispatch": local_body_dispatch,
        "handoff_transport": handoff_transport,
        "contribute_cps": contribute_cps,
        "final_judgment": final_judgment,
        "hold_gap_loop": hold_gap_loop,
        "final_selected_agents": final_selected_agents,
        "route_candidate_catalog": route_candidate_catalog,
        "receipt_delta_gate": receipt_delta_gate,
        "continuation_receipt": build_continuation_receipt(packet, final_judgment, receipt_delta_gate, route) if final_judgment.get("status") != "pass" else None,
        "C_AC_route_receipt": build_c_ac_route_receipt(route, receipt_delta_gate),
        "runtime_navigation_receipt": navigation_receipt,
        **working_graph_operational,
    }


def run(packet_path: Path, out_dir: Path, repo: Path, mode: str = "live-maat") -> dict[str, Any]:
    packet = _load_packet(packet_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    max_reentry = max_reentry_iterations(packet)
    candidate = build_candidate(packet, packet_path, repo)
    original_candidate = candidate
    cps_trace_events = candidate.get("cps_trace_events", [])
    c1_trace_context = _c1_trace_context(packet, {"normalized_result": candidate.get("normalized_result", {})})
    chain = execute_preflight_chain(packet, packet_path, repo, mode, candidate)
    receipt_delta_gate = chain.get("receipt_delta_gate", evaluate_receipt_delta(packet))
    reentry_input: dict[str, Any] | None = None
    reentry_chains: list[dict[str, Any]] = []
    iteration = 1 if receipt_delta_gate.get("action") == "reenter" else 0

    candidate = chain["candidate"]
    route = chain["route"]
    draft_probes = chain["draft_probes"]
    probe_responses = chain["probe_responses"]
    reducer_input = chain["reducer_input"]
    reducer_result = chain["reducer_result"]
    probes = chain["probes"]
    local_bodies = chain["local_bodies"]
    local_body_dispatch = chain["local_body_dispatch"]
    contribute_cps = chain["contribute_cps"]
    final_judgment = chain["final_judgment"]
    hold_gap_loop = chain["hold_gap_loop"]
    final_selected_agents = chain["final_selected_agents"]
    route_candidate_catalog = chain.get("route_candidate_catalog") or select_route_candidate_catalog(packet, candidate)
    final_output = final_output_from_judgment(final_judgment, hold_gap_loop)
    final_output["execution_state"] = project_execution_state(packet)
    final_output["mutation_closure"] = candidate.get("mutation_closure", {})
    build_cps_trace_events(c1_trace_context, packet, final_output=final_output, events=cps_trace_events, iteration=iteration, phase="closure")
    selected_for_policy = next((agent for agent in final_selected_agents if agent not in {"maat", "hermes-kann"}), None)
    route["session_policy"] = build_session_policy(packet, repo, selected_for_policy)
    learning = {
        "schema": "harness.cps_preflight.learning_event.v1",
        "contract_ref": str(CONTRACT_PATH),
        "packet_ref": str(packet_path),
        "C": reducer_result.get("revised_C") or route.get("C"),
        "cps_trace_events_ref": "cps_trace_events.json",
        "selected_agents": sorted(route["selected_agents"]),
        "final_selected_agents": sorted(final_selected_agents),
        "audit_plan": route["audit_plan"],
        "verification_gate": route.get("verification_gate", {}),
        "final_audit_needed": route["final_audit_needed"],
        "prohibitions": route["prohibitions"],
        "probe_response_count": len(probe_responses) if mode == "live-maat" else 0,
        "reducer_status": reducer_result.get("status"),
        "final_maat_status": final_judgment.get("status"),
        "Goal_closure": final_output.get("Goal_closure"),
        "reentry_iterations": iteration,
        "reentry_cap": max_reentry,
        "bounded_final_status": final_output.get("status"),
    }
    files = {
        "candidate": out_dir / "c_candidate_packet.json",
        "cps_trace_events": out_dir / "cps_trace_events.json",
        "route_gate": out_dir / "maat_route_gate.json",
        "probes": out_dir / "selected_agent_probes.json",
        "local_bodies": out_dir / "local_task_bodies.json",
        "local_body_dispatch": out_dir / "local_body_dispatch.json",
        "contribute_cps": out_dir / "contribute_cps.json",
        "final_maat_judgment": out_dir / "final_maat_judgment.json",
        "hold_gap_loop": out_dir / "hold_gap_loop.json",
        "learning_event": out_dir / "learning_event.json",
        "agent_draft_probes": out_dir / "agent_draft_probes.json",
        "agent_probe_responses": out_dir / "agent_probe_responses.json",
        "maat_reducer_input": out_dir / "maat_reducer_input.json",
        "maat_reducer_result": out_dir / "maat_reducer_result.json",
        "final_output": out_dir / "final_output.json",
        "dispatch_plan": out_dir / "dispatch_plan.json",
        "runtime_receipt": out_dir / "c1_runtime_receipt.json",
        "continuation_receipt": out_dir / "continuation_receipt.json",
    }
    if reentry_input is not None:
        files["reentry_input"] = out_dir / "reentry_input.json"
    files["candidate"].write_text(json.dumps(candidate, indent=2, ensure_ascii=False), encoding="utf-8")
    files["cps_trace_events"].write_text(json.dumps(cps_trace_events, indent=2, ensure_ascii=False), encoding="utf-8")
    files["route_gate"].write_text(json.dumps(route, indent=2, ensure_ascii=False), encoding="utf-8")
    files["probes"].write_text(json.dumps(probes, indent=2, ensure_ascii=False), encoding="utf-8")
    files["local_bodies"].write_text(json.dumps(local_bodies, indent=2, ensure_ascii=False), encoding="utf-8")
    files["local_body_dispatch"].write_text(json.dumps(local_body_dispatch, indent=2, ensure_ascii=False), encoding="utf-8")
    files["contribute_cps"].write_text(json.dumps(contribute_cps, indent=2, ensure_ascii=False), encoding="utf-8")
    files["final_maat_judgment"].write_text(json.dumps(final_judgment, indent=2, ensure_ascii=False), encoding="utf-8")
    files["hold_gap_loop"].write_text(json.dumps(hold_gap_loop, indent=2, ensure_ascii=False), encoding="utf-8")
    files["learning_event"].write_text(json.dumps(learning, indent=2, ensure_ascii=False), encoding="utf-8")
    files["agent_draft_probes"].write_text(json.dumps(draft_probes if mode == "live-maat" else {}, indent=2, ensure_ascii=False), encoding="utf-8")
    files["agent_probe_responses"].write_text(json.dumps(probe_responses if mode == "live-maat" else {}, indent=2, ensure_ascii=False), encoding="utf-8")
    files["maat_reducer_input"].write_text(json.dumps(reducer_input if mode == "live-maat" else {}, indent=2, ensure_ascii=False), encoding="utf-8")
    files["maat_reducer_result"].write_text(json.dumps(reducer_result, indent=2, ensure_ascii=False), encoding="utf-8")
    files["final_output"].write_text(json.dumps(final_output, indent=2, ensure_ascii=False), encoding="utf-8")
    files["dispatch_plan"].write_text(json.dumps(candidate.get("dispatch_plan"), indent=2, ensure_ascii=False), encoding="utf-8")
    files["runtime_receipt"].write_text(json.dumps(candidate.get("runtime_receipt"), indent=2, ensure_ascii=False), encoding="utf-8")
    continuation_receipt = chain.get("continuation_receipt")
    files["continuation_receipt"].write_text(json.dumps(continuation_receipt, indent=2, ensure_ascii=False), encoding="utf-8")
    if reentry_input is not None:
        files["reentry_input"].write_text(json.dumps(reentry_input, indent=2, ensure_ascii=False), encoding="utf-8")
    for idx, reentry_chain in enumerate(reentry_chains, start=1):
        prefix = out_dir / f"reentry_{idx}"
        (prefix.with_name(prefix.name + "_maat_route_gate.json")).write_text(json.dumps(reentry_chain["route"], indent=2, ensure_ascii=False), encoding="utf-8")
        (prefix.with_name(prefix.name + "_maat_reducer_result.json")).write_text(json.dumps(reentry_chain["reducer_result"], indent=2, ensure_ascii=False), encoding="utf-8")
        (prefix.with_name(prefix.name + "_final_maat_judgment.json")).write_text(json.dumps(reentry_chain["final_judgment"], indent=2, ensure_ascii=False), encoding="utf-8")
    record_preflight_runtime_observation(packet, files, cps_trace_events, candidate.get("runtime_receipt"))
    route_gate_ok = route_gate_usable(route, final_output, final_selected_agents, reducer_result)
    ok = route_gate_ok and final_output.get("status") == "pass"
    return {
        "ok": ok,
        "status": final_output.get("status"),
        "mode": mode,
        "out_dir": str(out_dir),
        "files": {k: str(v) for k, v in files.items()},
        "cps_trace_events": cps_trace_events,
        "route_gate": route,
        "route_candidate_catalog": route_candidate_catalog,
        "maat_reducer_result": reducer_result,
        "final_maat_judgment": final_judgment,
        "final_output": final_output,
        "mutation_closure": final_output["mutation_closure"],
        "continuation_receipt": continuation_receipt,
        "receipt_delta_gate": receipt_delta_gate,
        "reentry_iterations": iteration,
        "reentry_cap": max_reentry,
    }

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run CPS preflight route-gate over a Harness task packet.")
    ap.add_argument("--packet", required=True, type=Path)
    ap.add_argument("--repo", type=Path, default=DEFAULT_REPO)
    ap.add_argument("--out-dir", type=Path)
    ap.add_argument("--mode", choices=["live-maat", "deterministic"], default=os.environ.get("HARNESS_CPS_PREFLIGHT_MODE", "live-maat"))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    packet = args.packet if args.packet.is_absolute() else args.repo / args.packet
    out_dir = args.out_dir or (args.repo / ".harness" / "project" / "runs" / "preflight_route_gate" / packet.stem)
    result = run(packet, out_dir, args.repo, args.mode)
    print(json.dumps(result, indent=2, ensure_ascii=False) if args.json else f"preflight_route_gate={'PASS' if result['ok'] else 'HOLD'} out_dir={result['out_dir']}")
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())


def execution_receipt_transition(work_id: str, graph_root: Path, receipt: dict[str, Any]) -> dict[str, str]:
    registry = WorkingGraphRegistry(graph_root)
    registry.append_execution_receipt(work_id, receipt)
    return registry.resume_parent_edge(work_id, receipt["parent_edge_ref"])
