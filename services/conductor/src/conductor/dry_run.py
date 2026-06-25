"""
Ariadne conductor dry-run pipeline — deterministic, model-free, stdlib-only.

Demonstrates a phase-driven loop that the production conductor would use
to drive Core runtime substrate coordination without LLM execution.

Usage::

    PYTHONPATH=services/core/src:services/conductor/src python -m conductor dry-run
"""

from __future__ import annotations

import datetime
import json
import sys
from typing import Any, Callable


# ---------------------------------------------------------------------------
# Deterministic timestamps (no runtime clock)
# ---------------------------------------------------------------------------

T0 = datetime.datetime(2026, 6, 21, 12, 0, 0, tzinfo=datetime.timezone.utc)
T1 = datetime.datetime(2026, 6, 21, 12, 5, 0, tzinfo=datetime.timezone.utc)
T2 = datetime.datetime(2026, 6, 21, 12, 10, 0, tzinfo=datetime.timezone.utc)
T3 = datetime.datetime(2026, 6, 21, 12, 15, 0, tzinfo=datetime.timezone.utc)
T4 = datetime.datetime(2026, 6, 21, 12, 20, 0, tzinfo=datetime.timezone.utc)


# ---------------------------------------------------------------------------
# Deterministic compiler constants
# ---------------------------------------------------------------------------

REPO_ID = "ariadne"
PURPOSE_ID = "dry-run-purpose"
DOMAIN = "dry-run"
RISK_LEVEL = "low"
BASE_SHA = "dry-run-abc123"
INDEX_VERSION = "0.24"


# ---------------------------------------------------------------------------
# Phase context
# ---------------------------------------------------------------------------


class _PhaseContext:
    """Holds shared state for the dry-run phase loop."""

    def __init__(self) -> None:
        from core.runtime.store import InMemoryRuntimeStore
        self.store = InMemoryRuntimeStore()
        self.run_id = "dry-run-001"
        self.report: Any = None
        self.inputs: dict[str, Any] | None = None
        self.context_pack: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Phase functions
# ---------------------------------------------------------------------------


def _phase_initialize_run(ctx: _PhaseContext, ts: dict[str, Any]) -> None:
    from core.runtime_substrate import RunState, RunStatus
    run = RunState(
        run_id=ctx.run_id,
        task_id="dry-run-task-001",
        purpose_id="dry-run-purpose-001",
        domain="dry-run",
        status=RunStatus.PENDING,
        steps=[],
        created_at=ts["t0"],
        updated_at=ts["t0"],
    )
    ctx.store.create_run(run)


def _phase_plan_steps(ctx: _PhaseContext, ts: dict[str, Any]) -> None:
    from core.runtime_substrate import StepBoundary, AgentRole, StepStatus
    run = ctx.store.get_run(ctx.run_id)
    step1 = StepBoundary(
        step_id="step-001",
        agent_role=AgentRole.WORKER_CODER,
        status=StepStatus.PENDING,
    )
    step2 = StepBoundary(
        step_id="step-002",
        agent_role=AgentRole.REVIEWER,
        status=StepStatus.PENDING,
    )
    run.append_step(step1)
    run.append_step(step2)
    ctx.store.save_run(run)


def _phase_start_run(ctx: _PhaseContext, ts: dict[str, Any]) -> None:
    from core.runtime_substrate import RunStatus
    from core.runtime.transitions import validate_run_transition
    validate_run_transition(RunStatus.PENDING, RunStatus.RUNNING)
    run = ctx.store.get_run(ctx.run_id)
    run.status = RunStatus.RUNNING
    ctx.store.save_run(run)


def _phase_start_step(ctx: _PhaseContext, ts: dict[str, Any]) -> None:
    from core.runtime_substrate import StepStatus
    from core.runtime.transitions import validate_step_transition
    run = ctx.store.get_run(ctx.run_id)
    # Find the first PENDING step
    for step in run.steps:
        if step.status == StepStatus.PENDING:
            validate_step_transition(StepStatus.PENDING, StepStatus.RUNNING)
            step.status = StepStatus.RUNNING
            step.started_at = ts["t2"]
            break
    ctx.store.save_run(run)


def _phase_complete_step(ctx: _PhaseContext, ts: dict[str, Any]) -> None:
    from core.runtime_substrate import StepStatus
    from core.runtime.transitions import validate_step_transition
    run = ctx.store.get_run(ctx.run_id)
    for step in run.steps:
        if step.status == StepStatus.RUNNING:
            validate_step_transition(StepStatus.RUNNING, StepStatus.COMPLETED)
            step.status = StepStatus.COMPLETED
            step.completed_at = ts["t3"]
            break
    ctx.store.save_run(run)


def _phase_checkpoint(ctx: _PhaseContext, ts: dict[str, Any]) -> None:
    from core.runtime_substrate import Checkpoint
    from core.runtime.transitions import validate_checkpoint_attachment
    run = ctx.store.get_run(ctx.run_id)
    # Find the step without a checkpoint
    for step in run.steps:
        if step.checkpoint_id is None and step.status.value == "completed":
            cp = Checkpoint(
                checkpoint_id=f"cp-{step.step_id}",
                run_id=ctx.run_id,
                step_id=step.step_id,
                captured_at=ts["t4"],
                run_state_hash=f"hash-{step.step_id}",
                artifact_ids=[f"artifact-{step.step_id}"],
            )
            validate_checkpoint_attachment(run, cp)
            step.checkpoint_id = cp.checkpoint_id
            break
    ctx.store.save_run(run)


def _phase_attach_evidence(ctx: _PhaseContext, ts: dict[str, Any]) -> None:
    from core.runtime.verification import create_verification_evidence
    ev1 = create_verification_evidence(
        evidence_id="ev-pass-001",
        step_id="step-001",
        check_name="lint",
        status="passed",
        message="All lint checks passed",
    )
    ev2 = create_verification_evidence(
        evidence_id="ev-pass-002",
        step_id="step-002",
        check_name="verification",
        status="passed",
        message="All verification checks passed",
    )
    ctx.store.attach_verification_evidence(ctx.run_id, ev1)
    ctx.store.attach_verification_evidence(ctx.run_id, ev2)


def _phase_build_report(ctx: _PhaseContext, ts: dict[str, Any]) -> None:
    ctx.store.validate_final_report_readiness(ctx.run_id)
    ctx.report = ctx.store.build_final_report(ctx.run_id)


def _phase_complete_run(ctx: _PhaseContext, ts: dict[str, Any]) -> None:
    from core.runtime_substrate import RunStatus
    from core.runtime.transitions import validate_final_report_attachment
    run = ctx.store.get_run(ctx.run_id)
    validate_final_report_attachment(run, ctx.report)
    run.status = RunStatus.COMPLETED
    ctx.store.save_run(run)


# ---------------------------------------------------------------------------
# Context pack phases
# ---------------------------------------------------------------------------


def _phase_generate_context_pack_inputs(
    ctx: _PhaseContext,
    ts: dict[str, Any],
) -> None:
    from conductor.context_pack_inputs import build_context_pack_inputs
    ctx.inputs = build_context_pack_inputs(
        pr_id=ctx.run_id,
        task_goal="Dry-run context pack integration",
        source_contracts=["contract-a", "contract-b"],
        relevant_anchors=["anchor-001", "anchor-002"],
        allowed_paths=["services/**", "packages/**"],
        forbidden_paths=[".git/**", ".env"],
        cache_key_refs=[{"namespace": "context", "artifact_kind": "context_pack"}],
        known_risks=[
            {"id": "risk-001", "description": "Example risk", "severity": "low"},
        ],
        manual_checks_required=["Verify context pack fields"],
        context_freshness_status="fresh",
        context_freshness_last_verified="plan_steps",
        created_from_agent="conductor-dry-run",
        created_from_hook="before_plan",
        created_from_template="context-steward.before_plan.v1",
    )


def _phase_compile_context_pack(
    ctx: _PhaseContext,
    ts: dict[str, Any],
) -> None:
    from conductor.context_compiler import compile_context_pack
    ctx.context_pack = compile_context_pack(
        context_pack_inputs=ctx.inputs,
        repo_id=REPO_ID,
        purpose_id=PURPOSE_ID,
        domain=DOMAIN,
        risk_level=RISK_LEVEL,
        base_sha=BASE_SHA,
        index_version=INDEX_VERSION,
        task_subgraph=["services/conductor/src/conductor/dry_run.py"],
        relevant_files=["services/conductor/src/conductor/dry_run.py"],
    )


# ---------------------------------------------------------------------------
# Phase registry
# ---------------------------------------------------------------------------

_PHASES: list[tuple[str, Callable[[_PhaseContext, dict[str, Any]], None]]] = [
    ("initialize_run", _phase_initialize_run),
    ("plan_steps", _phase_plan_steps),
    ("generate_context_pack_inputs", _phase_generate_context_pack_inputs),
    ("compile_context_pack", _phase_compile_context_pack),
    ("start_run", _phase_start_run),
    ("start_step:step-001", _phase_start_step),
    ("complete_step:step-001", _phase_complete_step),
    ("checkpoint:step-001", _phase_checkpoint),
    ("start_step:step-002", _phase_start_step),
    ("complete_step:step-002", _phase_complete_step),
    ("checkpoint:step-002", _phase_checkpoint),
    ("attach_evidence", _phase_attach_evidence),
    ("build_final_report", _phase_build_report),
    ("complete_run", _phase_complete_run),
]


# ---------------------------------------------------------------------------
# Dry-run entrypoint
# ---------------------------------------------------------------------------


def run_conductor_dry_run() -> dict[str, Any]:
    """Execute a deterministic conductor dry-run pipeline.

    Returns
    -------
    dict
        A JSON-serializable dict with dry-run results.
    """
    ctx = _PhaseContext()
    ts = {"t0": T0, "t1": T1, "t2": T2, "t3": T3, "t4": T4}
    events: list[str] = []

    for name, phase_fn in _PHASES:
        phase_fn(ctx, ts)
        events.append(name)

    return _build_output(ctx, events)


def _build_output(ctx: _PhaseContext, events: list[str]) -> dict[str, Any]:
    """Build the deterministic output dict from the dry-run state."""
    report = ctx.store.build_final_report(ctx.run_id)
    evidence_summary = ctx.store.summarize_verification_evidence(ctx.run_id)
    run = ctx.store.get_run(ctx.run_id)

    return {
        "dry_run": "conductor",
        "run_id": ctx.run_id,
        "run_status": run.status.value,
        "planned_step_count": len(run.steps),
        "completed_step_count": sum(
            1 for s in run.steps if s.status.value == "completed"
        ),
        "checkpoint_count": sum(
            1 for s in run.steps if s.checkpoint_id is not None
        ),
        "evidence_summary": {
            "total": evidence_summary["total"],
            "passed": evidence_summary["passed"],
            "failed": evidence_summary["failed"],
            "warning": evidence_summary["warning"],
        },
        "final_report_present": True,
        "final_report_id": report.report_id,
        "conductor_events": events,
        "context_pack_summary": {
            "present": ctx.context_pack is not None,
            "context_pack_id": ctx.context_pack.get("context_pack_id") if ctx.context_pack else None,
            "task": ctx.context_pack.get("task") if ctx.context_pack else None,
            "domain": ctx.context_pack.get("domain") if ctx.context_pack else None,
            "risk_level": ctx.context_pack.get("risk_level") if ctx.context_pack else None,
            "risks": ctx.context_pack.get("risks", []) if ctx.context_pack else [],
            "anchors": ctx.context_pack.get("anchors", []) if ctx.context_pack else [],
            "invariants": ctx.context_pack.get("invariants", []) if ctx.context_pack else [],
            "section_count": len(ctx.context_pack) if ctx.context_pack else 0,
        },
    }


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Run the conductor dry-run and print JSON to stdout.

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
        result = run_conductor_dry_run()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        print(f"conductor dry-run failed: {exc}", file=sys.stderr)
        return 1
