import sys
import time
from session_lifecycle import EventBus, SessionLifecycleManager, start_eof_monitor

def main():
    bus = EventBus()
    mgr = SessionLifecycleManager(bus)
    t = start_eof_monitor(bus)
    
    # Keep alive until EOF
    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()
