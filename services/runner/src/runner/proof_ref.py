"""
Admissible proof reference runtime object for Ariadne.

Defines the ``ProofRef`` object — a reference to runtime-captured evidence that
is *admissible* only when tied to current product state, frozen acceptance
criteria, runtime capture, bounded artifact path, and phase/run identity.

Defines ``validate_proof_ref`` — a deterministic, pure function that
distinguishes admissible proof from agent claims.

Core principle:
    Agent output is not proof. Runtime-captured proof is evidence.
    The agent may be an executor, but not the notary of its own work.
"""

from __future__ import annotations

import dataclasses
import json
from typing import FrozenSet, Optional, Tuple


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class ProofRef:
    """A reference to runtime-captured evidence that may be admissible proof.

    A ProofRef is a claim that a particular runtime artifact constitutes
    admissible evidence for a specific claim about the system state.
    The ``validate_proof_ref`` function determines admissibility.
    """

    # Identity — ties proof to a specific phase/run
    run_id: str
    phase_id: str | None

    # Product state reference — what the system state was at time of capture
    product_state_ref: str  # e.g. sha256 of frozen acceptance criteria

    # Acceptance criteria reference — what was being verified
    acceptance_criteria_ref: str  # e.g. sha256 of a rubric pack

    # Runtime capture — how the evidence was produced
    runtime_capture_ref: str  # e.g. execution_result_id from substrate

    # Artifact path — where the evidence lives within the bounded store
    artifact_path: str  # relative, no "..", max 255 chars

    # Optional metadata
    summary: str = ""
    tags: FrozenSet[str] = dataclasses.field(default_factory=frozenset)

    def to_dict(self) -> dict:
        """Return a JSON-serializable dict for this ProofRef."""
        d = dataclasses.asdict(self)
        # frozenset serializes as a list; ensure deterministic sort
        d["tags"] = sorted(self.tags)
        return d

    def to_json(self) -> str:
        """Return a JSON string for this ProofRef."""
        return json.dumps(self.to_dict(), sort_keys=True)


@dataclasses.dataclass(frozen=True)
class ProofRefValidation:
    """Result of validating a ProofRef for admissibility."""

    admissible: bool
    reason_codes: Tuple[str, ...]  # empty if admissible, one or more if not
    details: str | None = None


# ---------------------------------------------------------------------------
# Constants — reason codes
# ---------------------------------------------------------------------------

REASON_MISSING_PRODUCT_STATE_REF = "missing_product_state_ref"
REASON_MISSING_ACCEPTANCE_CRITERIA_REF = "missing_acceptance_criteria_ref"
REASON_MISSING_RUNTIME_CAPTURE_REF = "missing_runtime_capture_ref"
REASON_MISSING_ARTIFACT_PATH = "missing_artifact_path"
REASON_UNBOUNDED_ARTIFACT_PATH = "unbounded_artifact_path"
REASON_MISSING_PHASE_OR_RUN_IDENTITY = "missing_phase_or_run_identity"
REASON_AGENT_CLAIM_ONLY = "agent_claim_only"
REASON_STALE_OR_UNLINKED_STATE = "stale_or_unlinked_state"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_proof_ref(
    proof_ref: ProofRef,
    current_product_state_ref: str,
) -> ProofRefValidation:
    """Validate a ProofRef for admissibility.

    Parameters
    ----------
    proof_ref:
        The ProofRef to validate.
    current_product_state_ref:
        The current system state reference (e.g. sha256 of latest frozen
        acceptance criteria hash). The validator does not compute or discover
        this value — it only checks equality against
        ``proof_ref.product_state_ref``.

    Returns
    -------
    ProofRefValidation
        ``admissible=True`` and ``reason_codes=()`` only when ALL required
        fields are present and the product state matches.
    """
    codes: list[str] = []

    # 1. Product state ref
    if not proof_ref.product_state_ref or proof_ref.product_state_ref.strip() == "":
        codes.append(REASON_MISSING_PRODUCT_STATE_REF)

    # 2. Acceptance criteria ref
    if not proof_ref.acceptance_criteria_ref or proof_ref.acceptance_criteria_ref.strip() == "":
        codes.append(REASON_MISSING_ACCEPTANCE_CRITERIA_REF)

    # 3. Runtime capture ref
    if not proof_ref.runtime_capture_ref or proof_ref.runtime_capture_ref.strip() == "":
        codes.append(REASON_MISSING_RUNTIME_CAPTURE_REF)

    # 4. Artifact path — missing
    if not proof_ref.artifact_path or proof_ref.artifact_path.strip() == "":
        codes.append(REASON_MISSING_ARTIFACT_PATH)
    else:
        # 4b. Artifact path — unbounded
        path = proof_ref.artifact_path
        is_unbounded = False
        unbounded_detail = ""

        if path.startswith("/"):
            is_unbounded = True
            unbounded_detail = "path starts with '/'"
        elif ".." in path.split("/"):
            is_unbounded = True
            unbounded_detail = "path contains '..'"
        elif len(path) > 255:
            is_unbounded = True
            unbounded_detail = f"path length {len(path)} exceeds 255"

        if is_unbounded:
            codes.append(REASON_UNBOUNDED_ARTIFACT_PATH)
        else:
            # 4c. Agent-claim-only: basename shorter than 3 characters
            basename = path.rstrip("/").rsplit("/", 1)[-1] if "/" in path.rstrip("/") else path
            if len(basename) < 3:
                codes.append(REASON_AGENT_CLAIM_ONLY)

    # 5. Run/phase identity — run_id is required even if phase_id is present
    if not proof_ref.run_id:
        codes.append(REASON_MISSING_PHASE_OR_RUN_IDENTITY)

    # 6. Stale or unlinked product state
    if (
        proof_ref.product_state_ref
        and proof_ref.product_state_ref.strip()
        and proof_ref.product_state_ref != current_product_state_ref
    ):
        codes.append(REASON_STALE_OR_UNLINKED_STATE)

    # --- Deterministic sort ---
    codes.sort()

    admissible = len(codes) == 0
    details = None
    if not admissible:
        detail_lines = [f"  - {c}" for c in codes]
        details = "ProofRef is not admissible:\n" + "\n".join(detail_lines)

    return ProofRefValidation(
        admissible=admissible,
        reason_codes=tuple(codes),
        details=details,
    )
