"""
Deterministic local Gate Evidence Bundle for Ariadne.

Defines ``GateEvidenceBundleInput``, ``GateEvidenceBundleResult``,
``GateEvidenceBundleStatus``, and ``build_gate_evidence_bundle()`` —
a deterministic, local function that verifies internal consistency across
frozen acceptance criteria, captured proof references, and a gate-ready
handoff packet, then writes a bounded bundle artifact.

Core principle:
    The gate evidence bundle does NOT evaluate criteria or approve gates.
    It only validates that all references are linked and consistent.
"""

from __future__ import annotations

import dataclasses
import enum
import hashlib
import json
import os
from typing import Optional, Tuple


# ---------------------------------------------------------------------------
# GateEvidenceBundleStatus — final verdict
# ---------------------------------------------------------------------------


class GateEvidenceBundleStatus(str, enum.Enum):
    """Final verdict for a gate evidence bundle operation."""

    BUNDLED = "bundled"
    REJECTED = "rejected"


# ---------------------------------------------------------------------------
# GateEvidenceBundleInput — input parameters
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class GateEvidenceBundleInput:
    """Input parameters for building a gate evidence bundle."""

    product_state_ref: str
    acceptance_criteria_ref: str
    phase_id: str
    run_id: str
    proof_ref_ids: Tuple[str, ...]  # Admissible proof ref IDs
    runtime_capture_refs: Tuple[str, ...]  # Proof capture refs from proof_capture output
    handoff_packet_path: str  # Path to handoff packet JSON file
    acceptance_criteria_path: str  # Path to frozen acceptance criteria artifact
    output_path: str  # Bounded local file path for bundle artifact
    capture_artifact_paths: Tuple[str, ...]  # Paths to proof capture artifacts
    gate_id: str = ""  # From handoff packet (for consistency check)
    actor_or_role: str = ""  # From handoff packet (for consistency check)


# ---------------------------------------------------------------------------
# GateEvidenceBundleResult — bundle result
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class GateEvidenceBundleResult:
    """Result of a gate evidence bundle operation."""

    status: GateEvidenceBundleStatus
    reason_codes: Tuple[str, ...]  # empty if bundled
    artifact_path: Optional[str] = None  # set only when bundled
    bundle_ref: Optional[str] = None  # SHA256 of bundle artifact; set only when bundled
    consistency_summary: Optional[str] = None  # human-readable summary; set only when bundled
    details: Optional[str] = None


# ---------------------------------------------------------------------------
# Stable reason codes
# ---------------------------------------------------------------------------

REASON_MISSING_PRODUCT_STATE_REF = "missing_product_state_ref"
REASON_MISSING_ACCEPTANCE_CRITERIA_REF = "missing_acceptance_criteria_ref"
REASON_MISSING_HANDOFF_PACKET = "missing_handoff_packet"
REASON_MISSING_PROOF_REFS = "missing_proof_refs"
REASON_MISSING_CAPTURE_REFS = "missing_capture_refs"
REASON_MISSING_PHASE_IDENTITY = "missing_phase_identity"
REASON_MISSING_RUN_IDENTITY = "missing_run_identity"
REASON_INCONSISTENT_PRODUCT_STATE_REF = "inconsistent_product_state_ref"
REASON_INCONSISTENT_ACCEPTANCE_CRITERIA_REF = "inconsistent_acceptance_criteria_ref"
REASON_INCONSISTENT_PHASE_IDENTITY = "inconsistent_phase_identity"
REASON_INCONSISTENT_RUN_IDENTITY = "inconsistent_run_identity"
REASON_INADMISSIBLE_PROOF_REF = "inadmissible_proof_ref"
REASON_UNKNOWN_CAPTURE_REF = "unknown_capture_ref"
REASON_UNBOUNDED_BUNDLE_OUTPUT_PATH = "unbounded_bundle_output_path"
REASON_OVERSIZED_BUNDLE = "oversized_bundle"
REASON_HIDDEN_REASONING_NOT_ALLOWED = "hidden_reasoning_not_allowed"
REASON_EXTERNAL_URL_ONLY_NOT_ALLOWED = "external_url_only_not_allowed"

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
_MAX_PHASE_ID_LENGTH = 128
_MAX_RUN_ID_LENGTH = 128
_MAX_PROOF_REF_ID_LENGTH = 256
_MAX_CAPTURE_REF_LENGTH = 256
_MAX_PATH_LENGTH = 255
_MAX_GATE_ID_LENGTH = 128
_MAX_ACTOR_OR_ROLE_LENGTH = 128
_MAX_BUNDLE_SIZE = 1048576  # 1MB

# ---------------------------------------------------------------------------
# Artifact constants
# ---------------------------------------------------------------------------

_ARIADNE_BUNDLE_VERSION = "1"


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _check_non_empty_stripped(value: str, max_len: int, reason: str, codes: list[str]) -> None:
    """Append *reason* to *codes* if *value* is empty or whitespace-only."""
    if not value or value.strip() == "":
        codes.append(reason)
    elif len(value) > max_len:
        codes.append(reason)


def _check_path_safe(path: str, reason: str, codes: list[str]) -> None:
    """Validate path boundedness."""
    if not path or path.strip() == "":
        codes.append(reason)
        return

    p = path.strip()
    if len(p) > _MAX_PATH_LENGTH:
        codes.append(reason)
        return
    if p.startswith("/"):
        codes.append(reason)
        return
    if ".." in p.split("/"):
        codes.append(reason)


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


# ---------------------------------------------------------------------------
# Bundle function
# ---------------------------------------------------------------------------


def build_gate_evidence_bundle(
    input_data: GateEvidenceBundleInput,
    output_dir: str = ".",
) -> GateEvidenceBundleResult:
    """Build a gate evidence bundle verifying cross-artifact consistency.

    Parameters
    ----------
    input_data:
        The input parameters for the bundle operation.
    output_dir:
        The directory where the bundle artifact will be written. Defaults to
        the current working directory.

    Returns
    -------
    GateEvidenceBundleResult
        ``status=BUNDLED`` with ``bundle_ref``, ``artifact_path``, and
        ``consistency_summary`` when all consistency checks pass.
        ``status=REJECTED`` with ``reason_codes`` when validation fails.
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
        REASON_MISSING_PHASE_IDENTITY,
        codes,
    )
    _check_non_empty_stripped(
        input_data.run_id,
        _MAX_RUN_ID_LENGTH,
        REASON_MISSING_RUN_IDENTITY,
        codes,
    )

    # 2. Proof ref IDs
    if not input_data.proof_ref_ids:
        codes.append(REASON_MISSING_PROOF_REFS)

    # 3. Path safety (only for output_path — artifact paths can be absolute)
    _check_path_safe(input_data.output_path, REASON_UNBOUNDED_BUNDLE_OUTPUT_PATH, codes)

    # 4. Check that artifact paths are non-empty
    if not input_data.handoff_packet_path or input_data.handoff_packet_path.strip() == "":
        codes.append(REASON_MISSING_HANDOFF_PACKET)
    if not input_data.acceptance_criteria_path or input_data.acceptance_criteria_path.strip() == "":
        codes.append(REASON_MISSING_ACCEPTANCE_CRITERIA_REF)
    for cap_path in input_data.capture_artifact_paths:
        if not cap_path or cap_path.strip() == "":
            codes.append(REASON_UNKNOWN_CAPTURE_REF)

    # If basic validation failed, return early
    if codes:
        codes.sort()
        detail_lines = [f"  - {c}" for c in codes]
        details = "Gate evidence bundle rejected:\n" + "\n".join(detail_lines)
        return GateEvidenceBundleResult(
            status=GateEvidenceBundleStatus.REJECTED,
            reason_codes=tuple(codes),
            details=details,
        )

    # 4. Read and validate handoff packet
    try:
        handoff_raw = open(input_data.handoff_packet_path, "r", encoding="utf-8").read()
        handoff_data = json.loads(handoff_raw)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        codes.append(REASON_MISSING_HANDOFF_PACKET)
        codes.sort()
        detail_lines = [f"  - {c}" for c in codes]
        details = "Gate evidence bundle rejected:\n" + "\n".join(detail_lines)
        return GateEvidenceBundleResult(
            status=GateEvidenceBundleStatus.REJECTED,
            reason_codes=tuple(codes),
            details=details,
        )

    # Check hidden reasoning in handoff payload
    if "payload" in handoff_data and isinstance(handoff_data["payload"], str):
        _check_hidden_reasoning(handoff_data["payload"], codes)
        _check_external_url_only(handoff_data["payload"], codes)

    # 5. Consistency: handoff packet fields
    hp_product_state = handoff_data.get("product_state_ref", "")
    hp_acceptance_criteria = handoff_data.get("acceptance_criteria_ref", "")
    hp_phase_id = handoff_data.get("phase_id", "")
    hp_run_id = handoff_data.get("run_id", "")
    hp_gate_id = handoff_data.get("gate_id", "")
    hp_proof_ref_ids = handoff_data.get("proof_ref_ids", [])

    if hp_product_state != input_data.product_state_ref:
        codes.append(REASON_INCONSISTENT_PRODUCT_STATE_REF)
    if hp_acceptance_criteria != input_data.acceptance_criteria_ref:
        codes.append(REASON_INCONSISTENT_ACCEPTANCE_CRITERIA_REF)
    if hp_phase_id != input_data.phase_id:
        codes.append(REASON_INCONSISTENT_PHASE_IDENTITY)
    if hp_run_id != input_data.run_id:
        codes.append(REASON_INCONSISTENT_RUN_IDENTITY)

    # 6. Handoff proof_ref_ids must be a superset of input proof_ref_ids
    hp_proof_set = set(hp_proof_ref_ids)
    input_proof_set = set(input_data.proof_ref_ids)
    if not hp_proof_set.issuperset(input_proof_set):
        codes.append(REASON_INADMISSIBLE_PROOF_REF)

    # 7. Read and validate acceptance criteria artifact
    try:
        criteria_raw = open(input_data.acceptance_criteria_path, "r", encoding="utf-8").read()
        criteria_data = json.loads(criteria_raw)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        codes.append(REASON_INCONSISTENT_ACCEPTANCE_CRITERIA_REF)

    # 8. Verify acceptance_criteria_ref via SHA256 of criteria artifact
    if codes.count(REASON_INCONSISTENT_ACCEPTANCE_CRITERIA_REF) == 0:
        criteria_sha256 = hashlib.sha256(criteria_raw.encode("utf-8")).hexdigest()[:16]
        if criteria_sha256 != input_data.acceptance_criteria_ref:
            codes.append(REASON_INCONSISTENT_ACCEPTANCE_CRITERIA_REF)

    # Extract criterion_ids from criteria artifact
    criterion_ids: list[str] = []
    if codes.count(REASON_INCONSISTENT_ACCEPTANCE_CRITERIA_REF) == 0:
        criteria_list = criteria_data.get("criteria", [])
        criterion_ids = [c.get("criterion_id", "") for c in criteria_list if isinstance(c, dict)]

    # 9. Read and validate capture artifacts
    found_capture_refs: set[str] = set()
    for cap_path in input_data.capture_artifact_paths:
        try:
            cap_raw = open(cap_path, "r", encoding="utf-8").read()
            cap_data = json.loads(cap_raw)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            codes.append(REASON_UNKNOWN_CAPTURE_REF)
            continue

        # Check hidden reasoning in capture payload
        if "payload" in cap_data and isinstance(cap_data["payload"], str):
            _check_hidden_reasoning(cap_data["payload"], codes)
            _check_external_url_only(cap_data["payload"], codes)

        # Extract runtime_capture_ref from capture artifact
        # The capture artifact has a "payload" field but the runtime_capture_ref
        # is not stored inside the artifact itself — it's derived from the artifact
        # content. We compute it the same way proof_capture does.
        # However, the capture artifact doesn't store runtime_capture_ref directly.
        # We need to check if the artifact content matches any of the input refs.
        # The proof_capture derives runtime_capture_ref as:
        #   capture-{kind}-{sha256_prefix}
        # We can verify by computing SHA256 of the artifact and checking if
        # any input ref matches the expected pattern.
        cap_kind = cap_data.get("runtime_capture_kind", "")
        cap_payload = cap_data.get("payload", "")
        cap_product_state = cap_data.get("product_state_ref", "")
        cap_acceptance_criteria = cap_data.get("acceptance_criteria_ref", "")

        # Compute the expected runtime_capture_ref
        # Reconstruct the artifact JSON that proof_capture would have produced
        cap_artifact_for_hash = {
            "ariadne_capture_version": cap_data.get("ariadne_capture_version", "1"),
            "product_state_ref": cap_product_state,
            "acceptance_criteria_ref": cap_acceptance_criteria,
            "runtime_capture_kind": cap_kind,
            "phase_id": cap_data.get("phase_id", ""),
            "run_id": cap_data.get("run_id", ""),
            "payload": cap_payload,
            "summary": cap_data.get("summary", ""),
            "tags": sorted(cap_data.get("tags", [])),
            "captured_at": None,
        }
        cap_artifact_json = json.dumps(cap_artifact_for_hash, sort_keys=True, indent=2)
        cap_sha256 = hashlib.sha256(cap_artifact_json.encode("utf-8")).hexdigest()[:12]
        expected_ref = f"capture-{cap_kind}-{cap_sha256}"

        if expected_ref in input_data.runtime_capture_refs:
            found_capture_refs.add(expected_ref)

    # 10. Check that all input runtime_capture_refs were found
    for ref in input_data.runtime_capture_refs:
        if ref not in found_capture_refs:
            codes.append(REASON_UNKNOWN_CAPTURE_REF)
            break

    # 11. Check for missing capture refs (if runtime_capture_refs is non-empty but none found)
    if input_data.runtime_capture_refs and not found_capture_refs:
        codes.append(REASON_MISSING_CAPTURE_REFS)

    # --- Deterministic sort ---
    codes.sort()

    if codes:
        detail_lines = [f"  - {c}" for c in codes]
        details = "Gate evidence bundle rejected:\n" + "\n".join(detail_lines)
        return GateEvidenceBundleResult(
            status=GateEvidenceBundleStatus.REJECTED,
            reason_codes=tuple(codes),
            details=details,
        )

    # --- Build canonical bundle artifact ---
    sorted_proof_ref_ids = sorted(input_data.proof_ref_ids)
    sorted_capture_refs = sorted(input_data.runtime_capture_refs)
    sorted_criterion_ids = sorted(criterion_ids)

    artifact = {
        "ariadne_bundle_version": _ARIADNE_BUNDLE_VERSION,
        "product_state_ref": input_data.product_state_ref,
        "acceptance_criteria_ref": input_data.acceptance_criteria_ref,
        "phase_id": input_data.phase_id,
        "run_id": input_data.run_id,
        "handoff_gate_id": hp_gate_id,
        "proof_ref_ids": sorted_proof_ref_ids,
        "runtime_capture_refs": sorted_capture_refs,
        "criterion_ids": sorted_criterion_ids,
        "capture_count": len(input_data.runtime_capture_refs),
        "criteria_canonical_ref": input_data.acceptance_criteria_ref,
        "bundled_at": None,  # deterministic; no wall-clock time
    }

    artifact_json = json.dumps(artifact, sort_keys=True, indent=2)

    # Derive bundle_ref from SHA256 of bundle artifact (first 16 hex chars)
    bundle_ref = hashlib.sha256(artifact_json.encode("utf-8")).hexdigest()[:16]

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

    # Build consistency summary
    consistency_summary = (
        f"Gate evidence bundle: {len(input_data.proof_ref_ids)} proof ref(s), "
        f"{len(input_data.runtime_capture_refs)} capture(s), "
        f"{len(criterion_ids)} criterion/criteria, "
        f"gate={hp_gate_id}"
    )

    return GateEvidenceBundleResult(
        status=GateEvidenceBundleStatus.BUNDLED,
        reason_codes=(),
        artifact_path=output_path,
        bundle_ref=bundle_ref,
        consistency_summary=consistency_summary,
        details=None,
    )
