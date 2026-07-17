import json
import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[1] / ".harness" / "hermes" / "tools"
sys.path.insert(0, str(TOOLS))

import cps_preflight_route_gate as preflight
import cps_working_graph_registry as registry


class FakeProcess:
    returncode = 0

    def __init__(self, body):
        self.stdout = "session_id: maat-test\n" + json.dumps(body, ensure_ascii=False)


class MaatReducerRegistryIntegrationTests(unittest.TestCase):
    def test_T31_final_maat_prompt_receives_only_reloaded_lane_evidence_and_cannot_mutate_goal(self):
        evidence = {
            "status": "eligible_for_maat_audit",
            "semantic_lane": {"graph_ref": "graph:1", "graph_revision": 4, "graph_digest": "a" * 64},
            "execution_lane": {"receipt_ref": "run-1:3", "status": "pass", "parent_edge_ref": "C1/P1", "return_to_node_ref": "C1"},
        }
        contribute = {"production_final_audit": evidence, "Goal_closure": {"status": "pending_maat_final"}}
        prompt = json.loads(preflight._maat_final_prompt(contribute))
        self.assertEqual(prompt["contribute_CPS"]["production_final_audit"], evidence)
        self.assertEqual(prompt["contribute_CPS"]["Goal_closure"]["status"], "pending_maat_final")
        self.assertTrue(any("never infer acceptance or rewrite the root goal" in rule.lower() for rule in prompt["hard_rules"]))
    def provenance(self, root):
        del root
        repo = TOOLS.parents[2]
        source = repo.parent / "harness-brain" / "projects" / repo.name / "decisions" / "cps-memory-lifecycle-and-honcho-anchor.md"
        line_count = len(source.read_text(encoding="utf-8").splitlines())
        return {
            "canonical_source_locator": str(source), "canonical_source_readback": f"{source}:1-{line_count}",
            "current_source_revision": subprocess.check_output(["git", "-C", str(source.parent), "rev-parse", "HEAD"], text=True).strip(),
            "current_content_hash": hashlib.sha256(source.read_bytes()).hexdigest(),
            "canonical_section": f"{source}:75-108",
            "semantic_field_definition_coverage": {"schema": f"{source}:78", "C.shape": f"{source}:85"},
        }

    def test_reducer_requires_exact_packet_and_live_maat_provenance_echo(self):
        with tempfile.TemporaryDirectory() as tmp:
            provenance = self.provenance(tmp)
            anchor = {"schema": "harness.honcho.cps_cluster.v1", "C": {"shape": "bounded"}}
            raw = {"status": "pass", "semantic_anchor": anchor, "semantic_provenance_binding": provenance}
            result = preflight.invoke_maat_reducer(
                {"semantic_anchor": anchor, "semantic_provenance_binding": provenance},
                Path("/repo"),
                process_runner=lambda *args, **kwargs: FakeProcess(raw),
            )
            self.assertEqual(result["semantic_provenance_binding"], provenance)
            changed = json.loads(json.dumps(provenance))
            changed["current_source_revision"] = "prior-maat-default"
            held = preflight.invoke_maat_reducer(
                {"semantic_anchor": anchor, "semantic_provenance_binding": provenance},
                Path("/repo"),
                process_runner=lambda *args, **kwargs: FakeProcess({"status": "pass", "semantic_anchor": anchor, "semantic_provenance_binding": changed}),
            )
            self.assertEqual(held["status"], "hold")
            self.assertEqual(held["failure_codes"], ["HOLD_UNMAPPED_SEMANTIC_FIELD"])
            unknown = preflight.invoke_maat_reducer(
                {"semantic_anchor": anchor, "semantic_provenance_binding": provenance}, Path("/repo"),
                process_runner=lambda *args, **kwargs: FakeProcess({
                    "status": "pass", "semantic_anchor": {**anchor, "invented": True},
                    "semantic_provenance_binding": provenance,
                }),
            )
            self.assertEqual(unknown["failure_codes"], ["HOLD_UNMAPPED_SEMANTIC_FIELD"])
    def runtime_observation(self, root, *, addendum=None):
        body = {"schema": "harness.honcho.cps_cluster.v1", "C": {"shape": "bounded"}}
        provenance = self.provenance(root)
        store = registry.WorkingGraphRegistry(Path(root))
        store.create("work-1", body, semantic_provenance_binding=provenance)
        if addendum is not None:
            store.update_addendum("work-1", addendum)
        packet = {"cps_working_graph_runtime": {"work_id": "work-1", "graph_root": root}}
        files = {
            "candidate": Path(root) / "run" / "c_candidate_packet.json",
            "final_output": Path(root) / "run" / "final_output.json",
        }
        events = [{
            "event_id": "evt-001", "event_type": "seed_created", "parent_event_id": None,
            "iteration": 0, "phase": "initial", "event_payload": {"C": "raw semantic body"},
            "timestamp": "raw stdout", "actor": "selected_agents",
        }]
        receipt = {
            "producer_ref": "adapter:harness-brain:file:v1", "consumer_ref": "build_candidate",
            "outcome": "match", "normalized_result_hash": "hash-1",
            "normalized_result": {"query": "raw prompt"}, "graph_ref": "semantic source body",
        }
        return store, body, packet, files, events, receipt

    def test_invoke_reducer_preserves_exact_parsed_maat_body(self):
        raw = {
            "status": "pass",
            "C": {"opaque": [1, {"name": "원문"}]},
            "unexpected_extension": {"keep": True},
        }
        calls = []

        def runner(*args, **kwargs):
            calls.append((args, kwargs))
            return FakeProcess(raw)

        result = preflight.invoke_maat_reducer({}, Path("/repo"), process_runner=runner)

        self.assertEqual(result["maat_body"], raw)
        self.assertIsNot(result["maat_body"], result)
        self.assertEqual(len(calls), 1)

    def test_opt_in_materialization_creates_graph_source_and_keeps_addendum_separate(self):
        raw = {"schema": "harness.honcho.cps_cluster.v1", "C": {"shape": "bounded"}}
        addendum = {"observations": ["receipt observed"], "source_refs": ["run:1"]}
        with tempfile.TemporaryDirectory() as tmp:
            result = registry.materialize_maat_body(
                raw,
                {"work_id": "work-1", "graph_root": tmp},
                semantic_provenance_binding=self.provenance(tmp),
                addendum=addendum,
            )
            graph = registry.load_json_or_yaml(Path(result["graph_ref"]))

        self.assertEqual(graph["maat_body"], raw)
        self.assertEqual(graph["hermes_kann_addendum"], addendum)
        self.assertEqual(result["source_digest"], graph["maat_body_digest"])
        self.assertIsNone(result["checkpoint_receipt"])

    def test_materialization_without_binding_or_raw_body_does_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(registry.materialize_maat_body({"status": "pass"}, None))
            self.assertIsNone(registry.materialize_maat_body(None, {"work_id": "work-1", "graph_root": tmp}))
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_checkpoint_dispatcher_result_is_receipt_only(self):
        raw = {"schema": "harness.honcho.cps_cluster.v1", "C": {"shape": "bounded"}}
        checkpoint = {
            "repository": {"root": "/repo", "branch": "feature", "upstream": "origin/feature"},
            "scoped_paths": ["bounded.py"],
            "excluded_dirty_paths": ["dirty.py"],
            "closure_AC_ref": "AC:1",
            "CPS_refs": {"C": "C:1"},
            "prohibited_actions": ["git push"],
            "owner_approval": True,
            "commit_message": "Checkpoint\n\nCPS-Packet: packet:work-1@r1",
            "verification_command": None,
        }
        with tempfile.TemporaryDirectory() as tmp:
            result = registry.materialize_maat_body(
                raw,
                {"work_id": "work-1", "graph_root": tmp},
                semantic_provenance_binding=self.provenance(tmp),
                checkpoint_settings=checkpoint,
                dispatcher=lambda packet: {"status": "git_pending", "packet_id": packet["checkpoint_id"]},
            )
            graph = registry.load_json_or_yaml(Path(result["graph_ref"]))

        self.assertEqual(graph["maat_body"], raw)
        self.assertNotIn("status", result)
        self.assertEqual(result["checkpoint_receipt"]["status"], "git_pending")
        self.assertEqual(result["checkpoint_packet"]["work_id"], "work-1")
        self.assertTrue(result["checkpoint_packet"]["owner_approval"])
        self.assertEqual(result["checkpoint_packet"]["commit_message"], checkpoint["commit_message"])
        self.assertIsNone(result["checkpoint_packet"]["verification_command"])

    def test_preflight_materializes_only_explicit_runtime_binding_under_nonsemantic_key(self):
        provenance = self.provenance("unused")
        anchor = {"schema": "harness.honcho.cps_cluster.v1", "C": {"shape": "bounded"}}
        packet = {"cps_working_graph_runtime": {"work_id": "work-1", "graph_root": "/graphs"}, "semantic_anchor": anchor, "semantic_provenance_binding": provenance}
        reducer_result = {"status": "pass", "maat_body": anchor, "semantic_anchor": anchor, "semantic_provenance_binding": provenance}
        operational = {"graph_ref": "/graphs/work-1.yaml", "source_digest": "abc", "checkpoint_receipt": {"status": "git_pending"}}

        with patch.object(preflight, "materialize_maat_runtime_binding", return_value=operational) as materialize:
            result = preflight.materialize_preflight_working_graph(packet, reducer_result)

        materialize.assert_called_once_with(reducer_result["maat_body"], packet["cps_working_graph_runtime"], provenance)
        self.assertEqual(result, {"cps_working_graph_operational": operational})
        self.assertEqual(reducer_result["status"], "pass")

    def test_preflight_without_explicit_runtime_key_does_not_materialize(self):
        with patch.object(preflight, "materialize_maat_runtime_binding") as materialize:
            self.assertEqual(preflight.materialize_preflight_working_graph({}, {"maat_body": {"status": "pass"}}), {})
        materialize.assert_not_called()

    def test_reducer_hold_never_reaches_materializer(self):
        provenance = self.provenance("unused")
        anchor = {"schema": "harness.honcho.cps_cluster.v1", "C": {"shape": "bounded"}}
        packet = {
            "cps_working_graph_runtime": {"work_id": "work-1", "graph_root": "/graphs"},
            "semantic_anchor": anchor,
            "semantic_provenance_binding": provenance,
        }
        reducer_result = {
            "status": "hold",
            "maat_body": anchor,
            "semantic_anchor": anchor,
            "semantic_provenance_binding": provenance,
        }
        with patch.object(preflight, "materialize_maat_runtime_binding") as materialize:
            self.assertEqual(preflight.materialize_preflight_working_graph(packet, reducer_result), {})
        materialize.assert_not_called()

    def test_runtime_observation_is_automatically_recorded_with_artifact_refs(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, _, packet, files, events, receipt = self.runtime_observation(tmp)
            preflight.record_preflight_runtime_observation(packet, files, events, receipt)
            addendum = store.load("work-1")["hermes_kann_addendum"]

        self.assertEqual(addendum["observations"], [
            {key: events[0][key] for key in ("event_id", "event_type", "parent_event_id", "iteration", "phase")},
            {key: receipt[key] for key in ("producer_ref", "consumer_ref", "outcome", "normalized_result_hash")},
        ])
        self.assertEqual(addendum["source_refs"], [str(path) for path in files.values()])

    def test_runtime_observation_without_complete_binding_is_no_op(self):
        for binding in (None, {}, {"work_id": "work-1"}, {"graph_root": "/graphs"}):
            with self.subTest(binding=binding), patch.object(preflight.WorkingGraphRegistry, "update_addendum") as update:
                packet = {} if binding is None else {"cps_working_graph_runtime": binding}
                self.assertIsNone(preflight.record_preflight_runtime_observation(packet, {}, [], None))
                update.assert_not_called()

    def test_runtime_observation_preserves_existing_addendum_and_dedupes(self):
        existing_event = {
            "event_id": "evt-001", "event_type": "seed_created", "parent_event_id": None,
            "iteration": 0, "phase": "initial",
        }
        with tempfile.TemporaryDirectory() as tmp:
            prior = {
                "observations": [{"note": "preserve"}, existing_event],
                "source_refs": ["prior:1", str(Path(tmp) / "run" / "c_candidate_packet.json")],
            }
            store, _, packet, files, events, receipt = self.runtime_observation(tmp, addendum=prior)
            preflight.record_preflight_runtime_observation(packet, files, events, receipt)
            preflight.record_preflight_runtime_observation(packet, files, events, receipt)
            addendum = store.load("work-1")["hermes_kann_addendum"]

        self.assertEqual(addendum["observations"][0], {"note": "preserve"})
        self.assertEqual(addendum["observations"].count(existing_event), 1)
        self.assertEqual(len(addendum["observations"]), 3)
        self.assertEqual(addendum["source_refs"], ["prior:1", *[str(path) for path in files.values()]])

    def test_runtime_observation_preserves_body_digest_and_excludes_raw_semantics(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, body, packet, files, events, receipt = self.runtime_observation(tmp)
            before = store.load("work-1")
            preflight.record_preflight_runtime_observation(packet, files, events, receipt)
            after = store.load("work-1")

        self.assertEqual(after["maat_body"], body)
        self.assertEqual(after["maat_body_digest"], before["maat_body_digest"])
        encoded = json.dumps(after["hermes_kann_addendum"], ensure_ascii=False)
        for excluded in (
            "raw semantic body", "raw stdout", "selected_agents", "raw prompt", "semantic source body",
        ):
            self.assertNotIn(excluded, encoded)
        observation_keys = set().union(*(item.keys() for item in after["hermes_kann_addendum"]["observations"]))
        self.assertTrue({"event_payload", "normalized_result", "query", "C"}.isdisjoint(observation_keys))

    def test_runtime_observation_fails_closed_on_readback_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, _, packet, files, events, receipt = self.runtime_observation(tmp)
            original_load = store.load

            def changed_readback(work_id):
                graph = original_load(work_id)
                if graph["hermes_kann_addendum"]["observations"]:
                    graph["maat_body"] = {"status": "hold"}
                return graph

            with patch.object(preflight.WorkingGraphRegistry, "load", side_effect=changed_readback):
                with self.assertRaisesRegex(registry.RegistryError, "HOLD_WRITE_READBACK"):
                    preflight.record_preflight_runtime_observation(packet, files, events, receipt)

    def test_execution_receipt_transition_timeout_with_changes(self):
        receipt = {
            "parent_edge_ref": "C1.P2/S2",
            "status": "blocked",
            "changed_paths": ["artifact.py"],
            "partial_mutation_disposition": "reconcile",
            "return_to_node_ref": "C1.P2",
        }
        with tempfile.TemporaryDirectory() as tmp:
            store = registry.WorkingGraphRegistry(Path(tmp))
            body = {"schema": "harness.honcho.cps_cluster.v1", "C": {"shape": "bounded"}}
            store.create("work-1", body, semantic_provenance_binding=self.provenance(tmp))
            result = preflight.execution_receipt_transition("work-1", Path(tmp), receipt)
            reloaded = registry.load_json_or_yaml(Path(tmp) / "work-1.execution-receipts.json")
            persisted = reloaded["receipts"][-1]
            self.assertNotIn("consumer_transition_receipt", persisted)
            self.assertEqual(persisted["parent_edge_ref"], result["parent_edge_ref"])

        self.assertEqual(result["parent_edge_ref"], receipt["parent_edge_ref"])
        self.assertEqual(result["disposition"], "reconcile_or_return")


if __name__ == "__main__":
    unittest.main()
