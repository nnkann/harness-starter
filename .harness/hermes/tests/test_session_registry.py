from pathlib import Path
import sys

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

from session_registry import clear_orphan_route, enforce_profile_cap, lane_key, load_registry, mark_reclaim_candidate, save_registry, upsert_representative


def test_representative_insert_update(tmp_path):
    path = tmp_path / "session_registry.json"
    registry = load_registry(path)
    key = lane_key(profile="ptah", platform="discord", chat_id="c1", thread_id="t1", project_slug="harness-starter")
    row = upsert_representative(
        registry,
        key=key,
        profile="ptah",
        platform="discord",
        chat_id="c1",
        thread_id="t1",
        project_slug="harness-starter",
        session_id="s1",
        request_signature="ptah:goal",
        now_iso="2026-07-05T00:00:00Z",
    )
    save_registry(path, registry)
    loaded = load_registry(path)
    assert row["representative_session_id"] == "s1"
    assert loaded["lanes"][key]["open_sessions"][0]["role"] == "representative"


def test_duplicate_candidate_recording():
    registry = load_registry(Path("missing.json"))
    key = lane_key(profile="ptah", platform="discord", chat_id="c1", thread_id="t1", project_slug="harness-starter")
    upsert_representative(registry, key=key, profile="ptah", platform="discord", chat_id="c1", thread_id="t1", project_slug="harness-starter", session_id="s1", request_signature="ptah:goal")
    row = mark_reclaim_candidate(registry, key=key, session_id="s1", reason="duplicate_open", state="duplicate_open_present")
    assert row["state"] == "duplicate_open_present"
    assert row["reclaim_candidates"][0]["reason"] == "duplicate_open"


def test_orphan_clear():
    registry = load_registry(Path("missing.json"))
    key = lane_key(profile="maat", platform="discord", chat_id="c1", thread_id="t1", project_slug="harness-starter")
    upsert_representative(registry, key=key, profile="maat", platform="discord", chat_id="c1", thread_id="t1", project_slug="harness-starter", session_id="s1", request_signature="maat:goal")
    row = clear_orphan_route(registry, key=key, evidence_refs=["state.db"])
    assert row["representative_session_id"] is None
    assert row["state"] == "orphan_route_present"
    assert row["reclaim_candidates"][0]["reason"] == "orphan_route"


def test_profile_cap_ranking_order():
    registry = load_registry(Path("missing.json"))
    for idx, state in enumerate(["stale_open", "duplicate_open_present", "orphan_route_present"]):
        key = lane_key(profile="sia", platform="local", chat_id=str(idx), thread_id=None, project_slug="harness-starter")
        upsert_representative(registry, key=key, profile="sia", platform="local", chat_id=str(idx), thread_id=None, project_slug="harness-starter", session_id=f"s{idx}", request_signature="sia:goal", state=state)
    result = enforce_profile_cap(registry, profile="sia", caps={"sia": 1})
    assert result["status"] == "candidates_available"
    assert [c["state"] for c in result["ranked_candidates"]] == ["orphan_route_present", "duplicate_open_present", "stale_open"]
