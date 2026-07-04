"""
Product iteration evidence summary for Ariadne.

Summarizes existing product iteration records into a deterministic,
read-only local evidence digest.

The module does not mutate product iteration records, write ``.ariadne``,
mutate backlog, mutate decision history, execute decisions, call providers,
use external network, introduce analytics, capture hidden reasoning, capture
full transcripts, read arbitrary files, run subprocesses, run Docker, or run
git.
"""

from __future__ import annotations

import dataclasses
from typing import Optional

from task_intake.product_iteration import (
    ProductIterationRecord,
    ProductIterationResult,
    ProductIterationStatus,
    list_product_iteration_signals,
)


# ---------------------------------------------------------------------------
# ProductIterationSummaryStatus — status values
# ---------------------------------------------------------------------------


class ProductIterationSummaryStatus(str):
    """Status values for product iteration summary operations."""

    READY = "ready"
    EMPTY = "empty"
    REJECTED = "rejected"


# ---------------------------------------------------------------------------
# ProductIterationSummaryData — summary data
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class ProductIterationSummaryData:
    """Deterministic summary of product iteration records."""

    total_records: int
    total_screen_time_seconds: int
    total_active_time_seconds: int
    total_idle_time_seconds: int
    active_ratio: float
    idle_ratio: float
    sessions_count: int
    latest_session_ref: Optional[str]
    run_refs_count: int
    feedback_refs_count: int
    confusion_refs_count: int
    report_refs_count: int
    decision_trace_refs_count: int
    records_with_human_note_count: int


# ---------------------------------------------------------------------------
# ProductIterationSummaryResult — operation result
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class ProductIterationSummaryResult:
    """Result of a product iteration summary operation."""

    status: str
    reason_codes: tuple[str, ...] = ()
    summary: Optional[ProductIterationSummaryData] = None
    details: Optional[str] = None


# ---------------------------------------------------------------------------
# Build summary from records
# ---------------------------------------------------------------------------


def build_product_iteration_summary(
    records: tuple[ProductIterationRecord, ...],
) -> ProductIterationSummaryResult:
    """Build a deterministic summary from product iteration records.

    Parameters
    ----------
    records:
        Product iteration records to summarize.

    Returns
    -------
    ProductIterationSummaryResult
        ``status="ready"`` with ``summary`` when records are present.
        ``status="empty"`` when no records are provided.
    """
    if not records:
        return ProductIterationSummaryResult(
            status=ProductIterationSummaryStatus.EMPTY,
            summary=ProductIterationSummaryData(
                total_records=0,
                total_screen_time_seconds=0,
                total_active_time_seconds=0,
                total_idle_time_seconds=0,
                active_ratio=0.0,
                idle_ratio=0.0,
                sessions_count=0,
                latest_session_ref=None,
                run_refs_count=0,
                feedback_refs_count=0,
                confusion_refs_count=0,
                report_refs_count=0,
                decision_trace_refs_count=0,
                records_with_human_note_count=0,
            ),
        )

    total_screen_time = 0
    total_active_time = 0
    total_idle_time = 0
    sessions: set[str] = set()
    latest_session_ref: Optional[str] = None
    total_run_refs = 0
    total_feedback_refs = 0
    total_confusion_refs = 0
    total_report_refs = 0
    total_decision_trace_refs = 0
    records_with_note = 0

    for record in records:
        total_screen_time += record.screen_time_seconds
        total_active_time += record.active_time_seconds
        total_idle_time += record.idle_time_seconds

        if record.session_ref:
            sessions.add(record.session_ref)
            # Latest session ref by iteration_ref ordering (records are sorted)
            latest_session_ref = record.session_ref

        total_run_refs += len(record.run_refs)
        total_feedback_refs += len(record.feedback_refs)
        total_confusion_refs += len(record.confusion_refs)
        total_report_refs += len(record.report_refs)
        total_decision_trace_refs += len(record.decision_trace_refs)

        if record.human_iteration_note and record.human_iteration_note.strip():
            records_with_note += 1

    # Compute ratios
    total_time = total_active_time + total_idle_time
    active_ratio = round(total_active_time / total_time, 4) if total_time > 0 else 0.0
    idle_ratio = round(total_idle_time / total_time, 4) if total_time > 0 else 0.0

    summary = ProductIterationSummaryData(
        total_records=len(records),
        total_screen_time_seconds=total_screen_time,
        total_active_time_seconds=total_active_time,
        total_idle_time_seconds=total_idle_time,
        active_ratio=active_ratio,
        idle_ratio=idle_ratio,
        sessions_count=len(sessions),
        latest_session_ref=latest_session_ref,
        run_refs_count=total_run_refs,
        feedback_refs_count=total_feedback_refs,
        confusion_refs_count=total_confusion_refs,
        report_refs_count=total_report_refs,
        decision_trace_refs_count=total_decision_trace_refs,
        records_with_human_note_count=records_with_note,
    )

    return ProductIterationSummaryResult(
        status=ProductIterationSummaryStatus.READY,
        summary=summary,
    )


# ---------------------------------------------------------------------------
# Build summary from store (convenience)
# ---------------------------------------------------------------------------


def build_product_iteration_summary_from_store(
    store_dir: str = ".ariadne/product-iterations",
    session_ref: Optional[str] = None,
    max_results: int = 1000,
) -> ProductIterationSummaryResult:
    """Build a deterministic summary from the product iteration store.

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
    ProductIterationSummaryResult
        ``status="ready"`` with ``summary`` when records are present.
        ``status="empty"`` when no records match.
        ``status="rejected"`` with ``reason_codes`` when the store is
        invalid.
    """
    list_result = list_product_iteration_signals(
        store_dir=store_dir,
        session_ref=session_ref,
        max_results=max_results,
    )

    if list_result.status == ProductIterationStatus.REJECTED:
        return ProductIterationSummaryResult(
            status=ProductIterationSummaryStatus.REJECTED,
            reason_codes=tuple(list_result.reason_codes),
            details=list_result.details,
        )

    if list_result.status == ProductIterationStatus.EMPTY or not list_result.records:
        return ProductIterationSummaryResult(
            status=ProductIterationSummaryStatus.EMPTY,
            summary=ProductIterationSummaryData(
                total_records=0,
                total_screen_time_seconds=0,
                total_active_time_seconds=0,
                total_idle_time_seconds=0,
                active_ratio=0.0,
                idle_ratio=0.0,
                sessions_count=0,
                latest_session_ref=None,
                run_refs_count=0,
                feedback_refs_count=0,
                confusion_refs_count=0,
                report_refs_count=0,
                decision_trace_refs_count=0,
                records_with_human_note_count=0,
            ),
        )

    return build_product_iteration_summary(list_result.records)
