"""Tests for the git boundary."""

from __future__ import annotations

import hashlib
import inspect
import os
from pathlib import Path
from typing import Any, Optional

from runner.git_boundary import (
    GitBoundaryRequest,
    GitCommandSpec,
    GitBoundaryPlan,
    GitBoundaryResult,
    GitBoundaryStatus,
    prepare_git_boundary_plan,
    execute_git_boundary_plan,
    REASON_PIPELINE_NOT_ELIGIBLE,
    REASON_DIRTY_TREE_INVALID,
    REASON_FORBIDDEN_PATH,
    REASON_REJECTED_FILE,
    REASON_MISSING_COMMIT_MESSAGE,
    REASON_MISSING_PR_TITLE,
    REASON_HUMAN_APPROVAL_REQUIRED,
    REASON_MISSING_APPROVED_BY,
    REASON_MISSING_APPROVAL_REASON,
    REASON_EXECUTION_FAILED,
    _FORBIDDEN_PATHS,
    _ADDITIONAL_BLOCKED_PATHS,
    _is_forbidden_path,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _clock() -> str:
    """Deterministic clock provider."""
    return "2026-07-06T14:00:00Z"


def _valid_request(**overrides: Any) -> GitBoundaryRequest:
    """Create a valid GitBoundaryRequest."""
    kwargs = {
        "repo_root": "/tmp/test-repo",
        "base_branch": "main",
        "head_branch": "0128-git-boundary",
        "current_branch": "0128-git-boundary",
        "pipeline_status": "completed",
        "pipeline_final_action": "continue",
        "pipeline_has_blockers": False,
        "pipeline_artifact_hashes": {
            ".project-memory/pr/0128/PLAN.md": "abc123",
            ".project-memory/pr/0128/reviews/plan-review.yml": "def456",
            ".project-memory/pr/0128/reviews/precommit-review.yml": "ghi789",
        },
        "dirty_files": ("services/runner/src/runner/git_boundary.py", "services/runner/tests/test_git_boundary.py"),
        "allowed_files": ("services/runner/src/runner/git_boundary.py", "services/runner/tests/test_git_boundary.py"),
        "files_to_stage": ("services/runner/src/runner/git_boundary.py", "services/runner/tests/test_git_boundary.py"),
        "commit_message": "PR 0128 — Git Boundary implementation",
        "pr_title": "PR 0128 — Git Boundary",
        "pr_body": "Implements the Git Boundary module.",
        "human_approved": True,
        "approved_by": "human-reviewer-001",
        "approval_reason": "Pipeline completed, all gates passed.",
    }
    kwargs.update(overrides)
    return GitBoundaryRequest(**kwargs)  # type: ignore[arg-type]


def _fake_executor(spec: GitCommandSpec) -> dict[str, Any]:
    """Fake executor that returns success."""
    return {"exit_code": 0, "stdout": "ok", "stderr": ""}


def _fake_failing_executor(spec: GitCommandSpec) -> dict[str, Any]:
    """Fake executor that returns failure."""
    return {"exit_code": 1, "stdout": "", "stderr": "error"}


# ---------------------------------------------------------------------------
# Valid pipeline plan
# ---------------------------------------------------------------------------


class TestValidPipelinePlan:
    def test_valid_plan(self):
        """Completed pipeline → plan with 5 command specs."""
        request = _valid_request()
        plan, codes = prepare_git_boundary_plan(request)
        assert plan.command_count == 5
        assert plan.pipeline_eligible is True
        assert plan.dirty_tree_valid is True
        assert len(codes) == 0

    def test_command_specs_order(self):
        """Command specs in deterministic order."""
        request = _valid_request()
        plan, codes = prepare_git_boundary_plan(request)
        operations = [s.operation for s in plan.command_specs]
        assert operations == ["git_status", "git_add", "git_commit", "git_push", "gh_pr_create"]


# ---------------------------------------------------------------------------
# Blocked without approval
# ---------------------------------------------------------------------------


class TestBlockedWithoutApproval:
    def test_blocked_without_approval(self):
        """No human_approved → blocked."""
        request = _valid_request(human_approved=False)
        plan, codes = prepare_git_boundary_plan(request)
        result = execute_git_boundary_plan(request, plan, executor=_fake_executor)
        assert result.status == GitBoundaryStatus.BLOCKED.value
        assert REASON_HUMAN_APPROVAL_REQUIRED in result.reason_codes


# ---------------------------------------------------------------------------
# Missing approved_by
# ---------------------------------------------------------------------------


class TestBlockedMissingApprovedBy:
    def test_missing_approved_by(self):
        """approved_by empty → blocked."""
        request = _valid_request(approved_by="")
        plan, codes = prepare_git_boundary_plan(request)
        result = execute_git_boundary_plan(request, plan, executor=_fake_executor)
        assert result.status == GitBoundaryStatus.BLOCKED.value
        assert REASON_MISSING_APPROVED_BY in result.reason_codes


# ---------------------------------------------------------------------------
# Missing approval_reason
# ---------------------------------------------------------------------------


class TestBlockedMissingApprovalReason:
    def test_missing_approval_reason(self):
        """approval_reason empty → blocked."""
        request = _valid_request(approval_reason="")
        plan, codes = prepare_git_boundary_plan(request)
        result = execute_git_boundary_plan(request, plan, executor=_fake_executor)
        assert result.status == GitBoundaryStatus.BLOCKED.value
        assert REASON_MISSING_APPROVAL_REASON in result.reason_codes


# ---------------------------------------------------------------------------
# Approval does not override pipeline block
# ---------------------------------------------------------------------------


class TestApprovalDoesNotOverridePipelineBlock:
    def test_approval_does_not_override_pipeline_block(self):
        """human_approved but pipeline stopped → blocked."""
        request = _valid_request(pipeline_status="stopped")
        plan, codes = prepare_git_boundary_plan(request)
        assert REASON_PIPELINE_NOT_ELIGIBLE in codes
        result = execute_git_boundary_plan(request, plan, executor=_fake_executor)
        assert result.status == GitBoundaryStatus.BLOCKED.value


# ---------------------------------------------------------------------------
# Blocked pipeline has blockers
# ---------------------------------------------------------------------------


class TestBlockedPipelineHasBlockers:
    def test_blocked_pipeline_has_blockers(self):
        """Pipeline has blockers → blocked."""
        request = _valid_request(pipeline_has_blockers=True)
        plan, codes = prepare_git_boundary_plan(request)
        assert REASON_PIPELINE_NOT_ELIGIBLE in codes


# ---------------------------------------------------------------------------
# Blocked pipeline final_action stop
# ---------------------------------------------------------------------------


class TestBlockedPipelineFinalActionStop:
    def test_blocked_pipeline_final_action_stop(self):
        """final_action=stop → blocked."""
        request = _valid_request(pipeline_final_action="stop")
        plan, codes = prepare_git_boundary_plan(request)
        assert REASON_PIPELINE_NOT_ELIGIBLE in codes


# ---------------------------------------------------------------------------
# Blocked dirty file outside allowed
# ---------------------------------------------------------------------------


class TestBlockedDirtyFileOutsideAllowed:
    def test_dirty_file_outside_allowed(self):
        """Dirty file not in allowed_files → blocked."""
        request = _valid_request(
            dirty_files=("services/runner/src/runner/unauthorized.py",),
            allowed_files=("services/runner/src/runner/git_boundary.py",),
        )
        plan, codes = prepare_git_boundary_plan(request)
        assert REASON_DIRTY_TREE_INVALID in codes
        assert plan.dirty_tree_valid is False


# ---------------------------------------------------------------------------
# Blocked forbidden path
# ---------------------------------------------------------------------------


class TestBlockedForbiddenPath:
    def test_forbidden_path_blocked(self):
        """agents/*.yml dirty → blocked with forbidden_path."""
        request = _valid_request(
            dirty_files=("agents/coder.yml",),
            allowed_files=("agents/coder.yml",),
        )
        plan, codes = prepare_git_boundary_plan(request)
        assert REASON_FORBIDDEN_PATH in codes
        assert plan.dirty_tree_valid is False

    def test_schemas_path_blocked(self):
        """schemas/ path → blocked."""
        request = _valid_request(
            dirty_files=("schemas/schema.yml",),
            allowed_files=("schemas/schema.yml",),
        )
        plan, codes = prepare_git_boundary_plan(request)
        assert REASON_FORBIDDEN_PATH in codes

    def test_task_intake_path_blocked(self):
        """services/task_intake/ path → blocked."""
        request = _valid_request(
            dirty_files=("services/task_intake/src/app.py",),
            allowed_files=("services/task_intake/src/app.py",),
        )
        plan, codes = prepare_git_boundary_plan(request)
        assert REASON_FORBIDDEN_PATH in codes

    def test_roadmap_blocked(self):
        """ROADMAP.md → blocked."""
        request = _valid_request(
            dirty_files=("ROADMAP.md",),
            allowed_files=("ROADMAP.md",),
        )
        plan, codes = prepare_git_boundary_plan(request)
        assert REASON_FORBIDDEN_PATH in codes

    def test_pyproject_blocked(self):
        """pyproject.toml → blocked."""
        request = _valid_request(
            dirty_files=("pyproject.toml",),
            allowed_files=("pyproject.toml",),
        )
        plan, codes = prepare_git_boundary_plan(request)
        assert REASON_FORBIDDEN_PATH in codes


# ---------------------------------------------------------------------------
# Blocked empty commit message
# ---------------------------------------------------------------------------


class TestBlockedEmptyCommitMessage:
    def test_empty_commit_message(self):
        """Empty commit_message → blocked."""
        request = _valid_request(commit_message="")
        plan, codes = prepare_git_boundary_plan(request)
        assert REASON_MISSING_COMMIT_MESSAGE in codes


# ---------------------------------------------------------------------------
# Blocked empty PR title
# ---------------------------------------------------------------------------


class TestBlockedEmptyPrTitle:
    def test_empty_pr_title(self):
        """pr_title empty but PR requested → blocked."""
        request = _valid_request(pr_title="")
        plan, codes = prepare_git_boundary_plan(request)
        assert REASON_MISSING_PR_TITLE in codes


# ---------------------------------------------------------------------------
# Command specs are argv
# ---------------------------------------------------------------------------


class TestCommandSpecsAreArgv:
    def test_all_specs_use_argv(self):
        """All command specs use tuple argv, not shell strings."""
        request = _valid_request()
        plan, codes = prepare_git_boundary_plan(request)
        for spec in plan.command_specs:
            assert isinstance(spec.argv, tuple)
            assert len(spec.argv) > 0
            assert all(isinstance(a, str) for a in spec.argv)


# ---------------------------------------------------------------------------
# Side-effecting flags
# ---------------------------------------------------------------------------


class TestSideEffectingFlags:
    def test_side_effecting_flags(self):
        """commit/push/pr marked side_effecting=true."""
        request = _valid_request()
        plan, codes = prepare_git_boundary_plan(request)
        for spec in plan.command_specs:
            if spec.operation in ("git_commit", "git_push", "gh_pr_create"):
                assert spec.side_effecting is True
            else:
                assert spec.side_effecting is False


# ---------------------------------------------------------------------------
# Git add includes allowed files
# ---------------------------------------------------------------------------


class TestGitAddIncludesAllowedFiles:
    def test_git_add_includes_files_to_stage(self):
        """git add includes only files_to_stage."""
        request = _valid_request()
        plan, codes = prepare_git_boundary_plan(request)
        add_spec = [s for s in plan.command_specs if s.operation == "git_add"]
        assert len(add_spec) == 1
        # argv should include files_to_stage after "git", "add", "--"
        for f in request.files_to_stage:
            assert f in add_spec[0].argv


# ---------------------------------------------------------------------------
# Gh pr create included only with title
# ---------------------------------------------------------------------------


class TestGhPrCreateIncludedOnlyWithTitle:
    def test_pr_create_included_with_title(self):
        """PR command present when pr_title is set."""
        request = _valid_request(pr_title="Test PR", pr_body="Body")
        plan, codes = prepare_git_boundary_plan(request)
        operations = [s.operation for s in plan.command_specs]
        assert "gh_pr_create" in operations

    def test_pr_create_not_included_without_title(self):
        """PR command absent when pr_title is None."""
        request = _valid_request(pr_title=None, pr_body=None)
        plan, codes = prepare_git_boundary_plan(request)
        operations = [s.operation for s in plan.command_specs]
        assert "gh_pr_create" not in operations


# ---------------------------------------------------------------------------
# Dry run / no executor
# ---------------------------------------------------------------------------


class TestDryRunSkipsExecution:
    def test_no_executor_skips_execution(self):
        """No executor → approved but not executed."""
        request = _valid_request()
        plan, codes = prepare_git_boundary_plan(request)
        result = execute_git_boundary_plan(request, plan, executor=None)
        assert result.status == GitBoundaryStatus.APPROVED.value
        assert result.execution_attempted is False
        assert len(result.execution_results) == 0


# ---------------------------------------------------------------------------
# Injected fake executor
# ---------------------------------------------------------------------------


class TestInjectedFakeExecutor:
    def test_fake_executor_records_specs(self):
        """Fake executor receives command specs."""
        received_specs: list[GitCommandSpec] = []

        def recording_executor(spec: GitCommandSpec) -> dict[str, Any]:
            received_specs.append(spec)
            return {"exit_code": 0, "stdout": "ok", "stderr": ""}

        request = _valid_request()
        plan, codes = prepare_git_boundary_plan(request)
        result = execute_git_boundary_plan(request, plan, executor=recording_executor)
        assert result.status == GitBoundaryStatus.APPROVED.value
        assert result.execution_attempted is True
        assert len(received_specs) == plan.command_count


# ---------------------------------------------------------------------------
# Execution results recorded
# ---------------------------------------------------------------------------


class TestExecutionResultsRecorded:
    def test_execution_results_recorded(self):
        """Execution results include operation, exit_code."""
        request = _valid_request()
        plan, codes = prepare_git_boundary_plan(request)
        result = execute_git_boundary_plan(request, plan, executor=_fake_executor)
        assert result.execution_attempted is True
        assert len(result.execution_results) == plan.command_count
        for res in result.execution_results:
            assert "operation" in res
            assert "exit_code" in res


# ---------------------------------------------------------------------------
# Execution failure
# ---------------------------------------------------------------------------


class TestExecutionFailure:
    def test_execution_failure(self):
        """Executor returns non-zero → failed."""
        request = _valid_request()
        plan, codes = prepare_git_boundary_plan(request)
        result = execute_git_boundary_plan(request, plan, executor=_fake_failing_executor)
        assert result.status == GitBoundaryStatus.FAILED.value
        assert REASON_EXECUTION_FAILED in result.reason_codes


# ---------------------------------------------------------------------------
# No subprocess.run/os.system/shell=True
# ---------------------------------------------------------------------------


class TestNoSubprocessRunOsSystemShell:
    def test_no_subprocess_run(self):
        """Module does not use subprocess.run/os.system/shell=True."""
        from runner.git_boundary import prepare_git_boundary_plan, execute_git_boundary_plan
        source = inspect.getsource(prepare_git_boundary_plan) + inspect.getsource(execute_git_boundary_plan)
        assert "subprocess.run" not in source
        assert "os.system" not in source
        assert "shell=True" not in source


# ---------------------------------------------------------------------------
# No Docker
# ---------------------------------------------------------------------------


class TestNoDocker:
    def test_no_docker(self):
        """Module does not reference docker."""
        from runner.git_boundary import prepare_git_boundary_plan, execute_git_boundary_plan
        source = inspect.getsource(prepare_git_boundary_plan) + inspect.getsource(execute_git_boundary_plan)
        assert "docker" not in source


# ---------------------------------------------------------------------------
# No .ariadne/ residue
# ---------------------------------------------------------------------------


class TestNoAriadneResidue:
    def test_no_ariadne_residue(self):
        """Uses tmp_path, not .ariadne/."""
        request = _valid_request()
        plan, codes = prepare_git_boundary_plan(request)
        result = execute_git_boundary_plan(request, plan, executor=_fake_executor)
        assert result.status == GitBoundaryStatus.APPROVED.value
        assert not Path(".ariadne").exists()


# ---------------------------------------------------------------------------
# No pipeline modified
# ---------------------------------------------------------------------------


class TestNoPipelineModified:
    def test_no_pipeline_import(self):
        """Module does not import pipeline_runner."""
        import inspect
        from runner.git_boundary import prepare_git_boundary_plan
        source = inspect.getsource(prepare_git_boundary_plan)
        assert "pipeline_runner" not in source


# ---------------------------------------------------------------------------
# Deterministic repeats
# ---------------------------------------------------------------------------


class TestDeterministicRepeats:
    def test_deterministic_repeats(self):
        """Same inputs → same output."""
        request = _valid_request()
        plan1, codes1 = prepare_git_boundary_plan(request)
        plan2, codes2 = prepare_git_boundary_plan(request)
        assert plan1.command_count == plan2.command_count
        assert plan1.pipeline_eligible == plan2.pipeline_eligible
        assert plan1.dirty_tree_valid == plan2.dirty_tree_valid
        assert codes1 == codes2

        result1 = execute_git_boundary_plan(request, plan1, executor=_fake_executor, clock_provider=_clock)
        result2 = execute_git_boundary_plan(request, plan2, executor=_fake_executor, clock_provider=_clock)
        assert result1.status == result2.status
        assert result1.execution_attempted == result2.execution_attempted


# ---------------------------------------------------------------------------
# Forbidden path helper
# ---------------------------------------------------------------------------


class TestForbiddenPathHelper:
    def test_forbidden_paths(self):
        """_is_forbidden_path correctly identifies forbidden paths."""
        assert _is_forbidden_path("agents/coder.yml") is True
        assert _is_forbidden_path("schemas/schema.yml") is True
        assert _is_forbidden_path("services/task_intake/src/app.py") is True
        assert _is_forbidden_path(".project-memory/post-0100/strategic-direction/agent-manifest.md") is True
        assert _is_forbidden_path("ROADMAP.md") is True
        assert _is_forbidden_path("docs/adr/0011.md") is True
        assert _is_forbidden_path("pyproject.toml") is True
        assert _is_forbidden_path("package.json") is True
        assert _is_forbidden_path("Makefile") is True

    def test_allowed_paths(self):
        """_is_forbidden_path correctly allows non-forbidden paths."""
        assert _is_forbidden_path("services/runner/src/runner/git_boundary.py") is False
        assert _is_forbidden_path("services/runner/tests/test_git_boundary.py") is False
        assert _is_forbidden_path(".project-memory/pr/0128/PLAN.md") is False


# ---------------------------------------------------------------------------
# Product name
# ---------------------------------------------------------------------------


class TestProductName:
    def test_module_docstring_contains_ariadne(self):
        """Module docstring contains 'Ariadne'."""
        import runner.git_boundary
        doc = runner.git_boundary.__doc__ or ""
        assert "Ariadne" in doc


# ---------------------------------------------------------------------------
# No forbidden legacy names
# ---------------------------------------------------------------------------


class TestNoForbiddenNames:
    def test_no_forbidden_strings(self):
        """Source contains no forbidden legacy names."""
        from runner.git_boundary import prepare_git_boundary_plan
        source = inspect.getsource(prepare_git_boundary_plan)
        forbidden = [
            "water_meter", "water-meter", "Broken Clock", "broken_clock",
            "daily-consumption", ".grace", "@grace-", "old Flask",
        ]
        for f in forbidden:
            assert f not in source, f"Forbidden string found: {f!r}"
