import hashlib
import importlib.util
import inspect
import json
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
TOOLS = REPO / ".harness" / "hermes" / "tools"
sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location("external_runtime_dispatcher", TOOLS / "external_runtime_dispatcher.py")
assert spec and spec.loader
dispatcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dispatcher)


class ExternalRuntimeDispatcherTests(unittest.TestCase):
    def identity(self, body=b"bounded body", run_handle="run-1"):
        return {
            "work_id": "case-1",
            "graph_ref": "graph:case-1",
            "graph_revision": 2,
            "graph_digest": "a" * 64,
            "stage_ref": "S:W2",
            "owner_ref": "ptah",
            "parent_edge_ref": "C_W2/P1",
            "return_to_node_ref": "C_W2",
            "run_handle": run_handle,
            "attempt": 1,
            "immutable_body_digest": hashlib.sha256(body).hexdigest(),
        }

    def test_dispatch_appends_durable_observed_before_launch_and_uses_identity(self):
        body = "maat immutable body\n정확".encode()
        identity = self.identity(body)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            seen = {}

            def launch(argv):
                chain = dispatcher.load_receipt_chain(identity, root)
                seen["chain"] = chain
                _, current_path, _ = dispatcher._paths(identity, root)
                seen["runner_argv"] = argv
                seen["projection"] = json.loads(current_path.read_text(encoding="utf-8"))
                seen["body"] = (current_path.parent / chain[-1]["facts"]["body_artifact_ref"]).read_bytes()
                return 4321

            receipt = dispatcher.dispatch_external_runtime(
                "ptah", body, root,
                identity=identity, process_runner=launch,
            )

            self.assertEqual(len(seen["chain"]), 1)
            self.assertEqual(seen["chain"][0]["status"], "observed")
            self.assertEqual(seen["chain"][0]["facts"]["event"], "dispatch")
            self.assertEqual(seen["projection"], seen["chain"][0])
            self.assertEqual(seen["body"], body)
            _, current_path, _ = dispatcher._paths(identity, root)
            self.assertEqual(seen["runner_argv"], dispatcher._runner_argv(current_path))
            facts = seen["chain"][0]["facts"]
            expected_argv = [
                "hermes", "-p", "ptah", "chat", "-Q", "--pass-session-id", "--source",
                f"harness:{facts['native_correlation_id']}", "--max-turns", "8",
                "-t", "file", "-q", body.decode(),
            ]
            self.assertEqual(facts["argv"], expected_argv)
            self.assertEqual(facts["argv"][-1].encode(), body)
            self.assertNotIn("-z", facts["argv"])
            self.assertNotIn("HERMES_HOME", json.dumps(facts))
            self.assertEqual(facts["body_artifact_ref"], "artifacts/body.bin")
            self.assertEqual(facts["body_digest"], hashlib.sha256(body).hexdigest())
            self.assertEqual(facts["body_byte_count"], len(body))
            for stream in ("stdout", "stderr"):
                self.assertEqual(facts[f"{stream}_artifact_ref"], f"artifacts/{stream}.bin")
                self.assertEqual(facts[f"{stream}_digest"], hashlib.sha256(b"").hexdigest())
                self.assertEqual(facts[f"{stream}_byte_count"], 0)
            self.assertFalse(any(key.endswith("_path") for key in facts))
            self.assertEqual(receipt["status"], "observed")
            self.assertEqual(receipt["facts"]["event"], "poll")
            self.assertEqual(receipt["facts"]["pid"], 4321)
            for key, value in identity.items():
                self.assertEqual(receipt[key], value)
            self.assertEqual(len(dispatcher.load_receipt_chain(identity, root)), 2)
            other_edge = dict(identity, parent_edge_ref="C_W2/P2")
            self.assertNotEqual(dispatcher._case_dir(identity, root), dispatcher._case_dir(other_edge, root))
            for projected in dispatcher.load_receipt_chain(identity, root):
                self.assertEqual(projected["parent_edge_ref"], identity["parent_edge_ref"])
                self.assertEqual(projected["return_to_node_ref"], identity["return_to_node_ref"])
            for key in dispatcher.SEMANTIC_KEYS:
                self.assertNotIn(key, receipt["facts"])

    def test_legacy_caller_argv_overload_is_removed(self):
        parameters = inspect.signature(dispatcher.dispatch_external_runtime).parameters
        self.assertEqual(list(parameters)[:3], ["consumer_ref", "body", "record_root"])
        self.assertNotIn("argv", parameters)
        self.assertNotIn("legacy_record_root", parameters)

    def test_poll_and_lost_blocker_append_observed_until_terminal_then_only_reload(self):
        identity = self.identity()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            receipt = dispatcher.dispatch_external_runtime(
                "ptah", b"bounded body", root,
                identity=identity, process_runner=lambda argv: 987654321,
            )
            polled = dispatcher.poll_external_runtime(identity, root)
            self.assertEqual(polled["status"], "observed")
            self.assertEqual(polled["facts"]["event"], "poll")
            lost = dispatcher.reconcile_external_runtime(identity, root, pid_is_alive=lambda pid: False)
            self.assertEqual(lost["status"], "observed")
            self.assertEqual(lost["facts"]["event"], "blocker")
            self.assertEqual(lost["errors"], ["runtime:lost"])
            stale = dispatcher.reconcile_external_runtime(
                identity, root, pid_is_alive=lambda pid: True, stale_after_seconds=0,
            )
            self.assertEqual(stale["status"], "observed")
            self.assertEqual(stale["facts"]["event"], "blocker")
            self.assertEqual(stale["errors"], ["runtime:stale"])

            terminal = dispatcher.append_terminal_receipt(identity, root, "blocked", errors=["runtime:terminated"])
            chain_path, current_path, _ = dispatcher._paths(identity, root)
            terminal_digests = (
                hashlib.sha256(chain_path.read_bytes()).digest(),
                hashlib.sha256(current_path.read_bytes()).digest(),
            )
            self.assertEqual(dispatcher.poll_external_runtime(identity, root), terminal)
            self.assertEqual(
                (hashlib.sha256(chain_path.read_bytes()).digest(), hashlib.sha256(current_path.read_bytes()).digest()),
                terminal_digests,
            )
            with self.assertRaisesRegex(RuntimeError, "terminal receipt already recorded"):
                dispatcher.reconcile_external_runtime(identity, root, pid_is_alive=lambda pid: False)
            self.assertEqual(
                (hashlib.sha256(chain_path.read_bytes()).digest(), hashlib.sha256(current_path.read_bytes()).digest()),
                terminal_digests,
            )
            with self.assertRaisesRegex(RuntimeError, "terminal receipt already recorded"):
                dispatcher.append_terminal_receipt(identity, root, "pass")
            self.assertEqual(
                (hashlib.sha256(chain_path.read_bytes()).digest(), hashlib.sha256(current_path.read_bytes()).digest()),
                terminal_digests,
            )

    def test_event_status_matrix_and_transition_continuity_reject_before_write(self):
        identity = self.identity()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dispatcher.dispatch_external_runtime(
                "ptah", b"bounded body", root,
                identity=identity, process_runner=lambda argv: 1234,
            )
            chain_path, current_path, _ = dispatcher._paths(identity, root)
            chain = dispatcher.load_receipt_chain(identity, root)
            self.assertEqual([item["transition_from_ref"] for item in chain], [None, chain[0]["receipt_ref"]])

            for event, status in (("heartbeat", "pass"), ("terminal", "observed"), ("unknown", "observed")):
                before = (chain_path.read_bytes(), current_path.read_bytes())
                with self.subTest(event=event, status=status), dispatcher._case_lock(identity, root):
                    with self.assertRaisesRegex(ValueError, "event/status combination"):
                        dispatcher._append_locked(identity, root, "ptah", status, {"event": event})
                self.assertEqual((chain_path.read_bytes(), current_path.read_bytes()), before)

            current_path.write_text(json.dumps(chain[0], sort_keys=True), encoding="utf-8")
            before = (chain_path.read_bytes(), current_path.read_bytes())
            with self.assertRaisesRegex(RuntimeError, "current projection does not match chain tail"):
                dispatcher.poll_external_runtime(identity, root)
            self.assertEqual((chain_path.read_bytes(), current_path.read_bytes()), before)

            current_path.write_text(json.dumps(chain[-1], sort_keys=True), encoding="utf-8")
            broken = list(chain)
            broken[-1] = dict(broken[-1], transition_from_ref="broken")
            chain_path.write_text("".join(json.dumps(item, sort_keys=True) + "\n" for item in broken), encoding="utf-8")
            before = (chain_path.read_bytes(), current_path.read_bytes())
            with self.assertRaisesRegex(RuntimeError, "broken receipt transition"):
                dispatcher.poll_external_runtime(identity, root)
            self.assertEqual((chain_path.read_bytes(), current_path.read_bytes()), before)

            chain_path.write_text("{malformed\n", encoding="utf-8")
            before = (chain_path.read_bytes(), current_path.read_bytes())
            with self.assertRaisesRegex(RuntimeError, "malformed receipt chain"):
                dispatcher.poll_external_runtime(identity, root)
            self.assertEqual((chain_path.read_bytes(), current_path.read_bytes()), before)

    def test_terminal_rejects_raw_stdout_before_receipt_writes(self):
        identity = self.identity()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dispatcher.dispatch_external_runtime(
                "ptah", b"bounded body", root,
                identity=identity, process_runner=lambda argv: 1234,
            )
            chain_path, current_path, _ = dispatcher._paths(identity, root)
            before = (chain_path.read_bytes(), current_path.read_bytes())

            with self.assertRaisesRegex(ValueError, "runtime facts"):
                dispatcher.append_terminal_receipt(
                    identity, root, "pass", facts={"raw_stdout": "secret"},
                )

            self.assertEqual((chain_path.read_bytes(), current_path.read_bytes()), before)

    def test_terminal_rejects_goal_eligible_before_receipt_writes(self):
        identity = self.identity()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dispatcher.dispatch_external_runtime(
                "ptah", b"bounded body", root,
                identity=identity, process_runner=lambda argv: 1234,
            )
            chain_path, current_path, _ = dispatcher._paths(identity, root)
            before = (chain_path.read_bytes(), current_path.read_bytes())

            with self.assertRaisesRegex(ValueError, "runtime facts"):
                dispatcher.append_terminal_receipt(
                    identity, root, "pass", facts={"goal_eligible": True},
                )

            self.assertEqual((chain_path.read_bytes(), current_path.read_bytes()), before)

    def test_terminal_is_first_writer_wins_under_concurrency(self):
        identity = self.identity()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dispatcher.dispatch_external_runtime(
                "ptah", b"bounded body", root,
                identity=identity, process_runner=lambda argv: 1234,
            )

            def write(status):
                try:
                    return dispatcher.append_terminal_receipt(identity, root, status)
                except RuntimeError as exc:
                    return str(exc)

            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(write, ("pass", "fail")))

            winners = [item for item in results if isinstance(item, dict)]
            rejected = [item for item in results if isinstance(item, str)]
            self.assertEqual(len(winners), 1)
            self.assertEqual(rejected, ["terminal receipt already recorded"])
            terminals = [item for item in dispatcher.load_receipt_chain(identity, root) if item["status"] in dispatcher.TERMINAL_STATUSES]
            self.assertEqual(terminals, winners)

    def test_run_job_executes_closed_native_argv_and_correlates_native_records(self):
        body = b"approved native body"
        identity = self.identity(body)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dispatcher.dispatch_external_runtime(
                "ptah", body, root, identity=identity, process_runner=lambda argv: 999,
            )
            _, current_path, _ = dispatcher._paths(identity, root)
            process = mock.Mock()
            process.wait.return_value = 0
            def native(profile, body_value, correlation, exit_status):
                self.assertEqual(body_value, body)
                return {
                    "profile": profile, "correlation_id": correlation,
                    "session_ref": f"state.db:sessions:{profile}", "session_digest": "c" * 64,
                    "exit_status": exit_status, "output_digest": "d" * 64,
                    "gate_status": "pass", "tool_evidence": [{
                        "tool_name": "terminal", "canonical_input_digest": "e" * 64,
                        "exit_status": 0, "output_digest": "f" * 64,
                    }],
                }
            with mock.patch.object(dispatcher.subprocess, "Popen", return_value=process) as popen, \
                 mock.patch.object(dispatcher, "_native_run_evidence", side_effect=native):
                final = dispatcher.run_job(current_path)
            self.assertEqual(popen.call_count, 3)
            self.assertEqual([call.args[0][2] for call in popen.call_args_list], ["ptah", "anubis", "maat"])
            self.assertEqual(final["status"], "pass")
            self.assertEqual(final["facts"]["exit_code"], 0)
            self.assertEqual(final["receipt_ref"], f"{identity['run_handle']}:3")
            self.assertEqual(final["facts"]["body_digest"], hashlib.sha256(body).hexdigest())
            self.assertEqual([run["profile"] for run in final["facts"]["native_runs"]], ["ptah", "anubis", "maat"])
            self.assertTrue(all(run["correlation_id"] == final["facts"]["native_correlation_id"] for run in final["facts"]["native_runs"]))

    def test_native_session_absence_mismatch_and_duplicate_correlation_close_as_hold(self):
        body = b"native hold body"
        identity = self.identity(body)
        for error in (
            "native session store absent",
            "native session body mismatch",
            "native correlation absent or duplicated",
        ):
            with self.subTest(error=error), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                dispatcher.dispatch_external_runtime(
                    "ptah", body, root, identity=identity, process_runner=lambda argv: 999,
                )
                _, current_path, _ = dispatcher._paths(identity, root)
                process = mock.Mock()
                process.wait.return_value = 0
                with mock.patch.object(dispatcher.subprocess, "Popen", return_value=process), \
                     mock.patch.object(dispatcher, "_native_run_evidence", side_effect=RuntimeError(error)):
                    terminal = dispatcher.run_job(current_path)
                self.assertEqual(terminal["status"], "blocked")
                self.assertNotEqual(terminal["status"], "pass")
                self.assertIn(error, terminal["errors"][0])
                self.assertEqual(terminal["facts"]["native_runs"], [])

    def test_rejects_non_text_and_owner_profile_mismatch_before_launch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            launch = mock.Mock(return_value=1)
            binary = b"\xff"
            with self.assertRaisesRegex(ValueError, "UTF-8 text"):
                dispatcher.dispatch_external_runtime(
                    "ptah", binary, root, identity=self.identity(binary), process_runner=launch,
                )
            with self.assertRaisesRegex(ValueError, "owner_ref"):
                dispatcher.dispatch_external_runtime(
                    "anubis", b"bounded body", root, identity=self.identity(), process_runner=launch,
                )
            launch.assert_not_called()
            self.assertEqual(list(root.rglob("*")), [])

    def test_execution_receipt_schema_carries_exact_runtime_artifact_metadata(self):
        schema_path = REPO / ".harness" / "hermes" / "schemas" / "execution-receipt.schema.yaml"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        receipt = schema["$defs"]["execution_receipt"]
        self.assertIn("transition_from_ref", receipt["required"])
        facts = schema["$defs"]["external_runtime_facts"]
        artifact_fields = {
            f"{stream}_{suffix}"
            for stream in ("body", "stdout", "stderr")
            for suffix in ("artifact_ref", "digest", "byte_count")
        }
        self.assertTrue(artifact_fields <= set(facts["required"]))
        self.assertTrue(artifact_fields <= set(facts["properties"]))
        self.assertFalse(facts["additionalProperties"])
        self.assertFalse(any(key.endswith("_path") for key in facts["properties"]))

    def test_rejects_missing_or_mismatched_explicit_identity_without_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(TypeError):
                dispatcher.dispatch_external_runtime("ptah", b"body", root)
            identity = self.identity(b"other")
            with self.assertRaisesRegex(ValueError, "immutable_body_digest"):
                dispatcher.dispatch_external_runtime(
                    "ptah", b"body", root,
                    identity=identity, process_runner=lambda argv: 1,
                )
            self.assertEqual(list(root.rglob("*")), [])


if __name__ == "__main__":
    unittest.main()
