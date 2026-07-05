import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

REPO = Path(__file__).resolve().parent
TOOLS = REPO / ".harness" / "hermes" / "tools"
sys.path.insert(0, str(TOOLS))
MODULE_PATH = TOOLS / "cps_preflight_route_gate.py"
LIFECYCLE_PATH = TOOLS / "lifecycle_runner.py"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


preflight = load_module("cps_preflight_route_gate", MODULE_PATH)
lifecycle = load_module("lifecycle_runner", LIFECYCLE_PATH)


class TestCpsPreflightVerificationGate(TestCase):
    def candidate(self, verification, p=None, s=None, e=None):
        packet = {
            "root_goal": "verification gate test",
            "CPS": {
                "C": "one C",
                "P1": "problem one",
                "S1": "solution one",
            },
            "verification": verification,
        }
        built = preflight.build_candidate(packet, Path("packet.yaml"), REPO)
        if p is not None:
            built["P?"] = p
        if s is not None:
            built["S?"] = s
        if e is not None:
            built["E?"] = e
        return built

    def route_gap(self, verification, p=None, s=None, e=None):
        route = preflight.adjudicate(self.candidate(verification, p, s, e))
        return route["verification_gate"]["gap_class"], route

    def test_build_candidate_promotes_packet_verification_block(self):
        verification = {
            "execution_kind": "execution-needed",
            "verification_S": ["S1"],
            "evidence_mode": "readback-backed",
            "minimum_evidence": {"readback-backed": {"changed_path": "x", "closure_line_ref": "x:1"}},
        }
        candidate = self.candidate(verification)
        self.assertEqual(candidate["verification"], verification)

    def test_execution_needed_without_verification_s_holds_with_gap_class(self):
        gap, route = self.route_gap({"execution_kind": "execution-needed", "evidence_mode": "source-backed"})
        self.assertEqual(gap, "verification_s_missing")
        self.assertEqual(route["status"], "hold")
        self.assertIn("verification_s_missing", route["gap_scan"]["missing"])

    def test_missing_evidence_mode_holds_with_gap_class(self):
        gap, route = self.route_gap({"execution_kind": "execution-needed", "verification_S": ["S1"]})
        self.assertEqual(gap, "evidence_mode_missing")
        self.assertEqual(route["C_boundary"], "HOLD")

    def test_readback_without_closure_line_ref_is_minimum_evidence_missing(self):
        gap, route = self.route_gap({
            "execution_kind": "execution-needed",
            "verification_S": ["S1"],
            "evidence_mode": "readback-backed",
            "minimum_evidence": {"readback-backed": {"changed_path": "x"}},
        })
        self.assertEqual(gap, "minimum_evidence_missing")
        self.assertEqual(route["verification_gate"]["minimum_evidence_check"], "fail")

    def test_accepted_s_and_evidence_without_p_is_problem_p_missing(self):
        gap, _ = self.route_gap({
            "execution_kind": "execution-needed",
            "verification_S": ["S1"],
            "evidence_mode": "source-backed",
            "minimum_evidence": {"source-backed": {"source_ref": "ref", "application_reason": "reason"}},
        }, p={}, s={"S1": "solution one"}, e=[])
        self.assertEqual(gap, "problem_p_missing")

    def test_missing_p_to_s_edge_is_p_s_trace_missing(self):
        gap, _ = self.route_gap({
            "execution_kind": "execution-needed",
            "verification_S": ["S2"],
            "evidence_mode": "trace-backed",
            "minimum_evidence": {"trace-backed": {"p_to_s_ref": "P2 -> S2", "artifact_ref": "trace"}},
        }, p={"P2": "problem two"}, s={"S2": "solution two"}, e=[])
        self.assertEqual(gap, "p_s_trace_missing")

    def test_orphan_p_present_gap_class(self):
        gap, _ = self.route_gap({
            "execution_kind": "execution-needed",
            "verification_S": ["S1"],
            "evidence_mode": "source-backed",
            "minimum_evidence": {"source-backed": {"source_ref": "ref", "application_reason": "reason"}},
        }, p={"P1": "problem one", "P3": "orphan"}, s={"S1": "solution one"}, e=["P1 -> S1"])
        self.assertEqual(gap, "orphan_p_present")

    def test_verification_gate_continues_into_reducer_probe_and_dispatch(self):
        route = preflight.adjudicate(self.candidate({
            "execution_kind": "execution-needed",
            "verification_S": ["S1"],
            "evidence_mode": "source-backed",
            "minimum_evidence": {"source-backed": {"source_ref": "ref", "application_reason": "reason"}},
        }))
        reducer_input = preflight.build_reducer_input(route, {})
        reducer_result = {
            "status": "pass",
            "revised_C": route["C"],
            "revised_P": route["accepted_P"],
            "revised_S": route["accepted_S"],
            "revised_E": route["E"],
            "final_selected_agents": route["selected_agents"],
            "local_body_scope": {"hermes-kann": True},
        }
        probe = preflight.build_probe("hermes-kann", route, route["selected_agents"]["hermes-kann"], reducer_result)
        dispatch = preflight.build_local_body_dispatch(route, reducer_result, {}, route["selected_agents"])
        self.assertEqual(reducer_input["verification_gate"], route["verification_gate"])
        self.assertEqual(probe["verification_gate"], route["verification_gate"])
        self.assertEqual(dispatch["verification_gate"], route["verification_gate"])

    def test_handoff_packets_require_cps_reason_and_exclude_raw_transcript_fields(self):
        route = {
            "C": {"C1": "implement code"},
            "accepted_P": {"P1": "route_request_to_minimal_agent_set"},
            "accepted_S": {"S1": "maat_route_gate"},
            "E": ["P1 -> S1"],
            "verification_gate": {"gap_class": "none"},
            "AC_mode": "route_gate_only",
            "audit_plan": {"mode": "targeted"},
            "selected_agents": {"ptah": {"P": ["P1"], "S": ["S1"]}},
        }
        draft_probe = preflight.build_agent_draft_probe("ptah", route)
        reducer_result = {
            "revised_C": route["C"],
            "revised_P": route["accepted_P"],
            "revised_S": route["accepted_S"],
            "revised_E": route["E"],
        }
        probe = preflight.build_probe("ptah", route, route["selected_agents"]["ptah"], reducer_result)
        packet = {
            "task_AC": ["AC1"],
            "owner_approval_boundary": "owner",
            "source_refs": ["src"],
            "artifact_refs": ["art"],
            "messages": [{"role": "user", "content": "entire conversation"}],
            "history": ["h1", "h2"],
            "raw_transcript": "full transcript should not pass",
            "conversation": "all prior chat",
        }
        local_body = preflight.build_local_body("ptah", probe, packet, Path("packet.json"))
        self.assertTrue(draft_probe["profile_call_requires_cps_reason"])
        self.assertTrue(probe["profile_call_requires_cps_reason"])
        self.assertNotIn("messages", local_body)
        self.assertNotIn("history", local_body)
        self.assertNotIn("raw_transcript", local_body)
        self.assertNotIn("conversation", local_body)

    def test_run_marks_ok_when_final_judgment_passes_despite_route_hold(self):
        chain = {
            "candidate": {"schema": "candidate"},
            "route": {
                "status": "hold",
                "C_boundary": "HOLD",
                "selected_agents": {"thoth": {"response": "need_local_body"}},
                "audit_plan": {},
                "prohibitions": [],
                "verification_gate": {"gap_class": "orphan_p_present"},
                "final_audit_needed": False,
                "C": {"C1": "implement code"},
            },
            "draft_probes": {},
            "probe_responses": {},
            "reducer_input": {},
            "reducer_result": {
                "status": "pass",
                "revised_C": {"C1": "implement code"},
                "revised_P": {"P6": "bounded_implementation_needed"},
                "revised_S": {"Sx": "thoth.local_body"},
                "revised_E": ["P6 -> thoth.local_body"],
                "final_selected_agents": {"thoth": {"selected": True}},
                "local_body_scope": {"thoth": {"granted": True}},
            },
            "probes": {},
            "local_bodies": {},
            "local_body_dispatch": {},
            "contribute_cps": {"Goal_closure": {"status": "pass", "reason": "closed"}},
            "final_judgment": {"status": "pass", "Goal_closure": {"status": "pass", "reason": "closed"}},
            "hold_gap_loop": {"status": "closed", "missing_evidence": []},
            "final_selected_agents": {"thoth": {"selected": True}},
        }
        out_dir = REPO / ".harness" / "project" / "runs" / "test_route_gate_usable"
        packet = REPO / ".harness" / "project" / "runs" / "test_route_gate_usable_packet.json"
        packet.parent.mkdir(parents=True, exist_ok=True)
        packet.write_text(json.dumps({"root_goal": "implement code"}), encoding="utf-8")
        try:
            with patch.object(preflight, "_load_packet", return_value={"root_goal": "implement code"}), \
                 patch.object(preflight, "build_candidate", return_value={"schema": "candidate"}), \
                 patch.object(preflight, "execute_preflight_chain", return_value=chain), \
                 patch.object(preflight, "max_reentry_iterations", return_value=0):
                result = preflight.run(packet, out_dir, REPO, mode="live-maat")
            self.assertTrue(result["ok"])
            self.assertEqual(result["final_output"]["status"], "pass")
            self.assertEqual(result["route_gate"]["status"], "hold")
        finally:
            packet.unlink(missing_ok=True)
            if out_dir.exists():
                for child in out_dir.iterdir():
                    child.unlink(missing_ok=True)
                out_dir.rmdir()

    def test_lifecycle_delegate_records_preflight_verification_gate(self):
        preflight_result = {
            "ok": True,
            "out_dir": "runs/preflight",
            "route_gate": {
                "selected_agents": {"ptah": {"P": ["P1"], "S": ["S1"], "response": "need_local_body"}},
                "verification_gate": {"gap_class": "none", "evidence_mode": "source-backed"},
            },
        }
        packet = REPO / ".harness" / "project" / "runs" / "test_cps_delegate_packet.json"
        packet.parent.mkdir(parents=True, exist_ok=True)
        packet.write_text(json.dumps({"root_goal": "implement code"}), encoding="utf-8")
        completed = subprocess.CompletedProcess(["preflight"], 0, json.dumps(preflight_result), "")
        with patch.object(lifecycle, "REPO_ROOT", REPO), patch.object(lifecycle.subprocess, "run", return_value=completed):
            self.assertEqual(lifecycle.do_delegate(str(packet)), 0)
        decision_path = REPO / ".harness" / "project" / "runs" / "delegation_decision.json"
        decision = json.loads(decision_path.read_text())
        self.assertEqual(decision["preflight_verification_gate"], preflight_result["route_gate"]["verification_gate"])
        for path in (packet, decision_path, REPO / ".harness" / "project" / "runs" / "last_preflight-route-gate.log"):
            path.unlink(missing_ok=True)

    def test_lifecycle_delegate_writes_handoff_snapshot(self):
        preflight_result = {
            "ok": True,
            "out_dir": "runs/preflight",
            "route_gate": {
                "selected_agents": {"ptah": {"P": ["P1"], "S": ["S1"], "response": "need_local_body"}},
                "verification_gate": {"gap_class": "none", "evidence_mode": "source-backed"},
            },
        }
        packet = REPO / ".harness" / "project" / "runs" / "test_handoff_snapshot_packet.json"
        packet.parent.mkdir(parents=True, exist_ok=True)
        packet.write_text(json.dumps({
            "root_goal": "implement code",
            "run_id": "run-123",
            "token_budget_remaining": 9123,
            "context_remaining_pct": 61,
        }), encoding="utf-8")
        completed = subprocess.CompletedProcess(["preflight"], 0, json.dumps(preflight_result), "")
        with patch.object(lifecycle, "REPO_ROOT", REPO), patch.object(lifecycle.subprocess, "run", return_value=completed):
            self.assertEqual(lifecycle.do_delegate(str(packet)), 0)
        snapshot_path = REPO / ".harness" / "project" / "runs" / "handoff_snapshot.json"
        snapshot = json.loads(snapshot_path.read_text())
        self.assertEqual(snapshot["task_id"], "run-123")
        self.assertEqual(snapshot["expected_next_hop"], "ptah")
        self.assertEqual(snapshot["current_owner"], "hermes-kann")
        self.assertEqual(snapshot["token_budget_remaining"], 9123)
        self.assertEqual(snapshot["context_remaining_pct"], 61)
        self.assertFalse(snapshot["anomaly_flag"])
        self.assertFalse((REPO / ".harness" / "project" / "runs" / "handoff_snapshot.prev1.json").exists())
        for path in (packet, snapshot_path, REPO / ".harness" / "project" / "runs" / "delegation_decision.json", REPO / ".harness" / "project" / "runs" / "last_preflight-route-gate.log"):
            path.unlink(missing_ok=True)

    def test_lifecycle_delegate_rotates_handoff_snapshots_with_three_file_cap(self):
        preflight_result = {
            "ok": True,
            "out_dir": "runs/preflight",
            "route_gate": {
                "selected_agents": {"ptah": {"P": ["P1"], "S": ["S1"], "response": "need_local_body"}},
                "verification_gate": {"gap_class": "none", "evidence_mode": "source-backed"},
            },
        }
        completed = subprocess.CompletedProcess(["preflight"], 0, json.dumps(preflight_result), "")
        packets = []
        try:
            with patch.object(lifecycle, "REPO_ROOT", REPO), patch.object(lifecycle.subprocess, "run", return_value=completed):
                for idx in range(1, 5):
                    packet = REPO / ".harness" / "project" / "runs" / f"test_handoff_snapshot_packet_{idx}.json"
                    packet.parent.mkdir(parents=True, exist_ok=True)
                    packet.write_text(json.dumps({
                        "root_goal": "implement code",
                        "run_id": f"run-{idx}",
                    }), encoding="utf-8")
                    packets.append(packet)
                    self.assertEqual(lifecycle.do_delegate(str(packet)), 0)
            runs_dir = REPO / ".harness" / "project" / "runs"
            current = json.loads((runs_dir / "handoff_snapshot.json").read_text())
            prev1 = json.loads((runs_dir / "handoff_snapshot.prev1.json").read_text())
            prev2 = json.loads((runs_dir / "handoff_snapshot.prev2.json").read_text())
            self.assertEqual(current["task_id"], "run-4")
            self.assertEqual(prev1["task_id"], "run-3")
            self.assertEqual(prev2["task_id"], "run-2")
            self.assertFalse((runs_dir / "handoff_snapshot.prev3.json").exists())
        finally:
            for path in [
                *packets,
                REPO / ".harness" / "project" / "runs" / "handoff_snapshot.json",
                REPO / ".harness" / "project" / "runs" / "handoff_snapshot.prev1.json",
                REPO / ".harness" / "project" / "runs" / "handoff_snapshot.prev2.json",
                REPO / ".harness" / "project" / "runs" / "handoff_snapshot.prev3.json",
                REPO / ".harness" / "project" / "runs" / "delegation_decision.json",
                REPO / ".harness" / "project" / "runs" / "last_preflight-route-gate.log",
            ]:
                path.unlink(missing_ok=True)

    def test_lifecycle_delegate_reuses_previous_route_as_follow_up(self):
        preflight_result = {
            "ok": True,
            "out_dir": "runs/preflight",
            "route_gate": {
                "selected_agents": {"ptah": {"P": ["P1"], "S": ["S1"], "response": "need_local_body"}},
                "verification_gate": {"gap_class": "none", "evidence_mode": "source-backed"},
            },
        }
        completed = subprocess.CompletedProcess(["preflight"], 0, json.dumps(preflight_result), "")
        runs_dir = REPO / ".harness" / "project" / "runs"
        packet1 = runs_dir / "test_follow_up_packet_1.json"
        packet2 = runs_dir / "test_follow_up_packet_2.json"
        cleanup = [
            packet1,
            packet2,
            runs_dir / "handoff_snapshot.json",
            runs_dir / "handoff_snapshot.prev1.json",
            runs_dir / "handoff_snapshot.prev2.json",
            runs_dir / "handoff_snapshot.prev3.json",
            runs_dir / "delegation_decision.json",
            runs_dir / "last_preflight-route-gate.log",
            runs_dir / "handoff_continuity.json",
            runs_dir / "hu_handoff_packet.json",
            runs_dir / "hu_handoff_analysis.json",
        ]
        try:
            packet1.parent.mkdir(parents=True, exist_ok=True)
            packet1.write_text(json.dumps({
                "root_goal": "implement code",
                "run_id": "follow-up-1",
                "snapshot_at": "2026-07-04T10:00:00Z",
            }), encoding="utf-8")
            packet2.write_text(json.dumps({
                "root_goal": "implement code",
                "run_id": "follow-up-2",
                "snapshot_at": "2026-07-04T10:09:00Z",
                "response_received_at": "2026-07-04T10:00:30Z",
            }), encoding="utf-8")
            with patch.object(lifecycle, "REPO_ROOT", REPO), patch.object(lifecycle.subprocess, "run", return_value=completed) as mock_run:
                self.assertEqual(lifecycle.do_delegate(str(packet1)), 0)
                self.assertEqual(lifecycle.do_delegate(str(packet2)), 0)
            self.assertEqual(mock_run.call_count, 1)
            continuity = json.loads((runs_dir / "handoff_continuity.json").read_text())
            self.assertEqual(continuity["status"], "follow_up")
            self.assertEqual(continuity["classification"], "reused_existing_handoff")
            self.assertEqual(continuity["previous_task_id"], "follow-up-1")
            self.assertEqual(continuity["current_task_id"], "follow-up-2")
            self.assertEqual(continuity["selected_profile"], "ptah")
            snapshot = json.loads((runs_dir / "handoff_snapshot.json").read_text())
            self.assertFalse(snapshot["anomaly_flag"])
            self.assertEqual(snapshot["current_stage"], "follow_up_linked")
            self.assertEqual(snapshot["expected_next_hop"], "ptah")
            self.assertEqual(snapshot["request_kind"], "follow_up")
            self.assertFalse((runs_dir / "hu_handoff_packet.json").exists())
            self.assertFalse((runs_dir / "hu_handoff_analysis.json").exists())
        finally:
            for path in cleanup:
                path.unlink(missing_ok=True)

    def test_build_hu_handoff_analysis_detects_duplicate_request_after_response(self):
        previous_snapshot = {
            "packet_ref": "/tmp/prev.json",
            "request_signature": "ptah:implement code",
            "expected_next_hop": "ptah",
        }
        current_snapshot = {
            "packet_ref": "/tmp/current.json",
            "request_signature": "ptah:implement code",
            "expected_next_hop": "ptah",
            "snapshot_at": "2026-07-04T10:09:00Z",
            "response_received_at": "2026-07-04T10:00:30Z",
        }
        hu_analysis = lifecycle.build_hu_handoff_analysis(current_snapshot, previous_snapshot)
        self.assertIsNotNone(hu_analysis)
        assert hu_analysis is not None
        self.assertEqual(hu_analysis["anomaly_type"], "duplicate_request_after_response")
        self.assertEqual(hu_analysis["idle_gap_seconds"], 510)
        self.assertIn("same_request_signature_as_prev1", hu_analysis["risk_points"])
        self.assertIn("response_received_before_repeat_request", hu_analysis["risk_points"])
