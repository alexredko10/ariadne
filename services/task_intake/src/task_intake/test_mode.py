"""
Ariadne test-mode execution entrypoint.

Runnable via::

    PYTHONPATH=services/task_intake/src:services/runner/src \\
        python -m task_intake.test_mode --task "Ariadne test run" --json

Exercises the same code path as ``POST /runs/execute`` through
``run_mock_execution_handoff``.

No new HTTP route.  No server.py changes.  No direct runner imports.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from task_intake.execution_handoff import run_mock_execution_handoff

_APPROVAL_MAP = {
    "not_required": None,
    "pending": {"required": True, "approved": False},
    "approved": {"required": True, "approved": True},
    "denied": {"required": True, "approved": False},
    "after_execution": {"required": True, "after_execution": True},
}


# ---------------------------------------------------------------------------
# Test mode callable
# ---------------------------------------------------------------------------


def run_test_mode(payload: dict) -> dict:
    """Run Ariadne in test mode with a given payload.

    Parameters
    ----------
    payload
        A dict with at least a ``task`` string.

    Returns
    -------
    dict
        Deterministic test-mode result from the execution handoff path.
    """
    if not isinstance(payload, dict):
        return {
            "ok": False,
            "mode": "test",
            "runtime_status": "error",
            "execution_request": None,
            "execution_result": None,
            "execution_envelope": None,
            "review_boundary": None,
            "errors": [{"code": "invalid_payload", "message": "payload must be a dict."}],
            "warnings": [],
            "metadata": {"entrypoint": "test_mode", "version": "0.1"},
        }

    task = payload.get("task", "")
    if not task or not isinstance(task, str):
        return {
            "ok": False,
            "mode": "test",
            "runtime_status": "error",
            "execution_request": None,
            "execution_result": None,
            "execution_envelope": None,
            "review_boundary": None,
            "errors": [{"code": "invalid_payload", "message": "task is required and must be a non-empty string."}],
            "warnings": [],
            "metadata": {"entrypoint": "test_mode", "version": "0.1"},
        }

    # Map payload to handoff input
    raw: dict[str, Any] = {
        "raw_task": task,
        "requested_adapter": payload.get("requested_adapter", "noop"),
        "execution_mode": payload.get("execution_mode", "dry_run"),
    }

    # Add approval if provided
    approval_status = payload.get("execution_approval")
    if isinstance(approval_status, dict):
        raw["execution_approval"] = approval_status

    # Call handoff
    handoff_result = run_mock_execution_handoff(raw)

    return {
        "ok": handoff_result.get("ok", False),
        "mode": "test",
        "runtime_status": handoff_result.get("runtime_status") or (
            "error" if not handoff_result.get("ok") else "completed"
        ),
        "execution_request": handoff_result.get("execution_request"),
        "execution_result": handoff_result.get("execution_result"),
        "execution_envelope": handoff_result.get("execution_envelope"),
        "review_boundary": handoff_result.get("review_boundary"),
        "errors": handoff_result.get("errors", []),
        "warnings": handoff_result.get("warnings", []),
        "metadata": {"entrypoint": "test_mode", "version": "0.1"},
    }


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for Ariadne test mode.

    Parameters
    ----------
    argv
        Command-line arguments (default: ``sys.argv[1:]``).

    Returns
    -------
    int
        Exit code (0 = success).
    """
    parser = argparse.ArgumentParser(
        description="Ariadne test-mode execution entrypoint",
    )
    parser.add_argument("--task", "-t", required=True, help="Task description text")
    parser.add_argument("--json", action="store_true", help="Print JSON output")
    parser.add_argument("--adapter", default="noop", help="Adapter identifier (default: noop)")
    parser.add_argument("--mode", default="dry_run", help="Execution mode (default: dry_run)")
    parser.add_argument(
        "--approval-status",
        choices=list(_APPROVAL_MAP.keys()),
        default="not_required",
        help=f"Approval status ({', '.join(_APPROVAL_MAP.keys())})",
    )

    args = parser.parse_args(argv)

    approval = _APPROVAL_MAP.get(args.approval_status, None)

    payload: dict[str, Any] = {
        "task": args.task,
        "requested_adapter": args.adapter,
        "execution_mode": args.mode,
    }
    if approval is not None:
        payload["execution_approval"] = approval

    result = run_test_mode(payload)

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"ok: {result.get('ok')}")
        print(f"mode: {result.get('mode')}")
        print(f"runtime_status: {result.get('runtime_status')}")

    return 0 if result.get("ok") else 1


# ---------------------------------------------------------------------------
# Direct execution
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    sys.exit(main())
