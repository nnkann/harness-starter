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

    def get_or_create(self, key):
        self.calls.append(("get_or_create", key))
        return self.session

    def get_session_context(self, key, peer):
        self.calls.append(("get_session_context", key, peer))
        return {"summary": "actual configured context", "recent_messages": [{"content": "one"}]}

    def search_context(self, key, query, max_tokens, peer):
        self.calls.append(("search_context", key, query, max_tokens, peer))
        return "actual configured search result"


class HonchoSessionReaderTests(unittest.TestCase):
    def retrieve(self, binding):
        return contract.retrieve_advisory(binding, "resume packet", {"request_ref": "C:honcho-reader"})

    def test_configured_sdk_session_readback_uses_context_and_search_without_writes(self):
        config = SimpleNamespace(enabled=True, workspace_id="workspace-7", host="hermes", resolve_session_name=lambda: "default-key")
        session = SimpleNamespace(honcho_session_id="sdk-session-8", user_peer_id="user-9", assistant_peer_id="assistant-10")
        manager = FakeManager(session)
        client_calls = []
        manager_calls = []

        binding = reader.configured_honcho_session_binding(
            "packet-session",
            config_loader=lambda: config,
            client_factory=lambda received: client_calls.append(received) or object(),
            manager_factory=lambda **kwargs: manager_calls.append(kwargs) or manager,
        )
        result = self.retrieve(binding)

        self.assertEqual(result.state, "available")
        self.assertEqual(result.producer_ref, "honcho-sdk:workspace-7:hermes")
        self.assertEqual(result.source_identity, "honcho-sdk-session:sdk-session-8")
        self.assertEqual(result.reader_context, {"request_ref": "C:honcho-reader"})
        self.assertEqual(result.evidence["record_count"], 3)
        self.assertEqual(result.evidence["source_receipt"], "session=sdk-session-8;user_peer=user-9;assistant_peer=assistant-10")
        self.assertEqual(len(result.evidence["content_digest"]), 64)
        self.assertEqual(client_calls, [config])
        self.assertEqual(len(manager_calls), 1)
        self.assertEqual(manager.calls, [
            ("get_or_create", "packet-session"),
            ("get_session_context", "packet-session", "user"),
            ("search_context", "packet-session", "resume packet", reader.SEARCH_TOKEN_LIMIT, "user"),
        ])

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

    def test_context_or_search_failure_is_explicitly_unavailable(self):
        config = SimpleNamespace(enabled=True, workspace_id="workspace", host="hermes", resolve_session_name=lambda: "unused")
        session = SimpleNamespace(honcho_session_id="sdk-session", user_peer_id="user", assistant_peer_id="assistant")
        manager = FakeManager(session)
        manager.search_context = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("offline"))

        binding = reader.configured_honcho_session_binding(
            "packet-session",
            config_loader=lambda: config,
            client_factory=lambda received: object(),
            manager_factory=lambda **kwargs: manager,
        )
        result = self.retrieve(binding)

        self.assertEqual(result.state, "unavailable")
        self.assertEqual(result.evidence["source_receipt"], "honcho-session-reader:read_failure")


if __name__ == "__main__":
    unittest.main()
