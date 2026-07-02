"""
Platform-runner doctor command for Ariadne: validates that key runner modules are importable.

This module exposes:
- ``run_doctor()`` → returns 0 on success, 1 on failure
- ``main(argv)`` → argument-parsing entry point
- ``validate_proof_file(path)`` → validates a JSON proof ref file
- ``validate_handoff_file(path, ...)`` → validates a JSON handoff packet file
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from .acceptance_criteria import (
    AcceptanceCriteriaFreezeInput,
    freeze_acceptance_criteria,
)
from .gate_evidence import (
    GateEvidenceBundleInput,
    build_gate_evidence_bundle,
)
from .handoff_packet import (
    GateReadyHandoffPacket,
    validate_handoff_packet,
)
from .backlog_surface import (
    BacklogSurfaceInput,
    BacklogSurfaceStatus,
    build_backlog_surface,
)
from .improvement_backlog import (
    BacklogItemInput,
    enqueue_backlog_item,
    list_backlog,
    archive_backlog_item,
)
from .improvement_candidate import (
    ImprovementCandidateInput,
    propose_improvement_candidate,
)
from .proof_capture import (
    ProofCaptureInput,
    capture_proof,
)
from .proof_ref import (
    ProofRef,
    validate_proof_ref,
)
from .session_continuity import (
    SessionContinuityInput,
    build_session_continuity_packet,
)


EXPECTED_OUTPUT_LINES = (
    "platform-runner doctor",
    "runner import: ok",
    "patch models: ok",
    "patch safety: ok",
)


# ---------------------------------------------------------------------------
# Doctor checks
# ---------------------------------------------------------------------------


def run_doctor() -> int:
    """Run all doctor checks and print results to stdout.

    Returns 0 if all checks pass, 1 otherwise.
    """
    checks = (
        ("runner import", "runner"),
        ("patch models", "runner.models"),
        ("patch safety", "runner.patch"),
    )

    print(EXPECTED_OUTPUT_LINES[0])

    for label, module_name in checks:
        try:
            importlib.import_module(module_name)
        except Exception as exc:
            print(f"{label}: failed", file=sys.stderr)
            print(f"{module_name}: {exc.__class__.__name__}: {exc}", file=sys.stderr)
            return 1
        print(f"{label}: ok")

    return 0


# ---------------------------------------------------------------------------
# Validate proof file
# ---------------------------------------------------------------------------


def validate_proof_file(path: str) -> dict:
    """Read a JSON file, parse as ProofRef, and validate.

    Parameters
    ----------
    path:
        Path to a JSON file containing ProofRef data.

    Returns
    -------
    dict
        A JSON-serializable result dict with keys:
        ``status``, ``command``, ``result``, ``error``.
    """
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return {
            "status": "error",
            "command": "validate proof",
            "result": None,
            "error": f"File not found: {path}",
        }
    except OSError as exc:
        return {
            "status": "error",
            "command": "validate proof",
            "result": None,
            "error": f"Error reading file: {exc}",
        }

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return {
            "status": "error",
            "command": "validate proof",
            "result": None,
            "error": f"Invalid JSON: {exc}",
        }

    if not isinstance(data, dict):
        return {
            "status": "error",
            "command": "validate proof",
            "result": None,
            "error": "JSON root must be an object",
        }

    try:
        proof_ref = ProofRef(**data)
    except (TypeError, ValueError) as exc:
        return {
            "status": "error",
            "command": "validate proof",
            "result": None,
            "error": f"Invalid ProofRef data: {exc}",
        }

    # Determine current_product_state_ref from the proof ref itself
    # (the file may embed it; caller can override via CLI flag in future)
    current_product_state_ref = proof_ref.product_state_ref

    validation = validate_proof_ref(proof_ref, current_product_state_ref)

    return {
        "status": "ok",
        "command": "validate proof",
        "result": {
            "admissible": validation.admissible,
            "reason_codes": list(validation.reason_codes),
            "details": validation.details,
        },
        "error": None,
    }


# ---------------------------------------------------------------------------
# Validate handoff file
# ---------------------------------------------------------------------------


def validate_handoff_file(
    path: str,
    current_product_state_ref: str | None = None,
    admissible_ref_ids: list[str] | None = None,
) -> dict:
    """Read a JSON file, parse as GateReadyHandoffPacket, and validate.

    Parameters
    ----------
    path:
        Path to a JSON file containing GateReadyHandoffPacket data.
    current_product_state_ref:
        Override for the current product state ref. If None, uses the value
        from the packet itself (which means stale-state check is skipped).
    admissible_ref_ids:
        List of admissible proof ref IDs. If None, uses the packet's own
        proof_ref_ids (which means inadmissible-proof-ref check is skipped).

    Returns
    -------
    dict
        A JSON-serializable result dict with keys:
        ``status``, ``command``, ``result``, ``error``.
    """
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return {
            "status": "error",
            "command": "validate handoff",
            "result": None,
            "error": f"File not found: {path}",
        }
    except OSError as exc:
        return {
            "status": "error",
            "command": "validate handoff",
            "result": None,
            "error": f"Error reading file: {exc}",
        }

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return {
            "status": "error",
            "command": "validate handoff",
            "result": None,
            "error": f"Invalid JSON: {exc}",
        }

    if not isinstance(data, dict):
        return {
            "status": "error",
            "command": "validate handoff",
            "result": None,
            "error": "JSON root must be an object",
        }

    # Convert proof_ref_ids list to tuple if present
    if "proof_ref_ids" in data and isinstance(data["proof_ref_ids"], list):
        data["proof_ref_ids"] = tuple(data["proof_ref_ids"])

    # Convert metadata list of lists to tuple of tuples if present
    if "metadata" in data and isinstance(data["metadata"], list):
        data["metadata"] = tuple(tuple(pair) for pair in data["metadata"])

    try:
        packet = GateReadyHandoffPacket(**data)
    except (TypeError, ValueError) as exc:
        return {
            "status": "error",
            "command": "validate handoff",
            "result": None,
            "error": f"Invalid GateReadyHandoffPacket data: {exc}",
        }

    # Resolve validation parameters
    state_ref = current_product_state_ref if current_product_state_ref is not None else packet.product_state_ref
    ref_ids = frozenset(admissible_ref_ids) if admissible_ref_ids is not None else frozenset(packet.proof_ref_ids)

    validation = validate_handoff_packet(packet, state_ref, ref_ids)

    return {
        "status": "ok",
        "command": "validate handoff",
        "result": {
            "status": validation.status.value,
            "reason_codes": list(validation.reason_codes),
            "details": validation.details,
        },
        "error": None,
    }


# ---------------------------------------------------------------------------
# Capture proof file
# ---------------------------------------------------------------------------


def capture_proof_file(path: str, output_dir: str = ".") -> dict:
    """Read a JSON file, parse as ProofCaptureInput, and capture proof.

    Parameters
    ----------
    path:
        Path to a JSON file containing ProofCaptureInput data.
    output_dir:
        Directory where the artifact will be written.

    Returns
    -------
    dict
        A JSON-serializable result dict with keys:
        ``status``, ``command``, ``result``, ``error``.
    """
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return {
            "status": "error",
            "command": "capture proof",
            "result": None,
            "error": f"File not found: {path}",
        }
    except OSError as exc:
        return {
            "status": "error",
            "command": "capture proof",
            "result": None,
            "error": f"Error reading file: {exc}",
        }

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return {
            "status": "error",
            "command": "capture proof",
            "result": None,
            "error": f"Invalid JSON: {exc}",
        }

    if not isinstance(data, dict):
        return {
            "status": "error",
            "command": "capture proof",
            "result": None,
            "error": "JSON root must be an object",
        }

    # Convert tags list to frozenset if present
    if "tags" in data and isinstance(data["tags"], list):
        data["tags"] = frozenset(data["tags"])

    try:
        capture_input = ProofCaptureInput(**data)
    except (TypeError, ValueError) as exc:
        return {
            "status": "error",
            "command": "capture proof",
            "result": None,
            "error": f"Invalid ProofCaptureInput data: {exc}",
        }

    result = capture_proof(capture_input, output_dir=output_dir)

    return {
        "status": "ok",
        "command": "capture proof",
        "result": {
            "capture_status": result.status.value,
            "reason_codes": list(result.reason_codes),
            "artifact_path": result.artifact_path,
            "proof_ref_fields": result.proof_ref_fields,
            "details": result.details,
        },
        "error": None,
    }


# ---------------------------------------------------------------------------
# Freeze acceptance criteria file
# ---------------------------------------------------------------------------


def freeze_acceptance_criteria_file(path: str, output_dir: str = ".") -> dict:
    """Read a JSON file, parse as AcceptanceCriteriaFreezeInput, and freeze.

    Parameters
    ----------
    path:
        Path to a JSON file containing AcceptanceCriteriaFreezeInput data.
    output_dir:
        Directory where the artifact will be written.

    Returns
    -------
    dict
        A JSON-serializable result dict with keys:
        ``status``, ``command``, ``result``, ``error``.
    """
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return {
            "status": "error",
            "command": "freeze criteria",
            "result": None,
            "error": f"File not found: {path}",
        }
    except OSError as exc:
        return {
            "status": "error",
            "command": "freeze criteria",
            "result": None,
            "error": f"Error reading file: {exc}",
        }

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return {
            "status": "error",
            "command": "freeze criteria",
            "result": None,
            "error": f"Invalid JSON: {exc}",
        }

    if not isinstance(data, dict):
        return {
            "status": "error",
            "command": "freeze criteria",
            "result": None,
            "error": "JSON root must be an object",
        }

    # Convert criteria list to tuple of AcceptanceCriterion
    if "criteria" in data and isinstance(data["criteria"], list):
        from .acceptance_criteria import AcceptanceCriterion
        criteria_list = []
        for c in data["criteria"]:
            if isinstance(c, dict):
                criteria_list.append(AcceptanceCriterion(
                    criterion_id=c.get("criterion_id", ""),
                    description=c.get("description", ""),
                ))
            else:
                return {
                    "status": "error",
                    "command": "freeze criteria",
                    "result": None,
                    "error": "Each criterion must be an object with criterion_id and description",
                }
        data["criteria"] = tuple(criteria_list)

    try:
        freeze_input = AcceptanceCriteriaFreezeInput(**data)
    except (TypeError, ValueError) as exc:
        return {
            "status": "error",
            "command": "freeze criteria",
            "result": None,
            "error": f"Invalid AcceptanceCriteriaFreezeInput data: {exc}",
        }

    result = freeze_acceptance_criteria(freeze_input, output_dir=output_dir)

    return {
        "status": "ok",
        "command": "freeze criteria",
        "result": {
            "freeze_status": result.status.value,
            "reason_codes": list(result.reason_codes),
            "artifact_path": result.artifact_path,
            "acceptance_criteria_ref": result.acceptance_criteria_ref,
            "criteria_count": result.criteria_count,
            "criterion_ids": list(result.criterion_ids) if result.criterion_ids else None,
            "details": result.details,
        },
        "error": None,
    }


# ---------------------------------------------------------------------------
# Build gate evidence bundle file
# ---------------------------------------------------------------------------


def build_gate_evidence_bundle_file(path: str, output_dir: str = ".") -> dict:
    """Read a JSON file, parse as GateEvidenceBundleInput, and build bundle.

    Parameters
    ----------
    path:
        Path to a JSON file containing GateEvidenceBundleInput data.
    output_dir:
        Directory where the bundle artifact will be written.

    Returns
    -------
    dict
        A JSON-serializable result dict with keys:
        ``status``, ``command``, ``result``, ``error``.
    """
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return {
            "status": "error",
            "command": "bundle evidence",
            "result": None,
            "error": f"File not found: {path}",
        }
    except OSError as exc:
        return {
            "status": "error",
            "command": "bundle evidence",
            "result": None,
            "error": f"Error reading file: {exc}",
        }

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return {
            "status": "error",
            "command": "bundle evidence",
            "result": None,
            "error": f"Invalid JSON: {exc}",
        }

    if not isinstance(data, dict):
        return {
            "status": "error",
            "command": "bundle evidence",
            "result": None,
            "error": "JSON root must be an object",
        }

    # Convert list fields to tuples
    if "proof_ref_ids" in data and isinstance(data["proof_ref_ids"], list):
        data["proof_ref_ids"] = tuple(data["proof_ref_ids"])
    if "runtime_capture_refs" in data and isinstance(data["runtime_capture_refs"], list):
        data["runtime_capture_refs"] = tuple(data["runtime_capture_refs"])
    if "capture_artifact_paths" in data and isinstance(data["capture_artifact_paths"], list):
        data["capture_artifact_paths"] = tuple(data["capture_artifact_paths"])

    try:
        bundle_input = GateEvidenceBundleInput(**data)
    except (TypeError, ValueError) as exc:
        return {
            "status": "error",
            "command": "bundle evidence",
            "result": None,
            "error": f"Invalid GateEvidenceBundleInput data: {exc}",
        }

    result = build_gate_evidence_bundle(bundle_input, output_dir=output_dir)

    return {
        "status": "ok",
        "command": "bundle evidence",
        "result": {
            "bundle_status": result.status.value,
            "reason_codes": list(result.reason_codes),
            "artifact_path": result.artifact_path,
            "bundle_ref": result.bundle_ref,
            "consistency_summary": result.consistency_summary,
            "details": result.details,
        },
        "error": None,
    }


# ---------------------------------------------------------------------------
# Propose improvement candidate file
# ---------------------------------------------------------------------------


def propose_improvement_candidate_file(path: str, output_dir: str = ".") -> dict:
    """Read a JSON file, parse as ImprovementCandidateInput, and propose.

    Parameters
    ----------
    path:
        Path to a JSON file containing ImprovementCandidateInput data.
    output_dir:
        Directory where the candidate artifact will be written.

    Returns
    -------
    dict
        A JSON-serializable result dict with keys:
        ``status``, ``command``, ``result``, ``error``.
    """
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return {
            "status": "error",
            "command": "improve propose",
            "result": None,
            "error": f"File not found: {path}",
        }
    except OSError as exc:
        return {
            "status": "error",
            "command": "improve propose",
            "result": None,
            "error": f"Error reading file: {exc}",
        }

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return {
            "status": "error",
            "command": "improve propose",
            "result": None,
            "error": f"Invalid JSON: {exc}",
        }

    if not isinstance(data, dict):
        return {
            "status": "error",
            "command": "improve propose",
            "result": None,
            "error": "JSON root must be an object",
        }

    # Convert list fields to tuples
    if "source_reason_codes" in data and isinstance(data["source_reason_codes"], list):
        data["source_reason_codes"] = tuple(data["source_reason_codes"])
    if "evidence_refs" in data and isinstance(data["evidence_refs"], list):
        data["evidence_refs"] = tuple(data["evidence_refs"])

    try:
        candidate_input = ImprovementCandidateInput(**data)
    except (TypeError, ValueError) as exc:
        return {
            "status": "error",
            "command": "improve propose",
            "result": None,
            "error": f"Invalid ImprovementCandidateInput data: {exc}",
        }

    result = propose_improvement_candidate(candidate_input, output_dir=output_dir)

    return {
        "status": "ok",
        "command": "improve propose",
        "result": {
            "proposal_status": result.status.value,
            "reason_codes": list(result.reason_codes),
            "candidate_id": result.candidate.candidate_id if result.candidate else None,
            "improvement_category": result.candidate.improvement_category if result.candidate else None,
            "artifact_path": result.artifact_path,
            "details": result.details,
        },
        "error": None,
    }


# ---------------------------------------------------------------------------
# Build session continuity packet file
# ---------------------------------------------------------------------------


def build_session_continuity_packet_file(path: str, output_dir: str = ".") -> dict:
    """Read a JSON file, parse as SessionContinuityInput, and build packet.

    Parameters
    ----------
    path:
        Path to a JSON file containing SessionContinuityInput data.
    output_dir:
        Directory where the packet artifact will be written.

    Returns
    -------
    dict
        A JSON-serializable result dict with keys:
        ``status``, ``command``, ``result``, ``error``.
    """
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return {
            "status": "error",
            "command": "session new",
            "result": None,
            "error": f"File not found: {path}",
        }
    except OSError as exc:
        return {
            "status": "error",
            "command": "session new",
            "result": None,
            "error": f"Error reading file: {exc}",
        }

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return {
            "status": "error",
            "command": "session new",
            "result": None,
            "error": f"Invalid JSON: {exc}",
        }

    if not isinstance(data, dict):
        return {
            "status": "error",
            "command": "session new",
            "result": None,
            "error": "JSON root must be an object",
        }

    # Convert list fields to tuples
    for list_field in ("gate_evidence_refs", "improvement_candidate_refs",
                       "known_drift_risks", "deferred_capabilities",
                       "blocked_actions", "files_in_scope", "files_out_of_scope",
                       "evidence_refs"):
        if list_field in data and isinstance(data[list_field], list):
            data[list_field] = tuple(data[list_field])

    try:
        continuity_input = SessionContinuityInput(**data)
    except (TypeError, ValueError) as exc:
        return {
            "status": "error",
            "command": "session new",
            "result": None,
            "error": f"Invalid SessionContinuityInput data: {exc}",
        }

    result = build_session_continuity_packet(continuity_input, output_dir=output_dir)

    return {
        "status": "ok",
        "command": "session new",
        "result": {
            "continuity_status": result.status.value,
            "reason_codes": list(result.reason_codes),
            "continuity_ref": result.packet.continuity_ref if result.packet else None,
            "artifact_path": result.artifact_path,
            "details": result.details,
        },
        "error": None,
    }


# ---------------------------------------------------------------------------
# Backlog enqueue file
# ---------------------------------------------------------------------------


def backlog_enqueue_file(path: str, output_dir: str = ".", backlog_store_dir: str = ".ariadne/backlog") -> dict:
    """Read a JSON file, parse as BacklogItemInput, and enqueue.

    Parameters
    ----------
    path:
        Path to a JSON file containing BacklogItemInput data.
    output_dir:
        Directory where the item artifact will be written.
    backlog_store_dir:
        Directory for durable backlog persistence.

    Returns
    -------
    dict
        A JSON-serializable result dict with keys:
        ``status``, ``command``, ``result``, ``error``.
    """
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return {
            "status": "error",
            "command": "backlog enqueue",
            "result": None,
            "error": f"File not found: {path}",
        }
    except OSError as exc:
        return {
            "status": "error",
            "command": "backlog enqueue",
            "result": None,
            "error": f"Error reading file: {exc}",
        }

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return {
            "status": "error",
            "command": "backlog enqueue",
            "result": None,
            "error": f"Invalid JSON: {exc}",
        }

    if not isinstance(data, dict):
        return {
            "status": "error",
            "command": "backlog enqueue",
            "result": None,
            "error": "JSON root must be an object",
        }

    # Convert list fields to tuples
    for list_field in ("source_reason_codes", "evidence_refs",
                       "blocked_actions", "drift_risks"):
        if list_field in data and isinstance(data[list_field], list):
            data[list_field] = tuple(data[list_field])

    try:
        backlog_input = BacklogItemInput(**data)
    except (TypeError, ValueError) as exc:
        return {
            "status": "error",
            "command": "backlog enqueue",
            "result": None,
            "error": f"Invalid BacklogItemInput data: {exc}",
        }

    result = enqueue_backlog_item(backlog_input, output_dir=output_dir, backlog_store_dir=backlog_store_dir)

    return {
        "status": "ok",
        "command": "backlog enqueue",
        "result": {
            "backlog_status": result.status,
            "reason_codes": list(result.reason_codes),
            "backlog_item_ref": result.backlog_item.backlog_item_ref if result.backlog_item else None,
            "artifact_path": result.artifact_path,
            "total_count": result.total_count,
            "details": result.details,
        },
        "error": None,
    }


# ---------------------------------------------------------------------------
# Backlog list
# ---------------------------------------------------------------------------


def backlog_list(status_filter: str | None = None, backlog_store_dir: str = ".ariadne/backlog") -> dict:
    """List backlog items from the durable store.

    Parameters
    ----------
    status_filter:
        Optional status to filter by.
    backlog_store_dir:
        Directory for durable backlog persistence.

    Returns
    -------
    dict
        A JSON-serializable result dict with keys:
        ``status``, ``command``, ``result``, ``error``.
    """
    result = list_backlog(status_filter=status_filter, backlog_store_dir=backlog_store_dir)

    items_list = []
    for item in result.backlog_items:
        items_list.append({
            "backlog_item_ref": item.backlog_item_ref,
            "candidate_ref": item.candidate_ref,
            "status": item.status,
            "improvement_category": item.improvement_category,
            "next_safe_action": item.next_safe_action,
            "requires_human_review": item.requires_human_review,
        })

    return {
        "status": "ok",
        "command": "backlog list",
        "result": {
            "backlog_status": result.status,
            "items": items_list,
            "total_count": result.total_count,
        },
        "error": None,
    }


# ---------------------------------------------------------------------------
# Backlog archive file
# ---------------------------------------------------------------------------


def backlog_archive_file(backlog_item_ref: str, target_status: str = "archived", backlog_store_dir: str = ".ariadne/backlog") -> dict:
    """Archive or reject a backlog item.

    Parameters
    ----------
    backlog_item_ref:
        The ref of the backlog item to archive.
    target_status:
        Target status: ``"archived"`` or ``"rejected"``.
    backlog_store_dir:
        Directory for durable backlog persistence.

    Returns
    -------
    dict
        A JSON-serializable result dict with keys:
        ``status``, ``command``, ``result``, ``error``.
    """
    result = archive_backlog_item(backlog_item_ref, target_status=target_status, backlog_store_dir=backlog_store_dir)

    return {
        "status": "ok",
        "command": "backlog archive",
        "result": {
            "backlog_status": result.status,
            "reason_codes": list(result.reason_codes),
            "backlog_item_ref": result.backlog_item.backlog_item_ref if result.backlog_item else None,
            "details": result.details,
        },
        "error": None,
    }


# ---------------------------------------------------------------------------
# Backlog surface
# ---------------------------------------------------------------------------


def backlog_surface(
    backlog_store_dir: str = ".ariadne/backlog",
    status_filter: str | None = None,
    category_filter: str | None = None,
    max_items: int = 0,
) -> dict:
    """Build a read-only surface view of the self-improvement backlog.

    Parameters
    ----------
    backlog_store_dir:
        Directory for durable backlog persistence.
    status_filter:
        Optional status to filter by.
    category_filter:
        Optional category to filter by.
    max_items:
        Maximum number of items to include (0 = unlimited).

    Returns
    -------
    dict
        A JSON-serializable result dict with keys:
        ``status``, ``command``, ``result``, ``error``.
    """
    inp = BacklogSurfaceInput(
        backlog_store_dir=backlog_store_dir,
        status_filter=status_filter,
        category_filter=category_filter,
        max_items=max_items,
    )
    result = build_backlog_surface(inp)

    if result.status == BacklogSurfaceStatus.REJECTED:
        return {
            "status": "ok",
            "command": "backlog surface",
            "result": {
                "surface_status": result.status.value,
                "reason_codes": list(result.reason_codes),
                "details": result.details,
            },
            "error": None,
        }

    if result.surface_view is None:
        return {
            "status": "ok",
            "command": "backlog surface",
            "result": {
                "surface_status": result.status.value,
                "view": None,
                "summary": None,
                "human_review_required_count": 0,
                "drift_risk_items": [],
                "ready_for_review_items": [],
            },
            "error": None,
        }

    view = result.surface_view
    return {
        "status": "ok",
        "command": "backlog surface",
        "result": {
            "surface_status": result.status.value,
            "view": {
                "items": list(view.items),
                "summary": view.summary,
                "total_count": view.total_count,
                "human_review_required_count": view.human_review_required_count,
                "drift_risk_items": list(view.drift_risk_items),
                "ready_for_review_items": list(view.ready_for_review_items),
            },
        },
        "error": None,
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    """Argument-based entry point for ``python -m runner``."""
    parser = argparse.ArgumentParser(
        prog="python -m runner",
        description="Platform runner command line utilities.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Existing doctor subcommand
    subparsers.add_parser("doctor", help="Run platform-runner runtime diagnostics.")

    # Validate subcommand group
    validate_parser = subparsers.add_parser("validate", help="Validate proof refs or handoff packets.")
    validate_subparsers = validate_parser.add_subparsers(dest="validate_command", required=True)

    # validate proof <path>
    proof_parser = validate_subparsers.add_parser("proof", help="Validate a proof ref JSON file.")
    proof_parser.add_argument("path", help="Path to the proof ref JSON file.")

    # validate handoff <path>
    handoff_parser = validate_subparsers.add_parser("handoff", help="Validate a handoff packet JSON file.")
    handoff_parser.add_argument("path", help="Path to the handoff packet JSON file.")
    handoff_parser.add_argument(
        "--current-product-state-ref",
        help="Override current product state ref for stale-state check.",
    )
    handoff_parser.add_argument(
        "--admissible-ref-ids",
        nargs="*",
        help="List of admissible proof ref IDs.",
    )

    # Capture subcommand group
    capture_parser = subparsers.add_parser("capture", help="Capture proof artifacts.")
    capture_subparsers = capture_parser.add_subparsers(dest="capture_command", required=True)

    # capture proof <path>
    capture_proof_parser = capture_subparsers.add_parser("proof", help="Capture a proof artifact from a JSON input file.")
    capture_proof_parser.add_argument("path", help="Path to the proof capture input JSON file.")
    capture_proof_parser.add_argument(
        "--output-dir",
        default=".",
        help="Directory where the artifact will be written (default: current directory).",
    )

    # Freeze subcommand group
    freeze_parser = subparsers.add_parser("freeze", help="Freeze acceptance criteria.")
    freeze_subparsers = freeze_parser.add_subparsers(dest="freeze_command", required=True)

    # freeze criteria <path>
    freeze_criteria_parser = freeze_subparsers.add_parser("criteria", help="Freeze acceptance criteria from a JSON input file.")
    freeze_criteria_parser.add_argument("path", help="Path to the acceptance criteria freeze input JSON file.")
    freeze_criteria_parser.add_argument(
        "--output-dir",
        default=".",
        help="Directory where the artifact will be written (default: current directory).",
    )

    # Bundle subcommand group
    bundle_parser = subparsers.add_parser("bundle", help="Build gate evidence bundles.")
    bundle_subparsers = bundle_parser.add_subparsers(dest="bundle_command", required=True)

    # bundle evidence <path>
    bundle_evidence_parser = bundle_subparsers.add_parser("evidence", help="Build a gate evidence bundle from a JSON input file.")
    bundle_evidence_parser.add_argument("path", help="Path to the gate evidence bundle input JSON file.")
    bundle_evidence_parser.add_argument(
        "--output-dir",
        default=".",
        help="Directory where the bundle artifact will be written (default: current directory).",
    )

    # Improve subcommand group
    improve_parser = subparsers.add_parser("improve", help="Propose improvement candidates.")
    improve_subparsers = improve_parser.add_subparsers(dest="improve_command", required=True)

    # improve propose <path>
    improve_propose_parser = improve_subparsers.add_parser("propose", help="Propose an improvement candidate from a JSON input file.")
    improve_propose_parser.add_argument("path", help="Path to the improvement candidate input JSON file.")
    improve_propose_parser.add_argument(
        "--output-dir",
        default=".",
        help="Directory where the candidate artifact will be written (default: current directory).",
    )

    # Session subcommand group
    session_parser = subparsers.add_parser("session", help="Manage session continuity packets.")
    session_subparsers = session_parser.add_subparsers(dest="session_command", required=True)

    # session new <path>
    session_new_parser = session_subparsers.add_parser("new", help="Create a session continuity packet from a JSON input file.")
    session_new_parser.add_argument("path", help="Path to the session continuity input JSON file.")
    session_new_parser.add_argument(
        "--output-dir",
        default=".",
        help="Directory where the packet artifact will be written (default: current directory).",
    )

    # Backlog subcommand group
    backlog_parser = subparsers.add_parser("backlog", help="Manage self-improvement backlog.")
    backlog_subparsers = backlog_parser.add_subparsers(dest="backlog_command", required=True)

    # backlog enqueue <path>
    backlog_enqueue_parser = backlog_subparsers.add_parser("enqueue", help="Enqueue a backlog item from a JSON input file.")
    backlog_enqueue_parser.add_argument("path", help="Path to the backlog item input JSON file.")
    backlog_enqueue_parser.add_argument(
        "--output-dir",
        default=".",
        help="Directory where the item artifact will be written (default: current directory).",
    )
    backlog_enqueue_parser.add_argument(
        "--backlog-store-dir",
        default=".ariadne/backlog",
        help="Directory for durable backlog persistence (default: .ariadne/backlog).",
    )

    # backlog list
    backlog_list_parser = backlog_subparsers.add_parser("list", help="List backlog items.")
    backlog_list_parser.add_argument(
        "--status",
        default=None,
        help="Optional status filter: new, human_review, archived, rejected",
    )
    backlog_list_parser.add_argument(
        "--backlog-store-dir",
        default=".ariadne/backlog",
        help="Directory for durable backlog persistence (default: .ariadne/backlog).",
    )

    # backlog archive <ref>
    backlog_archive_parser = backlog_subparsers.add_parser("archive", help="Archive or reject a backlog item.")
    backlog_archive_parser.add_argument("ref", help="Backlog item ref to archive.")
    backlog_archive_parser.add_argument(
        "--status",
        default="archived",
        choices=["archived", "rejected"],
        help="Target status: archived or rejected (default: archived).",
    )
    backlog_archive_parser.add_argument(
        "--backlog-store-dir",
        default=".ariadne/backlog",
        help="Directory for durable backlog persistence (default: .ariadne/backlog).",
    )

    # backlog surface
    backlog_surface_parser = backlog_subparsers.add_parser("surface", help="Show a read-only surface view of the self-improvement backlog.")
    backlog_surface_parser.add_argument(
        "--status",
        default=None,
        help="Optional status filter: new, human_review, archived, rejected",
    )
    backlog_surface_parser.add_argument(
        "--category",
        default=None,
        help="Optional category filter: self_improvement, continuity_followup, drift_risk, validation_gap, frontend_visibility_gap, human_review_required",
    )
    backlog_surface_parser.add_argument(
        "--max-items",
        type=int,
        default=0,
        help="Maximum number of items to include (0 = unlimited).",
    )
    backlog_surface_parser.add_argument(
        "--backlog-store-dir",
        default=".ariadne/backlog",
        help="Directory for durable backlog persistence (default: .ariadne/backlog).",
    )

    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.command == "doctor":
        return run_doctor()

    if args.command == "validate":
        if args.validate_command == "proof":
            result = validate_proof_file(args.path)
            _print_json_result(result)
            return 0 if result["status"] == "ok" and result["result"] and result["result"].get("admissible") else 1

        if args.validate_command == "handoff":
            result = validate_handoff_file(
                args.path,
                current_product_state_ref=args.current_product_state_ref,
                admissible_ref_ids=args.admissible_ref_ids,
            )
            _print_json_result(result)
            if result["status"] == "error":
                return 1
            if result["result"] and result["result"].get("status") == "not_gate_ready":
                return 1
            return 0

    if args.command == "capture":
        if args.capture_command == "proof":
            result = capture_proof_file(args.path, output_dir=args.output_dir)
            _print_json_result(result)
            if result["status"] == "error":
                return 1
            if result["result"] and result["result"].get("capture_status") == "rejected":
                return 1
            return 0

    if args.command == "freeze":
        if args.freeze_command == "criteria":
            result = freeze_acceptance_criteria_file(args.path, output_dir=args.output_dir)
            _print_json_result(result)
            if result["status"] == "error":
                return 1
            if result["result"] and result["result"].get("freeze_status") == "rejected":
                return 1
            return 0

    if args.command == "bundle":
        if args.bundle_command == "evidence":
            result = build_gate_evidence_bundle_file(args.path, output_dir=args.output_dir)
            _print_json_result(result)
            if result["status"] == "error":
                return 1
            if result["result"] and result["result"].get("bundle_status") == "rejected":
                return 1
            return 0

    if args.command == "improve":
        if args.improve_command == "propose":
            result = propose_improvement_candidate_file(args.path, output_dir=args.output_dir)
            _print_json_result(result)
            if result["status"] == "error":
                return 1
            if result["result"] and result["result"].get("proposal_status") == "rejected":
                return 1
            return 0

    if args.command == "session":
        if args.session_command == "new":
            result = build_session_continuity_packet_file(args.path, output_dir=args.output_dir)
            _print_json_result(result)
            if result["status"] == "error":
                return 1
            if result["result"] and result["result"].get("continuity_status") == "rejected":
                return 1
            return 0

    if args.command == "backlog":
        if args.backlog_command == "enqueue":
            result = backlog_enqueue_file(args.path, output_dir=args.output_dir, backlog_store_dir=args.backlog_store_dir)
            _print_json_result(result)
            if result["status"] == "error":
                return 1
            if result["result"] and result["result"].get("backlog_status") == "rejected":
                return 1
            return 0

        if args.backlog_command == "list":
            result = backlog_list(status_filter=args.status, backlog_store_dir=args.backlog_store_dir)
            _print_json_result(result)
            return 0 if result["status"] == "ok" else 1

        if args.backlog_command == "archive":
            result = backlog_archive_file(args.ref, target_status=args.status, backlog_store_dir=args.backlog_store_dir)
            _print_json_result(result)
            if result["status"] == "error":
                return 1
            if result["result"] and result["result"].get("backlog_status") == "rejected":
                return 1
            return 0

        if args.backlog_command == "surface":
            result = backlog_surface(
                backlog_store_dir=args.backlog_store_dir,
                status_filter=args.status,
                category_filter=args.category,
                max_items=args.max_items,
            )
            _print_json_result(result)
            if result["status"] == "error":
                return 1
            if result["result"] and result["result"].get("surface_status") == "rejected":
                return 1
            return 0

    parser.print_usage(sys.stderr)
    return 2


# ---------------------------------------------------------------------------
# Output helper
# ---------------------------------------------------------------------------


def _print_json_result(result: dict) -> None:
    """Print a JSON result dict to stdout with deterministic formatting."""
    print(json.dumps(result, sort_keys=True, indent=2))
