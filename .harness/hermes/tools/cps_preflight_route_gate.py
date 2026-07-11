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
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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


def build_cps_seed_graph(packet: dict[str, Any], packet_path: Path, repo: Path) -> dict[str, Any]:
    """Build the first-class compact draft_C/seed_graph artifact before C_candidate compilation."""
    all_text = _text_values(packet)
    lowered = all_text.lower()
    refs = _path_refs(packet, all_text)
    canonical_refs = [ref for ref in refs if "harness-brain" in ref or "contracts" in ref or "decisions" in ref]
    ssot_hint = canonical_refs[0] if canonical_refs else (refs[0] if refs else "unknown")
    project_hint = _packet_field(packet, "project_slug", "project", default=repo.name)
    cps_raw = packet.get("CPS")
    cps = cps_raw if isinstance(cps_raw, dict) else {}
    c_hint = _text_values(cps.get("C") or packet.get("root_goal") or packet.get("goal") or packet.get("task") or packet_path.stem.replace("_", " "))[:240] or "runtime CPS entry seed"
    domains = _domain_hints(lowered)
    seed = {
        "seed_id": "C0",
        "C_hint": c_hint,
        "source_hint": refs[:8],
        "project_hint": project_hint,
        "ssot_hint": ssot_hint,
        "domain_hint": domains,
        "first_move": _first_move(lowered, ssot_hint),
        "expansion_allowed": True,
        "status": "candidate",
        "ssot_confidence": "high" if canonical_refs else ("medium" if refs else "low"),
        "ssot_role": "canonical" if canonical_refs else ("implementation_surface" if refs else "unknown"),
    }
    seed_relations: list[dict[str, Any]] = []
    if len(refs) > 1:
        seed_relations.append({
            "from": "C0",
            "to": ssot_hint,
            "type": "implements",
            "surface_ref": refs[1],
            "reason": "implementation surface is governed by the referenced SSOT candidate",
        })
    return {
        "schema": "harness.cps_entry.seed_graph.v1",
        "request_id": packet.get("run_id") or packet.get("flow_graph_id") or packet_path.stem,
        "packet_ref": str(packet_path),
        "repo": _repo_meta(repo),
        "seeds": {"C0": seed},
        "seed_relations": seed_relations,
        "memory_enrichment": {
            "pivots": {
                "C_shape": ["intent", "boundary_hint", "mutation_or_verification_nature"],
                "domain": domains,
                "ssot_residency": [ssot_hint],
                "project_scope": [project_hint],
            },
            "lookup_required": any(domain != "general" for domain in domains) and seed["first_move"] != "short_local_response_or_bounded_probe",
            "matches": [],
            "status": "not_started",
        },
        "route_seed": {
            "route_class": "ssot_discovery" if ssot_hint == "unknown" else ("implement_candidate" if "implementation" in domains else "inspect_source"),
            "reason": "seed-first CPS entry; route may grow from memory/SSOT/evidence",
            "allowed_action": "narrow_read_only" if ssot_hint == "unknown" else "bounded_probe",
        },
    }


def _seed_requires_maat(seed_graph: dict[str, Any], packet: dict[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
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
    maat_needed, maat_reasons = _seed_requires_maat(seed_graph, packet)
    trace = events if events is not None else []

    def append(event_type: str, payload: dict[str, Any], actor: str = "hermes-kann") -> None:
        parent = trace[-1]["event_id"] if trace else None
        event_id = f"evt-{len(trace) + 1:03d}"
        trace.append({
            "trace_id": trace_id, "event_id": event_id, "parent_event_id": parent,
            "timestamp": timestamp, "event_type": event_type, "actor": actor,
            "iteration": iteration, "event_payload": payload,
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
        if isinstance(packet.get("memory_lookup_result"), dict):
            result = packet["memory_lookup_result"]
            append("memory_lookup_started", {"lookup_ref": result.get("lookup_ref")})
            if result.get("matches"):
                append("memory_match_attached", {"lookup_ref": result.get("lookup_ref"), "match_count": len(result["matches"])})
    elif phase == "reentry":
        append("reentry_started", {"verification_link_delta": packet.get("revised_E", []), "missing_evidence_count": len(packet.get("missing_evidence", []))})
    if final_output is not None:
        append("workflow_closed", {"closure_ref": "final_output.json", "closure_type": final_output.get("status")})
    return trace

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
    all_text = _text_values(packet).lower()
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
    verification = packet.get("verification") if isinstance(packet.get("verification"), dict) else {}
    cps_seed_graph = build_cps_seed_graph(packet, packet_path, repo)
    cps_trace_events = build_cps_trace_events(cps_seed_graph, packet)
    maat_needed, maat_reasons = _seed_requires_maat(cps_seed_graph, packet)
    return {
        "schema": "harness.cps_preflight.candidate.v1",
        "status": "candidate",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "contract_ref": str(CONTRACT_PATH),
        "packet_ref": str(packet_path),
        "repo": _repo_meta(repo),
        "cps_seed_graph": cps_seed_graph,
        "cps_trace_events": cps_trace_events,
        "route_enrichment": {
            "memory": cps_seed_graph.get("memory_enrichment", {}),
            "first_route": cps_seed_graph.get("route_seed", {}),
            "selective_maat_escalation": {"needed": maat_needed, "reasons": maat_reasons},
        },
        "C?": {"C1": c_text[:240] or "task_route_candidate"},
        "Goal": goal[:240],
        "P?": p,
        "S?": s,
        "E?": edges,
        "verification_links": edges,
        "verification": verification,
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
        "cps_seed_graph": candidate.get("cps_seed_graph", {}),
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
    return apply_verification_gate(route, candidate)


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
    allowed = {"schema", "status", "C?", "Goal", "P?", "S?", "E?", "verification_links", "verification", "uncertainty", "request_to_maat", "route_enrichment", "cps_seed_graph"}
    return {key: value for key, value in candidate.items() if key in allowed}


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
            "failure_codes": [],
            "notes": []
        },
        "candidate": _maat_candidate(candidate),
        "body_manifest": manifests,
        "packet_metadata": {key: packet.get(key) for key in ("run_id", "project_slug", "mutation_scope", "route_candidates", "required_evidence_floor", "cross_project_relation") if key in packet},
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
    return apply_verification_gate(route, candidate)


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
        "candidate_agents": route.get("selected_agents", {}),
        "body_manifest": body_manifest or build_body_manifest(route.get("selected_agents", {})),
        "probe_responses": probe_responses,
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


def invoke_maat_reducer(reducer_input: dict[str, Any], repo: Path, timeout: int = 180) -> dict[str, Any]:
    """Ask live Maat to reduce role-probe responses before any local-body dispatch."""
    import subprocess
    env = os.environ.copy()
    env["HERMES_PROFILE"] = "maat"
    cmd = [
        "hermes", "chat", "-Q", "--max-turns", "1", "-t", "", "-q",
        _maat_reducer_prompt(reducer_input),
    ]
    proc = subprocess.run(cmd, cwd=str(repo), env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False, timeout=timeout)
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
    return _normalize_maat_reducer_result(parsed, reducer_input, session_id, stdout)


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
    raw = reducer_result.get("final_selected_agents")
    if not isinstance(raw, dict) or not raw:
        raw = route.get("selected_agents", {})
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
        if local_body_allowed(agent, reducer_result):
            bodies[agent] = build_local_body(agent, probe, packet, packet_path)
    return probes, bodies


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
    """Convert compact re-entry input without recreating the original seed or trace."""
    revised_p = reentry_input.get("revised_P") if isinstance(reentry_input.get("revised_P"), dict) else {}
    revised_s = reentry_input.get("revised_S") if isinstance(reentry_input.get("revised_S"), dict) else {}
    revised_e = reentry_input.get("revised_E") if isinstance(reentry_input.get("revised_E"), list) else []
    original = original_candidate or {}
    cps_seed_graph = original.get("cps_seed_graph", {})
    cps_trace_events = original.get("cps_trace_events", [])
    return {
        "schema": "harness.cps_preflight.candidate.v1",
        "status": "candidate",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "contract_ref": str(CONTRACT_PATH),
        "packet_ref": str(packet_path),
        "repo": _repo_meta(repo),
        "cps_seed_graph": cps_seed_graph,
        "cps_trace_events": cps_trace_events,
        "route_enrichment": original.get("route_enrichment", {}),
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


def execute_preflight_chain(packet: dict[str, Any], packet_path: Path, repo: Path, mode: str, candidate: dict[str, Any]) -> dict[str, Any]:
    """Run route-gate -> probes -> Maat reducer -> local-body gate -> Maat final once."""
    route_candidate_catalog = select_route_candidate_catalog(packet, candidate)
    escalation = candidate.get("route_enrichment", {}).get("selective_maat_escalation", {})
    if not escalation.get("needed", True):
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
    route = invoke_live_maat(candidate, packet, repo, body_manifest=body_manifest) if mode == "live-maat" else adjudicate(candidate)
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
    final_selected_agents = normalize_selected_agents(route, reducer_result)
    selected_manifest = {agent: body_manifest[agent] for agent in final_selected_agents if agent in body_manifest}
    probes, local_bodies = build_agent_body_map(final_selected_agents, route, reducer_result, packet, packet_path)
    local_body_dispatch = build_local_body_dispatch(route, reducer_result, local_bodies, final_selected_agents, selected_manifest)
    contribute_cps = build_contribute_cps(packet, candidate, route, probe_responses, reducer_result, local_body_dispatch)
    final_judgment = invoke_maat_final_judgment(contribute_cps, repo) if mode == "live-maat" else {
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
        "contribute_cps": contribute_cps,
        "final_judgment": final_judgment,
        "hold_gap_loop": hold_gap_loop,
        "final_selected_agents": final_selected_agents,
        "route_candidate_catalog": route_candidate_catalog,
    }


def run(packet_path: Path, out_dir: Path, repo: Path, mode: str = "live-maat") -> dict[str, Any]:
    packet = _load_packet(packet_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    max_reentry = max_reentry_iterations(packet)
    candidate = build_candidate(packet, packet_path, repo)
    original_candidate = candidate
    cps_seed_graph = candidate.get("cps_seed_graph", {})
    cps_trace_events = candidate.get("cps_trace_events", [])
    chain = execute_preflight_chain(packet, packet_path, repo, mode, candidate)
    reentry_input: dict[str, Any] | None = None
    reentry_chains: list[dict[str, Any]] = []
    iteration = 0
    while str(chain["final_judgment"].get("status", "hold")).lower() != "pass" and iteration < max_reentry:
        iteration += 1
        reentry_input = build_reentry_input(chain["hold_gap_loop"], str(packet_path), iteration)
        build_cps_trace_events(cps_seed_graph, reentry_input, events=cps_trace_events, iteration=iteration, phase="reentry")
        reentry_candidate = build_candidate_from_reentry(reentry_input, packet_path, repo, original_candidate)
        chain = execute_preflight_chain(packet, packet_path, repo, mode, reentry_candidate)
        reentry_chains.append(chain)

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
    final_output["mutation_closure"] = candidate.get("mutation_closure", {})
    if isinstance(cps_seed_graph, dict) and cps_seed_graph:
        build_cps_trace_events(cps_seed_graph, packet, final_output=final_output, events=cps_trace_events, iteration=iteration, phase="closure")
    selected_for_policy = next((agent for agent in final_selected_agents if agent not in {"maat", "hermes-kann"}), None)
    route["session_policy"] = build_session_policy(packet, repo, selected_for_policy)
    learning = {
        "schema": "harness.cps_preflight.learning_event.v1",
        "contract_ref": str(CONTRACT_PATH),
        "packet_ref": str(packet_path),
        "C": reducer_result.get("revised_C") or route.get("C"),
        "cps_seed_graph_ref": "cps_seed_graph.json",
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
        "cps_seed_graph": out_dir / "cps_seed_graph.json",
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
    }
    if reentry_input is not None:
        files["reentry_input"] = out_dir / "reentry_input.json"
    files["candidate"].write_text(json.dumps(candidate, indent=2, ensure_ascii=False), encoding="utf-8")
    files["cps_seed_graph"].write_text(json.dumps(cps_seed_graph, indent=2, ensure_ascii=False), encoding="utf-8")
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
    if reentry_input is not None:
        files["reentry_input"].write_text(json.dumps(reentry_input, indent=2, ensure_ascii=False), encoding="utf-8")
    for idx, reentry_chain in enumerate(reentry_chains, start=1):
        prefix = out_dir / f"reentry_{idx}"
        (prefix.with_name(prefix.name + "_maat_route_gate.json")).write_text(json.dumps(reentry_chain["route"], indent=2, ensure_ascii=False), encoding="utf-8")
        (prefix.with_name(prefix.name + "_maat_reducer_result.json")).write_text(json.dumps(reentry_chain["reducer_result"], indent=2, ensure_ascii=False), encoding="utf-8")
        (prefix.with_name(prefix.name + "_final_maat_judgment.json")).write_text(json.dumps(reentry_chain["final_judgment"], indent=2, ensure_ascii=False), encoding="utf-8")
    route_gate_ok = route_gate_usable(route, final_output, final_selected_agents, reducer_result)
    ok = route_gate_ok and final_output.get("status") == "pass"
    return {
        "ok": ok,
        "status": final_output.get("status"),
        "mode": mode,
        "out_dir": str(out_dir),
        "files": {k: str(v) for k, v in files.items()},
        "cps_seed_graph": cps_seed_graph,
        "cps_trace_events": cps_trace_events,
        "route_gate": route,
        "route_candidate_catalog": route_candidate_catalog,
        "maat_reducer_result": reducer_result,
        "final_maat_judgment": final_judgment,
        "final_output": final_output,
        "mutation_closure": final_output["mutation_closure"],
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
