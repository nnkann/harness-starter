import asyncio
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

from session_lifecycle import SessionLifecycleManager, SessionState

class TestSessionLifecycleManager(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.manager = SessionLifecycleManager()

    def test_maat_audit_complete_transitions_to_evictable(self):
        # Arrange
        mock_resource = MagicMock()
        self.manager.register_resource(mock_resource)
        self.assertEqual(self.manager.state, SessionState.ACTIVE)
        self.assertEqual(len(self.manager.resources), 1)

        # Act
        self.manager.trigger_maat_audit_complete()

        # Assert
        self.assertEqual(self.manager.state, SessionState.EVICTABLE)
        mock_resource.close.assert_called_once()
        self.assertEqual(len(self.manager.resources), 0)

    @patch('os._exit')
    @patch('sys.stdout.flush')
    @patch('sys.stderr.flush')
    async def test_pipeline_eof_triggers_exit(self, mock_stderr_flush, mock_stdout_flush, mock_exit):
        # Arrange
        mock_reader = asyncio.StreamReader()
        mock_reader.feed_eof() # Simulate EOF immediately

        # Act
        await self.manager.monitor_pipeline_eof(mock_reader)

        # Assert
        mock_stdout_flush.assert_called_once()
        mock_stderr_flush.assert_called_once()
        mock_exit.assert_called_once_with(0)

if __name__ == '__main__':
    unittest.main()
