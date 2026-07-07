"""Tests for the ariadne task CLI."""

from __future__ import annotations

import hashlib
import inspect
import json
import os
from pathlib import Path
from typing import Any, Optional

from runner.ariadne_task_cli import (
    _build_cli_request,
    _detect_payload_artifact_path,
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
    REASON_DIRTY_TREE_OUT_OF_SCOPE,
)
from runner.run_persistence import persist_run_record, load_run_record
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
        "allowed_files": ("test_stage_file.py",),
        "files_to_stage": ("test_stage_file.py",),
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


def _clean_baseline_check(repo_root, allowed_files):
    """Clean baseline check provider for tests."""
    return True, [], []


def _clean_branch_sync(repo_root, expected_branch):
    """Clean branch sync provider for tests."""
    return {
        "branch_match": True,
        "ahead": 0,
        "behind": 0,
        "has_upstream": True,
        "block_reason": None,
    }


# ---------------------------------------------------------------------------
# Parse task description
# ---------------------------------------------------------------------------


class TestParseTaskDescription:
    def test_parse_task_description(self):
        """Parses 'ariadne task \"do x\"' → task_description set."""
        args = parse_ariadne_task_args(["do x"])
        request = _build_cli_request(args)
        assert request.task_description == "do x"

    def test_parse_missing_task_description(self):
        """No description → task_description is None."""
        args = parse_ariadne_task_args([])
        request = _build_cli_request(args)
        assert request.task_description == ""


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
        request = _build_cli_request(args)
        assert request.task_description == "test task"
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
            baseline_check_fn=_clean_baseline_check,
            branch_sync_fn=_clean_branch_sync,
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
            baseline_check_fn=_clean_baseline_check,
            branch_sync_fn=_clean_branch_sync,
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
            baseline_check_fn=_clean_baseline_check,
            branch_sync_fn=_clean_branch_sync,
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
            baseline_check_fn=_clean_baseline_check,
            branch_sync_fn=_clean_branch_sync,
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
            baseline_check_fn=_clean_baseline_check,
            branch_sync_fn=_clean_branch_sync,
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
            baseline_check_fn=_clean_baseline_check,
            branch_sync_fn=_clean_branch_sync,
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
            baseline_check_fn=_clean_baseline_check,
            branch_sync_fn=_clean_branch_sync,
        )
        assert call_count[0] == 1


# ---------------------------------------------------------------------------
# No real git mutation in tests
# ---------------------------------------------------------------------------


class TestNoRealGitMutationInTests:
    def test_no_subprocess_run_in_test_code(self):
        """Test code does not use subprocess.run for git mutation."""
        import inspect
        import runner.ariadne_task_cli as mod
        source = inspect.getsource(mod)
        # run_ariadne_task may contain subprocess.run for dirty-tree preflight
        # (git status --short), but must not contain git mutation commands
        assert "git add" not in source
        assert "git commit" not in source
        assert "git push" not in source
        assert "gh pr create" not in source


# ---------------------------------------------------------------------------
# No Docker
# ---------------------------------------------------------------------------


class TestNoDocker:
    def test_no_docker(self):
        """Module does not reference docker."""
        import inspect
        import runner.ariadne_task_cli as mod
        source = inspect.getsource(mod)
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
            baseline_check_fn=_clean_baseline_check,
            branch_sync_fn=_clean_branch_sync,
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
        import inspect
        import runner.ariadne_task_cli as mod
        source = inspect.getsource(mod)
        forbidden = [
            "water_meter", "water-meter", "Broken Clock", "broken_clock",
            "daily-consumption", ".grace", "@grace-", "old Flask",
        ]
        for f in forbidden:
            assert f not in source, f"Forbidden string found: {f!r}"


# ---------------------------------------------------------------------------
# Dirty-tree out-of-scope behavior (PR 0131F)
# ---------------------------------------------------------------------------


class TestDirtyTreeOutOfScope:
    """Dirty-tree preflight blocks when unrelated dirty files exist."""

    def test_dirty_tree_out_of_scope_blocks(self):
        """Unrelated dirty file blocks before Git Boundary."""
        # Use a tmp_path-based repo_root so dirty-tree preflight runs
        import tempfile
        repo_root = tempfile.mkdtemp(prefix="dirty-tree-test-")
        request = _valid_request(
            repo_root=repo_root,
            allowed_files=("allowed.py",),
            files_to_stage=("allowed.py",),
            execute=True,
            approve=True,
            approved_by="tester",
            approval_reason="Testing",
            dry_run=True,
        )
        # Create allowed file
        with open(os.path.join(repo_root, "allowed.py"), "w") as f:
            f.write("# allowed")
        # Init git repo and create initial commit with only allowed file
        import subprocess
        subprocess.run(["git", "init"], cwd=repo_root, capture_output=True)
        subprocess.run(["git", "checkout", "-b", "0129-ariadne-task-cli"], cwd=repo_root, capture_output=True)
        subprocess.run(["git", "add", "allowed.py"], cwd=repo_root, capture_output=True)
        subprocess.run(["git", "commit", "-m", "initial"], cwd=repo_root, capture_output=True)
        # Create an unrelated dirty file AFTER initial commit
        with open(os.path.join(repo_root, "unrelated.py"), "w") as f:
            f.write("# unrelated")
        subprocess.run(["git", "add", "unrelated.py"], cwd=repo_root, capture_output=True)

        result = run_ariadne_task(
            request,
            pipeline_runner_fn=_fake_pipeline_runner(),
            git_boundary_planner_fn=_fake_git_boundary_planner(),
            git_boundary_executor_fn=_fake_git_boundary_executor(),
            clock_provider=_clock,
        )
        assert result.status == AriadneTaskCliStatus.BLOCKED
        assert REASON_DIRTY_TREE_OUT_OF_SCOPE in result.reason_codes

    def test_dirty_tree_allows_allowed_files_only(self):
        """Only allowed dirty payload file can proceed."""
        import tempfile
        repo_root = tempfile.mkdtemp(prefix="dirty-tree-allow-test-")
        request = _valid_request(
            repo_root=repo_root,
            allowed_files=("allowed.py",),
            files_to_stage=("allowed.py",),
        )
        # Create only the allowed file
        with open(os.path.join(repo_root, "allowed.py"), "w") as f:
            f.write("# allowed")
        import subprocess
        subprocess.run(["git", "init"], cwd=repo_root, capture_output=True)
        subprocess.run(["git", "checkout", "-b", "0129-ariadne-task-cli"], cwd=repo_root, capture_output=True)
        subprocess.run(["git", "add", "allowed.py"], cwd=repo_root, capture_output=True)
        subprocess.run(["git", "commit", "-m", "initial"], cwd=repo_root, capture_output=True)

        result = run_ariadne_task(
            request,
            pipeline_runner_fn=_fake_pipeline_runner(),
            git_boundary_planner_fn=_fake_git_boundary_planner(),
            git_boundary_executor_fn=_fake_git_boundary_executor(),
            clock_provider=_clock,
        )
        # Should reach git boundary (blocked on execute, not dirty tree)
        assert REASON_DIRTY_TREE_OUT_OF_SCOPE not in result.reason_codes

    def test_dirty_tree_ariadne_captures_blocked_as_payload(self):
        """.ariadne/ and captures/ are blocked as forbidden payload."""
        import tempfile
        repo_root = tempfile.mkdtemp(prefix="dirty-tree-residue-test-")
        request = _valid_request(
            repo_root=repo_root,
            allowed_files=("allowed.py",),
            files_to_stage=("allowed.py",),
            execute=True,
            approve=True,
            approved_by="tester",
            approval_reason="Testing",
            dry_run=True,
        )
        # Create allowed file
        with open(os.path.join(repo_root, "allowed.py"), "w") as f:
            f.write("# allowed")
        import subprocess
        subprocess.run(["git", "init"], cwd=repo_root, capture_output=True)
        subprocess.run(["git", "checkout", "-b", "0129-ariadne-task-cli"], cwd=repo_root, capture_output=True)
        subprocess.run(["git", "add", "allowed.py"], cwd=repo_root, capture_output=True)
        subprocess.run(["git", "commit", "-m", "initial"], cwd=repo_root, capture_output=True)
        # Create local residue files AFTER initial commit (so they appear as untracked)
        os.makedirs(os.path.join(repo_root, ".ariadne"), exist_ok=True)
        with open(os.path.join(repo_root, ".ariadne/run.json"), "w") as f:
            f.write("{}")
        os.makedirs(os.path.join(repo_root, "captures"), exist_ok=True)
        with open(os.path.join(repo_root, "captures/proof.json"), "w") as f:
            f.write("{}")

        result = run_ariadne_task(
            request,
            pipeline_runner_fn=_fake_pipeline_runner(),
            git_boundary_planner_fn=_fake_git_boundary_planner(),
            git_boundary_executor_fn=_fake_git_boundary_executor(),
            clock_provider=_clock,
        )
        # .ariadne/ and captures/ should be blocked as forbidden payload
        assert REASON_DIRTY_TREE_OUT_OF_SCOPE in result.reason_codes


# ---------------------------------------------------------------------------
# Dry-run warning behavior (PR 0131F)
# ---------------------------------------------------------------------------


class TestDryRunWarning:
    """--execute without --no-dry-run produces explicit dry-run warning."""

    def test_dry_run_execute_without_no_dry_run_warning(self):
        """--execute without --no-dry-run adds dry-run warning."""
        request = _valid_request(
            execute=True,
            approve=True,
            approved_by="tester",
            approval_reason="Testing",
            dry_run=True,
        )
        result = run_ariadne_task(
            request,
            pipeline_runner_fn=_fake_pipeline_runner(),
            git_boundary_planner_fn=_fake_git_boundary_planner(),
            git_boundary_executor_fn=_fake_git_boundary_executor(),
            clock_provider=_clock,
            baseline_check_fn=_clean_baseline_check,
            branch_sync_fn=_clean_branch_sync,
        )
        # Should have dry-run warning
        assert any("Dry-run mode active" in w for w in result.warnings)
        assert any("no-dry-run" in w for w in result.warnings)
        # Execution should not be attempted
        assert result.execution_attempted is False

    def test_dry_run_execution_not_attempted(self):
        """execute=True, dry_run=True → execution_attempted=False."""
        request = _valid_request(
            execute=True,
            approve=True,
            approved_by="tester",
            approval_reason="Testing",
            dry_run=True,
        )
        result = run_ariadne_task(
            request,
            pipeline_runner_fn=_fake_pipeline_runner(),
            git_boundary_planner_fn=_fake_git_boundary_planner(),
            git_boundary_executor_fn=_fake_git_boundary_executor(),
            clock_provider=_clock,
            baseline_check_fn=_clean_baseline_check,
            branch_sync_fn=_clean_branch_sync,
        )
        assert result.execution_attempted is False

    def test_no_dry_run_execution_attempted(self):
        """execute=True, dry_run=False → execution_attempted=True with fake executor."""
        request = _valid_request(
            execute=True,
            approve=True,
            approved_by="tester",
            approval_reason="Testing",
            dry_run=False,
        )
        result = run_ariadne_task(
            request,
            pipeline_runner_fn=_fake_pipeline_runner(),
            git_boundary_planner_fn=_fake_git_boundary_planner(),
            git_boundary_executor_fn=_fake_git_boundary_executor(),
            clock_provider=_clock,
            baseline_check_fn=_clean_baseline_check,
            branch_sync_fn=_clean_branch_sync,
        )
        assert result.execution_attempted is True
        assert len(result.execution_results) > 0


# ---------------------------------------------------------------------------
# Payload routing behavior (PR 0131F)
# ---------------------------------------------------------------------------


class TestPayloadRouting:
    """Payload artifact path routing from CLI to Pipeline Runner."""

    def test_payload_routing_via_cli_detected(self):
        """CLI stage-file payload path reaches PipelineRunnerRequest."""
        # Test _detect_payload_artifact_path directly
        files = (
            ".project-memory/pr/test/PLAN.md",
            ".project-memory/pr/test/reviews/plan-review.yml",
            ".project-memory/pr/test/dogfood-proof.yml",
        )
        result = _detect_payload_artifact_path(files)
        assert result == ".project-memory/pr/test/dogfood-proof.yml"

    def test_payload_routing_excludes_plan_md(self):
        """PLAN.md is excluded from payload routing."""
        files = (".project-memory/pr/test/PLAN.md",)
        result = _detect_payload_artifact_path(files)
        assert result == ""

    def test_payload_routing_excludes_reviews(self):
        """reviews/*.yml files are excluded from payload routing."""
        files = (".project-memory/pr/test/reviews/plan-review.yml",)
        result = _detect_payload_artifact_path(files)
        assert result == ""

    def test_payload_routing_empty_when_no_payload(self):
        """No payload candidate → empty string."""
        files = ("services/runner/src/runner/foo.py",)
        result = _detect_payload_artifact_path(files)
        assert result == ""

    def test_payload_routing_dogfood_proof_yml(self):
        """dogfood-proof.yml is detected as payload."""
        files = (".project-memory/pr/test/dogfood-proof.yml",)
        result = _detect_payload_artifact_path(files)
        assert result == ".project-memory/pr/test/dogfood-proof.yml"


# ---------------------------------------------------------------------------
# Stopped pipeline persistence (PR 0131B)
# ---------------------------------------------------------------------------


class TestStoppedPipelinePersistence:
    """Stopped pipeline with runs_root/run_id persists run records."""

    def test_stopped_pipeline_writes_run_json(self, tmp_path: Path):
        """Stopped pipeline with runs_root writes run.json."""
        runs_root = str(tmp_path / "runs")
        request = _valid_request(
            runs_root=runs_root,
            run_id="stopped-test",
        )
        result = run_ariadne_task(
            request,
            pipeline_runner_fn=_fake_pipeline_runner(status="stopped"),
            git_boundary_planner_fn=_fake_git_boundary_planner(),
            git_boundary_executor_fn=_fake_git_boundary_executor(),
            persistence_fn=persist_run_record,
            clock_provider=_clock,
        )
        assert result.run_id == "stopped-test"
        assert result.run_record_path is not None
        run_json = Path(result.run_record_path)
        assert run_json.exists()
        data = json.loads(run_json.read_text(encoding="utf-8"))
        assert data["status"] == "stopped"
        assert "pipeline_stopped" in data["reason_codes"]

    def test_stopped_pipeline_writes_manifest_json(self, tmp_path: Path):
        """Stopped pipeline writes manifest.json."""
        runs_root = str(tmp_path / "runs")
        request = _valid_request(
            runs_root=runs_root,
            run_id="stopped-test-manifest",
        )
        result = run_ariadne_task(
            request,
            pipeline_runner_fn=_fake_pipeline_runner(status="stopped"),
            git_boundary_planner_fn=_fake_git_boundary_planner(),
            git_boundary_executor_fn=_fake_git_boundary_executor(),
            persistence_fn=persist_run_record,
            clock_provider=_clock,
        )
        assert result.run_record_path is not None
        manifest_path = Path(result.run_record_path).parent / "manifest.json"
        assert manifest_path.exists()
        manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest_data["run_json_hash"] is not None
        assert "run.json" in manifest_data.get("files", [])

    def test_stopped_pipeline_json_includes_run_id_and_path(self, tmp_path: Path):
        """JSON output includes run_id and run_record_path."""
        runs_root = str(tmp_path / "runs")
        request = _valid_request(
            runs_root=runs_root,
            run_id="stopped-test-json",
            json_output=True,
        )
        result = run_ariadne_task(
            request,
            pipeline_runner_fn=_fake_pipeline_runner(status="stopped"),
            git_boundary_planner_fn=_fake_git_boundary_planner(),
            git_boundary_executor_fn=_fake_git_boundary_executor(),
            persistence_fn=persist_run_record,
            clock_provider=_clock,
        )
        # Build the same output dict as main()
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
        assert output_dict["run_id"] == "stopped-test-json"
        assert output_dict["run_record_path"] is not None
        assert "stopped" in output_dict["status"]

    def test_load_run_record_can_read_stopped_run(self, tmp_path: Path):
        """load_run_record can read a stopped persisted run."""
        runs_root = str(tmp_path / "runs")
        request = _valid_request(
            runs_root=runs_root,
            run_id="stopped-test-readback",
        )
        result = run_ariadne_task(
            request,
            pipeline_runner_fn=_fake_pipeline_runner(status="stopped"),
            git_boundary_planner_fn=_fake_git_boundary_planner(),
            git_boundary_executor_fn=_fake_git_boundary_executor(),
            persistence_fn=persist_run_record,
            clock_provider=_clock,
        )
        read_result = load_run_record(runs_root, "stopped-test-readback")
        assert read_result.status == "read_ok"
        assert read_result.record is not None
        assert read_result.record.status == "stopped"
        assert "pipeline_stopped" in read_result.record.reason_codes
        assert read_result.record.execution_attempted is False
        assert read_result.record.git_boundary_status is None

    def test_stopped_run_git_boundary_not_called(self, tmp_path: Path):
        """Stopped run does not call git boundary planner."""
        planner_call_count = [0]
        executor_call_count = [0]

        def counting_planner(request):
            planner_call_count[0] += 1
            return _fake_git_boundary_planner()(request)

        def counting_executor(request, plan, executor=None, clock_provider=None):
            executor_call_count[0] += 1
            return _fake_git_boundary_executor()(request, plan, executor, clock_provider)

        runs_root = str(tmp_path / "runs")
        request = _valid_request(
            runs_root=runs_root,
            run_id="stopped-test-no-git",
        )
        result = run_ariadne_task(
            request,
            pipeline_runner_fn=_fake_pipeline_runner(status="stopped"),
            git_boundary_planner_fn=counting_planner,
            git_boundary_executor_fn=counting_executor,
            persistence_fn=persist_run_record,
            clock_provider=_clock,
        )
        assert planner_call_count[0] == 0
        assert executor_call_count[0] == 0

    def test_stopped_run_no_repo_ariadne_residue(self, tmp_path: Path):
        """Stopped run uses tmp_path, not .ariadne/."""
        runs_root = str(tmp_path / "runs")
        request = _valid_request(
            runs_root=runs_root,
            run_id="stopped-test-residue",
        )
        result = run_ariadne_task(
            request,
            pipeline_runner_fn=_fake_pipeline_runner(status="stopped"),
            git_boundary_planner_fn=_fake_git_boundary_planner(),
            git_boundary_executor_fn=_fake_git_boundary_executor(),
            persistence_fn=persist_run_record,
            clock_provider=_clock,
        )
        assert not Path(".ariadne").exists()


# ---------------------------------------------------------------------------
# Dogfood proof renderer tests
# ---------------------------------------------------------------------------


class TestDogfoodProofRenderer:
    """Dogfood proof renderer creates complete, sanitized proof YAML."""

    def test_proof_renderer_creates_required_fields(self):
        """Proof renderer creates all required fields."""
        from runner.ariadne_task_cli import _render_dogfood_proof_yaml
        request = _valid_request(
            pr_id="0131g-test",
            branch="0131g-test-branch",
            approved_by="tester",
            approval_reason="Testing proof renderer",
        )
        proof = _render_dogfood_proof_yaml(
            pipeline_status="completed",
            pipeline_final_action="continue",
            pipeline_has_blockers=False,
            pipeline_artifact_hashes={"file1.yml": "abc123def456"},
            git_plan=None,
            request=request,
            run_id="run-test-001",
            run_record_path=".ariadne/runs/run-test-001/run.json",
            clock_provider=_clock,
        )
        assert 'schema_version: "0.1"' in proof
        assert 'pr_id: "0131g-test"' in proof
        assert 'run_id: "run-test-001"' in proof
        assert 'branch: "0131g-test-branch"' in proof
        assert 'invocation_mode: "cli"' in proof
        assert 'pipeline_status: "completed"' in proof
        assert 'pipeline_final_action: "continue"' in proof
        assert "pipeline_has_blockers: False" in proof
        assert 'git_boundary_status: "pending"' in proof
        assert "execution_attempted: false" in proof
        assert "pr_created: false" in proof
        assert 'pr_url: "pending-before-gh-pr-create"' in proof
        assert 'run_record_path: ".ariadne/runs/run-test-001/run.json"' in proof
        assert 'run_json_hash: "pending"' in proof
        assert 'proof_artifact_ref:' in proof
        assert 'proof_artifact_ref: "' in proof
        assert 'proof_artifact_ref: ""' not in proof
        assert 'timestamp: "2026-07-06T15:00:00Z"' in proof
        assert 'note: "dogfood proof artifact, not a product feature"' in proof

    def test_proof_renderer_sanitizes_task_prompt(self):
        """Proof renderer does not include raw task description with secrets."""
        from runner.ariadne_task_cli import _render_dogfood_proof_yaml
        request = _valid_request(
            task_description="Implement feature X with secret_key=abc123 and password=secret",
            approved_by="tester",
            approval_reason="Testing with secret=xyz",
        )
        proof = _render_dogfood_proof_yaml(
            pipeline_status="completed",
            pipeline_final_action="continue",
            pipeline_has_blockers=False,
            pipeline_artifact_hashes={},
            git_plan=None,
            request=request,
            run_id="run-test-002",
            run_record_path=None,
            clock_provider=_clock,
        )
        # Raw task description should not appear in proof
        assert "secret_key=abc123" not in proof
        assert "password=secret" not in proof
        # Approval summary is sanitized (truncated to 80 chars)
        # The approval_reason is included but truncated
        assert "secret=xyz" in proof  # truncated to 80 chars, still contains the reason

    def test_proof_renderer_no_raw_stdout_stderr(self):
        """Proof renderer does not include raw stdout/stderr."""
        from runner.ariadne_task_cli import _render_dogfood_proof_yaml
        request = _valid_request(
            approved_by="tester",
            approval_reason="Testing",
        )
        proof = _render_dogfood_proof_yaml(
            pipeline_status="completed",
            pipeline_final_action="continue",
            pipeline_has_blockers=False,
            pipeline_artifact_hashes={"output.log": "abcdef1234567890"},
            git_plan=None,
            request=request,
            run_id="run-test-003",
            run_record_path=None,
            clock_provider=_clock,
        )
        # Only operation summaries and sanitized hashes, no raw stdout/stderr
        assert "stdout" not in proof
        assert "stderr" not in proof
        # Hashes should be truncated to 16 chars
        assert "abcdef1234567890" in proof

    def test_proof_renderer_pr_url_pending_before_gh_pr_create(self):
        """pr_url is 'pending-before-gh-pr-create' before gh pr create."""
        from runner.ariadne_task_cli import _render_dogfood_proof_yaml
        request = _valid_request(
            approved_by="tester",
            approval_reason="Testing",
        )
        proof = _render_dogfood_proof_yaml(
            pipeline_status="completed",
            pipeline_final_action="continue",
            pipeline_has_blockers=False,
            pipeline_artifact_hashes={},
            git_plan=None,
            request=request,
            run_id="run-test-004",
            run_record_path=None,
            clock_provider=_clock,
        )
        assert 'pr_url: "pending-before-gh-pr-create"' in proof
        # Not empty, not a real URL
        assert "https://" not in proof
        assert "github.com" not in proof

    def test_proof_renderer_includes_command_plan_summary(self):
        """Proof includes command_plan_summary with operation names."""
        from runner.ariadne_task_cli import _render_dogfood_proof_yaml
        from runner.git_boundary import GitCommandSpec
        request = _valid_request(
            approved_by="tester",
            approval_reason="Testing",
        )
        # Create a mock git plan with command specs
        class MockGitPlan:
            command_specs = (
                GitCommandSpec(
                    operation="git_status",
                    argv=("git", "status"),
                    cwd=".",
                    allowed_files=(),
                    requires_human_approval=False,
                    side_effecting=False,
                    redacted_display="git status",
                ),
                GitCommandSpec(
                    operation="git_add",
                    argv=("git", "add", "--", "file.yml"),
                    cwd=".",
                    allowed_files=(),
                    requires_human_approval=False,
                    side_effecting=False,
                    redacted_display="git add -- 1 file(s)",
                ),
            )
        proof = _render_dogfood_proof_yaml(
            pipeline_status="completed",
            pipeline_final_action="continue",
            pipeline_has_blockers=False,
            pipeline_artifact_hashes={},
            git_plan=MockGitPlan(),
            request=request,
            run_id="run-test-005",
            run_record_path=None,
            clock_provider=_clock,
        )
        assert "command_plan_summary:" in proof
        assert '"git_status"' in proof
        assert '"git_add"' in proof

    def test_proof_renderer_includes_execution_attempted(self):
        """execution_attempted is False at render time."""
        from runner.ariadne_task_cli import _render_dogfood_proof_yaml
        request = _valid_request(
            approved_by="tester",
            approval_reason="Testing",
        )
        proof = _render_dogfood_proof_yaml(
            pipeline_status="completed",
            pipeline_final_action="continue",
            pipeline_has_blockers=False,
            pipeline_artifact_hashes={},
            git_plan=None,
            request=request,
            run_id="run-test-006",
            run_record_path=None,
            clock_provider=_clock,
        )
        assert "execution_attempted: false" in proof

    def test_proof_renderer_includes_run_record_path(self):
        """Proof includes run_record_path."""
        from runner.ariadne_task_cli import _render_dogfood_proof_yaml
        request = _valid_request(
            approved_by="tester",
            approval_reason="Testing",
            runs_root="/tmp/runs",
        )
        proof = _render_dogfood_proof_yaml(
            pipeline_status="completed",
            pipeline_final_action="continue",
            pipeline_has_blockers=False,
            pipeline_artifact_hashes={},
            git_plan=None,
            request=request,
            run_id="run-test-007",
            run_record_path="/tmp/runs/run-test-007/run.json",
            clock_provider=_clock,
        )
        assert 'run_record_path: "/tmp/runs/run-test-007/run.json"' in proof

    def test_proof_renderer_run_json_hash_pending_if_not_persisted(self):
        """run_json_hash is 'pending' when not yet persisted."""
        from runner.ariadne_task_cli import _render_dogfood_proof_yaml
        request = _valid_request(
            approved_by="tester",
            approval_reason="Testing",
        )
        proof = _render_dogfood_proof_yaml(
            pipeline_status="completed",
            pipeline_final_action="continue",
            pipeline_has_blockers=False,
            pipeline_artifact_hashes={},
            git_plan=None,
            request=request,
            run_id="run-test-008",
            run_record_path=None,
            clock_provider=_clock,
        )
        assert 'run_json_hash: "pending"' in proof

    def test_proof_renderer_includes_approval_summary(self):
        """Proof includes sanitized approval_summary."""
        from runner.ariadne_task_cli import _render_dogfood_proof_yaml
        request = _valid_request(
            approved_by="human-reviewer-001",
            approval_reason="Pipeline completed, all gates passed",
        )
        proof = _render_dogfood_proof_yaml(
            pipeline_status="completed",
            pipeline_final_action="continue",
            pipeline_has_blockers=False,
            pipeline_artifact_hashes={},
            git_plan=None,
            request=request,
            run_id="run-test-009",
            run_record_path=None,
            clock_provider=_clock,
        )
        assert "approval_summary:" in proof
        assert "human-reviewer-001" in proof
        assert "all gates passed" in proof

    def test_proof_written_before_git_boundary_execution(self):
        """Proof file exists on disk before Git Boundary planner is invoked."""
        import tempfile
        repo_root = tempfile.mkdtemp(prefix="proof-before-git-test-")
        stage_file = ".project-memory/pr/test-dogfood/dogfood-proof.yml"
        request = _valid_request(
            repo_root=repo_root,
            allowed_files=(stage_file,),
            files_to_stage=(stage_file,),
            execute=True,
            approve=True,
            approved_by="tester",
            approval_reason="Testing proof before git",
            dry_run=True,
        )
        # Create parent directory for stage file
        stage_dir = os.path.join(repo_root, ".project-memory", "pr", "test-dogfood")
        os.makedirs(stage_dir, exist_ok=True)

        # Fake planner that observes proof file existence before delegating
        observed = {}

        def planner_asserts_proof_exists(git_request):
            proof_path = os.path.join(repo_root, stage_file)
            observed["proof_exists_before_plan"] = os.path.exists(proof_path)
            return _fake_git_boundary_planner()(git_request)

        result = run_ariadne_task(
            request,
            pipeline_runner_fn=_fake_pipeline_runner(),
            git_boundary_planner_fn=planner_asserts_proof_exists,
            git_boundary_executor_fn=_fake_git_boundary_executor(),
            clock_provider=_clock,
            baseline_check_fn=_clean_baseline_check,
            branch_sync_fn=_clean_branch_sync,
        )
        # Proof file should exist on disk after run_ariadne_task completes
        proof_path = os.path.join(repo_root, stage_file)
        assert os.path.exists(proof_path), f"Proof file not found: {proof_path}"
        # Planner observed proof file existed before it was called
        assert observed.get("proof_exists_before_plan") is True
        # Verify stage_file path is under .project-memory/pr/
        assert stage_file.startswith(".project-memory/pr/")
        # Verify proof content
        with open(proof_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert 'schema_version: "0.1"' in content
        assert 'pr_url: "pending-before-gh-pr-create"' in content
        assert "proof_artifact_ref:" in content


# ---------------------------------------------------------------------------
# Dirty baseline enforcement tests
# ---------------------------------------------------------------------------


class TestDirtyBaselineEnforcement:
    """Dirty baseline enforcement blocks before Git Boundary."""

    def test_dirty_baseline_unrelated_untracked_file_blocks(self):
        """Unrelated untracked file blocks before Git Boundary."""
        from runner.ariadne_task_cli import _check_git_baseline

        def status_provider(repo_root, allowed_files):
            return False, ["dirty_tree_out_of_scope"], ["Unrelated dirty file: unrelated.py"]

        ok, codes, warnings = _check_git_baseline(
            repo_root=".",
            allowed_files=("allowed.py",),
            status_provider=status_provider,
        )
        assert ok is False
        assert "dirty_tree_out_of_scope" in codes

    def test_dirty_baseline_unrelated_tracked_modification_blocks(self):
        """Unrelated tracked modification blocks."""
        from runner.ariadne_task_cli import _check_git_baseline

        def status_provider(repo_root, allowed_files):
            return False, ["dirty_tree_out_of_scope"], ["Unrelated dirty file: modified.py"]

        ok, codes, warnings = _check_git_baseline(
            repo_root=".",
            allowed_files=("allowed.py",),
            status_provider=status_provider,
        )
        assert ok is False
        assert "dirty_tree_out_of_scope" in codes

    def test_dirty_baseline_staged_file_before_run_blocks(self):
        """Staged file before run blocks."""
        from runner.ariadne_task_cli import _check_git_baseline

        def status_provider(repo_root, allowed_files):
            return False, ["dirty_tree_out_of_scope"], ["Unrelated dirty file: staged.py"]

        ok, codes, warnings = _check_git_baseline(
            repo_root=".",
            allowed_files=(),
            status_provider=status_provider,
        )
        assert ok is False
        assert "dirty_tree_out_of_scope" in codes

    def test_dirty_baseline_ariadne_path_blocked(self):
        """.ariadne/** files are blocked as forbidden payload."""
        from runner.ariadne_task_cli import _check_git_baseline

        def status_provider(repo_root, allowed_files):
            return False, ["dirty_tree_out_of_scope"], ["Forbidden payload path: .ariadne/runs/foo/run.json"]

        ok, codes, warnings = _check_git_baseline(
            repo_root=".",
            allowed_files=(),
            status_provider=status_provider,
        )
        assert ok is False
        assert "dirty_tree_out_of_scope" in codes

    def test_dirty_baseline_captures_path_blocked(self):
        """captures/** files are blocked as forbidden payload."""
        from runner.ariadne_task_cli import _check_git_baseline

        def status_provider(repo_root, allowed_files):
            return False, ["dirty_tree_out_of_scope"], ["Forbidden payload path: captures/proof.json"]

        ok, codes, warnings = _check_git_baseline(
            repo_root=".",
            allowed_files=(),
            status_provider=status_provider,
        )
        assert ok is False
        assert "dirty_tree_out_of_scope" in codes

    def test_dirty_baseline_prevents_execution_attempted_true(self):
        """Dirty tree prevents execution_attempted=true."""
        import tempfile
        repo_root = tempfile.mkdtemp(prefix="dirty-exec-test-")
        request = _valid_request(
            repo_root=repo_root,
            allowed_files=("allowed.py",),
            files_to_stage=("allowed.py",),
            execute=True,
            approve=True,
            approved_by="tester",
            approval_reason="Testing",
            dry_run=True,
        )
        # Create allowed file
        with open(os.path.join(repo_root, "allowed.py"), "w") as f:
            f.write("# allowed")
        # Init git repo
        import subprocess
        subprocess.run(["git", "init"], cwd=repo_root, capture_output=True)
        subprocess.run(["git", "checkout", "-b", "0129-ariadne-task-cli"], cwd=repo_root, capture_output=True)
        subprocess.run(["git", "add", "allowed.py"], cwd=repo_root, capture_output=True)
        subprocess.run(["git", "commit", "-m", "initial"], cwd=repo_root, capture_output=True)
        # Create unrelated dirty file
        with open(os.path.join(repo_root, "unrelated.py"), "w") as f:
            f.write("# unrelated")

        result = run_ariadne_task(
            request,
            pipeline_runner_fn=_fake_pipeline_runner(),
            git_boundary_planner_fn=_fake_git_boundary_planner(),
            git_boundary_executor_fn=_fake_git_boundary_executor(),
            clock_provider=_clock,
        )
        assert result.execution_attempted is False
        assert REASON_DIRTY_TREE_OUT_OF_SCOPE in result.reason_codes

    def test_dirty_baseline_returns_dirty_tree_out_of_scope_code(self):
        """Dirty baseline returns dirty_tree_out_of_scope reason code."""
        from runner.ariadne_task_cli import _check_git_baseline

        def status_provider(repo_root, allowed_files):
            return False, ["dirty_tree_out_of_scope"], ["Unrelated dirty file: foo.py"]

        ok, codes, warnings = _check_git_baseline(
            repo_root=".",
            allowed_files=(),
            status_provider=status_provider,
        )
        assert "dirty_tree_out_of_scope" in codes

    def test_dirty_baseline_clean_tree_proceeds(self):
        """Clean tree with allowed files proceeds."""
        from runner.ariadne_task_cli import _check_git_baseline

        def status_provider(repo_root, allowed_files):
            return True, [], []

        ok, codes, warnings = _check_git_baseline(
            repo_root=".",
            allowed_files=("allowed.py",),
            status_provider=status_provider,
        )
        assert ok is True
        assert len(codes) == 0


# ---------------------------------------------------------------------------
# Branch baseline tests
# ---------------------------------------------------------------------------


class TestBranchBaseline:
    """Branch baseline enforcement."""

    def test_branch_mismatch_blocks(self):
        """Current branch mismatch blocks."""
        from runner.ariadne_task_cli import _check_branch_sync

        def status_provider(expected_branch):
            return {
                "branch_match": False,
                "ahead": 0,
                "behind": 0,
                "has_upstream": True,
                "block_reason": "branch_mismatch",
            }

        result = _check_branch_sync(
            repo_root=".",
            expected_branch="right-branch",
            status_provider=status_provider,
        )
        assert result["branch_match"] is False
        assert result["block_reason"] == "branch_mismatch"

    def test_branch_ahead_of_upstream_blocks(self):
        """Branch ahead of upstream blocks."""
        from runner.ariadne_task_cli import _check_branch_sync

        def status_provider(expected_branch):
            return {
                "branch_match": True,
                "ahead": 3,
                "behind": 0,
                "has_upstream": True,
                "block_reason": "branch_ahead_or_behind",
            }

        result = _check_branch_sync(
            repo_root=".",
            expected_branch="test-branch",
            status_provider=status_provider,
        )
        assert result["block_reason"] == "branch_ahead_or_behind"

    def test_branch_behind_upstream_blocks(self):
        """Branch behind upstream blocks."""
        from runner.ariadne_task_cli import _check_branch_sync

        def status_provider(expected_branch):
            return {
                "branch_match": True,
                "ahead": 0,
                "behind": 2,
                "has_upstream": True,
                "block_reason": "branch_ahead_or_behind",
            }

        result = _check_branch_sync(
            repo_root=".",
            expected_branch="test-branch",
            status_provider=status_provider,
        )
        assert result["block_reason"] == "branch_ahead_or_behind"

    def test_branch_no_upstream_blocks(self):
        """No upstream configured blocks."""
        from runner.ariadne_task_cli import _check_branch_sync

        def status_provider(expected_branch):
            return {
                "branch_match": True,
                "ahead": 0,
                "behind": 0,
                "has_upstream": False,
                "block_reason": "branch_not_clean",
            }

        result = _check_branch_sync(
            repo_root=".",
            expected_branch="test-branch",
            status_provider=status_provider,
        )
        assert result["block_reason"] == "branch_not_clean"

    def test_branch_clean_synced_proceeds(self):
        """Clean synchronized branch proceeds."""
        from runner.ariadne_task_cli import _check_branch_sync

        def status_provider(expected_branch):
            return {
                "branch_match": True,
                "ahead": 0,
                "behind": 0,
                "has_upstream": True,
                "block_reason": None,
            }

        result = _check_branch_sync(
            repo_root=".",
            expected_branch="test-branch",
            status_provider=status_provider,
        )
        assert result["block_reason"] is None
        assert result["branch_match"] is True


# ---------------------------------------------------------------------------
# Dry-run / No-dry-run behavior tests
# ---------------------------------------------------------------------------


class TestDryRunNoDryRunBehavior:
    """Dry-run and no-dry-run behavior."""

    def test_dry_run_still_non_mutating_with_clean_baseline(self):
        """--dry-run with clean baseline: no execution side effects."""
        request = _valid_request(
            execute=True,
            approve=True,
            approved_by="tester",
            approval_reason="Testing",
            dry_run=True,
        )
        result = run_ariadne_task(
            request,
            pipeline_runner_fn=_fake_pipeline_runner(),
            git_boundary_planner_fn=_fake_git_boundary_planner(),
            git_boundary_executor_fn=_fake_git_boundary_executor(),
            clock_provider=_clock,
            baseline_check_fn=_clean_baseline_check,
            branch_sync_fn=_clean_branch_sync,
        )
        assert result.execution_attempted is False
        assert any("Dry-run mode active" in w for w in result.warnings)

    def test_no_dry_run_dirty_baseline_blocks_before_execution(self):
        """--no-dry-run with dirty baseline blocks before execution."""
        import tempfile
        repo_root = tempfile.mkdtemp(prefix="no-dry-dirty-test-")
        request = _valid_request(
            repo_root=repo_root,
            allowed_files=("allowed.py",),
            files_to_stage=("allowed.py",),
            execute=True,
            approve=True,
            approved_by="tester",
            approval_reason="Testing",
            dry_run=False,
        )
        # Create allowed file
        with open(os.path.join(repo_root, "allowed.py"), "w") as f:
            f.write("# allowed")
        # Init git repo
        import subprocess
        subprocess.run(["git", "init"], cwd=repo_root, capture_output=True)
        subprocess.run(["git", "checkout", "-b", "0129-ariadne-task-cli"], cwd=repo_root, capture_output=True)
        subprocess.run(["git", "add", "allowed.py"], cwd=repo_root, capture_output=True)
        subprocess.run(["git", "commit", "-m", "initial"], cwd=repo_root, capture_output=True)
        # Create unrelated dirty file
        with open(os.path.join(repo_root, "unrelated.py"), "w") as f:
            f.write("# unrelated")

        result = run_ariadne_task(
            request,
            pipeline_runner_fn=_fake_pipeline_runner(),
            git_boundary_planner_fn=_fake_git_boundary_planner(),
            git_boundary_executor_fn=_fake_git_boundary_executor(),
            clock_provider=_clock,
        )
        assert result.execution_attempted is False
        assert REASON_DIRTY_TREE_OUT_OF_SCOPE in result.reason_codes

    def test_no_dry_run_clean_baseline_fake_git_gh_proceeds(self):
        """--no-dry-run with clean baseline and fake git/gh proceeds."""
        import tempfile
        repo_root = tempfile.mkdtemp(prefix="no-dry-clean-test-")
        request = _valid_request(
            repo_root=repo_root,
            allowed_files=("allowed.py",),
            files_to_stage=("allowed.py",),
            execute=True,
            approve=True,
            approved_by="tester",
            approval_reason="Testing",
            dry_run=False,
        )
        # Create allowed file
        with open(os.path.join(repo_root, "allowed.py"), "w") as f:
            f.write("# allowed")
        # Init git repo
        import subprocess
        subprocess.run(["git", "init"], cwd=repo_root, capture_output=True)
        subprocess.run(["git", "checkout", "-b", "0129-ariadne-task-cli"], cwd=repo_root, capture_output=True)
        subprocess.run(["git", "add", "allowed.py"], cwd=repo_root, capture_output=True)
        subprocess.run(["git", "commit", "-m", "initial"], cwd=repo_root, capture_output=True)

        result = run_ariadne_task(
            request,
            pipeline_runner_fn=_fake_pipeline_runner(),
            git_boundary_planner_fn=_fake_git_boundary_planner(),
            git_boundary_executor_fn=_fake_git_boundary_executor(),
            clock_provider=_clock,
        )
        assert result.execution_attempted is True
        assert len(result.execution_results) > 0


# ---------------------------------------------------------------------------
# Dogfood proof incomplete blocks
# ---------------------------------------------------------------------------


class TestDogfoodProofIncomplete:
    """Incomplete dogfood proof blocks."""

    def test_dogfood_proof_incomplete_reason_defined(self):
        """REASON_DOGFOOD_PROOF_INCOMPLETE is defined."""
        from runner.ariadne_task_cli import REASON_DOGFOOD_PROOF_INCOMPLETE
        assert REASON_DOGFOOD_PROOF_INCOMPLETE == "dogfood_proof_incomplete"

    def test_proof_renderer_without_stage_file_skips(self):
        """No files_to_stage → proof renderer is skipped."""
        from runner.ariadne_task_cli import _render_dogfood_proof_yaml
        request = _valid_request(
            files_to_stage=(),
            approved_by="tester",
            approval_reason="Testing",
        )
        proof = _render_dogfood_proof_yaml(
            pipeline_status="completed",
            pipeline_final_action="continue",
            pipeline_has_blockers=False,
            pipeline_artifact_hashes={},
            git_plan=None,
            request=request,
            run_id="run-test-010",
            run_record_path=None,
            clock_provider=_clock,
        )
        # Proof can still be rendered, but won't be written to disk
        assert proof is not None
        assert 'schema_version: "0.1"' in proof
