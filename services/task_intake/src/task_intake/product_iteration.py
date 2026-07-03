"""
Local product iteration signal contract for Ariadne.

Records deterministic local product-iteration signal evidence for operator
session/screen-time data.  All data stays in ``.ariadne/product-iterations/``.
No external analytics.  No network.  No provider calls.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import os
from typing import Optional

from runner.improvement_backlog import (
    _FORBIDDEN_HIDDEN_REASONING_PATTERNS,
    _FORBIDDEN_ACTION_PATTERNS,
)


# ---------------------------------------------------------------------------
# ProductIterationStatus — status values
# ---------------------------------------------------------------------------


class ProductIterationStatus(str):
    """Status values for product iteration signals."""

    RECORDED = "recorded"
    DRAFT = "draft"
    REJECTED = "rejected"
    EMPTY = "empty"


# ---------------------------------------------------------------------------
# ProductIterationInput — input parameters
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class ProductIterationInput:
    """Input parameters for recording a product iteration signal."""

    session_ref: str = ""
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    screen_time_seconds: int = 0
    active_time_seconds: int = 0
    idle_time_seconds: int = 0
    run_refs: tuple[str, ...] = ()
    feedback_refs: tuple[str, ...] = ()
    confusion_refs: tuple[str, ...] = ()
    report_refs: tuple[str, ...] = ()
    decision_trace_refs: tuple[str, ...] = ()
    human_iteration_note: str = ""
    source_surface: str = "task_intake"
    product_signal_status: str = "recorded"
    store_dir: str = ".ariadne/product-iterations"


# ---------------------------------------------------------------------------
# ProductIterationRecord — persisted record
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class ProductIterationRecord:
    """An immutable product iteration signal record."""

    iteration_ref: str
    session_ref: str
    started_at: Optional[str]
    ended_at: Optional[str]
    screen_time_seconds: int
    active_time_seconds: int
    idle_time_seconds: int
    run_refs: tuple[str, ...]
    feedback_refs: tuple[str, ...]
    confusion_refs: tuple[str, ...]
    report_refs: tuple[str, ...]
    decision_trace_refs: tuple[str, ...]
    human_iteration_note: str
    product_signal_status: str
    created_at: None
    source_surface: str
    schema_version: str = "1"


# ---------------------------------------------------------------------------
# ProductIterationResult — operation result
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class ProductIterationResult:
    """Result of a product iteration signal operation."""

    status: str
    reason_codes: tuple[str, ...] = ()
    record: Optional[ProductIterationRecord] = None
    iteration_ref: Optional[str] = None
    records: tuple[ProductIterationRecord, ...] = ()
    total_count: int = 0
    details: Optional[str] = None


# ---------------------------------------------------------------------------
# Stable reason codes
# ---------------------------------------------------------------------------

REASON_MISSING_SESSION_REF = "missing_session_ref"
REASON_HIDDEN_REASONING_NOT_ALLOWED = "hidden_reasoning_not_allowed"
REASON_EXTERNAL_URL_ONLY_NOT_ALLOWED = "external_url_only_not_allowed"
REASON_MUTATION_NOT_ALLOWED = "mutation_not_allowed"
REASON_ARCHIVE_NOT_ALLOWED = "archive_not_allowed"
REASON_APPROVAL_NOT_ALLOWED = "approval_not_allowed"
REASON_GATE_FINALIZATION_NOT_ALLOWED = "gate_finalization_not_allowed"
REASON_COMMAND_EXECUTION_NOT_ALLOWED = "command_execution_not_allowed"
REASON_PROVIDER_CALL_NOT_ALLOWED = "provider_call_not_allowed"
REASON_GIT_MUTATION_NOT_ALLOWED = "git_mutation_not_allowed"
REASON_UNBOUNDED_STORE_PATH = "unbounded_store_path"
REASON_OVERSIZED_PAYLOAD = "oversized_payload"
REASON_DUPLICATE_ITERATION_REF = "duplicate_iteration_ref"

# ---------------------------------------------------------------------------
# Forbidden patterns
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

_MAX_PAYLOAD_BYTES = 1024 * 100  # 100 KB
_MAX_LIST_RESULTS = 1000


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _check_store_path(store_dir: str, codes: list[str]) -> None:
    """Validate store path boundedness."""
    if not store_dir or store_dir.strip() == "":
        codes.append(REASON_UNBOUNDED_STORE_PATH)
        return

    path = store_dir.strip()

    if ".." in path.split("/"):
        codes.append(REASON_UNBOUNDED_STORE_PATH)
        return


def _check_hidden_reasoning(text: str, codes: list[str]) -> None:
    """Check for hidden reasoning patterns in text."""
    for pattern in _FORBIDDEN_HIDDEN_REASONING_PATTERNS:
        if pattern in text:
            codes.append(REASON_HIDDEN_REASONING_NOT_ALLOWED)
            return


def _check_external_url_only(text: str, codes: list[str]) -> None:
    """Check for external URL-only evidence in text."""
    stripped = text.strip()
    if stripped.startswith("http://") or stripped.startswith("https://"):
        if "\n" not in stripped and " " not in stripped:
            codes.append(REASON_EXTERNAL_URL_ONLY_NOT_ALLOWED)


def _check_forbidden_actions(text: str, codes: list[str]) -> None:
    """Check for forbidden action patterns in text."""
    for pattern, reason in _FORBIDDEN_ACTION_PATTERNS:
        if pattern in text:
            codes.append(reason)
            return


def _check_forbidden_mutation(text: str, codes: list[str]) -> None:
    """Check for forbidden mutation patterns in text."""
    for pattern, reason in _FORBIDDEN_MUTATION_PATTERNS:
        if pattern in text:
            codes.append(reason)
            return


# ---------------------------------------------------------------------------
# Canonical JSON builder
# ---------------------------------------------------------------------------


def _build_canonical_json(input_data: ProductIterationInput) -> str:
    """Build a deterministic canonical JSON string from input data."""
    canonical = {
        "session_ref": input_data.session_ref,
        "started_at": input_data.started_at,
        "ended_at": input_data.ended_at,
        "screen_time_seconds": input_data.screen_time_seconds,
        "active_time_seconds": input_data.active_time_seconds,
        "idle_time_seconds": input_data.idle_time_seconds,
        "run_refs": sorted(input_data.run_refs),
        "feedback_refs": sorted(input_data.feedback_refs),
        "confusion_refs": sorted(input_data.confusion_refs),
        "report_refs": sorted(input_data.report_refs),
        "decision_trace_refs": sorted(input_data.decision_trace_refs),
        "human_iteration_note": input_data.human_iteration_note,
        "source_surface": input_data.source_surface,
        "product_signal_status": input_data.product_signal_status,
    }
    return json.dumps(canonical, sort_keys=True, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Record product iteration signal
# ---------------------------------------------------------------------------


def record_product_iteration_signal(
    input_data: ProductIterationInput,
) -> ProductIterationResult:
    """Record a product iteration signal.

    Parameters
    ----------
    input_data:
        Input parameters including session ref, screen-time data,
        run/feedback/confusion/report/decision-trace refs, and
        human iteration note.

    Returns
    -------
    ProductIterationResult
        ``status="recorded"`` with ``record`` and ``iteration_ref``
        when the signal is recorded.
        ``status="rejected"`` with ``reason_codes`` when validation fails.
    """
    codes: list[str] = []

    # 1. Validate required fields
    if not input_data.session_ref or input_data.session_ref.strip() == "":
        codes.append(REASON_MISSING_SESSION_REF)

    if codes:
        codes.sort()
        detail_lines = [f"  - {c}" for c in codes]
        details = "Product iteration signal rejected:\n" + "\n".join(detail_lines)
        return ProductIterationResult(
            status=ProductIterationStatus.REJECTED,
            reason_codes=tuple(codes),
            details=details,
        )

    # 2. Validate store path
    _check_store_path(input_data.store_dir, codes)

    # 3. Check for forbidden patterns in text fields
    text_fields = [input_data.human_iteration_note]
    for text in text_fields:
        _check_hidden_reasoning(text, codes)
        _check_external_url_only(text, codes)
        _check_forbidden_actions(text, codes)
        _check_forbidden_mutation(text, codes)

    if codes:
        codes.sort()
        detail_lines = [f"  - {c}" for c in codes]
        details = "Product iteration signal rejected:\n" + "\n".join(detail_lines)
        return ProductIterationResult(
            status=ProductIterationStatus.REJECTED,
            reason_codes=tuple(codes),
            details=details,
        )

    # 4. Build canonical JSON and derive iteration_ref
    canonical = _build_canonical_json(input_data)
    iteration_ref = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]

    # 5. Check payload size
    payload_bytes = canonical.encode("utf-8")
    if len(payload_bytes) > _MAX_PAYLOAD_BYTES:
        codes.append(REASON_OVERSIZED_PAYLOAD)
        codes.sort()
        detail_lines = [f"  - {c}" for c in codes]
        details = "Product iteration signal rejected:\n" + "\n".join(detail_lines)
        return ProductIterationResult(
            status=ProductIterationStatus.REJECTED,
            reason_codes=tuple(codes),
            details=details,
        )

    # 6. Ensure store directory exists
    store_path = input_data.store_dir.strip()
    os.makedirs(store_path, exist_ok=True)

    # 7. Check for duplicate
    record_file = os.path.join(store_path, f"{iteration_ref}.json")
    if os.path.exists(record_file):
        return ProductIterationResult(
            status=ProductIterationStatus.REJECTED,
            reason_codes=(REASON_DUPLICATE_ITERATION_REF,),
            iteration_ref=iteration_ref,
            details=f"Iteration {iteration_ref} already exists.",
        )

    # 8. Build record
    record = ProductIterationRecord(
        iteration_ref=iteration_ref,
        session_ref=input_data.session_ref,
        started_at=input_data.started_at,
        ended_at=input_data.ended_at,
        screen_time_seconds=input_data.screen_time_seconds,
        active_time_seconds=input_data.active_time_seconds,
        idle_time_seconds=input_data.idle_time_seconds,
        run_refs=tuple(sorted(input_data.run_refs)),
        feedback_refs=tuple(sorted(input_data.feedback_refs)),
        confusion_refs=tuple(sorted(input_data.confusion_refs)),
        report_refs=tuple(sorted(input_data.report_refs)),
        decision_trace_refs=tuple(sorted(input_data.decision_trace_refs)),
        human_iteration_note=input_data.human_iteration_note,
        product_signal_status=input_data.product_signal_status,
        created_at=None,
        source_surface=input_data.source_surface,
        schema_version="1",
    )

    # 9. Write record JSON
    record_dict = {
        "iteration_ref": record.iteration_ref,
        "session_ref": record.session_ref,
        "started_at": record.started_at,
        "ended_at": record.ended_at,
        "screen_time_seconds": record.screen_time_seconds,
        "active_time_seconds": record.active_time_seconds,
        "idle_time_seconds": record.idle_time_seconds,
        "run_refs": list(record.run_refs),
        "feedback_refs": list(record.feedback_refs),
        "confusion_refs": list(record.confusion_refs),
        "report_refs": list(record.report_refs),
        "decision_trace_refs": list(record.decision_trace_refs),
        "human_iteration_note": record.human_iteration_note,
        "product_signal_status": record.product_signal_status,
        "created_at": record.created_at,
        "source_surface": record.source_surface,
        "schema_version": record.schema_version,
    }
    record_json = json.dumps(record_dict, sort_keys=True, ensure_ascii=False, indent=2)

    with open(record_file, "w", encoding="utf-8") as f:
        f.write(record_json)

    return ProductIterationResult(
        status=ProductIterationStatus.RECORDED,
        record=record,
        iteration_ref=iteration_ref,
    )


# ---------------------------------------------------------------------------
# List product iteration signals
# ---------------------------------------------------------------------------


def list_product_iteration_signals(
    store_dir: str = ".ariadne/product-iterations",
    session_ref: Optional[str] = None,
    max_results: int = 100,
) -> ProductIterationResult:
    """List product iteration signals from the store.

    Parameters
    ----------
    store_dir:
        Directory for product iteration signal persistence.
    session_ref:
        Optional session ref to filter by.
    max_results:
        Maximum number of results to return.

    Returns
    -------
    ProductIterationResult
        ``status="recorded"`` with ``records`` and ``total_count``
        when signals are found.
        ``status="empty"`` when no signals match.
        ``status="rejected"`` with ``reason_codes`` when validation fails.
    """
    codes: list[str] = []

    # 1. Validate store path
    _check_store_path(store_dir, codes)

    if codes:
        codes.sort()
        detail_lines = [f"  - {c}" for c in codes]
        details = "Product iteration list rejected:\n" + "\n".join(detail_lines)
        return ProductIterationResult(
            status=ProductIterationStatus.REJECTED,
            reason_codes=tuple(codes),
            details=details,
        )

    # 2. Check store exists
    if not os.path.exists(store_dir):
        return ProductIterationResult(
            status=ProductIterationStatus.EMPTY,
            records=(),
            total_count=0,
        )

    if not os.path.isdir(store_dir):
        return ProductIterationResult(
            status=ProductIterationStatus.REJECTED,
            reason_codes=(REASON_UNBOUNDED_STORE_PATH,),
            details="Store path is not a directory.",
        )

    # 3. Enumerate JSON files
    try:
        json_files = sorted([
            f for f in os.listdir(store_dir)
            if f.endswith(".json")
        ])
    except OSError:
        return ProductIterationResult(
            status=ProductIterationStatus.EMPTY,
            records=(),
            total_count=0,
        )

    if not json_files:
        return ProductIterationResult(
            status=ProductIterationStatus.EMPTY,
            records=(),
            total_count=0,
        )

    # 4. Load records
    records: list[ProductIterationRecord] = []

    for filename in json_files:
        filepath = os.path.join(store_dir, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                raw = f.read()
        except OSError:
            continue

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue

        if not isinstance(data, dict):
            continue

        iteration_ref = data.get("iteration_ref", "")
        if not iteration_ref:
            continue

        record = ProductIterationRecord(
            iteration_ref=iteration_ref,
            session_ref=data.get("session_ref", ""),
            started_at=data.get("started_at"),
            ended_at=data.get("ended_at"),
            screen_time_seconds=data.get("screen_time_seconds", 0),
            active_time_seconds=data.get("active_time_seconds", 0),
            idle_time_seconds=data.get("idle_time_seconds", 0),
            run_refs=tuple(data.get("run_refs", [])),
            feedback_refs=tuple(data.get("feedback_refs", [])),
            confusion_refs=tuple(data.get("confusion_refs", [])),
            report_refs=tuple(data.get("report_refs", [])),
            decision_trace_refs=tuple(data.get("decision_trace_refs", [])),
            human_iteration_note=data.get("human_iteration_note", ""),
            product_signal_status=data.get("product_signal_status", "recorded"),
            created_at=None,
            source_surface=data.get("source_surface", "task_intake"),
            schema_version=data.get("schema_version", "1"),
        )
        records.append(record)

    # 5. Apply session_ref filter
    if session_ref is not None:
        records = [r for r in records if r.session_ref == session_ref]

    if not records:
        return ProductIterationResult(
            status=ProductIterationStatus.EMPTY,
            records=(),
            total_count=0,
        )

    # 6. Sort by iteration_ref (deterministic)
    records.sort(key=lambda r: r.iteration_ref)

    # 7. Cap at max_results
    max_results = min(max_results, _MAX_LIST_RESULTS)
    if len(records) > max_results:
        records = records[:max_results]

    return ProductIterationResult(
        status=ProductIterationStatus.RECORDED,
        records=tuple(records),
        total_count=len(records),
    )
