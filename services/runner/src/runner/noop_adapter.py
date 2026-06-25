"""
Minimal no-op runner adapter — pure deterministic function.

Accepts a ``RunnerExecutionRequest`` dict (PR 0068 contract) and returns a
deterministic ``RunnerExecutionResult`` dict without performing any real
execution.

No Docker, no subprocess, no shell, no network, no filesystem writes,
no model/provider calls, no agent execution.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Required field names from PR 0068 request schema
# ---------------------------------------------------------------------------

_REQUIRED_FIELDS = [
    "execution_request_id",
    "run_id",
    "task_intake_id",
    "context_preview_id",
    "requested_adapter",
    "execution_mode",
    "inputs",
    "constraints",
]

# Supported adapter patterns (adapter id must contain "noop").
_EXECUTION_MODES = frozenset({"dry_run", "preview"})


# ---------------------------------------------------------------------------
# Error helpers
# ---------------------------------------------------------------------------


def _fail_result(
    execution_request_id: str,
    run_id: str,
    errors: list[dict],
) -> dict:
    return {
        "execution_result_id": f"{execution_request_id}-result",
        "execution_request_id": execution_request_id or "",
        "run_id": run_id or "",
        "status": "failed",
        "adapter": "noop-v1",
        "artifacts": [],
        "evidence": [],
        "errors": errors,
        "warnings": [],
        "review_required": False,
        "next": "",
    }


def _failed_field(field: str, reason: str) -> dict:
    return {"code": "invalid_field", "message": f"{field}: {reason}"}


# ---------------------------------------------------------------------------
# Request validation
# ---------------------------------------------------------------------------


def _validate_request(data: dict) -> list[dict]:
    """Validate a RunnerExecutionRequest dict.

    Parameters
    ----------
    data
        The request dict to validate.

    Returns
    -------
    list[dict]
        A list of error dicts (empty if valid).
    """
    if not isinstance(data, dict):
        return [_failed_field("request", "Request must be a dict.")]

    errors: list[dict] = []

    for field in _REQUIRED_FIELDS:
        val = data.get(field)
        if val is None:
            errors.append(_failed_field(field, "Required field is missing."))
        elif isinstance(val, str) and not val.strip():
            errors.append(_failed_field(field, "Required field must be a non-empty string."))

    # If execution_request_id or run_id is missing, we still try to produce
    # a useful result. But required fields must be present for success.

    return errors


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


def run_noop_execution(execution_request: dict) -> dict:
    """Execute a deterministic no-op runner adapter response.

    Accepts a RunnerExecutionRequest dict (as defined in
    ``schemas/runner-execution-request.schema.yml``) and returns a
    deterministic RunnerExecutionResult dict without performing any
    real execution.

    Parameters
    ----------
    execution_request
        The execution request dict.

    Returns
    -------
    dict
        A deterministic execution result dict conforming to
        ``schemas/runner-execution-result.schema.yml``.
    """
    # --- Validate ---
    errors = _validate_request(execution_request)

    if errors:
        return _fail_result(
            execution_request.get("execution_request_id", ""),
            execution_request.get("run_id", ""),
            errors,
        )

    req_id = execution_request["execution_request_id"]
    run_id = execution_request["run_id"]
    requested_adapter = execution_request["requested_adapter"]
    execution_mode = execution_request["execution_mode"]
    approval = execution_request.get("approval")

    # --- Check adapter ---
    if "noop" not in requested_adapter.lower():
        return _fail_result(
            req_id, run_id,
            [{"code": "unsupported_adapter",
              "message": f"Unsupported adapter: {requested_adapter!r}. "
                         f"No-op adapter requires 'noop' in the adapter id."}],
        )

    # --- Check execution mode ---
    if execution_mode not in _EXECUTION_MODES:
        return _fail_result(
            req_id, run_id,
            [{"code": "unsupported_mode",
              "message": f"Unsupported execution_mode: {execution_mode!r}. "
                         f"No-op adapter supports: {sorted(_EXECUTION_MODES)}."}],
        )

    # --- Check approval ---
    if isinstance(approval, dict):
        if approval.get("required") is True and approval.get("approved") is False:
            return {
                "execution_result_id": f"{req_id}-result",
                "execution_request_id": req_id,
                "run_id": run_id,
                "status": "blocked",
                "adapter": "noop-v1",
                "artifacts": [],
                "evidence": [
                    {
                        "evidence_id": f"{req_id}-noop-evidence-blocked",
                        "evidence_kind": "execution_note",
                        "summary": (
                            "No-op adapter blocked execution because human approval "
                            "is required and not yet granted."
                        ),
                        "status": "skipped",
                    },
                ],
                "errors": [],
                "warnings": ["Execution blocked pending human approval."],
                "review_required": False,
                "next": "",
            }

        if approval.get("required") is True and approval.get("after_execution") is True:
            return {
                "execution_result_id": f"{req_id}-result",
                "execution_request_id": req_id,
                "run_id": run_id,
                "status": "requires_review",
                "adapter": "noop-v1",
                "artifacts": [],
                "evidence": [
                    {
                        "evidence_id": f"{req_id}-noop-evidence-pending-review",
                        "evidence_kind": "execution_note",
                        "summary": (
                            "No-op adapter completed dry-run. "
                            "Human review is required before proceeding."
                        ),
                        "status": "passed",
                    },
                ],
                "errors": [],
                "warnings": [],
                "review_required": True,
                "next": "",
            }

    # --- Success (dry_run or preview) ---
    return {
        "execution_result_id": f"{req_id}-result",
        "execution_request_id": req_id,
        "run_id": run_id,
        "status": "completed",
        "adapter": "noop-v1",
        "artifacts": [],
        "evidence": [
            {
                "evidence_id": f"{req_id}-noop-evidence-ok",
                "evidence_kind": "execution_note",
                "summary": (
                    f"No-op adapter (noop-v1) completed. "
                    f"No real execution was performed. "
                    f"No Docker, no subprocess, no shell, no network, "
                    f"no filesystem writes, no model/provider calls, "
                    f"no agent execution."
                ),
                "status": "passed",
            },
        ],
        "errors": [],
        "warnings": [],
        "review_required": False,
        "next": f"/runs/{run_id}/status",
    }
