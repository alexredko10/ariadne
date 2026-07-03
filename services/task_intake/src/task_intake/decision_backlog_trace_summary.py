"""
Read-only decision-to-backlog trace summary / evidence map for Ariadne.

Composes existing Ariadne runtime objects (backlog items from PR 0109-0110,
decision records from PR 0112, decision history items from PR 0113) into a
local evidence map.

Core principle:
    The trace summary is read-only.  It links decisions to backlog items,
    surfaces blocked agent actions and next safe human action, and reports
    missing/unresolvable evidence.  It must not mutate backlog items,
    decision records, execute decisions, or call providers.
"""

from __future__ import annotations

import dataclasses
import enum
import json
import os
from typing import Optional

from task_intake.backlog_decision import BacklogDecisionType
from task_intake.decision_history import (
    DecisionHistoryInput,
    DecisionHistoryStatus,
    load_decision_history,
)


# ---------------------------------------------------------------------------
# DecisionTraceStatus — surface view status
# ---------------------------------------------------------------------------


class DecisionTraceStatus(str, enum.Enum):
    """Status of a decision trace view."""

    READY = "ready"
    EMPTY = "empty"
    PARTIAL = "partial"
    REJECTED = "rejected"


# ---------------------------------------------------------------------------
# DecisionTraceInput — input parameters
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class DecisionTraceInput:
    """Input parameters for building a decision trace summary."""

    backlog_store_dir: str = ".ariadne/backlog"
    decision_store_dir: str = ".ariadne/decisions"
    max_traces: int = 50
    backlog_item_ref: Optional[str] = None
    include_backlog_items_without_decisions: bool = False
    sort_by: str = "backlog_item_ref"
    sort_descending: bool = False


# ---------------------------------------------------------------------------
# DecisionTraceBacklogItem — backlog item in trace context
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class DecisionTraceBacklogItem:
    """Backlog item in trace context."""

    backlog_item_ref: str
    backlog_status: str
    backlog_category: Optional[str] = None
    candidate_ref: Optional[str] = None
    continuity_ref: Optional[str] = None


# ---------------------------------------------------------------------------
# DecisionTraceDecision — decision record in trace context
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class DecisionTraceDecision:
    """Decision record in trace context."""

    decision_ref: str
    decision_type: str
    decision_reason: str
    human_actor: str
    created_at: Optional[str] = None
    evidence_refs: tuple[str, ...] = ()
    next_human_action: str = ""
    blocked_agent_actions: tuple[str, ...] = ()
    source_surface: str = ""
    requires_human_review: bool = False


# ---------------------------------------------------------------------------
# DecisionTraceItem — a single trace (backlog item + linked decisions)
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class DecisionTraceItem:
    """A single trace linking a backlog item to its decisions."""

    backlog_item: DecisionTraceBacklogItem
    decisions: tuple[DecisionTraceDecision, ...]
    decision_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    missing_evidence_refs: tuple[str, ...]
    blocked_agent_actions: tuple[str, ...]
    trace_status: str
    trace_warnings: tuple[str, ...]
    latest_decision_ref: Optional[str] = None
    latest_decision_type: Optional[str] = None
    next_safe_human_action: str = ""
    requires_human_review: bool = False


# ---------------------------------------------------------------------------
# DecisionTraceSummary — summary counts
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class DecisionTraceSummary:
    """Summary counts for a decision trace view."""

    total_backlog_items: int
    traced_backlog_items: int
    backlog_items_without_decisions: int
    total_decisions: int
    decisions_without_backlog_item: int
    total_evidence_refs: int
    unresolved_traces: int
    invalid_decision_records: int
    human_review_required: int


# ---------------------------------------------------------------------------
# DecisionTraceResult — operation result
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class DecisionTraceResult:
    """Result of a decision trace build operation."""

    status: str
    reason_codes: tuple[str, ...] = ()
    traces: tuple[DecisionTraceItem, ...] = ()
    untraced_decisions: tuple[DecisionTraceDecision, ...] = ()
    summary: Optional[DecisionTraceSummary] = None
    details: Optional[str] = None


# ---------------------------------------------------------------------------
# Stable reason codes (reused from decision_history.py where applicable)
# ---------------------------------------------------------------------------

REASON_MISSING_BACKLOG_STORE = "missing_backlog_store"
REASON_BACKLOG_STORE_NOT_DIRECTORY = "backlog_store_not_directory"
REASON_UNBOUNDED_BACKLOG_STORE_PATH = "unbounded_backlog_store_path"
REASON_MISSING_DECISION_STORE = "missing_decision_store"
REASON_DECISION_STORE_NOT_DIRECTORY = "decision_store_not_directory"
REASON_UNBOUNDED_DECISION_STORE_PATH = "unbounded_decision_store_path"
REASON_UNREADABLE_BACKLOG_ITEM = "unreadable_backlog_item"
REASON_MALFORMED_BACKLOG_ITEM_JSON = "malformed_backlog_item_json"
REASON_OVERSIZED_TRACE_VIEW = "oversized_trace_view"

# ---------------------------------------------------------------------------
# Bounds
# ---------------------------------------------------------------------------

_MAX_TRACE_RESULTS = 1000


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _check_backlog_store_path(backlog_store_dir: str, codes: list[str]) -> None:
    """Validate backlog store path boundedness and existence."""
    if not backlog_store_dir or backlog_store_dir.strip() == "":
        codes.append(REASON_UNBOUNDED_BACKLOG_STORE_PATH)
        return

    path = backlog_store_dir.strip()

    if ".." in path.split("/"):
        codes.append(REASON_UNBOUNDED_BACKLOG_STORE_PATH)
        return

    if not os.path.exists(path):
        codes.append(REASON_MISSING_BACKLOG_STORE)
        return

    if not os.path.isdir(path):
        codes.append(REASON_BACKLOG_STORE_NOT_DIRECTORY)
        return


def _check_decision_store_path(decision_store_dir: str, codes: list[str]) -> None:
    """Validate decision store path boundedness and existence."""
    if not decision_store_dir or decision_store_dir.strip() == "":
        codes.append(REASON_UNBOUNDED_DECISION_STORE_PATH)
        return

    path = decision_store_dir.strip()

    if ".." in path.split("/"):
        codes.append(REASON_UNBOUNDED_DECISION_STORE_PATH)
        return

    if not os.path.exists(path):
        codes.append(REASON_MISSING_DECISION_STORE)
        return

    if not os.path.isdir(path):
        codes.append(REASON_DECISION_STORE_NOT_DIRECTORY)
        return


# ---------------------------------------------------------------------------
# Load backlog items from store (direct JSON enumeration)
# ---------------------------------------------------------------------------


def _load_backlog_items(backlog_store_dir: str) -> tuple[list[dict], int]:
    """Load backlog items from the store directory.

    Returns (valid_items, invalid_count).
    """
    valid_items: list[dict] = []
    invalid_count = 0

    try:
        json_files = sorted([
            f for f in os.listdir(backlog_store_dir)
            if f.endswith(".json")
        ])
    except OSError:
        return [], 0

    for filename in json_files:
        filepath = os.path.join(backlog_store_dir, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                raw = f.read()
        except OSError:
            invalid_count += 1
            continue

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            invalid_count += 1
            continue

        if not isinstance(data, dict):
            invalid_count += 1
            continue

        backlog_item_ref = data.get("backlog_item_ref", "")
        if not backlog_item_ref:
            invalid_count += 1
            continue

        valid_items.append(data)

    return valid_items, invalid_count


# ---------------------------------------------------------------------------
# Build decision trace
# ---------------------------------------------------------------------------


def build_decision_trace(
    input_data: DecisionTraceInput,
) -> DecisionTraceResult:
    """Build a read-only decision-to-backlog trace summary.

    Parameters
    ----------
    input_data:
        Input parameters including backlog store path, decision store path,
        optional filters, sort options, and max traces limit.

    Returns
    -------
    DecisionTraceResult
        ``status="ready"`` with ``traces``, ``untraced_decisions``, and
        ``summary`` when traces are built.
        ``status="empty"`` when no data is available.
        ``status="partial"`` when some data is available but incomplete.
        ``status="rejected"`` with ``reason_codes`` when validation fails.
    """
    codes: list[str] = []

    # 1. Validate backlog store path
    _check_backlog_store_path(input_data.backlog_store_dir, codes)

    if codes:
        codes.sort()
        detail_lines = [f"  - {c}" for c in codes]
        details = "Decision trace rejected:\n" + "\n".join(detail_lines)
        return DecisionTraceResult(
            status=DecisionTraceStatus.REJECTED.value,
            reason_codes=tuple(codes),
            details=details,
        )

    # 2. Validate decision store path
    _check_decision_store_path(input_data.decision_store_dir, codes)

    if codes:
        codes.sort()
        detail_lines = [f"  - {c}" for c in codes]
        details = "Decision trace rejected:\n" + "\n".join(detail_lines)
        return DecisionTraceResult(
            status=DecisionTraceStatus.REJECTED.value,
            reason_codes=tuple(codes),
            details=details,
        )

    # 3. Load backlog items
    backlog_items, invalid_backlog_count = _load_backlog_items(
        input_data.backlog_store_dir
    )

    # 4. Load decision history
    history_input = DecisionHistoryInput(
        decision_store_dir=input_data.decision_store_dir,
        max_results=_MAX_TRACE_RESULTS,
    )
    history_result = load_decision_history(history_input)

    # 5. Build decision lookup by backlog_item_ref
    decisions_by_backlog_ref: dict[str, list[DecisionTraceDecision]] = {}
    all_decisions: list[DecisionTraceDecision] = []
    untraced_decisions: list[DecisionTraceDecision] = []

    if history_result.status == DecisionHistoryStatus.READY.value and history_result.view:
        for item in history_result.view.items:
            decision = DecisionTraceDecision(
                decision_ref=item.decision_ref,
                decision_type=item.decision_type,
                decision_reason=item.decision_reason,
                human_actor=item.human_actor,
                created_at=None,
                evidence_refs=item.evidence_refs,
                next_human_action=item.next_human_action,
                blocked_agent_actions=item.blocked_agent_actions,
                source_surface=item.source_surface,
                requires_human_review=item.requires_human_review,
            )
            all_decisions.append(decision)

            ref = item.backlog_item_ref
            if ref not in decisions_by_backlog_ref:
                decisions_by_backlog_ref[ref] = []
            decisions_by_backlog_ref[ref].append(decision)

    # 6. Build traces
    traces: list[DecisionTraceItem] = []
    backlog_refs_with_decisions: set[str] = set()
    total_evidence_refs = 0
    unresolved_traces = 0
    human_review_required = 0

    # Apply optional backlog_item_ref filter
    filtered_backlog_items = backlog_items
    if input_data.backlog_item_ref is not None:
        filtered_backlog_items = [
            item for item in backlog_items
            if item.get("backlog_item_ref") == input_data.backlog_item_ref
        ]

    for backlog_data in filtered_backlog_items:
        backlog_item_ref = backlog_data.get("backlog_item_ref", "")
        backlog_status = backlog_data.get("status", "unknown")
        backlog_category = backlog_data.get("improvement_category")
        candidate_ref = backlog_data.get("candidate_ref")
        continuity_ref = backlog_data.get("continuity_ref")

        backlog_item = DecisionTraceBacklogItem(
            backlog_item_ref=backlog_item_ref,
            backlog_status=backlog_status,
            backlog_category=backlog_category,
            candidate_ref=candidate_ref,
            continuity_ref=continuity_ref,
        )

        linked_decisions = decisions_by_backlog_ref.get(backlog_item_ref, [])
        decision_refs = tuple(d.decision_ref for d in linked_decisions)

        # Collect all evidence refs from linked decisions
        evidence_refs: set[str] = set()
        for d in linked_decisions:
            for ref in d.evidence_refs:
                evidence_refs.add(ref)
        evidence_refs_list = tuple(sorted(evidence_refs))
        total_evidence_refs += len(evidence_refs_list)

        # Determine missing evidence refs (evidence refs from backlog item not in decisions)
        backlog_evidence_refs = set(backlog_data.get("evidence_refs", []))
        missing_evidence_refs = tuple(sorted(
            ref for ref in backlog_evidence_refs if ref not in evidence_refs
        ))

        # Determine blocked agent actions
        blocked_actions: set[str] = set()
        for d in linked_decisions:
            for action in d.blocked_agent_actions:
                blocked_actions.add(action)
        blocked_actions_list = tuple(sorted(blocked_actions))

        # Determine next safe human action (from latest decision)
        next_safe_human_action = ""
        if linked_decisions:
            next_safe_human_action = linked_decisions[-1].next_human_action

        # Determine trace status
        if not linked_decisions:
            trace_status = "no_decisions"
        elif missing_evidence_refs:
            trace_status = "partial"
        else:
            trace_status = "complete"

        # Determine latest decision ref and type
        latest_decision_ref = None
        latest_decision_type = None
        if linked_decisions:
            latest_decision_ref = linked_decisions[-1].decision_ref
            latest_decision_type = linked_decisions[-1].decision_type

        # Warnings
        trace_warnings: list[str] = []
        if missing_evidence_refs:
            trace_warnings.append("missing_evidence_refs")
        if trace_status == "no_decisions":
            trace_warnings.append("no_decisions")

        requires_review = any(d.requires_human_review for d in linked_decisions)
        if requires_review:
            human_review_required += 1

        if trace_status in ("partial", "no_decisions"):
            unresolved_traces += 1

        trace_item = DecisionTraceItem(
            backlog_item=backlog_item,
            decisions=tuple(linked_decisions),
            decision_refs=decision_refs,
            latest_decision_ref=latest_decision_ref,
            latest_decision_type=latest_decision_type,
            evidence_refs=evidence_refs_list,
            missing_evidence_refs=missing_evidence_refs,
            blocked_agent_actions=blocked_actions_list,
            next_safe_human_action=next_safe_human_action,
            trace_status=trace_status,
            trace_warnings=tuple(trace_warnings),
            requires_human_review=requires_review,
        )
        traces.append(trace_item)

        if linked_decisions:
            backlog_refs_with_decisions.add(backlog_item_ref)

    # 7. Identify untraced decisions (decisions referencing unknown backlog items)
    all_backlog_refs = {item.get("backlog_item_ref", "") for item in backlog_items}
    for decision in all_decisions:
        if decision.decision_ref not in {d.decision_ref for d in untraced_decisions}:
            # Check if this decision's backlog_item_ref is in the backlog
            # We need to find the backlog_item_ref from the decision
            pass

    # Find decisions whose backlog_item_ref is not in any backlog item
    decision_refs_in_backlog: set[str] = set()
    for trace in traces:
        for d in trace.decisions:
            decision_refs_in_backlog.add(d.decision_ref)

    for decision in all_decisions:
        if decision.decision_ref not in decision_refs_in_backlog:
            untraced_decisions.append(decision)

    # 8. Apply include_backlog_items_without_decisions filter
    if not input_data.include_backlog_items_without_decisions:
        traces = [t for t in traces if t.decisions]

    # 9. Sort
    sort_desc = input_data.sort_descending
    sort_field = input_data.sort_by

    def _sort_key(item: DecisionTraceItem) -> tuple:
        if sort_field == "backlog_item_ref":
            return (item.backlog_item.backlog_item_ref,)
        elif sort_field == "latest_decision_type":
            return (item.latest_decision_type or "",)
        elif sort_field == "trace_status":
            return (item.trace_status,)
        else:
            return (item.backlog_item.backlog_item_ref,)

    traces.sort(key=_sort_key, reverse=sort_desc)

    # 10. Cap at max_traces
    max_traces = min(input_data.max_traces, _MAX_TRACE_RESULTS)
    if len(traces) > max_traces:
        codes.append(REASON_OVERSIZED_TRACE_VIEW)
        traces = traces[:max_traces]

    # 11. Compute summary
    total_backlog_items = len(backlog_items)
    traced_backlog_items = len(backlog_refs_with_decisions)
    backlog_items_without_decisions = total_backlog_items - traced_backlog_items
    total_decisions = len(all_decisions)
    decisions_without_backlog_item = len(untraced_decisions)
    invalid_decision_records = history_result.view.summary.rejected_or_invalid_decision_records if history_result.view else 0

    summary = DecisionTraceSummary(
        total_backlog_items=total_backlog_items,
        traced_backlog_items=traced_backlog_items,
        backlog_items_without_decisions=backlog_items_without_decisions,
        total_decisions=total_decisions,
        decisions_without_backlog_item=decisions_without_backlog_item,
        total_evidence_refs=total_evidence_refs,
        unresolved_traces=unresolved_traces,
        invalid_decision_records=invalid_decision_records,
        human_review_required=human_review_required,
    )

    # 12. Determine overall status
    if not traces and not untraced_decisions:
        status = DecisionTraceStatus.EMPTY.value
    elif not traces and untraced_decisions:
        status = DecisionTraceStatus.PARTIAL.value
    elif codes:
        status = DecisionTraceStatus.PARTIAL.value
    else:
        status = DecisionTraceStatus.READY.value

    return DecisionTraceResult(
        status=status,
        reason_codes=tuple(codes) if codes else (),
        traces=tuple(traces),
        untraced_decisions=tuple(untraced_decisions),
        summary=summary,
    )
