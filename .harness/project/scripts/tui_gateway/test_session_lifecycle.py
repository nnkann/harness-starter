import os
import sys
import threading
import time

# Update path to import correctly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from session_lifecycle import EventBus, SessionLifecycleManager, SessionState

def test_gc_transition():
    bus = EventBus()
    mgr = SessionLifecycleManager(bus)
    assert mgr.state == SessionState.INIT
    
    # AC2: Maat audit complete should transition to EVICTABLE
    bus.publish("SIG_AUDIT_DONE")
    assert mgr.state == SessionState.EVICTABLE
    print("[AC2] Success: Maat audit complete triggered EVICTABLE state.")

def test_eof_termination():
    bus = EventBus()
    mgr = SessionLifecycleManager(bus)

    # Mock os._exit to test if it's called
    original_exit = os._exit
    exit_called = []
    def mock_exit(code):
        exit_called.append(code)
    
    os._exit = mock_exit
    try:
        bus.publish("PIPELINE_EOF")
        assert len(exit_called) == 1
        assert exit_called[0] == 0
        assert mgr.state == SessionState.TERMINATED
        print("[AC3] Success: EOF immediately called os._exit(0) without polling.")
    finally:
        os._exit = original_exit

if __name__ == "__main__":
    test_gc_transition()
    test_eof_termination()
    print("All tests passed.")
