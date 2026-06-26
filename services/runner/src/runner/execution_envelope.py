"""
Execution artifact envelope — deterministic normalization of runtime artifacts
and evidence from execution request/result data.

No filesystem reads, no filesystem writes, no digest computation from disk,
no subprocess, no network, no wall-clock timing, no random IDs.
"""

from __future__ import annotations

import hashlib
from typing import Any


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_envelope_id(req_id: str, result_id: str) -> str:
    """Generate a deterministic envelope ID from request and result IDs."""
    digest = hashlib.sha256(f"{req_id}{result_id}".encode("utf-8")).hexdigest()
    return f"env_{digest[:12]}"


def _normalize_artifact(
    artifact: Any,
    index: int,
    result_id: str,
) -> dict:
    """Normalize a single artifact entry.

    Parameters
    ----------
    artifact
        The raw artifact dict.
    index
        The index of this artifact in the list.
    result_id
        The execution result ID for deterministic fill of missing IDs.

    Returns
    -------
    dict
        A normalized artifact dict.
    """
    if not isinstance(artifact, dict):
        return _artifact_fallback(result_id, index)

    result: dict[str, Any] = {}

    # artifact_id
    aid = artifact.get("artifact_id")
    result["artifact_id"] = aid if aid else f"artifact-{result_id}-{index}"

    # kind
    result["kind"] = artifact.get("kind", "")

    # reference
    ref = artifact.get("reference")
    if ref:
        result["reference"] = ref

    # relative_path (alias from "path" if needed)
    rel = artifact.get("relative_path") or artifact.get("path")
    if rel:
        result["relative_path"] = rel
        if isinstance(rel, str) and rel.startswith("/"):
            result["_warning"] = "absolute path"

    # digest — preserve only if non-empty
    dig = artifact.get("digest")
    if dig:
        result["digest"] = dig

    # producer
    result["producer"] = artifact.get("producer", "execution_adapter")

    return result


def _artifact_fallback(result_id: str, index: int) -> dict:
    """Return a fallback artifact entry for malformed input."""
    return {
        "artifact_id": f"artifact-{result_id}-{index}",
        "producer": "execution_adapter",
    }


def _normalize_evidence(
    evidence: Any,
    index: int,
    result_id: str,
) -> dict:
    """Normalize a single evidence entry.

    Parameters
    ----------
    evidence
        The raw evidence dict.
    index
        The index of this evidence in the list.
    result_id
        The execution result ID for deterministic fill of missing IDs.

    Returns
    -------
    dict
        A normalized evidence dict.
    """
    if not isinstance(evidence, dict):
        return _evidence_fallback(result_id, index)

    result: dict[str, Any] = {}

    # evidence_id
    eid = evidence.get("evidence_id")
    result["evidence_id"] = eid if eid else f"evidence-{result_id}-{index}"

    # kind
    result["kind"] = evidence.get("kind", "")

    # summary
    result["summary"] = evidence.get("summary", "")

    # status
    status = evidence.get("status")
    if status:
        result["status"] = status

    # supports
    supports = evidence.get("supports")
    if supports:
        result["supports"] = supports

    # producer
    result["producer"] = evidence.get("producer", "execution_adapter")

    return result


def _evidence_fallback(result_id: str, index: int) -> dict:
    """Return a fallback evidence entry for malformed input."""
    return {
        "evidence_id": f"evidence-{result_id}-{index}",
        "producer": "execution_adapter",
    }


# ---------------------------------------------------------------------------
# Envelope
# ---------------------------------------------------------------------------


def build_execution_envelope(
    execution_request: dict,
    execution_result: dict,
) -> dict:
    """Build a deterministic execution envelope from request and result.

    Parameters
    ----------
    execution_request
        The RunnerExecutionRequest dict.
    execution_result
        The RunnerExecutionResult dict.

    Returns
    -------
    dict
        A normalized envelope dict.
    """
    errors: list[dict] = []
    warnings: list[str] = []

    # --- Validate input types ---
    if not isinstance(execution_request, dict):
        errors.append({
            "code": "invalid_envelope_input",
            "message": "execution_request must be a dict.",
            "field": "execution_request",
        })
        execution_request = {}

    if not isinstance(execution_result, dict):
        errors.append({
            "code": "invalid_envelope_input",
            "message": "execution_result must be a dict.",
            "field": "execution_result",
        })
        execution_result = {}

    # --- Validate required IDs ---
    req_id = execution_request.get("execution_request_id", "")
    result_id = execution_result.get("execution_result_id", "")
    run_id = execution_request.get("run_id", "")

    if not req_id:
        errors.append({
            "code": "invalid_envelope_input",
            "message": "execution_request_id is required.",
            "field": "execution_request_id",
        })

    if not result_id:
        errors.append({
            "code": "invalid_envelope_input",
            "message": "execution_result_id is required.",
            "field": "execution_result_id",
        })

    if not run_id:
        errors.append({
            "code": "invalid_envelope_input",
            "message": "run_id is required.",
            "field": "run_id",
        })

    # --- Build envelope ---
    envelope_id = _make_envelope_id(req_id, result_id) if req_id and result_id else ""

    status = execution_result.get("status", "failed") if isinstance(execution_result, dict) else "failed"
    # Override status to failed if there were input-level errors
    if errors:
        status = "failed"

    # --- Normalize artifacts ---
    raw_artifacts = execution_result.get("artifacts", []) if isinstance(execution_result, dict) else []
    if not isinstance(raw_artifacts, list):
        raw_artifacts = []
        warnings.append("artifacts was not a list; treated as empty")

    normalized_artifacts: list[dict] = []
    for i, art in enumerate(raw_artifacts):
        normalized = _normalize_artifact(art, i, result_id)
        # Collect path warnings
        if normalized.get("_warning") == "absolute path":
            warnings.append(
                f"artifact {normalized['artifact_id']}: absolute path "
                f"'{normalized.get('relative_path', '')}'"
            )
            del normalized["_warning"]
        normalized_artifacts.append(normalized)

    # --- Normalize evidence ---
    raw_evidence = execution_result.get("evidence", []) if isinstance(execution_result, dict) else []
    if not isinstance(raw_evidence, list):
        raw_evidence = []
        warnings.append("evidence was not a list; treated as empty")

    normalized_evidence: list[dict] = []
    for i, ev in enumerate(raw_evidence):
        normalized_evidence.append(_normalize_evidence(ev, i, result_id))

    # --- Assemble ---
    metadata: dict[str, Any] = {}
    if isinstance(execution_result, dict):
        metadata["adapter"] = execution_result.get("adapter", "")
    if isinstance(execution_request, dict):
        metadata["execution_mode"] = execution_request.get("execution_mode", "")

    return {
        "schema_version": "0.1",
        "envelope_id": envelope_id,
        "execution_request_id": req_id,
        "execution_result_id": result_id,
        "run_id": run_id,
        "status": status,
        "artifacts": normalized_artifacts,
        "evidence": normalized_evidence,
        "errors": errors,
        "warnings": warnings,
        "metadata": metadata,
    }
