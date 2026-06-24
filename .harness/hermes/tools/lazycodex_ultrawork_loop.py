#!/usr/bin/env python3
"""LazyCodex Ultrawork Loop Control Engine.
Enforces 2-cycle self-correction, boulder state management, and CPS Trace formula generation.
"""

from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Find repository root
def find_repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in [current, *current.parents]:
        if (parent / ".harness" / "hermes" / "loader.py").exists():
            return parent
    return Path("/Users/kann/projects/harness-starter")

REPO_ROOT = find_repo_root()
BOULDER_STATE_FILE = REPO_ROOT / ".harness" / "project" / "runs" / "boulder_state.json"
LEDGER_FILE = REPO_ROOT / ".harness" / "project" / "runs" / "boulder_ledger.jsonl"

def load_state() -> dict[str, Any]:
    """Loads the current boulder state or returns a default skeleton."""
    if not BOULDER_STATE_FILE.exists():
        return {
            "session_id": "session_harness_default",
            "status": "INIT",
            "current_step": "explore",
            "self_correction_count": 0,
            "max_self_corrections": 2,
            "error_history": [],
            "cps_trace": ["C"],
            "last_error": None,
            "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        }
    try:
        return json.loads(BOULDER_STATE_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        sys.stderr.write(f"[Ultrawork Loop] Warning: Failed to load boulder state: {e}. Resetting.\n")
        return {
            "session_id": "session_harness_default",
            "status": "INIT",
            "current_step": "explore",
            "self_correction_count": 0,
            "max_self_corrections": 2,
            "error_history": [],
            "cps_trace": ["C"],
            "last_error": None,
            "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        }

def save_state(state: dict[str, Any]) -> None:
    """Saves the boulder state safely and atomically."""
    state["updated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    BOULDER_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp_file = BOULDER_STATE_FILE.with_suffix(".tmp")
    tmp_file.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp_file.replace(BOULDER_STATE_FILE)

def write_ledger(entry: dict[str, Any]) -> None:
    """Writes a structured entry to the ledger log."""
    entry["timestamp"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    LEDGER_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LEDGER_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def run_oracle_verification(verify_cmd: str) -> tuple[int, str]:
    """Runs the oracle verification command (tests, lint, build)."""
    print(f"[Ultrawork Loop] Executing Oracle Verification: {verify_cmd}")
    try:
        res = subprocess.run(
            verify_cmd,
            shell=True,
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=60
        )
        return res.returncode, res.stdout
    except subprocess.TimeoutExpired:
        return -1, "Verification timed out after 60 seconds."
    except Exception as e:
        return -2, f"Exception during verification: {e}"

def generate_trace_formula(trace_steps: list[str]) -> str:
    """Formats the trace steps into a canonical CPS Trace formula (e.g., C > P1,P3 > S2,S4 > P2 > S3)."""
    return " > ".join(trace_steps)

def handle_verification_result(
    success: bool,
    error_msg: str | None,
    verify_cmd: str,
    problem_id: str | None = None,
    solution_id: str | None = None
) -> int:
    """Manages the self-correction cycle and state transition based on verification."""
    state = load_state()
    
    # Track Problems and Solutions if provided
    p_str = problem_id if problem_id else "P_UNKNOWN"
    s_str = solution_id if solution_id else "S_UNKNOWN"

    if success:
        print("[Ultrawork Loop] Oracle Verification PASSED.")
        # If we had prior errors, record the successful resolution
        if state["status"] == "SELF_CORRECTING":
            state["cps_trace"].append(s_str)
            state["status"] = "SUCCESS"
        else:
            state["status"] = "SUCCESS"
            state["cps_trace"].append(s_str)
            
        state["self_correction_count"] = 0  # Reset on success
        state["last_error"] = None
        save_state(state)
        
        write_ledger({
            "action": "verify_pass",
            "verify_cmd": verify_cmd,
            "cps_trace_formula": generate_trace_formula(state["cps_trace"]),
            "message": "Verification passed successfully."
        })
        return 0
    else:
        print(f"[Ultrawork Loop] Oracle Verification FAILED: {error_msg}")
        state["last_error"] = error_msg
        
        # Ingest the problem trace
        if p_str not in state["cps_trace"]:
            state["cps_trace"].append(p_str)
            
        if state["status"] != "SELF_CORRECTING":
            state["status"] = "SELF_CORRECTING"
            state["self_correction_count"] = 1
            state["cps_trace"].append(s_str)  # Initial fix attempt
            save_state(state)
            
            write_ledger({
                "action": "self_correction_triggered",
                "attempt": 1,
                "problem": p_str,
                "solution": s_str,
                "cps_trace_formula": generate_trace_formula(state["cps_trace"]),
                "error": error_msg
            })
            print(f"[Ultrawork Loop] Self-correction #1 triggered. Modify code to fix. CPS Trace: {generate_trace_formula(state['cps_trace'])}")
            return 2  # Signal to retry / self-correct
        else:
            state["self_correction_count"] += 1
            state["cps_trace"].append(s_str)  # Secondary fix attempt
            
            if state["self_correction_count"] > state["max_self_corrections"]:
                # Limit exceeded (Max 2 attempts)
                state["status"] = "HOLD_BLOCKED"
                
                # Context Chaining (New C) Mechanism
                chained_session_id = f"{state['session_id']}_chained_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
                chained_context = {
                    "parent_session_id": state["session_id"],
                    "parent_status": "HOLD_BLOCKED",
                    "inherited_cps_trace": state["cps_trace"].copy(),
                    "inherited_last_error": error_msg,
                    "new_context_id": f"C_CHAINED_FROM_{state['session_id']}",
                    "remediation_status": "PENDING_TRIAGE",
                    "suggested_next_session_id": chained_session_id
                }
                state["chained_context"] = chained_context
                save_state(state)
                
                write_ledger({
                    "action": "loop_blocked",
                    "attempt": state["self_correction_count"],
                    "cps_trace_formula": generate_trace_formula(state["cps_trace"]),
                    "error": error_msg,
                    "chained_context": chained_context,
                    "message": f"Self-correction limit ({state['max_self_corrections']}) exceeded. Halting loop and spawning Chained Context (New C)."
                })
                print(f"[Ultrawork Loop] CRITICAL: Self-correction limit exceeded ({state['self_correction_count']}/{state['max_self_corrections']}).")
                print(f"[Ultrawork Loop] CPS Trace Route: {generate_trace_formula(state['cps_trace'])}")
                print(f"[Ultrawork Loop] Status set to HOLD_BLOCKED. Chained Context (New C) established: {chained_context['new_context_id']}")
                print("[Ultrawork Loop] To transition to the next chained loop, run: python3 ... transition --new-session-id <new_id>")
                return 1  # Blocked exit code
            else:
                save_state(state)
                write_ledger({
                    "action": "self_correction_retry",
                    "attempt": state["self_correction_count"],
                    "problem": p_str,
                    "solution": s_str,
                    "cps_trace_formula": generate_trace_formula(state["cps_trace"]),
                    "error": error_msg
                })
                print(f"[Ultrawork Loop] Self-correction #{state['self_correction_count']} triggered. CPS Trace: {generate_trace_formula(state['cps_trace'])}")
                return 2

def main() -> int:
    parser = argparse.ArgumentParser(description="LazyCodex Ultrawork Loop Control Engine")
    parser.add_argument("action", choices=["verify", "reset", "status", "transition"], help="Action to perform")
    parser.add_argument("--verify-cmd", help="Verification shell command to execute")
    parser.add_argument("--problem", help="CPS Problem ID (e.g. P1, P3)")
    parser.add_argument("--solution", help="CPS Solution ID (e.g. S2, S4)")
    parser.add_argument("--session-id", help="Active session ID for the run")
    parser.add_argument("--new-session-id", help="New session ID for transition")
    parser.add_argument("--new-problem", help="Initial problem ID for the transitioned session")
    parser.add_argument("--new-solution", help="Initial solution ID for the transitioned session")
    args = parser.parse_args()

    if args.action == "reset":
        state = {
            "session_id": args.session_id or "session_harness_default",
            "status": "INIT",
            "current_step": "explore",
            "self_correction_count": 0,
            "max_self_corrections": 2,
            "error_history": [],
            "cps_trace": ["C"],
            "last_error": None,
            "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        }
        save_state(state)
        write_ledger({"action": "reset", "message": "Ultrawork loop state reset to initial."})
        print("[Ultrawork Loop] Loop state successfully reset.")
        return 0

    elif args.action == "status":
        state = load_state()
        print(f"Session ID:         {state['session_id']}")
        print(f"Loop Status:        {state['status']}")
        print(f"Correction Count:   {state['self_correction_count']}/{state['max_self_corrections']}")
        print(f"CPS Trace Formula:  {generate_trace_formula(state['cps_trace'])}")
        print(f"Last Error:         {state['last_error']}")
        if "chained_context" in state:
            print(f"Chained Context:    {state['chained_context']['new_context_id']} (Status: {state['chained_context']['remediation_status']})")
        return 0

    elif args.action == "transition":
        state = load_state()
        if state["status"] != "HOLD_BLOCKED":
            print(f"[Ultrawork Loop] Error: Cannot transition from status '{state['status']}'. Status must be 'HOLD_BLOCKED'.")
            return 3
        
        chained_ctx = state.get("chained_context")
        if not chained_ctx:
            print("[Ultrawork Loop] Error: No chained_context metadata found in the current state.")
            return 4
            
        new_sess_id = args.new_session_id or chained_ctx.get("suggested_next_session_id") or "session_harness_chained"
        
        # Build the transitioned state inheriting the parent context
        parent_trace = chained_ctx.get("inherited_cps_trace", ["C"])
        new_context_marker = chained_ctx.get("new_context_id", f"C_CHAINED_FROM_{state['session_id']}")
        
        new_trace = [new_context_marker]
        if args.new_problem:
            new_trace.append(args.new_problem)
        if args.new_solution:
            new_trace.append(args.new_solution)
            
        new_state = {
            "session_id": new_sess_id,
            "status": "INIT",
            "current_step": "explore",
            "self_correction_count": 0,
            "max_self_corrections": 2,
            "error_history": state.get("error_history", []) + [{
                "session_id": state["session_id"],
                "last_error": chained_ctx.get("inherited_last_error"),
                "cps_trace": parent_trace
            }],
            "cps_trace": new_trace,
            "parent_session_info": {
                "session_id": state["session_id"],
                "cps_trace": parent_trace,
                "last_error": chained_ctx.get("inherited_last_error")
            },
            "last_error": None,
            "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        }
        save_state(new_state)
        
        write_ledger({
            "action": "transition",
            "parent_session_id": state["session_id"],
            "new_session_id": new_sess_id,
            "new_cps_trace_formula": generate_trace_formula(new_trace),
            "message": f"Successfully transitioned to a new chained loop: {new_sess_id} representing New C."
        })
        
        print(f"[Ultrawork Loop] Successfully transitioned from {state['session_id']} (HOLD_BLOCKED) to {new_sess_id} (INIT).")
        print(f"[Ultrawork Loop] New Context (New C) established. CPS Trace: {generate_trace_formula(new_trace)}")
        return 0

    elif args.action == "verify":
        if not args.verify_cmd:
            parser.error("--verify-cmd is required for 'verify' action")
            
        code, stdout = run_oracle_verification(args.verify_cmd)
        success = (code == 0)
        error_msg = None if success else f"Exit code {code}. Output:\n{stdout}"
        
        return handle_verification_result(
            success=success,
            error_msg=error_msg,
            verify_cmd=args.verify_cmd,
            problem_id=args.problem,
            solution_id=args.solution
        )

    return 0

if __name__ == "__main__":
    sys.exit(main())
