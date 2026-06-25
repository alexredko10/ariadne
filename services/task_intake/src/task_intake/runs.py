"""
Deterministic mock run creation — pure function.

Accepts normalized task intake and context preview data and returns a
deterministic mock run object with a simple status object.

No model calls, no repository scanning, no Git inspection, no persistence.
No real run execution, no Docker agents, no runner invocation.
"""

from __future__ import annotations

import hashlib
from typing import Any


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_run_id(task_goal: str, context_preview_id: str) -> str:
    """Generate a deterministic run ID."""
    digest = hashlib.sha256(
        f"{task_goal}{context_preview_id}".encode("utf-8")
    ).hexdigest()
    return f"run_{digest[:12]}"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _validate_request(data: dict) -> list[str]:
    """Validate a mock run creation request.

    Parameters
    ----------
    data
        The raw request dict.

    Returns
    -------
    list[str]
        A list of validation errors (empty if valid).
    """
    errors: list[str] = []

    if not isinstance(data, dict):
        return ["Request body must be a JSON object."]

    # task_intake
    ti = data.get("task_intake")
    if ti is None:
        errors.append("task_intake is required")
    elif not isinstance(ti, dict):
        errors.append("task_intake must be a dict")
    else:
        task_goal = ti.get("task_goal")
        if task_goal is None:
            errors.append("task_intake.task_goal is required")
        elif not isinstance(task_goal, str) or not task_goal.strip():
            errors.append("task_intake.task_goal must be a non-empty string")

    # context_preview
    cp = data.get("context_preview")
    if cp is None:
        errors.append("context_preview is required")
    elif not isinstance(cp, dict):
        errors.append("context_preview must be a dict")
    else:
        cp_id = cp.get("context_preview_id")
        if cp_id is None:
            errors.append("context_preview.context_preview_id is required")
        elif not isinstance(cp_id, str) or not cp_id.strip():
            errors.append("context_preview.context_preview_id must be a non-empty string")

    # Cross-validate task_intake_id
    if isinstance(ti, dict) and isinstance(cp, dict):
        ti_id = ti.get("task_intake_id")
        cp_ti_id = cp.get("task_intake_id")
        if ti_id and cp_ti_id and ti_id != cp_ti_id:
            errors.append(
                f"task_intake_id mismatch: "
                f"task_intake has '{ti_id}', "
                f"context_preview has '{cp_ti_id}'"
            )

    # run_options
    run_opts = data.get("run_options")
    if run_opts is not None and not isinstance(run_opts, dict):
        errors.append("run_options must be a dict if provided")

    return errors


# ---------------------------------------------------------------------------
# Mock run creation
# ---------------------------------------------------------------------------


def create_mock_run(raw: dict) -> dict:
    """Create a deterministic mock run from a raw request.

    Parameters
    ----------
    raw
        The raw request dict containing ``task_intake``, ``context_preview``,
        and optional fields.

    Returns
    -------
    dict
        A normalized response with ``ok``, ``run_id``, ``status``,
        ``task_intake_id``, ``context_preview_id``, ``run``, ``validation``,
        and ``next`` fields.
    """
    # Validate
    errors = _validate_request(raw)

    if errors:
        return {
            "ok": False,
            "status": {
                "state": "validation_failed",
                "phase": "mock_run",
                "message": "Run validation failed.",
                "is_terminal": True,
                "progress": 0,
                "updated_by": "task-intake-api",
            },
            "validation": {
                "valid": False,
                "errors": errors,
                "warnings": [],
            },
        }

    ti = raw["task_intake"]
    cp = raw["context_preview"]

    task_goal = ti.get("task_goal", "")
    constraints = ti.get("constraints", [])
    requested_output = ti.get("requested_output", "plan")
    inferred_mode = ti.get("inferred_mode", "unknown")
    task_intake_id = ti.get("task_intake_id", "")
    source = ti.get("source", "manual")
    metadata = ti.get("metadata", {})

    cp_id = cp.get("context_preview_id", "")

    run_options = raw.get("run_options") or {}

    # Generate deterministic IDs
    run_id = _make_run_id(task_goal, cp_id)

    return {
        "ok": True,
        "run_id": run_id,
        "status": {
            "state": "created",
            "phase": "mock_run",
            "message": (
                "Mock run created — no execution was performed. "
                "Submit to runner adapter for real execution."
            ),
            "is_terminal": False,
            "progress": 0,
            "updated_by": "task-intake-api",
        },
        "task_intake_id": task_intake_id,
        "context_preview_id": cp_id,
        "run": {
            "run_id": run_id,
            "task_intake_id": task_intake_id,
            "context_preview_id": cp_id,
            "requested_mode": inferred_mode,
            "constraints": sorted(constraints) if isinstance(constraints, list) else [],
            "requested_output": requested_output,
            "run_options": dict(run_options),
            "execution_plan_placeholder": {
                "note": "Real execution plan would be generated by conductor",
                "suggested_next_phase": "orchestrate",
            },
            "evidence": {
                "mock_run": True,
                "execution_performed": False,
                "runner_adapter_required": True,
            },
        },
        "validation": {
            "valid": True,
            "errors": [],
            "warnings": [
                "No real execution was performed. "
                "This is a mock run object."
            ],
        },
        "next": f"/runs/{run_id}/status",
    }
