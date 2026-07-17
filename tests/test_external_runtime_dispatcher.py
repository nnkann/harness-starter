import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

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
        body = b"\x00maat-body\xff"
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
                "ptah", body, [sys.executable, "worker.py"], root,
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
            self.assertEqual(facts["body_artifact_ref"], "artifacts/body.bin")
            self.assertEqual(facts["body_digest"], hashlib.sha256(body).hexdigest())
            self.assertEqual(facts["body_byte_count"], len(body))
            for stream in ("stdout", "stderr"):
                self.assertEqual(facts[f"{stream}_artifact_ref"], f"artifacts/{stream}.bin")
                self.assertEqual(facts[f"{stream}_digest"], hashlib.sha256(b"").hexdigest())
                self.assertEqual(facts[f"{stream}_byte_count"], 0)
            self.assertFalse(any(key.endswith("_path") for key in facts))
            self.assertEqual(receipt["status"], "observed")
            self.assertEqual(receipt["facts"]["event"], "heartbeat")
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

    def test_poll_and_lost_blocker_append_observed_until_terminal_then_only_reload(self):
        identity = self.identity()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            receipt = dispatcher.dispatch_external_runtime(
                "ptah", b"bounded body", [sys.executable, "worker.py"], root,
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
                dispatcher.append_heartbeat(identity, root, pid=1)
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
                "ptah", b"bounded body", [sys.executable, "worker.py"], root,
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
                dispatcher.append_heartbeat(identity, root, pid=2)
            self.assertEqual((chain_path.read_bytes(), current_path.read_bytes()), before)

            current_path.write_text(json.dumps(chain[-1], sort_keys=True), encoding="utf-8")
            broken = list(chain)
            broken[-1] = dict(broken[-1], transition_from_ref="broken")
            chain_path.write_text("".join(json.dumps(item, sort_keys=True) + "\n" for item in broken), encoding="utf-8")
            before = (chain_path.read_bytes(), current_path.read_bytes())
            with self.assertRaisesRegex(RuntimeError, "broken receipt transition"):
                dispatcher.append_heartbeat(identity, root, pid=2)
            self.assertEqual((chain_path.read_bytes(), current_path.read_bytes()), before)

            chain_path.write_text("{malformed\n", encoding="utf-8")
            before = (chain_path.read_bytes(), current_path.read_bytes())
            with self.assertRaisesRegex(RuntimeError, "malformed receipt chain"):
                dispatcher.append_heartbeat(identity, root, pid=2)
            self.assertEqual((chain_path.read_bytes(), current_path.read_bytes()), before)

    def test_terminal_rejects_raw_stdout_before_receipt_writes(self):
        identity = self.identity()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dispatcher.dispatch_external_runtime(
                "ptah", b"bounded body", [sys.executable, "worker.py"], root,
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
                "ptah", b"bounded body", [sys.executable, "worker.py"], root,
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
                "ptah", b"bounded body", [sys.executable, "worker.py"], root,
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

    def test_run_job_keeps_raw_stdio_out_of_receipts(self):
        body = b"\x00raw-body-marker\xff"
        stderr_bytes = b"raw-stderr-marker"
        identity = self.identity(body)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            receipt = dispatcher.dispatch_external_runtime(
                "ptah", body,
                [sys.executable, "-c", "import sys; data=sys.stdin.buffer.read(); sys.stdout.buffer.write(data); sys.stderr.buffer.write(bytes([114,97,119,45,115,116,100,101,114,114,45,109,97,114,107,101,114]))"],
                root, identity=identity, process_runner=lambda argv: 999,
            )
            _, current_path, _ = dispatcher._paths(identity, root)
            final = dispatcher.run_job(current_path)
            self.assertEqual(final["status"], "pass")
            self.assertEqual((current_path.parent / final["facts"]["stdout_artifact_ref"]).read_bytes(), body)
            self.assertEqual((current_path.parent / final["facts"]["stderr_artifact_ref"]).read_bytes(), stderr_bytes)
            self.assertEqual(final["facts"]["exit_code"], 0)
            self.assertEqual(final["receipt_ref"], f"{identity['run_handle']}:3")
            self.assertEqual(final["transition_from_ref"], receipt["receipt_ref"])
            self.assertEqual(final["facts"]["body_digest"], hashlib.sha256(body).hexdigest())
            self.assertEqual(final["facts"]["body_byte_count"], len(body))
            self.assertEqual(final["facts"]["stdout_digest"], hashlib.sha256(body).hexdigest())
            self.assertEqual(final["facts"]["stdout_byte_count"], len(body))
            self.assertEqual(final["facts"]["stderr_digest"], hashlib.sha256(stderr_bytes).hexdigest())
            self.assertEqual(final["facts"]["stderr_byte_count"], len(stderr_bytes))
            self.assertFalse(any(key.endswith("_path") for key in final["facts"]))
            serialized = json.dumps(dispatcher.load_receipt_chain(identity, root))
            self.assertNotIn("raw-body-marker", serialized)
            self.assertNotIn("raw-stderr-marker", serialized)

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
                dispatcher.dispatch_external_runtime("ptah", b"body", ["worker"], root)
            identity = self.identity(b"other")
            with self.assertRaisesRegex(ValueError, "immutable_body_digest"):
                dispatcher.dispatch_external_runtime(
                    "ptah", b"body", ["worker"], root,
                    identity=identity, process_runner=lambda argv: 1,
                )
            self.assertEqual(list(root.rglob("*")), [])


if __name__ == "__main__":
    unittest.main()
