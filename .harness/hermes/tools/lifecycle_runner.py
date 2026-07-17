#!/usr/bin/env python3
"""Harness Lifecycle Orchestrator Runner & Agent Delegation Automation.
Automates task session lifecycles (init, check, close) and routes tasks to appropriate Hermes profiles.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from external_runtime_dispatcher import (
    IDENTITY_KEYS as _EXTERNAL_RUNTIME_IDENTITY_KEYS,
    OBSERVED_EVENTS as _EXTERNAL_RUNTIME_OBSERVED_EVENTS,
    TERMINAL_STATUSES as _EXTERNAL_RUNTIME_TERMINAL_STATUSES,
    _paths as _locate_external_runtime_receipts,
    _read_chain_unlocked as _load_external_runtime_chain_read_only,
    _read_current_unlocked as _load_external_runtime_current_read_only,
    _validate_identity as _validate_external_runtime_identity,
    _validate_runtime_facts as _validate_external_runtime_facts,
    dispatch_external_runtime as _dispatch_external_runtime,
    load_receipt_chain as _load_external_runtime_chain,
    poll_external_runtime as _poll_external_runtime,
    reconcile_external_runtime as _reconcile_external_runtime,
)
from cps_working_graph_registry import RegistryError, WorkingGraphRegistry
from session_reclaim import build_reclaim_manifest, classify_lane_state, read_hermes_sessions_json, read_hermes_state_db_summary, reuse_decision
from session_registry import clear_orphan_route, enforce_profile_cap, lane_key, load_registry, mark_reclaim_candidate, save_registry, upsert_representative

# Find repository root
def find_repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in [current, *current.parents]:
        if (parent / ".harness" / "hermes" / "loader.py").exists():
            return parent
    return Path("/Users/kann/projects/harness-starter")

REPO_ROOT = find_repo_root()
SCRIPTS_DIR = REPO_ROOT / ".harness" / "project" / "scripts"
ROUTER_DIR = SCRIPTS_DIR / "router"
LOG_FILE = REPO_ROOT / ".harness" / "project" / "runs" / "background_audit.log"

# Fallback paths from environment or standard locations
HERMES_AGENT_ROOT = Path(os.environ.get("HERMES_AGENT_ROOT", Path.home() / ".hermes/hermes-agent"))
HERMES_RUNTIME_PYTHON = Path("/Users/kann/.hermes/hermes-agent/venv/bin/python")


def _imports_honcho(python: Path, agent_root: Path = HERMES_AGENT_ROOT) -> bool:
    probe = """
import os, sys
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path.home() / '.hermes/.env')
sys.path.insert(0, sys.argv[1])
import honcho
os.environ['HONCHO_BASE_URL']
"""
    if not python.is_file() or not os.access(python, os.X_OK):
        return False
    result = subprocess.run(
        [str(python), "-c", probe, str(agent_root)],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def _select_python() -> Path:
    if _imports_honcho(HERMES_RUNTIME_PYTHON):
        return HERMES_RUNTIME_PYTHON
    current = Path(sys.executable)
    if _imports_honcho(current):
        return current
    raise RuntimeError("no Hermes runtime interpreter can import Honcho with HONCHO_BASE_URL configured")


PYTHON_EXEC = _select_python()


class ExternalRuntimeProductionAdapter:
    def __init__(self, record_root: Path):
        self.record_root = Path(record_root)

    def dispatch(
        self,
        identity: dict[str, Any],
        consumer_ref: str,
        body: bytes,
        argv: list[str],
        *,
        process_runner=None,
    ) -> dict[str, Any]:
        return _dispatch_external_runtime(
            consumer_ref,
            body,
            argv,
            self.record_root,
            identity=identity,
            process_runner=process_runner,
        )

    def poll(self, identity: dict[str, Any]) -> dict[str, Any] | None:
        return _poll_external_runtime(identity, self.record_root)

    def reconcile(
        self,
        identity: dict[str, Any],
        *,
        pid_is_alive=None,
        stale_after_seconds: float | None = None,
    ) -> dict[str, Any] | None:
        return _reconcile_external_runtime(
            identity,
            self.record_root,
            pid_is_alive=pid_is_alive,
            stale_after_seconds=stale_after_seconds,
        )


class ExternalRuntimeStateProjectionAdapter:
    def __init__(self, record_root: Path):
        self.record_root = Path(record_root)

    @staticmethod
    def _issued(authorization: dict[str, Any]) -> dict[str, Any]:
        return {
            "authorization_state": "ISSUED",
            "runtime_state": None,
            "execution_status": None,
            "execution_receipt_ref": None,
            "execution_event": None,
            "run_handle": None,
            "attempt": None,
            "recorded_at": authorization.get("recorded_at"),
            "audit_verdict": None,
            "state_source_ref": authorization.get("state_source_ref"),
        }

    @staticmethod
    def _identity(authorization: dict[str, Any]) -> dict[str, Any]:
        nested = authorization.get("identity")
        if isinstance(nested, dict):
            return _validate_external_runtime_identity(nested)
        identity = {key: authorization.get(key) for key in _EXTERNAL_RUNTIME_IDENTITY_KEYS}
        return _validate_external_runtime_identity(identity)

    @staticmethod
    def _valid_chain(chain: list[dict[str, Any]]) -> bool:
        terminal_seen = False
        for index, receipt in enumerate(chain):
            event = receipt.get("facts", {}).get("event")
            status = receipt.get("status")
            if terminal_seen or receipt.get("family") != "execution_receipt":
                return False
            if not isinstance(receipt.get("recorded_at"), str):
                return False
            external = receipt.get("external_runtime_receipt")
            if not isinstance(external, dict) or not all(external.get(key) for key in ("producer_ref", "runtime_receipt", "consumer_ref")):
                return False
            try:
                _validate_external_runtime_facts(receipt.get("facts"))
            except ValueError:
                return False
            if event == "terminal":
                if status not in _EXTERNAL_RUNTIME_TERMINAL_STATUSES or index != len(chain) - 1:
                    return False
                terminal_seen = True
            elif event not in _EXTERNAL_RUNTIME_OBSERVED_EVENTS or status != "observed":
                return False
        return True

    def project(self, authorization: dict[str, Any]) -> dict[str, Any]:
        issued = self._issued(authorization)
        try:
            identity = self._identity(authorization)
            chain_path, current_path, _ = _locate_external_runtime_receipts(identity, self.record_root)
            if not chain_path.is_file() or not current_path.is_file():
                return issued
            chain = _load_external_runtime_chain_read_only(identity, self.record_root)
            current = _load_external_runtime_current_read_only(identity, self.record_root)
            if not chain or not isinstance(current, dict) or current != chain[-1] or not self._valid_chain(chain):
                return issued
            chain_after = _load_external_runtime_chain_read_only(identity, self.record_root)
            current_after = _load_external_runtime_current_read_only(identity, self.record_root)
            if chain_after != chain or current_after != current:
                return issued
        except (OSError, RuntimeError, TypeError, ValueError):
            return issued
        event = current["facts"]["event"]
        terminal = event == "terminal"
        return {
            "authorization_state": "ISSUED",
            "runtime_state": "TERMINAL" if terminal else "RUNNING",
            "execution_status": current["status"] if terminal else None,
            "execution_receipt_ref": current["receipt_ref"],
            "execution_event": event,
            "run_handle": current["run_handle"],
            "attempt": current["attempt"],
            "recorded_at": current["recorded_at"],
            "audit_verdict": None,
            "state_source_ref": str(current_path.resolve()),
        }


def project_external_runtime_state(authorization: dict[str, Any], record_root: Path) -> dict[str, Any]:
    return ExternalRuntimeStateProjectionAdapter(record_root).project(authorization)


class PreAuthorizedTransitionProductionAdapter:
    def __init__(self, graph_root: Path, evidence_root: Path):
        self.store = WorkingGraphRegistry(Path(graph_root))
        self.evidence_root = Path(evidence_root).resolve()

    def _load_ref(self, ref: str) -> dict[str, Any]:
        if not isinstance(ref, str) or not ref or Path(ref).is_absolute() or ".." in Path(ref).parts:
            raise RegistryError("HOLD_PREAUTH_PREDICATE")
        path = (self.evidence_root / ref).resolve()
        if self.evidence_root not in path.parents:
            raise RegistryError("HOLD_PREAUTH_PREDICATE")
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except Exception as error:
            raise RegistryError("HOLD_PREAUTH_PREDICATE") from error
        if not isinstance(value, dict):
            raise RegistryError("HOLD_PREAUTH_PREDICATE")
        return value

    def materialize(
        self,
        work_id: str,
        transition_id: str,
        materialization_binding: dict[str, Any],
    ) -> dict[str, Any]:
        return self.store.materialize_pre_authorized_transition(
            work_id, transition_id, materialization_binding, self._load_ref,
        )


class FinalAuditProductionAdapter:
    def __init__(self, graph_root: Path, execution_root: Path):
        self.graph_root = Path(graph_root)
        self.store = WorkingGraphRegistry(self.graph_root)
        self.execution_root = Path(execution_root)

    def reload(self, identity: dict[str, Any]) -> dict[str, Any]:
        work_id = identity.get("work_id", "")
        graph = self.store.load(work_id)
        expected_graph_ref = str((self.graph_root / f"{work_id}.yaml").resolve())
        if (
            identity.get("graph_ref") != expected_graph_ref
            or graph.get("revision") != identity.get("graph_revision")
            or graph.get("maat_body_digest") != identity.get("graph_digest")
            or not self.store.verify_readback(work_id)
        ):
            return {"status": "hold", "failure_code": "HOLD_BINDING_MISMATCH"}
        chain = _load_external_runtime_chain(identity, self.execution_root)
        current = chain[-1] if chain else None
        if not isinstance(current, dict) or current.get("facts", {}).get("event") != "terminal":
            return {"status": "hold", "failure_code": "HOLD_EXECUTION_INCOMPLETE"}
        if current.get("status") != "pass":
            return {"status": "hold", "failure_code": "HOLD_EXECUTION_CASE"}
        body = graph.get("maat_body")
        if not isinstance(body, dict) or body.get("goal_eligible") is not True:
            return {"status": "hold", "failure_code": "HOLD_SEMANTIC_AC"}
        returns_to = body.get("returns_to", [])
        if not isinstance(returns_to, list) or any(
            not isinstance(edge, dict) or edge.get("status") != "satisfied" for edge in returns_to
        ):
            return {"status": "hold", "failure_code": "HOLD_RETURN_EDGE"}
        return {
            "status": "eligible_for_maat_audit",
            "semantic_lane": {
                "graph_ref": expected_graph_ref,
                "graph_revision": graph["revision"],
                "graph_digest": graph["maat_body_digest"],
            },
            "execution_lane": {
                "receipt_ref": current.get("receipt_ref"),
                "status": current.get("status"),
                "parent_edge_ref": current.get("parent_edge_ref"),
                "return_to_node_ref": current.get("return_to_node_ref"),
            },
        }


def dispatch_external_body(
    agent: str,
    body: bytes,
    argv: list[str],
    record_root: Path,
    *,
    identity: dict[str, Any] | None = None,
    process_runner=None,
) -> dict[str, Any]:
    if identity is None:
        raise TypeError("explicit receipt identity required; direct runtime bypass rejected")
    return ExternalRuntimeProductionAdapter(record_root).dispatch(
        identity, agent, body, argv, process_runner=process_runner,
    )


def poll_external_body(identity: dict[str, Any], record_root: Path) -> dict[str, Any] | None:
    return ExternalRuntimeProductionAdapter(record_root).poll(identity)


def reconcile_external_body(
    identity: dict[str, Any],
    record_root: Path,
    *,
    pid_is_alive=None,
    stale_after_seconds: float | None = None,
) -> dict[str, Any] | None:
    return ExternalRuntimeProductionAdapter(record_root).reconcile(
        identity,
        pid_is_alive=pid_is_alive,
        stale_after_seconds=stale_after_seconds,
    )

def log_audit(action: str, exit_code: int, message: str) -> None:
    """Write structured audit log to keep compatibility with bash runner."""
    timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    log_entry = {
        "timestamp": timestamp,
        "action": action,
        "exit_code": exit_code,
        "message": message
    }
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry) + "\n")

def run_command_with_audit(name: str, cmd: list[str], cwd: Path) -> int:
    """Run a command, capture output, and write audit log."""
    print(f"[Harness Lifecycle] Running: {name}...")
    try:
        # Run command, capturing stdout and stderr
        result = subprocess.run(
            cmd,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False
        )
        # Save last log to runs dir
        log_dir = REPO_ROOT / ".harness" / "project" / "runs"
        log_dir.mkdir(parents=True, exist_ok=True)
        last_log = log_dir / f"last_{name}.log"
        last_log.write_text(result.stdout, encoding="utf-8")
        
        if result.returncode == 0:
            print(f"[Harness Lifecycle] {name} completed successfully.")
            log_audit(name, 0, "Success")
            return 0
        else:
            print(f"[Harness Lifecycle] ERROR: {name} failed with exit code {result.returncode}.")
            # Print last few lines of log
            lines = result.stdout.strip().splitlines()
            snippet = "\n".join(lines[-10:]) if len(lines) > 10 else result.stdout
            print(f"--- Log Snippet ---\n{snippet}\n-------------------")
            log_audit(name, result.returncode, f"Failed. Check last_{name}.log for details.")
            return result.returncode
    except Exception as e:
        print(f"[Harness Lifecycle] ERROR: Exception while running {name}: {e}")
        log_audit(name, -1, f"Failed with exception: {e}")
        return -1

def load_packet(packet_path: Path) -> dict[str, Any]:
    """Load task packet supporting both JSON and YAML if pyyaml is installed."""
    if not packet_path.exists():
        raise FileNotFoundError(f"Task packet not found at: {packet_path}")
    
    raw = packet_path.read_text(encoding="utf-8")
    if packet_path.suffix.lower() == ".json":
        return json.loads(raw)
        
    try:
        import yaml
        return yaml.safe_load(raw) or {}
    except ImportError:
        # Dependency-free fallback parser for YAML (extract basic fields)
        data: dict[str, Any] = {}
        current_key = None
        for line in raw.splitlines():
            line_strip = line.strip()
            if not line_strip or line_strip.startswith("#"):
                continue
            if not line.startswith(" ") and ":" in line:
                key, _, val = line.partition(":")
                current_key = key.strip()
                val_strip = val.strip()
                if val_strip:
                    data[current_key] = val_strip
                else:
                    data[current_key] = []
            elif line.startswith(" ") and current_key in data and isinstance(data[current_key], list):
                # Simple list element extraction
                if line_strip.startswith("-"):
                    data[current_key].append(line_strip[1:].strip())
        return data

def _utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _parse_iso8601(timestamp: str | None) -> datetime | None:
    if not timestamp:
        return None
    try:
        return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except Exception:
        return None


def _normalize_request_signature(root_goal: str, expected_next_hop: str) -> str:
    normalized = " ".join(str(root_goal or "").lower().split())
    return f"{expected_next_hop}:{normalized}"


def _normalized_goal_key(root_goal: str) -> str:
    return " ".join(str(root_goal or "").lower().split())


def _packet_value(packet_data: dict[str, Any], *keys: str, default: str | None = None) -> str | None:
    for key in keys:
        value = packet_data.get(key)
        if value not in (None, ""):
            return str(value)
    return default


def _project_slug(packet_data: dict[str, Any]) -> str:
    return _packet_value(packet_data, "project_slug", "project", default=REPO_ROOT.name) or REPO_ROOT.name


def _request_signature(packet_data: dict[str, Any], profile: str) -> str:
    root_goal = str(packet_data.get("root_goal", "") or packet_data.get("goal", ""))
    return str(packet_data.get("request_signature") or _normalize_request_signature(root_goal, profile))


def _packet_session_id(packet_data: dict[str, Any], profile: str) -> str:
    return str(
        packet_data.get("representative_session_id")
        or packet_data.get("session_id")
        or packet_data.get("run_id")
        or packet_data.get("flow_graph_id")
        or f"pending:{profile}:{_normalized_goal_key(str(packet_data.get('root_goal') or packet_data.get('goal') or 'unknown'))[:80]}"
    )


def apply_session_policy(packet_data: dict[str, Any], routing: dict[str, Any], runs_dir: Path) -> dict[str, Any]:
    registry_path = runs_dir / "session_registry.json"
    manifest_path = runs_dir / "session_reclaim_manifest.json"
    profile = str(routing.get("selected_profile") or packet_data.get("profile") or packet_data.get("target_profile") or "default")
    platform = _packet_value(packet_data, "platform", "source_platform", default="local") or "local"
    chat_id = _packet_value(packet_data, "chat_id", "channel_id", "conversation_id", default="local") or "local"
    thread_id = _packet_value(packet_data, "thread_id", "topic_id")
    project_slug = _project_slug(packet_data)
    key = lane_key(profile=profile, platform=platform, chat_id=chat_id, thread_id=thread_id, project_slug=project_slug)
    now = _utc_now()
    registry = load_registry(registry_path)
    row = registry.get("lanes", {}).get(key)
    evidence_session_ids = [str(s.get("session_id")) for s in (row or {}).get("open_sessions", []) if isinstance(s, dict) and s.get("session_id")]
    if row and row.get("representative_session_id"):
        evidence_session_ids.append(str(row["representative_session_id"]))
    hermes_evidence = {
        "sessions_json": read_hermes_sessions_json(),
        "state_db": read_hermes_state_db_summary(sorted(set(evidence_session_ids))),
    }
    classification = classify_lane_state(row, hermes_evidence, now_iso=now) if row else {"state": "closed", "reason": "no_existing_lane", "reuse_blockers": []}
    if row:
        row["state"] = classification["state"]
        row["reuse_blockers"] = classification.get("reuse_blockers", [])
        if classification["state"] == "orphan_route_present":
            row = clear_orphan_route(registry, key=key, evidence_refs=["~/.hermes/state.db", "~/.hermes/sessions/sessions.json"], now_iso=now)
        elif classification["state"] == "duplicate_open_present":
            open_sessions = sorted(row.get("open_sessions", []), key=lambda item: str(item.get("last_activity_at") or item.get("started_at") or ""))
            for duplicate in open_sessions[:-1]:
                mark_reclaim_candidate(registry, key=key, session_id=str(duplicate.get("session_id")), reason="duplicate_open", state="duplicate_open_present", evidence_refs=["session_registry.json"], now_iso=now)
        elif classification["state"] == "stale_open" and row.get("representative_session_id"):
            mark_reclaim_candidate(registry, key=key, session_id=str(row["representative_session_id"]), reason="stale_open", state="stale_open", evidence_refs=["session_registry.json"], now_iso=now)
    row = registry.get("lanes", {}).get(key, {})
    decision = reuse_decision(row, packet_data, context_limit_hint=packet_data.get("context_limit_hint")) if row else {"decision": "fresh", "representative_session_id": None, "blockers": ["no_existing_lane"]}
    if decision["decision"] == "fresh":
        row = upsert_representative(
            registry,
            key=key,
            profile=profile,
            platform=platform,
            chat_id=chat_id,
            thread_id=thread_id,
            project_slug=project_slug,
            session_id=_packet_session_id(packet_data, profile),
            request_signature=_request_signature(packet_data, profile),
            now_iso=now,
            handoff_snapshot_ref=".harness/project/runs/handoff_snapshot.json",
            evidence={"sessions_json_seen": bool(hermes_evidence["sessions_json"]), "state_db_seen": bool(hermes_evidence["state_db"].get("seen")), "thread_snapshot_seen": bool(thread_id)},
            state=classification["state"] if classification["state"] in {"duplicate_open_present", "orphan_route_present", "stale_open"} else "representative_open",
        )
    cap_result = enforce_profile_cap(registry, profile=profile)
    if cap_result.get("status") == "blocked_reclaim":
        row = registry.get("lanes", {}).get(key, row)
        row["state"] = "blocked_reclaim"
        decision = {"decision": "blocked", "representative_session_id": None, "blockers": ["profile_cap_exceeded_no_candidate"]}
    save_registry(registry_path, registry)
    manifest_ref = None
    manifest = build_reclaim_manifest(registry)
    if manifest["candidate_count"]:
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        manifest_ref = str(manifest_path.relative_to(REPO_ROOT))
    elif manifest_path.exists():
        manifest_path.unlink()
    return {
        "lane_key": key,
        "representative_session_id": row.get("representative_session_id"),
        "reuse_decision": decision["decision"],
        "reuse_blockers": decision.get("blockers", []),
        "reclaim_state": row.get("state", classification["state"]),
        "reclaim_manifest_ref": manifest_ref,
        "registry_ref": str(registry_path.relative_to(REPO_ROOT)),
        "cap_status": cap_result,
    }


def attach_dispatch_plan(routing: dict[str, Any], preflight_result: dict[str, Any]) -> None:
    route_gate = preflight_result.get("route_gate")
    plan = route_gate.get("dispatch_plan") if isinstance(route_gate, dict) else None
    if not isinstance(plan, dict):
        return
    routing["dispatch_plan"] = plan
    routing["selected_nodes"] = list(plan.get("nodes", {}))
    routing["ready_nodes"] = list(plan.get("ready_nodes", []))
    routing["blocked_nodes"] = dict(plan.get("blocked_nodes", {}))


def build_handoff_snapshot(packet_data: dict[str, Any], routing: dict[str, Any], preflight_result: dict[str, Any] | None) -> dict[str, Any]:
    route_gate = preflight_result.get("route_gate", {}) if isinstance(preflight_result, dict) and isinstance(preflight_result.get("route_gate"), dict) else {}
    selected_agents = route_gate.get("selected_agents", {}) if isinstance(route_gate.get("selected_agents"), dict) else {}
    expected_next_hop = routing.get("selected_profile") or "unknown"
    handoff_chain = ["hermes-kann"] + [agent for agent in selected_agents if agent != "hermes-kann"]
    root_goal = str(packet_data.get("root_goal", "") or packet_data.get("goal", ""))
    snapshot_at = packet_data.get("snapshot_at") or _utc_now()
    response_received_at = packet_data.get("response_received_at")
    last_response_at = packet_data.get("last_response_at") or response_received_at or snapshot_at
    return {
        "schema": "harness.handoff_snapshot.v1",
        "snapshot_at": snapshot_at,
        "task_id": packet_data.get("run_id") or packet_data.get("flow_graph_id") or packet_data.get("task_id") or root_goal or "unknown_task",
        "packet_ref": routing.get("packet_ref"),
        "root_goal": root_goal,
        "request_signature": packet_data.get("request_signature") or _normalize_request_signature(root_goal, expected_next_hop),
        "current_owner": "hermes-kann",
        "expected_next_hop": expected_next_hop,
        "current_stage": "delegation_ready",
        "last_action": "delegate_route_selected",
        "last_response_from": "maat_preflight" if preflight_result else "local_router",
        "last_response_at": last_response_at,
        "response_received_at": response_received_at,
        "handoff_chain": handoff_chain,
        "anomaly_flag": False,
        "anomaly_type": None,
        "anomaly_brief": None,
        "handoff_count": max(len(handoff_chain) - 1, 0),
        "retry_count": int(packet_data.get("retry_count", 0) or 0),
        "elapsed_seconds": int(packet_data.get("elapsed_seconds", 0) or 0),
        "token_budget_remaining": packet_data.get("token_budget_remaining"),
        "context_remaining_pct": packet_data.get("context_remaining_pct"),
        "session_policy": routing.get("session_policy"),
        "dispatch_plan": routing.get("dispatch_plan"),
        "selected_nodes": routing.get("selected_nodes", []),
        "ready_nodes": routing.get("ready_nodes", []),
        "blocked_nodes": routing.get("blocked_nodes", {}),
    }


def write_handoff_snapshot(snapshot: dict[str, Any], runs_dir: Path) -> Path:
    current = runs_dir / "handoff_snapshot.json"
    prev1 = runs_dir / "handoff_snapshot.prev1.json"
    prev2 = runs_dir / "handoff_snapshot.prev2.json"
    prev3 = runs_dir / "handoff_snapshot.prev3.json"
    runs_dir.mkdir(parents=True, exist_ok=True)
    prev3.unlink(missing_ok=True)
    if prev1.exists():
        if prev2.exists():
            prev2.unlink()
        prev1.replace(prev2)
    if current.exists():
        current.replace(prev1)
    current.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    return current


def _load_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def build_hu_handoff_analysis(current_snapshot: dict[str, Any], previous_snapshot: dict[str, Any] | None) -> dict[str, Any] | None:
    if not previous_snapshot:
        return None
    risk_points: list[str] = []
    anomaly_type: str | None = None
    idle_gap_seconds = None
    if current_snapshot.get("request_signature") == previous_snapshot.get("request_signature"):
        risk_points.append("same_request_signature_as_prev1")
    response_received_at = _parse_iso8601(current_snapshot.get("response_received_at"))
    snapshot_at = _parse_iso8601(current_snapshot.get("snapshot_at"))
    if response_received_at and snapshot_at:
        idle_gap_seconds = int((snapshot_at - response_received_at).total_seconds())
        if idle_gap_seconds >= 300:
            risk_points.append("idle_gap_exceeded_threshold")
    if response_received_at:
        risk_points.append("response_received_before_repeat_request")
    if {
        "same_request_signature_as_prev1",
        "response_received_before_repeat_request",
        "idle_gap_exceeded_threshold",
    }.issubset(set(risk_points)):
        anomaly_type = "duplicate_request_after_response"
    elif {"response_received_before_repeat_request", "idle_gap_exceeded_threshold"}.issubset(set(risk_points)):
        anomaly_type = "idle_after_response"
    if not anomaly_type:
        return None
    return {
        "anomaly_type": anomaly_type,
        "severity": "medium" if anomaly_type == "duplicate_request_after_response" else "low",
        "idle_gap_seconds": idle_gap_seconds,
        "risk_points": risk_points,
        "current_snapshot_ref": current_snapshot.get("packet_ref"),
        "previous_snapshot_ref": previous_snapshot.get("packet_ref"),
        "request_signature": current_snapshot.get("request_signature"),
        "summary": f"{anomaly_type} detected for {current_snapshot.get('expected_next_hop')} after {idle_gap_seconds}s idle gap" if idle_gap_seconds is not None else f"{anomaly_type} detected",
    }


def detect_follow_up_continuity(packet_data: dict[str, Any], previous_snapshot: dict[str, Any] | None, previous_routing: dict[str, Any] | None) -> dict[str, Any] | None:
    if not previous_snapshot or not previous_routing:
        return None
    if not packet_data.get("response_received_at"):
        return None
    current_goal = _normalized_goal_key(str(packet_data.get("root_goal", "") or packet_data.get("goal", "")))
    previous_goal = _normalized_goal_key(str(previous_snapshot.get("root_goal", "")))
    if not current_goal or current_goal != previous_goal:
        return None
    return {
        "status": "follow_up",
        "classification": "reused_existing_handoff",
        "previous_task_id": previous_snapshot.get("task_id"),
        "previous_snapshot_ref": previous_snapshot.get("packet_ref"),
        "selected_profile": previous_snapshot.get("expected_next_hop") or previous_routing.get("selected_profile"),
        "reason": "same_root_goal_after_response",
    }


def build_follow_up_snapshot(packet_data: dict[str, Any], previous_snapshot: dict[str, Any], routing: dict[str, Any], packet_ref: Path) -> dict[str, Any]:
    snapshot = build_handoff_snapshot(packet_data, routing, None)
    snapshot.update({
        "current_stage": "follow_up_linked",
        "last_action": "reuse_existing_handoff",
        "request_kind": "follow_up",
        "linked_snapshot_ref": previous_snapshot.get("packet_ref"),
        "linked_task_id": previous_snapshot.get("task_id"),
        "anomaly_flag": False,
        "anomaly_type": None,
        "anomaly_brief": None,
        "packet_ref": str(packet_ref),
    })
    return snapshot


def write_handoff_continuity(continuity: dict[str, Any], current_snapshot: dict[str, Any], runs_dir: Path) -> Path:
    path = runs_dir / "handoff_continuity.json"
    payload = dict(continuity)
    payload.update({
        "schema": "harness.handoff_continuity.v1",
        "current_task_id": current_snapshot.get("task_id"),
        "current_snapshot_ref": current_snapshot.get("packet_ref"),
        "request_signature": current_snapshot.get("request_signature"),
    })
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def reuse_previous_routing(previous_routing: dict[str, Any], packet_ref: Path, continuity: dict[str, Any]) -> dict[str, Any]:
    routing = dict(previous_routing)
    routing["packet_ref"] = str(packet_ref)
    routing["selected_profile"] = continuity.get("selected_profile") or previous_routing.get("selected_profile")
    routing["rationale"] = "Follow-up continuation matched an existing handoff; reused prior selected route instead of creating a new delegation request."
    routing["request_kind"] = "follow_up"
    routing["continuity"] = continuity
    return routing


def write_hu_handoff_artifacts(analysis: dict[str, Any] | None, current_snapshot: dict[str, Any], runs_dir: Path) -> tuple[Path | None, Path | None]:
    packet_path = runs_dir / "hu_handoff_packet.json"
    analysis_path = runs_dir / "hu_handoff_analysis.json"
    if not analysis:
        packet_path.unlink(missing_ok=True)
        analysis_path.unlink(missing_ok=True)
        return None, None
    hu_packet = {
        "schema": "harness.hu_handoff_packet.v1",
        "target_profile": "hu",
        "source_profile": "hermes-kann",
        "anomaly_type": analysis["anomaly_type"],
        "snapshot_ref": current_snapshot.get("packet_ref"),
        "snapshot_task_id": current_snapshot.get("task_id"),
        "request_signature": analysis.get("request_signature"),
        "summary": analysis.get("summary"),
    }
    hu_analysis = {
        "schema": "harness.hu_handoff_analysis.v1",
        "target_profile": "hu",
        "analysis": analysis,
    }
    packet_path.write_text(json.dumps(hu_packet, indent=2), encoding="utf-8")
    analysis_path.write_text(json.dumps(hu_analysis, indent=2), encoding="utf-8")
    return packet_path, analysis_path


def route_task_packet(packet_data: dict[str, Any]) -> dict[str, Any]:
    """Analyze CPS and other metadata in a task packet to route it to the optimal profile."""
    # Look at CPS C, P, S
    cps_raw = packet_data.get("CPS", {})
    cps = cps_raw if isinstance(cps_raw, dict) else {}
    c_list = cps.get("C", []) if isinstance(cps.get("C"), list) else [str(cps.get("C") or "")]
    p_list = cps.get("P", []) if isinstance(cps.get("P"), list) else [str(cps.get("P") or "")]
    s_list = cps.get("S", []) if isinstance(cps.get("S"), list) else [str(cps.get("S") or "")]
    
    c_text = " ".join(map(str, c_list)).lower()
    p_text = " ".join(map(str, p_list)).lower()
    s_text = " ".join(map(str, s_list)).lower()
    
    # Check other fields
    task_ac_list = packet_data.get("task_AC", [])
    task_ac = " ".join(map(str, task_ac_list if isinstance(task_ac_list, list) else [task_ac_list])).lower()
    
    goal = str(packet_data.get("root_goal", "") or packet_data.get("goal", "")).lower()
    
    cps_full_text = json.dumps(cps, ensure_ascii=False).lower() if isinstance(cps, dict) else str(cps).lower()
    all_text = f"{c_text} {p_text} {s_text} {task_ac} {goal} {cps_full_text}"
    
    # Scored mapping based on domain keywords
    scores = {
        "seshat": 0,             # docs-operator
        "ptah": 0,               # coder
        "anubis": 0,             # reviewer / lifecycle / cleanup
        "sekhmet": 0,            # threat-guard
        "researcher": 0,         # researcher
        "thoth": 0,              # orchestrator
        "maat": 0,               # moderator
        "sia": 0,                # cognitive-analyzer
    }
    
    # seshat: docs, markdown, frontmatter, document, manifest, required_docs, doc_ops, wiki, digest
    for word in ["doc", "markdown", "frontmatter", "manifest", "required_docs", "doc_ops", "wiki", "digest"]:
        if word in all_text:
            scores["seshat"] += 3
            
    # ptah: code, implement, test, refactor, script, python, execution, bug, algorithm, feature, backend, database
    for word in ["code", "implement", "test", "refactor", "script", "python", "execution", "bug", "algorithm", "feature", "backend", "database", "compile"]:
        if word in all_text:
            scores["ptah"] += 3
            
    # anubis: review, audit, check, verify, compliance, cleanup, close, gateway, snapshot, writeback, completion, gate
    for word in ["review", "audit", "check", "verify", "compliance", "cleanup", "close", "gateway", "snapshot", "writeback", "completion", "gate"]:
        if word in all_text:
            scores["anubis"] += 3
            
    # sekhmet: security, threat, permission, secret, safe, sandbox, auth, exposure, credentials, policy, restrict
    for word in ["security", "threat", "permission", "secret", "safe", "sandbox", "auth", "exposure", "credentials", "policy", "restrict"]:
        if word in all_text:
            scores["sekhmet"] += 3
            
    # researcher: research, external, freshest, crawl, api, spider, scrape, internet, search, fact, source
    for word in ["research", "external", "freshest", "crawl", "api", "spider", "scrape", "internet", "search", "fact", "source"]:
        if word in all_text:
            scores["researcher"] += 3
            
    # thoth: coordinate, triage, route, compile-contract, fan-out, planning, coordination
    for word in ["coordinate", "triage", "route", "compile-contract", "fan-out", "planning", "coordination"]:
        if word in all_text:
            scores["thoth"] += 3
            
    # maat: gate, approve, judge, moderator, final-gate, criteria
    for word in ["gate", "approve", "judge", "moderator", "final-gate", "criteria"]:
        if word in all_text:
            scores["maat"] += 3

    # sia: cognitive, perception, diagnose, diagnostics, reasoning, analysis, low-token, memory-only
    for word in ["cognitive", "perception", "diagnose", "diagnostics", "reasoning", "analysis", "low-token", "memory-only"]:
        if word in all_text:
            scores["sia"] += 3
 
    # Resolve highest scoring profile
    best_profile = max(scores, key=scores.get)
    if scores[best_profile] == 0:
        # default fallback
        best_profile = "ptah"
        
    profile_details = {
        "seshat": {"role": "docs-operator", "deity": "seshat", "desc": "Handles documents, frontmatter, required-docs, and Honcho digests."},
        "ptah": {"role": "coder", "deity": "ptah", "desc": "Handles code implementation, testing, refactoring, and execution."},
        "anubis": {"role": "reviewer", "deity": "anubis", "desc": "Handles review, compliance, lifecycle cleanup, and snapshots."},
        "sekhmet": {"role": "threat-guard", "deity": "sekhmet", "desc": "Handles sandbox policy, secrets, permissions, and threat guarding."},
        "researcher": {"role": "researcher", "deity": "imhotep", "desc": "Handles external facts, searches, and documentation research."},
        "thoth": {"role": "orchestrator", "deity": "thoth", "desc": "Handles triage, task routing, and coordinating handoffs."},
        "maat": {"role": "moderator", "deity": "maat", "desc": "Handles gating, final approvals, and compliance verification."},
        "sia": {"role": "cognitive-analyzer", "deity": "sia", "desc": "Handles low-token cognitive analysis, diagnostics, perception, and reasoning-review."}
    }
    
    details = profile_details[best_profile]
    return {
        "selected_profile": best_profile,
        "role": details["role"],
        "deity": details["deity"],
        "description": details["desc"],
        "scores": scores,
        "rationale": f"Profile '{best_profile}' selected with a score of {scores[best_profile]} matching keywords in the task packet."
    }

def do_init(session_id: str, manifest: str | None) -> int:
    """AC-1: Seed Honcho context, ingest pending manifests, and trigger LazyCodex wiki/research."""
    print("=== Phase: Init (Seeding & Ingestion with LazyCodex) ===")
    
    # Step 1: Seeding
    seed_script = ROUTER_DIR / "seed_honcho_project_context.py"
    seed_cmd = [
        str(PYTHON_EXEC),
        str(seed_script),
        "--honcho-session-key", session_id,
        "--hermes-agent-root", str(HERMES_AGENT_ROOT),
        "--repo", str(REPO_ROOT)
    ]
    ret = run_command_with_audit("seed-context", seed_cmd, REPO_ROOT)
    if ret != 0:
        return ret
        
    # Step 2: Ingest manifests
    worker_script = ROUTER_DIR / "honcho_background_worker.py"
    ingest_cmd = [
        str(PYTHON_EXEC),
        str(worker_script),
        "--action", "ingest",
        "--honcho-session-key", session_id,
        "--hermes-agent-root", str(HERMES_AGENT_ROOT),
        "--repo", str(REPO_ROOT)
    ]
    if manifest:
        ingest_cmd.extend(["--manifest", manifest])
        
    ret = run_command_with_audit("ingest-manifests", ingest_cmd, REPO_ROOT)
    if ret != 0:
        return ret

    # Step 3: LazyCodex doc_ops Wiki Indexing
    print("[Harness Lifecycle] Ingesting domain abbreviations into LLM Wiki...")
    wiki_script = REPO_ROOT / ".harness" / "hermes" / "tools" / "lazycodex_doc_ops_wiki.py"
    if wiki_script.exists():
        wiki_cmd = [str(PYTHON_EXEC), str(wiki_script), "CPS"]
        run_command_with_audit("wiki-index", wiki_cmd, REPO_ROOT)

    # Step 4: Asynchronous Swarm Research (Triggered if GITHUB_TOKEN is present)
    research_script = REPO_ROOT / ".harness" / "hermes" / "tools" / "lazycodex_swarm_research.py"
    if research_script.exists() and os.environ.get("GITHUB_TOKEN"):
        print("[Harness Lifecycle] Triggering background Swarm Research...")
        research_cmd = [
            str(PYTHON_EXEC),
            str(research_script),
            "--repo", "code-yeongyu/lazycodex",
            "--query", "lifecycle init auto"
        ]
        # Run asynchronously to avoid blocking init phase
        try:
            subprocess.Popen(
                research_cmd,
                cwd=str(REPO_ROOT),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print("[Harness Lifecycle] Swarm Research launched in background.")
        except Exception as e:
            print(f"[Harness Lifecycle] Failed to launch Swarm Research: {e}")

    return 0

def do_check(session_id: str, manifest: str | None) -> int:
    """AC-2: Drift Detection, Static Clean & Slim Compliance, and Reporting."""
    print("=== Phase: Check (Drift Detection & Clean/Slim Compliance) ===")
    worker_script = ROUTER_DIR / "honcho_background_worker.py"
    check_cmd = [
        str(PYTHON_EXEC),
        str(worker_script),
        "--action", "check-drift",
        "--honcho-session-key", session_id,
        "--hermes-agent-root", str(HERMES_AGENT_ROOT),
        "--repo", str(REPO_ROOT)
    ]
    if manifest:
        check_cmd.extend(["--manifest", manifest])
        
    # Run the check-drift action
    print(f"[Harness Lifecycle] Running check-drift...")
    result = subprocess.run(
        check_cmd,
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False
    )
    
    drift_output = result.stdout
    drift_exit_code = result.returncode

    # Run Clean & Slim Audit
    print("[Harness Lifecycle] Running Clean & Slim compliance check...")
    audit_script = REPO_ROOT / ".harness" / "hermes" / "tools" / "audit_clean_slim.py"
    audit_output = ""
    audit_exit_code = 0
    if audit_script.exists():
        audit_cmd = [
            str(PYTHON_EXEC),
            str(audit_script),
            "--path", str(REPO_ROOT / ".harness" / "hermes" / "tools")
        ]
        audit_result = subprocess.run(
            audit_cmd,
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False
        )
        audit_output = audit_result.stdout
        audit_exit_code = audit_result.returncode

    # Combine reports
    reports_dir = REPO_ROOT / ".harness" / "project" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_file = reports_dir / f"drift_report_{session_id}.txt"

    combined_report = []
    combined_report.append("=========================================")
    combined_report.append("HARNESS INTEGRATED LIFECYCLE CHECK REPORT")
    combined_report.append(f"Session ID: {session_id}")
    combined_report.append(f"Timestamp: {datetime.now().isoformat()}")
    combined_report.append("=========================================\n")
    
    combined_report.append("### 1. HONCHO DRIFT DETECTION")
    combined_report.append(f"Exit Code: {drift_exit_code}")
    combined_report.append(drift_output)
    combined_report.append("\n-----------------------------------------\n")
    
    combined_report.append("### 2. CLEAN & SLIM STATIC AUDIT")
    combined_report.append(f"Exit Code: {audit_exit_code}")
    combined_report.append(audit_output if audit_output else "Audit script not executed or no output.")
    
    report_content = "\n".join(combined_report)
    report_file.write_text(report_content, encoding="utf-8")
    
    # Save last check log
    log_dir = REPO_ROOT / ".harness" / "project" / "runs"
    log_dir.mkdir(parents=True, exist_ok=True)
    last_log = log_dir / "last_check-drift.log"
    last_log.write_text(report_content, encoding="utf-8")

    if drift_exit_code == 0 and audit_exit_code == 0:
        print(f"[Harness Lifecycle] Integrated check completed. Report written to {report_file.relative_to(REPO_ROOT)}")
        print(report_content)
        log_audit("check-drift", 0, "Integrated drift and clean/slim report successfully generated")
        return 0
    else:
        print(f"[Harness Lifecycle] ERROR: Integrated check failed (Drift: {drift_exit_code}, Audit: {audit_exit_code}).")
        # Print snippet of failures
        failures = []
        if drift_exit_code != 0:
            failures.append("Honcho Drift Detection Failed")
        if audit_exit_code != 0:
            failures.append("Clean & Slim Static Audit Failed (Compliance issues detected)")
        log_audit("check-drift", -1, f"Integrated check failed: {', '.join(failures)}")
        return -1

def do_close(session_id: str, writeback_args: list[str]) -> int:
    """AC-3: Writeback & Gateway Cleanup."""
    print("=== Phase: Close (Writeback & Gateway Cleanup) ===")
    worker_script = ROUTER_DIR / "honcho_background_worker.py"
    close_cmd = [
        str(PYTHON_EXEC),
        str(worker_script),
        "--action", "writeback",
        "--session-id", session_id,
        "--hermes-agent-root", str(HERMES_AGENT_ROOT),
        "--repo", str(REPO_ROOT)
    ]
    # Parse writeback specific options from writeback_args if they are passed
    close_cmd.extend(writeback_args)
    
    return run_command_with_audit("writeback", close_cmd, REPO_ROOT)

def do_delegate(packet_path: str) -> int:
    """Analyze a task packet and determine the optimal agent delegation."""
    print("=== Agent Delegation & Role Routing ===")
    p_path = Path(packet_path)
    if not p_path.is_absolute():
        p_path = REPO_ROOT / p_path
    runs_dir = REPO_ROOT / ".harness" / "project" / "runs"
    previous_snapshot = _load_json_if_exists(runs_dir / "handoff_snapshot.json")
    previous_routing = _load_json_if_exists(runs_dir / "delegation_decision.json")
        
    try:
        packet_data = load_packet(p_path)
    except Exception as e:
        print(f"ERROR: Failed to load task packet: {e}")
        return 1

    continuity = detect_follow_up_continuity(packet_data, previous_snapshot, previous_routing)
    if continuity and previous_snapshot and previous_routing:
        routing = reuse_previous_routing(previous_routing, p_path, continuity)
        session_policy = apply_session_policy(packet_data, routing, runs_dir)
        routing["session_policy"] = session_policy
        decision_file = runs_dir / "delegation_decision.json"
        decision_file.parent.mkdir(parents=True, exist_ok=True)
        decision_file.write_text(json.dumps(routing, indent=2), encoding="utf-8")
        snapshot = build_follow_up_snapshot(packet_data, previous_snapshot, routing, p_path)
        snapshot_file = write_handoff_snapshot(snapshot, runs_dir)
        continuity_file = write_handoff_continuity(continuity, snapshot, runs_dir)
        write_hu_handoff_artifacts(None, snapshot, runs_dir)
        print(f"Follow-up continuation reused via {continuity_file.relative_to(REPO_ROOT)}")
        print(f"Delegation decision saved to {decision_file.relative_to(REPO_ROOT)}")
        print(f"Handoff snapshot saved to {snapshot_file.relative_to(REPO_ROOT)}")
        return 0
        
    preflight_script = REPO_ROOT / ".harness" / "hermes" / "tools" / "cps_preflight_route_gate.py"
    preflight_dir = REPO_ROOT / ".harness" / "project" / "runs" / "preflight_route_gate" / p_path.stem
    preflight_result: dict[str, Any] | None = None
    if preflight_script.exists():
        preflight_cmd = [
            str(PYTHON_EXEC),
            str(preflight_script),
            "--packet",
            str(p_path),
            "--repo",
            str(REPO_ROOT),
            "--out-dir",
            str(preflight_dir),
            "--json",
        ]
        result = subprocess.run(preflight_cmd, cwd=str(REPO_ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False)
        (REPO_ROOT / ".harness" / "project" / "runs").mkdir(parents=True, exist_ok=True)
        (REPO_ROOT / ".harness" / "project" / "runs" / "last_preflight-route-gate.log").write_text(result.stdout, encoding="utf-8")
        if result.returncode != 0:
            print("ERROR: CPS preflight route-gate returned HOLD/FAIL.")
            print(result.stdout)
            return result.returncode
        try:
            preflight_result = json.loads(result.stdout)
        except Exception:
            preflight_result = None

    routing = route_task_packet(packet_data)
    routing["packet_ref"] = str(p_path)
    if preflight_result:
        route_gate = preflight_result.get("route_gate", {}) if isinstance(preflight_result.get("route_gate"), dict) else {}
        verification_gate = route_gate.get("verification_gate", {}) if isinstance(route_gate.get("verification_gate"), dict) else {}
        selected_agents = route_gate.get("selected_agents", {})
        non_control = [a for a in selected_agents if a not in {"maat", "hermes-kann"}]
        if non_control:
            details = {
                "seshat": ("docs-operator", "seshat", "Handles documents, frontmatter, source refs, and doc_ops evidence."),
                "ptah": ("coder", "ptah", "Handles bounded implementation after settled local P/S/AC/body."),
                "thoth": ("orchestrator", "thoth", "Handles CPS compile/fan-out when Maat keeps that branch."),
                "sia": ("cognitive-analyzer", "sia", "Handles compact recall when Maat keeps that branch."),
                "sekhmet": ("threat-guard", "sekhmet", "Handles security/sandbox/secret/path risk."),
                "hu": ("efficiency-advisor", "hu", "Handles token/time/footprint optimization."),
                "anubis": ("reviewer", "anubis", "Handles integrity, diff, and reversibility checks."),
            }
            chosen = non_control[0]
            routing["selected_profile"] = chosen
            if chosen in details:
                routing["role"], routing["deity"], routing["description"] = details[chosen]
            routing["rationale"] = f"Selected after CPS preflight route-gate; local body is available under {preflight_result.get('out_dir')}"
        routing["preflight_verification_gate"] = verification_gate
        routing["preflight_route_gate"] = preflight_result
        attach_dispatch_plan(routing, preflight_result)
    session_policy = apply_session_policy(packet_data, routing, runs_dir)
    routing["session_policy"] = session_policy
    if preflight_result and isinstance(preflight_result.get("route_gate"), dict):
        preflight_result["route_gate"]["session_policy"] = session_policy
    snapshot = build_handoff_snapshot(packet_data, routing, preflight_result)
    
    print("\n--- Delegation Decision ---")
    print(f"Target Packet: {p_path.relative_to(REPO_ROOT)}")
    if preflight_result:
        print(f"Preflight Route:  {preflight_result.get('out_dir')}")
    print(f"Selected Profile: {routing['selected_profile']}")
    print(f"Role Archetype:   {routing['role']}")
    print(f"Deity Binding:    {routing['deity']}")
    print(f"Description:     {routing['description']}")
    print(f"Rationale:       {routing['rationale']}")
    print("\nScores:")
    for profile, score in sorted(routing['scores'].items(), key=lambda x: x[1], reverse=True):
        print(f"  - {profile:18}: {score}")
    print("---------------------------\n")
    
    # Output delegation JSON for machine parsing
    decision_file = REPO_ROOT / ".harness" / "project" / "runs" / "delegation_decision.json"
    runs_dir = REPO_ROOT / ".harness" / "project" / "runs"
    decision_file.parent.mkdir(parents=True, exist_ok=True)
    decision_file.write_text(json.dumps(routing, indent=2), encoding="utf-8")
    snapshot_file = write_handoff_snapshot(snapshot, runs_dir)
    previous_snapshot = _load_json_if_exists(runs_dir / "handoff_snapshot.prev1.json")
    hu_analysis = build_hu_handoff_analysis(snapshot, previous_snapshot)
    if hu_analysis:
        snapshot["anomaly_flag"] = True
        snapshot["anomaly_type"] = hu_analysis["anomaly_type"]
        snapshot["anomaly_brief"] = hu_analysis["summary"]
        snapshot_file.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    write_hu_handoff_artifacts(hu_analysis, snapshot, runs_dir)
    print(f"Delegation decision saved to {decision_file.relative_to(REPO_ROOT)}")
    print(f"Handoff snapshot saved to {snapshot_file.relative_to(REPO_ROOT)}")
    if hu_analysis:
        print(f"Hu handoff analysis saved to {(runs_dir / 'hu_handoff_analysis.json').relative_to(REPO_ROOT)}")
    return 0

def _sha(value: str) -> str:
    if len(value) != 40 or any(character not in "0123456789abcdefABCDEF" for character in value):
        raise argparse.ArgumentTypeError("must be a 40-character SHA")
    return value.lower()


def _budget_measurement(value: str) -> Any:
    try:
        return int(value)
    except ValueError:
        return value


class _LifecycleArgumentParser(argparse.ArgumentParser):
    def parse_known_args(self, args: Any = None, namespace: argparse.Namespace | None = None):
        parsed, unknown = super().parse_known_args(args, namespace)
        if parsed.action == "c2-memory":
            missing = [name for name in ("branch", "pushed_sha", "source_ref", "lifecycle") if not getattr(parsed, name)]
            if missing:
                self.error("c2-memory requires " + ", ".join("--" + name.replace("_", "-") for name in missing))
            if parsed.lifecycle == "initialization" and parsed.prior_ref:
                self.error("initialization cannot be paired with --prior-ref")
        return parsed, unknown


def build_parser() -> argparse.ArgumentParser:
    parser = _LifecycleArgumentParser(description="Harness Lifecycle Orchestrator & Delegation Runner")
    parser.add_argument("action", choices=["init", "check", "close", "all", "delegate", "c2-memory"], help="Lifecycle phase or delegation action")
    parser.add_argument("--session-id", help="Honcho session key or ID")
    parser.add_argument("--packet", help="Path to the task packet (required for 'delegate')")
    parser.add_argument("--manifest", help="Custom path to Honcho ingest manifest")
    parser.add_argument("--branch", required=False)
    parser.add_argument("--pushed-sha", type=_sha)
    parser.add_argument("--source-ref")
    parser.add_argument("--lifecycle", choices=("initialization", "revised", "withdrawn"))
    parser.add_argument("--prior-ref")
    parser.add_argument("--token-estimate", type=_budget_measurement)
    parser.add_argument("--token-budget-remaining", type=_budget_measurement)
    parser.add_argument("--context-remaining-pct", type=_budget_measurement)
    parser.add_argument("--budget-source-ref", default="lifecycle-runner:c2-memory-cli")
    parser.add_argument("--budget-age-seconds", type=_budget_measurement)
    parser.add_argument("--actual-token-usage", type=_budget_measurement)
    return parser


def _load_cps_memory_lifecycle():
    path = ROUTER_DIR / "cps_memory_lifecycle.py"
    spec = importlib.util.spec_from_file_location("cps_memory_lifecycle_production", path)
    if not spec or not spec.loader:
        raise RuntimeError("c2-memory lifecycle module unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _remote_branch_contains(repo: Path, branch: str, pushed_sha: str) -> bool:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", pushed_sha, f"refs/remotes/origin/{branch}"],
        cwd=str(repo), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL, check=False,
    )
    return result.returncode == 0


def _build_event(module, repo: Path, args):
    blob = subprocess.run(
        ["git", "show", f"{args.pushed_sha}:{args.source_ref}"], cwd=str(repo),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL, check=False,
    )
    if blob.returncode != 0:
        raise RuntimeError("source-ref-unavailable-at-pushed-sha")
    lifecycle_name = "revised" if args.lifecycle == "initialization" else args.lifecycle
    source_digest = hashlib.sha256(args.source_ref.encode("utf-8")).hexdigest()
    return module.PushedShaEvent(
        event_id=f"push:{args.branch}:{args.pushed_sha}:{source_digest}", pushed_sha=args.pushed_sha,
        source_ref=args.source_ref, source_revision=args.pushed_sha,
        content_hash=hashlib.sha256(blob.stdout).hexdigest(), lifecycle=lifecycle_name,
        graph_ref=module.CANONICAL_GRAPH_REF, prior_ref=args.prior_ref, attempt=1,
        first_anchor_initialization=args.lifecycle == "initialization",
    )


class HonchoUnavailable(RuntimeError):
    pass


class _BudgetBlockedAnchorPort:
    def __init__(self, identity: str):
        self.identity = identity


class _HonchoSdkAnchorPort:
    def __init__(self, client, identity: str, observer: str, target: str):
        self.client, self.identity, self.observer, self.target = client, identity, observer, target

    def _scope(self):
        return self.client.peer(self.observer).conclusions_of(self.target)

    def write_anchor(self, anchor):
        created = self._scope().create([{"content": json.dumps(dict(anchor), sort_keys=True)}])
        item = created[0] if isinstance(created, (list, tuple)) and created else created
        ref = getattr(item, "id", None) or (item.get("id") if isinstance(item, dict) else None)
        if not ref:
            raise RuntimeError("Honcho returned no conclusion ID")
        return str(ref)

    def read_anchor(self, anchor_ref):
        conclusion_id = anchor_ref.removeprefix("honcho:")
        page = self._scope().list(size=50)
        while page is not None:
            for item in page:
                item_id = getattr(item, "id", None) or (item.get("id") if isinstance(item, dict) else None)
                if str(item_id) != conclusion_id:
                    continue
                content = getattr(item, "content", None) or (item.get("content") if isinstance(item, dict) else None)
                if not content:
                    raise RuntimeError("Honcho conclusion readback unavailable")
                parsed = json.loads(content)
                return parsed.get("cps_compact_anchor", parsed)
            page = page.get_next_page() if page.has_next_page else None
        raise RuntimeError("Honcho conclusion readback unavailable")

    def deactivate_anchor(self, anchor_ref, superseded_by):
        created = self._scope().create([{"content": json.dumps({"inactive_ref": anchor_ref, "superseded_by": superseded_by}, sort_keys=True)}])
        return bool(created)


def _load_honcho_worker():
    path = ROUTER_DIR / "honcho_background_worker.py"
    spec = importlib.util.spec_from_file_location("honcho_background_worker_production", path)
    if not spec or not spec.loader:
        raise RuntimeError("Honcho production adapter module unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _build_honcho_ports():
    worker = _load_honcho_worker()
    agent_root = Path(os.environ.get("HERMES_AGENT_ROOT", HERMES_AGENT_ROOT))
    try:
        writer_manager, _, writer_cfg = worker._init_honcho(REPO_ROOT, agent_root, "cps-anchor-writer")
        if writer_manager is None or not writer_cfg.enabled:
            raise RuntimeError("client disabled")
        writer = worker.HonchoAnchorAdapter(writer_manager, "cps-anchor-writer")

        from plugins.memory.honcho.client import reset_honcho_client
        reset_honcho_client()
        reader_manager, _, reader_cfg = worker._init_honcho(REPO_ROOT, agent_root, "cps-anchor-readback")
        if reader_manager is None or not reader_cfg.enabled:
            raise RuntimeError("readback client disabled")
        reader_session = reader_manager.get_or_create("cps-anchor-readback")
        writer_session = writer_manager.get_or_create("cps-anchor-writer")
        reader = _HonchoSdkAnchorPort(
            reader_manager._honcho,
            "readback:%s" % reader_session.honcho_session_id,
            writer_session.assistant_peer_id,
            writer_session.user_peer_id,
        )
        return writer, reader
    except Exception as exc:
        raise HonchoUnavailable(str(exc)) from exc


def run_c2_memory(args, repo: Path = REPO_ROOT) -> tuple[int, dict[str, Any]]:
    module = _load_cps_memory_lifecycle()
    action_ref = f"c2-memory:{args.branch}:{args.pushed_sha}"
    evidence: dict[str, Any] = {
        "action_ref": action_ref,
        "call_ref": module.CANONICAL_GRAPH_REF,
        "profile_call_requires_cps_reason": True,
    }
    if not _remote_branch_contains(repo, args.branch, args.pushed_sha):
        evidence.update(status="blocked", reason="pushed-sha-not-confirmed-on-existing-tracking-ref", closure_candidate=False)
        return 2, evidence
    try:
        event = _build_event(module, repo, args)
        budget_decision = module.build_budget_decision(
            getattr(args, "budget_source_ref", "lifecycle-runner:c2-memory-cli"),
            getattr(args, "token_estimate", None),
            getattr(args, "token_budget_remaining", None),
            getattr(args, "context_remaining_pct", None),
            getattr(args, "budget_age_seconds", None),
            getattr(args, "actual_token_usage", None),
        )
        if budget_decision.decision == "admitted":
            writer, reader = _build_honcho_ports()
        else:
            writer = _BudgetBlockedAnchorPort("budget-gate-writer")
            reader = _BudgetBlockedAnchorPort("budget-gate-reader")
        database_path = repo / ".harness" / "project" / "runs" / "cps_memory_lifecycle.sqlite3"
        adapters = module.ProductionStageAdapters(repo, database_path, writer, reader, budget_decision)
        module.run_stage_core(event, adapters)
        receipts = tuple(adapters.reload_stage_receipts(event))
        closure_candidate = module.evaluate_closure(receipts, event)
    except HonchoUnavailable as exc:
        evidence.update(status="blocked", reason=f"honcho-unavailable:{exc}", closure_candidate=False)
        return 3, evidence
    except Exception as exc:
        evidence.update(status="blocked", reason=str(exc), closure_candidate=False)
        return 4, evidence
    evidence.update(
        status="closure_candidate" if closure_candidate else "blocked",
        closure_candidate=closure_candidate,
        receipt_refs=[f"{receipt.event_id}:{receipt.stage_id}:{receipt.attempt}" for receipt in receipts],
        receipts=[{
            "stage_id": receipt.stage_id,
            "status": receipt.status,
            "reason": receipt.reason,
            "refs": dict(receipt.refs),
        } for receipt in receipts],
        durable_receipt_reload=tuple(receipts) == tuple(adapters.reload_stage_receipts(event)),
        anchor_ref=next((receipt.refs.get("conclusion_ref") for receipt in receipts if receipt.stage_id == "N7"), None),
        readback_ref=next((receipt.refs.get("conclusion_ref") for receipt in receipts if receipt.stage_id == "N8"), None),
        anchor_readback_exact=next((receipt.refs.get("conclusion_ref") for receipt in receipts if receipt.stage_id == "N7"), None)
        == next((receipt.refs.get("conclusion_ref") for receipt in receipts if receipt.stage_id == "N8"), None),
    )
    return (0 if closure_candidate else 5), evidence


def main() -> int:
    parser = build_parser()
    
    # Capture all remaining arguments to pass to writeback or scripts
    args, unknown = parser.parse_known_args()
    
    # Resolve or generate session ID
    session_id = args.session_id
    if not session_id:
        if args.packet:
            try:
                packet_data = load_packet(Path(args.packet))
                session_id = packet_data.get("run_id") or packet_data.get("flow_graph_id")
            except Exception:
                pass
        if not session_id:
            session_id = os.environ.get("HERMES_KANBAN_RUN_ID") or "session_harness_auto"
            
    # Perform actions
    if args.action == "c2-memory":
        if unknown:
            parser.error("unrecognized arguments: " + " ".join(unknown))
        code, evidence = run_c2_memory(args)
        print(json.dumps(evidence, sort_keys=True))
        return code
    if args.action == "init":
        return do_init(session_id, args.manifest)
    elif args.action == "check":
        return do_check(session_id, args.manifest)
    elif args.action == "close":
        return do_close(session_id, unknown)
    elif args.action == "all":
        ret = do_init(session_id, args.manifest)
        if ret != 0:
            return ret
        ret = do_check(session_id, args.manifest)
        if ret != 0:
            return ret
        return do_close(session_id, unknown)
    elif args.action == "delegate":
        if not args.packet:
            parser.error("--packet is required when action is 'delegate'")
        return do_delegate(args.packet)
        
    return 0

if __name__ == "__main__":
    sys.exit(main())
