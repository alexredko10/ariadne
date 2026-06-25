from __future__ import annotations

"""
Mock app-loop composition for Task Intake — pure functions.

Composes existing normalize, context_preview, and runs functions to
produce a deterministic end-to-end mock loop response.

This module intentionally avoids any I/O, networking, or external
integration. It does not execute runs or call models.
"""

import hashlib
from typing import Any

from task_intake.normalize import normalize_task_intake
from task_intake.context_preview import generate_context_preview
from task_intake.runs import create_mock_run


def _make_loop_id(task_goal: str, context_preview_id: str) -> str:
    digest = hashlib.sha256(f"{task_goal}{context_preview_id}".encode("utf-8")).hexdigest()
    return f"loop_{digest[:12]}"


def run_mock_loop(raw: Any) -> dict:
    """Run the composed mock application loop.

    Parameters
    ----------
    raw
        The raw request mapping. Expected to contain the same fields
        accepted by the normalize endpoint (e.g. "raw_task", optional
        overrides).

    Returns
    -------
    dict
        Combined loop response with keys: ok, loop_id, task_intake,
        context_preview, run, status, validation, warnings, evidence, next
    """
    # Step 0: Basic input validation
    if not isinstance(raw, dict):
        return {
            "ok": False,
            "loop_id": "",
            "validation": {"valid": False, "errors": ["Request must be a JSON object."], "warnings": []},
            "status": {"state": "validation_failed", "phase": "mock_loop", "message": "Request must be a JSON object.", "is_terminal": True, "progress": 0, "updated_by": "mock_loop"},
            "warnings": [],
            "evidence": {"mock_loop": True, "execution_performed": False},
        }

    # Step 1: Normalize or accept provided task_intake
    if "task_intake" in raw and isinstance(raw.get("task_intake"), dict):
        # Assume caller provided a normalized task intake (from normalize)
        normalized_task = raw["task_intake"]
        # If caller provided a wrapper like {"normalized": {...}, "task_intake_id": ...}, handle it
        if "normalized" in normalized_task and isinstance(normalized_task["normalized"], dict):
            normalized_task = normalized_task["normalized"]
            task_intake_id = raw["task_intake"].get("task_intake_id", "")
        else:
            task_intake_id = normalized_task.get("task_intake_id", "")
        norm_result = {"ok": True, "normalized_task": normalized_task, "task_intake_id": task_intake_id}
    else:
        norm_result = normalize_task_intake(raw)
        if not norm_result.get("ok"):
            return {
                "ok": False,
                "loop_id": "",
                "task_intake": norm_result,
                "validation": {"valid": False, "errors": norm_result.get("validation", {}).get("errors", []), "warnings": norm_result.get("validation", {}).get("warnings", [])},
                "status": {"state": "validation_failed", "phase": "normalize", "message": "Normalization failed.", "is_terminal": True, "progress": 0, "updated_by": "mock_loop"},
                "warnings": [],
                "evidence": {"normalize": norm_result, "mock_loop": True, "execution_performed": False},
            }
        normalized_task = norm_result.get("normalized_task", {})
        task_intake_id = norm_result.get("task_intake_id", "")

    # Prepare context preview request
    cp_request = {"task_intake": {**normalized_task, "task_intake_id": task_intake_id}}
    # Merge through optional preview options if present in raw
    if "include_sections" in raw:
        cp_request["include_sections"] = raw["include_sections"]
    if "preview_options" in raw:
        cp_request["preview_options"] = raw["preview_options"]

    # Step 2: Context preview
    if "context_preview" in raw and isinstance(raw.get("context_preview"), dict):
        # Caller provided a context_preview dict (maybe from previous step)
        cp_result = raw["context_preview"]
    else:
        cp_result = generate_context_preview(cp_request)
        if not cp_result.get("ok"):
            return {
                "ok": False,
                "loop_id": "",
                "task_intake": norm_result,
                "context_preview": cp_result,
                "validation": {"valid": False, "errors": cp_result.get("validation", {}).get("errors", []), "warnings": cp_result.get("validation", {}).get("warnings", [])},
                "status": {"state": "validation_failed", "phase": "context_preview", "message": "Context preview failed.", "is_terminal": True, "progress": 0, "updated_by": "mock_loop"},
                "warnings": [],
                "evidence": {"normalize": norm_result, "context_preview": cp_result, "mock_loop": True, "execution_performed": False},
            }

    cp_id = cp_result.get("context_preview_id", "")

    # Prepare runs request
    if "context_preview" in raw and isinstance(raw.get("context_preview"), dict):
        # Use the provided context_preview as-is (to allow validation of mismatched ids)
        runs_request = {
            "task_intake": {**normalized_task, "task_intake_id": task_intake_id},
            "context_preview": cp_result,
        }
    else:
        runs_request = {
            "task_intake": {**normalized_task, "task_intake_id": task_intake_id},
            "context_preview": {"context_preview_id": cp_id, "task_intake_id": task_intake_id, "preview": cp_result.get("preview", {})},
        }
    if "run_options" in raw:
        runs_request["run_options"] = raw["run_options"]

    # Step 3: Create mock run
    run_result = create_mock_run(runs_request)
    if not run_result.get("ok"):
        return {
            "ok": False,
            "loop_id": "",
            "task_intake": norm_result,
            "context_preview": cp_result,
            "run": run_result,
            "validation": {"valid": False, "errors": run_result.get("validation", {}).get("errors", []), "warnings": run_result.get("validation", {}).get("warnings", [])},
            "status": {"state": "validation_failed", "phase": "runs", "message": "Run creation failed.", "is_terminal": True, "progress": 0, "updated_by": "mock_loop"},
            "warnings": [],
            "evidence": {"normalize": norm_result, "context_preview": cp_result, "run": run_result, "mock_loop": True, "execution_performed": False},
        }

    # Success: compose final response
    task_goal = normalized_task.get("task_goal", "")
    loop_id = _make_loop_id(task_goal, cp_id)

    return {
        "ok": True,
        "loop_id": loop_id,
        "task_intake": {"normalized": normalized_task, "task_intake_id": task_intake_id, "raw_normalize_result": norm_result},
        "context_preview": cp_result,
        "run": run_result,
        "status": {"state": "completed_mock_loop", "phase": "mock_loop", "message": "Mock app loop completed. No execution performed.", "is_terminal": True, "progress": 100, "updated_by": "mock_loop"},
        "validation": {"valid": True, "errors": [], "warnings": run_result.get("validation", {}).get("warnings", [])},
        "warnings": ["No real execution was performed. This is a mock loop."],
        "evidence": {"normalize": norm_result, "context_preview": cp_result, "run": run_result, "mock_loop": True, "execution_performed": False},
        "next": f"/runs/{run_result.get('run_id')}/status",
    }
