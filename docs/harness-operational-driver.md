# Harness operational driver

The driver consumes one immutable operational input, captures its declared files once, and runs its one focused test command once. It does not query or validate Kanban or Honcho, and has no wheel, build, virtual-environment, install, artifact-mode, or cache path.

## Receipt

The UTF-8 JSON receipt has exactly these fields:

```json
{
  "schema": "harness.operational-driver.scope-receipt.v1",
  "task_ref": "opaque task correlation value",
  "revision": "opaque revision correlation value",
  "source_root": "/absolute/source/root",
  "files": [
    {"path": "relative/file", "sha256": "<64 lowercase hex>"}
  ],
  "focused_test_command": {
    "args": ["-q", "tests/focused_test.py"]
  }
}
```

`task_ref` and `revision` are opaque, non-empty correlation strings and pass through unchanged. Unknown or missing fields, malformed test arguments, non-normalized paths, symlinks, aliases, non-regular files, escapes, and digest mismatches fail closed. The input bytes and each listed source file are read once. The driver does not accept or emit Goal/AC material.

## Execution

Run the driver with Python 3.11 or later:

```sh
python3 scripts/harness_operational_driver.py \
  --scope-receipt /absolute/scope-receipt.json
```

The driver verifies and invokes the repository-configured pytest runner once with the declared test arguments, `shell=False`, from the private snapshot, with a 300-second timeout. No discovery, packaging, or other subprocess runs.

A single driver-owned temporary root contains the snapshot and command working directory. One `finally` cleanup removes it after success, focused-test failure, timeout, or snapshot failure. Cleanup failure makes the packet unsuccessful while preserving the operation outcome in its execution evidence.

## Packet

Standard output is one compact JSON packet addressed to Anubis and Maat. The packet records:

- unchanged opaque `task_ref` and `revision` correlation fields;
- the SHA-256 digest of the exact operational-input bytes;
- the captured path, digest, and size manifest and its digest;
- configured runner identity and version;
- the exact argv, outcome, monotonic duration, exit code when available, stdout, stderr, and timeout when applicable;
- cleanup status;
- evidence retention at `packet.evidence` until Maat closes the operation.

The process exits zero only when the declared focused test exits zero. Focused-test failure, timeout, input rejection, configured-runner rejection, snapshot failure, and cleanup failure produce a non-success packet and nonzero process exit.

The focused test is:

```sh
.venv/bin/python -m pytest tests/runtime/test_harness_operational_driver.py
```
