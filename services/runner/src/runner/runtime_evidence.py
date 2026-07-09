"""
Runtime Evidence Read Model for Ariadne — first Artifact Workspace Read-Only UI PR.

Reads persisted local runtime artifacts (run.json, manifest.json, run-report.txt)
and normalizes them into stable typed structures for future UI consumption.

Read-only — never mutates files, never runs agents, never shells out.
"""

from __future__ import annotations

import dataclasses
import json
import os
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Output structures
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class RunEvidenceSummary:
    """Summary of a single run for list views."""

    run_id: str
    status: str
    reason_codes: tuple[str, ...]
    pipeline_status: Optional[str]
    git_boundary_status: Optional[str]
    execution_attempted: bool
    created_at: Optional[str]
    run_json_path: Optional[str]
    manifest_path: Optional[str]
    run_report_path: Optional[str]
    pr_url: Optional[str]
    missing_evidence: tuple[str, ...]
    malformed_evidence: tuple[str, ...]


@dataclasses.dataclass(frozen=True)
class RunEvidenceDetail:
    """Detailed evidence for a single run."""

    summary: RunEvidenceSummary
    execution_results: tuple[dict[str, Any], ...]
    manifest_files: tuple[str, ...]
    run_json_hash: Optional[str]
    report_preview: Optional[str]
    payload_cleanliness: Optional[Any]
    readiness: Optional[Any]
    evidence_paths: tuple[str, ...]
    source_errors: tuple[str, ...]


@dataclasses.dataclass(frozen=True)
class ArtifactEvidenceRef:
    """Reference to a single evidence artifact."""

    path: str
    exists: bool
    file_size: int
    description: str


@dataclasses.dataclass(frozen=True)
class MissingEvidenceNotice:
    """Notice about missing or malformed evidence."""

    expected_path: str
    reason: str  # e.g. "file_not_found", "unreadable", "malformed"


@dataclasses.dataclass(frozen=True)
class RuntimeEvidenceReadResult:
    """Result of a read operation."""

    ok: bool
    error: Optional[str]
    summary: Optional[RunEvidenceSummary]
    detail: Optional[RunEvidenceDetail]
    missing: tuple[MissingEvidenceNotice, ...]
    malformed: tuple[MissingEvidenceNotice, ...]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _safe_read_json(path: str) -> tuple[Optional[dict], Optional[str]]:
    """Read and parse a JSON file safely.

    Parameters
    ----------
    path:
        Path to the JSON file.

    Returns
    -------
    tuple
        (parsed_data, error_message).  ``parsed_data`` is None on failure.
    """
    if not os.path.exists(path):
        return None, "file_not_found"
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return None, "not_a_dict"
        return data, None
    except json.JSONDecodeError:
        return None, "malformed_json"
    except OSError as e:
        return None, f"read_error: {e}"


def _safe_read_text(path: str, max_chars: int = 2000) -> tuple[Optional[str], Optional[str]]:
    """Read a text file safely up to a maximum character count.

    Parameters
    ----------
    path:
        Path to the text file.
    max_chars:
        Maximum characters to read.

    Returns
    -------
    tuple
        (content, error_message).  ``content`` is None on failure.
    """
    if not os.path.exists(path):
        return None, "file_not_found"
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read(max_chars)
        return content, None
    except OSError as e:
        return None, f"read_error: {e}"


def _extract_pr_url(execution_results: tuple[dict[str, Any], ...]) -> Optional[str]:
    """Extract PR URL from execution results if present.

    Parameters
    ----------
    execution_results:
        Execution results from run.json.

    Returns
    -------
    Optional[str]
        PR URL if found, None otherwise.
    """
    for res in execution_results:
        if res.get("operation") == "gh_pr_create":
            pr_url = res.get("pr_url", "")
            if pr_url:
                return pr_url
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def list_run_evidence_summaries(
    runs_root: str,
) -> tuple[RunEvidenceSummary, ...]:
    """List all run evidence summaries from a runs root directory.

    Parameters
    ----------
    runs_root:
        Root directory containing run subdirectories (e.g. ``.ariadne/runs``).

    Returns
    -------
    tuple[RunEvidenceSummary, ...]
        Sorted list of run summaries (newest first by run_id).
    """
    if not os.path.isdir(runs_root):
        return ()

    run_ids: list[str] = []
    try:
        for entry in os.listdir(runs_root):
            run_dir = os.path.join(runs_root, entry)
            if os.path.isdir(run_dir):
                run_ids.append(entry)
    except OSError:
        return ()

    # Sort deterministically (reverse for newest-first convention)
    run_ids.sort(reverse=True)

    summaries: list[RunEvidenceSummary] = []
    for run_id in run_ids:
        run_dir = os.path.join(runs_root, run_id)
        run_json_path = os.path.join(run_dir, "run.json")
        manifest_path = os.path.join(run_dir, "manifest.json")
        report_path = os.path.join(run_dir, "run-report.txt")

        missing: list[str] = []
        malformed: list[str] = []

        # Read run.json
        run_data, run_err = _safe_read_json(run_json_path)
        if run_data is None:
            if run_err == "file_not_found":
                missing.append("run.json")
            else:
                malformed.append("run.json")
            # Still produce a summary with what we have
            summaries.append(
                RunEvidenceSummary(
                    run_id=run_id,
                    status="unknown",
                    reason_codes=(),
                    pipeline_status=None,
                    git_boundary_status=None,
                    execution_attempted=False,
                    created_at=None,
                    run_json_path=run_json_path if os.path.exists(run_json_path) else None,
                    manifest_path=manifest_path if os.path.exists(manifest_path) else None,
                    run_report_path=report_path if os.path.exists(report_path) else None,
                    pr_url=None,
                    missing_evidence=tuple(missing),
                    malformed_evidence=tuple(malformed),
                )
            )
            continue

        status = run_data.get("status", "unknown")
        reason_codes = tuple(run_data.get("reason_codes", []))
        pipeline_status = run_data.get("pipeline_status")
        git_boundary_status = run_data.get("git_boundary_status")
        execution_attempted = run_data.get("execution_attempted", False)
        created_at = run_data.get("finished_at") or run_data.get("started_at")
        execution_results = tuple(run_data.get("execution_results_summary", []))
        pr_url = _extract_pr_url(execution_results)

        # Check manifest
        manifest_data, manifest_err = _safe_read_json(manifest_path)
        if manifest_data is None:
            if manifest_err == "file_not_found":
                missing.append("manifest.json")
            else:
                malformed.append("manifest.json")

        # Check report
        if not os.path.exists(report_path):
            missing.append("run-report.txt")

        summaries.append(
            RunEvidenceSummary(
                run_id=run_id,
                status=status,
                reason_codes=reason_codes,
                pipeline_status=pipeline_status,
                git_boundary_status=git_boundary_status,
                execution_attempted=execution_attempted,
                created_at=created_at,
                run_json_path=run_json_path,
                manifest_path=manifest_path if os.path.exists(manifest_path) else None,
                run_report_path=report_path if os.path.exists(report_path) else None,
                pr_url=pr_url,
                missing_evidence=tuple(missing),
                malformed_evidence=tuple(malformed),
            )
        )

    return tuple(summaries)


def read_run_evidence_detail(
    runs_root: str,
    run_id: str,
) -> RuntimeEvidenceReadResult:
    """Read detailed evidence for a single run.

    Parameters
    ----------
    runs_root:
        Root directory containing run subdirectories.
    run_id:
        The run ID to read.

    Returns
    -------
    RuntimeEvidenceReadResult
        Structured read result with summary, detail, missing, and malformed.
    """
    run_dir = os.path.join(runs_root, run_id)
    run_json_path = os.path.join(run_dir, "run.json")
    manifest_path = os.path.join(run_dir, "manifest.json")
    report_path = os.path.join(run_dir, "run-report.txt")

    missing_notices: list[MissingEvidenceNotice] = []
    malformed_notices: list[MissingEvidenceNotice] = []
    source_errors: list[str] = []

    # Read run.json
    run_data, run_err = _safe_read_json(run_json_path)
    if run_data is None:
        if run_err == "file_not_found":
            missing_notices.append(
                MissingEvidenceNotice(expected_path=run_json_path, reason="file_not_found")
            )
        else:
            malformed_notices.append(
                MissingEvidenceNotice(expected_path=run_json_path, reason=run_err or "malformed")
            )
        return RuntimeEvidenceReadResult(
            ok=False,
            error=f"run.json not available for run_id={run_id}",
            summary=None,
            detail=None,
            missing=tuple(missing_notices),
            malformed=tuple(malformed_notices),
        )

    status = run_data.get("status", "unknown")
    reason_codes = tuple(run_data.get("reason_codes", []))
    pipeline_status = run_data.get("pipeline_status")
    git_boundary_status = run_data.get("git_boundary_status")
    execution_attempted = run_data.get("execution_attempted", False)
    created_at = run_data.get("finished_at") or run_data.get("started_at")
    execution_results = tuple(run_data.get("execution_results_summary", []))
    run_json_hash = run_data.get("run_json_hash")
    pr_url = _extract_pr_url(execution_results)

    # Read manifest
    manifest_data, manifest_err = _safe_read_json(manifest_path)
    manifest_files: tuple[str, ...] = ()
    if manifest_data is None:
        if manifest_err == "file_not_found":
            missing_notices.append(
                MissingEvidenceNotice(expected_path=manifest_path, reason="file_not_found")
            )
        else:
            malformed_notices.append(
                MissingEvidenceNotice(expected_path=manifest_path, reason=manifest_err or "malformed")
            )
    else:
        manifest_files = tuple(manifest_data.get("files", []))
        if not run_json_hash:
            run_json_hash = manifest_data.get("run_json_hash")

    # Read report
    report_preview: Optional[str] = None
    report_content, report_err = _safe_read_text(report_path)
    if report_content is None:
        if report_err == "file_not_found":
            missing_notices.append(
                MissingEvidenceNotice(expected_path=report_path, reason="file_not_found")
            )
        else:
            malformed_notices.append(
                MissingEvidenceNotice(expected_path=report_path, reason=report_err or "unreadable")
            )
    else:
        report_preview = report_content[:500]

    # Build evidence paths
    evidence_paths: list[str] = []
    if os.path.exists(run_json_path):
        evidence_paths.append(run_json_path)
    if os.path.exists(manifest_path):
        evidence_paths.append(manifest_path)
    if os.path.exists(report_path):
        evidence_paths.append(report_path)

    # Build summary
    summary = RunEvidenceSummary(
        run_id=run_id,
        status=status,
        reason_codes=reason_codes,
        pipeline_status=pipeline_status,
        git_boundary_status=git_boundary_status,
        execution_attempted=execution_attempted,
        created_at=created_at,
        run_json_path=run_json_path,
        manifest_path=manifest_path if os.path.exists(manifest_path) else None,
        run_report_path=report_path if os.path.exists(report_path) else None,
        pr_url=pr_url,
        missing_evidence=tuple(n.expected_path for n in missing_notices),
        malformed_evidence=tuple(n.expected_path for n in malformed_notices),
    )

    # Build detail
    detail = RunEvidenceDetail(
        summary=summary,
        execution_results=execution_results,
        manifest_files=manifest_files,
        run_json_hash=run_json_hash,
        report_preview=report_preview,
        payload_cleanliness=None,
        readiness=None,
        evidence_paths=tuple(evidence_paths),
        source_errors=tuple(source_errors),
    )

    ok = len(missing_notices) == 0 and len(malformed_notices) == 0

    return RuntimeEvidenceReadResult(
        ok=ok,
        error=None if ok else "missing or malformed evidence",
        summary=summary,
        detail=detail,
        missing=tuple(missing_notices),
        malformed=tuple(malformed_notices),
    )
