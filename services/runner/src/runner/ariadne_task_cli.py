"""
Ariadne task CLI — second Stage 2 Closed Loop PR.

Minimal CLI surface that connects PR 0127 Pipeline Runner and PR 0128 Git
Boundary into a single command.  Default mode is safe dry-run.  Explicit
``--execute`` and ``--approve`` flags required for side effects.

Core principle:
    Agent output is not evidence.  Runtime/file-captured artifacts are
    evidence.  Git mutation is an external side effect and must be
    approval-gated.  Agents must not receive unattended git mutation
    rights.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Optional

from runner.git_boundary import (
    GitBoundaryRequest,
    GitBoundaryStatus,
    GitCommandSpec,
    prepare_git_boundary_plan,
    execute_git_boundary_plan,
)
from runner.pipeline_runner import (
    PipelineRunnerRequest,
    PipelineRunnerStatus,
    run_pr_pipeline,
)


# ---------------------------------------------------------------------------
# AriadneTaskCliStatus — status values
# ---------------------------------------------------------------------------


class AriadneTaskCliStatus(str):
    """Status values for ariadne task CLI operations."""

    COMPLETED = "completed"
    COMPLETED_WITH_WARNING = "completed_with_warning"
    STOPPED = "stopped"
    BLOCKED = "blocked"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# AriadneTaskCliRequest — aggregated input dataclass
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class AriadneTaskCliRequest:
    """Aggregated input parameters for CLI orchestration."""

    task_description: str
    pr_id: str = ""
    branch: str = ""
    base_branch: str = "main"
    repo_root: str = "."
    allowed_files: tuple[str, ...] = ()
    files_to_stage: tuple[str, ...] = ()
    commit_message: str = ""
    pr_title: Optional[str] = None
    pr_body: Optional[str] = None
    pr_body_path: Optional[str] = None
    dry_run: bool = True
    execute: bool = False
    approve: bool = False
    approved_by: Optional[str] = None
    approval_reason: Optional[str] = None
    json_output: bool = False


# ---------------------------------------------------------------------------
# AriadneTaskCliResult — structured CLI result
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class AriadneTaskCliResult:
    """Structured result of a CLI task operation."""

    status: str
    reason_codes: tuple[str, ...]
    task_description: str
    task_description_hash: str
    pipeline_status: Optional[str]
    pipeline_final_action: Optional[str]
    pipeline_has_blockers: Optional[bool]
    git_boundary_status: Optional[str]
    command_plan: Optional[list[dict[str, Any]]]
    execution_attempted: bool
    execution_results: tuple[dict[str, str], ...]
    warnings: tuple[str, ...]
    next_action: str
    started_at: Optional[str]
    finished_at: Optional[str]
    details: Optional[str]


# ---------------------------------------------------------------------------
# Stable reason codes
# ---------------------------------------------------------------------------

REASON_MISSING_TASK_DESCRIPTION = "missing_task_description"
REASON_PIPELINE_STOPPED = "pipeline_stopped"
REASON_PIPELINE_FAILED = "pipeline_failed"
REASON_GIT_BOUNDARY_BLOCKED = "git_boundary_blocked"
REASON_EXECUTION_REQUIRED = "execution_required"
REASON_APPROVAL_REQUIRED = "approval_required"
REASON_MISSING_APPROVED_BY = "missing_approved_by"
REASON_MISSING_APPROVAL_REASON = "missing_approval_reason"
REASON_EXECUTION_FAILED = "execution_failed"


# ---------------------------------------------------------------------------
# Parse CLI arguments
# ---------------------------------------------------------------------------


def parse_ariadne_task_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    """Parse CLI arguments for ``ariadne task``.

    Parameters
    ----------
    argv:
        Command-line argument list.  If ``None``, uses ``sys.argv[1:]``.

    Returns
    -------
    argparse.Namespace
        Parsed arguments.
    """
    parser = argparse.ArgumentParser(
        prog="ariadne task",
        description="Run a full Ariadne PR pipeline for a task description.",
    )

    parser.add_argument(
        "task_description",
        nargs="?",
        default=None,
        help="Task description string (required)",
    )

    parser.add_argument("--pr-id", default="", help="PR identifier (default: auto-generated)")
    parser.add_argument("--branch", default="", help="Branch name (default: auto-generated)")
    parser.add_argument("--base-branch", default="main", help="Base branch name (default: main)")
    parser.add_argument("--repo-root", default=".", help="Repository root path (default: .)")
    parser.add_argument("--allowed-file", action="append", default=[], help="Allowed files for staging (repeatable)")
    parser.add_argument("--stage-file", action="append", default=[], help="Files to stage (repeatable)")
    parser.add_argument("--commit-message", default="", help="Commit message")
    parser.add_argument("--pr-title", default=None, help="PR title")
    parser.add_argument("--pr-body", default=None, help="PR body text")
    parser.add_argument("--pr-body-path", default=None, help="Path to PR body file")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Dry-run mode (default: True)")
    parser.add_argument("--no-dry-run", action="store_false", dest="dry_run", help="Disable dry-run")
    parser.add_argument("--execute", action="store_true", default=False, help="Enable side-effecting execution")
    parser.add_argument("--approve", action="store_true", default=False, help="Explicit approval flag")
    parser.add_argument("--approved-by", default=None, help="Approval identity")
    parser.add_argument("--approval-reason", default=None, help="Approval justification")
    parser.add_argument("--json", action="store_true", default=False, help="Machine-readable JSON output")

    args = parser.parse_args(argv)
    return args


# ---------------------------------------------------------------------------
# Build CLI request from parsed args
# ---------------------------------------------------------------------------


def _build_cli_request(args: argparse.Namespace) -> AriadneTaskCliRequest:
    """Build an AriadneTaskCliRequest from parsed CLI arguments."""
    task_description = args.task_description or ""

    # Auto-generate PR ID and branch if not provided
    pr_id = args.pr_id
    if not pr_id:
        desc_hash = hashlib.sha256(task_description.encode("utf-8")).hexdigest()[:8]
        pr_id = f"cli-{desc_hash}"

    branch = args.branch
    if not branch:
        branch = pr_id

    return AriadneTaskCliRequest(
        task_description=task_description,
        pr_id=pr_id,
        branch=branch,
        base_branch=args.base_branch,
        repo_root=args.repo_root,
        allowed_files=tuple(args.allowed_file),
        files_to_stage=tuple(args.stage_file),
        commit_message=args.commit_message,
        pr_title=args.pr_title,
        pr_body=args.pr_body,
        pr_body_path=args.pr_body_path,
        dry_run=args.dry_run,
        execute=args.execute,
        approve=args.approve,
        approved_by=args.approved_by,
        approval_reason=args.approval_reason,
        json_output=args.json,
    )


# ---------------------------------------------------------------------------
# Local git command executor
# ---------------------------------------------------------------------------


def _execute_git_command_spec(spec: GitCommandSpec) -> dict[str, Any]:
    """Execute a single git command spec locally.

    Parameters
    ----------
    spec:
        The command spec to execute.

    Returns
    -------
    dict
        Result dict with ``exit_code``, ``stdout``, ``stderr``.
    """
    try:
        result = subprocess.run(
            spec.argv,
            capture_output=True,
            text=True,
            shell=False,
            cwd=spec.cwd,
        )
        return {
            "exit_code": result.returncode,
            "stdout": result.stdout[:2000] if result.stdout else "",
            "stderr": result.stderr[:2000] if result.stderr else "",
        }
    except FileNotFoundError:
        return {"exit_code": -1, "stdout": "", "stderr": f"Command not found: {spec.argv[0]}"}
    except Exception as e:
        return {"exit_code": -1, "stdout": "", "stderr": str(e)}


# ---------------------------------------------------------------------------
# Run ariadne task
# ---------------------------------------------------------------------------


def run_ariadne_task(
    request: AriadneTaskCliRequest,
    pipeline_runner_fn: Optional[Callable] = None,
    git_boundary_planner_fn: Optional[Callable] = None,
    git_boundary_executor_fn: Optional[Callable] = None,
    clock_provider: Optional[Callable] = None,
) -> AriadneTaskCliResult:
    """Run the ariadne task orchestration.

    Parameters
    ----------
    request:
        CLI request with task description and options.
    pipeline_runner_fn:
        Injectable pipeline runner function.  Default: ``run_pr_pipeline``.
    git_boundary_planner_fn:
        Injectable git boundary planner function.
        Default: ``prepare_git_boundary_plan``.
    git_boundary_executor_fn:
        Injectable git boundary executor function.
        Default: ``execute_git_boundary_plan``.
    clock_provider:
        Optional callable returning a timestamp string.

    Returns
    -------
    AriadneTaskCliResult
        Structured CLI result.
    """
    codes: list[str] = []
    warnings: list[str] = []
    started_at = clock_provider() if clock_provider else None

    # Resolve injectable boundaries
    pipeline_fn = pipeline_runner_fn or run_pr_pipeline
    planner_fn = git_boundary_planner_fn or prepare_git_boundary_plan
    executor_fn = git_boundary_executor_fn or execute_git_boundary_plan

    # 1. Validate task description
    if not request.task_description or request.task_description.strip() == "":
        codes.append(REASON_MISSING_TASK_DESCRIPTION)
        finished_at = clock_provider() if clock_provider else None
        return AriadneTaskCliResult(
            status=AriadneTaskCliStatus.FAILED,
            reason_codes=tuple(codes),
            task_description=request.task_description,
            task_description_hash="",
            pipeline_status=None,
            pipeline_final_action=None,
            pipeline_has_blockers=None,
            git_boundary_status=None,
            command_plan=None,
            execution_attempted=False,
            execution_results=(),
            warnings=tuple(warnings),
            next_action="stop",
            started_at=started_at,
            finished_at=finished_at,
            details="Missing task description",
        )

    task_description_hash = hashlib.sha256(request.task_description.encode("utf-8")).hexdigest()[:16]

    # 2. Build PipelineRunnerRequest
    pipeline_request = PipelineRunnerRequest(
        pr_id=request.pr_id,
        branch=request.branch,
        task_title=request.task_description[:80],
        task_description=request.task_description,
        repo_root=request.repo_root,
        agents_dir=os.path.join(request.repo_root, "agents"),
        project_memory_dir=os.path.join(request.repo_root, ".project-memory"),
        workdir=request.repo_root,
        allow_docker=False,
    )

    # 3. Run pipeline
    pipeline_result = pipeline_fn(pipeline_request)

    pipeline_status = getattr(pipeline_result, "status", None)
    pipeline_final_action = getattr(pipeline_result, "final_action", None)
    pipeline_has_blockers = getattr(pipeline_result, "has_blockers", None)
    pipeline_artifact_hashes = getattr(pipeline_result, "artifact_hashes", {})

    # 4. Check pipeline result
    if pipeline_status in (PipelineRunnerStatus.STOPPED,):
        codes.append(REASON_PIPELINE_STOPPED)
        finished_at = clock_provider() if clock_provider else None
        return AriadneTaskCliResult(
            status=AriadneTaskCliStatus.STOPPED,
            reason_codes=tuple(codes),
            task_description=request.task_description,
            task_description_hash=task_description_hash,
            pipeline_status=pipeline_status,
            pipeline_final_action=pipeline_final_action,
            pipeline_has_blockers=pipeline_has_blockers,
            git_boundary_status=None,
            command_plan=None,
            execution_attempted=False,
            execution_results=(),
            warnings=tuple(warnings),
            next_action="stop",
            started_at=started_at,
            finished_at=finished_at,
            details="Pipeline stopped",
        )

    if pipeline_status in (PipelineRunnerStatus.FAILED,):
        codes.append(REASON_PIPELINE_FAILED)
        finished_at = clock_provider() if clock_provider else None
        return AriadneTaskCliResult(
            status=AriadneTaskCliStatus.FAILED,
            reason_codes=tuple(codes),
            task_description=request.task_description,
            task_description_hash=task_description_hash,
            pipeline_status=pipeline_status,
            pipeline_final_action=pipeline_final_action,
            pipeline_has_blockers=pipeline_has_blockers,
            git_boundary_status=None,
            command_plan=None,
            execution_attempted=False,
            execution_results=(),
            warnings=tuple(warnings),
            next_action="stop",
            started_at=started_at,
            finished_at=finished_at,
            details="Pipeline failed",
        )

    if pipeline_has_blockers:
        codes.append(REASON_PIPELINE_STOPPED)
        finished_at = clock_provider() if clock_provider else None
        return AriadneTaskCliResult(
            status=AriadneTaskCliStatus.STOPPED,
            reason_codes=tuple(codes),
            task_description=request.task_description,
            task_description_hash=task_description_hash,
            pipeline_status=pipeline_status,
            pipeline_final_action=pipeline_final_action,
            pipeline_has_blockers=pipeline_has_blockers,
            git_boundary_status=None,
            command_plan=None,
            execution_attempted=False,
            execution_results=(),
            warnings=tuple(warnings),
            next_action="stop",
            started_at=started_at,
            finished_at=finished_at,
            details="Pipeline has blockers",
        )

    # 5. Build GitBoundaryRequest
    git_request = GitBoundaryRequest(
        repo_root=request.repo_root,
        base_branch=request.base_branch,
        head_branch=request.branch,
        current_branch=request.branch,
        pipeline_status=pipeline_status or "",
        pipeline_final_action=pipeline_final_action or "",
        pipeline_has_blockers=pipeline_has_blockers or False,
        pipeline_artifact_hashes=pipeline_artifact_hashes,
        dirty_files=request.files_to_stage,
        allowed_files=request.allowed_files,
        files_to_stage=request.files_to_stage,
        commit_message=request.commit_message,
        pr_title=request.pr_title,
        pr_body=request.pr_body,
        pr_body_path=request.pr_body_path,
        human_approved=request.approve,
        approved_by=request.approved_by,
        approval_reason=request.approval_reason,
    )

    # 6. Plan git boundary
    git_plan, git_codes = planner_fn(git_request)

    # 7. Check git boundary plan
    if not git_plan.pipeline_eligible or not git_plan.dirty_tree_valid or git_codes:
        codes.extend(git_codes)
        codes.append(REASON_GIT_BOUNDARY_BLOCKED)
        finished_at = clock_provider() if clock_provider else None
        return AriadneTaskCliResult(
            status=AriadneTaskCliStatus.BLOCKED,
            reason_codes=tuple(codes),
            task_description=request.task_description,
            task_description_hash=task_description_hash,
            pipeline_status=pipeline_status,
            pipeline_final_action=pipeline_final_action,
            pipeline_has_blockers=pipeline_has_blockers,
            git_boundary_status=GitBoundaryStatus.BLOCKED.value,
            command_plan=[_spec_to_dict(s) for s in git_plan.command_specs],
            execution_attempted=False,
            execution_results=(),
            warnings=tuple(warnings),
            next_action="stop",
            started_at=started_at,
            finished_at=clock_provider() if clock_provider else None,
            details="Git boundary blocked",
        )

    # 8. Check execution requirements
    if not request.execute:
        codes.append(REASON_EXECUTION_REQUIRED)
        finished_at = clock_provider() if clock_provider else None
        return AriadneTaskCliResult(
            status=AriadneTaskCliStatus.BLOCKED,
            reason_codes=tuple(codes),
            task_description=request.task_description,
            task_description_hash=task_description_hash,
            pipeline_status=pipeline_status,
            pipeline_final_action=pipeline_final_action,
            pipeline_has_blockers=pipeline_has_blockers,
            git_boundary_status=GitBoundaryStatus.APPROVED.value,
            command_plan=[_spec_to_dict(s) for s in git_plan.command_specs],
            execution_attempted=False,
            execution_results=(),
            warnings=tuple(warnings),
            next_action="execute_required",
            started_at=started_at,
            finished_at=clock_provider() if clock_provider else None,
            details="Execution required (use --execute)",
        )

    if not request.approve:
        codes.append(REASON_APPROVAL_REQUIRED)
        finished_at = clock_provider() if clock_provider else None
        return AriadneTaskCliResult(
            status=AriadneTaskCliStatus.BLOCKED,
            reason_codes=tuple(codes),
            task_description=request.task_description,
            task_description_hash=task_description_hash,
            pipeline_status=pipeline_status,
            pipeline_final_action=pipeline_final_action,
            pipeline_has_blockers=pipeline_has_blockers,
            git_boundary_status=GitBoundaryStatus.APPROVED.value,
            command_plan=[_spec_to_dict(s) for s in git_plan.command_specs],
            execution_attempted=False,
            execution_results=(),
            warnings=tuple(warnings),
            next_action="approval_required",
            started_at=started_at,
            finished_at=clock_provider() if clock_provider else None,
            details="Approval required (use --approve)",
        )

    if not request.approved_by or request.approved_by.strip() == "":
        codes.append(REASON_MISSING_APPROVED_BY)
        finished_at = clock_provider() if clock_provider else None
        return AriadneTaskCliResult(
            status=AriadneTaskCliStatus.BLOCKED,
            reason_codes=tuple(codes),
            task_description=request.task_description,
            task_description_hash=task_description_hash,
            pipeline_status=pipeline_status,
            pipeline_final_action=pipeline_final_action,
            pipeline_has_blockers=pipeline_has_blockers,
            git_boundary_status=GitBoundaryStatus.APPROVED.value,
            command_plan=[_spec_to_dict(s) for s in git_plan.command_specs],
            execution_attempted=False,
            execution_results=(),
            warnings=tuple(warnings),
            next_action="approval_required",
            started_at=started_at,
            finished_at=clock_provider() if clock_provider else None,
            details="Missing --approved-by",
        )

    if not request.approval_reason or request.approval_reason.strip() == "":
        codes.append(REASON_MISSING_APPROVAL_REASON)
        finished_at = clock_provider() if clock_provider else None
        return AriadneTaskCliResult(
            status=AriadneTaskCliStatus.BLOCKED,
            reason_codes=tuple(codes),
            task_description=request.task_description,
            task_description_hash=task_description_hash,
            pipeline_status=pipeline_status,
            pipeline_final_action=pipeline_final_action,
            pipeline_has_blockers=pipeline_has_blockers,
            git_boundary_status=GitBoundaryStatus.APPROVED.value,
            command_plan=[_spec_to_dict(s) for s in git_plan.command_specs],
            execution_attempted=False,
            execution_results=(),
            warnings=tuple(warnings),
            next_action="approval_required",
            started_at=started_at,
            finished_at=clock_provider() if clock_provider else None,
            details="Missing --approval-reason",
        )

    # 9. Execute git boundary
    execution_attempted = False
    execution_results: tuple[dict[str, str], ...] = ()

    if not request.dry_run:
        execution_attempted = True
        git_result = executor_fn(git_request, git_plan, executor=_execute_git_command_spec)

        if git_result.status == GitBoundaryStatus.FAILED.value:
            codes.append(REASON_EXECUTION_FAILED)
            execution_results = git_result.execution_results
            finished_at = clock_provider() if clock_provider else None
            return AriadneTaskCliResult(
                status=AriadneTaskCliStatus.FAILED,
                reason_codes=tuple(codes),
                task_description=request.task_description,
                task_description_hash=task_description_hash,
                pipeline_status=pipeline_status,
                pipeline_final_action=pipeline_final_action,
                pipeline_has_blockers=pipeline_has_blockers,
                git_boundary_status=git_result.status,
                command_plan=[_spec_to_dict(s) for s in git_plan.command_specs],
                execution_attempted=execution_attempted,
                execution_results=execution_results,
                warnings=tuple(warnings),
                next_action="stop",
                started_at=started_at,
                finished_at=clock_provider() if clock_provider else None,
                details="Execution failed",
            )

        execution_results = git_result.execution_results

    # 10. Determine final status
    if pipeline_status == PipelineRunnerStatus.COMPLETED_WITH_WARNING:
        final_status = AriadneTaskCliStatus.COMPLETED_WITH_WARNING
    else:
        final_status = AriadneTaskCliStatus.COMPLETED

    finished_at = clock_provider() if clock_provider else None

    return AriadneTaskCliResult(
        status=final_status,
        reason_codes=tuple(codes),
        task_description=request.task_description,
        task_description_hash=task_description_hash,
        pipeline_status=pipeline_status,
        pipeline_final_action=pipeline_final_action,
        pipeline_has_blockers=pipeline_has_blockers,
        git_boundary_status=GitBoundaryStatus.APPROVED.value,
        command_plan=[_spec_to_dict(s) for s in git_plan.command_specs],
        execution_attempted=execution_attempted,
        execution_results=execution_results,
        warnings=tuple(warnings),
        next_action="continue",
        started_at=started_at,
        finished_at=finished_at,
        details=None,
    )


# ---------------------------------------------------------------------------
# Helper: convert GitCommandSpec to dict
# ---------------------------------------------------------------------------


def _spec_to_dict(spec: GitCommandSpec) -> dict[str, Any]:
    """Convert a GitCommandSpec to a JSON-safe dict."""
    return {
        "operation": spec.operation,
        "argv": list(spec.argv),
        "requires_human_approval": spec.requires_human_approval,
        "side_effecting": spec.side_effecting,
        "redacted_display": spec.redacted_display,
        "details": spec.details,
    }


# ---------------------------------------------------------------------------
# Format human-readable output
# ---------------------------------------------------------------------------


def _format_human_output(result: AriadneTaskCliResult) -> str:
    """Format a CLI result as human-readable text."""
    lines: list[str] = []
    lines.append(f"Ariadne task: {result.task_description}")
    lines.append("")

    if result.pipeline_status is not None:
        lines.append(f"Pipeline status: {result.pipeline_status} (final_action={result.pipeline_final_action})")
        lines.append(f"Pipeline has_blockers: {result.pipeline_has_blockers}")
    lines.append("")

    if result.git_boundary_status is not None:
        lines.append(f"Git Boundary status: {result.git_boundary_status}")
    lines.append("")

    if result.command_plan:
        lines.append("Command plan:")
        for i, spec in enumerate(result.command_plan, 1):
            lines.append(f"  [{i}] {spec.get('redacted_display', spec.get('operation', 'unknown'))}")
        lines.append("")

    lines.append(f"Execution attempted: {result.execution_attempted}")
    if result.execution_results:
        lines.append("Execution results:")
        for res in result.execution_results:
            lines.append(f"  {res.get('operation', '?')}: exit_code={res.get('exit_code', '?')}")
    lines.append("")

    if result.warnings:
        lines.append("Warnings:")
        for w in result.warnings:
            lines.append(f"  - {w}")
        lines.append("")

    lines.append(f"Next action: {result.next_action}")

    if result.details:
        lines.append(f"Details: {result.details}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main(argv: Optional[list[str]] = None) -> int:
    """Main entry point for the ariadne task CLI.

    Parameters
    ----------
    argv:
        Command-line argument list.  If ``None``, uses ``sys.argv[1:]``.

    Returns
    -------
    int
        Exit code (0 for success, 1 for failure/blocked).
    """
    args = parse_ariadne_task_args(argv)
    request = _build_cli_request(args)
    result = run_ariadne_task(request)

    if result.json_output:
        output_dict = {
            "status": result.status,
            "reason_codes": list(result.reason_codes),
            "task_description": result.task_description,
            "task_description_hash": result.task_description_hash,
            "pipeline_status": result.pipeline_status,
            "pipeline_final_action": result.pipeline_final_action,
            "pipeline_has_blockers": result.pipeline_has_blockers,
            "git_boundary_status": result.git_boundary_status,
            "command_plan": result.command_plan,
            "execution_attempted": result.execution_attempted,
            "execution_results": list(result.execution_results),
            "warnings": list(result.warnings),
            "next_action": result.next_action,
            "started_at": result.started_at,
            "finished_at": result.finished_at,
            "details": result.details,
        }
        print(json.dumps(output_dict, sort_keys=True, ensure_ascii=False))
    else:
        print(_format_human_output(result))

    if result.status in (AriadneTaskCliStatus.COMPLETED, AriadneTaskCliStatus.COMPLETED_WITH_WARNING):
        return 0
    return 1
