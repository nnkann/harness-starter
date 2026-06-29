import os
import sys
import threading
from enum import Enum, auto
from typing import Callable, Any

class SessionState(Enum):
    INIT = auto()
    ACTIVE = auto()
    EVICTABLE = auto()
    TERMINATED = auto()

class EventBus:
    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = {}
        self._lock = threading.Lock()

    def subscribe(self, event_type: str, handler: Callable):
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(handler)

    def publish(self, event_type: str, payload: Any = None):
        with self._lock:
            handlers = self._subscribers.get(event_type, [])
        for handler in handlers:
            try:
                handler(payload)
            except Exception as e:
                # Log error, don't crash bus
                sys.stderr.write(f"[EventBus] Handler error for {event_type}: {e}\n")

class SessionLifecycleManager:
    def __init__(self, event_bus: EventBus):
        self.state = SessionState.INIT
        self.bus = event_bus
        self._lock = threading.Lock()

        # Subscribe to relevant events
        self.bus.subscribe("SIG_AUDIT_DONE", self._on_maat_audit_complete)
        self.bus.subscribe("WEBSOCKET_PING", self._on_ws_ping)
        self.bus.subscribe("PIPELINE_EOF", self._on_pipeline_eof)
        self.bus.subscribe("PIPELINE_SIGPIPE", self._on_pipeline_eof)

    def transition_to(self, new_state: SessionState):
        with self._lock:
            old_state = self.state
            self.state = new_state
            # Optional: log state change
            self.bus.publish("STATE_CHANGED", {"old": old_state, "new": new_state})

    def _on_maat_audit_complete(self, payload: Any):
        """When Maat Audit Complete signal is received, transition to EVICTABLE."""
        self.transition_to(SessionState.EVICTABLE)

    def _on_ws_ping(self, payload: Any):
        """Respond to ping with pong to keep active."""
        if self.state == SessionState.INIT:
            self.transition_to(SessionState.ACTIVE)
        self.bus.publish("WEBSOCKET_PONG", {"status": "alive", "state": self.state.name})

    def _on_pipeline_eof(self, payload: Any):
        """Handle EOF/SIGPIPE by gracefully terminating without polling."""
        self.transition_to(SessionState.TERMINATED)
        # AC3: Worker self-terminates directly on EOF without polling
        sys.stderr.write("[Lifecycle] EOF/SIGPIPE detected. Terminating immediately.\n")
        os._exit(0)

def start_eof_monitor(bus: EventBus):
    """
    Blocks on stdin to detect EOF. 
    Does not use timeout/polling.
    """
    def _monitor():
        try:
            # Blocking read; when EOF is reached, it returns empty string
            _ = sys.stdin.read()
            bus.publish("PIPELINE_EOF")
        except Exception:
            bus.publish("PIPELINE_SIGPIPE")

    t = threading.Thread(target=_monitor, daemon=True)
    t.start()
    return t
