#!/bin/sh
set -eu

cd "$(dirname "$0")/.."
python -m unittest \
  test_cps_preflight_verification_gate.TestCpsPreflightVerificationGate.test_lifecycle_delegate_writes_handoff_snapshot \
  test_cps_preflight_verification_gate.TestCpsPreflightVerificationGate.test_lifecycle_delegate_rotates_handoff_snapshots_with_three_file_cap
