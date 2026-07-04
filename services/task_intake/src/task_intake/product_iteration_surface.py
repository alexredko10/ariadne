"""
Product iteration session capture surface for Ariadne.

Provides deterministic, testable helpers for browser/session capture
semantics on top of the PR 0117 ``ProductIterationInput`` contract.

The module does not perform network calls, write ``.ariadne``, call
providers, run subprocesses, use Docker, or call git.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import time
from typing import Optional

from task_intake.product_iteration import (
    ProductIterationInput,
    ProductIterationStatus,
    record_product_iteration_signal,
)


# ---------------------------------------------------------------------------
# SessionSurfaceStatus — surface status values
# ---------------------------------------------------------------------------


class SessionSurfaceStatus(str):
    """Status values for session capture surface operations."""

    RECORDED = "recorded"
    REJECTED = "rejected"
    INVALID = "invalid"


# ---------------------------------------------------------------------------
# SessionSurfaceResult — surface operation result
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class SessionSurfaceResult:
    """Result of a session capture surface operation."""

    status: str
    iteration_ref: Optional[str] = None
    reason_codes: tuple[str, ...] = ()
    details: Optional[str] = None


# ---------------------------------------------------------------------------
# Bounds
# ---------------------------------------------------------------------------

_MAX_SCREEN_TIME_SECONDS = 86400  # 24 hours
_MAX_ACTIVE_TIME_SECONDS = 86400
_MAX_IDLE_TIME_SECONDS = 86400
_MAX_HUMAN_NOTE_LENGTH = 5000
_MAX_REF_LENGTH = 200
_MAX_REFS_COUNT = 100


# ---------------------------------------------------------------------------
# Session ref generation
# ---------------------------------------------------------------------------


def generate_session_ref() -> str:
    """Generate a deterministic session ref from current monotonic time.

    Returns
    -------
    str
        A 16-character hex string derived from monotonic time.
    """
    raw = str(time.monotonic()).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def normalize_session_ref(session_ref: str) -> str:
    """Normalize a session ref to a safe bounded string.

    Parameters
    ----------
    session_ref:
        Raw session ref input.

    Returns
    -------
    str
        Normalized session ref (first 64 chars, alphanumeric + hyphen).
    """
    safe = "".join(c for c in session_ref if c.isalnum() or c in "-_")
    return safe[:64]


# ---------------------------------------------------------------------------
# Bounded screen-time / active-time / idle-time
# ---------------------------------------------------------------------------


def bounded_screen_time(seconds: int) -> int:
    """Clamp screen-time seconds to a bounded range.

    Parameters
    ----------
    seconds:
        Raw screen-time seconds.

    Returns
    -------
    int
        Clamped value (0 to ``_MAX_SCREEN_TIME_SECONDS``).
    """
    if seconds < 0:
        return 0
    if seconds > _MAX_SCREEN_TIME_SECONDS:
        return _MAX_SCREEN_TIME_SECONDS
    return seconds


def bounded_active_time(seconds: int) -> int:
    """Clamp active-time seconds to a bounded range.

    Parameters
    ----------
    seconds:
        Raw active-time seconds.

    Returns
    -------
    int
        Clamped value (0 to ``_MAX_ACTIVE_TIME_SECONDS``).
    """
    if seconds < 0:
        return 0
    if seconds > _MAX_ACTIVE_TIME_SECONDS:
        return _MAX_ACTIVE_TIME_SECONDS
    return seconds


def bounded_idle_time(seconds: int) -> int:
    """Clamp idle-time seconds to a bounded range.

    Parameters
    ----------
    seconds:
        Raw idle-time seconds.

    Returns
    -------
    int
        Clamped value (0 to ``_MAX_IDLE_TIME_SECONDS``).
    """
    if seconds < 0:
        return 0
    if seconds > _MAX_IDLE_TIME_SECONDS:
        return _MAX_IDLE_TIME_SECONDS
    return seconds


# ---------------------------------------------------------------------------
# Ref list normalization
# ---------------------------------------------------------------------------


def normalize_ref_list(refs: tuple[str, ...], max_count: int = _MAX_REFS_COUNT) -> tuple[str, ...]:
    """Normalize a tuple of refs to a bounded, sorted, deduplicated tuple.

    Parameters
    ----------
    refs:
        Raw refs tuple.
    max_count:
        Maximum number of refs to include.

    Returns
    -------
    tuple[str, ...]
        Normalized refs (sorted, deduplicated, bounded).
    """
    seen: set[str] = set()
    result: list[str] = []
    for ref in refs:
        safe = "".join(c for c in ref if c.isalnum() or c in "-_./:")
        safe = safe[:_MAX_REF_LENGTH]
        if safe and safe not in seen:
            seen.add(safe)
            result.append(safe)
    result.sort()
    return tuple(result[:max_count])


# ---------------------------------------------------------------------------
# Human iteration note normalization
# ---------------------------------------------------------------------------


def normalize_human_note(note: str) -> str:
    """Normalize a human iteration note to a bounded string.

    Parameters
    ----------
    note:
        Raw human iteration note.

    Returns
    -------
    str
        Normalized note (trimmed, bounded).
    """
    if not note:
        return ""
    return note.strip()[:_MAX_HUMAN_NOTE_LENGTH]


# ---------------------------------------------------------------------------
# Build ProductIterationInput from surface parameters
# ---------------------------------------------------------------------------


def build_product_iteration_input(
    session_ref: str,
    screen_time_seconds: int = 0,
    active_time_seconds: int = 0,
    idle_time_seconds: int = 0,
    run_refs: tuple[str, ...] = (),
    feedback_refs: tuple[str, ...] = (),
    confusion_refs: tuple[str, ...] = (),
    report_refs: tuple[str, ...] = (),
    decision_trace_refs: tuple[str, ...] = (),
    human_iteration_note: str = "",
    source_surface: str = "task_intake",
    started_at: Optional[str] = None,
    ended_at: Optional[str] = None,
    store_dir: str = ".ariadne/product-iterations",
) -> ProductIterationInput:
    """Build a ``ProductIterationInput`` from surface parameters.

    All time values are bounded.  All ref lists are normalized.
    The human iteration note is trimmed and bounded.

    Parameters
    ----------
    session_ref:
        Session ref (will be normalized).
    screen_time_seconds:
        Screen-time seconds (will be bounded).
    active_time_seconds:
        Active-time seconds (will be bounded).
    idle_time_seconds:
        Idle-time seconds (will be bounded).
    run_refs:
        Run refs (will be normalized).
    feedback_refs:
        Feedback refs (will be normalized).
    confusion_refs:
        Confusion refs (will be normalized).
    report_refs:
        Report refs (will be normalized).
    decision_trace_refs:
        Decision trace refs (will be normalized).
    human_iteration_note:
        Human iteration note (will be trimmed and bounded).
    source_surface:
        Source surface identifier.
    started_at:
        Optional start timestamp.
    ended_at:
        Optional end timestamp.
    store_dir:
        Store directory path.

    Returns
    -------
    ProductIterationInput
        A validated, bounded input ready for ``record_product_iteration_signal()``.
    """
    return ProductIterationInput(
        session_ref=normalize_session_ref(session_ref),
        started_at=started_at,
        ended_at=ended_at,
        screen_time_seconds=bounded_screen_time(screen_time_seconds),
        active_time_seconds=bounded_active_time(active_time_seconds),
        idle_time_seconds=bounded_idle_time(idle_time_seconds),
        run_refs=normalize_ref_list(run_refs),
        feedback_refs=normalize_ref_list(feedback_refs),
        confusion_refs=normalize_ref_list(confusion_refs),
        report_refs=normalize_ref_list(report_refs),
        decision_trace_refs=normalize_ref_list(decision_trace_refs),
        human_iteration_note=normalize_human_note(human_iteration_note),
        source_surface=source_surface,
        product_signal_status="recorded",
        store_dir=store_dir,
    )


# ---------------------------------------------------------------------------
# Record session signal (surface-level convenience)
# ---------------------------------------------------------------------------


def record_session_signal(
    session_ref: str,
    screen_time_seconds: int = 0,
    active_time_seconds: int = 0,
    idle_time_seconds: int = 0,
    run_refs: tuple[str, ...] = (),
    feedback_refs: tuple[str, ...] = (),
    confusion_refs: tuple[str, ...] = (),
    report_refs: tuple[str, ...] = (),
    decision_trace_refs: tuple[str, ...] = (),
    human_iteration_note: str = "",
    source_surface: str = "task_intake",
    started_at: Optional[str] = None,
    ended_at: Optional[str] = None,
    store_dir: str = ".ariadne/product-iterations",
) -> SessionSurfaceResult:
    """Record a session signal through the surface layer.

    Builds a bounded ``ProductIterationInput`` and delegates to
    ``record_product_iteration_signal()``.

    Parameters
    ----------
    Same as ``build_product_iteration_input()``.

    Returns
    -------
    SessionSurfaceResult
        ``status="recorded"`` with ``iteration_ref`` when successful.
        ``status="rejected"`` with ``reason_codes`` when the backend rejects.
        ``status="invalid"`` when the session ref is empty after normalization.
    """
    normalized_ref = normalize_session_ref(session_ref)
    if not normalized_ref:
        return SessionSurfaceResult(
            status=SessionSurfaceStatus.INVALID,
            reason_codes=("empty_session_ref",),
            details="Session ref is empty after normalization.",
        )

    inp = build_product_iteration_input(
        session_ref=session_ref,
        screen_time_seconds=screen_time_seconds,
        active_time_seconds=active_time_seconds,
        idle_time_seconds=idle_time_seconds,
        run_refs=run_refs,
        feedback_refs=feedback_refs,
        confusion_refs=confusion_refs,
        report_refs=report_refs,
        decision_trace_refs=decision_trace_refs,
        human_iteration_note=human_iteration_note,
        source_surface=source_surface,
        started_at=started_at,
        ended_at=ended_at,
        store_dir=store_dir,
    )

    result = record_product_iteration_signal(inp)

    if result.status == ProductIterationStatus.RECORDED:
        return SessionSurfaceResult(
            status=SessionSurfaceStatus.RECORDED,
            iteration_ref=result.iteration_ref,
        )

    return SessionSurfaceResult(
        status=SessionSurfaceStatus.REJECTED,
        reason_codes=tuple(result.reason_codes),
        details=result.details,
    )
