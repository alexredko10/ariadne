"""
Deterministic local self-improvement backlog store / local queue for Ariadne.

Defines ``BacklogItemInput``, ``BacklogItem``, ``BacklogResult``,
``BacklogStatus``, ``BacklogCategory``, and the functions
``enqueue_backlog_item()``, ``list_backlog()``, ``archive_backlog_item()``.

Core principle:
    Ariadne may propose and store improvement candidates for human review.
    Ariadne must not autonomously edit code, mutate git state, create
    commits, create PRs, approve gates, finalize gates, call providers,
    run shell commands, or repair itself without a human-reviewed
    implementation PR.
"""

from __future__ import annotations

import dataclasses
import enum
import hashlib
import json
import os
from typing import Optional, Tuple


# ---------------------------------------------------------------------------
# BacklogStatus — lifecycle states
# ---------------------------------------------------------------------------


class BacklogStatus(str, enum.Enum):
    """Lifecycle status for a backlog item."""

    NEW = "new"
    HUMAN_REVIEW = "human_review"
    ARCHIVED = "archived"
    REJECTED = "rejected"


# Valid transitions: NEW → HUMAN_REVIEW → ARCHIVED | REJECTED
_VALID_TRANSITIONS: dict[BacklogStatus, tuple[BacklogStatus, ...]] = {
    BacklogStatus.NEW: (BacklogStatus.HUMAN_REVIEW, BacklogStatus.ARCHIVED, BacklogStatus.REJECTED),
    BacklogStatus.HUMAN_REVIEW: (BacklogStatus.ARCHIVED, BacklogStatus.REJECTED),
    BacklogStatus.ARCHIVED: (),
    BacklogStatus.REJECTED: (),
}


# ---------------------------------------------------------------------------
# BacklogCategory — deterministic category mapping
# ---------------------------------------------------------------------------


class BacklogCategory(str, enum.Enum):
    """Deterministic backlog category."""

    SELF_IMPROVEMENT = "self_improvement"
    CONTINUITY_FOLLOWUP = "continuity_followup"
    DRIFT_RISK = "drift_risk"
    VALIDATION_GAP = "validation_gap"
    FRONTEND_VISIBILITY_GAP = "frontend_visibility_gap"
    HUMAN_REVIEW_REQUIRED = "human_review_required"


# ---------------------------------------------------------------------------
# BacklogItemInput — input parameters
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class BacklogItemInput:
    """Input parameters for enqueuing a backlog item."""

    candidate_ref: str  # candidate_id from PR 0107
    continuity_ref: str = ""  # continuity_ref from PR 0108 (optional)
    product_state_ref: str = ""
    source_reason_codes: Tuple[str, ...] = ()
    evidence_refs: Tuple[str, ...] = ()
    improvement_category: str = ""  # ImprovementCategory or BacklogCategory value
    next_safe_action: str = ""
    blocked_actions: Tuple[str, ...] = ()
    drift_risks: Tuple[str, ...] = ()
    requires_human_review: bool = True
    phase_id: str = ""
    run_id: str = ""
    output_path: str = ""  # for artifact output
    session_label: str = ""


# ---------------------------------------------------------------------------
# BacklogItem — output item object
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class BacklogItem:
    """A single backlog item in the self-improvement backlog store."""

    backlog_item_ref: str  # first 16 hex chars of SHA256(canonical JSON)
    candidate_ref: str
    continuity_ref: str
    product_state_ref: str
    source_reason_codes: Tuple[str, ...]
    evidence_refs: Tuple[str, ...]
    improvement_category: str
    next_safe_action: str
    blocked_actions: Tuple[str, ...]
    drift_risks: Tuple[str, ...]
    requires_human_review: bool
    status: str  # BacklogStatus value
    phase_id: str
    run_id: str
    session_label: str
    created_at: None  # deterministic; no wall-clock time
    archived_at: Optional[None] = None  # deterministic; no wall-clock time


# ---------------------------------------------------------------------------
# BacklogResult — operation result
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class BacklogResult:
    """Result of a backlog operation."""

    status: str  # "enqueued" | "duplicate" | "archived" | "rejected" | "listed"
    reason_codes: Tuple[str, ...] = ()
    backlog_item: Optional[BacklogItem] = None
    backlog_items: Tuple[BacklogItem, ...] = ()  # for list operation
    artifact_path: Optional[str] = None
    total_count: int = 0
    details: Optional[str] = None


# ---------------------------------------------------------------------------
# Stable reason codes
# ---------------------------------------------------------------------------

REASON_MISSING_CANDIDATE_REF = "missing_candidate_ref"
REASON_MISSING_PRODUCT_STATE_REF = "missing_product_state_ref"
REASON_MISSING_EVIDENCE_REFS = "missing_evidence_refs"
REASON_MISSING_NEXT_SAFE_ACTION = "missing_next_safe_action"
REASON_MISSING_HUMAN_REVIEW_BOUNDARY = "missing_human_review_boundary"
REASON_DUPLICATE_CANDIDATE = "duplicate_candidate"
REASON_INVALID_BACKLOG_STATUS = "invalid_backlog_status"
REASON_INVALID_BACKLOG_ITEM = "invalid_backlog_item"
REASON_HIDDEN_REASONING_NOT_ALLOWED = "hidden_reasoning_not_allowed"
REASON_EXTERNAL_URL_ONLY_NOT_ALLOWED = "external_url_only_not_allowed"
REASON_UNBOUNDED_BACKLOG_OUTPUT_PATH = "unbounded_backlog_output_path"
REASON_OVERSIZED_BACKLOG_ITEM = "oversized_backlog_item"
REASON_AUTONOMOUS_CODE_CHANGE_NOT_ALLOWED = "autonomous_code_change_not_allowed"
REASON_GIT_MUTATION_NOT_ALLOWED = "git_mutation_not_allowed"
REASON_PROVIDER_CALL_NOT_ALLOWED = "provider_call_not_allowed"
REASON_COMMAND_EXECUTION_NOT_ALLOWED = "command_execution_not_allowed"

# ---------------------------------------------------------------------------
# Forbidden hidden reasoning patterns
# ---------------------------------------------------------------------------

_FORBIDDEN_HIDDEN_REASONING_PATTERNS: Tuple[str, ...] = (
    "<cot>",
    "<chain_of_thought>",
    "hidden_reasoning",
)

# ---------------------------------------------------------------------------
# Forbidden action patterns
# ---------------------------------------------------------------------------

_FORBIDDEN_ACTION_PATTERNS: Tuple[Tuple[str, str], ...] = (
    ("git commit", REASON_GIT_MUTATION_NOT_ALLOWED),
    ("git push", REASON_GIT_MUTATION_NOT_ALLOWED),
    ("git merge", REASON_GIT_MUTATION_NOT_ALLOWED),
    ("git rebase", REASON_GIT_MUTATION_NOT_ALLOWED),
    ("import openai", REASON_PROVIDER_CALL_NOT_ALLOWED),
    ("import anthropic", REASON_PROVIDER_CALL_NOT_ALLOWED),
    ("from openai", REASON_PROVIDER_CALL_NOT_ALLOWED),
    ("from anthropic", REASON_PROVIDER_CALL_NOT_ALLOWED),
    ("pip install", REASON_AUTONOMOUS_CODE_CHANGE_NOT_ALLOWED),
    ("npm install", REASON_AUTONOMOUS_CODE_CHANGE_NOT_ALLOWED),
    ("subprocess.run", REASON_COMMAND_EXECUTION_NOT_ALLOWED),
    ("subprocess.Popen", REASON_COMMAND_EXECUTION_NOT_ALLOWED),
    ("os.system", REASON_COMMAND_EXECUTION_NOT_ALLOWED),
)

# ---------------------------------------------------------------------------
# Bounds
# ---------------------------------------------------------------------------

_MAX_CANDIDATE_REF_LENGTH = 64
_MAX_CONTINUITY_REF_LENGTH = 64
_MAX_PRODUCT_STATE_REF_LENGTH = 256
_MAX_REASON_CODE_LENGTH = 128
_MAX_EVIDENCE_REF_LENGTH = 256
_MAX_CATEGORY_LENGTH = 64
_MAX_NEXT_SAFE_ACTION_LENGTH = 4096
_MAX_BLOCKED_ACTION_LENGTH = 2048
_MAX_DRIFT_RISK_LENGTH = 2048
_MAX_PHASE_ID_LENGTH = 128
_MAX_RUN_ID_LENGTH = 128
_MAX_OUTPUT_PATH_LENGTH = 255
_MAX_SESSION_LABEL_LENGTH = 256

# ---------------------------------------------------------------------------
# Artifact constants
# ---------------------------------------------------------------------------

_ARIADNE_BACKLOG_VERSION = "1"


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _check_non_empty_stripped(value: str, max_len: int, reason: str, codes: list[str]) -> None:
    """Append *reason* to *codes* if *value* is empty or whitespace-only."""
    if not value or value.strip() == "":
        codes.append(reason)
    elif len(value) > max_len:
        codes.append(reason)


def _check_output_path(output_path: str, codes: list[str]) -> None:
    """Validate output path boundedness."""
    if not output_path or output_path.strip() == "":
        codes.append(REASON_UNBOUNDED_BACKLOG_OUTPUT_PATH)
        return

    path = output_path.strip()

    if len(path) > _MAX_OUTPUT_PATH_LENGTH:
        codes.append(REASON_UNBOUNDED_BACKLOG_OUTPUT_PATH)
        return

    if path.startswith("/"):
        codes.append(REASON_UNBOUNDED_BACKLOG_OUTPUT_PATH)
        return

    if ".." in path.split("/"):
        codes.append(REASON_UNBOUNDED_BACKLOG_OUTPUT_PATH)
        return


def _check_hidden_reasoning(text: str, codes: list[str]) -> None:
    """Check for hidden reasoning patterns in text."""
    for pattern in _FORBIDDEN_HIDDEN_REASONING_PATTERNS:
        if pattern in text:
            codes.append(REASON_HIDDEN_REASONING_NOT_ALLOWED)
            return


def _check_external_url_only(text: str, codes: list[str]) -> None:
    """Check if text is only a URL."""
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


def _check_tuple_non_empty_stripped(
    values: Tuple[str, ...],
    max_len: int,
    reason: str,
    codes: list[str],
) -> None:
    """Validate each entry in a tuple is non-empty and within bounds."""
    for v in values:
        if not v or v.strip() == "":
            codes.append(reason)
            return
        if len(v) > max_len:
            codes.append(reason)
            return


# ---------------------------------------------------------------------------
# Enqueue backlog item
# ---------------------------------------------------------------------------


def enqueue_backlog_item(
    input_data: BacklogItemInput,
    backlog_store_dir: str = ".ariadne/backlog",
    output_dir: str = ".",
) -> BacklogResult:
    """Enqueue a backlog item from explicit structured input.

    Parameters
    ----------
    input_data:
        The input parameters for the backlog item.
    backlog_store_dir:
        Directory for durable backlog persistence. Defaults to
        ``.ariadne/backlog``.
    output_dir:
        Directory where the item artifact will be written. Defaults to
        the current working directory.

    Returns
    -------
    BacklogResult
        ``status="enqueued"`` with ``backlog_item`` and ``artifact_path``
        when the item is enqueued. ``status="duplicate"`` when the same
        item already exists. ``status="rejected"`` with ``reason_codes``
        when validation fails.
    """
    codes: list[str] = []

    # 1. Candidate ref
    _check_non_empty_stripped(
        input_data.candidate_ref,
        _MAX_CANDIDATE_REF_LENGTH,
        REASON_MISSING_CANDIDATE_REF,
        codes,
    )

    # 2. Product state ref
    _check_non_empty_stripped(
        input_data.product_state_ref,
        _MAX_PRODUCT_STATE_REF_LENGTH,
        REASON_MISSING_PRODUCT_STATE_REF,
        codes,
    )

    # 3. Evidence refs
    if not input_data.evidence_refs:
        codes.append(REASON_MISSING_EVIDENCE_REFS)
    else:
        _check_tuple_non_empty_stripped(
            input_data.evidence_refs,
            _MAX_EVIDENCE_REF_LENGTH,
            REASON_MISSING_EVIDENCE_REFS,
            codes,
        )

    # 4. Next safe action
    _check_non_empty_stripped(
        input_data.next_safe_action,
        _MAX_NEXT_SAFE_ACTION_LENGTH,
        REASON_MISSING_NEXT_SAFE_ACTION,
        codes,
    )
    if input_data.next_safe_action and input_data.next_safe_action.strip() and len(input_data.next_safe_action) > _MAX_NEXT_SAFE_ACTION_LENGTH:
        if REASON_MISSING_NEXT_SAFE_ACTION in codes:
            codes.remove(REASON_MISSING_NEXT_SAFE_ACTION)
        codes.append(REASON_OVERSIZED_BACKLOG_ITEM)
    _check_hidden_reasoning(input_data.next_safe_action, codes)
    _check_external_url_only(input_data.next_safe_action, codes)
    _check_forbidden_actions(input_data.next_safe_action, codes)

    # 5. Human review boundary
    if not input_data.requires_human_review:
        codes.append(REASON_MISSING_HUMAN_REVIEW_BOUNDARY)

    # 6. Source reason codes bounds
    _check_tuple_non_empty_stripped(
        input_data.source_reason_codes,
        _MAX_REASON_CODE_LENGTH,
        REASON_OVERSIZED_BACKLOG_ITEM,
        codes,
    )

    # 7. Blocked actions bounds
    _check_tuple_non_empty_stripped(
        input_data.blocked_actions,
        _MAX_BLOCKED_ACTION_LENGTH,
        REASON_OVERSIZED_BACKLOG_ITEM,
        codes,
    )

    # 8. Drift risks bounds
    _check_tuple_non_empty_stripped(
        input_data.drift_risks,
        _MAX_DRIFT_RISK_LENGTH,
        REASON_OVERSIZED_BACKLOG_ITEM,
        codes,
    )

    # 9. Output path
    _check_output_path(input_data.output_path, codes)

    # 10. Session label bounds
    if len(input_data.session_label) > _MAX_SESSION_LABEL_LENGTH:
        codes.append(REASON_OVERSIZED_BACKLOG_ITEM)

    # --- Deterministic sort ---
    codes.sort()

    if codes:
        detail_lines = [f"  - {c}" for c in codes]
        details = "Backlog item rejected:\n" + "\n".join(detail_lines)
        return BacklogResult(
            status="rejected",
            reason_codes=tuple(codes),
            details=details,
        )

    # --- Build canonical item JSON ---
    sorted_reason_codes = sorted(input_data.source_reason_codes)
    sorted_evidence_refs = sorted(input_data.evidence_refs)
    sorted_blocked_actions = sorted(input_data.blocked_actions)
    sorted_drift_risks = sorted(input_data.drift_risks)

    item_dict = {
        "ariadne_backlog_version": _ARIADNE_BACKLOG_VERSION,
        "candidate_ref": input_data.candidate_ref,
        "continuity_ref": input_data.continuity_ref,
        "product_state_ref": input_data.product_state_ref,
        "source_reason_codes": sorted_reason_codes,
        "evidence_refs": sorted_evidence_refs,
        "improvement_category": input_data.improvement_category,
        "next_safe_action": input_data.next_safe_action,
        "blocked_actions": sorted_blocked_actions,
        "drift_risks": sorted_drift_risks,
        "requires_human_review": input_data.requires_human_review,
        "status": BacklogStatus.NEW.value,
        "phase_id": input_data.phase_id,
        "run_id": input_data.run_id,
        "session_label": input_data.session_label,
        "created_at": None,  # deterministic; no wall-clock time
        "archived_at": None,
    }

    # Derive backlog_item_ref from SHA256 of canonical JSON (first 16 hex chars)
    item_json = json.dumps(item_dict, sort_keys=True, indent=2)
    backlog_item_ref = hashlib.sha256(item_json.encode("utf-8")).hexdigest()[:16]

    # Add backlog_item_ref to the dict
    item_dict["backlog_item_ref"] = backlog_item_ref

    # Re-serialize with backlog_item_ref included
    item_json = json.dumps(item_dict, sort_keys=True, indent=2)

    # Check for duplicate in backlog store
    backlog_store_path = os.path.abspath(backlog_store_dir)
    store_file = os.path.join(backlog_store_path, f"{backlog_item_ref}.json")
    if os.path.exists(store_file):
        return BacklogResult(
            status="duplicate",
            reason_codes=(REASON_DUPLICATE_CANDIDATE,),
            details=f"Backlog item {backlog_item_ref} already exists in store",
        )

    # Build BacklogItem object
    backlog_item = BacklogItem(
        backlog_item_ref=backlog_item_ref,
        candidate_ref=input_data.candidate_ref,
        continuity_ref=input_data.continuity_ref,
        product_state_ref=input_data.product_state_ref,
        source_reason_codes=tuple(sorted_reason_codes),
        evidence_refs=tuple(sorted_evidence_refs),
        improvement_category=input_data.improvement_category,
        next_safe_action=input_data.next_safe_action,
        blocked_actions=tuple(sorted_blocked_actions),
        drift_risks=tuple(sorted_drift_risks),
        requires_human_review=input_data.requires_human_review,
        status=BacklogStatus.NEW.value,
        phase_id=input_data.phase_id,
        run_id=input_data.run_id,
        session_label=input_data.session_label,
        created_at=None,
        archived_at=None,
    )

    # Normalize output path
    output_path = input_data.output_path.strip()
    full_path = os.path.join(output_dir, output_path)

    # Ensure parent directory exists
    parent_dir = os.path.dirname(full_path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)

    # Write artifact
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(item_json)

    # Ensure backlog store directory exists
    os.makedirs(backlog_store_path, exist_ok=True)

    # Copy to backlog store
    store_file = os.path.join(backlog_store_path, f"{backlog_item_ref}.json")
    with open(store_file, "w", encoding="utf-8") as f:
        f.write(item_json)

    return BacklogResult(
        status="enqueued",
        reason_codes=(),
        backlog_item=backlog_item,
        artifact_path=output_path,
        total_count=1,
        details=None,
    )


# ---------------------------------------------------------------------------
# List backlog items
# ---------------------------------------------------------------------------


def list_backlog(
    backlog_store_dir: str = ".ariadne/backlog",
    status_filter: Optional[str] = None,
) -> BacklogResult:
    """List backlog items from the durable store.

    Parameters
    ----------
    backlog_store_dir:
        Directory for durable backlog persistence. Defaults to
        ``.ariadne/backlog``.
    status_filter:
        Optional status to filter by (``"new"``, ``"human_review"``,
        ``"archived"``, ``"rejected"``).

    Returns
    -------
    BacklogResult
        ``status="listed"`` with ``backlog_items`` and ``total_count``.
    """
    backlog_store_path = os.path.abspath(backlog_store_dir)

    if not os.path.isdir(backlog_store_path):
        return BacklogResult(
            status="listed",
            backlog_items=(),
            total_count=0,
        )

    items: list[BacklogItem] = []
    try:
        filenames = sorted(os.listdir(backlog_store_path))
    except OSError:
        return BacklogResult(
            status="listed",
            backlog_items=(),
            total_count=0,
        )

    for filename in filenames:
        if not filename.endswith(".json"):
            continue
        filepath = os.path.join(backlog_store_path, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        # Parse as BacklogItem
        try:
            item = BacklogItem(
                backlog_item_ref=data.get("backlog_item_ref", ""),
                candidate_ref=data.get("candidate_ref", ""),
                continuity_ref=data.get("continuity_ref", ""),
                product_state_ref=data.get("product_state_ref", ""),
                source_reason_codes=tuple(data.get("source_reason_codes", [])),
                evidence_refs=tuple(data.get("evidence_refs", [])),
                improvement_category=data.get("improvement_category", ""),
                next_safe_action=data.get("next_safe_action", ""),
                blocked_actions=tuple(data.get("blocked_actions", [])),
                drift_risks=tuple(data.get("drift_risks", [])),
                requires_human_review=data.get("requires_human_review", True),
                status=data.get("status", BacklogStatus.NEW.value),
                phase_id=data.get("phase_id", ""),
                run_id=data.get("run_id", ""),
                session_label=data.get("session_label", ""),
                created_at=None,
                archived_at=None,
            )
        except (TypeError, ValueError):
            continue

        # Apply status filter
        if status_filter is not None and item.status != status_filter:
            continue

        items.append(item)

    # Sort by backlog_item_ref (deterministic)
    items.sort(key=lambda i: i.backlog_item_ref)

    return BacklogResult(
        status="listed",
        backlog_items=tuple(items),
        total_count=len(items),
    )


# ---------------------------------------------------------------------------
# Archive backlog item
# ---------------------------------------------------------------------------


def archive_backlog_item(
    backlog_item_ref: str,
    target_status: str = "archived",
    backlog_store_dir: str = ".ariadne/backlog",
) -> BacklogResult:
    """Archive or reject a backlog item.

    Parameters
    ----------
    backlog_item_ref:
        The ref of the backlog item to archive.
    target_status:
        Target status: ``"archived"`` or ``"rejected"``.
    backlog_store_dir:
        Directory for durable backlog persistence. Defaults to
        ``.ariadne/backlog``.

    Returns
    -------
    BacklogResult
        ``status="archived"`` or ``status="rejected"`` with the updated
        ``backlog_item`` when successful. ``status="rejected"`` with
        ``reason_codes`` when validation fails.
    """
    codes: list[str] = []

    # Validate target_status
    if target_status not in ("archived", "rejected"):
        codes.append(REASON_INVALID_BACKLOG_STATUS)

    # Validate backlog_item_ref
    if not backlog_item_ref or backlog_item_ref.strip() == "":
        codes.append(REASON_INVALID_BACKLOG_ITEM)

    if codes:
        codes.sort()
        detail_lines = [f"  - {c}" for c in codes]
        details = "Archive operation rejected:\n" + "\n".join(detail_lines)
        return BacklogResult(
            status="rejected",
            reason_codes=tuple(codes),
            details=details,
        )

    # Read from backlog store
    backlog_store_path = os.path.abspath(backlog_store_dir)
    store_file = os.path.join(backlog_store_path, f"{backlog_item_ref}.json")

    if not os.path.exists(store_file):
        return BacklogResult(
            status="rejected",
            reason_codes=(REASON_INVALID_BACKLOG_ITEM,),
            details=f"Backlog item {backlog_item_ref} not found in store",
        )

    try:
        with open(store_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return BacklogResult(
            status="rejected",
            reason_codes=(REASON_INVALID_BACKLOG_ITEM,),
            details=f"Failed to read backlog item {backlog_item_ref}",
        )

    # Parse current status
    current_status_str = data.get("status", BacklogStatus.NEW.value)
    try:
        current_status = BacklogStatus(current_status_str)
    except ValueError:
        return BacklogResult(
            status="rejected",
            reason_codes=(REASON_INVALID_BACKLOG_STATUS,),
            details=f"Invalid current status: {current_status_str}",
        )

    # Validate transition
    target_enum = BacklogStatus(target_status)
    allowed = _VALID_TRANSITIONS.get(current_status, ())
    if target_enum not in allowed:
        return BacklogResult(
            status="rejected",
            reason_codes=(REASON_INVALID_BACKLOG_STATUS,),
            details=f"Invalid transition: {current_status.value} → {target_status}",
        )

    # Update status
    data["status"] = target_status
    data["archived_at"] = None  # deterministic

    # Re-serialize
    updated_json = json.dumps(data, sort_keys=True, indent=2)

    # Write back to store
    with open(store_file, "w", encoding="utf-8") as f:
        f.write(updated_json)

    # Build updated BacklogItem
    updated_item = BacklogItem(
        backlog_item_ref=data.get("backlog_item_ref", backlog_item_ref),
        candidate_ref=data.get("candidate_ref", ""),
        continuity_ref=data.get("continuity_ref", ""),
        product_state_ref=data.get("product_state_ref", ""),
        source_reason_codes=tuple(data.get("source_reason_codes", [])),
        evidence_refs=tuple(data.get("evidence_refs", [])),
        improvement_category=data.get("improvement_category", ""),
        next_safe_action=data.get("next_safe_action", ""),
        blocked_actions=tuple(data.get("blocked_actions", [])),
        drift_risks=tuple(data.get("drift_risks", [])),
        requires_human_review=data.get("requires_human_review", True),
        status=target_status,
        phase_id=data.get("phase_id", ""),
        run_id=data.get("run_id", ""),
        session_label=data.get("session_label", ""),
        created_at=None,
        archived_at=None,
    )

    return BacklogResult(
        status=target_status,
        reason_codes=(),
        backlog_item=updated_item,
        details=None,
    )
