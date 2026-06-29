# Zombie Session and Deadlock Documentation (AC4)

## Deadlock Case: Polling with Timeout on Closed Pipes
In previous iterations, workers used `select()` or `time.sleep()` based polling on `sys.stdin` to detect if the gateway was still alive. This created a race condition:
1. The gateway closes the pipe abruptly (e.g., due to OOM or network drop).
2. The worker is stuck inside a blocking operation (e.g., a long compilation) and its polling thread is asleep.
3. The worker finishes, tries to write results back to the closed stdout, triggering a SIGPIPE.
4. If SIGPIPE is caught or ignored, the worker goes back to polling, but fails to realize the session is dead because the polling logic wasn't responsive to EOF.
Result: Deadlocked worker waiting for events on a closed pipe.

## Zombie Session Case: Missing Maat Finalization
When the worker successfully completes its tasks, `Maat` generates an audit complete signal.
1. The worker finishes but does not terminate immediately because it waits for the gateway to close the connection.
2. The gateway loses the connection state internally but leaves the pipe open.
3. The session remains `ACTIVE` indefinitely because there is no periodic cleanup for sessions that have finished but haven't been reaped.
Result: Zombie session consuming memory and process table slots.

## Solution Implemented
- **No-polling EOF monitor:** A dedicated daemon thread performs a blocking `sys.stdin.read()`. The OS kernel immediately unblocks this read with an empty string when the pipe is closed (EOF). The worker then directly invokes `os._exit(0)`.
- **Maat Signal GC Transition:** When `MAAT_AUDIT_COMPLETE` is received over the EventBus, the state machine synchronously transitions the session to `EVICTABLE`. This allows the background daemon (Gateway Cleanup) to safely reap the session even if the process hasn't fully terminated yet.
