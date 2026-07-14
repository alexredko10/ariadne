"""
Run Evidence Serialization Contract — version 1.

Pure serialization helpers for runtime evidence route responses.
No filesystem access, no ASGI routing, no mutation, no external dependencies.
"""

from __future__ import annotations

from typing import Any, Optional

from runner.runtime_evidence import (
    RunEvidenceSummary,
    RunEvidenceDetail,
    RuntimeEvidenceReadResult,
)

EVIDENCE_CONTRACT_VERSION = "1"


def serialize_run_evidence_summary(
    s: RunEvidenceSummary,
) -> dict:
    """Serialize a RunEvidenceSummary to a JSON-safe dict.

    Parameters
    ----------
    s:
        The run evidence summary to serialize.

    Returns
    -------
    dict
        JSON-safe dict with exact contract key set.
    """
    return {
        "run_id": s.run_id,
        "status": s.status,
        "reason_codes": list(s.reason_codes),
        "pipeline_status": s.pipeline_status,
        "git_boundary_status": s.git_boundary_status,
        "execution_attempted": s.execution_attempted,
        "created_at": s.created_at,
        "run_json_available": s.run_json_path is not None,
        "manifest_available": s.manifest_path is not None,
        "run_report_available": s.run_report_path is not None,
        "missing_evidence": list(s.missing_evidence),
        "malformed_evidence": list(s.malformed_evidence),
        "pr_url": s.pr_url,
        "payload_cleanliness_available": False,
        "readiness_available": False,
    }


def serialize_run_evidence_detail(
    result: RuntimeEvidenceReadResult,
) -> dict:
    """Serialize a RuntimeEvidenceReadResult to a JSON-safe dict.

    Parameters
    ----------
    result:
        The runtime evidence read result to serialize.

    Returns
    -------
    dict
        JSON-safe dict with exact contract key sets for envelope,
        summary, detail, and evidence notices.
    """
    response: dict = {
        "ev_contract_version": EVIDENCE_CONTRACT_VERSION,
        "ok": result.ok,
        "error": result.error,
    }

    if result.summary is not None:
        response["summary"] = serialize_run_evidence_summary(result.summary)
    else:
        response["summary"] = None

    if result.detail is not None:
        response["detail"] = {
            "execution_results": [dict(r) for r in result.detail.execution_results],
            "manifest_files": list(result.detail.manifest_files),
            "run_json_hash": result.detail.run_json_hash,
            "report_preview": result.detail.report_preview,
            "evidence_paths": list(result.detail.evidence_paths),
            "source_errors": list(result.detail.source_errors),
        }
    else:
        response["detail"] = None

    response["payload_cleanliness"] = (
        result.detail.payload_cleanliness if result.detail is not None else None
    )
    response["readiness"] = (
        result.detail.readiness if result.detail is not None else None
    )
    response["missing"] = [
        {"expected_path": n.expected_path, "reason": n.reason}
        for n in result.missing
    ]
    response["malformed"] = [
        {"expected_path": n.expected_path, "reason": n.reason}
        for n in result.malformed
    ]

    return response


def serialize_run_index(
    summaries: tuple[RunEvidenceSummary, ...],
    runs_root: str,
    ok: bool = True,
    error: Optional[str] = None,
) -> dict:
    """Serialize a run index response.

    Parameters
    ----------
    summaries:
        Run evidence summaries.
    runs_root:
        The runs root path used.
    ok:
        Whether the request succeeded.
    error:
        Error message if not ok.

    Returns
    -------
    dict
        JSON-safe dict with exact contract key set.
    """
    response: dict = {
        "ev_contract_version": EVIDENCE_CONTRACT_VERSION,
        "ok": ok,
        "count": len(summaries) if ok else 0,
        "runs": [serialize_run_evidence_summary(s) for s in summaries] if ok else [],
        "runs_root": runs_root,
    }
    if error is not None:
        response["error"] = error
    return response
