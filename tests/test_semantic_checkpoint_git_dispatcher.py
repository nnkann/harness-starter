import copy
import hashlib
import inspect
import json
import os
import sys
import tempfile
import threading
import unittest
import subprocess
from pathlib import Path
from unittest import mock

from jsonschema import Draft202012Validator

TOOLS = Path(__file__).resolve().parents[1] / ".harness" / "hermes" / "tools"
SCHEMAS = TOOLS.parent / "schemas"
sys.path.insert(0, str(TOOLS))

import semantic_checkpoint_git_dispatcher as dispatcher


class DispatcherTests(unittest.TestCase):
    def candidate_admission(self):
        return {
            "schema": "harness.l3-adaptation-candidate.v1",
            "candidate_ref": "C-L3.1:manual-candidate-001",
            "status": "candidate-only",
            "cohort": {
                "artifact_ref": "/tmp/c-l3-cohort.json",
                "artifact_sha256": "sha256:" + "1" * 64,
                "schema": "harness.l3-cohort-snapshot.v1",
                "enrollment_policy_revision": "sha256:" + "2" * 64,
                "cutoff": "2026-08-07T06:19:31Z",
                "membership_digest": "sha256:" + "3" * 64,
                "members": [
                    {
                        "project_id": "project-1",
                        "native_slug": "project-1",
                        "evaluation_slug": "project-1-evaluation",
                        "primary_root": "/tmp/project-1",
                        "classification": "baseline_ready",
                        "reason": "source_native_active_record",
                        "gaps": [],
                    }
                ],
            },
            "baseline": {
                "commit": "4" * 40,
                "tree": "5" * 40,
                "worktree_state": {"clean": False, "status_digest": "sha256:" + "6" * 64},
            },
            "candidate": {
                "identity": "isolated:manual-candidate-001",
                "baseline_commit": "4" * 40,
                "allowed_write_refs": ["runtime/target.py"],
                "causal_hypothesis": "A bounded target change removes the declared failure.",
                "target": {
                    "c_ref": "C-L3.target",
                    "ac_ref": "AC-runtime-1",
                    "expected_ac_effect": "Reduce the declared target failure without changing controls.",
                },
            },
            "fixed_evaluation": {
                "model": {"identity": "model:fixed-v1", "configuration_digest": "sha256:" + "7" * 64},
                "evaluator": {"identity": "evaluator:fixed-v1", "configuration_digest": "sha256:" + "8" * 64},
                "splits": {
                    "held_in_ref": "split:held-in-v1",
                    "held_in_digest": "sha256:" + "9" * 64,
                    "held_out_ref": "split:held-out-v1",
                    "held_out_digest": "sha256:" + "a" * 64,
                    "sampling_identity": "sampling:fixed-v1",
                    "secrecy_boundary": "held_out_opaque_no_content_access",
                },
            },
            "criteria": {
                "benefit": "direct_target_runtime_evidence_reduces_declared_ac_failure",
                "non_inferiority": "all_declared_preserved_ac_and_control_surfaces_remain_non_regressed",
                "regression_stop": "any_material_semantic_regression_requires_revert",
                "uncertainty_disposition": "missing_direct_evidence_or_unresolved_uncertainty_requires_owner_hold",
                "preserved_ac_refs": ["AC-control-1"],
            },
            "immutable_controls": {
                "evaluator_ref": "evaluator:fixed-v1",
                "held_out_ref": "split:held-out-v1",
                "permission_boundary_ref": "authority:permission-v1",
                "maat_disposition_ref": "authority:maat-v1",
                "sia_promotion_ref": "authority:sia-v1",
                "cohort_policy_ref": "sha256:" + "2" * 64,
                "execution_receipt_schema_ref": "contracts/execution-receipt.schema.json",
                "additional_refs": ["contracts/control-surface.v1"],
            },
            "authority": {
                "confirm": "Maat",
                "revert": "Maat",
                "owner_hold": "Maat",
                "learning_consideration": "SIA",
                "learning_automatic": False,
            },
            "observability": {
                "allowed_projections": ["candidate_ref"],
                "correlation_key": {"name": "candidate_ref", "definition": "Exact candidate correlation."},
                "retention_seconds": 86400,
                "cardinality_ceiling": 100,
                "max_dashboards": 0,
                "max_alerts": 0,
            },
        }

    def candidate_admission_sha256(self, admission):
        canonical = json.dumps(
            admission, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8") + b"\n"
        return "sha256:" + hashlib.sha256(canonical).hexdigest()

    def test_packet_local_source_native_ac_is_not_promoted_or_mapping_gated(self):
        admission = self.candidate_admission()
        source_ac_ref = admission["candidate"]["target"]["ac_ref"]
        packet = dispatcher.build_executor_local_packet(
            work_id="work-1", graph_ref="graph:work-1", local_nodes=["S1"], local_edges=[],
            source_refs=["source:native"], task_AC=[source_ac_ref], evidence_requirements=["direct evidence"],
            candidate_admission=admission,
            expected_candidate_admission_sha256=self.candidate_admission_sha256(admission),
        )

        self.assertEqual(packet["task_AC"], [source_ac_ref])
        self.assertNotIn("semantic_reference_mappings", packet)

    def build_candidate_packet(self, admission=None, expected_sha256=None):
        admission = admission or self.candidate_admission()
        return dispatcher.build_executor_local_packet(
            work_id="work-1",
            graph_ref="cps://project/work-1@r2",
            local_nodes=[{"ref": "S:git"}],
            local_edges=[{"ref": "P->S"}],
            source_refs=[
                "/tmp/maat-c-l3-1-manual-adaptation-contract.txt",
                "sha256:979a1a2e7498f8c985b2548054b259a60c14bd0add2817fffc5ba7459941a690",
            ],
            task_AC=["focused tests pass"],
            evidence_requirements=[
                "later exact pre/post/revert readback",
                "later execution_receipt refs/facts",
            ],
            candidate_admission=admission,
            expected_candidate_admission_sha256=(
                expected_sha256 or self.candidate_admission_sha256(admission)
            ),
        )

    def packet(self):
        return {
            "schema": "harness.cps.semantic-checkpoint-git-closure.v1",
            "checkpoint_id": "work-1@r2",
            "work_id": "work-1",
            "graph_source": {"ref": "graphs/work-1/current.json", "digest": "a" * 64, "expected_prior_revision": 1},
            "repository": {"root": "/tmp/repo", "branch": "feature", "upstream": "origin/feature"},
            "scoped_paths": ["graphs/work-1/current.json"],
            "excluded_dirty_paths": ["unrelated.txt"],
            "lifecycle_declaration": {
                "baseline": {"change.txt": "absent"},
                "source_mutations": ["change.txt"],
                "ephemeral_generated_paths": [],
                "persistent_evidence_paths": [],
            },
            "closure_AC_ref": "AC:closure",
            "CPS_refs": {"C": "C:work-1", "P": ["P:write"], "S": "S:git", "AC": "AC:closure", "packet": "packet:work-1@r2"},
            "prohibited_actions": ["git add -A", "stash", "main push"],
            "owner_approval": True,
            "execution_instruction": dispatcher.EXECUTION_INSTRUCTION,
            "commit_message": "Close semantic checkpoint\n\nCPS-Packet: packet:work-1@r2",
            "verification_command": None,
        }

    def test_exact_git_worker_argv(self):
        self.assertEqual(
            dispatcher.build_worker_argv(Path("/tmp/packet.json")),
            ["hermes", "chat", "--provider", "openai-codex", "-m", "gpt-5.3-codex-spark", "-t", "terminal,file", "-Q", "-q", "@/tmp/packet.json"],
        )

    def test_dispatch_without_cps_refs_or_closure_ac_is_owner_approved(self):
        packet = self.packet()
        packet.pop("CPS_refs")
        packet.pop("closure_AC_ref")
        packet["commit_message"] = "Close semantic checkpoint"
        launches = []
        with tempfile.TemporaryDirectory() as tmp:
            receipt = dispatcher.dispatch_checkpoint(packet, Path(tmp), process_runner=lambda argv: launches.append(argv) or 4321)
        self.assertEqual(receipt["status"], "git_pending")
        self.assertEqual(len(launches), 1)

    def test_dispatch_rejects_partial_cps_binding_without_launch(self):
        for omitted in ("CPS_refs", "closure_AC_ref"):
            with self.subTest(omitted=omitted), tempfile.TemporaryDirectory() as tmp:
                packet = self.packet()
                del packet[omitted]
                launches = []
                receipt = dispatcher.dispatch_checkpoint(packet, Path(tmp), process_runner=launches.append)
                self.assertEqual(receipt["status"], "rejected_dispatch")
                self.assertIn("CPS_binding:partial", receipt["errors"])
                self.assertFalse(launches)

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
        for path in ("schema", "graph_source", "repository", "prohibited_actions"):
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
        self.assertEqual(receipt["provider"], "openai-codex")
        self.assertEqual(receipt["model"], "gpt-5.3-codex-spark")
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

    def _seed_repo(self, root, *, ignored_pattern=None):
        repo = self._repo_with_remote(root)
        (repo / "README.md").write_text("baseline\n")
        if ignored_pattern:
            (repo / ".gitignore").write_text(f"{ignored_pattern}\n")
        self._git(repo, "add", ".")
        self._git(repo, "commit", "-m", "baseline")
        self._git(repo, "push", "-u", "origin", "feature")
        return repo

    def _closure_packet(self, repo, *, ephemeral=(), persistent=()):
        packet = self.packet()
        packet["repository"]["root"] = str(repo)
        packet["lifecycle_declaration"] = {
            "baseline": {
                **{"change.txt": "absent"},
                **{path: "absent" for path in ephemeral},
                **{path: "absent" for path in persistent},
            },
            "source_mutations": ["change.txt"],
            "ephemeral_generated_paths": list(ephemeral),
            "persistent_evidence_paths": list(persistent),
        }
        return packet

    def _commit_push_worker(self, repo, packet, *, remove=(), persistent=()):
        def worker(argv, stdout_path, stderr_path):
            for path in remove:
                (repo / path).unlink()
            (repo / "change.txt").write_text("done\n")
            for path in persistent:
                self._git(repo, "add", path)
            self._git(repo, "add", "change.txt")
            self._git(repo, "commit", "-m", packet["commit_message"])
            self._git(repo, "push", "origin", "feature")
            return 0
        return worker

    def test_declared_ephemeral_is_removed_and_read_back_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = self._seed_repo(root)
            (repo / "generated.tmp").write_text("temporary\n")
            packet = self._closure_packet(repo, ephemeral=["generated.tmp"])
            receipt = dispatcher.dispatch_checkpoint(packet, root / "records", process_runner=lambda argv: 7)
            final = dispatcher.run_job(Path(receipt["job_path"]), worker_runner=self._commit_push_worker(repo, packet, remove=["generated.tmp"]))
            self.assertEqual(final["status"], "git_pushed")
            self.assertFalse((repo / "generated.tmp").exists())
            self.assertEqual(final["cleanup_observations"]["ephemeral"][0]["kind"], "absent")

    def test_ignored_declared_ephemeral_is_removed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = self._seed_repo(root, ignored_pattern="*.cache")
            (repo / "generated.cache").write_text("temporary\n")
            packet = self._closure_packet(repo, ephemeral=["generated.cache"])
            receipt = dispatcher.dispatch_checkpoint(packet, root / "records", process_runner=lambda argv: 7)
            final = dispatcher.run_job(Path(receipt["job_path"]), worker_runner=self._commit_push_worker(repo, packet, remove=["generated.cache"]))
            self.assertEqual(final["status"], "git_pushed")
            observation = final["cleanup_observations"]["ephemeral"][0]
            self.assertFalse(observation["exists"])
            self.assertTrue(observation["ignored"])

    def test_persistent_evidence_is_retained(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = self._seed_repo(root)
            (repo / "evidence.json").write_text("{}\n")
            packet = self._closure_packet(repo, persistent=["evidence.json"])
            receipt = dispatcher.dispatch_checkpoint(packet, root / "records", process_runner=lambda argv: 7)
            final = dispatcher.run_job(Path(receipt["job_path"]), worker_runner=self._commit_push_worker(repo, packet, persistent=["evidence.json"]))
            self.assertEqual(final["status"], "git_pushed")
            self.assertTrue((repo / "evidence.json").is_file())
            self.assertTrue(final["cleanup_observations"]["persistent"][0]["exists"])

    def test_preexisting_path_is_preserved_instead_of_cleaned(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = self._seed_repo(root)
            (repo / "README.md").write_text("pre-existing change\n")
            packet = self._closure_packet(repo)
            packet["lifecycle_declaration"] = {
                "baseline": {"README.md": "present"},
                "source_mutations": [],
                "ephemeral_generated_paths": ["README.md"],
                "persistent_evidence_paths": [],
            }
            receipt = dispatcher.dispatch_checkpoint(packet, root / "records", process_runner=lambda argv: self.fail("must not launch"))
            self.assertEqual(receipt["status"], "git_failed")
            self.assertEqual((repo / "README.md").read_text(), "pre-existing change\n")

    def test_symlink_ambiguity_holds_without_cleanup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = self._seed_repo(root)
            (repo / "target.tmp").write_text("keep\n")
            (repo / "ambiguous.tmp").symlink_to("target.tmp")
            packet = self._closure_packet(repo, ephemeral=["ambiguous.tmp"])
            receipt = dispatcher.dispatch_checkpoint(packet, root / "records", process_runner=lambda argv: self.fail("must not launch"))
            self.assertEqual(receipt["status"], "git_failed")
            self.assertTrue((repo / "ambiguous.tmp").is_symlink())
            self.assertTrue(any("path_ambiguous" in error for error in receipt["errors"]))

    def test_directory_cleanup_target_is_blocked_and_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = self._seed_repo(root)
            (repo / "generated-dir").mkdir()
            (repo / "generated-dir" / "keep.txt").write_text("keep\n")
            packet = self._closure_packet(repo, ephemeral=["generated-dir"])
            receipt = dispatcher.dispatch_checkpoint(packet, root / "records", process_runner=lambda argv: self.fail("must not launch"))
            self.assertEqual(receipt["status"], "git_failed")
            self.assertTrue((repo / "generated-dir" / "keep.txt").is_file())

    def test_nonexact_duplicate_and_cross_class_paths_are_blocked(self):
        invalid_declarations = [
            ({"/absolute": "absent"}, ["/absolute"], [], []),
            ({"a/../escape": "absent"}, ["a/../escape"], [], []),
            ({"*.tmp": "absent"}, ["*.tmp"], [], []),
            ({"e\u0301.txt": "absent"}, ["e\u0301.txt"], [], []),
            ({"duplicate": "absent"}, ["duplicate", "duplicate"], [], []),
            ({"shared": "absent"}, ["shared"], [], ["shared"]),
        ]
        for baseline, source, ephemeral, persistent in invalid_declarations:
            with self.subTest(source=source, persistent=persistent), tempfile.TemporaryDirectory() as tmp:
                packet = self.packet()
                packet["repository"]["root"] = tmp
                packet["lifecycle_declaration"] = {
                    "baseline": baseline,
                    "source_mutations": source,
                    "ephemeral_generated_paths": ephemeral,
                    "persistent_evidence_paths": persistent,
                }
                receipt = dispatcher.dispatch_checkpoint(packet, Path(tmp) / "records", process_runner=lambda argv: self.fail("must not launch"))
                self.assertEqual(receipt["status"], "git_failed")

    def test_unrelated_ignored_and_untracked_paths_are_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = self._seed_repo(root, ignored_pattern="unrelated.cache")
            (repo / "generated.tmp").write_text("temporary\n")
            (repo / "unrelated.cache").write_text("ignored\n")
            (repo / "unrelated.txt").write_text("untracked\n")
            packet = self._closure_packet(repo, ephemeral=["generated.tmp"])
            receipt = dispatcher.dispatch_checkpoint(packet, root / "records", process_runner=lambda argv: 7)
            final = dispatcher.run_job(Path(receipt["job_path"]), worker_runner=self._commit_push_worker(repo, packet, remove=["generated.tmp"]))
            self.assertEqual(final["status"], "git_pushed")
            self.assertTrue((repo / "unrelated.cache").is_file())
            self.assertTrue((repo / "unrelated.txt").is_file())

    def test_cleanup_readback_failure_prevents_git_pushed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = self._seed_repo(root)
            (repo / "generated.tmp").write_text("temporary\n")
            packet = self._closure_packet(repo, ephemeral=["generated.tmp"])
            receipt = dispatcher.dispatch_checkpoint(packet, root / "records", process_runner=lambda argv: 7)
            worker = self._commit_push_worker(repo, packet, remove=["generated.tmp"])
            with mock.patch.object(dispatcher, "_path_readback", side_effect=RuntimeError("readback failed")):
                final = dispatcher.run_job(Path(receipt["job_path"]), worker_runner=worker)
            self.assertEqual(final["status"], "git_failed")
            self.assertTrue(any("readback failed" in error for error in final["errors"]))

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
        admission = self.candidate_admission()
        identity = self.candidate_admission_sha256(admission)
        packet = self.build_candidate_packet(admission, identity)
        self.assertEqual(packet["family"], "executor_local_packet")
        self.assertNotIn("commands", packet)
        self.assertEqual(packet["local_nodes"], [{"ref": "S:git"}])
        self.assertEqual(packet["allowed_write_refs"], ["runtime/target.py"])
        self.assertEqual(
            packet["source_refs"],
            [
                "/tmp/maat-c-l3-1-manual-adaptation-contract.txt",
                "sha256:979a1a2e7498f8c985b2548054b259a60c14bd0add2817fffc5ba7459941a690",
                admission["candidate_ref"],
                identity,
            ],
        )
        self.assertEqual(
            packet["evidence_requirements"],
            ["later exact pre/post/revert readback", "later execution_receipt refs/facts"],
        )
        self.assertTrue(packet["must_preserve"])
        self.assertTrue(packet["forbidden_effects"])
        self.assertNotIn("evidence_required", packet)
        self.assertIn(f"baseline.commit={admission['baseline']['commit']}", packet["must_preserve"])
        self.assertIn("authority.confirm=Maat", packet["must_preserve"])
        self.assertIn(
            "forbid:read:held_out:split:held-out-v1", packet["forbidden_effects"]
        )
        for prohibited in ("receipt", "status", "baseline", "revert", "result", "verdict", "PASS", "closure", "promotion"):
            self.assertNotIn(prohibited, packet)
        receipt = dispatcher.build_git_worker_receipt(packet, "git_failed", errors=[str(i) for i in range(50)])
        self.assertEqual(len(receipt["errors"]), dispatcher.MAX_RECEIPT_ERRORS)

    def test_candidate_local_identity_shape_and_authority_fail_closed(self):
        admission = self.candidate_admission()
        with self.assertRaisesRegex(ValueError, "identity mismatch"):
            self.build_candidate_packet(admission, "sha256:" + "0" * 64)

        mutations = [
            (("schema",), "harness.l3-adaptation-candidate.v2"),
            (("status",), "PASS"),
            (("criteria", "benefit"), "weaker"),
            (("authority", "confirm"), "Ptah"),
        ]
        for path, value in mutations:
            with self.subTest(path=path):
                changed = copy.deepcopy(admission)
                target = changed
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = value
                with self.assertRaises(ValueError):
                    self.build_candidate_packet(changed)

        for path in ((), ("baseline",), ("fixed_evaluation", "splits"), ("immutable_controls",)):
            with self.subTest(unknown_at=path):
                changed = copy.deepcopy(admission)
                target = changed
                for key in path:
                    target = target[key]
                target["unknown"] = True
                with self.assertRaisesRegex(ValueError, "fields"):
                    self.build_candidate_packet(changed)

    def test_candidate_local_allowed_write_ref_denial_matrix(self):
        denied = [
            [],
            ["runtime/target.py", "runtime/target.py"],
            ["runtime", "runtime/target.py"],
            ["/runtime/target.py"],
            ["runtime\\target.py"],
            ["runtime/./target.py"],
            ["runtime/../target.py"],
            ["runtime//target.py"],
            ["runtime/*.py"],
            ["runtime/e\u0301.py"],
            [1],
        ]
        for refs in denied:
            with self.subTest(refs=refs):
                admission = self.candidate_admission()
                admission["candidate"]["allowed_write_refs"] = refs
                with self.assertRaises(ValueError):
                    self.build_candidate_packet(admission)

    def test_candidate_local_rejects_malformed_cohort_member_and_observability(self):
        mutations = [
            (("cohort", "members"), [{"project_id": "project-1"}]),
            (("cohort", "members", 0, "classification"), "HOLD_GAP"),
            (("cohort", "members", 0, "gaps"), ["gap", "gap"]),
            (("cohort", "members", 0, "unknown"), "value"),
            (("cohort", "artifact_sha256"), "not-a-digest"),
            (("cohort", "enrollment_policy_revision"), "not-a-digest"),
            (("cohort", "membership_digest"), "not-a-digest"),
            (("cohort", "cutoff"), "not-a-cutoff"),
            (("observability", "allowed_projections"), []),
            (("observability", "allowed_projections"), ["candidate_ref", "candidate_ref"]),
            (("observability", "allowed_projections"), ["Invalid-Projection"]),
            (("observability", "correlation_key"), "candidate_ref"),
            (("observability", "correlation_key"), {"name": "candidate_ref"}),
            (("observability", "correlation_key", "name"), "other_ref"),
            (("observability", "correlation_key", "definition"), "short"),
            (("observability", "correlation_key", "unknown"), "value"),
            (("observability", "retention_seconds"), 0),
            (("observability", "retention_seconds"), True),
            (("observability", "cardinality_ceiling"), "unbounded"),
            (("observability", "max_dashboards"), -1),
            (("observability", "max_alerts"), False),
        ]
        for path, value in mutations:
            with self.subTest(path=path, value=value):
                admission = self.candidate_admission()
                target = admission
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = value
                with self.assertRaises(ValueError):
                    self.build_candidate_packet(admission)

    def test_candidate_local_rejects_control_namespace_write_refs_in_compiler_and_schema(self):
        schema = json.loads((SCHEMAS / "executor-local-packet.schema.yaml").read_text())
        validator = Draft202012Validator(schema)
        denied = [
            "evaluator:fixed-v1",
            "split:held-out-v1",
            "authority:permission-v1",
            "authority:maat-v1",
            "authority:sia-v1",
            "sha256:" + "2" * 64,
        ]
        for ref in denied:
            with self.subTest(ref=ref):
                admission = self.candidate_admission()
                admission["candidate"]["allowed_write_refs"] = [ref]
                with self.assertRaises(ValueError):
                    self.build_candidate_packet(admission)

                packet = self.build_candidate_packet()
                packet["allowed_write_refs"] = [ref]
                self.assertTrue(list(validator.iter_errors(packet)))

    def test_candidate_local_rejects_equal_ancestor_and_descendant_controls(self):
        for mutable, control in (
            ("contracts/control-surface.v1", "contracts/control-surface.v1"),
            ("contracts", "contracts/control-surface.v1"),
            ("contracts/control-surface.v1/child", "contracts/control-surface.v1"),
            ("contracts", "contracts/execution-receipt.schema.json"),
        ):
            with self.subTest(mutable=mutable, control=control):
                admission = self.candidate_admission()
                admission["candidate"]["allowed_write_refs"] = [mutable]
                admission["immutable_controls"]["additional_refs"] = [control]
                with self.assertRaisesRegex(ValueError, "overlaps"):
                    self.build_candidate_packet(admission)

    def test_candidate_local_schema_meta_validation_and_compiler_parity(self):
        schema = json.loads((SCHEMAS / "executor-local-packet.schema.yaml").read_text())
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
        packet = self.build_candidate_packet()
        validator.validate(packet)

        for field in ("allowed_write_refs", "must_preserve", "forbidden_effects"):
            with self.subTest(missing=field):
                changed = copy.deepcopy(packet)
                del changed[field]
                self.assertTrue(list(validator.iter_errors(changed)))
            for invalid in ([], ["duplicate", "duplicate"], [""]):
                with self.subTest(field=field, invalid=invalid):
                    changed = copy.deepcopy(packet)
                    changed[field] = invalid
                    self.assertTrue(list(validator.iter_errors(changed)))
        changed = copy.deepcopy(packet)
        changed["unknown"] = {"recursive": True}
        self.assertTrue(list(validator.iter_errors(changed)))
        changed = copy.deepcopy(packet)
        changed["commands"] = ["execute"]
        self.assertTrue(list(validator.iter_errors(changed)))

    def test_candidate_local_builder_path_has_no_side_effect_access(self):
        source = "\n".join(
            inspect.getsource(function)
            for function in (
                dispatcher._exact_candidate_mapping,
                dispatcher._candidate_text,
                dispatcher._candidate_texts,
                dispatcher._candidate_identity,
                dispatcher._candidate_path_parts,
                dispatcher._path_parts_overlap,
                dispatcher._path_like_preserved_ref,
                dispatcher._candidate_boundary_projection,
                dispatcher.build_executor_local_packet,
                dispatcher._valid_repo_relative_path,
            )
        )
        for prohibited in (
            "open(", "read_text(", "read_bytes(", "write_text(", "write_bytes(",
            "subprocess", "os.", "environ", "socket", "urllib", "requests", "_git(", "dispatch_",
        ):
            self.assertNotIn(prohibited, source)

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
        self.assertEqual(set(checkpoint_schema["required"]), dispatcher.TOP_KEYS - {"closure_AC_ref", "CPS_refs"})
        self.assertFalse(checkpoint_schema["additionalProperties"])
        self.assertEqual(checkpoint_schema["properties"]["schema"]["const"], dispatcher.SCHEMA)
        self.assertEqual(set(executor_schema["required"]), {"family", "work_id", "graph_ref", "local_nodes", "local_edges", "source_refs", "task_AC", "evidence_requirements", "allowed_write_refs", "must_preserve", "forbidden_effects"})
        self.assertFalse(executor_schema["additionalProperties"])
        self.assertNotIn("commands", executor_schema["properties"])


if __name__ == "__main__":
    unittest.main()
