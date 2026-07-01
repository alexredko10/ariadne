"""
Deterministic local proof capture for Ariadne.

Defines the ``ProofCaptureInput``, ``ProofCaptureResult``, and
``capture_proof()`` — a deterministic, local function that writes a bounded
captured proof artifact and returns a proof_ref-compatible result.

Core principle:
    Agent output is not proof. Runtime-captured proof is evidence.
    The agent may be an executor, but not the notary of its own work.
"""

from __future__ import annotations

import dataclasses
import enum
import hashlib
import json
import os
from typing import FrozenSet, Optional, Tuple


# ---------------------------------------------------------------------------
# ProofCaptureStatus — final verdict
# ---------------------------------------------------------------------------


class ProofCaptureStatus(str, enum.Enum):
    """Final verdict for a proof capture operation."""

    CAPTURED = "captured"
    REJECTED = "rejected"


# ---------------------------------------------------------------------------
# ProofCaptureInput — input parameters
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class ProofCaptureInput:
    """Input parameters for a deterministic local proof capture."""

    product_state_ref: str
    acceptance_criteria_ref: str
    runtime_capture_kind: str  # e.g. "text", "json"
    phase_id: str
    run_id: str
    payload: str  # The captured evidence content
    output_path: str  # Bounded local file path for the artifact
    summary: str = ""  # Optional human-readable summary
    tags: FrozenSet[str] = dataclasses.field(default_factory=frozenset)


# ---------------------------------------------------------------------------
# ProofCaptureResult — capture result
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class ProofCaptureResult:
    """Result of a proof capture operation."""

    status: ProofCaptureStatus
    reason_codes: Tuple[str, ...]  # empty if captured
    artifact_path: Optional[str] = None  # set only when captured
    proof_ref_fields: Optional[dict] = None  # proof_ref-compatible dict; set only when captured
    details: Optional[str] = None


# ---------------------------------------------------------------------------
# Stable reason codes
# ---------------------------------------------------------------------------

REASON_MISSING_PRODUCT_STATE_REF = "missing_product_state_ref"
REASON_MISSING_ACCEPTANCE_CRITERIA_REF = "missing_acceptance_criteria_ref"
REASON_MISSING_RUNTIME_CAPTURE_KIND = "missing_runtime_capture_kind"
REASON_MISSING_PHASE_IDENTITY = "missing_phase_identity"
REASON_MISSING_RUN_IDENTITY = "missing_run_identity"
REASON_MISSING_OUTPUT_PATH = "missing_output_path"
REASON_UNBOUNDED_OUTPUT_PATH = "unbounded_output_path"
REASON_OVERSIZED_CAPTURE = "oversized_capture"
REASON_HIDDEN_REASONING_NOT_ALLOWED = "hidden_reasoning_not_allowed"
REASON_EXTERNAL_URL_ONLY_NOT_ALLOWED = "external_url_only_not_allowed"
REASON_ARBITRARY_COMMAND_EXECUTION_NOT_ALLOWED = "arbitrary_command_execution_not_allowed"

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
_MAX_ACCEPTANCE_CRITERIA_REF_LENGTH = 256
_MAX_RUNTIME_CAPTURE_KIND_LENGTH = 64
_MAX_PHASE_ID_LENGTH = 128
_MAX_RUN_ID_LENGTH = 128
_MAX_PAYLOAD_LENGTH = 65536
_MAX_OUTPUT_PATH_LENGTH = 255
_MAX_SUMMARY_LENGTH = 1024
_MAX_TAGS = 64
_MAX_TAG_LENGTH = 64

# ---------------------------------------------------------------------------
# Artifact constants
# ---------------------------------------------------------------------------

_ARIADNE_CAPTURE_VERSION = "1"


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


def _check_payload(payload: str, codes: list[str]) -> None:
    """Validate payload bounds and forbidden patterns."""
    if not payload:
        codes.append(REASON_OVERSIZED_CAPTURE)
        return

    if len(payload) > _MAX_PAYLOAD_LENGTH:
        codes.append(REASON_OVERSIZED_CAPTURE)

    # Check hidden reasoning patterns
    for pattern in _FORBIDDEN_HIDDEN_REASONING_PATTERNS:
        if pattern in payload:
            codes.append(REASON_HIDDEN_REASONING_NOT_ALLOWED)
            break

    # Check external URL-only proof
    stripped = payload.strip()
    if stripped.startswith("http://") or stripped.startswith("https://"):
        # If the payload is only a URL (no other meaningful content)
        remaining = stripped
        for prefix in ("http://", "https://"):
            if remaining.startswith(prefix):
                remaining = remaining[len(prefix):]
        # If after removing the protocol prefix, there's only a path (no spaces/newlines)
        if "\n" not in stripped and " " not in stripped:
            codes.append(REASON_EXTERNAL_URL_ONLY_NOT_ALLOWED)


def _check_tags(tags: FrozenSet[str], codes: list[str]) -> None:
    """Validate tags bounds."""
    if len(tags) > _MAX_TAGS:
        codes.append(REASON_OVERSIZED_CAPTURE)
        return

    for tag in tags:
        if not tag or tag.strip() == "":
            codes.append(REASON_OVERSIZED_CAPTURE)
            return
        if len(tag) > _MAX_TAG_LENGTH:
            codes.append(REASON_OVERSIZED_CAPTURE)
            return


# ---------------------------------------------------------------------------
# Capture function
# ---------------------------------------------------------------------------


def capture_proof(
    input_data: ProofCaptureInput,
    output_dir: str = ".",
) -> ProofCaptureResult:
    """Perform a deterministic local proof capture.

    Parameters
    ----------
    input_data:
        The input parameters for the capture.
    output_dir:
        The directory where the artifact will be written. Defaults to the
        current working directory.

    Returns
    -------
    ProofCaptureResult
        ``status=CAPTURED`` with ``artifact_path`` and ``proof_ref_fields``
        when the capture succeeds. ``status=REJECTED`` with ``reason_codes``
        when validation fails.
    """
    codes: list[str] = []

    # 1. Product state ref
    _check_non_empty_stripped(
        input_data.product_state_ref,
        _MAX_PRODUCT_STATE_REF_LENGTH,
        REASON_MISSING_PRODUCT_STATE_REF,
        codes,
    )

    # 2. Acceptance criteria ref
    _check_non_empty_stripped(
        input_data.acceptance_criteria_ref,
        _MAX_ACCEPTANCE_CRITERIA_REF_LENGTH,
        REASON_MISSING_ACCEPTANCE_CRITERIA_REF,
        codes,
    )

    # 3. Runtime capture kind
    _check_non_empty_stripped(
        input_data.runtime_capture_kind,
        _MAX_RUNTIME_CAPTURE_KIND_LENGTH,
        REASON_MISSING_RUNTIME_CAPTURE_KIND,
        codes,
    )

    # 3b. Arbitrary command execution check
    if input_data.runtime_capture_kind.strip() == "command_execution":
        codes.append(REASON_ARBITRARY_COMMAND_EXECUTION_NOT_ALLOWED)

    # 4. Phase identity
    _check_non_empty_stripped(
        input_data.phase_id,
        _MAX_PHASE_ID_LENGTH,
        REASON_MISSING_PHASE_IDENTITY,
        codes,
    )

    # 5. Run identity
    _check_non_empty_stripped(
        input_data.run_id,
        _MAX_RUN_ID_LENGTH,
        REASON_MISSING_RUN_IDENTITY,
        codes,
    )

    # 6. Output path
    _check_output_path(input_data.output_path, codes)

    # 7. Payload
    _check_payload(input_data.payload, codes)

    # 8. Summary bounds
    if len(input_data.summary) > _MAX_SUMMARY_LENGTH:
        codes.append(REASON_OVERSIZED_CAPTURE)

    # 9. Tags bounds
    _check_tags(input_data.tags, codes)

    # --- Deterministic sort ---
    codes.sort()

    if codes:
        detail_lines = [f"  - {c}" for c in codes]
        details = "Proof capture rejected:\n" + "\n".join(detail_lines)
        return ProofCaptureResult(
            status=ProofCaptureStatus.REJECTED,
            reason_codes=tuple(codes),
            details=details,
        )

    # --- Build artifact ---
    artifact = {
        "ariadne_capture_version": _ARIADNE_CAPTURE_VERSION,
        "product_state_ref": input_data.product_state_ref,
        "acceptance_criteria_ref": input_data.acceptance_criteria_ref,
        "runtime_capture_kind": input_data.runtime_capture_kind,
        "phase_id": input_data.phase_id,
        "run_id": input_data.run_id,
        "payload": input_data.payload,
        "summary": input_data.summary,
        "tags": sorted(input_data.tags),
        "captured_at": None,  # deterministic; no wall-clock time
    }

    artifact_json = json.dumps(artifact, sort_keys=True, indent=2)

    # Derive runtime_capture_ref from SHA256 of artifact content
    sha256_hash = hashlib.sha256(artifact_json.encode("utf-8")).hexdigest()[:12]
    runtime_capture_ref = f"capture-{input_data.runtime_capture_kind}-{sha256_hash}"

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

    # Build proof_ref-compatible fields
    proof_ref_fields = {
        "product_state_ref": input_data.product_state_ref,
        "acceptance_criteria_ref": input_data.acceptance_criteria_ref,
        "runtime_capture_ref": runtime_capture_ref,
        "artifact_path": output_path,
        "phase_id": input_data.phase_id,
        "run_id": input_data.run_id,
        "summary": input_data.summary,
        "tags": sorted(input_data.tags),
    }

    return ProofCaptureResult(
        status=ProofCaptureStatus.CAPTURED,
        reason_codes=(),
        artifact_path=output_path,
        proof_ref_fields=proof_ref_fields,
        details=None,
    )
