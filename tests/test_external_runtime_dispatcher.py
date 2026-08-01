import hashlib
import importlib.util
import inspect
import json
import os
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import mock

import jsonschema

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

    def execution_transport(self, identity):
        attachment = {
            "issuer": "maat",
            "issuer_ref": "receipt:maat:42",
            "binding": {**identity, "project_root": str(REPO)},
            "provider": "packet-provider",
            "model": "packet-model",
            "toolsets": ["file", "terminal"],
            "cwd_binding": "project_root",
        }
        attachment["attachment_digest"] = dispatcher._canonical_digest(attachment)
        return attachment

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
                "hermes", "-p", "ptah", "chat", "-Q", "--pass-session-id",
                "--source", f"harness:{facts['native_correlation_id']}", "--max-turns", "8",
                "-q", body.decode(),
            ]
            self.assertEqual(facts["argv"], expected_argv)
            self.assertEqual((facts["provider"], facts["model"]), (None, None))
            self.assertEqual(facts["toolsets"], [])
            self.assertIsNone(facts["execution_transport"])
            self.assertIsNone(facts["execution_transport_digest"])
            self.assertEqual(facts["cwd"], str(REPO))
            self.assertEqual(facts["terminal_cwd"], str(REPO))
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

    def test_run_job_preserves_default_transport_for_ptah_anubis_and_maat(self):
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
            with mock.patch.dict(os.environ, {"TERMINAL_CWD": "/Users/kann/project"}), \
                 mock.patch.object(dispatcher.subprocess, "Popen", return_value=process) as popen, \
                 mock.patch.object(dispatcher, "_native_run_evidence", side_effect=native):
                final = dispatcher.run_job(current_path)
            self.assertEqual(popen.call_count, 3)
            self.assertEqual([call.args[0][2] for call in popen.call_args_list], ["ptah", "anubis", "maat"])
            for call in popen.call_args_list:
                self.assertNotIn("--provider", call.args[0])
                self.assertNotIn("-m", call.args[0])
                self.assertEqual(call.kwargs["cwd"], REPO)
                self.assertEqual(call.kwargs["env"]["TERMINAL_CWD"], str(REPO))
            self.assertEqual(final["status"], "pass")
            self.assertEqual(final["facts"]["exit_code"], 0)
            self.assertEqual(final["receipt_ref"], f"{identity['run_handle']}:3")
            self.assertEqual(final["facts"]["body_digest"], hashlib.sha256(body).hexdigest())
            self.assertEqual([run["profile"] for run in final["facts"]["native_runs"]], ["ptah", "anubis", "maat"])
            self.assertTrue(all(run["provider"] is run["model"] is None for run in final["facts"]["native_runs"]))
            self.assertTrue(all(run["correlation_id"] == final["facts"]["native_correlation_id"] for run in final["facts"]["native_runs"]))
            self.assertTrue(all(run["cwd"] == run["terminal_cwd"] == str(REPO) for run in final["facts"]["native_runs"]))

    def test_packet_local_attachment_overrides_only_owner_transport(self):
        body = b"approved override body"
        identity = self.identity(body)
        transport = self.execution_transport(identity)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dispatched = dispatcher.dispatch_external_runtime(
                "ptah", body, root, identity=identity, process_runner=lambda argv: 999,
                execution_transport=transport,
            )
            _, current_path, _ = dispatcher._paths(identity, root)
            process = mock.Mock()
            process.wait.return_value = 0

            def native(profile, body_value, correlation, exit_status):
                return {
                    "profile": profile, "correlation_id": correlation,
                    "session_ref": f"state.db:sessions:{profile}", "session_digest": "c" * 64,
                    "exit_status": exit_status, "output_digest": "d" * 64,
                    "gate_status": "pass", "tool_evidence": [],
                }

            with mock.patch.object(dispatcher.subprocess, "Popen", return_value=process) as popen, \
                 mock.patch.object(dispatcher, "_native_run_evidence", side_effect=native):
                final = dispatcher.run_job(current_path)

            expected_override = ["--provider", transport["provider"], "-m", transport["model"], "-t", "file,terminal"]
            self.assertEqual(dispatched["facts"]["provider"], transport["provider"])
            self.assertEqual(dispatched["facts"]["model"], transport["model"])
            self.assertEqual(dispatched["facts"]["toolsets"], transport["toolsets"])
            self.assertEqual(dispatched["facts"]["execution_transport"], transport)
            self.assertEqual(dispatched["facts"]["execution_transport_digest"], transport["attachment_digest"])
            self.assertEqual(dispatched["facts"]["argv"][6:12], expected_override)
            self.assertEqual(popen.call_count, 3)
            for index, call in enumerate(popen.call_args_list):
                argv = call.args[0]
                if index == 0:
                    self.assertEqual(argv[6:12], expected_override)
                else:
                    self.assertNotIn("--provider", argv)
                    self.assertNotIn("-m", argv)
                    self.assertNotIn("-t", argv)
            self.assertEqual(
                [(run["provider"], run["model"]) for run in final["facts"]["native_runs"]],
                [(transport["provider"], transport["model"]), (None, None), (None, None)],
            )
            self.assertEqual([run["toolsets"] for run in final["facts"]["native_runs"]], [transport["toolsets"], [], []])

    def test_malformed_digest_and_binding_reject_before_writes(self):
        body = b"rejected attachment body"
        identity = self.identity(body)
        valid = self.execution_transport(identity)
        candidates = {
            "malformed": {key: value for key, value in valid.items() if key != "issuer_ref"},
            "digest": dict(valid, attachment_digest="0" * 64),
            "binding": dict(valid, binding=dict(valid["binding"], owner_ref="other")),
            "duplicate_toolset": dict(valid, toolsets=["file", "file"]),
        }
        for name, contract in candidates.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                launch = mock.Mock(return_value=1)
                with self.assertRaises(ValueError):
                    dispatcher.dispatch_external_runtime(
                        "ptah", body, root, identity=identity, process_runner=launch,
                        execution_transport=contract,
                    )
                launch.assert_not_called()
                self.assertEqual(list(root.rglob("*")), [])

    def test_child_processes_normalize_inherited_terminal_cwd(self):
        for inherited in (None, "/Users/kann", "/Users/kann/projects/harness-starter"):
            with self.subTest(inherited=inherited), mock.patch.dict(os.environ, {}, clear=False):
                if inherited is None:
                    os.environ.pop("TERMINAL_CWD", None)
                else:
                    os.environ["TERMINAL_CWD"] = inherited
                process = mock.Mock(pid=1234)
                with mock.patch.object(dispatcher.subprocess, "Popen", return_value=process) as popen:
                    self.assertEqual(dispatcher._background_runner(["runner"]), 1234)
                self.assertEqual(popen.call_args.kwargs["cwd"], REPO)
                self.assertEqual(popen.call_args.kwargs["env"]["TERMINAL_CWD"], str(REPO))

    def test_provider_only_and_model_only_runtime_contracts_reject(self):
        identity = self.identity(b"body")
        transport = self.execution_transport(identity)
        facts = {
            "event": "dispatch", "argv": dispatcher._native_argv("ptah", b"body", "a" * 64, transport),
            "provider": transport["provider"], "model": transport["model"], "toolsets": transport["toolsets"],
            "cwd": str(REPO), "terminal_cwd": str(REPO), "pid": None, "exit_code": None,
            "body_artifact_ref": "body", "body_digest": "a" * 64, "body_byte_count": 4,
            "stdout_artifact_ref": "stdout", "stdout_digest": "b" * 64, "stdout_byte_count": 0,
            "stderr_artifact_ref": "stderr", "stderr_digest": "c" * 64, "stderr_byte_count": 0,
            "native_profile_ref": "ptah", "native_correlation_id": "d" * 64,
            "verification_profiles": ["anubis", "maat"], "native_runs": [],
            "execution_transport": transport, "execution_transport_digest": transport["attachment_digest"],
        }
        for missing in ("provider", "model"):
            with self.subTest(missing=missing), self.assertRaisesRegex(ValueError, "closed allowlist"):
                dispatcher._validate_runtime_facts({key: value for key, value in facts.items() if key != missing}, identity)
        for removed in (("--provider", transport["provider"]), ("-m", transport["model"])):
            malformed = dict(facts, argv=list(facts["argv"]))
            for value in removed:
                malformed["argv"].remove(value)
            with self.subTest(removed=removed), self.assertRaisesRegex(ValueError, "selected transport"):
                dispatcher._validate_runtime_facts(malformed, identity)

    def test_anubis_501_blocks_before_maat(self):
        body = b"approved native body"
        identity = self.identity(body)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dispatcher.dispatch_external_runtime("ptah", body, root, identity=identity, process_runner=lambda argv: 999)
            _, current_path, _ = dispatcher._paths(identity, root)
            exits = iter((0, 501))
            profiles = []

            def popen(argv, **kwargs):
                profiles.append(argv[2])
                process = mock.Mock()
                process.wait.return_value = next(exits)
                return process

            def native(profile, body_value, correlation, exit_status):
                return {
                    "profile": profile, "correlation_id": correlation,
                    "session_ref": f"state.db:sessions:{profile}", "session_digest": "c" * 64,
                    "exit_status": exit_status, "output_digest": "d" * 64,
                    "gate_status": "pass", "tool_evidence": [],
                }

            with mock.patch.object(dispatcher.subprocess, "Popen", side_effect=popen), \
                 mock.patch.object(dispatcher, "_native_run_evidence", side_effect=native):
                final = dispatcher.run_job(current_path)
            self.assertEqual(profiles, ["ptah", "anubis"])
            self.assertEqual(final["status"], "blocked")
            self.assertEqual(final["facts"]["exit_code"], 501)
            self.assertEqual([run["profile"] for run in final["facts"]["native_runs"]], profiles)

    def test_incomplete_consumer_evidence_blocks_before_later_stages(self):
        body = b"approved native body"
        identity = self.identity(body)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dispatcher.dispatch_external_runtime("ptah", body, root, identity=identity, process_runner=lambda argv: 999)
            _, current_path, _ = dispatcher._paths(identity, root)
            process = mock.Mock()
            process.wait.return_value = 0
            with mock.patch.object(dispatcher.subprocess, "Popen", return_value=process) as popen, \
                 mock.patch.object(dispatcher, "_native_run_evidence", return_value={}):
                final = dispatcher.run_job(current_path)
            self.assertEqual(popen.call_count, 1)
            self.assertEqual(final["status"], "blocked")
            self.assertEqual(final["facts"]["exit_code"], 0)
            self.assertEqual(final["facts"]["native_runs"], [])
            self.assertIn("native evidence incomplete", final["errors"][0])

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
        self.assertTrue({"execution_transport", "execution_transport_digest", "provider", "model", "toolsets", "argv", "cwd", "terminal_cwd"} <= set(facts["required"]))

        body = b"schema body"
        identity = self.identity(body)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            receipt = dispatcher.dispatch_external_runtime(
                "ptah", body, root, identity=identity, process_runner=lambda argv: 1234,
            )
            validator = jsonschema.Draft202012Validator(schema)
            validator.validate(receipt)
            attached = dispatcher.dispatch_external_runtime(
                "ptah", body, root / "attached", identity=identity,
                process_runner=lambda argv: 1234,
                execution_transport=self.execution_transport(identity),
            )
            validator.validate(attached)
            for missing in ("provider", "model"):
                malformed = json.loads(json.dumps(receipt))
                del malformed["facts"][missing]
                with self.subTest(missing=missing), self.assertRaises(jsonschema.ValidationError):
                    validator.validate(malformed)

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
