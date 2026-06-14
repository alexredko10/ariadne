"""
Runner typed models.

Standard-library-only dataclasses for run specification, patch representation,
and run artifacts. No external dependencies.
"""

from __future__ import annotations

import dataclasses


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class CommandSpec:
    """A single command to execute inside the sandbox or runner shell."""

    argv: tuple[str, ...]
    cwd: str | None = None
    timeout_seconds: int = 60

    def __post_init__(self) -> None:
        if not self.argv:
            raise ValueError("Command argv must not be empty")
        if self.timeout_seconds < 1:
            raise ValueError(
                f"timeout_seconds must be positive, got {self.timeout_seconds}"
            )


@dataclasses.dataclass(frozen=True)
class RunSpec:
    """Describes a complete run: what to execute and under which constraints.

    Note: ``allowed_write_paths`` are stored as plain strings. Callers should
    validate each path with ``patch.validate_patch_path`` before constructing
    this model.
    """

    run_id: str
    task_id: str
    command: CommandSpec
    allowed_write_paths: tuple[str, ...] = ()
    timeout_seconds: int = 60

    def __post_init__(self) -> None:
        if self.timeout_seconds < 1:
            raise ValueError(
                f"timeout_seconds must be positive, got {self.timeout_seconds}"
            )


@dataclasses.dataclass(frozen=True)
class PatchFile:
    """A single file touched by a diff."""

    path: str
    status: str = "modified"


@dataclasses.dataclass(frozen=True)
class NormalizedPatch:
    """A validated, parsed representation of a diff."""

    text: str
    touched_paths: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True)
class RunResult:
    """Captured output and exit code from a command execution."""

    exit_code: int
    stdout: str
    stderr: str


@dataclasses.dataclass(frozen=True)
class RunArtifact:
    """Complete record of a run, including its result and any patch produced."""

    run_id: str
    task_id: str
    result: RunResult
    normalized_patch: NormalizedPatch
    touched_paths: tuple[str, ...] = ()
    runner_version: str = "0.1.0"
