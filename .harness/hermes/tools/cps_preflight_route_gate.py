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
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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

CONTRACT_PATH = Path("/Users/kann/projects/harness-brain/projects/harness-starter/contracts/cp-cps-preflight-route-gate.md")
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
    for pid in p:
        base = pid[1:].rstrip("?")
        sid = f"S{base}"
        if pid.endswith("?") and f"{sid}?" in s:
            sid = f"{sid}?"
        if sid in s:
            edges.append(f"{pid} -> {sid}")
    return {
        "schema": "harness.cps_preflight.candidate.v1",
        "status": "candidate",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "contract_ref": str(CONTRACT_PATH),
        "packet_ref": str(packet_path),
        "repo": _repo_meta(repo),
        "C?": {"C1": c_text[:240] or "task_route_candidate"},
        "Goal": goal[:240],
        "P?": p,
        "S?": s,
        "E?": edges,
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
    return {
        "schema": "harness.cps_preflight.route_gate.v1",
        "status": "hold" if missing else "pass",
        "C_boundary": "HOLD" if missing else "PASS_ONE_C",
        "C": candidate.get("C?", {}),
        "accepted_P": accepted_p,
        "rejected_P": rejected_p,
        "accepted_S": accepted_s,
        "rejected_S": rejected_s,
        "E": [edge.replace("?", "") for edge in candidate.get("E?", [])],
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


def _live_maat_prompt(candidate: dict[str, Any], packet: dict[str, Any]) -> str:
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
            "selected_agents": {"thoth": {"P": [], "S": [], "response": "need_local_body"}},
            "final_audit_needed": False,
            "failure_codes": [],
            "notes": []
        },
        "candidate": candidate,
        "packet_keys": sorted(packet.keys()),
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
    return route


def invoke_live_maat(candidate: dict[str, Any], packet: dict[str, Any], repo: Path, timeout: int = 180) -> dict[str, Any]:
    """Call the live Maat profile for C-boundary/route-gate adjudication."""
    import subprocess
    env = os.environ.copy()
    env["HERMES_PROFILE"] = "maat"
    cmd = [
        "hermes", "chat", "-Q", "--max-turns", "1", "-t", "", "-q",
        _live_maat_prompt(candidate, packet),
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
        return route
    return _normalize_live_maat(parsed, candidate, session_id, stdout)


def build_agent_draft_probe(agent: str, route: dict[str, Any]) -> dict[str, Any]:
    """Build an agent-specific draft CPS probe; never send the original Maat draft wholesale."""
    spec = route.get("selected_agents", {}).get(agent, {})
    p_ids = spec.get("P", []) if isinstance(spec, dict) else []
    s_ids = spec.get("S", []) if isinstance(spec, dict) else []
    return {
        "schema": "harness.cps_preflight.agent_draft_probe.v1",
        "agent": agent,
        "C_ref": route.get("C"),
        "draft_CPS": {
            "C": route.get("C"),
            "P": {pid: route.get("accepted_P", {}).get(pid) for pid in p_ids if pid in route.get("accepted_P", {})},
            "S": {sid: route.get("accepted_S", {}).get(sid) for sid in s_ids if sid in route.get("accepted_S", {})},
            "E": [edge for edge in route.get("E", []) if any(sid in edge for sid in s_ids)],
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


def build_reducer_input(route: dict[str, Any], probe_responses: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "harness.cps_preflight.reducer_input.v1",
        "route_source": route.get("source"),
        "live_maat_session_id": route.get("live_maat_session_id"),
        "C": route.get("C"),
        "accepted_P": route.get("accepted_P", {}),
        "accepted_S": route.get("accepted_S", {}),
        "E": route.get("E", []),
        "candidate_agents": route.get("selected_agents", {}),
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
        "contract_ref": str(CONTRACT_PATH),
        "C": rr.get("revised_C") or route.get("C"),
        "local_P": {pid: accepted_p.get(pid) for pid in spec.get("P", []) if pid in accepted_p},
        "local_S": {sid: accepted_s.get(sid) for sid in spec.get("S", []) if sid in accepted_s},
        "local_E": [edge for edge in edges if any(sid in edge for sid in spec.get("S", []))],
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
        "task_AC": packet.get("task_AC") or (packet.get("CPS", {}) if isinstance(packet.get("CPS"), dict) else {}).get("AC"),
        "owner_approval_boundary": packet.get("owner_approval_boundary"),
        "prohibited_actions": packet.get("prohibited_actions", ["git add", "git commit", "git push"]),
        "source_refs": packet.get("source_refs", []),
        "artifact_refs": packet.get("artifact_refs", []),
    }


def build_local_body_dispatch(route: dict[str, Any], reducer_result: dict[str, Any], local_bodies: dict[str, Any], final_selected_agents: dict[str, Any] | None = None) -> dict[str, Any]:
    """Record reducer-based dispatch status without inventing a second verification contract."""
    selected = final_selected_agents or normalize_selected_agents(route, reducer_result)
    scope = reducer_result.get("local_body_scope", {}) if isinstance(reducer_result.get("local_body_scope"), dict) else {}
    dispatch: dict[str, Any] = {}
    for agent in selected:
        dispatch[agent] = {
            "selected": True,
            "reducer_status": reducer_result.get("status"),
            "local_body_scope": scope.get(agent),
            "local_body_emitted": agent in local_bodies,
        }
    return {
        "schema": "harness.cps_preflight.local_body_dispatch.v1",
        "status": "pass" if reducer_result.get("status") == "pass" else "hold",
        "policy": "local_task_body is emitted only when reducer_result.local_body_scope grants the agent",
        "dispatch": dispatch,
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


def build_candidate_from_reentry(reentry_input: dict[str, Any], packet_path: Path, repo: Path) -> dict[str, Any]:
    """Convert compact re-entry input back into a Maat route-gate candidate."""
    revised_p = reentry_input.get("revised_P") if isinstance(reentry_input.get("revised_P"), dict) else {}
    revised_s = reentry_input.get("revised_S") if isinstance(reentry_input.get("revised_S"), dict) else {}
    revised_e = reentry_input.get("revised_E") if isinstance(reentry_input.get("revised_E"), list) else []
    return {
        "schema": "harness.cps_preflight.candidate.v1",
        "status": "candidate",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "contract_ref": str(CONTRACT_PATH),
        "packet_ref": str(packet_path),
        "repo": _repo_meta(repo),
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
    return {
        "status": "hold",
        "Goal_closure": final_judgment.get("Goal_closure", {"status": "hold", "reason": "bounded HOLD after Maat final judgment"}),
        "missing_evidence": missing,
    }


def _maat_final_prompt(contribute_cps: dict[str, Any]) -> str:
    payload = {
        "role": "hermes-kann_control_plane",
        "request": "live Maat final AC judgment over CPS preflight trace",
        "hard_rules": [
            "Return exactly one JSON object and no markdown.",
            "Do not mutate files, run tools, use git, or implement.",
            "Judge only the supplied CPS AC and Goal closure; do not invent new criteria.",
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
    route = invoke_live_maat(candidate, packet, repo) if mode == "live-maat" else adjudicate(candidate)
    draft_probes, probe_responses = probe_agents_as_arrive(route, repo) if mode == "live-maat" else ({}, {})
    reducer_input = build_reducer_input(route, probe_responses) if mode == "live-maat" else {}
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
    probes: dict[str, Any] = {}
    local_bodies: dict[str, Any] = {}
    final_selected_agents = normalize_selected_agents(route, reducer_result)
    for agent, spec in final_selected_agents.items():
        probe = build_probe(agent, route, spec, reducer_result)
        probes[agent] = probe
        if local_body_allowed(agent, reducer_result):
            local_bodies[agent] = build_local_body(agent, probe, packet, packet_path)
    local_body_dispatch = build_local_body_dispatch(route, reducer_result, local_bodies, final_selected_agents)
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
    }


def run(packet_path: Path, out_dir: Path, repo: Path, mode: str = "live-maat") -> dict[str, Any]:
    packet = _load_packet(packet_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    max_reentry = max_reentry_iterations(packet)
    candidate = build_candidate(packet, packet_path, repo)
    chain = execute_preflight_chain(packet, packet_path, repo, mode, candidate)
    reentry_input: dict[str, Any] | None = None
    reentry_chains: list[dict[str, Any]] = []
    iteration = 0
    while str(chain["final_judgment"].get("status", "hold")).lower() != "pass" and iteration < max_reentry:
        iteration += 1
        reentry_input = build_reentry_input(chain["hold_gap_loop"], str(packet_path), iteration)
        reentry_candidate = build_candidate_from_reentry(reentry_input, packet_path, repo)
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
    final_output = final_output_from_judgment(final_judgment, hold_gap_loop)
    learning = {
        "schema": "harness.cps_preflight.learning_event.v1",
        "contract_ref": str(CONTRACT_PATH),
        "packet_ref": str(packet_path),
        "C": reducer_result.get("revised_C") or route.get("C"),
        "selected_agents": sorted(route["selected_agents"]),
        "final_selected_agents": sorted(final_selected_agents),
        "audit_plan": route["audit_plan"],
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
    route_gate_usable = route.get("status") == "pass" or (
        route.get("C_boundary") != "HOLD" and bool(route.get("selected_agents"))
    )
    ok = route_gate_usable and final_output.get("status") == "pass"
    return {
        "ok": ok,
        "status": final_output.get("status"),
        "mode": mode,
        "out_dir": str(out_dir),
        "files": {k: str(v) for k, v in files.items()},
        "route_gate": route,
        "maat_reducer_result": reducer_result,
        "final_maat_judgment": final_judgment,
        "final_output": final_output,
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
