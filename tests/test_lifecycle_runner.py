import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

REPO = Path(__file__).resolve().parents[1]
TOOLS = REPO / ".harness" / "hermes" / "tools"
sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location("lifecycle_runner_plan", TOOLS / "lifecycle_runner.py")
assert spec and spec.loader
lifecycle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lifecycle)


class TestLifecycleRunner(unittest.TestCase):
    def test_named_runtime_dispatch_preserves_body_and_calls_existing_dispatch_once(self):
        body = "approved immutable body\n한글".encode()
        identity = {
            "work_id": "incident-i2", "graph_ref": "graph:incident-i2", "graph_revision": 1,
            "graph_digest": "a" * 64, "stage_ref": "I2", "owner_ref": "ptah",
            "parent_edge_ref": "incident/I2", "return_to_node_ref": "anubis",
            "run_handle": "run-i2", "attempt": 1,
            "immutable_body_digest": hashlib.sha256(body).hexdigest(),
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            body_path = root / "body.bin"
            identity_path = root / "identity.json"
            body_path.write_bytes(body)
            identity_path.write_text(json.dumps(identity), encoding="utf-8")
            args = SimpleNamespace(
                runtime_operation="dispatch", body_artifact=str(body_path),
                identity_artifact=str(identity_path), consumer_ref="ptah",
                record_root=str(root / "receipts"),
            )
            observed = {**identity, "status": "observed", "facts": {"event": "poll"}}

            with patch.object(lifecycle, "dispatch_external_body", return_value=observed) as dispatch:
                result = lifecycle.run_named_runtime(args)

            self.assertEqual(result, observed)
            dispatch.assert_called_once_with(
                "ptah", body, root / "receipts", identity=identity,
            )

    def test_named_runtime_dispatch_rejects_identity_digest_and_owner_mismatch_without_launch(self):
        body = b"approved immutable body"
        valid = {
            "work_id": "incident-i2", "graph_ref": "graph:incident-i2", "graph_revision": 1,
            "graph_digest": "a" * 64, "stage_ref": "I2", "owner_ref": "ptah",
            "parent_edge_ref": "incident/I2", "return_to_node_ref": "anubis",
            "run_handle": "run-i2", "attempt": 1,
            "immutable_body_digest": hashlib.sha256(body).hexdigest(),
        }
        cases = (
            (dict(valid, run_handle=None), "receipt identity"),
            (dict(valid, immutable_body_digest="0" * 64), "immutable_body_digest"),
            (dict(valid, owner_ref="anubis"), "consumer_ref"),
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            body_path = root / "body.bin"
            identity_path = root / "identity.json"
            body_path.write_bytes(body)
            args = SimpleNamespace(
                runtime_operation="dispatch", body_artifact=str(body_path),
                identity_artifact=str(identity_path), consumer_ref="ptah",
                record_root=str(root / "receipts"),
            )
            with patch.object(lifecycle, "dispatch_external_body") as dispatch:
                for identity, message in cases:
                    with self.subTest(message=message):
                        identity_path.write_text(json.dumps(identity), encoding="utf-8")
                        with self.assertRaisesRegex((TypeError, ValueError), message):
                            lifecycle.run_named_runtime(args)
                dispatch.assert_not_called()

    def test_named_runtime_status_ignores_empty_stdout_until_terminal_receipt(self):
        import external_runtime_dispatcher as dispatcher

        body = b"approved final-only body"
        identity = {
            "work_id": "incident-i2", "graph_ref": "graph:incident-i2", "graph_revision": 1,
            "graph_digest": "a" * 64, "stage_ref": "I2", "owner_ref": "ptah",
            "parent_edge_ref": "incident/I2", "return_to_node_ref": "anubis",
            "run_handle": "run-i2", "attempt": 1,
            "immutable_body_digest": hashlib.sha256(body).hexdigest(),
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            record_root = root / "receipts"
            identity_path = root / "identity.json"
            identity_path.write_text(json.dumps(identity), encoding="utf-8")
            (root / "sessions.db").write_bytes(b"")
            lifecycle.dispatch_external_body(
                "ptah", body,
                record_root, identity=identity, process_runner=lambda argv: 4242,
            )
            args = SimpleNamespace(
                runtime_operation="status", identity_artifact=str(identity_path),
                record_root=str(record_root), body_artifact=None, consumer_ref=None, runtime_argv=None,
            )
            _, current_path, _ = dispatcher._paths(identity, record_root)
            current = json.loads(current_path.read_text(encoding="utf-8"))
            stdout_path = current_path.parent / current["facts"]["stdout_artifact_ref"]
            self.assertEqual(stdout_path.read_bytes(), b"")

            with patch.object(lifecycle.os, "kill") as kill:
                observed = lifecycle.run_named_runtime(args)
            self.assertEqual(observed["status"], "observed")
            self.assertEqual(observed["facts"]["event"], "poll")
            kill.assert_not_called()

            process = Mock()
            process.wait.return_value = 0
            def native(profile, body_value, correlation, exit_status):
                return {
                    "profile": profile, "correlation_id": correlation,
                    "session_ref": f"state.db:sessions:{profile}", "session_digest": "a" * 64,
                    "exit_status": exit_status, "output_digest": "b" * 64,
                    "gate_status": "pass", "tool_evidence": [],
                }
            with patch.object(dispatcher.subprocess, "Popen", return_value=process), \
                 patch.object(dispatcher, "_native_run_evidence", side_effect=native):
                terminal = dispatcher.run_job(current_path)
            chain_before_readback = dispatcher.load_receipt_chain(identity, record_root)
            readback = lifecycle.run_named_runtime(args)
            chain_after_readback = dispatcher.load_receipt_chain(identity, record_root)

            self.assertEqual(readback, terminal)
            self.assertEqual(chain_after_readback, chain_before_readback)
            self.assertEqual(sum(item["facts"]["event"] == "terminal" for item in chain_after_readback), 1)
            self.assertEqual(stdout_path.read_bytes(), b"")
            for receipt in chain_after_readback:
                for key in ("run_handle", "parent_edge_ref", "return_to_node_ref", "immutable_body_digest"):
                    self.assertEqual(receipt[key], identity[key])

    def test_named_runtime_action_accepts_artifacts_identity_and_consumer_without_argv(self):
        args = lifecycle.build_parser().parse_args([
            "named-runtime", "--runtime-operation", "dispatch",
            "--identity-artifact", "identity.json", "--body-artifact", "body.bin",
            "--consumer-ref", "ptah", "--record-root", "runtime",
        ])
        self.assertEqual(args.action, "named-runtime")
        self.assertEqual(args.runtime_operation, "dispatch")
        self.assertEqual(args.identity_artifact, "identity.json")
        self.assertEqual(args.body_artifact, "body.bin")
        self.assertEqual(args.consumer_ref, "ptah")
        self.assertEqual(args.record_root, "runtime")
        self.assertFalse(hasattr(args, "runtime_argv"))

    def test_named_runtime_reconcile_uses_existing_receipt_boundary(self):
        identity = {
            "work_id": "incident-i2", "graph_ref": "graph:incident-i2", "graph_revision": 1,
            "graph_digest": "a" * 64, "stage_ref": "I2", "owner_ref": "ptah",
            "parent_edge_ref": "incident/I2", "return_to_node_ref": "anubis",
            "run_handle": "run-i2", "attempt": 1, "immutable_body_digest": "b" * 64,
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            identity_path = root / "identity.json"
            identity_path.write_text(json.dumps(identity), encoding="utf-8")
            args = SimpleNamespace(
                runtime_operation="reconcile", identity_artifact=str(identity_path),
                record_root=str(root / "receipts"), body_artifact=None,
                consumer_ref=None, runtime_argv=None,
            )
            observed = {**identity, "status": "observed", "facts": {"event": "blocker"}}
            with patch.object(lifecycle, "reconcile_external_body", return_value=observed) as reconcile:
                result = lifecycle.run_named_runtime(args)

            self.assertEqual(result, observed)
            reconcile.assert_called_once_with(identity, root / "receipts")

    def test_T30_T31_final_audit_adapter_reloads_both_lanes_and_never_closes_goal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            graph = {"revision": 4, "maat_body_digest": "a" * 64, "maat_body": {"goal_eligible": True, "returns_to": []}}
            store = Mock()
            store.load.return_value = graph
            identity = {
                "work_id": "work-1", "graph_ref": str((root / "graphs" / "work-1.yaml").resolve()),
                "graph_revision": 4, "graph_digest": "a" * 64, "stage_ref": "S1", "owner_ref": "ptah",
                "parent_edge_ref": "C1/P1", "return_to_node_ref": "C1", "run_handle": "run-1", "attempt": 1,
                "immutable_body_digest": "b" * 64,
            }
            terminal = {**identity, "status": "pass", "receipt_ref": "run-1:3", "facts": {"event": "terminal"}}
            with patch.object(lifecycle, "WorkingGraphRegistry", return_value=store), \
                 patch.object(lifecycle, "_load_external_runtime_chain", return_value=[terminal]) as reload_chain:
                result = lifecycle.FinalAuditProductionAdapter(root / "graphs", root / "runtime").reload(identity)
            self.assertEqual(result["status"], "eligible_for_maat_audit")
            self.assertNotIn("Goal_closure", result)
            self.assertEqual(result["semantic_lane"]["graph_revision"], 4)
            self.assertEqual(result["execution_lane"]["receipt_ref"], "run-1:3")
            reload_chain.assert_called_once_with(identity, root / "runtime")

    def test_T32_final_audit_adapter_holds_stale_or_incomplete_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            identity = {
                "work_id": "work-1", "graph_ref": str((root / "graphs" / "work-1.yaml").resolve()),
                "graph_revision": 4, "graph_digest": "a" * 64, "stage_ref": "S1", "owner_ref": "ptah",
                "parent_edge_ref": "C1/P1", "return_to_node_ref": "C1", "run_handle": "run-1", "attempt": 1,
                "immutable_body_digest": "b" * 64,
            }
            store = Mock()
            store.load.return_value = {"revision": 5, "maat_body_digest": "c" * 64, "maat_body": {"goal_eligible": True}}
            with patch.object(lifecycle, "WorkingGraphRegistry", return_value=store), patch.object(lifecycle, "_load_external_runtime_chain") as reload_chain:
                result = lifecycle.FinalAuditProductionAdapter(root / "graphs", root / "runtime").reload(identity)
            self.assertEqual(result["status"], "hold")
            self.assertEqual(result["failure_code"], "HOLD_BINDING_MISMATCH")
            reload_chain.assert_not_called()
    def test_preserves_entire_dispatch_plan_in_routing_and_handoff(self):
        plan = {
            "graph_revision": "graph-r2",
            "ready_nodes": ["P1", "P2"],
            "blocked_nodes": {"P3": "dependency:P1"},
            "nodes": {
                "P1": {"owner": "ptah"},
                "P2": {"owner": "anubis"},
                "P3": {"owner": "seshat"},
            },
        }
        routing = {"selected_profile": "ptah", "packet_ref": "packet.json"}
        preflight = {"route_gate": {"dispatch_plan": plan}}

        lifecycle.attach_dispatch_plan(routing, preflight)
        snapshot = lifecycle.build_handoff_snapshot({}, routing, preflight)

        self.assertEqual(routing["dispatch_plan"], plan)
        self.assertEqual(routing["selected_nodes"], ["P1", "P2", "P3"])
        self.assertEqual(routing["ready_nodes"], ["P1", "P2"])
        self.assertEqual(routing["blocked_nodes"], {"P3": "dependency:P1"})
        self.assertEqual(snapshot["dispatch_plan"], plan)
        self.assertEqual(snapshot["selected_nodes"], ["P1", "P2", "P3"])

    def test_external_runtime_production_adapter_requires_identity_and_uses_receipt_path(self):
        body = b"bounded body"
        identity = {
            "work_id": "case-1",
            "graph_ref": "graph:case-1",
            "graph_revision": 2,
            "graph_digest": "a" * 64,
            "stage_ref": "S:W2",
            "owner_ref": "ptah",
            "parent_edge_ref": "C_W2/P1",
            "return_to_node_ref": "C_W2",
            "run_handle": "run-1",
            "attempt": 1,
            "immutable_body_digest": hashlib.sha256(body).hexdigest(),
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            receipt = lifecycle.dispatch_external_body(
                "ptah", body, root,
                identity=identity,
                process_runner=lambda argv: 987654321,
            )
            adapter = lifecycle.ExternalRuntimeProductionAdapter(root)
            polled = adapter.poll(identity)
            self.assertEqual(polled["status"], "observed")
            self.assertEqual(polled["facts"]["event"], "poll")
            self.assertEqual(polled["run_handle"], identity["run_handle"])
            reconciled = adapter.reconcile(identity, pid_is_alive=lambda pid: False)
            self.assertEqual(reconciled["status"], "observed")
            self.assertEqual(reconciled["facts"]["event"], "blocker")

            with self.assertRaisesRegex(TypeError, "explicit receipt identity required"):
                lifecycle.dispatch_external_body(
                    "ptah", body, root,
                    process_runner=lambda argv: 1,
                )

    def test_pre_authorized_transition_production_adapter_reloads_exact_refs_explicitly(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence_root = root / "evidence"
            evidence_root.mkdir()
            document = {"ref": "case.json", "status": "pass"}
            (evidence_root / "case.json").write_text(json.dumps(document), encoding="utf-8")
            store = Mock()

            def materialize(work_id, transition_id, binding, loader):
                self.assertEqual(loader("case.json"), document)
                return {"work_id": work_id, "transition_id": transition_id, "binding": binding}

            store.materialize_pre_authorized_transition.side_effect = materialize
            with patch.object(lifecycle, "WorkingGraphRegistry", return_value=store):
                adapter = lifecycle.PreAuthorizedTransitionProductionAdapter(root / "graphs", evidence_root)
                result = adapter.materialize("work-1", "transition:S1:satisfied", {"graph_revision": 1})

            self.assertEqual(result["transition_id"], "transition:S1:satisfied")
            store.materialize_pre_authorized_transition.assert_called_once()

    def test_pre_authorized_transition_adapter_rejects_ref_escape_and_terminal_dispatch_does_not_materialize(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence_root = root / "evidence"
            evidence_root.mkdir()
            store = Mock()

            def materialize(work_id, transition_id, binding, loader):
                del work_id, transition_id, binding
                loader("../outside.json")

            store.materialize_pre_authorized_transition.side_effect = materialize
            with patch.object(lifecycle, "WorkingGraphRegistry", return_value=store):
                adapter = lifecycle.PreAuthorizedTransitionProductionAdapter(root / "graphs", evidence_root)
                with self.assertRaisesRegex(lifecycle.RegistryError, "HOLD_PREAUTH_PREDICATE"):
                    adapter.materialize("work-1", "transition:S1:satisfied", {})

            with patch.object(lifecycle.PreAuthorizedTransitionProductionAdapter, "materialize") as automatic:
                lifecycle.dispatch_external_body(
                    "ptah", b"terminal receipt", root / "runtime",
                    identity={
                        "work_id": "work-1", "graph_ref": "graph:work-1", "graph_revision": 1,
                        "graph_digest": "a" * 64, "stage_ref": "S1", "owner_ref": "ptah",
                        "parent_edge_ref": "edge:S1", "return_to_node_ref": "S1",
                        "run_handle": "run-1", "attempt": 1,
                        "immutable_body_digest": hashlib.sha256(b"terminal receipt").hexdigest(),
                    },
                    process_runner=lambda argv: 123456789,
                )
                automatic.assert_not_called()


class TestR2ReceiptBackedStateProjection(unittest.TestCase):
    projection_fields = {
        "authorization_state", "runtime_state", "execution_status", "execution_receipt_ref",
        "execution_event", "run_handle", "attempt", "recorded_at", "audit_verdict", "state_source_ref",
    }

    def setUp(self):
        self.body = b"r2 body"
        self.identity = {
            "work_id": "work-r2", "graph_ref": "graph:work-r2", "graph_revision": 2,
            "graph_digest": "a" * 64, "stage_ref": "S:R2", "owner_ref": "ptah",
            "parent_edge_ref": "C_R2/P1", "return_to_node_ref": "C_R2",
            "run_handle": "run-r2", "attempt": 1,
            "immutable_body_digest": hashlib.sha256(self.body).hexdigest(),
        }
        self.authorization = {
            "authorization_state": "ISSUED", "identity": self.identity,
            "recorded_at": "2026-07-16T00:00:00+00:00", "state_source_ref": "authorization:work-r2",
        }

    def dispatch(self, root):
        lifecycle.dispatch_external_body(
            "ptah", self.body, root,
            identity=self.identity, process_runner=lambda argv: 123456789,
        )

    def paths(self, root):
        import external_runtime_dispatcher as dispatcher
        return dispatcher._paths(self.identity, root)[:2]

    def load_records(self, root):
        chain_path, current_path = self.paths(root)
        records = [json.loads(line) for line in chain_path.read_text(encoding="utf-8").splitlines()]
        return chain_path, current_path, records

    def write_records(self, chain_path, current_path, records):
        chain_path.write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")
        current_path.write_text(json.dumps(records[-1]), encoding="utf-8")

    def test_R2_01_authorization_only_projects_issued_with_exact_fields_and_null_runtime_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            projection = lifecycle.ExternalRuntimeStateProjectionAdapter(Path(tmp)).project(self.authorization)
        self.assertEqual(set(projection), self.projection_fields)
        self.assertEqual(projection["authorization_state"], "ISSUED")
        for field in ("runtime_state", "execution_status", "execution_receipt_ref", "execution_event", "run_handle", "attempt", "audit_verdict"):
            self.assertIsNone(projection[field])
        self.assertEqual(projection["state_source_ref"], "authorization:work-r2")

    def test_R2_02_delegation_self_report_caller_boolean_pid_and_memory_claims_do_not_make_running(self):
        claims = dict(self.authorization, delegation_status="running", self_report="RUNNING", caller_running=True, pid=42, in_memory_state="RUNNING")
        with tempfile.TemporaryDirectory() as tmp:
            projection = lifecycle.project_external_runtime_state(claims, Path(tmp))
        self.assertIsNone(projection["runtime_state"])
        self.assertIsNone(projection["execution_event"])

    def test_R2_03_exact_dispatch_receipt_reload_projects_running(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.dispatch(root)
            chain_path, current_path, records = self.load_records(root)
            self.write_records(chain_path, current_path, records[:1])
            projection = lifecycle.project_external_runtime_state(self.authorization, root)
        self.assertEqual(projection["runtime_state"], "RUNNING")
        self.assertEqual(projection["execution_event"], "dispatch")
        self.assertIsNone(projection["execution_status"])

    def test_R2_04_poll_and_blocker_receipts_project_running(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.dispatch(root)
            for event in ("poll", "blocker"):
                if event == "poll":
                    lifecycle.poll_external_body(self.identity, root)
                elif event == "blocker":
                    lifecycle.reconcile_external_body(self.identity, root, pid_is_alive=lambda pid: False)
                projection = lifecycle.project_external_runtime_state(self.authorization, root)
                self.assertEqual(projection["runtime_state"], "RUNNING")
                self.assertEqual(projection["execution_event"], event)
                self.assertIsNone(projection["execution_status"])

    def test_R2_05_terminal_pass_fail_blocked_are_execution_status_only_and_audit_stays_null(self):
        import external_runtime_dispatcher as dispatcher
        for status in ("pass", "fail", "blocked"):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.dispatch(root)
                dispatcher.append_terminal_receipt(self.identity, root, status)
                projection = lifecycle.project_external_runtime_state(self.authorization, root)
                self.assertEqual(projection["runtime_state"], "TERMINAL")
                self.assertEqual(projection["execution_status"], status)
                self.assertEqual(projection["execution_event"], "terminal")
                self.assertIsNone(projection["audit_verdict"])
                self.assertNotIn(status.upper(), projection.values())

    def test_R2_06_missing_receipts_fail_closed_without_writes_or_no_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            before = list(root.rglob("*"))
            projection = lifecycle.project_external_runtime_state(self.authorization, root)
            after = list(root.rglob("*"))
        self.assertEqual(before, after)
        self.assertIsNone(projection["runtime_state"])
        self.assertNotIn("NO_OUTPUT", projection.values())

    def test_R2_07_malformed_receipts_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.dispatch(root)
            chain_path, _, _ = self.load_records(root)
            chain_path.write_text("{malformed\n", encoding="utf-8")
            projection = lifecycle.project_external_runtime_state(self.authorization, root)
        self.assertIsNone(projection["runtime_state"])
        self.assertIsNone(projection["execution_receipt_ref"])

    def test_R2_08_current_must_equal_chain_tail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.dispatch(root)
            _, current_path, records = self.load_records(root)
            current_path.write_text(json.dumps(records[0]), encoding="utf-8")
            projection = lifecycle.project_external_runtime_state(self.authorization, root)
        self.assertIsNone(projection["runtime_state"])

    def test_R2_09_receipt_identity_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.dispatch(root)
            chain_path, current_path, records = self.load_records(root)
            records[-1]["owner_ref"] = "caller"
            self.write_records(chain_path, current_path, records)
            projection = lifecycle.project_external_runtime_state(self.authorization, root)
        self.assertIsNone(projection["runtime_state"])

    def test_R2_10_post_terminal_receipt_mismatch_fails_closed(self):
        import external_runtime_dispatcher as dispatcher
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.dispatch(root)
            dispatcher.append_terminal_receipt(self.identity, root, "pass")
            chain_path, current_path, records = self.load_records(root)
            post_terminal = dict(records[-2])
            post_terminal["receipt_ref"] = f"{self.identity['run_handle']}:{len(records) + 1}"
            post_terminal["transition_from_ref"] = records[-1]["receipt_ref"]
            post_terminal["recorded_at"] = "2026-07-16T00:00:01+00:00"
            post_terminal["facts"] = dict(post_terminal["facts"], event="poll")
            records.append(post_terminal)
            self.write_records(chain_path, current_path, records)
            projection = lifecycle.project_external_runtime_state(self.authorization, root)
        self.assertIsNone(projection["runtime_state"])
        self.assertIsNone(projection["execution_status"])

    def test_R2_11_projection_exposes_receipt_identity_and_current_source_ref_without_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.dispatch(root)
            _, current_path = self.paths(root)
            before = {path: path.read_bytes() for path in root.rglob("*") if path.is_file()}
            projection = lifecycle.project_external_runtime_state(self.authorization, root)
            after = {path: path.read_bytes() for path in root.rglob("*") if path.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(projection["execution_receipt_ref"], "run-r2:2")
        self.assertEqual(projection["run_handle"], "run-r2")
        self.assertEqual(projection["attempt"], 1)
        self.assertEqual(projection["state_source_ref"], str(current_path.resolve()))


if __name__ == "__main__":
    unittest.main()
