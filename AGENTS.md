# Harness-starter Hermes adapter baseline context

This repository's active Harness/Hermes SSOT branch is `hermes/harness-starter-baseline`.

## Canonical operating rule

- `hermes/harness-starter-baseline` is the canonical branch for Harness/Hermes adapter contracts, reference packs, and baseline docs.
- `main` is a default/upstream anchor, not the active mutation target unless the owner explicitly says so.
- Retired experimental branches such as `codex/hermes-adapter` must not be treated as merge targets.
- Branch, commit, push, auth-sensitive, and write-capable operations must pass the runtime context guard before action.

## Prompt canaries for optional context verification

- MAAT judges first.
- THOTH compiles the contract before fan-out.
- Failure is a CPS event.
- Truthful reporting rules.
- Hermes context-loading reality.

## Baseline contract vocabulary

- Root user outcome is `root_goal`.
- Child/node completion criteria are `task_AC`.
- C split produces a `cps_flow_graph`; children inherit root identity by reference.
- P/S expression steps are ordered; order, occurrence, consumes/emits, and dependencies can change the workflow meaning.
- Review checks artifacts; CPS audit checks graph/transition/actor-binding/learning correctness.
- Actor choice is `actor_binding` and must be justified by CPS/profile routing evidence.
- Actor binding is adaptive: templates suggest candidate pools, but actual agent invocation is late-bound by expression step, evidence obligation, risk, context, and outcome trace.
- Final completion requires graph closure evidence and LangSmith-style trace keys, not a role checklist.

## CPS-governed operating loop

Treat any work touching Hermes runtime, Harness, CPS, Honcho, GBrain, project memory, doc_ops, Kanban routing, write-back, gateway/session lifecycle, or cross-session learning as **CPS-governed work**.

### Architecture Targets
- **Hermes**: Default runtime/control plane. Enforces preflight, owner boundary, board/cwd discipline, and post-completion write-back decision.
- **Harness**: CPS compiler/router/audit plane. Converts user work into root_goal/task_AC/cps_flow_graph and enforces Maat gate before fan-out or completion.
- **Honcho**: Digest-first context plane. Stores compact conclusions/session messages with source_refs, not raw stdout/transcripts. Verifies write path separately.
- **GBrain / harness-brain**: Git-backed long-term project memory/wiki. Stores source_ref-backed decisions, procedures, session-close snapshots, doc_ops manifests, lifecycle incidents, and searchable project records. Never replaces project repo docs.

### Honcho & GBrain Background Sync & Learning Substrate
- **GBrain Syncer (`honcho_background_worker.py`)**: 세션 종료 및 writeback 시, 스냅샷 정보를 `.harness/project/runs/gbrain_memory_store.json` 로컬 학습 기저에 리스트 형태로 누적 저장하여 세션 간 컨텍스트 데카이(Decay)를 방지합니다.
- **Background Daemon (`run_harness_background_loop.sh`)**: `daemon [interval_seconds]` 액션을 통해 백그라운드에서 주기적으로 기동하여 프로젝트 drift 감지 및 manifest auto-ingest를 자동화하고, 구조화된 JSON 감사 이력을 `.harness/project/runs/background_audit.log`에 기록합니다. SIGINT/SIGTERM 시 안전한 종료 트랩이 동작합니다.
- **Anubis Delegation**: 모든 물리적 리포지토리 뮤테이션은 조율자(default)가 아닌 Coder/Executor Lane인 아누비스(Anubis)가 수행하며, Ponytail의 게으른 개발자 사다리(LOC 100 제한 및 의존성 추가 제한) 검증을 거쳐 반영됩니다.

For CPS-governed work, do not proceed as ad-hoc terminal/debug action. Before implementation, remediation, debugging, live service changes, or worker fan-out:

1. Bind to a concrete board/project and filesystem scope: board slug, `default_workdir`/cwd, repo root, branch, remote, and owner approval boundary. Never infer this from Discord thread title or prior conversation alone.
2. Find or create a source-ref-backed CPS/Maat artifact containing `root_goal`, `task_AC`, C/P/S framing, `source_refs`, `artifact_refs`, `owner_approval_boundary`, `prohibited_actions`, `evidence_acquisition`, a Maat compliance matrix, and validation/readback plan.
3. If no artifact exists, stop execution immediately. A missing CPS/Maat artifact is a hard pre-action blocker. Create the appropriate packet first: harness-brain/GBrain for work history or project memory, repo docs for policy/contracts/source of truth, skill for reusable procedure, and Honcho only for compact digest-first context.
4. If an unexpected blocker diverts the work, do not silently switch `root_goal`. Create or update a CPS incident artifact first, recording: original root_goal, blocker, evidence, temporary remediation, Maat gap, and required return path to original task_AC. After resolving the blocker, explicitly return to the original CPS packet. Do not report "operational normal" as completion if the root goal is still incomplete.
5. Use digest-first evidence: paths, line refs, counts, timestamps, exit codes, HTTP status, and top errors. Do not dump raw logs, full transcripts, broad grep output, or secrets into Honcho/GBrain.
6. Before any completion claim, run a Maat-style matrix against all `task_AC` and prohibited actions. Where applicable, verify enforcement in runnable schemas, templates, validators, manifests, scripts, or CI/check commands; Markdown keyword presence alone is not enough.
7. At completion or blocker, perform the correct learning write-back: repo SSOT for policy/contract changes, harness-brain/GBrain for lifecycle/decisions/procedures, Honcho for compact source-ref-backed context, skill patch/create for reusable procedure, and memory only for compact durable facts.
8. After prerequisite or infrastructure remediation, explicitly return to the original `root_goal`/`task_AC` or report the documented hold.

### Secret Hygiene Rules
- Never print, store, or write secret values/tokens in chat logs, memories, or files.
- If secrets were exposed in chat/logs, record a rotation follow-up as an owner action, not as memory content containing the secret.

## hermes-kann default runtime obligations

`hermes-kann` replaces the generic default for user-facing Harness work. It is not an optional wrapper.

```yaml
hermes-kann:
  role: default_user_facing_harness_runtime
  replaces: generic_default
  obligations:
    - digest_first_tool_use
    - cps_before_execution
    - owner_approval_boundary
    - project_context_routing
    - honcho_context_merge
    - sibling_thread_recall
    - post_completion_honcho_update
    - gateway_route_lifecycle_check
    - raw_output_hygiene
```

Maat-style handoff compliance must run before completion claims for Harness CPS doc_ops / Honcho wiki / Kanban promotion work.

## Cross-session learning and lifecycle obligations

Harness operates above Hermes as the routing/process plane, so every task preflight must reconcile the surrounding workspace before execution. A Harness worker must check sibling Discord threads/sessions for related work, merge relevant Honcho context, and treat thread lifecycle, Hermes gateway route lifecycle, DB session lifecycle, and compression lifecycle as one operational boundary. Archiving a Discord thread is not sufficient if `~/.hermes/sessions/sessions.json` still points at a completed DB session.

Completion claims for Harness work require a learning write-back decision:

- if the result changes project policy, contracts, routing, or operating procedure, update the repo source_ref and queue/perform a Honcho digest update;
- if the result is a corrected agent procedure, patch the relevant skill or Agent/SOUL instruction immediately;
- if the result closes a thread/task, verify route/session cleanup ownership and session-close snapshot creation or create an explicit follow-up task;
- if a conversation/session is completed or intentionally archived, emit a bounded snapshot for background analysis/propagation instead of relying on the full transcript;
- sibling threads must be able to discover the result through Honcho/session_search, not only through the original Discord thread.

Failure to find already-completed related work is a process failure. Record the missing lookup or missing write-back as a CPS learning event before continuing.

## Evidence acquisition contract

Harness task packets should make evidence needs explicit before tool use. THOTH must compile this for fan-out when a task involves inspection, debugging, validation, review, or triage. This section is CPS-shaped: `C` defines the context/decision needing evidence, `P` defines the uncertainty or risk being resolved, and `S` defines the minimal evidence strategy and output shape. This is not another guardrail; it is an acquisition contract that prevents unnecessary stdout requests from being made.

Required packet section:

```yaml
evidence_acquisition:
  mode: digest-first
  C:
    decision_context: "What CPS/task_AC decision will this evidence support?"
    scope_refs: [root_goal, task_AC, cps_flow_graph_node]
  P:
    uncertainty: "What is unknown, risky, or disputed?"
    failure_mode_if_wrong: "What silent failure or wasted work happens if we collect the wrong evidence?"
  S:
    evidence_strategy: "How to answer with the smallest sufficient signal"
    expected_signal:
      - exit_code | count | changed_paths | top_errors | timestamp_window | line_refs | artifact_refs
    stdout_shape: "bounded digest; no raw corpus by default"
    raw_artifact_policy: "only when task_AC requires raw evidence; save artifact and report path + reason + index/readback plan"
    prohibited_stdout:
      - full git diff
      - unbounded grep/rg/search results
      - broad log tails
      - sqlite/session dumps
      - full test output
      - recursive file lists
```

Raw terminal stdout is not a default evidence source. Commands should emit the answer-shaped signal needed for the CPS decision: counts, paths, timestamps, failing examples, exit codes, and line references. If the raw corpus is genuinely necessary, it belongs in an artifact reference with a digest, not in worker-visible context.

## The Lazy Dev's Ladder (Ponytail) operating rule

이 리포지토리는 DietrichGebert/ponytail의 '게으른 개발자의 사다리(The Lazy Dev's Ladder)' 철학을 Harness CPS(Context, Problem, Solution) 라이프사이클에 유기적으로 결합하여 코딩을 통제합니다. 에이전트는 코드를 작성하거나 패키지를 추가하기 전에 반드시 다음 7단계를 순차적으로 검토하고, 이를 입증해야 합니다.

1. **존재할 필요가 있는가 (YAGNI)**: 요구사항 범위를 벗어난 불필요한 기능 구현은 즉시 중단합니다. (C: Context 맥락 분석)
2. **이미 코드베이스에 있는가**: 기존 구현을 최대한 재사용하고 중복 코드를 작성하지 않습니다. (C: Context 맥락 분석)
3. **표준 라이브러리(Stdlib)로 가능한가**: 외부 패키지나 복잡한 모듈 대신 내장 라이브러리를 우선 사용합니다. (C: Context 맥락 분석)
4. **네이티브 플랫폼 기능인가**: 프레임워크나 외부 솔루션 대신 플랫폼/런타임 내장 기능을 활용합니다. (C: Context 맥락 분석)
5. **이미 설치된 의존성인가**: 신규 패키지 추가를 엄격히 제한하고 이미 설치된 의존성 범위 내에서 해결합니다. (P: Problem 문제 정의 - 외부 의존성 추가나 과도한 확장을 문제로 포착)
6. **한 줄로 가능한가**: 코드를 극한으로 단순화하여 단일 라인 혹은 단일 함수 단위로 해결합니다. (S: Solution 해결책 설계 - 최소 비용의 해법 도출)
7. **최소한의 코드 작동 (LOC 최소화)**: 작성하는 코드는 작동하는 최소한의 크기여야 하며, 태스크당 추가 라인 수(LOC)는 기계적 감사(S: Solution 구현체 - `audit_ponytail_compliance.py`)에 의해 100 LOC로 제한됩니다.

에이전트는 태스크 패킷 작성 시 `lazy_dev_justification` 필드에 이 사다리 검토 결과를 명시해야 하며, 사전 소유자 승인 없이 의존성 파일을 수정하거나 LOC 한도를 초과할 경우 검증 파이프라인에서 즉시 반려(FAIL)됩니다.
