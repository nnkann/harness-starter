import pytest

from harness_runtime.readiness_controller import ReadinessError, run_ready


def test_run_ready_invokes_runner_for_complete_readiness():
    result = run_ready({"ready": True}, lambda: "started")

    assert result == "started"


def test_run_ready_rejects_incomplete_input_before_launch():
    launches = 0

    def launch():
        nonlocal launches
        launches += 1

    with pytest.raises(ReadinessError, match="complete readiness input is required"):
        run_ready({}, launch)

    assert launches == 0
