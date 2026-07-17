import asyncio
import os
import sys
import enum
import logging

class SessionState(enum.Enum):
    ACTIVE = "ACTIVE"
    EVICTABLE = "EVICTABLE"

class SessionLifecycleManager:
    def __init__(self):
        self.state = SessionState.ACTIVE
        self.resources = []

    def register_resource(self, resource):
        """Register a resource (like a socket or file descriptor) to be cleaned up."""
        self.resources.append(resource)

    def trigger_maat_audit_complete(self, assignee: str = "Maat", task_content: str = "CPS 분석 및 에이전트 호출"):
        """Transitions immediately to Evictable state upon Maat's signal, logging delegation details."""
        log_msg = f"[{assignee}] {task_content}"
        print(log_msg, flush=True)
        self._transition_to_evictable()

    def _transition_to_evictable(self):
        self.state = SessionState.EVICTABLE
        self._release_resources()

    def _release_resources(self):
        for res in self.resources:
            try:
                if hasattr(res, 'close'):
                    res.close()
            except Exception as e:
                logging.error(f"Error closing resource: {e}")
        self.resources.clear()

    async def monitor_pipeline_eof(self, reader: asyncio.StreamReader):
        """Event-driven pipeline EOF monitoring."""
        try:
            data = await reader.read()
            if not data:
                self._handle_eof()
        except asyncio.IncompleteReadError:
            self._handle_eof()
        except Exception as e:
            logging.error(f"Pipeline error: {e}")
            self._handle_eof()

    def _handle_eof(self):
        """Handles EOF safely by flushing buffers and exiting."""
        try:
            sys.stdout.flush()
            sys.stderr.flush()
        except Exception:
            pass
        finally:
            os._exit(0)
