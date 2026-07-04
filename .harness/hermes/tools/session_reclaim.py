#!/usr/bin/env python3
"""Read-only Hermes evidence probes and Harness reclaim judgment."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HOME = Path.home()
DEFAULT_SESSIONS_JSON = HOME / ".hermes" / "sessions" / "sessions.json"
DEFAULT_STATE_DB = HOME / ".hermes" / "state.db"
HARD_CONTEXT_USED_CUTOFF = 0.95
STALE_SECONDS = 24 * 60 * 60


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        text = str(value).replace("Z", "+00:00")
        return datetime.fromisoformat(text)
    except Exception:
        return None


def read_hermes_sessions_json(path: Path | None = None) -> dict[str, Any] | None:
    target = path or DEFAULT_SESSIONS_JSON
    if not target.exists():
        return None
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except Exception:
        return None
    if isinstance(data, dict):
        return {"path": str(target), "data": data, "seen": True}
    if isinstance(data, list):
        return {"path": str(target), "data": {"sessions": data}, "seen": True}
    return {"path": str(target), "data": {}, "seen": True}


def read_hermes_state_db_summary(session_ids: list[str], path: Path | None = None) -> dict[str, Any]:
    target = path or DEFAULT_STATE_DB
    summary: dict[str, Any] = {"path": str(target), "seen": target.exists(), "sessions": {}}
    if not target.exists() or not session_ids:
        return summary
    try:
        conn = sqlite3.connect(f"file:{target}?mode=ro", uri=True)
    except Exception as exc:
        summary["error"] = str(exc)
        return summary
    try:
        tables = [row[0] for row in conn.execute("select name from sqlite_master where type='table'")]
        summary["tables_seen"] = tables
        for table in tables:
            cols = [row[1] for row in conn.execute(f"pragma table_info({table})")]
            if "session_id" not in cols and "id" not in cols:
                continue
            id_col = "session_id" if "session_id" in cols else "id"
            wanted_cols = [c for c in (id_col, "status", "state", "ended_at", "closed_at", "updated_at", "last_activity_at") if c in cols]
            if not wanted_cols:
                continue
            placeholders = ",".join("?" for _ in session_ids)
            query = f"select {', '.join(wanted_cols)} from {table} where {id_col} in ({placeholders})"
            for row in conn.execute(query, session_ids):
                item = dict(zip(wanted_cols, row))
                sid = str(item.get(id_col))
                summary["sessions"].setdefault(sid, []).append({"table": table, **item})
    except Exception as exc:
        summary["error"] = str(exc)
    finally:
        conn.close()
    return summary


def _sessions_json_records(evidence: dict[str, Any]) -> dict[str, dict[str, Any]]:
    data = evidence.get("sessions_json", evidence)
    raw = data.get("data", data) if isinstance(data, dict) else {}
    candidates: list[Any] = []
    if isinstance(raw, dict):
        if isinstance(raw.get("sessions"), list):
            candidates = raw["sessions"]
        else:
            candidates = list(raw.values())
    records: dict[str, dict[str, Any]] = {}
    for item in candidates:
        if not isinstance(item, dict):
            continue
        sid = item.get("session_id") or item.get("id") or item.get("sessionId")
        if sid:
            records[str(sid)] = item
    return records


def _state_rows(evidence: dict[str, Any], session_id: str) -> list[dict[str, Any]]:
    state_db = evidence.get("state_db", {}) if isinstance(evidence, dict) else {}
    sessions = state_db.get("sessions", {}) if isinstance(state_db, dict) else {}
    rows = sessions.get(session_id, [])
    return rows if isinstance(rows, list) else []


def _ended_in_evidence(evidence: dict[str, Any], session_id: str) -> bool:
    record = _sessions_json_records(evidence).get(session_id, {})
    for key in ("ended_at", "closed_at"):
        if record.get(key):
            return True
    status = str(record.get("status") or record.get("state") or "").lower()
    if status in {"closed", "ended", "complete", "completed"}:
        return True
    for row in _state_rows(evidence, session_id):
        row_status = str(row.get("status") or row.get("state") or "").lower()
        if row_status in {"closed", "ended", "complete", "completed"} or row.get("ended_at") or row.get("closed_at"):
            return True
    return False


def classify_lane_state(registry_row: dict[str, Any], hermes_evidence: dict[str, Any], *, now_iso: str) -> dict[str, Any]:
    rep = registry_row.get("representative_session_id")
    open_sessions = [s for s in registry_row.get("open_sessions", []) if isinstance(s, dict) and s.get("state", "open") == "open"]
    if rep and _ended_in_evidence(hermes_evidence, str(rep)):
        return {"state": "orphan_route_present", "reason": "representative_ended_in_hermes_evidence", "reuse_blockers": ["representative_ended"]}
    if len(open_sessions) >= 2:
        return {"state": "duplicate_open_present", "reason": "multiple_open_sessions_same_lane", "reuse_blockers": ["duplicate_open_present"]}
    last_response = _parse_time(registry_row.get("last_response_at"))
    last_activity = _parse_time(registry_row.get("last_activity_at"))
    now = _parse_time(now_iso) or datetime.now(timezone.utc)
    if open_sessions and not registry_row.get("task_active_handoff") and not registry_row.get("open_final_audit_path") and not registry_row.get("pending_follow_up_packet") and not registry_row.get("intentionally_long_lived"):
        anchor = last_response or last_activity
        if anchor is None or (now - anchor).total_seconds() >= STALE_SECONDS:
            return {"state": "stale_open", "reason": "open_without_fresh_response_or_active_handoff", "reuse_blockers": ["stale_open"]}
    return {"state": "reusable_open" if rep else "closed", "reason": "clear", "reuse_blockers": []}


def _request_signature(packet: dict[str, Any]) -> str | None:
    value = packet.get("request_signature")
    if value:
        return str(value)
    goal = packet.get("root_goal") or packet.get("goal")
    profile = packet.get("profile") or packet.get("target_profile") or packet.get("selected_profile") or "default"
    if goal:
        return f"{profile}:{' '.join(str(goal).lower().split())}"
    return None


def reuse_decision(registry_row: dict[str, Any], packet: dict[str, Any], *, context_limit_hint: int | None) -> dict[str, Any]:
    blockers = list(registry_row.get("reuse_blockers", []))
    state = registry_row.get("state")
    if state in {"duplicate_open_present", "orphan_route_present", "stale_open", "blocked_reclaim"}:
        blockers.append(str(state))
    if not registry_row.get("representative_session_id"):
        blockers.append("no_representative")
    if packet.get("project_slug") and packet.get("project_slug") != registry_row.get("project_slug"):
        blockers.append("project_drift")
    if packet.get("thread_id") and str(packet.get("thread_id")) != str(registry_row.get("thread_id")):
        blockers.append("thread_drift")
    used = packet.get("context_used_ratio")
    if used is None and packet.get("context_remaining_pct") is not None:
        try:
            used = 1 - (float(packet["context_remaining_pct"]) / 100)
        except Exception:
            used = None
    if used is None and context_limit_hint and registry_row.get("last_known_prompt_tokens") is not None:
        try:
            used = float(registry_row.get("last_known_prompt_tokens") or 0) / float(context_limit_hint)
        except Exception:
            used = None
    if used is not None and float(used) >= HARD_CONTEXT_USED_CUTOFF:
        blockers.append("context_cutoff_95pct")
    current_sig = _request_signature(packet)
    previous_sig = registry_row.get("representative_request_signature")
    follow_up = bool(packet.get("follow_up_compatible") or packet.get("response_received_at") or packet.get("request_kind") == "follow_up")
    if previous_sig and current_sig and previous_sig != current_sig and not follow_up:
        blockers.append("request_signature_mismatch")
    decision = "fresh" if blockers else "reuse"
    return {
        "decision": decision,
        "representative_session_id": registry_row.get("representative_session_id") if decision == "reuse" else None,
        "blockers": sorted(set(blockers)),
        "context_used_ratio": used,
        "hard_cutoff": HARD_CONTEXT_USED_CUTOFF,
    }


def build_reclaim_manifest(registry: dict[str, Any]) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    for key, row in registry.get("lanes", {}).items():
        for candidate in row.get("reclaim_candidates", []):
            candidates.append({
                "lane_key": key,
                "session_id": candidate.get("session_id"),
                "reason_class": candidate.get("reason"),
                "state": candidate.get("state"),
                "evidence_refs": candidate.get("evidence_refs", []),
                "recommended_cleanup_command": "owner-approved bounded follow-up only; inspect `hermes sessions prune` capabilities first",
                "safe": False,
                "blocked_reason": "Hermes exposes coarse cleanup unless an exact state-based close command is owner-approved",
            })
    return {
        "schema": "harness.session_reclaim_manifest.v1",
        "generated_at": _utc_now(),
        "candidate_count": len(candidates),
        "candidates": candidates,
        "physical_cleanup_policy": "logical reclaim only by default; no hidden Hermes mutation",
    }
