"""
Read-only self-improvement backlog surfacing layer for Ariadne.

Provides ``BacklogSurfaceInput``, ``BacklogSurfaceView``,
``BacklogSurfaceResult``, ``BacklogSurfaceStatus``, stable reason codes,
and ``build_backlog_surface()``.

Core principle:
    Ariadne may surface backlog items for human inspection.
    Ariadne must not mutate backlog items, archive/reject/accept them,
    approve gates, edit code, or call providers through this layer.
"""

from __future__ import annotations

import dataclasses
import enum
import json
import os
from typing import Optional

from .improvement_backlog import (
    BacklogItem,
    BacklogStatus,
    list_backlog,
    REASON_HIDDEN_REASONING_NOT_ALLOWED,
    REASON_EXTERNAL_URL_ONLY_NOT_ALLOWED,
    REASON_COMMAND_EXECUTION_NOT_ALLOWED,
    REASON_PROVIDER_CALL_NOT_ALLOWED,
    REASON_GIT_MUTATION_NOT_ALLOWED,
    _FORBIDDEN_HIDDEN_REASONING_PATTERNS,
    _FORBIDDEN_ACTION_PATTERNS,
)


# ---------------------------------------------------------------------------
# BacklogSurfaceStatus — surface view status
# ---------------------------------------------------------------------------


class BacklogSurfaceStatus(str, enum.Enum):
    """Status of a backlog surface view."""

    READY = "ready"
    EMPTY = "empty"
    REJECTED = "rejected"


# ---------------------------------------------------------------------------
# BacklogSurfaceInput — input parameters
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class BacklogSurfaceInput:
    """Input parameters for building a backlog surface view."""

    backlog_store_dir: str = ".ariadne/backlog"
    status_filter: Optional[str] = None  # optional: new, human_review, archived, rejected
    category_filter: Optional[str] = None  # optional: self_improvement, continuity_followup, etc.
    max_items: int = 0  # 0 = unlimited


# ---------------------------------------------------------------------------
# BacklogSurfaceView — read-only view object
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class BacklogSurfaceView:
    """A read-only view of the self-improvement backlog."""

    items: tuple[dict, ...]  # Full detail dicts for each item
    summary: dict  # Counts by status and category
    total_count: int
    human_review_required_count: int
    drift_risk_items: tuple[dict, ...]  # Items with drift risks
    ready_for_review_items: tuple[str, ...]  # backlog_item_refs needing human review


# ---------------------------------------------------------------------------
# BacklogSurfaceResult — operation result
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class BacklogSurfaceResult:
    """Result of a backlog surface build operation."""

    status: BacklogSurfaceStatus
    reason_codes: tuple[str, ...] = ()
    surface_view: Optional[BacklogSurfaceView] = None
    details: Optional[str] = None


# ---------------------------------------------------------------------------
# Stable reason codes
# ---------------------------------------------------------------------------

REASON_MISSING_BACKLOG_STORE = "missing_backlog_store"
REASON_BACKLOG_STORE_NOT_DIRECTORY = "backlog_store_not_directory"
REASON_UNBOUNDED_BACKLOG_STORE_PATH = "unbounded_backlog_store_path"
REASON_UNREADABLE_BACKLOG_ITEM = "unreadable_backlog_item"
REASON_MALFORMED_BACKLOG_ITEM_JSON = "malformed_backlog_item_json"
REASON_DUPLICATE_BACKLOG_ITEM_REF = "duplicate_backlog_item_ref"
REASON_UNSUPPORTED_BACKLOG_STATUS = "unsupported_backlog_status"
REASON_MUTATION_NOT_ALLOWED = "mutation_not_allowed"
REASON_ARCHIVE_NOT_ALLOWED = "archive_not_allowed"
REASON_APPROVAL_NOT_ALLOWED = "approval_not_allowed"
REASON_GATE_FINALIZATION_NOT_ALLOWED = "gate_finalization_not_allowed"
REASON_OVERSIZED_BACKLOG_VIEW = "oversized_backlog_view"

# ---------------------------------------------------------------------------
# Forbidden mutation patterns (surface-specific)
# ---------------------------------------------------------------------------

_FORBIDDEN_MUTATION_PATTERNS: tuple[tuple[str, str], ...] = (
    ("archive", REASON_ARCHIVE_NOT_ALLOWED),
    ("reject", REASON_ARCHIVE_NOT_ALLOWED),
    ("accept", REASON_MUTATION_NOT_ALLOWED),
    ("approve", REASON_APPROVAL_NOT_ALLOWED),
    ("finalize", REASON_GATE_FINALIZATION_NOT_ALLOWED),
    ("gate_ready", REASON_APPROVAL_NOT_ALLOWED),
)

# ---------------------------------------------------------------------------
# Bounds
# ---------------------------------------------------------------------------

_MAX_SURFACE_ITEMS = 1000  # hard limit to prevent oversized views


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _check_backlog_store_path(backlog_store_dir: str, codes: list[str]) -> None:
    """Validate backlog store path boundedness and existence."""
    if not backlog_store_dir or backlog_store_dir.strip() == "":
        codes.append(REASON_UNBOUNDED_BACKLOG_STORE_PATH)
        return

    path = backlog_store_dir.strip()

    # Reject paths with parent-directory traversal
    if ".." in path.split("/"):
        codes.append(REASON_UNBOUNDED_BACKLOG_STORE_PATH)
        return

    if not os.path.exists(path):
        codes.append(REASON_MISSING_BACKLOG_STORE)
        return

    if not os.path.isdir(path):
        codes.append(REASON_BACKLOG_STORE_NOT_DIRECTORY)
        return


def _check_hidden_reasoning_in_item(item: BacklogItem, codes: list[str]) -> None:
    """Check for hidden reasoning patterns in item text fields."""
    text_fields = [
        item.next_safe_action,
        item.improvement_category,
    ]
    for text in text_fields:
        for pattern in _FORBIDDEN_HIDDEN_REASONING_PATTERNS:
            if pattern in text:
                codes.append(REASON_HIDDEN_REASONING_NOT_ALLOWED)
                return


def _check_external_url_only_in_item(item: BacklogItem, codes: list[str]) -> None:
    """Check for external URL-only evidence in item."""
    for ref in item.evidence_refs:
        stripped = ref.strip()
        if stripped.startswith("http://") or stripped.startswith("https://"):
            if "\n" not in stripped and " " not in stripped:
                codes.append(REASON_EXTERNAL_URL_ONLY_NOT_ALLOWED)
                return

    for code in item.source_reason_codes:
        stripped = code.strip()
        if stripped.startswith("http://") or stripped.startswith("https://"):
            if "\n" not in stripped and " " not in stripped:
                codes.append(REASON_EXTERNAL_URL_ONLY_NOT_ALLOWED)
                return


def _check_forbidden_actions_in_item(item: BacklogItem, codes: list[str]) -> None:
    """Check for forbidden action patterns in item text fields."""
    text_fields = [
        item.next_safe_action,
        item.improvement_category,
    ]
    for text in text_fields:
        for pattern, reason in _FORBIDDEN_ACTION_PATTERNS:
            if pattern in text:
                codes.append(reason)
                return


def _check_forbidden_mutation_in_item(item: BacklogItem, codes: list[str]) -> None:
    """Check for forbidden mutation patterns in item text fields."""
    text_fields = [
        item.next_safe_action,
        item.improvement_category,
    ]
    for text in text_fields:
        for pattern, reason in _FORBIDDEN_MUTATION_PATTERNS:
            if pattern in text:
                codes.append(reason)
                return


def _check_unsupported_status(item: BacklogItem, codes: list[str]) -> None:
    """Check if item status is a valid BacklogStatus value."""
    try:
        BacklogStatus(item.status)
    except ValueError:
        codes.append(REASON_UNSUPPORTED_BACKLOG_STATUS)


# ---------------------------------------------------------------------------
# Build backlog surface
# ---------------------------------------------------------------------------


def build_backlog_surface(
    input_data: BacklogSurfaceInput,
) -> BacklogSurfaceResult:
    """Build a read-only surface view of the self-improvement backlog.

    Parameters
    ----------
    input_data:
        Input parameters including backlog store path, optional filters,
        and max items limit.

    Returns
    -------
    BacklogSurfaceResult
        ``status="ready"`` with ``surface_view`` when items are loaded.
        ``status="empty"`` when no items match.
        ``status="rejected"`` with ``reason_codes`` when validation fails.
    """
    codes: list[str] = []

    # 1. Validate backlog store path
    _check_backlog_store_path(input_data.backlog_store_dir, codes)

    if codes:
        codes.sort()
        detail_lines = [f"  - {c}" for c in codes]
        details = "Backlog surface rejected:\n" + "\n".join(detail_lines)
        return BacklogSurfaceResult(
            status=BacklogSurfaceStatus.REJECTED,
            reason_codes=tuple(codes),
            details=details,
        )

    # 2. Load items from backlog store
    list_result = list_backlog(
        backlog_store_dir=input_data.backlog_store_dir,
        status_filter=input_data.status_filter,
    )

    if list_result.total_count == 0:
        return BacklogSurfaceResult(
            status=BacklogSurfaceStatus.EMPTY,
            surface_view=BacklogSurfaceView(
                items=(),
                summary={
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
                total_count=0,
                human_review_required_count=0,
                drift_risk_items=(),
                ready_for_review_items=(),
            ),
        )

    # 3. Apply category filter (list_backlog doesn't support category filter)
    items: list[BacklogItem] = []
    for item in list_result.backlog_items:
        if input_data.category_filter is not None:
            if item.improvement_category != input_data.category_filter:
                continue
        items.append(item)

    if not items:
        return BacklogSurfaceResult(
            status=BacklogSurfaceStatus.EMPTY,
            surface_view=BacklogSurfaceView(
                items=(),
                summary={
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
                total_count=0,
                human_review_required_count=0,
                drift_risk_items=(),
                ready_for_review_items=(),
            ),
        )

    # 4. Enforce max_items limit
    if input_data.max_items > 0 and len(items) > input_data.max_items:
        items = items[:input_data.max_items]

    # 5. Enforce hard limit
    if len(items) > _MAX_SURFACE_ITEMS:
        codes.append(REASON_OVERSIZED_BACKLOG_VIEW)
        codes.sort()
        detail_lines = [f"  - {c}" for c in codes]
        details = "Backlog surface rejected:\n" + "\n".join(detail_lines)
        return BacklogSurfaceResult(
            status=BacklogSurfaceStatus.REJECTED,
            reason_codes=tuple(codes),
            details=details,
        )

    # 6. Check for duplicate backlog_item_ref values
    seen_refs: set[str] = set()
    for item in items:
        if item.backlog_item_ref in seen_refs:
            codes.append(REASON_DUPLICATE_BACKLOG_ITEM_REF)
            break
        seen_refs.add(item.backlog_item_ref)

    # 7. Check each item for issues
    for item in items:
        _check_unsupported_status(item, codes)
        _check_hidden_reasoning_in_item(item, codes)
        _check_external_url_only_in_item(item, codes)
        _check_forbidden_actions_in_item(item, codes)
        _check_forbidden_mutation_in_item(item, codes)

    if codes:
        codes.sort()
        detail_lines = [f"  - {c}" for c in codes]
        details = "Backlog surface rejected:\n" + "\n".join(detail_lines)
        return BacklogSurfaceResult(
            status=BacklogSurfaceStatus.REJECTED,
            reason_codes=tuple(codes),
            details=details,
        )

    # 8. Build full detail dicts for each item
    item_dicts: list[dict] = []
    for item in items:
        item_dicts.append({
            "backlog_item_ref": item.backlog_item_ref,
            "candidate_ref": item.candidate_ref,
            "continuity_ref": item.continuity_ref,
            "product_state_ref": item.product_state_ref,
            "source_reason_codes": list(item.source_reason_codes),
            "evidence_refs": list(item.evidence_refs),
            "improvement_category": item.improvement_category,
            "next_safe_action": item.next_safe_action,
            "blocked_actions": list(item.blocked_actions),
            "drift_risks": list(item.drift_risks),
            "requires_human_review": item.requires_human_review,
            "status": item.status,
            "phase_id": item.phase_id,
            "run_id": item.run_id,
            "session_label": item.session_label,
            "created_at": item.created_at,
            "archived_at": item.archived_at,
        })

    # 9. Build summary counts
    by_status: dict[str, int] = {
        "new": 0,
        "human_review": 0,
        "archived": 0,
        "rejected": 0,
    }
    by_category: dict[str, int] = {
        "self_improvement": 0,
        "continuity_followup": 0,
        "drift_risk": 0,
        "validation_gap": 0,
        "frontend_visibility_gap": 0,
        "human_review_required": 0,
    }

    for item in items:
        status = item.status
        if status in by_status:
            by_status[status] += 1

        category = item.improvement_category
        if category in by_category:
            by_category[category] += 1

    summary = {
        "total": len(items),
        "by_status": by_status,
        "by_category": by_category,
    }

    # 10. Build drift_risk_items
    drift_risk_items: list[dict] = []
    for item in items:
        if item.drift_risks:
            drift_risk_items.append({
                "backlog_item_ref": item.backlog_item_ref,
                "drift_risks": list(item.drift_risks),
                "improvement_category": item.improvement_category,
                "status": item.status,
            })

    # 11. Build ready_for_review_items
    ready_for_review_items: list[str] = []
    for item in items:
        if item.status == "new" and item.requires_human_review:
            ready_for_review_items.append(item.backlog_item_ref)

    # 12. Count human_review_required
    human_review_required_count = sum(
        1 for item in items if item.requires_human_review
    )

    # 13. Sort deterministically by backlog_item_ref
    item_dicts.sort(key=lambda d: d["backlog_item_ref"])
    drift_risk_items.sort(key=lambda d: d["backlog_item_ref"])
    ready_for_review_items.sort()

    surface_view = BacklogSurfaceView(
        items=tuple(item_dicts),
        summary=summary,
        total_count=len(items),
        human_review_required_count=human_review_required_count,
        drift_risk_items=tuple(drift_risk_items),
        ready_for_review_items=tuple(ready_for_review_items),
    )

    return BacklogSurfaceResult(
        status=BacklogSurfaceStatus.READY,
        surface_view=surface_view,
    )
