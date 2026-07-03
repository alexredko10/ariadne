"""
Human backlog decision intake layer for Ariadne.

Records explicit human decisions about backlog items as separate local
decision evidence records in ``.ariadne/decisions/``.

Core principle:
    A decision record is evidence of a human choice.
    A decision record must not mutate the backlog item it references.
    Recording a decision is allowed only when it records human intent.
    It must not perform the intent.
"""

from __future__ import annotations

import dataclasses
import enum
import hashlib
import json
import os
from typing import Optional

from runner.improvement_backlog import (
    _FORBIDDEN_HIDDEN_REASONING_PATTERNS,
    _FORBIDDEN_ACTION_PATTERNS,
)


# ---------------------------------------------------------------------------
# BacklogDecisionType — stable decision types
# ---------------------------------------------------------------------------


class BacklogDecisionType(str, enum.Enum):
    """Stable decision types for human backlog decisions."""

    NEEDS_MORE_EVIDENCE = "needs_more_evidence"
    DEFER = "defer"
    DISMISS = "dismiss"
    CANDIDATE_FOR_FUTURE_PR = "candidate_for_future_pr"
    ACCEPT_FOR_HUMAN_PLANNING = "accept_for_human_planning"


# ---------------------------------------------------------------------------
# BacklogDecisionInput — input parameters
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class BacklogDecisionInput:
    """Input parameters for recording a human backlog decision."""

    backlog_item_ref: str  # Required — ref of the backlog item
    decision_type: str  # BacklogDecisionType value
    human_actor: str  # Human identifier or label
    decision_reason: str  # Free-text reason for the decision
    decision_store_dir: str = ".ariadne/decisions"
    evidence_refs: tuple[str, ...] = ()
    next_human_action: str = ""
    candidate_ref: str = ""
    continuity_ref: str = ""


# ---------------------------------------------------------------------------
# BacklogDecisionRecord — immutable decision record
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class BacklogDecisionRecord:
    """An immutable record of a human backlog decision."""

    decision_ref: str
    backlog_item_ref: str
    decision_type: str
    human_actor: str
    decision_reason: str
    evidence_refs: tuple[str, ...]
    next_human_action: str
    candidate_ref: str
    continuity_ref: str
    created_at: None = None  # deterministic; no wall-clock time


# ---------------------------------------------------------------------------
# BacklogDecisionResult — operation result
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class BacklogDecisionResult:
    """Result of a human decision recording operation."""

    status: str  # "recorded" | "rejected" | "duplicate"
    reason_codes: tuple[str, ...] = ()
    decision_record: Optional[BacklogDecisionRecord] = None
    decision_ref: Optional[str] = None
    details: Optional[str] = None


# ---------------------------------------------------------------------------
# Stable reason codes
# ---------------------------------------------------------------------------

REASON_MISSING_BACKLOG_ITEM_REF = "missing_backlog_item_ref"
REASON_INVALID_DECISION_TYPE = "invalid_decision_type"
REASON_MISSING_HUMAN_ACTOR = "missing_human_actor"
REASON_MISSING_DECISION_REASON = "missing_decision_reason"
REASON_HIDDEN_REASONING_NOT_ALLOWED = "hidden_reasoning_not_allowed"
REASON_EXTERNAL_URL_ONLY_NOT_ALLOWED = "external_url_only_not_allowed"
REASON_MUTATION_NOT_ALLOWED = "mutation_not_allowed"
REASON_ARCHIVE_NOT_ALLOWED = "archive_not_allowed"
REASON_APPROVAL_NOT_ALLOWED = "approval_not_allowed"
REASON_GATE_FINALIZATION_NOT_ALLOWED = "gate_finalization_not_allowed"
REASON_COMMAND_EXECUTION_NOT_ALLOWED = "command_execution_not_allowed"
REASON_PROVIDER_CALL_NOT_ALLOWED = "provider_call_not_allowed"
REASON_GIT_MUTATION_NOT_ALLOWED = "git_mutation_not_allowed"
REASON_DUPLICATE_DECISION_REF = "duplicate_decision_ref"
REASON_UNBOUNDED_DECISION_STORE_PATH = "unbounded_decision_store_path"
REASON_OVERSIZED_DECISION_PAYLOAD = "oversized_decision_payload"

# ---------------------------------------------------------------------------
# Forbidden patterns (decision-specific)
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

_MAX_DECISION_PAYLOAD_BYTES = 1024 * 100  # 100 KB


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _check_decision_store_path(decision_store_dir: str, codes: list[str]) -> None:
    """Validate decision store path boundedness."""
    if not decision_store_dir or decision_store_dir.strip() == "":
        codes.append(REASON_UNBOUNDED_DECISION_STORE_PATH)
        return

    path = decision_store_dir.strip()

    # Reject paths with parent-directory traversal
    if ".." in path.split("/"):
        codes.append(REASON_UNBOUNDED_DECISION_STORE_PATH)
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


def _build_canonical_json(input_data: BacklogDecisionInput) -> str:
    """Build a deterministic canonical JSON string from input data."""
    canonical = {
        "backlog_item_ref": input_data.backlog_item_ref,
        "decision_type": input_data.decision_type,
        "human_actor": input_data.human_actor,
        "decision_reason": input_data.decision_reason,
        "evidence_refs": sorted(input_data.evidence_refs),
        "next_human_action": input_data.next_human_action,
        "candidate_ref": input_data.candidate_ref,
        "continuity_ref": input_data.continuity_ref,
    }
    return json.dumps(canonical, sort_keys=True, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Record human decision
# ---------------------------------------------------------------------------


def record_human_decision(
    input_data: BacklogDecisionInput,
) -> BacklogDecisionResult:
    """Record a human decision about a backlog item.

    Parameters
    ----------
    input_data:
        Input parameters including backlog item ref, decision type,
        human actor, and decision reason.

    Returns
    -------
    BacklogDecisionResult
        ``status="recorded"`` with ``decision_record`` and ``decision_ref``
        when the decision is recorded.
        ``status="rejected"`` with ``reason_codes`` when validation fails.
        ``status="duplicate"`` when an identical decision already exists.
    """
    codes: list[str] = []

    # 1. Validate required fields
    if not input_data.backlog_item_ref or input_data.backlog_item_ref.strip() == "":
        codes.append(REASON_MISSING_BACKLOG_ITEM_REF)

    if not input_data.human_actor or input_data.human_actor.strip() == "":
        codes.append(REASON_MISSING_HUMAN_ACTOR)

    if not input_data.decision_reason or input_data.decision_reason.strip() == "":
        codes.append(REASON_MISSING_DECISION_REASON)

    # 2. Validate decision type
    valid_types = {t.value for t in BacklogDecisionType}
    if input_data.decision_type not in valid_types:
        codes.append(REASON_INVALID_DECISION_TYPE)

    if codes:
        codes.sort()
        detail_lines = [f"  - {c}" for c in codes]
        details = "Decision rejected:\n" + "\n".join(detail_lines)
        return BacklogDecisionResult(
            status="rejected",
            reason_codes=tuple(codes),
            details=details,
        )

    # 3. Validate decision store path
    _check_decision_store_path(input_data.decision_store_dir, codes)

    # 4. Check for forbidden patterns in text fields
    text_fields = [
        input_data.decision_reason,
        input_data.next_human_action,
    ]
    for text in text_fields:
        _check_hidden_reasoning(text, codes)
        _check_external_url_only(text, codes)
        _check_forbidden_actions(text, codes)
        _check_forbidden_mutation(text, codes)

    if codes:
        codes.sort()
        detail_lines = [f"  - {c}" for c in codes]
        details = "Decision rejected:\n" + "\n".join(detail_lines)
        return BacklogDecisionResult(
            status="rejected",
            reason_codes=tuple(codes),
            details=details,
        )

    # 5. Build canonical JSON and derive decision_ref
    canonical = _build_canonical_json(input_data)
    decision_ref = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]

    # 6. Check payload size
    payload_bytes = canonical.encode("utf-8")
    if len(payload_bytes) > _MAX_DECISION_PAYLOAD_BYTES:
        codes.append(REASON_OVERSIZED_DECISION_PAYLOAD)
        codes.sort()
        detail_lines = [f"  - {c}" for c in codes]
        details = "Decision rejected:\n" + "\n".join(detail_lines)
        return BacklogDecisionResult(
            status="rejected",
            reason_codes=tuple(codes),
            details=details,
        )

    # 7. Ensure decision store directory exists
    store_path = input_data.decision_store_dir.strip()
    os.makedirs(store_path, exist_ok=True)

    # 8. Check for duplicate
    decision_file = os.path.join(store_path, f"{decision_ref}.json")
    if os.path.exists(decision_file):
        return BacklogDecisionResult(
            status="duplicate",
            reason_codes=(REASON_DUPLICATE_DECISION_REF,),
            decision_ref=decision_ref,
            details=f"Decision {decision_ref} already exists.",
        )

    # 9. Build decision record
    record = BacklogDecisionRecord(
        decision_ref=decision_ref,
        backlog_item_ref=input_data.backlog_item_ref,
        decision_type=input_data.decision_type,
        human_actor=input_data.human_actor,
        decision_reason=input_data.decision_reason,
        evidence_refs=tuple(sorted(input_data.evidence_refs)),
        next_human_action=input_data.next_human_action,
        candidate_ref=input_data.candidate_ref,
        continuity_ref=input_data.continuity_ref,
        created_at=None,
    )

    # 10. Write decision record JSON
    record_dict = {
        "decision_ref": record.decision_ref,
        "backlog_item_ref": record.backlog_item_ref,
        "decision_type": record.decision_type,
        "human_actor": record.human_actor,
        "decision_reason": record.decision_reason,
        "evidence_refs": list(record.evidence_refs),
        "next_human_action": record.next_human_action,
        "candidate_ref": record.candidate_ref,
        "continuity_ref": record.continuity_ref,
        "created_at": record.created_at,
    }
    record_json = json.dumps(record_dict, sort_keys=True, ensure_ascii=False, indent=2)

    with open(decision_file, "w", encoding="utf-8") as f:
        f.write(record_json)

    return BacklogDecisionResult(
        status="recorded",
        decision_record=record,
        decision_ref=decision_ref,
    )
