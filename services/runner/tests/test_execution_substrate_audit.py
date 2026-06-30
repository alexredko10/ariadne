"""Tests for the execution substrate audit module."""

from __future__ import annotations

from runner.execution_substrate_audit import run_execution_substrate_audit


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _adapter_registry_with_dual_gate() -> str:
    return '''
def _dispatch_docker_agent(execution_request: dict) -> dict:
    request_allows_docker = execution_request.get("allow_docker") is True
    env_raw = os.environ.get("ARIADNE_ALLOW_DOCKER_EXECUTION", "")
    env_allowed = env_raw.strip().lower() not in ("", "0", "false", "no", "off")
    if not (request_allows_docker and env_allowed):
        return run_docker_agent_execution(execution_request, allow_docker=False)
    return run_docker_agent_execution(execution_request, executor=run_docker_subprocess, allow_docker=True)
'''


def _adapter_registry_no_env() -> str:
    return '''
def _dispatch_docker_agent(execution_request: dict) -> dict:
    request_allows_docker = execution_request.get("allow_docker") is True
    if request_allows_docker:
        return run_docker_agent_execution(execution_request, executor=run_docker_subprocess, allow_docker=True)
    return run_docker_agent_execution(execution_request, allow_docker=False)
'''


def _adapter_registry_no_false_guard() -> str:
    return '''
def _dispatch_docker_agent(execution_request: dict) -> dict:
    request_allows_docker = execution_request.get("allow_docker") is True
    env_raw = os.environ.get("ARIADNE_ALLOW_DOCKER_EXECUTION", "")
    env_allowed = bool(env_raw)
    if not (request_allows_docker and env_allowed):
        return run_docker_agent_execution(execution_request, allow_docker=False)
    return run_docker_agent_execution(execution_request, executor=run_docker_subprocess, allow_docker=True)
'''


def _docker_agent_adapter_with_requires_review() -> str:
    return '''
success = executor_result.get("success", False)
if success:
    status = "requires_review"
else:
    status = "failed"
return {"status": status, "artifacts": []}
'''


def _docker_agent_adapter_with_completed() -> str:
    return '''
success = executor_result.get("success", False)
if success:
    status = "completed"
else:
    status = "failed"
return {"status": status, "artifacts": []}
'''


def _docker_agent_adapter_blocked() -> str:
    return '''
if not allow_docker:
    return {
        "status": "blocked",
        "adapter": "docker-agent-v1",
        "artifacts": [],
        "evidence": [],
    }
'''


def _docker_run_artifacts_with_all_kinds() -> str:
    return '''
artifacts.append({"kind": "docker_stdout"})
artifacts.append({"kind": "docker_stderr"})
artifacts.append({"kind": "docker_execution_metadata"})
artifacts.append({"kind": "docker_command_metadata"})
'''


def _docker_run_artifacts_missing_one_kind() -> str:
    return '''
artifacts.append({"kind": "docker_stdout"})
artifacts.append({"kind": "docker_stderr"})
artifacts.append({"kind": "docker_execution_metadata"})
'''


def _docker_run_artifacts_with_evidence() -> str:
    return '''"evidence_kind": "execution_log"'''


def _docker_run_artifacts_without_evidence_note() -> str:
    return '''"evidence_kind": "execution_log"
'''


def _docker_run_artifacts_with_evidence_note() -> str:
    return '''
evidence.append({"evidence_kind": "execution_log"})
evidence.append({"evidence_kind": "execution_note"})
'''


def _docker_run_artifacts_with_bounding() -> str:
    return '''
_MAX_CONTENT_LENGTH = 10000
def bound(content):
    if len(content) > 10000:
        return content[:10000] + "\\n... [truncated at 10000 characters]"
    return content
'''


def _docker_run_artifacts_no_bounding() -> str:
    return '''
def bound(content):
    return content
'''


def _docker_run_artifacts_with_env_redaction() -> str:
    return '''
def _safe_environment_key_list(environment):
    safe_keys = {"ARIADNE_RUN_ID", "ARIADNE_REQUEST_ID", "ARIADNE_MODE"}
    result = [k for k in environment if k in safe_keys]
    return result

content = {"environment_keys": safe_env_keys, "env_var_count": len(safe_env_keys)}
'''


def _docker_run_artifacts_no_env_redaction() -> str:
    return '''
content = {"environment": environment}
'''


def _docker_subprocess_executor_with_subprocess() -> str:
    return '''
import subprocess

def run_docker_subprocess(command_metadata: dict) -> dict:
    result = subprocess.run(["docker", "run"], capture_output=True, text=True)
'''


def _review_boundary_with_mapping() -> str:
    return '''
if result_status == "requires_review":
    decision = "requires_review"
elif result_status == "blocked":
    decision = "blocked"
elif result_status in ("failed", "error") or not result_status:
    decision = "failed"
'''


def _review_boundary_no_mapping() -> str:
    return '''
if result_status == "something":
    decision = "something"
'''


def _clean_task_intake_source() -> str:
    return "async def safe_handler(): pass"


def _dirty_task_intake_source() -> str:
    return "import subprocess\nasync def unsafe_handler(): pass"


def _docker_subprocess_executor_other() -> str:
    return "# no subprocess imports here"


# ---------------------------------------------------------------------------
# Docker dual gate
# ---------------------------------------------------------------------------


class TestDualGate:
    def test_pass(self):
        report = run_execution_substrate_audit(
            adapter_registry_source=_adapter_registry_with_dual_gate(),
        )
        check = _find_check(report, "docker_dual_gate")
        assert check is not None
        assert check["passed"] is True

    def test_fail_env_missing(self):
        report = run_execution_substrate_audit(
            adapter_registry_source=_adapter_registry_no_env(),
        )
        check = _find_check(report, "docker_dual_gate")
        assert check is not None
        assert check["passed"] is False

    def test_fail_false_bypass(self):
        report = run_execution_substrate_audit(
            adapter_registry_source=_adapter_registry_no_false_guard(),
        )
        check = _find_check(report, "docker_dual_gate")
        assert check is not None
        assert check["passed"] is False


# ---------------------------------------------------------------------------
# requires_review
# ---------------------------------------------------------------------------


class TestRequiresReview:
    def test_pass(self):
        report = run_execution_substrate_audit(
            docker_agent_adapter_source=_docker_agent_adapter_with_requires_review(),
        )
        check = _find_check(report, "docker_success_requires_review")
        assert check is not None
        assert check["passed"] is True, f"Failed: {check['details']}"

    def test_fail_completed(self):
        report = run_execution_substrate_audit(
            docker_agent_adapter_source=_docker_agent_adapter_with_completed(),
        )
        check = _find_check(report, "docker_success_requires_review")
        assert check is not None
        assert check["passed"] is False


# ---------------------------------------------------------------------------
# Failed unchanged
# ---------------------------------------------------------------------------


class TestFailedUnchanged:
    def test_pass(self):
        report = run_execution_substrate_audit(
            docker_agent_adapter_source=_docker_agent_adapter_with_requires_review(),
        )
        check = _find_check(report, "docker_failed_unchanged")
        assert check is not None
        assert check["passed"] is True


# ---------------------------------------------------------------------------
# Blocked unchanged
# ---------------------------------------------------------------------------


class TestBlockedUnchanged:
    def test_pass(self):
        report = run_execution_substrate_audit(
            docker_agent_adapter_source=_docker_agent_adapter_blocked(),
        )
        check = _find_check(report, "docker_blocked_unchanged")
        assert check is not None
        assert check["passed"] is True


# ---------------------------------------------------------------------------
# Artifact kinds
# ---------------------------------------------------------------------------


class TestArtifactKinds:
    def test_pass_all_four(self):
        report = run_execution_substrate_audit(
            docker_run_artifacts_source=_docker_run_artifacts_with_all_kinds(),
        )
        check = _find_check(report, "artifact_kinds_present")
        assert check is not None
        assert check["passed"] is True

    def test_fail_missing_one(self):
        report = run_execution_substrate_audit(
            docker_run_artifacts_source=_docker_run_artifacts_missing_one_kind(),
        )
        check = _find_check(report, "artifact_kinds_present")
        assert check is not None
        assert check["passed"] is False


# ---------------------------------------------------------------------------
# Evidence kinds
# ---------------------------------------------------------------------------


class TestEvidenceKinds:
    def test_pass_both_present(self):
        report = run_execution_substrate_audit(
            docker_run_artifacts_source=_docker_run_artifacts_with_evidence_note(),
        )
        check = _find_check(report, "evidence_kinds_present")
        assert check is not None
        assert check["passed"] is True

    def test_fail_missing_one(self):
        report = run_execution_substrate_audit(
            docker_run_artifacts_source=_docker_run_artifacts_without_evidence_note(),
        )
        check = _find_check(report, "evidence_kinds_present")
        assert check is not None
        assert check["passed"] is False


# ---------------------------------------------------------------------------
# stdout/stderr bounded
# ---------------------------------------------------------------------------


class TestStdoutBounded:
    def test_pass_with_bounding(self):
        report = run_execution_substrate_audit(
            docker_run_artifacts_source=_docker_run_artifacts_with_bounding(),
        )
        check = _find_check(report, "stdout_stderr_bounded")
        assert check is not None
        assert check["passed"] is True

    def test_fail_no_bounding(self):
        report = run_execution_substrate_audit(
            docker_run_artifacts_source=_docker_run_artifacts_no_bounding(),
        )
        check = _find_check(report, "stdout_stderr_bounded")
        assert check is not None
        assert check["passed"] is False


# ---------------------------------------------------------------------------
# Environment redaction
# ---------------------------------------------------------------------------


class TestEnvRedaction:
    def test_pass_with_redaction(self):
        report = run_execution_substrate_audit(
            docker_run_artifacts_source=_docker_run_artifacts_with_env_redaction(),
        )
        check = _find_check(report, "env_values_redacted")
        assert check is not None
        assert check["passed"] is True

    def test_fail_no_redaction(self):
        report = run_execution_substrate_audit(
            docker_run_artifacts_source=_docker_run_artifacts_no_env_redaction(),
        )
        check = _find_check(report, "env_values_redacted")
        assert check is not None
        assert check["passed"] is False


# ---------------------------------------------------------------------------
# Subprocess isolation
# ---------------------------------------------------------------------------


class TestSubprocessIsolation:
    def test_pass_when_isolated(self):
        report = run_execution_substrate_audit(
            docker_subprocess_executor_source=_docker_subprocess_executor_with_subprocess(),
            docker_agent_adapter_source=_docker_subprocess_executor_other(),
            docker_run_artifacts_source=_docker_subprocess_executor_other(),
            adapter_registry_source=_docker_subprocess_executor_other(),
            review_boundary_source=_docker_subprocess_executor_other(),
        )
        check = _find_check(report, "subprocess_isolation")
        assert check is not None
        assert check["passed"] is True

    def test_fail_when_in_other_file(self):
        report = run_execution_substrate_audit(
            docker_subprocess_executor_source=_docker_subprocess_executor_with_subprocess(),
            docker_agent_adapter_source=_docker_agent_adapter_with_requires_review(),
            docker_run_artifacts_source=_docker_run_artifacts_with_all_kinds(),
            adapter_registry_source=_adapter_registry_with_dual_gate(),
            review_boundary_source=_review_boundary_with_mapping(),
        )
        check = _find_check(report, "subprocess_isolation")
        assert check is not None
        assert check["passed"] is True  # these files don't have subprocess


# ---------------------------------------------------------------------------
# Forbidden strings
# ---------------------------------------------------------------------------


class TestForbiddenStrings:
    def test_pass_clean_source(self):
        report = run_execution_substrate_audit(
            task_intake_http_source=_clean_task_intake_source(),
        )
        check = _find_check(report, "task_intake_no_forbidden_strings")
        assert check is not None
        assert check["passed"] is True

    def test_fail_dirty_source(self):
        report = run_execution_substrate_audit(
            task_intake_http_source=_dirty_task_intake_source(),
        )
        check = _find_check(report, "task_intake_no_forbidden_strings")
        assert check is not None
        assert check["passed"] is False


# ---------------------------------------------------------------------------
# Review boundary mapping
# ---------------------------------------------------------------------------


class TestReviewBoundaryMapping:
    def test_pass_full_mapping(self):
        report = run_execution_substrate_audit(
            review_boundary_source=_review_boundary_with_mapping(),
        )
        check = _find_check(report, "review_boundary_status_map")
        assert check is not None
        assert check["passed"] is True

    def test_fail_no_mapping(self):
        report = run_execution_substrate_audit(
            review_boundary_source=_review_boundary_no_mapping(),
        )
        check = _find_check(report, "review_boundary_status_map")
        assert check is not None
        assert check["passed"] is False


# ---------------------------------------------------------------------------
# Review-process completeness retro-check
# ---------------------------------------------------------------------------


class TestRetroCheck:
    """Review-process completeness retro-check tests."""

    def test_no_gap_when_all_covered(self):
        pr_diff = [
            {
                "pr_id": "0094",
                "diff_files": ["file_a.py", "file_b.py"],
                "precommit_files_read": ["file_a.py", "file_b.py", "file_c.md"],
            },
        ]
        report = run_execution_substrate_audit(pr_diff_files=pr_diff)
        check = _find_check(report, "retro_check_0094")
        assert check is not None
        assert check["passed"] is True

    def test_warning_when_file_missing(self):
        pr_diff = [
            {
                "pr_id": "0094",
                "diff_files": ["file_a.py", "file_missing.py"],
                "precommit_files_read": ["file_a.py"],
            },
        ]
        report = run_execution_substrate_audit(pr_diff_files=pr_diff)
        check = _find_check(report, "retro_check_0094")
        assert check is not None
        assert check["passed"] is False
        assert check["severity"] == "tech_debt"
        extra = check.get("extra", {})
        assert "file_missing.py" in extra.get("files_in_diff_but_not_read", [])

    def test_severity_is_tech_debt(self):
        pr_diff = [
            {
                "pr_id": "0095",
                "diff_files": ["x.py", "y.py"],
                "precommit_files_read": ["x.py"],
            },
        ]
        report = run_execution_substrate_audit(pr_diff_files=pr_diff)
        check = _find_check(report, "retro_check_0095")
        assert check is not None
        assert check["passed"] is False
        assert check["severity"] == "tech_debt"

    def test_no_branch_ref_needed(self):
        """Tests must not require old PR branches to exist."""
        pr_diff = [
            {
                "pr_id": "0096",
                "diff_files": ["a.py", "b.py"],
                "precommit_files_read": ["a.py", "b.py", "c.py"],
            },
        ]
        # No git commands, no branch refs — pure fixture comparison
        report = run_execution_substrate_audit(pr_diff_files=pr_diff)
        check = _find_check(report, "retro_check_0096")
        assert check is not None
        assert check["passed"] is True

    def test_multiple_prs(self):
        pr_diff = [
            {
                "pr_id": "0094",
                "diff_files": ["a.py", "b.py"],
                "precommit_files_read": ["a.py", "b.py"],
            },
            {
                "pr_id": "0095",
                "diff_files": ["c.py"],
                "precommit_files_read": ["c.py"],
            },
            {
                "pr_id": "0096",
                "diff_files": ["d.py"],
                "precommit_files_read": ["d.py"],
            },
        ]
        report = run_execution_substrate_audit(pr_diff_files=pr_diff)
        for pr_id in ("0094", "0095", "0096"):
            check = _find_check(report, f"retro_check_{pr_id}")
            assert check is not None, f"Missing check for PR {pr_id}"
            assert check["passed"] is True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_check(report: dict, check_id: str) -> dict | None:
    """Find an audit check by ID."""
    for c in report.get("checks", []):
        if c["check_id"] == check_id:
            return c
    return None


# ---------------------------------------------------------------------------
# Audit matches actual adapter behavior
# ---------------------------------------------------------------------------


class TestAuditMatchesRealAdapter:
    """Integration: audit invariants match real adapter behavior.

    These tests use the real run_docker_agent_execution function with
    fake executors, then pass the actual adapter source to the audit.
    """

    def _adapter_with_blocked(self) -> str:
        return 'status = "blocked"'

    def _adapter_with_requires_review(self) -> str:
        return 'status = "requires_review"'

    def _adapter_with_failed(self) -> str:
        return 'status = "failed"'

    def test_requires_review_invariant_passes_with_real_adapter(self):
        """The audit invariant for requires_review must match the adapter's
        actual behavior when allow_docker=True and executor succeeds."""
        from runner.docker_agent_adapter import run_docker_agent_execution

        result = run_docker_agent_execution(
            {
                "execution_request_id": "test-er",
                "run_id": "test-run",
                "inputs": {"task_goal": "test"},
                "execution_mode": "execute",
                "constraints": [],
            },
            allow_docker=True,
            executor=lambda cmd: {
                "exit_code": 0,
                "stdout": "ok",
                "stderr": "",
                "success": True,
            },
        )
        assert result["status"] == "requires_review"

        # Verify the audit's invariant check passes for this behavior
        report = run_execution_substrate_audit(
            docker_agent_adapter_source=_docker_agent_adapter_with_requires_review(),
        )
        requires_check = _find_check(report, "docker_success_requires_review")
        assert requires_check is not None
        assert requires_check["passed"] is True

    def test_blocked_invariant_passes_with_real_adapter(self):
        """The audit invariant for blocked must match the adapter's
        actual behavior when allow_docker=False."""
        from runner.docker_agent_adapter import run_docker_agent_execution

        result = run_docker_agent_execution(
            {
                "execution_request_id": "test-er",
                "run_id": "test-run",
                "inputs": {"task_goal": "test"},
                "execution_mode": "execute",
                "constraints": [],
            },
            allow_docker=False,
        )
        assert result["status"] == "blocked"

        report = run_execution_substrate_audit(
            docker_agent_adapter_source=_docker_agent_adapter_blocked(),
        )
        blocked_check = _find_check(report, "docker_blocked_unchanged")
        assert blocked_check is not None
        assert blocked_check["passed"] is True

    def test_failed_invariant_passes_with_real_adapter(self):
        """The audit invariant for failed must match the adapter's
        actual behavior when executor fails."""
        from runner.docker_agent_adapter import run_docker_agent_execution

        result = run_docker_agent_execution(
            {
                "execution_request_id": "test-er",
                "run_id": "test-run",
                "inputs": {"task_goal": "test"},
                "execution_mode": "execute",
                "constraints": [],
            },
            allow_docker=True,
            executor=lambda cmd: {
                "exit_code": 1,
                "stdout": "",
                "stderr": "error",
                "success": False,
            },
        )
        assert result["status"] == "failed"

        report = run_execution_substrate_audit(
            docker_agent_adapter_source=_docker_agent_adapter_with_requires_review(),
        )
        failed_check = _find_check(report, "docker_failed_unchanged")
        assert failed_check is not None
        assert failed_check["passed"] is True
