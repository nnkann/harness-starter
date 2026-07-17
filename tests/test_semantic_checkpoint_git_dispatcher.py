import copy
import json
import os
import sys
import tempfile
import threading
import unittest
import subprocess
from pathlib import Path
from unittest import mock

TOOLS = Path(__file__).resolve().parents[1] / ".harness" / "hermes" / "tools"
SCHEMAS = TOOLS.parent / "schemas"
sys.path.insert(0, str(TOOLS))

import semantic_checkpoint_git_dispatcher as dispatcher


class DispatcherTests(unittest.TestCase):
    def packet(self):
        return {
            "schema": "harness.cps.semantic-checkpoint-git-closure.v1",
            "checkpoint_id": "work-1@r2",
            "work_id": "work-1",
            "graph_source": {"ref": "graphs/work-1/current.json", "digest": "a" * 64, "expected_prior_revision": 1},
            "repository": {"root": "/tmp/repo", "branch": "feature", "upstream": "origin/feature"},
            "scoped_paths": ["graphs/work-1/current.json"],
            "excluded_dirty_paths": ["unrelated.txt"],
            "closure_AC_ref": "AC:closure",
            "CPS_refs": {"C": "C:work-1", "P": ["P:write"], "S": "S:git", "AC": "AC:closure", "packet": "packet:work-1@r2"},
            "prohibited_actions": ["git add -A", "stash", "main push"],
            "owner_approval": True,
            "execution_instruction": "Perform only the scoped Git closure described by this packet: run verification_command if present; stage only scoped_paths; create the exact commit_message; push only repository.branch to repository.upstream; then report facts.",
            "commit_message": "Close semantic checkpoint\n\nCPS-Packet: packet:work-1@r2",
            "verification_command": None,
        }

    def test_exact_git_worker_argv(self):
        self.assertEqual(
            dispatcher.build_worker_argv(Path("/tmp/packet.json")),
            ["agy", "--model", "Gemini 3.5 Flash (High)", "--dangerously-skip-permissions", "--print", "Read and execute only the Git closure packet at /tmp/packet.json."],
        )

    def test_dispatch_validates_nested_packet_and_exact_key_is_idempotent(self):
        launches = []
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = dispatcher.dispatch_checkpoint(self.packet(), root, process_runner=lambda argv: launches.append(argv) or 4321)
            second = dispatcher.dispatch_checkpoint(self.packet(), root, process_runner=lambda argv: launches.append(argv) or 9999)
            self.assertEqual(first, second)
            self.assertEqual(first["status"], "git_pending")
            self.assertEqual(first["checkpoint_id"], "work-1@r2")
            self.assertEqual(len(launches), 1)

    def test_same_checkpoint_with_changed_digest_or_upstream_rejects_without_launch(self):
        for field in ("digest", "upstream"):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                launches = []
                original = self.packet()
                dispatcher.dispatch_checkpoint(original, Path(tmp), process_runner=lambda argv: launches.append(argv) or 1)
                conflict = copy.deepcopy(original)
                if field == "digest":
                    conflict["graph_source"]["digest"] = "b" * 64
                else:
                    conflict["repository"]["upstream"] = "fork/feature"
                receipt = dispatcher.dispatch_checkpoint(conflict, Path(tmp), process_runner=lambda argv: launches.append(argv) or 2)
                self.assertEqual(receipt["status"], "rejected_dispatch")
                self.assertEqual(len(launches), 1)

    def test_rejects_nested_contract_negative_cases_without_launch(self):
        invalid_packets = []
        for path in ("schema", "graph_source", "repository", "CPS_refs", "prohibited_actions"):
            packet = self.packet()
            del packet[path]
            invalid_packets.append(packet)
        packet = self.packet()
        del packet["graph_source"]["digest"]
        invalid_packets.append(packet)
        packet = self.packet()
        packet["checkpoint_id"] = "unrelated-id"
        invalid_packets.append(packet)
        for packet in invalid_packets:
            with self.subTest(packet=packet), tempfile.TemporaryDirectory() as tmp:
                launches = []
                receipt = dispatcher.dispatch_checkpoint(packet, Path(tmp), process_runner=launches.append)
                self.assertEqual(receipt["status"], "rejected_dispatch")
                self.assertFalse(launches)

    def test_rejects_missing_or_invalid_authoritative_launch_fields(self):
        invalid_packets = []
        for key in ("owner_approval", "execution_instruction", "commit_message", "verification_command"):
            packet = self.packet()
            del packet[key]
            invalid_packets.append(packet)
        for key, value in (("owner_approval", False), ("execution_instruction", ""), ("commit_message", ""), ("verification_command", 1)):
            packet = self.packet()
            packet[key] = value
            invalid_packets.append(packet)
        for packet in invalid_packets:
            with self.subTest(packet=packet), tempfile.TemporaryDirectory() as tmp:
                launches = []
                receipt = dispatcher.dispatch_checkpoint(packet, Path(tmp), process_runner=launches.append)
                self.assertEqual(receipt["status"], "rejected_dispatch")
                self.assertFalse(launches)

    def test_pending_record_contains_process_and_log_lifecycle_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            receipt = dispatcher.dispatch_checkpoint(self.packet(), root, process_runner=lambda argv: 4321)
            persisted = dispatcher.poll_checkpoint("work-1@r2", root)
        self.assertEqual(receipt, persisted)
        self.assertEqual(receipt["pid"], 4321)
        self.assertEqual(receipt["provider"], "agy-router")
        self.assertEqual(receipt["model"], "Gemini 3.5 Flash (High)")
        self.assertTrue(receipt["stdout_log_path"].endswith(".stdout.log"))
        self.assertTrue(receipt["stderr_log_path"].endswith(".stderr.log"))

    def _git(self, repo, *args):
        return subprocess.run(["git", *args], cwd=repo, check=True, text=True, capture_output=True).stdout.strip()

    def _repo_with_remote(self, root):
        remote = root / "remote.git"
        repo = root / "repo"
        self._git(root, "init", "--bare", str(remote))
        self._git(root, "init", "-b", "feature", str(repo))
        self._git(repo, "config", "user.name", "Test")
        self._git(repo, "config", "user.email", "test@example.invalid")
        self._git(repo, "remote", "add", "origin", str(remote))
        return repo

    def test_runner_transitions_success_to_git_pushed_after_independent_postcheck(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = self._repo_with_remote(root)
            packet = self.packet()
            packet["repository"]["root"] = str(repo)
            receipt = dispatcher.dispatch_checkpoint(packet, root / "records", process_runner=lambda argv: 7)

            def fake_worker(argv, stdout_path, stderr_path):
                self.assertEqual(argv, dispatcher.build_worker_argv(Path(receipt["packet_path"]).resolve()))
                (repo / "change.txt").write_text("done\n")
                self._git(repo, "add", "change.txt")
                self._git(repo, "commit", "-m", packet["commit_message"])
                self._git(repo, "push", "-u", "origin", "feature")
                stdout_path.write_text("worker ok\n")
                stderr_path.write_text("")
                return 0

            final = dispatcher.run_job(Path(receipt["job_path"]), worker_runner=fake_worker)
            polled = dispatcher.poll_checkpoint(packet["checkpoint_id"], root / "records")
        self.assertEqual(final, polled)
        self.assertEqual(final["status"], "git_pushed")
        self.assertEqual(final["head_sha"], final["upstream_sha"])
        self.assertEqual(final["worker_exit_code"], 0)

    def test_runner_records_failed_worker_without_git_postcheck(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            receipt = dispatcher.dispatch_checkpoint(self.packet(), root, process_runner=lambda argv: 7)
            final = dispatcher.run_job(Path(receipt["job_path"]), worker_runner=lambda argv, out, err: 9)
        self.assertEqual(final["status"], "git_failed")
        self.assertEqual(final["worker_exit_code"], 9)

    def test_runner_rejects_remote_mismatch_after_successful_worker(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = self._repo_with_remote(root)
            packet = self.packet()
            packet["repository"]["root"] = str(repo)
            receipt = dispatcher.dispatch_checkpoint(packet, root / "records", process_runner=lambda argv: 7)

            def commit_without_push(argv, stdout_path, stderr_path):
                (repo / "change.txt").write_text("done\n")
                self._git(repo, "add", "change.txt")
                self._git(repo, "commit", "-m", packet["commit_message"])
                return 0

            final = dispatcher.run_job(Path(receipt["job_path"]), worker_runner=commit_without_push)
        self.assertEqual(final["status"], "git_failed")
        self.assertTrue(any("upstream" in error for error in final["errors"]))

    def _write_pending(self, packet, record_root, *, pid):
        receipt = dispatcher.dispatch_checkpoint(packet, record_root, process_runner=lambda argv: pid)
        return Path(receipt["job_path"]), receipt

    def test_dead_pending_successful_reconciliation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            job_path, _ = self._write_pending(self.packet(), root, pid=99999999)
            with mock.patch.object(dispatcher, "_postcheck", return_value=({"head_sha": "a" * 40, "upstream_sha": "a" * 40}, [])):
                final = dispatcher.reconcile_checkpoint("work-1@r2", root)
            self.assertEqual(final["status"], "git_pushed")
            self.assertTrue(final["reconciliation"]["dead_pid_postcheck"])
            self.assertEqual(json.loads(job_path.read_text()), final)

    def test_dead_pending_failed_reconciliation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_pending(self.packet(), root, pid=99999999)
            with mock.patch.object(dispatcher, "_postcheck", return_value=({}, ["postcheck:upstream_sha_mismatch"])):
                final = dispatcher.reconcile_checkpoint("work-1@r2", root)
            self.assertEqual(final["status"], "git_failed")
            self.assertIn("postcheck:upstream_sha_mismatch", final["errors"])

    def test_alive_pending_is_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, pending = self._write_pending(self.packet(), root, pid=os.getpid())
            with mock.patch.object(dispatcher, "_postcheck") as postcheck:
                reconciled = dispatcher.reconcile_checkpoint("work-1@r2", root)
            self.assertEqual(reconciled, pending)
            postcheck.assert_not_called()

    def test_run_job_exception_transitions_to_git_failed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            job_path, _ = self._write_pending(self.packet(), root, pid=7)
            with mock.patch.object(dispatcher, "_postcheck", side_effect=RuntimeError("postcheck exploded")):
                final = dispatcher.run_job(job_path, worker_runner=lambda argv, out, err: 0)
            self.assertEqual(final["status"], "git_failed")
            self.assertTrue(any("postcheck exploded" in error for error in final["errors"]))
            self.assertEqual(json.loads(job_path.read_text()), final)

    def test_dispatch_race_preserves_terminal_child_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            child_done = threading.Event()

            def launch(argv):
                job_path = Path(argv[-1])

                def child():
                    dispatcher.run_job(job_path, worker_runner=lambda worker_argv, out, err: 9)
                    child_done.set()

                thread = threading.Thread(target=child)
                thread.start()
                self.assertTrue(child_done.wait(2))
                thread.join()
                return 4321

            receipt = dispatcher.dispatch_checkpoint(self.packet(), root, process_runner=launch)
            self.assertEqual(receipt["status"], "git_failed")
            self.assertEqual(dispatcher.poll_checkpoint("work-1@r2", root)["status"], "git_failed")

    def test_executor_local_packet_is_selected_ref_projection(self):
        packet = dispatcher.build_executor_local_packet(
            work_id="work-1", graph_ref="cps://project/work-1@r2",
            local_nodes=[{"ref": "S:git"}], local_edges=[{"ref": "P->S"}],
            source_refs=["contract:dispatcher"], task_AC=["focused tests pass"],
            evidence_requirements=["command and exit code"],
        )
        self.assertEqual(packet["family"], "executor_local_packet")
        self.assertNotIn("commands", packet)
        self.assertEqual(packet["local_nodes"], [{"ref": "S:git"}])
        receipt = dispatcher.build_git_worker_receipt(packet, "git_failed", errors=[str(i) for i in range(50)])
        self.assertEqual(len(receipt["errors"]), dispatcher.MAX_RECEIPT_ERRORS)

    def test_git_worker_receipt_has_only_dispatcher_terminal_statuses(self):
        packet = self.packet()
        receipt_schema = json.loads((SCHEMAS / "git-worker-receipt.schema.yaml").read_text())
        self.assertFalse(receipt_schema["additionalProperties"])
        self.assertIn("checkpoint_id", receipt_schema["properties"])
        self.assertEqual(set(receipt_schema["properties"]["status"]["enum"]), dispatcher.GIT_WORKER_STATUSES)
        for status in dispatcher.GIT_WORKER_STATUSES:
            self.assertEqual(dispatcher.build_git_worker_receipt(packet, status)["status"], status)
        with self.assertRaises(ValueError):
            dispatcher.build_git_worker_receipt(packet, "pass")
        for key in ("verdict", "C", "P", "S", "AC", "task_AC", "closure"):
            self.assertNotIn(key, receipt_schema["properties"])
            with self.subTest(key=key), self.assertRaises(ValueError):
                dispatcher.build_git_worker_receipt(packet, "git_pending", **{key: "semantic"})

    def test_generic_runtime_receipt_records_nonsemantic_facts_without_git_status(self):
        packet = {"work_id": "work-1", "checkpoint_id": "work-1@r2"}
        receipt_schema = json.loads((SCHEMAS / "execution-receipt.schema.yaml").read_text())
        execution_def = receipt_schema["$defs"]["execution_receipt"]
        self.assertEqual(set(execution_def["properties"]["status"]["enum"]), dispatcher.RUNTIME_RECEIPT_STATUSES)
        receipt = dispatcher.build_runtime_receipt(packet, "observed", facts={"readback": "present"})
        self.assertEqual(receipt["family"], "execution_receipt")
        self.assertEqual(receipt["status"], "observed")
        self.assertEqual(receipt["facts"]["readback"], "present")
        for status in dispatcher.GIT_WORKER_STATUSES:
            with self.subTest(status=status), self.assertRaises(ValueError):
                dispatcher.build_runtime_receipt(packet, status)
        for key in ("verdict", "C", "P", "S", "AC", "task_AC", "closure"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                dispatcher.build_runtime_receipt(packet, "observed", facts={"nested": [{key: "semantic"}]})

    def test_schema_documents_preserve_checkpoint_and_projection_contracts(self):
        checkpoint_schema = json.loads((SCHEMAS / "semantic-checkpoint-git-closure.schema.yaml").read_text())
        executor_schema = json.loads((SCHEMAS / "executor-local-packet.schema.yaml").read_text())
        self.assertEqual(set(checkpoint_schema["required"]), dispatcher.TOP_KEYS)
        self.assertFalse(checkpoint_schema["additionalProperties"])
        self.assertEqual(checkpoint_schema["properties"]["schema"]["const"], dispatcher.SCHEMA)
        self.assertEqual(set(executor_schema["required"]), {"family", "work_id", "graph_ref", "local_nodes", "local_edges", "source_refs", "task_AC", "evidence_requirements"})
        self.assertFalse(executor_schema["additionalProperties"])
        self.assertNotIn("commands", executor_schema["properties"])


if __name__ == "__main__":
    unittest.main()
