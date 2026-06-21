"""
Ariadne runtime smoke demo — proves Core runtime layers work together.

Deterministic, model-free, stdlib-only.

Usage::

    PYTHONPATH=services/core/src:services/runner/src python -m runner runtime-smoke
"""

from __future__ import annotations

import datetime
import json
import sys
from typing import Any


# ---------------------------------------------------------------------------
# Deterministic timestamp (no runtime clock)
# ---------------------------------------------------------------------------

T0 = datetime.datetime(2026, 6, 21, 12, 0, 0, tzinfo=datetime.timezone.utc)
T1 = datetime.datetime(2026, 6, 21, 12, 5, 0, tzinfo=datetime.timezone.utc)
T2 = datetime.datetime(2026, 6, 21, 12, 10, 0, tzinfo=datetime.timezone.utc)


# ---------------------------------------------------------------------------
# Smoke demo
# ---------------------------------------------------------------------------


def run_runtime_smoke_demo() -> dict[str, Any]:
    """Execute a deterministic runtime lifecycle and return the result dict.

    Returns
    -------
    dict
        A JSON-serializable dict with smoke demo results.
    """
    # Lazy imports — Core runtime modules may not be on sys.path when
    # this module is imported but not executed (e.g. doctor CLI).
    from core.runtime_substrate import (
        AgentRole,
        Checkpoint,
        RunState,
        RunStatus,
        StepBoundary,
        StepStatus,
    )
    from core.runtime.transitions import (
        validate_checkpoint_attachment,
        validate_final_report_attachment,
        validate_run_transition,
        validate_step_transition,
    )
    from core.runtime.verification import create_verification_evidence
    from core.runtime.store import InMemoryRuntimeStore

    store = InMemoryRuntimeStore()

    # 1. Create run
    run = RunState(
        run_id="smoke-run-001",
        task_id="smoke-task-001",
        purpose_id="smoke-purpose-001",
        domain="smoke",
        status=RunStatus.PENDING,
        steps=[],
        created_at=T0,
        updated_at=T0,
    )
    store.create_run(run)

    # 2. Create step 1, transition to COMPLETED
    step1 = StepBoundary(
        step_id="step-001",
        agent_role=AgentRole.WORKER_CODER,
        status=StepStatus.PENDING,
    )
    run = store.get_run("smoke-run-001")
    run.append_step(step1)

    # step PENDING -> RUNNING -> COMPLETED
    validate_step_transition(StepStatus.PENDING, StepStatus.RUNNING)
    run.steps[0].status = StepStatus.RUNNING
    run.steps[0].started_at = T1
    validate_step_transition(StepStatus.RUNNING, StepStatus.COMPLETED)
    run.steps[0].status = StepStatus.COMPLETED
    run.steps[0].completed_at = T2

    # run PENDING -> RUNNING
    validate_run_transition(RunStatus.PENDING, RunStatus.RUNNING)
    run.status = RunStatus.RUNNING
    store.save_run(run)

    # 3. Create checkpoint for step 1
    cp1 = Checkpoint(
        checkpoint_id="cp-001",
        run_id="smoke-run-001",
        step_id="step-001",
        captured_at=T2,
        run_state_hash="smoke-hash-001",
        artifact_ids=["artifact-001"],
    )
    validate_checkpoint_attachment(run, cp1)
    run = store.get_run("smoke-run-001")
    run.steps[0].checkpoint_id = "cp-001"
    store.save_run(run)

    # 4. Create step 2, transition to COMPLETED
    run = store.get_run("smoke-run-001")
    step2 = StepBoundary(
        step_id="step-002",
        agent_role=AgentRole.REVIEWER,
        status=StepStatus.PENDING,
    )
    run.append_step(step2)

    # step PENDING -> RUNNING -> COMPLETED
    validate_step_transition(StepStatus.PENDING, StepStatus.RUNNING)
    run.steps[1].status = StepStatus.RUNNING
    run.steps[1].started_at = T2
    validate_step_transition(StepStatus.RUNNING, StepStatus.COMPLETED)
    run.steps[1].status = StepStatus.COMPLETED
    run.steps[1].completed_at = T2
    store.save_run(run)

    # 5. Attach verification evidence
    from core.runtime.verification import create_verification_evidence as _cve
    ev_pass = _cve(
        evidence_id="ev-pass-001",
        step_id="step-001",
        check_name="lint",
        status="passed",
        message="All lint checks passed",
    )
    ev_warn = _cve(
        evidence_id="ev-warn-001",
        step_id="step-002",
        check_name="coverage",
        status="warning",
        message="Coverage below threshold",
    )
    store.attach_verification_evidence("smoke-run-001", ev_pass)
    store.attach_verification_evidence("smoke-run-001", ev_warn)

    # 6. Build final report
    store.validate_final_report_readiness("smoke-run-001")
    report = store.build_final_report("smoke-run-001")

    # 7. Transition run to COMPLETED via final report
    from core.runtime.transitions import validate_final_report_attachment as _vfra
    run = store.get_run("smoke-run-001")
    _vfra(run, report)
    run.status = RunStatus.COMPLETED
    store.save_run(run)

    # 8. Produce deterministic output
    evidence_summary = store.summarize_verification_evidence("smoke-run-001")

    return {
        "smoke_demo": "runtime",
        "run_id": "smoke-run-001",
        "run_status": "completed",
        "step_count": 2,
        "checkpoint_count": 1,
        "evidence_summary": {
            "total": evidence_summary["total"],
            "passed": evidence_summary["passed"],
            "failed": evidence_summary["failed"],
            "warning": evidence_summary["warning"],
            "failing_evidence_ids": evidence_summary["failing_evidence_ids"],
            "warning_evidence_ids": evidence_summary["warning_evidence_ids"],
        },
        "final_report_present": True,
        "final_report_id": report.report_id,
    }


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Run the smoke demo and print JSON to stdout.

    Parameters
    ----------
    argv
        Command-line arguments (ignored for this subcommand).

    Returns
    -------
    int
        Exit code (0 = success).
    """
    try:
        result = run_runtime_smoke_demo()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        print(f"runtime smoke demo failed: {exc}", file=sys.stderr)
        return 1
