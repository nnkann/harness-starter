# Harness runtime build and state contract

The build input is the repository root `pyproject.toml` and `uv.lock`. The wheel contains only the isolated runtime package, the versioned execution-receipt schema, and the `harness-runtime` entrypoint. It excludes project adapters, templates, tests, Harness Brain prose, `.harness/project/runs/`, and generated state.

## Deterministic artifact test producer

`harness-runtime run` executes one artifact test command. It requires:

- an explicit `--worktree-cwd` that is the root of a clean Git worktree with a committed `HEAD`;
- an explicit external `HARNESS_STATE_DIR`;
- a command that does not depend on caller environment state.

The runner does not inherit the caller environment. It supplies only `PATH`, `LANG`, `LC_ALL`, `TZ`, and `HARNESS_STATE_DIR`; Hermes and AGY variables are absent. `HARNESS_STATE_DIR` must resolve outside the execution worktree. The versioned terminal receipt records the exact argv and digest, constrained environment and digest, canonical worktree cwd and digest, Git commit and tree, exit code, and body/stdout/stderr artifact hashes. `run` verifies the persisted terminal receipt before emitting it.

Use absolute executable paths because the constrained `PATH` is the platform default:

```bash
HARNESS_STATE_DIR="$tmp_state" \
  harness-runtime run \
  --case "$case_id" \
  --consumer anubis \
  --body-file "$packet_json" \
  --worktree-cwd "$tmp_worktree" \
  -- "$absolute_python" -m pytest -q tests/runtime/test_runtime_contract.py
```

`harness-runtime readback` verifies the terminal projection against its two-event journal, validates execution metadata digests, and verifies every persisted artifact hash. `harness-runtime analysis-input` performs the same verification and returns bounded decoded stdout/stderr with explicit truncation flags for Anubis. Without that verified input, analysis has no execution basis.

Runtime state never belongs in the source tree. `HARNESS_STATE_DIR` is required for all producer and consumer operations; there is no home-directory, source-tree, Hermes, AGY, gateway, or live-state fallback.
