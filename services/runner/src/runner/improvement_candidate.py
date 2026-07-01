"""
Deterministic local evidence-backed self-improvement candidates for Ariadne.

Defines ``ImprovementCandidateInput``, ``ImprovementCandidate``,
``ImprovementCandidateResult``, ``ImprovementCandidateStatus``,
``ImprovementCategory``, and ``propose_improvement_candidate()`` —
a deterministic, local function that produces bounded improvement
candidates from runtime evidence and stable reason codes.

Core principle:
    The improvement candidate is a proposal, not an action. It does NOT
    edit code, commit changes, call models, or approve itself.
"""

from __future__ import annotations

import dataclasses
import enum
import hashlib
import json
import os
from typing import Optional, Tuple


# ---------------------------------------------------------------------------
# ImprovementCandidateStatus — final verdict
# ---------------------------------------------------------------------------


class ImprovementCandidateStatus(str, enum.Enum):
    """Final verdict for an improvement candidate proposal."""

    PROPOSED = "proposed"
    REJECTED = "rejected"


# ---------------------------------------------------------------------------
# ImprovementCategory — deterministic category mapping
# ---------------------------------------------------------------------------


class ImprovementCategory(str, enum.Enum):
    """Deterministic improvement category mapped from evidence reason codes."""

    VALIDATION_GAP = "validation_gap"
    EVIDENCE_GAP = "evidence_gap"
    CONSISTENCY_GAP = "consistency_gap"
    SCOPE_DRIFT = "scope_drift"
    MISSING_RUNTIME_ARTIFACT = "missing_runtime_artifact"
    CLI_SURFACE_GAP = "cli_surface_gap"
    FRONTEND_VISIBILITY_GAP = "frontend_visibility_gap"


# ---------------------------------------------------------------------------
# ImprovementCandidateInput — input parameters
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class ImprovementCandidateInput:
    """Input parameters for proposing an improvement candidate from evidence."""

    product_state_ref: str
    acceptance_criteria_ref: str
    phase_id: str
    run_id: str
    source_bundle_ref: str  # bundle_ref from PR 0106 gate evidence bundle
    source_reason_codes: Tuple[str, ...]  # reason_codes from gate evidence or validation
    output_path: str  # Bounded local file path for candidate artifact
    evidence_refs: Tuple[str, ...]  # Ref IDs from evidence that triggered the candidate
    proposed_next_action: str = ""  # Human-readable suggested action (max 4096 chars)
    affected_runtime_area: str = ""  # Area name (max 256 chars)
    requires_human_review: bool = True  # Default True — candidates are proposals, not actions


# ---------------------------------------------------------------------------
# ImprovementCandidate — output candidate object
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class ImprovementCandidate:
    """A bounded, evidence-backed improvement candidate proposal."""

    candidate_id: str  # first 16 hex chars of SHA256(candidate JSON)
    product_state_ref: str
    acceptance_criteria_ref: str
    source_bundle_ref: str
    source_reason_codes: Tuple[str, ...]
    evidence_refs: Tuple[str, ...]
    improvement_category: str  # ImprovementCategory value
    proposed_next_action: str
    affected_runtime_area: str
    phase_id: str
    run_id: str
    requires_human_review: bool


# ---------------------------------------------------------------------------
# ImprovementCandidateResult — freeze result
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class ImprovementCandidateResult:
    """Result of an improvement candidate proposal."""

    status: ImprovementCandidateStatus
    reason_codes: Tuple[str, ...]  # empty if proposed
    candidate: Optional[ImprovementCandidate] = None  # set only when proposed
    artifact_path: Optional[str] = None  # set only when proposed
    details: Optional[str] = None


# ---------------------------------------------------------------------------
# Stable reason codes
# ---------------------------------------------------------------------------

REASON_MISSING_GATE_EVIDENCE = "missing_gate_evidence"
REASON_MISSING_PRODUCT_STATE_REF = "missing_product_state_ref"
REASON_MISSING_ACCEPTANCE_CRITERIA_REF = "missing_acceptance_criteria_ref"
REASON_MISSING_REASON_CODE = "missing_reason_code"
REASON_MISSING_EVIDENCE_REF = "missing_evidence_ref"
REASON_UNSUPPORTED_REASON_CODE = "unsupported_reason_code"
REASON_HIDDEN_REASONING_NOT_ALLOWED = "hidden_reasoning_not_allowed"
REASON_EXTERNAL_URL_ONLY_NOT_ALLOWED = "external_url_only_not_allowed"
REASON_UNBOUNDED_CANDIDATE_OUTPUT_PATH = "unbounded_candidate_output_path"
REASON_OVERSIZED_CANDIDATE = "oversized_candidate"
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
# Forbidden action patterns (autonomous code change, git mutation, provider)
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
_MAX_ACCEPTANCE_CRITERIA_REF_LENGTH = 256
_MAX_PHASE_ID_LENGTH = 128
_MAX_RUN_ID_LENGTH = 128
_MAX_SOURCE_BUNDLE_REF_LENGTH = 64
_MAX_REASON_CODE_LENGTH = 128
_MAX_EVIDENCE_REF_LENGTH = 256
_MAX_OUTPUT_PATH_LENGTH = 255
_MAX_PROPOSED_NEXT_ACTION_LENGTH = 4096
_MAX_AFFECTED_RUNTIME_AREA_LENGTH = 256

# ---------------------------------------------------------------------------
# Category mapping: deterministic mapping from reason code patterns
# ---------------------------------------------------------------------------

_CATEGORY_MAPPING: Tuple[Tuple[str, ImprovementCategory], ...] = (
    # EVIDENCE_GAP: specific patterns first (before generic "missing_")
    ("missing_proof_refs", ImprovementCategory.EVIDENCE_GAP),
    ("missing_capture_refs", ImprovementCategory.EVIDENCE_GAP),
    ("unknown_capture_ref", ImprovementCategory.EVIDENCE_GAP),
    # CONSISTENCY_GAP: specific patterns first
    ("inconsistent_", ImprovementCategory.CONSISTENCY_GAP),
    ("inadmissible_", ImprovementCategory.CONSISTENCY_GAP),
    # SCOPE_DRIFT: specific patterns
    ("hidden_reasoning_not_allowed", ImprovementCategory.SCOPE_DRIFT),
    ("external_url_only_not_allowed", ImprovementCategory.SCOPE_DRIFT),
    # MISSING_RUNTIME_ARTIFACT: specific patterns
    ("unbounded_", ImprovementCategory.MISSING_RUNTIME_ARTIFACT),
    ("oversized_", ImprovementCategory.MISSING_RUNTIME_ARTIFACT),
    # CLI_SURFACE_GAP: reserved for future CLI context
    ("cli_", ImprovementCategory.CLI_SURFACE_GAP),
    # FRONTEND_VISIBILITY_GAP: reserved for future frontend context
    ("frontend_", ImprovementCategory.FRONTEND_VISIBILITY_GAP),
    # VALIDATION_GAP: generic catch-all for missing_* patterns
    ("missing_", ImprovementCategory.VALIDATION_GAP),
)

# Sort order for tie-breaking when multiple categories match
_CATEGORY_SORT_ORDER: Tuple[ImprovementCategory, ...] = (
    ImprovementCategory.CLI_SURFACE_GAP,
    ImprovementCategory.CONSISTENCY_GAP,
    ImprovementCategory.EVIDENCE_GAP,
    ImprovementCategory.FRONTEND_VISIBILITY_GAP,
    ImprovementCategory.MISSING_RUNTIME_ARTIFACT,
    ImprovementCategory.SCOPE_DRIFT,
    ImprovementCategory.VALIDATION_GAP,
)


# ---------------------------------------------------------------------------
# Artifact constants
# ---------------------------------------------------------------------------

_ARIADNE_CANDIDATE_VERSION = "1"


# ---------------------------------------------------------------------------
# Category mapping function
# ---------------------------------------------------------------------------


def _map_reason_code_to_category(reason_code: str) -> ImprovementCategory:
    """Map a single reason code to an ImprovementCategory deterministically.

    Uses the first matching pattern from the mapping table.
    Falls back to VALIDATION_GAP if no pattern matches.
    """
    for pattern, category in _CATEGORY_MAPPING:
        if pattern in reason_code:
            return category
    return ImprovementCategory.VALIDATION_GAP


def _determine_improvement_category(reason_codes: Tuple[str, ...]) -> ImprovementCategory:
    """Determine the single improvement category from multiple reason codes.

    If all codes map to the same category, use that category.
    If multiple categories, use the first in sort order (deterministic).
    """
    categories = set()
    for code in reason_codes:
        categories.add(_map_reason_code_to_category(code))

    if len(categories) == 1:
        return categories.pop()

    # Multiple categories — use first in sort order
    for cat in _CATEGORY_SORT_ORDER:
        if cat in categories:
            return cat

    return ImprovementCategory.VALIDATION_GAP


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
        codes.append(REASON_UNBOUNDED_CANDIDATE_OUTPUT_PATH)
        return

    path = output_path.strip()

    if len(path) > _MAX_OUTPUT_PATH_LENGTH:
        codes.append(REASON_UNBOUNDED_CANDIDATE_OUTPUT_PATH)
        return

    if path.startswith("/"):
        codes.append(REASON_UNBOUNDED_CANDIDATE_OUTPUT_PATH)
        return

    if ".." in path.split("/"):
        codes.append(REASON_UNBOUNDED_CANDIDATE_OUTPUT_PATH)
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
    """Check for forbidden action patterns in proposed_next_action."""
    for pattern, reason in _FORBIDDEN_ACTION_PATTERNS:
        if pattern in text:
            codes.append(reason)
            return


# ---------------------------------------------------------------------------
# Propose improvement candidate function
# ---------------------------------------------------------------------------


def propose_improvement_candidate(
    input_data: ImprovementCandidateInput,
    output_dir: str = ".",
) -> ImprovementCandidateResult:
    """Propose an improvement candidate from runtime evidence.

    Parameters
    ----------
    input_data:
        The input parameters for the candidate proposal.
    output_dir:
        The directory where the candidate artifact will be written. Defaults
        to the current working directory.

    Returns
    -------
    ImprovementCandidateResult
        ``status=PROPOSED`` with ``candidate`` and ``artifact_path`` when
        the proposal succeeds. ``status=REJECTED`` with ``reason_codes``
        when validation fails.
    """
    codes: list[str] = []

    # 1. Basic field validation
    _check_non_empty_stripped(
        input_data.product_state_ref,
        _MAX_PRODUCT_STATE_REF_LENGTH,
        REASON_MISSING_PRODUCT_STATE_REF,
        codes,
    )
    _check_non_empty_stripped(
        input_data.acceptance_criteria_ref,
        _MAX_ACCEPTANCE_CRITERIA_REF_LENGTH,
        REASON_MISSING_ACCEPTANCE_CRITERIA_REF,
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

    # 2. Source bundle ref (gate evidence)
    _check_non_empty_stripped(
        input_data.source_bundle_ref,
        _MAX_SOURCE_BUNDLE_REF_LENGTH,
        REASON_MISSING_GATE_EVIDENCE,
        codes,
    )

    # 3. Source reason codes
    if not input_data.source_reason_codes:
        codes.append(REASON_MISSING_REASON_CODE)
    else:
        for code in input_data.source_reason_codes:
            if not code or code.strip() == "":
                codes.append(REASON_MISSING_REASON_CODE)
                break
            if len(code) > _MAX_REASON_CODE_LENGTH:
                codes.append(REASON_UNSUPPORTED_REASON_CODE)
                break

    # 4. Evidence refs
    if not input_data.evidence_refs:
        codes.append(REASON_MISSING_EVIDENCE_REF)
    else:
        for ref in input_data.evidence_refs:
            if not ref or ref.strip() == "":
                codes.append(REASON_MISSING_EVIDENCE_REF)
                break
            if len(ref) > _MAX_EVIDENCE_REF_LENGTH:
                codes.append(REASON_OVERSIZED_CANDIDATE)
                break

    # 5. Output path
    _check_output_path(input_data.output_path, codes)

    # 6. Proposed next action bounds and forbidden patterns
    if len(input_data.proposed_next_action) > _MAX_PROPOSED_NEXT_ACTION_LENGTH:
        codes.append(REASON_OVERSIZED_CANDIDATE)

    _check_hidden_reasoning(input_data.proposed_next_action, codes)
    _check_external_url_only(input_data.proposed_next_action, codes)
    _check_forbidden_actions(input_data.proposed_next_action, codes)

    # 7. Affected runtime area bounds
    if len(input_data.affected_runtime_area) > _MAX_AFFECTED_RUNTIME_AREA_LENGTH:
        codes.append(REASON_OVERSIZED_CANDIDATE)

    # --- Deterministic sort ---
    codes.sort()

    if codes:
        detail_lines = [f"  - {c}" for c in codes]
        details = "Improvement candidate rejected:\n" + "\n".join(detail_lines)
        return ImprovementCandidateResult(
            status=ImprovementCandidateStatus.REJECTED,
            reason_codes=tuple(codes),
            details=details,
        )

    # --- Determine improvement category ---
    improvement_category = _determine_improvement_category(input_data.source_reason_codes)

    # --- Build canonical candidate JSON ---
    sorted_reason_codes = sorted(input_data.source_reason_codes)
    sorted_evidence_refs = sorted(input_data.evidence_refs)

    # Build candidate dict (without candidate_id — we need the hash first)
    candidate_dict = {
        "ariadne_candidate_version": _ARIADNE_CANDIDATE_VERSION,
        "product_state_ref": input_data.product_state_ref,
        "acceptance_criteria_ref": input_data.acceptance_criteria_ref,
        "source_bundle_ref": input_data.source_bundle_ref,
        "source_reason_codes": sorted_reason_codes,
        "evidence_refs": sorted_evidence_refs,
        "improvement_category": improvement_category.value,
        "proposed_next_action": input_data.proposed_next_action,
        "affected_runtime_area": input_data.affected_runtime_area,
        "phase_id": input_data.phase_id,
        "run_id": input_data.run_id,
        "requires_human_review": input_data.requires_human_review,
        "proposed_at": None,  # deterministic; no wall-clock time
    }

    # Derive candidate_id from SHA256 of canonical JSON (first 16 hex chars)
    candidate_json = json.dumps(candidate_dict, sort_keys=True, indent=2)
    candidate_id = hashlib.sha256(candidate_json.encode("utf-8")).hexdigest()[:16]

    # Add candidate_id to the dict
    candidate_dict["candidate_id"] = candidate_id

    # Re-serialize with candidate_id included
    candidate_json = json.dumps(candidate_dict, sort_keys=True, indent=2)

    # Build ImprovementCandidate object
    candidate = ImprovementCandidate(
        candidate_id=candidate_id,
        product_state_ref=input_data.product_state_ref,
        acceptance_criteria_ref=input_data.acceptance_criteria_ref,
        source_bundle_ref=input_data.source_bundle_ref,
        source_reason_codes=tuple(sorted_reason_codes),
        evidence_refs=tuple(sorted_evidence_refs),
        improvement_category=improvement_category.value,
        proposed_next_action=input_data.proposed_next_action,
        affected_runtime_area=input_data.affected_runtime_area,
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
        f.write(candidate_json)

    return ImprovementCandidateResult(
        status=ImprovementCandidateStatus.PROPOSED,
        reason_codes=(),
        candidate=candidate,
        artifact_path=output_path,
        details=None,
    )
