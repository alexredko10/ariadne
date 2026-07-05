"""
Product iteration human review packet for Ariadne.

Composes PR 0117 (product iteration signal store), PR 0120 (evidence
summary), and PR 0121 (recommendation candidate) into one coherent
human-readable review packet.

The packet is read-only advisory.  It does not create backlog items,
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
    ProductIterationSummaryStatus,
    build_product_iteration_summary_from_store,
)
from task_intake.product_iteration_candidate import (
    ProductIterationCandidate,
    ProductIterationCandidateStatus,
    build_product_iteration_candidate_from_store,
    RC_NO_RECORDS_YET,
    RC_HIGH_IDLE_RATIO,
    RC_LOW_ACTIVE_RATIO,
    RC_HIGH_CONFUSION_SIGNAL_COUNT,
    RC_FEEDBACK_PRESENT,
    RC_HUMAN_NOTES_PRESENT,
    RC_LONG_SCREEN_TIME_WITHOUT_REFS,
    RC_HEALTHY_USAGE_SIGNAL,
    RC_INSUFFICIENT_EVIDENCE,
)


# ---------------------------------------------------------------------------
# ProductIterationReviewPacketStatus — status values
# ---------------------------------------------------------------------------


class ProductIterationReviewPacketStatus(str):
    """Status values for review packet operations."""

    READY = "ready"
    EMPTY = "empty"
    REJECTED = "rejected"


# ---------------------------------------------------------------------------
# ProductIterationReviewPacket — the review packet
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class ProductIterationReviewPacket:
    """A deterministic human-readable review packet."""

    packet_ref: str
    packet_status: str
    generated_from: str
    summary: Optional[ProductIterationSummaryData]
    candidate_ref: Optional[str]
    candidate_status: Optional[str]
    priority: Optional[str]
    confidence: Optional[str]
    reason_codes: tuple[str, ...]
    recommended_focus: Optional[str]
    human_review_required: bool
    evidence_counts: dict[str, int]
    evidence_highlights: dict[str, int]
    recommended_human_questions: tuple[str, ...]
    decision_options: tuple[str, ...]
    safety_boundaries: tuple[str, ...]
    validation_notes: tuple[str, ...]
    record_count: int
    session_count: int
    markdown_text: str
    plain_text: str


# ---------------------------------------------------------------------------
# ProductIterationReviewPacketResult — operation result
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class ProductIterationReviewPacketResult:
    """Result of a review packet build operation."""

    status: str
    reason_codes: tuple[str, ...] = ()
    packet: Optional[ProductIterationReviewPacket] = None
    details: Optional[str] = None


# ---------------------------------------------------------------------------
# Stable reason codes
# ---------------------------------------------------------------------------

REASON_MISSING_STORE = "missing_store"
REASON_STORE_NOT_DIRECTORY = "store_not_directory"
REASON_UNBOUNDED_STORE_PATH = "unbounded_store_path"

# ---------------------------------------------------------------------------
# Advisory decision options
# ---------------------------------------------------------------------------

_DECISION_OPTIONS: tuple[str, ...] = (
    "accept_for_manual_planning",
    "reject_candidate",
    "defer_until_more_evidence",
    "request_more_local_testing",
)

# ---------------------------------------------------------------------------
# Recommended human questions (derived from reason codes)
# ---------------------------------------------------------------------------

_RECOMMENDED_QUESTIONS: dict[str, str] = {
    RC_HIGH_IDLE_RATIO: "What caused the high idle time? Are there UI friction points or workflow pauses?",
    RC_LOW_ACTIVE_RATIO: "Why is active usage low? Does the task need better guidance?",
    RC_HIGH_CONFUSION_SIGNAL_COUNT: "What specific interactions triggered confusion signals? Can we review them with the operator?",
    RC_FEEDBACK_PRESENT: "Has the feedback been reviewed? Are there actionable insights?",
    RC_HUMAN_NOTES_PRESENT: "Have the human iteration notes been reviewed for product ideas?",
    RC_LONG_SCREEN_TIME_WITHOUT_REFS: "Why did the operator spend a long time without running tasks?",
    RC_HEALTHY_USAGE_SIGNAL: "The current approach appears healthy. Is there anything to improve?",
    RC_INSUFFICIENT_EVIDENCE: "Is there enough evidence to make a product decision, or should more data be collected?",
    RC_NO_RECORDS_YET: "No product iteration records exist. Should session capture be started?",
}

# ---------------------------------------------------------------------------
# Safety boundaries
# ---------------------------------------------------------------------------

_SAFETY_BOUNDARIES: tuple[str, ...] = (
    "This packet is read-only advisory. It does not modify any Ariadne state.",
    "Decision options in this packet are advisory labels only. They are not executed.",
    "No AI or LLM was used to generate this packet. All content is deterministic.",
    "No external analytics or telemetry are included.",
    "All data is local to this Ariadne instance.",
    "No personal data is included beyond explicit operator notes.",
    "No hidden reasoning or full transcripts are captured.",
    "This packet is not a replacement for human product judgment.",
)

# ---------------------------------------------------------------------------
# Validation notes
# ---------------------------------------------------------------------------

_VALIDATION_NOTES: tuple[str, ...] = (
    "Packet generated from local product iteration records only.",
    "All data is deterministic and reproducible.",
    "No external validation was performed.",
    "Packet ref is derived from all composed data.",
)

# ---------------------------------------------------------------------------
# Build review packet
# ---------------------------------------------------------------------------


def build_product_iteration_review_packet(
    store_dir: str = ".ariadne/product-iterations",
    session_ref: Optional[str] = None,
    max_results: int = 1000,
) -> ProductIterationReviewPacketResult:
    """Build a deterministic human-readable review packet.

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
    ProductIterationReviewPacketResult
        ``status="ready"`` with ``packet`` when data is available.
        ``status="empty"`` when no data is available.
        ``status="rejected"`` with ``reason_codes`` when the store is
        invalid.
    """
    # 1. Build summary
    summary_result = build_product_iteration_summary_from_store(
        store_dir=store_dir,
        session_ref=session_ref,
        max_results=max_results,
    )

    if summary_result.status == ProductIterationSummaryStatus.REJECTED:
        return ProductIterationReviewPacketResult(
            status=ProductIterationReviewPacketStatus.REJECTED,
            reason_codes=tuple(summary_result.reason_codes),
            details=summary_result.details,
        )

    # 2. Build candidate
    candidate_result = build_product_iteration_candidate_from_store(
        store_dir=store_dir,
        session_ref=session_ref,
        max_results=max_results,
    )

    if candidate_result.status == ProductIterationCandidateStatus.REJECTED:
        return ProductIterationReviewPacketResult(
            status=ProductIterationReviewPacketStatus.REJECTED,
            reason_codes=tuple(candidate_result.reason_codes),
            details=candidate_result.details,
        )

    # 3. Check for empty
    summary = summary_result.summary
    candidate = candidate_result.candidate

    # If candidate is EMPTY but summary exists, build candidate directly from summary
    if candidate is None and summary is not None:
        from task_intake.product_iteration_candidate import build_product_iteration_candidate
        direct_result = build_product_iteration_candidate(summary)
        if direct_result.status == ProductIterationCandidateStatus.READY:
            candidate = direct_result.candidate

    if summary is None and candidate is None:
        return ProductIterationReviewPacketResult(
            status=ProductIterationReviewPacketStatus.EMPTY,
        )

    # 4. Compose packet data
    reason_codes = candidate.reason_codes if candidate else ()
    evidence_counts = candidate.evidence_counts if candidate else {}
    evidence_highlights = dict(evidence_counts)  # same as evidence_counts

    # 5. Derive recommended human questions from reason codes
    questions: list[str] = []
    for rc in reason_codes:
        q = _RECOMMENDED_QUESTIONS.get(rc)
        if q and q not in questions:
            questions.append(q)
    if not questions:
        questions.append("Review the product iteration data and determine next steps.")

    # 6. Build validation notes
    validation_notes = list(_VALIDATION_NOTES)
    if summary and summary.total_records == 0:
        validation_notes.append("No product iteration records found.")
    if candidate and candidate.candidate_status == "insufficient_evidence":
        validation_notes.append("Insufficient evidence for a strong recommendation.")

    # 7. Build markdown and plain text
    markdown_text = _render_markdown(
        summary=summary,
        candidate=candidate,
        reason_codes=reason_codes,
        evidence_counts=evidence_counts,
        evidence_highlights=evidence_highlights,
        questions=questions,
        decision_options=list(_DECISION_OPTIONS),
        safety_boundaries=list(_SAFETY_BOUNDARIES),
        validation_notes=validation_notes,
        store_dir=store_dir,
        session_ref=session_ref,
    )
    plain_text = _render_plain_text(
        summary=summary,
        candidate=candidate,
        reason_codes=reason_codes,
        evidence_counts=evidence_counts,
        evidence_highlights=evidence_highlights,
        questions=questions,
        decision_options=list(_DECISION_OPTIONS),
        safety_boundaries=list(_SAFETY_BOUNDARIES),
        validation_notes=validation_notes,
        store_dir=store_dir,
        session_ref=session_ref,
    )

    # 8. Generate deterministic packet_ref
    raw = json.dumps({
        "store_dir": store_dir,
        "session_ref": session_ref,
        "summary_snapshot": candidate.summary_snapshot if candidate else "",
        "reason_codes": list(reason_codes),
        "markdown_text": markdown_text,
    }, sort_keys=True, ensure_ascii=False)
    packet_ref = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    # 9. Build packet
    packet = ProductIterationReviewPacket(
        packet_ref=packet_ref,
        packet_status=ProductIterationReviewPacketStatus.READY,
        generated_from=store_dir,
        summary=summary,
        candidate_ref=candidate.candidate_ref if candidate else None,
        candidate_status=candidate.candidate_status if candidate else None,
        priority=candidate.priority if candidate else None,
        confidence=candidate.confidence if candidate else None,
        reason_codes=reason_codes,
        recommended_focus=candidate.recommended_focus if candidate else None,
        human_review_required=candidate.human_review_required if candidate else False,
        evidence_counts=evidence_counts,
        evidence_highlights=evidence_highlights,
        recommended_human_questions=tuple(questions),
        decision_options=_DECISION_OPTIONS,
        safety_boundaries=_SAFETY_BOUNDARIES,
        validation_notes=tuple(validation_notes),
        record_count=summary.total_records if summary else 0,
        session_count=summary.sessions_count if summary else 0,
        markdown_text=markdown_text,
        plain_text=plain_text,
    )

    return ProductIterationReviewPacketResult(
        status=ProductIterationReviewPacketStatus.READY,
        packet=packet,
    )


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------


def _render_markdown(
    summary: Optional[ProductIterationSummaryData],
    candidate: Optional[ProductIterationCandidate],
    reason_codes: tuple[str, ...],
    evidence_counts: dict[str, int],
    evidence_highlights: dict[str, int],
    questions: list[str],
    decision_options: list[str],
    safety_boundaries: list[str],
    validation_notes: list[str],
    store_dir: str,
    session_ref: Optional[str],
) -> str:
    """Render the review packet as deterministic markdown."""
    lines: list[str] = []
    lines.append("# Product Iteration Review Packet")
    lines.append("")

    # Summary section
    lines.append("## Summary")
    lines.append("")
    if summary:
        lines.append(f"- **Total records**: {summary.total_records}")
        lines.append(f"- **Session count**: {summary.sessions_count}")
        lines.append(f"- **Total screen time**: {summary.total_screen_time_seconds}s")
        lines.append(f"- **Total active time**: {summary.total_active_time_seconds}s")
        lines.append(f"- **Total idle time**: {summary.total_idle_time_seconds}s")
        lines.append(f"- **Active ratio**: {summary.active_ratio}")
        lines.append(f"- **Idle ratio**: {summary.idle_ratio}")
        lines.append(f"- **Run refs count**: {summary.run_refs_count}")
        lines.append(f"- **Feedback refs count**: {summary.feedback_refs_count}")
        lines.append(f"- **Confusion refs count**: {summary.confusion_refs_count}")
        lines.append(f"- **Report refs count**: {summary.report_refs_count}")
        lines.append(f"- **Decision trace refs count**: {summary.decision_trace_refs_count}")
        lines.append(f"- **Records with human notes**: {summary.records_with_human_note_count}")
    else:
        lines.append("No summary data available.")
    lines.append("")

    # Recommendation section
    lines.append("## Recommendation")
    lines.append("")
    if candidate:
        lines.append(f"- **Candidate ref**: {candidate.candidate_ref}")
        lines.append(f"- **Candidate status**: {candidate.candidate_status}")
        lines.append(f"- **Priority**: {candidate.priority}")
        lines.append(f"- **Confidence**: {candidate.confidence}")
        lines.append(f"- **Human review required**: {candidate.human_review_required}")
        lines.append(f"- **Recommended focus**: {candidate.recommended_focus}")
        lines.append("")
        lines.append("### Reason codes")
        for rc in reason_codes:
            lines.append(f"- `{rc}`")
    else:
        lines.append("No recommendation available.")
    lines.append("")

    # Evidence details
    lines.append("## Evidence Details")
    lines.append("")
    lines.append("### Evidence counts")
    for key, value in sorted(evidence_counts.items()):
        lines.append(f"- **{key}**: {value}")
    lines.append("")
    lines.append("### Evidence highlights")
    for key, value in sorted(evidence_highlights.items()):
        lines.append(f"- **{key}**: {value}")
    lines.append("")

    # Recommended human questions
    lines.append("## Recommended Human Questions")
    lines.append("")
    for q in questions:
        lines.append(f"- {q}")
    lines.append("")

    # Decision options
    lines.append("## Decision Options (Advisory)")
    lines.append("")
    lines.append("These options are advisory labels only. They are not executed.")
    lines.append("")
    for opt in decision_options:
        lines.append(f"- `{opt}`")
    lines.append("")

    # Safety boundaries
    lines.append("## Safety Boundaries")
    lines.append("")
    for b in safety_boundaries:
        lines.append(f"- {b}")
    lines.append("")

    # Validation notes
    lines.append("## Validation Notes")
    lines.append("")
    for note in validation_notes:
        lines.append(f"- {note}")
    lines.append("")

    # Footer
    lines.append("---")
    lines.append(f"*Generated from: `{store_dir}`*")
    if session_ref:
        lines.append(f"*Session filter: `{session_ref}`*")
    lines.append("*Packet version: 1*")
    lines.append("*No AI or LLM was used to generate this packet.*")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Plain-text rendering
# ---------------------------------------------------------------------------


def _render_plain_text(
    summary: Optional[ProductIterationSummaryData],
    candidate: Optional[ProductIterationCandidate],
    reason_codes: tuple[str, ...],
    evidence_counts: dict[str, int],
    evidence_highlights: dict[str, int],
    questions: list[str],
    decision_options: list[str],
    safety_boundaries: list[str],
    validation_notes: list[str],
    store_dir: str,
    session_ref: Optional[str],
) -> str:
    """Render the review packet as deterministic plain text."""
    lines: list[str] = []
    lines.append("PRODUCT ITERATION REVIEW PACKET")
    lines.append("")

    # Summary section
    lines.append("=== Summary ===")
    lines.append("")
    if summary:
        lines.append(f"  Total records: {summary.total_records}")
        lines.append(f"  Session count: {summary.sessions_count}")
        lines.append(f"  Total screen time: {summary.total_screen_time_seconds}s")
        lines.append(f"  Total active time: {summary.total_active_time_seconds}s")
        lines.append(f"  Total idle time: {summary.total_idle_time_seconds}s")
        lines.append(f"  Active ratio: {summary.active_ratio}")
        lines.append(f"  Idle ratio: {summary.idle_ratio}")
        lines.append(f"  Run refs count: {summary.run_refs_count}")
        lines.append(f"  Feedback refs count: {summary.feedback_refs_count}")
        lines.append(f"  Confusion refs count: {summary.confusion_refs_count}")
        lines.append(f"  Report refs count: {summary.report_refs_count}")
        lines.append(f"  Decision trace refs count: {summary.decision_trace_refs_count}")
        lines.append(f"  Records with human notes: {summary.records_with_human_note_count}")
    else:
        lines.append("  No summary data available.")
    lines.append("")

    # Recommendation section
    lines.append("=== Recommendation ===")
    lines.append("")
    if candidate:
        lines.append(f"  Candidate ref: {candidate.candidate_ref}")
        lines.append(f"  Candidate status: {candidate.candidate_status}")
        lines.append(f"  Priority: {candidate.priority}")
        lines.append(f"  Confidence: {candidate.confidence}")
        lines.append(f"  Human review required: {candidate.human_review_required}")
        lines.append(f"  Recommended focus: {candidate.recommended_focus}")
        lines.append("")
        lines.append("  Reason codes:")
        for rc in reason_codes:
            lines.append(f"    - {rc}")
    else:
        lines.append("  No recommendation available.")
    lines.append("")

    # Evidence details
    lines.append("=== Evidence Details ===")
    lines.append("")
    lines.append("  Evidence counts:")
    for key, value in sorted(evidence_counts.items()):
        lines.append(f"    {key}: {value}")
    lines.append("")
    lines.append("  Evidence highlights:")
    for key, value in sorted(evidence_highlights.items()):
        lines.append(f"    {key}: {value}")
    lines.append("")

    # Recommended human questions
    lines.append("=== Recommended Human Questions ===")
    lines.append("")
    for q in questions:
        lines.append(f"  - {q}")
    lines.append("")

    # Decision options
    lines.append("=== Decision Options (Advisory) ===")
    lines.append("")
    lines.append("  These options are advisory labels only. They are not executed.")
    lines.append("")
    for opt in decision_options:
        lines.append(f"  - {opt}")
    lines.append("")

    # Safety boundaries
    lines.append("=== Safety Boundaries ===")
    lines.append("")
    for b in safety_boundaries:
        lines.append(f"  - {b}")
    lines.append("")

    # Validation notes
    lines.append("=== Validation Notes ===")
    lines.append("")
    for note in validation_notes:
        lines.append(f"  - {note}")
    lines.append("")

    # Footer
    lines.append("---")
    lines.append(f"Generated from: {store_dir}")
    if session_ref:
        lines.append(f"Session filter: {session_ref}")
    lines.append("Packet version: 1")
    lines.append("No AI or LLM was used to generate this packet.")

    return "\n".join(lines)
