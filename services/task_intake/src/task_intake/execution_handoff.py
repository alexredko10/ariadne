"""
Mock-run to runner-dispatcher handoff — deterministic composition.

Calls the existing mock loop, builds a RunnerExecutionRequest,
runs the local execution harness, and returns a combined result.

No HTTP route changes, no mock-loop logic changes, no real execution.
"""

from __future__ import annotations

import hashlib
from typing import Any

from task_intake.mock_loop import run_mock_loop
from runner.local_harness import run_local_execution_harness


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_handoff_id(
    task_goal: str,
    context_preview_id: str,
    loop_id: str,
) -> str:
    digest = hashlib.sha256(
        f"{task_goal}{context_preview_id}{loop_id}".encode("utf-8")
    ).hexdigest()
    return f"handoff_{digest[:12]}"


def _make_execution_request_id(
    task_goal: str,
    context_preview_id: str,
    loop_id: str,
) -> str:
    digest = hashlib.sha256(
        f"{task_goal}{context_preview_id}{loop_id}".encode("utf-8")
    ).hexdigest()
    return f"er_{digest[:12]}"


def _build_execution_request(
    mock_result: dict,
    raw: dict,
) -> dict:
    """Build a RunnerExecutionRequest from mock loop result and raw input."""
    ti = mock_result.get("task_intake", {})
    normalized = ti.get("normalized", {})
    context_preview = mock_result.get("context_preview", {})
    run = mock_result.get("run", {})

    task_goal = normalized.get("task_goal", "")
    cp_id = context_preview.get("context_preview_id", "")
    loop_id = mock_result.get("loop_id", "")

    return {
        "execution_request_id": _make_execution_request_id(task_goal, cp_id, loop_id),
        "run_id": run.get("run_id", "") or loop_id,
        "task_intake_id": ti.get("task_intake_id", ""),
        "context_preview_id": cp_id,
        "requested_adapter": raw.get("requested_adapter", "noop"),
        "execution_mode": raw.get("execution_mode", "dry_run"),
        "inputs": {
            "task_goal": task_goal,
            "source": normalized.get("source", "manual"),
            "inferred_mode": normalized.get("inferred_mode", "unknown"),
            "inferred_domains": normalized.get("inferred_domains", []),
            "context_sections_included": list(
                context_preview.get("preview", {}).get("context_sections", {}).keys()
            ),
        },
        "constraints": normalized.get("constraints", []),
        "expected_outputs": [normalized.get("requested_output", "plan")],
        "approval": raw.get("execution_approval"),
        "metadata": {"source": "mock-execution-handoff", "handoff_via": "run_mock_execution_handoff"},
    }


# ---------------------------------------------------------------------------
# Handoff
# ---------------------------------------------------------------------------


def run_mock_execution_handoff(raw: Any) -> dict:
    """Run the mock app loop then dispatch execution through the runner adapter.

    Parameters
    ----------
    raw
        The raw task request (same shape as ``run_mock_loop`` input).

    Returns
    -------
    dict
        A combined handoff response.
    """
    if not isinstance(raw, dict):
        return {
            "ok": False,
            "handoff_id": "",
            "mock_loop_result": None,
            "execution_request": None,
            "execution_result": None,
            "execution_envelope": None,
            "review_boundary": None,
            "runtime_status": "",
            "errors": [{"code": "invalid_request", "message": "Request must be a dict."}],
            "warnings": [],
            "next": "",
        }

    # Step 1: Run the mock app loop
    mock_result = run_mock_loop(raw)
    if not mock_result.get("ok"):
        return {
            "ok": False,
            "handoff_id": "",
            "mock_loop_result": mock_result,
            "execution_request": None,
            "execution_result": None,
            "execution_envelope": None,
            "review_boundary": None,
            "runtime_status": "",
            "errors": mock_result.get("validation", {}).get("errors", []),
            "warnings": mock_result.get("warnings", []),
            "next": "",
        }

    ti = mock_result.get("task_intake", {})
    normalized = ti.get("normalized", {})
    cp = mock_result.get("context_preview", {})
    run = mock_result.get("run", {})
    task_goal = normalized.get("task_goal", "")
    cp_id = cp.get("context_preview_id", "")
    loop_id = mock_result.get("loop_id", "")
    run_id = run.get("run_id", "")
    handoff_id = _make_handoff_id(task_goal, cp_id, loop_id)

    # Step 2: Build execution request
    execution_request = _build_execution_request(mock_result, raw)

    # Step 3: Run local execution harness (dispatcher → envelope → review boundary)
    harness_result = run_local_execution_harness(execution_request)

    # Step 4: Combine
    errors: list = []
    warnings: list = []
    har_errors = harness_result.get("errors", [])
    execution_result = harness_result.get("execution_result", {})
    envelope = harness_result.get("execution_envelope", {})
    boundary = harness_result.get("review_boundary", {})

    if execution_result.get("status") == "failed":
        errors.extend(execution_result.get("errors", []))
    errors.extend(har_errors)
    errors.extend(mock_result.get("validation", {}).get("errors", []))
    warnings.extend(mock_result.get("warnings", []))
    warnings.extend(harness_result.get("warnings", []))

    return {
        "ok": True,
        "handoff_id": handoff_id,
        "mock_loop_result": {
            "loop_id": loop_id,
            "task_intake_id": ti.get("task_intake_id", ""),
            "task_goal": task_goal,
            "context_preview_id": cp_id,
            "status": mock_result.get("status", {}),
        },
        "execution_request": execution_request,
        "execution_result": execution_result,
        "execution_envelope": envelope,
        "review_boundary": boundary,
        "runtime_status": harness_result.get("runtime_status", ""),
        "errors": errors,
        "warnings": warnings,
        "next": f"/runs/{run_id}/status" if run_id else "",
    }
