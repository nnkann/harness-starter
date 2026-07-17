#!/usr/bin/env python3
"""Harness Background Daemon.

Automates Honcho, GBrain Memory, and Gateway Cleanup processes in a periodic loop.
Handles graceful shutdown (SIGINT/SIGTERM) and writes structured JSON logs.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path

# Paths Setup
REPO_DIR = Path(__file__).resolve().parents[3]
PROJECT_DIR = REPO_DIR / ".harness/project"
RUNS_DIR = PROJECT_DIR / "runs"
REPORTS_DIR = PROJECT_DIR / "reports"
SCRIPTS_DIR = PROJECT_DIR / "scripts"

# Log Files
DAEMON_LOG_FILE = RUNS_DIR / "background_daemon.log"
AUDIT_LOG_FILE = RUNS_DIR / "background_audit.log"

# Default python interpreter path (Hermes virtual environment or system fallback)
HERMES_VENV_PYTHON = Path("/Users/kann/.hermes/hermes-agent/.venv/bin/python")
PYTHON_EXEC = str(HERMES_VENV_PYTHON) if HERMES_VENV_PYTHON.exists() else sys.executable

# Daemon control event for graceful shutdown
shutdown_event = threading.Event()


def log_structured(file_path: Path, data: dict) -> None:
    """Writes a single-line structured JSON log entry."""
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")
    except Exception as e:
        sys.stderr.write(f"[Daemon Error] Failed to write log to {file_path}: {e}\n")


def handle_shutdown(signum, frame) -> None:
    """Signal handler to trigger graceful shutdown."""
    sys.stdout.write(f"\n[Daemon] Received signal {signum}. Triggering graceful shutdown...\n")
    shutdown_event.set()


def run_subprocess(cmd: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    """Runs a subprocess safely, returning exit code, stdout, and stderr."""
    try:
        res = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=45,  # Avoid hanging indefinitely
        )
        return res.returncode, res.stdout, res.stderr
    except subprocess.TimeoutExpired as e:
        return -1, "", f"Timeout expired after 45s: {e}"
    except Exception as e:
        return -2, "", f"Exception during execution: {type(e).__name__} - {e}"


def run_honcho_ingest(session_key: str) -> dict:
    """Ingests pending manifests using honcho_background_worker.py."""
    worker_script = SCRIPTS_DIR / "router/honcho_background_worker.py"
    cmd = [
        PYTHON_EXEC,
        str(worker_script),
        "--action",
        "ingest",
        "--honcho-session-key",
        session_key,
        "--repo",
        str(REPO_DIR),
    ]
    code, out, err = run_subprocess(cmd, cwd=REPO_DIR)
    return {
        "exit_code": code,
        "success": code == 0,
        "stdout_summary": out.strip().splitlines()[-3:] if out else [],
        "stderr_summary": err.strip().splitlines()[-3:] if err else [],
    }


def run_honcho_drift_check(session_key: str) -> dict:
    """Performs drift QA check and writes report to reports directory."""
    worker_script = SCRIPTS_DIR / "router/honcho_background_worker.py"
    cmd = [
        PYTHON_EXEC,
        str(worker_script),
        "--action",
        "check-drift",
        "--honcho-session-key",
        session_key,
        "--repo",
        str(REPO_DIR),
    ]
    code, out, err = run_subprocess(cmd, cwd=REPO_DIR)

    # Save the drift report to reports directory
    report_file = REPORTS_DIR / f"drift_report_{session_key}.txt"
    try:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        report_file.write_text(out if code == 0 else f"Error running drift check:\n{err}", encoding="utf-8")
    except Exception as e:
        err += f"\n[Daemon Alert] Failed to write drift report file: {e}"

    return {
        "exit_code": code,
        "success": code == 0,
        "report_path": str(report_file),
        "stderr_summary": err.strip().splitlines()[-3:] if err else [],
    }


def run_supabase_inventory() -> dict:
    """Runs read_only_supabase_inventory.py to verify metadata access."""
    inventory_script = SCRIPTS_DIR / "harness_memory/read_only_supabase_inventory.py"
    cmd = [PYTHON_EXEC, str(inventory_script)]
    code, out, err = run_subprocess(cmd, cwd=REPO_DIR)

    # Parse JSON output if successful
    parsed_report = None
    if code == 0 and out.strip():
        try:
            parsed_report = json.loads(out)
        except Exception:
            pass

    return {
        "exit_code": code,
        "success": code == 0,
        "inventory_summary": parsed_report,
        "stderr_summary": err.strip().splitlines()[-3:] if err else [],
    }


def run_candidate_dry_run() -> dict:
    """Runs ingest_candidates.py to scan and generate candidate JSONL."""
    candidates_script = SCRIPTS_DIR / "harness_memory/ingest_candidates.py"
    output_path = REPORTS_DIR / "harness_memory_candidates.jsonl"
    cmd = [
        PYTHON_EXEC,
        str(candidates_script),
        "--repo",
        str(REPO_DIR),
        "--out",
        str(output_path),
        "--mode",
        "dry-run",
    ]
    code, out, err = run_subprocess(cmd, cwd=REPO_DIR)

    parsed_summary = None
    if code == 0 and out.strip():
        try:
            parsed_summary = json.loads(out)
        except Exception:
            pass

    return {
        "exit_code": code,
        "success": code == 0,
        "candidates_summary": parsed_summary,
        "stderr_summary": err.strip().splitlines()[-3:] if err else [],
    }


def perform_gateway_cleanup() -> dict:
    """Synchronizes writeback metadata to user sessions.json (Gateway Cleanup)."""
    sessions_file = Path.home() / ".hermes/sessions/sessions.json"
    if not sessions_file.exists():
        return {
            "success": False,
            "message": f"sessions.json not found at {sessions_file}",
            "cleaned_sessions": [],
        }

    # 1. Scan writeback files in runs directory to collect completed sessions
    completed_sessions = set()
    try:
        for p in RUNS_DIR.glob("writeback_*.json"):
            # Avoid reading in-progress templates or invalid JSONs
            if p.stem == "writeback_harness-starter":
                continue
            try:
                wb_data = json.loads(p.read_text(encoding="utf-8"))
                s_id = wb_data.get("session_id")
                if s_id:
                    completed_sessions.add(s_id)
            except Exception:
                pass
    except Exception as e:
        return {"success": False, "message": f"Failed to scan writeback files: {e}", "cleaned_sessions": []}

    if not completed_sessions:
        return {
            "success": True,
            "message": "No completed sessions found in writeback files.",
            "cleaned_sessions": [],
        }

    # 2. Load, update, and save sessions.json safely
    cleaned_sessions = []
    try:
        # Load sessions
        sessions_data = json.loads(sessions_file.read_text(encoding="utf-8"))
        updated = False

        for key, s_info in list(sessions_data.items()):
            s_id = s_info.get("session_id")
            s_key = s_info.get("session_key")

            # Check if this session is marked as completed
            if (s_id in completed_sessions) or (s_key in completed_sessions):
                # Check if it needs cleanup
                is_suspended = s_info.get("suspended")
                is_finalized = s_info.get("expiry_finalized")
                cleanup_state = s_info.get("route_cleanup_state")

                if not is_suspended or not is_finalized or cleanup_state != "completed":
                    s_info["suspended"] = True
                    s_info["expiry_finalized"] = True
                    s_info["route_cleanup_state"] = "completed"
                    s_info["cleaned_at_by_daemon"] = datetime.utcnow().isoformat() + "Z"
                    cleaned_sessions.append(s_id or s_key)
                    updated = True

        # Save back using safe atomic write
        if updated:
            tmp_file = sessions_file.with_suffix(".tmp")
            tmp_file.write_text(json.dumps(sessions_data, indent=2, ensure_ascii=False), encoding="utf-8")
            tmp_file.replace(sessions_file)
            message = f"Cleaned up {len(cleaned_sessions)} active sessions in sessions.json."
        else:
            message = "All completed sessions are already cleaned up."

        return {
            "success": True,
            "message": message,
            "cleaned_sessions": cleaned_sessions,
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Exception during sessions.json update: {e}",
            "cleaned_sessions": cleaned_sessions,
        }


def run_cycle(cycle_number: int, session_key: str) -> None:
    """Executes a single workflow cycle and records audits."""
    start_time = datetime.utcnow()
    timestamp_str = start_time.isoformat() + "Z"

    sys.stdout.write(f"\n[Daemon] --- Cycle {cycle_number} Start at {timestamp_str} ---\n")

    # Step 1: Honcho Ingest
    sys.stdout.write("[Daemon] Running Honcho Ingest...\n")
    ingest_res = run_honcho_ingest(session_key)

    # Step 2: Honcho Drift Check
    sys.stdout.write("[Daemon] Running Honcho Drift Check...\n")
    drift_res = run_honcho_drift_check(session_key)

    # Step 3: Supabase Inventory
    sys.stdout.write("[Daemon] Running Supabase Inventory Check...\n")
    supabase_res = run_supabase_inventory()

    # Step 4: Candidate Dry Run
    sys.stdout.write("[Daemon] Running Candidate Dry Run Scan...\n")
    candidate_res = run_candidate_dry_run()

    # Step 5: Gateway Cleanup
    sys.stdout.write("[Daemon] Running Gateway Session Cleanup...\n")
    cleanup_res = perform_gateway_cleanup()

    # Calculate execution durations
    end_time = datetime.utcnow()
    duration = (end_time - start_time).total_seconds()

    # Consolidate results for structured audit
    cycle_audit_data = {
        "timestamp": timestamp_str,
        "cycle": cycle_number,
        "duration_seconds": duration,
        "status": "success",
        "session_key": session_key,
        "steps": {
            "honcho_ingest": {
                "exit_code": ingest_res["exit_code"],
                "success": ingest_res["success"],
                "stdout_summary": ingest_res["stdout_summary"],
                "stderr_summary": ingest_res["stderr_summary"],
            },
            "honcho_drift_check": {
                "exit_code": drift_res["exit_code"],
                "success": drift_res["success"],
                "report_path": drift_res["report_path"],
                "stderr_summary": drift_res["stderr_summary"],
            },
            "supabase_inventory": {
                "exit_code": supabase_res["exit_code"],
                "success": supabase_res["success"],
                "inventory_summary": supabase_res["inventory_summary"],
                "stderr_summary": supabase_res["stderr_summary"],
            },
            "candidate_dry_run": {
                "exit_code": candidate_res["exit_code"],
                "success": candidate_res["success"],
                "candidates_summary": candidate_res["candidates_summary"],
                "stderr_summary": candidate_res["stderr_summary"],
            },
            "gateway_cleanup": {
                "success": cleanup_res["success"],
                "message": cleanup_res["message"],
                "cleaned_sessions": cleanup_res["cleaned_sessions"],
            },
        },
    }

    # Write to audit logs
    log_structured(DAEMON_LOG_FILE, cycle_audit_data)

    # Write simplified action summary to background_audit.log for project compliance (AC-4)
    simple_audit_entry = {
        "timestamp": timestamp_str,
        "action": f"daemon-cycle-{cycle_number}",
        "exit_code": 0 if (ingest_res["success"] and drift_res["success"] and candidate_res["success"]) else 1,
        "message": f"Cycle {cycle_number} completed in {duration:.2f}s. "
                   f"Cleaned sessions: {cleanup_res['cleaned_sessions']}. "
                   f"Candidates: {candidate_res.get('candidates_summary', {}).get('candidate_count', 0)}.",
    }
    log_structured(AUDIT_LOG_FILE, simple_audit_entry)

    sys.stdout.write(f"[Daemon] --- Cycle {cycle_number} Completed in {duration:.2f}s ---\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Harness Background Daemon")
    parser.add_argument("--interval", type=int, default=60, help="Execution interval in seconds (default: 60)")
    parser.add_argument("--session-key", default="session_harness_bg_sync", help="Honcho session key to sync with")
    args = parser.parse_args()

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    # Audit daemon startup
    startup_timestamp = datetime.utcnow().isoformat() + "Z"
    startup_msg = {
        "timestamp": startup_timestamp,
        "action": "daemon-start",
        "exit_code": 0,
        "message": f"Harness Background Daemon started with interval {args.interval}s on session {args.session_key}. Python: {PYTHON_EXEC}",
    }
    log_structured(AUDIT_LOG_FILE, startup_msg)
    log_structured(DAEMON_LOG_FILE, {"event": "daemon-start", "timestamp": startup_timestamp, "pid": os.getpid(), "interval": args.interval, "session_key": args.session_key})

    sys.stdout.write(f"[Daemon] Starting Harness Background Daemon (PID: {os.getpid()}) with {args.interval}s interval...\n")

    cycle_count = 0
    while not shutdown_event.is_set():
        cycle_count += 1
        try:
            run_cycle(cycle_count, args.session_key)
        except Exception as e:
            err_timestamp = datetime.utcnow().isoformat() + "Z"
            sys.stderr.write(f"[Daemon Error] Exception in cycle {cycle_count}: {e}\n")
            log_structured(DAEMON_LOG_FILE, {
                "timestamp": err_timestamp,
                "cycle": cycle_count,
                "status": "failed",
                "error": str(e)
            })
            log_structured(AUDIT_LOG_FILE, {
                "timestamp": err_timestamp,
                "action": f"daemon-cycle-{cycle_count}",
                "exit_code": 99,
                "message": f"Unhandled exception: {e}"
            })

        # Wait for the next interval or shutdown signal
        sys.stdout.write(f"[Daemon] Sleeping for {args.interval} seconds...\n")
        # Event.wait returns True if the internal flag is set, False if the timeout occurs
        if shutdown_event.wait(timeout=args.interval):
            break

    # Graceful shutdown audit
    shutdown_timestamp = datetime.utcnow().isoformat() + "Z"
    shutdown_msg = {
        "timestamp": shutdown_timestamp,
        "action": "daemon-stop",
        "exit_code": 0,
        "message": "Harness Background Daemon stopped gracefully.",
    }
    log_structured(AUDIT_LOG_FILE, shutdown_msg)
    log_structured(DAEMON_LOG_FILE, {"event": "daemon-stop", "timestamp": shutdown_timestamp})
    sys.stdout.write("[Daemon] Shutdown complete.\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
