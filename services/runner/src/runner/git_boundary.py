"""
Git Boundary for Ariadne — first Stage 2 Closed Loop PR.

Validates pipeline result eligibility, dirty-tree allowlist, and human
approval fields, then produces argv-based command specs for git status,
git add, git commit, git push, and gh pr create.  Execution is possible
only through an injected fakeable executor and only when explicit human
approval is present.

Core principle:
    Agent output is not evidence.  Runtime/file-captured artifacts are
    evidence.  Git mutation is an external side effect and must be
    approval-gated.  Agents must not receive unattended git mutation
    rights.
"""

from __future__ import annotations

import dataclasses
import enum
import os
from typing import Any, Callable, Optional


# ---------------------------------------------------------------------------
# GitBoundaryStatus — status values
# ---------------------------------------------------------------------------


class GitBoundaryStatus(str, enum.Enum):
    """Status values for git boundary operations."""

    APPROVED = "approved"
    BLOCKED = "blocked"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# GitBoundaryRequest — input dataclass
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class GitBoundaryRequest:
    """Input parameters for the git boundary."""

    repo_root: str
    base_branch: str
    head_branch: str
    current_branch: str
    pipeline_status: str
    pipeline_final_action: str
    pipeline_has_blockers: bool
    pipeline_artifact_hashes: dict[str, str]
    dirty_files: tuple[str, ...]
    allowed_files: tuple[str, ...]
    files_to_stage: tuple[str, ...]
    commit_message: str
    pr_title: Optional[str] = None
    pr_body: Optional[str] = None
    pr_body_path: Optional[str] = None
    human_approved: bool = False
    approved_by: Optional[str] = None
    approval_reason: Optional[str] = None


# ---------------------------------------------------------------------------
# GitCommandSpec — single command specification
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class GitCommandSpec:
    """A single git/gh command specification."""

    operation: str
    argv: tuple[str, ...]
    cwd: str
    allowed_files: tuple[str, ...]
    requires_human_approval: bool
    side_effecting: bool
    redacted_display: str
    details: Optional[str] = None


# ---------------------------------------------------------------------------
# GitBoundaryPlan — command plan
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class GitBoundaryPlan:
    """A plan of git/gh commands."""

    command_specs: tuple[GitCommandSpec, ...]
    command_count: int
    files_to_stage: tuple[str, ...]
    rejected_files: tuple[str, ...]
    pipeline_eligible: bool
    dirty_tree_valid: bool
    approval_summary: str


# ---------------------------------------------------------------------------
# GitBoundaryResult — operation result
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class GitBoundaryResult:
    """Result of a git boundary operation."""

    status: str
    reason_codes: tuple[str, ...]
    approved: bool
    blocked: bool
    command_plan: Optional[GitBoundaryPlan]
    command_count: int
    files_to_stage: tuple[str, ...]
    rejected_files: tuple[str, ...]
    pipeline_eligible: bool
    dirty_tree_valid: bool
    approval_summary: str
    execution_attempted: bool
    execution_results: tuple[dict[str, str], ...]
    artifact_hashes: dict[str, str]
    started_at: Optional[str]
    finished_at: Optional[str]
    details: Optional[str]


# ---------------------------------------------------------------------------
# Stable reason codes
# ---------------------------------------------------------------------------

REASON_PIPELINE_NOT_ELIGIBLE = "pipeline_not_eligible"
REASON_DIRTY_TREE_INVALID = "dirty_tree_invalid"
REASON_FORBIDDEN_PATH = "forbidden_path"
REASON_REJECTED_FILE = "rejected_file"
REASON_MISSING_COMMIT_MESSAGE = "missing_commit_message"
REASON_MISSING_PR_TITLE = "missing_pr_title"
REASON_HUMAN_APPROVAL_REQUIRED = "human_approval_required"
REASON_MISSING_APPROVED_BY = "missing_approved_by"
REASON_MISSING_APPROVAL_REASON = "missing_approval_reason"
REASON_EXECUTION_FAILED = "execution_failed"

# ---------------------------------------------------------------------------
# Forbidden paths
# ---------------------------------------------------------------------------

_FORBIDDEN_PATHS: tuple[str, ...] = (
    "agents/",
    "schemas/",
    "services/task_intake/",
    ".project-memory/post-0100/",
)

_ADDITIONAL_BLOCKED_PATHS: tuple[str, ...] = (
    "ROADMAP.md",
    "docs/",
    "pyproject.toml",
    "package.json",
    "Makefile",
)


# ---------------------------------------------------------------------------
# Check if a path is forbidden
# ---------------------------------------------------------------------------


def _is_forbidden_path(path: str) -> bool:
    """Check if a path is forbidden for git mutation."""
    for forbidden in _FORBIDDEN_PATHS:
        if path.startswith(forbidden) or path == forbidden.rstrip("/"):
            return True
    for blocked in _ADDITIONAL_BLOCKED_PATHS:
        if path == blocked or path.startswith(blocked):
            return True
    return False


# ---------------------------------------------------------------------------
# Prepare git boundary plan
# ---------------------------------------------------------------------------


def prepare_git_boundary_plan(
    request: GitBoundaryRequest,
) -> tuple[GitBoundaryPlan, list[str]]:
    """Prepare a git boundary plan.

    Parameters
    ----------
    request:
        Input parameters including pipeline result, dirty files, allowed
        files, approval fields, and commit/PR details.

    Returns
    -------
    tuple[GitBoundaryPlan, list[str]]
        ``(plan, reason_codes)``.
    """
    codes: list[str] = []
    rejected_files: list[str] = []

    # 1. Pipeline eligibility
    pipeline_eligible = True
    if request.pipeline_status not in ("completed", "completed_with_warning"):
        codes.append(REASON_PIPELINE_NOT_ELIGIBLE)
        pipeline_eligible = False
    elif request.pipeline_final_action not in ("continue", "continue_with_warning"):
        codes.append(REASON_PIPELINE_NOT_ELIGIBLE)
        pipeline_eligible = False
    elif request.pipeline_has_blockers:
        codes.append(REASON_PIPELINE_NOT_ELIGIBLE)
        pipeline_eligible = False
    elif not request.pipeline_artifact_hashes:
        codes.append(REASON_PIPELINE_NOT_ELIGIBLE)
        pipeline_eligible = False

    # 2. Dirty tree validity
    dirty_tree_valid = True
    for dirty_file in request.dirty_files:
        if _is_forbidden_path(dirty_file):
            codes.append(REASON_FORBIDDEN_PATH)
            rejected_files.append(dirty_file)
            dirty_tree_valid = False
        elif dirty_file not in request.allowed_files:
            codes.append(REASON_DIRTY_TREE_INVALID)
            rejected_files.append(dirty_file)
            dirty_tree_valid = False

    # 3. File staging validity
    for stage_file in request.files_to_stage:
        if stage_file not in request.dirty_files:
            codes.append(REASON_REJECTED_FILE)
            rejected_files.append(stage_file)
        elif stage_file not in request.allowed_files:
            codes.append(REASON_REJECTED_FILE)
            rejected_files.append(stage_file)

    # 4. Commit message
    if not request.commit_message or request.commit_message.strip() == "":
        codes.append(REASON_MISSING_COMMIT_MESSAGE)

    # 5. PR title (if PR is requested)
    pr_requested = request.pr_title is not None and request.pr_title.strip() != ""
    if request.pr_title is not None and request.pr_title.strip() == "":
        codes.append(REASON_MISSING_PR_TITLE)

    # 6. Build command specs
    command_specs: list[GitCommandSpec] = []

    # git status
    command_specs.append(GitCommandSpec(
        operation="git_status",
        argv=("git", "status"),
        cwd=request.repo_root,
        allowed_files=request.allowed_files,
        requires_human_approval=False,
        side_effecting=False,
        redacted_display="git status",
        details="Check repository status",
    ))

    # git add
    if request.files_to_stage:
        command_specs.append(GitCommandSpec(
            operation="git_add",
            argv=("git", "add", "--") + request.files_to_stage,
            cwd=request.repo_root,
            allowed_files=request.files_to_stage,
            requires_human_approval=False,
            side_effecting=False,
            redacted_display=f"git add -- {len(request.files_to_stage)} file(s)",
            details=f"Stage {len(request.files_to_stage)} file(s)",
        ))

    # git commit
    command_specs.append(GitCommandSpec(
        operation="git_commit",
        argv=("git", "commit", "-m", request.commit_message),
        cwd=request.repo_root,
        allowed_files=request.allowed_files,
        requires_human_approval=True,
        side_effecting=True,
        redacted_display="git commit -m <redacted>",
        details="Commit staged changes",
    ))

    # git push
    command_specs.append(GitCommandSpec(
        operation="git_push",
        argv=("git", "push", "origin", request.head_branch),
        cwd=request.repo_root,
        allowed_files=request.allowed_files,
        requires_human_approval=True,
        side_effecting=True,
        redacted_display=f"git push origin {request.head_branch}",
        details=f"Push branch {request.head_branch} to origin",
    ))

    # gh pr create (only if pr_title is present)
    if pr_requested:
        pr_argv = ["gh", "pr", "create", "--title", request.pr_title]
        if request.pr_body:
            pr_argv.extend(["--body", request.pr_body])
        elif request.pr_body_path:
            pr_argv.extend(["--body-file", request.pr_body_path])
        pr_argv.extend(["--base", request.base_branch, "--head", request.head_branch])

        command_specs.append(GitCommandSpec(
            operation="gh_pr_create",
            argv=tuple(pr_argv),
            cwd=request.repo_root,
            allowed_files=request.allowed_files,
            requires_human_approval=True,
            side_effecting=True,
            redacted_display=f"gh pr create --title <redacted> --base {request.base_branch} --head {request.head_branch}",
            details=f"Create PR from {request.head_branch} to {request.base_branch}",
        ))

    # 7. Build approval summary
    if request.human_approved and request.approved_by and request.approval_reason:
        approval_summary = f"Approved by {request.approved_by}: {request.approval_reason}"
    elif request.human_approved:
        approval_summary = "Approved (incomplete approval metadata)"
    else:
        approval_summary = "Not approved"

    plan = GitBoundaryPlan(
        command_specs=tuple(command_specs),
        command_count=len(command_specs),
        files_to_stage=request.files_to_stage,
        rejected_files=tuple(rejected_files),
        pipeline_eligible=pipeline_eligible,
        dirty_tree_valid=dirty_tree_valid,
        approval_summary=approval_summary,
    )

    return plan, codes


# ---------------------------------------------------------------------------
# Execute git boundary plan
# ---------------------------------------------------------------------------


def execute_git_boundary_plan(
    request: GitBoundaryRequest,
    plan: GitBoundaryPlan,
    executor: Optional[Callable] = None,
    clock_provider: Optional[Callable] = None,
) -> GitBoundaryResult:
    """Execute a git boundary plan.

    Parameters
    ----------
    request:
        Input parameters including approval fields.
    plan:
        The command plan to execute.
    executor:
        Optional injected executor callable.  Receives ``GitCommandSpec``
        and returns ``dict`` with ``exit_code``, ``stdout``, ``stderr``.
    clock_provider:
        Optional callable returning a timestamp string.

    Returns
    -------
    GitBoundaryResult
        ``status="approved"`` when execution succeeds.
        ``status="blocked"`` when validation fails.
        ``status="failed"`` when execution fails.
    """
    codes: list[str] = []
    started_at = clock_provider() if clock_provider else None
    execution_results: list[dict[str, str]] = []
    execution_attempted = False

    # 1. Check human approval
    if not request.human_approved:
        codes.append(REASON_HUMAN_APPROVAL_REQUIRED)
        finished_at = clock_provider() if clock_provider else None
        return GitBoundaryResult(
            status=GitBoundaryStatus.BLOCKED.value,
            reason_codes=tuple(codes),
            approved=False,
            blocked=True,
            command_plan=plan,
            command_count=plan.command_count,
            files_to_stage=plan.files_to_stage,
            rejected_files=plan.rejected_files,
            pipeline_eligible=plan.pipeline_eligible,
            dirty_tree_valid=plan.dirty_tree_valid,
            approval_summary=plan.approval_summary,
            execution_attempted=False,
            execution_results=(),
            artifact_hashes=request.pipeline_artifact_hashes,
            started_at=started_at,
            finished_at=finished_at,
            details="Human approval required",
        )

    if not request.approved_by or request.approved_by.strip() == "":
        codes.append(REASON_MISSING_APPROVED_BY)
        finished_at = clock_provider() if clock_provider else None
        return GitBoundaryResult(
            status=GitBoundaryStatus.BLOCKED.value,
            reason_codes=tuple(codes),
            approved=False,
            blocked=True,
            command_plan=plan,
            command_count=plan.command_count,
            files_to_stage=plan.files_to_stage,
            rejected_files=plan.rejected_files,
            pipeline_eligible=plan.pipeline_eligible,
            dirty_tree_valid=plan.dirty_tree_valid,
            approval_summary=plan.approval_summary,
            execution_attempted=False,
            execution_results=(),
            artifact_hashes=request.pipeline_artifact_hashes,
            started_at=started_at,
            finished_at=clock_provider() if clock_provider else None,
            details="Missing approved_by",
        )

    if not request.approval_reason or request.approval_reason.strip() == "":
        codes.append(REASON_MISSING_APPROVAL_REASON)
        finished_at = clock_provider() if clock_provider else None
        return GitBoundaryResult(
            status=GitBoundaryStatus.BLOCKED.value,
            reason_codes=tuple(codes),
            approved=False,
            blocked=True,
            command_plan=plan,
            command_count=plan.command_count,
            files_to_stage=plan.files_to_stage,
            rejected_files=plan.rejected_files,
            pipeline_eligible=plan.pipeline_eligible,
            dirty_tree_valid=plan.dirty_tree_valid,
            approval_summary=plan.approval_summary,
            execution_attempted=False,
            execution_results=(),
            artifact_hashes=request.pipeline_artifact_hashes,
            started_at=started_at,
            finished_at=clock_provider() if clock_provider else None,
            details="Missing approval_reason",
        )

    # 2. Check plan eligibility
    if not plan.pipeline_eligible or not plan.dirty_tree_valid or codes:
        finished_at = clock_provider() if clock_provider else None
        return GitBoundaryResult(
            status=GitBoundaryStatus.BLOCKED.value,
            reason_codes=tuple(codes) if codes else (REASON_PIPELINE_NOT_ELIGIBLE,),
            approved=False,
            blocked=True,
            command_plan=plan,
            command_count=plan.command_count,
            files_to_stage=plan.files_to_stage,
            rejected_files=plan.rejected_files,
            pipeline_eligible=plan.pipeline_eligible,
            dirty_tree_valid=plan.dirty_tree_valid,
            approval_summary=plan.approval_summary,
            execution_attempted=False,
            execution_results=(),
            artifact_hashes=request.pipeline_artifact_hashes,
            started_at=started_at,
            finished_at=clock_provider() if clock_provider else None,
            details="Plan not eligible for execution",
        )

    # 3. Execute through executor
    if executor is None:
        finished_at = clock_provider() if clock_provider else None
        return GitBoundaryResult(
            status=GitBoundaryStatus.APPROVED.value,
            reason_codes=(),
            approved=True,
            blocked=False,
            command_plan=plan,
            command_count=plan.command_count,
            files_to_stage=plan.files_to_stage,
            rejected_files=plan.rejected_files,
            pipeline_eligible=plan.pipeline_eligible,
            dirty_tree_valid=plan.dirty_tree_valid,
            approval_summary=plan.approval_summary,
            execution_attempted=False,
            execution_results=(),
            artifact_hashes=request.pipeline_artifact_hashes,
            started_at=started_at,
            finished_at=clock_provider() if clock_provider else None,
            details="No executor provided; plan approved but not executed",
        )

    execution_attempted = True
    for spec in plan.command_specs:
        try:
            result = executor(spec)
            if isinstance(result, dict):
                execution_results.append({
                    "operation": spec.operation,
                    "exit_code": str(result.get("exit_code", "")),
                    "stdout": result.get("stdout", ""),
                    "stderr": result.get("stderr", ""),
                })
                if result.get("exit_code", 0) != 0:
                    codes.append(REASON_EXECUTION_FAILED)
            else:
                execution_results.append({
                    "operation": spec.operation,
                    "exit_code": "-1",
                    "stdout": "",
                    "stderr": "Executor returned non-dict result",
                })
                codes.append(REASON_EXECUTION_FAILED)
        except Exception as e:
            execution_results.append({
                "operation": spec.operation,
                "exit_code": "-1",
                "stdout": "",
                "stderr": str(e),
            })
            codes.append(REASON_EXECUTION_FAILED)

    finished_at = clock_provider() if clock_provider else None

    if codes:
        return GitBoundaryResult(
            status=GitBoundaryStatus.FAILED.value,
            reason_codes=tuple(codes),
            approved=False,
            blocked=False,
            command_plan=plan,
            command_count=plan.command_count,
            files_to_stage=plan.files_to_stage,
            rejected_files=plan.rejected_files,
            pipeline_eligible=plan.pipeline_eligible,
            dirty_tree_valid=plan.dirty_tree_valid,
            approval_summary=plan.approval_summary,
            execution_attempted=execution_attempted,
            execution_results=tuple(execution_results),
            artifact_hashes=request.pipeline_artifact_hashes,
            started_at=started_at,
            finished_at=finished_at,
            details="Execution failed",
        )

    return GitBoundaryResult(
        status=GitBoundaryStatus.APPROVED.value,
        reason_codes=(),
        approved=True,
        blocked=False,
        command_plan=plan,
        command_count=plan.command_count,
        files_to_stage=plan.files_to_stage,
        rejected_files=plan.rejected_files,
        pipeline_eligible=plan.pipeline_eligible,
        dirty_tree_valid=plan.dirty_tree_valid,
        approval_summary=plan.approval_summary,
        execution_attempted=execution_attempted,
        execution_results=tuple(execution_results),
        artifact_hashes=request.pipeline_artifact_hashes,
        started_at=started_at,
        finished_at=finished_at,
        details="Execution completed successfully",
    )
