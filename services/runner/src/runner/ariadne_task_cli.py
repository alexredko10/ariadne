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
from datetime import datetime, timezone
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
from runner.run_persistence import (
    RunPersistenceRequest,
    RunPersistenceStatus,
    persist_run_record,
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
    runs_root: Optional[str] = None
    run_id: Optional[str] = None


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
    run_id: Optional[str] = None
    run_record_path: Optional[str] = None


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
REASON_DIRTY_TREE_OUT_OF_SCOPE = "dirty_tree_out_of_scope"
REASON_DOGFOOD_PROOF_INCOMPLETE = "dogfood_proof_incomplete"


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
        nargs="*",
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
    parser.add_argument("--runs-root", default=None, help="Run persistence root directory (default: no persistence)")
    parser.add_argument("--run-id", default=None, help="Run identifier (default: auto-generated)")

    args = parser.parse_args(argv)
    return args


# ---------------------------------------------------------------------------
# Build CLI request from parsed args
# ---------------------------------------------------------------------------


def _build_cli_request(args: argparse.Namespace) -> AriadneTaskCliRequest:
    """Build an AriadneTaskCliRequest from parsed CLI arguments."""
    # Handle task_description as a list (nargs="*")
    raw_parts = args.task_description or []
    if isinstance(raw_parts, list) and len(raw_parts) > 0:
        # If first part is literal "task", skip it
        if raw_parts[0] == "task":
            raw_parts = raw_parts[1:]
        task_description = " ".join(raw_parts)
    else:
        task_description = ""

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
        runs_root=args.runs_root,
        run_id=args.run_id,
    )


# ---------------------------------------------------------------------------
# Detect payload artifact path from files_to_stage
# ---------------------------------------------------------------------------


def _detect_payload_artifact_path(files_to_stage: tuple[str, ...]) -> str:
    """Detect the user-intended payload artifact from files_to_stage.

    The payload is the first file in files_to_stage that:
    - Is under ``.project-memory/pr/<pr_id>/``
    - Is not ``PLAN.md``
    - Is not under ``reviews/``

    Returns empty string if no such file.
    """
    for f in files_to_stage:
        if not f.startswith(".project-memory/pr/"):
            continue
        basename = os.path.basename(f)
        if basename == "PLAN.md":
            continue
        if "/reviews/" in f:
            continue
        return f
    return ""


# ---------------------------------------------------------------------------
# Compute plan summary from request parameters
# ---------------------------------------------------------------------------


def _compute_plan_summary(request: AriadneTaskCliRequest) -> list[str]:
    """Compute a deterministic command plan summary from request parameters.

    Returns a list of operation names that the Git Boundary would execute.
    This is used before Git Boundary planning to populate the proof's
    ``command_plan_summary`` field.

    Parameters
    ----------
    request:
        The CLI request.

    Returns
    -------
    list[str]
        Ordered list of operation names.
    """
    operations: list[str] = []
    operations.append("git_status")
    if request.files_to_stage:
        operations.append("git_add")
    operations.append("git_commit")
    operations.append("git_push")
    if request.pr_title:
        operations.append("gh_pr_create")
    return operations


# ---------------------------------------------------------------------------
# Validate dogfood proof content
# ---------------------------------------------------------------------------


_REQUIRED_PROOF_FIELDS: tuple[str, ...] = (
    "schema_version",
    "pr_id",
    "run_id",
    "branch",
    "invocation_mode",
    "pipeline_status",
    "pipeline_final_action",
    "pipeline_has_blockers",
    "git_boundary_status",
    "command_plan_summary",
    "execution_attempted",
    "pr_created",
    "pr_url",
    "run_record_path",
    "run_json_hash",
    "artifact_hashes",
    "approval_summary",
    "timestamp",
    "note",
    "proof_artifact_ref",
)

_CRITICAL_NON_EMPTY_FIELDS: tuple[str, ...] = (
    "pr_id",
    "run_id",
    "branch",
    "proof_artifact_ref",
)


_ALLOWED_SENTINEL_VALUES: dict[str, tuple[str, ...]] = {
    "pr_url": ("pending-before-gh-pr-create",),
    "run_json_hash": ("pending",),
}


_WEAK_BRIDGE_PATTERNS: tuple[str, ...] = (
    "dogfood_type: \"local-non-docker\"",
    "bridge_task_prompt_hash:",
    "bridge_agent_config_hash:",
    "materialized_at:",
)


def _validate_dogfood_proof_content(path: str) -> tuple[bool, list[str], list[str]]:
    """Validate a written dogfood proof file on disk.

    Checks:
    1. All 20 required fields are present
    2. Critical fields are non-empty
    3. No weak bridge placeholder patterns

    Parameters
    ----------
    path:
        Path to the proof file on disk.

    Returns
    -------
    tuple[bool, list[str], list[str]]
        ``(ok, reason_codes, warnings)``.
    """
    codes: list[str] = []
    warnings: list[str] = []

    if not os.path.exists(path):
        codes.append("dogfood_proof_incomplete")
        warnings.append("Proof file does not exist: " + path)
        return False, codes, warnings

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError as e:
        codes.append("dogfood_proof_incomplete")
        warnings.append("Cannot read proof file: " + str(e))
        return False, codes, warnings

    # Check for weak bridge placeholder patterns
    for pattern in _WEAK_BRIDGE_PATTERNS:
        if pattern in content:
            codes.append("dogfood_proof_incomplete")
            warnings.append("Weak bridge placeholder pattern found: " + pattern)
            return False, codes, warnings

    # Check all required fields are present
    for field in _REQUIRED_PROOF_FIELDS:
        if field + ":" not in content:
            codes.append("dogfood_proof_incomplete")
            warnings.append("Missing required proof field: " + field)

    # Check critical non-empty fields
    for field in _CRITICAL_NON_EMPTY_FIELDS:
        pattern = field + ': ""'
        if pattern in content:
            codes.append("dogfood_proof_incomplete")
            warnings.append("Empty critical field: " + field)

    # Check command_plan_summary is not empty
    if "command_plan_summary: []" in content:
        codes.append("dogfood_proof_incomplete")
        warnings.append("command_plan_summary is empty")

    ok = len(codes) == 0
    return ok, codes, warnings


# ---------------------------------------------------------------------------
# Dogfood proof renderer
# ---------------------------------------------------------------------------


def _render_dogfood_proof_yaml(
    pipeline_status: Optional[str],
    pipeline_final_action: Optional[str],
    pipeline_has_blockers: Optional[bool],
    pipeline_artifact_hashes: dict[str, str],
    command_plan_summary: list[str],
    request: AriadneTaskCliRequest,
    run_id: str,
    run_record_path: Optional[str],
    clock_provider: Optional[Callable] = None,
) -> str:
    """Render a dogfood proof YAML artifact from runtime context."""
    timestamp = clock_provider() if clock_provider else datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Sanitize approval summary
    approved_by = request.approved_by or ""
    approval_reason = request.approval_reason or ""
    if approved_by:
        approval_summary = f"Approved by {approved_by[:40]}"
        if approval_reason:
            approval_summary += f": {approval_reason[:80]}"
    else:
        approval_summary = "Not approved"

    # Build run_record_path
    if run_record_path:
        record_path = run_record_path
    elif request.runs_root and run_id:
        record_path = os.path.join(request.runs_root, run_id, "run.json")
    else:
        record_path = ""

    # Build proof_artifact_ref from stage-file path
    if request.files_to_stage:
        proof_artifact_ref = request.files_to_stage[0]
    else:
        proof_artifact_ref = "pending-before-proof-hash"

    # Build run_json_hash (pending if not yet persisted)
    run_json_hash = "pending"

    # Build artifact_hashes summary
    artifact_hashes_summary = {}
    for path, h in pipeline_artifact_hashes.items():
        artifact_hashes_summary[path] = h[:16]

    lines = [
        'schema_version: "0.1"',
        'pr_id: "' + request.pr_id + '"',
        'run_id: "' + run_id + '"',
        'branch: "' + request.branch + '"',
        'invocation_mode: "cli"',
        'pipeline_status: "' + (pipeline_status or "") + '"',
        'pipeline_final_action: "' + (pipeline_final_action or "") + '"',
        "pipeline_has_blockers: " + str(pipeline_has_blockers or False),
        'git_boundary_status: "pending"',
        "execution_attempted: false",
        "pr_created: false",
        'pr_url: "pending-before-gh-pr-create"',
        'run_record_path: "' + record_path + '"',
        'run_json_hash: "' + run_json_hash + '"',
        'proof_artifact_ref: "' + proof_artifact_ref + '"',
        'timestamp: "' + timestamp + '"',
        'note: "dogfood proof artifact, not a product feature"',
    ]

    # Add command_plan_summary
    if command_plan_summary:
        lines.append("command_plan_summary:")
        for op in command_plan_summary:
            lines.append('  - "' + op + '"')
    else:
        lines.append("command_plan_summary: []")

    # Add artifact_hashes
    if artifact_hashes_summary:
        lines.append("artifact_hashes:")
        for path, h in artifact_hashes_summary.items():
            lines.append('  "' + path + '": "' + h + '"')
    else:
        lines.append("artifact_hashes: {}")

    # Add approval_summary
    lines.append('approval_summary: "' + approval_summary + '"')

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Check branch sync
# ---------------------------------------------------------------------------


def _check_branch_sync(
    repo_root: str,
    expected_branch: str,
    status_provider: Optional[Callable] = None,
) -> dict:
    """Check branch synchronization status."""
    if status_provider is not None:
        return status_provider(expected_branch)

    result: dict = {
        "branch_match": False,
        "ahead": 0,
        "behind": 0,
        "has_upstream": False,
        "block_reason": None,
    }

    try:
        branch_result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True, text=True, shell=False,
            cwd=repo_root,
        )
        if branch_result.returncode != 0:
            result["block_reason"] = "branch_not_clean"
            return result

        current_branch = branch_result.stdout.strip()
        result["branch_match"] = (current_branch == expected_branch)

        if not result["branch_match"]:
            result["block_reason"] = "branch_mismatch"
            return result

        status_result = subprocess.run(
            ["git", "status", "--porcelain=v1", "--branch"],
            capture_output=True, text=True, shell=False,
            cwd=repo_root,
        )
        if status_result.returncode != 0:
            result["block_reason"] = "branch_not_clean"
            return result

        first_line = status_result.stdout.splitlines()[0] if status_result.stdout else ""
        if not first_line.startswith("##"):
            result["block_reason"] = "branch_not_clean"
            return result

        if "..." not in first_line:
            result["has_upstream"] = False
            return result

        result["has_upstream"] = True

        if "ahead " in first_line:
            import re
            match = re.search(r"ahead (\d+)", first_line)
            if match:
                result["ahead"] = int(match.group(1))

        if "behind " in first_line:
            import re
            match = re.search(r"behind (\d+)", first_line)
            if match:
                result["behind"] = int(match.group(1))

        if result["ahead"] > 0 or result["behind"] > 0:
            result["block_reason"] = "branch_ahead_or_behind"
            return result

    except (FileNotFoundError, subprocess.CalledProcessError):
        result["block_reason"] = "branch_not_clean"

    return result


# ---------------------------------------------------------------------------
# Check git baseline
# ---------------------------------------------------------------------------


def _check_git_baseline(
    repo_root: str,
    allowed_files: tuple[str, ...],
    status_provider: Optional[Callable] = None,
) -> tuple[bool, list[str], list[str]]:
    """Check git working tree baseline before execution."""
    if status_provider is not None:
        return status_provider(repo_root, allowed_files)

    codes: list[str] = []
    warnings: list[str] = []
    allowed_set = set(allowed_files)

    FORBIDDEN_PAYLOAD_PREFIXES = (".ariadne/", "captures/", "reviews/")

    try:
        status_result = subprocess.run(
            ["git", "status", "--porcelain=v1"],
            capture_output=True, text=True, shell=False,
            cwd=repo_root,
        )
        if status_result.returncode != 0:
            codes.append("branch_not_clean")
            return False, codes, warnings

        for line in status_result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            if len(line) < 4:
                continue
            filename = line[3:].strip()
            if not filename:
                continue

            is_forbidden_payload = any(
                filename.startswith(p) for p in FORBIDDEN_PAYLOAD_PREFIXES
            )
            if is_forbidden_payload:
                codes.append("dirty_tree_out_of_scope")
                warnings.append("Forbidden payload path: " + filename)
                continue

            if filename not in allowed_set:
                codes.append("dirty_tree_out_of_scope")
                warnings.append("Unrelated dirty file: " + filename)

    except (FileNotFoundError, subprocess.CalledProcessError):
        codes.append("branch_not_clean")
        return False, codes, warnings

    ok = len(codes) == 0
    return ok, codes, warnings


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
    persistence_fn: Optional[Callable] = None,
    clock_provider: Optional[Callable] = None,
    baseline_check_fn: Optional[Callable] = None,
    branch_sync_fn: Optional[Callable] = None,
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
    baseline_check_fn:
        Injectable baseline check function.
        Default: ``_check_git_baseline``.
    branch_sync_fn:
        Injectable branch sync check function.
        Default: ``_check_branch_sync``.

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
    baseline_fn = baseline_check_fn or _check_git_baseline
    branch_fn = branch_sync_fn or _check_branch_sync

    # Auto-default runs_root when run_id is explicitly provided
    if request.run_id and not request.runs_root:
        request = AriadneTaskCliRequest(
            task_description=request.task_description,
            pr_id=request.pr_id,
            branch=request.branch,
            base_branch=request.base_branch,
            repo_root=request.repo_root,
            allowed_files=request.allowed_files,
            files_to_stage=request.files_to_stage,
            commit_message=request.commit_message,
            pr_title=request.pr_title,
            pr_body=request.pr_body,
            pr_body_path=request.pr_body_path,
            dry_run=request.dry_run,
            execute=request.execute,
            approve=request.approve,
            approved_by=request.approved_by,
            approval_reason=request.approval_reason,
            json_output=request.json_output,
            runs_root=".ariadne/runs",
            run_id=request.run_id,
        )

    # 1. Validate task description
    if not request.task_description or request.task_description.strip() == "":
        codes.append(REASON_MISSING_TASK_DESCRIPTION)
        finished_at = clock_provider() if clock_provider else None
        return _persist_and_return(
            request, persistence_fn, clock_provider,
            AriadneTaskCliResult(
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
            ),
        )

    task_description_hash = hashlib.sha256(request.task_description.encode("utf-8")).hexdigest()[:16]

    # 2. Detect payload artifact path
    payload_artifact_path = _detect_payload_artifact_path(request.files_to_stage)

    # 2b. Build PipelineRunnerRequest
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
        payload_artifact_path=payload_artifact_path,
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
        return _persist_and_return(
            request, persistence_fn, clock_provider,
            AriadneTaskCliResult(
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
            ),
        )

    if pipeline_status in (PipelineRunnerStatus.FAILED,):
        codes.append(REASON_PIPELINE_FAILED)
        finished_at = clock_provider() if clock_provider else None
        return _persist_and_return(
            request, persistence_fn, clock_provider,
            AriadneTaskCliResult(
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
            ),
        )

    if pipeline_has_blockers:
        codes.append(REASON_PIPELINE_STOPPED)
        finished_at = clock_provider() if clock_provider else None
        return _persist_and_return(
            request, persistence_fn, clock_provider,
            AriadneTaskCliResult(
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
            ),
        )

    # 4b. Git baseline check — runs when execute is requested
    if request.execute:
        # Check git baseline (untracked, modified, staged files)
        baseline_ok, baseline_codes, baseline_warnings = baseline_fn(
            repo_root=request.repo_root,
            allowed_files=request.allowed_files,
        )
        codes.extend(baseline_codes)
        warnings.extend(baseline_warnings)

        # Check branch sync
        branch_info = branch_fn(
            repo_root=request.repo_root,
            expected_branch=request.branch,
        )
        if branch_info.get("block_reason"):
            codes.append(branch_info["block_reason"])
            if branch_info["block_reason"] == "branch_mismatch":
                warnings.append(
                    "Branch mismatch: expected '" + request.branch + "'"
                )
            elif branch_info["block_reason"] == "branch_ahead_or_behind":
                warnings.append(
                    "Branch ahead=" + str(branch_info.get("ahead", 0)) + ", "
                    "behind=" + str(branch_info.get("behind", 0))
                )
            else:
                warnings.append("Branch not clean or no upstream configured")

        # If baseline or branch check failed, block before Git Boundary
        if not baseline_ok or branch_info.get("block_reason"):
            finished_at = clock_provider() if clock_provider else None
            return _persist_and_return(
                request, persistence_fn, clock_provider,
                AriadneTaskCliResult(
                    status=AriadneTaskCliStatus.BLOCKED,
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
                    details="Git baseline check failed",
                ),
            )

    # 4c. Render dogfood proof if files_to_stage contains a payload path
    if request.files_to_stage:
        run_id = request.run_id or "run-" + (task_description_hash or "unknown")
        run_record_path = None
        if request.runs_root:
            run_record_path = os.path.join(request.runs_root, run_id, "run.json")

        # Compute plan summary from request params (not from git_plan, which
        # is unavailable before Git Boundary planning)
        plan_summary = _compute_plan_summary(request)

        proof_yaml = _render_dogfood_proof_yaml(
            pipeline_status=pipeline_status,
            pipeline_final_action=pipeline_final_action,
            pipeline_has_blockers=pipeline_has_blockers,
            pipeline_artifact_hashes=pipeline_artifact_hashes,
            command_plan_summary=plan_summary,
            request=request,
            run_id=run_id,
            run_record_path=run_record_path,
            clock_provider=clock_provider,
        )

        # Write proof to each stage-file path (overwrites bridge placeholder)
        for stage_file in request.files_to_stage:
            full_path = os.path.join(request.repo_root, stage_file)
            parent_dir = os.path.dirname(full_path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(proof_yaml)

        # Validate written proof content
        for stage_file in request.files_to_stage:
            full_path = os.path.join(request.repo_root, stage_file)
            proof_ok, proof_codes, proof_warnings = _validate_dogfood_proof_content(full_path)
            codes.extend(proof_codes)
            warnings.extend(proof_warnings)
            if not proof_ok:
                codes.append(REASON_DOGFOOD_PROOF_INCOMPLETE)
                finished_at = clock_provider() if clock_provider else None
                return _persist_and_return(
                    request, persistence_fn, clock_provider,
                    AriadneTaskCliResult(
                        status=AriadneTaskCliStatus.BLOCKED,
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
                        finished_at=clock_provider() if clock_provider else None,
                        details="Dogfood proof incomplete",
                    ),
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
        return _persist_and_return(
            request, persistence_fn, clock_provider,
            AriadneTaskCliResult(
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
            ),
        )

    # 8. Check execution requirements
    if not request.execute:
        codes.append(REASON_EXECUTION_REQUIRED)
        finished_at = clock_provider() if clock_provider else None
        return _persist_and_return(
            request, persistence_fn, clock_provider,
            AriadneTaskCliResult(
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
            ),
        )

    if not request.approve:
        codes.append(REASON_APPROVAL_REQUIRED)
        finished_at = clock_provider() if clock_provider else None
        return _persist_and_return(
            request, persistence_fn, clock_provider,
            AriadneTaskCliResult(
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
            ),
        )

    if not request.approved_by or request.approved_by.strip() == "":
        codes.append(REASON_MISSING_APPROVED_BY)
        finished_at = clock_provider() if clock_provider else None
        return _persist_and_return(
            request, persistence_fn, clock_provider,
            AriadneTaskCliResult(
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
            ),
        )

    if not request.approval_reason or request.approval_reason.strip() == "":
        codes.append(REASON_MISSING_APPROVAL_REASON)
        finished_at = clock_provider() if clock_provider else None
        return _persist_and_return(
            request, persistence_fn, clock_provider,
            AriadneTaskCliResult(
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
            ),
        )

    # 8b. Dry-run warning
    if request.dry_run and request.execute:
        warnings.append("Dry-run mode active (--no-dry-run required for execution)")

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
            return _persist_and_return(
                request, persistence_fn, clock_provider,
                AriadneTaskCliResult(
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
                ),
            )

        execution_results = git_result.execution_results

    # 10. Determine final status
    if pipeline_status == PipelineRunnerStatus.COMPLETED_WITH_WARNING:
        final_status = AriadneTaskCliStatus.COMPLETED_WITH_WARNING
    else:
        final_status = AriadneTaskCliStatus.COMPLETED

    finished_at = clock_provider() if clock_provider else None

    result = AriadneTaskCliResult(
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

    return _persist_and_return(request, persistence_fn, clock_provider, result)


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
# Persist helper
# ---------------------------------------------------------------------------


def _persist_and_return(
    request: AriadneTaskCliRequest,
    persistence_fn: Optional[Callable],
    clock_provider: Optional[Callable],
    result: AriadneTaskCliResult,
) -> AriadneTaskCliResult:
    """Persist a run record if configured, then return the result.

    Parameters
    ----------
    request:
        The CLI request (may contain runs_root and run_id).
    persistence_fn:
        Injectable persistence function.
    clock_provider:
        Optional clock provider.
    result:
        The CLI result to persist and return.

    Returns
    -------
    AriadneTaskCliResult
        The result, possibly updated with run_id and run_record_path.
    """
    if not request.runs_root or not persistence_fn:
        return result

    task_description_hash = result.task_description_hash
    if not task_description_hash and result.task_description:
        task_description_hash = hashlib.sha256(result.task_description.encode("utf-8")).hexdigest()[:16]

    run_id = request.run_id or f"run-{task_description_hash or 'unknown'}"

    persist_request = RunPersistenceRequest(
        runs_root=request.runs_root,
        run_id=run_id,
        task_description_hash=task_description_hash or "",
        task_description_redacted=result.task_description[:80] if result.task_description else "",
        branch=request.branch,
        base_branch=request.base_branch,
        status=result.status,
        reason_codes=result.reason_codes,
        pipeline_status=result.pipeline_status,
        pipeline_final_action=result.pipeline_final_action,
        pipeline_has_blockers=result.pipeline_has_blockers,
        pipeline_step_summary=(),
        pipeline_gate_summary=(),
        git_boundary_status=result.git_boundary_status,
        command_plan_summary=tuple(result.command_plan or []),
        execution_attempted=result.execution_attempted,
        execution_results_summary=result.execution_results,
        approval_summary=request.approval_reason or "",
        artifact_hashes={},
        warnings=result.warnings,
        next_action=result.next_action,
        started_at=result.started_at,
        finished_at=result.finished_at,
        clock_provider=clock_provider,
    )

    persist_result = persistence_fn(persist_request)

    if persist_result.status == RunPersistenceStatus.PERSISTED.value:
        return AriadneTaskCliResult(
            status=result.status,
            reason_codes=result.reason_codes,
            task_description=result.task_description,
            task_description_hash=result.task_description_hash,
            pipeline_status=result.pipeline_status,
            pipeline_final_action=result.pipeline_final_action,
            pipeline_has_blockers=result.pipeline_has_blockers,
            git_boundary_status=result.git_boundary_status,
            command_plan=result.command_plan,
            execution_attempted=result.execution_attempted,
            execution_results=result.execution_results,
            warnings=result.warnings,
            next_action=result.next_action,
            started_at=result.started_at,
            finished_at=result.finished_at,
            details=result.details,
            run_id=run_id,
            run_record_path=persist_result.run_json_path,
        )

    return AriadneTaskCliResult(
        status=AriadneTaskCliStatus.FAILED,
        reason_codes=tuple(list(result.reason_codes) + list(persist_result.reason_codes)),
        task_description=result.task_description,
        task_description_hash=result.task_description_hash,
        pipeline_status=result.pipeline_status,
        pipeline_final_action=result.pipeline_final_action,
        pipeline_has_blockers=result.pipeline_has_blockers,
        git_boundary_status=result.git_boundary_status,
        command_plan=result.command_plan,
        execution_attempted=result.execution_attempted,
        execution_results=result.execution_results,
        warnings=result.warnings,
        next_action="stop",
        started_at=result.started_at,
        finished_at=result.finished_at,
        details=f"Persistence failed: {persist_result.details}",
    )


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

    if result.run_id:
        lines.append(f"Run ID: {result.run_id}")
    if result.run_record_path:
        lines.append(f"Run record: {result.run_record_path}")

    lines.append(f"Next action: {result.next_action}")

    if result.details:
        lines.append(f"Details: {result.details}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def _utc_clock() -> str:
    """Return an ISO-8601 UTC timestamp."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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
    result = run_ariadne_task(
        request,
        persistence_fn=persist_run_record,
        clock_provider=_utc_clock,
    )

    if request.json_output:
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
            "run_id": result.run_id,
            "run_record_path": result.run_record_path,
        }
        print(json.dumps(output_dict, sort_keys=True, ensure_ascii=False))
    else:
        print(_format_human_output(result))

    if result.status in (AriadneTaskCliStatus.COMPLETED, AriadneTaskCliStatus.COMPLETED_WITH_WARNING):
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
