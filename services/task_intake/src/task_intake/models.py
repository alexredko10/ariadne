"""Task Intake API models — request/response types.

Stdlib only. No web framework dependency.
"""

from __future__ import annotations

import dataclasses
import enum
import hashlib
import re
from typing import Literal


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_PROMPT_LENGTH = 10000
"""Maximum allowed prompt length in characters."""


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class TaskIntakeStatus(str, enum.Enum):
    """Outcome of a task intake request."""

    ACCEPTED = "accepted"
    REJECTED = "rejected"


class TaskIntakeError(str, enum.Enum):
    """Structured error codes for task intake rejection."""

    BLANK_PROMPT = "blank_prompt"
    OVERSIZED_PROMPT = "oversized_prompt"


# ---------------------------------------------------------------------------
# Legacy models (Sprint 0 — used by normalizer)
# ---------------------------------------------------------------------------

# These are preserved for backward compatibility with the Sprint 0 normalizer.
# They will be refactored when the Task Intake API skeleton is completed
# with the new TaskIntakeRequest / TaskIntakeAccepted models.

InputType = Literal["text", "voice", "github_issue", "short_note"]
Mode = Literal["bugfix", "feature", "refactor", "test", "review"]


@dataclasses.dataclass(frozen=True)
class NormalizeRequest:
    raw_input: str
    input_type: InputType = "text"
    repo_id: str | None = None
    branch: str | None = None
    hint_labels: list[str] = dataclasses.field(default_factory=list)
    language: str = "en"


@dataclasses.dataclass(frozen=True)
class TaskDraft:
    draft_id: str
    description: str
    original_input: str
    input_type: InputType
    inferred_mode: Mode
    inferred_domains: list[str]
    inferred_risk_hints: list[str]
    suggested_repo_id: str | None
    mode_confidence: float
    description_quality: str
    warnings: list[str]


# ---------------------------------------------------------------------------
# Task Intake API skeleton models (PR 0027)
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class TaskIntakeRequest:
    """A request to submit a task for intake."""

    prompt: str


@dataclasses.dataclass(frozen=True)
class TaskIntakeAccepted:
    """Response indicating the task was accepted."""

    task_id: str
    status: TaskIntakeStatus = TaskIntakeStatus.ACCEPTED


@dataclasses.dataclass(frozen=True)
class TaskIntakeRejected:
    """Response indicating the task was rejected."""

    reason: str
    error_code: TaskIntakeError | None = None
    status: TaskIntakeStatus = TaskIntakeStatus.REJECTED


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_TASK_ID_SAFE = re.compile(r"^[0-9a-z_]+$")


def _make_task_id(prompt: str) -> str:
    """Generate a deterministic, bounded task id from *prompt*."""
    normalized = prompt.strip().lower()
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return f"task_{digest[:12]}"
