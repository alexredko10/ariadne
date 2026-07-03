"""
Read-only human decision history surface for Ariadne.

Provides ``DecisionHistoryInput``, ``DecisionHistoryItem``,
``DecisionHistoryView``, ``DecisionHistorySummary``,
``DecisionHistoryResult``, ``DecisionHistoryStatus``, stable reason codes,
and ``load_decision_history()``.

Core principle:
    Decision records are durable evidence of human intent.
    Viewing them must be deterministic, local, bounded, read-only,
    and reviewable.
"""

from __future__ import annotations

import dataclasses
import enum
import json
import os
from typing import Optional

from task_intake.backlog_decision import BacklogDecisionType


# ---------------------------------------------------------------------------
# DecisionHistoryStatus — surface view status
# ---------------------------------------------------------------------------


class DecisionHistoryStatus(str, enum.Enum):
    """Status of a decision history view."""

    READY = "ready"
    EMPTY = "empty"
    REJECTED = "rejected"


# ---------------------------------------------------------------------------
# DecisionHistoryInput — input parameters
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class DecisionHistoryInput:
    """Input parameters for loading decision history."""

    decision_store_dir: str = ".ariadne/decisions"
    max_results: int = 100
    backlog_item_ref: Optional[str] = None  # optional filter
    decision_type: Optional[str] = None  # optional filter
    human_actor: Optional[str] = None  # optional filter
    sort_by: str = "created_at"  # "created_at" | "backlog_item_ref" | "decision_ref"
    sort_descending: bool = True


# ---------------------------------------------------------------------------
# DecisionHistoryItem — read-only item
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class DecisionHistoryItem:
    """A read-only decision history item."""

    decision_ref: str
    backlog_item_ref: str
    candidate_ref: str
    continuity_ref: str
    evidence_refs: tuple[str, ...]
    human_actor: str
    decision_type: str
    decision_reason: str
    next_human_action: str
    blocked_agent_actions: tuple[str, ...]
    created_at: None
    product_name: str
    source_surface: str
    requires_human_review: bool
    decision_record_path: Optional[str]
    linked_backlog_item_status: Optional[str] = None
    schema_version: Optional[str] = None


# ---------------------------------------------------------------------------
# DecisionHistorySummary — summary counts
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class DecisionHistorySummary:
    """Summary counts for a decision history view."""

    total_decisions: int
    decisions_by_type: dict[str, int]
    decisions_by_backlog_item: dict[str, int]
    rejected_or_invalid_decision_records: int
    human_review_required: int


# ---------------------------------------------------------------------------
# DecisionHistoryView — read-only view
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class DecisionHistoryView:
    """A read-only view of decision history."""

    items: tuple[DecisionHistoryItem, ...]
    total_count: int
    summary: DecisionHistorySummary


# ---------------------------------------------------------------------------
# DecisionHistoryResult — operation result
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class DecisionHistoryResult:
    """Result of a decision history load operation."""

    status: str  # "ready" | "empty" | "rejected"
    reason_codes: tuple[str, ...] = ()
    view: Optional[DecisionHistoryView] = None
    details: Optional[str] = None


# ---------------------------------------------------------------------------
# Stable reason codes
# ---------------------------------------------------------------------------

REASON_MISSING_DECISION_STORE = "missing_decision_store"
REASON_DECISION_STORE_NOT_DIRECTORY = "decision_store_not_directory"
REASON_UNBOUNDED_DECISION_STORE_PATH = "unbounded_decision_store_path"
REASON_UNREADABLE_DECISION_RECORD = "unreadable_decision_record"
REASON_MALFORMED_DECISION_RECORD_JSON = "malformed_decision_record_json"
REASON_MISSING_DECISION_REF = "missing_decision_ref"
REASON_DUPLICATE_DECISION_REF = "duplicate_decision_ref"
REASON_MISSING_BACKLOG_ITEM_REF = "missing_backlog_item_ref"
REASON_UNSUPPORTED_DECISION_TYPE = "unsupported_decision_type"
REASON_HIDDEN_REASONING_NOT_ALLOWED = "hidden_reasoning_not_allowed"
REASON_MUTATION_NOT_ALLOWED = "mutation_not_allowed"
REASON_ARCHIVE_NOT_ALLOWED = "archive_not_allowed"
REASON_APPROVAL_NOT_ALLOWED = "approval_not_allowed"
REASON_GATE_FINALIZATION_NOT_ALLOWED = "gate_finalization_not_allowed"
REASON_COMMAND_EXECUTION_NOT_ALLOWED = "command_execution_not_allowed"
REASON_PROVIDER_CALL_NOT_ALLOWED = "provider_call_not_allowed"
REASON_GIT_MUTATION_NOT_ALLOWED = "git_mutation_not_allowed"
REASON_OVERSIZED_DECISION_HISTORY_VIEW = "oversized_decision_history_view"

# ---------------------------------------------------------------------------
# Forbidden patterns (reused from backlog_decision)
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

_MAX_HISTORY_RESULTS = 1000


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _check_decision_store_path(decision_store_dir: str, codes: list[str]) -> None:
    """Validate decision store path boundedness and existence."""
    if not decision_store_dir or decision_store_dir.strip() == "":
        codes.append(REASON_UNBOUNDED_DECISION_STORE_PATH)
        return

    path = decision_store_dir.strip()

    # Reject paths with parent-directory traversal
    if ".." in path.split("/"):
        codes.append(REASON_UNBOUNDED_DECISION_STORE_PATH)
        return

    if not os.path.exists(path):
        codes.append(REASON_MISSING_DECISION_STORE)
        return

    if not os.path.isdir(path):
        codes.append(REASON_DECISION_STORE_NOT_DIRECTORY)
        return


def _check_forbidden_patterns(text: str, codes: list[str]) -> None:
    """Check for forbidden patterns in text."""
    from runner.improvement_backlog import (
        _FORBIDDEN_HIDDEN_REASONING_PATTERNS,
        _FORBIDDEN_ACTION_PATTERNS,
    )

    # Hidden reasoning
    for pattern in _FORBIDDEN_HIDDEN_REASONING_PATTERNS:
        if pattern in text:
            codes.append(REASON_HIDDEN_REASONING_NOT_ALLOWED)
            return

    # Forbidden actions (command execution, provider call, git mutation)
    for pattern, reason in _FORBIDDEN_ACTION_PATTERNS:
        if pattern in text:
            codes.append(reason)
            return

    # Forbidden mutation patterns
    for pattern, reason in _FORBIDDEN_MUTATION_PATTERNS:
        if pattern in text:
            codes.append(reason)
            return


# ---------------------------------------------------------------------------
# Load decision history
# ---------------------------------------------------------------------------


def load_decision_history(
    input_data: DecisionHistoryInput,
) -> DecisionHistoryResult:
    """Load a read-only view of decision history.

    Parameters
    ----------
    input_data:
        Input parameters including decision store path, optional filters,
        sort options, and max results limit.

    Returns
    -------
    DecisionHistoryResult
        ``status="ready"`` with ``view`` when decisions are loaded.
        ``status="empty"`` when no decisions match.
        ``status="rejected"`` with ``reason_codes`` when validation fails.
    """
    codes: list[str] = []

    # 1. Validate decision store path
    _check_decision_store_path(input_data.decision_store_dir, codes)

    if codes:
        codes.sort()
        detail_lines = [f"  - {c}" for c in codes]
        details = "Decision history rejected:\n" + "\n".join(detail_lines)
        return DecisionHistoryResult(
            status=DecisionHistoryStatus.REJECTED.value,
            reason_codes=tuple(codes),
            details=details,
        )

    # 2. Enumerate JSON files in decision store
    store_path = input_data.decision_store_dir.strip()
    try:
        json_files = sorted([
            f for f in os.listdir(store_path)
            if f.endswith(".json")
        ])
    except OSError:
        codes.append(REASON_UNREADABLE_DECISION_RECORD)
        codes.sort()
        detail_lines = [f"  - {c}" for c in codes]
        details = "Decision history rejected:\n" + "\n".join(detail_lines)
        return DecisionHistoryResult(
            status=DecisionHistoryStatus.REJECTED.value,
            reason_codes=tuple(codes),
            details=details,
        )

    if not json_files:
        return DecisionHistoryResult(
            status=DecisionHistoryStatus.EMPTY.value,
            view=DecisionHistoryView(
                items=(),
                total_count=0,
                summary=DecisionHistorySummary(
                    total_decisions=0,
                    decisions_by_type={},
                    decisions_by_backlog_item={},
                    rejected_or_invalid_decision_records=0,
                    human_review_required=0,
                ),
            ),
        )

    # 3. Load each decision record
    valid_items: list[DecisionHistoryItem] = []
    rejected_count = 0
    seen_refs: set[str] = set()

    valid_types = {t.value for t in BacklogDecisionType}

    for filename in json_files:
        filepath = os.path.join(store_path, filename)

        # Read file
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                raw = f.read()
        except OSError:
            rejected_count += 1
            continue

        # Parse JSON
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            rejected_count += 1
            continue

        if not isinstance(data, dict):
            rejected_count += 1
            continue

        # Validate required fields
        decision_ref = data.get("decision_ref", "")
        backlog_item_ref = data.get("backlog_item_ref", "")

        if not decision_ref:
            rejected_count += 1
            continue

        if not backlog_item_ref:
            rejected_count += 1
            continue

        # Check for duplicate decision_ref
        if decision_ref in seen_refs:
            rejected_count += 1
            continue
        seen_refs.add(decision_ref)

        # Validate decision_type
        decision_type = data.get("decision_type", "")
        if decision_type not in valid_types:
            rejected_count += 1
            continue

        # Check for forbidden patterns in text fields
        item_codes: list[str] = []
        text_fields = [
            data.get("decision_reason", ""),
            data.get("next_human_action", ""),
        ]
        for text in text_fields:
            _check_forbidden_patterns(text, item_codes)

        if item_codes:
            rejected_count += 1
            continue

        # Build item
        evidence_refs = tuple(sorted(data.get("evidence_refs", [])))
        blocked_actions = tuple(data.get("blocked_agent_actions", []))

        item = DecisionHistoryItem(
            decision_ref=decision_ref,
            backlog_item_ref=backlog_item_ref,
            candidate_ref=data.get("candidate_ref", ""),
            continuity_ref=data.get("continuity_ref", ""),
            evidence_refs=evidence_refs,
            human_actor=data.get("human_actor", ""),
            decision_type=decision_type,
            decision_reason=data.get("decision_reason", ""),
            next_human_action=data.get("next_human_action", ""),
            blocked_agent_actions=blocked_actions,
            created_at=None,
            product_name="Ariadne",
            source_surface="task_intake",
            requires_human_review=True,
            decision_record_path=filepath,
            linked_backlog_item_status=None,
            schema_version=None,
        )
        valid_items.append(item)

    # 4. Apply optional filters
    if input_data.backlog_item_ref is not None:
        valid_items = [
            item for item in valid_items
            if item.backlog_item_ref == input_data.backlog_item_ref
        ]

    if input_data.decision_type is not None:
        valid_items = [
            item for item in valid_items
            if item.decision_type == input_data.decision_type
        ]

    if input_data.human_actor is not None:
        valid_items = [
            item for item in valid_items
            if item.human_actor == input_data.human_actor
        ]

    if not valid_items:
        return DecisionHistoryResult(
            status=DecisionHistoryStatus.EMPTY.value,
            view=DecisionHistoryView(
                items=(),
                total_count=0,
                summary=DecisionHistorySummary(
                    total_decisions=0,
                    decisions_by_type={},
                    decisions_by_backlog_item={},
                    rejected_or_invalid_decision_records=rejected_count,
                    human_review_required=0,
                ),
            ),
        )

    # 5. Sort
    sort_desc = input_data.sort_descending
    sort_field = input_data.sort_by

    def _sort_key(item: DecisionHistoryItem) -> tuple:
        if sort_field == "created_at":
            # None values sort to end for ascending, beginning for descending
            return (0 if sort_desc else 1, "")
        elif sort_field == "backlog_item_ref":
            return (1, item.backlog_item_ref)
        elif sort_field == "decision_ref":
            return (1, item.decision_ref)
        else:
            return (1, "")

    valid_items.sort(key=_sort_key, reverse=sort_desc)

    # 6. Cap at max_results
    max_results = min(input_data.max_results, _MAX_HISTORY_RESULTS)
    if len(valid_items) > max_results:
        codes.append(REASON_OVERSIZED_DECISION_HISTORY_VIEW)
        valid_items = valid_items[:max_results]

    # 7. Compute summary counts
    decisions_by_type: dict[str, int] = {}
    decisions_by_backlog_item: dict[str, int] = {}
    human_review_required = 0

    for item in valid_items:
        decisions_by_type[item.decision_type] = decisions_by_type.get(item.decision_type, 0) + 1
        decisions_by_backlog_item[item.backlog_item_ref] = decisions_by_backlog_item.get(item.backlog_item_ref, 0) + 1
        if item.requires_human_review:
            human_review_required += 1

    summary = DecisionHistorySummary(
        total_decisions=len(valid_items),
        decisions_by_type=decisions_by_type,
        decisions_by_backlog_item=decisions_by_backlog_item,
        rejected_or_invalid_decision_records=rejected_count,
        human_review_required=human_review_required,
    )

    view = DecisionHistoryView(
        items=tuple(valid_items),
        total_count=len(valid_items),
        summary=summary,
    )

    return DecisionHistoryResult(
        status=DecisionHistoryStatus.READY.value,
        reason_codes=tuple(codes) if codes else (),
        view=view,
    )
