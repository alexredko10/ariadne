"""Tests for the runner doctor CLI (``python -m runner doctor``)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

# Repository root is three levels up from services/runner/tests/
REPO_ROOT = Path(__file__).resolve().parents[3]
RUNNER_SRC = REPO_ROOT / "services" / "runner" / "src"

EXPECTED_OUTPUT_LINES = [
    "platform-runner doctor",
    "runner import: ok",
    "patch models: ok",
    "patch safety: ok",
]


def _runner_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(RUNNER_SRC)
    return env


def test_doctor_cli_succeeds_with_stable_output() -> None:
    """``python -m runner doctor`` exits 0 and prints expected lines in order."""
    result = subprocess.run(
        [sys.executable, "-m", "runner", "doctor"],
        cwd=REPO_ROOT,
        env=_runner_env(),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stderr == ""

    output_lines = result.stdout.strip().splitlines()
    assert output_lines == EXPECTED_OUTPUT_LINES


def test_unknown_command_exits_non_zero_and_prints_usage() -> None:
    """An unrecognised subcommand exits non-zero and shows usage."""
    result = subprocess.run(
        [sys.executable, "-m", "runner", "unknown-command"],
        cwd=REPO_ROOT,
        env=_runner_env(),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    combined_output = result.stdout + result.stderr
    assert "usage:" in combined_output
