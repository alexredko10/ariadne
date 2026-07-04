"""
Product iteration recommendation candidate for Ariadne.

Derives deterministic advisory recommendation candidates from
``ProductIterationSummaryData`` using hard-coded thresholds and
reason-code rules.

The candidate is read-only advisory.  It does not create backlog items,
mutate decisions, mutate product iteration records, call providers, use
AI, or introduce analytics.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from typing import Optional

from task_intake.product_iteration_summary import (
    ProductIterationSummaryData,
    ProductIterationSummaryResult,
    ProductIterationSummaryStatus,
    build_product_iteration_summary_from_store,
)


# ---------------------------------------------------------------------------
# ProductIterationCandidateStatus — status values
# ---------------------------------------------------------------------------


class ProductIterationCandidateStatus(str):
    """Status values for product iteration candidate operations."""

    READY = "ready"
    EMPTY = "empty"
    REJECTED = "rejected"


# ---------------------------------------------------------------------------
# ProductIterationCandidate — recommendation candidate
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class ProductIterationCandidate:
    """A deterministic advisory recommendation candidate."""

    candidate_ref: str
    candidate_status: str
    priority: str
    confidence: str
    reason_codes: tuple[str, ...]
    summary_snapshot: str
    recommended_focus: str
    human_review_required: bool
    evidence_counts: dict[str, int]
    explanation_lines: tuple[str, ...]


# ---------------------------------------------------------------------------
# ProductIterationCandidateResult — operation result
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class ProductIterationCandidateResult:
    """Result of a product iteration candidate operation."""

    status: str
    reason_codes: tuple[str, ...] = ()
    candidate: Optional[ProductIterationCandidate] = None
    details: Optional[str] = None


# ---------------------------------------------------------------------------
# Stable reason codes
# ---------------------------------------------------------------------------

RC_NO_RECORDS_YET = "no_records_yet"
RC_HIGH_IDLE_RATIO = "high_idle_ratio"
RC_LOW_ACTIVE_RATIO = "low_active_ratio"
RC_HIGH_CONFUSION_SIGNAL_COUNT = "high_confusion_signal_count"
RC_FEEDBACK_PRESENT = "feedback_present"
RC_HUMAN_NOTES_PRESENT = "human_notes_present"
RC_LONG_SCREEN_TIME_WITHOUT_REFS = "long_screen_time_without_refs"
RC_HEALTHY_USAGE_SIGNAL = "healthy_usage_signal"
RC_INSUFFICIENT_EVIDENCE = "insufficient_evidence"

# ---------------------------------------------------------------------------
# Threshold constants
# ---------------------------------------------------------------------------

HIGH_IDLE_RATIO_THRESHOLD = 0.5
LOW_ACTIVE_RATIO_THRESHOLD = 0.2
HIGH_CONFUSION_SIGNAL_THRESHOLD = 3
LONG_SCREEN_TIME_THRESHOLD_SECONDS = 3600
HEALTHY_ACTIVE_RATIO_THRESHOLD = 0.5
HEALTHY_IDLE_RATIO_MAX = 0.3
INSUFFICIENT_EVIDENCE_RECORDS = 3
RULES_VERSION = "1"


# ---------------------------------------------------------------------------
# Priority / confidence / focus derivation
# ---------------------------------------------------------------------------

_PRIORITY_MAP: dict[str, str] = {
    RC_NO_RECORDS_YET: "none",
    RC_HIGH_IDLE_RATIO: "high",
    RC_LOW_ACTIVE_RATIO: "high",
    RC_HIGH_CONFUSION_SIGNAL_COUNT: "high",
    RC_FEEDBACK_PRESENT: "medium",
    RC_HUMAN_NOTES_PRESENT: "medium",
    RC_LONG_SCREEN_TIME_WITHOUT_REFS: "medium",
    RC_HEALTHY_USAGE_SIGNAL: "low",
    RC_INSUFFICIENT_EVIDENCE: "low",
}

_CONFIDENCE_MAP: dict[str, str] = {
    RC_NO_RECORDS_YET: "high",
    RC_HIGH_IDLE_RATIO: "high",
    RC_LOW_ACTIVE_RATIO: "high",
    RC_HIGH_CONFUSION_SIGNAL_COUNT: "high",
    RC_FEEDBACK_PRESENT: "medium",
    RC_HUMAN_NOTES_PRESENT: "medium",
    RC_LONG_SCREEN_TIME_WITHOUT_REFS: "medium",
    RC_HEALTHY_USAGE_SIGNAL: "medium",
    RC_INSUFFICIENT_EVIDENCE: "low",
}

_FOCUS_MAP: dict[str, str] = {
    RC_NO_RECORDS_YET: "No product iteration records yet. Start capturing session data.",
    RC_HIGH_IDLE_RATIO: "High idle ratio detected. Consider reviewing UI friction or workflow bottlenecks.",
    RC_LOW_ACTIVE_RATIO: "Low active ratio detected. Consider reviewing engagement or task clarity.",
    RC_HIGH_CONFUSION_SIGNAL_COUNT: "Multiple confusion signals recorded. Consider a focused review session.",
    RC_FEEDBACK_PRESENT: "Feedback has been recorded. Review feedback for actionable insights.",
    RC_HUMAN_NOTES_PRESENT: "Human notes are present. Review notes for product iteration ideas.",
    RC_LONG_SCREEN_TIME_WITHOUT_REFS: "Long screen time without run refs. Consider reviewing session focus.",
    RC_HEALTHY_USAGE_SIGNAL: "Healthy usage pattern detected. Continue current approach.",
    RC_INSUFFICIENT_EVIDENCE: "Insufficient evidence for a recommendation. Continue capturing data.",
}

_HUMAN_REVIEW_MAP: dict[str, bool] = {
    RC_NO_RECORDS_YET: False,
    RC_HIGH_IDLE_RATIO: True,
    RC_LOW_ACTIVE_RATIO: True,
    RC_HIGH_CONFUSION_SIGNAL_COUNT: True,
    RC_FEEDBACK_PRESENT: True,
    RC_HUMAN_NOTES_PRESENT: True,
    RC_LONG_SCREEN_TIME_WITHOUT_REFS: True,
    RC_HEALTHY_USAGE_SIGNAL: False,
    RC_INSUFFICIENT_EVIDENCE: False,
}

# Priority ordering for selecting the most significant reason code
_PRIORITY_ORDER: list[str] = [
    RC_NO_RECORDS_YET,
    RC_HIGH_IDLE_RATIO,
    RC_LOW_ACTIVE_RATIO,
    RC_HIGH_CONFUSION_SIGNAL_COUNT,
    RC_FEEDBACK_PRESENT,
    RC_HUMAN_NOTES_PRESENT,
    RC_LONG_SCREEN_TIME_WITHOUT_REFS,
    RC_HEALTHY_USAGE_SIGNAL,
    RC_INSUFFICIENT_EVIDENCE,
]


# ---------------------------------------------------------------------------
# Build candidate
# ---------------------------------------------------------------------------


def build_product_iteration_candidate(
    summary: ProductIterationSummaryData,
) -> ProductIterationCandidateResult:
    """Build a deterministic advisory recommendation candidate.

    Parameters
    ----------
    summary:
        Product iteration summary data to derive the candidate from.

    Returns
    -------
    ProductIterationCandidateResult
        ``status="ready"`` with ``candidate`` when a candidate is derived.
        ``status="empty"`` when the summary is empty.
    """
    # 1. Check for no records
    if summary.total_records == 0:
        reason_codes = (RC_NO_RECORDS_YET,)
        candidate = _build_candidate(summary, reason_codes)
        return ProductIterationCandidateResult(
            status=ProductIterationCandidateStatus.READY,
            candidate=candidate,
        )

    # 2. Apply each reason-code rule
    triggered: list[str] = []

    if summary.idle_ratio > HIGH_IDLE_RATIO_THRESHOLD:
        triggered.append(RC_HIGH_IDLE_RATIO)

    if summary.active_ratio < LOW_ACTIVE_RATIO_THRESHOLD:
        triggered.append(RC_LOW_ACTIVE_RATIO)

    if summary.confusion_refs_count >= HIGH_CONFUSION_SIGNAL_THRESHOLD:
        triggered.append(RC_HIGH_CONFUSION_SIGNAL_COUNT)

    if summary.feedback_refs_count > 0:
        triggered.append(RC_FEEDBACK_PRESENT)

    if summary.records_with_human_note_count > 0:
        triggered.append(RC_HUMAN_NOTES_PRESENT)

    if summary.total_screen_time_seconds > LONG_SCREEN_TIME_THRESHOLD_SECONDS and summary.run_refs_count == 0:
        triggered.append(RC_LONG_SCREEN_TIME_WITHOUT_REFS)

    if summary.active_ratio >= HEALTHY_ACTIVE_RATIO_THRESHOLD and summary.idle_ratio <= HEALTHY_IDLE_RATIO_MAX and summary.confusion_refs_count == 0:
        triggered.append(RC_HEALTHY_USAGE_SIGNAL)

    # 3. Check for insufficient evidence
    if not triggered and summary.total_records < INSUFFICIENT_EVIDENCE_RECORDS:
        triggered.append(RC_INSUFFICIENT_EVIDENCE)

    # 4. If still no triggers, use insufficient_evidence
    if not triggered:
        triggered.append(RC_INSUFFICIENT_EVIDENCE)

    # 5. Sort by priority order
    reason_codes = tuple(sorted(triggered, key=lambda rc: _PRIORITY_ORDER.index(rc) if rc in _PRIORITY_ORDER else 999))

    candidate = _build_candidate(summary, reason_codes)
    return ProductIterationCandidateResult(
        status=ProductIterationCandidateStatus.READY,
        candidate=candidate,
    )


# ---------------------------------------------------------------------------
# Build candidate from store (convenience)
# ---------------------------------------------------------------------------


def build_product_iteration_candidate_from_store(
    store_dir: str = ".ariadne/product-iterations",
    session_ref: Optional[str] = None,
    max_results: int = 1000,
) -> ProductIterationCandidateResult:
    """Build a deterministic advisory recommendation candidate from store.

    Parameters
    ----------
    store_dir:
        Directory for product iteration signal persistence.
    session_ref:
        Optional session ref to filter by.
    max_results:
        Maximum number of records to include.

    Returns
    -------
    ProductIterationCandidateResult
        ``status="ready"`` with ``candidate`` when a candidate is derived.
        ``status="empty"`` when the store is empty.
        ``status="rejected"`` with ``reason_codes`` when the store is
        invalid.
    """
    summary_result = build_product_iteration_summary_from_store(
        store_dir=store_dir,
        session_ref=session_ref,
        max_results=max_results,
    )

    if summary_result.status == ProductIterationSummaryStatus.REJECTED:
        return ProductIterationCandidateResult(
            status=ProductIterationCandidateStatus.REJECTED,
            reason_codes=tuple(summary_result.reason_codes),
            details=summary_result.details,
        )

    if summary_result.status == ProductIterationSummaryStatus.EMPTY or summary_result.summary is None:
        return ProductIterationCandidateResult(
            status=ProductIterationCandidateStatus.EMPTY,
        )

    return build_product_iteration_candidate(summary_result.summary)


# ---------------------------------------------------------------------------
# Internal: build candidate dataclass
# ---------------------------------------------------------------------------


def _build_candidate(
    summary: ProductIterationSummaryData,
    reason_codes: tuple[str, ...],
) -> ProductIterationCandidate:
    """Build a ProductIterationCandidate from summary and reason codes."""
    # Build summary snapshot
    snapshot = json.dumps({
        "total_records": summary.total_records,
        "total_screen_time_seconds": summary.total_screen_time_seconds,
        "total_active_time_seconds": summary.total_active_time_seconds,
        "total_idle_time_seconds": summary.total_idle_time_seconds,
        "active_ratio": summary.active_ratio,
        "idle_ratio": summary.idle_ratio,
        "sessions_count": summary.sessions_count,
        "run_refs_count": summary.run_refs_count,
        "feedback_refs_count": summary.feedback_refs_count,
        "confusion_refs_count": summary.confusion_refs_count,
        "report_refs_count": summary.report_refs_count,
        "decision_trace_refs_count": summary.decision_trace_refs_count,
        "records_with_human_note_count": summary.records_with_human_note_count,
    }, sort_keys=True, ensure_ascii=False)

    # Generate deterministic candidate_ref
    raw = snapshot + "|" + "|".join(reason_codes) + "|" + RULES_VERSION
    candidate_ref = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    # Derive priority, confidence, focus from the most significant reason code
    primary_rc = reason_codes[0] if reason_codes else RC_INSUFFICIENT_EVIDENCE
    priority = _PRIORITY_MAP.get(primary_rc, "low")
    confidence = _CONFIDENCE_MAP.get(primary_rc, "low")
    recommended_focus = _FOCUS_MAP.get(primary_rc, "No specific recommendation.")
    human_review_required = _HUMAN_REVIEW_MAP.get(primary_rc, False)

    # Build evidence counts
    evidence_counts = {
        "total_records": summary.total_records,
        "total_screen_time_seconds": summary.total_screen_time_seconds,
        "total_active_time_seconds": summary.total_active_time_seconds,
        "total_idle_time_seconds": summary.total_idle_time_seconds,
        "active_ratio": summary.active_ratio,
        "idle_ratio": summary.idle_ratio,
        "sessions_count": summary.sessions_count,
        "run_refs_count": summary.run_refs_count,
        "feedback_refs_count": summary.feedback_refs_count,
        "confusion_refs_count": summary.confusion_refs_count,
        "report_refs_count": summary.report_refs_count,
        "decision_trace_refs_count": summary.decision_trace_refs_count,
        "records_with_human_note_count": summary.records_with_human_note_count,
    }

    # Build explanation lines
    explanation_lines: list[str] = []
    for rc in reason_codes:
        explanation_lines.append(_FOCUS_MAP.get(rc, f"Reason code: {rc}"))

    # Determine candidate_status
    if primary_rc in (RC_NO_RECORDS_YET, RC_INSUFFICIENT_EVIDENCE):
        candidate_status = "insufficient_evidence"
    elif primary_rc == RC_HEALTHY_USAGE_SIGNAL:
        candidate_status = "no_recommendation"
    else:
        candidate_status = "recommended"

    return ProductIterationCandidate(
        candidate_ref=candidate_ref,
        candidate_status=candidate_status,
        priority=priority,
        confidence=confidence,
        reason_codes=reason_codes,
        summary_snapshot=snapshot,
        recommended_focus=recommended_focus,
        human_review_required=human_review_required,
        evidence_counts=evidence_counts,
        explanation_lines=tuple(explanation_lines),
    )
