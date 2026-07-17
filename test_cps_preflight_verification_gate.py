import importlib.util
import json
import hashlib
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
    def anchor_packet(self):
        source = REPO.parent / "harness-brain" / "projects" / REPO.name / "decisions" / "cps-memory-lifecycle-and-honcho-anchor.md"
        line_count = len(source.read_text(encoding="utf-8").splitlines())
        anchor = {"schema": "harness.honcho.cps_cluster.v1", "C": {"shape": "bounded"}}
        binding = {
            "canonical_source_locator": str(source),
            "canonical_source_readback": f"{source}:1-{line_count}",
            "current_source_revision": subprocess.check_output(["git", "-C", str(source.parent), "rev-parse", "HEAD"], text=True).strip(),
            "current_content_hash": hashlib.sha256(source.read_bytes()).hexdigest(),
            "canonical_section": f"{source}:75-108",
            "semantic_field_definition_coverage": {"schema": f"{source}:78", "C.shape": f"{source}:85"},
        }
        return {"semantic_anchor": anchor, "semantic_provenance_binding": binding, "route_candidates": ["ptah"]}

    def test_T18_derived_c_candidate_is_transient_non_authoritative_and_exactly_bound(self):
        binding = {
            "parent_work_id": "work-1", "parent_graph_ref": "graph:work-1", "parent_graph_revision": 3,
            "parent_graph_digest": "a" * 64, "blocked_receipt_ref": "run-1:4",
            "parent_edge_ref": "C1/P1", "return_to_node_ref": "C1",
        }
        candidate = preflight.build_derived_c_candidate(binding, ["run-1:2", "run-1:3"], same_c_recovery_exhausted=True)
        self.assertEqual(candidate["status"], "candidate")
        self.assertEqual(candidate["authority"], "non_authoritative")
        self.assertEqual(candidate["parent_binding"], binding)
        self.assertNotIn("maat_body", candidate)

    def test_T27_same_c_recovery_available_holds_without_candidate(self):
        binding = {
            "parent_work_id": "work-1", "parent_graph_ref": "graph:work-1", "parent_graph_revision": 3,
            "parent_graph_digest": "a" * 64, "blocked_receipt_ref": "run-1:4",
            "parent_edge_ref": "C1/P1", "return_to_node_ref": "C1",
        }
        result = preflight.build_derived_c_candidate(binding, ["run-1:2"], same_c_recovery_exhausted=False)
        self.assertEqual(result, {"status": "hold", "failure_code": "HOLD_SAME_C_RECOVERY_AVAILABLE", "graph_mutation": False})

    def test_T30_production_final_audit_hold_blocks_live_maat(self):
        packet = self.anchor_packet()
        packet["active_case_final_audit"] = {"graph_root": "/graphs", "execution_root": "/runtime", "identity": {}}
        candidate = {"route_enrichment": {"selective_maat_escalation": {"needed": True}}}
        route = {
            "status": "pass", "selected_agents": {}, "final_audit_needed": True,
            "semantic_anchor": packet["semantic_anchor"],
            "semantic_provenance_binding": packet["semantic_provenance_binding"],
        }
        reducer = {"status": "pass", "final_selected_agents": {}, "local_body_scope": {}}
        with patch.object(preflight, "invoke_live_maat", return_value=route), \
             patch.object(preflight, "probe_agents_as_arrive", return_value=({}, {})), \
             patch.object(preflight, "invoke_maat_reducer", return_value=reducer), \
             patch.object(preflight, "load_production_final_audit", return_value={"status": "hold", "failure_code": "HOLD_EXECUTION_INCOMPLETE"}), \
             patch.object(preflight, "invoke_maat_final_judgment") as final_maat:
            chain = preflight.execute_preflight_chain(packet, REPO / "packet.yaml", REPO, "live-maat", candidate)
        self.assertEqual(chain["final_judgment"]["failure_codes"], ["HOLD_EXECUTION_INCOMPLETE"])
        final_maat.assert_not_called()

    def test_semantic_gate_applies_only_to_anchor_semantics_packets(self):
        self.assertFalse(preflight.is_anchor_semantics_packet({"CPS": {"C": "ordinary"}}))
        self.assertTrue(preflight.is_anchor_semantics_packet({"semantic_anchor": {}}))
        packet = {"CPS": {"C": "ordinary"}, "route_candidates": ["ptah"]}
        candidate = {"route_enrichment": {"selective_maat_escalation": {"needed": True}}}
        reducer_result = {
            "status": "hold", "final_selected_agents": {}, "local_body_scope": {},
            "failure_codes": [], "hold_reasons": [],
        }
        with patch.object(preflight, "invoke_live_maat", return_value={"status": "hold", "selected_agents": {}}) as live, \
             patch.object(preflight, "probe_agents_as_arrive", return_value=({}, {})), \
             patch.object(preflight, "invoke_maat_reducer", return_value=reducer_result):
            preflight.execute_preflight_chain(packet, REPO / "packet.yaml", REPO, "live-maat", candidate)
        live.assert_called_once()

    def test_anchor_semantics_missing_binding_holds_before_live_or_reducer(self):
        packet = {"semantic_anchor": {"schema": "harness.honcho.cps_cluster.v1"}, "route_candidates": ["ptah"]}
        candidate = {"route_enrichment": {"selective_maat_escalation": {"needed": True}}}
        with patch.object(preflight, "invoke_live_maat") as live, patch.object(preflight, "invoke_maat_reducer") as reducer:
            chain = preflight.execute_preflight_chain(packet, REPO / "packet.yaml", REPO, "live-maat", candidate)
        self.assertEqual(chain["final_judgment"]["failure_codes"], ["HOLD_UNMAPPED_SEMANTIC_FIELD"])
        live.assert_not_called()
        reducer.assert_not_called()

    def test_live_anchor_unknown_leaf_or_prior_route_body_holds_before_probe(self):
        packet = self.anchor_packet()
        candidate = {"route_enrichment": {"selective_maat_escalation": {"needed": True}}}
        for body in ({**packet["semantic_anchor"], "invented": True}, {"schema": "prior-route-default"}):
            route = {
                "status": "pass", "selected_agents": {"ptah": {}},
                "semantic_anchor": body,
                "semantic_provenance_binding": packet["semantic_provenance_binding"],
            }
            with self.subTest(body=body), patch.object(preflight, "invoke_live_maat", return_value=route), patch.object(preflight, "probe_agents_as_arrive") as probes:
                chain = preflight.execute_preflight_chain(packet, REPO / "packet.yaml", REPO, "live-maat", candidate)
            self.assertEqual(chain["final_judgment"]["failure_codes"], ["HOLD_UNMAPPED_SEMANTIC_FIELD"])
            probes.assert_not_called()

    def test_node_projection_hold_blocks_semantic_materializer(self):
        packet = self.anchor_packet()
        packet["cps_working_graph_runtime"] = {"work_id": "work-1", "graph_root": "/graphs"}
        candidate = {"route_enrichment": {"selective_maat_escalation": {"needed": True}}}
        route = {
            "status": "pass", "selected_agents": {"ptah": {}},
            "semantic_anchor": packet["semantic_anchor"],
            "semantic_provenance_binding": packet["semantic_provenance_binding"],
        }
        reducer = {
            "status": "pass", "final_selected_agents": {"ptah": {}}, "local_body_scope": {"ptah": True},
            "maat_body": packet["semantic_anchor"], "semantic_anchor": packet["semantic_anchor"],
            "semantic_provenance_binding": packet["semantic_provenance_binding"],
        }
        with patch.object(preflight, "invoke_live_maat", return_value=route), \
             patch.object(preflight, "probe_agents_as_arrive", return_value=({}, {})), \
             patch.object(preflight, "invoke_maat_reducer", return_value=reducer), \
             patch.object(preflight, "apply_node_projection_gate", return_value={"status": "hold", "gap_classes": ["node_projection.local_body_ref"]}), \
             patch.object(preflight, "materialize_maat_runtime_binding") as materialize, \
             patch.object(preflight, "invoke_maat_final_judgment") as final_maat:
            chain = preflight.execute_preflight_chain(packet, REPO / "packet.yaml", REPO, "live-maat", candidate)
        materialize.assert_not_called()
        final_maat.assert_not_called()
        self.assertEqual(chain["final_selected_agents"], {})
        self.assertNotIn("cps_working_graph_operational", chain)

    def test_runtime_graph_missing_required_node_data_holds_without_synthesis(self):
        packet = {
            "runtime_packet": True,
            "cps_flow_graph": {"revision": "graph-r1", "nodes": [{"id": "P1"}]},
        }

        gate = preflight.validate_runtime_graph(packet)

        self.assertEqual(gate["status"], "hold")
        self.assertIn("P1.dependencies", gate["gaps"])
        self.assertIn("P1.parallel_group", gate["gaps"])
        self.assertIn("P1.owner", gate["gaps"])
        self.assertIn("P1.task_AC", gate["gaps"])
        self.assertIn("P1.evidence", gate["gaps"])
        self.assertIn("P1.S", gate["gaps"])
        self.assertNotIn("dispatch_plan", gate)

    def test_runtime_graph_missing_s_order_owner_and_evidence_holds(self):
        packet = {"runtime_packet": True, "cps_flow_graph": {"revision": "r1", "nodes": [{
            "id": "P1", "dependencies": [], "parallel_group": "g", "owner": "ptah",
            "task_AC": ["AC1"], "evidence": ["EV1"], "S": [{"id": "S1", "dependencies": []}],
        }]}}

        gate = preflight.validate_runtime_graph(packet)

        self.assertEqual(gate["status"], "hold")
        self.assertIn("P1.S1.ordinal", gate["gaps"])
        self.assertIn("P1.S1.owner", gate["gaps"])
        self.assertIn("P1.S1.task_AC", gate["gaps"])
        self.assertIn("P1.S1.evidence", gate["gaps"])

    def test_dispatch_plan_orders_s_and_groups_only_independent_ready_p(self):
        graph = {
            "revision": "graph-r2",
            "nodes": [
                {"id": "P1", "dependencies": [], "parallel_group": "g1", "owner": "ptah", "task_AC": ["AC-P1"], "evidence": ["EV-P1"], "S": [
                    {"id": "S2", "ordinal": 2, "dependencies": ["S1"], "owner": "ptah", "task_AC": ["AC-S2"], "evidence": ["EV-S2"]},
                    {"id": "S1", "ordinal": 1, "dependencies": [], "owner": "ptah", "task_AC": ["AC-S1"], "evidence": ["EV-S1"]},
                ]},
                {"id": "P2", "dependencies": [], "parallel_group": "g1", "owner": "anubis", "task_AC": ["AC-P2"], "evidence": ["EV-P2"], "S": [
                    {"id": "S3", "ordinal": 1, "dependencies": [], "owner": "anubis", "task_AC": ["AC-S3"], "evidence": ["EV-S3"]},
                ]},
                {"id": "P3", "dependencies": ["P1"], "parallel_group": "g1", "owner": "seshat", "task_AC": ["AC-P3"], "evidence": ["EV-P3"], "S": [
                    {"id": "S4", "ordinal": 1, "dependencies": [], "owner": "seshat", "task_AC": ["AC-S4"], "evidence": ["EV-S4"]},
                ]},
            ],
        }

        plan = preflight.build_dispatch_plan(graph)

        self.assertEqual(plan["graph_revision"], "graph-r2")
        self.assertEqual(plan["ready_groups"][0]["P_refs"], ["P1", "P2"])
        self.assertEqual(plan["nodes"]["P1"]["ready_S"], ["S1"])
        self.assertEqual(plan["nodes"]["P1"]["blocked_S"]["S2"], "dependency:S1")
        self.assertEqual(plan["nodes"]["P3"]["blocked_reason"], "dependency:P1")
        self.assertNotIn("P3", plan["ready_groups"][0]["P_refs"])
        self.assertEqual(plan["nodes"]["P2"]["owner"], "anubis")
        self.assertEqual(plan["nodes"]["P2"]["AC_refs"], ["AC-P2"])

    def physical_packet(self):
        return {
            "projection": {
                "graph_ref": {"ref": "graph:physical", "revision": "rev-1"},
                "canonical_source_ref": {"ref": "contract:physical", "revision": "rev-1"},
                "local_refs": [{"ref": "node:ptah", "revision": "rev-1", "node": "ptah"}],
            },
            "doc_ops": {"required": False},
            "route_candidates": ["ptah"],
        }

    def required_doc_ops(self):
        return {
            "required": True,
            "doc_refs": ["doc:contract"],
            "required_docs": ["contract.md"],
            "source_refs": ["source:maat"],
            "ssot_residency": "harness-brain",
            "canonical_author": "hermes-kann",
            "research_sources_from": ["seshat"],
            "allowed_write_surface": ["docs/contract.md"],
            "integration_owner": "hermes-kann",
            "manifest": {"expected_entries": ["contract.md"], "validator_ref": "validator:physical"},
            "verification": {
                "mode": "readback",
                "changed_paths": ["docs/contract.md"],
                "closure_line_refs": ["docs/contract.md:1"],
                "canonical_consistency_ref": "check:canonical",
            },
        }

    def test_physical_validator_allows_optional_doc_ops_without_dummy_fields(self):
        gate = preflight.validate_physical_docops_route(self.physical_packet())
        self.assertEqual(gate["status"], "pass")
        self.assertEqual(gate["gap_classes"], [])

    def test_required_doc_ops_holds_each_missing_or_invalid_field(self):
        valid = self.physical_packet()
        valid["doc_ops"] = self.required_doc_ops()
        self.assertEqual(preflight.validate_physical_docops_route(valid)["status"], "pass")
        invalidations = {
            "doc_refs": lambda d: d.pop("doc_refs"),
            "required_docs": lambda d: d.pop("required_docs"),
            "source_refs": lambda d: d.pop("source_refs"),
            "ssot_residency": lambda d: d.pop("ssot_residency"),
            "canonical_author": lambda d: d.__setitem__("canonical_author", "maat"),
            "research_sources_from": lambda d: d.__setitem__("research_sources_from", ["seshat", "sia"]),
            "allowed_write_surface": lambda d: d.pop("allowed_write_surface"),
            "integration_owner": lambda d: d.__setitem__("integration_owner", "maat"),
            "manifest.expected_entries": lambda d: d["manifest"].pop("expected_entries"),
            "manifest.validator_ref": lambda d: d["manifest"].pop("validator_ref"),
            "verification.mode": lambda d: d["verification"].pop("mode"),
            "verification.changed_paths": lambda d: d["verification"].pop("changed_paths"),
            "verification.closure_line_refs": lambda d: d["verification"].pop("closure_line_refs"),
            "verification.canonical_consistency_ref": lambda d: d["verification"].pop("canonical_consistency_ref"),
        }
        for field, invalidate in invalidations.items():
            packet = self.physical_packet()
            packet["doc_ops"] = json.loads(json.dumps(self.required_doc_ops()))
            invalidate(packet["doc_ops"])
            with self.subTest(field=field):
                gate = preflight.validate_physical_docops_route(packet)
                self.assertEqual(gate["status"], "hold")
                self.assertIn(f"doc_ops.{field}", gate["gap_classes"])

    def test_projection_rejects_canonical_bodies_and_ref_revision_gaps_without_reducing(self):
        forbidden = ("C", "P", "S", "AC", "E")
        for key in forbidden:
            packet = self.physical_packet()
            packet["projection"][key] = {"full": "copy"}
            original = json.loads(json.dumps(packet["projection"]))
            with self.subTest(key=key):
                gate = preflight.validate_physical_docops_route(packet)
                self.assertEqual(gate["status"], "hold")
                self.assertIn("projection.canonical_body_present", gate["gap_classes"])
                self.assertEqual(packet["projection"], original)
        for ref_key in ("graph_ref", "canonical_source_ref"):
            packet = self.physical_packet()
            packet["projection"][ref_key].pop("revision")
            with self.subTest(ref_key=ref_key):
                self.assertIn("projection.ref_revision_missing", preflight.validate_physical_docops_route(packet)["gap_classes"])
        packet = self.physical_packet()
        packet["projection"]["local_refs"][0]["expected_revision"] = "rev-2"
        self.assertIn("projection.ref_revision_mismatch", preflight.validate_physical_docops_route(packet)["gap_classes"])

    def test_thoth_is_rejected_only_in_actor_binding_locations(self):
        packet = self.physical_packet()
        packet["research_note"] = "Thoth appears in ordinary source history"
        packet["doc_ops"] = {"required": False, "source_refs": ["research about Thoth"]}
        self.assertEqual(preflight.validate_physical_docops_route(packet)["status"], "pass")
        for key in ("candidate_agents", "selected_agents", "final_selected_agents", "fallback", "compile_dependency", "local_body_scope"):
            bound = self.physical_packet()
            bound[key] = {"thoth": True}
            with self.subTest(key=key):
                self.assertIn("actor_binding.thoth_forbidden", preflight.validate_physical_docops_route(bound)["gap_classes"])

    def test_c2_runtime_requires_all_verified_dependencies_and_rejects_downscope(self):
        packet = self.physical_packet()
        packet["selected_agents"] = {"C2-RUNTIME": {"dependencies": [
            {"id": dep, "status": "verified"} for dep in preflight.C2_RUNTIME_DEPENDENCIES
        ]}}
        self.assertEqual(preflight.validate_physical_docops_route(packet)["status"], "pass")
        packet["selected_agents"]["C2-RUNTIME"]["dependencies"].pop()
        self.assertIn("c2_runtime.dependencies_unverified", preflight.validate_physical_docops_route(packet)["gap_classes"])
        packet = self.physical_packet()
        packet["selected_agents"] = {"C2-RUNTIME": {"dependencies": [
            {"id": dep, "status": "verified"} for dep in preflight.C2_RUNTIME_DEPENDENCIES
        ], "downscope": "background-job"}}
        self.assertIn("c2_runtime.generic_downscope_forbidden", preflight.validate_physical_docops_route(packet)["gap_classes"])

    def test_physical_gate_is_preserved_and_applied_before_all_release_paths(self):
        packet = self.physical_packet()
        candidate = preflight.build_candidate(packet, Path("packet.json"), REPO)
        self.assertEqual(candidate["physical_docops_gate"]["status"], "pass")
        deterministic = preflight.adjudicate(candidate)
        self.assertEqual(deterministic["physical_docops_gate"]["status"], "pass")
        live = preflight._normalize_live_maat({"selected_agents": {"ptah": {"P": [], "S": []}}}, candidate, None, "{}")
        self.assertEqual(live["physical_docops_gate"]["status"], "pass")
        probe = preflight.build_probe("ptah", live, {"P": [], "S": []})
        self.assertEqual(probe["physical_docops_gate"]["status"], "pass")
        held = self.physical_packet()
        held["projection"]["C"] = {"copied": True}
        held_candidate = preflight.build_candidate(held, Path("packet.json"), REPO)
        held_route = preflight.adjudicate(held_candidate)
        reducer = {"status": "pass", "local_body_scope": {"ptah": True}, "final_selected_agents": {"ptah": {"P": [], "S": []}}}
        probes, bodies = preflight.build_agent_body_map({"ptah": {"P": [], "S": []}}, held_route, reducer, held, Path("packet.json"))
        self.assertEqual(probes["ptah"]["physical_docops_gate"]["status"], "hold")
        self.assertEqual(bodies, {})
    def node_projection(self):
        return {
            "graph_ref": {"ref": "graph:AC8", "revision": "rev-8"},
            "canonical_source_ref": {"ref": "source:AC8", "revision": "rev-8"},
            "local_refs": {
                "C": "C:AC8", "P": "P:AC8", "S": "S:AC8",
                "AC": "AC:AC8", "E": "E:AC8",
            },
            "local_body_ref": "body:ptah:AC8",
            "node_local_AC": ["AC8"],
            "evidence": ["test:AC8"],
            "prohibitions": ["no unrelated mutation"],
            "source_revision": "rev-8",
            "changed_path_manifest": ["test_cps_preflight_verification_gate.py"],
            "next_C": {"ref": "C:AC9", "order": 9},
        }

    def test_node_projection_complete_reference_projection_passes(self):
        gate = preflight.validate_node_projection(
            self.node_projection(),
            expected_revision="rev-8",
            expected_changed_paths=["test_cps_preflight_verification_gate.py"],
        )
        self.assertEqual(gate["status"], "pass")
        self.assertEqual(gate["gap_classes"], [])

    def test_node_projection_missing_required_field_holds(self):
        projection = self.node_projection()
        projection.pop("local_body_ref")
        gate = preflight.validate_node_projection(projection)
        self.assertEqual(gate["status"], "hold")
        self.assertIn("node_projection.local_body_ref", gate["gap_classes"])

    def test_node_projection_rejects_nonexact_local_refs(self):
        projection = self.node_projection()
        projection["local_refs"]["Goal"] = "Goal:AC8"
        gate = preflight.validate_node_projection(projection)
        self.assertEqual(gate["status"], "hold")
        self.assertIn("node_projection.local_refs_exact_map", gate["gap_classes"])

    def test_node_projection_rejects_revision_mismatch(self):
        projection = self.node_projection()
        projection["canonical_source_ref"]["revision"] = "rev-7"
        gate = preflight.validate_node_projection(projection, expected_revision="rev-8")
        self.assertEqual(gate["status"], "hold")
        self.assertIn("node_projection.source_revision_mismatch", gate["gap_classes"])

    def test_node_projection_rejects_changed_path_manifest_mismatch(self):
        gate = preflight.validate_node_projection(
            self.node_projection(), expected_changed_paths=["different.py"],
        )
        self.assertEqual(gate["status"], "hold")
        self.assertIn("node_projection.changed_path_manifest_not_exact", gate["gap_classes"])

    def test_node_projection_requires_next_c_or_terminal(self):
        projection = self.node_projection()
        projection.pop("next_C")
        gate = preflight.validate_node_projection(projection)
        self.assertEqual(gate["status"], "hold")
        self.assertIn("node_projection.next_C_or_terminal", gate["gap_classes"])

    def test_failed_node_projection_dispatch_clears_agent_and_body_scope(self):
        route = {"selected_agents": {"ptah": {"P": ["P1"], "S": ["S1"]}}}
        reducer = {
            "status": "pass",
            "final_selected_agents": {"ptah": {"P": ["P1"], "S": ["S1"]}},
            "local_body_scope": {"ptah": True},
        }
        gate = preflight.apply_node_projection_gate(route, reducer, {})
        self.assertEqual(gate["status"], "hold")
        self.assertEqual(reducer["final_selected_agents"], {})
        self.assertEqual(reducer["local_body_scope"], {})
        self.assertEqual(reducer["status"], "hold")
        self.assertIn("HOLD_NODE_PROJECTION", reducer["failure_codes"])

    def test_failed_node_projection_cannot_restore_route_selected_agents(self):
        route = {"selected_agents": {"ptah": {"P": ["P1"], "S": ["S1"]}}}
        reducer = {
            "status": "pass",
            "final_selected_agents": {"ptah": {"P": ["P1"], "S": ["S1"]}},
            "local_body_scope": {"ptah": True},
        }

        preflight.apply_node_projection_gate(route, reducer, {})
        selected = preflight.normalize_selected_agents(route, reducer)
        dispatch = preflight.build_local_body_dispatch(route, reducer, {"ptah": {"schema": "body"}})

        self.assertEqual(selected, {})
        self.assertEqual(dispatch["aggregate"]["selected_count"], 0)
        self.assertEqual(dispatch["aggregate"]["direct_dispatch_count"], 0)

    def test_live_final_audit_projection_hold_makes_no_external_final_call(self):
        packet = {
            "root_goal": "change runtime",
            "mutation_scope": ["runtime"],
            "route_candidates": ["ptah"],
        }
        candidate = preflight.build_candidate(packet, Path("packet.json"), REPO)
        route = preflight.adjudicate(candidate)
        route.update({
            "status": "pass",
            "C_boundary": "PASS_ONE_C",
            "selected_agents": {"ptah": {"P": ["P1"], "S": ["S1"]}},
            "final_audit_needed": True,
        })
        reducer = {
            "status": "pass",
            "revised_C": route["C"],
            "revised_P": route["accepted_P"],
            "revised_S": route["accepted_S"],
            "revised_E": route["E"],
            "final_selected_agents": route["selected_agents"],
            "local_body_scope": {"ptah": True},
        }

        with patch.object(preflight, "invoke_live_maat", return_value=route), \
             patch.object(preflight, "probe_agents_as_arrive", return_value=({}, {})), \
             patch.object(preflight, "invoke_maat_reducer", return_value=reducer), \
             patch.object(preflight, "invoke_maat_final_judgment") as final_maat:
            chain = preflight.execute_preflight_chain(packet, Path("packet.json"), REPO, "live-maat", candidate)

        final_maat.assert_not_called()
        self.assertEqual(chain["reducer_result"]["node_projection_gate"]["status"], "hold")
        self.assertEqual(chain["final_judgment"]["source"], "local_node_projection_gate")

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

    def test_trace_has_no_false_memory_lookup_and_uses_delta_payloads(self):
        candidate = preflight.build_candidate({"root_goal": "implement code"}, Path("packet.json"), REPO)
        events = candidate["cps_trace_events"]
        self.assertEqual([event["event_type"] for event in events].count("seed_created"), 1)
        self.assertNotIn("memory_lookup_started", [event["event_type"] for event in events])
        self.assertNotIn("memory_match_attached", [event["event_type"] for event in events])
        self.assertNotIn("current_state", events[0])
        self.assertIn("seed_delta", events[0]["event_payload"])

    def test_candidate_consumes_foreground_c1_and_runtime_graph_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "brain.md"
            source.write_text("current", encoding="utf-8")
            packet = {
                "runtime_packet": True,
                "harness_brain_source": {"source_ref": str(source), "source_revision": "r1", "lifecycle": "validated"},
                "cps_flow_graph": {"revision": "g1", "nodes": [{
                    "id": "P1", "dependencies": [], "parallel_group": "g", "owner": "ptah",
                    "task_AC": ["AC1"], "evidence": ["EV1"], "S": [{
                        "id": "S1", "ordinal": 1, "dependencies": [], "owner": "ptah",
                        "task_AC": ["AC1"], "evidence": ["EV1"],
                    }],
                }]},
            }
            candidate = preflight.build_candidate(packet, Path("packet.json"), REPO)

        self.assertEqual(candidate["route_enrichment"]["memory"]["status"], "match")
        self.assertEqual(candidate["runtime_graph_gate"]["status"], "pass")
        self.assertEqual(candidate["dispatch_plan"]["ready_nodes"], ["P1"])
        self.assertEqual(candidate["c1_runtime_evidence_gate"]["status"], "pass")
        self.assertEqual(candidate["producer_ref"], "adapter:harness-brain:file:v1")

    def test_foreground_harness_brain_adapter_reads_current_source_and_links_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "brain.json"
            source.write_text("settled memory", encoding="utf-8")
            packet = {
                "harness_brain_source": {
                    "source_ref": str(source),
                    "source_revision": "brain-r7",
                    "lifecycle": "validated",
                },
                "graph_ref": "graph:C1",
                "graph_revision": "graph-r2",
            }
            result = preflight.retrieve_c1_foreground(packet, "candidate.json", "trace.json")

        self.assertEqual(result["normalized_result"]["status"], "match")
        match = result["normalized_result"]["matches"][0]
        self.assertEqual(match["source_ref"], str(source))
        self.assertEqual(match["source_revision"], "brain-r7")
        self.assertEqual(match["content_hash"], preflight.hashlib.sha256(b"settled memory").hexdigest())
        self.assertIn("mtime_ns", match["freshness"])
        self.assertTrue(result["normalized_result"]["active_only"])
        receipt = result["runtime_receipt"]
        self.assertEqual(receipt["producer_ref"], result["producer_ref"])
        self.assertEqual(receipt["consumer_ref"], "build_candidate")
        self.assertEqual(receipt["normalized_result_hash"], preflight.canonical_hash(result["normalized_result"]))
        self.assertEqual(receipt["candidate_artifact_ref"], "candidate.json")
        self.assertEqual(receipt["trace_artifact_ref"], "trace.json")

    def test_runtime_evidence_gate_rejects_fixture_only_and_mismatched_links(self):
        fixture_only = {"memory_lookup_result": {"harness-brain": {"status": "match", "matches": [{}]}}}
        self.assertEqual(preflight.validate_c1_runtime_evidence(fixture_only)["failure_code"], "HOLD_C1_RUNTIME_EVIDENCE")
        linked = {
            "producer_ref": "adapter:harness-brain:file:v1",
            "consumer_ref": "build_candidate",
            "runtime_receipt": {
                "producer_ref": "adapter:harness-brain:file:v1",
                "consumer_ref": "build_candidate",
                "normalized_result_hash": "expected",
            },
            "normalized_result": {"status": "match"},
        }
        self.assertEqual(preflight.validate_c1_runtime_evidence(linked)["status"], "hold")

    def test_unavailable_stale_and_nonadmissible_source_never_match(self):
        cases = [
            {},
            {"harness_brain_source": {"source_ref": "/missing", "source_revision": "r1", "lifecycle": "validated"}},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "brain.md"
            source.write_text("old", encoding="utf-8")
            cases.append({"harness_brain_source": {"source_ref": str(source), "source_revision": "r1", "lifecycle": "stale"}})
            for packet in cases:
                with self.subTest(packet=packet):
                    result = preflight.retrieve_c1_foreground(packet, "candidate.json", "trace.json")
                    self.assertNotEqual(result["normalized_result"]["status"], "match")

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

    def test_reentry_candidate_preserves_trace(self):
        original = self.candidate({})
        reentry = preflight.build_candidate_from_reentry({
            "revised_C": {"C1": "close gap"}, "revised_P": {"P1": "problem"},
            "revised_S": {"S1": "solution"}, "revised_E": ["P1 -> S1"],
            "missing_evidence": ["evidence"], "iteration": 1, "packet_ref": "packet.json",
        }, Path("packet.json"), REPO, original)
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

    def test_handoff_transport_preserves_opaque_maat_body_bytes_end_to_end(self):
        original = b"Maat body:\x00\xff\n  exact spacing\r\n"
        envelope = preflight.build_handoff_envelope(original, {"local_body_state": "complete", "agent": "ptah"})
        prompt = preflight.build_handoff_prompt(envelope)
        consumed = preflight.consume_handoff_prompt(prompt)
        runner_calls = []

        result = preflight.dispatch_handoff_transport(
            original, envelope, prompt, consumed, lambda body: runner_calls.append(body),
        )

        self.assertEqual(envelope["metadata"]["agent"], "ptah")
        self.assertNotIn("agent", envelope["body_transport"])
        self.assertEqual(consumed["body"], original)
        self.assertEqual(runner_calls, [original])
        self.assertEqual(result["status"], "dispatched")
        self.assertEqual(result["identity"]["original"], result["identity"]["consumer"])
        self.assertEqual(result["dispatch_count"], 1)
        self.assertEqual(result["search_count"], 0)

    def test_handoff_producer_snapshots_separable_metadata_without_touching_body(self):
        metadata = {"local_body_state": "complete", "labels": {"agent": "ptah"}}
        original = b"immutable body"

        envelope = preflight.build_handoff_envelope(original, metadata)
        metadata["labels"]["agent"] = "changed-after-production"
        consumed = preflight.consume_handoff_prompt(preflight.build_handoff_prompt(envelope))

        self.assertEqual(envelope["metadata"]["labels"], {"agent": "ptah"})
        self.assertNotIn("payload", envelope["metadata"])
        self.assertEqual(consumed["body"], original)

    def test_handoff_dispatcher_holds_every_negative_identity_case_before_runner(self):
        original = b"source body"

        def valid_chain(body=original):
            envelope = preflight.build_handoff_envelope(body, {"local_body_state": "complete"})
            prompt = preflight.build_handoff_prompt(envelope)
            return envelope, prompt, preflight.consume_handoff_prompt(prompt)

        cases = {}
        envelope, prompt, consumed = valid_chain(b"different envelope body")
        cases["source_to_envelope"] = (envelope, prompt, consumed)

        envelope, _, _ = valid_chain()
        other_envelope, prompt, consumed = valid_chain(b"different prompt body")
        self.assertNotEqual(envelope, other_envelope)
        cases["envelope_to_prompt"] = (envelope, prompt, consumed)

        envelope, prompt, _ = valid_chain()
        _, other_prompt, consumed = valid_chain(b"different consumer body")
        self.assertNotEqual(prompt, other_prompt)
        cases["prompt_to_consumer"] = (envelope, prompt, consumed)

        envelope, prompt, consumed = valid_chain()
        consumed["body_sha256"] = "0" * 64
        cases["consumer_digest"] = (envelope, prompt, consumed)

        envelope, prompt, consumed = valid_chain()
        consumed["search_count"] = 1
        cases["consumer_search"] = (envelope, prompt, consumed)

        for state in ("incomplete", "ambiguous"):
            envelope = preflight.build_handoff_envelope(original, {"local_body_state": state})
            prompt = preflight.build_handoff_prompt(envelope)
            cases[f"consumer_{state}"] = (envelope, prompt, preflight.consume_handoff_prompt(prompt))

        envelope, _, _ = valid_chain()
        malformed_prompt = "{not-json"
        cases["malformed_prompt"] = (
            envelope, malformed_prompt, preflight.consume_handoff_prompt(malformed_prompt),
        )

        envelope, prompt, consumed = valid_chain()
        envelope["body_transport"]["sha256"] = "0" * 64
        cases["malformed_envelope"] = (envelope, prompt, consumed)

        envelope, prompt, _ = valid_chain()
        cases["malformed_consumer"] = (envelope, prompt, None)

        for name, (envelope, prompt, consumed) in cases.items():
            runner_calls = []
            with self.subTest(name=name):
                result = preflight.dispatch_handoff_transport(
                    original, envelope, prompt, consumed, lambda body: runner_calls.append(body),
                )
                self.assertEqual(result["status"], "hold")
                self.assertEqual(result["failure_code"], "HOLD_HANDOFF_TRANSPORT_INTEGRITY")
                self.assertEqual(result["dispatch_count"], 0)
                self.assertEqual(result["search_count"], 0)
                self.assertEqual(runner_calls, [])

    def test_handoff_consumer_never_reconstructs_incomplete_or_ambiguous_body(self):
        for state, expected in (("incomplete", "need_local_body"), ("ambiguous", "hold")):
            envelope = preflight.build_handoff_envelope(b"partial", {"local_body_state": state})
            with self.subTest(state=state), patch.object(preflight, "search_handoff_body") as search:
                consumed = preflight.consume_handoff_prompt(preflight.build_handoff_prompt(envelope))
            self.assertEqual(consumed["status"], expected)
            self.assertEqual(consumed["search_count"], 0)
            self.assertNotIn("body", consumed)
            search.assert_not_called()

    def test_handoff_dispatcher_blocks_mismatch_before_runner_with_zero_dispatch_and_search(self):
        original = b"exact Maat body"
        envelope = preflight.build_handoff_envelope(original, {"local_body_state": "complete"})
        prompt = preflight.build_handoff_prompt(envelope)
        consumed = preflight.consume_handoff_prompt(prompt)
        consumed["body"] += b" tampered"
        runner_calls = []

        result = preflight.dispatch_handoff_transport(
            original, envelope, prompt, consumed, lambda body: runner_calls.append(body),
        )

        self.assertEqual(result["status"], "hold")
        self.assertEqual(result["failure_code"], "HOLD_HANDOFF_TRANSPORT_INTEGRITY")
        self.assertEqual(result["dispatch_count"], 0)
        self.assertEqual(result["search_count"], 0)
        self.assertEqual(runner_calls, [])

    def test_handoff_consumer_holds_malformed_transport_without_search(self):
        envelope = preflight.build_handoff_envelope(b"body", {"local_body_state": "complete"})
        prompt = preflight.build_handoff_prompt(envelope)
        payload = json.loads(prompt)
        payload["handoff_envelope"]["body_transport"]["sha256"] = "0" * 64

        with patch.object(preflight, "search_handoff_body") as search:
            consumed = preflight.consume_handoff_prompt(json.dumps(payload))

        self.assertEqual(consumed["status"], "hold")
        self.assertEqual(consumed["failure_code"], "HOLD_HANDOFF_TRANSPORT_INTEGRITY")
        self.assertEqual(consumed["search_count"], 0)
        search.assert_not_called()

    def production_handoff_chain(self, runner, consumer=None):
        packet = {"root_goal": "bounded handoff", "mutation_scope": ["runtime"], "route_candidates": ["ptah"]}
        candidate = preflight.build_candidate(packet, Path("packet.json"), REPO)
        route = preflight.adjudicate(candidate)
        route.update({"status": "pass", "selected_agents": {"ptah": {"P": ["P1"], "S": ["S1"]}}})
        reducer = {
            "status": "pass",
            "final_selected_agents": route["selected_agents"],
            "local_body_scope": {"ptah": True},
        }
        patches = [
            patch.object(preflight, "invoke_live_maat", return_value=route),
            patch.object(preflight, "probe_agents_as_arrive", return_value=({}, {})),
            patch.object(preflight, "invoke_maat_reducer", return_value=reducer),
            patch.object(preflight, "apply_node_projection_gate", return_value={"status": "pass"}),
        ]
        if consumer is not None:
            patches.append(patch.object(preflight, "consume_handoff_prompt", side_effect=consumer))
        with patches[0], patches[1], patches[2], patches[3]:
            if consumer is None:
                return preflight.execute_preflight_chain(
                    packet, Path("packet.json"), REPO, "live-maat", candidate,
                    selected_agent_runner=runner,
                )
            with patches[4]:
                return preflight.execute_preflight_chain(
                    packet, Path("packet.json"), REPO, "live-maat", candidate,
                    selected_agent_runner=runner,
                )

    def test_execute_preflight_chain_runs_selected_agent_with_verified_original_bytes(self):
        runner_calls = []

        chain = self.production_handoff_chain(lambda agent, body: runner_calls.append((agent, body)))

        expected = json.dumps(
            chain["local_bodies"]["ptah"], sort_keys=True, ensure_ascii=False, separators=(",", ":"),
        ).encode("utf-8")
        self.assertEqual(runner_calls, [("ptah", expected)])
        self.assertEqual(chain["handoff_transport"]["status"], "dispatched")
        self.assertEqual(chain["handoff_transport"]["dispatch_count"], 1)
        self.assertEqual(chain["handoff_transport"]["search_count"], 0)

    def test_execute_preflight_chain_one_byte_mismatch_holds_before_selected_agent_runner(self):
        runner_calls = []
        real_consumer = preflight.consume_handoff_prompt

        def one_byte_mismatch(prompt):
            consumed = real_consumer(prompt)
            consumed["body"] = bytes([consumed["body"][0] ^ 1]) + consumed["body"][1:]
            return consumed

        with patch.object(preflight, "search_handoff_body") as search:
            chain = self.production_handoff_chain(
                lambda agent, body: runner_calls.append((agent, body)), one_byte_mismatch,
            )

        self.assertEqual(chain["handoff_transport"]["status"], "hold")
        self.assertEqual(chain["handoff_transport"]["failure_code"], "HOLD_HANDOFF_TRANSPORT_INTEGRITY")
        self.assertEqual(chain["handoff_transport"]["dispatch_count"], 0)
        self.assertEqual(chain["handoff_transport"]["search_count"], 0)
        self.assertEqual(runner_calls, [])
        search.assert_not_called()
        self.assertEqual(chain["final_selected_agents"], {})
        self.assertEqual(chain["reducer_result"]["final_selected_agents"], {})
        self.assertEqual(chain["reducer_result"]["local_body_scope"], {})
        self.assertEqual(chain["local_body_dispatch"]["aggregate"]["selected_count"], 0)
        self.assertEqual(chain["local_body_dispatch"]["aggregate"]["direct_dispatch_count"], 0)
        self.assertEqual(chain["final_judgment"]["failure_codes"], ["HOLD_HANDOFF_TRANSPORT_INTEGRITY"])

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

    def test_deterministic_run_has_no_implicit_reentry_without_repair_evidence(self):
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
        self.assertEqual(reentries, [])
        self.assertEqual(result["reentry_iterations"], 0)
        self.assertEqual(events[-1]["event_type"], "workflow_closed")

    def test_fresh_verified_repair_reuses_c_ac_route_receipt_without_route_model_call(self):
        packet = {
            "root_goal": "repair AC3",
            "task_AC": [{"id": "AC3", "text": "fresh repair"}],
            "mutation_scope": ["runtime"],
            "route_candidates": ["ptah"],
            "C_ref": "C:repair",
            "graph_revision": "graph-r1",
            "parent_edge_ref": "C1.P1/S1",
            "repair_revision": "repair-r2",
            "mutation_actor": "ptah",
            "new_evidence_refs": ["evidence:fresh-r2"],
        }
        candidate = preflight.build_candidate(packet, Path("packet.json"), REPO)
        route = preflight.adjudicate(candidate)
        route["route_candidate_catalog"] = preflight.select_route_candidate_catalog(packet, candidate)
        delta = preflight.build_downstream_packet_delta(packet, "verdict:hold-r1")
        identity = preflight.canonical_hash({
            key: delta[key] for key in ("C_ref", "AC_digest", "graph_revision", "parent_edge_ref")
        })
        route_receipt = {
            "schema": "harness.cps_preflight.c_ac_route_receipt.v1",
            "receipt_identity": identity,
            **{key: delta[key] for key in ("C_ref", "AC_digest", "graph_revision", "parent_edge_ref")},
            "route": route,
        }
        packet["prior_continuation_receipt"] = {
            "status": "hold",
            "receipt_identity": identity,
            "evidence_fingerprint": preflight.canonical_hash(["evidence:old-r1"]),
            "repair_revision": "repair-r1",
            "verifier_receipt_ref": "verify:old-r1",
            "verdict_ref": "verdict:hold-r1",
            "C_AC_route_receipt": route_receipt,
        }
        packet["verifier_receipt"] = {
            "actor": "anubis",
            "receipt_identity": identity,
            "repair_revision": "repair-r2",
            "receipt_ref": "verify:fresh-r2",
        }
        candidate = preflight.build_candidate(packet, Path("packet.json"), REPO)
        reducer_result = {"status": "hold", "final_selected_agents": {}, "local_body_scope": {}}

        with patch.object(preflight, "invoke_live_maat") as route_maat, \
             patch.object(preflight, "probe_agents_as_arrive", return_value=({}, {})), \
             patch.object(preflight, "invoke_maat_reducer", return_value=reducer_result) as reducer:
            chain = preflight.execute_preflight_chain(packet, Path("packet.json"), REPO, "live-maat", candidate)

        route_maat.assert_not_called()
        reducer.assert_called_once()
        self.assertEqual(chain["receipt_delta_gate"]["action"], "reenter")
        for key in ("receipt_identity", "C_ref", "AC_digest", "graph_revision", "parent_edge_ref"):
            self.assertEqual(chain["C_AC_route_receipt"][key], route_receipt[key])
        self.assertEqual(chain["route"]["C"], route["C"])
        self.assertEqual(chain["route"]["accepted_P"], route["accepted_P"])
        self.assertEqual(chain["route"]["accepted_S"], route["accepted_S"])

        mismatch = json.loads(json.dumps(packet))
        mismatch["prior_continuation_receipt"]["C_AC_route_receipt"]["C_ref"] = "C:other"
        mismatch_candidate = preflight.build_candidate(mismatch, Path("packet.json"), REPO)
        with patch.object(preflight, "invoke_live_maat") as mismatch_route_maat:
            held = preflight.execute_preflight_chain(mismatch, Path("packet.json"), REPO, "live-maat", mismatch_candidate)
        mismatch_route_maat.assert_not_called()
        self.assertEqual(held["receipt_delta_gate"]["action"], "hold_mismatch")
        self.assertIn("receipt_delta.C_AC_route_receipt_identity_mismatch", held["receipt_delta_gate"]["gap_classes"])

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

    def r2c_identity(self):
        body = b"r2c body"
        return body, {
            "work_id": "work-r2c", "graph_ref": "graph:work-r2c", "graph_revision": 2,
            "graph_digest": "b" * 64, "stage_ref": "S:R2C", "owner_ref": "ptah",
            "parent_edge_ref": "C_R2C/P1", "return_to_node_ref": "C_R2C",
            "run_handle": "run-r2c", "attempt": 1,
            "immutable_body_digest": hashlib.sha256(body).hexdigest(),
        }

    def r2c_chain(self):
        goal_closure = {"status": "pass", "reason": "Maat judgment remains authoritative"}
        return {
            "candidate": {"schema": "candidate", "mutation_closure": {}},
            "route": {
                "status": "pass", "C_boundary": "PASS_ONE_C", "selected_agents": {},
                "audit_plan": {}, "prohibitions": [], "verification_gate": {"gap_class": "none"},
                "final_audit_needed": False, "C": {"C1": "caller projection"},
            },
            "draft_probes": {}, "probe_responses": {}, "reducer_input": {},
            "reducer_result": {
                "status": "pass", "revised_C": {"C1": "caller projection"},
                "final_selected_agents": {}, "local_body_scope": {},
            },
            "probes": {}, "local_bodies": {}, "local_body_dispatch": {},
            "contribute_cps": {"Goal_closure": goal_closure},
            "final_judgment": {"status": "pass", "Goal_closure": goal_closure, "marker": "unchanged"},
            "hold_gap_loop": {"status": "closed", "missing_evidence": []},
            "final_selected_agents": {},
        }

    def run_r2c(self, root, identity):
        packet_path = root / "packet.json"
        out_dir = root / "out"
        packet_path.write_text(json.dumps({
            "root_goal": "R2-C1 caller integration",
            "active_case_final_audit": {
                "graph_root": str(root / "graphs"),
                "execution_root": str(root / "runtime"),
                "identity": identity,
            },
        }), encoding="utf-8")
        chain = self.r2c_chain()
        with patch.object(preflight, "build_candidate", return_value=chain["candidate"]), \
             patch.object(preflight, "execute_preflight_chain", return_value=chain), \
             patch.object(preflight, "max_reentry_iterations", return_value=0), \
             patch.object(preflight, "record_preflight_runtime_observation"):
            result = preflight.run(packet_path, out_dir, REPO, mode="live-maat")
        return result, json.loads((out_dir / "final_output.json").read_text(encoding="utf-8"))

    def test_R2C_01_run_and_final_output_project_authorization_only_as_issued(self):
        _, identity = self.r2c_identity()
        with tempfile.TemporaryDirectory() as tmp:
            result, artifact = self.run_r2c(Path(tmp), identity)
        for output in (result["final_output"], artifact):
            state = output["execution_state"]
            self.assertEqual(state["authorization_state"], "ISSUED")
            self.assertIsNone(state["runtime_state"])
            self.assertIsNone(state["execution_status"])
            self.assertIsNone(state["audit_verdict"])

    def test_R2C_02_reloaded_observed_and_terminal_receipts_project_runtime_only(self):
        import external_runtime_dispatcher as dispatcher
        body, identity = self.r2c_identity()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runtime = root / "runtime"
            lifecycle.dispatch_external_body(
                "ptah", body, [sys.executable, "worker.py"], runtime,
                identity=identity, process_runner=lambda argv: 123456789,
            )
            chain_path, current_path, _ = dispatcher._paths(identity, runtime)
            records = [json.loads(line) for line in chain_path.read_text(encoding="utf-8").splitlines()]
            for event, selected in (("dispatch", records[:1]), ("heartbeat", records)):
                chain_path.write_text("".join(json.dumps(item) + "\n" for item in selected), encoding="utf-8")
                current_path.write_text(json.dumps(selected[-1]), encoding="utf-8")
                with self.subTest(event=event):
                    result, _ = self.run_r2c(root, identity)
                    state = result["final_output"]["execution_state"]
                    self.assertEqual(state["runtime_state"], "RUNNING")
                    self.assertEqual(state["execution_event"], event)
                    self.assertIsNone(state["execution_status"])
                    self.assertIsNone(state["audit_verdict"])
            chain_path.write_text("".join(json.dumps(item) + "\n" for item in records), encoding="utf-8")
            current_path.write_text(json.dumps(records[-1]), encoding="utf-8")
            lifecycle.poll_external_body(identity, runtime)
            for event in ("poll", "blocker"):
                if event == "blocker":
                    lifecycle.reconcile_external_body(identity, runtime, pid_is_alive=lambda pid: False)
                with self.subTest(event=event):
                    result, _ = self.run_r2c(root, identity)
                    state = result["final_output"]["execution_state"]
                    self.assertEqual(state["runtime_state"], "RUNNING")
                    self.assertEqual(state["execution_event"], event)
                    self.assertIsNone(state["execution_status"])
                    self.assertIsNone(state["audit_verdict"])
            for status in ("pass", "fail", "blocked"):
                chain_path.write_text("".join(json.dumps(item) + "\n" for item in records), encoding="utf-8")
                current_path.write_text(json.dumps(records[-1]), encoding="utf-8")
                dispatcher.append_terminal_receipt(identity, runtime, status)
                with self.subTest(status=status):
                    result, _ = self.run_r2c(root, identity)
                    state = result["final_output"]["execution_state"]
                    self.assertEqual(state["runtime_state"], "TERMINAL")
                    self.assertEqual(state["execution_status"], status)
                    self.assertIsNone(state["audit_verdict"])
                    self.assertEqual(result["final_output"]["status"], "pass")
                    self.assertEqual(result["final_maat_judgment"]["marker"], "unchanged")

    def test_R2C_03_malformed_identity_tail_and_postterminal_fail_closed(self):
        import external_runtime_dispatcher as dispatcher
        body, identity = self.r2c_identity()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            malformed, _ = self.run_r2c(root, {"run_handle": "caller-claim"})
            self.assertIsNone(malformed["final_output"]["execution_state"]["runtime_state"])
            runtime = root / "runtime"
            lifecycle.dispatch_external_body(
                "ptah", body, [sys.executable, "worker.py"], runtime,
                identity=identity, process_runner=lambda argv: 123456789,
            )
            chain_path, current_path, _ = dispatcher._paths(identity, runtime)
            records = [json.loads(line) for line in chain_path.read_text(encoding="utf-8").splitlines()]
            chain_path.write_text("{malformed\n", encoding="utf-8")
            malformed_receipt, _ = self.run_r2c(root, identity)
            self.assertIsNone(malformed_receipt["final_output"]["execution_state"]["runtime_state"])
            mismatched_records = json.loads(json.dumps(records))
            mismatched_records[-1]["owner_ref"] = "caller"
            chain_path.write_text("".join(json.dumps(item) + "\n" for item in mismatched_records), encoding="utf-8")
            current_path.write_text(json.dumps(mismatched_records[-1]), encoding="utf-8")
            identity_mismatch, _ = self.run_r2c(root, identity)
            self.assertIsNone(identity_mismatch["final_output"]["execution_state"]["runtime_state"])
            chain_path.write_text("".join(json.dumps(item) + "\n" for item in records), encoding="utf-8")
            current_path.write_text(json.dumps(records[0]), encoding="utf-8")
            mismatch, _ = self.run_r2c(root, identity)
            self.assertIsNone(mismatch["final_output"]["execution_state"]["runtime_state"])
            current_path.write_text(json.dumps(records[-1]), encoding="utf-8")
            dispatcher.append_terminal_receipt(identity, runtime, "pass")
            records = [json.loads(line) for line in chain_path.read_text(encoding="utf-8").splitlines()]
            postterminal = dict(records[-2])
            postterminal["receipt_ref"] = f"{identity['run_handle']}:{len(records) + 1}"
            postterminal["transition_from_ref"] = records[-1]["receipt_ref"]
            postterminal["facts"] = dict(postterminal["facts"], event="poll")
            records.append(postterminal)
            chain_path.write_text("".join(json.dumps(item) + "\n" for item in records), encoding="utf-8")
            current_path.write_text(json.dumps(records[-1]), encoding="utf-8")
            held, _ = self.run_r2c(root, identity)
            self.assertIsNone(held["final_output"]["execution_state"]["runtime_state"])
            self.assertIsNone(held["final_output"]["execution_state"]["execution_status"])

    def test_R2C_04_projection_is_read_only_and_does_not_rejudge_closure(self):
        body, identity = self.r2c_identity()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runtime = root / "runtime"
            lifecycle.dispatch_external_body(
                "ptah", body, [sys.executable, "worker.py"], runtime,
                identity=identity, process_runner=lambda argv: 123456789,
            )
            before = {path: path.read_bytes() for path in runtime.rglob("*") if path.is_file()}
            result, artifact = self.run_r2c(root, identity)
            after = {path: path.read_bytes() for path in runtime.rglob("*") if path.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(result["final_output"]["status"], "pass")
        self.assertEqual(result["final_output"]["Goal_closure"], {"status": "pass", "reason": "Maat judgment remains authoritative"})
        self.assertEqual(result["final_maat_judgment"]["marker"], "unchanged")
        self.assertEqual(artifact["status"], "pass")
        self.assertIsNone(artifact["execution_state"]["audit_verdict"])

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


class TestMaatR3BoundedVerifierScope(TestCase):
    SOURCE = ".harness/hermes/tools/cps_preflight_route_gate.py"
    TEST = "test_cps_preflight_verification_gate.py"
    SELECTORS = [
        "test_cps_preflight_verification_gate.TestMaatR3BoundedVerifierScope.test_R3_01_focused_pass_builds_nonfinal_candidate_and_separates_baselines",
        "test_cps_preflight_verification_gate.TestMaatR3BoundedVerifierScope.test_R3_02_focused_selected_target_failure_decides_failure_candidate",
        "test_cps_preflight_verification_gate.TestMaatR3BoundedVerifierScope.test_R3_03_missing_mismatch_nonexact_command_and_path_escape_hold",
        "test_cps_preflight_verification_gate.TestMaatR3BoundedVerifierScope.test_R3_04_only_exact_maat_import_can_change_baseline_case_effect",
        "test_cps_preflight_verification_gate.TestMaatR3BoundedVerifierScope.test_R3_05_evaluation_is_read_only_and_emits_no_audit_claim",
    ]

    def scope(self):
        return {
            "repo_cwd": str(REPO),
            "target_command": ["/usr/bin/python3", "-B", "-m", "unittest", *self.SELECTORS],
            "allowed_source_paths": [self.SOURCE],
            "allowed_test_paths": [self.TEST],
            "exact_unittest_selectors": self.SELECTORS,
            "maat_import": None,
        }

    def baselines(self):
        return [{"observation_id": "baseline-schema", "status": "fail", "evidence": "existing failure"}]

    def completed(self, returncode=0):
        return subprocess.CompletedProcess(self.scope()["target_command"], returncode, b"focused stdout", b"focused stderr")

    def binding(self, scope):
        executable = Path("/usr/bin/python3")
        path_hashes = {
            path: hashlib.sha256((REPO / path).read_bytes()).hexdigest()
            for path in scope["allowed_source_paths"] + scope["allowed_test_paths"]
        }
        body = {
            "executable": {
                "path": str(executable),
                "realpath": str(executable.resolve(strict=True)),
                "sha256": hashlib.sha256(executable.resolve(strict=True).read_bytes()).hexdigest(),
            },
            "cwd": str(REPO),
            "argv": scope["target_command"],
            "selectors": scope["exact_unittest_selectors"],
            "allowed_path_hashes": path_hashes,
        }
        return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    def canonical_import(self, root, scope, **overrides):
        identity = {"actor_ref": "maat", "role": "final_gate", "adjudication_id": "R3-D2-adjudication-1"}
        document = {
            "schema": "harness.maat.final_gate_adjudication.v1",
            "adjudicator_identity": identity,
            "observation_ids": ["baseline-schema"],
            "scope_binding_digest": self.binding(scope),
        }
        ref = root / "maat-final-adjudication.json"
        ref.write_text(json.dumps(document, sort_keys=True, separators=(",", ":")), encoding="utf-8")
        imported = {
            "adjudication_ref": str(ref),
            "adjudication_sha256": hashlib.sha256(ref.read_bytes()).hexdigest(),
            "adjudicator_identity": identity,
            "observation_ids": ["baseline-schema"],
            "scope_binding_digest": document["scope_binding_digest"],
        }
        imported.update(overrides)
        return imported

    def run_candidate(self, scope=None, baselines=None, returncode=0):
        with patch.object(preflight.subprocess, "run", return_value=self.completed(returncode)) as runner:
            result = preflight.build_bounded_verifier_candidate(
                scope or self.scope(), self.baselines() if baselines is None else baselines, repo=REPO,
            )
        return result, runner

    def test_R3_01_focused_pass_builds_nonfinal_candidate_and_separates_baselines(self):
        result, runner = self.run_candidate()

        runner.assert_called_once_with(
            self.scope()["target_command"], cwd=str(REPO), capture_output=True, text=False, check=False,
        )
        receipt = result["focused_execution_receipt"]
        self.assertEqual(set(receipt), preflight.R3_FOCUSED_EXECUTION_RECEIPT_FIELDS)
        identity = {key: receipt[key] for key in preflight.R3_EXECUTION_IDENTITY_FIELDS}
        self.assertEqual(receipt["execution_identity_digest"], preflight._r3_json_digest(identity))
        digest_body = {key: value for key, value in receipt.items() if key != "receipt_digest"}
        self.assertEqual(receipt["receipt_digest"], preflight._r3_json_digest(digest_body))
        self.assertEqual(result["focused_result"], receipt)
        self.assertEqual(result["active_case_verdict_candidate"]["evidence"], receipt)
        self.assertEqual(result["active_case_verdict_candidate"]["status"], "pass")
        self.assertEqual(result["baseline_observations"][0]["case_effect"], "none")

    def test_R3_02_focused_selected_target_failure_decides_failure_candidate(self):
        result, _ = self.run_candidate(baselines=[], returncode=1)
        self.assertEqual(result["focused_execution_receipt"]["status"], "fail")
        self.assertEqual(result["active_case_verdict_candidate"]["status"], "fail")
        self.assertEqual(result["active_case_verdict_candidate"]["authority"], "candidate_only")

    def test_R3_03_missing_mismatch_nonexact_command_and_path_escape_hold(self):
        invalid = []
        scope = self.scope()
        scope["repo_cwd"] = str(REPO.parent)
        invalid.append((scope, "repo_cwd_mismatch"))
        scope = self.scope()
        scope["target_command"] = ["/usr/bin/python3", "-B", "-m", "unittest", "discover"]
        invalid.append((scope, "target_command_not_exact"))
        scope = self.scope()
        scope["exact_unittest_selectors"] = self.SELECTORS[:-1]
        invalid.append((scope, "target_command_not_exact"))
        for scope, reason in invalid:
            with self.subTest(reason=reason):
                result = preflight.build_bounded_verifier_candidate(scope, [], repo=REPO)
                self.assertEqual(result["active_case_verdict_candidate"]["hold_reason"], reason)

        mismatch = subprocess.CompletedProcess(["/bin/echo", "OK"], 0, b"OK", b"")
        with patch.object(preflight.subprocess, "run", return_value=mismatch):
            held = preflight.build_bounded_verifier_candidate(self.scope(), [], repo=REPO)
        self.assertEqual(held["active_case_verdict_candidate"]["hold_reason"], "completed_process_mismatch")

    def test_R3_04_only_exact_maat_import_can_change_baseline_case_effect(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scope = self.scope()
            scope["maat_import"] = self.canonical_import(root, scope)
            with patch.object(preflight.subprocess, "run", return_value=self.completed()):
                imported = preflight.build_bounded_verifier_candidate(scope, self.baselines(), repo=REPO)
            self.assertEqual(imported["active_case_verdict_candidate"]["status"], "fail")
            self.assertTrue(imported["baseline_observations"][0]["explicitly_imported"])

            identity_cases = (
                {"actor_ref": "anubis", "role": "final_gate", "adjudication_id": "R3-D2-adjudication-1"},
                {"actor_ref": "maat", "role": "review", "adjudication_id": "R3-D2-adjudication-1"},
                {"actor_ref": "maat", "role": "final_gate", "adjudication_id": ""},
            )
            for identity in identity_cases:
                rejected_scope = self.scope()
                rejected_scope["maat_import"] = self.canonical_import(root, rejected_scope, adjudicator_identity=identity)
                with self.subTest(identity=identity):
                    rejected = preflight.build_bounded_verifier_candidate(rejected_scope, self.baselines(), repo=REPO)
                    self.assertEqual(rejected["active_case_verdict_candidate"]["hold_reason"], "maat_import_mismatch")

            mismatches = {
                "adjudication_ref": str(root / "missing.json"),
                "adjudication_sha256": "0" * 64,
                "observation_ids": ["different-observation"],
                "scope_binding_digest": "f" * 64,
            }
            for field, value in mismatches.items():
                rejected_scope = self.scope()
                rejected_scope["maat_import"] = self.canonical_import(root, rejected_scope, **{field: value})
                with self.subTest(field=field):
                    rejected = preflight.build_bounded_verifier_candidate(rejected_scope, self.baselines(), repo=REPO)
                    self.assertEqual(rejected["active_case_verdict_candidate"]["hold_reason"], "maat_import_mismatch")

    def test_R3_05_evaluation_is_read_only_and_emits_no_audit_claim(self):
        paths = [MODULE_PATH, Path(__file__).resolve()]
        before = {path: path.read_bytes() for path in paths}
        result, _ = self.run_candidate(baselines=[])
        after = {path: path.read_bytes() for path in paths}

        self.assertEqual(before, after)
        self.assertEqual(result["active_case_verdict_candidate"]["authority"], "candidate_only")
        self.assertFalse(result["active_case_verdict_candidate"]["final_audit_verdict"])
        self.assertNotIn("audit_verdict", result["active_case_verdict_candidate"])
        self.assertEqual(result["side_effects"], {
            "receipt_writes": 0, "graph_writes": 0, "route_writes": 0, "business_writes": 0,
        })
