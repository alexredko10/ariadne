"""
ApplyPatch stub + HITL gate for the runner.

This module defines the Apply Gate enforcement layer.  It validates an
ApplyRequest-like object against all contract requirements and returns
a refusal-first stub result.  Actual patch application is NOT implemented.

See PLAN.md for full contract and .project-memory/apply-gate.schema.yml
for the schema this code enforces.
"""

from __future__ import annotations

import dataclasses
import enum
import re
from pathlib import Path


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ApplyStatus(str, enum.Enum):
    """Possible outcomes of an ApplyRequest evaluation."""

    READY_FOR_APPLY = "ready_for_apply"
    REFUSED = "refused"


class ApprovalStatus(str, enum.Enum):
    """Human approval decision."""

    APPROVED = "approved"
    REJECTED = "rejected"
    CHANGES_REQUESTED = "changes_requested"
    WAIVED_VALIDATION = "waived_validation"


class ValidationResult(str, enum.Enum):
    """Outcome of a single validation command."""

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    WAIVED = "waived"


class SnapshotVerifiedBy(str, enum.Enum):
    """Mechanism used to verify snapshot freshness."""

    GIT_INTROSPECTION = "git introspection"
    FILESYSTEM = "filesystem"
    NOT_AVAILABLE = "not available"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class HumanApproval:
    """Human approval metadata for an apply request."""

    status: ApprovalStatus
    approved_by: str
    approval_reason: str
    approved_at: str  # ISO8601 UTC


@dataclasses.dataclass(frozen=True)
class ValidationEntry:
    """A single validation command result."""

    command: str
    result: ValidationResult
    evidence: str = ""


@dataclasses.dataclass(frozen=True)
class ApplyRequest:
    """An ApplyRequest-like object carrying all fields required by the Apply Gate contract.

    This is the runner-local representation.  The canonical schema is
    defined in ``.project-memory/apply-gate.schema.yml``.
    """

    normalized_patch_id: str
    normalized_patch_source: str
    run_record_path: str
    run_id: str
    base_sha: str
    base_sha_source: str
    current_head: str
    snapshot_verified: bool
    snapshot_verified_by: str
    patch_normalized: bool
    scope_approved: bool
    allowed_paths: tuple[str, ...]
    forbidden_paths: tuple[str, ...]
    validation_results: tuple[ValidationEntry, ...]
    human_approval: HumanApproval | None = None
    stale_waiver_note: str | None = None
    validation_waiver_note: str | None = None


@dataclasses.dataclass(frozen=True)
class ApplyDecision:
    """Decision returned by the ApplyGate gate."""

    status: ApplyStatus
    reasons: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ApplyGateError(ValueError):
    """Raised when an ApplyRequest is structurally invalid."""


# ---------------------------------------------------------------------------
# Gate
# ---------------------------------------------------------------------------


class ApplyPatch:
    """ApplyPatch stub — validates an ApplyRequest against the Apply Gate contract.

    This is a **gate/stub**.  It never performs canonical repository writes,
    git actions, Docker commands, or subprocess execution.  Approved requests
    return ``ApplyDecision(status=READY_FOR_APPLY)`` only.
    """

    @staticmethod
    def evaluate(request: ApplyRequest) -> ApplyDecision:
        """Evaluate *request* and return an ApplyDecision.

        The decision is always refuse-first.  All gate checks must pass
        before ``READY_FOR_APPLY`` is returned.
        """
        reasons: list[str] = []

        # Gate check 1: human approval
        if request.human_approval is None:
            reasons.append("human approval is missing")
        elif request.human_approval.status not in (
            ApprovalStatus.APPROVED,
            ApprovalStatus.WAIVED_VALIDATION,
        ):
            reasons.append(
                f"human approval status is {request.human_approval.status.value}, "
                f"expected approved or waived_validation"
            )

        # Gate check 2: normalized patch reference
        if not request.normalized_patch_id:
            reasons.append("normalized_patch_id is missing")
        if not request.normalized_patch_source:
            reasons.append("normalized_patch_source is missing")

        # Gate check 3: run record reference
        if not request.run_record_path:
            reasons.append("run_record_path is missing")
        if not request.run_id:
            reasons.append("run_id is missing")

        # Gate check 4: snapshot verification
        if not request.snapshot_verified:
            reasons.append("snapshot_verified is false")
        if not request.snapshot_verified_by:
            reasons.append("snapshot_verified_by is missing")

        # Gate check 5: base_sha / current_head match (or stale waiver)
        if request.base_sha != request.current_head:
            if request.stale_waiver_note:
                reasons.append(
                    f"base_sha/current_head mismatch but stale waiver provided: "
                    f"{request.stale_waiver_note}"
                )
            else:
                reasons.append(
                    f"base_sha ({request.base_sha}) != current_head "
                    f"({request.current_head}) and no stale waiver"
                )

        # Gate check 6: scope approval
        if not request.scope_approved:
            reasons.append("scope_approved is false")

        # Gate check 7: patch normalization
        if not request.patch_normalized:
            reasons.append("patch_normalized is false")

        # Gate check 8: forbidden paths
        if not request.forbidden_paths:
            reasons.append("forbidden_paths are absent")
        # (individual path validation is delegated to the path policy)

        # Gate check 9: allowed paths
        if not request.allowed_paths:
            reasons.append("allowed_paths are absent")

        # Gate check 10: validation results
        if not request.validation_results:
            reasons.append("validation_results are empty")
        else:
            has_failure = False
            for entry in request.validation_results:
                if entry.result == ValidationResult.FAILED:
                    has_failure = True
            if has_failure:
                if request.validation_waiver_note:
                    reasons.append(
                        f"validation failed but waiver provided: "
                        f"{request.validation_waiver_note}"
                    )
                else:
                    reasons.append(
                        "validation failed and no human waiver present"
                    )

        if reasons:
            return ApplyDecision(status=ApplyStatus.REFUSED, reasons=tuple(reasons))

        return ApplyDecision(status=ApplyStatus.READY_FOR_APPLY)


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def validate_sha256(sha: str) -> None:
    """Raise ``ApplyGateError`` if *sha* is not a valid lowercase hex sha256."""
    if not _SHA256_RE.match(sha):
        raise ApplyGateError(
            f"sha256 must be lowercase 64-char hex, got: {sha!r}"
        )


def validate_repo_relative(path: str) -> None:
    """Raise ``ApplyGateError`` if *path* is not a safe repo-relative POSIX path.

    This is a basic sanity check.  Full path validation should be
    delegated to ``runner.patch.validate_patch_path`` when actual
    patch application is implemented.
    """
    p = Path(path)
    if p.is_absolute():
        raise ApplyGateError(f"path must be repo-relative, got absolute: {path}")
    if ".." in path.split("/"):
        raise ApplyGateError(f"path must not contain traversal: {path}")
