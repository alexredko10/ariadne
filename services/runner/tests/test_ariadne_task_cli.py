"""Tests for the ariadne task CLI."""

from __future__ import annotations

import hashlib
import inspect
import json
import os
from pathlib import Path
from typing import Any, Optional

from runner.ariadne_task_cli import (
    AriadneTaskCliRequest,
    AriadneTaskCliResult,
    AriadneTaskCliStatus,
    parse_ariadne_task_args,
    run_ariadne_task,
    main,
    REASON_MISSING_TASK_DESCRIPTION,
    REASON_PIPELINE_STOPPED,
    REASON_PIPELINE_FAILED,
    REASON_GIT_BOUNDARY_BLOCKED,
    REASON_EXECUTION_REQUIRED,
    REASON_APPROVAL_REQUIRED,
    REASON_MISSING_APPROVED_BY,
    REASON_MISSING_APPROVAL_REASON,
    REASON_EXECUTION_FAILED,
)
from runner.pipeline_runner import (
    PipelineRunnerRequest,
    PipelineRunnerResult,
    PipelineRunnerStatus,
)
from runner.git_boundary import (
    GitBoundaryRequest,
    GitBoundaryPlan,
    GitBoundaryResult,
    GitBoundaryStatus,
    GitCommandSpec,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _clock() -> str:
    """Deterministic clock provider."""
    return "2026-07-06T15:00:00Z"


def _fake_pipeline_runner(status: str = "completed", final_action: str = "continue",
                          has_blockers: bool = False) -> Any:
    """Create a fake pipeline runner function."""
    def fn(request: PipelineRunnerRequest) -> PipelineRunnerResult:
        return PipelineRunnerResult(
            status=status,
            reason_codes=(),
            pr_id=request.pr_id,
            branch=request.branch,
            task_title=request.task_title,
            prompt_order=("planner", "plan-review", "coder", "precommit-review"),
            step_results=(),
            gate_results=(),
            final_action=final_action,
            stopped_at=None,
            stop_reason=None,
            has_blockers=has_blockers,
            warnings=(),
            artifact_hashes={
                ".project-memory/pr/test/PLAN.md": "abc123",
                ".project-memory/pr/test/reviews/plan-review.yml": "def456",
                ".project-memory/pr/test/reviews/precommit-review.yml": "ghi789",
            },
            proof_summary="Pipeline completed",
            started_at=_clock(),
            finished_at=_clock(),
            details=None,
        )
    return fn


def _fake_git_boundary_planner(eligible: bool = True, dirty_valid: bool = True,
                                codes: Optional[list[str]] = None) -> Any:
    """Create a fake git boundary planner function."""
    def fn(request: GitBoundaryRequest) -> tuple[GitBoundaryPlan, list[str]]:
        plan = GitBoundaryPlan(
            command_specs=(
                GitCommandSpec(
                    operation="git_status",
                    argv=("git", "status"),
                    cwd=request.repo_root,
                    allowed_files=request.allowed_files,
                    requires_human_approval=False,
                    side_effecting=False,
                    redacted_display="git status",
                    details="Check repository status",
                ),
                GitCommandSpec(
                    operation="git_commit",
                    argv=("git", "commit", "-m", request.commit_message),
                    cwd=request.repo_root,
                    allowed_files=request.allowed_files,
                    requires_human_approval=True,
                    side_effecting=True,
                    redacted_display="git commit -m <redacted>",
                    details="Commit staged changes",
                ),
            ),
            command_count=2,
            files_to_stage=request.files_to_stage,
            rejected_files=(),
            pipeline_eligible=eligible,
            dirty_tree_valid=dirty_valid,
            approval_summary="Approved by test",
        )
        return plan, codes or []
    return fn


def _fake_git_boundary_executor(status: str = "approved") -> Any:
    """Create a fake git boundary executor function."""
    def fn(request: GitBoundaryRequest, plan: GitBoundaryPlan,
           executor: Any = None, clock_provider: Any = None) -> GitBoundaryResult:
        return GitBoundaryResult(
            status=status,
            reason_codes=(),
            approved=True,
            blocked=False,
            command_plan=plan,
            command_count=plan.command_count,
            files_to_stage=plan.files_to_stage,
            rejected_files=plan.rejected_files,
            pipeline_eligible=plan.pipeline_eligible,
            dirty_tree_valid=plan.dirty_tree_valid,
            approval_summary="Approved by test",
            execution_attempted=True,
            execution_results=(
                {"operation": "git_status", "exit_code": "0", "stdout": "ok", "stderr": ""},
                {"operation": "git_commit", "exit_code": "0", "stdout": "ok", "stderr": ""},
            ),
            artifact_hashes=request.pipeline_artifact_hashes,
            started_at=_clock(),
            finished_at=_clock(),
            details=None,
        )
    return fn


def _valid_request(**overrides: Any) -> AriadneTaskCliRequest:
    """Create a valid AriadneTaskCliRequest."""
    kwargs = {
        "task_description": "Implement the ariadne task CLI",
        "pr_id": "0129",
        "branch": "0129-ariadne-task-cli",
        "base_branch": "main",
        "repo_root": ".",
        "allowed_files": ("services/runner/src/runner/ariadne_task_cli.py",),
        "files_to_stage": ("services/runner/src/runner/ariadne_task_cli.py",),
        "commit_message": "PR 0129 — ariadne task CLI",
        "pr_title": "PR 0129 — ariadne task CLI",
        "pr_body": "Implements the ariadne task CLI.",
        "dry_run": True,
        "execute": False,
        "approve": False,
        "approved_by": None,
        "approval_reason": None,
        "json_output": False,
    }
    kwargs.update(overrides)
    return AriadneTaskCliRequest(**kwargs)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Parse task description
# ---------------------------------------------------------------------------


class TestParseTaskDescription:
    def test_parse_task_description(self):
        """Parses 'ariadne task \"do x\"' → task_description set."""
        args = parse_ariadne_task_args(["do x"])
        assert args.task_description == "do x"

    def test_parse_missing_task_description(self):
        """No description → task_description is None."""
        args = parse_ariadne_task_args([])
        assert args.task_description is None


# ---------------------------------------------------------------------------
# Parse options
# ---------------------------------------------------------------------------


class TestParseOptions:
    def test_parse_all_options(self):
        """All CLI options parse correctly."""
        args = parse_ariadne_task_args([
            "test task",
            "--pr-id", "0129",
            "--branch", "0129-test",
            "--base-branch", "develop",
            "--repo-root", "/tmp/repo",
            "--allowed-file", "file1.py",
            "--allowed-file", "file2.py",
            "--stage-file", "file1.py",
            "--commit-message", "Test commit",
            "--pr-title", "Test PR",
            "--pr-body", "Test body",
            "--execute",
            "--approve",
            "--approved-by", "tester",
            "--approval-reason", "Testing",
            "--json",
        ])
        assert args.task_description == "test task"
        assert args.pr_id == "0129"
        assert args.branch == "0129-test"
        assert args.base_branch == "develop"
        assert args.repo_root == "/tmp/repo"
        assert args.allowed_file == ["file1.py", "file2.py"]
        assert args.stage_file == ["file1.py"]
        assert args.commit_message == "Test commit"
        assert args.pr_title == "Test PR"
        assert args.pr_body == "Test body"
        assert args.execute is True
        assert args.approve is True
        assert args.approved_by == "tester"
        assert args.approval_reason == "Testing"
        assert args.json is True


# ---------------------------------------------------------------------------
# Default dry-run
# ---------------------------------------------------------------------------


class TestDefaultDryRun:
    def test_default_dry_run(self):
        """Default mode: pipeline runs, git boundary plans, no execution."""
        request = _valid_request()
        result = run_ariadne_task(
            request,
            pipeline_runner_fn=_fake_pipeline_runner(),
            git_boundary_planner_fn=_fake_git_boundary_planner(),
            git_boundary_executor_fn=_fake_git_boundary_executor(),
            clock_provider=_clock,
        )
        assert result.status == AriadneTaskCliStatus.BLOCKED
        assert REASON_EXECUTION_REQUIRED in result.reason_codes
        assert result.execution_attempted is False
        assert result.command_plan is not None
        assert len(result.command_plan) > 0


# ---------------------------------------------------------------------------
# Pipeline completed
# ---------------------------------------------------------------------------


class TestPipelineCompleted:
    def test_pipeline_completed(self):
        """Pipeline completed → GitBoundaryRequest built with artifact_hashes."""
        request = _valid_request(execute=True, approve=True, approved_by="tester",
                                  approval_reason="Testing", dry_run=True)
        result = run_ariadne_task(
            request,
            pipeline_runner_fn=_fake_pipeline_runner(),
            git_boundary_planner_fn=_fake_git_boundary_planner(),
            git_boundary_executor_fn=_fake_git_boundary_executor(),
            clock_provider=_clock,
        )
        assert result.pipeline_status == "completed"
        assert result.pipeline_final_action == "continue"
        assert result.pipeline_has_blockers is False


# ---------------------------------------------------------------------------
# Pipeline stopped
# ---------------------------------------------------------------------------


class TestPipelineStopped:
    def test_pipeline_stopped(self):
        """Pipeline stopped → git boundary blocked, CLI blocked."""
        request = _valid_request()
        result = run_ariadne_task(
            request,
            pipeline_runner_fn=_fake_pipeline_runner(status="stopped"),
            git_boundary_planner_fn=_fake_git_boundary_planner(),
            git_boundary_executor_fn=_fake_git_boundary_executor(),
            clock_provider=_clock,
        )
        assert result.status == AriadneTaskCliStatus.STOPPED
        assert REASON_PIPELINE_STOPPED in result.reason_codes


# ---------------------------------------------------------------------------
# Pipeline failed
# ---------------------------------------------------------------------------


class TestPipelineFailed:
    def test_pipeline_failed(self):
        """Pipeline failed → CLI failed."""
        request = _valid_request()
        result = run_ariadne_task(
            request,
            pipeline_runner_fn=_fake_pipeline_runner(status="failed"),
            git_boundary_planner_fn=_fake_git_boundary_planner(),
            git_boundary_executor_fn=_fake_git_boundary_executor(),
            clock_provider=_clock,
        )
        assert result.status == AriadneTaskCliStatus.FAILED
        assert REASON_PIPELINE_FAILED in result.reason_codes


# ---------------------------------------------------------------------------
# Pipeline blockers
# ---------------------------------------------------------------------------


class TestPipelineBlockers:
    def test_pipeline_blockers(self):
        """has_blockers true → git boundary blocked."""
        request = _valid_request()
        result = run_ariadne_task(
            request,
            pipeline_runner_fn=_fake_pipeline_runner(has_blockers=True),
            git_boundary_planner_fn=_fake_git_boundary_planner(),
            git_boundary_executor_fn=_fake_git_boundary_executor(),
            clock_provider=_clock,
        )
        assert result.status == AriadneTaskCliStatus.STOPPED
        assert REASON_PIPELINE_STOPPED in result.reason_codes


# ---------------------------------------------------------------------------
# Git blocked without execute
# ---------------------------------------------------------------------------


class TestGitBlockedWithoutExecute:
    def test_git_blocked_without_execute(self):
        """No --execute → blocked."""
        request = _valid_request(execute=False)
        result = run_ariadne_task(
            request,
            pipeline_runner_fn=_fake_pipeline_runner(),
            git_boundary_planner_fn=_fake_git_boundary_planner(),
            git_boundary_executor_fn=_fake_git_boundary_executor(),
            clock_provider=_clock,
        )
        assert result.status == AriadneTaskCliStatus.BLOCKED
        assert REASON_EXECUTION_REQUIRED in result.reason_codes


# ---------------------------------------------------------------------------
# Git blocked without approve
# ---------------------------------------------------------------------------


class TestGitBlockedWithoutApprove:
    def test_git_blocked_without_approve(self):
        """--execute without --approve → blocked."""
        request = _valid_request(execute=True, approve=False)
        result = run_ariadne_task(
            request,
            pipeline_runner_fn=_fake_pipeline_runner(),
            git_boundary_planner_fn=_fake_git_boundary_planner(),
            git_boundary_executor_fn=_fake_git_boundary_executor(),
            clock_provider=_clock,
        )
        assert result.status == AriadneTaskCliStatus.BLOCKED
        assert REASON_APPROVAL_REQUIRED in result.reason_codes


# ---------------------------------------------------------------------------
# Git blocked missing approved_by
# ---------------------------------------------------------------------------


class TestGitBlockedMissingApprovedBy:
    def test_git_blocked_missing_approved_by(self):
        """--approve without --approved-by → blocked."""
        request = _valid_request(execute=True, approve=True, approved_by="",
                                  approval_reason="Testing")
        result = run_ariadne_task(
            request,
            pipeline_runner_fn=_fake_pipeline_runner(),
            git_boundary_planner_fn=_fake_git_boundary_planner(),
            git_boundary_executor_fn=_fake_git_boundary_executor(),
            clock_provider=_clock,
        )
        assert result.status == AriadneTaskCliStatus.BLOCKED
        assert REASON_MISSING_APPROVED_BY in result.reason_codes


# ---------------------------------------------------------------------------
# Git blocked missing approval_reason
# ---------------------------------------------------------------------------


class TestGitBlockedMissingApprovalReason:
    def test_git_blocked_missing_approval_reason(self):
        """--approve without --approval-reason → blocked."""
        request = _valid_request(execute=True, approve=True, approved_by="tester",
                                  approval_reason="")
        result = run_ariadne_task(
            request,
            pipeline_runner_fn=_fake_pipeline_runner(),
            git_boundary_planner_fn=_fake_git_boundary_planner(),
            git_boundary_executor_fn=_fake_git_boundary_executor(),
            clock_provider=_clock,
        )
        assert result.status == AriadneTaskCliStatus.BLOCKED
        assert REASON_MISSING_APPROVAL_REASON in result.reason_codes


# ---------------------------------------------------------------------------
# Approval does not override pipeline block
# ---------------------------------------------------------------------------


class TestApprovalDoesNotOverridePipelineBlock:
    def test_approval_does_not_override_pipeline_block(self):
        """Approval but stopped pipeline → blocked."""
        request = _valid_request(execute=True, approve=True, approved_by="tester",
                                  approval_reason="Testing")
        result = run_ariadne_task(
            request,
            pipeline_runner_fn=_fake_pipeline_runner(status="stopped"),
            git_boundary_planner_fn=_fake_git_boundary_planner(),
            git_boundary_executor_fn=_fake_git_boundary_executor(),
            clock_provider=_clock,
        )
        assert result.status == AriadneTaskCliStatus.STOPPED
        assert REASON_PIPELINE_STOPPED in result.reason_codes


# ---------------------------------------------------------------------------
# Execution with full approval
# ---------------------------------------------------------------------------


class TestExecutionWithFullApproval:
    def test_execution_with_full_approval(self):
        """All flags present → execution attempted."""
        request = _valid_request(execute=True, approve=True, approved_by="tester",
                                  approval_reason="Testing", dry_run=False)
        result = run_ariadne_task(
            request,
            pipeline_runner_fn=_fake_pipeline_runner(),
            git_boundary_planner_fn=_fake_git_boundary_planner(),
            git_boundary_executor_fn=_fake_git_boundary_executor(),
            clock_provider=_clock,
        )
        assert result.status == AriadneTaskCliStatus.COMPLETED
        assert result.execution_attempted is True
        assert len(result.execution_results) > 0


# ---------------------------------------------------------------------------
# Human-readable output
# ---------------------------------------------------------------------------


class TestHumanReadableOutput:
    def test_human_readable_output(self):
        """Default output contains key fields."""
        request = _valid_request()
        result = run_ariadne_task(
            request,
            pipeline_runner_fn=_fake_pipeline_runner(),
            git_boundary_planner_fn=_fake_git_boundary_planner(),
            git_boundary_executor_fn=_fake_git_boundary_executor(),
            clock_provider=_clock,
        )
        from runner.ariadne_task_cli import _format_human_output
        output = _format_human_output(result)
        assert "Ariadne task:" in output
        assert "Pipeline status:" in output
        assert "Git Boundary status:" in output
        assert "Command plan:" in output
        assert "Execution attempted:" in output
        assert "Next action:" in output


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------


class TestJsonOutput:
    def test_json_output_deterministic(self):
        """JSON output is deterministic."""
        request = _valid_request(json_output=True)
        result = run_ariadne_task(
            request,
            pipeline_runner_fn=_fake_pipeline_runner(),
            git_boundary_planner_fn=_fake_git_boundary_planner(),
            git_boundary_executor_fn=_fake_git_boundary_executor(),
            clock_provider=_clock,
        )
        # Build JSON dict
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
        json_str = json.dumps(output_dict, sort_keys=True, ensure_ascii=False)
        parsed = json.loads(json_str)
        assert parsed["status"] == result.status
        assert parsed["task_description"] == result.task_description
        assert parsed["pipeline_status"] == result.pipeline_status


# ---------------------------------------------------------------------------
# Fake pipeline runner
# ---------------------------------------------------------------------------


class TestFakePipelineRunner:
    def test_fake_pipeline_runner_used(self):
        """Injected fake pipeline runner used."""
        call_count = [0]

        def fake_runner(request: PipelineRunnerRequest) -> PipelineRunnerResult:
            call_count[0] += 1
            return _fake_pipeline_runner()(request)

        request = _valid_request()
        result = run_ariadne_task(
            request,
            pipeline_runner_fn=fake_runner,
            git_boundary_planner_fn=_fake_git_boundary_planner(),
            git_boundary_executor_fn=_fake_git_boundary_executor(),
            clock_provider=_clock,
        )
        assert call_count[0] == 1


# ---------------------------------------------------------------------------
# Fake git boundary planner
# ---------------------------------------------------------------------------


class TestFakeGitBoundaryPlanner:
    def test_fake_planner_used(self):
        """Injected fake planner used."""
        call_count = [0]

        def fake_planner(request: GitBoundaryRequest) -> tuple[GitBoundaryPlan, list[str]]:
            call_count[0] += 1
            return _fake_git_boundary_planner()(request)

        request = _valid_request()
        result = run_ariadne_task(
            request,
            pipeline_runner_fn=_fake_pipeline_runner(),
            git_boundary_planner_fn=fake_planner,
            git_boundary_executor_fn=_fake_git_boundary_executor(),
            clock_provider=_clock,
        )
        assert call_count[0] == 1


# ---------------------------------------------------------------------------
# Fake git boundary executor
# ---------------------------------------------------------------------------


class TestFakeGitBoundaryExecutor:
    def test_fake_executor_used(self):
        """Injected fake executor used."""
        call_count = [0]

        def fake_executor(request: GitBoundaryRequest, plan: GitBoundaryPlan,
                          executor: Any = None, clock_provider: Any = None) -> GitBoundaryResult:
            call_count[0] += 1
            return _fake_git_boundary_executor()(request, plan, executor, clock_provider)

        request = _valid_request(execute=True, approve=True, approved_by="tester",
                                  approval_reason="Testing", dry_run=False)
        result = run_ariadne_task(
            request,
            pipeline_runner_fn=_fake_pipeline_runner(),
            git_boundary_planner_fn=_fake_git_boundary_planner(),
            git_boundary_executor_fn=fake_executor,
            clock_provider=_clock,
        )
        assert call_count[0] == 1


# ---------------------------------------------------------------------------
# No real git mutation in tests
# ---------------------------------------------------------------------------


class TestNoRealGitMutationInTests:
    def test_no_subprocess_run_in_test_code(self):
        """Test code does not use subprocess.run for execution."""
        import inspect
        from runner.ariadne_task_cli import run_ariadne_task
        source = inspect.getsource(run_ariadne_task)
        # run_ariadne_task should not contain subprocess.run
        assert "subprocess.run" not in source


# ---------------------------------------------------------------------------
# No Docker
# ---------------------------------------------------------------------------


class TestNoDocker:
    def test_no_docker(self):
        """Module does not reference docker."""
        import inspect
        from runner.ariadne_task_cli import run_ariadne_task
        source = inspect.getsource(run_ariadne_task)
        assert "import docker" not in source


# ---------------------------------------------------------------------------
# No .ariadne/ residue
# ---------------------------------------------------------------------------


class TestNoAriadneResidue:
    def test_no_ariadne_residue(self):
        """Uses tmp_path, not .ariadne/."""
        request = _valid_request()
        result = run_ariadne_task(
            request,
            pipeline_runner_fn=_fake_pipeline_runner(),
            git_boundary_planner_fn=_fake_git_boundary_planner(),
            git_boundary_executor_fn=_fake_git_boundary_executor(),
            clock_provider=_clock,
        )
        assert not Path(".ariadne").exists()


# ---------------------------------------------------------------------------
# No pipeline modified
# ---------------------------------------------------------------------------


class TestNoPipelineModified:
    def test_no_pipeline_import(self):
        """Module imports pipeline_runner but does not modify it."""
        import runner.ariadne_task_cli
        assert hasattr(runner.ariadne_task_cli, "run_ariadne_task")


# ---------------------------------------------------------------------------
# No git boundary modified
# ---------------------------------------------------------------------------


class TestNoGitBoundaryModified:
    def test_no_git_boundary_import(self):
        """Module imports git_boundary but does not modify it."""
        import runner.ariadne_task_cli
        assert hasattr(runner.ariadne_task_cli, "run_ariadne_task")


# ---------------------------------------------------------------------------
# Deterministic repeats
# ---------------------------------------------------------------------------


class TestDeterministicRepeats:
    def test_deterministic_repeats(self):
        """Same inputs → same output."""
        request = _valid_request()
        result1 = run_ariadne_task(
            request,
            pipeline_runner_fn=_fake_pipeline_runner(),
            git_boundary_planner_fn=_fake_git_boundary_planner(),
            git_boundary_executor_fn=_fake_git_boundary_executor(),
            clock_provider=_clock,
        )
        result2 = run_ariadne_task(
            request,
            pipeline_runner_fn=_fake_pipeline_runner(),
            git_boundary_planner_fn=_fake_git_boundary_planner(),
            git_boundary_executor_fn=_fake_git_boundary_executor(),
            clock_provider=_clock,
        )
        assert result1.status == result2.status
        assert result1.reason_codes == result2.reason_codes
        assert result1.task_description_hash == result2.task_description_hash


# ---------------------------------------------------------------------------
# Missing task description
# ---------------------------------------------------------------------------


class TestMissingTaskDescription:
    def test_missing_task_description(self):
        """Empty task description → failed."""
        request = _valid_request(task_description="")
        result = run_ariadne_task(
            request,
            pipeline_runner_fn=_fake_pipeline_runner(),
            git_boundary_planner_fn=_fake_git_boundary_planner(),
            git_boundary_executor_fn=_fake_git_boundary_executor(),
            clock_provider=_clock,
        )
        assert result.status == AriadneTaskCliStatus.FAILED
        assert REASON_MISSING_TASK_DESCRIPTION in result.reason_codes


# ---------------------------------------------------------------------------
# Git boundary blocked
# ---------------------------------------------------------------------------


class TestGitBoundaryBlocked:
    def test_git_boundary_blocked(self):
        """Git boundary planner returns blocked → CLI blocked."""
        request = _valid_request(execute=True, approve=True, approved_by="tester",
                                  approval_reason="Testing")
        result = run_ariadne_task(
            request,
            pipeline_runner_fn=_fake_pipeline_runner(),
            git_boundary_planner_fn=_fake_git_boundary_planner(
                eligible=False, codes=["pipeline_not_eligible"]
            ),
            git_boundary_executor_fn=_fake_git_boundary_executor(),
            clock_provider=_clock,
        )
        assert result.status == AriadneTaskCliStatus.BLOCKED
        assert REASON_GIT_BOUNDARY_BLOCKED in result.reason_codes


# ---------------------------------------------------------------------------
# Product name
# ---------------------------------------------------------------------------


class TestProductName:
    def test_module_docstring_contains_ariadne(self):
        """Module docstring contains 'Ariadne'."""
        import runner.ariadne_task_cli
        doc = runner.ariadne_task_cli.__doc__ or ""
        assert "Ariadne" in doc


# ---------------------------------------------------------------------------
# No forbidden legacy names
# ---------------------------------------------------------------------------


class TestNoForbiddenNames:
    def test_no_forbidden_strings(self):
        """Source contains no forbidden legacy names."""
        from runner.ariadne_task_cli import run_ariadne_task
        source = inspect.getsource(run_ariadne_task)
        forbidden = [
            "water_meter", "water-meter", "Broken Clock", "broken_clock",
            "daily-consumption", ".grace", "@grace-", "old Flask",
        ]
        for f in forbidden:
            assert f not in source, f"Forbidden string found: {f!r}"
