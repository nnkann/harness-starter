#!/usr/bin/env python3
"""Harness Lifecycle Orchestrator Runner & Agent Delegation Automation.
Automates task session lifecycles (init, check, close) and routes tasks to appropriate Hermes profiles.
"""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
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
SCRIPTS_DIR = REPO_ROOT / ".harness" / "project" / "scripts"
ROUTER_DIR = SCRIPTS_DIR / "router"
LOG_FILE = REPO_ROOT / ".harness" / "project" / "runs" / "background_audit.log"

# Fallback paths from environment or standard locations
HERMES_AGENT_ROOT = Path(os.environ.get("HERMES_AGENT_ROOT", Path.home() / ".hermes/hermes-agent"))
# Try to find python executable from hermes agent venv, fallback to current python
DEFAULT_PYTHON = Path("/Users/kann/.hermes/hermes-agent/.venv/bin/python")
PYTHON_EXEC = DEFAULT_PYTHON if DEFAULT_PYTHON.exists() else Path(sys.executable)

def log_audit(action: str, exit_code: int, message: str) -> None:
    """Write structured audit log to keep compatibility with bash runner."""
    timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    log_entry = {
        "timestamp": timestamp,
        "action": action,
        "exit_code": exit_code,
        "message": message
    }
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry) + "\n")

def run_command_with_audit(name: str, cmd: list[str], cwd: Path) -> int:
    """Run a command, capture output, and write audit log."""
    print(f"[Harness Lifecycle] Running: {name}...")
    try:
        # Run command, capturing stdout and stderr
        result = subprocess.run(
            cmd,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False
        )
        # Save last log to runs dir
        log_dir = REPO_ROOT / ".harness" / "project" / "runs"
        log_dir.mkdir(parents=True, exist_ok=True)
        last_log = log_dir / f"last_{name}.log"
        last_log.write_text(result.stdout, encoding="utf-8")
        
        if result.returncode == 0:
            print(f"[Harness Lifecycle] {name} completed successfully.")
            log_audit(name, 0, "Success")
            return 0
        else:
            print(f"[Harness Lifecycle] ERROR: {name} failed with exit code {result.returncode}.")
            # Print last few lines of log
            lines = result.stdout.strip().splitlines()
            snippet = "\n".join(lines[-10:]) if len(lines) > 10 else result.stdout
            print(f"--- Log Snippet ---\n{snippet}\n-------------------")
            log_audit(name, result.returncode, f"Failed. Check last_{name}.log for details.")
            return result.returncode
    except Exception as e:
        print(f"[Harness Lifecycle] ERROR: Exception while running {name}: {e}")
        log_audit(name, -1, f"Failed with exception: {e}")
        return -1

def load_packet(packet_path: Path) -> dict[str, Any]:
    """Load task packet supporting both JSON and YAML if pyyaml is installed."""
    if not packet_path.exists():
        raise FileNotFoundError(f"Task packet not found at: {packet_path}")
    
    raw = packet_path.read_text(encoding="utf-8")
    if packet_path.suffix.lower() == ".json":
        return json.loads(raw)
        
    try:
        import yaml
        return yaml.safe_load(raw) or {}
    except ImportError:
        # Dependency-free fallback parser for YAML (extract basic fields)
        data: dict[str, Any] = {}
        current_key = None
        for line in raw.splitlines():
            line_strip = line.strip()
            if not line_strip or line_strip.startswith("#"):
                continue
            if not line.startswith(" ") and ":" in line:
                key, _, val = line.partition(":")
                current_key = key.strip()
                val_strip = val.strip()
                if val_strip:
                    data[current_key] = val_strip
                else:
                    data[current_key] = []
            elif line.startswith(" ") and current_key in data and isinstance(data[current_key], list):
                # Simple list element extraction
                if line_strip.startswith("-"):
                    data[current_key].append(line_strip[1:].strip())
        return data

def route_task_packet(packet_data: dict[str, Any]) -> dict[str, Any]:
    """Analyze CPS and other metadata in a task packet to route it to the optimal profile."""
    # Look at CPS C, P, S
    cps = packet_data.get("CPS", {})
    c_list = cps.get("C", []) if isinstance(cps.get("C"), list) else [str(cps.get("C") or "")]
    p_list = cps.get("P", []) if isinstance(cps.get("P"), list) else [str(cps.get("P") or "")]
    s_list = cps.get("S", []) if isinstance(cps.get("S"), list) else [str(cps.get("S") or "")]
    
    c_text = " ".join(map(str, c_list)).lower()
    p_text = " ".join(map(str, p_list)).lower()
    s_text = " ".join(map(str, s_list)).lower()
    
    # Check other fields
    task_ac_list = packet_data.get("task_AC", [])
    task_ac = " ".join(map(str, task_ac_list if isinstance(task_ac_list, list) else [task_ac_list])).lower()
    
    goal = str(packet_data.get("root_goal", "") or packet_data.get("goal", "")).lower()
    
    all_text = f"{c_text} {p_text} {s_text} {task_ac} {goal}"
    
    # Scored mapping based on domain keywords
    scores = {
        "seshat": 0,             # docs-operator
        "ptah": 0,               # coder
        "anubis": 0,             # reviewer / lifecycle / cleanup
        "sekhmet": 0,            # threat-guard
        "researcher": 0,         # researcher
        "thoth": 0,              # orchestrator
        "maat": 0,               # moderator
        "sia": 0,                # cognitive-analyzer
    }
    
    # seshat: docs, markdown, frontmatter, document, manifest, required_docs, doc_ops, wiki, digest
    for word in ["doc", "markdown", "frontmatter", "manifest", "required_docs", "doc_ops", "wiki", "digest"]:
        if word in all_text:
            scores["seshat"] += 3
            
    # ptah: code, implement, test, refactor, script, python, execution, bug, algorithm, feature, backend, database
    for word in ["code", "implement", "test", "refactor", "script", "python", "execution", "bug", "algorithm", "feature", "backend", "database", "compile"]:
        if word in all_text:
            scores["ptah"] += 3
            
    # anubis: review, audit, check, verify, compliance, cleanup, close, gateway, snapshot, writeback, completion, gate
    for word in ["review", "audit", "check", "verify", "compliance", "cleanup", "close", "gateway", "snapshot", "writeback", "completion", "gate"]:
        if word in all_text:
            scores["anubis"] += 3
            
    # sekhmet: security, threat, permission, secret, safe, sandbox, auth, exposure, credentials, policy, restrict
    for word in ["security", "threat", "permission", "secret", "safe", "sandbox", "auth", "exposure", "credentials", "policy", "restrict"]:
        if word in all_text:
            scores["sekhmet"] += 3
            
    # researcher: research, external, freshest, crawl, api, spider, scrape, internet, search, fact, source
    for word in ["research", "external", "freshest", "crawl", "api", "spider", "scrape", "internet", "search", "fact", "source"]:
        if word in all_text:
            scores["researcher"] += 3
            
    # thoth: coordinate, triage, route, compile-contract, fan-out, planning, coordination
    for word in ["coordinate", "triage", "route", "compile-contract", "fan-out", "planning", "coordination"]:
        if word in all_text:
            scores["thoth"] += 3
            
    # maat: gate, approve, judge, moderator, final-gate, criteria
    for word in ["gate", "approve", "judge", "moderator", "final-gate", "criteria"]:
        if word in all_text:
            scores["maat"] += 3

    # sia: cognitive, perception, diagnose, diagnostics, reasoning, analysis, low-token, memory-only
    for word in ["cognitive", "perception", "diagnose", "diagnostics", "reasoning", "analysis", "low-token", "memory-only"]:
        if word in all_text:
            scores["sia"] += 3
 
    # Resolve highest scoring profile
    best_profile = max(scores, key=scores.get)
    if scores[best_profile] == 0:
        # default fallback
        best_profile = "ptah"
        
    profile_details = {
        "seshat": {"role": "docs-operator", "deity": "seshat", "desc": "Handles documents, frontmatter, required-docs, and Honcho digests."},
        "ptah": {"role": "coder", "deity": "ptah", "desc": "Handles code implementation, testing, refactoring, and execution."},
        "anubis": {"role": "reviewer", "deity": "anubis", "desc": "Handles review, compliance, lifecycle cleanup, and snapshots."},
        "sekhmet": {"role": "threat-guard", "deity": "sekhmet", "desc": "Handles sandbox policy, secrets, permissions, and threat guarding."},
        "researcher": {"role": "researcher", "deity": "imhotep", "desc": "Handles external facts, searches, and documentation research."},
        "thoth": {"role": "orchestrator", "deity": "thoth", "desc": "Handles triage, task routing, and coordinating handoffs."},
        "maat": {"role": "moderator", "deity": "maat", "desc": "Handles gating, final approvals, and compliance verification."},
        "sia": {"role": "cognitive-analyzer", "deity": "sia", "desc": "Handles low-token cognitive analysis, diagnostics, perception, and reasoning-review."}
    }
    
    details = profile_details[best_profile]
    return {
        "selected_profile": best_profile,
        "role": details["role"],
        "deity": details["deity"],
        "description": details["desc"],
        "scores": scores,
        "rationale": f"Profile '{best_profile}' selected with a score of {scores[best_profile]} matching keywords in the task packet."
    }

def do_init(session_id: str, manifest: str | None) -> int:
    """AC-1: Seed Honcho context, ingest pending manifests, and trigger LazyCodex wiki/research."""
    print("=== Phase: Init (Seeding & Ingestion with LazyCodex) ===")
    
    # Step 1: Seeding
    seed_script = ROUTER_DIR / "seed_honcho_project_context.py"
    seed_cmd = [
        str(PYTHON_EXEC),
        str(seed_script),
        "--honcho-session-key", session_id,
        "--hermes-agent-root", str(HERMES_AGENT_ROOT),
        "--repo", str(REPO_ROOT)
    ]
    ret = run_command_with_audit("seed-context", seed_cmd, REPO_ROOT)
    if ret != 0:
        return ret
        
    # Step 2: Ingest manifests
    worker_script = ROUTER_DIR / "honcho_background_worker.py"
    ingest_cmd = [
        str(PYTHON_EXEC),
        str(worker_script),
        "--action", "ingest",
        "--honcho-session-key", session_id,
        "--hermes-agent-root", str(HERMES_AGENT_ROOT),
        "--repo", str(REPO_ROOT)
    ]
    if manifest:
        ingest_cmd.extend(["--manifest", manifest])
        
    ret = run_command_with_audit("ingest-manifests", ingest_cmd, REPO_ROOT)
    if ret != 0:
        return ret

    # Step 3: LazyCodex doc_ops Wiki Indexing
    print("[Harness Lifecycle] Ingesting domain abbreviations into LLM Wiki...")
    wiki_script = REPO_ROOT / ".harness" / "hermes" / "tools" / "lazycodex_doc_ops_wiki.py"
    if wiki_script.exists():
        wiki_cmd = [str(PYTHON_EXEC), str(wiki_script), "CPS"]
        run_command_with_audit("wiki-index", wiki_cmd, REPO_ROOT)

    # Step 4: Asynchronous Swarm Research (Triggered if GITHUB_TOKEN is present)
    research_script = REPO_ROOT / ".harness" / "hermes" / "tools" / "lazycodex_swarm_research.py"
    if research_script.exists() and os.environ.get("GITHUB_TOKEN"):
        print("[Harness Lifecycle] Triggering background Swarm Research...")
        research_cmd = [
            str(PYTHON_EXEC),
            str(research_script),
            "--repo", "code-yeongyu/lazycodex",
            "--query", "lifecycle init auto"
        ]
        # Run asynchronously to avoid blocking init phase
        try:
            subprocess.Popen(
                research_cmd,
                cwd=str(REPO_ROOT),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print("[Harness Lifecycle] Swarm Research launched in background.")
        except Exception as e:
            print(f"[Harness Lifecycle] Failed to launch Swarm Research: {e}")

    return 0

def do_check(session_id: str, manifest: str | None) -> int:
    """AC-2: Drift Detection, Static Clean & Slim Compliance, and Reporting."""
    print("=== Phase: Check (Drift Detection & Clean/Slim Compliance) ===")
    worker_script = ROUTER_DIR / "honcho_background_worker.py"
    check_cmd = [
        str(PYTHON_EXEC),
        str(worker_script),
        "--action", "check-drift",
        "--honcho-session-key", session_id,
        "--hermes-agent-root", str(HERMES_AGENT_ROOT),
        "--repo", str(REPO_ROOT)
    ]
    if manifest:
        check_cmd.extend(["--manifest", manifest])
        
    # Run the check-drift action
    print(f"[Harness Lifecycle] Running check-drift...")
    result = subprocess.run(
        check_cmd,
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False
    )
    
    drift_output = result.stdout
    drift_exit_code = result.returncode

    # Run Clean & Slim Audit
    print("[Harness Lifecycle] Running Clean & Slim compliance check...")
    audit_script = REPO_ROOT / ".harness" / "hermes" / "tools" / "audit_clean_slim.py"
    audit_output = ""
    audit_exit_code = 0
    if audit_script.exists():
        audit_cmd = [
            str(PYTHON_EXEC),
            str(audit_script),
            "--path", str(REPO_ROOT / ".harness" / "hermes" / "tools")
        ]
        audit_result = subprocess.run(
            audit_cmd,
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False
        )
        audit_output = audit_result.stdout
        audit_exit_code = audit_result.returncode

    # Combine reports
    reports_dir = REPO_ROOT / ".harness" / "project" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_file = reports_dir / f"drift_report_{session_id}.txt"

    combined_report = []
    combined_report.append("=========================================")
    combined_report.append("HARNESS INTEGRATED LIFECYCLE CHECK REPORT")
    combined_report.append(f"Session ID: {session_id}")
    combined_report.append(f"Timestamp: {datetime.now().isoformat()}")
    combined_report.append("=========================================\n")
    
    combined_report.append("### 1. HONCHO DRIFT DETECTION")
    combined_report.append(f"Exit Code: {drift_exit_code}")
    combined_report.append(drift_output)
    combined_report.append("\n-----------------------------------------\n")
    
    combined_report.append("### 2. CLEAN & SLIM STATIC AUDIT")
    combined_report.append(f"Exit Code: {audit_exit_code}")
    combined_report.append(audit_output if audit_output else "Audit script not executed or no output.")
    
    report_content = "\n".join(combined_report)
    report_file.write_text(report_content, encoding="utf-8")
    
    # Save last check log
    log_dir = REPO_ROOT / ".harness" / "project" / "runs"
    log_dir.mkdir(parents=True, exist_ok=True)
    last_log = log_dir / "last_check-drift.log"
    last_log.write_text(report_content, encoding="utf-8")

    if drift_exit_code == 0 and audit_exit_code == 0:
        print(f"[Harness Lifecycle] Integrated check completed. Report written to {report_file.relative_to(REPO_ROOT)}")
        print(report_content)
        log_audit("check-drift", 0, "Integrated drift and clean/slim report successfully generated")
        return 0
    else:
        print(f"[Harness Lifecycle] ERROR: Integrated check failed (Drift: {drift_exit_code}, Audit: {audit_exit_code}).")
        # Print snippet of failures
        failures = []
        if drift_exit_code != 0:
            failures.append("Honcho Drift Detection Failed")
        if audit_exit_code != 0:
            failures.append("Clean & Slim Static Audit Failed (Compliance issues detected)")
        log_audit("check-drift", -1, f"Integrated check failed: {', '.join(failures)}")
        return -1

def do_close(session_id: str, writeback_args: list[str]) -> int:
    """AC-3: Writeback & Gateway Cleanup."""
    print("=== Phase: Close (Writeback & Gateway Cleanup) ===")
    worker_script = ROUTER_DIR / "honcho_background_worker.py"
    close_cmd = [
        str(PYTHON_EXEC),
        str(worker_script),
        "--action", "writeback",
        "--session-id", session_id,
        "--hermes-agent-root", str(HERMES_AGENT_ROOT),
        "--repo", str(REPO_ROOT)
    ]
    # Parse writeback specific options from writeback_args if they are passed
    close_cmd.extend(writeback_args)
    
    return run_command_with_audit("writeback", close_cmd, REPO_ROOT)

def do_delegate(packet_path: str) -> int:
    """Analyze a task packet and determine the optimal agent delegation."""
    print("=== Agent Delegation & Role Routing ===")
    p_path = Path(packet_path)
    if not p_path.is_absolute():
        p_path = REPO_ROOT / p_path
        
    try:
        packet_data = load_packet(p_path)
    except Exception as e:
        print(f"ERROR: Failed to load task packet: {e}")
        return 1
        
    routing = route_task_packet(packet_data)
    
    print("\n--- Delegation Decision ---")
    print(f"Target Packet: {p_path.relative_to(REPO_ROOT)}")
    print(f"Selected Profile: {routing['selected_profile']}")
    print(f"Role Archetype:   {routing['role']}")
    print(f"Deity Binding:    {routing['deity']}")
    print(f"Description:     {routing['description']}")
    print(f"Rationale:       {routing['rationale']}")
    print("\nScores:")
    for profile, score in sorted(routing['scores'].items(), key=lambda x: x[1], reverse=True):
        print(f"  - {profile:18}: {score}")
    print("---------------------------\n")
    
    # Output delegation JSON for machine parsing
    decision_file = REPO_ROOT / ".harness" / "project" / "runs" / "delegation_decision.json"
    decision_file.parent.mkdir(parents=True, exist_ok=True)
    decision_file.write_text(json.dumps(routing, indent=2), encoding="utf-8")
    print(f"Delegation decision saved to {decision_file.relative_to(REPO_ROOT)}")
    return 0

def main() -> int:
    parser = argparse.ArgumentParser(description="Harness Lifecycle Orchestrator & Delegation Runner")
    parser.add_argument("action", choices=["init", "check", "close", "all", "delegate"], help="Lifecycle phase or delegation action")
    parser.add_argument("--session-id", help="Honcho session key or ID")
    parser.add_argument("--packet", help="Path to the task packet (required for 'delegate')")
    parser.add_argument("--manifest", help="Custom path to Honcho ingest manifest")
    
    # Capture all remaining arguments to pass to writeback or scripts
    args, unknown = parser.parse_known_args()
    
    # Resolve or generate session ID
    session_id = args.session_id
    if not session_id:
        if args.packet:
            try:
                packet_data = load_packet(Path(args.packet))
                session_id = packet_data.get("run_id") or packet_data.get("flow_graph_id")
            except Exception:
                pass
        if not session_id:
            session_id = os.environ.get("HERMES_KANBAN_RUN_ID") or "session_harness_auto"
            
    # Perform actions
    if args.action == "init":
        return do_init(session_id, args.manifest)
    elif args.action == "check":
        return do_check(session_id, args.manifest)
    elif args.action == "close":
        return do_close(session_id, unknown)
    elif args.action == "all":
        ret = do_init(session_id, args.manifest)
        if ret != 0:
            return ret
        ret = do_check(session_id, args.manifest)
        if ret != 0:
            return ret
        return do_close(session_id, unknown)
    elif args.action == "delegate":
        if not args.packet:
            parser.error("--packet is required when action is 'delegate'")
        return do_delegate(args.packet)
        
    return 0

if __name__ == "__main__":
    sys.exit(main())
