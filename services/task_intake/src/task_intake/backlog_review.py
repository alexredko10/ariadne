"""
Read-only backlog review adapter for the task_intake HTTP server.

Provides ``BacklogReviewInput`` and ``build_backlog_review_json()``
which consumes the PR 0110 ``build_backlog_surface()`` from the runner
and returns a deterministic JSON-safe dict with ``read_only: true``.

Core principle:
    Ariadne may surface backlog items for human inspection through the
    local HTTP server.  The server must not mutate backlog items,
    archive/reject/accept them, approve gates, edit code, or call
    providers through this layer.
"""

from __future__ import annotations

import dataclasses
from typing import Optional

from runner.backlog_surface import (
    BacklogSurfaceInput,
    BacklogSurfaceStatus,
    build_backlog_surface,
)


# ---------------------------------------------------------------------------
# BacklogReviewInput — input parameters
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class BacklogReviewInput:
    """Input parameters for building a backlog review JSON response."""

    backlog_store_dir: str = ".ariadne/backlog"
    status_filter: Optional[str] = None
    category_filter: Optional[str] = None
    max_items: int = 0  # 0 = unlimited


# ---------------------------------------------------------------------------
# Build backlog review JSON
# ---------------------------------------------------------------------------


def build_backlog_review_json(
    input_data: BacklogReviewInput,
) -> dict:
    """Build a deterministic JSON-safe backlog review response.

    Parameters
    ----------
    input_data:
        Input parameters forwarded to ``build_backlog_surface()``.

    Returns
    -------
    dict
        A JSON-safe dict with keys:
        ``status``, ``read_only``, ``surface`` (when ready/empty),
        or ``status``, ``read_only``, ``reason_codes``, ``details``
        (when rejected).
    """
    # Convert to BacklogSurfaceInput and call the runner surface
    surface_input = BacklogSurfaceInput(
        backlog_store_dir=input_data.backlog_store_dir,
        status_filter=input_data.status_filter,
        category_filter=input_data.category_filter,
        max_items=input_data.max_items,
    )
    surface_result = build_backlog_surface(surface_input)

    # Always include read_only: true
    base: dict = {
        "read_only": True,
    }

    if surface_result.status == BacklogSurfaceStatus.REJECTED:
        base["status"] = "rejected"
        base["reason_codes"] = list(surface_result.reason_codes)
        base["details"] = surface_result.details
        return base

    if surface_result.status == BacklogSurfaceStatus.EMPTY:
        base["status"] = "empty"
        base["surface"] = {
            "items": [],
            "summary": {
                "total": 0,
                "by_status": {
                    "new": 0,
                    "human_review": 0,
                    "archived": 0,
                    "rejected": 0,
                },
                "by_category": {
                    "self_improvement": 0,
                    "continuity_followup": 0,
                    "drift_risk": 0,
                    "validation_gap": 0,
                    "frontend_visibility_gap": 0,
                    "human_review_required": 0,
                },
            },
            "total_count": 0,
            "human_review_required_count": 0,
            "drift_risk_items": [],
            "ready_for_review_items": [],
        }
        return base

    # READY
    view = surface_result.surface_view
    base["status"] = "ready"
    base["surface"] = {
        "items": list(view.items) if view else [],
        "summary": view.summary if view else {},
        "total_count": view.total_count if view else 0,
        "human_review_required_count": view.human_review_required_count if view else 0,
        "drift_risk_items": list(view.drift_risk_items) if view else [],
        "ready_for_review_items": list(view.ready_for_review_items) if view else [],
    }
    return base
