"""
Human review boundary — deterministic interpretation of execution request/result
approval/review state.

No UI, no notifications, no approval storage, no persistence, no database,
no HTTP, no model calls.
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _normalize_approval(raw: Any) -> dict:
    """Normalize an approval dict from an execution request."""
    if not isinstance(raw, dict):
        return {}
    result: dict[str, Any] = {}
    if raw.get("required") is True:
        result["required"] = True
    if raw.get("status") in ("pending", "approved", "denied"):
        result["status"] = raw["status"]
    if raw.get("after_execution") is True:
        result["after_execution"] = True
    reviewer = raw.get("reviewer")
    if reviewer:
        result["reviewer"] = reviewer
    reason = raw.get("reason")
    if reason:
        result["reason"] = reason
    return result


# ---------------------------------------------------------------------------
# Review boundary
# ---------------------------------------------------------------------------


def derive_review_boundary(
    execution_request: dict,
    execution_result: dict,
) -> dict:
    """Interpret execution request/result and produce a deterministic
    review-boundary decision.

    Parameters
    ----------
    execution_request
        The RunnerExecutionRequest dict.
    execution_result
        The RunnerExecutionResult dict.

    Returns
    -------
    dict
        A review-boundary decision dict.
    """
    errors: list[dict] = []
    warnings: list[str] = []

    # --- Validate input types ---
    if not isinstance(execution_request, dict):
        return _error_decision(
            errors_override=[{"code": "invalid_input", "message": "execution_request must be a dict.", "field": "execution_request"}],
        )
    if not isinstance(execution_result, dict):
        return _error_decision(
            errors_override=[{"code": "invalid_input", "message": "execution_result must be a dict.", "field": "execution_result"}],
        )

    req_id = execution_request.get("execution_request_id", "")
    result_id = execution_result.get("execution_result_id", "")
    run_id = execution_request.get("run_id", "")
    result_status = execution_result.get("status", "")
    approval_raw = execution_request.get("approval")
    approval = _normalize_approval(approval_raw)

    # --- Validate required IDs ---
    if not req_id:
        errors.append({"code": "invalid_input", "message": "execution_request_id is required.", "field": "execution_request_id"})
    if not result_id:
        errors.append({"code": "invalid_input", "message": "execution_result_id is required.", "field": "execution_result_id"})

    if errors:
        return _error_decision(
            req_id=req_id, result_id=result_id, run_id=run_id,
            errors_override=errors,
            approval=approval,
            result_status=result_status,
        )

    # --- Check result status ---
    if not result_status:
        warnings.append("execution_result has no 'status' field; treating as failed")

    # --- Determine decision ---
    decision = "completed"
    reason_code = ""
    reasons: list[str] = []

    # Check approval first (gates execution)
    if approval.get("required") is True:
        app_status = approval.get("status", "")
        if app_status == "denied":
            decision = "blocked"
            reason_code = "approval_denied"
            reasons.append("Human approval was denied.")
        elif approval.get("after_execution") is True:
            if result_status == "completed":
                decision = "requires_review"
                reason_code = "requires_review"
                reasons.append("Execution completed but requires human review.")
            else:
                # Delegate to result status handling below
                pass
        elif app_status == "approved":
            # Approved — check result status
            pass
        elif app_status == "pending" or not app_status:
            decision = "requires_review"
            reason_code = "approval_pending"
            reasons.append("Human approval is required and not yet granted.")

    # If not determined by approval, check result status
    if decision == "completed":
        if result_status == "requires_review":
            decision = "requires_review"
            reason_code = "requires_review"
            reasons.append("Execution result requires human review.")
        elif result_status == "blocked":
            decision = "blocked"
            reason_code = "blocked"
            reasons.append("Execution is blocked pending external input.")
        elif result_status in ("failed", "error") or not result_status:
            decision = "failed"
            reason_code = "execution_failed"
            reasons.append("Execution failed.")

    # --- Build response ---
    return {
        "schema_version": "0.1",
        "decision": decision,
        "requires_review": decision == "requires_review",
        "blocked": decision == "blocked",
        "completed": decision == "completed",
        "failed": decision in ("failed", "error"),
        "reason_code": reason_code,
        "reasons": reasons,
        "execution_request_id": req_id,
        "execution_result_id": result_id,
        "run_id": run_id,
        "approval": approval,
        "metadata": {
            "execution_adapter": execution_result.get("adapter", ""),
            "execution_mode": execution_request.get("execution_mode", ""),
        },
        "errors": errors,
        "warnings": warnings,
    }


def _error_decision(
    req_id: str = "",
    result_id: str = "",
    run_id: str = "",
    errors_override: list | None = None,
    approval: dict | None = None,
    result_status: str = "",
) -> dict:
    return {
        "schema_version": "0.1",
        "decision": "error",
        "requires_review": False,
        "blocked": False,
        "completed": False,
        "failed": False,
        "reason_code": "invalid_input",
        "reasons": [],
        "execution_request_id": req_id,
        "execution_result_id": result_id,
        "run_id": run_id,
        "approval": approval or {},
        "metadata": {
            "execution_adapter": "",
            "execution_mode": "",
        },
        "errors": errors_override or [],
        "warnings": [],
    }
