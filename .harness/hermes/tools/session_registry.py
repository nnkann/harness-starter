#!/usr/bin/env python3
"""Project-local Harness session registry."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "harness.session_registry.v1"
ALLOWED_STATES = {
    "representative_open",
    "reusable_open",
    "stale_open",
    "duplicate_open_present",
    "orphan_route_present",
    "closed",
    "blocked_reclaim",
}
PROFILE_CAPS = {
    "maat": 8,
    "thoth": 8,
    "sia": 6,
    "seshat": 6,
    "ptah": 10,
    "anubis": 10,
    "default": 12,
}
RECLAIM_RANK = {
    "orphan_route_present": 0,
    "duplicate_open_present": 1,
    "stale_open": 2,
    "closed": 3,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_registry(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"schema": SCHEMA, "updated_at": utc_now(), "lanes": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"registry must be an object: {path}")
    data.setdefault("schema", SCHEMA)
    data.setdefault("updated_at", utc_now())
    data.setdefault("lanes", {})
    if not isinstance(data["lanes"], dict):
        raise ValueError(f"registry lanes must be an object: {path}")
    return data


def save_registry(path: Path, data: dict[str, Any]) -> None:
    payload = dict(data)
    payload["schema"] = SCHEMA
    payload["updated_at"] = utc_now()
    payload.setdefault("lanes", {})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def lane_key(*, profile: str, platform: str, chat_id: str, thread_id: str | None, project_slug: str | None) -> str:
    stable_thread = thread_id or f"chat:{chat_id}"
    stable_project = project_slug or "unscoped"
    return "|".join([profile or "default", platform or "unknown", chat_id or "unknown", stable_thread, stable_project])


def _session_entry(session_id: str, role: str, state: str, now_iso: str) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "role": role,
        "state": state,
        "started_at": now_iso,
        "last_activity_at": now_iso,
    }


def upsert_representative(
    registry: dict[str, Any],
    *,
    key: str,
    profile: str,
    platform: str,
    chat_id: str,
    thread_id: str | None,
    project_slug: str | None,
    session_id: str | None,
    request_signature: str | None,
    now_iso: str | None = None,
    handoff_snapshot_ref: str | None = None,
    evidence: dict[str, Any] | None = None,
    state: str = "representative_open",
) -> dict[str, Any]:
    now = now_iso or utc_now()
    lanes = registry.setdefault("lanes", {})
    row = dict(lanes.get(key, {}))
    row.update({
        "profile": profile,
        "platform": platform,
        "chat_id": chat_id,
        "thread_id": thread_id,
        "project_slug": project_slug,
        "representative_session_id": session_id,
        "representative_request_signature": request_signature,
        "state": state if state in ALLOWED_STATES else "representative_open",
        "started_at": row.get("started_at") or now,
        "last_activity_at": now,
        "last_response_at": row.get("last_response_at"),
        "last_known_prompt_tokens": row.get("last_known_prompt_tokens", 0),
        "context_limit_hint": row.get("context_limit_hint"),
        "reuse_blockers": row.get("reuse_blockers", []),
        "open_sessions": row.get("open_sessions", []),
        "reclaim_candidates": row.get("reclaim_candidates", []),
        "handoff_snapshot_ref": handoff_snapshot_ref or row.get("handoff_snapshot_ref"),
    })
    raw_evidence = row.get("evidence")
    row_evidence: dict[str, Any] = raw_evidence if isinstance(raw_evidence, dict) else {}
    row["evidence"] = {**row_evidence, **(evidence or {})}
    if session_id:
        existing = [s for s in row["open_sessions"] if s.get("session_id") != session_id]
        current = next((s for s in row["open_sessions"] if s.get("session_id") == session_id), None)
        entry = {**_session_entry(session_id, "representative", "open", now), **(current or {})}
        entry.update({"role": "representative", "state": "open", "last_activity_at": now})
        row["open_sessions"] = existing + [entry]
    lanes[key] = row
    return row


def mark_reclaim_candidate(
    registry: dict[str, Any],
    *,
    key: str,
    session_id: str,
    reason: str,
    state: str,
    evidence_refs: list[str] | None = None,
    now_iso: str | None = None,
) -> dict[str, Any]:
    row = registry.setdefault("lanes", {}).setdefault(key, {"open_sessions": [], "reclaim_candidates": []})
    now = now_iso or utc_now()
    candidates = [c for c in row.get("reclaim_candidates", []) if c.get("session_id") != session_id]
    candidates.append({
        "session_id": session_id,
        "reason": reason,
        "state": state,
        "marked_at": now,
        "evidence_refs": evidence_refs or [],
    })
    row["reclaim_candidates"] = candidates
    row["state"] = state if state in ALLOWED_STATES else "blocked_reclaim"
    return row


def clear_orphan_route(registry: dict[str, Any], *, key: str, evidence_refs: list[str] | None = None, now_iso: str | None = None) -> dict[str, Any]:
    row = registry.setdefault("lanes", {}).setdefault(key, {"open_sessions": [], "reclaim_candidates": []})
    old_session = row.get("representative_session_id")
    if old_session:
        mark_reclaim_candidate(
            registry,
            key=key,
            session_id=str(old_session),
            reason="orphan_route",
            state="orphan_route_present",
            evidence_refs=evidence_refs,
            now_iso=now_iso,
        )
    row["representative_session_id"] = None
    row["state"] = "orphan_route_present"
    return row


def enforce_profile_cap(registry: dict[str, Any], *, profile: str, caps: dict[str, int] | None = None) -> dict[str, Any]:
    cap_map = {**PROFILE_CAPS, **(caps or {})}
    cap = cap_map.get(profile, cap_map["default"])
    lanes = registry.setdefault("lanes", {})
    active = [(key, row) for key, row in lanes.items() if row.get("profile") == profile and row.get("representative_session_id") and row.get("state") != "closed"]
    if len(active) <= cap:
        return {"status": "clear", "profile": profile, "cap": cap, "active_count": len(active), "ranked_candidates": []}
    ranked = sorted(
        ((key, row.get("state", "representative_open"), row.get("representative_session_id")) for key, row in active if row.get("state") in RECLAIM_RANK),
        key=lambda item: RECLAIM_RANK[item[1]],
    )
    if not ranked:
        for key, row in active:
            row["state"] = "blocked_reclaim"
            row.setdefault("reuse_blockers", [])
            if "profile_cap_exceeded_no_candidate" not in row["reuse_blockers"]:
                row["reuse_blockers"].append("profile_cap_exceeded_no_candidate")
        return {"status": "blocked_reclaim", "profile": profile, "cap": cap, "active_count": len(active), "ranked_candidates": []}
    return {
        "status": "candidates_available",
        "profile": profile,
        "cap": cap,
        "active_count": len(active),
        "ranked_candidates": [
            {"lane_key": key, "state": state, "session_id": session_id} for key, state, session_id in ranked
        ],
    }
