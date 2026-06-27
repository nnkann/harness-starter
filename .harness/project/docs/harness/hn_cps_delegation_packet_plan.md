---
title: Harness CPS delegation packet rewrite plan
description: Compact rewrite plan plus CPS semantic E2E failure correction for the owner-approved packet/doc task.
domain: harness/goals
status: draft
owner: seshat_doc_ops_fix
c: Keep delegation packets compact and prove C/P/S/AC semantics, not just JSON output.
problem: Prior smoke checks passed file shapes while missing live Maat C-boundary, Thoth compile, and CPS equation trace.
s: seshat_doc_ops_fix
tags: [harness, cps, delegation, doc_ops, packet, e2e]
owner_approval_boundary:
  implementation_scope: owner-approved packet and planning-doc edits only
  commit: explicit owner approval required
  push: explicit owner approval required
prohibited_actions:
  - full prompt bundling
  - execution dump inclusion
  - default acting as Maat or Thoth
  - git add
  - git commit
  - git push
freshness:
  updated_at: 2026-06-26
source_refs:
  - path: /Users/kann/projects/harness-starter/.harness/project/runs/_template/cps_packet.yaml
    freshness: 2026-06-26 edited
    confidence: High
    reason: Active packet template updated to include semantic CPS checks.
  - path: /Users/kann/projects/harness-brain/projects/harness-starter/contracts/cp-cps-preflight-route-gate.md
    freshness: 2026-06-26 edited
    confidence: High
    reason: Contract records live Maat -> Thoth ping-pong requirement.
constraints:
  - Keep this plan under 120 lines.
  - Deterministic checks are evidence only; Maat owns PASS/WARN/FAIL.
  - A route JSON/probe count is not E2E success without a CPS trace.
  - Default may draft C_candidate/frontmatter only; it must not plan, adjudicate, or compile.
---

# Objective
Fix the packet/doc shape and record the failed first E2E lesson: CPS semantic trace is the test center.

# Correct orchestration
```text
Hermes-kann/default drafts C_candidate/CPS frontmatter
→ Maat live-adjudicates C-boundary, gaps, audit scope, candidate_agents
→ Hermes-kann sends each candidate a role-local draft_CPS probe, not the Maat draft or a shared prompt
→ Probe responses are gathered as they arrive and summarized for a Maat reducer
→ Accepted agents receive only Maat-approved local C/P#/S#/AC and contribute CPS
→ Maat↔agent ping-pong handles HOLD_GAP/REVISE until settled
→ Maat final audits S# outputs against AC and Goal closure
```

# Explicit failure record
```text
FAIL_CPS_SEMANTIC_ABSENCE: JSON/probe counts exist without live Maat, agent probe, CPS trace, or final AC judgment.
FAIL_MISSING_LIVE_MAAT_C_BOUNDARY: default or deterministic code replaced live Maat adjudication.
FAIL_MISSING_THOTH_COMPILE: Maat-selected Thoth compile artifact is absent.
FAIL_MISSING_MAAT_FINAL_AC_JUDGMENT: no final Maat judgment ties S# outputs to AC and Goal closure.
```

# Required CPS trace table
```yaml
C:
  candidate: <default draft>
  maat_verdict: PASS_ONE_C|SPLIT|HOLD
  final_C: <Maat-approved C>
P:
  P1: {received_by: thoth, input: <bounded input>, order: 1, status: open|closed}
S:
  S1: {operator: thoth_compile, consumes: [P1], output_ref: <artifact>, status: pass|hold|fail}
E:
  - P1 -> S1
AC:
  AC1: {judges: S1.output_ref, verdict: PASS|WARN|FAIL, evidence_ref: <path>}
Goal:
  closure: PASS|WARN|FAIL
Goal.closure: explicit PASS|WARN|FAIL field required for semantic E2E
```


# Probe fan-out rule
```yaml
agent_draft_probe:
  agent: thoth
  draft_CPS: {C: {}, P: {}, S: {}, E: [], AC: {}, Goal: "frontmatter-only role probe"}
role_response:
  response: ACCEPT|REJECT|NEED_LOCAL_BODY|HOLD
  fitted_C: {}
  missing: []
maat_reducer_input:
  mode: as_arrives
  do_not_wait_for_all_optional: true
```

# Rewrite intent
1. Keep P#/S# compact and operator-routable.
2. Add semantic checks for C-boundary, P→S edges, AC judgment, and Goal closure.
3. Treat deterministic validators as evidence generators only.
4. Mark deterministic route-gate-only output as smoke evidence, not E2E PASS.
5. Require live Maat and Thoth lane artifacts for E2E success.

# E2E acceptance criteria
- AC1: Maat live output exists with C-boundary and selected agent decision.
- AC2: Thoth output exists and preserves Maat-approved C/P#/S#/AC.
- AC3: Every P# has a mapped S# and ordered P→S edge.
- AC4: Every S# output has an AC judgment by Maat.
- AC5: Goal closure is explicitly PASS/WARN/FAIL.
- AC6: `FAIL_CPS_SEMANTIC_ABSENCE` triggers when only JSON/probe counts are present.
- AC7: default-authored plans are rejected unless Maat delegated planning to Thoth.

# Deferred follow-up
Runtime remains HOLD until live Maat reducer + contribute CPS + final AC judgment are implemented.
