"""
Mock Coder — sandbox-only proof harness.

This module demonstrates that agent-like writes are confined to a
sandbox/worktree area and cannot mutate the canonical repository.

The implementation is a proof harness, not a real LLM coder.
"""

from __future__ import annotations

import dataclasses
import os
from pathlib import Path


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class WriteOutcome(str):
    """Result status of a single intended write."""

    SANDBOX_WRITE_PERFORMED = "sandbox_write_performed"
    SANDBOX_WRITE_REFUSED = "sandbox_write_refused"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class SandboxWrite:
    """A successful sandbox write."""

    target: str  # repo-relative POSIX path
    full_path: str  # resolved sandbox path


@dataclasses.dataclass(frozen=True)
class SandboxViolation:
    """A refused write with a structured reason."""

    target: str  # the intended write target as provided
    reason: str  # human-readable explanation


@dataclasses.dataclass(frozen=True)
class MockCoderRequest:
    """Describes a set of intended sandbox writes."""

    sandbox_root: str  # absolute POSIX path to the sandbox directory
    intended_writes: tuple[str, ...]  # repo-relative POSIX paths


@dataclasses.dataclass(frozen=True)
class MockCoderResult:
    """Result of executing a MockCoderRequest."""

    writes: tuple[SandboxWrite, ...] = ()
    violations: tuple[SandboxViolation, ...] = ()


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class MockCoderError(ValueError):
    """Raised when the MockCoder receives an invalid request."""


# ---------------------------------------------------------------------------
# MockCoder
# ---------------------------------------------------------------------------


class MockCoder:
    """Mock Coder — sandbox-only proof harness.

    Accepts a ``MockCoderRequest`` and performs writes strictly under
    the sandbox root.  Writes that would escape the sandbox are refused
    with structured reasons.  No canonical repository paths are touched.
    """

    @staticmethod
    def execute(request: MockCoderRequest) -> MockCoderResult:
        """Execute the intended writes in *request*.

        Parameters
        ----------
        request
            The intended writes and sandbox root.

        Returns
        -------
        MockCoderResult
            All performed writes and any violations that were refused.

        Raises
        ------
        MockCoderError
            If the sandbox root does not exist or is not a directory.
        """
        sandbox = Path(request.sandbox_root).resolve(strict=False)

        if not sandbox.exists():
            raise MockCoderError(
                f"Sandbox root does not exist: {request.sandbox_root}"
            )
        if not sandbox.is_dir():
            raise MockCoderError(
                f"Sandbox root is not a directory: {request.sandbox_root}"
            )

        writes: list[SandboxWrite] = []
        violations: list[SandboxViolation] = []

        for target in request.intended_writes:
            # --- Refuse: absolute paths ---
            if target.startswith("/"):
                violations.append(
                    SandboxViolation(
                        target=target,
                        reason="absolute path refused — all paths must be repo-relative POSIX",
                    )
                )
                continue

            # --- Refuse: path traversal ---
            if ".." in target.split("/"):
                violations.append(
                    SandboxViolation(
                        target=target,
                        reason="path traversal refused — '..' is not allowed",
                    )
                )
                continue

            # --- Resolve the full path within the sandbox ---
            target_path = (sandbox / target).resolve()

            # --- Refuse: resolve escapes sandbox root ---
            if not str(target_path).startswith(str(sandbox)):
                violations.append(
                    SandboxViolation(
                        target=target,
                        reason=(
                            f"resolved path escapes sandbox root — "
                            f"{target_path} is not under {sandbox}"
                        ),
                    )
                )
                continue

            # --- Refuse: symlink escape (symlink target outside sandbox) ---
            if target_path.is_symlink():
                real = target_path.resolve()
                if not str(real).startswith(str(sandbox)):
                    violations.append(
                        SandboxViolation(
                            target=target,
                            reason=(
                                f"symlink escape refused — "
                                f"{target_path} resolves to {real} outside sandbox"
                            ),
                        )
                    )
                    continue

            # --- Perform the write ---
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(f"MockCoder wrote: {target}\n")

            writes.append(
                SandboxWrite(
                    target=target,
                    full_path=str(target_path),
                )
            )

        return MockCoderResult(
            writes=tuple(writes),
            violations=tuple(violations),
        )
