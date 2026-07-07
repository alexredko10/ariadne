"""
Pipeline Runner for Ariadne — fourth executable Production Line PR.

Connects PR 0124 (Agent Runner Bridge), PR 0125 (Prompt Composer), and
PR 0126 (Verdict Parser) into a single deterministic call that executes
the full agent sequence:

    compose prompts → planner → artifact check → plan-review → gate →
    coder → precommit-review → gate

Stops on block.  Returns structured pipeline result.
No git boundary, no CLI, no persistence, no retry execution.

Core principle:
    Agent output is not evidence.  Runtime/file-captured artifacts are
    evidence.  The substrate exists to run the loop — the human must stop
    being the orchestrator.
"""

from __future__ import annotations

import dataclasses
import hashlib
import os
from typing import Any, Callable, Optional


# ---------------------------------------------------------------------------
# PipelineRunnerStatus — final pipeline status
# ---------------------------------------------------------------------------


class PipelineRunnerStatus(str):
    """Final pipeline status values."""

    COMPLETED = "completed"
    COMPLETED_WITH_WARNING = "completed_with_warning"
    STOPPED = "stopped"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# PipelineRunnerRequest — input dataclass
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class PipelineRunnerRequest:
    """Input parameters for running the PR pipeline."""

    pr_id: str
    branch: str
    task_title: str
    task_description: str
    repo_root: str = "."
    agents_dir: str = "agents"
    project_memory_dir: str = ".project-memory"
    workdir: Optional[str] = None
    allow_docker: bool = False
    prompt_composer: Optional[Callable] = None
    bridge_runner: Optional[Callable] = None
    artifact_reader: Optional[Callable] = None
    verdict_parser: Optional[Callable] = None
    clock_provider: Optional[Callable] = None
    payload_artifact_path: str = ""
    overwrite_allowed: bool = False


# ---------------------------------------------------------------------------
# PipelineStepResult — single step result
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class PipelineStepResult:
    """Result of a single pipeline step."""

    step_name: str
    status: str
    reason_codes: tuple[str, ...]
    agent_name: Optional[str] = None
    prompt_hash: Optional[str] = None
    expected_artifact_path: Optional[str] = None
    artifact_exists: bool = False
    artifact_hash: Optional[str] = None
    artifact_line_count: Optional[int] = None
    bridge_status: Optional[str] = None
    bridge_proof_summary: Optional[str] = None
    parsed_verdict: Optional[str] = None
    next_action: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    details: Optional[str] = None


# ---------------------------------------------------------------------------
# PipelineGateResult — gate result
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class PipelineGateResult:
    """Result of a pipeline gate."""

    gate_name: str
    verdict: str
    normalized_verdict: str
    has_blockers: bool
    next_action: str
    is_retry_candidate: bool
    human_required: bool
    artifact_hash: str
    parsed: Optional[dict[str, Any]]


# ---------------------------------------------------------------------------
# PipelineRunnerResult — final result
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class PipelineRunnerResult:
    """Final result of a pipeline run."""

    status: str
    reason_codes: tuple[str, ...]
    pr_id: str
    branch: str
    task_title: str
    prompt_order: tuple[str, ...]
    step_results: tuple[PipelineStepResult, ...]
    gate_results: tuple[PipelineGateResult, ...]
    final_action: str
    stopped_at: Optional[str]
    stop_reason: Optional[str]
    has_blockers: bool
    warnings: tuple[str, ...]
    artifact_hashes: dict[str, str]
    proof_summary: str
    started_at: Optional[str]
    finished_at: Optional[str]
    details: Optional[str]


# ---------------------------------------------------------------------------
# Stable reason codes
# ---------------------------------------------------------------------------

REASON_MISSING_PLANNER_ARTIFACT = "missing_planner_artifact"
REASON_MISSING_REVIEW_ARTIFACT = "missing_review_artifact"
REASON_CODER_STEP_FAILED = "coder_step_failed"
REASON_GATE_STOP = "gate_stop"
REASON_PIPELINE_STOPPED = "pipeline_stopped"
REASON_PIPELINE_COMPLETED = "pipeline_completed"
REASON_COMPOSE_FAILED = "compose_failed"
REASON_BRIDGE_FAILED = "bridge_failed"
REASON_PARSER_FAILED = "parser_failed"

# ---------------------------------------------------------------------------
# Default artifact reader
# ---------------------------------------------------------------------------


def _default_artifact_reader(path: str) -> Optional[str]:
    """Read an artifact file and return its text.

    Returns ``None`` if the file does not exist or cannot be read.
    """
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


# ---------------------------------------------------------------------------
# Run PR pipeline
# ---------------------------------------------------------------------------


def run_pr_pipeline(
    request: PipelineRunnerRequest,
) -> PipelineRunnerResult:
    """Run the full PR pipeline.

    Parameters
    ----------
    request:
        Input parameters including PR identity, task description, and
        optional injected boundaries.

    Returns
    -------
    PipelineRunnerResult
        ``status="completed"`` when all gates pass.
        ``status="completed_with_warning"`` when gates pass with warnings.
        ``status="stopped"`` when a gate blocks.
        ``status="failed"`` when composition fails.
    """
    codes: list[str] = []
    warnings: list[str] = []
    step_results: list[PipelineStepResult] = []
    gate_results: list[PipelineGateResult] = []
    artifact_hashes: dict[str, str] = {}
    prompt_order = ("planner", "plan-review", "coder", "precommit-review")
    started_at = request.clock_provider() if request.clock_provider else None

    # Resolve injected boundaries
    composer_fn = request.prompt_composer
    bridge_fn = request.bridge_runner
    reader_fn = request.artifact_reader or _default_artifact_reader
    parser_fn = request.verdict_parser

    # -----------------------------------------------------------------------
    # Step 1: compose_prompts
    # -----------------------------------------------------------------------
    step_start = request.clock_provider() if request.clock_provider else None
    compose_result = None
    compose_codes: list[str] = []

    if composer_fn is not None:
        compose_result = composer_fn(request)
    else:
        from runner.prompt_composer import PromptComposerRequest, compose_pr_prompts
        composer_request = PromptComposerRequest(
            pr_id=request.pr_id,
            branch=request.branch,
            task_title=request.task_title,
            task_description=request.task_description,
            agents_dir=request.agents_dir,
            repo_root=request.repo_root,
        )
        compose_result = compose_pr_prompts(composer_request)

    if compose_result is None or getattr(compose_result, "status", "failed") in ("failed", "blocked"):
        compose_codes.append(REASON_COMPOSE_FAILED)
        step_end = request.clock_provider() if request.clock_provider else None
        step_results.append(PipelineStepResult(
            step_name="compose_prompts",
            status="failed",
            reason_codes=tuple(compose_codes),
            started_at=step_start,
            finished_at=step_end,
            details="Prompt composition failed",
        ))
        return PipelineRunnerResult(
            status=PipelineRunnerStatus.FAILED,
            reason_codes=tuple(compose_codes),
            pr_id=request.pr_id,
            branch=request.branch,
            task_title=request.task_title,
            prompt_order=prompt_order,
            step_results=tuple(step_results),
            gate_results=(),
            final_action="stop",
            stopped_at="compose_prompts",
            stop_reason="Prompt composition failed",
            has_blockers=False,
            warnings=tuple(warnings),
            artifact_hashes=artifact_hashes,
            proof_summary="Pipeline failed at compose_prompts",
            started_at=started_at,
            finished_at=request.clock_provider() if request.clock_provider else None,
            details="Prompt composition failed",
        )

    prompt_packets = getattr(compose_result, "prompt_packets", ())
    compose_warnings = getattr(compose_result, "warnings", ())
    warnings.extend(list(compose_warnings))

    step_end = request.clock_provider() if request.clock_provider else None
    step_results.append(PipelineStepResult(
        step_name="compose_prompts",
        status="completed",
        reason_codes=(),
        started_at=step_start,
        finished_at=step_end,
        details=f"Composed {len(prompt_packets)} prompt packets",
    ))

    # -----------------------------------------------------------------------
    # Helper: run a bridge step
    # -----------------------------------------------------------------------
    def _run_bridge_step(
        step_name: str,
        agent_name: str,
        prompt_packet: Any,
    ) -> PipelineStepResult:
        s_start = request.clock_provider() if request.clock_provider else None
        prompt_text = getattr(prompt_packet, "prompt_text", "")
        prompt_hash_val = getattr(prompt_packet, "prompt_hash", "")
        expected_path = getattr(prompt_packet, "expected_output_path", "")

        # Override coder expected_output_path if payload_artifact_path is set
        if agent_name == "coder" and request.payload_artifact_path:
            expected_path = request.payload_artifact_path

        bridge_codes: list[str] = []

        if bridge_fn is not None:
            bridge_result = bridge_fn(
                agent_name,
                prompt_text,
                expected_artifact_path=expected_path,
                overwrite_allowed=request.overwrite_allowed,
            )
        else:
            from runner.agent_runner_bridge import run_agent_runner_bridge
            bridge_result = run_agent_runner_bridge(
                agent_name=agent_name,
                task_prompt=prompt_text,
                agents_dir=request.agents_dir,
                workdir=request.workdir,
                allow_docker=request.allow_docker,
                output_dir=request.repo_root,
                expected_artifact_path=expected_path,
                overwrite_allowed=request.overwrite_allowed,
            )

        bridge_status = getattr(bridge_result, "status", "failed")
        bridge_proof = getattr(bridge_result, "proof_summary", "")
        bridge_codes_list = list(getattr(bridge_result, "reason_codes", ()))
        bridge_codes.extend(bridge_codes_list)

        s_end = request.clock_provider() if request.clock_provider else None

        return PipelineStepResult(
            step_name=step_name,
            status=bridge_status,
            reason_codes=tuple(bridge_codes),
            agent_name=agent_name,
            prompt_hash=prompt_hash_val,
            expected_artifact_path=expected_path,
            bridge_status=bridge_status,
            bridge_proof_summary=bridge_proof,
            started_at=s_start,
            finished_at=s_end,
        )

    # -----------------------------------------------------------------------
    # Helper: check artifact exists
    # -----------------------------------------------------------------------
    def _check_artifact(step_name: str, path: str) -> PipelineStepResult:
        c_start = request.clock_provider() if request.clock_provider else None
        text = reader_fn(path)
        exists = text is not None
        ahash = ""
        line_count = 0
        if exists and text is not None:
            ahash = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
            line_count = len(text.split("\n"))
            artifact_hashes[path] = ahash
        c_end = request.clock_provider() if request.clock_provider else None
        return PipelineStepResult(
            step_name=step_name,
            status="completed" if exists else "failed",
            reason_codes=() if exists else (REASON_MISSING_PLANNER_ARTIFACT,),
            expected_artifact_path=path,
            artifact_exists=exists,
            artifact_hash=ahash,
            artifact_line_count=line_count,
            started_at=c_start,
            finished_at=c_end,
        )

    # -----------------------------------------------------------------------
    # Helper: run a gate
    # -----------------------------------------------------------------------
    def _run_gate(
        gate_name: str,
        artifact_path: str,
    ) -> tuple[PipelineGateResult, PipelineStepResult, bool]:
        g_start = request.clock_provider() if request.clock_provider else None
        g_codes: list[str] = []

        # Read artifact
        text = reader_fn(artifact_path)
        if text is None:
            g_codes.append(REASON_MISSING_REVIEW_ARTIFACT)
            g_end = request.clock_provider() if request.clock_provider else None
            gate_result = PipelineGateResult(
                gate_name=gate_name,
                verdict="",
                normalized_verdict="invalid",
                has_blockers=False,
                next_action="stop",
                is_retry_candidate=False,
                human_required=False,
                artifact_hash="",
                parsed=None,
            )
            step_result = PipelineStepResult(
                step_name=f"{gate_name}_gate",
                status="failed",
                reason_codes=tuple(g_codes),
                expected_artifact_path=artifact_path,
                artifact_exists=False,
                parsed_verdict="invalid",
                next_action="stop",
                started_at=g_start,
                finished_at=g_end,
                details="Missing review artifact",
            )
            return gate_result, step_result, True  # stop

        ahash = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
        line_count = len(text.split("\n"))
        artifact_hashes[artifact_path] = ahash

        # Parse artifact
        if parser_fn is not None:
            parsed = parser_fn(text)
        else:
            from runner.verdict_parser import VerdictParserRequest, parse_review_artifact, decide_next_action
            parser_request = VerdictParserRequest(
                artifact_path=artifact_path,
                artifact_text=text,
                strict=False,
            )
            parsed = parse_review_artifact(parser_request)

        if parsed is None:
            g_codes.append(REASON_PARSER_FAILED)
            g_end = request.clock_provider() if request.clock_provider else None
            gate_result = PipelineGateResult(
                gate_name=gate_name,
                verdict="",
                normalized_verdict="invalid",
                has_blockers=False,
                next_action="stop",
                is_retry_candidate=False,
                human_required=False,
                artifact_hash=ahash,
                parsed=None,
            )
            step_result = PipelineStepResult(
                step_name=f"{gate_name}_gate",
                status="failed",
                reason_codes=tuple(g_codes),
                expected_artifact_path=artifact_path,
                artifact_exists=True,
                artifact_hash=ahash,
                artifact_line_count=line_count,
                parsed_verdict="invalid",
                next_action="stop",
                started_at=g_start,
                finished_at=g_end,
                details="Parser returned None",
            )
            return gate_result, step_result, True  # stop

        # Decide next action
        if parser_fn is not None:
            decision = parsed  # parser_fn returns VerdictDecision directly
        else:
            decision = decide_next_action(parsed)

        next_action = getattr(decision, "next_action", "stop")
        normalized_verdict = getattr(decision, "normalized_verdict", "invalid")
        has_blockers = getattr(decision, "has_blockers", False)
        is_retry = getattr(decision, "is_retry_candidate", False)
        human_req = getattr(decision, "human_required", False)

        # Build parsed dict
        parsed_dict = {
            "review_type": getattr(parsed, "review_type", ""),
            "raw_verdict": getattr(parsed, "raw_verdict", ""),
            "normalized_verdict": normalized_verdict,
            "has_blockers": has_blockers,
            "blockers": list(getattr(parsed, "blockers", ())),
            "artifact_hash": getattr(parsed, "artifact_hash", ahash),
            "artifact_line_count": getattr(parsed, "artifact_line_count", line_count),
        }

        # Determine if stop
        should_stop = next_action in ("stop", "invalid") or has_blockers or human_req

        if should_stop:
            g_codes.append(REASON_GATE_STOP)

        g_end = request.clock_provider() if request.clock_provider else None

        gate_result = PipelineGateResult(
            gate_name=gate_name,
            verdict=getattr(parsed, "raw_verdict", ""),
            normalized_verdict=normalized_verdict,
            has_blockers=has_blockers,
            next_action=next_action,
            is_retry_candidate=is_retry,
            human_required=human_req,
            artifact_hash=ahash,
            parsed=parsed_dict,
        )

        step_result = PipelineStepResult(
            step_name=f"{gate_name}_gate",
            status="completed" if not should_stop else "blocked",
            reason_codes=tuple(g_codes),
            expected_artifact_path=artifact_path,
            artifact_exists=True,
            artifact_hash=ahash,
            artifact_line_count=line_count,
            parsed_verdict=normalized_verdict,
            next_action=next_action,
            started_at=g_start,
            finished_at=g_end,
            details=f"Gate {gate_name}: {next_action}",
        )

        return gate_result, step_result, should_stop

    # -----------------------------------------------------------------------
    # Step 2: planner
    # -----------------------------------------------------------------------
    planner_packet = prompt_packets[0] if len(prompt_packets) > 0 else None
    if planner_packet is not None:
        planner_step = _run_bridge_step("planner", "planner", planner_packet)
        step_results.append(planner_step)

        # Step 3: planner_artifact_check
        planner_expected_path = getattr(planner_packet, "expected_output_path", "")
        full_planner_path = os.path.join(request.repo_root, planner_expected_path) if planner_expected_path else ""
        artifact_check = _check_artifact("planner_artifact_check", full_planner_path)
        step_results.append(artifact_check)

        if not artifact_check.artifact_exists:
            codes.append(REASON_MISSING_PLANNER_ARTIFACT)
            return _build_final_result(
                request, step_results, gate_results, artifact_hashes,
                prompt_order, warnings, codes, started_at,
                status=PipelineRunnerStatus.STOPPED,
                final_action="stop",
                stopped_at="planner_artifact_check",
                stop_reason="Missing planner artifact",
                details="Planner artifact not found at expected path",
            )

    # -----------------------------------------------------------------------
    # Step 4: plan_review
    # -----------------------------------------------------------------------
    plan_review_packet = prompt_packets[1] if len(prompt_packets) > 1 else None
    if plan_review_packet is not None:
        plan_review_step = _run_bridge_step("plan_review", "plan-review", plan_review_packet)
        step_results.append(plan_review_step)

        # Step 5: plan_review_gate
        plan_review_path = getattr(plan_review_packet, "expected_output_path", "")
        full_plan_review_path = os.path.join(request.repo_root, plan_review_path) if plan_review_path else ""
        gate_result, gate_step, should_stop = _run_gate("plan-review", full_plan_review_path)
        gate_results.append(gate_result)
        step_results.append(gate_step)

        if should_stop:
            codes.append(REASON_GATE_STOP)
            return _build_final_result(
                request, step_results, gate_results, artifact_hashes,
                prompt_order, warnings, codes, started_at,
                status=PipelineRunnerStatus.STOPPED,
                final_action="stop",
                stopped_at="plan_review_gate",
                stop_reason="Plan-review gate stopped",
                details=f"Plan-review gate: {gate_result.next_action}",
            )

    # -----------------------------------------------------------------------
    # Step 6: coder
    # -----------------------------------------------------------------------
    coder_packet = prompt_packets[2] if len(prompt_packets) > 2 else None
    if coder_packet is not None:
        coder_step = _run_bridge_step("coder", "coder", coder_packet)
        step_results.append(coder_step)

        if coder_step.status in ("failed", "blocked"):
            codes.append(REASON_CODER_STEP_FAILED)
            return _build_final_result(
                request, step_results, gate_results, artifact_hashes,
                prompt_order, warnings, codes, started_at,
                status=PipelineRunnerStatus.STOPPED,
                final_action="stop",
                stopped_at="coder",
                stop_reason="Coder step failed",
                details=f"Coder bridge status: {coder_step.status}",
            )

    # -----------------------------------------------------------------------
    # Step 7: precommit_review
    # -----------------------------------------------------------------------
    precommit_packet = prompt_packets[3] if len(prompt_packets) > 3 else None
    if precommit_packet is not None:
        precommit_step = _run_bridge_step("precommit_review", "precommit-review", precommit_packet)
        step_results.append(precommit_step)

        # Step 8: precommit_gate
        precommit_path = getattr(precommit_packet, "expected_output_path", "")
        full_precommit_path = os.path.join(request.repo_root, precommit_path) if precommit_path else ""
        gate_result, gate_step, should_stop = _run_gate("precommit-review", full_precommit_path)
        gate_results.append(gate_result)
        step_results.append(gate_step)

        if should_stop:
            codes.append(REASON_GATE_STOP)
            return _build_final_result(
                request, step_results, gate_results, artifact_hashes,
                prompt_order, warnings, codes, started_at,
                status=PipelineRunnerStatus.STOPPED,
                final_action="stop",
                stopped_at="precommit_gate",
                stop_reason="Precommit-review gate stopped",
                details=f"Precommit-review gate: {gate_result.next_action}",
            )

    # -----------------------------------------------------------------------
    # Determine final status
    # -----------------------------------------------------------------------
    codes.append(REASON_PIPELINE_COMPLETED)

    # Check if any gate had warnings
    has_warnings = len(warnings) > 0 or any(
        g.next_action == "continue_with_warning" for g in gate_results
    )

    if has_warnings:
        final_status = PipelineRunnerStatus.COMPLETED_WITH_WARNING
    else:
        final_status = PipelineRunnerStatus.COMPLETED

    return _build_final_result(
        request, step_results, gate_results, artifact_hashes,
        prompt_order, warnings, codes, started_at,
        status=final_status,
        final_action="continue",
        stopped_at=None,
        stop_reason=None,
        details="Pipeline completed successfully",
    )


# ---------------------------------------------------------------------------
# Build final result
# ---------------------------------------------------------------------------


def _build_final_result(
    request: PipelineRunnerRequest,
    step_results: list[PipelineStepResult],
    gate_results: list[PipelineGateResult],
    artifact_hashes: dict[str, str],
    prompt_order: tuple[str, ...],
    warnings: list[str],
    codes: list[str],
    started_at: Optional[str],
    status: str,
    final_action: str,
    stopped_at: Optional[str],
    stop_reason: Optional[str],
    details: Optional[str],
) -> PipelineRunnerResult:
    """Build the final PipelineRunnerResult."""
    has_blockers = any(g.has_blockers for g in gate_results)

    # Build proof summary
    if status == PipelineRunnerStatus.COMPLETED:
        proof_summary = "Pipeline completed: all gates passed"
    elif status == PipelineRunnerStatus.COMPLETED_WITH_WARNING:
        proof_summary = "Pipeline completed with warnings"
    elif status == PipelineRunnerStatus.STOPPED:
        proof_summary = f"Pipeline stopped at {stopped_at}: {stop_reason}"
    else:
        proof_summary = f"Pipeline failed: {details}"

    finished_at = request.clock_provider() if request.clock_provider else None

    return PipelineRunnerResult(
        status=status,
        reason_codes=tuple(codes),
        pr_id=request.pr_id,
        branch=request.branch,
        task_title=request.task_title,
        prompt_order=prompt_order,
        step_results=tuple(step_results),
        gate_results=tuple(gate_results),
        final_action=final_action,
        stopped_at=stopped_at,
        stop_reason=stop_reason,
        has_blockers=has_blockers,
        warnings=tuple(warnings),
        artifact_hashes=artifact_hashes,
        proof_summary=proof_summary,
        started_at=started_at,
        finished_at=finished_at,
        details=details,
    )
