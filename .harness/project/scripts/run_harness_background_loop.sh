#!/usr/bin/env bash
# run_harness_background_loop.sh
# Automates the Honcho & GBrain background processes for the Harness task lifecycle.
# Equipped with strict boundary controls and audit logging.

set -euo pipefail

# Path setup
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
PYTHON_EXEC="/Users/kann/.hermes/hermes-agent/.venv/bin/python"
HERMES_AGENT_ROOT="/Users/kann/.hermes/hermes-agent"

# Environment configuration
export HERMES_HONCHO_HOST="hermes_anubis"

# Directories
RUNS_DIR="${REPO_DIR}/.harness/project/runs"
REPORTS_DIR="${REPO_DIR}/.harness/project/reports"
LOG_FILE="${RUNS_DIR}/background_audit.log"

mkdir -p "${RUNS_DIR}" "${REPORTS_DIR}"

# Helper to log audits (AC-4)
log_audit() {
    local action="$1"
    local exit_code="$2"
    local message="$3"
    local timestamp
    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    # Write structured audit log without leaking any secrets
    echo "{\"timestamp\": \"${timestamp}\", \"action\": \"${action}\", \"exit_code\": ${exit_code}, \"message\": \"${message}\"}" >> "${LOG_FILE}"
}

# Helper to execute command and audit it
run_step() {
    local name="$1"
    shift
    local cmd=("$@")
    
    echo "[Harness Background] Running: ${name}..."
    
    # Run command and capture output safely
    local exit_code=0
    set +e
    # Run command, ensuring we don't leak secrets in logs
    "${cmd[@]}" > "${RUNS_DIR}/last_${name}.log" 2>&1
    exit_code=$?
    set -e
    
    if [ ${exit_code} -eq 0 ]; then
        echo "[Harness Background] ${name} completed successfully."
        log_audit "${name}" "${exit_code}" "Success"
    else
        echo "[Harness Background] ERROR: ${name} failed with exit code ${exit_code}."
        log_audit "${name}" "${exit_code}" "Failed. Check last_${name}.log for details."
        return ${exit_code}
    fi
}

show_usage() {
    echo "Usage: $0 [init|check|close|all|daemon] [session_id] [options...]"
    echo "  init   - Seeds Honcho context and ingests pending manifests (AC-1)"
    echo "  check  - Performs drift detection and writes structured report (AC-2)"
    echo "  close  - Performs final writeback and gateway cleanup (AC-3)"
    echo "  daemon - Runs init and check periodically in a background loop"
    echo "  all    - Runs all phases sequentially"
}

if [ $# -lt 2 ]; then
    show_usage
    exit 1
fi

ACTION="$1"
SESSION_ID="$2"
shift 2

# Additional arguments for writeback
WRITEBACK_ARGS=("$@")

case "${ACTION}" in
    init)
        # AC-1: Seeding & Ingestion
        run_step "seed-context" "${PYTHON_EXEC}" "${SCRIPT_DIR}/router/seed_honcho_project_context.py" --honcho-session-key "${SESSION_ID}" --hermes-agent-root "${HERMES_AGENT_ROOT}" --repo "${REPO_DIR}"
        run_step "ingest-manifests" "${PYTHON_EXEC}" "${SCRIPT_DIR}/router/honcho_background_worker.py" --action ingest --honcho-session-key "${SESSION_ID}" --hermes-agent-root "${HERMES_AGENT_ROOT}" --repo "${REPO_DIR}"
        ;;
        
    check)
        # AC-2: Drift Detection & Reporting
        echo "[Harness Background] Running check-drift..."
        exit_code=0
        set +e
        "${PYTHON_EXEC}" "${SCRIPT_DIR}/router/honcho_background_worker.py" --action check-drift --honcho-session-key "${SESSION_ID}" --hermes-agent-root "${HERMES_AGENT_ROOT}" --repo "${REPO_DIR}" > "${REPORTS_DIR}/drift_report_${SESSION_ID}.txt" 2>&1
        exit_code=$?
        set -e
        
        if [ ${exit_code} -eq 0 ]; then
            echo "[Harness Background] Drift check completed. Report written to ${REPORTS_DIR}/drift_report_${SESSION_ID}.txt"
            cat "${REPORTS_DIR}/drift_report_${SESSION_ID}.txt"
            log_audit "check-drift" "${exit_code}" "Drift report successfully generated"
        else
            echo "[Harness Background] ERROR: Drift check failed with exit code ${exit_code}."
            log_audit "check-drift" "${exit_code}" "Failed to run drift check"
            exit ${exit_code}
        fi
        ;;
        
    close)
        # AC-3: Writeback & Gateway Cleanup
        run_step "writeback" "${PYTHON_EXEC}" "${SCRIPT_DIR}/router/honcho_background_worker.py" --action writeback --session-id "${SESSION_ID}" --hermes-agent-root "${HERMES_AGENT_ROOT}" --repo "${REPO_DIR}" ${WRITEBACK_ARGS[@]+"${WRITEBACK_ARGS[@]}"}
        ;;
        
    all)
        # Sequence of all actions for a full lifecycle
        # We invoke this script itself recursively
        "${SCRIPT_DIR}/run_harness_background_loop.sh" init "${SESSION_ID}"
        "${SCRIPT_DIR}/run_harness_background_loop.sh" check "${SESSION_ID}"
        "${SCRIPT_DIR}/run_harness_background_loop.sh" close "${SESSION_ID}" ${WRITEBACK_ARGS[@]+"${WRITEBACK_ARGS[@]}"}
        ;;
        
    daemon)
        INTERVAL="${1:-60}"
        echo "[Harness Background] Starting daemon with interval ${INTERVAL}s for session ${SESSION_ID}..."
        log_audit "daemon-start" 0 "Daemon started with interval ${INTERVAL}s"
        
        terminate_daemon() {
            echo "[Harness Background] Terminating daemon..."
            log_audit "daemon-stop" 0 "Daemon stopped gracefully"
            exit 0
        }
        trap terminate_daemon SIGINT SIGTERM
        
        while true; do
            echo "[Harness Background] Daemon cycle start: $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
            set +e
            "${SCRIPT_DIR}/run_harness_background_loop.sh" init "${SESSION_ID}"
            INIT_EC=$?
            "${SCRIPT_DIR}/run_harness_background_loop.sh" check "${SESSION_ID}"
            CHECK_EC=$?
            set -e
            
            log_audit "daemon-cycle" 0 "Daemon cycle completed. init_exit_code=${INIT_EC}, check_exit_code=${CHECK_EC}"
            echo "[Harness Background] Daemon cycle complete. Sleeping for ${INTERVAL}s..."
            
            sleep "${INTERVAL}" &
            wait $!
        done
        ;;
        
    *)
        show_usage
        exit 1
        ;;
esac
