import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

TOOLS = Path(__file__).resolve().parents[1] / ".harness" / "hermes" / "tools"
SCHEMAS = TOOLS.parent / "schemas"
sys.path.insert(0, str(TOOLS))

import cps_c1_retrieval_adapter as adapter


class C1RetrievalAdapterTests(unittest.TestCase):
    def compact_c(self):
        return {
            "request_ref": "request:1",
            "binding_ref": "binding:1",
            "C_shape": {
                "intent": "find prior CPS runtime route",
                "continuity": "follow_up",
                "boundary_hint": "linked",
                "cardinality_hint": "multiple",
                "source_current_state_need": "required",
            },
            "direct_source_refs": ["direct:1"],
        }

    def test_direct_candidates_outrank_advisory_recall(self):
        result = adapter.retrieve(
            self.compact_c(),
            lambda c_shape: {"matches": [{"ref": "recall:1", "score": 0.9}]},
            direct_reader=lambda ref: {"ref": ref, "current_state": "loaded"},
        )
        self.assertEqual(result["status"], "match")
        self.assertEqual([item["ref"] for item in result["source_candidates"]], ["direct:1", "recall:1"])
        self.assertEqual(result["source_candidates"][0]["source_kind"], "direct")
        self.assertEqual(result["source_candidates"][0]["current_state"], "loaded")
        self.assertEqual(result["source_candidates"][1]["source_kind"], "advisory_recall")

    def test_normalizes_no_match(self):
        compact_c = self.compact_c()
        compact_c["direct_source_refs"] = []
        result = adapter.retrieve(compact_c, lambda c_shape: {"matches": []})
        self.assertEqual(result["status"], "no_match")
        self.assertEqual(result["source_candidates"], [])

    def test_normalizes_unavailable_without_semantic_judgment(self):
        compact_c = self.compact_c()
        compact_c["direct_source_refs"] = []
        result = adapter.retrieve(compact_c, lambda c_shape: (_ for _ in ()).throw(OSError("offline")))
        self.assertEqual(result["status"], "unavailable")
        for semantic_key in ("route", "verdict", "selected_agents", "graph_revision", "hold"):
            self.assertNotIn(semantic_key, result)

    def test_advisory_exception_is_unavailable_while_preserving_direct_candidates(self):
        result = adapter.retrieve(
            self.compact_c(),
            lambda c_shape: (_ for _ in ()).throw(TimeoutError("offline")),
            direct_reader=lambda ref: {"ref": ref, "current_state": "loaded"},
        )
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual([candidate["ref"] for candidate in result["source_candidates"]], ["direct:1"])
        self.assertEqual(result["source_candidates"][0]["source_kind"], "direct")
        self.assertEqual(result["ref_metadata"]["advisory_error"], "TimeoutError: offline")

    def test_result_cannot_create_semantic_judgment(self):
        result = adapter.retrieve(self.compact_c(), lambda c_shape: {"matches": []})
        self.assertEqual(set(result), {"family", "request_ref", "binding_ref", "status", "source_candidates", "ref_metadata"})
        self.assertEqual(result["ref_metadata"]["direct_source_refs"], ["direct:1"])

    def test_schema_documents_encode_canonical_compact_c_and_advisory_result(self):
        compact_schema = json.loads((SCHEMAS / "compact-c.schema.yaml").read_text())
        result_schema = json.loads((SCHEMAS / "c1-retrieval-result.schema.yaml").read_text())
        self.assertEqual(set(compact_schema["required"]), adapter._REQUIRED)
        self.assertEqual(set(compact_schema["properties"]["C_shape"]["required"]), adapter._C_SHAPE_REQUIRED)
        for key, values in adapter._C_SHAPE_DOMAINS.items():
            self.assertEqual(set(compact_schema["properties"]["C_shape"]["properties"][key]["enum"]), values)
        self.assertFalse(compact_schema["additionalProperties"])
        observations = result_schema["properties"]["observations"]["items"]
        self.assertEqual(observations["properties"]["status"]["enum"], ["match", "no_match", "unavailable"])
        self.assertFalse(result_schema["additionalProperties"])
        for semantic_key in ("route", "verdict", "selected_agents", "graph_revision", "hold"):
            self.assertNotIn(semantic_key, observations["properties"])

    def test_rejects_invalid_compact_c(self):
        with self.assertRaises(adapter.RetrievalError):
            adapter.retrieve({"request_ref": "request:1"}, lambda c_shape: {})
        invalid_values = {
            "continuity": "continuation",
            "boundary_hint": ["linked"],
            "cardinality_hint": "one_or_more",
            "source_current_state_need": True,
        }
        for key, invalid in invalid_values.items():
            compact_c = self.compact_c()
            compact_c["C_shape"][key] = invalid
            with self.subTest(key=key), self.assertRaises(adapter.RetrievalError):
                adapter.retrieve(compact_c, lambda c_shape: {"matches": []})

    def test_rejects_non_string_or_empty_intent(self):
        for intent in ("", [], 1, None):
            compact_c = self.compact_c()
            compact_c["C_shape"]["intent"] = intent
            with self.subTest(intent=intent), self.assertRaises(adapter.RetrievalError):
                adapter.retrieve(compact_c, lambda c_shape: {"matches": []})
        compact_schema = json.loads((SCHEMAS / "compact-c.schema.yaml").read_text())
        self.assertEqual(compact_schema["properties"]["C_shape"]["properties"]["intent"], {"type": "string", "minLength": 1})

    def test_observation_bindings_normalize_all_source_outcomes(self):
        bindings = {
            "honcho": lambda ref, query: {"matches": [{"content": "honcho hit", "source_ref": "honcho:1"}]},
            "gbrain": lambda ref, query: {"matches": []},
            "harness_brain": lambda ref, query: (_ for _ in ()).throw(OSError("offline")),
        }
        result = adapter.observe_sources(
            {}, advisory_bindings=bindings, query="C1", timestamp="2026-07-13T00:00:00Z"
        )
        self.assertEqual([item["source_kind"] for item in result["observations"]], ["honcho", "gbrain", "harness_brain"])
        self.assertEqual([item["status"] for item in result["observations"]], ["match", "no_match", "unavailable"])
        evidence = result["observations"][0]["evidence"]
        self.assertEqual(set(evidence), {"count", "timestamp", "digest"})
        self.assertEqual(evidence["count"], 1)
        self.assertEqual(len(evidence["digest"]), 64)

    def test_direct_refs_are_read_once_without_implicit_advisory_calls(self):
        calls = []
        def reader(ref, query):
            calls.append(ref)
            return {"matches": [{"content": ref or "advisory", "source_ref": ref or "honcho:recall"}]}
        result = adapter.observe_sources(
            {"honcho": reader, "gbrain": reader, "harness_brain": reader},
            direct_refs=[
                {"source_kind": "gbrain", "source_ref": "gbrain:explicit"},
                {"source_kind": "honcho", "source_ref": "honcho:explicit"},
            ],
            query="recall",
            timestamp="2026-07-13T00:00:00Z",
        )
        self.assertEqual(calls, ["gbrain:explicit", "honcho:explicit"])
        self.assertEqual(
            [item["source_ref"] for item in result["observations"]],
            ["gbrain:explicit", "honcho:explicit"],
        )

    def test_explicit_advisory_bindings_run_after_direct_refs(self):
        calls = []
        def direct_reader(ref, query):
            calls.append(("direct", ref))
            return {"matches": [{"content": ref, "source_ref": ref}]}
        def advisory_reader(ref, query):
            calls.append(("advisory", ref))
            return {"matches": [{"content": "advisory", "source_ref": "honcho:recall"}]}
        result = adapter.observe_sources(
            {"gbrain": direct_reader},
            direct_refs=[{"source_kind": "gbrain", "source_ref": "gbrain:explicit"}],
            advisory_bindings={"honcho": advisory_reader},
            query="recall",
            timestamp="2026-07-13T00:00:00Z",
        )
        self.assertEqual(calls, [("direct", "gbrain:explicit"), ("advisory", None)])
        self.assertEqual([item["source_kind"] for item in result["observations"]], ["gbrain", "honcho"])

    def test_each_source_handles_positive_no_match_unavailable_and_malformed(self):
        outcomes = (
            ({"matches": [{"content": "hit"}]}, "match"),
            ({"matches": []}, "no_match"),
            (OSError("offline"), "unavailable"),
            ({"unexpected": "shape"}, "unavailable"),
        )
        for source_kind in adapter.SOURCE_KINDS:
            for value, expected in outcomes:
                def reader(ref, query, value=value):
                    if isinstance(value, Exception):
                        raise value
                    return value
                with self.subTest(source_kind=source_kind, expected=expected):
                    result = adapter.observe_sources(
                        {},
                        advisory_bindings={source_kind: reader},
                        query="q",
                        timestamp="2026-07-13T00:00:00Z",
                    )
                    self.assertEqual(result["observations"][0]["status"], expected)

    def test_observations_exclude_every_prohibited_semantic_field_even_nested(self):
        prohibited = {
            "route", "selected_agents", "actor_binding", "verdict", "hold",
            "graph_revision", "mutation", "task_AC", "closure",
            "learning_candidate", "promotion",
        }
        payload = {"matches": [{"content": "safe", **{key: "forbidden" for key in prohibited}}]}
        result = adapter.observe_sources(
            {},
            advisory_bindings={"honcho": lambda ref, query: payload},
            timestamp="2026-07-13T00:00:00Z",
        )
        def keys(value):
            if isinstance(value, dict):
                return set(value).union(*(keys(item) for item in value.values()))
            if isinstance(value, list):
                return set().union(*(keys(item) for item in value))
            return set()
        self.assertFalse(keys(result) & prohibited)
        self.assertEqual(set(result), {"observations"})
        self.assertEqual(set(result["observations"][0]), {"source_kind", "status", "source_ref", "evidence"})

    def test_rejects_undeclared_source_kind(self):
        with self.assertRaises(adapter.RetrievalError):
            adapter.observe_sources({"other": lambda ref, query: {"matches": []}})
        with self.assertRaises(adapter.RetrievalError):
            adapter.observe_sources(
                {"honcho": lambda ref, query: {"matches": []}},
                direct_refs=[{"source_kind": "other", "source_ref": "x"}],
            )

    def test_observation_schema_is_closed_and_declares_exact_sources(self):
        schema = json.loads((SCHEMAS / "c1-retrieval-result.schema.yaml").read_text())
        observation = schema["properties"]["observations"]["items"]
        self.assertEqual(observation["properties"]["source_kind"]["enum"], list(adapter.SOURCE_KINDS))
        self.assertFalse(schema["additionalProperties"])
        self.assertFalse(observation["additionalProperties"])
        self.assertEqual(set(observation["required"]), {"source_kind", "status", "source_ref", "evidence"})

    def test_configured_live_bindings_have_exact_adapter_owned_sources(self):
        bindings = adapter.configured_live_bindings(Path("/gbrain"), Path("/harness-brain"), subprocess_runner=lambda *args, **kwargs: None)
        self.assertEqual(set(bindings), {"honcho", "gbrain", "harness_brain"})
        self.assertEqual(bindings["gbrain"], Path("/gbrain"))
        self.assertEqual(bindings["harness_brain"], Path("/harness-brain"))

    def test_configured_honcho_binding_normalizes_success_without_raw_output(self):
        calls = []
        class Completed:
            returncode = 0
            stdout = "Honcho available"
            stderr = "secret diagnostic"
        def runner(command, **kwargs):
            calls.append((command, kwargs))
            return Completed()
        bindings = adapter.configured_live_bindings(
            Path("/gbrain"), Path("/harness-brain"),
            honcho_command=("custom-hermes", "honcho", "status"), subprocess_runner=runner,
        )
        result = adapter.observe_sources(
            {}, advisory_bindings={"honcho": bindings["honcho"]}, timestamp="2026-07-13T00:00:00Z"
        )
        self.assertEqual(result["observations"][0]["status"], "match")
        self.assertEqual(set(result["observations"][0]["evidence"]), {"count", "timestamp", "digest"})
        self.assertEqual(calls, [(("custom-hermes", "honcho", "status"), {"capture_output": True, "text": True, "check": False, "timeout": 10})])
        self.assertNotIn("Honcho available", json.dumps(result))
        self.assertNotIn("secret diagnostic", json.dumps(result))

    def test_configured_honcho_binding_normalizes_nonzero_as_unavailable(self):
        class Completed:
            returncode = 2
            stdout = "raw failure"
            stderr = "secret diagnostic"
        bindings = adapter.configured_live_bindings(Path("/gbrain"), Path("/harness-brain"), subprocess_runner=lambda *args, **kwargs: Completed())
        result = adapter.observe_sources(
            {}, advisory_bindings={"honcho": bindings["honcho"]}, timestamp="2026-07-13T00:00:00Z"
        )
        self.assertEqual(result["observations"][0]["status"], "unavailable")
        self.assertNotIn("raw failure", json.dumps(result))
        self.assertNotIn("secret diagnostic", json.dumps(result))

    def test_configured_honcho_binding_normalizes_timeout_as_unavailable(self):
        def runner(*args, **kwargs):
            raise TimeoutError("timed out with raw command data")
        bindings = adapter.configured_live_bindings(Path("/gbrain"), Path("/harness-brain"), subprocess_runner=runner)
        result = adapter.observe_sources(
            {}, advisory_bindings={"honcho": bindings["honcho"]}, timestamp="2026-07-13T00:00:00Z"
        )
        self.assertEqual(result["observations"][0]["status"], "unavailable")
        self.assertNotIn("timed out with raw command data", json.dumps(result))

    def test_gbrain_search_binding_is_bounded_and_hides_raw_fields(self):
        calls = []

        def reader_factory(**kwargs):
            calls.append(("factory", kwargs))

            def reader(query, args):
                calls.append(("reader", query, args))
                return {
                    "query": query,
                    "stdout": "route: forbidden search content",
                    "stderr": "secret diagnostic",
                    "returncode": 0,
                }

            return reader

        result = adapter.retrieve_gbrain_search_source(
            query="C1 prior context",
            reader_context={"request_ref": "C:gbrain-adapter"},
            source_revision="index-4",
            timeout=3.0,
            reader_factory=reader_factory,
        )

        self.assertEqual(result["status"], "match")
        self.assertEqual(result["evidence"]["record_count"], 1)
        self.assertEqual(len(result["evidence"]["content_digest"]), 64)
        self.assertEqual(
            result["readback_metadata"],
            {
                "producer_ref": adapter._GBRAIN_PRODUCER,
                "source_identity": adapter._GBRAIN_SOURCE_IDENTITY,
                "source_revision": "index-4",
            },
        )
        self.assertEqual(calls, [("factory", {"timeout": 3.0}), ("reader", "C1 prior context", None)])
        serialized = json.dumps(result)
        for raw_value in ("C1 prior context", "route: forbidden search content", "secret diagnostic"):
            self.assertNotIn(raw_value, serialized)

    def test_gbrain_no_match_has_zero_record_receipt(self):
        result = adapter.retrieve_gbrain_search_source(
            query="no prior context",
            reader_context={"request_ref": "C:gbrain-no-match"},
            reader_factory=lambda **kwargs: lambda query, args: {
                "query": query,
                "stdout": "  \n",
                "stderr": "",
                "returncode": 0,
            },
        )
        self.assertEqual(result["status"], "no_match")
        self.assertEqual(result["evidence"], {"record_count": 0})

    def test_gbrain_failures_return_explicit_unavailable_source_receipts(self):
        cases = (
            (
                lambda **kwargs: (_ for _ in ()).throw(OSError("raw factory failure")),
                "gbrain-search-reader:command_error",
            ),
            (
                lambda **kwargs: lambda query, args: (_ for _ in ()).throw(TimeoutError("raw command timeout")),
                "gbrain-search-reader:command_error",
            ),
            (
                lambda **kwargs: lambda query, args: {
                    "query": query,
                    "stdout": "raw nonzero output",
                    "stderr": "raw nonzero error",
                    "returncode": 2,
                },
                "gbrain-search-reader:nonzero_exit",
            ),
            (
                lambda **kwargs: lambda query, args: {"stdout": "raw malformed output"},
                "gbrain-search-reader:malformed_output",
            ),
        )
        for reader_factory, receipt in cases:
            with self.subTest(receipt=receipt):
                result = adapter.retrieve_gbrain_search_source(
                    query="C1 search",
                    reader_context={"request_ref": "C:gbrain-unavailable"},
                    reader_factory=reader_factory,
                )
                self.assertEqual(result["status"], "unavailable")
                self.assertEqual(result["evidence"], {"record_count": 0, "source_receipt": receipt})
                serialized = json.dumps(result)
                for raw_value in (
                    "C1 search", "raw factory failure", "raw command timeout", "raw nonzero output",
                    "raw nonzero error", "raw malformed output",
                ):
                    self.assertNotIn(raw_value, serialized)

    def test_gbrain_adapter_excludes_control_and_lifecycle_fields(self):
        result = adapter.retrieve_gbrain_search_source(
            query="C1 search",
            reader_context={"request_ref": "C:gbrain-no-semantics"},
            reader_factory=lambda **kwargs: lambda query, args: {
                "query": query,
                "stdout": "route selected_agents verdict hold graph mutation closure learning",
                "stderr": "",
                "returncode": 0,
            },
        )
        prohibited = {
            "route", "selected_agents", "verdict", "hold", "graph", "mutation",
            "closure", "learning",
        }

        def keys(value):
            if isinstance(value, dict):
                return set(value).union(*(keys(item) for item in value.values()))
            if isinstance(value, list):
                return set().union(*(keys(item) for item in value))
            return set()

        self.assertEqual(set(result), {"family", "source_kind", "status", "evidence", "readback_metadata"})
        self.assertFalse(keys(result) & prohibited)
        self.assertNotIn("route selected_agents verdict hold graph mutation closure learning", json.dumps(result))

    def test_explicit_harness_brain_source_flows_through_advisory_readback_only(self):
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir) / "harness-brain"
            source = root / "projects" / "decision.md"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"bounded advisory source")
            before = source.read_bytes()

            result = adapter.retrieve_harness_brain_source(
                "projects/decision.md",
                root,
                query="C1 source readback",
                reader_context={"request_ref": "C:explicit-harness-brain"},
                source_revision="r3",
            )

            self.assertEqual(result["status"], "match")
            self.assertEqual(result["evidence"]["record_count"], 1)
            self.assertEqual(len(result["evidence"]["content_digest"]), 64)
            self.assertEqual(
                result["readback_metadata"],
                {
                    "producer_ref": adapter._HARNESS_BRAIN_PRODUCER,
                    "source_identity": str(source.resolve()),
                    "source_revision": "r3",
                    "reader_context": {"request_ref": "C:explicit-harness-brain"},
                },
            )
            self.assertNotIn("bounded advisory source", json.dumps(result))
            self.assertEqual(source.read_bytes(), before)

    def test_harness_brain_unavailable_and_malformed_results_are_non_pass_diagnostics(self):
        cases = (
            (
                lambda *args, **kwargs: {
                    "status": "unavailable",
                    "source_ref": "projects/missing.md",
                    "source_identity": "projects/missing.md",
                    "readback": None,
                    "reason": "absent",
                },
                "unavailable",
                "absent",
            ),
            (lambda *args, **kwargs: {"status": "available"}, "query_error", "malformed_reader_result"),
            (lambda *args, **kwargs: (_ for _ in ()).throw(OSError("offline secret")), "unavailable", "unavailable"),
        )
        for source_reader, expected_status, expected_diagnostic in cases:
            with self.subTest(status=expected_status, diagnostic=expected_diagnostic):
                result = adapter.retrieve_harness_brain_source(
                    "projects/missing.md",
                    Path("/not-read-by-test"),
                    query="C1 source readback",
                    reader_context={"request_ref": "C:harness-brain-diagnostic"},
                    source_reader=source_reader,
                )
                self.assertEqual(result["status"], expected_status)
                self.assertNotEqual(result["status"].casefold(), "pass")
                self.assertEqual(result["evidence"], {"record_count": 0, "source_receipt": expected_diagnostic})
                self.assertNotIn("offline secret", json.dumps(result))

    def test_harness_brain_adapter_edge_excludes_cps_semantics(self):
        result = adapter.retrieve_harness_brain_source(
            "projects/decision.md",
            Path("/not-read-by-test"),
            query="C1 source readback",
            reader_context={"request_ref": "C:no-semantics"},
            source_reader=lambda *args, **kwargs: {
                "status": "available",
                "source_ref": "projects/decision.md",
                "source_identity": "harness-brain:decision",
                "readback": {"content": b"route: forbidden", "byte_count": 16},
            },
        )
        prohibited = {"route", "verdict", "selected_agents", "graph_revision", "hold", "mutation", "task_AC"}

        def keys(value):
            if isinstance(value, dict):
                return set(value).union(*(keys(item) for item in value.values()))
            if isinstance(value, list):
                return set().union(*(keys(item) for item in value))
            return set()

        self.assertFalse(keys(result) & prohibited)
        self.assertNotIn("route: forbidden", json.dumps(result))

    def test_configured_honcho_session_flows_through_advisory_contract_without_raw_reads(self):
        class Config:
            enabled = True
            workspace_id = "workspace-7"
            host = "hermes"

            def resolve_session_name(self):
                return "resolved-session"

        class Session:
            honcho_session_id = "sdk-session-8"
            user_peer_id = "user-9"
            assistant_peer_id = "assistant-10"

        class Manager:
            def __init__(self):
                self.calls = []

            def get_or_create(self, key):
                self.calls.append(("get_or_create", key))
                return Session()

            def get_session_context(self, key, peer):
                self.calls.append(("get_session_context", key, peer))
                return {"summary": "raw configured context"}

            def search_context(self, key, query, max_tokens, peer):
                self.calls.append(("search_context", key, query, max_tokens, peer))
                return "raw semantic search"

        manager = Manager()

        def binding_factory(session_key):
            return adapter.configured_honcho_session_binding(
                session_key,
                config_loader=Config,
                client_factory=lambda config: object(),
                manager_factory=lambda **kwargs: manager,
            )

        result = adapter.retrieve_honcho_session_source(
            query="C1 prior context",
            reader_context={"request_ref": "C:honcho-adapter"},
            session_key="packet-session",
            binding_factory=binding_factory,
        )

        self.assertEqual(result["status"], "available")
        self.assertEqual(result["evidence"]["record_count"], 2)
        self.assertEqual(len(result["evidence"]["content_digest"]), 64)
        self.assertEqual(
            result["readback_metadata"],
            {
                "producer_ref": "honcho-sdk:workspace-7:hermes",
                "source_identity": "honcho-sdk-session:sdk-session-8",
                "source_revision": None,
            },
        )
        self.assertEqual(
            manager.calls,
            [
                ("get_or_create", "packet-session"),
                ("get_session_context", "packet-session", "user"),
                ("search_context", "packet-session", "C1 prior context", 256, "user"),
            ],
        )
        self.assertNotIn("raw configured context", json.dumps(result))
        self.assertNotIn("raw semantic search", json.dumps(result))

    def test_honcho_disabled_unresolved_and_sdk_failures_are_unavailable(self):
        cases = (
            (False, lambda: "disabled-session", lambda config: object(), "config_disabled"),
            (True, lambda: "", lambda config: object(), "session_key_absent"),
            (
                True,
                lambda: "failed-session",
                lambda config: (_ for _ in ()).throw(RuntimeError("raw sdk failure")),
                "sdk_or_session_failure",
            ),
        )
        for enabled, resolve_session_name, client_factory, receipt in cases:
            config = SimpleNamespace(enabled=enabled, resolve_session_name=resolve_session_name)

            def binding_factory(session_key, config=config, client_factory=client_factory):
                return adapter.configured_honcho_session_binding(
                    session_key,
                    config_loader=lambda: config,
                    client_factory=client_factory,
                    manager_factory=lambda **kwargs: self.fail("manager must not be used"),
                )

            with self.subTest(receipt=receipt):
                result = adapter.retrieve_honcho_session_source(
                    query="C1 prior context",
                    reader_context={"request_ref": "C:honcho-unavailable"},
                    binding_factory=binding_factory,
                )
                self.assertEqual(result["status"], "unavailable")
                self.assertNotIn(result["status"], {"pass", "no_match"})
                self.assertEqual(
                    result["evidence"],
                    {"record_count": 0, "source_receipt": "honcho-session-reader:" + receipt},
                )
                self.assertLessEqual(len(result["evidence"]["source_receipt"]), 256)
                self.assertNotIn("raw sdk failure", json.dumps(result))

    def test_honcho_read_failure_is_unavailable_and_output_is_advisory_only(self):
        class Config:
            enabled = True
            workspace_id = "workspace"
            host = "hermes"

            def resolve_session_name(self):
                return "read-session"

        class Manager:
            def get_or_create(self, key):
                return type("Session", (), {"honcho_session_id": "session-1"})()

            def get_session_context(self, key, peer):
                raise RuntimeError("route: forbidden raw failure")

            def search_context(self, *args, **kwargs):
                raise AssertionError("search must not run after context failure")

        manager = Manager()
        result = adapter.retrieve_honcho_session_source(
            query="C1 prior context",
            reader_context={"request_ref": "C:honcho-read-failure"},
            binding_factory=lambda session_key: adapter.configured_honcho_session_binding(
                session_key,
                config_loader=Config,
                client_factory=lambda config: object(),
                manager_factory=lambda **kwargs: manager,
            ),
        )
        prohibited = {
            "route", "selected_agents", "verdict", "hold", "graph", "mutation",
            "closure", "learning",
        }

        def keys(value):
            if isinstance(value, dict):
                return set(value).union(*(keys(item) for item in value.values()))
            if isinstance(value, list):
                return set().union(*(keys(item) for item in value))
            return set()

        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(
            result["evidence"],
            {"record_count": 0, "source_receipt": "honcho-session-reader:read_failure"},
        )
        self.assertEqual(set(result), {"family", "source_kind", "status", "evidence", "readback_metadata"})
        self.assertFalse(keys(result) & prohibited)
        self.assertNotIn("route: forbidden raw failure", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
