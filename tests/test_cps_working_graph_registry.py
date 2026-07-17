import json
import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[1] / ".harness" / "hermes" / "tools"
SCHEMAS = TOOLS.parent / "schemas"
sys.path.insert(0, str(TOOLS))

import cps_working_graph_registry as registry


class WorkingGraphRegistryTests(unittest.TestCase):
    def provenance(self, root: Path):
        del root
        repo = TOOLS.parents[2]
        source = repo.parent / "harness-brain" / "projects" / repo.name / "decisions" / "cps-memory-lifecycle-and-honcho-anchor.md"
        line_count = len(source.read_text(encoding="utf-8").splitlines())
        return {
            "canonical_source_locator": str(source),
            "canonical_source_readback": f"{source}:1-{line_count}",
            "current_source_revision": subprocess.check_output(["git", "-C", str(source.parent), "rev-parse", "HEAD"], text=True).strip(),
            "current_content_hash": hashlib.sha256(source.read_bytes()).hexdigest(),
            "canonical_section": f"{source}:75-108",
            "semantic_field_definition_coverage": {"schema": f"{source}:78", "C.shape": f"{source}:85"},
        }

    def create(self, store, work_id, body, **kwargs):
        return store.create(work_id, body, semantic_provenance_binding=self.provenance(store.root), **kwargs)

    def test_materialization_persists_exact_provenance_binding_with_body_before_any_checkpoint(self):
        calls = []
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            body = {"schema": "x", "C": {"shape": "bounded"}}
            provenance = self.provenance(root)
            result = registry.materialize_maat_body(
                body,
                {"work_id": "work-1", "graph_root": root},
                semantic_provenance_binding=provenance,
                checkpoint_settings=self.checkpoint_args(root / "work-1.yaml"),
                dispatcher=lambda packet: calls.append(packet) or {"status": "pending"},
            )
            graph = registry.load_json_or_yaml(Path(result["graph_ref"]))
            self.assertTrue(store := registry.WorkingGraphRegistry(root))
            self.assertTrue(store.verify_readback("work-1", body, provenance))
            changed = registry.load_json_or_yaml(Path(result["graph_ref"]))
            changed["semantic_provenance_binding"]["current_source_revision"] = "changed"
            Path(result["graph_ref"]).write_text(json.dumps(changed), encoding="utf-8")
            self.assertFalse(store.verify_readback("work-1", body, provenance))
        self.assertEqual(graph["semantic_provenance_binding"], provenance)
        self.assertEqual(calls[0]["work_id"], "work-1")

    def test_invalid_provenance_fails_before_graph_or_checkpoint_write(self):
        calls = []
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            provenance = self.provenance(root)
            provenance["semantic_field_definition_coverage"] = {"schema": "prior Maat output"}
            with self.assertRaisesRegex(registry.RegistryError, "HOLD_UNMAPPED_SEMANTIC_FIELD"):
                registry.materialize_maat_body(
                    {"schema": "x", "C": {"shape": "bounded"}},
                    {"work_id": "work-1", "graph_root": root},
                    semantic_provenance_binding=provenance,
                    checkpoint_settings=self.checkpoint_args(root / "work-1.yaml"),
                    dispatcher=lambda packet: calls.append(packet),
                )
            self.assertFalse((root / "work-1.yaml").exists())
            self.assertEqual(calls, [])
            for operation in (
                lambda: registry.WorkingGraphRegistry(root).create("missing", {"schema": "x"}),
                lambda: registry.WorkingGraphRegistry(root).apply_maat_delta("work-1", {"schema": "x"}),
            ):
                with self.assertRaisesRegex(registry.RegistryError, "HOLD_UNMAPPED_SEMANTIC_FIELD"):
                    operation()
            self.assertFalse((root / "missing.yaml").exists())

    def test_create_and_apply_require_complete_body_coverage_before_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = registry.WorkingGraphRegistry(root)
            provenance = self.provenance(root)
            body = {"schema": "x", "C": {"shape": "bounded"}, "unexpected_extension": True}
            with self.assertRaisesRegex(registry.RegistryError, "HOLD_UNMAPPED_SEMANTIC_FIELD"):
                store.create("work-1", body, semantic_provenance_binding=provenance)
            self.assertFalse(store._path("work-1").exists())

            valid = {"schema": "x", "C": {"shape": "bounded"}}
            valid_provenance = self.provenance(root)
            valid_provenance["semantic_field_definition_coverage"] = {
                "schema": valid_provenance["semantic_field_definition_coverage"]["schema"],
                "C.shape": valid_provenance["semantic_field_definition_coverage"]["C.shape"],
            }
            store.create("work-1", valid, semantic_provenance_binding=valid_provenance)
            before = store._path("work-1").read_bytes()
            invalid = {**valid, "unexpected_extension": True}
            with self.assertRaisesRegex(registry.RegistryError, "HOLD_UNMAPPED_SEMANTIC_FIELD"):
                store.apply_maat_delta("work-1", invalid, valid_provenance)
            self.assertEqual(store._path("work-1").read_bytes(), before)

    def test_write_readback_hold_removes_create_and_restores_apply_preimage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = registry.WorkingGraphRegistry(root)
            body = {"schema": "x", "C": {"shape": "bounded"}}
            provenance = self.provenance(root)
            with patch.object(store, "verify_readback", return_value=False):
                with self.assertRaisesRegex(registry.RegistryError, "HOLD_WRITE_READBACK"):
                    store.create("work-1", body, semantic_provenance_binding=provenance)
            self.assertFalse(store._path("work-1").exists())

            store.create("work-1", body, semantic_provenance_binding=provenance)
            before = store._path("work-1").read_bytes()
            current = store.load("work-1")
            with patch.object(store, "verify_readback", return_value=False):
                with self.assertRaisesRegex(registry.RegistryError, "HOLD_WRITE_READBACK"):
                    store.apply_maat_delta(
                        "work-1",
                        body,
                        provenance,
                        expected_revision=current["revision"],
                        expected_digest=current["maat_body_digest"],
                    )
            self.assertEqual(store._path("work-1").read_bytes(), before)

            with patch.object(store, "verify_readback", return_value=False):
                with self.assertRaisesRegex(registry.RegistryError, "HOLD_WRITE_READBACK"):
                    store.update_addendum("work-1", {"observations": ["changed"], "source_refs": []})
            self.assertEqual(store._path("work-1").read_bytes(), before)

    def maat_body(self):
        return {"schema": "harness.honcho.cps_cluster.v1", "C": {"shape": "bounded"}}

    def w2_receipt(self, store, work_id="work-1"):
        graph = store.load(work_id)
        return {
            "work_id": work_id,
            "graph_ref": str(store._path(work_id).resolve()),
            "graph_revision": graph["revision"],
            "graph_digest": graph["maat_body_digest"],
            "stage_ref": "S:W2",
            "owner_ref": "ptah",
            "run_handle": "run-1",
            "attempt": 1,
            "immutable_body_digest": "b" * 64,
            "parent_edge_ref": "C1.P2/S2",
            "status": "observed",
            "changed_paths": [],
            "return_to_node_ref": "C1.P2",
        }

    def return_body(self, status="satisfied"):
        body = self.maat_body()
        body["derived_c_lineage"] = {
            "issued_by": "maat", "status": "accepted", "derived_c_ref": "derived-C:closure",
            "parent_work_id": "parent-work", "parent_graph_ref": "graph:parent",
            "parent_graph_revision": 1, "parent_graph_digest": "a" * 64,
            "blocked_receipt_ref": "receipt:blocked", "parent_edge_ref": "C1.P2/S2",
            "return_to_node_ref": "C1.P2",
        }
        body["returns_to"] = [{
            "kind": "returns_to",
            "id": "return:C1.P2",
            "from": "derived-C:closure",
            "to": "C1.P2",
            "parent_edge_ref": "C1.P2/S2",
            "resume_if": [
                {"kind": "evidence_ref", "ref": "evidence:derived-C"},
                {"kind": "derived_c_ac_satisfied", "ref": "AC:derived-C"},
                {"kind": "execution_terminal_unblocked", "ref": "execution:derived-C"},
            ],
            "status": status,
        }]
        return body

    def checkpoint_args(self, graph_source):
        return {
            "repository": {"root": "/repo", "branch": "feature", "upstream": "origin/feature"},
            "scoped_paths": [str(graph_source), ".harness/hermes/tools/cps_working_graph_registry.py"],
            "excluded_dirty_paths": [".harness/hermes/tools/lifecycle_runner.py"],
            "closure_AC_ref": "AC:git-closure",
            "CPS_refs": {"C": "C:work-1", "P": ["P:materialize"], "S": "S:git", "AC": "AC:git-closure", "packet": "packet:work-1@r1"},
            "prohibited_actions": ["git add -A", "stash", "main push"],
            "owner_approval": True,
            "commit_message": "Close semantic checkpoint\n\nCPS-Packet: packet:work-1@r1",
            "verification_command": "/usr/bin/python3 -m unittest tests.test_cps_working_graph_registry",
        }

    def preauthorization(self, body, *, predicate_id="lane_b_exact_pass_v1", source="active", target="satisfied"):
        return {
            "id": "transition:S1:satisfied",
            "issued_by": "maat",
            "authority_revision": 1,
            "authority_digest": registry._digest(body),
            "source_state_ref": "/maat_body/lifecycle",
            "source_lifecycle": source,
            "trigger": {
                "predicate_id": predicate_id,
                "predicate_version": "1",
                "execution_case_refs": ["case.json"],
                "required_lane_B_AC_refs": ["ac.json"],
                "required_evidence_refs": ["evidence.json"],
            },
            "target": {
                "target_state_ref": "/maat_body/lifecycle",
                "target_lifecycle": target,
            },
            "allowed_delta_paths": ["/maat_body/lifecycle"],
            "forbidden_delta_paths": [],
            "expires_on_revision_change": True,
            "replay_policy": "idempotent",
            "failure_disposition": "hold_no_write",
        }

    def preauthorized_body(self, lifecycle="active"):
        body = self.maat_body()
        body["lifecycle"] = lifecycle
        return body

    def preauth_provenance(self, root):
        provenance = self.provenance(root)
        provenance["semantic_field_definition_coverage"]["lifecycle"] = f"{provenance['canonical_source_locator']}:104"
        return provenance

    def preauth_fixture(self, root, *, status="pass", predicate_id="lane_b_exact_pass_v1", source="active", target="satisfied"):
        store = registry.WorkingGraphRegistry(root)
        body = self.preauthorized_body(source)
        authorization = self.preauthorization(body, predicate_id=predicate_id, source=source, target=target)
        graph = store.create(
            "work-1", body,
            semantic_provenance_binding=self.preauth_provenance(root),
            pre_authorized_transitions=[authorization],
        )
        graph_ref = str(store._path("work-1").resolve())
        common = {
            "graph_ref": graph_ref,
            "graph_revision": graph["revision"],
            "graph_digest": graph["maat_body_digest"],
            "stage_ref": "S1",
            "parent_edge_ref": "edge:S1",
        }
        documents = {
            "case.json": {"ref": "case.json", "event_kind": "terminal", "status": status, **common},
            "ac.json": {"ref": "ac.json", "status": "satisfied", **common},
            "evidence.json": {"ref": "evidence.json", "status": "observed", **common},
        }
        binding = {
            "graph_ref": graph_ref,
            "graph_revision": graph["revision"],
            "graph_digest": graph["maat_body_digest"],
            "evidence_digests": {ref: registry._digest(value) for ref, value in documents.items()},
        }
        return store, graph, documents, binding

    def materialize(self, store, documents, binding):
        return store.materialize_pre_authorized_transition(
            "work-1", "transition:S1:satisfied", binding, documents.__getitem__,
        )

    def test_T04_terminal_pass_without_authorization_holds_without_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = registry.WorkingGraphRegistry(root)
            body = self.preauthorized_body()
            store.create("work-1", body, semantic_provenance_binding=self.preauth_provenance(root))
            before = store._path("work-1").read_bytes()

            with self.assertRaisesRegex(registry.RegistryError, "HOLD_PREAUTH_MISSING"):
                store.materialize_pre_authorized_transition(
                    "work-1", "transition:S1:satisfied", {}, lambda ref: {},
                )

            self.assertEqual(store._path("work-1").read_bytes(), before)

    def test_T05_exact_authorization_and_predicate_materialize_one_named_transition(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, graph, documents, binding = self.preauth_fixture(Path(tmp))
            result = self.materialize(store, documents, binding)
            readback = store.load("work-1")

            self.assertEqual(readback["revision"], graph["revision"] + 1)
            self.assertEqual(readback["maat_body"]["lifecycle"], "satisfied")
            self.assertEqual(len(readback["materialized_transitions"]), 1)
            self.assertEqual(result, readback["materialized_transitions"][0])
            self.assertEqual(result["transition_id"], "transition:S1:satisfied")
            self.assertEqual(result["resulting_digest"], readback["maat_body_digest"])

    def test_T06_terminal_fail_or_blocked_never_writes_success(self):
        for status in ("fail", "blocked"):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as tmp:
                store, _, documents, binding = self.preauth_fixture(Path(tmp), status=status)
                before = store._path("work-1").read_bytes()
                with self.assertRaisesRegex(registry.RegistryError, "HOLD_PREAUTH_PREDICATE"):
                    self.materialize(store, documents, binding)
                self.assertEqual(store._path("work-1").read_bytes(), before)

    def test_T07_revision_digest_or_graph_binding_mismatch_is_stale_without_write(self):
        for field, value in (("graph_revision", 2), ("graph_digest", "0" * 64), ("graph_ref", "/wrong/graph.yaml")):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                store, _, documents, binding = self.preauth_fixture(Path(tmp))
                binding[field] = value
                before = store._path("work-1").read_bytes()
                with self.assertRaisesRegex(registry.RegistryError, "HOLD_PREAUTH_STALE"):
                    self.materialize(store, documents, binding)
                self.assertEqual(store._path("work-1").read_bytes(), before)

    def test_T08_false_predicate_missing_or_changed_reload_holds_without_write(self):
        for mutation in ("missing", "digest", "ac"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as tmp:
                store, _, documents, binding = self.preauth_fixture(Path(tmp))
                if mutation == "missing":
                    documents.pop("evidence.json")
                elif mutation == "digest":
                    binding["evidence_digests"]["case.json"] = "0" * 64
                else:
                    documents["ac.json"]["status"] = "pending"
                before = store._path("work-1").read_bytes()
                with self.assertRaisesRegex(registry.RegistryError, "HOLD_PREAUTH_PREDICATE"):
                    self.materialize(store, documents, binding)
                self.assertEqual(store._path("work-1").read_bytes(), before)

    def test_T09_unauthorized_delta_path_holds_without_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store, _, documents, binding = self.preauth_fixture(root)
            graph = store.load("work-1")
            graph["pre_authorized_transitions"][0]["allowed_delta_paths"] = ["/maat_body/C/shape"]
            registry._write(store._path("work-1"), graph)
            before = store._path("work-1").read_bytes()
            with self.assertRaisesRegex(registry.RegistryError, "HOLD_PREAUTH_SCOPE"):
                self.materialize(store, documents, binding)
            self.assertEqual(store._path("work-1").read_bytes(), before)

    def test_T10_concurrent_materializers_create_one_revision_and_one_record(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier

        with tempfile.TemporaryDirectory() as tmp:
            store, graph, documents, binding = self.preauth_fixture(Path(tmp))
            barrier = Barrier(2)

            def materialize():
                barrier.wait()
                return self.materialize(store, documents, binding)

            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda _: materialize(), range(2)))
            readback = store.load("work-1")
            self.assertEqual(results[0], results[1])
            self.assertEqual(readback["revision"], graph["revision"] + 1)
            self.assertEqual(len(readback["materialized_transitions"]), 1)

    def test_T11_duplicate_replay_returns_same_ref_without_revision(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, _, documents, binding = self.preauth_fixture(Path(tmp))
            first = self.materialize(store, documents, binding)
            before = store._path("work-1").read_bytes()
            second = self.materialize(store, {}, {})
            self.assertEqual(second, first)
            self.assertEqual(store._path("work-1").read_bytes(), before)

    def test_T29_blocked_parent_exact_resume_is_the_only_resumable_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, graph, documents, binding = self.preauth_fixture(
                Path(tmp), status="blocked", predicate_id="blocked_parent_exact_resume_v1",
                source="blocked", target="resumable",
            )
            result = self.materialize(store, documents, binding)
            readback = store.load("work-1")
            self.assertEqual(readback["maat_body"]["lifecycle"], "resumable")
            self.assertEqual(readback["revision"], graph["revision"] + 1)
            self.assertEqual(result["predicate_id"], "blocked_parent_exact_resume_v1")

    def test_create_uses_single_declared_yaml_source_and_preserves_exact_body(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = registry.WorkingGraphRegistry(Path(tmp))
            issued = self.maat_body()
            graph = self.create(store, "work-1", issued)
            same = store.load("work-1")
            self.assertEqual(same["work_id"], "work-1")
            self.assertEqual(same["maat_body"], issued)
            self.assertEqual(same["maat_body_digest"], graph["maat_body_digest"])
            self.assertEqual(store._path("work-1"), Path(tmp) / "work-1.yaml")
            self.assertEqual([path.name for path in Path(tmp).iterdir()], ["work-1.yaml"])
            self.assertTrue(store.verify_readback("work-1", issued))
            with self.assertRaises(registry.RegistryError):
                self.create(store, "work-1", issued)

    def test_readback_rejects_changed_work_id_body_or_digest(self):
        for mutation in ("work_id", "body", "digest"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as tmp:
                store = registry.WorkingGraphRegistry(Path(tmp))
                issued = self.maat_body()
                self.create(store, "work-1", issued)
                path = Path(tmp) / "work-1.yaml"
                value = json.loads(path.read_text())
                if mutation == "work_id":
                    value["work_id"] = "other-work"
                elif mutation == "body":
                    value["maat_body"]["C"]["shape"] = "changed"
                    value["maat_body_digest"] = registry._digest(value["maat_body"])
                else:
                    value["maat_body_digest"] = "0" * 64
                path.write_text(json.dumps(value), encoding="utf-8")
                self.assertFalse(store.verify_readback("work-1", issued))

    def test_addendum_is_observations_and_source_refs_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = registry.WorkingGraphRegistry(Path(tmp))
            self.create(store, "work-1", self.maat_body())
            graph = store.update_addendum("work-1", {"observations": ["readback ok"], "source_refs": ["run:1"]})
            self.assertEqual(graph["revision"], 1)
            for invalid in ({"source_pointers": ["x"]}, {"verdict": "retain"}, {"observations": [], "source_refs": [], "extra": True}):
                with self.assertRaises(registry.RegistryError):
                    store.update_addendum("work-1", invalid)

    def test_addendum_recursively_rejects_semantic_keys_and_preserves_exact_body_digest(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = registry.WorkingGraphRegistry(Path(tmp))
            issued = self.maat_body()
            before = self.create(store, "work-1", issued)
            before_body_bytes = registry._canonical(before["maat_body"])
            semantic_keys = ("maat_body", "verdict", "C", "P", "S", "AC", "ordered_P", "ordered_S", "selected_agents", "audit_scope", "edge", "order", "actor", "closure", "task_AC", "evidence")
            for key in semantic_keys:
                with self.subTest(key=key), self.assertRaises(registry.RegistryError):
                    store.update_addendum("work-1", {"observations": [{"nested": [{key: "semantic"}]}], "source_refs": ["run:1"]})
                with self.subTest(source_ref_key=key), self.assertRaises(registry.RegistryError):
                    store.update_addendum("work-1", {"observations": [], "source_refs": [{"nested": {key: "semantic"}}]})
            after = store.update_addendum("work-1", {"observations": [{"readback": "ok"}], "source_refs": ["run:1"]})
            self.assertEqual(registry._canonical(after["maat_body"]), before_body_bytes)
            self.assertEqual(after["maat_body_digest"], before["maat_body_digest"])

    def test_addendum_rejects_semantic_keys_nested_in_tuples_and_sets(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = registry.WorkingGraphRegistry(Path(tmp))
            self.create(store, "work-1", self.maat_body())
            class HashableDict(dict):
                def __hash__(self):
                    return id(self)

            nested_values = (
                ("tuple", ({"verdict": "semantic"},)),
                ("set", {HashableDict(evidence="semantic")}),
            )
            for container, value in nested_values:
                with self.subTest(container=container), self.assertRaises(registry.RegistryError):
                    store.update_addendum("work-1", {"observations": [value], "source_refs": ["run:1"]})

    def test_unknown_semantic_extensions_hold_without_graph_creation(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = registry.WorkingGraphRegistry(Path(tmp))
            self.create(store, "work-1", self.maat_body())
            for index, body in enumerate((
                {"custom": {"anything": [1, 2]}},
                {"verdict": "retain"},
                {**self.maat_body(), "unexpected_extension": True},
            ), start=2):
                with self.subTest(body=body), self.assertRaisesRegex(
                    registry.RegistryError, "HOLD_UNMAPPED_SEMANTIC_FIELD",
                ):
                    self.create(store, f"work-{index}", body)
                self.assertFalse(store._path(f"work-{index}").exists())

    def test_maat_update_preserves_canonical_shape_and_only_explicit_split_creates_child(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = registry.WorkingGraphRegistry(Path(tmp))
            self.create(store, "work-1", self.maat_body())
            replacement = self.maat_body()
            replacement["C"]["shape"] = "single"
            provenance = self.provenance(Path(tmp))
            current = store.load("work-1")
            revised = store.apply_maat_delta(
                "work-1",
                replacement,
                provenance,
                expected_revision=current["revision"],
                expected_digest=current["maat_body_digest"],
            )
            self.assertEqual(revised["revision"], 2)
            child = store.split("work-1", "work-2", replacement, {"split_id": "s1", "issued_by": "maat", "reason": "explicit split"}, provenance)
            self.assertEqual(child["split_from"], "work-1")

    def test_stale_and_concurrent_cas_allow_one_writer_without_other_writes(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = registry.WorkingGraphRegistry(root)
            graph = self.create(store, "work-1", self.maat_body())
            store.append_execution_receipt("work-1", {
                "parent_edge_ref": "C1.P2/S2",
                "status": "pass",
                "changed_paths": [],
                "return_to_node_ref": "C1.P2",
            })
            graph_path = store._path("work-1")
            sidecar_path = store._execution_receipts_path("work-1")

            for expected_revision, expected_digest in (
                (graph["revision"] - 1, graph["maat_body_digest"]),
                (graph["revision"], "0" * 64),
            ):
                graph_preimage = graph_path.read_bytes()
                sidecar_preimage = sidecar_path.read_bytes()
                residues = sorted(path.name for path in root.iterdir())
                with self.subTest(expected_revision=expected_revision, expected_digest=expected_digest):
                    with self.assertRaisesRegex(registry.RegistryError, "HOLD_PREAUTH_CAS"):
                        store.apply_maat_delta(
                            "work-1",
                            self.maat_body(),
                            self.provenance(root),
                            expected_revision=expected_revision,
                            expected_digest=expected_digest,
                        )
                    self.assertEqual(graph_path.read_bytes(), graph_preimage)
                    self.assertEqual(sidecar_path.read_bytes(), sidecar_preimage)
                    self.assertEqual(sorted(path.name for path in root.iterdir()), residues)

            barrier = Barrier(2)
            bodies = []
            for shape in ("writer-a", "writer-b"):
                body = self.maat_body()
                body["C"]["shape"] = shape
                bodies.append(body)

            def write(body):
                barrier.wait()
                try:
                    revised = store.apply_maat_delta(
                        "work-1",
                        body,
                        self.provenance(root),
                        expected_revision=graph["revision"],
                        expected_digest=graph["maat_body_digest"],
                    )
                    return "write", revised
                except registry.RegistryError as error:
                    return str(error), None

            graph_preimage = graph_path.read_bytes()
            sidecar_preimage = sidecar_path.read_bytes()
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(write, bodies))
            final = store.load("work-1")

            self.assertEqual([status for status, _ in results].count("write"), 1)
            self.assertEqual([status for status, _ in results].count("HOLD_PREAUTH_CAS"), 1)
            self.assertEqual(final["revision"], graph["revision"] + 1)
            self.assertNotEqual(graph_path.read_bytes(), graph_preimage)
            self.assertEqual(sidecar_path.read_bytes(), sidecar_preimage)
            self.assertFalse(any(path.suffix == ".tmp" for path in root.iterdir()))

    def test_return_edge_rejects_malformed_and_only_exact_satisfied_edge_continues(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = registry.WorkingGraphRegistry(root)
            malformed = self.return_body()
            malformed["returns_to"][0]["condition"] = "resume when Maat thinks it is ready"
            with self.assertRaisesRegex(registry.RegistryError, "HOLD_RETURN_EDGE_SCHEMA"):
                self.create(store, "malformed", malformed)
            self.assertFalse(store._path("malformed").exists())

            pending = self.return_body("pending")
            graph = self.create(store, "work-1", pending)
            parent = store.append_execution_receipt("work-1", {
                "parent_edge_ref": "C1.P2/S2",
                "status": "pass",
                "changed_paths": [],
                "return_to_node_ref": "C1.P2",
            })
            graph_path = store._path("work-1")
            sidecar_path = store._execution_receipts_path("work-1")

            def held(**overrides):
                arguments = {
                    "returns_to_ref": "return:C1.P2",
                    "parent_receipt_ref": parent["receipt_ref"],
                    "parent_edge_ref": "C1.P2/S2",
                    "return_to_node_ref": "C1.P2",
                }
                arguments.update(overrides)
                graph_preimage = graph_path.read_bytes()
                receipt_preimage = sidecar_path.read_bytes()
                with self.assertRaisesRegex(registry.RegistryError, "HOLD_RETURN_EDGE"):
                    store.consume_return_edge("work-1", **arguments)
                self.assertEqual(graph_path.read_bytes(), graph_preimage)
                self.assertEqual(sidecar_path.read_bytes(), receipt_preimage)

            held()
            for status in ("eligible", "blocked"):
                next_body = self.return_body(status)
                graph = store.apply_maat_delta(
                    "work-1",
                    next_body,
                    self.provenance(root),
                    expected_revision=graph["revision"],
                    expected_digest=graph["maat_body_digest"],
                )
                held()
            satisfied = self.return_body("satisfied")
            revised = store.apply_maat_delta(
                "work-1",
                satisfied,
                self.provenance(root),
                expected_revision=graph["revision"],
                expected_digest=graph["maat_body_digest"],
            )
            held(parent_edge_ref="wrong-edge")
            held(return_to_node_ref="wrong-target")
            held(returns_to_ref="missing-edge")

            graph_preimage = graph_path.read_bytes()
            continuation = store.consume_return_edge(
                "work-1",
                returns_to_ref="return:C1.P2",
                parent_receipt_ref=parent["receipt_ref"],
                parent_edge_ref="C1.P2/S2",
                return_to_node_ref="C1.P2",
            )
            self.assertEqual(continuation["returns_to_ref"], "return:C1.P2")
            self.assertEqual(continuation["parent_receipt_ref"], parent["receipt_ref"])
            self.assertEqual(graph_path.read_bytes(), graph_preimage)
            self.assertEqual(store.load("work-1")["revision"], revised["revision"])

    def test_return_edge_schema_and_runtime_reject_the_same_invalid_shapes_before_write(self):
        working_schema = json.loads((SCHEMAS / "cps-working-graph.schema.yaml").read_text())
        edge_schema = working_schema["$defs"]["return_edge"]
        resume_schema = working_schema["$defs"]["resume_condition"]
        self.assertEqual(set(edge_schema["required"]), registry.RETURN_EDGE_FIELDS)
        self.assertEqual(set(edge_schema["properties"]), registry.RETURN_EDGE_FIELDS)
        self.assertFalse(edge_schema["additionalProperties"])
        self.assertEqual(set(edge_schema["properties"]["status"]["enum"]), registry.RETURN_EDGE_STATUSES)
        self.assertEqual(set(resume_schema["required"]), registry.RESUME_IF_FIELDS)
        self.assertEqual(set(resume_schema["properties"]["kind"]["enum"]), registry.RESUME_IF_KINDS)
        self.assertFalse(resume_schema["additionalProperties"])

        with tempfile.TemporaryDirectory() as tmp:
            store = registry.WorkingGraphRegistry(Path(tmp))
            invalid_bodies = []

            missing_kind = self.return_body()
            missing_kind["returns_to"][0]["resume_if"].pop()
            invalid_bodies.append(missing_kind)

            duplicate_kind = self.return_body()
            duplicate_kind["returns_to"][0]["resume_if"][2]["kind"] = "evidence_ref"
            invalid_bodies.append(duplicate_kind)

            extra_property = self.return_body()
            extra_property["returns_to"][0]["resume_if"][0]["predicate"] = "natural language"
            invalid_bodies.append(extra_property)

            empty_ref = self.return_body()
            empty_ref["returns_to"][0]["resume_if"][0]["ref"] = ""
            invalid_bodies.append(empty_ref)

            duplicate_id = self.return_body()
            second = json.loads(json.dumps(duplicate_id["returns_to"][0]))
            second["from"] = "derived-C:other-closure"
            duplicate_id["returns_to"].append(second)
            invalid_bodies.append(duplicate_id)

            invalid_status = self.return_body()
            invalid_status["returns_to"][0]["status"] = "ready"
            invalid_bodies.append(invalid_status)

            for index, body in enumerate(invalid_bodies):
                with self.subTest(index=index), self.assertRaisesRegex(
                    registry.RegistryError, "HOLD_RETURN_EDGE_SCHEMA",
                ):
                    self.create(store, f"invalid-{index}", body)
                self.assertFalse(store._path(f"invalid-{index}").exists())

    def test_execution_receipt_schema_accepts_complete_w2_identity_and_legacy(self):
        schema = json.loads((SCHEMAS / "execution-receipt.schema.yaml").read_text())
        execution = schema["$defs"]["execution_receipt"]
        identity_fields = registry.EXECUTION_RECEIPT_IDENTITY_FIELDS
        bundle_guard = execution["allOf"][0]

        self.assertEqual(
            set(execution["required"]),
            {"family", "receipt_ref", "transition_from_ref", "work_id", "checkpoint_id", "status", "recorded_at"},
        )
        self.assertTrue(identity_fields.issubset(execution["properties"]))
        self.assertEqual(set(bundle_guard["then"]["required"]), identity_fields)
        self.assertEqual(bundle_guard["then"]["properties"]["work_id"], {"type": "string", "minLength": 1})

    def test_execution_receipt_schema_allows_legacy_facts_work_id(self):
        schema = json.loads((SCHEMAS / "execution-receipt.schema.yaml").read_text())
        forbidden = {
            clause["required"][0]
            for clause in schema["$defs"]["facts_without_identity"]["not"]["anyOf"]
        }

        self.assertEqual(forbidden, registry.EXECUTION_RECEIPT_W2_IDENTITY_FIELDS)
        self.assertNotIn("work_id", forbidden)

    def test_execution_receipt_schema_rejects_partial_malformed_and_nested_w2_identity(self):
        schema = json.loads((SCHEMAS / "execution-receipt.schema.yaml").read_text())
        execution = schema["$defs"]["execution_receipt"]
        properties = execution["properties"]
        bundle_guard = execution["allOf"][0]
        triggered_fields = {
            clause["required"][0] for clause in bundle_guard["if"]["anyOf"]
        }
        hidden_identity_fields = {
            clause["required"][0]
            for clause in schema["$defs"]["facts_without_identity"]["not"]["anyOf"]
        }

        self.assertEqual(triggered_fields, registry.EXECUTION_RECEIPT_W2_IDENTITY_FIELDS)
        self.assertEqual(hidden_identity_fields, registry.EXECUTION_RECEIPT_W2_IDENTITY_FIELDS)
        for field in ("graph_ref", "stage_ref", "owner_ref", "run_handle"):
            self.assertEqual(properties[field], {"type": "string", "minLength": 1})
        for field in ("graph_revision", "attempt"):
            self.assertEqual(properties[field], {"type": "integer", "minimum": 1})
        for field in ("graph_digest", "immutable_body_digest"):
            self.assertEqual(properties[field], {"type": "string", "pattern": "^[0-9a-f]{64}$"})
        self.assertEqual(properties["facts"], {"$ref": "#/$defs/facts_without_identity"})

    def test_execution_receipt_schema_defines_exact_continuation_record(self):
        receipt_schema = json.loads((SCHEMAS / "execution-receipt.schema.yaml").read_text())
        continuation = receipt_schema["$defs"]["continuation_receipt"]
        fields = {
            "family", "receipt_ref", "parent_receipt_ref", "work_id",
            "parent_edge_ref", "returns_to_ref", "return_to_node_ref",
            "disposition", "recorded_at",
        }
        self.assertEqual(set(continuation["required"]), fields)
        self.assertEqual(set(continuation["properties"]), fields)
        self.assertEqual(continuation["properties"]["family"], {"const": "continuation_receipt"})
        self.assertEqual(continuation["properties"]["disposition"], {"const": "continue"})
        self.assertFalse(continuation["additionalProperties"])

    def test_checkpoint_packet_matches_contract_exactly(self):
        calls = []
        with tempfile.TemporaryDirectory() as tmp:
            store = registry.WorkingGraphRegistry(Path(tmp))
            graph = self.create(store, "work-1", self.maat_body())
            graph_source = Path(tmp) / "work-1.yaml"
            packet, receipt = store.checkpoint("work-1", dispatcher=lambda value: calls.append(value) or {"status": "git_pending"}, **self.checkpoint_args(graph_source))
            self.assertEqual(packet["schema"], "harness.cps.semantic-checkpoint-git-closure.v1")
            self.assertEqual(packet["checkpoint_id"], "work-1@r1")
            self.assertEqual(packet["graph_source"], {"ref": str(graph_source), "digest": graph["maat_body_digest"], "expected_prior_revision": None})
            self.assertEqual(packet["scoped_paths"], [str(graph_source), ".harness/hermes/tools/cps_working_graph_registry.py"])
            self.assertEqual(packet["owner_approval"], True)
            self.assertEqual(packet["execution_instruction"], "Perform only the scoped Git closure described by this packet: run verification_command if present; stage only scoped_paths; create the exact commit_message; push only repository.branch to repository.upstream; then report facts.")
            self.assertEqual(packet["commit_message"], "Close semantic checkpoint\n\nCPS-Packet: packet:work-1@r1")
            self.assertEqual(packet["verification_command"], "/usr/bin/python3 -m unittest tests.test_cps_working_graph_registry")
            self.assertEqual(set(packet), {"schema", "checkpoint_id", "work_id", "graph_source", "repository", "scoped_paths", "excluded_dirty_paths", "closure_AC_ref", "CPS_refs", "prohibited_actions", "owner_approval", "execution_instruction", "commit_message", "verification_command"})
            self.assertEqual(receipt["status"], "git_pending")
            self.assertEqual(len(calls), 1)

    def test_schema_documents_preserve_registry_contract_shape(self):
        working_schema = json.loads((SCHEMAS / "cps-working-graph.schema.yaml").read_text())
        delta_schema = json.loads((SCHEMAS / "maat-semantic-delta.schema.yaml").read_text())
        self.assertEqual(set(working_schema["required"]), {"family", "work_id", "revision", "maat_body", "maat_body_digest", "pre_authorized_transitions", "materialized_transitions", "semantic_provenance_binding", "hermes_kann_addendum"})
        self.assertFalse(working_schema["additionalProperties"])
        preauthorized = working_schema["$defs"]["pre_authorized_transition"]
        trigger = working_schema["$defs"]["pre_authorized_trigger"]
        target = working_schema["$defs"]["pre_authorized_target"]
        materialized = working_schema["$defs"]["materialized_transition"]
        self.assertEqual(set(preauthorized["required"]), registry.PREAUTHORIZED_TRANSITION_FIELDS)
        self.assertEqual(set(preauthorized["properties"]), registry.PREAUTHORIZED_TRANSITION_FIELDS)
        self.assertEqual(set(trigger["required"]), registry.PREAUTHORIZED_TRIGGER_FIELDS)
        self.assertEqual(set(trigger["properties"]), registry.PREAUTHORIZED_TRIGGER_FIELDS)
        self.assertEqual(set(target["required"]), registry.PREAUTHORIZED_TARGET_FIELDS)
        self.assertEqual(set(materialized["required"]), registry.MATERIALIZED_TRANSITION_FIELDS)
        self.assertEqual(set(materialized["properties"]), registry.MATERIALIZED_TRANSITION_FIELDS)
        self.assertEqual(set(trigger["properties"]["predicate_id"]["enum"]), {"lane_b_exact_pass_v1", "blocked_parent_exact_resume_v1"})
        self.assertFalse(preauthorized["additionalProperties"])
        self.assertFalse(materialized["additionalProperties"])
        returns_to = working_schema["properties"]["maat_body"]["properties"]["returns_to"]
        return_edge = working_schema["$defs"]["return_edge"]
        derived_lineage = working_schema["$defs"]["derived_c_lineage"]
        resume_condition = working_schema["$defs"]["resume_condition"]
        self.assertTrue(returns_to["uniqueItems"])
        self.assertEqual(returns_to["items"], {"$ref": "#/$defs/return_edge"})
        self.assertEqual(set(return_edge["required"]), registry.RETURN_EDGE_FIELDS)
        self.assertEqual(set(return_edge["properties"]), registry.RETURN_EDGE_FIELDS)
        self.assertFalse(return_edge["additionalProperties"])
        self.assertEqual(set(derived_lineage["required"]), registry.DERIVED_C_LINEAGE_FIELDS)
        self.assertEqual(set(derived_lineage["properties"]), registry.DERIVED_C_LINEAGE_FIELDS)
        self.assertFalse(derived_lineage["additionalProperties"])
        self.assertEqual(set(return_edge["properties"]["status"]["enum"]), registry.RETURN_EDGE_STATUSES)
        self.assertEqual(set(resume_condition["required"]), registry.RESUME_IF_FIELDS)
        self.assertEqual(set(resume_condition["properties"]), registry.RESUME_IF_FIELDS)
        self.assertEqual(set(resume_condition["properties"]["kind"]["enum"]), registry.RESUME_IF_KINDS)
        self.assertFalse(resume_condition["additionalProperties"])
        self.assertEqual(set(working_schema["$defs"]["addendum"]["properties"]), registry.ADDENDUM_KEYS)
        self.assertFalse(working_schema["$defs"]["addendum"]["additionalProperties"])
        self.assertEqual(delta_schema["properties"]["maat_body"], {"type": "object"})
        self.assertIn("materialization_context", delta_schema["required"])
        self.assertEqual(set(delta_schema["properties"]["hermes_kann_addendum"]["properties"]), registry.ADDENDUM_KEYS)
        self.assertEqual(
            set(working_schema["$defs"]["semantic_provenance_binding"]["required"]),
            registry.SEMANTIC_PROVENANCE_FIELDS,
        )
        self.assertEqual(
            set(delta_schema["$defs"]["semantic_provenance_binding"]["required"]),
            registry.SEMANTIC_PROVENANCE_FIELDS,
        )

    def test_continuation_append_preserves_receipt_prefix_and_replay_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = registry.WorkingGraphRegistry(Path(tmp))
            graph = self.create(store, "work-1", self.maat_body())
            parent = store.append_execution_receipt("work-1", {
                "parent_edge_ref": "C1.P2/S2",
                "status": "pass",
                "changed_paths": [],
                "return_to_node_ref": "C1.P2",
            })
            sidecar = store._execution_receipts_path("work-1")
            prefix = json.loads(sidecar.read_text())["receipts"]
            prefix_digest = registry._digest(prefix)

            continuation = store.append_continuation_receipt(
                "work-1",
                parent_receipt_ref=parent["receipt_ref"],
                parent_edge_ref="C1.P2/S2",
                returns_to_ref="return:C1.P2",
                return_to_node_ref="C1.P2",
            )
            after = json.loads(sidecar.read_text())["receipts"]

            self.assertEqual(after[:-1], prefix)
            self.assertEqual(registry._digest(after[:-1]), prefix_digest)
            self.assertEqual(len(after), len(prefix) + 1)
            self.assertEqual(continuation, after[-1])
            self.assertEqual(continuation["family"], "continuation_receipt")
            self.assertEqual(continuation["parent_receipt_ref"], parent["receipt_ref"])
            self.assertEqual(continuation["work_id"], "work-1")
            self.assertEqual(continuation["disposition"], "continue")
            self.assertEqual(store.load("work-1")["revision"], graph["revision"])

            replay = store.append_continuation_receipt(
                "work-1",
                parent_receipt_ref=parent["receipt_ref"],
                parent_edge_ref="C1.P2/S2",
                returns_to_ref="return:C1.P2",
                return_to_node_ref="C1.P2",
            )
            self.assertEqual(replay, continuation)
            self.assertEqual(json.loads(sidecar.read_text())["receipts"], after)
            self.assertEqual(store.load("work-1")["revision"], graph["revision"])

    def test_concurrent_continuation_replay_appends_exactly_once(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier

        with tempfile.TemporaryDirectory() as tmp:
            store = registry.WorkingGraphRegistry(Path(tmp))
            self.create(store, "work-1", self.maat_body())
            parent = store.append_execution_receipt("work-1", {
                "parent_edge_ref": "C1.P2/S2",
                "status": "pass",
                "changed_paths": [],
                "return_to_node_ref": "C1.P2",
            })
            sidecar = store._execution_receipts_path("work-1")
            prefix = json.loads(sidecar.read_text())["receipts"]
            barrier = Barrier(2)

            def append():
                barrier.wait()
                return store.append_continuation_receipt(
                    "work-1",
                    parent_receipt_ref=parent["receipt_ref"],
                    parent_edge_ref="C1.P2/S2",
                    returns_to_ref="return:C1.P2",
                    return_to_node_ref="C1.P2",
                )

            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda _: append(), range(2)))
            after = json.loads(sidecar.read_text())["receipts"]

            self.assertEqual(results[0], results[1])
            self.assertEqual(after[:-1], prefix)
            self.assertEqual(len(after), len(prefix) + 1)

    def test_resume_parent_edge_dispositions_preserve_the_parent_edge(self):
        parent_edge_ref = "C1.P2/S2"
        cases = (
            ("blocked", ["runtime/output.json"], "reconcile_or_return"),
            ("blocked", [], "resume_or_retry"),
            ("pass", [], "continue"),
        )
        for status, changed_paths, disposition in cases:
            with self.subTest(status=status, changed_paths=changed_paths), tempfile.TemporaryDirectory() as tmp:
                store = registry.WorkingGraphRegistry(Path(tmp))
                self.create(store, "work-1", self.maat_body())
                receipt = {
                    "parent_edge_ref": parent_edge_ref,
                    "status": status,
                    "changed_paths": changed_paths,
                    "return_to_node_ref": "C1.P2",
                }
                if status == "blocked" and changed_paths:
                    receipt["partial_mutation_disposition"] = "reconcile"
                store.append_execution_receipt("work-1", receipt)
                resumed = store.resume_parent_edge("work-1", parent_edge_ref)
                self.assertEqual(resumed["parent_edge_ref"], parent_edge_ref)
                self.assertEqual(resumed["disposition"], disposition)

    def test_T19_return_edge_advances_only_pending_eligible_satisfied_by_preauthorized_cas(self):
        for source, target in (("pending", "eligible"), ("eligible", "satisfied")):
            with self.subTest(source=source, target=target), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                store = registry.WorkingGraphRegistry(root)
                body = self.return_body(source)
                body["derived_c_lineage"] = {
                    "issued_by": "maat", "status": "accepted", "derived_c_ref": "derived-C:closure",
                    "parent_work_id": "parent-work", "parent_graph_ref": "graph:parent",
                    "parent_graph_revision": 7, "parent_graph_digest": "a" * 64,
                    "blocked_receipt_ref": "receipt:blocked", "parent_edge_ref": "C1.P2/S2",
                    "return_to_node_ref": "C1.P2",
                }
                transition_id = f"transition:return:{target}"
                path = "/maat_body/returns_to/0/status"
                authorization = {
                    "id": transition_id, "issued_by": "maat", "authority_revision": 1,
                    "authority_digest": registry._digest(body), "source_state_ref": path,
                    "source_lifecycle": source,
                    "trigger": {"predicate_id": "lane_b_exact_pass_v1", "predicate_version": "1",
                                "execution_case_refs": ["case.json"], "required_lane_B_AC_refs": ["ac.json"],
                                "required_evidence_refs": ["evidence.json"]},
                    "target": {"target_state_ref": path, "target_lifecycle": target},
                    "allowed_delta_paths": [path], "forbidden_delta_paths": [],
                    "expires_on_revision_change": True, "replay_policy": "idempotent",
                    "failure_disposition": "hold_no_write",
                }
                graph = store.create("work-1", body, semantic_provenance_binding=self.provenance(root),
                                     pre_authorized_transitions=[authorization])
                common = {"graph_ref": str(store._path("work-1").resolve()), "graph_revision": 1,
                          "graph_digest": graph["maat_body_digest"]}
                documents = {
                    "case.json": {"ref": "case.json", **common, "event_kind": "terminal", "status": "pass"},
                    "ac.json": {"ref": "ac.json", **common, "status": "satisfied"},
                    "evidence.json": {"ref": "evidence.json", **common, "status": "present"},
                }
                binding = {**common, "evidence_digests": {ref: registry._digest(value) for ref, value in documents.items()}}
                result = store.materialize_pre_authorized_transition("work-1", transition_id, binding, documents.__getitem__)
                readback = store.load("work-1")
                self.assertEqual(readback["maat_body"]["returns_to"][0]["status"], target)
                self.assertEqual(readback["revision"], 2)
                self.assertEqual(result["resulting_digest"], readback["maat_body_digest"])
                self.assertEqual(store.materialize_pre_authorized_transition("work-1", transition_id, binding, documents.__getitem__), result)
                self.assertEqual(store.load("work-1")["revision"], 2)
        with self.assertRaisesRegex(registry.RegistryError, "HOLD_RETURN_EDGE"):
            registry.validate_return_status_transition("eligible", "pending")

    def test_T20_unaccepted_or_mismatched_derived_lineage_holds_without_write(self):
        body = self.return_body("pending")
        binding = {
            "parent_work_id": "work-1", "parent_graph_ref": "graph:work-1", "parent_graph_revision": 2,
            "parent_graph_digest": "a" * 64, "blocked_receipt_ref": "receipt:blocked",
            "parent_edge_ref": "C1.P2/S2", "return_to_node_ref": "C1.P2",
        }
        for lineage in (None, {**binding, "issued_by": "hermes-kann", "status": "accepted", "derived_c_ref": "derived-C:closure"},
                        {**binding, "issued_by": "maat", "status": "candidate", "derived_c_ref": "derived-C:closure"}):
            candidate = json.loads(json.dumps(body))
            if lineage is not None:
                candidate["derived_c_lineage"] = lineage
            else:
                candidate.pop("derived_c_lineage")
            before = registry._canonical(candidate)
            with self.assertRaisesRegex(registry.RegistryError, "HOLD_RETURN_EDGE"):
                registry.validate_accepted_derived_c_lineage(candidate, binding)
            self.assertEqual(registry._canonical(candidate), before)

    def test_w2_execution_receipt_rejects_partial_malformed_and_work_id_mismatch_without_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = registry.WorkingGraphRegistry(root)
            self.create(store, "work-1", self.maat_body())
            complete = self.w2_receipt(store)
            store.append_execution_receipt("work-1", {
                "parent_edge_ref": "C1.P2/S2",
                "status": "observed",
                "changed_paths": [],
                "return_to_node_ref": "C1.P2",
            })
            invalid = []

            partial = {key: complete[key] for key in registry.EXECUTION_RECEIPT_REQUIRED_FIELDS}
            partial["graph_ref"] = complete["graph_ref"]
            invalid.append(partial)

            malformed = dict(complete)
            malformed["graph_revision"] = True
            invalid.append(malformed)
            for field, value in (
                ("work_id", ""),
                ("graph_ref", ""),
                ("stage_ref", ""),
                ("owner_ref", ""),
                ("run_handle", ""),
                ("attempt", True),
                ("attempt", 0),
                ("graph_digest", "A" * 64),
                ("immutable_body_digest", "short"),
            ):
                malformed = dict(complete)
                malformed[field] = value
                invalid.append(malformed)

            mismatched_work = dict(complete)
            mismatched_work["work_id"] = "other-work"
            invalid.append(mismatched_work)
            invalid.append({
                **{key: complete[key] for key in registry.EXECUTION_RECEIPT_REQUIRED_FIELDS},
                "work_id": "other-work",
            })

            sidecar = store._execution_receipts_path("work-1")
            for receipt in invalid:
                preimage = sidecar.read_bytes()
                residues = sorted(path.name for path in root.iterdir())
                with self.subTest(receipt=receipt), self.assertRaises(registry.RegistryError):
                    store.append_execution_receipt("work-1", receipt)
                self.assertEqual(sidecar.read_bytes(), preimage)
                self.assertEqual(sorted(path.name for path in root.iterdir()), residues)
                self.assertFalse(any(path.suffix == ".tmp" for path in root.iterdir()))

    def test_complete_w2_identity_persists_exact_values_and_legacy_receipt_remains_valid(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = registry.WorkingGraphRegistry(Path(tmp))
            self.create(store, "work-1", self.maat_body())
            identity = self.w2_receipt(store)

            stored = store.append_execution_receipt("work-1", identity)
            readback = registry.load_json_or_yaml(store._execution_receipts_path("work-1"))["receipts"][-1]
            for field in registry.EXECUTION_RECEIPT_IDENTITY_FIELDS:
                self.assertEqual(stored[field], identity[field])
                self.assertEqual(readback[field], identity[field])

            legacy = store.append_execution_receipt("work-1", {
                "parent_edge_ref": "C1.P2/S2",
                "status": "pass",
                "changed_paths": [],
                "return_to_node_ref": "C1.P2",
            })
            self.assertEqual(legacy["family"], "execution_receipt")
            self.assertEqual(legacy["work_id"], "work-1")
            self.assertTrue(registry.EXECUTION_RECEIPT_W2_IDENTITY_FIELDS.isdisjoint(legacy))

    def test_legacy_facts_work_id_persists_without_w2_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = registry.WorkingGraphRegistry(Path(tmp))
            self.create(store, "work-1", self.maat_body())
            receipt = {
                "parent_edge_ref": "C1.P2/S2",
                "status": "observed",
                "changed_paths": [],
                "return_to_node_ref": "C1.P2",
                "facts": {"work_id": "legacy-work", "nested": [{"work_id": "legacy-child"}]},
            }

            stored = store.append_execution_receipt("work-1", receipt)
            readback = registry.load_json_or_yaml(store._execution_receipts_path("work-1"))["receipts"][-1]

            self.assertEqual(stored["facts"], receipt["facts"])
            self.assertEqual(readback["facts"], receipt["facts"])
            self.assertTrue(registry.EXECUTION_RECEIPT_W2_IDENTITY_FIELDS.isdisjoint(stored))

    def test_w2_graph_locator_revision_and_digest_mismatch_reject_without_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = registry.WorkingGraphRegistry(root)
            self.create(store, "work-1", self.maat_body())
            store.append_execution_receipt("work-1", {
                "parent_edge_ref": "C1.P2/S2",
                "status": "observed",
                "changed_paths": [],
                "return_to_node_ref": "C1.P2",
            })
            complete = self.w2_receipt(store)
            invalid = []
            for field, value in (
                ("graph_ref", str(root / "." / "other.yaml")),
                ("graph_revision", complete["graph_revision"] + 1),
                ("graph_digest", "0" * 64),
            ):
                receipt = dict(complete)
                receipt[field] = value
                invalid.append(receipt)

            sidecar = store._execution_receipts_path("work-1")
            for receipt in invalid:
                preimage = sidecar.read_bytes()
                residues = sorted(path.name for path in root.iterdir())
                with self.subTest(receipt=receipt), self.assertRaises(registry.RegistryError):
                    store.append_execution_receipt("work-1", receipt)
                self.assertEqual(sidecar.read_bytes(), preimage)
                self.assertEqual(sorted(path.name for path in root.iterdir()), residues)
                self.assertFalse(any(path.suffix == ".tmp" for path in root.iterdir()))

    def test_w2_identity_keys_nested_in_facts_reject_without_sidecar_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = registry.WorkingGraphRegistry(root)
            self.create(store, "work-1", self.maat_body())
            store.append_execution_receipt("work-1", {
                "parent_edge_ref": "C1.P2/S2",
                "status": "observed",
                "changed_paths": [],
                "return_to_node_ref": "C1.P2",
                "facts": {"legacy": ["kept"]},
            })
            sidecar = store._execution_receipts_path("work-1")

            for key in registry.EXECUTION_RECEIPT_W2_IDENTITY_FIELDS:
                for location, facts in (
                    ("direct", {key: "hidden"}),
                    ("nested", {"outer": [{"inner": {key: "hidden"}}]}),
                ):
                    receipt = {
                        "parent_edge_ref": "C1.P2/S2",
                        "status": "observed",
                        "changed_paths": [],
                        "return_to_node_ref": "C1.P2",
                        "facts": facts,
                    }
                    preimage = sidecar.read_bytes()
                    residues = sorted(path.name for path in root.iterdir())
                    with self.subTest(key=key, location=location), self.assertRaises(registry.RegistryError):
                        store.append_execution_receipt("work-1", receipt)
                    self.assertEqual(sidecar.read_bytes(), preimage)
                    self.assertEqual(sorted(path.name for path in root.iterdir()), residues)
                    self.assertFalse(any(path.suffix == ".tmp" for path in root.iterdir()))

    def test_semantic_execution_receipt_rejection_precedes_sidecar_creation(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = registry.WorkingGraphRegistry(Path(tmp))
            self.create(store, "work-1", self.maat_body())
            sidecar = store._execution_receipts_path("work-1")
            with self.assertRaises(registry.RegistryError):
                store.append_execution_receipt("work-1", {
                    "parent_edge_ref": "C1.P2/S2",
                    "status": "pass",
                    "changed_paths": [],
                    "return_to_node_ref": "C1.P2",
                    "C": "semantic mutation",
                })
            self.assertFalse(sidecar.exists())


if __name__ == "__main__":
    unittest.main()
