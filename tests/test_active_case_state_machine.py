import ast
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock, patch

REPO = Path(__file__).resolve().parents[1]
TOOLS = REPO / ".harness" / "hermes" / "tools"
FIXTURES = Path(__file__).with_name("fixtures") / "active_case_state"
CONTRACT = REPO.parent / "harness-brain" / "projects" / REPO.name / "contracts" / "cp_active_case_state_test_system.md"
sys.path.insert(0, str(TOOLS))

import cps_working_graph_registry as registry
import cps_preflight_route_gate as preflight
import external_runtime_dispatcher as dispatcher
import lifecycle_runner as lifecycle


class ActiveCaseStateMachineTests(unittest.TestCase):
    def load_fixture(self, name):
        return json.loads((FIXTURES / name).read_text(encoding="utf-8"))

    def matrix(self):
        return self.load_fixture("matrix.json")["cases"]

    def test_machine_enforces_canonical_T01_T32_fixture_and_production_test_coverage(self):
        cases = self.matrix()
        expected_ids = ["T01", "T02", "T02a", *[f"T{index:02d}" for index in range(3, 33)]]
        required = {
            "id", "input", "initial_graph_fixture", "receipt_sequence_fixture",
            "authorization_fixture", "predicate_result", "expected_revision_delta",
            "expected_hold", "persisted_refs", "readback_digest",
            "forbidden_write_assertion", "production_entrypoint", "test_ref",
        }
        self.assertEqual([case["id"] for case in cases], expected_ids)
        self.assertEqual(len({case["id"] for case in cases}), len(expected_ids))

        canonical = CONTRACT.read_text(encoding="utf-8")
        for test_id in expected_ids[:-3]:
            self.assertIn(f"| {test_id} |", canonical)

        for case in cases:
            with self.subTest(case=case["id"]):
                self.assertEqual(set(case), required)
                self.assertTrue((FIXTURES / case["initial_graph_fixture"]).is_file())
                self.assertTrue((FIXTURES / case["receipt_sequence_fixture"]).is_file())
                if case["authorization_fixture"] is not None:
                    self.assertTrue((FIXTURES / case["authorization_fixture"]).is_file())
                self.assertRegex(case["readback_digest"], r"^[0-9a-f]{64}$")
                self.assertTrue(case["forbidden_write_assertion"])
                path_ref, class_name, method_name = case["test_ref"].split("::")
                source_path = REPO / path_ref
                self.assertTrue(source_path.is_file())
                tree = ast.parse(source_path.read_text(encoding="utf-8"))
                classes = {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}
                self.assertIn(class_name, classes)
                methods = {node.name for node in classes[class_name].body if isinstance(node, ast.FunctionDef)}
                self.assertIn(method_name, methods)

    def test_fixture_digests_and_refs_are_deterministic(self):
        graph = self.load_fixture("initial_graph.json")
        body_digest = hashlib.sha256(
            json.dumps(graph["maat_body"], sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        ).hexdigest()
        self.assertEqual(graph["maat_body_digest"], body_digest)
        self.assertTrue(all(case["readback_digest"] == body_digest for case in self.matrix()))
        sequence = self.load_fixture("receipt_sequences.json")
        self.assertEqual(sequence["identity"]["graph_digest"], body_digest)
        self.assertEqual(
            sequence["identity"]["immutable_body_digest"],
            hashlib.sha256(b"authorized W5 body").hexdigest(),
        )

    def test_T02a_event_status_compatibility_is_exhaustive(self):
        sequence = self.load_fixture("receipt_sequences.json")
        accepted = {(item["event_kind"], item["status"]) for item in sequence["valid"]}
        rejected = {(item["event_kind"], item["status"]) for item in sequence["invalid"]}
        universe = {
            (event, status)
            for event in ("dispatch", "heartbeat", "poll", "blocker", "terminal")
            for status in ("observed", "pass", "fail", "blocked")
        }
        self.assertEqual(accepted | rejected, universe)
        self.assertFalse(accepted & rejected)
        for event, status in accepted:
            dispatcher._validate_event_status(event, status)
        for event, status in rejected:
            with self.assertRaisesRegex(ValueError, "event/status combination"):
                dispatcher._validate_event_status(event, status)

    def _registry_test_helpers(self):
        path = REPO / "tests" / "test_cps_working_graph_registry.py"
        spec = importlib.util.spec_from_file_location("w5_registry_test_helpers", path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.WorkingGraphRegistryTests()

    def test_T16_crash_before_CAS_has_no_partial_write_and_retry_recovers(self):
        helpers = self._registry_test_helpers()
        with tempfile.TemporaryDirectory() as tmp:
            store, graph, documents, binding = helpers.preauth_fixture(Path(tmp))
            graph_path = store._path("work-1")
            preimage = graph_path.read_bytes()
            with patch.object(registry, "_write", side_effect=OSError("crash before CAS")):
                with self.assertRaisesRegex(registry.RegistryError, "HOLD_PREAUTH_READBACK"):
                    helpers.materialize(store, documents, binding)
            self.assertEqual(graph_path.read_bytes(), preimage)
            result = helpers.materialize(store, documents, binding)
            self.assertEqual(result["resulting_revision"], graph["revision"] + 1)
            self.assertEqual(store.load("work-1")["materialized_transitions"], [result])

    def test_T17_crash_after_write_replay_reads_same_materialization_without_duplicate(self):
        helpers = self._registry_test_helpers()
        with tempfile.TemporaryDirectory() as tmp:
            store, graph, documents, binding = helpers.preauth_fixture(Path(tmp))
            first = helpers.materialize(store, documents, binding)
            written = store._path("work-1").read_bytes()
            replay = store.materialize_pre_authorized_transition(
                "work-1", first["transition_id"], {}, lambda ref: {},
            )
            readback = store.load("work-1")
            self.assertEqual(replay, first)
            self.assertEqual(store._path("work-1").read_bytes(), written)
            self.assertEqual(readback["revision"], graph["revision"] + 1)
            self.assertEqual(readback["materialized_transitions"], [first])

    def test_T21_final_Maat_audit_absence_holds_without_goal_closure(self):
        result = preflight.load_production_final_audit(None)
        self.assertEqual(result, {"status": "hold", "failure_code": "HOLD_FINAL_GATE"})
        self.assertNotIn("Goal_closure", result)

    def test_T22_automatic_root_goal_close_is_rejected_without_write(self):
        helpers = self._registry_test_helpers()
        with tempfile.TemporaryDirectory() as tmp:
            store, _, documents, binding = helpers.preauth_fixture(Path(tmp))
            graph = store.load("work-1")
            authorization = graph["pre_authorized_transitions"][0]
            authorization["source_state_ref"] = "/maat_body/root_goal_status"
            authorization["source_lifecycle"] = "open"
            authorization["target"] = {
                "target_state_ref": "/maat_body/root_goal_status",
                "target_lifecycle": "closed",
            }
            authorization["allowed_delta_paths"] = ["/maat_body/root_goal_status"]
            registry._write(store._path("work-1"), graph)
            preimage = store._path("work-1").read_bytes()
            with self.assertRaisesRegex(registry.RegistryError, "HOLD_PREAUTH_SCOPE"):
                helpers.materialize(store, documents, binding)
            self.assertEqual(store._path("work-1").read_bytes(), preimage)

    def test_T28_complete_joint_evidence_is_only_eligible_for_Maat_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            identity = {
                "work_id": "work-1", "graph_ref": str((root / "graphs" / "work-1.yaml").resolve()),
                "graph_revision": 4, "graph_digest": "a" * 64, "stage_ref": "S1", "owner_ref": "ptah",
                "parent_edge_ref": "C1/P1", "return_to_node_ref": "C1", "run_handle": "run-1",
                "attempt": 1, "immutable_body_digest": "b" * 64,
            }
            graph = {
                "revision": 4, "maat_body_digest": "a" * 64,
                "maat_body": {"goal_eligible": True, "root_goal_status": "open", "returns_to": []},
            }
            terminal = {**identity, "status": "pass", "receipt_ref": "run-1:3", "facts": {"event": "terminal"}}
            store = Mock()
            store.load.return_value = deepcopy(graph)
            store.verify_readback.return_value = True
            with patch.object(lifecycle, "WorkingGraphRegistry", return_value=store), \
                 patch.object(lifecycle, "_load_external_runtime_chain", return_value=[terminal]):
                result = lifecycle.FinalAuditProductionAdapter(root / "graphs", root / "runtime").reload(identity)
            self.assertEqual(result["status"], "eligible_for_maat_audit")
            self.assertNotIn("Goal_closure", result)
            self.assertEqual(store.load.return_value["maat_body"]["root_goal_status"], "open")


if __name__ == "__main__":
    unittest.main()
