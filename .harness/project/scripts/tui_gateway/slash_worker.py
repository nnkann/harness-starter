"""
tui_gateway/slash_worker.py
Integrates session_lifecycle module.
"""

import time
import sys
from .session_lifecycle import EventBus, SessionLifecycleManager, start_eof_monitor

def main():
    bus = EventBus()
    manager = SessionLifecycleManager(bus)

    # Start EOF monitor that will block and trigger os._exit(0) on EOF
    start_eof_monitor(bus)

    # Main event loop for the worker
    try:
        sys.stderr.write("[Worker] Started. Waiting for events...\n")
        while True:
            # Simulate processing and heartbeat
            time.sleep(1)
            bus.publish("WEBSOCKET_PING")
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
