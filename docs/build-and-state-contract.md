# Harness runtime build and state contract

The build input is the repository root `pyproject.toml` and `uv.lock`. The wheel contains only the isolated runtime package, the versioned execution-receipt and canonical-binding schemas, and the `harness-runtime` entrypoint. It excludes project adapters, templates, tests, Harness Brain prose, `.harness/project/runs/`, and all generated state.

Runtime state never belongs in the source tree. Unless an explicit `HARNESS_STATE_DIR` is supplied for an isolated fixture, runtime state resolves to:

```text
~/.harness/state/<profile>/<project-slug>/<canonical-cwd-hash>/
```

The root contains only runtime-owned directories such as `sessions/`, `receipts/`, `checkpoints/`, `locks/`, `sqlite/`, and `logs/`. The isolated receipt implementation writes below `receipts/`; it never falls back to `.harness/project/runs/`.

`HARNESS_STATE_DIR` is the only state location permitted for tests. Tests must not use live `$HERMES_HOME`, a Hermes service venv, gateway state, or a source-tree runtime directory.

## Canonical binding registry contract

`harness_runtime.CanonicalBindingRegistry` is the source-identity authority for the versioned `canonical-binding.v1` contract. A request has exactly `platform`, `guild_id`, `parent_channel_id`, `thread_id`, and `profile`; a resolved result has exactly `project_slug`, `canonical_cwd`, `write_scope`, `binding_revision`, and `source_ref`. It does not inspect a process cwd, thread title, Hermes session data, or any implicit fallback.

The registry produces a receipt with `resolver_revision`, `binding_digest`, `session_key`, and a `consumer_readback` identity. `persist_receipt()` and `readback()` require an explicit `HARNESS_STATE_DIR`; this creates a reproducible producer → temporary-state receipt → consumer-readback path without Hermes-host receipt storage. A future separately authorized resolver bridge may exchange this input/result/receipt shape, but this runtime package neither imports nor implements that bridge.
