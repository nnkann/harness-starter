from pathlib import Path
import sys

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

from session_reclaim import build_reclaim_manifest, classify_lane_state, reuse_decision
from session_registry import lane_key, load_registry, mark_reclaim_candidate, save_registry, upsert_representative
import cps_preflight_route_gate
import lifecycle_runner


def test_same_lane_ended_db_row_is_orphan():
    row = {"representative_session_id": "s1", "open_sessions": [{"session_id": "s1", "state": "open"}]}
    evidence = {"state_db": {"sessions": {"s1": [{"state": "closed"}]}}, "sessions_json": None}
    result = classify_lane_state(row, evidence, now_iso="2026-07-05T00:00:00Z")
    assert result["state"] == "orphan_route_present"


def test_same_lane_two_open_sessions_is_duplicate():
    row = {"representative_session_id": "s2", "open_sessions": [{"session_id": "s1", "state": "open"}, {"session_id": "s2", "state": "open"}]}
    result = classify_lane_state(row, {"state_db": {}, "sessions_json": {}}, now_iso="2026-07-05T00:00:00Z")
    assert result["state"] == "duplicate_open_present"


def test_stale_open_without_live_handoff():
    row = {"representative_session_id": "s1", "last_activity_at": "2026-07-03T00:00:00Z", "open_sessions": [{"session_id": "s1", "state": "open"}]}
    result = classify_lane_state(row, {"state_db": {}, "sessions_json": {}}, now_iso="2026-07-05T00:00:00Z")
    assert result["state"] == "stale_open"


def test_below_cutoff_same_purpose_followup_reuses():
    row = {
        "state": "reusable_open",
        "representative_session_id": "s1",
        "representative_request_signature": "ptah:fix bug",
        "project_slug": "harness-starter",
        "thread_id": "t1",
    }
    packet = {"request_signature": "ptah:fix bug", "project_slug": "harness-starter", "thread_id": "t1", "context_used_ratio": 0.50}
    result = reuse_decision(row, packet, context_limit_hint=None)
    assert result["decision"] == "reuse"


def test_at_or_above_cutoff_fresh():
    row = {"state": "reusable_open", "representative_session_id": "s1", "representative_request_signature": "ptah:fix bug"}
    result = reuse_decision(row, {"request_signature": "ptah:fix bug", "context_used_ratio": 0.95}, context_limit_hint=None)
    assert result["decision"] == "fresh"
    assert "context_cutoff_95pct" in result["blockers"]


def test_manifest_lists_candidates():
    registry = load_registry(Path("missing.json"))
    key = lane_key(profile="ptah", platform="local", chat_id="c", thread_id=None, project_slug="harness-starter")
    upsert_representative(registry, key=key, profile="ptah", platform="local", chat_id="c", thread_id=None, project_slug="harness-starter", session_id="s1", request_signature="ptah:goal")
    mark_reclaim_candidate(registry, key=key, session_id="s1", reason="duplicate_open", state="duplicate_open_present")
    manifest = build_reclaim_manifest(registry)
    assert manifest["candidate_count"] == 1
    assert manifest["candidates"][0]["safe"] is False


def test_lifecycle_policy_writes_registry_and_manifest(tmp_path, monkeypatch):
    monkeypatch.setattr(lifecycle_runner, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(lifecycle_runner, "read_hermes_sessions_json", lambda: {"seen": True, "data": {}})
    monkeypatch.setattr(lifecycle_runner, "read_hermes_state_db_summary", lambda session_ids: {"seen": True, "sessions": {}})
    runs = tmp_path / ".harness" / "project" / "runs"
    key = lane_key(profile="ptah", platform="discord", chat_id="c1", thread_id="t1", project_slug="harness-starter")
    registry = load_registry(runs / "session_registry.json")
    row = upsert_representative(registry, key=key, profile="ptah", platform="discord", chat_id="c1", thread_id="t1", project_slug="harness-starter", session_id="old", request_signature="ptah:goal")
    row["open_sessions"].append({"session_id": "new", "role": "representative", "state": "open", "started_at": "2026-07-05T01:00:00Z", "last_activity_at": "2026-07-05T01:00:00Z"})
    save_registry(runs / "session_registry.json", registry)
    policy = lifecycle_runner.apply_session_policy(
        {"root_goal": "goal", "project_slug": "harness-starter", "platform": "discord", "chat_id": "c1", "thread_id": "t1", "session_id": "fresh"},
        {"selected_profile": "ptah"},
        runs,
    )
    assert policy["reclaim_manifest_ref"] == ".harness/project/runs/session_reclaim_manifest.json"
    assert (runs / "session_registry.json").exists()
    assert (runs / "session_reclaim_manifest.json").exists()


def test_followup_packet_reuses_representative(tmp_path, monkeypatch):
    monkeypatch.setattr(lifecycle_runner, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(lifecycle_runner, "read_hermes_sessions_json", lambda: {"seen": True, "data": {}})
    monkeypatch.setattr(lifecycle_runner, "read_hermes_state_db_summary", lambda session_ids: {"seen": True, "sessions": {}})
    runs = tmp_path / ".harness" / "project" / "runs"
    first = lifecycle_runner.apply_session_policy(
        {"root_goal": "same goal", "project_slug": "harness-starter", "platform": "discord", "chat_id": "c1", "thread_id": "t1", "session_id": "s1"},
        {"selected_profile": "ptah"},
        runs,
    )
    second = lifecycle_runner.apply_session_policy(
        {"root_goal": "same goal", "request_signature": "ptah:same goal", "project_slug": "harness-starter", "platform": "discord", "chat_id": "c1", "thread_id": "t1", "response_received_at": "2026-07-05T00:00:00Z"},
        {"selected_profile": "ptah"},
        runs,
    )
    assert first["representative_session_id"] == "s1"
    assert second["reuse_decision"] == "reuse"
    assert second["representative_session_id"] == "s1"


def test_route_gate_output_includes_session_policy(tmp_path):
    runs = tmp_path / ".harness" / "project" / "runs"
    key = lane_key(profile="ptah", platform="discord", chat_id="c1", thread_id="t1", project_slug="harness-starter")
    registry = load_registry(runs / "session_registry.json")
    upsert_representative(registry, key=key, profile="ptah", platform="discord", chat_id="c1", thread_id="t1", project_slug="harness-starter", session_id="s1", request_signature="ptah:goal")
    save_registry(runs / "session_registry.json", registry)
    policy = cps_preflight_route_gate.build_session_policy({"project_slug": "harness-starter", "platform": "discord", "chat_id": "c1", "thread_id": "t1"}, tmp_path, "ptah")
    assert policy["lane_key"] == key
    assert policy["representative_session_id"] == "s1"
    assert policy["reuse_decision"] == "reuse"
