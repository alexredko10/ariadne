"""
Deterministic local Session Continuity Packet for Ariadne.

Defines ``SessionContinuityInput``, ``SessionContinuityPacket``,
``SessionContinuityResult``, ``SessionContinuityStatus``, and
``build_session_continuity_packet()`` — a deterministic, local function
that produces a bounded, durable session continuity artifact.

Core principle:
    Ariadne must be able to say, from deterministic runtime evidence
    rather than model memory: where we are, what we were trying to do,
    what was already decided, what evidence exists, what is still blocked,
    what is deferred, what files are in scope, what files are out of scope,
    what would count as drift, what the next safe action is, and how a
    human or another agent should resume.
"""

from __future__ import annotations

import dataclasses
import enum
import hashlib
import json
import os
from typing import Optional, Tuple


# ---------------------------------------------------------------------------
# SessionContinuityStatus — final verdict
# ---------------------------------------------------------------------------


class SessionContinuityStatus(str, enum.Enum):
    """Final verdict for a session continuity packet operation."""

    CREATED = "created"
    REJECTED = "rejected"


# ---------------------------------------------------------------------------
# SessionContinuityInput — input parameters
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class SessionContinuityInput:
    """Input parameters for building a session continuity packet."""

    # Identity
    product_state_ref: str
    phase_id: str
    run_id: str

    # Current work context
    current_pr: str  # PR number or branch name
    current_goal: str  # Human-readable current objective

    # Evidence links
    approved_plan_ref: str  # Plan ref or PLAN.md path
    latest_review_status: str  # e.g. "pending", "approved", "rejected"
    latest_validation_status: str  # e.g. "passed", "failed", "not_run"
    gate_evidence_refs: Tuple[str, ...] = ()  # bundle_refs from PR 0106
    improvement_candidate_refs: Tuple[str, ...] = ()  # candidate_ids from PR 0107

    # Drift and scope
    known_drift_risks: Tuple[str, ...] = ()  # Human-readable drift risks
    deferred_capabilities: Tuple[str, ...] = ()  # Capabilities deferred to future PRs
    next_safe_action: str = ""  # The deterministic next safe action
    blocked_actions: Tuple[str, ...] = ()  # Actions currently blocked

    # File scope
    files_in_scope: Tuple[str, ...] = ()  # Files relevant to current work
    files_out_of_scope: Tuple[str, ...] = ()  # Files intentionally excluded

    # Output
    output_path: str = ""  # Bounded file path for packet artifact

    # Optional
    session_label: str = ""  # Human label (max 256 chars)
    evidence_refs: Tuple[str, ...] = ()  # Additional evidence refs
    requires_human_review: bool = True


# ---------------------------------------------------------------------------
# SessionContinuityPacket — output packet object
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class SessionContinuityPacket:
    """A durable session continuity packet for resuming work."""

    continuity_ref: str  # first 16 hex chars of SHA256(packet JSON)
    product_state_ref: str
    current_pr: str
    current_goal: str
    approved_plan_ref: str
    latest_review_status: str
    latest_validation_status: str
    gate_evidence_refs: Tuple[str, ...]
    improvement_candidate_refs: Tuple[str, ...]
    known_drift_risks: Tuple[str, ...]
    deferred_capabilities: Tuple[str, ...]
    next_safe_action: str
    blocked_actions: Tuple[str, ...]
    files_in_scope: Tuple[str, ...]
    files_out_of_scope: Tuple[str, ...]
    evidence_refs: Tuple[str, ...]
    resume_summary: str  # Deterministic template-based summary
    resume_prompt: str  # Deterministic template-based prompt for next agent
    session_label: str
    phase_id: str
    run_id: str
    requires_human_review: bool


# ---------------------------------------------------------------------------
# SessionContinuityResult — freeze result
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class SessionContinuityResult:
    """Result of a session continuity packet operation."""

    status: SessionContinuityStatus
    reason_codes: Tuple[str, ...]  # empty if created
    packet: Optional[SessionContinuityPacket] = None  # set only when created
    artifact_path: Optional[str] = None  # set only when created
    details: Optional[str] = None


# ---------------------------------------------------------------------------
# Stable reason codes
# ---------------------------------------------------------------------------

REASON_MISSING_PRODUCT_STATE_REF = "missing_product_state_ref"
REASON_MISSING_CURRENT_PR = "missing_current_pr"
REASON_MISSING_CURRENT_GOAL = "missing_current_goal"
REASON_MISSING_APPROVED_PLAN_REF = "missing_approved_plan_ref"
REASON_MISSING_EVIDENCE_REFS = "missing_evidence_refs"
REASON_MISSING_NEXT_SAFE_ACTION = "missing_next_safe_action"
REASON_MISSING_REVIEW_STATUS = "missing_review_status"
REASON_MISSING_DRIFT_RISK = "missing_drift_risk"
REASON_INVALID_SCOPE_BOUNDARY = "invalid_scope_boundary"
REASON_HIDDEN_REASONING_NOT_ALLOWED = "hidden_reasoning_not_allowed"
REASON_EXTERNAL_URL_ONLY_NOT_ALLOWED = "external_url_only_not_allowed"
REASON_UNBOUNDED_CONTINUITY_OUTPUT_PATH = "unbounded_continuity_output_path"
REASON_OVERSIZED_CONTINUITY_PACKET = "oversized_continuity_packet"
REASON_AUTONOMOUS_CODE_CHANGE_NOT_ALLOWED = "autonomous_code_change_not_allowed"
REASON_GIT_MUTATION_NOT_ALLOWED = "git_mutation_not_allowed"
REASON_PROVIDER_CALL_NOT_ALLOWED = "provider_call_not_allowed"

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
)

# ---------------------------------------------------------------------------
# Bounds
# ---------------------------------------------------------------------------

_MAX_PRODUCT_STATE_REF_LENGTH = 256
_MAX_PHASE_ID_LENGTH = 128
_MAX_RUN_ID_LENGTH = 128
_MAX_CURRENT_PR_LENGTH = 256
_MAX_CURRENT_GOAL_LENGTH = 4096
_MAX_APPROVED_PLAN_REF_LENGTH = 256
_MAX_REVIEW_STATUS_LENGTH = 64
_MAX_VALIDATION_STATUS_LENGTH = 64
_MAX_EVIDENCE_REF_LENGTH = 256
_MAX_GATE_EVIDENCE_REF_LENGTH = 64
_MAX_CANDIDATE_REF_LENGTH = 64
_MAX_DRIFT_RISK_LENGTH = 2048
_MAX_DEFERRED_CAPABILITY_LENGTH = 1024
_MAX_NEXT_SAFE_ACTION_LENGTH = 4096
_MAX_BLOCKED_ACTION_LENGTH = 2048
_MAX_FILE_SCOPE_LENGTH = 512
_MAX_OUTPUT_PATH_LENGTH = 255
_MAX_SESSION_LABEL_LENGTH = 256

# ---------------------------------------------------------------------------
# Artifact constants
# ---------------------------------------------------------------------------

_ARIADNE_CONTINUITY_VERSION = "1"


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
        codes.append(REASON_UNBOUNDED_CONTINUITY_OUTPUT_PATH)
        return

    path = output_path.strip()

    if len(path) > _MAX_OUTPUT_PATH_LENGTH:
        codes.append(REASON_UNBOUNDED_CONTINUITY_OUTPUT_PATH)
        return

    if path.startswith("/"):
        codes.append(REASON_UNBOUNDED_CONTINUITY_OUTPUT_PATH)
        return

    if ".." in path.split("/"):
        codes.append(REASON_UNBOUNDED_CONTINUITY_OUTPUT_PATH)
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
# Resume template builders
# ---------------------------------------------------------------------------


def _build_resume_summary(input_data: SessionContinuityInput) -> str:
    """Build a deterministic resume summary from a template."""
    label = input_data.session_label if input_data.session_label else input_data.current_pr
    goal_preview = input_data.current_goal[:200] if len(input_data.current_goal) > 200 else input_data.current_goal
    return (
        f"Session: {label}\n"
        f"Goal: {goal_preview}\n"
        f"Next safe action: {input_data.next_safe_action}\n"
        f"Drift risks: {len(input_data.known_drift_risks)} risk(s)\n"
        f"Files in scope: {len(input_data.files_in_scope)} file(s)\n"
        f"Review status: {input_data.latest_review_status}\n"
        f"Validation status: {input_data.latest_validation_status}\n"
        f"Requires human review: {input_data.requires_human_review}"
    )


def _build_resume_prompt(input_data: SessionContinuityInput) -> str:
    """Build a deterministic resume prompt from a template."""
    sorted_evidence = sorted(input_data.evidence_refs)
    sorted_files_in = sorted(input_data.files_in_scope)
    sorted_files_out = sorted(input_data.files_out_of_scope)

    drift_lines = "\n".join(f"- {risk}" for risk in input_data.known_drift_risks)
    blocked_lines = "\n".join(f"- {action}" for action in input_data.blocked_actions)

    return (
        f"## Resume Context\n\n"
        f"Objective: {input_data.current_goal}\n"
        f"PR: {input_data.current_pr}\n"
        f"Plan ref: {input_data.approved_plan_ref}\n\n"
        f"## Evidence\n"
        f"Gate evidence bundles: {len(input_data.gate_evidence_refs)}\n"
        f"Improvement candidates: {len(input_data.improvement_candidate_refs)}\n"
        f"Evidence refs: {sorted_evidence}\n\n"
        f"## Scope\n"
        f"Files in scope: {sorted_files_in}\n"
        f"Files out of scope: {sorted_files_out}\n\n"
        f"## Drift Risks\n"
        f"{drift_lines}\n\n"
        f"## Next Safe Action\n"
        f"{input_data.next_safe_action}\n\n"
        f"## Blocked Actions\n"
        f"{blocked_lines}\n\n"
        f"## Forbidden Actions\n"
        f"- Do not edit source code autonomously\n"
        f"- Do not create git commits or PRs\n"
        f"- Do not call external providers or models\n"
        f"- Do not execute shell commands\n"
        f"- Do not approve gates or finalize work\n"
        f"- Do not modify files outside files_in_scope"
    )


# ---------------------------------------------------------------------------
# Build session continuity packet function
# ---------------------------------------------------------------------------


def build_session_continuity_packet(
    input_data: SessionContinuityInput,
    output_dir: str = ".",
) -> SessionContinuityResult:
    """Build a session continuity packet from explicit structured input.

    Parameters
    ----------
    input_data:
        The input parameters for the continuity packet.
    output_dir:
        The directory where the packet artifact will be written. Defaults to
        the current working directory.

    Returns
    -------
    SessionContinuityResult
        ``status=CREATED`` with ``packet`` and ``artifact_path`` when
        the packet is created. ``status=REJECTED`` with ``reason_codes``
        when validation fails.
    """
    codes: list[str] = []

    # 1. Identity fields
    _check_non_empty_stripped(
        input_data.product_state_ref,
        _MAX_PRODUCT_STATE_REF_LENGTH,
        REASON_MISSING_PRODUCT_STATE_REF,
        codes,
    )
    _check_non_empty_stripped(
        input_data.phase_id,
        _MAX_PHASE_ID_LENGTH,
        REASON_MISSING_PRODUCT_STATE_REF,
        codes,
    )
    _check_non_empty_stripped(
        input_data.run_id,
        _MAX_RUN_ID_LENGTH,
        REASON_MISSING_PRODUCT_STATE_REF,
        codes,
    )

    # 2. Current work context
    _check_non_empty_stripped(
        input_data.current_pr,
        _MAX_CURRENT_PR_LENGTH,
        REASON_MISSING_CURRENT_PR,
        codes,
    )
    _check_non_empty_stripped(
        input_data.current_goal,
        _MAX_CURRENT_GOAL_LENGTH,
        REASON_MISSING_CURRENT_GOAL,
        codes,
    )
    _check_hidden_reasoning(input_data.current_goal, codes)

    # 3. Evidence links
    _check_non_empty_stripped(
        input_data.approved_plan_ref,
        _MAX_APPROVED_PLAN_REF_LENGTH,
        REASON_MISSING_APPROVED_PLAN_REF,
        codes,
    )
    _check_non_empty_stripped(
        input_data.latest_review_status,
        _MAX_REVIEW_STATUS_LENGTH,
        REASON_MISSING_REVIEW_STATUS,
        codes,
    )
    _check_non_empty_stripped(
        input_data.latest_validation_status,
        _MAX_VALIDATION_STATUS_LENGTH,
        REASON_MISSING_REVIEW_STATUS,
        codes,
    )

    # 4. Evidence refs — at least one evidence-related field must be non-empty
    has_evidence = (
        len(input_data.gate_evidence_refs) > 0
        or len(input_data.improvement_candidate_refs) > 0
        or len(input_data.evidence_refs) > 0
    )
    if not has_evidence:
        codes.append(REASON_MISSING_EVIDENCE_REFS)

    # Validate each evidence ref
    _check_tuple_non_empty_stripped(
        input_data.gate_evidence_refs,
        _MAX_GATE_EVIDENCE_REF_LENGTH,
        REASON_MISSING_EVIDENCE_REFS,
        codes,
    )
    _check_tuple_non_empty_stripped(
        input_data.improvement_candidate_refs,
        _MAX_CANDIDATE_REF_LENGTH,
        REASON_MISSING_EVIDENCE_REFS,
        codes,
    )
    _check_tuple_non_empty_stripped(
        input_data.evidence_refs,
        _MAX_EVIDENCE_REF_LENGTH,
        REASON_MISSING_EVIDENCE_REFS,
        codes,
    )

    # 5. Next safe action
    _check_non_empty_stripped(
        input_data.next_safe_action,
        _MAX_NEXT_SAFE_ACTION_LENGTH,
        REASON_MISSING_NEXT_SAFE_ACTION,
        codes,
    )
    # If non-empty but oversized, use oversized reason
    if input_data.next_safe_action and input_data.next_safe_action.strip() and len(input_data.next_safe_action) > _MAX_NEXT_SAFE_ACTION_LENGTH:
        codes.remove(REASON_MISSING_NEXT_SAFE_ACTION)
        codes.append(REASON_OVERSIZED_CONTINUITY_PACKET)
    _check_hidden_reasoning(input_data.next_safe_action, codes)
    _check_external_url_only(input_data.next_safe_action, codes)
    _check_forbidden_actions(input_data.next_safe_action, codes)

    # 6. Drift risks — at least one
    if not input_data.known_drift_risks:
        codes.append(REASON_MISSING_DRIFT_RISK)
    else:
        _check_tuple_non_empty_stripped(
            input_data.known_drift_risks,
            _MAX_DRIFT_RISK_LENGTH,
            REASON_MISSING_DRIFT_RISK,
            codes,
        )

    # 7. Deferred capabilities bounds
    _check_tuple_non_empty_stripped(
        input_data.deferred_capabilities,
        _MAX_DEFERRED_CAPABILITY_LENGTH,
        REASON_OVERSIZED_CONTINUITY_PACKET,
        codes,
    )

    # 8. Blocked actions bounds
    _check_tuple_non_empty_stripped(
        input_data.blocked_actions,
        _MAX_BLOCKED_ACTION_LENGTH,
        REASON_OVERSIZED_CONTINUITY_PACKET,
        codes,
    )

    # 9. File scope — at least one file in scope
    if not input_data.files_in_scope:
        codes.append(REASON_INVALID_SCOPE_BOUNDARY)
    else:
        _check_tuple_non_empty_stripped(
            input_data.files_in_scope,
            _MAX_FILE_SCOPE_LENGTH,
            REASON_INVALID_SCOPE_BOUNDARY,
            codes,
        )

    _check_tuple_non_empty_stripped(
        input_data.files_out_of_scope,
        _MAX_FILE_SCOPE_LENGTH,
        REASON_INVALID_SCOPE_BOUNDARY,
        codes,
    )

    # 10. Scope boundary overlap check
    if input_data.files_in_scope and input_data.files_out_of_scope:
        in_set = set(input_data.files_in_scope)
        out_set = set(input_data.files_out_of_scope)
        overlap = in_set & out_set
        if overlap:
            codes.append(REASON_INVALID_SCOPE_BOUNDARY)

    # 11. Output path
    _check_output_path(input_data.output_path, codes)

    # 12. Session label bounds
    if len(input_data.session_label) > _MAX_SESSION_LABEL_LENGTH:
        codes.append(REASON_OVERSIZED_CONTINUITY_PACKET)

    # --- Deterministic sort ---
    codes.sort()

    if codes:
        detail_lines = [f"  - {c}" for c in codes]
        details = "Session continuity packet rejected:\n" + "\n".join(detail_lines)
        return SessionContinuityResult(
            status=SessionContinuityStatus.REJECTED,
            reason_codes=tuple(codes),
            details=details,
        )

    # --- Build resume fields ---
    resume_summary = _build_resume_summary(input_data)
    resume_prompt = _build_resume_prompt(input_data)

    # --- Build canonical packet JSON ---
    sorted_gate_evidence_refs = sorted(input_data.gate_evidence_refs)
    sorted_improvement_candidate_refs = sorted(input_data.improvement_candidate_refs)
    sorted_known_drift_risks = sorted(input_data.known_drift_risks)
    sorted_deferred_capabilities = sorted(input_data.deferred_capabilities)
    sorted_blocked_actions = sorted(input_data.blocked_actions)
    sorted_files_in_scope = sorted(input_data.files_in_scope)
    sorted_files_out_of_scope = sorted(input_data.files_out_of_scope)
    sorted_evidence_refs = sorted(input_data.evidence_refs)

    packet_dict = {
        "ariadne_continuity_version": _ARIADNE_CONTINUITY_VERSION,
        "product_state_ref": input_data.product_state_ref,
        "current_pr": input_data.current_pr,
        "current_goal": input_data.current_goal,
        "approved_plan_ref": input_data.approved_plan_ref,
        "latest_review_status": input_data.latest_review_status,
        "latest_validation_status": input_data.latest_validation_status,
        "gate_evidence_refs": sorted_gate_evidence_refs,
        "improvement_candidate_refs": sorted_improvement_candidate_refs,
        "known_drift_risks": sorted_known_drift_risks,
        "deferred_capabilities": sorted_deferred_capabilities,
        "next_safe_action": input_data.next_safe_action,
        "blocked_actions": sorted_blocked_actions,
        "files_in_scope": sorted_files_in_scope,
        "files_out_of_scope": sorted_files_out_of_scope,
        "evidence_refs": sorted_evidence_refs,
        "resume_summary": resume_summary,
        "resume_prompt": resume_prompt,
        "session_label": input_data.session_label,
        "phase_id": input_data.phase_id,
        "run_id": input_data.run_id,
        "requires_human_review": input_data.requires_human_review,
        "created_at": None,  # deterministic; no wall-clock time
    }

    # Derive continuity_ref from SHA256 of canonical JSON (first 16 hex chars)
    packet_json = json.dumps(packet_dict, sort_keys=True, indent=2)
    continuity_ref = hashlib.sha256(packet_json.encode("utf-8")).hexdigest()[:16]

    # Add continuity_ref to the dict
    packet_dict["continuity_ref"] = continuity_ref

    # Re-serialize with continuity_ref included
    packet_json = json.dumps(packet_dict, sort_keys=True, indent=2)

    # Build SessionContinuityPacket object
    packet = SessionContinuityPacket(
        continuity_ref=continuity_ref,
        product_state_ref=input_data.product_state_ref,
        current_pr=input_data.current_pr,
        current_goal=input_data.current_goal,
        approved_plan_ref=input_data.approved_plan_ref,
        latest_review_status=input_data.latest_review_status,
        latest_validation_status=input_data.latest_validation_status,
        gate_evidence_refs=tuple(sorted_gate_evidence_refs),
        improvement_candidate_refs=tuple(sorted_improvement_candidate_refs),
        known_drift_risks=tuple(sorted_known_drift_risks),
        deferred_capabilities=tuple(sorted_deferred_capabilities),
        next_safe_action=input_data.next_safe_action,
        blocked_actions=tuple(sorted_blocked_actions),
        files_in_scope=tuple(sorted_files_in_scope),
        files_out_of_scope=tuple(sorted_files_out_of_scope),
        evidence_refs=tuple(sorted_evidence_refs),
        resume_summary=resume_summary,
        resume_prompt=resume_prompt,
        session_label=input_data.session_label,
        phase_id=input_data.phase_id,
        run_id=input_data.run_id,
        requires_human_review=input_data.requires_human_review,
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
        f.write(packet_json)

    return SessionContinuityResult(
        status=SessionContinuityStatus.CREATED,
        reason_codes=(),
        packet=packet,
        artifact_path=output_path,
        details=None,
    )
