import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / ".harness" / "hermes" / "tools"
sys.path.insert(0, str(TOOLS))

import cps_c1_retrieval_adapter as adapter
import cps_preflight_route_gate as preflight
import cps_runtime_navigation as navigation
import cps_working_graph_registry as registry
import lifecycle_runner as lifecycle


class CpsCurrentSystemIntegrationTests(unittest.TestCase):
    def test_T32_preflight_final_audit_loader_uses_production_adapter_result_without_goal_mutation(self):
        binding = {"graph_root": "/graphs", "execution_root": "/runtime", "identity": {"work_id": "work-1"}}
        evidence = {"status": "eligible_for_maat_audit", "semantic_lane": {"graph_ref": "graph:1"}, "execution_lane": {"receipt_ref": "run:3"}}
        adapter = Mock()
        adapter.reload.return_value = evidence
        with patch.object(lifecycle, "FinalAuditProductionAdapter", return_value=adapter) as factory:
            result = preflight.load_production_final_audit(binding)
        self.assertEqual(result, evidence)
        self.assertNotIn("Goal_closure", result)
        factory.assert_called_once_with(Path("/graphs"), Path("/runtime"))
        adapter.reload.assert_called_once_with(binding["identity"])
    def test_read_only_c1_graph_projection_dispatch_chain(self):
        with tempfile.TemporaryDirectory() as tmp:
            temp_root = Path(tmp)
            source_paths = {}
            bindings = {}
            binding_calls = []
            for source_kind in adapter.SOURCE_KINDS:
                source = temp_root / f"{source_kind}.txt"
                source.write_text(f"bounded {source_kind} advisory", encoding="utf-8")
                source_paths[source_kind] = source

                def reader(source_ref, query, *, kind=source_kind, path=source):
                    binding_calls.append((kind, source_ref, query))
                    return {"matches": [{"source_ref": f"{kind}:mocked", "content": path.read_bytes()}]}

                bindings[source_kind] = reader

            advisory = adapter.observe_sources(
                {},
                advisory_bindings=bindings,
                query="bounded C1 current-state lookup",
                timestamp="2026-07-15T00:00:00Z",
            )
            self.assertEqual(
                [observation["source_kind"] for observation in advisory["observations"]],
                list(adapter.SOURCE_KINDS),
            )
            self.assertEqual([observation["status"] for observation in advisory["observations"]], ["match"] * 3)
            self.assertEqual(len(binding_calls), 3)
            for observation in advisory["observations"]:
                self.assertEqual(set(observation), {"source_kind", "status", "source_ref", "evidence"})
                self.assertEqual(set(observation["evidence"]), {"count", "timestamp", "digest"})
            bounded_advisory = json.dumps(advisory, sort_keys=True)
            self.assertNotIn("bounded honcho advisory", bounded_advisory)
            self.assertNotIn("bounded gbrain advisory", bounded_advisory)
            self.assertNotIn("bounded harness_brain advisory", bounded_advisory)

            memory_lookup_result = {"lookup_ref": "lookup:current-system"}
            for source_kind, layer in (
                ("honcho", "honcho"),
                ("gbrain", "gbrain"),
                ("harness_brain", "harness-brain"),
            ):
                source = source_paths[source_kind]
                memory_lookup_result[layer] = {"matches": [{
                    "source_ref": str(source),
                    "source_revision": "source-r1",
                    "content_hash": hashlib.sha256(source.read_bytes()).hexdigest(),
                    "freshness": "2026-07-15T00:00:00Z",
                    "lifecycle": "validated",
                    "supersedes": None,
                }]}

            graph_root = temp_root / "working-graphs"
            maat_body = {"schema": "harness.honcho.cps_cluster.v1", "C": {"shape": "bounded"}}
            canonical_source = ROOT.parent / "harness-brain" / "projects" / ROOT.name / "decisions" / "cps-memory-lifecycle-and-honcho-anchor.md"
            source_text = canonical_source.read_text(encoding="utf-8")
            section_ref, definition_refs = navigation._anchor_definition_refs(canonical_source, source_text)
            provenance = {
                "canonical_source_locator": str(canonical_source),
                "canonical_source_readback": f"{canonical_source}:1-{len(source_text.splitlines())}",
                "current_source_revision": subprocess.check_output(
                    ["git", "-C", str(canonical_source.parent), "rev-parse", "HEAD"], text=True,
                ).strip(),
                "current_content_hash": hashlib.sha256(canonical_source.read_bytes()).hexdigest(),
                "canonical_section": section_ref,
                "semantic_field_definition_coverage": {
                    key: definition_refs[key] for key in ("schema", "C.shape")
                },
            }
            graph_packet = {
                "cps_working_graph_runtime": {
                    "work_id": "current-system",
                    "graph_root": str(graph_root),
                },
                "semantic_anchor": maat_body,
                "semantic_provenance_binding": provenance,
            }
            operational = preflight.materialize_preflight_working_graph(
                graph_packet,
                {
                    "status": "pass", "maat_body": maat_body, "semantic_anchor": maat_body,
                    "semantic_provenance_binding": provenance,
                },
            )
            self.assertEqual(operational["cps_working_graph_operational"]["revision"], 1)
            store = registry.WorkingGraphRegistry(graph_root)
            graph_before = store.load("current-system")
            body_digest = graph_before["maat_body_digest"]

            runtime_graph = {
                "revision": "graph-r1",
                "nodes": [{
                    "id": "P1",
                    "dependencies": [],
                    "parallel_group": "group-1",
                    "owner": "ptah",
                    "task_AC": ["AC1"],
                    "evidence": ["integration receipt"],
                    "S": [{
                        "id": "S1",
                        "ordinal": 1,
                        "dependencies": [],
                        "owner": "ptah",
                        "task_AC": ["AC1"],
                        "evidence": ["integration receipt"],
                    }],
                }],
            }
            complete_projection = {
                "graph_ref": {"ref": "graph:current-system", "revision": "source-r1"},
                "canonical_source_ref": {"ref": "source:current-system", "revision": "source-r1"},
                "local_refs": {"C": "C:1", "P": "P:1", "S": "S:1", "AC": "AC:1", "E": "E:1"},
                "local_body_ref": "body:ptah:1",
                "node_local_AC": ["AC1"],
                "evidence": ["integration receipt"],
                "prohibitions": ["read only"],
                "source_revision": "source-r1",
                "changed_path_manifest": ["tests/test_cps_current_system_integration.py"],
                "next_C": {"ref": "C:2", "order": 2},
            }
            honcho_source = source_paths["honcho"]
            honcho_matches = [{
                "source_ref": str(honcho_source),
                "source_revision": "source-r1",
                "content_hash": hashlib.sha256(honcho_source.read_bytes()).hexdigest(),
                "freshness": "2026-07-15T00:00:00Z",
                "lifecycle": "validated",
                "supersedes": None,
            }]
            packet = {
                "root_goal": "exercise the bounded current CPS chain",
                "runtime_packet": True,
                "memory_lookup_result": memory_lookup_result,
                "honcho_memory_reader": {
                    "sdk": type("ReadOnlyHoncho", (), {
                        "search_context": lambda self, session_key, query, max_tokens, peer: honcho_matches,
                    })(),
                    "session_key": "current-system",
                    "peer": "harness-starter",
                },
                "gbrain_source": {
                    "source_ref": str(source_paths["gbrain"]), "source_revision": "source-r1", "lifecycle": "validated",
                },
                "harness_brain_source": {
                    "source_ref": str(source_paths["harness_brain"]), "source_revision": "source-r1", "lifecycle": "validated",
                },
                "cps_flow_graph": runtime_graph,
                "graph_ref": "graph:current-system",
                "graph_revision": "graph-r1",
                "route_candidates": ["ptah"],
                "mutation_scope": ["integration-test-runtime"],
                "task_AC": ["AC1"],
                "source_revision": "source-r1",
                "changed_path_manifest": ["tests/test_cps_current_system_integration.py"],
                "node_projection": complete_projection,
                "semantic_anchor": maat_body,
                "semantic_provenance_binding": provenance,
            }
            packet_path = temp_root / "packet.json"
            candidate = preflight.build_candidate(packet, packet_path, ROOT)
            self.assertEqual(candidate["route_enrichment"]["memory"]["status"], "match")
            self.assertEqual(
                [layer["layer"] for layer in candidate["route_enrichment"]["memory"]["layers"]],
                ["honcho", "gbrain", "harness-brain"],
            )
            receipt = candidate["runtime_receipt"]
            self.assertEqual(receipt["producer_ref"], candidate["producer_ref"])
            self.assertEqual(receipt["consumer_ref"], "build_candidate")
            self.assertEqual(receipt["normalized_result_hash"], preflight.canonical_hash(candidate["normalized_result"]))
            self.assertEqual(candidate["c1_runtime_evidence_gate"]["status"], "pass")
            self.assertEqual(candidate["dispatch_plan"]["ready_nodes"], ["P1"])

            observation_files = {
                "candidate": temp_root / "c_candidate_packet.json",
                "trace": temp_root / "cps_trace_events.json",
            }
            preflight.record_preflight_runtime_observation(
                graph_packet,
                observation_files,
                candidate["cps_trace_events"],
                receipt,
            )
            graph_after = store.load("current-system")
            self.assertEqual(graph_after["maat_body"], maat_body)
            self.assertEqual(graph_after["maat_body_digest"], body_digest)
            self.assertEqual(set(graph_after["hermes_kann_addendum"]), {"observations", "source_refs"})
            for observation in graph_after["hermes_kann_addendum"]["observations"]:
                self.assertTrue(set(observation).issubset({
                    "event_id", "event_type", "parent_event_id", "iteration", "phase",
                    "producer_ref", "consumer_ref", "outcome", "normalized_result_hash",
                }))

            parent_receipt = {
                "parent_edge_ref": "C1.P1/S1",
                "status": "pass",
                "changed_paths": [],
                "return_to_node_ref": "C1.P1",
            }
            continuation = preflight.execution_receipt_transition("current-system", graph_root, parent_receipt)
            self.assertEqual(continuation, {"parent_edge_ref": "C1.P1/S1", "disposition": "continue"})
            receipt_sidecar = graph_root / "current-system.execution-receipts.json"
            sidecar_before_hold = receipt_sidecar.read_bytes()

            route = {
                "schema": "harness.cps_preflight.route_gate.v1",
                "status": "pass",
                "C_boundary": "PASS_ONE_C",
                "C": {"C1": "bounded chain"},
                "accepted_P": {"P1": "bounded dispatch"},
                "accepted_S": {"S1": "ptah bounded read-only body"},
                "E": ["P1 -> S1"],
                "selected_agents": {"ptah": {"P": ["P1"], "S": ["S1"]}},
                "verification_gate": {"status": "pass", "gap_class": "none"},
                "physical_docops_gate": {"status": "pass", "gap_classes": []},
                "audit_plan": {"mode": "targeted"},
                "prohibitions": ["no writes"],
                "final_audit_needed": True,
            }
            reducer = {
                "schema": "harness.cps_preflight.maat_reducer_result.v1",
                "status": "pass",
                "revised_C": route["C"],
                "revised_P": route["accepted_P"],
                "revised_S": route["accepted_S"],
                "revised_E": route["E"],
                "final_selected_agents": {"ptah": {"P": ["P1"], "S": ["S1"]}},
                "local_body_scope": {"ptah": "granted_bounded_read_only"},
                "maat_body": maat_body,
                "semantic_anchor": maat_body,
                "semantic_provenance_binding": provenance,
            }
            route["semantic_anchor"] = maat_body
            route["semantic_provenance_binding"] = provenance
            final_result = {
                "status": "pass",
                "AC_verdicts": {},
                "Goal_closure": {"status": "pass", "reason": "mocked complete projection"},
                "missing_evidence": [],
                "failure_codes": [],
            }
            with patch.object(preflight, "invoke_live_maat", return_value=copy.deepcopy(route)), \
                 patch.object(preflight, "probe_agents_as_arrive", return_value=({}, {})), \
                 patch.object(preflight, "invoke_maat_reducer", return_value=copy.deepcopy(reducer)), \
                 patch.object(preflight, "invoke_maat_final_judgment", return_value=final_result) as complete_final:
                complete_chain = preflight.execute_preflight_chain(packet, packet_path, ROOT, "live-maat", candidate)
            complete_final.assert_called_once()
            self.assertEqual(complete_chain["reducer_result"]["node_projection_gate"]["status"], "pass")
            self.assertEqual(list(complete_chain["final_selected_agents"]), ["ptah"])
            self.assertEqual(list(complete_chain["local_bodies"]), ["ptah"])
            self.assertEqual(complete_chain["local_body_dispatch"]["aggregate"]["direct_dispatch_count"], 1)

            external_root = temp_root / "external-runtime-records"
            launch_observations = []
            local_body_bytes = json.dumps(
                complete_chain["local_bodies"]["ptah"], sort_keys=True, ensure_ascii=False, separators=(",", ":")
            ).encode("utf-8")
            identity = {
                "work_id": "current-system", "graph_ref": str(store._path("current-system").resolve()),
                "graph_revision": graph_after["revision"], "graph_digest": graph_after["maat_body_digest"],
                "stage_ref": "S1", "owner_ref": "ptah", "parent_edge_ref": "C1.P1/S1",
                "return_to_node_ref": "C1.P1", "run_handle": "run-current-system", "attempt": 1,
                "immutable_body_digest": hashlib.sha256(local_body_bytes).hexdigest(),
            }

            def observed_launch(argv):
                projection_path = Path(argv[-1])
                job = json.loads(projection_path.read_text(encoding="utf-8"))
                case_dir = projection_path.parent
                body_content = (case_dir / job["facts"]["body_artifact_ref"]).read_bytes()
                launch_observations.append((job["status"], body_content))
                return 987654321

            external_receipts = preflight.dispatch_external_local_bodies(
                complete_chain["local_bodies"],
                external_root,
                identities={"ptah": identity},
                process_runner=observed_launch,
            )
            ptah_receipt = external_receipts["ptah"]
            self.assertEqual(launch_observations[0][0], "observed")
            self.assertEqual(json.loads(launch_observations[0][1]), complete_chain["local_bodies"]["ptah"])
            self.assertEqual(
                set(ptah_receipt["external_runtime_receipt"]),
                {"producer_ref", "runtime_receipt", "consumer_ref"},
            )

            incomplete_packet = copy.deepcopy(packet)
            incomplete_packet.pop("task_AC")
            incomplete_packet["node_projection"].pop("node_local_AC")
            route["final_audit_needed"] = False
            hold_final = Mock(return_value={
                "status": "hold",
                "Goal_closure": {"status": "hold", "reason": "must not be externally dispatched"},
                "missing_evidence": [],
            })
            with patch.object(preflight, "invoke_live_maat", return_value=copy.deepcopy(route)), \
                 patch.object(preflight, "probe_agents_as_arrive", return_value=({}, {})), \
                 patch.object(preflight, "invoke_maat_reducer", return_value=copy.deepcopy(reducer)), \
                 patch.object(preflight, "invoke_maat_final_judgment", hold_final):
                hold_chain = preflight.execute_preflight_chain(
                    incomplete_packet, packet_path, ROOT, "live-maat", candidate
                )

            hold_gate = hold_chain["reducer_result"]["node_projection_gate"]
            self.assertEqual(hold_gate["status"], "hold")
            self.assertEqual(hold_gate["gap_classes"], ["node_projection.node_AC"])
            self.assertEqual(hold_chain["final_selected_agents"], {})
            self.assertEqual(hold_chain["local_bodies"], {})
            self.assertEqual(hold_chain["local_body_dispatch"]["aggregate"]["selected_count"], 0)
            self.assertEqual(hold_chain["local_body_dispatch"]["aggregate"]["direct_dispatch_count"], 0)
            self.assertEqual(hold_chain["final_judgment"], {
                "schema": "harness.cps_preflight.final_maat_judgment.v1",
                "source": "local_node_projection_gate",
                "status": "hold",
                "AC_verdicts": {},
                "Goal_closure": {"status": "hold", "reason": "node projection gate requires missing evidence"},
                "missing_evidence": hold_gate["gap_classes"],
                "failure_codes": ["HOLD_NODE_PROJECTION"],
                "notes": ["External final Maat dispatch was blocked by the node projection gate."],
            })
            self.assertEqual(hold_chain["hold_gap_loop"]["missing_evidence"], hold_gate["gap_classes"])
            self.assertEqual(receipt_sidecar.read_bytes(), sidecar_before_hold)
            self.assertFalse(any("learning" in key.lower() for key in hold_chain))
            self.assertNotIn("learning_candidate", json.dumps(hold_chain, sort_keys=True))
            self.assertNotIn("learning_artifact_source_ref", json.dumps(hold_chain, sort_keys=True))
            self.assertEqual(len(binding_calls), 3)
            hold_final.assert_not_called()

    def test_production_preflight_consumes_navigation_hold_before_dispatch(self):
        packet = {
            "runtime_navigation_request": {
                "requested_target": "contract",
                "requested_refs": [{"ref": "contracts/missing.md"}],
            }
        }
        receipt = {
            "schema": "harness.cps_runtime_navigation_receipt.v1",
            "status": "hold",
            "diagnostic_codes": ["HOLD_RUNTIME_NAVIGATION_REF_MISSING"],
            "resolved_refs": [],
            "c1_runtime_closure": False,
        }
        candidate = {
            "C?": {"C1": "bounded navigation"},
            "route_enrichment": {"selective_maat_escalation": {"needed": True}},
        }
        packet_path = ROOT / "packet.json"
        with patch.object(preflight, "navigate_cps_runtime", return_value=receipt) as navigate, \
             patch.object(preflight, "invoke_live_maat") as route_call, \
             patch.object(preflight, "probe_agents_as_arrive") as probe_call, \
             patch.object(preflight, "invoke_maat_reducer") as reducer_call, \
             patch.object(preflight, "build_agent_body_map") as local_body_map_call, \
             patch.object(preflight, "build_local_body") as local_body_call, \
             patch.object(preflight, "invoke_maat_final_judgment") as final_maat_call:
            chain = preflight.execute_preflight_chain(packet, packet_path, ROOT, "live-maat", candidate)

        navigate.assert_called_once_with(ROOT, packet["runtime_navigation_request"])
        self.assertEqual(chain["runtime_navigation_receipt"], receipt)
        self.assertEqual(chain["final_judgment"]["missing_evidence"], receipt["diagnostic_codes"])
        self.assertEqual(chain["final_selected_agents"], {})
        self.assertEqual(chain["local_bodies"], {})
        for call in (route_call, probe_call, reducer_call, local_body_map_call, local_body_call, final_maat_call):
            self.assertEqual(call.call_count, 0)


if __name__ == "__main__":
    unittest.main()

