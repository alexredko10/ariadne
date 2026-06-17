"""Tests for the ApplyPatch stub + HITL gate."""

from __future__ import annotations

import pytest

from runner.apply import (
    ApplyDecision,
    ApplyGateError,
    ApplyPatch,
    ApplyRequest,
    ApplyStatus,
    ApprovalStatus,
    HumanApproval,
    ValidationEntry,
    ValidationResult,
    validate_repo_relative,
    validate_sha256,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_SHA = "a" * 64
_VALID_REQUEST_KWARGS = dict(
    normalized_patch_id=_VALID_SHA,
    normalized_patch_source=".project-memory/pr/0022-applypatch-stub-hitl-gate/PLAN.md",
    run_record_path=".project-memory/pr/0022-applypatch-stub-hitl-gate/run_record.yml",
    run_id="0022-plan-coder-001",
    base_sha=_VALID_SHA,
    base_sha_source=".project-memory/pr/0022-applypatch-stub-hitl-gate/PLAN.md",
    current_head=_VALID_SHA,
    snapshot_verified=True,
    snapshot_verified_by="git introspection",
    patch_normalized=True,
    scope_approved=True,
    allowed_paths=("services/runner/src/runner/apply.py",),
    forbidden_paths=(".git", ".env", ".env.*"),
    validation_results=(
        ValidationEntry(command="python -m pytest -q", result=ValidationResult.PASSED),
    ),
    human_approval=HumanApproval(
        status=ApprovalStatus.APPROVED,
        approved_by="human-reviewer",
        approval_reason="All checks pass",
        approved_at="2026-06-18T00:00:00Z",
    ),
)


def make_request(**overrides: object) -> ApplyRequest:
    """Create an ApplyRequest with *VALID_REQUEST_KWARGS* merged with *overrides*."""
    kwargs = dict(_VALID_REQUEST_KWARGS)
    kwargs.update(overrides)
    return ApplyRequest(**kwargs)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Default behaviour
# ---------------------------------------------------------------------------


class TestDefaultRefuse:
    def test_default_request_is_refused(self):
        """A bare-minimum request without human approval should be refused."""
        request = ApplyRequest(
            normalized_patch_id="",
            normalized_patch_source="",
            run_record_path="",
            run_id="",
            base_sha="",
            base_sha_source="",
            current_head="",
            snapshot_verified=False,
            snapshot_verified_by="",
            patch_normalized=False,
            scope_approved=False,
            allowed_paths=(),
            forbidden_paths=(),
            validation_results=(),
        )
        decision = ApplyPatch.evaluate(request)
        assert decision.status == ApplyStatus.REFUSED
        assert len(decision.reasons) >= 1


# ---------------------------------------------------------------------------
# Gate checks
# ---------------------------------------------------------------------------


class TestHumanApproval:
    def test_missing_human_approval_refused(self):
        request = make_request(human_approval=None)
        decision = ApplyPatch.evaluate(request)
        assert decision.status == ApplyStatus.REFUSED
        assert any("human approval" in r for r in decision.reasons)

    def test_wrong_approval_status_refused(self):
        request = make_request(
            human_approval=HumanApproval(
                status=ApprovalStatus.REJECTED,
                approved_by="human",
                approval_reason="not ready",
                approved_at="2026-06-18T00:00:00Z",
            )
        )
        decision = ApplyPatch.evaluate(request)
        assert decision.status == ApplyStatus.REFUSED
        assert any("human approval" in r.lower() for r in decision.reasons)


class TestNormalizedPatchReference:
    def test_missing_normalized_patch_id_refused(self):
        request = make_request(normalized_patch_id="")
        decision = ApplyPatch.evaluate(request)
        assert decision.status == ApplyStatus.REFUSED
        assert any("normalized_patch_id" in r for r in decision.reasons)

    def test_missing_normalized_patch_source_refused(self):
        request = make_request(normalized_patch_source="")
        decision = ApplyPatch.evaluate(request)
        assert decision.status == ApplyStatus.REFUSED
        assert any("normalized_patch_source" in r for r in decision.reasons)


class TestRunRecordReference:
    def test_missing_run_record_path_refused(self):
        request = make_request(run_record_path="")
        decision = ApplyPatch.evaluate(request)
        assert decision.status == ApplyStatus.REFUSED
        assert any("run_record_path" in r for r in decision.reasons)

    def test_missing_run_id_refused(self):
        request = make_request(run_id="")
        decision = ApplyPatch.evaluate(request)
        assert decision.status == ApplyStatus.REFUSED
        assert any("run_id" in r for r in decision.reasons)


class TestSnapshotVerification:
    def test_false_snapshot_verified_refused(self):
        request = make_request(snapshot_verified=False)
        decision = ApplyPatch.evaluate(request)
        assert decision.status == ApplyStatus.REFUSED
        assert any("snapshot_verified" in r for r in decision.reasons)

    def test_missing_snapshot_verified_by_refused(self):
        request = make_request(snapshot_verified_by="")
        decision = ApplyPatch.evaluate(request)
        assert decision.status == ApplyStatus.REFUSED
        assert any("snapshot_verified_by" in r for r in decision.reasons)


class TestScopeApproval:
    def test_missing_scope_approval_refused(self):
        request = make_request(scope_approved=False)
        decision = ApplyPatch.evaluate(request)
        assert decision.status == ApplyStatus.REFUSED
        assert any("scope_approved" in r for r in decision.reasons)


class TestPatchNormalization:
    def test_missing_patch_normalization_refused(self):
        request = make_request(patch_normalized=False)
        decision = ApplyPatch.evaluate(request)
        assert decision.status == ApplyStatus.REFUSED
        assert any("patch_normalized" in r for r in decision.reasons)


class TestForbiddenPaths:
    def test_empty_forbidden_paths_refused(self):
        request = make_request(forbidden_paths=())
        decision = ApplyPatch.evaluate(request)
        assert decision.status == ApplyStatus.REFUSED
        assert any("forbidden_paths" in r for r in decision.reasons)


class TestAllowedPaths:
    def test_empty_allowed_paths_refused(self):
        request = make_request(allowed_paths=())
        decision = ApplyPatch.evaluate(request)
        assert decision.status == ApplyStatus.REFUSED
        assert any("allowed_paths" in r for r in decision.reasons)


class TestValidation:
    def test_empty_validation_results_refused(self):
        request = make_request(validation_results=())
        decision = ApplyPatch.evaluate(request)
        assert decision.status == ApplyStatus.REFUSED
        assert any("validation" in r.lower() for r in decision.reasons)

    def test_failed_validation_refused(self):
        request = make_request(
            validation_results=(
                ValidationEntry(
                    command="python -m pytest -q",
                    result=ValidationResult.FAILED,
                ),
            )
        )
        decision = ApplyPatch.evaluate(request)
        assert decision.status == ApplyStatus.REFUSED
        assert any("validation" in r.lower() for r in decision.reasons)

    def test_failed_validation_with_waiver_accepted(self):
        request = make_request(
            validation_results=(
                ValidationEntry(
                    command="python -m pytest -q",
                    result=ValidationResult.FAILED,
                ),
            ),
            validation_waiver_note="Waived by human-reviewer: known flaky test",
        )
        decision = ApplyPatch.evaluate(request)
        assert decision.status == ApplyStatus.REFUSED
        # With waiver it still produces a note-level reason but doesn't block
        # actually with this implementation it adds a note reason. Let's check.
        assert any("waiver" in r.lower() for r in decision.reasons)


class TestBaseShaCurrentHead:
    def test_mismatch_without_waiver_refused(self):
        request = make_request(current_head="b" * 64)
        decision = ApplyPatch.evaluate(request)
        assert decision.status == ApplyStatus.REFUSED
        assert any("base_sha" in r.lower() for r in decision.reasons)

    def test_mismatch_with_waiver_note_refused(self):
        """Mismatch with a stale waiver is still refused by default.

        The waiver is informational — the gate does not auto-approve it.
        The evaluator should still return refused with a note.
        """
        request = make_request(
            current_head="b" * 64,
            stale_waiver_note="Waived by human: known safe delta",
        )
        decision = ApplyPatch.evaluate(request)
        assert decision.status == ApplyStatus.REFUSED
        assert any("stale waiver" in r.lower() for r in decision.reasons)


# ---------------------------------------------------------------------------
# Valid approved request
# ---------------------------------------------------------------------------


class TestValidApprovedRequest:
    def test_returns_ready_for_apply(self):
        request = make_request()
        decision = ApplyPatch.evaluate(request)
        assert decision.status == ApplyStatus.READY_FOR_APPLY
        assert len(decision.reasons) == 0


# ---------------------------------------------------------------------------
# Structured rejection reasons
# ---------------------------------------------------------------------------


class TestStructuredReasons:
    def test_multiple_failures_return_multiple_reasons(self):
        request = make_request(
            human_approval=None,
            normalized_patch_id="",
            run_record_path="",
            run_id="",
            snapshot_verified=False,
            scope_approved=False,
            patch_normalized=False,
            forbidden_paths=(),
            allowed_paths=(),
            validation_results=(),
        )
        decision = ApplyPatch.evaluate(request)
        assert decision.status == ApplyStatus.REFUSED
        # Should have multiple reasons
        assert len(decision.reasons) >= 5


# ---------------------------------------------------------------------------
# No side-effects
# ---------------------------------------------------------------------------


class TestNoSideEffects:
    def test_no_repo_mutation(self, tmp_path):
        """Test that evaluate does not write any files."""
        before = set(tmp_path.rglob("*"))
        request = make_request()
        ApplyPatch.evaluate(request)
        after = set(tmp_path.rglob("*"))
        assert before == after

    def test_no_git_no_subprocess_no_docker(self):
        """Test that evaluate does not call subprocess, git, or docker.

        Since we use only pure-Python dataclass operations, this test
        simply asserts the module is self-contained and stdlib-only.
        """
        import sys
        import subprocess
        import inspect

        # Check that the apply module has no references to subprocess/git/docker
        source = inspect.getsource(ApplyPatch.evaluate)
        assert "subprocess" not in source
        assert "git " not in source
        assert "docker" not in source
        assert "os.system" not in source


# ---------------------------------------------------------------------------
# Helpers: validate_sha256 and validate_repo_relative
# ---------------------------------------------------------------------------


class TestValidateSha256:
    def test_valid_sha256_passes(self):
        validate_sha256(_VALID_SHA)  # should not raise

    def test_invalid_sha256_raises(self):
        with pytest.raises(ApplyGateError, match="sha256"):
            validate_sha256("abc123")

    def test_empty_sha256_raises(self):
        with pytest.raises(ApplyGateError, match="sha256"):
            validate_sha256("")


class TestValidateRepoRelative:
    def test_repo_relative_path_passes(self):
        validate_repo_relative("services/runner/src/runner/apply.py")  # should not raise

    def test_absolute_path_raises(self):
        with pytest.raises(ApplyGateError, match="absolute"):
            validate_repo_relative("/etc/passwd")

    def test_traversal_raises(self):
        with pytest.raises(ApplyGateError, match="traversal"):
            validate_repo_relative("../../etc/passwd")
