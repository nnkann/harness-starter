import sys
import unittest
import unittest.mock
from pathlib import Path
from types import SimpleNamespace


HERMES = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERMES / "contracts"))
sys.path.insert(0, str(HERMES / "readers"))

import cps_advisory_reader_contract as contract
import honcho_session_reader as reader


class FakeManager:
    def __init__(self, session):
        self.session = session
        self.calls = []

    def _sanitize_id(self, key):
        return key


class HonchoSessionReaderTests(unittest.TestCase):
    def retrieve(self, binding):
        return contract.retrieve_advisory(binding, "resume packet", {"request_ref": "C:honcho-reader"})

    def test_configured_sdk_session_readback_uses_semantic_search_once_without_writes(self):
        config = SimpleNamespace(enabled=True, workspace_id="workspace-7", host="hermes", resolve_session_name=lambda: "default-key")
        session = SimpleNamespace(honcho_session_id="sdk-session-8", user_peer_id="user-9", assistant_peer_id="assistant-10")
        manager = FakeManager(session)
        client_calls = []
        manager_calls = []

        class Client:
            workspace_id = "workspace-7"
            _http = SimpleNamespace(post=lambda *args, **kwargs: {"items": [{"id": "default-key"}]})

            def search(self, query, **kwargs):
                client_calls.append(("search", query, kwargs))
                return [SimpleNamespace(
                    content="The resume packet records the bounded source receipt. Irrelevant second sentence.",
                    session_id="source-session",
                    id="message-1",
                )]

        binding = reader.configured_honcho_session_binding(
            "packet-session",
            config_loader=lambda: config,
            client_factory=lambda received: client_calls.append(received) or Client(),
            manager_factory=lambda **kwargs: manager_calls.append(kwargs) or manager,
        )
        result = self.retrieve(binding)

        self.assertEqual(result.state, "available")
        self.assertEqual(result.producer_ref, "honcho-sdk:workspace-7:hermes")
        self.assertEqual(result.source_identity, "honcho-sdk-semantic-peer:user")
        self.assertEqual(result.reader_context, {"request_ref": "C:honcho-reader"})
        self.assertEqual(result.evidence["record_count"], 1)
        self.assertEqual(result.evidence["source_receipt"], "semantic-session=source-session;message=message-1")
        self.assertEqual(len(result.evidence["content_digest"]), 64)
        self.assertEqual(result.candidate["clue"], "The resume packet records the bounded source receipt.")
        self.assertEqual(result.candidate["source_ref"], result.source_identity)
        self.assertEqual(result.candidate["source_receipt"], result.evidence["source_receipt"])
        self.assertEqual(result.candidate["lifecycle"], "candidate")
        self.assertRegex(result.candidate["observed_at"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
        self.assertLessEqual(len(result.candidate["clue"]), 256)
        self.assertEqual(client_calls, [
            config,
            ("search", "resume packet", {"filters": {"peer_perspective": "user"}, "limit": 3}),
        ])
        self.assertEqual(len(manager_calls), 1)
        self.assertEqual(manager.calls, [])

    def test_disabled_config_is_explicitly_unavailable_without_sdk_construction(self):
        config = SimpleNamespace(enabled=False, resolve_session_name=lambda: "disabled-session")
        client_factory = unittest.mock.Mock()
        manager_factory = unittest.mock.Mock()

        binding = reader.configured_honcho_session_binding(
            config_loader=lambda: config, client_factory=client_factory, manager_factory=manager_factory
        )
        result = self.retrieve(binding)

        self.assertEqual(result.state, "unavailable")
        self.assertEqual(result.source_identity, "honcho-sdk-session:disabled-session")
        self.assertEqual(result.evidence, {"record_count": 0, "source_receipt": "honcho-session-reader:config_disabled"})
        client_factory.assert_not_called()
        manager_factory.assert_not_called()

    def test_sdk_or_session_failure_is_explicitly_unavailable(self):
        config = SimpleNamespace(enabled=True, resolve_session_name=lambda: "failed-session")

        binding = reader.configured_honcho_session_binding(
            config_loader=lambda: config,
            client_factory=lambda received: (_ for _ in ()).throw(RuntimeError("offline")),
            manager_factory=lambda **kwargs: self.fail("manager must not be constructed"),
        )
        result = self.retrieve(binding)

        self.assertEqual(result.state, "unavailable")
        self.assertEqual(result.evidence["source_receipt"], "honcho-session-reader:sdk_or_session_failure")

    def test_semantic_search_failure_is_explicitly_unavailable(self):
        config = SimpleNamespace(enabled=True, workspace_id="workspace", host="hermes", resolve_session_name=lambda: "unused")
        session = SimpleNamespace(honcho_session_id="sdk-session", user_peer_id="user", assistant_peer_id="assistant")
        manager = FakeManager(session)
        client = SimpleNamespace(
            workspace_id="workspace",
            _http=SimpleNamespace(post=lambda *args, **kwargs: {"items": [{"id": "unused"}]}),
            search=lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("offline")),
        )

        binding = reader.configured_honcho_session_binding(
            "packet-session",
            config_loader=lambda: config,
            client_factory=lambda received: client,
            manager_factory=lambda **kwargs: manager,
        )
        result = self.retrieve(binding)

        self.assertEqual(result.state, "unavailable")
        self.assertEqual(result.evidence["source_receipt"], "honcho-session-reader:read_failure")

    def test_surface_memory_context_cannot_become_a_clue(self):
        candidate = reader._candidate(
            [{"content": "The resume packet preserves the CPS source boundary.", "session_id": ""}],
            "resume packet",
            "honcho-sdk-semantic-peer:user",
        )

        self.assertIsNone(candidate)

    def test_c_shape_overlap_cannot_select_a_query_irrelevant_clue(self):
        candidate = reader._candidate(
            [{"content": "The linked boundary requires multiple current state records.", "session_id": "one"}],
            "resume packet",
            "honcho-sdk-semantic-peer:user",
        )

        self.assertIsNone(candidate)


if __name__ == "__main__":
    unittest.main()
