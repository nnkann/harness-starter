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
            lambda c_shape: {"matches": [{
                "ref": adapter._CANONICAL_CPS_SOURCE_REF,
                "source": "harness_brain",
                "score": 0.9,
            }]},
            direct_reader=lambda ref: {"ref": ref, "current_state": "loaded"},
        )
        self.assertEqual(result["status"], "match")
        self.assertEqual(
            [item["ref"] for item in result["source_candidates"]],
            ["direct:1", adapter._CANONICAL_CPS_SOURCE_REF],
        )
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

    def test_relevant_concrete_finding_short_circuits_fallback_with_one_clue(self):
        calls = []
        result = adapter.retrieve(
            self.compact_c(),
            lambda c_shape: calls.append(c_shape) or {"matches": []},
            direct_reader=lambda ref: {
                "ref": ref,
                "summary": "Prior CPS runtime route uses the project source boundary. Extra sentence is excluded.",
                "source_receipt": "receipt:direct:1",
            },
        )

        self.assertEqual(calls, [])
        clues = [item["vector_clue"] for item in result["source_candidates"] if "vector_clue" in item]
        self.assertEqual(clues, [
            "Prior CPS runtime route uses the project source boundary."
        ])

    def test_direct_phase_reads_only_first_explicit_source_before_fallback(self):
        compact_c = self.compact_c()
        compact_c["direct_source_refs"] = ["direct:1", "direct:2"]
        reads = []
        fallback_calls = []

        result = adapter.retrieve(
            compact_c,
            lambda c_shape: fallback_calls.append(c_shape) or {"matches": []},
            direct_reader=lambda ref: reads.append(ref) or {
                "ref": ref,
                "summary": "A recent message discusses lunch plans.",
                "source_receipt": "receipt:" + ref,
            },
        )

        self.assertEqual(reads, ["direct:1"])
        self.assertEqual(len(fallback_calls), 1)
        self.assertEqual([item["ref"] for item in result["source_candidates"]], ["direct:1"])

    def test_relevant_direct_without_valid_vector_clue_is_omitted_and_falls_back_once(self):
        fallback_calls = []
        overlong_finding = "CPS runtime route " + "x" * 260

        result = adapter.retrieve(
            self.compact_c(),
            lambda c_shape: fallback_calls.append(c_shape) or {"matches": [{
                "ref": adapter._CANONICAL_CPS_SOURCE_REF,
                "source": "harness_brain",
                "summary": "The CPS runtime route retains the canonical project boundary.",
                "source_receipt": "receipt:cps:canonical",
            }]},
            direct_reader=lambda ref: {
                "ref": ref,
                "summary": overlong_finding,
                "source_receipt": "receipt:" + ref,
            },
        )

        self.assertEqual(len(fallback_calls), 1)
        self.assertEqual(
            [item["ref"] for item in result["source_candidates"]],
            [adapter._CANONICAL_CPS_SOURCE_REF],
        )
        self.assertEqual(
            result["source_candidates"][0]["vector_clue"],
            "The CPS runtime route retains the canonical project boundary.",
        )

    def test_irrelevant_concrete_finding_calls_fallback_once_and_clues_never_coexist(self):
        calls = []
        result = adapter.retrieve(
            self.compact_c(),
            lambda c_shape: calls.append(c_shape) or {"matches": [{
                "ref": adapter._CANONICAL_CPS_SOURCE_REF,
                "source": "harness_brain",
                "summary": "The CPS runtime route retains the project scope boundary.",
                "source_receipt": "receipt:cps:canonical",
            }]},
            direct_reader=lambda ref: {
                "ref": ref,
                "summary": "A recent message discusses lunch plans.",
                "source_receipt": "receipt:direct:1",
            },
        )

        self.assertEqual(len(calls), 1)
        clues = [item["vector_clue"] for item in result["source_candidates"] if "vector_clue" in item]
        self.assertEqual(clues, [
            "The CPS runtime route retains the project scope boundary."
        ])

    def test_c_shape_overlap_without_intent_overlap_emits_no_clue(self):
        result = adapter.retrieve(
            self.compact_c(),
            lambda c_shape: {"matches": []},
            direct_reader=lambda ref: {
                "ref": ref,
                "summary": "Linked multiple records provide required current state.",
                "source_receipt": "receipt:direct:1",
            },
        )

        self.assertFalse(any("vector_clue" in item for item in result["source_candidates"]))

    def test_fallback_accepts_only_the_canonical_cps_source(self):
        matches = [
            {
                "ref": "honcho:memory",
                "source": "honcho",
                "summary": "The CPS runtime route is remembered.",
                "source_receipt": "receipt:honcho",
            },
            {
                "ref": "fixture/projects/harness-starter/decisions/cps-equation-ssot.md",
                "source": "harness_brain",
                "summary": "The CPS runtime route is in a fixture.",
                "source_receipt": "receipt:fixture",
            },
            {
                "ref": "projects/harness-starter/memory/runtime.md",
                "source": "harness_brain",
                "summary": "The CPS runtime route is in noncanonical memory.",
                "source_receipt": "receipt:memory",
            },
            {
                "ref": adapter._CANONICAL_CPS_SOURCE_REF,
                "source": "harness_brain",
                "summary": "The CPS runtime route is in the canonical packet.",
                "source_receipt": "receipt:canonical",
            },
        ]

        result = adapter.retrieve(
            {**self.compact_c(), "direct_source_refs": []},
            lambda c_shape: {"matches": matches},
        )

        self.assertEqual(
            [candidate["ref"] for candidate in result["source_candidates"]],
            [adapter._CANONICAL_CPS_SOURCE_REF],
        )
        self.assertEqual(
            result["source_candidates"][0]["vector_clue"],
            "The CPS runtime route is in the canonical packet.",
        )

    def test_no_relevant_direct_or_fallback_finding_emits_no_clue(self):
        calls = []
        result = adapter.retrieve(
            self.compact_c(),
            lambda c_shape: calls.append(c_shape) or {"matches": []},
            direct_reader=lambda ref: {
                "ref": ref,
                "summary": "A recent message discusses lunch plans.",
                "source_receipt": "receipt:direct:1",
            },
        )

        self.assertEqual(len(calls), 1)
        self.assertFalse(any("vector_clue" in item for item in result["source_candidates"]))

    def test_direct_hit_stops_remaining_reads_and_metadata_sources_cannot_emit_clues(self):
        compact_c = self.compact_c()
        compact_c["direct_source_refs"] = ["direct:1", "direct:2"]
        reads = []

        result = adapter.retrieve(
            compact_c,
            lambda c_shape: self.fail("relevant first direct read must suppress fallback"),
            direct_reader=lambda ref: reads.append(ref) or {
                "ref": ref,
                "summary": "The CPS runtime route retains the project boundary.",
                "source_receipt": "receipt:" + ref,
            },
        )
        self.assertEqual(reads, ["direct:1"])
        self.assertEqual(sum("vector_clue" in item for item in result["source_candidates"]), 1)

        for source in ("harness_brain", "gbrain"):
            with self.subTest(source=source):
                fallback_calls = []
                result = adapter.retrieve(
                    self.compact_c(),
                    lambda c_shape: fallback_calls.append(c_shape) or {"matches": []},
                    direct_reader=lambda ref, source=source: {
                        "ref": ref,
                        "source": source,
                        "summary": "The CPS runtime route retains the project boundary.",
                        "source_receipt": "receipt:" + source,
                    },
                )
                self.assertEqual(len(fallback_calls), 1)
                self.assertFalse(any("vector_clue" in item for item in result["source_candidates"]))

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

    def test_canonical_cps_candidate_rejects_metadata_and_accepts_source_finding_sentence(self):
        metadata = b"""---
purpose: CPS runtime C-boundary uses the project focus boundary.
---
# CPS runtime C-boundary uses the project focus boundary.
- purpose: CPS runtime C-boundary uses the project focus boundary.
"""
        finding = b"""---
purpose: metadata only
---
# Decision
- CPS retrieval uses the bound-project C-boundary for gateway ingress.
"""

        def readback(content):
            return lambda *args, **kwargs: {
                "status": "available",
                "source_ref": adapter._CANONICAL_CPS_SOURCE_REF,
                "source_identity": "harness-brain:canonical-cps",
                "readback": {"content": content, "byte_count": len(content)},
            }

        rejected = adapter.retrieve_harness_brain_source(
            adapter._CANONICAL_CPS_SOURCE_REF,
            Path("/not-read-by-test"),
            query="CPS retrieval gateway C-boundary",
            reader_context={"request_ref": "C:metadata-rejected"},
            source_reader=readback(metadata),
        )
        accepted = adapter.retrieve_harness_brain_source(
            adapter._CANONICAL_CPS_SOURCE_REF,
            Path("/not-read-by-test"),
            query="CPS retrieval gateway C-boundary",
            reader_context={"request_ref": "C:decision-finding"},
            source_reader=readback(finding),
        )

        self.assertNotIn("candidate", rejected)
        self.assertEqual(
            accepted["candidate"]["clue"],
            "CPS retrieval uses the bound-project C-boundary for gateway ingress.",
        )

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
        calls = []

        class Config:
            enabled = True
            workspace_id = "workspace-7"
            host = "hermes"

            def resolve_session_name(self, gateway_session_key=None):
                calls.append(("resolve_session_name", gateway_session_key))
                return "packet-session"

        class HTTP:
            def post(self, route, *, body, query):
                calls.append(("lookup_session", body, query))
                return {"items": [{"id": "packet-session"}]}

        class Client:
            workspace_id = "workspace-7"
            _http = HTTP()

            def search(self, query, **kwargs):
                calls.append(("semantic_search", query, kwargs))
                return [SimpleNamespace(
                    content="C1 prior context uses bounded semantic search.",
                    session_id="source-session",
                    id="message-1",
                )]

            def __getattr__(self, name):
                if name in {"session", "peer", "add", "create", "upsert", "save", "flush"}:
                    raise AssertionError("write-capable SDK path must not run")
                raise AttributeError(name)

        class Manager:
            def _sanitize_id(self, key):
                return key


        manager = Manager()
        client = Client()

        def binding_factory(session_key):
            return adapter.configured_honcho_session_binding(
                session_key,
                config_loader=Config,
                client_factory=lambda config: client,
                manager_factory=lambda **kwargs: manager,
            )

        result = adapter.retrieve_honcho_session_source(
            query="C1 prior context",
            reader_context={"request_ref": "C:honcho-adapter"},
            session_key="packet-session",
            binding_factory=binding_factory,
        )

        self.assertEqual(result["status"], "available")
        self.assertEqual(result["evidence"]["record_count"], 1)
        self.assertEqual(len(result["evidence"]["content_digest"]), 64)
        self.assertEqual(result["candidate"]["clue"], "C1 prior context uses bounded semantic search.")
        self.assertEqual(result["candidate"]["source_ref"], "honcho-sdk-semantic-peer:user")
        self.assertEqual(result["candidate"]["source_receipt"], result["evidence"]["source_receipt"])
        self.assertEqual(result["candidate"]["lifecycle"], "candidate")
        self.assertRegex(result["candidate"]["observed_at"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
        self.assertLessEqual(len(result["candidate"]["clue"]), 256)
        self.assertEqual(
            result["readback_metadata"],
            {
                "producer_ref": "honcho-sdk:workspace-7:hermes",
                "source_identity": "honcho-sdk-semantic-peer:user",
                "source_revision": None,
            },
        )
        self.assertEqual(
            calls,
            [
                ("resolve_session_name", "packet-session"),
                ("lookup_session", {"filters": {"id": "packet-session"}}, {"page": 1, "size": 1}),
                ("semantic_search", "C1 prior context", {"filters": {"peer_perspective": "user"}, "limit": 3}),
            ],
        )
        self.assertEqual(
            sum(call[0] in {"get_or_create", "create", "upsert", "add", "save", "flush"} for call in calls),
            0,
        )
        self.assertEqual(json.dumps(result).count("C1 prior context uses bounded semantic search."), 1)

    def test_honcho_dotenv_load_precedes_config_resolution(self):
        calls = []
        config = SimpleNamespace(enabled=False, resolve_session_name=lambda **_: "dotenv-session")

        def env_loader(**kwargs):
            calls.append(("dotenv", kwargs))

        def config_loader():
            calls.append(("config", {}))
            self.assertEqual(calls[0][0], "dotenv")
            return config

        binding = adapter.configured_honcho_session_binding(
            "dotenv-session",
            config_loader=config_loader,
            client_factory=lambda _: self.fail("disabled config must not construct a client"),
            manager_factory=lambda **_: self.fail("disabled config must not construct a manager"),
            env_loader=env_loader,
        )
        result = binding.reader(SimpleNamespace(query="q", reader_context={"request_ref": "dotenv-order"}))

        self.assertEqual(result["state"], "unavailable")
        self.assertEqual(result["evidence"]["source_receipt"], "honcho-session-reader:config_disabled")
        self.assertEqual(calls[0][0], "dotenv")
        self.assertEqual(calls[1][0], "config")
        self.assertEqual(calls[0][1]["project_env"].name, ".env")

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

            def resolve_session_name(self, gateway_session_key=None):
                return "read-session"

        class Manager:
            def _sanitize_id(self, key):
                return key

        manager = Manager()
        client = SimpleNamespace(
            workspace_id="workspace",
            _http=SimpleNamespace(post=lambda *args, **kwargs: {"items": [{"id": "read-session"}]}),
            search=lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("route: forbidden raw failure")),
        )
        result = adapter.retrieve_honcho_session_source(
            query="C1 prior context",
            reader_context={"request_ref": "C:honcho-read-failure"},
            binding_factory=lambda session_key: adapter.configured_honcho_session_binding(
                session_key,
                config_loader=Config,
                client_factory=lambda config: client,
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

    def test_honcho_session_absent_is_unavailable_without_write_calls(self):
        calls = []
        config = SimpleNamespace(
            enabled=True,
            workspace_id="workspace",
            host="hermes",
            resolve_session_name=lambda: "absent-session",
        )

        class HTTP:
            def post(self, route, *, body, query):
                calls.append(("lookup_session", body, query))
                return {"items": []}

        class Manager:
            def _sanitize_id(self, key):
                return key

            def __getattr__(self, name):
                if name in {"get_or_create", "create", "upsert", "add", "save", "flush"}:
                    raise AssertionError("write-capable manager path must not run")
                raise AttributeError(name)

        client = SimpleNamespace(workspace_id="workspace", _http=HTTP())
        result = adapter.retrieve_honcho_session_source(
            query="C1 prior context",
            reader_context={"request_ref": "C:honcho-absent"},
            binding_factory=lambda session_key: adapter.configured_honcho_session_binding(
                session_key,
                config_loader=lambda: config,
                client_factory=lambda loaded: client,
                manager_factory=lambda **kwargs: Manager(),
            ),
        )

        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(
            result["evidence"],
            {"record_count": 0, "source_receipt": "honcho-session-reader:session_absent"},
        )
        self.assertEqual(calls, [
            ("lookup_session", {"filters": {"id": "absent-session"}}, {"page": 1, "size": 1})
        ])
        self.assertEqual(
            sum(call[0] in {"get_or_create", "create", "upsert", "add", "save", "flush"} for call in calls),
            0,
        )


if __name__ == "__main__":
    unittest.main()
