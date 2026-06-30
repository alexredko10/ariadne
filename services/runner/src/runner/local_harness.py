"""
Local execution harness — bounded deterministic runtime slice.

Composes:
1. Runner dispatcher → execution result
2. Execution envelope
3. Human review boundary

No real execution, no Docker daemon, no process spawning, no network calls, no filesystem IO.
"""

from __future__ import annotations

from typing import Any

from runner.adapter_registry import dispatch_execution
from runner.execution_envelope import build_execution_envelope
from runner.review_boundary import derive_review_boundary


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


def run_local_execution_harness(execution_request: dict) -> dict:
    """Run a local execution harness:
    dispatcher → execution result → envelope → review boundary.

    Parameters
    ----------
    execution_request
        A RunnerExecutionRequest dict.

    Returns
    -------
    dict
        A deterministic harness result dict.
    """
    if not isinstance(execution_request, dict):
        return {
            "ok": False,
            "runtime_status": "error",
            "execution_request": None,
            "execution_result": None,
            "execution_envelope": None,
            "review_boundary": None,
            "errors": [{"code": "invalid_input", "message": "execution_request must be a dict."}],
            "warnings": [],
            "metadata": {"harness": "local", "harness_version": "0.1"},
        }

    # 1. Dispatcher
    execution_result = dispatch_execution(execution_request)

    # 2. Envelope
    envelope = build_execution_envelope(execution_request, execution_result)

    # 3. Review boundary
    boundary = derive_review_boundary(execution_request, execution_result)

    # 4. Collect errors / warnings
    errors: list = []
    warnings: list = []

    # Envelope errors
    if envelope.get("errors"):
        errors.extend(envelope["errors"])
    if envelope.get("warnings"):
        warnings.extend(envelope["warnings"])

    # Boundary errors
    if boundary.get("errors"):
        errors.extend(boundary["errors"])
    if boundary.get("warnings"):
        warnings.extend(boundary["warnings"])

    # Result errors
    if execution_result.get("errors"):
        errors.extend(execution_result["errors"])
    if execution_result.get("warnings"):
        warnings.extend(execution_result["warnings"])

    # Runtime status from boundary decision
    runtime_status = boundary.get("decision", "error")

    return {
        "ok": True,
        "runtime_status": runtime_status,
        "execution_request": execution_request,
        "execution_result": execution_result,
        "execution_envelope": envelope,
        "review_boundary": boundary,
        "errors": errors,
        "warnings": warnings,
        "metadata": {"harness": "local", "harness_version": "0.1"},
    }
