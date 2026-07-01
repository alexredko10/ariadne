"""
Deterministic acceptance criteria freeze for Ariadne.

Defines ``AcceptanceCriterion``, ``AcceptanceCriteriaFreezeInput``,
``AcceptanceCriteriaFreezeResult``, and ``freeze_acceptance_criteria()`` —
a deterministic, local function that writes a bounded frozen artifact and
returns an ``acceptance_criteria_ref``-compatible result.

Core principle:
    Acceptance criteria must be frozen before they can be referenced by
    proof captures or handoff packets. A frozen criteria set is immutable
    and its reference is derived from its content.
"""

from __future__ import annotations

import dataclasses
import enum
import hashlib
import json
import os
import re
from typing import Optional, Tuple


# ---------------------------------------------------------------------------
# AcceptanceCriteriaFreezeStatus — final verdict
# ---------------------------------------------------------------------------


class AcceptanceCriteriaFreezeStatus(str, enum.Enum):
    """Final verdict for an acceptance criteria freeze operation."""

    FROZEN = "frozen"
    REJECTED = "rejected"


# ---------------------------------------------------------------------------
# AcceptanceCriterion — a single frozen criterion
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class AcceptanceCriterion:
    """A single frozen acceptance criterion."""

    criterion_id: str  # Stable identifier, e.g. "AC-001"
    description: str  # Human-readable criterion text


# ---------------------------------------------------------------------------
# AcceptanceCriteriaFreezeInput — input parameters
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class AcceptanceCriteriaFreezeInput:
    """Input parameters for freezing acceptance criteria."""

    product_state_ref: str
    criteria: Tuple[AcceptanceCriterion, ...]  # At least one
    phase_id: str
    run_id: str
    output_path: str  # Bounded local file path
    title: str = ""  # Optional title for the criteria set


# ---------------------------------------------------------------------------
# AcceptanceCriteriaFreezeResult — freeze result
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class AcceptanceCriteriaFreezeResult:
    """Result of an acceptance criteria freeze operation."""

    status: AcceptanceCriteriaFreezeStatus
    reason_codes: Tuple[str, ...]  # empty if frozen
    artifact_path: Optional[str] = None  # set only when frozen
    acceptance_criteria_ref: Optional[str] = None  # deterministic ref; set only when frozen
    criteria_count: Optional[int] = None  # set only when frozen
    criterion_ids: Optional[Tuple[str, ...]] = None  # sorted; set only when frozen
    details: Optional[str] = None


# ---------------------------------------------------------------------------
# Stable reason codes
# ---------------------------------------------------------------------------

REASON_MISSING_PRODUCT_STATE_REF = "missing_product_state_ref"
REASON_MISSING_CRITERIA = "missing_criteria"
REASON_MISSING_CRITERION_ID = "missing_criterion_id"
REASON_MISSING_CRITERION_TEXT = "missing_criterion_text"
REASON_DUPLICATE_CRITERION_ID = "duplicate_criterion_id"
REASON_UNBOUNDED_CRITERION_TEXT = "unbounded_criterion_text"
REASON_OVERSIZED_CRITERIA_SET = "oversized_criteria_set"
REASON_MISSING_OUTPUT_PATH = "missing_output_path"
REASON_UNBOUNDED_OUTPUT_PATH = "unbounded_output_path"
REASON_HIDDEN_REASONING_NOT_ALLOWED = "hidden_reasoning_not_allowed"
REASON_EXTERNAL_URL_ONLY_NOT_ALLOWED = "external_url_only_not_allowed"
REASON_MUTABLE_CRITERIA_NOT_ALLOWED = "mutable_criteria_not_allowed"

# ---------------------------------------------------------------------------
# Forbidden hidden reasoning patterns
# ---------------------------------------------------------------------------

_FORBIDDEN_HIDDEN_REASONING_PATTERNS: Tuple[str, ...] = (
    "<cot>",
    "<chain_of_thought>",
    "hidden_reasoning",
)

# ---------------------------------------------------------------------------
# Bounds
# ---------------------------------------------------------------------------

_MAX_PRODUCT_STATE_REF_LENGTH = 256
_MAX_CRITERION_ID_LENGTH = 64
_MAX_CRITERION_DESCRIPTION_LENGTH = 4096
_MAX_CRITERIA_COUNT = 100
_MAX_PHASE_ID_LENGTH = 128
_MAX_RUN_ID_LENGTH = 128
_MAX_OUTPUT_PATH_LENGTH = 255
_MAX_TITLE_LENGTH = 256

# ---------------------------------------------------------------------------
# Criterion ID pattern
# ---------------------------------------------------------------------------

_CRITERION_ID_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9\-]*$")

# ---------------------------------------------------------------------------
# Artifact constants
# ---------------------------------------------------------------------------

_ARIADNE_ACCEPTANCE_CRITERIA_VERSION = "1"


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
        codes.append(REASON_MISSING_OUTPUT_PATH)
        return

    path = output_path.strip()

    if len(path) > _MAX_OUTPUT_PATH_LENGTH:
        codes.append(REASON_UNBOUNDED_OUTPUT_PATH)
        return

    if path.startswith("/"):
        codes.append(REASON_UNBOUNDED_OUTPUT_PATH)
        return

    if ".." in path.split("/"):
        codes.append(REASON_UNBOUNDED_OUTPUT_PATH)
        return


def _check_description(description: str, codes: list[str]) -> None:
    """Validate description bounds and forbidden patterns."""
    if not description or description.strip() == "":
        codes.append(REASON_MISSING_CRITERION_TEXT)
        return

    if len(description) > _MAX_CRITERION_DESCRIPTION_LENGTH:
        codes.append(REASON_UNBOUNDED_CRITERION_TEXT)

    # Check hidden reasoning patterns
    for pattern in _FORBIDDEN_HIDDEN_REASONING_PATTERNS:
        if pattern in description:
            codes.append(REASON_HIDDEN_REASONING_NOT_ALLOWED)
            break

    # Check external URL-only description
    stripped = description.strip()
    if stripped.startswith("http://") or stripped.startswith("https://"):
        if "\n" not in stripped and " " not in stripped:
            codes.append(REASON_EXTERNAL_URL_ONLY_NOT_ALLOWED)


def _check_criterion_id(criterion_id: str, codes: list[str]) -> None:
    """Validate criterion_id presence and format."""
    if not criterion_id or criterion_id.strip() == "":
        codes.append(REASON_MISSING_CRITERION_ID)
        return

    if len(criterion_id) > _MAX_CRITERION_ID_LENGTH:
        codes.append(REASON_MISSING_CRITERION_ID)

    if not _CRITERION_ID_PATTERN.match(criterion_id):
        codes.append(REASON_MISSING_CRITERION_ID)


# ---------------------------------------------------------------------------
# Freeze function
# ---------------------------------------------------------------------------


def freeze_acceptance_criteria(
    input_data: AcceptanceCriteriaFreezeInput,
    output_dir: str = ".",
) -> AcceptanceCriteriaFreezeResult:
    """Freeze acceptance criteria to a deterministic artifact.

    Parameters
    ----------
    input_data:
        The input parameters for the freeze operation.
    output_dir:
        The directory where the artifact will be written. Defaults to the
        current working directory.

    Returns
    -------
    AcceptanceCriteriaFreezeResult
        ``status=FROZEN`` with ``acceptance_criteria_ref``, ``artifact_path``,
        ``criteria_count``, and ``criterion_ids`` when the freeze succeeds.
        ``status=REJECTED`` with ``reason_codes`` when validation fails.
    """
    codes: list[str] = []

    # 1. Product state ref
    _check_non_empty_stripped(
        input_data.product_state_ref,
        _MAX_PRODUCT_STATE_REF_LENGTH,
        REASON_MISSING_PRODUCT_STATE_REF,
        codes,
    )

    # 2. Phase identity
    _check_non_empty_stripped(
        input_data.phase_id,
        _MAX_PHASE_ID_LENGTH,
        REASON_MISSING_CRITERIA,
        codes,
    )

    # 3. Run identity
    _check_non_empty_stripped(
        input_data.run_id,
        _MAX_RUN_ID_LENGTH,
        REASON_MISSING_CRITERIA,
        codes,
    )

    # 4. Criteria presence and count
    if not input_data.criteria:
        codes.append(REASON_MISSING_CRITERIA)
    elif len(input_data.criteria) > _MAX_CRITERIA_COUNT:
        codes.append(REASON_OVERSIZED_CRITERIA_SET)

    # 5. Validate each criterion
    seen_ids: set[str] = set()
    for criterion in input_data.criteria:
        _check_criterion_id(criterion.criterion_id, codes)
        _check_description(criterion.description, codes)

        # Check duplicate IDs
        cid = criterion.criterion_id.strip()
        if cid and cid in seen_ids:
            codes.append(REASON_DUPLICATE_CRITERION_ID)
        seen_ids.add(cid)

    # 6. Title bounds
    if len(input_data.title) > _MAX_TITLE_LENGTH:
        codes.append(REASON_OVERSIZED_CRITERIA_SET)

    # 7. Output path
    _check_output_path(input_data.output_path, codes)

    # --- Deterministic sort ---
    codes.sort()

    if codes:
        detail_lines = [f"  - {c}" for c in codes]
        details = "Acceptance criteria freeze rejected:\n" + "\n".join(detail_lines)
        return AcceptanceCriteriaFreezeResult(
            status=AcceptanceCriteriaFreezeStatus.REJECTED,
            reason_codes=tuple(codes),
            details=details,
        )

    # --- Build canonical artifact ---
    # Sort criteria by criterion_id for determinism
    sorted_criteria = sorted(input_data.criteria, key=lambda c: c.criterion_id)

    criteria_list = [
        {"criterion_id": c.criterion_id, "description": c.description}
        for c in sorted_criteria
    ]

    artifact = {
        "ariadne_acceptance_criteria_version": _ARIADNE_ACCEPTANCE_CRITERIA_VERSION,
        "product_state_ref": input_data.product_state_ref,
        "title": input_data.title,
        "phase_id": input_data.phase_id,
        "run_id": input_data.run_id,
        "criteria": criteria_list,
        "frozen_at": None,  # deterministic; no wall-clock time
    }

    artifact_json = json.dumps(artifact, sort_keys=True, indent=2)

    # Derive acceptance_criteria_ref from SHA256 of artifact content (first 16 hex chars)
    sha256_hash = hashlib.sha256(artifact_json.encode("utf-8")).hexdigest()[:16]
    acceptance_criteria_ref = sha256_hash

    # Normalize output path
    output_path = input_data.output_path.strip()
    full_path = os.path.join(output_dir, output_path)

    # Ensure parent directory exists
    parent_dir = os.path.dirname(full_path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)

    # Write artifact
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(artifact_json)

    # Collect sorted criterion IDs
    criterion_ids = tuple(c.criterion_id for c in sorted_criteria)

    return AcceptanceCriteriaFreezeResult(
        status=AcceptanceCriteriaFreezeStatus.FROZEN,
        reason_codes=(),
        artifact_path=output_path,
        acceptance_criteria_ref=acceptance_criteria_ref,
        criteria_count=len(input_data.criteria),
        criterion_ids=criterion_ids,
        details=None,
    )
