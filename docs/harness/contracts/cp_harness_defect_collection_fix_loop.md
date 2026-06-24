---
title: cp_harness_defect_collection_fix_loop
description: Defect collection and fix loop contract for decoupled upstream/downstream Harness systems
domain: harness/contracts
status: active
c: cp_harness_defect_collection_fix_loop
problem:
  - P1: Downstream defect detection causing runtime deadlocks or infinite retry loops during active sessions.
  - P2: Lack of structured evidence and trace logs when collecting downstream runtime failures.
  - P3: Unvalidated patches introduced during hotfixes compromising the integrity of the upstream reference.
s:
  - S1: Enforce a strict decoupled one-way collection loop with a 2-retry limit and Fail-Fast hold state.
  - S2: Require structured incident reports containing a maximum of 20 lines of log, CWD, and reproduction steps.
  - S3: Mandate running loader.py validate-reference as a physical gate before promoting any hotfix to the reference.
tags:
  - defect-loop
  - hotfix
  - decoupling
  - diagnostics
relates-to:
  - docs/harness/contracts/cp_owner_approval_boundary.md
  - docs/harness/contracts/cp_cps_evidence_acquisition.md
owner_approval_boundary:
  - no hotfix branch creation without owner approval
  - no direct commit or push to the baseline branch without validation passing
prohibited_actions:
  - propagating downstream runtime errors directly into the upstream repository without quarantine
  - running more than 2 consecutive automated retries for the same runtime failure
---

# Harness Defect Collection and Fix Loop Contract

## 1. Context (C)
This contract governs the physical boundaries and communication mechanisms when defects are discovered in the downstream runtime environment. Under the decoupled architecture, the downstream runtime and the upstream reference remain completely isolated. When a runtime deviation or a system failure is detected, the downstream agent must not attempt invasive runtime modifications. Instead, it must invoke a structured, one-way **Collection/Fix Loop** to report, quarantine, analyze, and remediate the defect.

---

## 2. Problems & Solutions Matrix

### Problems

| ID | Title | Description |
|---|---|---|
| **P1** | Downstream Runtime Deadlocks | Automated repair attempts or recursive retry loops during active sessions cause token exhaustion and rate limits (429). |
| **P2** | Unstructured Evidence Collection | Missing or unstructured diagnostic logs make root cause analysis difficult and delay incident recovery. |
| **P3** | Upstream Reference Regression | Introducing unvalidated patches to resolve hotfixes corrupts the upstream reference configuration. |

### Solutions

| ID | Title | Description | Relates To |
|---|---|---|---|
| **S1** | Decoupled Quarantine & Fail-Fast | Limit consecutive self-correction retries to **2**. If the failure persists, enter a hard `HOLD` state, quarantine the session, and notify the owner. | **P1** |
| **S2** | Structured Incident Reporting | Generate a standardized incident artifact containing exactly the CWD, environment variables, reproduction steps, and a maximum of 20 lines of error trace. | **P2** |
| **S3** | Upstream Validation Gate | Run the physical verification tool `python3 .harness/hermes/loader.py validate-reference` before merging or applying any hotfix patches. | **P3** |

---

## 3. Actor Bindings & Responsibilities

The defect collection and fix loop is executed by two specialized role archetypes to ensure separation of concerns:

### Moderator (`maat`)
* **Trigger**: Any downstream task execution encountering 2 consecutive failures or a critical exception.
* **Responsibility**:
  1. Enforces the `HOLD` gate and blocks further automated tool execution.
  2. Generates the structured Incident Report in the `incidents/` directory.
  3. Formulates the next steps and requests explicit owner approval.
  4. Audits the final fix against the original task acceptance criteria (AC).

### Coder (`ptah`)
* **Trigger**: Owner approval of the quarantine remediation plan.
* **Responsibility**:
  1. Creates a isolated hotfix branch (never direct mutation on `main`).
  2. Implements the targeted correction strictly within the approved write scope.
  3. Executes the physical self-diagnosis command:
     ```bash
     python3 .harness/hermes/loader.py validate-reference
     ```
  4. Merges the validated hotfix back to the approved baseline branch upon successful check.

---

## 4. Execution Guardrails

1. **Strict Failure Log Hygiene**: Under no circumstances should complete logs, tracebacks, or raw stdout be printed to the console or chat logs. On failure, extract a maximum of 20 lines of the relevant error, save the full log output to a local artifact file, and report only the file path.
2. **Prevent Compression Loops**: If a session's token footprint becomes extremely large, do not attempt to trigger self-healing compression or summary loops. Halt execution immediately and instruct the user to start a new session (`/new`) or reset the context.
3. **No Fallback Execution**: Unresolved assignees or role-only names must be blocked immediately by `maat`. Every runnable task must be explicitly mapped to a concrete selectable profile.
