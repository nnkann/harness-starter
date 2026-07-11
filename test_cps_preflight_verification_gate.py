import importlib.util
import json
import subprocess
import sys
import tempfile
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
    def test_configured_contract_is_active_cps_preflight_route_gate_contract(self):
        self.assertTrue(preflight.CONTRACT_PATH.is_file())
        contract = preflight.CONTRACT_PATH.read_text(encoding="utf-8")
        self.assertIn("title: CPS Preflight Route-Gate Work Contract", contract)
        self.assertIn("status: active", contract)
        self.assertIn("c: cps_preflight_route_gate", contract)

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

    def test_seed_relations_are_separate_from_verification_links(self):
        packet = {
            "root_goal": "implement route gate",
            "source_refs": ["/canonical/decision.md", ".harness/hermes/tools/cps_preflight_route_gate.py"],
            "CPS": {"C": "one C", "P1": "problem", "S1": "solution", "E": ["P1 -> S1"]},
        }
        candidate = preflight.build_candidate(packet, Path("packet.json"), REPO)
        graph = candidate["cps_seed_graph"]
        self.assertNotIn("edges", graph)
        self.assertEqual(graph["seed_relations"][0]["to"], "/canonical/decision.md")
        self.assertEqual(candidate["verification_links"], ["P1 -> S1"])
        route = preflight.adjudicate(candidate)
        self.assertEqual(route["E"], route["verification_links"])

    def test_trace_has_no_false_memory_lookup_and_uses_delta_payloads(self):
        candidate = preflight.build_candidate({"root_goal": "implement code"}, Path("packet.json"), REPO)
        events = candidate["cps_trace_events"]
        self.assertEqual([event["event_type"] for event in events].count("seed_created"), 1)
        self.assertNotIn("memory_lookup_started", [event["event_type"] for event in events])
        self.assertNotIn("memory_match_attached", [event["event_type"] for event in events])
        self.assertNotIn("current_state", events[0])
        self.assertIn("seed_delta", events[0]["event_payload"])

    def test_memory_match_requires_current_readable_source_and_preserves_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "decision.md"
            source.write_text("current decision", encoding="utf-8")
            content_hash = preflight.hashlib.sha256(source.read_bytes()).hexdigest()
            result = preflight.normalize_memory_lookup_result({
                "lookup_ref": "lookup:1",
                "gbrain": {"matches": [{
                    "source_ref": str(source),
                    "source_revision": "revision-1",
                    "content_hash": content_hash,
                    "freshness": "2026-07-11T00:00:00Z",
                    "lifecycle": "validated",
                    "supersedes": "revision-0",
                }]},
            })
        self.assertEqual(result["status"], "match")
        self.assertTrue(result["active_only"])
        self.assertEqual(result["matches"], [{
            "layer": "gbrain",
            "source_ref": str(source),
            "source_revision": "revision-1",
            "content_hash": content_hash,
            "freshness": "2026-07-11T00:00:00Z",
            "lifecycle": "validated",
            "supersedes": "revision-0",
        }])

    def test_memory_no_match_and_unavailable_are_explicit(self):
        no_match = preflight.normalize_memory_lookup_result({
            "honcho": {"status": "no_match", "matches": []},
            "gbrain": {"status": "no_match", "matches": []},
        })
        unavailable = preflight.normalize_memory_lookup_result({
            "honcho": "unstructured retrieval text without source provenance",
            "gbrain": [],
            "harness-brain": RuntimeError("reader unavailable"),
        })
        self.assertEqual(no_match["status"], "no_match")
        self.assertEqual(no_match["matches"], [])
        self.assertEqual(unavailable["status"], "unavailable")
        self.assertEqual(unavailable["matches"], [])

    def test_memory_active_only_excludes_inactive_unknown_and_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "decision.md"
            source.write_text("current", encoding="utf-8")
            common = {
                "source_ref": str(source), "source_revision": "rev",
                "content_hash": preflight.hashlib.sha256(source.read_bytes()).hexdigest(),
                "freshness": "2026-07-11T00:00:00Z", "supersedes": None,
            }
            records = [{**common, "lifecycle": lifecycle} for lifecycle in (
                "stale", "conflict", "withdrawn", "candidate", "unknown",
            )]
            records.append({**common, "lifecycle": "promoted", "content_hash": "wrong"})
            result = preflight.normalize_memory_lookup_result({"harness-brain": records})
        self.assertEqual(result["status"], "no_match")
        self.assertEqual(result["matches"], [])
        self.assertEqual(result["excluded_count"], len(records))

    def test_candidate_attaches_only_normalized_match_and_emits_no_false_match_trace(self):
        packet = {"root_goal": "implement code", "memory_lookup_result": {
            "lookup_ref": "lookup:empty", "honcho": [],
        }}
        candidate = preflight.build_candidate(packet, Path("packet.json"), REPO)
        memory = candidate["route_enrichment"]["memory"]
        events = [event["event_type"] for event in candidate["cps_trace_events"]]
        self.assertEqual(memory["status"], "unavailable")
        self.assertEqual(memory["matches"], [])
        self.assertIn("memory_lookup_started", events)
        self.assertNotIn("memory_match_attached", events)

    def test_reentry_candidate_preserves_seed_graph_and_trace(self):
        original = self.candidate({})
        reentry = preflight.build_candidate_from_reentry({
            "revised_C": {"C1": "close gap"}, "revised_P": {"P1": "problem"},
            "revised_S": {"S1": "solution"}, "revised_E": ["P1 -> S1"],
            "missing_evidence": ["evidence"], "iteration": 1, "packet_ref": "packet.json",
        }, Path("packet.json"), REPO, original)
        self.assertIs(reentry["cps_seed_graph"], original["cps_seed_graph"])
        self.assertEqual(reentry["cps_trace_events"], original["cps_trace_events"])
        self.assertEqual(reentry["reentry"]["iteration"], 1)

    def test_maat_inputs_are_body_free_and_reference_manifests(self):
        candidate = self.candidate({})
        candidate["agent_body_map"] = {"ptah": {"secret_body": "must not relay"}}
        manifests = preflight.build_body_manifest(["ptah"])
        prompt = json.loads(preflight._live_maat_prompt(candidate, {"raw_transcript": "secret"}, manifests))
        serialized = json.dumps(prompt)
        self.assertNotIn("agent_body_map", serialized)
        self.assertNotIn("secret_body", serialized)
        self.assertNotIn("raw_transcript", serialized)
        self.assertEqual(prompt["body_manifest"], manifests)
        self.assertIn("body_manifest_ids", prompt["required_response_schema"]["selected_agents"]["ptah"])
        reducer = preflight.build_reducer_input(preflight.adjudicate(candidate), {}, manifests)
        self.assertEqual(reducer["body_manifest"], manifests)
        self.assertNotIn("agent_body_map", reducer)

    def test_explicit_route_candidates_narrow_manifest_catalog(self):
        packet = {"route_candidates": ["ptah", {"agent": "anubis"}, {"profile": "seshat"}, "maat"]}
        catalog = preflight.select_route_candidate_catalog(packet, {})
        self.assertEqual(catalog["selected_candidate_ids"], ["ptah", "anubis", "seshat"])
        self.assertEqual(catalog["candidate_count"], 3)
        self.assertEqual(catalog["manifest_count"], 3)
        self.assertEqual(catalog["excluded_profile_count"], len(preflight.PROFILES) - 1 - 3)

    def test_candidate_s_values_narrow_to_referenced_known_profiles(self):
        candidate = {"S?": {"S1": "ptah apply", "S2": "anubis evidence", "S3": "unknown lane"}}
        catalog = preflight.select_route_candidate_catalog({}, candidate)
        self.assertEqual(catalog["selected_candidate_ids"], ["ptah", "anubis"])

    def test_structural_fallback_selects_only_relevant_candidates(self):
        packet = {
            "source_refs": ["docs/contract.md"],
            "verification": {"execution_kind": "execution-needed"},
            "memory_continuity": {"required": True},
        }
        catalog = preflight.select_route_candidate_catalog(packet, {})
        self.assertEqual(catalog["selected_candidate_ids"], ["seshat", "anubis", "sia"])
        mutation = preflight.select_route_candidate_catalog({"mutation_scope": ["runtime"]}, {})
        self.assertEqual(mutation["selected_candidate_ids"], ["ptah"])

    def test_execute_chain_uses_narrow_catalog_and_keeps_maat_inputs_body_free(self):
        packet = {"root_goal": "bounded task", "mutation_scope": ["runtime"], "route_candidates": ["ptah", "anubis", "seshat"]}
        candidate = preflight.build_candidate(packet, Path("packet.json"), REPO)
        route = preflight.adjudicate(candidate)
        with patch.object(preflight, "invoke_live_maat", return_value=route) as route_maat, \
             patch.object(preflight, "probe_agents_as_arrive", return_value=({}, {})), \
             patch.object(preflight, "invoke_maat_reducer", return_value={"status": "hold", "final_selected_agents": {}, "local_body_scope": {}}), \
             patch.object(preflight, "invoke_maat_final_judgment", return_value={"status": "hold", "Goal_closure": {"status": "hold"}}):
            chain = preflight.execute_preflight_chain(packet, Path("packet.json"), REPO, "live-maat", candidate)
        manifests = route_maat.call_args.kwargs["body_manifest"]
        self.assertEqual(list(manifests), ["ptah", "anubis", "seshat"])
        self.assertEqual(chain["route_candidate_catalog"]["manifest_count"], 3)
        prompt = preflight._live_maat_prompt(candidate, packet, manifests)
        self.assertNotIn("body:thoth:v1", prompt)
        self.assertNotIn("agent_body_map", prompt)

    def test_dispatch_trace_counts_selected_duplicate_unselected_and_no_maat_relay(self):
        bodies = {"ptah": {"schema": "body", "value": "x"}}
        manifests = preflight.build_body_manifest(["ptah", "anubis"])
        trace = preflight.build_local_body_dispatch(
            {"verification_gate": {}}, {"status": "pass", "local_body_scope": {"ptah": True}},
            bodies, {"ptah": {"body_manifest_ids": [manifests["ptah"]["body_manifest_id"]]}}, manifests,
        )
        aggregate = trace["aggregate"]
        self.assertEqual(aggregate["direct_dispatch_count"], 1)
        self.assertEqual(aggregate["duplicate_dispatch_count"], 0)
        self.assertEqual(aggregate["unselected_dispatch_count"], 0)
        self.assertEqual(aggregate["maat_body_relay_count"], 0)
        self.assertGreater(aggregate["token_estimate"], 0)
        self.assertTrue(trace["dispatch"]["ptah"]["body_hash"])

    def test_selective_maat_escalation_uses_explicit_signals(self):
        short = preflight.build_candidate({"root_goal": "rewrite this sentence"}, Path("packet.json"), REPO)
        self.assertFalse(short["route_enrichment"]["selective_maat_escalation"]["needed"])
        scoped = preflight.build_candidate({
            "root_goal": "change runtime", "mutation_scope": ["runtime"],
            "route_candidates": ["ptah", "anubis"], "required_evidence_floor": "test-backed",
        }, Path("packet.json"), REPO)
        reasons = scoped["route_enrichment"]["selective_maat_escalation"]["reasons"]
        self.assertIn("mutation_scope_present", reasons)
        self.assertIn("multiple_route_candidates", reasons)
        self.assertIn("verification_or_evidence_floor_required", reasons)

    def test_short_local_contract_bypasses_maat_reducer_and_final_maat(self):
        packet = {
            "root_goal": "rewrite this sentence",
            "inline_response_contract": {"response": "Rewritten sentence."},
        }
        candidate = preflight.build_candidate(packet, Path("packet.json"), REPO)
        with patch.object(preflight, "invoke_live_maat") as route_maat, \
             patch.object(preflight, "invoke_maat_reducer") as reducer, \
             patch.object(preflight, "invoke_maat_final_judgment") as final_maat:
            chain = preflight.execute_preflight_chain(packet, Path("packet.json"), REPO, "live-maat", candidate)
        route_maat.assert_not_called()
        reducer.assert_not_called()
        final_maat.assert_not_called()
        self.assertEqual(chain["route"]["wire"], "short_cps")
        self.assertEqual(chain["final_judgment"]["status"], "pass")

    def test_mutation_verification_multi_agent_and_ssot_uncertainty_route_to_maat(self):
        signals = (
            {"mutation_scope": ["runtime"]},
            {"required_evidence_floor": "test-backed"},
            {"route_candidates": ["ptah", "anubis"]},
            {"ssot_authority_uncertainty": True},
        )
        for signal in signals:
            packet = {"root_goal": "bounded task", **signal}
            candidate = preflight.build_candidate(packet, Path("packet.json"), REPO)
            with self.subTest(signal=signal), patch.object(preflight, "invoke_live_maat", return_value=preflight.adjudicate(candidate)) as route_maat, \
                 patch.object(preflight, "probe_agents_as_arrive", return_value=({}, {})), \
                 patch.object(preflight, "invoke_maat_reducer", return_value={"status": "hold", "final_selected_agents": {}, "local_body_scope": {}}), \
                 patch.object(preflight, "invoke_maat_final_judgment", return_value={"status": "hold", "Goal_closure": {"status": "hold"}}):
                preflight.execute_preflight_chain(packet, Path("packet.json"), REPO, "live-maat", candidate)
                route_maat.assert_called_once()

    def test_explicit_agent_work_without_route_signal_holds_without_implicit_maat(self):
        packet = {
            "root_goal": "agent work",
            "CPS": {"C": "one C", "P1": "implement", "S1": "ptah apply", "E": ["P1 -> S1"]},
        }
        candidate = preflight.build_candidate(packet, Path("packet.json"), REPO)
        with patch.object(preflight, "invoke_live_maat") as route_maat:
            chain = preflight.execute_preflight_chain(packet, Path("packet.json"), REPO, "live-maat", candidate)
        route_maat.assert_not_called()
        self.assertEqual(chain["final_judgment"]["status"], "hold")
        self.assertIn("route_gate_signal_missing", chain["final_judgment"]["missing_evidence"])

    def test_deterministic_run_records_one_reentry_and_terminal_closure(self):
        packet = {
            "root_goal": "change runtime",
            "mutation_scope": ["runtime"],
            "max_reentry_iterations": 1,
        }
        with tempfile.TemporaryDirectory() as tmp:
            packet_path = Path(tmp) / "packet.json"
            packet_path.write_text(json.dumps(packet), encoding="utf-8")
            result = preflight.run(packet_path, Path(tmp) / "out", REPO, mode="deterministic")
        events = result["cps_trace_events"]
        reentries = [event for event in events if event["event_type"] == "reentry_started"]
        self.assertEqual(len(reentries), 1)
        self.assertEqual(reentries[0]["iteration"], 1)
        self.assertEqual(reentries[0]["parent_event_id"], events[events.index(reentries[0]) - 1]["event_id"])
        self.assertEqual(events[-1]["event_type"], "workflow_closed")
        self.assertEqual(events[-1]["parent_event_id"], reentries[0]["event_id"])

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

    def test_active_ac_ref_and_in_scope_mutation_is_git_closure_candidate(self):
        packet = {
            "task_AC": [{"id": "AC1", "text": "change gate"}],
            "allowed_paths": [".harness/hermes/tools/cps_preflight_route_gate.py"],
            "mutation_manifest": [{"path": ".harness/hermes/tools/cps_preflight_route_gate.py", "AC_ref": "AC1"}],
            "owner_approval_boundary": {"git_commit": True, "git_push": True},
        }
        closure = preflight.classify_mutation_closure(packet)
        self.assertEqual(closure["active_AC_refs"], ["AC1"])
        self.assertEqual(closure["git_closure_candidates"][0]["path"], packet["mutation_manifest"][0]["path"])
        self.assertEqual(closure["status"], "candidate")

    def test_no_ac_ref_is_excluded_without_hold_or_another_c(self):
        packet = {
            "task_AC": ["AC1"], "mutation_scope": ["tmp/output.txt"],
            "mutation_manifest": [{"path": "tmp/output.txt"}],
            "owner_approval_boundary": {"git_commit": True, "git_push": True},
        }
        closure = preflight.classify_mutation_closure(packet)
        self.assertEqual(closure["unclaimed_mutations"][0]["path"], "tmp/output.txt")
        self.assertEqual(closure["excluded_mutations"][0]["reason"], "missing_AC_ref")
        self.assertEqual(closure["hold_reasons"], [])
        self.assertNotIn("another_C", json.dumps(closure))

    def test_unclaimed_conflict_evidence_holds(self):
        closure = preflight.classify_mutation_closure({
            "task_AC": ["AC1"], "mutation_scope": ["x.py"],
            "mutation_manifest": [{"path": "x.py", "conflict_evidence": "overlaps owner patch"}],
        })
        self.assertEqual(closure["status"], "hold")
        self.assertEqual(closure["hold_reasons"][0]["reason"], "conflict_evidence")

    def test_ac_linked_out_of_scope_mutation_holds(self):
        closure = preflight.classify_mutation_closure({
            "CPS": {"AC": [{"id": "AC2"}]}, "allowed_paths": ["in.py"],
            "mutation_manifest": [{"path": "out.py", "AC_ref": "AC2"}],
        })
        self.assertEqual(closure["status"], "hold")
        self.assertEqual(closure["excluded_mutations"][0]["reason"], "scope_violation")

    def test_ephemeral_unclaimed_artifact_stays_excluded_without_hold(self):
        closure = preflight.classify_mutation_closure({
            "task_AC": ["AC1"], "mutation_scope": ["tmp/test.log"],
            "mutation_manifest": [{"path": "tmp/test.log", "disposition": "ephemeral"}],
        })
        self.assertEqual(closure["status"], "not_required")
        self.assertEqual(closure["unclaimed_mutations"][0]["disposition"], "ephemeral")
        self.assertEqual(closure["hold_reasons"], [])

    def test_disallowed_commit_push_boundary_prevents_candidate_status(self):
        packet = {
            "task_AC": ["AC1"], "allowed_paths": ["x.py"],
            "mutation_manifest": [{"path": "x.py", "AC_ref": "AC1"}],
            "owner_approval_boundary": {"git_commit": False, "git_push": False},
        }
        candidate = preflight.build_candidate(packet, Path("packet.json"), REPO)
        closure = candidate["mutation_closure"]
        self.assertEqual(closure["status"], "hold")
        self.assertEqual(closure["git_closure_candidates"], [])
        self.assertEqual(closure["excluded_mutations"][0]["reason"], "git_owner_boundary_disallowed")
        self.assertEqual(closure["hold_reasons"], [{
            "path": "x.py",
            "reason": "git_owner_boundary_disallowed",
            "evidence": {"git_commit": False, "git_push": False},
        }])

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
