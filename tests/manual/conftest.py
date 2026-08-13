"""Explicit input boundary for retained historical L3 evidence."""

import os
from pathlib import Path

import pytest


def pytest_addoption(parser):
    group = parser.getgroup("historical L3 evidence")
    group.addoption("--historical-l3-cohort", metavar="PATH", help="original retained L3 cohort evidence")
    group.addoption("--historical-l3-admission", metavar="PATH", help="original retained L3.4 admission evidence")


def pytest_configure(config):
    cohort = config.getoption("historical_l3_cohort")
    admission = config.getoption("historical_l3_admission")
    if not cohort or not admission:
        raise pytest.UsageError(
            "tests/manual requires explicit --historical-l3-cohort PATH and "
            "--historical-l3-admission PATH; it never creates or restores them"
        )
    paths = (Path(cohort), Path(admission))
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise pytest.UsageError("historical evidence input is not a regular file: " + ", ".join(missing))
    os.environ["HARNESS_HISTORICAL_L3_COHORT_PATH"] = str(paths[0])
    os.environ["HARNESS_HISTORICAL_L3_ADMISSION_PATH"] = str(paths[1])
