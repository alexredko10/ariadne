"""
Gate-ready handoff packet runtime object for Ariadne.

Defines the ``GateReadyHandoffPacket`` — a deterministic, JSON-serializable
object that carries gate-ready context across Ariadne workflow phases.

Defines ``validate_handoff_packet`` — a deterministic, pure function that
validates a handoff packet against current product state and admissible proof
references.

Core principle:
    The handoff packet is evidence of gate readiness, not an execution
    authorization. It does not bypass the Apply Gate or human review boundary.
"""

from __future__ import annotations

import dataclasses
import enum
import json
from typing import Optional, Tuple


# ---------------------------------------------------------------------------
# HandoffPacketStatus — final verdict
# ---------------------------------------------------------------------------


class HandoffPacketStatus(str, enum.Enum):
    """Final verdict for a gate-ready handoff packet validation."""

    GATE_READY = "gate_ready"
    NOT_GATE_READY = "not_gate_ready"


# ---------------------------------------------------------------------------
# HandoffPacketValidation — validation result
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class HandoffPacketValidation:
    """Result of validating a GateReadyHandoffPacket."""

    status: HandoffPacketStatus
    reason_codes: Tuple[str, ...]  # sorted, stable
    details: Optional[str] = None


# ---------------------------------------------------------------------------
# Stable reason codes
# ---------------------------------------------------------------------------

REASON_MISSING_PRODUCT_STATE_REF = "missing_product_state_ref"
REASON_MISSING_ACCEPTANCE_CRITERIA_REF = "missing_acceptance_criteria_ref"
REASON_MISSING_PHASE_IDENTITY = "missing_phase_identity"
REASON_MISSING_RUN_IDENTITY = "missing_run_identity"
REASON_MISSING_GATE = "missing_gate"
REASON_MISSING_ACTOR_OR_ROLE = "missing_actor_or_role"
REASON_MISSING_PROOF_REFS = "missing_proof_refs"
REASON_INADMISSIBLE_PROOF_REF = "inadmissible_proof_ref"
REASON_STALE_OR_UNLINKED_STATE = "stale_or_unlinked_state"
REASON_HIDDEN_REASONING_NOT_ALLOWED = "hidden_reasoning_not_allowed"
REASON_UNBOUNDED_PAYLOAD = "unbounded_payload"

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

_MAX_PAYLOAD_LENGTH = 65536
_MAX_PRODUCT_STATE_REF_LENGTH = 256
_MAX_ACCEPTANCE_CRITERIA_REF_LENGTH = 256
_MAX_PHASE_ID_LENGTH = 128
_MAX_RUN_ID_LENGTH = 128
_MAX_GATE_ID_LENGTH = 128
_MAX_ACTOR_OR_ROLE_LENGTH = 128
_MAX_PROOF_REF_ID_LENGTH = 256
_MAX_METADATA_PAIRS = 64
_MAX_METADATA_KEY_LENGTH = 128
_MAX_METADATA_VALUE_LENGTH = 4096


# ---------------------------------------------------------------------------
# GateReadyHandoffPacket — frozen dataclass
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class GateReadyHandoffPacket:
    """A deterministic, JSON-serializable gate-ready handoff packet.

    Carries all context required to transfer frozen gate state between
    Ariadne workflow phases.
    """

    # Identity — ties packet to a specific product state
    product_state_ref: str  # Hash or identity of the current product state

    # Acceptance criteria — frozen reference
    acceptance_criteria_ref: str  # Frozen acceptance criteria reference

    # Phase/run identity
    phase_id: str  # Phase/step identity (e.g. "phase-1", "review")
    run_id: str  # Unique run/execution identity

    # Target gate/action
    gate_id: str  # Target gate or action identity

    # Actor/role identity
    actor_or_role: str  # Actor identity or role name

    # Admissible proof ref IDs (validated via PR 0101)
    proof_ref_ids: Tuple[str, ...]  # At least one entry

    # Bounded plain-text payload
    payload: str  # Max 65536 chars

    # Optional ordered key-value metadata
    metadata: Tuple[Tuple[str, str], ...] = ()  # Max 64 pairs

    def to_dict(self) -> dict:
        """Return a JSON-serializable dict for this packet."""
        d = dataclasses.asdict(self)
        # Ensure tuple fields serialize as sorted lists for determinism
        d["proof_ref_ids"] = sorted(self.proof_ref_ids)
        d["metadata"] = sorted(self.metadata)
        return d

    def to_json(self) -> str:
        """Return a JSON string for this packet."""
        return json.dumps(self.to_dict(), sort_keys=True)


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _check_non_empty_stripped(value: str, max_len: int, reason: str, codes: list[str]) -> None:
    """Append *reason* to *codes* if *value* is empty or whitespace-only."""
    if not value or value.strip() == "":
        codes.append(reason)
    elif len(value) > max_len:
        codes.append(reason)


def _check_proof_ref_ids(
    proof_ref_ids: Tuple[str, ...],
    admissible_ref_ids: frozenset[str],
    codes: list[str],
) -> None:
    """Validate proof_ref_ids presence and admissibility."""
    if not proof_ref_ids:
        codes.append(REASON_MISSING_PROOF_REFS)
        return

    # Check each ID is non-empty and within bounds
    for ref_id in proof_ref_ids:
        if not ref_id or ref_id.strip() == "":
            codes.append(REASON_MISSING_PROOF_REFS)
            break

    # Check admissibility
    for ref_id in proof_ref_ids:
        if ref_id and ref_id.strip() and ref_id not in admissible_ref_ids:
            codes.append(REASON_INADMISSIBLE_PROOF_REF)
            break


def _check_payload(payload: str, codes: list[str]) -> None:
    """Validate payload bounds and hidden reasoning exclusion."""
    if not payload:
        codes.append(REASON_UNBOUNDED_PAYLOAD)
        return

    if len(payload) > _MAX_PAYLOAD_LENGTH:
        codes.append(REASON_UNBOUNDED_PAYLOAD)

    for pattern in _FORBIDDEN_HIDDEN_REASONING_PATTERNS:
        if pattern in payload:
            codes.append(REASON_HIDDEN_REASONING_NOT_ALLOWED)
            break


def _check_metadata(metadata: Tuple[Tuple[str, str], ...], codes: list[str]) -> None:
    """Validate metadata bounds."""
    if len(metadata) > _MAX_METADATA_PAIRS:
        codes.append(REASON_UNBOUNDED_PAYLOAD)
        return

    for key, value in metadata:
        if not key or key.strip() == "":
            codes.append(REASON_UNBOUNDED_PAYLOAD)
            return
        if len(key) > _MAX_METADATA_KEY_LENGTH:
            codes.append(REASON_UNBOUNDED_PAYLOAD)
            return
        if len(value) > _MAX_METADATA_VALUE_LENGTH:
            codes.append(REASON_UNBOUNDED_PAYLOAD)
            return


# ---------------------------------------------------------------------------
# Public validation function
# ---------------------------------------------------------------------------


def validate_handoff_packet(
    packet: GateReadyHandoffPacket,
    current_product_state_ref: str,
    admissible_ref_ids: frozenset[str],
) -> HandoffPacketValidation:
    """Validate a GateReadyHandoffPacket for gate readiness.

    Parameters
    ----------
    packet:
        The handoff packet to validate.
    current_product_state_ref:
        The current system state reference. The validator does not compute or
        discover this value — it only checks equality against
        ``packet.product_state_ref``.
    admissible_ref_ids:
        The set of admissible proof ref IDs (pre-validated via PR 0101
        ``validate_proof_ref``). The handoff packet does NOT re-run proof
        validation — it only checks membership in this set.

    Returns
    -------
    HandoffPacketValidation
        ``status=GATE_READY`` and ``reason_codes=()`` only when ALL required
        fields are present, product state matches, all proof ref IDs are
        admissible, payload is within bounds, and no hidden reasoning patterns
        are detected.
    """
    codes: list[str] = []

    # 1. Product state ref
    _check_non_empty_stripped(
        packet.product_state_ref,
        _MAX_PRODUCT_STATE_REF_LENGTH,
        REASON_MISSING_PRODUCT_STATE_REF,
        codes,
    )

    # 2. Acceptance criteria ref
    _check_non_empty_stripped(
        packet.acceptance_criteria_ref,
        _MAX_ACCEPTANCE_CRITERIA_REF_LENGTH,
        REASON_MISSING_ACCEPTANCE_CRITERIA_REF,
        codes,
    )

    # 3. Phase identity
    _check_non_empty_stripped(
        packet.phase_id,
        _MAX_PHASE_ID_LENGTH,
        REASON_MISSING_PHASE_IDENTITY,
        codes,
    )

    # 4. Run identity
    _check_non_empty_stripped(
        packet.run_id,
        _MAX_RUN_ID_LENGTH,
        REASON_MISSING_RUN_IDENTITY,
        codes,
    )

    # 5. Gate identity
    _check_non_empty_stripped(
        packet.gate_id,
        _MAX_GATE_ID_LENGTH,
        REASON_MISSING_GATE,
        codes,
    )

    # 6. Actor or role
    _check_non_empty_stripped(
        packet.actor_or_role,
        _MAX_ACTOR_OR_ROLE_LENGTH,
        REASON_MISSING_ACTOR_OR_ROLE,
        codes,
    )

    # 7. Proof ref IDs — presence and admissibility
    _check_proof_ref_ids(packet.proof_ref_ids, admissible_ref_ids, codes)

    # 8. Stale or unlinked product state
    if (
        packet.product_state_ref
        and packet.product_state_ref.strip()
        and packet.product_state_ref != current_product_state_ref
    ):
        codes.append(REASON_STALE_OR_UNLINKED_STATE)

    # 9. Payload — bounds and hidden reasoning
    _check_payload(packet.payload, codes)

    # 10. Metadata — bounds
    _check_metadata(packet.metadata, codes)

    # --- Deterministic sort ---
    codes.sort()

    gate_ready = len(codes) == 0
    status = HandoffPacketStatus.GATE_READY if gate_ready else HandoffPacketStatus.NOT_GATE_READY
    details = None
    if not gate_ready:
        detail_lines = [f"  - {c}" for c in codes]
        details = "Handoff packet is not gate-ready:\n" + "\n".join(detail_lines)

    return HandoffPacketValidation(
        status=status,
        reason_codes=tuple(codes),
        details=details,
    )
