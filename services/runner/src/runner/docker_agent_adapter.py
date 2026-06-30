"""
Opt-in Docker agent runner adapter — deterministic execution boundary.

The Docker adapter requires TWO opt-in steps to execute:
1. ``requested_adapter`` must contain ``"docker"`` (dispatcher-level selection).
2. ``allow_docker=True`` must be passed to ``run_docker_agent_execution``.

Without opt-in, the adapter returns a deterministic ``blocked`` result.

No subprocess, no Docker SDK, no network, no filesystem IO at import time.
"""

from __future__ import annotations

from typing import Any, Callable

from runner.docker_run_artifacts import build_docker_artifacts, build_docker_evidence


# ---------------------------------------------------------------------------
# Default executor
# ---------------------------------------------------------------------------

_DEFAULT_EXECUTOR: Callable[[dict], dict] = lambda cmd: {
    "exit_code": -1,
    "stdout": "",
    "stderr": "Docker daemon not available. Run with allow_docker and an injected executor.",
    "success": False,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def build_docker_agent_command(execution_request: dict) -> dict:
    """Build a deterministic Docker command metadata dict from an execution request.

    Parameters
    ----------
    execution_request
        The RunnerExecutionRequest dict.

    Returns
    -------
    dict
        Deterministic command metadata (never executes anything).
    """
    req_id = execution_request.get("execution_request_id", "")
    run_id = execution_request.get("run_id", "")
    task_goal = (
        execution_request.get("inputs", {}).get("task_goal", "")
        or execution_request.get("execution_request_id", "")
    )
    mode = execution_request.get("execution_mode", "dry_run")

    return {
        "adapter": "docker-agent-v1",
        "container_image": "ariadne-agent-base:latest",
        "container_command": [
            "agent", "run",
            "--run-id", run_id,
            "--request-id", req_id,
            "--mode", mode,
        ],
        "workdir": "/workspace",
        "volumes": {
            "/workspace": {"bind": "/workspace", "mode": "rw"},
        },
        "environment": {
            "ARIADNE_RUN_ID": run_id,
            "ARIADNE_REQUEST_ID": req_id,
            "ARIADNE_TASK_GOAL": task_goal,
            "ARIADNE_MODE": mode,
        },
        "network_mode": "none" if mode == "dry_run" else "bridge",
        "memory_limit": "4g",
        "cpu_count": 2,
        "timeout_seconds": 300,
        "evidence": {
            "note": "Docker command metadata is deterministic and references the execution request.",
            "execution_performed": False,
        },
    }


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


def run_docker_agent_execution(
    execution_request: dict,
    *,
    executor: Callable[[dict], dict] | None = None,
    allow_docker: bool = False,
) -> dict:
    """Run a Docker agent execution adapter.

    Parameters
    ----------
    execution_request
        The RunnerExecutionRequest dict.
    executor
        Callable for executing Docker commands.  Default executor returns a
        blocked result.  Inject a fake executor in tests.
    allow_docker
        Must be True to attempt Docker execution.  Default False for safety.

    Returns
    -------
    dict
        A RunnerExecutionResult dict.
    """
    req_id = execution_request.get("execution_request_id", "")
    run_id = execution_request.get("run_id", "")

    # --- Build command metadata (available to both branches) ---
    command_metadata = build_docker_agent_command(execution_request)

    # --- Opt-in check ---
    if not allow_docker:
        return {
            "execution_result_id": f"{req_id}-result",
            "execution_request_id": req_id,
            "run_id": run_id,
            "status": "blocked",
            "adapter": "docker-agent-v1",
            "artifacts": build_docker_artifacts(
                {"exit_code": -1, "stdout": "", "stderr": "", "success": False},
                command_metadata,
                req_id,
            ),
            "evidence": build_docker_evidence(
                {"exit_code": -1, "stdout": "", "stderr": "", "success": False},
                command_metadata,
                req_id,
            ),
            "errors": [],
            "warnings": [],
            "review_required": False,
            "next": "",
        }

    # --- Execute (or simulate) ---
    actual_executor = executor or _DEFAULT_EXECUTOR
    executor_result = actual_executor(command_metadata)

    success = executor_result.get("success", False)

    if success:
        status = "requires_review"
    else:
        status = "failed"

    # --- Normalize result ---
    return {
        "execution_result_id": f"{req_id}-result",
        "execution_request_id": req_id,
        "run_id": run_id,
        "status": status,
        "adapter": "docker-agent-v1",
        "artifacts": build_docker_artifacts(executor_result, command_metadata, req_id),
        "evidence": build_docker_evidence(executor_result, command_metadata, req_id),
        "errors": [] if success else [
            {"code": "execution_failed", "message": executor_result.get("stderr", "Unknown error")},
        ],
        "warnings": [],
        "review_required": False,
        "next": f"/runs/{run_id}/status" if run_id else "",
    }
