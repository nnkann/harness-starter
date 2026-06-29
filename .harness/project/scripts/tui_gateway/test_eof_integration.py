import subprocess
import time
import sys
import psutil

def test_integration():
    print("[Integration Test] Starting dummy worker...")
    p = subprocess.Popen(
        [sys.executable, "dummy_worker.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait a bit to ensure it is running
    time.sleep(1)
    
    if p.poll() is not None:
        print("[Integration Test] Worker died too early.")
        sys.exit(1)
        
    print(f"[Integration Test] Worker is running with PID {p.pid}.")
    
    # Check if process is zombies
    proc = psutil.Process(p.pid)
    assert proc.status() != psutil.STATUS_ZOMBIE, "Process should be running, not zombie."
    
    print("[Integration Test] Closing pipeline (EOF)...")
    p.stdin.close()
    
    # Wait for process to exit
    p.wait(timeout=5)
    
    print(f"[Integration Test] Worker exited with code {p.returncode}")
    assert p.returncode == 0, "Worker should exit cleanly with code 0"
    
    # Check if process exists (it shouldn't)
    try:
        proc.status()
        is_zombie = proc.status() == psutil.STATUS_ZOMBIE
        if is_zombie:
            print("[Integration Test] Error: Process is a zombie!")
            sys.exit(1)
    except psutil.NoSuchProcess:
        print("[Integration Test] Process successfully cleaned up (no zombie left).")
        
    print("[Integration Test] Success! Pipeline disconnect safely terminated child process.")

if __name__ == "__main__":
    test_integration()
